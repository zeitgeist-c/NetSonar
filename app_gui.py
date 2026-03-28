"""
AgTara — PyQt6 Grafik Kullanıcı Arayüzü
Minimal tek-sayfa tasarım + Popup diyaloglar
"""

import sys
import json
import threading
from datetime import datetime
import dns_cache

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLabel,
    QTabWidget, QLineEdit, QComboBox, QCheckBox, QSpinBox, QFrame, QSizePolicy,
    QTextEdit, QTextBrowser, QSystemTrayIcon, QMenu, QMessageBox, QFormLayout,
    QGroupBox, QRadioButton, QButtonGroup, QScrollArea, QSplitter,
    QProgressBar, QWidgetAction, QDialog,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtGui import (
    QIcon, QColor, QFont, QPixmap, QPainter, QAction, QBrush,
    QLinearGradient, QPainterPath, QPen,
)

# ─── Renk Paleti ─────────────────────────────────────────────────────
C = {
    "bg":       "#0a0e1a",
    "surface":  "#131927",
    "surface2": "#1a2236",
    "border":   "#2a3550",
    "accent":   "#4f8ef7",
    "danger":   "#ef4444",
    "warning":  "#f59e0b",
    "success":  "#10b981",
    "text":     "#e2e8f0",
    "muted":    "#94a3b8",
}

DARK_STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {C["bg"]};
    color: {C["text"]};
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}}
QTabWidget::pane {{
    border: 1px solid {C["border"]};
    background: {C["surface"]};
    border-radius: 8px;
}}
QTabBar::tab {{
    background: {C["surface"]};
    color: {C["muted"]};
    padding: 10px 22px;
    border: none;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    color: {C["text"]};
    border-bottom: 2px solid {C["accent"]};
    background: {C["surface2"]};
}}
QTabBar::tab:hover {{ color: {C["text"]}; }}
QTableWidget {{
    background: {C["surface"]};
    gridline-color: {C["border"]};
    border: 1px solid {C["border"]};
    border-radius: 6px;
    color: {C["text"]};
    selection-background-color: {C["surface2"]};
}}
QTableWidget::item {{ padding: 4px 8px; }}
QHeaderView::section {{
    background: {C["surface2"]};
    color: {C["muted"]};
    border: none;
    border-bottom: 1px solid {C["border"]};
    padding: 6px 8px;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
}}
QPushButton {{
    background: {C["accent"]};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: 600;
}}
QPushButton:hover  {{ background: #3a7ef0; }}
QPushButton:pressed {{ background: #2563eb; }}
QPushButton#danger {{
    background: {C["danger"]};
}}
QPushButton#danger:hover {{ background: #dc2626; }}
QPushButton#success {{
    background: {C["success"]};
}}
QPushButton#muted {{
    background: {C["surface2"]};
    color: {C["muted"]};
    border: 1px solid {C["border"]};
}}
QPushButton#muted:hover {{ color: {C["text"]}; background: {C["border"]}; }}
QLineEdit, QComboBox, QSpinBox {{
    background: {C["surface2"]};
    color: {C["text"]};
    border: 1px solid {C["border"]};
    border-radius: 6px;
    padding: 7px 10px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {C["accent"]};
}}
QComboBox::drop-down {{ border: none; width: 28px; }}
QGroupBox {{
    border: 1px solid {C["border"]};
    border-radius: 8px;
    margin-top: 12px;
    padding: 10px;
    color: {C["muted"]};
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    top: -8px;
    padding: 0 6px;
    background: {C["bg"]};
}}
QScrollBar:vertical {{
    background: {C["surface"]};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {C["border"]};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {C["muted"]}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QTextEdit {{
    background: {C["surface2"]};
    color: {C["text"]};
    border: 1px solid {C["border"]};
    border-radius: 6px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
}}
QLabel#title {{
    font-size: 22px;
    font-weight: 700;
    color: {C["text"]};
}}
QLabel#subtitle {{
    color: {C["muted"]};
    font-size: 12px;
}}
QProgressBar {{
    background: {C["surface2"]};
    border: 1px solid {C["border"]};
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {C["accent"]};
    border-radius: 4px;
}}
QFrame#card {{
    background: {C["surface"]};
    border: 1px solid {C["border"]};
    border-radius: 10px;
}}
QFrame#separator {{
    background: {C["border"]};
    max-height: 1px;
    min-height: 1px;
}}
"""


# ─── Arka Plan Worker Thread'leri ─────────────────────────────────────
class AIWorker(QThread):
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)

    def __init__(self, analyzer, force_full: bool = False):
        super().__init__()
        self.analyzer   = analyzer
        self.force_full = force_full

    def run(self):
        try:
            result = self.analyzer.analyze(hours=1, force_full=self.force_full)
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class VTWorker(QThread):
    result = pyqtSignal(str, dict)   # (ip, result_dict)

    def __init__(self, ip: str):
        super().__init__()
        self.ip = ip

    def run(self):
        from threat_intel import check_ip
        res = check_ip(self.ip)
        self.result.emit(self.ip, res)


class ModelFetchWorker(QThread):
    """OpenRouter'dan ucretsiz model listesini asenkron ceker."""
    fetched = pyqtSignal(list)   # list[str]
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
            self.fetched.emit(free or ["Ucretsiz model bulunamadi"])
        except Exception as exc:
            self.error.emit(str(exc))




# ─── Byte Formatör ────────────────────────────────────────
def _fmt(b: int) -> str:
    """Byte degerini okunakli formata cevirir."""
    if b < 1_024:
        return f"{b} B"
    if b < 1_024 ** 2:
        return f"{b / 1_024:.1f} KB"
    if b < 1_024 ** 3:
        return f"{b / 1_024 ** 2:.1f} MB"
    return f"{b / 1_024 ** 3:.2f} GB"


# ─── Hafif Mini Grafik Widget ─────────────────────────────
class MiniLineChart(QFrame):
    """Hafif çizgi grafik widget - Harici kütüphane gerektirmez."""
    
    def __init__(self, data: list = None, color: str = C["accent"], parent=None):
        super().__init__(parent)
        self._data = data or []
        self._color = color
        self.setMinimumHeight(40)
        self.setMaximumHeight(50)
        self.setStyleSheet(f"background: transparent; border: none;")
    
    def set_data(self, data: list):
        self._data = data
        self.update()
    
    def paintEvent(self, event):
        if not self._data or len(self._data) < 2:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Verileri ölce
        max_val = max(self._data) if max(self._data) > 0 else 1
        min_val = min(self._data)
        range_val = max_val - min_val if max_val != min_val else 1
        
        # Gradyan firca
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0, QColor(self._color))
        gradient.setColorAt(1, QColor(self._color + "00"))  # Transparan
        
        # Cizgi kalemi
        pen = QPen(QColor(self._color), 2)
        painter.setPen(pen)
        
        # Noktalari ciz
        path = QPainterPath()
        for i, val in enumerate(self._data):
            x = int(i * w / (len(self._data) - 1))
            y = h - int((val - min_val) / range_val * (h - 4)) - 2
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        
        painter.drawPath(path)
        
        # Altini doldur
        fill_path = QPainterPath(path)
        fill_path.lineTo(w, h)
        fill_path.lineTo(0, h)
        fill_path.closeSubpath()
        painter.fillPath(fill_path, QBrush(gradient))


# ─── Trafik Paneli ───────────────────────────────────────────
class TrafficPanel(QFrame):
    """
    Yatay panel: Saat / Gun / Hafta / Ay / Yil bazinda
    Upload (yukari ok) ve Download (asagi ok) gosterir.
    Ekstra: Anlik hiz, surecler, protokol dagilimi, karsilastirma.
    """

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setObjectName("card")
        self.setMinimumHeight(140)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 10, 16, 10)
        outer.setSpacing(6)

        # Baslik satiri
        hdr = QHBoxLayout()
        title_lbl = QLabel("Veri Transferı İstatistikleri")
        title_lbl.setStyleSheet("font-weight:700; font-size:13px; border:none;")
        hdr.addWidget(title_lbl)
        
        # Hiz gostergesi
        self.speed_lbl = QLabel("⚡ 0 KB/s")
        self.speed_lbl.setStyleSheet(f"color:{C['accent']}; font-size:11px; font-weight:600; border:none;")
        hdr.addWidget(self.speed_lbl)
        
        hdr.addStretch()
        
        # Karsilastirma
        self.comparison_lbl = QLabel("")
        self.comparison_lbl.setStyleSheet(f"color:{C['muted']}; font-size:10px; border:none;")
        hdr.addWidget(self.comparison_lbl)
        
        outer.addLayout(hdr)

        # Donem kartlari
        row = QHBoxLayout()
        row.setSpacing(8)
        self._cards: list[dict] = []

        for short in ("Saat", "Gun", "Hafta", "Ay", "Yil"):
            card = QFrame()
            card.setStyleSheet(
                f"background:{C['surface2']};border:1px solid {C['border']};"
                "border-radius:8px;"
            )
            vl = QVBoxLayout(card)
            vl.setContentsMargins(10, 6, 10, 6)
            vl.setSpacing(2)

            period_lbl = QLabel(short)
            period_lbl.setStyleSheet(
                f"color:{C['muted']};font-size:10px;font-weight:700;border:none;"
            )
            up_lbl = QLabel("↑ —")
            up_lbl.setStyleSheet(
                f"color:{C['warning']};font-size:12px;font-weight:600;border:none;"
            )
            dl_lbl = QLabel("↓ —")
            dl_lbl.setStyleSheet(
                f"color:{C['accent']};font-size:12px;font-weight:600;border:none;"
            )
            tot_lbl = QLabel("= —")
            tot_lbl.setStyleSheet(
                f"color:{C['muted']};font-size:10px;border:none;"
            )

            vl.addWidget(period_lbl)
            vl.addWidget(up_lbl)
            vl.addWidget(dl_lbl)
            vl.addWidget(tot_lbl)
            row.addWidget(card)

            self._cards.append({
                "up":  up_lbl,
                "dl":  dl_lbl,
                "tot": tot_lbl,
            })

        outer.addLayout(row)
        
        # Ekstra istatistikler (süreçler + protokol)
        extra_row = QHBoxLayout()
        extra_row.setSpacing(12)
        
        # Surecler
        proc_card = QFrame()
        proc_card.setStyleSheet(f"background:{C['surface2']};border:1px solid {C['border']};border-radius:6px;")
        proc_layout = QVBoxLayout(proc_card)
        proc_layout.setContentsMargins(8, 4, 8, 4)
        proc_layout.setSpacing(2)
        proc_title = QLabel("🔃 Süreçler")
        proc_title.setStyleSheet(f"color:{C['muted']};font-size:9px;font-weight:600;border:none;")
        proc_layout.addWidget(proc_title)
        self.process_lbl = QLabel("Veri yok")
        self.process_lbl.setStyleSheet(f"color:{C['text']};font-size:10px;border:none;")
        proc_layout.addWidget(self.process_lbl)
        extra_row.addWidget(proc_card, 1)
        
        # Protokol
        proto_card = QFrame()
        proto_card.setStyleSheet(f"background:{C['surface2']};border:1px solid {C['border']};border-radius:6px;")
        proto_layout = QVBoxLayout(proto_card)
        proto_layout.setContentsMargins(8, 4, 8, 4)
        proto_layout.setSpacing(2)
        proto_title = QLabel("🌐 Protokol")
        proto_title.setStyleSheet(f"color:{C['muted']};font-size:9px;font-weight:600;border:none;")
        proto_layout.addWidget(proto_title)
        self.proto_lbl = QLabel("Veri yok")
        self.proto_lbl.setStyleSheet(f"color:{C['text']};font-size:10px;border:none;")
        proto_layout.addWidget(self.proto_lbl)
        extra_row.addWidget(proto_card, 1)
        
        # Aktif baglanti
        active_card = QFrame()
        active_card.setStyleSheet(f"background:{C['surface2']};border:1px solid {C['border']};border-radius:6px;")
        active_layout = QVBoxLayout(active_card)
        active_layout.setContentsMargins(8, 4, 8, 4)
        active_layout.setSpacing(2)
        active_title = QLabel("🔗 Aktif IP")
        active_title.setStyleSheet(f"color:{C['muted']};font-size:9px;font-weight:600;border:none;")
        active_layout.addWidget(active_title)
        self.active_lbl = QLabel("0")
        self.active_lbl.setStyleSheet(f"color:{C['accent']};font-size:10px;font-weight:600;border:none;")
        active_layout.addWidget(self.active_lbl)
        extra_row.addWidget(active_card, 1)
        
        outer.addLayout(extra_row)

        # Mini grafik satiri
        chart_row = QHBoxLayout()
        chart_row.setSpacing(8)
        
        # Upload grafigi
        upload_chart_frame = QFrame()
        upload_chart_frame.setStyleSheet(f"background:{C['surface2']};border:1px solid {C['border']};border-radius:4px;")
        upload_chart_layout = QVBoxLayout(upload_chart_frame)
        upload_chart_layout.setContentsMargins(6, 2, 6, 2)
        upload_chart_title = QLabel("↑ Gonderim")
        upload_chart_title.setStyleSheet(f"color:{C['success']};font-size:9px;font-weight:600;border:none;")
        upload_chart_layout.addWidget(upload_chart_title)
        self.upload_chart = MiniLineChart(color=C["success"])
        upload_chart_layout.addWidget(self.upload_chart)
        chart_row.addWidget(upload_chart_frame, 1)
        
        # Download grafigi
        download_chart_frame = QFrame()
        download_chart_frame.setStyleSheet(f"background:{C['surface2']};border:1px solid {C['border']};border-radius:4px;")
        download_chart_layout = QVBoxLayout(download_chart_frame)
        download_chart_layout.setContentsMargins(6, 2, 6, 2)
        download_chart_title = QLabel("↓ Indirim")
        download_chart_title.setStyleSheet(f"color:{C['accent']};font-size:9px;font-weight:600;border:none;")
        download_chart_layout.addWidget(download_chart_title)
        self.download_chart = MiniLineChart(color=C["accent"])
        download_chart_layout.addWidget(self.download_chart)
        chart_row.addWidget(download_chart_frame, 1)
        
        outer.addLayout(chart_row)

    def refresh(self):
        try:
            stats = self.db.get_traffic_stats()
        except Exception:
            return
        for i, period in enumerate(stats):
            if i >= len(self._cards):
                break
            c = self._cards[i]
            c["up"].setText(f"↑ {_fmt(period['upload'])}")
            c["dl"].setText(f"↓ {_fmt(period['download'])}")
            c["tot"].setText(f"= {_fmt(period['total'])}  ({period['conn_count']:,} bağlantı)")
        
        # Yeni istatistikler
        try:
            # Hız
            speed = self.db.get_traffic_speed(minutes=5)
            self.speed_lbl.setText(f"⚡ {speed['total_kbs']:.1f} KB/s")
            
            # Karşılaştırma
            comp = self.db.get_traffic_comparison()
            if comp.get("today_change", 0) != 0:
                change = comp["today_change"]
                color = C["success"] if change < 0 else C["danger"]
                arrow = "↓" if change < 0 else "↑"
                self.comparison_lbl.setText(f"Bugün vs Dün: {arrow}{abs(change)}%")
                self.comparison_lbl.setStyleSheet(f"color:{color}; font-size:10px; font-weight:600; border:none;")
            
            # Süreçler
            procs = self.db.get_top_processes(hours=1, limit=3)
            if procs:
                proc_text = " • ".join([f"{p['process'][:12]} ({_fmt(p['total_bytes'])})" for p in procs])
                self.process_lbl.setText(proc_text)
            
            # Protokol
            protos = self.db.get_protocol_distribution(hours=24)
            if protos:
                proto_text = " | ".join([f"{k}:{v['percentage']:.0f}%" for k, v in protos.items()])
                self.proto_lbl.setText(proto_text)
            
            # Aktif IP
            active = self.db.get_active_connections_count(minutes=60)
            self.active_lbl.setText(str(active))
            
            # Grafik verileri
            try:
                timeline = self.db.get_traffic_timeline(hours=1, points=12)
                if timeline:
                    upload_data = [max(t["bytes"] * 0.4, 100) for t in timeline]
                    download_data = [max(t["bytes"] * 0.6, 100) for t in timeline]
                    self.upload_chart.set_data(upload_data)
                    self.download_chart.set_data(download_data)
            except Exception as e:
                print(f"Chart update error: {e}")
            
        except Exception as e:
            print(f"Traffic panel extra stats error: {e}")


