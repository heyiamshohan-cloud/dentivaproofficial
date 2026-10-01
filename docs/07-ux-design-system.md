# Dentiva Pro — UX architecture & design system (Phase 1)

Implementation home: `dentiva/ui/theme/{tokens.py,qss.py,icons.py,fonts.py}` and
`dentiva/ui/components/*`. Tokens are Python constants; QSS is **generated** from
them, so there is exactly one source of truth (REQ-UIX-009).

## 1. Design language
*"Calm clinical precision."* Cool near-white surfaces, a teal clinical primary,
generous whitespace, thin hairline borders, soft elevation, crisp 24 px line icons,
and restrained motion. No glossy gradients, no neon, no consumer-app playfulness.

### Colour tokens (light theme, v1)
| Token | Value | Use |
|---|---|---|
| `--canvas` | `#F4F7F9` | window background |
| `--surface` | `#FFFFFF` | cards, panels |
| `--surface-2` | `#F8FAFB` | table header, nested panels |
| `--border` | `#E2E8EC` | hairlines |
| `--border-strong` | `#CBD5DB` | inputs, dividers |
| `--ink` | `#0E2A32` | primary text |
| `--ink-2` | `#405A63` | secondary text |
| `--ink-3` | `#7A8F98` | muted/hints |
| `--primary` | `#0F8B8D` | primary action, active nav |
| `--primary-hover` | `#0C7476` | |
| `--primary-press` | `#0A6365` | |
| `--primary-soft` | `#E6F4F4` | selected row/chip background |
| `--accent` | `#22C1C3` | charts, highlights |
| `--success` | `#1FA463` | success states, paid |
| `--success-soft` | `#E8F6EE` | |
| `--warning` | `#D9822B` | expiring, due soon |
| `--warning-soft` | `#FDF3E7` | |
| `--danger` | `#D64545` | destructive, overdue |
| `--danger-soft` | `#FCECEC` | |
| `--info` | `#2F80ED` | informational |
| `--focus` | `#0F8B8D` with 2 px ring + 3 px 30 % halo | focus visibility |

Status colours are always paired with a **shape/text** cue (icon + label), never
colour alone (accessibility).

### Typography
- UI font: **Segoe UI** on Windows (10 px small, 12 px caption, **13 px base**,
  15 px subtitle, 18/22/28 px titles), with bundled **Noto Sans** as the cross-platform
  fallback; Bengali resolves to bundled **Noto Sans Bengali** via
  `QFont.insertSubstitutions` (ADR-0011).
- Tabular numerals (`font-variant-numeric` equivalent via `QFont.setFixedPitch` for
  numeric columns) so money columns align.
- Line-height 1.45; labels 12 px medium; values 13 px regular.

### Spacing / radius / elevation
- Spacing scale: **4, 8, 12, 16, 20, 24, 32, 40, 48** px. Grid base 8 px.
- Radius: control 6 px, card 10 px, dialog 14 px, pill 999 px.
- Elevation: `e1` card `0 1px 2px rgba(14,42,50,.06)` + hairline;
  `e2` popover `0 8px 24px rgba(14,42,50,.12)`; `e3` modal `0 24px 64px rgba(14,42,50,.18)`.
- Minimum touch/click target 32 px (28 px for dense table controls).

### Motion
Durations: micro 90 ms, standard 160 ms, panel 220 ms; easing
`cubic-bezier(.2,.8,.2,1)`. Animated: sidebar collapse, dialog fade+rise,
drawer slide, toast slide, hover/press colour transitions, skeleton shimmer,
table row selection. Nothing animates during data entry typing; a global
"reduce motion" setting disables non-essential animation (also honours the Windows
accessibility setting).

## 2. Component inventory (all must exist with all states)
`PrimaryButton`, `SecondaryButton`, `GhostButton`, `DangerButton`, `IconButton`,
`SplitButton` (print ▾), `TextField`, `TextArea`, `NumberField`, `MoneyField`,
`ComboBox`, `SearchableComboBox`, `DatePicker`, `TimePicker`, `DateTimePicker`,
`CheckBox`, `RadioGroup`, `Switch`, `Slider` (rare), `Tag/Chip`, `Badge`,
`StatusPill`, `Avatar`, `Card`, `StatCard`, `SectionCard`, `DataTable`
(sortable, paged, resizable columns, row actions, sticky header, empty/loading
states), `TreeTable` (where hierarchy is needed), `Tabs` (icon+label, perfectly
aligned, keyboard-navigable), `Accordion`, `Dialog` (modal), `Drawer` (side panel),
`Toast`, `NotificationItem`, `Tooltip`, `Menu`, `ContextMenu`, `ProgressBar`,
`IndeterminateSpinner`, `Skeleton`, `EmptyState`, `ErrorState`, `NoPermissionState`,
`Banner`, `Breadcrumb`, `Pagination`, `SegmentedControl` (period filters),
`Stepper` (setup wizard), `Divider`, `KeyValGrid`, `TimelineItem`,
`ToothWidget`, `DentalChartWidget`, `PrintPreviewWidget`, `PaperProfileSelector`,
`FileDropZone`, `AttachmentCard`, `AvatarUpload`, `ResponsiveGrid`,
`LockOverlay`, `ShortcutHint`.

**State matrix** for every interactive component: default, hover, focus-visible,
pressed, selected, disabled, loading, error/validation, read-only, no-permission.

## 3. Layout & responsiveness rules (REQ-RSP)
- Never absolute positioning for content; everything lives in
  `QHBoxLayout/QVBoxLayout/QGridLayout` with size policies and stretch factors.
- `QScrollArea` only where a region is *conceptually* scrollable (lists, tables,
  long forms, timeline). Top-level screens fit the viewport; inner regions scroll.
