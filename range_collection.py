"""Bounded, cancellable number-only collection from a single range."""
import asyncio
import io
import re
import secrets
from dataclasses import dataclass, field


MAX_REQUESTS = 50
REQUEST_INTERVAL = 1.0
REQUEST_TIMEOUT = 20


def parse_range(value):
    value = str(value).strip().upper()
    if not re.fullmatch(r"[0-9]{1,15}X{0,14}", value) or len(value) > 15:
        raise ValueError("Range nümunəsi: 234XXX və ya 26134")
    return value.rstrip("X")


@dataclass
class CollectionResult:
    numbers: list = field(default_factory=list)
    requests: int = 0
    reason: str = "limit"


async def collect_numbers(rid, fetch, record, stop, *, limit=MAX_REQUESTS,
                          interval=REQUEST_INTERVAL, timeout=REQUEST_TIMEOUT):
    result = CollectionResult()
    seen = set()
    repeats = 0
    empty = 0
    for _ in range(min(MAX_REQUESTS, max(1, limit))):
        if stop.is_set():
            result.reason = "stopped"
            break
        result.requests += 1
        try:
            number, _country = await asyncio.wait_for(fetch(rid), timeout)
        except (Exception, asyncio.TimeoutError):
            result.reason = "error"
            break
        if not number:
            empty += 1
            if empty >= 3:
                result.reason = "empty"
                break
        else:
            raw = str(number).strip()
            digits = re.sub(r"\D", "", raw)
            if not re.fullmatch(r"\+?[0-9 ()-]+", raw) or not 7 <= len(digits) <= 15 or not digits.startswith(rid):
                result.reason = "mismatch"
                break
            empty = 0
            number = "+" + digits
            if number in seen:
                repeats += 1
                if repeats >= 3:
                    result.reason = "repeated"
                    break
            else:
                repeats = 0
                seen.add(number)
                result.numbers.append(number)
                try:
                    await record(number)
                except Exception:
                    result.reason = "storage"
                    break
        if stop.is_set():
            result.reason = "stopped"
            break
        if interval and result.requests < limit:
            try:
                await asyncio.wait_for(stop.wait(), interval)
            except asyncio.TimeoutError:
                pass
    return result


class RangeCollector:
    def __init__(self):
        self.jobs = {}

    async def start(self, update, context, range_text, fetch, archive):
        message = update.effective_message
        uid = update.effective_user.id
        if not update.effective_chat or update.effective_chat.type != "private":
            await message.reply_text("Bu funksiyanı botun şəxsi çatında açın.")
            return
        try:
            rid = parse_range(range_text)
        except ValueError as exc:
            await message.reply_text(str(exc))
            return
        # One collection at a time avoids concurrent bulk load on the API.
        if self.jobs:
            await message.reply_text("⏳ Toplama artıq davam edir. Bitdikdən sonra yenidən cəhd edin.")
            return
        stop = asyncio.Event()
        token = secrets.token_hex(6)
        self.jobs[uid] = (stop, token)
        context.application.create_task(
            self._run(message, uid, rid, range_text, fetch, archive, stop, token),
            update=update,
        )

    def stop_all(self):
        for stop, _token in self.jobs.values():
            stop.set()

    async def _run(self, message, uid, rid, range_text, fetch, archive, stop, token):
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        try:
            status = await message.reply_text(
                f"📥 {range_text}: nömrələr toplanır.\n"
                f"Maksimum {MAX_REQUESTS} sorğu; saniyədə ən çox 1 sorğu.\n"
                "Bu, bütün mövcud nömrələrin tam siyahısına zəmanət vermir.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                    "⏹ Dayandır", callback_data=f"range_collect_stop_{token}")]]),
            )
            async def record(number):
                await asyncio.to_thread(archive.record, number, uid)
            result = await collect_numbers(rid, fetch, record, stop)
            reasons = {
                "limit": "Sorğu limitinə çatıldı.", "stopped": "İstəyinizlə dayandırıldı.",
                "empty": "API ardıcıl 3 boş cavab qaytardı.",
                "repeated": "API ardıcıl 3 təkrar nömrə qaytardı.",
                "error": "API xətası və ya vaxt limiti səbəbilə dayandırıldı.",
                "mismatch": "API uyğun olmayan nömrə qaytardı; toplama dayandırıldı.",
                "storage": "Arxivə yazma xətası səbəbilə dayandırıldı.",
            }
            summary = (f"📥 Range: {rid}\n📞 Unikal nömrə: {len(result.numbers)}\n"
                       f"Sorğu: {result.requests}\n{reasons[result.reason]}\n\n"
                       "API-dəki bütün nömrələrin toplandığı təsdiqlənmir.")
            try:
                await status.edit_text(summary)
            except Exception:
                pass
            if result.numbers:
                preview = "\n".join(result.numbers[:10])
                document = io.BytesIO(("\n".join(result.numbers) + "\n").encode())
                await message.reply_document(
                    document=document, filename=f"range_{rid}.txt",
                    caption=summary + "\n\nİlk nömrələr:\n" + preview,
                )
            else:
                await message.reply_text(summary)
        finally:
            self.jobs.pop(uid, None)

    async def stop(self, query):
        job = self.jobs.get(query.from_user.id)
        token = query.data.removeprefix("range_collect_stop_")
        if not job or job[1] != token:
            await query.message.reply_text("Aktiv toplama tapılmadı.")
            return
        job[0].set()
        await query.message.reply_text("⏹ Dayandırılır. Hazırkı sorğudan sonra toplanmış nəticələr göndəriləcək.")
