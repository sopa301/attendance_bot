import html
import json
import logging

from flask import Flask, request

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, ReplyKeyboardMarkup, Update, InlineQueryResultArticle, InputTextMessageContent
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
        "/help to get help\n"
        "/cancel to cancel the conversation",
        )
    return ConversationHandler.END

async def create_new_poll(update: Update, context: CustomContext) -> int:
    """Sends a message when the command /new_poll is issued"""
    user = update.message.from_user
    logger.info("User %s requested to create a new poll.", user.first_name)
    await update.message.reply_text("Please input the number of events you want to poll for.")
    return routes["GET_NUMBER_OF_EVENTS"]

# currently, the thing only accepts one event. TODO: implement up to n events
async def get_number_of_events(update: Update, context: CustomContext) -> int:
    try:
        number_of_events = int(update.message.text)
        context.user_data["number_of_events"] = number_of_events
        await update.message.reply_text("Please input the title of the poll.")
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

# TODO: handle invalid input, logic to loop back for multiple events
async def get_end_time(update: Update, context: CustomContext) -> int:
    end_time = update.message.text
    context.user_data["end_time"] = end_time
    await update.message.reply_text("Poll created.")
    # TODO: create buttons to publish the poll to both groups, update results, or delete the poll

    # TODO: create entry in DB
    poll_id = 1 # dummy poll id
    # create the inline buttons for all
    inline_keyboard = [[InlineKeyboardButton("Publish Non Regular Poll", switch_inline_query=f"nr_{poll_id}")],
                        [InlineKeyboardButton("Publish Regular Poll", switch_inline_query=f"r_{poll_id}")],
                        [InlineKeyboardButton("Update Results", callback_data=f"u_{poll_id}")], 
                        [InlineKeyboardButton("Delete Poll", callback_data=f"d_{poll_id}")]]

    # create a button to forward a message with inline buttons to another chat
    await update.message.reply_text("Please click the button below to send the poll to another chat.",
                                    reply_markup=InlineKeyboardMarkup(inline_keyboard))
    return ConversationHandler.END


def generate_poll_voting_callback_data(poll_id: int, poll_type: str, index: int) -> str:
    return f"p_{poll_type}_{poll_id}_{index}"

def generate_poll_group_text(poll_group: PollGroup, poll_type) -> str:
    poll_body = [poll_group.name + "\n"]
    for i, poll in enumerate(poll_group.polls):
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

async def forward_poll(update: Update, context: CustomContext) -> None:
    query = update.inline_query.query
    # parse the query in the format "nr_{poll_id}" or "r_{poll_id}"
    poll_id = query.split("_")[1]
    if query.startswith("nr"):
        poll_type = "nr"
    elif query.startswith("r"):
        poll_type = "r"
    else:
        raise ValueError("Invalid query type: " + query)

    # TODO: retrieve poll details from DB
    poll_group = get_poll_group_from_db(poll_id)

    keyboard = []
    for i, poll in enumerate(poll_group.polls):
        keyboard.append([InlineKeyboardButton(f"{poll.title}",
                                              callback_data=generate_poll_voting_callback_data(poll_group.id, poll_type, i))])

    reply_markup = InlineKeyboardMarkup(keyboard)
    poll_body = generate_poll_group_text(poll_group, poll_type)
    results = []  # Prepare response options for inline query
    # Add the inline query result with buttons
    results.append(
        InlineQueryResultArticle(
            id=poll_id,
            title="Send Poll",
            input_message_content=InputTextMessageContent(
                poll_body,
            ),
            reply_markup=reply_markup,  # Attach inline buttons here
        )
    )
    
    await update.inline_query.answer(results)
   
def get_poll_voting_callback_data(query: str) -> tuple:
    poll_type, poll_id, index = query.split("_")[1:]
    return int(poll_id), poll_type, int(index)

