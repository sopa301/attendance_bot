import asyncio
import html
import json
import logging
from dataclasses import dataclass
from http import HTTPStatus

import uvicorn
from asgiref.wsgi import WsgiToAsgi
from flask import Flask, Response, abort, make_response, request

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CallbackContext,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    ExtBot,
    MessageHandler,
    TypeHandler,
    filters,
)
import traceback
from mongopersistence import MongoPersistence

from util.objects import AttendanceList
from util import import_env
from util.texts import ABSENT, PRESENT, LAST_MINUTE_CANCELLATION, \
                      REQUEST_FOR_ATTENDANCE_LIST_INPUT

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# import env variables
env_variables = ["DEPLOYMENT_URL", "BOT_TOKEN", "MONGO_URL", "MONGO_DB_NAME",
                 "MONGO_USER_DATA_COLLECTION_NAME", "PORT", "HOST", "DEVELOPER_CHAT_ID",
                 "MONGO_CHAT_DATA_COLLECTION_NAME"]
env_config = import_env(env_variables)

# Define configuration constants
URL = env_config["DEPLOYMENT_URL"] 
ADMIN_CHAT_ID = int(env_config["DEVELOPER_CHAT_ID"])
TOKEN = env_config["BOT_TOKEN"]  # nosec B105

persistence = MongoPersistence(
    mongo_url=env_config["MONGO_URL"],
    db_name=env_config["MONGO_DB_NAME"],
    name_col_user_data=env_config["MONGO_USER_DATA_COLLECTION_NAME"],  # optional
    name_col_chat_data=env_config["MONGO_CHAT_DATA_COLLECTION_NAME"],  # optional
    ignore_general_data=["cache"],
    ignore_user_data=["foo", "bar"],
    load_on_flush=False,
)

# CONSTANTS
SELECT_NEW_OR_CONTINUE, INPUT_LIST, EDIT_LIST, SUMMARY = range(4)

@dataclass
class WebhookUpdate:
    """Simple dataclass to wrap a custom update type"""

    user_id: int
    payload: str


class CustomContext(CallbackContext[ExtBot, dict, dict, dict]):
    """
    Custom CallbackContext class that makes `user_data` available for updates of type
    `WebhookUpdate`.
    """

    @classmethod
    def from_update(
        cls,
        update: object,
        application: "Application",
    ) -> "CustomContext":
        if isinstance(update, WebhookUpdate):
            return cls(application=application, user_id=update.user_id)
        return super().from_update(update, application)

async def start(update: Update, context: CustomContext) -> int:
    text = "Hi! Please click 'New List' to input a new list."
    reply_keyboard = [["New List"]]
    if "dct" in context.chat_data:
        reply_keyboard[0].append("Continue List")
        text = "Hi! Please click 'New List' to input a new list or 'Continue List' to edit the existing list."
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return SELECT_NEW_OR_CONTINUE

async def input_list(update: Update, context: CustomContext) -> int:
    message_text = update.message.text
    if (message_text == "New List"):
        if "dct" in context.chat_data:
            del context.chat_data["dct"]
        await update.message.reply_text(REQUEST_FOR_ATTENDANCE_LIST_INPUT, reply_markup=ReplyKeyboardRemove())
        return INPUT_LIST
    try:
      attendance_list = AttendanceList.parse_list(message_text)
      context.chat_data["dct"] = attendance_list.to_dict()
    except Exception as e:
      await update.message.reply_text("Invalid list format. Please input the list again.")
      logger.info(e)
      return INPUT_LIST
    await display_edit_list(AttendanceList.from_dict(context.chat_data["dct"]), update)
    return EDIT_LIST

async def edit_list(update: Update, context: CustomContext) -> int:
    """Allows the user to make edits to the list."""
    user = update.message.from_user
    logger.info("Displaying list for %s", user.first_name)
    if ("dct" not in context.chat_data):
        await update.message.reply_text("You have no list yet. Please input the list first.")
        await update.message.reply_text(REQUEST_FOR_ATTENDANCE_LIST_INPUT, reply_markup=ReplyKeyboardRemove())
        return INPUT_LIST
    await display_edit_list(AttendanceList.from_dict(context.chat_data["dct"]), update)
    return EDIT_LIST

