"""Inventory: items, batches, purchases and the stock ledger (REQ-INV-101…108).

Quantities are integers and the ledger is append-only: every movement records
the balance **after** the change, so stock can be reconstructed and audited at
any point in time. Adjustments always state a reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.clock import local_today, utc_now
from dentiva.core.errors import NotFound, ValidationError
from dentiva.core.money import ZERO, Money
from dentiva.data.models.accounting import Expense, ExpenseCategory
from dentiva.data.models.inventory import (
    InventoryBatch,
    InventoryItem,
    InventoryPurchase,
    InventoryPurchaseLine,
    StockMovement,
    Supplier,
)
from dentiva.security.session import current
from dentiva.services.rbac import require

#: Movement reasons.
REASON_PURCHASE = "purchase"
REASON_USAGE = "usage"
REASON_ADJUSTMENT = "adjustment"
REASON_DAMAGE = "damage"
REASON_RETURN = "return"
REASON_COUNT = "count"

ADJUSTMENT_REASONS = (REASON_ADJUSTMENT, REASON_DAMAGE, REASON_COUNT, REASON_RETURN)


@dataclass(frozen=True, slots=True)
class ItemRecord:
    """A stock-kept item."""

    id: int
    business_id: int
    code: str
    name: str
    unit: str
    current_stock: int
    reorder_level: int
    unit_cost: Money
    sale_price: Money | None
    location: str
    notes: str
    category: str
    supplier: str
    is_active: bool
    needs_reorder: bool
    version: int


@dataclass(frozen=True, slots=True)
class MovementRecord:
    """One entry of the stock ledger."""

    id: int
    item_id: int
    change: int
    balance_after: int
    reason: str
    note: str
    performed_by: str
    performed_at_utc: str


@dataclass(frozen=True, slots=True)
class PurchaseRecord:
    """A purchase from a supplier."""

    id: int
    business_id: int
    supplier: str
    purchased_on: date
    invoice_reference: str
    total_cost: Money
    lines: int
    mirrored_expense_id: int | None


class InventoryService:
    """Stock control for the clinic's consumables and materials."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------ reads --
    @require("inventory.view", action="inventory.list", entity="inventory")
    def list_items(
        self,
        db: DBSession,
        *,
        business_id: int,
        term: str = "",
        include_inactive: bool = False,
        low_stock_only: bool = False,
        limit: int = 300,
    ) -> list[ItemRecord]:
        """Items, optionally filtered by name/code or low stock."""
        statement = select(InventoryItem).where(
            InventoryItem.business_id == business_id, InventoryItem.deleted_at_utc.is_(None)
        )
        if not include_inactive:
            statement = statement.where(InventoryItem.is_active.is_(True))
        if term := (term or "").strip():
            pattern = f"%{term.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(InventoryItem.name).like(pattern),
                    func.lower(InventoryItem.code).like(pattern),
                )
            )
        rows = (
            db.execute(statement.order_by(InventoryItem.name).limit(max(1, limit))).scalars().all()
        )
        records = [self._item(db, row) for row in rows]
        if low_stock_only:
            records = [record for record in records if record.needs_reorder]
        return records

    @require("inventory.view", action="inventory.get", entity="inventory", entity_id_arg="item_id")
    def get_item(self, db: DBSession, *, item_id: int) -> ItemRecord:
        """One item."""
        return self._item(db, self._load(db, item_id))

    @require(
        "inventory.view", action="inventory.ledger", entity="inventory", entity_id_arg="item_id"
    )
    def ledger(self, db: DBSession, *, item_id: int, limit: int = 200) -> list[MovementRecord]:
        """The append-only stock ledger for one item (newest first)."""
        rows = (
            db.execute(
                select(StockMovement)
                .where(StockMovement.item_id == item_id)
                .order_by(StockMovement.id.desc())
                .limit(max(1, limit))
            )
            .scalars()
            .all()
        )
        return [self._movement(db, row) for row in rows]

    @require("inventory.view", action="inventory.expiring", entity="inventory")
    def expiring_batches(
        self,
        db: DBSession,
        *,
        business_id: int,
        within_days: int = 60,
        limit: int = 100,
    ) -> list[tuple[str, str, date, int]]:
        """Batches that expire soon (item name, batch no, expiry, remaining)."""
        horizon = local_today() + timedelta(days=max(1, within_days))
        rows = db.execute(
            select(
                InventoryItem.name,
                InventoryBatch.batch_no,
                InventoryBatch.expiry_on,
                InventoryBatch.remaining,
            )
            .join(InventoryBatch, InventoryBatch.item_id == InventoryItem.id)
            .where(
                InventoryItem.business_id == business_id,
                InventoryBatch.remaining > 0,
                InventoryBatch.expiry_on.is_not(None),
                InventoryBatch.expiry_on <= horizon,
            )
            .order_by(InventoryBatch.expiry_on)
            .limit(max(1, limit))
        ).all()
        return [
            (str(row[0]), str(row[1] or ""), row[2], int(row[3]))
            for row in rows
            if row[2] is not None
        ]

    # ----------------------------------------------------------------- writes --
    @require("inventory.manage", action="inventory.item.create", entity="inventory")
    def create_item(
        self,
        db: DBSession,
        *,
        business_id: int,
        name: str,
        code: str = "",
        unit: str = "pcs",
        reorder_level: int = 0,
        unit_cost: Money = ZERO,
        sale_price: Money | None = None,
        location: str = "",
        notes: str = "",
        category: str = "",
        supplier: str = "",
        opening_stock: int = 0,
    ) -> ItemRecord:
        """Add an item to the inventory (optionally with an opening balance)."""
        clean = (name or "").strip()
        if not clean:
            raise ValidationError("Give the item a name.")
        if opening_stock < 0:
            raise ValidationError("The opening stock cannot be negative.")
        item_code = (code or "").strip() or self._next_code(db, business_id)
        if self._code_taken(db, business_id, item_code):
            raise ValidationError(f"The code '{item_code}' is already used by another item.")
        item = InventoryItem(
            business_id=business_id,
            code=item_code,
            name=clean,
            category_id=self._category_id(db, category),
            supplier_id=self._supplier_id(db, supplier),
            unit=(unit or "pcs").strip() or "pcs",
            current_stock=0,
            reorder_level=max(0, int(reorder_level)),
            unit_cost_paisa=unit_cost,
            default_sale_price_paisa=sale_price,
            location=(location or "").strip() or None,
            notes=(notes or "").strip() or None,
            is_active=True,
        )
        db.add(item)
        db.flush()
        if opening_stock:
            self._move(
                db,
                item,
                change=opening_stock,
                reason=REASON_COUNT,
                note="Opening stock",
            )
        db.flush()
        return self._item(db, item)

    @require(
        "inventory.manage",
        action="inventory.item.update",
        entity="inventory",
        entity_id_arg="item_id",
    )
    def update_item(
        self,
        db: DBSession,
        *,
        item_id: int,
        expected_version: int,
        **changes: object,
    ) -> ItemRecord:
        """Edit the descriptive fields of an item (never the stock)."""
        item = self._load(db, item_id)
        if int(item.version) != int(expected_version):
            raise ValidationError("This item was changed by someone else. Reload it and try again.")
        allowed = {
            "name",
            "unit",
            "reorder_level",
            "unit_cost",
            "sale_price",
            "location",
            "notes",
            "category",
            "supplier",
            "is_active",
        }
        unknown = sorted(set(changes) - allowed)
        if unknown:
            raise ValidationError(f"These fields cannot be changed here: {', '.join(unknown)}.")
        if "name" in changes:
            clean = str(changes["name"] or "").strip()
            if not clean:
                raise ValidationError("Give the item a name.")
            item.name = clean
        if "unit" in changes:
            item.unit = str(changes["unit"] or "pcs").strip() or "pcs"
        if "reorder_level" in changes:
            item.reorder_level = max(0, _coerce_int(changes["reorder_level"]))
        if "unit_cost" in changes:
            item.unit_cost_paisa = changes["unit_cost"]  # type: ignore[assignment]
        if "sale_price" in changes:
            item.default_sale_price_paisa = changes["sale_price"]  # type: ignore[assignment]
        if "location" in changes:
            item.location = str(changes["location"] or "").strip() or None
        if "notes" in changes:
            item.notes = str(changes["notes"] or "").strip() or None
        if "category" in changes:
            item.category_id = self._category_id(db, str(changes["category"] or ""))
        if "supplier" in changes:
            item.supplier_id = self._supplier_id(db, str(changes["supplier"] or ""))
        if "is_active" in changes:
            item.is_active = bool(changes["is_active"])
        db.flush()
        return self._item(db, item)

    @require(
        "inventory.adjust", action="inventory.adjust", entity="inventory", entity_id_arg="item_id"
    )
    def adjust(
        self,
        db: DBSession,
        *,
        item_id: int,
        change: int,
        reason: str,
        note: str = "",
    ) -> ItemRecord:
        """Correct the stock by a signed amount, with a stated reason."""
        item = self._load(db, item_id)
        if change == 0:
            raise ValidationError("Enter how much the stock changed.")
        if reason not in ADJUSTMENT_REASONS:
            raise ValidationError(
                "Choose one of these reasons: " + ", ".join(ADJUSTMENT_REASONS) + "."
            )
        if not (note or "").strip():
            raise ValidationError("Record why the stock is being changed.")
        if item.current_stock + change < 0:
            raise ValidationError(
                f"Stock cannot go below zero (current stock is {item.current_stock})."
            )
        self._move(db, item, change=change, reason=reason, note=note.strip())
        db.flush()
        return self._item(db, item)

    @require("inventory.purchase", action="inventory.purchase", entity="inventory")
    def record_purchase(
        self,
        db: DBSession,
        *,
        business_id: int,
        supplier: str = "",
        purchased_on: date | None = None,
        invoice_reference: str = "",
        lines: list[tuple[int, int, Money, str | None, date | None]],
        notes: str = "",
        mirror_as_expense: bool = True,
        expense_category: str = "",
    ) -> PurchaseRecord:
        """Book a purchase: creates batches, stock movements and (optionally) an expense.

        ``lines`` is a list of ``(item_id, quantity, unit_cost, batch_no, expiry)``.
        """
        if not lines:
            raise ValidationError("Add at least one item to the purchase.")
        day = purchased_on or local_today()
        purchase = InventoryPurchase(
            business_id=business_id,
            supplier_id=self._supplier_id(db, supplier),
            purchased_on=day,
            invoice_reference=(invoice_reference or "").strip() or None,
            total_cost_paisa=Money.zero(),
            notes=(notes or "").strip() or None,
            recorded_by_user_id=_current_user_id(),
        )
        db.add(purchase)
        db.flush()
        total = Money.zero()
        for item_id, quantity, unit_cost, batch_no, expiry in lines:
            if quantity <= 0:
                raise ValidationError("Every purchase line needs a quantity of at least 1.")
            if unit_cost.is_negative:
                raise ValidationError("A unit cost cannot be negative.")
            item = self._load(db, item_id)
            line_total = Money(unit_cost.paisa * quantity)
            db.add(
                InventoryPurchaseLine(
                    purchase_id=purchase.id,
                    item_id=item.id,
                    batch_no=(batch_no or "").strip() or None,
                    quantity=quantity,
                    unit_cost_paisa=unit_cost,
                    expiry_on=expiry,
                    line_total_paisa=line_total,
                )
            )
            db.add(
                InventoryBatch(
                    item_id=item.id,
                    batch_no=(batch_no or "").strip() or None,
                    supplier_id=purchase.supplier_id,
                    purchase_id=purchase.id,
                    quantity=quantity,
                    remaining=quantity,
                    unit_cost_paisa=unit_cost,
                    expiry_on=expiry,
                    received_on=day,
                )
            )
            item.unit_cost_paisa = unit_cost
            self._move(
                db,
                item,
                change=quantity,
                reason=REASON_PURCHASE,
                note=f"Purchase #{purchase.id}",
                reference_type="purchase",
                reference_id=purchase.id,
            )
            total = total + line_total
        purchase.total_cost_paisa = total
        db.flush()

        expense_id: int | None = None
        if mirror_as_expense:
            category_id = self._expense_category_id(db, expense_category)
            expense = Expense(
                business_id=business_id,
                category_id=category_id,
                title=f"Stock purchase {invoice_reference or '#' + str(purchase.id)}".strip(),
                description=f"{len(lines)} line(s) from {(supplier or 'supplier').strip()}",
                amount_paisa=total,
                spent_on=day,
                paid_by_user_id=_current_user_id(),
                vendor_name=(supplier or "").strip() or None,
                inventory_purchase_id=purchase.id,
                recorded_at_utc=utc_now(),
            )
            db.add(expense)
            db.flush()
            expense_id = expense.id
            purchase.expense_id = expense.id
            db.flush()
        return PurchaseRecord(
            id=purchase.id,
            business_id=purchase.business_id,
            supplier=(supplier or "").strip(),
            purchased_on=purchase.purchased_on,
            invoice_reference=purchase.invoice_reference or "",
            total_cost=purchase.total_cost_paisa,
            lines=len(lines),
            mirrored_expense_id=expense_id,
        )

    @require(
        "inventory.manage", action="inventory.consume", entity="inventory", entity_id_arg="item_id"
    )
    def consume(
        self,
        db: DBSession,
        *,
        item_id: int,
        quantity: int,
        patient_id: int | None = None,
        visit_id: int | None = None,
        note: str = "",
    ) -> ItemRecord:
        """Use stock during treatment (linked to the visit when known)."""
        if quantity <= 0:
            raise ValidationError("Enter how much was used.")
        item = self._load(db, item_id)
        if item.current_stock < quantity:
            raise ValidationError(
                f"Only {item.current_stock} {item.unit} in stock; {quantity} was requested."
            )
        self._move(
            db,
            item,
            change=-quantity,
            reason=REASON_USAGE,
            note=(note or "Used in treatment").strip(),
            reference_type="visit" if visit_id is not None else None,
            reference_id=visit_id,
            patient_id=patient_id,
            visit_id=visit_id,
        )
        db.flush()
        return self._item(db, item)

    # ---------------------------------------------------------------- internals --
    def _load(self, db: DBSession, item_id: int) -> InventoryItem:
        item = db.get(InventoryItem, item_id)
        if item is None or item.deleted_at_utc is not None:
            raise NotFound("That item no longer exists.")
        return item

    def _move(
        self,
        db: DBSession,
        item: InventoryItem,
        *,
        change: int,
        reason: str,
        note: str,
        reference_type: str | None = None,
        reference_id: int | None = None,
        patient_id: int | None = None,
        visit_id: int | None = None,
    ) -> StockMovement:
        item.current_stock = int(item.current_stock) + change
        movement = StockMovement(
            item_id=item.id,
            change=change,
            balance_after=item.current_stock,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            patient_id=patient_id,
            visit_id=visit_id,
            note=note,
            performed_by_user_id=_current_user_id(),
            performed_at_utc=utc_now(),
        )
        db.add(movement)
        db.flush()
        return movement

    def _next_code(self, db: DBSession, business_id: int) -> str:
        highest = db.execute(
            select(func.coalesce(func.max(InventoryItem.id), 0)).where(
                InventoryItem.business_id == business_id
            )
        ).scalar_one()
        return f"ITEM-{int(highest) + 1:04d}"

    def _code_taken(self, db: DBSession, business_id: int, code: str) -> bool:
        return (
            db.execute(
                select(InventoryItem.id).where(
                    InventoryItem.business_id == business_id, InventoryItem.code == code
                )
            ).scalar_one_or_none()
            is not None
        )

    def _category_id(self, db: DBSession, name: str) -> int | None:
        from dentiva.data.models.inventory import InventoryCategory

        if not (name or "").strip():
            return None
        category = db.execute(
            select(InventoryCategory).where(InventoryCategory.name == name.strip())
        ).scalar_one_or_none()
        if category is None:
            category = InventoryCategory(name=name.strip())
            db.add(category)
            db.flush()
        return category.id

    def _supplier_id(self, db: DBSession, name: str) -> int | None:
        """Suppliers are shared across clinics, so they are matched by name."""
        if not (name or "").strip():
            return None
        clean = name.strip()
        supplier = db.execute(
            select(Supplier).where(func.lower(Supplier.name) == func.lower(clean))
        ).scalar_one_or_none()
        if supplier is None:
            supplier = Supplier(name=clean, is_active=True)
            db.add(supplier)
            db.flush()
        return supplier.id

    def _expense_category_id(self, db: DBSession, name: str) -> int | None:
        if (name or "").strip():
            category = db.execute(
                select(ExpenseCategory).where(ExpenseCategory.name == name.strip())
            ).scalar_one_or_none()
            if category is None:
                category = ExpenseCategory(name=name.strip(), is_active=True)
                db.add(category)
                db.flush()
            return category.id
        category = (
            db.execute(
                select(ExpenseCategory)
                .where(
                    ExpenseCategory.name.ilike("%purchase%") | ExpenseCategory.name.ilike("%suppl%")
                )
                .order_by(ExpenseCategory.sort_order)
            )
            .scalars()
            .first()
        )
        if category is None:
            category = (
                db.execute(select(ExpenseCategory).order_by(ExpenseCategory.sort_order))
                .scalars()
                .first()
            )
        return category.id if category else None

    def _item(self, db: DBSession, item: InventoryItem) -> ItemRecord:
        from dentiva.data.models.inventory import InventoryCategory

        category = db.get(InventoryCategory, item.category_id) if item.category_id else None
        supplier = db.get(Supplier, item.supplier_id) if item.supplier_id else None
        return ItemRecord(
            id=item.id,
            business_id=item.business_id,
            code=item.code,
            name=item.name,
            unit=item.unit,
            current_stock=int(item.current_stock),
            reorder_level=int(item.reorder_level),
            unit_cost=item.unit_cost_paisa,
            sale_price=item.default_sale_price_paisa,
            location=item.location or "",
            notes=item.notes or "",
            category=category.name if category else "",
            supplier=supplier.name if supplier else "",
            is_active=bool(item.is_active),
            needs_reorder=int(item.current_stock) <= int(item.reorder_level),
            version=int(item.version),
        )

    def _movement(self, db: DBSession, movement: StockMovement) -> MovementRecord:
        from dentiva.data.models.security import User

        user = (
            db.get(User, movement.performed_by_user_id) if movement.performed_by_user_id else None
        )
        return MovementRecord(
            id=movement.id,
            item_id=movement.item_id,
            change=int(movement.change),
            balance_after=int(movement.balance_after),
            reason=movement.reason,
            note=movement.note or "",
            performed_by=user.display_name or user.username if user else "system",
            performed_at_utc=movement.performed_at_utc.isoformat(),
        )


def _coerce_int(value: object, *, default: int = 0) -> int:
    """Read an integer out of a free-form ``**changes`` value (never raises)."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.lstrip("-").isdigit():
            return int(cleaned)
    return default


def _current_user_id() -> int | None:
    session = current()
    return None if session is None else session.user_id


def stock_value(db: DBSession, *, business_id: int) -> Money:
    """Value of the stock on hand at the latest unit cost (dashboard tile)."""
    total = db.execute(
        select(
            func.coalesce(func.sum(InventoryItem.current_stock * InventoryItem.unit_cost_paisa), 0)
        ).where(InventoryItem.business_id == business_id, InventoryItem.deleted_at_utc.is_(None))
    ).scalar_one()
    return Money(int(total or 0))
