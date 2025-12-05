"""Service class for handling poll-related operations."""

import logging
from datetime import datetime, timedelta

from model.event_poll import EventPoll
from repositories.poll_repository import PollRepository
from util.constants import Membership
from util.errors import PollNotFoundError


class PollService:
    """
    Service class for handling poll-related operations.
    """

    def __init__(self, poll_repository: PollRepository):
        # Enable logging
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        # set higher logging level for httpx to avoid all GET and POST requests being logged
        logging.getLogger("httpx").setLevel(logging.WARNING)

        self.logger = logging.getLogger(__name__)
        self.poll_repository = poll_repository

    def save_event_polls(self, polls_data: list) -> list:
        """
        Adds multiple event polls to the repository.
        Polls data is in the format of list of lists with start_time, end_time, details.
        Returns list of poll IDs.
        """
        self.logger.info("Adding %d event polls.", len(polls_data))
        polls = [EventPoll(*poll_data, [100, 100]) for poll_data in polls_data]
        return self.poll_repository.insert_event_polls(polls)

    def update_poll_group_id(self, polls_ids: list, poll_group_id: str):
        """
        Updates the poll group ID for multiple polls.
        """
        self.logger.info(
            "Updating poll group ID to %s for %d polls.", poll_group_id, len(polls_ids)
        )
        self.poll_repository.update_poll_group_id(polls_ids, poll_group_id)

    def get_event_polls(self, polls_ids: list) -> list:
        """
        Gets multiple event polls by their IDs.
        """
        try:
            return self.poll_repository.get_event_polls(polls_ids)
        except PollNotFoundError as e:
            self.logger.error("Error getting event polls: %s", e)
            return []

    def get_event_poll(self, poll_id: str) -> EventPoll | None:
        """
        Gets a single event poll by its ID.
        """
        try:
            return self.poll_repository.get_event_poll(poll_id)
        except PollNotFoundError as e:
            self.logger.error("Error getting event poll: %s", e)
            return None

    def set_person_in_poll(
        self, poll_id: str, username: str, membership: Membership, is_sign_up: bool
    ) -> EventPoll | None:
        """
        Sets a person's sign-up status in a poll. Returns the poll if successful, None otherwise.
        """
        self.logger.info(
            "Setting sign-up status for user %s in poll %s to %s.",
            username,
            poll_id,
            is_sign_up,
        )
        try:
            poll = self.poll_repository.get_event_poll(poll_id)
        except PollNotFoundError as e:
            self.logger.warning("Error setting person in poll: %s", e)
            return None
        is_changed = poll.is_person_status_changed(username, membership, is_sign_up)
        if not is_changed:
            self.logger.info(
                "No change in sign-up status for user %s in poll %s.", username, poll_id
            )
            return poll
        field = membership.to_db_representation()
        if is_sign_up:
            self.poll_repository.add_person_to_poll(poll_id, username, field)
        else:
            self.poll_repository.remove_person_from_poll(poll_id, username, field)

        return poll

    def save_next_polls(self, polls: list):
        """Saves the next week's polls based on the given polls."""
        new_polls = []
        for poll in polls:
            new_start_time = datetime.fromisoformat(poll.start_time) + timedelta(
                weeks=1
            )
            new_start_time = new_start_time.isoformat()
            new_end_time = datetime.fromisoformat(poll.end_time) + timedelta(weeks=1)
            new_end_time = new_end_time.isoformat()
            new_poll = EventPoll(
                new_start_time,
                new_end_time,
                poll.details,
                poll.allocations,
                is_active=poll.is_active,
            )
            new_polls.append(new_poll)
        new_ids = self.poll_repository.insert_event_polls(new_polls)
        for i, poll in enumerate(new_polls):
            poll.insert_id(new_ids[i])
        return new_polls

    def delete_polls(self, poll_ids: list):
        """Deletes multiple polls by their IDs."""
        return self.poll_repository.delete_event_polls(poll_ids)

    def set_active_status(self, poll_id: str, membership: Membership, is_active: bool):
        """Sets the active status for a specific membership in an event poll."""
        self.poll_repository.set_active_status(poll_id, membership, is_active)
        return self.get_event_poll(poll_id)