- **Breakpoints** (logical width in DIPs): `xs < 1100`, `sm < 1360`, `md < 1700`,
  `lg < 2200`, `xl ≥ 2200`.
- **`ResponsiveGrid`** — the deliberate card grid:
  - computes `columns = clamp(1, floor((width + gap) / (min_card_width + gap)), max_columns)`
    from a per-screen config (e.g. dashboard: `min_card_width=320, max_columns=4`),
  - fills a `QGridLayout` row by row, and **centres the last row** by inserting
    elastic spacers, so 6 cards at 3 columns render **3 + 3** — never 4+2 (REQ-RSP-005),
  - keeps card heights equal within a row (size policy + `QStackedLayout` where
    content differs), and reflows on resize with a single relayout pass (no flicker).
- Tables: horizontal scrolling is allowed **only** for the table body, with a
  configurable column-priority system (essential columns always visible, optional
  columns hidden below a breakpoint). Headers never scroll away vertically
  (sticky header).
- Forms: two-column layout at `sm+`, single column at `xs`; labels above fields;
  inline validation messages reserve their space so nothing jumps.
- Dialogs: max height 90 % of the viewport, content scrolls, action bar pinned at
  the bottom; minimum widths per dialog so buttons never wrap awkwardly.
- Long text: `QFontMetrics`-based elision with tooltips; wrapping where the content
  is a sentence (notes) and elision where it is an identifier (code, phone).

### High-DPI
- `Qt::HighDpiScaleFactorRoundingPolicy::PassThrough` set before `QApplication`.
- All icons SVG (rendered at device pixel ratio), all images rendered with
  `devicePixelRatioF()` awareness, no raster assets below 2× for the logo.
- No fixed pixel sizes for anything that must scale (heights derive from font
  metrics + spacing tokens).

## 4. Screen inventory (every item = real, working screen)
**Practice**: `DashboardView`, `PatientsView` (list, filters, registration),
`PatientProfileView` (13 tabs), `AppointmentsView`, `QueueView`.
**Clinical**: `TreatmentsView` (catalog + performed register), `PrescriptionsView`
(list + editor).
**Billing**: `InvoicesView` (list + editor), `PaymentsView`, `InventoryView`
(items, batches, purchases, movements, alerts), `AccountingView` (income/expenses,
reports).
**Administration**: `StaffUsersView` (staff + users + roles/permissions),
`BackupRestoreView`, `SettingsView` (grouped, with a Danger zone), `AboutView`,
`AuditLogView`, `SystemHealthView`.
**Shell/global**: `LoginDialog`, `ActivationDialog`, `SetupWizard`,
`NotificationCenter` (drawer), `GlobalSearch` (header, with a results drawer),
`PrintPreviewDialog`, `PrintCenterDialog`, `LockOverlay`, `ConfirmDangerDialog`,
`ReAuthDialog`, `ShortcutHelpDialog`, `ErrorDialog`.

## 5. Patient profile information architecture
Header (avatar, name, code, age/gender, phone, tags, alerts) + segmented tabs:
Overview · Personal · Timeline · Visits · Dental Chart · Treatments ·
Prescriptions · Appointments · Invoices · Payments · Financial History ·
Referrals · Attachments. Actions in the header: New Visit, New Appointment,
New Prescription, New Invoice, Receive Payment, Print, Edit, More (archive/delete).

## 6. Keyboard shortcuts (REQ-KBD)
| Shortcut | Action |
|---|---|
| `Ctrl+K` / `Ctrl+F` | Global search |
| `Ctrl+N` | New patient (context-aware: New <entity> on the active module) |
| `Ctrl+S` | Save current editor |
| `Esc` | Close dialog / cancel editor (with unsaved-changes guard) |
| `Ctrl+P` | Print the current document |
| `Ctrl+Shift+P` | Save as PDF |
| `Ctrl+Shift+A` | New appointment |
| `Ctrl+Shift+V` | New visit |
| `Ctrl+L` | Lock now |
| `Ctrl+1..9` | Navigate to the n-th sidebar item |
| `Ctrl+B` | Toggle sidebar |
| `F5` | Refresh current view |
| `Alt+←/→` | Back/forward in profile navigation |
| `Ctrl+,` | Settings |
| `F1` | Shortcut help |
No shortcut overrides a Windows system combination (Ctrl+Alt+Del, Win+*, Alt+F4,
Ctrl+Shift+Esc) or a standard edit combination (Ctrl+C/V/X/Z/A).

## 7. Accessibility & usability
- Full keyboard reachability with a visible focus ring; logical tab order per
  screen (explicitly set, not auto-guessed).
- Contrast ≥ 4.5:1 for body text, ≥ 3:1 for large text and UI boundaries.
- No information conveyed by colour alone; every status has an icon/label.
- Error messages say what happened, why, and what to do next
  ("Could not save the invoice: the patient has an outstanding draft. Open it or
  void it first.").
- Destructive actions use the danger styling, require explicit confirmation, and
  never sit adjacent to the primary action without separation.

## 8. Layout audit harness (how the "no clipping" requirement is enforced)
`tests/ui/layout_audit.py` walks every screen at 1366×768, 1600×900, 1920×1080,
2560×1440, 3840×2160 and at `devicePixelRatio` 1.0/1.25/1.5/1.75/2.0 and asserts:
1. no widget's `geometry()` exceeds its parent's `contentsRect()` (allow 1 px
   rounding), 2. no `QLabel` is elided unless it declares elidable intent,
   3. no horizontal scrollbar appears on a top-level screen container,
   4. no overlapping siblings in the same layout, 5. all text has ≥ 8 px padding
   from its container edge, 6. `minimumSizeHint()` fits within the smallest
   supported viewport. Screenshots of every screen/size are exported for human
   review in the release artifacts.
