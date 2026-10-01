"""Human-visible document numbers (REQ-FRS-006, docs/04 §7).

Numbers are allocated from the ``number_sequence`` table with a single
``UPDATE … RETURNING`` statement, so two concurrent registrations can never
receive the same patient code or invoice number. Uniqueness is *also* enforced
by a database constraint — the sequence is for readability, never the only guard.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from dentiva.core.clock import local_today
from dentiva.data.models.ops import NumberSequence

#: Sequence scopes.
SCOPE_PATIENT = "patient"
SCOPE_VISIT = "visit"
SCOPE_INVOICE = "invoice"
SCOPE_PAYMENT = "payment"
SCOPE_PRESCRIPTION = "prescription"
SCOPE_QUEUE_TICKET = "queue_ticket"

SCOPES: tuple[str, ...] = (
    SCOPE_PATIENT,
    SCOPE_VISIT,
    SCOPE_INVOICE,
    SCOPE_PAYMENT,
    SCOPE_PRESCRIPTION,
    SCOPE_QUEUE_TICKET,
)

#: Default prefixes and padding per scope (a clinic can change both later).
DEFAULTS: dict[str, tuple[str, int, bool]] = {
    SCOPE_PATIENT: ("P", 4, False),
    SCOPE_VISIT: ("V", 3, False),
    SCOPE_INVOICE: ("INV", 4, True),
    SCOPE_PAYMENT: ("MR", 4, True),
    SCOPE_PRESCRIPTION: ("RX", 4, True),
    SCOPE_QUEUE_TICKET: ("", 2, False),
}


@dataclass(frozen=True, slots=True)
class AllocatedNumber:
    """The number that was allocated, plus its parts for display."""

    value: str
    number: int
    prefix: str
    year: int | None


def ensure_sequences(session: Session, business_id: int) -> None:
    """Create the default sequences for a business (idempotent)."""
    for scope, (prefix, padding, year_reset) in DEFAULTS.items():
        exists = session.execute(
            select(NumberSequence).where(
                NumberSequence.business_id == business_id,
                NumberSequence.scope == scope,
            )
        ).scalar_one_or_none()
        if exists is None:
            session.add(
                NumberSequence(
                    business_id=business_id,
                    scope=scope,
                    prefix=prefix,
                    next_value=1,
                    padding=padding,
                    year_reset=year_reset,
                    year=local_today().year if year_reset else None,
                )
            )
    session.flush()


def allocate(session: Session, *, business_id: int, scope: str) -> AllocatedNumber:
    """Atomically take the next number for *scope* and return it formatted."""
    if scope not in DEFAULTS:
        raise ValueError(f"Unknown number sequence scope: {scope!r}")
    if (
        session.execute(
            select(NumberSequence.id).where(
                NumberSequence.business_id == business_id, NumberSequence.scope == scope
            )
        ).scalar_one_or_none()
        is None
    ):
        ensure_sequences(session, business_id)

    year = local_today().year
    # Year-scoped counters restart every January (invoice/payment/receipt numbers).
    session.execute(
        update(NumberSequence)
        .where(
            NumberSequence.business_id == business_id,
            NumberSequence.scope == scope,
            NumberSequence.year_reset.is_(True),
            NumberSequence.year.is_not(None),
            NumberSequence.year < year,
        )
        .values(next_value=1, year=year)
    )
    row = session.execute(
        update(NumberSequence)
        .where(
            NumberSequence.business_id == business_id,
            NumberSequence.scope == scope,
        )
        .values(next_value=NumberSequence.next_value + 1)
        .returning(
            NumberSequence.next_value,
            NumberSequence.prefix,
            NumberSequence.padding,
            NumberSequence.year,
        )
    ).one()
    number = int(row[0]) - 1  # the UPDATE already advanced the counter
    prefix, padding, stored_year = str(row[1]), int(row[2]), row[3]
    return AllocatedNumber(
        value=format_number(prefix, number, padding, stored_year),
        number=number,
        prefix=prefix,
        year=stored_year,
    )


def format_number(prefix: str, number: int, padding: int, year: int | None = None) -> str:
    """Render ``INV-2026-0007`` / ``P-0007`` / ``07`` style numbers."""
    digits = f"{max(0, int(number)):0{max(1, int(padding))}d}"
    parts = [part for part in (prefix, str(year) if year else "", digits) if part]
    return "-".join(parts)


def peek(session: Session, *, business_id: int, scope: str) -> str:
    """What the next number will look like (for UI placeholders)."""
    sequence = session.execute(
        select(NumberSequence).where(
            NumberSequence.business_id == business_id, NumberSequence.scope == scope
        )
    ).scalar_one_or_none()
    if sequence is None:
        prefix, padding, year_reset = DEFAULTS[scope]
        return format_number(prefix, 1, padding, local_today().year if year_reset else None)
    return format_number(sequence.prefix, sequence.next_value, sequence.padding, sequence.year)
