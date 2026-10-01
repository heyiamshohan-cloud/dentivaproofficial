"""Accounting: expenses and non-payment income (docs/04 §5)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dentiva.core.money import Money
from dentiva.data.base import AuditColumns, Base


class ExpenseCategory(Base):
    """Clinic-maintained expense categories."""

    __tablename__ = "expense_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Expense(AuditColumns, Base):
    """Money leaving the clinic (rent, salary, supplies, purchases…)."""

    __tablename__ = "expense"
    __table_args__ = (Index("ix_expense_business_id_spent_on", "business_id", "spent_on"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("expense_category.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    spent_on: Mapped[date] = mapped_column(Date, nullable=False)
    paid_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    payment_method_id: Mapped[int | None] = mapped_column(
        ForeignKey("payment_method.id", ondelete="SET NULL"), nullable=True
    )
    reference_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    vendor_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    inventory_purchase_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_purchase.id", ondelete="SET NULL"), nullable=True
    )
    attachment_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset.id", ondelete="SET NULL"), nullable=True
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(nullable=False)


class Income(AuditColumns, Base):
    """Money entering the clinic that is not a patient payment."""

    __tablename__ = "income"
    __table_args__ = (Index("ix_income_business_id_received_on", "business_id", "received_on"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amount_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    received_on: Mapped[date] = mapped_column(Date, nullable=False)
    received_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    payment_method_id: Mapped[int | None] = mapped_column(
        ForeignKey("payment_method.id", ondelete="SET NULL"), nullable=True
    )
    reference_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
