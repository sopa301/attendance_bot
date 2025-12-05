"""TODO: Migrate these to the views folder as they are text templates."""

from util import ABSENT_SYMBOL, CANCELLATION_SYMBOL, PRESENT_SYMBOL

START_TEXT = (
    "Hi! I am the attendance bot. Please click:\n"
    + "/new_poll to create a new weekly poll\n"
    + "/attendance to manage attendance for an event\n"
    + "/polls to manage your polls\n"
    + "/info to get information about this bot\n"
    + "/cancel to cancel the conversation"
)

INFO_TEXT = (
    "This bot is designed to help you manage your weekly events"
    " between a regular and non-regular chat. "
    "You can create a new poll for your event, take attendance,"
    " and view the results of the poll. "
    "To get started, click /new_poll to create a new poll, /attendance"
    " to start taking attendance for the upcoming event, "
    "or /polls to manage your polls."
)

POLL_GROUP_MANAGEMENT_TEXT = (
    "Click 'Publish Poll' to publish the poll to a group.\n"
    "Click 'Update Results' to view the latest results.\n"
    "Click 'Manage Active Events' to set the viewable status of events.\n"
    "Click 'Generate Next Week's Poll' to generate a new poll for the"
    " next week with the same details and time.\n"
    "Click 'Delete Poll' to delete the poll."
)

CANCEL_TEXT = "Bye!"

ABSENT, PRESENT, LAST_MINUTE_CANCELLATION = range(3)

status_map = [ABSENT_SYMBOL, PRESENT_SYMBOL, CANCELLATION_SYMBOL]

POLL_GROUP_TEMPLATE = (
    "Example: PB for week 1. Attendance is on a first come first serve basis!"
)

DETAILS_TEMPLATE = "Example: USC Multipurpose Courts 16 & 17. Max 24 people"

DATE_FORMAT_TEMPLATE = (
    "Format should be in dd/mm/YYYY,HH:MM.\nExample: 01/05/2025,10:30"
)


def escape_markdown_characters(text: str) -> str:
    characters = [
        "\\",
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]
    for character in characters:
        text = text.replace(character, f"\\{character}")
    return text
