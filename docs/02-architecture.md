# Dentiva Pro — Architecture (Phase 1)

## 1. Architectural style

**Layered, service-oriented monolith** for a single Windows workstation / small
clinic LAN, with a strict dependency direction:

```
UI (PySide6 Widgets)  ──▶  Application Services  ──▶  Domain rules  ──▶  Repositories  ──▶  ORM  ──▶  SQLite
        │                          │                                        ▲
        └────────── Documents (Qt) ┘                                        │
                     (own engine, no DB access)                       migrations (Alembic)
```

Rules that are enforced by convention + lint + tests:

1. **The UI never talks to the ORM.** It calls application services with DTOs and
   receives DTOs. (No `QSqlTableModel`, no ORM entities in widgets.)
2. **Every service method declares one required permission.** A decorator
   (`@require("invoice.create")`) resolves the current session, checks the
   permission, writes the audit entry, and wraps the operation in a transaction.
   Permission enforcement is therefore impossible to bypass from another screen,
   a shortcut, an export or a direct call (REQ-RBAC-003/004).
3. **Domain rules are pure Python** (money, invoice totals, stock movement,
   timeline projection, duplicate scoring, appointment state machine, backup
   manifest) — unit-testable with no Qt and no DB.
4. **Documents are rendered from a Qt-free document model**; only the layout engine
   touches Qt (ADR-0004). This keeps print/PDF/preview logic testable and identical
   across output devices.
5. **No module outside `dentiva/security` handles credentials or secrets.**

## 2. Package layout (planned)

```
dentiva/
  __init__.py                 # __version__ = "1.0.0" (single source of truth)
  main.py                     # CLI entry: gui | --selftest | --version | --diagnostics
  app.py                      # QApplication bootstrap, single-instance guard, excepthook
  core/
    paths.py                  # AppPaths: install dir vs per-user data dir (Windows)
    config.py                 # typed settings facade over the Settings table
    clock.py                  # injectable clock (tests freeze time)
    errors.py                 # exception hierarchy -> user message mapping
    money.py                  # Money value object (integer paisa) + parsing/formatting
    result.py                 # Result/Ok/Err for service returns
    logging_setup.py          # rotating structured logs, redaction filter
    textutil.py               # Unicode normalisation, safe filename, truncation
    hashing.py                # sha256 helpers for files/streams
  data/
    engine.py                 # engine factory + PRAGMA wiring + integrity helpers
    session.py                # session scope/unit-of-work, session-per-task
    base.py                   # DeclarativeBase, common columns, TypeDecorators
    models/                   # one module per aggregate (see docs/04)
    repositories/             # query objects (paged, filtered, indexed)
    migrations/               # Alembic env + versions
    seed/                     # default catalogs, role templates, print profiles
  domain/
    permissions.py            # permission catalogue (single source of truth)
    rbac.py                   # role/permission resolution + evaluation
    numbering.py              # patient code, invoice no, receipt no, visit no
    invoice_math.py           # line/total/discount/tax/due calculations
    stock.py                  # stock movement rules
    timeline.py               # timeline projection from source records
    duplicates.py             # patient duplicate scoring
    appointment_state.py      # appointment state machine
    queue_state.py            # queue state machine
    period.py                 # period filters (today/7/30/90/1y/custom/all)
  services/
    bootstrap.py  setup_service.py  auth_service.py  session_service.py
    audit_service.py  clinic_service.py  dentist_service.py  staff_service.py
    user_service.py  role_service.py  patient_service.py  attachment_service.py
    visit_service.py  chart_service.py  treatment_service.py  prescription_service.py
    appointment_service.py  queue_service.py  invoice_service.py  payment_service.py
    inventory_service.py  accounting_service.py  referral_service.py
    notification_service.py  search_service.py  dashboard_service.py
    backup_service.py  restore_service.py  scheduler_service.py
    import_export_service.py  settings_service.py  printing_service.py
    system_health_service.py
  security/
    password.py               # Argon2id hashing + policy
    activation.py             # offline derived verifier (ADR-0006)
    secrets.py                # local secret store (DPAPI on Windows, file fallback)
    session.py                # in-memory session, activity clock, lock policy
  documents/
    model.py                  # DocumentModel / blocks (Qt-free)
    profiles.py               # paper profiles (A4/A5/58/80/mini/custom)
    layout.py                 # DocumentModel -> QTextDocument (the layout engine)
    paginate.py               # pagination + painting onto any QPaintDevice
    templates/                # prescription.py invoice.py receipt.py report.py
    preview.py                # preview widget (zoom, page nav, paper info)
    printer.py                # printer enumeration, selection, output, fallbacks
    pdf.py                    # PDF export helper
  backup/
    archive.py                # .dvbk container, manifest, checksums
    verify.py                 # backup verification
    restore.py                # safe restore + pre-restore backup
  ui/
    theme/                    # tokens.py, qss.py, icons.py, fonts.py
    components/               # buttons, inputs, cards, tables, dialogs, drawers, ...
    shell/                    # MainWindow, Header, Sidebar, NotificationCenter,
                              # LockScreen, LoginDialog, SetupWizard, PrintCenter
    views/                    # dashboard, patients(+profile), appointments, queue,
                              # treatments, prescriptions, invoice, payments,
                              # inventory, accounting, staff, users, backup,
                              # settings, about, audit, system_health
    state.py                  # shared app state/session signal bus
    workers.py                # QThreadPool task runner + progress/cancel
    shortcuts.py              # keyboard shortcut registry
    diagnostics.py            # --selftest implementation
assets/
  icons/dentiva.ico, dentiva.png
  fonts/NotoSans*.ttf + OFL.txt
  images/
tools/dev/                    # headless Linux bootstrap (dev only)
docs/, tests/, packaging/ (pyinstaller spec, inno .iss, version info)
```

