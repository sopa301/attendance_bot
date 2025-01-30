from util.constants import *

# For encoding data into strings of up to 64 characters to be stored
# in the callback data of inline keyboard buttons. We separate by
# inline queries and callback queries because they don't have the 
# same handlers, so we can reuse some encoding functions.

DO_NOTHING = "."  # For non-interactive buttons
DO_NOTHING_REGEX_STRING = "^.$"

## Inline Queries

# Publish polls
PUBLISH_POLL_REGEX_STRING = "^p_"
def encode_publish_poll(poll_id: str) -> str:
    return f"p_{poll_id}"

def decode_publish_poll_query(query: str) -> str:
    return query.split("_")[1]

## Callback Queries

# Generate next week's poll
GENERATE_NEXT_POLL_REGEX_STRING = "^g_"
def encode_generate_next_poll(poll_group_id: str) -> str:
    return f"g_{poll_group_id}"

def decode_generate_next_poll_callback(query: str) -> str:
    return query.split("_")[1]

# Manage poll groups
MANAGE_POLL_GROUPS_REGEX_STRING = "^mg_"
def encode_manage_poll_groups(poll_group_id: str) -> str:
    return f"mg_{poll_group_id}"

def decode_manage_poll_groups_callback(query: str) -> str:
    return query.split("_")[1]

# Manage active polls
MANAGE_ACTIVE_POLLS_REGEX_STRING = "^m_"

def encode_manage_active_polls(poll_group_id: str) -> str:
    return f"m_{poll_group_id}"

def decode_manage_active_polls_callback(query: str) -> str:
    return query.split("_")[1]

# Set poll active status
SET_POLL_ACTIVE_STATUS_REGEX_STRING = "^sp_"
def encode_set_poll_active_status(poll_id: str, is_active: bool) -> str:
    return f"sp_{poll_id}_{1 if is_active else 0}" # 1 for True, 0 for False

def decode_set_poll_active_status_callback(query: str) -> tuple:
    poll_id, is_active = query.split("_")[1:]
    return poll_id, bool(int(is_active))

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
POLL_VOTING_REGEX_STRING = "^v_"
def encode_poll_voting(poll_id: str, membership: Membership, is_sign_up: bool) -> str:
    return f"v_{membership.value}_{poll_id}_{1 if is_sign_up else 0}" # 1 for True, 0 for False

def decode_poll_voting_callback(query: str) -> tuple:
    membership, poll_id, is_sign_up = query.split("_")[1:]
    return poll_id, Membership(int(membership)), bool(int(is_sign_up))

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