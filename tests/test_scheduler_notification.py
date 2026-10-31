"""Scheduler notification: the real finding count and provider name must be used."""

import sys
import unittest
from unittest import mock

sys.path.insert(0, r"C:/Users/mahmu/Projeler/NetSonar")

import scheduler


class FakeAnalyzer:
    provider = "gemini"

    def __init__(self, findings):
        self._findings = findings

    def analyze_pending(self):
        return {
            "risk_score": 8.2,
            "status": "risky",
            "findings": self._findings,
            "_meta": {"skipped": False},
        }


class SchedulerNotificationTests(unittest.TestCase):
    def test_notification_carries_real_finding_count_and_provider(self):
        analyzer = FakeAnalyzer([
            {"severity": "critical", "evidence": "a"},
            {"severity": "high", "evidence": "b"},
            {"severity": "medium", "evidence": "c"},
        ])
        with mock.patch.object(scheduler, "notify_analysis_done") as notified:
            scheduler._run_analysis(object(), analyzer)
        notified.assert_called_once_with(8.2, "risky", "gemini", 3)

    def test_notification_is_skipped_without_findings(self):
        analyzer = FakeAnalyzer([])
        with mock.patch.object(scheduler, "notify_analysis_done") as notified:
            scheduler._run_analysis(object(), analyzer)
        notified.assert_not_called()


if __name__ == "__main__":
    unittest.main()
