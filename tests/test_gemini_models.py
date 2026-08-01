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


class GeminiRequestTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()