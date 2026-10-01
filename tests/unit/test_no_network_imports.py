"""The product must be able to run with the network cable unplugged.

REQ-GEN-005 / REQ-GEN-006: no cloud service, no paid SDK, no telemetry and —
above all — no code path that can send clinic data off the machine. Nothing can
be sent if nothing that can send is ever imported.

This test walks every module in ``src/dentiva`` and fails if a networking
module is imported. Qt's own ``QtNetwork`` is refused too: it is not needed by
an offline-first clinic application, and banning it keeps the guarantee
mechanical rather than a matter of discipline.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "dentiva"

#: Top-level modules that can open a socket or issue an HTTP request.
FORBIDDEN_ROOTS = frozenset(
    {
        "socket",
        "ssl",
        "http",
        "urllib",
        "urllib2",
        "ftplib",
        "smtplib",
        "requests",
        "httpx",
        "aiohttp",
        "urllib3",
        "telnetlib",
        "xmlrpc",
        "websockets",
        "socketserver",
        "asyncio",  # Qt already provides the event loop; async I/O hides network use
    }
)

FORBIDDEN_QUALIFIED = frozenset({"PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineCore"})

#: Qt's network module is allowed for **local IPC only** (the single-instance
#: guard uses QLocalServer/QLocalSocket, which never touch a network interface).
LOCAL_IPC_ONLY = {"PySide6.QtNetwork": {"QLocalServer", "QLocalSocket"}}


def _python_files() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module)
    return roots


def _imported_names(tree: ast.AST) -> dict[str, set[str]]:
    """Map ``module -> imported names`` for ``from X import a, b`` statements."""
    imported: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.setdefault(node.module, set()).update(alias.name for alias in node.names)
    return imported


def test_no_module_imports_networking() -> None:
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for name in _imported_roots(tree):
            if name in FORBIDDEN_QUALIFIED or name.split(".")[0] in FORBIDDEN_ROOTS:
                offenders.append(f"{path.relative_to(SRC)}: {name}")
        imported = _imported_names(tree)
        for module, allowed in LOCAL_IPC_ONLY.items():
            used = imported.get(module)
            if used is not None and not used <= allowed:
                offenders.append(
                    f"{path.relative_to(SRC)}: {module} may only be used for "
                    f"{sorted(allowed)}, found {sorted(used - allowed)}"
                )
    assert not offenders, "network capable imports found:\n" + "\n".join(offenders)


def test_the_source_tree_is_actually_scanned() -> None:
    """Guard against the check silently passing because the path drifted."""
    files = _python_files()
    assert len(files) > 20, f"expected the real source tree, found {len(files)} files"


def test_no_plaintext_activation_code_in_the_source() -> None:
    """REQ-SEC-001: the fixed activation code must never appear as text."""
    pattern = "1516591935015165"
    offenders = [
        str(path.relative_to(SRC))
        for path in _python_files()
        if pattern in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"activation code found in: {offenders}"
