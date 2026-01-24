"""Main application file for the Telegram bot."""

import json
import logging
import os

import redis
from bson import ObjectId
from flask import Blueprint, request
from qstash import QStash
from qstash.receiver import Receiver
from telegram import Bot, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.request import HTTPXRequest

from src.repositories import ban_repo, poll_group_repo, poll_repo
from src.service import BanService, PollGroupService, PollService
from src.util import Membership, import_env
from src.view import build_voting_buttons, generate_poll_group_text

QSTASH_CURRENT_SIGNING_KEY = os.environ["QSTASH_CURRENT_SIGNING_KEY"]
QSTASH_NEXT_SIGNING_KEY = os.environ.get("QSTASH_NEXT_SIGNING_KEY")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
BOT_TOKEN = os.environ["BOT_TOKEN"]

receiver = Receiver(
    current_signing_key=QSTASH_CURRENT_SIGNING_KEY,
    next_signing_key=QSTASH_NEXT_SIGNING_KEY,
)
redis_client = redis.from_url(REDIS_URL)
bp = Blueprint("debounce_worker", __name__)

# import env variables
env_variables = [
    "DEPLOYMENT_URL",
    "BOT_TOKEN",
    "MONGO_URL",
    "MONGO_DB_NAME",
    "MONGO_POLLS_COLLECTION_NAME",
    "MONGO_GROUPS_COLLECTION_NAME",
    "MONGO_BANS_COLLECTION_NAME",
    "REDIS_URL",
    "QSTASH_TOKEN",
]
env_config = import_env(env_variables)

# Instantiate services
redis_client = redis.from_url(env_config["REDIS_URL"], decode_responses=True)
qstash_client = QStash(env_config["QSTASH_TOKEN"])

ban_service = BanService(ban_repo)
poll_service = PollService(poll_repo, ban_service)
poll_group_service = PollGroupService(poll_group_repo, poll_service)

logger = logging.getLogger(__name__)


@bp.route("/qstash_debounced", methods=["POST"])
async def handler():
    """Specialised QStash handler for debounced tasks. Dumbly executes any tasks given."""

    # 1. Read body + signature
    body_bytes = request.get_data()
    body = body_bytes.decode("utf-8")
    signature = request.headers.get("Upstash-Signature")

    if not signature:
        return ("Missing signature", 401)

    # 2. Verify QStash signature
    try:
        receiver.verify(signature=signature, body=body)
    except Exception as e:
        print("Signature verification failed:", e)
        return ("Invalid signature", 401)

    # 3. Parse payload
    try:
        data = json.loads(body)
        debounce_key = data["debounce_key"]
    except Exception as e:
        print("Payload parsing failed:", e)
        return ("Bad payload", 400)

    # 5. Load aggregated state
    state = redis_client.get(debounce_key)
    if not state:
        return ("No state, nothing to do", 200)

    # 6. Do the actual work (call your bot logic, API, etc.)
    request_object = HTTPXRequest()
    receiver_bot = Bot(token=BOT_TOKEN, request=request_object)
    await update_message_with_poll_group_details(state, receiver_bot)

    # 7. Cleanup
    redis_client.delete(debounce_key)

    return ("OK", 200)


async def update_message_with_poll_group_details(json_body, receiver_bot: Bot):
    """Given the serialized state, update the inline message."""
    logger.info("Updating inline message with state: %s", json_body)
    dct = json.loads(json_body)
    poll_group_id = ObjectId(dct["poll_group_id"])
    message_id = dct["inline_message_id"]
    poll_group, polls = poll_group_service.get_full_poll_group_details(poll_group_id)
    membership = Membership.from_data_string(dct["membership"])
    pollmaker_id = poll_group.owner_id

    try:
        await receiver_bot.edit_message_text(
            inline_message_id=message_id,
            text=generate_poll_group_text(poll_group, polls, membership),
            reply_markup=InlineKeyboardMarkup(
                build_voting_buttons(polls, membership, pollmaker_id)
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except BadRequest as e:
        logger.error("Failed to edit message:", exc_info=e)
