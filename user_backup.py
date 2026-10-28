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
    def __init__(self, users_file, stats_file, activity_file=None, news_file=None,
                 referral_file=None, extra_files=None):
        self.files = {"users": Path(users_file), "stats": Path(stats_file)}
        self.activity_file = Path(activity_file) if activity_file else None
        self.news_file = Path(news_file) if news_file else None
        self.referral_file = Path(referral_file) if referral_file else None
        # Explicit allow-list of non-OTP runtime data; never back up provider
        # credentials, raw SMS messages, OTP codes, or session cookies.
        self.extra_files = {
            str(key): Path(path) for key, path in (extra_files or {}).items()
            if key in self._ALLOWED_EXTRAS
        }
        self.status = "İstifadəçi bazasının yedəklənməsi başlayır."
        self.ready = False
        self._lock = asyncio.Lock()
        self._changed = asyncio.Event()

    _ALLOWED_EXTRAS = frozenset((
        "system_config", "number_prices", "user_otp_rates",
        "required_channels", "az_range_permissions", "banned_users",
        "withdraw_requests", "datarange", "fake_otp_config",
        "world_news_settings", "ai_post_settings", "active_leases",
    ))
    _LIST_EXTRAS = frozenset(("required_channels", "banned_users"))
    _MAX_EXTRA_BYTES = 12_000_000

    def _extra_value(self, key, value):
        expected = list if key in self._LIST_EXTRAS else dict
        if not isinstance(value, expected):
            raise ValueError("Invalid private settings backup format")
        # Bound and validate JSON before persisting to a private repo.
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if len(raw.encode("utf-8")) > self._MAX_EXTRA_BYTES:
            raise ValueError("Private settings record exceeds safe backup size")
        return value

    def _read_extras(self):
        result = {}
        for key, path in self.extra_files.items():
            if path.exists():
                try:
                    content = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError) as exc:
                    raise RuntimeError("Local private settings cannot be read safely") from exc
                result[key] = self._extra_value(key, content)
        return result

    def changed(self):
        """Wake the background sync after an account or usage update."""
        self._changed.set()

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

    def _read_activity(self):
        if self.activity_file is None or not self.activity_file.exists():
            return []
        try:
            entries = json.loads(self.activity_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise RuntimeError("History cannot be read safely")
        if not isinstance(entries, list):
            raise ValueError("Invalid local history")
        return self._sanitize_activity(entries)

    @staticmethod
    def _sanitize_activity(entries):
        # Archive metadata only; never save OTP codes, numbers or SMS bodies.
        if not isinstance(entries, list):
            return []
        result = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            uid = str(item.get("uid", ""))
            action = str(item.get("action", ""))[:64]
            timestamp = str(item.get("timestamp", ""))[:50]
            if (uid.isdecimal() or uid == "SYSTEM") and action and timestamp:
                result.append({"uid": uid, "action": action, "timestamp": timestamp})
        return result

    @staticmethod
    def _sanitize_news(value):
        """Only private, non-sensitive RSS fingerprints and normalized titles."""
        if not isinstance(value, dict):
            return {}
        seen_ids = value.get("seen_ids", [])
        seen_titles = value.get("seen_titles", [])
        if not isinstance(seen_ids, list):
            seen_ids = []
        if not isinstance(seen_titles, list):
            seen_titles = []
        ids = [x for x in seen_ids if isinstance(x, str)
               and re.fullmatch(r"[0-9a-f]{64}", x)]
        titles = [x for x in seen_titles if isinstance(x, str)
                  and 5 <= len(x) <= 180 and not re.search(r"[\x00-\x1f]", x)]
        sent = value.get("last_sent", 0)
        if type(sent) not in (int, float) or not 0 <= sent <= 1e12:
            sent = 0
        return {
            "initialized": bool(value.get("initialized") or ids or titles),
            "last_sent": sent,
            "seen_ids": list(dict.fromkeys(ids))[-3000:],
            "seen_titles": list(dict.fromkeys(titles))[-3000:],
        }

    def _read_news(self):
        if self.news_file is None or not self.news_file.exists():
            return {}
        return self._sanitize_news(self._read(self.news_file))

    @staticmethod
    def _sanitize_referral_settings(value):
        if not isinstance(value, dict) or type(value.get("enabled")) is not bool:
            return {}
        timestamp = value.get("updated_at", 0)
        if type(timestamp) not in (int, float) or not 0 <= timestamp <= 1e12:
            timestamp = 0
        return {"enabled": value["enabled"], "required": 5,
                "updated_at": float(timestamp)}

    def _read_referral_settings(self):
        if self.referral_file is None or not self.referral_file.exists():
            return {}
        return self._sanitize_referral_settings(self._read(self.referral_file))

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
        if self.activity_file is not None:
            recovered = self._sanitize_activity(remote.get("activity", []))
            current = self._read_activity()
            combined = {(v["uid"], v["action"], v["timestamp"]): v for v in recovered}
            for entry in current:
                combined[(entry["uid"], entry["action"], entry["timestamp"])] = entry
            restored = sorted(combined.values(), key=lambda v: v["timestamp"])
            if restored != current:
                self.activity_file.parent.mkdir(parents=True, exist_ok=True)
                atomic_save(restored, self.activity_file)
        if self.news_file is not None:
            recovered = self._sanitize_news(remote.get("news", {}))
            current = self._read_news()
            if current or recovered:
                # A server redeploy must not discard previously published RSS
                # IDs/titles. Merge both sides, keeping the longer remembered
                # history and most recent sent time.
                merged = {
                    "initialized": bool(current.get("initialized") or
                                        recovered.get("initialized")),
                    "last_sent": max(current.get("last_sent", 0),
                                     recovered.get("last_sent", 0)),
                    "seen_ids": list(dict.fromkeys(
                        recovered.get("seen_ids", []) +
                        current.get("seen_ids", [])))[-3000:],
                    "seen_titles": list(dict.fromkeys(
                        recovered.get("seen_titles", []) +
                        current.get("seen_titles", [])))[-3000:],
                }
                if merged != current:
                    self.news_file.parent.mkdir(parents=True, exist_ok=True)
                    atomic_save(merged, self.news_file)

        if self.referral_file is not None:
            remote_config = self._sanitize_referral_settings(remote.get("whatsapp_referrals"))
            local_config = self._read_referral_settings()
            if remote_config and (not local_config or
                                  remote_config.get("updated_at", 0) > local_config.get("updated_at", 0)):
                self.referral_file.parent.mkdir(parents=True, exist_ok=True)
                atomic_save(remote_config, self.referral_file)

        if self.extra_files:
            remote_settings = remote.get("settings", {})
            if not isinstance(remote_settings, dict):
                raise ValueError("Invalid private settings snapshot")
            for key, path in self.extra_files.items():
                if key not in remote_settings:
                    continue
                restored = self._extra_value(key, remote_settings[key])
                local = self._read_extras().get(key)
                if local != restored:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    atomic_save(restored, path)

    def _snapshot(self):
        snapshot = {
            "version": 1,
            "users": self._validate("users", self._read(self.files["users"])),
            "stats": self._validate("stats", self._read(self.files["stats"])),
            "activity": self._read_activity(),
        }
        if self.news_file is not None:
            snapshot["news"] = self._read_news()
        if self.referral_file is not None:
            snapshot["whatsapp_referrals"] = self._read_referral_settings()
        if self.extra_files:
            snapshot["settings"] = self._read_extras()
        return snapshot

    async def _remote(self, client):
        token = os.environ.get("NUMBER_ARCHIVE_GITHUB_TOKEN", "").strip()
        repo = os.environ.get("NUMBER_ARCHIVE_GITHUB_REPO", "").strip()
        branch = os.environ.get("NUMBER_ARCHIVE_GITHUB_BRANCH", "").strip()
        path = os.environ.get("USER_BACKUP_GITHUB_PATH", "user_profiles.json").strip()
        if not token or not repo:
            raise RuntimeError("Private archive token or repository missing")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("Invalid private archive repository")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\.json", path):
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
                try:
                    await asyncio.wait_for(self._changed.wait(), timeout=interval)
                    self._changed.clear()
                    # Batch related writes from the same Telegram operation.
                    await asyncio.sleep(2)
                except asyncio.TimeoutError:
                    pass
