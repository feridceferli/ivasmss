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

## Admin-only number lists (new)

These two source repositories do not document a number-purchase or stock API.
The SMS `number` field is the destination number in a delivered message;
it must not be represented as a currently available number for allocation.

For a usable admin-only authorized number list, open **Admin → Green SMS**
or **Admin → Ivasmsper** in the website/Mini App and:

1. Paste phone numbers (one per line, E.164 international format), or choose a
   plain `.txt` file, then press **Nömrələri əlavə et**.
2. Use **Kopyala** for one of your imported numbers or **Sil** to remove it.
3. Keep SMS events in the separate **mesajlar** view above the inventory.

Each provider has a completely separate stored list. The `/green_sms` and
`/ivasmsper` Telegram commands are private and admin-only, showing the count
and five sample numbers. An admin can send
`/green_sms add +994501234567` or `/ivasmsper add +994501234567` to import
a number. No regular Telegram user can see or modify these lists.

The source of numbers is **explicit admin input**, not arbitrary generation or
an unverified external stock feed. Imported numbers are NOT automatically
rentable, and incoming SMS is only available when the upstream service
actually routes SMS to those numbers.

`admin_provider_numbers.json` is included in `user_backup`'s private GitHub
snapshot. Writes are refused while that private backup is not ready, and the
site reports a backup error if a local save was not synchronized remotely.
Do not set `NUMBER_ARCHIVE_GITHUB_REPO` to a public repository.

## If no messages show up

- First check whether the admin status reports the provider as configured.
- The Green SMS sample hardcodes an **HTTP-only IP address**. That is not a
  secure HTTPS API endpoint and will be rejected by this integration.
  Configure a legitimate HTTPS endpoint offered by your provider, or a
  properly secured TLS reverse proxy you own.
- Ivasmsper's sample uses manually entered REST panels and optional Socket.IO
  credentials, not a discovered inventory. If an authorized REST panel has no
  messages, its result may be empty.
- Render deploying successfully confirms that the bot server started, not
  that a provider authorized requests or had SMS/number inventory.

## Telegram admin checks

In the **bot's private chat**, use:

- `/green_sms` / `/ivasmsper`: count and first five imported numbers.
- `/green_sms status` / `/ivasmsper status`: provider configuration and
  optional live socket status, **without displaying secret tokens**.
- `/green_sms sms` / `/ivasmsper sms`: up to five actual records from the
  configured provider feed. If the provider returns no records or HTTP 401,
  403, 404 or 429, the bot explains that status rather than inventing numbers.
- `/green_sms add +994501234567` and
  `/ivasmsper add +994501234567`: add explicitly authorized stock after
  successfully synchronizing to the private backup.

Only server-confirmed bot administrators in private conversations can execute
these commands; nothing is forwarded to a group. Telegram commands and
website/Mini App share the **same** two inventories.
