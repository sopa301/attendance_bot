"""
Handlers for attendance-related commands and callbacks.
"""

from telegram import InlineKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import ConversationHandler

from src.model import AttendanceList
from src.service import AttendanceService, PollGroupService, PollService
from src.util import (
    CustomContext,
    PollNotFoundError,
    decode_manage_attendance_list,
    decode_mark_attendance,
    decode_view_attendance_list,
    decode_view_attendance_summary,
    decode_view_attendance_tracking_format,
    routes,
)
from src.view import (
    REQUEST_FOR_ATTENDANCE_LIST_INPUT_TEXT,
    build_attendance_list_deleted_message,
    build_attendance_list_logged_and_deleted_message,
    build_attendance_list_not_found_message,
    build_attendance_list_summary_text,
    build_attendance_menu_text,
    build_inline_keyboard_for_attendance_lists,
    build_inline_keyboard_for_attendance_summaries,
    build_inline_keyboard_for_attendance_tracking_format,
    build_invalid_attendance_list_format_message,
    build_manage_attendance_list_options,
    build_manage_attendance_list_text,
    build_manual_edit_attendance_list_message,
    build_manual_edit_attendance_list_repr,
    build_no_attendance_lists_for_import_text,
    build_no_attendance_lists_text,
    build_poll_group_not_found_message,
    build_poll_not_found_message,
    build_select_poll_group_to_import_options,
    build_select_poll_group_to_import_text,
    build_select_poll_to_import_options,
    build_select_poll_to_import_text,
    build_take_attendance_buttons,
    build_take_attendance_text,
    build_view_attendance_list_text,
    build_view_attendance_summaries_text,
    build_view_attendance_summary_excel_format_text,
    generate_attendance_summary_excel_format_text,
)


