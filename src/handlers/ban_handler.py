import logging

from telegram import InlineKeyboardMarkup, Update

from src.service import BanService
from src.util.encodings import decode_unban_user
from src.util.telegram import CustomContext
from src.view.ban_views import build_banned_users_keyboard


class BanHandler:
    """Handler class for ban-related commands and callbacks."""

    def __init__(self, ban_service: BanService):
        self.ban_service = ban_service
        self.logger = logging.getLogger(__name__)

    async def get_bans(self, update: Update, _: CustomContext) -> int:
        """Gets all banned users for the command issuer."""
        user_id = update.message.from_user.id
        banned = self.ban_service.get_banned_users(str(user_id))
        if not banned:
            await update.message.reply_text("You have not banned any users.")
            return

        keyboard = build_banned_users_keyboard(banned)
        await update.message.reply_text(
            "Click users to unban:", reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def unban_user(self, update: Update, _: CustomContext) -> None:
        """Unbans a user when the corresponding button is clicked."""
        query = update.callback_query
        await query.answer()
        user_to_unban = decode_unban_user(query.data)
        issuer_user_id = str(query.from_user.id)

        self.ban_service.unban_user(user_to_unban, issuer_user_id)
        self.logger.info("User %s unbanned user %s.", issuer_user_id, user_to_unban)
        banned = self.ban_service.get_banned_users(issuer_user_id)
        if banned:
            keyboard = build_banned_users_keyboard(banned)
            await query.edit_message_text(
                f"Unbanned user: {user_to_unban}",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return
        await query.edit_message_text(f"Unbanned user: {user_to_unban}")
