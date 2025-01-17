from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup, Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    ConversationHandler,
)
import logging

from util.objects import AttendanceList
from util.texts import ABSENT, PRESENT, LAST_MINUTE_CANCELLATION, REQUEST_FOR_ATTENDANCE_LIST_INPUT

from api.util import CustomContext, routes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def input_list(update: Update, context: CustomContext) -> int:
    message_text = update.message.text
    if (message_text == "New List"):
        if "dct" in context.user_data:
            del context.user_data["dct"]
        await update.message.reply_text(REQUEST_FOR_ATTENDANCE_LIST_INPUT, reply_markup=ReplyKeyboardRemove())
        return routes["INPUT_LIST"]
    try:
      attendance_list = AttendanceList.parse_list(message_text)
      context.user_data["dct"] = attendance_list.to_dict()
    except Exception as e:
      await update.message.reply_text("Invalid list format. Please input the list again.")
      logger.info(e)
      return routes["INPUT_LIST"]
    await display_edit_list(AttendanceList.from_dict(context.user_data["dct"]), update)
    return routes["EDIT_LIST"]

async def edit_list(update: Update, context: CustomContext) -> int:
    """Allows the user to make edits to the list."""
    user = update.message.from_user
    logger.info("Displaying list for %s", user.first_name)
    if ("dct" not in context.user_data):
        await update.message.reply_text("You have no list yet. Please input the list first.")
        await update.message.reply_text(REQUEST_FOR_ATTENDANCE_LIST_INPUT, reply_markup=ReplyKeyboardRemove())
        return routes["INPUT_LIST"]
    await display_edit_list(AttendanceList.from_dict(context.user_data["dct"]), update)
    return ConversationHandler.END

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
    if ("dct" not in context.user_data):
        await update.message.reply_text("Please input the list first")
        return routes["INPUT_LIST"]
    attendance_list = AttendanceList.from_dict(context.user_data["dct"])
    summary_text = attendance_list.generate_summary_text()
    await update.message.reply_text(summary_text, parse_mode="MarkdownV2")
    return ConversationHandler.END

async def change_status(update: Update, context: CustomContext) -> None:
    """Handles the attendance status of the user."""
    user = update.callback_query.from_user
    user_data = context.user_data
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
    return routes["SETTING_STATUS"]
    
async def setting_user_status(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    user_data = context.user_data
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
    return routes["EDIT_LIST"]

async def do_nothing(update: Update, context: CustomContext) -> None:
    """Answer the callback query but do nothing."""
    await update.callback_query.answer()

