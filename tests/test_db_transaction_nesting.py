"""Transaction nesting between capture flush and analysis workers.

`FlowAccumulator.flush()` writes every bucket with `commit=False` in one
transaction. Before the fix, `claim_pending_batch`/`complete_batch`/
`cleanup_old_records` opened `BEGIN IMMEDIATE` while that transaction was
still open, which raised
    sqlite3.OperationalError: cannot start a transaction within a transaction
and the following rollback silently discarded the captured buckets.
"""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from database import Database
from flow_accumulator import FlowAccumulator


def flow(**overrides):
    data = {
        "bucket_start": "2026-08-01T12:30:00",
        "local_ip": "192.168.1.10",
        "local_port": 50100,
        "remote_ip": "1.1.1.1",
        "remote_port": 443,
        "protocol": "TCP",
        "process": "browser.exe",
        "sent_bytes": 100,
        "received_bytes": 0,
        "sent_packets": 1,
        "received_packets": 0,
        "first_seen": "2026-08-01T12:30:01",
        "last_seen": "2026-08-01T12:30:01",
    }
    data.update(overrides)
    return data


class NestedTransactionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "nested.db")

    def tearDown(self):
        self.db.close()
        self.tempdir.cleanup()

    def _open_capture_transaction(self) -> FlowAccumulator:
        """Leave an uncommitted bucket write, exactly like a flush in flight."""
        accumulator = FlowAccumulator(self.db)
        accumulator.upsert_flow_bucket(flow())
        self.db.upsert_flow_bucket(flow(), commit=False)
        self.assertTrue(self.db.conn.in_transaction)
        return accumulator

    def test_claim_pending_batch_inside_open_capture_transaction(self):
        self._open_capture_transaction()
        batch = self.db.claim_pending_batch()
        self.assertIsNotNone(batch)
        self.assertEqual("running", batch["status"])

    def test_claim_does_not_lose_pending_capture_writes(self):
        accumulator = self._open_capture_transaction()
        batch = self.db.claim_pending_batch()
        # Analysis claims the batch, then the capture flush commits its rows.
        accumulator.flush()
        self.assertEqual(1, self.db.conn.execute(
            "SELECT COUNT(*) FROM flow_buckets").fetchone()[0])
        self.assertEqual(batch["id"], self.db.conn.execute(
            "SELECT batch_id FROM flow_buckets").fetchone()[0])

    def test_complete_batch_inside_open_capture_transaction(self):
        self._open_capture_transaction()
        batch = self.db.claim_pending_batch()
        self.db.complete_batch(batch["id"], 0.5, "safe")
        self.assertEqual("completed", self.db.conn.execute(
            "SELECT status FROM analysis_batches WHERE id=?", (batch["id"],)).fetchone()[0])

    def test_cleanup_old_records_inside_open_capture_transaction(self):
        accumulator = FlowAccumulator(self.db)
        old = (datetime.now() - timedelta(hours=25)).replace(microsecond=0).isoformat()
        self.db.upsert_flow_bucket(flow(bucket_start=old[:13] + ":00:00",
                                       first_seen=old, last_seen=old), commit=False)
        result = self.db.cleanup_old_records()
        self.assertIn("expired_flows", result)
        accumulator.flush()

    def test_failed_inner_block_keeps_outer_transaction(self):
        self._open_capture_transaction()
        with self.assertRaises(ValueError):
            with self.db._atomic():
                raise ValueError("boom")
        # Outer capture transaction must still be intact and committable.
        self.assertTrue(self.db.conn.in_transaction)
        self.db.flush()
        self.assertEqual(1, self.db.conn.execute(
            "SELECT COUNT(*) FROM flow_buckets").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
