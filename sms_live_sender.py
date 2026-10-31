"""Admin-only transactional SMS transport over Twilio's official HTTPS API.

Only administrator-configured, explicitly allowlisted test destinations are
eligible. This module never uses third-party OTP/registration endpoints.
"""
from __future__ import annotations

import os
import re

import httpx

from sms_test_diagnostics import normalize_test_phone

_TEST_BODY = "AZE SMS PANEL: Icaze verdiyiniz SMS baglanti testidir."
_ACCOUNT_RE = re.compile(r"AC[0-9a-fA-F]{32}\Z")
_MESSAGE_RE = re.compile(r"(?:SM|MM)[0-9a-fA-F]{32}\Z")


class SmsLiveError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class TwilioAllowlistedSender:
    """Strict sender: credentials and allowed recipients come only from Render env."""

    def _settings(self):
        sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        origin = os.getenv("TWILIO_FROM_NUMBER", "").strip()
        enabled = os.getenv("SMS_LIVE_ENABLED", "").strip().lower() == "true"
        raw = os.getenv("SMS_LIVE_ALLOWED_NUMBERS", "").strip()
        requested = [value for value in re.split(r"[,;\s]+", raw) if value]
        approved = {normalize_test_phone(value) for value in requested}
        valid_list = bool(requested) and None not in approved
        allowed = approved if valid_list else set()
        valid_config = bool(
            enabled and _ACCOUNT_RE.fullmatch(sid) and token
            and normalize_test_phone(origin) == origin and valid_list
        )
        return {
            "account_sid": sid, "auth_token": token, "origin": origin,
            "allowed": allowed, "enabled": enabled, "configured": valid_config,
        }

    def status(self):
        config = self._settings()
        return {
            "provider": "twilio",
            "enabled": config["enabled"],
            "configured": config["configured"],
            "allowlisted_number_count": len(config["allowed"]),
            "delivery_confirmation": "provider_submission_only",
            "requires_admin": True,
        }

    def check_destination(self, number):
        config = self._settings()
        if not config["configured"]:
            raise SmsLiveError("provider_not_configured")
        if number not in config["allowed"]:
            raise SmsLiveError("destination_not_allowlisted")
        return config

    async def send(self, number, client=None):
        config = self.check_destination(number)
        url = ("https://api.twilio.com/2010-04-01/Accounts/" +
               config["account_sid"] + "/Messages.json")
        data = {"To": number, "From": config["origin"], "Body": _TEST_BODY}
        auth = httpx.BasicAuth(config["account_sid"], config["auth_token"])
        try:
            if client is None:
                async with httpx.AsyncClient(
                    timeout=15.0, follow_redirects=False
                ) as live_client:
                    response = await live_client.post(url, data=data, auth=auth)
            else:
                response = await client.post(url, data=data, auth=auth)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            # The carrier may have accepted the SMS even if the connection died.
            raise SmsLiveError("provider_result_unknown") from exc
        if response.status_code in (401, 403):
            raise SmsLiveError("provider_auth_failed")
        if response.status_code == 429:
            raise SmsLiveError("provider_rate_limited")
        if response.status_code < 200 or response.status_code >= 300:
            raise SmsLiveError("provider_rejected")
        try:
            payload = response.json()
        except (ValueError, TypeError) as exc:
            raise SmsLiveError("provider_result_unknown") from exc
        sid = payload.get("sid") if isinstance(payload, dict) else None
        if not isinstance(sid, str) or not _MESSAGE_RE.fullmatch(sid):
            raise SmsLiveError("provider_result_unknown")
        provider_status = payload.get("status") if isinstance(payload.get("status"), str) else "accepted"
        return {"message_sid": sid, "provider_status": provider_status,
                "status": "accepted_by_provider"}
