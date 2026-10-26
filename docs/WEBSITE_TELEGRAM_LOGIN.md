# Telegram + website — unified login

Production website: https://ivasmss.onrender.com/
Telegram Mini App: same URL in the bot menu if `WEBAPP_URL` is set to that URL.
Both surfaces use one backend and the Telegram numeric user ID as their account key.

## How the website sign-in works
1. In a normal browser, open the website and choose **Telegram hesabımı bağla**.
2. The website generates a random pairing challenge, usable for at most 10 minutes.
3. The browser opens a Telegram bot deep link. The user must approve **Sayta girişi təsdiqlə** in that bot's private chat.
4. The original browser detects approval and gets a signed, 7-day HttpOnly, Secure, SameSite=Strict cookie.
5. Existing backend routes now accept either valid Telegram Mini App `initData` or a valid website session. A valid website session is only accepted on same-origin write requests. All balances and orders still use the authenticated Telegram user ID.
6. Click **Çıxış** in the website header to end the browser session.

The bot token never appears in the HTML or JavaScript. Wrong-browser polling is rejected using a separate HttpOnly flow cookie. The server never treats an unverified username or ID sent by the browser as authentication.

## Render configuration
Use **one running instance** of the service hosting `main.py`.
- Build: `pip install -r requirements.txt`
- Start: `python main.py` (the existing Procfile may also be used)
- `BOT_TOKEN` and `AZE_SMS_API_KEY` are secret environment variables.
- `WEBAPP_URL=https://ivasmss.onrender.com/` (if it is set to the old GitHub Pages URL, update it in Render).
- `RENDER_EXTERNAL_URL` is normally provided automatically by Render and determines the Telegram webhook endpoint as `/webhook`.
- Test `/health` (bot + web service), then test `/` and account pairing in a regular HTTPS browser. An unauthenticated API request must return HTTP 401.
- In BotFather, update the bot's Mini App URL to `https://ivasmss.onrender.com/` if its profile Mini App still points elsewhere. The chat menu URL is configured programmatically at startup.

Pending 10-minute pairing challenges are stored in memory, so if Render restarts during pairing, start over. The final session cookie is signed, survives restarts while BOT_TOKEN remains unchanged, and expires after 7 days. Rotating BOT_TOKEN invalidates sessions and requires reconnecting. Free Render instances may sleep during inactivity.
