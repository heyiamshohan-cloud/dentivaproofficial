"""Reporting periods (docs/07 §8).

Reports, dashboards and the cash-up screen all need the same date windows
("today", "this month", "last 30 days"). Those windows are **local calendar**
windows — a clinic in Dhaka closes its day at midnight Asia/Dhaka, not at UTC —
so every helper here works on :func:`dentiva.core.clock.local_today` and returns
plain :class:`datetime.date` values that map directly onto the ``local_date``
columns of the ledger tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from dentiva.core.clock import local_today

#: Period presets offered by every screen that shows money or activity.
PERIOD_TODAY = "today"
PERIOD_YESTERDAY = "yesterday"
PERIOD_THIS_WEEK = "this_week"
PERIOD_LAST_7_DAYS = "last_7_days"
PERIOD_THIS_MONTH = "this_month"
PERIOD_LAST_MONTH = "last_month"
PERIOD_LAST_30_DAYS = "last_30_days"
PERIOD_THIS_QUARTER = "this_quarter"
PERIOD_THIS_YEAR = "this_year"
PERIOD_ALL = "all_time"

#: Presets in the order the UI lists them.
PRESETS: tuple[str, ...] = (
    PERIOD_TODAY,
    PERIOD_YESTERDAY,
    PERIOD_THIS_WEEK,
    PERIOD_LAST_7_DAYS,
    PERIOD_THIS_MONTH,
    PERIOD_LAST_MONTH,
    PERIOD_LAST_30_DAYS,
    PERIOD_THIS_QUARTER,
    PERIOD_THIS_YEAR,
)

_LABELS: dict[str, str] = {
    PERIOD_TODAY: "Today",
    PERIOD_YESTERDAY: "Yesterday",
    PERIOD_THIS_WEEK: "This week",
    PERIOD_LAST_7_DAYS: "Last 7 days",
    PERIOD_THIS_MONTH: "This month",
    PERIOD_LAST_MONTH: "Last month",
    PERIOD_LAST_30_DAYS: "Last 30 days",
    PERIOD_THIS_QUARTER: "This quarter",
    PERIOD_THIS_YEAR: "This year",
    PERIOD_ALL: "All time",
}


@dataclass(frozen=True, slots=True)
class Period:
    """An inclusive local-date window."""

    key: str = PERIOD_THIS_MONTH
    from_date: date | None = None
    to_date: date | None = None

    def __post_init__(self) -> None:
        if (self.from_date is None) != (self.to_date is None):
            raise ValueError("A period needs both ends, or neither.")

    @property
    def is_open(self) -> bool:
        """True for "all time", where neither end is set."""
        return self.from_date is None

    @property
    def days(self) -> int:
        """Inclusive length in days (0 when the period is open)."""
        if self.from_date is None or self.to_date is None:
            return 0
        return (self.to_date - self.from_date).days + 1

    @property
    def label(self) -> str:
        return _LABELS.get(self.key, self.key.replace("_", " ").title())

    def contains(self, day: date) -> bool:
        if self.from_date is None or self.to_date is None:
            return True
        return self.from_date <= day <= self.to_date

    def previous(self) -> Period:
        """The window of the same length immediately before this one."""
        if self.from_date is None or self.to_date is None:
            return self
        length = self.days
        return Period(
            key=self.key,
            from_date=self.from_date - timedelta(days=length),
            to_date=self.from_date - timedelta(days=1),
        )


def resolve(key: str, *, today: date | None = None) -> Period:
    """Turn a preset key into concrete dates using the clinic's local calendar."""
    day = today or local_today()
    if key == PERIOD_TODAY:
        return Period(key, day, day)
    if key == PERIOD_YESTERDAY:
        yesterday = day - timedelta(days=1)
        return Period(key, yesterday, yesterday)
    if key == PERIOD_THIS_WEEK:
        # The clinic week starts on Saturday (the Bangladesh working week).
        start = day - timedelta(days=(day.weekday() + 2) % 7)
        return Period(key, start, day)
    if key == PERIOD_LAST_7_DAYS:
        return Period(key, day - timedelta(days=6), day)
    if key == PERIOD_THIS_MONTH:
        return Period(key, day.replace(day=1), day)
    if key == PERIOD_LAST_MONTH:
        first_of_this_month = day.replace(day=1)
        last_day = first_of_this_month - timedelta(days=1)
        return Period(key, last_day.replace(day=1), last_day)
    if key == PERIOD_LAST_30_DAYS:
        return Period(key, day - timedelta(days=29), day)
    if key == PERIOD_THIS_QUARTER:
        quarter_start_month = ((day.month - 1) // 3) * 3 + 1
        return Period(key, day.replace(month=quarter_start_month, day=1), day)
    if key == PERIOD_THIS_YEAR:
        return Period(key, day.replace(month=1, day=1), day)
    if key == PERIOD_ALL:
        return Period(key)
    raise ValueError(f"Unknown period: {key!r}")


def month_to_date(*, today: date | None = None) -> Period:
    """Shortcut used by the reports screen when it opens."""
    return resolve(PERIOD_THIS_MONTH, today=today)


def days_between(start: date, end: date) -> list[date]:
    """Every local date from *start* to *end* inclusive (for zero-gap charts)."""
    if end < start:
        return []
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def month_keys(start: date, end: date) -> list[str]:
    """``YYYY-MM`` keys covering *start*..*end* (for trend charts)."""
    keys: list[str] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        keys.append(f"{year:04d}-{month:02d}")
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return keys
