"""Static parity checks for Telegram Mini App, world countries and +994 access.

Run offline. No Telegram credentials, OTP contents or provider number requests.
"""
import ast
import re
import time
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from number_pricing import PricingError, initial_prices, quote_range
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HTML = (ROOT / "docs/index.html").read_text(encoding="utf-8")
JS = (ROOT / "docs/app.js").read_text(encoding="utf-8")
PY = (ROOT / "main.py").read_text(encoding="utf-8")
MODULE = ast.parse(PY)


class IdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.tabs = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        if "id" in props:
            self.ids.append(props["id"])
        if tag == "button" and "tab-btn" in props.get("class", ""):
            self.tabs.append(props.get("onclick", ""))


class MiniAppParityTests(unittest.TestCase):
    def test_navigation_and_new_panels(self):
        parser = IdParser()
        parser.feed(HTML)
        self.assertEqual(len(parser.ids), len(set(parser.ids)), "Duplicate IDs in Mini App HTML")
        for name in ("services", "countries", "azerbaijan", "active", "history", "admin"):
            self.assertIn("tab-" + name, parser.ids)
            self.assertIn("switchTab('" + name + "')", parser.tabs)
        for name in ("country-search", "countries-list", "country-range-list",
                     "az-operators-list", "request-az-access", "admin-users-list",
                     "admin-target-id"):
            self.assertIn(name, parser.ids)

    def test_api_paths_have_matching_server_handlers(self):
        funcs = {n.name for n in MODULE.body if isinstance(n, ast.AsyncFunctionDef)}
        self.assertTrue({
            "miniapp_countries_api", "miniapp_az_access_api",
            "miniapp_services_api", "miniapp_admin_api", "miniapp_get_number_api"
        } <= funcs)
        for path in ("/api/countries", "/api/az-access", "/api/services",
                     "/api/admin", "/api/get-number", "/api/dashboard"):
            self.assertIn(path, PY)
            self.assertIn(path, JS)

    def test_client_handles_real_country_selection(self):
        self.assertIn('encodeURIComponent(iso)', JS)
        self.assertIn('country_iso: countryIso', JS)
        self.assertIn('item.service', JS)
        self.assertIn('az_catalog', PY)
        self.assertIn('build_all_country_rows', PY)

    def test_approval_checks_are_authoritative(self):
        self.assertIn('if not is_admin(uid)', PY)
        self.assertIn('if not az_range_allowed(uid)', PY)
        self.assertIn('"admin_approval_required"', PY)
        self.assertIn('selected_rid not in actual_ranges', PY)
        self.assertIn('if not selected_country or not selected_country["ranges"]:', PY)
        self.assertIn('_miniapp_auth(request)', PY)
        self.assertNotIn("referral_required", JS)

    def test_untrusted_api_data_uses_safe_text_output(self):
        # Render API responses must not be interpolated into HTML.
        self.assertNotIn(".innerHTML", JS)
        self.assertIn("textContent", JS)
        self.assertIn("createElement", JS)

    def test_operator_catalog_is_compatible(self):
        from world_country_codes import WORLD_COUNTRIES
        self.assertGreaterEqual(len(WORLD_COUNTRIES), 240)
        for prefix in ("99440", "99444"):
            self.assertIn(prefix, PY)
        for name in ("Catel", "CDMA", "Bakcell", "Azercell", "Nar"):
            self.assertIn(name, PY)



class MiniAppCountryIsoRegressionTests(unittest.IsolatedAsyncioTestCase):
    """Reproduce +994 Mini App requests without contacting the number provider."""

    async def asyncSetUp(self):
        self.allocate = AsyncMock(return_value=("+994702101234", "Azerbaijan"))
        self.orders = {}
        target = next(node for node in MODULE.body if isinstance(node, ast.AsyncFunctionDef)
                      and node.name == "miniapp_get_number_api")

        def json_response(payload, status=200):
            return {"status": status, "body": payload}

        namespace = {
            "web": SimpleNamespace(json_response=json_response),
            "_miniapp_cors": lambda value: value,
            "_miniapp_auth": lambda request: ({"id": 77}, None),
            "is_user_banned": lambda uid: False,
            "is_az_range": lambda rid: str(rid).startswith("994"),
            "az_range_allowed": lambda uid: True,
            "az_catalog_lookup": lambda **kwargs: {"name": "Nar"},
            "fetch_services_cached": AsyncMock(return_value={}),
            "load_number_prices": initial_prices,
            "quote_range": quote_range,
            "PricingError": PricingError,
            "get_number_from_api": self.allocate,
            "normalize_number": lambda number: re.sub(r"\D", "", str(number)),
            "add_number_taken": lambda uid, count: None,
            "active_numbers": {},
            "datetime": datetime,
            "save_number_range_info": lambda uid, number, rid: None,
            "mask_number": lambda number: "****" + number[-4:],
            "miniapp_orders": self.orders,
            "time": time,
        }
        compiled = compile(ast.fix_missing_locations(
            ast.Module(body=[target], type_ignores=[])), "main.py", "exec")
        exec(compiled, namespace)
        self.handler = namespace["miniapp_get_number_api"]

    async def request_number(self, extra=None):
        body = {"service": "az", "country": "994", "range": "99470210",
                "expected_price_cents": 1000}
        if extra:
            body.update(extra)
        request = SimpleNamespace(method="POST", json=AsyncMock(return_value=body))
        return await self.handler(request)

    async def test_json_null_country_iso_never_becomes_string_none(self):
        response = await self.request_number({"country_iso": None})
        self.assertEqual(response["status"], 200, response)
        self.assertTrue(response["body"]["success"])
        self.assertEqual(self.allocate.await_args.kwargs["country_iso"], "")
        self.assertEqual(self.allocate.await_args.kwargs["expected_price_cents"], 1000)

    async def test_missing_country_iso_is_accepted(self):
        response = await self.request_number()
        self.assertEqual(response["status"], 200, response)
        self.assertEqual(self.allocate.await_args.kwargs["country_iso"], "")

    async def test_explicit_az_country_iso_is_accepted(self):
        response = await self.request_number({"country_iso": " az "})
        self.assertEqual(response["status"], 200, response)
        self.assertEqual(self.allocate.await_args.kwargs["country_iso"], "AZ")

    async def test_wrong_country_iso_remains_rejected(self):
        response = await self.request_number({"country_iso": "US"})
        self.assertEqual(response["status"], 400, response)
        self.assertEqual(response["body"]["error"], "country_mismatch")
        self.allocate.assert_not_awaited()

if __name__ == "__main__":
    unittest.main()
