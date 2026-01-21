"""Views for poll-related bot messages and options."""

from typing import List

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.constants import ParseMode

from src.model import EventPoll, PollGroup
from src.util import (
    ACTIVE_SYMBOL,
    DATE_FORMAT_TEMPLATE,
    DETAILS_TEMPLATE,
    DO_NOTHING,
    DROP_OUT_SYMBOL,
    INACTIVE_SYMBOL,
    POLL_GROUP_MANAGEMENT_TEXT,
    POLL_GROUP_TEMPLATE,
    SIGN_UP_SYMBOL,
    Membership,
    encode_delete_poll,
    encode_generate_next_poll,
    encode_manage_active_polls,
    encode_manage_poll_groups,
    encode_poll_voting,
    encode_publish_poll,
    encode_set_poll_active_status,
    encode_update_poll_results,
    escape_markdown_characters,
    format_dt_string,
)


def build_no_polls_message() -> str:
    """Builds the bot message when there are no polls."""
    return "You have no polls."


def build_select_poll_group_message() -> str:
    """Builds the bot message for selecting a poll group."""
    return "Please select a poll to view."


def build_select_poll_group_options(poll_groups: List[PollGroup]) -> list:
    """Builds an inline keyboard for selecting poll groups."""
    inline_keyboard = []
    for group in poll_groups:
        inline_keyboard.append(
            [
                InlineKeyboardButton(
                    group.name, callback_data=encode_manage_poll_groups(group.id)
                )
            ]
        )
    return inline_keyboard


def build_poll_group_not_found_message() -> str:
    """Builds the bot message when a poll group is not found."""
    return "Poll not found."


def build_poll_group_management_message(poll_group: PollGroup) -> str:
    """Builds the bot message for managing a specific poll group."""
    return f"Viewing {poll_group.name}\n\n" + POLL_GROUP_MANAGEMENT_TEXT


def build_poll_group_management_options(poll_group: PollGroup) -> list:
    """Builds an inline keyboard for managing a specific poll group."""
    group_id = poll_group.id
    return [
        [
            InlineKeyboardButton(
                "Publish Poll", switch_inline_query=encode_publish_poll(group_id)
            )
        ],
        [
            InlineKeyboardButton(
                "Update Results", callback_data=encode_update_poll_results(group_id)
            )
        ],
        [
            InlineKeyboardButton(
                "Manage Active Events",
                callback_data=encode_manage_active_polls(group_id),
            )
        ],
        [
            InlineKeyboardButton(
                "Generate Next Week's Poll",
                callback_data=encode_generate_next_poll(group_id),
            )
        ],
        [
            InlineKeyboardButton(
                "Delete Poll", callback_data=encode_delete_poll(group_id)
            )
        ],
    ]


def build_new_poll_group_message() -> str:
    """Builds the bot message for creating a new poll group."""
    return "What would you like to call this poll?\n" + POLL_GROUP_TEMPLATE


def build_get_number_of_events_message() -> str:
    """Builds the bot message for getting the number of events."""
    return "Please input the number of events you want to poll for."


def build_get_details_of_event_message(event_number: int) -> str:
    """Builds the bot message for getting the details of an event."""
    return f"Please input the details of event {event_number}.\n" + DETAILS_TEMPLATE


def build_invalid_number_of_events_message() -> str:
    """Builds the bot message for invalid number of events input."""
    return "Please input a valid number that is at least 1."


def build_get_start_time_message() -> str:
    """Builds the bot message for getting the start time of an event."""
    return "Please input the start time of the event.\n" + DATE_FORMAT_TEMPLATE


def build_invalid_start_time_message(error: str) -> str:
    """Builds the bot message for invalid start time input."""
    return (
        f"Unsuccessful: {error}. Please input start time again.\n"
        + DATE_FORMAT_TEMPLATE
    )


def build_get_end_time_message() -> str:
    """Builds the bot message for getting the end time of an event."""
    return "Please input the end time of the event.\n" + DATE_FORMAT_TEMPLATE


