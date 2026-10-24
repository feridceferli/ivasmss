"""Server-authoritative AZN pricing for number allocations.

Prices are stored as integer qəpik; client labels are never trusted.
International calling codes shared by multiple regions cannot identify a
specific region from the provider range alone. Require a range override if
those regions have different prices.
"""
import re
from decimal import Decimal, InvalidOperation
from world_country_codes import WORLD_COUNTRIES

MAX_CENTS = 1_000_000  # 10,000 AZN
DEFAULT_PRICES = {
    "currency": "AZN",
    "default": {"cents": 0, "free": True},
    "country": {},  # ISO alpha-2 -> rule
    "range": {},  # exact provider range -> rule
}
AZ_DEFAULT = {"cents": 1000, "free": False}


class PricingError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def price_rule(price, free):
    if type(free) is not bool:
        raise PricingError("invalid_price", "Pulsuz seçimi düzgün deyil.")
    if free:
        return {"cents": 0, "free": True}
    if isinstance(price, bool) or price is None:
        raise PricingError("invalid_price", "Qiymət düzgün deyil.")
    try:
        value = Decimal(str(price).strip())
    except (InvalidOperation, ValueError):
        raise PricingError("invalid_price", "AZN qiymətini düzgün daxil edin.") from None
    cents = value * 100
    if (not cents.is_finite() or cents != cents.to_integral_value()
            or not (1 <= cents <= MAX_CENTS)):
        raise PricingError("invalid_price", "Qiymət 0.01–10000 AZN və maksimum 2 onluq olmalıdır.")
    return {"cents": int(cents), "free": False}


def initial_prices():
    return {"currency": "AZN", "default": {"cents": 0, "free": True},
            "country": {}, "range": {}}


def effective_rule(iso, settings):
    return settings.get("country", {}).get(iso) or (
        AZ_DEFAULT if iso == "AZ" else settings.get("default", DEFAULT_PRICES["default"])
    )


def quote_range(rid, settings, country_iso=None):
    rid = re.sub(r"\D", "", str(rid or ""))
    if not re.fullmatch(r"\d{1,10}", rid):
        raise PricingError("invalid_range", "Range düzgün deyil.")
    matching_codes = [code for _, _, code in WORLD_COUNTRIES if rid.startswith(code)]
    if not matching_codes:
        raise PricingError("unknown_country", "Bu range üçün ölkə müəyyən edilmir.")
    code = max(matching_codes, key=len)
    regions = [iso for iso, _, prefix in WORLD_COUNTRIES if prefix == code]
    chosen = str(country_iso or "").upper().strip()
    if chosen and chosen not in regions:
        raise PricingError("country_mismatch", "Seçilmiş ölkə bu telefon koduna uyğun deyil.")
    override = settings.get("range", {}).get(rid)
    if override is not None:
        rule = override
        source = "range"
    else:
        signatures = {(effective_rule(iso, settings)["cents"],
                       effective_rule(iso, settings)["free"]) for iso in regions}
        if len(signatures) != 1:
            raise PricingError(
                "ambiguous_country_price",
                "Bu +kod bir neçə ölkəyə aiddir və qiymətlər fərqlidir. Admin həmin range üçün ayrıca qiymət təyin etməlidir.",
            )
        rule = effective_rule(regions[0], settings)
        source = "country" if any(iso in settings.get("country", {}) or iso == "AZ" for iso in regions) else "default"
    cents = int(rule["cents"])
    return {"currency": "AZN", "cents": cents, "price": f"{cents / 100:.2f}",
            "free": bool(rule["free"]), "source": source, "prefix": code,
            "country_iso": chosen or (regions[0] if len(regions) == 1 else None),
            "shared": len(regions) > 1}


def valid_country(iso):
    return bool(re.fullmatch(r"[A-Z]{2}", iso)) and any(row[0] == iso for row in WORLD_COUNTRIES)


def valid_range(rid):
    return bool(re.fullmatch(r"\d{1,10}", rid or ""))
