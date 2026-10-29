"""Offline regression tests for API-sale privacy, pricing and account checkout."""
import json
import tempfile
import threading
import unittest
from pathlib import Path

from api_sales import ApiSalesError, ApiSalesStore, price_to_cents


class ApiSalesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.users = self.root / "users.json"
        self.catalog = self.root / "api_sales_private.json"
        self.users.write_text(json.dumps({"42": {"user_id": "42", "balance": 2.50}}), encoding="utf-8")
        def read(path):
            return json.loads(Path(path).read_text(encoding="utf-8"))
        def save(value, path):
            Path(path).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        self.store = ApiSalesStore(self.catalog, self.users, read, save)

    def item(self, price="1.00"):
        return self.store.upsert({
            "name": "Test API", "description": "Request a test token",
            "endpoint": "https://api.example.test/v1", "secret": "test-only-secret",
            "price": price,
        })

    def test_catalog_hidden_and_public_secret_never_exposed(self):
        item = self.item()
        customer = self.store.list_products("42")
        self.assertFalse(customer["visible"])
        self.assertEqual(customer["products"], [])
        self.assertNotIn("test-only-secret", json.dumps(customer))
        admin = self.store.list_products("42", admin=True)
        self.assertTrue(admin["products"][0]["has_secret"])
        self.assertIn("endpoint", admin["products"][0])
        self.store.toggle_section(True)
        public = self.store.list_products("42")
        self.assertEqual(len(public["products"]), 1)
        self.assertNotIn("endpoint", public["products"][0])
        self.assertNotIn("secret", public["products"][0])

    def test_one_time_purchase_and_owned_secret(self):
        item = self.item("1.20")
        self.store.toggle_section(True)
        bought, charged = self.store.buy("42", item["id"])
        self.assertTrue(charged)
        self.assertEqual(bought["secret"], "test-only-secret")
        self.assertEqual(self.store.read_users(self.users)["42"]["balance"], 1.30)
        again, charged = self.store.buy("42", item["id"])
        self.assertFalse(charged)
        self.assertEqual(again, bought)
        self.assertEqual(self.store.read_users(self.users)["42"]["balance"], 1.30)
        mine = self.store.list_products("42")
        self.assertEqual(mine["owned"][0]["secret"], "test-only-secret")

    def test_insufficient_balance_no_debit(self):
        item = self.item("3.00")
        self.store.toggle_section(True)
        with self.assertRaisesRegex(ApiSalesError, "insufficient_balance"):
            self.store.buy("42", item["id"])
        self.assertEqual(self.store.read_users(self.users)["42"]["balance"], 2.50)
        self.assertNotIn("api_purchases", self.store.read_users(self.users)["42"])

    def test_disabled_item_and_hidden_section_reject_new_purchases(self):
        item = self.item()
        with self.assertRaisesRegex(ApiSalesError, "unavailable"):
            self.store.buy("42", item["id"])
        self.store.toggle_section(True)
        self.store.toggle_product(item["id"], False)
        with self.assertRaisesRegex(ApiSalesError, "unavailable"):
            self.store.buy("42", item["id"])

    def test_purchased_access_survives_catalog_delete(self):
        item = self.item()
        self.store.toggle_section(True)
        receipt, _ = self.store.buy("42", item["id"])
        self.store.delete(item["id"])
        self.store.toggle_section(False)
        owned = self.store.list_products("42")["owned"]
        self.assertEqual(owned[0], receipt)

    def test_edit_product_does_not_double_charge(self):
        item = self.item()
        changed = self.store.upsert({
            "id": item["id"], "name": "Updated API", "description": "Updated docs",
            "endpoint": "https://api.example.test/v2", "secret": "", "price": "2.10"
        })
        self.assertEqual(item["id"], changed["id"])
        self.store.toggle_section(True)
        self.assertEqual(self.store.list_products("42")["products"][0]["price_cents"], 210)
        receipt, charged = self.store.buy("42", item["id"])
        self.assertTrue(charged)
        self.assertEqual(receipt["secret"], "test-only-secret")

    def test_invalid_prices(self):
        for value in ["0", "-1", "1.001", "NaN", "Infinity", "10000.01", None]:
            with self.subTest(value=value):
                with self.assertRaises(ApiSalesError):
                    price_to_cents(value)

    def test_concurrent_repeat_purchase_one_debit(self):
        item = self.item()
        self.store.toggle_section(True)
        results = []
        def worker():
            results.append(self.store.buy("42", item["id"])[1])
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 9)
        self.assertEqual(self.store.read_users(self.users)["42"]["balance"], 1.50)

    def test_invalid_endpoint_rejected(self):
        with self.assertRaises(ApiSalesError):
            self.store.upsert({
                "name": "Danger", "description": "", "endpoint": "http://no-tls.test",
                "secret": "abc", "price": "1.00",
            })


if __name__ == "__main__":
    unittest.main()
