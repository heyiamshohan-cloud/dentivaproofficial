"""Component state matrix: every control renders its documented states.

REQ-UIX-003/008, REQ-STE-001, REQ-NBI-001.
"""

from __future__ import annotations

import pytest

from dentiva.core.paging import Page, PageRequest
from dentiva.ui.components.buttons import Button, IconButton, SplitButton
from dentiva.ui.components.cards import ActionCard, Card, StatCard
from dentiva.ui.components.dialogs import ConfirmDialog, DangerConfirmDialog, ErrorDialog
from dentiva.ui.components.display import Avatar, Badge, Chip, IconText, KeyValueGrid, StatusPill
from dentiva.ui.components.feedback import (
    Banner,
    EmptyState,
    ErrorState,
    LoadingState,
    NoPermissionState,
)
from dentiva.ui.components.inputs import (
    CheckBox,
    ComboBox,
    DatePicker,
    IntField,
    LabeledField,
    SearchInput,
    Switch,
    TextArea,
    TextField,
)
from dentiva.ui.components.states import StateStack
from dentiva.ui.components.tables import Column, DataTable, Pagination
from dentiva.ui.components.tabs import SegmentedControl, Tabs, VerticalTabs


def test_button_variants_and_busy_state(qtbot) -> None:
    for variant in ("primary", "secondary", "ghost", "subtle", "soft", "danger"):
        button = Button("Save", variant=variant)
        qtbot.addWidget(button)
        assert button.property("variant") == variant
    button = Button("Save")
    qtbot.addWidget(button)
    button.set_busy(True)
    assert not button.isEnabled() and button.is_busy
    button.set_busy(False)
    assert button.isEnabled() and button.text() == "Save"


def test_button_disabled_reason_is_exposed(qtbot) -> None:
    button = Button("Delete patient")
    qtbot.addWidget(button)
    button.set_enabled(False, reason="Requires the patient.delete permission")
    assert "permission" in button.toolTip()


def test_icon_button_and_split_button(qtbot) -> None:
    icon_button = IconButton("plus", tooltip="New patient")
    qtbot.addWidget(icon_button)
    assert icon_button.iconSize().width() == 18
    split = SplitButton("Print")
    qtbot.addWidget(split)
    split.set_busy(True)
    assert not split.main.isEnabled()


def test_inputs_render_all_states(qtbot) -> None:
    field = TextField(placeholder="Patient name")
    qtbot.addWidget(field)
    field.set_error_state(True)
    assert field.property("state") == "error"
    field.set_error_state(False)
    field.set_read_only(True)
    assert field.property("state") == "readonly"
    field.set_read_only(False)
    assert not field.isReadOnly()

    area = TextArea(placeholder="Notes", min_lines=4)
    qtbot.addWidget(area)
    assert area.minimumHeight() > 0

    combo = ComboBox([("Cash", "cash"), ("bKash", "bkash")])
    qtbot.addWidget(combo)
    assert combo.current_value() == "cash"
    assert combo.select_value("bkash")

    labelled = LabeledField("Phone", TextField(), required=True, hint="Include the country code")
    qtbot.addWidget(labelled)
    labelled.set_error("Phone is required")
    assert not labelled.message.isHidden()
    labelled.clear_error()
    assert labelled.message.isHidden()

    qtbot.addWidget(CheckBox("Recall in 6 months", description="Adds a follow-up appointment"))
    qtbot.addWidget(IntField(minimum=0, maximum=10, value=3, suffix=" days"))
    qtbot.addWidget(DatePicker())
    qtbot.addWidget(SearchInput(placeholder="Search patients"))
    toggle = Switch("Enable automatic backup", checked=True)
    qtbot.addWidget(toggle)
    assert toggle.is_checked()


def test_display_components(qtbot) -> None:
    qtbot.addWidget(Avatar("Shohan Khan"))
    badge = Badge("Paid", tone="success")
    qtbot.addWidget(badge)
    badge.set_tone("danger")
    assert badge.property("tone") == "danger"
    pill = StatusPill("partial")
    qtbot.addWidget(pill)
    pill.set_status("paid")
    assert pill.status == "paid"
    qtbot.addWidget(Chip("Diabetic"))
    qtbot.addWidget(IconText("phone", "+880 1700 000000"))
    grid = KeyValueGrid(columns=2)
    grid.add("Total billed", "৳ 12,500.00", emphasise=True)
    grid.add("Outstanding", "৳ 2,000.00", tone="warning")
    grid.finish()
    qtbot.addWidget(grid)


def test_cards(qtbot) -> None:
    card = Card("Patient details", subtitle="Demographics and history")
    qtbot.addWidget(card)
    card.add_widget(TextField())
    card.add_action(IconButton("edit", tooltip="Edit"))
    stat = StatCard("Today's revenue", "৳ 0.00", icon_name="payments", caption="No payments yet")
    qtbot.addWidget(stat)
    stat.set_value("৳ 4,500.00", caption="3 payments")
    assert "4,500" in stat.value_label.text()
    qtbot.addWidget(ActionCard("New patient", "plus", description="Register a patient"))