# ─── Stat Kartı ──────────────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, label: str, value: str = "0", color: str = C["accent"]):
        super().__init__()
        self.setObjectName("card")
        self.setFixedHeight(90)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {color}; border: none;"
        )
        self.desc_label = QLabel(label)
        self.desc_label.setStyleSheet(f"color: {C['muted']}; font-size: 11px; font-weight: 600; border: none;")

        layout.addWidget(self.value_label)
        layout.addWidget(self.desc_label)

    def set_value(self, v):
        self.value_label.setText(str(v))


# ─── Dashboard Sekmesi ────────────────────────────────────────────────
class DashboardTab(QWidget):
    request_block = pyqtSignal(str)   # IP'yi ana pencereye ilet

    def __init__(self, db):
        super().__init__()
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ── Başlık ──
        hdr = QHBoxLayout()
        title = QLabel("Canlı Ağ Trafiği")
        title.setObjectName("title")
        status = QLabel("● KORUMA AKTİF")
        status.setStyleSheet(f"color: {C['success']}; font-weight: 700; font-size: 12px;")
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(status)
        layout.addLayout(hdr)

        # ── Stat Kartları ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.card_conns   = StatCard("BUGÜNKÜ BAĞLANTI", "0", C["accent"])
        self.card_threats = StatCard("TEHDİT TESPİTİ",  "0", C["danger"])
        self.card_blocked = StatCard("ENGELLENDİ",       "0", C["warning"])
        self.card_reports = StatCard("AI RAPORU",        "0", C["success"])
        for card in (self.card_conns, self.card_threats, self.card_blocked, self.card_reports):
            stats_row.addWidget(card)
        layout.addLayout(stats_row)

        # ── Trafik İstatistikleri Paneli ──
        self.traffic_panel = TrafficPanel(db=self.db)
        layout.addWidget(self.traffic_panel)

        # ── Grafik Paneli (Top 5 IP) ──
        self.chart_panel = QGroupBox("En Fazla Trafik Yapan IP'ler")
        chart_layout = QVBoxLayout(self.chart_panel)
        self.top_ips_table = QTableWidget()
        self.top_ips_table.setColumnCount(2)
        self.top_ips_table.setHorizontalHeaderLabels(["IP", "Toplam Veri"])
        self.top_ips_table.setMaximumHeight(150)
        self.top_ips_table.verticalHeader().setVisible(False)
        chart_layout.addWidget(self.top_ips_table)
        layout.addWidget(self.chart_panel)

        # ── Filtre satiri ──
        filter_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 IP, port veya süreç ara...")
        self.search_box.textChanged.connect(self._filter_table_debounced)
        filter_row.addWidget(self.search_box)
        
        # Protokol filtresi
        self.protocol_filter = QComboBox()
        self.protocol_filter.addItems(["Tümü", "TCP", "UDP", "OTHER"])
        self.protocol_filter.currentTextChanged.connect(lambda _: self._filter_table(self.search_box.text()))
        filter_row.addWidget(QLabel("Protokol:"))
        filter_row.addWidget(self.protocol_filter)
        
        # Tehdit filtresi
        self.threat_filter = QComboBox()
        self.threat_filter.addItems(["Tümü", "Tehdit Var", "Temiz"])
        self.threat_filter.currentTextChanged.connect(lambda _: self._filter_table(self.search_box.text()))
        filter_row.addWidget(QLabel("Durum:"))
        filter_row.addWidget(self.threat_filter)
        
        filter_row.addStretch()
        layout.addLayout(filter_row)

        # ── Bağlantı Tablosu ──
        self.table = QTableWidget()
        #  0:Zaman  1:Hedef IP  2:Site  3:Port  4:Protokol  5:Veri(KB)  6:Süreç  7:Durum  8:Engelle
        cols = ["Zaman", "Hedef IP", "Site", "Port", "Protokol", "Veri (KB)", "Süreç", "Durum", ""]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(1, 125)
        self.table.setColumnWidth(3, 55)
        self.table.setColumnWidth(4, 75)
        self.table.setColumnWidth(5, 75)
        self.table.setColumnWidth(7, 85)
        self.table.setColumnWidth(8, 82)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            self.table.styleSheet() +
            f"QTableWidget {{alternate-background-color: {C['surface2']};}}"
        )
        layout.addWidget(self.table)

        # ── Sayfalama ──
        page_row = QHBoxLayout()
        page_row.addStretch()
        self.prev_btn = QPushButton("◀ Önceki")
        self.prev_btn.clicked.connect(lambda: self._change_page(-1))
        self.page_label = QLabel("Sayfa 1")
        self.next_btn = QPushButton("Sonraki ▶")
        self.next_btn.clicked.connect(lambda: self._change_page(1))
        page_row.addWidget(self.prev_btn)
        page_row.addWidget(self.page_label)
        page_row.addWidget(self.next_btn)
        page_row.addStretch()
        layout.addLayout(page_row)

        self._page = 0
        self._page_size = 100
        self._all_rows: list[dict] = []

    def _change_page(self, delta: int):
        new_page = self._page + delta
        if new_page < 0:
            return
        offset = new_page * self._page_size
        rows = self.db.get_recent_connections(limit=self._page_size, offset=offset)
        if not rows:
            if new_page > 0:
                return
        else:
            self._page = new_page
            self._all_rows = rows
            self._populate_table(rows)
            self.page_label.setText(f"Sayfa {self._page + 1}")

    def refresh(self):
        self._page = 0
        rows = self.db.get_recent_connections(limit=self._page_size, offset=0)
        stats = self.db.get_stats()
        self.card_conns.set_value(f"{stats['today_connections']:,}")
        self.card_threats.set_value(stats["total_threats"])
        self.card_blocked.set_value(stats["blocked_ips"])
        self.card_reports.set_value(stats["total_reports"])
        self.traffic_panel.refresh()      # Trafik istatistiklerini guncelle
        self._all_rows = rows
        self._populate_table(rows)
        self._load_top_ips()

    def _load_top_ips(self):
        """En fazla trafik yapan IP'leri yükle."""
        try:
            summary = self.db.get_summary(hours=24, limit=5)
            self.top_ips_table.setRowCount(0)
            for row in summary:
                r = self.top_ips_table.rowCount()
                self.top_ips_table.insertRow(r)
                self.top_ips_table.setItem(r, 0, QTableWidgetItem(row.get("dst_ip", "")))
                mb = row.get("total_bytes", 0) / (1024 * 1024)
                self.top_ips_table.setItem(r, 1, QTableWidgetItem(f"{mb:.1f} MB"))
        except Exception:
            pass

    def _populate_table(self, rows):
        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            ts      = row.get("timestamp", "")[:19].replace("T", " ")
            kb      = f"{row.get('bytes', 0) / 1024:.1f}"
            flagged = row.get("flagged", 0)
            dst_ip  = row.get("dst_ip", "")
            domain  = dns_cache.resolve(dst_ip)  # arka planda çözülür

            #  col 0: Zaman
            #  col 1: Hedef IP
            #  col 2: Site (domain)
            #  col 3: Port
            #  col 4: Protokol
            #  col 5: Veri KB
            #  col 6: Süreç
            items = [
                ts,
                dst_ip,
                domain,
                str(row.get("dst_port", "")),
                row.get("protocol", ""),
                kb,
                row.get("process", ""),
            ]
            for col, val in enumerate(items):
                item = QTableWidgetItem(val)
                # Site sütunu için özel renk: çözülmediyse soluk, yerel ağ ise mavi
                if col == 2:
                    if val == "...":
                        item.setForeground(QColor(C["muted"]))
                    elif val == "Yerel Ag":
                        item.setForeground(QColor(C["accent"]))
                    else:
                        item.setForeground(QColor(C["success"]))
                else:
                    item.setForeground(QColor(C["text"]))
                self.table.setItem(r, col, item)

            # Durum (col 7)
            if flagged:
                status_item = QTableWidgetItem("Supheeli")
                status_item.setForeground(QColor(C["warning"]))
            else:
                status_item = QTableWidgetItem("Normal")
                status_item.setForeground(QColor(C["success"]))
            self.table.setItem(r, 7, status_item)

            # Engelle butonu (col 8) — yalnizca harici IP'ler icin
            if dst_ip and not dst_ip.startswith(("192.168.", "10.", "127.", "172.")):
                btn = QPushButton("Engelle")
                btn.setFixedSize(76, 26)
                btn.clicked.connect(lambda _, ip=dst_ip: self.request_block.emit(ip))
                btn.setStyleSheet(
                    f"background:{C['danger']};color:white;border-radius:4px;"
                    f"font-size:11px;font-weight:600;"
                )
                self.table.setCellWidget(r, 8, btn)

    def _filter_table_debounced(self, text: str):
        if hasattr(self, '_filter_timer') and self._filter_timer.isActive():
            self._filter_timer.stop()
        from PyQt6.QtCore import QTimer
        self._filter_timer = QTimer()
        self._filter_timer.setSingleShot(True)
        self._filter_timer.timeout.connect(lambda: self._filter_table(text))
        self._filter_timer.start(200)

    def _filter_table(self, text: str):
        t = text.lower()
        proto_filter = self.protocol_filter.currentText()
        threat_filter = self.threat_filter.currentText()
        
        filtered = []
        for row in self._all_rows:
            # Metin filtresi
            match_text = (
                row.get("dst_ip", "") +
                str(row.get("dst_port", "")) +
                row.get("process", "") +
                row.get("protocol", "")
            ).lower()
            
            if t and t not in match_text:
                continue
            
            # Protokol filtresi
            if proto_filter != "Tümü" and row.get("protocol", "") != proto_filter:
                continue
            
            # Tehdit filtresi
            if threat_filter == "Tehdit Var" and not row.get("flagged", 0):
                continue
            if threat_filter == "Temiz" and row.get("flagged", 0):
                continue
            
            filtered.append(row)
        
        self._populate_table(filtered)
        # Filtre sonucunu status bar'da göster
        self._filter_status = f"{len(filtered)} / {len(self._all_rows)} kayıt"
        if hasattr(self, '_status_label'):
            self._status_label.setText(self._filter_status)


