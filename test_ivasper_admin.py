import ast
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

from ivasper_admin import admin_allowed, render_inventory, CALLBACK_PATTERN


class IvasperAdminTests(unittest.TestCase):
    def test_private_admin_only(self):
        allow = lambda uid: uid == 5
        no_bans = lambda _: False
        self.assertTrue(admin_allowed(SimpleNamespace(id=5),
                                      SimpleNamespace(type="private"), allow, no_bans))
        self.assertFalse(admin_allowed(SimpleNamespace(id=6),
                                       SimpleNamespace(type="private"), allow, no_bans))
        self.assertFalse(admin_allowed(SimpleNamespace(id=5),
                                       SimpleNamespace(type="group"), allow, no_bans))
        self.assertFalse(admin_allowed(SimpleNamespace(id=5),
                                       SimpleNamespace(type="private"), allow,
                                       lambda _: True))

    def test_bot_shows_independent_stock_only(self):
        stock = {"status": "ok", "numbers": [
            {"number": "+994501234567", "country": "Azerbaijan",
             "service": "Telegram"},
            {"number": "+4915112345678", "country": "Germany",
             "service": "WhatsApp"},
        ]}
        title, keyboard = render_inventory("summary", stock)
        self.assertIn("2", title)
        self.assertIn("IVASMS nömrə bazası", title)
        countries, nav = render_inventory("archive", stock)
        self.assertIn("ÖLKƏLƏR", countries)
        self.assertTrue(nav.inline_keyboard)
        report, nav = render_inventory("country:0:0", stock)
        self.assertIn("+994501234567", report)
        self.assertNotIn("+4915112345678", report)
        self.assertTrue(re.match(CALLBACK_PATTERN, "ivasper_admin:country:0:0"))

    def test_no_fallback_when_no_authorized_source(self):
        message, keyboard = render_inventory(
            "summary", {"status": "not_configured", "numbers": [],
                        "message": "IVASPER mənbəyi qoşulmayıb."})
        self.assertIn("qoşulmayıb", message)
        self.assertNotIn("+99450", message)
        self.assertTrue(keyboard.inline_keyboard)

    def test_registration_wiring(self):
        root = Path(__file__).resolve().parent
        main = (root / "main.py").read_text(encoding="utf-8")
        ast.parse(main)
        ast.parse((root / "ivasper_admin.py").read_text(encoding="utf-8"))
        self.assertIn("register_ivasper_admin_handlers(", main)
        self.assertIn("load_ivasper_inventory,", main)
        self.assertIn("🧰 IVASPER NƏZARƏT", main)
        self.assertLess(main.index("    register_ivasper_admin_handlers("),
                        main.index("    app.add_handler(CallbackQueryHandler(button_callback))"))


if __name__ == "__main__":
    unittest.main()