def test_feedback_states(qtbot) -> None:
    for widget in (
        EmptyState(action_label="Add patient"),
        ErrorState(detail="sqlite3.OperationalError: database is locked"),
        NoPermissionState(),
        LoadingState(rows=3),
    ):
        qtbot.addWidget(widget)
    banner = Banner("Backup completed", tone="success", action_label="Open folder")
    qtbot.addWidget(banner)
    banner.set_message("Backup verified")


def test_state_stack_switches_between_states(qtbot) -> None:
    stack = StateStack()
    qtbot.addWidget(stack)
    assert stack.state == "loading"
    content = TextField()
    stack.set_content(content)
    assert stack.state == "content"
    stack.show_empty("No patients yet", "Register the first patient.")
    assert stack.state == "empty"
    stack.show_error("Could not load patients", detail="timeout")
    assert stack.state == "error"
    stack.show_no_permission()
    assert stack.state == "no_permission"
    stack.show_content()
    assert stack.state == "content"


def test_data_table_and_pagination(qtbot) -> None:
    columns = (
        Column("code", "Code", width=110),
        Column("name", "Name", stretch=True),
        Column("phone", "Phone", width=140),
    )
    table = DataTable(columns)
    qtbot.addWidget(table)
    rows = [
        {"code": "P-0001", "name": "মোহাম্মদ রাহাত হোসেন", "phone": "01700000001"},
        {"code": "P-0002", "name": "Shohan Khan", "phone": "01700000002"},
    ]
    table.set_rows(rows)
    assert table.model.rowCount() == 2
    table.view.selectRow(0)
    assert table.selected_row() == rows[0]

    pagination = Pagination(page_size=2)
    qtbot.addWidget(pagination)
    seen: list[int] = []
    pagination.pageChanged.connect(seen.append)
    pagination.set_state(page=2, page_size=2, total=7)
    assert "Showing 3–4 of 7" in pagination.summary.text()
    pagination.next.click()
    assert seen == [3]


def test_tabs_and_segmented_control(qtbot) -> None:
    tabs = Tabs()
    tabs.add_tab(TextField(), "Overview", icon_name="dashboard")
    tabs.add_tab(TextField(), "Timeline", icon_name="clock")
    qtbot.addWidget(tabs)
    assert tabs.count() == 2

    segmented = SegmentedControl(
        (("today", "Today"), ("7d", "7 days"), ("30d", "30 days")), value="today"
    )
    qtbot.addWidget(segmented)
    changes: list[str] = []
    segmented.selectionChanged.connect(changes.append)
    segmented.set_value("7d")
    assert changes == ["7d"] and segmented.value() == "7d"

    vertical = VerticalTabs((("general", "General"), ("printing", "Printing")))
    qtbot.addWidget(vertical)
    vertical.set_value("printing")
    assert vertical.value() == "printing"


def test_dialogs(qtbot) -> None:
    confirm = ConfirmDialog("Delete patient?", "This will archive the patient record.")
    qtbot.addWidget(confirm)
    assert not confirm.confirmed

    def verifier(password: str) -> bool:
        return password == "correct horse"

    danger = DangerConfirmDialog(
        "Delete all records",
        "Every patient, visit, invoice and payment will be removed.",
        consequences=("A safety backup will be created first.", "This cannot be undone."),
        confirm_word="DELETE",
        require_password=True,
        password_verifier=verifier,
    )
    qtbot.addWidget(danger)
    assert not danger.confirm.isEnabled()
    danger.word_input.setText("delete")
    assert not danger.confirm.isEnabled()  # password still missing
    danger.password_input.setText("wrong")
    assert danger.confirm.isEnabled()  # form complete; the password is checked on confirm
    danger.confirm.click()
    assert danger.result() != danger.DialogCode.Accepted
    assert danger.password_input.property("state") == "error"
    danger.password_input.setText("correct horse")
    danger.confirm.click()
    assert danger.result() == danger.DialogCode.Accepted

    error = ErrorDialog(
        "Could not save", "The invoice could not be saved.", detail="IntegrityError"
    )
    qtbot.addWidget(error)
    assert error.details.isHidden()
    error.show_details.click()
    assert not error.details.isHidden()


@pytest.mark.parametrize("tone", ["info", "success", "warning", "danger"])
def test_banner_tones(qtbot, tone) -> None:
    banner = Banner("Message", tone=tone)
    qtbot.addWidget(banner)
    assert banner.property("tone") == tone


def test_pagination_understands_page_objects(qtbot) -> None:
    pagination = Pagination()
    qtbot.addWidget(pagination)
    page = Page.from_sequence(
        [f"P-{index}" for index in range(1, 121)], PageRequest(page=3, page_size=25), total=1204
    )
    pagination.apply_page(page)
    assert pagination.summary.text() == "Showing 51–75 of 1204"
    request = pagination.page_request()
    assert (request.page, request.page_size) == (3, 25)