# ─── AI Analiz Sekmesi ────────────────────────────────────────────────
class AnalysisTab(QWidget):
    def __init__(self, db, analyzer):
        super().__init__()
        self.db = db
        self.analyzer = analyzer
        self._worker = None
        self._current_report = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Başlık ve kontroller
        hdr = QHBoxLayout()
        lbl = QLabel("AI Güvenlik Analizi")
        lbl.setObjectName("title")
        
        self.force_full_cb = QCheckBox("Tam Analiz (Son 1 Saat)")
        self.force_full_cb.setToolTip("İşaretlenmezse sadece son analizden sonra gelen 'yeni' veriler gönderilir (Token tasarrufu).")
        self.force_full_cb.setStyleSheet(f"color: {C['muted']}; font-size: 11px;")
        
        self.run_btn = QPushButton("▶  Analizi Şimdi Çalıştır")
        self.run_btn.setFixedHeight(38)
        self.run_btn.clicked.connect(self._run_analysis)
        
        hdr.addWidget(lbl)
        hdr.addStretch()
        hdr.addWidget(self.force_full_cb)
        hdr.addWidget(self.run_btn)
        layout.addLayout(hdr)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Risk skoru kartı
        risk_frame = QFrame()
        risk_frame.setObjectName("card")
        risk_frame.setFixedHeight(100)
        risk_layout = QHBoxLayout(risk_frame)
        risk_layout.setContentsMargins(24, 16, 24, 16)

        self.risk_score_lbl = QLabel("—")
        self.risk_score_lbl.setStyleSheet(
            f"font-size: 40px; font-weight: 700; color: {C['muted']}; border: none;"
        )
        risk_layout.addWidget(self.risk_score_lbl)

        right_v = QVBoxLayout()
        self.risk_status_lbl = QLabel("Henüz Analiz Yapılmadı")
        self.risk_status_lbl.setStyleSheet(
            f"font-size: 16px; font-weight: 600; color: {C['muted']}; border: none;"
        )
        self.risk_time_lbl = QLabel("")
        self.risk_time_lbl.setStyleSheet(f"color: {C['muted']}; font-size: 11px; border: none;")
        right_v.addWidget(self.risk_status_lbl)
        right_v.addWidget(self.risk_time_lbl)
        risk_layout.addLayout(right_v)
        risk_layout.addStretch()

        self.provider_lbl = QLabel("")
        self.provider_lbl.setStyleSheet(
            f"color: {C['accent']}; font-size: 11px; font-weight: 600; border: none;"
        )
        risk_layout.addWidget(self.provider_lbl)
        layout.addWidget(risk_frame)

        # Şüpheli bağlantılar tablosu
        susp_label = QLabel("Şüpheli Bağlantılar")
        susp_label.setStyleSheet(f"font-weight: 700; color: {C['text']};")
        layout.addWidget(susp_label)

        self.susp_table = QTableWidget()
        self.susp_table.setColumnCount(4)
        self.susp_table.setHorizontalHeaderLabels(["IP", "Port", "Süreç", "Neden / Eylem"])
        self.susp_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.susp_table.setColumnWidth(0, 140)
        self.susp_table.setColumnWidth(1, 60)
        self.susp_table.setColumnWidth(2, 140)
        self.susp_table.verticalHeader().setVisible(False)
        self.susp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.susp_table.setFixedHeight(180)
        layout.addWidget(self.susp_table)

        # AI Raporu + Gonderilen Veri Onizlemesi (Splitter)
        reports_split = QSplitter(Qt.Orientation.Horizontal)
        
        # Sol: AI Raporu
        rapor_widget = QWidget()
        rapor_layout = QVBoxLayout(rapor_widget)
        rapor_layout.setContentsMargins(0,0,0,0)
        rapor_layout.addWidget(QLabel("AI Analiz Raporu"))
        self.report_browser = QTextBrowser()
        self.report_browser.setReadOnly(True)
        self.report_browser.setPlaceholderText("Analiz calistirildiktan sonra AI yorumu burada goruntulenir...")
        self.report_browser.setMinimumHeight(200)
        self.report_browser.setOpenExternalLinks(False)
        self.report_browser.setStyleSheet(
            f"background:{C['surface2']};color:{C['text']};"
            f"border:1px solid {C['border']};border-radius:6px;"
            f"font-family:'Segoe UI',sans-serif;font-size:13px;"
        )
        rapor_layout.addWidget(self.report_browser)
        
        # Sag: Veri Onizlemesi
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0,0,0,0)
        preview_layout.addWidget(QLabel("Gönderilen Veri Önizlemesi"))
        self.preview_browser = QTextBrowser()
        self.preview_browser.setReadOnly(True)
        self.preview_browser.setPlaceholderText("AI'a gonderilen ham JSON meta verisi (Paket icerigi gitmez).")
        self.preview_browser.setStyleSheet(
            f"background:#0d1117;color:#c9d1d9;"
            f"border:1px solid {C['border']};border-radius:6px;"
            f"font-family:'Cascadia Code', monospace;font-size:11px;"
        )
        preview_layout.addWidget(self.preview_browser)
        
        reports_split.addWidget(rapor_widget)
        reports_split.addWidget(preview_widget)
        reports_split.setSizes([600, 400])
        layout.addWidget(reports_split)

        # Geçmiş Raporlar
        hist_label = QLabel("Rapor Geçmişi")
        hist_label.setStyleSheet(f"font-weight: 700; color: {C['text']};")
        layout.addWidget(hist_label)

        # Export butonları
        export_row = QHBoxLayout()
        export_row.addStretch()
        export_json_btn = QPushButton("📥 JSON İndir")
        export_json_btn.clicked.connect(lambda: self._export_report("json"))
        export_csv_btn = QPushButton("📥 CSV İndir")
        export_csv_btn.clicked.connect(lambda: self._export_report("csv"))
        export_txt_btn = QPushButton("📥 TXT İndir")
        export_txt_btn.clicked.connect(lambda: self._export_report("txt"))
        export_row.addWidget(export_json_btn)
        export_row.addWidget(export_csv_btn)
        export_row.addWidget(export_txt_btn)
        export_row.addStretch()
        layout.addLayout(export_row)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Tarih", "Sağlayıcı", "Risk", "Durum"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setColumnWidth(1, 110)
        self.history_table.setColumnWidth(2, 60)
        self.history_table.setColumnWidth(3, 180)
        layout.addWidget(self.history_table)

    def _run_analysis(self):
        self.run_btn.setEnabled(False)
        self.run_btn.setText("Analiz ediliyor...")
        self.progress.setVisible(True)
        
        force = self.force_full_cb.isChecked()
        self._worker = AIWorker(self.analyzer, force_full=force)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, result: dict):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶  Analizi Şimdi Çalıştır")
        self.progress.setVisible(False)
        try:
            self._display_report(result)
            self._load_history()
        except Exception as exc:
            QMessageBox.critical(self, "Rapor Gösterme Hatası", str(exc))

    def _on_error(self, msg: str):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("▶  Analizi Şimdi Çalıştır")
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Analiz Hatası", msg)

    def _export_report(self, format: str):
        from exporter import export_report
        current = self._current_report
        if not current:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak rapor yok.")
            return
        try:
            filepath = export_report(current, format)
            QMessageBox.information(self, "Başarılı", f"Rapor kaydedildi:\n{filepath}")
        except Exception as exc:
            QMessageBox.critical(self, "Hata", f"Dışa aktarma hatası:\n{exc}")

    def _display_report(self, r: dict):
        score  = r.get("risk_score", 0)
        status = r.get("status", "")
        import importlib, config
        importlib.reload(config)
        provider = config.AI_PROVIDER.upper()

        # Renk ve skor
        if isinstance(score, (int, float)) and score >= 0:
            color = C["success"] if score < 4 else C["warning"] if score < 7 else C["danger"]
            score_txt = f"{score:.1f}"
            self.risk_score_lbl.setText(score_txt)
        else:
            color = C["danger"]
            score_txt = "✕"
            self.risk_score_lbl.setText(score_txt)

        self.risk_score_lbl.setStyleSheet(
            f"font-size:40px;font-weight:700;color:{color};border:none;"
        )
        self.risk_status_lbl.setStyleSheet(
            f"font-size:16px;font-weight:600;color:{color};border:none;"
        )
        self.risk_status_lbl.setText(status or "Bilinmiyor")
        self.risk_time_lbl.setText(f"Son analiz: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        self.provider_lbl.setText(f"🤖 {provider}")

        self.provider_lbl.setText(f"🤖 {provider}")

        # _meta Onizleme (Token Tahmini ve gonderilen ham veri)
        meta = r.get("_meta", {})
        if meta:
            if meta.get("skipped"):
                self.preview_browser.setHtml(
                    f"<div style='color:{C['warning']};padding:10px;'>"
                    f"<b>Atlandi:</b> {meta.get('reason','')}"
                    f"</div>"
                )
            else:
                raw_json = meta.get("raw_payload", "")
                self.preview_browser.setPlainText(raw_json)
                
            est = meta.get('est_tokens', 0)
            if est > 0:
                self.provider_lbl.setText(f"🤖 {provider}  (~{est} token)")

        # ── HTML Rapor ──────────────────────────────────────────
        conns   = r.get("suspicious_connections", []) or []
        summary = r.get("summary", "")

        badge_bg = (
            "#052e16" if score < 4
            else "#451a03" if score < 7
            else "#450a0a"
        )

        rows_html = ""
        for i, conn in enumerate(conns, 1):
            if not isinstance(conn, dict):
                continue
            ip      = conn.get("ip", "")
            port    = conn.get("port", "")
            proc    = conn.get("process", "")
            reason  = conn.get("reason", "")
            action  = conn.get("action", "")
            vt_m    = conn.get("vt_malicious", None)
            vt_s    = conn.get("vt_suspicious", None)
            country = conn.get("vt_country", "")
            is_thr  = conn.get("vt_is_threat", False)

            vt_html = ""
            if vt_m is not None:
                vt_color = C["danger"] if is_thr else C["success"]
                vt_label = f"🛡️ VT: {vt_m} zararli" if is_thr else f"✅ VT: Temiz"
                if country:
                    vt_label += f" &nbsp;|&nbsp; 🌍 {country}"
                vt_html = f'<span style="color:{vt_color};font-size:11px;">{vt_label}</span>'

            rows_html += f"""
            <tr>
              <td style="color:{C['warning']};font-weight:700;padding:6px 4px;">{i}.</td>
              <td style="padding:6px 8px;">
                <b style="color:{C['text']}">{ip}:{port}</b>
                &nbsp;<span style="color:{C['muted']};font-size:11px;">{proc}</span><br>
                <span style="color:{C['text']}">{reason}</span><br>
                <span style="color:{C['accent']};font-size:11px;">➡️ {action}</span><br>
                {vt_html}
              </td>
            </tr>
            <tr><td colspan="2" style="border-top:1px solid {C['border']};padding:0;"></td></tr>
            """

        conns_section = ""
        if conns:
            conns_section = f"""
            <h3 style="color:{C['warning']};margin:16px 0 8px;">&#9888; Supheeli Baglantilar ({len(conns)} adet)</h3>
            <table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
              {rows_html}
            </table>
            """
        else:
            conns_section = (
                f'<p style="color:{C["success"]};margin:14px 0;">&nbsp;&#10003; Supheeli baglanti tespit edilmedi.</p>'
            )

        # summary paragraf satirlari
        summary_lines = "".join(
            f'<p style="margin:4px 0;line-height:1.6;">{line}</p>'
            for line in (summary or "İnceleme sonucu mevcut degil.").split("\n")
            if line.strip()
        )

        html = f"""
        <html><body style="background:{C['surface2']};color:{C['text']};
                           font-family:'Segoe UI',sans-serif;font-size:13px;padding:12px;">

          <div style="background:{badge_bg};border-radius:8px;padding:10px 16px;margin-bottom:14px;">
            <span style="font-size:22px;font-weight:700;color:{color};">{score_txt}/10</span>
            &nbsp;&nbsp;
            <span style="font-size:15px;font-weight:600;color:{color};">{status}</span>
            &nbsp;&nbsp;
            <span style="font-size:11px;color:{C['muted']};">&#128340; {datetime.now().strftime('%d.%m.%Y %H:%M')}
            &nbsp;|&nbsp; 🤖 {provider}</span>
          </div>

          <h3 style="color:{C['accent']};margin:0 0 6px;">📄 AI Degerlendirmesi</h3>
          <div style="background:{C['surface']};border-radius:6px;padding:10px 14px;
                      border-left:3px solid {color};">
            {summary_lines}
          </div>

          {conns_section}

        </body></html>
        """
        self.report_browser.setHtml(html)

        # Eski supheli tablo da goster (uyumluluk icin)
        self.susp_table.setRowCount(0)
        for conn in conns:
            if not isinstance(conn, dict):
                continue
            row = self.susp_table.rowCount()
            self.susp_table.insertRow(row)
            reason_action = f"{conn.get('reason', '')} → {conn.get('action', '')}"
            vt_info = ""
            if conn.get("vt_malicious") is not None:
                vt_info = f" | VT: {conn['vt_malicious']} zararli"
            for col, val in enumerate([
                conn.get("ip", ""),
                str(conn.get("port", "")),
                conn.get("process", ""),
                reason_action + vt_info,
            ]):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(C["warning"]))
                self.susp_table.setItem(row, col, item)


    def _load_history(self):
        reports = self.db.get_all_reports()
        self.history_table.setRowCount(0)
        for rep in reports:
            r = self.history_table.rowCount()
            self.history_table.insertRow(r)
            score = rep.get("risk_score", 0)
            color = C["success"] if score < 4 else C["warning"] if score < 7 else C["danger"]
            for col, val in enumerate([
                rep.get("created_at", "")[:19].replace("T", " "),
                rep.get("provider", "").upper(),
                f"{score:.1f}",
                rep.get("status", ""),
            ]):
                item = QTableWidgetItem(val)
                if col == 2:
                    item.setForeground(QColor(color))
                else:
                    item.setForeground(QColor(C["text"]))
                self.history_table.setItem(r, col, item)

    def refresh(self):
        self._load_history()


# ─── Engellenen IP'ler Sekmesi ────────────────────────────────────────
class BlockedTab(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        hdr = QHBoxLayout()
        title = QLabel("Engellenen IP Adresleri")
        title.setObjectName("title")
        hdr.addWidget(title)
        hdr.addStretch()

        # Manuel engelleme
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("IP adresi gir (örn: 185.220.101.5)")
        self.ip_input.setFixedWidth(220)
        block_btn = QPushButton("Engelle")
        block_btn.setObjectName("danger")
        block_btn.clicked.connect(self._manual_block)
        hdr.addWidget(self.ip_input)
        hdr.addWidget(block_btn)
        layout.addLayout(hdr)

        # VT sorgu satırı
        vt_row = QHBoxLayout()
        self.vt_input = QLineEdit()
        self.vt_input.setPlaceholderText("VirusTotal IP sorgusu...")
        self.vt_input.setFixedWidth(220)
        vt_btn = QPushButton("VT Sorgula")
        vt_btn.setObjectName("muted")
        vt_btn.clicked.connect(self._vt_check)
        self.vt_result_lbl = QLabel("")
        self.vt_result_lbl.setStyleSheet(f"color:{C['muted']};")
        vt_row.addWidget(self.vt_input)
        vt_row.addWidget(vt_btn)
        vt_row.addWidget(self.vt_result_lbl)
        vt_row.addStretch()
        layout.addLayout(vt_row)

        sep = QFrame()
        sep.setObjectName("separator")
        layout.addWidget(sep)

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["IP Adresi", "Neden", "Engelleme Tarihi", ""])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(2, 175)
        self.table.setColumnWidth(3, 110)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    def refresh(self):
        blocked = self.db.get_blocked_ips()
        self.table.setRowCount(0)
        for entry in blocked:
            r = self.table.rowCount()
            self.table.insertRow(r)
            ip = entry.get("ip", "")
            for col, val in enumerate([
                ip,
                entry.get("reason", ""),
                entry.get("blocked_at", "")[:19].replace("T", " "),
            ]):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(C["text"]))
                self.table.setItem(r, col, item)

            unb_btn = QPushButton("Engeli Kaldır")
            unb_btn.setObjectName("muted")
            unb_btn.setFixedSize(100, 26)
            unb_btn.setStyleSheet(
                f"background:{C['surface2']};color:{C['muted']};border-radius:4px;"
                f"font-size:11px;border:1px solid {C['border']};"
            )
            unb_btn.clicked.connect(lambda _, i=ip: self._unblock(i))
            self.table.setCellWidget(r, 3, unb_btn)

    def _manual_block(self):
        ip = self.ip_input.text().strip()
        if not ip:
            return
        from kill_switch import block_ip
        from notifier import notify_ip_blocked
        ok = block_ip(ip, reason="Manuel engelleme", db=self.db)
        if ok:
            notify_ip_blocked(ip)
            self.ip_input.clear()
            self.refresh()
        else:
            QMessageBox.critical(self, "Hata", f"{ip} engellenemedi.\nYönetici yetkisi gereklidir.")

    def _unblock(self, ip: str):
        from kill_switch import unblock_ip
        ok = unblock_ip(ip)
        if ok:
            self.db.remove_blocked_ip(ip)
            self.refresh()
        else:
            QMessageBox.warning(self, "Uyarı", f"{ip} için kural kaldırılamadı.")

    def _vt_check(self):
        ip = self.vt_input.text().strip()
        if not ip:
            return
        self.vt_result_lbl.setText("Sorgulanıyor...")
        self._vt_worker = VTWorker(ip)
        self._vt_worker.result.connect(self._on_vt_result)
        self._vt_worker.start()

    def _on_vt_result(self, ip: str, res: dict):
        if res.get("error"):
            self.vt_result_lbl.setText(f"Hata: {res['error']}")
            self.vt_result_lbl.setStyleSheet(f"color:{C['danger']};")
            return
        mal = res["malicious"]
        country = res["country"]
        is_threat = res["is_threat"]
        color = C["danger"] if is_threat else C["success"]
        icon = "⛔" if is_threat else "✓"
        self.vt_result_lbl.setText(
            f"{icon} {ip} ({country}) — {mal} kötü niyetli motor"
        )
        self.vt_result_lbl.setStyleSheet(f"color:{color};font-weight:600;")


