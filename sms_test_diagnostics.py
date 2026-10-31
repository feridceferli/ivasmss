"""Safe SMS workflow diagnostics: zero network sends, private opt-in test history.

This module intentionally does NOT import or execute the uploaded SMS flooder.
The source script invokes 49 third-party OTP endpoints and supports unlimited
parallel submissions. That behavior is not safe to distribute.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from data_storage import atomic_save, data_path

MAX_HISTORY = 5000
MAX_SHOW = 80
MAX_USER_PER_MINUTE = 5
MAX_USER_PER_DAY = 50
LIVE_GLOBAL_PER_DAY = 10
LIVE_PER_PHONE_SECONDS = 3600
MAX_LIVE_HISTORY = 1000
THIRD_PARTY_ENDPOINTS_DISABLED = 49


class SmsDiagnosticError(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def normalize_test_phone(value):
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"[\s().-]", "", value.strip())
    if not re.fullmatch(r"\+[1-9][0-9]{6,14}", normalized):
        return None
    return normalized


class SmsDiagnosticStore:
    """Administrator-managed dry-run visibility and authenticated audit log."""

    def __init__(self, path=None):
        self.path = Path(path or data_path("sms_test_diagnostics_private.json"))
        self.lock = asyncio.Lock()

    def _read(self):
        try:
            result = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"version": 1, "enabled_for_all": False, "entries": [], "live_entries": []}
        except (ValueError, OSError) as exc:
            raise SmsDiagnosticError("storage_unavailable") from exc
        if (not isinstance(result, dict) or result.get("version") != 1
                or not isinstance(result.get("enabled_for_all"), bool)
                or not isinstance(result.get("entries"), list)
                or len(result["entries"]) > MAX_HISTORY
                or not isinstance(result.get("live_entries", []), list)
                or len(result.get("live_entries", [])) > MAX_LIVE_HISTORY):
            raise SmsDiagnosticError("storage_unavailable")
        result.setdefault("live_entries", [])
        return result

    def _write(self, result):
        atomic_save(result, self.path)

    def snapshot(self, uid, is_admin):
        state = self._read()
        available = bool(is_admin or state["enabled_for_all"])
        records = (state["entries"] if is_admin else
                   [r for r in state["entries"] if r.get("user_id") == uid])
        real_entries = state["live_entries"] if is_admin else []
        accepted = sum(1 for entry in real_entries if
                       entry.get("status") == "accepted_by_provider")
        return {
            "live_submitted_count": accepted,
            "live_history": list(reversed(real_entries[-MAX_SHOW:])) if is_admin else [],
            "available": available,
            "enabled_for_all": state["enabled_for_all"] if is_admin else None,
            "mode": "dry_run_no_sms_sent",
            "total_real_sms_sent": accepted,
            "third_party_endpoints_disabled": THIRD_PARTY_ENDPOINTS_DISABLED,
            "total_simulated_checks": len(state["entries"]) if is_admin else len(records),
            "history": list(reversed(records[-MAX_SHOW:])) if available else [],
        }

    async def set_visibility(self, enabled):
        if not isinstance(enabled, bool):
            raise SmsDiagnosticError("invalid_visibility")
        async with self.lock:
            state = self._read()
            state["enabled_for_all"] = enabled
            self._write(state)
            return {"enabled_for_all": enabled}

    async def simulate(self, uid, number, consent, is_admin=False):
        if consent is not True:
            raise SmsDiagnosticError("consent_required")
        phone = normalize_test_phone(number)
        if not phone:
            raise SmsDiagnosticError("invalid_phone")
        now = time.time()
        async with self.lock:
            state = self._read()
            if not is_admin and not state["enabled_for_all"]:
                raise SmsDiagnosticError("feature_disabled")
            past = [item for item in state["entries"] if item.get("user_id") == uid]
            if sum(1 for item in past if now - item.get("timestamp", 0) < 60) >= MAX_USER_PER_MINUTE:
                raise SmsDiagnosticError("rate_limited")
            if sum(1 for item in past if now - item.get("timestamp", 0) < 86400) >= MAX_USER_PER_DAY:
                raise SmsDiagnosticError("daily_limit")
            entry = {
                "id": "%s-%s" % (int(now * 1000), len(state["entries"])),
                "user_id": uid,
                "phone": phone,
                "timestamp": now,
                "date": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                "status": "simulated_no_sms_sent",
                "real_sms_sent": 0,
            }
            state["entries"].append(entry)
            state["entries"] = state["entries"][-MAX_HISTORY:]
            self._write(state)
            return entry

    async def send_live(self, uid, number, consent, is_admin, sender):
        """One controlled attempt, admin only, held under the audit/rate-limit lock.

        A pending entry is written before the HTTPS request so that a timed-out
        attempt still consumes its cooldown and is never blindly retried.
        """
        from sms_live_sender import SmsLiveError

        if not is_admin:
            raise SmsDiagnosticError("forbidden")
        if consent is not True:
            raise SmsDiagnosticError("consent_required")
        phone = normalize_test_phone(number)
        if not phone:
            raise SmsDiagnosticError("invalid_phone")
        sender.check_destination(phone)
        async with self.lock:
            data = self._read()
            now = time.time()
            attempts = data["live_entries"]
            if sum(1 for record in attempts if now - record.get("timestamp", 0) < 86400) >= LIVE_GLOBAL_PER_DAY:
                raise SmsDiagnosticError("live_daily_limit")
            if any(record.get("phone") == phone and now - record.get("timestamp", 0) < LIVE_PER_PHONE_SECONDS
                   for record in attempts):
                raise SmsDiagnosticError("live_phone_cooldown")

            record = {
                "id": "%s-%s" % (int(now * 1000), len(attempts)),
                "user_id": uid, "phone": phone, "timestamp": now,
                "date": datetime.fromtimestamp(now, timezone.utc).isoformat(),
                "status": "sending_pending", "real_sms_sent": 0,
            }
            attempts.append(record)
            data["live_entries"] = attempts[-MAX_LIVE_HISTORY:]
            self._write(data)
            try:
                reply = await sender.send(phone)
            except SmsLiveError as exc:
                record["status"] = ("delivery_unknown" if exc.code == "provider_result_unknown"
                                    else "provider_rejected")
                record["error_code"] = exc.code
                self._write(data)
                return {"ok": False, "error": exc.code, "entry": record}

            record["status"] = "accepted_by_provider"
            record["provider_status"] = reply["provider_status"]
            record["message_sid"] = reply["message_sid"]
            record["real_sms_sent"] = 1
            self._write(data)
            return {"ok": True, "entry": record}
