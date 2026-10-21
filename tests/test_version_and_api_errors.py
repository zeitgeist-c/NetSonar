import json
import unittest
from pathlib import Path

from ai_analyzer import _gemini_error_message
from config import APP_VERSION, get_app_version
import update


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

    def test_versioned_bat_launches_matching_portable_exe(self):
        root = Path(__file__).resolve().parents[1]
        # Kurulumcu kanalinda surumlu BAT uretilmez; kaynak kokundeki BAT
        # gelistirme icin venv ile calisir.
        root_launcher = (root / "NetSonar.bat").read_text(encoding="utf-8")
        self.assertIn(r".venv\Scripts\pythonw.exe", root_launcher)
        self.assertIn(r"%~dp0main.py", root_launcher)

    def test_installer_contract_is_versioned_and_setup(self):
        """Teslim dosyasi adi: NetSonar-Sürüm-Setup.exe."""
        version = APP_VERSION.lstrip("v")
        expected = f"NetSonar-v{version}-Setup.exe"
        self.assertEqual(update.installer_asset_name(version), expected)
        self.assertTrue(expected.startswith("NetSonar-"))
        self.assertTrue(expected.endswith("-Setup.exe"))


if __name__ == "__main__":
    unittest.main()
