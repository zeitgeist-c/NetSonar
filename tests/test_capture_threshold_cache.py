"""H-01: _packet_handler must not read settings.json from disk per packet."""

import unittest

from scapy.all import IP, TCP

import capture_engine
from capture_engine import _packet_handler


class FakeDB:
    def __init__(self):
        self.rows = []

    def upsert_flow_bucket(self, data):
        self.rows.append(data)
        return len(self.rows)


def _packet(src="192.168.1.20", dst="8.8.8.8", sport=50000, dport=443):
    return IP(src=src, dst=dst) / TCP(sport=sport, dport=dport)


class ThresholdCacheTests(unittest.TestCase):
    def test_threshold_is_not_reloaded_from_disk_per_packet(self):
        calls = []

        def fake_load_settings():
            calls.append(1)
            return {"HIGH_TRAFFIC_THRESHOLD_BYTES": 50 * 1024 * 1024}

        original = capture_engine.load_settings
        capture_engine.load_settings = fake_load_settings
        try:
            db = FakeDB()
            local = {"192.168.1.20"}
            _packet_handler(_packet(), db, local, set())
            _packet_handler(_packet(sport=50001), db, local, set())
        finally:
            capture_engine.load_settings = original
        self.assertEqual(2, len(db.rows))
        self.assertLessEqual(len(calls), 1, f"load_settings called {len(calls)}x for 2 packets")


if __name__ == "__main__":
    unittest.main()
