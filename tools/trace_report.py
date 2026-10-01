"""Cross-check the requirements traceability matrix (REQ-TRC-001/002).

Two documents have to agree with each other and with the code:

* ``docs/01-requirements-baseline.md`` — the frozen requirement list, each with a
  priority: **M** mandatory (release-blocking), **S** should-have, **N** out of
  scope by decision;
* ``docs/12-requirements-traceability.md`` — the matrix: one row per requirement
  (or per contiguous range) with the implementation target, the screen, the test
  target and a status of **P** planned · **IP** in progress · **I** implemented ·
  **V** verified · **R** released.

The checker reports, and fails on:

1. a requirement from the baseline that has no row in the matrix;
2. a matrix row whose *Test* column points at a test file that does not exist
   (a renamed test silently un-verifies a requirement);
3. a test file that contains no tests at all;
4. with ``--release``: any **M** requirement whose status is below **V**.

Usage::

    python tools/trace_report.py                  # report + structural failures
    python tools/trace_report.py --release        # + every M must be verified
    python tools/trace_report.py --json           # machine readable (CI)
    python tools/trace_report.py --prefix AUTH    # one requirement family
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

#: Statuses, weakest first.
STATUS_ORDER = ("P", "IP", "I", "V", "R")
RELEASE_STATUS = "V"

BASELINE_DOC = Path("docs/01-requirements-baseline.md")
MATRIX_DOC = Path("docs/12-requirements-traceability.md")
TESTS_ROOT = Path("tests")

#: ``**REQ-GEN-001 (M)**`` in the baseline.
_BASELINE_ID = re.compile(r"REQ-([A-Z]+)-(\d+)\s*\(([MSN])\)")
#: ``AUD-001…003`` / ``SET-001/002`` / ``GEN-001`` in the matrix.
_ROW_ID = re.compile(r"^([A-Z]+)-(.+)$")
#: Backticked tokens inside a table cell.
_CODE = re.compile(r"`([^`]+)`")

#: Test-column entries that are procedures rather than files, and therefore not
#: resolvable on disk. They are reported as "process" and never counted as broken.
PROCEDURE_HINTS = ("CI", "job", "gate", "review", "n/a", "process", "release", "checklist")


@dataclass(frozen=True, slots=True)
class Requirement:
    """One row of the baseline."""

    identifier: str
    family: str
    priority: str


@dataclass(frozen=True, slots=True)
class MatrixRow:
    """One row of the traceability matrix."""

    cell: str
    identifiers: tuple[str, ...]
    requirement: str
    implementation: str
    screen: str
    test_target: str
    status: str


@dataclass(slots=True)
class Report:
    """Everything the tool found out."""

    requirements: dict[str, Requirement] = field(default_factory=dict)
    rows: list[MatrixRow] = field(default_factory=list)
    unmapped: list[str] = field(default_factory=list)
    unknown: list[str] = field(default_factory=list)
    missing_test_files: list[tuple[str, str]] = field(default_factory=list)
    planned_test_targets: list[tuple[str, str]] = field(default_factory=list)
    missing_named_tests: list[tuple[str, str]] = field(default_factory=list)
    empty_test_files: list[str] = field(default_factory=list)
    process_targets: list[str] = field(default_factory=list)
    test_counts: dict[str, int] = field(default_factory=dict)

    @property
    def status_counts(self) -> Counter[str]:
        """How many requirements sit in each status (ranges counted per ID)."""
        counts: Counter[str] = Counter()
        for row in self.rows:
            counts[row.status] += len(row.identifiers)
        return counts

    @property
    def below_release(self) -> list[str]:
        """Mandatory requirements that are not yet verified."""
        rank = STATUS_ORDER.index(RELEASE_STATUS)
        return sorted(
            identifier
            for row in self.rows
            for identifier in row.identifiers
            if self.requirements.get(identifier, Requirement(identifier, identifier, "M")).priority
            == "M"
            and STATUS_ORDER.index(row.status) < rank
        )


# ------------------------------------------------------------------- parsing --


def parse_baseline(path: Path) -> dict[str, Requirement]:
    """Read the requirement list with its priorities."""
    text = path.read_text(encoding="utf-8")
    requirements: dict[str, Requirement] = {}
    for family, number, priority in _BASELINE_ID.findall(text):
        identifier = f"{family}-{int(number):03d}"
        requirements[identifier] = Requirement(identifier, family, priority)
    return requirements


def _expand(cell: str) -> tuple[str, ...]:
    """``AUD-001…003`` → ``AUD-001, AUD-002, AUD-003``; ``SET-001/002`` → both."""
    match = _ROW_ID.match(cell.strip())
    if not match:
        return ()
    family, rest = match.groups()
    numbers = [int(value) for value in re.findall(r"\d+", rest)]
    if not numbers:
        return ()
    if "…" in rest or "..." in rest:
        return tuple(f"{family}-{value:03d}" for value in range(numbers[0], numbers[-1] + 1))
    return tuple(f"{family}-{value:03d}" for value in numbers)


def parse_matrix(path: Path) -> list[MatrixRow]:
    """Read every data row of the matrix (header rows are skipped)."""
    rows: list[MatrixRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.count("|") != 7:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        identifier, requirement, implementation, screen, test_target, status = cells
        if identifier in ("REQ", "") or status == "Status" or set(identifier) <= set("-: "):
            continue  # header or separator row
        if not _expand(identifier):
            continue
        rows.append(
            MatrixRow(
                cell=identifier,
                identifiers=_expand(identifier),
                requirement=requirement,
                implementation=implementation,
                screen=screen,
                test_target=test_target,
                status=status,
            )
        )
    return rows


# -------------------------------------------------------------- test targets --


def _resolve(token: str) -> tuple[str, ...]:
    """Resolve a Test-column token to concrete files (a path or a glob)."""
    candidate = Path(token)
    if token.startswith("tests/") or token.startswith("tools/"):
        if "*" in token:
            matches = sorted(path for path in Path().glob(token) if path.is_file())
            return tuple(str(path) for path in matches) if matches else ()
        return (token,) if candidate.is_file() else ()
    if token.endswith(".py"):
        # A bare file name: find it wherever it lives under tests/.
        matches = sorted(TESTS_ROOT.rglob(Path(token).name))
        return tuple(str(path) for path in matches)
    return ()


def count_tests(path: Path) -> int:
    """Number of ``test_*`` functions in a test module (0 when unreadable)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):  # pragma: no cover - defensive
        return 0
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )


