# Phase 3 report — Database, domain model, security, RBAC

**Status:** complete · **Branch:** `arena/01a0f682-dentivaproofficial` ·
**Date:** 2026-10-01 · **Phase plan:** [`13-phase-plan.md`](13-phase-plan.md) ·
**Previous report:** [`17-phase-02-report.md`](17-phase-02-report.md)

This report states exactly what was built, what was verified (with the command
that produces the evidence), what is deliberately deferred, and what the known
limitations are. Every claim below is reproducible from the repository.

---

## 1. Scope delivered

The Phase 3 scope from the plan was: full schema + migrations, repositories,
domain rules, services skeleton, Argon2id auth, session + auto-lock, permission
catalogue, roles, `@require` enforcement, audit foundation + triggers + hash
chain, financial permission enforcement.

| Deliverable | Where | Notes |
|---|---|---|
| Full business schema | `data/models/{identity,security,patient,clinical,scheduling,billing,inventory,accounting,ops}.py` | **60 tables**, 104 indexes, 9 aggregates, one module each; `MoneyType` (integer paisa) and `UTCDateTime` for every money/time column |
| First migration | `data/migrations/versions/0001_initial_schema.py` (revision `f49b8a81a1f2`) | Hand-reviewed, **reversible**, includes the append-only audit triggers |
| Reversible migrations | `data/engine.py::downgrade()` | Maintenance-only rollback; round trip proven by test |
| Unit of work | `data/session.py::session_scope` | One transaction per task, commit-once, rollback-on-error, UTC audit stamps |
| Domain rules | `domain/{permissions,rbac,numbering,invoice_math,period}.py` | Qt-free and DB-free; callable from services and tests alike |
| Permission catalogue | `domain/permissions.py` | **72 permissions** in 7 groups, `is_financial` and `sensitive` flags |
| Role templates | `data/seed/roles.py` | Administrator (72), Dentist (24), Receptionist (16), Dental Assistant (9), Accountant (15), Inventory Manager (7), Read-only (20) |
| Service layer | `services/*.py` (22 modules, 18 services) | 133 public entry points: **105 `@require`-protected** (21 of them additionally demand a recent password), 10 `@public_operation`, 14 `@internal`; the 4 `audit.*` methods are transaction-joiners, not entry points |
| Enforcement | `services/rbac.py` | `@require(permission, action=…, entity=…, entity_id_arg=…, sensitive=…)` — permission check **and** audit write **and** re-auth gate in one decorator |
| Argon2id auth | `security/password.py`, `services/auth_service.py` | Per-password salt, silent rehash on parameter upgrade, policy (10 chars, 3 of 4 classes, history of 3), lockout 60 s → 15 min doubling, unknown-user verification burns the same work |
| Session & auto-lock | `security/session.py` | Immutable value object, thread-local current actor, idle countdown for 5/10/15/30 min, lock/unlock, re-auth valid for 5 min |
| Audit foundation | `services/audit_service.py` + SQL triggers | 21 columns incl. before/after JSON, severity, session and correlation id; `prev_hash`/`row_hash` SHA-256 chain; `verify()` reports the first broken row |
| Append-only guarantee | `trg_audit_log_no_update`, `trg_audit_log_no_delete` | `RAISE(ABORT)` inside SQLite — a direct `UPDATE`/`DELETE` fails even outside the application |
| Financial enforcement | `tests/security/test_financial_isolation.py` | Money-bearing services may only declare financial permissions; search and reports refuse without them |
| Offline activation | `security/activation.py`, `security/_activation_part_a.py`, `_activation_part_b.py` | Verifier and salt split across two private modules; HMAC token written to file **and** database; both must agree |
| Secret store | `security/secrets.py` | Owner-only key file, seal/unseal with tamper detection, `machine_id` |
| Traceability tooling | `tools/trace_report.py` | Cross-checks `docs/01` ↔ `docs/12` ↔ the test suite; `--release` fails while any mandatory requirement is below **V** |

### 1.1 Design decisions made this phase

- **Enforcement lives in the decorator, not in the screens.** A UI that hides a
  button is not access control. `@require` reads the *current session* from a
  thread-local, checks the permission, raises `PermissionDenied` (which the
  error hierarchy turns into a safe user message), and writes the audit entry in
  the caller's transaction. Denials are audited too.
- **The audit log is defended three times**: SQL triggers (nothing can rewrite a
  row), a hash chain (a rewrite that bypasses the triggers is detected), and the
  absence of any update path in the service (the normal code cannot do it).
- **Money is never a float and never duplicated.** `domain/invoice_math.py`
  computes every figure from the stored parts in integer paisa; the service
  layer has no "cached total" column that could drift.
- **Reporting periods follow the local calendar** (`domain/period.py`): the
  clinic week starts on **Saturday**, the Bangladesh working week.
- **Reversibility is a claim, so it is now a test.** `docs/04` §10 says
  revisions are reversible; `downgrade()` exists and the round trip is proven.

---

## 2. Verification evidence

All commands were run in this workspace; each is reproducible.

