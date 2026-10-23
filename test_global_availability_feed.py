"""Offline tests for the metadata-only global Telegram availability digest.

No SMS, OTP, third-party phone data or live network access is involved.
"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from global_availability_feed import (
    availability_snapshot,
    compose_availability_notice,
    publish_global_availability_feed,
)


def country_prefix(number):
    for code in ("994", "1246", "44", "1"):
        if number.startswith(code):
            return code
    return None


def country_name(code):
    return ("🌍", {"994": "Azerbaijan", "1246": "Barbados",
                     "44": "United Kingdom", "1": "United States"}.get(code, ""))


SAMPLE = {
    "wa": ["99450211", "99455210", "447700", "1246XXX"],
    "tg": ["99450211", "199900", "not-a-range"],
}


class SnapshotTests(unittest.TestCase):
    def test_country_and_service_summary_without_numbers(self):
        snap = availability_snapshot(SAMPLE, country_prefix)
        self.assertEqual(snap["services"], 2)
        self.assertEqual(snap["countries"], 4)
        self.assertEqual(snap["range_entries"], 6)
        self.assertEqual(snap["country_counts"]["994"], 3)
        self.assertTrue(len(snap["fingerprint"]) == 64)
        self.assertNotIn("99450211", json.dumps(snap))

    def test_snapshot_ignores_provider_order(self):
        a = availability_snapshot(SAMPLE, country_prefix)
        b = availability_snapshot({
            "tg": list(reversed(SAMPLE["tg"])),
            "wa": list(reversed(SAMPLE["wa"])),
        }, country_prefix)
        self.assertEqual(a["fingerprint"], b["fingerprint"])

    def test_notice_contains_aggregates_not_credentials(self):
        snap = availability_snapshot(SAMPLE, country_prefix)
        notice = compose_availability_notice(snap, country_name_lookup=country_name)
        for label in ("GLOBAL FEED", "Ölkə kodları", "Xidmət/range",
                      "SMS/OTP", "994"):
            self.assertIn(label, notice)
        for sensitive in ("99450211", "447700", "199900"):
            self.assertNotIn(sensitive, notice)
        self.assertLess(len(notice), 1600)


class FakeTelegramBot:
    def __init__(self, fail=False):
        self.messages = []
        self.fail = fail

    async def send_message(self, **kwargs):
        if self.fail:
            raise RuntimeError("test failure")
        self.messages.append(kwargs)


class PublishingTests(unittest.IsolatedAsyncioTestCase):
    async def test_group_only_dedupe_cooldown_and_recovery(self):
        with tempfile.TemporaryDirectory() as root:
            state = str(Path(root) / "feed.json")
            bot = FakeTelegramBot()
            args = dict(bot=bot, group_id="-100123456", country_prefix_lookup=country_prefix,
                        country_name_lookup=country_name, state_file=state)
            first = await publish_global_availability_feed(
                services=SAMPLE, now=1000, **args)
            self.assertEqual(first, "sent")
            self.assertEqual(len(bot.messages), 1)
            self.assertEqual(bot.messages[0]["chat_id"], -100123456)
            self.assertEqual(bot.messages[0]["parse_mode"], "HTML")
            self.assertNotIn("99450211", bot.messages[0]["text"])
            unchanged = await publish_global_availability_feed(
                services=SAMPLE, now=1600, **args)
            self.assertEqual(unchanged, "unchanged")

            changed = dict(SAMPLE)
            changed["tg"] = SAMPLE["tg"] + ["99440211"]
            cooldown = await publish_global_availability_feed(
                services=changed, now=1100, **args)
            self.assertEqual(cooldown, "cooldown")
            self.assertEqual(len(bot.messages), 1)
            later = await publish_global_availability_feed(
                services=changed, now=1401, **args)
            self.assertEqual(later, "sent")
            self.assertEqual(len(bot.messages), 2)
            saved = json.loads(Path(state).read_text(encoding="utf-8"))
            self.assertEqual(saved["last_sent"], 1401)
            self.assertNotIn("99440211", json.dumps(saved))

    async def test_failed_send_does_not_mark_seen(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / "feed.json")
            bad = FakeTelegramBot(fail=True)
            failed = await publish_global_availability_feed(
                services=SAMPLE, bot=bad, group_id="-100123456",
                country_prefix_lookup=country_prefix, now=1000, state_file=path)
            self.assertEqual(failed, "send_failed")
            self.assertFalse(Path(path).exists())
            good = FakeTelegramBot()
            retry = await publish_global_availability_feed(
                services=SAMPLE, bot=good, group_id="-100123456",
                country_prefix_lookup=country_prefix, now=1001, state_file=path)
            self.assertEqual(retry, "sent")

    async def test_no_group_or_empty_catalog(self):
        bot = FakeTelegramBot()
        missing = await publish_global_availability_feed(
            services=SAMPLE, bot=bot, group_id="", country_prefix_lookup=country_prefix)
        self.assertEqual(missing, "not_configured")
        empty = await publish_global_availability_feed(
            services={}, bot=bot, group_id="-100123456",
            country_prefix_lookup=country_prefix)
        self.assertEqual(empty, "empty_catalog")
        self.assertFalse(bot.messages)


if __name__ == "__main__":
    unittest.main()
