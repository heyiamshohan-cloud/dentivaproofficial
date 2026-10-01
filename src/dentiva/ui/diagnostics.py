"""Programmatic UI checks used by tests, CI and the shipped ``--selftest`` mode.

These checks exist because "it renders" is not acceptance (REQ-UAA-002). They look
for the failure modes that matter on a real clinic desktop: content escaping its
container, clipped labels, overlapping siblings, accidental horizontal scrolling
and screens that cannot fit the smallest supported resolution.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QLabel, QLayout, QScrollArea, QSizePolicy, QWidget

ALLOWED_OVERFLOW_PX = 1
MIN_SUPPORTED_WIDTH = 1024
MIN_SUPPORTED_HEIGHT = 640


@dataclass(frozen=True, slots=True)
class LayoutIssue:
    """A single detected layout problem."""

    widget: str
    kind: str
    detail: str

    def describe(self) -> str:
        return f"[{self.kind}] {self.widget}: {self.detail}"


def audit_widget(root: QWidget) -> list[LayoutIssue]:
    """Inspect *root* and every descendant for layout defects."""
    issues: list[LayoutIssue] = []
    if root is None:
        return issues
    _audit_recursive(root, root.objectName() or root.__class__.__name__, issues)
    return issues


def _audit_recursive(widget: QWidget, path: str, issues: list[LayoutIssue]) -> None:
    label = f"{path}/{widget.objectName() or widget.__class__.__name__}"

    size = widget.size()
    if size.width() <= 0 or size.height() <= 0:
        # Not laid out yet (hidden tab, collapsed panel): nothing to assert.
        return

    # 1. children must stay inside their parent's content rectangle
    parent_rect = QRect(widget.rect())
    for child in widget.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
        if not child.isVisible() or child.isWindow():
            continue
        child_rect = QRect(child.geometry())
        if not parent_rect.adjusted(
            -ALLOWED_OVERFLOW_PX, -ALLOWED_OVERFLOW_PX, ALLOWED_OVERFLOW_PX, ALLOWED_OVERFLOW_PX
        ).contains(child_rect):
            overflow = _overflow_amount(child_rect, parent_rect)
            if overflow > ALLOWED_OVERFLOW_PX:
                issues.append(
                    LayoutIssue(
                        label,
                        "overflow",
                        f"child {child.objectName() or child.__class__.__name__} exceeds parent by "
                        f"{overflow}px (child={child_rect.width()}x{child_rect.height()} "
                        f"parent={parent_rect.width()}x{parent_rect.height()})",
                    )
                )

    # 2. labels must not be silently clipped
    if (
        isinstance(widget, QLabel)
        and widget.text()
        and not widget.hasScaledContents()
        and not widget.wordWrap()
    ):
        needed = widget.sizeHint().width()
        available = widget.width()
        elidable = widget.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Expanding
        overlong = needed - available > ALLOWED_OVERFLOW_PX
        if overlong and widget.text() not in ("", " ") and not elidable:
            issues.append(
                LayoutIssue(
                    label,
                    "clipped-label",
                    f"needs {needed}px, has {available}px, not elidable",
                )
            )

    # 3. horizontal scrolling is only acceptable where it is intentional
    content = widget.widget() if isinstance(widget, QScrollArea) else None
    if content is not None:
        bar = widget.horizontalScrollBar()
        content_wider = content.sizeHint().width() > widget.viewport().width() + ALLOWED_OVERFLOW_PX
        if bar is not None and bar.isVisible() and content_wider:
            issues.append(
                LayoutIssue(
                    label,
                    "horizontal-scroll",
                    f"content {content.sizeHint().width()}px wider than viewport "
                    f"{widget.viewport().width()}px",
                )
            )

    # 4. siblings inside the same layout must not overlap
    layout = widget.layout()
    if layout is not None:
        _audit_layout(layout, label, issues)

    for child in widget.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
        _audit_recursive(child, label, issues)


def _audit_layout(layout: QLayout, path: str, issues: list[LayoutIssue]) -> None:
    rects: list[tuple[str, QRect]] = []
    for index in range(layout.count()):
        item = layout.itemAt(index)
        if item is None or item.isEmpty():
            continue
        widget = item.widget()
        if widget is None or not widget.isVisible():
            continue
        rects.append((widget.objectName() or widget.__class__.__name__, QRect(widget.geometry())))
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            name_a, rect_a = rects[i]
            name_b, rect_b = rects[j]
            if not rect_a.intersects(rect_b):
                continue
            intersection = rect_a.intersected(rect_b)
            if (
                intersection.width() > ALLOWED_OVERFLOW_PX
                and intersection.height() > ALLOWED_OVERFLOW_PX
            ):
                issues.append(
                    LayoutIssue(
                        path,
                        "overlap",
                        f"{name_a} overlaps {name_b} by {intersection.width()}x"
                        f"{intersection.height()}px",
                    )
                )


def _overflow_amount(child: QRect, parent: QRect) -> int:
    return max(
        max(0, -child.left()),
        max(0, -child.top()),
        max(0, child.right() - parent.right()),
        max(0, child.bottom() - parent.bottom()),
    )


def audit_screen_fit(widget: QWidget, width: int, height: int) -> list[LayoutIssue]:
    """Check that *widget* fits the given viewport (REQ-RSP-001/003)."""
    issues: list[LayoutIssue] = []
    hint = widget.minimumSizeHint()
    if hint.width() > max(width, MIN_SUPPORTED_WIDTH):
        issues.append(
            LayoutIssue(
                widget.objectName() or widget.__class__.__name__,
                "min-width",
                f"minimum width {hint.width()}px exceeds viewport {width}px",
            )
        )
    if hint.height() > max(height, MIN_SUPPORTED_HEIGHT):
        issues.append(
            LayoutIssue(
                widget.objectName() or widget.__class__.__name__,
                "min-height",
                f"minimum height {hint.height()}px exceeds viewport {height}px",
            )
        )
    return issues
