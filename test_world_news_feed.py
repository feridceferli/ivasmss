"""Offline news-source, freshness, provenance and scheduling tests.

No live RSS fetching or Telegram sends are performed.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from unittest.mock import patch

import world_news_feed as news


def make_item(title, link, stamp, description=""):
    date = format_datetime(datetime.fromtimestamp(stamp, timezone.utc))
    return ("<item><title>" + title + "</title><link>" + link +
            "</link><description>" + description + "</description>" +
            "<pubDate>" + date + "</pubDate></item>")


def feed(items):
    return ("<?xml version='1.0'?><rss version='2.0'><channel>" +
            "".join(items) + "</channel></rss>").encode("utf-8")


NOW = 100000.0
WORLD = news.SOURCES[0][1]
TECH = news.SOURCES[1][1]
GUARDIAN = news.SOURCES[2][1]


class FakeResponse:
    def __init__(self, body):
        self.content = body
    def raise_for_status(self):
        return None


class FakeMemoryResponse:
    def __init__(self, translation, code=200):
        self.translation = translation
        self.code = code
    def raise_for_status(self):
        return None
    def json(self):
        return {"responseStatus": self.code,
                "responseData": {"translatedText": self.translation}}


class FakeMemoryClient:
    def __init__(self, translation, code=200):
        self.translation = translation
        self.code = code
        self.calls = []
    async def get(self, url, params):
        self.calls.append((url, params))
        return FakeMemoryResponse(self.translation, self.code)


class FakeRssClient:
    def __init__(self, bodies):
        self.bodies = bodies
        self.calls = []
    async def get(self, url, follow_redirects=True):
        self.calls.append(url)
        return FakeResponse(self.bodies.get(url, feed([])))


class FakeBot:
    def __init__(self, fail=False):
        self.messages = []
        self.fail = fail
    async def send_message(self, **data):
        if self.fail:
            raise RuntimeError("test Telegram failure")
        self.messages.append(data)


class FakeAiResponse:
    def __init__(self, content):
        self.content = content
    def raise_for_status(self):
        return None
    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


class FakeAiClient:
    def __init__(self, content):
        self.content = content
        self.payload = None
    async def post(self, endpoint, json, headers):
        self.payload = json
        return FakeAiResponse(self.content)


class NewsParsingTests(unittest.TestCase):
    def test_recent_source_link_and_escaping(self):
        payload = feed([
            make_item("New space robot launched for deep sea research",
                      "https://www.bbc.com/news/science-111?utm_source=rss",
                      NOW - 100),
            make_item("Worrying old headline from last month",
                      "https://www.bbc.com/news/old", NOW - 40 * 3600),
            make_item("Fake link from misleading site",
                      "https://evilbbc.com/news/abc", NOW - 100),
            make_item("Harmful markup in source",
                      "javascript:alert(1)", NOW - 100),
        ])
        result = news.parse_rss(payload, "BBC World",
                                ("bbc.co.uk", "bbc.com"), now=NOW)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["url"],
                         "https://www.bbc.com/news/science-111")
        self.assertEqual(len(result[0]["id"]), 64)
        summary = "Dəniz tədqiqatı üçün yeni kosmik robot hazırlanıb."
        formatted = news.compose_news_digest(result, {result[0]["id"]: summary})
        self.assertIn("BBC World", formatted)
        self.assertIn(summary, formatted)
        self.assertNotIn("https://", formatted)
        self.assertNotIn("<a ", formatted)
        self.assertNotIn("utm_source=", formatted)
        self.assertEqual(news.compose_news_digest(result), "",
                         "Never display untranslated English article titles")

    def test_bad_xml_future_and_stale_news_are_skipped(self):
        self.assertEqual(news.parse_rss(b"<rss><garbled", "BBC World",
                                        ("bbc.com",), now=NOW), [])
        self.assertEqual(news.parse_rss(
            feed([make_item("A headline with good words", "https://bbc.com/news/x",
                            NOW + 3600)]), "BBC World", ("bbc.com",), now=NOW), [])
        self.assertEqual(news.parse_rss(b"x" * (news.MAX_FEED_BYTES + 1),
                                        "BBC World", ("bbc.com",), now=NOW), [])

    def test_sensitive_headlines_not_amusing(self):
        source = feed([
            make_item("War attack kills people at night",
                      "https://www.bbc.co.uk/news/serious", NOW - 30),
            make_item("Space robot discovered in museum",
                      "https://www.bbc.co.uk/news/space", NOW - 60),
        ])
        items = news.parse_rss(source, "BBC World", ("bbc.co.uk",), now=NOW)
        self.assertEqual(len(news.choose_headlines(items, set())), 1)
        self.assertIn("Space robot", news.choose_headlines(items, set())[0]["title"])

    def test_azeri_world_items_are_prioritized_and_summarized_without_translation(self):
        payload = feed([
            make_item("Alimlər yeni təbiət layihəsini təqdim ediblər",
                      "https://www.azadliq.org/a/elm-xeber/33123456.html",
                      NOW - 100,
                      "Alimlər bildirirlər ki, yeni layihədə robotlardan istifadə olunur."),
        ])
        current = news.parse_rss(payload, "AzadlıqRadiosu",
                                 ("azadliq.org",), now=NOW)
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["language"], "az")
        self.assertGreaterEqual(current[0]["score"], 20)
        self.assertTrue(news._native_az_summary(current[0]).startswith("Alimlər"))
        rendered = news.compose_news_digest(
            current, {current[0]["id"]: news._native_az_summary(current[0])})
        self.assertIn("Alimlər", rendered)
        self.assertIn("Mənbə: AzadlıqRadiosu", rendered)
        self.assertNotIn("https://", rendered)

    def test_settings_default_validate_and_preserve(self):
        with tempfile.TemporaryDirectory() as root:
            with patch.object(news, "SETTINGS_FILE", str(Path(root) / "settings.json")):
                self.assertTrue(news.load_news_settings()["enabled"])
                self.assertFalse(news.save_news_settings(False)["enabled"])
                self.assertFalse(news.load_news_settings()["enabled"])
                with self.assertRaises(ValueError):
                    news.save_news_settings("false")


class NewsPublishingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = str(Path(self.folder.name) / "news_state.json")
        self.settings = str(Path(self.folder.name) / "news_settings.json")
        self.patcher = patch.object(news, "SETTINGS_FILE", self.settings)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def client_for(self, first=True, second=False):
        entries = []
        if first:
            entries.append(make_item("Space museum opens new exhibition",
                                     "https://www.bbc.co.uk/news/space", NOW - 120))
        if second:
            entries.append(make_item("Scientists invent new underwater robot",
                                     "https://www.bbc.co.uk/news/robot", NOW + 7210))
        return FakeRssClient({WORLD: feed(entries)})

    async def test_first_story_is_sent_and_ten_minute_cooldown_applies(self):
        bot = FakeBot()
        args = dict(bot=bot, group_id="-10012345", state_file=self.path,
                    client=self.client_for(),
                    translate=lambda stories: async_az_translation(stories))
        # Startup seeds all current RSS entries without falsely treating them
        # as new after a Render restart.
        self.assertEqual(await news.publish_world_news(now=NOW, **args), "initialized")
        self.assertEqual(len(bot.messages), 0)
        self.assertEqual(await news.publish_world_news(now=NOW + 100, **args),
                         "cooldown")
        self.assertEqual(len(bot.messages), 0)
        # Once due, the same article is not re-sent.
        self.assertEqual(await news.publish_world_news(now=NOW + 601, **args),
                         "nothing_new")
        self.assertEqual(len(bot.messages), 0)

    async def test_new_news_is_group_only_and_deduplicated(self):
        bot = FakeBot()
        await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=self.client_for(), now=NOW,
            translate=lambda stories: async_az_translation(stories))
        next_client = self.client_for(first=True, second=True)
        result = await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=next_client, now=NOW + 7300,
            translate=lambda stories: async_az_translation(stories))
        self.assertEqual(result, "sent")
        self.assertEqual(len(bot.messages), 1,
                         "Only the first genuinely new article is delivered")
        self.assertEqual(bot.messages[-1]["chat_id"], -10012345)
        self.assertIn("Alimlər sualtı robot", bot.messages[-1]["text"])
        self.assertIn("BBC World", bot.messages[-1]["text"])
        self.assertNotIn("utm_", bot.messages[-1]["text"])
        self.assertEqual(bot.messages[-1]["parse_mode"], "HTML")
        self.assertTrue(bot.messages[-1]["disable_web_page_preview"])
        self.assertEqual(len(bot.messages), 1)
        self.assertEqual(await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=next_client, now=NOW + 7400), "cooldown")

    async def test_failed_telegram_delivery_preserves_state(self):
        await news.publish_world_news(
            bot=FakeBot(), group_id="-10012345", state_file=self.path,
            client=self.client_for(), now=NOW,
            translate=lambda stories: async_az_translation(stories))
        original = Path(self.path).read_text(encoding="utf-8")
        client = self.client_for(first=True, second=True)
        result = await news.publish_world_news(
            bot=FakeBot(fail=True), group_id="-10012345",
            state_file=self.path, client=client, now=NOW + 7300,
            translate=lambda stories: async_az_translation(stories))
        self.assertEqual(result, "send_failed")
        self.assertEqual(Path(self.path).read_text(encoding="utf-8"), original)
        bot = FakeBot()
        self.assertEqual(await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=client, now=NOW + 7330,
            translate=lambda stories: async_az_translation(stories)), "sent")
        self.assertEqual(len(bot.messages), 1)

    async def test_disabled_and_missing_group_do_not_fetch_rss(self):
        news.save_news_settings(False)
        bot = FakeBot()
        fake = self.client_for()
        self.assertEqual(await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=fake, now=NOW), "disabled")
        self.assertEqual(fake.calls, [])
        news.save_news_settings(True)
        self.assertEqual(await news.publish_world_news(
            bot=bot, group_id="", state_file=self.path,
            client=fake, now=NOW), "not_configured")
        self.assertEqual(fake.calls, [])

    async def test_optional_ai_translation_rejects_fabricated_numbers(self):
        article = {"id": "test", "title": "Scientists discover 3 planets"}
        with patch.dict(os.environ, {"GROQ_API_KEY": "unit-test-key"}):
            valid = FakeAiClient('{"summaries":["Alimlər 3 planet kəşf ediblər"]}')
            result = await news.translate_headlines(
                [article], client=valid, allow_fallback=False)
            self.assertEqual(result["test"], "Alimlər 3 planet kəşf ediblər")
            invalid = FakeAiClient('{"summaries":["Alimlər 7 planet kəşf ediblər"]}')
            result = await news.translate_headlines(
                [article], client=invalid, allow_fallback=False)
            self.assertFalse(result)

    async def test_native_azerbaijani_story_needs_no_translate_provider(self):
        story = {
            "id": "az-1", "language": "az",
            "title": "Alimlər yeni tədqiqat layihəsini təqdim ediblər",
            "description": "Tədqiqatçılar bildiriblər ki, layihə gələn il davam edəcək."
        }
        with patch.dict(os.environ, {"GROQ_API_KEY": "simulated-unreachable-key"}):
            result = await news.translate_headlines(
                [story], client=FakeAiClient("invalid"),
                fallback_client=FakeMemoryClient("invalid"))
        self.assertIn("Alimlər", result[story["id"]])
        self.assertEqual(len(result), 1)

    async def test_keyless_free_translation_makes_short_az_summary(self):
        story = {"id": "space-1", "title": "Scientists create new space robot",
                 "description": "Researchers say the robot can explore distant planets."}
        backend = FakeMemoryClient(
            "Alimlər yeni kosmik robot hazırlayıblar. Robot uzaq planetləri araşdıra bilər.")
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            result = await news.translate_headlines(
                [story], fallback_client=backend)
        self.assertIn(story["id"], result)
        self.assertEqual(len(backend.calls), 1)
        self.assertEqual(backend.calls[0][0], news.MYMEMORY_ENDPOINT)
        self.assertEqual(backend.calls[0][1]["langpair"], "en|az-AZ")
        self.assertNotIn("http", result[story["id"]])

    async def test_no_english_or_links_when_translation_unavailable(self):
        bot = FakeBot()
        await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=self.client_for(), now=NOW,
            translate=lambda stories: async_az_translation(stories))
        before = Path(self.path).read_text(encoding="utf-8")
        later = self.client_for(first=False, second=True)
        unavailable = await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=later, now=NOW + 7300,
            translate=lambda stories: async_unavailable_translation())
        self.assertEqual(unavailable, "translation_unavailable")
        self.assertEqual(len(bot.messages), 0,
                         "Failed translation must not create a new post")
        self.assertEqual(Path(self.path).read_text(encoding="utf-8"), before)
        self.assertEqual(await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=later, now=NOW + 7330,
            translate=lambda stories: async_az_translation(stories)), "sent")
        self.assertEqual(len(bot.messages), 1)
        self.assertNotIn("https://", bot.messages[-1]["text"])
        self.assertNotIn("<a ", bot.messages[-1]["text"])
        self.assertNotIn("underwater robot", bot.messages[-1]["text"])

    async def test_republished_url_and_punctuation_only_changes_never_repost(self):
        bot = FakeBot()
        first = feed([make_item(
            "Alimlər yeni kosmik robot layihəsini təqdim ediblər",
            "https://www.bbc.co.uk/news/article-a", NOW - 120)])
        second = feed([make_item(
            "ALİMLƏR: Yeni kosmik robot layihəsini təqdim ediblər!",
            "https://www.bbc.co.uk/news/article-b", NOW + 7100)])
        # Baseline seeds an already published story. A changed article URL
        # and punctuation/casing must not create another group notification.
        self.assertEqual(await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=FakeRssClient({WORLD: first}), now=NOW), "initialized")
        self.assertEqual(await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=FakeRssClient({WORLD: second}), now=NOW + 7200,
            translate=lambda stories: async_az_translation(stories)),
            "nothing_new")
        self.assertFalse(bot.messages)

    async def test_same_story_from_two_publishers_is_not_repeated(self):
        bot = FakeBot()
        original = feed([make_item(
            "Space robot developed for exploring distant planets",
            "https://www.bbc.co.uk/news/space-robots", NOW - 100)])
        duplicate = feed([make_item(
            "Space robot developed for exploring distant planets",
            "https://www.theguardian.com/technology/space-robots", NOW + 7200)])
        await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=FakeRssClient({WORLD: original}), now=NOW)
        result = await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=FakeRssClient({GUARDIAN: duplicate}), now=NOW + 7300,
            translate=lambda stories: async_az_translation(stories))
        self.assertEqual(result, "nothing_new")
        self.assertFalse(bot.messages)

    async def test_new_story_is_persisted_with_title_and_no_replay_on_reopen(self):
        sent = []
        bot = FakeBot()
        newer = self.client_for(first=True, second=True)
        initialize = await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=self.client_for(), now=NOW,
            on_state_change=lambda: sent.append("snapshot"))
        self.assertEqual(initialize, "initialized")
        self.assertEqual(len(sent), 1)
        self.assertEqual(await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=newer, now=NOW + 7300,
            translate=lambda stories: async_az_translation(stories),
            on_state_change=lambda: sent.append("published")), "sent")
        self.assertEqual(sent, ["snapshot", "published"])
        stored = json.loads(Path(self.path).read_text(encoding="utf-8"))
        self.assertEqual(len(stored["seen_ids"]), 2)
        self.assertEqual(len(stored["seen_titles"]), 2)
        self.assertEqual(await news.publish_world_news(
            bot=bot, group_id="-10012345", state_file=self.path,
            client=newer, now=NOW + 8000,
            translate=lambda stories: async_az_translation(stories)), "nothing_new")
        self.assertEqual(len(bot.messages), 1)

    async def test_bad_free_translation_is_skipped(self):
        story = {"id": "x", "title": "Scientists create a new space robot",
                 "description": "New technology research"}
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            for output in ("Scientists create a new space robot",
                           "Yeni robot https://evil.example saytında göstərilib.",
                           "Bu məlumat bbc.com saytında təqdim olunub.",
                           "Alimlər 400 yeni robot yaradıb!"):
                result = await news.translate_headlines(
                    [story], fallback_client=FakeMemoryClient(output))
                self.assertFalse(result)


async def async_unavailable_translation():
    return {}

async def async_az_translation(stories):
    return {story["id"]:
            "Alimlər sualtı robot hazırlayıblar və yeni tədqiqatlara başlayıblar."
            for story in stories}


if __name__ == "__main__":
    unittest.main()
