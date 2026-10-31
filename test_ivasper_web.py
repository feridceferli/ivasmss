"""Offline privacy, catalogue and allocation-scope checks for the web IVASPER panel."""
import ast
import unittest
from datetime import datetime
from pathlib import Path

from ivasper_web import catalog_snapshot

ROOT = Path(__file__).resolve().parent


class IvasperWebTests(unittest.TestCase):
    def test_only_owned_current_numbers_and_clean_catalogue(self):
        timestamp = datetime(2026, 10, 31)
        services = {
            "wa": ["99450210", "99450210", "1202444"],
            "tg": ["44770"],
            "<bad>": ["99450"],
            "empty": ["xyz"],
        }
        archive = {
            "994502101122": {"country": "Azerbaijan", "user_id": "7777",
                             "message": "otp-secrets-must-not-leak"},
        }
        active = {
            "994502101122": {"uid": 5, "range": "99450210", "timestamp": timestamp, "left": 90},
            "447701234567": {"uid": 8, "range": "44770", "timestamp": timestamp, "left": 90},
            "994502199999": {"uid": 5, "range": "99450219", "timestamp": timestamp, "left": 0},
        }
        result = catalog_snapshot(
            services, archive, {"state": "ok", "http_status": 200,
                                "last_error": "password=test-secret"},
            active, 5, lambda info: info["left"])
        self.assertEqual(result["services"]["wa"], ["1202444", "99450210"])
        self.assertNotIn("<bad>", result["services"])
        self.assertEqual((result["service_count"], result["range_count"]), (2, 3))
        self.assertEqual(result["archive_count"], 1)
        self.assertEqual(len(result["own_active"]), 1)
        self.assertEqual(result["own_active"][0]["number"], "+994502101122")
        encoded = str(result)
        for secret in ("447701234567", "994502199999", "otp-secrets-must-not-leak", "7777", "test-secret"):
            self.assertNotIn(secret, encoded)

    def test_input_validations_and_monitored_status(self):
        result = catalog_snapshot(
            {"bad": {"ranges": ["1"]}, "wa": ["abc", "", "12345678901", "9945"]},
            [], {"state": "<error>", "http_status": "200", "token": "secret"},
            {"994501234567": {"uid": 0, "left": 45}},
            5, lambda info: info["left"])
        self.assertEqual(result["services"], {"wa": ["9945"]})
        self.assertEqual(result["own_active"], [])
        self.assertIsNone(result["monitor"]["http_status"])
        self.assertEqual(result["monitor"]["state"], "naməlum")
        self.assertNotIn("secret", str(result))

    def test_server_restricts_method_and_admin_identity(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(node for node in tree.body
                        if isinstance(node, ast.AsyncFunctionDef)
                        and node.name == "miniapp_ivasper_api")
        body = ast.get_source_segment(source, function)
        self.assertIn("_miniapp_auth(request)", body)
        self.assertIn("not is_admin(uid) or is_user_banned(uid)", body)
        self.assertIn('request.method != "GET"', body)
        self.assertIn('"Cache-Control": "private, no-store"', body)
        self.assertIn("catalog_snapshot(", body)
        self.assertIn('"/api/ivasper", miniapp_ivasper_api', source)


if __name__ == "__main__":
    unittest.main()
