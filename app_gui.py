"""
NetSonar — Yeniden Tasarlanmış PyQt6 Arayüzü
Cyber-Noir SOC Estetiği · JetBrains Mono + Sora tipografisi
"""

import sys
import os
import time
import json
import threading
from datetime import datetime
from config import get_app_version


# dns_cache lazy import edilir — başlangıçta yüklenmiyor
_dns_cache = None
def _resolve(ip):
    global _dns_cache
    if _dns_cache is None:
        try:
            import dns_cache as _dc
            _dns_cache = _dc
        except Exception:
            return ip
    return _dns_cache.resolve(ip)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLabel,
    QTabWidget, QLineEdit, QComboBox, QCheckBox, QSpinBox, QFrame, QSizePolicy,
    QTextEdit, QTextBrowser, QSystemTrayIcon, QMenu, QMessageBox, QFormLayout,
    QGroupBox, QRadioButton, QButtonGroup, QScrollArea, QSplitter,
    QProgressBar, QWidgetAction, QDialog, QStackedWidget, QListWidget,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, pyqtSlot, QSize, QMetaObject, Q_ARG
from PyQt6.QtGui import (
    QIcon, QColor, QFont, QPixmap, QPainter, QAction, QBrush,
    QLinearGradient, QPainterPath, QPen,
)

# ─── Renk Paleti (Cyber-Noir SOC) ─────────────────────────────────────
C = {
    "bg":        "#05070f",
    "bg1":       "#080c18",
    "bg2":       "#0c1120",
    "bg3":       "#111828",
    "border":    "#1a2540",
    "border2":   "#243055",
    "accent":    "#00d4ff",
    "accent2":   "#0096b8",
    "teal":      "#00ffb8",
    "danger":    "#ff3b5c",
    "warning":   "#ffb740",
    "success":   "#00e676",
    "purple":    "#a855f7",
    "text":      "#e8f0ff",
    "text2":     "#8899bb",
    "text3":     "#4d607a",
    "mono":      "JetBrains Mono",
}

STYLESHEET = f"""
/* ── Temel ── */
QMainWindow, QWidget {{
    background: {C["bg"]};
    color: {C["text"]};
    font-family: 'Segoe UI', 'Sora', sans-serif;
    font-size: 13px;
}}

/* ── Tab ── */
QTabWidget::pane {{
    border: 1px solid {C["border"]};
    background: {C["bg1"]};
    border-radius: 0px;
}}
QTabBar::tab {{
    background: {C["bg1"]};
    color: {C["text3"]};
    padding: 11px 22px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 600;
    font-size: 12px;
    letter-spacing: 0.03em;
}}
QTabBar::tab:selected {{
    color: {C["accent"]};
    border-bottom: 2px solid {C["accent"]};
    background: {C["bg2"]};
}}
QTabBar::tab:hover {{ color: {C["text2"]}; }}

/* ── Tablo ── */
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
    font-size: 10px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
}}

/* ── Butonlar ── */
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

/* ── Input ── */
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

/* ── GroupBox ── */
QGroupBox {{
    border: 1px solid {C["border"]};
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px;
    color: {C["text2"]};
    font-weight: 700;
    font-size: 11px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px; top: -9px;
    padding: 0 8px;
    background: {C["bg"]};
    color: {C["text3"]};
}}

/* ── ScrollBar ── */
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

/* ── TextEdit ── */
QTextEdit, QTextBrowser {{
    background: {C["bg3"]};
    color: {C["text"]};
    border: 1px solid {C["border"]};
    border-radius: 6px;
    font-family: 'JetBrains Mono', 'Cascadia Code', monospace;
    font-size: 12px;
    padding: 6px;
}}

/* ── CheckBox ── */
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

/* ── ProgressBar ── */
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

/* ── QDialog ── */
QDialog {{
    background: {C["bg1"]};
}}

/* ── SplashBar ── */
QSplitter::handle {{
    background: {C["border"]};
    width: 1px;
}}

QLabel#title {{
    font-size: 20px;
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


# ═══════════════════════════════════════════════════════════════════════
#  WORKER THREADS  (değişmedi)
# ═══════════════════════════════════════════════════════════════════════

class AIWorker(QThread):
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)
    def __init__(self, analyzer, force_full=False):
        super().__init__()
        self.analyzer   = analyzer
        self.force_full = force_full
    def run(self):
        try:
            result = self.analyzer.analyze(hours=1, force_full=self.force_full)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class ModelFetchWorker(QThread):
    fetched = pyqtSignal(list)
    error   = pyqtSignal(str)
    def run(self):
        try:
            import requests, importlib, config
            importlib.reload(config)
            r = requests.get(
                f"{config.OPENROUTER_BASE_URL}/models",
                headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"},
                timeout=8,
            )
            models = r.json().get("data", [])
            free = sorted([
                m["id"] for m in models
                if float((m.get("pricing") or {}).get("prompt", "1") or "1") == 0
            ])
            self.fetched.emit(free or ["Ücretsiz model bulunamadı"])
        except Exception as exc:
            self.error.emit(str(exc))


class AnalysisWorker(QThread):
    finished = pyqtSignal(dict)
    stage = pyqtSignal(str, int)
    def __init__(self, analyzer):
        super().__init__()
        self.analyzer = analyzer

    def _stage_callback(self, stage_name, progress):
        self.stage.emit(stage_name, progress)

    def run(self):
        def stage_cb(name, prog):
            self.stage.emit(name, prog)
        result = self.analyzer.analyze(hours=1, force_full=True, stage_callback=stage_cb)
        self.finished.emit(result)


class AnalysisProgressWidget(QWidget):
    stages = [
        "Hazırlanıyor…",
        "İşleniyor…",
        "Gönderiliyor…",
        "Bekleniyor…",
        "İşleniyor…",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(180)
        self._progress_bar.setFixedHeight(14)
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
        self._percent_lbl.setFixedWidth(35)
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
    """Ana istatistikleri (stats) arka planda çeker."""
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
    """Dashboard için tüm ağır DB sorgularını arka planda çalıştırır."""
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


# ═══════════════════════════════════════════════════════════════════════
#  YARDIMCI FONKSİYONLAR
# ═══════════════════════════════════════════════════════════════════════

def _fmt(b):
    if b < 1_024:          return f"{b} B"
    if b < 1_024**2:       return f"{b/1_024:.1f} KB"
    if b < 1_024**3:       return f"{b/1_024**2:.1f} MB"
    return f"{b/1_024**3:.2f} GB"


# ═══════════════════════════════════════════════════════════════════════
#  UI YARDIMCI WİDGET'LER
# ═══════════════════════════════════════════════════════════════════════

class Separator(QFrame):
    """İnce yatay çizgi ayırıcı."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background: {C['border']}; border: none;")


class SectionLabel(QLabel):
    """Küçük büyük harfli bölüm başlığı."""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"color: {C['text3']}; font-size: 10px; font-weight: 700; "
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
            f"border-radius:4px; padding:2px 7px; font-size:10px; font-weight:700; "
            f"font-family:'JetBrains Mono','Consolas',monospace;"
        )


class StatCard(QFrame):
    """Sol kenarlıklı istatistik kartı."""
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
        self.setMinimumHeight(88)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(3)

        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"font-size:30px; font-weight:700; color:{color}; border:none; "
            f"font-family:'JetBrains Mono','Consolas',monospace; letter-spacing:-0.02em;"
        )
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{C['text2']}; font-size:11px; font-weight:600; border:none; letter-spacing:0.04em;")
        sub = QLabel(subtitle)
        sub.setStyleSheet(f"color:{C['text3']}; font-size:10px; border:none; font-family:'JetBrains Mono',monospace;")

        lay.addWidget(self._val)
        lay.addWidget(lbl)
        lay.addWidget(sub)

    def set_value(self, v):
        self._val.setText(str(v))


class MiniLineChart(QFrame):
    """Hafif çizgi grafik — bağımlılık yok."""
    def __init__(self, data=None, color=None, parent=None):
        super().__init__(parent)
        self._data  = data or []
        self._color = color or C["accent"]
        self.setMinimumHeight(36)
        self.setMaximumHeight(44)
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
    """Başlık + sağ aksiyonları olan kart başlığı."""
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame {{ background:{C['bg3']}; border:none; "
            f"border-bottom:1px solid {C['border']}; border-radius:0; }}"
        )
        self.setFixedHeight(44)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 12, 0)

        self._title = QLabel(title)
        self._title.setStyleSheet(f"color:{C['text']}; font-size:13px; font-weight:600; border:none;")
        lay.addWidget(self._title)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"color:{C['text3']}; font-size:10px; font-family:'JetBrains Mono',monospace; border:none; margin-left:8px;")
            lay.addWidget(sub)

        lay.addStretch()
        self._right = lay  # butonlar eklenebilir

    def add_widget(self, w):
        self._right.addWidget(w)

    def set_subtitle(self, text):
        pass


