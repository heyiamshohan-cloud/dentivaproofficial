"""File operations under hostile conditions (REQ-FFH-001, REQ-DCP-001)."""

from __future__ import annotations

from dentiva.core.errors import InsufficientSpaceError, StorageError
from dentiva.core.fileutil import (
    atomic_copy,
    atomic_write,
    directory_size,
    ensure_directory,
    ensure_free_space,
    free_space,
    remove_file,
    unique_path,
)


def test_atomic_write_publishes_only_complete_files(tmp_path) -> None:
    target = tmp_path / "out.txt"
    atomic_write(target, b"complete")
    assert target.read_bytes() == b"complete"
    assert not [path for path in tmp_path.iterdir() if path.name.startswith(".out.txt")]


def test_atomic_write_never_leaves_temp_files_on_failure(tmp_path, monkeypatch) -> None:
    import os

    target = tmp_path / "out.txt"
    real_replace = os.replace

    def fake_replace(*_args, **_kwargs):
        raise OSError("disk on fire")

    monkeypatch.setattr(os, "replace", fake_replace)
    try:
        atomic_write(target, b"data")
    except StorageError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected StorageError")
    monkeypatch.setattr(os, "replace", real_replace)
    assert not target.exists()
    assert not [path for path in tmp_path.iterdir() if path.suffix == ".tmp"]


def test_atomic_copy_streams_and_preserves_content(tmp_path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"x" * 5000)
    destination = atomic_copy(source, tmp_path / "nested" / "copy.bin", chunk_size=512)
    assert destination.read_bytes() == source.read_bytes()


def test_unique_path_avoids_overwrites(tmp_path) -> None:
    first = tmp_path / "report.pdf"
    first.write_text("1")
    assert unique_path(first) == tmp_path / "report (2).pdf"


def test_remove_file_is_safe_when_missing(tmp_path) -> None:
    assert remove_file(tmp_path / "missing.txt") is False


def test_disk_space_helpers(tmp_path) -> None:
    assert free_space(tmp_path) > 0
    ensure_free_space(tmp_path, 1)
    try:
        ensure_free_space(tmp_path, 2**62)
    except InsufficientSpaceError as error:
        assert error.context["required"] == 2**62
    else:  # pragma: no cover
        raise AssertionError("expected InsufficientSpaceError")


def test_directory_size_and_ensure_directory(tmp_path) -> None:
    (tmp_path / "a").write_text("12345")
    assert directory_size(tmp_path) >= 5
    assert directory_size(tmp_path / "missing") == 0
    assert ensure_directory(tmp_path / "deep" / "folder").is_dir()
