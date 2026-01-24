"""Main application file for the Telegram bot."""

import logging

import redis
from flask import Flask, request
from qstash import QStash
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    InlineQueryHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from src.api.debounce_worker import bp as debounce_worker_bp
from src.handlers import AttendanceHandler, BanHandler, GeneralHandler, PollHandler
from src.repositories import attendance_repo, ban_repo, poll_group_repo, poll_repo
from src.service import (
    AttendanceService,
    BanService,
    PollGroupService,
    PollService,
    TelegramMessageUpdater,
)
from src.util import (
    DELETE_POLL_REGEX_STRING,
    DO_NOTHING_REGEX_STRING,
    GENERATE_NEXT_POLL_REGEX_STRING,
    MANAGE_ACTIVE_POLLS_REGEX_STRING,
    MANAGE_ATTENDANCE_LIST_REGEX_STRING,
    MANAGE_POLL_GROUPS_REGEX_STRING,
    MARK_ATTENDANCE_REGEX_STRING,
    POLL_VOTING_REGEX_STRING,
    SET_POLL_ACTIVE_STATUS_REGEX_STRING,
    UNBAN_USER_REGEX_STRING,
    UPDATE_POLL_RESULTS_REGEX_STRING,
    VIEW_ATTENDANCE_LISTS_REGEX_STRING,
    VIEW_ATTENDANCE_TRACKING_FORMAT_REGEX_STRING,
    VIEW_SUMMARY_REGEX_STRING,
    CustomContext,
    WebhookUpdate,
    import_env,
    routes,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

app = Flask(__name__)
app.register_blueprint(debounce_worker_bp)

# import env variables
env_variables = [
    "DEPLOYMENT_URL",
    "BOT_TOKEN",
    "MONGO_URL",
    "MONGO_DB_NAME",
    "DEVELOPER_CHAT_ID",
    "MONGO_POLLS_COLLECTION_NAME",
    "MONGO_GROUPS_COLLECTION_NAME",
    "MONGO_ATTENANCES_COLLECTION_NAME",
    "MONGO_BANS_COLLECTION_NAME",
    "REDIS_URL",
    "QSTASH_TOKEN",
]
env_config = import_env(env_variables)

# Define configuration constants
admin_chat_id = int(env_config["DEVELOPER_CHAT_ID"])
context_types = ContextTypes(context=CustomContext)
application = (
    ApplicationBuilder()
    .token(env_config["BOT_TOKEN"])
    .context_types(context_types)
    .build()
)
bot = application.bot

# Instantiate services
redis_client = redis.from_url(env_config["REDIS_URL"], decode_responses=True)
qstash_client = QStash(env_config["QSTASH_TOKEN"])

ban_service = BanService(ban_repo)
poll_service = PollService(poll_repo, ban_service)
poll_group_service = PollGroupService(poll_group_repo, poll_service)
attendance_service = AttendanceService(attendance_repo, poll_service, ban_service)
telegram_message_updater = TelegramMessageUpdater(redis_client, bot, qstash_client)

# Instantiate internal handlers
poll_handler = PollHandler(poll_service, poll_group_service, telegram_message_updater)
attendance_handler = AttendanceHandler(
    attendance_service, poll_group_service, poll_service, ban_service
)
ban_handler = BanHandler(ban_service)
general_handler = GeneralHandler(admin_chat_id)

# register handlers
general_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("start", general_handler.start),
        CommandHandler("info", general_handler.get_info),
    ],
    states={},
    fallbacks=[CommandHandler("cancel", general_handler.cancel)],
)

poll_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("new_poll", poll_handler.create_new_poll),
        CommandHandler("polls", poll_handler.get_polls),
        CallbackQueryHandler(
            poll_handler.handle_generate_next_poll_callback,
            pattern=GENERATE_NEXT_POLL_REGEX_STRING,
        ),
    ],
    states={
        routes["GET_NUMBER_OF_EVENTS"]: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                poll_handler.process_number_of_events_and_ask_details,
            )
        ],
        routes["GET_DETAILS"]: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                poll_handler.process_details_and_ask_start_time,
            )
        ],
        routes["GET_START_TIME"]: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                poll_handler.process_start_time_and_ask_end_time,
            )
        ],
        routes["GET_END_TIME"]: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                poll_handler.process_end_time_and_handle_remaining_poll_details,
            )
        ],
        routes["GET_POLL_NAME"]: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                poll_handler.process_poll_name_and_ask_number_of_events,
            )
        ],
        routes["GET_NEW_POLL_NAME"]: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                poll_handler.process_new_poll_name_and_create_new_poll,
            )
        ],
    },
    fallbacks=[CommandHandler("cancel", general_handler.cancel)],
)

