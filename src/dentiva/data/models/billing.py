"""Invoices, payments and the derived financial cache (docs/04 §5).

Source-of-truth rule (REQ-FIN-002 / REQ-MON-001): totals and dues are computed by
:mod:`dentiva.domain.invoice_math` from items and payments. ``financial_summary``
is a **cache** that is recomputed by the integrity job, never hand-edited.
Invoices and payments are never destroyed — they are voided and audited.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dentiva.core.money import Money
from dentiva.data.base import AuditColumns, Base, VersionedColumns


class Invoice(AuditColumns, VersionedColumns, Base):
    """A bill. ``number`` is unique per business and never reused."""

    __tablename__ = "invoice"
    __table_args__ = (
        Index("uq_invoice_business_id_number", "business_id", "number", unique=True),
        Index("ix_invoice_business_id_issued_at_utc", "business_id", "issued_at_utc"),
        Index("ix_invoice_patient_id_issued_at_utc", "patient_id", "issued_at_utc"),
        Index("ix_invoice_status_due_paisa", "status", "due_paisa"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    visit_id: Mapped[int | None] = mapped_column(
        ForeignKey("visit.id", ondelete="SET NULL"), nullable=True
    )
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    issued_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    issued_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    dentist_id: Mapped[int | None] = mapped_column(
        ForeignKey("dentist.id", ondelete="SET NULL"), nullable=True
    )
    subtotal_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    discount_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    tax_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    total_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    paid_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    due_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    rounding_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    voided_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    voided_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class InvoiceItem(Base):
    """One invoice line, with the treatment name and price **snapshotted**."""

    __tablename__ = "invoice_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="CASCADE"), nullable=False, index=True
    )
    treatment_catalog_id: Mapped[int | None] = mapped_column(
        ForeignKey("treatment_catalog.id", ondelete="SET NULL"), nullable=True
    )
    treatment_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("treatment_record.id", ondelete="SET NULL"), nullable=True
    )
    name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tooth_fdi: Mapped[str | None] = mapped_column(String(3), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_scale: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    discount_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    line_total_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class PaymentMethod(Base):
    """Cash, bank, card, MFS wallets… ``requires_reference`` drives validation."""

    __tablename__ = "payment_method"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_reference: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Payment(AuditColumns, Base):
    """Money received. ``idempotency_key`` makes a double submit impossible."""

    __tablename__ = "payment"
    __table_args__ = (
        Index(
            "uq_payment_invoice_id_idempotency_key", "invoice_id", "idempotency_key", unique=True
        ),
        Index("ix_payment_business_id_paid_at_utc", "business_id", "paid_at_utc"),
        Index("ix_payment_invoice_id", "invoice_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient.id", ondelete="RESTRICT"), nullable=True
    )
    received_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    amount_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    paid_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    method_id: Mapped[int | None] = mapped_column(
        ForeignKey("payment_method.id", ondelete="RESTRICT"), nullable=True
    )
    reference_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="posted")
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    voided_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    voided_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class FinancialSummary(Base):
    """Derived cache of a patient's billed/paid/outstanding totals.

    Recomputed by :mod:`dentiva.services.system_health_service` (integrity job);
    any drift against invoices + payments is reported in System Health.
    """

    __tablename__ = "financial_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    total_billed_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    total_paid_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    outstanding_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    last_invoice_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    last_payment_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    recomputed_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
