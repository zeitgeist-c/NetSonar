import unittest
from unittest.mock import patch

import notifier


class NotificationCooldownTests(unittest.TestCase):
    def setUp(self):
        notifier._toast_cooldowns.clear()

    def test_same_rule_and_ip_toasts_once_in_ten_minutes(self):
        with patch.object(notifier, "_send_toast") as sender, patch(
            "notifier.time.monotonic", side_effect=[100.0, 101.0, 701.0]
        ):
            self.assertTrue(notifier.notify_custom_alert("rule", "8.8.8.8", "one"))
            self.assertFalse(notifier.notify_custom_alert("rule", "8.8.8.8", "two"))
            self.assertTrue(notifier.notify_custom_alert("rule", "8.8.8.8", "three"))
        self.assertEqual(2, sender.call_count)


if __name__ == "__main__":
    unittest.main()
