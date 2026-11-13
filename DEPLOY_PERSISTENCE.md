# Render persistent storage and paid rental rollout

## Status / deployment guardrail

This branch is **not** automatically deployed to the live Render service. Review
GitHub Actions checks and merge only after configuring durable storage and backing
up the current private runtime data. Do not put real SMS, OTP, balances, receipts,
bank details, API keys, or bot tokens in this **public** repository.

## Keep all admin settings and balances after a restart

The bot currently uses single-process JSON snapshots, with an atomic write for
each file. The following records MUST be stored on a durable mounted disk:

- `users.json`: balances, three-minute rental journal, receipt-based top-ups,
  account permissions and preferences.
- `system_config.json`: payment card display text, hidden service list and
  other admin-managed settings.
- `active_leases.json`: live number ownership and remaining time.
- All other files resolved by `data_storage.data_path()`, plus the SQLite
  number archive (`number_archive.sqlite3`).

In the **confirmed** Render service, attach a **persistent disk** mounted at
`/var/data`, and set `DB_FOLDER=/var/data` in Environment. A local JSON file
on an ephemeral Render filesystem will be lost on a redeploy or restart.
A free service that cannot attach persistent disks cannot meet the requirement.
Keep exactly one application instance while using this file-backed accounting;
horizontal scaling needs a real transactional database (e.g. PostgreSQL).

Before changing paths, back up the current private data. Existing backup support
is based on `USER_BACKUP_GITHUB_PATH` and private GitHub credentials. Backup
synchronization is additional protection, **not** a replacement for the
durable primary volume. Do not enable automatic deployment for this branch before
verifying that the disk and backup have the expected files.

## Paid number order policy

- At most **three pending rentals** per user simultaneously.
- One rental lasts **180 seconds**; customers cannot cancel it before expiry.
- Deduct the server-defined price when the reservation is made.
- A received SMS within the rental window marks that order completed. **No
  per-SMS balance bonus** is issued.
- If no SMS is recognized before expiry, the reservation price is credited
  back once, with an idempotent status update in the same `users.json` write.
- Failed provider allocation is refunded immediately.
- On restart, pending rentals in `users.json` are reconciled. Live numbers
  within the time window are reconstructed from `active_leases.json`.

The upstream `/getnum` endpoint has no confirmed cancellation/return-to-stock
API, so a local refund does not imply a refund from the external provider.
Legacy rentals started before this branch do not have new journal entries and
are not automatically migrated. Reconcile older orders before deploying.

## Admin-only service visibility

- `/services_admin` in a private Telegram chat lists live upstream service IDs.
- Admin can select each button to show/hide that service.
- Bot and Mini App user catalogues display only visible active services;
  purchase and preview actions enforce the rule server-side.
- Admin sees all upstream-active services.
- Visibility settings are persisted in `system_config.json` and require
  durable storage.

Imported `Green SMS` / `Ivasmsper` forwarding numbers are a **separate**
admin-managed list. This release does not misrepresent them as purchasable or
reservable upstream inventory.

## Manual balance top-ups

- Admin: `/set_topup_card <recipient name and bank transfer details>` in a
  private chat. `/set_topup_card OFF` disables card instructions.
- User: `/topup 5` for a **5.00 AZN** transfer request. User then sends a
  receipt **photo** in private chat.
- Bot stores Telegram's receipt file ID and sends an approve/reject card to
  admins. Pending receipts are available through `/topup_pending`.
- Only a Telegram admin may approve or reject. A request can be approved once;
  both its status and balance credit are saved atomically in `users.json`.
- Verify the transfer in the actual bank account before approving. A
  screenshot is **not proof of payment**.

This is a manual transfer-and-review workflow. It is **not** automated card
acquiring; automated payments require a legitimate processor's integration,
server-validated callback, and merchant onboarding. Never collect CVV, card
PIN, or card expiry in Telegram.

## Smoke tests before switching Render

1. Run `python -m unittest -v test_rental_ledger test_topup_ledger test_service_policy`.
2. Verify admin can hide/show a service, update a card and restart; settings
   remain unchanged.
3. Test 3 rentals, rejection of a fourth, refund on no SMS at 180 seconds,
   and no refund once an SMS is delivered.
4. Approve a synthetic receipt once and verify the second approval does not
   credit again. Check both the user view and the private stored journal.
5. Restart the Render service with an unexpired order and confirm it retains
   the original expiry instead of resetting the 3-minute timer.

External payment and provider tests must use an authorized test account; never
use someone else's verification codes or payment information.
