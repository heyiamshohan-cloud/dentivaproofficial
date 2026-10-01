# ADR-0008 — Backup format: ZIP container + SQLite online backup + manifest

- Status: **Accepted** (Phase 1)

## Decision
A backup is a single `DentivaPro-YYYYMMDD-HHMMSS.dvbk` file (ZIP, stdlib
`zipfile`, deflate) containing:
```
manifest.json      # schema_version, app_version, business_id, created_at,
                   #   source_db_integrity, entry list with sha256 + size + count
database.sqlite    # produced with the SQLite online-backup API (consistent snapshot)
attachments/...    # stored attachment files (relative paths, sanitised)
assets/logo.*      # clinic logo and other configured assets
signature.sha256   # canonical digest over manifest + entries
```
- **Atomicity**: write to `<name>.dvbk.part` in the destination folder, fsync, then
  `os.replace()` to the final name. A `.part` file is never presented as a backup.
- **Verification**: after writing, reopen the archive, verify every SHA-256, verify
  `manifest.json` parses, and run `PRAGMA integrity_check` + `PRAGMA
  quick_check` on the extracted DB copy in a temp directory; record the result in
  the `BackupRecord` table and in the audit log.
- **Restore**: validate → auto-create a **pre-restore backup** of the live state →
  restore into a staging directory → integrity-check → atomically swap the live DB
  (and attachments) → record audit entries. Any failure leaves the live state
  untouched and reports precisely why.
- **Multi-selection**: full restore is a single-backup, replace-database operation.
  If several files are selected, the newest **valid** file is used and the UI states
  exactly that; backups are never merged (merging independent full backups cannot be
  done safely — documented in the UI and `docs/09`).

## Rejected
- Plain copy of the live `.db` file (not safe while the app holds a connection).
- JSON/SQL-dump backups (slow, lossy, harder to verify).
- Cloud targets (forbidden).
