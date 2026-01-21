"""Unit tests for the PollService class."""

# pylint: disable=missing-function-docstring, import-error
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from model import EventPoll
from service import PollService
from util import Membership, PollNotFoundError


class PollServiceTest(unittest.TestCase):
    """Unit tests for the PollService class."""

    def setUp(self):
        self.repo = MagicMock()
        self.ban_service = MagicMock()
        self.ban_service.get_ban_duration.return_value = 0
        self.ban_service.is_user_banned.return_value = False
        self.service = PollService(self.repo, self.ban_service)

    def test_save_event_polls(self):
        polls_data = [
            ["2025-01-01T10:00", "2025-01-01T12:00", "A"],
            ["2025-01-02T10:00", "2025-01-02T12:00", "B"],
        ]

        self.repo.insert_event_polls.return_value = ["id1", "id2"]

        result = self.service.save_event_polls(polls_data)

        self.assertEqual(result, ["id1", "id2"])
        self.repo.insert_event_polls.assert_called_once()
        # Ensure EventPoll was created correctly
        created = self.repo.insert_event_polls.call_args[0][0]
        self.assertEqual(len(created), 2)
        self.assertIsInstance(created[0], EventPoll)

    def test_update_poll_group_id(self):
        self.service.update_poll_group_id(["id1"], "group123")
        self.repo.update_poll_group_id.assert_called_once_with(["id1"], "group123")

    def test_get_event_polls_success(self):
        polls = [MagicMock(), MagicMock()]
        self.repo.get_event_polls.return_value = polls

        result = self.service.get_event_polls(["id1", "id2"])
        self.assertEqual(result, polls)

    def test_get_event_polls_not_found(self):
        test_id = "id1"
        self.repo.get_event_polls.side_effect = PollNotFoundError(test_id)

        with self.assertRaises(PollNotFoundError):
            self.service.get_event_polls([test_id])

    def test_get_event_poll_success(self):
        poll = MagicMock()
        self.repo.get_event_poll.return_value = poll

        result = self.service.get_event_poll("id1")
        self.assertEqual(result, poll)

    def test_get_event_poll_not_found(self):
        test_id = "id1"
        self.repo.get_event_poll.side_effect = PollNotFoundError(test_id)

        with self.assertRaises(PollNotFoundError):
            self.service.get_event_poll(test_id)

    def test_set_person_in_poll_no_change(self):
        poll = MagicMock()
        poll.is_person_status_changed.return_value = False
        membership = MagicMock()
        membership.to_db_representation.return_value = "db_field"

        self.repo.get_event_poll.return_value = poll

        result = self.service.set_person_in_poll("id1", "john", membership, True, "1")
        self.assertEqual(result, poll)
        self.repo.add_person_to_poll.assert_not_called()

    def test_set_person_in_poll_add(self):
        poll = MagicMock()
        poll.is_person_status_changed.return_value = True
        membership = MagicMock()
        membership.to_db_representation.return_value = "db_field"

        self.repo.get_event_poll.return_value = poll

        result = self.service.set_person_in_poll("id1", "john", membership, True, "1")

        self.repo.add_person_to_poll.assert_called_once_with("id1", "john", "db_field")
        self.assertEqual(result, poll)

    def test_set_person_in_poll_remove(self):
        poll = MagicMock()
        poll.is_person_status_changed.return_value = True
        membership = MagicMock()
        membership.to_db_representation.return_value = "db_field"

        self.repo.get_event_poll.return_value = poll

        result = self.service.set_person_in_poll("id1", "john", membership, False, "1")

        self.repo.remove_person_from_poll.assert_called_once_with(
            "id1", "john", "db_field"
        )
        self.assertEqual(result, poll)

    def test_set_person_in_poll_not_found(self):
        test_id = "id1"
        self.repo.get_event_poll.side_effect = PollNotFoundError(test_id)
        membership = MagicMock()

        with self.assertRaises(PollNotFoundError):
            self.service.set_person_in_poll(test_id, "john", membership, True, "1")

    def test_save_next_polls(self):
        base_poll = EventPoll(
            "2025-01-01T10:00",
            "2025-01-01T12:00",
            "details",
            [100, 100],
            is_active=True,
        )

        self.repo.insert_event_polls.return_value = ["new1"]

        result = self.service.save_next_polls([base_poll])

        self.assertEqual(len(result), 1)
        new_poll = result[0]

        self.assertEqual(
            new_poll.start_time,
            (
                datetime.fromisoformat(base_poll.start_time) + timedelta(weeks=1)
            ).isoformat(),
        )
        self.assertEqual(
            new_poll.end_time,
            (
                datetime.fromisoformat(base_poll.end_time) + timedelta(weeks=1)
            ).isoformat(),
        )

        self.repo.insert_event_polls.assert_called_once()

    def test_delete_polls(self):
        self.service.delete_polls(["id1", "id2"])
        self.repo.delete_event_polls.assert_called_once_with(["id1", "id2"])

    def test_set_active_status(self):
        poll = MagicMock()
        self.repo.get_event_poll.return_value = poll

        result = self.service.set_active_status("id1", Membership.NON_REGULAR, True)

        self.repo.set_active_status.assert_called_once()
        self.assertEqual(result, poll)


if __name__ == "__main__":
    unittest.main()
