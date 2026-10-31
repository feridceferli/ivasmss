"""Admin-only, read-only diagnostics inspired by Ivasmsper's inventory/status UI.

Uses the *existing* IVASMS provider and archive. It never starts Ivasmsper's
workers, imports their embedded secrets, forwards OTPs or exports phone records.
"""
import asyncio
import html
import re
from collections import Counter
from ivasper_web import archive_country_page

ADMIN_LABEL = "🧰 IVASPER NƏZARƏT"
CALLBACK_PATTERN = r"^ivasper_admin:(?:summary|archive|services|close|archive_page:[0-9]{1,3}|country:[0-9]{1,3}:[0-9]{1,4})$"
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



def archive_country_keyboard(countries, list_page=0):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    max_pages = max(1, (len(countries) + 9) // 10)
    page = min(max(0, int(list_page)), max_pages - 1)
    rows = []
    for idx in range(page * 10, min(len(countries), (page + 1) * 10)):
        item = countries[idx]
        label = str(item["country"])[:30] + " · " + str(item["my_count"]) + " mənim"
        rows.append([InlineKeyboardButton(
            label, callback_data=f"ivasper_admin:country:{idx}:0")])
    navigation = []
    if page:
        navigation.append(InlineKeyboardButton(
            "◀ Ölkələr", callback_data=f"ivasper_admin:archive_page:{page - 1}"))
    if page < max_pages - 1:
        navigation.append(InlineKeyboardButton(
            "Ölkələr ▶", callback_data=f"ivasper_admin:archive_page:{page + 1}"))
    if navigation:
        rows.append(navigation)
    rows.append([InlineKeyboardButton("🔙 Əsas panel", callback_data="ivasper_admin:summary")])
    return InlineKeyboardMarkup(rows)


def archive_detail_text(archived, owner_id, country_index, page):
    """One country's *owner-only* allocated numbers, never other users' phones."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    countries, _ = archive_country_page(archived, owner_id)
    if not countries or country_index not in range(len(countries)):
        return ("Arxivdə ölkə tapılmadı.", archive_country_keyboard(countries))
    country = countries[country_index]["country"]
    _, selected = archive_country_page(
        archived, owner_id, country=country, page=page, page_size=12)
    lines = [
        "📦 <b>IVASPER — ÖLKƏ ÜZRƏ ARXİV</b>",
        f"🌍 <b>{html.escape(country)}</b>",
        f"📊 Ümumi arxiv qeydi: <b>{selected['total_count']}</b>",
        f"📱 Öz nömrələrim: <b>{selected['my_count']}</b>",
        "",
    ]
    if selected["entries"]:
        lines.extend(f"• <code>{html.escape(item['number'])}</code> "
                     f"— {html.escape(item['range'])}"
                     for item in selected["entries"])
    else:
        lines.append("Bu ölkədə sizə ayrılmış arxiv nömrəsi yoxdur.")
    lines.extend(["", "ℹ️ Arxivdəki nömrə hazırda aktiv olmaya bilər.",
                  "🔒 Başqa istifadəçilərin tam nömrələri göstərilmir."])
    rows = []
    nav = []
    if selected["page"] > 0:
        nav.append(InlineKeyboardButton(
            "◀", callback_data=f"ivasper_admin:country:{country_index}:{selected['page'] - 1}"))
    if selected["page"] + 1 < selected["pages"]:
        nav.append(InlineKeyboardButton(
            "▶", callback_data=f"ivasper_admin:country:{country_index}:{selected['page'] + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(
        "🔙 Ölkələr", callback_data=f"ivasper_admin:archive_page:{country_index // 10}")])
    rows.append([InlineKeyboardButton(
        "🏠 Admin paneli", callback_data="ivasper_admin:summary")])
    return "\\n".join(lines), InlineKeyboardMarkup(rows)


def register_ivasper_admin_handlers(app, is_admin, is_banned, load_archive,
                                   fetch_services, get_monitor):
    """Install before the generic Telegram message and callback handlers."""
    from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters
    from telegram.error import BadRequest

    async def render(mode, uid):
        try:
            archive = load_archive()
        except (OSError, ValueError, TypeError):
            archive = {}
        if mode.startswith("country:"):
            _, index, page = mode.split(":")
            return archive_detail_text(archive, uid, int(index), int(page))
        if mode == "archive" or mode.startswith("archive_page:"):
            countries, _ = archive_country_page(archive, uid)
            list_page = int(mode.split(":")[1]) if ":" in mode else 0
            report = build_report("archive", {}, archive, {})
            return (report + "\\n\\n🌍 Ölkəyə toxunaraq öz tam nömrələrinizi görün.",
                    archive_country_keyboard(countries, list_page))
        try:
            services = await asyncio.wait_for(fetch_services(), timeout=8)
        except (asyncio.TimeoutError, OSError, ValueError, RuntimeError):
            services = {}
        try:
            monitor = get_monitor()
        except (TypeError, ValueError, RuntimeError):
            monitor = {}
        return build_report(mode, services, archive, monitor), panel_keyboard()

    async def open_panel(update, context):
        if not admin_allowed(update.effective_user, update.effective_chat,
                             is_admin, is_banned):
            return
        message, keyboard = await render("summary", update.effective_user.id)
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
            await query.edit_message_text("IVASPER admin paneli bağlandı.")
            return
        message, keyboard = await render(mode, update.effective_user.id)
        try:
            await query.edit_message_text(
                message, parse_mode="HTML", reply_markup=keyboard)
        except BadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                raise

    app.add_handler(CommandHandler("ivasper", open_panel))
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.Regex(r"^🧰 IVASPER NƏZARƏT$"),
        open_panel,
    ))
    app.add_handler(CallbackQueryHandler(callback, pattern=CALLBACK_PATTERN))
