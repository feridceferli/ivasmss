"""Regression tests for the WhatsApp-only Telegram referral gate."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import whatsapp_referrals as wa


class WhatsAppReferralTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = str(Path(self.temp.name) / "referral.json")
        self.patch = patch.object(wa, "SETTINGS_FILE", self.file)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_disabled_by_default_and_admin_toggle_validates_boolean(self):
        self.assertFalse(wa.load_settings()["enabled"])
        self.assertTrue(wa.save_settings(True)["enabled"])
        self.assertTrue(wa.load_settings()["enabled"])
        self.assertFalse(wa.save_settings(False)["enabled"])
        for invalid in ("true", 1, None):
            with self.assertRaises(ValueError):
                wa.save_settings(invalid)

    def test_only_whatsapp_service_is_restricted(self):
        users = {"1": {"user_id": "1"}}
        cfg = {"enabled": True}
        for service in ("wa", "WHATSAPP", "whatsapp_business", "whatsapp-business"):
            self.assertTrue(wa.requires_invites(users, "1", service, cfg))
        for service in ("tg", "telegram", "bolt", "az", "custom", "", None):
            self.assertFalse(wa.requires_invites(users, "1", service, cfg))
        self.assertFalse(wa.requires_invites(users, "1", "wa", cfg, is_admin=True))
        self.assertFalse(wa.requires_invites(users, "1", "wa", {"enabled": False}))

    def test_new_user_is_unique_cannot_self_ref_and_cannot_reassign(self):
        users = {"100": {"user_id": "100"}, "200": {"user_id": "200"}}
        self.assertFalse(wa.record_first_referral(users, "100", "100"))
        self.assertFalse(wa.record_first_referral(users, "100", "200"))
        self.assertFalse(wa.record_first_referral(users, "301", "301"))
        self.assertFalse(wa.record_first_referral(users, "301", "999"))
        self.assertTrue(wa.record_first_referral(users, "301", "100"))
        self.assertFalse(wa.record_first_referral(users, "301", "200"))
        self.assertEqual(users["301"]["referred_by_pending"], "100")
        self.assertEqual(wa.progress(users, "100", enabled=True)["count"], 0)
        self.assertTrue(wa.confirm_referral(users, "301"))
        self.assertFalse(wa.confirm_referral(users, "301"))
        self.assertEqual(wa.progress(users, "100", enabled=True)["count"], 1)
        self.assertEqual(wa.progress(users, "200", enabled=True)["count"], 0)

    def test_five_unique_valid_invites_unlock_only_whatsapp(self):
        users = {"100": {"user_id": "100"}}
        for i in range(201, 206):
            self.assertTrue(wa.record_first_referral(users, str(i), "100"))
            self.assertTrue(wa.confirm_referral(users, str(i)))
        result = wa.progress(users, "100", enabled=True, bot_username="ExampleSMS_bot")
        self.assertEqual(result["count"], 5)
        self.assertEqual(result["remaining"], 0)
        self.assertTrue(result["unlocked"])
        self.assertEqual(result["invite_link"], "https://t.me/ExampleSMS_bot?start=ref_100")
        self.assertFalse(wa.requires_invites(users, "100", "wa", {"enabled": True}))

    def test_link_payload_validation(self):
        self.assertEqual(wa.referral_param("ref_50505"), "50505")
        self.assertIsNone(wa.referral_param("ref_0"))
        self.assertIsNone(wa.referral_param("ref_-1"))
        self.assertIsNone(wa.referral_param("ref_50505extra"))
        self.assertIsNone(wa.referral_param("connect_fakeref_100"))


if __name__ == "__main__":
    unittest.main()
