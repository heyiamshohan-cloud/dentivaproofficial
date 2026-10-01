"""Qt stylesheet generated from :mod:`dentiva.ui.theme.tokens`.

Widgets select a visual variant through Qt dynamic properties (for example
``button.setProperty("variant", "primary")``), which keeps styling declarative and
consistent: no widget hard-codes colours, paddings or radii.
"""

from __future__ import annotations

from dentiva.ui.theme import tokens as t

_C = t.COLORS
_S = t.SPACING
_R = t.RADIUS
_T = t.TYPE


def _font_stack() -> str:
    """Ordered font families: native Latin first, bundled Unicode fallbacks after."""
    return ", ".join(
        f'"{family}"' for family in (_T.family_native, _T.family_ui, _T.family_bengali)
    )


def build_stylesheet(*, compact: bool = False) -> str:
    """Return the complete application stylesheet."""
    pad_x = _S.md if not compact else _S.sm
    pad_y = _S.sm if not compact else _S.xs
    return "\n".join(
        [
            _base(pad_x, pad_y),
            _buttons(),
            _inputs(),
            _tables(),
            _tabs(),
            _scrollbars(),
            _menus_and_tooltips(),
            _dialogs(),
            _displays(),
            _progress(),
        ]
    )


def _base(pad_x: int, pad_y: int) -> str:
    return f"""
/* ------------------------------------------------------------------ base -- */
QWidget {{
    color: {_C.ink};
    font-family: {_font_stack()};
    font-size: {_T.size_body}px;
    selection-background-color: {_C.primary_soft};
    selection-color: {_C.ink};
}}
QWidget#appRoot, QMainWindow, QMainWindow > QWidget {{
    background: {_C.canvas};
}}
QLabel {{
    background: transparent;
    color: {_C.ink};
}}
QLabel[role="caption"] {{
    color: {_C.ink_muted};
    font-size: {_T.size_caption}px;
}}
QLabel[role="heading"] {{
    color: {_C.ink};
    font-size: {_T.size_title}px;
    font-weight: {_T.weight_semibold};
}}
QLabel[role="display"] {{
    color: {_C.ink};
    font-size: {_T.size_display}px;
    font-weight: {_T.weight_semibold};
}}
QLabel[role="muted"] {{
    color: {_C.ink_muted};
}}
QLabel[role="number"] {{
    font-family: "{_T.family_monospace}";
    font-weight: {_T.weight_semibold};
}}
QFrame[role="divider"] {{
    background: {_C.border};
    max-height: 1px;
    min-height: 1px;
    border: none;
}}
QFrame[role="card"], QWidget[role="card"] {{
    background: {_C.surface};
    border: 1px solid {_C.border};
    border-radius: {_R.card}px;
}}
QFrame[role="section"], QWidget[role="section"] {{
    background: {_C.surface};
    border: 1px solid {_C.border};
    border-radius: {_R.card}px;
    padding: {pad_x}px;
}}
QWidget[role="surfaceAlt"] {{
    background: {_C.surface_alt};
    border-radius: {_R.control}px;
}}
QToolTip {{
    background: {_C.ink};
    color: {_C.ink_inverse};
    border: none;
    border-radius: {_R.control}px;
    padding: {_S.xs}px {_S.sm}px;
    font-size: {_T.size_caption}px;
}}
QSplitter::handle {{
    background: {_C.border};
}}
"""


