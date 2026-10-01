# ADR-0009 — Audit log: append-only table + hash chain + DB triggers

- Status: **Accepted** (Phase 1)

## Decision
- `audit_log` rows are **append-only**. SQLite triggers `BEFORE UPDATE` and
  `BEFORE DELETE` raise `ABORT`, so the history cannot be erased even by direct
  SQL access through a generic SQLite tool (verified in the Phase 1 spike).
- Each row stores `prev_hash` and `row_hash`
  (`SHA-256(prev_hash || canonical_json(fields))`) forming a **tamper-evident hash
  chain**; `System Health` verifies the chain and reports the first broken link.
- Fields: `id, ts_utc, ts_local, actor_user_id, actor_username, actor_role, action,
  entity, entity_id, business_id, patient_id (nullable), visit_id (nullable),
  summary, before_json, after_json, severity, source (ui/service/cli), ip_host,
  session_id, prev_hash, row_hash`.
- Sensitive values (passwords, hashes, activation secrets) are **never** written to
  audit fields; a redaction filter runs before persistence.

## Rejected
- Mutable audit rows with a "deleted" flag (erasable).
- File-based audit log only (harder to query, easier to lose).
