# ADR-0001 — Desktop UI framework: PySide6 (Qt 6) Widgets

- Status: **Accepted** (Phase 1)
- Date: 2026-10-01
- Deciders: Lead architect (Dentiva Pro)

## Context
Dentiva Pro is a flagship commercial offline Windows desktop product requiring:
premium bespoke visuals (not "generic Python app"), High-DPI correctness across
100%–200% scaling, complex data grids/tabs/dialogs/drawers, an interactive dental
chart, native Windows printing (A4/A5/58mm/80mm/custom, USB/network/Bluetooth
printers exposed by Windows), Unicode + Bengali shaping, and commercial
redistribution.

## Options considered
| Option | Verdict | Reason |
|---|---|---|
| **PySide6 Widgets (Qt 6, LGPLv3)** | **Chosen** | Mature, LGPL (commercial redistribution compliant with attribution + relinking), native print stack (`QPrinter`/`QPrintDialog`/`QPdfWriter`), `QTextDocument` layout+pagination engine shared by preview/print/PDF, per-monitor High-DPI, `QThreadPool`, SVG, QSS styling, huge install base. |
| PyQt6 | Rejected | GPLv3 or paid commercial licence; buying a licence conflicts with "no paid SDK" and adds cost. LGPL PySide6 gives the same engine. |
| PySide6 QML / Qt Quick | Rejected | Printing WebEngine/Quick content to a Windows printer is not supported (Qt docs recommend print-to-PDF first); QML packaging is heavier; no benefit for dense clinical forms. |
| tkinter (+ ttkbootstrap) | Rejected | Cannot reach the required visual bar; no native print engine; poor High-DPI; would force an external PDF/print stack (layout/preview parity lost). |
| wxPython | Rejected | wxHTML printing is weaker; theming/animation effort higher; smaller ecosystem for the required widgets. |
| Flet / webview / Electron-like (CEF) | Rejected | Bundles a browser engine (huge, extra licences, update/security burden); printing requires the OS default handler; slower startup. |
| Kivy | Rejected | Non-native look; printing story inadequate. |

## Decision
Build the UI with **PySide6 (Qt 6) Widgets**, styled by a token-driven QSS
generator and custom QWidget components (see `docs/07-ux-design-system.md`).

## Consequences / obligations
- Comply with **LGPLv3**: ship `THIRD_PARTY_NOTICES.md` with the LGPL text, the Qt
  copyright notice, and a written offer for Qt sources; use unmodified Qt shared
  libraries from the official wheels; do not statically link Qt.
- Pin `PySide6==6.x` (Essentials is sufficient: QtCore/Gui/Widgets/PrintSupport/Svg/Sql/Network/Concurrent).
- Enable `PassThrough` High-DPI rounding policy; never use absolute pixel layouts.
