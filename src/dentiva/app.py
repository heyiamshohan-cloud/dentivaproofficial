"""Application bootstrap: single instance, logging, database, theme, shell.

The boot sequence is deliberately explicit and every step is logged, because
first-launch failures are the most expensive support cases for a desktop product.
"""

from __future__ import annotations

import sys
import traceback
from collections.abc import Sequence
from types import TracebackType
from typing import Any

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox

from dentiva.core.errors import DentivaError
from dentiva.core.logging_setup import configure_logging, get_logger
from dentiva.core.paths import AppPaths
from dentiva.ui.theme import apply_theme, configure_high_dpi

LOGGER = get_logger("app")
INSTANCE_KEY = "DentivaPro.SingleInstance.v1"


class Application:
    """Owns the process: QApplication, logging, database and the main window."""

    def __init__(self, argv: Sequence[str] | None = None, *, paths: AppPaths | None = None) -> None:
        self.argv = list(sys.argv if argv is None else argv)
        self.paths = paths or AppPaths.create()
        self.qt_application: QApplication | None = None
        self.window: Any = None
        self.log_path: Any = None
        self._local_server: QLocalServer | None = None

    # ------------------------------------------------------------------ boot --
    def run(self) -> int:
        """Start the application and return the process exit code."""
        configure_high_dpi()
        app = QApplication(self.argv)
        self.qt_application = app
        QCoreApplication.setOrganizationName("DentivaPro")
        QCoreApplication.setApplicationName("Dentiva Pro")
        QCoreApplication.setApplicationVersion(_version())
        app.setApplicationDisplayName("Dentiva Pro")
        app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)

        self.paths.ensure()
        self.log_path = configure_logging(self.paths)
        LOGGER.info("Dentiva Pro starting (version %s)", _version())

        self._install_exception_hooks()
        if not self._acquire_single_instance():
            return 0

        try:
            self._prepare_database()
        except DentivaError as error:
            LOGGER.error("Database preparation failed: %s", error.detail or error)
            self._fatal(error.user_message(), error.detail)
            return 1

        bundle = apply_theme(app)
        if bundle.missing:
            LOGGER.warning("Bundled fonts missing: %s", ", ".join(bundle.missing))

        from dentiva.ui.shell.main_window import MainWindow

        self.window = MainWindow()
        self.window.restore_last_screen()
        self.window.show()
        LOGGER.info("Main window shown")
        exit_code = app.exec()
        LOGGER.info("Dentiva Pro exiting with code %s", exit_code)
        return int(exit_code)

    # -------------------------------------------------------------- internals --
    def _prepare_database(self) -> None:
        """Open the clinic database and apply any pending migrations."""
        from dentiva.data.engine import assert_healthy, create_engine_for, upgrade

        engine = create_engine_for(self.paths.database)
        self.engine = engine
        upgrade(engine)
        assert_healthy(engine)
        LOGGER.info("Database ready: %s", self.paths.database)

    def _acquire_single_instance(self) -> bool:
        """Refuse to start a second instance (protects the SQLite file)."""
        socket = QLocalSocket()
        socket.connectToServer(INSTANCE_KEY)
        if socket.waitForConnected(300):
            socket.disconnectFromServer()
            QMessageBox.information(
                None,
                "Dentiva Pro is already running",
                "Dentiva Pro is already open on this computer.\n\n"
                "Only one instance can run at a time so that clinic data stays consistent.",
            )
            return False
        server = QLocalServer()
        if not server.listen(INSTANCE_KEY):
            QLocalServer.removeServer(INSTANCE_KEY)
            server.listen(INSTANCE_KEY)
        self._local_server = server
        return True

    def _install_exception_hooks(self) -> None:
        """Route unhandled exceptions to the log and a user-facing dialog."""

        def hook(
            exc_type: type[BaseException], exc_value: BaseException, exc_tb: TracebackType | None
        ) -> None:
            if issubclass(exc_type, KeyboardInterrupt):  # pragma: no cover - interactive only
                sys.__excepthook__(exc_type, exc_value, exc_tb)
                return
            detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            LOGGER.critical("Unhandled exception\n%s", detail)
            self._fatal("Dentiva Pro hit an unexpected problem.", detail)

        sys.excepthook = hook

    @staticmethod
    def _fatal(message: str, detail: str = "") -> None:
        from dentiva.ui.components.dialogs import ErrorDialog

        dialog = ErrorDialog("Dentiva Pro cannot continue", message, detail=detail)
        dialog.exec()


def _version() -> str:
    from dentiva import __version__

    return __version__
