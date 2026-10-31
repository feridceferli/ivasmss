import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from ivasper_admin import admin_allowed, archive_summary, build_report, service_summary, archive_detail_text, CALLBACK_PATTERN

class IvasperTests(unittest.TestCase):
    def test_permissions(self):
        admin = SimpleNamespace(id=5)
        outsider = SimpleNamespace(id=6)
        priv = SimpleNamespace(type='private')
        group = SimpleNamespace(type='group')
        allow = lambda uid: uid == 5
        no_bans = lambda uid: False
        self.assertTrue(admin_allowed(admin, priv, allow, no_bans))
        self.assertFalse(admin_allowed(outsider, priv, allow, no_bans))
        self.assertFalse(admin_allowed(admin, group, allow, no_bans))
        self.assertFalse(admin_allowed(None, priv, allow, no_bans))

    def test_reports_aggregate_only(self):
        archive = {'994501234567': {'country': 'Azerbaijan', 'number': '+994501234567', 'user_id': '987654'}}
        report = build_report('archive', {}, archive, {})
        self.assertIn('Azerbaijan', report)
        self.assertNotIn('994501234567', report)
        self.assertNotIn('987654', report)
        self.assertEqual(archive_summary(archive)[0], 1)
        self.assertEqual(service_summary({'wa': [{}, {}]})[1], 2)

    def test_archive_country_callback_reveals_own_numbers_only(self):
        import re
        records = {
            "994502110012": {"country": "🇦🇿 Azərbaycan", "number": "+994502110012",
                              "user_id": "5", "range": "99450211"},
            "994502118888": {"country": "🇦🇿 Azərbaycan", "number": "+994502118888",
                              "user_id": "8", "range": "99450211"},
        }
        report, keyboard = archive_detail_text(records, 5, 0, 0)
        self.assertIn("994502110012", report)
        self.assertNotIn("994502118888", report)
        self.assertIn("Öz nömrələrim", report)
        self.assertTrue(re.match(CALLBACK_PATTERN, "ivasper_admin:country:0:0"))
        self.assertTrue(re.match(CALLBACK_PATTERN, "ivasper_admin:archive_page:1"))
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, "ivasper_admin:archive_page:0")

    def test_wiring_and_syntax(self):
        root = Path(__file__).resolve().parent
        main = (root / 'main.py').read_text(encoding='utf-8')
        ast.parse(main)
        ast.parse((root / 'ivasper_admin.py').read_text(encoding='utf-8'))
        self.assertIn('register_ivasper_admin_handlers(', main)
        self.assertIn('🧰 IVASPER NƏZARƏT', main)
        self.assertLess(main.index('    register_ivasper_admin_handlers('), main.index('    app.add_handler(CallbackQueryHandler(button_callback))'))

if __name__ == '__main__':
    unittest.main()
