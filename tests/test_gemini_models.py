import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import ai_analyzer
import config


class FakeResponse:
    status_code = 200
    text = ""

    def json(self):
        return {
            "candidates": [
                {"content": {"parts": [{"text": '{"status": "ok"}'}]}}
            ]
        }


class FakeSession:
    def __init__(self):
        self.request = None

    def post(self, endpoint, **kwargs):
        self.request = (endpoint, kwargs)
        return FakeResponse()


class GeminiSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_settings_file = config.SETTINGS_FILE
        config.SETTINGS_FILE = os.path.join(self.temp_dir.name, "settings.json")

    def tearDown(self):
        config.SETTINGS_FILE = self.original_settings_file
        self.temp_dir.cleanup()

    def write_settings(self, data):
        with open(config.SETTINGS_FILE, "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    def test_new_settings_default_to_gemini_35(self):
        settings = config.load_settings()

        self.assertEqual(config.DEFAULT_GEMINI_MODEL, settings["GEMINI_MODEL"])
        self.assertEqual(
            config.GEMINI_MODEL_SELECTION_VERSION,
            settings["GEMINI_MODEL_SELECTION_VERSION"],
        )

    def test_legacy_31_is_migrated_once_then_user_choice_is_preserved(self):
        self.write_settings({"GEMINI_MODEL": "gemini-3.1-flash-lite"})

        migrated = config.load_settings()
        self.assertEqual("gemini-3.5-flash-lite", migrated["GEMINI_MODEL"])

        migrated["GEMINI_MODEL"] = "gemini-3.1-flash-lite"
        config.save_settings(migrated)

        reloaded = config.load_settings()
        self.assertEqual("gemini-3.1-flash-lite", reloaded["GEMINI_MODEL"])

    def test_unsupported_model_falls_back_to_default(self):
        self.write_settings(
            {
                "GEMINI_MODEL": "gemini-unknown",
                "GEMINI_MODEL_SELECTION_VERSION": (
                    config.GEMINI_MODEL_SELECTION_VERSION
                ),
            }
        )

        settings = config.load_settings()

        self.assertEqual("gemini-3.5-flash-lite", settings["GEMINI_MODEL"])

    def test_plaintext_api_key_is_migrated_to_dpapi(self):
        self.write_settings({
            "GEMINI_API_KEY": "secret-key", "GEMINI_API_KEYS": ["secret-key"],
            "GEMINI_MODEL": config.DEFAULT_GEMINI_MODEL,
            "GEMINI_MODEL_SELECTION_VERSION": config.GEMINI_MODEL_SELECTION_VERSION,
        })
        with patch.object(config, "protect_secret", return_value="dpapi:encrypted"):
            loaded = config.load_settings()
        self.assertEqual(["secret-key"], loaded["GEMINI_API_KEYS"])
        with open(config.SETTINGS_FILE, "r", encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertTrue(stored["GEMINI_API_KEYS"][0].startswith("dpapi:"))
        self.assertNotIn("secret-key", json.dumps(stored))

    def test_external_provider_keys_are_migrated_to_dpapi(self):
        self.write_settings({
            "VIRUSTOTAL_API_KEY": "vt-secret", "TAVILY_API_KEY": "tvly-secret",
            "GEMINI_MODEL": config.DEFAULT_GEMINI_MODEL,
            "GEMINI_MODEL_SELECTION_VERSION": config.GEMINI_MODEL_SELECTION_VERSION,
        })
        with patch.object(config, "protect_secret", side_effect=lambda value:
                          "dpapi:" + value if value else ""), patch.object(
            config, "unprotect_secret", side_effect=lambda value:
                value.removeprefix("dpapi:")):
            loaded = config.load_settings()
        self.assertEqual("vt-secret", loaded["VIRUSTOTAL_API_KEY"])
        self.assertEqual("tvly-secret", loaded["TAVILY_API_KEY"])
        with open(config.SETTINGS_FILE, "r", encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertTrue(stored["VIRUSTOTAL_API_KEY"].startswith("dpapi:"))
        self.assertNotIn('"vt-secret"', json.dumps(stored))


class GeminiRequestTests(unittest.TestCase):
    def setUp(self):
        ai_analyzer._GEMINI_KEY_COOLDOWNS.clear()
        ai_analyzer._GEMINI_SERVICE_BACKOFF_UNTIL = 0
        ai_analyzer._GEMINI_SERVICE_FAILURES = 0

    def run_request(self, model):
        fake_config = SimpleNamespace(
            GEMINI_API_KEYS=[f"key-{model}"],
            GEMINI_API_KEY="",
            GEMINI_MODEL=model,
            AI_PROMPT="Return JSON.",
        )
        session = FakeSession()
        with (
            patch.object(ai_analyzer, "_cfg", return_value=fake_config),
            patch.object(ai_analyzer, "_session", return_value=session),
        ):
            result = ai_analyzer._analyze_gemini("Analyze.")

        self.assertEqual({"status": "ok"}, result)
        return session.request

    def test_gemini_35_omits_temperature(self):
        endpoint, request = self.run_request("gemini-3.5-flash-lite")

        self.assertIn("/models/gemini-3.5-flash-lite:generateContent", endpoint)
        self.assertEqual("key-gemini-3.5-flash-lite", request["headers"]["x-goog-api-key"])
        self.assertNotIn("params", request)
        self.assertNotIn("temperature", request["json"]["generationConfig"])

    def test_gemini_31_keeps_temperature(self):
        endpoint, request = self.run_request("gemini-3.1-flash-lite")

        self.assertIn("/models/gemini-3.1-flash-lite:generateContent", endpoint)
        self.assertEqual(0.2, request["json"]["generationConfig"]["temperature"])

    def test_validation_accepts_both_supported_models(self):
        analyzer = ai_analyzer.AIAnalyzer.__new__(ai_analyzer.AIAnalyzer)
        for model in config.SUPPORTED_GEMINI_MODELS:
            fake_config = SimpleNamespace(
                AI_PROVIDER="gemini",
                GEMINI_MODEL=model,
                GEMINI_API_KEYS=["key"],
                SUPPORTED_GEMINI_MODELS=config.SUPPORTED_GEMINI_MODELS,
            )
            with self.subTest(model=model), patch.object(
                ai_analyzer, "_cfg", return_value=fake_config
            ):
                self.assertEqual([], analyzer.validate_config())

    def test_403_rotates_to_next_key(self):
        class Response:
            headers = {}
            def __init__(self, status):
                self.status_code, self.text = status, "denied"
            def json(self):
                return FakeResponse().json()
        class Session:
            def __init__(self): self.calls = []
            def post(self, endpoint, **kwargs):
                self.calls.append(kwargs)
                return Response(403 if len(self.calls) == 1 else 200)
        cfg = SimpleNamespace(GEMINI_API_KEYS=["bad", "good"], GEMINI_API_KEY="",
                              GEMINI_MODEL="gemini-3.5-flash-lite", AI_PROMPT="Return JSON")
        session = Session()
        with patch.object(ai_analyzer, "_cfg", return_value=cfg), patch.object(
            ai_analyzer, "_session", return_value=session
        ):
            self.assertEqual({"status": "ok"}, ai_analyzer._analyze_gemini("Analyze"))
        self.assertEqual(["bad", "good"],
            [call["headers"]["x-goog-api-key"] for call in session.calls])

    def test_429_retry_after_marks_only_current_key(self):
        class Response:
            text = "limited"
            def __init__(self, status, retry=None):
                self.status_code = status
                self.headers = {"Retry-After": retry} if retry else {}
            def json(self): return FakeResponse().json()
        responses = iter([Response(429, "12"), Response(200)])
        session = SimpleNamespace(post=lambda *args, **kwargs: next(responses))
        cfg = SimpleNamespace(GEMINI_API_KEYS=["limited", "ready"], GEMINI_API_KEY="",
                              GEMINI_MODEL="gemini-3.5-flash-lite", AI_PROMPT="Return JSON")
        with patch.object(ai_analyzer, "_cfg", return_value=cfg), patch.object(
            ai_analyzer, "_session", return_value=session
        ):
            ai_analyzer._analyze_gemini("Analyze")
        self.assertIn("limited", ai_analyzer._GEMINI_KEY_COOLDOWNS)
        self.assertNotIn("ready", ai_analyzer._GEMINI_KEY_COOLDOWNS)

    def test_invalid_api_key_rotates_to_next_key(self):
        class Response:
            headers = {}
            def __init__(self, status, body=""):
                self.status_code, self.text = status, body
            def json(self): return FakeResponse().json()
        responses = iter([
            Response(400, '{"error":{"status":"API_KEY_INVALID"}}'),
            Response(200),
        ])
        session = SimpleNamespace(post=lambda *args, **kwargs: next(responses))
        cfg = SimpleNamespace(GEMINI_API_KEYS=["invalid", "ready"], GEMINI_API_KEY="",
                              GEMINI_MODEL="gemini-3.5-flash-lite", AI_PROMPT="Return JSON")
        with patch.object(ai_analyzer, "_cfg", return_value=cfg), patch.object(
            ai_analyzer, "_session", return_value=session
        ):
            self.assertEqual({"status": "ok"}, ai_analyzer._analyze_gemini("Analyze"))
        self.assertIn("invalid", ai_analyzer._GEMINI_KEY_COOLDOWNS)
        self.assertNotIn("ready", ai_analyzer._GEMINI_KEY_COOLDOWNS)

    def test_503_sets_service_wide_exponential_backoff(self):
        response = SimpleNamespace(status_code=503, text="busy", headers={})
        session = SimpleNamespace(post=lambda *args, **kwargs: response)
        cfg = SimpleNamespace(GEMINI_API_KEYS=["key"], GEMINI_API_KEY="",
                              GEMINI_MODEL="gemini-3.5-flash-lite", AI_PROMPT="Return JSON")
        with patch.object(ai_analyzer, "_cfg", return_value=cfg), patch.object(
            ai_analyzer, "_session", return_value=session
        ), self.assertRaises(ai_analyzer.GeminiQuotaError):
            ai_analyzer._analyze_gemini("Analyze")
        self.assertEqual(1, ai_analyzer._GEMINI_SERVICE_FAILURES)
        self.assertGreater(ai_analyzer._GEMINI_SERVICE_BACKOFF_UNTIL, 0)


if __name__ == "__main__":
    unittest.main()
