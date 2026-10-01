# Dentiva Pro — Risk register, environment findings & open decisions (Phase 1)

## 1. Environment findings (verified 2026-10-01 in the development sandbox)

| Finding | Impact | Decision / mitigation |
|---|---|---|
| Development sandbox is **Debian 12 (headless Linux)**, Python 3.11.2, gcc available, no X server, no `libGL/libEGL/libdbus/libxkbcommon`, no system fonts | Qt GUI cannot normally start | `tools/dev/setup_headless_linux.sh` creates an isolated venv and, **only when the system libraries are missing**, builds throw-away stub shared libraries (`LD_LIBRARY_PATH`) so Qt loads for **offscreen** tests and screenshots. Verified: PySide6 6.11.2 imports and `QApplication` runs. Stubs are dev-only and never shipped. |
| Network is allow-listed: PyPI and github.com reachable; `raw.githubusercontent.com`, `objects.githubusercontent.com`, deb.debian.org, Google blocked | Cannot `apt-get install`, cannot fetch raw release assets | All fonts and test assets are obtained through PyPI wheels or a **sparse git clone** (github.com works). Verified: `git clone --filter=blob:none --sparse` of `google/fonts` fetched Noto Sans + Noto Sans Bengali. |
| Target platform is Windows but the sandbox is Linux | The `.exe`, real printing and the installer cannot be produced here | Windows work (build, print-path, installer, clean-machine) runs on **GitHub Actions `windows-latest`**; the app ships a headless `--selftest` so those validations are automated rather than manual. |
| PySide6 6.11.2, SQLAlchemy 2.1.1, Alembic 1.20, argon2-cffi 25.1, Pillow 12.3, openpyxl 3.1.5, pytest 9.1, pytest-qt 4.5, ruff 0.16, mypy 2.3 all install and import cleanly | — | Pin these (or the Windows-equivalent) in `requirements*.txt`. |
| Spike: Qt **offscreen** + `QTextDocument` → `QPdfWriter` works; custom 58 mm/80 mm page sizes accepted; 80-row A4 table → 3 correctly paginated pages; PDF embeds Noto Sans and Noto Sans Bengali subsets | Document engine risk retired | Proceed with ADR-0004. |
| Spike: Argon2id ≈ 78 ms at m=64 MiB/t=2; SQLite FK enforcement, append-only triggers, online backup and Unicode round-trip all verified | Data/security risk retired | Proceed with ADR-0002/0005/0009. |
| **The agent has no vision capability in this session** — images/screenshots cannot be visually inspected | A purely visual "UI acceptance audit" is impossible for the agent | Visual verification is automated (geometry/overflow/elision/overlap audit, ink-coverage and embedded-font checks on PDFs, text-presence assertions) **and** screenshot bundles are exported for **human** review at every phase. This limitation is stated openly rather than papered over; the user's review is a required gate. |
| PDF text *extraction* of Bengali returns glyph-order artefacts (matras/ligature components have no 1:1 Unicode mapping) | Only affects machine extraction, not rendering/printing | Documented in `docs/08`; machine-readable needs are served by CSV/XLSX export; tests assert **glyph presence and ink**, not extraction fidelity. |
| GitHub Actions permissions API returned 403 for the integration token | Workflow presence could not be queried via API | Workflows are pushed and validated by running them; if Actions are disabled for the repo, the user will be told immediately and the fallback (`dist/` + local artifacts) is used. |

## 2. Risk register

