# Admin-only Green SMS / Ivasmsper integration

The website and Telegram Mini App share a backend and UI. These integrations
have **no public navigation entries**: they are under `Admin` only, and the
`/api/admin-provider-feeds` endpoint verifies the Telegram signature or
website session and an allowed administrator ID **on every request**.

## Private Render Environment configuration

Use **new credentials issued for accounts you control**. Both third-party
repositories expose hard-coded keys/bot tokens; treat those as compromised.
Never copy those credentials, Telegram bot tokens or upstream forwarding loops
into this project. Configure these separately in the selected Render service:

| Variable | Purpose |
|---|---|
| `GREEN_SMS_API_BASE_URL` | HTTPS API base, without `/messages/` suffix |
| `GREEN_SMS_API_KEY` | Private Green SMS Bearer key |
| `IVASMSPER_PANEL_URL` | Full HTTPS URL of the authorized REST messages panel |
| `IVASMSPER_PANEL_TOKEN` | Private token for the REST panel |
| `IVASMSPER_WS_URL` | Optional authorized `wss://` Socket.IO live SMS URL |

Green SMS uses GET `/messages/?since_id=0&page_size=20` with a Bearer header.
Ivasmsper REST uses GET `?token=...&records=20` as defined by its sample
client. Use a trusted endpoint, because the REST provider protocol transmits
its key in a query parameter. Live mode listens for Socket.IO `42/livesms,`
events. These external services must actually provide live data to your
authorized account; an empty response is not fixed by installing a UI.

## Use

1. Set the variables on the Render service. Leave unused optional variables empty.
2. Redeploy the service once configuration has been saved.
3. Sign in to the website with Telegram or open the bot's Mini App.
4. Open **Admin → Green SMS** or **Admin → Ivasmsper** and press refresh.

The adapters **do not** send SMS or verification codes to Telegram groups,
public feeds, or other users. The HTTP adapter reads at most 30 messages;
the optional live WSS listener keeps at most 60 recent events in process
memory. This live buffer is not a persistent archive and resets on redeploy.

No provider credentials, SMS content, or tokens are placed into the public
repository, local browser storage, logs or user profile backups.
Use existing persistent backups for the bot's original user data only.
The new providers remain fully separate from the old number catalog.

## Deployment and test

Run `python -m unittest -v test_admin_provider_feeds`,
`python -m py_compile admin_provider_feeds.py main.py` and
`node --check docs/admin-provider-feeds.js`.
This doesn't exercise actual external provider logins; confirm the
authorization and permitted numbers directly from your provider portal.

The app intentionally refuses insecure HTTP/Ws upstream URLs to keep private
keys and messages from being transmitted without transport encryption.
For a legacy HTTP-only provider, install an authenticated HTTPS reverse proxy
under your control before pointing the application to it.
