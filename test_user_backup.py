"""Offline regression coverage for private user balance and purchase history backups."""
import asyncio
import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from user_backup import UserProfileBackup


class Response:
    def __init__(self, status, body):
        self.status_code, self.body = status, body

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise ValueError(f"HTTP {self.status_code}")


class FakeGitHub:
    def __init__(self):
        self.stored = None
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        if url.endswith("/contents/user_profiles.json"):
            if self.stored is None:
                return Response(404, {})
            return Response(200, {
                "type": "file", "size": len(self.stored), "sha": "test-sha",
                "encoding": "base64",
                "content": base64.b64encode(self.stored).decode("ascii")
            })
        return Response(200, {"private": True, "default_branch": "main"})

    async def put(self, url, **kwargs):
        self.calls.append(("PUT", url))
        self.stored = base64.b64decode(kwargs["json"]["content"])
        return Response(201, {})


class BackupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.gh = FakeGitHub()
        patcher = patch.dict(os.environ, {
            "NUMBER_ARCHIVE_GITHUB_TOKEN": "offline-test-only",
            "NUMBER_ARCHIVE_GITHUB_REPO": "example/private-test",
        })
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_roundtrip_restores_balance_and_purchase_history(self):
        users = self.folder / "users.json"
        stats = self.folder / "user_stats.json"
        users.write_text(json.dumps({"123": {"user_id": "123", "balance": 5.75}}))
        stats.write_text(json.dumps({"123": {"numbers_taken": ["2026-10-25T12:00:00"],
                                            "otps_received": []}}))
        first = UserProfileBackup(users, stats)
        await first.restore(self.gh)
        await first.sync_once(self.gh)
        self.assertEqual(json.loads(self.gh.stored)["users"]["123"]["balance"], 5.75)
        users.unlink()
        stats.unlink()
        next_instance = UserProfileBackup(users, stats)
        await next_instance.restore(self.gh)
        self.assertEqual(json.loads(users.read_text())["123"]["balance"], 5.75)
        self.assertEqual(len(json.loads(stats.read_text())["123"]["numbers_taken"]), 1)

    async def test_never_uploads_before_successful_restore(self):
        with patch.dict(os.environ, {"NUMBER_ARCHIVE_GITHUB_TOKEN": ""}):
            backup = UserProfileBackup(self.folder / "users.json", self.folder / "user_stats.json")
            with self.assertRaises(RuntimeError):
                await backup.restore(self.gh)
            with self.assertRaises(RuntimeError):
                await backup.sync_once(self.gh)
        self.assertFalse(any(method == "PUT" for method, _ in self.gh.calls))

    async def test_local_changes_not_replaced_by_stale_remote(self):
        self.gh.stored = json.dumps({
            "version": 1, "users": {"123": {"balance": 1.0}},
            "stats": {"123": {"numbers_taken": [], "otps_received": []}}
        }).encode()
        users = self.folder / "users.json"
        users.write_text(json.dumps({"123": {"balance": 9.0}}))
        backup = UserProfileBackup(users, self.folder / "user_stats.json")
        await backup.restore(self.gh)
        self.assertEqual(json.loads(users.read_text())["123"]["balance"], 9.0)


if __name__ == "__main__":
    unittest.main()
