"""Regression checks for the customer-facing manual top-up entry point."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class TopupVisibilityTests(unittest.TestCase):
    def test_customer_page_has_payment_action(self):
        page = (ROOT / "docs/index.html").read_text(encoding="utf-8")
        for marker in ('id="tab-topup"', 'id="topup-card"',
                       'id="topup-bot-link"', 'id="topup-history"',
                       'id="admin-topup-card"', "switchTab('topup')"):
            self.assertIn(marker, page)

    def test_backend_requires_auth_and_admin_for_settings(self):
        src = (ROOT / "main.py").read_text(encoding="utf-8")
        begin = src.index("async def miniapp_topup_details_api")
        end = src.index("async def miniapp_prices_api", begin)
        api = src[begin:end]
        for marker in ("_miniapp_auth(request)", "is_user_banned(uid)",
                       "if not is_admin(uid):", "manual_topups.set_card",
                       "manual_topups.set_contact", "row.get(\"uid\") == str(uid)",
                       "user_backup.ready"):
            self.assertIn(marker, api)
        self.assertIn('"/api/topup-details"', src)
        self.assertIn('args[0] == "topup"', src)

    def test_website_and_bot_linked(self):
        js = (ROOT / "docs/app.js").read_text(encoding="utf-8")
        for marker in ('"topup"', "loadTopupDetails", "saveTopupSettings",
                       'api("/api/topup-details"', "copyTopupCard"):
            self.assertIn(marker, js)

if __name__ == "__main__":
    unittest.main()
