# Dentiva Pro — Technology decisions & evaluation (Phase 1)

Requirement: *"Evaluate them against offline operation, Windows compatibility,
commercial redistribution, performance, maintainability, security, printing,
Unicode, High-DPI support, and long-term reliability. Record and justify the final
technology decisions before implementation."*

Each decision below is also recorded as an ADR in `docs/adr/`. Scoring: ✅ excellent,
◐ acceptable with mitigation, ✗ disqualifying.

## 1. Language & runtime
| Candidate | Verdict |
|---|---|
| **Python 3.11 (CPython, x64)** | **Chosen.** Mature ecosystem for Qt (`PySide6`), packaging, Windows; matches the development sandbox; PyInstaller/PySide6 wheels are first-class. Long-term support is adequate; ADR-0007 keeps the frozen interpreter inside the installer, so the clinic never installs Python. |
| Python 3.12/3.13 | Not chosen for v1: 3.11 gives the widest wheel/tooling compatibility today; the code stays 3.11-compatible and forward-compatible checks run in CI. |
| C#/.NET (WPF) | Rejected: the request is for a Python desktop stack; WPF would also change the whole dependency/licence profile. |
| Electron/TypeScript | Rejected: browser runtime, larger attack surface, printing/PDF parity issues, offline packaging bloat. |

## 2. UI framework — see ADR-0001
**PySide6 (Qt 6, LGPLv3) Widgets.**

| Criterion | Assessment |
|---|---|
| Offline | ✅ self-contained, no network stack used |
| Windows | ✅ native feel, per-monitor DPI, native print dialogs, taskbar/shortcut integration |
| Commercial redistribution | ✅ LGPLv3 with notices + written offer; unmodified shared libs |
| Performance | ✅ native C++ core; virtualisable item views |
| Maintainability | ✅ QSS + tokens, huge ecosystem |
| Security | ✅ no script/HTML surface in the UI path |
| Printing | ✅ `QPrinter`/`QPrintDialog`/`QPdfWriter` (the decisive criterion) |
| Unicode | ✅ DirectWrite/HarfBuzz shaping, font fallback and substitution |
| High-DPI | ✅ `Qt::HighDpiScaleFactorRoundingPolicy::PassThrough`, vector SVG icons |
| Long-term reliability | ✅ Qt is a 30-year, commercially backed toolkit |

Rejected: PyQt6 (GPL/paid), Qt Quick/QML (printing limitations), tkinter (visual
bar + no print engine), wxPython (weaker print/theme story), Flet/CEF/webview
(browser bundling, licences, printing), Kivy (non-native).

## 3. Database & data access — see ADR-0002
**SQLite (WAL) + SQLAlchemy 2.0 ORM + Alembic migrations.** All offline, all
MIT-licensed. Rejected: client-server engines (server admin in a clinic), raw SQL
(higher defect risk), SQLCipher (licence/packaging risk; OS ACL + FDE guidance
instead), hand-rolled migrations (less auditable than Alembic).

## 4. Money — see ADR-0003
**Integer minor units (paisa)** + `Decimal` at the boundaries, `ROUND_HALF_UP`
quantised once per line and once per document.

## 5. Document / printing engine — see ADR-0004
**Document Model → QTextDocument → QPrinter | QPdfWriter | QImage.**
Phase-1 spike evidence (recorded above): A4/A5/58 mm/80 mm custom page sizes
accepted, correct pagination (80-row table → 3 A4 pages), Unicode text preserved,
PDF embeds Bengali + Latin font subsets at 300 dpi.

## 6. Password hashing — see ADR-0005
**Argon2id (`argon2-cffi`, MIT)**, unique salts, PHC strings, constant-time verify,
`needs_rehash` upgrade path. Spike: 78 ms at m=64 MiB, t=2 → interactive login is
comfortable; final parameters tuned in Phase 3.

## 7. Activation — see ADR-0006
Offline derived verifier, split/obfuscated constants, HMAC activation record,
optional Cython hardening at release. Honest threat model published.

## 8. Fonts — see ADR-0011
Bundle **Noto Sans** + **Noto Sans Bengali** (SIL OFL 1.1, unmodified, notices
shipped), static instances generated with `fonttools` (MIT). Windows UI font stays
Segoe UI; Bengali wired as a substitution so no system font is assumed.

## 9. Icons — see ADR-0013
In-house 24×24 SVG icon set rendered via `QSvgRenderer` (crisp at any DPI,
recolourable, zero third-party licence surface).

