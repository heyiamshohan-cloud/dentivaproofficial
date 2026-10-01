"""Bengali glyph coverage through the bundled font stack (REQ-BNG-001/002)."""

from __future__ import annotations

import pytest
from PySide6.QtGui import QFont, QFontMetricsF, QRawFont
from PySide6.QtWidgets import QApplication

from dentiva.ui.theme.fonts import application_font, load_bundled_fonts
from dentiva.ui.theme.tokens import TYPE

SAMPLE = "দাঁতে ব্যথা, মাড়ি ফুলা ও রক্ত পড়া"


@pytest.mark.usefixtures("themed_app")
def test_bengali_has_real_glyphs_in_the_bundled_font(assets_root) -> None:
    load_bundled_fonts(assets_root)
    font = QFont()
    font.setFamilies([TYPE.family_bengali])
    font.setPointSize(12)
    indexes = QRawFont.fromFont(font).glyphIndexesForString(SAMPLE)
    assert indexes and all(index > 0 for index in indexes), "no Bengali glyphs available"


@pytest.mark.usefixtures("themed_app")
def test_latin_font_does_not_claim_bengali_glyphs(assets_root) -> None:
    load_bundled_fonts(assets_root)
    font = QFont()
    font.setFamilies([TYPE.family_ui])
    font.setPointSize(12)
    indexes = QRawFont.fromFont(font).glyphIndexesForString(SAMPLE)
    assert any(index == 0 for index in indexes), "Latin font unexpectedly covers Bengali"


@pytest.mark.usefixtures("themed_app")
def test_application_font_measures_bengali_text(assets_root) -> None:
    load_bundled_fonts(assets_root)
    font = application_font(13)
    assert QFontMetricsF(font).horizontalAdvance(SAMPLE) > 0


@pytest.mark.usefixtures("themed_app")
def test_mixed_content_is_measured_without_error() -> None:
    metrics = QFontMetricsF(application_font(13))
    assert metrics.horizontalAdvance("রাহাত Hossain — Tooth 36") > 0
    assert QApplication.instance() is not None
