"""In-memory session: permissions, activity clock, auto-lock and re-auth
(docs/05 §3, REQ-AUTH-002/003/005/006).

The session is never persisted and never shared between threads. It is an
immutable value: every transition returns a new object, so a background thread
can hold a consistent view while the user keeps working.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from dentiva.core.clock import utc_now
from dentiva.security.session import (
    AUTO_LOCK_OPTIONS,
    DEFAULT_AUTO_LOCK_MINUTES,
    REAUTH_VALID_MINUTES,
    ActingAs,
    Session,
    current,
    current_or_fail,
    iter_permissions,
    new_session_id,
    set_current,
)


@pytest.fixture(autouse=True)
def _no_session() -> None:
    """Every test starts (and ends) with nobody signed in."""
    set_current(None)
    yield
    set_current(None)


def _session(**overrides: object) -> Session:
    now = utc_now()
    base = {
        "session_id": "s-1",
        "user_id": 1,
        "username": "admin",
        "display_name": "Admin",
        "roles": ("Administrator",),
        "permissions": frozenset({"patient.view", "invoice.create", "user.manage"}),
        "business_id": 1,
        "is_system_admin": True,
        "timeout_minutes": 15,
        "started_at": now,
        "last_activity_at": now,
        "reauthenticated_at": None,
        "locked": False,
    }
    base.update(overrides)
    return Session(**base)  # type: ignore[arg-type]


def test_permission_checks() -> None:
    session = _session()
    assert session.has("patient.view")
    assert not session.has("patient.delete")
    assert session.has_any("patient.delete", "patient.view")
    assert not session.has_any("patient.delete", "business.delete")


def test_activity_clock_drives_the_auto_lock() -> None:
    session = _session(timeout_minutes=5)
    idle = _session(timeout_minutes=5, last_activity_at=utc_now() - timedelta(minutes=6))
    assert session.should_lock() is False
    assert idle.should_lock() is True
    assert idle.idle_seconds() >= 300
    assert idle.seconds_until_lock() <= 0
    assert session.seconds_until_lock() > 0


def test_touch_resets_the_clock_without_mutating_the_original() -> None:
    old = _session(last_activity_at=utc_now() - timedelta(minutes=10))
    new = old.touch()
    assert old.idle_seconds() >= 590
    assert new.idle_seconds() < 5
    assert new is not old


def test_lock_and_unlock() -> None:
    session = _session()
    locked = session.lock()
    assert locked.locked and not session.locked
    assert locked.unlock().locked is False


def test_reauthentication_expires() -> None:
    session = _session()
    assert session.is_reauthentication_valid() is False
    fresh = session.grant_reauthentication()
    assert fresh.is_reauthentication_valid() is True
    stale = _session(reauthenticated_at=utc_now() - timedelta(minutes=REAUTH_VALID_MINUTES + 1))
    assert stale.is_reauthentication_valid() is False
    assert fresh.clear_reauthentication().is_reauthentication_valid() is False


def test_timeout_choices_are_the_configured_ones() -> None:
    assert AUTO_LOCK_OPTIONS == (5, 10, 15, 30)
    assert DEFAULT_AUTO_LOCK_MINUTES in AUTO_LOCK_OPTIONS
    session = _session().with_timeout(30)
    assert session.timeout_minutes == 30
    assert _session().with_timeout(45).timeout_minutes == DEFAULT_AUTO_LOCK_MINUTES


def test_roles_and_permissions_can_be_narrowed_for_a_task() -> None:
    session = _session()
    narrowed = session.with_permissions(frozenset({"patient.view"}))
    assert narrowed.has("patient.view")
    assert not narrowed.has("invoice.create")
    assert session.has("invoice.create"), "the original must be untouched"
    renamed = session.with_roles(("Receptionist",))
    assert renamed.roles == ("Receptionist",)


def test_current_session_registry_is_thread_scoped() -> None:
    from dentiva.core.errors import AuthenticationRequired

    assert current() is None
    with pytest.raises(AuthenticationRequired):
        current_or_fail()
    session = _session()
    set_current(session)
    assert current() is session
    assert list(iter_permissions(session)) == sorted(session.permissions)


def test_a_locked_session_cannot_be_used_as_the_actor() -> None:
    from dentiva.core.errors import AuthenticationRequired

    set_current(_session(locked=True))
    with pytest.raises(AuthenticationRequired, match="locked"):
        current_or_fail()


def test_acting_as_restores_the_previous_actor() -> None:
    outer = _session(username="outer")
    inner = _session(username="inner")
    set_current(outer)
    with ActingAs(inner) as active:
        assert active is inner
        assert current() is inner
    assert current() is outer


def test_session_ids_are_unique() -> None:
    identifiers = {new_session_id() for _ in range(100)}
    assert len(identifiers) == 100
