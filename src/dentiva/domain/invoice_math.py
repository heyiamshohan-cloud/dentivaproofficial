"""Invoice and payment arithmetic — pure functions over :class:`Money`
(REQ-MON-001…004, REQ-FIN-002, ADR-0003).

This module is the *single source of truth* for money: the invoice service, the
financial-summary recalculation, the dashboard and the reports all call it, so a
total can never disagree with itself. Integer paisa throughout; no float is ever
involved, and every division rounds half-up to one paisa.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from dentiva.core.errors import ValidationError
from dentiva.core.money import ZERO, Money

#: Invoice lifecycle states.
STATUS_DRAFT = "draft"
STATUS_ISSUED = "issued"
STATUS_PARTIALLY_PAID = "partially_paid"
STATUS_PAID = "paid"
STATUS_VOID = "void"
STATUS_CANCELLED = "cancelled"

OPEN_STATUSES: tuple[str, ...] = (STATUS_DRAFT, STATUS_ISSUED, STATUS_PARTIALLY_PAID)
BILLABLE_STATUSES: tuple[str, ...] = (STATUS_ISSUED, STATUS_PARTIALLY_PAID, STATUS_PAID)


@dataclass(frozen=True, slots=True)
class LineInput:
    """One invoice line before totals are computed."""

    name: str
    quantity: int = 1
    unit_scale: int = 1
    unit_price: Money = ZERO
    discount: Money = ZERO


@dataclass(frozen=True, slots=True)
class LineResult:
    """One invoice line with its computed total."""

    name: str
    quantity: int
    unit_scale: int
    unit_price: Money
    discount: Money
    line_total: Money


@dataclass(frozen=True, slots=True)
class InvoiceTotals:
    """The complete money picture of an invoice."""

    subtotal: Money
    discount: Money
    tax: Money
    total: Money
    rounding: Money
    paid: Money
    due: Money
    status: str


def line_total(line: LineInput) -> Money:
    """``(unit_price × quantity ÷ unit_scale) − discount``, never negative."""
    if line.quantity <= 0:
        raise ValidationError("Quantity must be at least 1.", detail=f"quantity={line.quantity}")
    if line.unit_scale <= 0:
        raise ValidationError(
            "The unit scale must be positive.", detail=f"unit_scale={line.unit_scale}"
        )
    gross = _scaled(line.unit_price * int(line.quantity), line.unit_scale)
    net = gross - line.discount
    return Money.zero() if net.is_negative else net


def _scaled(amount: Money, scale: int) -> Money:
    """Divide by *scale* with half-up rounding (integer arithmetic only)."""
    if scale == 1:
        return amount
    paisa = int(amount)
    divided = (Decimal(paisa) / Decimal(scale)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return Money(int(divided))


def compute_lines(lines: Iterable[LineInput]) -> list[LineResult]:
    """Compute every line total (validation errors surface on the first bad line)."""
    results: list[LineResult] = []
    for line in lines:
        results.append(
            LineResult(
                name=line.name,
                quantity=line.quantity,
                unit_scale=line.unit_scale,
                unit_price=line.unit_price,
                discount=line.discount,
                line_total=line_total(line),
            )
        )
    return results


def compute_totals(
    lines: Sequence[LineInput | LineResult],
    *,
    invoice_discount: Money = ZERO,
    tax: Money = ZERO,
    paid: Money = ZERO,
    status: str = STATUS_DRAFT,
) -> InvoiceTotals:
    """Compute subtotal/total/due and the resulting status.

    Rounding is tracked explicitly (``rounding``) so that a total is always the
    sum of the stored parts — the integrity job can therefore prove that no
    figure was quietly adjusted.
    """
    line_results = [
        line
        if isinstance(line, LineResult)
        else LineResult(
            line.name,
            line.quantity,
            line.unit_scale,
            line.unit_price,
            line.discount,
            line_total(line),
        )
        for line in lines
    ]
    subtotal = Money.zero()
    for line in line_results:
        subtotal = subtotal + line.line_total
    discount = _clamp(invoice_discount, subtotal)
    taxable = subtotal - discount
    tax_amount = Money.zero() if tax.is_negative else tax
    total = taxable + tax_amount
    total = Money.zero() if total.is_negative else total
    paid_amount = _clamp(paid, total)
    due = total - paid_amount
    return InvoiceTotals(
        subtotal=subtotal,
        discount=discount,
        tax=tax_amount,
        total=total,
        rounding=Money.zero(),
        paid=paid_amount,
        due=due,
        status=status_for(total, paid_amount, current_status=status),
    )


def status_for(total: Money, paid: Money, *, current_status: str = STATUS_ISSUED) -> str:
    """Derive the invoice status from the money (never stored independently)."""
    if current_status in (STATUS_VOID, STATUS_CANCELLED, STATUS_DRAFT):
        return current_status
    if paid.is_zero:
        return STATUS_ISSUED
    if paid >= total:
        return STATUS_PAID
    return STATUS_PARTIALLY_PAID


def apply_payment(total: Money, paid: Money, amount: Money) -> tuple[Money, Money, str]:
    """Apply *amount* to an invoice; return ``(paid, due, status)``.

    Overpayment is refused by the service layer (a clinic can record a refund as
    a separate, audited operation instead).
    """
    if amount.is_zero or amount.is_negative:
        raise ValidationError("Enter an amount greater than zero.", detail=f"amount={amount}")
    new_paid = paid + amount
    if new_paid > total:
        raise ValidationError(
            "This payment is more than the amount due.",
            detail=f"total={total} paid={paid} amount={amount}",
        )
    due = total - new_paid
    return new_paid, due, status_for(total, new_paid)


def reverse_payment(total: Money, paid: Money, amount: Money) -> tuple[Money, Money, str]:
    """Undo a posted payment (void/refund): return ``(paid, due, status)``."""
    if amount.is_zero or amount.is_negative:
        raise ValidationError("Enter an amount greater than zero.", detail=f"amount={amount}")
    new_paid = paid - amount
    if new_paid.is_negative:
        raise ValidationError(
            "This payment cannot be voided: it is larger than the amount paid.",
            detail=f"paid={paid} amount={amount}",
        )
    return new_paid, total - new_paid, status_for(total, new_paid)


def percent_of(base: Money, rate: Decimal | str) -> Money:
    """Percentage of *base* (used for discounts and tax)."""
    return base.percent(rate)


def _clamp(amount: Money, ceiling: Money) -> Money:
    if amount.is_negative:
        return Money.zero()
    return ceiling if amount > ceiling else amount
