/* IVASPER browser/Mini App isolation smoke test (no real API calls). */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const html = fs.readFileSync("docs/index.html", "utf8");
const js = fs.readFileSync("docs/app.js", "utf8");

for (const id of [
  "admin-ivasper-section", "ivasper-status", "ivasper-country-filter",
  "ivasper-service-filter", "ivasper-number-filter", "ivasper-number-count",
  "ivasper-number-list", "ivasper-import-country", "ivasper-import-service",
  "ivasper-import-numbers", "ivasper-import-status"
]) assert.ok(html.includes('id="' + id + '"'), "Missing IVASPER UI id " + id);
const admin = html.indexOf('id="tab-admin"');
const panel = html.indexOf('id="admin-ivasper-section"');
assert.ok(admin >= 0 && panel > admin, "IVASPER must remain admin-only");
assert.ok(js.includes('api("/api/ivasper")'), "Dedicated inventory endpoint required");
assert.ok(js.includes('async function saveIvasperNumbers()'), "Simple admin number submission is missing");
assert.ok(js.includes('method: "POST", body: {numbers, service, country}'), "IVASPER submission must use authorized POST");
const start = js.indexOf("// IVASPER has a different, read-only inventory source");
const end = js.indexOf("let adminUsersCache = [];", start);
assert.ok(start > 0 && end > start, "Dedicated IVASPER browser functions missing");
const dedicated = js.slice(start, end);
assert.ok(!dedicated.includes(".innerHTML"), "Inventory values must render as text");
for (const prohibited of ["state.services =", "selectService(", 'api("/api/get-number")',
                          "fetchCountries()", "fetchPrices()", "number_archive",
                          "renderIvasperOwnNumbers", "loadIvasperArchivePage"]) {
  assert.ok(!dedicated.includes(prohibited), "IVASPER must not mix with IVASMS: " + prohibited);
}
const context = {
  state: {isAdmin: false}, document: {
    getElementById() {throw Error("Non-admin must not touch DOM");}
  }, api() {throw Error("Non-admin must not touch provider");},
  node() {}, copyPhoneNumber() {}, clearAndText() {}
};
vm.createContext(context);
vm.runInContext(dedicated, context);
Promise.resolve(context.loadIvasperAdmin()).then(() => {
  context.renderIvasperNumbers();
  context.saveIvasperNumbers();
  console.log("PASS: IVASPER is separate and admin-only for both viewing and receiving stock");
}).catch(e => {console.error(e); process.exitCode = 1;});
