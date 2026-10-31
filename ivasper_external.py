"""Standalone read-only IVASPER inventory adapter.

Only a separately configured, authorized HTTPS JSON inventory feed is used.
This module never imports or mutates IVASMS provider state, numbers, balances,
orders, price catalogue, OTP data or GitHub archives.
"""
import ipaddress
import json
import os
import re
from urllib.parse import urlsplit

import httpx


class IvasperSourceError(Exception):
    """Safe status marker; do not include upstream URLs, headers or bodies."""


def valid_inventory_url(url):
    try:
        target = urlsplit(url)
        if target.scheme != "https" or not target.hostname or target.username or target.password:
            return False
        if target.port not in (None, 443) or target.fragment:
            return False
        host = target.hostname.strip(".").lower()
        if host in ("localhost", "localhost.localdomain") or host.endswith((".local", ".internal")):
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            pass
        if not re.fullmatch(r"[a-z0-9.-]{4,250}", host) or "." not in host:
            return False
        return True
    except (ValueError, TypeError):
        return False


def _text(value, limit=60):
    return re.sub(r"[\x00-\x1f\x7f]", "", str(value or "")).strip()[:limit]


def _number(value):
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        return None
    raw = str(value).strip()
    if not re.fullmatch(r"\+?[0-9 ()-]+", raw):
        return None
    digits = re.sub(r"\D", "", raw)
    if not 7 <= len(digits) <= 15:
        return None
    return "+" + digits


def normalize_inventory(payload):
    """Accept a dedicated flat list or the public Ivasmsper GN_DATA structure.

    Do not accept SMS message feeds (with num/recipient), OTP logs, or
    chat-history records as evidence of available number stock.
    """
    records = []
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        flat = payload.get("numbers")
        if not isinstance(flat, list) and isinstance(payload.get("data"), dict):
            flat = payload["data"].get("numbers")
        if isinstance(flat, list):
            records = flat
        else:
            services = payload.get("services", {})
            if isinstance(services, dict):
                for service, meta in list(services.items())[:100]:
                    if not isinstance(meta, dict) or not isinstance(meta.get("countries"), dict):
                        continue
                    for country, setting in list(meta["countries"].items())[:250]:
                        if not isinstance(setting, dict) or not isinstance(setting.get("numbers"), list):
                            continue
                        for phone in setting["numbers"][:1500]:
                            records.append({"number": phone, "service": service,
                                            "country": country})
    result = []
    seen = set()
    for row in records[:3000]:
        if not isinstance(row, dict):
            # Phone-only flat arrays are supported for owned, dedicated feeds.
            row = {"number": row} if isinstance(row, (str, int)) else {}
        phone = _number(row.get("number") or row.get("phone"))
        if not phone:
            continue
        service = _text(row.get("service") or "IVASPER", 48) or "IVASPER"
        country = _text(row.get("country") or "Naməlum", 48) or "Naməlum"
        unique = (phone, service, country)
        if unique in seen:
            continue
        seen.add(unique)
        result.append({"number": phone, "service": service, "country": country})
        if len(result) >= 1000:
            break
    result.sort(key=lambda item: (item["country"], item["service"], item["number"]))
    return result


async def load_ivasper_inventory():
    """Read a *separate* authorized feed. Do not fall back to IVASMS data."""
    url = os.environ.get("IVASPER_NUMBERS_URL", "").strip()
    if not url:
        return {"connected": False, "status": "not_configured", "numbers": [],
                "message": "IVASPER mənbəyi qoşulmayıb. Render-də IVASPER_NUMBERS_URL təyin edin."}
    if not valid_inventory_url(url):
        return {"connected": False, "status": "invalid_source", "numbers": [],
                "message": "IVASPER mənbə URL-i etibarlı HTTPS inventar endpoint-i olmalıdır."}
    headers = {"Accept": "application/json"}
    token = os.environ.get("IVASPER_NUMBERS_TOKEN", "").strip()
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0), follow_redirects=False,
            trust_env=False,
        ) as client:
            async with client.stream("GET", url, headers=headers) as response:
                if response.status_code in (401, 403):
                    raise IvasperSourceError("access_denied")
                if response.status_code == 503:
                    # The dedicated source explicitly reports whether its
                    # own PostgreSQL storage has not yet been connected.
                    raw = b""
                    async for chunk in response.aiter_bytes():
                        raw += chunk
                        if len(raw) > 2048:
                            break
                    try:
                        status = json.loads(raw).get("error")
                    except (ValueError, AttributeError):
                        status = None
                    if status == "persistent_storage_not_connected":
                        raise IvasperSourceError("database_not_connected")
                    raise IvasperSourceError("storage_unavailable")
                if response.status_code != 200:
                    raise IvasperSourceError("upstream_unavailable")
                if "application/json" not in response.headers.get("content-type", ""):
                    raise IvasperSourceError("invalid_format")
                chunks, count = [], 0
                async for part in response.aiter_bytes():
                    count += len(part)
                    if count > 1_000_000:
                        raise IvasperSourceError("too_large")
                    chunks.append(part)
        payload = json.loads(b"".join(chunks))
        numbers = normalize_inventory(payload)
        return {"connected": True, "status": "ok", "numbers": numbers,
                "count": len(numbers),
                "message": "Yalnız ayrıca IVASPER inventar mənbəyindən oxundu."}
    except IvasperSourceError as exc:
        status = str(exc)
    except (httpx.HTTPError, ValueError, TypeError, json.JSONDecodeError):
        status = "source_unavailable"
    problems = {
        "database_not_connected": (
            "IVASPER PostgreSQL bağlı deyil. Render → ivasper-independent-api "
            "→ Environment → DATABASE_URL hissəsinə ayrıca PostgreSQL "
            "resursunun Internal Database URL ünvanını yazın."),
        "storage_unavailable": (
            "IVASPER verilənlər bazası cavab vermir. Render-də PostgreSQL "
            "bağlantısını və servisin loglarını yoxlayın."),
        "access_denied": (
            "IVASPER API giriş açarı uyğun deyil. Render-də READER və "
            "NUMBERS_TOKEN dəyərlərini yoxlayın."),
    }
    return {"connected": False, "status": status, "numbers": [],
            "message": problems.get(
                status, "IVASPER inventarı oxunmadı. Mənbə bağlantısını yoxlayın.")}
