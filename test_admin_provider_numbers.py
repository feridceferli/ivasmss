"""No live SMS/provider calls; verify private admin number stock behavior."""
import ast
import tempfile
import unittest
from pathlib import Path

from admin_provider_numbers import (
    AdminNumberStock, NumberStockError, normalize_number, parse_number_lines,
)


class NumberFormatTests(unittest.TestCase):
    def test_phone_validation(self):
        self.assertEqual(normalize_number("+994 50 123 45 67"), "+994501234567")
        self.assertEqual(normalize_number("994-55-123-45-67"), "+994551234567")
        self.assertIsNone(normalize_number("abc"))
        self.assertIsNone(normalize_number("0000000"))
        self.assertIsNone(normalize_number("123"))
        self.assertIsNone(normalize_number("1234567890123456"))

    def test_import_rejects_invalid_and_duplicates(self):
        self.assertEqual(parse_number_lines("+994501234567\n994501234567\n# comment"),
                         ["+994501234567"])
        with self.assertRaises(NumberStockError):
            parse_number_lines("+994501234567\nINVALID")
        with self.assertRaises(NumberStockError):
            parse_number_lines("")
        with self.assertRaises(NumberStockError):
            parse_number_lines("\n".join("+1234567" for _ in range(201)))


class NumberStoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "numbers.json"
        self.store = AdminNumberStock(self.path)

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def test_provider_isolation_and_dedup(self):
        first = await self.store.import_text("green_sms", "+994501234567\n+994551234567")
        self.assertEqual(first["added"], 2)
        second = await self.store.import_text("green_sms", "+994501234567")
        self.assertEqual(second["added"], 0)
        self.assertEqual(self.store.list("ivasmsper")["count"], 0)
        await self.store.import_text("ivasmsper", "+447700900123")
        self.assertEqual(self.store.list("ivasmsper")["count"], 1)

    async def test_delete_only_own_provider_and_persist(self):
        await self.store.import_text("green_sms", "+994501234567")
        with self.assertRaises(NumberStockError):
            await self.store.delete("ivasmsper", "+994501234567")
        self.assertEqual(self.store.list("green_sms")["count"], 1)
        await self.store.delete("green_sms", "+994501234567")
        self.assertEqual(AdminNumberStock(self.path).list("green_sms")["count"], 0)

    async def test_corrupted_local_file_causes_error(self):
        self.path.write_text("NOT JSON")
        with self.assertRaises(NumberStockError):
            self.store.list("green_sms")

    async def test_shared_number_allowed_between_isolated_providers(self):
        await self.store.import_text("green_sms", "+994501234567")
        await self.store.import_text("ivasmsper", "+994501234567")
        self.assertEqual(self.store.list("green_sms")["count"], 1)
        self.assertEqual(self.store.list("ivasmsper")["count"], 1)


class NumberStockAccessTests(unittest.TestCase):
    def test_private_backup_and_server_auth(self):
        main = Path("main.py").read_text(encoding="utf-8")
        backup = Path("user_backup.py").read_text(encoding="utf-8")
        tree = ast.parse(main)
        funcs = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                 and n.name == "miniapp_admin_provider_numbers_api"]
        self.assertEqual(len(funcs), 1)
        code = ast.get_source_segment(main, funcs[0])
        self.assertIn("_miniapp_auth(request)", code)
        self.assertIn("if not is_admin(uid) or is_user_banned(uid):", code)
        self.assertIn("if not user_backup.ready:", code)
        self.assertIn("await _commit_admin_number_changes()", code)
        self.assertIn('"/api/admin-provider-numbers", miniapp_admin_provider_numbers_api', main)
        self.assertIn('"admin_provider_numbers": ADMIN_PROVIDER_NUMBERS_FILE', main)
        self.assertIn('"admin_provider_numbers",', backup)

    def test_ui_renders_only_in_admin_and_without_raw_html(self):
        html = Path("docs/index.html").read_text(encoding="utf-8")
        js = Path("docs/admin-provider-feeds.js").read_text(encoding="utf-8")
        self.assertIn('id="tab-admin" class="tab-content" hidden', html)
        for provider in ("green_sms", "ivasmsper"):
            self.assertIn('id="admin-' + provider + '-number-import"', html)
            self.assertIn('id="admin-' + provider + '-numbers"', html)
        self.assertIn("if (!state.isAdmin", js)
        self.assertNotIn(".innerHTML", js)
        self.assertIn("window.importAdminProviderNumbers", js)


if __name__ == "__main__":
    unittest.main()
