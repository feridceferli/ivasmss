"""Offline checks for hourly bot reminders, admin settings and recipient safety."""
import json
import tempfile
import unittest
from pathlib import Path

from bot_user_promos import (
    DEFAULT_TEMPLATES, PromoConfigError, eligible_users, load_settings,
    mark_scheduled, normalize_settings, planned_message, ready_to_dispatch,
    save_settings, update_settings,
)


class HourlyUserPromoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "bot_user_promos.json"

    def test_hourly_default_with_rotating_short_messages(self):
        settings = load_settings(self.path)
        self.assertEqual(settings["interval_minutes"], 60)
        self.assertTrue(settings["enabled"])
        self.assertGreaterEqual(len(DEFAULT_TEMPLATES), 3)
        first = planned_message(settings)
        self.assertLess(len(first), 260)
        self.assertIn("/promo_off", first)
        marked = mark_scheduled(settings, 1000)
        self.assertEqual(marked["next_due_at"], 4600)
        self.assertNotEqual(first, planned_message(marked))
        self.assertFalse(ready_to_dispatch(marked, 4599))
        self.assertTrue(ready_to_dispatch(marked, 4600))

    def test_persists_across_restart_and_no_immediate_rebroadcast(self):
        initial = load_settings(self.path)
        save_settings(self.path, mark_scheduled(initial, 1200))
        restored = load_settings(self.path)
        self.assertEqual(restored["next_due_at"], 4800)
        self.assertFalse(ready_to_dispatch(restored, 4799))
        disabled = update_settings(self.path, enabled=False, now=2000)
        self.assertFalse(ready_to_dispatch(disabled, 999999))
        enabled = update_settings(self.path, enabled=True, now=3000)
        self.assertFalse(ready_to_dispatch(enabled, 3000))
        self.assertEqual(load_settings(self.path)["next_due_at"], 6600)

    def test_admin_can_change_interval_and_messages(self):
        settings = update_settings(self.path, interval_minutes=90,
                                   templates=["📱 İndi nömrə kataloqunu yoxla! /start"],
                                   now=100)
        self.assertEqual(settings["interval_minutes"], 90)
        self.assertEqual(settings["next_due_at"], 5500)
        self.assertEqual(len(settings["templates"]), 1)
        self.assertIn("kataloqu", planned_message(settings))

    def test_opt_out_and_invalid_bot_users_filtered(self):
        users = {
            "42": {"promo_opt_out": False},
            "55": {"promo_opt_out": True},
            "77": {},
            "-100": {},
            "bot": {},
            "99": {"promo_opt_out": False},
        }
        self.assertEqual(eligible_users(users, banned_ids=["99"]), [42, 77])

    def test_validation_rejects_sensitive_codes_long_text_and_bad_interval(self):
        with self.assertRaises(PromoConfigError):
            update_settings(self.path, interval_minutes=10)
        for text in ("otp: 123456", "password: secret-password", "A"*230, "Hi"):
            with self.subTest(text=text):
                with self.assertRaises((ValueError, PromoConfigError)):
                    update_settings(self.path, templates=[text])
        self.assertEqual(load_settings(self.path)["interval_minutes"], 60)

    def test_corrupt_settings_do_not_overwrite_existing_file(self):
        self.path.write_text("{corrupted", encoding="utf-8")
        with self.assertRaises(PromoConfigError):
            update_settings(self.path, enabled=False)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{corrupted")


if __name__ == "__main__":
    unittest.main()
