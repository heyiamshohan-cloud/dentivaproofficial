# Dentiva Pro — Security model (Phase 1)

Scope: a local, offline, single-workstation/small-LAN commercial application holding
clinical and financial data. The model below is designed to be honest about what a
local application can and cannot guarantee.

## 1. Assets and trust boundaries
| Asset | Protection |
|---|---|
| Password hashes | Argon2id, unique salt, PHC string, never logged |
| Clinic/patient clinical data | Filesystem ACL in the user profile; no network egress; optional OS full-disk encryption (documented requirement) |
| Financial data | RBAC at the service layer; export restricted; audit |
| Activation secret | Derived + split representation, never the literal code (ADR-0006) |
| Local key material (settings encryption, activation token) | `%LOCALAPPDATA%\DentivaPro\security\local.key`, DPAPI-protected on Windows (`CryptProtectData` via `ctypes`), ACL restricted to the current user; file-permission fallback elsewhere with a logged warning |
| Backups | User-chosen folder; containers are plain ZIP (documented: protect the folder; DB encryption is out of scope for v1) |
| Attachments | Stored outside the executable; validated types; opened only via explicit user action |

Threat model summary (documented for users as well):
- **In scope to defend**: casual/local unauthorised use of the app (login, lock,
  RBAC), accidental data loss (backup/restore/transactions), privilege abuse by
  clinic staff (permissions + audit), tampering with the audit trail, casual
  extraction of the activation code.
- **Explicitly not defensible offline**: an attacker with administrative control of
  the Windows machine and reverse-engineering tooling can read any local data and
  can ultimately bypass a purely local activation check. This is stated plainly in
  the product documentation rather than overclaimed (REQ-ACT-005).

## 2. Authentication
- Passwords: **Argon2id** (`argon2-cffi`), parameters stored with the hash;
  `time_cost=3, memory_cost=64 MiB, parallelism=2` (tuned in Phase 3 to keep login
  < 400 ms). Silent rehash on login when parameters change.
- Password policy (Settings → Security, configurable): minimum 10 characters, at
  least 3 of 4 character classes, not equal to the username, not in a small local
  common-password list, no reuse of the last 3 hashes, forced change on first login
  for admin-created accounts, optional expiry (default off).
- Login throttling: 5 failed attempts → 1-minute lockout, doubling to a 15-minute
  cap; the counter and lock are per user and audited; verification work is
  identical for unknown users (dummy hash) to avoid user enumeration.
- Logout: clears the in-memory session, cancels timers, writes an audit entry,
  returns to the login screen.

## 3. Session, auto-lock and re-authentication
- Session object holds `user_id`, `username`, `roles`, resolved permission set,
  `session_id`, `last_activity_at`, timeout preference. Not persisted to disk.
- Auto-lock after **5 / 10 / 15 / 30 minutes** of inactivity (configurable; default
  15). The timer is driven by an application-level activity monitor (input events),
  not by widget-level timers, so it is consistent everywhere.
- **Auto-lock never destroys work** (REQ-AUTH-004):
  1. Open editors autosave a draft (JSON) to `%LOCALAPPDATA%\DentivaPro\drafts`
     every 20 s and immediately on lock;
  2. The lock screen is an overlay — main-window state (opened patient, tab, scroll
     position) is preserved;
  3. On unlock, drafts are offered back ("Restore unsaved changes?");
  4. Drafts are cleared on successful save and encrypted-at-rest is unnecessary
     because they live in the protected user profile (documented).
- Unlock requires the logged-in user's password (Argon2id verify). Failed unlock
  attempts are throttled and audited.
- **Re-authentication** is required for: destructive operations (delete patient,
  delete business, reset application, hard delete), restore, role/permission
  changes, user password resets, changing security settings, disabling audit, and
  any permission marked `sensitive`.

## 4. Authorisation (RBAC)
- 40+ granular permissions in `domain/permissions.py` (single source of truth),
  seeded into the `permission` table; full catalogue in `docs/06`.
