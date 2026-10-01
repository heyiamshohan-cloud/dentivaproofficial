"""Reporting periods (docs/07 §8).

Money windows are **local** windows: a clinic in Dhaka closes its day at
midnight Asia/Dhaka. These tests pin that behaviour down, including the
Saturday-start working week used in Bangladesh.
"""

from __future__ import annotations

from datetime import date

import pytest

from dentiva.domain.period import (
    PERIOD_ALL,
    PERIOD_LAST_MONTH,
    PERIOD_THIS_MONTH,
    PERIOD_THIS_QUARTER,
    PERIOD_THIS_WEEK,
    PERIOD_THIS_YEAR,
    PRESETS,
    Period,
    days_between,
    month_keys,
    month_to_date,
    resolve,
)


def test_today_is_a_single_day() -> None:
    period = resolve("today", today=date(2026, 3, 15))
    assert (period.from_date, period.to_date) == (date(2026, 3, 15), date(2026, 3, 15))
    assert period.days == 1


def test_this_month_starts_on_the_first_and_ends_today() -> None:
    period = resolve(PERIOD_THIS_MONTH, today=date(2026, 3, 15))
    assert (period.from_date, period.to_date) == (date(2026, 3, 1), date(2026, 3, 15))
    assert period.days == 15


def test_last_month_spans_the_whole_previous_month() -> None:
    period = resolve(PERIOD_LAST_MONTH, today=date(2026, 3, 15))
    assert (period.from_date, period.to_date) == (date(2026, 2, 1), date(2026, 2, 28))


def test_last_month_works_across_a_year_boundary() -> None:
    period = resolve(PERIOD_LAST_MONTH, today=date(2026, 1, 10))
    assert (period.from_date, period.to_date) == (date(2025, 12, 1), date(2025, 12, 31))


def test_the_week_starts_on_saturday() -> None:
    # 2026-03-18 is a Wednesday; the Bangladesh working week began on Saturday
    # 2026-03-14.
    period = resolve(PERIOD_THIS_WEEK, today=date(2026, 3, 18))
    assert period.from_date == date(2026, 3, 14)
    assert period.to_date == date(2026, 3, 18)
    assert period.from_date.strftime("%A") == "Saturday"


def test_a_week_that_starts_on_saturday_is_one_day_long() -> None:
    period = resolve(PERIOD_THIS_WEEK, today=date(2026, 3, 14))
    assert (period.from_date, period.to_date) == (date(2026, 3, 14), date(2026, 3, 14))


def test_rolling_windows_are_inclusive() -> None:
    period = resolve("last_30_days", today=date(2026, 3, 30))
    assert (period.from_date, period.to_date) == (date(2026, 3, 1), date(2026, 3, 30))
    assert period.days == 30
    week = resolve("last_7_days", today=date(2026, 3, 30))
    assert week.days == 7


def test_quarters_and_years() -> None:
    assert resolve(PERIOD_THIS_QUARTER, today=date(2026, 5, 4)).from_date == date(2026, 4, 1)
    assert resolve(PERIOD_THIS_QUARTER, today=date(2026, 12, 31)).from_date == date(2026, 10, 1)
    assert resolve(PERIOD_THIS_YEAR, today=date(2026, 7, 1)).from_date == date(2026, 1, 1)


def test_all_time_is_an_open_period() -> None:
    period = resolve(PERIOD_ALL, today=date(2026, 3, 15))
    assert period.is_open
    assert period.days == 0
    assert period.contains(date(1999, 1, 1))
    assert period.previous() == period


def test_previous_period_is_adjacent_and_the_same_length() -> None:
    """``previous`` shifts the window back by exactly its own length.

    Calendar-aware presets ("last month") exist separately; this one is used by
    "compare with the previous period" tiles, which must never overlap.
    """
    period = resolve(PERIOD_THIS_MONTH, today=date(2026, 3, 31))
    previous = period.previous()
    assert (previous.from_date, previous.to_date) == (date(2026, 1, 29), date(2026, 2, 28))
    assert previous.days == period.days
    assert previous.to_date < period.from_date  # type: ignore[operator]


def test_every_preset_resolves_and_has_a_label() -> None:
    for key in PRESETS:
        period = resolve(key, today=date(2026, 3, 15))
        assert period.from_date is not None and period.to_date is not None
        assert period.from_date <= period.to_date
        assert period.label and period.label != key.replace("_", " ")


def test_unknown_periods_are_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown period"):
        resolve("fortnight", today=date(2026, 3, 15))


def test_a_period_needs_both_ends() -> None:
    with pytest.raises(ValueError, match="both ends"):
        Period(key="broken", from_date=date(2026, 1, 1))


def test_month_to_date_uses_the_local_calendar() -> None:
    period = month_to_date(today=date(2026, 3, 15))
    assert (period.from_date, period.to_date) == (date(2026, 3, 1), date(2026, 3, 15))


def test_days_between_is_inclusive_and_ordered() -> None:
    assert days_between(date(2026, 3, 1), date(2026, 3, 3)) == [
        date(2026, 3, 1),
        date(2026, 3, 2),
        date(2026, 3, 3),
    ]
    assert days_between(date(2026, 3, 3), date(2026, 3, 1)) == []
    assert days_between(date(2026, 3, 1), date(2026, 3, 1)) == [date(2026, 3, 1)]


def test_month_keys_walk_across_the_year_boundary() -> None:
    assert month_keys(date(2026, 11, 1), date(2027, 2, 1)) == [
        "2026-11",
        "2026-12",
        "2027-01",
        "2027-02",
    ]
