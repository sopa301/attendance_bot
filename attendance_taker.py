#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
First, a few callback functions are defined. Then, those functions are passed to
the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.

Usage:
Example of a bot-user conversation using ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from dotenv import dotenv_values
from enum import Enum

# CONSTANTS
class AttendanceStatus(Enum):
    ABSENT = 0
    PRESENT = 1
    LAST_MINUTE_CANCELLATION = 2

PRESENT_SYMBOL = "✅"
ABSENT_SYMBOL = "❌"

def generate_status_string(status: AttendanceStatus, name: str, index: int) -> str:
    if status == AttendanceStatus.ABSENT:
        return generate_absent_string(name, index)
    elif status == AttendanceStatus.PRESENT:
        return generate_present_string(name, index)
    elif status == AttendanceStatus.LAST_MINUTE_CANCELLATION:
        return generate_last_minute_cancellation_string(name, index)
    else:
        raise ValueError("Invalid status")

def generate_absent_string(absentee: str, index: int) -> str:
    return f"{index}\. {ABSENT_SYMBOL}{absentee}"

def generate_present_string(presentee: str, index: int) -> str:
    return f"{index}\. {PRESENT_SYMBOL}{presentee}"

def generate_last_minute_cancellation_string(cancellation: str, index: int) -> str:
    return f"~{index}\. {cancellation}~"


# import token
config = dotenv_values(".env")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

ATTENDANCE, INPUT_LIST, SUMMARY = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and asks the user about their gender."""
    # reply_keyboard = [["Boy", "Girl", "Other"]]

    await update.message.reply_text(
        "Hi! Please send the list. "
    )

    return INPUT_LIST

async def input_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Parses the list and shows the parsed list."""
    user = update.message.from_user
    message_text = update.message.text
    try:
      dct = parse_list(message_text)
    except:
      await update.message.reply_text("Invalid list format. Please input the list again.")
      return INPUT_LIST
    context.user_data["dct"] = dct
    logger.info("Displaying list for %s", user.first_name)

    summary_text = generate_summary_text(context.user_data["dct"])
    inlinekeyboard = [[InlineKeyboardButton(s["name"], callback_data=s["name"])] for s in context.user_data["dct"]["non_regulars"]]
    inlinekeyboard.extend(list([InlineKeyboardButton(s["name"], callback_data=s["name"])] for s in context.user_data["dct"]["regulars"]))
    await update.message.reply_text(summary_text + "\n\nPlease choose the handle of the person you want to edit\.",
                                    reply_markup=InlineKeyboardMarkup(inlinekeyboard),
                                    parse_mode="MarkdownV2")
    return INPUT_LIST

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
    dct["non_regulars"] = list({"name": s[s.index('.')+1:].strip(), "status": AttendanceStatus.ABSENT.value} for s in lines[lines.index("Non regulars")+1:lines.index("Regulars")-1])
    dct["regulars"] = list({"name": s[s.index('.')+1:].strip(), "status": AttendanceStatus.ABSENT.value} for s in lines[lines.index("Regulars")+1:lines.index("Exco")-1])
    dct["exco"] = lines[lines.index("Exco")+1:]
    return dct

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prints the attendance summary"""
    logger.info("User requested for the summary.")
    if ("dct" not in context.user_data):
        await update.message.reply_text("Please input the list first")
        return INPUT_LIST
    summary_text = generate_summary_text(context.user_data["dct"])
    await update.message.reply_text(summary_text, parse_mode="MarkdownV2")
    return ConversationHandler.END

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
      output_list.append(generate_status_string(AttendanceStatus(tp["status"]), tp["name"], i+1))

    output_list.append("")

    output_list.append("Regulars")
    for i, tp in enumerate(dct["regulars"]):
      output_list.append(generate_status_string(AttendanceStatus(tp["status"]), tp["name"], i+1))

    return "\n".join(output_list)

async def gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the selected gender and asks for a photo."""
    user = update.message.from_user
    logger.info("Gender of %s: %s", user.first_name, update.message.text)
    await update.message.reply_text(
        "I see! Please send me a photo of yourself, "
        "so I know what you look like, or send /skip if you don't want to.",
        reply_markup=ReplyKeyboardRemove(),
    )

    return PHOTO


