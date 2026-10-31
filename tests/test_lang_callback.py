"""AUD-NET-002 behavior test: the language-change callback reaches the right object.

Regression: SettingsTab._on_lang used to call a non-existent
``self.refresh_ui_language()`` (AttributeError). It now emits a signal;
MainWindow.refresh_ui_language is connected. Navigation must also have
6 entries (Dashboard/Analysis/Flows/Rules/Keys/Settings).
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
    assert received, "language_changed signal was not emitted"


def test_nav_items_cover_six_pages():
    import app_gui
    import re
    src = open("app_gui.py", encoding="utf-8").read()
    m = re.search(r"def refresh_ui_language.*?nav_items = \[(.*?)\]\n",
                  src, re.S)
    assert m, "nav_items not found"
    pairs = re.findall(r'\(t\("([^"]+)"\), t\("', m.group(1))
    assert pairs == ["Panel", "Analiz", "Akışlar",
                     "Kurallar", "Anahtarlar", "Ayarlar"], pairs
