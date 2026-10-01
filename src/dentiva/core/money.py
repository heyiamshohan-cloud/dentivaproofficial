"""Money handling for Dentiva Pro.

All monetary amounts are stored and computed as **integer minor units** (paisa;
100 paisa = 1 BDT). Floating point never participates in a money calculation
(see ADR-0003). `decimal.Decimal` is used only at the parsing/formatting
boundaries and is quantised with `ROUND_HALF_UP`.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, SupportsIndex

ZERO_PAISA = 0
PAISA_PER_TAKA = 100
CENT = Decimal("0.01")


class Money:
    """An immutable amount of money in paisa."""

    __slots__ = ("paisa",)

    #: Integer minor units (1 BDT = 100 paisa). The only stored state.
    paisa: int

    def __init__(self, paisa: int = ZERO_PAISA) -> None:
        if isinstance(paisa, bool) or not isinstance(paisa, int):
            raise TypeError("Money must be constructed from an integer number of paisa")
        object.__setattr__(self, "paisa", paisa)

    # ------------------------------------------------------------------ build --
    @classmethod
    def zero(cls) -> Money:
        return cls(0)

    @classmethod
    def from_paisa(cls, paisa: int) -> Money:
        return cls(int(paisa))

    @classmethod
    def from_taka(cls, value: Decimal | int | str) -> Money:
        """Build from a taka amount. ``float`` is rejected on purpose."""
        if isinstance(value, float):
            raise TypeError(
                "Money.from_taka() does not accept float; pass Decimal, int or str "
                "so that no binary rounding can enter a monetary value"
            )
        if isinstance(value, SupportsIndex):
            return cls(int(value) * PAISA_PER_TAKA)
        try:
            decimal_value = value if isinstance(value, Decimal) else Decimal(str(value).strip())
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Not a valid amount: {value!r}") from exc
        return cls(
            int((decimal_value * PAISA_PER_TAKA).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        )

    # ------------------------------------------------------------------ read --
    @property
    def taka(self) -> Decimal:
        return (Decimal(self.paisa) / PAISA_PER_TAKA).quantize(CENT)

    def __int__(self) -> int:
        return self.paisa

    def __hash__(self) -> int:
        return hash(("Money", self.paisa))

    def __repr__(self) -> str:
        return f"Money(paisa={self.paisa})"

    def __str__(self) -> str:
        return self.format()

    # -------------------------------------------------------------- arithmetic --
    def __add__(self, other: Money) -> Money:
        return Money(self.paisa + _as_paisa(other))

    def __sub__(self, other: Money) -> Money:
        return Money(self.paisa - _as_paisa(other))

    def __mul__(self, factor: int | Decimal) -> Money:
        if isinstance(factor, Decimal):
            return Money.from_taka((self.taka * factor).quantize(CENT, rounding=ROUND_HALF_UP))
        if not isinstance(factor, int):
            raise TypeError("Money can only be multiplied by int or Decimal")
        return Money(self.paisa * factor)

    def __neg__(self) -> Money:
        return Money(-self.paisa)

    def __abs__(self) -> Money:
        return Money(abs(self.paisa))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Money):
            return self.paisa == other.paisa
        return NotImplemented

    def __lt__(self, other: Money) -> bool:
        return self.paisa < _as_paisa(other)

    def __le__(self, other: Money) -> bool:
        return self.paisa <= _as_paisa(other)

    def __gt__(self, other: Money) -> bool:
        return self.paisa > _as_paisa(other)

    def __ge__(self, other: Money) -> bool:
        return self.paisa >= _as_paisa(other)

    @property
    def is_negative(self) -> bool:
        return self.paisa < 0

    @property
    def is_zero(self) -> bool:
        return self.paisa == 0

    # -------------------------------------------------------------- business --
    def percent(self, rate: Decimal | str) -> Money:
        """Return ``rate`` percent of this amount, rounded half-up to paisa."""
        percent = rate if isinstance(rate, Decimal) else Decimal(str(rate))
        return Money.from_taka(
            (self.taka * percent / Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP)
        )

    def split_evenly(self, parts: int) -> list[Money]:
        """Split into ``parts`` amounts whose sum equals this amount exactly."""
        if parts <= 0:
            raise ValueError("parts must be positive")
        base, remainder = divmod(abs(self.paisa), parts)
        pieces = [Money(base) for _ in range(parts)]
        for index in range(remainder):
            pieces[index] = Money(pieces[index].paisa + 1)
        return [Money(-piece.paisa) if self.is_negative else piece for piece in pieces]

    # -------------------------------------------------------------- formatting --
    def format(self, symbol: str = "৳", *, grouping: bool = True, decimals: int = 2) -> str:
        quantum = Decimal(1).scaleb(-decimals)
        amount = self.taka.quantize(quantum, rounding=ROUND_HALF_UP)
        text = f"{amount:,.{decimals}f}" if grouping else f"{amount:.{decimals}f}"
        return f"{symbol} {text}" if symbol else text

    def format_plain(self, *, grouping: bool = True) -> str:
        return self.format(symbol="", grouping=grouping)

    def amount_in_words(self) -> str:
        """Taka amount in words, used on printed receipts."""
        return _taka_in_words(int(abs(self.paisa) // PAISA_PER_TAKA))


def _as_paisa(value: Any) -> int:
    if isinstance(value, Money):
        return value.paisa
    raise TypeError(f"Expected Money, got {type(value).__name__}")


def total(values: list[Money] | tuple[Money, ...]) -> Money:
    """Sum of money values (empty input -> zero)."""
    return Money(sum(value.paisa for value in values))


_ONES = (
    "Zero",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
    "Thirteen",
    "Fourteen",
    "Fifteen",
    "Sixteen",
    "Seventeen",
    "Eighteen",
    "Nineteen",
)
_TENS = ("", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety")


def _under_thousand(number: int) -> str:
    if number < 20:
        return _ONES[number]
    if number < 100:
        tens, ones = divmod(number, 10)
        return _TENS[tens] + (f"-{_ONES[ones]}" if ones else "")
    hundreds, rest = divmod(number, 100)
    return f"{_ONES[hundreds]} Hundred" + (f" and {_under_thousand(rest)}" if rest else "")


def _taka_in_words(amount: int) -> str:
    """Convert a non-negative integer amount of taka into English words."""
    if amount == 0:
        return "Zero Taka only"
    scales = ((1_000_000_000, "Billion"), (1_000_000, "Million"), (1_000, "Thousand"))
    words = []
    remainder = amount
    for factor, label in scales:
        count, remainder = divmod(remainder, factor)
        if count:
            words.append(f"{_under_thousand(count)} {label}")
    if remainder:
        words.append(_under_thousand(remainder))
    return " ".join(words) + " Taka only"
