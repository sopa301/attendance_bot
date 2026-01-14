"""Debouncer implementations."""

import abc
import inspect

import redis

DEFAULT_WAIT_TIME_MS = 500


class Debouncer(abc.ABC):
    """Abstract base class for a debouncer."""

    @abc.abstractmethod
    async def debounce(
        self, key: str, callback: callable, wait_time: int = DEFAULT_WAIT_TIME_MS
    ) -> bool:
        """
        Debounces calls to the given callback function identified by the key.
        If a call with the same key is made within the wait_time, the previous call is cancelled.
        Returns True if the callback was executed, False if it was debounced.
        """


class NoOpDebouncer(Debouncer):
    """A debouncer that does nothing (no-op). Fallback for environments without Redis."""

    async def debounce(
        self, key: str, callback: callable, wait_time: int = DEFAULT_WAIT_TIME_MS
    ) -> bool:
        """Immediately executes the callback without debouncing."""
        await callback()
        return True


class RedisDebouncer(Debouncer):
    """A debouncer implementation using Redis."""

    def __init__(self, redis_url: str):
        self.redis_client = redis.Redis.from_url(redis_url)

    def _key_name(self, key: str) -> str:
        return f"debouncer:{key}"

    async def debounce(
        self,
        key: str,
        callback: callable,
        wait_time: int = DEFAULT_WAIT_TIME_MS,
    ) -> bool:

        key = self._key_name(key)

        # SET key NX PX wait_time (ms)
        was_set = self.redis_client.set(key, "1", px=wait_time, nx=True)
        print(was_set)
        if not was_set:
            return False

        # Run callback, supporting both sync and async
        result = callback()
        if inspect.iscoroutine(result):
            await result

        return True
