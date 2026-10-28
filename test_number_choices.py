"""Five-number choice security, expiration and accounting-free staging tests."""
import unittest
from number_choices import NumberChoiceStore


class FakeClock:
    def __init__(self):
        self.now = 1000.0
    def __call__(self):
        return self.now


class NumberChoiceTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.store = NumberChoiceStore(clock=self.clock)

    def test_five_distinct_real_numbers_and_one_time_choice(self):
        self.assertTrue(self.store.reserve_request(123))
        offered = self.store.create(123, "99450", "WA", "", [
            {"number": "+994501111111", "country": "Azerbaijan"},
            {"number": "+994501111112", "country": "Azerbaijan"},
            {"number": "+994501111113", "country": "Azerbaijan"},
            {"number": "+994501111114", "country": "Azerbaijan"},
            {"number": "+994501111115", "country": "Azerbaijan"},
            {"number": "+994501111116", "country": "Azerbaijan"},
        ])
        self.assertEqual(len(offered["numbers"]), 5)
        self.assertEqual(self.store.get(123, offered["token"], 2)["number"],
                         "+994501111113")
        self.assertIsNone(self.store.get(456, offered["token"], 2))
        self.assertIsNone(self.store.consume(456, offered["token"], 2))
        self.assertIsNone(self.store.consume(123, offered["token"], 100))
        self.assertEqual(self.store.consume(123, offered["token"], 2)["number"],
                         "+994501111113")
        self.assertIsNone(self.store.consume(123, offered["token"], 2))

    def test_invalid_provider_data_and_duplicate_offers_are_skipped(self):
        offer = self.store.create(1, "26134", "tg", "", [
            {"number": "261341234"},
            {"number": "261341234"},
            {"number": "99999"},
            {"number": "abc"},
            {"number": "+261341235"},
        ])
        self.assertEqual(len(offer["numbers"]), 2)
        self.assertEqual(offer["numbers"][1]["number"], "+261341235")

    def test_90_second_expiry_and_30_second_cooldown(self):
        self.assertTrue(self.store.reserve_request(5))
        issued = self.store.create(5, "26134", "tg", "", [{"number": "261341234"}])
        self.assertFalse(self.store.reserve_request(5))
        self.clock.now += 31
        self.assertTrue(self.store.reserve_request(5))
        self.clock.now += 60
        self.assertIsNone(self.store.get(5, issued["token"], 0))

    def test_admin_exemption_allows_immediate_repeat_without_disabling_user_limit(self):
        self.assertTrue(self.store.reserve_request(900, exempt=True))
        self.assertTrue(self.store.reserve_request(900, exempt=True))
        self.assertTrue(self.store.reserve_request(900))
        self.assertFalse(self.store.reserve_request(900))
        self.assertTrue(self.store.reserve_request(901, exempt=True))
        self.assertTrue(self.store.reserve_request(901))
        self.assertFalse(self.store.reserve_request(901))

    def test_new_session_invalidates_old_tokens(self):
        first = self.store.create(9, "44", "WA", "",
                                  [{"number": "44111111"}])
        second = self.store.create(9, "44", "WA", "",
                                   [{"number": "44222222"}])
        self.assertIsNone(self.store.get(9, first["token"], 0))
        self.assertIsNotNone(self.store.get(9, second["token"], 0))

    def test_only_selected_number_is_returned(self):
        offer = self.store.create(11, "44", "WA", "", [
            {"number": "44111111"}, {"number": "44222222"},
            {"number": "44333333"}, {"number": "44444444"},
            {"number": "44555555"},
        ])
        selected = self.store.consume(11, offer["token"], 4)
        self.assertEqual(selected["number"], "+44555555")
        self.assertNotIn("numbers", selected)
        self.assertEqual(len(self.store._offers), 0)


if __name__ == "__main__":
    unittest.main()
