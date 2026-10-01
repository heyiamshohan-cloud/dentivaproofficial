"""Patient balance cache (ADR: derived data is always recomputable).

``financial_summary`` exists so the patient list can show a balance without
summing every invoice on every keystroke. It is a **cache**: the invoices and
payments are the truth, :mod:`dentiva.services.system_health_service` compares
the two, and any drift is reported rather than silently accepted.

The refresh below runs inside the caller's transaction, so a cached balance can
never commit without the invoice or payment that changed it.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dentiva.core.clock import utc_now
from dentiva.core.money import Money
from dentiva.data.models.billing import FinancialSummary, Invoice, Payment


def refresh_patient_summary(session: Session, *, business_id: int, patient_id: int) -> None:
    """Recompute one patient's cached totals from invoices and payments."""
    billed = int(
        session.execute(
            select(func.coalesce(func.sum(Invoice.total_paisa), 0)).where(
                Invoice.patient_id == patient_id, Invoice.status != "void"
            )
        ).scalar_one()
        or 0
    )
    paid = int(
        session.execute(
            select(func.coalesce(func.sum(Payment.amount_paisa), 0)).where(
                Payment.patient_id == patient_id, Payment.status == "posted"
            )
        ).scalar_one()
        or 0
    )
    last_invoice = session.execute(
        select(func.max(Invoice.issued_at_utc)).where(Invoice.patient_id == patient_id)
    ).scalar_one()
    last_payment = session.execute(
        select(func.max(Payment.paid_at_utc)).where(Payment.patient_id == patient_id)
    ).scalar_one()
    summary = session.execute(
        select(FinancialSummary).where(FinancialSummary.patient_id == patient_id)
    ).scalar_one_or_none()
    if summary is None:
        summary = FinancialSummary(business_id=business_id, patient_id=patient_id)
        session.add(summary)
    summary.total_billed_paisa = Money(billed)
    summary.total_paid_paisa = Money(paid)
    summary.outstanding_paisa = Money(max(0, billed - paid))
    summary.last_invoice_at_utc = last_invoice
    summary.last_payment_at_utc = last_payment
    summary.recomputed_at_utc = utc_now()
    session.flush()


def patient_balance(session: Session, *, patient_id: int) -> tuple[Money, Money, Money]:
    """``(billed, paid, outstanding)`` straight from the source rows."""
    billed = int(
        session.execute(
            select(func.coalesce(func.sum(Invoice.total_paisa), 0)).where(
                Invoice.patient_id == patient_id, Invoice.status != "void"
            )
        ).scalar_one()
        or 0
    )
    paid = int(
        session.execute(
            select(func.coalesce(func.sum(Payment.amount_paisa), 0)).where(
                Payment.patient_id == patient_id, Payment.status == "posted"
            )
        ).scalar_one()
        or 0
    )
    return Money(billed), Money(paid), Money(max(0, billed - paid))
