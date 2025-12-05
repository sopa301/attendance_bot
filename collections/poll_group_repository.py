"""
Abstraction to store poll groups in the database.
"""

from typing import List

from bson import ObjectId
from pymongo.collection import Collection

from model.poll_group import PollGroup
from util.errors import PollGroupNotFoundError


class PollGroupRepository:
    """Repository for managing poll group storage."""

    def __init__(self, collection: Collection):
        self.collection = collection

    def insert_poll_group(self, poll_group: PollGroup) -> str:
        """Inserts a new poll group into the collection."""
        return str(self.collection.insert_one(poll_group.to_dict()).inserted_id)

    def get_poll_group(self, group_id):
        """Retrieves a poll group by its ID."""
        poll_group_json = self.collection.find_one({"_id": ObjectId(group_id)})
        if poll_group_json is None:
            raise PollGroupNotFoundError(group_id)
        poll_group = PollGroup.from_dict(poll_group_json)
        poll_group.insert_id(group_id)
        return poll_group

    def get_poll_groups_by_owner_id(self, owner_id) -> List[PollGroup]:
        """Retrieves all poll groups owned by a specific user."""
        poll_group_jsons = list(self.collection.find({"owner_id": owner_id}))
        poll_groups = list(map(PollGroup.from_dict, poll_group_jsons))
        for i, group in enumerate(poll_groups):
            group.insert_id(str(poll_group_jsons[i]["_id"]))
        return poll_groups

    def delete_poll_group(self, group_id):
        """Deletes a poll group by its ID."""
        result = self.collection.delete_one({"_id": ObjectId(group_id)})
        if result.deleted_count == 0:
            raise PollGroupNotFoundError(group_id)
