# Dentiva Pro — Phase execution plan (18 phases)

Global rules
- Phases run strictly in order; a phase is finished only when its **exit gate**
  passes and the phase report is delivered.
- The agent never merges a Pull Request; the user merges (REQ-PR-001).
- On **Continue**, the repository is inspected first (`git status`, log, open PRs,
  tests, previous report) and any unfinished work is completed before new work.
- Every phase end state: code committed and pushed to the session branch, docs
  updated (traceability matrix refreshed), a PR opened from Phase 2 onward, and a
  report that states explicitly what was verified and what evidence exists.
- Definition of Done (applies to every phase): no new lint/type errors; no new
  failing tests; no TODO/FIXME tied to unfinished work; no dead code introduced;
  screens touched in the phase pass the layout audit at all breakpoints; traceability
  rows updated; diagrams/docs updated to match reality.

---

### Phase 1 — Discovery, requirements freeze, technical planning *(current)*
**Exit gate:** repository inspected; requirements baseline (REQ-*) written;
architecture, DB design, security/RBAC, UX system, printing, backup, testing,
build/release and CI plans written; ADRs recorded; dependency/licence baseline
recorded; traceability matrix created; executable spike evidence for the risky
decisions (Qt headless, document engine, pagination, Unicode PDF, Argon2id, SQLite
integrity/triggers/backup) captured in ADRs. **No feature code.**

### Phase 2 — Repository, engineering foundation, design system
**Scope:** project skeleton (`src/` layout, `pyproject.toml`, pinned requirements),
ruff/mypy/pytest/pytest-qt config, logging, paths/config, error hierarchy,
`Money`, Alembic wiring, token→QSS design system, icon set, app-shell skeleton,
GitHub Actions baseline, `tools/dev` bootstrap, initial README/docs index.
**Exit gate:** `ruff`, `mypy`, `pytest` green in CI; a styled empty shell boots
offscreen with header + collapsible sidebar + theme applied; one representative
component of each family renders with all states; dependency licences recorded.
**PR opened — not merged.**

### Phase 3 — Database, domain model, security, RBAC
**Scope:** full schema + migrations, repositories, domain rules, services skeleton,
Argon2id auth, session + auto-lock, permission catalogue, roles, `@require`
enforcement, audit foundation + triggers + hash chain, financial permission
enforcement.
**Exit gate:** schema matches `docs/04`; `PRAGMA` integrity/foreign-key checks
clean; permission matrix test passes for every service method; financial isolation
test passes; audit append-only test passes; migrations reversible where claimed.

### Phase 4 — Premium application shell & core UI
**Scope:** MainWindow/header/sidebar/navigation, notification drawer, dialogs,
drawers, toasts, states, keyboard-shortcut framework, search framework, worker
runner, High-DPI handling, animation framework, `ResponsiveGrid`, layout audit
harness.
**Exit gate:** every navigation target opens a real (possibly stub-by-design but
functional) screen; layout audit clean at 5 resolutions × 5 DPRs; shortcut
framework wired; visual QA screenshots exported.

### Phase 5 — Clinic setup, dentists, staff, users, administration
**Scope:** first-run wizard (transactional/recoverable), clinic settings, dentists
with multiple designations/qualifications, staff, users, roles/permissions UI,
Settings (all groups), About.
**Exit gate:** setup interruption/rollback tests pass; multi-dentist + multi-designation
verified; role/permission editing verified and audited; every Settings group
persists and reloads.

### Phase 6 — Patients, profiles, attachments
**Scope:** registration form, list with period filters and ordering, duplicate
detection, patient profile with all tabs, attachments (upload/preview/validation),
patient permissions.
**Exit gate:** realistic patient workflow tests pass; attachments validated
(type/size/corruption/missing file); profile shows correct billed/paid/outstanding
computed from transactions; no permission leak.

