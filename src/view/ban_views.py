"""View utilities for ban-related views."""

from telegram import InlineKeyboardButton

from src.util.encodings import encode_unban_user


def build_banned_users_keyboard(banned_users: list) -> list:
    """Builds a keyboard layout for the list of banned users."""
    keyboard = []
    for username in banned_users:
        keyboard.append(
            [InlineKeyboardButton(username, callback_data=encode_unban_user(username))]
        )
    return keyboard
