"""Per-user Azerbaijani / English UI language helpers."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

DEFAULT_LANGUAGE = "az"
SUPPORTED_LANGUAGES = {"az", "en"}

TEXT = {
    "az": {
        "choose_language": "🌐 Dili seçin",
        "language_saved": "✅ Dil Azərbaycan dili olaraq seçildi.",
        "get_number": "📞 NÖMRƏ AL",
        "active_numbers": "📋 AKTİV NÖMRƏLƏR",
        "search_otp": "🔍 OTP AXTAR",
        "get_2fa": "⚡ 2FA AL",
        "balance": "💰 BALANS",
        "profile": "👤 PROFİL",
        "refer": "👥 DƏVƏT ET VƏ QAZAN",
        "leaderboard": "🏆 LİDERLƏR",
        "support": "💬 DƏSTƏK",
        "admin": "⚙️ ADMİN PANEL",
        "mini_app": "🚀 MİNİ TƏTBİQ",
    },
    "en": {
        "choose_language": "🌐 Choose language",
        "language_saved": "✅ Language set to English.",
        "get_number": "📞 GET NUMBER",
        "active_numbers": "📋 ACTIVE NUMBERS",
        "search_otp": "🔍 SEARCH OTP",
        "get_2fa": "⚡ GET 2FA",
        "balance": "💰 BALANCE",
        "profile": "👤 PROFILE",
        "refer": "👥 REFER AND EARN",
        "leaderboard": "🏆 LEADERBOARD",
        "support": "💬 SUPPORT",
        "admin": "⚙️ ADMIN PANEL",
        "mini_app": "🚀 MINI APP",
    },
}

def normalize_language(value):
    value = str(value or "").lower()
    return value if value in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

def t(language, key):
    language = normalize_language(language)
    return TEXT.get(language, TEXT[DEFAULT_LANGUAGE]).get(key, key)

def language_keyboard():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇦🇿 Azərbaycan", callback_data="lang_az"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]])

def menu_labels(language):
    language = normalize_language(language)
    return {key: t(language, key) for key in (
        "get_number", "active_numbers", "search_otp", "get_2fa",
        "balance", "profile", "refer", "leaderboard", "support",
        "admin", "mini_app",
    )}
