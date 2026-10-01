"""Tabs and segmented controls with perfectly aligned icon+text labels."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QTabWidget, QVBoxLayout, QWidget

from dentiva.ui.components.buttons import Button
from dentiva.ui.theme import icons
from dentiva.ui.theme.tokens import SPACING


class Tabs(QTabWidget):
    """Styled tab widget (icons and labels on a shared baseline)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setDocumentMode(False)
        self.setMovable(False)
        self.setUsesScrollButtons(True)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setIconSize(icons.icon_size(18))
        self.tabBar().setExpanding(False)

    def add_tab(self, widget: QWidget, label: str, *, icon_name: str | None = None) -> int:
        icon = icons.icon(icon_name, 18) if icon_name else icons.icon("file", 18)
        return self.addTab(widget, icon, label)


class SegmentedControl(QWidget):
    """Period/status filter control (Today · 7 days · 30 days · Custom …)."""

    selectionChanged = Signal(str)

    def __init__(
        self,
        options: Sequence[tuple[str, str]],
        *,
        value: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.options = list(options)
        self._value = value or (self.options[0][0] if self.options else "")
        self._buttons: dict[str, Button] = {}
        host = QWidget()
        host.setProperty("role", "card")
        host.setStyleSheet("background: #EDF2F5; border: none;")
        layout = QHBoxLayout(host)
        layout.setContentsMargins(SPACING.xxs, SPACING.xxs, SPACING.xxs, SPACING.xxs)
        layout.setSpacing(SPACING.xxs)
        for key, label in self.options:
            button = Button(label, variant="ghost", size="compact")
            button.setProperty("role", "segment")
            button.setProperty("segment-selected", "true" if key == self._value else "false")
            button.setCheckable(True)
            button.setChecked(key == self._value)
            button.clicked.connect(lambda _checked=False, key=key: self.set_value(key))
            layout.addWidget(button)
            self._buttons[key] = button
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(host)
        outer.addStretch(1)

    def set_value(self, value: str) -> None:
        if value == self._value:
            return
        self._value = value
        for key, button in self._buttons.items():
            selected = key == value
            button.setChecked(selected)
            button.setProperty("segment-selected", "true" if selected else "false")
            button.style().unpolish(button)
            button.style().polish(button)
        self.selectionChanged.emit(value)

    def value(self) -> str:
        return self._value


class VerticalTabs(QWidget):
    """Left-hand vertical tab list used by dense screens (settings, profile)."""

    currentChanged = Signal(str)

    def __init__(
        self,
        options: Sequence[tuple[str, str]],
        *,
        value: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.options = list(options)
        self._value = value or (self.options[0][0] if self.options else "")
        self._buttons: dict[str, Button] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING.xxs)
        for key, label in self.options:
            button = Button(label, variant="ghost")
            button.setProperty("role", "segment")
            button.setProperty("segment-selected", "true" if key == self._value else "false")
            button.clicked.connect(lambda _checked=False, key=key: self.set_value(key))
            layout.addWidget(button)
            self._buttons[key] = button
        layout.addStretch(1)

    def set_value(self, value: str) -> None:
        changed = value != self._value
        self._value = value
        for key, button in self._buttons.items():
            selected = key == value
            button.setProperty("segment-selected", "true" if selected else "false")
            button.style().unpolish(button)
            button.style().polish(button)
        if changed:
            self.currentChanged.emit(value)

    def value(self) -> str:
        return self._value
