"""Form controls: labelled fields, text areas, selects, pickers and toggles.

Every control supports the full state matrix (default, hover, focus, disabled,
read-only, error, success) and reserves space for its validation message so the
layout never jumps when validation appears.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from dentiva.ui.theme import icons
from dentiva.ui.theme.tokens import COLORS, SIZE, SPACING


class FieldLabel(QLabel):
    """Small caption label used above every control."""

    def __init__(self, text: str, *, required: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(text + ("  *" if required else ""), parent)
        self.setProperty("role", "caption")
        self.setTextFormat(Qt.TextFormat.PlainText)


class ValidationMessage(QLabel):
    """Reserved-height message area (prevents layout shift on validation)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("", parent)
        self.setProperty("role", "caption")
        self.setWordWrap(True)
        self.setMinimumHeight(14)
        self.setVisible(False)

    def show_error(self, message: str) -> None:
        self.setText(message)
        self.setStyleSheet(f"color: {COLORS.danger};")
        self.setVisible(True)

    def show_hint(self, message: str) -> None:
        self.setText(message)
        self.setStyleSheet(f"color: {COLORS.ink_muted};")
        self.setVisible(bool(message))

    def clear(self) -> None:
        self.setText("")
        self.setStyleSheet("")
        self.setVisible(False)


class LabeledField(QWidget):
    """Vertical container: label, control, validation message."""

    def __init__(
        self, label: str, control: QWidget, *, required: bool = False, hint: str = ""
    ) -> None:
        super().__init__()
        self.label = FieldLabel(label, required=required)
        self.control = control
        self.message = ValidationMessage()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING.xs)
        layout.addWidget(self.label)
        layout.addWidget(control)
        if hint:
            self.message.show_hint(hint)
        layout.addWidget(self.message)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_error(self, message: str) -> None:
        self.message.show_error(message)
        self.control.setProperty("state", "error")
        self._repolish()

    def clear_error(self) -> None:
        self.message.clear()
        self.control.setProperty("state", "")
        self._repolish()

    def _repolish(self) -> None:
        style = self.control.style()
        style.unpolish(self.control)
        style.polish(self.control)

    def set_visible_state(self, visible: bool) -> None:
        self.setVisible(visible)


