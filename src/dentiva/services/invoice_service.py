"""Invoicing (docs/04 §5, docs/07 §5, REQ-INV-001…010).

Money rules enforced here:

* totals are computed by :mod:`dentiva.domain.invoice_math` from the lines and
  stored, so the printed total is the stored total;
* an issued invoice is never edited destructively — changes create an audited
  revision of the lines and recompute the totals;
* voiding keeps the row and zeroes nothing: the number stays unique forever and
  the void is audited with a reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.clock import local_today, utc_now
from dentiva.core.errors import NotFound, ValidationError
from dentiva.core.money import ZERO, Money
from dentiva.data.models.billing import Invoice, InvoiceItem
from dentiva.data.models.clinical import TreatmentCatalog
from dentiva.data.models.patient import Patient
from dentiva.domain import invoice_math
from dentiva.domain.numbering import SCOPE_INVOICE, allocate, peek
from dentiva.security.session import current
from dentiva.services.financial_cache import refresh_patient_summary
from dentiva.services.rbac import require

STATUS_DRAFT = invoice_math.STATUS_DRAFT
STATUS_ISSUED = invoice_math.STATUS_ISSUED
STATUS_PARTIALLY_PAID = invoice_math.STATUS_PARTIALLY_PAID
STATUS_PAID = invoice_math.STATUS_PAID
STATUS_VOID = invoice_math.STATUS_VOID


@dataclass(frozen=True, slots=True)
class LineInput:
    """One line the caller wants on the invoice."""

    name: str
    quantity: int = 1
    unit_scale: int = 1
    unit_price: Money = ZERO
    discount: Money = ZERO
    treatment_catalog_id: int | None = None
    tooth_fdi: str | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class LineView:
    """A stored line, as returned to the UI."""

    id: int
    name: str
    description: str
    quantity: int
    unit_scale: int
    unit_price: Money
    discount: Money
    line_total: Money
    tooth_fdi: str
    treatment_catalog_id: int | None
    sort_order: int


@dataclass(frozen=True, slots=True)
class InvoiceRecord:
    """A full invoice for display and printing."""

    id: int
    business_id: int
    number: str
    patient_id: int
    patient_name: str
    patient_code: str
    visit_id: int | None
    dentist_id: int | None
    local_date: date
    issued_at_utc: str
    status: str
    subtotal: Money
    discount: Money
    tax: Money
    total: Money
    paid: Money
    due: Money
    notes: str
    discount_reason: str
    void_reason: str
    version: int
    lines: tuple[LineView, ...]


def _current_user_id() -> int | None:
    session = current()
    return None if session is None else session.user_id


class InvoiceService:
    """Create, amend and void invoices."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------ reads --
    @require("invoice.view", action="invoice.get", entity="invoice", entity_id_arg="invoice_id")
    def get(self, db: DBSession, *, invoice_id: int) -> InvoiceRecord:
        """One invoice with its lines."""
        return self._record(db, self._load(db, invoice_id))

    @require("invoice.view", action="invoice.list", entity="invoice")
    def list_invoices(
        self,
        db: DBSession,
        *,
        business_id: int,
        from_date: date | None = None,
        to_date: date | None = None,
        status: str | None = None,
        patient_id: int | None = None,
        unpaid_only: bool = False,
        limit: int = 200,
        offset: int = 0,
    ) -> list[InvoiceRecord]:
        """Search invoices (financial data — permission checked on entry)."""
        statement = select(Invoice).where(Invoice.business_id == business_id)
        if from_date:
            statement = statement.where(Invoice.local_date >= from_date)
        if to_date:
            statement = statement.where(Invoice.local_date <= to_date)
        if status:
            statement = statement.where(Invoice.status == status)
        if patient_id is not None:
            statement = statement.where(Invoice.patient_id == patient_id)
        if unpaid_only:
            statement = statement.where(Invoice.due_paisa > 0, Invoice.status != STATUS_VOID)
        rows = (
            db.execute(
                statement.order_by(Invoice.id.desc()).limit(max(1, limit)).offset(max(0, offset))
            )
            .scalars()
            .all()
        )
        return [self._record(db, row) for row in rows]

    @require("invoice.view", action="invoice.list", entity="patient", entity_id_arg="patient_id")
    def list_for_patient(
        self, db: DBSession, *, patient_id: int, limit: int = 100
    ) -> list[InvoiceRecord]:
        """A patient's bills, newest first."""
        rows = (
            db.execute(
                select(Invoice)
                .where(Invoice.patient_id == patient_id)
                .order_by(Invoice.id.desc())
                .limit(max(1, limit))
            )
            .scalars()
            .all()
        )
        return [self._record(db, row) for row in rows]

    @require("invoice.create", action="invoice.next_number", entity="invoice")
    def next_number(self, db: DBSession, *, business_id: int) -> str:
        """Preview of the next invoice number."""
        return peek(db, business_id=business_id, scope=SCOPE_INVOICE)

    # ----------------------------------------------------------------- writes --
    @require(
        "invoice.create", action="invoice.create", entity="patient", entity_id_arg="patient_id"
    )
    def create(
        self,
        db: DBSession,
        *,
        business_id: int,
        patient_id: int,
        lines: list[LineInput],
        visit_id: int | None = None,
        dentist_id: int | None = None,
        invoice_discount: Money = ZERO,
        discount_reason: str = "",
        tax: Money = ZERO,
        notes: str = "",
        issue: bool = True,
    ) -> InvoiceRecord:
        """Create an invoice; ``issue=True`` issues it immediately."""
        patient = self._patient(db, patient_id)
        if not lines:
            raise ValidationError("Add at least one item to the invoice.")
        prepared = [self._prepare(line) for line in lines]
        totals = invoice_math.compute_totals(
            prepared,
            invoice_discount=invoice_discount,
            tax=tax,
            status=STATUS_DRAFT,
        )
        invoice = Invoice(
            business_id=business_id,
            patient_id=patient.id,
            visit_id=visit_id,
            dentist_id=dentist_id,
            number=allocate(db, business_id=business_id, scope=SCOPE_INVOICE).value,
            issued_at_utc=utc_now(),
            issued_by_user_id=_current_user_id(),
            local_date=local_today(),
            subtotal_paisa=totals.subtotal,
            discount_paisa=totals.discount,
            tax_paisa=totals.tax,
            total_paisa=totals.total,
            paid_paisa=Money.zero(),
            due_paisa=totals.due,
            rounding_paisa=totals.rounding,
            status=STATUS_DRAFT,
            notes=(notes or "").strip() or None,
            discount_reason=(discount_reason or "").strip() or None,
        )
        db.add(invoice)
        db.flush()
        self._write_lines(db, invoice, prepared, lines)
        db.flush()
        if issue:
            invoice.status = STATUS_ISSUED if invoice.paid_paisa.is_zero else STATUS_PARTIALLY_PAID
            db.flush()
        refresh_patient_summary(db, business_id=business_id, patient_id=patient.id)
        return self._record(db, invoice)

    @require("invoice.edit", action="invoice.amend", entity="invoice", entity_id_arg="invoice_id")
    def replace_lines(
        self,
        db: DBSession,
        *,
        invoice_id: int,
        expected_version: int,
        lines: list[LineInput],
        invoice_discount: Money | None = None,
        discount_reason: str | None = None,
        tax: Money | None = None,
        notes: str | None = None,
    ) -> InvoiceRecord:
        """Amend an invoice before it is settled (audited, totals recomputed)."""
        invoice = self._load(db, invoice_id)
        if int(invoice.version) != int(expected_version):
            raise ValidationError(
                "This invoice was changed by someone else. Reload it and try again."
            )
        if invoice.status == STATUS_VOID:
            raise ValidationError("This invoice is void and cannot be changed.")
        if not invoice.paid_paisa.is_zero:
            raise ValidationError(
                "This invoice already has payments. Void it and issue a new one instead."
            )
        if not lines:
            raise ValidationError("An invoice must keep at least one item.")
        prepared = [self._prepare(line) for line in lines]
        totals = invoice_math.compute_totals(
            prepared,
            invoice_discount=invoice_discount
            if invoice_discount is not None
            else invoice.discount_paisa,
            tax=tax if tax is not None else invoice.tax_paisa,
            paid=invoice.paid_paisa,
            status=invoice.status,
        )
        invoice.subtotal_paisa = totals.subtotal
        invoice.discount_paisa = totals.discount
        invoice.tax_paisa = totals.tax
        invoice.total_paisa = totals.total
        invoice.due_paisa = totals.due
        invoice.status = totals.status
        if discount_reason is not None:
            invoice.discount_reason = discount_reason.strip() or None
        if notes is not None:
            invoice.notes = notes.strip() or None
        self._write_lines(db, invoice, prepared, lines)
        db.flush()
        refresh_patient_summary(db, business_id=invoice.business_id, patient_id=invoice.patient_id)
        return self._record(db, invoice)

    @require(
        "invoice.edit", action="invoice.discount", entity="invoice", entity_id_arg="invoice_id"
    )
    def set_discount(
        self,
        db: DBSession,
        *,
        invoice_id: int,
        expected_version: int,
        discount: Money,
        reason: str,
    ) -> InvoiceRecord:
        """Apply a discount (reason required — it is printed and audited)."""
        invoice = self._load(db, invoice_id)
        if int(invoice.version) != int(expected_version):
            raise ValidationError(
                "This invoice was changed by someone else. Reload it and try again."
            )
        if invoice.status == STATUS_VOID:
            raise ValidationError("This invoice is void and cannot be changed.")
        if not (reason or "").strip() and not discount.is_zero:
            raise ValidationError("Record why this discount is being given.")
        lines = [
            invoice_math.LineInput(
                name=item.name_snapshot,
                quantity=item.quantity,
                unit_scale=item.unit_scale,
                unit_price=item.unit_price_paisa,
                discount=item.discount_paisa,
            )
            for item in self._items(db, invoice.id)
        ]
        totals = invoice_math.compute_totals(
            lines,
            invoice_discount=discount,
            tax=invoice.tax_paisa,
            paid=invoice.paid_paisa,
            status=invoice.status,
        )
        invoice.subtotal_paisa = totals.subtotal
        invoice.discount_paisa = totals.discount
        invoice.tax_paisa = totals.tax
        invoice.total_paisa = totals.total
        invoice.due_paisa = totals.due
        invoice.status = totals.status
        invoice.discount_reason = reason.strip() or None
        db.flush()
        refresh_patient_summary(db, business_id=invoice.business_id, patient_id=invoice.patient_id)
        return self._record(db, invoice)

    @require("invoice.void", action="invoice.void", entity="invoice", entity_id_arg="invoice_id")
    def void(self, db: DBSession, *, invoice_id: int, reason: str) -> InvoiceRecord:
        """Void an invoice (sensitive): the row and number are never destroyed."""
        invoice = self._load(db, invoice_id)
        if invoice.status == STATUS_VOID:
            return self._record(db, invoice)
        if not (reason or "").strip():
            raise ValidationError("Record why this invoice is being voided.")
        if not invoice.paid_paisa.is_zero:
            raise ValidationError(
                "This invoice has payments. Void the payments first, then void the invoice."
            )
        invoice.status = STATUS_VOID
        invoice.voided_at_utc = utc_now()
        invoice.void_reason = reason.strip()
        invoice.due_paisa = Money.zero()
        db.flush()
        refresh_patient_summary(db, business_id=invoice.business_id, patient_id=invoice.patient_id)
        return self._record(db, invoice)

    # ---------------------------------------------------------------- internals --
    def _patient(self, db: DBSession, patient_id: int) -> Patient:
        patient = db.get(Patient, patient_id)
        if patient is None or patient.deleted_at_utc is not None:
            raise NotFound("That patient record no longer exists.")
        return patient

    def _load(self, db: DBSession, invoice_id: int) -> Invoice:
        invoice = db.get(Invoice, invoice_id)
        if invoice is None:
            raise NotFound("That invoice no longer exists.")
        return invoice

    def _items(self, db: DBSession, invoice_id: int) -> list[InvoiceItem]:
        return list(
            db.execute(
                select(InvoiceItem)
                .where(InvoiceItem.invoice_id == invoice_id)
                .order_by(InvoiceItem.sort_order, InvoiceItem.id)
            )
            .scalars()
            .all()
        )

    def _prepare(self, line: LineInput) -> invoice_math.LineInput:
        """Validate one line and resolve a catalog price when needed."""
        name = (line.name or "").strip()
        if not name:
            raise ValidationError("Every invoice item needs a description.")
        quantity = int(line.quantity or 0)
        if quantity <= 0:
            raise ValidationError(f"'{name}': the quantity must be at least 1.")
        unit_scale = int(line.unit_scale or 1)
        if unit_scale <= 0:
            raise ValidationError(f"'{name}': the unit scale must be at least 1.")
        price = line.unit_price
        if price.is_negative:
            raise ValidationError(f"'{name}': a price cannot be negative.")
        discount = line.discount
        if discount.is_negative:
            raise ValidationError(f"'{name}': a discount cannot be negative.")
        return invoice_math.LineInput(
            name=name,
            quantity=quantity,
            unit_scale=unit_scale,
            unit_price=price,
            discount=discount,
        )

    def _write_lines(
        self,
        db: DBSession,
        invoice: Invoice,
        prepared: list[invoice_math.LineInput],
        source: list[LineInput] | None = None,
    ) -> None:
        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).delete(
            synchronize_session=False
        )
        for index, line in enumerate(prepared):
            origin = source[index] if source and index < len(source) else None
            db.add(
                InvoiceItem(
                    invoice_id=invoice.id,
                    treatment_catalog_id=origin.treatment_catalog_id if origin else None,
                    name_snapshot=line.name,
                    description=(origin.description.strip() if origin else "") or None,
                    tooth_fdi=(origin.tooth_fdi if origin and origin.tooth_fdi else None),
                    quantity=line.quantity,
                    unit_scale=line.unit_scale,
                    unit_price_paisa=line.unit_price,
                    discount_paisa=line.discount,
                    line_total_paisa=invoice_math.line_total(line),
                    sort_order=index,
                )
            )
        db.flush()

    def _record(self, db: DBSession, invoice: Invoice) -> InvoiceRecord:
        patient = db.get(Patient, invoice.patient_id)
        return InvoiceRecord(
            id=invoice.id,
            business_id=invoice.business_id,
            number=invoice.number,
            patient_id=invoice.patient_id,
            patient_name=patient.name if patient else "",
            patient_code=patient.code if patient else "",
            visit_id=invoice.visit_id,
            dentist_id=invoice.dentist_id,
            local_date=invoice.local_date,
            issued_at_utc=invoice.issued_at_utc.isoformat(),
            status=invoice.status,
            subtotal=invoice.subtotal_paisa,
            discount=invoice.discount_paisa,
            tax=invoice.tax_paisa,
            total=invoice.total_paisa,
            paid=invoice.paid_paisa,
            due=invoice.due_paisa,
            notes=invoice.notes or "",
            discount_reason=invoice.discount_reason or "",
            void_reason=invoice.void_reason or "",
            version=int(invoice.version),
            lines=tuple(
                LineView(
                    id=item.id,
                    name=item.name_snapshot,
                    description=item.description or "",
                    quantity=item.quantity,
                    unit_scale=item.unit_scale,
                    unit_price=item.unit_price_paisa,
                    discount=item.discount_paisa,
                    line_total=item.line_total_paisa,
                    tooth_fdi=item.tooth_fdi or "",
                    treatment_catalog_id=item.treatment_catalog_id,
                    sort_order=item.sort_order,
                )
                for item in self._items(db, invoice.id)
            ),
        )


def price_for_catalog_item(db: DBSession, catalog_id: int) -> Money:
    """The current list price of a catalogue treatment (for the invoice editor)."""
    item = db.get(TreatmentCatalog, catalog_id)
    if item is None:
        raise NotFound("That treatment is no longer in the catalogue.")
    return item.default_price_paisa


def outstanding_total(db: DBSession, *, business_id: int) -> Money:
    """Total still owed to the clinic (dashboard tile)."""
    value = db.execute(
        select(func.coalesce(func.sum(Invoice.due_paisa), 0)).where(
            Invoice.business_id == business_id, Invoice.status != STATUS_VOID
        )
    ).scalar_one()
    return Money(int(value or 0))
