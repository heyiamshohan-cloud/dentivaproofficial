"""Backup, verification and restore (docs/04 §9, REQ-BKP-001…009).

Product behaviour, non-negotiable:

* a backup is a **consistent snapshot** taken with the SQLite online-backup API,
  never a raw file copy that can catch a half-written page;
* it is written to a temporary file and renamed into place, so a crash can never
  leave a truncated backup that looks complete;
* it is **verified** after writing (integrity + foreign keys + schema stamp) and
  the outcome is recorded;
* restoring takes a **pre-restore backup** first and validates the candidate's
  integrity before a single byte of the live database is replaced;
* the destination folder is chosen with a folder picker — never typed by hand.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core import fileutil
from dentiva.core.clock import local_today, utc_now
from dentiva.core.config import NS_BACKUP
from dentiva.core.errors import BackupError, ConfirmationRequired, NotFound
from dentiva.core.hashing import sha256_file
from dentiva.core.paths import AppPaths
from dentiva.data.engine import backup_database
from dentiva.data.models.ops import BackupRecord
from dentiva.security.session import current
from dentiva.services.rbac import internal, require

#: Restore confirmation phrase (typed, never a single click).
RESTORE_PHRASE = "RESTORE"

#: Backup kinds.
KIND_MANUAL = "manual"
KIND_SCHEDULED = "scheduled"
KIND_PRE_RESTORE = "pre_restore"
KIND_PRE_UPGRADE = "pre_upgrade"

#: Schedules offered to the user (days); 0 disables scheduled backups.
SCHEDULE_OFF = 0
SCHEDULE_OPTIONS = (0, 7, 15, 30)


@dataclass(frozen=True, slots=True)
class BackupSummary:
    """One backup as shown on the maintenance screen."""

    id: int
    file_name: str
    file_path: str
    created_at_utc: str
    size_bytes: int
    kind: str
    status: str
    verified: bool
    db_integrity: str
    app_version: str
    schema_version: str
    notes: str
    exists_on_disk: bool


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Outcome of validating a backup file."""

    ok: bool
    integrity: str
    details: str
    patient_count: int
    invoice_count: int
    size_bytes: int


