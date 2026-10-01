"""Layout audit across the supported resolution and DPI matrix (REQ-RSP-001/002/006)."""

from __future__ import annotations

import itertools

import pytest

from dentiva.ui.diagnostics import audit_widget
from dentiva.ui.shell.main_window import MainWindow
from dentiva.ui.shell.navigation import ordered

RESOLUTIONS = [(1366, 768), (1600, 900), (1920, 1080), (2560, 1440), (3840, 2160)]
SCALING = [1.0, 1.25, 1.5, 1.75, 2.0]


def _configure_dpr(monkeypatch, factor: float) -> None:
    monkeypatch.setenv("QT_SCALE_FACTOR", str(factor))


@pytest.mark.parametrize(("width", "height"), RESOLUTIONS)
def test_every_screen_is_clean_at_every_resolution(qtbot, monkeypatch, width, height) -> None:
    _configure_dpr(monkeypatch, 1.0)
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(width, height)
    window.show()
    problems: list[str] = []
    for item in ordered():
        window.navigate(item.id)
        view = window.view_for(item.id)
        assert view is not None
        for issue in audit_widget(view):
            problems.append(f"{item.id}@{width}x{height}: {issue.describe()}")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize(("width", "factor"), list(itertools.product([1366, 1920], SCALING)))
def test_shell_renders_at_every_scaling_factor(qtbot, monkeypatch, width, factor) -> None:
    _configure_dpr(monkeypatch, factor)
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(width, 768)
    window.show()
    problems: list[str] = []
    for item in ordered():
        window.navigate(item.id)
        view = window.view_for(item.id)
        assert view is not None
        for issue in audit_widget(view):
            problems.append(f"{item.id}@{width}/{factor}: {issue.describe()}")
    assert not problems, "\n".join(problems)
