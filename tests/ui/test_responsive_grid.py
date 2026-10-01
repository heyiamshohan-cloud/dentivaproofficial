"""The responsive card grid must fill rows deliberately (REQ-RSP-005).

Six cards at a three-column breakpoint must render 3 + 3 — never 4 + 2 or 5 + 1,
which is what an uncontrolled wrapping flow produces.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy

from dentiva.ui.components.layout import ResponsiveGrid, density_for_width


def _resize(widget, width: int, height: int) -> None:
    """Resize and let Qt deliver the layout event before geometry is asserted."""
    widget.resize(width, height)
    QApplication.processEvents()


def _cards(count: int) -> list[QLabel]:
    cards = []
    for index in range(count):
        card = QLabel(f"Card {index + 1}")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card.setMinimumWidth(280)
        cards.append(card)
    return cards


def _positions(grid: ResponsiveGrid) -> list[tuple[int, int]]:
    layout = grid.grid
    positions: list[tuple[int, int]] = []
    for card in grid._items:
        index = layout.indexOf(card)
        row, column, _rowspan, _colspan = layout.getItemPosition(index)
        positions.append((row, column))
    return positions


def test_six_cards_render_three_plus_three(qtbot) -> None:
    grid = ResponsiveGrid(min_card_width=300, max_columns=3)
    qtbot.addWidget(grid)
    _resize(grid, 1000, 600)
    grid.set_items(_cards(6))
    assert grid.column_count(1000) == 3
    assert _positions(grid) == [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]


def test_column_count_follows_available_width(qtbot) -> None:
    grid = ResponsiveGrid(min_card_width=300, max_columns=4)
    qtbot.addWidget(grid)
    assert grid.column_count(640) == 2
    assert grid.column_count(1000) == 3
    assert grid.column_count(1600) == 4
    assert grid.column_count(4000) == 4  # capped by max_columns


def test_five_cards_leave_one_centred_slot(qtbot) -> None:
    grid = ResponsiveGrid(min_card_width=300, max_columns=3)
    qtbot.addWidget(grid)
    _resize(grid, 1000, 600)
    grid.set_items(_cards(5))
    positions = _positions(grid)
    assert positions[:3] == [(0, 0), (0, 1), (0, 2)]
    assert positions[3:] == [(1, 0), (1, 1)]


def test_grid_is_rebuilt_when_the_column_count_changes(qtbot, monkeypatch) -> None:
    grid = ResponsiveGrid(min_card_width=300, max_columns=4)
    qtbot.addWidget(grid)
    _resize(grid, 1600, 800)
    grid.set_items(_cards(8))
    assert len({row for row, _column in _positions(grid)}) == 2  # 4 columns
    monkeypatch.setattr(grid, "column_count", lambda width=None: 2)
    grid._relayout()
    positions = _positions(grid)
    assert len({row for row, _column in positions}) == 4
    assert [column for _row, column in positions[:2]] == [0, 1]


def test_clear_removes_every_item(qtbot) -> None:
    grid = ResponsiveGrid()
    qtbot.addWidget(grid)
    grid.set_items(_cards(3))
    grid.clear()
    assert grid._items == []


def test_density_helper() -> None:
    assert density_for_width(1024) == "compact"
    assert density_for_width(1300) == "compact"
    assert density_for_width(1366) == "comfortable"
    assert density_for_width(1920) == "comfortable"
