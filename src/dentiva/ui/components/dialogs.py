"""Dialogs: base modal, confirm, destructive confirm and error reporting.

Destructive dialogs implement the safeguards required by REQ-DST-001: they state
exactly what will happen, can require a typed confirmation word, and can require
administrator re-authentication before the action is allowed.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from dentiva.ui.components.buttons import Button, ButtonRow
from dentiva.ui.components.inputs import LabeledField, TextField
from dentiva.ui.components.states import ScrollableContent
from dentiva.ui.theme import icons
from dentiva.ui.theme.tokens import COLORS, SPACING, TYPE


class BaseDialog(QDialog):
    """Modal dialog with header, scrollable body and a pinned action bar."""

    def __init__(
        self,
        title: str,
        *,
        subtitle: str = "",
        icon_name: str | None = None,
        parent: QWidget | None = None,
        min_width: int = 420,
        min_height: int = 0,
    ) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setMinimumWidth(min_width)
        if min_height:
            self.setMinimumHeight(min_height)
        self.setSizeGripEnabled(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setProperty("role", "dialogHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(SPACING.xl, SPACING.lg, SPACING.xl, SPACING.lg)
        header_layout.setSpacing(SPACING.md)
        if icon_name:
            icon = QLabel()
            icon.setPixmap(icons.pixmap(icon_name, 20, COLORS.primary))
            icon.setFixedWidth(20)
            header_layout.addWidget(
                icon, 0, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignTop
            )
        text_column = QVBoxLayout()
        text_column.setSpacing(SPACING.xxs)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"font-size: {TYPE.size_subtitle}px; font-weight: 600;")
        self.title_label.setWordWrap(True)
        text_column.addWidget(self.title_label)
        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setProperty("role", "caption")
            self.subtitle_label.setWordWrap(True)
            text_column.addWidget(self.subtitle_label)
        header_layout.addLayout(text_column, 1)
        root.addWidget(header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(SPACING.xl, SPACING.lg, SPACING.xl, SPACING.lg)
        self.body_layout.setSpacing(SPACING.md)
        self.content_area = ScrollableContent(self.body)
        root.addWidget(self.content_area, 1)

        self.footer = QFrame()
        self.footer.setProperty("role", "dialogFooter")
        self.footer_layout = QHBoxLayout(self.footer)
        self.footer_layout.setContentsMargins(SPACING.xl, SPACING.md, SPACING.xl, SPACING.md)
        self.footer_layout.setSpacing(SPACING.sm)
        root.addWidget(self.footer)

    def add_body_widget(self, widget: QWidget) -> None:
        self.body_layout.addWidget(widget)

    def add_body_layout(self, layout: QHBoxLayout | QVBoxLayout) -> None:
        self.body_layout.addLayout(layout)

    def add_footer_widget(self, widget: QWidget, *, stretch_before: bool = True) -> None:
        if stretch_before:
            self.footer_layout.addStretch(1)
        self.footer_layout.addWidget(widget)

    def set_buttons(self, *buttons: Button) -> None:
        """Replace the footer content with a standard right-aligned button row."""
        while self.footer_layout.count():
            item = self.footer_layout.takeAt(0)
            if item is None:
                break
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)  # type: ignore[call-overload]
        row = ButtonRow(*buttons, align="right")
        self.footer_layout.addWidget(row)

    @staticmethod
    def center_on_screen() -> None:
        """Keep the dialog within the available screen geometry."""
        window = QApplication.activeWindow()
        if window is None:
            return
        frame = window.frameGeometry()
        screen = QApplication.screenAt(window.geometry().center())
        if screen is None:
            return
        frame.moveCenter(screen.availableGeometry().center())
        window.move(frame.topLeft())


class ConfirmDialog(BaseDialog):
    """Yes/No confirmation with an explicit explanation of the consequence."""

    def __init__(
        self,
        title: str,
        message: str,
        *,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        tone: str = "primary",
        icon_name: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, icon_name=icon_name, parent=parent, min_width=440)
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.add_body_widget(message_label)
        self.confirm = Button(confirm_label, variant="danger" if tone == "danger" else "primary")
        self.cancel = Button(cancel_label)
        self.confirm.clicked.connect(self.accept)
        self.cancel.clicked.connect(self.reject)
        self.set_buttons(self.cancel, self.confirm)
        self.cancel.setFocus()

    @property
    def confirmed(self) -> bool:
        return self.result() == QDialog.DialogCode.Accepted


class DangerConfirmDialog(BaseDialog):
    """Destructive action guard: consequence list, typed confirmation, re-auth."""

    def __init__(
        self,
        title: str,
        message: str,
        *,
        consequences: tuple[str, ...] = (),
        confirm_word: str = "",
        confirm_label: str = "I understand, continue",
        require_password: bool = False,
        password_verifier: Callable[[str], bool] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, icon_name="warning", parent=parent, min_width=520)
        intro = QLabel(message)
        intro.setWordWrap(True)
        self.add_body_widget(intro)

        if consequences:
            for item in consequences:
                row = QHBoxLayout()
                row.setSpacing(SPACING.sm)
                bullet = QLabel()
                bullet.setPixmap(icons.pixmap("warning", 14, COLORS.danger))
                bullet.setFixedWidth(16)
                row.addWidget(bullet, 0, Qt.AlignmentFlag.AlignTop)
                label = QLabel(item)
                label.setWordWrap(True)
                row.addWidget(label, 1)
                self.add_body_layout(row)

        self.confirm_word = confirm_word
        self.password_verifier = password_verifier
        self.require_password = require_password

        if confirm_word:
            hint = QLabel(f"Type <b>{confirm_word}</b> to confirm.")
            hint.setWordWrap(True)
            self.add_body_widget(hint)
            self.word_input = TextField(placeholder=confirm_word)
            self.add_body_widget(LabeledField("Confirmation", self.word_input, required=True))
            self.word_input.textChanged.connect(self._validate)
        else:
            self.word_input = None  # type: ignore[assignment]

        if require_password:
            self.password_input = TextField(placeholder="Your account password", echo_password=True)
            self.add_body_widget(
                LabeledField("Re-enter your password", self.password_input, required=True)
            )
            self.password_input.textChanged.connect(self._validate)
        else:
            self.password_input = None  # type: ignore[assignment]

        self.confirm = Button(confirm_label, variant="danger")
        self.cancel = Button("Cancel")
        self.confirm.clicked.connect(self._on_confirm)
        self.cancel.clicked.connect(self.reject)
        self.set_buttons(self.cancel, self.confirm)
        self.confirm.set_enabled(False, reason="Complete the confirmation to continue")
        self.cancel.setFocus()

    def _validate(self) -> None:
        word_ok = True
        if self.confirm_word and self.word_input is not None:
            word_ok = self.word_input.text().strip().upper() == self.confirm_word.upper()
        password_ok = True
        if self.require_password and self.password_input is not None:
            password_ok = len(self.password_input.text()) > 0
        self.confirm.set_enabled(
            word_ok and password_ok, reason="Complete the confirmation to continue"
        )

    def _on_confirm(self) -> None:
        if (
            self.require_password
            and self.password_verifier is not None
            and not self.password_verifier(self.password_input.text())
        ):
            self.password_input.set_error_state(True)
            return
        self.accept()


class ErrorDialog(BaseDialog):
    """User-facing error with the technical detail kept one click away."""

    def __init__(
        self,
        title: str,
        message: str,
        *,
        detail: str = "",
        correlation_id: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, icon_name="error", parent=parent, min_width=480)
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        self.add_body_widget(message_label)
        if correlation_id:
            reference = QLabel(f"Reference: {correlation_id}")
            reference.setProperty("role", "caption")
            self.add_body_widget(reference)
        self.details = QLabel(detail or "No additional technical detail available.")
        self.details.setProperty("role", "caption")
        self.details.setWordWrap(True)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.details.setVisible(False)
        self.add_body_widget(self.details)
        self.show_details = Button("Show technical details", variant="ghost", size="compact")
        self.show_details.clicked.connect(
            lambda: self.details.setVisible(not self.details.isVisible())
        )
        self.add_body_widget(self.show_details)

        close = Button("Close", variant="primary")
        close.clicked.connect(self.accept)
        copy = Button("Copy details", variant="ghost")
        copy.clicked.connect(self._copy_details)
        self.set_buttons(copy, close)
        close.setFocus()

    def _copy_details(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(f"{self.title_label.text()}\n\n{self.details.text()}")
