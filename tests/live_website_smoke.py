"""Read-only live HTTP smoke test for Telegram bot + website integration.

Run with Python 3.12+: python tests/live_website_smoke.py
No real users, SMS providers, OTPs, or balance writes are touched.
"""
import http.cookiejar
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = os.getenv("LIVE_WEBSITE_URL", "https://ivasmss.onrender.com").rstrip("/")


def request(opener, path, method="GET", headers=None, data=None):
    req = urllib.request.Request(
        BASE_URL + path, data=data, method=method,
        headers={"User-Agent": "IVASMSSLiveSmoke/1.0", **(headers or {})}
    )
    try:
        with opener.open(req, timeout=35) as response:
            return response.status, response.read(250_000), response.headers
    except urllib.error.HTTPError as error:
        return error.code, error.read(4096), error.headers


def assert_http(actual, expected, name):
    assert actual == expected, f"{name}: expected HTTP {expected}, received {actual}"
    print(f"OK: {name} (HTTP {actual})")


def main():
    cookies = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
    anon = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    status, body, _ = request(client, "/health")
    assert_http(status, 200, "health")
    health = json.loads(body)
    assert health.get("ok") is True, "health payload is not OK"
    assert health.get("telegram_mode") == "webhook", "Telegram webhook is not configured"

    status, body, _ = request(client, "/")
    assert_http(status, 200, "website homepage")
    assert b"web-login.js" in body, "browser sign-in script absent"
    assert b"app.js" in body, "site app absent"

    for asset in ("/web-login.js", "/web-login.css", "/app.js"):
        status, body, _ = request(client, asset)
        assert_http(status, 200, "static asset " + asset)
        assert len(body) > 100, asset + " is empty"

    status, _, _ = request(client, "/api/web-auth/me")
    assert_http(status, 401, "anonymous website session rejected")

    status, _, _ = request(client, "/api/dashboard")
    assert_http(status, 401, "anonymous dashboard denied")

    status, _, _ = request(client, "/api/web-auth/start", method="POST", data=b"")
    assert_http(status, 403, "login start without same-origin marker denied")

    status, _, _ = request(client, "/api/web-auth/start", method="POST",
                           headers={"X-Website-Request": "1", "Origin": "https://other.example"}, data=b"")
    assert_http(status, 403, "cross-origin login start denied")

    status, body, _ = request(client, "/api/web-auth/start", method="POST",
                              headers={"X-Website-Request": "1",
                                       "Origin": BASE_URL}, data=b"")
    assert_http(status, 200, "begin Telegram pairing")
    issued = json.loads(body)
    deep_link = issued.get("bot_url", "")
    assert deep_link.startswith("https://t.me/") and "?start=connect_" in deep_link, "Telegram link is missing"
    token = issued.get("token", "")
    assert len(token) >= 30 and all(ch.isalnum() or ch in "_-" for ch in token), "invalid pairing challenge"
    assert any(c.name == "web_link_flow" and c.secure for c in cookies), "pairing cookie missing"
    print("OK: Telegram bot deep link + secure flow cookie")

    path = "/api/web-auth/status?token=" + urllib.parse.quote(token)
    status, body, _ = request(client, path)
    assert_http(status, 200, "original browser pending confirmation")
    assert json.loads(body).get("status") == "pending", "new link should be pending"

    status, _, _ = request(anon, path)
    assert_http(status, 403, "second browser cannot claim pairing")

    print("RESULT: All website smoke checks passed; Telegram user approval must be tested interactively.")


if __name__ == "__main__":
    main()
