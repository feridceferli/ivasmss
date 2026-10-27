"""OTP leaderboard aggregation shared by Telegram bot and web Mini App.

Counts are derived from recorded OTP receipt timestamps; no SMS contents,
phone numbers or authentication codes are returned to callers.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

BAKU_TZ = ZoneInfo("Asia/Baku")
PAGE_SIZE = 50


def _day(timestamp):
    """Old bot records use naive UTC; new aware timestamps are also accepted."""
    if not isinstance(timestamp, str):
        return None
    try:
        dt = datetime.fromisoformat(timestamp)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(BAKU_TZ).date()
    except (ValueError, TypeError, OverflowError):
        return None


def _label(uid, profile):
    if not isinstance(profile, dict):
        profile = {}
    name = " ".join(
        str(profile.get(k) or "").strip()
        for k in ("first_name", "last_name")
    ).strip()
    name = name or str(profile.get("full_name") or "").strip()
    username = str(profile.get("username") or "").strip().lstrip("@")
    if not name and username:
        name = "@" + username
    if not name:
        name = "İstifadəçi " + str(uid)
    # Don't expose raw HTML, numbers, SMS or OTPs via the display name.
    # Telegram messages escape this value at rendering time; JS uses textContent.
    return name[:90]


def otp_leaderboards(stats_map, user_map, *, now=None, activity=None):
    """Rank historical OTP records, including archived free-service receipts.

    Some legacy versions saved free OTPs only to activity history, not stats.
    Compare each calendar day's stat and activity counts, taking the larger
    rather than summing to avoid double counting when both sources overlap.
    """
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    date = reference.astimezone(BAKU_TZ).date()
    today = []
    all_time = []
    total_otp = 0
    if not isinstance(stats_map, dict):
        stats_map = {}
    if not isinstance(user_map, dict):
        user_map = {}

    # Activity archive is metadata-only and can include older free receipts.
    from collections import defaultdict
    activity_days = defaultdict(lambda: defaultdict(int))
    if isinstance(activity, list):
        for event in activity:
            if not isinstance(event, dict):
                continue
            if event.get("action") not in ("OTP_RECEIVED", "OTP_RECEIVED_FREE"):
                continue
            uid = str(event.get("uid") or "")
            day = _day(event.get("timestamp"))
            if uid.isdecimal() and day is not None:
                activity_days[uid][day] += 1

    for uid in set(str(k) for k in stats_map) | set(activity_days):
        if not uid.isdecimal():
            continue
        stat = stats_map.get(uid, {})
        if not isinstance(stat, dict):
            stat = {}
        timestamps = stat.get("otps_received", [])
        if not isinstance(timestamps, list):
            timestamps = []
        stat_days = defaultdict(int)
        unparsed = 0
        for stamp in timestamps:
            day = _day(stamp)
            if day is None:
                # Preserve historical total counters even for old timestamps
                # written by a previous bot version.
                unparsed += 1
            else:
                stat_days[day] += 1
        events = activity_days.get(uid, {})
        lifetime = unparsed + sum(
            max(stat_days.get(day, 0), events.get(day, 0))
            for day in (stat_days.keys() | events.keys())
        )
        if not lifetime:
            continue
        daily = max(stat_days.get(date, 0), events.get(date, 0))
        row = {"name": _label(uid, user_map.get(uid, {})), "count": lifetime}
        all_time.append(row)
        total_otp += lifetime
        if daily:
            today.append({"name": row["name"], "count": daily})
    ordering = lambda row: (-row["count"], row["name"].casefold())
    today.sort(key=ordering)
    all_time.sort(key=ordering)
    return {
        "date": date.isoformat(),
        "timezone": "Asia/Baku",
        "daily": today,
        "all_time": all_time,
        "total_otps": total_otp,
        "total_users": len(all_time),
        "today_otps": sum(row["count"] for row in today),
        "today_users": len(today),
    }


def leaderboard_page(board, period="all", offset=0, limit=PAGE_SIZE):
    """Full all-time list can be paged, rather than silently cut at TOP 10."""
    period = "today" if period == "today" else "all"
    values = board["daily"] if period == "today" else board["all_time"]
    offset = max(0, int(offset))
    limit = max(1, min(PAGE_SIZE, int(limit)))
    return {
        "metric": "today_otps" if period == "today" else "total_otps",
        "period": period,
        "leaders": values[offset:offset + limit],
        "offset": offset,
        "limit": limit,
        "total": len(values),
        "has_more": offset + limit < len(values),
        "date": board["date"],
        "timezone": board["timezone"],
        "summary": {
            "today_otps": board["today_otps"],
            "today_users": board["today_users"],
            "total_otps": board["total_otps"],
            "total_users": board["total_users"],
        },
    }
