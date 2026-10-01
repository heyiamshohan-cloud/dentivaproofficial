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
| `adr/ADR-0001…0015` | Architecture decision records (one per significant technology decision) |

Reading order for a reviewer: 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 →
12 → 13 → 14 → 15 → 16.

Status: **Phase 1 (planning) — no application code exists yet.** Every document
describes the *planned* implementation and is updated as phases complete. The
documentation is written to describe what will be built and is corrected whenever
reality differs (REQ-DCM-002).
