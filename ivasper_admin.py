"""Private admin-only Telegram viewer for independent IVASPER number inventory.

No IVASMS numbers, pricing, allocations, OTPs, archives, or provider calls.
"""
import html
import re
from collections import Counter

ADMIN_LABEL = "🧰 IVASPER NƏZARƏT"
CALLBACK_PATTERN = r"^ivasper_admin:(?:summary|services|archive|country:[0-9]{1,3}:[0-9]{1,4}|close)$"


def admin_allowed(user, chat, is_admin, is_banned):
    if not user or not chat or getattr(chat, "type", None) != "private":
        return False
    try:
        uid = int(user.id)
        return bool(is_admin(uid)) and not bool(is_banned(uid))
    except (TypeError, ValueError, AttributeError):
        return False


def panel_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 IVASPER nömrələr", callback_data="ivasper_admin:archive")],
        [InlineKeyboardButton("📡 Xidmət statistikası", callback_data="ivasper_admin:services")],
        [InlineKeyboardButton("🔄 Yenilə", callback_data="ivasper_admin:summary")],
        [InlineKeyboardButton("✖️ Bağla", callback_data="ivasper_admin:close")],
    ])


def render_inventory(mode, inventory):
    """Display no more than 12 authorized numbers on one Telegram page."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    status = str(inventory.get("status") or "not_configured")
    numbers = inventory.get("numbers")
    numbers = numbers if isinstance(numbers, list) else []
    if status != "ok":
        message = html.escape(str(inventory.get("message") or "IVASPER mənbəyi əlçatan deyil.")[:300])
        return ("🧰 <b>IVASPER — AYRICA NÖMRƏ SİYAHISI</b>\n\n"
                f"⚠️ {message}\n\n"
                "IVASMS nömrələrindən heç nə götürülmür.", panel_keyboard())

    country_names = sorted({str(n.get("country") or "Naməlum") for n in numbers
                            if isinstance(n, dict)})
    if mode.startswith("country:"):
        _, index, page = mode.split(":")
        index, page = int(index), int(page)
        if index >= len(country_names):
            return "Ölkə artıq siyahıda yoxdur.", panel_keyboard()
        country = country_names[index]
        entries = [item for item in numbers if item.get("country") == country]
        pages = max(1, (len(entries) + 11) // 12)
        page = min(page, pages - 1)
        selected = entries[page * 12:page * 12 + 12]
        lines = [f"🌍 <b>{html.escape(country)}</b> — IVASPER",
                 f"📱 Nömrə sayı: {len(entries)}",
                 f"📄 Səhifə {page + 1}/{pages}", ""]
        lines.extend(
            f"• <code>{html.escape(str(item['number']))}</code> — "
            f"{html.escape(str(item.get('service') or 'IVASPER'))}"
            for item in selected
        )
        rows = []
        nav = []
        if page:
            nav.append(InlineKeyboardButton("◀", callback_data=f"ivasper_admin:country:{index}:{page-1}"))
        if page < pages - 1:
            nav.append(InlineKeyboardButton("▶", callback_data=f"ivasper_admin:country:{index}:{page+1}"))
        if nav:
            rows.append(nav)
        rows.append([InlineKeyboardButton("🔙 Ölkələr", callback_data="ivasper_admin:archive")])
        return "\n".join(lines), InlineKeyboardMarkup(rows)
    if mode == "archive":
        rows = []
        for index, country in enumerate(country_names[:75]):
            count = sum(item.get("country") == country for item in numbers)
            rows.append([InlineKeyboardButton(
                f"{country[:30]} · {count} nömrə", callback_data=f"ivasper_admin:country:{index}:0")])
        rows.append([InlineKeyboardButton("🔙 Geri", callback_data="ivasper_admin:summary")])
        return ("📱 <b>IVASPER — ÖLKƏLƏR</b>\n"
                "Yalnız müstəqil IVASPER mənbəyinin nömrələri göstərilir.\n"
                "Ölkəni seçin:", InlineKeyboardMarkup(rows))
    if mode == "services":
        counts = Counter(str(n.get("service") or "IVASPER") for n in numbers)
        lines = ["📡 <b>IVASPER — XİDMƏTLƏR</b>", ""]
        lines.extend(f"• {html.escape(name)}: {count} nömrə"
                     for name, count in counts.most_common(30))
        if not counts:
            lines.append("Hələ nömrə yoxdur.")
        return "\n".join(lines), panel_keyboard()

    return ("🧰 <b>IVASPER — AYRICA NÖMRƏ SİYAHISI</b>\n\n"
            f"📱 Nömrələr: <b>{len(numbers)}</b>\n"
            f"🌍 Ölkələr: <b>{len(country_names)}</b>\n\n"
            "IVASMS nömrə bazası, arxivi, balansı və aktiv sifarişləri dəyişdirilmir.",
            panel_keyboard())


def register_ivasper_admin_handlers(app, is_admin, is_banned, load_inventory):
    from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters
    from telegram.error import BadRequest

    async def render(mode):
        try:
            stock = await load_inventory()
        except Exception:
            stock = {"status": "source_unavailable",
                     "message": "IVASPER bağlantısı mümkün olmadı.", "numbers": []}
        return render_inventory(mode, stock)

    async def open_panel(update, context):
        if not admin_allowed(update.effective_user, update.effective_chat,
                             is_admin, is_banned):
            return
        message, keyboard = await render("summary")
        await update.effective_message.reply_text(
            message, parse_mode="HTML", reply_markup=keyboard)

    async def callback(update, context):
        query = update.callback_query
        if not query:
            return
        if not admin_allowed(update.effective_user, update.effective_chat,
                             is_admin, is_banned):
            await query.answer("⛔ İcazə yoxdur.", show_alert=True)
            return
        await query.answer()
        mode = query.data[len("ivasper_admin:"):]
        if mode == "close":
            await query.edit_message_text("IVASPER siyahısı bağlandı.")
            return
        message, keyboard = await render(mode)
        try:
            await query.edit_message_text(
                message, parse_mode="HTML", reply_markup=keyboard)
        except BadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                raise

    app.add_handler(CommandHandler("ivasper", open_panel))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.Regex(r"^🧰 IVASPER NƏZARƏT$"), open_panel))
    app.add_handler(CallbackQueryHandler(callback, pattern=CALLBACK_PATTERN))
