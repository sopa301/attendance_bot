import html
import json
import logging

from flask import Flask, request
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    Update,
    InlineQueryResultArticle,
    InputTextMessageContent
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

import traceback

from util.objects import AttendanceList, PollGroup, EventPoll, Status
from util import import_env
from util.db import *
from util.helper import parse_dt_to_iso, compare_time
from util.encodings import *
from util.texts import INFO_TEXT, START_TEXT, CANCEL_TEXT, POLL_GROUP_TEMPLATE, DETAILS_TEMPLATE, DATE_FORMAT_TEMPLATE, ATTENDANCE_MENU_TEXT

from api.attendance_taker import *
from api.util import CustomContext, WebhookUpdate, routes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# import env variables
env_variables = ["DEPLOYMENT_URL", "BOT_TOKEN", "MONGO_URL", "MONGO_DB_NAME",
                 "DEVELOPER_CHAT_ID"]
env_config = import_env(env_variables)

# Define configuration constants
ADMIN_CHAT_ID = int(env_config["DEVELOPER_CHAT_ID"])
context_types = ContextTypes(context=CustomContext)
application = ApplicationBuilder().token(env_config["BOT_TOKEN"]).context_types(context_types).build()

async def start(update: Update, context: CustomContext) -> int:
    """Sends a message when the command /start is issued."""
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    await update.message.reply_text(START_TEXT)
    return ConversationHandler.END

async def get_info(update: Update, context: CustomContext) -> int:
    await update.message.reply_text(INFO_TEXT)
    return ConversationHandler.END

async def get_polls(update: Update, context: CustomContext) -> int:
    user = update.message.from_user
    logger.info("User %s requested to view their polls.", user.first_name)
    poll_groups = get_poll_groups_by_owner_id(user.id)
    if not poll_groups:
        await update.message.reply_text("You have no polls.")
        return ConversationHandler.END
    context.user_data["poll_groups"] = {group.id: group.to_dict() for group in poll_groups}
    inline_keyboard = []
    for group in poll_groups:
        inline_keyboard.append([InlineKeyboardButton(group.name, callback_data=group.id)])
    await update.message.reply_text("Please select a poll group to view the polls.", reply_markup=InlineKeyboardMarkup(inline_keyboard))
    return routes["SELECT_POLL_GROUP"]

async def poll_title_clicked_callback(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    logger.info("User %s clicked on a poll title.", user.first_name)
    poll_group_id = update.callback_query.data
    try:
      poll_group = PollGroup.from_dict(context.user_data["poll_groups"][poll_group_id])
    except PollGroupNotFoundError:
      await update.callback_query.edit_message_text("Poll has been deleted.")
      await update.callback_query.answer()
      return
    polls = get_event_polls(poll_group.get_poll_ids())
    response_text = poll_group.generate_overview_text(polls, True)
    keyboard = get_poll_group_inline_keyboard(poll_group.id)
    await update.callback_query.edit_message_text(response_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN_V2)
    await update.callback_query.answer()
    return ConversationHandler.END

async def create_new_poll(update: Update, context: CustomContext) -> int:
    """Sends a message when the command /new_poll is issued"""
    user = update.message.from_user
    logger.info("User %s requested to create a new poll.", user.first_name)
    await update.message.reply_text("What would you like to call this poll?\n" + POLL_GROUP_TEMPLATE)
    context.user_data["polls"] = []
    return routes["GET_POLL_NAME"]

async def get_poll_name(update: Update, context: CustomContext) -> int:
    poll_name = update.message.text
    await update.message.reply_text("Please input the number of events you want to poll for.")
    context.user_data["poll_name"] = poll_name
    return routes["GET_NUMBER_OF_EVENTS"]

async def get_number_of_events(update: Update, context: CustomContext) -> int:
    try:
        number_of_events = int(update.message.text)
        context.user_data["number_of_events"] = number_of_events
        await update.message.reply_text("Please input the details of this event")
        return routes["GET_DETAILS"]
    except ValueError:
        await update.message.reply_text("Please input a valid number.")
        return routes["GET_NUMBER_OF_EVENTS"]

async def get_details(update: Update, context: CustomContext) -> int:
    details = update.message.text
    context.user_data["details"] = details
    await update.message.reply_text("Please input the start time of the poll.\n" + DATE_FORMAT_TEMPLATE)
    return routes["GET_START_TIME"]

async def get_start_time(update: Update, context: CustomContext) -> int:
    start_time = update.message.text
    
    status = Status()
    start_dt = parse_dt_to_iso(start_time, status)
    
    if not status.status:
        await update.message.reply_text(f"Unsuccessful: {status.message}. Please input start time again")
        return routes["GET_START_TIME"]

    context.user_data["start_time"] = start_dt 
    await update.message.reply_text("Please input the end time of the poll.\n" + DATE_FORMAT_TEMPLATE)

    return routes["GET_END_TIME"]

def get_poll_group_inline_keyboard(poll_id: str) -> list:
    return [[InlineKeyboardButton("Publish Non Regular Poll", switch_inline_query=encode_publish_non_regular_poll(poll_id))],
            [InlineKeyboardButton("Publish Regular Poll", switch_inline_query=encode_publish_regular_poll(poll_id))],
            [InlineKeyboardButton("Update Results", callback_data=encode_update_poll_results(poll_id))], 
            [InlineKeyboardButton("Delete Poll", callback_data=encode_delete_poll(poll_id))]]

# TODO: handle logic to loop back for multiple events
async def get_end_time(update: Update, context: CustomContext) -> int:
    end_time = update.message.text
    status = Status()
    et = parse_dt_to_iso(end_time, status)

    if not status.status:
        await update.message.reply_text(f"Unsuccessful: {status.message}. Please input end time again")
        return routes["GET_END_TIME"]

    if compare_time(context.user_data["start_time"], et) > 0:
        await update.message.reply_text(f"Unsuccessful: end time given is before start time. Please input end time again")
        return routes["GET_END_TIME"]
    
    user_id = update.message.from_user.id
    st = context.user_data["start_time"]
    details = context.user_data["details"]
    poll = EventPoll(st, et, details, [12, 12])
    context.user_data["polls"].append(poll.to_dict())

    # Repeat the poll
    context.user_data["number_of_events"] -= 1
    num_events = context.user_data["number_of_events"]
    
    if num_events > 0:
        await update.message.reply_text("Please input the details of the next event.")
        return routes["GET_DETAILS"]

    polls_jsons = context.user_data["polls"]
    polls_ids = insert_event_polls_dicts(polls_jsons)
    poll_group = PollGroup(user_id, context.user_data["poll_name"])
    poll_group.insert_poll_ids(polls_ids)
    poll_group_id = insert_poll_group(poll_group)
    update_poll_group_id(polls_ids, poll_group_id)

    inline_keyboard = get_poll_group_inline_keyboard(poll_group_id)
    await update.message.reply_text("Poll created.")
    await update.message.reply_text("Please click the button below to send the poll to another chat.",
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard))
    del context.user_data["details"]
    del context.user_data["start_time"]
    del context.user_data["poll_name"]
    del context.user_data["number_of_events"]
    del context.user_data["polls"]
    return ConversationHandler.END

