"""Service for updating Telegram messages."""

import logging

from telegram.error import BadRequest

from src.util import Debouncer


class TelegramMessageUpdater:
    """Service for updating Telegram messages with debouncing."""

    def __init__(self, debouncer: Debouncer):
        self.debouncer = debouncer
        self.logger = logging.getLogger(__name__)

    async def update_message(self, message_id: str, message_function: callable):
        """Update a Telegram message with debouncing."""
        try:
            await self.debouncer.debounce(message_id, message_function)
        except BadRequest as e:
            self.logger.error("Failed to update message %s: %s", message_id, e)
