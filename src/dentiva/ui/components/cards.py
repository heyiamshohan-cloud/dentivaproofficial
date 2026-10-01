"""Cards: the primary content container of every screen."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from dentiva.ui.theme.tokens import RADIUS, SPACING, TYPE


class Card(QFrame):
    """Surface with an optional title, subtitle and action area."""

    def __init__(
        self,
        title: str = "",
        *,
        subtitle: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(SPACING.lg, SPACING.lg, SPACING.lg, SPACING.lg)
        self.outer.setSpacing(SPACING.md)

        self.header = QHBoxLayout()
        self.header.setSpacing(SPACING.sm)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"font-size: {TYPE.size_subtitle}px; font-weight: 600;")
        self.title_label.setWordWrap(True)
        self.header.addWidget(self.title_label, 1)
        self.action_row = QHBoxLayout()
        self.action_row.setSpacing(SPACING.xs)
        self.header.addLayout(self.action_row, 0)
        if title:
            self.outer.addLayout(self.header)
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setProperty("role", "caption")
            self.subtitle_label.setWordWrap(True)
            self.outer.addWidget(self.subtitle_label)

        self.body = QVBoxLayout()
        self.body.setSpacing(SPACING.md)
        self.outer.addLayout(self.body, 1)

    def set_title(self, title: str) -> None:
        self.title_label.setText(title)

    def add_widget(self, widget: QWidget, stretch: int = 0) -> None:
        self.body.addWidget(widget, stretch)

    def add_layout(self, layout: QHBoxLayout | QVBoxLayout, stretch: int = 0) -> None:
        self.body.addLayout(layout, stretch)

    def add_stretch(self, stretch: int = 1) -> None:
        self.body.addStretch(stretch)

    def add_action(self, widget: QWidget) -> None:
        self.action_row.addWidget(widget)


class SectionCard(Card):
    """Card with a leading accent bar, used for grouped settings and summaries."""

    def __init__(
        self, title: str = "", *, subtitle: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(title, subtitle=subtitle, parent=parent)
        self.setStyleSheet(f"QFrame[role='card'] {{ border-radius: {RADIUS.card}px; }}")


class StatCard(QFrame):
    """Dashboard tile: label, value, delta and icon (equal height in a grid row)."""

    clicked = Signal()

    def __init__(
        self,
        label: str,
        value: str = "0",
        *,
        caption: str = "",
        icon_name: str | None = None,
        trend: str = "",
        tone: str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumHeight(112)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        layout.setSpacing(SPACING.xs)

        top = QHBoxLayout()
        top.setSpacing(SPACING.sm)
        self.label_widget = QLabel(label)
        self.label_widget.setProperty("role", "caption")
        self.label_widget.setWordWrap(True)
        top.addWidget(self.label_widget, 1)
        if icon_name:
            from dentiva.ui.theme import icons as icon_theme

            icon = QLabel()
            icon.setPixmap(icon_theme.pixmap(icon_name, 18))
            icon.setFixedSize(20, 20)
            top.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(top)

        self.value_label = QLabel(value)
        self.value_label.setProperty("role", "display")
        self.value_label.setWordWrap(True)
        layout.addWidget(self.value_label)

        self.caption_widget = QLabel(caption)
        self.caption_widget.setProperty("role", "caption")
        self.caption_widget.setWordWrap(True)
        self.caption_widget.setVisible(bool(caption))
        layout.addWidget(self.caption_widget)

        self.trend_widget = QLabel(trend)
        self.trend_widget.setProperty("role", "caption")
        self.trend_widget.setVisible(bool(trend))
        layout.addWidget(self.trend_widget)
        layout.addStretch(1)

    def set_value(self, value: str, *, caption: str | None = None) -> None:
        self.value_label.setText(value)
        if caption is not None:
            self.caption_widget.setText(caption)
            self.caption_widget.setVisible(bool(caption))


class ActionCard(QFrame):
    """Quick-action tile used on the dashboard."""

    clicked = Signal()

    def __init__(
        self, label: str, icon_name: str, *, description: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(96)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        layout.setSpacing(SPACING.xs)
        from dentiva.ui.theme import icons as icon_theme

        icon = QLabel()
        icon.setPixmap(icon_theme.pixmap(icon_name, 20))
        icon.setFixedSize(22, 22)
        layout.addWidget(icon)
        title = QLabel(label)
        title.setStyleSheet("font-weight: 600;")
        title.setWordWrap(True)
        layout.addWidget(title)
        if description:
            hint = QLabel(description)
            hint.setProperty("role", "caption")
            hint.setWordWrap(True)
            layout.addWidget(hint)
        layout.addStretch(1)

    def mouseReleaseEvent(self, event) -> None:
        self.clicked.emit()
        super().mouseReleaseEvent(event)
