"""General purpose handlers for the bot."""

import html
import json
import logging
import traceback

from telegram import ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import ConversationHandler

from util import CANCEL_TEXT, INFO_TEXT, START_TEXT, CustomContext, WebhookUpdate


class GeneralHandler:
    """General purpose handler class for the bot."""

    def __init__(self, admin_chat_id: str):
        self.admin_chat_id = admin_chat_id
        # Enable logging
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        # set higher logging level for httpx to avoid all GET and POST requests being logged
        logging.getLogger("httpx").setLevel(logging.WARNING)
        self.logger = logging.getLogger(__name__)

    async def start(self, update: Update, _: CustomContext) -> int:
        """Sends a message when the command /start is issued."""
        await update.message.reply_text(START_TEXT)
        return ConversationHandler.END

    async def get_info(self, update: Update, _: CustomContext) -> int:
        """Sends info about the bot when the command /info is issued."""
        await update.message.reply_text(INFO_TEXT)
        return ConversationHandler.END

    async def cancel(self, update: Update, _: CustomContext) -> int:
        """Ends the conversation."""
        await update.message.reply_text(CANCEL_TEXT, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    async def webhook_update(
        self, update: WebhookUpdate, context: CustomContext
    ) -> None:
        """Handle custom updates."""
        chat_member = await context.bot.get_chat_member(
            chat_id=update.user_id, user_id=update.user_id
        )
        payloads = context.user_data.setdefault("payloads", [])
        payloads.append(update.payload)
        combined_payloads = "</code>\n• <code>".join(payloads)
        text = (
            f"The user {chat_member.user.mention_html()} has sent a new payload. "
            f"So far they have sent the following payloads: \n\n• <code>{combined_payloads}</code>"
        )
        await context.bot.send_message(
            chat_id=self.admin_chat_id, text=text, parse_mode=ParseMode.HTML
        )

    async def error_handler(self, update: object, context: CustomContext) -> None:
        """Log the error and send a telegram message to notify the developer."""
        # Log the error before we do anything else, so we can see it even if something breaks.
        self.logger.error("Exception while handling an update:", exc_info=context.error)

        # traceback.format_exception returns the usual python message about an exception, but as a
        # list of strings rather than a single string, so we have to join them together.
        tb_list = traceback.format_exception(
            None, context.error, context.error.__traceback__
        )
        tb_string = "".join(tb_list)

        # Build the message with some markup and additional information about what happened.
        # You might need to add some logic to deal with messages
        # longer than the 4096 character limit.
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            "An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
            "</pre>\n\n"
            f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
            f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        )
        message2 = f"<pre>{html.escape(tb_string)}</pre>"

        # Finally, send the message
        await context.bot.send_message(
            chat_id=self.admin_chat_id, text=message, parse_mode=ParseMode.HTML
        )
        await context.bot.send_message(
            chat_id=self.admin_chat_id, text=message2, parse_mode=ParseMode.HTML
        )

    async def do_nothing(self, update: Update, _: CustomContext) -> None:
        """Answer the callback query but do nothing."""
        await update.callback_query.answer()
