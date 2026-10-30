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
    from PyQt6.QtCore import QObject
    host = types.SimpleNamespace()
    host._qobj = QObject()
    real_consume = app_gui.MainWindow._consume_pending_refresh

    class _Bound:
        def __call__(self):
            real_consume(host)

    host._consume_pending_refresh = _Bound()
    # singleShot icin guclu referans: gercek MainWindow QObject'tur.
    # (__self__ atanmaz; sip weakref SimpleNamespace'e takilir.)
    # findChildren: gercek MainWindow'da QObject'ten gelir.
    host.findChildren = lambda *a, **k: []
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
    # _consume_pending_refresh: yukaridaki _Bound (singleShot uyumlu).
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


def test_singleshot_retry_applies_after_worker_ends(qt_app):
    """Yedek yol: consume mesgulken erteler, worker bitince UI
    boslugunda refresh uygulanir."""
    from PyQt6.QtTest import QTest
    host = make_host()
    host._stats_worker = BusyWorker()
    host._worker = None
    host._dash_worker = None
    lang_change(host)
    assert host._pending_lang_refresh is True
    # mesgulken cagri -> singleShot ile yeniden planlar, uygulamaz
    host._consume_pending_refresh()
    assert host._pending_lang_refresh is True
    assert host.calls == []
    host._stats_worker.finish()
    QTest.qWait(600)
    qt_app.processEvents()
    assert host._pending_lang_refresh is False
    assert host.calls == [1]


def test_done_before_finished_keeps_pending_until_thread_end(qt_app):
    """done callback'i isRunning true iken gelse bile pending yasanir;
    gercek bitis (finished yolu) tuketir."""
    import threading
    from PyQt6.QtCore import QThread
    from PyQt6.QtTest import QSignalSpy
    import app_gui

    release = threading.Event()

    class SlowDb:
        def get_stats(self):
            release.wait(5)
            return {}

    host = make_host()
    worker = app_gui.StatsWorker(SlowDb())
    seen_running = {}
    from PyQt6.QtCore import Qt
    worker.done.connect(lambda stats: seen_running.setdefault(
        "running_at_done", worker.isRunning()), Qt.ConnectionType.DirectConnection)
    worker.done.connect(lambda stats: host.__dict__.setdefault(
        "_stats_worker", worker))
    host._stats_worker = worker
    host._worker = None
    host._dash_worker = None
    # finished baglantisi kaynak kodda (_refresh_all); burada finished'i
    # bekleyip ayni yolu manuel tetikliyoruz (slot QObject degil).
    from PyQt6.QtTest import QTest
    worker.start()
    assert release.wait(0) is False
    # done henuz gelmedi; dil degisimi -> ertele
    lang_change(host)
    assert host._pending_lang_refresh is True
    release.set()
    worker.wait(5000)
    qt_app.processEvents()
    # done run() icinden emit edildigi icin worker o anda aktifti.
    assert seen_running.get("running_at_done") is True
    # thread bitti (finished); kaynak koddaki finished baglantisi ile
    # ayni tuketim yolu calisir. singleShot yedegi test disi birakilir.
    assert worker.isFinished() or not worker.isRunning()
    host._consume_pending_refresh()
    # singleShot yedegi UI boslugunda da sorunsuz calismali; kisa bekle.
    from PyQt6.QtTest import QTest
    QTest.qWait(600)
    assert host._pending_lang_refresh is False
    assert host.calls == [1]
