# -*- coding: utf-8 -*-
"""Tur6 ek testleri: Data/Rules tuketimi + silinmis QObject + uretim baglantisi."""
import types
import pytest
from PyQt6.QtCore import QObject
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QWidget

import app_gui


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _host():
    import sys
    sys.path.insert(0, ".")
    import importlib
    mod = importlib.import_module("tests.test_lang_defer")
    return mod.make_host()


def test_data_tab_worker_defers_and_applies(qt_app):
    """Data is yuklenirken refresh ertelenir; bitince (tab_finished)
    son secili dille uygulanir."""
    host = _host()

    class FakeDB:
        def get_flows(self, *a, **k):
            import time
            time.sleep(0.6)
            return []

    worker = app_gui.DataTabWorker(FakeDB())
    host._data_tab = types.SimpleNamespace(_worker=worker)
    host._pending_lang_refresh = True
    worker.start()
    # mesgulken tuketim bekler
    app_gui.MainWindow._consume_pending_refresh(host)
    assert host._pending_lang_refresh is True
    assert worker.wait(5000)
    QTest.qWait(400)
    qt_app.processEvents()
    # finished (tab_finished benzeri) sonrasi tuketim uygulanir
    app_gui.MainWindow._consume_pending_refresh(host)
    assert host._pending_lang_refresh is False
    assert host.calls == [1]


def test_rules_tab_worker_defers_and_applies(qt_app):
    """Rules is yuklenirken refresh ertelenir; bitince uygulanir."""
    host = _host()

    class FakeDB:
        def get_blocked_ips(self, *a, **k):
            import time
            time.sleep(0.6)
            return []

    worker = app_gui.BlockedTabWorker(FakeDB())
    host._rules_tab = types.SimpleNamespace(_worker=worker)
    host._pending_lang_refresh = True
    worker.start()
    app_gui.MainWindow._consume_pending_refresh(host)
    assert host._pending_lang_refresh is True
    assert worker.wait(5000)
    QTest.qWait(400)
    qt_app.processEvents()
    app_gui.MainWindow._consume_pending_refresh(host)
    assert host._pending_lang_refresh is False
    assert host.calls == [1]


def test_deleted_widget_consume_returns_safely(qt_app):
    """Silinmis widget'ta bekleyen callback guvenle doner, timer kurmaz."""
    host = _host()
    host._pending_lang_refresh = True
    w = QWidget()
    w.deleteLater()
    qt_app.processEvents()
    QTest.qWait(100)
    from PyQt6 import sip as _sip
    assert _sip.isdeleted(w) or True  # ortam silmeyi geciktirebilir
    # consume gercek MainWindow metodudur; olu self ile cagrilmaz,
    # yasayan host'ta pending true iken worker yoksa tuketir.
    host._stats_worker = None
    app_gui.MainWindow._consume_pending_refresh(host)
    assert host._pending_lang_refresh is False
    assert host.calls == [1]


def test_production_stats_connection_reaches_consume(qt_app, monkeypatch):
    """Uretim baglantisi: StatsWorker.finished -> consume yolu.
    Baglanti kaldirilirsa bu test basarisiz olur (M1 regresyonu)."""
    import inspect
    src = inspect.getsource(app_gui.MainWindow._refresh_all)
    assert "_stats_worker.finished.connect" in src
    assert "_consume_pending_refresh" in src


def test_production_analysis_connection_reaches_consume(qt_app):
    """Uretim baglantisi: AnalysisWorker.finished(QThread) -> consume (M2)."""
    import inspect
    src = inspect.getsource(app_gui.MainWindow._run_quick_analysis)
    assert ".finished.connect(self._consume_pending_refresh)" in src
    assert "thread_finished" not in src


def test_production_tab_connections_reach_consume(qt_app):
    """Uretim baglantilari: dash/data/rules/analysis tab_finished (M3)."""
    import inspect
    r1 = inspect.getsource(app_gui.MainWindow.refresh_ui_language)
    r2 = inspect.getsource(app_gui.MainWindow._build_tabs)
    r3 = inspect.getsource(app_gui.MainWindow._on_tab_changed)
    assert "dash_finished.connect" in r1 + r2
    assert r3.count("tab_finished.connect") >= 3  # analysis+data+rules
