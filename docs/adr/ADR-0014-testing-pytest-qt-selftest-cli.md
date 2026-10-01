# ADR-0014 — Testing: pytest + pytest-qt (offscreen) + headless self-test CLI

- Status: **Accepted** (Phase 1)

## Decision
- **pytest** with markers `unit`, `integration`, `ui`, `print`, `backup`, `security`,
  `stress` (excluded from the default run, executed in a nightly/release job).
- **pytest-qt** (`qtbot`) for widget tests using the `offscreen` Qt platform on
  Linux CI and `minimal`/`offscreen` on Windows CI. Geometry assertions
  (overflow/clipping/elision/alignment) are automated because a human cannot
  reliably eyeball every resolution — see the layout audit helper in `docs/10`.
- Every service/permission/document/money rule is tested **without Qt** (pure
  Python), so the correctness core is verifiable anywhere.
- The shipped application exposes **`DentivaPro.exe --selftest`** — a headless,
  no-GUI diagnostics mode that boots the real service layer, runs the clean-machine
  checklist (DB init/migrate, activation, backup, restore, document → PDF,
  permission enforcement, integrity checks) and prints/returns a report with a
  non-zero exit code on failure. This makes clean-machine validation repeatable in
  CI on a Windows runner and useful for real support cases.
- Coverage gate: ≥ 85 % on `dentiva/services`, `dentiva/domain`, `dentiva/documents`,
  `dentiva/security`, `dentiva/backup`; every screen has an automated smoke test.

## Rejected
- Manual-only QA as the sole gate.
- Snapshot/pixel-diff golden-image testing as a gate (too brittle across DPI/font
  versions); screenshots are generated for **human** review instead.
