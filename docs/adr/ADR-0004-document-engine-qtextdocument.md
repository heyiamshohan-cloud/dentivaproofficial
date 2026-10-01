# ADR-0004 — Document/print engine: Document Model → QTextDocument → device

- Status: **Accepted** (Phase 1)

## Context
One document engine must serve ultra-premium prescriptions, invoices, receipts,
reports and clinical summaries across A4, A5, 58mm, 80mm, mini/receipt and custom
paper profiles, on every printer exposed by Windows, with Bengali/Unicode, High-DPI
sharpness, pagination for long content, and a preview that matches the print.

## Options considered
| Option | Verdict | Reason |
|---|---|---|
| **Document Model → QTextDocument → (QPrinter \| QPdfWriter \| QImage)** | **Chosen** | One layout engine for preview/print/PDF; Qt handles text shaping (DirectWrite on Windows, HarfBuzz elsewhere), tables, images, pagination; `QPdfWriter` embeds font subsets (Unicode preserved); works with any Windows printer through the standard GDI/print-driver path. |
| Qt WebEngine (Chromium) + HTML/CSS | Rejected | Printing WebEngine content to a Windows printer is unsupported (Qt recommends PDF-then-print); adds ~150 MB and Chromium licence notices for no gain. |
| reportlab / fpdf2 for PDF + separate print path | Rejected | Two layout engines → preview/print/PDF divergence, double maintenance, double Bengali-shaping risk. |
| Screenshot/"hard-coded" rendering | Explicitly forbidden by the specification. |
| Proprietary printer SDKs | Forbidden by the specification unless unavoidable. |

## Decision (validated by Phase 1 spike)
1. **Document model** (pure Python, Qt-free, unit-testable): sections/blocks
   (heading, key-value grid, paragraph, medicine table, item table, totals,
   signature block, footer).
2. **Layout engine**: builds a `QTextDocument` from the model for a given *paper
   profile* (page size, margins, base font, template variant: `full` | `compact`).
3. **Pagination**: `doc.setPageSize(contentRect)` → `doc.pageCount()` → paint each
   page with a clipped/translated `QPainter` (verified: 80 table rows on A4
   produced 3 correctly split pages).
4. **Devices**: `QPrinter` (physical/Windows printer, `QPrintDialog` selection),
   `QPdfWriter` (Save as PDF, 300 dpi), `QImage` (preview + thumbnails).
5. **Roll/thermal**: compute document height, then request a custom `QPageSize`
   (`QSizeF(w, h)` millimetres). If the driver rejects custom sizes, fall back to
   the driver's nearest supported page and reflow; if the driver cannot print at
   all, offer the "print PDF via Windows default handler" path.

## Spike evidence (Phase 1, 2026-10-01)
- Custom page sizes 80×1200 mm and 58×600 mm accepted; PDFs generated.
- A4 80-row table → 3 pages; A5 40 rows → 4 pages; no clipping.
- PDF embeds `/FontFile2` subsets of Noto Sans **and** Noto Sans Bengali; Latin text
  extracts exactly; Bengali glyphs are embedded (visual/logical re-order on text
  extraction is an inherent Indic-PDF artefact, not data loss — see `docs/08`).

## Consequences
- All document templates live in `dentiva/documents/`; no template string is
  duplicated between preview and output.
- Windows print-path verification runs in CI against "Microsoft Print to PDF"
  and "Microsoft XPS Document Writer" (see `docs/10`).
