"""Restricted admin-only diagnostics for the IVASMS Telegram bot.

No bombing, registration-code requests, arbitrary recipients, or bulk sending.
This UI is visible only to configured admins in private chats.
"""
import os

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

from whatsapp_safe import (
    WhatsAppConfig,
    WhatsAppConfigError,
    get_whatsapp_smoke_test,
)

ADMIN_TEST_LABEL = "🧪 TEST ALƏTLƏRİ"
CALLBACK_PREFIX = "admin_sandbox_"

def admin_allowed(user, chat, is_admin):
    """Always enforce permission server-side, not just by hiding a button."""
    return bool(user and chat and chat.type == "private" and is_admin(user.id))

def test_tools_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 API konfiqurasiyası", callback_data="admin_sandbox_status")],
        [InlineKeyboardButton("📱 WhatsApp-a 1 test mesajı", callback_data="admin_sandbox_wa")],
        [InlineKeyboardButton("🔙 Admin panelinə qayıt", callback_data="admin_sandbox_back")],
    ])

def status_text():
    cfg = WhatsAppConfig.from_env()
    try:
        cfg.validate()
        wa = "✅ WhatsApp test parametrləri təyin olunub (real bağlantı yoxlanmayıb). " + cfg.masked_recipient()
    except WhatsAppConfigError:
        wa = "⚠️ WhatsApp test parametrləri tam deyil."
    sms = bool((os.getenv("AZE_SMS_API_KEY") or os.getenv("VOLTX_API_KEY") or "").strip())
    return (
        "🧪 ADMIN TEST ALƏTLƏRİ\n\n"
        f"📱 {wa}\n"
        f"📡 SMS API açarı: {'✅ təyin olunub' if sms else '⚠️ yoxdur'} "
        "(API sorğusu göndərilmədi).\n\n"
        "Yalnız əvvəlcədən razılıq verilmiş test nömrəsinə bir sabit WhatsApp mesajı göndərmək olar. "
        "Təkrar göndərişlərə 5 dəqiqəlik limit tətbiq edilir. "
        "OTP, qeydiyyat kodu və kütləvi mesaj göndərilmir."
    )

async def whatsapp_once_message():
    cfg = WhatsAppConfig.from_env()
    try:
        sent, remaining = await get_whatsapp_smoke_test().run(cfg)
    except WhatsAppConfigError:
        return "⚠️ WhatsApp Cloud API məlumatları natamamdır. Render Environment ayarlarını yoxlayın."
    except httpx.HTTPStatusError as err:
        return f"❌ WhatsApp Cloud API mesajı qəbul etmədi (HTTP {err.response.status_code})."
    except httpx.RequestError:
        return "❌ WhatsApp Cloud API ilə şəbəkə əlaqəsi alınmadı."
    if sent:
        return "✅ Bir test mesajı API tərəfindən qəbul olundu. Çatdırılma ayrıca yoxlanmalıdır."
    return f"⏳ Növbəti sınaq üçün təxminən {remaining} saniyə qalır."

def register_admin_test_tools(app, is_admin, admin_main_keyboard):
    """Install BEFORE the generic text/callback handlers in register_handlers()."""
    async def open_panel(update, context):
        if not admin_allowed(update.effective_user, update.effective_chat, is_admin):
            return
        await update.effective_message.reply_text(status_text(), reply_markup=test_tools_keyboard())

    async def on_callback(update, context):
        query = update.callback_query
        if not query:
            return
        if not admin_allowed(update.effective_user, update.effective_chat, is_admin):
            await query.answer("⛔ İcazə yoxdur.", show_alert=True)
            return
        await query.answer()
        if query.data == "admin_sandbox_back":
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text("⚙️ Admin paneli", reply_markup=admin_main_keyboard())
        elif query.data == "admin_sandbox_status":
            await query.edit_message_text(status_text(), reply_markup=test_tools_keyboard())
        elif query.data == "admin_sandbox_wa":
            result = await whatsapp_once_message()
            await query.edit_message_text(result + "\n\n" + status_text(), reply_markup=test_tools_keyboard())

    app.add_handler(CommandHandler("test_tools", open_panel))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.Regex(r"^🧪 TEST ALƏTLƏRİ$"), open_panel
    ))
    app.add_handler(CallbackQueryHandler(on_callback, pattern=r"^admin_sandbox_(status|wa|back)$"))
