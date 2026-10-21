import unittest
from unittest.mock import patch

import autostart
from app_options import AutostartController


class AutostartTests(unittest.TestCase):
    def test_failed_or_unverified_change_returns_false(self):
        """Kayit yazilamazsa veya dogrulanamazsa False doner."""
        controller = AutostartController(app_name="TestApp")
        with patch.object(controller, "_write_registry", return_value=False), \
             patch.object(controller, "_read_registry", return_value=None):
            self.assertFalse(controller.set_enabled(True))
        with patch.object(controller, "_write_registry", return_value=True), \
             patch.object(controller, "_read_registry", return_value=None):
            self.assertFalse(controller.set_enabled(True))

    def test_module_functions_use_the_shared_controller(self):
        """autostart fonksiyonlari ortak modulu kullanir."""
        with patch.object(autostart, "_controller") as factory:
            factory.return_value.set_enabled.return_value = True
            self.assertTrue(autostart.set_autostart(True))
            factory.return_value.set_enabled.assert_called_once_with(True)

    def test_is_enabled_delegates_to_controller(self):
        with patch.object(autostart, "_controller") as factory:
            factory.return_value.is_enabled.return_value = True
            self.assertTrue(autostart.is_autostart_enabled())

    def test_retarget_keeps_disabled_state(self):
        """Kapali tercih guncellemede acilmaz."""
        with patch.object(autostart.AutostartController, "is_enabled",
                          return_value=False):
            self.assertTrue(autostart.retarget_launch(r"C:\X\X.exe"))


if __name__ == "__main__":
    unittest.main()