async def display_edit_list(attendance_list: AttendanceList, update: Update) -> None:
    summary_text = attendance_list.generate_summary_text()
    inlinekeyboard = generate_inline_keyboard_list_for_edit_list(attendance_list)
    await update.message.reply_text(summary_text + "\n\nPlease choose the handle of the person you want to edit\.",
                                    reply_markup=InlineKeyboardMarkup(inlinekeyboard),
                                    parse_mode="MarkdownV2")

def generate_inline_keyboard_list_for_edit_list(attendance_list: AttendanceList) -> list:
    inlinekeyboard = []
    DO_NOTHING = "."
    inlinekeyboard.append([InlineKeyboardButton("NON REGULARS", callback_data=DO_NOTHING)])
    for index, person in enumerate(attendance_list.non_regulars):
        callback_data = person["id"]
        inlinekeyboard.append([InlineKeyboardButton(f"{index+1}. {person['name']}", callback_data=callback_data)])
    inlinekeyboard.append([InlineKeyboardButton("REGULARS", callback_data=DO_NOTHING)])
    for index, person in enumerate(attendance_list.regulars):
        callback_data = person["id"]
        inlinekeyboard.append([InlineKeyboardButton(f"{index+1}. {person['name']}", callback_data=callback_data)])
    inlinekeyboard.append([InlineKeyboardButton("STANDINS", callback_data=DO_NOTHING)])
    for index, person in enumerate(attendance_list.standins):
        callback_data = person["id"]
        inlinekeyboard.append([InlineKeyboardButton(f"{index+1}. {person['name']}", callback_data=callback_data)])
    return inlinekeyboard
    

async def summary(update: Update, context: CustomContext) -> int:
    """Prints the attendance summary"""
    logger.info("User requested for the summary.")
    if ("dct" not in context.chat_data):
        await update.message.reply_text("Please input the list first")
        return INPUT_LIST
    attendance_list = AttendanceList.from_dict(context.chat_data["dct"])
    summary_text = attendance_list.generate_summary_text()
    await update.message.reply_text(summary_text, parse_mode="MarkdownV2")
    return ConversationHandler.END

async def change_status(update: Update, context: CustomContext) -> None:
    """Handles the attendance status of the user."""
    user = update.callback_query.from_user
    user_data = context.chat_data
    attendance_list = AttendanceList.from_dict(user_data["dct"])
    user_data["selected_id"] = update.callback_query.data
    selected_user = attendance_list.find_user_by_id(int(user_data["selected_id"]))
    user_data["dct"] = attendance_list.to_dict()
    del user_data["selected_id"]
    user_data["selected_user"] = selected_user
    logger.info("User %s selected %s with id %s", user.first_name, selected_user["name"], selected_user["id"])
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"Please select the attendance status of {selected_user['name']}",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Absent", callback_data=f"s{ABSENT}")],
                [InlineKeyboardButton("Present", callback_data=f"s{PRESENT}")],
                [InlineKeyboardButton("Last Minute Cancellation", callback_data=f"s{LAST_MINUTE_CANCELLATION}")],
            ]
        ),
    )
   
