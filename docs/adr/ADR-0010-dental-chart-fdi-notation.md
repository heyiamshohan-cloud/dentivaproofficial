# ADR-0010 — Dental chart notation: FDI / ISO 3950 two-digit

- Status: **Accepted** (Phase 1)

## Context
The specification requires a documented, recognised tooth-numbering convention with
appropriate support for Bangladeshi clinical practice.

## Decision
- **Primary notation: FDI / ISO 3950 two-digit** (quadrant 1–4 + tooth 1–8 for the
  permanent dentition → 11–48; quadrants 5–8 + tooth 1–5 for the primary dentition
  → 51–85). Rationale: it is the international ISO standard, unambiguous in text and
  print, taught in Bangladeshi dental curricula (BSMMU/DU/dental colleges) and used
  across South Asian and European practice; it maps cleanly to a database
  (`tooth_number` integer) and to printed documents.
- **Display alternatives** provided as a per-clinic setting (labels only, same
  underlying FDI identity): **Palmer notation** and **Universal (1–32 / A–T)**
  toggles, so a clinic comfortable with another convention can work that way
  without data duplication.
- The chart is a **painted, interactive QWidget** (adult 32-tooth and paediatric
  20-tooth layouts), not a decorative image: each tooth is a hit-testable region
  with status colours/shapes, multi-select, per-tooth surfaces, and per-tooth
  finding history.

## Consequences
- `tooth_finding` rows store `tooth_fdi` (11..48 / 51..85), `surface set`,
  `status`, `visit_id`, `chart_id`, `dentist_id`, `note`, `recorded_at`.
- Historical integrity: a finding is **never** mutated by a later visit; a new visit
  creates new finding rows; "presenting" state is derived from the latest finding
  per tooth **as of** a selected visit (see `docs/04`).