def _buttons() -> str:
    return f"""
/* --------------------------------------------------------------- buttons -- */
QPushButton, QToolButton {{
    background: {_C.surface};
    border: 1px solid {_C.border_strong};
    border-radius: {_R.control}px;
    padding: {_S.sm}px {_S.lg}px;
    min-height: {t.SIZE.control_height - 10}px;
    color: {_C.ink};
    font-weight: {_T.weight_medium};
}}
QPushButton:hover, QToolButton:hover {{
    background: {_C.hover_soft};
    border-color: {_C.border_strong};
}}
QPushButton:pressed, QToolButton:pressed {{
    background: {_C.surface_sunken};
}}
QPushButton:focus-visible, QToolButton:focus-visible {{
    border-color: {_C.focus_ring};
    outline: 2px solid {_C.focus_ring}33;
}}
QPushButton:disabled, QToolButton:disabled {{
    color: {_C.disabled_text};
    background: {_C.disabled_surface};
    border-color: {_C.border};
}}
QPushButton[variant="primary"] {{
    background: {_C.primary};
    border-color: {_C.primary};
    color: {_C.ink_inverse};
}}
QPushButton[variant="primary"]:hover {{ background: {_C.primary_hover}; border-color: {_C.primary_hover}; }}
QPushButton[variant="primary"]:pressed {{ background: {_C.primary_press}; border-color: {_C.primary_press}; }}
QPushButton[variant="primary"]:disabled {{
    background: {_C.primary_border}; border-color: {_C.primary_border}; color: {_C.ink_inverse};
}}
QPushButton[variant="danger"] {{
    background: {_C.danger};
    border-color: {_C.danger};
    color: {_C.ink_inverse};
}}
QPushButton[variant="danger"]:hover {{ background: {_C.danger_hover}; border-color: {_C.danger_hover}; }}
QPushButton[variant="danger"]:pressed {{ background: {_C.danger_press}; border-color: {_C.danger_press}; }}
QPushButton[variant="ghost"], QToolButton[variant="ghost"] {{
    background: transparent;
    border-color: transparent;
}}
QPushButton[variant="ghost"]:hover, QToolButton[variant="ghost"]:hover {{
    background: {_C.hover_soft};
}}
QPushButton[variant="soft"] {{
    background: {_C.primary_soft};
    border-color: {_C.primary_border};
    color: {_C.primary};
}}
QPushButton[variant="subtle"] {{
    background: {_C.surface_alt};
    border-color: {_C.border};
}}
QPushButton[size="compact"], QToolButton[size="compact"] {{
    padding: {_S.xs}px {_S.sm}px;
    min-height: {t.SIZE.control_height_compact - 10}px;
}}
QPushButton[size="large"] {{
    padding: {_S.md}px {_S.xl}px;
    min-height: {t.SIZE.control_height_large - 14}px;
}}
QToolButton {{
    padding: {_S.xs}px;
    min-width: {t.SIZE.min_touch}px;
    min-height: {t.SIZE.min_touch}px;
}}
QToolButton[role="icon"], QPushButton[role="icon"] {{
    border-color: transparent;
    background: transparent;
    padding: {_S.xs}px;
}}
QToolButton[role="icon"]:hover, QPushButton[role="icon"]:hover {{ background: {_C.hover_soft}; }}
"""


def _inputs() -> str:
    return f"""
/* ---------------------------------------------------------------- inputs -- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit {{
    background: {_C.surface};
    border: 1px solid {_C.border_strong};
    border-radius: {_R.control}px;
    padding: {_S.xs + 2}px {_S.sm + 2}px;
    min-height: {t.SIZE.control_height - 14}px;
    selection-background-color: {_C.primary_soft};
}}
QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QDateEdit:hover {{
    border-color: {_C.ink_muted};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDateEdit:focus, QTimeEdit:focus {{
    border: 1px solid {_C.focus_ring};
    background: {_C.surface};
}}
QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled, QDateEdit:disabled {{
    background: {_C.disabled_surface};
    color: {_C.disabled_text};
}}
QLineEdit[state="error"], QTextEdit[state="error"] {{
    border-color: {_C.danger};
    background: {_C.danger_soft};
}}
QLineEdit[state="success"] {{
    border-color: {_C.success};
}}
QLineEdit[state="readonly"] {{
    background: {_C.surface_alt};
    color: {_C.ink_secondary};
}}
QComboBox {{
    background: {_C.surface};
    border: 1px solid {_C.border_strong};
    border-radius: {_R.control}px;
    padding: {_S.xs + 2}px {_S.sm + 2}px;
    min-height: {t.SIZE.control_height - 14}px;
}}
QComboBox:hover {{ border-color: {_C.ink_muted}; }}
QComboBox:focus {{ border-color: {_C.focus_ring}; }}
QComboBox:disabled {{ background: {_C.disabled_surface}; color: {_C.disabled_text}; }}
QComboBox::drop-down {{
    border: none;
    width: {t.SIZE.icon}px;
}}
QComboBox QAbstractItemView {{
    background: {_C.surface};
    border: 1px solid {_C.border};
    border-radius: {_R.control}px;
    selection-background-color: {_C.primary_soft};
    selection-color: {_C.ink};
    padding: {_S.xs}px;
}}
QCheckBox, QRadioButton {{
    spacing: {_S.sm}px;
    color: {_C.ink};
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: {t.SIZE.icon_small}px;
    height: {t.SIZE.icon_small}px;
    border: 1px solid {_C.border_strong};
    border-radius: 4px;
    background: {_C.surface};
}}
QRadioButton::indicator {{ border-radius: {t.SIZE.icon_small // 2}px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {_C.primary}; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background: {_C.primary};
    border-color: {_C.primary};
}}
QCheckBox:disabled, QRadioButton:disabled {{ color: {_C.disabled_text}; }}
QCheckBox::indicator:disabled {{ background: {_C.disabled_surface}; }}
"""