async def go_back_to_list(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    user_data = context.chat_data
    new_value = update.callback_query.data[1:]
    selected_user = user_data["selected_user"]
    del user_data["selected_user"]
    user_id = selected_user["id"]
    attendance_list = AttendanceList.from_dict(user_data["dct"])
    attendance_list.update_user_status(user_id, int(new_value))
    user_data["dct"] = attendance_list.to_dict()
    logger.info("User %s selected %s", user.first_name, new_value)
    await update.callback_query.answer()
    summary_text = attendance_list.generate_summary_text()
    inlinekeyboard = generate_inline_keyboard_list_for_edit_list(attendance_list)
    await update.callback_query.edit_message_text(summary_text + "\n\nPlease choose the handle of the person you want to edit\.",
                                    reply_markup=InlineKeyboardMarkup(inlinekeyboard),
                                    parse_mode="MarkdownV2")

async def cancel(update: Update, context: CustomContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye!", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

async def webhook_update(update: WebhookUpdate, context: CustomContext) -> None:
    """Handle custom updates."""
    chat_member = await context.bot.get_chat_member(chat_id=update.user_id, user_id=update.user_id)
    payloads = context.user_data.setdefault("payloads", [])
    payloads.append(update.payload)
    combined_payloads = "</code>\n• <code>".join(payloads)
    text = (
        f"The user {chat_member.user.mention_html()} has sent a new payload. "
        f"So far they have sent the following payloads: \n\n• <code>{combined_payloads}</code>"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text, parse_mode=ParseMode.HTML)

async def error_handler(update: object, context: CustomContext) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Finally, send the message
    await context.bot.send_message(
        chat_id=int(env_config["DEVELOPER_CHAT_ID"]), text=message, parse_mode=ParseMode.HTML
    )

async def do_nothing(update: Update, context: CustomContext) -> None:
    """Answer the callback query but do nothing."""
    await update.callback_query.answer()

async def main() -> None:
    """Set up PTB application and a web application for handling the incoming requests."""
    context_types = ContextTypes(context=CustomContext)
    # Here we set updater to None because we want our custom webhook server to handle the updates
    # and hence we don't need an Updater instance
    application = (
        Application.builder().token(TOKEN).updater(None).context_types(context_types).persistence(persistence).build()
    )

    # register handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_NEW_OR_CONTINUE: [MessageHandler(filters.Regex("^New List$"), input_list),
                                     MessageHandler(filters.Regex("^Continue List$"), edit_list)],
            INPUT_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_list)],
            EDIT_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_list),
                        CallbackQueryHandler(change_status, pattern="^\d+$"),
                        CallbackQueryHandler(do_nothing, pattern="^.$"), # this needs to be first to avoid matching the other pattern
                        CallbackQueryHandler(go_back_to_list, pattern="^(?!\d+$).+")],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("summary", summary)],
    )
    application.add_handler(conv_handler)
    application.add_handler(TypeHandler(type=WebhookUpdate, callback=webhook_update))
    application.add_error_handler(error_handler)

    # Pass webhook settings to telegram
    await application.bot.set_webhook(url=f"{URL}/telegram", allowed_updates=Update.ALL_TYPES)

    # Set up webserver
    flask_app = Flask(__name__)

    @flask_app.post("/telegram")  # type: ignore[misc]
    async def telegram() -> Response:
        """Handle incoming Telegram updates by putting them into the `update_queue`"""
        await application.update_queue.put(Update.de_json(data=request.json, bot=application.bot))
        return Response(status=HTTPStatus.OK)

    @flask_app.route("/submitpayload", methods=["GET", "POST"])  # type: ignore[misc]
    async def custom_updates() -> Response:
        """
        Handle incoming webhook updates by also putting them into the `update_queue` if
        the required parameters were passed correctly.
        """
        try:
            user_id = int(request.args["user_id"])
            payload = request.args["payload"]
        except KeyError:
            abort(
                HTTPStatus.BAD_REQUEST,
                "Please pass both `user_id` and `payload` as query parameters.",
            )
        except ValueError:
            abort(HTTPStatus.BAD_REQUEST, "The `user_id` must be a string!")

        await application.update_queue.put(WebhookUpdate(user_id=user_id, payload=payload))
        return Response(status=HTTPStatus.OK)

    @flask_app.get("/healthcheck")  # type: ignore[misc]
    async def health() -> Response:
        """For the health endpoint, reply with a simple plain text message."""
        response = make_response("The bot is still running fine :)", HTTPStatus.OK)
        response.mimetype = "text/plain"
        return response

    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=WsgiToAsgi(flask_app),
            port=int(env_config["PORT"]),
            use_colors=False,
            host=env_config["HOST"],
        )
    )

    # Run application and webserver together
    async with application:
        await application.start()
        await webserver.serve()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())