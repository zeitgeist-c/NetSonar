"""NetSonar's central, dependency-free Qt theme definition.

The module deliberately keeps the historic ``C`` color lookup available while
also exposing the richer ``THEME`` dictionary used by the new components.  Qt
stylesheets are generated at runtime so tests, previews, and future themes can
override individual tokens without duplicating a large QSS string.

Palette: "Grafit & Kobalt" (option D) -- neutral graphite surfaces with a
cobalt accent.  Chosen for dense table/chart screens where legibility and a
tool-like feel beat decoration.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


COLORS: dict[str, str] = {
    # Historic keys -- do not rename: older screens import these directly.
    "bg": "#0B0D10",
    "bg1": "#13161B",
    "bg2": "#1A1E25",
    "bg3": "#22262E",
    "border": "#2B313B",
    "border2": "#3A4150",
    "accent": "#4C8DFF",
    "accent2": "#2A4E8C",
    "teal": "#3EC8BE",
    "danger": "#FF5F6E",
    "warning": "#F0B94F",
    "success": "#35D07F",
    "purple": "#A78BFA",
    "text": "#EEF2F8",
    "text2": "#C7CEDB",
    "text3": "#8A93A3",
    "mono": "Cascadia Mono",
    # Additional semantic aliases for new code.
    "surface": "#13161B",
    "surface_raised": "#1A1E25",
    "surface_hover": "#22262E",
    "surface_active": "#262C36",
    "accent_hover": "#7AA8FF",
    "accent_pressed": "#3D71CC",
    "focus": "#9DC0FF",
    "disabled_bg": "#171A1F",
    "disabled_text": "#5C636E",
    # Pre-blended tints.  Qt parses QSS alpha per platform, so every translucent
    # surface is emitted as a solid hex blended over the colour behind it.
    "tint_accent_bg": "#1F293B",
    "tint_accent_border": "#2A426B",
    "tint_success_bg": "#1D302E",
    "tint_success_border": "#235742",
    "tint_warning_bg": "#2F2E29",
    "tint_warning_border": "#5E5032",
    "tint_danger_bg": "#31242C",
    "tint_danger_border": "#63333C",
    "nav_active_bg": "#1B273B",
    "nav_active_border": "#213352",
    "table_sel_bg": "#223048",
    "table_hover_bg": "#1E2634",
    "btn_danger_bg": "#35262E",
    "btn_danger_border": "#813B46",
    "btn_danger_hover": "#482B34",
    "btn_success_bg": "#1D3330",
    "btn_success_border": "#266E4E",
    "btn_success_hover": "#1F4237",
    "input_hover_border": "#293F66",
    "card_hover_border": "#354D76",
    "menu_hover_bg": "#202B3F",
    "primary_grad_a": "#2A4E8C",
    "primary_grad_b": "#4C8DFF",
    "primary_hover_a": "#3560B0",
    "primary_hover_b": "#7AA8FF",
    "primary_press_a": "#24406F",
    "primary_press_b": "#3D71CC",
}

FONTS: dict[str, str] = {
    # These are all present on supported Windows versions. Qt selects the first
    # installed family in the list and safely falls back to its default font.
    "ui": "'Segoe UI Variable', 'Segoe UI', sans-serif",
    "display": "'Segoe UI Variable Display', 'Segoe UI', sans-serif",
    "mono": "'Cascadia Mono', 'Cascadia Code', 'Consolas', monospace",
}

THEME: dict[str, Any] = {
    **COLORS,
    "colors": COLORS,
    "fonts": FONTS,
    "radius": {"sm": 5, "md": 8, "lg": 12, "xl": 16},
    "spacing": {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24},
    "motion": {"fast": 120, "normal": 160, "slow": 180},
}

# Backwards-compatible palette name used throughout app_gui.py.  It aliases the
# central theme (rather than copying it), so overrides stay consistent.
C = THEME


def _resolved_tokens(overrides: Mapping[str, Any] | None) -> tuple[dict[str, str], dict[str, str]]:
    """Return color and font tokens with optional shallow/nested overrides."""

    colors = dict(COLORS)
    fonts = dict(FONTS)
    if not overrides:
        return colors, fonts

    nested_colors = overrides.get("colors")
    if isinstance(nested_colors, Mapping):
        colors.update({key: str(value) for key, value in nested_colors.items() if key in colors})
    nested_fonts = overrides.get("fonts")
    if isinstance(nested_fonts, Mapping):
        fonts.update({key: str(value) for key, value in nested_fonts.items() if key in fonts})

    colors.update({key: str(value) for key, value in overrides.items() if key in colors})
    return colors, fonts


def build_stylesheet(overrides: Mapping[str, Any] | None = None) -> str:
    """Build the application QSS from theme tokens.

    ``overrides`` can contain historic flat color keys (for example
    ``{"accent": "#00AAFF"}``) or nested ``colors`` / ``fonts`` dictionaries.
    The resulting stylesheet uses only syntax supported by Qt 6.
    """

    c, f = _resolved_tokens(overrides)
    return f"""
