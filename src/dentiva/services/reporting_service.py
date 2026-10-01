"""Reports (docs/07 §8, REQ-REP-001…006).

Every figure is computed from the source rows with integer-paisa arithmetic at
the moment the report is asked for — there is no shadow table of totals that can
drift away from the invoices. Financial reports require ``finance.reports``;
clinical reports require the corresponding clinical permission.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.money import Money
from dentiva.data.models.accounting import Expense, Income
from dentiva.data.models.billing import Invoice, Payment, PaymentMethod
from dentiva.data.models.clinical import TreatmentRecord, Visit
from dentiva.data.models.patient import Patient
from dentiva.domain.period import month_to_date
from dentiva.services.rbac import internal, require


@dataclass(frozen=True, slots=True)
class DailyTotal:
    """One day of collections."""

    day: date
    invoiced: Money
    collected: Money
    invoices: int
    payments: int


@dataclass(frozen=True, slots=True)
class MethodTotal:
    """Collections split by payment method."""

    label: str
    code: str
    amount: Money
    count: int


@dataclass(frozen=True, slots=True)
class OutstandingRow:
    """A patient with money still owed."""

    patient_id: int
    patient_code: str
    patient_name: str
    phone: str
    outstanding: Money
    oldest_invoice_on: date | None


@dataclass(frozen=True, slots=True)
class PeriodReport:
    """The clinic's money for one period."""

    from_date: date
    to_date: date
    invoiced: Money
    collected: Money
    expenses: Money
    other_income: Money
    outstanding: Money
    by_method: tuple[MethodTotal, ...]
    by_day: tuple[DailyTotal, ...]

    @property
    def net(self) -> Money:
        """Collected money minus expenses (excludes unpaid invoices)."""
        return (self.collected + self.other_income) - self.expenses


@dataclass(frozen=True, slots=True)
class TreatmentTally:
    """How often a treatment was performed."""

    name: str
    count: int
    billed: Money


