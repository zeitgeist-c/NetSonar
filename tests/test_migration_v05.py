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


if __name__ == "__main__":
    unittest.main()