/* ---------- Application shell and typography ---------- */
QApplication, QMainWindow, QDialog {{
    background-color: {c['bg']};
    color: {c['text']};
    font-family: {f['ui']};
    font-size: 13px;
}}
QWidget {{
    color: {c['text']};
    font-family: {f['ui']};
    font-size: 13px;
}}
QWidget#appRoot, QWidget#pageRoot {{ background-color: {c['bg']}; }}
QLabel {{ background-color: transparent; border: none; }}
QLabel#title, QLabel[role="pageTitle"] {{
    color: {c['text']};
    font-family: {f['display']};
    font-size: 22px;
    font-weight: 700;
}}
QLabel#subtitle, QLabel[role="pageSubtitle"] {{
    color: {c['text3']};
    font-size: 12px;
}}
QLabel[role="eyebrow"] {{
    color: {c['accent']};
    font-family: {f['mono']};
    font-size: 10px;
    font-weight: 700;
}}
QLabel[role="sectionLabel"] {{
    color: {c['text3']};
    font-family: {f['mono']};
    font-size: 10px;
    font-weight: 700;
}}

/* ---------- Buttons ---------- */
QPushButton, QToolButton {{
    min-height: 30px;
    padding: 0 14px;
    background-color: {c['bg3']};
    color: {c['text2']};
    border: 1px solid {c['border2']};
    border-radius: 7px;
    font-weight: 600;
}}
QPushButton:hover, QToolButton:hover {{
    background-color: {c['surface_active']};
    color: {c['text']};
    border-color: {c['accent2']};
}}
QPushButton:pressed, QToolButton:pressed {{
    background-color: {c['border']};
    color: {c['text']};
    border-color: {c['accent']};
}}
QPushButton:focus, QToolButton:focus {{
    border: 1px solid {c['focus']};
}}
QPushButton:disabled, QToolButton:disabled {{
    background-color: {c['disabled_bg']};
    color: {c['disabled_text']};
    border-color: {c['border']};
}}

QPushButton[variant="primary"], QPushButton#primary {{
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
        stop:0 {c['primary_grad_a']}, stop:1 {c['primary_grad_b']});
    color: #FFFFFF;
    border: 1px solid {c['accent']};
    font-weight: 700;
}}
QPushButton[variant="primary"]:hover, QPushButton#primary:hover {{
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
        stop:0 {c['primary_hover_a']}, stop:1 {c['primary_hover_b']});
    border-color: {c['focus']};
}}
QPushButton[variant="primary"]:pressed, QPushButton#primary:pressed {{
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
        stop:0 {c['primary_press_a']}, stop:1 {c['primary_press_b']});
}}
QPushButton[variant="primary"]:checked, QPushButton#primary:checked {{
    background-color: {c['accent_pressed']};
    border-color: {c['focus']};
}}

QPushButton[variant="secondary"] {{
    background-color: {c['bg3']};
    color: {c['text2']};
    border-color: {c['border2']};
}}
QPushButton[variant="secondary"]:checked {{
    background-color: {c['surface_active']};
    color: {c['accent']};
    border-color: {c['accent2']};
}}

QPushButton[variant="ghost"], QPushButton#ghost {{
    background-color: transparent;
    color: {c['text2']};
    border-color: transparent;
}}
QPushButton[variant="ghost"]:hover, QPushButton#ghost:hover {{
    background-color: {c['bg3']};
    color: {c['text']};
    border-color: {c['border']};
}}
QPushButton[variant="ghost"]:checked, QPushButton#ghost:checked {{
    background-color: {c['nav_active_bg']};
    color: {c['accent']};
    border-color: {c['nav_active_border']};
}}

QPushButton[variant="success"], QPushButton#success {{
    background-color: {c['btn_success_bg']};
    color: {c['success']};
    border-color: {c['btn_success_border']};
}}
QPushButton[variant="success"]:hover, QPushButton#success:hover {{
    background-color: {c['btn_success_hover']};
    border-color: {c['success']};
}}
QPushButton[variant="success"]:pressed, QPushButton[variant="success"]:checked,
QPushButton#success:pressed, QPushButton#success:checked {{
    background-color: {c['btn_success_border']};
}}

