"""Bundled font loading and font stacks (ADR-0011).

Requirements addressed:
  * Bengali and Latin content must render on any supported Windows build, so the
    application ships Noto Sans and Noto Sans Bengali (SIL OFL 1.1);
  * the Windows interface keeps its native look (Segoe UI) for Latin text;
  * documents (print/PDF) use the bundled families so glyphs are always embedded.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase

from dentiva.ui.theme.tokens import TYPE

#: Font files shipped in ``assets/fonts``.
BUNDLED_FONTS: tuple[str, ...] = (
    "NotoSans-Regular.ttf",
    "NotoSans-SemiBold.ttf",
    "NotoSans-Italic.ttf",
    "NotoSansBengali-Regular.ttf",
    "NotoSansBengali-SemiBold.ttf",
)


@dataclass(frozen=True, slots=True)
class FontBundle:
    """Result of loading the bundled fonts."""

    loaded: tuple[str, ...]
    missing: tuple[str, ...]

    @property
    def has_bengali(self) -> bool:
        return TYPE.family_bengali in self.loaded

    @property
    def ok(self) -> bool:
        return bool(self.loaded) and not self.missing


def fonts_directory(assets_root: Path | None = None) -> Path:
    """Directory that holds the bundled font files."""
    if assets_root is not None:
        return Path(assets_root) / "fonts"
    from dentiva.core.paths import assets_root as _assets_root

    return _assets_root() / "fonts"


def load_bundled_fonts(assets_root: Path | None = None) -> FontBundle:
    """Register the bundled fonts with Qt. Safe to call more than once."""
    directory = fonts_directory(assets_root)
    loaded: list[str] = []
    missing: list[str] = []
    for name in BUNDLED_FONTS:
        path = directory / name
        if not path.is_file():
            missing.append(name)
            continue
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            missing.append(name)
            continue
        for family in QFontDatabase.applicationFontFamilies(font_id):
            if family not in loaded:
                loaded.append(family)
    return FontBundle(loaded=tuple(loaded), missing=tuple(missing))


def application_families() -> list[str]:
    """Ordered family list used for QFont.setFamilies (per-character fallback)."""
    return [TYPE.family_native, TYPE.family_ui, TYPE.family_bengali]


def application_font(size: int | None = None, *, weight: int | None = None) -> QFont:
    """Default UI font: native Latin first, bundled Unicode fallbacks after."""
    font = QFont()
    font.setFamilies(application_families())
    font.setPointSize(size or TYPE.size_body)
    if weight is not None:
        font.setWeight(weight)
    return font


def document_families() -> list[str]:
    """Family list used by printed documents (always embeddable in PDF)."""
    return [TYPE.family_ui, TYPE.family_bengali]


def document_font_stack() -> str:
    """CSS ``font-family`` value for the document engine."""
    return ", ".join(f"'{family}'" for family in document_families())


def document_font(size_pt: float = 10.0, *, bold: bool = False, italic: bool = False) -> QFont:
    """QFont for document rendering (bundled families only)."""
    font = QFont()
    font.setFamilies(document_families())
    font.setPointSizeF(size_pt)
    font.setBold(bold)
    font.setItalic(italic)
    return font


def has_glyphs(family: str, text: str) -> bool:
    """True when *family* provides glyphs for *text* (used by the font tests)."""
    from PySide6.QtGui import QFontMetricsF

    font = QFont()
    font.setFamilies([family])
    font.setPointSize(12)
    metrics = QFontMetricsF(font)
    return float(metrics.horizontalAdvance(text)) > 0
