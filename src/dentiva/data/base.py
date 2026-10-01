"""Declarative base, shared column types and mixins.

Conventions (see docs/04):
  * every table uses the naming convention below so migrations stay deterministic;
  * money is stored as INTEGER paisa through :class:`MoneyType` (ADR-0003);
  * timestamps are stored as UTC ISO-8601 text through :class:`UTCDateTime`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import Integer, MetaData, String, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from dentiva.core.money import Money

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class MoneyType(TypeDecorator):
    """Stores :class:`~dentiva.core.money.Money` as an INTEGER number of paisa."""

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Any, _dialect: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, Money):
            return value.paisa
        if isinstance(value, int):
            return value
        if isinstance(value, Decimal):
            return Money.from_taka(value).paisa
        raise TypeError(
            f"MoneyType received {type(value).__name__}; expected Money, int or Decimal"
        )

    def process_result_value(self, value: int | None, _dialect: Any) -> Money | None:
        return None if value is None else Money(int(value))


class UTCDateTime(TypeDecorator):
    """Stores tz-aware datetimes as UTC ISO-8601 text (unambiguous, sortable)."""

    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, _dialect: Any) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat(timespec="microseconds")

    def process_result_value(self, value: str | None, _dialect: Any) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)


class Base(DeclarativeBase):
    """Declarative base for every Dentiva Pro table."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: ClassVar[dict[Any, Any]] = {Money: MoneyType, datetime: UTCDateTime}


class AuditColumns:
    """Creation/modification metadata shared by mutable business tables."""

    created_at_utc: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    updated_at_utc: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SoftDeleteColumns:
    """Soft delete support: rows are archived, never silently removed."""

    deleted_at_utc: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    deleted_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at_utc is not None
