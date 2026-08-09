import unittest
import time
from types import SimpleNamespace
from unittest.mock import patch

from ai_analyzer import AIAnalyzer


class FakeDB:
    def is_trusted_ip(self, ip):
        return ip == "9.9.9.9"


class AutoBlockPolicyTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = AIAnalyzer.__new__(AIAnalyzer)
        self.analyzer.db = FakeDB()
        self.cfg = SimpleNamespace(AUTO_BLOCK_ENABLED=True, AUTO_BLOCK_MIN_RISK_SCORE=7,
                                   SUSPICIOUS_BYTES_THRESHOLD=50 * 1024 * 1024,
                                   SUSPICIOUS_PORTS={4444}, SUSPICIOUS_PROCESSES={"powershell.exe"},
                                   VIRUSTOTAL_MAX_ANALYSIS_AGE_DAYS=30)

    def finding(self, **changes):
        value = {"severity": "critical", "confidence": .96, "block_now": True,
                 "flow_refs": [1]}
        value.update(changes)
        return value

    def test_only_global_corroborated_critical_flow_is_blocked(self):
        flows = {1: {"remote_ip": "8.8.8.8", "remote_port": 4444,
                     "sent_bytes": 1, "received_bytes": 0}}
        with patch("ai_analyzer._cfg", return_value=self.cfg), patch(
            "kill_switch.block_ip", return_value=True
        ) as blocker:
            blocked = self.analyzer._auto_block_findings(
                {"risk_score": 9, "findings": [self.finding()]}, flows,
                [{"indicator": "8.8.8.8", "verdict": "malicious", "malicious": 5,
                  "last_analysis_at": time.time()}])
        self.assertEqual(["8.8.8.8"], blocked)
        blocker.assert_called_once()

    def test_do_not_block_text_private_fake_or_low_confidence(self):
        flows = {1: {"remote_ip": "192.168.1.8", "remote_port": 4444,
                     "sent_bytes": 100_000_000, "received_bytes": 0}}
        findings = [self.finding(recommended_action="Do not block"),
                    self.finding(confidence=.94), self.finding(flow_refs=[999])]
        with patch("ai_analyzer._cfg", return_value=self.cfg), patch(
            "kill_switch.block_ip", return_value=True
        ) as blocker:
            blocked = self.analyzer._auto_block_findings(
                {"risk_score": 9, "findings": findings}, flows)
        self.assertEqual([], blocked)
        blocker.assert_not_called()

    def test_web_context_alone_never_auto_blocks(self):
        flows = {1: {"remote_ip": "8.8.8.8", "remote_port": 4444,
                     "process": "powershell.exe", "sent_bytes": 100_000_000,
                     "received_bytes": 0}}
        with patch("ai_analyzer._cfg", return_value=self.cfg), patch(
            "kill_switch.block_ip", return_value=True
        ) as blocker:
            blocked = self.analyzer._auto_block_findings(
                {"risk_score": 10, "findings": [self.finding(
                    source_refs=["web:8.8.8.8:0"])]}, flows, [])
        self.assertEqual([], blocked)
        blocker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
