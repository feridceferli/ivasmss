"""Server-side visibility rules for operator-announced SMS services.

Admin may see and toggle every upstream-active service. Customers receive only
visible entries, and hidden identifiers are rejected at allocation endpoints.
"""
import re


class ServicePolicyError(ValueError):
    pass


def normalized_sid(value):
    sid = str(value or "").lower().strip()
    if not re.fullmatch(r"[a-z0-9_.-]{1,40}", sid):
        raise ServicePolicyError("Invalid service identifier")
    return sid


def hidden_set(config):
    raw = config.get("hidden_services", [])
    if not isinstance(raw, list):
        return set()
    return {str(s).lower() for s in raw if isinstance(s, str)}


def is_visible(config, sid, admin=False):
    if admin:
        return True
    try:
        return normalized_sid(sid) not in hidden_set(config)
    except ServicePolicyError:
        return False


def visible_services(services, config, admin=False):
    return {sid: ranges for sid, ranges in services.items()
            if is_visible(config, sid, admin)}


def set_visible(config, sid, visible):
    sid = normalized_sid(sid)
    hidden = hidden_set(config)
    if visible:
        hidden.discard(sid)
    else:
        hidden.add(sid)
    config["hidden_services"] = sorted(hidden)
    return config
