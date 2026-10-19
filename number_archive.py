"""Number-only archive, scoped TXT downloads and private GitHub backup."""
import asyncio
import base64
import logging
import os
import re
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

import httpx

log = logging.getLogger(__name__)


def normalize_phone(value):
    # Accept phone formatting only, never arbitrary API/SMS content.
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not re.fullmatch(r"\+?[0-9 ()-]+", text):
        return None
    digits = re.sub(r"[^0-9]", "", text)
    return "+" + digits if 7 <= len(digits) <= 15 else None


class NumberArchive:
    def __init__(self, folder):
        self.folder = Path(folder).expanduser().resolve()
        self.folder.mkdir(parents=True, exist_ok=True)
        self.path = self.folder / "number_archive.sqlite3"
        self.status = "GitHub sinxronizasiyası hələ başlamayıb."
        self._sync_lock = asyncio.Lock()
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS numbers (number TEXT PRIMARY KEY)")
            db.execute("""CREATE TABLE IF NOT EXISTS allocations (
                user_id TEXT NOT NULL, number TEXT NOT NULL,
                PRIMARY KEY (user_id, number))""")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def record(self, value, user_id=None):
        number = normalize_phone(value)
        if number is None:
            return False
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO numbers VALUES (?)", (number,))
            if user_id is not None:
                db.execute("INSERT OR IGNORE INTO allocations VALUES (?, ?)",
                           (str(user_id), number))
        return True

    def import_legacy(self, records):
        with self._connect() as db:
            for key, record in records.items():
                if not isinstance(record, dict):
                    continue
                number = normalize_phone(record.get("number") or key)
                if not number:
                    continue
                db.execute("INSERT OR IGNORE INTO numbers VALUES (?)", (number,))
                if record.get("user_id") is not None:
                    db.execute("INSERT OR IGNORE INTO allocations VALUES (?, ?)",
                               (str(record["user_id"]), number))

    def text(self, user_id=None):
        with self._connect() as db:
            if user_id is None:
                rows = db.execute("SELECT number FROM numbers ORDER BY number")
            else:
                rows = db.execute("SELECT number FROM allocations WHERE user_id=? ORDER BY number",
                                  (str(user_id),))
            return "".join(number + "\n" for (number,) in rows)

    def merge_remote(self, text):
        numbers = []
        for line in text.splitlines():
            if not line.strip():
                continue
            number = normalize_phone(line)
            if number is None:
                raise ValueError("Remote archive is not a number-only TXT file")
            numbers.append((number,))
        with self._connect() as db:
            db.executemany("INSERT OR IGNORE INTO numbers VALUES (?)", numbers)
        # Remote TXT does not prove who owns a number: never restore user allocations from it.

    def write_snapshot(self):
        text = self.text()
        target = self.folder / "numbers.txt"
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.folder,
                                             prefix="numbers-", suffix=".tmp", delete=False) as f:
                temporary = f.name
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, target)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        return text

    async def sync_once(self, client, repository, branch, path="numbers.txt"):
        async with self._sync_lock:
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
                raise ValueError("NUMBER_ARCHIVE_GITHUB_REPO must be owner/repository")
            if not path.endswith(".txt") or any(p in ("", ".", "..") for p in path.split("/")):
                raise ValueError("Invalid archive TXT path")
            root = "https://api.github.com/repos/" + repository
            repo = await client.get(root)
            repo.raise_for_status()
            metadata = repo.json()
            if metadata.get("private") is not True:
                raise ValueError("Number archive destination must be a private repository")
            branch = branch or metadata["default_branch"]
            url = root + "/contents/" + quote(path, safe="/")
            for _ in range(3):
                response = await client.get(url, params={"ref": branch})
                sha = None
                remote = ""
                if response.status_code != 404:
                    response.raise_for_status()
                    entry = response.json()
                    if not isinstance(entry, dict) or entry.get("type") != "file":
                        raise ValueError("Archive destination is not a regular file")
                    sha = entry["sha"]
                    if entry.get("size", 0) > 40_000_000:
                        raise ValueError("Archive exceeds 40 MB; storage migration required")
                    if entry.get("encoding") != "base64":
                        blob = await client.get(root + "/git/blobs/" + quote(sha, safe=""))
                        blob.raise_for_status()
                        entry = blob.json()
                    if entry.get("encoding") != "base64":
                        raise ValueError("Unsupported GitHub content encoding")
                    remote = base64.b64decode(entry["content"]).decode("utf-8")
                    await asyncio.to_thread(self.merge_remote, remote)
                text = await asyncio.to_thread(self.write_snapshot)
                if text == remote:
                    self.status = "GitHub arxivi yenidir."
                    return
                content = text.encode("utf-8")
                if len(content) > 40_000_000:
                    raise ValueError("Archive exceeds 40 MB; storage migration required")
                payload = {"message": "Update number archive [skip ci]", "branch": branch,
                           "content": base64.b64encode(content).decode("ascii")}
                if sha:
                    payload["sha"] = sha
                result = await client.put(url, json=payload)
                if result.status_code in (409, 422):
                    # Refetch and merge so another writer's additions are retained.
                    continue
                result.raise_for_status()
                self.status = "GitHub arxivi yeniləndi."
                return
            raise RuntimeError("GitHub archive conflict; will retry next cycle")

    async def run(self):
        token = os.environ.get("NUMBER_ARCHIVE_GITHUB_TOKEN", "").strip()
        repository = os.environ.get("NUMBER_ARCHIVE_GITHUB_REPO", "").strip()
        branch = os.environ.get("NUMBER_ARCHIVE_GITHUB_BRANCH", "").strip()
        path = os.environ.get("NUMBER_ARCHIVE_GITHUB_PATH", "numbers.txt").strip()
        try:
            interval = max(30, int(os.environ.get("NUMBER_ARCHIVE_SYNC_SECONDS", "60")))
        except ValueError:
            interval = 60
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10"}
        if token:
            headers["Authorization"] = "Bearer " + token
        # Separate client: never send the number-provider API key to GitHub.
        async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=False) as client:
            while True:
                try:
                    await asyncio.to_thread(self.write_snapshot)
                    if token and repository:
                        await self.sync_once(client, repository, branch, path)
                    else:
                        self.status = "Yerli TXT hazırdır; GitHub repo/token konfiqurasiyası yoxdur."
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    # Do not log tokens, phone numbers, URLs or upstream response bodies.
                    code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else type(exc).__name__
                    self.status = f"GitHub sinxronizasiya xətası ({code}); yenidən sınanacaq."
                    log.warning("Number archive sync failed (%s); will retry", code)
                await asyncio.sleep(interval)


def txt_chunks(text, limit=2_000_000):
    """Keep Telegram documents small without splitting a phone number."""
    chunk = bytearray()
    for line in text.splitlines(keepends=True):
        data = line.encode("utf-8")
        if chunk and len(chunk) + len(data) > limit:
            yield bytes(chunk)
            chunk.clear()
        chunk.extend(data)
    if chunk:
        yield bytes(chunk)
