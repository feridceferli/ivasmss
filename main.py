import asyncio
from data_storage import data_path, atomic_save
from number_archive import NumberArchive, txt_chunks
from range_collection import RangeCollector
from world_country_codes import WORLD_COUNTRIES, build_all_country_rows, region_flag

range_collector = RangeCollector()
import io
import re
import json
import html
import os  # Operating system utilities
import hmac
import hashlib
import time
from urllib.parse import parse_qsl
import httpx
import pyotp
import random
import string
from datetime import datetime, timedelta
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)
from telegram.error import TelegramError
from aiohttp import web
from bot_localization import install_azerbaijani_localization, normalize_button_input
from bot_languages import t, language_keyboard, menu_labels, normalize_language, membership_keyboard, otp_copy_keyboard
from premium_ui import (premium_inline_button, premium_html_emoji, premium_icons_enabled,
                        disable_premium_icons, is_premium_emoji_error)

from whatsapp_safe import register_whatsapp_handlers
from admin_test_tools import register_admin_test_tools

# ==================== CONFIG SECTION ====================

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or "").strip()
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://feridceferli.github.io/ivasmss/").strip()

# ==================== AZE SMS PANEL API CONFIGURATION ====================
API_KEY = (os.environ.get("AZE_SMS_API_KEY") or os.environ.get("VOLTX_API_KEY") or "").strip()
BASE_URL = "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api"
HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["mauthapi"] = API_KEY

USER_DATA_FILE = data_path("users.json")
PAID_SMS_FILE = data_path("paid_sms.json")
STATS_FILE = data_path("user_stats.json")
BANNED_USERS_FILE = data_path("banned_users.json")
WITHDRAW_DATA_FILE = data_path("withdraw_requests.json")
ACTIVITY_LOGS_FILE = data_path("activity_logs.json")
DATA_RANGE_FILE = data_path("datarange.json")
AZ_ACCESS_FILE = data_path("az_range_permissions.json")
SYSTEM_CONFIG_FILE = data_path("system_config.json")
USER_OTP_RATE_FILE = data_path("user_otp_rates.json")
REQUIRED_CHANNELS_FILE = data_path("required_channels.json")
FAKE_OTP_CONFIG_FILE = data_path("fake_otp_config.json")
number_archive = NumberArchive(os.environ.get("DB_FOLDER", "").strip() or ".")

# ==================== MULTIPLE ADMINS CONFIGURATION ====================
ADMINS = [5152261397, 1667507073, 8431489105, 8727114055, 2130079556]

OTP_GROUP_ID =-1003812747446

# ==================== XOŞ GƏLİŞ MESAJI ====================
WELCOME_MESSAGE = """🇦🇿💎 AZE SMS PANEL 💎🇦🇿

🌍 Virtual nömrə platforması
📩 Birdəfəlik kodların ani çatdırılması
🚀 Sürətli təsdiqləmə xidməti
🔐 Təhlükəsiz və anonim giriş

📲 Facebook • WhatsApp • Telegram • Instagram

✨ Daha çox xidmət...

💎 Premium xidmət keyfiyyətindən
🇦🇿 Aze Sms Panel ilə yararlanın!"""

# ==================== OTP RATE CONFIGURATION ====================
DEFAULT_OTP_RATE = 0.20

# ==================== WITHDRAW CONFIGURATION ====================
DEFAULT_MIN_WITHDRAW = 50
DEFAULT_MAX_WITHDRAW = 10000
DEFAULT_PAYMENT_METHODS = {
    "BKASH": True,
    "NAGAD": True,
    "ROCKET": True,
    "BINANCE": True,
}

# ==================== SUPPORT & DEVELOPER LINKS ====================
SUPPORT_LINK = "https://t.me/betrunaz"
DEVELOPER_LINK = "https://t.me/betrunaz"
NOTIFY_GROUP_ID = os.environ.get("NOTIFY_GROUP_ID", "").strip()
NOTIFY_BOT_TOKEN = os.environ.get("NOTIFY_BOT_TOKEN", "").strip() or BOT_TOKEN

request_queue = asyncio.Queue()
MAX_WORKERS = 5000

client_async = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=10.0, read=15.0, write=10.0, pool=5.0),
    headers=HEADERS,
    limits=httpx.Limits(max_connections=1000, max_keepalive_connections=200),
)

active_numbers = {}
last_range = {}
CHECK_INTERVAL = 2

# ==================== SERVICE CACHE ====================
_services_cache = {"services": {}, "timestamp": 0}
CACHE_TTL = 30

# ==================== COUNTRY HOTNESS TRACKING ====================
_country_otp_timestamps = {}
HOT_THRESHOLD = 5
HOT_WINDOW = timedelta(minutes=30)


def update_country_otp_count(number: str):
    prefix = get_country_prefix_from_number(number)
    if not prefix:
        return
    now = datetime.now()
    if prefix not in _country_otp_timestamps:
        _country_otp_timestamps[prefix] = []
    ts_list = _country_otp_timestamps[prefix]
    ts_list.append(now)
    cutoff = now - HOT_WINDOW
    _country_otp_timestamps[prefix] = [t for t in ts_list if t > cutoff]


def get_country_prefix_from_number(number: str) -> str:
    clean = re.sub(r"\D", "", str(number))
    prefixes = sorted(COUNTRY_PREFIX_MAP.keys(), key=len, reverse=True)
    for p in prefixes:
        if clean.startswith(p):
            return p
    return ""


def is_country_hot(prefix: str) -> bool:
    if prefix not in _country_otp_timestamps:
        return False
    now = datetime.now()
    cutoff = now - HOT_WINDOW
    recent = [t for t in _country_otp_timestamps[prefix] if t > cutoff]
    _country_otp_timestamps[prefix] = recent
    return len(recent) >= HOT_THRESHOLD


# ==================== COUNTRY PREFIX MAP ====================
COUNTRY_PREFIX_MAP = {
    "994": ("🇦🇿", "Azərbaycan"),
    "2376": ("🇨🇲", "Cameroon"),
    "2250": ("🇨🇮", "Ivory Coast"),
    "2613": ("🇲🇬", "Madagascar"),
    "4077": ("🇷🇴", "Romania"),
    "237": ("🇨🇲", "Cameroon"),
    "225": ("🇨🇮", "Ivory Coast"),
    "261": ("🇲🇬", "Madagascar"),
    "20": ("🇪🇬", "Egypt"),
    "27": ("🇿🇦", "South Africa"),
    "234": ("🇳🇬", "Nigeria"),
    "254": ("🇰🇪", "Kenya"),
    "233": ("🇬🇭", "Ghana"),
    "212": ("🇲🇦", "Morocco"),
    "213": ("🇩🇿", "Algeria"),
    "216": ("🇹🇳", "Tunisia"),
    "218": ("🇱🇾", "Libya"),
    "249": ("🇸🇩", "Sudan"),
    "251": ("🇪🇹", "Ethiopia"),
    "252": ("🇸🇴", "Somalia"),
    "253": ("🇩🇯", "Djibouti"),
    "255": ("🇹🇿", "Tanzania"),
    "256": ("🇺🇬", "Uganda"),
    "257": ("🇧🇮", "Burundi"),
    "258": ("🇲🇿", "Mozambique"),
    "260": ("🇿🇲", "Zambia"),
    "263": ("🇿🇼", "Zimbabwe"),
    "264": ("🇳🇦", "Namibia"),
    "265": ("🇲🇼", "Malawi"),
    "266": ("🇱🇸", "Lesotho"),
    "267": ("🇧🇼", "Botswana"),
    "268": ("🇸🇿", "Eswatini"),
    "269": ("🇰🇲", "Comoros"),
    "220": ("🇬🇲", "Gambia"),
    "221": ("🇸🇳", "Senegal"),
    "222": ("🇲🇷", "Mauritania"),
    "223": ("🇲🇱", "Mali"),
    "224": ("🇬🇳", "Guinea"),
    "226": ("🇧🇫", "Burkina Faso"),
    "227": ("🇳🇪", "Niger"),
    "228": ("🇹🇬", "Togo"),
    "229": ("🇧🇯", "Benin"),
    "230": ("🇲🇺", "Mauritius"),
    "231": ("🇱🇷", "Liberia"),
    "232": ("🇸🇱", "Sierra Leone"),
    "235": ("🇹🇩", "Chad"),
    "236": ("🇨🇫", "Central African Republic"),
    "238": ("🇨🇻", "Cape Verde"),
    "239": ("🇸🇹", "Sao Tome and Principe"),
    "240": ("🇬🇶", "Equatorial Guinea"),
    "241": ("🇬🇦", "Gabon"),
    "242": ("🇨🇬", "Congo"),
    "243": ("🇨🇩", "DR Congo"),
    "244": ("🇦🇴", "Angola"),
    "245": ("🇬🇼", "Guinea-Bissau"),
    "247": ("🇸🇭", "Saint Helena"),
    "248": ("🇸🇨", "Seychelles"),
    "250": ("🇷🇼", "Rwanda"),
    "290": ("🇸🇭", "Saint Helena"),
    "291": ("🇪🇷", "Eritrea"),
    "40": ("🇷🇴", "Romania"),
    "44": ("🇬🇧", "United Kingdom"),
    "33": ("🇫🇷", "France"),
    "49": ("🇩🇪", "Germany"),
    "39": ("🇮🇹", "Italy"),
    "34": ("🇪🇸", "Spain"),
    "31": ("🇳🇱", "Netherlands"),
    "32": ("🇧🇪", "Belgium"),
    "41": ("🇨🇭", "Switzerland"),
    "43": ("🇦🇹", "Austria"),
    "46": ("🇸🇪", "Sweden"),
    "47": ("🇳🇴", "Norway"),
    "45": ("🇩🇰", "Denmark"),
    "358": ("🇫🇮", "Finland"),
    "351": ("🇵🇹", "Portugal"),
    "353": ("🇮🇪", "Ireland"),
    "36": ("🇭🇺", "Hungary"),
    "48": ("🇵🇱", "Poland"),
    "380": ("🇺🇦", "Ukraine"),
    "370": ("🇱🇹", "Lithuania"),
    "371": ("🇱🇻", "Latvia"),
    "372": ("🇪🇪", "Estonia"),
    "373": ("🇲🇩", "Moldova"),
    "374": ("🇦🇲", "Armenia"),
    "375": ("🇧🇾", "Belarus"),
    "376": ("🇦🇩", "Andorra"),
    "377": ("🇲🇨", "Monaco"),
    "381": ("🇷🇸", "Serbia"),
    "382": ("🇲🇪", "Montenegro"),
    "385": ("🇭🇷", "Croatia"),
    "386": ("🇸🇮", "Slovenia"),
    "387": ("🇧🇦", "Bosnia and Herzegovina"),
    "389": ("🇲🇰", "North Macedonia"),
    "350": ("🇬🇮", "Gibraltar"),
    "352": ("🇱🇺", "Luxembourg"),
    "354": ("🇮🇸", "Iceland"),
    "355": ("🇦🇱", "Albania"),
    "356": ("🇲🇹", "Malta"),
    "357": ("🇨🇾", "Cyprus"),
    "359": ("🇧🇬", "Bulgaria"),
    "421": ("🇸🇰", "Slovakia"),
    "420": ("🇨🇿", "Czech Republic"),
    "298": ("🇫🇴", "Faroe Islands"),
    "299": ("🇬🇱", "Greenland"),
    "1": ("🇺🇸", "United States"),
    "7": ("🇷🇺", "Russia"),
    "91": ("🇮🇳", "India"),
    "92": ("🇵🇰", "Pakistan"),
    "880": ("🇧🇩", "Bangladesh"),
    "86": ("🇨🇳", "China"),
    "81": ("🇯🇵", "Japan"),
    "82": ("🇰🇷", "South Korea"),
    "84": ("🇻🇳", "Vietnam"),
    "66": ("🇹🇭", "Thailand"),
    "62": ("🇮🇩", "Indonesia"),
    "60": ("🇲🇾", "Malaysia"),
    "65": ("🇸🇬", "Singapore"),
    "63": ("🇵🇭", "Philippines"),
    "95": ("🇲🇲", "Myanmar"),
    "94": ("🇱🇰", "Sri Lanka"),
    "977": ("🇳🇵", "Nepal"),
    "93": ("🇦🇫", "Afghanistan"),
    "98": ("🇮🇷", "Iran"),
    "90": ("🇹🇷", "Turkey"),
    "964": ("🇮🇶", "Iraq"),
    "963": ("🇸🇾", "Syria"),
    "961": ("🇱🇧", "Lebanon"),
    "962": ("🇯🇴", "Jordan"),
    "965": ("🇰🇼", "Kuwait"),
    "966": ("🇸🇦", "Saudi Arabia"),
    "967": ("🇾🇪", "Yemen"),
    "968": ("🇴🇲", "Oman"),
    "971": ("🇦🇪", "UAE"),
    "972": ("🇮🇱", "Israel"),
    "973": ("🇧🇭", "Bahrain"),
    "974": ("🇶🇦", "Qatar"),
    "994": ("🇦🇿", "Azerbaijan"),
    "995": ("🇬🇪", "Georgia"),
    "996": ("🇰🇬", "Kyrgyzstan"),
    "992": ("🇹🇯", "Tajikistan"),
    "993": ("🇹🇲", "Turkmenistan"),
    "998": ("🇺🇿", "Uzbekistan"),
    "855": ("🇰🇭", "Cambodia"),
    "856": ("🇱🇦", "Laos"),
    "976": ("🇲🇳", "Mongolia"),
    "850": ("🇰🇵", "North Korea"),
    "55": ("🇧🇷", "Brazil"),
    "52": ("🇲🇽", "Mexico"),
    "54": ("🇦🇷", "Argentina"),
    "57": ("🇨🇴", "Colombia"),
    "51": ("🇵🇪", "Peru"),
    "58": ("🇻🇪", "Venezuela"),
    "56": ("🇨🇱", "Chile"),
    "593": ("🇪🇨", "Ecuador"),
    "591": ("🇧🇴", "Bolivia"),
    "595": ("🇵🇾", "Paraguay"),
    "598": ("🇺🇾", "Uruguay"),
    "502": ("🇬🇹", "Guatemala"),
    "503": ("🇸🇻", "El Salvador"),
    "504": ("🇭🇳", "Honduras"),
    "506": ("🇨🇷", "Costa Rica"),
    "507": ("🇵🇦", "Panama"),
    "509": ("🇭🇹", "Haiti"),
    "501": ("🇧🇿", "Belize"),
    "61": ("🇦🇺", "Australia"),
    "64": ("🇳🇿", "New Zealand"),
    "675": ("🇵🇬", "Papua New Guinea"),
    "679": ("🇫🇯", "Fiji"),
    "1246": ("🇧🇧", "Barbados"),
    "1876": ("🇯🇲", "Jamaica"),
    "53": ("🇨🇺", "Cuba"),
    "592": ("🇬🇾", "Guyana"),
}

# Supplement the legacy map with global country calling codes, so a
# successfully allocated range from any listed country has a matching flag
# and country label. Preserve the legacy more-specific prefix overrides.
for _iso, _name, _calling_code in WORLD_COUNTRIES:
    COUNTRY_PREFIX_MAP.setdefault(_calling_code, (region_flag(_iso), _name))


def get_country_by_prefix(prefix: str):
    if prefix in COUNTRY_PREFIX_MAP:
        return COUNTRY_PREFIX_MAP[prefix]
    sorted_prefixes = sorted(COUNTRY_PREFIX_MAP.keys(), key=len, reverse=True)
    for p in sorted_prefixes:
        if prefix.startswith(p):
            return COUNTRY_PREFIX_MAP[p]
    return ("🌍", "Unknown")


# ==================== SYSTEM CONFIG ====================
def load_system_config():
    if not os.path.exists(SYSTEM_CONFIG_FILE):
        default_config = {
            "min_withdraw": DEFAULT_MIN_WITHDRAW,
            "max_withdraw": DEFAULT_MAX_WITHDRAW,
            "payment_methods": DEFAULT_PAYMENT_METHODS.copy(),
            "otp_rate": DEFAULT_OTP_RATE,
        }
        save_system_config(default_config)
        return default_config
    try:
        with open(SYSTEM_CONFIG_FILE, "r") as f:
            config = json.load(f)
            if "otp_rate" not in config:
                config["otp_rate"] = DEFAULT_OTP_RATE
                save_system_config(config)
            return config
    except:
        return {
            "min_withdraw": DEFAULT_MIN_WITHDRAW,
            "max_withdraw": DEFAULT_MAX_WITHDRAW,
            "payment_methods": DEFAULT_PAYMENT_METHODS.copy(),
            "otp_rate": DEFAULT_OTP_RATE,
        }