def _tables() -> str:
    return f"""
/* ---------------------------------------------------------------- tables -- */
QTableView, QTableWidget, QTreeView, QListView {{
    background: {_C.surface};
    border: 1px solid {_C.border};
    border-radius: {_R.card}px;
    gridline-color: {_C.border};
    selection-background-color: {_C.primary_soft};
    selection-color: {_C.ink};
    alternate-background-color: {_C.surface_alt};
}}
QTableView::item, QTableWidget::item {{
    padding: {_S.xs}px {_S.sm}px;
    border-bottom: 1px solid {_C.border};
}}
QTableView::item:selected, QTableWidget::item:selected {{
    background: {_C.primary_soft};
    color: {_C.ink};
}}
QTableView::item:hover, QTableWidget::item:hover {{
    background: {_C.hover_soft};
}}
QHeaderView {{
    background: {_C.surface};
    border: none;
}}
QHeaderView::section {{
    background: {_C.surface_alt};
    color: {_C.ink_secondary};
    border: none;
    border-bottom: 1px solid {_C.border};
    border-right: 1px solid {_C.border};
    padding: {_S.sm}px;
    font-weight: {_T.weight_semibold};
    font-size: {_T.size_caption}px;
}}
QHeaderView::section:last {{ border-right: none; }}
QTableCornerButton::section {{ background: {_C.surface_alt}; border: none; }}
"""


def _tabs() -> str:
    return f"""
/* ------------------------------------------------------------------ tabs -- */
QTabWidget::pane {{
    background: {_C.canvas};
    border: none;
    border-top: 1px solid {_C.border};
    top: -1px;
}}
QTabBar {{
    background: transparent;
    qproperty-drawBase: 0;
}}
QTabBar::tab {{
    background: transparent;
    color: {_C.ink_secondary};
    padding: {_S.sm + 2}px {_S.lg}px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: {_T.weight_medium};
    margin-right: {_S.xs}px;
}}
QTabBar::tab:hover {{
    color: {_C.ink};
    background: {_C.hover_soft};
    border-radius: {_R.control}px {_R.control}px 0 0;
}}
QTabBar::tab:selected {{
    color: {_C.primary};
    border-bottom: 2px solid {_C.primary};
    background: transparent;
}}
QTabBar::tab:disabled {{ color: {_C.disabled_text}; }}
QTabBar::tab:focus-visible {{
    outline: none;
    border-bottom: 2px solid {_C.focus_ring};
}}
QFrame[role="segmented"] {{
    background: {_C.surface_sunken};
    border-radius: {_R.control}px;
}}
QPushButton[role="segment"] {{
    background: transparent;
    border: none;
    border-radius: {_R.control}px;
    padding: {_S.xs}px {_S.lg}px;
    color: {_C.ink_secondary};
}}
QPushButton[role="segment"]:hover {{ color: {_C.ink}; }}
QPushButton[role="segment"][segment-selected="true"] {{
    background: {_C.surface};
    color: {_C.primary};
    font-weight: {_T.weight_semibold};
}}
"""


def _scrollbars() -> str:
    return f"""
/* ------------------------------------------------------------ scroll bars -- */
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
    margin: 0px;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background: {_C.border_strong};
    border-radius: 6px;
    min-height: 32px;
    min-width: 32px;
}}
QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
    background: {_C.ink_muted};
}}
QScrollBar::add-line, QScrollBar::sub-line {{ background: transparent; height: 0px; width: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
"""


