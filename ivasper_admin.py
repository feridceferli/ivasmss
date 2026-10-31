"""Admin-only, read-only diagnostics inspired by Ivasmsper's inventory/status UI.

Uses the *existing* IVASMS provider and archive. It never starts Ivasmsper's
workers, imports their embedded secrets, forwards OTPs or exports phone records.
"""
import asyncio
import html
import re
from collections import Counter

ADMIN_LABEL = "🧰 IVASPER NƏZARƏT"
CALLBACK_PATTERN = r"^ivasper_admin:(summary|archive|services|close)$"
SOURCE_REPO = "shagunallrepo/Ivasmsper"


def admin_allowed(user, chat, is_admin, is_banned):
    """Both menu actions and callbacks enforce private-chat admin authorization."""
    if not user or not chat or getattr(chat, "type", None) != "private":
        return False
    try:
        uid = int(user.id)
        return bool(is_admin(uid)) and not bool(is_banned(uid))
    except (TypeError, ValueError, AttributeError):
        return False


def _safe_label(value, limit=45):
    value = re.sub(r"[\x00-\x1f\x7f]", " ", str(value or "")).strip()
    return html.escape(value[:limit], quote=False) or "Naməlum"


def archive_summary(archive):
    """Group local archived records without disclosing numbers or user IDs."""
    if not isinstance(archive, dict):
        return 0, []
    countries = Counter()
    count = 0
    for record in archive.values():
        if not isinstance(record, dict):
            continue
        count += 1
        countries[_safe_label(record.get("country"), 45)] += 1
    return count, sorted(countries.items(), key=lambda row: (-row[1], row[0]))


def service_summary(services):
    """Count configured range entries, not available/working phone numbers."""
    if not isinstance(services, dict):
        return 0, 0, []
    rows = []
    for name, ranges in services.items():
        if not isinstance(ranges, list):
            continue
        rows.append((_safe_label(name, 32), len(ranges)))
    rows.sort(key=lambda row: (-row[1], row[0]))
    return len(rows), sum(count for _, count in rows), rows


def build_report(mode, services, archive, monitor):
    """All reports contain aggregates only. No OTP, phone, token or raw errors."""
    total, countries = archive_summary(archive)
    service_count, range_count, service_rows = service_summary(services)
    monitor = monitor if isinstance(monitor, dict) else {}
    state = monitor.get("state")
    state = state if state in {"ok", "checking", "starting", "error", "failed"} else "naməlum"
    code = monitor.get("http_status")
    code_label = str(code) if isinstance(code, int) and 100 <= code <= 599 else "—"

    if mode == "archive":
        entries = [f"• {name}: {count}" for name, count in countries[:15]]
        return ("📦 <b>IVASPER — YADDA SAXLANAN NÖMRƏLƏR</b>\n"
                f"Arxiv qeydləri: <b>{total}</b>\n"
                f"Ölkə sayı: <b>{len(countries)}</b>\n\n" +
                ("\n".join(entries) if entries else "Arxivdə qeyd yoxdur.") +
                "\n\nℹ️ Arxiv sayı aktiv nömrə ehtiyatını göstərmir.")
    if mode == "services":
        entries = [f"• {name}: {count} range" for name, count in service_rows[:15]]
        return ("📡 <b>IVASPER — XİDMƏT KATALOQU</b>\n"
                f"Xidmətlər: <b>{service_count}</b>\n"
                f"Range qeydləri: <b>{range_count}</b>\n\n" +
                ("\n".join(entries) if entries else "API kataloqunda xidmət görünmür.") +
                "\n\nℹ️ Range qeydi nömrənin aktiv olmasını təsdiqləmir.")
    return ("🧰 <b>IVASPER — ADMIN NƏZARƏTİ</b>\n\n"
            f"📡 Mövcud API monitoru: <b>{html.escape(state)}</b>\n"
            f"🌐 Son HTTP statusu: <b>{code_label}</b>\n"
            f"🧩 Xidmətlər: <b>{service_count}</b>\n"
            f"📶 Range qeydləri: <b>{range_count}</b>\n"
            f"📦 Arxivdə saxlanan nömrə qeydləri: <b>{total}</b>\n\n"
            "🔐 Yalnız admin / şəxsi çat.\n"
            "Xarici repodakı tokenlər, OTP izləyiciləri və kütləvi göndərişlər qoşulmayıb.")


def panel_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Status", callback_data="ivasper_admin:summary")],
        [InlineKeyboardButton("📦 Ölkələr üzrə arxiv", callback_data="ivasper_admin:archive")],
        [InlineKeyboardButton("📡 Servis/range statistikası", callback_data="ivasper_admin:services")],
        [InlineKeyboardButton("✖️ Bağla", callback_data="ivasper_admin:close")],
    ])


def register_ivasper_admin_handlers(app, is_admin, is_banned, load_archive,
                                   fetch_services, get_monitor):
    """Install before the generic Telegram message and callback handlers."""
    from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters
    from telegram.error import BadRequest

    async def render(mode):
        try:
            archive = load_archive()
        except (OSError, ValueError, TypeError):
            archive = {}
        try:
            services = await asyncio.wait_for(fetch_services(), timeout=8)
        except (asyncio.TimeoutError, OSError, ValueError, RuntimeError):
            services = {}
        try:
            monitor = get_monitor()
        except (TypeError, ValueError, RuntimeError):
            monitor = {}
        return build_report(mode, services, archive, monitor)

    async def open_panel(update, context):
        if not admin_allowed(update.effective_user, update.effective_chat,
                             is_admin, is_banned):
            return
        message = await render("summary")
        await update.effective_message.reply_text(
            message, parse_mode="HTML", reply_markup=panel_keyboard())

    async def callback(update, context):
        query = update.callback_query
        if not query:
            return
        if not admin_allowed(update.effective_user, update.effective_chat,
                             is_admin, is_banned):
            await query.answer("⛔ İcazə yoxdur.", show_alert=True)
            return
        await query.answer()
        mode = query.data.rsplit(":", 1)[-1]
        if mode == "close":
            await query.edit_message_text("IVASPER admin paneli bağlandı.")
            return
        message = await render(mode)
        try:
            await query.edit_message_text(
                message, parse_mode="HTML", reply_markup=panel_keyboard())
        except BadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                raise

    app.add_handler(CommandHandler("ivasper", open_panel))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.Regex(r"^🧰 IVASPER NƏZARƏT$"),
        open_panel,
    ))
    app.add_handler(CallbackQueryHandler(callback, pattern=CALLBACK_PATTERN))
