# Phase 2 report — Repository, engineering foundation & design system

**Status:** complete · **Branch:** `arena/01a0f682-dentivaproofficial` ·
**Date:** 2026-10-01 · **Phase plan:** [`13-phase-plan.md`](13-phase-plan.md)

This report states exactly what was built, what was verified (with the command
that produces the evidence), what is deliberately deferred to later phases, and
what the known limitations are. Every claim below is reproducible from the
repository.

---

## 1. Scope delivered

The Phase 2 scope from the plan was: project skeleton, pinned dependencies,
ruff/mypy/pytest wiring, logging, paths/config, error hierarchy, `Money`,
Alembic wiring, token→QSS design system, icon set, app-shell skeleton, GitHub
Actions baseline, `tools/dev` bootstrap, initial README/docs index.

| Deliverable | Where | Notes |
|---|---|---|
| `src/` layout, packaging metadata | `pyproject.toml`, `src/dentiva/**` | 48 Python modules, ~6 600 lines; console + GUI entry points (`DentivaPro`) |
| Pinned dependencies | `requirements.txt`, `requirements-dev.txt`, `requirements-build.txt`, `pyproject.toml` | Runtime, dev and build pins kept in sync (a drift was found and fixed) |
| Core primitives | `core/{money,paths,logging_setup,errors,clock,textutil,hashing,fileutil,paging}.py` | Qt-free and DB-free; importable without a display |
| Money | `core/money.py`, `data/base.py::MoneyType` | Integer paisa; `float`/`bool` rejected at construction; SQLAlchemy round-trip type |
| Data layer | `data/{base,engine,session}.py`, `data/migrations/` | WAL + `foreign_keys=ON` + `synchronous=FULL` + busy timeout; integrity and FK checks; online backup; packaged Alembic environment |
| Design system | `ui/theme/{tokens,qss,icons,fonts}.py` | One token source → generated QSS; 49 in-house icons rendered by a tiny SVG path engine; bundled Noto Sans + Noto Sans Bengali |
| Components | `ui/components/**` | Buttons, inputs, display, feedback, cards, `ResponsiveGrid`, tables, tabs, states (`StateStack`), dialogs |
| Shell | `ui/shell/{navigation,sidebar,header,main_window}.py`, `ui/views/*` | 16-item phase-gated navigation registry, collapsible sidebar, header, lazy `QStackedWidget`, About screen |
| Layout audit | `ui/diagnostics.py`, `diagnostics.py::audit_layout`, `--audit-layout` | Overflow, clipped labels, unintended horizontal scroll, sibling overlap, minimum-size fit |
| Self-test / diagnostics | `diagnostics.py`, `main.py` | `--selftest`, `--diagnostics FILE`, `--build-info`, `--audit-layout [--scale F]` |
| CI | `.github/workflows/ci.yml` | ruff, ruff format, mypy, pytest (Linux + **Windows**), vulture, hygiene (TODO/secret grep) |
| Bootstrap | `tools/dev/setup_headless_linux.sh` | Headless Linux venv; stubs are created outside the repository and never shipped |
| Docs | `README.md`, `THIRD_PARTY_NOTICES.md`, `licenses/`, `docs/00`, `docs/12`, `docs/16`, this report | |

## 2. Verification evidence

All commands below were run in this workspace; each is reproducible.

```bash
export QT_QPA_PLATFORM=offscreen          # Linux/headless
pytest -q                                  # 138 passed
ruff check .                               # All checks passed
ruff format --check .                      # 100 files already formatted
mypy src/dentiva                           # Success: no issues found in 48 source files
vulture src tests --min-confidence 80      # no findings
python -m dentiva.main --selftest          # PASS — 9/9 checks
python -m dentiva.main --audit-layout      # PASS — 16 screens × 5 resolutions, 0 issues
python -m dentiva.main --audit-layout --scale 2.0   # PASS at 200 % scaling
python -m dentiva.main --build-info        # Dentiva Pro 1.0.0 (development) …
```

Self-test output (verbatim):

```
[PASS] environment: Qt 6.11.2, SQLAlchemy 2.1.1
[PASS] paths: data root created and traversal blocked
[PASS] logging: rotating log configured, secrets redacted
[PASS] database: migrations applied and integrity verified (revision None)
[PASS] money: integer paisa arithmetic verified
[PASS] unicode: Bangla/Latin text helpers verified
[PASS] theme: stylesheet generated, fonts loaded (Noto Sans, Noto Sans SemiBold,
              Noto Sans Bengali, Noto Sans Bengali SemiBold)
[PASS] icons: 49 icons rendered, Bengali glyph coverage confirmed
[PASS] shell: 16 screens built and audited without layout defects
```

Test suite (138 tests, 20 files):