# TODO: make this real
def get_poll_group_from_db(poll_id: int) -> PollGroup:
    poll_group = PollGroup(poll_id, "Regular Sessions", 2)
    poll1 = EventPoll("2022-01-01 00:00:00", "2022-01-01 23:59:59", "Pickleball", "Multipurpose Courts", "Regular", 2, [12, 12])
    poll2 = EventPoll("2022-01-02 00:00:00", "2022-01-02 23:59:59", "Pickleball2", "Multipurpose Courts2", "Regular", 2, [12, 12])
    poll_group.polls = [poll1, poll2]
    return poll_group

# TODO
def save_poll_group_to_db(poll_group: PollGroup) -> None:
    pass

async def handle_poll_voting_callback(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    logger.info("User %s responded to the poll.", user.username)
    # send a message to the admin that the user has responded to the poll
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"{user.mention_html()} has responded to the poll.",
        parse_mode=ParseMode.HTML,
    )
    query = update.callback_query.data
    poll_id, poll_type, index = get_poll_voting_callback_data(query)
    poll_group = get_poll_group_from_db(poll_id)
    username = update.callback_query.from_user.username
    if poll_type == "nr":
        poll = poll_group.polls[index]
        if username in poll.non_regulars:
            poll.non_regulars.remove(username)
        else:
            poll.non_regulars.append(username)
    elif poll_type == "r":
        poll = poll_group.polls[index]
        if username in poll.regulars:
            poll.regulars.remove(username)
        else:
            poll.regulars.append(username)
    else:
        raise ValueError("Invalid poll type: " + poll_type)
    save_poll_group_to_db(poll_group)
    await update.callback_query.answer()
    # update the list to show the new status
    keyboard = []
    for i, poll in enumerate(poll_group.polls):
        keyboard.append([InlineKeyboardButton(f"{poll.title}",
                                              callback_data=generate_poll_voting_callback_data(poll_group.id, poll_type, i))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    poll_body = generate_poll_group_text(poll_group, poll_type)
    await update.callback_query.edit_message_text(poll_body, reply_markup=reply_markup)

def get_update_results_callback_data(query: str) -> int:
    return int(query.split("_")[1])

async def handle_update_results_callback(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    logger.info("User %s requested the latest results of the poll.", user.username)
    data = update.callback_query.data
    poll_id = get_update_results_callback_data(data)
    poll_group = get_poll_group_from_db(poll_id)
    combined_text = "Non Regulars:\n" + generate_poll_group_text(poll_group, "nr") + "\n\nRegulars\n" + generate_poll_group_text(poll_group, "r")
    inline_keyboard = [[InlineKeyboardButton("Publish Non Regular Poll", switch_inline_query=f"nr_{poll_id}")],
                        [InlineKeyboardButton("Publish Regular Poll", switch_inline_query=f"r_{poll_id}")],
                        [InlineKeyboardButton("Update Results", callback_data=f"u_{poll_id}")], 
                        [InlineKeyboardButton("Delete Poll", callback_data=f"d_{poll_id}")]]
    await update.callback_query.edit_message_text(combined_text, reply_markup=InlineKeyboardMarkup(inline_keyboard))
    await update.callback_query.answer()

def get_delete_poll_callback_data(query: str) -> int:
    return int(query.split("_")[1])

def delete_poll_from_db(poll_id: int) -> None:
    pass

async def handle_delete_poll_callback(update: Update, context: CustomContext) -> None:
    user = update.callback_query.from_user
    logger.info("User %s requested to delete the poll.", user.username)
    # TODO: add confirmation
    data = update.callback_query.data
    poll_id = get_delete_poll_callback_data(data)
    delete_poll_from_db(poll_id)
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
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    await update.message.reply_text(
        "Bye!", reply_markup=ReplyKeyboardRemove()
    )

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
        chat_id=int(env_config["DEVELOPER_CHAT_ID"]), text=message, parse_mode=ParseMode.HTML
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
                  CommandHandler("new_poll", create_new_poll), CommandHandler("summary", summary)],
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
        routes["GET_END_TIME"]: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_end_time)]
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