```bash
bash tools/dev/setup_headless_linux.sh            # venv + stubs + fonts (~21 s)
export QT_QPA_PLATFORM=offscreen                  # Linux/headless
pytest -q                                         # 289 passed
ruff check .                                      # All checks passed
ruff format --check .                             # 167 files already formatted
mypy src/dentiva                                  # Success: no issues found in 96 source files
vulture src tests tools --min-confidence 80       # no findings
python -m dentiva.main --selftest                 # PASS — 9/9 checks
python -m dentiva.main --audit-layout             # PASS — 16 screens × 5 resolutions, 0 issues
python tools/trace_report.py                      # PASS — matrix agrees with baseline + suite
python tools/trace_report.py --release            # FAIL by design (259 mandatory not yet V)
```

Self-test output (verbatim):

```
[PASS] environment: Qt 6.11.2, SQLAlchemy 2.1.1
[PASS] paths: data root created and traversal blocked
[PASS] logging: rotating log configured, secrets redacted
[PASS] database: migrations applied and integrity verified (revision f49b8a81a1f2)
[PASS] money: integer paisa arithmetic verified
[PASS] unicode: Bangla/Latin text helpers verified
[PASS] theme: stylesheet generated, fonts loaded (Noto Sans, Noto Sans SemiBold,
              Noto Sans Bengali, Noto Sans Bengali SemiBold)
[PASS] icons: 49 icons rendered, Bengali glyph coverage confirmed
[PASS] shell: 16 screens built and audited without layout defects
```

Traceability report (verbatim):

```
baseline   : 317 requirements
matrix     : 219 rows
status     : R=0, V=63, I=7, IP=28, P=219  (of 317 mapped)
priority   : M=296, S=20, N=1
test files : 28 referenced, 243 tests collected by AST
planned    : 130 test targets for later phases
process    : 16 targets verified by review/CI
[PASS] the matrix agrees with the baseline and the test suite
```

### 2.1 Test suite (289 tests, 32 files)

| Suite | Files | Covers |
|---|---|---|
| `tests/unit` | 20 | money, errors, paths, text/Unicode, hashing, logging redaction, atomic IO, clock, theme, icons, no-network, paging, **password policy/hash/Argon2id**, **session/auto-lock/re-auth**, **reporting periods**, **invoice mathematics**, **offline activation**, **permission docs ↔ catalogue**, **traceability checker** |
| `tests/security` | 5 | **permission matrix** (13), **financial isolation** (10), **audit append-only** (12), **auth flow** (15), **secrets** (8) |
| `tests/integration` | 2 | database PRAGMAs/backup/`session_scope`, **schema integrity** (13) |
| `tests/ui` | 6 | components, `ResponsiveGrid`, shell/navigation, layout audit, CLI, About |

### 2.2 The four Phase-3 exit-gate tests

| Gate | Test | What it proves |
|---|---|---|
| Schema matches `docs/04` | `tests/integration/test_schema_integrity.py` (13) | A real `alembic upgrade head` on an empty file produces exactly the 60 ORM tables — no missing table, no orphan table, 104 indexes, both audit triggers, integer money columns, 6 required unique indexes, `PRAGMA integrity_check`/`foreign_key_check` clean, re-upgrade idempotent, and **upgrade → downgrade → upgrade round trip** |
| Permission matrix | `tests/security/test_permission_matrix.py` (13) | Every one of the 18 services' 133 entry points declares a permission, `@public_operation` or `@internal`; every declared code exists in the 72-code catalogue; 40+ protected methods are exercised with a permission-less session and refused; sensitive methods demand fresh re-authentication; denials are audited; the Administrator role cannot be stripped of `role.manage` |
| Financial isolation | `tests/security/test_financial_isolation.py` (10) | Money-bearing services declare only financial permissions; a user holding **every** non-financial permission still cannot create an invoice, take a payment, see an invoice in global search, or open a financial report; seeded clinical roles have no money-write permission; every denial is audited |
| Audit append-only | `tests/security/test_audit_append_only.py` (12) | `UPDATE` and `DELETE` are rejected by the triggers; a service-level attempt fails; the hash chain detects a tampered row and reports the first broken id; no update path exists in the service; a fresh database verifies intact; the actor columns resolve to the **signed-in user**, not to a placeholder |

### 2.3 Defects found and fixed during this phase

Honest record — these were real bugs that the phase's own tests caught:

1. **Audit entries were attributed to nobody.** `AuditService.record()` read the
   actor's `business_id`/`user_id`/`username`/`roles` from its `actor` argument
   (`None` for sign-in and for internal calls) instead of the resolved actor.
   Every row was therefore anonymous. Fixed; `tests/security/test_auth_flow.py`
   and the append-only test now assert the username, user id and role names.
2. **Two test modules polluted the product metadata.** `tests/unit/test_money.py`
   and `tests/integration/test_database.py` declared helper models on
   `dentiva.data.base.Base`, so `money_row` and `note` were silently added to
   the ORM metadata and reported as "tables missing after upgrade". Both now use
   a private declarative base, and a guard test fails the suite if any test
   model is ever declared on the product base again.