attendance_conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("attendance", attendance_handler.attendance),
        CommandHandler("summary", attendance_handler.handle_summary_request),
        CommandHandler(
            "attendance_tracking", attendance_handler.handle_excel_summary_request
        ),
    ],
    states={
        routes["SELECT_NEW_OR_CONTINUE"]: [
            CommandHandler("new_list", attendance_handler.request_attendance_list),
            CommandHandler("view_lists", attendance_handler.get_attendance_lists),
            CommandHandler(
                "import_from_poll", attendance_handler.handle_import_from_poll
            ),
        ],
        routes["MANAGE_ATTENDANCE_LIST"]: [
            CallbackQueryHandler(
                attendance_handler.handle_manage_attendance_list,
                pattern=MANAGE_ATTENDANCE_LIST_REGEX_STRING,
            )
        ],
        routes["RECEIVE_INPUT_LIST"]: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                attendance_handler.process_inputted_attendance_list,
            )
        ],
        routes["VIEW_LIST"]: [
            CallbackQueryHandler(
                attendance_handler.handle_view_attendance_list,
                pattern=VIEW_ATTENDANCE_LISTS_REGEX_STRING,
            )
        ],
        routes["RECEIVE_EDITED_LIST"]: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                attendance_handler.process_edited_attendance_list,
            )
        ],
        routes["SELECT_POLL_GROUP"]: [
            CallbackQueryHandler(attendance_handler.handle_select_poll_group)
        ],
        routes["SELECT_POLL"]: [
            CallbackQueryHandler(attendance_handler.handle_select_poll)
        ],
    },
    fallbacks=[CommandHandler("cancel", general_handler.cancel)],
)

ban_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("bans", ban_handler.get_bans)],
    states={},
    fallbacks=[CommandHandler("cancel", general_handler.cancel)],
)

# Always-active request handlers
application.add_handler(InlineQueryHandler(poll_handler.forward_poll))
application.add_handler(
    CallbackQueryHandler(
        poll_handler.handle_poll_voting_callback, pattern=POLL_VOTING_REGEX_STRING
    )
)
application.add_handler(
    CallbackQueryHandler(
        poll_handler.handle_update_results_callback,
        pattern=UPDATE_POLL_RESULTS_REGEX_STRING,
    )
)
application.add_handler(
    CallbackQueryHandler(
        poll_handler.handle_manage_active_polls_callback,
        pattern=MANAGE_ACTIVE_POLLS_REGEX_STRING,
    )
)
application.add_handler(
    CallbackQueryHandler(
        poll_handler.handle_change_poll_active_status_callback,
        pattern=SET_POLL_ACTIVE_STATUS_REGEX_STRING,
    )
)
application.add_handler(
    CallbackQueryHandler(
        poll_handler.handle_delete_poll_callback, pattern=DELETE_POLL_REGEX_STRING
    )
)
application.add_handler(
    CallbackQueryHandler(
        poll_handler.poll_title_clicked_callback,
        pattern=MANAGE_POLL_GROUPS_REGEX_STRING,
    )
)
application.add_handler(
    CallbackQueryHandler(
        attendance_handler.handle_view_attendance_summary,
        pattern=VIEW_SUMMARY_REGEX_STRING,
    )
)
application.add_handler(
    ConversationHandler(  # Wrap in ConversationHandler to use per_message handling
        entry_points=[
            CallbackQueryHandler(
                attendance_handler.change_attendance,
                pattern=MARK_ATTENDANCE_REGEX_STRING,
            )
        ],
        states={},
        fallbacks=[],
        per_message=True,
    )
)
application.add_handler(
    CallbackQueryHandler(general_handler.do_nothing, pattern=DO_NOTHING_REGEX_STRING)
)
application.add_handler(
    CallbackQueryHandler(
        attendance_handler.handle_view_attendance_excel_summary,
        pattern=VIEW_ATTENDANCE_TRACKING_FORMAT_REGEX_STRING,
    )
)
application.add_handler(
    CallbackQueryHandler(ban_handler.unban_user, pattern=UNBAN_USER_REGEX_STRING)
)

# Transient conversation handler
application.add_handler(general_conv_handler)
application.add_handler(poll_conv_handler)
application.add_handler(attendance_conv_handler)
application.add_handler(ban_conv_handler)


# Misc handlers
application.add_handler(
    TypeHandler(type=WebhookUpdate, callback=general_handler.webhook_update)
)
application.add_error_handler(general_handler.error_handler)


@app.route("/", methods=["POST"])
async def webhook():
    """Webhook endpoint to receive updates from Telegram."""
    if request.headers.get("content-type") == "application/json":
        async with application:
            update = Update.de_json(request.get_json(force=True), application.bot)
            await application.process_update(update)
            return ("", 204)
    else:
        return ("Bad request", 400)
