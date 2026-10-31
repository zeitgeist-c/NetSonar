"""Regression: the two expensive steps on the packet path.

1) `orient_flow` re-normalized the local IP set on every packet.
2) `load_alerts` called ALERTS_FILE.exists()+stat() on every packet.
"""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import custom_alerts
import flow_utils
from flow_utils import orient_flow


class OrientFlowCacheTests(unittest.TestCase):
    def setUp(self):
        flow_utils._LOCAL_CACHE.clear()
        flow_utils._BROADCAST_CACHE.clear()

    def test_direction_survives_the_cache(self):
        local = {"192.168.1.10", "10.0.0.5"}
        out = orient_flow("192.168.1.10", 50100, "8.8.8.8", 443, local, {"255.255.255.255"})
        self.assertEqual(out["direction"], "outbound")
        inbound = orient_flow("8.8.8.8", 443, "192.168.1.10", 50100, local)
        self.assertEqual(inbound["direction"], "inbound")
        self.assertEqual(inbound["local_ip"], "192.168.1.10")

    def test_broadcast_and_unspecified_are_still_rejected(self):
        local = {"192.168.1.10"}
        self.assertIsNone(orient_flow("192.168.1.10", 1, "255.255.255.255", 2, local))
        self.assertIsNone(orient_flow("0.0.0.0", 1, "192.168.1.10", 2, local))
        self.assertIsNone(orient_flow("192.168.1.10", 1, "224.0.0.1", 2, local))

    def test_loopback_only_traffic_is_ignored(self):
        local = {"192.168.1.10", "127.0.0.1"}
        self.assertIsNone(orient_flow("127.0.0.1", 1, "127.0.0.1", 2, local))

    def test_cache_is_bounded(self):
        for index in range(flow_utils._CACHE_LIMIT * 2):
            orient_flow("192.168.1.10", 1, "8.8.8.8", 443, {f"10.0.0.{index}"})
        self.assertLessEqual(len(flow_utils._LOCAL_CACHE), flow_utils._CACHE_LIMIT)

    def test_changed_local_set_is_reflected_immediately(self):
        """When the network changes (new IP), the stale cache must not yield
        a wrong result."""
        first = {"10.0.0.1"}
        self.assertIsNone(orient_flow("10.0.0.2", 1, "8.8.8.8", 443, first))
        second = {"10.0.0.1", "10.0.0.2"}
        result = orient_flow("10.0.0.2", 1, "8.8.8.8", 443, second)
        self.assertEqual(result["direction"], "outbound")


class AlertStatThrottleTests(unittest.TestCase):
    def setUp(self):
        custom_alerts._cache_lock = custom_alerts.threading.Lock()
        custom_alerts._cached_rules = []
        custom_alerts._cached_mtime_ns = None
        custom_alerts._cached_checked_at = 0.0

    def test_repeated_calls_do_not_stat_the_file_every_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom_alerts.json"
            path.write_text(json.dumps([{"name": "r", "port": 4444}]), encoding="utf-8")
            with mock.patch.object(custom_alerts, "ALERTS_FILE", path), \
                 mock.patch.object(custom_alerts, "_STAT_INTERVAL_SECONDS", 60.0):
                first = custom_alerts.load_alerts()
                with mock.patch.object(Path, "stat", side_effect=AssertionError(
                        "stat() must not run on every packet")):
                    for _ in range(50):
                        self.assertEqual([r.name for r in custom_alerts.load_alerts()],
                                         [r.name for r in first])

    def test_new_rule_file_is_picked_up_after_the_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom_alerts.json"
            with mock.patch.object(custom_alerts, "ALERTS_FILE", path), \
                 mock.patch.object(custom_alerts, "_STAT_INTERVAL_SECONDS", 0.0):
                self.assertEqual([], custom_alerts.load_alerts())
                path.write_text(json.dumps([{"name": "new", "port": 22}]), encoding="utf-8")
                names = [rule.name for rule in custom_alerts.load_alerts()]
                self.assertEqual(["new"], names)


if __name__ == "__main__":
    unittest.main()
