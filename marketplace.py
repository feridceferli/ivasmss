"""Admin-published provider services and durable, idempotent rental refunds.

The provider's liveaccess lists *ranges*, not a count of purchasable numbers.
We never claim a number exists before /getnum actually supplies it.
"""
import re
import time
from pathlib import Path
from data_storage import atomic_save
import json


def _rid(value):
    return re.sub(r"[^0-9]", "", str(value))


def _read(path, default):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    if not isinstance(value, dict):
        raise ValueError("Invalid marketplace data: " + str(path))
    return value


class MarketCatalog:
    def __init__(self, filename, on_change=lambda: None):
        self.filename = filename
        self.on_change = on_change

    def _published(self):
        payload = _read(self.filename, {})
        return {
            service.lower(): {_rid(r) for r in ranges}
            for service, ranges in payload.items()
            if isinstance(service, str) and isinstance(ranges, list)
        }

    def allowed(self, service, rid):
        return _rid(rid) in self._published().get(str(service).lower(), set())

    def public(self, upstream):
        approved = self._published()
        return {
            name: [rid for rid in ranges if _rid(rid) in approved.get(str(name).lower(), set())]
            for name, ranges in upstream.items()
            if any(_rid(rid) in approved.get(str(name).lower(), set()) for rid in ranges)
        }

    def toggle(self, service, rid, upstream):
        service = str(service).lower()
        rid = _rid(rid)
        if (service not in upstream or rid not in [_rid(r) for r in upstream[service]]
                or not re.fullmatch(r"\d{1,10}", rid)):
            raise ValueError("Range is not advertised by the provider")
        config = _read(self.filename, {})
        current = config.setdefault(service, [])
        if rid in current:
            current.remove(rid)
            enabled = False
        else:
            current.append(rid)
            enabled = True
        atomic_save(config, self.filename)
        self.on_change()
        return enabled


class RentalLedger:
    """A local journal included in the bot's private GitHub backup.

    The user balance's _rental_refunds record is the idempotency marker:
    persist that marker and the money in ONE users.json write before
    marking the journal row refunded.
    """
    def __init__(self, filename, on_change=lambda: None):
        self.filename = filename
        self.on_change = on_change

    def _all(self):
        return _read(self.filename, {})

    def record(self, lease_id, uid, number, cents, *, now=None):
        if not re.fullmatch(r"[0-9a-f]{16}", str(lease_id)):
            raise ValueError("Invalid lease ID")
        if type(cents) is not int or cents < 0:
            raise ValueError("Invalid rental charge")
        data = self._all()
        if lease_id in data:
            raise ValueError("Duplicate rental lease")
        start = int(time.time() if now is None else now)
        data[lease_id] = {
            "uid": str(uid), "number": str(number), "cents": cents,
            "created_at": start, "expires_at": start + 180,
            "status": "pending",
        }
        atomic_save(data, self.filename)
        self.on_change()

    def abort(self, lease_id):
        """End an uncommitted allocation; no expiry refund is due."""
        data = self._all()
        row = data.get(str(lease_id))
        if not row or row.get("status") != "pending":
            return False
        row["status"] = "aborted"
        atomic_save(data, self.filename)
        self.on_change()
        return True

    def received(self, lease_id, *, now=None):
        data = self._all()
        row = data.get(str(lease_id))
        stamp = int(time.time() if now is None else now)
        if not row or row["status"] != "pending" or stamp > row["expires_at"]:
            return False
        row["status"] = "received"
        atomic_save(data, self.filename)
        self.on_change()
        return True

    def settle_due(self, load_users, save_users, *, now=None):
        stamp = int(time.time() if now is None else now)
        entries = self._all()
        due = [(key, rec) for key, rec in entries.items()
               if rec.get("status") == "pending" and rec.get("expires_at", 0) <= stamp]
        if not due:
            return []
        users = load_users()
        refunded = []
        touched = False
        for key, row in due:
            uid = str(row["uid"])
            record = users.get(uid)
            if not isinstance(record, dict):
                # Fail closed rather than silently discarding a paid refund.
                raise RuntimeError("Refund account missing: " + uid)
            seen = record.setdefault("_rental_refunds", {})
            if not isinstance(seen, dict):
                raise RuntimeError("Invalid refund idempotency marker")
            cents = int(row["cents"])
            if cents and key not in seen:
                balance = round(float(record.get("balance", 0.0)) * 100)
                record["balance"] = round((balance + cents) / 100, 2)
                seen[key] = cents
                touched = True
            row["status"] = "refunded"
            refunded.append(key)
        if touched:
            save_users(users)
        atomic_save(entries, self.filename)
        self.on_change()
        return refunded

    def active_count(self, uid, *, now=None):
        stamp = int(time.time() if now is None else now)
        return sum(1 for r in self._all().values()
                   if r.get("uid") == str(uid) and r.get("status") == "pending"
                   and r.get("expires_at", 0) > stamp)
