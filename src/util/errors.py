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


class UserBannedError(Exception):
    """
    Exception raised when a user is banned from performing an action.
    """

    def __init__(self, username, banned_duration: int):
        self.username = username
        self.message = "User is banned with username: " + username
        self.banned_duration = banned_duration
        super().__init__(self.message)


class ServiceUnavailableError(Exception):
    """
    Exception raised when a dependent service is unavailable.
    """

    def __init__(self, user_id, service_name: str):
        self.message = (
            f"Service is unavailable for user ID: {user_id} in service: {service_name}"
        )
        super().__init__(self.message)
