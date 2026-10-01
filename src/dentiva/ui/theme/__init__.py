"""Dentiva Pro design system: tokens, generated stylesheet, icons and fonts."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from dentiva.ui.theme import fonts, icons
from dentiva.ui.theme.fonts import FontBundle
from dentiva.ui.theme.qss import build_stylesheet
from dentiva.ui.theme.tokens import SIZE, TYPE


def configure_high_dpi() -> None:
    """Enable exact Windows scaling (100/125/150/175/200 %) for the process.

    Must be called *before* the QApplication is constructed (REQ-RSP-002).
    """
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def apply_theme(app: QApplication, *, compact: bool = False) -> FontBundle:
    """Load the bundled fonts, set the default font and install the stylesheet."""
    bundle = fonts.load_bundled_fonts()
    app.setFont(fonts.application_font(TYPE.size_body))
    app.setStyleSheet(build_stylesheet(compact=compact))
    return bundle


def standard_icon_size() -> int:
    """Default icon edge length in logical pixels."""
    return SIZE.icon


__all__ = [
    "FontBundle",
    "apply_theme",
    "build_stylesheet",
    "configure_high_dpi",
    "fonts",
    "icons",
    "standard_icon_size",
]
