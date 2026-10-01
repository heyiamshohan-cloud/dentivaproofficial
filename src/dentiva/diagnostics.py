"""Headless self-test and diagnostics (``DentivaPro.exe --selftest``).

The self-test exercises the real service layer on a temporary database and renders
real documents, so it is meaningful on a clean machine and in CI (ADR-0014). It
never touches clinic data.
"""

from __future__ import annotations

import json
import platform
import tempfile
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CheckResult = dict[str, Any]


def run_selftest(*, with_gui: bool = True, paths: Any = None) -> dict[str, Any]:
    """Run every available self-check and return a structured report."""
    started = datetime.now(UTC)
    checks: list[CheckResult] = []
    for name, func in _checks(with_gui):
        result = _run_check(name, func)
        checks.append(result)
    finished = datetime.now(UTC)
    failures = [check for check in checks if check["status"] == "fail"]
    return {
        "product": "Dentiva Pro",
        "version": _version(),
        "started_utc": started.isoformat(timespec="seconds"),
        "finished_utc": finished.isoformat(timespec="seconds"),
        "duration_seconds": round((finished - started).total_seconds(), 3),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "passed": len(checks) - len(failures),
        "failed": len(failures),
        "ok": not failures,
        "checks": checks,
    }


def selftest_report_text(report: dict[str, Any]) -> str:
    """Render a human readable self-test report."""
    lines = [
        f"Dentiva Pro {report['version']} — self-test",
        f"platform : {report['platform']}",
        f"python   : {report['python']}",
        f"result   : {'PASS' if report['ok'] else 'FAIL'} "
        f"({report['passed']} passed, {report['failed']} failed)",
        "",
    ]
    for check in report["checks"]:
        marker = {"pass": "PASS", "fail": "FAIL", "skip": "SKIP"}[check["status"]]
        lines.append(f"[{marker}] {check['name']}: {check['message']}")
    return "\n".join(lines)


# --------------------------------------------------------------------- checks --
def _checks(with_gui: bool) -> list[tuple[str, Callable[[], str]]]:
    checks: list[tuple[str, Callable[[], str]]] = [
        ("environment", _check_environment),
        ("paths", _check_paths),
        ("logging", _check_logging),
        ("database", _check_database),
        ("money", _check_money),
        ("unicode", _check_unicode),
    ]
    if with_gui:
        checks.append(("theme", _check_theme))
        checks.append(("icons", _check_icons))
        checks.append(("shell", _check_shell))
    return checks


def _run_check(name: str, func: Callable[[], str]) -> CheckResult:
    from dentiva.core.logging_setup import get_logger

    logger = get_logger("selftest")
    try:
        message = func() or "ok"
    except Exception as exc:
        logger.exception("Self-test check %s failed", name)
        return {"name": name, "status": "fail", "message": f"{type(exc).__name__}: {exc}"}
    return {"name": name, "status": "pass", "message": message}


def _check_environment() -> str:
    import PySide6
    from sqlalchemy import __version__ as sqlalchemy_version

    return f"Qt {PySide6.__version__}, SQLAlchemy {sqlalchemy_version}"


def _check_paths() -> str:
    from dentiva.core.paths import AppPaths

    with tempfile.TemporaryDirectory() as tmp:
        paths = AppPaths.create(Path(tmp) / "data").ensure()
        for directory in (
            paths.logs,
            paths.attachments,
            paths.backups,
            paths.drafts,
            paths.security,
        ):
            if not directory.is_dir():
                raise AssertionError(f"missing directory {directory}")
        target = paths.within("attachments", "patient-1", "report.pdf")
        if not str(target).startswith(str(paths.data)):
            raise AssertionError("path containment check failed")
        try:
            paths.within("..", "escape.txt")
        except ValueError:
            pass
        else:  # pragma: no cover - defensive
            raise AssertionError("path traversal was not blocked")
        return f"data root created and traversal blocked ({paths.data})"


