# SMS test diagnostics — safe integration

The uploaded `nower-sms-bombası [HIZLANDIRILMIŞ](1).py` was reviewed but
**is not executed, imported, or copied into the deployed bot**. It makes
concurrent OTP/SMS requests to 49 third-party services and supports unlimited
requests. This is unsuitable for a public, multi-user app.

## What was integrated instead

- A private, **dry-run-only** SMS diagnostics tab on the website and Telegram
  Mini App, disabled for ordinary users by default.
- Admin-only toggle to show or hide **the dry-run tab** for everyone. Turning
  it on **never enables real SMS delivery**.
- E.164 phone input, explicit test authorization declaration, per-user
  throttling (5/minute, 50/day), and diagnostics showing **0 real SMS sent**.
- Date/time, requesting user ID, full phone number and simulated result
  recorded privately as `sms_test_diagnostics_private.json`.
- Per-user history is scoped to the signed-in user; admins can view the full
  audit trail. Number history is excluded from public source control.
- The existing private GitHub user-backup system preserves the setting and
  history across Render redeploys. Changes fail closed until the private
  backup is ready; unsuccessful remote sync returns a visible error.
- One authenticated endpoint: `GET/POST /api/sms-diagnostics`.
  `POST {action:"visibility", enabled:bool}` is admin-only.
  `POST {action:"simulate", number:"+994...", consent:true}` performs
  **no network requests or SMS transmissions**.

Admin navigation: **Admin → SMS diaqnostikası**. User navigation appears as
**SMS Test** only when the admin has enabled the safe simulation.

## Source behavior intentionally excluded

There is no invocation of `send()`, `send_service()`, third-party registration
or OTP endpoints, unbounded workers, or any real SMS campaign. All counts and
history are labeled **simulation**. Historical test targets must never be
represented as successfully delivered SMS.
