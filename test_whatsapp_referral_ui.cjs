/* Confirm WhatsApp referral widget and server-facing controls in BOTH clients. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const html = fs.readFileSync("docs/index.html", "utf8");
const js = fs.readFileSync("docs/app.js", "utf8");
const css = fs.readFileSync("docs/whatsapp-referrals.css", "utf8");
for (const id of [
  "wa-referral-card", "wa-referral-status", "wa-referral-progress-bar",
  "wa-referral-link", "admin-wa-referral-enabled", "admin-wa-referral-status",
  "wa-referral-service-info", "admin-wa-referral-section"
]) assert.ok(html.includes('id="' + id + '"'), "Missing control: " + id);

assert.match(html, /whatsapp-referrals.css/);
assert.ok(js.includes("renderWhatsappReferrals(data.whatsapp_referrals)"));
assert.ok(js.includes("state.whatsappReferrals?.enabled"));
assert.ok(js.includes("async function copyWhatsappReferralLink"));
assert.ok(js.includes("async function saveWhatsappReferralSettings"));
assert.ok(js.includes('sendAdminToolAction("wa_referral_settings", {enabled})'));
assert.ok(js.includes('await api("/api/profile")'));
assert.ok(js.includes('await api("/api/dashboard")'));
assert.match(css, /wa-referral-progress/);
console.log("PASS: WhatsApp-only referral progress/link and admin toggle shown in web and Mini App");
