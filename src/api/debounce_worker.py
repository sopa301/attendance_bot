"""Main application file for the Telegram bot."""

import json
import os

import redis
from flask import Blueprint, request
from qstash.receiver import Receiver
from telegram import Bot
from telegram.error import BadRequest
from telegram.request import HTTPXRequest

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
    await update_inline_message(state, receiver_bot)

    # 7. Cleanup
    redis_client.delete(debounce_key)

    return ("OK", 200)


async def update_inline_message(state, receiver_bot: Bot):
    """Given the serialized state, update the inline message."""
    print("Updating inline message with state:", state)
    try:
        await receiver_bot.edit_message_text(**json.loads(state))
    except BadRequest as e:
        print("Failed to edit message:", e)
