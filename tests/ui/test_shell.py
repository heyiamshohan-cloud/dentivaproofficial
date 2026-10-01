"""Shell: header, collapsible sidebar, navigation and persistence.

REQ-SHL-001..008, REQ-UAA-001.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QWidget

from dentiva.ui.diagnostics import audit_screen_fit, audit_widget
from dentiva.ui.shell.main_window import MainWindow
from dentiva.ui.shell.navigation import CURRENT_PHASE, by_id, grouped, ordered


def test_sidebar_lists_every_required_item() -> None:
    labels = {item.label for item in ordered()}
    for required in (
        "Dashboard",
        "Patients",
        "Appointments",
        "Queue",
        "Treatments",
        "Prescriptions",
        "Invoice",
        "Payments",
        "Inventory",
        "Accounting",
        "Staff & Users",
        "Backup & Restore",
        "Settings",
        "About",
    ):
        assert required in labels


def test_sidebar_groups_are_practice_clinical_billing_administration() -> None:
    assert [group for group, _items in grouped()] == [
        "Practice",
        "Clinical",
        "Billing",
        "Administration",
    ]


def test_collapsed_and_expanded_states_are_both_usable(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    sidebar = window.sidebar
    assert not sidebar.is_collapsed
    expanded_width = sidebar.width()
    sidebar.set_collapsed(True)
    QApplication.processEvents()
    assert sidebar.is_collapsed
    assert sidebar.width() < expanded_width
    for button in sidebar.buttons().values():
        assert button.toolTip()  # collapsed buttons keep a tooltip label
        assert not button.isHidden()
    sidebar.set_collapsed(False)
    QApplication.processEvents()
    assert not sidebar.is_collapsed


def test_navigation_creates_and_reuses_screens(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.navigate("about")
    first = window.view_for("about")
    assert first is not None and window.current_screen() == "about"
    window.navigate("patients")
    window.navigate("about")
    assert window.view_for("about") is first


def test_every_navigation_item_opens_a_screen(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    for item in ordered():
        window.navigate(item.id)
        assert window.current_screen() == item.id
        view = window.view_for(item.id)
        assert isinstance(view, QWidget)


def test_no_module_stays_pending_past_its_phase() -> None:
    """A module scheduled for the current (or an earlier) phase must be real."""
    pending = [item.id for item in ordered() if item.is_pending and item.phase <= CURRENT_PHASE]
    assert not pending, f"modules past due: {pending}"


def test_header_shows_brand_clinic_and_date(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.header.clinic_name.text()
    assert window.header.date_label.text()
    window.set_clinic_name("স্মাইল ডেন্টাল কেয়ার")
    assert window.header.clinic_name.text() == "স্মাইল ডেন্টাল কেয়ার"


def test_shell_is_free_of_layout_defects(qtbot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1366, 768)
    window.show()
    for item in ordered():
        window.navigate(item.id)
        view = window.view_for(item.id)
        assert view is not None
        assert audit_widget(view) == []
        assert audit_screen_fit(view, 1366, 768) == []


def test_navigation_metadata_is_complete() -> None:
    for item in ordered():
        assert item.id and item.label and item.icon and item.group
        assert item.phase >= 1
        assert by_id(item.id) is item
