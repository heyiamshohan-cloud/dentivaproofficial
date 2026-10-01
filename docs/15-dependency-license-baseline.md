# Dentiva Pro — Dependency & licence baseline (Phase 1)

Policy (REQ-LIC-001..003): every production dependency must be (a) needed for a
concrete requirement, (b) usable **offline**, (c) redistributable in a **commercial
closed-source** product, (d) pinned to an exact version in the build, and (e)
accompanied by its licence notice in `THIRD_PARTY_NOTICES.md`. Anything that fails
(a)–(d) is rejected. CI enforces the approved-licence list.

## 1. Approved licence list
MIT · BSD-2/3 · Apache-2.0 · PSF-2.0 · ISC · HPND (PIL) · MPL-2.0 (file-level copyleft only) ·
SIL OFL 1.1 (fonts) · LGPLv3 (Qt/PySide6 shared libraries, with notices + relinking offer) ·
GPLv2 **with** the PyInstaller bootloader exception (build-time component only) ·
zlib/libpng · CC0 (assets only).

## 2. Production dependencies

| Package | Version (planned pin) | Licence | Purpose | Offline | Commercial redistribution |
|---|---|---|---|---|---|
| **PySide6** (Essentials) | 6.11.x (Qt 6.11) | LGPLv3 (+ Qt third-party notices) | UI, printing, PDF, SVG, SQL | Yes | Yes — ship LGPL text, Qt copyright, written offer for Qt sources; use unmodified shared libraries; no static linking |
| **shiboken6** | matching PySide6 | LGPLv3 | PySide6 binding runtime | Yes | As above |
| **SQLAlchemy** | 2.1.x | MIT | ORM, sessions, queries | Yes | Yes (notice) |
| **Alembic** | 1.20.x | MIT | Schema migrations | Yes | Yes (notice) |
| **argon2-cffi** (+ bindings) | 25.1.x | MIT | Argon2id password hashing | Yes | Yes (notice) |
| **Pillow** | 12.3.x | HPND | Logo/photo handling, thumbnails, `.ico` generation | Yes | Yes (notice) |
| **openpyxl** | 3.1.x | MIT | XLSX export/import | Yes | Yes (notice) |
| **Noto Sans** / **Noto Sans Bengali** (static instances) | upstream stable | SIL OFL 1.1 | Guaranteed Unicode/Bangla rendering + PDF embedding | Yes | Yes — ship OFL text + copyright; unmodified; not sold standalone |
| **PyInstaller bootloader** (embedded by the build) | 6.x | GPLv2 **with** the bootloader exception | Frozen executable bootstrap | Yes | Yes under the exception — ship GPL text + exception notice; bootloader unmodified |

Python standard library (zipfile, sqlite3, hashlib, hmac, secrets, logging, csv,
json, datetime, ctypes, pathlib, threading) is used for everything else — no
unnecessary dependencies.

## 3. Build / development / test dependencies (not shipped)

| Package | Licence | Purpose |
|---|---|---|
| ruff | MIT | lint + format |
| mypy | MIT | static typing |
| pytest, pytest-qt, pytest-cov | MIT | test suite, Qt widget tests, coverage |
| pypdfium2 | BSD-3-Clause | **test-only** PDF verification (page counts, embedded fonts, ink coverage) |
| fonttools | MIT | **build-time** static font instances from upstream variable fonts |
| vulture | MIT | dead-code detection (supports the "no dead code" requirement) |
| pip-audit / licence checker | Apache-2.0 | dependency vulnerability + licence verification in CI |
| Inno Setup 6 | Inno Setup licence (BSD/zlib-style; free for commercial use) | Installer compiler (CI only) |

## 4. Explicitly rejected dependencies
| Rejected | Reason |
|---|---|
| PyQt6 | GPLv3 or paid commercial licence |
| Any cloud SDK (boto3, firebase, requests-based telemetry) | Violates offline/no-egress requirements |
| SQLCipher / pysqlcipher3 | Licensing and packaging risk for the encryption benefit at v1 scope |
| QtWebEngine / Chromium bundles | ~150 MB, extra notices, unsupported Windows printing path |
| WeasyPrint / wkhtmltopdf | External binaries, system deps, divergent layout from the preview |
| pandas | Heavy dependency for work that stdlib + SQLAlchemy already do |
| dateutil / arrow / pendulum | Avoidable weight; stdlib `datetime` + explicit tz policy is used |
| keyring | Pulls platform secret services with unpredictable behaviour; DPAPI via `ctypes` is used instead |
| Any icon font (Font Awesome, Material Icons) | Extra licence/attribution surface; alignment issues next to Bengali text; in-house SVG set used instead |
| Nuitka (as a *required* tool) | Optional hardening only (Apache-2.0); evaluated at Phase 17 |

## 5. Verification steps executed / planned
- Phase 1: licences checked against upstream project pages; redistribution terms
  recorded in this file.
- Phase 2+: `requirements*.txt` pinned; CI job `licence` generates
  `THIRD_PARTY_NOTICES.md` from the installed set and fails on any licence outside
  the approved list.
- Phase 15/18: full re-audit, including the Qt third-party notices file shipped with
  PySide6, the Pillow/HPND notice, the OFL notices for the fonts, and the PyInstaller
  GPL + exception notice.

## 6. Notice delivery
`THIRD_PARTY_NOTICES.md` is shipped in the installer, installed next to the
executable, and reachable from **About → Licences**. The fonts directory additionally
ships `OFL.txt`.