class BackupService:
    """Manual, scheduled and pre-restore backups."""

    def __init__(
        self,
        session_factory: sessionmaker[DBSession],
        *,
        engine: Engine,
        paths: AppPaths | None = None,
        schema_version: str = "",
        app_version: str = "",
    ) -> None:
        self._session_factory = session_factory
        self._engine = engine
        self._paths = paths or AppPaths.create().ensure()
        self._schema_version = schema_version
        self._app_version = app_version

    # ------------------------------------------------------------------ reads --
    @require("backup.create", action="backup.list", entity="backup")
    def list_backups(self, db: DBSession, *, limit: int = 50) -> list[BackupSummary]:
        """Newest backups first, with whether the file is still on disk."""
        rows = (
            db.execute(select(BackupRecord).order_by(BackupRecord.id.desc()).limit(max(1, limit)))
            .scalars()
            .all()
        )
        return [self._summarise(row) for row in rows]

    @require("backup.create", action="backup.status", entity="backup")
    def status(self, db: DBSession) -> tuple[BackupSummary | None, bool, int]:
        """``(latest backup, is a scheduled backup due, days since the last one)``."""
        return self._status(db)

    @internal
    def _status(self, db: DBSession) -> tuple[BackupSummary | None, bool, int]:
        row = db.execute(
            select(BackupRecord)
            .where(BackupRecord.status == "complete")
            .order_by(BackupRecord.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        latest = self._summarise(row) if row else None
        days = _days_since(row.created_at_utc.date() if row else None)
        interval = _coerce_int(self._setting(db, "schedule_days", 7), default=7)
        due = interval > 0 and (latest is None or (days or 0) >= interval)
        return latest, due, days or 0

    @internal
    def default_destination(self, db: DBSession) -> str:
        """Internal: the configured folder, or the managed backups folder."""
        configured = str(self._setting(db, "folder", "") or "").strip()
        return configured or str(self._paths.backups)

    # ----------------------------------------------------------------- writes --
    @require("backup.create", action="backup.create", entity="backup")
    def create(
        self,
        db: DBSession,
        *,
        destination_dir: str,
        business_id: int | None = None,
        kind: str = KIND_MANUAL,
        notes: str = "",
    ) -> BackupSummary:
        """Take a verified snapshot of the live database."""
        return self._create(
            db, destination_dir=destination_dir, business_id=business_id, kind=kind, notes=notes
        )

    @internal
    def _create(
        self,
        db: DBSession,
        *,
        destination_dir: str,
        business_id: int | None = None,
        kind: str = KIND_MANUAL,
        notes: str = "",
    ) -> BackupSummary:
        directory = fileutil.ensure_directory(destination_dir or self.default_destination(db))
        stamp = utc_now().strftime("%Y%m%d-%H%M%S")
        file_name = backup_file_name(stamp)
        final_path = directory / file_name
        record = BackupRecord(
            business_id=business_id,
            file_path=str(final_path),
            file_name=file_name,
            created_at_utc=utc_now(),
            size_bytes=0,
            kind=kind,
            status="in_progress",
            verified=False,
            app_version=self._app_version or None,
            schema_version=self._schema_version or None,
            triggered_by_user_id=_current_user_id(),
            notes=(notes or "").strip() or None,
        )
        db.add(record)
        db.flush()

        temp_path = final_path.with_name(final_path.name + ".partial")
        try:
            fileutil.ensure_free_space(
                directory, _database_size(self._engine) * 2 + 8 * 1024 * 1024
            )
            backup_database(self._engine, temp_path)
            sha = sha256_file(temp_path)
            size = temp_path.stat().st_size
            fileutil.atomic_copy(temp_path, final_path)
            verification = self.verify_file(final_path)
        except (OSError, sqlite3.Error, BackupError) as error:
            record.status = "failed"
            record.verification_error = str(error)
            db.flush()
            raise BackupError("The backup could not be completed.", detail=str(error)) from error
        finally:
            fileutil.remove_file(temp_path)

        record.size_bytes = size
        record.sha256 = sha
        record.status = "complete" if verification.ok else "failed"
        record.verified = verification.ok
        record.verified_at_utc = utc_now() if verification.ok else None
        record.verification_error = None if verification.ok else verification.details
        record.db_integrity = verification.integrity
        db.flush()
        if not verification.ok:
            raise BackupError(
                "The backup was written but failed verification, so it must not be relied on.",
                detail=verification.details,
            )
        return self._summarise(record)

    @require("backup.create", action="backup.verify", entity="backup", entity_id_arg="backup_id")
    def verify(self, db: DBSession, *, backup_id: int) -> VerificationResult:
        """Re-verify a stored backup and record the outcome."""
        record = db.get(BackupRecord, backup_id)
        if record is None:
            raise NotFound("That backup record no longer exists.")
        path = _resolve(record.file_path)
        result = self.verify_file(path)
        record.verified = result.ok
        record.verified_at_utc = utc_now() if result.ok else None
        record.verification_error = None if result.ok else result.details
        record.db_integrity = result.integrity
        record.size_bytes = result.size_bytes or record.size_bytes
        db.flush()
        return result

    @require("backup.restore", action="backup.restore", entity="backup", entity_id_arg="backup_id")
    def restore(
        self,
        db: DBSession,
        *,
        backup_id: int,
        confirmation_phrase: str,
        note: str = "",
    ) -> BackupSummary:
        """Restore the clinic database from a verified backup (sensitive).

        Order of operations (never reordered):
        1. the typed confirmation is checked;
        2. the candidate is validated (integrity, foreign keys, schema stamp);
        3. a **pre-restore backup** of the current database is taken and verified;
        4. only then is the live database replaced.
        """
        if confirmation_phrase.strip().upper() != RESTORE_PHRASE:
            raise ConfirmationRequired(
                "Type RESTORE to replace the current clinic data with this backup. "
                "A safety backup of the current data is taken first.",
                action="backup.restore",
                phrase=RESTORE_PHRASE,
            )
        record = db.get(BackupRecord, backup_id)
        if record is None:
            raise NotFound("That backup record no longer exists.")
        candidate = _resolve(record.file_path)
        validation = self.verify_file(candidate)
        if not validation.ok:
            raise BackupError(
                "This backup is damaged and cannot be restored.", detail=validation.details
            )
        safety = self._create(
            db,
            destination_dir=self.default_destination(db),
            kind=KIND_PRE_RESTORE,
            notes=f"Safety copy before restoring backup #{backup_id} {note}".strip(),
        )
        # The safety backup must be on disk *before* the live file is replaced.
        db.commit()
        try:
            self._replace_live_database(candidate)
        except (OSError, sqlite3.Error) as error:
            raise BackupError(
                "The restore failed. The clinic database was left untouched; "
                f"a safety backup exists at {safety.file_path}.",
                detail=str(error),
            ) from error
        db.flush()
        return safety

    @require("backup.create", action="backup.prune", entity="backup")
    def prune(self, db: DBSession, *, keep_last: int | None = None) -> int:
        """Delete the oldest backups beyond the retention count (never the newest)."""
        keep = (
            keep_last
            if keep_last is not None
            else _coerce_int(self._setting(db, "keep_last", 10), default=10)
        )
        keep = max(1, keep)
        rows = db.execute(select(BackupRecord).order_by(BackupRecord.id.desc())).scalars().all()
        removed = 0
        for row in rows[keep:]:
            fileutil.remove_file(_resolve(row.file_path))
            db.delete(row)
            removed += 1
        db.flush()
        return removed

    @require("backup.create", action="backup.due", entity="backup")
    def scheduled_backup_due(self, db: DBSession) -> bool:
        """Whether a scheduled backup is due today (checked at start-up)."""
        _, due, _ = self._status(db)
        return due

    # ------------------------------------------------------------ verification --
    @internal
    def verify_file(self, path: str | Path) -> VerificationResult:
        """Open *path* read-only and prove it is a usable Dentiva database."""
        candidate = _resolve(path)
        if not candidate.is_file():
            return VerificationResult(False, "missing", f"No such file: {candidate}", 0, 0, 0)
        uri = f"file:{candidate.as_posix()}?mode=ro"
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(uri, uri=True)
            problems = _sqlite_integrity(connection)
            counts = _table_counts(connection)
            schema = _schema_revision(connection)
        except sqlite3.Error as error:
            return VerificationResult(False, "error", str(error), 0, 0, 0)
        finally:
            if connection is not None:
                connection.close()
        if problems:
            return VerificationResult(
                False, "failed", "; ".join(problems[:3]), 0, 0, candidate.stat().st_size
            )
        if counts.get("patient", -1) < 0 or counts.get("business", -1) < 0:
            return VerificationResult(
                False,
                "schema",
                "The file is a valid SQLite database but not a Dentiva Pro clinic database.",
                0,
                0,
                candidate.stat().st_size,
            )
        if self._schema_version and schema and schema != self._schema_version:
            # A newer schema is fine after an upgrade; an unknown one is not.
            return VerificationResult(
                False,
                "schema",
                f"Backup schema revision {schema} does not match this "
                f"application ({self._schema_version}).",
                counts.get("patient", 0),
                counts.get("invoice", 0),
                candidate.stat().st_size,
            )
        return VerificationResult(
            True,
            "ok",
            "integrity and foreign keys verified",
            counts.get("patient", 0),
            counts.get("invoice", 0),
            candidate.stat().st_size,
        )

    # ---------------------------------------------------------------- internals --
    def _setting(self, db: DBSession, key: str, fallback: Any) -> Any:
        from dentiva.data.models.ops import Setting

        row = db.execute(
            select(Setting).where(Setting.namespace == NS_BACKUP, Setting.key == key)
        ).scalar_one_or_none()
        if row is None:
            return fallback
        import json

        try:
            return json.loads(row.value_json)
        except ValueError:
            return fallback

    def _replace_live_database(self, candidate: Path) -> None:
        """Swap the live SQLite file for *candidate* (the engine is reset first)."""
        from dentiva.data.engine import _database_file

        target = _database_file(self._engine)
        if target is None:
            raise BackupError(
                "This installation has no database file on disk, so it cannot be restored."
            )
        self._engine.dispose()
        fileutil.atomic_copy(candidate, target)
        for suffix in ("-wal", "-shm"):
            sidecar = target.with_name(target.name + suffix)
            fileutil.remove_file(sidecar)

    def _summarise(self, record: BackupRecord) -> BackupSummary:
        return BackupSummary(
            id=record.id,
            file_name=record.file_name,
            file_path=record.file_path,
            created_at_utc=record.created_at_utc.isoformat(),
            size_bytes=int(record.size_bytes or 0),
            kind=record.kind,
            status=record.status,
            verified=bool(record.verified),
            db_integrity=record.db_integrity or "",
            app_version=record.app_version or "",
            schema_version=record.schema_version or "",
            notes=record.notes or "",
            exists_on_disk=_resolve(record.file_path).is_file(),
        )


def backup_file_name(stamp: str | None = None) -> str:
    """The timestamped name used for every backup file."""
    return f"dentiva-backup-{stamp or utc_now().strftime('%Y%m%d-%H%M%S')}.db"


def days_until_next_schedule(last_run: date | None, interval_days: int) -> int:
    """Days until the next scheduled backup (0 when it is already due)."""
    if interval_days <= 0 or last_run is None:
        return 0
    elapsed = (local_today() - last_run).days
    return max(0, interval_days - elapsed)


def _coerce_int(value: Any, *, default: int = 0) -> int:
    """Read an integer out of a free-form settings value (never raises)."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return default


def _current_user_id() -> int | None:
    session = current()
    return None if session is None else session.user_id


def _resolve(path: str | Path) -> Path:
    return Path(path)


def _days_since(day: date | None) -> int | None:
    if day is None:
        return None
    return (local_today() - day).days


def _database_size(engine: Engine) -> int:
    from dentiva.data.engine import _database_file

    path = _database_file(engine)
    return path.stat().st_size if path and path.is_file() else 0


def _sqlite_integrity(connection: sqlite3.Connection) -> list[str]:
    problems: list[str] = []
    for row in connection.execute("PRAGMA integrity_check").fetchall():
        if str(row[0]).lower() != "ok":
            problems.append(f"integrity_check: {row[0]}")
    for row in connection.execute("PRAGMA foreign_key_check").fetchall():
        problems.append(
            f"foreign_key_violation: table={row[0]} rowid={row[1] if len(row) > 1 else '?'}"
        )
    return problems


def _table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    counts: dict[str, int] = {}
    for table in ("business", "patient", "invoice", "payment", "visit"):
        counts[table] = (
            int(connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])
            if table in names
            else -1
        )
    return counts


def _schema_revision(connection: sqlite3.Connection) -> str:
    try:
        row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    except sqlite3.Error:
        return ""
    return str(row[0]) if row else ""


def retention_cutoff(days: int) -> date:
    """Files older than this date fall outside the retention window."""
    return local_today() - timedelta(days=max(0, days))
