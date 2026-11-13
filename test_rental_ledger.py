import copy
import unittest
from rental_ledger import RentalError, reserve, refund, refund_expired, record_sms, set_number


class RentalLedgerTests(unittest.TestCase):
    def test_three_limit_and_refund_once(self):
        users = {"1": {"balance": 10.0}}
        for i in range(3):
            reserve(users, 1, str(i), 125, now=100)
        self.assertEqual(users["1"]["balance"], 6.25)
        with self.assertRaises(RentalError) as caught:
            reserve(users, 1, "four", 125, now=101)
        self.assertEqual(caught.exception.code, "number_limit")
        self.assertEqual(refund_expired(users, now=279), [])
        self.assertEqual(len(refund_expired(users, now=280)), 3)
        self.assertEqual(refund_expired(users, now=281), [])
        self.assertEqual(users["1"]["balance"], 10.0)
        reserve(users, 1, "new", 100, now=300)

    def test_sms_settles_without_bonus_and_never_refunds(self):
        users = {"1": {"balance": 5.0}}
        reserve(users, 1, "abc", 200, now=100)
        set_number(users, 1, "abc", "447700900101")
        self.assertFalse(record_sms(users, 1, "abc", "447700900102", now=110))
        self.assertTrue(record_sms(users, 1, "abc", "447700900101", now=110))
        self.assertFalse(record_sms(users, 1, "abc", "447700900101", now=120))
        self.assertEqual(refund_expired(users, now=500), [])
        self.assertEqual(users["1"]["balance"], 3.0)

    def test_failed_reservation_is_refunded_once(self):
        users = {"1": {"balance": 4.0}}
        reserve(users, "1", "id", 150, now=100)
        self.assertTrue(refund(users, "1", "id", status="failed", now=110))
        self.assertFalse(refund(users, "1", "id", status="failed", now=112))
        self.assertEqual(users["1"]["balance"], 4.0)

    def test_resume_with_serialized_users_state(self):
        users = {"1": {"balance": 2.0}}
        reserve(users, 1, "id", 75, now=100)
        restored = copy.deepcopy(users)
        self.assertEqual(len(refund_expired(restored, now=281)), 1)
        self.assertEqual(restored["1"]["balance"], 2.0)
        self.assertEqual(len(refund_expired(restored, now=300)), 0)


if __name__ == "__main__":
    unittest.main()
