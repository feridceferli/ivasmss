"""Offline regression checks for authenticated Mini App admin tools.

These tests read source only; they never send WhatsApp, Telegram, OTP
or other external messages.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
PY = (ROOT / "main.py").read_text(encoding="utf-8")
JS = (ROOT / "docs/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "docs/index.html").read_text(encoding="utf-8")
TREE = ast.parse(PY)


class MiniAppAdminToolsTests(unittest.TestCase):
    def test_admin_tools_route_is_registered(self):
        self.assertIn('"/api/admin-tools", miniapp_admin_tools_api', PY)
        self.assertIn('api("/api/admin-tools"', JS)

    def test_tools_require_server_side_admin_approval(self):
        match = [n for n in TREE.body if isinstance(n, ast.AsyncFunctionDef)
                 and n.name == "miniapp_admin_tools_api"]
        self.assertEqual(len(match), 1)
        code = ast.get_source_segment(PY, match[0])
        self.assertIn("_miniapp_auth(request)", code)
        self.assertIn("if not is_admin(uid) or is_user_banned(uid):", code)
        self.assertIn('"forbidden"', code)
        for item in ("save_settings", "add_channel", "remove_channel",
                     "whatsapp_test", "group_notice"):
            self.assertIn('action == "' + item + '"', code)
        self.assertIn("get_whatsapp_smoke_test().run(cfg)", code)
        self.assertIn("send_group_notification(notice)", code)
        self.assertIn('if len(notice) < 5 or len(notice) > 600:', code)
        self.assertIn("90:", code)

    def test_admin_controls_are_in_protected_view(self):
        for tag in ("cfg-min-withdraw", "cfg-max-withdraw", "cfg-payment-methods",
                    "admin-channels-list", "admin-channel-link", "admin-channel-label",
                    "admin-channel-chat-id", "admin-group-notice", "admin-test-status"):
            self.assertIn('id="' + tag + '"', HTML)
        self.assertIn('id="tab-admin" class="tab-content" hidden', HTML)

    def test_functions_are_bound_to_ui(self):
        functions = ("loadAdminTools", "saveAdminSettings", "adminAddChannel",
                     "adminRemoveChannel", "adminSendGroupNotice", "adminWhatsAppTest")
        for name in functions:
            self.assertIn("function " + name + "(", JS)
        for attr in ("saveAdminSettings()", "adminAddChannel()",
                     "adminSendGroupNotice()", "adminWhatsAppTest()"):
            self.assertIn(attr, HTML)
        self.assertNotIn(".innerHTML", JS)

    def test_no_provider_secrets_sent_to_miniapp(self):
        code = ast.get_source_segment(
            PY, next(n for n in TREE.body if isinstance(n, ast.AsyncFunctionDef)
                     and n.name == "miniapp_admin_tools_api")
        )
        self.assertNotIn("cfg.token", code)
        self.assertNotIn("API_KEY", code)
        self.assertNotIn("BOT_TOKEN", code)


if __name__ == "__main__":
    unittest.main()
