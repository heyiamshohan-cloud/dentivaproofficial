"""In-house SVG icon set (ADR-0013).

Icons are described as a list of primitives on a 24×24 grid and rendered through
``QSvgRenderer`` at the requested size and device pixel ratio, so they stay sharp
at any Windows scaling (100 %–200 %) and can be recoloured with the design tokens.

No third-party icon pack is bundled: no extra licence, no icon-font alignment
problems next to Bangla text.
"""

from __future__ import annotations

from typing import Final

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

GRID: Final = 24
STROKE_WIDTH: Final = 1.7

#: Available icon names, for documentation and tests.
ICON_NAMES: Final[tuple[str, ...]] = (
    "about",
    "accounting",
    "appointments",
    "arrowDown",
    "arrowUp",
    "audit",
    "backup",
    "bell",
    "calendar",
    "check",
    "chevronDown",
    "chevronLeft",
    "chevronRight",
    "chevronUp",
    "clock",
    "close",
    "dashboard",
    "download",
    "edit",
    "error",
    "file",
    "filter",
    "health",
    "image",
    "info",
    "inventory",
    "invoice",
    "lock",
    "logout",
    "menu",
    "minus",
    "moreHorizontal",
    "patients",
    "phone",
    "payments",
    "plus",
    "prescriptions",
    "printer",
    "queue",
    "refresh",
    "save",
    "search",
    "settings",
    "staff",
    "treatments",
    "trash",
    "upload",
    "user",
    "warning",
)

