"""Offline tests for the separate IVASPER inventory; no external traffic."""
import ast
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from ivasper_external import normalize_inventory, valid_inventory_url, load_ivasper_inventory


class IvasperExternalTests(unittest.TestCase):
    def test_flat_stock_and_no_sms_feed(self):
        output = normalize_inventory({
            "numbers": [
                {"number": "+994501234567", "country": "Azərbaycan",
                 "service": "Telegram", "message": "SMS secret"},
                {"number": "+994501234567", "country": "Azərbaycan", "service": "Telegram"},
                {"number": "+447701112222", "service": "WhatsApp", "otp": "746829"},
                {"num": "+994551111111", "message": "This is an SMS receipt"},
                {"number": "<script>alert(1)</script>"},
            ]
        })
        self.assertEqual(len(output), 2)
        text = str(output)
        self.assertIn("+994501234567", text)
        for private in ("SMS secret", "746829", "script", "+994551111111"):
            self.assertNotIn(private, text)

    def test_ivasmsper_nested_stock(self):
        payload = {"services": {
            "Telegram": {"countries": {
                "Azerbaijan": {"numbers": ["+994501111111", "994502222222"]}}},
            "WhatsApp": {"countries": {"Germany": {"numbers": ["+4915112345678"]}}},
        }}
        output = normalize_inventory(payload)
        self.assertEqual(len(output), 3)
        self.assertEqual({item["service"] for item in output},
                         {"Telegram", "WhatsApp"})
        self.assertEqual({item["country"] for item in output},
                         {"Azerbaijan", "Germany"})

    def test_no_ivasms_fallback_and_no_credentials(self):
        for bad in ("http://example.com/feed", "https://127.0.0.1/stock",
                    "https://localhost/private", "https://[::1]/x",
                    "https://user:pass@example.com/stock",
                    "https://example.com:8080/api", "https://example.internal/stock"):
            self.assertFalse(valid_inventory_url(bad), bad)
        self.assertTrue(valid_inventory_url("https://inventory.example.com/api/numbers"))
        source = Path(__file__).resolve().parent
        code = (source / "main.py").read_text(encoding="utf-8")
        ast.parse(code)
        node = next(n for n in ast.parse(code).body
                    if isinstance(n, ast.AsyncFunctionDef)
                    and n.name == "miniapp_ivasper_api")
        body = ast.get_source_segment(code, node)
        self.assertIn("_miniapp_auth(request)", body)
        self.assertIn("not is_admin(uid) or is_user_banned(uid)", body)
        self.assertIn("await load_ivasper_inventory()", body)
        self.assertNotIn("load_range_db", body)
        self.assertNotIn("fetch_services_cached", body)
        self.assertNotIn("number_archive", body)
        self.assertNotIn("get_number_from_api", body)
        self.assertIn('"Cache-Control": "private, no-store"', body)

    def test_admin_import_separate_from_ivasmss(self):
        from pathlib import Path
        import ast
        code = Path(__file__).resolve().parent.joinpath("main.py").read_text(encoding="utf-8")
        node = next(n for n in ast.parse(code).body
                    if isinstance(n, ast.AsyncFunctionDef)
                    and n.name == "miniapp_ivasper_api")
        body = ast.get_source_segment(code, node)
        self.assertIn('request.method != "POST"', body)
        self.assertIn('not is_admin(uid) or is_user_banned(uid)', body)
        self.assertIn('IVASPER_IMPORT_TOKEN', body)
        self.assertIn('"/import"', body)
        self.assertIn('json={"numbers": rows}', body)
        for forbidden in ('save_range_db(', 'number_archive.record(',
                          'assign_active_number(', 'get_number_from_api('):
            self.assertNotIn(forbidden, body)

    def test_unconfigured_does_not_use_ivasmss_as_fallback(self):
        import asyncio
        with patch.dict(os.environ, {"IVASPER_NUMBERS_URL": ""}):
            result = asyncio.run(load_ivasper_inventory())
        self.assertFalse(result["connected"])
        self.assertEqual(result["status"], "not_configured")
        self.assertEqual(result["numbers"], [])


if __name__ == "__main__":
    unittest.main()
