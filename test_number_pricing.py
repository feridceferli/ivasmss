"""Offline pricing, admin-rule and allocation-balance regression tests.

All phone numbers and provider responses are synthetic; no real network calls.
"""
import ast
import asyncio
import copy
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from number_pricing import (
    PricingError, initial_prices, price_rule, quote_range,
    valid_country, valid_range,
)


class PriceRuleTests(unittest.TestCase):
    def setUp(self):
        self.p = initial_prices()

    def test_initial_rates_and_paid_azerbaijan(self):
        self.assertEqual(quote_range("99450210", self.p)["cents"], 1000)
        self.assertTrue(quote_range("447700", self.p)["free"])
        self.assertEqual(quote_range("447700", self.p)["price"], "0.00")

    def test_country_price_and_free_toggle(self):
        self.p["country"]["AZ"] = price_rule("2.50", False)
        self.assertEqual(quote_range("99450210", self.p, "AZ")["cents"], 250)
        self.p["country"]["AZ"] = price_rule("999", True)
        self.assertTrue(quote_range("99450210", self.p)["free"])

    def test_range_overrides_country(self):
        self.p["country"]["AZ"] = price_rule("10.50", False)
        self.p["range"]["99450210"] = price_rule("1.20", False)
        self.assertEqual(quote_range("99450210", self.p)["cents"], 120)
        self.assertEqual(quote_range("99450211", self.p)["cents"], 1050)

    def test_shared_prefix_different_country_prices_require_range_override(self):
        self.p["country"]["CA"] = price_rule("3.00", False)
        with self.assertRaises(PricingError) as ctx:
            quote_range("1202555", self.p, "US")
        self.assertEqual(ctx.exception.code, "ambiguous_country_price")
        self.p["range"]["1202555"] = price_rule("2.00", False)
        self.assertEqual(quote_range("1202555", self.p, "CA")["cents"], 200)

    def test_country_spoof_invalid_and_input_validation(self):
        with self.assertRaises(PricingError):
            quote_range("447700", self.p, "AZ")
        with self.assertRaises(PricingError):
            price_rule("1.001", False)
        with self.assertRaises(PricingError):
            price_rule("NaN", False)
        with self.assertRaises(PricingError):
            price_rule("-1", False)
        with self.assertRaises(PricingError):
            price_rule("10000.01", False)
        with self.assertRaises(PricingError):
            price_rule(True, False)
        with self.assertRaises(PricingError):
            price_rule("3", "false")
        self.assertTrue(valid_country("AZ"))
        self.assertFalse(valid_country("ZZ"))
        self.assertTrue(valid_range("99450210"))
        self.assertFalse(valid_range("99450X"))


MODULE = ast.parse(Path(__file__).with_name("main.py").read_text(encoding="utf-8"))


def extract_allocator(ns):
    target = next(node for node in MODULE.body
                  if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_number_from_api")
    code = compile(ast.fix_missing_locations(
        ast.Module(body=[target], type_ignores=[])), "main.py", "exec")
    exec(code, ns)
    return ns["get_number_from_api"]


class PurchaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.users = {"77": {"user_id": "77", "balance": 20.0}}
        self.settings = initial_prices()
        self.post = AsyncMock(return_value=SimpleNamespace(json=lambda: {
            "meta": {"code": 200},
            "data": {"full_number": "+994502101234", "country": "Azerbaijan"},
        }))
        self.archive = []
        def load(file):
            return copy.deepcopy(self.users)
        def save(data, file):
            self.users = copy.deepcopy(data)
        ns = {
            "re": re, "asyncio": asyncio,
            "PricingError": PricingError, "quote_range": quote_range,
            "load_number_prices": lambda: self.settings,
            "is_az_range": lambda rid: rid.startswith("994"),
            "az_range_allowed": lambda uid: int(uid or 0) == 77,
            "_number_purchase_locks": {},
            "get_user": lambda uid: self.users[str(uid)],
            "load_data": load, "save_data": save,
            "USER_DATA_FILE": "users.json",
            "client_async": SimpleNamespace(post=self.post),
            "BASE_URL": "https://example.invalid",
            "number_archive": SimpleNamespace(record=lambda number: self.archive.append(number)),
        }
        self.allocate = extract_allocator(ns)

    async def test_success_charges_exactly_once(self):
        number, _ = await self.allocate("99450210", requester_id=77)
        self.assertEqual(number, "+994502101234")
        self.assertEqual(self.users["77"]["balance"], 10.0)
        self.assertEqual(len(self.archive), 1)
        self.post.assert_awaited_once()

    async def test_failed_provider_refunds_price(self):
        self.post.return_value = SimpleNamespace(json=lambda: {"meta": {"code": 404}})
        self.assertEqual((None, None), await self.allocate("99450210", requester_id=77))
        self.assertEqual(self.users["77"]["balance"], 20.0)
        self.assertEqual(self.archive, [])

    async def test_insufficient_balance_never_calls_provider(self):
        self.users["77"]["balance"] = 9.99
        with self.assertRaises(PricingError) as ctx:
            await self.allocate("99450210", requester_id=77)
        self.assertEqual(ctx.exception.code, "insufficient_balance")
        self.post.assert_not_awaited()

    async def test_changed_price_is_rejected_under_lock_without_debit(self):
        # Quote the original 10 AZN, then raise the admin price to 12 AZN.
        self.settings["country"]["AZ"] = price_rule("12", False)
        with self.assertRaises(PricingError) as ctx:
            await self.allocate(
                "99450210", requester_id=77, expected_price_cents=1000,
            )
        self.assertEqual(ctx.exception.code, "price_changed")
        self.assertEqual(self.users["77"]["balance"], 20.0)
        self.post.assert_not_awaited()

    async def test_expected_price_matches_paid_purchase(self):
        await self.allocate(
            "99450210", requester_id=77, expected_price_cents=1000,
        )
        self.assertEqual(self.users["77"]["balance"], 10.0)

    async def test_concurrent_orders_do_not_double_spend(self):
        self.users["77"]["balance"] = 10.0
        responses = await asyncio.gather(
            self.allocate("99450210", requester_id=77),
            self.allocate("99450210", requester_id=77),
            return_exceptions=True)
        self.assertEqual(sum(isinstance(v, PricingError) for v in responses), 1)
        self.assertEqual(self.users["77"]["balance"], 0.0)
        self.assertEqual(self.post.await_count, 1)

    async def test_free_country_does_not_debit(self):
        self.post.return_value = SimpleNamespace(json=lambda: {
            "meta": {"code": 200},
            "data": {"full_number": "+447700123456", "country": "UK"},
        })
        number, _ = await self.allocate("447700", requester_id=77, country_iso="GB")
        self.assertEqual(number, "+447700123456")
        self.assertEqual(self.users["77"]["balance"], 20.0)


if __name__ == "__main__":
    unittest.main()