class AttendanceHandler:
    """Handler class for attendance-related commands and callbacks."""

    def __init__(
        self,
        attendance_service: AttendanceService,
        poll_group_service: PollGroupService,
        poll_service: PollService,
    ):
        self.attendance_service = attendance_service
        self.poll_group_service = poll_group_service
        self.poll_service = poll_service

    async def attendance(self, update: Update, _: CustomContext) -> int:
        """Entry point for attendance management."""
        await update.message.reply_text(build_attendance_menu_text())
        return routes["SELECT_NEW_OR_CONTINUE"]

    async def get_attendance_lists(self, update: Update, _: CustomContext) -> int:
        """Displays the list of attendance lists."""
        user = update.message.from_user
        attendance_lists = self.attendance_service.get_attendance_lists_by_owner_id(
            user.id
        )
        if not attendance_lists:
            await update.message.reply_text(build_no_attendance_lists_text())
            return ConversationHandler.END
        await update.message.reply_text(
            build_view_attendance_list_text(),
            reply_markup=InlineKeyboardMarkup(
                build_inline_keyboard_for_attendance_lists(attendance_lists)
            ),
        )
        return routes["VIEW_LIST"]

    async def handle_import_from_poll(self, update: Update, _: CustomContext) -> int:
        """Imports the attendance list from a poll."""
        user = update.message.from_user
        poll_groups = self.poll_group_service.get_poll_groups(user)

        if not poll_groups:
            await update.message.reply_text(build_no_attendance_lists_for_import_text())
            return ConversationHandler.END
        await update.message.reply_text(
            build_select_poll_group_to_import_text(),
            reply_markup=InlineKeyboardMarkup(
                build_select_poll_group_to_import_options(poll_groups)
            ),
        )
        return routes["SELECT_POLL_GROUP"]

    async def handle_select_poll_group(self, update: Update, _: CustomContext) -> int:
        """Handles the selection of a poll group for importing attendance lists."""
        poll_group_id = update.callback_query.data
        poll_group, polls = self.poll_group_service.get_full_poll_group_details(
            poll_group_id
        )
        await update.callback_query.answer()
        if not poll_group:
            await update.callback_query.edit_message_text(
                build_poll_group_not_found_message()
            )
            return ConversationHandler.END

        await update.callback_query.edit_message_text(
            build_select_poll_to_import_text(),
            reply_markup=InlineKeyboardMarkup(
                build_select_poll_to_import_options(polls)
            ),
        )
        return routes["SELECT_POLL"]

    async def handle_select_poll(self, update: Update, _: CustomContext) -> int:
        """Handles the selection of a poll for importing attendance lists."""
        poll_id = update.callback_query.data

        try:
            attendance_list = self.attendance_service.create_attendance_list_from_poll(
                poll_id, update.callback_query.from_user
            )
        except PollNotFoundError:
            await update.callback_query.edit_message_text(
                build_poll_not_found_message()
            )
            return ConversationHandler.END
        await self._edit_message_take_attendance_buttons(attendance_list, update)
        return ConversationHandler.END

    async def handle_view_attendance_list(
        self, update: Update, context: CustomContext
    ) -> int:
        """Handles viewing an attendance list."""
        attendance_list_id = decode_view_attendance_list(update.callback_query.data)

        attendance_list = self.attendance_service.get_attendance_list(
            attendance_list_id
        )
        if not attendance_list:
            await update.callback_query.edit_message_text(
                build_attendance_list_not_found_message()
            )
            return ConversationHandler.END

        context.user_data["attendance_list"] = attendance_list.to_dict()
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            build_manage_attendance_list_text(attendance_list),
            reply_markup=InlineKeyboardMarkup(build_manage_attendance_list_options()),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return routes["MANAGE_ATTENDANCE_LIST"]

    async def _edit_message_take_attendance_buttons(
        self, attendance_list, update: Update
    ) -> None:
        """Displays the take attendance buttons."""
        attendance_list_buttons = build_take_attendance_buttons(attendance_list)
        await update.callback_query.edit_message_text(build_take_attendance_text())
        for index, msg in enumerate(attendance_list_buttons):
            await update.callback_query.message.reply_text(
                f"Part {index + 1}", reply_markup=InlineKeyboardMarkup(msg)
            )

    async def _reply_take_attendance_buttons(
        self, attendance_list, update: Update
    ) -> None:
        """Displays the take attendance buttons."""
        attendance_list_buttons = build_take_attendance_buttons(attendance_list)
        await update.message.reply_text(build_take_attendance_text())
        for index, msg in enumerate(attendance_list_buttons):
            await update.message.reply_text(
                f"Part {index + 1}", reply_markup=InlineKeyboardMarkup(msg)
            )

    async def handle_manage_attendance_list(
        self, update: Update, context: CustomContext
    ) -> int:
        """Handles managing an attendance list."""
        command = decode_manage_attendance_list(update.callback_query.data)
        attendance_list = AttendanceList.from_dict(context.user_data["attendance_list"])
        if command == "take_attendance":
            await self._edit_message_take_attendance_buttons(attendance_list, update)
            return ConversationHandler.END
        if command == "edit":
            await update.callback_query.edit_message_text(
                build_manual_edit_attendance_list_message()
            )
            await update.callback_query.message.reply_text(
                build_manual_edit_attendance_list_repr(attendance_list)
            )
            return routes["RECEIVE_EDITED_LIST"]
        if command == "delete":
            self.attendance_service.delete_attendance_list(attendance_list.id)
            await update.callback_query.edit_message_text(
                build_attendance_list_deleted_message()
            )
            return ConversationHandler.END
        if command == "log_and_delete":
            # log_bans(attendance_list)
            self.attendance_service.delete_attendance_list(attendance_list.id)
            await update.callback_query.edit_message_text(
                build_attendance_list_logged_and_deleted_message()
            )
            return ConversationHandler.END
        raise ValueError("Invalid command: " + command)

    async def process_edited_attendance_list(
        self, update: Update, context: CustomContext
    ) -> int:
        """Processes the edited attendance list from the user."""
        message_text = update.message.text
        old_list = AttendanceList.from_dict(context.user_data["attendance_list"])
        try:
            attendance_list = AttendanceList.parse_list(message_text)
        except (ValueError, KeyError, AttributeError):
            await update.message.reply_text(
                build_invalid_attendance_list_format_message()
            )
            return routes["RECEIVE_EDITED_LIST"]
        attendance_list = self.attendance_service.process_edited_list(
            old_list, attendance_list
        )
        await self._reply_take_attendance_buttons(attendance_list, update)
        return ConversationHandler.END

    async def request_attendance_list(self, update: Update, _: CustomContext) -> int:
        """Requests the raw attendance list text from the user."""
        await update.message.reply_text(
            REQUEST_FOR_ATTENDANCE_LIST_INPUT_TEXT, reply_markup=ReplyKeyboardRemove()
        )
        return routes["RECEIVE_INPUT_LIST"]

    async def process_inputted_attendance_list(
        self, update: Update, _: CustomContext
    ) -> int:
        """Processes the new inputted attendance list from the user."""
        message_text = update.message.text
        try:
            attendance_list = AttendanceList.parse_list(message_text)
        except (ValueError, KeyError, AttributeError):
            await update.message.reply_text(
                build_invalid_attendance_list_format_message()
            )
            return routes["RECEIVE_INPUT_LIST"]
        attendance_list = self.attendance_service.create_attendance_list(
            attendance_list, update.message.from_user.id
        )
        await self._reply_take_attendance_buttons(attendance_list, update)
        return ConversationHandler.END

    async def handle_summary_request(self, update: Update, _: CustomContext) -> int:
        """Handle request for attendance summary via /summary."""

        attendance_lists = self.attendance_service.get_attendance_lists_by_owner_id(
            update.message.from_user.id
        )
        if not attendance_lists:
            await update.message.reply_text(build_no_attendance_lists_text())
            return ConversationHandler.END

        await update.message.reply_text(
            build_view_attendance_summaries_text(),
            reply_markup=InlineKeyboardMarkup(
                build_inline_keyboard_for_attendance_summaries(attendance_lists)
            ),
        )
        return ConversationHandler.END

    async def handle_view_attendance_summary(
        self, update: Update, _: CustomContext
    ) -> int:
        """Handles request to view a specific attendance summary."""
        attendance_list_id = decode_view_attendance_summary(update.callback_query.data)
        attendance_list = self.attendance_service.get_attendance_list(
            attendance_list_id
        )
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            build_attendance_list_summary_text(attendance_list), parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

    async def handle_excel_summary_request(
        self, update: Update, _: CustomContext
    ) -> int:
        """Handles request for the summary for attendance tracking excel sheet"""
        attendance_lists = self.attendance_service.get_attendance_lists_by_owner_id(
            update.message.from_user.id
        )
        if not attendance_lists:
            await update.message.reply_text(build_no_attendance_lists_text())
            return ConversationHandler.END
        await update.message.reply_text(
            build_view_attendance_summary_excel_format_text(),
            reply_markup=InlineKeyboardMarkup(
                build_inline_keyboard_for_attendance_tracking_format(attendance_lists)
            ),
        )
        return ConversationHandler.END

    async def handle_view_attendance_excel_summary(
        self, update: Update, _: CustomContext
    ) -> int:
        """Handles request to view attendance tracking format summary."""
        attendance_list_id = decode_view_attendance_tracking_format(
            update.callback_query.data
        )
        attendance_list = self.attendance_service.get_attendance_list(
            attendance_list_id
        )
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            generate_attendance_summary_excel_format_text(attendance_list)
        )
        return ConversationHandler.END

    async def change_attendance(self, update: Update, _: CustomContext) -> None:
        """Handles the attendance status of the user."""
        user_id, attendance_list_id, new_status = decode_mark_attendance(
            update.callback_query.data
        )
        attendance_list = self.attendance_service.update_user_status(
            attendance_list_id, user_id, new_status
        )

        if not attendance_list:
            await update.callback_query.answer(
                build_attendance_list_not_found_message()
            )
            return ConversationHandler.END
        attendance_list_buttons = build_take_attendance_buttons(attendance_list)
        message_text = update.callback_query.message.text
        index = self._parse_index_from_message_text(message_text)
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=InlineKeyboardMarkup(attendance_list_buttons[index]),
        )
        return ConversationHandler.END

    def _parse_index_from_message_text(self, message_text: str) -> int:
        """Parses the index from the message text, assuming it is in the format 'Part X',
        where X is the index number indexed from 1."""
        return int(message_text.split("Part ")[1]) - 1
