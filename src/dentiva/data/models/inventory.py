"""Inventory, suppliers, batches and stock movements (docs/04 §6).

Stock is only ever changed through the inventory service, which writes the
movement row and the item balance in **one** transaction and audits it
(REQ-STK-004/005). ``balance_after`` makes the ledger self-verifying.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dentiva.core.money import Money
from dentiva.data.base import AuditColumns, Base, SoftDeleteColumns, VersionedColumns


class Supplier(AuditColumns, Base):
    """Vendor of inventory items."""

    __tablename__ = "supplier"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(160), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class InventoryCategory(Base):
    """Grouping for inventory items (consumables, instruments, medicines…)."""

    __tablename__ = "inventory_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class InventoryItem(AuditColumns, SoftDeleteColumns, VersionedColumns, Base):
    """A stock-kept item. Quantities are integers so they never drift."""

    __tablename__ = "inventory_item"
    __table_args__ = (
        Index("uq_inventory_item_business_id_code", "business_id", "code", unique=True),
        Index("ix_inventory_item_business_id_name", "business_id", "name"),
        Index("ix_inventory_item_current_stock", "current_stock"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_category.id", ondelete="SET NULL"), nullable=True
    )
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("supplier.id", ondelete="SET NULL"), nullable=True
    )
    unit: Mapped[str] = mapped_column(String(24), nullable=False, default="pcs")
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_cost_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    default_sale_price_paisa: Mapped[Money | None] = mapped_column(nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class InventoryBatch(Base):
    """A purchased lot with its own cost and expiry."""

    __tablename__ = "inventory_batch"
    __table_args__ = (Index("ix_inventory_batch_expiry_on", "expiry_on"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_item.id", ondelete="CASCADE"), nullable=False, index=True
    )
    batch_no: Mapped[str | None] = mapped_column(String(60), nullable=True)
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("supplier.id", ondelete="SET NULL"), nullable=True
    )
    purchase_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_purchase.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remaining: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_cost_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    manufactured_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_on: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class InventoryPurchase(AuditColumns, Base):
    """A purchase from a supplier (optionally mirrored as an expense)."""

    __tablename__ = "inventory_purchase"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("supplier.id", ondelete="SET NULL"), nullable=True
    )
    purchased_on: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    invoice_reference: Mapped[str | None] = mapped_column(String(80), nullable=True)
    total_cost_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    expense_id: Mapped[int | None] = mapped_column(
        ForeignKey("expense.id", ondelete="SET NULL"), nullable=True
    )


class InventoryPurchaseLine(Base):
    """One line of a purchase; creates a batch and a stock movement."""

    __tablename__ = "inventory_purchase_line"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purchase_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_purchase.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_item.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    batch_no: Mapped[str | None] = mapped_column(String(60), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_cost_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    expiry_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    line_total_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)


class StockMovement(Base):
    """Append-only stock ledger. ``balance_after`` is written by the service."""

    __tablename__ = "stock_movement"
    __table_args__ = (
        Index("ix_stock_movement_item_id_performed_at_utc", "item_id", "performed_at_utc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("inventory_item.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_batch.id", ondelete="SET NULL"), nullable=True
    )
    change: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str] = mapped_column(String(24), nullable=False, default="adjustment")
    reference_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    patient_id: Mapped[int | None] = mapped_column(
        ForeignKey("patient.id", ondelete="SET NULL"), nullable=True
    )
    visit_id: Mapped[int | None] = mapped_column(
        ForeignKey("visit.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    performed_at_utc: Mapped[datetime] = mapped_column(nullable=False)
