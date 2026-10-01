# ADR-0002 — Data layer: SQLite + SQLAlchemy 2.0 ORM + Alembic migrations

- Status: **Accepted** (Phase 1)

## Context
Offline-first single-workstation / small-LAN clinic product; zero server
administration; must survive power loss; must support unlimited records (no
artificial caps); must be transactional, auditable and restorable.

## Options considered
| Option | Verdict | Reason |
|---|---|---|
| **SQLite + SQLAlchemy 2.0 + Alembic** | **Chosen** | Embedded, serverless, zero-config, single-file DB (atomic backup/restore via the SQLite online backup API), `PRAGMA foreign_keys`, WAL for concurrency, SQLAlchemy 2.0 gives a typed ORM + Unit of Work, Alembic gives versioned, auditable migrations. All MIT-licensed. |
| PostgreSQL / MySQL bundled | Rejected | Requires a running service in the clinic, installer complexity, admin burden, slower on a single workstation, and far worse atomic-backup ergonomics. |
| Firebird / embedded variants | Rejected | Smaller ecosystem, weaker tooling, packaging/licensing questions. |
| Raw `sqlite3` + hand-rolled SQL | Rejected | No ORM means more hand-written SQL → higher risk of injection-style mistakes and drift; migration discipline must be built from scratch. |
| SQLAlchemy + custom migration runner (no Alembic) | Rejected | Alembic is industry standard, already MIT, and provides an auditable version table; a hand-rolled runner is more code to trust. |

## Decision
SQLite database file under the per-user data directory, accessed exclusively
through SQLAlchemy 2.0 sessions, schema owned by Alembic migrations
(hand-reviewed, `render_as_batch=True` for SQLite ALTER support).

## Mandatory connection PRAGMAs
`foreign_keys=ON`, `journal_mode=WAL`, `synchronous=FULL`, `busy_timeout=5000`,
`temp_store=MEMORY`, plus `PRAGMA integrity_check` on app start (cheap mode) and
before/after backup-restore.

## Consequences
- SQLite ALTER limitations → every schema change uses Alembic **batch** mode.
- Long/reporting queries must be indexed and paginated (see `docs/04`).
- DB file encryption is out of scope for v1; mitigated by OS user-profile ACLs and
  documented full-disk-encryption guidance (see `docs/05`).
