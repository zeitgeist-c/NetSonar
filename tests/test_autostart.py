import unittest
from unittest.mock import patch

import autostart


class AutostartTests(unittest.TestCase):
    def test_failed_or_unverified_change_returns_false(self):
        with patch.object(autostart, "enable_autostart", return_value=False), patch.object(
            autostart, "is_autostart_enabled", return_value=False
        ):
            self.assertFalse(autostart.set_autostart(True))
        with patch.object(autostart, "enable_autostart", return_value=True), patch.object(
            autostart, "is_autostart_enabled", return_value=False
        ):
            self.assertFalse(autostart.set_autostart(True))


if __name__ == "__main__":
    unittest.main()