| Suite | Covers |
|---|---|
| `tests/unit` (12 files) | money (incl. DB round-trip and split-total preservation), errors, paths (Windows/Linux roots, traversal refusal, safe names), text/Unicode, hashing, logging redaction, atomic file IO + disk-space error, clock injection, theme/QSS tokens, icon rendering, Bengali glyph coverage, **no networking imports**, paging |
| `tests/integration/test_database.py` | PRAGMA policy, Alembic wiring, `PRAGMA integrity_check`, online backup with Bangla content, `session_scope` commit/rollback, `MigrationError` |
| `tests/ui` (6 files) | component state matrix (every family), `ResponsiveGrid` arithmetic (6 cards → 3+3), shell/navigation/persistence, layout audit at 5 resolutions and 5 scaling factors, CLI entry points, About screen |

Notable guarantees that are now mechanically enforced:

- **No network capability.** `tests/unit/test_no_network_imports.py` parses every
  module under `src/` and fails on any import of `socket`, `urllib`, `http`,
  `requests`, … Qt's network module is permitted only for `QLocalServer`/
  `QLocalSocket` (the single-instance guard), which never touch a NIC.
- **No plaintext activation code.** The same test fails if the fixed code
  appears anywhere under `src/`. It was found (in a self-test fixture) and
  removed during this phase.
- **Money never floats.** `Money(True)` and `Money(1.5)` raise `TypeError`;
  `split_evenly` preserves the total to the paisa.
- **Balanced grids.** `ResponsiveGrid` is asserted to place six cards at (0,0),
  (0,1), (0,2), (1,0), (1,1), (1,2) at a three-column breakpoint — never 4+2.
- **UI settings never touch the registry or the developer's machine.** State
  lives in `<data dir>/ui.ini`; the test suite redirects it per test.

## 3. What the shell looks like today

- Header: brand mark + name, clinic name ("Clinic not configured" until setup
  runs in Phase 5), today's date with weekday (refreshed every minute).
- Sidebar: four groups — **Practice** (Dashboard, Patients, Appointments,
  Queue), **Clinical** (Treatments, Prescriptions), **Billing** (Invoice,
  Payments, Inventory, Accounting), **Administration** (Staff & Users, Backup &
  Restore, Settings, Audit Log, System Health, About). Collapsed (icon-only,
  still tool-tipped) and expanded states both work and persist across restarts.
- Content: every navigation item opens a screen. Items scheduled for a later
  phase open an explicit build-state screen ("Scheduled for Phase N") — never a
  silent stub and never a button that does nothing. `About` is a real screen
  (product, version, **Created by Shohan Khan**, mailto link, third-party
  notices, expandable system details).
- `CURRENT_PHASE` in `ui/shell/navigation.py` is the single lever that turns
  pending modules into real screens; `tests/ui/test_shell.py` fails if any
  module is still pending at or before the current phase.

## 4. Deferred to later phases (per the plan, not gaps)

| Item | Phase |
|---|---|
| Full schema + the first Alembic migration, repositories, services | 3 (the migration environment, PRAGMA policy and integrity checks are already wired; the first business migration lands with the models) |
| Authentication, RBAC enforcement, audit chain, activation | 3 |
| Notification drawer, toasts, shortcut and search frameworks, animation framework | 4 |
| Clinic setup wizard, settings screens, staff/users | 5 |
| Patients, visits, chart, appointments, prescriptions, billing, inventory, accounting, printing, backup | 6–16 |
| Installer, reproducible release build | 17–18 |

## 5. Known limitations (stated honestly)

1. **All verification so far is Linux/offscreen.** Qt rendering, layout geometry,
   Unicode shaping, SQLite behaviour and the audit harness were exercised on
   Linux with stubbed GL/EGL/dbus symbols. The Windows-specific paths
   (printing, DPI, installer) are exercised by the `windows-latest` CI job,
   which runs the same suite plus `--selftest` and `--audit-layout` at 200 %.
   The very first Windows run of this phase's workflow is part of the evidence
   the reviewer should look at.
2. **I cannot see.** Visual acceptance is therefore expressed as automated
   geometry/overflow/elision/overlap assertions and screenshot bundles for
   human review; "looks premium" still requires a human pass at Phase 4.
3. **No business schema yet.** The database the app creates is migrated and
   integrity-checked but contains only Alembic's bookkeeping until Phase 3.
4. **The icon master (`assets/icons/dentiva.png`) is not designed yet**, so the
   About screen and window icon fall back to an in-house glyph. The window icon
   path and the ICO/PNG pipeline are specified (`ICO-001…006`) and land with
   Phase 4/17.

## 6. Definition of Done (Phase 2) — checklist

- [x] No new lint/type errors (`ruff check`, `ruff format --check`, `mypy`)
- [x] No failing tests (138 passing); no dead code (`vulture`)
- [x] No TODO/FIXME in `src/` or `tests/` (CI gate added)
- [x] Screens pass the layout audit at 1366×768 … 3840×2160 and 100–200 % scaling
- [x] Traceability rows updated (`docs/12`) — 42 rows moved to I/V/IP
- [x] Docs updated to match reality (`README.md`, `docs/00`, `docs/16`, this report)
- [x] Dependency licences recorded (`THIRD_PARTY_NOTICES.md`, `licenses/`, `docs/15`)
- [x] PR opened for review — **not merged** (REQ-PR-001)
