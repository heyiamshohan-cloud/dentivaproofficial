"""Persistent UI settings storage.

Window geometry, the last visited screen and sidebar state are stored as a
plain INI file **inside the application data directory** rather than in the
Windows registry. That keeps a clinic's workspace portable (the whole folder
can be copied to another machine), makes backups and diagnostics trivial, and
lets the test suite redirect storage with a single environment variable.

REQ-STO-005, REQ-SHL-004.

Convention: the file is written atomically by Qt on ``sync()``; nothing
secret is ever stored here — credentials live only in the database.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

from dentiva.core.paths import AppPaths

#: Name of the INI file kept beside the database.
SETTINGS_FILENAME = "ui.ini"


def settings_path(paths: AppPaths | None = None) -> str:
    """Absolute path of the settings file (Qt wants a string)."""
    resolved = paths if paths is not None else AppPaths.create().ensure()
    return str(resolved.data / SETTINGS_FILENAME)


def application_settings() -> QSettings:
    """Return the shared UI settings store.

    The file is created lazily by Qt and re-read on every call, so a settings
    change made by another window is visible immediately.
    """
    return QSettings(settings_path(), QSettings.Format.IniFormat)
