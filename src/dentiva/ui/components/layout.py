"""Layout helpers, including the deliberate responsive card grid (REQ-RSP-005)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QSpacerItem, QWidget

from dentiva.ui.theme.tokens import BREAKPOINTS, SPACING


class ResponsiveGrid(QWidget):
    """Card grid that fills rows completely and centres the last row.

    A natural wrapping flow layout would turn six cards into 4+2 or 5+1 as the
    window resizes. This grid instead derives a column count from the available
    width (``columns = clamp(1, floor((w + gap) / (min_card_width + gap)), max_columns)``),
    fills the grid row by row, and centres the final row with elastic spacers, so
    six cards always render 3+3 at a three-column breakpoint.
    """

    def __init__(
        self,
        *,
        min_card_width: int = 320,
        max_columns: int = 4,
        gap: int = SPACING.lg,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.min_card_width = min_card_width
        self.max_columns = max_columns
        self.gap = gap
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(gap)
        self.grid.setVerticalSpacing(gap)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._items: list[QWidget] = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    # ------------------------------------------------------------------ data --
    def set_items(self, items: list[QWidget]) -> None:
        """Replace the grid contents and relayout."""
        self.clear()
        self._items = list(items)
        self._relayout()

    def add_item(self, item: QWidget) -> None:
        self._items.append(item)
        self._relayout()

    def clear(self) -> None:
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child is None:
                break
            widget = child.widget()
            if widget is not None and widget.parent() is self:
                widget.setParent(None)  # type: ignore[call-overload]
                widget.deleteLater()
        self._items = []

    # --------------------------------------------------------------- layout --
    def column_count(self, width: int | None = None) -> int:
        """Columns for the given (or current) width."""
        available = width if width is not None else self.contentsRect().width()
        if available <= 0:
            return 1
        count = (available + self.gap) // (self.min_card_width + self.gap)
        return max(1, min(int(count), self.max_columns))

    def _relayout(self) -> None:
        while self.grid.count():
            child = self.grid.takeAt(0)
            if child is None:
                break
            if child.spacerItem() is not None:
                continue
            widget = child.widget()
            if widget is not None:
                self.grid.removeWidget(widget)
                widget.hide()
        if not self._items:
            return

        columns = self.column_count()
        rows = (len(self._items) + columns - 1) // columns
        for index, item in enumerate(self._items):
            row, column = divmod(index, columns)
            item.setParent(self)
            item.show()
            item.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self.grid.addWidget(item, row, column)
            self.grid.setColumnStretch(column, 1)

        # Centre the final (partial) row with elastic spacers.
        remainder = len(self._items) % columns
        if remainder:
            leading = (columns - remainder) // 2
            trailing = columns - remainder - leading
            if leading:
                self.grid.addItem(
                    QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum),
                    rows - 1,
                    0,
                )
            if trailing:
                self.grid.addItem(
                    QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum),
                    rows - 1,
                    columns - 1,
                )
        for column in range(columns):
            self.grid.setColumnStretch(column, 1)
        self.grid.setRowStretch(rows, 1)

    def resizeEvent(self, event) -> None:
        self._relayout()
        super().resizeEvent(event)


def density_for_width(width: int) -> str:
    """Return ``compact`` on small desktops so 1366×768 stays usable."""
    if width < BREAKPOINTS.xs:
        return "compact"
    if width < BREAKPOINTS.sm:
        return "compact"
    return "comfortable"
