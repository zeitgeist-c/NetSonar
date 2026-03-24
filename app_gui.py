"""
AgTara — PyQt6 Grafik Kullanıcı Arayüzü
Dark-theme, tabbed arayüz: Dashboard, AI Analizi, Engellenen IP'ler, Ayarlar.
System tray desteği ile arka planda sessizce çalışır.
"""

import sys
import json
import threading
from datetime import datetime
import dns_cache

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLabel,
    QTabWidget, QLineEdit, QComboBox, QSpinBox, QFrame, QSizePolicy,
    QTextEdit, QTextBrowser, QSystemTrayIcon, QMenu, QMessageBox, QFormLayout,
    QGroupBox, QRadioButton, QButtonGroup, QScrollArea, QSplitter,
    QProgressBar,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt6.QtGui import (
    QIcon, QColor, QFont, QPixmap, QPainter, QAction, QBrush,
    QLinearGradient,
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

    def __init__(self, analyzer):
        super().__init__()
        self.analyzer = analyzer

    def run(self):
        try:
            result = self.analyzer.analyze(hours=1)
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


# ─── Trafik Paneli ───────────────────────────────────────────
class TrafficPanel(QFrame):
    """
    Yatay panel: Saat / Gun / Hafta / Ay / Yil bazinda
    Upload (yukari ok) ve Download (asagi ok) gosterir.
    """

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setObjectName("card")
        self.setFixedHeight(118)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 10, 16, 10)
        outer.setSpacing(6)

        # Baslik satiri
        hdr = QHBoxLayout()
        title_lbl = QLabel("Veri Transferı İstatistikleri")
        title_lbl.setStyleSheet("font-weight:700; font-size:13px; border:none;")
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        last_lbl = QLabel("Kaynaktan gelen ↓ • Giden ↑")
        last_lbl.setStyleSheet(f"color:{C['muted']}; font-size:11px; border:none;")
        hdr.addWidget(last_lbl)
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

        # ── Filtre satiri ──
        filter_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 IP, port veya süreç ara...")
        self.search_box.textChanged.connect(self._filter_table)
        filter_row.addWidget(self.search_box)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        # ── Bağlantı Tablosu ──
        self.table = QTableWidget()
        #  0:Zaman  1:Hedef IP  2:Site  3:Port  4:Protokol  5:Veri(KB)  6:Süreç  7:Durum  8:Engelle
        cols = ["Zaman", "Hedef IP", "Site", "Port", "Protokol", "Veri (KB)", "Süreç", "Durum", ""]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Site genişler
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # Süreç genişler
        self.table.setColumnWidth(0, 140)  # Zaman
        self.table.setColumnWidth(1, 125)  # Hedef IP
        self.table.setColumnWidth(3, 55)   # Port
        self.table.setColumnWidth(4, 75)   # Protokol
        self.table.setColumnWidth(5, 75)   # Veri KB
        self.table.setColumnWidth(7, 85)   # Durum
        self.table.setColumnWidth(8, 82)   # Engelle
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            self.table.styleSheet() +
            f"QTableWidget {{alternate-background-color: {C['surface2']};}}"
        )
        layout.addWidget(self.table)

        self._all_rows: list[dict] = []

    def refresh(self):
        rows = self.db.get_recent_connections(limit=150)
        stats = self.db.get_stats()
        self.card_conns.set_value(f"{stats['today_connections']:,}")
        self.card_threats.set_value(stats["total_threats"])
        self.card_blocked.set_value(stats["blocked_ips"])
        self.card_reports.set_value(stats["total_reports"])
        self.traffic_panel.refresh()      # Trafik istatistiklerini guncelle
        self._all_rows = rows
        self._populate_table(rows)

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

    def _filter_table(self, text: str):
        t = text.lower()
        filtered = [
            row for row in self._all_rows
            if t in (
                row.get("dst_ip", "") +
                str(row.get("dst_port", "")) +
                row.get("process", "") +
                dns_cache.resolve(row.get("dst_ip", ""))  # domain'e gore de filtrele
            ).lower()
        ]
        self._populate_table(filtered)


# ─── AI Analiz Sekmesi ────────────────────────────────────────────────
class AnalysisTab(QWidget):
    def __init__(self, db, analyzer):
        super().__init__()
        self.db = db
        self.analyzer = analyzer
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Başlık + buton
        hdr = QHBoxLayout()
        lbl = QLabel("AI Güvenlik Analizi")
        lbl.setObjectName("title")
        self.run_btn = QPushButton("▶  Analizi Şimdi Çalıştır")
        self.run_btn.setFixedHeight(38)
        self.run_btn.clicked.connect(self._run_analysis)
        hdr.addWidget(lbl)
        hdr.addStretch()
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

        # AI Raporu (HTML formatli)
        layout.addWidget(QLabel("AI Analiz Raporu"))
        self.report_browser = QTextBrowser()
        self.report_browser.setReadOnly(True)
        self.report_browser.setPlaceholderText("Analiz calistirildiktan sonra rapor burada goruntulenir...")
        self.report_browser.setMinimumHeight(200)
        self.report_browser.setOpenExternalLinks(False)
        self.report_browser.setStyleSheet(
            f"background:{C['surface2']};color:{C['text']};"
            f"border:1px solid {C['border']};border-radius:6px;"
            f"font-family:'Segoe UI',sans-serif;font-size:13px;"
        )
        layout.addWidget(self.report_browser)

        # Geçmiş Raporlar
        hist_label = QLabel("Rapor Geçmişi")
        hist_label.setStyleSheet(f"font-weight: 700; color: {C['text']};")
        layout.addWidget(hist_label)

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
        self._worker = AIWorker(self.analyzer)
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

        self.openrouter_key = QLineEdit()
        self.openrouter_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openrouter_key.setPlaceholderText("sk-or-...")
        or_form.addRow("API Key:", self.openrouter_key)

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

        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key.setPlaceholderText("AIza...")
        gm_form.addRow("API Key:", self.gemini_key)

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
        layout.addWidget(sched_group)

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
                ("AI_PROVIDER",        cfg.AI_PROVIDER),
                ("OPENROUTER_API_KEY", cfg.OPENROUTER_API_KEY),
                ("OPENROUTER_MODEL",   cfg.OPENROUTER_MODEL),
                ("GEMINI_API_KEY",     cfg.GEMINI_API_KEY),
                ("GEMINI_MODEL",       cfg.GEMINI_MODEL),
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




