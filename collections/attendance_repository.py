"""
Abstraction to store attendances in the database.
"""

from bson import ObjectId
from pymongo.collection import Collection

from model.attendance_list import AttendanceList
from util.errors import AttendanceListNotFoundError


class AttendanceRepository:
    """Repository for managing attendance list storage."""

    def __init__(self, collection: Collection):
        self.collection = collection

    def insert_attendance_list(self, attendance: AttendanceList) -> AttendanceList:
        """Insert a new attendance list into the database."""
        new_id = str(self.collection.insert_one(attendance.to_dict()).inserted_id)
        attendance.insert_id(new_id)
        return attendance

    def get_attendance_list(self, attendance_id):
        """Retrieve an attendance list by its ID."""
        attendance_json = self.collection.find_one({"_id": ObjectId(attendance_id)})
        if attendance_json is None:
            raise AttendanceListNotFoundError(attendance_id)
        attendance = AttendanceList.from_dict(attendance_json)
        attendance.insert_id(attendance_id)
        return attendance

    def get_attendance_lists_by_owner_id(self, owner_id):
        """Retrieve all attendance lists owned by a specific user."""
        attendance_jsons = list(self.collection.find({"owner_id": owner_id}))
        attendance_lists = list(map(AttendanceList.from_dict, attendance_jsons))
        for i, attendance in enumerate(attendance_lists):
            attendance.insert_id(str(attendance_jsons[i]["_id"]))
        return attendance_lists

    def patch_user_status_in_attendance_list(
        self, attendance_list: AttendanceList, user_id, new_status
    ):
        """Update the status of a user in an attendance list."""
        category, index = attendance_list.get_category_and_index(user_id)
        return self.collection.update_one(
            {"_id": ObjectId(attendance_list.id)},
            {"$set": {f"{category}.{index}.status": new_status}},
        )

    def put_attendance_list(self, attendance_id, attendance_list):
        """Update an entire attendance list in the database."""
        return self.collection.update_one(
            {"_id": ObjectId(attendance_id)}, {"$set": attendance_list.to_dict()}
        )

    def delete_attendance_list(self, attendance_id):
        """Delete an attendance list from the database."""
        return self.collection.delete_one({"_id": ObjectId(attendance_id)})
