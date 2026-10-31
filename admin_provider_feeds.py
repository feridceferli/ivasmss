"""Private, opt-in integrations for administrator-owned SMS feeds.

The upstream public examples contained embedded access tokens. Never import their
tokens or Telegram forwarding loops. This module reads ONLY the credentials set
separately in Render, keeps private records off public endpoints, and does not
forward or persist SMS/OTP data.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from urllib.parse import urlsplit

import httpx

try:
    from aiohttp import ClientSession, ClientTimeout, WSMsgType
except ImportError:  # pragma: no cover - production requirements include aiohttp
    ClientSession = ClientTimeout = WSMsgType = None

_MAX_ITEMS = 30
_LIVE_EVENTS = deque(maxlen=60)
_LIVE_STATE = {"connected": False, "last_event": None, "last_error": None}
_GREEN_BASE = "GREEN_SMS_API_BASE_URL"
_GREEN_KEY = "GREEN_SMS_API_KEY"
_IVAS_URL = "IVASMSPER_PANEL_URL"
_IVAS_KEY = "IVASMSPER_PANEL_TOKEN"
_IVAS_WS = "IVASMSPER_WS_URL"


class ProviderFeedError(Exception):
    def __init__(self, code: str, http_status: int = 502):
        super().__init__(code)
        self.code = code
        self.http_status = http_status


def _valid_endpoint(value: str, scheme: str = "https") -> bool:
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme == scheme and bool(parsed.hostname)
            and not parsed.username and not parsed.password
            and parsed.hostname.lower() not in ("localhost", "127.0.0.1", "::1")
            and not parsed.fragment
        )
    except ValueError:
        return False


def configured_status() -> dict:
    green_url = os.getenv(_GREEN_BASE, "").strip()
    green_token = os.getenv(_GREEN_KEY, "").strip()
    ivas_url = os.getenv(_IVAS_URL, "").strip()
    ivas_token = os.getenv(_IVAS_KEY, "").strip()
    ws_uri = os.getenv(_IVAS_WS, "").strip()
    return {
        "green_sms": {
            "rest_configured": bool(green_token and _valid_endpoint(green_url)),
            "mode": "REST",
        },
        "ivasmsper": {
            "rest_configured": bool(ivas_token and _valid_endpoint(ivas_url)),
            "websocket_configured": bool(_valid_endpoint(ws_uri, "wss")),
            "live_connected": bool(_LIVE_STATE["connected"]),
            "last_live_event": _LIVE_STATE["last_event"],
            "live_event_count": len(_LIVE_EVENTS),
            "mode": "REST + WebSocket",
        },
    }


def _text(value, limit: int = 1200) -> str:
    return str(value if value is not None else "")[:limit]


def _record(number="", service="", message="", timestamp="", source="", event_id="") -> dict:
    return {
        "number": _text(number, 40),
        "service": _text(service, 120),
        "message": _text(message, 1200),
        "time": _text(timestamp, 80),
        "source": source,
        "id": _text(event_id, 80),
    }


def parse_green_payload(payload, limit: int = _MAX_ITEMS) -> list[dict]:
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ProviderFeedError("invalid_provider_response")
    rows = []
    for item in payload["results"][:limit]:
        if isinstance(item, dict):
            rows.append(_record(
                item.get("number"), item.get("sender") or item.get("service"),
                item.get("sms"), item.get("created_at") or item.get("date"),
                "Green SMS", item.get("id"),
            ))
    return rows


def parse_ivas_payload(payload, limit: int = _MAX_ITEMS) -> list[dict]:
    if isinstance(payload, dict):
        if payload.get("status") != "success" or not isinstance(payload.get("data"), list):
            raise ProviderFeedError("invalid_provider_response")
        entries = payload["data"]
    elif isinstance(payload, list):
        entries = payload
    else:
        raise ProviderFeedError("invalid_provider_response")
    rows = []
    for item in entries[:limit]:
        if isinstance(item, dict):
            rows.append(_record(
                item.get("num"), item.get("cli"), item.get("message"),
                item.get("dt"), "Ivasmsper REST",
            ))
        elif isinstance(item, (list, tuple)) and len(item) >= 4:
            rows.append(_record(item[1], item[0], item[2], item[3], "Ivasmsper REST"))
    return rows


async def _http_json(url: str, *, headers=None, params=None):
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(12.0, connect=5.0), follow_redirects=False
        ) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 401:
                raise ProviderFeedError("upstream_unauthorized")
            if response.status_code == 403:
                raise ProviderFeedError("upstream_forbidden")
            if response.status_code == 404:
                raise ProviderFeedError("upstream_endpoint_missing")
            if response.status_code == 429:
                raise ProviderFeedError("upstream_rate_limited")
            if response.status_code >= 400:
                raise ProviderFeedError("upstream_http_error")
            if response.is_redirect:
                raise ProviderFeedError("upstream_redirect_rejected")
            if len(response.content) > 1024 * 1024:
                raise ProviderFeedError("response_too_large")
            return response.json()
    except (httpx.RequestError, ValueError) as exc:
        raise ProviderFeedError("upstream_unreachable_or_invalid") from exc


async def fetch_green(limit: int = _MAX_ITEMS) -> list[dict]:
    base = os.getenv(_GREEN_BASE, "").strip().rstrip("/")
    token = os.getenv(_GREEN_KEY, "").strip()
    if not token or not _valid_endpoint(base):
        raise ProviderFeedError("provider_not_configured", 503)
    data = await _http_json(
        base + "/messages/",
        headers={"Authorization": "Bearer " + token},
        params={"since_id": 0, "page_size": min(limit, _MAX_ITEMS)},
    )
    return parse_green_payload(data, limit)


async def fetch_ivas_rest(limit: int = _MAX_ITEMS) -> list[dict]:
    url = os.getenv(_IVAS_URL, "").strip()
    token = os.getenv(_IVAS_KEY, "").strip()
    if not token or not _valid_endpoint(url):
        raise ProviderFeedError("provider_not_configured", 503)
    data = await _http_json(url, params={"token": token, "records": min(limit, _MAX_ITEMS)})
    return parse_ivas_payload(data, limit)


def live_ivas_snapshot(limit: int = _MAX_ITEMS) -> list[dict]:
    return list(reversed(list(_LIVE_EVENTS)))[:limit]


async def feed_snapshot(provider: str, limit: int = _MAX_ITEMS) -> dict:
    limit = max(1, min(int(limit), _MAX_ITEMS))
    if provider == "green_sms":
        return {"provider": provider, "records": await fetch_green(limit)}
    if provider != "ivasmsper":
        raise ProviderFeedError("invalid_provider", 400)
    details = configured_status()["ivasmsper"]
    rows = live_ivas_snapshot(limit)
    if details["rest_configured"]:
        try:
            rows.extend(await fetch_ivas_rest(limit))
        except ProviderFeedError:
            if not rows:
                raise
    if not details["rest_configured"] and not details["websocket_configured"]:
        raise ProviderFeedError("provider_not_configured", 503)
    return {"provider": provider, "records": rows[:limit], "live_connected": details["live_connected"]}


def _process_ivas_ws_text(data: str) -> bool:
    if not data.startswith("42/livesms,"):
        return False
    try:
        event = json.loads(data[len("42/livesms,"):])
    except (TypeError, ValueError):
        return False
    if not isinstance(event, list) or len(event) < 2 or not isinstance(event[1], dict):
        return False
    item = event[1]
    _LIVE_EVENTS.append(_record(
        item.get("recipient"), item.get("originator"),
        item.get("message"), item.get("receivedAt") or item.get("timestamp") or
        time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "Ivasmsper WebSocket", item.get("id"),
    ))
    _LIVE_STATE["last_event"] = int(time.time())
    return True


async def run_ivasmsper_websocket():
    """Optional read-only live listener for the admin's own WSS session.

    Only ephemeral RAM holds the last 60 messages; no Telegram/group forwarding.
    """
    uri = os.getenv(_IVAS_WS, "").strip()
    if not _valid_endpoint(uri, "wss") or ClientSession is None:
        return
    while True:
        try:
            timeout = ClientTimeout(total=None, sock_connect=12)
            async with ClientSession(timeout=timeout) as session:
                async with session.ws_connect(uri, heartbeat=30, max_msg_size=262144) as ws:
                    initial = await ws.receive(timeout=15)
                    if initial.type != WSMsgType.TEXT or not str(initial.data).startswith("0"):
                        raise ProviderFeedError("invalid_ws_handshake")
                    await ws.send_str("40/livesms,")
                    _LIVE_STATE["connected"] = True
                    _LIVE_STATE["last_error"] = None
                    async for msg in ws:
                        if msg.type == WSMsgType.TEXT:
                            if msg.data == "2":
                                await ws.send_str("3")
                            else:
                                _process_ivas_ws_text(msg.data)
                        elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                            break
        except asyncio.CancelledError:
            raise
        except Exception:
            # Never log the URI, messages, access tokens or handshake content.
            _LIVE_STATE["last_error"] = "connection_unavailable"
        finally:
            _LIVE_STATE["connected"] = False
        await asyncio.sleep(10)