# ─── Ana Pencere ──────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, db, analyzer, engine, scheduler):
        super().__init__()
        self.db         = db
        self.analyzer   = analyzer
        self.engine     = engine
        self.scheduler  = scheduler
        self.setWindowTitle("AgTara — AI Ağ İzleyici")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)
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
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top Bar ──
        topbar = QFrame()
        topbar.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 #0d1b3e, stop:1 #0a0e1a);"
            f"border-bottom: 1px solid {C['border']};"
        )
        topbar.setFixedHeight(54)
        tb_layout = QHBoxLayout(topbar)
        tb_layout.setContentsMargins(20, 0, 20, 0)

        logo_lbl = QLabel("🛡 AgTara")
        logo_lbl.setStyleSheet(
            "font-size:18px;font-weight:700;color:white;"
            "letter-spacing:1px;"
        )
        self.status_lbl = QLabel("● İzleme Aktif")
        self.status_lbl.setStyleSheet(
            f"color:{C['success']};font-size:11px;font-weight:600;"
        )
        tb_layout.addWidget(logo_lbl)
        tb_layout.addStretch()

        quick_analyze = QPushButton("⚡ Hızlı Analiz")
        quick_analyze.setFixedHeight(32)
        quick_analyze.clicked.connect(self._quick_analyze)
        tb_layout.addWidget(quick_analyze)
        tb_layout.addSpacing(12)
        tb_layout.addWidget(self.status_lbl)

        root.addWidget(topbar)

        # ── Tabs ──
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.dash_tab     = DashboardTab(db=self.db)
        self.analysis_tab = AnalysisTab(db=self.db, analyzer=self.analyzer)
        self.blocked_tab  = BlockedTab(db=self.db)
        self.settings_tab = SettingsTab()

        self.tabs.addTab(self.dash_tab,     "  📡  Dashboard  ")
        self.tabs.addTab(self.analysis_tab, "  🤖  AI Analizi  ")
        self.tabs.addTab(self.blocked_tab,  "  🔒  Engellenen IP'ler  ")
        self.tabs.addTab(self.settings_tab, "  ⚙️  Ayarlar  ")

        root.addWidget(self.tabs)

        # Dashboard engelle sinyalini bağla
        self.dash_tab.request_block.connect(self._block_from_dashboard)

        # ── Status Bar ──
        self.statusBar().setStyleSheet(
            f"background:{C['surface']};color:{C['muted']};border-top:1px solid {C['border']};"
        )
        self.statusBar().showMessage("AgTara hazır — ağ trafiği izleniyor")

    def _setup_tray(self):
        # Basit ikon: mavi kare
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
        analyze_action = QAction("Hızlı Analiz", self)
        analyze_action.triggered.connect(self._quick_analyze)
        quit_action = QAction("Çıkış", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(show_action)
        menu.addAction(analyze_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.setToolTip("AgTara — Ağ Koruması Aktif")
        self.tray.activated.connect(
            lambda reason: self.showNormal()
            if reason == QSystemTrayIcon.ActivationReason.Trigger else None
        )
        self.tray.show()

    def _setup_timer(self):
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_all)
        self._refresh_timer.start(3000)   # Her 3 saniyede bir yenile

    def _refresh_all(self):
        if self.tabs.currentIndex() == 0:
            self.dash_tab.refresh()
        elif self.tabs.currentIndex() == 1:
            self.analysis_tab.refresh()
        elif self.tabs.currentIndex() == 2:
            self.blocked_tab.refresh()

    def _quick_analyze(self):
        self.tabs.setCurrentIndex(1)
        self.analysis_tab._run_analysis()

    def _block_from_dashboard(self, ip: str):
        from kill_switch import block_ip
        from notifier import notify_ip_blocked
        reply = QMessageBox.question(
            self, "IP Engelle",
            f"{ip} adresini engellemek istediğine emin misin?\n"
            "Windows Güvenlik Duvarı'na kalıcı kural eklenecek.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            ok = block_ip(ip, reason="Dashboard'dan engellendi", db=self.db)
            if ok:
                notify_ip_blocked(ip)
                self.statusBar().showMessage(f"✓ {ip} engellendi")
            else:
                QMessageBox.critical(self, "Hata", "Engelleme başarısız. Yönetici yetkisi gerekli.")

    def closeEvent(self, event):
        # Kapatma butonuna basıldığında tray'e küçül
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "AgTara Arka Planda",
            "İzleme devam ediyor. Çıkmak için sistem tepsisi menüsünü kullanın.",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _quit(self):
        self.engine.stop()
        self.scheduler.stop()
        self.tray.hide()
        QApplication.quit()


# ─── Uygulama Başlatıcı ───────────────────────────────────────────────
def run_gui(db, analyzer, engine, scheduler):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("AgTara")
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow(db=db, analyzer=analyzer, engine=engine, scheduler=scheduler)
    window.show()
    window.dash_tab.refresh()

    return app.exec()
