"""Payments (docs/04 §5, REQ-PAY-001…007).

A payment is immutable once posted: correcting a mistake **voids** the payment
and, if needed, records a new one. Every insert carries an idempotency key so a
double-click or a retry cannot take the money twice.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.clock import local_today, utc_now
from dentiva.core.errors import ConflictError, NotFound, ValidationError
from dentiva.core.money import Money
from dentiva.data.models.billing import Invoice, Payment, PaymentMethod
from dentiva.data.models.patient import Patient
from dentiva.domain import invoice_math
from dentiva.security.session import current
from dentiva.services.financial_cache import refresh_patient_summary
from dentiva.services.rbac import require

STATUS_POSTED = "posted"
STATUS_VOID = "void"


@dataclass(frozen=True, slots=True)
class PaymentRecord:
    """A money receipt (this is what prints on a money receipt)."""

    id: int
    business_id: int
    invoice_id: int
    invoice_number: str
    patient_id: int | None
    patient_name: str
    amount: Money
    paid_at_utc: str
    local_date: date
    method_code: str
    method_label: str
    reference_number: str
    notes: str
    status: str
    received_by_user_id: int | None
    idempotency_key: str
    void_reason: str


def _current_user_id() -> int | None:
    session = current()
    return None if session is None else session.user_id


class PaymentService:
    """Record, inspect and void payments."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------ reads --
    @require("payment.view", action="payment.list", entity="invoice", entity_id_arg="invoice_id")
    def list_for_invoice(self, db: DBSession, *, invoice_id: int) -> list[PaymentRecord]:
        """Every payment on one invoice, oldest first."""
        rows = (
            db.execute(select(Payment).where(Payment.invoice_id == invoice_id).order_by(Payment.id))
            .scalars()
            .all()
        )
        return [self._record(db, row) for row in rows]

    @require("payment.view", action="payment.list", entity="payment")
    def list_for_day(
        self,
        db: DBSession,
        *,
        business_id: int,
        on: date | None = None,
        method_code: str | None = None,
        limit: int = 200,
    ) -> list[PaymentRecord]:
        """The day's collections (cash-up screen)."""
        statement = select(Payment).where(
            Payment.business_id == business_id, Payment.local_date == (on or local_today())
        )
        if method_code:
            method = self._method_by_code(db, method_code)
            statement = statement.where(Payment.method_id == method.id)
        rows = (
            db.execute(statement.order_by(Payment.id.desc()).limit(max(1, limit))).scalars().all()
        )
        return [self._record(db, row) for row in rows]

    @require("finance.reports", action="payment.totals", entity="payment")
    def totals_by_method(
        self,
        db: DBSession,
        *,
        business_id: int,
        on: date | None = None,
    ) -> list[tuple[str, Money, int]]:
        """Collection totals per payment method for one day (cash-up)."""
        rows = db.execute(
            select(
                PaymentMethod.label,
                PaymentMethod.code,
                func.sum(Payment.amount_paisa),
                func.count(Payment.id),
            )
            .join(Payment, Payment.method_id == PaymentMethod.id)
            .where(
                Payment.business_id == business_id,
                Payment.local_date == (on or local_today()),
                Payment.status == STATUS_POSTED,
            )
            .group_by(PaymentMethod.id, PaymentMethod.label, PaymentMethod.code)
            .order_by(PaymentMethod.sort_order)
        ).all()
        return [(str(row[0]), Money(int(row[2] or 0)), int(row[3] or 0)) for row in rows]

    # ----------------------------------------------------------------- writes --
    @require(
        "payment.create", action="payment.record", entity="invoice", entity_id_arg="invoice_id"
    )
    def record(
        self,
        db: DBSession,
        *,
        business_id: int,
        invoice_id: int,
        amount: Money,
        method_code: str,
        reference_number: str = "",
        notes: str = "",
        paid_at: datetime | None = None,
        idempotency_key: str = "",
    ) -> PaymentRecord:
        """Take a payment against an invoice (overpayment is refused)."""
        invoice = self._invoice(db, invoice_id)
        if invoice.status == invoice_math.STATUS_VOID:
            raise ValidationError("This invoice is void, so it cannot be paid.")
        method = self._method_by_code(db, method_code)
        reference = (reference_number or "").strip()
        if method.requires_reference and not reference:
            raise ValidationError(
                f"{method.label} payments need a reference or transaction number."
            )
        key = (idempotency_key or "").strip() or uuid.uuid4().hex
        duplicate = db.execute(
            select(Payment).where(Payment.invoice_id == invoice_id, Payment.idempotency_key == key)
        ).scalar_one_or_none()
        if duplicate is not None:
            # Safe replay: return the original receipt instead of charging twice.
            return self._record(db, duplicate)

        paid, due, status = invoice_math.apply_payment(
            invoice.total_paisa, invoice.paid_paisa, amount
        )
        now = paid_at or utc_now()
        payment = Payment(
            business_id=business_id,
            invoice_id=invoice.id,
            patient_id=invoice.patient_id,
            amount_paisa=amount,
            paid_at_utc=now,
            local_date=local_today(),
            method_id=method.id,
            reference_number=reference or None,
            notes=(notes or "").strip() or None,
            status=STATUS_POSTED,
            idempotency_key=key,
            received_by_user_id=_current_user_id(),
        )
        db.add(payment)
        db.flush()
        invoice.paid_paisa = paid
        invoice.due_paisa = due
        invoice.status = status
        db.flush()
        refresh_patient_summary(db, business_id=business_id, patient_id=invoice.patient_id)
        return self._record(db, payment)

    @require("payment.void", action="payment.void", entity="payment", entity_id_arg="payment_id")
    def void(self, db: DBSession, *, payment_id: int, reason: str) -> PaymentRecord:
        """Void a posted payment (sensitive): the row stays, the money moves back."""
        payment = db.get(Payment, payment_id)
        if payment is None:
            raise NotFound("That payment no longer exists.")
        if payment.status == STATUS_VOID:
            return self._record(db, payment)
        if not (reason or "").strip():
            raise ValidationError("Record why this payment is being voided.")
        invoice = self._invoice(db, payment.invoice_id)
        if invoice.status == invoice_math.STATUS_VOID:
            raise ValidationError(
                "The invoice for this payment is void. Voiding the payment would hide the trail."
            )
        paid, due, status = invoice_math.reverse_payment(
            invoice.total_paisa, invoice.paid_paisa, payment.amount_paisa
        )
        payment.status = STATUS_VOID
        payment.voided_at_utc = utc_now()
        payment.void_reason = reason.strip()
        invoice.paid_paisa = paid
        invoice.due_paisa = due
        invoice.status = status
        db.flush()
        refresh_patient_summary(db, business_id=invoice.business_id, patient_id=invoice.patient_id)
        return self._record(db, payment)

    # ---------------------------------------------------------------- internals --
    def _invoice(self, db: DBSession, invoice_id: int) -> Invoice:
        invoice = db.get(Invoice, invoice_id)
        if invoice is None:
            raise NotFound("That invoice no longer exists.")
        return invoice

    def _method_by_code(self, db: DBSession, code: str) -> PaymentMethod:
        method = db.execute(
            select(PaymentMethod).where(PaymentMethod.code == (code or "").strip().lower())
        ).scalar_one_or_none()
        if method is None:
            raise ValidationError("Choose how the money was received.")
        if not method.is_active:
            raise ConflictError(f"{method.label} payments are not accepted at the moment.")
        return method

    def _record(self, db: DBSession, payment: Payment) -> PaymentRecord:
        invoice = db.get(Invoice, payment.invoice_id)
        patient = db.get(Patient, payment.patient_id) if payment.patient_id else None
        method = db.get(PaymentMethod, payment.method_id) if payment.method_id else None
        return PaymentRecord(
            id=payment.id,
            business_id=payment.business_id,
            invoice_id=payment.invoice_id,
            invoice_number=invoice.number if invoice else "",
            patient_id=payment.patient_id,
            patient_name=patient.name if patient else "",
            amount=payment.amount_paisa,
            paid_at_utc=payment.paid_at_utc.isoformat(),
            local_date=payment.local_date,
            method_code=method.code if method else "",
            method_label=method.label if method else "",
            reference_number=payment.reference_number or "",
            notes=payment.notes or "",
            status=payment.status,
            received_by_user_id=payment.received_by_user_id,
            idempotency_key=payment.idempotency_key,
            void_reason=payment.void_reason or "",
        )


def receipt_display(payment: PaymentRecord) -> str:
    """The money-receipt number printed for a patient (stable, never reused)."""
    return f"MR-{payment.local_date:%Y%m%d}-{payment.id:04d}"
