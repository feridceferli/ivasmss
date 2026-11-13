"""Guard against accidentally reintroducing retired provider and SMS demo UI."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RemovedPanelsTests(unittest.TestCase):
    def test_no_retired_backend_routes_or_workers(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        for marker in (
            "miniapp_sms_diagnostics_api", "miniapp_admin_provider_feeds_api",
            "miniapp_admin_provider_numbers_api", "admin_provider_number_command",
            "fake_otp_loop", "admin_fake_otp_menu", "run_ivasmsper_websocket",
            'CommandHandler("green_sms"', 'CommandHandler("ivasmsper"',
            '"/api/test-sms"', '"/api/sms-diagnostics"',
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_no_retired_web_sections(self):
        page = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        app = (ROOT / "docs/app.js").read_text(encoding="utf-8")
        for marker in (
            "admin-green_sms-section", "admin-ivasmsper-section",
            "admin-sms-lab-section", "tab-sms-lab", "admin-fake-otp-section",
            "admin-provider-feeds.js", "sms-test-diagnostics.js",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, page)
        self.assertNotIn('"sms-lab"', app)

    def test_core_purchasing_and_payment_unchanged(self):
        source = (ROOT / "main.py").read_text(encoding="utf-8")
        for marker in (
            "market_bot_ui.register(app)", "rental_ledger.settle_due",
            '"/api/get-number"', '"/api/services"', "API_KEY",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)
        for filename in ("market_bot_ui.py", "marketplace.py", "manual_topups.py"):
            self.assertTrue((ROOT / filename).exists(), filename)


if __name__ == "__main__":
    unittest.main()