def build_report(
    *, baseline: Path = BASELINE_DOC, matrix: Path = MATRIX_DOC, prefix: str = ""
) -> Report:
    """Compare the two documents with each other and with the test suite."""
    report = Report(requirements=parse_baseline(baseline), rows=parse_matrix(matrix))
    if prefix:
        wanted = prefix.upper()
        report.rows = [row for row in report.rows if row.identifiers[0].startswith(wanted)]
    mapped = {identifier for row in report.rows for identifier in row.identifiers}
    report.unmapped = sorted(
        identifier
        for identifier, requirement in report.requirements.items()
        if identifier not in mapped
        and identifier.split("-")[0] == (prefix.upper() if prefix else identifier.split("-")[0])
    )
    report.unknown = sorted(
        identifier for identifier in mapped if identifier not in report.requirements
    )

    #: A row only *has* to point at a real test once it claims work was done.
    #: Planned rows (P/IP) legitimately name files a later phase will write.
    required = ("I", "V", "R")

    seen: set[str] = set()
    for row in report.rows:
        for token in _tokens(row.test_target):
            path_token, _, node = token.partition("::")
            resolved = _resolve(path_token)
            if not (path_token.endswith(".py") or "*" in path_token):
                if any(hint in token for hint in PROCEDURE_HINTS) and (
                    token not in report.process_targets
                ):
                    report.process_targets.append(token)
                continue
            if not resolved:
                if row.status in required:
                    report.missing_test_files.append((row.cell, token))
                else:
                    report.planned_test_targets.append((row.cell, token))
                continue
            for path in resolved:
                if node and node not in _test_names(Path(path)):
                    report.missing_named_tests.append((row.cell, token))
                if path in seen:
                    continue
                seen.add(path)
                report.test_counts[path] = count_tests(Path(path))
    report.empty_test_files = sorted(
        path
        for path, count in report.test_counts.items()
        if count == 0 and Path(path).name != "conftest.py"
    )
    return report


def _tokens(cell: str) -> list[str]:
    """Every target named in a *Test* cell, backticked or bare."""
    tokens = [token.strip() for token in _CODE.findall(cell) if token.strip()]
    if not tokens and cell.strip() not in ("", "—", "-"):
        tokens = [cell.strip()]
    return tokens


