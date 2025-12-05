"""Model for a group of polls."""


# TODO: create the aggregated poll results in the db as well for efficient access.
# remember to use transactions to ensure that the poll results are consistent
class PollGroup:
    """Class representing a group of polls."""

    def __init__(self, owner_id, name, polls_ids=None):
        if polls_ids is None:
            self.polls_ids = []
        else:
            self.polls_ids = polls_ids.copy()
        self.owner_id = owner_id
        self.id = None
        self.name = name

    def to_dict(self):
        """Converts the PollGroup to a dictionary."""
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "polls_ids": self.polls_ids,
        }

    def insert_id(self, new_id: str):
        """Inserts the ID of the PollGroup."""
        self.id = new_id

    def get_poll_ids(self):
        """Returns the list of poll IDs in the group."""
        return self.polls_ids

    @staticmethod
    def from_dict(dct):
        """Creates a PollGroup from a dictionary."""
        group = PollGroup(dct["owner_id"], dct["name"], dct["polls_ids"])
        group.id = dct["id"]
        return group
