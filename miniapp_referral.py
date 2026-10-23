"""Referral deep-link helpers used by the Telegram bot and authenticated Mini App."""

import re


def resolve_referrer(start_argument, invitee_id, known_user_ids, is_new_user):
    """Support both ref_ID and legacy numeric links without confusing range requests."""
    if not is_new_user or not isinstance(start_argument, str):
        return None
    argument = start_argument.strip()
    if argument.startswith("ref_"):
        argument = argument[4:]
    if not re.fullmatch(r"[1-9][0-9]{0,18}", argument):
        return None
    referrer = int(argument)
    known = {str(value) for value in known_user_ids}
    if referrer == int(invitee_id) or str(referrer) not in known:
        return None
    return referrer


def build_referral_link(bot_username, user_id):
    """Build a direct Telegram link only from a validated bot username and numeric ID."""
    username = str(bot_username or "").lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", username):
        raise ValueError("Invalid bot username")
    if int(user_id) <= 0:
        raise ValueError("Invalid Telegram user ID")
    return f"https://t.me/{username}?start=ref_{int(user_id)}"
