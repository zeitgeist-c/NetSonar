"""
NetSonar - PyQt6 arayÃ¼zÃ¼
AÄŸ izleme ve AI analiz paneli
"""

import sys
import os
import json
import logging
from datetime import datetime
from config import get_app_version, app_path

log = logging.getLogger("NetSonar.GUI")


from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLabel,
    QLineEdit, QComboBox, QCheckBox, QFrame, QSizePolicy,
    QTextEdit, QTextBrowser, QSystemTrayIcon, QMenu, QMessageBox, QFormLayout,
    QGroupBox, QScrollArea, QSplitter,
    QProgressBar, QDialog, QStackedWidget, QListWidget,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import (
    QIcon, QColor, QPixmap, QPainter, QAction, QBrush,
    QLinearGradient, QPainterPath, QPen,
)

# â”€â”€â”€ Renk Paleti (Cyber-Noir SOC) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
C = {
    "bg":        "#090E1A",
    "bg1":       "#0E1627",
    "bg2":       "#131E31",
    "bg3":       "#19263B",
    "border":    "#2A3B55",
    "border2":   "#3A506E",
    "accent":    "#38BDF8",
    "accent2":   "#087EA4",
    "teal":      "#00ffb8",
    "danger":    "#ff3b5c",
    "warning":   "#ffb740",
    "success":   "#00e676",
    "purple":    "#a855f7",
    "text":      "#F4F8FF",
    "text2":     "#C2CEE0",
    "text3":     "#91A4BE",
    "mono":      "JetBrains Mono",
}

APP_ICON_FILE = app_path("netsonar.ico")
APP_LOGO_FILE = app_path("assets", "netsonar.png")


def _app_icon():
    if os.path.exists(APP_ICON_FILE):
        return QIcon(APP_ICON_FILE)
    if os.path.exists(APP_LOGO_FILE):
        return QIcon(APP_LOGO_FILE)
    return QIcon()


def _app_logo_pixmap(size=30):
    src = APP_LOGO_FILE if os.path.exists(APP_LOGO_FILE) else APP_ICON_FILE
    pix = QPixmap(src) if os.path.exists(src) else QPixmap()
    if pix.isNull():
        fallback = QPixmap(size, size)
        fallback.fill(Qt.GlobalColor.transparent)
        painter = QPainter(fallback)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(C["accent2"])))
        painter.setPen(QPen(QColor(C["accent"]), 2))
        painter.drawEllipse(3, 3, size - 6, size - 6)
        painter.setPen(QPen(QColor(C["teal"]), 2))
        painter.drawLine(size // 2, 8, size // 2, size - 8)
        painter.drawLine(8, size // 2, size - 8, size // 2)
        painter.end()
        return fallback
    return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

STYLESHEET = f"""
/* â”€â”€ Temel â”€â”€ */
QMainWindow, QWidget {{
    background: {C["bg"]};
    color: {C["text"]};
    font-family: 'Segoe UI', 'Sora', sans-serif;
    font-size: 13px;
}}

/* â”€â”€ Tab â”€â”€ */
QTabWidget::pane {{
    border: 1px solid {C["border"]};
    background: {C["bg1"]};
    border-radius: 0px;
}}
QTabBar::tab {{
    background: {C["bg1"]};
    color: {C["text3"]};
    padding: 10px 18px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0;
}}
QTabBar::tab:selected {{
    color: {C["accent"]};
    border-bottom: 2px solid {C["accent"]};
    background: {C["bg2"]};
}}
QTabBar::tab:hover {{ color: {C["text2"]}; }}

/* â”€â”€ Tablo â”€â”€ */
QTableWidget {{
    background: {C["bg2"]};
    gridline-color: {C["border"]};
    border: 1px solid {C["border"]};
    border-radius: 8px;
    color: {C["text"]};
    selection-background-color: rgba(0,212,255,0.07);
    selection-color: {C["text"]};
    font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
}}
QTableWidget::item {{ padding: 5px 10px; border: none; }}
QHeaderView::section {{
    background: {C["bg3"]};
    color: {C["text3"]};
    border: none;
    border-bottom: 1px solid {C["border"]};
    padding: 7px 10px;
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}}

/* â”€â”€ Butonlar â”€â”€ */
QPushButton {{
    background: {C["accent2"]};
    color: {C["text"]};
    border: 1px solid rgba(0,212,255,0.25);
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton:hover   {{ background: #00a8d4; border-color: {C["accent"]}; }}
QPushButton:pressed {{
    background: #006e8a;
    border-color: {C["accent"]};
    padding-top: 9px;
    padding-bottom: 7px;
}}
QPushButton:disabled {{ background: {C["bg3"]}; color: {C["text3"]}; border-color: {C["border"]}; }}

QPushButton#danger {{
    background: rgba(255,59,92,0.12);
    color: {C["danger"]};
    border: 1px solid rgba(255,59,92,0.3);
}}
QPushButton#danger:hover   {{ background: rgba(255,59,92,0.22); border-color: {C["danger"]}; }}
QPushButton#danger:pressed {{ background: rgba(255,59,92,0.35); }}

QPushButton#success {{
    background: rgba(0,230,118,0.1);
    color: {C["success"]};
    border: 1px solid rgba(0,230,118,0.25);
}}
QPushButton#success:hover   {{ background: rgba(0,230,118,0.2); }}
QPushButton#success:pressed {{ background: rgba(0,230,118,0.3); }}

QPushButton#ghost {{
    background: {C["bg3"]};
    color: {C["text2"]};
    border: 1px solid {C["border2"]};
}}
QPushButton#ghost:hover   {{ border-color: {C["accent2"]}; color: {C["text"]}; }}
QPushButton#ghost:pressed {{ background: {C["border"]}; color: {C["text"]}; }}

/* â”€â”€ Input â”€â”€ */
QLineEdit, QComboBox, QSpinBox {{
    background: {C["bg3"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    border-radius: 6px;
    padding: 7px 11px;
    font-size: 12px;
    selection-background-color: {C["accent2"]};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {C["accent"]};
    background: {C["bg2"]};
}}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background: {C["bg3"]};
    color: {C["text"]};
    border: 1px solid {C["border2"]};
    selection-background-color: rgba(0,212,255,0.1);
}}

/* â”€â”€ GroupBox â”€â”€ */
QGroupBox {{
    border: 1px solid {C["border"]};
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px;
    color: {C["text2"]};
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px; top: -9px;
    padding: 0 8px;
    background: {C["bg"]};
    color: {C["text3"]};
}}

/* â”€â”€ ScrollBar â”€â”€ */
QScrollBar:vertical {{
    background: {C["bg1"]};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {C["border2"]};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {C["text3"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {C["bg1"]};
    height: 6px; border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {C["border2"]}; border-radius: 3px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* â”€â”€ TextEdit â”€â”€ */
QTextEdit, QTextBrowser {{
    background: {C["bg3"]};
    color: {C["text"]};
    border: 1px solid {C["border"]};
    border-radius: 6px;
    font-family: 'JetBrains Mono', 'Cascadia Code', monospace;
    font-size: 12px;
    padding: 6px;
}}

/* â”€â”€ CheckBox â”€â”€ */
QCheckBox {{
    color: {C["text2"]};
    spacing: 8px;
    font-size: 12px;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {C["border2"]};
    border-radius: 4px;
    background: {C["bg3"]};
}}
QCheckBox::indicator:checked {{
    background: {C["accent2"]};
    border-color: {C["accent"]};
}}
QCheckBox::indicator:hover {{ border-color: {C["accent2"]}; }}

/* â”€â”€ ProgressBar â”€â”€ */
QProgressBar {{
    background: {C["bg3"]};
    border: 1px solid {C["border"]};
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {C["accent2"]},stop:1 {C["accent"]});
    border-radius: 3px;
}}

/* â”€â”€ QDialog â”€â”€ */
QDialog {{
    background: {C["bg1"]};
}}

/* â”€â”€ SplashBar â”€â”€ */
QSplitter::handle {{
    background: {C["border"]};
    width: 1px;
}}

QLabel#title {{
    font-size: 18px;
    font-weight: 700;
    color: {C["text"]};
    letter-spacing: -0.02em;
}}
QLabel#subtitle {{
    color: {C["text3"]};
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
}}
"""


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  WORKER THREADS  (deÄŸiÅŸmedi)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class AnalysisWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    stage = pyqtSignal(str, int)
    def __init__(self, analyzer):
        super().__init__()
        self.analyzer = analyzer

    def _stage_callback(self, stage_name, progress):
        self.stage.emit(stage_name, progress)

    def run(self):
        def stage_cb(name, prog):
            self.stage.emit(name, prog)
        try:
            result = self.analyzer.analyze(hours=1, force_full=True, stage_callback=stage_cb)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class AnalysisProgressWidget(QWidget):
    stages = [
        "HazÄ±rlanÄ±yorâ€¦",
        "Ä°ÅŸleniyorâ€¦",
        "GÃ¶nderiliyorâ€¦",
        "Bekleniyorâ€¦",
        "Ä°ÅŸleniyorâ€¦",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimumWidth(150)
        self._progress_bar.setMinimumHeight(14)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {C['bg3']};
                border: none;
                border-radius: 7px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C['accent2']}, stop:1 {C['accent']});
                border-radius: 7px;
            }}
        """)

        self._percent_lbl = QLabel("0%")
        self._percent_lbl.setMinimumWidth(38)
        self._percent_lbl.setStyleSheet(
            f"color:{C['text2']}; font-size:11px; font-weight:600; "
            f"font-family:'JetBrains Mono',monospace;"
        )

        self._stage_lbl = QLabel("")
        self._stage_lbl.setStyleSheet(
            f"color:{C['accent']}; font-size:11px; font-weight:600; "
            f"font-family:'JetBrains Mono',monospace;"
        )

        lay.addWidget(self._progress_bar)
        lay.addWidget(self._percent_lbl)
        lay.addWidget(self._stage_lbl)

    @pyqtSlot(str, int)
    def set_stage(self, stage_name, progress):
        if progress <= 0:
            self.setVisible(True)
            self._progress_bar.setValue(5)
            self._percent_lbl.setText("5%")
            self._stage_lbl.setText(stage_name)
        elif progress >= 100:
            self.setVisible(False)
        else:
            self.setVisible(True)
            self._progress_bar.setValue(progress)
            self._percent_lbl.setText(f"{progress}%")
            self._stage_lbl.setText(stage_name)

    def reset(self):
        self.setVisible(False)
        self._progress_bar.setValue(0)
        self._percent_lbl.setText("0%")
        self._stage_lbl.setText("")


class StatsWorker(QThread):
    """Ana istatistikleri (stats) arka planda Ã§eker."""
    done = pyqtSignal(dict)

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        try:
            stats = self.db.get_stats()
            self.done.emit(stats)
        except Exception:
            self.done.emit({})


class DashboardWorker(QThread):
    """Dashboard iÃ§in tÃ¼m aÄŸÄ±r DB sorgularÄ±nÄ± arka planda Ã§alÄ±ÅŸtÄ±rÄ±r."""
    done = pyqtSignal(dict)

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        result = {}
        try:
            result["traffic"] = self.db.get_traffic_stats()
        except Exception:
            result["traffic"] = []
        try:
            result["top_ips"] = self.db.get_summary(hours=24, limit=7)
        except Exception:
            result["top_ips"] = []
        try:
            result["speed"]   = self.db.get_traffic_speed(minutes=5)
        except Exception:
            result["speed"] = {}
        try:
            result["procs"]   = self.db.get_top_processes(hours=1, limit=3)
        except Exception:
            result["procs"] = []
        try:
            result["protos"]  = self.db.get_protocol_distribution(hours=24)
        except Exception:
            result["protos"] = {}
        try:
            result["active"]  = self.db.get_active_connections_count(minutes=60)
        except Exception:
            result["active"] = 0
        try:
            result["timeline"] = self.db.get_traffic_timeline(hours=1, points=12)
        except Exception:
            result["timeline"] = []
        self.done.emit(result)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  YARDIMCI FONKSÄ°YONLAR
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _fmt(b):
    if b < 1_024:          return f"{b} B"
    if b < 1_024**2:       return f"{b/1_024:.1f} KB"
    if b < 1_024**3:       return f"{b/1_024**2:.1f} MB"
    return f"{b/1_024**3:.2f} GB"


def _section_title(text):
    label = QLabel(text)
    label.setStyleSheet(f"color:{C['text']}; font-size:14px; font-weight:700; border:none;")
    label.setWordWrap(True)
    return label


def _muted_label(text=""):
    label = QLabel(text)
    label.setStyleSheet(f"color:{C['text3']}; font-size:12px; border:none;")
    label.setWordWrap(True)
    return label


def _configure_table(table):
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setAlternatingRowColors(False)
    table.setWordWrap(False)
    table.verticalHeader().setDefaultSectionSize(32)
    table.horizontalHeader().setMinimumSectionSize(56)
    table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return table


def _wrap_scroll(widget):
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet(f"QScrollArea {{ border:none; background:{C['bg']}; }}")
    scroll.setWidget(widget)
    return scroll


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  UI YARDIMCI WÄ°DGET'LER
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class Separator(QFrame):
    """Ä°nce yatay Ã§izgi ayÄ±rÄ±cÄ±."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {C['border']}; border: none;")


