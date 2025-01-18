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

from util.objects import AttendanceList, PollGroup, EventPoll
from util import import_env
from util.db import *
from util.texts import INFO_TEXT

from api.attendance_taker import input_list, edit_list, setting_user_status, do_nothing, summary, change_status
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
    await update.message.reply_text(
        "Hi! I am the attendance bot. Please click:\n"
        "/new_poll to create a new weekly poll\n"
        "/attendance to start taking attendance for the upcoming event\n"
        "/polls to manage your polls\n"
        "/info to get information about this bot\n"
        "/cancel to cancel the conversation",
        )
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

def generate_poll_group_overview_text(poll_group: PollGroup) -> str:
    return "Non Regulars:\n" + generate_poll_group_text(poll_group, "nr") + "\n\nRegulars\n" + generate_poll_group_text(poll_group, "r")

async def poll_title_clicked_callback(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    logger.info("User %s clicked on a poll title.", user.first_name)
    poll_group_id = update.callback_query.data
    poll_group = PollGroup.from_dict(context.user_data["poll_groups"][poll_group_id])
    response_text = generate_poll_group_overview_text(poll_group)
    keyboard = get_poll_group_inline_keyboard(poll_group.id)
    await update.callback_query.edit_message_text(response_text, reply_markup=InlineKeyboardMarkup(keyboard))
    await update.callback_query.answer()
    return ConversationHandler.END

async def create_new_poll(update: Update, context: CustomContext) -> int:
    """Sends a message when the command /new_poll is issued"""
    user = update.message.from_user
    logger.info("User %s requested to create a new poll.", user.first_name)
    await update.message.reply_text("What would you like to call this poll?")
    context.user_data["polls"] = []
    return routes["GET_POLL_NAME"]

async def get_poll_name(update: Update, context: CustomContext) -> int:
    poll_name = update.message.text
    await update.message.reply_text("Please input the number of events you want to poll for.")
    context.user_data["poll_name"] = poll_name
    return routes["GET_NUMBER_OF_EVENTS"]

# currently, the thing only accepts one event. TODO: implement up to n events
async def get_number_of_events(update: Update, context: CustomContext) -> int:
    try:
        number_of_events = int(update.message.text)
        context.user_data["number_of_events"] = number_of_events
        await update.message.reply_text("Please input the title of this event")
        return routes["GET_TITLE"]
    except ValueError:
        await update.message.reply_text("Please input a valid number.")
        return routes["GET_NUMBER_OF_EVENTS"]

# TODO: handle invalid input
async def get_title(update: Update, context: CustomContext) -> int:
    title = update.message.text
    context.user_data["title"] = title
    await update.message.reply_text("Please input the details of the poll.")
    return routes["GET_DETAILS"]

# TODO: handle invalid input
async def get_details(update: Update, context: CustomContext) -> int:
    details = update.message.text
    context.user_data["details"] = details
    await update.message.reply_text("Please input the start time of the poll.")
    return routes["GET_START_TIME"]

# TODO: handle invalid input
async def get_start_time(update: Update, context: CustomContext) -> int:
    start_time = update.message.text
    context.user_data["start_time"] = start_time
    await update.message.reply_text("Please input the end time of the poll.")
    return routes["GET_END_TIME"]

def get_poll_group_inline_keyboard(poll_id: str) -> list:
    return [[InlineKeyboardButton("Publish Non Regular Poll", switch_inline_query=f"nr_{poll_id}")],
            [InlineKeyboardButton("Publish Regular Poll", switch_inline_query=f"r_{poll_id}")],
            [InlineKeyboardButton("Update Results", callback_data=f"u_{poll_id}")], 
            [InlineKeyboardButton("Delete Poll", callback_data=f"d_{poll_id}")]]

# TODO: handle invalid input, logic to loop back for multiple events
async def get_end_time(update: Update, context: CustomContext) -> int:
    end_time = update.message.text
    user_id = update.message.from_user.id
    context.user_data["end_time"] = end_time
    poll = EventPoll(context.user_data["start_time"], context.user_data["end_time"], context.user_data["title"], context.user_data["details"], [12, 12])
    context.user_data["polls"].append(poll.to_dict())

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
    del context.user_data["title"]
    del context.user_data["details"]
    del context.user_data["start_time"]
    del context.user_data["end_time"]
    del context.user_data["poll_name"]
    del context.user_data["number_of_events"]
    del context.user_data["polls"]
    return ConversationHandler.END


def generate_poll_voting_callback_data(poll_id: int, poll_type: str, index: int) -> str:
    return f"p_{poll_type}_{poll_id}_{index}"

def generate_poll_group_text(poll_group: PollGroup, poll_type) -> str:
    polls = get_event_polls(poll_group.get_poll_ids())
    poll_body = [poll_group.name + "\n"]
    for i, poll in enumerate(polls):
        poll_body.append(f"{i+1}. {poll.title}\n{poll.details}\n{poll.start_time} - {poll.end_time}\n")
        if poll_type == "nr":
            lst = poll.non_regulars
        elif poll_type == "r":
            lst = poll.regulars
        else:
            raise ValueError("Invalid poll type: " + poll_type)
        for j, person in enumerate(lst):
            poll_body.append(f"{j+1}. {person}")
        poll_body.append("\n")
    poll_body = "\n".join(poll_body)
    return poll_body

def parse_forward_poll_query(query: str) -> tuple:
    poll_group_id = query.split("_")[1]
    if query.startswith("nr"):
        poll_type = "nr"
    elif query.startswith("r"):
        poll_type = "r"
    else:
        raise ValueError("Invalid query type: " + query)
    return poll_group_id, poll_type

async def forward_poll(update: Update, context: CustomContext) -> None:
    query = update.inline_query.query
    poll_group_id, poll_type = parse_forward_poll_query(query)

    poll_group = get_poll_group(poll_group_id)
    polls = get_event_polls(poll_group.get_poll_ids())

    keyboard = []
    for i, poll in enumerate(polls):
        keyboard.append([InlineKeyboardButton(f"{poll.title}",
                                              callback_data=generate_poll_voting_callback_data(poll.id, poll_type, i))])

    reply_markup = InlineKeyboardMarkup(keyboard)
    poll_body = generate_poll_group_text(poll_group, poll_type)
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
   
def parse_poll_voting_callback_query(query: str) -> tuple:
    poll_type, poll_id, index = query.split("_")[1:]
    return poll_id, poll_type, int(index)

# TODO: Refactor for better abstraction
def add_person_to_event(poll_id: str, username: str, poll_type: str) -> None:
    if poll_type == "nr":
        field = "non_regulars"
    elif poll_type == "r":
        field = "regulars"
    else:
        raise ValueError("Invalid poll type: " + poll_type)
    add_person_to_event_poll(poll_id, username, field)  

# TODO: Refactor for better abstraction
def remove_person_from_event(poll_id: str, username: str, poll_type: str) -> None:
    if poll_type == "nr":
        field = "non_regulars"
    elif poll_type == "r":
        field = "regulars"
    else:
        raise ValueError("Invalid poll type: " + poll_type)
    remove_person_from_event_poll(poll_id, username, field)

async def handle_poll_voting_callback(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    query = update.callback_query.data
    poll_id, poll_type, index = parse_poll_voting_callback_query(query)
    poll = get_event_poll(poll_id)
    username = update.callback_query.from_user.username
    # TODO: refactor this for better readability and logic
    if poll_type == "nr":
        if username in poll.non_regulars:
            remove_person_from_event(poll_id, username, poll_type)
        else:
            add_person_to_event(poll_id, username, poll_type)
    elif poll_type == "r":
        if username in poll.regulars:
            remove_person_from_event(poll_id, username, poll_type)
        else:
            add_person_to_event(poll_id, username, poll_type)
    else:
        raise ValueError("Invalid poll type: " + poll_type)
    await update.callback_query.answer()

    poll_group = get_poll_group(poll.poll_group_id)
    poll_body = generate_poll_group_text(poll_group, poll_type)
    keyboard = []
    polls = get_event_polls(poll_group.get_poll_ids())
    for i, poll in enumerate(polls):
        keyboard.append([InlineKeyboardButton(f"{poll.title}",
                                              callback_data=generate_poll_voting_callback_data(poll.id, poll_type, i))])
    await update.callback_query.edit_message_text(poll_body, reply_markup=InlineKeyboardMarkup(keyboard))
    logger.info("User %s responded to the poll.", user.username)
    # send a message to the admin that the user has responded to the poll
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"{user.mention_html()} has responded to the poll.",
        parse_mode=ParseMode.HTML,
    )

def get_update_results_callback_data(query: str) -> str:
    return query.split("_")[1]

async def handle_update_results_callback(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    old_text = update.callback_query.message.text
    logger.info("User %s requested the latest results of the poll.", user.username)
    data = update.callback_query.data
    poll_id = get_update_results_callback_data(data)
    poll_group = get_poll_group(poll_id)
    combined_text = generate_poll_group_overview_text(poll_group)
    # TODO: find a better way to check for no changes
    if old_text.strip("\n ") != combined_text.strip("\n "):
      await update.callback_query.edit_message_text(combined_text, reply_markup=update.callback_query.message.reply_markup)
    await update.callback_query.answer()

def get_delete_poll_callback_data(query: str) -> str:
    return query.split("_")[1]

async def handle_delete_poll_callback(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    logger.info("User %s requested to delete the poll.", user.username)
    # TODO: add confirmation step
    data = update.callback_query.data
    poll_group_id = get_delete_poll_callback_data(data)
    delete_poll_group(poll_group_id)
    await update.callback_query.edit_message_text("Poll deleted.")

async def attendance(update: Update, context: CustomContext) -> int:
    text = "Hi! Please click 'New List' to input a new list."
    reply_keyboard = [["New List"]]
    if "dct" in context.user_data:
        reply_keyboard[0].append("Continue List")
        text = "Hi! Please click 'New List' to input a new list or 'Continue List' to edit the existing list."
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return routes["SELECT_NEW_OR_CONTINUE"]

async def cancel(update: Update, context: CustomContext) -> int:
    """Ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text("Bye!", reply_markup=ReplyKeyboardRemove())
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
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Finally, send the message
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID, text=message, parse_mode=ParseMode.HTML
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
    entry_points=[CommandHandler("start", start), CommandHandler("attendance", attendance),
                  CommandHandler("new_poll", create_new_poll), CommandHandler("summary", summary),
                  CommandHandler("info", get_info), CommandHandler("polls", get_polls)],
    states={
        routes["SELECT_NEW_OR_CONTINUE"]: [MessageHandler(filters.Regex("^New List$"), input_list),
                                  MessageHandler(filters.Regex("^Continue List$"), edit_list)],
        routes["INPUT_LIST"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_list)],
        routes["EDIT_LIST"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_list),
                        CallbackQueryHandler(change_status, pattern="^\d+$"),
                        CallbackQueryHandler(do_nothing, pattern="^.$")],
        routes["SETTING_STATUS"]: [CallbackQueryHandler(setting_user_status, pattern="^(?!\d+$).+")],
        routes["GET_NUMBER_OF_EVENTS"]: [MessageHandler(filters.Regex("^\d+$") & ~filters.COMMAND, get_number_of_events)],
        routes["GET_TITLE"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
        routes["GET_DETAILS"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_details)],
        routes["GET_START_TIME"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_start_time)],
        routes["GET_END_TIME"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_end_time)],
        routes["SELECT_POLL_GROUP"]: [CallbackQueryHandler(poll_title_clicked_callback, pattern="^.+$")],
        routes["GET_POLL_NAME"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_poll_name)],
    },
    fallbacks=[CommandHandler("cancel", cancel), CommandHandler("summary", summary)],
)
application.add_handler(InlineQueryHandler(forward_poll))
application.add_handler(CallbackQueryHandler(handle_poll_voting_callback, pattern="^p_"))
application.add_handler(CallbackQueryHandler(handle_update_results_callback, pattern="^u_"))
application.add_handler(CallbackQueryHandler(handle_delete_poll_callback, pattern="^d_"))
application.add_handler(conv_handler)
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