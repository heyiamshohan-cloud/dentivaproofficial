"""Operational tables: settings, numbering, notifications, audit, backups,
printing and managed binary assets (docs/04 §7).

``audit_log`` is append-only: SQLite triggers (created in the migration) reject
UPDATE and DELETE, and every row carries a SHA-256 hash chain link
(ADR-0009). Tampering is therefore detectable, not merely discouraged.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dentiva.data.base import AuditColumns, Base


class Asset(Base):
    """A managed binary file (logo, patient photo, signature, attachment)."""

    __tablename__ = "asset"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    relpath: Mapped[str] = mapped_column(String(400), nullable=False, unique=True)
    mime: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, default="other")
    created_at_utc: Mapped[datetime] = mapped_column(nullable=False)


class Setting(Base):
    """Typed key/value settings store (the only configuration source)."""

    __tablename__ = "settings"
    __table_args__ = (Index("uq_settings_namespace_key", "namespace", "key", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    namespace: Mapped[str] = mapped_column(String(40), nullable=False, default="app")
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False, default="str")
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    updated_at_utc: Mapped[datetime] = mapped_column(nullable=False)


class NumberSequence(Base):
    """Per-business counters for human-visible document numbers."""

    __tablename__ = "number_sequence"
    __table_args__ = (
        Index("uq_number_sequence_business_id_scope", "business_id", "scope", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    next_value: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    padding: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    year_reset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ActivationRecord(Base):
    """Proof of offline activation (HMAC over the machine id) — never the code."""

    __tablename__ = "activation_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[str] = mapped_column(String(128), nullable=False)
    token: Mapped[str] = mapped_column(String(128), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False, default="hmac-sha256")
    activated_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Notification(Base):
    """A system-generated alert, optionally gated by its own permission."""

    __tablename__ = "notification"
    __table_args__ = (
        Index(
            "ix_notification_business_id_created_at_utc_kind",
            "business_id",
            "created_at_utc",
            "kind",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    patient_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient.id", ondelete="CASCADE"), nullable=True
    )
    required_permission: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    expires_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)


class NotificationRead(Base):
    """Per-user read state (composite key: notification + user)."""

    __tablename__ = "notification_read"
    __table_args__ = (
        Index("uq_notification_read_pair", "notification_id", "user_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    notification_id: Mapped[int] = mapped_column(
        ForeignKey("notification.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    read_at_utc: Mapped[datetime] = mapped_column(nullable=False)


class AuditLog(Base):
    """Append-only audit trail with a SHA-256 hash chain (ADR-0009).

    ``prev_hash`` / ``row_hash`` make silent editing detectable; the triggers
    created in migration ``0001`` make UPDATE/DELETE impossible outright.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_business_id_ts_utc", "business_id", "ts_utc"),
        Index("ix_audit_log_entity_entity_id", "entity", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts_utc: Mapped[datetime] = mapped_column(nullable=False)
    ts_local: Mapped[str | None] = mapped_column(String(32), nullable=True)
    business_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_role_names: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    patient_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="app")
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")


class BackupRecord(AuditColumns, Base):
    """One backup attempt, its verification outcome and integrity evidence."""

    __tablename__ = "backup_record"
    __table_args__ = (Index("ix_backup_record_created_at_utc", "created_at_utc"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int | None] = mapped_column(
        ForeignKey("business.id", ondelete="SET NULL"), nullable=True
    )
    file_path: Mapped[str] = mapped_column(String(600), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_progress")
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    verification_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    schema_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    db_integrity: Mapped[str | None] = mapped_column(String(32), nullable=True)
    triggered_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PrinterProfile(AuditColumns, Base):
    """Paper/printer/template profile for prescriptions, invoices and receipts."""

    __tablename__ = "printer_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    paper: Mapped[str] = mapped_column(String(16), nullable=False, default="A4")
    width_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_top_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_right_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_bottom_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    margin_left_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    orientation: Mapped[str] = mapped_column(String(16), nullable=False, default="portrait")
    base_font_pt: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    template_variant: Mapped[str] = mapped_column(String(16), nullable=False, default="full")
    printer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_default_for: Mapped[str | None] = mapped_column(String(40), nullable=True)
    show_logo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    show_signature: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    footer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PrintJob(Base):
    """Reprint history for the Print Center."""

    __tablename__ = "print_job"
    __table_args__ = (
        Index("ix_print_job_document_type_document_id", "document_type", "document_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_type: Mapped[str] = mapped_column(String(40), nullable=False)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False)
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("printer_profile.id", ondelete="SET NULL"), nullable=True
    )
    printer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    printed_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    printed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    pages: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    result: Mapped[str] = mapped_column(String(16), nullable=False, default="ok")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
