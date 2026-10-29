"""AUD-NET-002 davranis testi: dil degisimi callback'i dogru nesneye ulasir.

Regresyon: SettingsTab._on_lang eskiden var olmayan
``self.refresh_ui_language()`` cagiriyordu (AttributeError). Simdi sinyal
yayar; MainWindow.refresh_ui_language baglanir. Ayrica navigasyon
6 kayit olmali (Panel/Analiz/Akislar/Kurallar/Anahtarlar/Ayarlar).
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


def test_on_lang_emits_signal_without_attribute_error(qt_app, monkeypatch):
    import config
    import app_gui
    from app_gui import SettingsTab
    monkeypatch.setattr(config, "set_language", lambda code: code)
    monkeypatch.setattr(config, "get_language", lambda: "en")
    monkeypatch.setattr(app_gui, "i18n_set", lambda code: None)
    tab = SettingsTab(db=None)
    received = []
    tab.language_changed.connect(lambda: received.append(True))
    idx_en = tab._lang_combo.findData("en")
    tab._lang_combo.setCurrentIndex(idx_en)
    qt_app.processEvents()
    received.clear()
    idx = tab._lang_combo.findData("de")
    assert idx >= 0 and idx != tab._lang_combo.currentIndex()
    tab._lang_combo.setCurrentIndex(idx)
    qt_app.processEvents()
    assert received, "language_changed sinyali yayilmadi"


def test_nav_items_cover_six_pages():
    import app_gui
    import re
    src = open("app_gui.py", encoding="utf-8").read()
    m = re.search(r"def refresh_ui_language.*?nav_items = \[(.*?)\]\n",
                  src, re.S)
    assert m, "nav_items bulunamadi"
    pairs = re.findall(r'\(t\("([^"]+)"\), t\("', m.group(1))
    assert pairs == ["Panel", "Analiz", "Akışlar",
                     "Kurallar", "Anahtarlar", "Ayarlar"], pairs