class NeoCard(QFrame):
    """Kenarlıklı, başlıklı kart container."""
    def __init__(self, title="", subtitle="", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QFrame#neocard {{ background:{C['bg2']}; border:1px solid {C['border']}; "
            f"border-radius:10px; }}"
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


# ═══════════════════════════════════════════════════════════════════════
#  DASHBOARD SEKMESİ
# ═══════════════════════════════════════════════════════════════════════

class DashboardTab(QWidget):
    request_block = pyqtSignal(str)

    def __init__(self, db):
        super().__init__()
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        # ── Stat Kartları ──────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)
        self.card_conns   = StatCard("BUGÜNKÜ BAĞLANTI",  "0",  "blue",  "güncelleniyor…")
        self.card_threats = StatCard("TEHDİT TESPİTİ",    "0",  "red",   "toplam")
        self.card_blocked = StatCard("ENGELLENDİ",         "0",  "amber", "IP adresi")
        self.card_reports = StatCard("AI RAPORU",          "0",  "green", "çalıştırıldı")
        for c in (self.card_conns, self.card_threats, self.card_blocked, self.card_reports):
            cards_row.addWidget(c)
        root.addLayout(cards_row)

        # ── Orta satır: Trafik + Top IP ─────────────────────────────
        mid = QHBoxLayout()
        mid.setSpacing(12)

        # Trafik paneli
        self._traffic_card = NeoCard("VERİ TRANSFERİ", "son 1 saat")
        tc_body = self._traffic_card.body_layout()
        tc_body.setContentsMargins(14, 10, 14, 10)
        tc_body.setSpacing(8)

        # Hız satırı
        speed_row = QHBoxLayout()
        self._speed_lbl = QLabel("⚡ — KB/s")
        self._speed_lbl.setStyleSheet(f"color:{C['accent']}; font-family:'JetBrains Mono',monospace; font-size:12px; font-weight:700; border:none;")
        self._cmp_lbl = QLabel("")
        self._cmp_lbl.setStyleSheet(f"color:{C['text3']}; font-size:10px; font-family:'JetBrains Mono',monospace; border:none;")
        speed_row.addWidget(self._speed_lbl)
        speed_row.addWidget(self._cmp_lbl)
        speed_row.addStretch()
        tc_body.addLayout(speed_row)

        # Dönem kartları
        periods_row = QHBoxLayout()
        periods_row.setSpacing(6)
        self._period_cards = []
        for lbl in ("Saat", "Gün", "Hafta", "Ay", "Yıl"):
            pf = QFrame()
            pf.setStyleSheet(
                f"QFrame {{ background:{C['bg3']}; border:1px solid {C['border']}; "
                f"border-radius:7px; }}"
            )
            pv = QVBoxLayout(pf)
            pv.setContentsMargins(8, 6, 8, 6)
            pv.setSpacing(1)
            pl = QLabel(lbl)
            pl.setStyleSheet(f"color:{C['text3']}; font-size:9px; font-weight:700; letter-spacing:0.08em; border:none;")
            ul = QLabel("↑ —")
            ul.setStyleSheet(f"color:{C['success']}; font-size:11px; font-weight:600; font-family:'JetBrains Mono',monospace; border:none;")
            dl = QLabel("↓ —")
            dl.setStyleSheet(f"color:{C['accent']}; font-size:11px; font-weight:600; font-family:'JetBrains Mono',monospace; border:none;")
            tl = QLabel("= —")
            tl.setStyleSheet(f"color:{C['text3']}; font-size:9px; font-family:'JetBrains Mono',monospace; border:none;")
            pv.addWidget(pl); pv.addWidget(ul); pv.addWidget(dl); pv.addWidget(tl)
            periods_row.addWidget(pf)
            self._period_cards.append({"up": ul, "dn": dl, "tot": tl})
        tc_body.addLayout(periods_row)

        # Mini chart
        chart_row = QHBoxLayout()
        chart_row.setSpacing(6)
        for title, color in (("↑ Gönderim", C["success"]), ("↓ İndirim", C["accent"])):
            cf = QFrame()
            cf.setStyleSheet(f"QFrame {{ background:{C['bg3']}; border:1px solid {C['border']}; border-radius:5px; }}")
            cv = QVBoxLayout(cf)
            cv.setContentsMargins(6, 4, 6, 4)
            ct = QLabel(title)
            ct.setStyleSheet(f"color:{color}; font-size:9px; font-weight:700; border:none;")
            cv.addWidget(ct)
            chart = MiniLineChart(color=color)
            cv.addWidget(chart)
            chart_row.addWidget(cf, 1)
            if "Gönderim" in title:
                self._upload_chart = chart
            else:
                self._download_chart = chart
        tc_body.addLayout(chart_row)

        # Süreç / Protokol / Aktif satırı
        extra_row = QHBoxLayout()
        extra_row.setSpacing(8)
        for attr, label, color in (
            ("_proc_lbl",   "🔃 Süreçler",    C["text2"]),
            ("_proto_lbl",  "🌐 Protokol",    C["accent"]),
            ("_active_lbl", "🔗 Aktif IP",    C["teal"]),
        ):
            ef = QFrame()
            ef.setStyleSheet(f"QFrame {{ background:{C['bg3']}; border:1px solid {C['border']}; border-radius:5px; }}")
            ev = QVBoxLayout(ef)
            ev.setContentsMargins(8, 4, 8, 4); ev.setSpacing(1)
            etl = QLabel(label)
            etl.setStyleSheet(f"color:{C['text3']}; font-size:9px; font-weight:700; border:none;")
            evl = QLabel("—")
            evl.setStyleSheet(f"color:{color}; font-size:10px; font-family:'JetBrains Mono',monospace; border:none;")
            ev.addWidget(etl); ev.addWidget(evl)
            extra_row.addWidget(ef, 1)
            setattr(self, attr, evl)
        tc_body.addLayout(extra_row)

        mid.addWidget(self._traffic_card, 3)

        # Top IP kartı
        self._topip_card = NeoCard("EN YÜKSEK TRAFİK", "son 24 saat")
        tip_body = self._topip_card.body_layout()
        tip_body.setContentsMargins(0, 0, 0, 0)
        self._topip_table = QTableWidget()
        self._topip_table.setColumnCount(3)
        self._topip_table.setHorizontalHeaderLabels(["IP", "Veri", "Bağ."])
        self._topip_table.verticalHeader().setVisible(False)
        self._topip_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._topip_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._topip_table.setMaximumHeight(220)
        tip_body.addWidget(self._topip_table)
        mid.addWidget(self._topip_card, 2)

        root.addLayout(mid)


    # ── Yenile ─────────────────────────────────────────────────────────
    def refresh(self):
        """Tüm DB sorgularını arka planda çalıştırır — UI bloklanmaz."""
        if hasattr(self, "_dash_worker") and self._dash_worker.isRunning():
            return
        self._dash_worker = DashboardWorker(self.db)
        self._dash_worker.done.connect(self._on_data_ready)
        self._dash_worker.start()

    def _on_data_ready(self, data):
        """Worker tamamlandığında UI thread'de tüm alanları güncelle."""
        traffic  = data.get("traffic", [])
        top_ips  = data.get("top_ips", [])
        speed    = data.get("speed", {})
        procs    = data.get("procs", [])
        protos   = data.get("protos", {})
        active   = data.get("active", 0)
        timeline = data.get("timeline", [])

        for i, p in enumerate(traffic):
            if i >= len(self._period_cards):
                break
            c = self._period_cards[i]
            c["up"].setText(f"↑ {_fmt(p['upload'])}")
            c["dn"].setText(f"↓ {_fmt(p['download'])}")
            c["tot"].setText(f"= {_fmt(p['total'])}  ({p['conn_count']:,} bağ)")

        if speed:
            self._speed_lbl.setText(f"⚡ {speed.get('total_kbs', 0):.1f} KB/s")
        if procs:
            self._proc_lbl.setText(" · ".join(p["process"][:12] for p in procs))
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


# ═══════════════════════════════════════════════════════════════════════
#  AI ANALİZ SEKMESİ
# ═══════════════════════════════════════════════════════════════════════

class AnalysisTabWorker(QThread):
    done = pyqtSignal(list)

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        reports = self.db.get_all_reports()
        self.done.emit(reports)


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
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── 2x2 Grid Layout ─────────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)

        # Risk Skoru Kartı (0, 0) - Sol Üst
        risk_frame = QFrame()
        risk_frame.setStyleSheet(
            f"QFrame {{ background:{C['bg2']}; border:1px solid {C['border']}; border-radius:10px; }}"
        )
        risk_frame.setMinimumHeight(120)
        risk_lay = QHBoxLayout(risk_frame)
        risk_lay.setContentsMargins(16, 12, 16, 12)
        risk_lay.setSpacing(16)

        self._risk_score = QLabel("—")
        self._risk_score.setStyleSheet(
            f"font-size:40px; font-weight:700; color:{C['text3']}; "
            f"font-family:'JetBrains Mono',monospace; border:none;"
        )
        risk_lay.addWidget(self._risk_score)

        right_v = QVBoxLayout()
        self._risk_status = QLabel("Henüz Analiz Yapılmadı")
        self._risk_status.setStyleSheet(f"font-size:14px; font-weight:700; color:{C['text3']}; border:none;")
        self._risk_time = QLabel("")
        self._risk_time.setStyleSheet(f"color:{C['text3']}; font-size:10px; font-family:'JetBrains Mono',monospace; border:none;")
        right_v.addWidget(self._risk_status)
        right_v.addWidget(self._risk_time)
        risk_lay.addLayout(right_v)
        risk_lay.addStretch()

        self._provider_lbl = QLabel("")
        self._provider_lbl.setStyleSheet(f"color:{C['accent']}; font-size:10px; font-weight:600; font-family:'JetBrains Mono',monospace; border:none;")
        risk_lay.addWidget(self._provider_lbl)

        risk_container = QWidget()
        risk_vbox = QVBoxLayout(risk_container)
        risk_vbox.setContentsMargins(0, 0, 0, 0)
        risk_vbox.addWidget(QLabel("📊 Risk Skoru"))
        risk_vbox.addWidget(risk_frame)
        grid.addWidget(risk_container, 0, 0)

        # Şüpheli Bağlantılar (0, 1) - Sağ Üst
        self._susp_table = QTableWidget()
        self._susp_table.setColumnCount(4)
        self._susp_table.setHorizontalHeaderLabels(["IP", "Port", "Süreç", "Neden / Eylem"])
        self._susp_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._susp_table.setColumnWidth(0, 130); self._susp_table.setColumnWidth(1, 55); self._susp_table.setColumnWidth(2, 120)
        self._susp_table.verticalHeader().setVisible(False)
        self._susp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._susp_table.setMinimumHeight(120)
        self._susp_table.setStyleSheet(f"QTableWidget {{ background:{C['bg2']}; border:1px solid {C['border']}; border-radius:8px; }}")

        susp_container = QWidget()
        susp_vbox = QVBoxLayout(susp_container)
        susp_vbox.setContentsMargins(0, 0, 0, 0)
        susp_vbox.addWidget(QLabel("⚠️ Şüpheli Bağlantılar"))
        susp_vbox.addWidget(self._susp_table)
        grid.addWidget(susp_container, 0, 1)

        # AI Analiz Raporu (1, 0) - Sol Alt
        self._report_browser = QTextBrowser()
        self._report_browser.setOpenExternalLinks(False)
        self._report_browser.setStyleSheet(
            f"QTextBrowser {{ background:{C['bg2']}; border:1px solid {C['border']}; "
            f"border-radius:8px; color:{C['text']}; }}"
        )

        report_container = QWidget()
        report_vbox = QVBoxLayout(report_container)
        report_vbox.setContentsMargins(0, 0, 0, 0)
        report_vbox.addWidget(QLabel("📝 AI Analiz Raporu"))
        report_vbox.addWidget(self._report_browser)
        grid.addWidget(report_container, 1, 0)

        # Gönderilen Veri Önizlemesi (1, 1) - Sağ Alt
        self._preview_browser = QTextBrowser()
        self._preview_browser.setStyleSheet(
            f"QTextBrowser {{ background:#03050b; color:#c9d1d9; border:1px solid {C['border']}; "
            f"border-radius:8px; font-family:'JetBrains Mono',monospace; font-size:11px; }}"
        )

        preview_container = QWidget()
        preview_vbox = QVBoxLayout(preview_container)
        preview_vbox.setContentsMargins(0, 0, 0, 0)
        preview_vbox.addWidget(QLabel("📤 Gönderilen Veri"))
        preview_vbox.addWidget(self._preview_browser)
        grid.addWidget(preview_container, 1, 1)

        # Grid stretch - rapor ve veri büyüsün
        grid.setRowStretch(0, 1)  # Üst satır kompakt
        grid.setRowStretch(1, 3)  # Alt satır esnek
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        root.addLayout(grid, 1)

        # ── Rapor Geçmişi (En Alt) ────────────────────────────────────
        hist_lbl = QLabel("📜 Rapor Geçmişi")
        hist_lbl.setStyleSheet(f"color:{C['text2']}; font-size:12px; font-weight:600;")
        root.addWidget(hist_lbl)

        self._hist_table = QTableWidget()
        self._hist_table.setColumnCount(4)
        self._hist_table.setHorizontalHeaderLabels(["Tarih", "Sağlayıcı", "Risk", "Durum"])
        self._hist_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._hist_table.verticalHeader().setVisible(False)
        self._hist_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._hist_table.setColumnWidth(1, 100); self._hist_table.setColumnWidth(2, 50); self._hist_table.setColumnWidth(3, 150)
        self._hist_table.setMinimumHeight(100)
        self._hist_table.setStyleSheet(f"QTableWidget {{ background:{C['bg2']}; border:1px solid {C['border']}; border-radius:8px; }}")
        root.addWidget(self._hist_table)

    def _export(self, fmt):
        from exporter import export_report
        if not self._current_report:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak rapor yok.")
            return
        try:
            fp = export_report(self._current_report, fmt)
            QMessageBox.information(self, "Başarılı", f"Rapor kaydedildi:\n{fp}")
        except Exception as exc:
            QMessageBox.critical(self, "Hata", f"Dışa aktarma hatası:\n{exc}")

    def _display_report(self, r, provider=None):
        self._current_report = r
        score  = r.get("risk_score", 0)
        status = r.get("status", "")
        if provider is None:
            import config
            provider = config.AI_PROVIDER.upper()
        else:
            provider = provider.upper()

        if isinstance(score, (int, float)) and score >= 0:
            if score < 3:   color, score_txt = C["success"], f"{score:.1f}"
            elif score < 6: color, score_txt = C["warning"], f"{score:.1f}"
            elif score < 8: color, score_txt = C["danger"],  f"{score:.1f}"
            else:           color, score_txt = "#ff1744",    f"{score:.1f}"
        else:
            color, score_txt = C["danger"], "✕"

        self._risk_score.setStyleSheet(f"font-size:44px; font-weight:700; color:{color}; font-family:'JetBrains Mono',monospace; border:none;")
        self._risk_score.setText(score_txt)
        self._risk_status.setStyleSheet(f"font-size:16px; font-weight:700; color:{color}; border:none;")
        self._risk_status.setText(status or "Bilinmiyor")
        self._risk_time.setText(f"Son analiz: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        self._provider_lbl.setText(f"🤖 {provider}")

        meta = r.get("_meta", {})
        if meta:
            if meta.get("skipped"):
                self._preview_browser.setPlainText(f"[Atlandı] {meta.get('reason','')}")
            else:
                self._preview_browser.setPlainText(meta.get("raw_payload", ""))
            est = meta.get("est_tokens", 0)
            if est > 0:
                self._provider_lbl.setText(f"🤖 {provider}  (~{est} token)")

        conns   = r.get("suspicious_connections", []) or []
        summary = r.get("summary", "")

        rows_html = ""
        for i, conn in enumerate(conns, 1):
            if not isinstance(conn, dict):
                continue
            rows_html += f"""
            <tr>
              <td style="color:{C['warning']};font-weight:700;padding:7px 4px;">{i}.</td>
              <td style="padding:7px 10px;border-bottom:1px solid {C['border']};">
                <b style="color:{C['text']};font-family:'JetBrains Mono',monospace;">{conn.get('ip','')}:{conn.get('port','')}</b>
                &nbsp;<span style="color:{C['text3']};font-size:11px;">{conn.get('process','')}</span><br>
                <span style="color:{C['text2']};">{conn.get('reason','')}</span><br>
                <span style="color:{C['accent']};font-size:11px;">➡ {conn.get('action','')}</span>
              </td>
            </tr>"""

        conns_section = f"""
            <h3 style="color:{C['warning']};margin:14px 0 8px;">⚠ Şüpheli Bağlantılar ({len(conns)} adet)</h3>
            <table width="100%" cellspacing="0" cellpadding="0">{rows_html}</table>
        """ if conns else f'<p style="color:{C["success"]};margin:12px 0;">✓ Şüpheli bağlantı tespit edilmedi.</p>'

        badge_bg = ("#0a1f12" if score < 3 else "#1f140a" if score < 7 else "#1f0a0e")
        sum_lines = "".join(f'<p style="margin:3px 0;line-height:1.65;">{l}</p>' for l in (summary or "Sonuç mevcut değil.").split("\n") if l.strip())

        html = f"""<html><body style="background:{C['bg2']};color:{C['text']};
            font-family:'Segoe UI',sans-serif;font-size:13px;padding:12px;">
          <div style="background:{badge_bg};border-radius:8px;padding:10px 16px;margin-bottom:14px;
                      border-left:4px solid {color};">
            <span style="font-size:22px;font-weight:700;color:{color};font-family:'JetBrains Mono',monospace;">{score_txt}/10</span>
            &nbsp;&nbsp;
            <span style="font-size:15px;font-weight:700;color:{color};">{status}</span>
            &nbsp;&nbsp;
            <span style="font-size:11px;color:{C['text3']};">🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}
            &nbsp;|&nbsp; 🤖 {provider}</span>
          </div>
          <h3 style="color:{C['accent']};margin:0 0 6px;font-size:12px;letter-spacing:0.06em;">AI DEĞERLENDİRMESİ</h3>
          <div style="background:{C['bg3']};border-radius:6px;padding:10px 14px;
                      border-left:3px solid {color};">{sum_lines}</div>
          {conns_section}
        </body></html>"""
        self._report_browser.setHtml(html)

        self._susp_table.setRowCount(0)
        for conn in conns:
            if not isinstance(conn, dict): continue
            row = self._susp_table.rowCount()
            self._susp_table.insertRow(row)
            ra = f"{conn.get('reason','')} → {conn.get('action','')}"
            for col, val in enumerate([conn.get("ip",""), str(conn.get("port","")), conn.get("process",""), ra]):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(C["warning"]))
                self._susp_table.setItem(row, col, item)

    def _load_history(self):
        if self._loading:
            return
        self._loading = True
        self._history_worker = AnalysisTabWorker(self.db)
        self._history_worker.done.connect(self._on_history_loaded)
        self._history_worker.start()

    def _on_history_loaded(self, reports):
        self._loading = False
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
                self._current_report = parsed_content
                self._display_report(parsed_content, provider=latest.get("provider", ""))
            except Exception as e:
                print(f"[AnalysisTab] Rapor gösterilemedi: {e}")

    def refresh(self):
        self._load_history()


