"""Custom error for when objects are not found"""


class PollNotFoundError(Exception):
    """
    Exception raised when a poll or multiple polls are not found in the database.
    """

    def __init__(self, poll_id):
        self.poll_id = poll_id
        if isinstance(poll_id, str):
            self.message = "Poll not found with id: " + poll_id
        else:
            self.message = "Polls not found with ids: " + ", ".join(poll_id)
        super().__init__(self.message)


class PollGroupNotFoundError(Exception):
    """
    Exception raised when a poll group is not found in the database.
    """

    def __init__(self, group_id):
        self.group_id = group_id
        self.message = "Poll group not found with id: " + group_id
        super().__init__(self.message)


class AttendanceListNotFoundError(Exception):
    """
    Exception raised when an attendance list is not found in the database."""

    def __init__(self, attendance_id):
        self.attendance_id = attendance_id
        self.message = "Attendance list not found with id: " + attendance_id
        super().__init__(self.message)
