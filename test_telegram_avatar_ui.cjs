/* Offline Mini App Telegram avatar visual tests.
   All user identities, URL objects and photos are synthetic.
*/
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const html = fs.readFileSync("docs/index.html", "utf8");
const app = fs.readFileSync("docs/app.js", "utf8");
const css = fs.readFileSync("docs/miniapp-modern.css", "utf8");
assert.match(html, /id="user-avatar"/);
assert.match(html, /id="profile-avatar"/);
assert.match(html, /refreshTelegramAvatar\(\)/);
assert.match(html, /app\.js\?v=\d{8}[\w-]+/);
assert.match(css, /\.avatar img,\.profile-avatar img/);
assert.match(app, /"\/api\/avatar"/);
assert.doesNotMatch(app, /api\.telegram\.org\/file\/bot/);
assert.doesNotMatch(app, /\.innerHTML/);

const first = app.indexOf("const telegramAvatarState = {");
const end = app.indexOf("\nasync function fetchDashboard()", first);
assert.ok(first >= 0 && end > first, "Avatar helper must be present in app.js");
const code = app.slice(first, end) + "\nthis.avatarStateForTest = telegramAvatarState;";

function element(tag) {
  return {
    tag,
    textContent: "",
    children: [],
    replaceChildren(...items) {
      this.children = [...items];
      this.textContent = "";
    },
    addEventListener(_kind, callback) {
      this.onError = callback;
    },
  };
}
const top = element("div");
const profile = element("div");
const loads = [];
const revoked = [];
let requests = [];
let photoExists = true;
const sandbox = {
  API_BASE: "https://mock.invalid",
  getAuthHeaders: () => ({"X-Telegram-Init-Data": "signed-session"}),
  document: {
    getElementById: id => id === "user-avatar" ? top :
                                id === "profile-avatar" ? profile : null,
    createElement: element,
  },
  URL: {
    createObjectURL(blob) {
      assert.equal(blob.type, "image/jpeg");
      const url = "blob:mock-" + (loads.length + 1);
      loads.push(url);
      return url;
    },
    revokeObjectURL(url) {revoked.push(url);},
  },
  fetch: async (url, opts) => {
    requests.push({url, opts});
    assert.equal(url, "https://mock.invalid/api/avatar");
    assert.equal(opts.headers["X-Telegram-Init-Data"], "signed-session");
    if (!photoExists) return {ok: false, status: 404};
    return {
      ok: true,
      async blob() {return {type: "image/jpeg", size: 64};},
    };
  },
  toast() {},
  api: async () => ({user: {id: 777, first_name: "Demo"}}),
};
vm.createContext(sandbox);
vm.runInContext(code, sandbox);

(async () => {
  const owner = {id: 777, first_name: "Demo"};
  assert.equal(await sandbox.updateTelegramAvatar(owner), true);
  assert.equal(requests.length, 1);
  assert.equal(top.children.length, 1);
  assert.equal(profile.children.length, 1);
  assert.equal(top.children[0].src, profile.children[0].src);
  assert.equal(top.children[0].alt, "Telegram profil şəkliniz");
  assert.equal(await sandbox.updateTelegramAvatar(owner), true);
  assert.equal(requests.length, 1, "30s dashboard polls must not re-fetch photos");
  assert.equal(await sandbox.updateTelegramAvatar(owner, true), true);
  assert.equal(requests.length, 2, "User-initiated refresh must check photo again");
  assert.deepEqual(revoked, ["blob:mock-1"]);
  photoExists = false;
  assert.equal(await sandbox.updateTelegramAvatar({id: 998, first_name: "Baku"}), false);
  assert.equal(requests.length, 3);
  assert.equal(top.textContent, "B");
  assert.equal(profile.textContent, "B");
  assert.equal(top.children.length, 0);
  assert.equal(profile.children.length, 0);
  assert.ok(!sandbox.avatarStateForTest.objectUrl,
            "Switching identities must release previous photo");
  console.log("PASS: Telegram avatar loaded once per account, duplicated in profile, refreshed and safely reset");
})().catch(error => { console.error(error); process.exitCode = 1; });
