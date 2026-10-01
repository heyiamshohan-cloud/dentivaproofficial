# ADR-0003 — Money representation: integer minor units (paisa)

- Status: **Accepted** (Phase 1)

## Context
The specification forbids risk to monetary precision ("Do not use floating-point
arithmetic for monetary values if it risks precision problems") and demands that
invoice totals, payments, discounts, dues and accounting summaries stay
mathematically consistent.

## Decision
- Persist **all** monetary amounts as `INTEGER` **paisa** (1 BDT = 100 paisa).
- Convert to `decimal.Decimal` only at the boundary (input parsing and display),
  using a single `Money` value object + SQLAlchemy `TypeDecorator`.
- Rounding rule: `ROUND_HALF_UP`, quantised to paisa, applied once per line item
  and once per document total (documented in `docs/04`).
- Percentages/discounts computed with `Decimal`, quantised once.

## Rejected
- `REAL`/`FLOAT` — binary rounding error, non-deterministic aggregates.
- SQLite `NUMERIC` via SQLAlchemy `Numeric` — SQLite NUMERIC affinity stores as
  INTEGER **or** REAL depending on the value, so precision is not guaranteed.
- Storing formatted strings — un-queryable, un-summable.

## Consequences
- No float ever enters money code paths; a lint rule + unit tests enforce it.
- Display layer formats as `৳ 1,234.00` / `BDT 1,234.00` per locale setting.
