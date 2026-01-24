"""
For encoding data into strings of up to 64 characters to be stored
in the callback data of inline keyboard buttons. We separate by
inline queries and callback queries because they don't have the
same handlers, so we can reuse some encoding functions.
"""

from .constants import Membership

DO_NOTHING = "."  # For non-interactive buttons
DO_NOTHING_REGEX_STRING = "^.$"

## Inline Queries

# Publish polls
PUBLISH_POLL_REGEX_STRING = "^p_"


def encode_publish_poll(poll_id: str) -> str:
    """Encode poll ID for publishing a poll."""
    return f"p_{poll_id}"


def decode_publish_poll_query(query: str) -> str:
    """Decode poll ID from publishing a poll query."""
    lst = query.split("_")
    if len(lst) != 2:
        return ""
    return lst[1]


## Callback Queries

# Generate next week's poll
GENERATE_NEXT_POLL_REGEX_STRING = "^g_"


def encode_generate_next_poll(poll_group_id: str) -> str:
    """Encode poll group ID for generating next week's poll."""
    return f"g_{poll_group_id}"


def decode_generate_next_poll_callback(query: str) -> str:
    """Decode poll group ID from generating next week's poll callback."""
    return query.split("_")[1]


# Manage poll groups
MANAGE_POLL_GROUPS_REGEX_STRING = "^mg_"


def encode_manage_poll_groups(poll_group_id: str) -> str:
    """Encode poll group ID for managing poll groups."""
    return f"mg_{poll_group_id}"


def decode_manage_poll_groups_callback(query: str) -> str:
    """Decode poll group ID from managing poll groups callback."""
    return query.split("_")[1]


# Manage active polls
MANAGE_ACTIVE_POLLS_REGEX_STRING = "^m_"


def encode_manage_active_polls(poll_group_id: str) -> str:
    """Encode poll group ID for managing active polls."""
    return f"m_{poll_group_id}"


def decode_manage_active_polls_callback(query: str) -> str:
    """Decode poll group ID from managing active polls callback."""
    return query.split("_")[1]


# Set poll active status
SET_POLL_ACTIVE_STATUS_REGEX_STRING = "^sp_"


def encode_set_poll_active_status(
    poll_id: str, membership: Membership, is_active: bool
) -> str:
    """Encode poll ID, membership, and active status for setting poll active status."""
    return f"sp_{poll_id}_{membership.value}_{1 if is_active else 0}"  # 1 for True, 0 for False


def decode_set_poll_active_status_callback(query: str) -> tuple:
    """Decode poll ID, membership, and active status from setting poll active status callback."""
    poll_id, membership, is_active = query.split("_")[1:]
    return poll_id, Membership.from_data_string(membership), bool(int(is_active))


# Update poll results
UPDATE_POLL_RESULTS_REGEX_STRING = "^u_"


def encode_update_poll_results(poll_id: str) -> str:
    """Encode poll ID for updating poll results."""
    return f"u_{poll_id}"


def decode_update_poll_results_callback(query: str) -> str:
    """Decode poll ID from updating poll results callback."""
    return query.split("_")[1]


# Delete poll
DELETE_POLL_REGEX_STRING = "^d_"


def encode_delete_poll(poll_id: str) -> str:
    """Encode poll ID for deleting a poll."""
    return f"d_{poll_id}"


def decode_delete_poll_callback(query: str) -> str:
    """Decode poll ID from deleting a poll callback."""
    return query.split("_")[1]


# Poll voting
POLL_VOTING_REGEX_STRING = "^v_"


def encode_poll_voting(
    poll_id: str, membership: Membership, is_sign_up: bool, pollmaker_id: str
) -> str:
    """Encode poll ID, membership, sign-up status and pollmaker ID for poll voting."""
    return f"v_{membership.value}_{poll_id}_{1 if is_sign_up else 0}_{pollmaker_id}"  # 1 for True, 0 for False


def decode_poll_voting_callback(query: str) -> tuple[str, Membership, bool, str | None]:
    """Decode poll ID, membership, sign-up status and pollmaker ID from poll voting callback."""
    results = query.split("_")[1:]
    if len(results) == 3:
        return (
            results[1],
            Membership.from_data_string(results[0]),
            bool(int(results[2])),
            None,
        )
    return (
        results[1],
        Membership.from_data_string(results[0]),
        bool(int(results[2])),
        results[3],
    )


# View attendance lists
VIEW_ATTENDANCE_LISTS_REGEX_STRING = "^va_"


def encode_view_attendance_list(a_l_id: str) -> str:
    """Encode attendance list ID for viewing attendance lists."""
    return "va_" + a_l_id


def decode_view_attendance_list(encoded: str) -> str:
    """Decode attendance list ID from viewing attendance lists."""
    return encoded.split("_")[1]


# Mark attendance
MARK_ATTENDANCE_REGEX_STRING = "^a,"


def encode_mark_attendance(user_id: str, a_l_id: str, status: int) -> str:
    """Encode user ID, attendance list ID, and status for marking attendance."""
    return "a," + user_id + "," + a_l_id + "," + str(status)


def decode_mark_attendance(encoded: str) -> tuple:
    """Decode user ID, attendance list ID, and status from marking attendance."""
    data = encoded.split(",")[1:]
    data[2] = int(data[2])
    return tuple(data)


# View summary
VIEW_SUMMARY_REGEX_STRING = "^s_"


def encode_view_attendance_summary(a_l_id: str, with_refresh: bool = False) -> str:
    """Encode attendance list ID for viewing attendance summary."""
    return "s_" + a_l_id + ("_r" if with_refresh else "")


def decode_view_attendance_summary(encoded: str) -> tuple[str, bool]:
    """Decode attendance list ID from viewing attendance summary."""
    vals = encoded.split("_")
    return vals[1], len(vals) > 2 and vals[2] == "r"


# Manage attendance list
MANAGE_ATTENDANCE_LIST_REGEX_STRING = "^ma,"


def decode_manage_attendance_list(encoded: str) -> str:
    """Decode attendance list ID from managing attendance list callback."""
    return encoded.split(",")[1]


def encode_manage_attendance_list(s: str) -> str:
    """Encode attendance list ID for managing attendance list."""
    return "ma," + s


# View attendance tracking format
VIEW_ATTENDANCE_TRACKING_FORMAT_REGEX_STRING = "^atf_"


def encode_view_attendance_tracking_format(a_l_id: str) -> str:
    """Encode attendance list ID for viewing attendance tracking format."""
    return "atf_" + a_l_id


def decode_view_attendance_tracking_format(encoded: str) -> str:
    """Decode attendance list ID from viewing attendance tracking format."""
    return encoded.split("_")[1]


# Unban user
UNBAN_USER_REGEX_STRING = "^unb_"


def encode_unban_user(user_id: str) -> str:
    """Encode user ID for unbanning a user."""
    return "unb_" + user_id


def decode_unban_user(encoded: str) -> str:
    """Decode user ID from unbanning a user."""
    return encoded.split("_")[1]
