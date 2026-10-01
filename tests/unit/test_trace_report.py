"""The traceability checker itself (REQ-TRC-002).

A checker that only ever passes is worse than no checker, so these tests feed it
deliberately broken documents and require it to notice.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("trace_report", ROOT / "tools" / "trace_report.py")
assert SPEC and SPEC.loader
trace_report = importlib.util.module_from_spec(SPEC)
sys.modules["trace_report"] = trace_report
SPEC.loader.exec_module(trace_report)


@pytest.fixture()
def _in_repo(monkeypatch: pytest.MonkeyPatch):
    """Tools and docs are addressed by relative path."""
    monkeypatch.chdir(ROOT)


def test_the_shipped_documents_agree(_in_repo: None) -> None:
    report = trace_report.build_report()
    assert report.requirements, "the baseline must define requirements"
    assert not report.unmapped, f"requirements with no matrix row: {report.unmapped}"
    assert not report.unknown, f"matrix rows with no requirement: {report.unknown}"
    assert not report.missing_test_files, report.missing_test_files
    assert not report.missing_named_tests, report.missing_named_tests
    assert not report.empty_test_files, report.empty_test_files
    assert trace_report.main([]) == 0


def test_every_requirement_has_a_priority(_in_repo: None) -> None:
    priorities = {requirement.priority for requirement in report_requirements()}
    assert priorities <= {"M", "S", "N"}, priorities
    assert "M" in priorities


def report_requirements() -> list[trace_report.Requirement]:
    return list(trace_report.build_report().requirements.values())


def test_a_verified_row_must_point_at_a_real_test(_in_repo: None, tmp_path: Path) -> None:
    matrix = tmp_path / "12.md"
    matrix.write_text(
        "| REQ | Requirement | Impl | Screen | Test | Status |\n"
        "|---|---|---|---|---|---|\n"
        "| GEN-001 | Product name | `app.py` | all | `tests/unit/test_does_not_exist.py` | V |\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "01.md"
    baseline.write_text("- **REQ-GEN-001 (M)** Product name.\n", encoding="utf-8")
    report = trace_report.build_report(baseline=baseline, matrix=matrix)
    assert [token for _, token in report.missing_test_files] == [
        "tests/unit/test_does_not_exist.py"
    ]
    assert trace_report.main(["--baseline", str(baseline), "--matrix", str(matrix)]) == 1


def test_a_planned_row_may_name_a_test_that_does_not_exist_yet(
    _in_repo: None, tmp_path: Path
) -> None:
    matrix = tmp_path / "12.md"
    matrix.write_text(
        "| REQ | Requirement | Impl | Screen | Test | Status |\n"
        "|---|---|---|---|---|---|\n"
        "| GEN-001 | Product name | `app.py` | all | `tests/unit/test_later.py` | P |\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "01.md"
    baseline.write_text("- **REQ-GEN-001 (M)** Product name.\n", encoding="utf-8")
    report = trace_report.build_report(baseline=baseline, matrix=matrix)
    assert report.missing_test_files == []
    assert [token for _, token in report.planned_test_targets] == ["tests/unit/test_later.py"]


def test_a_missing_requirement_row_is_reported(tmp_path: Path) -> None:
    matrix = tmp_path / "12.md"
    matrix.write_text(
        "| REQ | Requirement | Impl | Screen | Test | Status |\n"
        "|---|---|---|---|---|---|\n"
        "| GEN-002 | Something else | `app.py` | all | `tests/unit/test_errors.py` | V |\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "01.md"
    baseline.write_text(
        "- **REQ-GEN-001 (M)** Product name.\n- **REQ-GEN-002 (M)** Other.\n",
        encoding="utf-8",
    )
    report = trace_report.build_report(baseline=baseline, matrix=matrix)
    assert report.unmapped == ["GEN-001"]


def test_ranges_expand_and_statuses_are_counted_per_requirement(tmp_path: Path) -> None:
    assert trace_report._expand("AUD-001…003") == ("AUD-001", "AUD-002", "AUD-003")
    assert trace_report._expand("SET-001/002") == ("SET-001", "SET-002")
    assert trace_report._expand("GEN-007") == ("GEN-007",)
    assert trace_report._expand("nonsense") == ()

    matrix = tmp_path / "12.md"
    matrix.write_text(
        "| REQ | Requirement | Impl | Screen | Test | Status |\n"
        "|---|---|---|---|---|---|\n"
        "| AUD-001…003 | Audit | `audit_service` | Audit | `tests/unit/test_errors.py` | V |\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "01.md"
    baseline.write_text(
        "".join(f"- **REQ-AUD-00{n} (M)** Audit.\n" for n in (1, 2, 3)), encoding="utf-8"
    )
    report = trace_report.build_report(baseline=baseline, matrix=matrix)
    assert report.status_counts["V"] == 3
    assert report.unmapped == []


def test_release_mode_demands_verified_mandatory_requirements(tmp_path: Path) -> None:
    matrix = tmp_path / "12.md"
    baseline = tmp_path / "01.md"
    baseline.write_text(
        "- **REQ-GEN-001 (M)** Mandatory.\n- **REQ-KBD-003 (S)** Optional.\n", encoding="utf-8"
    )
    matrix.write_text(
        "| REQ | Requirement | Impl | Screen | Test | Status |\n"
        "|---|---|---|---|---|---|\n"
        "| GEN-001 | Mandatory | `a` | all | `tests/unit/test_errors.py` | I |\n"
        "| KBD-003 | Optional | `b` | all | `tests/unit/test_errors.py` | I |\n",
        encoding="utf-8",
    )
    payload_plain = trace_report._json_payload(
        trace_report.build_report(baseline=baseline, matrix=matrix), release=False
    )
    assert payload_plain["ok"] is True
    payload_release = trace_report._json_payload(
        trace_report.build_report(baseline=baseline, matrix=matrix), release=True
    )
    assert payload_release["ok"] is False
    assert payload_release["below_release"] == ["GEN-001"], "only the mandatory one blocks"
    assert (
        trace_report.main(["--release", "--baseline", str(baseline), "--matrix", str(matrix)]) == 1
    )


def test_a_named_test_node_id_is_checked(tmp_path: Path) -> None:
    matrix = tmp_path / "12.md"
    baseline = tmp_path / "01.md"
    baseline.write_text("- **REQ-GEN-001 (M)** Product name.\n", encoding="utf-8")
    matrix.write_text(
        "| REQ | Requirement | Impl | Screen | Test | Status |\n"
        "|---|---|---|---|---|---|\n"
        "| GEN-001 | Product name | `a` | all | "
        "`tests/unit/test_errors.py::test_no_such_test` | V |\n",
        encoding="utf-8",
    )
    report = trace_report.build_report(baseline=baseline, matrix=matrix)
    assert report.missing_named_tests, "a node id that does not exist must be reported"

    matrix.write_text(
        "| REQ | Requirement | Impl | Screen | Test | Status |\n"
        "|---|---|---|---|---|---|\n"
        "| GEN-001 | Product name | `a` | all | "
        "`tests/unit/test_errors.py::test_every_error_exposes_a_safe_message` | V |\n",
        encoding="utf-8",
    )
    report = trace_report.build_report(baseline=baseline, matrix=matrix)
    assert report.missing_named_tests == [], "an existing node id must be accepted"


def test_prefix_narrows_the_report() -> None:
    report = trace_report.build_report(prefix="AUTH")
    families = {identifier.split("-")[0] for row in report.rows for identifier in row.identifiers}
    assert families == {"AUTH"}
    assert len(report.rows) == 7


def test_a_missing_document_is_an_error_not_a_crash() -> None:
    assert trace_report.main(["--baseline", "nope.md", "--matrix", "nope.md"]) == 2
