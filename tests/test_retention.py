import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from database import Database


class RetentionTests(unittest.TestCase):
    def test_expired_pending_batch_keeps_anonymous_rollup(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "retention.db")
            old = (datetime.now() - timedelta(hours=25)).replace(microsecond=0).isoformat()
            db.upsert_flow_bucket({"bucket_start": old[:13] + ":00:00", "local_ip": "10.0.0.2",
                "local_port": 50000, "remote_ip": "8.8.8.8", "remote_port": 443,
                "protocol": "TCP", "process": "test.exe", "sent_bytes": 10,
                "received_bytes": 20, "sent_packets": 1, "received_packets": 1,
                "first_seen": old, "last_seen": old})
            batch = db.claim_pending_batch()
            db.conn.execute("UPDATE analysis_batches SET created_at=? WHERE id=?", (old, batch["id"]))
            db.conn.commit()
            result = db.cleanup_old_records()
            self.assertTrue(result["warning"])
            self.assertEqual(0, db.conn.execute("SELECT COUNT(*) FROM flow_buckets").fetchone()[0])
            rollup = db.conn.execute("SELECT * FROM hourly_rollups").fetchone()
            self.assertEqual((10, 20, 1),
                (rollup["sent_bytes"], rollup["received_bytes"], rollup["flow_count"]))
            self.assertEqual("expired", db.conn.execute(
                "SELECT status FROM analysis_batches"
            ).fetchone()[0])
            db.close()


if __name__ == "__main__":
    unittest.main()