class SectionLabel(QLabel):
    """KÃ¼Ã§Ã¼k bÃ¼yÃ¼k harfli bÃ¶lÃ¼m baÅŸlÄ±ÄŸÄ±."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"color: {C['text3']}; font-size: 11px; font-weight: 700; "
            f"letter-spacing: 0.1em; font-family: 'JetBrains Mono','Consolas',monospace; "
            f"text-transform: uppercase;"
        )


class Tag(QLabel):
    """Renkli etiket/badge."""
    def __init__(self, text, color="accent", parent=None):
        super().__init__(text, parent)
        colors = {
            "accent":  (C["accent"],  "rgba(0,212,255,0.08)",  "rgba(0,212,255,0.2)"),
            "danger":  (C["danger"],  "rgba(255,59,92,0.08)",  "rgba(255,59,92,0.25)"),
            "warning": (C["warning"], "rgba(255,183,64,0.08)", "rgba(255,183,64,0.25)"),
            "success": (C["success"], "rgba(0,230,118,0.08)",  "rgba(0,230,118,0.2)"),
            "muted":   (C["text3"],   C["bg3"],               C["border"]),
        }
        fg, bg, border = colors.get(color, colors["accent"])
        self.setStyleSheet(
            f"color:{fg}; background:{bg}; border:1px solid {border}; "
            f"border-radius:4px; padding:2px 7px; font-size:11px; font-weight:700; "
            f"font-family:'JetBrains Mono','Consolas',monospace;"
        )


class StatCard(QFrame):
    """Sol kenarlÄ±klÄ± istatistik kartÄ±."""
    COLORS = {
        "blue":  C["accent"],
        "red":   C["danger"],
        "amber": C["warning"],
        "green": C["success"],
    }

    def __init__(self, label, value="0", variant="blue", subtitle="", parent=None):
        super().__init__(parent)
        color = self.COLORS.get(variant, C["accent"])
        self.setStyleSheet(
            f"QFrame {{ background:{C['bg2']}; border:1px solid {C['border']}; "
            f"border-left:3px solid {color}; border-radius:8px; }}"
        )
        self.setMinimumHeight(96)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(3)

        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"font-size:28px; font-weight:700; color:{color}; border:none; "
            f"font-family:'JetBrains Mono','Consolas',monospace; letter-spacing:-0.02em;"
        )
        lbl = QLabel(label)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{C['text2']}; font-size:11px; font-weight:600; border:none; letter-spacing:0.04em;")
        sub = QLabel(subtitle)
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color:{C['text3']}; font-size:11px; border:none; font-family:'JetBrains Mono',monospace;")

        lay.addWidget(self._val)
        lay.addWidget(lbl)
        lay.addWidget(sub)

    def set_value(self, v):
        self._val.setText(str(v))


class MiniLineChart(QFrame):
    """Hafif Ã§izgi grafik â€” baÄŸÄ±mlÄ±lÄ±k yok."""
    def __init__(self, data=None, color=None, parent=None):
        super().__init__(parent)
        self._data  = data or []
        self._color = color or C["accent"]
        self.setMinimumHeight(36)
        self.setMinimumHeight(44)
        self.setStyleSheet("background:transparent; border:none;")

    def set_data(self, data):
        self._data = data
        self.update()

    def paintEvent(self, event):
        if not self._data or len(self._data) < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        mx = max(self._data) or 1
        mn = min(self._data)
        rng = (mx - mn) or 1

        path = QPainterPath()
        for i, v in enumerate(self._data):
            x = int(i * w / (len(self._data) - 1))
            y = h - int((v - mn) / rng * (h - 4)) - 2
            path.moveTo(x, y) if i == 0 else path.lineTo(x, y)

        pen = QPen(QColor(self._color), 1.5)
        painter.setPen(pen)
        painter.drawPath(path)

        # fill
        fill = QPainterPath(path)
        fill.lineTo(w, h)
        fill.lineTo(0, h)
        fill.closeSubpath()
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(self._color + "50"))
        grad.setColorAt(1, QColor(self._color + "00"))
        painter.fillPath(fill, QBrush(grad))


class CardHeader(QFrame):
    """BaÅŸlÄ±k + saÄŸ aksiyonlarÄ± olan kart baÅŸlÄ±ÄŸÄ±."""
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background:{C['bg3']}; border:none; "
            f"border-bottom:1px solid {C['border']}; border-radius:0; }}"
        )
        self.setMinimumHeight(44)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 12, 0)

        self._title = QLabel(title)
        self._title.setWordWrap(True)
        self._title.setStyleSheet(f"color:{C['text']}; font-size:13px; font-weight:600; border:none;")
        lay.addWidget(self._title)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"color:{C['text3']}; font-size:11px; font-family:'JetBrains Mono',monospace; border:none; margin-left:8px;")
            lay.addWidget(sub)

        lay.addStretch()
        self._right = lay  # butonlar eklenebilir

    def add_widget(self, w):
        self._right.addWidget(w)


class NeoCard(QFrame):
    """KenarlÄ±klÄ±, baÅŸlÄ±klÄ± kart container."""
    def __init__(self, title="", subtitle="", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame#neocard {{ background:{C['bg2']}; border:1px solid {C['border']}; "
            f"border-radius:8px; }}"
        )
        self.setObjectName("neocard")
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)

        if title:
            self._hdr = CardHeader(title, subtitle, self)
            self._outer.addWidget(self._hdr)

        self._body = QWidget()
        self._body.setStyleSheet("background:transparent; border:none;")
        self._body_lay = QVBoxLayout(self._body)
        self._body_lay.setContentsMargins(0, 0, 0, 0)
        self._outer.addWidget(self._body)

    def body_layout(self):
        return self._body_lay

    def add_header_widget(self, w):
        if hasattr(self, "_hdr"):
            self._hdr.add_widget(w)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  DASHBOARD SEKMESÄ°
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class DashboardTab(QWidget):
    request_block = pyqtSignal(str)

    def __init__(self, db):
        super().__init__()
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        self.card_conns = StatCard("BugÃ¼nkÃ¼ BaÄŸlantÄ±", "0", "blue", "canlÄ± izleme")
        self.card_threats = StatCard("Tehdit", "0", "red", "toplam")
        self.card_blocked = StatCard("Engellenen", "0", "amber", "IP adresi")
        self.card_reports = StatCard("AI Raporu", "0", "green", "kayÄ±tlÄ±")
        for card in (self.card_conns, self.card_threats, self.card_blocked, self.card_reports):
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cards_row.addWidget(card)
        root.addLayout(cards_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self._traffic_card = NeoCard("Veri Transferi", "son 1 saat")
        traffic_body = self._traffic_card.body_layout()
        traffic_body.setContentsMargins(14, 12, 14, 12)
        traffic_body.setSpacing(12)

        speed_row = QHBoxLayout()
        self._speed_lbl = QLabel("0.0 KB/s")
        self._speed_lbl.setStyleSheet(f"color:{C['accent']}; font-family:'JetBrains Mono',monospace; font-size:18px; font-weight:700; border:none;")
        self._cmp_lbl = _muted_label("AnlÄ±k trafik hÄ±zÄ±")
        speed_row.addWidget(self._speed_lbl)
        speed_row.addWidget(self._cmp_lbl)
        speed_row.addStretch()
        traffic_body.addLayout(speed_row)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(10)
        for title, color in (("GÃ¶nderim", C["success"]), ("Ä°ndirim", C["accent"])):
            chart_box = QFrame()
            chart_box.setStyleSheet(f"QFrame {{ background:{C['bg3']}; border:1px solid {C['border']}; border-radius:6px; }}")
            chart_layout = QVBoxLayout(chart_box)
            chart_layout.setContentsMargins(10, 8, 10, 8)
            chart_layout.setSpacing(6)
            chart_layout.addWidget(_section_title(title))
            chart = MiniLineChart(color=color)
            chart.setMinimumHeight(72)
            chart_layout.addWidget(chart)
            chart_row.addWidget(chart_box, 1)
            if title == "GÃ¶nderim":
                self._upload_chart = chart
            else:
                self._download_chart = chart
        traffic_body.addLayout(chart_row)

        self._traffic_table = QTableWidget()
        self._traffic_table.setColumnCount(4)
        self._traffic_table.setHorizontalHeaderLabels(["DÃ¶nem", "GÃ¶nderim", "Ä°ndirim", "Toplam"])
        _configure_table(self._traffic_table)
        self._traffic_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._traffic_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._traffic_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._traffic_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._traffic_table.setMinimumHeight(190)
        traffic_body.addWidget(self._traffic_table, 1)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)
        for attr, label, color in (
            ("_proc_lbl", "SÃ¼reÃ§ler", C["text2"]),
            ("_proto_lbl", "Protokol", C["accent"]),
            ("_active_lbl", "Aktif IP", C["teal"]),
        ):
            box = QFrame()
            box.setStyleSheet(f"QFrame {{ background:{C['bg3']}; border:1px solid {C['border']}; border-radius:6px; }}")
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(10, 8, 10, 8)
            box_layout.setSpacing(4)
            box_layout.addWidget(_muted_label(label))
            value = QLabel("-")
            value.setWordWrap(True)
            value.setStyleSheet(f"color:{color}; font-size:12px; font-family:'JetBrains Mono',monospace; border:none;")
            box_layout.addWidget(value)
            meta_row.addWidget(box, 1)
            setattr(self, attr, value)
        traffic_body.addLayout(meta_row)

        splitter.addWidget(self._traffic_card)

        self._topip_card = NeoCard("En YÃ¼ksek Trafik", "son 24 saat")
        top_body = self._topip_card.body_layout()
        top_body.setContentsMargins(0, 0, 0, 0)
        self._topip_table = QTableWidget()
        self._topip_table.setColumnCount(3)
        self._topip_table.setHorizontalHeaderLabels(["IP", "Veri", "BaÄŸlantÄ±"])
        _configure_table(self._topip_table)
        self._topip_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._topip_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._topip_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        top_body.addWidget(self._topip_table)
        splitter.addWidget(self._topip_card)
        splitter.setSizes([760, 420])
        root.addWidget(splitter, 1)

        outer.addWidget(_wrap_scroll(content), 1)

    def refresh(self):
        """TÃ¼m DB sorgularÄ±nÄ± arka planda Ã§alÄ±ÅŸtÄ±rÄ±r â€” UI bloklanmaz."""
        if hasattr(self, "_dash_worker") and self._dash_worker.isRunning():
            return
        self._dash_worker = DashboardWorker(self.db)
        self._dash_worker.done.connect(self._on_data_ready)
        self._dash_worker.start()

    def _on_data_ready(self, data):
        """Worker tamamlandÄ±ÄŸÄ±nda UI thread'de tÃ¼m alanlarÄ± gÃ¼ncelle."""
        traffic  = data.get("traffic", [])
        top_ips  = data.get("top_ips", [])
        speed    = data.get("speed", {})
        procs    = data.get("procs", [])
        protos   = data.get("protos", {})
        active   = data.get("active", 0)
        timeline = data.get("timeline", [])

        labels = ["Saat", "GÃ¼n", "Hafta", "Ay", "YÄ±l"]
        self._traffic_table.setUpdatesEnabled(False)
        self._traffic_table.setRowCount(0)
        for i, p in enumerate(traffic[:len(labels)]):
            row = self._traffic_table.rowCount()
            self._traffic_table.insertRow(row)
            values = [
                labels[i],
                _fmt(p.get("upload", 0)),
                _fmt(p.get("download", 0)),
                f"{_fmt(p.get('total', 0))} ({p.get('conn_count', 0):,} baÄŸlantÄ±)",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setToolTip(str(val))
                item.setForeground(QColor(C["text"] if col == 0 else C["text2"]))
                self._traffic_table.setItem(row, col, item)
        self._traffic_table.setUpdatesEnabled(True)

        if speed:
            self._speed_lbl.setText(f"{speed.get('total_kbs', 0):.1f} KB/s")
        if procs:
            self._proc_lbl.setText(" Â· ".join(p["process"][:12] for p in procs))
        if protos:
            self._proto_lbl.setText("  ".join(f"{k}:{v['percentage']:.0f}%" for k, v in protos.items()))
        self._active_lbl.setText(str(active))
        if timeline:
            self._upload_chart.set_data([max(t["bytes"] * .4, 100) for t in timeline])
            self._download_chart.set_data([max(t["bytes"] * .6, 100) for t in timeline])

        self._topip_table.setUpdatesEnabled(False)
        self._topip_table.setRowCount(0)
        for row in top_ips:
            r = self._topip_table.rowCount()
            self._topip_table.insertRow(r)
            ip_item = QTableWidgetItem(row.get("dst_ip", ""))
            ip_item.setForeground(QColor(C["text"]))
            mb_item = QTableWidgetItem(_fmt(row.get("total_bytes", 0)))
            mb_item.setForeground(QColor(C["accent"]))
            cn_item = QTableWidgetItem(str(row.get("conn_count", 0)))
            cn_item.setForeground(QColor(C["text3"]))
            for col, item in enumerate([ip_item, mb_item, cn_item]):
                self._topip_table.setItem(r, col, item)
        self._topip_table.setUpdatesEnabled(True)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  AI ANALÄ°Z SEKMESÄ°
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def _show_trusted_ip_dialog(parent, db, initial_ip=""):
    dialog = QDialog(parent)
    dialog.setWindowTitle("GÃ¼venli IP Ekle")
    dialog.setMinimumWidth(440)
    layout = QVBoxLayout(dialog)
    form = QFormLayout()
    ip_input = QLineEdit(str(initial_ip or ""))
    ip_input.setPlaceholderText("Ã–rnek: 8.8.8.8 veya 2001:4860:4860::8888")
    note_input = QLineEdit()
    note_input.setPlaceholderText("Neden gÃ¼venli? (isteÄŸe baÄŸlÄ±)")
    form.addRow("IP adresi:", ip_input)
    form.addRow("AÃ§Ä±klama:", note_input)
    layout.addLayout(form)
    info = QLabel("Bu IP baÄŸlantÄ± geÃ§miÅŸinde gÃ¶rÃ¼nmeye devam eder; yalnÄ±zca sonraki AI analizlerinden ve otomatik engellemeden Ã§Ä±karÄ±lÄ±r.")
    info.setWordWrap(True)
    info.setStyleSheet(f"color:{C['text3']}; font-size:11px;")
    layout.addWidget(info)
    buttons = QHBoxLayout()
    buttons.addStretch()
    cancel = QPushButton("Ä°ptal")
    cancel.setObjectName("ghost")
    save = QPushButton("GÃ¼venli Listeye Ekle")
    save.setObjectName("primary")
    cancel.clicked.connect(dialog.reject)
    buttons.addWidget(cancel)
    buttons.addWidget(save)
    layout.addLayout(buttons)

    def submit():
        try:
            entry = db.add_trusted_ip(ip_input.text(), note_input.text())
        except ValueError as exc:
            QMessageBox.warning(dialog, "IP Eklenemedi", str(exc))
            ip_input.setFocus()
            return
        dialog.setProperty("trusted_entry", entry)
        dialog.accept()

    save.clicked.connect(submit)
    ip_input.returnPressed.connect(submit)
    return dialog.exec() == QDialog.DialogCode.Accepted


class AnalysisTabWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        reports = self.db.get_all_reports()
        self.done.emit(reports)


class TrustedTabWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        self.done.emit(self.db.get_trusted_ips())


class BlockedTabWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        blocked = self.db.get_blocked_ips()
        self.done.emit(blocked)


class AnalysisTab(QWidget):
    def __init__(self, db, analyzer):
        super().__init__()
        self.db = db
        self.analyzer = analyzer
        self._worker  = None
        self._history_worker = None
        self._current_report = None
        self._loading = False
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(20, 16, 20, 24)
        lay.setSpacing(14)

        risk_frame = QFrame()
        risk_frame.setObjectName("analysisRisk")
        risk_frame.setStyleSheet(
            f"QFrame#analysisRisk {{ background:{C['bg2']}; border:1px solid {C['border2']}; border-radius:10px; }}"
        )
        risk_lay = QGridLayout(risk_frame)
        risk_lay.setContentsMargins(18, 14, 18, 14)
        risk_lay.setHorizontalSpacing(18)
        risk_lay.setVerticalSpacing(5)

        self._risk_score = QLabel("-")
        self._risk_score.setMinimumSize(112, 72)
        self._risk_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._risk_score.setStyleSheet(
            f"font-size:38px; font-weight:700; color:{C['text3']}; font-family:'JetBrains Mono',monospace; border:none;"
        )
        risk_lay.addWidget(self._risk_score, 0, 0, 3, 1)

        self._risk_status = QLabel("HenÃ¼z analiz yapÄ±lmadÄ±")
        self._risk_status.setWordWrap(True)
        self._risk_status.setStyleSheet(f"font-size:17px; font-weight:700; color:{C['text3']}; border:none;")
        risk_lay.addWidget(self._risk_status, 0, 1)

        self._risk_level = QLabel("Durum: Bekleniyor")
        self._risk_level.setWordWrap(True)
        self._risk_level.setStyleSheet(f"font-size:13px; font-weight:700; color:{C['text2']}; border:none;")
        risk_lay.addWidget(self._risk_level, 1, 1)

        self._risk_time = _muted_label("Analiz geÃ§miÅŸi yÃ¼kleniyorâ€¦")
        risk_lay.addWidget(self._risk_time, 2, 1)

        self._provider_lbl = QLabel("AI saÄŸlayÄ±cÄ±sÄ±: -")
        self._provider_lbl.setWordWrap(True)
        self._provider_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._provider_lbl.setStyleSheet(
            f"color:{C['accent']}; font-size:12px; font-weight:700; font-family:'JetBrains Mono',monospace; border:none;"
        )
        risk_lay.addWidget(self._provider_lbl, 0, 2, 3, 1)
        risk_lay.setColumnStretch(1, 1)
        lay.addWidget(risk_frame)

        report_card = NeoCard("Analiz Sonucu", "risklerin sade ve uygulanabilir Ã¶zeti")
        report_card.body_layout().setContentsMargins(0, 0, 0, 0)
        self._report_browser = QTextBrowser()
        self._report_browser.setOpenExternalLinks(False)
        self._report_browser.setMinimumHeight(280)
        self._report_browser.setStyleSheet(
            f"QTextBrowser {{ background:{C['bg2']}; border:1px solid {C['border']}; border-radius:8px; color:{C['text']}; font-size:13px; padding:4px; }}"
        )
        self._set_report_empty_state("HenÃ¼z gÃ¶rÃ¼ntÃ¼lenecek bir analiz sonucu yok.")
        report_card.body_layout().addWidget(self._report_browser)
        lay.addWidget(report_card)

        susp_card = NeoCard("ÅÃ¼pheli BaÄŸlantÄ±lar", "neden ve Ã¶nerilen iÅŸlem ayrÄ± gÃ¶sterilir")
        susp_body = susp_card.body_layout()
        susp_body.setContentsMargins(0, 0, 0, 0)
        self._susp_table = QTableWidget()
        self._susp_table.setColumnCount(6)
        self._susp_table.setHorizontalHeaderLabels(["IP / Port", "SÃ¼reÃ§", "Risk nedeni", "Ã–nerilen iÅŸlem", "Durum", "Ä°ÅŸlem"])
        _configure_table(self._susp_table)
        header = self._susp_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._susp_table.setMinimumHeight(190)
        self._susp_table.setTextElideMode(Qt.TextElideMode.ElideRight)
        susp_body.addWidget(self._susp_table)
        lay.addWidget(susp_card)

        self._technical_btn = QPushButton("Teknik ayrÄ±ntÄ±yÄ± gÃ¶ster")
        self._technical_btn.setObjectName("ghost")
        self._technical_btn.setCheckable(True)
        self._technical_btn.setMinimumHeight(38)
        self._technical_btn.toggled.connect(self._toggle_technical_details)
        lay.addWidget(self._technical_btn, 0, Qt.AlignmentFlag.AlignLeft)

        self._technical_card = NeoCard("AI'ye GÃ¶nderilen Teknik Veri", "yalnÄ±zca inceleme ve hata ayÄ±klama iÃ§in")
        tech_body = self._technical_card.body_layout()
        tech_body.setContentsMargins(0, 0, 0, 0)
        self._preview_browser = QTextBrowser()
        self._preview_browser.setMinimumHeight(170)
        self._preview_browser.setStyleSheet(
            f"QTextBrowser {{ background:#080D17; color:{C['text2']}; border:1px solid {C['border']}; border-radius:8px; font-family:'JetBrains Mono',monospace; font-size:12px; }}"
        )
        tech_body.addWidget(self._preview_browser)
        self._technical_card.setVisible(False)
        lay.addWidget(self._technical_card)

        hist_card = NeoCard("Rapor GeÃ§miÅŸi", "bir satÄ±ra tÄ±klayarak raporu yeniden gÃ¶rÃ¼ntÃ¼leyin")
        hist_body = hist_card.body_layout()
        hist_body.setContentsMargins(0, 0, 0, 0)
        self._hist_table = QTableWidget()
        self._hist_table.setColumnCount(4)
        self._hist_table.setHorizontalHeaderLabels(["Tarih", "SaÄŸlayÄ±cÄ±", "Risk", "Durum"])
        _configure_table(self._hist_table)
        self._hist_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._hist_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._hist_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._hist_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._hist_table.setMinimumHeight(170)
        self._hist_table.cellClicked.connect(self._show_history_report)
        hist_body.addWidget(self._hist_table)
        lay.addWidget(hist_card)
        root.addWidget(_wrap_scroll(content), 1)

    def _set_report_empty_state(self, message):
        self._report_browser.setHtml(
            f"<div style='color:{C['text2']};font-size:13px;padding:28px;text-align:center;'>"
            f"<b style='color:{C['text']};'>Analiz bilgisi</b><br><br>{message}</div>"
        )

    def _toggle_technical_details(self, visible):
        self._technical_card.setVisible(visible)
        self._technical_btn.setText(
            "Teknik ayrÄ±ntÄ±yÄ± gizle" if visible else "Teknik ayrÄ±ntÄ±yÄ± gÃ¶ster"
        )

    def _export(self, fmt):
        from exporter import export_report
        if not self._current_report:
            QMessageBox.warning(self, "UyarÄ±", "DÄ±ÅŸa aktarÄ±lacak rapor yok.")
            return
        try:
            fp = export_report(self._current_report, fmt)
            QMessageBox.information(self, "BaÅŸarÄ±lÄ±", f"Rapor kaydedildi:\n{fp}")
        except Exception as exc:
            QMessageBox.critical(self, "Hata", f"DÄ±ÅŸa aktarma hatasÄ±:\n{exc}")

    def _display_report(self, r, provider=None):
        from html import escape
        self._current_report = r
        score = r.get("risk_score", 0)
        status = str(r.get("status", "") or "Bilinmiyor")
        if provider is None:
            import config
            provider = config.AI_PROVIDER.upper()
        else:
            provider = str(provider).upper()

        if not isinstance(score, (int, float)) or score < 0:
            color, score_txt, level, icon = C["danger"], "Hata", "Analiz hatasÄ±", "âœ•"
        elif score < 3:
            color, score_txt, level, icon = C["success"], f"{score:.1f}", "DÃ¼ÅŸÃ¼k risk", "âœ“"
        elif score < 6:
            color, score_txt, level, icon = C["warning"], f"{score:.1f}", "Orta risk", "!"
        elif score < 8:
            color, score_txt, level, icon = C["danger"], f"{score:.1f}", "YÃ¼ksek risk", "âš "
        else:
            color, score_txt, level, icon = "#ff1744", f"{score:.1f}", "Kritik risk", "âš "

        self._risk_score.setText(score_txt)
        self._risk_score.setStyleSheet(f"font-size:38px;font-weight:700;color:{color};font-family:'JetBrains Mono',monospace;border:none;")
        self._risk_status.setText(status)
        self._risk_status.setStyleSheet(f"font-size:17px;font-weight:700;color:{color};border:none;")
        self._risk_level.setText(f"{icon}  {level}")
        self._risk_level.setStyleSheet(f"font-size:13px;font-weight:700;color:{color};border:none;")
        analysis_time = r.get("created_at") or (r.get("_meta", {}) or {}).get("created_at")
        if analysis_time:
            try:
                parsed_time = datetime.fromisoformat(str(analysis_time).replace("Z", "+00:00"))
                analysis_time_text = parsed_time.strftime("%d.%m.%Y %H:%M")
            except (TypeError, ValueError):
                analysis_time_text = str(analysis_time)[:19].replace("T", " ")
        else:
            analysis_time_text = datetime.now().strftime("%d.%m.%Y %H:%M")
        self._risk_time.setText(f"Son analiz: {analysis_time_text}")
        self._provider_lbl.setText(f"AI saÄŸlayÄ±cÄ±sÄ±: {provider}")

        meta = r.get("_meta", {}) or {}
        preview = f"[AtlandÄ±] {meta.get('reason','')}" if meta.get("skipped") else str(meta.get("raw_payload", ""))
        self._preview_browser.setPlainText(preview or "Teknik veri kaydedilmemiÅŸ.")
        if meta.get("est_tokens"):
            self._provider_lbl.setText(f"AI saÄŸlayÄ±cÄ±sÄ±: {provider}\nYaklaÅŸÄ±k {meta['est_tokens']} token")

        conns = [c for c in (r.get("suspicious_connections", []) or []) if isinstance(c, dict)]
        summary = str(r.get("summary", "") or "Analiz sonucu iÃ§in aÃ§Ä±klama bulunmuyor.")
        summary_lines = [x.strip() for x in summary.splitlines() if x.strip()] or [summary]
        reasons, actions = [], []
        for conn in conns:
            for value, target in ((str(conn.get("reason","")).strip(), reasons),(str(conn.get("action","")).strip(), actions)):
                if value and value not in target: target.append(value)

        def paras(items):
            return "".join(f"<p style='margin:0 0 8px;line-height:1.55;color:{C['text2']};'>{escape(x)}</p>" for x in items)
        def bullets(items, empty, dot):
            if not items: return f"<p style='margin:0;color:{C['text3']};'>{escape(empty)}</p>"
            return "<ul style='margin:0;padding-left:20px;'>"+"".join(f"<li style='margin-bottom:8px;color:{dot};'><span style='color:{C['text2']};'>{escape(x)}</span></li>" for x in items)+"</ul>"
        conn_html = "".join(
            f"<div style='margin-bottom:8px;padding:10px 12px;background:{C['bg2']};border:1px solid {C['border']};border-radius:7px;'>"
            f"<b style='color:{C['warning']};'>{escape(str(c.get('ip','')))}:{escape(str(c.get('port','')))}</b>"
            f"<span style='color:{C['text3']};'> &nbsp; {escape(str(c.get('process','') or 'Bilinmeyen sÃ¼reÃ§'))}</span></div>" for c in conns
        ) or f"<p style='color:{C['success']};'>âœ“ ÅÃ¼pheli baÄŸlantÄ± tespit edilmedi.</p>"
        card=f"background:{C['bg3']};border:1px solid {C['border']};border-radius:8px;padding:14px 16px;margin-bottom:12px;"
        html = f'''<html><body style="background:{C['bg2']};color:{C['text']};font-family:'Segoe UI';font-size:13px;padding:12px;">
        <div style="{card}border-left:4px solid {color};"><b style="color:{C['accent']};">KISA SONUÃ‡</b><div style="margin-top:10px;">{paras(summary_lines)}</div></div>
        <div style="{card}"><b style="color:{C['warning']};">TESPÄ°T EDÄ°LEN RÄ°SKLER</b><div style="margin-top:10px;">{bullets(reasons,'Belirgin bir risk nedeni bildirilmedi.',C['warning'])}</div></div>
        <div style="{card}"><b style="color:{C['accent']};">Ã–NERÄ°LEN Ä°ÅLEMLER</b><div style="margin-top:10px;">{bullets(actions,'Ek bir iÅŸlem Ã¶nerilmedi.',C['accent'])}</div></div>
        <div style="{card}"><b>ÅÃœPHELÄ° BAÄLANTILAR ({len(conns)})</b><div style="margin-top:10px;">{conn_html}</div></div>
        </body></html>'''
        self._report_browser.setHtml(html)

        self._susp_table.clearSpans()
        self._susp_table.setRowCount(0)
        if not conns:
            self._susp_table.setRowCount(1); self._susp_table.setSpan(0,0,1,6)
            item=QTableWidgetItem("ÅÃ¼pheli baÄŸlantÄ± tespit edilmedi."); item.setForeground(QColor(C["success"]))
            self._susp_table.setItem(0,0,item)
        for conn in conns:
            row=self._susp_table.rowCount(); self._susp_table.insertRow(row)
            vals=[f"{conn.get('ip','')}:{conn.get('port','')}",conn.get("process",""),conn.get("reason",""),conn.get("action",""),level]
            for col,val in enumerate(vals):
                item=QTableWidgetItem(str(val)); item.setToolTip(str(val))
                item.setForeground(QColor(color if col==4 else C["text2"])); self._susp_table.setItem(row,col,item)
            ip = str(conn.get("ip", "") or "").strip()
            trust_btn = QPushButton("GÃ¼venli")
            trust_btn.setObjectName("ghost")
            trust_btn.setMinimumSize(76, 30)
            trust_btn.setEnabled(bool(ip) and not self.db.is_trusted_ip(ip))
            trust_btn.setText("GÃ¼venli âœ“" if self.db.is_trusted_ip(ip) else "GÃ¼venli")
            trust_btn.clicked.connect(lambda _, target=ip: self._mark_trusted(target))
            self._susp_table.setCellWidget(row, 5, trust_btn)

    def _mark_trusted(self, ip):
        if not ip:
            QMessageBox.warning(self, "IP BulunamadÄ±", "Bu risk satÄ±rÄ±nda geÃ§erli bir IP adresi yok.")
            return
        if _show_trusted_ip_dialog(self, self.db, ip):
            QMessageBox.information(self, "GÃ¼venli IP", f"{ip} sonraki AI analizlerinin dÄ±ÅŸÄ±nda bÄ±rakÄ±lacak.")
            self._display_report(self._current_report or {})

    def _load_history(self):
        if self._loading:
            return
        self._loading = True
        self._history_worker = AnalysisTabWorker(self.db)
        self._history_worker.done.connect(self._on_history_loaded)
        self._history_worker.start()

    def _on_history_loaded(self, reports):
        self._loading = False
        self._history_reports = list(reports or [])
        self._hist_table.setRowCount(0)
        for rep in reports:
            r = self._hist_table.rowCount()
            self._hist_table.insertRow(r)
            score = rep.get("risk_score", 0)
            color = C["success"] if score < 4 else C["warning"] if score < 7 else C["danger"]
            for col, val in enumerate([
                rep.get("created_at","")[:19].replace("T"," "),
                rep.get("provider","").upper(),
                f"{score:.1f}",
                rep.get("status",""),
            ]):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(color if col == 2 else C["text2"]))
                self._hist_table.setItem(r, col, item)

        if reports:
            latest = reports[0]
            try:
                import json
                content = latest.get("content", "{}")
                if isinstance(content, str):
                    parsed_content = json.loads(content)
                else:
                    parsed_content = content
                parsed_content["_meta"] = {"skipped": False, "raw_payload": content if isinstance(content, str) else str(content)}
                parsed_content["provider_used"] = latest.get("provider", "")
                parsed_content["created_at"] = latest.get("created_at", "")
                self._current_report = parsed_content
                self._display_report(parsed_content, provider=latest.get("provider", ""))
            except Exception as e:
                log.error("Rapor gösterilemedi: %s", e)

    def _show_history_report(self, row, _column):
        if row < 0 or row >= len(getattr(self, "_history_reports", [])):
            return
        report = self._history_reports[row]
        try:
            content = report.get("content", "{}")
            parsed = json.loads(content) if isinstance(content, str) else dict(content or {})
            parsed["_meta"] = {
                "skipped": False,
                "raw_payload": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, indent=2),
            }
            parsed["created_at"] = report.get("created_at", "")
            self._display_report(parsed, provider=report.get("provider", ""))
            self._hist_table.selectRow(row)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._set_report_empty_state(f"SeÃ§ilen rapor okunamadÄ±: {exc}")

    def refresh(self):
        self._load_history()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  AYARLAR SEKMESÄ°
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# (SettingsTab class continues below after MainWindow)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  ANA PENCERE
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class MainWindow(QMainWindow):
    def __init__(self, db, analyzer, engine, scheduler):
        super().__init__()
        self.db        = db
        self.analyzer  = analyzer
        self.engine    = engine
        self.scheduler = scheduler
        self.setWindowTitle(f"NetSonar {get_app_version()} â€” AI AÄŸ Ä°zleyici")
        self.setMinimumSize(1280, 760)
        self.resize(1280, 800)
        self.setStyleSheet(STYLESHEET)
        self._setup_ui()
        self._setup_tray()
        self._setup_timer()

    # â”€â”€ UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())
        root.addWidget(self._build_tabs(), 1)
        root.addWidget(self._build_statusbar())

    # â”€â”€ Topbar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _build_topbar(self):
        bar = QFrame()
        bar.setStyleSheet(
            f"QFrame {{ background:{C['bg1']}; border:none; "
            f"border-bottom:1px solid {C['border']}; }}"
        )
        bar.setMinimumHeight(58)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 16, 0)
        lay.setSpacing(12)

        logo_pix = QLabel()
        logo_pix.setPixmap(_app_logo_pixmap(32))
        logo_pix.setFixedSize(36, 36)
        logo_pix.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_pix.setStyleSheet("border:none; background:transparent;")
        lay.addWidget(logo_pix)

        title_box = QVBoxLayout()
        title_box.setContentsMargins(0, 0, 0, 0)
        title_box.setSpacing(0)
        logo = QLabel(f"NetSonar {get_app_version()}")
        logo.setStyleSheet(
            f"font-size:17px; font-weight:700; color:{C['text']}; "
            f"font-family:'JetBrains Mono','Consolas',monospace; letter-spacing:0.03em; border:none;"
        )
        subtitle = QLabel("AÄŸ korumasÄ± ve AI analiz")
        subtitle.setStyleSheet(f"color:{C['text3']}; font-size:11px; border:none;")
        title_box.addWidget(logo)
        title_box.addWidget(subtitle)
        lay.addLayout(title_box)

        self._analysis_progress = AnalysisProgressWidget()
        lay.addWidget(self._analysis_progress)
        lay.addStretch()

        for obj, label, slot in [
            ("primary", "Analizi BaÅŸlat", self._run_quick_analysis),
        ]:
            btn = QPushButton(label)
            btn.setMinimumHeight(36)
            btn.setObjectName(obj)
            if obj == "primary":
                btn.setStyleSheet(
                    f"QPushButton {{ background:linear-gradient(135deg,{C['accent2']},{C['bg3']}); "
                    f"color:{C['text']}; border:1px solid rgba(0,212,255,0.3); border-radius:6px; "
                    f"padding:0 14px; font-weight:700; font-size:12px; }}"
                    f"QPushButton:hover {{ border-color:{C['accent']}; }}"
                )
                self._quick_btn = btn
            btn.clicked.connect(slot)
            lay.addWidget(btn)

        return bar

    # â”€â”€ Sekmeler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _build_tabs(self):
        shell = QFrame()
        layout = QHBoxLayout(shell); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        self._navigation = QListWidget(); self._navigation.setFixedWidth(220); self._navigation.setSpacing(4)
        self._navigation.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._navigation.setStyleSheet(f"""
            QListWidget {{ background:{C['bg1']}; border:none; border-right:1px solid {C['border']}; padding:18px 10px; outline:none; }}
            QListWidget::item {{ color:{C['text2']}; border-radius:8px; padding:13px 14px; margin:2px 0; font-size:13px; font-weight:600; }}
            QListWidget::item:hover {{ background:{C['bg3']}; color:{C['text']}; }}
            QListWidget::item:selected {{ background:{C['accent2']}; color:#FFFFFF; border-left:3px solid {C['accent']}; }}
        """)
        for title,tip in [("Panel","Dashboard"),("AI Analiz","AI reports"),("BaÄŸlantÄ±lar","Connections"),("Engellenenler","Blocked IPs"),("GÃ¼venli IP'ler","Trusted IPs"),("Ayarlar","Settings")]:
            item=QListWidgetItem(title); item.setToolTip(tip); item.setSizeHint(QSize(194,48)); self._navigation.addItem(item)
        self._tabs=QStackedWidget()
        self._dashboard_tab=DashboardTab(self.db); self._dashboard_tab.request_block.connect(self._block_ip)
        self._analysis_tab=self._data_tab=self._blocked_tab=self._trusted_tab=self._settings_tab=None
        def _placeholder():
            w=QWidget(); lay=QVBoxLayout(w); lbl=QLabel("YÃ¼kleniyorâ€¦"); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{C['text2']}; font-size:13px;"); lay.addWidget(lbl); return w
        self._tabs.addWidget(self._dashboard_tab)
        for _ in range(5): self._tabs.addWidget(_placeholder())
        self._navigation.currentRowChanged.connect(self._tabs.setCurrentIndex)
        self._tabs.currentChanged.connect(self._on_tab_changed); self._navigation.setCurrentRow(0)
        layout.addWidget(self._navigation); layout.addWidget(self._tabs,1); return shell

    def _build_statusbar(self):
        bar = QFrame()
        bar.setStyleSheet(
            f"QFrame {{ background:{C['bg1']}; border:none; border-top:1px solid {C['border']}; }}"
        )
        bar.setMinimumHeight(30)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(14)

        def sb_item(text, color=None):
            lbl = QLabel(text)
            lbl.setWordWrap(False)
            col = color or C["text2"]
            lbl.setStyleSheet(f"color:{col}; font-size:11px; font-family:'JetBrains Mono',monospace; border:none;")
            return lbl

        self._status_label = sb_item("Ä°zleme aktif", C["success"])
        lay.addWidget(self._status_label)
        self._sb_iface = sb_item("ArayÃ¼z: -")
        lay.addWidget(self._sb_iface)
        self._sb_ai = sb_item("AI: Gemini")
        lay.addWidget(self._sb_ai)
        self._sb_next = sb_item("Sonraki analiz: -")
        lay.addWidget(self._sb_next)
        lay.addStretch()
        self._sb_db = sb_item("DB: -")
        lay.addWidget(self._sb_db)
        self._sb_time = sb_item(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        lay.addWidget(self._sb_time)
        return bar

    def _on_tab_changed(self, idx):
        """Ä°lk aÃ§Ä±lÄ±ÅŸta sekme widget'larÄ±nÄ± oluÅŸtur (lazy), sonra refresh et."""
        if idx == 0:
            self._dashboard_tab.refresh()

        elif idx == 1:
            if self._analysis_tab is None:
                self._analysis_tab = AnalysisTab(self.db, self.analyzer)
                old=self._tabs.widget(1)
                self._tabs.removeWidget(old); old.deleteLater()
                self._tabs.insertWidget(1, self._analysis_tab)
                self._tabs.setCurrentIndex(1)
            self._analysis_tab.refresh()

        elif idx == 2:
            if self._data_tab is None:
                self._data_tab = DataTab(self.db)
                old=self._tabs.widget(2)
                self._tabs.removeWidget(old); old.deleteLater()
                self._tabs.insertWidget(2, self._data_tab)
                self._tabs.setCurrentIndex(2)
            self._data_tab.refresh()

        elif idx == 3:
            if self._blocked_tab is None:
                self._blocked_tab = BlockedTab(self.db)
                old=self._tabs.widget(3)
                self._tabs.removeWidget(old); old.deleteLater()
                self._tabs.insertWidget(3, self._blocked_tab)
                self._tabs.setCurrentIndex(3)
            self._blocked_tab.refresh()

        elif idx == 4:
            if self._trusted_tab is None:
                self._trusted_tab = TrustedTab(self.db)
                old=self._tabs.widget(4)
                self._tabs.removeWidget(old); old.deleteLater()
                self._tabs.insertWidget(4, self._trusted_tab)
                self._tabs.setCurrentIndex(4)
            self._trusted_tab.refresh()

        elif idx == 5:
            if self._settings_tab is None:
                self._settings_tab = SettingsTab()
                old=self._tabs.widget(5)
                self._tabs.removeWidget(old); old.deleteLater()
                self._tabs.insertWidget(5, self._settings_tab)
                self._tabs.setCurrentIndex(5)
            self._settings_tab.refresh()


    def _refresh_all(self):
        """Stats'Ä± arka planda Ã§ek, UI'Ä± bloklamadan gÃ¼ncelle."""
        if hasattr(self, "_stats_worker") and self._stats_worker.isRunning():
            return
        self._stats_worker = StatsWorker(self.db)
        self._stats_worker.done.connect(self._on_stats_ready)
        self._stats_worker.start()

    def _on_stats_ready(self, stats):
        try:
            dash = self._dashboard_tab
            dash.card_conns.set_value(f"{stats.get('today_connections', 0):,}")
            dash.card_threats.set_value(stats.get("total_threats", 0))
            dash.card_blocked.set_value(stats.get("blocked_ips", 0))
            dash.card_reports.set_value(stats.get("total_reports", 0))
            # Sadece aktif Dashboard sekmesindeyse tam refresh
            if self._tabs.currentIndex() == 0:
                dash.refresh()
        except Exception as e:
            log.error("Stats update error: %s", e)

    def _run_quick_analysis(self):
        if getattr(self, "_worker", None) and self._worker.isRunning():
            return
        self._status_label.setText("â— Analiz Ã§alÄ±ÅŸÄ±yorâ€¦")
        self._status_label.setStyleSheet(
            f"color:{C['warning']}; font-size:11px; font-family:'JetBrains Mono',monospace; border:none;"
        )

        def done(result):
            self._analysis_progress.reset()
            self._refresh_all()
            if getattr(self, "_worker", None):
                self._worker.deleteLater()
                self._worker = None

            risk_score = result.get("risk_score", 0)
            status = result.get("status", "")

            if risk_score == -1:
                self._status_label.setText("â— Hata oluÅŸtu")
                self._status_label.setStyleSheet(
                    f"color:{C['danger']}; font-size:11px; font-family:'JetBrains Mono',monospace; border:none;"
                )
                error_msg = result.get("summary", "Bilinmeyen hata")
                QMessageBox.warning(
                    self, "Analiz HatasÄ±",
                    f"Analiz sÄ±rasÄ±nda hata oluÅŸtu:\n\n{error_msg}\n\n"
                    "LÃ¼tfen Ayarlar'dan API anahtarÄ±nÄ±zÄ± kontrol edin."
                )
            else:
                self._status_label.setText("â— Analiz tamamlandÄ±")
                self._status_label.setStyleSheet(
                    f"color:{C['success']}; font-size:11px; font-family:'JetBrains Mono',monospace; border:none;"
                )

            QTimer.singleShot(5000, lambda: self._status_label.setText("â— Ä°zleme aktif"))

        def failed(message):
            done({
                "risk_score": -1,
                "status": "API HATASI",
                "summary": message,
                "suspicious_connections": [],
            })

        self._worker = AnalysisWorker(self.analyzer)
        self._worker.stage.connect(self._analysis_progress.set_stage)
        self._worker.finished.connect(done)
        self._worker.error.connect(failed)
        self._worker.start()


    def _block_ip(self, ip):
        reply = QMessageBox.question(
            self, "IP Engelle",
            f"<b>{ip}</b> adresini engellemek istiyor musunuz",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from kill_switch import block_ip
        from notifier import notify_ip_blocked
        ok = block_ip(ip, reason="Dashboard'dan engellendi", db=self.db)
        if ok:
            notify_ip_blocked(ip)
            self._refresh_all()
        else:
            QMessageBox.critical(self, "Hata", f"{ip} engellenemedi.\nYÃ¶netici yetkisi gerekli.")

    # â”€â”€ System Tray â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(_app_icon(), self)
        menu = QMenu()
        show_a = QAction("NetSonar'Ä± GÃ¶ster", self)
        show_a.triggered.connect(self.showNormal)
        menu.addAction(show_a)
        ana_a = QAction("Analizi BaÅŸlat", self)
        ana_a.triggered.connect(self._run_quick_analysis)
        menu.addAction(ana_a)
        menu.addSeparator()
        quit_a = QAction("Ã‡Ä±kÄ±ÅŸ", self)
        quit_a.triggered.connect(self._quit)
        menu.addAction(quit_a)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("NetSonar - AÄŸ korumasÄ± aktif")
        self.tray.activated.connect(lambda r: self.showNormal() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def _setup_timer(self):
        # Ä°lk refresh pencere aÃ§Ä±ldÄ±ktan 1.5 saniye sonra baÅŸlasÄ±n
        QTimer.singleShot(1500, self._refresh_all)
        # Periyodik refresh: 90 saniyede bir
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_all)
        self._timer.start(90_000)
        # Saat: sadece pencere gÃ¶rÃ¼nÃ¼rken gÃ¼ncelle
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick_clock)
        self._clock.start(1000)

    def _tick_clock(self):
        if self.isVisible():
            self._sb_time.setText(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))

    def _init_statusbar_config(self):
        """Statusbar'daki AI bilgisini baÅŸlangÄ±Ã§ta bir kez yÃ¼kle."""
        try:
            import config as cfg
            self._sb_ai.setText(f"AI: GEMINI - {cfg.GEMINI_MODEL}")
        except Exception:
            pass

    def closeEvent(self, event):
        from config import load_settings
        if load_settings().get("MINIMIZE_TO_TRAY", True):
            event.ignore()
            self.hide()
            self.tray.showMessage("NetSonar Arka Planda", "Ä°zleme devam ediyor.", QSystemTrayIcon.MessageIcon.Information, 2000)
        else:
            self._quit()

    def _quit(self):
        if hasattr(self, "_timer"):
            self._timer.stop()
        if hasattr(self, "_clock"):
            self._clock.stop()
        self.engine.stop()
        self.scheduler.stop()
        can_close_db = True
        for name in ("_worker", "_stats_worker", "_dash_worker"):
            worker = getattr(self, name, None)
            if worker and worker.isRunning():
                worker.wait(1500)
                can_close_db = can_close_db and not worker.isRunning()
        if can_close_db and hasattr(self.db, "close"):
            self.db.close()
        self.tray.hide()
        QApplication.quit()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  VERÄ° TAB (AnalysisDataTab - Sekme Olarak)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  DATA TAB (Veri Sekmesi)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class DataTabWorker(QThread):
    done = pyqtSignal(list, str)

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        last_ts = self.db.get_last_analysis_time()
        if last_ts is None:
            rows = self.db.get_summary(hours=1, limit=500)
            since_label = "Son 1 saat (henÃ¼z analiz yapÄ±lmadÄ±)"
        else:
            rows = self.db.get_summary_since(since_ts=last_ts, limit=500)
            since_label = f"Son analizden beri: {last_ts[:16]}"
        self.done.emit(rows, since_label)


class DataTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._page = 0
        self._page_size = 50
        self._all_rows = []
        self._selected_ip = None
        self._loading = False
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # â”€â”€ BaÅŸlÄ±k + Ä°statistik â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        hdr = QHBoxLayout()
        title = QLabel("Analize HazÄ±r Veri")
        title.setObjectName("title")
        hdr.addWidget(title)

        self._stats_lbl = QLabel("Veriler yÃ¼kleniyor...")
        self._stats_lbl.setStyleSheet(f"color:{C['text3']}; font-size:12px;")
        hdr.addWidget(self._stats_lbl)
        hdr.addStretch()
        root.addLayout(hdr)

        # â”€â”€ Sol: Tablo, SaÄŸ: Detay â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # Sol Panel: Tablo
        left = QWidget()
        left.setStyleSheet(f"background:{C['bg1']};")
        vl = QVBoxLayout(left)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(8)

        # Filtreler
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("âŒ•  IP veya sÃ¼reÃ§ araâ€¦")
        self._search.setMinimumHeight(34)
        self._search.textChanged.connect(self._filter_debounce)
        filter_row.addWidget(self._search, 2)

        self._proto_combo = QComboBox()
        self._proto_combo.addItems(["TÃ¼mÃ¼", "TCP", "UDP", "OTHER"])
        self._proto_combo.setMinimumHeight(34)
        self._proto_combo.currentTextChanged.connect(lambda _: self._filter())
        filter_row.addWidget(self._proto_combo)

        self._page_size_combo = QComboBox()
        self._page_size_combo.addItems(["50", "100", "250"])
        self._page_size_combo.setCurrentIndex(0)
        self._page_size_combo.setMinimumHeight(34)
        self._page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        lbl = QLabel("GÃ¶ster:")
        lbl.setStyleSheet(f"color:{C['text3']}; font-size:11px;")
        filter_row.addWidget(lbl)
        filter_row.addWidget(self._page_size_combo)
        vl.addLayout(filter_row)

        # HÄ±zlÄ± Filtreler
        quick_row = QHBoxLayout()
        quick_row.setSpacing(6)

        self._filter_suspicious = QCheckBox("ğŸ”´ ÅÃ¼pheli Port")
        self._filter_suspicious.stateChanged.connect(lambda _: self._filter())
        quick_row.addWidget(self._filter_suspicious)

        self._filter_high_traffic = QCheckBox(">1MB Trafik")
        self._filter_high_traffic.stateChanged.connect(lambda _: self._filter())
        quick_row.addWidget(self._filter_high_traffic)

        self._filter_after_hours = QCheckBox("ğŸŒ™ Mesai DÄ±ÅŸÄ±")
        self._filter_after_hours.stateChanged.connect(lambda _: self._filter())
        quick_row.addWidget(self._filter_after_hours)

        quick_row.addStretch()
        vl.addLayout(quick_row)

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["DURUM", "BAÄ", "HEDEF IP", "PORT", "PROTO", "VERÄ°", "SÃœREÃ‡", ""])
        self.table.verticalHeader().setVisible(False)
        _configure_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(3, 55)
        self.table.setColumnWidth(4, 55)
        self.table.setColumnWidth(5, 70)
        self.table.setColumnWidth(7, 90)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        vl.addWidget(self.table, 1)

        # Sayfalama
        page_row = QHBoxLayout()
        page_row.addStretch()
        self._prev_btn = QPushButton("â—€ Ã–nceki")
        self._prev_btn.setObjectName("ghost")
        self._prev_btn.clicked.connect(lambda: self._change_page(-1))
        self._page_lbl = QLabel("Sayfa 1")
        self._page_lbl.setStyleSheet(f"color:{C['text3']}; font-family:'JetBrains Mono',monospace; font-size:11px;")
        self._next_btn = QPushButton("Sonraki â–¶")
        self._next_btn.setObjectName("ghost")
        self._next_btn.clicked.connect(lambda: self._change_page(1))
        page_row.addWidget(self._prev_btn)
        page_row.addWidget(self._page_lbl)
        page_row.addWidget(self._next_btn)
        page_row.addStretch()
        vl.addLayout(page_row)

        splitter.addWidget(left)

        # SaÄŸ Panel: Detay
        self._detail_panel = self._create_detail_panel()
        splitter.addWidget(self._detail_panel)
        splitter.setSizes([600, 250])

        root.addWidget(splitter, 1)

    def _create_detail_panel(self):
        panel = QWidget()
        panel.setStyleSheet(f"background:{C['bg2']}; border:1px solid {C['border']}; border-radius:8px;")
        vl = QVBoxLayout(panel)
        vl.setContentsMargins(12, 12, 12, 12)
        vl.setSpacing(8)

        lbl = QLabel("BaÄŸlantÄ± DetayÄ±")
        lbl.setStyleSheet(f"color:{C['accent']}; font-weight:700; font-size:12px; border:none;")
        vl.addWidget(lbl)

        self._detail_content = QWidget()
        dv = QVBoxLayout(self._detail_content)
        dv.setSpacing(4)
        dv.setContentsMargins(0, 8, 0, 8)

        self._detail_ip = QLabel("IP: â€”")
        self._detail_port = QLabel("Port: â€”")
        self._detail_proto = QLabel("Protokol: â€”")
        self._detail_bytes = QLabel("Toplam Veri: â€”")
        self._detail_process = QLabel("SÃ¼reÃ§: â€”")
        self._detail_time = QLabel("Son GÃ¶rÃ¼lme: â€”")

        for lbl in [self._detail_ip, self._detail_port, self._detail_proto,
                     self._detail_bytes, self._detail_process, self._detail_time]:
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color:{C['text2']}; font-size:12px; border:none;")
            dv.addWidget(lbl)

        vl.addWidget(self._detail_content)

        self._detail_risk = QWidget()
        rv = QVBoxLayout(self._detail_risk)
        rv.setSpacing(2)
        rv.setContentsMargins(0, 8, 0, 0)

        rl = QLabel("ğŸ”´ Risk GÃ¶stergeleri")
        rl.setStyleSheet(f"color:{C['danger']}; font-weight:700; font-size:11px; border:none;")
        rv.addWidget(rl)

        self._risk_list = QLabel("BaÄŸlantÄ± seÃ§in")
        self._risk_list.setWordWrap(True)
        self._risk_list.setStyleSheet(f"color:{C['text3']}; font-size:12px; border:none;")
        rv.addWidget(self._risk_list)

        vl.addWidget(self._detail_risk)
        vl.addStretch()

        self._block_detail_btn = QPushButton("Engelle")
        self._block_detail_btn.setMinimumHeight(36)
        self._block_detail_btn.setObjectName("danger")
        self._block_detail_btn.clicked.connect(self._block_selected)
        self._block_detail_btn.setEnabled(False)
        vl.addWidget(self._block_detail_btn)

        return panel

    def refresh(self):
        if self._loading:
            return
        self._loading = True
        self._stats_lbl.setText("Veriler yÃ¼kleniyor...")
        self._worker = DataTabWorker(self.db)
        self._worker.done.connect(self._on_data_loaded)
        self._worker.start()

    def _on_data_loaded(self, rows, since_label):
        self._loading = False
        total_bytes = sum(r.get('total_bytes', 0) for r in rows)
        self._stats_lbl.setText(f"{len(rows)} baÄŸlantÄ±, {_fmt(total_bytes)} veri â€” {since_label}")
        self._all_rows = rows
        self._page = 0
        self._populate_table(rows)

    def _populate_table(self, rows):
        try:
            from config import SUSPICIOUS_PORTS as _SP
        except Exception:
            _SP = set()

        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)

        start = self._page * self._page_size
        end = start + self._page_size
        page_rows = rows[start:end]

        for row in page_rows:
            r = self.table.rowCount()
            self.table.insertRow(r)

            dst_ip = row.get('dst_ip', '')
            dst_port = row.get('dst_port', 0)
            proto = row.get('protocol', '')
            process = row.get('process', '')
            total_bytes = row.get('total_bytes', 0)
            conn_count = row.get('conn_count', 1)

            is_suspicious = dst_port in _SP or row.get('is_suspicious_port')
            is_high_traffic = row.get('is_high_traffic') or total_bytes > 1_000_000

            status_icon = "ğŸ”´" if is_suspicious else ("âš ï¸" if is_high_traffic else "âœ…")
            status = QTableWidgetItem(status_icon)
            status.setForeground(QColor(C["danger"]) if is_suspicious else QColor(C["text3"]))
            self.table.setItem(r, 0, status)

            conn_count = row.get('conn_count', 1)
            count_item = QTableWidgetItem(str(conn_count))
            count_item.setForeground(QColor(C["accent"] if conn_count > 10 else C["text3"]))
            self.table.setItem(r, 1, count_item)

            ip_item = QTableWidgetItem(dst_ip)
            ip_item.setForeground(QColor(C["danger"] if is_suspicious else C["text"]))
            self.table.setItem(r, 2, ip_item)

            port_item = QTableWidgetItem(str(dst_port))
            port_item.setForeground(QColor(C["danger"] if is_suspicious else C["text2"]))
            self.table.setItem(r, 3, port_item)

            proto_item = QTableWidgetItem(proto)
            proto_item.setForeground(QColor(C["text3"]))
            self.table.setItem(r, 4, proto_item)

            bytes_item = QTableWidgetItem(_fmt(total_bytes))
            bytes_item.setForeground(QColor(C["accent"] if is_high_traffic else C["text3"]))
            self.table.setItem(r, 5, bytes_item)

            proc_item = QTableWidgetItem(process)
            proc_item.setForeground(QColor(C["text2"]))
            self.table.setItem(r, 6, proc_item)

            block_btn = QPushButton("Engelle")
            block_btn.setMinimumHeight(30)
            block_btn.setStyleSheet("QPushButton { padding: 0 12px; font-size: 11px; }")
            block_btn.setObjectName("danger")
            block_btn.clicked.connect(lambda _, ip=dst_ip: self._block_ip(ip))
            self.table.setCellWidget(r, 7, block_btn)

        self.table.setUpdatesEnabled(True)
        self._page_lbl.setText(f"Sayfa {self._page + 1}")
        total_pages = max(1, (len(rows) + self._page_size - 1) // self._page_size)
        self._prev_btn.setEnabled(self._page > 0)
        self._next_btn.setEnabled(self._page < total_pages - 1)

    def _on_row_selected(self):
        selected = self.table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        if row < 0:
            return

        ip = self.table.item(row, 2).text()
        port = self.table.item(row, 3).text()
        proto = self.table.item(row, 4).text()
        bytes_val = self.table.item(row, 5).text()
        process = self.table.item(row, 6).text()

        self._detail_ip.setText(f"IP: {ip}")
        self._detail_port.setText(f"Port: {port}")
        self._detail_proto.setText(f"Protokol: {proto}")
        self._detail_bytes.setText(f"Toplam Veri: {bytes_val}")
        self._detail_process.setText(f"SÃ¼reÃ§: {process}")

        try:
            from config import SUSPICIOUS_PORTS
            is_suspicious_port = int(port) in SUSPICIOUS_PORTS
        except:
            is_suspicious_port = False

        risk_items = []
        if is_suspicious_port:
            risk_items.append("âš ï¸ Bilinen tehlikeli port")
        if "powershell" in process.lower() or "cmd" in process.lower() or "wscript" in process.lower():
            risk_items.append("âš ï¸ Sistem sÃ¼reci dÄ±ÅŸ baÄŸlantÄ±")

        if risk_items:
            self._risk_list.setText("\n".join(risk_items))
        else:
            self._risk_list.setText("Belirgin risk tespit edilmedi")

        self._block_detail_btn.setEnabled(True)
        self._selected_ip = ip

    def _block_ip(self, ip):
        reply = QMessageBox.question(
            self, "IP Engelle",
            f"<b>{ip}</b> adresini engellemek istiyor musunuz",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from kill_switch import block_ip
        from notifier import notify_ip_blocked
        ok = block_ip(ip, reason="Veri sekmesinden engellendi", db=self.db)
        if ok:
            notify_ip_blocked(ip)
            self.refresh()

    def _block_selected(self):
        if self._selected_ip:
            self._block_ip(self._selected_ip)

    def _filter_debounce(self):
        QTimer.singleShot(300, self._filter)

    def _filter(self):
        text = self._search.text().lower()
        proto = self._proto_combo.currentText()
        filter_suspicious = self._filter_suspicious.isChecked()
        filter_high = self._filter_high_traffic.isChecked()
        filter_hours = self._filter_after_hours.isChecked()

        try:
            from config import SUSPICIOUS_PORTS
        except:
            SUSPICIOUS_PORTS = set()

        filtered = []
        for row in self._all_rows:
            if text and text not in row.get('dst_ip', '').lower() and text not in row.get('process', '').lower():
                continue
            if proto != "TÃ¼mÃ¼" and row.get('protocol', '') != proto:
                continue

            is_susp = row.get('dst_port', 0) in SUSPICIOUS_PORTS

            if filter_suspicious and not is_susp:
                continue
            if filter_high and row.get('total_bytes', 0) < 1_000_000:
                continue

            filtered.append(row)

        self._page = 0
        self._populate_table(filtered)

    def _on_page_size_changed(self, val):
        self._page_size = int(val)
        self._page = 0
        self._populate_table(self._all_rows)

    def _change_page(self, delta):
        total = len(self._all_rows)
        total_pages = max(1, (total + self._page_size - 1) // self._page_size)
        new_page = self._page + delta
        if new_page < 0 or new_page >= total_pages:
            return
        self._page = new_page
        self._populate_table(self._all_rows)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  BLOCKED TAB (Engellenenler Sekmesi)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class BlockedTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._loading = False
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel("Engellenen IP Adresleri")
        title.setObjectName("title")
        hdr.addWidget(title)

        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet(f"color:{C['text3']}; font-size:12px;")
        hdr.addWidget(self._stats_lbl)
        hdr.addStretch()
        root.addLayout(hdr)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["IP ADRESÄ°", "SEBEP", "TARÄ°H", "EYLEM"])
        self.table.verticalHeader().setVisible(False)
        _configure_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table, 1)

        page_row = QHBoxLayout()
        page_row.addStretch()
        self._prev_btn = QPushButton("â—€ Ã–nceki")
        self._prev_btn.setObjectName("ghost")
        self._prev_btn.clicked.connect(lambda: self._change_page(-1))
        self._page_lbl = QLabel("Sayfa 1")
        self._page_lbl.setStyleSheet(f"color:{C['text3']}; font-family:'JetBrains Mono',monospace; font-size:11px;")
        self._next_btn = QPushButton("Sonraki â–¶")
        self._next_btn.setObjectName("ghost")
        self._next_btn.clicked.connect(lambda: self._change_page(1))
        page_row.addWidget(self._prev_btn)
        page_row.addWidget(self._page_lbl)
        page_row.addWidget(self._next_btn)
        page_row.addStretch()
        root.addLayout(page_row)

        self._page = 0
        self._page_size = 50
        self._all_rows = []

    def refresh(self):
        if self._loading:
            return
        self._loading = True
        self._worker = BlockedTabWorker(self.db)
        self._worker.done.connect(self._on_data_loaded)
        self._worker.start()

    def _on_data_loaded(self, blocked):
        self._loading = False
        self._all_rows = blocked

        total = len(blocked)
        today = sum(1 for b in blocked if b.get('blocked_at', '').startswith(datetime.now().strftime('%Y-%m-%d')))

        self._stats_lbl.setText(f"Toplam: {total} | BugÃ¼n: {today}")
        self._page = 0
        self._populate_table()

    def _populate_table(self):
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)

        start = self._page * self._page_size
        end = start + self._page_size
        page_rows = self._all_rows[start:end]

        for entry in page_rows:
            r = self.table.rowCount()
            self.table.insertRow(r)

            ip = entry.get('ip', '')
            ip_item = QTableWidgetItem(ip)
            ip_item.setForeground(QColor(C["danger"]))
            self.table.setItem(r, 0, ip_item)

            reason_item = QTableWidgetItem(entry.get('reason', '-'))
            reason_item.setForeground(QColor(C["text2"]))
            self.table.setItem(r, 1, reason_item)

            dt = entry.get('blocked_at', '')[:19].replace('T', ' ')
            dt_item = QTableWidgetItem(dt)
            dt_item.setForeground(QColor(C["text3"]))
            self.table.setItem(r, 2, dt_item)

            unblock_btn = QPushButton("KaldÄ±r")
            unblock_btn.setMinimumSize(78, 30)
            unblock_btn.setObjectName("ghost")
            unblock_btn.clicked.connect(lambda _, ipt=ip: self._unblock_ip(ipt))
            self.table.setCellWidget(r, 3, unblock_btn)

        self.table.setUpdatesEnabled(True)

        total = len(self._all_rows)
        total_pages = max(1, (total + self._page_size - 1) // self._page_size)
        self._page_lbl.setText(f"Sayfa {self._page + 1} / {total_pages}")
        self._prev_btn.setEnabled(self._page > 0)
        self._next_btn.setEnabled(self._page < total_pages - 1)

    def _unblock_ip(self, ip):
        reply = QMessageBox.question(
            self, "Engel KaldÄ±r",
            f"<b>{ip}</b> IP'sinin engelini kaldÄ±rmak istiyor musunuz",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from kill_switch import unblock_ip
        ok = unblock_ip(ip)
        if ok:
            self.refresh()

    def _change_page(self, delta):
        total = len(self._all_rows)
        total_pages = max(1, (total + self._page_size - 1) // self._page_size)
        new_page = self._page + delta
        if new_page < 0 or new_page >= total_pages:
            return
        self._page = new_page
        self._populate_table()


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  SETTINGS TAB (Ayarlar Sekmesi)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•



# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  TRUSTED TAB (GÃ¼venli IP'ler)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class TrustedTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._loading = False
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("GÃ¼venli IP Adresleri")
        title.setObjectName("title")
        subtitle = QLabel("Bu IP'ler baÄŸlantÄ± geÃ§miÅŸinde kalÄ±r, ancak AI analizine ve otomatik engellemeye katÄ±lmaz.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{C['text3']}; font-size:12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        hdr.addLayout(title_box)
        hdr.addStretch()
        add_btn = QPushButton("+ IP Ekle")
        add_btn.setObjectName("primary")
        add_btn.setMinimumHeight(36)
        add_btn.clicked.connect(self._add_ip)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)

        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet(f"color:{C['text3']}; font-size:12px;")
        root.addWidget(self._stats_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["IP ADRESÄ°", "AÃ‡IKLAMA", "EKLENME TARÄ°HÄ°", "EYLEM"])
        _configure_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.table, 1)

    def refresh(self):
        if self._loading:
            return
        self._loading = True
        self._worker = TrustedTabWorker(self.db)
        self._worker.done.connect(self._on_loaded)
        self._worker.start()

    def _on_loaded(self, entries):
        self._loading = False
        self._stats_lbl.setText(f"Toplam {len(entries)} gÃ¼venli IP")
        self.table.setRowCount(0)
        for entry in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            ip = entry.get("ip", "")
            values = [
                ip,
                entry.get("note", "") or "â€”",
                entry.get("added_at", "")[:19].replace("T", " "),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setForeground(QColor(C["success"] if col == 0 else C["text2"]))
                item.setToolTip(str(value))
                self.table.setItem(row, col, item)
            remove_btn = QPushButton("Listeden Ã‡Ä±kar")
            remove_btn.setObjectName("ghost")
            remove_btn.setMinimumSize(104, 30)
            remove_btn.clicked.connect(lambda _, target=ip: self._remove_ip(target))
            self.table.setCellWidget(row, 3, remove_btn)

    def _add_ip(self):
        if _show_trusted_ip_dialog(self, self.db):
            self.refresh()

    def _remove_ip(self, ip):
        reply = QMessageBox.question(
            self,
            "GÃ¼venli Listeden Ã‡Ä±kar",
            f"<b>{ip}</b> yeniden sonraki AI analizlerine katÄ±lsÄ±n mÄ±?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.db.remove_trusted_ip(ip):
            self.refresh()
        else:
            QMessageBox.warning(self, "KayÄ±t BulunamadÄ±", f"{ip} gÃ¼venli listede bulunamadÄ±.")


class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._all_models = []
        self._selected_model = None
        self._gemini_api_keys = ""
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border:none; background:{C['bg']}; }}")

        content = QWidget()
        content.setStyleSheet(f"background:{C['bg']};")
        cv = QVBoxLayout(content)
        cv.setSpacing(14)

        # AI settings
        ai_gb = QGroupBox("AI AyarlarÄ±")
        ai_fl = QFormLayout(ai_gb)
        ai_fl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._provider_fixed = QLabel("Gemini")
        self._provider_fixed.setWordWrap(True)
        self._provider_fixed.setStyleSheet(f"color:{C['accent']}; font-weight:700;")
        ai_fl.addRow("AI saÄŸlayÄ±cÄ±:", self._provider_fixed)

        self._fixed_model = QLabel("gemini-3.1-flash-lite")
        self._fixed_model.setWordWrap(True)
        self._fixed_model.setStyleSheet(
            f"color:{C['text']}; font-weight:700; font-family:'JetBrains Mono','Consolas',monospace;"
        )
        ai_fl.addRow("Model:", self._fixed_model)

        key_row=QWidget(); key_layout=QHBoxLayout(key_row); key_layout.setContentsMargins(0,0,0,0)
        self._api_key=QLineEdit(); self._api_key.setPlaceholderText("Gemini API keys")
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password); self._api_key.setMinimumHeight(40)
        self._api_key.textChanged.connect(self._on_api_key_changed)
        self._show_keys_btn=QPushButton("GÃ¶ster"); self._show_keys_btn.setObjectName("ghost")
        self._show_keys_btn.setCheckable(True); self._show_keys_btn.clicked.connect(self._toggle_api_keys)
        key_layout.addWidget(self._api_key,1); key_layout.addWidget(self._show_keys_btn)
        ai_fl.addRow("Gemini API keyleri:",key_row)

        self._key_status = QLabel("KayÄ±tlÄ± key yok")
        self._key_status.setWordWrap(True)
        self._key_status.setStyleSheet(f"color:{C['text3']}; font-size:12px;")
        ai_fl.addRow("Key durumu:", self._key_status)

        self._model_status = QLabel("Sabit model kullanÄ±lÄ±yor. OpenRouter/Ollama ve alternatif model seÃ§imi devre dÄ±ÅŸÄ±.")
        self._model_status.setWordWrap(True)
        self._model_status.setStyleSheet(f"color:{C['text3']}; font-size:12px;")
        ai_fl.addRow("Not:", self._model_status)

        cv.addWidget(ai_gb)

        # Analiz Zamanlama
        timing_gb = QGroupBox("Analiz Zamanlama")
        timing_fl = QFormLayout(timing_gb)

        self._auto_analysis_cb = QCheckBox("AÃ§Ä±k")
        self._auto_analysis_cb.setChecked(True)
        timing_fl.addRow("Otomatik Analiz:", self._auto_analysis_cb)

        self._interval_combo = QComboBox()
        self._interval_combo.addItems([
            "Her 15 dakikada bir",
            "Her 30 dakikada bir",
            "Her 1 saatte bir",
            "Her 2 saatte bir",
            "Her 6 saatte bir",
        ])
        self._interval_combo.setCurrentIndex(2)
        timing_fl.addRow("Periyot:", self._interval_combo)

        cv.addWidget(timing_gb)

        # GÃ¼venlik
        sec_gb = QGroupBox("GÃ¼venlik")
        sec_fl = QFormLayout(sec_gb)

        self._auto_block_cb = QCheckBox("Otomatik IP engelleme")
        sec_fl.addRow("", self._auto_block_cb)

        self._min_risk_combo = QComboBox()
        self._min_risk_combo.addItems(["5.0", "6.0", "7.0", "8.0", "9.0"])
        self._min_risk_combo.setCurrentIndex(2)
        sec_fl.addRow("Min Risk Skoru:", self._min_risk_combo)

        cv.addWidget(sec_gb)

        # Sistem
        sys_gb = QGroupBox("Sistem")
        sys_fl = QFormLayout(sys_gb)

        self._autostart_cb = QCheckBox("Windows'ta otomatik baÅŸlat")
        sys_fl.addRow("", self._autostart_cb)

        self._tray_cb = QCheckBox("KapatÄ±lÄ±nca tepsiye kÃ¼Ã§Ã¼lt")
        self._tray_cb.setChecked(True)
        sys_fl.addRow("", self._tray_cb)

        cv.addWidget(sys_gb)

        # Prompt
        prompt_gb = QGroupBox("AI Prompt")
        prompt_vl = QVBoxLayout(prompt_gb)

        desc = QLabel("AI'nin trafik analizinde kullandÄ±ÄŸÄ± talimatlar.")
        desc.setStyleSheet(f"color:{C['text3']}; font-size:11px;")
        desc.setWordWrap(True)
        prompt_vl.addWidget(desc)

        self._prompt = QTextEdit()
        self._prompt.setMinimumHeight(200)
        prompt_vl.addWidget(self._prompt)

        pbr = QHBoxLayout()
        pbr.addStretch()
        reset_btn = QPushButton("VarsayÄ±lana SÄ±fÄ±rla")
        reset_btn.setObjectName("ghost")
        reset_btn.clicked.connect(self._reset_prompt)
        pbr.addWidget(reset_btn)
        prompt_vl.addLayout(pbr)

        cv.addWidget(prompt_gb)
        cv.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        # Kaydet butonu
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Kaydet")
        save_btn.setMinimumSize(120, 40)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)
    def _load_settings(self):
            from config import load_settings, get_ai_prompt, DEFAULT_SYSTEM_PROMPT

            s = load_settings()

            self._auto_analysis_cb.setChecked(s.get("AUTO_ANALYSIS_ENABLED", True))

            interval_minutes = s.get("ANALYSIS_INTERVAL_MINUTES", 60)
            interval_map = {15: 0, 30: 1, 60: 2, 120: 3, 360: 4}
            idx = interval_map.get(interval_minutes, 2)
            self._interval_combo.setCurrentIndex(idx)

            self._auto_block_cb.setChecked(s.get("AUTO_BLOCK_ENABLED", False))
            self._autostart_cb.setChecked(s.get("autostart", False))
            self._tray_cb.setChecked(s.get("MINIMIZE_TO_TRAY", True))

            min_risk = s.get("AUTO_BLOCK_MIN_RISK_SCORE", 7.0)
            idx = self._min_risk_combo.findText(str(min_risk))
            if idx >= 0:
                self._min_risk_combo.setCurrentIndex(idx)

            api_keys = s.get("GEMINI_API_KEYS", []) or []
            if isinstance(api_keys, str):
                api_keys = [k.strip() for k in api_keys.replace(",", "\n").replace(";", "\n").splitlines() if k.strip()]
            if not api_keys and s.get("GEMINI_API_KEY", ""):
                api_keys = [s.get("GEMINI_API_KEY", "")]
            self._gemini_api_keys = "\n".join(api_keys)
            self._api_key.setText(", ".join(api_keys))
            self._update_key_status()
            try:
                self._prompt.setText(get_ai_prompt())
            except:
                self._prompt.setText(DEFAULT_SYSTEM_PROMPT)

    def refresh(self):
        self._load_settings()
    def _on_api_key_changed(self):
        self._gemini_api_keys = self._api_key.text()
        self._update_key_status()

    def _toggle_api_keys(self, visible):
        self._api_key.setEchoMode(QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)
        self._show_keys_btn.setText("Gizle" if visible else "GÃ¶ster")

    def _update_key_status(self):
        keys = []
        seen_keys = set()
        text = self._api_key.text().replace(",", "\n").replace(";", "\n")
        for raw_key in text.splitlines():
            key = raw_key.strip()
            if key and key not in seen_keys:
                keys.append(key)
                seen_keys.add(key)
        if not keys:
            self._key_status.setText("KayÄ±tlÄ± Gemini API key yok")
            self._key_status.setStyleSheet(f"color:{C['warning']}; font-size:11px;")
        else:
            self._key_status.setText(f"{len(keys)} Gemini API key kayÄ±tlÄ±. 429/503 durumunda key 30 dakika bekletilir.")
            self._key_status.setStyleSheet(f"color:{C['success']}; font-size:11px;")

    def _reset_prompt(self):
        from config import DEFAULT_SYSTEM_PROMPT
        self._prompt.setText(DEFAULT_SYSTEM_PROMPT)

    def _save(self):
        try:
            from config import save_settings, save_ai_prompt, load_settings
            import importlib

            prov = "gemini"
            api_key_text = self._api_key.text()
            api_keys = []
            seen_keys = set()
            for raw_key in api_key_text.replace(",", "\n").replace(";", "\n").splitlines():
                key = raw_key.strip()
                if key and key not in seen_keys:
                    api_keys.append(key)
                    seen_keys.add(key)
            model = "gemini-3.1-flash-lite"

            interval_map = {0: 15, 1: 30, 2: 60, 3: 120, 4: 360}
            interval_minutes = interval_map.get(self._interval_combo.currentIndex(), 60)

            s = load_settings()
            s["AI_PROVIDER"] = prov
            s["AUTO_ANALYSIS_ENABLED"] = self._auto_analysis_cb.isChecked()
            s["ANALYSIS_INTERVAL_MINUTES"] = interval_minutes
            s["AUTO_BLOCK_ENABLED"] = self._auto_block_cb.isChecked()
            s["AUTO_BLOCK_MIN_RISK_SCORE"] = float(self._min_risk_combo.currentText())
            s["autostart"] = self._autostart_cb.isChecked()
            s["MINIMIZE_TO_TRAY"] = self._tray_cb.isChecked()

            s["GEMINI_API_KEYS"] = api_keys
            s["GEMINI_API_KEY"] = api_keys[0] if api_keys else ""
            s["GEMINI_MODEL"] = model

            save_settings(s)

            import config
            importlib.reload(config)

            p = self._prompt.toPlainText()
            if p.strip():
                save_ai_prompt(p)

            QMessageBox.information(self, "âœ“ BaÅŸarÄ±lÄ±", "Ayarlar kaydedildi.\nDeÄŸiÅŸiklikler bir sonraki analizde geÃ§erli olur.")

        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Ayarlar kaydedilirken hata:\n{e}")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  UYGULAMA BAÅLATICI
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
#  UYGULAMA BAÅLATICI
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def run_gui(db, analyzer, engine, scheduler):
    # Windows bildirimlerini python.exe yerine NetSonar uygulamas?yla ili?kilendir.
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "NetSonar.NetworkMonitor"
            )
        except Exception:
            pass

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("NetSonar")
    app.setApplicationDisplayName("NetSonar")
    app.setOrganizationName("NetSonar")
    app.setWindowIcon(_app_icon())
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow(db=db, analyzer=analyzer, engine=engine, scheduler=scheduler)
    window.show()
    # Config bilgisini hemen gÃ¶ster, aÄŸÄ±r DB sorgularÄ±nÄ± timer baÅŸlatÄ±r
    window._init_statusbar_config()
    return app.exec()
