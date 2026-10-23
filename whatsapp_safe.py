"""Opt-in, admin-only WhatsApp Cloud API smoke test for the Telegram bot.

This module never requests WhatsApp registration/OTP codes or sends arbitrary
messages. Only a fixed, environment-configured test recipient can be used.
"""

import asyncio
import os
import re
import time
from dataclasses import dataclass
from typing import Optional

import httpx

TEST_MESSAGE = "IVASMS WhatsApp əlaqə testi. Bu, əvvəlcədən razılaşdırılmış sınaq mesajıdır."
COOLDOWN_SECONDS = 300


class WhatsAppConfigError(ValueError):
    pass


@dataclass(frozen=True)
class WhatsAppConfig:
    token: str
    phone_number_id: str
    recipient: str
    graph_version: str = "v25.0"

    @classmethod
    def from_env(cls):
        return cls(
            token=os.getenv("WA_ACCESS_TOKEN", "").strip(),
            phone_number_id=os.getenv("WA_PHONE_NUMBER_ID", "").strip(),
            recipient=os.getenv("WA_TEST_RECIPIENT", "").strip(),
            graph_version=os.getenv("WA_GRAPH_VERSION", "v25.0").strip(),
        )

    def validate(self):
        if not self.token:
            raise WhatsAppConfigError("WA_ACCESS_TOKEN yoxdur")
        if not re.fullmatch(r"\d{5,25}", self.phone_number_id):
            raise WhatsAppConfigError("WA_PHONE_NUMBER_ID düzgün deyil")
        if not re.fullmatch(r"[1-9]\d{6,14}", self.recipient):
            raise WhatsAppConfigError("WA_TEST_RECIPIENT ölkə kodu ilə rəqəmlərdən ibarət olmalıdır")
        if not re.fullmatch(r"v\d{1,2}\.\d{1,2}", self.graph_version):
            raise WhatsAppConfigError("WA_GRAPH_VERSION düzgün deyil")

    def masked_recipient(self):
        return (self.recipient[:3] + "***" + self.recipient[-2:]) if len(self.recipient) >= 7 else "***"


async def send_opt_in_test(config: WhatsAppConfig, *, client: Optional[httpx.AsyncClient] = None):
    """Send one fixed text to the one configured, opted-in test destination.

    Caller owns an injected client. Never echoes token, OTP, or response body.
    WhatsApp may require an active 24-hour customer-service window for freeform texts.
    """
    config.validate()
    url = f"https://graph.facebook.com/{config.graph_version}/{config.phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": config.recipient,
        "type": "text",
        "text": {"preview_url": False, "body": TEST_MESSAGE},
    }
    headers = {"Authorization": f"Bearer {config.token}", "Content-Type": "application/json"}
    if client is not None:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return True
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as own_client:
        response = await own_client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return True


class WhatsAppSmokeTest:
    def __init__(self, *, cooldown_seconds=COOLDOWN_SECONDS, now=time.monotonic):
        self.cooldown_seconds = cooldown_seconds
        self.now = now
        self._last_attempt = None
        self._lock = asyncio.Lock()

    async def run(self, config: WhatsAppConfig, *, client=None):
        config.validate()
        async with self._lock:
            t = self.now()
            if self._last_attempt is not None and t-self._last_attempt < self.cooldown_seconds:
                return False, int(self.cooldown_seconds-(t-self._last_attempt))+1
            # The cooldown applies even on failure. No automatic retry is performed.
            self._last_attempt = t
        await send_opt_in_test(config, client=client)
        return True, 0


def register_whatsapp_handlers(app, is_admin):
    """Register two admin-only Telegram commands on an existing Application."""
    from telegram.ext import CommandHandler

    smoke_test = WhatsAppSmokeTest()

    async def wa_status(update, context):
        if not update.effective_user or not is_admin(update.effective_user.id):
            return
        cfg = WhatsAppConfig.from_env()
        try:
            cfg.validate()
        except WhatsAppConfigError as err:
            await update.effective_message.reply_text(f"⚠️ WhatsApp bağlantısı hazır deyil: {err}")
            return
        await update.effective_message.reply_text(
            f"✅ WhatsApp sınaq konfiqurasiyası hazırdır. Test nömrəsi: {cfg.masked_recipient()}. "
            "Bu, real API bağlantısının uğurlu olmasını hələ təsdiqləmir."
        )

    async def wa_test(update, context):
        if not update.effective_user or not is_admin(update.effective_user.id):
            return
        cfg = WhatsAppConfig.from_env()
        try:
            sent, remaining = await smoke_test.run(cfg)
        except WhatsAppConfigError as err:
            await update.effective_message.reply_text(f"⚠️ Test başlamadı: {err}")
        except httpx.HTTPStatusError as err:
            # Never relay an upstream body: it could include sensitive details.
            await update.effective_message.reply_text(
                f"❌ WhatsApp API mesajı qəbul etmədi (HTTP {err.response.status_code}). "
                "Meta API icazələrini və 24 saatlıq mesajlaşma pəncərəsini yoxla."
            )
        except httpx.RequestError:
            await update.effective_message.reply_text("❌ WhatsApp API ilə şəbəkə əlaqəsi qurulmadı.")
        else:
            if sent:
                await update.effective_message.reply_text("✅ Test mesajı WhatsApp API tərəfindən qəbul edildi. Çatdırılma ayrıca təsdiqlənməlidir.")
            else:
                await update.effective_message.reply_text(f"⏳ Təkrar test üçün təxminən {remaining} saniyə gözlə.")

    app.add_handler(CommandHandler("wa_status", wa_status))
    app.add_handler(CommandHandler("wa_test", wa_test))