QPushButton[variant="danger"], QPushButton#danger {{
    background-color: {c['btn_danger_bg']};
    color: {c['danger']};
    border-color: {c['btn_danger_border']};
}}
QPushButton[variant="danger"]:hover, QPushButton#danger:hover {{
    background-color: {c['btn_danger_hover']};
    border-color: {c['danger']};
}}
QPushButton[variant="danger"]:pressed, QPushButton[variant="danger"]:checked,
QPushButton#danger:pressed, QPushButton#danger:checked {{
    background-color: {c['btn_danger_border']};
}}
QPushButton[busy="true"] {{ color: {c['text2']}; }}

/* Segmented switch used by the merged "Kurallar" page. */
QPushButton[segment="true"] {{
    background-color: transparent;
    color: {c['text3']};
    border: 1px solid {c['border']};
    border-radius: 7px;
    font-weight: 600;
}}
QPushButton[segment="true"]:hover {{
    color: {c['text']};
    border-color: {c['border2']};
    background-color: {c['bg3']};
}}
QPushButton[segment="true"]:checked {{
    background-color: {c['nav_active_bg']};
    color: {c['accent']};
    border-color: {c['nav_active_border']};
    font-weight: 700;
}}

/* ---------- Inputs ---------- */
QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QComboBox,
QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit, QTimeEdit {{
    background-color: {c['bg2']};
    color: {c['text']};
    border: 1px solid {c['border2']};
    border-radius: 7px;
    padding: 7px 10px;
    selection-background-color: {c['accent2']};
    selection-color: #FFFFFF;
}}
QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover, QComboBox:hover,
QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover, QDateTimeEdit:hover {{
    border-color: {c['input_hover_border']};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus {{
    background-color: {c['surface_raised']};
    border-color: {c['focus']};
}}
QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled, QComboBox:disabled,
QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background-color: {c['disabled_bg']};
    color: {c['disabled_text']};
    border-color: {c['border']};
}}
QLineEdit[readOnly="true"], QPlainTextEdit[readOnly="true"], QTextEdit[readOnly="true"] {{
    color: {c['text2']};
}}
QTextEdit, QTextBrowser, QPlainTextEdit {{
    font-family: {f['mono']};
    font-size: 12px;
}}
QComboBox {{ padding-right: 28px; }}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
}}
QComboBox::down-arrow {{
    width: 6px;
    height: 6px;
    border-right: 2px solid {c['text3']};
    border-bottom: 2px solid {c['text3']};
}}
QComboBox QAbstractItemView {{
    background-color: {c['bg2']};
    color: {c['text']};
    border: 1px solid {c['border2']};
    selection-background-color: {c['nav_active_bg']};
    selection-color: {c['text']};
    outline: none;
    padding: 4px;
}}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
    width: 22px;
    background-color: {c['bg3']};
    border: none;
}}

/* ---------- Tables and list data ---------- */
QTableView, QTableWidget, QTreeView, QListView {{
    background-color: {c['bg2']};
    alternate-background-color: {c['bg1']};
    color: {c['text2']};
    gridline-color: {c['border']};
    border: 1px solid {c['border']};
    border-radius: 9px;
    selection-background-color: {c['table_sel_bg']};
    selection-color: {c['text']};
    outline: none;
}}
QTableView::item, QTableWidget::item, QTreeView::item, QListView::item {{
    padding: 7px 10px;
    border: none;
}}
QTableView::item:hover, QTableWidget::item:hover, QTreeView::item:hover,
QListView::item:hover {{ background-color: {c['table_hover_bg']}; }}
QHeaderView {{ background-color: transparent; }}
QHeaderView::section {{
    background-color: {c['bg3']};
    color: {c['text3']};
    border: none;
    border-bottom: 1px solid {c['border']};
    padding: 8px 10px;
    font-family: {f['mono']};
    font-size: 10px;
    font-weight: 700;
}}
QTableCornerButton::section {{
    background-color: {c['bg3']};
    border: none;
    border-bottom: 1px solid {c['border']};
}}

