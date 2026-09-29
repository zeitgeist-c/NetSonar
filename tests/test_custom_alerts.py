"""Custom alerts: eşleşme mantığı + kural doğrulama regresyon koruması."""
import unittest

from custom_alerts import AlertRule


class AlertRuleMatchTest(unittest.TestCase):
    def test_disabled_never_matches(self):
        rule = AlertRule("kapalı", port=80, enabled=False)
        self.assertFalse(rule.matches("1.2.3.4", 80, "x"))

    def test_wildcard_ip(self):
        rule = AlertRule("w", ip_pattern="192.168.*.*")
        self.assertTrue(rule.matches("192.168.1.5", 443, "x"))
        self.assertFalse(rule.matches("10.0.0.1", 443, "x"))

    def test_port_and_process(self):
        rule = AlertRule("p", port=4444, process="POWERSHELL")
        self.assertTrue(rule.matches("1.1.1.1", 4444, "powershell.exe"))
        self.assertFalse(rule.matches("1.1.1.1", 80, "powershell.exe"))

    def test_open_rule_matches_all(self):
        self.assertTrue(AlertRule("açık").matches("8.8.8.8", 53, "dns"))


class AlertRuleValidationTest(unittest.TestCase):
    def test_name_required(self):
        with self.assertRaises(ValueError):
            AlertRule.from_dict({"port": 80})

    def test_port_range(self):
        with self.assertRaises(ValueError):
            AlertRule.from_dict({"name": "x", "port": 99999})

    def test_bad_wildcard_rejected(self):
        with self.assertRaises(ValueError):
            AlertRule.from_dict({"name": "x", "ip_pattern": "300.*.*.*"})

    def test_roundtrip(self):
        rule = AlertRule("r", ip_pattern="10.*.*.*", port=22,
                         process="ssh", allow_auto_block=True)
        clone = AlertRule.from_dict(rule.to_dict())
        self.assertTrue(clone.matches("10.1.2.3", 22, "ssh.exe"))
        self.assertTrue(clone.allow_auto_block)


if __name__ == "__main__":
    unittest.main()
