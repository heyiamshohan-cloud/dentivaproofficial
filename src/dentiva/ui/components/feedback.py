"""Feedback components: empty/error/no-permission states, banners, toasts, loaders."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from dentiva.ui.components.buttons import Button
from dentiva.ui.theme import icons
from dentiva.ui.theme.tokens import COLORS, MOTION, RADIUS, SPACING


class PlaceholderState(QWidget):
    """Base class for the designed placeholder states (REQ-STE-001)."""

    actionRequested = Signal()

    def __init__(
        self,
        icon_name: str,
        title: str,
        message: str,
        *,
        action_label: str = "",
        tone: str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.tone = tone
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING.xxl, SPACING.xxl, SPACING.xxl, SPACING.xxl)
        layout.setSpacing(SPACING.md)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel()
        self.icon_label.setPixmap(icons.pixmap(icon_name, 40, COLORS.ink_muted))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setProperty("role", "emptyIcon")
        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignCenter)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.message_label = QLabel(message)
        self.message_label.setProperty("role", "caption")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        self.message_label.setMaximumWidth(420)
        layout.addWidget(self.message_label)

        self.action: Button | None
        if action_label:
            self.action = Button(action_label, variant="primary")
            self.action.clicked.connect(self.actionRequested.emit)
            layout.addWidget(self.action, 0, Qt.AlignmentFlag.AlignCenter)
        else:
            self.action = None

    def set_message(self, message: str) -> None:
        self.message_label.setText(message)


class EmptyState(PlaceholderState):
    """No data yet — explains what will appear here and offers the next action."""

    def __init__(
        self,
        title: str = "Nothing here yet",
        message: str = "Records you add will appear here.",
        *,
        icon_name: str = "file",
        action_label: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(icon_name, title, message, action_label=action_label, parent=parent)


class ErrorState(PlaceholderState):
    """Recoverable error with a retry action and expandable technical detail."""

    def __init__(
        self,
        title: str = "Something went wrong",
        message: str = "The information could not be loaded.",
        *,
        detail: str = "",
        action_label: str = "Try again",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            "error", title, message, action_label=action_label, tone="danger", parent=parent
        )
        self.icon_label.setPixmap(icons.pixmap("error", 40, COLORS.danger))
        self.detail_label: QLabel | None
        if detail:
            self.detail_label = QLabel(detail)
            self.detail_label.setProperty("role", "caption")
            self.detail_label.setWordWrap(True)
            self.detail_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            container = self.layout()
            if container is not None:
                container.addWidget(self.detail_label)
        else:
            self.detail_label = None


class NoPermissionState(PlaceholderState):
    """Shown when the signed-in user lacks the permission for this screen."""

    def __init__(
        self,
        title: str = "You do not have access to this area",
        message: str = "Ask an administrator if your role should include this permission.",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("lock", title, message, parent=parent)
        self.icon_label.setPixmap(icons.pixmap("lock", 40, COLORS.warning))


class LoadingState(QWidget):
    """Skeleton/spinner placeholder shown while data is being fetched."""

    def __init__(
        self, message: str = "Loading…", *, rows: int = 4, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING.xxl, SPACING.xxl, SPACING.xxl, SPACING.xxl)
        layout.setSpacing(SPACING.md)
        self.spinner = QProgressBar()
        self.spinner.setRange(0, 0)
        self.spinner.setFixedWidth(180)
        layout.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel(message)
        self.label.setProperty("role", "caption")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        for _ in range(rows):
            bar = QFrame()
            bar.setProperty("role", "skeleton")
            bar.setFixedHeight(14)
            bar.setStyleSheet(
                f"background: {COLORS.surface_sunken}; border-radius: {RADIUS.control}px;"
            )
            layout.addWidget(bar)
        layout.addStretch(1)


class Banner(QFrame):
    """Inline message strip (info/success/warning/danger) with optional action."""

    dismissed = Signal()

    def __init__(
        self,
        message: str,
        *,
        tone: str = "info",
        action_label: str = "",
        dismissible: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "banner")
        self.setProperty("tone", tone)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING.md, SPACING.sm, SPACING.md, SPACING.sm)
        layout.setSpacing(SPACING.sm)

        icon_name = {
            "info": "info",
            "success": "check",
            "warning": "warning",
            "danger": "error",
        }.get(tone, "info")
        icon = QLabel()
        icon.setPixmap(icons.pixmap(icon_name, 16))
        icon.setFixedWidth(18)
        layout.addWidget(icon, 0, Qt.AlignmentFlag.AlignVCenter)

        self.message_label = QLabel(message)
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.message_label, 1, Qt.AlignmentFlag.AlignVCenter)

        self.action: Button | None
        if action_label:
            self.action = Button(action_label, variant="ghost", size="compact")
            layout.addWidget(self.action, 0, Qt.AlignmentFlag.AlignVCenter)
        else:
            self.action = None
        if dismissible:
            close = Button("Dismiss", variant="ghost", size="compact")
            close.clicked.connect(self._dismiss)
            layout.addWidget(close, 0, Qt.AlignmentFlag.AlignVCenter)

    def _dismiss(self) -> None:
        self.hide()
        self.dismissed.emit()

    def set_message(self, message: str) -> None:
        self.message_label.setText(message)


class Toast(QFrame):
    """Transient notification that slides in and fades out (REQ-UIX-007)."""

    closed = Signal()

    def __init__(
        self,
        message: str,
        *,
        tone: str = "success",
        timeout_ms: int = 3200,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setProperty("role", "banner")
        self.setProperty("tone", tone)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING.md, SPACING.sm, SPACING.md, SPACING.sm)
        icon = QLabel()
        icon.setPixmap(
            icons.pixmap(
                {"success": "check", "error": "error", "warning": "warning"}.get(tone, "info"), 16
            )
        )
        layout.addWidget(icon)
        self.label = QLabel(message)
        self.label.setWordWrap(True)
        layout.addWidget(self.label, 1)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._animation = QPropertyAnimation(self._effect, b"opacity", self)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.timeout_ms = timeout_ms

    def show_animated(self) -> None:
        self._effect.setOpacity(0.0)
        self.show()
        self._animation.setDuration(MOTION.panel_ms)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.start()
        self._animation.finished.connect(self._schedule_hide)

    def _schedule_hide(self) -> None:
        with suppress(RuntimeError, TypeError):  # no connections yet
            self._animation.finished.disconnect(self._schedule_hide)
        from PySide6.QtCore import QTimer

        QTimer.singleShot(self.timeout_ms, self.hide_animated)

    def hide_animated(self) -> None:
        self._animation.setDuration(MOTION.standard_ms)
        self._animation.setStartValue(1.0)
        self._animation.setEndValue(0.0)
        self._animation.start()
        self._animation.finished.connect(self._finish)

    def _finish(self) -> None:
        with suppress(RuntimeError, TypeError):  # already disconnected
            self._animation.finished.disconnect(self._finish)
        self.hide()
        self.closed.emit()


class ToastHost(QWidget):
    """Bottom-right stack that owns and positions toasts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(SPACING.lg, SPACING.lg, SPACING.lg, SPACING.lg)
        self.layout_.setSpacing(SPACING.sm)
        self.layout_.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        self._toasts: list[Toast] = []

    def notify(self, message: str, *, tone: str = "success", timeout_ms: int = 3200) -> Toast:
        toast = Toast(message, tone=tone, timeout_ms=timeout_ms, parent=self)
        toast.closed.connect(lambda: self._remove(toast))
        self.layout_.addWidget(toast, 0, Qt.AlignmentFlag.AlignRight)
        self._toasts.append(toast)
        toast.show_animated()
        return toast

    def _remove(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        self.layout_.removeWidget(toast)
        toast.deleteLater()

    def clear(self) -> None:
        for toast in list(self._toasts):
            self._remove(toast)

    def make_handler(self) -> Callable[[str, str], None]:
        """Return a ``notify(message, tone)`` helper for services and controllers."""

        def handler(message: str, tone: str = "success") -> None:
            self.notify(message, tone=tone)

        return handler
