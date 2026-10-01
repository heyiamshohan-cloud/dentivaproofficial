"""SQLite engine construction, PRAGMA policy and integrity checks."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import Connection

from dentiva.core.clock import utc_now
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


def upgrade(
    engine_or_url: Engine | str,
    *,
    revision: str = "head",
    safety_backup_dir: str | Path | None = None,
) -> Path | None:
    """Apply Alembic migrations up to *revision* (imports Alembic lazily).

    SQLite DDL is not transactional in every failure mode, so a migration can
    leave a half-built schema behind. Dentiva Pro therefore behaves like a
    database product rather than a script (REQ-DB-006, docs/04 §10):

    1. if a migration is pending and the database already holds data, a
       **pre-upgrade safety backup** is taken automatically;
    2. the upgrade runs;
    3. on failure the partial database is replaced by that backup (or, for a
       database that was still empty, removed so the next start rebuilds it) and
       a :class:`MigrationError` carrying the recovery information is raised.

    Returns the path of the safety backup when one was taken, else ``None``.
    """
    from alembic import command

    engine = (
        engine_or_url
        if isinstance(engine_or_url, Engine)
        else create_engine_for_db_url(engine_or_url)
    )
    db_path = _database_file(engine)
    had_tables = _has_user_tables(engine)
    backup_path: Path | None = None
    if had_tables and db_path is not None and safety_backup_dir is not None:
        timestamp = utc_now().strftime("%Y%m%d-%H%M%S")
        backup_path = Path(safety_backup_dir) / f"pre-upgrade-{timestamp}.db"
        backup_database(engine, backup_path)

    config = _alembic_config(str(engine.url))
    try:
        command.upgrade(config, revision)
    except Exception as exc:
        recovered = _recover_after_failed_upgrade(engine, db_path, backup_path, had_tables)
        raise MigrationError(
            "The clinic database could not be prepared for this version.",
            detail=f"{type(exc).__name__}: {exc}",
            recovery=str(recovered) if recovered else "",
        ) from exc
    return backup_path


def downgrade(
    engine_or_url: Engine | str,
    *,
    revision: str = "base",
) -> None:
    """Roll migrations back to *revision* (docs/04 §10: revisions are reversible).

    Reversal is a maintenance operation, never part of normal start-up, so it
    does not take the automatic safety backup that :func:`upgrade` takes: a
    downgrade is destructive by definition and the caller (a support engineer
    restoring an older build) must have taken a backup first.
    """
    from alembic import command

    engine = (
        engine_or_url
        if isinstance(engine_or_url, Engine)
        else create_engine_for_db_url(engine_or_url)
    )
    config = _alembic_config(str(engine.url))
    try:
        command.downgrade(config, revision)
    except Exception as exc:
        raise MigrationError(
            "The clinic database could not be rolled back to the requested revision.",
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


def _database_file(engine: Engine) -> Path | None:
    """Path of the SQLite file behind *engine* (``None`` for in-memory URLs)."""
    database = engine.url.database
    return Path(database) if database and database != ":memory:" else None


def _has_user_tables(engine: Engine) -> bool:
    """True when the database already contains at least one table."""
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT count(*) FROM sqlite_master WHERE type='table'")
        ).scalar()
    return bool(rows)


def _recover_after_failed_upgrade(
    engine: Engine,
    db_path: Path | None,
    backup_path: Path | None,
    had_tables: bool,
) -> Path | None:
    """Put the database back the way it was before a failed migration."""
    engine.dispose()
    if db_path is None:
        return None
    if backup_path is not None and backup_path.is_file():
        # Restore the snapshot and drop the WAL/SHM files of the broken state.
        shutil.copyfile(backup_path, db_path)
        for suffix in ("-wal", "-shm"):
            sidecar = db_path.with_name(db_path.name + suffix)
            if sidecar.exists():
                sidecar.unlink()
        return backup_path
    if not had_tables:
        # The database was still empty: remove the partial schema so the next
        # start rebuilds it from scratch instead of failing forever.
        for suffix in ("", "-wal", "-shm"):
            candidate = db_path.with_name(db_path.name + suffix)
            if candidate.exists():
                candidate.unlink()
    return None


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
    # Alembic stores options in a ConfigParser, where "%" starts an
    # interpolation. A SQLAlchemy URL percent-escapes the colon of a Windows
    # drive ("sqlite:///C%3A/..."), so it must be doubled here and is turned
    # back into a single "%" when Alembic reads the option.
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
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
