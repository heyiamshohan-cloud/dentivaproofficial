"""About screen: branding, authorship, contact and notices (REQ-ABT-001…004)."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget

from dentiva import __author__, __contact__, __product_name__, __version__
from dentiva.ui.diagnostics import audit_widget
from dentiva.ui.views.about import AboutView, notices_path


@pytest.mark.usefixtures("themed_app")
def test_about_shows_product_author_and_contact(qtbot) -> None:
    about = AboutView()
    qtbot.addWidget(about)
    about.show()
    text = _collect_text(about)
    assert __product_name__ in text
    assert __version__ in text
    assert __author__ in text
    assert __contact__ in text


@pytest.mark.usefixtures("themed_app")
def test_about_credits_shohan_khan_by_name(qtbot) -> None:
    about = AboutView()
    qtbot.addWidget(about)
    about.show()
    text = _collect_text(about)
    assert "Shohan Khan" in text
    assert "helloiamshohan@gmail.com" in text


@pytest.mark.usefixtures("themed_app")
def test_about_links_the_licence_notices(qtbot) -> None:
    about = AboutView()
    qtbot.addWidget(about)
    about.show()
    assert "notices" in _collect_text(about).lower()
    assert notices_path() is not None


@pytest.mark.usefixtures("themed_app")
def test_about_lists_build_and_runtime_details(qtbot) -> None:
    about = AboutView()
    qtbot.addWidget(about)
    about.show()
    text = _collect_text(about)
    assert "Python" in text
    assert "Qt" in text


@pytest.mark.usefixtures("themed_app")
def test_about_is_free_of_layout_defects(qtbot) -> None:
    about = AboutView()
    qtbot.addWidget(about)
    about.resize(1366, 768)
    about.show()
    assert audit_widget(about) == []


def _collect_text(widget: QWidget) -> str:
    parts: list[str] = []
    for child in widget.findChildren(QWidget):
        text = child.property("text")
        if isinstance(text, str):
            parts.append(text)
        tooltip = child.toolTip()
        if isinstance(tooltip, str):
            parts.append(tooltip)
    if isinstance(widget.windowTitle(), str):
        parts.append(widget.windowTitle())
    return "\n".join(parts)