## 10. Packaging & installer — see ADR-0007
**PyInstaller 6.x** (GPLv2 **with** the bootloader exception that permits
distribution inside commercial products; unmodified bootloader; notices shipped) +
**Inno Setup 6** (free for commercial use). Alternatives: cx_Freeze (PSF) as
fallback; **Nuitka (Apache-2.0)** evaluated at Phase 17 as an optional hardening
step for tamper resistance. Rejected: py2exe, MSI/WiX, MSIX, NSIS (for this scope).

## 11. Backup format — see ADR-0008
`.dvbk` ZIP container + SQLite online-backup snapshot + manifest + SHA-256 +
atomic rename + verification. Rejected: raw file copy, JSON dumps, cloud targets.

## 12. Audit — see ADR-0009
Append-only table enforced by SQLite triggers (spike-verified) plus a SHA-256 hash
chain; `System Health` verifies chain continuity.

## 13. Dental chart — see ADR-0010
Interactive painted QWidget; **FDI/ISO 3950** two-digit identity with Palmer and
Universal *label* options; per-visit historical findings.

## 14. Concurrency — see ADR-0012
`QThreadPool` + session-per-task + single writer lock + DTOs across threads.

## 15. Testing & verification — see ADR-0014
pytest + pytest-qt (offscreen), pure-Python domain tests, and a shipped
`--selftest` headless diagnostics mode for clean-machine/CI validation.

## 16. CI/CD — see ADR-0015
GitHub Actions: Linux (lint/type/unit+integration/UI-offscreen) and Windows
(unit/print-path/build/installer/`--selftest`); release job publishes a GitHub
Release with the installer, falling back to `dist/` in the repository.

## 17. Supporting library decisions
| Need | Choice | Why | Rejected |
|---|---|---|---|
| Images (logo, thumbnails, ICO build) | **Pillow** (HPND) | mature, builds the multi-resolution `.ico`, EXIF-aware orientation | OpenCV (huge), raw Qt (cannot build multi-size ICO) |
| Font subsetting/instancing (build-time) | **fonttools** (MIT, dev-only) | generate static instances from upstream variable fonts | shipping 2 MB variable fonts |
| Argon2id | **argon2-cffi** (MIT) | reference-quality, PHC strings | passlib-only (extra layer) |
| ORM/migrations | SQLAlchemy + Alembic (MIT) | standard | — |
| XLSX export | **openpyxl** (MIT) | pure Python, offline | xlsxwriter (fine but less flexible), pandas (heavy) |
| Date/time | **stdlib `datetime`** + explicit tz policy | no dependency, deterministic | dateutil/arrow/pendulum (avoidable weight) |
| Logging | **stdlib logging** + `RotatingFileHandler` | no dependency, configurable | loguru (extra dep), structlog (python 3.12+/extra dep) |
| ZIP/CSV/JSON/UUID/secrets | **stdlib** | zero-dependency core | — |
| Lint/format | **ruff** (MIT) | one fast tool for lint+format | flake8+black+isort stack |
| Type checking | **mypy** (MIT) | catches API drift in a 100 kLOC-scale codebase | pyright (node-based; fine but mypy integrates better here) |
| Dead-code review | **vulture** (MIT) + ruff rules | supports the "no dead code / no dead buttons" requirement | manual review only |
| Coverage | **pytest-cov** (MIT) | gate coverage on critical packages | — |
| PDF verification (dev/test only) | **pypdfium2** (BSD-3) | rasterise/parse generated PDFs in tests to assert page counts, embedded fonts and ink coverage | human-only PDF review |

## 18. Deliberate non-goals (recorded so they are decisions, not gaps)
Dark theme, multi-language UI, cloud sync, mobile client, web portal, SMS/email
gateways, online booking, imaging device integration, insurance claims, payroll,
multi-clinic tenancy UI, DB-level encryption, plugin system, telemetry.

## 19. Licence compatibility summary (production dependencies)
| Dependency | Licence | Redistribution in a commercial closed-source product |
|---|---|---|
| PySide6 (+ Qt 6 shared libs) | LGPLv3 | ✅ with notices + written offer for Qt sources, dynamic linking, unmodified libs |
| SQLAlchemy | MIT | ✅ notice |
| Alembic | MIT | ✅ notice |
| argon2-cffi (+ bindings) | MIT | ✅ notice |
| Pillow | HPND | ✅ notice |
| openpyxl | MIT | ✅ notice |
| Noto Sans / Noto Sans Bengali | SIL OFL 1.1 | ✅ ship OFL text + copyright; no standalone sale; unmodified |
| PyInstaller *bootloader* (build-time, shipped) | GPLv2 + exception | ✅ exception permits distribution with the product; ship GPL text + exception notice |
| Inno Setup (build tool, not shipped) | Inno Setup licence (BSD/zlib-style) | ✅ free for commercial use |

Full matrix with versions and purposes: `docs/15-dependency-license-baseline.md`.
