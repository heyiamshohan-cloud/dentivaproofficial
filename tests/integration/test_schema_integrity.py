"""The shipped schema *is* the model (docs/04, REQ-DB-001…006).

Phase 3 exit gate: "schema matches docs/04; PRAGMA integrity/foreign-key checks
clean". This test upgrades a brand-new database with the real Alembic migration
and compares the result against the ORM metadata, so a model change that was
never migrated (or a migration that drifts from the models) fails the build.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from dentiva.data.base import Base
from dentiva.data.engine import (
    check_integrity,
    create_engine_for,
    current_revision,
    downgrade,
    upgrade,
)
from dentiva.data.models import *  # noqa: F403 - every mapper must be registered
from dentiva.data.models import Base as ModelBase

EXPECTED_TRIGGERS = {"trg_audit_log_no_update", "trg_audit_log_no_delete"}


@pytest.fixture()
def migrated(tmp_path):  # type: ignore[no-untyped-def]
    engine = create_engine_for(tmp_path / "schema.db")
    upgrade(engine, safety_backup_dir=tmp_path)
    yield engine
    engine.dispose()


def _tables(engine) -> set[str]:
    with engine.connect() as connection:
        return {
            row[0]
            for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        }


def test_migration_reaches_a_known_revision(migrated) -> None:
    revision = current_revision(migrated)
    assert revision, "the database must carry a schema revision"


def test_every_model_table_exists_after_the_migration(migrated) -> None:
    present = _tables(migrated)
    missing = sorted(set(ModelBase.metadata.tables) - present)
    assert not missing, f"tables missing after upgrade: {missing}"


def test_no_table_exists_that_the_models_do_not_know(migrated) -> None:
    present = _tables(migrated)
    extra = sorted(
        present - set(ModelBase.metadata.tables) - {"alembic_version", "sqlite_sequence"}
    )
    assert not extra, f"unexpected tables: {extra}"


def test_integrity_and_foreign_keys_are_clean(migrated) -> None:
    with migrated.connect() as connection:
        assert check_integrity(connection) == []


def test_foreign_key_enforcement_is_on(migrated) -> None:
    with migrated.connect() as connection:
        assert int(connection.execute(text("PRAGMA foreign_keys")).scalar_one()) == 1


def test_the_append_only_triggers_exist(migrated) -> None:
    with migrated.connect() as connection:
        triggers = {
            row[0]
            for row in connection.execute(
                text("SELECT name FROM sqlite_master WHERE type='trigger'")
            )
        }
    assert triggers >= EXPECTED_TRIGGERS, f"missing triggers: {EXPECTED_TRIGGERS - triggers}"


def test_money_columns_are_stored_as_integers(migrated) -> None:
    """ADR-0003: no REAL/FLOAT money column may ever reach the schema."""
    from dentiva.data.models.billing import Invoice

    offenders: list[str] = []
    with migrated.connect() as connection:
        for row in connection.execute(text("PRAGMA table_info(invoice)")):
            name, declared = str(row[1]), str(row[2]).upper()
            if name.endswith("_paisa") and declared != "INTEGER":
                offenders.append(f"invoice.{name} -> {declared}")
    assert not offenders, f"money columns must be INTEGER: {offenders}"
    assert "total_paisa" in Invoice.__table__.columns


def test_unique_indexes_that_the_product_depends_on(migrated) -> None:
    with migrated.connect() as connection:
        indexes = {
            row[0]
            for row in connection.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))
        }
    required = {
        "uq_invoice_business_id_number",
        "uq_patient_business_id_code",
        "uq_settings_namespace_key",
        "uq_user_role_pair",
        "uq_payment_invoice_id_idempotency_key",
        "uq_queue_entry_active_patient_per_day",
    }
    missing = sorted(required - indexes)
    assert not missing, f"required unique indexes missing: {missing}"


def test_the_schema_survives_a_second_upgrade(migrated) -> None:
    """Running the migrator again must be a no-op, never a data-destroying event."""
    before = _tables(migrated)
    upgrade(migrated, safety_backup_dir=None)
    assert _tables(migrated) == before


def test_a_database_file_is_created_next_to_the_data_directory(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "clinic.db"
    engine = create_engine_for(target)
    assert target.parent.is_dir(), "the engine must create missing directories"
    engine.dispose()


def test_base_metadata_is_the_single_source_of_truth() -> None:
    assert Base is ModelBase
    assert len(ModelBase.metadata.tables) >= 60, "the clinic model should cover ~60 tables"


def test_no_test_module_declares_a_table_on_the_product_base() -> None:
    """Guard: a test model on ``dentiva.data.base.Base`` silently becomes a
    "missing table" in the migration check above. Tests must use a private
    declarative base (see ``tests/unit/test_money.py``)."""
    from pathlib import Path

    tests_root = Path(__file__).resolve().parent.parent
    offenders = sorted(
        str(path.relative_to(tests_root))
        for path in tests_root.rglob("*.py")
        if "__tablename__" in path.read_text(encoding="utf-8")
        and "dentiva.data.base import" in path.read_text(encoding="utf-8")
        and "DeclarativeBase" not in path.read_text(encoding="utf-8")
    )
    assert not offenders, f"test models must not use the product Base: {offenders}"


def test_the_migration_is_reversible(tmp_path) -> None:
    """docs/04 §10 claims every revision is reversible: prove the round trip.

    Upgrade → downgrade to ``base`` → upgrade again, and require the schema that
    comes back to be identical to the first one (tables, triggers, integrity).
    """
    engine = create_engine_for(tmp_path / "reversible.db")
    try:
        upgrade(engine, safety_backup_dir=tmp_path)
        first = _tables(engine)

        downgrade(engine, revision="base")
        with engine.connect() as connection:
            remaining = {
                row[0]
                for row in connection.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            }
            triggers = {
                row[0]
                for row in connection.execute(
                    text("SELECT name FROM sqlite_master WHERE type='trigger'")
                )
            }
        assert remaining <= {"alembic_version"}, f"downgrade left tables behind: {remaining}"
        assert triggers & EXPECTED_TRIGGERS == set(), "downgrade must drop the audit triggers"
        assert current_revision(engine) in (None, ""), "the revision stamp must be cleared"

        upgrade(engine, safety_backup_dir=tmp_path)
        assert _tables(engine) == first, "the re-upgraded schema must match the original"
        with engine.connect() as connection:
            assert not check_integrity(connection)
    finally:
        engine.dispose()
