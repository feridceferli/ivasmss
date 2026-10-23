/* Offline +994 operator and owner-active-number diagnostics tests.
   No real phone/SMS/OTP request is made in this test.
*/
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const js = fs.readFileSync("docs/az-provider-diagnostics.js", "utf8");
const html = fs.readFileSync("docs/index.html", "utf8");
assert.ok(html.includes('id="az-provider-refresh"'));
assert.ok(html.includes('id="az-provider-diagnostics"'));
assert.ok(html.includes('src="az-provider-diagnostics.js?v=20261023-operator-status"'));
assert.equal(/\bsuccess-otp\b|\bgetnum\b|\bget-number\b/.test(js), false,
    "Read-only diagnostic must never call number allocation or SMS/OTP APIs");
assert.equal(/\b(localStorage|sessionStorage)\b/.test(js), false,
    "Diagnostic must not save private data locally");
assert.ok(js.includes('"/api/services"'));
assert.ok(js.includes('"/api/dashboard"'));
assert.ok(js.includes('X-Telegram-Init-Data'));
assert.ok(js.includes("99440") && js.includes("99444"));

class FakeNode {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.textContent = "";
    this.events = [];
    this.disabled = false;
  }
  appendChild(value) { this.children.push(value); return value; }
  replaceChildren(...values) { this.children = values; }
  addEventListener(name, callback) { this.events.push({name, callback}); }
}
const panel = new FakeNode("div");
const button = new FakeNode("button");
let calls = [];
const services = {
  wa: ["99450210", "99455211", "99440210", "99444211", "99470210"],
  tg: ["99451211", "99499210", "99460211", "99477210", "99410211"],
};
const dashboard = {orders: [
  {number: "+994502110123", range: "99450211", remaining_seconds: 2500},
  {number: "+994402100456", range: "99440210", remaining_seconds: 1200},
  {number: "+994442110789", range: "99444211", remaining_seconds: 3500},
  {number: "+994552110234", range: "99455211", remaining_seconds: 0},
  {number_masked: "+99450***", remaining_seconds: 3000},
  {number: "+447700123456", remaining_seconds: 1200},
  {number: "+994402100456", remaining_seconds: 1000}
]};
const sandbox = {
  window: {Telegram: {WebApp: {initData: "mock-verified-session"}}},
  document: {
    getElementById(id) {
      return id === "az-provider-diagnostics" ? panel :
             id === "az-provider-refresh" ? button : null;
    },
    createElement: tag => new FakeNode(tag)
  },
  navigator: {clipboard: {writeText: async () => {}}},
  fetch: async (url, options) => {
    calls.push({url, options});
    const data = url.endsWith("/api/services") ? {services} :
                 url.endsWith("/api/dashboard") ? dashboard : null;
    assert.ok(data, "Unexpected external endpoint called: " + url);
    return {ok: true, status: 200, async json() {return data;}};
  }
};
vm.createContext(sandbox);
vm.runInContext(js, sandbox);

function textContent(root) {
  return [root.textContent, ...root.children.map(textContent)].join(" ");
}
(async () => {
  assert.equal(typeof sandbox.window.refreshAzProviderDiagnostics, "function");
  await sandbox.window.refreshAzProviderDiagnostics();
  assert.equal(button.disabled, false);
  assert.equal(calls.length, 2, "Only services and own dashboard should be requested");
  assert.ok(calls.every(x => x.options.headers["X-Telegram-Init-Data"] ===
    "mock-verified-session"));
  assert.ok(calls.some(x => x.url.endsWith("/api/services")));
  assert.ok(calls.some(x => x.url.endsWith("/api/dashboard")));

  const allText = textContent(panel);
  for (const op of ["Bakcell", "Azercell", "Nar", "Naxtell", "Catel", "CDMA"]) {
    assert.ok(allText.includes(op), "Missing operator " + op);
  }
  assert.ok(allText.includes("10 fərqli +994 range"));
  assert.ok(allText.includes("Mənim aktiv nömrələrim: 3"));
  assert.ok(allText.includes("+994502110123"));
  assert.ok(allText.includes("+994402100456"));
  assert.ok(allText.includes("+994442110789"));
  assert.ok(!allText.includes("+994552110234"), "Expired number must not be listed");
  assert.ok(!allText.includes("+447700123456"), "Foreign country must be excluded");
  assert.ok(!allText.includes("+99450***"), "Masked number must not be inferred");
  assert.ok(allText.includes("SMS/OTP"), "Must warn that catalog listing is not delivery");
  console.log("PASS: six +994 operator summaries, owner-active numbers, read-only API");
})().catch(err => {console.error(err); process.exitCode = 1;});
