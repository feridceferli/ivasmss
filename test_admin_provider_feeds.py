"""Offline tests; no provider credentials or live SMS required."""
import ast
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import admin_provider_feeds as feeds


class ProviderAdapterTests(unittest.TestCase):
    def test_green_rest_format(self):
        rows = feeds.parse_green_payload({
            "results": [
                {"id": 11, "number": "+994500000000", "sms": "test sms",
                 "sender": "Example", "created_at": "2026-10-31"}
            ]
        })
        self.assertEqual(rows[0]["number"], "+994500000000")
        self.assertEqual(rows[0]["message"], "test sms")
        self.assertEqual(rows[0]["source"], "Green SMS")

    def test_ivas_panel_formats(self):
        records = feeds.parse_ivas_payload({
            "status": "success",
            "data": [{"dt": "now", "num": "+123", "cli": "test",
                      "message": "synthetic test"}]
        })
        self.assertEqual(records[0]["number"], "+123")
        self.assertEqual(records[0]["message"], "synthetic test")
        legacy = feeds.parse_ivas_payload([["service", "+44", "sms", "time"]])
        self.assertEqual(legacy[0]["number"], "+44")

    def test_strict_provider_response_and_caps(self):
        with self.assertRaises(feeds.ProviderFeedError):
            feeds.parse_green_payload({"results": "wrong"})
        with self.assertRaises(feeds.ProviderFeedError):
            feeds.parse_ivas_payload({"status": "failure", "data": []})
        self.assertLessEqual(len(feeds.parse_green_payload(
            {"results": [{"id": i} for i in range(100)]})), 30)

    def test_required_secure_urls(self):
        for bad in ("http://example.org/api", "https://localhost/api",
                    "https://name:pass@example.org", "not-a-url"):
            self.assertFalse(feeds._valid_endpoint(bad))
        self.assertTrue(feeds._valid_endpoint("https://api.example.org/messages"))
        self.assertTrue(feeds._valid_endpoint("wss://api.example.org/socket", "wss"))

    def test_configuration_never_exposes_credentials(self):
        with patch.dict(os.environ, {
            "GREEN_SMS_API_BASE_URL": "https://api.example.org/api/partner/v1",
            "GREEN_SMS_API_KEY": "SECRET_A",
            "IVASMSPER_PANEL_URL": "https://api.example.org/api/v1/messages",
            "IVASMSPER_PANEL_TOKEN": "SECRET_B",
            "IVASMSPER_WS_URL": "wss://api.example.org/socket?auth=SECRET_C",
        }):
            status = feeds.configured_status()
        self.assertTrue(status["green_sms"]["rest_configured"])
        self.assertTrue(status["ivasmsper"]["rest_configured"])
        self.assertTrue(status["ivasmsper"]["websocket_configured"])
        self.assertNotIn("SECRET_", str(status))

    def test_ivas_websocket_event_parsing(self):
        feeds._LIVE_EVENTS.clear()
        self.assertTrue(feeds._process_ivas_ws_text(
            '42/livesms,["new",{"recipient":"+12345","originator":"test",'
            '"message":"synthetic test"}]'))
        self.assertEqual(feeds.live_ivas_snapshot()[0]["number"], "+12345")
        self.assertFalse(feeds._process_ivas_ws_text("42/livesms,wrong"))
        feeds._LIVE_EVENTS.clear()


class ProviderAccessSecurityTests(unittest.TestCase):
    def test_route_and_strong_auth(self):
        source = Path("main.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        funcs = [node for node in tree.body
                 if isinstance(node, ast.AsyncFunctionDef)
                 and node.name == "miniapp_admin_provider_feeds_api"]
        self.assertEqual(len(funcs), 1)
        code = ast.get_source_segment(source, funcs[0])
        self.assertIn("_miniapp_auth(request)", code)
        self.assertIn("if not is_admin(uid) or is_user_banned(uid):", code)
        self.assertIn('"forbidden"', code)
        self.assertIn('"Cache-Control"] = "no-store"', code)
        self.assertIn('"/api/admin-provider-feeds", miniapp_admin_provider_feeds_api', source)

    def test_ui_is_hidden_from_non_admin_and_escapes_messages(self):
        html = Path("docs/index.html").read_text(encoding="utf-8")
        js = Path("docs/admin-provider-feeds.js").read_text(encoding="utf-8")
        self.assertIn('id="tab-admin" class="tab-content" hidden', html)
        self.assertIn("if (!state.isAdmin) return;", js)
        self.assertIn("textContent = String(record.message", js)
        self.assertNotIn(".innerHTML", js)
        self.assertIn('admin-provider-feeds.js', html)
        self.assertIn('window.loadAdminProviderFeeds?.();',
                      Path("docs/app.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