- Roles are **data**: seeded templates (Administrator, Dentist, Receptionist,
  Dental Assistant, Accountant, Inventory Manager, Read-only) plus fully custom
  roles. Permissions = union over the user's roles.
- Enforcement: `@require("code")` on **every** service method that touches
  protected data; the decorator raises `PermissionDenied` (mapped to a
  no-permission UI state) and writes a security audit entry. Services are the only
  path to data, so no screen, shortcut, export, report, search or scripted call can
  bypass it (REQ-RBAC-003/004).
- Financial permissions are additionally tagged `is_financial`; the test suite
  includes a matrix that asserts every financial service rejects users without the
  tag, and that search/export/dashboard/report paths respect it.

## 5. Audit
- Append-only `audit_log` with SQLite triggers blocking UPDATE/DELETE
  (spike-verified in Phase 1) plus a SHA-256 hash chain (`prev_hash`/`row_hash`).
- `System Health → Audit integrity` verifies the chain and reports the first broken
  link with its id and timestamp.
- Redaction filter: keys matching `password`, `hash`, `token`, `secret`, `key`,
  `activation` are replaced with `«redacted»` before persistence; clinical free text
  is summarised (length + hash) rather than duplicated wholesale where practical.
- Audited actions per REQ-AUD-001 (full list in `domain/audit_actions.py`).

## 6. Activation (offline)
Per ADR-0006: derived verifier (Argon2id of the entered code with an application
salt assembled at runtime from split fragments) compared with `hmac.compare_digest`
against a stored digest that is itself split across modules; on success an
activation record (HMAC over machine id) is written to the data directory **and**
the database, and startup requires both to agree. No network call is ever made.
Re-activation with the code is always possible; no hardware lock-in.

## 7. Application hardening
- No `eval`/`exec` of user data; no `pickle` deserialisation of any file that a
  user can influence; JSON only.
- All SQL through SQLAlchemy (parameterised); no string-built SQL.
- Path safety: every user-supplied filename is sanitised
  (`core.textutil.safe_filename`), joined against the data root and verified with
  `os.path.commonpath` to prevent traversal; extraction of backup archives rejects
  `..`, absolute paths, symlink entries and zip-slip patterns.
- Attachment validation: allow-list of extensions
  (`.pdf .png .jpg .jpeg .webp .bmp .tif .tiff .doc .docx .xls .xlsx .txt .csv .dcm`
  is trimmed to what we can safely preview/handle), MIME sniffing against the
  declared extension, size cap (default 25 MB, configurable), virus-free cannot be
  guaranteed — files are never executed and are opened only with an explicit user
  action via the OS handler.
- Secrets: nothing sensitive in logs (redaction filter + explicit unit test that
  feeds a password through the stack and greps the log output); no credentials in
  source; the local key file is DPAPI-protected and ACL-restricted.
- Updates: no auto-update (offline product); a release is delivered by the
  installer, so no unsigned code download path exists.
- Single-instance guard prevents two processes fighting over the SQLite file.

## 8. Data-at-rest and backup security (honest position)
- SQLite is not encrypted in v1. Mitigations: per-user data directory with
  restricted ACLs, documentation recommending BitLocker/device encryption, and a
  "backups contain unencrypted clinic data — store them on protected media" warning
  shown in the Backup & Restore screen and in the user guide.
- Encrypted backups are a possible future addition; deliberately **not** claimed as
  a v1 feature.

## 9. Secure development practices tied to CI
`ruff` (lint + format), `mypy`, dependency pinning with hashes for build inputs,
a CI step that fails on TODO/FIXME markers tied to unfinished functionality, a CI
step that fails if `bandit`-style dangerous patterns are introduced (eval/exec/
pickle/shell=True), a secret-scanning grep over the repository, and the licence
manifest check (no dependency whose licence is not on the approved list).