# ─── Ayarlar Sekmesi ─────────────────────────────────────────────────
class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._fetch_worker  = None
        self._ollama_worker = None
        self._setup_ui()

    def _setup_ui(self):
        from PyQt6.QtWidgets import QStackedWidget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Ayarlar")
        title.setObjectName("title")
        layout.addWidget(title)

        # ── Provider Secimi ───────────────────────────────────────────
        prov_group = QGroupBox("AI Sağlayıcı Seçimi")
        prov_form  = QFormLayout(prov_group)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["openrouter", "gemini"])
        prov_form.addRow("Aktif Sağlayıcı:", self.provider_combo)

        # Sağlayıcı bilgi etiketi
        self.provider_info = QLabel("")
        self.provider_info.setStyleSheet(f"color:{C['muted']};font-size:11px;")
        self.provider_info.setWordWrap(True)
        prov_form.addRow("", self.provider_info)
        layout.addWidget(prov_group)

        # ── Sağlayıcıya Özel Stacked Panel ───────────────────────────
        self.stack = QStackedWidget()

        # ── Panel 0: OpenRouter ───────────────────────
        or_widget = QWidget()
        or_form   = QFormLayout(or_widget)
        or_form.setContentsMargins(0, 0, 0, 0)

        or_key_row = QHBoxLayout()
        self.openrouter_key = QLineEdit()
        self.openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openrouter_key.setPlaceholderText("sk-or-...")
        or_key_row.addWidget(self.openrouter_key)
        self._or_show_btn = QPushButton("👁")
        self._or_show_btn.setFixedWidth(30)
        self._or_show_btn.clicked.connect(lambda: self._toggle_password(self.openrouter_key, self._or_show_btn))
        or_key_row.addWidget(self._or_show_btn)
        or_form.addRow("API Key:", or_key_row)

        # Model: Dropdown + yenile butonu
        model_row = QHBoxLayout()
        self.openrouter_model_combo = QComboBox()
        self.openrouter_model_combo.setEditable(True)
        self.openrouter_model_combo.setMinimumWidth(300)
        model_row.addWidget(self.openrouter_model_combo)
        fetch_btn = QPushButton("↻ Modelleri Getir")
        fetch_btn.setObjectName("muted")
        fetch_btn.setFixedWidth(160)
        fetch_btn.clicked.connect(self._fetch_or_models)
        model_row.addWidget(fetch_btn)
        or_form.addRow("Model:", model_row)

        # Kredi / bakiye bilgisi
        self.credits_lbl = QLabel("")
        self.credits_lbl.setStyleSheet(f"color:{C['muted']};font-size:11px;")
        or_form.addRow("Kredi:", self.credits_lbl)

        self.stack.addWidget(or_widget)

        # ── Panel 1: Gemini ───────────────────────────
        gm_widget = QWidget()
        gm_form   = QFormLayout(gm_widget)
        gm_form.setContentsMargins(0, 0, 0, 0)

        gm_key_row = QHBoxLayout()
        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key.setPlaceholderText("AIza...")
        gm_key_row.addWidget(self.gemini_key)
        self._gm_show_btn = QPushButton("👁")
        self._gm_show_btn.setFixedWidth(30)
        self._gm_show_btn.clicked.connect(lambda: self._toggle_password(self.gemini_key, self._gm_show_btn))
        gm_key_row.addWidget(self._gm_show_btn)
        gm_form.addRow("API Key:", gm_key_row)

        self.gemini_model_combo = QComboBox()
        self.gemini_model_combo.addItems([
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
        ])
        gm_form.addRow("Model:", self.gemini_model_combo)

        gm_info = QLabel("Ücretsiz katman: dakikada 15 istek, günde 1500 istek")
        gm_info.setStyleSheet(f"color:{C['muted']};font-size:11px;")
        gm_form.addRow("", gm_info)
        gm_link = QLabel('<a href="https://aistudio.google.com/apikey" style="color:#4f8ef7;">API Key Al →</a>')
        gm_link.setOpenExternalLinks(True)
        gm_form.addRow("", gm_link)

        self.stack.addWidget(gm_widget)

        provider_box = QGroupBox("Sağlayıcı Ayarları")
        stack_layout  = QVBoxLayout(provider_box)
        stack_layout.addWidget(self.stack)
        layout.addWidget(provider_box)

        # Provider değişince paneli güncelle
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)

        # ── Zamanlayıcı ───────────────────────────────────────────────
        sched_group = QGroupBox("Analiz Zamanlayıcısı")
        sched_form  = QFormLayout(sched_group)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(5, 1440)
        self.interval_spin.setValue(60)
        self.interval_spin.setSuffix(" dakika")
        sched_form.addRow("Analiz Aralığı:", self.interval_spin)
        
        # Ağ arayüzü seçimi
        iface_row = QHBoxLayout()
        self.interface_combo = QComboBox()
        self.interface_combo.addItem("Tüm Ağ Arayüzleri", None)
        self._load_interfaces()
        iface_row.addWidget(self.interface_combo)
        iface_refresh_btn = QPushButton("↻")
        iface_refresh_btn.setToolTip("Ağ arayüzlerini yenile")
        iface_refresh_btn.setFixedWidth(30)
        iface_refresh_btn.clicked.connect(self._load_interfaces)
        iface_row.addWidget(iface_refresh_btn)
        sched_form.addRow("Ağ Arayüzü:", iface_row)
        
        # Windows başlangıcı
        self.autostart_cb = QCheckBox("Windows açılınca otomatik başlat")
        self.autostart_cb.setToolTip("Bilgisayar her açıldığında AgTara arka planda çalışır.")
        sched_form.addRow("Otomatik Başlatma:", self.autostart_cb)

        # ── Özel Uyarılar ─────────────────────────────────────────────
        alerts_group = QGroupBox("Özel Uyarı Kuralları")
        alerts_layout = QVBoxLayout(alerts_group)
        
        alerts_info = QLabel("Belirli IP veya portlar için bildirim alın.")
        alerts_info.setStyleSheet(f"color: {C['muted']}; font-size: 11px;")
        alerts_layout.addWidget(alerts_info)
        
        # Uyarı listesi
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(4)
        self.alerts_table.setHorizontalHeaderLabels(["Ad", "IP Deseni", "Port", "Aktif"])
        self.alerts_table.setMaximumHeight(120)
        self.alerts_table.verticalHeader().setVisible(False)
        self._load_alerts()
        alerts_layout.addWidget(self.alerts_table)
        
        # Uyarı ekle butonları
        alert_btn_row = QHBoxLayout()
        add_alert_btn = QPushButton("+ Ekle")
        add_alert_btn.clicked.connect(self._add_alert)
        remove_alert_btn = QPushButton("🗑️ Sil")
        remove_alert_btn.clicked.connect(self._remove_alert)
        alert_btn_row.addWidget(add_alert_btn)
        alert_btn_row.addWidget(remove_alert_btn)
        alert_btn_row.addStretch()
        alerts_layout.addLayout(alert_btn_row)
        
        layout.addWidget(alerts_group)

        # ── Butonlar ─────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        save_btn = QPushButton("💾  Ayarları Kaydet")
        save_btn.clicked.connect(self._save)
        save_btn.setFixedHeight(40)
        btn_row.addWidget(save_btn)

        test_btn = QPushButton("🔌  Bağlantıyı Test Et")
        test_btn.setObjectName("muted")
        test_btn.clicked.connect(self._test_api)
        test_btn.setFixedHeight(40)
        btn_row.addWidget(test_btn)
        layout.addLayout(btn_row)

        self.test_result_lbl = QLabel("")
        self.test_result_lbl.setWordWrap(True)
        self.test_result_lbl.setStyleSheet(f"color:{C['muted']};font-size:12px;")
        layout.addWidget(self.test_result_lbl)

        layout.addStretch()
        self._load_current_settings()
        # Provider'ı set ettikten sonra panel güncelle
        self._on_provider_changed(self.provider_combo.currentText())

    # ──────────────────────────────────────────────────────────────────
    def _on_provider_changed(self, provider: str):
        """Provider değişince ilgili paneli aç ve bilgi metnini güncelle."""
        idx_map  = {"openrouter": 0, "gemini": 1}
        info_map = {
            "openrouter": "☁️  Bulut AI — OpenRouter.ai aracılığıyla 200+ model. Aktif ücretsiz modeller için 'Modelleri Getir' butonuna bas.",
            "gemini":     "☁️  Google Gemini — Ücretssiz katman mevcut. aistudio.google.com/apikey adresinden anahtar al.",
        }
        self.stack.setCurrentIndex(idx_map.get(provider, 0))
        self.provider_info.setText(info_map.get(provider, ""))

    def _fetch_or_models(self):
        """OpenRouter ücretsiz model listesini arka planda çek."""
        self.credits_lbl.setText("Modeller getiriliyor...")
        key = self.openrouter_key.text().strip()
        if not key:
            self.credits_lbl.setText("⚠️ Önce API key gir.")
            return

        # Geçici olarak key'i config'e yaz
        import config as cfg
        cfg.OPENROUTER_API_KEY = key

        self._fetch_worker = ModelFetchWorker()
        self._fetch_worker.fetched.connect(self._on_or_models_fetched)
        self._fetch_worker.error.connect(lambda e: self.credits_lbl.setText(f"❌ {e[:60]}"))
        self._fetch_worker.start()

        # Kredi bilgisini de çek
        self._fetch_credits(key)

    def _fetch_credits(self, key: str):
        """OpenRouter kredi bilgisini çek."""
        import threading, requests
        def _do():
            try:
                import config as cfg
                r = requests.get(
                    f"{cfg.OPENROUTER_BASE_URL}/auth/key",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=6,
                )
                if r.status_code == 200:
                    data  = r.json().get("data", {})
                    limit = data.get("limit")
                    usage = data.get("usage")
                    label = data.get("label", "")
                    if limit is not None and usage is not None:
                        remaining = limit - usage
                        self.credits_lbl.setText(
                            f"💳 Kullanılan: ${usage:.4f} / ${limit:.2f}  |  Kalan: ${remaining:.4f}"
                            + (f"  |  🏷️ {label}" if label else "")
                        )
                    else:
                        self.credits_lbl.setText("💳 Kredi bilgisi alındı (limit yok / sınırsız)")
            except Exception as e:
                self.credits_lbl.setText(f"Kredi bilgisi alınamadı: {e}")
        threading.Thread(target=_do, daemon=True).start()

    def _on_or_models_fetched(self, models: list):
        """OpenRouter model listesi gelince dropdown'ı doldur."""
        import config as cfg
        current = cfg.OPENROUTER_MODEL
        self.openrouter_model_combo.clear()
        self.openrouter_model_combo.addItems(models)
        # Mevcut modeli seç
        idx = self.openrouter_model_combo.findText(current)
        if idx >= 0:
            self.openrouter_model_combo.setCurrentIndex(idx)
        self.credits_lbl.setText(
            (self.credits_lbl.text() or "") +
            f"  |  📦 {len(models)} ücretsiz model yüklendi"
        )

    def _load_alerts(self):
        """Uyarı kurallarını yükle."""
        from custom_alerts import load_alerts
        rules = load_alerts()
        self.alerts_table.setRowCount(0)
        for rule in rules:
            row = self.alerts_table.rowCount()
            self.alerts_table.insertRow(row)
            self.alerts_table.setItem(row, 0, QTableWidgetItem(rule.name))
            self.alerts_table.setItem(row, 1, QTableWidgetItem(rule.ip_pattern or "*"))
            self.alerts_table.setItem(row, 2, QTableWidgetItem(str(rule.port) if rule.port else "*"))
            enabled_item = QTableWidgetItem("✓" if rule.enabled else "✗")
            enabled_item.setCheckState(Qt.CheckState.Checked if rule.enabled else Qt.CheckState.Unchecked)
            self.alerts_table.setItem(row, 3, enabled_item)

    def _add_alert(self):
        """Yeni uyarı kuralı ekle."""
        from custom_alerts import load_alerts, save_alerts, AlertRule
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Yeni Uyarı", "Kural adı:")
        if not ok or not name:
            return
        ip, _ = QInputDialog.getText(self, "IP Deseni", "IP (boş = her IP, * = joker):")
        port_str, _ = QInputDialog.getText(self, "Port", "Port (boş = her port):")
        port = int(port_str) if port_str.strip() else None
        rule = AlertRule(name=name, ip_pattern=ip or None, port=port)
        rules = load_alerts()
        rules.append(rule)
        save_alerts(rules)
        self._load_alerts()

    def _remove_alert(self):
        """Seçili uyarı kuralını sil."""
        from custom_alerts import load_alerts, save_alerts
        row = self.alerts_table.currentRow()
        if row < 0:
            return
        rules = load_alerts()
        if row < len(rules):
            rules.pop(row)
            save_alerts(rules)
            self._load_alerts()

    def _load_current_settings(self):
        """Mevcut config.py değerlerini formlara yükle."""
        try:
            import config as cfg, importlib
            importlib.reload(cfg)
            idx = self.provider_combo.findText(cfg.AI_PROVIDER)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
            self.openrouter_key.setText(cfg.OPENROUTER_API_KEY)
            self.openrouter_model_combo.clear()
            self.openrouter_model_combo.addItem(cfg.OPENROUTER_MODEL)
            # Gemini model
            gm_idx = self.gemini_model_combo.findText(cfg.GEMINI_MODEL)
            if gm_idx >= 0:
                self.gemini_model_combo.setCurrentIndex(gm_idx)
            self.gemini_key.setText(cfg.GEMINI_API_KEY)
            self.interval_spin.setValue(cfg.ANALYSIS_INTERVAL_MINUTES)
            
            # Otomatik başlatma durumunu yükle
            try:
                from autostart import is_autostart_enabled
                self.autostart_cb.setChecked(is_autostart_enabled())
            except Exception:
                pass

        except Exception:
            pass

    def _save(self):
        """Seçilen değerleri config.py dosyasına yaz."""
        import config as cfg, importlib
        provider = self.provider_combo.currentText()
        cfg.AI_PROVIDER = provider

        cfg.OPENROUTER_API_KEY = self.openrouter_key.text().strip()
        cfg.OPENROUTER_MODEL   = (
            self.openrouter_model_combo.currentText().strip()
            or cfg.OPENROUTER_MODEL
        )
        cfg.GEMINI_API_KEY = self.gemini_key.text().strip()
        cfg.GEMINI_MODEL   = self.gemini_model_combo.currentText()
        cfg.ANALYSIS_INTERVAL_MINUTES = self.interval_spin.value()

        # Otomatik başlatma ayarını kaydet
        try:
            from autostart import enable_autostart, disable_autostart
            if self.autostart_cb.isChecked():
                enable_autostart()
            else:
                disable_autostart()
        except Exception as exc:
            print(f"Otomatik başlatma ayarı kaydedilirken hata: {exc}")

        try:
            import pathlib, re
            config_path = pathlib.Path("config.py")
            text = config_path.read_text(encoding="utf-8")

            def _set(src: str, key: str, val: str) -> str:
                """key = \"...\" seklindeki satiri degistir. re.escape KULLANMA, lambda ile degistir."""
                pattern = rf'^({re.escape(key)}\s*=\s*")[^"]*(")'
                return re.sub(
                    pattern,
                    lambda m: m.group(1) + val + m.group(2),
                    src,
                    flags=re.MULTILINE,
                )

            for key, val in [
                ("AI_PROVIDER",                  cfg.AI_PROVIDER),
                ("OPENROUTER_API_KEY",           cfg.OPENROUTER_API_KEY),
                ("OPENROUTER_MODEL",             cfg.OPENROUTER_MODEL),
                ("GEMINI_API_KEY",               cfg.GEMINI_API_KEY),
                ("GEMINI_MODEL",                 cfg.GEMINI_MODEL),
                ("ANALYSIS_INTERVAL_MINUTES",    str(cfg.ANALYSIS_INTERVAL_MINUTES)),
            ]:
                text = _set(text, key, val)

            config_path.write_text(text, encoding="utf-8")
            importlib.reload(cfg)
            self.test_result_lbl.setStyleSheet(f"color:{C['success']};font-size:12px;font-weight:600;")
            self.test_result_lbl.setText(
                f"✅ Kaydedildi — Aktif sağlayıcı: {cfg.AI_PROVIDER.upper()} "
                f"| Model: {cfg.OPENROUTER_MODEL if provider == 'openrouter' else cfg.GEMINI_MODEL}"
            )

        except Exception as e:
            QMessageBox.warning(self, "Kayıt Hatası", f"config.py güncellenemedi: {e}\nAyarlar çalışma süresi için geçerli.")

    def _toggle_password(self, line_edit: QLineEdit, btn: QPushButton):
        """API key göster/gizle."""
        if line_edit.echoMode() == QLineEdit.EchoMode.Password:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("🔒")
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("👁")

    def _load_interfaces(self):
        """Ağ arayüzlerini yükle."""
        from capture_engine import get_network_interfaces
        current = self.interface_combo.currentData()
        self.interface_combo.blockSignals(True)
        self.interface_combo.clear()
        self.interface_combo.addItem("Tüm Ağ Arayüzleri", None)
        try:
            for iface in get_network_interfaces():
                text = f"{iface['name']} ({iface['ip']})"
                self.interface_combo.addItem(text, iface['name'])
        except Exception as exc:
            print(f"Ağ arayüzleri yüklenirken hata: {exc}")
        # Eski seçimi koru
        if current:
            idx = self.interface_combo.findData(current)
            if idx >= 0:
                self.interface_combo.setCurrentIndex(idx)
        self.interface_combo.blockSignals(False)

    def _test_api(self):
        """Seçili sağlayıcının bağlantısını test et."""
        self._save()
        self.test_result_lbl.setStyleSheet(f"color:{C['muted']};font-size:12px;")
        self.test_result_lbl.setText("🔄 Test ediliyor...")
        try:
            from ai_analyzer import AIAnalyzer
            class _FakeDB:
                def get_summary(self, **_): return []
                def save_report(self, **_): pass
            analyzer = AIAnalyzer(_FakeDB())
            issues   = analyzer.validate_config()
        except Exception as exc:
            issues = [str(exc)]

        provider = self.provider_combo.currentText().upper()
        if issues:
            msg = "\n".join(f"• {i}" for i in issues)
            self.test_result_lbl.setStyleSheet(f"color:{C['danger']};font-size:12px;font-weight:600;")
            self.test_result_lbl.setText(f"❌ {provider} — Sorun:\n{msg}")
        else:
            self.test_result_lbl.setStyleSheet(f"color:{C['success']};font-size:12px;font-weight:600;")
            self.test_result_lbl.setText(f"✅ {provider} yapılandırması geçerli.")




