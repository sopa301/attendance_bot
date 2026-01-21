"""Repository for managing ban records."""

import redis

from src.util import ServiceUnavailableError


class BanRepository:

    def __init__(self, redis_url: str):
        self.redis_client = redis.Redis.from_url(redis_url)

    def _get_key(self, user_id: str, banner_id: str) -> str:
        """Generates a Redis key for the given user ID."""
        return f"ban:{user_id}:by:{banner_id}"

    def ban_users(
        self, user_ids: list, issuer_user_id: str, duration_seconds: int
    ) -> None:
        """Bans multiple users for a specified duration."""
        for user_id in user_ids:
            self.redis_client.setex(
                self._get_key(user_id, issuer_user_id),
                duration_seconds,
                "banned",
            )

    def get_banned_users(self, issuer_user_id: str) -> list:
        """Gets a list of all currently banned users by the issuer."""
        pattern = self._get_key("*", issuer_user_id)
        keys = self.redis_client.keys(pattern)
        banned_users = [key.decode().split(":")[1] for key in keys]
        return banned_users

    def unban_user(self, user_id: str, issuer_user_id: str) -> None:
        """Unbans a user."""
        self.redis_client.delete(self._get_key(user_id, issuer_user_id))

    def get_ban_duration(self, user_id: str, issuer_user_id: str) -> bool:
        """Gets the ban duration for a user. Returns the remaining ban time in seconds
        or 0 if not banned."""
        value = self.redis_client.ttl(self._get_key(user_id, issuer_user_id))
        return max(0, value)

    def is_user_banned(self, username: str, issuer_user_id: str) -> bool:
        """Checks if a user is currently banned by the issuer."""
        try:
            return (
                self.redis_client.exists(self._get_key(username, issuer_user_id))
                and self.get_ban_duration(username, issuer_user_id) > 0
            )
        except redis.exceptions.ResponseError as e:
            raise ServiceUnavailableError(
                issuer_user_id, self.__class__.__name__
            ) from e
