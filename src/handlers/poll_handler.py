"""
Handlers for poll-related commands and callbacks.
"""

import logging

from telegram import InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ConversationHandler

from src.service import PollGroupService, PollService, TelegramMessageUpdater
from src.util import (
    POLL_GROUP_MANAGEMENT_TEXT,
    CustomContext,
    PollGroupNotFoundError,
    PollNotFoundError,
    Status,
    UserBannedError,
    compare_time,
    decode_delete_poll_callback,
    decode_generate_next_poll_callback,
    decode_manage_active_polls_callback,
    decode_manage_poll_groups_callback,
    decode_poll_voting_callback,
    decode_publish_poll_query,
    decode_set_poll_active_status_callback,
    decode_update_poll_results_callback,
    parse_dt_to_iso,
    routes,
)
from src.view import (
    build_ask_user_to_register_username_message,
    build_cannot_generate_next_poll_message,
    build_cannot_manage_active_polls_message,
    build_cannot_update_poll_results_message,
    build_end_time_before_start_time_message,
    build_get_details_of_event_message,
    build_get_end_time_message,
    build_get_number_of_events_message,
    build_get_start_time_message,
    build_invalid_end_time_message,
    build_invalid_number_of_events_message,
    build_invalid_start_time_message,
    build_manage_active_polls_message,
    build_new_poll_group_message,
    build_no_polls_message,
    build_poll_deleted_message,
    build_poll_group_management_message,
    build_poll_group_management_options,
    build_poll_group_not_found_message,
    build_poll_maker_overview_text,
    build_poll_unable_to_vote_message,
    build_poll_vote_confirmation_message,
    build_publish_options,
    build_select_poll_group_message,
    build_select_poll_group_options,
    build_user_banned_message,
    build_voting_buttons,
    generate_manage_active_polls_buttons,
    generate_poll_group_text,
)


