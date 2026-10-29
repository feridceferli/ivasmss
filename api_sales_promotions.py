"""Public API-sale group digest. Do not include endpoint URLs or credentials.

Promotions are derived solely from the public product metadata of an
administrator-visible catalog. No purchase details or user data is included.
"""
import html
import math
import re

INTERVAL_SECONDS = 15 * 60
MAX_MESSAGE = 3900
MAX_PRODUCTS = 15


def safe_promotion_state(catalog):
    raw = catalog.get("promotions")
    raw = raw if isinstance(raw, dict) else {}
    stamp = raw.get("last_sent_at", 0)
    if not isinstance(stamp, (float, int)) or isinstance(stamp, bool) or not math.isfinite(stamp):
        stamp = 0
    return {"enabled": raw.get("enabled") is not False, "interval_minutes": 15,
            "last_sent_at": max(0, float(stamp))}


def active_public_products(catalog):
    if not isinstance(catalog, dict) or not catalog.get("visible"):
        return []
    items = catalog.get("items")
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if not isinstance(item, dict) or item.get("enabled") is not True:
            continue
        # Whitelist public metadata explicitly. Never read secret or endpoint.
        cents = item.get("price_cents")
        if type(cents) is not int or cents <= 0:
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        result.append({"name": name, "description": str(item.get("description") or ""),
                       "price_cents": cents})
    return result


def promotion_due(catalog, now):
    state = safe_promotion_state(catalog)
    return (state["enabled"] and bool(active_public_products(catalog))
            and now >= state["last_sent_at"] + INTERVAL_SECONDS)


def _safe_description(value, limit=220):
    """Only public, credential-free marketing metadata goes into the group."""
    s = str(value or "").strip()
    # Product descriptions are public, but defensively redact accidental
    # credentials and any URLs included by the administrator.
    s = re.sub(r"(?i)(?:https?://|www\.)[^\s]+", "[keçid gizlidir]", s)
    s = re.sub(r"(?i)\b(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*[^\s,;]+",
               r"\1: [gizlidir]", s)
    s = re.sub(r"\s+", " ", s)
    return html.escape(s[:limit])


def build_group_digest(catalog, purchase_url=""):
    products = active_public_products(catalog)
    if not products:
        return ""
    header = (
        "🛒 <b>AZE SMS PANEL — API SATIŞI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 <b>API Satışı bölməmiz aktivdir!</b>\n\n"
        "📢 Xidmətlər üçün mövcud API təkliflərini şəxsi hesabınızın "
        "balansı ilə əldə edə bilərsiniz.\n"
        f"📦 <b>Satışda olan API sayı:</b> {len(products)}\n\n"
        "📋 <b>AKTİV API-LƏR VƏ QİYMƏTLƏR</b>\n"
    )
    parts = [header]
    chosen = 0
    for product in products[:MAX_PRODUCTS]:
        name = html.escape(product["name"][:80])
        desc = _safe_description(product["description"])
        offer = (
            f"\n<b>{chosen + 1}. {name}</b>\n"
            + (f"📝 {desc}\n" if desc else "")
            + f"💰 <b>Qiymət:</b> {product['price_cents']/100:.2f} AZN\n"
            + "✅ <b>Status:</b> Satışdadır\n"
        )
        if len("".join(parts)) + len(offer) > MAX_MESSAGE - 880:
            break
        parts.append(offer)
        chosen += 1
    if len(products) > chosen:
        parts.append(f"\n➕ Daha {len(products) - chosen} API üçün satış bölməsinə baxın.\n")
    parts.append(
        "\n💳 <b>API-ni necə almaq olar?</b>\n"
        "1️⃣ Telegram botunda /start yazın və Mini App-i açın.\n"
        "2️⃣ <b>🛒 API Satışı</b> bölməsinə keçin.\n"
        "3️⃣ API-ni seçin, qiyməti və balansınızı yoxlayın.\n"
        "4️⃣ Alışı təsdiqləyin — məbləğ balansınızdan tutulur.\n"
        "5️⃣ Alınan API məlumatlarını <b>📦 Aldığım API-lər</b> bölməsində görün.\n\n"
        "🔒 <i>API açarları və şəxsi məlumatlar qrupda paylaşılmır. "
        "Açar yalnız satın alan istifadəçiyə açılır.</i>\n"
    )
    if purchase_url.startswith("https://"):
        parts.append("\n🌐 <b>Sayt / Mini App:</b> " + html.escape(purchase_url[:300]))
    message = "".join(parts)
    return message[:MAX_MESSAGE]
