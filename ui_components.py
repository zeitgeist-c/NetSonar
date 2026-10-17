"""Reusable Premium SOC widgets for the NetSonar desktop interface."""

from __future__ import annotations

import logging
import os
from typing import Iterable

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from config import app_path
from ui_theme import C, THEME

log = logging.getLogger("NetSonar.UI")


BUTTON_HEIGHTS = {"sm": 32, "md": 40, "lg": 48}
BUTTON_ICON_SIZES = {"sm": 14, "md": 17, "lg": 20}
BUTTON_VARIANTS = {"primary", "secondary", "ghost", "success", "danger"}


def icon_path(name: str) -> str:
    """Resolve a bundled monochrome SVG icon by its short name."""

    filename = name if name.lower().endswith(".svg") else f"{name}.svg"
    return app_path("assets", "icons", filename)


def load_icon(icon: str | QIcon | None) -> QIcon:
    """Return a QIcon from a bundled name, absolute path, or existing QIcon."""

    if isinstance(icon, QIcon):
        return icon
    if not icon:
        return QIcon()
    candidate = icon if os.path.isabs(icon) else icon_path(icon)
    return QIcon(candidate) if os.path.exists(candidate) else QIcon()


def _repolish(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class AppButton(QPushButton):
    """Consistent button with semantic variants, sizes, busy state, and CTA glow."""

    def __init__(
        self,
        text: str,
        icon: str | QIcon | None = None,
        variant: str = "secondary",
        size: str = "md",
        checkable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        if variant not in BUTTON_VARIANTS:
            raise ValueError(f"Unknown button variant: {variant}")
        if size not in BUTTON_HEIGHTS:
            raise ValueError(f"Unknown button size: {size}")

        self._label = text
        self._variant = variant
        self._size = size
        self._busy = False
        self._enabled_before_busy = True
        self._glow: QGraphicsDropShadowEffect | None = None
        self._glow_animation: QPropertyAnimation | None = None

        self.setProperty("variant", variant)
        self.setProperty("size", size)
        self.setProperty("busy", "false")
        self.setCheckable(checkable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedHeight(BUTTON_HEIGHTS[size])
        self.setIconSize(QSize(BUTTON_ICON_SIZES[size], BUTTON_ICON_SIZES[size]))
        resolved_icon = load_icon(icon)
        if not resolved_icon.isNull():
            self.setIcon(resolved_icon)

        if variant == "primary":
            self._install_glow()

    @property
    def variant(self) -> str:
        return self._variant

    @property
    def button_size(self) -> str:
        return self._size

    def _install_glow(self) -> None:
        self._glow = QGraphicsDropShadowEffect(self)
        self._glow.setBlurRadius(11.0)
        self._glow.setOffset(0, 2)
        glow_color = QColor(C["accent"])
        glow_color.setAlpha(68)
        self._glow.setColor(glow_color)
        self.setGraphicsEffect(self._glow)

        self._glow_animation = QPropertyAnimation(self._glow, b"blurRadius", self)
        self._glow_animation.setDuration(int(THEME["motion"]["fast"]))
        self._glow_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _animate_glow(self, radius: float) -> None:
        if not self._glow or not self._glow_animation or self._busy:
            return
        self._glow_animation.stop()
        self._glow_animation.setStartValue(self._glow.blurRadius())
        self._glow_animation.setEndValue(radius)
        self._glow_animation.start()

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._animate_glow(22.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt API
        self._animate_glow(11.0)
        super().leaveEvent(event)

    def set_busy(self, busy: bool) -> None:
        """Expose a stable loading state without changing button geometry."""

        busy = bool(busy)
        if busy == self._busy:
            return
        self._busy = busy
        self.setProperty("busy", "true" if busy else "false")
        if busy:
            self._enabled_before_busy = self.isEnabled()
            self.setText(f"{self._label}  ···")
            self.setEnabled(False)
        else:
            self.setText(self._label)
            self.setEnabled(self._enabled_before_busy)
        _repolish(self)

    def is_busy(self) -> bool:
        return self._busy


class StatusPill(QLabel):
    """Compact semantic status badge."""

    def __init__(self, text: str, status: str = "accent", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("role", "statusPill")
        self.setProperty("status", status)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_status(self, status: str, text: str | None = None) -> None:
        self.setProperty("status", status)
        if text is not None:
            self.setText(text)
        _repolish(self)


class PageHeader(QFrame):
    """Shared title/subtitle/eyebrow row with optional actions."""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        eyebrow: str = "NETSONAR / SOC",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "pageHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 2)
        layout.setSpacing(16)

        copy = QVBoxLayout()
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(2)
        if eyebrow:
            eyebrow_label = QLabel(eyebrow)
            eyebrow_label.setProperty("role", "eyebrow")
            copy.addWidget(eyebrow_label)
        self.title_label = QLabel(title)
        self.title_label.setProperty("role", "pageTitle")
        copy.addWidget(self.title_label)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setProperty("role", "pageSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        copy.addWidget(self.subtitle_label)
        layout.addLayout(copy, 1)

        self.actions = QHBoxLayout()
        self.actions.setContentsMargins(0, 0, 0, 0)
        self.actions.setSpacing(8)
        layout.addLayout(self.actions)

    def add_action(self, widget: QWidget) -> QWidget:
        self.actions.addWidget(widget)
        return widget


class _CardHeader(QFrame):
    def __init__(self, title: str, subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "cardHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 12, 10)
        layout.setSpacing(9)
        title_label = QLabel(title)
        title_label.setProperty("role", "cardTitle")
        layout.addWidget(title_label)
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setProperty("role", "cardSubtitle")
            layout.addWidget(subtitle_label)
        layout.addStretch()
        self.actions = layout


class SurfaceCard(QFrame):
    """Raised card compatible with the historic NeoCard API."""

    def __init__(self, title: str = "", subtitle: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "surfaceCard")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self._header: _CardHeader | None = None
        if title:
            self._header = _CardHeader(title, subtitle, self)
            outer.addWidget(self._header)
        self._body = QWidget(self)
        self._body.setObjectName("cardBody")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(14, 14, 14, 14)
        self._body_layout.setSpacing(10)
        outer.addWidget(self._body, 1)

    def body_layout(self) -> QVBoxLayout:
        return self._body_layout

    def add_header_widget(self, widget: QWidget) -> None:
        if self._header:
            self._header.actions.addWidget(widget)


class MetricCard(QFrame):
    """Compact KPI card compatible with the historic StatCard API."""

    _TONE_MAP = {"blue": "accent", "red": "danger", "amber": "warning", "green": "success"}

    def __init__(
        self,
        label: str,
        value: str = "0",
        variant: str = "blue",
        subtitle: str = "",
        icon: str | QIcon | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        tone = self._TONE_MAP.get(variant, variant)
        self.setProperty("role", "metricCard")
        self.setProperty("tone", tone)
        self.setMinimumHeight(108)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(3)
        top = QHBoxLayout()
        self._value = QLabel(str(value))
        self._value.setProperty("role", "metricValue")
        top.addWidget(self._value)
        top.addStretch()
        resolved_icon = load_icon(icon)
        if not resolved_icon.isNull():
            icon_label = QLabel()
            icon_label.setPixmap(resolved_icon.pixmap(22, 22))
            top.addWidget(icon_label)
        layout.addLayout(top)
        label_widget = QLabel(label)
        label_widget.setProperty("role", "metricLabel")
        layout.addWidget(label_widget)
        subtitle_widget = QLabel(subtitle)
        subtitle_widget.setProperty("role", "metricSubtitle")
        subtitle_widget.setVisible(bool(subtitle))
        layout.addWidget(subtitle_widget)

    def set_value(self, value) -> None:
        self._value.setText(str(value))


class NavigationRail(QFrame):
    """Scrollbar-free icon navigation with a QListWidget-like row API."""

    currentRowChanged = pyqtSignal(int)

    def __init__(
        self,
        items: Iterable[tuple[str, str, str]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "navigationRail")
        self.setFixedWidth(224)
        self._current_row = -1
        self._buttons: list[QToolButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self.setCurrentRow)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 18, 12, 14)
        self._layout.setSpacing(5)
        self._layout.addStretch(1)
        if items:
            for text, icon, tooltip in items:
                self.add_item(text, icon, tooltip)

    def add_item(self, text: str, icon: str | QIcon | None = None, tooltip: str = "") -> QToolButton:
        button = QToolButton(self)
        button.setProperty("navItem", "true")
        button.setText(text)
        button.setCheckable(True)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setIconSize(QSize(18, 18))
        resolved_icon = load_icon(icon)
        if not resolved_icon.isNull():
            button.setIcon(resolved_icon)
        button.setToolTip(tooltip)
        index = len(self._buttons)
        self._buttons.append(button)
        self._group.addButton(button, index)
        self._layout.insertWidget(self._layout.count() - 1, button)
        return button

    def count(self) -> int:
        return len(self._buttons)

    def button(self, row: int) -> QToolButton | None:
        return self._buttons[row] if 0 <= row < len(self._buttons) else None

    def currentRow(self) -> int:  # noqa: N802 - QListWidget compatibility
        return self._current_row

    def setCurrentRow(self, row: int) -> None:  # noqa: N802 - QListWidget compatibility
        if not 0 <= row < len(self._buttons):
            return
        button = self._buttons[row]
        button.setChecked(True)
        if row == self._current_row:
            return
        self._current_row = row
        self.currentRowChanged.emit(row)


class SubNav(QFrame):
    """Narrow secondary navigation used inside a page (settings sections)."""

    currentRowChanged = pyqtSignal(int)

    def __init__(
        self,
        items: Iterable[tuple[str, str, str]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "subNavRail")
        self.setFixedWidth(190)
        self._current_row = -1
        self._buttons: list[QToolButton] = []
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._group.idClicked.connect(self.setCurrentRow)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 12, 10, 12)
        self._layout.setSpacing(4)
        self._layout.addStretch(1)
        if items:
            for text, icon, tooltip in items:
                self.add_item(text, icon, tooltip)

    def add_item(self, text: str, icon: str | QIcon | None = None, tooltip: str = "") -> QToolButton:
        button = QToolButton(self)
        button.setProperty("subNav", "true")
        button.setText(text)
        button.setCheckable(True)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setIconSize(QSize(16, 16))
        resolved_icon = load_icon(icon)
        if not resolved_icon.isNull():
            button.setIcon(resolved_icon)
        button.setToolTip(tooltip)
        index = len(self._buttons)
        self._buttons.append(button)
        self._group.addButton(button, index)
        self._layout.insertWidget(self._layout.count() - 1, button)
        return button

    def count(self) -> int:
        return len(self._buttons)

    def button(self, row: int) -> QToolButton | None:
        return self._buttons[row] if 0 <= row < len(self._buttons) else None

    def currentRow(self) -> int:  # noqa: N802 - QListWidget compatibility
        return self._current_row

    def setCurrentRow(self, row: int) -> None:  # noqa: N802 - QListWidget compatibility
        if not 0 <= row < len(self._buttons):
            return
        button = self._buttons[row]
        button.setChecked(True)
        if row == self._current_row:
            return
        self._current_row = row
        self.currentRowChanged.emit(row)


class EmptyState(QFrame):
    """Guided empty state: what happened, what to do next."""

    def __init__(
        self,
        title: str,
        body: str = "",
        action_text: str = "",
        action_icon: str | QIcon | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "emptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 30, 24, 30)
        layout.setSpacing(8)
        layout.addStretch(1)

        self.title_label = QLabel(title)
        self.title_label.setProperty("role", "emptyTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.body_label = QLabel(body)
        self.body_label.setProperty("role", "emptyBody")
        self.body_label.setWordWrap(True)
        self.body_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body_label.setVisible(bool(body))
        layout.addWidget(self.body_label)

        self.action_button: AppButton | None = None
        if action_text:
            self.action_button = AppButton(
                action_text, icon=action_icon, variant="primary", size="md"
            )
            layout.addWidget(self.action_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)

    def set_message(self, title: str | None = None, body: str | None = None) -> None:
        if title is not None:
            self.title_label.setText(title)
        if body is not None:
            self.body_label.setText(body)
            self.body_label.setVisible(bool(body))


class DetailStrip(QFrame):
    """Bottom strip carrying the selected row's fields plus its actions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "detailStrip")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(14, 10, 14, 10)
        self._layout.setSpacing(20)
        self._fields: dict[str, QLabel] = {}

    def add_field(self, key: str, value: str = "—") -> QLabel:
        box = QVBoxLayout()
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(1)
        key_label = QLabel(key)
        key_label.setProperty("role", "detailKey")
        value_label = QLabel(str(value) if value not in (None, "") else "—")
        value_label.setProperty("role", "detailValue")
        value_label.setWordWrap(True)
        box.addWidget(key_label)
        box.addWidget(value_label)
        self._layout.addLayout(box)
        self._fields[key] = value_label
        return value_label

    def set_field(self, key: str, value) -> None:
        label = self._fields.get(key)
        if label is not None:
            text = str(value) if value not in (None, "") else "—"
            label.setText(text)

    def add_stretch(self) -> None:
        self._layout.addStretch(1)

    def add_action(self, widget: QWidget) -> QWidget:
        self._layout.addWidget(widget)
        return widget


class MiniBarChart(QFrame):
    """Dependency-free bar chart for hourly traffic."""

    def __init__(self, data=None, color: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data = [float(v) for v in (data or [])]
        self._color = color or C["accent"]
        self.setMinimumHeight(96)
        self.setStyleSheet("background:transparent; border:none;")

    def set_data(self, data) -> None:
        self._data = [float(v) for v in (data or [])]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        try:
            if not self._data:
                return
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            width, height = self.width(), self.height()
            if width <= 2 or height <= 4:
                return
            baseline = height - 14
            peak = max(self._data) or 1.0
            count = len(self._data)
            gap = 3
            bar_width = max(2.0, (width - gap * (count - 1)) / count)
            painter.setPen(Qt.PenStyle.NoPen)
            for index, value in enumerate(self._data):
                bar_height = max(2.0, (value / peak) * (baseline - 6))
                rect = QRectF(index * (bar_width + gap), baseline - bar_height, bar_width, bar_height)
                painter.setBrush(QColor(self._color))
                painter.drawRoundedRect(rect, 2.0, 2.0)
            painter.setBrush(QColor(C["border2"]))
            painter.drawRect(QRectF(0, baseline, width, 1))
        except Exception:  # pragma: no cover - painting must never kill the process
            log.exception("MiniBarChart.paintEvent failed")


class FeedRow(QFrame):
    """One live-feed line: tone dot, message, right-aligned timestamp."""

    _TONES = {
        "danger": C["danger"],
        "warning": C["warning"],
        "success": C["success"],
        "accent": C["accent"],
    }

    def __init__(self, text: str, time_text: str = "", tone: str = "accent", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "feedRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 7, 2, 7)
        layout.setSpacing(9)

        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(
            f"background:{self._TONES.get(tone, C['accent'])}; border-radius:4px; border:none;"
        )
        layout.addWidget(dot)

        message = QLabel(text)
        message.setProperty("role", "feedText")
        message.setWordWrap(False)
        layout.addWidget(message, 1)

        stamp = QLabel(time_text)
        stamp.setProperty("role", "feedTime")
        layout.addWidget(stamp)


class RatioBar(QWidget):
    """Label + proportion bar + value, used by 'top traffic' rows."""

    def __init__(self, label: str, ratio: float, value_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        from PyQt6.QtWidgets import QProgressBar

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        name = QLabel(label)
        name.setMinimumWidth(132)
        name.setStyleSheet(
            f"color:{C['text']}; font-family:'Cascadia Mono','Consolas',monospace; font-size:12px; border:none;"
        )
        layout.addWidget(name)

        bar = QProgressBar()
        bar.setProperty("role", "ratio")
        bar.setRange(0, 100)
        bar.setValue(max(2, min(100, int(round(ratio * 100)))))
        bar.setTextVisible(False)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(bar, 1)

        amount = QLabel(value_text)
        amount.setMinimumWidth(74)
        amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        amount.setStyleSheet(
            f"color:{C['accent']}; font-family:'Cascadia Mono','Consolas',monospace; font-size:12px; border:none;"
        )
        layout.addWidget(amount)


# Naming aliases make incremental migration from app_gui.py explicit.
NeoCard = SurfaceCard
StatCard = MetricCard


__all__ = [
    "AppButton",
    "BUTTON_HEIGHTS",
    "BUTTON_VARIANTS",
    "DetailStrip",
    "EmptyState",
    "FeedRow",
    "MetricCard",
    "MiniBarChart",
    "NavigationRail",
    "NeoCard",
    "PageHeader",
    "RatioBar",
    "StatCard",
    "StatusPill",
    "SubNav",
    "SurfaceCard",
    "icon_path",
    "load_icon",
]
