"""Service for handling bans related operations."""

from model import AttendanceList
from src.repositories import BanRepository

DEFAULT_BAN_DURATION_SECONDS = 28 * 24 * 60 * 60  # 28 days


class BanService:
    """Service for handling bans related operations."""

    def __init__(self, repository: BanRepository):
        self.repository = repository

    def log_bans(self, attendance_list: AttendanceList, issuer_user_id: str) -> None:
        """Logs bans for the given attendance list."""
        usernames_to_ban = attendance_list.get_penalisable_names()
        print(f"Banning users: {usernames_to_ban} with issuer ID: {issuer_user_id}")
        self.repository.ban_users(
            usernames_to_ban, issuer_user_id, DEFAULT_BAN_DURATION_SECONDS
        )

    def get_banned_users(self, issuer_user_id: str) -> list:
        """Gets all banned users for the issuer."""
        return self.repository.get_banned_users(issuer_user_id)

    def ban_user(
        self, user_id: str, issuer_user_id: str, duration_seconds: int
    ) -> None:
        """Bans a user for a specified duration."""
        self.repository.ban_users([user_id], issuer_user_id, duration_seconds)

    def get_ban_duration(self, user_id: str, issuer_user_id: str) -> bool:
        """Gets the ban duration for a user. Returns the remaining ban time in seconds
        or 0 if not banned."""
        return self.repository.get_ban_duration(user_id, issuer_user_id)

    def is_user_banned(self, user_id: str, issuer_user_id: str) -> bool:
        """Checks if a user is currently banned by the issuer."""
        return self.repository.is_user_banned(user_id, issuer_user_id)

    def remove_banned_people(
        self, attendance_list: AttendanceList, user_id: str
    ) -> tuple[AttendanceList, list]:
        """Removes banned people from the attendance list."""
        all_names = attendance_list.get_all_player_names()
        banned_names = [
            name for name in all_names if self.is_user_banned(name, user_id)
        ]
        attendance_list.remove_banned_people(banned_names)
        return attendance_list, banned_names

    def unban_user(self, user_id: str, issuer_user_id: str) -> None:
        """Unbans a user."""
        self.repository.unban_user(user_id, issuer_user_id)
