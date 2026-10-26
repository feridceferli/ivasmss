"""Private GitHub backup for bot user accounts and usage statistics.

Never commit these files to the public source repository. A backup is read
before the first write, so an empty Render filesystem cannot erase a remote
snapshot during deployment.
"""
import asyncio
import base64
import json
import logging
import os
import re
from pathlib import Path
from urllib.parse import quote

import httpx

from data_storage import atomic_save

log = logging.getLogger(__name__)


class UserProfileBackup:
    def __init__(self, users_file, stats_file):
        self.files = {"users": Path(users_file), "stats": Path(stats_file)}
        self.status = "İstifadəçi bazasının yedəklənməsi başlayır."
        self.ready = False
        self._lock = asyncio.Lock()

    @staticmethod
    def _read(path):
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise RuntimeError("Local user backup data cannot be read safely")
        if not isinstance(data, dict):
            raise ValueError("Invalid local user backup data")
        return data

    @staticmethod
    def _validate(kind, records):
        if not isinstance(records, dict):
            raise ValueError("Invalid private backup format")
        filtered = {}
        for uid, data in records.items():
            if not isinstance(uid, str) or not uid.isdecimal() or not isinstance(data, dict):
                continue
            if kind == "users":
                balance = data.get("balance", 0)
                if type(balance) not in (int, float) or not (0 <= float(balance) < 1e12):
                    continue
            else:
                if not isinstance(data.get("numbers_taken", []), list):
                    continue
                if not isinstance(data.get("otps_received", []), list):
                    continue
            filtered[uid] = data
        return filtered

    def _merge_restore(self, remote):
        if remote.get("version") != 1:
            raise ValueError("Unknown private backup version")
        for kind, path in self.files.items():
            original = self._read(path)
            recovered = self._validate(kind, remote.get(kind, {}))
            merged = dict(recovered)
            # Existing local records may include changes not yet synced;
            # never overwrite them with potentially stale remote values.
            merged.update(original)
            if kind == "stats":
                for uid in original.keys() & recovered.keys():
                    old = original[uid].get("numbers_taken", [])
                    prior = recovered[uid].get("numbers_taken", [])
                    if isinstance(old, list) and isinstance(prior, list) and len(prior) > len(old):
                        merged[uid] = recovered[uid]
            if merged != original:
                path.parent.mkdir(parents=True, exist_ok=True)
                atomic_save(merged, path)

    def _snapshot(self):
        return {
            "version": 1,
            "users": self._validate("users", self._read(self.files["users"])),
            "stats": self._validate("stats", self._read(self.files["stats"])),
        }

    async def _remote(self, client):
        token = os.environ.get("NUMBER_ARCHIVE_GITHUB_TOKEN", "").strip()
        repo = os.environ.get("NUMBER_ARCHIVE_GITHUB_REPO", "").strip()
        branch = os.environ.get("NUMBER_ARCHIVE_GITHUB_BRANCH", "").strip()
        path = os.environ.get("USER_BACKUP_GITHUB_PATH", "user_profiles.json").strip()
        if not token or not repo:
            raise RuntimeError("Private archive token or repository missing")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("Invalid private archive repository")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\\.json", path):
            raise ValueError("Invalid private user backup path")
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        root = "https://api.github.com/repos/" + repo
        meta = await client.get(root, headers=headers)
        meta.raise_for_status()
        if meta.json().get("private") is not True:
            raise RuntimeError("Backup repository must remain private")
        branch = branch or meta.json()["default_branch"]
        return root + "/contents/" + quote(path, safe="/"), branch, headers

    async def _read_remote(self, client, url, branch, headers):
        response = await client.get(url, params={"ref": branch}, headers=headers)
        if response.status_code == 404:
            return None, None
        response.raise_for_status()
        item = response.json()
        if item.get("type") != "file" or item.get("size", 0) > 40_000_000:
            raise ValueError("Private backup is invalid or too large")
        if item.get("encoding") != "base64":
            raise ValueError("Unsupported GitHub backup encoding")
        data = json.loads(base64.b64decode(item["content"]).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Private backup must be an object")
        return data, item["sha"]

    async def restore(self, client):
        async with self._lock:
            url, branch, headers = await self._remote(client)
            data, _ = await self._read_remote(client, url, branch, headers)
            if data is not None:
                await asyncio.to_thread(self._merge_restore, data)
            self.ready = True
            self.status = "✅ İstifadəçi məlumatları bərpa edildi." if data is not None else "✅ Yeni özəl istifadəçi arxivi hazırdır."

    async def sync_once(self, client):
        async with self._lock:
            if not self.ready:
                raise RuntimeError("Cannot upload user snapshot before restore")
            url, branch, headers = await self._remote(client)
            for _ in range(3):
                remote, sha = await self._read_remote(client, url, branch, headers)
                if remote is not None and remote.get("version") != 1:
                    raise ValueError("Incompatible private backup version")
                snapshot = await asyncio.to_thread(self._snapshot)
                if remote == snapshot:
                    self.status = "✅ İstifadəçi arxivi yenidir."
                    return
                payload = {
                    "message": "Backup private user accounts and statistics [skip ci]",
                    "branch": branch,
                    "content": base64.b64encode(json.dumps(
                        snapshot, ensure_ascii=False, separators=(",", ":")
                    ).encode("utf-8")).decode("ascii"),
                }
                if sha is not None:
                    payload["sha"] = sha
                response = await client.put(url, headers=headers, json=payload)
                if response.status_code in (409, 422):
                    continue
                response.raise_for_status()
                self.status = "✅ İstifadəçi arxivi yeniləndi."
                return
            raise RuntimeError("Private backup conflict")

    async def run(self):
        try:
            interval = max(30, int(os.getenv("NUMBER_ARCHIVE_SYNC_SECONDS", "60")))
        except ValueError:
            interval = 60
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            while True:
                try:
                    if not self.ready:
                        await self.restore(client)
                    await self.sync_once(client)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.status = "❌ İstifadəçi arxivi xətası (" + type(exc).__name__ + ")."
                    log.warning("Private user backup failed (%s)", type(exc).__name__)
                await asyncio.sleep(interval)
