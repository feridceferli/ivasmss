"""Offline integration test for five real options and single-charge activation."""
import ast
import asyncio
import re
import time
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx

from number_choices import NumberChoiceStore
from number_pricing import PricingError


ROOT = Path(__file__).resolve().parent
MODULE = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))


def build_methods(fake):
    functions = [node for node in MODULE.body
                 if isinstance(node, ast.AsyncFunctionDef)
                 and node.name in ("prepare_number_choices", "confirm_number_choice")]
    assert len(functions) == 2
    exec(compile(ast.fix_missing_locations(
        ast.Module(body=functions, type_ignores=[])), "main.py", "exec"), fake)
    return fake


class NumberChoiceIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.users = {"7": {"balance": 10.0}}
        self.record = Mock()
        self.stats = []
        self.active = {}
        self.saved_ranges = []
        replies = iter([
            SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda number=number: {
                    "meta": {"code": 200},
                    "data": {"full_number": number, "country": "UK"},
                }
            ) for number in ("44770000001", "44770000002", "44770000003",
                             "44770000004", "44770000005")
        ])
        provider = SimpleNamespace(post=AsyncMock(side_effect=lambda *a, **k: next(replies)))
        fake = {
            "asyncio": asyncio,
            "re": re,
            "time": time,
            "httpx": httpx,
            "PricingError": PricingError,
            "number_choices": NumberChoiceStore(),
            "_number_purchase_locks": {},
            "USER_DATA_FILE": "users.json",
            "NUMBER_WAIT_SECONDS": 180,
            "number_archive": SimpleNamespace(record=self.record),
            "client_async": provider,
            "BASE_URL": "https://example.invalid/api",
            "is_az_range": lambda rid: False,
            "az_range_allowed": lambda uid: True,
            "is_user_banned": lambda uid: False,
            "is_admin": lambda uid: False,
            "load_number_prices": lambda: {},
            "quote_range": lambda rid, *args: {"cents": 100, "price": 1.0},
            "get_user": lambda uid: self.users[str(uid)],
            "load_data": lambda path: self.users,
            "save_data": lambda data, path: None,
            "normalize_number": lambda n: re.sub(r"\D", "", str(n)),
            "active_numbers": self.active,
            "active_number_remaining": lambda info: 180,
            "add_number_taken": lambda uid, n: self.stats.append((uid, n)),
            "last_range": {},
            "assign_active_number": lambda uid, number, rid: self.active.setdefault(
                number, {"uid": uid, "range": rid, "lease_id": "abc"})["lease_id"],
            "save_number_range_info": lambda *args: self.saved_ranges.append(args),
            "mask_number": lambda x: "****" + x[-4:],
            "miniapp_orders": {},
        }
        self.env = build_methods(fake)

    async def test_offer_is_free_then_selection_charges_exactly_once(self):
        offer = await self.env["prepare_number_choices"](
            7, "447700", "wa", "GB", expected_price_cents=100)
        self.assertEqual(len(offer["numbers"]), 5)
        self.assertEqual(self.env["client_async"].post.await_count, 5)
        self.assertEqual(self.users["7"]["balance"], 10.0)
        self.record.assert_not_called()
        self.assertEqual(self.stats, [])
        self.assertEqual(self.active, {})

        chosen = await self.env["confirm_number_choice"](
            7, offer["token"], 3, expected_price_cents=100)
        self.assertTrue(chosen["success"])
        self.assertEqual(chosen["number"], "+44770000004")
        self.assertEqual(self.users["7"]["balance"], 9.0)
        self.record.assert_called_once_with("+44770000004")
        self.assertEqual(self.stats, [(7, 1)])
        self.assertEqual(len(self.active), 1)
        self.assertEqual(len(self.env["miniapp_orders"][7]), 1)

        with self.assertRaises(PricingError):
            await self.env["confirm_number_choice"](
                7, offer["token"], 0, expected_price_cents=100)
        self.assertEqual(self.users["7"]["balance"], 9.0)

    async def test_foreign_user_cannot_take_options(self):
        offer = await self.env["prepare_number_choices"](7, "447700", "wa", "GB", 100)
        with self.assertRaises(PricingError):
            await self.env["confirm_number_choice"](8, offer["token"], 1, 100)
        self.assertEqual(self.users["7"]["balance"], 10.0)
        self.record.assert_not_called()

    async def test_price_change_rejected_without_charge_or_record(self):
        offer = await self.env["prepare_number_choices"](7, "447700", "wa", "GB", 100)
        with self.assertRaises(PricingError) as err:
            await self.env["confirm_number_choice"](7, offer["token"], 1, 999)
        self.assertEqual(err.exception.code, "price_changed")
        self.record.assert_not_called()
        self.assertEqual(self.users["7"]["balance"], 10.0)


if __name__ == "__main__":
    unittest.main()
