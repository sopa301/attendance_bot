"""Service class for handling poll-group-related operations."""

import logging
from typing import List, Tuple

from telegram import User

from model.event_poll import EventPoll
from model.poll_group import PollGroup
from repositories.poll_group_repository import PollGroupRepository
from services.poll_service import PollService
from util.errors import PollGroupNotFoundError


class PollGroupService:
    """
    Service class for handling poll-group-related operations.
    """

    def __init__(
        self, poll_group_repository: PollGroupRepository, poll_service: PollService
    ):
        # Enable logging
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        # set higher logging level for httpx to avoid all GET and POST requests being logged
        logging.getLogger("httpx").setLevel(logging.WARNING)

        self._logger = logging.getLogger(__name__)
        self._poll_group_repository = poll_group_repository
        self._poll_service = poll_service

    def get_poll_groups(self, user: User | None) -> list:
        """Gets all poll groups owned by the user."""
        if user is None:
            self._logger.warning("Anonymous user tried to access poll groups.")
            return []
        self._logger.info("User %s requested to view their polls.", user.first_name)
        return self._poll_group_repository.get_poll_groups_by_owner_id(user.id)

    def get_poll_group(self, group_id: str, user: User | None) -> PollGroup | None:
        """Gets a poll group by its ID."""
        if user is None:
            self._logger.warning(
                "Anonymous user tried to access poll group with ID %s.", group_id
            )
            return None
        self._logger.info(
            "User %s requested poll group with ID %s.",
            user.first_name,
            group_id,
        )
        try:
            poll_group = self._poll_group_repository.get_poll_group(group_id)
            if poll_group.owner_id != user.id:
                self._logger.warning(
                    "User %s tried to access poll group with ID %s they do not own.",
                    user.first_name,
                    group_id,
                )
                return None
            return poll_group
        except PollGroupNotFoundError:
            self._logger.warning(
                "Poll group with ID %s not found for user %s.",
                group_id,
                user.first_name,
            )
            return None

    def create_poll_group(self, owner_id: int, name: str, polls_ids: List[str]) -> str:
        """Creates a new poll group and returns its ID."""
        self._logger.info(
            "Creating new poll group '%s' for user ID %d.", name, owner_id
        )
        poll_group = PollGroup(owner_id, name, polls_ids)
        return self._poll_group_repository.insert_poll_group(poll_group)

    def get_full_poll_group_details(
        self, group_id: str
    ) -> Tuple[PollGroup | None, List[EventPoll]]:
        """Gets full details of a poll group by its ID."""
        try:
            poll_group = self._poll_group_repository.get_poll_group(group_id)
        except PollGroupNotFoundError:
            return None, []
        polls = self._poll_service.get_event_polls(poll_group.get_poll_ids())

        return poll_group, polls

    def generate_next_poll_group(
        self, poll_group_id: str, new_poll_name: str
    ) -> Tuple[PollGroup | None, List[EventPoll]]:
        """Generates the next week's poll group and polls."""
        self._logger.info(
            "Generating next poll group for poll group ID %s.", poll_group_id
        )
        poll_group, polls = self.get_full_poll_group_details(poll_group_id)
        if poll_group is None:
            return None, []
        new_polls = self._poll_service.save_next_polls(polls)
        new_poll_ids = [poll.id for poll in new_polls]
        new_group = PollGroup(poll_group.owner_id, new_poll_name, new_poll_ids)
        group_id = self._poll_group_repository.insert_poll_group(new_group)
        self._poll_service.update_poll_group_id(new_poll_ids, group_id)
        new_group.insert_id(group_id)
        return new_group, new_polls

    def delete_poll_group(self, poll_group_id: str, user: User | None) -> bool:
        """Deletes a poll group and its associated polls."""
        if user is None:
            self._logger.warning(
                "Anonymous user tried to delete poll group with ID %s.", poll_group_id
            )
            return False
        self._logger.info(
            "User %s requested to delete poll group with ID %s.",
            user.first_name,
            poll_group_id,
        )
        try:
            poll_group = self._poll_group_repository.get_poll_group(poll_group_id)
            if poll_group.owner_id != user.id:
                self._logger.warning(
                    "User %s tried to delete poll group with ID %s they do not own.",
                    user.first_name,
                    poll_group_id,
                )
                return False
            # Delete associated polls
            self._poll_service.delete_polls(poll_group.get_poll_ids())
            # Delete the poll group
            self._poll_group_repository.delete_poll_group(poll_group_id)
            return True
        except PollGroupNotFoundError:
            self._logger.warning(
                "Poll group with ID %s not found for user %s.",
                poll_group_id,
                user.first_name,
            )
            return False
