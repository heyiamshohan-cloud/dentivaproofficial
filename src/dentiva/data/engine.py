"""SQLite engine construction, PRAGMA policy and integrity checks."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import Connection

from dentiva.core.errors import IntegrityError, MigrationError

#: PRAGMAs applied to every connection (REQ-DB-005, ADR-0002).
PRAGMAS = {
    "foreign_keys": "ON",
    "journal_mode": "WAL",
    "synchronous": "FULL",
    "busy_timeout": "5000",
    "temp_store": "MEMORY",
}


def database_url(path: str | Path) -> str:
    """Return the SQLAlchemy URL for a SQLite database file."""
    return f"sqlite:///{Path(path).as_posix()}"


def create_engine_for(path: str | Path, *, echo: bool = False) -> Engine:
    """Create an engine with the mandatory PRAGMA policy attached."""
    target = Path(path)
    if target.parent and str(target.parent) not in ("", "."):
        target.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url(target), echo=echo, future=True)
    event.listen(engine, "connect", _apply_pragmas)
    return engine


def _apply_pragmas(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        for key, value in PRAGMAS.items():
            cursor.execute(f"PRAGMA {key}={value}")
    finally:
        cursor.close()


def upgrade(engine_or_url: Engine | str, *, revision: str = "head") -> None:
    """Apply Alembic migrations up to *revision* (imports Alembic lazily)."""
    from alembic import command

    config = _alembic_config(engine_or_url)
    try:
        command.upgrade(config, revision)
    except Exception as exc:  # surface as a domain error, keep the cause in the log
        raise MigrationError(
            "The clinic database could not be prepared for this version.",
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


def current_revision(engine_or_url: Engine | str) -> str | None:
    """Return the schema revision stamped in the database (None when empty)."""
    from alembic.migration import MigrationContext

    engine = (
        engine_or_url
        if isinstance(engine_or_url, Engine)
        else create_engine_for_db_url(engine_or_url)
    )
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()


def create_engine_for_db_url(url: str) -> Engine:
    """Create an engine from a raw SQLAlchemy URL (helper for migration contexts)."""
    engine = create_engine(url, future=True)
    event.listen(engine, "connect", _apply_pragmas)
    return engine


def _alembic_config(engine_or_url: Engine | str) -> Any:
    from alembic.config import Config

    from dentiva.data.migrations import script_location

    url = engine_or_url if isinstance(engine_or_url, str) else str(engine_or_url.url)
    config = Config()
    config.set_main_option("script_location", str(script_location()))
    config.set_main_option("sqlalchemy.url", url)
    return config


def check_integrity(connection: Connection) -> list[str]:
    """Run SQLite integrity and foreign-key checks; return a list of problems."""
    problems: list[str] = []
    result = connection.execute(text("PRAGMA integrity_check")).fetchall()
    for row in result:
        if str(row[0]).lower() != "ok":
            problems.append(f"integrity_check: {row[0]}")
    violations = connection.execute(text("PRAGMA foreign_key_check")).fetchall()
    for row in violations:
        problems.append(
            f"foreign_key_violation: table={row[0]} rowid={row[1] if len(row) > 1 else '?'} "
            f"parent={row[2] if len(row) > 2 else '?'}"
        )
    return problems


def assert_healthy(engine: Engine) -> None:
    """Raise :class:`IntegrityError` when the database fails an integrity check."""
    with engine.connect() as connection:
        problems = check_integrity(connection)
    if problems:
        raise IntegrityError(
            "The clinic database reported an integrity problem.",
            detail="; ".join(problems[:5]),
            problems=problems,
        )


def backup_database(source_engine: Engine, target_path: str | Path, *, pages: int = 100) -> Path:
    """Create a consistent snapshot using the SQLite online-backup API (ADR-0008)."""
    destination = Path(target_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw_source = source_engine.raw_connection().driver_connection
    assert isinstance(raw_source, sqlite3.Connection)
    target = sqlite3.connect(str(destination))
    try:
        raw_source.backup(target, pages=pages)
        target.commit()
    finally:
        target.close()
    return destination