3. **The password policy reported the wrong reason.** A breached password like
   `bangladesh1` was rejected for length rather than for being common. The
   common-password check now runs first, so the message the receptionist sees is
   the useful one.
4. **`downgrade()` did not exist** although `docs/04` claims reversible
   migrations. Added, tested.

---

## 3. What the security model looks like today

```
sign in → Argon2id verify → Session (immutable, thread-local)
                              ├── permissions (from roles, resolved per business)
                              ├── idle countdown → auto-lock at 5/10/15/30 min
                              └── re-auth stamp (valid 5 min)
   │
   └── every service call ──→ @require(permission, sensitive?)
                                ├── no session      → AuthenticationRequired
                                ├── no permission   → PermissionDenied + audit
                                ├── sensitive + stale re-auth → AuthenticationRequired
                                └── ok              → work + audit + hash chain
```

- **Password policy:** minimum 10 characters, at least 3 of 4 character classes,
  not one of the 12 blocked common passwords, not the username, not any of the
  last 3 passwords. Hashes carry their own salt; parameters are raised silently
  on next sign-in when the policy is tightened.
- **Lockout:** 5 failures lock for 60 s, doubling each further failure to a
  15-minute ceiling. A successful sign-in clears the counter.
- **Activation:** the fixed code is verified against an Argon2id verifier whose
  hash and salt are split across two private modules; the plaintext appears
  nowhere in `src/` (asserted by a test that greps the package). The resulting
  token is an HMAC of the machine identifier, written to both the data directory
  and the database; start-up requires the two to agree, so neither a copied
  folder nor a copied database alone will activate another machine.
- **Audit:** 21 columns, severity levels, before/after JSON for sensitive
  changes, session and correlation ids, and a SHA-256 chain (`prev_hash` →
  `row_hash`) verified from the service layer.

---

## 4. Deferred to later phases (per the plan, not gaps)

| Item | Phase |
|---|---|
| `LockOverlay`, activity monitor, draft autosave (the *countdown* and the unlock/re-auth service calls are done and tested) | 4 |
| First-run setup wizard, clinic/dentist/staff/user screens, role editor, Settings, Activation dialog | 5 |
| `repositories/` package as a separate layer (queries live in the services today, paged and indexed) | 6+ |
| Patients, visits, chart, appointments, prescriptions, billing, inventory, accounting, printing, backup | 6–16 |
| Financial *workflows* on top of the enforced permissions (invoice editor, payment capture, reports UI) | 10–12 |
| Backup/restore, import/export | 13 |
| Installer, reproducible release build | 17–18 |

---

## 5. Known limitations (stated honestly)

1. **All verification so far is Linux/offscreen.** Windows-specific behaviour
   (DPAPI secret store, printing, DPI, installer) is exercised only by the
   `windows-latest` CI job. The secret store runs its POSIX fallback here; the
   DPAPI path is written but not yet executed on Windows.
2. **No screens consume the services yet.** The shell still opens the
   phase-gated build screens; the services are exercised by tests, not by clicks.
   That is the Phase 4/5 work, and nothing here is a stub.
3. **Auto-lock is enforced in the session object, not yet by a timer in the
   event loop.** `Session.should_lock()` and the countdown are tested; wiring
   them to the Qt activity monitor happens with the shell (Phase 4) so that
   unsaved work can be preserved (REQ-AUTH-004).
4. **40 of the 72 permissions are used by today's services.** The rest belong to
   screens and workflows built in later phases; they are already documented
   (`docs/06`) and enforced identically the moment a service declares them.
   `tests/unit/test_permission_docs.py` keeps the catalogue and the document in
   agreement.
5. **The migration is reversible, but a downgrade destroys data.** It is a
   support tool for rolling back an installation, not a user feature; the
   docstring says so and it deliberately takes no automatic backup.

---

## 6. Definition of Done (Phase 3) — checklist

- [x] No new lint/type errors (`ruff check`, `ruff format --check`, `mypy` — 96 files)
- [x] No failing tests (**289 passing**, up from 138 at the end of Phase 2); no dead code (`vulture`, including `tools/`)
- [x] No TODO/FIXME in `src/`, `tests/` or `tools/` (CI gate)
- [x] Schema matches `docs/04`; `PRAGMA integrity_check` and `foreign_key_check` clean
- [x] Permission matrix test passes for every service method
- [x] Financial isolation test passes
- [x] Audit append-only test passes
- [x] Migrations reversible where claimed (round-trip test added)
- [x] Screens untouched this phase; layout audit still clean at 5 resolutions
- [x] Traceability rows updated (`docs/12`): 63 requirements now **V**, 28 **IP**, 7 **I**
- [x] `tools/trace_report.py` cross-checks the matrix against the baseline and the suite (REQ-TRC-002), with its own test
- [x] Docs updated to match reality (`docs/00`, `docs/04` §10, this report)
- [x] PR opened for review — **not merged** (REQ-PR-001)
