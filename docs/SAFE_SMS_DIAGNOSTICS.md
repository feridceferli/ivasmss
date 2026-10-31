# IVASMS SMS diagnostics and admin live test sender

The previously uploaded bulk-SMS script is **not executed or deployed**.
Its 49 third-party OTP/registration endpoints, concurrent mass-submission
functionality and unlimited request behavior remain blocked.

## Live SMS for administrators

A separate real SMS test route uses the **official Twilio Messaging API**.
It does not use the uploaded script.

- Only verified IVASMS administrators can call `action:"send_live"`.
  Opening the simulation tab to other users does not grant live sending rights.
- Allowed destinations are controlled outside the UI using
  `SMS_LIVE_ALLOWED_NUMBERS` in Render, **not** from user input alone.
  Only numbers you own or whose subscribers specifically consented may be added.
- A fixed, non-marketing test message is sent. Users cannot set arbitrary content,
  sender IDs, service endpoints, number lists or send rate.
- The limit is **one attempt per destination per hour**, and **10 attempts
  globally per 24 hours**. Failed and uncertain attempts also consume the limit.
- Twilio HTTPS endpoint, Basic Auth, timeout and no redirects are enforced.
  Provider status `queued` or `accepted` does **not** prove mobile delivery.
- Every attempt (including provider rejections and uncertain responses) is saved
  in `sms_test_diagnostics_private.json` via the existing private GitHub backup.
- Telegram and website authorization, banned-user checks, and website CSRF
  checks apply to both simulation and real admin actions.
- No real SMS is sent until administrator **explicitly configures a live provider**
  and enables it through Render environment variables.

## Render environment variables to configure

| Variable | Description |
|---|---|
| `TWILIO_ACCOUNT_SID` | Live Twilio Account SID, begins `AC` |
| `TWILIO_AUTH_TOKEN` | Private Twilio auth token; never commit to GitHub |
| `TWILIO_FROM_NUMBER` | SMS-capable Twilio-owned sender number in +E.164 format |
| `SMS_LIVE_ALLOWED_NUMBERS` | Comma-separated consenting destination numbers in +E.164 |
| `SMS_LIVE_ENABLED` | Must equal `true` to allow real sends; off otherwise |

Example for a privately owned consenting number:
`SMS_LIVE_ALLOWED_NUMBERS=+9945XXXXXXXX,+9947XXXXXXXX`

These are examples only, **not** verified working numbers. Twilio trial
accounts also require verified recipients, and country permissions, sender
eligibility, balance and regulatory requirements may affect delivery. All
credentials live only in Render, not in the repository or Mini App.

## How to use

1. Configure the five variables under the IVASMS Render service.
2. Open the verified website or Telegram Mini App as an IVASMS administrator.
3. **Admin → SMS diaqnostikası → Real SMS**.
4. Enter an allowlisted, consenting number and tick the consent checkbox.
5. Press **Real test SMS göndər** once, then review the Twilio status.
6. Use the Twilio Console for the authoritative delivery result.

The existing **SMS Test** page remains simulation-only even if admins enable
the page for ordinary users. Users cannot use the live Twilio endpoint.

## Offline verification

The GitHub workflow runs tests for HTTP request shape, auth, destination
allowlist, consent, denied/non-admin access, rate limiting, private persistence,
legacy data compatibility and UI wiring. Tests mock HTTPS; passing them does
not validate the user's Twilio account or prove SMS delivery.
