"""Display primitives: avatars, chips, badges, key/value grids and dividers."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from dentiva.core.textutil import initials
from dentiva.ui.theme import icons
from dentiva.ui.theme.tokens import COLORS, SIZE, SPACING, status_color, status_soft


class Divider(QFrame):
    """Hairline separator (horizontal or vertical)."""

    def __init__(self, orientation: str = "horizontal", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "divider")
        self.setFrameShape(
            QFrame.Shape.HLine if orientation == "horizontal" else QFrame.Shape.VLine
        )
        self.setFixedHeight(1 if orientation == "horizontal" else 0)
        if orientation == "vertical":
            self.setFixedWidth(1)


class Avatar(QLabel):
    """Initials avatar with a deterministic colour derived from the name."""

    _PALETTE = (
        (COLORS.primary_soft, COLORS.primary),
        (COLORS.info_soft, COLORS.info),
        (COLORS.success_soft, COLORS.success),
        (COLORS.warning_soft, COLORS.warning),
    )

    def __init__(
        self, name: str, *, size: int = SIZE.avatar, parent: QWidget | None = None
    ) -> None:
        super().__init__(initials(name), parent)
        self.setProperty("role", "avatar")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(size, size)
        background, foreground = self._PALETTE[sum(map(ord, name or "?")) % len(self._PALETTE)]
        self.setStyleSheet(
            f"background: {background}; color: {foreground}; border-radius: {size // 2}px; "
            f"font-weight: 600; font-size: {max(10, size // 3)}px;"
        )


class Badge(QLabel):
    """Compact status indicator (colour + text, never colour alone)."""

    def __init__(self, text: str, *, tone: str = "neutral", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("role", "badge")
        self.setProperty("tone", tone)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        self.style().unpolish(self)
        self.style().polish(self)


class StatusPill(Badge):
    """Badge whose tone is derived from a domain status name."""

    def __init__(self, status: str, parent: QWidget | None = None) -> None:
        super().__init__(status.title(), tone=_tone_for(status), parent=parent)
        self.status = status

    def set_status(self, status: str) -> None:
        self.status = status
        self.setText(status.title())
        self.set_tone(_tone_for(status))


def _tone_for(status: str) -> str:
    mapping = {
        "paid": "success",
        "completed": "success",
        "confirmed": "success",
        "active": "success",
        "ok": "success",
        "partial": "warning",
        "due": "warning",
        "pending": "warning",
        "waiting": "warning",
        "scheduled": "info",
        "in_consultation": "info",
        "arrived": "info",
        "overdue": "danger",
        "missed": "danger",
        "failed": "danger",
        "void": "danger",
        "cancelled": "neutral",
        "skipped": "neutral",
        "draft": "neutral",
    }
    return mapping.get(status.lower(), "neutral")


class Chip(QLabel):
    """Neutral tag (patient tags, categories, filters)."""

    def __init__(
        self, text: str, *, removable: bool = False, parent: QWidget | None = None
    ) -> None:
        super().__init__(text, parent)
        self.setProperty("role", "chip")
        self.removable = removable
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)


class IconText(QWidget):
    """Icon and label on one baseline — guaranteed vertical centring."""

    def __init__(
        self,
        icon_name: str,
        text: str,
        *,
        icon_size: int = 16,
        color: str | None = None,
        role: str = "caption",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.icon_label = QLabel()
        self.icon_label.setPixmap(icons.pixmap(icon_name, icon_size, color or COLORS.ink_muted))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.icon_label.setFixedSize(icon_size + 2, icon_size + 2)
        self.text_label = QLabel(text)
        self.text_label.setProperty("role", role)
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING.xs + 2)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch(1)

    def setText(self, text: str) -> None:
        self.text_label.setText(text)

    def text(self) -> str:
        return self.text_label.text()


class KeyValueGrid(QWidget):
    """Two-column label/value grid (patient summaries, invoice totals)."""

    def __init__(
        self, *, columns: int = 2, spacing: int = SPACING.md, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(spacing)
        self.grid.setVerticalSpacing(SPACING.sm)
        self.columns = columns
        self._row = 0
        self._column = 0

    def add(
        self, label: str, value: str, *, emphasise: bool = False, tone: str | None = None
    ) -> None:
        key = QLabel(label)
        key.setProperty("role", "caption")
        key.setWordWrap(True)
        val = QLabel(value)
        val.setWordWrap(True)
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if emphasise:
            val.setStyleSheet("font-weight: 600; font-size: 15px;")
        if tone:
            val.setStyleSheet(f"color: {status_color(tone)}; font-weight: 600;")
        column = self._column * 2
        self.grid.addWidget(key, self._row, column)
        self.grid.addWidget(val, self._row, column + 1)
        self._column += 1
        if self._column >= self.columns:
            self._column = 0
            self._row += 1

    def add_row(self, label: str, value: str, **kwargs: object) -> None:
        """Force a new grid row before adding the pair."""
        if self._column:
            self._column = 0
            self._row += 1
        self.add(label, value, **kwargs)  # type: ignore[arg-type]

    def finish(self) -> None:
        """Balance the last row so columns stay aligned."""
        if self._column:
            self.grid.setColumnStretch(self._column * 2 + 1, 1)
        self.grid.setColumnStretch(self.columns * 2 - 1, 1)


class StatTile(QWidget):
    """Compact statistic with an icon, label, value and optional caption."""

    def __init__(
        self,
        label: str,
        value: str,
        *,
        icon_name: str | None = None,
        caption: str = "",
        tone: str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.tone = tone
        container = QFrame(self)
        container.setProperty("role", "card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        inner = QHBoxLayout(container)
        inner.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        inner.setSpacing(SPACING.md)

        text_column = QVBoxLayout()
        text_column.setSpacing(SPACING.xxs)
        caption_label = QLabel(label)
        caption_label.setProperty("role", "caption")
        value_label = QLabel(value)
        value_label.setProperty("role", "display")
        text_column.addWidget(caption_label)
        text_column.addWidget(value_label)
        if caption:
            hint = QLabel(caption)
            hint.setProperty("role", "caption")
            text_column.addWidget(hint)
        text_column.addStretch(1)
        inner.addLayout(text_column, 1)

        if icon_name:
            icon_host = QFrame()
            icon_host.setFixedSize(40, 40)
            icon_host.setStyleSheet(
                f"background: {status_soft(tone)}; border-radius: 10px;"
                if tone != "neutral"
                else f"background: {COLORS.surface_sunken}; border-radius: 10px;"
            )
            icon_layout = QVBoxLayout(icon_host)
            icon_layout.setContentsMargins(0, 0, 0, 0)
            icon = QLabel()
            icon.setPixmap(icons.pixmap(icon_name, 20, status_color(tone)))
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_layout.addWidget(icon)
            inner.addWidget(icon_host, 0, Qt.AlignmentFlag.AlignTop)

        layout.addWidget(container)
        self.value_label = value_label
        self.label_widget = caption_label

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)
