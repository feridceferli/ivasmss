"""Regression tests for server-side +994 access control.

Run without importing the bot or making real provider requests.
"""
import ast
import asyncio
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock


SOURCE = Path(__file__).with_name("main.py").read_text(encoding="utf-8")
MODULE = ast.parse(SOURCE)


def extract(name, namespace):
    nodes = [
        item for item in MODULE.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name
    ]
    if len(nodes) != 1:
        raise AssertionError(f"Expected exactly one function {name}")
    code = compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), "main.py", "exec")
    exec(code, namespace)
    return namespace[name]


class AzerbaijanAccessTests(unittest.TestCase):
    def setUp(self):
        self.approved = {}
        self.namespace = {
            "re": re, "ADMINS": [100],
            "load_data": lambda path: self.approved,
            "AZ_ACCESS_FILE": "test.json",
        }
        self.namespace["is_admin"] = extract("is_admin", self.namespace)
        self.namespace["is_az_range"] = extract("is_az_range", self.namespace)
        self.namespace["az_range_allowed"] = extract("az_range_allowed", self.namespace)

    def test_country_code_normalization(self):
        az = self.namespace["is_az_range"]
        self.assertTrue(az("+994 50 211"))
        self.assertTrue(az("99450211XXX"))
        self.assertFalse(az("994"[:2]))
        self.assertFalse(az("234XXX"))
        self.assertFalse(az(""))

    def test_approval_required_and_revocable(self):
        allowed = self.namespace["az_range_allowed"]
        self.assertTrue(allowed(100))  # Built-in admin
        self.assertFalse(allowed(200))
        self.assertFalse(allowed(None))
        self.approved["200"] = True
        self.assertTrue(allowed(200))
        self.approved.pop("200")
        self.assertFalse(allowed(200))

    def test_no_referral_gate(self):
        self.assertNotIn("referral_gate_handler", SOURCE)
        self.assertNotIn("referral_required", SOURCE)


class ProviderAllocationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.approved = {}
        self.post = AsyncMock()
        self.archive_calls = []
        archive = SimpleNamespace(record=lambda n: self.archive_calls.append(n))
        self.ns = {
            "re": re, "asyncio": asyncio,
            "ADMINS": [100], "AZ_ACCESS_FILE": "test.json",
            "load_data": lambda path: self.approved,
            "number_archive": archive,
            "client_async": SimpleNamespace(post=self.post),
            "BASE_URL": "https://example.invalid",
        }
        for name in ("is_admin", "is_az_range", "az_range_allowed"):
            self.ns[name] = extract(name, self.ns)
        self.get_number = extract("get_number_from_api", self.ns)

    async def test_denied_az_range_never_calls_provider(self):
        self.assertEqual((None, None), await self.get_number("99450211", requester_id=200))
        self.post.assert_not_awaited()

    async def test_no_unattributed_az_allocation(self):
        self.assertEqual((None, None), await self.get_number("99450"))
        self.post.assert_not_awaited()

    async def test_approved_allocation_checks_returned_prefix(self):
        self.approved["200"] = True
        self.post.return_value = SimpleNamespace(json=lambda: {
            "meta": {"code": 200},
            "data": {"full_number": "+994502111234", "country": "Azerbaijan"},
        })
        num, country = await self.get_number("99450211", requester_id=200)
        self.assertEqual(num, "+994502111234")
        self.assertEqual(country, "Azerbaijan")
        self.assertEqual(self.archive_calls, [num])

    async def test_wrong_country_is_rejected(self):
        self.post.return_value = SimpleNamespace(json=lambda: {
            "meta": {"code": 200},
            "data": {"full_number": "+994502111234", "country": "Azerbaijan"},
        })
        self.assertEqual((None, None), await self.get_number("234", requester_id=200))
        self.assertEqual(self.archive_calls, [])


if __name__ == "__main__":
    unittest.main()
