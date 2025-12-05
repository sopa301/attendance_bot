"""Views related to attendance functionalities."""

from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

from model import AttendanceList, EventPoll, PollGroup
from util import (
    ABSENT,
    ABSENT_SYMBOL,
    DO_NOTHING,
    LAST_MINUTE_CANCELLATION,
    PRESENT,
    PRESENT_SYMBOL,
    encode_manage_attendance_list,
    encode_mark_attendance,
    encode_view_attendance_list,
    encode_view_attendance_summary,
    encode_view_attendance_tracking_format,
    escape_markdown_characters,
    status_map,
)


def generate_absent_string(absentee: str, index: int) -> str:
    """Generates an absent string for the absentee."""
    absentee = escape_markdown_characters(absentee)
    return f"{index}\. {ABSENT_SYMBOL}{absentee}"


def generate_present_string(presentee: str, index: int) -> str:
    """Generates a present string for the presentee."""
    presentee = escape_markdown_characters(presentee)
    return f"{index}\. {PRESENT_SYMBOL}{presentee}"


def generate_last_minute_cancellation_string(cancellation: str, index: int) -> str:
    """Generates a last minute cancellation string for the cancellation."""
    cancellation = escape_markdown_characters(cancellation)
    return f"~{index}\. {cancellation}~"


def generate_status_string(status: int, name: str, index: int) -> str:
    """Generates a status string based on the status."""
    if status == ABSENT:
        return generate_absent_string(name, index)
    elif status == PRESENT:
        return generate_present_string(name, index)
    elif status == LAST_MINUTE_CANCELLATION:
        return generate_last_minute_cancellation_string(name, index)
    else:
        raise ValueError("Invalid status")


def build_attendance_menu_text() -> str:
    """Builds the attendance menu text."""
    return (
        "Please select an option:\n"
        + "/new_list to create a new attendance list\n"
        + "/import_from_poll to import a list from a poll\n"
        + "/view_lists to manage existing lists"
    )


def _build_inline_keyboard_for_attendance_list_titles(
    attendance_lists: List[AttendanceList], callback_encoder: callable
) -> List[List[InlineKeyboardButton]]:
    """Builds an inline keyboard for displaying a list of attendance list titles
    using the provided callback encoder function."""
    inlinekeyboard = []
    for attendance_list in attendance_lists:
        inlinekeyboard.append(
            [
                InlineKeyboardButton(
                    attendance_list.get_title(),
                    callback_data=callback_encoder(attendance_list.id),
                )
            ]
        )
    return inlinekeyboard


def build_inline_keyboard_for_attendance_lists(
    attendance_lists: List[AttendanceList],
) -> List[List[InlineKeyboardButton]]:
    """Builds an inline keyboard for displaying a list of attendance list titles
    for viewing the attendance lists."""
    return _build_inline_keyboard_for_attendance_list_titles(
        attendance_lists, encode_view_attendance_list
    )


def build_inline_keyboard_for_attendance_summaries(
    attendance_lists: List[AttendanceList],
) -> List[List[InlineKeyboardButton]]:
    """Builds an inline keyboard for displaying a list of attendance list titles for
    viewing summaries."""
    return _build_inline_keyboard_for_attendance_list_titles(
        attendance_lists, encode_view_attendance_summary
    )


def build_inline_keyboard_for_attendance_tracking_format(
    attendance_lists: List[AttendanceList],
) -> List[List[InlineKeyboardButton]]:
    """Generates an inline keyboard for displaying a list of attendance list titles for
    viewing the excel attendance tracking format."""
    return _build_inline_keyboard_for_attendance_list_titles(
        attendance_lists, encode_view_attendance_tracking_format
    )


def build_view_attendance_list_text() -> str:
    """Builds the text for viewing an attendance list."""
    return "Please select the attendance list you want to edit."


def build_no_attendance_lists_text() -> str:
    """Builds the text for when there are no attendance lists."""
    return "You have no attendance list yet."


def build_no_attendance_lists_for_import_text() -> str:
    """Builds the text for when there are no attendance lists available for import."""
    return "You have no attendance lists available for import."


