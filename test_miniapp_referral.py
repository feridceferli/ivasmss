"""Offline checks for referral deep links and user-scoped Mini App state."""
import unittest

from miniapp_referral import resolve_referrer, build_referral_link


class ReferralHelperTests(unittest.TestCase):
    def test_new_user_from_correct_deep_link(self):
        self.assertEqual(resolve_referrer("ref_42", 100, ("42", "77"), True), 42)

    def test_existing_numeric_links_still_work(self):
        self.assertEqual(resolve_referrer("42", 100, ("42",), True), 42)

    def test_duplicate_join_does_not_increment(self):
        self.assertIsNone(resolve_referrer("ref_42", 100, ("42",), False))

    def test_invalid_or_self_links_are_rejected(self):
        for arg in ("ref_100", "ref_-12", "ref_abc", "ref_999", "123XXX", "", "ref_42\n123"):
            self.assertIsNone(resolve_referrer(arg, 100, ("42", "100"), True))

    def test_generated_links_are_safe(self):
        self.assertEqual(build_referral_link("sample_bot", 42),
                         "https://t.me/sample_bot?start=ref_42")
        with self.assertRaises(ValueError):
            build_referral_link("bad.example/other", 42)
        with self.assertRaises(ValueError):
            build_referral_link("sample_bot", -1)


if __name__ == "__main__":
    unittest.main()
