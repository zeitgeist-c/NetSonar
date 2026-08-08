import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import PropertyMock, patch

import ai_analyzer
from ai_analyzer import AIAnalyzer
from database import Database


class AnalysisBatchTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tempdir.name) / "analysis.db")
        for index in range(201):
            self.db.upsert_flow_bucket({
                "bucket_start": "2026-08-01T12:30:00", "local_ip": "10.0.0.2",
                "local_port": 50000 + index, "remote_ip": "1.1.1.1", "remote_port": 443,
                "protocol": "TCP", "process": "test.exe", "sent_bytes": 1,
                "sent_packets": 1, "first_seen": "2026-08-01T12:30:01",
                "last_seen": "2026-08-01T12:30:01",
            })
        self.analyzer = AIAnalyzer.__new__(AIAnalyzer)
        self.analyzer.db = self.db

    def tearDown(self):
        self.db.close()
        self.tempdir.cleanup()

    def test_pending_analysis_chunks_and_deletes_details(self):
        sizes = []
        def provider(payload):
            flows = json.loads(payload)["flows"]
            sizes.append(len(flows))
            return {"risk_score": 0, "status": "safe", "summary": "ok", "findings": []}
        with patch.dict(ai_analyzer.PROVIDERS, {"gemini": provider}), patch.object(
            AIAnalyzer, "provider", new_callable=PropertyMock, return_value="gemini"
        ):
            result = self.analyzer.analyze_pending()
        self.assertEqual([200, 1], sizes)
        self.assertEqual(0, self.db.conn.execute("SELECT COUNT(*) FROM flow_buckets").fetchone()[0])
        self.assertEqual(201, result["_meta"]["flow_count"])
        self.assertEqual(2, self.db.conn.execute(
            "SELECT COUNT(*) FROM analysis_chunks WHERE status='completed'"
        ).fetchone()[0])

    def test_out_of_batch_reference_keeps_batch_pending(self):
        invalid = {"risk_score": 9, "status": "risk", "summary": "bad", "findings": [{
            "flow_refs": [999999], "severity": "critical", "confidence": .99,
            "evidence": "invented", "recommended_action": "block", "block_now": True,
        }]}
        with patch.dict(ai_analyzer.PROVIDERS, {"gemini": lambda payload: invalid}), patch.object(
            AIAnalyzer, "provider", new_callable=PropertyMock, return_value="gemini"
        ):
            result = self.analyzer.analyze_pending()
        self.assertEqual("API HATASI", result["status"])
        self.assertEqual("pending", self.db.conn.execute(
            "SELECT status FROM analysis_batches"
        ).fetchone()[0])
        self.assertEqual(201, self.db.conn.execute("SELECT COUNT(*) FROM flow_buckets").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