def build_select_poll_group_to_import_text() -> str:
    """Builds the text for selecting a poll group to import from."""
    return "Please select the poll group you want to import from."


def build_select_poll_group_to_import_options(poll_groups: List[PollGroup]) -> str:
    """Builds the text for selecting a poll group to import from."""
    keyboard = []
    for poll_group in poll_groups:
        keyboard.append(
            [InlineKeyboardButton(poll_group.name, callback_data=poll_group.id)]
        )
    return keyboard


def build_select_poll_to_import_text() -> str:
    """Builds the text for selecting a poll to import from."""
    return "Please select the poll you want to import from."


def build_select_poll_to_import_options(polls: List[EventPoll]) -> list:
    """Builds an inline keyboard for selecting polls to import from."""
    return _build_inline_keyboard_for_attendance_list_titles(polls, lambda x: x)


def build_attendance_list_not_found_message() -> str:
    """Builds the message for when an attendance list is not found."""
    return "The selected attendance list was not found."


def build_manage_attendance_list_text(attendance_list: AttendanceList) -> str:
    """Builds the text for managing an attendance list."""
    return (
        f"You are managing the attendance list: "
        f"*{escape_markdown_characters(attendance_list.get_title())}*\n\n"
        "Please choose an option below:"
    )


def build_manage_attendance_list_options() -> List[List[InlineKeyboardButton]]:
    """Builds the inline keyboard options for managing an attendance list."""
    return [
        [
            InlineKeyboardButton(
                "Take Attendance",
                callback_data=encode_manage_attendance_list("take_attendance"),
            )
        ],
        [
            InlineKeyboardButton(
                "Edit", callback_data=encode_manage_attendance_list("edit")
            )
        ],
        [
            InlineKeyboardButton(
                "Delete", callback_data=encode_manage_attendance_list("delete")
            )
        ],
        [
            InlineKeyboardButton(
                "Log and Delete",
                callback_data=encode_manage_attendance_list("log_and_delete"),
            )
        ],
    ]


def build_manual_edit_attendance_list_message() -> str:
    """Builds the text for manually editing an attendance list."""
    return "Please copy and edit the list, then send it to me."


def build_manual_edit_attendance_list_repr(attendance_list: AttendanceList) -> str:
    """Builds the representation text for manually editing an attendance list."""
    return attendance_list.to_parsable_list()


def build_attendance_list_deleted_message() -> str:
    """Builds the message for when an attendance list is deleted."""
    return "Attendance list deleted."


def build_attendance_list_logged_and_deleted_message() -> str:
    """Builds the message for when an attendance list is logged and deleted."""
    return "Attendance list logged and deleted."


def build_invalid_attendance_list_format_message() -> str:
    """Builds the message for when an attendance list format is invalid."""
    return "Invalid list format. Please input the list again."


REQUEST_FOR_ATTENDANCE_LIST_INPUT_TEXT = (
    "Please input the list in the following format: "
    "\n\nPickleball session (date)\n\nNon-Regulars\n1. ...\n2. ...\n\nRegulars\n1. ...\n2."
    " ...\n\nStandins\n1. ...\n2. ...\n\nExco\n...\n..."
)


def build_view_attendance_summaries_text() -> str:
    """Builds the text for viewing attendance summaries."""
    return "Please select the attendance list summary you want to view."


def build_view_attendance_summary_excel_format_text() -> str:
    """Builds the text for viewing attendance summary in excel format."""
    return "Please select the attendance list you want to view in excel format."


def build_attendance_list_summary_text(attendance_list: AttendanceList) -> str:
    """Builds the summary text for an attendance list."""
    output_list = []
    for line in attendance_list.details:
        output_list.append(escape_markdown_characters(line))
    output_list.append("")

    output_list.append(escape_markdown_characters("Non-Regulars"))
    for i, tp in enumerate(attendance_list.non_regulars):
        output_list.append(generate_status_string(tp.status, tp.name, i + 1))

    output_list.append("")

    output_list.append("Regulars")
    for i, tp in enumerate(attendance_list.regulars):
        output_list.append(generate_status_string(tp.status, tp.name, i + 1))

    if len(attendance_list.standins) > 0:
        output_list.append("")

        output_list.append("Standins")
        for i, tp in enumerate(attendance_list.standins):
            output_list.append(generate_status_string(tp.status, tp.name, i + 1))

    return "\n".join(output_list)


