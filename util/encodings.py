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
POLL_VOTING_REGEX_STRING = "^p_"
def encode_poll_voting(poll_id: int, poll_type: str, index: int) -> str:
    return f"p_{poll_type}_{poll_id}_{index}"

def decode_poll_voting_callback(query: str) -> tuple:
    poll_type, poll_id, index = query.split("_")[1:]
    return poll_id, poll_type, int(index)

# View attendance lists
VIEW_ATTENDANCE_LISTS_REGEX_STRING = "^va_"
def encode_view_attendance_list(a_l_id: str) -> str:
    return "va_" + a_l_id

def decode_view_attendance_list(encoded: str) -> str:
    return encoded.split("_")[1]

# Mark attendance
MARK_ATTENDANCE_REGEX_STRING = "^a,"
def encode_mark_attendance(user_id: str, a_l_id: str, status: int) -> str:
    return "a," + user_id + "," + a_l_id + "," + str(status)

def decode_mark_attendance(encoded: str) -> tuple:
    data = encoded.split(",")[1:]
    data[2] = int(data[2])
    return tuple(data)

# View summary
VIEW_SUMMARY_REGEX_STRING = "^s_"
def encode_view_attendance_summary(a_l_id: str) -> str:
    return "s_" + a_l_id

def decode_view_attendance_summary(encoded: str) -> str:
    return encoded.split("_")[1]

# Manage attendance list
MANAGE_ATTENDANCE_LIST_REGEX_STRING = "^ma,"
def decode_manage_attendance_list(encoded: str) -> str:
    return encoded.split(",")[1]

def encode_manage_attendance_list(s: str) -> str:
    return "ma," + s

# # Select poll group for managing attendance
# SELECT_POLL_GROUP_MANAGE_REGEX_STRING = "^pgm,"
# def encode_select_poll_group_manage(group_id: str) -> str:
#     return "pgm," + group_id

# def decode_select_poll_group_manage(encoded: str) -> str:
#     return encoded.split(",")[1]

# # Select poll group for importing attendance list
# SELECT_POLL_GROUP_IMPORT_REGEX_STRING = "^pgi,"
# def encode_select_poll_group_import(group_id: str) -> str:
#     return "pgi," + group_id

# def decode_select_poll_group_import(encoded: str) -> str:
#     return encoded.split(",")[1]