# ═══════════════════════════════════════════════════════════════════════
#  AYARLAR SEKMESİ
# ═══════════════════════════════════════════════════════════════════════
# (SettingsTab class continues below after MainWindow)


# ═══════════════════════════════════════════════════════════════════════
#  ANA PENCERE
# ═══════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self, db, analyzer, engine, scheduler):
        super().__init__()
        self.db        = db
        self.analyzer  = analyzer
        self.engine    = engine
        self.scheduler = scheduler
        self.setWindowTitle(f"NetSonar {get_app_version()} — AI Ağ İzleyici")
        self.setMinimumSize(1100, 680)
        self.resize(1280, 800)
        self.setStyleSheet(STYLESHEET)
        self._setup_ui()
        self._setup_tray()
        self._setup_timer()

    # ── UI ─────────────────────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())
        root.addWidget(self._build_tabs(), 1)
        root.addWidget(self._build_statusbar())

    # ── Topbar ─────────────────────────────────────────────────────────
    def _build_topbar(self):
        bar = QFrame()
        bar.setStyleSheet(
            f"QFrame {{ background:{C['bg1']}; border:none; "
            f"border-bottom:1px solid {C['border']}; }}"
        )
        bar.setFixedHeight(52)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 0, 16, 0)
        lay.setSpacing(12)

        logo = QLabel(f"🛡  NetSonar {get_app_version()}")
        logo.setStyleSheet(
            f"font-size:18px; font-weight:700; color:{C['accent']}; "
            f"font-family:'JetBrains Mono','Consolas',monospace; letter-spacing:0.04em;"
        )
        lay.addWidget(logo)

        self._analysis_progress = AnalysisProgressWidget()
        lay.addWidget(self._analysis_progress)
        lay.addStretch()

        for obj, label, slot in [
            ("primary", "⚡ Analizi Başlat", self._run_quick_analysis),
        ]:
            btn = QPushButton(label)
            btn.setFixedHeight(34)
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

    # ── Sekmeler ───────────────────────────────────────────────────────
    def _build_tabs(self):
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            f"QTabWidget::pane {{ border:none; background:{C['bg']}; }}"
            f"QTabBar {{ background:{C['bg1']}; }}"
            f"QTabBar::tab {{ background:{C['bg1']}; color:{C['text3']}; "
            f"padding:12px 24px; border:none; border-bottom:2px solid transparent; "
            f"font-weight:600; font-size:12px; letter-spacing:0.03em; }}"
            f"QTabBar::tab:selected {{ color:{C['accent']}; border-bottom:2px solid {C['accent']}; background:{C['bg']}; }}"
            f"QTabBar::tab:hover {{ color:{C['text2']}; }}"
        )

        # Sadece Dashboard hemen oluşturulur — diğerleri ilk açılışta lazy
        self._dashboard_tab = DashboardTab(self.db)
        self._dashboard_tab.request_block.connect(self._block_ip)
        self._analysis_tab  = None
        self._data_tab      = None
        self._blocked_tab    = None
        self._settings_tab  = None

        # Placeholder widget'lar — gerçek içerik ilk tıklamada yüklenir
        def _placeholder():
            w = QWidget()
            lay = QVBoxLayout(w)
            lbl = QLabel("Yükleniyor…")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{C['text3']}; font-size:13px;")
            lay.addWidget(lbl)
            return w

        self._tabs.addTab(self._dashboard_tab, "  Dashboard  ")
        self._tabs.addTab(_placeholder(),      "  AI Analiz  ")
        self._tabs.addTab(_placeholder(),      "  Veri  ")
        self._tabs.addTab(_placeholder(),      "  Engellenenler  ")
        self._tabs.addTab(_placeholder(),      "  Ayarlar  ")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        return self._tabs

    # ── Status bar ─────────────────────────────────────────────────────
    def _build_statusbar(self):
        bar = QFrame()
        bar.setStyleSheet(
            f"QFrame {{ background:{C['bg1']}; border:none; "
            f"border-top:1px solid {C['border']}; }}"
        )
        bar.setFixedHeight(26)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(16)

        def sb_item(text, color=None):
            lbl = QLabel(text)
            col = color or C["text3"]
            lbl.setStyleSheet(f"color:{col}; font-size:10px; font-family:'JetBrains Mono',monospace; border:none;")
            return lbl

        def divider():
            d = QFrame()
            d.setFixedSize(1, 14)
            d.setStyleSheet(f"background:{C['border']}; border:none;")
            return d

        lay.addWidget(sb_item("● Ağ Yakalama Aktif", C["success"]))
        lay.addWidget(divider())
        self._status_label = sb_item("● İzleme aktif", C["success"])
        lay.addWidget(self._status_label)
        lay.addWidget(divider())
        self._sb_iface = sb_item("Arayüz: —")
        lay.addWidget(self._sb_iface)
        lay.addWidget(divider())
        self._sb_ai = sb_item("AI: —")
        lay.addWidget(self._sb_ai)
        lay.addWidget(divider())
        self._sb_next = sb_item("Sonraki analiz: —")
        lay.addWidget(self._sb_next)
        lay.addWidget(divider())
        self._sb_db = sb_item("DB: —")
        lay.addWidget(self._sb_db)
        lay.addStretch()
        self._sb_time = sb_item(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        lay.addWidget(self._sb_time)
        return bar

    # ── Olaylar ────────────────────────────────────────────────────────
    def _on_tab_changed(self, idx):
        """İlk açılışta sekme widget'larını oluştur (lazy), sonra refresh et."""
        if idx == 0:
            self._dashboard_tab.refresh()

        elif idx == 1:
            if self._analysis_tab is None:
                self._analysis_tab = AnalysisTab(self.db, self.analyzer)
                self._tabs.removeTab(1)
                self._tabs.insertTab(1, self._analysis_tab, "  AI Analiz  ")
                self._tabs.setCurrentIndex(1)
            self._analysis_tab.refresh()

        elif idx == 2:
            if self._data_tab is None:
                self._data_tab = DataTab(self.db)
                self._tabs.removeTab(2)
                self._tabs.insertTab(2, self._data_tab, "  Veri  ")
                self._tabs.setCurrentIndex(2)
            self._data_tab.refresh()

        elif idx == 3:
            if self._blocked_tab is None:
                self._blocked_tab = BlockedTab(self.db)
                self._tabs.removeTab(3)
                self._tabs.insertTab(3, self._blocked_tab, "  Engellenenler  ")
                self._tabs.setCurrentIndex(3)
            self._blocked_tab.refresh()

        elif idx == 4:
            if self._settings_tab is None:
                self._settings_tab = SettingsTab()
                self._tabs.removeTab(4)
                self._tabs.insertTab(4, self._settings_tab, "  Ayarlar  ")
                self._tabs.setCurrentIndex(4)
            self._settings_tab.refresh()


    def _refresh_all(self):
        """Stats'ı arka planda çek, UI'ı bloklamadan güncelle."""
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
            print(f"Stats update error: {e}")

    def _run_quick_analysis(self):
        self._status_label.setText("● Analiz çalışıyor…")
        self._status_label.setStyleSheet(
            f"color:{C['warning']}; font-size:10px; font-family:'JetBrains Mono',monospace; border:none;"
        )

        def done(result):
            self._analysis_progress.reset()
            self._refresh_all()
            
            risk_score = result.get("risk_score", 0)
            status = result.get("status", "")
            
            if risk_score == -1:
                self._status_label.setText("● Hata oluştu")
                self._status_label.setStyleSheet(
                    f"color:{C['danger']}; font-size:10px; font-family:'JetBrains Mono',monospace; border:none;"
                )
                error_msg = result.get("summary", "Bilinmeyen hata")
                QMessageBox.warning(
                    self, "Analiz Hatası",
                    f"Analiz sırasında hata oluştu:\n\n{error_msg}\n\n"
                    "Lütfen Ayarlar'dan API anahtarınızı kontrol edin."
                )
            else:
                self._status_label.setText("● Analiz tamamlandı")
                self._status_label.setStyleSheet(
                    f"color:{C['success']}; font-size:10px; font-family:'JetBrains Mono',monospace; border:none;"
                )
            
            QTimer.singleShot(5000, lambda: self._status_label.setText("● İzleme aktif"))

        self._worker = AnalysisWorker(self.analyzer)
        self._worker.stage.connect(self._analysis_progress.set_stage)
        self._worker.finished.connect(done)
        self._worker.start()


    def _block_ip(self, ip):
        reply = QMessageBox.question(
            self, "IP Engelle",
            f"<b>{ip}</b> adresini engellemek istiyor musunuz?",
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
            QMessageBox.critical(self, "Hata", f"{ip} engellenemedi.\nYönetici yetkisi gerekli.")

    # ── System Tray ────────────────────────────────────────────────────
    def _setup_tray(self):
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(C["accent"])))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        p.end()
        self.tray = QSystemTrayIcon(QIcon(pix), self)
        menu = QMenu()
        show_a = QAction("NetSonar'yı Göster", self); show_a.triggered.connect(self.showNormal); menu.addAction(show_a)
        ana_a  = QAction("⚡ Analizi Başlat",  self); ana_a.triggered.connect(self._run_quick_analysis); menu.addAction(ana_a)
        menu.addSeparator()
        quit_a = QAction("❌ Çıkış", self); quit_a.triggered.connect(self._quit); menu.addAction(quit_a)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("NetSonar — Ağ Koruması Aktif")
        self.tray.activated.connect(lambda r: self.showNormal() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def _setup_timer(self):
        # İlk refresh pencere açıldıktan 1.5 saniye sonra başlasın
        QTimer.singleShot(1500, self._refresh_all)
        # Periyodik refresh: 90 saniyede bir
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_all)
        self._timer.start(90_000)
        # Saat: sadece pencere görünürken güncelle
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick_clock)
        self._clock.start(1000)

    def _tick_clock(self):
        if self.isVisible():
            self._sb_time.setText(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))

    def _init_statusbar_config(self):
        """Statusbar'daki AI bilgisini başlangıçta bir kez yükle."""
        try:
            import config as cfg
            self._sb_ai.setText(
                f"AI: {cfg.AI_PROVIDER.upper()} · "
                f"{cfg.GEMINI_MODEL if cfg.AI_PROVIDER == 'gemini' else cfg.OPENROUTER_MODEL.split('/')[-1]}"
            )
        except Exception:
            pass

    def closeEvent(self, event):
        from config import load_settings
        if load_settings().get("MINIMIZE_TO_TRAY", True):
            event.ignore()
            self.hide()
            self.tray.showMessage("NetSonar Arka Planda", "İzleme devam ediyor.", QSystemTrayIcon.MessageIcon.Information, 2000)
        else:
            self._quit()

    def _quit(self):
        self.engine.stop()
        self.scheduler.stop()
        self.tray.hide()
        QApplication.quit()


