"""Per-user Azerbaijani / English / Turkish UI language helpers."""
from telegram import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup

DEFAULT_LANGUAGE = "az"
SUPPORTED_LANGUAGES = {"az", "en", "tr"}

TEXT = {
    "az": {
        "all_countries": "🌍 Bütün ölkələr",
        "choose_country": "Ölkə seçin:",
        "no_countries": "Hazırda heç bir ölkə mövcud deyil.",
        "countries_back": "🔙 Əsas menyu",
        "copy_code": "📋 Kodu kopyala",
        "choose_language": "🌐 Dili seçin",
        "language_saved": "✅ Dil Azərbaycan dili olaraq seçildi.",
        "membership_required": "🔐 Botdan istifadə etmək üçün aşağıdakı kanal və qruplara qoşulun, sonra «✅ Yoxla» düyməsinə basın.",
        "membership_failed": "❌ <b>Üzvlük təsdiqlənmədi!</b>\n\nAşağıdakı kanal və qruplara qoşulmamısınız:",
        "membership_retry": "Qoşulduqdan sonra «✅ Yoxla» düyməsinə yenidən basın.",
        "membership_unavailable": "⚠️ <b>Üzvlüyü yoxlamaq mümkün olmadı.</b>\n\nBir az sonra yenidən cəhd edin və ya dəstəyə yazın. Yoxlanılmayan kanallar:",
        "membership_verified": "✅ Üzvlük təsdiqləndi!\n\nİndi botdan istifadə edə bilərsiniz.",
        "membership_no_channels": "✅ Yoxlanılacaq kanal yoxdur. Botdan istifadə edə bilərsiniz.",
        "membership_chat_unresolved": "❌ Kanalın chat ID-si müəyyən edilmədi.",
        "membership_chat_missing": "❌ Kanalın chat ID-si təyin edilməyib.",
        "membership_check_error": "⚠️ Kanal üzvlüyünü yoxlamaq mümkün olmadı.",
        "verify_button": "✅ Yoxla",
        "join_channel": "📢 Kanala qoşul",
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
    "tr": {
        "all_countries": "🌍 Tüm ülkeler",
        "choose_country": "Ülke seçin:",
        "no_countries": "Şu anda kullanılabilir ülke yok.",
        "countries_back": "🔙 Ana menü",
        "copy_code": "📋 Kodu kopyala",
        "choose_language": "🌐 Dil seçin",
        "language_saved": "✅ Dil Türkçe olarak seçildi.",
        "membership_required": "🔐 Botu kullanmak için aşağıdaki kanal ve gruplara katılın, ardından «✅ Kontrol et» düğmesine basın.",
        "membership_failed": "❌ <b>Üyelik doğrulanamadı!</b>\n\nAşağıdaki kanal ve gruplara katılmadınız:",
        "membership_retry": "Katıldıktan sonra «✅ Kontrol et» düğmesine tekrar basın.",
        "membership_unavailable": "⚠️ <b>Üyelik kontrol edilemedi.</b>\n\nBiraz sonra tekrar deneyin veya desteğe yazın. Kontrol edilemeyen kanallar:",
        "membership_verified": "✅ Üyelik doğrulandı!\n\nArtık botu kullanabilirsiniz.",
        "membership_no_channels": "✅ Kontrol edilecek kanal yok. Botu kullanabilirsiniz.",
        "membership_chat_unresolved": "❌ Kanalın sohbet kimliği bulunamadı.",
        "membership_chat_missing": "❌ Kanalın sohbet kimliği ayarlanmamış.",
        "membership_check_error": "⚠️ Kanal üyeliği kontrol edilemedi.",
        "verify_button": "✅ Kontrol et",
        "join_channel": "📢 Kanala katıl",
        "get_number": "📞 NUMARA AL",
        "active_numbers": "📋 AKTİF NUMARALAR",
        "search_otp": "🔍 OTP ARA",
        "get_2fa": "⚡ 2FA AL",
        "balance": "💰 BAKİYE",
        "profile": "👤 PROFİL",
        "refer": "👥 DAVET ET VE KAZAN",
        "leaderboard": "🏆 LİDERLER",
        "support": "💬 DESTEK",
        "admin": "⚙️ ADMİN PANELİ",
        "mini_app": "🚀 MİNİ UYGULAMA",
    },
    "en": {
        "all_countries": "🌍 All countries",
        "choose_country": "Choose a country:",
        "no_countries": "No countries are currently available.",
        "countries_back": "🔙 Main menu",
        "copy_code": "📋 Copy code",
        "choose_language": "🌐 Choose language",
        "language_saved": "✅ Language set to English.",
        "membership_required": "🔐 Join the channels and groups below to use the bot, then press «✅ Verify».",
        "membership_failed": "❌ <b>Membership not verified!</b>\n\nYou have not joined the following channels or groups:",
        "membership_retry": "After joining, press «✅ Verify» again.",
        "membership_unavailable": "⚠️ <b>Membership could not be checked.</b>\n\nTry again shortly or contact support. Unchecked channels:",
        "membership_verified": "✅ Membership verified!\n\nYou can now use the bot.",
        "membership_no_channels": "✅ There are no channels to check. You can use the bot.",
        "membership_chat_unresolved": "❌ The channel chat ID could not be resolved.",
        "membership_chat_missing": "❌ The channel chat ID is not configured.",
        "membership_check_error": "⚠️ Channel membership could not be checked.",
        "verify_button": "✅ Verify",
        "join_channel": "📢 Join channel",
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
        InlineKeyboardButton("🇹🇷 Türkçe", callback_data="lang_tr"),
    ]])


def membership_keyboard(channels, language):
    rows = [[InlineKeyboardButton(
        channel.get("label") or t(language, "join_channel"),
        url=channel["link"], style=channel.get("style", "primary"),
    )] for channel in channels if channel.get("link")]
    rows.append([InlineKeyboardButton(
        t(language, "verify_button"), callback_data="verify_me", style="success",
    )])
    return InlineKeyboardMarkup(rows)

def menu_labels(language):
    language = normalize_language(language)
    return {key: t(language, key) for key in (
        "get_number", "active_numbers", "search_otp", "get_2fa",
        "balance", "profile", "refer", "leaderboard", "support",
        "admin", "mini_app",
    )}



def otp_copy_keyboard(code, language="az"):
    """Copy only the displayed code; omit unavailable or invalid values."""
    if code is None:
        return None
    code = str(code).strip()
    if not code or code == "N/A" or len(code) > 256:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton(
        t(language, "copy_code"), copy_text=CopyTextButton(text=code),
    )]])