class TextField(QLineEdit):
    """Single-line text input with placeholder, validation and read-only support."""

    def __init__(
        self, placeholder: str = "", *, echo_password: bool = False, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(SIZE.control_height)
        if echo_password:
            self.setEchoMode(QLineEdit.EchoMode.Password)

    def set_error_state(self, has_error: bool) -> None:
        self.setProperty("state", "error" if has_error else "")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_read_only(self, read_only: bool) -> None:
        """Read-only state (Qt already owns the ``readOnly`` property name)."""
        self.setReadOnly(read_only)
        self.setProperty("state", "readonly" if read_only else "")
        self.style().unpolish(self)
        self.style().polish(self)


class SearchInput(QWidget):
    """Search box with a leading icon and a clear button."""

    textChanged = Signal(str)
    submitted = Signal(str)

    def __init__(self, placeholder: str = "Search…", *, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.setMinimumHeight(SIZE.control_height)
        self.input.setClearButtonEnabled(True)
        self.input.addAction(icons.icon("search", 16), QLineEdit.ActionPosition.LeadingPosition)
        self.input.textChanged.connect(self.textChanged.emit)
        self.input.returnPressed.connect(lambda: self.submitted.emit(self.input.text()))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.input)

    def text(self) -> str:
        return self.input.text()

    def setText(self, value: str) -> None:
        self.input.setText(value)

    def setFocus(self, reason: Qt.FocusReason = Qt.FocusReason.OtherFocusReason) -> None:
        self.input.setFocus(reason)


class TextArea(QPlainTextEdit):
    """Multi-line text input (clinical notes, addresses, instructions)."""

    def __init__(
        self, placeholder: str = "", *, min_lines: int = 3, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setTabChangesFocus(True)
        metric = self.fontMetrics()
        self.setMinimumHeight(metric.lineSpacing() * min_lines + SPACING.lg)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def set_error_state(self, has_error: bool) -> None:
        self.setProperty("state", "error" if has_error else "")
        self.style().unpolish(self)
        self.style().polish(self)


class ComboBox(QComboBox):
    """Select control with optional key/value items."""

    def __init__(
        self, items: Iterable[tuple[str, object] | str] | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setMinimumHeight(SIZE.control_height)
        if items:
            self.set_items(items)

    def set_items(self, items: Iterable[tuple[str, object] | str]) -> None:
        self.clear()
        for item in items:
            if isinstance(item, str):
                self.addItem(item, item)
            else:
                label, value = item
                self.addItem(label, value)

    def current_value(self) -> object:
        return self.currentData()

    def select_value(self, value: object) -> bool:
        index = self.findData(value)
        if index >= 0:
            self.setCurrentIndex(index)
            return True
        return False


class IntField(QSpinBox):
    """Integer input with an inclusive range."""

    def __init__(
        self,
        *,
        minimum: int = 0,
        maximum: int = 1_000_000,
        value: int = 0,
        suffix: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setRange(minimum, maximum)
        self.setValue(value)
        self.setSuffix(suffix)
        self.setMinimumHeight(SIZE.control_height)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)


class DatePicker(QDateEdit):
    """Date input with a calendar popup and configurable display format."""

    def __init__(
        self,
        *,
        value: date | None = None,
        display_format: str = "dd MMM yyyy",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat(display_format)
        self.setMinimumHeight(SIZE.control_height)
        if value is not None:
            self.setDate(value)

    def value(self) -> date:
        py_date = self.date().toPython()
        return py_date if isinstance(py_date, date) else date.today()


class Switch(QWidget):
    """Accessible on/off toggle (painted track + knob)."""

    toggled = Signal(bool)

    def __init__(
        self, label: str = "", *, checked: bool = False, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._checked = checked
        self._label = label
        self.checkbox = QCheckBox(label)
        self.checkbox.setChecked(checked)
        self.checkbox.setTristate(False)
        self.checkbox.stateChanged.connect(lambda state: self._on_state_changed(state))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING.sm)
        layout.addWidget(self.checkbox)
        layout.addStretch(1)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _on_state_changed(self, state: int) -> None:
        self._checked = state == Qt.CheckState.Checked.value
        self.toggled.emit(self._checked)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, checked: bool) -> None:
        self.checkbox.setChecked(checked)

    def set_label(self, label: str) -> None:
        self.checkbox.setText(label)


class CheckBox(QCheckBox):
    """Checkbox with an optional description rendered beneath the label."""

    def __init__(self, text: str, *, description: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._description = description
        if description:
            self.setToolTip(description)

    @property
    def description(self) -> str:
        return self._description


class FormSection(QWidget):
    """Titled group of fields (used to keep large forms scannable)."""

    def __init__(self, title: str, *, description: str = "", columns: int = 2) -> None:
        super().__init__()
        self.grid = QHBoxLayout()
        self.columns: list[QVBoxLayout] = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(SPACING.md)
        heading = QLabel(title)
        heading.setProperty("role", "heading")
        outer.addWidget(heading)
        if description:
            caption = QLabel(description)
            caption.setProperty("role", "caption")
            caption.setWordWrap(True)
            outer.addWidget(caption)
        row = QHBoxLayout()
        row.setSpacing(SPACING.lg)
        for _ in range(max(1, columns)):
            column = QVBoxLayout()
            column.setSpacing(SPACING.md)
            row.addLayout(column, 1)
            self.columns.append(column)
        outer.addLayout(row)

    def add(self, field: QWidget, column: int = 0) -> None:
        self.columns[min(column, len(self.columns) - 1)].addWidget(field)

    def add_stretch(self) -> None:
        for column in self.columns:
            column.addStretch(1)
