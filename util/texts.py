REQUEST_FOR_ATTENDANCE_LIST_INPUT = "Please input the list in the following format: \n\nPickleball session (date)\n\nNon regulars\n1. ...\n2. ...\n\nRegulars\n1. ...\n2. ...\n\nStandins\n1. ...\n2. ...\n\nExco\n...\n..."

ABSENT, PRESENT, LAST_MINUTE_CANCELLATION = range(3)

PRESENT_SYMBOL = "✅"
ABSENT_SYMBOL = "❌"

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
