"""Independent IVASPER inventory ingestion service for Render.

Only explicit authenticated number-stock uploads. No IVASMS data, Telegram
bot credentials, SMS/OTP feeds, or third-party Ivasmsper token reuse.
Uses a separate Render Postgres database so redeploys do not erase stock.
"""
import asyncio
import hmac
import json
import os
import re

from aiohttp import web
import psycopg

from ivasper_external import normalize_inventory

DATABASE_URL = os.getenv("DATABASE_URL", "")
MAX_JSON_BYTES = 500_000


def _authorized(request, env_key):
    configured = os.getenv(env_key, "")
    value = request.headers.get("Authorization", "")
    if len(configured) < 32 or not value.startswith("Bearer "):
        return False
    return hmac.compare_digest(value[7:], configured)


def _static_inventory():
    """Optional Render Environment JSON snapshot when DB credentials are unavailable."""
    try:
        payload = json.loads(os.environ.get("IVASPER_STOCK_JSON", '{"numbers":[]}'))
        if not _stock_payload_only(payload):
            return None
        return normalize_inventory(payload)
    except (ValueError, TypeError):
        return None


def _connection():
    if not DATABASE_URL:
        raise RuntimeError("standalone_inventory_db_not_configured")
    return psycopg.connect(DATABASE_URL, connect_timeout=8)


def init_storage():
    with _connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS ivasper_inventory (
                number TEXT NOT NULL,
                service TEXT NOT NULL,
                country TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (number, service, country)
            )"""
        )


def read_inventory():
    init_storage()
    with _connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT number,service,country
                   FROM ivasper_inventory
                   ORDER BY country,service,number
                   LIMIT 1000"""
            )
            return [
                {"number": number, "service": service, "country": country}
                for number, service, country in cur.fetchall()
            ]


def add_inventory(rows):
    """Append authenticated stock records; never wipe previous numbers."""
    init_storage()
    with _connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO ivasper_inventory (number,service,country)
                   VALUES (%s,%s,%s)
                   ON CONFLICT (number,service,country)
                   DO UPDATE SET updated_at = NOW()""",
                [(x["number"], x["service"], x["country"]) for x in rows],
            )


async def health(request):
    if not DATABASE_URL:
        return web.json_response({
            "ok": _static_inventory() is not None,
            "role": "independent-ivasper-inventory",
            "storage": "render_environment_read_only",
            "persistent_import_enabled": False,
        }, status=200 if _static_inventory() is not None else 503)
    try:
        await asyncio.wait_for(asyncio.to_thread(init_storage), timeout=12)
        return web.json_response({"ok": True, "role": "independent-ivasper-inventory"})
    except Exception:
        return web.json_response(
            {"ok": False, "error": "storage_unavailable"}, status=503)


async def get_numbers(request):
    if not _authorized(request, "IVASPER_READER_TOKEN"):
        return web.json_response({"error": "forbidden"}, status=403)
    if not DATABASE_URL:
        rows = _static_inventory()
        if rows is None:
            return web.json_response({"error": "invalid_inventory_config"}, status=503)
    else:
        try:
            rows = await asyncio.wait_for(asyncio.to_thread(read_inventory), timeout=12)
        except Exception:
            return web.json_response(
                {"error": "storage_unavailable"}, status=503)
    return web.json_response(
        {"numbers": rows},
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


def _stock_payload_only(payload):
    """Disallow SMS history or OTP feeds being treated as stock."""
    if not isinstance(payload, dict):
        return False
    candidate = payload.get("numbers")
    if not isinstance(candidate, list):
        return False
    prohibited = {"otp", "sms", "code", "message", "text", "recipient"}
    for item in candidate:
        if not isinstance(item, dict):
            return False
        if any(k.lower() in prohibited for k in item):
            return False
    return True


async def import_inventory(request):
    if not _authorized(request, "IVASPER_WRITER_TOKEN"):
        return web.json_response({"error": "forbidden"}, status=403)
    if not DATABASE_URL:
        return web.json_response({"error": "persistent_storage_not_connected"}, status=503)
    if "application/json" not in request.headers.get("Content-Type", ""):
        return web.json_response({"error": "invalid_content_type"}, status=415)
    try:
        payload = await request.json()
    except (ValueError, TypeError):
        return web.json_response({"error": "invalid_json"}, status=400)
    if not _stock_payload_only(payload):
        return web.json_response(
            {"error": "inventory_only", "message": "SMS/OTP messages are not accepted."},
            status=400)
    if len(payload["numbers"]) > 1000:
        return web.json_response({"error": "too_many_numbers"}, status=413)
    rows = normalize_inventory(payload)
    if not rows and not (payload.get("clear") is True and not payload["numbers"]):
        return web.json_response({"error": "no_valid_numbers"}, status=400)
    if len(rows) != len(payload["numbers"]):
        return web.json_response(
            {"error": "invalid_or_duplicate_numbers"}, status=400)
    try:
        await asyncio.wait_for(asyncio.to_thread(add_inventory, rows), timeout=15)
    except Exception:
        return web.json_response({"error": "storage_unavailable"}, status=503)
    return web.json_response(
        {"ok": True, "accepted": len(rows), "source": "ivasper_only"},
        headers={"Cache-Control": "no-store"},
    )


def create_app():
    app = web.Application(client_max_size=MAX_JSON_BYTES)
    app.router.add_get("/health", health)
    app.router.add_get("/numbers", get_numbers)
    app.router.add_post("/import", import_inventory)
    return app


if __name__ == "__main__":
    web.run_app(
        create_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
