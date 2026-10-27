"""Offline OTP leaderboard regression tests.

No provider calls, no real OTP codes or private account access.
"""
import unittest
from datetime import datetime, timezone

from otp_leaderboard import otp_leaderboards, leaderboard_page


class OtpLeaderboardTests(unittest.TestCase):
    def test_daily_and_all_time_counts_reset_at_baku_midnight(self):
        users = {
            "1": {"first_name": "Aysel", "last_name": "Quliyeva", "username": "aysel"},
            "2": {"username": "user_two"}
        }
        # UTC 20:00 is midnight in Azerbaijan. Previous-day OTP must be
        # excluded from the new daily ranking while kept in lifetime totals.
        stats = {
            "1": {"otps_received": [
                "2026-10-27T19:59:59", "2026-10-27T20:00:00",
                "2026-10-28T03:00:00",
            ]},
            "2": {"otps_received": ["2026-10-27T20:30:00"]},
        }
        now = datetime(2026, 10, 28, 12, tzinfo=timezone.utc)
        board = otp_leaderboards(stats, users, now=now)
        self.assertEqual(board["date"], "2026-10-28")
        self.assertEqual(board["today_otps"], 3)
        self.assertEqual(board["total_otps"], 4)
        self.assertEqual(board["daily"][0], {"name": "Aysel Quliyeva", "count": 2})
        self.assertEqual(board["all_time"][0]["count"], 3)
        self.assertEqual(board["total_users"], 2)

    def test_legacy_free_activity_is_included_without_double_counting(self):
        stats = {
            "42": {"otps_received": ["2026-10-27T10:00:00"]},
        }
        activity = [
            {"uid": "42", "action": "OTP_RECEIVED", "timestamp": "2026-10-27T10:00:01"},
            {"uid": "42", "action": "OTP_RECEIVED_FREE", "timestamp": "2026-10-27T11:00:01"},
            {"uid": "43", "action": "OTP_RECEIVED_FREE", "timestamp": "2026-10-27T12:00:01"},
            {"uid": "42", "action": "NUMBER_TAKEN", "timestamp": "2026-10-27T13:00:01"},
        ]
        board = otp_leaderboards(
            stats, {"42": {"username": "abc"}, "43": {"first_name": "Elvin"}},
            activity=activity, now=datetime(2026, 10, 27, 15, tzinfo=timezone.utc))
        self.assertEqual(board["total_users"], 2)
        self.assertEqual(board["total_otps"], 3)
        self.assertEqual(board["all_time"][0], {"name": "@abc", "count": 2})
        self.assertEqual(board["today_otps"], 3)

    def test_same_event_in_stats_and_activity_is_not_twice_counted(self):
        stats = {"1": {"otps_received": ["2026-10-27T12:00:00"]}}
        activity = [{"uid": "1", "action": "OTP_RECEIVED_FREE",
                     "timestamp": "2026-10-27T12:00:01"}]
        board = otp_leaderboards(
            stats, {}, activity=activity,
            now=datetime(2026, 10, 27, 14, tzinfo=timezone.utc))
        self.assertEqual(board["total_otps"], 1)

    def test_pagination_returns_all_users_not_only_top_ten(self):
        users = {str(i): {"first_name": f"User {i}"} for i in range(1, 126)}
        stats = {uid: {"otps_received": ["2026-10-27T14:00:00"] * int(uid)}
                 for uid in users}
        board = otp_leaderboards(stats, users,
                                 now=datetime(2026, 10, 27, 16, tzinfo=timezone.utc))
        first = leaderboard_page(board, period="all", limit=50)
        second = leaderboard_page(board, period="all", offset=50, limit=50)
        last = leaderboard_page(board, period="all", offset=100, limit=50)
        self.assertEqual([len(p["leaders"]) for p in (first, second, last)], [50, 50, 25])
        self.assertTrue(first["has_more"])
        self.assertFalse(last["has_more"])
        self.assertEqual(first["total"], 125)
        self.assertEqual(first["leaders"][0]["name"], "User 125")

    def test_bad_timestamps_and_non_otp_history_are_ignored(self):
        stats = {"3": {"otps_received": ["broken", "", None]},
                 "4": {"otps_received": "bad"},
                 "bad": {"otps_received": ["2026-10-27T12:00:00"]}}
        activity = [{"uid": "3", "action": "LOGIN", "timestamp": "2026-10-27T12:00:00"},
                    {"uid": "3", "action": "OTP_RECEIVED_FREE", "timestamp": "not-a-date"}]
        board = otp_leaderboards(stats, {}, activity=activity)
        self.assertEqual(board["today_otps"], 0)
        self.assertEqual(board["total_users"], 1)
        self.assertEqual(board["total_otps"], 3)


if __name__ == "__main__":
    unittest.main()
