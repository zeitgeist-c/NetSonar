import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import requests

from database import Database
from threat_intel import ThreatIntelService, rank_candidates, _BACKOFF_UNTIL


def cfg(**values):
    defaults = dict(VIRUSTOTAL_API_KEY="vt-key", TAVILY_API_KEY="tvly-key",
        VIRUSTOTAL_DAILY_SOFT_LIMIT=480, TAVILY_MONTHLY_SOFT_LIMIT=900,
        THREAT_INTEL_ERROR_BACKOFF_MINUTES=15, THREAT_INTEL_CACHE_HOURS=24,
        THREAT_INTEL_UNKNOWN_CACHE_HOURS=6, VIRUSTOTAL_MAX_LOOKUPS_PER_RUN=4,
        TAVILY_MAX_SEARCHES_PER_RUN=2, SUSPICIOUS_PORTS={4444},
        SUSPICIOUS_PROCESSES={"powershell.exe"}, SUSPICIOUS_BYTES_THRESHOLD=1000)
    defaults.update(values)
    return SimpleNamespace(**defaults)


class Response:
    def __init__(self, status=200, data=None):
        self.status_code, self._data, self.headers = status, data or {}, {}
    def json(self): return self._data


class Session:
    def __init__(self, get_response=None, post_response=None):
        self.get_response, self.post_response = get_response, post_response
        self.get_calls, self.post_calls = [], []
    def get(self, *args, **kwargs):
        self.get_calls.append((args, kwargs))
        response = self.get_response.pop(0) if isinstance(self.get_response, list) else self.get_response
        if isinstance(response, Exception): raise response
        return response
    def post(self, *args, **kwargs):
        self.post_calls.append((args, kwargs))
        response = self.post_response.pop(0) if isinstance(self.post_response, list) else self.post_response
        if isinstance(response, Exception): raise response
        return response


class ThreatIntelTests(unittest.TestCase):
    def setUp(self):
        _BACKOFF_UNTIL.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "intel.db")
    def tearDown(self):
        self.db.close(); self.tmp.cleanup()

    def test_candidate_ranking_excludes_non_public_and_scores_signals(self):
        rows = [{"remote_ip":"192.168.1.2","remote_port":4444,"process":"powershell.exe",
                 "sent_bytes":5000,"flow_count":5,"first_seen":"2026-08-01T03:00:00","last_seen":""},
                {"remote_ip":"8.8.8.8","remote_port":4444,"process":"powershell.exe",
                 "sent_bytes":5000,"flow_count":5,"first_seen":"2026-08-01T03:00:00","last_seen":""}]
        ranked = rank_candidates(rows, {4444}, {"powershell.exe"}, 1000)
        self.assertEqual(["8.8.8.8"], [x["ip"] for x in ranked])
        self.assertEqual(11, ranked[0]["local_score"])

    def test_virustotal_normalizes_and_caches(self):
        session = Session(get_response=Response(data={"data":{"attributes":{
            "last_analysis_stats":{"malicious":4,"suspicious":1,"harmless":2,"undetected":3},
            "reputation":-5,"last_analysis_date":123}}}))
        service = ThreatIntelService(self.db, session)
        first = service.lookup_virustotal("8.8.8.8", cfg())
        second = service.lookup_virustotal("8.8.8.8", cfg())
        self.assertEqual("malicious", first["verdict"])
        self.assertTrue(second["cached"])
        self.assertEqual(1, len(session.get_calls))

    def test_virustotal_404_is_unknown_and_errors_are_nonfatal(self):
        service = ThreatIntelService(self.db, Session(get_response=Response(404)))
        self.assertEqual("unknown", service.lookup_virustotal("8.8.4.4", cfg())["verdict"])
        timeout = ThreatIntelService(self.db, Session(get_response=requests.Timeout()))
        self.assertIsNone(timeout.lookup_virustotal("1.1.1.1", cfg()))

    def test_tavily_uses_privacy_limited_request_and_sanitizes(self):
        session = Session(post_response=Response(data={"results":[{
            "title":"Result\x00 title","url":"https://example.com/ioc",
            "content":"evidence\x01 " + "x"*700,"score":0.8}]}))
        sources = ThreatIntelService(self.db, session).search_tavily("8.8.8.8", cfg())
        request = session.post_calls[0][1]["json"]
        self.assertIn('"8.8.8.8"', request["query"])
        self.assertNotIn("process", str(request).lower())
        self.assertFalse(request["include_raw_content"])
        self.assertLessEqual(len(sources[0]["snippet"]), 500)
        self.assertNotIn("\x01", sources[0]["snippet"])

    def test_provider_failures_do_not_raise(self):
        for status in (401, 403, 429, 500):
            with self.subTest(status=status):
                _BACKOFF_UNTIL.clear()
                service = ThreatIntelService(self.db, Session(
                    get_response=Response(status), post_response=Response(status)))
                self.assertIsNone(service.lookup_virustotal(f"8.8.8.{status % 10}", cfg()))
                self.assertEqual([], service.search_tavily(f"9.9.9.{status % 10}", cfg()))

    def test_virustotal_uses_default_key_then_falls_back(self):
        session = Session(get_response=[Response(429), Response(data={"data":{"attributes":{
            "last_analysis_stats":{"malicious":0,"suspicious":0,"harmless":1}}}})])
        result = ThreatIntelService(self.db, session).lookup_virustotal(
            "8.8.8.8", cfg(VIRUSTOTAL_API_KEYS=["default-vt", "backup-vt"]))
        self.assertEqual("clean", result["verdict"])
        self.assertEqual("default-vt", session.get_calls[0][1]["headers"]["x-apikey"])
        self.assertEqual("backup-vt", session.get_calls[1][1]["headers"]["x-apikey"])
        self.assertNotIn("virustotal", _BACKOFF_UNTIL)

    def test_tavily_uses_default_key_then_falls_back(self):
        session = Session(post_response=[requests.Timeout(), Response(data={"results":[]} )])
        ThreatIntelService(self.db, session).search_tavily(
            "9.9.9.9", cfg(TAVILY_API_KEYS=["default-tvly", "backup-tvly"]))
        self.assertEqual("Bearer default-tvly", session.post_calls[0][1]["headers"]["Authorization"])
        self.assertEqual("Bearer backup-tvly", session.post_calls[1][1]["headers"]["Authorization"])
        self.assertNotIn("tavily", _BACKOFF_UNTIL)

    def test_valid_not_found_does_not_rotate_keys(self):
        session = Session(get_response=Response(404))
        result = ThreatIntelService(self.db, session).lookup_virustotal(
            "1.0.0.1", cfg(VIRUSTOTAL_API_KEYS=["default-vt", "backup-vt"]))
        self.assertEqual("unknown", result["verdict"])
        self.assertEqual(1, len(session.get_calls))


if __name__ == "__main__": unittest.main()
