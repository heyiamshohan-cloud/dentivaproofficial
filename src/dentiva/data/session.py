"""Session management: one session per unit of work / per background task.

Sessions are never shared between threads (ADR-0012) and every write goes through
:func:`session_scope`, which commits once and rolls back on any exception.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

SessionMaker = sessionmaker


def session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a ``sessionmaker`` bound to *engine* (expire_on_commit disabled)."""
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


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
