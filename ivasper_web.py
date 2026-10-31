"""Read-only catalogue for the admin IVASPER website/Mini App panel.

Uses only the existing trusted IVASMS catalogue and user-scoped allocations.
No third-party Ivasmsper credentials, SMS messages, OTP codes, or group feeds.
"""
import re
from collections import Counter



def archive_country_page(archived, owner_id, country="", page=0, page_size=25):
    """Country totals and paginated owner-only numbers from the local archive.

    Archive entries belong to users; a country aggregate never grants access
    to another person's allocation. An unowned number is never revealed.
    """
    totals = Counter()
    own = {}
    if isinstance(archived, dict):
        for key, record in archived.items():
            if not isinstance(record, dict):
                continue
            label = str(record.get("country") or "Naməlum").strip()[:70]
            label = label or "Naməlum"
            totals[label] += 1
            if str(record.get("user_id") or "") != str(owner_id):
                continue
            number = str(record.get("number") or key).strip()
            if not re.fullmatch(r"\+?[0-9 ()-]+", number):
                continue
            digits = re.sub(r"\D", "", number)
            if not re.fullmatch(r"\d{7,15}", digits):
                continue
            own.setdefault(label, {})["+" + digits] = {
                "number": "+" + digits,
                "range": str(record.get("range") or "")[:35],
            }

    countries = [
        {"country": label, "count": count, "my_count": len(own.get(label, {}))}
        for label, count in sorted(totals.items(),
                                   key=lambda pair: (-pair[1], pair[0]))
    ]
    if not countries:
        return countries, {
            "country": "", "page": 0, "pages": 0, "my_count": 0,
            "total_count": 0, "entries": [],
        }
    names = {item["country"] for item in countries}
    if country not in names:
        preferred = next(
            (item["country"] for item in countries
             if ("azərbaycan" in item["country"].casefold()
                 or "azerbaijan" in item["country"].casefold()
                 or "🇦🇿" in item["country"])), None)
        country = preferred or countries[0]["country"]
    page_size = max(1, min(int(page_size), 50))
    all_numbers = sorted(own.get(country, {}).values(),
                         key=lambda item: item["number"])
    pages = max(1, (len(all_numbers) + page_size - 1) // page_size)
    try:
        index = min(max(0, int(page)), pages - 1)
    except (ValueError, TypeError, OverflowError):
        index = 0
    return countries, {
        "country": country,
        "page": index,
        "pages": pages,
        "my_count": len(all_numbers),
        "total_count": totals[country],
        "entries": all_numbers[index * page_size:(index + 1) * page_size],
    }


def catalog_snapshot(services, archived, monitor, active, owner_id, remaining_seconds,
                     country="", page=0):
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
                label = str(record.get("country") or "Naməlum").strip()[:70]
                countries[label] += 1

    archive_countries, archive_page = archive_country_page(\n        archived, owner_id, country, page)\n\n    own_active = []
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
        "archive_countries": len(countries),\n        "archive_country_list": archive_countries,\n        "archive_page": archive_page,
        "own_active": own_active,
        "monitor": {"state": state, "http_status": http_status},
        "note": "Ölkə statistikası ümumi arxiv sayıdır. Tam nömrələr yalnız sizin arxiv qeydlərinizdən göstərilir; bu, nömrənin hazırda aktiv olduğunu sübut etmir.",
    }
