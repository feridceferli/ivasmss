"""Short-lived, user-bound phone choices from a one-number-per-call provider.

The provider's /getnum POST allocates immediately, not a read-only preview.
Unused options cannot be released without a documented provider release API.
No option creates a bot order, number archive row, or user-side charge until
the authenticated user explicitly selects it.
"""
import secrets
import time


class NumberChoiceStore:
    TTL = 90
    MAX_CHOICES = 5
    COOLDOWN = 30

    def __init__(self, clock=None):
        self.clock = clock or time.monotonic
        self._offers = {}
        self._last = {}

    def _purge(self):
        now = self.clock()
        for key in list(self._offers):
            if self._offers[key]["expires"] <= now:
                del self._offers[key]
        for key in list(self._last):
            if self._last[key] + self.COOLDOWN <= now:
                del self._last[key]

    def can_request(self, uid):
        self._purge()
        return self.clock() - self._last.get(str(uid), -1e20) >= self.COOLDOWN

    def reserve_request(self, uid, *, exempt=False):
        """Only non-admin users have a 30-second preview cooldown.

        Caller must verify admin privileges on the server; never trust a
        flag from a client request. The purchase lock still serializes calls.
        """
        self._purge()
        if exempt:
            return True
        if not self.can_request(uid):
            return False
        self._last[str(uid)] = self.clock()
        return True

    def create(self, uid, rid, service, iso, numbers):
        self._purge()
        seen = set()
        clean = []
        for entry in numbers:
            number = str(entry.get("number") or "").strip()
            digits = number.lstrip("+")
            if (digits.isdecimal() and 4 <= len(digits) <= 15
                    and digits.startswith(str(rid)) and digits not in seen):
                seen.add(digits)
                clean.append({"number": "+" + digits,
                              "country": str(entry.get("country") or "")[:80]})
            if len(clean) >= self.MAX_CHOICES:
                break
        if not clean:
            return None
        token = secrets.token_urlsafe(12)
        uid = str(uid)
        # Invalidate the user's earlier choices to prevent double-allocation.
        for previous in list(self._offers):
            if self._offers[previous]["uid"] == uid:
                del self._offers[previous]
        self._offers[token] = {
            "uid": uid, "rid": str(rid), "service": str(service)[:35],
            "iso": str(iso)[:4], "numbers": clean,
            "expires": self.clock() + self.TTL,
        }
        return {"token": token, "numbers": list(clean), "expires_in": self.TTL}

    def get(self, uid, token, index):
        self._purge()
        offer = self._offers.get(str(token))
        if (not offer or offer["uid"] != str(uid)
                or type(index) is not int or not 0 <= index < len(offer["numbers"])):
            return None
        return {
            "rid": offer["rid"], "service": offer["service"],
            "iso": offer["iso"], **offer["numbers"][index]
        }

    def consume(self, uid, token, index):
        item = self.get(uid, token, index)
        if item is None:
            return None
        self._offers.pop(str(token), None)
        return item


number_choices = NumberChoiceStore()
