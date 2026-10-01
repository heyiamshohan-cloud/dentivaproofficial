"""In-memory session, activity clock and lock policy (docs/05 §3).

The session is **never** written to disk: it holds no credential, only the
resolved permission set. Auto-lock is driven by one application-level activity
monitor, so it behaves identically on every screen.

Auto-lock never destroys work (REQ-AUTH-004): locking is a state on the session
object, not a teardown. The application keeps the main window and any open editor
alive, autosaves drafts, and restores them after a successful unlock.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from dentiva.core.clock import utc_now
from dentiva.core.errors import AuthenticationRequired

#: Auto-lock options offered in Settings (minutes). Default 15.
AUTO_LOCK_OPTIONS: tuple[int, ...] = (5, 10, 15, 30)
DEFAULT_AUTO_LOCK_MINUTES = 15

#: How long a password re-authentication stays valid for sensitive actions.
REAUTH_VALID_MINUTES = 5

MIN_PASSWORD_LENGTH_HINT = 10


@dataclass(frozen=True, slots=True)
class Session:
    """The signed-in user, their permissions and their activity clock."""

    session_id: str
    user_id: int
    username: str
    display_name: str
    roles: tuple[str, ...]
    permissions: frozenset[str]
    business_id: int | None = None
    is_system_admin: bool = False
    timeout_minutes: int = DEFAULT_AUTO_LOCK_MINUTES
    started_at: datetime = field(default_factory=utc_now)
    last_activity_at: datetime = field(default_factory=utc_now)
    reauthenticated_at: datetime | None = None
    locked: bool = False

    def has(self, permission: str) -> bool:
        return permission in self.permissions

    def has_any(self, *permissions: str) -> bool:
        return any(permission in self.permissions for permission in permissions)

    def touch(self) -> Session:
        """Return a copy with the activity clock reset (sessions are immutable)."""
        return replace(self, last_activity_at=utc_now())

    def with_permissions(self, permissions: frozenset[str]) -> Session:
        return replace(self, permissions=permissions)

    def with_roles(self, roles: tuple[str, ...]) -> Session:
        return replace(self, roles=roles)

    def with_timeout(self, minutes: int) -> Session:
        return replace(self, timeout_minutes=_valid_timeout(minutes))

    def lock(self) -> Session:
        return replace(self, locked=True, reauthenticated_at=None)

    def unlock(self) -> Session:
        return replace(self, locked=False, last_activity_at=utc_now(), reauthenticated_at=utc_now())

    def grant_reauthentication(self) -> Session:
        return replace(self, reauthenticated_at=utc_now(), last_activity_at=utc_now())

    def clear_reauthentication(self) -> Session:
        return replace(self, reauthenticated_at=None)

    def idle_seconds(self, now: datetime | None = None) -> float:
        moment = now or utc_now()
        return max(0.0, (moment - self.last_activity_at).total_seconds())

    def seconds_until_lock(self, now: datetime | None = None) -> float:
        return max(0.0, self.timeout_minutes * 60 - self.idle_seconds(now))

    def should_lock(self, now: datetime | None = None) -> bool:
        return not self.locked and self.idle_seconds(now) >= self.timeout_minutes * 60

    def is_reauthentication_valid(self, now: datetime | None = None) -> bool:
        if self.reauthenticated_at is None:
            return False
        moment = now or utc_now()
        return moment - self.reauthenticated_at < timedelta(minutes=REAUTH_VALID_MINUTES)


def new_session_id() -> str:
    return uuid.uuid4().hex


def _valid_timeout(minutes: int) -> int:
    if minutes in AUTO_LOCK_OPTIONS:
        return minutes
    return DEFAULT_AUTO_LOCK_MINUTES


# ------------------------------------------------------------------ registry --
# A single signed-in user per process; worker threads inherit it explicitly by
# passing the Session into the service call, never by reading it implicitly.
_STATE = threading.local()


def set_current(session: Session | None) -> None:
    """Set (or clear) the process-wide current session."""
    _STATE.session = session


def current() -> Session | None:
    return getattr(_STATE, "session", None)


def current_or_fail() -> Session:
    """Return the current session or raise :class:`AuthenticationRequired`."""
    session = current()
    if session is None:
        raise AuthenticationRequired("Please sign in to continue.")
    if session.locked:
        raise AuthenticationRequired("The application is locked. Enter your password to continue.")
    return session


class ActingAs:
    """Context manager that runs a block as *session* (tests and worker tasks)."""

    def __init__(self, session: Session | None) -> None:
        self.session = session
        self.previous: Session | None = None

    def __enter__(self) -> Session | None:
        self.previous = current()
        set_current(self.session)
        return self.session

    def __exit__(self, *_exc: object) -> None:
        set_current(self.previous)


def iter_permissions(session: Session) -> Iterator[str]:
    """Yield the session's permissions in a stable order (for audit records)."""
    yield from sorted(session.permissions)
