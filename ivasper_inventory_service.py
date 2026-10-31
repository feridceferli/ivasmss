"""Independent IVASPER inventory ingestion service for Render.

Only explicit authenticated number-stock uploads. No IVASMS data, Telegram
bot credentials, SMS/OTP feeds, or third-party Ivasmsper token reuse.
Uses a separate Render Postgres database so redeploys do not erase stock.
"""
import asyncio
import hmac
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


def replace_inventory(rows):
    with _connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ivasper_inventory")
            cur.executemany(
                """INSERT INTO ivasper_inventory
                   (number,service,country)
                   VALUES (%s,%s,%s)""",
                [(x["number"], x["service"], x["country"]) for x in rows],
            )


async def health(request):
    try:
        await asyncio.wait_for(asyncio.to_thread(init_storage), timeout=12)
        return web.json_response({"ok": True, "role": "independent-ivasper-inventory"})
    except Exception:
        return web.json_response(
            {"ok": False, "error": "storage_unavailable"}, status=503)


async def get_numbers(request):
    if not _authorized(request, "IVASPER_READER_TOKEN"):
        return web.json_response({"error": "forbidden"}, status=403)
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
        await asyncio.wait_for(asyncio.to_thread(replace_inventory, rows), timeout=15)
    except Exception:
        return web.json_response({"error": "storage_unavailable"}, status=503)
    return web.json_response(
        {"ok": True, "imported": len(rows), "source": "ivasper_only"},
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