def generate_voting_buttons(polls: list, poll_type: str) -> list:
    keyboard = []
    for i, poll in enumerate(polls):
        keyboard.append([InlineKeyboardButton(f"{poll.get_title()}",
                                              callback_data=encode_poll_voting(poll.id, poll_type, i))])
    return keyboard

async def forward_poll(update: Update, context: CustomContext) -> None:
    query = update.inline_query.query
    poll_group_id, poll_type = decode_publish_poll_query(query)

    try:
      poll_group = get_poll_group(poll_group_id)
      polls = get_event_polls(poll_group.get_poll_ids())
    except PollGroupNotFoundError or PollNotFoundError:
      # TODO: handle this better
      await update.inline_query.answer([])
      return

    reply_markup = InlineKeyboardMarkup(generate_voting_buttons(polls, poll_type))
    polls = get_event_polls(poll_group.get_poll_ids())
    poll_body = poll_group.generate_poll_group_text(polls, poll_type)
    results = []
    results.append(
        InlineQueryResultArticle(
            id=poll_group_id,
            title=poll_group.name,
            input_message_content=InputTextMessageContent(
                poll_body,
            ),
            reply_markup=reply_markup, 
        )
    )
    await update.inline_query.answer(results)

def toggle_person_in_event(poll_id: str, poll: EventPoll, username: str, poll_type: str) -> None:
    if poll_type == "nr":
        field = "non_regulars"
    elif poll_type == "r":
        field = "regulars"
    else:
        raise ValueError("Invalid poll type: " + poll_type)
    if username in poll.non_regulars or username in poll.regulars:
        remove_person_from_event_poll(poll_id, username, field)
    else:
        add_person_to_event_poll(poll_id, username, field)