### Phase 7 — Visits, timeline, dental chart, treatments
**Scope:** visit editor and register, timeline projection, dental chart widget
(adult/paediatric, FDI + label toggles, historical findings), treatment catalog and
treatment records, clinical catalogs.
**Exit gate:** longitudinal history test (10+ visits) passes; chart history "as of
visit" verified; nothing overwritten; catalog snapshots verified.

### Phase 8 — Appointments & queue
**Scope:** appointment CRUD + states + history + reschedule, queue board with live
updates, integration with visits and patient profile.
**Exit gate:** state machine tests; queue concurrency test; both entry points
verified; notification hooks wired.

### Phase 9 — Prescriptions & clinical document engine
**Scope:** prescription editor (multi-medicine, schedules, PRN, free text),
document model + layout engine + pagination, paper profiles, print preview, PDF,
printer selection, signature area, Print Center.
**Exit gate:** long-content and 50-medicine documents paginate cleanly; Bengali and
mixed content verified in preview, PDF and CI print-path; all paper profiles render
without clipping.

### Phase 10 — Invoice, payments, financial controls
**Scope:** treatment→invoice billing, invoice editor, partial/later payments,
payment methods incl. MFS, financial history, outstanding balances, financial
permissions, accounting foundation, invoice printing/PDF.
**Exit gate:** financial math property tests; idempotency; unauthorised access
rejected on every path; invoice prints on all profiles.

### Phase 11 — Inventory & accounting
**Scope:** items, categories, suppliers, purchases, batches, movements, expiry and
low-stock alerts, income/expense, reports, audit, accounting integration.
**Exit gate:** stock integrity property tests (movements always reconcile); alert
queries correct; reports match recomputed totals; permissions enforced.

### Phase 12 — Search, notifications, dashboard, operational intelligence
**Scope:** global search with permission filtering, notification centre and
generators, dashboard widgets with the deliberate grid, quick actions, performance
tuning.
**Exit gate:** dashboard totals independently recomputed and matching; search
permission tests; performance budgets met with the 20 k-patient fixture.

### Phase 13 — Backup, restore, import/export, data integrity
**Scope:** manual + scheduled backup, verification, restore with pre-restore
backup and rollback, import/export with validation, corruption protection, recovery
scenarios.
**Exit gate:** fault-injection suite (interrupt/corrupt/no space) passes; a real
backup→restore round trip verified in CI; exports respect permissions.

### Phase 14 — Printing/PDF/printer-profile finalisation
**Scope:** harden all templates and profiles, multi-page, signature areas, receipts,
reports, High-DPI preview, fallback paths, Print Center polish.
**Exit gate:** print audit on Windows CI (A4/A5/58/80/custom, PDF printer); preview
parity checks; Bengali ink/font assertions; long-document suite green.

### Phase 15 — Security, audit, performance, UX hardening
**Scope:** full security review, RBAC bypass testing, activation review, audit
review, performance optimisation, memory/resource review, UX/accessibility pass,
error-state pass.
**Exit gate:** security test matrix green; no secrets in logs/binaries (scan);
performance budgets met; accessibility checklist complete.

### Phase 16 — Full QA, stress testing, regression
**Scope:** entire suite incl. stress, installer and clean-machine tests; fix every
release-blocking defect; retest.
**Exit gate:** zero failing tests; zero open release-blocking defects; stress report
within budgets; repeated-run stability evidence.

### Phase 17 — Installer & release candidate
**Scope:** RC build, installer/uninstaller validation, clean-machine validation,
activation, first-run setup, full workflow pass on the RC, shortcut/icon validation.
**Exit gate:** RC audit passes every gate in `docs/11` §6; artifact integrity
verified (checksums); RC is installable and usable on a clean runner.

### Phase 18 — Final audit, GitHub Actions, production release
**Scope:** requirement-by-requirement audit against this matrix (every row at
**V**), CI validation, final `.exe`, artifact verification, GitHub Release (or
`dist/` fallback), final release report.
**Exit gate:** no unverified mandatory requirement; all workflows green; release
published or fallback committed; final report delivered. **No PR merged by the
agent.**
