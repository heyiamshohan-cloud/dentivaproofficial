# ADR-0011 — Fonts: bundle Noto Sans + Noto Sans Bengali (SIL OFL 1.1)

- Status: **Accepted** (Phase 1)

## Context
"Do not assume a single font exists on every Windows system." Bengali must render
in forms, tables, documents, PDF and print. Windows ships *Nirmala UI* (Bengali) on
10/11, but older builds, stripped/embedded editions and "N" variants cannot be
relied upon, and a missing font silently degrades documents to boxes.

## Decision
- Bundle **Noto Sans** (Latin/Greek/Cyrillic) and **Noto Sans Bengali**
  (Regular/SemiBold; Italic for Latin), generated as **static instances** from the
  upstream variable fonts with `fonttools` (MIT), so no variable-font edge cases and
  a smaller payload.
- Licence: **SIL Open Font License 1.1** — permits redistribution and embedding;
  obligations: ship the OFL text + copyright notice, do not sell the fonts alone,
  and (for any modification) rename. We ship them **unmodified** and include
  `THIRD_PARTY_NOTICES.md` + `assets/fonts/OFL.txt`.
- On Windows the UI base font stays **Segoe UI** (native look); the bundled Bengali
  font is registered with `QFontDatabase.addApplicationFont` and wired as a
  **substitution** (`QFont.insertSubstitutions`) so Bengali glyphs resolve to a
  bundled font while Latin keeps the native UI font.
- Documents (print/PDF) explicitly use the bundled families in the CSS
  `font-family` fallback list, guaranteeing embedded subsets and identical output on
  every machine.

## Rejected
- Relying on Nirmala UI / Vrinda / Kalpurush being present (unreliable, and Kalpurush
  licensing/provenance is unclear for commercial redistribution).
- Bundling a font with unclear redistribution terms.
