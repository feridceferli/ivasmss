/* Offline smoke test for service → country → range selection.
   No real API allocation, Telegram contact or external network calls.
*/
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const js = fs.readFileSync("docs/app.js", "utf8");
const html = fs.readFileSync("docs/index.html", "utf8");
const start = js.indexOf("function serviceCountryGroups(service) {");
const end = js.indexOf("\nasync function showServiceRanges", start);
assert.ok(start >= 0 && end > start, "Country grouping function must be present");
const pureFunction = js.slice(start, end);

const context = {
    state: {
        countries: [
            {iso: "AZ", prefix: "994", flag: "🇦🇿", name: "Azerbaijan"},
            {iso: "US", prefix: "1", flag: "🇺🇸", name: "United States"},
            {iso: "CA", prefix: "1", flag: "🇨🇦", name: "Canada"},
            {iso: "BB", prefix: "1246", flag: "🇧🇧", name: "Barbados"},
            {iso: "GB", prefix: "44", flag: "🇬🇧", name: "United Kingdom"}
        ],
        services: {
            wa: ["99450211", "99450211", "1202444", "1246123", "447700"],
            tg: []
        }
    }
};

const groups = vm.runInNewContext(pureFunction + '\nserviceCountryGroups("wa");', context);
const byCode = Object.fromEntries(groups.map(item => [item.code, item]));
assert.equal(groups.length, 4);
assert.equal(byCode["994"].items.length, 1, "Duplicate API ranges must not appear twice");
assert.equal(byCode["994"].iso, "AZ");
assert.equal(byCode["1"].shared, true, "Shared international calling codes must be marked");
assert.equal(byCode["1"].iso, null, "Do not invent one country for a shared calling code");
assert.equal(byCode["1246"].iso, "BB", "Match the longest specific dial prefix");
assert.equal(byCode["44"].iso, "GB");
assert.equal(vm.runInNewContext(pureFunction + '\nserviceCountryGroups("tg");', context).length, 0);

assert.match(html, /id="service-detail"/, "Service picker must have a real HTML container");
assert.match(html, /id="country-az-pricing"/);
assert.match(html, /href="https:\/\/t\.me\/lacin_0041"/);
assert.match(html, /10 AZN/);
assert.match(js, /addRangeButton\(listing, "📞 \+" \+ rid \+ " — Nömrə al"/);
assert.match(js, /body: \{ service, country, range, country_iso: countryIso \}/);
assert.match(js, /window\.confirm\([\s\S]*?10 AZN/);
assert.match(js, /if \(locked\)/);
assert.ok(!js.includes(".innerHTML"), "Untrusted provider data must not go into innerHTML");

console.log("PASS: service selection, country code matching, range buttons, +994 pricing, contact and access guards");
