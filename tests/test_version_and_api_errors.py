import json
import unittest

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


if __name__ == "__main__":
    unittest.main()
