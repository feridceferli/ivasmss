import asyncio
import logging
import os
from aiohttp import web
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# Logging quraşdırması
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Sadə yaddaş bazası (Orijinal struktur)
users_db = {}

# Mühit dəyişənləri
TOKEN = os.environ.get("BOT_TOKEN")
NOTIFY_GROUP_ID = os.environ.get("NOTIFY_GROUP_ID")
if NOTIFY_GROUP_ID:
    NOTIFY_GROUP_ID = int(NOTIFY_GROUP_ID)

PORT = int(os.environ.get("PORT", 8080))
WEB_URL = os.environ.get("WEB_URL", "https://sizin-proyekt.onrender.com")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if user_id not in users_db:
        users_db[user_id] = {"invited_count": 0, "referred_by": None, "messages": []}

        if context.args:
            arg = context.args[0]
            if arg.startswith("ref_"):
                try:
                    referrer_id = int(arg.replace("ref_", ""))
                    if referrer_id != user_id and referrer_id in users_db:
                        if users_db[user_id]["referred_by"] is None:
                            users_db[user_id]["referred_by"] = referrer_id
                            users_db[referrer_id]["invited_count"] += 1

                            await context.bot.send_message(
                                chat_id=referrer_id,
                                text="🎉 Təbriklər! Bir dostunuz sizin linkinizlə bota qoşuldu.",
                            )
                except ValueError:
                    pass

    invited_count = users_db[user_id]["invited_count"]
    bot_username = context.bot.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    mini_app_url = f"{WEB_URL}/?user_id={user_id}"

    keyboard = [
        [
            InlineKeyboardButton(
                "🚀 Mini App-i Aç", web_app=WebAppInfo(url=mini_app_url)
            )
        ],
        [
            InlineKeyboardButton(
                "🔗 Dostunu Dəvət Et (Paylaş)",
                url=f"https://t.me/share/url?url={ref_link}&text=Botdan istifadə etmək üçün bu keçidə daxil ol!",
            )
        ],
        [
            InlineKeyboardButton(
                "🔄 Vəziyyəti Yoxla", callback_data="check_status"
            )
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if invited_count < 1:
        await update.message.reply_text(
            "❌ **Botdan istifadə etmək üçün ən azı 1 dostunuzu dəvət etməlisiniz!**\n\n"
            f"Sizin dəvət linkiniz:\n`{ref_link}`\n\n"
            f"Cari dəvət sayınız: {invited_count}/1",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "✅ **Şərt ödaəndi! Botu və Mini App-i indi istifadə edə bilərsiniz.**\n\n"
            "Xoş gəlmisiniz! Əsas menyu aktivdir.",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id not in users_db:
        users_db[user_id] = {"invited_count": 0, "referred_by": None, "messages": []}

    invited_count = users_db[user_id]["invited_count"]

    if query.data == "check_status":
        if invited_count >= 1:
            await query.edit_message_text(
                "✅ Şərt ödəndi! Botu və Mini App-i indi istifadə edə bilərsiniz."
            )
        else:
            bot_username = context.bot.username
            ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
            await query.edit_message_text(
                "❌ Hələ ki heç kim sizin linkinizlə qoşulmayıb.\n\n"
                f"Dəvət linkiniz:\n`{ref_link}`\n\n"
                f"Cari dəvət sayınız: {invited_count}/1",
                parse_mode="Markdown",
            )


async def api_get_user(request):
    user_id = request.query.get("user_id")
    if not user_id:
        return web.json_response({"error": "user_id tapılmadı"}, status=400)

    try:
        user_id = int(user_id)
    except ValueError:
        return web.json_response({"error": "Invalid user_id"}, status=400)

    if user_id not in users_db:
        users_db[user_id] = {"invited_count": 0, "referred_by": None, "messages": []}

    data = users_db[user_id]
    bot_username = request.app["bot_username"]
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
    }

    return web.json_response({
        "user_id": user_id,
        "invited_count": data.get("invited_count", 0),
        "ref_link": ref_link,
        "messages": data.get("messages", []),
    }, headers=headers)


async def handle_ivasmss_webhook(request):
    try:
        data = await request.json()
        logger.info(f"DEBUG: Webhook sorğusu gəldi: {data}")

        user_id = (
            data.get("user_id") or data.get("chat_id") or data.get("telegram_id")
        )
        phone = data.get("phone") or data.get("number") or data.get("gsm") or ""
        sms_text = data.get("sms_text") or data.get("message") or data.get("text") or ""

        if not user_id or not sms_text:
            return web.Response(text="Eksik məlumat", status=400)

        user_id = int(user_id)
        if user_id not in users_db:
            users_db[user_id] = {"invited_count": 0, "referred_by": None, "messages": []}

        if "messages" not in users_db[user_id]:
            users_db[user_id]["messages"] = []

        users_db[user_id]["messages"].insert(0, {"phone": phone, "sms_text": sms_text})

        formatted_msg = (
            f"📨 **YENİ SMS / OTP KODU**\n\n"
            f"👤 **İstifadəçi ID:** `{user_id}`\n"
            f"📱 **Nömrə:** `{phone}`\n"
            f"💬 **Mesaj:**\n`{sms_text}`"
        )

        app_instance = request.app["bot_application"]

        # 1. İstifadəçiyə göndər
        try:
            await app_instance.bot.send_message(
                chat_id=user_id, text=formatted_msg, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"İstifadəçiyə mesaj göndərilərkən xəta: {e}")

        # 2. Qrupa göndər (NOTIFY_GROUP_ID vasitəsilə)
        if NOTIFY_GROUP_ID:
            try:
                await app_instance.bot.send_message(
                    chat_id=NOTIFY_GROUP_ID, text=formatted_msg, parse_mode="Markdown"
                )
                logger.info(f"DEBUG: Mesaj qrupa ({NOTIFY_GROUP_ID}) uğurla göndərildi!")
            except Exception as e:
                logger.error(f"Qrupa mesaj göndərilərkən xəta: {e}")
        else:
            logger.warning("NOTIFY_GROUP_ID təyin olunmayıb!")

        return web.Response(text="OK", status=200)
    except Exception as e:
        logger.error(f"Webhook xətası: {e}")
        return web.Response(text=str(e), status=500)


async def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN mühit dəyişəni tapılmadı!")

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    await application.initialize()
    await application.start()

    bot_info = await application.bot.get_me()
    app_username = bot_info.username

    app = web.Application()
    app["bot_application"] = application
    app["bot_username"] = app_username

    app.router.add_get("/api/user", api_get_user)
    app.router.add_post("/webhook", handle_ivasmss_webhook)
    app.router.add_static("/", path="./static", name="static", show_index=True)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"Server {PORT} portunda işə düşdü və webhook aktivdir...")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
