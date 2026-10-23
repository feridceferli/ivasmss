/* Offline world-country diagnostics: no real phone or OTP requests. */
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const js = fs.readFileSync("docs/world-provider-diagnostics.js", "utf8");
const html = fs.readFileSync("docs/index.html", "utf8");
assert.ok(html.includes('id="world-diagnostic-refresh"'));
assert.ok(html.includes('id="world-diagnostic-summary"'));
assert.ok(html.includes('id="world-diagnostic-list"'));
assert.ok(html.includes('id="world-diagnostic-detail"'));
assert.ok(html.includes('src="world-provider-diagnostics.js?v=20261023-world-owner"'));
assert.ok(!/\b(success-otp|getnum|get-number|create_test)\b/.test(js));
assert.ok(!/\b(localStorage|sessionStorage)\b/.test(js));
assert.ok(!js.includes(".innerHTML"));

class FakeNode {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.listeners = {};
    this.textContent = "";
    this.value = "";
    this.hidden = false;
    this.disabled = false;
    this.style = {};
  }
  appendChild(element) {this.children.push(element);return element;}
  replaceChildren(...elements) {this.children = [...elements];}
  addEventListener(name, callback) {
    this.listeners[name] = callback;
  }
  scrollIntoView() {}
}
const controls = new Map([
  "world-diagnostic-refresh", "world-diagnostic-summary",
  "world-diagnostic-list", "world-diagnostic-detail",
  "world-diagnostic-prev", "world-diagnostic-next",
  "world-diagnostic-page", "world-diagnostic-search"
].map(key => [key, new FakeNode(key)]));
const countries = [
  {iso:"AZ",name:"Azerbaijan",flag:"🇦🇿",prefix:"994",count:2,is_shared:false},
  {iso:"US",name:"United States",flag:"🇺🇸",prefix:"1",count:3,is_shared:true},
  {iso:"CA",name:"Canada",flag:"🇨🇦",prefix:"1",count:3,is_shared:true},
  {iso:"BB",name:"Barbados",flag:"🇧🇧",prefix:"1246",count:1,is_shared:false},
  {iso:"GB",name:"United Kingdom",flag:"🇬🇧",prefix:"44",count:1,is_shared:false},
];
const dashboard = {orders:[
  {number:"+994502110123",range:"99450211",remaining_seconds:1200,created_at:200},
  {number:"+994502110123",range:"99450211",remaining_seconds:1200,created_at:100},
  {number:"+12465550123",range:"1246",remaining_seconds:1500,created_at:300},
  {number:"+15551234567",range:"1",remaining_seconds:2000,created_at:400},
  {number:"+447700123456",range:"44",remaining_seconds:0,created_at:500},
  {number_masked:"+44770***",remaining_seconds:3000},
  {number:"+994552110111",remaining_seconds:2000,created_at:200},
]};
const calls=[];
const fakeFetch = async (url, options) => {
  calls.push({url, options});
  assert.equal(options.headers["X-Telegram-Init-Data"],"test-session");
  const data = url.endsWith("/api/countries") ?
    {countries,available_countries:5,total:5} :
    url.includes("/api/countries?iso=") ?
    {country:{ranges:[{rid:"99450211",service:"wa"}]}} :
    url.endsWith("/api/dashboard") ? dashboard : null;
  assert.ok(data,"Unexpected endpoint "+url);
  return {ok:true,async json(){return data;}};
};
const sandbox = {
  window:{Telegram:{WebApp:{initData:"test-session"}}},
  document:{
    readyState:"complete",
    getElementById(id){return controls.get(id) || null;},
    createElement(tag){return new FakeNode(tag);}
  },
  navigator:{clipboard:{async writeText() {}}},
  fetch:fakeFetch,
};
vm.createContext(sandbox);
vm.runInContext(js,sandbox);
function flatten(el) {
  return [el.textContent,...el.children.map(flatten)].join(" ");
}
(async()=>{
  assert.equal(typeof sandbox.window.refreshWorldProviderDiagnostics,"function");
  await sandbox.window.refreshWorldProviderDiagnostics();
  assert.equal(calls.length,2,"Only world directory and owned dashboard fetched initially");
  assert.ok(calls.some(x=>x.url.endsWith("/api/countries")));
  assert.ok(calls.some(x=>x.url.endsWith("/api/dashboard")));
  assert.ok(flatten(controls.get("world-diagnostic-summary")).includes(
    "3 fərqli aktiv nömrəm var") === false,
    "Number of owned active numbers should count unique valid numbers including 2 AZ, Barbados, +1"
  );
  assert.ok(flatten(controls.get("world-diagnostic-summary")).includes(
    "4 fərqli aktiv nömrəm var"));
  let countryButtons=controls.get("world-diagnostic-list").children;
  assert.equal(countryButtons.length,5);
  const barbados=countryButtons.find(b=>flatten(b).includes("Barbados"));
  assert.ok(barbados);
  assert.ok(flatten(barbados).includes("📱 1"),
    "Longest match +1246 must be grouped as Barbados, not +1");
  const us=countryButtons.find(b=>flatten(b).includes("United States"));
  assert.ok(flatten(us).includes("📱 1"));
  const canada=countryButtons.find(b=>flatten(b).includes("Canada"));
  assert.ok(flatten(canada).includes("📱 1"),
    "Shared code gets shared label, not a claim of location");

  const azerbaijan=countryButtons.find(b=>flatten(b).includes("Azerbaijan"));
  assert.ok(flatten(azerbaijan).includes("📱 2"));
  await azerbaijan.listeners.click();
  let detail=flatten(controls.get("world-diagnostic-detail"));
  assert.ok(detail.includes("+994502110123"));
  assert.ok(detail.includes("+994552110111"));
  assert.ok(!detail.includes("99450***"));
  assert.ok(!detail.includes("+447700123456"));
  assert.ok(calls.some(x=>x.url.endsWith("/api/countries?iso=AZ")));

  controls.get("world-diagnostic-search").value="Barbados";
  controls.get("world-diagnostic-search").listeners.input();
  countryButtons=controls.get("world-diagnostic-list").children;
  assert.equal(countryButtons.length,1);
  assert.ok(flatten(countryButtons[0]).includes("Barbados"));
  console.log("PASS: world-country range discovery and owner-only active numbers");
})().catch(e=>{console.error(e);process.exitCode=1});