async def handle_poll_voting_callback(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    query = update.callback_query.data
    poll_id, poll_type, _ = decode_poll_voting_callback(query)
    username = f"@{user.username}"
    try:
      poll = get_event_poll(poll_id)
      toggle_person_in_event(poll_id, poll, username, poll_type)
    except PollNotFoundError:
      await update.callback_query.edit_message_text("Poll has closed.")
      await update.callback_query.answer()
      return
    poll_group = get_poll_group(poll.poll_group_id)
    polls = get_event_polls(poll_group.get_poll_ids())
    poll_body = poll_group.generate_poll_group_text(polls, poll_type)

    polls = get_event_polls(poll_group.get_poll_ids())
    reply_markup = InlineKeyboardMarkup(generate_voting_buttons(polls, poll_type))
    await update.callback_query.edit_message_text(poll_body, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    logger.info("User %s responded to the poll.", user.username)
    await update.callback_query.answer()

async def handle_update_results_callback(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    old_text = update.callback_query.message.text
    logger.info("User %s requested the latest results of the poll.", user.username)
    data = update.callback_query.data
    poll_id = decode_update_poll_results_callback(data)
    try:
      poll_group = get_poll_group(poll_id)
      polls = get_event_polls(poll_group.get_poll_ids())
    except PollGroupNotFoundError or PollNotFoundError:
      await update.callback_query.edit_message_text("Poll has been deleted.")
      await update.callback_query.answer()
      return
    combined_text = poll_group.generate_overview_text(polls, True)
    # TODO: find a better way to check for no changes
    if old_text.strip("\n ") != combined_text.strip("\n "):
      await update.callback_query.edit_message_text(combined_text, reply_markup=update.callback_query.message.reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    await update.callback_query.answer()

async def handle_delete_poll_callback(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    logger.info("User %s requested to delete the poll.", user.username)
    # TODO: add confirmation step
    data = update.callback_query.data
    poll_group_id = decode_delete_poll_callback(data)
    try:
      delete_poll_group(poll_group_id)
      await update.callback_query.edit_message_text("Poll deleted.")
    except PollGroupNotFoundError:
      await update.callback_query.edit_message_text("Poll has been deleted.")
    finally:
      await update.callback_query.answer()

async def attendance(update: Update, context: CustomContext) -> int:
    await update.message.reply_text(ATTENDANCE_MENU_TEXT)
    logger.info("User %s requested to manage attendance.", update.message.from_user.first_name)
    return routes["SELECT_NEW_OR_CONTINUE"]

async def cancel(update: Update, context: CustomContext) -> int:
    """Ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(CANCEL_TEXT, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

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
    )
    message2 = (
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Finally, send the message
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID, text=message, parse_mode=ParseMode.HTML
    )
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID, text=message2, parse_mode=ParseMode.HTML
    )

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

# register handlers
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start),
                  CommandHandler("new_poll", create_new_poll),
                  CommandHandler("info", get_info), CommandHandler("polls", get_polls)],
    states={
        routes["GET_NUMBER_OF_EVENTS"]: [MessageHandler(filters.Regex("^\d+$") & ~filters.COMMAND, get_number_of_events)],
        routes["GET_DETAILS"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_details)],
        routes["GET_START_TIME"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_start_time)],
        routes["GET_END_TIME"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_end_time)],
        routes["SELECT_POLL_GROUP"]: [CallbackQueryHandler(poll_title_clicked_callback, pattern="^.+$")],
        routes["GET_POLL_NAME"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_poll_name)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

attendance_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("attendance", attendance), CommandHandler("summary", summary)],
    states={
        routes["SELECT_NEW_OR_CONTINUE"]: [CommandHandler("new_list", request_attendance_list),
                                           CommandHandler("view_lists", get_lists),
                                           CommandHandler("import_from_poll", import_from_poll)],
        routes["MANAGE_ATTENDANCE_LIST"]: [CallbackQueryHandler(handle_manage_attendance_list, pattern=MANAGE_ATTENDANCE_LIST_REGEX_STRING)],
        routes["RECEIVE_INPUT_LIST"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_inputted_attendance_list)],
        routes["VIEW_LIST"]: [CallbackQueryHandler(handle_view_attendance_list, pattern=VIEW_ATTENDANCE_LISTS_REGEX_STRING)],
        routes["INPUT_LIST"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_attendance_list)],
        routes["RECEIVE_EDITED_LIST"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_edited_attendance_list)],
        routes["SELECT_POLL_GROUP"]: [CallbackQueryHandler(handle_select_poll_group)],
        routes["SELECT_POLL"]: [CallbackQueryHandler(handle_select_poll)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Always-active request handlers
application.add_handler(InlineQueryHandler(forward_poll))
application.add_handler(CallbackQueryHandler(handle_poll_voting_callback, pattern=POLL_VOTING_REGEX_STRING))
application.add_handler(CallbackQueryHandler(handle_update_results_callback, pattern=UPDATE_POLL_RESULTS_REGEX_STRING))
application.add_handler(CallbackQueryHandler(handle_delete_poll_callback, pattern=DELETE_POLL_REGEX_STRING))
application.add_handler(CallbackQueryHandler(handle_view_attendance_summary, pattern=VIEW_SUMMARY_REGEX_STRING))
application.add_handler(CallbackQueryHandler(change_status, pattern=MARK_ATTENDANCE_REGEX_STRING))
application.add_handler(CallbackQueryHandler(do_nothing, pattern="^.$"))

# Transient conversation handler 
application.add_handler(conv_handler)
application.add_handler(attendance_conv_handler)


# Misc handlers
application.add_handler(TypeHandler(type=WebhookUpdate, callback=webhook_update))
application.add_error_handler(error_handler)

@app.route('/', methods=['POST'])
async def webhook():
    if request.headers.get('content-type') == 'application/json':
        async with application:
            update = Update.de_json(request.get_json(force=True),application.bot)
            await application.process_update(update)
            return ('', 204)
    else:
        return ('Bad request', 400)