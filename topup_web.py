"""Validate manual transfer amounts and receipt images submitted through the Mini App.

Never store card secrets or assume that a submitted receipt proves payment.
Only an administrator may approve a recorded request.
"""
import base64
import binascii
import re
from decimal import Decimal, InvalidOperation

from topup_ledger import TopupError


def parse_amount_cents(raw):
    if not isinstance(raw, str) or not re.fullmatch(r"(?:[1-9][0-9]{0,4})(?:\.[0-9]{1,2})?", raw.strip()):
        raise TopupError("invalid_amount", "Məbləğ 1.00–10000.00 AZN arasında olmalıdır.")
    try:
        cents = int(Decimal(raw.strip()) * 100)
    except (InvalidOperation, ValueError):
        raise TopupError("invalid_amount", "Məbləğ düzgün deyil.")
    if not 100 <= cents <= 1_000_000:
        raise TopupError("invalid_amount", "Məbləğ 1.00–10000.00 AZN arasında olmalıdır.")
    return cents


def decode_receipt(data_url):
    if not isinstance(data_url, str) or len(data_url) > 900_000:
        raise TopupError("invalid_receipt", "Çek şəkli çox böyükdür.")
    match = re.fullmatch(r"data:image/(jpeg|png);base64,([A-Za-z0-9+/]+={0,2})", data_url)
    if not match:
        raise TopupError("invalid_receipt", "JPEG və ya PNG şəkli göndərin.")
    try:
        content = base64.b64decode(match.group(2), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise TopupError("invalid_receipt", "Şəkil oxunmadı.") from exc
    if not 32 <= len(content) <= 650_000:
        raise TopupError("invalid_receipt", "Çek şəkli 650 KB-dan kiçik olmalıdır.")
    suffix = match.group(1)
    if suffix == "jpeg" and not (content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9")):
        raise TopupError("invalid_receipt", "JPEG şəkli düzgün deyil.")
    if suffix == "png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise TopupError("invalid_receipt", "PNG şəkli düzgün deyil.")
    return content, ("receipt.jpg" if suffix == "jpeg" else "receipt.png")
