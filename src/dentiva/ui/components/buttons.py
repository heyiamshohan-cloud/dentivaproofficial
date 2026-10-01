"""Buttons: variants, sizes, icon buttons and busy state.

Variants are selected with the ``variant`` Qt property consumed by the generated
stylesheet: ``primary`` (default action), ``secondary`` (default look),
``ghost`` (borderless), ``subtle`` (filled grey), ``soft`` (tinted brand) and
``danger`` (destructive).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QToolButton, QWidget

from dentiva.ui.theme import icons

ButtonVariant = str  # "primary" | "secondary" | "ghost" | "subtle" | "soft" | "danger"


class Button(QPushButton):
    """Primary interaction control with a complete state matrix."""

    def __init__(
        self,
        text: str = "",
        *,
        variant: ButtonVariant = "secondary",
        icon_name: str | None = None,
        size: str = "default",
        tooltip: str = "",
        shortcut: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.variant = variant
        self._icon_name = icon_name
        self._busy = False
        self._idle_text = text
        self.setProperty("variant", variant)
        if size != "default":
            self.setProperty("size", size)
        if icon_name:
            self.setIcon(icons.icon(icon_name, 18))
        if tooltip:
            self.setToolTip(tooltip)
        if shortcut:
            self.setShortcut(shortcut)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ------------------------------------------------------------------ state --
    def set_variant(self, variant: ButtonVariant) -> None:
        self.variant = variant
        self.setProperty("variant", variant)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_busy(self, busy: bool, *, busy_text: str = "Working…") -> None:
        """Loading state: disabled with an explanatory label (never a dead button)."""
        if busy == self._busy:
            return
        self._busy = busy
        if busy:
            self._idle_text = self.text()
            self.setText(busy_text)
        else:
            self.setText(self._idle_text)
        self.setDisabled(busy)
        self.repaint()

    @property
    def is_busy(self) -> bool:
        return self._busy

    def set_enabled(self, enabled: bool, *, reason: str = "") -> None:
        """Disable with an explanation rendered as a tooltip (REQ-UIX-008)."""
        self.setEnabled(enabled)
        if reason and not enabled:
            self.setToolTip(reason)
        elif not reason:
            self.setToolTip("")


class IconButton(QToolButton):
    """Square icon-only button (optically centred icon, 32 px minimum target)."""

    def __init__(
        self,
        icon_name: str,
        *,
        tooltip: str = "",
        size: int = 32,
        icon_size: int = 18,
        checkable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.icon_name = icon_name
        self.setProperty("role", "icon")
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setIcon(icons.icon(icon_name, icon_size))
        self.setIconSize(icons.icon_size(icon_size))
        self.setFixedSize(size, size)
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_icon(self, icon_name: str, icon_size: int = 18) -> None:
        self.icon_name = icon_name
        self.setIcon(icons.icon(icon_name, icon_size))


class SplitButton(QWidget):
    """Primary action with a secondary menu button (for example Print ▾)."""

    actionTriggered = Signal()
    menuTriggered = Signal()

    def __init__(
        self,
        text: str,
        *,
        variant: ButtonVariant = "primary",
        icon_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.main = Button(text, variant=variant, icon_name=icon_name)
        self.menu_button = IconButton(
            "chevronDown", tooltip=f"More {text.lower()} options", size=30
        )
        self.main.clicked.connect(self.actionTriggered.emit)
        self.menu_button.clicked.connect(self.menuTriggered.emit)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.main)
        layout.addWidget(self.menu_button)

    def set_busy(self, busy: bool) -> None:
        self.main.set_busy(busy)
        self.menu_button.setDisabled(busy)


class ButtonRow(QWidget):
    """Right-aligned dialog/button row with consistent spacing."""

    def __init__(
        self, *buttons: Button, align: str = "right", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        if align in ("right", "center"):
            layout.addStretch(1)
        for index, button in enumerate(buttons):
            layout.addWidget(button)
            if index != len(buttons) - 1:
                layout.setSpacing(8)
        if align == "center":
            layout.addStretch(1)
