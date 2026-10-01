# Dentiva Pro

**Offline-first, production-grade Windows desktop dental clinic management software for Bangladesh.**
English interface · Unicode/Bangla clinical content · BDT (৳) currency · no cloud dependency.

Created by **Shohan Khan** · <helloiamshohan@gmail.com>

---

## Current status

**Phase 2 — Repository, engineering foundation and design system: complete.**
The repository now contains a real, runnable (if feature-empty) application: a
styled shell that boots with the design system applied, a collapsible sidebar
over the full navigation model, a database that migrates and verifies itself on
start-up, money and logging primitives, a token-driven theme with an in-house
icon set, and a 138-test suite gated by lint, type, dead-code and layout audits
on Linux **and** Windows CI.

What is *not* built yet: clinical and business features. Those arrive in
Phases 3–16 (see [`docs/13-phase-plan.md`](docs/13-phase-plan.md)); every
navigation item that is not yet implemented shows an explicit
"Scheduled for Phase N" state instead of pretending to work
([`docs/17-phase-02-report.md`](docs/17-phase-02-report.md) lists each one).

## Quick start

```bash
# Windows / macOS / Linux with a display
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .
python -m dentiva.main                            # launch the shell
python -m dentiva.main --selftest                 # headless health check
python -m dentiva.main --audit-layout             # layout audit at 5 resolutions
python -m dentiva.main --audit-layout --scale 2.0 # …at 200 % Windows scaling
pytest -q
```

Headless Linux (CI/containers) — the bootstrap script installs the pinned
dependencies and makes Qt importable without an X server:

```bash
./tools/dev/setup_headless_linux.sh
source /tmp/dentiva-venv/bin/activate
export QT_QPA_PLATFORM=offscreen
pytest -q
```

## Repository layout

```
src/dentiva/
  core/         Qt-free, DB-free primitives: money (integer paisa), paths,
                logging, errors, clock, text/Unicode helpers, hashing, atomic
                file IO, paging
  data/         SQLAlchemy base + type decorators, engine (PRAGMA policy,
                integrity checks, online backup), sessions, packaged Alembic
                migrations
  ui/
    theme/      design tokens → generated QSS, in-house SVG icon engine,
                bundled fonts, High-DPI policy
    components/ buttons, inputs, display, feedback, cards, layout
                (ResponsiveGrid), tables, tabs, states, dialogs
    shell/      navigation registry, sidebar, header, main window
    views/      screens (About; the rest arrive with their phases)
    diagnostics layout audit harness
  app.py        bootstrap: logging → database → theme → single instance → shell
  diagnostics.py headless self-test + diagnostics bundle
  main.py       CLI (--selftest, --diagnostics, --build-info, --audit-layout)
assets/         fonts (bundled Noto Sans + Noto Sans Bengali), icon masters
docs/           01…17 — requirements, architecture, ADRs, phase reports
licenses/       verbatim third-party licence texts
tests/          unit / integration / ui suites (pytest + pytest-qt, offscreen)
tools/dev/      headless Linux bootstrap
.github/        CI: ruff, mypy, pytest (Linux + Windows), vulture, hygiene
```

## Engineering rules (enforced, not aspirational)

- **Money** is integer paisa end to end; floats are rejected at the type level
  (`core/money.py`).
- **Offline**: no module under `src/` may import a networking module —
  `tests/unit/test_no_network_imports.py` fails the build if one ever does.
  Qt's network module is allowed only for local IPC (`QLocalServer`).
- **One design source**: every colour, radius, spacing and font size comes from
  `ui/theme/tokens.py`; the stylesheet is generated from those tokens.
- **Layout audits**: `ui/diagnostics.py` walks every screen and fails on
  overflow, clipped labels, unintended horizontal scrolling, overlapping
  siblings and screens that cannot fit 1024×640. The suite runs it at
  1366×768, 1600×900, 1920×1080, 2560×1440 and 3840×2160, and at
  100/125/150/175/200 % scaling.
- **No dead code, no TODOs, no fake buttons** — vulture and a CI grep gate.
- **Quality gates**: `ruff check`, `ruff format --check`, `mypy`, `pytest -q`,
  `vulture` and `--selftest` all pass on Linux and Windows runners.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/00-index.md`](docs/00-index.md) | Documentation index and reading order |
| `docs/01`…`docs/11` | Requirements, architecture, DB model, security/RBAC, UX system, printing, backup, testing, build/release |
| [`docs/12-requirements-traceability.md`](docs/12-requirements-traceability.md) | REQ → implementation → screen → test → status |
| [`docs/13-phase-plan.md`](docs/13-phase-plan.md) | The 18 phases with exit gates |
| [`docs/15-dependency-license-baseline.md`](docs/15-dependency-license-baseline.md) | Dependency and licence baseline |
| [`docs/17-phase-02-report.md`](docs/17-phase-02-report.md) | **Phase 2 report** — what was built, verified and deferred |
| [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | Third-party licences shipped with the product |
| [`docs/adr/`](docs/adr/) | Architecture decision records |

## Technology (decided, with rationale in the ADRs)

| Area | Decision |
|---|---|
| UI | PySide6 (Qt 6, LGPLv3) Widgets + token-generated QSS + in-house SVG icon set |
| Data | SQLite (WAL) + SQLAlchemy 2.0 + Alembic migrations |
| Money | Integer minor units (paisa) — no floating point |
| Documents | Document Model → QTextDocument → QPrinter / QPdfWriter / QImage (one engine for preview, print and PDF) |
| Security | Argon2id password hashing, granular data-driven RBAC enforced at the service layer, append-only tamper-evident audit log |
| Activation | Offline derived verifier (no plaintext code, no online dependency) |
| Packaging | PyInstaller + Inno Setup; reproducible GitHub Actions build; GitHub Release with a `dist/` fallback |
| Fonts | Bundled Noto Sans + Noto Sans Bengali (SIL OFL 1.1) so Bangla always renders and embeds in PDF |