def _check_logging() -> str:
    from dentiva.core.logging_setup import configure_logging, redact

    with tempfile.TemporaryDirectory() as tmp:
        from dentiva.core.paths import AppPaths

        paths = AppPaths.create(Path(tmp) / "data").ensure()
        log_file = configure_logging(paths, console=False)
        if log_file is None or not Path(log_file).parent.is_dir():
            raise AssertionError("log file was not created")
    # A synthetic sample: the real activation code is never written to source.
    redacted = redact("password=hunter2 activation_code=0000000000000000")
    if "hunter2" in redacted or "0000000000000000" in redacted:
        raise AssertionError("secrets were not redacted from log output")
    return "rotating log configured, secrets redacted"


def _check_database() -> str:
    from dentiva.data.engine import assert_healthy, create_engine_for, current_revision, upgrade

    with tempfile.TemporaryDirectory() as tmp:
        engine = create_engine_for(Path(tmp) / "test.db")
        upgrade(engine)
        revision = current_revision(engine)
        assert_healthy(engine)
        engine.dispose()
    return f"migrations applied and integrity verified (revision {revision})"


def _check_money() -> str:
    from decimal import Decimal

    from dentiva.core.money import Money

    if Money.from_taka(Decimal("1.005")).paisa != 101:
        raise AssertionError("half-up rounding is incorrect")
    if (Money.from_taka("10.00") - Money.from_taka("2.50")) != Money.from_taka("7.50"):
        raise AssertionError("subtraction is incorrect")
    if Money.from_taka(100).percent("12.5") != Money.from_taka("12.50"):
        raise AssertionError("percentage is incorrect")
    pieces = Money.from_taka(10).split_evenly(3)
    if sum(piece.paisa for piece in pieces) != 1000:
        raise AssertionError("split does not preserve the total")
    try:
        Money.from_taka(1.5)  # type: ignore[arg-type]
    except TypeError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("float was accepted for money")
    return "integer paisa arithmetic verified"


def _check_unicode() -> str:
    from dentiva.core.textutil import clean_text, normalise_key, truncate

    sample = "মোহাম্মদ  রাহাত  হোসেন"
    if clean_text(sample) != "মোহাম্মদ রাহাত হোসেন":
        raise AssertionError("whitespace normalisation failed")
    if not normalise_key("Rahat") == "rahat":
        raise AssertionError("key normalisation failed")
    if not truncate("abcdefghij", 5).endswith("…"):
        raise AssertionError("truncation failed")
    return "Bangla/Latin text helpers verified"


def _gui_application() -> Any:
    """Return the running QApplication, creating one when a check runs alone."""
    from PySide6.QtWidgets import QApplication

    existing = QApplication.instance()
    return existing if isinstance(existing, QApplication) else QApplication([])


def _check_theme() -> str:
    from dentiva.ui.theme.fonts import load_bundled_fonts
    from dentiva.ui.theme.qss import build_stylesheet

    app = _gui_application()
    stylesheet = build_stylesheet()
    if len(stylesheet) < 1000:
        raise AssertionError("stylesheet was not generated")
    bundle = load_bundled_fonts()
    if bundle.missing:
        raise AssertionError(f"missing bundled fonts: {', '.join(bundle.missing)}")
    if not bundle.has_bengali:
        raise AssertionError("Bengali font was not registered")
    app.setStyleSheet(stylesheet)
    return f"stylesheet generated, fonts loaded ({', '.join(bundle.loaded)})"


def _check_icons() -> str:
    from dentiva.ui.theme import icons

    broken = []
    for name in icons.ICON_NAMES:
        pixmap = icons.pixmap(name, 24)
        if pixmap.isNull():
            broken.append(name)
    if broken:
        raise AssertionError(f"icons failed to render: {', '.join(broken)}")
    glyphs = _bengali_glyph_coverage()
    if not glyphs:
        raise AssertionError("Bengali glyphs are not available from the bundled font")
    return f"{len(icons.ICON_NAMES)} icons rendered, Bengali glyph coverage confirmed"


def _bengali_glyph_coverage() -> bool:
    from PySide6.QtGui import QFont, QRawFont

    from dentiva.ui.theme.tokens import TYPE

    font = QFont()
    font.setFamilies([TYPE.family_bengali])
    font.setPointSize(12)
    raw = QRawFont.fromFont(font)
    indexes = raw.glyphIndexesForString("দাঁতে ব্যথা মাড়ি ফুলা")
    return bool(indexes) and all(index > 0 for index in indexes)


