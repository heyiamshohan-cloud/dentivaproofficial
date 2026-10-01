# ADR-0012 — Concurrency: QThreadPool + session-per-task; single writer

- Status: **Accepted** (Phase 1)

## Decision
- UI thread never performs DB I/O, file I/O, backup, restore, PDF rendering, import
  or export. Those run on `QThreadPool` workers (`QRunnable` + signals) or, for
  long/cancellable jobs, a dedicated `QThread` worker with progress + cancellation.
- A **new SQLAlchemy `Session` per task** (sessions are not thread-safe); results
  are converted to immutable DTOs before crossing back to the UI thread.
- Writes are serialised through a single application-level writer lock and executed
  in one transaction per business operation.
- SQLite is configured in WAL mode so a single writer coexists with readers.
- No cross-thread QWidget access; all UI mutation happens on the GUI thread.

## Rejected
- Passing ORM entities across threads (detached-instance bugs, lazy loads off-thread).
- `QSqlTableModel`-style live DB models on the UI thread (unbounded loads).
