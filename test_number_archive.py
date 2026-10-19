import ast
import asyncio
import base64
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx

from number_archive import NumberArchive, normalize_phone, txt_chunks


class ArchiveTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.archive = NumberArchive(self.directory.name)

    def test_deduplication_persistence_and_user_scope(self):
        self.archive.record("+1 (202) 555-0101", 1)
        self.archive.record("12025550101", 1)
        self.archive.record("+12025550102", 2)
        self.archive.record("+12025550103")
        self.assertFalse(self.archive.record("OTP: 123456"))
        self.archive = NumberArchive(self.directory.name)
        self.assertEqual(self.archive.text(1), "+12025550101\n")
        self.assertEqual(self.archive.text(2), "+12025550102\n")
        self.assertEqual(self.archive.text(3), "")
        self.assertEqual(len(self.archive.text().splitlines()), 3)
        self.archive.write_snapshot()
        self.assertEqual((Path(self.directory.name) / "numbers.txt").read_text(), self.archive.text())

    def test_legacy_import_and_remote_restore_do_not_invent_ownership(self):
        self.archive.import_legacy({"a": {"number": "+12025550101", "user_id": "1"}, "bad": None})
        self.archive.merge_remote("+12025550102\n")
        self.assertEqual(self.archive.text(1), "+12025550101\n")
        self.assertEqual(self.archive.text(), "+12025550101\n+12025550102\n")
        with self.assertRaises(ValueError):
            self.archive.merge_remote("+12025550103\nnot a number\n")
        self.assertNotIn("+12025550103", self.archive.text())

    def test_validation_and_chunking(self):
        for value in (None, True, {}, "code=1234567", "123456", "1" * 16, "１２３４５６７"):
            self.assertIsNone(normalize_phone(value))
        text = "+12025550101\n+12025550102\n+12025550103\n"
        chunks = list(txt_chunks(text, limit=26))
        self.assertEqual(b"".join(chunks), text.encode())
        self.assertTrue(all(len(chunk) <= 26 and chunk.endswith(b"\n") for chunk in chunks))

    async def test_private_repository_check_prevents_public_upload(self):
        calls = []
        def respond(request):
            calls.append(request)
            return httpx.Response(200, json={"private": False, "default_branch": "main"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with self.assertRaises(ValueError):
                await self.archive.sync_once(client, "owner/archive", "")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].method, "GET")

    async def test_create_then_unchanged_snapshot_has_no_extra_commit(self):
        self.archive.record("+12025550101")
        state = {"text": None, "puts": 0}
        def respond(request):
            if request.url.path == "/repos/owner/archive":
                return httpx.Response(200, json={"private": True, "default_branch": "backup"})
            if request.method == "GET":
                self.assertEqual(request.url.params["ref"], "backup")
                if state["text"] is None:
                    return httpx.Response(404)
                return httpx.Response(200, json={"type": "file", "sha": "new-sha", "encoding": "base64",
                    "content": base64.b64encode(state["text"].encode()).decode()})
            body = json.loads(request.content)
            self.assertEqual(body["branch"], "backup")
            self.assertNotIn("sha", body)
            state["text"] = base64.b64decode(body["content"]).decode()
            state["puts"] += 1
            return httpx.Response(201, json={})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            await self.archive.sync_once(client, "owner/archive", "")
            await self.archive.sync_once(client, "owner/archive", "")
        self.assertEqual(state["puts"], 1)
        self.assertEqual(state["text"], "+12025550101\n")

    async def test_conflict_merges_remote_and_concurrent_local_additions(self):
        self.archive.record("+12025550101", 1)
        state = {"text": "+12025550102\n", "sha": "old", "puts": 0}
        def respond(request):
            if request.url.path == "/repos/owner/archive":
                return httpx.Response(200, json={"private": True, "default_branch": "main"})
            if request.method == "GET":
                return httpx.Response(200, json={"type": "file", "sha": state["sha"], "encoding": "base64",
                    "content": base64.b64encode(state["text"].encode()).decode()})
            body = json.loads(request.content)
            self.assertEqual(body["sha"], state["sha"])
            state["puts"] += 1
            if state["puts"] == 1:
                state["text"] += "+12025550103\n"
                state["sha"] = "updated"
                self.archive.record("+12025550104", 2)
                return httpx.Response(409)
            state["text"] = base64.b64decode(body["content"]).decode()
            return httpx.Response(200, json={})
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            await self.archive.sync_once(client, "owner/archive", "main")
        self.assertEqual(state["puts"], 2)
        self.assertEqual(len(state["text"].splitlines()), 4)
        self.assertEqual(self.archive.text(1), "+12025550101\n")
        self.assertEqual(self.archive.text(2), "+12025550104\n")

    async def test_failed_upload_keeps_local_numbers_for_retry(self):
        self.archive.record("+12025550101")
        def respond(request):
            if request.url.path == "/repos/owner/archive":
                return httpx.Response(200, json={"private": True, "default_branch": "main"})
            return httpx.Response(404 if request.method == "GET" else 503)
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with self.assertRaises(httpx.HTTPStatusError):
                await self.archive.sync_once(client, "owner/archive", "")
        self.assertEqual(NumberArchive(self.directory.name).text(), "+12025550101\n")


class DownloadAccessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        archive = NumberArchive(self.directory.name)
        archive.record("+12025550101", 1)
        archive.record("+12025550102", 2)
        # Load the actual handler without starting the bot or requiring production secrets.
        tree = ast.parse(Path(__file__).with_name("main.py").read_text())
        handler = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
                       and node.name == "download_numbers_txt")
        self.scope = {"asyncio": asyncio, "io": io, "txt_chunks": txt_chunks,
                      "number_archive": archive, "is_admin": lambda uid: uid == 99,
                      "is_user_banned": lambda uid: uid == 3,
                      "load_required_channels": lambda: [], "check_user_joined": AsyncMock(return_value=(True, None))}
        exec(compile(ast.Module(body=[handler], type_ignores=[]), "main.py", "exec"), self.scope)

    async def download(self, uid, all_numbers=False, chat_type="private"):
        message = SimpleNamespace(reply_document=AsyncMock(), reply_text=AsyncMock())
        update = SimpleNamespace(effective_user=SimpleNamespace(id=uid), effective_message=message,
                                 effective_chat=SimpleNamespace(type=chat_type))
        await self.scope["download_numbers_txt"](update, SimpleNamespace(bot=None), all_numbers)
        return message

    async def test_user_only_downloads_own_numbers(self):
        message = await self.download(1)
        self.assertEqual(message.reply_document.await_args.kwargs["document"].getvalue(), b"+12025550101\n")

    async def test_admin_can_download_all(self):
        message = await self.download(99, True)
        self.assertEqual(message.reply_document.await_args.kwargs["document"].getvalue(), b"+12025550101\n+12025550102\n")

    async def test_non_admin_banned_and_group_requests_do_not_download(self):
        for uid, all_numbers, chat_type in [(1, True, "private"), (3, False, "private"), (99, True, "group")]:
            message = await self.download(uid, all_numbers, chat_type)
            message.reply_document.assert_not_awaited()

    async def test_membership_required(self):
        self.scope["load_required_channels"] = lambda: [{"chat_id": "channel"}]
        self.scope["check_user_joined"] = AsyncMock(return_value=(False, None))
        message = await self.download(1)
        message.reply_document.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