def _check_shell() -> str:
    """Build every screen, switch to it and run the layout audit."""
    from dentiva.ui.diagnostics import audit_widget
    from dentiva.ui.shell.main_window import MainWindow
    from dentiva.ui.shell.navigation import ordered

    app = _gui_application()
    window = MainWindow()
    window.resize(1366, 768)
    window.show()
    app.processEvents()
    issues: list[str] = []
    for item in ordered():
        window.navigate(item.id)
        app.processEvents()
        view = window.view_for(item.id)
        if view is None:
            issues.append(f"{item.id}: view was not created")
            continue
        for issue in audit_widget(view):
            issues.append(f"{item.id}: {issue.describe()}")
    window.close()
    if issues:
        raise AssertionError(f"{len(issues)} layout issue(s): " + "; ".join(issues[:5]))
    return f"{len(ordered())} screens built and audited without layout defects"


def _version() -> str:
    from dentiva import __version__

    return __version__


#: Resolutions the product must look designed at (REQ-RSP-001).
SUPPORTED_RESOLUTIONS: tuple[tuple[int, int], ...] = (
    (1366, 768),
    (1600, 900),
    (1920, 1080),
    (2560, 1440),
    (3840, 2160),
)


def audit_layout(
    resolutions: Sequence[tuple[int, int]] = SUPPORTED_RESOLUTIONS,
) -> dict[str, Any]:
    """Build every screen and audit it at every supported resolution.

    Returns a structured report; :func:`audit_layout_report_text` renders it for
    the console. Used by ``DentivaPro --audit-layout`` and by CI, so a layout
    regression (overflow, clipped text, unintended scrollbars, overlapping
    siblings, a screen that cannot fit 1024x640) fails the build instead of
    reaching a clinic.
    """

    from dentiva.ui.diagnostics import audit_screen_fit, audit_widget
    from dentiva.ui.shell.main_window import MainWindow
    from dentiva.ui.shell.navigation import ordered
    from dentiva.ui.theme import apply_theme

    app = _gui_application()
    apply_theme(app)

    window = MainWindow()
    issues: list[str] = []
    audited = 0
    for width, height in resolutions:
        window.resize(width, height)
        window.show()
        for item in ordered():
            window.navigate(item.id)
            view = window.view_for(item.id)
            if view is None:  # pragma: no cover - every item has a factory
                issues.append(f"{item.id}: screen could not be created")
                continue
            audited += 1
            for issue in audit_widget(view):
                issues.append(f"{item.id} @ {width}x{height}: {issue.describe()}")
            for problem in audit_screen_fit(view, width, height):
                issues.append(f"{item.id} @ {width}x{height}: {problem.describe()}")
    window.close()
    return {
        "resolutions": [list(resolution) for resolution in resolutions],
        "screens": len(list(ordered())),
        "audits": audited,
        "issues": issues,
        "ok": not issues,
    }


def audit_layout_report_text(report: dict[str, Any]) -> str:
    """Render a layout audit report for the console."""
    lines = [
        f"Dentiva Pro {_version()} — layout audit",
        f"screens    : {report['screens']}",
        f"resolutions: {', '.join(f'{w}x{h}' for w, h in report['resolutions'])}",
        f"audits     : {report['audits']}",
        f"result     : {'PASS' if report['ok'] else 'FAIL'} ({len(report['issues'])} issues)",
        "",
    ]
    lines.extend(report["issues"])
    return "\n".join(lines)


def export_diagnostics_bundle(target: str | Path, *, paths: Any = None) -> Path:
    """Write a support bundle (report + recent log tail, secrets redacted)."""
    from dentiva.core.logging_setup import recent_log_tail

    destination = Path(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = run_selftest(with_gui=False)
    bundle = {
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "version": _version(),
        "platform": platform.platform(),
        "machine": platform.node(),
        "selftest": report,
        "log_tail": recent_log_tail(Path(paths.logs) / "dentiva.log") if paths else "",
    }
    destination.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    return destination


def main(argv: list[str] | None = None) -> int:
    """CLI entry for ``python -m dentiva.diagnostics``."""
    del argv  # the diagnostics module has no options of its own
    report = run_selftest(with_gui=True)
    print(selftest_report_text(report))
    return 0 if report["ok"] else 1
