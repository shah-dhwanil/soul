"""In-process throttle for the unauthenticated auth endpoints.

Register and login run argon2id, which is deliberately expensive. Without a
limit, an unauthenticated caller can burn CPU and memory with a few
concurrent requests, and can guess passwords without friction.

The limiter is per process: with more than one API replica the effective
limit is per replica. Behind a proxy, `request.client.host` is the proxy's
address, so the per-IP limit then applies to the proxy rather than the
caller.
"""

from collections import defaultdict, deque
from time import monotonic

_MAX_TRACKED_KEYS = 10_000


class SlidingWindowLimiter:
    """Allows `limit` hits per key within a rolling window."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        self._prune(now)
        return True

    def _prune(self, now: float) -> None:
        if len(self._hits) <= _MAX_TRACKED_KEYS:
            return
        stale = [
            key
            for key, hits in self._hits.items()
            if not hits or now - hits[-1] > self._window
        ]
        for key in stale:
            del self._hits[key]

    def reset(self) -> None:
        self._hits.clear()


# Password guessing against one account, from any number of addresses.
LOGIN_PER_ACCOUNT = SlidingWindowLimiter(limit=10, window_seconds=60)
# Password guessing across accounts from one address.
LOGIN_PER_IP = SlidingWindowLimiter(limit=20, window_seconds=60)
# Account creation, which is a unique-row write and an argon2 hash.
REGISTER_PER_IP = SlidingWindowLimiter(limit=10, window_seconds=3600)


def reset_limiters() -> None:
    """Forget every recorded hit. Used by tests."""
    LOGIN_PER_ACCOUNT.reset()
    LOGIN_PER_IP.reset()
    REGISTER_PER_IP.reset()
