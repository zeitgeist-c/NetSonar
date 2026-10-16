import unittest

from flow_accumulator import FlowAccumulator


class FakeDB:
    def __init__(self):
        self.rows = []
    def upsert_flow_bucket(self, row, commit=True):
        self.rows.append(row)
    def flush(self):
        pass
    def rollback(self):
        pass


class FlowAccumulatorTests(unittest.TestCase):
    def test_hundred_thousand_packets_become_one_delta(self):
        db = FakeDB()
        accumulator = FlowAccumulator(db)
        packet = {"bucket_start": "2026-08-08T12:00:00", "local_ip": "10.0.0.2",
                  "local_port": 50000, "remote_ip": "8.8.8.8", "remote_port": 443,
                  "protocol": "TCP", "process": "browser.exe", "sent_bytes": 100,
                  "received_bytes": 0, "sent_packets": 1, "received_packets": 0,
                  "first_seen": "2026-08-08T12:00:01", "last_seen": "2026-08-08T12:00:01"}
        for _ in range(100_000):
            accumulator.upsert_flow_bucket(packet)
        self.assertEqual(1, accumulator.bucket_count())
        accumulator.flush()
        self.assertEqual(1, len(db.rows))
        self.assertEqual(10_000_000, db.rows[0]["sent_bytes"])
        self.assertEqual(100_000, db.rows[0]["sent_packets"])


if __name__ == "__main__":
    unittest.main()
