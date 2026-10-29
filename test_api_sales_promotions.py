"""Offline regression tests for 15-minute API sales Telegram announcements."""
import unittest
from html import unescape

from api_sales_promotions import (
    INTERVAL_SECONDS, active_public_products, build_group_digest,
    promotion_due, safe_promotion_state,
)


def catalog(visible=True, enabled=True, last_sent_at=0):
    return {
        "visible": visible,
        "promotions": {"enabled": enabled, "last_sent_at": last_sent_at},
        "items": [
            {"id": "abc123", "name": "SMS API", "description": "Xidmət detalları",
             "endpoint": "https://hidden.example.test/private/path",
             "secret": "DO_NOT_EXPOSE_THE_SECRET",
             "enabled": True, "price_cents": 250},
            {"id": "def456", "name": "Invisible API",
             "description": "Private content must not be promoted",
             "endpoint": "https://hidden.example.test",
             "secret": "DO_NOT_EXPOSE_HIDDEN",
             "enabled": False, "price_cents": 500},
        ],
    }


class APIGroupPromoTests(unittest.TestCase):
    def test_promotion_every_fifteen_minutes(self):
        data = catalog(last_sent_at=1000)
        self.assertEqual(INTERVAL_SECONDS, 900)
        self.assertFalse(promotion_due(data, 1899))
        self.assertTrue(promotion_due(data, 1900))
        self.assertTrue(promotion_due(data, 1901))

    def test_off_and_invisible_catalog_are_never_promoted(self):
        self.assertFalse(promotion_due(catalog(enabled=False), 999999))
        self.assertFalse(promotion_due(catalog(visible=False), 999999))
        data = catalog()
        data["items"][0]["enabled"] = False
        self.assertFalse(promotion_due(data, 999999))

    def test_detailed_public_digest_is_safe(self):
        result = build_group_digest(catalog(), "https://ivasmss.onrender.com/")
        for text in ("SMS API", "2.50 AZN", "Xidmət detalları",
                     "Mini App", "Aldığım API-lər", "balans"):
            self.assertIn(text, result)
        for secret in ("DO_NOT_EXPOSE_THE_SECRET", "DO_NOT_EXPOSE_HIDDEN",
                       "hidden.example.test", "Private content must not be promoted"):
            self.assertNotIn(secret, result)
        self.assertLess(len(result), 4096)

    def test_escaped_admin_text_and_accidental_tokens(self):
        data = catalog()
        data["items"][0]["name"] = "<b>UNSAFE</b>"
        data["items"][0]["description"] = (
            "Sınaq API key: leaked123 https://secret.example/link "
            "token=xyz123 <script>alert(1)</script>"
        )
        value = build_group_digest(data)
        self.assertIn("&lt;b&gt;UNSAFE&lt;/b&gt;", value)
        self.assertNotIn("<script>", value)
        self.assertNotIn("leaked123", unescape(value))
        self.assertNotIn("xyz123", unescape(value))
        self.assertNotIn("secret.example", unescape(value))

    def test_no_secret_sku_without_price_and_empty_catalog(self):
        d = catalog()
        d["items"][0]["price_cents"] = 0
        self.assertEqual(active_public_products(d), [])
        self.assertEqual(build_group_digest(d), "")

    def test_missing_state_defaults_to_enabled_and_preserves_timestamp(self):
        d = catalog()
        d.pop("promotions")
        self.assertTrue(safe_promotion_state(d)["enabled"])
        self.assertEqual(safe_promotion_state(d)["last_sent_at"], 0)
        d["promotions"] = {"enabled": True, "last_sent_at": 12345}
        self.assertEqual(safe_promotion_state(d)["last_sent_at"], 12345)
        self.assertFalse(promotion_due(d, 12345 + 899))
        self.assertTrue(promotion_due(d, 12345 + 900))


if __name__ == "__main__":
    unittest.main()
