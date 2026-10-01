"""Filesystem locations used by Dentiva Pro.

Installed layout (Windows):
    binaries   %ProgramFiles%\\Dentiva Pro\\
    data       %LOCALAPPDATA%\\DentivaPro\\        (database, attachments, logs, ...)

The data directory always lives in the user profile so that (a) no administrator
rights are required at runtime, and (b) uninstalling the program never destroys
clinic data.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

APP_DIR_NAME = "DentivaPro"

#: Environment variables that override detection (used by tests and support).
ENV_DATA_DIR = "DENTIVA_DATA_DIR"


def is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def bundle_root() -> Path:
    """Directory that contains the bundled read-only assets."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    # src/dentiva/core/paths.py -> src/dentiva/core -> src/dentiva -> src -> repo root
    return Path(__file__).resolve().parents[3]


def executable_dir() -> Path:
    """Directory holding the executable (writable installs only use it read-only)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return bundle_root()


def _is_windows() -> bool:
    """Test seam: the platform check is isolated so tests never patch ``os``."""
    return os.name == "nt"


def _default_data_root() -> Path:
    if _is_windows():
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / APP_DIR_NAME
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / APP_DIR_NAME.lower()


def data_root(override: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the writable per-user data directory."""
    if override is not None:
        return Path(override).expanduser()
    env = os.environ.get(ENV_DATA_DIR)
    if env:
        return Path(env).expanduser()
    return _default_data_root()


def assets_root() -> Path:
    """Directory containing bundled assets (icons, fonts)."""
    for candidate in (executable_dir() / "assets", bundle_root() / "assets"):
        if candidate.is_dir():
            return candidate
    return bundle_root() / "assets"


@dataclass(frozen=True, slots=True)
class AppPaths:
    """Resolved, absolute locations used across the application."""

    data: Path
    logs: Path
    attachments: Path
    backups: Path
    drafts: Path
    security: Path
    assets: Path
    database: Path

    @classmethod
    def create(cls, root: str | os.PathLike[str] | None = None) -> AppPaths:
        base = data_root(root).resolve()
        return cls(
            data=base,
            logs=base / "logs",
            attachments=base / "attachments",
            backups=base / "backups",
            drafts=base / "drafts",
            security=base / "security",
            assets=assets_root(),
            database=base / "dentiva.db",
        )

    def ensure(self) -> AppPaths:
        """Create every managed directory (idempotent, best effort)."""
        for directory in (
            self.data,
            self.logs,
            self.attachments,
            self.backups,
            self.drafts,
            self.security,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return self

    def within(self, *parts: str) -> Path:
        """Join *parts* under the data root, refusing anything that escapes it."""
        target = (self.data.joinpath(*parts)).resolve()
        root = self.data.resolve()
        if target != root and root not in target.parents:
            raise ValueError(f"Refusing path outside the data directory: {target}")
        return target


def safe_filename(name: str, *, max_length: int = 120) -> str:
    """Return a filesystem-safe file name without directories or traversal."""
    cleaned = name.replace("\\", "/").split("/")[-1]
    cleaned = cleaned.strip().strip(".")
    cleaned = "".join(ch for ch in cleaned if ch.isprintable() and ch not in '<>:"|?*')
    cleaned = cleaned.strip()
    if not cleaned:
        cleaned = "unnamed"
    if len(cleaned) > max_length:
        stem, dot, suffix = cleaned.rpartition(".")
        keep = max_length - (len(suffix) + 1 if dot and len(suffix) <= 8 else 0)
        cleaned = (stem[:keep] + (dot + suffix if dot and len(suffix) <= 8 else "")).strip()
    return cleaned
