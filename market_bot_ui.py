"""Telegram menus for private service publication and manual bank transfer receipts."""
import asyncio
import html
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ApplicationHandlerStop
from manual_topups import TopupError, parse_amount_cents


class MarketBotUI:
    def __init__(self, *, catalog, topups, backup, is_admin, is_banned,
                 services, user, load_users, save_users, quote, admins):
        self.catalog = catalog
        self.topups = topups
        self.backup = backup
        self.is_admin = is_admin
        self.is_banned = is_banned
        self.services = services
        self.user = user
        self.load_users = load_users
        self.save_users = save_users
        self.quote = quote
        self.admins = admins
        self._review_lock = asyncio.Lock()

    def register(self, app):
        app.add_handler(CommandHandler("topup", self.topup_command))
        app.add_handler(CommandHandler("setcard", self.setcard_command))
        app.add_handler(CommandHandler("setcontact", self.setcontact_command))
        app.add_handler(CommandHandler("topups", self.topups_command))
        app.add_handler(CommandHandler("market_admin", self.admin_services))
        app.add_handler(CallbackQueryHandler(
            self.callback, pattern=r"^(?:market:(?:page|service|rp|range):\d+|topup:review:(?:yes|no):[0-9a-f]{16})$"))
        # Group -1 can stop only the active top-up state, leaving all other
        # text messages for the original bot handlers in group 0.
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,
                                       self.topup_amount_text), group=-1)
        app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL,
                                       self.topup_receipt), group=-1)

    @staticmethod
    def private(update):
        return bool(update.effective_chat and update.effective_chat.type == "private")

    async def topup_command(self, update, context):
        uid = update.effective_user.id
        if not self.private(update) or self.is_banned(uid):
            await update.effective_message.reply_text("🔒 Bu funksiya şəxsi çatda açılır.")
            return
        details = self.topups.details()
        card = details["card"]
        if not card:
            await update.effective_message.reply_text(
                "💳 Kart hələ əlavə edilməyib. Balans üçün adminlə əlaqə saxlayın.")
            return
        context.user_data["manual_topup_stage"] = "amount"
        context.user_data.pop("manual_topup_cents", None)
        contact = details["contact"]
        buttons = ([[InlineKeyboardButton("💬 Adminlə əlaqə", url=contact)]]
                   if contact else [])
        await update.effective_message.reply_text(
            "💳 <b>BALANS ARTIRMA</b>\n\n"
            "1. Bu karta bank tətbiqinizdən köçürmə edin:\n"
            f"<code>{html.escape(card)}</code>\n\n"
            "2. Köçürdüyünüz AZN məbləğini yazın (məsələn: 5.00).\n"
            "3. Bankın ödəniş çekini şəkil və ya PDF kimi bota göndərin.\n"
            "4. Admin yoxladıqdan sonra balans artırılacaq.\n\n"
            "Ləğv üçün: CANCEL",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        )

    async def setcard_command(self, update, context):
        if not self.private(update) or not self.is_admin(update.effective_user.id):
            return
        if not self.backup.ready:
            await update.effective_message.reply_text("⚠️ GitHub ehtiyat nüsxəsi hazır deyil.")
            return
        try:
            self.topups.set_card(" ".join(context.args))
        except TopupError as exc:
            await update.effective_message.reply_text("❌ " + str(exc) + "\nİstifadə: /setcard 4169 0000 0000 0000")
            return
        await update.effective_message.reply_text("✅ Kart nömrəsi saxlanıldı. /topup ilə yoxlayın.")

    async def setcontact_command(self, update, context):
        if not self.private(update) or not self.is_admin(update.effective_user.id):
            return
        if not self.backup.ready:
            await update.effective_message.reply_text("⚠️ GitHub ehtiyat nüsxəsi hazır deyil.")
            return
        try:
            self.topups.set_contact(" ".join(context.args))
        except TopupError as exc:
            await update.effective_message.reply_text("❌ " + str(exc))
            return
        await update.effective_message.reply_text("✅ Admin əlaqəsi yadda saxlanıldı.")

    async def topup_amount_text(self, update, context):
        stage = context.user_data.get("manual_topup_stage")
        if not stage:
            return
        text = (update.message.text or "").strip()
        if text.upper() in ("CANCEL", "❌ CANCEL"):
            context.user_data.pop("manual_topup_stage", None)
            context.user_data.pop("manual_topup_cents", None)
            await update.message.reply_text("❌ Balans artırma müraciəti ləğv edildi.")
            raise ApplicationHandlerStop
        if stage == "amount":
            try:
                cents = parse_amount_cents(text)
            except TopupError as exc:
                await update.message.reply_text("❌ " + str(exc))
                raise ApplicationHandlerStop
            context.user_data["manual_topup_stage"] = "receipt"
            context.user_data["manual_topup_cents"] = cents
            await update.message.reply_text(
                f"💰 {cents / 100:.2f} AZN qeyd edildi.\n"
                "📷 Bank çekini şəkil kimi və ya PDF faylı olaraq göndərin.")
            raise ApplicationHandlerStop
        await update.message.reply_text("📷 Çekin şəklini və ya PDF-ni göndərin, yaxud CANCEL yazın.")
        raise ApplicationHandlerStop

    async def topup_receipt(self, update, context):
        if context.user_data.get("manual_topup_stage") != "receipt":
            return
        message = update.effective_message
        uid = update.effective_user.id
        if not self.private(update) or self.is_banned(uid):
            raise ApplicationHandlerStop
        if not self.backup.ready:
            await message.reply_text("⚠️ Məlumat bazası hələ bərpa edilməyib. Sonra yenidən yoxlayın.")
            raise ApplicationHandlerStop
        if message.photo:
            media = message.photo[-1]
            kind = "photo"
        elif (message.document and message.document.mime_type in
              ("image/jpeg", "image/png", "application/pdf")):
            media = message.document
            kind = "document"
        else:
            await message.reply_text("❌ Yalnız JPG/PNG şəkil və PDF çek qəbul edilir.")
            raise ApplicationHandlerStop
        if media.file_size and media.file_size > 5 * 1024 * 1024:
            await message.reply_text("❌ Çek 5 MB-dan böyük ola bilməz.")
            raise ApplicationHandlerStop
        try:
            ident = self.topups.submit(uid, context.user_data["manual_topup_cents"],
                                       media.file_id, kind)
        except TopupError as exc:
            await message.reply_text("❌ " + str(exc))
            raise ApplicationHandlerStop
        context.user_data.pop("manual_topup_stage", None)
        context.user_data.pop("manual_topup_cents", None)
        await message.reply_text(
            f"✅ Çek göndərildi (#{ident}). Admin təsdiqləyənədək balansa pul əlavə edilmir.")
        await self.notify_admins(context.bot, ident)
        raise ApplicationHandlerStop

    async def notify_admins(self, bot, ident):
        row = self.topups.get(ident)
        if not row:
            return
        caption = (f"💳 Yeni balans müraciəti #{ident}\n"
                   f"👤 Telegram ID: {row['uid']}\n"
                   f"💰 {row['cents']/100:.2f} AZN\n"
                   "Köçürməni bank hesabında yoxladıqdan sonra qərar verin.")
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Təsdiq", callback_data=f"topup:review:yes:{ident}"),
            InlineKeyboardButton("❌ Rədd", callback_data=f"topup:review:no:{ident}"),
        ]])
        for admin_id in self.admins:
            try:
                if row["kind"] == "photo":
                    await bot.send_photo(admin_id, row["file_id"], caption=caption, reply_markup=keyboard)
                else:
                    await bot.send_document(admin_id, row["file_id"], caption=caption,
                                            reply_markup=keyboard)
            except Exception as exc:
                # A failed notification does not erase the persisted request.
                print("[topup] admin notification failed: " + type(exc).__name__)

    async def topups_command(self, update, context):
        if not self.private(update) or not self.is_admin(update.effective_user.id):
            return
        records = self.topups.pending()
        if not records:
            await update.effective_message.reply_text("✅ Gözləyən çek yoxdur.")
            return
        await update.effective_message.reply_text(f"💳 Gözləyən çeklər: {len(records)}. Son 10 göstərilir.")
        for ident, _ in records[-10:]:
            await self.notify_admins(context.bot, ident)

    async def admin_services(self, update, context, page=0):
        if not self.private(update) or not self.is_admin(update.effective_user.id):
            return
        live = await self.services()
        entries = sorted(live)
        context.user_data["_market_service_keys"] = entries
        page = max(0, min(page, (len(entries) - 1) // 15 if entries else 0))
        rows = []
        for i in range(page * 15, min(len(entries), (page + 1) * 15)):
            name = entries[i]
            count = len(live[name])
            published = len(self.catalog.public({name: live[name]}).get(name, []))
            rows.append([InlineKeyboardButton(
                f"{name.upper()} · {published}/{count} aktiv range",
                callback_data=f"market:service:{i}")])
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("◀️", callback_data=f"market:page:{page - 1}"))
        if (page + 1) * 15 < len(entries):
            nav.append(InlineKeyboardButton("▶️", callback_data=f"market:page:{page + 1}"))
        if nav:
            rows.append(nav)
        await update.effective_message.reply_text(
            "🔐 Admin: iVASMS xidmətlərini və range-ləri seçin.\n"
            "Yalnız aktiv etdiyiniz range-lər istifadəçiyə göstərilir.\n"
            "API siyahısı anlıq stok sayına zəmanət vermir.",
            reply_markup=InlineKeyboardMarkup(rows) if rows else None,
        )

    async def range_menu(self, query, context, page=0):
        service = context.user_data.get("_market_selected_service")
        upstream = await self.services()
        ranges = sorted(set(str(r) for r in upstream.get(service, [])))
        context.user_data["_market_range_keys"] = ranges
        page = max(0, min(page, (len(ranges) - 1) // 15 if ranges else 0))
        rows = []
        for i in range(page * 15, min(len(ranges), (page + 1) * 15)):
            rid = ranges[i]
            active = self.catalog.allowed(service, rid)
            try:
                quote = self.quote(rid)
                price = f"{quote['price']} AZN"
            except ValueError:
                price = "qiymət təyin edilməyib"
            rows.append([InlineKeyboardButton(
                ("✅" if active else "⚪") + f" {rid} · {price}",
                callback_data=f"market:range:{i}")])
        nav = []
        if page:
            nav.append(InlineKeyboardButton("◀️", callback_data=f"market:rp:{page - 1}"))
        if (page + 1) * 15 < len(ranges):
            nav.append(InlineKeyboardButton("▶️", callback_data=f"market:rp:{page + 1}"))
        if nav:
            rows.append(nav)
        await query.message.reply_text(
            "⚙️ " + html.escape(str(service or "Xidmət")) + " üçün aktiv range seçimi.\n"
            "✅ = istifadəçilərə açıq. Qiymətlər mövcud admin qiymət ayarlarından alınır.",
            reply_markup=InlineKeyboardMarkup(rows) if rows else None)

    async def callback(self, update, context):
        query = update.callback_query
        await query.answer()
        uid = update.effective_user.id
        if not self.private(update) or not self.is_admin(uid):
            await query.message.reply_text("⛔ Yalnız admin.")
            return
        data = query.data
        if data.startswith("topup:review:"):
            if not self.backup.ready:
                await query.message.reply_text("⚠️ Şəxsi məlumat arxivi hazır deyil.")
                return
            _, _, decision, ident = data.split(":")
            async with self._review_lock:
                try:
                    result = self.topups.review(ident, decision == "yes",
                                                self.load_users, self.save_users)
                except TopupError as exc:
                    await query.message.reply_text("⚠️ " + str(exc))
                    return
            await query.message.reply_text(
                f"✅ #{ident} — {result['status']}. "
                f"İstifadəçi: {result['uid']} · {result['cents']/100:.2f} AZN.")
            try:
                await context.bot.send_message(
                    int(result["uid"]),
                    (f"✅ {result['cents']/100:.2f} AZN balansınıza əlavə edildi."
                     if result["status"] == "approved"
                     else "❌ Balans artırma çekiniz təsdiqlənmədi. Adminlə əlaqə saxlayın."))
            except Exception:
                pass
            return
        if data.startswith("market:page:"):
            await self.admin_services(update, context, int(data.rsplit(":", 1)[1]))
            return
        if data.startswith("market:service:"):
            choices = context.user_data.get("_market_service_keys", [])
            index = int(data.rsplit(":", 1)[1])
            if not 0 <= index < len(choices):
                await query.message.reply_text("Siyahını /market_admin ilə yeniləyin.")
                return
            context.user_data["_market_selected_service"] = choices[index]
            await self.range_menu(query, context)
            return
        if data.startswith("market:rp:"):
            await self.range_menu(query, context, int(data.rsplit(":", 1)[1]))
            return
        if data.startswith("market:range:"):
            if not self.backup.ready:
                await query.message.reply_text("⚠️ Şəxsi məlumat arxivi hazır deyil.")
                return
            service = context.user_data.get("_market_selected_service")
            keys = context.user_data.get("_market_range_keys", [])
            index = int(data.rsplit(":", 1)[1])
            if not 0 <= index < len(keys):
                await query.message.reply_text("Range siyahısını yeniləyin.")
                return
            try:
                enabled = self.catalog.toggle(service, keys[index], await self.services())
            except ValueError:
                await query.message.reply_text("Range artıq provayder siyahısında deyil.")
                return
            await query.message.reply_text(
                ("✅ Aktiv edildi: " if enabled else "🔒 Bağlandı: ") +
                f"{service} / {keys[index]}")
