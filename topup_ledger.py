"""Manual bank-transfer top-ups with an atomic one-time credit journal.

These requests live in users.json (the same atomic snapshot as balances).
Only a Telegram administrator may change a request to approved/rejected.
No card credentials or payment card verification data are collected here.
"""
import time


class TopupError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def create_request(users, uid, request_id, amount_cents, photo_file_id, now=None):
    now = time.time() if now is None else float(now)
    if (type(amount_cents) is not int or not 100 <= amount_cents <= 1000000):
        raise TopupError("invalid_amount", "Məbləğ 1–10000 AZN arasında olmalıdır.")
    if (not isinstance(photo_file_id, str) or not 10 <= len(photo_file_id) <= 300
            or not all(char.isalnum() or char in "_-" for char in photo_file_id)):
        raise TopupError("invalid_receipt", "Ödəniş çeki düzgün deyil.")
    user = users.get(str(uid))
    if not isinstance(user, dict):
        raise TopupError("no_user", "İstifadəçi tapılmadı.")
    requests = user.setdefault("topup_requests", {})
    if not isinstance(requests, dict):
        raise TopupError("invalid_requests", "Ödəniş tarixçəsi zədələnib.")
    if request_id in requests:
        raise TopupError("duplicate_request", "Bu sorğu artıq mövcuddur.")
    if sum(1 for row in requests.values()
           if isinstance(row, dict) and row.get("status") == "pending") >= 3:
        raise TopupError("pending_limit", "Əvvəlki 3 ödəniş sorğunuz yoxlanmalıdır.")
    requests[request_id] = {
        "amount_cents": amount_cents,
        "file_id": photo_file_id,
        "status": "pending",
        "created_at": now,
    }
    return requests[request_id]


def resolve_request(users, uid, request_id, approve, admin_id, now=None):
    """Mutate both request state and account balance before one atomic save."""
    now = time.time() if now is None else float(now)
    user = users.get(str(uid))
    if not isinstance(user, dict):
        raise TopupError("not_found", "Ödəniş sorğusu tapılmadı.")
    req = user.get("topup_requests", {}).get(request_id)
    if not isinstance(req, dict):
        raise TopupError("not_found", "Ödəniş sorğusu tapılmadı.")
    if req.get("status") != "pending":
        raise TopupError("already_reviewed", "Sorğu artıq təsdiqlənib və ya rədd edilib.")
    if approve:
        amount = int(req["amount_cents"])
        old = round(float(user.get("balance", 0)) * 100)
        user["balance"] = round((old + amount) / 100, 2)
    req["status"] = "approved" if approve else "rejected"
    req["reviewed_by"] = str(admin_id)
    req["reviewed_at"] = now
    return req


def pending_requests(users, limit=20):
    rows = []
    for uid, account in users.items():
        if not isinstance(account, dict):
            continue
        for oid, row in account.get("topup_requests", {}).items():
            if isinstance(row, dict) and row.get("status") == "pending":
                rows.append((str(uid), str(oid), row))
    rows.sort(key=lambda item: float(item[2].get("created_at", 0)), reverse=True)
    return rows[:limit]
