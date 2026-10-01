"""Designed state for a module that is scheduled for a later phase.

This is **not** a placeholder screen shipped as product: it is a build-state
indicator. ``tests/ui/test_navigation_matrix.py`` fails the build as soon as
``CURRENT_PHASE`` reaches a module's phase and the real screen is not wired in,
so no module can remain pending at release.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from dentiva.ui.shell.navigation import NavItem
from dentiva.ui.theme import icons
from dentiva.ui.theme.tokens import COLORS, RADIUS, SPACING, TYPE


class ModulePendingView(QWidget):
    """Explains what the module will contain and when it is delivered."""

    def __init__(self, item: NavItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item = item
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING.xxl, SPACING.xxl, SPACING.xxl, SPACING.xxl)
        layout.setSpacing(SPACING.lg)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        card = QFrame()
        card.setProperty("role", "card")
        card.setMaximumWidth(560)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(SPACING.xxl, SPACING.xl, SPACING.xxl, SPACING.xl)
        card_layout.setSpacing(SPACING.md)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        icon = QLabel()
        icon.setPixmap(icons.pixmap(item.icon, 32, COLORS.primary))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(icon)

        title = QLabel(item.label)
        title.setStyleSheet(f"font-size: {TYPE.size_title}px; font-weight: 600;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)

        description = QLabel(
            item.description or "This module is part of the Dentiva Pro build plan."
        )
        description.setProperty("role", "caption")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(description)

        phase = QLabel(f"Scheduled for Phase {item.phase} of the Dentiva Pro build plan")
        phase.setStyleSheet(
            f"background: {COLORS.primary_soft}; color: {COLORS.primary}; padding: 6px 12px; "
            f"border-radius: {RADIUS.pill // 20}px; font-weight: 600;"
        )
        phase.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(phase, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