/* ---------- Dialogs, menus, tooltips ---------- */
QDialog {{
    background-color: {c['bg1']};
    border: 1px solid {c['border']};
}}
QDialogButtonBox {{ background-color: transparent; }}
QMessageBox QLabel {{ color: {c['text2']}; min-width: 240px; }}
QMenu {{
    background-color: {c['bg2']};
    color: {c['text2']};
    border: 1px solid {c['border2']};
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{ padding: 8px 26px 8px 10px; border-radius: 5px; }}
QMenu::item:selected {{ background-color: {c['menu_hover_bg']}; color: {c['text']}; }}
QMenu::item:disabled {{ color: {c['disabled_text']}; }}
QMenu::separator {{ height: 1px; background-color: {c['border']}; margin: 5px 8px; }}
QToolTip {{
    background-color: {c['surface_active']};
    color: {c['text']};
    border: 1px solid {c['border2']};
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 11px;
}}

/* ---------- Scrollbars ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px 1px;
}}
QScrollBar::handle:vertical {{
    background-color: {c['border2']};
    min-height: 32px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{ background-color: {c['text3']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 1px 2px;
}}
QScrollBar::handle:horizontal {{
    background-color: {c['border2']};
    min-width: 32px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{ background-color: {c['text3']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

/* ---------- Common controls ---------- */
QGroupBox {{
    background-color: {c['bg2']};
    color: {c['text2']};
    border: 1px solid {c['border']};
    border-radius: 10px;
    margin-top: 14px;
    padding: 16px 12px 12px 12px;
    font-weight: 700;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: {c['text3']};
    background-color: {c['bg2']};
}}
QCheckBox, QRadioButton {{ color: {c['text2']}; spacing: 8px; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    background-color: {c['bg2']};
    border: 1px solid {c['border2']};
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 8px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {c['accent']}; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {c['accent2']};
    border: 3px solid {c['accent']};
}}
QCheckBox:disabled, QRadioButton:disabled {{ color: {c['disabled_text']}; }}
QProgressBar {{
    background-color: {c['bg3']};
    color: transparent;
    border: none;
    border-radius: 3px;
    min-height: 6px;
    max-height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
        stop:0 {c['accent2']}, stop:1 {c['accent']});
    border-radius: 3px;
}}
QSplitter::handle {{ background-color: {c['border']}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}
QTabWidget::pane {{
    background-color: {c['bg1']};
    border: 1px solid {c['border']};
    border-radius: 8px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {c['text3']};
    padding: 10px 16px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 600;
}}
QTabBar::tab:hover {{ color: {c['text']}; background-color: {c['bg3']}; }}
QTabBar::tab:selected {{ color: {c['accent']}; border-bottom-color: {c['accent']}; }}

/* ---------- Reusable SOC components ---------- */
QFrame[role="pageHeader"] {{ background-color: transparent; border: none; }}
QLabel[role="statusPill"] {{
    color: {c['text3']};
    background-color: {c['bg3']};
    border: 1px solid {c['border']};
    border-radius: 9px;
    padding: 3px 9px;
    font-family: {f['mono']};
    font-size: 10px;
    font-weight: 700;
}}
QLabel[role="statusPill"][status="accent"] {{ color: {c['accent']}; background-color: {c['tint_accent_bg']}; border-color: {c['tint_accent_border']}; }}
QLabel[role="statusPill"][status="success"] {{ color: {c['success']}; background-color: {c['tint_success_bg']}; border-color: {c['tint_success_border']}; }}
QLabel[role="statusPill"][status="warning"] {{ color: {c['warning']}; background-color: {c['tint_warning_bg']}; border-color: {c['tint_warning_border']}; }}
QLabel[role="statusPill"][status="danger"] {{ color: {c['danger']}; background-color: {c['tint_danger_bg']}; border-color: {c['tint_danger_border']}; }}

QFrame[role="surfaceCard"] {{
    background-color: {c['bg2']};
    border: 1px solid {c['border']};
    border-radius: 11px;
}}
QFrame[role="surfaceCard"]:hover {{ border-color: {c['card_hover_border']}; }}
QFrame[role="cardHeader"] {{
    background-color: {c['bg3']};
    border: none;
    border-bottom: 1px solid {c['border']};
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}}
QLabel[role="cardTitle"] {{ color: {c['text']}; font-size: 13px; font-weight: 700; }}
QLabel[role="cardSubtitle"] {{ color: {c['text3']}; font-family: {f['mono']}; font-size: 10px; }}

QFrame[role="metricCard"] {{
    background-color: {c['bg2']};
    border: 1px solid {c['border']};
    border-left: 3px solid {c['accent']};
    border-radius: 10px;
}}
QFrame[role="metricCard"][tone="danger"] {{ border-left-color: {c['danger']}; }}
QFrame[role="metricCard"][tone="warning"] {{ border-left-color: {c['warning']}; }}
QFrame[role="metricCard"][tone="success"] {{ border-left-color: {c['success']}; }}
QFrame[role="metricCard"][tone="purple"] {{ border-left-color: {c['purple']}; }}
QLabel[role="metricValue"] {{ color: {c['accent']}; font-family: {f['mono']}; font-size: 27px; font-weight: 700; }}
QFrame[role="metricCard"][tone="danger"] QLabel[role="metricValue"] {{ color: {c['danger']}; }}
QFrame[role="metricCard"][tone="warning"] QLabel[role="metricValue"] {{ color: {c['warning']}; }}
QFrame[role="metricCard"][tone="success"] QLabel[role="metricValue"] {{ color: {c['success']}; }}
QFrame[role="metricCard"][tone="purple"] QLabel[role="metricValue"] {{ color: {c['purple']}; }}
QLabel[role="metricLabel"] {{ color: {c['text2']}; font-size: 11px; font-weight: 700; }}
QLabel[role="metricSubtitle"] {{ color: {c['text3']}; font-family: {f['mono']}; font-size: 10px; }}

QFrame[role="navigationRail"] {{
    background-color: {c['bg1']};
    border: none;
    border-right: 1px solid {c['border']};
}}
QToolButton[navItem="true"] {{
    min-height: 44px;
    padding: 0 13px;
    background-color: transparent;
    color: {c['text3']};
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}
QToolButton[navItem="true"]:hover {{
    background-color: {c['bg3']};
    color: {c['text']};
    border-color: {c['border']};
    border-left-color: transparent;
}}
QToolButton[navItem="true"]:checked {{
    background-color: {c['nav_active_bg']};
    color: {c['accent']};
    border-color: {c['nav_active_border']};
    border-left-color: {c['accent']};
}}
QToolButton[navItem="true"]:focus {{ border-color: {c['focus']}; }}

/* Side sub-navigation (settings sections, key groups). */
QToolButton[subNav="true"] {{
    min-height: 38px;
    padding: 0 12px;
    background-color: transparent;
    color: {c['text3']};
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    border-radius: 7px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}
QToolButton[subNav="true"]:hover {{
    background-color: {c['bg3']};
    color: {c['text']};
    border-color: {c['border']};
    border-left-color: transparent;
}}
QToolButton[subNav="true"]:checked {{
    background-color: {c['nav_active_bg']};
    color: {c['accent']};
    border-color: {c['nav_active_border']};
    border-left-color: {c['accent']};
}}
QToolButton[subNav="true"]:focus {{ border-color: {c['focus']}; }}

/* ---------- Empty states, detail strips, live feed ---------- */
QFrame[role="emptyState"] {{
    background-color: {c['bg2']};
    border: 1px dashed {c['border2']};
    border-radius: 11px;
}}
QLabel[role="emptyTitle"] {{ color: {c['text']}; font-size: 15px; font-weight: 700; }}
QLabel[role="emptyBody"] {{ color: {c['text3']}; font-size: 12px; }}

QFrame[role="detailStrip"] {{
    background-color: {c['bg3']};
    border: 1px solid {c['border']};
    border-radius: 10px;
}}
QLabel[role="detailKey"] {{ color: {c['text3']}; font-family: {f['mono']}; font-size: 10px; font-weight: 700; }}
QLabel[role="detailValue"] {{ color: {c['text']}; font-size: 12px; font-weight: 600; }}

QProgressBar[role="ratio"] {{ min-height: 8px; max-height: 8px; background-color: {c['bg3']}; }}
QFrame[role="barFill"] {{ background-color: {c['accent']}; border: none; border-radius: 2px; }}
QFrame[role="barTrack"] {{ background-color: {c['border']}; border: none; border-radius: 2px; }}

QFrame[role="feedRow"] {{
    background-color: transparent;
    border: none;
    border-bottom: 1px solid {c['border']};
}}
QLabel[role="feedText"] {{ color: {c['text2']}; font-size: 12px; }}
QLabel[role="feedTime"] {{ color: {c['text3']}; font-family: {f['mono']}; font-size: 10px; }}
"""


def apply_theme(widget: Any, overrides: Mapping[str, Any] | None = None) -> str:
    """Apply and return the generated stylesheet for an app or widget."""

    stylesheet = build_stylesheet(overrides)
    widget.setStyleSheet(stylesheet)
    return stylesheet


STYLESHEET = build_stylesheet()

__all__ = ["C", "COLORS", "FONTS", "THEME", "STYLESHEET", "apply_theme", "build_stylesheet"]
