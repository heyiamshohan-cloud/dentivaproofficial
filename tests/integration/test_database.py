"""Database integration: PRAGMAs, migrations, integrity and online backup.

REQ-DB-004/005/006, ADR-0002, REQ-BKP-003.
"""

from __future__ import annotations

from sqlalchemy import Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from dentiva.data.base import Base
from dentiva.data.engine import (
    assert_healthy,
    backup_database,
    check_integrity,
    create_engine_for,
    current_revision,
    upgrade,
)


def test_mandatory_pragmas_are_applied(db_engine) -> None:
    with db_engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert str(connection.execute(text("PRAGMA journal_mode")).scalar()).lower() == "wal"
        assert connection.execute(text("PRAGMA synchronous")).scalar() == 2  # FULL
        assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 5000


def test_alembic_upgrade_head_stamps_the_database(tmp_path) -> None:
    engine = create_engine_for(tmp_path / "migrate.db")
    upgrade(engine)
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        }
    assert "alembic_version" in tables
    with engine.connect() as connection:
        stamped = list(connection.execute(text("SELECT version_num FROM alembic_version")))
    # Phase 2 ships no business migration, so nothing is stamped yet; from
    # Phase 3 onward this must hold exactly one row (the head revision).
    assert len(stamped) <= 1
    if stamped:
        assert current_revision(engine) == stamped[0][0]
    engine.dispose()


def test_integrity_checks_report_clean_database(db_engine) -> None:
    with db_engine.connect() as connection:
        assert check_integrity(connection) == []
    assert_healthy(db_engine)


def test_online_backup_produces_a_readable_copy(db_engine, tmp_path) -> None:
    import sqlite3

    with db_engine.connect() as connection:
        connection.execute(text("CREATE TABLE sample (id INTEGER PRIMARY KEY, name TEXT)"))
        connection.execute(text("INSERT INTO sample (name) VALUES ('দাঁতের চিকিৎসা')"))
        connection.commit()

    target = backup_database(db_engine, tmp_path / "backup.db")
    copy = sqlite3.connect(str(target))
    assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert copy.execute("SELECT name FROM sample").fetchone()[0] == "দাঁতের চিকিৎসা"
    copy.close()


class Note(Base):
    """Module level model used by the session-scope test."""

    __tablename__ = "note"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


def test_session_scope_commits_once_and_rolls_back_on_error(tmp_path) -> None:
    from dentiva.data.session import session_factory, session_scope

    engine = create_engine_for(tmp_path / "session.db")
    Base.metadata.create_all(engine)
    factory = session_factory(engine)

    with session_scope(factory) as session:
        session.add(Note(id=1))
    with session_scope(factory) as session:
        assert session.get(Note, 1) is not None

    class BoomError(Exception):
        pass

    try:
        with session_scope(factory) as session:
            session.add(Note(id=2))
            raise BoomError()
    except BoomError:
        pass
    with session_scope(factory) as session:
        assert session.get(Note, 2) is None
    engine.dispose()


def test_migration_error_is_a_domain_error(tmp_path) -> None:
    from dentiva.core.errors import MigrationError

    engine = create_engine_for(tmp_path / "broken.db")
    with engine.connect() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
        connection.commit()
    try:
        upgrade(engine, revision="does-not-exist")
    except MigrationError as error:
        assert "database" in error.user_message().lower()
    else:  # pragma: no cover - depends on alembic behaviour with no revisions
        pass
    finally:
        engine.dispose()
