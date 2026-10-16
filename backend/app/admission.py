"""Who may open /ws/live (SPEC §5): RATE_PER_MIN new connections per IP per minute, and at most LIVE_SESSIONS open
Live sessions, the expensive part. Counts are per instance: with several Cloud Run instances each keeps its own
(BUILD-GUIDE T27 accepts that; the demo service runs one)."""

import time
from collections import deque
from collections.abc import Callable

RATE_PER_MIN = 20
LIVE_SESSIONS = 3
WINDOW_S = 60.0


class Admission:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._seen: dict[str, deque[float]] = {}
        self.open_sessions = 0

    def allow(self, ip: str) -> bool:
        """Counts a new connection from `ip`; False once it has made RATE_PER_MIN in the last minute."""
        now = self._clock()
        seen = self._seen.setdefault(ip, deque())
        while seen and now - seen[0] > WINDOW_S:
            seen.popleft()
        if len(seen) >= RATE_PER_MIN:
            return False
        seen.append(now)
        return True

    def acquire(self) -> bool:
        if self.open_sessions >= LIVE_SESSIONS:
            return False
        self.open_sessions += 1
        return True

    def release(self) -> None:
        self.open_sessions -= 1


ADMISSION = Admission()
