"""Injectable clock.

Everything that needs "now" goes through :data:`CLOCK` so that tests can freeze
time deterministically instead of sleeping or monkeypatching ``datetime``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


class Clock:
    """System clock (UTC)."""

    __slots__ = ()

    def now_utc(self) -> datetime:
        return datetime.now(UTC)

    def now_local(self) -> datetime:
        return datetime.now().astimezone()

    def today_local(self):
        return self.now_local().date()

    def monotonic(self) -> float:
        import time

        return time.monotonic()


@dataclass
class FrozenClock(Clock):
    """Clock pinned to a fixed instant; ``advance()`` moves it forward."""

    at: datetime
    _elapsed: float = 0.0

    def __post_init__(self) -> None:
        if self.at.tzinfo is None:
            self.at = self.at.replace(tzinfo=UTC)

    def now_utc(self) -> datetime:
        return self.at

    def now_local(self) -> datetime:
        return self.at.astimezone()

    def today_local(self):
        return self.now_local().date()

    def advance(self, delta: timedelta) -> None:
        self.at = self.at + delta

    def monotonic(self) -> float:
        self._elapsed += 1.0
        return self._elapsed


CLOCK = Clock()


def set_clock(clock: Clock) -> None:
    """Replace the process-wide clock (used by tests)."""
    global CLOCK
    CLOCK = clock


def reset_clock() -> None:
    """Restore the system clock."""
    global CLOCK
    CLOCK = Clock()


def utc_now() -> datetime:
    return CLOCK.now_utc()


def local_now() -> datetime:
    return CLOCK.now_local()


def iso_utc(value: datetime | None = None) -> str:
    """ISO-8601 timestamp in UTC, always with an explicit offset."""
    moment = value or CLOCK.now_utc()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 timestamp produced by :func:`iso_utc`."""
    return datetime.fromisoformat(value)
