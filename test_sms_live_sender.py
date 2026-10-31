"""Admin real-SMS integration tests: all provider requests mocked."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx

from sms_live_sender import SmsLiveError, TwilioAllowlistedSender
from sms_test_diagnostics import SmsDiagnosticError, SmsDiagnosticStore

class LiveSmsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = SmsDiagnosticStore(Path(self.temp.name) / "audit.json")
        self.env = patch.dict("os.environ", {
            "TWILIO_ACCOUNT_SID": "AC" + "1" * 32,
            "TWILIO_AUTH_TOKEN": "fake-test-token",
            "TWILIO_FROM_NUMBER": "+15550101010",
            "SMS_LIVE_ENABLED": "true",
            "SMS_LIVE_ALLOWED_NUMBERS": "+994501234567, +994551234567",
        })
        self.env.start()
        self.sender = TwilioAllowlistedSender()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    async def test_nonadmin_cannot_send_even_with_public_simulation(self):
        await self.store.set_visibility(True)
        with self.assertRaises(SmsDiagnosticError) as cm:
            await self.store.send_live(1, "+994501234567", True, False, self.sender)
        self.assertEqual(cm.exception.code, "forbidden")
        self.assertFalse(self.store.snapshot(1, True)["live_history"])

    async def test_consent_and_allowlist(self):
        with self.assertRaises(SmsDiagnosticError) as cm:
            await self.store.send_live(1, "+994501234567", False, True, self.sender)
        self.assertEqual(cm.exception.code, "consent_required")
        with self.assertRaises(SmsLiveError) as cm:
            await self.store.send_live(1, "+994701111111", True, True, self.sender)
        self.assertEqual(cm.exception.code, "destination_not_allowlisted")
        self.assertFalse(self.store.snapshot(1, True)["live_history"])

    async def test_disabled_provider(self):
        with patch.dict("os.environ", {"SMS_LIVE_ENABLED": "false"}):
            with self.assertRaises(SmsLiveError) as cm:
                await self.store.send_live(1, "+994501234567", True, True, self.sender)
            self.assertEqual(cm.exception.code, "provider_not_configured")

    async def test_https_twilio_request_persist_and_cooldown(self):
        hits = []
        def mock_transport(request):
            hits.append(request)
            self.assertEqual(request.url.host, "api.twilio.com")
            self.assertEqual(request.url.scheme, "https")
            self.assertTrue(request.headers["authorization"].startswith("Basic "))
            self.assertIn("To=%2B994501234567", request.content.decode())
            self.assertIn("Body=", request.content.decode())
            return httpx.Response(201, json={
                "sid": "SM" + "2" * 32, "status": "queued"
            })
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock_transport)) as client:
            class TestSender(TwilioAllowlistedSender):
                async def send(inner, number):
                    return await super(TestSender, inner).send(number, client=client)
            sender = TestSender()
            response = await self.store.send_live(
                1, "+994501234567", True, True, sender)
            self.assertTrue(response["ok"])
            self.assertEqual(response["entry"]["status"], "accepted_by_provider")
            self.assertEqual(len(hits), 1)
            reloaded = SmsDiagnosticStore(self.store.path).snapshot(1, True)
            self.assertEqual(reloaded["live_submitted_count"], 1)
            self.assertEqual(reloaded["live_history"][0]["phone"], "+994501234567")
            with self.assertRaises(SmsDiagnosticError) as cm:
                await self.store.send_live(1, "+994501234567", True, True, sender)
            self.assertEqual(cm.exception.code, "live_phone_cooldown")
            self.assertEqual(len(hits), 1)

    async def test_rejections_are_audited_and_not_retried(self):
        class RejectSender(TwilioAllowlistedSender):
            async def send(self, phone):
                raise SmsLiveError("provider_rejected")
        sender = RejectSender()
        response = await self.store.send_live(1, "+994501234567", True, True, sender)
        self.assertEqual(response["error"], "provider_rejected")
        self.assertEqual(self.store.snapshot(1, True)["live_submitted_count"], 0)
        with self.assertRaises(SmsDiagnosticError) as cm:
            await self.store.send_live(1, "+994501234567", True, True, sender)
        self.assertEqual(cm.exception.code, "live_phone_cooldown")

    def test_old_archive_reads_without_live_log(self):
        self.store.path.write_text(
            '{"version":1,"enabled_for_all":false,"entries":[]}', encoding="utf-8")
        self.assertEqual(self.store.snapshot(1, True)["live_history"], [])

if __name__ == "__main__":
    unittest.main()