| # | Risk | Likelihood | Impact | Mitigation / owner action |
|---|---|---|---|---|
| R1 | Scope/effort: 18 phases of flagship scope can slip into "demo depth" | High | High | Phase exit gates with objective evidence; traceability matrix audited at every gate; no phase marked complete with outstanding mandatory work. |
| R2 | Windows print behaviour on real thermal printers cannot be tested in this sandbox | Medium | High | Custom-page-size fallback chain + PDF-then-print path; CI print tests against Microsoft Print to PDF/XPS; a physical-printer manual checklist shipped with the release. |
| R3 | PyInstaller missing hidden imports / Qt plugin drift → broken frozen app | Medium | High | Frozen build validated on Windows CI every push; `--version` and `--selftest` smoke tests on the frozen binary; explicit hidden imports and collected data files. |
| R4 | SQLite ALTER limitations during migrations | Medium | Medium | Alembic batch mode; migrations exercised up **and down** in CI; automatic pre-upgrade backup. |
| R5 | Bengali shaping differences between Windows (DirectWrite) and Linux (HarfBuzz) | Low | Medium | Bundled fonts + explicit font-family fallback; Windows CI renders the same fixtures and asserts glyph/ink presence. |
| R6 | Auto-lock destroying unsaved work | Medium | High | Draft autosave + overlay lock (not teardown); explicit test that a form survives lock/unlock with content intact. |
| R7 | Financial drift between cached and computed totals | Medium | High | Single-source finance repository; consistency job; property-based tests; cache recomputed inside the same transaction. |
| R8 | RBAC bypass through a forgotten screen/export | Medium | High | Decorator-coverage test (every service method declares a permission) + financial-isolation matrix. |
| R9 | Backup/restore corruption on interruption | Low | Critical | Atomic `.part`→rename, staged restore, moved-aside live DB, rollback marker, fault-injection tests. |
| R10 | Dependency licence incompatibility | Low | High | Approved-licence list in CI; notices generated from the pinned lock file; review at Phase 15/18. |
| R11 | Performance collapse with large histories | Medium | Medium | Pagination + indexes from day one; 20 k-patient stress fixture in nightly runs; budgets enforced. |
| R12 | Icon/assets quality (cropping, transparency) | Medium | Medium | Generated at multiple sizes, verified programmatically (alpha corners transparent, subject bounding box centred with padding) and reviewed by the user. |
| R13 | GitHub Actions unavailable or minutes exhausted | Low | Medium | Build scripts are local-first (`tools/build/*`) and CI-independent; fallback artifacts committed to `dist/`. |
| R14 | Reverse engineering of the offline activation | Certain (eventually) | Low | Honest threat model (ADR-0006); split constants; optional Cython hardening at Phase 17. |

## 3. Decisions taken in Phase 1 that were *not* explicitly specified (recorded for approval)

1. **Dental numbering**: FDI/ISO 3950 as the stored identity, with Palmer and
   Universal **label toggles** (no data duplication).
2. **Multi-business**: the schema is business-scoped; the v1 UI manages one active
   business, and `business.delete` remains a fully implemented destructive
   operation.
3. **Auto-lock values**: 5/10/15/30 minutes only (no "never"), default 15.
4. **Backup destination**: local/network folders chosen with the native picker; no
   cloud. Backups are unencrypted — stated explicitly in the UI and docs.
5. **Installer**: per-machine by default, per-user fallback when admin rights are
   absent; data in `%LOCALAPPDATA%\DentivaPro`, preserved on uninstall unless
   `/REMOVEDATA=1` with a typed warning.
6. **Activation timing**: the **application** asks for the code on first launch, not
   the installer (keeps the installer simple and lets the clinic activate after
   copying a verified install).
7. **v1 UI language is English only**; document section labels are configurable so a
   clinic can print Bangla headings. All user content is Unicode.
8. **Dark theme is a non-goal** for v1 (recorded, not an oversight).
9. **Attachments** are stored on disk under the data directory with DB metadata;
   preview supported for PDF and common images; other allowed types open with the OS
   handler only after an explicit user action.
10. **No DB-level encryption in v1**; mitigated by profile ACLs and documented
    BitLocker/device-encryption guidance.
11. Packaging: **PyInstaller (GPLv2 + bootloader exception)** primary, cx_Freeze
    fallback, **Nuitka evaluated at Phase 17** as optional hardening.
12. Shipping a **portable zip** as a support convenience is optional; the installer
    is the supported deliverable.

## 4. Open questions for the user (non-blocking; the plan above is the default)
1. Do you want a **dark theme** in v1? (Default: no.)
2. Do you want the installer to **also** ask for the activation code, or keep it in
   the application? (Default: application.)
3. Should the release also publish a **portable zip**, or installer only?
   (Default: installer only.)
4. Do you want **encrypted backups** in v1 (password-derived)? (Default: no —
   documented limitation; can be added as a 1.0.x enhancement.)
