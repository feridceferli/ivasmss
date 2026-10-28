/* Website styling/navigating stays out of Telegram Mini App.
   All assertions are offline and do not access user accounts or provider APIs. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const html = fs.readFileSync("docs/index.html", "utf8");
const css = fs.readFileSync("docs/website-desktop.css", "utf8");
const siteJs = fs.readFileSync("docs/website-desktop.js", "utf8");
const miniCss = fs.readFileSync("docs/miniapp-modern.css", "utf8");
const miniJs = fs.readFileSync("docs/app.js", "utf8");

assert.match(html, /<link rel="stylesheet" href="miniapp-modern\.css/);
assert.match(html, /<link rel="stylesheet" href="website-desktop\.css/);
assert.match(html, /<script src="website-desktop\.js/);
assert.match(html, /<div id="website-navigation" class="tabs"/);
assert.match(html, /id="site-menu-toggle"/);
assert.match(html, /id="site-current-title"/);
assert.match(html, /if \(!window\.Telegram\?\.WebApp\?\.initData\)/);
assert.match(css, /html\.site-mode \.tabs/);
assert.match(css, /html\.site-mode \.services-grid/);
assert.match(css, /@media \(max-width:1000px\)/);
assert.match(css, /html\.site-mode\.site-nav-open/);
assert.match(siteJs, /classList\.contains\("site-mode"\)/);
assert.ok(!miniCss.includes("site-mode"), "Original Mini App styles were not changed");
assert.ok(!miniJs.includes("websiteDesktop"), "Original Mini App logic is untouched");

function fakeClassList(initial = []) {
  const entries = new Set(initial);
  return {
    contains(name) {return entries.has(name);},
    add(name) {entries.add(name);},
    remove(name) {entries.delete(name);},
    toggle(name) {
      if (entries.has(name)) {entries.delete(name); return false;}
      entries.add(name); return true;
    }
  };
}

function makeDocument(standalone) {
  const nodes = {
    "site-menu-toggle": {
      attributes: {},
      setAttribute(name, value) {this.attributes[name] = value;},
      addEventListener(name, fn) {this[name] = fn;}
    },
    "site-local-date": {textContent: ""},
    "site-current-title": {textContent: ""},
    "site-current-subtitle": {textContent: ""},
    "site-nav-backdrop": {addEventListener(name, fn) {this[name] = fn;}},
    "tab-services": {classList: fakeClassList(["active"])},
    "tab-active": {classList: fakeClassList()},
    "service-search": {focus() {}}
  };
  const callbacks = {};
  const doc = {
    title: "",
    documentElement: {classList: fakeClassList(standalone ? ["site-mode"] : [])},
    addEventListener(event, callback) {callbacks[event] = callback;},
    getElementById(id) {return nodes[id] || null;},
    querySelector(selector) {
      if (selector === ".app-brand-caption") {
        return {replaceChildren() {}};
      }
      return null;
    },
    querySelectorAll() {return []},
    createTextNode(text) {return {text}}
  };
  return {doc, callbacks, nodes};
}

{
  const {doc, callbacks} = makeDocument(false);
  const win = {switchTab() {}};
  const original = win.switchTab;
  vm.runInNewContext(siteJs, {window: win, document: doc});
  assert.equal(win.switchTab, original, "Telegram switchTab remains untouched");
  assert.equal(Object.keys(callbacks).length, 0, "No website listeners in Mini App");
  assert.equal(win.websiteDesktop, undefined);
}
{
  const {doc, callbacks, nodes} = makeDocument(true);
  const win = {
    switchTab(tab) {
      nodes["tab-services"].classList.remove("active");
      if (tab === "active") nodes["tab-active"].classList.add("active");
    },
  };
  vm.runInNewContext(siteJs, {window: win, document: doc});
  assert.ok(callbacks.DOMContentLoaded, "Standalone desktop enhancements load");
  callbacks.DOMContentLoaded();
  assert.match(nodes["site-local-date"].textContent, /\d{4}/);
  win.switchTab("active");
  assert.equal(nodes["site-current-title"].textContent, "Aktiv nömrələr");
  win.websiteDesktop.toggleNav();
  assert.equal(doc.documentElement.classList.contains("site-nav-open"), true);
  assert.equal(nodes["site-menu-toggle"].attributes["aria-expanded"], "true");
  win.websiteDesktop.closeNav();
  assert.equal(doc.documentElement.classList.contains("site-nav-open"), false);
}
console.log("PASS: standalone desktop navigation, mobile menu, and zero Mini App impact");
