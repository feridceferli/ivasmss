"""Safe, group-only provider availability digest.

Tracks /liveaccess service/country/range metadata. It never requests or reads
/console, /success-otp, SMS bodies, OTP codes, or allocated phone numbers.

A change summary is sent to one configured Telegram group, with a five-minute
cooldown and a persisted fingerprint to prevent duplicate restart notices.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
from pathlib import Path

from data_storage import atomic_save, data_path


_STATE_FILENAME = "global_availability_feed_state.json"
_MIN_NOTIFICATION_INTERVAL = 300
_MAX_COUNTRY_LINES = 8


def availability_snapshot(services, country_prefix_lookup):
    """Summarize only advertised prefixes (not phone numbers or SMS records)."""
    services_seen = set()
    by_country = {}
    identities = set()
    for raw_service, rows in (services or {}).items():
        service = str(raw_service).strip().lower()
        if not service or not isinstance(rows, (list, tuple)):
            continue
        for raw in rows:
            rid = re.sub(r"\D", "", str(raw or ""))
            # Provider /liveaccess values are range identifiers, not allocations.
            if not 1 <= len(rid) <= 10:
                continue
            prefix = str(country_prefix_lookup(rid) or "").strip()
            if not re.fullmatch(r"[1-9]\d{0,3}", prefix):
                continue
            services_seen.add(service)
            identities.add((service, prefix, rid))
            by_country.setdefault(prefix, set()).add((service, rid))

    # Hash for equality only; neither raw range nor phone data is persisted.
    serialized = json.dumps(sorted(identities), ensure_ascii=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return {
        "fingerprint": fingerprint,
        "services": len(services_seen),
        "countries": len(by_country),
        "range_entries": len(identities),
        "country_counts": {key: len(items) for key, items in sorted(by_country.items())},
    }


def compose_availability_notice(current, previous=None, country_name_lookup=None):
    """Plain aggregated feed text; all content is escaped for Telegram HTML."""
    previous = previous if isinstance(previous, dict) else {}
    old_counts = previous.get("country_counts", {})
    if not isinstance(old_counts, dict):
        old_counts = {}

    first = not bool(previous.get("fingerprint"))
    title = "🌍 <b>GLOBAL FEED — XİDMƏT AKTİVLİYİ</b>"
    rows = [
        title,
        "",
        ("📡 <b>API kataloqunun cari vəziyyəti</b>" if first
         else "🔄 <b>API range siyahısında dəyişiklik</b>"),
        f"🧩 Xidmət növləri: <b>{current['services']}</b>",
        f"🌐 Ölkə kodları: <b>{current['countries']}</b>",
        f"📊 Xidmət/range qeydiyyatları: <b>{current['range_entries']}</b>",
    ]

    changed = []
    counts = current["country_counts"]
    for code in set(counts) | set(old_counts):
        new_value = int(counts.get(code, 0))
        old_value = int(old_counts.get(code, 0))
        if new_value != old_value:
            changed.append((code, new_value, new_value - old_value))
    if changed:
        changed.sort(key=lambda item: (-abs(item[2]), item[0]))
        rows.append("")
        rows.append("📍 <b>Ölkə kodları üzrə dəyişikliklər:</b>" if not first
                    else "📍 <b>Ən aktiv ölkə kodları:</b>")
        for prefix, count, delta in changed[:_MAX_COUNTRY_LINES]:
            name = ""
            if country_name_lookup:
                try:
                    value = country_name_lookup(prefix)
                    if isinstance(value, (list, tuple)) and len(value) > 1:
                        name = str(value[1])[:45]
                except (ValueError, TypeError, KeyError):
                    pass
            sign = "+" if delta > 0 else ""
            safe_name = html.escape(name)
            rows.append(
                f"• <code>+{html.escape(prefix)}</code>"
                + (f" {safe_name}" if safe_name else "")
                + f" — {count} qeydiyyat"
                + (f" ({sign}{delta})" if not first else "")
            )
        if len(changed) > _MAX_COUNTRY_LINES:
            rows.append(f"… və daha {len(changed) - _MAX_COUNTRY_LINES} ölkə kodu")

    rows.extend([
        "",
        "ℹ️ Məlumat /liveaccess kataloqundan alınır.",
        "⚠️ Range siyahısı aktiv nömrə ehtiyatını və SMS/OTP çatdırılmasını təsdiqləmir.",
        "🔒 Şəxsi nömrələr, SMS mətnləri və OTP kodları paylaşılmır.",
    ])
    return "\n".join(rows)


def _read_state(filename):
    try:
        with Path(filename).open(encoding="utf-8") as source:
            state = json.load(source)
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


async def publish_global_availability_feed(
    *,
    services,
    bot,
    group_id,
    country_prefix_lookup,
    country_name_lookup=None,
    now=None,
    state_file=None,
):
    """Baseline without announcing on startup; send subsequent changes
    no more than once per five minutes.

    The baseline avoids a duplicate status announcement after Render restarts
    without persistent storage. On send failure the previous state is kept.
    """
    if not group_id:
        return "not_configured"
    current = availability_snapshot(services, country_prefix_lookup)
    if current["range_entries"] == 0:
        return "empty_catalog"

    location = state_file or data_path(_STATE_FILENAME)
    previous = _read_state(location)
    timestamp = time.time() if now is None else float(now)

    # Render may use ephemeral storage, causing its local snapshot to disappear
    # between deployments. Baseline silently rather than reannounce the entire
    # catalogue on every restart; changes during uptime still notify the group.
    if not previous.get("fingerprint"):
        atomic_save({
            "fingerprint": current["fingerprint"],
            "country_counts": current["country_counts"],
            "last_sent": timestamp,
        }, location)
        print("[global-feed] Initial snapshot saved; no startup spam", flush=True)
        return "initialized"

    if current["fingerprint"] == previous.get("fingerprint"):
        return "unchanged"

    last_sent = float(previous.get("last_sent", 0) or 0)
    if timestamp - last_sent < _MIN_NOTIFICATION_INTERVAL:
        return "cooldown"

    message = compose_availability_notice(current, previous, country_name_lookup)
    try:
        await bot.send_message(chat_id=int(group_id), text=message, parse_mode="HTML")
    except Exception as exc:
        # Do not expose user identifiers, authentication headers or feed contents.
        print(f"[global-feed] Telegram delivery failed: {type(exc).__name__}", flush=True)
        return "send_failed"

    atomic_save({
        "fingerprint": current["fingerprint"],
        "country_counts": current["country_counts"],
        "last_sent": timestamp,
    }, location)
    print("[global-feed] Aggregated provider status delivered", flush=True)
    return "sent"
