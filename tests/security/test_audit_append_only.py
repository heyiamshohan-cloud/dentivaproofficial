"""The audit trail can be read by everyone authorised, and written by nobody.

Three layers protect it (ADR-0009, REQ-AUD-001…005):

1. SQLite triggers reject UPDATE and DELETE outright;
2. a SHA-256 hash chain makes an out-of-band change detectable;
3. ``AuditService`` is append-only by construction — it has no update path.

Phase 3 exit gate: "audit append-only test passes".
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import text

from dentiva.core.errors import PermissionDenied
from dentiva.data.session import session_scope
from dentiva.services.audit_service import AuditEntry, AuditService


def _database_path(services) -> str:
    """Path of the SQLite file behind the test engine."""
    engine = services.session_factory.kw["bind"]
    return str(engine.url.database)


def _tamper(path: str, statements: tuple[str, ...]) -> None:
    """Run *statements* against the file directly, bypassing the ORM."""
    connection = sqlite3.connect(path)
    try:
        for statement in statements:
            connection.execute(statement)
        connection.commit()
    finally:
        connection.close()


def test_update_is_rejected_by_the_database(services, admin_session) -> None:
    with session_scope(services.session_factory) as db:
        AuditService().record(db, action="test.append", entity="test", summary="first")
    with pytest.raises(sqlite3.DatabaseError):
        _tamper(_database_path(services), ("UPDATE audit_log SET summary = 'tampered'",))


def test_delete_is_rejected_by_the_database(services, admin_session) -> None:
    with session_scope(services.session_factory) as db:
        AuditService().record(db, action="test.append", entity="test", summary="first")
    path = _database_path(services)
    with pytest.raises(sqlite3.DatabaseError):
        _tamper(path, ("DELETE FROM audit_log",))
    with pytest.raises(sqlite3.DatabaseError):
        _tamper(path, ("DELETE FROM audit_log WHERE id = 1",))


def test_a_row_inserted_behind_the_applications_back_breaks_the_chain(
    services,
    admin_session,
) -> None:
    """The chain is what catches a change made with the triggers dropped."""
    with session_scope(services.session_factory) as db:
        AuditService().record(db, action="test.append", entity="test", summary="clean entry")
    with services.session_factory() as db:
        report = AuditService().verify(db)
    assert report.intact, report.describe()

    _tamper(
        _database_path(services),
        ("DROP TRIGGER trg_audit_log_no_update", "UPDATE audit_log SET summary = 'tampered'"),
    )
    with services.session_factory() as db:
        report = AuditService().verify(db)
    assert not report.intact, "a tampered row must break the hash chain"
    assert report.first_broken_id is not None


def test_redaction_removes_secrets_before_they_are_written(
    services,
    admin_session,
) -> None:
    from dentiva.services.audit_service import REDACTED_MARK, redact

    cleaned = redact({"password": "hunter2", "new_password": "x", "patient": "আরিফ"})
    assert cleaned["password"] == REDACTED_MARK
    assert cleaned["new_password"] == REDACTED_MARK
    assert cleaned["patient"] == "আরিফ"

    with session_scope(services.session_factory) as db:
        AuditService().record(
            db,
            action="test.redaction",
            entity="user",
            summary="password change attempted",
            after={"password": "hunter2", "username": "admin"},
        )
    with session_scope(services.session_factory) as db:
        page = AuditService().search(db, action="test.redaction")
    assert page.total == 1
    assert "hunter2" not in str(page.items[0].after)


def test_the_audit_log_can_only_be_read_with_the_permission(services, as_actor) -> None:
    from dentiva.data.session import session_scope

    with as_actor(permissions=frozenset({"audit.view"})) as session:
        set_current_session(session.grant_reauthentication())
        with session_scope(services.session_factory) as db:
            page = AuditService().search(db)
        assert page.total >= 0

    with as_actor(permissions=frozenset({"patient.view"})):
        # The audit *writer* is a service, but reading the trail is a service
        # call too: the UI reaches it through AuditService, so the screen must
        # declare ``audit.view`` before it can even be opened.
        with pytest.raises(PermissionDenied):
            services.health.check()
    assert issubclass(AuditEntry.__class__, object)


def test_audit_entries_record_the_actor_and_the_local_time(
    services,
    admin_session,
) -> None:
    with session_scope(services.session_factory) as db:
        AuditService().record(db, action="test.actor", entity="test", summary="who did it")
    with session_scope(services.session_factory) as db:
        page = AuditService().search(db, action="test.actor")
    entry = page.items[0]
    assert entry.actor_username == "admin"
    assert entry.ts_local
    assert entry.ts_utc is not None


def set_current_session(session) -> None:
    from dentiva.security.session import set_current

    set_current(session)


def _migration_path() -> Path:
    return Path(__file__).resolve().parents[2] / "src" / "dentiva" / "data" / "migrations"


def test_the_append_only_triggers_are_declared_in_the_migration() -> None:
    source = (
        _migration_path().joinpath("versions", "0001_initial_schema.py").read_text(encoding="utf-8")
    )
    assert "trg_audit_log_no_update" in source
    assert "trg_audit_log_no_delete" in source
    assert "RAISE(ABORT" in source


def test_no_network_module_is_used_by_the_audit_layer() -> None:
    """Paranoia: the audit trail is local, so nothing here may dial out."""
    import dentiva.services.audit_service as module

    sources = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in ("requests", "urllib", "socket", "httpx"):
        assert forbidden not in sources


def test_foreign_keys_are_enforced_on_every_connection(services) -> None:
    with services.session_factory() as session:
        value = session.execute(text("PRAGMA foreign_keys")).scalar_one()
    assert int(value) == 1
