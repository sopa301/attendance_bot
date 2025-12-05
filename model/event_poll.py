"""Model for event polls."""

from enum import Enum
from typing import List

from util.constants import Membership
from util.date_time import format_dt_string


class PollType(Enum):
    """Types of polls."""

    WEEKLY = 0
    ADHOC = 1


# TODO: figure out how to handle old poll messages when the poll group is deleted
# also handle the updating of all messages when a poll is updated
# also handle the updating of all messages after the week passes
class EventPoll:
    """Class representing an event poll."""

    def __init__(self, start_time, end_time, details, allocations, is_active=None):
        self.id = None
        self.start_time = start_time
        self.end_time = end_time
        self.regulars = []
        self.non_regulars = []
        self.details = details
        self.type = PollType.WEEKLY  # not used currently
        if is_active is None:
            self.is_active = [True, True]
        else:
            self.is_active = is_active
        self.allocations = allocations
        self.poll_group_id = None

    def get_title(self):
        """Builds the title string for the poll."""
        [start_date, start_time] = format_dt_string(self.start_time)
        [_, end_time] = format_dt_string(self.end_time)
        return f"{start_date} {start_time} - {end_time}"

    def to_dict(self):
        """Converts the EventPoll object to a dictionary."""
        return {
            "id": self.id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "regulars": self.regulars,
            "non_regulars": self.non_regulars,
            "is_active": self.is_active,
            "details": self.details,
            "type": self.type.value,
            "allocations": self.allocations,
            "poll_group_id": self.poll_group_id,
        }

    @staticmethod
    def from_dict(dct):
        """Creates an EventPoll object from a dictionary."""
        poll = EventPoll(
            dct["start_time"], dct["end_time"], dct["details"], dct["allocations"]
        )
        poll.id = dct["id"]
        poll.regulars = dct["regulars"]
        poll.non_regulars = dct["non_regulars"]
        poll.type = PollType(dct["type"])
        poll.poll_group_id = dct["poll_group_id"]
        poll.is_active = (
            dct["is_active"]
            if "is_active" in dct and isinstance(dct["is_active"], List[bool, bool])
            else [True, True]
        )
        return poll

    def get_people_list_by_membership(self, membership: Membership):
        """Gets the list of people for the given membership."""
        if membership == Membership.REGULAR:
            return self.regulars
        if membership == Membership.NON_REGULAR:
            return self.non_regulars
        raise ValueError("Invalid membership: " + membership.value)

    def insert_id(self, new_id):
        "Inserts the given id into the EventPoll object."
        self.id = new_id

    def is_person_status_changed(
        self, username, membership: Membership, new_sign_up_status
    ):
        """Checks if the person's status has changed."""
        if membership == Membership.REGULAR:
            is_present = username in self.regulars
        elif membership == Membership.NON_REGULAR:
            is_present = username in self.non_regulars
        else:
            raise ValueError("Invalid membership: " + membership)
        return is_present != new_sign_up_status