def save_system_config(config):
    with open(SYSTEM_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def update_min_withdraw(new_min):
    config = load_system_config()
    config["min_withdraw"] = new_min
    save_system_config(config)


def update_otp_rate(new_rate):
    config = load_system_config()
    config["otp_rate"] = new_rate
    save_system_config(config)


def get_otp_rate():
    config = load_system_config()
    return config.get("otp_rate", DEFAULT_OTP_RATE)


def toggle_payment_method(method_name):
    config = load_system_config()
    if method_name in config["payment_methods"]:
        config["payment_methods"][method_name] = not config["payment_methods"][
            method_name
        ]
        save_system_config(config)
        return config["payment_methods"][method_name]
    return None


def get_enabled_payment_methods():
    config = load_system_config()
    return [name for name, enabled in config["payment_methods"].items() if enabled]


# ==================== PER-USER OTP RATE FUNCTIONS ====================
def load_user_otp_rates():
    if not os.path.exists(USER_OTP_RATE_FILE):
        with open(USER_OTP_RATE_FILE, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(USER_OTP_RATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_user_otp_rates(data):
    with open(USER_OTP_RATE_FILE, "w") as f:
        json.dump(data, f, indent=4)


def get_user_otp_rate(user_id):
    rates = load_user_otp_rates()
    uid_str = str(user_id)
    if uid_str in rates:
        try:
            rate = float(rates[uid_str])
            if rate > 0:
                return rate
        except:
            pass
    return get_otp_rate()


def set_user_otp_rate(user_id, rate):
    rates = load_user_otp_rates()
    uid_str = str(user_id)
    if rate > 0:
        rates[uid_str] = rate
    else:
        if uid_str in rates:
            del rates[uid_str]
    save_user_otp_rates(rates)


# ==================== FAKE OTP CONFIG FUNCTIONS ====================
def load_fake_otp_config():
    if not os.path.exists(FAKE_OTP_CONFIG_FILE):
        default = {
            "enabled": False,
            "service": "DEMO",
            "range": "",
            "interval": 10,
            "running": False,
            "otp_digits": 6,
            "sent_count": 0,
        }
        save_fake_otp_config(default)
        return default
    try:
        with open(FAKE_OTP_CONFIG_FILE, "r") as f:
            config = json.load(f)
            changed = False
            if "otp_digits" not in config:
                config["otp_digits"] = 6
                changed = True
            if "sent_count" not in config:
                config["sent_count"] = 0
                changed = True
            if changed:
                save_fake_otp_config(config)
            return config
    except:
        default = {
            "enabled": False,
            "service": "DEMO",
            "range": "",
            "interval": 10,
            "running": False,
            "otp_digits": 6,
            "sent_count": 0,
        }
        save_fake_otp_config(default)
        return default


def save_fake_otp_config(config):
    with open(FAKE_OTP_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def update_fake_otp_config(**kwargs):
    config = load_fake_otp_config()
    for key, value in kwargs.items():
        config[key] = value
    save_fake_otp_config(config)


# ==================== REQUIRED CHANNELS / GROUPS FUNCTIONS ====================
STYLES = ["primary", "success", "danger"]


def load_required_channels():
    if not os.path.exists(REQUIRED_CHANNELS_FILE):
        with open(REQUIRED_CHANNELS_FILE, "w") as f:
            json.dump([], f)
        return []
    try:
        with open(REQUIRED_CHANNELS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_required_channels(data):
    with open(REQUIRED_CHANNELS_FILE, "w") as f:
        json.dump(data, f, indent=4)


def add_required_channel(link, label=None, chat_id=None):
    channels = load_required_channels()
    for ch in channels:
        if ch.get("link") == link:
            return False, 'Bu keçid artıq mövcuddur.'
    if not label:
        label = link.replace("https://t.me/", "").replace("@", "")
        if label.startswith("+"):
            label = "Channel " + label
        else:
            label = "@" + label
    style_index = len(channels) % len(STYLES)
    style = STYLES[style_index]
    entry = {"link": link, "label": label, "style": style}
    if chat_id:
        entry["chat_id"] = chat_id
    else:
        username_match = re.search(
            r"(?:https?://)?(?:www\.)?t\.me/([a-zA-Z0-9_]+)", link
        )
        if username_match:
            entry["username"] = username_match.group(1)
        else:
            return (
                False,
                'Keçiddən çat ID-sini çıxarmaq mümkün olmadı. Zəhmət olmasa, çat ID-si ilə birlikdə əlavə edin və ya düzgün keçid verin.',
            )
    channels.append(entry)
    save_required_channels(channels)
    return True, 'Uğurla əlavə edildi.'


def remove_required_channel(link_or_label):
    channels = load_required_channels()
    new_channels = []
    removed = False
    for ch in channels:
        if ch.get("link") == link_or_label or ch.get("label") == link_or_label:
            removed = True
            continue
        new_channels.append(ch)
    if removed:
        save_required_channels(new_channels)
        return True, 'Silindi.'
    return False, 'Heç bir uyğunluq tapılmadı.'


def get_all_required_channels():
    return load_required_channels()


async def resolve_chat_id_from_username(bot, username):
    try:
        chat = await bot.get_chat(f"@{username}")
        return chat.id
    except:
        return None


async def check_user_joined(bot, user_id, channel_entry):
    # Optional channel links stay visible without requiring membership.
    if channel_entry.get("verification_required", True) is False:
        return True, None
    lang = get_user_language(user_id)
    chat_id = channel_entry.get("chat_id")
    if not chat_id:
        username = channel_entry.get("username")
        if username:
            chat_id = await resolve_chat_id_from_username(bot, username)
            if chat_id:
                channel_entry["chat_id"] = chat_id
                channels = load_required_channels()
                for ch in channels:
                    if ch.get("link") == channel_entry.get("link"):
                        ch["chat_id"] = chat_id
                        break
                save_required_channels(channels)
            else:
                return False, t(lang, "membership_chat_unresolved")
    if not chat_id:
        return False, t(lang, "membership_chat_missing")

    try:
        member = await bot.get_chat_member(chat_id, user_id)
        if member.status in ("member", "administrator", "creator"):
            return True, None
        else:
            return False, None
    except TelegramError:
        return False, t(lang, "membership_check_error")


async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    lang = get_user_language(uid)
    await query.answer()

    channels = load_required_channels()
    if not channels:
        await query.edit_message_text(
            t(lang, "membership_no_channels")
        )
        await show_main_menu(update, context, uid)
        return

    failed = []
    unavailable = []
    for ch in channels:
        ok, error = await check_user_joined(context.bot, uid, ch)
        if not ok:
            label = html.escape(str(ch.get("label") or ch.get("link") or t(lang, "join_channel")))
            (unavailable if error else failed).append(label)

    if failed or unavailable:
        parts = []
        if failed:
            parts.append(t(lang, "membership_failed") + "\n" + "\n".join(f"• {label}" for label in failed))
            parts.append(t(lang, "membership_retry"))
        if unavailable:
            parts.append(t(lang, "membership_unavailable") + "\n" + "\n".join(f"• {label}" for label in unavailable))
        await query.edit_message_text(
            "\n\n".join(parts), parse_mode="HTML",
            reply_markup=membership_keyboard(channels, lang),
        )
        return

    user_data = get_user(uid)
    user_data["verified"] = True
    all_data = load_data(USER_DATA_FILE)
    all_data[str(uid)] = user_data
    save_data(all_data)

    await query.edit_message_text(
        t(lang, "membership_verified")
    )
    await show_main_menu(update, context, uid)


# ==================== ASYNC HELPERS ====================
async def fetch_services_cached():
    global _services_cache
    now = datetime.now().timestamp()
    if _services_cache["services"] and (now - _services_cache["timestamp"]) < CACHE_TTL:
        return _services_cache["services"]
    try:
        r = await client_async.get(f"{BASE_URL}/liveaccess")
        data = r.json()
        if data.get("meta", {}).get("code") == 200:
            services_data = data.get("data", {}).get("services", [])
            services = {}
            for svc in services_data:
                if not isinstance(svc, dict):
                    continue
                # Ignore explicit promotional/ad entries from the upstream API.
                # Real service IDs (including numeric IDs) remain visible.
                entry_type = str(svc.get("type", "")).strip().lower()
                is_ad = svc.get("is_ad") is True or svc.get("ad") is True
                is_promo = svc.get("is_promo") is True or svc.get("promotional") is True
                if entry_type in {"ad", "ads", "advertisement", "promo", "promotion", "sponsored"} or is_ad or is_promo:
                    continue
                sid = str(svc.get("sid", "")).strip().lower()
                ranges = svc.get("ranges", [])
                if sid and isinstance(ranges, list) and ranges:
                    services[sid] = ranges
            _services_cache["services"] = services
            _services_cache["timestamp"] = now
            print(f"[services] cache updated — {len(services)} service(s)")
            return services
    except Exception as e:
        print(f"[services] fetch error: {e}")
    return _services_cache["services"]


_known_service_countries = set()
_known_service_types = set()
_service_country_watch_initialized = False

def _service_country_availability(services):
    found = {}
    for service, ranges in (services or {}).items():
        service_name = str(service).strip()
        if not service_name:
            continue
        for raw_range in ranges or []:
            rid = re.sub(r"[^0-9]", "", str(raw_range))
            prefix = get_country_prefix_from_number(rid)
            if not prefix:
                continue
            flag, country = get_country_by_prefix(prefix)
            key = (service_name.lower(), prefix)
            if key not in found:
                found[key] = {
                    "service": service_name,
                    "prefix": prefix,
                    "flag": flag,
                    "country": country,
                    "number_count": 0,
                }
            found[key]["number_count"] += 1
    return found

async def send_availability_notice(app, group_id, text):
    """Send non-sensitive availability notices to the group and bot users."""
    recipients = set(get_all_users())
    if group_id:
        recipients.add(str(group_id))
    for recipient in recipients:
        try:
            await app.bot.send_message(chat_id=int(recipient), text=text, parse_mode="HTML")
        except Exception as exc:
            print(f"[availability-notice] delivery failed: {type(exc).__name__}")


async def country_availability_loop(app):
    """Announce new service and country availability to group and bot users."""
    global _known_service_countries, _known_service_types, _service_country_watch_initialized
    while True:
        try:
            _services_cache["timestamp"] = 0
            services = await fetch_services_cached()
            current = _service_country_availability(services)
            current_keys = set(current)
            current_services = {str(name).strip().lower() for name in (services or {}) if str(name).strip()}
            if _service_country_watch_initialized:
                for service in sorted(current_services - _known_service_types):
                    notice = (
                        "🆕 <b>Yeni xidmət əlavə olundu</b>\n\n"
                        f"📡 Xidmət: <code>{html.escape(service.upper())}</code>\n\n"
                        "✅ API-də yeni xidmət növü aşkarlandı."
                    )
                    await send_availability_notice(app, NOTIFY_GROUP_ID, notice)
                for key in sorted(current_keys - _known_service_countries):
                    info = current[key]
                    notice = (
                        "🆕 <b>Yeni xidmət mövcudluğu</b>\n\n"
                        f"📡 Xidmət: <code>{html.escape(info['service'].upper())}</code>\n"
                        f"🌍 Ölkə: {info['flag']} {html.escape(info['country'])}\n"
                        f"📞 Ölkə kodu: <code>+{html.escape(info['prefix'])}</code>\n"
                        f"🔢 Diapazon sayı: <b>{info.get('number_count', 0)}</b>\n\n"
                        "✅ API-də bu xidmət üçün yeni diapazon mövcudluğu aşkarlandı."
                    )
                    await send_availability_notice(app, NOTIFY_GROUP_ID, notice)
            _known_service_countries = current_keys
            _known_service_types = current_services
            _service_country_watch_initialized = True
        except Exception as exc:
            print(f"[service-country-watch] {type(exc).__name__}: {exc}")
        await asyncio.sleep(30)


async def get_number_from_api(rid: str, requester_id=None):
    """Never allocate a +994 range without an explicit server-side permission."""
    digits = re.sub(r"[^0-9]", "", str(rid or ""))
    if not digits or (is_az_range(digits) and not az_range_allowed(requester_id)):
        return None, None
    try:
        r = await client_async.post(f"{BASE_URL}/getnum", json={"rid": digits})
        result = r.json()
        if result.get("meta", {}).get("code") == 200:
            data = result.get("data") or {}
            number = data.get("full_number")
            normalized = re.sub(r"[^0-9]", "", str(number or ""))
            if not normalized.startswith(digits) or (is_az_range(normalized) and not az_range_allowed(requester_id)):
                print("[number-api] Unexpected or restricted provider range")
                return None, None
            await asyncio.to_thread(number_archive.record, number)
            return number, data.get("country")
        return None, None
    except Exception as e:
        print(f"get_number error: {type(e).__name__}")
        return None, None


# ==================== CHECK IF USER IS ADMIN ====================
def is_admin(user_id):
    return user_id in ADMINS


def is_az_range(value):
    return re.sub(r"[^0-9]", "", str(value or "")).startswith("994")


def az_range_allowed(user_id):
    """Only admins and approved users can use Azerbaijan ranges."""
    if user_id is None:
        return False
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return False
    return is_admin(uid) or bool(load_data(AZ_ACCESS_FILE).get(str(uid)))


AZ_ACCESS_DENIED = "🔒 Azərbaycan (+994) nömrələri üçün admin təsdiqi lazımdır. /az_request yazın."
_az_request_times = {}

# Operator/prefix pairs requested by the administrator.
# 210/211 are subrange selectors, not verified API service identifiers.
AZ_OPERATOR_PREFIXES = (
    ("bakcell", "Bakcell", ("99455", "99499")),
    ("azercell", "Azercell", ("99450", "99451", "99410")),
    ("nar", "Nar", ("99470", "99477")),
    ("naxtell", "Naxtell", ("99460",)),
    ("catel", "Catel", ("99440",)),
    ("cdma", "CDMA", ("99444",)),
)
AZ_RANGE_SUFFIXES = ("210", "211")


def az_range_catalog(services=None):
    """Display the 210/211 presets plus other range metadata from /liveaccess.

    This is read-only range discovery, not bulk number retrieval. Full phone
    numbers are excluded from the catalogue.
    """
    listed = {
        digits for ranges in (services or {}).values()
        for raw in (ranges or [])
        for digits in [re.sub(r"[^0-9]", "", str(raw))]
        if digits.startswith("994") and 5 <= len(digits) <= 10
    }
    catalog = []
    for key, name, prefixes in AZ_OPERATOR_PREFIXES:
        groups = []
        for prefix in prefixes:
            standard = {prefix + suffix for suffix in AZ_RANGE_SUFFIXES}
            entries = [
                {
                    "rid": prefix + suffix,
                    "suffix": suffix,
                    "source": "configured",
                    "listed_in_api": prefix + suffix in listed,
                }
                for suffix in AZ_RANGE_SUFFIXES
            ]
            entries.extend({
                "rid": rid,
                "suffix": "",
                "source": "api",
                "listed_in_api": True,
            } for rid in sorted(listed) if rid.startswith(prefix) and rid not in standard)
            groups.append({"prefix": prefix, "ranges": entries})
        catalog.append({"id": key, "name": name, "prefixes": groups})
    return catalog


def az_catalog_lookup(operator_id=None, prefix=None, rid=None, services=None):
    """Authorize only configured 210/211 or ranges in the live API catalogue."""
    for group in az_range_catalog(services):
        if operator_id == group["id"]:
            return {"id": group["id"], "name": group["name"],
                    "prefixes": tuple(row["prefix"] for row in group["prefixes"])}
        for item in group["prefixes"]:
            if prefix == item["prefix"]:
                return {"id": group["id"], "name": group["name"],
                        "prefixes": tuple(row["prefix"] for row in group["prefixes"])}
            if rid is not None and any(entry["rid"] == rid for entry in item["ranges"]):
                return {"id": group["id"], "name": group["name"],
                        "prefixes": tuple(row["prefix"] for row in group["prefixes"])}
    return None




# ==================== WITHDRAW DATA FUNCTIONS ====================
def load_withdraw_requests():
    if not os.path.exists(WITHDRAW_DATA_FILE):
        with open(WITHDRAW_DATA_FILE, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(WITHDRAW_DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_withdraw_requests(data):
    with open(WITHDRAW_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def generate_payment_id():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=20))


# ==================== BANNED USERS ====================
def load_banned_users():
    if not os.path.exists(BANNED_USERS_FILE):
        with open(BANNED_USERS_FILE, "w") as f:
            json.dump([], f)
        return []
    try:
        with open(BANNED_USERS_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_banned_users(banned_list):
    with open(BANNED_USERS_FILE, "w") as f:
        json.dump(banned_list, f, indent=4)


def is_user_banned(uid):
    banned_list = load_banned_users()
    return str(uid) in banned_list


def ban_user(uid):
    banned_list = load_banned_users()
    uid_str = str(uid)
    if uid_str not in banned_list:
        banned_list.append(uid_str)
        save_banned_users(banned_list)
        return True
    return False


def unban_user(uid):
    banned_list = load_banned_users()
    uid_str = str(uid)
    if uid_str in banned_list:
        banned_list.remove(uid_str)
        save_banned_users(banned_list)
        return True
    return False


# ==================== DATA RANGE FILE ====================
def load_range_db():
    if not os.path.exists(DATA_RANGE_FILE):
        return {}
    try:
        with open(DATA_RANGE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_range_db(data):
    with open(DATA_RANGE_FILE, "w") as f:
        json.dump(data, f, indent=4)


def save_number_range_info(uid, number, range_text):
    number_archive.record(number, uid)
    db = load_range_db()
    flag, name = get_country_info(number)
    db[normalize_number(number)] = {
        "user_id": str(uid),
        "number": f"+{normalize_number(number)}",
        "range": range_text,
        "country": f"{flag} {name}",
    }
    save_range_db(db)


# ==================== COUNTRY INFO ====================
def get_country_info(number):
    number = str(number).strip()
    clean_num = re.sub(r"\D", "", number)
    sorted_prefixes = sorted(COUNTRY_PREFIX_MAP.keys(), key=len, reverse=True)
    for prefix in sorted_prefixes:
        if clean_num.startswith(prefix):
            return COUNTRY_PREFIX_MAP[prefix]
    return ("🌍", "Unknown")


# ==================== SERVICE DETECTION ====================
def detect_service(full_sms):
    if not full_sms:
        return "SMS SERVICE"
    sms_lower = full_sms.lower()
    service_keywords = {
        "facebook": "FACEBOOK",
        "fb": "FACEBOOK",
        "instagram": "INSTAGRAM",
        "insta": "INSTAGRAM",
        "tiktok": "TIKTOK",
        "twitter": "TWITTER",
        "x.com": "TWITTER",
        "snapchat": "SNAPCHAT",
        "snap": "SNAPCHAT",
        "whatsapp": "WHATSAPP",
        "telegram": "TELEGRAM",
        "discord": "DISCORD",
        "messenger": "MESSENGER",
        "linkedin": "LINKEDIN",
        "google": "GOOGLE",
        "gmail": "GOOGLE",
        "amazon": "AMAZON",
        "microsoft": "MICROSOFT",
        "outlook": "MICROSOFT",
        "yahoo": "YAHOO",
        "paypal": "PAYPAL",
        "binance": "BINANCE",
        "coinbase": "COINBASE",
        "spotify": "SPOTIFY",
        "netflix": "NETFLIX",
        "uber": "UBER",
        "apple": "APPLE",
        "icloud": "APPLE",
        "bkash": "BKASH",
        "nagad": "NAGAD",
        "stripe": "STRIPE",
        "line": "LINE",
        "wechat": "WECHAT",
        "viber": "VIBER",
        "signal": "SIGNAL",
        "pubg": "PUBG",
        "free fire": "FREE FIRE",
    }
    for keyword, service_name in sorted(
        service_keywords.items(), key=lambda x: len(x[0]), reverse=True
    ):
        if keyword in sms_lower:
            return service_name
    return "SMS SERVICE"


# ==================== KEYBOARDS ====================
def get_user_language(user_id):
    data = load_data(USER_DATA_FILE)
    return normalize_language(data.get(str(user_id), {}).get("language", "az"))

def main_keyboard(user_id):
    lang = get_user_language(user_id)
    labels = menu_labels(lang)
    rows = []
    if WEBAPP_URL:
        rows.append([
            premium_inline_button(labels["mini_app"], "mini_app",
                                  web_app=WebAppInfo(url=WEBAPP_URL), style="primary")
        ])
    rows.append([
        premium_inline_button("🧩 IVAS SMS WEB PANEL", "ivas_panel",
                              callback_data="menu_ivas_web_panel")
    ])
    rows.append([InlineKeyboardButton(t(lang, "all_countries"),
                                      callback_data="menu_all_countries", style="primary")])
    rows.append([InlineKeyboardButton("🇦🇿 Azərbaycan +994" + ("" if az_range_allowed(user_id) else " 🔒"),
                                      callback_data="menu_az_ranges")])
    rows += [
        [
            premium_inline_button(labels["get_number"], "get_number",
                                  callback_data="menu_get_number", style="success"),
            premium_inline_button(labels["active_numbers"], "active_numbers",
                                  callback_data="menu_active_numbers"),
        ],
        [
            premium_inline_button(labels["search_otp"], "search_otp",
                                  callback_data="menu_search_otp"),
            premium_inline_button(labels["get_2fa"], "get_2fa",
                                  callback_data="menu_get_2fa"),
        ],
        [
            premium_inline_button(labels["balance"], "balance",
                                  callback_data="menu_balance", style="primary"),
            premium_inline_button(labels["profile"], "profile",
                                  callback_data="menu_profile"),
        ],
        [
            premium_inline_button(labels["leaderboard"], "leaderboard",
                                  callback_data="menu_leaderboard"),
        ],
        [premium_inline_button(labels["support"], "support",
                               callback_data="menu_support")],
        [
            premium_inline_button(
                "🌐 DİLİ DƏYİŞ" if lang == "az" else
                "🌐 DİLİ DEĞİŞTİR" if lang == "tr" else
                "🌐 CHANGE LANGUAGE",
                "language", callback_data="menu_language", style="primary",
            )
        ],
    ]
    if is_admin(user_id):
        rows.append([InlineKeyboardButton("📥 BÜTÜN NÖMRƏLƏR — TXT", callback_data="menu_all_numbers_txt")])
        rows.append([
            premium_inline_button(labels["admin"], "admin",
                                  callback_data="menu_admin", style="danger")
        ])
    rows.append([InlineKeyboardButton("📥 NÖMRƏLƏRİM — TXT", callback_data="menu_numbers_txt")])
    return InlineKeyboardMarkup(rows)


async def premium_keyboard_error_handler(update, context):
    """Retry the standard menu if Telegram rejects Premium custom emoji."""
    error = context.error
    if premium_icons_enabled() and is_premium_emoji_error(error):
        disable_premium_icons()
        print("[premium-ui] Telegram rejected custom emojis; Unicode fallback enabled.")
        user = getattr(update, "effective_user", None)
        message = getattr(update, "effective_message", None)
        if user is not None and message is not None:
            try:
                await message.reply_text(
                    "🔹 Menyu adi emojilərlə açıldı / Menu opened with regular emoji.",
                    reply_markup=main_keyboard(user.id),
                )
            except TelegramError:
                print("[premium-ui] Could not resend fallback menu.")
        return
    print(f"[telegram-handler-error] {type(error).__name__}")


def cancel_keyboard():
    keyboard = [[KeyboardButton("❌ CANCEL")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def admin_main_keyboard():
    keyboard = [
        [KeyboardButton("👥 İSTİFADƏÇİ İDARƏETMƏSİ"), KeyboardButton("⚙️ SİSTEM KONFİQURASİYASI")],
        [KeyboardButton("🔗 TƏLƏB OLUNAN KANALLAR"), KeyboardButton("⚡ FAKE OTP")],
        [KeyboardButton("🛠 BİLDİRİŞ ALƏTLƏRİ")],
        [KeyboardButton("🧪 TEST ALƏTLƏRİ")],
        [KeyboardButton("🔙 ƏSAS MENYUYA QAYIT")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def admin_tools_keyboard():
    keyboard = [
        [KeyboardButton("📢 QRUPA BİLDİRİŞ"), KeyboardButton("🧪 QRUP TESTİ")],
        [KeyboardButton("ℹ️ BİLDİRİŞ STATUSU"), KeyboardButton("🔙 İNZİBATÇI PANELİNƏ QAYIT")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def send_group_notification(text: str):
    if not NOTIFY_GROUP_ID or not NOTIFY_BOT_TOKEN:
        return False, "Render Environment-də NOTIFY_GROUP_ID və NOTIFY_BOT_TOKEN konfiqurasiya edilməyib."
    try:
        chat_id = int(NOTIFY_GROUP_ID)
    except ValueError:
        chat_id = NOTIFY_GROUP_ID
    url = f"https://api.telegram.org/bot{NOTIFY_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json={"chat_id": chat_id, "text": text})
        if response.is_success and response.json().get("ok"):
            return True, "Bildiriş göndərildi."
        return False, f"Telegram xətası: HTTP {response.status_code}"
    except Exception as exc:
        return False, f"Göndərmə xətası: {type(exc).__name__}"


def user_management_keyboard():
    keyboard = [
        [KeyboardButton("📢 BÜTÜN İSTİFADƏÇİLƏRƏ MESAJ GÖNDƏR"), KeyboardButton("🆔 BÜTÜN İSTİFADƏÇİ ID-LƏRİ")],
        [KeyboardButton("📜 BLOKLANMIŞ İSTİFADƏÇİLƏR"), KeyboardButton("💰 BÜTÜN İSTİFADƏÇİLƏRİN BALANSI")],
        [KeyboardButton("👥 İSTİFADƏÇİ SİYAHISI (HAMISI)"), KeyboardButton("🔙 İNZİBATÇI PANELİNƏ QAYIT")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def system_config_keyboard():
    keyboard = [
        [KeyboardButton("📈 BU GÜNKÜ ÜMUMİ VƏZİYYƏT"), KeyboardButton("👤 İSTİFADƏÇİNİN VƏZİYYƏTİNİ YOXLAYIN")],
        [KeyboardButton("🩺 SMS MONİTOR STATUSU")],
        [KeyboardButton("⛔ İSTİFADƏÇİNİ BLOKLA"), KeyboardButton("🔓 BLOKDAN ÇIXAR")],
        [KeyboardButton("📜 BLOKLANMIŞ İSTİFADƏÇİLƏR")],
        [KeyboardButton("➖ BALANSI AZALT"), KeyboardButton("➕ BALANS ƏLAVƏ ET")],
        [KeyboardButton("⚙️ MİNİMUM ÇIXARIŞI DƏYİŞ")],
        [KeyboardButton("💳 ÖDƏNİŞ ÜSULLARINI DƏYİŞ")],
        [KeyboardButton("💲 OTP QİYMƏTİNİ DƏYİŞ")],
        [
            KeyboardButton("🔧 İSTİFADƏÇİ OTP QİYMƏTİNİ TƏYİN ET"),
            KeyboardButton("📋 İSTİFADƏÇİ OTP QİYMƏTİNƏ BAX"),
        ],
        [KeyboardButton("🔙 İNZİBATÇI PANELİNƏ QAYIT")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def required_channels_keyboard():
    keyboard = [
        [KeyboardButton("➕ KANAL ƏLAVƏ ET"), KeyboardButton("❌ KANALI SİL")],
        [KeyboardButton("📋 KANALLARIN SİYAHISI"), KeyboardButton("🔙 İNZİBATÇI PANELİNƏ QAYIT")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def fake_otp_keyboard():
    config = load_fake_otp_config()
    status = "✅ AKTİV" if config.get("running", False) else "❌ DEAKTİV"
    keyboard = [
        [KeyboardButton(f"📊 STATUS: {status}")],
        [KeyboardButton("▶️ START"), KeyboardButton("⏹ STOP")],
        [KeyboardButton("⚙️ SETTINGS"), KeyboardButton("📈 TEST STATİSTİKASI")],
        [KeyboardButton("🔙 İNZİBATÇI PANELİNƏ QAYIT")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def withdraw_method_keyboard():
    enabled_methods = get_enabled_payment_methods()
    if not enabled_methods:
        enabled_methods = ["BKASH", "NAGAD", "ROCKET", "BINANCE"]
    buttons = []
    for method in enabled_methods:
        if method == "BKASH":
            buttons.append([KeyboardButton("📱 BKASH")])
        elif method == "NAGAD":
            buttons.append([KeyboardButton("💵 NAGAD")])
        elif method == "ROCKET":
            buttons.append([KeyboardButton("🚀 ROCKET")])
        elif method == "BINANCE":
            buttons.append([KeyboardButton("🏦 BINANCE")])
    buttons.append([KeyboardButton("❌ CANCEL")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


# ==================== HELPER FUNCTIONS ====================
def format_balance(balance):
    return f"{balance:.2f}"


def extract_otp(text):
    if not text or text == "No Content":
        return "N/A"
    spaced_otp = re.search(r"\b(\d{3}\s\d{3})\b", text)
    if spaced_otp:
        return spaced_otp.group(1).replace(" ", "")
    match = re.search(r"\b(\d{4,8})\b", text)
    return match.group(1) if match else "N/A"


def normalize_number(num):
    return re.sub(r"\D", "", str(num))


def mask_number(num):
    if len(num) > 6:
        return f"{num[:4]}****{num[-6:]}"
    return num


def get_date_reset_time():
    now = datetime.now()
    today_midnight = datetime(now.year, now.month, now.day, 0, 0, 0)
    return today_midnight


def is_valid_bangladesh_number(number):
    number = re.sub(r"\D", "", str(number))
    return len(number) == 11 and number.startswith("01")


def is_range_request(param):
    return "X" in param.upper() or param.replace("X", "").replace("x", "").isdigit()


# ==================== DATABASE ====================
def load_data(filename=USER_DATA_FILE):
    if not os.path.exists(filename):
        with open(filename, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except:
        return {}


def save_data(data, filename=USER_DATA_FILE):
    atomic_save(data, filename)


def get_user(uid):
    uid = str(uid)
    data = load_data()
    if uid not in data:
        data[uid] = {
            "user_id": uid,
            "balance": 0.0,
            "total_numbers": 0,
            "verified": False,
        }
        save_data(data)
    return data[uid]


async def update_db_balance(uid, amount):
    uid = str(uid)
    data = load_data()
    if uid in data:
        data[uid]["balance"] = round(data[uid].get("balance", 0.0) + amount, 2)
        save_data(data)
        return data[uid]["balance"]
    return 0.0


def get_all_users():
    data = load_data(USER_DATA_FILE)
    return list(data.keys()) if data else []


def user_exists(uid):
    data = load_data(USER_DATA_FILE)
    return str(uid) in data


# ==================== STATS ====================
def load_stats():
    if not os.path.exists(STATS_FILE):
        with open(STATS_FILE, "w") as f:
            json.dump({}, f)
        return {}
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=4)


def add_number_taken(uid, count=1):
    uid = str(uid)
    stats = load_stats()
    if uid not in stats:
        stats[uid] = {"numbers_taken": [], "otps_received": []}
    now = datetime.now().isoformat()
    for _ in range(count):
        stats[uid]["numbers_taken"].append(now)
    log_global_activity(uid, "NUMBER_TAKEN", {"count": count})
    save_stats(stats)


def add_otp_received(uid):
    uid = str(uid)
    stats = load_stats()
    if uid not in stats:
        stats[uid] = {"numbers_taken": [], "otps_received": []}
    stats[uid]["otps_received"].append(datetime.now().isoformat())
    save_stats(stats)


def get_user_stats(uid):
    uid = str(uid)
    stats = load_stats()
    user_stats = stats.get(uid, {"numbers_taken": [], "otps_received": []})
    now = datetime.now()
    today_midnight = get_date_reset_time()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    numbers_taken = user_stats.get("numbers_taken", [])
    otps_received = user_stats.get("otps_received", [])
    today_numbers = sum(
        1 for t in numbers_taken if datetime.fromisoformat(t) >= today_midnight
    )
    today_otps = sum(
        1 for t in otps_received if datetime.fromisoformat(t) >= today_midnight
    )
    last24h_numbers = sum(
        1 for t in numbers_taken if datetime.fromisoformat(t) > last_24h
    )
    last24h_otps = sum(1 for t in otps_received if datetime.fromisoformat(t) > last_24h)
    last7d_numbers = sum(
        1 for t in numbers_taken if datetime.fromisoformat(t) > last_7d
    )
    last7d_otps = sum(1 for t in otps_received if datetime.fromisoformat(t) > last_7d)
    total_numbers = len(numbers_taken)
    total_otps = len(otps_received)
    return {
        "total_numbers": total_numbers,
        "total_otps": total_otps,
        "today_numbers": today_numbers,
        "today_otps": today_otps,
        "last24h_numbers": last24h_numbers,
        "last24h_otps": last24h_otps,
        "last7d_numbers": last7d_numbers,
        "last7d_otps": last7d_otps,
    }


def log_global_activity(uid, action, details):
    if not os.path.exists(ACTIVITY_LOGS_FILE):
        with open(ACTIVITY_LOGS_FILE, "w") as f:
            json.dump([], f)
    try:
        with open(ACTIVITY_LOGS_FILE, "r") as f:
            logs = json.load(f)
    except:
        logs = []
    now = datetime.now()
    logs.append(
        {
            "uid": str(uid),
            "action": action,
            "details": details,
            "timestamp": now.isoformat(),
            "date": now.strftime("%d/%m/%Y"),
            "time": now.strftime("%H:%M:%S"),
        }
    )
    with open(ACTIVITY_LOGS_FILE, "w") as f:
        json.dump(logs, f, indent=4)


def get_global_system_stats():
    stats = load_stats()
    now = datetime.now()
    today_midnight = datetime(now.year, now.month, now.day)
    last_7d = now - timedelta(days=7)
    total_n = total_o = today_n = today_o = seven_n = seven_o = 0
    for uid in stats:
        u = stats[uid]
        n_list = u.get("numbers_taken", [])
        o_list = u.get("otps_received", [])
        total_n += len(n_list)
        total_o += len(o_list)
        for t in n_list:
            dt = datetime.fromisoformat(t)
            if dt >= today_midnight:
                today_n += 1
            if dt >= last_7d:
                seven_n += 1
        for t in o_list:
            dt = datetime.fromisoformat(t)
            if dt >= today_midnight:
                today_o += 1
            if dt >= last_7d:
                seven_o += 1
    return today_n, today_o, seven_n, seven_o, total_n, total_o


# ==================== LEADERBOARD ====================
async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.effective_message.reply_text(
            "🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid)
        )
        return
    stats_data = load_stats()
    today_midnight = get_date_reset_time()
    user_data_all = load_data(USER_DATA_FILE)
    user_today_counts = []
    for uid_str, user_stats in stats_data.items():
        otps_received = user_stats.get("otps_received", [])
        today_count = 0
        for ts in otps_received:
            try:
                dt = datetime.fromisoformat(ts)
                if dt >= today_midnight:
                    today_count += 1
            except:
                continue
        if today_count > 0:
            name = user_data_all.get(uid_str, {}).get("full_name")
            if not name:
                name = user_data_all.get(uid_str, {}).get("username")
            if not name:
                name = f"User {uid_str}"
            user_today_counts.append((uid_str, today_count, html.escape(name)))
    user_today_counts.sort(key=lambda x: x[1], reverse=True)
    top10 = user_today_counts[:10]
    if not top10:
        msg = (
            "<b>🏆 TOP 10 OTP LEADERBOARD 🏆</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            '❌ Hələ heç kim OTP almayıb.\n'
        )
    else:
        msg = "<b>🏆 TOP 10 OTP RECEIVERS (TODAY) 🏆</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for idx, (uid_str, count, name) in enumerate(top10, 1):
            if idx == 1:
                medal = "🥇"
            elif idx == 2:
                medal = "🥈"
            elif idx == 3:
                medal = "🥉"
            else:
                medal = f"{idx}️⃣"
            msg += f"{medal} <b>{name}</b>\n   🔑 <code>{count}</code> OTPs\n\n"
        msg += '━━━━━━━━━━━━━━━━━━━━\n📊 <i>Hər gün gecə saat 12-də sıfırlanır</i>'
    await update.effective_message.reply_text(
        msg, parse_mode="HTML", reply_markup=main_keyboard(uid)
    )


# ==================== 2FA ====================
def generate_2fa_code(secret_key):
    try:
        clean_secret = secret_key.replace(" ", "").strip()
        totp = pyotp.TOTP(clean_secret)
        otp = totp.now()
        return otp, clean_secret
    except:
        return None, None


async def get_2fa_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.effective_message.reply_text(
            "🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid)
        )
        return
    context.user_data["mode"] = "get_2fa"
    await update.effective_message.reply_text(
        "⚡ <b>GET 2FA CODE</b> ⚡\n\n"
        "<blockquote>🔑 ENTER YOUR 2FA SECRET KEY:</blockquote>",
        parse_mode="HTML",
    )


async def process_2fa_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    secret_key = update.message.text.strip()
    context.user_data["mode"] = None
    otp_code, clean_key = generate_2fa_code(secret_key)
    if otp_code is None:
        await update.effective_message.reply_text(
            "❌ <b>INVALID 2FA SECRET KEY</b>\n\n⚠️ Please send a valid base32 key.",
            parse_mode="HTML",
            reply_markup=main_keyboard(uid),
        )
        return
    now = datetime.now()
    final_msg = (
        "✅ <b>2FA CODE GENERATED!</b>\n\n"
        f"<blockquote>🔑 KEY: <code>{clean_key}</code></blockquote>\n"
        f"<blockquote>🔢 CODE: <code>{otp_code}</code></blockquote>\n"
        f"<blockquote>⏳ EXPIRES IN: 30 SECONDS</blockquote>\n"
        f"📅 {now.strftime('%d %B, %Y')} | {now.strftime('%I:%M %p')}"
    )
    await update.effective_message.reply_text(
        final_msg, parse_mode="HTML",
        reply_markup=otp_copy_keyboard(otp_code, get_user_language(uid)),
    )


# ==================== GET NUMBER — SERVICE SELECTION ====================
_SVC_STYLES = [
    "danger",
    "primary",
    "success",
    "danger",
    "primary",
    "success",
    "danger",
    "primary",
    "success",
    "danger",
    "primary",
    "success",
]
_RANGE_EMOJIS = [
    "🚀",
    "🔥",
    "✨",
    "💎",
    "📱",
    "⚡",
    "🌟",
    "💫",
    "⭐",
    "🌀",
    "🌈",
    "🍀",
    "💥",
    "🎯",
    "🔮",
    "💡",
    "🪄",
    "🎨",
    "🏆",
    "🎖️",
]


def get_range_emoji(range_str):
    hash_val = hash(range_str) % len(_RANGE_EMOJIS)
    return _RANGE_EMOJIS[hash_val]


def get_flag_by_prefix(range_str):
    prefix = re.sub(r"[^0-9]", "", range_str)
    if not prefix:
        return None
    sorted_prefixes = sorted(COUNTRY_PREFIX_MAP.keys(), key=len, reverse=True)
    for p in sorted_prefixes:
        if prefix.startswith(p):
            return COUNTRY_PREFIX_MAP[p][0]
    return None


def _build_services_keyboard(services):
    buttons = []
    emoji_map = {
        "whatsapp": "💚",
        "facebook": "📘",
        "discord": "🎮",
        "telegram": "✈️",
        "instagram": "📸",
        "twitter": "🐦",
        "tiktok": "🎵",
        "snapchat": "👻",
        "google": "🔍",
        "gmail": "📧",
        "outlook": "📧",
        "yahoo": "🔮",
        "binance": "💰",
        "coinbase": "₿",
        "paypal": "💳",
        "amazon": "🛒",
        "netflix": "🎬",
        "spotify": "🎧",
        "uber": "🚗",
        "bolt": "⚡",
        "apple": "🍎",
        "icloud": "☁️",
        "microsoft": "🪟",
        "bkash": "💸",
        "nagad": "💵",
        "rocket": "🚀",
        "upay": "🏦",
        "line": "💬",
        "wechat": "💬",
        "viber": "📞",
        "signal": "🔒",
        "pubg": "🎯",
        "freefire": "🔥",
    }
    for i, svc in enumerate(services.keys()):
        emoji = emoji_map.get(svc, "📡")
        display = f"{emoji} {svc.capitalize()}"
        color = _SVC_STYLES[i % len(_SVC_STYLES)]
        buttons.append(
            InlineKeyboardButton(display, callback_data=f"svcidx_{i}", style=color)
        )
    rows = [buttons[j : j + 2] for j in range(0, len(buttons), 2)]
    rows.append(
        [
            InlineKeyboardButton("⚙️ CUSTOM RANGE", callback_data="custom_range", style="danger"),
            InlineKeyboardButton("🔙 BACK TO MAIN", callback_data="back_to_main"),
        ]
    )
    return InlineKeyboardMarkup(rows)


def _build_countries_keyboard(ranges, service, uid):
    countries = _collect_all_countries({service: ranges})
    rows = []
    for info in countries:
        label = f"{info['flag']} {info['name']} ({len(info['ranges'])})"
        if info["prefix"] == "994" and not az_range_allowed(uid):
            label += " 🔒"
        if is_country_hot(info["prefix"]):
            label += " 🔥"
        rows.append([InlineKeyboardButton(
            label, callback_data=f"menu_service_country_{info['prefix']}",
        )])
    rows.append([InlineKeyboardButton("◀️ BACK", callback_data="back_services")])
    return InlineKeyboardMarkup(rows)


def _collect_all_countries(services):
    """Keep every distinct range under its country, across all services."""
    countries = {}
    for service, ranges in sorted(services.items()):
        for range_text in ranges or []:
            rid = re.sub(r"[^0-9]", "", str(range_text))
            prefix = get_country_prefix_from_number(rid) if rid else ""
            if not prefix:
                continue
            if prefix not in countries:
                flag, name = get_country_by_prefix(prefix)
                countries[prefix] = {
                    "flag": flag, "name": name, "prefix": prefix,
                    "rid": rid, "service": service, "ranges": {},
                }
            countries[prefix]["ranges"].setdefault(rid, {
                "rid": rid, "service": service, "display": str(range_text),
            })
    for info in countries.values():
        info["ranges"] = sorted(info["ranges"].values(), key=lambda row: row["rid"])
    return sorted(countries.values(), key=lambda row: row["name"].casefold())


async def show_country_ranges(update, context, info=None, back=None, page=0):
    if info is not None:
        token = "".join(random.choices(string.ascii_letters + string.digits, k=10))
        context.user_data["country_range_view"] = {
            "info": info, "back": back, "token": token,
        }
    view = context.user_data.get("country_range_view")
    if not view:
        await show_all_countries(update, context)
        return
    info, token = view["info"], view["token"]
    entries = info["ranges"]
    size = 30
    pages = max(1, (len(entries) + size - 1) // size)
    page = max(0, min(page, pages - 1))
    rows = [[InlineKeyboardButton(
        f"📶 {entry['display']} · {entry['service']}", callback_data=f"menu_range_pick_{token}_{index}",
    )] for index, entry in enumerate(entries)
        if page * size <= index < (page + 1) * size]
    nav = []
    if page:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"menu_range_page_{token}_{page - 1}"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"menu_range_page_{token}_{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🔙", callback_data=view["back"])])
    lang = get_user_language(update.effective_user.id)
    title = f"{info['flag']} {info['name']} — {len(entries)} range\n\n"
    if info.get("is_shared"):
        title += "⚠️ Bu telefon kodu bir neçə ölkə arasında paylaşılır. " \
                 "API range-i konkret ölkəyə təsdiqləmir.\n\n"
    title += t(lang, "choose_range")
    if pages > 1:
        title += f"\n{page + 1}/{pages}"
    await update.effective_message.reply_text(title, reply_markup=InlineKeyboardMarkup(rows))



async def show_az_operator_menu(query, uid):
    rows = [
        [InlineKeyboardButton(
            f"🇦🇿 {name}" + ("" if az_range_allowed(uid) else " 🔒"),
            callback_data=f"az_operator_{key}",
        )]
        for key, name, prefixes in AZ_OPERATOR_PREFIXES
    ]
    rows.append([InlineKeyboardButton("🔙 Geri", callback_data="menu_all_countries")])
    await query.message.reply_text(
        "🇦🇿 AZƏRBAYCAN OPERATORLARI\n"
        "Hər prefiks üzrə 210 və 211 alt-range-ləri göstərilir.\n"
        "Range-in menyuda görünməsi nömrə mövcudluğunu təsdiqləmir.\n"
        + ("" if az_range_allowed(uid) else "\n" + AZ_ACCESS_DENIED),
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def show_az_prefix_menu(query, operator_id):
    operator = az_catalog_lookup(operator_id=operator_id)
    if not operator:
        await query.message.reply_text("❌ Operator tapılmadı.")
        return
    rows = [
        [InlineKeyboardButton("📱 +" + prefix, callback_data=f"az_prefix_{prefix}")]
        for prefix in operator["prefixes"]
    ]
    rows.append([InlineKeyboardButton("◀️ Operatorlar", callback_data="menu_az_ranges")])
    await query.message.reply_text(
        f"🇦🇿 {operator['name']} — prefiks seçin:",
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def show_az_suffix_menu(query, uid, prefix, page=0):
    operator = az_catalog_lookup(prefix=prefix)
    if not operator:
        await query.message.reply_text("❌ Prefiks tapılmadı.")
        return
    services = await fetch_services_cached()
    group = next(row for row in az_range_catalog(services) if row["id"] == operator["id"])
    rows_for_prefix = next(row for row in group["prefixes"] if row["prefix"] == prefix)
    entries = rows_for_prefix["ranges"]
    page_size = 20
    total_pages = max(1, (len(entries) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    rows = []
    for entry in entries[page * page_size:(page + 1) * page_size]:
        status = "📡 API" if entry["listed_in_api"] else "❔ Yoxlanmayıb"
        lock = "" if az_range_allowed(uid) else " 🔒"
        rows.append([InlineKeyboardButton(
            f"{entry['rid']} · {status}{lock}",
            callback_data=f"az_pick_{entry['rid']}",
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"az_page_{prefix}_{page - 1}"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"az_page_{prefix}_{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(
        "◀️ Prefikslər", callback_data=f"az_operator_{operator['id']}"
    )])
    await query.message.reply_text(
        f"🇦🇿 {operator['name']} / +{prefix} — {len(entries)} range "
        f"({page + 1}/{total_pages})\n"
        "210/211 + API-nin bildirdiyi əlavə range-lər. "
        "Siyahıda olması aktiv nömrəyə zəmanət deyil.",
        reply_markup=InlineKeyboardMarkup(rows),
    )

async def show_all_countries(update, context, page=0, refresh=True):
    """Show the full country-code directory, not just API-positive countries."""
    uid = update.effective_user.id
    lang = get_user_language(uid)
    if refresh or "all_country_rows" not in context.user_data:
        services = await fetch_services_cached()
        context.user_data["all_country_rows"] = build_all_country_rows(services)
    countries = context.user_data["all_country_rows"]
    page_size = 25
    pages = max(1, (len(countries) + page_size - 1) // page_size)
    page = max(0, min(page, pages - 1))
    rows = []
    for info in countries[page * page_size:(page + 1) * page_size]:
        count = len(info["ranges"])
        label = f"{info['flag']} {info['name']} (+{info['prefix']}) · {count}"
        if info["prefix"] == "994" and not az_range_allowed(uid):
            label += " 🔒"
        rows.append([InlineKeyboardButton(
            label, callback_data=f"menu_all_country_{info['iso']}"
        )])
    navigation = []
    if page:
        navigation.append(InlineKeyboardButton(
            "◀️", callback_data=f"menu_countries_page_{page - 1}"
        ))
    if page + 1 < pages:
        navigation.append(InlineKeyboardButton(
            "▶️", callback_data=f"menu_countries_page_{page + 1}"
        ))
    if navigation:
        rows.append(navigation)
    rows.append([InlineKeyboardButton(
        t(lang, "countries_back"), callback_data="back_to_main"
    )])
    available = sum(bool(country["ranges"]) for country in countries)
    text = (
        f"🌍 <b>BÜTÜN ÖLKƏLƏR VƏ TELEFON KODLARI</b>\n"
        f"Ölkə və ərazilər: <b>{len(countries)}</b>\n"
        f"API-də range görünən: <b>{available}</b>\n\n"
        "Ölkə yanında rəqəm API-də olan range sayıdır; "
        "0 olduqda nömrə yoxdur və ya API onu elan etmir.\n"
        "Eyni ölkə kodu bir neçə ölkə tərəfindən paylaşıla bilər.\n"
        f"Səhifə {page + 1}/{pages}"
    )
    await update.effective_message.reply_text(
        text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows)
    )


async def show_app_selection(update, context):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.effective_message.reply_text(
            "🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid)
        )
        return
    services = await fetch_services_cached()
    if not services:
        await update.effective_message.reply_text(
            '⚠️ <b>Heç bir xidmət mövcud deyil</b>\n⏳ Bir azdan yenidən cəhd edin.',
            parse_mode="HTML",
            reply_markup=main_keyboard(uid),
        )
        return
    # Show every service currently returned by the upstream API.
    # New services (for example Bolt) appear automatically without a code update.
    filtered_services = dict(sorted(services.items()))
    if not filtered_services:
        await update.effective_message.reply_text(
            '⚠️ <b>Heç bir xidmət mövcud deyil</b>\n⏳ Bir azdan yenidən cəhd edin.',
            parse_mode="HTML",
            reply_markup=main_keyboard(uid),
        )
        return
    context.user_data["la_services"] = filtered_services
    keyboard = _build_services_keyboard(filtered_services)
    await update.effective_message.reply_text(
        "📡✨ XİDMƏT SEÇİN ✨📡\n\n"
        "<blockquote>API-də hazırda mövcud olan bütün xidmətlər aşağıda göstərilir.</blockquote>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )



# ==================== AUTO OTP MONITOR (REAL) ====================
# Safe monitor diagnostics: records transport/health metadata only.
# SMS bodies, OTP values, phone numbers and user identifiers are never stored here.
monitor_diagnostics = {
    "state": "starting",
    "last_check": None,
    "last_success": None,
    "http_status": None,
    "upstream_code": None,
    "items_seen": 0,
    "last_error": None,
}


def _monitor_diag_time():
    return datetime.now().isoformat(timespec="seconds")


async def monitor_loop(app):
    sent_otps = set()
    while True:
        try:
            monitor_diagnostics["state"] = "checking"
            monitor_diagnostics["last_check"] = _monitor_diag_time()
            r = await client_async.get(f"{BASE_URL}/success-otp")
            monitor_diagnostics["http_status"] = r.status_code
            r.raise_for_status()
            result = r.json()
            upstream_code = result.get("meta", {}).get("code")
            monitor_diagnostics["upstream_code"] = upstream_code
            if upstream_code == 200:
                data_obj = result.get("data")
                if isinstance(data_obj, dict) and "otps" in data_obj:
                    otps = data_obj.get("otps", [])
                elif isinstance(data_obj, list):
                    otps = data_obj
                else:
                    otps = []
                monitor_diagnostics["state"] = "ok"
                monitor_diagnostics["last_success"] = _monitor_diag_time()
                monitor_diagnostics["items_seen"] = len(otps)
                monitor_diagnostics["last_error"] = None
                paid_data = load_data(PAID_SMS_FILE)
                paid_keys_set = set(paid_data.keys())
                for otp in otps:
                    number = otp.get("number")
                    if not number:
                        continue
                    full_sms = otp.get("message", "No SMS Content")
                    otp_time = otp.get("time", "")
                    otp_code = extract_otp(full_sms)
                    key = f"{normalize_number(number)}_{otp_time}"
                    if key in sent_otps:
                        continue
                    num = normalize_number(number)
                    sms_key = f"{num}_{full_sms[:50]}"
                    if num in active_numbers and sms_key not in paid_keys_set:
                        sent_otps.add(key)
                        details = active_numbers[num]
                        uid = details["uid"]
                        service_name = detect_service(full_sms)
                        is_free_service = service_name in ("TELEGRAM", "WHATSAPP")
                        if not is_free_service:
                            user_rate = get_user_otp_rate(uid)
                            await update_db_balance(uid, user_rate)
                            add_otp_received(uid)
                            log_global_activity(
                                uid,
                                "OTP_RECEIVED",
                                {"number": num, "otp": otp_code, "sms": full_sms},
                            )
                            update_country_otp_count(num)
                        else:
                            log_global_activity(
                                uid,
                                "OTP_RECEIVED_FREE",
                                {
                                    "number": num,
                                    "otp": otp_code,
                                    "service": service_name,
                                },
                            )
                        paid_keys_set.add(sms_key)
                        paid_data[sms_key] = {"uid": uid, "otp": otp_code}
                        num_range_info = active_numbers.get(num, {}).get("range", "")
                        if not num_range_info:
                            num_range_info = (
                                (num[:-3] + "XXX") if len(num) > 3 else (num + "XXX")
                            )
                        country_flag, country_name = get_country_info(num)
                        clean_num = num.replace("+", "").strip()
                        full_number = f"+{clean_num}"
                        masked_number = f"+{mask_number(clean_num)}"
                        safe_full_sms = html.escape(str(full_sms))
                        safe_otp_code = html.escape(str(otp_code))
                        if is_free_service:
                            balance_msg = (
                                "xoş sözdər eşidəsən ay qa)"
                            )
                        else:
                            user_rate = get_user_otp_rate(uid)
                            balance_msg = f"💵 ADD BALANCE FOR {user_rate:.2f} AZN"
                        user_msg = (
                            f"✅ <b>OTP RECEIVE SUCCESSFUL</b> ✅\n\n"
                            f"<blockquote>📶 RANGE: <code>{num_range_info}</code></blockquote>\n"
                            f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
                            f"<blockquote>📱 SERVICE: <code>{service_name}</code></blockquote>\n"
                            f"<blockquote>📞 NUMBER: <code>{full_number}</code></blockquote>\n"
                            f"<blockquote>🔑 OTP: <code>{safe_otp_code}</code></blockquote>\n\n"
                            f"<blockquote>📩 FULL SMS:\n<code>{safe_full_sms}</code></blockquote>\n\n"
                            f"<b>{balance_msg}</b>"
                        )
                        group_msg = (
                            f"✅ <b>OTP RECEIVE SUCCESSFUL</b> ✅\n\n"
                            f"<blockquote>📶 RANGE: <code>{num_range_info}</code></blockquote>\n"
                            f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
                            f"<blockquote>📱 SERVICE: <code>{service_name}</code></blockquote>\n"
                            f"<blockquote>📞 NUMBER: <code>{masked_number}</code></blockquote>\n"
                            f"<blockquote>🔑 OTP: <code>{safe_otp_code}</code></blockquote>\n\n"
                            f"<blockquote>📩 FULL SMS:\n<code>{safe_full_sms}</code></blockquote>"
                        )
                        
                        # DÜZƏLDİLMİŞ BÖLGƏ: URL formatı tam yazıldı
                        group_buttons = InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        "‼️ PANEL",
                                        url="https://t.me/ivaaaaasms_bot",
                                        style="danger",
                                    ),
                                    InlineKeyboardButton(
                                        "📢 Admin",
                                        url="https://t.me/betrunaz",
                                        style="success",
                                    ),
                                ]
                            ]
                        )
                        
                        try:
                            await app.bot.send_message(
                                uid, user_msg, parse_mode="HTML",
                                reply_markup=otp_copy_keyboard(otp_code, get_user_language(uid)),
                            )
                            miniapp_incoming_sms.setdefault(uid, []).insert(0, {
                                "service": service_name,
                                "number": full_number,
                                "otp": otp_code,
                                "message": full_sms,
                                "time": datetime.now().strftime("%H:%M:%S")
                            })
                            miniapp_incoming_sms[uid] = miniapp_incoming_sms[uid][:20]
                        except Exception as e:
                            print(f"❌ User Message Send Fail: {e}")
                            
                        try:
                            await app.bot.send_message(
                                OTP_GROUP_ID,
                                group_msg,
                                parse_mode="HTML",
                                reply_markup=group_buttons,
                            )
                            print("✅ OTP mesajı qrupa uğurla göndərildi.")
                        except Exception as e:
                            print(f"❌ Group Send Fail: {e}")

                        save_data(paid_data, PAID_SMS_FILE)
                current_time = datetime.now()
                for num_key in list(active_numbers.keys()):
                    entry = active_numbers[num_key]
                    if "timestamp" not in entry:
                        entry["timestamp"] = current_time
                    elif (current_time - entry["timestamp"]).total_seconds() > 3600:
                        del active_numbers[num_key]
            else:
                monitor_diagnostics["state"] = "upstream_error"
                monitor_diagnostics["last_error"] = f"API code: {upstream_code}"
        except Exception as e:
            monitor_diagnostics["state"] = "error"
            monitor_diagnostics["last_error"] = type(e).__name__
            print(f"Monitor Error: {type(e).__name__}")
        await asyncio.sleep(CHECK_INTERVAL)


# ==================== FAKE OTP LOOP ====================
async def fake_otp_loop(app):
    """Admin-controlled synthetic OTP demo generator. Never uses real numbers or real SMS data."""
    while True:
        try:
            config = load_fake_otp_config()
            if not config.get("running", False):
                await asyncio.sleep(3)
                continue

            interval = max(10, int(config.get("interval", 10)))
            otp_digits = min(8, max(4, int(config.get("otp_digits", 6))))
            service = str(config.get("service", "DEMO")).strip() or "DEMO"

            # Synthetic-only test data. The phone field is intentionally non-dialable/masked.
            demo_id = "TEST-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            otp_code = "".join(random.choices(string.digits, k=otp_digits))
            masked_phone = "+994 50 XXX XX " + "".join(random.choices(string.digits, k=2))
            safe_service = html.escape(service.upper())
            safe_demo_id = html.escape(demo_id)
            safe_phone = html.escape(masked_phone)
            safe_otp = html.escape(otp_code)

            # Keep the card visually close to a normal status card, while retaining a clear
            # disclosure so synthetic authentication data is never presented as genuine.
            group_msg = (
                "🇦🇿 <b>Azərbaycan</b>\n\n"
                f"📱 <code>{safe_phone}</code>\n"
                f"🔐 <code>{safe_otp}</code>\n"
                f"📦 <b>{safe_service}</b>\n"
                "🟢 <b>Aktiv</b>\n\n"
                "<i>Test məlumatı</i>"
            )

            try:
                await app.bot.send_message(
                    OTP_GROUP_ID, group_msg, parse_mode="HTML",
                    reply_markup=otp_copy_keyboard(otp_code),
                )
                config = load_fake_otp_config()
                config["sent_count"] = int(config.get("sent_count", 0)) + 1
                save_fake_otp_config(config)
                log_global_activity("SYSTEM", "DEMO_OTP_SENT", {"test_id": demo_id})
            except Exception as e:
                print(f"❌ Demo OTP göndərilmədi: {e}")

            await asyncio.sleep(interval)
        except Exception as e:
            print(f"Demo OTP loop error: {e}")
            await asyncio.sleep(5)



async def download_numbers_txt(update, context, all_numbers=False):
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return
    if not update.effective_chat or update.effective_chat.type != "private":
        await message.reply_text("TXT faylını botun şəxsi çatından endirin.")
        return
    uid = user.id
    if is_user_banned(uid):
        await message.reply_text("🚫 Girişiniz məhdudlaşdırılıb.")
        return
    if all_numbers and not is_admin(uid):
        await message.reply_text("Bu komanda yalnız admin üçündür.")
        return
    for channel in load_required_channels():
        joined, _ = await check_user_joined(context.bot, uid, channel)
        if not joined:
            await message.reply_text("Əvvəlcə /start ilə tələb olunan kanal/qrupa qoşulun.")
            return
    text = await asyncio.to_thread(number_archive.text, None if all_numbers else uid)
    if not text:
        await message.reply_text("Endirmək üçün saxlanmış nömrə yoxdur.")
        return
    for index, content in enumerate(txt_chunks(text), 1):
        prefix = "all_numbers" if all_numbers else "my_numbers"
        await message.reply_document(
            document=io.BytesIO(content), filename=f"{prefix}_{index}.txt",
            caption=f"📥 Nömrə arxivi • {content.count(bytes([10]))} nömrə",
        )


async def numbers_txt_command(update, context):
    await download_numbers_txt(update, context)


async def all_numbers_txt_command(update, context):
    await download_numbers_txt(update, context, all_numbers=True)


async def numbers_status_command(update, context):
    if (update.effective_user and is_admin(update.effective_user.id)
            and update.effective_chat and update.effective_chat.type == "private"
            and not is_user_banned(update.effective_user.id)):
        await update.effective_message.reply_text(number_archive.status)


async def show_active_numbers(update, context):
    """Show only the current user's active allocations and their local lifecycle status."""
    uid = update.effective_user.id
    now = datetime.now()
    rows = []
    for number, info in list(active_numbers.items()):
        if info.get("uid") != uid:
            continue
        ts = info.get("timestamp") or now
        age = max(0, int((now - ts).total_seconds()))
        if age >= 3600:
            continue
        remaining = max(0, 3600 - age)
        mins, secs = divmod(remaining, 60)
        rows.append((ts, number, info.get("range", "—"), mins, secs))

    rows.sort(reverse=True)
    if not rows:
        await update.effective_message.reply_text(
            "📋 <b>AKTİV NÖMRƏLƏR</b>\n\nHazırda aktiv nömrəniz yoxdur.",
            parse_mode="HTML", reply_markup=main_keyboard(uid)
        )
        return

    lines = [f"📋 <b>AKTİV NÖMRƏLƏR ({len(rows)})</b>", ""]
    for i, (_, number, range_text, mins, secs) in enumerate(rows, 1):
        lines.append(
            f"<blockquote><b>{i}.</b> 📞 <code>+{normalize_number(number)}</code>\n"
            f"📶 Range: <code>{html.escape(str(range_text))}</code>\n"
            f"🟢 Status: AKTİV\n"
            f"⏳ Qalan vaxt: {mins:02d}:{secs:02d}</blockquote>"
        )
    lines.append("\nℹ️ Bu status yalnız Aze Sms Panel-dəki aktiv sifariş vəziyyətini göstərir; üçüncü tərəf tətbiqlərində hesab mövcudluğunu yoxlamır.")
    await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML", reply_markup=main_keyboard(uid))


# ==================== WORKER & API ====================
async def fast_allocate_number(query, context, rid, service, range_display):
    uid = query.from_user.id
    if is_az_range(rid) and not az_range_allowed(uid):
        await query.message.reply_text(AZ_ACCESS_DENIED)
        return
    if is_user_banned(uid):
        await query.message.edit_text("🚫 YOU ARE BANNED 🚫")
        return
    try:
        num, country = await get_number_from_api(rid, requester_id=uid)
    except Exception as e:
        await query.message.edit_text(f"❌ Server error: {str(e)[:100]}")
        return
    if not num:
        await query.message.edit_text(
            '❌ <b>Nömrə tapılmadı.</b>\n\n'
            '<blockquote>⚠️ Bu diapazonda hazırda nömrə yoxdur və ya server məşğuldur.\n'
            'Başqa diapazonu sınayın.</blockquote>',
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 BACK", callback_data="back_services", style="danger"
                        )
                    ]
                ]
            ),
        )
        return
    clean_num = normalize_number(num)
    add_number_taken(uid, 1)
    last_range[uid] = rid
    active_numbers[clean_num] = {
        "uid": uid,
        "range": range_display,
        "timestamp": datetime.now(),
    }
    save_number_range_info(uid, clean_num, range_display)
    country_flag, country_name = get_country_info(clean_num)
    text = (
        f"✅ <b>YOUR NUMBER</b> ✅\n\n"
        f"<blockquote>🌍 COUNTRY: <code>{country_flag} {html.escape(country_name)}</code></blockquote>\n"
        f"<blockquote>📶 RANGE: <code>{range_display}</code></blockquote>\n"
        f"<blockquote>📱 SERVICE: <code>{service.upper()}</code></blockquote>\n"
        f"<blockquote>📞 NUMBER: <code>{num}</code></blockquote>\n\n"
        f"<b>📩 SMS STATUS: ⏳ WAITING...</b>"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔄 SAME RANGE",
                    callback_data=f"same_range_{rid}_{service}",
                    style="success",
                )
            ],
            [
                InlineKeyboardButton(
                    "📢 OTP GROUP", url="https://t.me/betrunaz", style="primary"
                )
            ],
            [InlineKeyboardButton("◀️ BACK", callback_data="back_to_services")],
        ]
    )
    try:
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        print(f"fast_allocate edit error: {e}")


async def worker():
    while True:
        task = await request_queue.get()
        try:
            if task["type"] == "process_numbers":
                await process_numbers(
                    task["update"],
                    task["context"],
                    task["range_text"],
                    task["count"],
                    task.get("service", ""),
                )
            elif task["type"] == "search_otp":
                await perform_otp_search(
                    task["update"], task["context"], task["target_num"]
                )
            elif task["type"] == "auto_number":
                await process_auto_number(
                    task["update"], task["context"], task["range_text"]
                )
        except Exception as e:
            print(f"Worker Error: {e}")
        finally:
            request_queue.task_done()


async def process_auto_number(update, context, range_text):
    uid = update.effective_user.id
    if is_az_range(range_text) and not az_range_allowed(uid):
        await update.effective_message.reply_text(AZ_ACCESS_DENIED)
        return
    chat_id = update.effective_chat.id
    if is_user_banned(uid):
        await context.bot.send_message(
            chat_id=chat_id,
            text="🚫 YOU ARE BANNED 🚫",
            reply_markup=main_keyboard(uid),
        )
        return
    status_msg = await context.bot.send_message(chat_id=chat_id, text="🔍 SEARCHING...")
    rid = re.sub(r"[^0-9]", "", range_text)
    if not rid:
        await status_msg.edit_text("❌ INVALID RANGE! Send numbers only.")
        return
    try:
        num, country = await get_number_from_api(rid, requester_id=uid)
        if not num:
            await status_msg.edit_text("❌ NO NUMBERS FOUND. TRY A VALID RANGE.")
            return
        clean_num = normalize_number(num)
        add_number_taken(uid, 1)
        last_range[uid] = rid
        active_numbers[clean_num] = {
            "uid": uid,
            "range": range_text,
            "timestamp": datetime.now(),
        }
        save_number_range_info(uid, clean_num, range_text)
        country_flag, country_name = get_country_info(clean_num)
        final_text = (
            f"✅ <b>YOUR NUMBER DETAILS</b> ✅\n\n"
            f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
            f"<blockquote>📶 RANGE: <code>{range_text}</code></blockquote>\n\n"
            f"<blockquote>📞 NUMBER: <code>{num}</code></blockquote>\n\n"
            f"<b>📩 SMS STATUS: ⏳ WAITING...</b>"
        )
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔄 SAME RANGE",
                        callback_data=f"same_range_{rid}_CUSTOM",
                        style="success",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📢 OTP GROUP", url="https://t.me/betrunaz", style="primary"
                    )
                ],
                [InlineKeyboardButton("◀️ BACK", callback_data="back_to_services")],
            ]
        )
        await status_msg.edit_text(final_text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        print(f"Auto Number Error: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)}")


async def process_numbers(update_or_query, context, range_text, count, service=""):
    if isinstance(update_or_query, Update) and update_or_query.callback_query:
        uid = update_or_query.callback_query.from_user.id
        chat_id = update_or_query.callback_query.message.chat_id
    else:
        uid = update_or_query.effective_user.id
        chat_id = update_or_query.effective_chat.id
    if is_user_banned(uid):
        await context.bot.send_message(
            chat_id=chat_id,
            text="🚫 YOU ARE BANNED 🚫",
            reply_markup=main_keyboard(uid),
        )
        return
    if is_az_range(range_text) and not az_range_allowed(uid):
        await context.bot.send_message(chat_id=chat_id, text=AZ_ACCESS_DENIED)
        return
    status_msg = await context.bot.send_message(
        chat_id=chat_id, text="🔍 SEARCHING . . ."
    )
    rid = re.sub(r"[^0-9]", "", range_text)
    if not rid:
        await status_msg.edit_text("❌ INVALID RANGE!")
        return
    try:
        add_number_taken(uid, count)
        last_range[uid] = rid
        num, country = await get_number_from_api(rid, requester_id=uid)
        if not num:
            await status_msg.edit_text("❌ NO NUMBERS FOUND. TRY A VALID RANGE.")
            return
        clean_num = normalize_number(num)
        active_numbers[clean_num] = {
            "uid": uid,
            "range": range_text,
            "timestamp": datetime.now(),
        }
        save_number_range_info(uid, clean_num, range_text)
        country_flag, country_name = get_country_info(clean_num)
        final_text = (
            f"✅ <b>YOUR NUMBER DETAILS</b> ✅\n\n"
            f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
            f"<blockquote>📶 RANGE: <code>{range_text}</code></blockquote>\n"
            f"{f'<blockquote>📱 SERVICE: <code>{service.upper()}</code></blockquote>' if service else ''}\n"
            f"<blockquote>📞 NUMBER: <code>{num}</code></blockquote>\n\n"
            f"<b>📩 SMS STATUS: ⏳ WAITING...</b>"
        )
        svc = service if service else "CUSTOM"
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔄 SAME RANGE",
                        callback_data=f"same_range_{rid}_{svc}",
                        style="success",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📢 OTP GROUP", url="https://t.me/betrunaz", style="primary"
                    )
                ],
                [InlineKeyboardButton("◀️ BACK", callback_data="back_to_services")],
            ]
        )
        await status_msg.edit_text(final_text, parse_mode="HTML", reply_markup=keyboard)
    except Exception as e:
        print(f"Process Number Error: {e}")
        await status_msg.edit_text(f"❌ System Error: {str(e)}")


async def perform_otp_search(update, context, target_num):
    uid = str(update.effective_user.id)
    if is_user_banned(int(uid)):
        await update.effective_message.reply_text(
            "🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(int(uid))
        )
        return
    if is_az_range(target_num):
        if not az_range_allowed(uid):
            await update.effective_message.reply_text(AZ_ACCESS_DENIED)
            return
        # Approval to obtain an AZ number must not expose other users' codes.
        if not is_admin(int(uid)):
            assigned = active_numbers.get(normalize_number(target_num))
            if not assigned or str(assigned.get("uid")) != uid:
                await update.effective_message.reply_text(
                    "🔒 Yalnız sizə ayrılmış Azərbaycan nömrəsinin mesajlarını yoxlaya bilərsiniz."
                )
                return
    status_msg = await update.effective_message.reply_text("🔍 SEARCHING IN SERVER...")
    try:
        r = await client_async.get(f"{BASE_URL}/success-otp")
        res = r.json()
        if res.get("meta", {}).get("code") == 200:
            data_obj = res.get("data")
            if isinstance(data_obj, dict) and "otps" in data_obj:
                all_otps = data_obj.get("otps", [])
            elif isinstance(data_obj, list):
                all_otps = data_obj
            else:
                all_otps = []
            found_otps = [
                o
                for o in all_otps
                if normalize_number(o.get("number", "")) == target_num
            ]
            if not found_otps:
                error_msg = (
                    "━━━━━━━━━━━━━━━━━━\n❌ NO OTP FOUND\n━━━━━━━━━━━━━━━━━━\n\n"
                    f"📞 NUMBER:\n`+{target_num}`\n\n⏳ PLEASE TRY AGAIN LATER\n━━━━━━━━━━━━━━━━━━"
                )
                await status_msg.edit_text(error_msg, parse_mode="Markdown")
                await update.effective_message.reply_text(
                    "🔙 RETURNING TO MAIN MENU...", reply_markup=main_keyboard(int(uid))
                )
            else:
                await status_msg.delete()
                paid_data = load_data(PAID_SMS_FILE)
                for o in found_otps:
                    full_sms = o.get("message", "No Content Found")
                    otp_code = extract_otp(full_sms)
                    otp_time = o.get("time", "")
                    key = f"{target_num}_{otp_time}"
                    if key in paid_data:
                        payment_status = "❌ ALREADY PAID"
                    else:
                        service_name = detect_service(full_sms)
                        is_free = service_name in ("TELEGRAM", "WHATSAPP")
                        if not is_free:
                            user_rate = get_user_otp_rate(int(uid))
                            await update_db_balance(uid, user_rate)
                            add_otp_received(uid)
                            payment_status = f"💵 ADD BALANCE FOR {user_rate:.2f} AZN"
                        else:
                            payment_status = (
                                '⚠️ Bu OTP üçün pul əlavə edilməyib (Telegram/WhatsApp)'
                            )
                        paid_data[key] = {"uid": uid, "otp": otp_code}
                    save_data(paid_data, PAID_SMS_FILE)
                    country_flag, country_name = get_country_info(target_num)
                    service_name = detect_service(full_sms)
                    msg = (
                        f"✅ <b>OTP FOUND!</b>\n\n"
                        f"<blockquote>🌍 COUNTRY: <code>{country_flag} {country_name}</code></blockquote>\n"
                        f"<blockquote>📱 SERVICE: <code>{service_name}</code></blockquote>\n"
                        f"<blockquote>📞 NUMBER: <code>+{target_num}</code></blockquote>\n"
                        f"<blockquote>🔑 OTP: <code>{html.escape(otp_code)}</code></blockquote>\n\n"
                        f"<blockquote>📩 FULL SMS:\n<code>{html.escape(str(full_sms))}</code></blockquote>\n\n"
                        f"<b>{payment_status}</b>"
                    )
                    await update.effective_message.reply_text(
                        msg, parse_mode="HTML",
                        reply_markup=otp_copy_keyboard(otp_code, get_user_language(int(uid)))
                    )
        else:
            await status_msg.edit_text("❌ SERVER RETURNED AN ERROR.")
            await update.effective_message.reply_text(
                "🔙 Returning to Main Menu...", reply_markup=main_keyboard(int(uid))
            )
    except Exception as e:
        try:
            await status_msg.edit_text(f"❌ Error: {str(e)}")
        except:
            await update.effective_message.reply_text(f"❌ Error: {str(e)}")
        await update.effective_message.reply_text(
            "🔙 Returning to Main Menu...", reply_markup=main_keyboard(int(uid))
        )


# ==================== WITHDRAW FUNCTIONS ====================
async def withdraw_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = normalize_button_input(update.message.text.strip())

    uid = update.effective_user.id
    if text == "❌ CANCEL":
        context.user_data["withdraw_mode"] = None
        await update.effective_message.reply_text(
            "❌ WITHDRAW CANCELLED", reply_markup=main_keyboard(uid)
        )
        return
    method_map = {
        "📱 BKASH": "BKASH",
        "💵 NAGAD": "NAGAD",
        "🚀 ROCKET": "ROCKET",
        "🏦 BINANCE": "BINANCE",
    }
    if text in method_map:
        method = method_map[text]
        config = load_system_config()
        if not config["payment_methods"].get(method, False):
            await update.effective_message.reply_text(
                '⚠️ Bu metod hazırda bağlıdır. Başqa bir metod seçin.',
                reply_markup=withdraw_method_keyboard(),
            )
            return
        balance = get_user(uid)["balance"]
        context.user_data["withdraw_method"] = method
        context.user_data["withdraw_mode"] = "amount"
        min_with = config["min_withdraw"]
        max_with = config["max_withdraw"]
        msg = (
            f"<blockquote>💸 SEND YOUR AMOUNT!\n"
            f"💵 TOTAL BALANCE: {format_balance(balance)} AZN</blockquote>\n\n"
            f"<blockquote>📉 MINIMUM WITHDRAW {min_with} AZN</blockquote>\n"
            f"<blockquote>📈 MAXIMUM WITHDRAW {max_with} AZN</blockquote>"
        )
        await update.effective_message.reply_text(
            msg, parse_mode="HTML", reply_markup=cancel_keyboard()
        )
    else:
        await update.effective_message.reply_text(
            "⚠️ PLEASE SELECT A VALID PAYMENT METHOD!",
            reply_markup=withdraw_method_keyboard(),
        )


async def withdraw_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = normalize_button_input(update.message.text.strip())
    uid = update.effective_user.id
    if text == "❌ CANCEL":
        context.user_data["withdraw_mode"] = None
        await update.effective_message.reply_text(
            "❌ WITHDRAW CANCELLED", reply_markup=main_keyboard(uid)
        )
        return
    try:
        amount = float(text)
    except:
        await update.effective_message.reply_text(
            "⚠️ PLEASE SEND A VALID AMOUNT!", reply_markup=cancel_keyboard()
        )
        return
    balance = get_user(uid)["balance"]
    config = load_system_config()
    min_with = config["min_withdraw"]
    max_with = config["max_withdraw"]
    if amount < min_with or amount > max_with:
        await update.effective_message.reply_text(
            f"📉 MIN: {min_with} AZN | MAX: {max_with} AZN",
            reply_markup=cancel_keyboard(),
        )
        return
    if amount > balance:
        await update.effective_message.reply_text(
            "🚫 INSUFFICIENT BALANCE!", reply_markup=cancel_keyboard()
        )
        return
    context.user_data["withdraw_amount"] = amount
    context.user_data["withdraw_mode"] = "number"
    await update.effective_message.reply_text(
        "📞 PLEASE SEND YOUR PAYMENT NUMBER!\n\n<blockquote>🔢 EXAMPLE: 017XXXXXXXX</blockquote>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


async def withdraw_number_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = normalize_button_input(update.message.text.strip())
    uid = update.effective_user.id
    if text == "❌ CANCEL":
        context.user_data["withdraw_mode"] = None
        await update.effective_message.reply_text(
            "❌ WITHDRAW CANCELLED", reply_markup=main_keyboard(uid)
        )
        return
    if not is_valid_bangladesh_number(text):
        await update.effective_message.reply_text(
            "⚠️ PLEASE SEND VALID NUMBER! 017XXXXXXXX", reply_markup=cancel_keyboard()
        )
        return
    method = context.user_data.get("withdraw_method")
    amount = context.user_data.get("withdraw_amount")
    payment_number = text
    payment_id = generate_payment_id()
    context.user_data["temp_withdraw"] = {
        "method": method,
        "amount": amount,
        "number": payment_number,
        "payment_id": payment_id,
    }
    msg = (
        "✨ <b>YOUR PAYMENT DETAILS!</b> ✨\n\n"
        f"<blockquote>📝 METHOD: {method}\n"
        f"📞 NUMBER: {payment_number}\n\n"
        f"✅ CORRECT → CONFIRM\n❌ WRONG → CANCEL</blockquote>"
    )
    await update.effective_message.reply_text(
        msg,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "❌ CANCEL", callback_data="withdraw_cancel", style="danger"
                    ),
                    InlineKeyboardButton(
                        "✅ CONFIRM", callback_data="withdraw_confirm", style="success"
                    ),
                ]
            ]
        ),
    )


async def process_withdraw_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    temp_data = context.user_data.get("temp_withdraw")
    if not temp_data:
        await query.message.reply_text(
            "⚠️ SESSION EXPIRED.", reply_markup=main_keyboard(uid)
        )
        return
    method = temp_data["method"]
    amount = temp_data["amount"]
    payment_number = temp_data["number"]
    payment_id = temp_data["payment_id"]
    new_balance = await update_db_balance(uid, -amount)
    wr = load_withdraw_requests()
    wr[str(payment_id)] = {
        "user_id": uid,
        "method": method,
        "amount": amount,
        "number": payment_number,
        "payment_id": payment_id,
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
    }
    save_withdraw_requests(wr)
    await query.message.edit_text(
        f"✅ <b>WITHDRAWAL REQUEST SUBMITTED</b> ✅\n\n"
        f"<blockquote>📝 METHOD: <code>{method}</code>\n"
        f"📞 NUMBER: <code>{payment_number}</code>\n"
        f"💰 AMOUNT: <code>{format_balance(amount)} AZN</code>\n"
        f"🆔 ID: <code>{payment_id}</code></blockquote>",
        parse_mode="HTML",
    )
    await context.bot.send_message(
        uid,
        "🎉 <b>WITHDRAW REQUEST SUBMITTED!</b>",
        parse_mode="HTML",
        reply_markup=main_keyboard(uid),
    )
    admin_msg = (
        f"✅ <b>NEW WITHDRAWAL REQUEST</b>\n\n"
        f"<blockquote>🆔 USER: <code>{uid}</code>\n"
        f"📝 METHOD: <code>{method}</code>\n"
        f"📞 NUMBER: <code>{payment_number}</code>\n"
        f"💰 AMOUNT: <code>{format_balance(amount)} AZN</code>\n"
        f"🆔 ID: <code>{payment_id}</code></blockquote>"
    )
    admin_kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "❌ REJECT",
                    callback_data=f"admin_reject_{payment_id}",
                    style="danger",
                ),
                InlineKeyboardButton(
                    "✅ APPROVE",
                    callback_data=f"admin_approve_{payment_id}",
                    style="success",
                ),
            ]
        ]
    )

 


    context.user_data["temp_withdraw"] = None
    context.user_data["withdraw_mode"] = None


async def process_withdraw_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    await query.answer()
    context.user_data["temp_withdraw"] = None
    context.user_data["withdraw_mode"] = None
    await query.message.edit_text("❌ WITHDRAW CANCELLED")
    await context.bot.send_message(
        uid, "🔹 PLEASE USE THE BUTTONS BELOW:", reply_markup=main_keyboard(uid)
    )


# ==================== ADMIN PANEL - WITHDRAW APPROVAL ====================
async def admin_approve_withdraw(update, context, payment_id):
    query = update.callback_query
    await query.answer()
    wr = load_withdraw_requests()
    if payment_id not in wr:
        await query.message.reply_text("⚠️ REQUEST NOT FOUND!")
        return
    rd = wr[payment_id]
    uid = rd["user_id"]
    method = rd["method"]
    amount = rd["amount"]
    payment_number = rd["number"]
    wr[payment_id]["status"] = "approved"
    save_withdraw_requests(wr)
    try:
        await context.bot.send_message(
            uid,
            f"🎉 <b>WITHDRAWAL APPROVED!</b>\n\n"
            f"<blockquote>📝 METHOD: <code>{method}</code>\n"
            f"📞 NUMBER: <code>{payment_number}</code>\n"
            f"💰 AMOUNT: <code>{format_balance(amount)} AZN</code></blockquote>",
            parse_mode="HTML",
        )
    except:
        pass
    await query.message.edit_text(
        f"✅ APPROVED | User: {uid} | Amount: {format_balance(amount)} AZN"
    )


async def admin_reject_withdraw(update, context, payment_id):
    query = update.callback_query
    await query.answer()
    wr = load_withdraw_requests()
    if payment_id not in wr:
        await query.message.reply_text("⚠️ REQUEST NOT FOUND!")
        return
    rd = wr[payment_id]
    uid = rd["user_id"]
    amount = rd["amount"]
    wr[payment_id]["status"] = "rejected"
    save_withdraw_requests(wr)
    try:
        await context.bot.send_message(
            uid,
            "❌ **WITHDRAWAL REQUEST REJECTED**\n\nContact admin for more info.",
            parse_mode="Markdown",
        )
    except:
        pass
    await query.message.edit_text(
        f"❌ REJECTED | User: {uid} | Amount: {format_balance(amount)} AZN"
    )


# ==================== ADMIN PANEL - BALANCE MANAGEMENT ====================
async def admin_add_balance_start(update, context):
    context.user_data["add_balance_mode"] = True
    context.user_data["remove_balance_mode"] = False
    await update.effective_message.reply_text("💰 SEND USER ID TO ADD BALANCE:")


async def admin_remove_balance_start(update, context):
    context.user_data["remove_balance_mode"] = True
    context.user_data["add_balance_mode"] = False
    await update.effective_message.reply_text("💸 SEND USER ID TO REMOVE BALANCE:")


async def process_add_balance_user(update, context):
    uid_to_add = normalize_button_input(update.message.text.strip())
    if not uid_to_add.isdigit():
        await update.effective_message.reply_text("❌ INVALID USER ID!")
        return
    uid_to_add_int = int(uid_to_add)
    if not user_exists(uid_to_add_int):
        await update.effective_message.reply_text("❌ USER NOT FOUND!")
        context.user_data["add_balance_mode"] = False
        return
    context.user_data["pending_add_user"] = uid_to_add_int
    await update.effective_message.reply_text("💵 SEND AMOUNT TO ADD:")


async def process_remove_balance_user(update, context):
    uid_to_remove = normalize_button_input(update.message.text.strip())
    if not uid_to_remove.isdigit():
        await update.effective_message.reply_text("❌ INVALID USER ID!")
        return
    uid_to_remove_int = int(uid_to_remove)
    if not user_exists(uid_to_remove_int):
        await update.effective_message.reply_text("❌ USER NOT FOUND!")
        context.user_data["remove_balance_mode"] = False
        return
    context.user_data["pending_remove_user"] = uid_to_remove_int
    await update.effective_message.reply_text("💸 SEND AMOUNT TO REMOVE:")


async def process_add_balance_amount(update, context):
    try:
        amount = float(normalize_button_input(update.message.text.strip()))
        if amount <= 0:
            raise ValueError
    except:
        await update.effective_message.reply_text("❌ INVALID AMOUNT!")
        return
    uid = context.user_data.get("pending_add_user")
    if not uid:
        context.user_data["add_balance_mode"] = False
        await update.effective_message.reply_text("⚠️ SESSION EXPIRED.")
        return
    old_balance = get_user(uid).get("balance", 0)
    new_balance = await update_db_balance(uid, amount)
    await update.effective_message.reply_text(
        f"✅ **ADD BALANCE SUCCESSFUL**\n🆔 USER: `{uid}`\n"
        f"💰 ADDED: `{format_balance(amount)} AZN`\n"
        f"📈 NEW BALANCE: `{format_balance(new_balance)} AZN`",
        parse_mode="Markdown",
    )
    try:
        await context.bot.send_message(
            uid,
            f"🎉 ADMIN ADDED `{format_balance(amount)} AZN` TO YOUR ACCOUNT!\n💵 NEW BALANCE: `{format_balance(new_balance)} AZN`",
            parse_mode="Markdown",
        )
    except:
        pass
    context.user_data["add_balance_mode"] = False
    context.user_data["pending_add_user"] = None


async def process_remove_balance_amount(update, context):
    try:
        amount = float(normalize_button_input(update.message.text.strip()))
        if amount <= 0:
            raise ValueError
    except:
        await update.effective_message.reply_text("❌ INVALID AMOUNT!")
        return
    uid = context.user_data.get("pending_remove_user")
    if not uid:
        context.user_data["remove_balance_mode"] = False
        await update.effective_message.reply_text("⚠️ SESSION EXPIRED.")
        return
    old_balance = get_user(uid).get("balance", 0)
    if amount > old_balance:
        await update.effective_message.reply_text(
            f"❌ INSUFFICIENT BALANCE! Current: {format_balance(old_balance)} AZN"
        )
        context.user_data["remove_balance_mode"] = False
        context.user_data["pending_remove_user"] = None
        return
    new_balance = await update_db_balance(uid, -amount)
    await update.effective_message.reply_text(
        f"✅ **REMOVE BALANCE SUCCESSFUL**\n🆔 USER: `{uid}`\n"
        f"💸 REMOVED: `{format_balance(amount)} AZN`\n"
        f"📉 NEW BALANCE: `{format_balance(new_balance)} AZN`",
        parse_mode="Markdown",
    )
    try:
        await context.bot.send_message(
            uid,
            f"⚠️ ADMIN REMOVED `{format_balance(amount)} AZN` FROM YOUR ACCOUNT!\n💵 NEW BALANCE: `{format_balance(new_balance)} AZN`",
            parse_mode="Markdown",
        )
    except:
        pass
    context.user_data["remove_balance_mode"] = False
    context.user_data["pending_remove_user"] = None


# ==================== ADMIN PANEL - BAN/UNBAN ====================
async def admin_ban_user_start(update, context):
    context.user_data["admin_ban_mode"] = True
    context.user_data["admin_unban_mode"] = False
    await update.effective_message.reply_text("🚫 SEND TELEGRAM ID TO BAN USER:")


async def admin_unban_user_start(update, context):
    context.user_data["admin_unban_mode"] = True
    context.user_data["admin_ban_mode"] = False
    await update.effective_message.reply_text("🔓 SEND TELEGRAM ID TO UNBAN USER:")


async def process_ban_user(update, context):
    uid_to_ban = normalize_button_input(update.message.text.strip())
    if not uid_to_ban.isdigit():
        await update.effective_message.reply_text("❌ INVALID USER ID!")
        return
    uid_to_ban_int = int(uid_to_ban)
    if not user_exists(uid_to_ban_int):
        await update.effective_message.reply_text("❌ USER NOT FOUND!")
        context.user_data["admin_ban_mode"] = False
        return
    if is_user_banned(uid_to_ban_int):
        await update.effective_message.reply_text("⚠️ USER IS ALREADY BANNED!")
        context.user_data["admin_ban_mode"] = False
        return
    ban_user(uid_to_ban_int)
    try:
        await context.bot.send_message(
            uid_to_ban_int,
            "🚫 **YOU HAVE BEEN BANNED**\n📞 Contact support.",
            parse_mode="Markdown",
        )
    except:
        pass
    await update.effective_message.reply_text(
        f"✅ USER `{uid_to_ban}` BANNED!",
        parse_mode="Markdown",
        reply_markup=system_config_keyboard(),
    )
    context.user_data["admin_ban_mode"] = False


async def process_unban_user(update, context):
    uid_to_unban = normalize_button_input(update.message.text.strip())
    if not uid_to_unban.isdigit():
        await update.effective_message.reply_text("❌ INVALID USER ID!")
        return
    uid_to_unban_int = int(uid_to_unban)
    if not is_user_banned(uid_to_unban_int):
        await update.effective_message.reply_text("⚠️ THIS USER IS NOT BANNED!")
        context.user_data["admin_unban_mode"] = False
        return
    unban_user(uid_to_unban_int)
    try:
        await context.bot.send_message(
            uid_to_unban_int,
            "✅ **YOU HAVE BEEN UNBANNED!** Use /start",
            parse_mode="Markdown",
        )
    except:
        pass
    await update.effective_message.reply_text(
        f"✅ USER `{uid_to_unban}` UNBANNED!",
        parse_mode="Markdown",
        reply_markup=system_config_keyboard(),
    )
    context.user_data["admin_unban_mode"] = False


async def show_banned_users_list(update, context):
    banned_list = load_banned_users()
    if not banned_list:
        await update.effective_message.reply_text(
            "📜 NO BANNED USERS.", reply_markup=system_config_keyboard()
        )
        return
    text = "📜 **BANNED USER LIST**\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, uid in enumerate(banned_list, 1):
        text += f"{i}. `{uid}`\n"
    text += f"\n📊 Total: {len(banned_list)}"
    await update.effective_message.reply_text(
        text, parse_mode="Markdown", reply_markup=system_config_keyboard()
    )


# ==================== ADMIN PANEL - SYSTEM CONFIG ====================
async def admin_change_min_withdraw_start(update, context):
    context.user_data["admin_min_withdraw_mode"] = True
    await update.effective_message.reply_text(
        '💵 YENİ MİNİMUM ÇIXARIŞ MƏBLƏĞİNİ GÖNDƏRİN (yalnız rəqəm):\n\nCari dəyər: '
        + str(load_system_config()["min_withdraw"]),
        reply_markup=cancel_keyboard(),
    )


async def admin_change_min_withdraw_amount(update, context):
    if not context.user_data.get("admin_min_withdraw_mode"):
        return
    try:
        new_min = float(normalize_button_input(update.message.text.strip()))
        if new_min < 0:
            raise ValueError
        update_min_withdraw(new_min)
        await update.effective_message.reply_text(
            f"✅ Minimum çıxarış məbləği {new_min} AZN olaraq dəyişdirildi.",
            reply_markup=system_config_keyboard(),
        )
    except:
        await update.effective_message.reply_text(
            '❌ Etibarlı məbləğ daxil edin.', reply_markup=system_config_keyboard()
        )
    finally:
        context.user_data["admin_min_withdraw_mode"] = False


async def admin_change_otp_rate_start(update, context):
    context.user_data["admin_otp_rate_mode"] = True
    current_rate = get_otp_rate()
    await update.effective_message.reply_text(
        f"💲 Cari OTP tarifi: `{current_rate:.2f} AZN`\n\nYeni tarifi göndərin (yalnız rəqəm, məsələn: `0.25`):\n\n<blockquote>Diqqət: bu tarif bütün yeni OTP-lərə tətbiq ediləcək.</blockquote>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


async def admin_change_otp_rate_amount(update, context):
    if not context.user_data.get("admin_otp_rate_mode"):
        return
    try:
        new_rate = float(normalize_button_input(update.message.text.strip()))
        if new_rate <= 0:
            raise ValueError
        update_otp_rate(new_rate)
        await update.effective_message.reply_text(
            f"✅ OTP tarifi `{new_rate:.2f} AZN` olaraq dəyişdirildi.\n\nYeni OTP-lər bu tariflə hesablanacaq.",
            parse_mode="HTML",
            reply_markup=system_config_keyboard(),
        )
    except:
        await update.effective_message.reply_text(
            '❌ Etibarlı dərəcə daxil edin (məsələn: 0.25).', reply_markup=system_config_keyboard()
        )
    finally:
        context.user_data["admin_otp_rate_mode"] = False


# ==================== ADMIN PANEL - PER-USER OTP RATE ====================
async def admin_set_user_otp_rate_start(update, context):
    context.user_data["admin_set_otp_rate_mode"] = "user"
    await update.effective_message.reply_text(
        '🔧 **İSTİFADƏÇİ OTP DƏRƏCƏSİNİ TƏYİN ET**\n\nZəhmət olmasa istifadəçi ID-sini daxil edin (yalnız rəqəm):',
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def admin_set_user_otp_rate_user(update, context):
    uid_str = normalize_button_input(update.message.text.strip())
    if uid_str == "❌ CANCEL":
        context.user_data["admin_set_otp_rate_mode"] = None
        await update.effective_message.reply_text(
            '❌ Əməliyyat ləğv edildi.', reply_markup=system_config_keyboard()
        )
        return
    if not uid_str.isdigit():
        await update.effective_message.reply_text(
            '❌ Etibarlı istifadəçi ID-si daxil edin (yalnız rəqəm)!', reply_markup=cancel_keyboard()
        )
        return
    uid_int = int(uid_str)
    if not user_exists(uid_int):
        await update.effective_message.reply_text(
            '❌ Bu istifadəçi qeydiyyatdan keçməyib. Yenidən cəhd edin.', reply_markup=cancel_keyboard()
        )
        return
    context.user_data["admin_set_otp_rate_user"] = uid_int
    context.user_data["admin_set_otp_rate_mode"] = "rate"
    current_rate = get_user_otp_rate(uid_int)
    global_rate = get_otp_rate()
    await update.effective_message.reply_text(
        f"İstifadəçinin cari tarifi: `{current_rate:.2f} AZN`\n"
        f"Ümumi tarif: `{global_rate:.2f} AZN`\n\n"
        'Yeni tarifi daxil edin (yalnız rəqəm, məsələn: 0.25):\n'
        'Tarifi 0 etsəniz, fərdi tarif silinəcək və ümumi tarif istifadə olunacaq.',
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def admin_set_user_otp_rate_amount(update, context):
    if context.user_data.get("admin_set_otp_rate_mode") != "rate":
        return
    uid = context.user_data.get("admin_set_otp_rate_user")
    if not uid:
        context.user_data["admin_set_otp_rate_mode"] = None
        await update.effective_message.reply_text(
            '⚠️ Sessiya bitdi. Yenidən cəhd edin.', reply_markup=system_config_keyboard()
        )
        return
    text = normalize_button_input(update.message.text.strip())
    if text == "❌ CANCEL":
        context.user_data["admin_set_otp_rate_mode"] = None
        context.user_data["admin_set_otp_rate_user"] = None
        await update.effective_message.reply_text(
            '❌ Əməliyyat ləğv edildi.', reply_markup=system_config_keyboard()
        )
        return
    try:
        rate = float(text)
        if rate < 0:
            raise ValueError
    except:
        await update.effective_message.reply_text(
            '❌ Etibarlı dərəcə daxil edin (məsələn: 0.25)!', reply_markup=cancel_keyboard()
        )
        return
    set_user_otp_rate(uid, rate)
    if rate > 0:
        await update.effective_message.reply_text(
            f"✅ İstifadəçi `{uid}` üçün OTP tarifi `{rate:.2f} AZN` olaraq təyin edildi.",
            parse_mode="Markdown",
            reply_markup=system_config_keyboard(),
        )
    else:
        await update.effective_message.reply_text(
            f"✅ İstifadəçi `{uid}` üçün fərdi OTP tarifi silindi. İndi ümumi tarif — `{get_otp_rate():.2f} AZN` tətbiq ediləcək.",
            parse_mode="Markdown",
            reply_markup=system_config_keyboard(),
        )
    context.user_data["admin_set_otp_rate_mode"] = None
    context.user_data["admin_set_otp_rate_user"] = None


async def admin_view_user_otp_rate_start(update, context):
    context.user_data["admin_view_otp_rate_mode"] = True
    await update.effective_message.reply_text(
        '📋 **İSTİFADƏÇİ OTP DƏRƏCƏSİNƏ BAX**\n\nZəhmət olmasa istifadəçi ID-sini daxil edin (yalnız rəqəm):',
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def admin_view_user_otp_rate(update, context):
    if not context.user_data.get("admin_view_otp_rate_mode"):
        return
    uid_str = normalize_button_input(update.message.text.strip())
    if uid_str == "❌ CANCEL":
        context.user_data["admin_view_otp_rate_mode"] = None
        await update.effective_message.reply_text(
            '❌ Əməliyyat ləğv edildi.', reply_markup=system_config_keyboard()
        )
        return
    if not uid_str.isdigit():
        await update.effective_message.reply_text(
            '❌ Etibarlı istifadəçi ID-si daxil edin (yalnız rəqəm)!', reply_markup=cancel_keyboard()
        )
        return
    uid_int = int(uid_str)
    if not user_exists(uid_int):
        await update.effective_message.reply_text(
            '❌ Bu istifadəçi qeydiyyatdan keçməyib.', reply_markup=system_config_keyboard()
        )
        context.user_data["admin_view_otp_rate_mode"] = None
        return
    custom_rate = get_user_otp_rate(uid_int)
    global_rate = get_otp_rate()
    rates = load_user_otp_rates()
    has_custom = str(uid_int) in rates and rates[str(uid_int)] > 0
    msg = (
        f"📊 **USER OTP RATE INFO**\n"
        f"🆔 İstifadəçi: `{uid_int}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 Fərdi tarif: `{custom_rate:.2f} AZN`\n"
        f"🌐 Ümumi tarif: `{global_rate:.2f} AZN`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔹 {'Bu istifadəçi üçün xüsusi dərəcə aktivdir.' if has_custom else 'Bu istifadəçi üçün xüsusi dərəcə yoxdur, qlobal dərəcə istifadə olunacaq.'}"
    )
    await update.effective_message.reply_text(
        msg, parse_mode="Markdown", reply_markup=system_config_keyboard()
    )
    context.user_data["admin_view_otp_rate_mode"] = None


# ==================== ADMIN PANEL - SHOW ALL USERS ====================
async def admin_show_all_users(update, context):
    uid = update.effective_user.id
    if not is_admin(uid):
        return

    user_db = load_data(USER_DATA_FILE)
    total_users = len(user_db)
    if total_users == 0:
        await update.effective_message.reply_text(
            "👥 Ümumi istifadəçi: 0\nHələ /start verən istifadəçi yoxdur.",
            reply_markup=user_management_keyboard(),
        )
        return

    def sort_key(item):
        user_id, info = item
        return info.get("joined_at", "") or ""

    users = sorted(user_db.items(), key=sort_key, reverse=True)
    lines = []
    for i, (user_id, info) in enumerate(users, 1):
        first = str(info.get("first_name", "") or "").strip()
        last = str(info.get("last_name", "") or "").strip()
        full_name = (first + " " + last).strip() or "Adsız istifadəçi"
        username = str(info.get("username", "") or "").strip()
        joined = str(info.get("joined_at", "") or "Məlum deyil")
        uname_text = f"@{username}" if username else "username yoxdur"
        lines.append(
            f"{i}. {full_name} | {uname_text} | ID: {user_id} | Qoşulub: {joined}"
        )

    if total_users <= 30:
        text_lines = []
        for i, (user_id, info) in enumerate(users, 1):
            first = str(info.get("first_name", "") or "").strip()
            last = str(info.get("last_name", "") or "").strip()
            full_name = html.escape((first + " " + last).strip() or "Adsız istifadəçi")
            username = str(info.get("username", "") or "").strip()
            joined = html.escape(str(info.get("joined_at", "") or "Məlum deyil"))
            uname_text = f"@{html.escape(username)}" if username else "username yoxdur"
            text_lines.append(
                f"{i}. 👤 <b>{full_name}</b>\n"
                f"   🔗 {uname_text}\n"
                f"   🆔 <code>{user_id}</code>\n"
                f"   📅 {joined}"
            )
        msg = f"👥 <b>START VERƏN İSTİFADƏÇİLƏR</b>\n📊 Ümumi: <b>{total_users}</b>\n\n" + "\n\n".join(text_lines)
        await update.effective_message.reply_text(
            msg, parse_mode="HTML", reply_markup=user_management_keyboard()
        )
    else:
        content = f"Aze Sms Panel - /start istifadəçiləri\nÜmumi: {total_users}\n\n" + "\n".join(lines)
        f = io.BytesIO(content.encode("utf-8"))
        f.name = f"START_USERS_{total_users}.txt"
        await update.message.reply_document(
            document=f,
            caption=f"👥 /start verən istifadəçilər: {total_users}",
            reply_markup=user_management_keyboard(),
        )


# ==================== ADMIN PANEL - TOGGLE PAYMENT METHODS ====================
async def admin_toggle_payment_methods(update, context):
    config = load_system_config()
    methods = config["payment_methods"]
    buttons = []
    for method, enabled in methods.items():
        status = "✅" if enabled else "❌"
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{status} {method}", callback_data=f"toggle_method_{method}"
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton("🔙 BACK", callback_data="back_to_admin_panel")]
    )
    await update.effective_message.reply_text(
        '💳 Ödəniş üsulunu dəyişin:\n\nYaşıl işarə aktiv, qırmızı isə deaktiv deməkdir.\nDəyişmək üçün klikləyin.',
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_toggle_method_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("toggle_method_"):
        method = data.replace("toggle_method_", "")
        new_state = toggle_payment_method(method)
        status = 'aktiv ✅' if new_state else 'deaktiv ❌'
        await query.edit_message_text(
            f"✅ {method} üsulunun hazırkı vəziyyəti: {status}।", reply_markup=query.message.reply_markup
        )
        config = load_system_config()
        methods = config["payment_methods"]
        buttons = []
        for m, enabled in methods.items():
            st = "✅" if enabled else "❌"
            buttons.append(
                [InlineKeyboardButton(f"{st} {m}", callback_data=f"toggle_method_{m}")]
            )
        buttons.append(
            [InlineKeyboardButton("🔙 BACK", callback_data="back_to_admin_panel")]
        )
        await query.message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif data == "back_to_admin_panel":
        await query.message.delete()
        await query.message.chat.send_message(
            "⚙️ System Configuration:", reply_markup=system_config_keyboard()
        )


# ==================== ADMIN PANEL - REQUIRED CHANNELS ====================
async def admin_add_channel_start(update, context):
    context.user_data["add_channel_mode"] = True
    await update.effective_message.reply_text(
        "➕ **ADD CHANNEL/GROUP**\n\n"
        'Format: `link|ad` (ad məcburi deyil)\n'
        'Nümunə: `https://t.me/betrunaz|📢 Kanalımız`\n'
        'Ad daxil etməsəniz, linkdən avtomatik yaradılacaq.\n\n'
        'Özəl link üçün: `link|çat_id|ad`',
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def admin_process_add_channel(update, context):
    if not context.user_data.get("add_channel_mode"):
        return
    text = normalize_button_input(update.message.text.strip())
    if text == "❌ CANCEL":
        context.user_data["add_channel_mode"] = None
        await update.effective_message.reply_text(
            '❌ Ləğv edildi.', reply_markup=required_channels_keyboard()
        )
        return
    parts = text.split("|")
    link = parts[0].strip()
    label = None
    chat_id = None
    if len(parts) > 1:
        if parts[1].strip().isdigit():
            chat_id = int(parts[1].strip())
            if len(parts) > 2:
                label = parts[2].strip()
        else:
            label = parts[1].strip()
    if len(parts) > 2 and not chat_id:
        label = parts[1].strip()
        if parts[2].strip().isdigit():
            chat_id = int(parts[2].strip())
    success, msg = add_required_channel(link, label, chat_id)
    if success:
        await update.effective_message.reply_text(
            f"✅ {msg}", reply_markup=required_channels_keyboard()
        )
    else:
        await update.effective_message.reply_text(f"❌ {msg}", reply_markup=cancel_keyboard())
    context.user_data["add_channel_mode"] = None


async def admin_remove_channel_start(update, context):
    context.user_data["remove_channel_mode"] = True
    await update.effective_message.reply_text(
        '❌ **KANAL/QRUPU SİL**\n\nZəhmət olmasa silmək istədiyiniz link və ya etiketi daxil edin:',
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def admin_process_remove_channel(update, context):
    if not context.user_data.get("remove_channel_mode"):
        return
    text = normalize_button_input(update.message.text.strip())
    if text == "❌ CANCEL":
        context.user_data["remove_channel_mode"] = None
        await update.effective_message.reply_text(
            '❌ Ləğv edildi.', reply_markup=required_channels_keyboard()
        )
        return
    success, msg = remove_required_channel(text)
    if success:
        await update.effective_message.reply_text(
            f"✅ {msg}", reply_markup=required_channels_keyboard()
        )
    else:
        await update.effective_message.reply_text(f"❌ {msg}", reply_markup=cancel_keyboard())
    context.user_data["remove_channel_mode"] = None


async def admin_list_channels(update, context):
    channels = get_all_required_channels()
    if not channels:
        await update.effective_message.reply_text(
            '📋 Heç bir kanal/qrup əlavə edilməyib.', reply_markup=required_channels_keyboard()
        )
        return
    text = '📋 **Mövcud kanal/qrup siyahısı:**\n\n'
    for i, ch in enumerate(channels, 1):
        link = ch.get("link", "N/A")
        label = ch.get("label", "N/A")
        style = ch.get("style", "primary")
        cid = ch.get("chat_id", "N/A")
        text += f"{i}. Ad: `{label}`\n   Link: `{link}`\n   Üslub: `{style}`\n   chat_id: `{cid}`\n\n"
    await update.effective_message.reply_text(
        text, parse_mode="Markdown", reply_markup=required_channels_keyboard()
    )


# ==================== ADMIN PANEL - FAKE OTP ====================
async def admin_fake_otp_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_fake_otp_config()
    status = "✅ AKTİV" if config.get("running", False) else "❌ DEAKTİV"
    await update.effective_message.reply_text(
        "🧪 **TEST OTP SİSTEMİ** 🧪\n\n"
        "Bu rejim yalnız demo və botun test edilməsi üçündür. Real nömrə, real SMS və real autentifikasiya məlumatı istifadə etmir.\n\n"
        f"📊 Status: {status}\n"
        f"📈 Göndərilən test sayı: `{config.get('sent_count', 0)}`",
        parse_mode="Markdown", reply_markup=fake_otp_keyboard())

async def admin_fake_otp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_fake_otp_config()
    if config.get("running", False):
        await update.effective_message.reply_text("⚠️ Test OTP sistemi artıq aktivdir.", reply_markup=fake_otp_keyboard())
        return
    config["running"] = True
    save_fake_otp_config(config)
    await update.effective_message.reply_text("✅ Test OTP sistemi aktiv edildi. Sintetik test mesajları qrupa göndəriləcək.", reply_markup=fake_otp_keyboard())

async def admin_fake_otp_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_fake_otp_config()
    config["running"] = False
    save_fake_otp_config(config)
    await update.effective_message.reply_text("⏹ Test OTP sistemi dayandırıldı.", reply_markup=fake_otp_keyboard())

async def admin_fake_otp_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_fake_otp_config()
    await update.effective_message.reply_text(
        f"📈 **TEST STATİSTİKASI**\n\nGöndərilən sintetik test mesajları: `{config.get('sent_count', 0)}`\n"
        f"Status: {'✅ AKTİV' if config.get('running', False) else '❌ DEAKTİV'}",
        parse_mode="Markdown", reply_markup=fake_otp_keyboard())

async def admin_fake_otp_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = load_fake_otp_config()
    msg = (
        "⚙️ **TEST OTP PARAMETRLƏRİ**\n\n"
        f"🏷️ Test etiketi: `{config.get('service', 'DEMO')}`\n"
        f"⏱ Interval: `{config.get('interval', 10)} saniyə`\n"
        f"🔢 Kod uzunluğu: `{config.get('otp_digits', 6)}`\n\n"
        "Test mesajları həmişə DEMO kimi işarələnir və real nömrələrdən istifadə etmir."
    )
    keyboard = [[KeyboardButton("📱 SET SERVICE")], [KeyboardButton("⏱ SET INTERVAL")],
                [KeyboardButton("🔢 SET OTP DIGITS")], [KeyboardButton("🔙 BACK TO FAKE OTP")]]
    await update.effective_message.reply_text(msg, parse_mode="Markdown", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    context.user_data["fake_otp_settings_mode"] = True

async def admin_fake_otp_set_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("🏷️ Demo etiketi yazın (məsələn: TEST-SERVICE):", reply_markup=cancel_keyboard())
    context.user_data["fake_otp_setting"] = "service"

async def admin_fake_otp_set_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("ℹ️ Demo rejimində real nömrə/range istifadə edilmir.", reply_markup=fake_otp_keyboard())

async def admin_fake_otp_set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("⏱ Intervalı saniyə ilə yazın (minimum 10):", reply_markup=cancel_keyboard())
    context.user_data["fake_otp_setting"] = "interval"

async def admin_fake_otp_set_otp_digits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("🔢 Test kodunun uzunluğunu yazın (4-8):", reply_markup=cancel_keyboard())
    context.user_data["fake_otp_setting"] = "otp_digits"

async def admin_fake_otp_process_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    setting = context.user_data.get("fake_otp_setting")
    if not setting:
        return
    text = normalize_button_input(update.message.text.strip())
    if text == "❌ CANCEL":
        context.user_data["fake_otp_setting"] = None
        context.user_data["fake_otp_settings_mode"] = False
        await update.effective_message.reply_text("❌ Ləğv edildi.", reply_markup=fake_otp_keyboard())
        return
    config = load_fake_otp_config()
    try:
        if setting == "service":
            config["service"] = (text[:32] or "DEMO")
        elif setting == "interval":
            val = int(text)
            if val < 10: raise ValueError
            config["interval"] = val
        elif setting == "otp_digits":
            val = int(text)
            if not 4 <= val <= 8: raise ValueError
            config["otp_digits"] = val
        save_fake_otp_config(config)
    except ValueError:
        await update.effective_message.reply_text("❌ Dəyər düzgün deyil. Interval minimum 10 saniyə, kod uzunluğu 4-8 olmalıdır.", reply_markup=cancel_keyboard())
        return
    context.user_data["fake_otp_setting"] = None
    context.user_data["fake_otp_settings_mode"] = False
    await update.effective_message.reply_text("✅ Parametr yadda saxlanıldı.", reply_markup=fake_otp_keyboard())


# ==================== SHOW MAIN MENU HELPER ====================
async def show_main_menu(update, context, uid):
    await context.bot.send_message(
        chat_id=uid,
        text="🔹 PLEASE USE THE BUTTONS BELOW:",
        reply_markup=main_keyboard(uid),
    )


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open the existing announcement flow for an administrator in private chat."""
    if not update.effective_user or not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔ Bu komanda yalnız admin üçündür.")
        return
    if update.effective_chat.type != "private":
        await update.effective_message.reply_text("Bu komandanı botun şəxsi çatında yazın.")
        return
    if context.application.bot_data.get("broadcast_running"):
        await update.effective_message.reply_text("⏳ Əvvəlki bildiriş hələ göndərilir.")
        return
    context.user_data["broadcast_mode"] = True
    await update.effective_message.reply_text(
        "📢 Bütün qeydiyyatlı istifadəçilərə göndəriləcək məlumat mətnini yazın.",
        reply_markup=cancel_keyboard(),
    )


# ==================== MESSAGE HANDLER ====================
async def deliver_admin_notice(context, targets, notice, status_msg):
    """Deliver outside the webhook request; release the active-job guard on failure."""
    try:
        from safe_broadcast import send_notice
        result = await send_notice(context.bot, targets, notice)
        await status_msg.edit_text(
            "✅ <b>Bildiriş göndərişi tamamlandı</b>\n\n"
            f"👥 Qeydiyyatda: <b>{result['targeted']}</b>\n"
            f"✅ Çatdırılan: <b>{result['sent']}</b>\n"
            f"❌ Çatdırılmayan: <b>{result['failed']}</b>\n"
            f"🚫 Botu bloklayanlar: <b>{result['blocked']}</b>\n"
            f"⏳ Limitə görə uğursuz: <b>{result['retry_exhausted']}</b>\n\n"
            "Qeyd: Bot yalnız onu başladan və bloklamayan istifadəçilərə "
            "mesaj göndərə bilər.",
            parse_mode="HTML",
        )
    finally:
        context.application.bot_data.pop("broadcast_running", None)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    uid = update.effective_user.id
    text = normalize_button_input(update.message.text.strip())

    # Admin-only ordinary information notices to users who started this bot.
    if text in ("📢 SEND MESSAGE TO ALL USERS", "📢 BÜTÜN İSTİFADƏÇİLƏRƏ MESAJ GÖNDƏR") and is_admin(uid):
        if context.application.bot_data.get("broadcast_running"):
            await update.effective_message.reply_text("⏳ Əvvəlki bildiriş hələ göndərilir.")
            return
        context.user_data["broadcast_mode"] = True
        await update.effective_message.reply_text(
            "📢 <b>BÜTÜN İSTİFADƏÇİLƏRƏ BİLDİRİŞ</b>\n\n"
            "Botu əvvəllər başladan istifadəçilərə göndərmək istədiyin "
            "məlumat mesajını yaz.\n\n"
            "Yalnız adi məlumat mətni göndərilir. OTP/SMS kodu və parol göndərmə.\n"
            "Ləğv etmək üçün ❌ CANCEL seç.",
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
        return

    if context.user_data.get("broadcast_mode") and is_admin(uid):
        if text == "❌ CANCEL":
            context.user_data.pop("broadcast_mode", None)
            await update.effective_message.reply_text("❌ Ləğv edildi", reply_markup=admin_main_keyboard())
            return
        if context.application.bot_data.get("broadcast_running"):
            await update.effective_message.reply_text("⏳ Əvvəlki bildiriş hələ göndərilir.")
            return
        context.user_data["broadcast_mode"] = False
        from safe_broadcast import validate_notice, recipient_ids
        try:
            notice = validate_notice(update.message.text or "")
        except ValueError as exc:
            await update.effective_message.reply_text(
                f"❌ {html.escape(str(exc))}", reply_markup=admin_main_keyboard()
            )
            return
        targets = recipient_ids(load_data(USER_DATA_FILE))
        if not targets:
            await update.effective_message.reply_text(
                "❌ Hazırda bildiriş göndərmək üçün qeydiyyatda istifadəçi yoxdur.",
                reply_markup=admin_main_keyboard(),
            )
            return
        context.application.bot_data["broadcast_running"] = True
        try:
            status_msg = await update.effective_message.reply_text(
                f"📢 <b>Bildiriş göndərilir...</b>\n👥 İstifadəçi sayı: {len(targets)}",
                parse_mode="HTML",
                reply_markup=admin_main_keyboard(),
            )
            context.application.create_task(
                deliver_admin_notice(context, targets, notice, status_msg), update=update
            )
        except Exception:
            context.application.bot_data.pop("broadcast_running", None)
            raise
        return

    # Fake OTP settings processing
    if context.user_data.get("fake_otp_setting") and is_admin(uid):
        await admin_fake_otp_process_setting(update, context)
        return

    # Withdraw flow
    if context.user_data.get("withdraw_mode") == "select_method":
        await withdraw_method_selected(update, context)
        return
    if context.user_data.get("withdraw_mode") == "amount":
        await withdraw_amount_received(update, context)
        return
    if context.user_data.get("withdraw_mode") == "number":
        await withdraw_number_received(update, context)
        return

    # Admin balance
    if context.user_data.get("add_balance_mode") and is_admin(uid):
        if context.user_data.get("pending_add_user"):
            await process_add_balance_amount(update, context)
        else:
            await process_add_balance_user(update, context)
        return
    if context.user_data.get("remove_balance_mode") and is_admin(uid):
        if context.user_data.get("pending_remove_user"):
            await process_remove_balance_amount(update, context)
        else:
            await process_remove_balance_user(update, context)
        return

    # Admin ban/unban
    if context.user_data.get("admin_ban_mode") and is_admin(uid):
        await process_ban_user(update, context)
        return
    if context.user_data.get("admin_unban_mode") and is_admin(uid):
        await process_unban_user(update, context)
        return

    # Admin change min withdraw
    if context.user_data.get("admin_min_withdraw_mode") and is_admin(uid):
        await admin_change_min_withdraw_amount(update, context)
        return

    # Admin change OTP rate
    if context.user_data.get("admin_otp_rate_mode") and is_admin(uid):
        await admin_change_otp_rate_amount(update, context)
        return

    # Admin set user OTP rate
    if context.user_data.get("admin_set_otp_rate_mode") == "user" and is_admin(uid):
        await admin_set_user_otp_rate_user(update, context)
        return
    if context.user_data.get("admin_set_otp_rate_mode") == "rate" and is_admin(uid):
        await admin_set_user_otp_rate_amount(update, context)
        return

    # Admin view user OTP rate
    if context.user_data.get("admin_view_otp_rate_mode") and is_admin(uid):
        await admin_view_user_otp_rate(update, context)
        return

    # Admin add/remove channel
    if context.user_data.get("add_channel_mode") and is_admin(uid):
        await admin_process_add_channel(update, context)
        return
    if context.user_data.get("remove_channel_mode") and is_admin(uid):
        await admin_process_remove_channel(update, context)
        return

    # Fake OTP settings menu navigation (admin)
    if context.user_data.get("fake_otp_settings_mode") and is_admin(uid):
        if text == "📱 SET SERVICE":
            await admin_fake_otp_set_service(update, context)
            return
        elif text == "📶 SET RANGE":
            await admin_fake_otp_set_range(update, context)
            return
        elif text == "⏱ SET INTERVAL":
            await admin_fake_otp_set_interval(update, context)
            return
        elif text == "🔢 SET OTP DIGITS":
            await admin_fake_otp_set_otp_digits(update, context)
            return
        elif text == "🔙 BACK TO FAKE OTP":
            context.user_data["fake_otp_settings_mode"] = False
            await admin_fake_otp_menu(update, context)
            return

    # Collect number-only TXT results for one custom range.
    if context.user_data.get("mode") == "custom_range_collect":
        context.user_data["mode"] = None
        if is_user_banned(uid):
            await update.effective_message.reply_text("🚫 Giriş məhdudlaşdırılıb.")
            return
        for channel in load_required_channels():
            joined, _ = await check_user_joined(context.bot, uid, channel)
            if not joined:
                await update.effective_message.reply_text(
                    t(get_user_language(uid), "membership_required"),
                    parse_mode="HTML",
                    reply_markup=membership_keyboard(load_required_channels(), get_user_language(uid)),
                )
                return
        if is_az_range(text) and not az_range_allowed(uid):
            await update.effective_message.reply_text(AZ_ACCESS_DENIED)
            return
        await range_collector.start(
            update, context, text,
            lambda rid: get_number_from_api(rid, requester_id=uid),
            number_archive,
        )
        return

    # CUSTOM RANGE
    if context.user_data.get("mode") == "custom_range":
        context.user_data["mode"] = None
        range_text = text.strip().upper()
        if is_az_range(range_text) and not az_range_allowed(uid):
            await update.effective_message.reply_text(AZ_ACCESS_DENIED)
            return
        if not re.search(r"\d", range_text):
            await update.effective_message.reply_text(
                "❌ <b>INVALID RANGE!</b>\n\n"
                '<blockquote>Düzgün nümunə: <code>234XXX</code> və ya <code>26134</code></blockquote>',
                parse_mode="HTML",
                reply_markup=main_keyboard(uid),
            )
            return
        await request_queue.put(
            {
                "type": "process_numbers",
                "update": update,
                "context": context,
                "range_text": range_text,
                "count": 1,
                "service": "CUSTOM",
            }
        )
        return

    # Ban check
    if not is_admin(uid) and is_user_banned(uid):
        await update.effective_message.reply_text(
            "🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid)
        )
        return

    # Cancel
    if text == "❌ CANCEL":
        context.user_data.clear()
        await update.effective_message.reply_text("❌ CANCELLED", reply_markup=main_keyboard(uid))
        return

    # Main menu buttons
    if text == "👤 PROFILE":
        user_data = get_user(uid)
        stats = get_user_stats(uid)
        user = update.effective_user
        full_name = html.escape(user.full_name)
        username = html.escape(user.username or "No username")
        profile_text = (
            f"👤 <b>YOUR PROFILE</b>\n\n"
            f"<blockquote>🏷️ NAME: <b>{full_name}</b></blockquote>\n"
            f"<blockquote>🆔 USERNAME: @{username}</blockquote>\n"
            f"<blockquote>🗝️ TELEGRAM ID: <code>{uid}</code></blockquote>\n\n"
            f"<blockquote>💵 BALANCE: <b>{format_balance(user_data.get('balance', 0))} AZN</b></blockquote>\n\n"
            f"✨ <b>TODAY</b>\n"
            f"<blockquote>📱 NUMBERS: {stats['today_numbers']}\n🔑 OTPS: {stats['today_otps']}</blockquote>\n\n"
            f"🔥 <b>LAST 7 DAYS</b>\n"
            f"<blockquote>📱 NUMBERS: {stats['last7d_numbers']}\n🔑 OTPS: {stats['last7d_otps']}</blockquote>\n\n"
            f"🌐 <b>ALL TIME</b>\n"
            f"<blockquote>📱 NUMBERS: {stats['total_numbers']}\n🔑 OTPS: {stats['total_otps']}</blockquote>"
        )
        await update.effective_message.reply_text(profile_text, parse_mode="HTML")
        return

    if text == "💰 BALANCE":
        balance = get_user(uid)["balance"]
        await update.effective_message.reply_text(
            f"💰 <b>YOUR CURRENT BALANCE</b>\n\n"
            f"<blockquote>💵 TOTAL: <b>{format_balance(balance)} AZN</b></blockquote>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "💸 WITHDRAW",
                            callback_data="withdraw_start",
                            style="primary",
                        )
                    ]
                ]
            ),
        )
        return

    if text == "🔍 SEARCH OTP":
        context.user_data["mode"] = "search_otp"
        await update.effective_message.reply_text(
            "🔍 **ENTER THE NUMBER TO SEARCH OTP:**", parse_mode="Markdown"
        )
        return

    if context.user_data.get("mode") == "search_otp":
        context.user_data["mode"] = None
        await request_queue.put(
            {
                "type": "search_otp",
                "update": update,
                "context": context,
                "target_num": normalize_number(text),
            }
        )
        return

    if text == "⚡ GET 2FA":
        await get_2fa_code(update, context)
        return

    if text == "📋 ACTIVE NUMBERS":
        await show_active_numbers(update, context)
        return

    if text == "📞 GET NUMBER":
        await show_app_selection(update, context)
        return

    if context.user_data.get("mode") == "get_2fa":
        await process_2fa_key(update, context)
        return

    if text == "🏆 LEADERBOARD":
        await leaderboard_command(update, context)
        return

    if text == "💬 SUPPORT":
        support_text = "💬 SUPPORT 🎧\n\nCLICK THE BUTTON BELOW TO CONTACT SUPPORT 📩"
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("💬 SUPPORT", url=SUPPORT_LINK, style="primary")],
                [
                    InlineKeyboardButton(
                        "👨‍💻 DEVELOPER BY", url=DEVELOPER_LINK, style="danger"
                    )
                ],
            ]
        )
        await update.effective_message.reply_text(
            support_text, reply_markup=keyboard, parse_mode="Markdown"
        )
        return

    # Admin panel
    if text == "⚙️ ADMIN PANEL ⚙️" and is_admin(uid):
        context.user_data["admin_mode"] = "main"
        await update.effective_message.reply_text(
            "⌬━━━━━━━━━━━━━━━━━━━━⌬\n   WELCOME ADMIN PANEL\n⌬━━━━━━━━━━━━━━━━━━━━⌬",
            reply_markup=admin_main_keyboard(),
        )
        return

    if text == "🔙 BACK TO MAIN" and context.user_data.get("admin_mode"):
        context.user_data["admin_mode"] = None
        await update.effective_message.reply_text(
            "🔙 Back to main menu.", reply_markup=main_keyboard(uid)
        )
        return

    if text == "🔙 BACK TO ADMIN":
        context.user_data["user_management_mode"] = None
        context.user_data["system_config_mode"] = None
        context.user_data["required_channels_mode"] = None
        context.user_data["fake_otp_settings_mode"] = False
        context.user_data["admin_mode"] = "main"
        await update.effective_message.reply_text(
            "🔙 Back to admin panel.", reply_markup=admin_main_keyboard()
        )
        return

    if (
        text == "👥 USER MANAGEMENT"
        and context.user_data.get("admin_mode") == "main"
        and is_admin(uid)
    ):
        context.user_data["user_management_mode"] = "main"
        await update.effective_message.reply_text(
            "👥 User Management:", reply_markup=user_management_keyboard()
        )
        return

    if (
        text == "⚙️ SYSTEM CONFIGURATION"
        and context.user_data.get("admin_mode") == "main"
        and is_admin(uid)
    ):
        context.user_data["system_config_mode"] = "main"
        await update.effective_message.reply_text(
            "⚙️ System Configuration:", reply_markup=system_config_keyboard()
        )
        return

    if (
        text == "🔗 REQUIRED CHANNELS"
        and context.user_data.get("admin_mode") == "main"
        and is_admin(uid)
    ):
        context.user_data["required_channels_mode"] = "main"
        await update.effective_message.reply_text(
            "🔗 Required Channels / Groups Management:",
            reply_markup=required_channels_keyboard(),
        )
        return

    if (
        text == "⚡ FAKE OTP"
        and context.user_data.get("admin_mode") == "main"
        and is_admin(uid)
    ):
        await admin_fake_otp_menu(update, context)
        return

    if (
        text == "▶️ START"
        and context.user_data.get("admin_mode") == "main"
        and is_admin(uid)
    ):
        await admin_fake_otp_start(update, context)
        return

    if (
        text == "⏹ STOP"
        and context.user_data.get("admin_mode") == "main"
        and is_admin(uid)
    ):
        await admin_fake_otp_stop(update, context)
        return

    if (
        text == "⚙️ SETTINGS"
        and context.user_data.get("admin_mode") == "main"
        and is_admin(uid)
    ):
        await admin_fake_otp_settings(update, context)
        return

    if (
        text == "📈 TEST STATİSTİKASI"
        and context.user_data.get("admin_mode") == "main"
        and is_admin(uid)
    ):
        await admin_fake_otp_stats(update, context)
        return

    # Required channels submenu
    if (
        text == "➕ ADD CHANNEL"
        and context.user_data.get("required_channels_mode") == "main"
        and is_admin(uid)
    ):
        await admin_add_channel_start(update, context)
        return

    if (
        text == "❌ REMOVE CHANNEL"
        and context.user_data.get("required_channels_mode") == "main"
        and is_admin(uid)
    ):
        await admin_remove_channel_start(update, context)
        return

    if (
        text == "📋 LIST CHANNELS"
        and context.user_data.get("required_channels_mode") == "main"
        and is_admin(uid)
    ):
        await admin_list_channels(update, context)
        return

    # System config submenu
    if text == "🩺 SMS MONİTOR STATUSU" and is_admin(uid):
        d = monitor_diagnostics
        msg = (
            "🩺 <b>SMS MONİTOR DİAQNOSTİKASI</b>\n\n"
            f"Vəziyyət: <b>{html.escape(str(d.get('state') or '-'))}</b>\n"
            f"Son yoxlama: <code>{html.escape(str(d.get('last_check') or '-'))}</code>\n"
            f"Son uğurlu əlaqə: <code>{html.escape(str(d.get('last_success') or '-'))}</code>\n"
            f"HTTP status: <code>{html.escape(str(d.get('http_status') or '-'))}</code>\n"
            f"API statusu: <code>{html.escape(str(d.get('upstream_code') or '-'))}</code>\n"
            f"Son cavabda element sayı: <code>{int(d.get('items_seen') or 0)}</code>\n"
            f"Son xəta: <code>{html.escape(str(d.get('last_error') or '-'))}</code>\n\n"
            "ℹ️ Bu diaqnostika SMS mətni, OTP, telefon nömrəsi və istifadəçi ID-si saxlamır."
        )
        await update.effective_message.reply_text(msg, parse_mode="HTML", reply_markup=system_config_keyboard())
        return

    if (
        text == "📈 TODAY ALL STATUS"
        and context.user_data.get("system_config_mode") == "main"
        and is_admin(uid)
    ):
        t_n, t_o, s_n, s_o, tot_n, tot_o = get_global_system_stats()
        msg = (
            f"📊 <b>SYSTEM STATUS</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✨ <b>TODAY</b>\n📱 NUMBERS: {t_n}\n🔑 OTPS: {t_o}\n\n"
            f"🔥 <b>LAST 7 DAYS</b>\n📱 NUMBERS: {s_n}\n🔑 OTPS: {s_o}\n\n"
            f"🌐 <b>ALL TIME</b>\n📱 NUMBERS: {tot_n}\n🔑 OTPS: {tot_o}"
        )
        await update.effective_message.reply_text(msg, parse_mode="HTML")
        return

    if text == "👤 USER STATUS CHECK" and is_admin(uid):
        context.user_data["mode"] = "input_user_id"
        await update.effective_message.reply_text(
            "🔍 ENTER TELEGRAM ID:", reply_markup=cancel_keyboard()
        )
        return

    if context.user_data.get("mode") == "input_user_id" and is_admin(uid):
        target_uid = text.strip()
        if not target_uid.isdigit():
            await update.effective_message.reply_text("❌ INVALID ID!")
            return
        context.user_data["mode"] = None
        stats = get_user_stats(target_uid)
        msg = (
            f"👤 <b>USER STATUS</b> — <code>{target_uid}</code>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✨ TODAY: 📱 {stats['today_numbers']} | 🔑 {stats['today_otps']}\n"
            f"🔥 7 DAYS: 📱 {stats['last7d_numbers']} | 🔑 {stats['last7d_otps']}\n"
            f"🌐 ALL TIME: 📱 {stats['total_numbers']} | 🔑 {stats['total_otps']}"
        )
        await update.effective_message.reply_text(
            msg,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📂 CHECK ALL DATA",
                            callback_data=f"full_logs_{target_uid}",
                            style="primary",
                        )
                    ]
                ]
            ),
        )
        return

    if (
        text == "🆔 ALL USER ID"
        and context.user_data.get("user_management_mode") == "main"
        and is_admin(uid)
    ):
        users = get_all_users()
        if users:
            content = "\n".join(f"{i}. {u}" for i, u in enumerate(users, 1))
            f = io.BytesIO(content.encode())
            f.name = f"ALL_USERS_{len(users)}.txt"
            await update.message.reply_document(
                document=f,
                caption=f"👥 Total Users: {len(users)}",
                reply_markup=user_management_keyboard(),
            )
        else:
            await update.effective_message.reply_text(
                "No users found.", reply_markup=user_management_keyboard()
            )
        return

    if (
        text == "💰 ALL USER BALANCE"
        and context.user_data.get("user_management_mode") == "main"
        and is_admin(uid)
    ):
        user_db = load_data(USER_DATA_FILE)
        if user_db:
            total_bal = sum(v.get("balance", 0) for v in user_db.values())
            lines = [
                f"{i}. {uid_}: {v.get('balance', 0):.2f} AZN"
                for i, (uid_, v) in enumerate(user_db.items(), 1)
            ]
            content = f"💰 TOTAL BALANCE: {total_bal:.2f} AZN\n\n" + "\n".join(lines)
            f = io.BytesIO(content.encode())
            f.name = f"BALANCES_{total_bal:.0f}.txt"
            await update.message.reply_document(
                document=f,
                caption=f"💵 Total Balance: {total_bal:.2f} AZN",
                reply_markup=user_management_keyboard(),
            )
        else:
            await update.effective_message.reply_text(
                "No data.", reply_markup=user_management_keyboard()
            )
        return

    if (
        text == "👥 USER LIST (ALL)"
        and context.user_data.get("user_management_mode") == "main"
        and is_admin(uid)
    ):
        await admin_show_all_users(update, context)
        return

    if text == "📜 BAN USER LIST" and is_admin(uid):
        await show_banned_users_list(update, context)
        return

    if (
        text == "⛔ BAN USER"
        and context.user_data.get("system_config_mode") == "main"
        and is_admin(uid)
    ):
        await admin_ban_user_start(update, context)
        return

    if (
        text == "🔓 UNBAN USER"
        and context.user_data.get("system_config_mode") == "main"
        and is_admin(uid)
    ):
        await admin_unban_user_start(update, context)
        return

    if (
        text == "➕ ADD BALANCE"
        and context.user_data.get("system_config_mode") == "main"
        and is_admin(uid)
    ):
        await admin_add_balance_start(update, context)
        return

    if (
        text == "➖ REMOVE BALANCE"
        and context.user_data.get("system_config_mode") == "main"
        and is_admin(uid)
    ):
        await admin_remove_balance_start(update, context)
        return

    if (
        text == "⚙️ CHANGE MIN WITHDRAW"
        and context.user_data.get("system_config_mode") == "main"
        and is_admin(uid)
    ):
        await admin_change_min_withdraw_start(update, context)
        return

    if (
        text == "💳 TOGGLE PAYMENT METHODS"
        and context.user_data.get("system_config_mode") == "main"
        and is_admin(uid)
    ):
        await admin_toggle_payment_methods(update, context)
        return

    if (
        text == "💲 CHANGE OTP PRICE"
        and context.user_data.get("system_config_mode") == "main"
        and is_admin(uid)
    ):
        await admin_change_otp_rate_start(update, context)
        return

    if (
        text == "🔧 SET USER OTP RATE"
        and context.user_data.get("system_config_mode") == "main"
        and is_admin(uid)
    ):
        await admin_set_user_otp_rate_start(update, context)
        return

    if (
        text == "📋 VIEW USER OTP RATE"
        and context.user_data.get("system_config_mode") == "main"
        and is_admin(uid)
    ):
        await admin_view_user_otp_rate_start(update, context)
        return

    # Safe group notification tools (admin only)
    if text == "🛠 BİLDİRİŞ ALƏTLƏRİ" and context.user_data.get("admin_mode") == "main" and is_admin(uid):
        context.user_data["admin_tools_mode"] = "main"
        context.user_data.pop("group_notification_mode", None)
        await update.effective_message.reply_text("🛠 Bildiriş alətləri:", reply_markup=admin_tools_keyboard())
        return

    if text == "📢 QRUPA BİLDİRİŞ" and context.user_data.get("admin_tools_mode") == "main" and is_admin(uid):
        context.user_data["group_notification_mode"] = True
        await update.effective_message.reply_text(
            "📢 Qrupa göndəriləcək adi elan/status mətnini yazın.\n\nOTP, SMS və təsdiqləmə kodlarını göndərməyin.",
            reply_markup=cancel_keyboard(),
        )
        return

    if context.user_data.get("group_notification_mode") and is_admin(uid):
        context.user_data["group_notification_mode"] = False
        ok, detail = await send_group_notification(update.effective_message.text or "")
        icon = "✅" if ok else "❌"
        await update.effective_message.reply_text(f"{icon} {detail}", reply_markup=admin_tools_keyboard())
        return

    if text == "🧪 QRUP TESTİ" and context.user_data.get("admin_tools_mode") == "main" and is_admin(uid):
        ok, detail = await send_group_notification("🧪 Test bildirişi: qrup bildiriş sistemi işləyir.")
        icon = "✅" if ok else "❌"
        await update.effective_message.reply_text(f"{icon} {detail}", reply_markup=admin_tools_keyboard())
        return

    if text == "ℹ️ BİLDİRİŞ STATUSU" and context.user_data.get("admin_tools_mode") == "main" and is_admin(uid):
        group_state = "✅ qurulub" if NOTIFY_GROUP_ID else "❌ qurulmayıb"
        token_state = "✅ qurulub" if NOTIFY_BOT_TOKEN else "❌ qurulmayıb"
        await update.effective_message.reply_text(
            f"ℹ️ QRUP BİLDİRİŞ STATUSU\n\nNOTIFY_GROUP_ID: {group_state}\nBot tokeni: {token_state}",
            reply_markup=admin_tools_keyboard(),
        )
        return

    if text == "🔙 İNZİBATÇI PANELİNƏ QAYIT" and context.user_data.get("admin_tools_mode") == "main" and is_admin(uid):
        context.user_data.pop("admin_tools_mode", None)
        context.user_data.pop("group_notification_mode", None)
        await update.effective_message.reply_text("🔐 İnzibatçı paneli", reply_markup=admin_main_keyboard())
        return

    await update.effective_message.reply_text(
        "🔹 PLEASE USE THE BUTTONS BELOW:", reply_markup=main_keyboard(uid)
    )



# ==================== AZERBAIJAN RANGE PERMISSIONS ====================
async def az_access_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.effective_message.reply_text(
        "🇦🇿 +994 giriş: " + ("✅ Təsdiqlənib" if az_range_allowed(uid) else "🔒 Admin təsdiqi tələb olunur.")
    )


async def az_request_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or update.effective_chat.type != "private":
        return
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.effective_message.reply_text("🚫 Giriş məhdudlaşdırılıb.")
        return
    if az_range_allowed(uid):
        await update.effective_message.reply_text("✅ +994 nömrələrinə girişiniz var.")
        return
    now = time.monotonic()
    if now - _az_request_times.get(uid, 0) < 300:
        await update.effective_message.reply_text(
            "⏳ İcazə sorğusu artıq göndərilib. Təkrar sorğu üçün 5 dəqiqə gözləyin."
        )
        return
    # Only request authorization; never send an SMS or allocate a number.
    notices = 0
    for admin_id in ADMINS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🇦🇿 +994 icazə sorğusu: Telegram ID {uid}\\n"
                     f"İcazə: /az_approve {uid}\\nİmtina/ləğv: /az_revoke {uid}",
            )
            notices += 1
        except TelegramError:
            continue
    if notices:
        _az_request_times[uid] = now
    await update.effective_message.reply_text(
        "📨 İcazə sorğunuz adminə göndərildi." if notices else
        "⚠️ Adminə çatdırılmadı. Adminlə əlaqə saxlayın."
    )


async def az_approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or update.effective_chat.type != "private":
        await update.effective_message.reply_text("⛔ Yalnız admin.")
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.effective_message.reply_text("İstifadə: /az_approve TELEGRAM_ID")
        return
    target = context.args[0]
    if not user_exists(target):
        await update.effective_message.reply_text("Bu ID botda qeydiyyatda deyil.")
        return
    access = load_data(AZ_ACCESS_FILE)
    access[target] = True
    save_data(access, AZ_ACCESS_FILE)
    await update.effective_message.reply_text(f"✅ +994 icazəsi verildi: {target}")
    try:
        await context.bot.send_message(int(target), "✅ Azərbaycan (+994) nömrələrindən istifadə icazəniz təsdiqləndi.")
    except TelegramError:
        pass


async def az_revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or update.effective_chat.type != "private":
        await update.effective_message.reply_text("⛔ Yalnız admin.")
        return
    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.effective_message.reply_text("İstifadə: /az_revoke TELEGRAM_ID")
        return
    target = context.args[0]
    access = load_data(AZ_ACCESS_FILE)
    access.pop(target, None)
    save_data(access, AZ_ACCESS_FILE)
    await update.effective_message.reply_text(f"🔒 +994 icazəsi ləğv edildi: {target}")


# ==================== COMMAND HANDLERS ====================
async def get1number_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.effective_message.reply_text(
            "🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid)
        )
        return
    await show_app_selection(update, context)


async def searchotp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.effective_message.reply_text(
            "🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid)
        )
        return
    context.user_data["mode"] = "search_otp"
    await update.effective_message.reply_text(
        "🔍 **ENTER THE NUMBER TO SEARCH OTP:**", parse_mode="Markdown"
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.effective_message.reply_text(
            "🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid)
        )
        return
    balance = get_user(uid)["balance"]
    await update.effective_message.reply_text(
        f"💰 BALANCE: `{format_balance(balance)} AZN`",
        parse_mode="Markdown",
        reply_markup=main_keyboard(uid),
    )


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.effective_message.reply_text(
            "🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid)
        )
        return
    user_data = get_user(uid)
    stats = get_user_stats(uid)
    user = update.effective_user
    profile_text = (
        f"👤 **YOUR PROFILE**\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏷️ NAME: `{user.full_name}`\n"
        f"🆔 USERNAME: @{user.username or 'No username'}\n"
        f"🗝️ ID: `{uid}`\n\n"
        f"💵 BALANCE: {format_balance(user_data.get('balance', 0))} AZN\n\n"
        f"✨ TODAY: 📱 {stats['today_numbers']} | 🔑 {stats['today_otps']}\n"
        f"🔥 7 DAYS: 📱 {stats['last7d_numbers']} | 🔑 {stats['last7d_otps']}\n"
        f"🌐 ALL TIME: 📱 {stats['total_numbers']} | 🔑 {stats['total_otps']}"
    )
    await update.effective_message.reply_text(profile_text, parse_mode="Markdown")


async def leaderboard_command_slash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.effective_message.reply_text(
            "🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid)
        )
        return
    await leaderboard_command(update, context)


# ==================== START & CALLBACK ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    uid_str = str(uid)
    existing_data = load_data(USER_DATA_FILE)
    is_new_user = uid_str not in existing_data
    if is_new_user:
        get_user(uid)

    # /start verən istifadəçinin əsas profil məlumatlarını saxla / yenilə.
    # Beləliklə admin paneldə yalnız ID yox, ad və username də görünür.
    try:
        tg_user = update.effective_user
        db = load_data(USER_DATA_FILE)
        record = db.get(uid_str, {})
        record["user_id"] = uid_str
        record["first_name"] = tg_user.first_name or ""
        record["last_name"] = tg_user.last_name or ""
        record["username"] = tg_user.username or ""
        if not record.get("joined_at"):
            record["joined_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record["last_start_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db[uid_str] = record
        save_data(db, USER_DATA_FILE)
    except Exception as e:
        print(f"User profile save error: {e}")

    channels = load_required_channels()
    if channels:
        missing = []
        for ch in channels:
            ok, _ = await check_user_joined(context.bot, uid, ch)
            if not ok:
                missing.append(ch)
        if missing:
            lang = get_user_language(uid)
            await update.effective_message.reply_text(
                t(lang, "membership_required"),
                reply_markup=membership_keyboard(channels, lang),
            )
            return

    args = context.args
    if args:
        param = args[0]
        if is_range_request(param) and not (param.isdigit() and param in existing_data):
            await request_queue.put({
                "type": "auto_number",
                "update": update,
                "context": context,
                "range_text": param,
            })
            return
    context.user_data.clear()
    if not get_user_language(uid) or "language" not in load_data(USER_DATA_FILE).get(uid_str, {}):
        await update.effective_message.reply_text(
            "🌐 Dili seçin / Choose language",
            reply_markup=language_keyboard(),
        )
        return
    lang = get_user_language(uid)
    await update.effective_message.reply_text(
        WELCOME_MESSAGE.replace("💎", premium_html_emoji("💎", "balance"), 1),
        parse_mode="HTML", reply_markup=ReplyKeyboardRemove(),
    )
    await update.effective_message.reply_text(
        ("🔹 Aşağıdakı düymələrdən istifadə edin:" if lang == "az" else
             "🔹 Aşağıdaki düğmeleri kullanın:" if lang == "tr" else
             "🔹 PLEASE USE THE BUTTONS BELOW:"),
        reply_markup=main_keyboard(uid),
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    await query.answer()

    if data in ("lang_az", "lang_en", "lang_tr"):
        lang = data.split("_", 1)[1]
        db = load_data(USER_DATA_FILE)
        record = db.get(str(uid), {})
        record["language"] = lang
        db[str(uid)] = record
        save_data(db, USER_DATA_FILE)
        await query.edit_message_text(t(lang, "language_saved"))
        menu_hint = (
            "🔹 Aşağıdakı düymələrdən istifadə edin:" if lang == "az" else
            "🔹 Aşağıdaki düğmeleri kullanın:" if lang == "tr" else
            "🔹 PLEASE USE THE BUTTONS BELOW:"
        )
        await query.message.reply_text(menu_hint, reply_markup=main_keyboard(uid))
        return

    if data.startswith("range_collect_stop_"):
        await range_collector.stop(query)
        return

    if data in ("back_services", "back_to_main") and context.user_data.get("mode") == "custom_range_collect":
        context.user_data["mode"] = None

    if data == "verify_me":
        await verify_user(update, context)
        return

    if not is_admin(uid) and is_user_banned(uid):
        await query.edit_message_text("🚫 YOU ARE BANNED 🚫")
        return

    # Enforce required channel/group membership for user-facing actions.
    if data.startswith("menu_"):
        channels = load_required_channels()
        if channels:
            missing = []
            for ch in channels:
                ok, _ = await check_user_joined(context.bot, uid, ch)
                if not ok:
                    missing.append(ch)
            if missing:
                lang = get_user_language(uid)
                await query.message.reply_text(
                    t(lang, "membership_required"),
                    reply_markup=membership_keyboard(channels, lang),
                )
                return

    if data == "menu_ivas_web_panel" or data == "menu_lamix_panel":
        ivassms_url = os.environ.get("IVASSMS_WEB_URL", "https://ivasssmsm-web.onrender.com").strip()
        if not ivassms_url.startswith("https://"):
            await query.message.reply_text("🧩 IVAS SMS veb-panel ünvanı düzgün deyil.")
            return
        await query.message.reply_text(
            "🧩 <b>IVAS SMS WEB PANEL</b>\n\n"
            "Bu veb-panel ayrıca işləyir və əsas botun məlumatları ilə birləşdirilmir.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🌐 IVAS PANELİ AÇ", url=ivassms_url)]
            ]),
        )
        return

    # USER INLINE MENU
    if data in ("menu_numbers_txt", "menu_all_numbers_txt"):
        await download_numbers_txt(update, context, all_numbers=data == "menu_all_numbers_txt")
        return
    if data == "menu_language":
        lang = get_user_language(uid)
        prompt = (
            "🌐 Dili seçin" if lang == "az" else
            "🌐 Dil seçin" if lang == "tr" else
            "🌐 Choose language"
        )
        await query.message.reply_text(prompt, reply_markup=language_keyboard())
        return
    if data == "menu_get_number":
        await show_app_selection(update, context)
        return
    if data == "menu_active_numbers":
        await show_active_numbers(update, context)
        return
    if data == "menu_search_otp":
        context.user_data["mode"] = "search_otp"
        await query.message.reply_text("🔍 <b>NÖMRƏNİ DAXİL EDİN:</b>", parse_mode="HTML")
        return
    if data == "menu_get_2fa":
        await get_2fa_code(update, context)
        return
    if data == "menu_balance":
        balance = get_user(uid)["balance"]
        await query.message.reply_text(
            f"💰 <b>YOUR CURRENT BALANCE</b>\n\n<blockquote>💵 TOTAL: <b>{format_balance(balance)} AZN</b></blockquote>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💸 WITHDRAW", callback_data="withdraw_start", style="primary")]])
        )
        return
    if data == "menu_profile":
        user_data = get_user(uid)
        stats = get_user_stats(uid)
        user = update.effective_user
        full_name = html.escape(user.full_name)
        username = html.escape(user.username or "No username")
        profile_text = (
            f"👤 <b>YOUR PROFILE</b>\n\n"
            f"<blockquote>🏷️ NAME: <b>{full_name}</b>\n🆔 USERNAME: @{username}\n🗝️ TELEGRAM ID: <code>{uid}</code></blockquote>\n"
            f"<blockquote>💵 BALANCE: <b>{format_balance(user_data.get('balance', 0))} AZN</b></blockquote>\n"
            f"<blockquote>✨ TODAY — 📱 {stats['today_numbers']} | 🔑 {stats['today_otps']}\n"
            f"🔥 7 DAYS — 📱 {stats['last7d_numbers']} | 🔑 {stats['last7d_otps']}\n"
            f"🌐 ALL — 📱 {stats['total_numbers']} | 🔑 {stats['total_otps']}</blockquote>"
        )
        await query.message.reply_text(profile_text, parse_mode="HTML", reply_markup=main_keyboard(uid))
        return
    if data == "menu_leaderboard":
        await leaderboard_command(update, context)
        return
    if data == "menu_support":
        await query.message.reply_text(
            "💬 SUPPORT 🎧",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 SUPPORT", url=SUPPORT_LINK, style="primary")],
                [InlineKeyboardButton("👨‍💻 DEVELOPER BY", url=DEVELOPER_LINK, style="danger")],
            ]),
        )
        return
    if data == "menu_admin" and is_admin(uid):
        context.user_data["admin_mode"] = "main"
        await query.message.reply_text("⌬━━━━━━━━━━━━━━━━━━━━⌬\n   WELCOME ADMIN PANEL\n⌬━━━━━━━━━━━━━━━━━━━━⌬", reply_markup=admin_main_keyboard())
        return

    if data == "menu_az_ranges":
        await show_az_operator_menu(query, uid)
        return
    if data.startswith("az_operator_"):
        await show_az_prefix_menu(query, data.removeprefix("az_operator_"))
        return
    if data.startswith("az_prefix_"):
        await show_az_suffix_menu(query, uid, data.removeprefix("az_prefix_"))
        return
    if data.startswith("az_page_"):
        payload = data.removeprefix("az_page_").split("_", 1)
        if len(payload) == 2 and payload[1].isdigit():
            await show_az_suffix_menu(query, uid, payload[0], int(payload[1]))
        return
    if data.startswith("az_pick_"):
        rid = data.removeprefix("az_pick_")
        if not az_range_allowed(uid):
            await query.message.reply_text(AZ_ACCESS_DENIED)
            return
        services = await fetch_services_cached()
        if not az_catalog_lookup(rid=rid, services=services):
            await query.message.reply_text("❌ Bu range API siyahısında yoxdur.")
            return
        await fast_allocate_number(query, context, rid, "AZ", rid + "XXX")
        return

    if data == "menu_all_countries":
        await show_all_countries(update, context)
        return
    if data.startswith("menu_countries_page_"):
        try:
            page = int(data.removeprefix("menu_countries_page_"))
        except ValueError:
            return
        await show_all_countries(update, context, page=page, refresh=False)
        return
    if data.startswith("menu_all_country_"):
        iso = data.removeprefix("menu_all_country_")
        info = next((row for row in context.user_data.get("all_country_rows", [])
                     if row["iso"] == iso), None)
        if info is None:
            await show_all_countries(update, context)
            return
        if not info["ranges"]:
            await query.message.reply_text(
                f"{info['flag']} {info['name']} (+{info['prefix']})\n"
                "API hazırda bu ölkə kodu üçün range elan etmir. "
                "Digər ölkələrə baxın və ya siyahını yenidən açın.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌍 Bütün ölkələr",
                                          callback_data="menu_all_countries")]
                ]),
            )
            return
        await show_country_ranges(update, context, info, "menu_all_countries")
        return

    if data.startswith("menu_service_country_"):
        prefix = data.removeprefix("menu_service_country_")
        service = context.user_data.get("la_service")
        countries = _collect_all_countries({service: context.user_data.get("la_ranges", [])}) if service else []
        info = next((row for row in countries if row["prefix"] == prefix), None)
        if info is None:
            await show_app_selection(update, context)
        elif len(info["ranges"]) > 1:
            await show_country_ranges(update, context, info, "back_services")
        else:
            entry = info["ranges"][0]
            await fast_allocate_number(query, context, entry["rid"], entry["service"], entry["display"])
        return

    if data.startswith(("menu_range_pick_", "menu_range_page_")):
        parts = data.rsplit("_", 2)
        view = context.user_data.get("country_range_view")
        if not view or view["token"] != parts[-2]:
            await show_all_countries(update, context)
            return
        try:
            index = int(parts[-1])
        except ValueError:
            return
        if data.startswith("menu_range_page_"):
            await show_country_ranges(update, context, page=index)
        elif 0 <= index < len(view["info"]["ranges"]):
            entry = view["info"]["ranges"][index]
            await fast_allocate_number(query, context, entry["rid"], entry["service"], entry["display"])
        return

    # SERVICE SELECTION
    if data.startswith("svcidx_"):
        # Resolve the index against the exact ordered list shown to this user,
        # not a freshly fetched API response whose order may have changed.
        displayed_services = context.user_data.get("la_services") or {}
        try:
            service_index = int(data[7:])
            service = list(displayed_services.keys())[service_index]
        except (ValueError, IndexError):
            await query.answer("Xidmət siyahısı yenilənib. Yenidən açın.", show_alert=True)
            return
        services = await fetch_services_cached()
        if service not in services:
            await query.answer('Bu xidmət hazırda mövcud deyil.', show_alert=True)
            return
        ranges = services[service]
        if not ranges:
            await query.answer('Bu xidmət üçün heç bir diapazon mövcud deyil.', show_alert=True)
            return
        context.user_data["la_service"] = service
        context.user_data["la_ranges"] = ranges
        keyboard = _build_countries_keyboard(ranges, service, uid)
        await query.message.edit_text(
            f"📡✨ {service.upper()} - AVAILABLE COUNTRIES ✨📡\n\n"
            f"<blockquote>📱 Service: <b>{html.escape(service)}</b></blockquote>\n"
            f"<blockquote>🌍 🔥isti ölkələr göstərilir:</blockquote>",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    # HOT RANGE SELECTION
    if data.startswith("hotrid_"):
        rid = data[7:]
        if not rid:
            await query.answer("Range məlumatı düzgün deyil.", show_alert=True)
            return
        service = context.user_data.get("la_service", "CUSTOM")
        range_display = rid + "XXX"
        await fast_allocate_number(query, context, rid, service, range_display)
        return

    # CUSTOM RANGE
    if data in ("custom_range", "custom_range_single"):
        context.user_data["mode"] = ("custom_range" if data == "custom_range_single" else "custom_range_collect")
        await query.message.edit_text(
            ("⚙️ <b>CUSTOM RANGE — TƏK NÖMRƏ</b>\n\n" if data == "custom_range_single" else
             "📥 <b>CUSTOM RANGE — NÖMRƏLƏRİ TOPLA</b>\n"
             "Maksimum 50 sorğu ilə unikal nömrələr TXT kimi veriləcək.\n\n") +
            '<blockquote>📶 Fərdi diapazonunuzu daxil edin.\n'
            'Nümunə: <code>234XXX</code> və ya <code>26134</code></blockquote>\n\n'
            '<blockquote>⌨️ Aşağıda diapazonu yazıb göndərin:</blockquote>',
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("📞 Tək nömrə al", callback_data="custom_range_single")],
                    [
                        InlineKeyboardButton(
                            "◀️ BACK", callback_data="back_services", style="danger"
                        )
                    ]
                ]
            ),
        )
        return

    # BACK TO SERVICES
    if data == "back_services":
        services = await fetch_services_cached()
        if not services:
            await query.message.edit_text('❌ Heç bir xidmət mövcud deyil.')
            return
        displayed_services = dict(sorted(services.items()))
        context.user_data["la_services"] = displayed_services
        keyboard = _build_services_keyboard(displayed_services)
        await query.message.edit_text(
            "📡✨ XİDMƏT SEÇİN ✨📡\n\n"
            "<blockquote>API-də hazırda mövcud olan bütün xidmətlər aşağıda göstərilir.</blockquote>",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    # SAME RANGE (fixed)
    if data.startswith("same_range_"):
        parts = data.split("_")
        if len(parts) < 3:
            await query.answer("Invalid same range data.", show_alert=True)
            return
        rid = parts[2]
        if is_az_range(rid) and not az_range_allowed(uid):
            await query.message.reply_text(AZ_ACCESS_DENIED)
            return
        service = parts[3] if len(parts) > 3 else "CUSTOM"
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except:
            pass
        try:
            num, country = await get_number_from_api(rid, requester_id=uid)
        except Exception as e:
            await query.message.reply_text(
                f"❌ Server error: {str(e)[:100]}", reply_markup=main_keyboard(uid)
            )
            return
        if not num:
            await query.message.reply_text(
                "❌ <b>Hal-hazırda bu diapazonda Nömrələr yoxdur!</b>\n\n"
                "<blockquote>⚠️ Xahiş edirəm başqa bir sıra seçin və ya sonra yenidən cəhd edin.</blockquote>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "◀️ BACK TO SERVICES",
                                callback_data="back_services",
                                style="danger",
                            )
                        ]
                    ]
                ),
            )
            return
        clean_num = normalize_number(num)
        active_numbers[clean_num] = {
            "uid": uid,
            "range": rid,
            "timestamp": datetime.now(),
        }
        add_number_taken(uid, 1)
        save_number_range_info(uid, clean_num, rid)
        flag, cname = get_country_info(clean_num)
        text = (
            f"✅ <b>YOUR NEW NUMBER FROM SAME RANGE</b> ✅\n\n"
            f"<blockquote>🌍 COUNTRY: <code>{flag} {cname}</code></blockquote>\n"
            f"<blockquote>📶 RANGE: <code>{rid}</code></blockquote>\n"
            f"<blockquote>📱 SERVICE: <code>{service.upper()}</code></blockquote>\n"
            f"<blockquote>📞 NUMBER: <code>{num}</code></blockquote>\n\n"
            f"<b>📩 SMS STATUS: ⏳ WAITING...</b>"
        )
        new_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔄 SAME RANGE",
                        callback_data=f"same_range_{rid}_{service}",
                        style="success",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📢 OTP GROUP", url="https://t.me/betrunaz", style="primary"
                    )
                ],
                [InlineKeyboardButton("◀️ BACK", callback_data="back_to_services")],
            ]
        )
        await query.message.reply_text(
            text, parse_mode="HTML", reply_markup=new_keyboard
        )
        return

    # WITHDRAW
    if data == "withdraw_start":
        balance = get_user(uid)["balance"]
        config = load_system_config()
        min_with = config["min_withdraw"]
        if balance < min_with:
            await query.message.reply_text(
                f"<blockquote>💵 BALANCE: {format_balance(balance)} AZN\n📉 MIN WITHDRAW: {min_with} AZN</blockquote>",
                parse_mode="HTML",
            )
            return
        context.user_data["withdraw_mode"] = "select_method"
        await query.message.reply_text(
            "💳 SELECT YOUR PAYMENT METHOD!", reply_markup=withdraw_method_keyboard()
        )
        return

    if data == "withdraw_confirm":
        await process_withdraw_confirm(update, context)
        return

    if data == "withdraw_cancel":
        await process_withdraw_cancel(update, context)
        return

    if data.startswith("admin_approve_"):
        await admin_approve_withdraw(
            update, context, data.replace("admin_approve_", "")
        )
        return

    if data.startswith("admin_reject_"):
        await admin_reject_withdraw(update, context, data.replace("admin_reject_", ""))
        return

    # BACK BUTTONS
    if data == "back_to_main":
        await query.edit_message_text("🔙 Returning to main menu...")
        await query.message.chat.send_message(
            "🔹 PLEASE USE THE BUTTONS BELOW:", reply_markup=main_keyboard(uid)
        )
        context.user_data.clear()
        return

    if data == "back_to_services":
        services = await fetch_services_cached()
        if not services:
            await query.edit_message_text('❌ Heç bir xidmət mövcud deyil.')
            return
        keyboard = _build_services_keyboard(services)
        await query.edit_message_text(
            "📡✨ XİDMƏT SEÇİN ✨📡\n\n"
            "<blockquote>API-də hazırda mövcud olan bütün xidmətlər aşağıda göstərilir.</blockquote>",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    # Handle toggle payment methods callback
    if data.startswith("toggle_method_"):
        await handle_toggle_method_callback(update, context)
        return

    if data == "back_to_admin_panel":
        await query.message.delete()
        await query.message.chat.send_message(
            "⚙️ System Configuration:", reply_markup=system_config_keyboard()
        )
        return

    # COPY / MISC
    if data.startswith("copy_id_"):
        await query.answer(
            f"✅ Copied ID: {data.replace('copy_id_', '')}", show_alert=True
        )
        return

    if data.startswith("copy_text_"):
        await query.answer(
            f"✅ Copied: {data.replace('copy_text_', '')}", show_alert=True
        )
        return

    if data.startswith("full_logs_"):
        target_uid = data.replace("full_logs_", "")
        stats = get_user_stats(target_uid)
        all_logs = load_data(ACTIVITY_LOGS_FILE)
        user_db = load_data(USER_DATA_FILE)
        user_info = user_db.get(str(target_uid), {})
        user_otps = [
            log
            for log in all_logs
            if str(log.get("uid")) == str(target_uid)
            and log.get("action") == "OTP_RECEIVED"
        ]
        content = (
            f"📊 USER DATA REPORT — {target_uid}\n"
            f"💰 BALANCE: {user_info.get('balance', 0):.2f} AZN\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"TODAY NUMBERS: {stats['today_numbers']}\n"
            f"TODAY OTPS: {stats['today_otps']}\n"
            f"7D NUMBERS: {stats['last7d_numbers']}\n"
            f"7D OTPS: {stats['last7d_otps']}\n"
            f"TOTAL NUMBERS: {stats['total_numbers']}\n"
            f"TOTAL OTPS: {stats['total_otps']}\n"
            f"━━━━━━━━━━━━━━━━━━\n\nOTP LOGS:\n"
        )
        for i, log in enumerate(user_otps, 1):
            try:
                dt_obj = datetime.fromisoformat(log["timestamp"])
                d = log.get("details", {})
                content += f"{i}. {dt_obj.strftime('%d/%m/%Y %I:%M %p')}\n   📞 {d.get('number', 'N/A')}\n   🔑 {d.get('otp', 'N/A')}\n\n"
            except:
                continue
        f = io.BytesIO(content.encode())
        f.name = f"USER_{target_uid}.txt"
        await context.bot.send_document(
            chat_id=uid,
            document=f,
            caption=f"✅ <b>DATA FOR USER: <code>{target_uid}</code></b>",
            parse_mode="HTML",
        )
        return



# ==================== TELEGRAM MINI APP ====================
async def webapp_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message or not update.message.web_app_data:
        return

    uid = update.effective_user.id
    if is_user_banned(uid):
        await update.effective_message.reply_text("🚫 YOU ARE BANNED 🚫", reply_markup=main_keyboard(uid))
        return

    try:
        payload = json.loads(update.message.web_app_data.data)
    except Exception:
        await update.effective_message.reply_text("❌ Mini App məlumatı oxunmadı.")
        return

    action = str(payload.get("action", "")).strip().lower()

    if action == "get_number":
        await show_app_selection(update, context)
    elif action == "active_numbers":
        await show_active_numbers(update, context)
    elif action == "search_otp":
        context.user_data["mode"] = "search_otp"
        await update.effective_message.reply_text("🔍 OTP axtarmaq üçün nömrəni göndərin:")
    elif action == "get_2fa":
        await get_2fa_code(update, context)
    elif action == "balance":
        balance = get_user(uid).get("balance", 0)
        await update.effective_message.reply_text(
            f"💰 <b>BALANS</b>\n\n<blockquote>💵 {format_balance(balance)} AZN</blockquote>",
            parse_mode="HTML",
        )
    elif action == "profile":
        stats = get_user_stats(uid)
        user_data = get_user(uid)
        user = update.effective_user
        name = html.escape(user.full_name or "İstifadəçi")
        username = html.escape(user.username or "yoxdur")
        msg = (
            f"👤 <b>PROFİL</b>\n\n"
            f"<blockquote>🏷️ Ad: <b>{name}</b></blockquote>\n"
            f"<blockquote>🆔 Username: @{username}</blockquote>\n"
            f"<blockquote>🔑 Telegram ID: <code>{uid}</code></blockquote>\n"
            f"<blockquote>💰 Balans: <b>{format_balance(user_data.get('balance', 0))} AZN</b></blockquote>\n\n"
            f"📊 Bu gün: {stats['today_numbers']} nömrə / {stats['today_otps']} OTP\n"
            f"🌐 Ümumi: {stats['total_numbers']} nömrə / {stats['total_otps']} OTP"
        )
        await update.effective_message.reply_text(msg, parse_mode="HTML")
    elif action == "leaderboard":
        await leaderboard_command(update, context)
    elif action == "support":
        await update.effective_message.reply_text(
            "💬 Dəstək",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("💬 DƏSTƏK", url=SUPPORT_LINK)]]
            ),
        )
    elif action in {"admin_panel", "system_config", "user_management", "required_channels"}:
        if not is_admin(uid):
            await update.effective_message.reply_text("⛔ Bu bölmə yalnız admin üçündür.")
            return
        if action == "admin_panel":
            context.user_data["admin_mode"] = "main"
            await update.effective_message.reply_text("⚙️ ADMIN PANEL", reply_markup=admin_main_keyboard())
        elif action == "system_config":
            context.user_data["admin_mode"] = "main"
            context.user_data["system_config_mode"] = "main"
            await update.effective_message.reply_text("⚙️ SYSTEM CONFIGURATION", reply_markup=system_config_keyboard())
        elif action == "user_management":
            context.user_data["admin_mode"] = "main"
            context.user_data["user_management_mode"] = "main"
            await update.effective_message.reply_text("👥 USER MANAGEMENT", reply_markup=user_management_keyboard())
        elif action == "required_channels":
            context.user_data["admin_mode"] = "main"
            context.user_data["required_channels_mode"] = "main"
            await update.effective_message.reply_text("🔗 REQUIRED CHANNELS", reply_markup=required_channels_keyboard())
    else:
        await update.effective_message.reply_text("⚠️ Naməlum Mini App əməliyyatı.")


# ==================== MINI APP HTTP API ====================
def validate_telegram_init_data(init_data: str, max_age: int = 86400):
    if not init_data:
        return None, "missing_init_data"
    if not BOT_TOKEN:
        return None, "missing_bot_token"
    try:
        data = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = data.pop("hash", "")
        auth_date = int(data.get("auth_date", "0"))
        now = int(time.time())
        if not received_hash:
            return None, "missing_hash"
        if not auth_date:
            return None, "missing_auth_date"
        if now - auth_date > max_age:
            return None, "expired_init_data"
        if auth_date - now > 300:
            return None, "future_auth_date"
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
        expected = hmac.new(secret_key, check_string.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected.lower(), received_hash.lower()):
            return None, "hash_mismatch"
        user = json.loads(data.get("user", "{}"))
        if not user.get("id"):
            return None, "missing_user"
        return user, None
    except (ValueError, TypeError):
        return None, "invalid_auth_date"
    except json.JSONDecodeError:
        return None, "invalid_user_json"
    except Exception as exc:
        print(f"Mini App initData parse error: {type(exc).__name__}: {exc}")
        return None, "invalid_init_data"


def _miniapp_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "https://feridceferli.github.io"
    resp.headers["Access-Control-Allow-Headers"] = "X-Telegram-Init-Data, Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Vary"] = "Origin"
    return resp


async def miniapp_dashboard(request):
    if request.method == "OPTIONS":
        return _miniapp_cors(web.Response(status=204))
    tg_user, auth_error = validate_telegram_init_data(request.headers.get("X-Telegram-Init-Data", ""))
    if not tg_user:
        print(f"Mini App auth rejected: {auth_error}")
        return _miniapp_cors(web.json_response({"error": "unauthorized", "reason": auth_error}, status=401))
    uid = int(tg_user["id"])
    if is_user_banned(uid):
        return _miniapp_cors(web.json_response({"error": "banned"}, status=403))

    user = get_user(uid)
    stats = get_user_stats(uid)
    now = datetime.now()
    orders = []
    for number, info in list(active_numbers.items()):
        if int(info.get("uid", 0)) != uid:
            continue
        ts = info.get("timestamp") or now
        age = max(0, int((now - ts).total_seconds()))
        if age >= 3600:
            continue
        orders.append({
            "label": "Aktiv sifariş",
            "number_masked": "+" + mask_number(normalize_number(number)),
            "range": str(info.get("range", "—")),
            "status": "SMS gözlənilir",
            "remaining_seconds": max(0, 3600 - age),
        })

    return _miniapp_cors(web.json_response({
        "user": {
            "id": uid,
            "first_name": tg_user.get("first_name", ""),
            "last_name": tg_user.get("last_name", ""),
            "username": tg_user.get("username", ""),
            "is_admin": is_admin(uid),
            "az_approved": az_range_allowed(uid),
        },
        "balance": format_balance(user.get("balance", 0)),
        "stats": {
            "today_numbers": stats.get("today_numbers", 0),
            "total_numbers": stats.get("total_numbers", 0),
            "last24h_numbers": stats.get("last24h_numbers", 0),
            "last7d_numbers": stats.get("last7d_numbers", 0),
        },
        "support_url": SUPPORT_LINK,
        "orders": orders,
    }))


# Mini App safe order/test-SMS state (no real SMS/OTP content)
miniapp_orders = {}
miniapp_history = {}

def _miniapp_auth(request):
    return validate_telegram_init_data(request.headers.get("X-Telegram-Init-Data", ""))

def _safe_order(uid, order):
    age = max(0, int(time.time() - order["created_at"]))
    return {"id": order["id"], "label": order["label"], "number_masked": order["number_masked"], "range": order["range"], "status": order["status"], "remaining_seconds": max(0, 3600-age), "created_at": order["created_at"]}

async def miniapp_orders_api(request):
    if request.method == "OPTIONS": return _miniapp_cors(web.Response(status=204))
    tg_user, err = _miniapp_auth(request)
    if not tg_user: return _miniapp_cors(web.json_response({"error":"unauthorized","reason":err}, status=401))
    uid=int(tg_user["id"])
    if request.method == "GET":
        active=[_safe_order(uid,o) for o in miniapp_orders.get(uid,[]) if o["status"]=="Aktiv"]
        history=miniapp_history.get(uid,[])[-20:][::-1]
        return _miniapp_cors(web.json_response({"orders":active,"history":history}))
    body=await request.json()
    action=body.get("action")
    if action=="create_test":
        oid=f"T{int(time.time()*1000)}"
        # Clearly synthetic number; never allocated from a real SMS provider.
        order={"id":oid,"label":"Test sifarişi","number_masked":"+994 50 *** ** 67","range":"Sandbox","status":"Aktiv","created_at":time.time()}
        miniapp_orders.setdefault(uid,[]).append(order)
        return _miniapp_cors(web.json_response({"ok":True,"order":_safe_order(uid,order)}))
    if action=="cancel":
        oid=str(body.get("id",""))
        for o in miniapp_orders.get(uid,[]):
            if o["id"]==oid and o["status"]=="Aktiv":
                o["status"]="Ləğv edildi"; miniapp_history.setdefault(uid,[]).append(_safe_order(uid,o)); return _miniapp_cors(web.json_response({"ok":True}))
        return _miniapp_cors(web.json_response({"error":"not_found"},status=404))
    return _miniapp_cors(web.json_response({"error":"bad_action"},status=400))

async def miniapp_test_sms(request):
    if request.method == "OPTIONS": return _miniapp_cors(web.Response(status=204))
    tg_user, err = _miniapp_auth(request)
    if not tg_user: return _miniapp_cors(web.json_response({"error":"unauthorized","reason":err},status=401))
    uid=int(tg_user["id"]); oid=request.query.get("order_id","")
    owned=any(o["id"]==oid for o in miniapp_orders.get(uid,[]))
    if not owned: return _miniapp_cors(web.json_response({"error":"not_found"},status=404))
    return _miniapp_cors(web.json_response({"messages":[{"id":"demo-1","sender":"Sandbox","text":"Bu test SMS-dir. Kod: 583921","code":"583921","is_test":True,"label":"Test məlumatı"}]}))


async def miniapp_admin_api(request):
    if request.method == "OPTIONS": return _miniapp_cors(web.Response(status=204))
    tg_user, err = _miniapp_auth(request)
    if not tg_user: return _miniapp_cors(web.json_response({"error":"unauthorized","reason":err},status=401))
    uid=int(tg_user["id"])
    if not is_admin(uid): return _miniapp_cors(web.json_response({"error":"forbidden"},status=403))
    users=load_data(USER_DATA_FILE)
    if request.method=="GET":
        rows=[]
        for user_id,data in list(users.items())[-100:]:
            rows.append({"id":user_id,"name":data.get("full_name") or data.get("username") or "İstifadəçi","balance":format_balance(data.get("balance",0)),"banned":is_user_banned(user_id),"az_approved":az_range_allowed(user_id)})
        cfg=load_system_config()
        return _miniapp_cors(web.json_response({"user_count":len(users),"users":rows,"config":{"min_withdraw":cfg.get("min_withdraw"),"max_withdraw":cfg.get("max_withdraw"),"payment_methods":cfg.get("payment_methods",{})}}))
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError()
    except (ValueError, TypeError):
        return _miniapp_cors(web.json_response({"error": "invalid_request"}, status=400))
    action = body.get("action")
    target = str(body.get("user_id", "")).strip()
    if action in ("az_approve", "az_revoke"):
        if not target.isdecimal() or len(target) > 20 or int(target) <= 0:
            return _miniapp_cors(web.json_response({"error": "invalid_user_id"}, status=400))
        if action == "az_approve" and not user_exists(target):
            return _miniapp_cors(web.json_response({"error": "user_not_found"}, status=404))
        access = load_data(AZ_ACCESS_FILE)
        if action == "az_approve":
            access[target] = True
        else:
            access.pop(target, None)
        save_data(access, AZ_ACCESS_FILE)
        if action == "az_approve":
            try:
                await request.app["telegram_bot"].send_message(
                    chat_id=int(target),
                    text="✅ +994 nömrələrinə icazəniz Mini App admini tərəfindən təsdiqləndi.",
                )
            except TelegramError:
                pass
        return _miniapp_cors(web.json_response({
            "ok": True, "user_id": target, "approved": action == "az_approve",
        }))
    if action in ("ban","unban") and target:
        (ban_user if action=="ban" else unban_user)(target)
        return _miniapp_cors(web.json_response({"ok":True}))
    if action=="balance" and target:
        try: amount=float(body.get("amount",0))
        except: return _miniapp_cors(web.json_response({"error":"invalid_amount"},status=400))
        new_balance=await update_db_balance(target,amount)
        return _miniapp_cors(web.json_response({"ok":True,"balance":format_balance(new_balance)}))
    return _miniapp_cors(web.json_response({"error":"bad_action"},status=400))


async def post_init(application):
    await asyncio.to_thread(number_archive.import_legacy, load_range_db())
    application.bot_data["number_archive_task"] = asyncio.create_task(number_archive.run())
    for _ in range(20):
        asyncio.create_task(worker())
    asyncio.create_task(monitor_loop(application))
    asyncio.create_task(fake_otp_loop(application))
    asyncio.create_task(country_availability_loop(application))


def register_handlers(app):
    register_whatsapp_handlers(app, is_admin)
    register_admin_test_tools(app, is_admin, admin_main_keyboard)
    app.add_handler(CommandHandler("numbers_txt", numbers_txt_command))
    app.add_handler(CommandHandler("all_numbers_txt", all_numbers_txt_command))
    app.add_handler(CommandHandler("numbers_status", numbers_status_command))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("az_access", az_access_command))
    app.add_handler(CommandHandler("az_request", az_request_command))
    app.add_handler(CommandHandler("az_approve", az_approve_command))
    app.add_handler(CommandHandler("az_revoke", az_revoke_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("get1number", get1number_command))
    app.add_handler(CommandHandler("searchotp", searchotp_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command_slash))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))


async def run_combined_server():
    """Start the bot and HTTP API together, using webhook on public services.

    A worker/local process without an external URL uses polling instead.
    Only one running instance should consume Telegram updates.
    """
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not configured in the environment.")
    if not API_KEY:
        print("[configuration] AZE_SMS_API_KEY is missing; provider features are unavailable.")

    app = ApplicationBuilder().token(BOT_TOKEN).concurrent_updates(True).build()
    register_handlers(app)
    app.add_error_handler(premium_keyboard_error_handler)

    external_url = (os.environ.get("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
    webhook_url = (os.environ.get("WEBHOOK_URL") or "").strip() or (
        f"{external_url}/webhook" if external_url else ""
    )
    if webhook_url and not webhook_url.startswith("https://"):
        raise RuntimeError("WEBHOOK_URL must be a public HTTPS URL.")

    # Telegram supplies this secret as an HTTP header for real webhook updates.
    webhook_secret = hashlib.sha256(
        ("telegram-webhook:" + BOT_TOKEN).encode("utf-8")
    ).hexdigest()

    async def telegram_webhook(request):
        if not webhook_url:
            return web.Response(status=404)
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(supplied, webhook_secret):
            return web.Response(status=403)
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                return web.Response(status=400)
            update = Update.de_json(payload, app.bot)
            if update is None:
                return web.Response(status=400)
            await app.process_update(update)
            return web.Response(text="OK")
        except (ValueError, TypeError):
            return web.Response(status=400)
        except Exception as exc:
            print(f"[webhook] Telegram update failed: {type(exc).__name__}")
            return web.Response(status=500)

    async def health(request):
        return web.json_response({
            "ok": True,
            "service": "aze-sms-panel",
            "telegram_mode": "webhook" if webhook_url else "polling",
            "provider_configured": bool(API_KEY),
        })

    server = web.Application(client_max_size=1024 * 1024)
    server["telegram_bot"] = app.bot
    server.router.add_post("/webhook", telegram_webhook)
    server.router.add_route("*", "/api/get-number", miniapp_get_number_api)
    server.router.add_route("GET", "/api/dashboard", miniapp_dashboard)
    server.router.add_route("OPTIONS", "/api/dashboard", miniapp_dashboard)
    server.router.add_route("*", "/api/orders", miniapp_orders_api)
    server.router.add_route("*", "/api/test-sms", miniapp_test_sms)
    server.router.add_route("*", "/api/admin", miniapp_admin_api)
    server.router.add_route("*", "/api/services", miniapp_services_api)
    server.router.add_route("*", "/api/countries", miniapp_countries_api)
    server.router.add_route("*", "/api/az-access", miniapp_az_access_api)
    server.router.add_route("*", "/api/incoming-sms", miniapp_incoming_sms_api)
    server.router.add_get("/health", health)

    runner = web.AppRunner(server)
    await app.initialize()
    server["bot_username"] = (await app.bot.get_me()).username
    await app.start()
    await post_init(app)
    polling_started = False
    try:
        await runner.setup()
        port = int(os.environ.get("PORT", "8080"))
        await web.TCPSite(runner, "0.0.0.0", port).start()
        if webhook_url:
            await app.bot.set_webhook(
                url=webhook_url,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=False,
                secret_token=webhook_secret,
            )
            print(f"[startup] Webhook active; listening on port {port}")
        else:
            await app.bot.delete_webhook(drop_pending_updates=False)
            await app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=False,
            )
            polling_started = True
            print(f"[startup] Polling active; HTTP health on port {port}")
        await asyncio.Event().wait()
    finally:
        range_collector.stop_all()
        archive_task = app.bot_data.get("number_archive_task")
        if archive_task:
            archive_task.cancel()
            await asyncio.gather(archive_task, return_exceptions=True)
        if polling_started:
            await app.updater.stop()
        await runner.cleanup()
        await app.stop()
        await app.shutdown()

def main():
    asyncio.run(run_combined_server())

# ==================== MİNİ APP GƏLƏN SMS VƏ XİDMƏTLƏR API ====================
miniapp_incoming_sms = {}  # { uid: [ {service, number, otp, message, time}, ... ] }

async def miniapp_services_api(request):
    if request.method == "OPTIONS":
        return _miniapp_cors(web.Response(status=204))
    tg_user, err = _miniapp_auth(request)
    if not tg_user:
        return _miniapp_cors(web.json_response({"error": "unauthorized", "reason": err}, status=401))
    
    uid = int(tg_user["id"])
    if is_user_banned(uid):
        return _miniapp_cors(web.json_response({"error": "banned"}, status=403))
    services = await fetch_services_cached()
    return _miniapp_cors(web.json_response({
        "services": services,
        "az_available": any(
            is_az_range(item)
            for ranges in services.values() for item in ranges
        ),
        "az_approved": az_range_allowed(uid),
        "az_catalog": az_range_catalog(services),
    }))


async def miniapp_countries_api(request):
    """Searchable world-country catalogue; upstream listing metadata only."""
    if request.method == "OPTIONS":
        return _miniapp_cors(web.Response(status=204))
    tg_user, err = _miniapp_auth(request)
    if not tg_user:
        return _miniapp_cors(web.json_response({"error": "unauthorized", "reason": err}, status=401))
    uid = int(tg_user["id"])
    if is_user_banned(uid):
        return _miniapp_cors(web.json_response({"error": "banned"}, status=403))
    services = await fetch_services_cached()
    countries = build_all_country_rows(services)
    iso = str(request.query.get("iso", "")).upper().strip()
    if iso:
        match = next((c for c in countries if c["iso"] == iso), None)
        if not match:
            return _miniapp_cors(web.json_response({"error": "unknown_country"}, status=404))
        return _miniapp_cors(web.json_response({
            "country": match, "az_approved": az_range_allowed(uid),
        }))
    return _miniapp_cors(web.json_response({
        "countries": [{
            "iso": c["iso"], "name": c["name"], "flag": c["flag"],
            "prefix": c["prefix"], "count": len(c["ranges"]),
            "is_shared": c["is_shared"],
        } for c in countries],
        "total": len(countries),
        "available_countries": sum(bool(c["ranges"]) for c in countries),
        "az_approved": az_range_allowed(uid),
    }))


async def miniapp_az_access_api(request):
    """Request +994 approval through authenticated Telegram initData."""
    if request.method == "OPTIONS":
        return _miniapp_cors(web.Response(status=204))
    tg_user, err = _miniapp_auth(request)
    if not tg_user:
        return _miniapp_cors(web.json_response({"error": "unauthorized", "reason": err}, status=401))
    uid = int(tg_user["id"])
    if is_user_banned(uid):
        return _miniapp_cors(web.json_response({"error": "banned"}, status=403))
    if request.method == "GET":
        return _miniapp_cors(web.json_response({
            "approved": az_range_allowed(uid), "is_admin": is_admin(uid),
        }))
    if request.method != "POST":
        return _miniapp_cors(web.json_response({"error": "method_not_allowed"}, status=405))
    if az_range_allowed(uid):
        return _miniapp_cors(web.json_response({
            "ok": True, "approved": True, "message": "Artıq icazəniz var.",
        }))
    now = time.monotonic()
    if now - _az_request_times.get(uid, 0) < 300:
        return _miniapp_cors(web.json_response({
            "error": "rate_limited", "message": "Təkrar sorğu üçün 5 dəqiqə gözləyin.",
        }, status=429))
    sent = 0
    for admin_id in ADMINS:
        try:
            await request.app["telegram_bot"].send_message(
                chat_id=admin_id,
                text=(f"🇦🇿 +994 Mini App icazə sorğusu: Telegram ID {uid}\n"
                      f"İcazə: /az_approve {uid}\nLəğv: /az_revoke {uid}"),
            )
            sent += 1
        except TelegramError:
            continue
    if not sent:
        return _miniapp_cors(web.json_response({
            "error": "delivery_failed", "message": "Adminə mesaj göndərilə bilmədi.",
        }, status=503))
    _az_request_times[uid] = now
    return _miniapp_cors(web.json_response({
        "ok": True, "approved": False, "message": "İcazə sorğunuz adminə göndərildi.",
    }))


async def miniapp_incoming_sms_api(request):
    if request.method == "OPTIONS":
        return _miniapp_cors(web.Response(status=204))
    tg_user, err = _miniapp_auth(request)
    if not tg_user:
        return _miniapp_cors(web.json_response({"error": "unauthorized", "reason": err}, status=401))
    
    uid = int(tg_user["id"])
    user_sms_list = miniapp_incoming_sms.get(uid, [])
    return _miniapp_cors(web.json_response({"sms_list": user_sms_list}))


async def miniapp_get_number_api(request):
    if request.method == "OPTIONS":
        return _miniapp_cors(web.Response(status=204))
    
    tg_user, err = _miniapp_auth(request)
    if not tg_user:
        return _miniapp_cors(web.json_response({"error": "unauthorized", "reason": err}, status=401))
    
    uid = int(tg_user["id"])
    if is_user_banned(uid):
        return _miniapp_cors(web.json_response({"error": "banned"}, status=403))
    
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("invalid body")
        service = str(body.get("service", "")).strip().lower()
    except (ValueError, TypeError):
        return _miniapp_cors(web.json_response({"error": "invalid_request"}, status=400))

    # +994 operator catalogue supports 210/211 subrange selections.
    # Catalogue entries are not claims that the upstream has live numbers.
    selected_rid = str(body.get("range", "")).strip()
    requested_country = str(body.get("country", "")).strip()
    if selected_rid:
        if not selected_rid.isdecimal() or len(selected_rid) > 10:
            return _miniapp_cors(web.json_response({"error": "invalid_range"}, status=400))
        if is_az_range(selected_rid) and service == "az":
            if not az_range_allowed(uid):
                return _miniapp_cors(web.json_response({
                    "error": "admin_approval_required", "message": AZ_ACCESS_DENIED,
                }, status=403))
            if (requested_country != "994" or not az_catalog_lookup(
                    rid=selected_rid, services=await fetch_services_cached())):
                return _miniapp_cors(web.json_response({"error": "invalid_catalog_range"}, status=400))
        else:
            services = await fetch_services_cached()
            actual_ranges = {
                re.sub(r"\D", "", str(item))
                for item in services.get(service, [])
            }
            if selected_rid not in actual_ranges:
                return _miniapp_cors(web.json_response({"error": "range_unavailable"}, status=404))
            country_iso = str(body.get("country_iso", "")).upper().strip()
            if country_iso:
                selected_country = next(
                    (c for c in build_all_country_rows({service: [selected_rid]})
                     if c["iso"] == country_iso), None,
                )
                if not selected_country or not selected_country["ranges"]:
                    return _miniapp_cors(web.json_response({"error": "country_mismatch"}, status=400))
            if is_az_range(selected_rid) and not az_range_allowed(uid):
                return _miniapp_cors(web.json_response({
                    "error": "admin_approval_required", "message": AZ_ACCESS_DENIED,
                }, status=403))
        rid = selected_rid
    else:
        # Ordinary services use ranges actually advertised by the upstream API.
        services = await fetch_services_cached()
        ranges = services.get(service, [])
        if not ranges:
            return _miniapp_cors(web.json_response({"error": "service_unavailable"}, status=404))
        valid_ranges = sorted(set(
            re.sub(r"[^0-9]", "", str(item))
            for item in ranges
            if re.sub(r"[^0-9]", "", str(item))
        ))
        if requested_country == "994":
            valid_ranges = [rid for rid in valid_ranges if is_az_range(rid)]
        else:
            valid_ranges = sorted(valid_ranges, key=lambda rid: (is_az_range(rid), rid))
        if not valid_ranges:
            return _miniapp_cors(web.json_response({"error": "range_unavailable"}, status=404))
        rid = valid_ranges[0]
        if is_az_range(rid) and not az_range_allowed(uid):
            return _miniapp_cors(web.json_response({
                "error": "admin_approval_required", "message": AZ_ACCESS_DENIED,
            }, status=403))

    num, country = await get_number_from_api(rid, requester_id=uid)
    if not num:
        return _miniapp_cors(web.json_response({"success": False, "message": "Şu anda bu serviste uygun numara bulunamadı."}, status=400))

    clean_num = normalize_number(num)
    add_number_taken(uid, 1)
    range_display = rid + "XXX"
    
    # Aktif numaralara ekliyoruz
    active_numbers[clean_num] = {
        "uid": uid,
        "range": range_display,
        "timestamp": datetime.now(),
    }
    save_number_range_info(uid, clean_num, range_display)
    
    # Mini App sipariş listesine ekliyoruz
    order = {
        "id": f"ord_{int(time.time())}",
        "label": service.upper(),
        "number_masked": "+" + mask_number(clean_num),
        "full_number": num,
        "range": range_display,
        "status": "Aktiv",
        "created_at": time.time(),
        "remaining_seconds": 3600
    }
    miniapp_orders.setdefault(uid, []).append(order)

    return _miniapp_cors(web.json_response({
        "success": True,
        "number": num,
        "masked_number": "+" + mask_number(clean_num),
        "service": service.upper(),
        "range": range_display
    }))



if __name__ == "__main__":
    main()
