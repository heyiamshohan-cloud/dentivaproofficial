# Bundled fonts

Dentiva Pro bundles Unicode-capable fonts so that Bangla and Latin content always
render and always embed correctly in PDF/print output, regardless of which fonts a
given Windows installation happens to provide.

| File | Upstream | Licence |
|---|---|---|
| `NotoSans-Regular.ttf`, `NotoSans-SemiBold.ttf`, `NotoSans-Italic.ttf` | Google Fonts — Noto Sans | SIL Open Font License 1.1 |
| `NotoSansBengali-Regular.ttf`, `NotoSansBengali-SemiBold.ttf` | Google Fonts — Noto Sans Bengali | SIL Open Font License 1.1 |

These are **static instances** produced from the upstream variable fonts with
Google's own `fontTools.varLib.instancer` (weights 400/600, width 100). No glyphs,
hints, names or metadata were otherwise altered. `OFL-NotoSans.txt` and `OFL-NotoSansBengali.txt` are the
upstream licence texts (verbatim, one per family) and ship with the application.

Licence obligations (SIL OFL 1.1): the fonts are redistributed unmodified, the OFL
text and the copyright notice accompany them, and they are not sold standalone.
See `THIRD_PARTY_NOTICES.md`.
