"""Ayar yazımı atomik olmalı: hedef dosya ya eski ya yeni içeriği taşır, yarım JSON olmaz."""
import json
import os
import tempfile
import unittest

import config


class AtomicSettingsWriteTest(unittest.TestCase):
    def test_write_produces_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "settings.json")
            old, config.SETTINGS_FILE = config.SETTINGS_FILE, target
            try:
                config._write_settings({"GEMINI_MODEL": "x", "GEMINI_API_KEYS": []})
                with open(target, encoding="utf-8") as f:
                    data = json.load(f)
                self.assertEqual(data["GEMINI_MODEL"], "x")
                self.assertFalse(os.path.exists(target + ".tmp"))
            finally:
                config.SETTINGS_FILE = old

    def test_failed_write_keeps_old_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "settings.json")
            with open(target, "w", encoding="utf-8") as f:
                json.dump({"old": True}, f)
            old, config.SETTINGS_FILE = config.SETTINGS_FILE, target
            try:
                with self.assertRaises(TypeError):
                    config._write_settings(object())
                with open(target, encoding="utf-8") as f:
                    self.assertEqual(json.load(f), {"old": True})
            finally:
                config.SETTINGS_FILE = old


if __name__ == "__main__":
    unittest.main()