async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the photo and asks for a location."""
    user = update.message.from_user
    photo_file = await update.message.photo[-1].get_file()
    await photo_file.download_to_drive("user_photo.jpg")
    logger.info("Photo of %s: %s", user.first_name, "user_photo.jpg")
    await update.message.reply_text(
        "Gorgeous! Now, send me your location please, or send /skip if you don't want to."
    )

    return LOCATION


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skips the photo and asks for a location."""
    user = update.message.from_user
    logger.info("User %s did not send a photo.", user.first_name)
    await update.message.reply_text(
        "I bet you look great! Now, send me your location please, or send /skip."
    )

    return LOCATION


async def location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the location and asks for some info about the user."""
    user = update.message.from_user
    user_location = update.message.location
    logger.info(
        "Location of %s: %f / %f", user.first_name, user_location.latitude, user_location.longitude
    )
    await update.message.reply_text(
        "Maybe I can visit you sometime! At last, tell me something about yourself."
    )

    return BIO


async def skip_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skips the location and asks for info about the user."""
    user = update.message.from_user
    logger.info("User %s did not send a location.", user.first_name)
    await update.message.reply_text(
        "You seem a bit paranoid! At last, tell me something about yourself."
    )

    return BIO


async def bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the info about the user and ends the conversation."""
    user = update.message.from_user
    logger.info("Bio of %s: %s", user.first_name, update.message.text)
    await update.message.reply_text("Thank you! I hope we can talk again some day.")

    return ConversationHandler.END


async def change_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the attendance status of the user."""
    user = update.callback_query.from_user
    user_data = context.user_data
    user_data["selected_user"] = update.callback_query.data
    logger.info("User %s selected %s", user.first_name, user_data["selected_user"])
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"Please select the attendance status of {user_data['selected_user']}",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("Absent", callback_data=AttendanceStatus.ABSENT.value)],
                [InlineKeyboardButton("Present", callback_data=AttendanceStatus.PRESENT.value)],
                [InlineKeyboardButton("Last Minute Cancellation", callback_data=AttendanceStatus.LAST_MINUTE_CANCELLATION.value)],
            ]
        ),
    )
    
def update_status(dct: dict, new_value: int, username: str) -> None:
    for i, person in enumerate(dct["non_regulars"]):
        if person["name"] == username:
            dct["non_regulars"][i]["status"] = AttendanceStatus(int(new_value))
            return
    for i, person in enumerate(dct["regulars"]):
        if person["name"] == username:
            dct["regulars"][i]["status"] = AttendanceStatus(int(new_value))
            return
    raise ValueError("Invalid username")
    

async def go_back_to_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.callback_query.from_user
    user_data = context.user_data
    new_value = update.callback_query.data
    update_status(user_data["dct"], new_value, user_data["selected_user"])
    logger.info("User %s selected %s", user.first_name, new_value)
    await update.callback_query.answer()
    summary_text = generate_summary_text(context.user_data["dct"])
    inlinekeyboard = [[InlineKeyboardButton(s["name"], callback_data=s["name"])] for s in context.user_data["dct"]["non_regulars"]]
    inlinekeyboard.extend(list([InlineKeyboardButton(s["name"], callback_data=s["name"])] for s in context.user_data["dct"]["regulars"]))
    await update.callback_query.edit_message_text(summary_text + "\n\nPlease choose the handle of the person you want to edit\.",
                                    reply_markup=InlineKeyboardMarkup(inlinekeyboard),
                                    parse_mode="MarkdownV2")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye! I hope we can talk again some day.", reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(config["BOT_TOKEN"]).build()

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            # SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, summary)],
            # ATTENDANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, attendance)],
            # GENDER: [MessageHandler(filters.Regex("^(Boy|Girl|Other)$"), gender)],
            # PHOTO: [MessageHandler(filters.PHOTO, photo), CommandHandler("skip", skip_photo)],
            # LOCATION: [
            #     MessageHandler(filters.LOCATION, location),
            #     CommandHandler("skip", skip_location),
            # ],
            # BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, bio)],
            INPUT_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_list),
                         CallbackQueryHandler(change_status, pattern="^(?!\d+$).+"),
                         CallbackQueryHandler(go_back_to_list, pattern="^\d+$")],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("summary", summary)],
    )

    application.add_handler(conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()