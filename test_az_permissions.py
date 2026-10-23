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



def catalog_constants(namespace):
    for node in MODULE.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        if name in ("AZ_OPERATOR_PREFIXES", "AZ_RANGE_SUFFIXES"):
            namespace[name] = ast.literal_eval(node.value)


class AzerbaijanCatalogTests(unittest.TestCase):
    def setUp(self):
        self.ns = {"re": re}
        catalog_constants(self.ns)
        self.catalog = extract("az_range_catalog", self.ns)
        self.lookup = extract("az_catalog_lookup", self.ns)

    def test_requested_operator_order_and_subranges(self):
        groups = self.catalog()
        self.assertEqual(
            [item["name"] for item in groups],
            ["Bakcell", "Azercell", "Nar", "Naxtell", "Catel", "CDMA"],
        )
        pairs = [
            (item["prefix"], entry["rid"])
            for group in groups
            for item in group["prefixes"]
            for entry in item["ranges"]
        ]
        expected = [
            ("99455", "99455210"), ("99455", "99455211"),
            ("99499", "99499210"), ("99499", "99499211"),
            ("99450", "99450210"), ("99450", "99450211"),
            ("99451", "99451210"), ("99451", "99451211"),
            ("99410", "99410210"), ("99410", "99410211"),
            ("99470", "99470210"), ("99470", "99470211"),
            ("99477", "99477210"), ("99477", "99477211"),
            ("99460", "99460210"), ("99460", "99460211"),
            ("99440", "99440210"), ("99440", "99440211"),
            ("99444", "99444210"), ("99444", "99444211"),
        ]
        self.assertEqual(pairs, expected)
        self.assertEqual(len(pairs), 20)

    def test_availability_only_when_exactly_listed(self):
        groups = self.catalog({"svc": ["99450211", "99455XXX", "99460210"]})
        flags = {
            range_entry["rid"]: range_entry["listed_in_api"]
            for group in groups
            for prefix in group["prefixes"]
            for range_entry in prefix["ranges"]
        }
        self.assertTrue(flags["99450211"])
        self.assertTrue(flags["99460210"])
        self.assertFalse(flags["99450210"])
        self.assertFalse(flags["99455211"])

    def test_lookup_rejects_unknown_range(self):
        self.assertEqual(self.lookup(rid="99450211")["name"], "Azercell")
        self.assertEqual(self.lookup(prefix="99499")["name"], "Bakcell")
        self.assertEqual(self.lookup(prefix="99440")["name"], "Catel")
        self.assertEqual(self.lookup(rid="99444211")["name"], "CDMA")
        self.assertIsNone(self.lookup(rid="99450333"))
        self.assertIsNone(self.lookup(prefix="99412"))

    def test_extra_api_ranges_are_sorted_and_owned_by_operator(self):
        services = {"wa": ["99450300", "99450212", "99444333", "99455077"],
                    "tg": ["99450300", "994501234567"]}
        groups = self.catalog(services)
        azercell = next(row for row in groups if row["id"] == "azercell")
        az50 = next(row for row in azercell["prefixes"] if row["prefix"] == "99450")
        self.assertEqual(
            [row["rid"] for row in az50["ranges"]],
            ["99450210", "99450211", "99450212", "99450300"],
        )
        self.assertFalse(az50["ranges"][0]["listed_in_api"])
        self.assertTrue(az50["ranges"][2]["listed_in_api"])
        self.assertEqual(az50["ranges"][2]["source"], "api")
        self.assertIsNotNone(self.lookup(rid="99444333", services=services))
        self.assertIsNone(self.lookup(rid="99444333"))
        self.assertIsNone(self.lookup(rid="994501234567", services=services))
        self.assertEqual(
            len(self.catalog(services)[0]["prefixes"][0]["ranges"]), 3
        )


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