def build_invalid_end_time_message(error: str) -> str:
    """Builds the bot message for invalid end time input."""
    return (
        f"Unsuccessful: {error}. Please input end time again.\n" + DATE_FORMAT_TEMPLATE
    )


def build_end_time_before_start_time_message() -> str:
    """Builds the bot message when end time is before start time."""
    return (
        "Unsuccessful: end time given is before start time. Please input end time again.\n"
        + DATE_FORMAT_TEMPLATE
    )


def build_voting_buttons(
    polls: List[EventPoll], membership: Membership, pollmaker_id: str
) -> list:
    """Generates inline keyboard buttons for voting on polls."""
    keyboard = []
    for _, poll in enumerate(polls):
        if bool(poll.is_active[membership.value]):
            keyboard.append(
                [InlineKeyboardButton(f"{poll.get_title()}", callback_data=DO_NOTHING)]
            )
            keyboard.append(
                [
                    InlineKeyboardButton(
                        SIGN_UP_SYMBOL,
                        callback_data=encode_poll_voting(
                            poll.id, membership, True, pollmaker_id
                        ),
                    ),
                    InlineKeyboardButton(
                        DROP_OUT_SYMBOL,
                        callback_data=encode_poll_voting(
                            poll.id, membership, False, pollmaker_id
                        ),
                    ),
                ]
            )

    return keyboard


def build_publish_options(
    poll_group: PollGroup, polls: List[EventPoll]
) -> List[InlineQueryResultArticle]:
    """Generates inline keyboard buttons for publishing a poll group."""
    lst = []
    for membership in Membership:
        lst.append(
            build_publish_option(poll_group, polls, membership, poll_group.owner_id)
        )
    return lst


def build_publish_option(
    poll_group: PollGroup,
    polls: List[EventPoll],
    membership: Membership,
    pollmaker_id: str,
) -> InlineQueryResultArticle:
    """
    Generates an inline query result article for publishing a poll group.
    Contains the poll message text and voting buttons for each poll in the poll group.
    """
    reply_markup = InlineKeyboardMarkup(
        build_voting_buttons(polls, membership, pollmaker_id)
    )
    return InlineQueryResultArticle(
        id=poll_group.id + str(membership.value),
        title=f"({membership.to_representation()}) {poll_group.name}",
        input_message_content=InputTextMessageContent(
            generate_poll_group_text(poll_group, polls, membership),
            parse_mode=ParseMode.MARKDOWN_V2,
        ),
        reply_markup=reply_markup,
    )


def build_ask_user_to_register_username_message() -> str:
    """Builds the bot message to ask user to register their username."""
    return (
        "To participate in polls, please set a Telegram username in your "
        "Telegram settings and try again."
    )


def build_poll_unable_to_vote_message() -> str:
    """Builds the bot message when unable to vote in a poll."""
    return "Poll has been closed or does not exist."


def build_user_banned_message(duration: int) -> str:
    """Builds the bot message when a user is banned."""
    units = [
        ("day", 86400),
        ("hour", 3600),
        ("minute", 60),
    ]

    parts = []
    remaining = duration

    for name, seconds in units:
        value, remaining = divmod(remaining, seconds)
        if value:
            parts.append(f"{value} {name}{'s' if value != 1 else ''}")

    if not parts:
        return "You are banned from voting."

    return f"You are banned from voting for {', '.join(parts)}."


def build_poll_vote_confirmation_message(poll_title: str, is_sign_up: bool) -> str:
    """Builds the bot message confirming a vote in a poll."""
    action = "signed up for" if is_sign_up else "dropped out of"
    return f"You have successfully {action} the poll: {poll_title}."


