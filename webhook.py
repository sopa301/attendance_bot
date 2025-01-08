#!/usr/bin/env python
# This program is dedicated to the public domain under the CC0 license.
# pylint: disable=import-error,unused-argument
"""
Simple example of a bot that uses a custom webhook setup and handles custom updates.
For the custom webhook setup, the libraries `flask`, `asgiref` and `uvicorn` are used. Please
install them as `pip install flask[async]~=2.3.2 uvicorn~=0.23.2 asgiref~=3.7.2`.
Note that any other `asyncio` based web server framework can be used for a custom webhook setup
just as well.

Usage:
Set bot Token, URL, admin CHAT_ID and PORT after the imports.
You may also need to change the `listen` value in the uvicorn configuration to match your setup.
Press Ctrl-C on the command line or send a signal to the process to stop the bot.
"""
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

from dotenv import dotenv_values
import os
from enum import Enum
import traceback

from mongopersistence import MongoPersistence

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# import env variables
env_variables = ["DEPLOYMENT_URL", "BOT_TOKEN", "MONGO_URL", "MONGO_DB_NAME", "MONGO_USER_DATA_COLLECTION_NAME", "PORT", "HOST", "DEVELOPER_CHAT_ID"]
def import_env(variables: list):
    # assume either all or none of the variables are present (because we either load all or none of them)
    all_present = all(var in os.environ for var in variables)
    if all_present:
        return {var: os.environ[var] for var in variables}
    else:
        return dotenv_values(".env")
env_config = import_env(env_variables)

# Define configuration constants
URL = env_config["DEPLOYMENT_URL"] 
ADMIN_CHAT_ID = int(env_config["DEVELOPER_CHAT_ID"])
TOKEN = env_config["BOT_TOKEN"]  # nosec B105

persistence = MongoPersistence(
    mongo_url=env_config["MONGO_URL"],
    db_name=env_config["MONGO_DB_NAME"],
    name_col_user_data=env_config["MONGO_USER_DATA_COLLECTION_NAME"],  # optional
    ignore_general_data=["cache"],
    ignore_user_data=["foo", "bar"],
    load_on_flush=False,
)

# CONSTANTS
SELECT_NEW_OR_CONTINUE, INPUT_LIST, EDIT_LIST, SUMMARY = range(4)
ABSENT, PRESENT, LAST_MINUTE_CANCELLATION = range(3)

PRESENT_SYMBOL = "✅"
ABSENT_SYMBOL = "❌"

def generate_status_string(status: int, name: str, index: int) -> str:
    if status == ABSENT:
        return generate_absent_string(name, index)
    elif status == PRESENT:
        return generate_present_string(name, index)
    elif status == LAST_MINUTE_CANCELLATION:
        return generate_last_minute_cancellation_string(name, index)
    else:
        raise ValueError("Invalid status")

def generate_absent_string(absentee: str, index: int) -> str:
    return f"{index}\. {ABSENT_SYMBOL}{absentee}"

def generate_present_string(presentee: str, index: int) -> str:
    return f"{index}\. {PRESENT_SYMBOL}{presentee}"

def generate_last_minute_cancellation_string(cancellation: str, index: int) -> str:
    return f"~{index}\. {cancellation}~"

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

def parse_list(message_text: str) -> dict:
    """
    Parses the list in this format: 
    Pickleball session (date)

    Non regulars
    1. ...
    2. ...

    Regulars
    1. ...
    2. ...

    Exco
    (Name)
    """
    lines = message_text.split("\n")
    dct = {}
    dct["session_info"] = lines[0]
    dct["non_regulars"] = list({"name": s[s.index('.')+1:].strip(), "status": ABSENT} for s in lines[lines.index("Non regulars")+1:lines.index("Regulars")-1])
    dct["regulars"] = list({"name": s[s.index('.')+1:].strip(), "status": ABSENT} for s in lines[lines.index("Regulars")+1:lines.index("Exco")-1])
    dct["exco"] = lines[lines.index("Exco")+1:]
    return dct

def generate_summary_text(dct: dict) -> str:
    """
    Generates the attendance summary in this format:
    Pickleball session (date)

    Non regulars
    1. ...
    2. ...

    Regulars
    1. ...
    2. ...
    """
    output_list = [dct["session_info"], ""]

    output_list.append("Non regulars")
    for i, tp in enumerate(dct["non_regulars"]):
      output_list.append(generate_status_string(tp["status"], tp["name"], i+1))

    output_list.append("")

    output_list.append("Regulars")
    for i, tp in enumerate(dct["regulars"]):
      output_list.append(generate_status_string(tp["status"], tp["name"], i+1))

    return "\n".join(output_list)

async def start(update: Update, context: CustomContext) -> int:
    text = "Hi!"
    reply_keyboard = [["New List"]]
    if "dct" in context.user_data:
        reply_keyboard[0].append("Continue List")
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return SELECT_NEW_OR_CONTINUE

