/* Offline regression tests: new active orders first and one-tap copy after allocation.
   Uses fake account numbers only and makes no network calls.
*/
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("docs/app.js", "utf8");

function extract(start, end) {
  const a = source.indexOf(start);
  const b = source.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "Missing JS function: " + start);
  return source.slice(a, b);
}
const code = [
  extract("async function selectService(", "\nasync function copyPhoneNumber("),
  extract("async function copyPhoneNumber(", "\nasync function fetchOrders("),
  extract("async function fetchOrders(", "\nasync function fetchIncomingSms(")
].join("\n");

const feedback = [];
const clipboard = [];
const events = [];
const container = {
  children: [],
  replaceChildren() { this.children = []; },
  appendChild(value) { this.children.push(value); }
};
const sandbox = {
  state: {azApproved: true},
  navigator: {clipboard: {async writeText(text) { clipboard.push(text); }}},
  document: {getElementById() {return container; }},
  alertUser(text) {feedback.push(text);},
  switchTab(tab) {events.push("tab:" + tab);},
  async fetchDashboard() {events.push("dashboard");},
  node(tag, text, klass) {
    return {
      tag, text, klass, children: [],
      appendChild(child) {this.children.push(child);},
      setAttribute() {},
      addEventListener() {}
    };
  },
  clearAndText() {throw new Error("Unexpected empty order list");},
  window: {confirm: () => true},
  api: async (url, opts) => {
    if (url === "/api/get-number") {
      assert.equal(opts.body.range, "447700");
      return {success: true, number: "447700123456"};
    }
    if (url === "/api/orders") return {orders: [
      {id: "old", number: "+447700000001", range: "44", created_at: 100, status: "Aktiv"},
      {id: "new", number: "+447700000002", range: "44", created_at: 300, status: "Aktiv"}
    ]};
    if (url === "/api/dashboard") return {orders: [
      {id: "middle", number: "+447700000003", range: "44", created_at: 200, status: "Aktiv"}
    ]};
    throw new Error("Unexpected API: " + url);
  }
};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);

(async () => {
  await sandbox.selectService("wa", "44", "447700", "GB");
  assert.deepEqual(clipboard, ["+447700123456"],
    "Successful allocation should attempt copying the full +number once");
  assert.ok(feedback.some(s => s.includes("avtomatik kopyalandı")),
    "Success notice should clearly confirm copying");
  await sandbox.fetchOrders();
  const displayed = container.children.map(card => card.children[0]?.text);
  assert.deepEqual(displayed, [
    "+447700000002", "+447700000003", "+447700000001"
  ], "Newest active numbers must be shown first across both APIs");
  assert.ok(source.includes("const combined = [...orders, ...botOrders]"));
  assert.ok(source.includes(".sort((a, b) => createdAt(b) - createdAt(a))"));
  console.log("PASS: automatic copy after number allocation and newest-first active list");
})().catch(err => {console.error(err); process.exitCode = 1;});
