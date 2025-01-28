from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup, Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    ConversationHandler,
)
import logging

from util.objects import AttendanceList
from util.texts import (
  ABSENT,
  PRESENT,
  LAST_MINUTE_CANCELLATION,
  REQUEST_FOR_ATTENDANCE_LIST_INPUT_TEXT,
  ABSENT_SYMBOL,
  PRESENT_SYMBOL,
  CANCELLATION_SYMBOL,
  status_map
)
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
        inlinekeyboard.append([InlineKeyboardButton(attendance_list.get_title(),
                                                    callback_data=encode_view_attendance_list(attendance_list.id))])
    return inlinekeyboard

def generate_inline_keyboard_for_attendance_summaries(attendance_lists: list) -> list:
    inlinekeyboard = []
    for attendance_list in attendance_lists:
        inlinekeyboard.append([InlineKeyboardButton(attendance_list.get_title(),
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
    await update.message.reply_text("Please select the attendance list you want to edit.", reply_markup=InlineKeyboardMarkup(inlinekeyboard))
    return routes["VIEW_LIST"]

async def import_from_poll(update: Update, context: CustomContext) -> int:
    """Imports the attendance list from a poll."""
    user = update.message.from_user
    logger.info("User %s requested to import from a poll.", user.first_name)
    keyboard = []
    poll_groups = get_poll_groups_by_owner_id(user.id)
    if len(poll_groups) == 0:
        await update.message.reply_text("You have no poll group yet.")
        return ConversationHandler.END
    for poll_group in poll_groups:
        keyboard.append([InlineKeyboardButton(poll_group.name, callback_data=poll_group.id)])
    await update.message.reply_text("Please select the poll group you want to import from.", reply_markup=InlineKeyboardMarkup(keyboard))
    return routes["SELECT_POLL_GROUP"]

async def handle_select_poll_group(update: Update, context: CustomContext) -> int:
    poll_group_id = update.callback_query.data
    try:
      poll_group = get_poll_group(poll_group_id)
      polls = get_event_polls(poll_group.get_poll_ids())
    except PollGroupNotFoundError:
      await update.callback_query.answer()
      await update.callback_query.edit_message_text("Poll group not found.")
      return ConversationHandler.END
    keyboard = []
    for poll in polls:
        keyboard.append([InlineKeyboardButton(poll.get_title(), callback_data=poll.id)])
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Please select the poll you want to import from.", reply_markup=InlineKeyboardMarkup(keyboard))
    return routes["SELECT_POLL"]

async def handle_select_poll(update: Update, context: CustomContext) -> int:
    poll_id = update.callback_query.data
    try:
      poll = get_event_poll(poll_id)
    except PollNotFoundError:
      await update.callback_query.answer()
      await update.callback_query.edit_message_text("Poll not found.")
      return ConversationHandler.END
    attendance_list = AttendanceList.from_poll(poll)
    attendance_list.insert_owner_id(update.callback_query.from_user.id)
    attendance_list_id = insert_attendance_list(attendance_list)
    attendance_list.insert_id(attendance_list_id)
    ban_list = get_and_update_banned_personnel(attendance_list)
    while len(ban_list) > 0:
      attendance_list.remove_banned_people(ban_list)
      attendance_list.replenish_numbers()
      ban_list = get_and_update_banned_personnel(attendance_list)
    await edit_to_edit_list(attendance_list, update)
    return ConversationHandler.END

async def handle_view_attendance_list(update: Update, context: CustomContext) -> int:
    attendance_list_id = decode_view_attendance_list(update.callback_query.data)
    attendance_list = get_attendance_list(attendance_list_id)
    context.user_data["attendance_list"] = attendance_list.to_dict()
    await update.callback_query.answer()
    inlinekeyboard = [
        [InlineKeyboardButton("Take Attendance", callback_data=encode_manage_attendance_list("take_attendance"))],
        [InlineKeyboardButton("Edit", callback_data=encode_manage_attendance_list("edit"))],
        [InlineKeyboardButton("Delete", callback_data=encode_manage_attendance_list("delete"))],
        [InlineKeyboardButton("Log and Delete", callback_data=encode_manage_attendance_list("log_and_delete"))]
    ]
    await update.callback_query.edit_message_text(f"Currently managing {attendance_list.get_title()}. What would you like to do?", reply_markup=InlineKeyboardMarkup(inlinekeyboard))
    return routes["MANAGE_ATTENDANCE_LIST"]

async def handle_manage_attendance_list(update: Update, context: CustomContext) -> int:
    attendance_list = AttendanceList.from_dict(context.user_data["attendance_list"])
    command = decode_manage_attendance_list(update.callback_query.data)
    if command == "take_attendance":
      await edit_to_edit_list(attendance_list, update)
      return ConversationHandler.END
    elif command == "edit":
        await update.callback_query.edit_message_text("Please copy and edit the list, then send it to me.")
        await update.callback_query.message.reply_text(attendance_list.to_parsable_list())
        return routes["RECEIVE_EDITED_LIST"]
    elif command == "delete":
        delete_attendance_list(attendance_list.id)
        await update.callback_query.edit_message_text("Attendance list deleted.")
        return ConversationHandler.END
    elif command == "log_and_delete":
        log_attendance_list(attendance_list)
        delete_attendance_list(attendance_list.id)
        await update.callback_query.edit_message_text("Attendance list logged and deleted.")
        return ConversationHandler.END
    else:
        raise ValueError("Invalid command: " + command)

async def process_edited_attendance_list(update: Update, context: CustomContext) -> int:
    message_text = update.message.text
    try:
      attendance_list = AttendanceList.parse_list(message_text)
      old_list = AttendanceList.from_dict(context.user_data["attendance_list"])
      attendance_list.update_administrative_details(old_list)
    except Exception as e:
      await update.message.reply_text("Invalid list format. Please input the list again.")
      logger.info(e)
      return routes["RECEIVE_EDITED_LIST"]
    update_attendance_list_full(attendance_list.id, attendance_list)
    await display_edit_list(attendance_list, update)
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
    await display_edit_list(attendance_list, update)
    return ConversationHandler.END

async def display_edit_list(attendance_list: AttendanceList, update: Update) -> None:
    await base_edit_list(attendance_list, update.message.reply_text)

async def edit_to_edit_list(attendance_list, update) -> None:
    await base_edit_list(attendance_list, update.callback_query.edit_message_text)
    
async def base_edit_list(attendance_list, fn) -> int:
    summary_text = attendance_list.generate_summary_text()
    inlinekeyboard = generate_inline_keyboard_list_for_edit_list(attendance_list)
    await fn(summary_text + "\n\nPlease edit using the buttons below\.",
             reply_markup=InlineKeyboardMarkup(inlinekeyboard),
             parse_mode="MarkdownV2")

def generate_inline_keyboard_list_for_edit_list(attendance_list: AttendanceList) -> list:
    inlinekeyboard = []
    lists = [attendance_list.non_regulars, attendance_list.regulars, attendance_list.standins]
    titles = ["NON REGULARS", "REGULARS", "STANDINS"]
    for index, lst in enumerate(lists):
        if len(lst) > 0:
          inlinekeyboard.append([InlineKeyboardButton(titles[index], callback_data=DO_NOTHING)])
        for index, person in enumerate(lst):
            inlinekeyboard.append([InlineKeyboardButton(f"{index+1}. {status_map[person.status]} {person.name}", callback_data=DO_NOTHING)])
            inline_list = [
                InlineKeyboardButton(PRESENT_SYMBOL, callback_data=encode_mark_attendance(person.id, attendance_list.id, PRESENT)),
                InlineKeyboardButton(ABSENT_SYMBOL, callback_data=encode_mark_attendance(person.id, attendance_list.id, ABSENT)),
                InlineKeyboardButton(CANCELLATION_SYMBOL, callback_data=encode_mark_attendance(person.id, attendance_list.id, LAST_MINUTE_CANCELLATION))
            ]
            inlinekeyboard.append(inline_list)
    return inlinekeyboard

async def summary(update: Update, context: CustomContext) -> int:
    """Prints the attendance summary"""
    logger.info("User requested for the summary.")
    attendance_lists = get_attendance_lists_by_owner_id(update.message.from_user.id)
    if len(attendance_lists) == 0:
        await update.message.reply_text("You have no attendance list yet.")
        return ConversationHandler.END
    keyboard = generate_inline_keyboard_for_attendance_summaries(attendance_lists)
    await update.message.reply_text("Please select the attendance list you want to view the summary of.", reply_markup=InlineKeyboardMarkup(keyboard))
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
    user_id, attendance_list_id, new_status = decode_mark_attendance(update.callback_query.data)
    attendance_list = get_attendance_list(attendance_list_id)
    selected_user = attendance_list.find_user_by_id(user_id)
    if selected_user.status == new_status:
        await update.callback_query.answer()
        return ConversationHandler.END
    attendance_list.update_user_status(user_id, new_status)
    update_attendance_list(attendance_list.id, attendance_list, user_id, new_status)
    logger.info("User %s selected %s with id %s, set to %s", user.first_name, selected_user.name, selected_user.id, selected_user.status)
    await update.callback_query.answer()
    await edit_to_edit_list(attendance_list, update)
    return ConversationHandler.END

async def do_nothing(update: Update, context: CustomContext) -> None:
    """Answer the callback query but do nothing."""
    await update.callback_query.answer()

