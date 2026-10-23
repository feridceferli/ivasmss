"""Offline tests for full-number display restricted to active order owners.

No Telegram credentials, API calls, real phone numbers or OTP data.
"""
import ast
import re
import time
import unittest
from pathlib import Path

SOURCE = Path(__file__).with_name("main.py").read_text(encoding="utf-8")
JS = (Path(__file__).parent / "docs" / "app.js").read_text(encoding="utf-8")
HTML = (Path(__file__).parent / "docs" / "index.html").read_text(encoding="utf-8")
MODULE = ast.parse(SOURCE)


def isolated_function(name, context):
    match = [node for node in MODULE.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
             and node.name == name]
    if len(match) != 1:
        raise AssertionError("Expected one function: " + name)
    unit = ast.fix_missing_locations(ast.Module(body=match, type_ignores=[]))
    exec(compile(unit, "main.py", "exec"), context)
    return context[name]


class MiniAppActiveNumbersTests(unittest.TestCase):
    def setUp(self):
        self.active = {}
        self.ctx = {
            "time": time,
            "active_numbers": self.active,
            "normalize_number": lambda x: re.sub(r"\D", "", str(x or "")),
        }
        self.safe_order = isolated_function("_safe_order", self.ctx)
        self.order = {
            "id": "demo-owned",
            "label": "Aktiv sifariş",
            "number_masked": "+994 50 *** ** 12",
            "full_number": "+994502110012",
            "range": "99450211XXX",
            "status": "Aktiv",
            "created_at": time.time(),
        }

    def test_owner_sees_full_number_without_stars(self):
        self.active["994502110012"] = {"uid": 125}
        value = self.safe_order(125, self.order)
        self.assertEqual(value["number"], "+994502110012")
        self.assertEqual(value["number_masked"], "+994502110012")
        self.assertNotIn("*", value["number"])

    def test_other_account_cannot_see_full_number(self):
        self.active["994502110012"] = {"uid": 125}
        value = self.safe_order(333, self.order)
        self.assertNotIn("number", value)
        self.assertNotIn("full_number", value)
        self.assertIn("*", value["number_masked"])

    def test_expired_or_inactive_order_not_unmasked(self):
        self.active["994502110012"] = {"uid": 125}
        self.order["created_at"] = time.time() - 3602
        self.assertNotIn("number", self.safe_order(125, self.order))
        self.order["created_at"] = time.time()
        self.order["status"] = "Ləğv edildi"
        self.assertNotIn("number", self.safe_order(125, self.order))

    def test_demo_order_never_yields_copyable_number(self):
        self.order.pop("full_number")
        self.assertNotIn("number", self.safe_order(125, self.order))

    def test_dashboard_filters_owner_and_has_unmasked_number(self):
        dashboard = next(node for node in MODULE.body
                         if isinstance(node, ast.AsyncFunctionDef)
                         and node.name == "miniapp_dashboard")
        code = ast.get_source_segment(SOURCE, dashboard)
        self.assertIn('int(info.get("uid", 0)) != uid', code)
        self.assertIn('"number": "+" + normalize_number(number)', code)
        self.assertIn('if age >= 3600:', code)

    def test_miniapp_copy_action_only_for_full_numbers(self):
        self.assertIn('async function copyPhoneNumber(number)', JS)
        self.assertIn('navigator.clipboard.writeText(number)', JS)
        self.assertIn('document.execCommand("copy")', JS)
        self.assertIn('if (validNumber)', JS)
        self.assertIn('copyPhoneNumber(fullNumber)', JS)
        self.assertIn('order.number || ""', JS)
        self.assertIn('app.js?v=20261023-services-az10', HTML)
        self.assertNotIn('.innerHTML', JS)


if __name__ == "__main__":
    unittest.main()
