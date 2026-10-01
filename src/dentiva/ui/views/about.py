"""About screen (REQ-ABT): product identity, creator and licence information."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from dentiva import __contact__, __product_name__, __version__
from dentiva.buildinfo import BUILD
from dentiva.core.paths import assets_root
from dentiva.ui.components.buttons import Button
from dentiva.ui.components.display import KeyValueGrid
from dentiva.ui.theme import icons
from dentiva.ui.theme.tokens import COLORS, RADIUS, SPACING, TYPE


class AboutView(QWidget):
    """Product information, deliberately free of unnecessary internal detail."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SPACING.xxl, SPACING.xl, SPACING.xxl, SPACING.xl)
        outer.setSpacing(SPACING.lg)

        hero = QFrame()
        hero.setProperty("role", "card")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(SPACING.xxl, SPACING.xxl, SPACING.xxl, SPACING.xxl)
        hero_layout.setSpacing(SPACING.md)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        logo = QLabel()
        logo_path = assets_root() / "icons" / "dentiva.png"
        if logo_path.is_file():
            from PySide6.QtGui import QPixmap

            pixmap = QPixmap(str(logo_path))
            logo.setPixmap(
                pixmap.scaled(
                    96,
                    96,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            logo.setPixmap(icons.pixmap("treatments", 72, COLORS.primary))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(logo)

        name = QLabel(__product_name__)
        name.setStyleSheet(f"font-size: {TYPE.size_headline}px; font-weight: 600;")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(name)

        tagline = QLabel("Offline dental clinic management for Bangladesh")
        tagline.setProperty("role", "caption")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(tagline)

        version = QLabel(f"Version {__version__}")
        version.setStyleSheet(
            f"background: {COLORS.primary_soft}; color: {COLORS.primary}; padding: 4px 12px; "
            f"border-radius: {RADIUS.pill // 20}px; font-weight: 600;"
        )
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(version, 0, Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(hero)

        creator = QFrame()
        creator.setProperty("role", "card")
        creator_layout = QVBoxLayout(creator)
        creator_layout.setContentsMargins(SPACING.xl, SPACING.lg, SPACING.xl, SPACING.lg)
        creator_layout.setSpacing(SPACING.md)

        heading = QLabel("Created by")
        heading.setStyleSheet(f"font-size: {TYPE.size_subtitle}px; font-weight: 600;")
        creator_layout.addWidget(heading)

        author = QLabel("Shohan Khan")
        author.setStyleSheet(f"font-size: {TYPE.size_title}px; font-weight: 600;")
        creator_layout.addWidget(author)

        email_row = QVBoxLayout()
        email_row.setSpacing(SPACING.xs)
        email_label = QLabel("Email")
        email_label.setProperty("role", "caption")
        email_row.addWidget(email_label)
        self.email_button = Button(__contact__, variant="ghost", icon_name="file")
        self.email_button.setStyleSheet(f"color: {COLORS.primary}; text-decoration: underline;")
        self.email_button.clicked.connect(self._open_email)
        email_row.addWidget(self.email_button, 0, Qt.AlignmentFlag.AlignLeft)
        creator_layout.addLayout(email_row)
        outer.addWidget(creator)

        notices = QFrame()
        notices.setProperty("role", "card")
        notices_layout = QVBoxLayout(notices)
        notices_layout.setContentsMargins(SPACING.xl, SPACING.lg, SPACING.xl, SPACING.lg)
        notices_layout.setSpacing(SPACING.sm)

        notices_heading = QLabel("Third-party notices")
        notices_heading.setStyleSheet(f"font-size: {TYPE.size_subtitle}px; font-weight: 600;")
        notices_layout.addWidget(notices_heading)

        credits = QLabel(
            "PySide6 and Qt (LGPLv3) · SQLAlchemy, Alembic, argon2-cffi, openpyxl (MIT) · "
            "Pillow (HPND) · Noto Sans and Noto Sans Bengali (SIL OFL 1.1)."
        )
        credits.setProperty("role", "caption")
        credits.setWordWrap(True)
        notices_layout.addWidget(credits)

        self.notices_button = Button(
            "Open licence notices", variant="ghost", size="compact", icon_name="file"
        )
        self.notices_button.clicked.connect(self._open_notices)
        notices_layout.addWidget(self.notices_button, 0, Qt.AlignmentFlag.AlignLeft)
        outer.addWidget(notices)

        details = QFrame()
        details.setProperty("role", "card")
        details_layout = QVBoxLayout(details)
        details_layout.setContentsMargins(SPACING.xl, SPACING.lg, SPACING.xl, SPACING.lg)
        details_layout.setSpacing(SPACING.md)
        self.details_toggle = Button("Show system details", variant="ghost", size="compact")
        self.details_toggle.clicked.connect(self._toggle_details)
        self.system_grid = KeyValueGrid(columns=2)
        self.system_grid.add("Product", __product_name__)
        self.system_grid.add("Version", __version__)
        self.system_grid.add("Build", BUILD.channel)
        self.system_grid.add("Commit", BUILD.git_commit)
        self.system_grid.add("Built", BUILD.build_date)
        self.system_grid.add("Python", BUILD.python_version)
        self.system_grid.add("Qt", BUILD.qt_version)
        self.system_grid.finish()
        self.system_grid.setVisible(False)
        details_layout.addWidget(self.details_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        details_layout.addWidget(self.system_grid)
        outer.addWidget(details)

        outer.addStretch(1)

        footer = QLabel(
            f"© {BUILD.build_date[:4] if BUILD.build_date[:4].isdigit() else '2026'} Shohan Khan. "
            "All rights reserved."
        )
        footer.setProperty("role", "caption")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(footer)

    def _toggle_details(self) -> None:
        visible = not self.system_grid.isVisible()
        self.system_grid.setVisible(visible)
        self.details_toggle.setText("Hide system details" if visible else "Show system details")

    def _open_email(self) -> None:
        QDesktopServices.openUrl(QUrl(f"mailto:{__contact__}"))

    def _open_notices(self) -> None:
        """Open the shipped third-party licence notices in the default viewer."""
        path = notices_path()
        if path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def notices_path() -> Path:
    """Location of the third-party notices shipped with the installation."""
    for candidate in (
        assets_root().parent / "THIRD_PARTY_NOTICES.md",
        Path("THIRD_PARTY_NOTICES.md"),
    ):
        if candidate.is_file():
            return candidate
    return Path("THIRD_PARTY_NOTICES.md")
