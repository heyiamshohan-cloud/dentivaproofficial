# Third-party notices — Dentiva Pro

Dentiva Pro is proprietary software created by **Shohan Khan**
(<helloiamshohan@gmail.com>). It is distributed as a self-contained,
offline-first application that **includes** the third-party components listed
below. This document, together with the `licenses/` directory, exists so that
every licence obligation is met in a commercial distribution
(REQ-GEN-007, REQ-LIC-001…003).

The About screen inside the application links to this file.

How to read this document

| Column | Meaning |
|---|---|
| **Component** | What is redistributed inside the installer |
| **Licence** | The licence that applies to that component |
| **Obligation** | What Dentiva Pro must do to comply — all of it is done here |

Complete licence texts are stored verbatim in [`licenses/`](licenses/).

---

## 1. Runtime components (shipped inside the installer)

| Component | Version | Licence | Obligation | Status |
|---|---|---|---|---|
| **PySide6 / Qt 6** (Essentials) | 6.11.2 | LGPL v3 (with Qt third-party notices) | Ship licence text, copyright notice and a written offer for the Qt sources; use unmodified shared libraries; no static linking; allow relinking | Done — `licenses/LGPL-3.0.txt`, `licenses/GPL-3.0.txt`, written offer in §3 |
| **shiboken6** | 6.11.2 | LGPL v3 | As above | Done — as above |
| **SQLAlchemy** | 2.1.1 | MIT | Ship licence + copyright | Done — `licenses/SQLAlchemy-MIT.txt` |
| **Alembic** | 1.20.0 | MIT | Ship licence + copyright | Done — `licenses/Alembic-MIT.txt` |
| **argon2-cffi** | 25.1.0 | MIT | Ship licence + copyright | Done — `licenses/argon2-cffi-MIT.txt` |
| **argon2-cffi-bindings** | 26.1.0 | MIT | Ship licence + copyright | Done — `licenses/argon2-cffi-bindings-MIT.txt` |
| **Pillow** | 12.3.0 | HPND (PIL) | Ship licence + copyright | Done — `licenses/Pillow-HPND.txt` |
| **openpyxl** | 3.1.5 | MIT | Ship licence + copyright | Done — `licenses/openpyxl-MIT.txt` |
| **Noto Sans** (static instances) | upstream stable | SIL Open Font License 1.1 | Ship OFL text + copyright, unmodified, not sold standalone | Done — `assets/fonts/OFL-NotoSans.txt` |
| **Noto Sans Bengali** (static instances) | upstream stable | SIL Open Font License 1.1 | As above | Done — `assets/fonts/OFL-NotoSansBengali.txt` |
| **CPython / Python** | 3.11 | PSF-2.0 | Ship licence | Done — referenced in §4 |

Every runtime dependency is redistributable for commercial use, requires no
network access, and is used unmodified from PyPI. No component is
copyleft-incompatible with this product: the only weak-copyleft component
(Qt/PySide6) is linked dynamically, unmodified, and relinking is explicitly
permitted (§3).

## 2. Development-only components (never shipped)

| Component | Licence | Purpose |
|---|---|---|
| pytest, pytest-qt, pytest-cov | MIT | test suite |
| ruff, mypy, vulture | MIT | linting, type checking, dead-code detection |
| pypdfium2 | BSD-3-Clause | verifying generated PDFs in tests only |
| fonttools | MIT | build-time static font instances |
| PyInstaller | GPL v2 with a special exception permitting commercial bundling | building the Windows executable (output is not a derivative of PyInstaller) |
| Inno Setup 6 | Inno Setup licence (BSD/zlib-style; free for commercial use) | installer compiler |

## 3. LGPL v3 notice and written offer (Qt / PySide6 / shiboken6)

Dentiva Pro uses **Qt 6** through **PySide6**, licensed under the
**GNU Lesser General Public License version 3**. In accordance with
section 4 of the LGPL v3:

- The Qt libraries are distributed as **unmodified shared libraries**
  (`Qt6Core.dll`, `Qt6Gui.dll`, `Qt6Widgets.dll`, `Qt6Svg.dll`, `Qt6PrintSupport.dll`,
  `Qt6Pdf.dll`, `Qt6Network.dll`, …) alongside the application executable.
- The application is **dynamically linked** against them, so a recipient can
  replace those libraries with a modified version and still run the product.
- The complete texts of the **GNU Lesser General Public License v3** and the
  **GNU General Public License v3** (which the LGPL v3 supplements) ship with
  this product as `licenses/LGPL-3.0.txt` and `licenses/GPL-3.0.txt`.

**Written offer.** Dentiva Pro conveys the Qt libraries under the LGPL v3. For a
period of at least three years from the date of distribution, Shohan Khan
(<helloiamshohan@gmail.com>) will provide, on request and at no charge other
than the cost of the medium, a complete machine-readable copy of the
corresponding source code of the LGPL-covered libraries used by this product,
on the same terms as the LGPL v3. The canonical upstream source is also
published at <https://www.qt.io/download-open-source>.

Qt additionally bundles third-party components under permissive licences; their
notices are shipped with the Qt installation and are reproduced in the
installation directory by the packaging pipeline.

## 4. Licence texts

| File | Component |
|---|---|
| `licenses/LGPL-3.0.txt` | Qt / PySide6 / shiboken6 |
| `licenses/GPL-3.0.txt` | Incorporated by the LGPL v3 |
| `licenses/SQLAlchemy-MIT.txt` | SQLAlchemy |
| `licenses/Alembic-MIT.txt` | Alembic |
| `licenses/argon2-cffi-MIT.txt` | argon2-cffi |
| `licenses/argon2-cffi-bindings-MIT.txt` | argon2-cffi-bindings |
| `licenses/Pillow-HPND.txt` | Pillow (includes the bundled codec notices) |
| `licenses/openpyxl-MIT.txt` | openpyxl |
| `assets/fonts/OFL-NotoSans.txt` | Noto Sans |
| `assets/fonts/OFL-NotoSansBengali.txt` | Noto Sans Bengali |

The Python interpreter is distributed under the **PSF License Agreement**; the
text is available at <https://docs.python.org/3/license.html> and is shipped
with the Python installation embedded in the product.

## 5. Fonts

The bundled fonts are **static instances** (weights 400/600, width 100) produced
from the upstream variable fonts with `fontTools.varLib.instancer`. No glyphs,
hints, names or metadata were otherwise altered, and the "Noto" reserved font
name is used unmodified as permitted by the OFL. See
[`assets/fonts/README.md`](assets/fonts/README.md).
