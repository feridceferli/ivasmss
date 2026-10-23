/* Read-only +994 diagnostics smoke tests. Does not fetch SMS or private data. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const js = fs.readFileSync("docs/az-provider-diagnostics.js", "utf8");
const html = fs.readFileSync("docs/index.html", "utf8");
assert.ok(html.includes('id="az-provider-refresh"'));
assert.ok(html.includes('id="az-provider-diagnostics"'));
assert.ok(html.includes('src="az-provider-diagnostics.js?v=20261023-check"'));
assert.equal(/\bsuccess-otp\b|\bgetnum\b|\bget-number\b/.test(js), false,
    "The read-only diagnostic must not call allocation or OTP APIs");
assert.equal(/\b(localStorage|sessionStorage)\b/.test(js), false,
    "The diagnostic must not persist private data");
assert.ok(js.includes('"/api/services"'));
assert.ok(js.includes('X-Telegram-Init-Data'));
assert.ok(js.includes("HTTP 200"));
assert.ok(js.includes("99440") && js.includes("99444"));
const sandbox = {
  window: {Telegram: {WebApp: {initData: ""}}},
  document: {getElementById() { return null; }, createElement() { return {}; }},
  fetch() { throw new Error("must not be called without user click"); },
};
vm.createContext(sandbox);
vm.runInContext(js, sandbox);
assert.equal(typeof sandbox.window.refreshAzProviderDiagnostics, "function");
console.log("PASS +994 provider diagnostics: read-only, protected and manually triggered.");
