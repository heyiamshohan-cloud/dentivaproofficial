# Dentiva Pro — Printing & document architecture (Phase 1)

Implements REQ-PRT-*, REQ-DOC-*, REQ-PPV-* with the decisions of ADR-0004/0011.
Validated by a Phase 1 spike (results quoted in ADR-0004).

## 1. Pipeline

```
                 ┌──────────────────────────────────────────────────────────┐
 Domain data ──▶ │ DocumentModel (pure Python, Qt-free, unit-testable)      │
                 │  sections → blocks (heading, keyvalue, paragraph,        │
                 │  table, medicine_table, totals, signature, footer,       │
                 │  spacer, image, qr, page_break_hint)                     │
                 └───────────────┬──────────────────────────────────────────┘
                                 ▼
                 ┌──────────────────────────────────────────────────────────┐
                 │ LayoutEngine  (Qt)                                       │
                 │  DocumentModel + PaperProfile + TemplateVariant          │
                 │       → QTextDocument (HTML/CSS built from tokens)       │
                 └───────────────┬──────────────────────────────────────────┘
                                 ▼
                 ┌──────────────────────────────────────────────────────────┐
                 │ Paginator                                                │
                 │  setPageSize(contentRect) → pageCount() → paint pages    │
                 └───────┬──────────────┬───────────────┬───────────────────┘
                         ▼              ▼               ▼
                    QPrinter       QPdfWriter        QImage
                  (Windows print)  (Save as PDF)   (Preview / thumbs)
                         │
                         ▼
                 PrintPreviewDialog → printer selection (QPrintDialog) → output
```

Because **one** `QTextDocument` is painted onto every device, preview, print and
PDF are the same layout by construction (REQ-PPV-002).

## 2. Document model
`documents/model.py` defines immutable dataclasses:
`Document(title, profile, sections[], metadata)` and blocks:
`Heading`, `ClinicHeader` (logo/name/address/contact/dentist block with
designations + qualifications), `PatientBlock` (name, code, age/gender, phone,
date, address), `ClinicalBlock` (C/C, O/E, R/E, Advice, Diagnosis — labels come
from the configurable document-label dictionary, so a clinic may use Bangla
headings), `MedicineTable` (index, medicine + form/strength, dose schedule, meal
relation, duration, quantity, instructions), `ItemTable` (treatment, description,
tooth, qty, unit price, discount, line total), `TotalsBlock` (subtotal, discount,
total, paid, due), `Paragraph`, `KeyValueGrid`, `NoteList`, `SignatureBlock`
(kept free of printed text), `FooterBlock`, `PageBreak`, `Spacer`, `ImageBlock`.
The model carries no Qt types and is fully unit-testable; a "long content" fixture
generator produces stress documents (50 medicines, 200 invoice lines, 4 000-character
notes) used by the pagination tests.

## 3. Paper profiles
| Profile | Size | Variant | Typical use |
|---|---|---|---|
| A4 | 210 × 297 mm | full | prescriptions, invoices, reports |
| A5 | 148 × 210 mm | full | compact prescriptions, invoices |
| 80 mm | 80 mm × auto-height | compact | pharmacy-style receipts, payments |
| 58 mm | 58 mm × auto-height | compact | small thermal receipts |
| Mini | 75 × 120 mm (configurable) | compact | counter receipts |
| Custom | user width/height/margins | full or compact | any printer form |

- Margins, base font size, orientation, logo on/off, signature on/off, footer text
  and "compact" layout are all per-profile settings persisted in
  `printer_profile` (REQ-SET-001).
- Roll profiles (**auto-height**): the engine lays the document out at the paper
  width, measures the resulting height, then requests a custom page size
  `QPageSize(QSizeF(width_mm, measured_height_mm), Millimeter)`. Verified in the
  spike for 58 mm and 80 mm.
- **Driver fallback chain for thermal/custom sizes:**
  1. request the custom `QPageSize`;
  2. if the printer refuses (invalid page size), retry with the closest supported
     driver page and reflow the document to it, warning the user once;
  3. if the printer cannot print at all, offer "Print via PDF" (render to a
     temporary PDF and hand it to the Windows default PDF handler) and log the
     reason in `print_job.result`.

