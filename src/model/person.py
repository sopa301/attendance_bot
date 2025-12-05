"""Person class representing an individual in a poll or attendance list."""

from util.constants import Membership


class Person:
    """Class representing a person."""

    def __init__(
        self,
        person_id: str,
        name: str,
        status: int,
        membership: Membership,
    ):
        self.id = person_id
        self.name = name
        self.status = status
        self.membership = membership

    def to_dict(self):
        """Converts the Person object to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "membership": self.membership.value,
        }

    @staticmethod
    def from_dict(dct):
        """Creates a Person object from a dictionary."""
        return Person(
            dct["id"], dct["name"], dct["status"], Membership(dct["membership"])
        )