class ReportingService:
    """Financial and clinical reports."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------- financial ----
    @require("finance.reports", action="report.period", entity="report")
    def period_report(
        self,
        db: DBSession,
        *,
        business_id: int,
        from_date: date,
        to_date: date,
    ) -> PeriodReport:
        """Collections, expenses and outstanding balances for a period."""
        if from_date > to_date:
            raise ValueError("The start date must be on or before the end date.")
        invoiced = self._sum(
            db,
            select(func.coalesce(func.sum(Invoice.total_paisa), 0)).where(
                Invoice.business_id == business_id,
                Invoice.local_date >= from_date,
                Invoice.local_date <= to_date,
                Invoice.status != "void",
            ),
        )
        collected = self._sum(
            db,
            select(func.coalesce(func.sum(Payment.amount_paisa), 0)).where(
                Payment.business_id == business_id,
                Payment.local_date >= from_date,
                Payment.local_date <= to_date,
                Payment.status == "posted",
            ),
        )
        expenses = self._sum(
            db,
            select(func.coalesce(func.sum(Expense.amount_paisa), 0)).where(
                Expense.business_id == business_id,
                Expense.spent_on >= from_date,
                Expense.spent_on <= to_date,
            ),
        )
        other_income = self._sum(
            db,
            select(func.coalesce(func.sum(Income.amount_paisa), 0)).where(
                Income.business_id == business_id,
                Income.received_on >= from_date,
                Income.received_on <= to_date,
            ),
        )
        outstanding = self._sum(
            db,
            select(func.coalesce(func.sum(Invoice.due_paisa), 0)).where(
                Invoice.business_id == business_id, Invoice.status != "void"
            ),
        )
        return PeriodReport(
            from_date=from_date,
            to_date=to_date,
            invoiced=invoiced,
            collected=collected,
            expenses=expenses,
            other_income=other_income,
            outstanding=outstanding,
            by_method=tuple(
                self._by_method(db, business_id=business_id, from_date=from_date, to_date=to_date)
            ),
            by_day=tuple(
                self._by_day(db, business_id=business_id, from_date=from_date, to_date=to_date)
            ),
        )

    @require("finance.reports", action="report.by_method", entity="report")
    def by_method(
        self,
        db: DBSession,
        *,
        business_id: int,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MethodTotal]:
        """Collections per payment method (cash-up and daily summary)."""
        return self._by_method(db, business_id=business_id, from_date=from_date, to_date=to_date)

    @internal
    def _by_method(
        self,
        db: DBSession,
        *,
        business_id: int,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[MethodTotal]:
        statement = (
            select(
                PaymentMethod.label,
                PaymentMethod.code,
                func.coalesce(func.sum(Payment.amount_paisa), 0),
                func.count(Payment.id),
            )
            .join(Payment, Payment.method_id == PaymentMethod.id)
            .where(
                Payment.business_id == business_id,
                Payment.status == "posted",
            )
            .group_by(PaymentMethod.id, PaymentMethod.label, PaymentMethod.code)
            .order_by(PaymentMethod.sort_order)
        )
        if from_date:
            statement = statement.where(Payment.local_date >= from_date)
        if to_date:
            statement = statement.where(Payment.local_date <= to_date)
        rows = db.execute(statement).all()
        return [
            MethodTotal(
                label=str(row[0]),
                code=str(row[1]),
                amount=Money(int(row[2] or 0)),
                count=int(row[3]),
            )
            for row in rows
        ]

    @require("finance.reports", action="report.by_day", entity="report")
    def by_day(
        self,
        db: DBSession,
        *,
        business_id: int,
        from_date: date,
        to_date: date,
    ) -> list[DailyTotal]:
        """One row per day, so the trend can be charted without gaps."""
        return self._by_day(db, business_id=business_id, from_date=from_date, to_date=to_date)

    @internal
    def _by_day(
        self,
        db: DBSession,
        *,
        business_id: int,
        from_date: date,
        to_date: date,
    ) -> list[DailyTotal]:
        invoiced_rows = {
            row[0]: (int(row[1] or 0), int(row[2] or 0))
            for row in db.execute(
                select(Invoice.local_date, func.sum(Invoice.total_paisa), func.count(Invoice.id))
                .where(
                    Invoice.business_id == business_id,
                    Invoice.local_date >= from_date,
                    Invoice.local_date <= to_date,
                    Invoice.status != "void",
                )
                .group_by(Invoice.local_date)
            ).all()
        }
        collected_rows = {
            row[0]: (int(row[1] or 0), int(row[2] or 0))
            for row in db.execute(
                select(Payment.local_date, func.sum(Payment.amount_paisa), func.count(Payment.id))
                .where(
                    Payment.business_id == business_id,
                    Payment.local_date >= from_date,
                    Payment.local_date <= to_date,
                    Payment.status == "posted",
                )
                .group_by(Payment.local_date)
            ).all()
        }
        totals: list[DailyTotal] = []
        day = from_date
        while day <= to_date:
            invoiced, invoice_count = invoiced_rows.get(day, (0, 0))
            collected, payment_count = collected_rows.get(day, (0, 0))
            totals.append(
                DailyTotal(
                    day=day,
                    invoiced=Money(invoiced),
                    collected=Money(collected),
                    invoices=invoice_count,
                    payments=payment_count,
                )
            )
            day += timedelta(days=1)
        return totals

    @require("finance.reports", action="report.outstanding", entity="report")
    def outstanding(
        self,
        db: DBSession,
        *,
        business_id: int,
        limit: int = 200,
    ) -> list[OutstandingRow]:
        """Patients with money still owed (the collections list)."""
        rows = db.execute(
            select(
                Patient.id,
                Patient.code,
                Patient.name,
                Patient.phone_primary,
                func.sum(Invoice.due_paisa),
                func.min(Invoice.local_date),
            )
            .join(Invoice, Invoice.patient_id == Patient.id)
            .where(
                Invoice.business_id == business_id,
                Invoice.status != "void",
                Invoice.due_paisa > 0,
            )
            .group_by(Patient.id, Patient.code, Patient.name, Patient.phone_primary)
            .order_by(func.sum(Invoice.due_paisa).desc())
            .limit(max(1, limit))
        ).all()
        return [
            OutstandingRow(
                patient_id=int(row[0]),
                patient_code=str(row[1]),
                patient_name=str(row[2]),
                phone=str(row[3] or ""),
                outstanding=Money(int(row[4] or 0)),
                oldest_invoice_on=row[5],
            )
            for row in rows
        ]

    # -------------------------------------------------------------- clinical ----
    @require("visit.view", action="report.visits", entity="report")
    def visit_counts(
        self,
        db: DBSession,
        *,
        business_id: int,
        from_date: date,
        to_date: date,
    ) -> list[tuple[date, int]]:
        """Visits per day in a period."""
        rows = db.execute(
            select(Visit.local_date, func.count(Visit.id))
            .where(
                Visit.business_id == business_id,
                Visit.local_date >= from_date,
                Visit.local_date <= to_date,
            )
            .group_by(Visit.local_date)
            .order_by(Visit.local_date)
        ).all()
        return [(row[0], int(row[1])) for row in rows]

    @require("treatment.view", action="report.treatments", entity="report")
    def treatment_tally(
        self,
        db: DBSession,
        *,
        business_id: int,
        from_date: date,
        to_date: date,
        limit: int = 20,
    ) -> list[TreatmentTally]:
        """Most performed treatments (names are frozen snapshots)."""
        rows = db.execute(
            select(
                TreatmentRecord.name_snapshot,
                func.count(TreatmentRecord.id),
                func.coalesce(func.sum(TreatmentRecord.price_snapshot_paisa), 0),
            )
            .join(Visit, Visit.id == TreatmentRecord.visit_id)
            .where(
                Visit.business_id == business_id,
                Visit.local_date >= from_date,
                Visit.local_date <= to_date,
            )
            .group_by(TreatmentRecord.name_snapshot)
            .order_by(func.count(TreatmentRecord.id).desc())
            .limit(max(1, limit))
        ).all()
        return [
            TreatmentTally(name=str(row[0]), count=int(row[1]), billed=Money(int(row[2] or 0)))
            for row in rows
        ]

    @require("patient.view", action="report.patients", entity="report")
    def patient_growth(
        self,
        db: DBSession,
        *,
        business_id: int,
        months: int = 12,
    ) -> list[tuple[str, int]]:
        """New patients per month (``YYYY-MM``), oldest month first."""
        rows = db.execute(
            select(
                func.strftime("%Y-%m", Patient.registered_at_utc),
                func.count(Patient.id),
            )
            .where(Patient.business_id == business_id)
            .group_by(func.strftime("%Y-%m", Patient.registered_at_utc))
            .order_by(func.strftime("%Y-%m", Patient.registered_at_utc))
        ).all()
        return [(str(row[0]), int(row[1])) for row in rows][-max(1, months) :]

    def _sum(self, db: DBSession, statement: Select[Any]) -> Money:
        value: Any = db.execute(statement).scalar_one()
        return Money(int(value or 0))


def default_period() -> tuple[date, date]:
    """Month-to-date, the period the reports screen opens with.

    Delegated to :mod:`dentiva.domain.period` so every screen that shows money
    closes its window at the same local midnight.
    """
    period = month_to_date()
    assert period.from_date is not None and period.to_date is not None
    return period.from_date, period.to_date
