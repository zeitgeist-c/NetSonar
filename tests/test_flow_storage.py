import tempfile
import unittest
from pathlib import Path

from database import Database


class FlowStorageTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "flows.db")

    def tearDown(self):
        self.db.close()
        self.tempdir.cleanup()

    @staticmethod
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

    def test_packets_merge_into_one_minute_bucket_with_real_directions(self):
        for _ in range(1000):
            self.db.upsert_flow_bucket(self.flow())
        self.db.upsert_flow_bucket(self.flow(
            sent_bytes=0, sent_packets=0, received_bytes=1_000_000,
            received_packets=1, last_seen="2026-08-01T12:30:59"
        ))
        row = self.db.conn.execute("SELECT * FROM flow_buckets").fetchone()
        self.assertEqual(1, self.db.conn.execute("SELECT COUNT(*) FROM flow_buckets").fetchone()[0])
        self.assertEqual(100_000, row["sent_bytes"])
        self.assertEqual(1_000_000, row["received_bytes"])
        self.assertEqual(1000, row["sent_packets"])

    def test_high_water_claim_does_not_capture_later_traffic(self):
        first_id = self.db.upsert_flow_bucket(self.flow())
        batch = self.db.claim_pending_batch()
        second_id = self.db.upsert_flow_bucket(self.flow(remote_ip="8.8.8.8"))
        self.assertEqual(first_id, batch["high_water_id"])
        self.assertGreater(second_id, batch["high_water_id"])
        self.assertIsNone(self.db.conn.execute(
            "SELECT batch_id FROM flow_buckets WHERE id=?", (second_id,)
        ).fetchone()[0])

    def test_success_deletes_details_but_keeps_audit(self):
        self.db.upsert_flow_bucket(self.flow())
        batch = self.db.claim_pending_batch()
        self.db.complete_batch(batch["id"], 0.2, "safe")
        self.assertEqual(0, self.db.conn.execute("SELECT COUNT(*) FROM flow_buckets").fetchone()[0])
        run = self.db.conn.execute("SELECT * FROM analysis_runs").fetchone()
        self.assertEqual("safe", run["status"])
        self.assertEqual(1, run["flow_count"])
        rollup = self.db.conn.execute("SELECT * FROM hourly_rollups").fetchone()
        self.assertEqual(100, rollup["sent_bytes"])

    def test_failure_releases_flows_for_retry(self):
        self.db.upsert_flow_bucket(self.flow())
        failed = self.db.claim_pending_batch()
        self.db.fail_batch(failed["id"], "temporary")
        retried = self.db.claim_pending_batch()
        self.assertIsNotNone(retried)
        self.assertEqual(failed["id"], retried["id"])
        self.assertEqual(1, len(self.db.get_batch_flows(retried["id"])))

    def test_risky_batch_keeps_finding_but_not_raw_flow(self):
        flow_id = self.db.upsert_flow_bucket(self.flow())
        batch = self.db.claim_pending_batch()
        self.db.complete_batch(batch["id"], 9.0, "risky", [{
            "severity": "critical", "confidence": .99, "evidence": "local evidence",
            "flow_refs": [flow_id], "recommended_action": "review", "block_now": False,
            "flow_evidence": [{"flow_id": flow_id, "remote_ip": "1.1.1.1"}],
        }])
        self.assertEqual(0, self.db.conn.execute("SELECT COUNT(*) FROM flow_buckets").fetchone()[0])
        finding = self.db.get_security_findings()[0]
        self.assertEqual("open", finding["status"])
        self.assertTrue(self.db.resolve_security_finding(finding["id"]))
        self.assertTrue(self.db.delete_security_finding(finding["id"]))
        self.assertEqual([], self.db.get_security_findings())

    def test_full_report_and_sources_survive_history_reload(self):
        self.db.upsert_flow_bucket(self.flow())
        batch = self.db.claim_pending_batch()
        report = {"risk_score": 8.0, "status": "risky", "summary": "current intel",
                  "intel_sources": [{"source_ref":"vt:1.1.1.1","indicator":"1.1.1.1"}],
                  "web_sources": [{"source_ref":"web:1.1.1.1:0","url":"https://example.com"}],
                  "findings": []}
        self.db.complete_batch(batch["id"], 8.0, "risky", [], report)
        import json
        restored = json.loads(self.db.get_all_reports()[0]["content"])
        self.assertEqual("current intel", restored["summary"])
        self.assertEqual("vt:1.1.1.1", restored["intel_sources"][0]["source_ref"])


if __name__ == "__main__":
    unittest.main()
