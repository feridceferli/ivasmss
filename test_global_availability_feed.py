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
            self.assertEqual(first, "initialized")
            self.assertEqual(len(bot.messages), 0, "Startup must not spam group")
            self.assertTrue(Path(state).exists())
            unchanged = await publish_global_availability_feed(
                services=SAMPLE, now=1300, **args)
            self.assertEqual(unchanged, "unchanged")

            changed = dict(SAMPLE)
            changed["tg"] = SAMPLE["tg"] + ["99440211"]
            cooldown = await publish_global_availability_feed(
                services=changed, now=1100, **args)
            self.assertEqual(cooldown, "cooldown")
            self.assertEqual(len(bot.messages), 0)
            later = await publish_global_availability_feed(
                services=changed, now=1601, **args)
            self.assertEqual(later, "sent")
            self.assertEqual(len(bot.messages), 1)
            self.assertEqual(bot.messages[0]["chat_id"], -100123456)
            self.assertEqual(bot.messages[0]["parse_mode"], "HTML")
            self.assertNotIn("99450211", bot.messages[0]["text"])
            saved = json.loads(Path(state).read_text(encoding="utf-8"))
            self.assertEqual(saved["last_sent"], 1601)
            self.assertNotIn("99440211", json.dumps(saved))
            # A new process with the same stored snapshot cannot resend it.
            new_bot = FakeTelegramBot()
            after_restart = await publish_global_availability_feed(
                services=changed, now=1800, **{**args, "bot": new_bot})
            self.assertEqual(after_restart, "unchanged")
            self.assertFalse(new_bot.messages)

    async def test_failed_send_does_not_mark_seen(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / "feed.json")
            seed = await publish_global_availability_feed(
                services=SAMPLE, bot=FakeTelegramBot(), group_id="-100123456",
                country_prefix_lookup=country_prefix, now=1000, state_file=path)
            self.assertEqual(seed, "initialized")
            original = json.loads(Path(path).read_text(encoding="utf-8"))
            changed = {**SAMPLE, "wa": SAMPLE["wa"] + ["99440211"]}
            bad = FakeTelegramBot(fail=True)
            failed = await publish_global_availability_feed(
                services=changed, bot=bad, group_id="-100123456",
                country_prefix_lookup=country_prefix, now=1601, state_file=path)
            self.assertEqual(failed, "send_failed")
            self.assertEqual(json.loads(Path(path).read_text(encoding="utf-8")), original)
            good = FakeTelegramBot()
            retry = await publish_global_availability_feed(
                services=changed, bot=good, group_id="-100123456",
                country_prefix_lookup=country_prefix, now=1602, state_file=path)
            self.assertEqual(retry, "sent")
            self.assertEqual(len(good.messages), 1)

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

    async def test_periodic_digest_every_ten_minutes_even_when_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "state.json")
            bot = FakeTelegramBot()
            args = dict(services=SAMPLE, bot=bot, group_id="-100123456",
                        country_prefix_lookup=country_prefix,
                        state_file=path)
            self.assertEqual(await publish_global_availability_feed(
                now=1000, **args), "initialized")
            self.assertEqual(await publish_global_availability_feed(
                now=1599, **args), "unchanged")
            self.assertEqual(await publish_global_availability_feed(
                now=1600, **args), "sent")
            self.assertEqual(len(bot.messages), 1)
            self.assertIn("10 DƏQİQƏLİK", bot.messages[0]["text"])
            self.assertEqual(await publish_global_availability_feed(
                now=1601, **args), "unchanged")
            self.assertEqual(await publish_global_availability_feed(
                now=2200, **args), "sent")
            self.assertEqual(len(bot.messages), 2)

    async def test_new_service_triggers_immediate_group_only_batched_notice(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "state.json")
            bot = FakeTelegramBot()
            args = dict(bot=bot, group_id="-100123456",
                        country_prefix_lookup=country_prefix, state_file=path)
            await publish_global_availability_feed(services=SAMPLE, now=1000, **args)
            updated = {**SAMPLE, "bolt": ["447755"], "discord": ["99440122"]}
            self.assertEqual(await publish_global_availability_feed(
                services=updated, now=1030, **args), "new_service")
            self.assertEqual(len(bot.messages), 1)
            sent = bot.messages[0]
            self.assertEqual(sent["chat_id"], -100123456)
            self.assertIn("BOLT", sent["text"])
            self.assertIn("DISCORD", sent["text"])
            self.assertNotIn("447755", sent["text"])
            self.assertEqual(await publish_global_availability_feed(
                services=updated, now=1040, **args), "unchanged")
            self.assertEqual(await publish_global_availability_feed(
                services=updated, now=1630, **args), "sent")
            self.assertEqual(len(bot.messages), 2)
            # A removed service is never falsely classified as new on return.
            await publish_global_availability_feed(services=SAMPLE, now=2230, **args)
            restored = await publish_global_availability_feed(
                services=updated, now=2240, **args)
            self.assertIn(restored, ("cooldown", "unchanged"))
            self.assertEqual(len(bot.messages), 3)

    async def test_failed_immediate_service_send_retries_without_state_advance(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "state.json")
            args = dict(group_id="-100123456", country_prefix_lookup=country_prefix,
                        state_file=path)
            await publish_global_availability_feed(services=SAMPLE, now=1000,
                                                   bot=FakeTelegramBot(), **args)
            before = Path(path).read_text(encoding="utf-8")
            new = {**SAMPLE, "new-app": ["99440211"]}
            self.assertEqual(await publish_global_availability_feed(
                services=new, bot=FakeTelegramBot(fail=True), now=1030, **args),
                "send_failed")
            self.assertEqual(Path(path).read_text(encoding="utf-8"), before)
            bot = FakeTelegramBot()
            self.assertEqual(await publish_global_availability_feed(
                services=new, bot=bot, now=1060, **args), "new_service")
            self.assertEqual(len(bot.messages), 1)
            again = FakeTelegramBot()
            self.assertEqual(await publish_global_availability_feed(
                services=new, bot=again, now=1100, **args), "unchanged")
            self.assertEqual(len(again.messages), 0)

    async def test_legacy_state_migration_does_not_announce_every_service(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "state.json")
            state = availability_snapshot(SAMPLE, country_prefix)
            Path(path).write_text(json.dumps({
                "fingerprint": state["fingerprint"],
                "country_counts": state["country_counts"],
                "last_sent": 1000,
            }), encoding="utf-8")
            bot = FakeTelegramBot()
            args = dict(services=SAMPLE, bot=bot, group_id="-100123456",
                        country_prefix_lookup=country_prefix, state_file=path)
            self.assertEqual(await publish_global_availability_feed(
                now=1030, **args), "unchanged")
            self.assertFalse(bot.messages)
            saved = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual(set(saved["known_services"]), {"tg", "wa"})


if __name__ == "__main__":
    unittest.main()
