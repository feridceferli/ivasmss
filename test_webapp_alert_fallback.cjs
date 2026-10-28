/* Browser regression: Telegram SDK can exist but showAlert throws
   WebAppMethodUnsupported. A successful server allocation must stay successful. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("docs/app.js", "utf8");

function extract(start, end) {
  const a = source.indexOf(start);
  const b = source.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, "Missing source function: " + start);
  return source.slice(a, b);
}
const code = [
  extract("let uiToastTimeout = null;", "\nfunction getAuthHeaders()"),
  extract("let pendingNumberSelection = null;", "\nasync function copyPhoneNumber(")
].join("\n");

function setup(telegramInitData, opts = {}) {
  const alerts = [];
  const network = [];
  const button = {disabled: false};
  const overlay = {hidden: false};
  const toast = {textContent: "", className: ""};
  const fakeWindow = {
    setTimeout() {return 1;},
    clearTimeout() {},
    alert(message) {alerts.push("native:" + message)}
  };
  const tg = {
    initData: telegramInitData,
    showAlert() {alerts.push("telegram"); throw new Error("WebAppMethodUnsupported");}
  };
  const context = {
    tg, window: fakeWindow,
    Date, Promise,
    document: {
      getElementById(id) {
        if (id === "ui-toast") return toast;
        if (id === "number-choices-overlay") return overlay;
        return null;
      },
      querySelectorAll() {return [button]},
    },
    api: async (path, options) => {
      assert.equal(path, "/api/get-number");
      assert.equal(options.body.mode, "select");
      network.push(options.body.choice_index);
      if (opts.failServer) throw new Error("No allocation");
      return {success: true, number: "+4915212515209"};
    },
    async copyPhoneNumber() {
      if (opts.failCopy) throw new Error("clipboard not supported");
      return true;
    },
    switchTab() {
      if (opts.failNavigation) throw new Error("navigation failed");
    },
    async fetchOrders() {if (opts.failRefresh) throw new Error("refresh unavailable");},
    async fetchDashboard() {if (opts.failRefresh) throw new Error("refresh unavailable");},
    node() {return {}},
  };
  vm.createContext(context);
  vm.runInContext(code, context);
  vm.runInContext("pendingNumberSelection = {token:'testtoken',priceCents:0,expiresAt:Date.now()+90000}", context);
  return {context, alerts, network, toast, button, overlay};
}

(async () => {
  {
    const x = setup("");
    x.context.alertUser("✅ Sifariş aktivləşdirildi");
    assert.ok(x.toast.textContent.includes("Sifariş aktivləşdirildi"));
    assert.equal(x.alerts.length, 0, "Website must never call Telegram showAlert");
  }
  {
    const x = setup("auth-data-from-telegram");
    assert.doesNotThrow(() => x.context.alertUser("✅ Seçim təsdiqləndi"));
    assert.deepEqual(x.alerts, ["telegram"], "Unsupported Telegram alert is safely caught");
    assert.ok(x.toast.textContent.includes("Seçim təsdiqləndi"));
  }
  {
    const x = setup("", {failCopy: true, failRefresh: true});
    await x.context.selectOfferedNumber(0);
    assert.deepEqual(x.network, [0]);
    assert.equal(x.overlay.hidden, true, "Completed selection overlay closes");
    assert.match(x.toast.textContent, /✅ Seçdiyiniz nömrə aktivləşdirildi/);
    assert.doesNotMatch(x.toast.textContent, /Seçim alınmadı/);
  }
  {
    const x = setup("auth-data-from-telegram", {failNavigation: true});
    await x.context.selectOfferedNumber(2);
    assert.deepEqual(x.network, [2]);
    assert.match(x.toast.textContent, /✅ Seçdiyiniz nömrə aktivləşdirildi/);
    assert.doesNotMatch(x.toast.textContent, /Seçim alınmadı/);
  }
  {
    const x = setup("", {failServer: true});
    await x.context.selectOfferedNumber(1);
    assert.equal(x.overlay.hidden, false, "Failed API choice is not closed");
    assert.equal(x.button.disabled, false, "Failed choice buttons re-enable");
    assert.match(x.toast.textContent, /Seçim alınmadı: No allocation/);
  }
  console.log("PASS: browser-safe alerts, confirmed selection and optional UI failure isolation");
})().catch(e => {console.error(e); process.exitCode = 1});
