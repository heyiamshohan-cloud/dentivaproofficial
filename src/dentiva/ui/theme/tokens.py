"""Design tokens — the single source of truth for the Dentiva Pro visual language.

Every colour, spacing step, radius, font size, elevation and duration used by the
interface is defined here. :mod:`dentiva.ui.theme.qss` turns these tokens into a
Qt stylesheet, so no widget may hard-code a visual value (REQ-UIX-009).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ColorTokens:
    """Clinical, calm, premium palette (light theme)."""

    # surfaces
    canvas: str = "#F4F7F9"
    surface: str = "#FFFFFF"
    surface_alt: str = "#F8FAFB"
    surface_sunken: str = "#EDF2F5"
    overlay: str = "#0E2A32B3"

    # borders
    border: str = "#E2E8EC"
    border_strong: str = "#CBD5DB"

    # ink
    ink: str = "#0E2A32"
    ink_secondary: str = "#405A63"
    ink_muted: str = "#7A8F98"
    ink_inverse: str = "#FFFFFF"

    # brand
    primary: str = "#0F8B8D"
    primary_hover: str = "#0C7476"
    primary_press: str = "#0A6365"
    primary_soft: str = "#E6F4F4"
    primary_border: str = "#B9DFDF"
    accent: str = "#22C1C3"

    # semantic
    success: str = "#1FA463"
    success_soft: str = "#E8F6EE"
    warning: str = "#D9822B"
    warning_soft: str = "#FDF3E7"
    danger: str = "#D64545"
    danger_soft: str = "#FCECEC"
    danger_hover: str = "#BF3A3A"
    danger_press: str = "#A73232"
    info: str = "#2F80ED"
    info_soft: str = "#EAF2FE"

    # interaction
    hover_soft: str = "#F1F5F7"
    selected: str = "#E6F4F4"
    disabled_text: str = "#A9B7BD"
    disabled_surface: str = "#F2F5F7"
    focus_ring: str = "#0F8B8D"


@dataclass(frozen=True, slots=True)
class SpacingTokens:
    """8 px grid."""

    xxs: int = 2
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 20
    xxl: int = 24
    xxxl: int = 32
    huge: int = 40
    giant: int = 48


@dataclass(frozen=True, slots=True)
class RadiusTokens:
    control: int = 6
    card: int = 10
    dialog: int = 14
    pill: int = 999


@dataclass(frozen=True, slots=True)
class TypographyTokens:
    """Windows-native first (Segoe UI) with bundled Unicode fallbacks."""

    family_native: str = "Segoe UI"
    family_ui: str = "Noto Sans"
    family_bengali: str = "Noto Sans Bengali"
    family_monospace: str = "Consolas"

    size_micro: int = 10
    size_caption: int = 12
    size_body: int = 13
    size_subtitle: int = 15
    size_title: int = 18
    size_headline: int = 22
    size_display: int = 28

    weight_regular: int = 400
    weight_medium: int = 500
    weight_semibold: int = 600

    line_height: float = 1.45


@dataclass(frozen=True, slots=True)
class ElevationTokens:
    card: str = "0 1px 2px rgba(14, 42, 50, 0.06)"
    popover: str = "0 8px 24px rgba(14, 42, 50, 0.12)"
    modal: str = "0 24px 64px rgba(14, 42, 50, 0.18)"


@dataclass(frozen=True, slots=True)
class MotionTokens:
    micro_ms: int = 90
    standard_ms: int = 160
    panel_ms: int = 220
    easing: str = "cubic-bezier(0.2, 0.8, 0.2, 1)"


@dataclass(frozen=True, slots=True)
class SizeTokens:
    """Control metrics derived from the spacing/typography scales."""

    control_height: int = 34
    control_height_compact: int = 28
    control_height_large: int = 40
    icon: int = 24
    icon_small: int = 16
    sidebar_width: int = 248
    sidebar_width_collapsed: int = 68
    header_height: int = 64
    row_height: int = 40
    avatar: int = 40
    avatar_large: int = 72
    min_touch: int = 32


@dataclass(frozen=True, slots=True)
class BreakpointTokens:
    """Logical width breakpoints (device independent pixels)."""

    xs: int = 1100
    sm: int = 1360
    md: int = 1700
    lg: int = 2200


COLORS = ColorTokens()
SPACING = SpacingTokens()
RADIUS = RadiusTokens()
TYPE = TypographyTokens()
ELEVATION = ElevationTokens()
MOTION = MotionTokens()
SIZE = SizeTokens()
BREAKPOINTS = BreakpointTokens()

DENSITY_PADDING = SPACING.md
CARD_GAP = SPACING.lg


def status_color(status: str) -> str:
    """Map a semantic status name to its colour token."""
    return {
        "success": COLORS.success,
        "paid": COLORS.success,
        "completed": COLORS.success,
        "warning": COLORS.warning,
        "due": COLORS.warning,
        "pending": COLORS.warning,
        "danger": COLORS.danger,
        "overdue": COLORS.danger,
        "failed": COLORS.danger,
        "info": COLORS.info,
        "scheduled": COLORS.info,
        "neutral": COLORS.ink_muted,
        "cancelled": COLORS.ink_muted,
    }.get(status.lower(), COLORS.ink_muted)


def status_soft(status: str) -> str:
    """Map a semantic status name to its soft background token."""
    return {
        "success": COLORS.success_soft,
        "paid": COLORS.success_soft,
        "completed": COLORS.success_soft,
        "warning": COLORS.warning_soft,
        "due": COLORS.warning_soft,
        "pending": COLORS.warning_soft,
        "danger": COLORS.danger_soft,
        "overdue": COLORS.danger_soft,
        "failed": COLORS.danger_soft,
        "info": COLORS.info_soft,
        "scheduled": COLORS.info_soft,
        "neutral": COLORS.surface_sunken,
        "cancelled": COLORS.surface_sunken,
    }.get(status.lower(), COLORS.surface_sunken)