_ICONS: Final[dict[str, tuple[str, ...]]] = {
    "dashboard": ("r:3,3,8,8,2", "r:13,3,8,5,2", "r:13,10,8,11,2", "r:3,13,8,8,2"),
    "patients": ("c:12,8,4", "d:M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"),
    "phone": (
        "d:M6 3h3l2 5-2.5 1.5a12 12 0 0 0 6 6L16 13l5 2v3a2 2 0 0 1-2 2 "
        "A16 16 0 0 1 4 5a2 2 0 0 1 2-2z",
    ),
    "appointments": ("r:3,5,18,16,2", "l:3,10,21,10", "l:8,3,8,7", "l:16,3,16,7"),
    "queue": ("c:4,6,1", "c:4,12,1", "c:4,18,1", "l:9,6,21,6", "l:9,12,21,12", "l:9,18,21,18"),
    "treatments": (
        "d:M12 3.5c-2.8 0-5.5 1.4-5.5 4.6 0 2.2-1.2 3.4-1.2 5.6 0 2.3 1.4 3.8 3.2 3.8 1.5 0 2.3-1 "
        "2.9-2.6l.3-.8c.4-1.2.9-1.8 1.8-1.8s1.4.6 1.8 1.8l.3.8c.6 1.6 1.4 2.6 2.9 2.6 1.8 0 "
        "3.2-1.5 "
        "3.2-3.8 0-2.2-1.2-3.4-1.2-5.6 0-3.2-2.7-4.6-5.5-4.6z",
    ),
    "prescriptions": ("r:6,2,12,20,2", "l:9,7,15,7", "l:9,12,15,12", "l:9,17,13,17"),
    "invoice": ("d:M5 2h14v20l-3-2-2 2-2-2-2 2-2-2-3 2z", "l:9,8,15,8", "l:9,13,15,13"),
    "payments": ("r:2,5,20,14,2", "l:2,10,22,10", "r:6,14,5,2,1"),
    "inventory": ("d:M3 7l9-4 9 4v10l-9 4-9-4z", "l:3,7,12,11", "l:21,7,12,11", "l:12,11,12,21"),
    "accounting": ("p:3,3,3,21,21,21", "r:6,12,3,6,1", "r:11,8,3,10,1", "r:16,14,3,4,1"),
    "staff": (
        "r:2,4,20,16,2",
        "c:8,10,2.4",
        "d:M5 17c0-1.7 1.3-3 3-3s3 1.3 3 3",
        "l:14,9,19,9",
        "l:14,13,19,13",
    ),
    "backup": ("r:3,4,18,16,2", "l:3,9,21,9", "l:3,15,21,15"),
    "settings": ("l:4,7,20,7", "c:9,7,2.3", "l:4,17,20,17", "c:15,17,2.3"),
    "about": ("c:12,12,9", "l:12,11,12,16", "c:12,8,0.9"),
    "audit": ("d:M12 3l8 3v6c0 5-3.5 8.3-8 9-4.5-.7-8-4-8-9V6z", "d:m9 12 2 2 4-4"),
    "health": ("p:2,12,7,12,10,5,14,19,17,12,22,12",),
    "search": ("c:11,11,7", "l:16.4,16.4,21,21"),
    "bell": ("d:M6 9a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6", "d:M10 20a2 2 0 0 0 4 0"),
    "lock": ("r:5,11,14,10,2", "d:M8 11V8a4 4 0 0 1 8 0v3"),
    "logout": (
        "d:M15 5H7a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h8",
        "l:11,12,21,12",
        "l:17,7,21,12",
        "l:21,12,17,17",
    ),
    "chevronLeft": ("p:15,6,9,12,15,18",),
    "chevronRight": ("p:9,6,15,12,9,18",),
    "chevronDown": ("p:6,9,12,15,18,9",),
    "chevronUp": ("p:6,15,12,9,18,15",),
    "plus": ("l:12,5,12,19", "l:5,12,19,12"),
    "minus": ("l:5,12,19,12",),
    "close": ("l:6,6,18,18", "l:18,6,6,18"),
    "check": ("p:5,13,10,18,19,7",),
    "edit": ("d:M4 20h4l10-10-4-4L4 16z", "l:14,6,18,10"),
    "trash": (
        "l:4,7,20,7",
        "d:M6 7l1 13h10l1-13",
        "d:M9 7V4h6v3",
        "l:10,11,10,17",
        "l:14,11,14,17",
    ),
    "printer": ("d:M6 9V3h12v6", "r:3,9,18,7,2", "d:M6 14h12v7H6z"),
    "save": ("d:M5 3h11l3 3v15H5z", "d:M8 3v6h8V3", "r:8,13,8,8,1"),
    "warning": ("d:M12 4l9 16H3z", "l:12,10,12,14", "c:12,17,0.9"),
    "error": ("c:12,12,9", "l:12,8,12,13", "c:12,16,0.9"),
    "info": ("c:12,12,9", "l:12,11,12,17", "c:12,8,0.9"),
    "calendar": ("r:3,5,18,16,2", "l:3,10,21,10", "l:8,3,8,7", "l:16,3,16,7"),
    "clock": ("c:12,12,9", "p:12,7,12,12,16,14"),
    "user": ("c:12,8,4", "d:M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"),
    "upload": ("l:12,16,12,4", "p:7,9,12,4,17,9", "d:M4 17v3h16v-3"),
    "download": ("l:12,4,12,16", "p:7,13,12,18,17,13", "d:M4 17v3h16v-3"),
    "filter": ("d:M3 5h18l-7 8v6l-4-2v-4z",),
    "refresh": ("d:M19.5 12a7.5 7.5 0 1 1-2.2-5.3", "d:M20 4v5h-5"),
    "moreHorizontal": ("c:5,12,1.6", "c:12,12,1.6", "c:19,12,1.6"),
    "menu": ("l:4,7,20,7", "l:4,12,20,12", "l:4,17,20,17"),
    "arrowUp": ("l:12,19,12,5", "p:6,11,12,5,18,11"),
    "arrowDown": ("l:12,5,12,19", "p:6,13,12,19,18,13"),
    "file": ("d:M6 3h8l4 4v14H6z", "d:M14 3v4h4"),
    "image": ("r:3,4,18,16,2", "c:8.5,9.5,2", "d:M4 18l5-5 4 4 3-3 4 4"),
}


def _escape_color(color: str) -> str:
    return QColor(color).name(QColor.NameFormat.HexRgb)


