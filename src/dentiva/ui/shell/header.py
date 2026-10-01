"""Global header (REQ-SHL-002).

Contents: Dentiva Pro identity, the configured clinic name, the current date, and
the session area. Elements that belong to later phases (notification centre, user
menu) are added by those phases — nothing is rendered inert in the meantime.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from dentiva.core.clock import local_now
from dentiva.ui.theme import icons
from dentiva.ui.theme.tokens import COLORS, SIZE, SPACING, TYPE


class Header(QFrame):
    """Application header bar."""

    lockRequested = Signal()
    settingsRequested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setProperty("role", "header")
        self.setFixedHeight(SIZE.header_height)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING.xl, SPACING.sm, SPACING.xl, SPACING.sm)
        layout.setSpacing(SPACING.md)

        # ---------------------------------------------------------- identity --
        brand = QHBoxLayout()
        brand.setSpacing(SPACING.sm)
        logo = QLabel()
        logo.setPixmap(icons.pixmap("treatments", 24, COLORS.primary))
        logo.setFixedSize(26, 26)
        brand.addWidget(logo)
        name = QLabel("Dentiva Pro")
        name.setStyleSheet(f"font-size: {TYPE.size_subtitle}px; font-weight: 600;")
        brand.addWidget(name)
        layout.addLayout(brand)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet(f"color: {COLORS.border};")
        divider.setFixedHeight(28)
        layout.addWidget(divider)

        # ------------------------------------------------------------ clinic --
        clinic_column = QVBoxLayout()
        clinic_column.setSpacing(0)
        self.clinic_name = QLabel("Clinic not configured")
        self.clinic_name.setStyleSheet(f"font-weight: {TYPE.weight_medium};")
        self.clinic_name.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        clinic_caption = QLabel("Complete first-run setup to name your clinic")
        clinic_caption.setProperty("role", "caption")
        clinic_column.addWidget(self.clinic_name)
        clinic_column.addWidget(clinic_caption)
        layout.addLayout(clinic_column)

        layout.addStretch(1)

        # -------------------------------------------------------------- date --
        date_column = QVBoxLayout()
        date_column.setSpacing(0)
        self.date_label = QLabel(self._format_date(local_now().date()))
        self.date_label.setStyleSheet(f"font-weight: {TYPE.weight_medium};")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.weekday_label = QLabel(local_now().strftime("%A"))
        self.weekday_label.setProperty("role", "caption")
        self.weekday_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        date_column.addWidget(self.date_label)
        date_column.addWidget(self.weekday_label)
        layout.addLayout(date_column)

        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self._refresh_date)
        self._timer.start()

    def _refresh_date(self) -> None:
        now = local_now()
        self.date_label.setText(self._format_date(now.date()))
        self.weekday_label.setText(now.strftime("%A"))

    @staticmethod
    def _format_date(value: date) -> str:
        qdate = QDate(value.year, value.month, value.day)
        return qdate.toString("dd MMM yyyy")

    def set_clinic_name(self, name: str) -> None:
        """Update the clinic identity shown in the header (Phase 5 wires this)."""
        self.clinic_name.setText(name or "Clinic not configured")
