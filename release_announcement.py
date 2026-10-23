"""One-time release-note announcement; no OTP or phone-number content.

This file is intentionally separate from message monitoring and only sends a
fixed product-changelog notice to the existing update group.
"""
import json
from pathlib import Path
from data_storage import data_path, atomic_save

RELEASE_KEY = "global-country-directory-2026-10-23"
NOTICE = (
    "📢 <b>AZE SMS PANEL — YENİLİKLƏR</b>\n\n"
    "🌍 <b>Bütün ölkələr:</b> 244 ölkə və ərazinin beynəlxalq telefon "
    "kodları əlavə edilib. API-nin bildirdiyi range-lər ölkələr üzrə "
    "sıralanır.\n\n"
    "🇦🇿 <b>Azərbaycan:</b> Bakcell, Azercell, Nar, Naxtell, Catel (+99440) "
    "və CDMA (+99444) bölmələri yenilənib. 210/211 seçimləri və API-də "
    "elan edilən əlavə range-lər göstərilir.\n\n"
    "🔒 <b>+994 istifadəsi:</b> admin təsdiqi lazımdır. "
    "İcazə üçün botun şəxsi çatına /az_request yazın.\n\n"
    "✅ <b>Dəvət sistemi:</b> dost dəvət etmək şərti ləğv edilib.\n\n"
    "📲 Yenilənmiş menyunu görmək üçün bota /start yazın.\n"
    "ℹ️ Range-in siyahıda olması aktiv nömrə mövcudluğuna zəmanət vermir."
)


async def send_release_notice_once(bot, group_id):
    marker = Path(data_path("release_notice_global_country_20261023.json"))
    try:
        previous = json.loads(marker.read_text(encoding="utf-8"))
        if previous.get("release") == RELEASE_KEY and previous.get("sent"):
            print("[release-notice] Already sent; skipped", flush=True)
            return False
    except (OSError, ValueError, TypeError):
        pass

    try:
        result = await bot.send_message(
            chat_id=int(group_id),
            text=NOTICE,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as exc:
        print(f"[release-notice] Send failed: {type(exc).__name__}: {str(exc)[:120]}", flush=True)
        return False

    try:
        atomic_save({
            "release": RELEASE_KEY,
            "sent": True,
            "message_id": int(result.message_id),
        }, marker)
    except OSError as exc:
        print(f"[release-notice] Marker save failed: {type(exc).__name__}", flush=True)
    print(f"[release-notice] Delivered to group; message_id={result.message_id}", flush=True)
    return True
