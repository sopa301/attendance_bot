"""
Abstraction to store polls in the database.
"""

from typing import List

from bson import ObjectId
from pymongo.collection import Collection

from src.model import EventPoll
from src.util import Membership, PollNotFoundError


class PollRepository:
    """Repository for managing poll storage."""

    def __init__(self, collection: Collection):
        self.collection = collection

    def insert_event_poll(self, poll: EventPoll) -> str:
        """Inserts a new event poll into the collection."""
        return str(self.collection.insert_one(poll.to_dict()).inserted_id)

    def insert_event_polls_dicts(self, polls: List[dict]) -> List[str]:
        """Inserts multiple event polls into the collection."""
        return list(map(str, self.collection.insert_many(polls).inserted_ids))

    def insert_event_polls(self, polls: List[EventPoll]) -> List[str]:
        """Inserts multiple event polls into the collection."""
        return self.insert_event_polls_dicts(list(map(lambda x: x.to_dict(), polls)))

    def get_event_poll(self, poll_id: str) -> EventPoll:
        """Retrieves an event poll by its ID."""
        event_poll_json = self.collection.find_one({"_id": ObjectId(poll_id)})
        if event_poll_json is None:
            raise PollNotFoundError(poll_id)
        event_poll = EventPoll.from_dict(event_poll_json)
        event_poll.insert_id(poll_id)
        return event_poll

    def get_event_polls(self, poll_ids: List[str]) -> List[EventPoll]:
        """Retrieves multiple event polls by their IDs."""
        event_polls_jsons = list(
            self.collection.find({"_id": {"$in": list(map(ObjectId, poll_ids))}})
        )
        if len(event_polls_jsons) != len(poll_ids):
            raise PollNotFoundError(poll_ids)
        event_polls = list(map(EventPoll.from_dict, event_polls_jsons))
        for i, poll in enumerate(event_polls):
            poll.insert_id(poll_ids[i])
        return event_polls

    def add_person_to_poll(self, poll_id: str, username: str, field: str):
        """Adds a person to a specific field in an event poll."""
        self.collection.update_one(
            {"_id": ObjectId(poll_id)}, {"$addToSet": {field: username}}
        )

    def remove_person_from_poll(self, poll_id: str, username: str, field: str):
        """Removes a person from a specific field in an event poll."""
        self.collection.update_one(
            {"_id": ObjectId(poll_id)}, {"$pull": {field: username}}
        )

    def update_poll_group_id(self, poll_ids: List[str], group_id: str):
        """Updates the poll group ID for multiple event polls."""
        return self.collection.update_many(
            {"_id": {"$in": list(map(ObjectId, poll_ids))}},
            {"$set": {"poll_group_id": ObjectId(group_id)}},
        )

    def set_active_status(self, poll_id: str, membership: Membership, is_active: bool):
        """Sets the active status for a specific membership in an event poll."""
        return self.collection.update_one(
            {"_id": ObjectId(poll_id)},
            {"$set": {f"is_active.{membership.value}": is_active}},
        )

    def delete_poll(self, poll_id: str):
        """Deletes an event poll by its ID."""
        return self.collection.delete_one({"_id": ObjectId(poll_id)})

    def delete_event_polls(self, poll_ids: List[str]):
        """Deletes multiple event polls by their IDs."""
        return self.collection.delete_many(
            {"_id": {"$in": list(map(ObjectId, poll_ids))}}
        )
