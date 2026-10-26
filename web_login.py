"""Short-lived, Telegram-confirmed website account pairing and signed sessions.

No bot token or Telegram login payload is exposed to browsers. Pending challenges
live only in this application instance; sessions are HMAC authenticated and expire.
"""
import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time


def _encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class WebsiteLogin:
    PAIR_TTL = 600
    SESSION_TTL = 7 * 86400
    MAX_PENDING = 512

    def __init__(self, bot_token):
        self._key = hashlib.sha256(("website-login-v1:" + bot_token).encode()).digest()
        self.pending = {}

    def _cleanup(self):
        now = time.time()
        for token, entry in list(self.pending.items()):
            if now - entry["created"] > self.PAIR_TTL:
                self.pending.pop(token, None)

    def begin(self):
        self._cleanup()
        if len(self.pending) >= self.MAX_PENDING:
            raise RuntimeError("too_many_pending_logins")
        token, flow = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
        self.pending[token] = {
            "created": time.time(),
            "flow_digest": hashlib.sha256(flow.encode()).digest(),
            "user": None,
        }
        return token, flow

    def can_confirm(self, token):
        self._cleanup()
        entry = self.pending.get(token)
        return bool(entry and entry["user"] is None)

    @staticmethod
    def _profile(user):
        uid = int(user["id"])
        if uid <= 0:
            raise ValueError("invalid_user_id")
        return {
            "id": uid,
            "first_name": str(user.get("first_name") or "")[:100],
            "last_name": str(user.get("last_name") or "")[:100],
            "username": str(user.get("username") or "")[:64],
        }

    def confirm(self, token, telegram_user):
        if not self.can_confirm(token):
            return False
        self.pending[token]["user"] = self._profile(telegram_user)
        return True

    def consume(self, token, flow):
        self._cleanup()
        entry = self.pending.get(token)
        if not entry or not flow:
            return "expired", None
        if not hmac.compare_digest(entry["flow_digest"], hashlib.sha256(flow.encode()).digest()):
            return "forbidden", None
        if entry["user"] is None:
            return "pending", None
        self.pending.pop(token, None)
        return "connected", entry["user"]

    def make_session(self, user, now=None):
        now = int(time.time() if now is None else now)
        body = self._profile(user)
        body.update({"v": 1, "iat": now, "exp": now + self.SESSION_TTL})
        payload = _encode(json.dumps(body, separators=(",", ":"), sort_keys=True).encode())
        signature = _encode(hmac.new(self._key, payload.encode(), hashlib.sha256).digest())
        return payload + "." + signature

    def verify_session(self, token, now=None):
        if not token or len(token) > 4096 or token.count(".") != 1:
            return None
        try:
            payload, signature = token.split(".", 1)
            expected = _encode(hmac.new(self._key, payload.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                return None
            body = json.loads(_decode(payload))
            now = int(time.time() if now is None else now)
            if body.get("v") != 1 or not (now - self.SESSION_TTL <= body.get("iat", 0) <= now + 60):
                return None
            if not (now < body.get("exp", 0) <= now + self.SESSION_TTL + 60):
                return None
            return self._profile(body)
        except (ValueError, TypeError, UnicodeDecodeError, KeyError, OverflowError, binascii.Error):
            return None
