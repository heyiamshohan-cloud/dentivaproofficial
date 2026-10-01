"""Safe file and folder operations.

Every function here is written for the hostile cases listed in REQ-FFH-001:
missing folder, permission denied, invalid path, missing file, existing file,
insufficient disk space, locked file, corrupted file and interrupted operations.
None of them is allowed to crash the application.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from dentiva.core.errors import InsufficientSpaceError, StorageError


def free_space(path: str | Path) -> int:
    """Free bytes available on the filesystem holding *path*."""
    usage = shutil.disk_usage(os.fspath(path))
    return int(usage.free)


def ensure_free_space(path: str | Path, required_bytes: int) -> None:
    """Raise :class:`InsufficientSpaceError` when fewer than *required* bytes are free."""
    available = free_space(path)
    if available < required_bytes:
        raise InsufficientSpaceError(
            "Not enough free disk space to continue.",
            detail=f"required={required_bytes} available={available} path={path}",
            required=required_bytes,
            available=available,
        )


def directory_size(path: str | Path) -> int:
    """Total size of every file under *path* (missing directory -> 0)."""
    root = Path(path)
    if not root.exists():
        return 0
    total = 0
    for current, _dirs, files in os.walk(root):
        for name in files:
            candidate = Path(current) / name
            try:
                total += candidate.stat().st_size
            except OSError:  # file vanished or is locked
                continue
    return total


def _open_temp(destination: Path) -> tuple[Path, Any]:
    """Create the hidden temporary file used by the atomic write helpers."""
    handle = tempfile.NamedTemporaryFile(  # noqa: SIM115 - lifetime is managed by the caller
        mode="wb",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    )
    return Path(handle.name), handle


def atomic_write(target: str | Path, payload: bytes, *, fsync: bool = True) -> Path:
    """Write *payload* to *target* atomically (temp file + ``os.replace``).

    A partially written file is never visible under the final name, so an
    interrupted write can never be mistaken for a complete one.
    """
    destination = Path(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path, handle = _open_temp(destination)
    try:
        with handle:
            handle.write(payload)
            if fsync:
                handle.flush()
                os.fsync(handle.fileno())
        temp_path.replace(destination)
    except OSError as exc:
        with suppress(OSError):
            temp_path.unlink()
        raise StorageError(
            f"Could not write {destination.name}.",
            detail=f"{type(exc).__name__}: {exc}",
            path=str(destination),
        ) from exc
    _fsync_directory(destination.parent)
    return destination


def atomic_copy(source: str | Path, target: str | Path, *, chunk_size: int = 1024 * 1024) -> Path:
    """Copy a file atomically, streaming so that large files never exhaust memory."""
    destination = Path(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp_path, handle = _open_temp(destination)
    try:
        with Path(source).open("rb") as reader, handle:
            for chunk in iter(lambda: reader.read(chunk_size), b""):
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        shutil.copymode(source, temp_path)
        temp_path.replace(destination)
    except OSError as exc:
        with suppress(OSError):
            temp_path.unlink()
        raise StorageError(
            f"Could not copy to {destination.name}.",
            detail=f"{type(exc).__name__}: {exc}",
            path=str(destination),
        ) from exc
    return destination


def unique_path(path: str | Path) -> Path:
    """Return *path* or a ``name (2)``-style variant that does not exist yet."""
    candidate = Path(path)
    if not candidate.exists():
        return candidate
    parent, stem, suffix = candidate.parent, candidate.stem, candidate.suffix
    for index in range(2, 10_000):
        alternative = parent / f"{stem} ({index}){suffix}"
        if not alternative.exists():
            return alternative
    raise StorageError("Too many files with the same name.", path=str(path))


def remove_file(path: str | Path) -> bool:
    """Delete a file; return False (never raise) when it cannot be removed."""
    try:
        Path(path).unlink()
    except FileNotFoundError:
        return False
    except OSError:
        return False
    return True


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise StorageError(
            "Could not create a required folder.",
            detail=f"{type(exc).__name__}: {exc}",
            path=str(directory),
        ) from exc
    return directory


def _fsync_directory(directory: Path) -> None:
    """Best-effort directory fsync so a rename survives a crash."""
    try:
        fd = os.open(os.fspath(directory), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)