## 4. Printer handling
- Enumeration via `QPrinterInfo` (name, description, location, make/model, state,
  supported page sizes); default printer read from Windows.
- Selection through the native `QPrintDialog` (so every Windows printer — USB,
  network, Wi-Fi, Bluetooth-paired, thermal — is reachable with its own driver
  preferences), plus a quick "printer profile" dropdown that stores the last
  printer per document type.
- `QPrinter.HighResolution` resolution; rasterisation is avoided — text stays
  vector, so 300–1200 dpi devices print sharply (REQ-PRT-010).
- Print result is recorded in `print_job` (pages, printer, result, error) for
  reprint and troubleshooting.

## 5. PDF
- `QPdfWriter` at 300 dpi, identical pagination code path, document metadata set
  (title = "Prescription P-000123 · Dentiva Pro", author = clinic, creator =
  "Dentiva Pro 1.0.0").
- Fonts: the document CSS sets `font-family: 'Noto Sans','Noto Sans Bengali'`;
  Qt embeds subsets (`/FontFile2`) — spike-verified for both Latin and Bengali,
  so the PDF renders identically on any machine (REQ-PRT-009).
- Known and accepted artefact: text *extraction* from an Indic PDF can return
  glyph-order/control characters (matras and ligature components have no single
  Unicode mapping). Rendering and printing are correct; this is inherent to
  shaped Indic text in PDF and is documented rather than papered over. Where
  machine-readable export matters, the app exports CSV/XLSX instead.
- Verification tests: page count, embedded-font presence, ink coverage per page
  (non-blank), and a golden-text check that Latin/reference fields are present.

## 6. Print preview
`PrintPreviewDialog`: page thumbnails strip, zoom (fit width / fit page / 50–400 %),
page navigation, paper profile + printer selectors, "paper size" label
(e.g. *A4 · 210 × 297 mm · 12 mm margins*), Print, Save as PDF, Close. It renders
through the paginator onto `QImage` at the current zoom × device pixel ratio, so
it is sharp on High-DPI displays and shows exactly the paginated pages.

## 7. Templates (each with full + compact variants)
1. **Prescription** — clinic header with logo, address, phone; dentist block with
   *all* designations and qualifications; patient block (name, code, age/gender,
   phone, date); clinical block (C/C, O/E, R/E/Advice, diagnosis); numbered medicine
   table with dose schedule columns and instructions; follow-up line; footer
   message; signature area bottom-right with adequate blank space and no printed
   text inside the writing area (REQ-DOC-007).
2. **Invoice** — clinic header (no dentist signature by default), bill-to block,
   item table, totals (subtotal, discount, total, paid, due), payment status,
   payment history block, terms/footer.
3. **Payment receipt** — compact by default; receipt no, invoice no, patient,
   amount in words and figures, method + reference, received-by, thank-you footer.
4. **Clinical summary / visit report** — visit details, complaints, findings,
   chart summary, treatments, advice.
5. **Reports** — accounting (period totals), inventory (stock/expiry), patient
   register, daily collection. Printable and exportable.

## 8. Document safety rules (enforced by tests)
- No block may overflow the content rectangle: the paginator is the only place
  that paints, and every block is measured before painting.
- Tables use `table-layout: fixed`-style percentage widths with
  `word-wrap`/`overflow-wrap`; long medicine names wrap instead of pushing columns
  off the page (verified with 60-character Bangla medicine names).
- Long documents paginate; the signature block and footer are pinned to the last
  page (`keep-with-next` behaviour implemented by measuring and inserting a page
  break when fewer than N points remain).
- Paper-profile switching re-runs the full layout; no state leaks between renders.
- Empty optional sections are omitted rather than leaving blank bands.

## 9. Print Center
A single dialog listing printables for the current context (patient, invoice,
visit, report) with document type, target profile, printer, "Preview", "Print",
"Save as PDF", and a reprint history from `print_job`.
