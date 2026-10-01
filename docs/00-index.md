# Dentiva Pro — Documentation index

| Document | Purpose |
|---|---|
| `01-requirements-baseline.md` | Formal, ID-bearing requirements baseline derived from the master specification (REQ-*) |
| `02-architecture.md` | Layered architecture, package map, runtime flows, threading, paths, error model |
| `03-technology-decisions.md` | Technology evaluation & justification (also mirrored as ADRs) |
| `04-database-model.md` | Entity/relationship design, integrity rules, indexing, migration policy |
| `05-security-model.md` | Authentication, sessions, auto-lock, RBAC enforcement, audit, activation, hardening, threat model |
| `06-rbac-permissions.md` | Granular permission catalogue, role templates, enforcement points |
| `07-ux-design-system.md` | Design tokens, component inventory, responsive/High-DPI rules, shortcuts, layout audit |
| `08-printing-architecture.md` | Document model → layout → paper profiles → preview → printer → output; PDF & Bengali |
| `09-backup-restore.md` | Backup container, atomicity, verification, scheduling, restore semantics, recovery |
| `10-testing-strategy.md` | Test pyramid, fixtures, CI validation, clean-machine tests, `--selftest` |
| `11-build-release-installer.md` | Versioning, reproducible build, PyInstaller + Inno Setup, release gates |
| `12-requirements-traceability.md` | REQ → implementation → screen → test → status (audited every phase) |
| `13-phase-plan.md` | The 18 phases with entry/exit gates and Definition of Done |
| `14-risk-register-and-environment.md` | Verified environment findings, risk register, decisions & open questions |
| `15-dependency-license-baseline.md` | Approved licences, dependency list, rejected candidates, notices |
| `16-developer-environment.md` | Dev setup, headless Linux bootstrap, common commands, hygiene |
| `17-phase-02-report.md` | Phase 2 report: what was built, what was verified, what is deferred |
| `adr/ADR-0001…0015` | Architecture decision records (one per significant technology decision) |

Reading order for a reviewer: 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 →
12 → 13 → 14 → 15 → 16 → 17.

Status: **Phase 2 (repository, engineering foundation, design system) complete.**
The foundation described by 02, 03, 07, 10 and 16 is implemented and verified;
the domain features described by 04, 05, 06, 08 and 09 are still *planned* and
arrive in their own phases. Every document is corrected whenever reality differs
from the plan (REQ-DCM-002) — the authoritative record of what exists today is
[`12-requirements-traceability.md`](12-requirements-traceability.md) together
with the phase reports.
