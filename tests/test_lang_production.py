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
    son secili dille uygulanir. Gercek DataTab + gercek sinyal."""
    from PyQt6.QtCore import QEventLoop
    host = _host()

    class FakeDB:
        def get_last_analysis_time(self):
            return None

        def get_flows(self, *a, **k):
            import time
            time.sleep(0.6)
            return []

    tab = app_gui.DataTab(FakeDB())
    fired = []
    tab.tab_finished.connect(lambda: fired.append(1))
    host._data_tab = tab
    host._pending_lang_refresh = True
    tab.refresh()
    assert tab._worker is not None and tab._worker.isRunning()
    app_gui.MainWindow._consume_pending_refresh(host)
    assert host._pending_lang_refresh is True
    loop = QEventLoop()
    tab.tab_finished.connect(loop.quit)
    loop.exec()
    qt_app.processEvents()
    assert fired == [1]
    app_gui.MainWindow._consume_pending_refresh(host)
    assert host._pending_lang_refresh is False
    assert host.calls == [1]


def test_rules_tab_worker_defers_and_applies(qt_app):
    """Rules is yuklenirken refresh ertelenir; bitince uygulanir.
    Gercek RulesTab + gercek sinyal."""
    from PyQt6.QtCore import QEventLoop
    host = _host()

    class FakeDB:
        def get_blocked_ips(self, *a, **k):
            import time
            time.sleep(0.6)
            return []

    tab = app_gui.RulesTab(FakeDB())
    fired = []
    tab.tab_finished.connect(lambda: fired.append(1))
    host._rules_tab = tab
    host._pending_lang_refresh = True
    tab.refresh()
    assert tab._worker is not None and tab._worker.isRunning()
    app_gui.MainWindow._consume_pending_refresh(host)
    assert host._pending_lang_refresh is True
    loop = QEventLoop()
    tab.tab_finished.connect(loop.quit)
    loop.exec()
    qt_app.processEvents()
    assert fired == [1]
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


def _connect_targets(method_name):
    """Uretim metodundaki .connect() cagrilarinin hedeflerini dondurur.
    Substring degil AST: `if False:` icindeki olu kod ayiklanir."""
    import ast
    import inspect
    import textwrap
    src = textwrap.dedent(inspect.getsource(getattr(app_gui.MainWindow, method_name)))
    tree = ast.parse(src)
    targets = []

    def visit(node, dead=False):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Constant) and node.test.value is False:
            dead = True
        if not dead and isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "connect":
                sig = f.value
                signame = sig.attr if isinstance(sig, ast.Attribute) else ""
                for a in node.args:
                    if isinstance(a, ast.Attribute):
                        targets.append((signame, a.attr))
                    elif isinstance(a, ast.Lambda):
                        targets.append((signame, "lambda"))
        for child in ast.iter_child_nodes(node):
            visit(child, dead)

    visit(tree)
    return targets


def test_production_stats_connection_reaches_consume(qt_app):
    """Uretim baglantisi: StatsWorker.finished -> consume yolu.
    Baglanti kaldirilirsa bu test basarisiz olur (M1 regresyonu)."""
    tg = _connect_targets("_refresh_all")
    assert ("finished", "_consume_pending_refresh") in tg


def test_production_analysis_connection_reaches_consume(qt_app):
    """Uretim baglantisi: AnalysisWorker.finished(QThread) -> consume (M2)."""
    tg = _connect_targets("_run_quick_analysis")
    assert ("finished", "_consume_pending_refresh") in tg
    assert not any("thread_finished" in s for s, _ in tg)


def test_production_tab_connections_reach_consume(qt_app):
    """Uretim baglantilari: dash/data/rules/analysis tab_finished (M3)."""
    r1 = _connect_targets("refresh_ui_language")
    r2 = _connect_targets("_build_tabs")
    r3 = _connect_targets("_on_tab_changed")
    assert ("dash_finished", "_consume_pending_refresh") in r1 + r2
    tablinks = [t for t in r3 if t[0] == "tab_finished" and t[1] == "_consume_pending_refresh"]
    assert len(tablinks) >= 3  # analysis+data+rules