# ═══════════════════════════════════════════════════════════════════════
#  VERİ TAB (AnalysisDataTab - Sekme Olarak)
# ═══════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════
#  DATA TAB (Veri Sekmesi)
# ═══════════════════════════════════════════════════════════════════════

class DataTabWorker(QThread):
    done = pyqtSignal(list, str)

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        last_ts = self.db.get_last_analysis_time()
        if last_ts is None:
            rows = self.db.get_summary(hours=1, limit=500)
            since_label = "Son 1 saat (henüz analiz yapılmadı)"
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

        # ── Başlık + İstatistik ───────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("📊 Analize Hazır Veri")
        title.setObjectName("title")
        hdr.addWidget(title)
        
        self._stats_lbl = QLabel("Veriler yükleniyor...")
        self._stats_lbl.setStyleSheet(f"color:{C['text3']}; font-size:12px;")
        hdr.addWidget(self._stats_lbl)
        hdr.addStretch()
        root.addLayout(hdr)

        # ── Sol: Tablo, Sağ: Detay ───────────────────────────────
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
        self._search.setPlaceholderText("⌕  IP veya süreç ara…")
        self._search.setFixedHeight(32)
        self._search.textChanged.connect(self._filter_debounce)
        filter_row.addWidget(self._search, 2)

        self._proto_combo = QComboBox()
        self._proto_combo.addItems(["Tümü", "TCP", "UDP", "OTHER"])
        self._proto_combo.setFixedHeight(32)
        self._proto_combo.currentTextChanged.connect(lambda _: self._filter())
        filter_row.addWidget(self._proto_combo)

        self._page_size_combo = QComboBox()
        self._page_size_combo.addItems(["50", "100", "250"])
        self._page_size_combo.setCurrentIndex(0)
        self._page_size_combo.setFixedHeight(32)
        self._page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        lbl = QLabel("Göster:")
        lbl.setStyleSheet(f"color:{C['text3']}; font-size:11px;")
        filter_row.addWidget(lbl)
        filter_row.addWidget(self._page_size_combo)
        vl.addLayout(filter_row)

        # Hızlı Filtreler
        quick_row = QHBoxLayout()
        quick_row.setSpacing(6)

        self._filter_suspicious = QCheckBox("🔴 Şüpheli Port")
        self._filter_suspicious.stateChanged.connect(lambda _: self._filter())
        quick_row.addWidget(self._filter_suspicious)

        self._filter_high_traffic = QCheckBox("📊 >1MB Trafik")
        self._filter_high_traffic.stateChanged.connect(lambda _: self._filter())
        quick_row.addWidget(self._filter_high_traffic)

        self._filter_after_hours = QCheckBox("🌙 Mesai Dışı")
        self._filter_after_hours.stateChanged.connect(lambda _: self._filter())
        quick_row.addWidget(self._filter_after_hours)

        quick_row.addStretch()
        vl.addLayout(quick_row)

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["DURUM", "BAĞ", "HEDEF IP", "PORT", "PROTO", "VERİ", "SÜREÇ", ""])
        self.table.verticalHeader().setVisible(False)
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
        self._prev_btn = QPushButton("◀ Önceki")
        self._prev_btn.setObjectName("ghost")
        self._prev_btn.clicked.connect(lambda: self._change_page(-1))
        self._page_lbl = QLabel("Sayfa 1")
        self._page_lbl.setStyleSheet(f"color:{C['text3']}; font-family:'JetBrains Mono',monospace; font-size:11px;")
        self._next_btn = QPushButton("Sonraki ▶")
        self._next_btn.setObjectName("ghost")
        self._next_btn.clicked.connect(lambda: self._change_page(1))
        page_row.addWidget(self._prev_btn)
        page_row.addWidget(self._page_lbl)
        page_row.addWidget(self._next_btn)
        page_row.addStretch()
        vl.addLayout(page_row)

        splitter.addWidget(left)

        # Sağ Panel: Detay
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

        lbl = QLabel("📋 Bağlantı Detayı")
        lbl.setStyleSheet(f"color:{C['accent']}; font-weight:700; font-size:12px; border:none;")
        vl.addWidget(lbl)

        self._detail_content = QWidget()
        dv = QVBoxLayout(self._detail_content)
        dv.setSpacing(4)
        dv.setContentsMargins(0, 8, 0, 8)

        self._detail_ip = QLabel("IP: —")
        self._detail_port = QLabel("Port: —")
        self._detail_proto = QLabel("Protokol: —")
        self._detail_bytes = QLabel("Toplam Veri: —")
        self._detail_process = QLabel("Süreç: —")
        self._detail_time = QLabel("Son Görülme: —")

        for lbl in [self._detail_ip, self._detail_port, self._detail_proto, 
                     self._detail_bytes, self._detail_process, self._detail_time]:
            lbl.setStyleSheet(f"color:{C['text2']}; font-size:11px; border:none;")
            dv.addWidget(lbl)

        vl.addWidget(self._detail_content)

        self._detail_risk = QWidget()
        rv = QVBoxLayout(self._detail_risk)
        rv.setSpacing(2)
        rv.setContentsMargins(0, 8, 0, 0)

        rl = QLabel("🔴 Risk Göstergeleri")
        rl.setStyleSheet(f"color:{C['danger']}; font-weight:700; font-size:11px; border:none;")
        rv.addWidget(rl)

        self._risk_list = QLabel("Bağlantı seçin")
        self._risk_list.setStyleSheet(f"color:{C['text3']}; font-size:10px; border:none;")
        rv.addWidget(self._risk_list)

        vl.addWidget(self._detail_risk)
        vl.addStretch()

        self._block_detail_btn = QPushButton("🚫 Engelle")
        self._block_detail_btn.setFixedHeight(36)
        self._block_detail_btn.setObjectName("danger")
        self._block_detail_btn.clicked.connect(self._block_selected)
        self._block_detail_btn.setEnabled(False)
        vl.addWidget(self._block_detail_btn)

        return panel

    def refresh(self):
        if self._loading:
            return
        self._loading = True
        self._stats_lbl.setText("Veriler yükleniyor...")
        self._worker = DataTabWorker(self.db)
        self._worker.done.connect(self._on_data_loaded)
        self._worker.start()

    def _on_data_loaded(self, rows, since_label):
        self._loading = False
        total_bytes = sum(r.get('total_bytes', 0) for r in rows)
        self._stats_lbl.setText(f"{len(rows)} bağlantı, {_fmt(total_bytes)} veri — {since_label}")
        self._all_rows = rows
        self._page = 0
        self._populate_table(rows)
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

            status_icon = "🔴" if is_suspicious else ("⚠️" if is_high_traffic else "✅")
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

            block_btn = QPushButton("🚫 Engelle")
            block_btn.setFixedHeight(28)
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
        self._detail_process.setText(f"Süreç: {process}")
        
        try:
            from config import SUSPICIOUS_PORTS
            is_suspicious_port = int(port) in SUSPICIOUS_PORTS
        except:
            is_suspicious_port = False
        
        risk_items = []
        if is_suspicious_port:
            risk_items.append("⚠️ Bilinen tehlikeli port")
        if "powershell" in process.lower() or "cmd" in process.lower() or "wscript" in process.lower():
            risk_items.append("⚠️ Sistem süreci dış bağlantı")
        
        if risk_items:
            self._risk_list.setText("\n".join(risk_items))
        else:
            self._risk_list.setText("Belirgin risk tespit edilmedi")
        
        self._block_detail_btn.setEnabled(True)
        self._selected_ip = ip

    def _block_ip(self, ip):
        reply = QMessageBox.question(
            self, "IP Engelle",
            f"<b>{ip}</b> adresini engellemek istiyor musunuz?",
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
            if proto != "Tümü" and row.get('protocol', '') != proto:
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


# ═══════════════════════════════════════════════════════════════════════
#  BLOCKED TAB (Engellenenler Sekmesi)
# ═══════════════════════════════════════════════════════════════════════

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
        title = QLabel("🚫 Engellenen IP Adresleri")
        title.setObjectName("title")
        hdr.addWidget(title)
        
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet(f"color:{C['text3']}; font-size:12px;")
        hdr.addWidget(self._stats_lbl)
        hdr.addStretch()
        root.addLayout(hdr)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["IP ADRESİ", "SEBEP", "TARİH", "EYLEM"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table, 1)

        page_row = QHBoxLayout()
        page_row.addStretch()
        self._prev_btn = QPushButton("◀ Önceki")
        self._prev_btn.setObjectName("ghost")
        self._prev_btn.clicked.connect(lambda: self._change_page(-1))
        self._page_lbl = QLabel("Sayfa 1")
        self._page_lbl.setStyleSheet(f"color:{C['text3']}; font-family:'JetBrains Mono',monospace; font-size:11px;")
        self._next_btn = QPushButton("Sonraki ▶")
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
        
        self._stats_lbl.setText(f"Toplam: {total} | Bugün: {today}")
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

            unblock_btn = QPushButton("Kaldır")
            unblock_btn.setFixedSize(70, 28)
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
            self, "Engel Kaldır",
            f"<b>{ip}</b> IP'sinin engelini kaldırmak istiyor musunuz?",
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


# ═══════════════════════════════════════════════════════════════════════
#  SETTINGS TAB (Ayarlar Sekmesi)
# ═══════════════════════════════════════════════════════════════════════

class OpenRouterCache:
    """OpenRouter model listesi önbellekleme (1 saat TTL)"""
    CACHE_FILE = "config/model_cache.json"
    TTL_SECONDS = 3600

    @staticmethod
    def get_models():
        if not os.path.exists(OpenRouterCache.CACHE_FILE):
            return None
        try:
            with open(OpenRouterCache.CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            cached_time = data.get("timestamp", 0)
            if time.time() - cached_time > OpenRouterCache.TTL_SECONDS:
                return None
            return data.get("models", [])
        except:
            return None

    @staticmethod
    def set_models(models):
        os.makedirs(os.path.dirname(OpenRouterCache.CACHE_FILE), exist_ok=True)
        with open(OpenRouterCache.CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": time.time(), "models": models}, f, indent=2)


def parse_openrouter_models(api_response):
    models = []
    for m in api_response.get("data", []):
        model_id = m.get("id", "")
        if not model_id:
            continue
        context_length = m.get("context_length", 0) or 0
        pricing = m.get("pricing", {})
        price_input = float(pricing.get("prompt", 0) or 0)
        price_output = float(pricing.get("completion", 0) or 0)
        total_price = (price_input + price_output) / 2
        is_free = total_price == 0
        short_name = model_id.split("/")[-1] if "/" in model_id else model_id
        if ":free" in short_name.lower():
            short_name = short_name.rsplit(":free", 1)[0]
        models.append({
            "id": model_id,
            "short_name": short_name,
            "context_length": context_length,
            "price_input": price_input,
            "price_output": price_output,
            "total_price": total_price,
            "is_free": is_free,
            "is_recommended": False,
        })
    return models


def get_recommended_model(models):
    free_models = [m for m in models if m["is_free"]]
    if not free_models:
        return None
    free_models.sort(key=lambda x: (-x["context_length"], "-" in x["short_name"]), reverse=True)
    return free_models[0]["id"] if free_models else None


class SettingsTab(QWidget):
    GEMINI_MODELS = [
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]

    DEFAULT_OPENROUTER_MODELS = [
        {"id": "meta-llama/llama-3.3-70b-instruct:free", "short_name": "llama-3.3-70b", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "google/gemma-3-4b-it:free", "short_name": "gemma-3-4b", "context_length": 32000, "is_free": True, "total_price": 0},
        {"id": "qwen/qwen-2.5-72b-instruct:free", "short_name": "qwen-2.5-72b", "context_length": 32000, "is_free": True, "total_price": 0},
        {"id": "mistral/mistral-small-24b-instruct:free", "short_name": "mistral-small-24b", "context_length": 32000, "is_free": True, "total_price": 0},
    ]

    OLLAMA_MODELS = [
        {"id": "minimax-m2.7", "short_name": "minimax-m2.7", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "minimax-m2.5", "short_name": "minimax-m2.5", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "minimax-m2.1", "short_name": "minimax-m2.1", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "minimax-m2", "short_name": "minimax-m2", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "qwen3.5", "short_name": "qwen3.5", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "qwen3-coder-next", "short_name": "qwen3-coder-next", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "qwen3-vl", "short_name": "qwen3-vl", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "qwen3-next", "short_name": "qwen3-next", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "devstral-small-2:24b", "short_name": "devstral-small-2", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "devstral-2:123b", "short_name": "devstral-2", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "nemotron-3-super", "short_name": "nemotron-3-super", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "nemotron-3-nano:30b", "short_name": "nemotron-3-nano", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "ministral-3:8b", "short_name": "ministral-3-8b", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "ministral-3:14b", "short_name": "ministral-3-14b", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "ministral-3:3b", "short_name": "ministral-3-3b", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "glm-5", "short_name": "glm-5", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "glm-4.7", "short_name": "glm-4.7", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "glm-4.6", "short_name": "glm-4.6", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "kimi-k2.5", "short_name": "kimi-k2.5", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "kimi-k2:1t", "short_name": "kimi-k2-1t", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "rnj-1:8b", "short_name": "rnj-1-8b", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "deepseek-v3.2", "short_name": "deepseek-v3.2", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "deepseek-v3.1:671b", "short_name": "deepseek-v3.1-671b", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "cogito-2.1:671b", "short_name": "cogito-2.1-671b", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "gemini-3-flash-preview", "short_name": "gemini-3-flash-preview", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "mistral-large-3:675b", "short_name": "mistral-large-3", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "gpt-oss:120b", "short_name": "gpt-oss-120b", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "gpt-oss:20b", "short_name": "gpt-oss-20b", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "gemma3:27b", "short_name": "gemma3-27b", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "gemma3:12b", "short_name": "gemma3-12b", "context_length": 128000, "is_free": True, "total_price": 0},
        {"id": "gemma3:4b", "short_name": "gemma3-4b", "context_length": 128000, "is_free": True, "total_price": 0},
    ]

    def __init__(self):
        super().__init__()
        self._all_models = []
        self._selected_model = None
        self._gemini_api_key = ""
        self._openrouter_api_key = ""
        self._ollama_api_key = ""
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

        # AI Ayarları
        ai_gb = QGroupBox("📋 AI Ayarları")
        ai_fl = QFormLayout(ai_gb)

        self._prov = QComboBox()
        self._prov.addItems(["openrouter", "gemini", "ollama"])
        self._prov.currentTextChanged.connect(self._on_provider_changed)
        ai_fl.addRow("AI Sağlayıcı:", self._prov)

        api_key_row = QHBoxLayout()
        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("API Key…")
        self._api_key.textChanged.connect(self._on_api_key_changed)
        api_key_row.addWidget(self._api_key)
        self._api_key_eye = QPushButton("👁")
        self._api_key_eye.setFixedWidth(32)
        self._api_key_eye.setObjectName("ghost")
        self._api_key_eye.clicked.connect(lambda: self._toggle_api_key())
        api_key_row.addWidget(self._api_key_eye)
        ai_fl.addRow("API Key:", api_key_row)

        cv.addWidget(ai_gb)

        # Model Seçimi Paneli
        model_gb = QGroupBox("🤖 Model Seçimi")
        model_vl = QVBoxLayout(model_gb)

        search_row = QHBoxLayout()
        self._model_search = QLineEdit()
        self._model_search.setPlaceholderText("🔍 Model ara...")
        self._model_search.textChanged.connect(self._on_model_search_changed)
        search_row.addWidget(self._model_search, 1)
        self._refresh_btn = QPushButton("↻")
        self._refresh_btn.setFixedWidth(40)
        self._refresh_btn.setObjectName("ghost")
        self._refresh_btn.clicked.connect(self._on_refresh_models)
        search_row.addWidget(self._refresh_btn)
        model_vl.addLayout(search_row)

        filter_row = QHBoxLayout()
        self._filter_all = QRadioButton("Tümü")
        self._filter_all.setChecked(True)
        self._filter_free = QRadioButton("Ücretsiz")
        self._filter_paid = QRadioButton("Ücretli")
        self._filter_all.toggled.connect(self._on_filter_changed)
        self._filter_free.toggled.connect(self._on_filter_changed)
        self._filter_paid.toggled.connect(self._on_filter_changed)
        filter_row.addWidget(self._filter_all)
        filter_row.addWidget(self._filter_free)
        filter_row.addWidget(self._filter_paid)
        filter_row.addStretch()
        model_vl.addLayout(filter_row)

        self._model_list = QListWidget()
        self._model_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._model_list.setMinimumHeight(280)
        self._model_list.setMaximumHeight(350)
        self._model_list.itemClicked.connect(self._on_model_item_clicked)
        self._model_list.itemDoubleClicked.connect(self._on_model_item_double_clicked)
        model_vl.addWidget(self._model_list)

        self._model_status = QLabel("")
        self._model_status.setStyleSheet(f"color:{C['text3']}; font-size:11px;")
        model_vl.addWidget(self._model_status)

        self._credits_lbl = QLabel("")
        self._credits_lbl.setStyleSheet(f"color:{C['accent']}; font-size:11px;")
        model_vl.addWidget(self._credits_lbl)

        cv.addWidget(model_gb)

        # Analiz Zamanlama
        timing_gb = QGroupBox("📅 Analiz Zamanlama")
        timing_fl = QFormLayout(timing_gb)

        self._auto_analysis_cb = QCheckBox("Açık")
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

        # Güvenlik
        sec_gb = QGroupBox("🛡 Güvenlik")
        sec_fl = QFormLayout(sec_gb)

        self._auto_block_cb = QCheckBox("Otomatik IP engelleme")
        sec_fl.addRow("", self._auto_block_cb)

        self._min_risk_combo = QComboBox()
        self._min_risk_combo.addItems(["5.0", "6.0", "7.0", "8.0", "9.0"])
        self._min_risk_combo.setCurrentIndex(2)
        sec_fl.addRow("Min Risk Skoru:", self._min_risk_combo)

        cv.addWidget(sec_gb)

        # Sistem
        sys_gb = QGroupBox("🚀 Sistem")
        sys_fl = QFormLayout(sys_gb)

        self._autostart_cb = QCheckBox("Windows'ta otomatik başlat")
        sys_fl.addRow("", self._autostart_cb)

        self._tray_cb = QCheckBox("Kapatılınca tepsiye küçült")
        self._tray_cb.setChecked(True)
        sys_fl.addRow("", self._tray_cb)

        cv.addWidget(sys_gb)

        # Prompt
        prompt_gb = QGroupBox("🤖 AI Prompt")
        prompt_vl = QVBoxLayout(prompt_gb)

        desc = QLabel("AI'nin trafik analizinde kullandığı talimatlar.")
        desc.setStyleSheet(f"color:{C['text3']}; font-size:11px;")
        desc.setWordWrap(True)
        prompt_vl.addWidget(desc)

        self._prompt = QTextEdit()
        self._prompt.setMinimumHeight(200)
        prompt_vl.addWidget(self._prompt)

        pbr = QHBoxLayout()
        pbr.addStretch()
        reset_btn = QPushButton("Varsayılana Sıfırla")
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
        save_btn.setFixedSize(120, 40)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

    def _toggle_api_key(self):
        if self._api_key.echoMode() == QLineEdit.EchoMode.Password:
            self._api_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self._api_key_eye.setText("🔒")
        else:
            self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
            self._api_key_eye.setText("👁")

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

        prov = s.get("AI_PROVIDER", "gemini")
        idx = self._prov.findText(prov)
        if idx >= 0:
            self._prov.setCurrentIndex(idx)

        self._gemini_api_key = s.get("GEMINI_API_KEY", "")
        self._openrouter_api_key = s.get("OPENROUTER_API_KEY", "")
        self._ollama_api_key = s.get("OLLAMA_API_KEY", "")

        if prov == "openrouter":
            self._api_key.setText(self._openrouter_api_key)
        elif prov == "ollama":
            self._api_key.setText(self._ollama_api_key)
        else:
            self._api_key.setText(self._gemini_api_key)

        self._on_provider_changed(prov)

        try:
            self._prompt.setText(get_ai_prompt())
        except:
            self._prompt.setText(DEFAULT_SYSTEM_PROMPT)

    def refresh(self):
        self._load_settings()

    def _on_provider_changed(self, provider):
        self._model_search.clear()
        if provider == "gemini":
            self._api_key.setText(self._gemini_api_key)
            self._load_gemini_models()
            self._credits_lbl.setText("💰 Google Gemini: Günlük 1500 istek, dakikada 15 istek")
            self._model_status.setText("")
        elif provider == "ollama":
            self._api_key.setText(self._ollama_api_key)
            self._load_ollama_models()
            self._credits_lbl.setText("💰 Ollama Cloud: Ücretsiz cloud modelleri")
            self._model_status.setText("")
        else:
            self._api_key.setText(self._openrouter_api_key)
            api_key = self._openrouter_api_key.strip()
            if api_key:
                self._load_openrouter_models(api_key)
            else:
                self._show_default_models()
            self._credits_lbl.setText("")

    def _on_api_key_changed(self, text):
        provider = self._prov.currentText()
        if provider == "gemini":
            self._gemini_api_key = text
        elif provider == "ollama":
            self._ollama_api_key = text
        else:
            self._openrouter_api_key = text
            if text.strip():
                self._load_openrouter_models(text.strip())
            else:
                self._show_default_models()
                self._credits_lbl.setText("")

    def _on_refresh_models(self):
        provider = self._prov.currentText()
        if provider == "openrouter":
            api_key = self._api_key.text().strip()
            if api_key:
                self._load_openrouter_models(api_key, force_refresh=True)
        elif provider == "ollama":
            self._load_ollama_models()

    def _load_gemini_models(self):
        gemini_info = [
            {"id": "gemini-2.0-flash-lite", "short_name": "gemini-2.0-flash-lite", "context_length": 64000, "is_free": True, "total_price": 0},
            {"id": "gemini-2.0-flash", "short_name": "gemini-2.0-flash", "context_length": 64000, "is_free": True, "total_price": 0},
            {"id": "gemini-1.5-flash", "short_name": "gemini-1.5-flash", "context_length": 128000, "is_free": True, "total_price": 0},
            {"id": "gemini-1.5-pro", "short_name": "gemini-1.5-pro", "context_length": 128000, "is_free": False, "total_price": 0.000125},
        ]
        self._all_models = gemini_info
        self._selected_model = None
        self._populate_model_list()

    def _load_ollama_models(self):
        self._all_models = self.OLLAMA_MODELS.copy()
        self._selected_model = None
        self._populate_model_list()
        self._model_status.setText("✓ Ollama Cloud modelleri yüklendi")

    def _show_default_models(self):
        self._all_models = self.DEFAULT_OPENROUTER_MODELS.copy()
        self._selected_model = None
        self._populate_model_list()
        self._model_status.setText("⚠️ API key girmeden model bilgileri sınırlı")

    def _load_openrouter_models(self, api_key, force_refresh=False):
        cached = None if force_refresh else OpenRouterCache.get_models()
        if cached:
            self._all_models = cached
            self._selected_model = None
            self._populate_model_list()
            self._model_status.setText(f"✓ {len(cached)} model önbellekten yüklendi")
            self._fetch_credits(api_key)
            return

        self._model_status.setText("⏳ Modeller yükleniyor...")
        threading.Thread(target=self._fetch_models_thread, args=(api_key,), daemon=True).start()

    def _fetch_models_thread(self, api_key):
        try:
            import requests
            resp = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=20
            )
            if resp.status_code == 200:
                data = resp.json()
                models = parse_openrouter_models(data)
                OpenRouterCache.set_models(models)
                recommended = get_recommended_model(models)
                if recommended:
                    for m in models:
                        m["is_recommended"] = m["id"] == recommended
                self._all_models = models
                self._selected_model = None
                QMetaObject.invokeMethod(self._model_list, "clear", Qt.ConnectionType.QueuedConnection)
                QMetaObject.invokeMethod(self, "_populate_model_list_safe", Qt.ConnectionType.QueuedConnection)
                QMetaObject.invokeMethod(self._model_status, "setText", Qt.ConnectionType.QueuedConnection, Q_ARG("QString", f"✓ {len(models)} model yüklendi"))
                self._fetch_credits(api_key)
            else:
                QMetaObject.invokeMethod(self._model_status, "setText", Qt.ConnectionType.QueuedConnection, Q_ARG("QString", f"❌ HTTP {resp.status_code}"))
                QMetaObject.invokeMethod(self, "_show_default_models_safe", Qt.ConnectionType.QueuedConnection)
        except Exception as e:
            QMetaObject.invokeMethod(self._model_status, "setText", Qt.ConnectionType.QueuedConnection, Q_ARG("QString", f"❌ Bağlantı hatası"))
            QMetaObject.invokeMethod(self, "_show_default_models_safe", Qt.ConnectionType.QueuedConnection)

    def _fetch_credits(self, api_key):
        def do_fetch():
            try:
                import requests
                resp = requests.get(
                    "https://openrouter.ai/api/v1/credits",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    usage = data.get("data", {}).get("total_usage", 0)
                    limit = data.get("data", {}).get("limit", 0)
                    if usage > 0:
                        usage_str = f"Kullanım: {usage:,.0f} token"
                        if limit > 0:
                            usage_str += f" / {limit:,.0f}"
                        QMetaObject.invokeMethod(self._credits_lbl, "setText", Qt.ConnectionType.QueuedConnection, Q_ARG("QString", f"💰 {usage_str}"))
            except:
                pass
        threading.Thread(target=do_fetch, daemon=True).start()

    @pyqtSlot()
    def _populate_model_list_safe(self):
        self._populate_model_list()

    @pyqtSlot()
    def _show_default_models_safe(self):
        self._show_default_models()

    def _populate_model_list(self):
        self._model_list.clear()
        filter_type = "free" if self._filter_free.isChecked() else ("paid" if self._filter_paid.isChecked() else "all")
        search_text = self._model_search.text().lower()
        recommended_id = get_recommended_model(self._all_models) if self._all_models else None

        for model in self._all_models:
            model_id = model["id"]
            short_name = model["short_name"]

            if search_text and search_text not in model_id.lower() and search_text not in short_name.lower():
                continue
            if filter_type == "free" and not model["is_free"]:
                continue
            if filter_type == "paid" and model["is_free"]:
                continue

            context = model["context_length"]
            ctx_str = f"{context // 1000}K" if context >= 1000 else (str(context) if context else "?")
            price_str = "🆓 Ücretsiz" if model["is_free"] else f"💰 ${model['total_price']:.4f}/M"

            badges = ""
            if model_id == recommended_id:
                badges += " ⭐"
            if model["is_free"]:
                badges += " 🆓"

            display = f"{short_name}{badges}   |   {ctx_str} ctx   |   {price_str}"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, model_id)
            item.setToolTip(model_id)
            self._model_list.addItem(item)

        if recommended_id:
            for i in range(self._model_list.count()):
                item = self._model_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == recommended_id:
                    self._model_list.setCurrentRow(i)
                    break
        elif self._model_list.count() > 0:
            self._model_list.setCurrentRow(0)

    def _on_model_search_changed(self, text):
        QTimer.singleShot(300, self._populate_model_list)

    def _on_filter_changed(self):
        self._populate_model_list()

    def _on_model_item_clicked(self, item):
        self._selected_model = item.data(Qt.ItemDataRole.UserRole)

    def _on_model_item_double_clicked(self, item):
        pass

    def _reset_prompt(self):
        from config import DEFAULT_SYSTEM_PROMPT
        self._prompt.setText(DEFAULT_SYSTEM_PROMPT)

    def _save(self):
        try:
            from config import save_settings, save_ai_prompt, load_settings
            import importlib

            prov = self._prov.currentText()
            api_key = self._api_key.text().strip()
            model = self._selected_model or ""

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

            if prov == "gemini":
                s["GEMINI_API_KEY"] = api_key
                s["GEMINI_MODEL"] = model
            elif prov == "ollama":
                s["OLLAMA_API_KEY"] = api_key
                s["OLLAMA_MODEL"] = model
            else:
                s["OPENROUTER_API_KEY"] = api_key
                s["OPENROUTER_MODEL"] = model

            save_settings(s)

            import config
            importlib.reload(config)

            p = self._prompt.toPlainText()
            if p.strip():
                save_ai_prompt(p)

            QMessageBox.information(self, "✓ Başarılı", "Ayarlar kaydedildi.\nDeğişiklikler bir sonraki analizde geçerli olur.")

        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Ayarlar kaydedilirken hata:\n{e}")


# ═══════════════════════════════════════════════════════════════════════
#  POPUP DİALOGLAR
# ═══════════════════════════════════════════════════════════════════════

def _dialog_base(parent, title, w=960, h=660):
    """Temel QDialog oluşturucu."""
    d = QDialog(parent)
    d.setWindowTitle(title)
    d.setMinimumSize(w, h)
    d.setStyleSheet(STYLESHEET)
    return d


class ConnectionsPopup(QDialog):
    def __init__(self, db, parent=None, filter_type="recent"):
        super().__init__(parent)
        self.db = db
        self.filter_type = filter_type
        titles = {"recent": "Tüm Bağlantılar", "frequent": "En Sık Bağlanılan",
                  "transfer": "En Fazla Veri Transferi", "ports": "Port Çeşitliliği"}
        self.setWindowTitle(f"📡 {titles.get(filter_type,'Bağlantılar')}")
        self.setMinimumSize(960, 660)
        self.setStyleSheet(STYLESHEET)
        self._page = 0; self._page_size = 50
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        hdr = QHBoxLayout()
        title = QLabel(self.windowTitle())
        title.setObjectName("title")
        hdr.addWidget(title); hdr.addStretch()
        lay.addLayout(hdr)

        filter_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("⌕  IP, port, süreç ara…")
        self._search.setFixedHeight(32)
        self._search.textChanged.connect(self._filter)
        self._proto = QComboBox()
        self._proto.addItems(["Tümü","TCP","UDP","OTHER"])
        self._proto.setFixedHeight(32)
        self._proto.currentTextChanged.connect(self._filter)
        lbl = QLabel("Protokol:"); lbl.setStyleSheet(f"color:{C['text3']};")
        filter_row.addWidget(self._search, 2); filter_row.addWidget(lbl); filter_row.addWidget(self._proto); filter_row.addStretch()
        lay.addLayout(filter_row)

        self._table = QTableWidget()
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels(["ZAMAN","KAYNAK IP","HEDEF IP","PORT","PROTOKOL","VERİ (KB)","SÜREÇ","EYLEM"])
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self._table, 1)

        page_row = QHBoxLayout(); page_row.addStretch()
        prev = QPushButton("◀ Önceki"); prev.setObjectName("ghost"); prev.clicked.connect(lambda: self._change_page(-1))
        self._plbl = QLabel("Sayfa 1"); self._plbl.setStyleSheet(f"color:{C['text3']}; font-family:'JetBrains Mono',monospace; min-width:80px;")
        nxt = QPushButton("Sonraki ▶"); nxt.setObjectName("ghost"); nxt.clicked.connect(lambda: self._change_page(1))
        page_row.addWidget(prev); page_row.addWidget(self._plbl); page_row.addWidget(nxt); page_row.addStretch()
        lay.addLayout(page_row)

    def _load_data(self):
        if   self.filter_type == "frequent": rows = self.db.get_frequent_connections(hours=24, limit=100)
        elif self.filter_type == "transfer": rows = self.db.get_top_transfer_connections(hours=24, limit=100)
        elif self.filter_type == "ports":    rows = self.db.get_diverse_port_connections(hours=24, limit=100)
        else:                                rows = self.db.get_recent_connections(limit=self._page_size, offset=self._page*self._page_size)
        self._populate(rows)

    def _populate(self, rows):
        self._table.setRowCount(0)
        for row in rows:
            r = self._table.rowCount(); self._table.insertRow(r)
            ts = row.get("timestamp","")[:19].replace("T"," ")
            for col, val in enumerate([ts, row.get("src_ip",""), row.get("dst_ip",""),
                                        str(row.get("dst_port","")), row.get("protocol",""),
                                        f"{row.get('bytes',0)/1024:.1f}", row.get("process","")]):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(C["text2"]))
                self._table.setItem(r, col, item)
            btn = QPushButton("Engelle"); btn.setFixedSize(70, 26); btn.setObjectName("danger")
            btn.clicked.connect(lambda _, ip=row.get("dst_ip"): self._block(ip))
            self._table.setCellWidget(r, 7, btn)

    def _filter(self):
        text = self._search.text().lower(); proto = self._proto.currentText()
        rows = self.db.get_recent_connections(limit=200)
        filtered = [r for r in rows if (not text or text in str(r.get("dst_ip","")).lower() or text in str(r.get("process","")).lower()) and (proto=="Tümü" or r.get("protocol")==proto)]
        self._populate(filtered[:50])

    def _change_page(self, delta):
        self._page = max(0, self._page + delta)
        self._load_data()
        self._plbl.setText(f"Sayfa {self._page+1}")

    def _block(self, ip):
        from kill_switch import block_ip
        from notifier import notify_ip_blocked
        if block_ip(ip, "Bağlantı listesinden engellendi", None): notify_ip_blocked(ip)


