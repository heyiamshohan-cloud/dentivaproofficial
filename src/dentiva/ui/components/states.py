"""State stack: loading / empty / error / no-permission / content.

Every screen that loads data owns one of these so that no region of the
application can ever show a blank white area that looks broken (REQ-STE-001).
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QScrollArea, QStackedLayout, QWidget

from dentiva.ui.components.feedback import EmptyState, ErrorState, LoadingState, NoPermissionState

State = str  # "content" | "loading" | "empty" | "error" | "no_permission"


class StateStack(QWidget):
    """Switches a content widget between the standard states."""

    stateChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.stack = QStackedLayout(self)
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.stack.setStackingMode(QStackedLayout.StackingMode.StackOne)

        self.content_widget: QWidget | None = None
        self.loading = LoadingState()
        self.empty = EmptyState()
        self.error = ErrorState()
        self.no_permission = NoPermissionState()

        self.stack.addWidget(self.loading)
        self.stack.addWidget(self.empty)
        self.stack.addWidget(self.error)
        self.stack.addWidget(self.no_permission)
        self._state: State = "loading"
        self.stack.setCurrentWidget(self.loading)

    # ------------------------------------------------------------------ API --
    def set_content(self, widget: QWidget) -> None:
        if self.content_widget is not None:
            self.stack.removeWidget(self.content_widget)
            self.content_widget.setParent(None)  # type: ignore[call-overload]
            self.content_widget.deleteLater()
        self.content_widget = widget
        self.stack.insertWidget(0, widget)
        self.show_content()

    def show_content(self) -> None:
        self._apply("content")

    def show_loading(self, message: str = "Loading…") -> None:
        self.loading.label.setText(message)
        self._apply("loading")

    def show_empty(
        self,
        title: str = "Nothing here yet",
        message: str = "Records you add will appear here.",
        *,
        icon_name: str = "file",
        action_label: str = "",
        on_action: Callable[[], None] | None = None,
    ) -> None:
        self.empty.icon_label.setPixmap(_icon(icon_name))
        self.empty.title_label.setText(title)
        self.empty.set_message(message)
        self._reconnect(self.empty, action_label, on_action)
        self._apply("empty")

    def show_error(
        self,
        message: str,
        *,
        title: str = "Something went wrong",
        detail: str = "",
        action_label: str = "Try again",
        on_retry: Callable[[], None] | None = None,
    ) -> None:
        self.error.title_label.setText(title)
        self.error.set_message(message)
        if self.error.detail_label is not None:
            self.error.detail_label.setText(detail)
            self.error.detail_label.setVisible(bool(detail))
        self._reconnect(self.error, action_label, on_retry)
        self._apply("error")

    def show_no_permission(self, message: str = "") -> None:
        if message:
            self.no_permission.set_message(message)
        self._apply("no_permission")

    @property
    def state(self) -> State:
        return self._state

    # --------------------------------------------------------------- internal --
    def _apply(self, state: State) -> None:
        changed = state != self._state
        self._state = state
        widget = {
            "content": self.content_widget,
            "loading": self.loading,
            "empty": self.empty,
            "error": self.error,
            "no_permission": self.no_permission,
        }[state]
        if widget is None:  # content requested before it exists
            widget = self.loading
            self._state = "loading"
        self.stack.setCurrentWidget(widget)
        if changed:
            self.stateChanged.emit(self._state)

    @staticmethod
    def _reconnect(target: QWidget, label: str, handler: Callable[[], None] | None) -> None:
        button = getattr(target, "action", None)
        if button is None:
            return
        button.setVisible(bool(label) and handler is not None)
        if label:
            button.setText(label)
        with suppress(RuntimeError, TypeError):  # no connections yet
            button.clicked.disconnect()
        if handler is not None:
            button.clicked.connect(handler)


def _icon(name: str):
    from dentiva.ui.theme import icons as icon_theme
    from dentiva.ui.theme.tokens import COLORS

    return icon_theme.pixmap(name, 40, COLORS.ink_muted)


class ScrollableContent(QScrollArea):
    """Scroll region with the correct frame-less, transparent presentation."""

    def __init__(self, widget: QWidget | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        if widget is not None:
            self.setWidget(widget)
