"""Regression tests for admin-published services, refunds and manual receipts."""
import json
import tempfile
import unittest
from pathlib import Path
from marketplace import MarketCatalog, RentalLedger
from manual_topups import ManualTopups, TopupError, parse_amount_cents


class MarketplaceTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.dir = Path(self.root.name)
        self.users = {"123": {"user_id": "123", "balance": 10.0}}
        self.catalog = MarketCatalog(self.dir / "market.json")
        self.rentals = RentalLedger(self.dir / "rentals.json")
        self.topups = ManualTopups(self.dir / "topups.json")

    def load(self):
        return json.loads(json.dumps(self.users))

    def save(self, data):
        self.users = data

    def test_admin_published_service_range(self):
        upstream = {"whatsapp": ["447700XX", "234"], "telegram": ["447700XX"]}
        self.assertEqual(self.catalog.public(upstream), {})
        self.assertTrue(self.catalog.toggle("whatsapp", "447700", upstream))
        self.assertTrue(self.catalog.allowed("whatsapp", "447700"))
        self.assertEqual(self.catalog.public(upstream), {"whatsapp": ["447700XX"]})
        self.assertFalse(self.catalog.allowed("telegram", "447700"))
        self.assertFalse(self.catalog.toggle("whatsapp", "447700", upstream))
        self.assertEqual(self.catalog.public(upstream), {})
        with self.assertRaises(ValueError):
            self.catalog.toggle("telegram", "99999", upstream)

    def test_refund_at_three_minutes_and_no_twice(self):
        self.rentals.record("a"*16, 123, "447700000001", 150, now=1000)
        self.users["123"]["balance"] = 8.50
        self.assertEqual(self.rentals.active_count(123, now=1100), 1)
        self.assertEqual(self.rentals.settle_due(self.load, self.save, now=1179), [])
        self.assertEqual(self.users["123"]["balance"], 8.50)
        self.assertEqual(self.rentals.settle_due(self.load, self.save, now=1180), ["a"*16])
        self.assertEqual(self.users["123"]["balance"], 10.0)
        self.assertEqual(self.rentals.settle_due(self.load, self.save, now=1300), [])
        self.assertEqual(self.users["123"]["balance"], 10.0)
        # Simulate crash after the balance+refund marker was written,
        # before the separate rental journal status could be updated.
        journal = json.loads((self.dir/"rentals.json").read_text())
        journal["a"*16]["status"] = "pending"
        (self.dir/"rentals.json").write_text(json.dumps(journal))
        self.assertEqual(self.rentals.settle_due(self.load, self.save, now=1300), ["a"*16])
        self.assertEqual(self.users["123"]["balance"], 10.0)

    def test_successful_sms_prevents_refund(self):
        self.rentals.record("b"*16, 123, "447700000002", 250, now=2000)
        self.users["123"]["balance"] = 7.50
        self.assertTrue(self.rentals.received("b"*16, now=2050))
        self.assertFalse(self.rentals.received("b"*16, now=2060))
        self.assertEqual(self.rentals.settle_due(self.load, self.save, now=2300), [])
        self.assertEqual(self.users["123"]["balance"], 7.50)
        self.assertEqual(self.rentals.active_count(123, now=2050), 0)

    def test_manual_receipt_is_admin_approved_only_once(self):
        self.topups.set_card("4169 0000 0000 0000")
        self.topups.set_contact("@adminaccount")
        self.assertEqual(self.topups.details()["contact"], "https://t.me/adminaccount")
        ident = self.topups.submit(123, parse_amount_cents("2.50"), "TGFILE12345", "photo")
        self.assertEqual(self.users["123"]["balance"], 10.0)
        self.assertEqual(len(self.topups.pending()), 1)
        result = self.topups.review(ident, True, self.load, self.save)
        self.assertEqual(result["status"], "approved")
        self.assertEqual(self.users["123"]["balance"], 12.50)
        with self.assertRaises(TopupError):
            self.topups.review(ident, True, self.load, self.save)
        self.assertEqual(self.users["123"]["balance"], 12.50)
        second = self.topups.submit(123, 300, "TGFILE67890", "document")
        self.topups.review(second, False, self.load, self.save)
        self.assertEqual(self.users["123"]["balance"], 12.50)

    def test_manual_input_validation(self):
        for wrong in ("", "0", "-1", "1.234", "Infinity", "10000.01"):
            with self.assertRaises(TopupError):
                parse_amount_cents(wrong)
        with self.assertRaises(TopupError):
            self.topups.set_card("4111 1111 abc")
        with self.assertRaises(TopupError):
            self.topups.submit(123, 100, "short", "invalid")


if __name__ == "__main__":
    unittest.main()
