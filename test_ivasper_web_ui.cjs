/* IVASPER browser and Mini App admin panel smoke test: no live provider calls. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const html = fs.readFileSync("docs/index.html", "utf8");
const js = fs.readFileSync("docs/app.js", "utf8");

for (const id of [
  "admin-ivasper-section", "ivasper-status", "ivasper-service-select",
  "ivasper-country-select", "ivasper-range-search", "ivasper-range-list",
  "ivasper-own-active"
]) assert.ok(html.includes('id="' + id + '"'), "Missing admin panel element: " + id);

for (const id of [
  "ivasper-archive-country", "ivasper-archive-summary", "ivasper-archive-list",
  "ivasper-archive-prev", "ivasper-archive-next", "ivasper-archive-pages"
]) assert.ok(html.includes('id="' + id + '"'), "Missing country archive element: " + id);
assert.ok(js.includes("function renderIvasperArchive()"));
assert.ok(js.includes("async function loadIvasperArchivePage(page = 0)"));
assert.ok(js.includes('api("/api/ivasper?country="'));
assert.ok(js.includes("encodeURIComponent(country)"));
assert.ok(js.includes("renderIvasperArchive();"));
assert.ok(js.includes('copy.addEventListener("click", () => copyPhoneNumber(number))'));
const archiveStart = js.indexOf("function renderIvasperArchive()");
const archiveEnd = js.indexOf("let adminUsersCache = []", archiveStart);
assert.ok(archiveStart >= 0 && archiveEnd > archiveStart, "Archive renderer missing");
assert.ok(!js.slice(archiveStart, archiveEnd).includes(".innerHTML"),
  "Archived numbers must be rendered as text nodes, not HTML");

const adminStart = html.indexOf('id="tab-admin"');
const panelStart = html.indexOf('id="admin-ivasper-section"');
assert.ok(adminStart >= 0 && panelStart > adminStart, "IVASPER must remain in protected admin tab");
assert.ok(html.includes("adminJump('admin-ivasper-section')"));
assert.ok(js.includes('loadIvasperAdmin();'), "Admin navigation must load data");
assert.ok(js.includes('api("/api/ivasper")'), "Must use authenticated endpoint");
assert.ok(js.includes('selectService(options.service, options.country || null, options.rid, options.iso || null)'),
  "Range selection must use the existing price and allocation flow");
assert.ok(js.includes('if (state.isAdmin && state.activeTab === "admin") void loadIvasperAdmin();'),
  "Own number list must refresh after allocation");

const start = js.indexOf("// IVASPER: one admin-scoped view");
const end = js.indexOf("let adminUsersCache = [];", start);
assert.ok(start >= 0 && end > start, "Admin code block missing");
const panelCode = js.slice(start, end);
assert.ok(!panelCode.includes(".innerHTML"), "Unsafe provider HTML insertion");
const context = {
  state: {isAdmin: false, services: {}, countries: [], pricing: null},
  document: {
    getElementById() {throw new Error("Non-admin should not access DOM");}
  },
  api() {throw new Error("Non-admin should not access provider");},
  node() {throw new Error("Non-admin should not render");},
  copyPhoneNumber() {},
  selectService() {},
  serviceCountryGroups() {return [];},
  addRangeButton() {},
  clearAndText() {},
  fetchCountries() {},
  fetchPrices() {},
};
vm.createContext(context);
vm.runInContext(panelCode, context);
Promise.resolve(context.loadIvasperAdmin()).then(() => {
  context.renderIvasperRanges();
  context.renderIvasperRangeList();
  context.renderIvasperOwnNumbers();
  console.log("PASS: IVASPER panel only renders with admin flag and reuses existing allocation");
}).catch(error => {console.error(error); process.exitCode = 1;});