## 3. Runtime flows

### 3.1 Boot
1. `--selftest` / `--diagnostics` → headless path (no GUI), else GUI path.
2. Resolve paths (`%LOCALAPPDATA%\DentivaPro` data, install dir read-only).
3. Configure logging (rotating, redacting), install `sys.excepthook` + Qt message
   handler → central error dialog (REQ-ERR-001/002).
4. Open/create the DB, `PRAGMA foreign_keys=ON`, run pending Alembic migrations
   inside a transaction (rollback on failure + clear recovery message).
5. Load bundled fonts, register Bengali substitution, build the theme from tokens.
6. Gate sequence: **activation → first-run setup → login → shell**.
   - Not activated → Activation dialog (offline).
   - Activated but no business → Setup wizard (transactional).
   - Activated + setup done → Login; after login, start session/lock timers.

### 3.2 A business operation (example: record payment)
`PaymentDialog` collects data → `payment_service.record_payment(dto)` →
`@require("payment.create")` (permission + audit) → domain validation
(invoice exists, amount ≤ due, method valid, idempotency key unused) → in one
transaction: insert `payment`, recompute invoice `paid_paisa/status`,
update `financial_summary` cache, create timeline/notification events, write
audit before/after → commit → return DTO → UI updates (queue/dashboard signals).

### 3.3 Printing
`PrintController.open(document_model, profile, printer)` → layout engine →
preview widget (QImage device) → user picks printer/profile →
`QPrinter` (physical) or `QPdfWriter` (PDF) — same pagination code path.

## 4. Threading & responsiveness (ADR-0012)
- `workers.TaskRunner`: `QThreadPool` + `QRunnable` emitting `started/progress/
  finished/error/cancelled` signals; long jobs (backup, restore, import, export,
  PDF batch, integrity scan) use a cancellable `QThread` worker.
- Session-per-task, DTO crossing, single writer lock, WAL.
- Perceived latency targets: screen open ≤ 250 ms, list paging ≤ 150 ms, print
  preview first page ≤ 400 ms, Argon2id login ≤ 400 ms, backup of a 200 MB DB ≤ 60 s.

## 5. Configuration, paths and data locations
| Item | Location (Windows) |
|---|---|
| Executable | `%ProgramFiles%\Dentiva Pro\` (or `%LOCALAPPDATA%\Programs\Dentiva Pro\` for per-user installs) |
| Database | `%LOCALAPPDATA%\DentivaPro\data\dentiva.db` (+ `-wal`, `-shm`) |
| Attachments | `%LOCALAPPDATA%\DentivaPro\data\attachments\<patient_id>\...` |
| Logs | `%LOCALAPPDATA%\DentivaPro\logs\dentiva.log` (rotating, 5 × 5 MB) |
| Backups | user-chosen folder; default `%LOCALAPPDATA%\DentivaPro\backups` |
| Drafts (unsaved work for auto-lock) | `%LOCALAPPDATA%\DentivaPro\drafts\` |
| Config | stored in the DB `settings` table (not a plain-text file) |
| Secret material | `%LOCALAPPDATA%\DentivaPro\security\local.key` (DPAPI-protected) |

Path resolution goes through `core.paths` which validates every user-supplied path
(rejects absolute-path traversal in attachment names, enforces the data root for
stored files).

## 6. Error handling model (REQ-ERR)
`DentivaError` hierarchy: `ValidationError`, `PermissionDenied`, `NotFound`,
`ConflictError` (duplicate/concurrency), `IntegrityError`, `StorageError`
(disk/permission/locked), `PrintError`, `BackupError`, `ActivationError`.
The UI layer maps each to a specific, actionable message and logs the technical
cause with a correlation id; raw tracebacks only in logs/diagnostics export.

## 7. Extensibility boundaries (no dead code)
Only extension points that are actually used in v1 exist: the clinical catalogs
(complaints, examinations, treatment catalog, medicine catalog, payment methods),
paper profiles, document label dictionary, and roles/permissions. There is no
plugin system, no scripting API, no theme marketplace.