def generate_attendance_summary_excel_format_text(
    attendance_list: AttendanceList,
) -> str:
    """Generates the attendance summary in excel format."""
    output_list = []
    for line in attendance_list.details:
        output_list.append(line)
    output_list.append("")
    count = 0

    output_list.append("Regulars")
    for person in attendance_list.regulars:
        if person.status == PRESENT:
            output_list.append(f"{person.name}")
            count += 1
    for person in attendance_list.exco:
        output_list.append(f"{person}")
        count += 1

    output_list.append("")

    output_list.append("Non-Regulars")
    for person in attendance_list.non_regulars:
        if person.status == PRESENT:
            output_list.append(f"{person.name}")
            count += 1

    for person in attendance_list.standins:
        if person.status == PRESENT:
            output_list.append(f"{person.name}")
            count += 1

    output_list.append(f"\nTotal: {count}")

    return "\n".join(output_list)


async def display_edit_list(attendance_list: AttendanceList, update: Update) -> None:
    await build_edit_attendance_list_template(
        attendance_list, update.message.reply_text
    )


async def edit_to_edit_list(attendance_list, update) -> None:
    await build_edit_attendance_list_template(
        attendance_list, update.callback_query.edit_message_text
    )


def build_take_attendance_buttons(
    attendance_list: AttendanceList,
    max_rows: int = 20,
) -> List[List[List[InlineKeyboardButton]]]:
    """Builds the take attendance buttons that are displayed across
    multiple messages if necessary."""
    inline_keyboards = generate_inline_keyboard_list_for_edit_list(attendance_list)
    chunks = []
    current = []

    for row in inline_keyboards:
        if len(current) >= max_rows:
            chunks.append(current)
            current = []
        current.append(row)

    if current:
        chunks.append(current)

    return chunks


def build_take_attendance_text() -> str:
    """Builds the take attendance text."""
    return "Please take attendance using the buttons below."


async def build_edit_attendance_list_template(attendance_list, fn) -> int:
    """Builds the edit attendance list template."""
    summary_text = build_attendance_list_summary_text(attendance_list)
    inlinekeyboard = generate_inline_keyboard_list_for_edit_list(attendance_list)
    await fn(
        summary_text + "\n\nPlease edit using the buttons below\\.",
        reply_markup=InlineKeyboardMarkup(inlinekeyboard),
        parse_mode="MarkdownV2",
    )


def generate_inline_keyboard_list_for_edit_list(
    attendance_list: AttendanceList,
) -> List[List[InlineKeyboardButton]]:
    inlinekeyboard = []
    lists = [
        attendance_list.non_regulars,
        attendance_list.regulars,
        attendance_list.standins,
    ]
    titles = ["NON REGULARS", "REGULARS", "STANDINS"]
    for index, lst in enumerate(lists):
        if len(lst) > 0:
            inlinekeyboard.append(
                [InlineKeyboardButton(titles[index], callback_data=DO_NOTHING)]
            )
        for index, person in enumerate(lst):
            inline_list = [
                InlineKeyboardButton(
                    f"{index+1}. {status_map[person.status]} {person.name}",
                    callback_data=DO_NOTHING,
                ),
                InlineKeyboardButton(
                    PRESENT_SYMBOL,
                    callback_data=encode_mark_attendance(
                        person.id, attendance_list.id, PRESENT
                    ),
                ),
                InlineKeyboardButton(
                    ABSENT_SYMBOL,
                    callback_data=encode_mark_attendance(
                        person.id, attendance_list.id, ABSENT
                    ),
                ),
            ]
            inlinekeyboard.append(inline_list)
    return inlinekeyboard
