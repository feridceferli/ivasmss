"""Manual card transfers with Telegram receipt file_ids, no payment gateway.

No credit happens until an administrator reviews a receipt. The request and
account ledger are backed up in the bot's existing PRIVATE repository.
"""
import json
import re
import secrets
from decimal import Decimal, InvalidOperation
from pathlib import Path
from data_storage import atomic_save


class TopupError(ValueError):
    pass


def parse_amount_cents(raw):
    try:
        value = Decimal(str(raw).replace(",", ".").strip())
        cents = value * 100
        if not cents.is_finite() or cents != cents.to_integral_value() or not 100 <= cents <= 1_000_000:
            raise TopupError("Məbləğ 1.00–10000.00 AZN arasında olmalıdır.")
        return int(cents)
    except (InvalidOperation, TypeError, ValueError) as exc:
        if isinstance(exc, TopupError):
            raise
        raise TopupError("Düzgün AZN məbləği yazın (məsələn 5.50).") from exc


class ManualTopups:
    def __init__(self, filename, on_change=lambda: None):
        self.filename = filename
        self.on_change = on_change

    def _load(self):
        try:
            data = json.loads(Path(self.filename).read_text(encoding="utf-8"))
        except FileNotFoundError:
            data = {"card": "", "contact": "", "requests": {}}
        if (not isinstance(data, dict) or
                not isinstance(data.get("requests", {}), dict)):
            raise TopupError("Ödəniş məlumatları oxunmur.")
        data.setdefault("requests", {})
        return data

    def _save(self, data):
        atomic_save(data, self.filename)
        self.on_change()

    def details(self):
        data = self._load()
        return {"card": data.get("card", ""), "contact": data.get("contact", "")}

    def set_card(self, value):
        text = str(value or "").strip()
        digits = re.sub(r"\s|-", "", text)
        if not re.fullmatch(r"\d{13,19}", digits):
            raise TopupError("Kart nömrəsi 13–19 rəqəm olmalıdır.")
        data = self._load()
        data["card"] = " ".join(digits[i:i+4] for i in range(0, len(digits), 4))
        self._save(data)

    def set_contact(self, value):
        text = str(value or "").strip()
        if text.startswith("@"):
            text = "https://t.me/" + text[1:]
        if not re.fullmatch(r"https://t\.me/[A-Za-z0-9_]{5,32}", text):
            raise TopupError("Telegram ünvanını @username və ya https://t.me/username şəklində yazın.")
        data = self._load()
        data["contact"] = text
        self._save(data)

    def submit(self, uid, amount_cents, file_id, kind):
        if (type(amount_cents) is not int or not 100 <= amount_cents <= 1_000_000
                or kind not in ("photo", "document") or not isinstance(file_id, str)
                or not 5 <= len(file_id) <= 500):
            raise TopupError("Çek məlumatları düzgün deyil.")
        data = self._load()
        uid = str(uid)
        pending = sum(1 for r in data["requests"].values()
                      if r.get("uid") == uid and r.get("status") == "pending")
        if pending >= 3:
            raise TopupError("Əvvəlki 3 ödəniş sorğunuzun yoxlanmasını gözləyin.")
        import time
        ident = secrets.token_hex(8)
        data["requests"][ident] = {
            "uid": uid, "cents": amount_cents, "file_id": file_id,
            "kind": kind, "status": "pending", "created_at": int(time.time()),
        }
        self._save(data)
        return ident

    def get(self, ident):
        if not re.fullmatch(r"[0-9a-f]{16}", str(ident)):
            raise TopupError("Yanlış ödəniş identifikatoru.")
        return self._load()["requests"].get(ident)

    def pending(self):
        return [(k, v) for k, v in self._load()["requests"].items()
                if v.get("status") == "pending"]

    def review(self, ident, approve, load_users, save_users):
        data = self._load()
        row = data["requests"].get(ident)
        if not row:
            raise TopupError("Sorğu tapılmadı.")
        if row.get("status") != "pending":
            raise TopupError("Bu sorğu artıq yoxlanılıb.")
        if approve:
            uid = row["uid"]
            users = load_users()
            user = users.get(uid)
            if not isinstance(user, dict):
                raise TopupError("İstifadəçi hesabı tapılmadı.")
            credits = user.setdefault("_manual_topup_credits", {})
            if not isinstance(credits, dict):
                raise TopupError("Kredit qeydləri zədələnib.")
            if ident not in credits:
                cents = round(float(user.get("balance", 0)) * 100)
                user["balance"] = round((cents + row["cents"]) / 100, 2)
                credits[ident] = row["cents"]
                save_users(users)
            row["status"] = "approved"
        else:
            row["status"] = "rejected"
        self._save(data)
        return {"uid": row["uid"], "cents": row["cents"], "status": row["status"]}
