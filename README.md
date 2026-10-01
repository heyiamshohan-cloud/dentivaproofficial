# Dentiva Pro

**Offline-first, production-grade Windows desktop dental clinic management software for Bangladesh.**
English interface · Unicode/Bangla clinical content · BDT (৳) currency · no cloud dependency.

## Current status

**Phase 1 — Product discovery, requirements freeze and technical planning.** (No application
code yet.) This phase produced the engineering baseline:

- [`docs/01-requirements-baseline.md`](docs/01-requirements-baseline.md) — formal, ID-bearing requirements (`REQ-*`)
- [`docs/02-architecture.md`](docs/02-architecture.md) — layered architecture, package map, runtime flows
- [`docs/03-technology-decisions.md`](docs/03-technology-decisions.md) — technology evaluation and justification
- [`docs/adr/`](docs/adr/) — 15 architecture decision records (UI framework, database, money, printing, security, packaging, …)
- [`docs/04-database-model.md`](docs/04-database-model.md) — entity/relationship design and integrity rules
- [`docs/05-security-model.md`](docs/05-security-model.md) · [`docs/06-rbac-permissions.md`](docs/06-rbac-permissions.md)
- [`docs/07-ux-design-system.md`](docs/07-ux-design-system.md) · [`docs/08-printing-architecture.md`](docs/08-printing-architecture.md)
- [`docs/09-backup-restore.md`](docs/09-backup-restore.md) · [`docs/10-testing-strategy.md`](docs/10-testing-strategy.md)
- [`docs/11-build-release-installer.md`](docs/11-build-release-installer.md) · [`docs/12-requirements-traceability.md`](docs/12-requirements-traceability.md)
- [`docs/13-phase-plan.md`](docs/13-phase-plan.md) · [`docs/14-risk-register-and-environment.md`](docs/14-risk-register-and-environment.md)
- [`docs/15-dependency-license-baseline.md`](docs/15-dependency-license-baseline.md) · [`docs/16-developer-environment.md`](docs/16-developer-environment.md)

Start with [`docs/00-index.md`](docs/00-index.md).

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

## Developer setup (Linux/CI, headless)

```bash
./tools/dev/setup_headless_linux.sh
source /tmp/dentiva-venv/bin/activate
export QT_QPA_PLATFORM=offscreen
pytest -q
```

On Windows/macOS/Linux with a display: `python -m venv .venv && pip install -r requirements-dev.txt`.

## Author

Dentiva Pro — created by **Shohan Khan** · <helloiamshohan@gmail.com>
