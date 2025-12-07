"""Abstraction to store banned personnel in the database.
Note that this isn't currently used."""

from pymongo import UpdateOne
from pymongo.collection import Collection

from src.model import AttendanceList
from src.util import (
    ABSENT_POINTS,
    BAN_DURATION_SESSIONS,
    BAN_THRESHOLD,
    LAST_MINUTE_CANCELLATION_POINTS,
)


class BanRepository:
    """Repository for managing banned personnel storage."""

    def __init__(self, collection: Collection):
        self.collection = collection

    def log_bans(self, attendance_list: AttendanceList):
        """Log bans for absent and last-minute cancelled personnel."""
        absent_persons, cancelled_persons = (
            attendance_list.get_non_present_penalisable_names()
        )
        all_persons = absent_persons + cancelled_persons
        existing_records = {
            doc["username"]: doc
            for doc in self.collection.find({"username": {"$in": all_persons}})
        }

        bulk_operations = []
        for person in absent_persons:
            current_record = existing_records.get(
                person, {"ban_points": 0, "ban_sessions": 0}
            )
            new_points = current_record["ban_points"] + ABSENT_POINTS
            if new_points >= BAN_THRESHOLD:
                new_points = new_points - BAN_THRESHOLD
                new_sessions = current_record["ban_sessions"] + BAN_DURATION_SESSIONS
            else:
                new_sessions = current_record["ban_sessions"]

            bulk_operations.append(
                UpdateOne(
                    {"username": person},
                    {"$set": {"ban_points": new_points, "ban_sessions": new_sessions}},
                    upsert=True,
                )
            )
        for person in cancelled_persons:
            current_record = existing_records.get(
                person, {"ban_points": 0, "ban_sessions": 0}
            )
            new_points = current_record["ban_points"] + LAST_MINUTE_CANCELLATION_POINTS
            if new_points >= BAN_THRESHOLD:
                new_points = new_points - BAN_THRESHOLD
                new_sessions = current_record["ban_sessions"] + BAN_DURATION_SESSIONS
            else:
                new_sessions = current_record["ban_sessions"]

            bulk_operations.append(
                UpdateOne(
                    {"username": person},
                    {"$set": {"ban_points": new_points, "ban_sessions": new_sessions}},
                    upsert=True,
                )
            )
        if bulk_operations:
            self.collection.bulk_write(bulk_operations)

    def get_and_update_banned_personnel(self, attendance_list: AttendanceList):
        """Retrieve and update banned personnel based on their ban sessions."""
        all_persons = attendance_list.get_all_player_names()
        banned_persons = []
        existing_records = {
            doc["username"]: doc
            for doc in self.collection.find({"username": {"$in": all_persons}})
        }
        bulk_operations = []
        for person in all_persons:
            current_record = existing_records.get(
                person, {"ban_points": 0, "ban_sessions": 0}
            )
            if current_record["ban_sessions"] > 0:
                banned_persons.append(person)
                new_sessions = current_record["ban_sessions"] - 1
                bulk_operations.append(
                    UpdateOne(
                        {"username": person}, {"$set": {"ban_sessions": new_sessions}}
                    )
                )
        if bulk_operations:
            self.collection.bulk_write(bulk_operations)
        return banned_persons
