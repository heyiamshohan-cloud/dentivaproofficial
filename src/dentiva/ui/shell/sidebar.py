"""Collapsible sidebar (REQ-SHL-003/004/006).

Both states are fully functional: expanded shows icon + label + group headings,
collapsed shows icons with tooltips (and keeps the same hit targets).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
)

from dentiva.ui.shell.navigation import NavItem, grouped
from dentiva.ui.theme import icons
from dentiva.ui.theme.tokens import COLORS, RADIUS, SIZE, SPACING, TYPE


class NavButton(QToolButton):
    """Sidebar entry: perfectly aligned icon + label, checkable selection."""

    def __init__(self, item: NavItem) -> None:
        super().__init__()
        self.item = item
        self.setCheckable(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setText(item.label)
        self.setIcon(icons.icon(item.icon, 18))
        self.setIconSize(icons.icon_size(18))
        self.setToolTip(item.label if item.label else "")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(38)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(
            f"""
            QToolButton {{
                background: transparent; border: none; border-radius: {RADIUS.control}px;
                padding: 0 {SPACING.md}px; text-align: left; color: {COLORS.ink_secondary};
                font-size: {TYPE.size_body}px; font-weight: {TYPE.weight_medium};
            }}
            QToolButton:hover {{ background: {COLORS.hover_soft}; color: {COLORS.ink}; }}
            QToolButton:checked {{ background: {COLORS.primary_soft}; color: {COLORS.primary};
                font-weight: 600; }}
            QToolButton:focus-visible {{ border: 1px solid {COLORS.focus_ring}; }}
            """
        )

    def set_collapsed(self, collapsed: bool) -> None:
        """Switch between icon+label and icon-only presentation."""
        self.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
            if collapsed
            else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        if collapsed:
            self.setText("")
            self.setFixedSize(40, 38)
            self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        else:
            self.setText(self.item.label)
            self.setFixedHeight(38)
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class Sidebar(QFrame):
    """Navigation sidebar with group headings and a collapse toggle."""

    navigate = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setProperty("role", "sidebar")
        self.setMinimumWidth(SIZE.sidebar_width_collapsed)
        self._collapsed = False
        self._buttons: dict[str, NavButton] = {}
        self._group_labels: list[QLabel] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(SPACING.sm, SPACING.md, SPACING.sm, SPACING.md)
        root.setSpacing(SPACING.xs)

        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(0, 0, 0, 0)
        self.toggle = QToolButton()
        self.toggle.setIcon(icons.icon("chevronLeft", 18))
        self.toggle.setIconSize(icons.icon_size(18))
        self.toggle.setToolTip("Collapse sidebar  (Ctrl+B)")
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle.setFixedSize(36, 36)
        self.toggle.setStyleSheet(
            f"QToolButton {{ border: none; border-radius: {RADIUS.control}px;\n"
            "                background: transparent; }\n"
            f"QToolButton:hover {{ background: {COLORS.hover_soft}; }}"
        )
        self.toggle.clicked.connect(lambda: self.set_collapsed(not self._collapsed))
        toggle_row.addWidget(self.toggle)
        toggle_row.addStretch(1)
        root.addLayout(toggle_row)
        root.addSpacing(SPACING.xs)

        for group, items in grouped():
            label = QLabel(group.upper())
            label.setProperty("role", "caption")
            label.setStyleSheet(
                f"color: {COLORS.ink_muted}; font-size: 10px; letter-spacing: 0.08em;"
            )
            label.setContentsMargins(SPACING.md, SPACING.sm, 0, SPACING.xs)
            root.addWidget(label)
            self._group_labels.append(label)
            for item in items:
                button = NavButton(item)
                button.clicked.connect(
                    lambda _checked=False, item=item: self.navigate.emit(item.id)
                )
                root.addWidget(button)
                self._buttons[item.id] = button
            root.addSpacing(SPACING.xs)

        root.addStretch(1)

    # ------------------------------------------------------------------ API --
    @property
    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        for label in self._group_labels:
            label.setVisible(not collapsed)
        for button in self._buttons.values():
            button.set_collapsed(collapsed)
        self.toggle.setIcon(icons.icon("chevronRight" if collapsed else "chevronLeft", 18))
        self.toggle.setToolTip(
            "Expand sidebar  (Ctrl+B)" if collapsed else "Collapse sidebar  (Ctrl+B)"
        )
        self.setFixedWidth(SIZE.sidebar_width_collapsed if collapsed else SIZE.sidebar_width)

    def set_active(self, item_id: str) -> None:
        for key, button in self._buttons.items():
            button.setChecked(key == item_id)

    def buttons(self) -> dict[str, NavButton]:
        return dict(self._buttons)

    def items(self) -> list[NavItem]:
        return [button.item for button in self._buttons.values()]
