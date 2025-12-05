"""Person class representing an individual in a poll or attendance list."""

from util.constants import Membership


class Person:
    def __init__(self, person_id=None, name=None, status=None, membership=None):
        self.id = person_id
        self.name = name
        self.status = status
        self.membership = membership

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "membership": self.membership.value,
        }

    @staticmethod
    def from_dict(dct):
        person = Person()
        person.id = dct["id"]
        person.name = dct["name"]
        person.status = dct["status"]
        person.membership = Membership(dct["membership"])
        return person
