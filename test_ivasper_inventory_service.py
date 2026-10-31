"""Standalone Render IVASPER stock API: no external or real number calls."""
import os
import unittest
from unittest.mock import patch
from aiohttp.test_utils import make_mocked_request
from ivasper_inventory_service import (
    _authorized, _static_inventory, _stock_payload_only, create_app
)


class InventoryServiceTests(unittest.TestCase):
    def test_empty_environment_source_is_independent(self):
        with patch.dict(os.environ, {"IVASPER_STOCK_JSON": '{"numbers":[]}'}):
            self.assertEqual(_static_inventory(), [])

    def test_independent_environment_numbers(self):
        payload = '{"numbers":[{"number":"+994501234567","country":"Azerbaijan","service":"Telegram"}]}'
        with patch.dict(os.environ, {"IVASPER_STOCK_JSON": payload}):
            self.assertEqual(_static_inventory(), [{
                "number": "+994501234567", "country": "Azerbaijan", "service": "Telegram"
            }])

    def test_reject_sms_otp_imports(self):
        self.assertFalse(_stock_payload_only(
            {"numbers": [{"number": "+994501234567", "otp": "123456"}]}))
        self.assertFalse(_stock_payload_only(
            {"data": [{"num": "+994501234567", "message": "test"}]}))
        self.assertTrue(_stock_payload_only(
            {"numbers": [{"number": "+994501234567"}]}))

    def test_reader_token_must_be_real_secret(self):
        import secrets
        reader = secrets.token_urlsafe(42)
        with patch.dict(os.environ, {"IVASPER_READER_TOKEN": reader}):
            request = make_mocked_request("GET", "/numbers",
                                          headers={"Authorization": "Bearer " + reader})
            self.assertTrue(_authorized(request, "IVASPER_READER_TOKEN"))
            request = make_mocked_request("GET", "/numbers",
                                          headers={"Authorization": "Bearer wrong"})
            self.assertFalse(_authorized(request, "IVASPER_READER_TOKEN"))
        with patch.dict(os.environ, {"IVASPER_READER_TOKEN": ""}):
            request = make_mocked_request("GET", "/numbers")
            self.assertFalse(_authorized(request, "IVASPER_READER_TOKEN"))

    def test_number_import_appends_without_destroying_stock(self):
        import inspect
        from ivasper_inventory_service import add_inventory, read_inventory, import_inventory
        source = inspect.getsource(add_inventory)
        self.assertIn("INSERT INTO ivasper_inventory", source)
        self.assertIn("ON CONFLICT", source)
        self.assertNotIn("DELETE FROM ivasper_inventory", source)
        self.assertIn("init_storage()", inspect.getsource(read_inventory))
        self.assertIn("asyncio.to_thread(add_inventory, rows)", inspect.getsource(import_inventory))
        self.assertIn("persistent_storage_not_connected", inspect.getsource(import_inventory))

    def test_no_postgres_is_error_not_false_empty_inventory(self):
        import asyncio
        import json
        from ivasper_inventory_service import health, get_numbers
        from unittest.mock import patch as mock_patch
        import secrets
        secret = secrets.token_urlsafe(42)
        with mock_patch("ivasper_inventory_service.DATABASE_URL", ""), \\
             mock_patch.dict(os.environ, {"IVASPER_READER_TOKEN": secret}):
            health_response = asyncio.run(
                health(make_mocked_request("GET", "/health")))
            self.assertEqual(health_response.status, 503)
            result = json.loads(health_response.text)
            self.assertFalse(result["ok"])
            self.assertEqual(result["storage"], "database_not_connected")
            request = make_mocked_request(
                "GET", "/numbers", headers={"Authorization": "Bearer " + secret})
            stock_response = asyncio.run(get_numbers(request))
            self.assertEqual(stock_response.status, 503)
            self.assertEqual(json.loads(stock_response.text)["error"],
                             "persistent_storage_not_connected")

    def test_isolated_routes_only(self):
        app = create_app()
        routes = [route.resource.canonical for route in app.router.routes()]
        for path in ("/health", "/numbers", "/import"):
            self.assertIn(path, routes)
        for forbidden in ("/api/get-number", "/api/dashboard",
                          "/api/orders", "/api/services", "/api/ivasper"):
            self.assertNotIn(forbidden, routes)


if __name__ == "__main__":
    unittest.main()