def _primitive_to_svg(item: str, color: str) -> str:
    kind, _, values = item.partition(":")
    if kind == "d":
        return f'<path d="{values}"/>'
    numbers = [float(part) for part in values.split(",")] if values else []
    if kind == "r" and len(numbers) >= 4:
        radius = numbers[4] if len(numbers) > 4 else 2.0
        return (
            f'<rect x="{numbers[0]}" y="{numbers[1]}" width="{numbers[2]}" height="{numbers[3]}" '
            f'rx="{radius}" ry="{radius}"/>'
        )
    if kind == "c" and len(numbers) >= 3:
        return f'<circle cx="{numbers[0]}" cy="{numbers[1]}" r="{numbers[2]}"/>'
    if kind == "l" and len(numbers) >= 4:
        return f'<line x1="{numbers[0]}" y1="{numbers[1]}" x2="{numbers[2]}" y2="{numbers[3]}"/>'
    if kind == "p" and len(numbers) >= 4:
        pairs = " ".join(f"{numbers[i]},{numbers[i + 1]}" for i in range(0, len(numbers) - 1, 2))
        return f'<polyline points="{pairs}"/>'
    raise ValueError(f"Unknown icon primitive: {item!r}")


def build_svg(name: str, color: str = "#0E2A32", *, stroke_width: float = STROKE_WIDTH) -> bytes:
    """Return the SVG document for *name* as UTF-8 bytes."""
    if name not in _ICONS:
        raise KeyError(f"Unknown icon: {name!r}")
    stroke = _escape_color(color)
    body = "".join(_primitive_to_svg(item, stroke) for item in _ICONS[name])
    document = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {GRID} {GRID}" width="{GRID}" '
        f'height="{GRID}" fill="none" stroke="{stroke}" stroke-width="{stroke_width}" '
        f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
    )
    return document.encode("utf-8")


_CACHE: dict[tuple[str, str, int, int], QPixmap] = {}


def _render(name: str, color: str, size: int, dpr: float) -> QPixmap:
    key = (name, color, size, round(dpr * 100))
    cached = _CACHE.get(key)
    if cached is not None and not cached.isNull():
        return cached
    renderer = QSvgRenderer(QByteArray(build_svg(name, color)))
    if not renderer.isValid():  # pragma: no cover - indicates malformed icon data
        raise ValueError(f"Icon {name!r} produced invalid SVG")
    pixmap = QPixmap(int(size * dpr), int(size * dpr))
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(dpr)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    _CACHE[key] = pixmap
    return pixmap


def pixmap(name: str, size: int = 24, color: str = "#0E2A32", *, dpr: float = 1.0) -> QPixmap:
    """Return a cached, DPR-aware pixmap for *name*."""
    return _render(name, color, size, dpr)


def icon(name: str, size: int = 24, color: str = "#0E2A32", *, dpr: float = 1.0) -> QIcon:
    """Return a :class:`QIcon` for *name*."""
    return QIcon(pixmap(name, size, color, dpr=dpr))


def icon_for_state(name: str, *, size: int = 24, dpr: float = 1.0, **states: str) -> QIcon:
    """Build an icon with per-mode colours, e.g. ``Normal``/``Disabled``/``Active``."""
    from PySide6.QtGui import QIcon as _QIcon

    result = _QIcon()
    mapping = {
        _QIcon.Mode.Normal: states.get("normal", "#0E2A32"),
        _QIcon.Mode.Disabled: states.get("disabled", "#A9B7BD"),
        _QIcon.Mode.Active: states.get("active", states.get("normal", "#0E2A32")),
        _QIcon.Mode.Selected: states.get("selected", states.get("normal", "#0E2A32")),
    }
    for mode, color in mapping.items():
        result.addPixmap(_render(name, color, size, dpr), mode, _QIcon.State.On)
        result.addPixmap(_render(name, color, size, dpr), mode, _QIcon.State.Off)
    return result


def clear_cache() -> None:
    """Drop cached pixmaps (used when the device pixel ratio changes)."""
    _CACHE.clear()


def available_icons() -> tuple[str, ...]:
    """Names of every icon in the set."""
    return tuple(sorted(_ICONS))


def icon_size(size: int = 24) -> QSize:
    return QSize(size, size)
