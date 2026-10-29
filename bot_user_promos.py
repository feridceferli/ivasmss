"""Opt-out capable hourly Telegram bot reminders for registered users.

Only short promotional information is sent. Never claim live inventory unless
a real allocation has been confirmed; these templates invite a catalog check.
"""
import json
import math
import time
from pathlib import Path

from data_storage import atomic_save
from safe_broadcast import recipient_ids, validate_notice

DEFAULT_TEMPLATES = [
    "📱 Gəl, nömrə seçimlərinə bax! Bəlkə axtardığın xidməti tapdın. /start",
    "🔥 Yaxşı nömrə axtarırsan? Botda mövcud seçimləri yoxla! /start",
    "✨ Nömrə axtarışını sonraya saxlama! Xidmətlərə və ölkələrə göz at. /start",
    "🚀 Yeni nömrə seçimlərini yoxlamağın vaxtıdır! Botu aç, özün seç. /start",
    "📲 Bir kliklə nömrə xidmətlərinə bax! Seçimini botdan et. /start",
]

DEFAULT_INTERVAL_MINUTES = 60
MAX_INTERVAL_MINUTES = 1440
MAX_TEMPLATES = 10
MAX_TEMPLATE_LENGTH = 220


class PromoConfigError(ValueError):
    pass


def validate_templates(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_TEMPLATES:
        raise PromoConfigError("1–10 qısa mesaj yazın, hər mesaj ayrı sətirdə olsun.")
    result = []
    for message in raw:
        if not isinstance(message, str):
            raise PromoConfigError("Mesajlar adi mətn olmalıdır.")
        msg = validate_notice(message)
        if not 8 <= len(msg) <= MAX_TEMPLATE_LENGTH or "\n" in msg or "\r" in msg:
            raise PromoConfigError("Hər mesaj bir sətir və 8–220 simvol olmalıdır.")
        if msg in result:
            raise PromoConfigError("Eyni mesajı iki dəfə yazmayın.")
        result.append(msg)
    return result


def normalize_settings(raw):
    if not isinstance(raw, dict):
        raise PromoConfigError("Promo konfiqurasiyası oxunmur.")
    enabled = raw.get("enabled", True)
    interval = raw.get("interval_minutes", DEFAULT_INTERVAL_MINUTES)
    templates = raw.get("templates", DEFAULT_TEMPLATES)
    if type(enabled) is not bool:
        raise PromoConfigError("Aktivlik düzgün deyil.")
    if type(interval) is not int or not DEFAULT_INTERVAL_MINUTES <= interval <= MAX_INTERVAL_MINUTES:
        raise PromoConfigError("Interval 60–1440 dəqiqə olmalıdır.")
    templates = validate_templates(templates)
    def timestamp(key):
        val = raw.get(key, 0)
        if type(val) not in (int, float) or not math.isfinite(val) or val < 0:
            raise PromoConfigError("Yadda saxlanan paylaşım vaxtı yanlışdır.")
        return float(val)
    index = raw.get("next_index", 0)
    if type(index) is not int or index < 0:
        raise PromoConfigError("Mesaj sıra nömrəsi yanlışdır.")
    return {
        "enabled": enabled,
        "interval_minutes": interval,
        "templates": templates,
        "next_due_at": timestamp("next_due_at"),
        "last_sent_at": timestamp("last_sent_at"),
        "next_index": index,
        "last_result": raw.get("last_result", {}) if isinstance(raw.get("last_result", {}), dict) else {},
    }


def load_settings(path):
    file = Path(path)
    if not file.exists():
        return normalize_settings({})
    try:
        return normalize_settings(json.loads(file.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        raise PromoConfigError("Promo ayarları oxunmadı; faylı yoxlayın.") from exc


def save_settings(path, data):
    value = normalize_settings(data)
    atomic_save(value, path)
    return value


def update_settings(path, *, enabled=None, interval_minutes=None, templates=None, now=None):
    current = load_settings(path)
    changes = {}
    if enabled is not None:
        if type(enabled) is not bool:
            raise PromoConfigError("Aktivlik true/false olmalıdır.")
        changes["enabled"] = enabled
    if interval_minutes is not None:
        changes["interval_minutes"] = interval_minutes
    if templates is not None:
        changes["templates"] = validate_templates(templates)
    if not changes:
        raise PromoConfigError("Dəyişiklik göndərilməyib.")
    old_enabled, old_interval = current["enabled"], current["interval_minutes"]
    current.update(changes)
    result = normalize_settings(current)
    # Re-enable or change interval: begin a fresh countdown; do not send instantly.
    if (not old_enabled and result["enabled"]) or result["interval_minutes"] != old_interval:
        result["next_due_at"] = (time.time() if now is None else now) + result["interval_minutes"] * 60
    return save_settings(path, result)


def planned_message(settings):
    data = normalize_settings(settings)
    index = data["next_index"] % len(data["templates"])
    return data["templates"][index] + "\n\n🔕 Bu elanları dayandırmaq: /promo_off"


def eligible_users(users, banned_ids=()):
    banned = {str(uid) for uid in banned_ids}
    return [
        uid for uid in recipient_ids(users)
        if str(uid) not in banned
        and isinstance(users.get(str(uid)), dict)
        and not users[str(uid)].get("promo_opt_out", False)
    ]


def mark_scheduled(settings, now=None):
    """Reserve the next 1-hour slot before dispatch to avoid restart duplication."""
    now = time.time() if now is None else now
    result = normalize_settings(settings)
    result["next_due_at"] = now + result["interval_minutes"] * 60
    result["next_index"] = (result["next_index"] + 1) % len(result["templates"])
    return result


def ready_to_dispatch(settings, now=None):
    data = normalize_settings(settings)
    now = time.time() if now is None else now
    return data["enabled"] and data["next_due_at"] > 0 and now >= data["next_due_at"]
