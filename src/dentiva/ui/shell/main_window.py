"""Main window: header, collapsible sidebar and a lazily built content stack."""

from __future__ import annotations

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from dentiva.core.paths import assets_root
from dentiva.ui.settings import application_settings
from dentiva.ui.shell.header import Header
from dentiva.ui.shell.navigation import NavItem, by_id, create_view, ordered
from dentiva.ui.shell.sidebar import Sidebar
from dentiva.ui.theme import icons

ORGANISATION = "DentivaPro"
APPLICATION = "DentivaPro"


class MainWindow(QMainWindow):
    """Application shell.

    Screens are created on first navigation and then kept alive, so switching is
    instant while memory stays proportional to the screens actually used.
    """

    screenChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Dentiva Pro")
        self.setMinimumSize(QSize(1024, 640))
        self.setObjectName("mainWindow")
        self._settings = application_settings()
        self._views: dict[str, QWidget] = {}
        self._current: str = ""

        container = QWidget()
        container.setObjectName("appRoot")
        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = Header()
        root.addWidget(self.header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.sidebar = Sidebar()
        self.sidebar.navigate.connect(self.navigate)
        body.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.setObjectName("contentStack")
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        self.setCentralWidget(container)
        self._restore_geometry()
        self._apply_window_icon()

    # ------------------------------------------------------------------ setup --
    def _apply_window_icon(self) -> None:
        icon_path = assets_root() / "icons" / "dentiva.ico"
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            self.setWindowIcon(icons.icon("treatments", 32))

    def _restore_geometry(self) -> None:
        geometry = self._settings.value("window/geometry")
        if isinstance(geometry, bytes):
            self.restoreGeometry(geometry)
        state = self._settings.value("window/state")
        if isinstance(state, bytes):
            self.restoreState(state)
        collapsed = self._settings.value("sidebar/collapsed", False, type=bool)
        self.sidebar.set_collapsed(bool(collapsed))

    # ------------------------------------------------------------- navigation --
    def navigate(self, item_id: str) -> None:
        """Show the screen for *item_id*, creating it on first use."""
        item = by_id(item_id)
        if item_id not in self._views:
            view = create_view(item)
            view.setObjectName(f"view_{item_id}")
            self.stack.addWidget(view)
            self._views[item_id] = view
        self.stack.setCurrentWidget(self._views[item_id])
        self._current = item_id
        self.sidebar.set_active(item_id)
        self._settings.setValue("navigation/last", item_id)
        self.screenChanged.emit(item_id)

    def current_screen(self) -> str:
        return self._current

    def view_for(self, item_id: str) -> QWidget | None:
        return self._views.get(item_id)

    def restore_last_screen(self) -> None:
        """Open the last used screen (or the first navigation item)."""
        last = self._settings.value("navigation/last", "", type=str)
        items = ordered()
        target = last if last and any(item.id == last for item in items) else items[0].id
        self.navigate(target)

    def every_view(self) -> dict[str, QWidget]:
        """Create and return every screen (used by the layout audit and selftest)."""
        for item in ordered():
            if item.id not in self._views:
                view = create_view(item)
                view.setObjectName(f"view_{item.id}")
                self.stack.addWidget(view)
                self._views[item.id] = view
        return dict(self._views)

    def toggle_sidebar(self) -> None:
        self.sidebar.set_collapsed(not self.sidebar.is_collapsed)

    # ------------------------------------------------------------------ events --
    def closeEvent(self, event: QCloseEvent) -> None:
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/state", self.saveState())
        self._settings.setValue("sidebar/collapsed", self.sidebar.is_collapsed)
        super().closeEvent(event)

    def set_clinic_name(self, name: str) -> None:
        self.header.set_clinic_name(name)


def default_window_size() -> QSize:
    """Sensible default size for a 1366×768 desktop."""
    return QSize(1200, 760)


def nav_item(item_id: str) -> NavItem:
    return by_id(item_id)
