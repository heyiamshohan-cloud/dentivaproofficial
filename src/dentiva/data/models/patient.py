"""Patients, attachments, merges and duplicate candidates (docs/04 §2).

Deletion policy: patients are **archived** (``is_active=false``); a hard delete is
a separate, authorised, audited, re-authenticated operation (REQ-RET-001/002).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dentiva.data.base import AuditColumns, Base, SoftDeleteColumns, VersionedColumns


class Patient(AuditColumns, SoftDeleteColumns, VersionedColumns, Base):
    """Patient master record. ``code`` is the human-visible identifier."""

    __tablename__ = "patient"
    __table_args__ = (
        Index("uq_patient_business_id_code", "business_id", "code", unique=True),
        Index("ix_patient_business_id_phone_primary", "business_id", "phone_primary"),
        Index("ix_patient_business_id_name_normalised", "business_id", "name_normalised"),
        Index("ix_patient_business_id_registered_at_utc", "business_id", "registered_at_utc"),
        Index("ix_patient_business_id_last_visit_on", "business_id", "last_visit_on"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_normalised: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    guardian_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    relation_of_guardian: Mapped[str | None] = mapped_column(String(40), nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    age_years_cached: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_updated_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(24), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(8), nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    nid_or_passport: Mapped[str | None] = mapped_column(String(64), nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    phone_primary: Mapped[str | None] = mapped_column(String(40), nullable=True)
    phone_secondary: Mapped[str | None] = mapped_column(String(40), nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(24), nullable=False, default="bn")
    referred_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    photo_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset.id", ondelete="SET NULL"), nullable=True
    )
    presenting_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    past_medical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    past_dental_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_medication: Mapped[str | None] = mapped_column(Text, nullable=True)
    habits: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(String(400), nullable=True)
    first_visit_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_visit_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    registered_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PatientAttachment(AuditColumns, SoftDeleteColumns, Base):
    """A file attached to a patient (optionally to one visit).

    Only the relative path is stored; the service layer validates the file and
    refuses anything outside the attachments root (zip-slip/traversal defence).
    """

    __tablename__ = "patient_attachment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="CASCADE"), nullable=False, index=True
    )
    visit_id: Mapped[int | None] = mapped_column(
        ForeignKey("visit.id", ondelete="SET NULL"), nullable=True
    )
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="other")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_relpath: Mapped[str] = mapped_column(String(400), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    is_missing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class PatientMergeLog(Base):
    """Merges are explicit, operator-driven and auditable — never automatic."""

    __tablename__ = "patient_merge_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kept_patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    merged_patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    performed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_at_utc: Mapped[datetime] = mapped_column(nullable=False)


class PatientDuplicateFlag(Base):
    """Detected duplicate candidates. The application never merges on its own."""

    __tablename__ = "patient_duplicate_flag"
    __table_args__ = (
        Index("uq_duplicate_pair", "patient_id", "candidate_patient_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signals_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
