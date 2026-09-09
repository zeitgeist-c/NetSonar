import tempfile
import unittest
from pathlib import Path

from database import Database


class StorageLoadTests(unittest.TestCase):
    def test_five_thousand_flows_checkpoint_under_100_mb(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "load.db"
            db = Database(path)
            for index in range(5000):
                db.upsert_flow_bucket({"bucket_start": "2026-08-08T12:00:00",
                    "local_ip": "10.0.0.2", "local_port": 10000 + index,
                    "remote_ip": f"8.8.{index // 256}.{index % 256}", "remote_port": 443,
                    "protocol": "TCP", "process": "load.exe", "sent_bytes": 100,
                    "received_bytes": 200, "sent_packets": 1, "received_packets": 1,
                    "first_seen": "2026-08-08T12:00:01", "last_seen": "2026-08-08T12:00:59"})
            self.assertEqual(5000, db.conn.execute("SELECT COUNT(*) FROM flow_buckets").fetchone()[0])
            db.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.assertLess(db.get_db_size_mb(), 100)
            self.assertEqual(2, db.conn.execute("PRAGMA auto_vacuum").fetchone()[0])
            db.close()


if __name__ == "__main__":
    unittest.main()
