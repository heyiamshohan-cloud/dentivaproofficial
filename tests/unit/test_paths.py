"""Path handling: Windows-first layout, overrides and traversal safety (REQ-SEC-003)."""

from __future__ import annotations

from dentiva.core.paths import AppPaths, assets_root, data_root, safe_filename


def test_data_root_uses_localappdata_on_windows(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("DENTIVA_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("dentiva.core.paths._is_windows", lambda: True)
    assert data_root() == tmp_path / "DentivaPro"


def test_data_root_uses_xdg_data_home_on_linux(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("dentiva.core.paths._is_windows", lambda: False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("DENTIVA_DATA_DIR", raising=False)
    assert data_root() == tmp_path / "xdg" / "dentivapro"


def test_data_root_honours_environment_override(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DENTIVA_DATA_DIR", str(tmp_path / "custom"))
    assert data_root() == tmp_path / "custom"


def test_ensure_creates_every_managed_directory(tmp_path) -> None:
    paths = AppPaths.create(tmp_path / "data").ensure()
    for directory in (paths.logs, paths.attachments, paths.backups, paths.drafts, paths.security):
        assert directory.is_dir()
    assert paths.database.parent == paths.data


def test_within_refuses_traversal(tmp_path) -> None:
    import pytest

    paths = AppPaths.create(tmp_path / "data").ensure()
    assert paths.within("attachments", "p1", "file.pdf").is_absolute()
    with pytest.raises(ValueError):
        paths.within("..", "escape.txt")


def test_safe_filename_strips_directories_and_bad_characters() -> None:
    assert safe_filename("../../etc/passwd") == "passwd"
    assert safe_filename("report:2026?*.pdf") == "report2026.pdf"
    assert "/" not in safe_filename("a/b/c.pdf")
    assert safe_filename("") == "unnamed"
    assert safe_filename("  .  ") == "unnamed"
    long_name = safe_filename("a" * 300 + ".pdf")
    assert len(long_name) <= 120
    assert long_name.endswith(".pdf")


def test_assets_root_points_at_repository_assets() -> None:
    assert (assets_root() / "fonts").is_dir()
