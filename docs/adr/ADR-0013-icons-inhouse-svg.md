# ADR-0013 — Iconography: in-house SVG icon set

- Status: **Accepted** (Phase 1)

## Decision
- All UI icons are **authored in this repository** as 24×24 SVG path data in
  `dentiva/ui/theme/icons.py`, rendered through `QSvgRenderer` and cached as
  device-pixel-ratio-aware `QPixmap`s (crisp at 100–200 % scaling, recolorable via
  `currentColor`-style palette substitution).
- No third-party icon pack is bundled.

## Rejected
- Font Awesome / Material icon fonts: extra licence/attribution surface, icon-font
  alignment/weight inconsistencies, and font-fallback complexity next to Bengali.
- Bundled PNG sprite sheets: blur at High-DPI, no recoloring.
