import sqlite3
import tempfile
import unittest
from pathlib import Path

from migration import needs_v05_reset, perform_v05_reset


class MigrationTests(unittest.TestCase):
    def make_legacy(self, path):
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE connections(id INTEGER PRIMARY KEY, dst_ip TEXT)")
        connection.execute("INSERT INTO connections(dst_ip) VALUES('8.8.8.8')")
        connection.commit()
        connection.close()

    def test_success_replaces_legacy_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "connections.db"
            self.make_legacy(path)
            self.assertTrue(needs_v05_reset(path))
            perform_v05_reset(path, firewall_cleanup=lambda: True)
            self.assertFalse(needs_v05_reset(path))
            connection = sqlite3.connect(path)
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            connection.close()
            self.assertIn("flow_buckets", tables)
            self.assertNotIn("connections", tables)

    def test_firewall_failure_preserves_legacy_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "connections.db"
            self.make_legacy(path)
            with self.assertRaises(RuntimeError):
                perform_v05_reset(path, firewall_cleanup=lambda: False)
            connection = sqlite3.connect(path)
            self.assertEqual(1, connection.execute("SELECT COUNT(*) FROM connections").fetchone()[0])
            connection.close()

    def test_v5_database_is_additively_upgraded_to_v6(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "connections.db"
            connection = sqlite3.connect(path)
            connection.executescript("""
                CREATE TABLE app_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                INSERT INTO app_metadata VALUES('schema_version','5');
                CREATE TABLE analysis_runs(id INTEGER PRIMARY KEY,batch_id INTEGER,
                    analyzed_at TEXT NOT NULL,status TEXT NOT NULL,risk_score REAL NOT NULL,
                    flow_count INTEGER NOT NULL DEFAULT 0);
                INSERT INTO analysis_runs VALUES(1,1,'2026-08-01','safe',0.1,7);
                CREATE TABLE security_findings(id INTEGER PRIMARY KEY,batch_id INTEGER,
                    created_at TEXT NOT NULL,severity TEXT NOT NULL,confidence REAL NOT NULL,
                    evidence TEXT NOT NULL,flow_refs TEXT NOT NULL,recommended_action TEXT,
                    block_now INTEGER NOT NULL DEFAULT 0,flow_evidence TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'open');
            """)
            connection.commit(); connection.close()
            from database import Database
            db = Database(path)
            self.assertEqual("6", db.conn.execute("SELECT value FROM app_metadata WHERE key='schema_version'").fetchone()[0])
            self.assertEqual(7, db.conn.execute("SELECT flow_count FROM analysis_runs").fetchone()[0])
            self.assertIn("report_json", {r[1] for r in db.conn.execute("PRAGMA table_info(analysis_runs)")})
            db.close()
            self.assertFalse(needs_v05_reset(path))


if __name__ == "__main__":
    unittest.main()
