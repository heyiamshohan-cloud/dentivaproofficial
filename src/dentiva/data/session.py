"""Session management: one session per unit of work / per background task.

Sessions are never shared between threads (ADR-0012) and every write goes through
:func:`session_scope`, which commits once and rolls back on any exception.

Audit stamping (``created_at_utc`` / ``updated_at_utc`` / ``*_by_user_id``) is
applied by a ``before_flush`` listener rather than by each service, so a missing
stamp is impossible to forget.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, event
from sqlalchemy.orm import Session, sessionmaker

from dentiva.core.clock import utc_now

SessionMaker = sessionmaker

_TIMESTAMPED = ("created_at_utc", "updated_at_utc")
_ACTOR_FIELDS = ("created_by_user_id", "updated_by_user_id")


def session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a ``sessionmaker`` bound to *engine* (expire_on_commit disabled)."""
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


def _current_user_id() -> int | None:
    """The signed-in user, when a session is bound to this thread."""
    from dentiva.security.session import current

    session = current()
    return None if session is None else session.user_id


def _stamp(session: Session) -> None:
    """Fill audit columns on new and modified rows before every flush."""
    now = utc_now()
    actor = _current_user_id()
    for obj in session.new:
        if not all(hasattr(obj, field) for field in _TIMESTAMPED):
            continue
        if getattr(obj, "created_at_utc", None) is None:
            obj.created_at_utc = now
        if getattr(obj, "updated_at_utc", None) is None:
            obj.updated_at_utc = now
        if actor is not None and getattr(obj, "created_by_user_id", None) is None:
            obj.created_by_user_id = actor
        if actor is not None and getattr(obj, "updated_by_user_id", None) is None:
            obj.updated_by_user_id = actor
    for obj in session.dirty:
        if not hasattr(obj, "updated_at_utc"):
            continue
        if not session.is_modified(obj, include_collections=False):
            continue
        obj.updated_at_utc = now
        if actor is not None and hasattr(obj, "updated_by_user_id"):
            obj.updated_by_user_id = actor


@event.listens_for(Session, "before_flush")
def _before_flush(session: Session, _flush_context: object, _instances: object) -> None:
    _stamp(session)


@contextmanager
def session_scope(factory: sessionmaker[Session] | Engine) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations.

    * commits on clean exit,
    * rolls back on any exception (never leaves a partial financial/clinical write),
    * always closes the session.
    """
    maker = factory if isinstance(factory, sessionmaker) else session_factory(factory)
    session = maker()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