# ─── Yeni Ana Pencere (Tek Sayfa + Popup) ─────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, db, analyzer, engine, scheduler):
        super().__init__()
        self.db         = db
        self.analyzer   = analyzer
        self.engine     = engine
        self.scheduler  = scheduler
        self.setWindowTitle("AgTara — AI Ağ İzleyici")
        self.setMinimumSize(1000, 650)
        self.resize(1200, 750)
        self._setup_style()
        self._setup_ui()
        self._setup_tray()
        self._setup_timer()

    def _setup_style(self):
        self.setStyleSheet(DARK_STYLESHEET)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(15)

        # Header
        header = self._create_header()
        root.addWidget(header)

        # İstatistik Kartları
        stats_row = self._create_stats_cards()
        root.addWidget(stats_row)

        # Ana İçerik
        content = self._create_content_area()
        root.addWidget(content, 1)

        # Footer
        footer = self._create_footer()
        root.addWidget(footer)

    def _create_header(self):
        frame = QFrame()
        frame.setStyleSheet(f"background: {C['surface']}; border-radius: 8px;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(20, 10, 20, 10)

        logo = QLabel("🛡️ AgTara")
        logo.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {C['accent']};")
        layout.addWidget(logo)
        
        self.status_label = QLabel("● İzleme aktif")
        self.status_label.setStyleSheet(f"color: {C['success']}; font-size: 12px; margin-left: 20px;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()

        self.refresh_btn = QPushButton("🔄 Yenile")
        self.refresh_btn.setFixedHeight(36)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 6px; padding: 0 12px; font-size: 13px; }}
            QPushButton:hover {{ background: {C['border']}; }}
        """)
        self.refresh_btn.clicked.connect(self._refresh_all)
        layout.addWidget(self.refresh_btn)

        self.quick_analyze_btn = QPushButton("⚡ Analiz")
        self.quick_analyze_btn.setFixedHeight(36)
        self.quick_analyze_btn.setStyleSheet(f"""
            QPushButton {{ background: {C['accent']}; color: white; border: none; border-radius: 6px; padding: 0 14px; font-weight: 600; font-size: 13px; }}
            QPushButton:hover {{ background: #3d7de8; }}
        """)
        self.quick_analyze_btn.clicked.connect(self._run_quick_analysis)
        layout.addWidget(self.quick_analyze_btn)

        self.blocked_btn = QPushButton("📋 Engelli")
        self.blocked_btn.setFixedHeight(36)
        self.blocked_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['surface2']};
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {C['border']}; }}
        """)
        self.blocked_btn.clicked.connect(self._show_blocked_popup)
        layout.addWidget(self.blocked_btn)

        self.data_btn = QPushButton("📤 Veri")
        self.data_btn.setFixedHeight(36)
        self.data_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['surface2']};
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {C['border']}; }}
        """)
        self.data_btn.clicked.connect(self._show_analysis_data)
        layout.addWidget(self.data_btn)

        settings_btn = QPushButton("⚙️ Ayarlar")
        settings_btn.setFixedHeight(36)
        settings_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: {C['surface2']}; 
                color: {C['text']}; 
                border: 1px solid {C['border']}; 
                border-radius: 6px; 
                padding: 0 15px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {C['border']}; }}
        """)
        settings_btn.clicked.connect(self._show_settings_popup)
        layout.addWidget(settings_btn)
        return frame

    def _create_stats_cards(self):
        row = QHBoxLayout()
        row.setSpacing(10)
        
        self.card_conns = self._make_stat_card("Bağlantı", "0", "Bugün", C["accent"])
        self.card_threats = self._make_stat_card("Tehdit", "0", "Tespit", C["danger"])
        self.card_blocked = self._make_stat_card("Engelli", "0", "IP", C["warning"])
        self.card_reports = self._make_stat_card("Rapor", "0", "AI", C["success"])
        
        for card in [self.card_conns, self.card_threats, self.card_blocked, self.card_reports]:
            row.addWidget(card)
        
        return self._wrap_layout(row)

    def _make_stat_card(self, title, value, subtitle, color):
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background: {C['surface']}; border: 1px solid {C['border']}; border-left: 3px solid {color}; border-radius: 6px; }}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {color}; border: none;")
        layout.addWidget(value_lbl)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {C['muted']}; border: none;")
        layout.addWidget(title_lbl)
        
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet(f"font-size: 10px; color: {C['muted']}; border: none;")
        layout.addWidget(sub_lbl)
        return frame

    def _make_stat_card(self, title, value, subtitle, color):
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background: {C['surface']}; border: 1px solid {C['border']}; border-left: 3px solid {color}; border-radius: 8px; }}")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(4)
        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(f"font-size: 32px; font-weight: 700; color: {color}; border: none;")
        layout.addWidget(value_lbl)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {C['muted']}; border: none;")
        layout.addWidget(title_lbl)
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet(f"font-size: 11px; color: {C['muted']}; border: none;")
        layout.addWidget(sub_lbl)
        
        return frame

    def _wrap_layout(self, layout):
        frame = QFrame()
        v = QVBoxLayout(frame)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        v.addLayout(layout)
        return frame

    def _create_content_area(self):
        row = QHBoxLayout()
        row.setSpacing(12)
        
        # Sol: Trafik + Rapor (yan yana)
        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        traffic = self._create_traffic_panel()
        report = self._create_report_panel()
        top_row.addWidget(traffic)
        top_row.addWidget(report)
        
        # Alt: Son Bağlantılar (kompakt)
        connections = self._create_connections_panel()
        
        # Ana layout'a ekle
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.addLayout(top_row)
        main_layout.addWidget(connections)
        
        return self._wrap_layout(main_layout)

    def _create_traffic_panel(self):
        frame = QFrame()
        frame.setStyleSheet(f"background: {C['surface']}; border-radius: 8px; border: 1px solid {C['border']};")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        
        header = QHBoxLayout()
        title = QLabel("📊 Ağ Trafiği")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {C['text']};")
        header.addWidget(title)
        
        # Hiz gostergesi
        self.traffic_speed = QLabel("⚡ 0 KB/s")
        self.traffic_speed.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {C['accent']};")
        header.addWidget(self.traffic_speed)
        
        # Karsilastirma
        self.traffic_comparison = QLabel("")
        self.traffic_comparison.setStyleSheet(f"font-size: 10px; color: {C['muted']};")
        header.addWidget(self.traffic_comparison)
        
        header.addStretch()
        
        self.traffic_detail_btn = QPushButton("Detay →")
        self.traffic_detail_btn.setFixedHeight(26)
        self.traffic_detail_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C['surface2']};
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 4px;
                padding: 0 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background: {C['border']}; }}
        """)
        self.traffic_detail_btn.setToolTip("Trafik detayları")
        self.traffic_detail_btn.clicked.connect(self._show_traffic_popup)
        header.addWidget(self.traffic_detail_btn)
        layout.addLayout(header)
        
        stats_row = QHBoxLayout()
        stats_row.setSpacing(15)
        
        up_col = QVBoxLayout()
        up_col.setSpacing(2)
        up_icon = QLabel("↑")
        up_icon.setStyleSheet(f"font-size: 16px; color: {C['success']}; font-weight: bold;")
        up_col.addWidget(up_icon)
        self.traffic_up = QLabel("0 B")
        self.traffic_up.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {C['success']};")
        up_col.addWidget(self.traffic_up)
        up_label = QLabel("Gönderim")
        up_label.setStyleSheet(f"font-size: 10px; color: {C['muted']};")
        up_col.addWidget(up_label)
        stats_row.addLayout(up_col)
        
        down_col = QVBoxLayout()
        down_col.setSpacing(2)
        down_icon = QLabel("↓")
        down_icon.setStyleSheet(f"font-size: 16px; color: {C['accent']}; font-weight: bold;")
        down_col.addWidget(down_icon)
        self.traffic_down = QLabel("0 B")
        self.traffic_down.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {C['accent']};")
        down_col.addWidget(self.traffic_down)
        down_label = QLabel("İndirim")
        down_label.setStyleSheet(f"font-size: 10px; color: {C['muted']};")
        down_col.addWidget(down_label)
        stats_row.addLayout(down_col)
        
        total_col = QVBoxLayout()
        total_col.setSpacing(2)
        total_icon = QLabel("⟳")
        total_icon.setStyleSheet(f"font-size: 16px; color: {C['text']}; font-weight: bold;")
        total_col.addWidget(total_icon)
        self.traffic_total = QLabel("0 B")
        self.traffic_total.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {C['text']};")
        total_col.addWidget(self.traffic_total)
        total_label = QLabel("Toplam")
        total_label.setStyleSheet(f"font-size: 10px; color: {C['muted']};")
        total_col.addWidget(total_label)
        stats_row.addLayout(total_col)
        
        stats_row.addStretch()
        layout.addLayout(stats_row)
        
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background: {C['border']};")
        layout.addWidget(separator)
        
        # Alt satir: baglanti + surecler + protokol
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(15)
        
        conn_col = QVBoxLayout()
        conn_col.setSpacing(0)
        self.traffic_conn_count = QLabel("Son 1 saatte 0 bağlantı")
        self.traffic_conn_count.setStyleSheet(f"font-size: 11px; color: {C['muted']};")
        conn_col.addWidget(self.traffic_conn_count)
        bottom_row.addLayout(conn_col)
        
        # Surecler
        proc_col = QVBoxLayout()
        proc_col.setSpacing(0)
        self.traffic_process = QLabel("")
        self.traffic_process.setStyleSheet(f"font-size: 10px; color: {C['text']};")
        proc_col.addWidget(self.traffic_process)
        bottom_row.addLayout(proc_col)
        
        # Protokol
        proto_col = QVBoxLayout()
        proto_col.setSpacing(0)
        self.traffic_proto = QLabel("")
        self.traffic_proto.setStyleSheet(f"font-size: 10px; color: {C['accent']};")
        proto_col.addWidget(self.traffic_proto)
        bottom_row.addLayout(proto_col)
        
        bottom_row.addStretch()
        layout.addLayout(bottom_row)
        
        return frame

    def _create_connections_panel(self):
        frame = QFrame()
        frame.setStyleSheet(f"background: {C['surface']}; border-radius: 8px; border: 1px solid {C['border']};")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        header = QHBoxLayout()
        title = QLabel("📊 Bağlantı Kontrol Paneli")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {C['text']};")
        header.addWidget(title)
        header.addStretch()
        
        view_all_btn = QPushButton("Tüm Bağlantılar →")
        view_all_btn.setFixedHeight(26)
        view_all_btn.setStyleSheet(f"QPushButton {{ background: {C['accent']}; color: white; border: none; border-radius: 4px; padding: 0 10px; font-size: 11px; font-weight: 600; }} QPushButton:hover {{ background: #3d7de8; }}")
        view_all_btn.clicked.connect(self._show_connections_popup)
        header.addWidget(view_all_btn)
        layout.addLayout(header)
        
        panels_row = QHBoxLayout()
        panels_row.setSpacing(10)
        
        self.freq_panel = self._make_connection_panel("En Sık Bağlanılan", "🔗", C["accent"], self._show_frequent_popup)
        self.transfer_panel = self._make_connection_panel("En Fazla Veri", "📈", C["success"], self._show_transfer_popup)
        self.ports_panel = self._make_connection_panel("Port Çeşitliliği", "🔀", C["warning"], self._show_ports_popup)
        
        panels_row.addWidget(self.freq_panel)
        panels_row.addWidget(self.transfer_panel)
        panels_row.addWidget(self.ports_panel)
        
        layout.addLayout(panels_row)
        return frame
    
    def _make_connection_panel(self, title, icon, color, click_callback):
        panel = QFrame()
        panel.setStyleSheet(f"QFrame {{ background: {C['surface2']}; border-radius: 6px; border: 1px solid {C['border']}; }}")
        panel.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        title_lbl = QLabel(f"{icon} {title}")
        title_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {C['muted']};")
        layout.addWidget(title_lbl)
        
        value_lbl = QLabel("Veri yok")
        value_lbl.setStyleSheet(f"font-size: 12px; color: {C['text']};")
        layout.addWidget(value_lbl)
        
        panel.mousePressEvent = lambda e: click_callback()
        
        if title == "En Sık Bağlanılan":
            self.freq_panel_value = value_lbl
        elif title == "En Fazla Veri":
            self.transfer_panel_value = value_lbl
        elif title == "Port Çeşitliliği":
            self.ports_panel_value = value_lbl
        
        return panel
    
    def _show_frequent_popup(self):
        popup = ConnectionsPopup(self.db, self, filter_type="frequent")
        popup.exec()
    
    def _show_transfer_popup(self):
        popup = ConnectionsPopup(self.db, self, filter_type="transfer")
        popup.exec()
    
    def _show_ports_popup(self):
        popup = ConnectionsPopup(self.db, self, filter_type="ports")
        popup.exec()

    def _create_report_panel(self):
        frame = QFrame()
        frame.setStyleSheet(f"background: {C['surface']}; border-radius: 8px; border: 1px solid {C['border']};")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        
        header = QHBoxLayout()
        title = QLabel("📋 Son AI Raporu")
        title.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {C['text']};")
        header.addWidget(title)
        header.addStretch()
        
        view_btn = QPushButton("Detay →")
        view_btn.setFixedHeight(26)
        view_btn.setStyleSheet(f"QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 0 10px; font-size: 11px; }} QPushButton:hover {{ background: {C['border']}; }}")
        view_btn.clicked.connect(self._show_report_popup)
        header.addWidget(view_btn)
        layout.addLayout(header)
        
        self.report_container = QFrame()
        self.report_container.setStyleSheet(f"""
            QFrame {{
                background: {C['surface2']};
                border-radius: 6px;
                border-left: 4px solid {C['success']};
            }}
        """)
        container_layout = QVBoxLayout(self.report_container)
        container_layout.setContentsMargins(12, 10, 12, 10)
        container_layout.setSpacing(6)
        
        risk_row = QHBoxLayout()
        risk_row.setSpacing(15)
        
        self.report_risk = QLabel("--")
        self.report_risk.setStyleSheet(f"font-size: 36px; font-weight: 700; color: {C['success']};")
        risk_row.addWidget(self.report_risk)
        
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        
        self.report_status = QLabel("Henüz rapor yok")
        self.report_status.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {C['text']};")
        info_col.addWidget(self.report_status)
        
        self.report_time = QLabel("")
        self.report_time.setStyleSheet(f"font-size: 11px; color: {C['muted']};")
        info_col.addWidget(self.report_time)
        
        risk_row.addLayout(info_col)
        risk_row.addStretch()
        container_layout.addLayout(risk_row)
        
        self.report_threats = QLabel("")
        self.report_threats.setStyleSheet(f"font-size: 11px; color: {C['muted']};")
        container_layout.addWidget(self.report_threats)
        
        self.report_summary = QLabel("")
        self.report_summary.setWordWrap(True)
        self.report_summary.setStyleSheet(f"font-size: 11px; color: {C['text']}; padding-top: 4px;")
        container_layout.addWidget(self.report_summary)
        
        self.report_iocs = QLabel("")
        self.report_iocs.setStyleSheet(f"font-size: 10px; color: {C['warning']}; padding-top: 4px;")
        container_layout.addWidget(self.report_iocs)
        
        layout.addWidget(self.report_container)
        
        return frame

    def _create_footer(self):
        frame = QFrame()
        frame.setStyleSheet(f"background: transparent; border: none;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        return frame

    def _show_connections_popup(self):
        popup = ConnectionsPopup(self.db, self)
        popup.exec()

    def _show_settings_popup(self):
        popup = SettingsPopup(self)
        popup.exec()

    def _show_blocked_popup(self):
        popup = BlockedIPsPopup(self.db, self)
        popup.exec()
        self._refresh_all()

    def _show_analysis_data(self):
        popup = AnalysisDataPopup(self.db, self.analyzer, self)
        popup.exec()

    def _show_traffic_popup(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QFrame
        dialog = QDialog(self)
        dialog.setWindowTitle("📊 Ağ Trafiği Detayları")
        dialog.setMinimumSize(700, 600)
        dialog.setStyleSheet(DARK_STYLESHEET)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(15)
        
        title = QLabel("📊 Ağ Trafiği Detayları")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {C['text']}; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Hız göstergesi
        try:
            speed = self.db.get_traffic_speed(minutes=5)
            speed_frame = QFrame()
            speed_frame.setStyleSheet(f"background: {C['surface']}; border-radius: 8px; border: 1px solid {C['border']};")
            speed_layout = QHBoxLayout(speed_frame)
            speed_layout.setContentsMargins(15, 12, 15, 12)
            
            speed_title = QLabel("⚡ Anlık Hız")
            speed_title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {C['text']};")
            speed_layout.addWidget(speed_title)
            
            speed_value = QLabel(f"{speed['total_kbs']:.1f} KB/s")
            speed_value.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {C['accent']};")
            speed_layout.addWidget(speed_value)
            
            speed_layout.addStretch()
            
            upload_speed = QLabel(f"↑ {speed['upload_kbs']:.1f} KB/s")
            upload_speed.setStyleSheet(f"font-size: 12px; color: {C['success']};")
            speed_layout.addWidget(upload_speed)
            
            download_speed = QLabel(f"↓ {speed['download_kbs']:.1f} KB/s")
            download_speed.setStyleSheet(f"font-size: 12px; color: {C['accent']};")
            speed_layout.addWidget(download_speed)
            
            layout.addWidget(speed_frame)
        except Exception:
            pass
        
        # Karşılaştırma
        try:
            comp = self.db.get_traffic_comparison()
            comp_frame = QFrame()
            comp_frame.setStyleSheet(f"background: {C['surface']}; border-radius: 8px; border: 1px solid {C['border']};")
            comp_layout = QVBoxLayout(comp_frame)
            comp_layout.setContentsMargins(15, 12, 15, 12)
            
            comp_title = QLabel("📈 Karşılaştırma")
            comp_title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {C['text']};")
            comp_layout.addWidget(comp_title)
            
            # Bugün vs Dün
            today_change = comp.get("today_change", 0)
            today_color = C["success"] if today_change < 0 else C["danger"]
            today_arrow = "↓" if today_change < 0 else "↑"
            today_text = QLabel(f"Bugün vs Dün: <span style='color:{today_color};font-weight:700;'>{today_arrow}{abs(today_change)}%</span>")
            today_text.setStyleSheet(f"font-size: 12px; color: {C['text']};")
            comp_layout.addWidget(today_text)
            
            # Bu hafta vs Geçen hafta
            week_change = comp.get("week_change", 0)
            week_color = C["success"] if week_change < 0 else C["danger"]
            week_arrow = "↓" if week_change < 0 else "↑"
            week_text = QLabel(f"Bu hafta vs Geçen hafta: <span style='color:{week_color};font-weight:700;'>{week_arrow}{abs(week_change)}%</span>")
            week_text.setStyleSheet(f"font-size: 12px; color: {C['text']};")
            comp_layout.addWidget(week_text)
            
            layout.addWidget(comp_frame)
        except Exception:
            pass
        
        traffic = self.db.get_traffic_stats()
        
        if traffic:
            for period_key in ["Bugün", "Bu Hafta", "Bu Ay"]:
                period_data = traffic[1] if period_key == "Bugün" else traffic[2] if period_key == "Bu Hafta" else traffic[3]
                if not period_data:
                    continue
                    
                period_frame = QFrame()
                period_frame.setStyleSheet(f"background: {C['surface']}; border-radius: 8px; border: 1px solid {C['border']};")
                period_layout = QVBoxLayout(period_frame)
                period_layout.setContentsMargins(15, 12, 15, 12)
                period_layout.setSpacing(8)
                
                period_title = QLabel(f"📅 {period_key}")
                period_title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {C['text']};")
                period_layout.addWidget(period_title)
                
                upload_bytes = period_data.get('upload', 0)
                download_bytes = period_data.get('download', 0)
                total_bytes = period_data.get('total', 0)
                conn_count = period_data.get('conn_count', 0)
                
                stats_grid = QLabel(
                    f"<span style='color:{C['success']};'>↑ Gönderim:</span> {self._format_bytes(upload_bytes)} &nbsp;&nbsp;"
                    f"<span style='color:{C['accent']};'>↓ İndirim:</span> {self._format_bytes(download_bytes)} &nbsp;&nbsp;"
                    f"<span style='color:{C['text']};'>⟳ Toplam:</span> {self._format_bytes(total_bytes)}<br>"
                    f"<span style='color:{C['muted']};'>📡 Bağlantı:</span> {conn_count:,}"
                )
                stats_grid.setStyleSheet(f"font-size: 12px; color: {C['text']};")
                period_layout.addWidget(stats_grid)
                
                layout.addWidget(period_frame)
        else:
            info = QLabel("Henüz trafik verisi bulunmuyor.")
            info.setStyleSheet(f"color: {C['muted']}; font-size: 13px;")
            layout.addWidget(info)
        
        # Süreçler bölümü
        try:
            procs = self.db.get_top_processes(hours=24, limit=5)
            if procs:
                proc_frame = QFrame()
                proc_frame.setStyleSheet(f"background: {C['surface']}; border-radius: 8px; border: 1px solid {C['border']};")
                proc_layout = QVBoxLayout(proc_frame)
                proc_layout.setContentsMargins(15, 12, 15, 12)
                
                proc_title = QLabel("🔃 En Fazla Trafik Yapan Süreçler (24s)")
                proc_title.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {C['text']};")
                proc_layout.addWidget(proc_title)
                
                for p in procs:
                    proc_row = QLabel(
                        f"• {p['process']}: {self._format_bytes(p['total_bytes'])} ({p['conn_count']} bağlantı)"
                    )
                    proc_row.setStyleSheet(f"font-size: 11px; color: {C['muted']};")
                    proc_layout.addWidget(proc_row)
                
                layout.addWidget(proc_frame)
        except Exception:
            pass
        
        close_btn = QPushButton("Kapat")
        close_btn.setFixedSize(100, 36)
        close_btn.setStyleSheet(f"QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 6px; }} QPushButton:hover {{ background: {C['border']}; }}")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        dialog.exec()

    def _show_report_popup(self):
        popup = ReportPopup(self.db, self)
        popup.exec()

    def _run_quick_analysis(self):
        self.status_label.setText("● Analiz çalışıyor...")
        self.quick_analyze_btn.setEnabled(False)
        self.quick_analyze_btn.setText("⏳ Çalışıyor...")
        def done():
            self._refresh_all()
            self.status_label.setText("● Analiz tamamlandı")
            self.quick_analyze_btn.setEnabled(True)
            self.quick_analyze_btn.setText("⚡ Analiz")
        self._worker = AnalysisWorker(self.analyzer)
        self._worker.finished.connect(done)
        self._worker.start()

    def _refresh_all(self):
        try:
            stats = self.db.get_stats()
            self._update_card(self.card_conns, f"{stats['today_connections']:,}")
            self._update_card(self.card_threats, str(stats['total_threats']))
            self._update_card(self.card_blocked, str(stats['blocked_ips']))
            self._update_card(self.card_reports, str(stats['total_reports']))
            
            # Trafik istatistiklerini güncelle
            try:
                traffic = self.db.get_traffic_stats()
                if traffic:
                    today = traffic[1]  # "Bugün"
                    upload_bytes = today.get('upload', 0)
                    download_bytes = today.get('download', 0)
                    total_bytes = today.get('total', 0)
                    
                    self.traffic_up.setText(self._format_bytes(upload_bytes))
                    self.traffic_down.setText(self._format_bytes(download_bytes))
                    self.traffic_total.setText(self._format_bytes(total_bytes))
                    
                    conn_count = today.get('conn_count', 0)
                    self.traffic_conn_count.setText(f"Son 1 saatte {conn_count:,} bağlantı")
                
                # Yeni: Hız göstergesi
                speed = self.db.get_traffic_speed(minutes=5)
                self.traffic_speed.setText(f"⚡ {speed['total_kbs']:.1f} KB/s")
                
                # Yeni: Karşılaştırma (bugün vs dün)
                comp = self.db.get_traffic_comparison()
                if comp.get("today_change", 0) != 0:
                    change = comp["today_change"]
                    color = C["success"] if change < 0 else C["danger"]
                    arrow = "↓" if change < 0 else "↑"
                    self.traffic_comparison.setText(f"{arrow}{abs(change)}% vs dün")
                    self.traffic_comparison.setStyleSheet(f"font-size: 10px; color: {color}; font-weight: 600;")
                
                # Yeni: Süreçler
                procs = self.db.get_top_processes(hours=1, limit=2)
                if procs:
                    proc_text = " • ".join([f"{p['process'][:10]}" for p in procs])
                    self.traffic_process.setText(f"🔃 {proc_text}")
                
                # Yeni: Protokol dağılımı
                protos = self.db.get_protocol_distribution(hours=24)
                if protos:
                    # En çok kullanılan protokolü göster
                    top_proto = max(protos.items(), key=lambda x: x[1]["count"])
                    self.traffic_proto.setText(f"🌐 {top_proto[0]}: {top_proto[1]['percentage']:.0f}%")
                    
            except Exception as e:
                print(f"Traffic refresh error: {e}")
            
            # Bağlantı kontrol paneli verilerini güncelle (VirusTotal olmadan - performans için)
            try:
                frequent = self.db.get_frequent_connections(hours=1, limit=10)
                transfer = self.db.get_top_transfer_connections(hours=1, limit=10)
                ports = self.db.get_diverse_port_connections(hours=1, limit=10)
                
                def get_ip_display(ip):
                    domain = dns_cache.resolve(ip)
                    if domain and domain != "...":
                        return f"{ip} ({domain})"
                    elif domain == "...":
                        return f"{ip}"
                    return ip
                
                freq_text = "<br>".join([f"{get_ip_display(r.get('dst_ip',''))} - {r.get('conn_count',0)} bağl." for r in frequent]) if frequent else "Veri yok"
                self.freq_panel_value.setText(freq_text)
                
                transfer_text = "<br>".join([f"{get_ip_display(r.get('dst_ip',''))} - {self._format_bytes(r.get('total_bytes',0))}" for r in transfer]) if transfer else "Veri yok"
                self.transfer_panel_value.setText(transfer_text)
                
                ports_text = "<br>".join([f"{get_ip_display(r.get('dst_ip',''))} - {r.get('port_count',0)} port" for r in ports]) if ports else "Veri yok"
                self.ports_panel_value.setText(ports_text)
            except Exception as e:
                print(f"Connection panel refresh error: {e}")
            
            # Son raporu güncelle
            report = self.db.get_latest_report()
            if report:
                score = report.get('risk_score', 0)
                self.report_risk.setText(f"{score:.1f}")
                
                if score < 3:
                    color = C['success']
                    status = "🟢 Güvenli"
                    border_color = C['success']
                elif score < 6:
                    color = C['warning']
                    status = "🟡 Normal"
                    border_color = C['warning']
                elif score < 8:
                    color = C['danger']
                    status = "🟠 Dikkat!"
                    border_color = C['danger']
                else:
                    color = "#ff0000"
                    status = "🔴 Kritik!"
                    border_color = "#ff0000"
                
                self.report_risk.setStyleSheet(f"font-size: 36px; font-weight: 700; color: {color};")
                self.report_status.setText(status)
                self.report_container.setStyleSheet(f"""
                    QFrame {{
                        background: {C['surface2']};
                        border-radius: 6px;
                        border-left: 4px solid {border_color};
                    }}
                """)
                
                ts = report.get('created_at', '')[:16].replace('T', ' ')
                self.report_time.setText(f"Son: {ts}")
                
                content = report.get('content', '{}')
                try:
                    data = json.loads(content)
                except:
                    data = {}
                
                suspicious = data.get('suspicious_connections', [])
                threat_count = len(suspicious)
                self.report_threats.setText(f"⚠️ {threat_count} şüpheli bağlantı tespit edildi")
                
                summary = data.get('summary', '')
                if summary:
                    short_summary = summary[:120] + "..." if len(summary) > 120 else summary
                    self.report_summary.setText(short_summary)
                else:
                    self.report_summary.setText("")
                
                iocs = data.get('iocs', [])
                if iocs:
                    ioc_text = " | ".join(iocs[:3])
                    self.report_iocs.setText(f"IOC: {ioc_text}")
                else:
                    self.report_iocs.setText("")
            else:
                self.report_risk.setText("--")
                self.report_risk.setStyleSheet(f"font-size: 36px; font-weight: 700; color: {C['muted']};")
                self.report_status.setText("Henüz rapor yok")
                self.report_time.setText("")
                self.report_threats.setText("")
                self.report_summary.setText("")
                self.report_iocs.setText("")
                self.report_container.setStyleSheet(f"""
                    QFrame {{
                        background: {C['surface2']};
                        border-radius: 6px;
                        border-left: 4px solid {C['muted']};
                    }}
                """)
        except Exception as e:
            print(f"Refresh error: {e}")

    def _update_card(self, card, value):
        card.layout().itemAt(0).widget().setText(value)

    def _format_bytes(self, bytes_val):
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024*1024:
            return f"{bytes_val/1024:.1f} KB"
        elif bytes_val < 1024*1024*1024:
            return f"{bytes_val/(1024*1024):.1f} MB"
        else:
            return f"{bytes_val/(1024*1024*1024):.2f} GB"

    def _setup_tray(self):
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setBrush(QBrush(QColor(C["accent"])))
        painter.drawEllipse(2, 2, 28, 28)
        painter.end()
        self.tray = QSystemTrayIcon(QIcon(pix), self)
        menu = QMenu()
        show_action = QAction("AgTara'yı Göster", self)
        show_action.triggered.connect(self.showNormal)
        menu.addAction(show_action)
        analyze_action = QAction("⚡ Hızlı Analiz", self)
        analyze_action.triggered.connect(self._run_quick_analysis)
        menu.addAction(analyze_action)
        menu.addSeparator()
        quit_action = QAction("❌ Çıkış", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("AgTara — Ağ Koruması Aktif")
        self.tray.activated.connect(lambda reason: self.showNormal() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

    def _setup_timer(self):
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_all)
        self._refresh_timer.start(60000)

    def closeEvent(self, event):
        from config import load_settings
        settings = load_settings()
        minimize_to_tray = settings.get("MINIMIZE_TO_TRAY", True)
        
        if minimize_to_tray:
            event.ignore()
            self.hide()
            self.tray.showMessage("AgTara Arka Planda", "İzleme devam ediyor.", QSystemTrayIcon.MessageIcon.Information, 3000)
        else:
            self._quit()

    def _quit(self):
        self.engine.stop()
        self.scheduler.stop()
        self.tray.hide()
        QApplication.quit()


# ─── Popup Diyaloglar ─────────────────────────────────────────────────

class ConnectionsPopup(QDialog):
    def __init__(self, db, parent=None, filter_type="recent"):
        super().__init__(parent)
        self.db = db
        self.filter_type = filter_type
        titles = {
            "recent": "Tüm Bağlantılar",
            "frequent": "En Sık Bağlanılan",
            "transfer": "En Fazla Veri Transferi",
            "ports": "Port Çeşitliliği"
        }
        self.setWindowTitle(f"📡 {titles.get(filter_type, 'Bağlantılar')}")
        self.setMinimumSize(950, 650)
        self.setStyleSheet(DARK_STYLESHEET)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)
        
        # Başlık
        titles = {
            "recent": "Tüm Bağlantılar",
            "frequent": "En Sık Bağlanılan IP'ler",
            "transfer": "En Fazla Veri Transferi",
            "ports": "Port Çeşitliliği"
        }
        title = QLabel(f"📡 {titles.get(self.filter_type, 'Bağlantılar')}")
        title.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {C['text']};")
        layout.addWidget(title)
        
        # Filtre satırı
        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 IP, port veya süreç ara...")
        self.search_box.setFixedHeight(34)
        self.search_box.textChanged.connect(self._filter)
        filter_row.addWidget(self.search_box, 2)
        
        self.protocol_filter = QComboBox()
        self.protocol_filter.addItems(["Tümü", "TCP", "UDP", "OTHER"])
        self.protocol_filter.setFixedHeight(34)
        self.protocol_filter.currentTextChanged.connect(self._filter)
        
        prot_lbl = QLabel("Protokol:")
        prot_lbl.setStyleSheet(f"color: {C['muted']};")
        filter_row.addWidget(prot_lbl)
        filter_row.addWidget(self.protocol_filter)
        filter_row.addStretch()
        
        layout.addLayout(filter_row)
        
        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["Zaman", "Kaynak IP", "Hedef IP", "Port", "Protokol", "Veri (KB)", "Süreç", "Eylem"])
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{ 
                background: {C['surface2']}; 
                border-radius: 8px; 
                gridline-color: {C['border']};
            }}
            QHeaderView::section {{
                background: {C['surface']};
                color: {C['muted']};
                padding: 8px;
                border: none;
                font-weight: 600;
            }}
        """)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        
        # Sayfalama
        page_row = QHBoxLayout()
        page_row.addStretch()
        
        self.prev_btn = QPushButton("◀ Önceki")
        self.prev_btn.setFixedHeight(34)
        self.prev_btn.setStyleSheet(f"QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 6px; padding: 0 15px; }} QPushButton:hover {{ background: {C['border']}; }}")
        self.prev_btn.clicked.connect(lambda: self._change_page(-1))
        
        self.page_label = QLabel("Sayfa 1")
        self.page_label.setStyleSheet(f"color: {C['muted']}; min-width: 80px;")
        
        self.next_btn = QPushButton("Sonraki ▶")
        self.next_btn.setFixedHeight(34)
        self.next_btn.setStyleSheet(f"QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 6px; padding: 0 15px; }} QPushButton:hover {{ background: {C['border']}; }}")
        self.next_btn.clicked.connect(lambda: self._change_page(1))
        
        page_row.addWidget(self.prev_btn)
        page_row.addWidget(self.page_label)
        page_row.addWidget(self.next_btn)
        page_row.addStretch()
        
        layout.addLayout(page_row)
        
        self._page = 0
        self._page_size = 50

    def _load_data(self):
        if self.filter_type == "frequent":
            rows = self.db.get_frequent_connections(hours=24, limit=100)
        elif self.filter_type == "transfer":
            rows = self.db.get_top_transfer_connections(hours=24, limit=100)
        elif self.filter_type == "ports":
            rows = self.db.get_diverse_port_connections(hours=24, limit=100)
        else:
            rows = self.db.get_recent_connections(limit=self._page_size, offset=self._page * self._page_size)
        self._populate_table(rows)

    def _populate_table(self, rows):
        self.table.setRowCount(0)
        for row in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            ts = row.get('timestamp', '')[:19].replace('T', ' ')
            self.table.setItem(r, 0, QTableWidgetItem(ts))
            self.table.setItem(r, 1, QTableWidgetItem(row.get('src_ip', '')))
            self.table.setItem(r, 2, QTableWidgetItem(row.get('dst_ip', '')))
            self.table.setItem(r, 3, QTableWidgetItem(str(row.get('dst_port', ''))))
            self.table.setItem(r, 4, QTableWidgetItem(row.get('protocol', '')))
            self.table.setItem(r, 5, QTableWidgetItem(f"{row.get('bytes', 0)/1024:.1f}"))
            self.table.setItem(r, 6, QTableWidgetItem(row.get('process', '')))
            btn = QPushButton("Engelle")
            btn.setFixedSize(70, 28)
            btn.setStyleSheet(f"QPushButton {{ background: {C['danger']}; color: white; border: none; border-radius: 4px; font-size: 11px; }} QPushButton:hover {{ background: #dc2626; }}")
            btn.clicked.connect(lambda _, ip=row.get('dst_ip'): self._block_ip(ip))
            self.table.setCellWidget(r, 7, btn)

    def _filter(self):
        text = self.search_box.text().lower()
        proto = self.protocol_filter.currentText()
        rows = self.db.get_recent_connections(limit=200)
        filtered = [r for r in rows if ((not text or text in str(r.get('dst_ip','')).lower() or text in str(r.get('process','')).lower()) and (proto == "Tümü" or r.get('protocol') == proto))]
        self._populate_table(filtered[:50])

    def _change_page(self, delta):
        self._page += delta
        if self._page < 0: self._page = 0
        self._load_data()
        self.page_label.setText(f"Sayfa {self._page + 1}")

    def _block_ip(self, ip):
        from kill_switch import block_ip
        from notifier import notify_ip_blocked
        ok = block_ip(ip, "GUI'den engellendi", self.db)
        if ok:
            notify_ip_blocked(ip)
            self._load_data()


class SettingsPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Ayarlar")
        self.setMinimumSize(800, 900)
        self.setStyleSheet(DARK_STYLESHEET)
        self._setup_ui()
        self._load_settings()
        self._load_prompt()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)
        
        header = QLabel("⚙️ Ayarlar")
        header.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {C['text']};")
        layout.addWidget(header)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {C['surface']}; }}")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background: {C['surface']};")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(1)
        
        left_widget = QWidget()
        left_widget.setStyleSheet(f"background: {C['surface']};")
        left_column = QVBoxLayout(left_widget)
        left_column.setContentsMargins(5, 5, 5, 5)
        left_column.setSpacing(10)
        
        group_style = f"""
            QGroupBox {{
                font-weight: 600;
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 10px;
                background: {C['surface']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
            }}
        """
        
        settings_group = QGroupBox("📋 Genel Ayarlar")
        settings_group.setStyleSheet(group_style)
        settings_layout = QFormLayout()
        settings_layout.setSpacing(10)
        settings_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.provider_combo = QComboBox()
        self.provider_combo.setFixedHeight(34)
        self.provider_combo.addItems(["openrouter", "gemini"])
        self.provider_combo.setStyleSheet(f"QComboBox {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 5px; }}")
        settings_layout.addRow("🤖 AI Sağlayıcı:", self.provider_combo)
        
        self.api_key = QLineEdit()
        self.api_key.setFixedHeight(34)
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("API Key...")
        self.api_key.setStyleSheet(f"QLineEdit {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 5px; }}")
        settings_layout.addRow("🔑 API Key:", self.api_key)
        
        settings_group.setLayout(settings_layout)
        left_column.addWidget(settings_group)
        
        security_group = QGroupBox("🛡️ Güvenlik")
        security_group.setStyleSheet(group_style)
        security_layout = QFormLayout()
        security_layout.setSpacing(10)
        
        self.auto_block_cb = QCheckBox("Otomatik IP engelleme (AI önerdiğinde)")
        self.auto_block_cb.setStyleSheet(f"QCheckBox {{ color: {C['text']}; spacing: 8px; }}")
        security_layout.addRow("", self.auto_block_cb)
        
        security_group.setLayout(security_layout)
        left_column.addWidget(security_group)
        
        system_group = QGroupBox("🚀 Sistem")
        system_group.setStyleSheet(group_style)
        system_layout = QFormLayout()
        system_layout.setSpacing(10)
        
        self.autostart_cb = QCheckBox("Windows'ta otomatik başlat")
        self.autostart_cb.setStyleSheet(f"QCheckBox {{ color: {C['text']}; spacing: 8px; }}")
        system_layout.addRow("", self.autostart_cb)
        
        self.minimize_to_tray_cb = QCheckBox("Kapatılınca sistem tepsisine küçült")
        self.minimize_to_tray_cb.setStyleSheet(f"QCheckBox {{ color: {C['text']}; spacing: 8px; }}")
        system_layout.addRow("", self.minimize_to_tray_cb)
        
        self.interface_combo = QComboBox()
        self.interface_combo.setFixedHeight(34)
        self.interface_combo.addItem("Tüm ağ arayüzleri", None)
        self.interface_combo.setStyleSheet(f"QComboBox {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 5px; }}")
        system_layout.addRow("🌐 Ağ Arayüzü:", self.interface_combo)
        
        system_group.setLayout(system_layout)
        left_column.addWidget(system_group)
        
        main_splitter.addWidget(left_widget)
        
        right_widget = QWidget()
        right_widget.setStyleSheet(f"background: {C['surface']};")
        right_column = QVBoxLayout(right_widget)
        right_column.setContentsMargins(5, 5, 5, 5)
        right_column.setSpacing(10)
        
        prompt_group = QGroupBox("🤖 AI Analiz Prompt'u")
        prompt_group.setStyleSheet(group_style)
        prompt_layout = QVBoxLayout()
        prompt_layout.setSpacing(10)
        
        prompt_desc = QLabel("AI'nin ağ trafiğini analiz ederken kullandığı talimatlar.")
        prompt_desc.setStyleSheet(f"color: {C['muted']}; font-size: 11px; margin-bottom: 5px;")
        prompt_desc.setWordWrap(True)
        prompt_layout.addWidget(prompt_desc)
        
        self.prompt_text = QTextEdit()
        self.prompt_text.setPlaceholderText("AI prompt'u buraya...")
        self.prompt_text.setStyleSheet(f"""
            QTextEdit {{
                background: {C['surface2']};
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                padding: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }}
        """)
        self.prompt_text.setMinimumHeight(400)
        prompt_layout.addWidget(self.prompt_text)
        
        prompt_btn_row = QHBoxLayout()
        prompt_btn_row.addStretch()
        
        reset_btn = QPushButton("Varsayılana Sıfırla")
        reset_btn.setFixedHeight(34)
        reset_btn.setStyleSheet(f"QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 4px; padding: 0 12px; }} QPushButton:hover {{ background: {C['border']}; }}")
        reset_btn.clicked.connect(self._reset_prompt)
        prompt_btn_row.addWidget(reset_btn)
        
        prompt_layout.addLayout(prompt_btn_row)
        
        prompt_group.setLayout(prompt_layout)
        right_column.addWidget(prompt_group)
        
        main_splitter.addWidget(right_widget)
        
        main_splitter.setSizes([350, 450])
        
        scroll_layout.addWidget(main_splitter)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        close_btn = QPushButton("İptal")
        close_btn.setFixedSize(100, 36)
        close_btn.setStyleSheet(f"QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 6px; }} QPushButton:hover {{ background: {C['border']}; }}")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        
        save_btn = QPushButton("Kaydet")
        save_btn.setFixedSize(100, 40)
        save_btn.setStyleSheet(f"QPushButton {{ background: {C['accent']}; color: white; border: none; border-radius: 6px; font-weight: 600; }} QPushButton:hover {{ background: #3d7de8; }}")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        
        layout.addLayout(btn_row)

    def _load_settings(self):
        from config import load_settings
        settings = load_settings()
        self.minimize_to_tray_cb.setChecked(settings.get("MINIMIZE_TO_TRAY", True))
        self.auto_block_cb.setChecked(settings.get("AUTO_BLOCK_ENABLED", False))
        self.autostart_cb.setChecked(settings.get("autostart", False))
        interface_data = settings.get("interface")
        if interface_data is not None:
            for i in range(self.interface_combo.count()):
                if self.interface_combo.itemData(i) == interface_data:
                    self.interface_combo.setCurrentIndex(i)
                    break
        
        # AI Sağlayıcı ayarlarını yükle
        import config as cfg
        import importlib
        importlib.reload(cfg)
        
        # Provider'ı seç
        idx = self.provider_combo.findText(cfg.AI_PROVIDER)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        
        # API key'leri yükle
        if cfg.AI_PROVIDER == "openrouter":
            self.api_key.setText(cfg.OPENROUTER_API_KEY or "")
        else:
            self.api_key.setText(cfg.GEMINI_API_KEY or "")

    def _load_prompt(self):
        from config import get_ai_prompt, DEFAULT_SYSTEM_PROMPT
        try:
            prompt = get_ai_prompt()
            self.prompt_text.setText(prompt)
        except:
            self.prompt_text.setText(DEFAULT_SYSTEM_PROMPT)

    def _reset_prompt(self):
        from config import DEFAULT_SYSTEM_PROMPT
        self.prompt_text.setText(DEFAULT_SYSTEM_PROMPT)

    def _save(self):
        try:
            from config import save_settings, save_ai_prompt, load_settings
            import importlib
            import re
            
            # Mevcut ayarları yükle
            settings = load_settings()
            settings["MINIMIZE_TO_TRAY"] = self.minimize_to_tray_cb.isChecked()
            settings["AUTO_BLOCK_ENABLED"] = self.auto_block_cb.isChecked()
            settings["autostart"] = self.autostart_cb.isChecked()
            settings["interface"] = self.interface_combo.currentData()
            save_settings(settings)
            
            # AI Sağlayıcı ayarlarını config.py'ye kaydet
            provider = self.provider_combo.currentText()
            api_key = self.api_key.text().strip()
            
            # config.py dosyasını oku
            import pathlib
            config_path = pathlib.Path("config.py")
            text = config_path.read_text(encoding="utf-8")
            
            # Provider değiştir
            text = re.sub(
                r'^(AI_PROVIDER\s*=\s*)"[^"]*"',
                f'\\1"{provider}"',
                text,
                flags=re.MULTILINE
            )
            
            # API key değiştir
            if provider == "openrouter":
                text = re.sub(
                    r'^(OPENROUTER_API_KEY\s*=\s*)"[^"]*"',
                    f'\\1"{api_key}"',
                    text,
                    flags=re.MULTILINE
                )
            else:
                text = re.sub(
                    r'^(GEMINI_API_KEY\s*=\s*)"[^"]*"',
                    f'\\1"{api_key}"',
                    text,
                    flags=re.MULTILINE
                )
            
            config_path.write_text(text, encoding="utf-8")
            
            # Modülü yeniden yükle
            import config
            importlib.reload(config)
            
            prompt = self.prompt_text.toPlainText()
            if prompt.strip():
                save_ai_prompt(prompt)
        except Exception as e:
            print(f"Ayar kaydetme hatası: {e}")
            QMessageBox.warning(self, "⚠️ Hata", f"Ayarlar kaydedilirken hata oluştu:\n{e}")
            return
        
        QMessageBox.information(self, "✅ Başarılı", "Ayarlar kaydedildi.\n\nNot: AI prompt değişiklikleri bir sonraki analizde geçerli olacaktır.")
        self.accept()


