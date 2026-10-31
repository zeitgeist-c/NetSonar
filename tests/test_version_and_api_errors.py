import json
import unittest
from pathlib import Path

import i18n
from ai_analyzer import _gemini_error_message
from config import APP_VERSION, get_app_version
import update


class VersionAndApiErrorTests(unittest.TestCase):
    """The AI error messages are catalogue keys; assert the source language."""

    def setUp(self):
        self._previous_lang = i18n.language()
        i18n.set_language("tr")

    def tearDown(self):
        i18n.set_language(self._previous_lang)

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

    def test_api_errors_are_translated_in_english(self):
        i18n.set_language("en")
        quota = _gemini_error_message(429, '{"error":{"message":"forbidden"}}')
        permission = _gemini_error_message(403, '{"error":{"message":"forbidden"}}')
        self.assertIn("HTTP 429", quota)
        self.assertIn("HTTP 403", permission)
        self.assertNotIn("anahtari gecerli", quota)
        self.assertNotIn("yetkisini", permission)

    def test_versioned_bat_launches_matching_portable_exe(self):
        root = Path(__file__).resolve().parents[1]
        # No versioned BAT is produced on the installer channel; the BAT in the
        # source root runs with the venv for development.
        root_launcher = (root / "NetSonar.bat").read_text(encoding="utf-8")
        self.assertIn(r".venv\Scripts\pythonw.exe", root_launcher)
        self.assertIn(r"%~dp0main.py", root_launcher)

    def test_installer_contract_is_versioned_and_setup(self):
        """Delivery file name: NetSonar-Version-Setup.exe."""
        version = APP_VERSION.lstrip("v")
        expected = f"NetSonar-v{version}-Setup.exe"
        self.assertEqual(update.installer_asset_name(version), expected)
        self.assertTrue(expected.startswith("NetSonar-"))
        self.assertTrue(expected.endswith("-Setup.exe"))


if __name__ == "__main__":
    unittest.main()
