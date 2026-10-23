import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from admin_test_tools import ADMIN_TEST_LABEL, admin_allowed, status_text, test_tools_keyboard
from whatsapp_safe import get_whatsapp_smoke_test

class AdminSandboxUnitTests(unittest.TestCase):
    def test_admin_private_only(self):
        admin = SimpleNamespace(id=123)
        other = SimpleNamespace(id=999)
        private = SimpleNamespace(type="private")
        group = SimpleNamespace(type="group")
        is_admin = lambda uid: uid == 123
        self.assertTrue(admin_allowed(admin, private, is_admin))
        self.assertFalse(admin_allowed(other, private, is_admin))
        self.assertFalse(admin_allowed(admin, group, is_admin))
        self.assertFalse(admin_allowed(None, private, is_admin))

    def test_only_fixed_test_number_and_no_credentials_in_status(self):
        env = {
            "WA_ACCESS_TOKEN": "top-secret-value",
            "WA_PHONE_NUMBER_ID": "1234567890",
            "WA_TEST_RECIPIENT": "994501112233",
            "WA_GRAPH_VERSION": "v25.0",
            "AZE_SMS_API_KEY": "sms-secret-value",
        }
        with patch.dict(os.environ, env, clear=True):
            text = status_text()
        self.assertIn("994***33", text)
        self.assertNotIn("top-secret-value", text)
        self.assertNotIn("sms-secret-value", text)
        self.assertNotIn("994501112233", text)

    def test_admin_buttons_are_private_callback_names(self):
        buttons = test_tools_keyboard().inline_keyboard
        callbacks = [button.callback_data for row in buttons for button in row]
        self.assertEqual(callbacks, [
            "admin_sandbox_status", "admin_sandbox_wa", "admin_sandbox_back"
        ])
        self.assertEqual(ADMIN_TEST_LABEL, "🧪 TEST ALƏTLƏRİ")

    def test_single_shared_cooldown(self):
        self.assertIs(get_whatsapp_smoke_test(), get_whatsapp_smoke_test())

    def test_main_registers_before_generic_handlers_and_hides_in_admin_keyboard(self):
        from pathlib import Path
        main = Path(__file__).resolve().parents[1].joinpath("main.py").read_text(encoding="utf-8")
        admin_keyboard = main.split("def admin_main_keyboard():", 1)[1].split("def admin_tools_keyboard():", 1)[0]
        public_keyboard = main.split("def main_keyboard(user_id):", 1)[1].split("async def premium_keyboard_error_handler", 1)[0]
        self.assertIn(ADMIN_TEST_LABEL, admin_keyboard)
        self.assertNotIn(ADMIN_TEST_LABEL, public_keyboard)
        self.assertLess(
            main.index("    register_admin_test_tools(app, is_admin, admin_main_keyboard)"),
            main.index('    app.add_handler(CallbackQueryHandler(button_callback))')
        )

if __name__ == "__main__":
    unittest.main()
