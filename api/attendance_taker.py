from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup, Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    ConversationHandler,
)
import logging

from util.objects import AttendanceList
from util.texts import ABSENT, PRESENT, LAST_MINUTE_CANCELLATION, REQUEST_FOR_ATTENDANCE_LIST_INPUT_TEXT
from util.db import *
from util.encodings import *

from api.util import CustomContext, routes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def generate_inline_keyboard_for_attendance_lists(attendance_lists: list) -> list:
    inlinekeyboard = []
    for attendance_list in attendance_lists:
        inlinekeyboard.append([InlineKeyboardButton(attendance_list.details[0],
                                                    callback_data=encode_view_attendance_list(attendance_list.id))])
    return inlinekeyboard

def generate_inline_keyboard_for_attendance_summaries(attendance_lists: list) -> list:
    inlinekeyboard = []
    for attendance_list in attendance_lists:
        inlinekeyboard.append([InlineKeyboardButton(attendance_list.details[0],
                                                    callback_data=encode_view_attendance_summary(attendance_list.id))])
    return inlinekeyboard

async def get_lists(update: Update, context: CustomContext) -> int:
    """Displays the list of attendance lists."""
    user = update.message.from_user
    logger.info("User %s requested for the list of attendance lists.", user.first_name)
    attendance_lists = get_attendance_lists_by_owner_id(user.id)
    if len(attendance_lists) == 0:
        await update.message.reply_text("You have no attendance list yet.")
        return ConversationHandler.END
    inlinekeyboard = generate_inline_keyboard_for_attendance_lists(attendance_lists)
    await update.message.reply_text("Please select the attendance list you want to edit\.", reply_markup=InlineKeyboardMarkup(inlinekeyboard))
    return routes["VIEW_LIST"]

async def handle_view_attendance_list(update: Update, context: CustomContext) -> int:
    attendance_list_id = decode_view_attendance_list(update.callback_query.data)
    attendance_list = get_attendance_list(attendance_list_id)
    await update.callback_query.answer()
    display_edit_list(attendance_list, update)
    return ConversationHandler.END

async def request_attendance_list(update: Update, context: CustomContext) -> int:
    await update.message.reply_text(REQUEST_FOR_ATTENDANCE_LIST_INPUT_TEXT, reply_markup=ReplyKeyboardRemove())
    return routes["RECEIVE_INPUT_LIST"]

async def process_inputted_attendance_list(update: Update, context: CustomContext) -> int:
    message_text = update.message.text
    try:
      attendance_list = AttendanceList.parse_list(message_text)
      attendance_list.insert_owner_id(update.message.from_user.id)
      attendance_list_id = insert_attendance_list(attendance_list)
      attendance_list.insert_id(attendance_list_id)
    except Exception as e:
      await update.message.reply_text("Invalid list format. Please input the list again.")
      logger.info(e)
      return routes["RECEIVE_INPUT_LIST"]
    display_edit_list(attendance_list, update)
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
    lists = [attendance_list.non_regulars, attendance_list.regulars, attendance_list.standins]
    titles = ["NON REGULARS", "REGULARS", "STANDINS"]
    for index, lst in enumerate(lists):
        inlinekeyboard.append([InlineKeyboardButton(titles[index], callback_data=DO_NOTHING)])
        for index, person in enumerate(lst):
            callback_data = encode_mark_attendance(callback_data, attendance_list.id)
            inlinekeyboard.append([InlineKeyboardButton(f"{index+1}. {person['name']}", callback_data=callback_data)])
    return inlinekeyboard

async def summary(update: Update, context: CustomContext) -> int:
    """Prints the attendance summary"""
    logger.info("User requested for the summary.")
    attendance_lists = get_attendance_lists_by_owner_id(update.message.from_user.id)
    if len(attendance_lists) == 0:
        await update.message.reply_text("You have no attendance list yet.")
        return ConversationHandler.END
    keyboard = generate_inline_keyboard_for_attendance_summaries(attendance_lists)
    await update.message.reply_text("Please select the attendance list you want to view the summary of\.", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END

async def handle_view_attendance_summary(update: Update, context: CustomContext) -> int:
    attendance_list_id = decode_view_attendance_summary(update.callback_query.data)
    attendance_list = get_attendance_list(attendance_list_id)
    await update.callback_query.answer()
    summary_text = attendance_list.generate_summary_text()
    await update.callback_query.edit_message_text(summary_text, parse_mode="MarkdownV2")
    return ConversationHandler.END

async def change_status(update: Update, context: CustomContext) -> None:
    """Handles the attendance status of the user."""
    user = update.callback_query.from_user
    user_data = context.user_data
    user_id, attendance_list_id = decode_mark_attendance(update.callback_query.data)
    attendance_list = get_attendance_list(attendance_list_id)
    user_data["selected_id"] = user_id
    selected_user = attendance_list.find_user_by_id(user_data["selected_id"])
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
    update_attendance_list(attendance_list)
    logger.info("User %s selected %s", user.first_name, new_value)
    await update.callback_query.answer()
    summary_text = attendance_list.generate_summary_text()
    inlinekeyboard = generate_inline_keyboard_list_for_edit_list(attendance_list)
    await update.callback_query.edit_message_text(summary_text + "\n\nPlease choose the handle of the person you want to edit\.",
                                    reply_markup=InlineKeyboardMarkup(inlinekeyboard),
                                    parse_mode="MarkdownV2")
    return ConversationHandler.END

async def do_nothing(update: Update, context: CustomContext) -> None:
    """Answer the callback query but do nothing."""
    await update.callback_query.answer()

