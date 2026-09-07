"""The exam clock. Monotonic, so a system clock change mid-sitting cannot extend your exam."""

from __future__ import annotations

import time

WARN_AT_MINUTES = (30, 10, 5, 1)


class Timer:
    def __init__(self, minutes: int, clock=time.monotonic) -> None:
        self.total = minutes * 60
        self._clock = clock
        self._start = clock()
        self._warned: set[int] = set()

    @property
    def elapsed(self) -> float:
        return self._clock() - self._start

    @property
    def remaining(self) -> float:
        return max(0.0, self.total - self.elapsed)

    @property
    def expired(self) -> bool:
        return self.remaining <= 0

    def due_warning(self) -> int | None:
        """The largest unspoken threshold now passed, or None. Each fires once."""
        minutes_left = self.remaining / 60
        for threshold in WARN_AT_MINUTES:
            if minutes_left <= threshold and threshold not in self._warned:
                self._warned.add(threshold)
                return threshold
        return None

    def format_remaining(self) -> str:
        secs = int(self.remaining)
        return f"{secs // 60}:{secs % 60:02d}"
