"""Service for updating Telegram messages."""

import json
import logging
import os

from qstash import QStash
from telegram.error import BadRequest

from src.util import Membership

DEFAULT_WAIT_TIME_MS = 2000

current_url = os.getenv("DEPLOYMENT_URL", "http://localhost:8000")


class TelegramMessageUpdater:
    """Service for updating Telegram messages with debouncing."""

    def __init__(self, redis_client, bot, qstash_client: QStash):
        self.redis_client = redis_client
        self.bot = bot
        self.qstash_client = qstash_client
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def key_name(key: str) -> str:
        """Gets the debouncer key name for Redis storage."""
        return f"debounce:{key}"

    async def update_polls_message(
        self,
        inline_message_id: str,
        text: str,
        reply_markup,
        parse_mode,
        poll_group_id: str,
        membership: Membership,
    ):
        """Update a Telegram message with debouncing."""

        debounce_key = self.key_name(inline_message_id)

        reply_markup_dict = reply_markup.to_dict()
        payload = {
            "text": text,
            "reply_markup": reply_markup_dict,
            "parse_mode": parse_mode,
            "inline_message_id": inline_message_id,
            "poll_group_id": str(poll_group_id),
            "membership": membership.value,
        }

        json_payload = json.dumps(payload)

        ttl_seconds = int(2 * DEFAULT_WAIT_TIME_MS / 1000)

        # 2. Acquire lock atomically (IMPORTANT: use NX)
        acquired = self.redis_client.set(
            debounce_key,
            json_payload,
            ex=ttl_seconds,
            nx=True,  # only set if not exists
        )

        if not acquired:
            self.logger.info(
                "Race: debounce key just acquired by another worker for %s",
                inline_message_id,
            )
            return

        # 3. Send first update immediately
        try:
            await self.bot.edit_message_text(
                text=text,
                inline_message_id=inline_message_id,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        except BadRequest as e:
            self.logger.warning("Initial edit failed: %s", e)
            # You may want to delete the key here if this fails
            self.redis_client.delete(debounce_key)
            return

        # 4. Enqueue trailing update to QStash
        try:
            self.qstash_client.message.publish_json(
                url=f"{current_url}/qstash_debounced",
                body={
                    "debounce_key": debounce_key,
                    **payload,
                },
                delay=int(DEFAULT_WAIT_TIME_MS / 1000),
            )
        except Exception as e:
            self.logger.error("Failed to enqueue QStash job: %s", e)
            self.redis_client.delete(debounce_key)
