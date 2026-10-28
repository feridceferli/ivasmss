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
assert.match(js, /renderWhatsappReferrals(data.whatsapp_referrals)/);
assert.match(js, /state.whatsappReferrals?.enabled/);
assert.match(js, /async function copyWhatsappReferralLink/);
assert.match(js, /async function saveWhatsappReferralSettings/);
assert.match(js, /sendAdminToolAction("wa_referral_settings",s*{enabled})/);
assert.match(js, /await api("/api/profile")/);
assert.match(js, /await api("/api/dashboard")/);
assert.match(css, /wa-referral-progress/);
console.log("PASS: WhatsApp-only referral progress/link and admin toggle shown in web and Mini App");
