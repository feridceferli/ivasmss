"""WhatsApp-only invite gate; recorded from verified Telegram /start updates.

Referrals count distinct Telegram accounts created by an eligible deep-link,
not visits, message counts, IPs, or arbitrary IDs submitted by a web client.
The gate defaults OFF until an administrator explicitly enables it.
"""
import re
import time
from data_storage import atomic_save, data_path

SETTINGS_FILE = data_path("whatsapp_referral_settings.json")
REQUIRED = 5


def is_whatsapp(service):
    return str(service or "").strip().casefold().replace("-", "_").replace(" ", "_") in (
        "wa", "whatsapp", "whatsapp_business"
    )


def referral_param(value):
    match = re.fullmatch(r"ref_([1-9][0-9]{0,19})", str(value or ""))
    return match.group(1) if match else None


def load_settings():
    import json
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            content = json.load(f)
        if isinstance(content, dict) and type(content.get("enabled")) is bool:
            return {"enabled": content["enabled"], "required": REQUIRED,
                    "updated_at": float(content.get("updated_at", 0) or 0)}
    except (OSError, ValueError, TypeError):
        pass
    return {"enabled": False, "required": REQUIRED, "updated_at": 0.0}


def save_settings(enabled):
    if type(enabled) is not bool:
        raise ValueError("enabled must be a boolean")
    result = {"enabled": enabled, "required": REQUIRED, "updated_at": time.time()}
    atomic_save(result, SETTINGS_FILE)
    return result


def record_first_referral(users, invited_id, inviter_id):
    """Attach the inviter only on first account creation, never reassign.

    The owner must already be a registered account and cannot self-refer.
    Caller authenticates invited_id from the verified Telegram update.
    """
    invited_id, inviter_id = str(invited_id), str(inviter_id)
    if (not invited_id.isdecimal() or not inviter_id.isdecimal()
            or invited_id == inviter_id or inviter_id not in users
            or invited_id in users):
        return False
    users[invited_id] = {
        "user_id": invited_id, "balance": 0.0,
        "total_numbers": 0, "verified": False,
        "referred_by_pending": inviter_id,
    }
    return True


def confirm_referral(users, invited_id):
    """Mark a pending referral only after required-channel checks pass."""
    invited_id = str(invited_id)
    record = users.get(invited_id)
    if not isinstance(record, dict):
        return False
    inviter_id = str(record.get("referred_by_pending") or "")
    if (not inviter_id.isdecimal() or inviter_id == invited_id
            or inviter_id not in users):
        return False
    if record.get("referred_by"):
        return False
    record["referred_by"] = inviter_id
    record.pop("referred_by_pending", None)
    return True


def progress(users, uid, *, enabled=False, is_admin=False, bot_username=""):
    uid = str(uid)
    # A Telegram user_id may only have one recorded inviter. Filtering
    # banned/delete state is unnecessary: accounts are counted only once.
    count = sum(
        str(record.get("referred_by", "")) == uid
        for record in users.values()
        if isinstance(record, dict)
    ) if isinstance(users, dict) else 0
    username = str(bot_username).lstrip("@")
    link = (f"https://t.me/{username}?start=ref_{uid}"
            if re.fullmatch(r"[A-Za-z0-9_]{5,32}", username) and uid.isdecimal()
            else "")
    required = REQUIRED
    return {
        "enabled": bool(enabled), "required": required,
        "count": count, "remaining": max(0, required - count),
        "unlocked": not enabled or is_admin or count >= required,
        "is_admin": bool(is_admin), "invite_link": link,
    }


def requires_invites(users, uid, service, settings, *, is_admin=False):
    if not is_whatsapp(service) or not settings.get("enabled") or is_admin:
        return False
    return not progress(users, uid, enabled=True)["unlocked"]
