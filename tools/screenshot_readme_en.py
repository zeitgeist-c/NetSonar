"""English README screenshots for NetSonar (2000x1250)."""
import os
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.pop("QT_QPA_PLATFORM", None)

import app_gui  # noqa: E402
import config  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402
from PyQt6.QtCore import Qt  # noqa: E402
import tempfile  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
SHOTS = ["01-panel.png", "02-analiz.png", "03-akislar.png",
         "04-kurallar.png", "05-anahtarlar.png", "06-ayarlar.png"]


def shoot(which=None):
    app = QApplication.instance() or QApplication([])
    with ExitStack() as stack:
        tmp = tempfile.TemporaryDirectory()
        stack.enter_context(patch.object(config, "SETTINGS_FILE",
                                         tmp.name + "/settings.json"))
        stack.enter_context(patch.object(config, "PROMPT_FILE",
                                         tmp.name + "/ai_prompt.txt"))
        stack.enter_context(patch.object(config, "DEFAULT_PROMPT_FILE",
                                         tmp.name + "/default_prompt.txt"))
        stack.enter_context(patch.object(app_gui.MainWindow, "_setup_tray", autospec=True))
        stack.enter_context(patch.object(app_gui.MainWindow, "_setup_timer", autospec=True))
        stack.enter_context(patch.object(app_gui.MainWindow, "_refresh_all", autospec=True))
        stack.enter_context(patch.object(app_gui.DashboardTab, "refresh", autospec=True))
        import sqlite3
        import types
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
        from test_ui_smoke import FakeAnalyzer, FakeDatabase, FakeService
        db = FakeDatabase()
        scheduler = types.SimpleNamespace(stop=lambda: None,
                                          reload_settings=lambda: None)
        window = app_gui.MainWindow(db=db, analyzer=FakeAnalyzer(),
                                    engine=FakeService(), scheduler=scheduler)
        window.resize(2000, 1250)
        window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        window.show()
        app.processEvents()
        for i, name in enumerate(SHOTS):
            if which and name != which:
                continue
            try:
                window._navigation._buttons[i].click()
            except (IndexError, AttributeError):
                pass
            app.processEvents()
            window.grab().save(str(OUT / name))
            print(f"wrote {name}", flush=True)
        window.close()
        app.processEvents()


if __name__ == "__main__":
    shoot(sys.argv[1] if len(sys.argv) > 1 else None)
