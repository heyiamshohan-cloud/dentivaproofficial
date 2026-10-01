"""Deterministic clock for tests and time-based business rules."""

from __future__ import annotations

from datetime import timedelta

from dentiva.core import clock as clock_module
from dentiva.core.clock import FrozenClock, iso_utc, parse_iso, reset_clock, set_clock


def test_frozen_clock_can_be_injected() -> None:
    frozen = FrozenClock(at=parse_iso("2026-01-02T03:04:05+00:00"))
    set_clock(frozen)
    try:
        assert clock_module.CLOCK.now_utc().year == 2026
        frozen.advance(timedelta(days=1))
        assert clock_module.CLOCK.now_utc().day == 3
        assert clock_module.CLOCK.today_local() is not None
    finally:
        reset_clock()


def test_iso_round_trip() -> None:
    frozen = FrozenClock(at=parse_iso("2026-05-06T07:08:09+00:00"))
    set_clock(frozen)
    try:
        stamp = iso_utc()
        assert stamp == "2026-05-06T07:08:09+00:00"
        assert parse_iso(stamp) == frozen.now_utc()
    finally:
        reset_clock()


def test_reset_restores_the_system_clock() -> None:
    set_clock(FrozenClock(at=parse_iso("2020-01-01T00:00:00+00:00")))
    reset_clock()
    assert isinstance(clock_module.CLOCK, clock_module.Clock)