class PollHandler:
    """Handler class for poll-group-related commands and callbacks."""

    def __init__(
        self,
        poll_service: PollService,
        poll_group_service: PollGroupService,
        telegram_message_updater: TelegramMessageUpdater,
    ):
        self.poll_service = poll_service
        self.poll_group_service = poll_group_service
        self.telegram_message_updater = telegram_message_updater
        self.logger = logging.getLogger(__name__)

    async def get_polls(self, update: Update, _: CustomContext) -> int:
        """Handles the /polls command to list the user's poll groups."""
        user = update.message.from_user
        poll_groups = self.poll_group_service.get_poll_groups(user)
        if not poll_groups:
            await update.message.reply_text(build_no_polls_message())
            return ConversationHandler.END
        await update.message.reply_text(
            build_select_poll_group_message(),
            reply_markup=InlineKeyboardMarkup(
                build_select_poll_group_options(poll_groups)
            ),
        )
        return ConversationHandler.END

    async def poll_title_clicked_callback(
        self, update: Update, _: CustomContext
    ) -> int:
        """Handles the callback when a poll group title is clicked in the poll group selection."""
        user = update.callback_query.from_user
        await update.callback_query.answer()
        poll_group_id = decode_manage_poll_groups_callback(update.callback_query.data)

        poll_group = self.poll_group_service.get_poll_group(poll_group_id, user)

        if poll_group is None:
            await update.callback_query.edit_message_text(
                build_poll_group_not_found_message()
            )
            return ConversationHandler.END
        await update.callback_query.edit_message_text(
            build_poll_group_management_message(poll_group),
            reply_markup=InlineKeyboardMarkup(
                build_poll_group_management_options(poll_group)
            ),
        )
        return ConversationHandler.END

    async def create_new_poll(self, update: Update, context: CustomContext) -> int:
        """Asks for the poll name when the command /new_poll is issued"""
        await update.message.reply_text(build_new_poll_group_message())
        context.user_data["polls"] = []
        return routes["GET_POLL_NAME"]

    async def process_poll_name_and_ask_number_of_events(
        self, update: Update, context: CustomContext
    ) -> int:
        """Handles receiving the poll name from the user and asks for the number of events."""
        poll_name = update.message.text
        await update.message.reply_text(build_get_number_of_events_message())
        context.user_data["poll_name"] = poll_name
        return routes["GET_NUMBER_OF_EVENTS"]

    async def process_number_of_events_and_ask_details(
        self, update: Update, context: CustomContext
    ) -> int:
        """Handles receiving the number of events from the user and asks for 1st event details."""
        try:
            number_of_events = int(update.message.text)
            if number_of_events < 1:
                raise ValueError()
            context.user_data["number_of_events"] = number_of_events
            context.user_data["current_event"] = 1
            await update.message.reply_text(build_get_details_of_event_message(1))
            return routes["GET_DETAILS"]
        except (ValueError, TypeError):
            await update.message.reply_text(build_invalid_number_of_events_message())
            return routes["GET_NUMBER_OF_EVENTS"]

    async def process_details_and_ask_start_time(
        self, update: Update, context: CustomContext
    ) -> int:
        """Handles receiving the event details from the user and asks for the start time."""
        details = update.message.text
        context.user_data["details"] = details
        await update.message.reply_text(build_get_start_time_message())
        return routes["GET_START_TIME"]

    async def process_start_time_and_ask_end_time(
        self, update: Update, context: CustomContext
    ) -> int:
        """Handles receiving the start time from the user and asks for the end time."""
        start_time = update.message.text

        status = Status()
        start_dt = parse_dt_to_iso(start_time, status)

        if not status.status:
            await update.message.reply_text(
                build_invalid_start_time_message(status.message)
            )
            return routes["GET_START_TIME"]

        context.user_data["start_time"] = start_dt
        await update.message.reply_text(build_get_end_time_message())

        return routes["GET_END_TIME"]

    async def process_end_time_and_handle_remaining_poll_details(
        self, update: Update, context: CustomContext
    ) -> int:
        """Handles receiving the end time from the user and processes the remaining poll details."""
        end_time = update.message.text
        status = Status()
        et = parse_dt_to_iso(end_time, status)

        if not status.status:
            await update.message.reply_text(
                build_invalid_end_time_message(status.message)
            )
            return routes["GET_END_TIME"]

        if compare_time(context.user_data["start_time"], et) > 0:
            await update.message.reply_text(build_end_time_before_start_time_message())
            return routes["GET_END_TIME"]

        user_id = update.message.from_user.id
        st = context.user_data["start_time"]
        details = context.user_data["details"]
        context.user_data["polls"].append([st, et, details])

        # Repeat the poll
        context.user_data["current_event"] += 1
        total_events = context.user_data["number_of_events"]
        current_event_count = context.user_data["current_event"]

        if current_event_count <= total_events:
            await update.message.reply_text(
                build_get_details_of_event_message(current_event_count)
            )
            return routes["GET_DETAILS"]

        polls_details = context.user_data["polls"]
        polls_ids = self.poll_service.save_event_polls(polls_details)
        poll_group = self.poll_group_service.create_poll_group(
            user_id, context.user_data["poll_name"], polls_ids
        )
        self.poll_service.update_poll_group_id(polls_ids, poll_group.id)

        inline_keyboard = build_poll_group_management_options(poll_group)
        await update.message.reply_text(
            f"Viewing {poll_group.name}\n\n" + POLL_GROUP_MANAGEMENT_TEXT,
            reply_markup=InlineKeyboardMarkup(inline_keyboard),
        )
        del context.user_data["details"]
        del context.user_data["start_time"]
        del context.user_data["poll_name"]
        del context.user_data["number_of_events"]
        del context.user_data["current_event"]
        del context.user_data["polls"]
        return ConversationHandler.END

    async def forward_poll(self, update: Update, _: CustomContext) -> None:
        """Handles inline queries to forward a poll to another Telegram chat."""
        query = update.inline_query.query
        poll_group_id = decode_publish_poll_query(query)
        if not poll_group_id:
            await update.inline_query.answer([])
            return
        try:
            poll_group, polls = self.poll_group_service.get_full_poll_group_details(
                poll_group_id
            )
        except (PollGroupNotFoundError, PollNotFoundError) as e:
            self.logger.warning("Error fetching poll/poll group details: %s", e)
            await update.inline_query.answer([])
            return
        await update.inline_query.answer(build_publish_options(poll_group, polls))

    async def handle_poll_voting_callback(
        self, update: Update, _: CustomContext
    ) -> None:
        """Handles the callback when a user votes in a poll."""
        user = update.callback_query.from_user
        query = update.callback_query.data
        poll_id, membership, is_sign_up, pollmaker_id = decode_poll_voting_callback(
            query
        )
        if user.username is None:
            await update.callback_query.answer(
                text=build_ask_user_to_register_username_message(),
                show_alert=True,
            )
            return
        username = f"@{user.username}"

        try:
            poll = self.poll_service.set_person_in_poll(
                poll_id, username, membership, is_sign_up, pollmaker_id
            )
        except PollNotFoundError:
            await update.callback_query.answer(
                text=build_poll_unable_to_vote_message(), show_alert=True
            )
            return
        except UserBannedError as e:
            await update.callback_query.answer(
                text=build_user_banned_message(e.banned_duration), show_alert=True
            )
            return
        await update.callback_query.answer(
            text=build_poll_vote_confirmation_message(poll.get_title(), is_sign_up),
            show_alert=True,
        )

        # Update the poll message
        poll_group, polls = self.poll_group_service.get_full_poll_group_details(
            poll.poll_group_id
        )

        await self.telegram_message_updater.update_polls_message(
            update.callback_query.inline_message_id,
            generate_poll_group_text(poll_group, polls, membership),
            InlineKeyboardMarkup(build_voting_buttons(polls, membership, pollmaker_id)),
            ParseMode.MARKDOWN_V2,
            poll.poll_group_id,
            membership,
        )

    async def handle_generate_next_poll_callback(
        self, update: Update, context: CustomContext
    ) -> None:
        """Handles the callback when a user requests to generate next week's poll."""
        data = update.callback_query.data
        poll_group_id = decode_generate_next_poll_callback(data)
        await update.callback_query.answer()
        context.user_data["poll_group_id"] = poll_group_id
        await update.callback_query.edit_message_text(build_new_poll_group_message())
        return routes["GET_NEW_POLL_NAME"]

    async def process_new_poll_name_and_create_new_poll(
        self, update: Update, context: CustomContext
    ) -> int:
        """Handles receiving the new poll name and creates the next week's poll."""
        new_poll_name = update.message.text
        poll_group_id = context.user_data["poll_group_id"]

        new_group, next_polls = self.poll_group_service.generate_next_poll_group(
            poll_group_id, new_poll_name
        )
        if new_group is None:
            await update.message.reply_text(build_cannot_generate_next_poll_message())
            return ConversationHandler.END

        await update.message.reply_text(
            build_poll_maker_overview_text(new_group, next_polls),
            reply_markup=InlineKeyboardMarkup(
                build_poll_group_management_options(new_group)
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ConversationHandler.END

    async def handle_update_results_callback(
        self, update: Update, _: CustomContext
    ) -> None:
        """Handles the callback when a user requests to update poll results."""
        data = update.callback_query.data
        poll_group_id = decode_update_poll_results_callback(data)
        poll_group, polls = self.poll_group_service.get_full_poll_group_details(
            poll_group_id
        )
        await update.callback_query.answer()
        if poll_group is None:
            await update.callback_query.edit_message_text(
                build_cannot_update_poll_results_message()
            )
            return
        try:
            await update.callback_query.edit_message_text(
                build_poll_maker_overview_text(poll_group, polls),
                reply_markup=update.callback_query.message.reply_markup,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except BadRequest:
            pass  # nothing changes

    async def handle_delete_poll_callback(
        self, update: Update, _: CustomContext
    ) -> None:
        """Handles the callback when a user requests to delete a poll group."""
        user = update.callback_query.from_user
        # TODO: add confirmation step
        data = update.callback_query.data
        poll_group_id = decode_delete_poll_callback(data)
        new_delete = self.poll_group_service.delete_poll_group(poll_group_id, user)
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            build_poll_deleted_message(new_delete)
        )

    async def handle_manage_active_polls_callback(
        self, update: Update, _: CustomContext
    ) -> None:
        """Handles the callback when a user requests to manage active polls."""
        data = update.callback_query.data
        poll_group_id = decode_manage_active_polls_callback(data)
        await update.callback_query.answer()
        poll_group, polls = self.poll_group_service.get_full_poll_group_details(
            poll_group_id
        )
        if poll_group is None:
            await update.callback_query.edit_message_text(
                build_cannot_manage_active_polls_message()
            )
            return
        keyboard = generate_manage_active_polls_buttons(polls, poll_group_id)
        await update.callback_query.edit_message_text(
            build_manage_active_polls_message(),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ConversationHandler.END

    async def handle_change_poll_active_status_callback(
        self, update: Update, _: CustomContext
    ) -> None:
        """Handles the callback when a user changes a poll's active status."""
        data = update.callback_query.data
        poll_id, membership, is_active = decode_set_poll_active_status_callback(data)
        await update.callback_query.answer()

        poll = self.poll_service.set_active_status(poll_id, membership, is_active)
        poll_group, polls = self.poll_group_service.get_full_poll_group_details(
            poll.poll_group_id
        )
        if poll_group is None:
            await update.callback_query.edit_message_text(
                build_cannot_manage_active_polls_message()
            )
            return
        try:
            await update.callback_query.edit_message_text(
                build_manage_active_polls_message(),
                reply_markup=InlineKeyboardMarkup(
                    generate_manage_active_polls_buttons(polls, poll_group.id)
                ),
            )
        except BadRequest:
            pass  # nothing changes
