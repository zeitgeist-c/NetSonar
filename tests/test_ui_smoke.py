import os

# Qt must select its headless platform before any PyQt6 or application module
# is imported.  This keeps the suite deterministic on CI and Windows hosts.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from PyQt6.QtCore import QCoreApplication, QEvent, QSize, Qt, QThread
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QScrollBar, QWidget

import app_gui
import config
from ui_components import AppButton, BUTTON_HEIGHTS, NavigationRail


class FakeDatabase:
    """Side-effect-free values for every query a UI refresh may request."""

    def __init__(self):
        self.closed = False

    def get_stats(self):
        return {
            "today_connections": 0,
            "total_threats": 0,
            "blocked_ips": 0,
            "total_reports": 0,
        }

    def get_traffic_stats(self):
        return []

    def get_summary(self, *args, **kwargs):
        return []

    def get_traffic_speed(self, *args, **kwargs):
        return {}

    def get_top_processes(self, *args, **kwargs):
        return []

    def get_protocol_distribution(self, *args, **kwargs):
        return {}

    def get_active_connections_count(self, *args, **kwargs):
        return 0

    def get_traffic_timeline(self, *args, **kwargs):
        return []

    def get_analysis_reports(self, *args, **kwargs):
        return []

    def get_recent_reports(self, *args, **kwargs):
        return []

    def get_last_analysis_time(self):
        return None

    def get_connections_since(self, *args, **kwargs):
        return []

    def get_blocked_ips(self):
        return []

    def get_trusted_ips(self):
        return []

    def is_trusted_ip(self, _ip):
        return False

    def close(self):
        self.closed = True


class FakeAnalyzer:
    def analyze(self, *args, **kwargs):
        raise AssertionError("Smoke tests must not call the AI/network layer")


class FakeService:
    def __init__(self):
        self.stop_calls = 0

    def stop(self):
        self.stop_calls += 1


class QtSmokeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.db = FakeDatabase()
        self.analyzer = FakeAnalyzer()
        self.engine = FakeService()
        self.scheduler = FakeService()

    def _running_threads(self, widget):
        """Find child and attribute-held workers, including parentless QThreads."""

        owners = [widget, *widget.findChildren(QWidget)]
        threads = set(widget.findChildren(QThread))
        for owner in owners:
            try:
                values = vars(owner).values()
            except TypeError:
                continue
            threads.update(value for value in values if isinstance(value, QThread))
        return [thread for thread in threads if thread.isRunning()]

    def _dispose(self, widget):
        for thread in self._running_threads(widget):
            thread.requestInterruption()
            thread.quit()
            if not thread.wait(1500):
                # A smoke-test fake must never reach this path, but terminating
                # is safer than letting Qt destroy a live worker at process exit.
                thread.terminate()
                thread.wait(1500)
        self.assertEqual([], self._running_threads(widget))
        widget.hide()
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    @contextmanager
    def _mocked_window_runtime(self):
        """Build only the shell: no tray, timers, workers, DB, or network work."""

        with ExitStack() as stack:
            mocks = {
                "tray": stack.enter_context(
                    patch.object(app_gui.MainWindow, "_setup_tray", autospec=True)
                ),
                "timer": stack.enter_context(
                    patch.object(app_gui.MainWindow, "_setup_timer", autospec=True)
                ),
                "stats_refresh": stack.enter_context(
                    patch.object(app_gui.MainWindow, "_refresh_all", autospec=True)
                ),
                "dashboard_refresh": stack.enter_context(
                    patch.object(app_gui.DashboardTab, "refresh", autospec=True)
                ),
            }
            yield mocks

    def _new_window(self):
        return app_gui.MainWindow(
            db=self.db,
            analyzer=self.analyzer,
            engine=self.engine,
            scheduler=self.scheduler,
        )


class AppButtonContractTests(QtSmokeTestCase):
    def test_variants_and_sizes_expose_stable_properties(self):
        host = QWidget()
        try:
            for variant in ("primary", "secondary", "ghost", "success", "danger"):
                for size in ("sm", "md", "lg"):
                    with self.subTest(variant=variant, size=size):
                        button = AppButton("Eylem", variant=variant, size=size, parent=host)
                        self.assertEqual(variant, button.property("variant"))
                        # QWidget already owns a QSize-valued ``size`` Qt
                        # property, so the component's public Python property
                        # is the unambiguous semantic size contract.
                        self.assertEqual(size, button.button_size)
                        self.assertEqual(BUTTON_HEIGHTS[size], button.height())
                        self.assertEqual(BUTTON_HEIGHTS[size], button.minimumHeight())
                        self.assertEqual(BUTTON_HEIGHTS[size], button.maximumHeight())
        finally:
            self._dispose(host)

    def test_focus_checkable_and_busy_contract(self):
        host = QWidget()
        button = AppButton(
            "Analizi Başlat",
            variant="primary",
            size="lg",
            checkable=True,
            parent=host,
        )
        host.resize(320, 120)
        button.move(16, 16)
        button.resize(180, button.height())
        host.show()
        self.app.processEvents()
        try:
            self.assertEqual(Qt.FocusPolicy.StrongFocus, button.focusPolicy())
            button.setFocus(Qt.FocusReason.TabFocusReason)
            self.app.processEvents()
            self.assertTrue(button.hasFocus())

            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            self.assertTrue(button.isChecked())

            button.set_busy(True)
            self.assertTrue(button.is_busy())
            self.assertEqual("true", str(button.property("busy")).lower())
            self.assertFalse(button.isEnabled())

            button.set_busy(False)
            self.assertFalse(button.is_busy())
            self.assertEqual("false", str(button.property("busy")).lower())
            self.assertTrue(button.isEnabled())
            self.assertEqual("Analizi Başlat", button.text())

            button.setEnabled(False)
            button.set_busy(True)
            button.set_busy(False)
            self.assertFalse(button.isEnabled(), "busy must restore the prior enabled state")
        finally:
            self._dispose(host)


