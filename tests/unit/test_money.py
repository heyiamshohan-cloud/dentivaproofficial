"""Money: integer paisa arithmetic (ADR-0003, REQ-MON-003, REQ-PAY-004)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, ClassVar

import pytest
from sqlalchemy import Integer, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from dentiva.core.money import Money, total
from dentiva.data.base import NAMING_CONVENTION, MoneyType


def test_from_taka_rejects_float() -> None:
    with pytest.raises(TypeError):
        Money.from_taka(12.5)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("0"), 0),
        (Decimal("1.00"), 100),
        (Decimal("12.34"), 1234),
        (Decimal("-7.05"), -705),
        ("1,250.50".replace(",", ""), 125050),
        (5, 500),
    ],
)
def test_from_taka(value, expected) -> None:
    assert Money.from_taka(value).paisa == expected


def test_rounding_is_half_up() -> None:
    assert Money.from_taka(Decimal("1.005")).paisa == 101
    assert Money.from_taka(Decimal("1.004")).paisa == 100
    assert Money.from_taka(Decimal("-1.005")).paisa == -101


def test_invalid_amount_raises_validation_error() -> None:
    from dentiva.core.errors import DentivaError

    with pytest.raises((ValueError, DentivaError)):
        Money.from_taka("not a number")


def test_arithmetic_never_uses_floats() -> None:
    a = Money.from_taka("10.10")
    b = Money.from_taka("0.20")
    assert (a - b) == Money.from_taka("9.90")
    assert (a + b) == Money.from_taka("10.30")
    assert (Money.from_taka("0.01") * 3) == Money.from_taka("0.03")
    assert (-a).paisa == -1010
    assert abs(Money.from_taka("-5")).paisa == 500


def test_comparisons_and_hashing() -> None:
    assert Money.from_taka(1) < Money.from_taka(2)
    assert Money.from_taka(2) >= Money.from_taka(2)
    assert {Money.from_taka(1), Money.from_taka(1)} == {Money.from_taka(1)}
    assert Money.zero().is_zero


def test_multiplication_by_decimal_rounds_half_up() -> None:
    assert (Money.from_taka("99.99") * Decimal("0.5")) == Money.from_taka("50.00")


def test_percent_rounds_once() -> None:
    assert Money.from_taka(100).percent("12.5") == Money.from_taka("12.50")
    assert Money.from_taka("333.33").percent(Decimal("10")) == Money.from_taka("33.33")


def test_split_preserves_total() -> None:
    amount = Money.from_taka("10.00")
    for parts in (1, 3, 7, 12):
        pieces = amount.split_evenly(parts)
        assert len(pieces) == parts
        assert total(pieces) == amount


def test_total_of_empty_is_zero() -> None:
    assert total([]) == Money.zero()


def test_formatting_uses_taka_symbol_and_grouping() -> None:
    assert Money.from_taka("1234.5").format() == "৳ 1,234.50"
    assert Money.from_taka("1234.5").format(symbol="BDT") == "BDT 1,234.50"
    assert Money.from_taka("1234.5").format_plain(grouping=False) == "1234.50"


def test_amount_in_words() -> None:
    assert Money.from_taka(0).amount_in_words() == "Zero Taka only"
    assert Money.from_taka(1250).amount_in_words().startswith("One Thousand Two Hundred and Fifty")


class _IsolatedBase(DeclarativeBase):
    """A private registry, so the test table never enters the product metadata."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: ClassVar[dict[Any, Any]] = {Money: MoneyType}


class MoneyRow(_IsolatedBase):
    """Module level model: SQLAlchemy resolves annotations from module globals."""

    __tablename__ = "money_row"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[Money] = mapped_column(MoneyType, nullable=False)


def test_negative_round_trip_with_database_column() -> None:
    from sqlalchemy import create_engine

    engine = create_engine("sqlite://", future=True)
    _IsolatedBase.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(MoneyRow(id=1, amount=Money.from_taka("-12.34")))
        session.commit()
    with Session(engine) as session:
        stored = session.get(MoneyRow, 1)
        assert stored is not None
        assert stored.amount == Money.from_taka("-12.34")
        assert isinstance(stored.amount.paisa, int)
