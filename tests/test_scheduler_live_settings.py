import unittest
from unittest.mock import patch

from scheduler import AnalysisScheduler


class FakeScheduler:
    def __init__(self):
        self.jobs = {}
    def get_job(self, name):
        return self.jobs.get(name)
    def remove_job(self, name):
        self.jobs.pop(name, None)
    def add_job(self, **kwargs):
        self.jobs[kwargs["id"]] = kwargs


class SchedulerLiveSettingsTests(unittest.TestCase):
    def setUp(self):
        self.scheduler = AnalysisScheduler.__new__(AnalysisScheduler)
        self.scheduler.db = object()
        self.scheduler.analyzer = object()
        self.scheduler._scheduler = FakeScheduler()

    def test_interval_and_enabled_changes_apply_immediately(self):
        with patch("scheduler.load_settings", return_value={
            "AUTO_ANALYSIS_ENABLED": True, "ANALYSIS_INTERVAL_MINUTES": 15
        }):
            self.scheduler._configure_analysis_job()
        self.assertIn("ai_analysis", self.scheduler._scheduler.jobs)
        trigger = self.scheduler._scheduler.jobs["ai_analysis"]["trigger"]
        self.assertEqual(15 * 60, int(trigger.interval.total_seconds()))
        with patch("scheduler.load_settings", return_value={"AUTO_ANALYSIS_ENABLED": False}):
            self.scheduler._configure_analysis_job()
        self.assertNotIn("ai_analysis", self.scheduler._scheduler.jobs)


if __name__ == "__main__":
    unittest.main()
