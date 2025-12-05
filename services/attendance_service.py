"""Service layer for attendance-related operations."""

import logging
from collections.attendance_repository import AttendanceRepository
from typing import List

from telegram import User

from model.attendance_list import AttendanceList
from services.poll_service import PollService
from util.errors import AttendanceListNotFoundError


class AttendanceService:
    """
    Service class for attendance-related operations.
    """

    def __init__(
        self, attendance_repository: AttendanceRepository, poll_service: PollService
    ):
        # Enable logging
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        # set higher logging level for httpx to avoid all GET and POST requests being logged
        logging.getLogger("httpx").setLevel(logging.WARNING)

        self.logger = logging.getLogger(__name__)
        self.attendance_repository = attendance_repository
        self.poll_service = poll_service

    def get_attendance_lists_by_owner_id(self, owner_id: str) -> List[AttendanceList]:
        """Retrieve all attendance lists owned by a specific user."""
        self.logger.info(
            "User %s requested for the list of attendance lists.", owner_id
        )
        return self.attendance_repository.get_attendance_lists_by_owner_id(owner_id)

    def create_attendance_list_from_poll(
        self, poll_id: str, user: User
    ) -> AttendanceList:
        """Create a new attendance list based on a poll ID."""
        self.logger.info("Creating attendance list from poll ID: %s", poll_id)
        poll = self.poll_service.get_event_poll(poll_id)
        if not poll:
            return None
        attendance_list = AttendanceList.from_poll(poll, user.id)
        attendance_list = self.attendance_repository.insert_attendance_list(
            attendance_list
        )
        return attendance_list

    def create_attendance_list(self, attendance_list: AttendanceList) -> AttendanceList:
        """Create a new attendance list."""
        self.logger.info(
            "Creating a new attendance list for owner ID: %s", attendance_list.owner_id
        )
        attendance_list = self.attendance_repository.insert_attendance_list(
            attendance_list
        )
        return attendance_list

    def get_attendance_list(self, attendance_list_id: str) -> AttendanceList | None:
        """Retrieve an attendance list by its ID."""
        self.logger.info("Retrieving attendance list ID: %s", attendance_list_id)
        try:
            return self.attendance_repository.get_attendance_list(attendance_list_id)
        except AttendanceListNotFoundError as e:
            self.logger.error("Error retrieving attendance list: %s", e)
            return None

    def delete_attendance_list(self, attendance_list_id: str) -> bool:
        """Delete an attendance list by its ID."""
        self.logger.info("Deleting attendance list ID: %s", attendance_list_id)
        result = self.attendance_repository.delete_attendance_list(attendance_list_id)
        return result.deleted_count > 0

    def process_edited_list(
        self, old_list: AttendanceList, new_list: AttendanceList
    ) -> AttendanceList:
        """Process and save an edited attendance list."""
        self.logger.info("Processing edited attendance list ID: %s", old_list.id)
        new_list.update_administrative_details(old_list)
        self.attendance_repository.put_attendance_list(new_list.id, new_list)
        return new_list

    def update_user_status(
        self, attendance_list_id: str, user_id: str, status: int
    ) -> AttendanceList | None:
        """Update a user's attendance status in an attendance list."""
        self.logger.info(
            "Updating status for user %s in attendance list %s to %d.",
            user_id,
            attendance_list_id,
            status,
        )
        try:
            attendance_list = self.attendance_repository.get_attendance_list(
                attendance_list_id
            )
            selected_user = attendance_list.find_user_by_id(user_id)
            if selected_user.status == status:
                return attendance_list
            attendance_list.update_user_status(user_id, status)
            self.attendance_repository.patch_user_status_in_attendance_list(
                attendance_list, user_id, status
            )
            return attendance_list
        except AttendanceListNotFoundError as e:
            self.logger.error("Error updating user status: %s", e)
            return None
