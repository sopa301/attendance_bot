

START_TEXT = "Hi! I am the attendance bot. Please click:\n" \
        + "/new_poll to create a new weekly poll\n" \
        + "/attendance to manage attendance for an event\n" \
        + "/polls to manage your polls\n" \
        + "/info to get information about this bot\n" \
        + "/cancel to cancel the conversation" \

REQUEST_FOR_ATTENDANCE_LIST_INPUT_TEXT = "Please input the list in the following format: \n\nPickleball session (date)\n\nNon regulars\n1. ...\n2. ...\n\nRegulars\n1. ...\n2. ...\n\nStandins\n1. ...\n2. ...\n\nExco\n...\n..."

INFO_TEXT = "This bot is designed to help you manage your weekly events between a regular and non-regular chat. " \
        + "You can create a new poll for your event, take attendance, and view the results of the poll. " \
        + "To get started, click /new_poll to create a new poll, /attendance to start taking attendance for the upcoming event, " \
        + "or /polls to manage your polls."

CANCEL_TEXT = "Bye!"

ABSENT, PRESENT, LAST_MINUTE_CANCELLATION = range(3)

PRESENT_SYMBOL = "✅"
ABSENT_SYMBOL = "❌"

POLL_GROUP_TEMPLATE = "Template: PB for week 1. Attendance is on a first come first serve basis!"

DETAILS_TEMPLATE = "Template: USC Multipurpose Courts 16 & 17. Max 24 people"

DATE_FORMAT_TEMPLATE = "Format should be in dd/mm/YYYY,HH:MM.\n Template: 01/05/2025,10:30"

def generate_status_string(status: int, name: str, index: int) -> str:
    if status == ABSENT:
        return generate_absent_string(name, index)
    elif status == PRESENT:
        return generate_present_string(name, index)
    elif status == LAST_MINUTE_CANCELLATION:
        return generate_last_minute_cancellation_string(name, index)
    else:
        raise ValueError("Invalid status")

def escape_markdown_characters(text: str) -> str:
    characters = ["\\", "_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
    for character in characters:
        text = text.replace(character, f"\\{character}")
    return text

def generate_absent_string(absentee: str, index: int) -> str:
    absentee = escape_markdown_characters(absentee)
    return f"{index}\. {ABSENT_SYMBOL}{absentee}"

def generate_present_string(presentee: str, index: int) -> str:
    presentee = escape_markdown_characters(presentee)
    return f"{index}\. {PRESENT_SYMBOL}{presentee}"

def generate_last_minute_cancellation_string(cancellation: str, index: int) -> str:
    cancellation = escape_markdown_characters(cancellation)
    return f"~{index}\. {cancellation}~"
