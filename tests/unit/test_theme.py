"""Design system: tokens drive the stylesheet, icons render, fonts load.

REQ-UIX-009, REQ-RSP-002, ADR-0011/0013.
"""

from __future__ import annotations

from dentiva.ui.theme import icons
from dentiva.ui.theme.fonts import application_families, document_font_stack, load_bundled_fonts
from dentiva.ui.theme.qss import build_stylesheet
from dentiva.ui.theme.tokens import COLORS, RADIUS, SIZE, SPACING, TYPE


def test_stylesheet_covers_every_component_family() -> None:
    sheet = build_stylesheet()
    for selector in (
        "QPushButton",
        "QLineEdit",
        "QComboBox",
        "QTableView",
        "QTabBar",
        "QDialog",
        "QScrollBar",
    ):
        assert selector in sheet
    assert COLORS.primary in sheet
    assert "danger" in sheet


def test_compact_stylesheet_is_still_complete() -> None:
    compact = build_stylesheet(compact=True)
    assert "QPushButton" in compact
    assert len(compact) > 1000


def test_every_declared_icon_renders() -> None:
    broken = []
    for name in icons.ICON_NAMES:
        pixmap = icons.pixmap(name, 24, COLORS.ink)
        if pixmap.isNull():
            broken.append(name)
    assert not broken, f"icons failed to render: {broken}"


def test_icon_pixmap_respects_device_pixel_ratio() -> None:
    pixmap = icons.pixmap("patients", 24, COLORS.primary, dpr=2.0)
    assert pixmap.width() == 48
    assert pixmap.devicePixelRatio() == 2.0


def test_unknown_icon_raises() -> None:
    import pytest

    with pytest.raises(KeyError):
        icons.pixmap("does-not-exist")


def test_bundled_fonts_include_bengali(assets_root) -> None:
    bundle = load_bundled_fonts(assets_root)
    assert not bundle.missing, bundle.missing
    assert bundle.has_bengali
    assert bundle.ok


def test_font_stacks_put_native_family_first() -> None:
    families = application_families()
    assert families[0] == TYPE.family_native
    assert TYPE.family_bengali in families
    assert TYPE.family_bengali in document_font_stack()


def test_tokens_are_internally_consistent() -> None:
    assert SPACING.sm < SPACING.lg < SPACING.xxl
    assert SIZE.min_touch >= 32
    assert RADIUS.control <= RADIUS.card <= RADIUS.dialog
    assert TYPE.size_caption < TYPE.size_body < TYPE.size_title
