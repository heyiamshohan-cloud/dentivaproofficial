"""Shared pytest fixtures for the Dentiva Pro suite."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path_factory):
    """Keep QSettings in a throw-away file (no pollution of the dev machine)."""
    from PySide6.QtCore import QCoreApplication, QSettings

    directory = tmp_path_factory.mktemp("settings")
    QCoreApplication.setOrganizationName("DentivaProTests")
    QCoreApplication.setApplicationName("DentivaProTests")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(directory))
    yield
    QSettings().sync()


@pytest.fixture(scope="session")
def assets_root() -> Path:
    """Repository assets directory (fonts, icons)."""
    return SRC.parent / "assets"


@pytest.fixture()
def themed_app(qapp, assets_root):  # type: ignore[no-untyped-def]
    """QApplication with the Dentiva Pro theme and bundled fonts installed."""
    from dentiva.ui.theme import apply_theme

    bundle = apply_theme(qapp)
    assert bundle.loaded, "bundled fonts must load in the test environment"
    return qapp


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch) -> Path:  # type: ignore[no-untyped-def]
    """Every test runs against a throw-away per-user data directory.

    Autouse: logs, settings, backups and databases must never land in the
    developer's real data directory (and tests must not read each other's).
    """
    from dentiva.core.paths import AppPaths

    monkeypatch.setenv("DENTIVA_DATA_DIR", str(tmp_path / "data"))
    return AppPaths.create().ensure().data


@pytest.fixture()
def db_engine(tmp_path):  # type: ignore[no-untyped-def]
    """Engine over a temporary, migrated database."""
    from dentiva.data.engine import create_engine_for, upgrade

    engine = create_engine_for(tmp_path / "test.db")
    upgrade(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def sample_clinic_text() -> str:
    """Realistic mixed Bangla/English clinic content."""
    return "স্মাইল ডেন্টাল কেয়ার — Smile Dental Care, Dhaka"
