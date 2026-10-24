"""Privacy checks for the Mini App's read-only withdrawal status.

No payment requests or financial transfers are made by these tests.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
PY = (ROOT / "main.py").read_text(encoding="utf-8")
JS = (ROOT / "docs/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "docs/index.html").read_text(encoding="utf-8")


class WithdrawalsParityTests(unittest.TestCase):
    def test_withdrawals_endpoint_has_authenticated_owner_filter(self):
        tree = ast.parse(PY)
        fn = next(x for x in tree.body
                  if isinstance(x, ast.AsyncFunctionDef) and x.name == "miniapp_withdrawals_api")
        code = ast.get_source_segment(PY, fn)
        self.assertIn("_miniapp_auth(request)", code)
        self.assertIn('if scope == "mine" and str(record.get("user_id")) != str(uid):', code)
        self.assertIn('if scope == "admin" and not is_admin(uid):', code)
        self.assertIn('if request.method != "GET":', code)
        self.assertNotIn('record.get("number")', code)
        self.assertNotIn('record["number"]', code)
        self.assertIn('"withdrawals": values[:100]', code)

    def test_withdrawal_section_is_not_in_miniapp(self):
        # UI removal preserves historical data and the authenticated API.
        self.assertNotIn('id="tab-withdrawals"', HTML)
        self.assertNotIn('id="withdrawals-list"', HTML)
        self.assertNotIn('id="admin-withdrawals-list"', HTML)
        self.assertNotIn("switchTab('withdrawals')", HTML)
        self.assertNotIn('"withdrawals"', JS)
        self.assertNotIn("fetchWithdrawals()", JS)
        self.assertNotIn("fetchAdminWithdrawals()", JS)
        self.assertNotIn("/api/withdrawals", JS)
        self.assertNotIn("renderWithdrawals(", JS)
        self.assertNotIn(".innerHTML", JS)


if __name__ == "__main__":
    unittest.main()
