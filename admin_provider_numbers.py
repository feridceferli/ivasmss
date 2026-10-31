"""Administrator-only phone inventory for owned Green SMS/Ivasmsper lines.

Source repositories implement SMS forwarding, not a purchasable number API.
Only explicitly imported, operator-authorized numbers are advertised here.
No OTP/SMS text or provider credentials are stored.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from data_storage import atomic_save, data_path

PROVIDERS = ("green_sms", "ivasmsper")
MAX_IMPORT = 200
MAX_STOCK_PER_PROVIDER = 4000
MAX_DISPLAY = 300


class NumberStockError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def normalize_number(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"[\s().-]", "", value.strip())
    if not re.fullmatch(r"\+?[1-9][0-9]{6,14}", cleaned):
        return None
    return "+" + cleaned.lstrip("+")


def parse_number_lines(text: str) -> list[str]:
    if not isinstance(text, str) or len(text) > 12000:
        raise NumberStockError("invalid_import")
    lines = [item.strip() for item in text.replace(",", "\n").splitlines()
             if item.strip() and not item.lstrip().startswith("#")]
    if not 1 <= len(lines) <= MAX_IMPORT:
        raise NumberStockError("invalid_count")
    valid = []
    for value in lines:
        item = normalize_number(value)
        if not item:
            raise NumberStockError("invalid_number")
        if item not in valid:
            valid.append(item)
    return valid


class AdminNumberStock:
    def __init__(self, filename=None):
        self.filename = Path(filename or data_path("admin_provider_numbers.json"))
        self._lock = asyncio.Lock()

    def _read(self) -> dict[str, list[dict]]:
        try:
            payload = json.loads(self.filename.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {key: [] for key in PROVIDERS}
        except (OSError, ValueError) as exc:
            raise NumberStockError("inventory_unavailable") from exc
        if not isinstance(payload, dict):
            raise NumberStockError("inventory_unavailable")
        result = {}
        for key in PROVIDERS:
            items = payload.get(key, [])
            if not isinstance(items, list) or len(items) > MAX_STOCK_PER_PROVIDER:
                raise NumberStockError("inventory_unavailable")
            result[key] = []
            for obj in items:
                if not isinstance(obj, dict) or normalize_number(obj.get("number")) != obj.get("number"):
                    raise NumberStockError("inventory_unavailable")
                result[key].append({
                    "number": obj["number"], "added_at": str(obj.get("added_at", ""))[:32]
                })
        return result

    def _write(self, state):
        atomic_save(state, self.filename)

    def list(self, provider: str) -> dict:
        if provider not in PROVIDERS:
            raise NumberStockError("invalid_provider")
        data = self._read()[provider]
        return {"provider": provider, "count": len(data),
                "numbers": list(reversed(data))[:MAX_DISPLAY],
                "source": "admin_import",
                "note": "Yalnız administrator tərəfindən əlavə edilmiş nömrələr"}

    async def import_text(self, provider: str, text: str) -> dict:
        if provider not in PROVIDERS:
            raise NumberStockError("invalid_provider")
        numbers = parse_number_lines(text)
        async with self._lock:
            state = self._read()
            existing = {item["number"] for item in state[provider]}
            new = [n for n in numbers if n not in existing]
            if len(state[provider]) + len(new) > MAX_STOCK_PER_PROVIDER:
                raise NumberStockError("stock_limit")
            now = datetime.now(timezone.utc).isoformat()
            state[provider].extend({"number": item, "added_at": now} for item in new)
            if new:
                self._write(state)
            return {"added": len(new), **self.list(provider)}

    async def delete(self, provider: str, value: str) -> dict:
        if provider not in PROVIDERS:
            raise NumberStockError("invalid_provider")
        number = normalize_number(value)
        if not number:
            raise NumberStockError("invalid_number")
        async with self._lock:
            state = self._read()
            before = len(state[provider])
            state[provider] = [item for item in state[provider] if item["number"] != number]
            if len(state[provider]) == before:
                raise NumberStockError("number_not_found")
            self._write(state)
            return {"removed": 1, **self.list(provider)}
