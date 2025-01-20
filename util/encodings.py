# For encoding data into strings of up to 64 characters to be stored
# in the callback data of inline keyboard buttons. We separate by
# inline queries and callback queries because they don't have the 
# same handlers, so we can reuse some encoding functions.

# NON_REGULAR = "nr"
# REGULAR = "r"

## Inline Queries

# Publish non_regular polls
PUBLISH_NON_REGULAR_POLL_REGEX_STRING = "^nr_"
def encode_publish_non_regular_poll(poll_id: str) -> str:
    return f"nr_{poll_id}"

# Publish regular polls
PUBLISH_REGULAR_POLL_REGEX_STRING = "^r_"
def encode_publish_regular_poll(poll_id: str) -> str:
    return f"r_{poll_id}"

def decode_publish_poll_query(query: str) -> tuple:
    poll_group_id = query.split("_")[1]
    if query.startswith("nr"):
        poll_type = "nr"
    elif query.startswith("r"):
        poll_type = "r"
    else:
        raise ValueError("Invalid query type: " + query)
    return poll_group_id, poll_type

## Callback Queries

# Update poll results
UPDATE_POLL_RESULTS_REGEX_STRING = "^u_"
def encode_update_poll_results(poll_id: str) -> str:
    return f"u_{poll_id}"

def decode_update_poll_results_callback(query: str) -> str:
    return query.split("_")[1]

# Delete poll
DELETE_POLL_REGEX_STRING = "^d_"
def encode_delete_poll(poll_id: str) -> str:
    return f"d_{poll_id}"

def decode_delete_poll_callback(query: str) -> str:
    return query.split("_")[1]

# Poll voting
def encode_poll_voting(poll_id: int, poll_type: str, index: int) -> str:
    return f"p_{poll_type}_{poll_id}_{index}"

def decode_poll_voting_callback(query: str) -> tuple:
    poll_type, poll_id, index = query.split("_")[1:]
    return poll_id, poll_type, int(index)

# View attendance lists
def encode_view_attendance_list(a_l_id: str) -> str:
    return "va_" + a_l_id

def decode_view_attendance_list(encoded: str) -> str:
    return encoded.split("_")[1]

# Mark attendance
MARK_ATTENDANCE_REGEX_STRING = "^a_"
def encode_mark_attendance(user_id: str, a_l_id: str) -> str:
    return "a_" + user_id + "_" + a_l_id

def decode_mark_attendance(encoded: str) -> tuple:
    return encoded.split("_")[1:]

# View summary
VIEW_SUMMARY_REGEX_STRING = "^s_"
def encode_view_attendance_summary(a_l_id: str) -> str:
    return "s_" + a_l_id

def decode_view_attendance_summary(encoded: str) -> str:
    return encoded.split("_")[1]
