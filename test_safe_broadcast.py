import asyncio
import unittest
from unittest.mock import AsyncMock

from telegram.error import Forbidden, NetworkError, RetryAfter
from safe_broadcast import recipient_ids, validate_notice, send_notice


class BroadcastTests(unittest.IsolatedAsyncioTestCase):
    def test_recipients(self):
        self.assertEqual(recipient_ids({"21": {}, "3": {}, "bad": {}, "-1": {}}), [3, 21])

    def test_sensitive_codes_not_broadcast(self):
        with self.assertRaises(ValueError):
            validate_notice("verification code: 123456")
        with self.assertRaises(ValueError):
            validate_notice("parol: secret-token")

    def test_blank_not_allowed(self):
        with self.assertRaises(ValueError):
            validate_notice("  ")

    async def test_html_escaped_and_deduped(self):
        bot = type("Fake", (), {})()
        bot.send_message = AsyncMock(return_value=None)
        summary = await send_notice(bot, [11, 11, 22], "<b>Məlumat</b>")
        self.assertEqual(summary["targeted"], 2)
        self.assertEqual(summary["sent"], 2)
        self.assertEqual(bot.send_message.await_count, 2)
        self.assertIn("&lt;b&gt;Məlumat&lt;/b&gt;", bot.send_message.await_args.kwargs["text"])

    async def test_blocked_account_is_counted(self):
        bot = type("Fake", (), {})()
        bot.send_message = AsyncMock(side_effect=Forbidden("Bot was blocked by the user"))
        summary = await send_notice(bot, [33], "Yeni yeniləmə")
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["blocked"], 1)

    async def test_retry_limit_counted(self):
        bot = type("Fake", (), {})()
        bot.send_message = AsyncMock(side_effect=RetryAfter(1))
        from unittest.mock import patch
        with patch("safe_broadcast.asyncio.sleep", new=AsyncMock()):
            summary = await send_notice(bot, [44], "Yeni məlumat")
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["retry_exhausted"], 1)
        self.assertEqual(bot.send_message.await_count, 4)

    async def test_temporary_network_failure_does_not_skip_user(self):
        bot = type("Fake", (), {})()
        bot.send_message = AsyncMock(side_effect=[NetworkError("offline"), None, None])
        from unittest.mock import patch
        with patch("safe_broadcast.asyncio.sleep", new=AsyncMock()):
            summary = await send_notice(bot, [11, 22], "Yeni məlumat")
        self.assertEqual(summary["sent"], 2)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual([call.kwargs["chat_id"] for call in bot.send_message.await_args_list], [11, 11, 22])

    async def test_full_server_retry_delay_is_respected(self):
        bot = type("Fake", (), {})()
        bot.send_message = AsyncMock(side_effect=[RetryAfter(120), None])
        from unittest.mock import patch
        with patch("safe_broadcast.asyncio.sleep", new=AsyncMock()) as sleep:
            summary = await send_notice(bot, [44], "Yeni məlumat")
        self.assertEqual(summary["sent"], 1)
        sleep.assert_any_await(120.5)


if __name__ == "__main__":
    unittest.main()