# To be used with Markdownv2
def generate_poll_group_text(
    poll_group: PollGroup, polls: List[EventPoll], membership: Membership
) -> str:
    """Generates the text that shows the poll results after a user votes."""
    title = escape_markdown_characters(poll_group.name)
    membership_of_poll = membership.to_representation()
    membership_of_poll = escape_markdown_characters(f"({membership_of_poll})")
    poll_body = [f"*{title} {membership_of_poll}*", ""]
    for i, poll in enumerate(polls):
        if not bool(poll.is_active[membership.value]):
            continue
        poll_header = generate_poll_details_template(poll, markdown_v2=True)
        poll_body.extend(poll_header)
        lst = poll.get_people_list_by_membership(membership)
        for j, person in enumerate(lst):
            poll_body.append(f"{j+1}\\. {escape_markdown_characters(person)}")
        if i < len(polls) - 1:
            poll_body.append("\n")
    poll_body = "\n".join(poll_body)
    return poll_body


def generate_poll_details_template(poll: EventPoll, markdown_v2=True) -> list:
    """Generates the poll details template for a given poll."""
    [start_date, start_time] = format_dt_string(poll.start_time)
    [_, end_time] = format_dt_string(poll.end_time)
    if markdown_v2:
        out = []
        out.append(f"*__Date\\: {escape_markdown_characters(start_date)}__*")
        out.append(
            f"Time\\: {escape_markdown_characters(start_time.lower())}"
            f" \\- {escape_markdown_characters(end_time.lower())}"
        )
        out.append(f"{escape_markdown_characters(poll.details)}")
        return out
    return list(
        (
            f"Date: {start_date}",
            f"Time: {start_time.lower()} - {end_time.lower()}",
            f"{poll.details}",
        )
    )


def build_cannot_generate_next_poll_message() -> str:
    """Builds the bot message when unable to generate next week's poll."""
    return "Unable to generate next week's poll as the poll group has been deleted."


def build_cannot_manage_active_polls_message() -> str:
    """Builds the bot message when unable to manage active polls."""
    return "Unable to manage active polls as the poll group has been deleted."


def build_manage_active_polls_message() -> str:
    """Builds the bot message for managing active polls."""
    return (
        "You can activate/deactivate polls here."
        " Note that it also affects polls already published."
    )


# To be used with MarkdownV2
def build_poll_maker_overview_text(poll_group: PollGroup, polls: list) -> str:
    """Shows all poll results to the poll maker."""
    out = [
        generate_poll_group_text(poll_group, polls, Membership.NON_REGULAR),
        escape_markdown_characters("-------------------------"),
        generate_poll_group_text(poll_group, polls, Membership.REGULAR),
    ]
    return "\n".join(out)


def build_cannot_update_poll_results_message() -> str:
    """Builds the bot message when unable to update poll results."""
    return "Unable to update poll results as the poll group has been deleted."


def get_active_status_representation(poll: EventPoll, membership: Membership):
    """Gets the active status representation of a poll for a given membership in
    the manage active polls panel."""
    return ACTIVE_SYMBOL if poll.is_active[membership.value] else INACTIVE_SYMBOL


def generate_manage_active_polls_buttons(
    polls: List[EventPoll], poll_group_id: str
) -> List[List[InlineKeyboardButton]]:
    """Generates inline keyboard buttons for managing active polls."""
    keyboard = []
    for poll in polls:
        keyboard.append(
            [InlineKeyboardButton(f"{poll.get_title()}", callback_data=DO_NOTHING)]
        )
        for membership in Membership:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"{membership.to_representation()}"
                        f"{get_active_status_representation(poll, membership)}",
                        callback_data=DO_NOTHING,
                    ),
                    InlineKeyboardButton(
                        "Unhide",
                        callback_data=encode_set_poll_active_status(
                            poll.id, membership, True
                        ),
                    ),
                    InlineKeyboardButton(
                        "Hide",
                        callback_data=encode_set_poll_active_status(
                            poll.id, membership, False
                        ),
                    ),
                ]
            )
    keyboard.append(
        [
            InlineKeyboardButton(
                "Back", callback_data=encode_manage_poll_groups(poll_group_id)
            )
        ]
    )
    return keyboard


def build_poll_deleted_message(new_delete: bool) -> str:
    """Builds the bot message when a poll has been deleted."""
    if new_delete:
        return "Poll deleted."
    return "Poll has been deleted."


def build_poll_not_found_message() -> str:
    """Builds the bot message when a poll is not found."""
    return "Poll not found."
