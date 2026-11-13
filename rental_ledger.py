"""Persistent, idempotent three-minute number-rental accounting.

The rental journal lives INSIDE users.json beside the balance, so one atomic
file replacement changes both balance and rental status. The caller must save
the resulting users mapping before awaiting any other work. A persistent
DB_FOLDER or independent private backup is still required on Render.
"""
import time


class RentalError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


RENTAL_SECONDS = 180
MAX_ACTIVE_RENTALS = 3


def _account(users, uid):
    account = users.get(str(uid))
    if not isinstance(account, dict):
        raise RentalError("account_missing", "İstifadəçi hesabı tapılmadı.")
    journal = account.setdefault("rental_orders", {})
    if not isinstance(journal, dict):
        raise RentalError("invalid_journal", "Sifariş tarixçəsi zədələnib.")
    return account, journal


def reserve(users, uid, order_id, cost_cents, now=None):
    """Reserve a slot and charge once. Save users.json immediately afterwards."""
    now = time.time() if now is None else float(now)
    if not isinstance(cost_cents, int) or isinstance(cost_cents, bool) or cost_cents < 0:
        raise RentalError("invalid_price", "Nömrə qiyməti düzgün deyil.")
    account, journal = _account(users, uid)
    if order_id in journal:
        raise RentalError("duplicate_order", "Sifariş artıq mövcuddur.")
    live = sum(
        1 for item in journal.values()
        if isinstance(item, dict) and item.get("status") == "pending"
        and float(item.get("expires_at", 0)) > now
    )
    if live >= MAX_ACTIVE_RENTALS:
        raise RentalError(
            "number_limit", "Eyni anda ən çox 3 aktiv nömrə götürə bilərsiniz.")
    balance_cents = round(float(account.get("balance", 0)) * 100)
    if balance_cents < cost_cents:
        raise RentalError("insufficient_balance", "Balans kifayət etmir.")
    account["balance"] = round((balance_cents - cost_cents) / 100, 2)
    journal[order_id] = {
        "number": "", "charge_cents": cost_cents, "status": "pending",
        "created_at": now, "expires_at": now + RENTAL_SECONDS,
    }
    return journal[order_id]


def set_number(users, uid, order_id, number):
    """Associate a reserved rental with its allocated number."""
    _, journal = _account(users, uid)
    order = journal.get(order_id)
    if not isinstance(order, dict) or order.get("status") != "pending":
        raise RentalError("not_pending", "Sifariş artıq aktiv deyil.")
    if order.get("number") and order["number"] != number:
        raise RentalError("number_mismatch", "Sifarişin nömrəsi fərqlidir.")
    order["number"] = str(number)


def record_sms(users, uid, order_id, number, now=None):
    """Complete only an owned, in-time rental; never credit a bonus."""
    now = time.time() if now is None else float(now)
    _, journal = _account(users, uid)
    order = journal.get(order_id)
    if (not isinstance(order, dict) or order.get("status") != "pending"
            or order.get("number") != str(number)
            or float(order.get("expires_at", 0)) <= now):
        return False
    order["status"] = "sms_received"
    order["settled_at"] = now
    return True


def refund(users, uid, order_id, status="refunded", now=None):
    """Return reserved money at most once, updating balance in same file."""
    now = time.time() if now is None else float(now)
    account, journal = _account(users, uid)
    order = journal.get(order_id)
    if not isinstance(order, dict) or order.get("status") != "pending":
        return False
    cost = int(order.get("charge_cents", 0))
    account["balance"] = round((round(float(account.get("balance", 0)) * 100) + cost) / 100, 2)
    order["status"] = status
    order["settled_at"] = now
    return True


def refund_expired(users, now=None):
    """Refund absent SMS after 180 seconds. Call on startup and in polling loop."""
    now = time.time() if now is None else float(now)
    refunded = []
    for uid, account in list(users.items()):
        if not isinstance(account, dict):
            continue
        journal = account.get("rental_orders", {})
        if not isinstance(journal, dict):
            continue
        for oid, order in list(journal.items()):
            if (isinstance(order, dict) and order.get("status") == "pending"
                    and float(order.get("expires_at", now + 1)) <= now):
                if refund(users, uid, oid, now=now):
                    refunded.append((uid, oid))
    return refunded