class MainWindowSmokeTests(QtSmokeTestCase):
    def test_shell_has_six_item_scrollbar_free_navigation(self):
        with self._mocked_window_runtime() as mocks:
            window = self._new_window()
            try:
                mocks["tray"].assert_called_once_with(window)
                mocks["timer"].assert_called_once_with(window)
                mocks["stats_refresh"].assert_not_called()

                navigation = window._navigation
                self.assertIsInstance(navigation, NavigationRail)
                self.assertEqual(6, navigation.count())
                self.assertEqual(
                    6,
                    len([navigation.button(index) for index in range(navigation.count())]),
                )
                horizontal_scrollbars = [
                    scrollbar
                    for scrollbar in navigation.findChildren(QScrollBar)
                    if scrollbar.orientation() == Qt.Orientation.Horizontal
                ]
                self.assertEqual([], horizontal_scrollbars)
            finally:
                self._dispose(window)

    def test_supported_window_sizes_can_be_rendered_offscreen(self):
        with self._mocked_window_runtime():
            window = self._new_window()
            window.show()
            self.app.processEvents()
            try:
                cta = window._quick_btn
                self.assertIsInstance(cta, AppButton)
                self.assertEqual("primary", cta.property("variant"))

                for width, height in ((1280, 760), (1600, 900)):
                    with self.subTest(size=(width, height)):
                        window.resize(width, height)
                        self.app.processEvents()
                        QTest.qWait(10)

                        self.assertEqual(QSize(width, height), window.size())
                        self.assertTrue(window.centralWidget().isVisibleTo(window))
                        self.assertTrue(cta.isVisibleTo(window))
                        frame = window.grab()
                        self.assertFalse(frame.isNull())
                        self.assertGreater(frame.width(), 0)
                        self.assertGreater(frame.height(), 0)
            finally:
                self._dispose(window)


class PageConstructionSmokeTests(QtSmokeTestCase):
    def test_every_page_constructs_without_starting_background_work(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = os.path.join(temp_dir, "settings.json")
            prompt_file = os.path.join(temp_dir, "ai_prompt.txt")
            fallback_prompt_file = os.path.join(temp_dir, "default_prompt.txt")

            with (
                patch.object(config, "SETTINGS_FILE", settings_file),
                patch.object(config, "PROMPT_FILE", prompt_file),
                patch.object(config, "DEFAULT_PROMPT_FILE", fallback_prompt_file),
            ):
                factories = (
                    ("dashboard", lambda: app_gui.DashboardTab(self.db)),
                    ("analysis", lambda: app_gui.AnalysisTab(self.db, self.analyzer)),
                    ("connections", lambda: app_gui.DataTab(self.db)),
                    ("blocked", lambda: app_gui.BlockedTab(self.db)),
                    ("trusted", lambda: app_gui.TrustedTab(self.db)),
                    ("settings", app_gui.SettingsTab),
                )
                pages = []
                try:
                    for name, factory in factories:
                        with self.subTest(page=name):
                            page = factory()
                            pages.append(page)
                            self.assertIsInstance(page, QWidget)
                            self.assertIsNotNone(page.layout())
                            self.assertEqual([], self._running_threads(page))
                finally:
                    for page in reversed(pages):
                        self._dispose(page)


class ApiKeyManagerTests(QtSmokeTestCase):
    def test_order_controls_default_and_backup_labels(self):
        manager = app_gui.ApiKeyManager("Gemini")
        try:
            manager.set_keys(["first-secret", "second-secret", "first-secret"])
            self.assertEqual(["first-secret", "second-secret"], manager.keys())
            self.assertTrue(manager.list.item(0).text().startswith("Varsayılan API"))
            self.assertTrue(manager.list.item(1).text().startswith("Yedek API 2"))
            self.assertNotIn("first-secret", manager.list.item(0).text())
            manager.list.setCurrentRow(1)
            manager._move(-1)
            self.assertEqual(["second-secret", "first-secret"], manager.keys())
            self.assertTrue(manager.list.item(0).text().startswith("Varsayılan API"))
        finally:
            self._dispose(manager)


if __name__ == "__main__":
    unittest.main()
