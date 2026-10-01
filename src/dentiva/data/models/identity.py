"""Identity, tenancy and clinic people (docs/04 §1).

Even though v1 exposes one active business, every business table is scoped by
``business_id`` so several clinics can coexist and "delete a business" is a
well-defined destructive operation.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dentiva.data.base import AuditColumns, Base, SoftDeleteColumns


class Business(AuditColumns, Base):
    """The clinic/company that owns the data."""

    __tablename__ = "business"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    logo_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset.id", ondelete="SET NULL"), nullable=True
    )
    address_line1: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(80), nullable=True)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="Bangladesh")
    phone_primary: Mapped[str | None] = mapped_column(String(40), nullable=True)
    phone_secondary: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    website: Mapped[str | None] = mapped_column(String(200), nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    registration_no: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Dhaka")
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False, default="BDT")
    currency_symbol: Mapped[str] = mapped_column(String(8), nullable=False, default="৳")
    date_format: Mapped[str] = mapped_column(String(24), nullable=False, default="dd MMM yyyy")
    time_format: Mapped[str] = mapped_column(String(24), nullable=False, default="hh:mm AP")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    activated_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)


class Designation(Base):
    """Professional title (BDS, MCPS, FCPS, …); global or clinic specific."""

    __tablename__ = "designation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int | None] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    abbr: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Qualification(Base):
    """Degree/diploma catalogue; global or clinic specific."""

    __tablename__ = "qualification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int | None] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    abbr: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Staff(AuditColumns, SoftDeleteColumns, Base):
    """Non-clinical clinic employee (reception, assistant, accountant, …)."""

    __tablename__ = "staff"
    __table_args__ = (Index("ix_staff_business_id_code", "business_id", "code", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    age_cached: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(24), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(8), nullable=True)
    nid_or_id_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    photo_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset.id", ondelete="SET NULL"), nullable=True
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    department: Mapped[str | None] = mapped_column(String(80), nullable=True)
    role_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    salary_paisa: Mapped[int | None] = mapped_column(Integer, nullable=True)
    joined_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    left_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Dentist(AuditColumns, SoftDeleteColumns, Base):
    """A clinician. May optionally be linked to a staff record."""

    __tablename__ = "dentist"
    __table_args__ = (
        Index(
            "uq_dentist_business_id_registration_number",
            "business_id",
            "registration_number",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    registration_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    specialty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset.id", ondelete="SET NULL"), nullable=True
    )
    signature_asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset.id", ondelete="SET NULL"), nullable=True
    )
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    joined_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DentistDesignation(Base):
    """A dentist holds many designations; one of them is primary (REQ-FRS-004)."""

    __tablename__ = "dentist_designation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dentist_id: Mapped[int] = mapped_column(
        ForeignKey("dentist.id", ondelete="CASCADE"), nullable=False, index=True
    )
    designation_id: Mapped[int] = mapped_column(
        ForeignKey("designation.id", ondelete="RESTRICT"), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DentistQualification(Base):
    """A dentist holds many qualifications, each with institution and year."""

    __tablename__ = "dentist_qualification"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dentist_id: Mapped[int] = mapped_column(
        ForeignKey("dentist.id", ondelete="CASCADE"), nullable=False, index=True
    )
    qualification_id: Mapped[int] = mapped_column(
        ForeignKey("qualification.id", ondelete="RESTRICT"), nullable=False
    )
    institution: Mapped[str | None] = mapped_column(String(160), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
