import asyncio
import json
import unittest
import httpx
from whatsapp_safe import WhatsAppConfig, WhatsAppConfigError, WhatsAppSmokeTest, TEST_MESSAGE, send_opt_in_test

class WhatsAppSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def test_payload_sent_to_single_configured_test_recipient(self):
        requests = []
        def handler(req):
            requests.append(req)
            return httpx.Response(200, json={"messages": [{"id": "test"}]})
        cfg = WhatsAppConfig("test-token", "1234567890", "994501112233")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            self.assertTrue(await send_opt_in_test(cfg, client=client))
        self.assertEqual(len(requests), 1)
        req = requests[0]
        self.assertEqual(req.url.path, "/v25.0/1234567890/messages")
        data = json.loads(req.content)
        self.assertEqual(data["to"], cfg.recipient)
        self.assertEqual(data["text"]["body"], TEST_MESSAGE)
        self.assertEqual(data["type"], "text")

    async def test_rejects_missing_token_and_invalid_recipient(self):
        with self.assertRaises(WhatsAppConfigError):
            await send_opt_in_test(WhatsAppConfig("", "1234567890", "994501112233"))
        with self.assertRaises(WhatsAppConfigError):
            WhatsAppConfig("test-token", "1234567890", "+994501112233").validate()

    async def test_cooldown_prevents_repeat(self):
        attempts = []
        def handler(req):
            attempts.append(req)
            return httpx.Response(200, json={})
        cfg = WhatsAppConfig("test-token", "1234567890", "994501112233")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            tester = WhatsAppSmokeTest(cooldown_seconds=300, now=lambda: 100.0)
            first = await tester.run(cfg, client=client)
            second = await tester.run(cfg, client=client)
        self.assertEqual(first, (True, 0))
        self.assertFalse(second[0])
        self.assertEqual(len(attempts), 1)

    async def test_non_success_api_response_propagates_without_retry(self):
        attempts = []
        def handler(req):
            attempts.append(req)
            return httpx.Response(403, json={"error": "sandbox-failure"})
        cfg = WhatsAppConfig("test-token", "1234567890", "994501112233")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaises(httpx.HTTPStatusError):
                await send_opt_in_test(cfg, client=client)
        self.assertEqual(len(attempts), 1)

if __name__ == "__main__":
    unittest.main()
