"""Safe, group-only provider availability digest.

Tracks /liveaccess service/country/range metadata. It never requests or reads
/console, /success-otp, SMS bodies, OTP codes, or allocated phone numbers.

A change summary is sent to one configured Telegram group, with a ten-minute
cadence and persisted state to prevent duplicate restart notices.
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
_MIN_NOTIFICATION_INTERVAL = 600
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
        "service_ids": sorted(s for s in services_seen
                              if re.fullmatch(r"[a-z0-9_-]{1,32}", s)),
    }


def compose_availability_notice(current, previous=None, country_name_lookup=None,
                                *, periodic=False, new_services=()):
    """Plain aggregated feed text; all content is escaped for Telegram HTML."""
    previous = previous if isinstance(previous, dict) else {}
    old_counts = previous.get("country_counts", {})
    if not isinstance(old_counts, dict):
        old_counts = {}

    first = not bool(previous.get("fingerprint"))
    title = ("🆕 <b>YENİ XİDMƏT XƏBƏRLƏRİ</b>" if new_services else
             "🕒 <b>10 DƏQİQƏLİK KATALOQ XÜLASƏSİ</b>" if periodic else
             "🌍 <b>GLOBAL FEED — XİDMƏT AKTİVLİYİ</b>")
    subtitle = ("😄 <b>Kataloqda təzə qonaq var!</b>" if new_services else
                "☕ <b>On dəqiqəlik kataloq fasiləsi</b>" if periodic else
                "📡 <b>API kataloqunun cari vəziyyəti</b>" if first else
                "🔄 <b>API range siyahısında dəyişiklik</b>")
    rows = [
        title, "", subtitle,
        f"🧩 Xidmət növləri: <b>{current['services']}</b>",
        f"🌐 Ölkə kodları: <b>{current['countries']}</b>",
        f"📊 Xidmət/range qeydiyyatları: <b>{current['range_entries']}</b>",
    ]
    if new_services:
        safe = [s for s in new_services if re.fullmatch(r"[a-z0-9_-]{1,32}", s)]
        rows.extend(["", "🎉 <b>Yeni xidmətlər:</b>"])
        rows.extend("• <code>" + html.escape(s.upper()) + "</code>" for s in safe[:15])
        if len(safe) > 15:
            rows.append(f"… və daha {len(safe) - 15} xidmət")

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
    message_decorator=None,
):
    """Ten-minute digest plus immediate, batched, new-service announcements.

    A first snapshot is silent; sent service IDs persist across restarts.
    Failed Telegram sends never advance state. Only group posts are sent.
    """
    if not group_id:
        return "not_configured"
    current = availability_snapshot(services, country_prefix_lookup)
    if current["range_entries"] == 0:
        return "empty_catalog"
    location = state_file or data_path(_STATE_FILENAME)
    previous = _read_state(location)
    timestamp = time.time() if now is None else float(now)
    service_ids = set(current["service_ids"])

    if not previous.get("fingerprint"):
        atomic_save({
            "fingerprint": current["fingerprint"],
            "country_counts": current["country_counts"],
            "known_services": sorted(service_ids),
            "post_count": 0,
            "last_sent": timestamp,
        }, location)
        print("[global-feed] Initial snapshot saved; no startup spam", flush=True)
        return "initialized"

    if not isinstance(previous.get("known_services"), list):
        # Old state has no remembered service IDs. Migrate silently.
        previous["known_services"] = sorted(service_ids)
        previous.setdefault("post_count", 0)
        atomic_save(previous, location)

    known = {s for s in previous["known_services"]
             if isinstance(s, str) and re.fullmatch(r"[a-z0-9_-]{1,32}", s)}
    new_services = sorted(service_ids - known)
    last_sent = float(previous.get("last_sent", timestamp) or timestamp)
    due = timestamp - last_sent >= _MIN_NOTIFICATION_INTERVAL
    if not due and not new_services:
        return ("unchanged" if current["fingerprint"] == previous.get("fingerprint")
                else "cooldown")

    message = compose_availability_notice(
        current, previous, country_name_lookup,
        periodic=not new_services, new_services=new_services,
    )
    if message_decorator is not None:
        try:
            captioned = await message_decorator(current, previous, message)
            if isinstance(captioned, str) and 1 <= len(captioned) <= 3800:
                message = captioned
        except Exception as exc:
            print(f"[global-feed] optional caption failed: {type(exc).__name__}",
                  flush=True)
    try:
        await bot.send_message(chat_id=int(group_id), text=message, parse_mode="HTML")
    except Exception as exc:
        print(f"[global-feed] Telegram delivery failed: {type(exc).__name__}", flush=True)
        return "send_failed"

    atomic_save({
        "fingerprint": current["fingerprint"],
        "country_counts": current["country_counts"],
        "known_services": sorted(known | service_ids),
        "post_count": int(previous.get("post_count", 0)) + 1,
        "last_sent": timestamp,
    }, location)
    kind = "new_service" if new_services else "sent"
    print(f"[global-feed] Published {kind} digest to group", flush=True)
    return kind
