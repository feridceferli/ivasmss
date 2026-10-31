"""Offline tests for non-sending, authenticated, persisted SMS diagnostics."""
import ast
import tempfile
import unittest
from pathlib import Path

from sms_test_diagnostics import SmsDiagnosticError, SmsDiagnosticStore, normalize_test_phone


class DiagnosticTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SmsDiagnosticStore(Path(self.tmp.name) / "diagnostics.json")

    async def asyncTearDown(self):
        self.tmp.cleanup()

    async def test_default_only_admin(self):
        self.assertTrue(self.store.snapshot(101, True)["available"])
        self.assertFalse(self.store.snapshot(102, False)["available"])
        self.assertFalse(self.store.snapshot(101, True)["enabled_for_all"])

    async def test_simulation_does_not_send_and_remembers_owned_phone(self):
        entry = await self.store.simulate(101, "+994501234567", True, is_admin=True)
        self.assertEqual(entry["real_sms_sent"], 0)
        self.assertEqual(entry["status"], "simulated_no_sms_sent")
        same_file = SmsDiagnosticStore(self.store.path)
        self.assertEqual(same_file.snapshot(101, True)["history"][0]["phone"], "+994501234567")
        self.assertEqual(same_file.snapshot(101, True)["total_real_sms_sent"], 0)
        self.assertEqual(same_file.snapshot(101, True)["third_party_endpoints_disabled"], 49)

    async def test_non_admin_cannot_simulate_when_off(self):
        with self.assertRaises(SmsDiagnosticError) as err:
            await self.store.simulate(202, "+994501234567", True, is_admin=False)
        self.assertEqual(err.exception.code, "feature_disabled")

    async def test_admin_toggle_and_user_private_history(self):
        await self.store.set_visibility(True)
        await self.store.simulate(101, "+994501234567", True)
        await self.store.simulate(202, "+994551234567", True)
        self.assertEqual(len(self.store.snapshot(101, False)["history"]), 1)
        self.assertEqual(self.store.snapshot(101, False)["history"][0]["user_id"], 101)
        self.assertEqual(len(self.store.snapshot(101, True)["history"]), 2)
        await self.store.set_visibility(False)
        self.assertFalse(self.store.snapshot(101, False)["available"])
        self.assertFalse(self.store.snapshot(101, False)["history"])
        self.assertEqual(len(self.store.snapshot(101, True)["history"]), 2)

    async def test_consent_and_number_format(self):
        self.assertEqual(normalize_test_phone("+994 50 123 45 67"), "+994501234567")
        self.assertIsNone(normalize_test_phone("994501234567"))
        self.assertIsNone(normalize_test_phone("+0000000"))
        self.assertIsNone(normalize_test_phone("javascript:alert(1)"))
        with self.assertRaises(SmsDiagnosticError) as err:
            await self.store.simulate(101, "+994501234567", False, is_admin=True)
        self.assertEqual(err.exception.code, "consent_required")

    async def test_throttling(self):
        for index in range(5):
            await self.store.simulate(101, "+994501234567", True, is_admin=True)
        with self.assertRaises(SmsDiagnosticError) as err:
            await self.store.simulate(101, "+994501234567", True, is_admin=True)
        self.assertEqual(err.exception.code, "rate_limited")

    async def test_bad_archive_fails_closed(self):
        self.store.path.write_text("corrupted")
        with self.assertRaises(SmsDiagnosticError):
            self.store.snapshot(101, True)


class AuthAndWiringTests(unittest.TestCase):
    def test_api_restricts_admin_settings_and_authenticated_access(self):
        main = Path("main.py").read_text(encoding="utf-8")
        tree = ast.parse(main)
        func = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                    and n.name == "miniapp_sms_diagnostics_api")
        body = ast.get_source_segment(main, func)
        self.assertIn("_miniapp_auth(request)", body)
        self.assertIn("if is_user_banned(uid):", body)
        self.assertIn('if action == "visibility":', body)
        self.assertIn("if not admin:", body)
        self.assertIn('elif action == "simulate":', body)
        self.assertIn("if not user_backup.ready:", body)
        self.assertIn('"/api/sms-diagnostics", miniapp_sms_diagnostics_api', main)

    def test_private_backup_and_safe_frontend(self):
        main = Path("main.py").read_text(encoding="utf-8")
        backup = Path("user_backup.py").read_text(encoding="utf-8")
        js = Path("docs/sms-test-diagnostics.js").read_text(encoding="utf-8")
        html = Path("docs/index.html").read_text(encoding="utf-8")
        self.assertIn('"sms_test_diagnostics": SMS_TEST_DIAGNOSTICS_FILE', main)
        self.assertIn('"sms_test_diagnostics",', backup)
        self.assertIn('id="sms-diagnostics-tab-button" hidden', html)
        self.assertIn('id="admin-sms-lab-section"', html)
        self.assertNotIn(".innerHTML", js)
        self.assertIn("Provayderə qəbul edilən real SMS:", js)
        self.assertIn('body: {action: "send_live"', js)
        self.assertIn("sms_live_sender.status()", main)
        self.assertIn("Simulyasiya", html)


if __name__ == "__main__":
    unittest.main()
