"""Dentiva Pro command line entry point.

Usage:
    DentivaPro.exe                 launch the desktop application
    DentivaPro.exe --version       print the version and exit
    DentivaPro.exe --selftest      run the headless self-test and print a report
    DentivaPro.exe --diagnostics   write a support bundle and print its path
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dentiva import __product_name__, __version__
from dentiva.buildinfo import BUILD


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="DentivaPro",
        description=f"{__product_name__} — offline dental clinic management",
    )
    parser.add_argument("--version", action="version", version=f"{__product_name__} {__version__}")
    parser.add_argument(
        "--selftest", action="store_true", help="run the headless self-test and exit"
    )
    parser.add_argument(
        "--diagnostics", metavar="FILE", nargs="?", const="", help="write a diagnostics bundle"
    )
    parser.add_argument("--build-info", action="store_true", help="print build metadata and exit")
    parser.add_argument(
        "--audit-layout",
        action="store_true",
        help="build every screen and audit it at every supported resolution",
    )
    parser.add_argument(
        "--scale",
        metavar="FACTOR",
        default=None,
        help="Windows scaling factor to audit/start with (1.0, 1.25, 1.5, 1.75, 2.0)",
    )
    return parser


def _parse_scale(value: str) -> float:
    """Validate a --scale factor; anything outside the supported set is refused."""
    try:
        factor = float(value)
    except ValueError:
        raise SystemExit(f"--scale expects a number, got {value!r}") from None
    if not 0.5 <= factor <= 4.0:
        raise SystemExit(f"--scale {value} is outside the supported range 0.5–4.0")
    return factor


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.scale:
        # Must be set before QApplication is constructed (Qt reads it once).
        os.environ["QT_SCALE_FACTOR"] = str(_parse_scale(args.scale))

    if args.audit_layout:
        from dentiva.diagnostics import audit_layout, audit_layout_report_text

        report = audit_layout()
        print(audit_layout_report_text(report))
        return 0 if report["ok"] else 1

    if args.build_info:
        print(BUILD.describe())
        return 0

    if args.selftest:
        from dentiva.diagnostics import run_selftest, selftest_report_text

        report = run_selftest(with_gui=True)
        print(selftest_report_text(report))
        return 0 if report["ok"] else 1

    if args.diagnostics is not None:
        from dentiva.core.logging_setup import configure_logging
        from dentiva.core.paths import AppPaths
        from dentiva.diagnostics import export_diagnostics_bundle

        paths = AppPaths.create().ensure()
        configure_logging(paths, console=False)
        target = (
            Path(args.diagnostics) if args.diagnostics else paths.logs / "dentiva-diagnostics.json"
        )
        written = export_diagnostics_bundle(target, paths=paths)
        print(f"Diagnostics bundle written to {written}")
        return 0

    try:
        from dentiva.app import Application
    except ImportError as error:  # pragma: no cover - missing Qt on a headless box
        print(f"The graphical interface could not be started ({error}).", file=sys.stderr)
        print("Run `DentivaPro --selftest` for a headless diagnostic report.", file=sys.stderr)
        return 2

    return Application().run()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
