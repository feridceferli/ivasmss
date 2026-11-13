import unittest
from topup_ledger import TopupError, create_request, resolve_request, pending_requests


class TopupTests(unittest.TestCase):
    def test_one_approval_one_credit(self):
        users = {"42": {"balance": 4.0}}
        create_request(users, 42, "a" * 16, 250, "a" * 20, now=100)
        self.assertEqual(users["42"]["balance"], 4.0)
        req = resolve_request(users, 42, "a" * 16, True, 1, now=120)
        self.assertEqual(req["status"], "approved")
        self.assertEqual(users["42"]["balance"], 6.5)
        with self.assertRaises(TopupError) as caught:
            resolve_request(users, 42, "a" * 16, True, 1, now=130)
        self.assertEqual(caught.exception.code, "already_reviewed")
        self.assertEqual(users["42"]["balance"], 6.5)

    def test_reject_never_credits(self):
        users = {"42": {"balance": 0}}
        create_request(users, 42, "a" * 16, 300, "a" * 20)
        resolve_request(users, 42, "a" * 16, False, 1)
        self.assertEqual(users["42"]["balance"], 0)

    def test_pending_limit_and_admin_queue(self):
        users = {"42": {"balance": 1.0}}
        for i in range(3):
            create_request(users, 42, str(i), 100, "a" * 20, now=100+i)
        self.assertEqual(len(pending_requests(users)), 3)
        with self.assertRaises(TopupError):
            create_request(users, 42, "four", 100, "a" * 20)
        resolve_request(users, 42, "0", True, 1)
        create_request(users, 42, "four", 100, "a" * 20)
        self.assertEqual(users["42"]["balance"], 2.0)


if __name__ == "__main__":
    unittest.main()
