# Dentiva Pro — Backup & restore behaviour (Phase 1)

Implements REQ-BKP-*, REQ-BKV-*, with ADR-0008. This document defines exact
behaviour so the implementation and the user guide cannot diverge.

## 1. Backup contents
A backup is one file: **`DentivaPro-YYYYMMDD-HHMMSS.dvbk`** — a ZIP
(`zipfile.ZIP_DEFLATED`) containing:

```
manifest.json        schema_version, app_version, build, business_id, business_name,
                     created_at_utc, created_by, db_integrity, counts{patients,visits,
                     invoices,payments,attachments,...}, entries[{path,sha256,bytes}]
database.sqlite      consistent snapshot via the SQLite online-backup API
attachments/...      stored attachment files (relative, sanitised paths)
assets/...           clinic logo, dentist photos/signatures
signature.sha256     SHA-256 over the canonical manifest + entry digests
```

The archive is self-describing and self-verifying; nothing outside it is needed to
restore.

## 2. Creating a backup (manual)
1. Destination chosen with the **native folder picker**
   (`QFileDialog` non-native-safe mode; no manual path typing — REQ-BKP-001).
2. Free-space pre-check (needs DB size × 2.5 + attachments, min 50 MB headroom);
   refuse early with a clear message instead of failing midway.
3. Write to `<final>.dvbk.part` in the *destination* folder (so a move is atomic on
   the same volume), `flush` + `fsync` each member.
4. Take the DB snapshot with the SQLite **online-backup API** (never a raw file
   copy) — the app stays usable and the snapshot is transactionally consistent.
5. Compute digests, write `manifest.json` and `signature.sha256`.
6. `os.replace(part, final)` → atomic publication. A `.part` file is never listed
   as a valid backup, and stale `.part` files are cleaned up on startup.
7. **Verify**: reopen, verify every digest, parse the manifest, extract the DB to a
   temp dir and run `PRAGMA integrity_check` + `PRAGMA foreign_key_check`.
8. Record `backup_record` (verified flag, size, sha256, app/schema version,
   integrity result) and write an audit entry; on failure, delete the file, record
   the error and raise a notification (REQ-NOT-001 backup success/failure).

## 3. Automatic backup
- Settings → Backup: enable, interval (**7 / 15 / 30 days**, or custom N days),
  destination folder, time of day, retention (keep last N, default 10), and
  "back up on application exit" option.
- Behaviour: on startup (and hourly while running) the scheduler compares
  `now - last_successful_backup` with the interval; when due, it runs the same
  manual pipeline in the background with a progress toast, non-blocking and
  cancellable. If the app was closed on the due date, the backup runs at the next
  start ("due backup" banner). Fully offline — no cloud, no service (REQ-BKP-005).
- Retention prunes older backups in the configured folder **only** if they match
  the Dentiva Pro naming pattern; pruning is audited and never deletes the last
  known-good backup.

## 4. Restore — semantics (REQ-BKP-006)
- **Full restore only**: the selected backup replaces the current database and
  attachments of the business. Backups are never merged — independent full
  snapshots cannot be combined safely, and the UI states this explicitly.
- The file picker accepts a single file. If several files are selected, the newest
  **verified-valid** one is used, and the confirmation dialog names it and explains
  that the others are ignored.
- Restore is a **destructive operation**: `backup.restore` permission +
  administrator re-authentication + typed confirmation (`RESTORE`) + a mandatory
  **pre-restore backup** of the current live state (REQ-BKP-007, REQ-DST-002).

### Restore sequence (all-or-nothing)
1. Validate the archive: ZIP integrity, manifest schema/version compatibility
   (refuse a backup from a newer schema with a clear "update Dentiva Pro" message),
   every entry digest, and DB `integrity_check`/`foreign_key_check` on a temp copy.
2. Create the pre-restore backup (same pipeline, `kind=pre_restore`).
3. Extract to a **staging directory** next to the data dir.
4. Run migrations on the staged copy if its schema is older (documented, audited).
5. Stop all application activity (single-instance write lock, close DB connection).
6. Swap: move the live DB aside (`.pre-restore`), move the staged DB in, swap the
   attachments directory atomically; verify the new DB's integrity.
7. Reopen, verify business/settings sanity, delete the moved-aside DB only after
   success, write the audit entry (`before`/`after` summary) and a notification.
8. On **any** failure: roll back to the moved-aside live DB (untouched by
   construction), remove staging, keep the pre-restore backup, show precisely what
   failed (REQ-BKP-008).

## 5. Recovery scenarios (tested)
| Scenario | Expected behaviour |
|---|---|
| App closed mid-backup | incomplete `.part` remains, is ignored/cleaned; no partial file is listed as valid |
| Power loss mid-restore | live DB is the moved-aside original; on next start the app detects the rollback marker and offers "resume restore" or "keep current data" |
| Corrupted archive / truncated file | verification fails before anything is replaced; live data untouched |
| Missing attachment file inside the archive | restore completes, the affected `patient_attachment` rows are flagged `is_missing`, and the user gets a report listing them |
| Destination folder deleted/unavailable | clear error, offer to choose another folder; no crash (REQ-FFH-001) |
| Insufficient disk space | pre-check refuses; if it still happens mid-write, the operation aborts cleanly and the `.part` file is removed |
| Backup from a newer schema | refused with an "update required" message |
| Backup on a machine with a different Windows user | restore works — backups are self-contained |

## 6. Verification tooling
- **Verify** button in Backup & Restore: re-runs the full verification on any
  existing backup file.
- **Test restore** button: restores into a **temporary workspace** (never touching
  live data), runs integrity checks and reports a summary — satisfies REQ-BKV-003
  and gives clinics a safe way to prove their backups.
- `System Health` shows: last successful backup, its age vs the configured
  interval, last verification result, and data-directory free space.

## 7. Security note (honest)
Backups are not encrypted; they contain the full clinic database. The UI and the
user guide state this and recommend storing backups on protected media /
encrypted volumes. Backups are written only to user-chosen local or network paths
— never to a cloud service (REQ-GEN-005/006).
