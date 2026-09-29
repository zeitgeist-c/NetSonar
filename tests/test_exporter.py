"""Exporter: format yuvarlakliği + CSV formül kaçışı regresyon koruması."""
import csv
import json
import os
import tempfile
import unittest

from exporter import _csv_cell, _suspicious_rows, export_report

REPORT = {
    "analysis_time": "2026-09-30T00:00:00",
    "risk_score": 8.5,
    "status": "review",
    "summary": "özet metni",
    "suspicious_connections": [
        {"ip": "1.2.3.4", "port": 4444, "process": "evil.exe",
         "reason": "şüpheli port", "action": "İncele"},
    ],
}


class ExporterTest(unittest.TestCase):
    def test_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.json")
            export_report(REPORT, "json", path)
            with open(path, encoding="utf-8") as f:
                self.assertEqual(json.load(f)["risk_score"], 8.5)

    def test_csv_escapes_formula_cells(self):
        bad = dict(REPORT, summary="=HYPERLINK(\"x\")",
                   suspicious_connections=[{"ip": "1.2.3.4", "port": 1,
                                            "process": "=cmd|evil", "reason": "+1",
                                            "action": "@x"}])
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.csv")
            export_report(bad, "csv", path)
            with open(path, encoding="utf-8", newline="") as f:
                cells = [c for row in csv.reader(f) for c in row]
        for dangerous in ("=cmd|evil", "+1", "@x"):
            self.assertNotIn(dangerous, cells)
        self.assertIn("'=cmd|evil", cells)

    def test_csv_cell_passthrough(self):
        self.assertEqual(_csv_cell("normal"), "normal")
        self.assertEqual(_csv_cell(None), "")
        self.assertEqual(_csv_cell(443), "443")

    def test_suspicious_rows_finding_shape(self):
        report = {"findings": [{"evidence": "kanıt", "recommended_action": "Engelle",
                                "flow_evidence": [{"remote_ip": "9.9.9.9",
                                                   "remote_port": 53,
                                                   "process": "dns.exe"}]}]}
        rows = _suspicious_rows(report)
        self.assertEqual(rows[0]["ip"], "9.9.9.9")

    def test_unsupported_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                export_report(REPORT, "xml", os.path.join(tmp, "r.xml"))


if __name__ == "__main__":
    unittest.main()
