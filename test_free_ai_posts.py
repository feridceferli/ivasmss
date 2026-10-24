"""Offline regression checks for optional free Groq captions (no network calls)."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import free_ai_posts as ai
from global_availability_feed import availability_snapshot, compose_availability_notice


def prefix(rid):
    return "994" if rid.startswith("994") else "44"


SAMPLE = {"wa": ["99450210", "447700"], "tg": ["99450211"]}


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


class FakeClient:
    def __init__(self, content):
        self.content = content
        self.request = None

    async def post(self, endpoint, json, headers):
        self.request = (endpoint, json, headers)
        return FakeResponse(self.content)


class FreeAiSettingsTests(unittest.TestCase):
    def test_persisted_validated_settings_and_hidden_key(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(ai, "SETTINGS_FILE", str(Path(folder) / "ai.json")):
                self.assertEqual(ai.load_ai_settings()["style"], "energetic")
                ai.save_ai_settings(False, "minimal")
                self.assertFalse(ai.load_ai_settings()["enabled"])
                with self.assertRaises(ValueError):
                    ai.save_ai_settings("false", "minimal")
                with self.assertRaises(ValueError):
                    ai.save_ai_settings(True, "unsupported")
                with patch.dict(os.environ, {"GROQ_API_KEY": "test-secret"}):
                    view = ai.public_ai_status()
                    self.assertTrue(view["key_configured"])
                    self.assertNotIn("test-secret", repr(view))


class FreeAiCopyTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_aggregates_are_sent_not_ranges_or_private_data(self):
        snapshot = availability_snapshot(SAMPLE, prefix)
        fake = FakeClient("✨ Xidmət kataloqu yenilənib, məlumatlara baxın!")
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-secret"}):
            result = await ai.generate_intro(snapshot, client=fake)
        self.assertIn("kataloqu", result)
        endpoint, payload, headers = fake.request
        self.assertEqual(endpoint, ai.GROQ_ENDPOINT)
        self.assertEqual(headers["Authorization"], "Bearer test-secret")
        self.assertEqual(set(json.loads(payload["messages"][1]["content"])),
                         {"services", "countries", "range_entries"})
        self.assertNotIn("99450210", str(payload))
        self.assertNotIn("447700", str(payload))

    async def test_untrusted_model_output_is_replaced(self):
        snapshot = availability_snapshot(SAMPLE, prefix)
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-secret"}):
            for sentence in (
                "500 aktiv nömrə var",
                "<b>Kataloq</b> yeniləndi",
                "https://example.org xidmət siyahısı",
                "OTP kodları gəlir",
            ):
                result = await ai.generate_intro(snapshot, client=FakeClient(sentence))
                self.assertEqual(result, ai.FALLBACK["energetic"])

    async def test_keyless_fallback_and_disabled_mode(self):
        snapshot = availability_snapshot(SAMPLE, prefix)
        base = compose_availability_notice(snapshot)
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(ai, "SETTINGS_FILE", str(Path(folder) / "ai.json")):
                with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
                    result = await ai.decorate_feed(snapshot, {}, base)
                    self.assertTrue(result.endswith(base))
                    self.assertNotIn("99450210", result)
                ai.save_ai_settings(False, "minimal")
                self.assertEqual(await ai.decorate_feed(snapshot, {}, base), base)


if __name__ == "__main__":
    unittest.main()