def _menus_and_tooltips() -> str:
    return f"""
/* ------------------------------------------------------------ menus, tips -- */
QMenu {{
    background: {_C.surface};
    border: 1px solid {_C.border};
    border-radius: {_R.card}px;
    padding: {_S.xs}px;
}}
QMenu::item {{
    padding: {_S.xs + 2}px {_S.lg}px;
    border-radius: {_R.control}px;
    color: {_C.ink};
}}
QMenu::item:selected {{ background: {_C.primary_soft}; color: {_C.ink}; }}
QMenu::item:disabled {{ color: {_C.disabled_text}; }}
QMenu::separator {{ height: 1px; background: {_C.border}; margin: {_S.xs}px {_S.sm}px; }}
QMenu::indicator {{ width: {t.SIZE.icon_small}px; height: {t.SIZE.icon_small}px; }}
"""


def _dialogs() -> str:
    return f"""
/* --------------------------------------------------------------- dialogs -- */
QDialog {{
    background: {_C.surface};
}}
QDialog[role="panel"] {{
    border-radius: {_R.dialog}px;
}}
QFrame[role="dialogHeader"] {{
    background: {_C.surface};
    border-bottom: 1px solid {_C.border};
}}
QFrame[role="dialogFooter"] {{
    background: {_C.surface_alt};
    border-top: 1px solid {_C.border};
}}
QFrame[role="banner"] {{
    border-radius: {_R.control}px;
    padding: {_S.sm}px {_S.md}px;
}}
QFrame[role="banner"][tone="info"] {{ background: {_C.info_soft}; border: 1px solid {_C.info}; }}
QFrame[role="banner"][tone="success"] {{ background: {_C.success_soft}; border: 1px solid {_C.success}; }}
QFrame[role="banner"][tone="warning"] {{ background: {_C.warning_soft}; border: 1px solid {_C.warning}; }}
QFrame[role="banner"][tone="danger"] {{ background: {_C.danger_soft}; border: 1px solid {_C.danger}; }}
QFrame[role="banner"][tone="neutral"] {{ background: {_C.surface_sunken}; border: 1px solid {_C.border}; }}
"""


def _displays() -> str:
    return f"""
/* ------------------------------------------------- badges, chips, avatars -- */
QLabel[role="badge"], QFrame[role="pill"] {{
    border-radius: {t.RADIUS.pill // 10}px;
    padding: 2px {_S.sm}px;
    font-size: {_T.size_caption}px;
    font-weight: {_T.weight_semibold};
}}
QLabel[role="badge"][tone="success"] {{ background: {_C.success_soft}; color: {_C.success}; }}
QLabel[role="badge"][tone="warning"] {{ background: {_C.warning_soft}; color: {_C.warning}; }}
QLabel[role="badge"][tone="danger"] {{ background: {_C.danger_soft}; color: {_C.danger}; }}
QLabel[role="badge"][tone="info"] {{ background: {_C.info_soft}; color: {_C.info}; }}
QLabel[role="badge"][tone="neutral"] {{ background: {_C.surface_sunken}; color: {_C.ink_secondary}; }}
QLabel[role="badge"][tone="primary"] {{ background: {_C.primary_soft}; color: {_C.primary}; }}
QLabel[role="avatar"] {{
    background: {_C.primary_soft};
    color: {_C.primary};
    border-radius: {t.SIZE.avatar // 2}px;
    font-weight: {_T.weight_semibold};
}}
QLabel[role="chip"] {{
    background: {_C.surface_sunken};
    border-radius: {t.RADIUS.pill // 10}px;
    padding: 2px {_S.sm}px;
    color: {_C.ink_secondary};
    font-size: {_T.size_caption}px;
}}
QLabel[role="emptyIcon"] {{
    color: {_C.ink_muted};
}}
"""


def _progress() -> str:
    return f"""
/* -------------------------------------------------------------- progress -- */
QProgressBar {{
    background: {_C.surface_sunken};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {_C.primary};
    border-radius: 4px;
}}
QProgressBar[state="error"]::chunk {{ background: {_C.danger}; }}
QProgressBar[state="success"]::chunk {{ background: {_C.success}; }}
QFrame[role="skeleton"] {{
    background: {_C.surface_sunken};
    border-radius: {_R.control}px;
}}
"""
