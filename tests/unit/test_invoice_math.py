"""Invoice arithmetic (REQ-MON-001…004, ADR-0003).

Every figure is computed in integer paisa from the stored parts, so the printed
total is always explainable: no rounding drift, no float, no duplicated total
that can disagree with its lines.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from dentiva.core.errors import ValidationError
from dentiva.core.money import Money
from dentiva.domain import invoice_math as im

TAKA = lambda value: Money.from_taka(value)  # noqa: E731 - readability in tests


def test_line_total_is_quantity_times_price_less_discount() -> None:
    line = im.LineInput("Scaling", quantity=2, unit_price=TAKA("500.00"), discount=TAKA("50.00"))
    assert im.line_total(line) == TAKA("950.00")


def test_fractional_scales_round_half_up_once() -> None:
    """1.5 sessions at ৳300 = ৳450 exactly — never 449.99 from a float."""
    line = im.LineInput("Therapy", quantity=3, unit_scale=2, unit_price=TAKA("300.00"))
    assert im.line_total(line) == TAKA("450.00")


def test_compute_lines_keeps_each_line_result() -> None:
    lines = [
        im.LineInput("Consultation", quantity=1, unit_price=TAKA("500.00")),
        im.LineInput("Filling", quantity=2, unit_price=TAKA("800.50"), discount=TAKA("0.50")),
    ]
    results = im.compute_lines(lines)
    assert [result.line_total for result in results] == [TAKA("500.00"), TAKA("1600.50")]


def test_totals_subtract_the_invoice_discount_and_add_tax() -> None:
    lines = [im.LineInput("A", quantity=1, unit_price=TAKA("2000.00"))]
    totals = im.compute_totals(
        lines,
        invoice_discount=TAKA("100.00"),
        tax=TAKA("50.00"),
        status=im.STATUS_ISSUED,
    )
    assert totals.subtotal == TAKA("2000.00")
    assert totals.discount == TAKA("100.00")
    assert totals.tax == TAKA("50.00")
    assert totals.total == TAKA("1950.00")
    assert totals.due == TAKA("1950.00")


def test_a_discount_can_never_exceed_the_subtotal() -> None:
    lines = [im.LineInput("A", quantity=1, unit_price=TAKA("100.00"))]
    totals = im.compute_totals(lines, invoice_discount=TAKA("500.00"))
    assert totals.discount == TAKA("100.00")
    assert totals.total == Money.zero()


def test_status_follows_the_money() -> None:
    assert im.status_for(TAKA("1000"), Money.zero()) == im.STATUS_ISSUED
    assert im.status_for(TAKA("1000"), TAKA("400")) == im.STATUS_PARTIALLY_PAID
    assert im.status_for(TAKA("1000"), TAKA("1000")) == im.STATUS_PAID
    assert im.status_for(TAKA("1000"), TAKA("1200")) == im.STATUS_PAID


def test_a_void_invoice_stays_void() -> None:
    assert im.status_for(TAKA("1"), Money.zero(), current_status=im.STATUS_VOID) == im.STATUS_VOID
    assert im.status_for(TAKA("1"), Money.zero(), current_status=im.STATUS_DRAFT) == im.STATUS_DRAFT


def test_applying_a_payment_moves_paid_and_due() -> None:
    paid, due, status = im.apply_payment(TAKA("3101.00"), Money.zero(), TAKA("1000.00"))
    assert (paid, due, status) == (TAKA("1000.00"), TAKA("2101.00"), im.STATUS_PARTIALLY_PAID)
    paid, due, status = im.apply_payment(TAKA("3101.00"), TAKA("1000.00"), TAKA("2101.00"))
    assert (paid, due, status) == (TAKA("3101.00"), Money.zero(), im.STATUS_PAID)


def test_overpayment_is_refused() -> None:
    with pytest.raises(ValidationError, match="more than the amount due"):
        im.apply_payment(TAKA("1000.00"), TAKA("900.00"), TAKA("200.00"))
    with pytest.raises(ValidationError, match="greater than zero"):
        im.apply_payment(TAKA("1000.00"), Money.zero(), Money.zero())


def test_reversing_a_payment_restores_the_due() -> None:
    paid, due, status = im.reverse_payment(TAKA("3101.00"), TAKA("1000.00"), TAKA("1000.00"))
    assert (paid, due, status) == (Money.zero(), TAKA("3101.00"), im.STATUS_ISSUED)
    with pytest.raises(ValidationError, match="larger than the amount paid"):
        im.reverse_payment(TAKA("3101.00"), TAKA("100.00"), TAKA("500.00"))


def test_percentages_are_exact_and_round_half_up() -> None:
    assert im.percent_of(TAKA("2000.00"), Decimal("10")) == TAKA("200.00")
    # ৳333.33 × 15% = ৳49.9995, which rounds half-up to ৳50.00 — never 49.99.
    assert im.percent_of(TAKA("333.33"), Decimal("15")) == TAKA("50.00")
    assert im.percent_of(Money.zero(), Decimal("15")) == Money.zero()


def test_many_lines_never_drift() -> None:
    """100 lines of ৳0.03 must equal ৳3.00 exactly (integers, never floats)."""
    lines = [im.LineInput(f"Item {index}", quantity=1, unit_price=Money(3)) for index in range(100)]
    totals = im.compute_totals(lines, status=im.STATUS_ISSUED)
    assert totals.subtotal == Money(300)
    assert totals.total == TAKA("3.00")


def test_totals_accept_already_computed_lines() -> None:
    lines = [im.LineInput("A", quantity=1, unit_price=TAKA("10.00"))]
    results = im.compute_lines(lines)
    again = im.compute_totals(results, status=im.STATUS_ISSUED)
    assert again.subtotal == TAKA("10.00")


def test_paid_is_never_more_than_the_total() -> None:
    lines = [im.LineInput("A", quantity=1, unit_price=TAKA("100.00"))]
    totals = im.compute_totals(lines, paid=TAKA("500.00"), status=im.STATUS_ISSUED)
    assert totals.paid == TAKA("100.00")
    assert totals.due == Money.zero()