class ReportPopup(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("AI Raporu")
        self.setMinimumSize(620, 480)
        self.setStyleSheet(STYLESHEET)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20); lay.setSpacing(12)
        title = QLabel("📊 AI Güvenlik Raporu"); title.setObjectName("title"); lay.addWidget(title)
        self._content = QTextBrowser()
        self._content.setStyleSheet(f"QTextBrowser {{ background:{C['bg2']}; border-radius:8px; border:1px solid {C['border']}; }}")
        lay.addWidget(self._content, 1)
        br = QHBoxLayout(); br.addStretch()
        cb = QPushButton("Kapat"); cb.setObjectName("ghost"); cb.setFixedSize(100,34); cb.clicked.connect(self.accept)
        br.addWidget(cb); lay.addLayout(br)
        self._load()

    def _load(self):
        report = self.db.get_latest_report()
        if not report: self._content.setHtml(f"<p style='color:{C['text3']};padding:12px;'>Henüz rapor bulunmuyor.</p>"); return
        try: data = json.loads(report.get("content","{}"))
        except: data = {}
        risk = report.get("risk_score", 0)
        color = C["success"] if risk < 3 else C["warning"] if risk < 6 else C["danger"]
        html = (f"<div style='padding:12px;background:{C['bg2']};color:{C['text']};font-family:Segoe UI,sans-serif;font-size:13px;'>"
                f"<h2 style='color:{color};font-family:JetBrains Mono,monospace;'>{risk:.1f}/10 &nbsp; {report.get('status','')}</h2>"
                f"<p style='color:{C['text3']};font-size:11px;font-family:JetBrains Mono,monospace;'>{report.get('created_at','')[:19].replace('T',' ')}</p>"
                f"<hr style='border-color:{C['border']};'>"
                f"<h3 style='color:{C['accent']};font-size:12px;letter-spacing:0.06em;'>ÖZET</h3>"
                f"<p style='line-height:1.65;'>{data.get('summary','Yok')}</p></div>")
        self._content.setHtml(html)


