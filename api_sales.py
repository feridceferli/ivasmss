"""Private API product catalog and one-time account purchases.

Never include credentials in public catalogs, messages to groups, or source files.
Catalog and user records must be backed up only to an access-restricted store.
"""
import copy
import json
import re
import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

_ID = re.compile(r"^[a-f0-9]{12}$")


class ApiSalesError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def price_to_cents(value):
    try:
        decimal = Decimal(str(value))
        cents = decimal * 100
        if not cents.is_finite() or cents != cents.to_integral_value() or not (1 <= cents <= 1_000_000):
            raise ApiSalesError("invalid_price")
        return int(cents)
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        raise ApiSalesError("invalid_price")


def _bounded(value, maximum, required=False):
    if not isinstance(value, str):
        raise ApiSalesError("invalid_field")
    value = value.strip()
    if len(value) > maximum or (required and not value):
        raise ApiSalesError("invalid_field")
    return value


def _url(value):
    value = _bounded(value, 600)
    if value:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ApiSalesError("invalid_endpoint")
    return value


class ApiSalesStore:
    def __init__(self, catalog_file, users_file, read_users, write_data):
        self.catalog_file = Path(catalog_file)
        self.users_file = Path(users_file)
        self.read_users = read_users
        self.write_data = write_data
        self.lock = threading.RLock()

    def _read(self):
        if not self.catalog_file.exists():
            return {"visible": False, "items": []}
        data = json.loads(self.catalog_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("items"), list):
            raise ApiSalesError("catalog_unavailable")
        return data

    def _write(self, data):
        self.write_data(data, self.catalog_file)

    @staticmethod
    def _public(item):
        return {
            "id": item["id"], "name": item["name"],
            "description": item["description"],
            "price_cents": item["price_cents"], "enabled": item["enabled"],
        }

    def list_products(self, uid, admin=False):
        with self.lock:
            data = self._read()
            users = self.read_users(self.users_file)
            mine = users.get(str(uid), {}).get("api_purchases", {})
            if not isinstance(mine, dict):
                mine = {}
            visible = bool(data.get("visible"))
            products = []
            for item in data["items"]:
                if admin or (visible and item.get("enabled")):
                    row = self._public(item)
                    if admin:
                        row["has_secret"] = bool(item.get("secret"))
                        row["endpoint"] = item["endpoint"]
                    products.append(row)
            owned = []
            for purchase in mine.values():
                if isinstance(purchase, dict):
                    owned.append(copy.deepcopy(purchase))
            return {"visible": visible, "products": products, "owned": owned}

    def buy(self, uid, product_id):
        """Synchronous transaction: no await between checking balance and saving."""
        if not isinstance(product_id, str) or not _ID.fullmatch(product_id):
            raise ApiSalesError("invalid_product")
        with self.lock:
            data = self._read()
            item = next((p for p in data["items"] if p["id"] == product_id), None)
            if not data.get("visible") or not item or not item["enabled"]:
                raise ApiSalesError("unavailable")
            users = self.read_users(self.users_file)
            user = users.get(str(uid))
            if not isinstance(user, dict):
                raise ApiSalesError("account_not_found")
            purchases = user.setdefault("api_purchases", {})
            if not isinstance(purchases, dict):
                raise ApiSalesError("corrupt_purchases")
            if product_id in purchases:
                return copy.deepcopy(purchases[product_id]), False
            cost = int(item["price_cents"])
            balance = price_to_balance_cents(user.get("balance", 0))
            if balance < cost:
                raise ApiSalesError("insufficient_balance")
            if not item.get("secret"):
                raise ApiSalesError("unavailable")
            purchase = {
                "id": product_id, "name": item["name"],
                "description": item["description"], "endpoint": item["endpoint"],
                "secret": item["secret"], "price_cents": cost,
                "purchased_at": datetime.now(timezone.utc).isoformat(),
            }
            user["balance"] = (balance - cost) / 100
            purchases[product_id] = purchase
            self.write_data(users, self.users_file)
            return copy.deepcopy(purchase), True

    def upsert(self, fields):
        with self.lock:
            data = self._read()
            ident = str(fields.get("id") or "").strip()
            item = next((p for p in data["items"] if p["id"] == ident), None) if ident else None
            if ident and (not _ID.fullmatch(ident) or item is None):
                raise ApiSalesError("invalid_product")
            name = _bounded(fields.get("name"), 80, True)
            description = _bounded(fields.get("description", ""), 600)
            endpoint = _url(fields.get("endpoint", ""))
            secret = _bounded(fields.get("secret", ""), 4000)
            if item and not secret:
                secret = item["secret"]
            if not secret:
                raise ApiSalesError("missing_secret")
            cents = price_to_cents(fields.get("price"))
            if len(data["items"]) >= 100 and not item:
                raise ApiSalesError("catalog_limit")
            if not item:
                item = {"id": uuid.uuid4().hex[:12]}
                data["items"].append(item)
            item.update(name=name, description=description, endpoint=endpoint,
                        secret=secret, price_cents=cents, enabled=bool(item.get("enabled", True)))
            self._write(data)
            return self._public(item)

    def toggle_section(self, visible):
        if type(visible) is not bool:
            raise ApiSalesError("invalid_field")
        with self.lock:
            data = self._read()
            data["visible"] = visible
            self._write(data)
        return visible

    def toggle_product(self, product_id, enabled):
        if type(enabled) is not bool:
            raise ApiSalesError("invalid_field")
        with self.lock:
            data = self._read()
            item = next((p for p in data["items"] if p["id"] == product_id), None)
            if not item:
                raise ApiSalesError("invalid_product")
            item["enabled"] = enabled
            self._write(data)
        return enabled

    def delete(self, product_id):
        with self.lock:
            data = self._read()
            before = len(data["items"])
            data["items"] = [p for p in data["items"] if p["id"] != product_id]
            if before == len(data["items"]):
                raise ApiSalesError("invalid_product")
            self._write(data)
        # Buyer receipts remain in their account even after a listing is deleted.


def price_to_balance_cents(value):
    try:
        cents = Decimal(str(value)) * 100
        if not cents.is_finite() or cents < 0 or cents != cents.to_integral_value():
            raise ApiSalesError("invalid_balance")
        return int(cents)
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        raise ApiSalesError("invalid_balance")
