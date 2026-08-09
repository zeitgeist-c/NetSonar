import json
import unittest
from pathlib import Path

from ai_analyzer import _gemini_error_message
from config import APP_VERSION, get_app_version


class VersionAndApiErrorTests(unittest.TestCase):
    def test_display_version_is_product_version(self):
        self.assertEqual(APP_VERSION, get_app_version())

    def test_quota_error_explains_key_is_valid_and_data_will_retry(self):
        body = json.dumps({"error": {"message": "Quota exceeded for free_tier input tokens"}})
        message = _gemini_error_message(429, body)
        self.assertIn("API anahtari gecerli", message)
        self.assertIn("yeniden denenecek", message)
        self.assertNotIn("free_tier", message)

    def test_permission_error_is_distinct_from_quota(self):
        message = _gemini_error_message(403, '{"error":{"message":"forbidden"}}')
        self.assertIn("HTTP 403", message)
        self.assertIn("yetkisini", message)

    def test_versioned_bat_launches_source_project_not_installer(self):
        root = Path(__file__).resolve().parents[1]
        launcher = (root / "dist" / f"NetSonar-{APP_VERSION}.bat").read_text(encoding="utf-8")
        self.assertIn(r"%~dp0..\NetSonar.bat", launcher)
        self.assertNotIn(f"NetSonar-{APP_VERSION}.exe", launcher)
        root_launcher = (root / "NetSonar.bat").read_text(encoding="utf-8")
        self.assertIn(r".venv\Scripts\pythonw.exe", root_launcher)
        self.assertIn(r"%~dp0main.py", root_launcher)


if __name__ == "__main__":
    unittest.main()
