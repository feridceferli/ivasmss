"""Read-only catalogue for the admin IVASPER website/Mini App panel.

Uses only the existing trusted IVASMS catalogue and user-scoped allocations.
No third-party Ivasmsper credentials, SMS messages, OTP codes, or group feeds.
"""
import re
from collections import Counter


def catalog_snapshot(services, archived, monitor, active, owner_id, remaining_seconds):
    """Return safe counts and only the requesting administrator's current leases."""
    catalogue = {}
    if isinstance(services, dict):
        for key, entries in services.items():
            name = str(key).strip().lower()
            if not re.fullmatch(r"[a-z0-9_.+ -]{1,40}", name):
                continue
            if not isinstance(entries, list):
                continue
            valid = sorted({
                digits for raw in entries
                if (digits := re.sub(r"\D", "", str(raw))) and
                   re.fullmatch(r"\d{1,10}", digits)
            })
            if valid:
                catalogue[name] = valid

    countries = Counter()
    if isinstance(archived, dict):
        for record in archived.values():
            if isinstance(record, dict):
                country = str(record.get("country") or "Naməlum").strip()[:70]
                countries[country] += 1

    own_active = []
    if isinstance(active, dict):
        for number, info in active.items():
            if not isinstance(info, dict):
                continue
            try:
                if int(info.get("uid", 0)) != int(owner_id):
                    continue
                remaining = int(remaining_seconds(info))
            except (TypeError, ValueError, OverflowError, KeyError):
                continue
            digits = re.sub(r"\D", "", str(number))
            if remaining <= 0 or not re.fullmatch(r"\d{7,15}", digits):
                continue
            timestamp = info.get("timestamp")
            own_active.append({
                "number": "+" + digits,
                "range": str(info.get("range") or "")[:35],
                "remaining_seconds": remaining,
                "created_at": timestamp.timestamp() if hasattr(timestamp, "timestamp") else 0,
            })
    own_active.sort(key=lambda item: item["created_at"], reverse=True)

    monitor = monitor if isinstance(monitor, dict) else {}
    state = monitor.get("state")
    if state not in {"ok", "checking", "starting", "error", "failed"}:
        state = "naməlum"
    http_status = monitor.get("http_status")
    if type(http_status) is not int or not 100 <= http_status <= 599:
        http_status = None
    return {
        "services": dict(sorted(catalogue.items())),
        "service_count": len(catalogue),
        "range_count": sum(len(ranges) for ranges in catalogue.values()),
        "archive_count": sum(countries.values()),
        "archive_countries": len(countries),
        "own_active": own_active,
        "monitor": {"state": state, "http_status": http_status},
        "note": "Range siyahısı nömrə ehtiyatını təsdiqləmir. Yalnız sizə ayrılmış aktiv nömrələr görünür.",
    }