class BlockedIPsPopup(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("🚫 Engellenen IP'ler")
        self.setMinimumSize(660, 560)
        self.setStyleSheet(STYLESHEET)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20); lay.setSpacing(12)
        title = QLabel("🚫 Engellenen IP Adresleri"); title.setObjectName("title"); lay.addWidget(title)
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["IP ADRESİ","SEBEP","TARİH"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        lay.addWidget(self._table, 1)
        br = QHBoxLayout(); br.addStretch()
        cb = QPushButton("Kapat"); cb.setObjectName("ghost"); cb.setFixedSize(120,38); cb.clicked.connect(self.accept)
        br.addWidget(cb); lay.addLayout(br)
        self._load()

    def _load(self):
        blocked = self.db.get_blocked_ips()
        self._table.setRowCount(0)
        for entry in blocked:
            r = self._table.rowCount(); self._table.insertRow(r)
            ip = entry.get("ip","")
            ip_i = QTableWidgetItem(ip); ip_i.setForeground(QColor(C["danger"]))
            re_i = QTableWidgetItem(entry.get("reason","-")); re_i.setForeground(QColor(C["text2"]))
            dt_i = QTableWidgetItem(entry.get("blocked_at","")[:19].replace("T"," ")); dt_i.setForeground(QColor(C["text3"]))
            self._table.setItem(r, 0, ip_i); self._table.setItem(r, 1, re_i); self._table.setItem(r, 2, dt_i)



# ═══════════════════════════════════════════════════════════════════════
#  UYGULAMA BAŞLATICI
# ═══════════════════════════════════════════════════════════════════════

def run_gui(db, analyzer, engine, scheduler):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("NetSonar")
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow(db=db, analyzer=analyzer, engine=engine, scheduler=scheduler)
    window.show()
    # Config bilgisini hemen göster, ağır DB sorgularını timer başlatır
    window._init_statusbar_config()
    return app.exec()
