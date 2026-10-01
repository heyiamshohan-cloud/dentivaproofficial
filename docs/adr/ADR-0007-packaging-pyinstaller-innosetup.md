# ADR-0007 — Packaging & installer: PyInstaller + Inno Setup (Nuitka evaluated)

- Status: **Accepted** (Phase 1)

## Options considered
| Option | Licence | Verdict |
|---|---|---|
| **PyInstaller 6.x** | GPLv2 **with an explicit exception** permitting distribution of the bootloader inside commercial products | **Chosen (primary)** — best-tested PySide6 hooks, deterministic onedir build, wide commercial use. |
| cx_Freeze | PSF-2.0 (MIT-like) | Fallback if PyInstaller proves unstable; no GPL exception analysis needed. |
| Nuitka | Apache-2.0 | **Optional hardening** (compiles to machine code → real resistance to `.pyc` decompilation, aligns with ADR-0006). Evaluate in Phase 17; adopt only if the Windows CI build is reproducible and faster/smaller or equal. |
| py2exe | MIT-ish | Weaker Qt 6 support; rejected. |

## Installer
**Inno Setup 6** — free for commercial use (BSD/zlib-style licence), mature,
produces a single `DentivaProSetup.exe`, supports per-machine install under
`%ProgramFiles%`, Start Menu + desktop shortcuts with the multi-resolution icon,
silent/unattended modes for CI, custom pages (activation), and a correct
uninstaller. Rejected: NSIS (weaker built-in UI/scripting for this scope), MSI
(needs WiX/MSI authoring effort with no benefit for a single-product installer),
MSIX (packaging constraints, store orientation).

## Decisions
- Install: per-machine binaries in `%ProgramFiles%\Dentiva Pro` (no admin rights
  required option in `%LOCALAPPDATA%\Programs\Dentiva Pro` for locked-down clinics).
- Data (DB, attachments, logs, backups default target): per-user
  `%LOCALAPPDATA%\DentivaPro` — never deleted by uninstall unless explicitly
  requested with a typed confirmation.
- Uninstall removes binaries, shortcuts and registry entries; it does **not** delete
  clinic data by default.
- Reinstall/upgrade preserves data and runs migrations on first launch after update.