class AnalysisDataPopup(QDialog):
    def __init__(self, db, analyzer, parent=None):
        super().__init__(parent)
        self.db = db
        self.analyzer = analyzer
        self.setWindowTitle("📤 AI Analiz Verileri")
        self.setMinimumSize(900, 700)
        self.setStyleSheet(DARK_STYLESHEET)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)
        
        # Başlık
        header = QLabel("📤 AI'a Gönderilen Veriler")
        header.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {C['text']};")
        layout.addWidget(header)
        
        # Sekmeler
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::paddle {{ border: 1px solid {C['border']}; }}
            QTabBar::tab {{
                background: {C['surface']};
                color: {C['muted']};
                padding: 8px 16px;
                border: 1px solid {C['border']};
                border-bottom: none;
            }}
            QTabBar::tab:selected {{
                background: {C['surface2']};
                color: {C['text']};
            }}
            QTabBar::tab:hover {{ color: {C['text']}; }}
        """)
        
        # Sekme 1: Genel Bilgi
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        info_layout.setSpacing(10)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet(f"""
            QTextEdit {{
                background: {C['surface2']};
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                padding: 10px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }}
        """)
        info_layout.addWidget(self.info_text)
        
        tabs.addTab(info_tab, "📋 Bilgi")
        
        # Sekme 2: Veri Tablosu
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_layout.setSpacing(8)
        
        data_header = QLabel("Gönderilen Bağlantı Kayıtları:")
        data_header.setStyleSheet(f"font-weight: 600; color: {C['text']};")
        data_layout.addWidget(data_header)
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels(["IP", "Port", "Protokol", "Süreç", "Bağlantı", "Toplam Byte", "Şüpheli"])
        self.data_table.setStyleSheet(f"""
            QTableWidget {{
                background: {C['surface']};
                gridline-color: {C['border']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                color: {C['text']};
            }}
            QTableWidget::item {{ padding: 6px; }}
            QHeaderView::section {{
                background: {C['surface2']};
                color: {C['muted']};
                border: none;
                border-bottom: 1px solid {C['border']};
                padding: 6px;
                font-weight: 600;
                font-size: 11px;
            }}
        """)
        self.data_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.data_table.verticalHeader().setVisible(False)
        data_layout.addWidget(self.data_table, 1)
        
        tabs.addTab(data_tab, "📊 Veri Tablosu")
        
        # Sekme 3: Prompt
        prompt_tab = QWidget()
        prompt_layout = QVBoxLayout(prompt_tab)
        
        self.prompt_text = QTextEdit()
        self.prompt_text.setReadOnly(True)
        self.prompt_text.setStyleSheet(f"""
            QTextEdit {{
                background: {C['surface2']};
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                padding: 10px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }}
        """)
        prompt_layout.addWidget(self.prompt_text)
        
        tabs.addTab(prompt_tab, "🤖 Prompt")
        
        # Sekme 4: Ham Yanıt
        raw_tab = QWidget()
        raw_layout = QVBoxLayout(raw_tab)
        
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setStyleSheet(f"""
            QTextEdit {{
                background: {C['surface2']};
                color: {C['text']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                padding: 10px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }}
        """)
        raw_layout.addWidget(self.raw_text)
        
        tabs.addTab(raw_tab, "🔍 Ham Yanıt")
        
        layout.addWidget(tabs, 1)
        
        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        run_btn = QPushButton("🚀 Analizi Çalıştır")
        run_btn.setFixedSize(160, 40)
        run_btn.setStyleSheet(f"QPushButton {{ background: {C['accent']}; color: white; border: none; border-radius: 6px; font-weight: 600; }} QPushButton:hover {{ background: #3d7de8; }}")
        run_btn.clicked.connect(self._run_analysis)
        btn_row.addWidget(run_btn)
        
        close_btn = QPushButton("Kapat")
        close_btn.setFixedSize(100, 40)
        close_btn.setStyleSheet(f"QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 6px; }} QPushButton:hover {{ background: {C['border']}; }}")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        
        layout.addLayout(btn_row)

    def _load_data(self):
        report = self.db.get_latest_report()
        
        if report:
            content = report.get('content', '{}')
            try:
                data = json.loads(content)
            except:
                data = {}
            
            info = f"""
╔══════════════════════════════════════════════════════════════╗
║                    ANALİZ BİLGİLERİ                           ║
╠══════════════════════════════════════════════════════════════╣
║ Tarih:          {report.get('created_at', '')[:19].replace('T', ' '):<45}║
║ Risk Skoru:     {report.get('risk_score', 0):<45}║
║ Durum:          {report.get('status', 'Bilinmiyor'):<45}║
╠══════════════════════════════════════════════════════════════╣
║ Gönderilen Kayıt: {data.get('records_sent', 0):<41}║
║ Yeni Bağlantı:    {data.get('new_connections', 0):<41}║
║ Dönem:            {data.get('period', '-'):<45}║
╠══════════════════════════════════════════════════════════════╣
║                    TEHDİT ÖZETİ                               ║
╠══════════════════════════════════════════════════════════════╣
{('║ ' + data.get('summary', 'Yok')[:58].replace(chr(10), ' ') + ' ║') if data.get('summary') else '║ Yok ║'}
╚══════════════════════════════════════════════════════════════╝
"""
            self.info_text.setText(info)
            
            suspicious = data.get('suspicious_connections', [])
            traffic = data.get('traffic_summary', [])
            
            self.data_table.setRowCount(0)
            for row in traffic:
                r = self.data_table.rowCount()
                self.data_table.insertRow(r)
                self.data_table.setItem(r, 0, QTableWidgetItem(row.get('dst_ip', '')))
                self.data_table.setItem(r, 1, QTableWidgetItem(str(row.get('dst_port', ''))))
                self.data_table.setItem(r, 2, QTableWidgetItem(row.get('protocol', '')))
                self.data_table.setItem(r, 3, QTableWidgetItem(row.get('process', '')))
                self.data_table.setItem(r, 4, QTableWidgetItem(str(row.get('conn_count', 1))))
                self.data_table.setItem(r, 5, QTableWidgetItem(str(row.get('total_bytes', 0))))
                is_suspicious = "⚠️" if row.get('is_suspicious_port') or row.get('is_high_traffic') else ""
                self.data_table.setItem(r, 6, QTableWidgetItem(is_suspicious))
            
            self.raw_text.setText(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            self.info_text.setText("Henüz analiz raporu bulunmuyor.\n\nAnaliz çalıştırarak verileri görebilirsiniz.")
            self.data_table.setRowCount(0)
            self.raw_text.setText("")
        
        from config import get_ai_prompt
        self.prompt_text.setText(get_ai_prompt())

    def _run_analysis(self):
        self.close()
        from PyQt6.QtCore import QTimer
        from app_gui import MainWindow
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, MainWindow):
                widget._run_quick_analysis()
                break


class ReportPopup(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("AI Raporu")
        self.setMinimumSize(600, 450)
        self.setStyleSheet(DARK_STYLESHEET)
        self._setup_ui()
        self._load_report()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        title = QLabel("📊 AI Güvenlik Raporu")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {C['text']};")
        layout.addWidget(title)
        self.content = QTextBrowser()
        self.content.setStyleSheet(f"QTextBrowser {{ background: {C['surface2']}; border-radius: 8px; color: {C['text']}; }}")
        layout.addWidget(self.content, 1)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Kapat")
        close_btn.setFixedSize(100, 36)
        close_btn.setStyleSheet(f"QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 6px; }}")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _load_report(self):
        report = self.db.get_latest_report()
        if not report:
            self.content.setHtml("<p style='color: #94a3b8;'>Henüz rapor bulunmuyor.</p>")
            return
        content = report.get('content', '{}')
        try:
            data = json.loads(content)
        except:
            data = {}
        risk = report.get('risk_score', 0)
        status = report.get('status', 'Bilinmiyor')
        color = C['success'] if risk < 3 else C['warning'] if risk < 6 else C['danger']
        html = f"<div style='padding: 10px;'><h2 style='color: {color};'>Risk Skoru: {risk}/10</h2><p><b>Durum:</b> {status}</p><p><b>Tarih:</b> {report.get('created_at', '')[:19].replace('T', ' ')}</p><hr style='border-color: {C['border']};'><h3>Özet</h3><p>{data.get('summary', 'Yok')}</p></div>"
        self.content.setHtml(html)


class BlockedIPsPopup(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("🚫 Engellenen IP'ler")
        self.setMinimumSize(650, 550)
        self.setStyleSheet(DARK_STYLESHEET)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(15)
        
        title = QLabel("🚫 Engellenen IP'ler")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {C['text']};")
        layout.addWidget(title)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["IP Adresi", "Sebep", "Tarih", "İşlem"])
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {C['surface']};
                gridline-color: {C['border']};
                border: 1px solid {C['border']};
                border-radius: 8px;
                color: {C['text']};
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid {C['border']};
            }}
            QHeaderView::section {{
                background: {C['surface2']};
                color: {C['muted']};
                border: none;
                border-bottom: 1px solid {C['border']};
                padding: 10px 8px;
                font-weight: 600;
                font-size: 12px;
            }}
        """)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setRowHeight(0, 36)
        layout.addWidget(self.table, 1)
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        close_btn = QPushButton("Kapat")
        close_btn.setFixedSize(120, 40)
        close_btn.setStyleSheet(f"QPushButton {{ background: {C['surface2']}; color: {C['text']}; border: 1px solid {C['border']}; border-radius: 6px; font-size: 12px; }} QPushButton:hover {{ background: {C['border']}; }}")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        
        layout.addLayout(btn_row)

    def _load_data(self):
        blocked = self.db.get_blocked_ips()
        self.table.setRowCount(0)
        for entry in blocked:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            ip_item = QTableWidgetItem(entry.get('ip', ''))
            ip_item.setForeground(QColor(C['danger']))
            self.table.setItem(row, 0, ip_item)
            
            reason_item = QTableWidgetItem(entry.get('reason', '-'))
            self.table.setItem(row, 1, reason_item)
            
            date_item = QTableWidgetItem(entry.get('blocked_at', '')[:19].replace('T', ' '))
            date_item.setForeground(QColor(C['muted']))
            self.table.setItem(row, 2, date_item)
            
            remove_btn = QPushButton("Kaldır")
            remove_btn.setFixedSize(70, 28)
            remove_btn.setStyleSheet(f"QPushButton {{ background: {C['danger']}; color: white; border: none; border-radius: 4px; font-size: 11px; }} QPushButton:hover {{ background: #dc2626; }}")
            remove_btn.clicked.connect(lambda checked, ip=entry.get('ip'): self._remove_ip(ip))
            self.table.setCellWidget(row, 3, remove_btn)
        
        if not blocked:
            self.table.setRowCount(1)
            empty_lbl = QLabel("Engellenen IP yok")
            empty_lbl.setStyleSheet(f"color: {C['muted']}; padding: 20px;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(0, 0, QWidget())
            self.table.setCellWidget(0, 1, QWidget())
            self.table.setCellWidget(0, 2, QWidget())
            self.table.setCellWidget(0, 3, QWidget())

    def _remove_ip(self, ip):
        from kill_switch import unblock_ip
        if unblock_ip(ip):
            self.db.remove_blocked_ip(ip)
            self._load_data()


class AnalysisWorker(QThread):
    finished = pyqtSignal()
    def __init__(self, analyzer):
        super().__init__()
        self.analyzer = analyzer
    def run(self):
        self.analyzer.analyze(hours=1, force_full=True)
        self.finished.emit()


# ─── Uygulama Başlatıcı ───────────────────────────────────────────────
def run_gui(db, analyzer, engine, scheduler):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("AgTara")
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow(db=db, analyzer=analyzer, engine=engine, scheduler=scheduler)
    window.show()
    window._refresh_all()
    return app.exec()
