"""Report history: findings must arrive in a single query (N+1 regression protection).

The old code ran a separate `SELECT ... WHERE batch_id=?` per report row;
measured 1201 queries and 175 ms on a 1200-report history.
"""

import json
import tempfile
import unittest
from pathlib import Path

from database import Database

FLOW = {
    "bucket_start": "2026-10-27T03:00:00", "local_ip": "10.0.0.2",
    "local_port": 40000, "remote_ip": "93.0.0.1", "remote_port": 443,
    "protocol": "TCP", "process": "x", "sent_bytes": 1, "received_bytes": 1,
    "sent_packets": 1, "received_packets": 1,
    "first_seen": "2026-10-27T03:00:01", "last_seen": "2026-10-27T03:00:02",
}


class ReportFindingsQueryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "reports.db")
        self.batch_ids = []
        for index in range(25):
            self.db.upsert_flow_bucket(dict(FLOW, local_port=40000 + index,
                                            remote_ip=f"93.0.0.{index}"))
            batch = self.db.claim_pending_batch()
            self.batch_ids.append(batch["id"])
            findings = [{
                "severity": "low", "confidence": 0.5, "evidence": f"e{item}",
                "flow_refs": [1], "recommended_action": "r", "block_now": False,
                "flow_evidence": [], "source_evidence": [],
            } for item in range(3)]
            self.db.complete_batch(batch["id"], 1.0, "safe", findings,
                                   {"summary": f"s{index}"})

    def tearDown(self):
        self.db.close()
        self.tempdir.cleanup()

    @staticmethod
    def _content(report):
        return json.loads(report["content"])

    def test_history_uses_one_findings_query(self):
        statements = []
        self.db.conn.set_trace_callback(statements.append)
        try:
            reports = self.db.get_all_reports()
        finally:
            self.db.conn.set_trace_callback(None)
        self.assertEqual(25, len(reports))
        self.assertLessEqual(len(statements), 3, statements)

    def test_findings_are_grouped_per_report(self):
        for report in self.db.get_all_reports():
            findings = self._content(report)["findings"]
            self.assertEqual(3, len(findings))
            self.assertTrue(all(isinstance(f["flow_refs"], list) for f in findings))

    def test_findings_belong_to_their_own_report(self):
        by_summary = {}
        for report in self.db.get_all_reports():
            content = self._content(report)
            by_summary[content["summary"]] = {f["evidence"] for f in content["findings"]}
        self.assertEqual(len(by_summary), 25)
        self.assertEqual({"e0", "e1", "e2"}, by_summary["s0"])

    def test_missing_batch_ids_yield_empty_map(self):
        self.assertEqual({}, self.db._findings_by_batch([]))
        self.assertEqual({}, self.db._findings_by_batch([None]))

    def test_corrupt_evidence_json_degrades_to_empty_list(self):
        self.db.conn.execute(
            "UPDATE security_findings SET flow_evidence='not json' WHERE id=1")
        self.db.conn.commit()
        grouped = self.db._findings_by_batch(self.batch_ids)
        flat = [finding for items in grouped.values() for finding in items]
        self.assertTrue(flat)
        self.assertTrue(any(f["flow_evidence"] == [] for f in flat))


if __name__ == "__main__":
    unittest.main()