def _test_names(path: Path) -> set[str]:
    """Names of the ``test_*`` functions in *path*."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):  # pragma: no cover - defensive
        return set()
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


# ------------------------------------------------------------------ printing --


def print_report(report: Report, *, release: bool) -> None:
    """Write a human-readable summary to stdout."""
    print("Dentiva Pro — requirements traceability report")
    print(f"baseline   : {len(report.requirements)} requirements")
    print(f"matrix     : {len(report.rows)} rows")
    counts = report.status_counts
    covered = sum(counts.values())
    print(
        "status     : "
        + ", ".join(f"{name}={counts.get(name, 0)}" for name in reversed(STATUS_ORDER))
        + f"  (of {covered} mapped)"
    )
    per_family = Counter(requirement.priority for requirement in report.requirements.values())
    print(
        "priority   : " + ", ".join(f"{name}={per_family.get(name, 0)}" for name in ("M", "S", "N"))
    )
    print(
        f"test files : {len(report.test_counts)} referenced, "
        f"{sum(report.test_counts.values())} tests collected by AST"
    )
    if report.planned_test_targets:
        print(f"planned    : {len(report.planned_test_targets)} test targets for later phases")
    if report.process_targets:
        print(f"process    : {len(report.process_targets)} targets verified by review/CI")

    problems = 0
    if report.unmapped:
        problems += len(report.unmapped)
        print(
            f"\n[FAIL] unmapped requirements ({len(report.unmapped)}): "
            f"{', '.join(report.unmapped[:20])}"
        )
    if report.unknown:
        problems += len(report.unknown)
        print(
            f"\n[FAIL] matrix rows with no baseline requirement ({len(report.unknown)}): "
            f"{', '.join(report.unknown[:20])}"
        )
    if report.missing_test_files:
        problems += 1
        print(
            f"\n[FAIL] verified rows whose test target does not exist "
            f"({len(report.missing_test_files)}):"
        )
        for cell, token in report.missing_test_files[:40]:
            print(f"         {cell}: {token}")
    if report.missing_named_tests:
        problems += 1
        print(f"\n[FAIL] named tests that do not exist ({len(report.missing_named_tests)}):")
        for cell, token in report.missing_named_tests[:40]:
            print(f"         {cell}: {token}")
    if report.empty_test_files:
        problems += len(report.empty_test_files)
        print(
            f"\n[FAIL] test modules with no tests ({len(report.empty_test_files)}): "
            f"{', '.join(report.empty_test_files)}"
        )
    if release and report.below_release:
        problems += 1
        print(
            f"\n[FAIL] {len(report.below_release)} mandatory requirements are not yet "
            f"verified ({RELEASE_STATUS}):"
        )
        print(
            f"         {', '.join(report.below_release[:40])}"
            f"{' …' if len(report.below_release) > 40 else ''}"
        )
    if not problems:
        print("\n[PASS] the matrix agrees with the baseline and the test suite")
    else:
        print(f"\nresult     : FAIL ({problems} problem group(s))")


def _json_payload(report: Report, *, release: bool) -> dict[str, object]:
    """Machine-readable form for CI."""
    return {
        "requirements": len(report.requirements),
        "rows": len(report.rows),
        "status_counts": dict(report.status_counts),
        "test_files": len(report.test_counts),
        "tests_collected": sum(report.test_counts.values()),
        "unmapped": report.unmapped,
        "unknown": report.unknown,
        "planned_test_targets": len(report.planned_test_targets),
        "missing_test_files": [list(item) for item in report.missing_test_files],
        "missing_named_tests": [list(item) for item in report.missing_named_tests],
        "empty_test_files": report.empty_test_files,
        "below_release": report.below_release if release else [],
        "ok": not (
            report.unmapped
            or report.unknown
            or report.missing_test_files
            or report.missing_named_tests
            or report.empty_test_files
            or (release and report.below_release)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--release",
        action="store_true",
        help=f"fail when a mandatory requirement is not at least {RELEASE_STATUS}",
    )
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--prefix", default="", help="restrict to one requirement family")
    parser.add_argument("--baseline", type=Path, default=BASELINE_DOC)
    parser.add_argument("--matrix", type=Path, default=MATRIX_DOC)
    args = parser.parse_args(argv)

    for path in (args.baseline, args.matrix):
        if not path.is_file():
            print(f"missing document: {path}", file=sys.stderr)
            return 2

    report = build_report(baseline=args.baseline, matrix=args.matrix, prefix=args.prefix)
    if args.json:
        print(json.dumps(_json_payload(report, release=args.release), indent=2))
    else:
        print_report(report, release=args.release)
    return 0 if _json_payload(report, release=args.release)["ok"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
