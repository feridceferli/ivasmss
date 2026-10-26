"""Website account-pairing regressions (standard-library-only)."""
import json
import time
import unittest

from web_login import WebsiteLogin


class WebsiteLoginTests(unittest.TestCase):
    def setUp(self):
        self.auth = WebsiteLogin("000000:integration-test-secret")
        self.user = {
            "id": 12345, "first_name": "Test", "last_name": "User",
            "username": "tester",
        }

    def test_link_requires_telegram_confirmation_and_original_browser(self):
        token, flow = self.auth.begin()
        self.assertTrue(self.auth.can_confirm(token))
        self.assertEqual(self.auth.consume(token, flow), ("pending", None))
        self.assertEqual(self.auth.consume(token, "not-original-cookie")[0], "forbidden")
        self.assertTrue(self.auth.confirm(token, self.user))
        self.assertFalse(self.auth.can_confirm(token))
        status, user = self.auth.consume(token, flow)
        self.assertEqual(status, "connected")
        self.assertEqual(user["id"], self.user["id"])
        self.assertEqual(self.auth.consume(token, flow), ("expired", None))

    def test_expired_link_cannot_confirm(self):
        token, flow = self.auth.begin()
        self.auth.pending[token]["created"] -= self.auth.PAIR_TTL + 1
        self.assertFalse(self.auth.can_confirm(token))
        self.assertFalse(self.auth.confirm(token, self.user))
        self.assertEqual(self.auth.consume(token, flow)[0], "expired")

    def test_session_signed_tamper_protected_and_time_limited(self):
        current = int(time.time())
        session = self.auth.make_session(self.user, now=current)
        self.assertEqual(self.auth.verify_session(session, now=current + 1)["id"], 12345)
        payload, signature = session.split(".")
        forged = payload + "." + signature[::-1]
        self.assertIsNone(self.auth.verify_session(forged, now=current))
        self.assertIsNone(self.auth.verify_session(session, now=current + self.auth.SESSION_TTL + 1))
        self.assertIsNone(self.auth.verify_session("completely.bad"))
        self.assertIsNone(self.auth.verify_session(None))

    def test_other_bot_secret_cannot_open_session(self):
        token = self.auth.make_session(self.user)
        self.assertIsNone(WebsiteLogin("other-secret").verify_session(token))

    def test_pending_limit(self):
        self.auth.MAX_PENDING = 1
        self.auth.begin()
        with self.assertRaises(RuntimeError):
            self.auth.begin()


if __name__ == "__main__":
    unittest.main()
