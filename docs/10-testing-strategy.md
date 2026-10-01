# Dentiva Pro — Testing strategy (Phase 1)

Objective: every mandatory requirement has at least one automated test that fails
if the requirement regresses, and every risky/manual area has a repeatable
procedure (many of them automated through the shipped `--selftest` mode).

## 1. Test pyramid

| Layer | Tooling | Scope | Gate |
|---|---|---|---|
| **Unit (domain)** | pytest | money math, invoice totals, stock rules, duplicate scoring, state machines, period filters, numbering, document model, manifest/hashing, activation verifier | every push; ≥ 90 % |
| **Unit (services)** | pytest + SQLite (tmp db) | every service method: happy path, validation, permission denial, audit side-effects, transaction rollback | every push; ≥ 85 % |
| **Integration** | pytest + real migrations | Alembic up/down, FK enforcement, audit triggers, financial consistency, search, dashboard aggregates | every push |
| **UI (widget)** | pytest-qt (`offscreen`) | every screen opens; tables paginate; dialogs commit/cancel; keyboard shortcuts; state rendering (loading/empty/error/no-permission) | every push |
| **Layout audit** | custom harness (see `docs/07` §8) | overflow, clipping, overlap, elision, horizontal scrollbars across 5 resolutions × 5 DPI factors | every push (fast subset), nightly (full) |
| **Document/print** | pytest + QPdfWriter + pypdfium2 (dev) | page counts, embedded fonts, ink coverage, long-content pagination, all paper profiles | every push |
| **Print path (Windows)** | pytest on `windows-latest` | print to "Microsoft Print to PDF" / "XPS" via `QPrinter` and verify the produced file | every push |
| **Security** | pytest | permission matrix over every service, financial isolation, RBAC bypass attempts, password/secret redaction in logs, path traversal, attachment validation | every push |
| **Backup/restore** | pytest + fault injection | atomicity, verification, restore, rollback, pre-restore backup, interrupted operations | every push |
| **Stress/perf** | pytest (`-m stress`), nightly/release | 20 k patients, 500-visit patient, 200-item invoice, 5 k attachments, 10 k-row exports, long sessions, lock/unlock loops | nightly + release |
| **Packaging/installer** | GitHub Actions | frozen build boots, `--selftest` passes, silent install/uninstall/reinstall, shortcuts + icon, data preserved | release |
| **Manual acceptance** | scripted checklists + exported screenshots | visual polish, real printer output on physical hardware, Bengali typography review | phase gates |

## 2. Fixtures and data
- `tests/fixtures/clinic.py` builds a realistic Bangladeshi clinic: 2–3 dentists
  (multiple designations/qualifications), 6 staff, 5 users across roles,
  200 patients with Bangla and English names, addresses in Dhaka/Chattogram,
  visits with complaints/findings/chart findings/treatments/prescriptions,
  invoices with partial and later payments, inventory with expiring batches,
  expenses, referrals, attachments.
- `tests/fixtures/long_content.py` generates stress documents (50 medicines,
  200 invoice lines, 4 000-character notes, 60-character Bangla medicine names).
- Deterministic clock (`core.clock`) and a seeded RNG keep tests reproducible.
- Realistic Unicode corpus: Bangla names, addresses, medicines, mixed
  English+Bangla clinical notes, emoji-free but full-width/punctuation variants.

## 3. Naming, traceability and gating
- Every test module references the REQ ids it covers in its docstring;
  `tools/trace_report.py` cross-references `docs/12-requirements-traceability.md`
  with test ids and reports **untested requirements** (fails the build if a
  mandatory requirement has no test at release time).
- Markers: `unit`, `integration`, `ui`, `security`, `print`, `backup`, `stress`,
  `slow`. Default CI run = all except `stress`/`slow`.
- Coverage gates: `dentiva/domain`, `dentiva/services`, `dentiva/security`,
  `dentiva/backup`, `dentiva/documents` ≥ 85 % line coverage; the build fails below.
- Flaky policy: no `sleep`-based synchronisation (`qtbot.waitUntil` / signals only);
  a test that fails once in CI is quarantined with an issue, never silently retried
  forever.

## 4. Windows print-path validation (CI)
On `windows-latest`:
1. enumerate printers, require "Microsoft Print to PDF";
2. render each template (prescription/invoice/receipt/report) to it with a
   temporary output path, confirm the file is created and non-trivial;
3. verify the PDF with pypdfium2 (page count > 0, ink present);
4. repeat for A4, A5, 58 mm and 80 mm profiles, exercising the custom-page-size
   fallback logic and asserting the fallback never silently drops content.

## 5. Clean-machine & installer validation
Automated in CI on a Windows runner (and repeated manually before release):
1. build installer → `DentivaProSetup.exe`;
2. `DentivaProSetup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`;
3. assert install directory, `DentivaPro.exe`, `dentiva.ico`, Start Menu shortcut
   (`.lnk` target + icon), uninstall registry entry;
4. run `DentivaPro.exe --selftest` → must exit 0 (see §7);
5. run `DentivaPro.exe --selftest --with-gui-boot` (boots the Qt shell offscreen,
   opens every screen, then quits);
6. uninstall → assert binaries removed and **clinic data still present**;
7. reinstall → assert the app starts, data is intact, migrations are clean;
8. optional destructive uninstall (`/REMOVEDATA=1`) → assert data removed only when
   explicitly requested.

## 6. Headless UI testing in Linux environments without GUI libraries
Development and Linux CI use `QT_QPA_PLATFORM=offscreen`. Where a minimal container
lacks `libGL/libEGL/libdbus/libxkbcommon`, `tools/dev/setup_headless_linux.sh`
creates an isolated venv and, **only if the system libraries are missing**, builds
throw-away stub shared objects so the Qt modules can be imported for headless
tests. This is a **development/CI convenience only** — the shipped Windows build
uses the real Qt binaries and real Windows printing. (See `docs/16`.)

## 7. `--selftest` (shipped diagnostics mode)
`DentivaPro.exe --selftest [--json out.json]` runs, without any GUI:
1. paths/logging/DB open; 2. pending migrations apply cleanly;
3. integrity: `integrity_check`, `foreign_key_check`, audit-chain verification;
4. financial consistency job (recompute vs stored);
5. activation verifier self-check (accepts the correct code, rejects wrong ones);
6. password hashing round-trip + policy;
7. permission matrix spot-check (restricted user cannot read financials);
8. end-to-end mini workflow on a **temporary** database: setup → dentist → user →
   patient → visit → chart → treatment → prescription → invoice → partial payment →
   later payment → balance check → referral → attachment → inventory → expense →
   search → dashboard;
9. document engine: render every template to PDF at A4/A5/58 mm/80 mm, assert page
   counts, embedded fonts and non-blank ink;
10. backup → verify → restore-into-temp → verify (atomicity + pre-restore backup);
11. print-path probe (enumerates printers; prints to a PDF printer if available).
Exit code 0 only if every step passes; a timestamped report is written to
`%LOCALAPPDATA%\DentivaPro\logs\selftest-*.json` and can be attached to a support
request.

## 8. Regression policy
Every fixed defect gets a test named after the requirement it protects
(`tests/regression/test_issue_<n>_<slug>.py`). Before any release the entire suite
(including `stress`) must pass on both Linux and Windows runners, and
`tools/trace_report.py` must report zero untested mandatory requirements.
