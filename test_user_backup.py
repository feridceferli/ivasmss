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

    async def test_news_history_roundtrip_survives_render_restart(self):
        users = self.folder / "users.json"
        stats = self.folder / "user_stats.json"
        news = self.folder / "world_news_digest_state.json"
        state = {
            "initialized": True, "last_sent": 100000.0,
            "seen_ids": ["a" * 64, "b" * 64],
            "seen_titles": [
                "alimlər kosmik robot təqdim ediblər",
                "yeni kosmik muzey sərgisi açılıb",
            ],
        }
        news.write_text(json.dumps(state), encoding="utf-8")
        previous = UserProfileBackup(users, stats, news_file=news)
        await previous.restore(self.gh)
        await previous.sync_once(self.gh)
        stored = json.loads(self.gh.stored.decode("utf-8"))
        self.assertEqual(stored["news"], state)
        news.unlink()
        recovered = UserProfileBackup(users, stats, news_file=news)
        await recovered.restore(self.gh)
        self.assertEqual(json.loads(news.read_text(encoding="utf-8")), state)

    async def test_news_archive_merges_history_instead_of_replacing(self):
        news = self.folder / "world_news_digest_state.json"
        news.write_text(json.dumps({
            "initialized": True, "last_sent": 200,
            "seen_ids": ["b" * 64],
            "seen_titles": ["ikinci xəbər başlığı"],
        }), encoding="utf-8")
        self.gh.stored = json.dumps({
            "version": 1, "users": {}, "stats": {},
            "news": {
                "initialized": True, "last_sent": 100,
                "seen_ids": ["a" * 64],
                "seen_titles": ["birinci xəbər başlığı"],
            },
        }).encode("utf-8")
        backup = UserProfileBackup(
            self.folder / "users.json", self.folder / "stats.json",
            news_file=news,
        )
        await backup.restore(self.gh)
        data = json.loads(news.read_text(encoding="utf-8"))
        self.assertEqual(data["last_sent"], 200)
        self.assertEqual(data["seen_ids"], ["a" * 64, "b" * 64])
        self.assertEqual(data["seen_titles"], [
            "birinci xəbər başlığı", "ikinci xəbər başlığı"])
        await backup.sync_once(self.gh)
        remote = json.loads(self.gh.stored.decode("utf-8"))
        self.assertEqual(remote["news"]["seen_ids"], data["seen_ids"])

    async def test_whatsapp_referral_setting_survives_redeploy(self):
        users = self.folder / "users.json"
        stats = self.folder / "stats.json"
        config = self.folder / "whatsapp_referral_settings.json"
        config.write_text(json.dumps({
            "enabled": False, "required": 5, "updated_at": 10000.0,
        }), encoding="utf-8")
        first = UserProfileBackup(users, stats, referral_file=config)
        await first.restore(self.gh)
        await first.sync_once(self.gh)
        saved = json.loads(self.gh.stored.decode("utf-8"))
        self.assertFalse(saved["whatsapp_referrals"]["enabled"])
        config.unlink()
        newer = UserProfileBackup(users, stats, referral_file=config)
        await newer.restore(self.gh)
        self.assertFalse(json.loads(config.read_text())["enabled"])

    async def test_newer_admin_referral_setting_is_not_overwritten(self):
        config = self.folder / "whatsapp_referral_settings.json"
        config.write_text(json.dumps({
            "enabled": True, "required": 5, "updated_at": 20000.0,
        }), encoding="utf-8")
        self.gh.stored = json.dumps({
            "version": 1, "users": {}, "stats": {}, "whatsapp_referrals": {
                "enabled": False, "required": 5, "updated_at": 10000.0,
            },
        }).encode("utf-8")
        instance = UserProfileBackup(
            self.folder / "users.json", self.folder / "stats.json",
            referral_file=config,
        )
        await instance.restore(self.gh)
        self.assertTrue(json.loads(config.read_text())["enabled"])

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
