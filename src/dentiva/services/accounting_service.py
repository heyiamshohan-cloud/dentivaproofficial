"""Clinic accounts: expenses and other income (docs/04 §6, REQ-ACC-001…006).

Patient invoices and payments are the clinical billing side; this service is the
clinic's own books. Every entry is money in integer paisa, dated by the clinic's
local calendar, and never destroyed — a mistake is corrected by a new entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.clock import local_today, utc_now
from dentiva.core.errors import NotFound, ValidationError
from dentiva.core.money import Money
from dentiva.data.models.accounting import Expense, ExpenseCategory, Income
from dentiva.data.models.billing import PaymentMethod
from dentiva.security.session import current
from dentiva.services.rbac import require


@dataclass(frozen=True, slots=True)
class ExpenseRecord:
    """Money leaving the clinic."""

    id: int
    business_id: int
    title: str
    description: str
    category: str
    amount: Money
    spent_on: date
    vendor_name: str
    method_code: str
    reference_number: str
    recorded_at_utc: str


@dataclass(frozen=True, slots=True)
class IncomeRecord:
    """Money entering the clinic that is not a patient payment."""

    id: int
    business_id: int
    source: str
    category: str
    amount: Money
    received_on: date
    method_code: str
    reference_number: str
    notes: str


@dataclass(frozen=True, slots=True)
class CategorySummary:
    """A category with its period total, for the accounts screen."""

    name: str
    total: Money
    entries: int


class AccountingService:
    """Expense and income bookkeeping."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------ reads --
    @require("accounting.view", action="expense.list", entity="expense")
    def list_expenses(
        self,
        db: DBSession,
        *,
        business_id: int,
        from_date: date | None = None,
        to_date: date | None = None,
        category: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[ExpenseRecord]:
        """Expenses in a period, newest first."""
        statement = select(Expense).where(Expense.business_id == business_id)
        if from_date:
            statement = statement.where(Expense.spent_on >= from_date)
        if to_date:
            statement = statement.where(Expense.spent_on <= to_date)
        if category:
            statement = statement.join(
                ExpenseCategory, ExpenseCategory.id == Expense.category_id
            ).where(ExpenseCategory.name == category)
        rows = (
            db.execute(
                statement.order_by(Expense.spent_on.desc(), Expense.id.desc())
                .limit(max(1, limit))
                .offset(max(0, offset))
            )
            .scalars()
            .all()
        )
        return [self._expense(db, row) for row in rows]

    @require("accounting.view", action="income.list", entity="income")
    def list_income(
        self,
        db: DBSession,
        *,
        business_id: int,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 200,
    ) -> list[IncomeRecord]:
        """Other income in a period."""
        statement = select(Income).where(Income.business_id == business_id)
        if from_date:
            statement = statement.where(Income.received_on >= from_date)
        if to_date:
            statement = statement.where(Income.received_on <= to_date)
        rows = (
            db.execute(
                statement.order_by(Income.received_on.desc(), Income.id.desc()).limit(max(1, limit))
            )
            .scalars()
            .all()
        )
        return [self._income(db, row) for row in rows]

    @require("accounting.view", action="expense.categories", entity="expense")
    def categories(self, db: DBSession) -> list[str]:
        """The clinic's expense categories (seeded, then clinic-maintained)."""
        return list(
            db.execute(
                select(ExpenseCategory.name)
                .where(ExpenseCategory.is_active.is_(True))
                .order_by(ExpenseCategory.sort_order, ExpenseCategory.name)
            )
            .scalars()
            .all()
        )

    @require("finance.reports", action="accounting.summary", entity="expense")
    def expense_summary(
        self,
        db: DBSession,
        *,
        business_id: int,
        from_date: date,
        to_date: date,
    ) -> list[CategorySummary]:
        """Totals per category for a period (the accounts report)."""
        rows = db.execute(
            select(
                ExpenseCategory.name,
                func.coalesce(func.sum(Expense.amount_paisa), 0),
                func.count(Expense.id),
            )
            .join(Expense, Expense.category_id == ExpenseCategory.id)
            .where(
                Expense.business_id == business_id,
                Expense.spent_on >= from_date,
                Expense.spent_on <= to_date,
            )
            .group_by(ExpenseCategory.id, ExpenseCategory.name)
            .order_by(func.sum(Expense.amount_paisa).desc())
        ).all()
        return [
            CategorySummary(
                name=str(row[0]), total=Money(int(row[1] or 0)), entries=int(row[2] or 0)
            )
            for row in rows
        ]

    # ----------------------------------------------------------------- writes --
    @require("accounting.manage", action="expense.record", entity="expense")
    def record_expense(
        self,
        db: DBSession,
        *,
        business_id: int,
        title: str,
        amount: Money,
        category: str | None = None,
        spent_on: date | None = None,
        vendor_name: str = "",
        method_code: str = "",
        reference_number: str = "",
        description: str = "",
    ) -> ExpenseRecord:
        """Record money leaving the clinic."""
        clean_title = (title or "").strip()
        if not clean_title:
            raise ValidationError("Give the expense a title.")
        if amount.is_zero or amount.is_negative:
            raise ValidationError("Enter an amount greater than zero.")
        category_id = self._category_id(db, category)
        method_id = self._method_id(db, method_code)
        expense = Expense(
            business_id=business_id,
            category_id=category_id,
            title=clean_title,
            description=(description or "").strip() or None,
            amount_paisa=amount,
            spent_on=spent_on or local_today(),
            paid_by_user_id=_current_user_id(),
            payment_method_id=method_id,
            reference_number=(reference_number or "").strip() or None,
            vendor_name=(vendor_name or "").strip() or None,
            recorded_at_utc=utc_now(),
        )
        db.add(expense)
        db.flush()
        return self._expense(db, expense)

    @require("accounting.manage", action="income.record", entity="income")
    def record_income(
        self,
        db: DBSession,
        *,
        business_id: int,
        source: str,
        amount: Money,
        category: str = "",
        received_on: date | None = None,
        method_code: str = "",
        reference_number: str = "",
        notes: str = "",
    ) -> IncomeRecord:
        """Record income that is not a patient payment."""
        clean_source = (source or "").strip()
        if not clean_source:
            raise ValidationError("Record where the money came from.")
        if amount.is_zero or amount.is_negative:
            raise ValidationError("Enter an amount greater than zero.")
        income = Income(
            business_id=business_id,
            source=clean_source,
            category=(category or "").strip() or None,
            amount_paisa=amount,
            received_on=received_on or local_today(),
            received_by_user_id=_current_user_id(),
            payment_method_id=self._method_id(db, method_code),
            reference_number=(reference_number or "").strip() or None,
            notes=(notes or "").strip() or None,
        )
        db.add(income)
        db.flush()
        return self._income(db, income)

    # ---------------------------------------------------------------- internals --
    def _category_id(self, db: DBSession, name: str | None) -> int | None:
        clean = (name or "").strip()
        if not clean:
            return None
        category = db.execute(
            select(ExpenseCategory).where(ExpenseCategory.name == clean)
        ).scalar_one_or_none()
        if category is None:
            raise NotFound(f"There is no expense category called '{clean}'.")
        return category.id

    def _method_id(self, db: DBSession, code: str | None) -> int | None:
        clean = (code or "").strip().lower()
        if not clean:
            return None
        method = db.execute(
            select(PaymentMethod).where(PaymentMethod.code == clean)
        ).scalar_one_or_none()
        if method is None:
            raise ValidationError("Choose how the money was paid.")
        return method.id

    def _expense(self, db: DBSession, expense: Expense) -> ExpenseRecord:
        category = db.get(ExpenseCategory, expense.category_id) if expense.category_id else None
        method = (
            db.get(PaymentMethod, expense.payment_method_id) if expense.payment_method_id else None
        )
        return ExpenseRecord(
            id=expense.id,
            business_id=expense.business_id,
            title=expense.title,
            description=expense.description or "",
            category=category.name if category else "",
            amount=expense.amount_paisa,
            spent_on=expense.spent_on,
            vendor_name=expense.vendor_name or "",
            method_code=method.code if method else "",
            reference_number=expense.reference_number or "",
            recorded_at_utc=expense.recorded_at_utc.isoformat(),
        )

    def _income(self, db: DBSession, income: Income) -> IncomeRecord:
        method = (
            db.get(PaymentMethod, income.payment_method_id) if income.payment_method_id else None
        )
        return IncomeRecord(
            id=income.id,
            business_id=income.business_id,
            source=income.source,
            category=income.category or "",
            amount=income.amount_paisa,
            received_on=income.received_on,
            method_code=method.code if method else "",
            reference_number=income.reference_number or "",
            notes=income.notes or "",
        )


def _current_user_id() -> int | None:
    session = current()
    return None if session is None else session.user_id
