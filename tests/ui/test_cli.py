"""Command line entry points: version, build info, self-test, layout audit.

REQ-OPS-002 (diagnostics), REQ-RSP-001 (layout audit gate).
"""

from __future__ import annotations

import pytest

from dentiva import __version__
from dentiva.main import main


def test_version_and_build_info_exit_cleanly(capsys) -> None:
    with pytest.raises(SystemExit) as exit_info:  # argparse handles --version itself
        main(["--version"])
    assert exit_info.value.code == 0
    assert "Dentiva Pro" in capsys.readouterr().out
    assert main(["--build-info"]) == 0
    assert __version__ in capsys.readouterr().out


def test_self_test_passes_end_to_end(capsys) -> None:
    assert main(["--selftest"]) == 0
    output = capsys.readouterr().out
    assert "result   : PASS" in output
    assert "shell" in output


@pytest.mark.usefixtures("themed_app")
def test_layout_audit_reports_no_defects(capsys) -> None:
    assert main(["--audit-layout"]) == 0
    output = capsys.readouterr().out
    assert "PASS (0 issues)" in output


@pytest.mark.usefixtures("themed_app")
def test_layout_audit_runs_at_a_scaling_factor(capsys) -> None:
    import os

    assert main(["--audit-layout", "--scale", "1.5"]) == 0
    assert os.environ["QT_SCALE_FACTOR"] == "1.5"
    assert "PASS (0 issues)" in capsys.readouterr().out


def test_scale_outside_the_supported_range_is_refused() -> None:
    with pytest.raises(SystemExit):
        main(["--audit-layout", "--scale", "9"])


@pytest.mark.usefixtures("data_dir")
def test_diagnostics_bundle_is_written(tmp_path) -> None:
    target = tmp_path / "bundle.json"
    assert main(["--diagnostics", str(target)]) == 0
    content = target.read_text(encoding="utf-8")
    assert "selftest" in content and "log_tail" in content
