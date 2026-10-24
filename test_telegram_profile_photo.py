"""Offline Telegram profile-photo ownership, fallback and privacy regression tests.

Extract only the handlers from main.py via AST: no Telegram or live HTTP/API
tokens are needed. All profile photos and users below are synthetic.
"""
import ast
import asyncio
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

SRC = Path("main.py").read_text(encoding="utf-8")
TREE = ast.parse(SRC)


class TelegramError(Exception):
    pass


def isolated(name, context):
    nodes = [item for item in TREE.body
             if isinstance(item, (ast.AsyncFunctionDef, ast.FunctionDef))
             and item.name == name]
    if len(nodes) != 1:
        raise AssertionError("Expected exactly one function: " + name)
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    exec(compile(module, "main.py", "exec"), context)
    return context[name]


class Response:
    def __init__(self, body=None, status=200, content_type=None, headers=None):
        self.body = body
        self.status = status
        self.content_type = content_type
        self.headers = dict(headers or {})
        self.json = None


class Web:
    Response = Response

    @staticmethod
    def json_response(payload, status=200):
        response = Response(status=status)
        response.json = payload
        return response


class File:
    file_size = 4

    async def download_as_bytearray(self):
        return bytearray(b"\xff\xd8\xff\xd9")


class Photos:
    def __init__(self, available=True):
        self.photos = [[SimpleNamespace(file_id="fake-file-id")]] if available else []


class Bot:
    def __init__(self, has_photo=True, fail=False):
        self.requested_uids = []
        self.requested_files = []
        self.has_photo = has_photo
        self.fail = fail

    async def get_user_profile_photos(self, user_id, limit=1):
        self.requested_uids.append(user_id)
        if self.fail:
            raise TelegramError("test failure")
        return Photos(available=self.has_photo)

    async def get_file(self, file_id):
        self.requested_files.append(file_id)
        return File()


class Message:
    def __init__(self):
        self.photos = []
        self.messages = []

    async def reply_photo(self, **kwargs):
        self.photos.append(kwargs)

    async def reply_text(self, *args, **kwargs):
        self.messages.append((args, kwargs))


class TelegramPhotoTests(unittest.IsolatedAsyncioTestCase):
    def test_api_context(self, authed=True, banned=False):
        return {
            "web": Web,
            "_miniapp_auth": lambda request: (
                ({"id": 880011} if authed else None),
                (None if authed else "bad_hash"),
            ),
            "_miniapp_cors": lambda response: response,
            "is_user_banned": lambda uid: banned,
            "TelegramError": TelegramError,
        }

    async def test_photo_url_is_owner_scoped_and_private(self):
        context = self.test_api_context()
        endpoint = isolated("miniapp_avatar_api", context)
        bot = Bot()
        request = SimpleNamespace(
            method="GET",
            headers={"X-Telegram-Init-Data": "authenticated-test-data"},
            app={"telegram_bot": bot},
        )
        response = await endpoint(request)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, b"\xff\xd8\xff\xd9")
        self.assertEqual(response.content_type, "image/jpeg")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(bot.requested_uids, [880011])
        self.assertEqual(bot.requested_files, ["fake-file-id"])
        self.assertNotIn("file_id", repr(response.__dict__))
        self.assertNotIn("bot_token", repr(response.__dict__))

    async def test_rejects_unauthenticated_or_banned_user(self):
        for authed, banned, expected in [(False, False, 401), (True, True, 403)]:
            endpoint = isolated("miniapp_avatar_api",
                                self.test_api_context(authed=authed, banned=banned))
            bot = Bot()
            response = await endpoint(SimpleNamespace(
                method="GET", headers={}, app={"telegram_bot": bot}
            ))
            self.assertEqual(response.status, expected)
            self.assertEqual(bot.requested_uids, [], "No API call for unauthorized users")

    async def test_missing_photo_is_not_server_failure(self):
        endpoint = isolated("miniapp_avatar_api", self.test_api_context())
        response = await endpoint(SimpleNamespace(
            method="GET", headers={}, app={"telegram_bot": Bot(has_photo=False)}
        ))
        self.assertEqual(response.status, 404)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    async def test_telegram_exception_has_safe_fallback(self):
        endpoint = isolated("miniapp_avatar_api", self.test_api_context())
        response = await endpoint(SimpleNamespace(
            method="GET", headers={}, app={"telegram_bot": Bot(fail=True)}
        ))
        self.assertEqual(response.status, 502)

    async def test_bot_profile_uses_current_photo_only_in_private_chat(self):
        context = {"TelegramError": TelegramError}
        reply = isolated("reply_with_telegram_profile_photo", context)
        bot = Bot()
        msg = Message()
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=880011),
            effective_chat=SimpleNamespace(type="private"),
            effective_message=msg,
        )
        sent = await reply(update, SimpleNamespace(bot=bot), "Test profile")
        self.assertTrue(sent)
        self.assertEqual(bot.requested_uids, [880011])
        self.assertEqual(msg.photos[0]["photo"], "fake-file-id")
        self.assertEqual(msg.photos[0]["caption"], "Test profile")
        self.assertFalse(msg.messages)

        group = SimpleNamespace(
            effective_user=SimpleNamespace(id=880011),
            effective_chat=SimpleNamespace(type="group"),
            effective_message=Message(),
        )
        await reply(group, SimpleNamespace(bot=bot), "Group profile")
        self.assertFalse(group.effective_message.photos)
        self.assertEqual(group.effective_message.messages[0][0][0], "Group profile")
        self.assertEqual(bot.requested_uids, [880011])

    async def test_bot_profile_falls_back_for_users_without_photos(self):
        context = {"TelegramError": TelegramError}
        reply = isolated("reply_with_telegram_profile_photo", context)
        msg = Message()
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=880011),
            effective_chat=SimpleNamespace(type="private"),
            effective_message=msg,
        )
        sent = await reply(update, SimpleNamespace(bot=Bot(has_photo=False)),
                           "Text-only profile")
        self.assertFalse(sent)
        self.assertEqual(msg.messages[0][0][0], "Text-only profile")
        self.assertFalse(msg.photos)

    def test_photo_handlers_are_wired_and_no_bot_token_in_client(self):
        js = Path("docs/app.js").read_text(encoding="utf-8")
        html = Path("docs/index.html").read_text(encoding="utf-8")
        self.assertIn('server.router.add_route("*", "/api/avatar", miniapp_avatar_api)', SRC)
        self.assertIn("get_user_profile_photos", SRC)
        self.assertIn("download_as_bytearray()", SRC)
        self.assertIn('"/api/avatar"', js)
        self.assertIn('X-Telegram-Init-Data', js)
        self.assertIn('id="user-avatar"', html)
        self.assertIn('id="profile-avatar"', html)
        self.assertNotIn("api.telegram.org/file/bot", js)
        self.assertNotIn(".innerHTML", js)


if __name__ == "__main__":
    unittest.main()
