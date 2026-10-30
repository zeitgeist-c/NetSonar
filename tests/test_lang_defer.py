"""AUD-NET-002: stats-only erteleme testi.

Senario: yalniz stats worker aktifken dil degisimi -> pending=True,
sayfalar yenilenmez. Stats bitip _on_stats_ready calisinca pending
tuketilir ve refresh_ui_language cagrilir. Baska analiz baslatilmaz.

Izleme: dil degisimi GERCEK metotla (sayilmaz); _on_stats_ready
icindeki self.refresh_ui_language host uzerinde spy'a cozulur (sayilir).
"""
import os
import types

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

import app_gui


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


class BusyWorker:
    def __init__(self):
        self._run = True

    def isRunning(self):
        return self._run

    def finish(self):
        self._run = False


class StubTabs:
    def __init__(self):
        self.idx = 2

    def currentIndex(self):
        return self.idx

    def setCurrentIndex(self, i):
        self.idx = i


def make_host():
    host = types.SimpleNamespace()
    host._navigation = types.SimpleNamespace(_buttons=[])
    host._status_label = types.SimpleNamespace(setText=lambda s: None)
    host._sb_iface = types.SimpleNamespace(setText=lambda s: None)
    host._tabs = StubTabs()
    host._dashboard_tab = None
    host._analysis_tab = None
    host._data_tab = None
    host._rules_tab = None
    host._keys_tab = None
    host._settings_tab = None
    host._pending_lang_refresh = False
    host.calls = []

    def spy():
        host.calls.append(1)

    # _on_stats_ready icindeki self.refresh_ui_language buraya cozulur.
    host.refresh_ui_language = spy
    host._on_stats_ready = types.MethodType(
        app_gui.MainWindow._on_stats_ready, host)
    return host


def lang_change(host):
    """Dil degisimi: GERCEK metot, sayilmaz."""
    app_gui.MainWindow.refresh_ui_language(host)


def test_stats_only_defers_then_applies(qt_app):
    host = make_host()
    host._stats_worker = BusyWorker()
    host._worker = None
    host._dash_worker = None
    lang_change(host)
    assert host._pending_lang_refresh is True
    assert host.calls == []
    host._stats_worker.finish()
    host._on_stats_ready({})
    assert host._pending_lang_refresh is False
    assert host.calls == [1]


def test_no_worker_refreshes_immediately(qt_app):
    host = make_host()
    host._stats_worker = None
    host._worker = None
    host._dash_worker = None
    lang_change(host)
    assert host._pending_lang_refresh is False
    assert host.calls == []


def test_repeated_language_change_single_refresh(qt_app):
    host = make_host()
    host._stats_worker = BusyWorker()
    host._worker = None
    host._dash_worker = None
    lang_change(host)
    lang_change(host)
    assert host._pending_lang_refresh is True
    host._stats_worker.finish()
    host._on_stats_ready({})
    assert host.calls == [1]
    assert host._pending_lang_refresh is False