async def input_list(update: Update, context: CustomContext) -> int:
    message_text = update.message.text
    if (message_text == "New List"):
        if "dct" in context.user_data:
            del context.user_data["dct"]
        await update.message.reply_text("Please input the list in the following format (note that no special characters other than '@' are allowed): \n\nPickleball session (date)\n\nNon regulars\n1. ...\n2. ...\n\nRegulars\n1. ...\n2. ...\n\nExco\n(Name)",
                                        reply_markup=ReplyKeyboardRemove())
        return INPUT_LIST
    try:
      dct = parse_list(message_text)
      context.user_data["dct"] = dct
    except:
      await update.message.reply_text("Invalid list format. Please input the list again.")
      return INPUT_LIST
    summary_text = generate_summary_text(context.user_data["dct"])
    inlinekeyboard = generate_inline_keyboard_list_for_edit_list(context.user_data["dct"])
    await update.message.reply_text(summary_text + "\n\nPlease choose the handle of the person you want to edit\.",
                                    reply_markup=InlineKeyboardMarkup(inlinekeyboard),
                                    parse_mode="MarkdownV2")
    return EDIT_LIST

async def edit_list(update: Update, context: CustomContext) -> int:
    """Allows the user to make edits to the list."""
    user = update.message.from_user
    logger.info("Displaying list for %s", user.first_name)
    if ("dct" not in context.user_data):
        await update.message.reply_text("You have no list yet. Please input the list first.")
        await update.message.reply_text("Please input the list in the following format (note that no special characters other than '@' are allowed): \n\nPickleball session (date)\n\nNon regulars\n1. ...\n2. ...\n\nRegulars\n1. ...\n2. ...\n\nExco\n(Name)",
                                        reply_markup=ReplyKeyboardRemove())
        return INPUT_LIST

    summary_text = generate_summary_text(context.user_data["dct"])
    inlinekeyboard = generate_inline_keyboard_list_for_edit_list(context.user_data["dct"])
    await update.message.reply_text(summary_text + "\n\nPlease choose the handle of the person you want to edit\.",
                                    reply_markup=InlineKeyboardMarkup(inlinekeyboard),
                                    parse_mode="MarkdownV2")
    return EDIT_LIST

def generate_inline_keyboard_list_for_edit_list(dct: dict) -> list:
    inlinekeyboard = []
    for index, person in enumerate(dct["non_regulars"]):
        callback_data = ",".join(["nr", str(index), person["name"]])
        inlinekeyboard.append([InlineKeyboardButton(person["name"], callback_data=callback_data)])
    for index, person in enumerate(dct["regulars"]):
        callback_data = ",".join(["r", str(index), person["name"]])
        inlinekeyboard.append([InlineKeyboardButton(person["name"], callback_data=callback_data)])
    return inlinekeyboard
    

async def summary(update: Update, context: CustomContext) -> int:
    """Prints the attendance summary"""
    logger.info("User requested for the summary.")
    if ("dct" not in context.user_data):
        await update.message.reply_text("Please input the list first")
        return INPUT_LIST
    summary_text = generate_summary_text(context.user_data["dct"])
    await update.message.reply_text(summary_text, parse_mode="MarkdownV2")
    return ConversationHandler.END

async def change_status(update: Update, context: CustomContext) -> None:
    """Handles the attendance status of the user."""
    user = update.callback_query.from_user
    user_data = context.user_data
    # in the format of "user_regular_status,user_index,username"
    user_data["selected_user"] = update.callback_query.data
    logger.info("User %s selected %s", user.first_name, user_data["selected_user"])
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"Please select the attendance status of {user_data['selected_user'].split(',')[2]}",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Absent", callback_data=ABSENT)],
                [InlineKeyboardButton("Present", callback_data=PRESENT)],
                [InlineKeyboardButton("Last Minute Cancellation", callback_data=LAST_MINUTE_CANCELLATION)],
            ]
        ),
    )
    
def update_status(dct: dict, new_value: int, user_regular_status: str, user_index: int, username: str) -> None:
    if user_regular_status == "nr" and dct["non_regulars"][user_index]["name"] == username:
        dct["non_regulars"][user_index]["status"] = new_value
    elif user_regular_status == "r" and dct["regulars"][user_index]["name"] == username:
        dct["regulars"][user_index]["status"] = new_value
    else:
        raise ValueError("Username, index, status combination not found. Query string: " + user_regular_status + ", " + str(user_index) + ", " + username)
    
async def go_back_to_list(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    user_data = context.user_data
    new_value = update.callback_query.data
    user_status, user_index, username = user_data["selected_user"].split(",")
    update_status(user_data["dct"], int(new_value), user_status, int(user_index), username)
    logger.info("User %s selected %s", user.first_name, new_value)
    await update.callback_query.answer()
    summary_text = generate_summary_text(context.user_data["dct"])
    inlinekeyboard = generate_inline_keyboard_list_for_edit_list(context.user_data["dct"])
    await update.callback_query.edit_message_text(summary_text + "\n\nPlease choose the handle of the person you want to edit\.",
                                    reply_markup=InlineKeyboardMarkup(inlinekeyboard),
                                    parse_mode="MarkdownV2")


async def cancel(update: Update, context: CustomContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
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
                        CallbackQueryHandler(change_status, pattern="^(?!\d+$).+"),
                        CallbackQueryHandler(go_back_to_list, pattern="^\d+$")],
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