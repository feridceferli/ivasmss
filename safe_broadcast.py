"""Reliable admin-only informational announcements to users who started the bot.

No phone numbers, OTP, passwords, or authentication messages are broadcast.
Follows Telegram rate limits and returns summary counters only.
"""
import asyncio
import html
import re

from telegram.error import Forbidden, RetryAfter, TelegramError

MAX_NOTICE_LENGTH = 3400
MIN_DELAY_SECONDS = 0.085  # <12 messages/s in a single worker
MAX_RETRIES = 3
SENSITIVE_PATTERNS = (
    re.compile(r"\b(?:otp|verification\s*code|two.factor\s*code|2fa\s*code|sms\s*code|təsdiq\s*kodu|doğrulama\s*kodu)\s*[:\-=]?\s*\d{4,8}\b", re.I),
    re.compile(r"\b(?:password|parol|şifrə|sifre)\s*[:=]\s*\S+", re.I),
)


def validate_notice(body):
    if not isinstance(body, str) or not body.strip():
        raise ValueError("Bildiriş mətni boş ola bilməz.")
    message = body.strip()
    if len(message) > MAX_NOTICE_LENGTH:
        raise ValueError("Bildiriş çox uzundur. 3400 simvoldan qısa mətn yaz.")
    if any(pattern.search(message) for pattern in SENSITIVE_PATTERNS):
        raise ValueError("SMS təsdiq kodları və parollar ümumi bildiriş kimi göndərilə bilməz.")
    return message


def recipient_ids(user_db):
    """Only users who previously started and were recorded by this bot."""
    if not isinstance(user_db, dict):
        return []
    found = []
    for key in user_db.keys():
        if str(key).isdigit():
            uid = int(key)
            if uid > 0:
                found.append(uid)
    return sorted(set(found))


async def send_notice(bot, ids, body):
    """Sequential rate-limited send, RetryAfter handling, no sensitive log output."""
    message = validate_notice(body)
    recipients = sorted(set(int(uid) for uid in ids if int(uid) > 0))
    summary = {"targeted": len(recipients), "sent": 0, "failed": 0, "blocked": 0, "retry_exhausted": 0}
    formatted = "📢 <b>MƏLUMAT BİLDİRİŞİ</b>\n\n" + html.escape(message)
    for uid in recipients:
        sent = False
        for attempt in range(MAX_RETRIES + 1):
            try:
                await bot.send_message(chat_id=uid, text=formatted, parse_mode="HTML")
                summary["sent"] += 1
                sent = True
                break
            except RetryAfter as exc:
                if attempt == MAX_RETRIES:
                    summary["retry_exhausted"] += 1
                    break
                await asyncio.sleep(min(max(float(exc.retry_after), 1.0), 60.0) + 0.5)
            except Forbidden:
                summary["blocked"] += 1
                break
            except TelegramError:
                break
        if not sent:
            summary["failed"] += 1
        await asyncio.sleep(MIN_DELAY_SECONDS)
    return summary
