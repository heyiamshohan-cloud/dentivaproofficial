"""Data table with pagination, alignment rules and a designed empty state hook.

The table never loads an unbounded dataset: callers pass one page at a time and
:class:`Pagination` reports the requested page back to the service layer.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from dentiva.core.paging import Page, PageRequest
from dentiva.ui.components.buttons import Button
from dentiva.ui.theme.tokens import SPACING

#: Qt passes a default-constructed index for "not a child"; the enum default is
#: kept in a module constant so the model signatures stay readable.
_NO_PARENT = QModelIndex()
_DISPLAY_ROLE = int(Qt.ItemDataRole.DisplayRole)


@dataclass(frozen=True, slots=True)
class Column:
    """Column definition: header, data key, alignment and optional formatter."""

    key: str
    header: str
    align: str = "left"
    width: int | None = None
    stretch: bool = False
    formatter: Callable[[Any], str] | None = None


class TableModel(QAbstractTableModel):
    """Read-only table model over a list of dictionaries."""

    def __init__(
        self, columns: Sequence[Column], rows: Sequence[dict[str, Any]] | None = None
    ) -> None:
        super().__init__()
        self._columns = list(columns)
        self._rows: list[dict[str, Any]] = list(rows or [])

    # -------------------------------------------------------------- Qt model --
    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = _NO_PARENT) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = _NO_PARENT) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = _DISPLAY_ROLE,
    ) -> Any:
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        row = self._rows[index.row()]
        column = self._columns[index.column()]
        value = row.get(column.key)
        return column.formatter(value) if column.formatter else _display(value)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = _DISPLAY_ROLE,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return None
        if 0 <= section < len(self._columns):
            return self._columns[section].header
        return None

    # ------------------------------------------------------------------ API --
    def set_rows(self, rows: Sequence[dict[str, Any]]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()


def _display(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


class DataTable(QWidget):
    """Styled table view with column configuration and row activation."""

    rowActivated = Signal(dict)
    rowSelected = Signal(dict)

    def __init__(
        self, columns: Sequence[Column], *, row_height: int = 40, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.columns = list(columns)
        self.model = TableModel(self.columns)
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.verticalHeader().setVisible(False)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.view.setAlternatingRowColors(True)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.setWordWrap(False)
        self.view.verticalHeader().setDefaultSectionSize(row_height)
        self.view.setShowGrid(False)
        self.view.doubleClicked.connect(self._on_activated)
        self.view.clicked.connect(self._on_clicked)

        header = self.view.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(64)
        for index, column in enumerate(self.columns):
            if column.width:
                self.view.setColumnWidth(index, column.width)
            if column.stretch:
                header.setSectionResizeMode(index, QHeaderView.ResizeMode.Stretch)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.view)

        self._rows: list[dict[str, Any]] = []

    def set_rows(self, rows: Sequence[dict[str, Any]]) -> None:
        self._rows = list(rows)
        self.model.set_rows(self._rows)

    def rows(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def selected_row(self) -> dict[str, Any] | None:
        indexes = self.view.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self._rows[row] if 0 <= row < len(self._rows) else None

    def _on_activated(self, index: QModelIndex) -> None:
        row = self._rows[index.row()] if 0 <= index.row() < len(self._rows) else None
        if row is not None:
            self.rowActivated.emit(row)

    def _on_clicked(self, index: QModelIndex) -> None:
        row = self._rows[index.row()] if 0 <= index.row() < len(self._rows) else None
        if row is not None:
            self.rowSelected.emit(row)


class Pagination(QWidget):
    """Page controls plus a 'showing X–Y of Z' summary."""

    pageChanged = Signal(int)

    def __init__(self, *, page_size: int = 25, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.page = 1
        self.page_size = page_size
        self.total = 0
        self.summary = QLabel("No records")
        self.summary.setProperty("role", "caption")
        self.prev = Button("Prev", size="compact", icon_name="chevronLeft")
        self.next = Button("Next", size="compact", icon_name="chevronRight")
        self.prev.clicked.connect(lambda: self.pageChanged.emit(max(1, self.page - 1)))
        self.next.clicked.connect(lambda: self.pageChanged.emit(self.page + 1))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, SPACING.sm, 0, 0)
        layout.setSpacing(SPACING.sm)
        layout.addWidget(self.summary, 1)
        layout.addWidget(self.prev)
        layout.addWidget(self.next)

    def apply_page(self, page: Page[Any]) -> None:
        """Update the controls from a :class:`Page` returned by a repository."""
        self.set_state(page=page.page, page_size=page.page_size, total=page.total)

    def page_request(self) -> PageRequest:
        """The :class:`PageRequest` the UI is currently showing."""
        return PageRequest(page=self.page, page_size=self.page_size)

    def set_state(self, *, page: int, page_size: int, total: int) -> None:
        self.page = max(1, page)
        self.page_size = max(1, page_size)
        self.total = max(0, total)
        last_page = max(1, (self.total + self.page_size - 1) // self.page_size)
        first = (self.page - 1) * self.page_size + 1 if self.total else 0
        last = min(self.page * self.page_size, self.total)
        self.summary.setText(
            f"Showing {first}–{last} of {self.total}" if self.total else "No records"
        )
        self.prev.set_enabled(self.page > 1)
        self.next.set_enabled(self.page < last_page)
