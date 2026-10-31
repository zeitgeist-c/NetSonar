"""AUD-NET-002: stats-only deferral test.

Scenario: language change while only the stats worker is active -> pending=True,
pages are not refreshed. Once stats finish and _on_stats_ready runs, pending is
consumed and refresh_ui_language is called. No other analysis is started.

Instrumentation: the language change uses the REAL method (not counted);
self.refresh_ui_language inside _on_stats_ready resolves to a spy on the host
(counted).
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
    # strong reference for singleShot: the real MainWindow is a QObject.
    # (__self__ is never assigned; sip weakref cannot hold a SimpleNamespace.)
    # findChildren: in the real MainWindow this comes from QObject.
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

    # self.refresh_ui_language inside _on_stats_ready resolves here.
    host.refresh_ui_language = spy
    host._on_stats_ready = types.MethodType(
        app_gui.MainWindow._on_stats_ready, host)
    # _consume_pending_refresh: the _Bound above (singleShot compatible).
    return host


def lang_change(host):
    """Language change: REAL method, not counted."""
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
    """Fallback path: consume defers while busy, and the refresh is applied
    in the UI gap once the worker ends."""
    from PyQt6.QtTest import QTest
    host = make_host()
    host._stats_worker = BusyWorker()
    host._worker = None
    host._dash_worker = None
    lang_change(host)
    assert host._pending_lang_refresh is True
    # call while busy -> rescheduled via singleShot, not applied
    host._consume_pending_refresh()
    assert host._pending_lang_refresh is True
    assert host.calls == []
    host._stats_worker.finish()
    QTest.qWait(600)
    qt_app.processEvents()
    assert host._pending_lang_refresh is False
    assert host.calls == [1]


def test_qthread_finished_fires_after_run_with_not_running(qt_app):
    """Finding 2 regression: QThread.finished arrives AFTER run ends;
    isRunning is False at that point (no custom signal shadowing)."""
    from PyQt6.QtTest import QTest
    from PyQt6.QtCore import QObject

    class FakeAnalyzer:
        def analyze_pending(self, stage_callback=None):
            if stage_callback:
                stage_callback("x", 1)
            return {"status": "ok"}

    fired = {}

    class Recv(QObject):
        def on_fin(self):
            fired["running"] = worker.isRunning()
            fired["finished"] = worker.isFinished()

    worker = app_gui.AnalysisWorker(FakeAnalyzer())
    recv = Recv()
    worker.finished.connect(recv.on_fin)
    worker.start()
    assert worker.wait(5000)
    QTest.qWait(300)
    qt_app.processEvents()
    assert fired.get("finished") is True
    assert fired.get("running") is False


def test_done_before_finished_keeps_pending_until_thread_end(qt_app):
    """Even when the done callback arrives while isRunning is true, pending
    stays set; the real end (finished path) consumes it."""
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
    # the finished connection lives in the source (_refresh_all); here we wait
    # for finished and trigger the same path manually (the slot is not a QObject).
    from PyQt6.QtTest import QTest
    worker.start()
    assert release.wait(0) is False
    # done has not arrived yet; language change -> defer
    lang_change(host)
    assert host._pending_lang_refresh is True
    release.set()
    worker.wait(5000)
    qt_app.processEvents()
    # done is emitted from inside run(), so the worker was active at that point.
    assert seen_running.get("running_at_done") is True
    # the thread ended (finished); the same consumption path as the finished
    # connection in the source runs. The singleShot fallback is out of scope here.
    assert worker.isFinished() or not worker.isRunning()
    host._consume_pending_refresh()
    # the singleShot fallback must also work in the UI gap without error; wait briefly.
    from PyQt6.QtTest import QTest
    QTest.qWait(600)
    assert host._pending_lang_refresh is False
    assert host.calls == [1]
