/* AZE SMS PANEL Mini App — Telegram-verified, mobile-first interface.
   All country/range metadata comes from the same Render backend as the bot.
   No referral gate, no invented stock, no secrets in the browser.
*/
const tg = window.Telegram.WebApp;
tg.expand();

const API_BASE = "https://ivasmss.onrender.com";
const TABS = ["services", "countries", "azerbaijan", "active", "history", "twofa", "leaderboard", "profile", "admin"];
const state = {
    activeTab: "services",
    services: {},
    azCatalog: [],
    azApproved: false,
    isAdmin: false,
    countries: [],
    countryFilter: "",
    countryPage: 0,
    countryPageSize: 25,
    authFailed: false
};

function node(tag, text = "", className = "") {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== null) item.textContent = String(text);
    return item;
}

function clearAndText(target, text) {
    target.replaceChildren(node("p", text, "notice-mini"));
}

function alertUser(message) {
    if (tg.showAlert) tg.showAlert(String(message));
    else window.alert(String(message));
}

function getAuthHeaders() {
    return {
        "X-Telegram-Init-Data": tg.initData || "",
        "Content-Type": "application/json"
    };
}

async function api(path, options = {}) {
    const res = await fetch(API_BASE + path, {
        method: options.method || "GET",
        headers: getAuthHeaders(),
        ...(options.body ? { body: JSON.stringify(options.body) } : {})
    });
    let data = {};
    try { data = await res.json(); } catch (_) { /* unavailable */ }
    if (!res.ok) {
        if (res.status === 401) state.authFailed = true;
        throw new Error(data.message || ({
            unauthorized: "Mini App-i Telegram botunun içindən açın.",
            banned: "Hesab məhdudlaşdırılıb.",
            admin_approval_required: "Azərbaycan nömrələri üçün admin icazəsi lazımdır.",
            invalid_catalog_range: "Bu range mövcud siyahıda yoxdur.",
            range_unavailable: "Bu range artıq API siyahısında yoxdur.",
            service_unavailable: "Bu xidmət mövcud deyil.",
            country_mismatch: "Ölkə və range uyğun gəlmir."
        }[data.error] || "Server xətası: " + res.status));
    }
    return data;
}

function setStatus(message) {
    const strip = document.getElementById("status-strip");
    if (strip) strip.textContent = message;
}

function switchTab(tab) {
    if (!TABS.includes(tab) || (tab === "admin" && !state.isAdmin)) return;
    state.activeTab = tab;
    document.querySelectorAll(".tab-content").forEach(content => {
        content.classList.toggle("active", content.id === "tab-" + tab);
    });
    document.querySelectorAll(".tab-btn").forEach((button, index) => {
        button.classList.toggle("active", TABS[index] === tab);
    });
    if (tab === "countries") {
        if (!state.countries.length) fetchCountries();
        else renderCountries();
    } else if (tab === "azerbaijan") {
        renderAzOperators();
    } else if (tab === "active") {
        fetchOrders();
    } else if (tab === "history") {
        fetchIncomingSms();
    } else if (tab === "twofa") {
        document.getElementById("totp-output").textContent = "— — — — — —";
        document.getElementById("totp-secret").value = "";
        lastLocal2faCode = "";
    } else if (tab === "leaderboard") {
        fetchLeaderboard();
    } else if (tab === "profile") {
        fetchProfile();
    } else if (tab === "admin") {
        fetchAdminUsers();
    }
}

async function fetchDashboard() {
    try {
        const data = await api("/api/dashboard");
        const user = data.user || {};
        document.getElementById("user-name").textContent = user.first_name || "İstifadəçi";
        document.getElementById("user-id").textContent = "ID: " + (user.id || "—");
        document.getElementById("user-balance").textContent = (data.balance || "0.00") + " AZN";
        const avatar = document.getElementById("user-avatar");
        avatar.textContent = (user.first_name || "İ").slice(0, 1).toUpperCase();
        state.isAdmin = !!user.is_admin;
        state.azApproved = !!user.az_approved;
        const adminButton = document.getElementById("admin-tab-button");
        adminButton.hidden = !state.isAdmin;
        document.getElementById("tab-admin").hidden = !state.isAdmin;
        const stats = data.stats || {};
        setStatus("🌍 Bütün ölkələr  ·  Bu gün: " + (stats.today_numbers || 0) +
                  " nömrə  ·  " + (state.isAdmin ? "👑 Admin" : "🔐 Təhlükəsiz giriş"));
        updatePermissionStatus();
        return data;
    } catch (err) {
        setStatus(state.authFailed
            ? "⚠️ Mini App-i Telegram botundan açın."
            : "⚠️ Profil yenilənmədi: " + err.message);
        return null;
    }
}

function updatePermissionStatus() {
    const status = document.getElementById("permission-status");
    const button = document.getElementById("request-az-access");
    if (!status || !button) return;
    status.textContent = state.azApproved
        ? "✅ +994 istifadə icazəniz var. Nömrə mövcudluğu API-dən asılıdır."
        : "🔒 +994 nömrələri üçün admin təsdiqi lazımdır. Sorğunu buradan göndərə bilərsiniz.";
    button.hidden = state.azApproved;
}

async function requestAzPermission() {
    const button = document.getElementById("request-az-access");
    button.disabled = true;
    try {
        const res = await api("/api/az-access", { method: "POST", body: {} });
        alertUser(res.message || "Sorğu göndərildi.");
        if (res.approved) state.azApproved = true;
        updatePermissionStatus();
    } catch (err) { alertUser(err.message); }
    finally { button.disabled = false; }
}

function addRangeButton(container, label, options) {
    const button = node("button", label, "catalog-row catalog-range");
    button.type = "button";
    const locked = options.isAz && !state.azApproved;
    if (locked) button.title = "Admin təsdiqi tələb olunur";
    button.addEventListener("click", () => {
        if (locked) {
            alertUser("🔒 Azərbaycan +994 üçün admin təsdiqi lazımdır. 🇦🇿 bölməsində icazə istəyə bilərsiniz.");
            switchTab("azerbaijan");
            return;
        }
        selectService(options.service, options.country || null, options.rid, options.iso || null);
    });
    container.appendChild(button);
    return button;
}

async function fetchServices() {
    const container = document.getElementById("services-grid-container");
    try {
        const data = await api("/api/services");
        state.services = data.services || {};
        state.azCatalog = data.az_catalog || [];
        state.azApproved = !!data.az_approved;
        updatePermissionStatus();
        renderServices();
        if (state.activeTab === "azerbaijan") renderAzOperators();
    } catch (err) {
        clearAndText(container, "Xidmətləri yükləmək mümkün olmadı. " + err.message);
    }
}

function renderServices() {
    const container = document.getElementById("services-grid-container");
    container.replaceChildren();
    const services = Object.keys(state.services).sort();
    if (!services.length) {
        clearAndText(container, "API hazırda heç bir xidmət göstərmir.");
        return;
    }
    services.forEach(service => {
        const offered = Array.isArray(state.services[service]) ? state.services[service] : [];
        const b = node("button", "📡 " + service.toUpperCase() + "  ·  " +
                       offered.length + " range", "service-card");
        b.type = "button";
        b.addEventListener("click", () => showServiceRanges(service));
        container.appendChild(b);
    });
}

function showServiceRanges(service) {
    const parent = document.getElementById("service-detail");
    if (!parent) return;
    parent.replaceChildren();
    parent.hidden = false;
    parent.appendChild(node("h4", "📡 " + service.toUpperCase() + " — API range-ləri"));
    parent.appendChild(node("p", "İstifadə etmək üçün konkret range seçin. " +
        "Siyahıda olması aktiv nömrəyə zəmanət vermir.", "notice-mini"));
    const area = node("div", "", "catalog-scroll");
    parent.appendChild(area);
    const ranges = state.services[service] || [];
    const unique = [...new Set(ranges.map(r => String(r).replace(/\D/g, "")))]
        .filter(r => /^\d{1,10}$/.test(r));
    if (!unique.length) clearAndText(area, "Uyğun range yoxdur.");
    for (const rid of unique) {
        addRangeButton(area, rid + (rid.startsWith("994") && !state.azApproved ? " 🔒" : ""),
            { service, rid, isAz: rid.startsWith("994") });
    }
    const back = node("button", "✕ Bağla", "action-small");
    back.addEventListener("click", () => { parent.hidden = true; });
    parent.appendChild(back);
    parent.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
}

function renderAzOperators() {
    const host = document.getElementById("az-operators-list");
    host.replaceChildren();
    updatePermissionStatus();
    if (!state.azCatalog.length) {
        clearAndText(host, "Operator kataloqu yüklənir...");
        return;
    }
    for (const op of state.azCatalog) {
        const group = node("details", null, "operator-group");
        const summary = node("summary", "📶 " + op.name);
        group.appendChild(summary);
        let count = 0;
        for (const prefix of (op.prefixes || [])) {
            const section = node("details", null, "operator-prefix");
            section.appendChild(node("summary", "+" + prefix.prefix +
                " · " + (prefix.ranges || []).length + " range"));
            const area = node("div");
            for (const entry of (prefix.ranges || [])) {
                count++;
                const listed = entry.listed_in_api ? "📡 API" : "❔ Təsdiqlənməyib";
                addRangeButton(area, entry.rid + " · " + listed +
                    (state.azApproved ? "" : " 🔒"),
                    { service: "az", country: "994", rid: entry.rid, isAz: true });
            }
            section.appendChild(area);
            group.appendChild(section);
        }
        summary.textContent += " · " + count + " range" + (state.azApproved ? "" : " 🔒");
        host.appendChild(group);
    }
}

async function fetchCountries() {
    try {
        const data = await api("/api/countries");
        state.countries = data.countries || [];
        state.azApproved = !!data.az_approved;
        document.getElementById("countries-summary").textContent =
            state.countries.length + " ölkə və ərazi · " +
            (data.available_countries || 0) + " ölkədə API range-ləri var. " +
            "0 = hazırda range göstərilmir.";
        updatePermissionStatus();
        renderCountries();
    } catch (err) {
        clearAndText(document.getElementById("countries-list"), err.message);
    }
}

function renderCountries() {
    const host = document.getElementById("countries-list");
    host.replaceChildren();
    const term = state.countryFilter;
    const matches = state.countries.filter(c =>
        String(c.name).toLocaleLowerCase().includes(term) ||
        String(c.prefix).includes(term.replace(/^\+/, "")) ||
        String(c.iso).toLocaleLowerCase().includes(term));
    const size = state.countryPageSize;
    const pages = Math.max(1, Math.ceil(matches.length / size));
    state.countryPage = Math.max(0, Math.min(state.countryPage, pages - 1));
    if (!matches.length) clearAndText(host, "Bu axtarışa uyğun ölkə tapılmadı.");
    matches.slice(state.countryPage * size, (state.countryPage + 1) * size).forEach(c => {
        const b = node("button", null, "catalog-row");
        b.type = "button";
        b.appendChild(node("span", c.flag + " " + c.name + " (+" + c.prefix + ")"));
        b.appendChild(node("small", (c.count || 0) + " range"));
        b.addEventListener("click", () => openCountry(c.iso));
        host.appendChild(b);
    });
    document.getElementById("countries-page").textContent =
        (state.countryPage + 1) + " / " + pages;
    document.getElementById("countries-prev").disabled = state.countryPage === 0;
    document.getElementById("countries-next").disabled = state.countryPage >= pages - 1;
}

function changeCountryPage(delta) {
    state.countryPage += delta;
    renderCountries();
}

function closeCountryDetails() {
    document.getElementById("country-details").hidden = true;
}

async function openCountry(iso) {
    const box = document.getElementById("country-details");
    box.hidden = false;
    const list = document.getElementById("country-range-list");
    clearAndText(list, "Range-lər yüklənir...");
    try {
        const data = await api("/api/countries?iso=" + encodeURIComponent(iso));
        const c = data.country;
        state.azApproved = !!data.az_approved;
        document.getElementById("country-detail-heading").textContent =
            c.flag + " " + c.name + " (+" + c.prefix + ")";
        document.getElementById("country-detail-hint").textContent =
            c.is_shared ? "⚠️ Bu telefon kodunu birdən çox ölkə paylaşır; API konkret ölkəni təsdiqləmir."
            : "Burada yalnız API-də göstərilən range-lər var. Nömrə mövcudluğuna zəmanət verilmir.";
        list.replaceChildren();
        if (!c.ranges?.length) {
            clearAndText(list, "API-də bu ölkə üçün hazırda range yoxdur.");
        }
        for (const item of (c.ranges || [])) {
            const rid = String(item.rid);
            addRangeButton(list, rid + " · " + String(item.service).toUpperCase() +
                (rid.startsWith("994") && !state.azApproved ? " 🔒" : ""),
                { rid, service: item.service, iso: c.iso, country: c.prefix,
                  isAz: rid.startsWith("994") });
        }
        box.scrollIntoView?.({ block: "start", behavior: "smooth" });
    } catch (err) {
        clearAndText(list, err.message);
    }
}

async function selectService(service, country = null, range = null, countryIso = null) {
    if (!range) {
        showServiceRanges(service);
        return;
    }
    // Only direct user clicks reach this path. No bulk allocation.
    try {
        const data = await api("/api/get-number", {
            method: "POST",
            body: { service, country, range, country_iso: countryIso }
        });
        if (!data.success) {
            alertUser(data.message || "Hazırda bu range üzrə nömrə yoxdur.");
            return;
        }
        alertUser("✅ Nömrə ayrıldı: " + data.number);
        switchTab("active");
        await fetchOrders();
        await fetchDashboard();
    } catch (err) {
        alertUser(err.message);
    }
}

async function copyPhoneNumber(number) {
    if (!/^\+\d{4,15}$/.test(number)) {
        alertUser("Bu sifariş üçün tam nömrə mövcud deyil.");
        return;
    }
    try {
        if (!navigator.clipboard?.writeText) throw new Error("clipboard_not_supported");
        await navigator.clipboard.writeText(number);
    } catch (_) {
        // Telegram's embedded browser may not expose the Clipboard API.
        const temp = document.createElement("textarea");
        temp.value = number;
        temp.readOnly = true;
        temp.style.position = "fixed";
        temp.style.opacity = "0";
        document.body.appendChild(temp);
        temp.select();
        const copied = document.execCommand("copy");
        temp.remove();
        if (!copied) {
            alertUser("Kopyalama mümkün olmadı. Nömrənin üzərinə toxunaraq əl ilə kopyalayın.");
            return;
        }
    }
    alertUser("📋 Nömrə kopyalandı!");
}

async function fetchOrders() {
    const container = document.getElementById("active-orders-container");
    try {
        const [ordersRes, dashboard] = await Promise.all([
            api("/api/orders"), api("/api/dashboard")
        ]);
        const orders = Array.isArray(ordersRes.orders) ? ordersRes.orders : [];
        const botOrders = Array.isArray(dashboard.orders) ? dashboard.orders : [];
        const combined = [...orders, ...botOrders];
        const seen = new Set();
        container.replaceChildren();
        if (!combined.length) {
            clearAndText(container, "Hazırda aktiv sifariş yoxdur.");
            return;
        }
        combined.forEach(order => {
            const fullNumber = String(order.number || "");
            const validNumber = /^\+\d{4,15}$/.test(fullNumber);
            // The same number can appear in /api/orders and /api/dashboard.
            const key = validNumber ? fullNumber : String(order.id || "");
            if (key && seen.has(key)) return;
            if (key) seen.add(key);

            const card = node("div", null, "sms-item");
            const display = validNumber
                ? fullNumber
                : (String(order.number_masked || "Sifariş"));
            const numberText = node("strong", display, "full-phone-number");
            card.appendChild(numberText);
            card.appendChild(node("p", "Range: " + (order.range || "—") +
                " · " + (order.status || "Aktiv"), "notice-mini"));
            if (validNumber) {
                const button = node("button", "📋 Kopyala", "action-small copy-phone-button");
                button.type = "button";
                button.setAttribute("aria-label", display + " nömrəsini kopyala");
                button.addEventListener("click", () => copyPhoneNumber(fullNumber));
                card.appendChild(button);
            } else {
                card.appendChild(node("p", "Tam nömrə bu sifarişdə mövcud deyil.", "notice-mini"));
            }
            container.appendChild(card);
        });
    } catch (err) {
        clearAndText(container, "Aktiv nömrələr yüklənmədi. " + err.message);
    }
}

async function fetchIncomingSms() {
    const container = document.getElementById("sms-list-container");
    try {
        const res = await api("/api/incoming-sms");
        const rows = Array.isArray(res.sms_list) ? res.sms_list : [];
        container.replaceChildren();
        if (!rows.length) {
            clearAndText(container, "Hələ ki bu hesaba aid mesaj yoxdur.");
            return;
        }
        rows.slice(0, 20).forEach(item => {
            const card = node("div", null, "sms-item");
            card.appendChild(node("strong", String(item.service || "SMS")));
            card.appendChild(node("p", "Nömrə: " + (item.number || "—"), "notice-mini"));
            card.appendChild(node("p", String(item.message || "")));
            card.appendChild(node("small", String(item.time || ""), "notice-mini"));
            container.appendChild(card);
        });
    } catch (err) { clearAndText(container, err.message); }
}


// Local-only RFC 6238 TOTP. The secret is never transmitted or stored.
let lastLocal2faCode = "";

function decodeBase32Key(input) {
    const normalized = String(input).trim().replace(/[\s-]/g, "").replace(/=+$/, "").toUpperCase();
    if (!normalized || !/^[A-Z2-7]+$/.test(normalized)) {
        throw new Error("Etibarlı Base32 2FA açarı daxil edin.");
    }
    const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
    let buffer = 0, bits = 0;
    const bytes = [];
    for (const ch of normalized) {
        buffer = (buffer << 5) | alphabet.indexOf(ch);
        bits += 5;
        if (bits >= 8) {
            bits -= 8;
            bytes.push((buffer >>> bits) & 255);
        }
    }
    if (bytes.length < 10 || bytes.length > 256) {
        throw new Error("2FA açarı düzgün uzunluqda deyil.");
    }
    return new Uint8Array(bytes);
}

async function createLocal2faCode() {
    const target = document.getElementById("totp-output");
    target.textContent = "Hesablanır...";
    lastLocal2faCode = "";
    try {
        if (!window.crypto?.subtle) throw new Error("Bu brauzer təhlükəsiz 2FA hesablamasını dəstəkləmir.");
        const secret = decodeBase32Key(document.getElementById("totp-secret").value);
        const key = await crypto.subtle.importKey(
            "raw", secret, { name: "HMAC", hash: "SHA-1" }, false, ["sign"]
        );
        const counter = BigInt(Math.floor(Date.now() / 30000));
        const block = new Uint8Array(8);
        for (let i = 7, value = counter; i >= 0; i--, value >>= 8n) {
            block[i] = Number(value & 255n);
        }
        const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, block));
        const offset = mac[mac.length - 1] & 15;
        const binary = ((mac[offset] & 127) << 24) |
            (mac[offset + 1] << 16) | (mac[offset + 2] << 8) | mac[offset + 3];
        lastLocal2faCode = String(binary % 1000000).padStart(6, "0");
        target.textContent = lastLocal2faCode;
        document.getElementById("totp-secret").value = "";
        // Do not retain the key, code is only for the current 30-second interval.
        target.dataset.expiry = String((Math.floor(Date.now() / 30000) + 1) * 30000);
    } catch (err) {
        target.textContent = "— — — — — —";
        alertUser(err.message);
    }
}

async function copyLocal2faCode() {
    const view = document.getElementById("totp-output");
    if (!lastLocal2faCode || Date.now() >= Number(view.dataset.expiry || 0)) {
        alertUser("Kodun müddəti bitib. Öz açarınızla yenisini yaradın.");
        return;
    }
    try {
        await navigator.clipboard.writeText(lastLocal2faCode);
        alertUser("🔐 Kod kopyalandı.");
    } catch (_) {
        alertUser("Kodu əl ilə kopyalayın.");
    }
}

async function fetchProfile() {
    const display = document.getElementById("profile-name");
    try {
        const data = await api("/api/profile");
        const u = data.user || {};
        display.textContent =
            "👤 " + (u.first_name || "İstifadəçi") +
            (u.username ? " · @" + u.username : "") +
            " · ID: " + (u.id || "—") +
            " · 💰 Balans: " + (data.balance || "0.00") + " AZN";
        const stats = data.stats || {};
        document.getElementById("profile-stats").textContent =
            "📱 Bu gün: " + (stats.today_numbers || 0) +
            " · Son 7 gün: " + (stats.last7d_numbers || 0) +
            " · Ümumi: " + (stats.total_numbers || 0) + " nömrə" +
            (data.az_approved ? " · 🇦🇿 +994 təsdiqlənib" : " · 🇦🇿 +994 icazəsi yoxdur");
        document.getElementById("profile-language").value = data.language || "az";
        const support = document.getElementById("support-link");
        if (typeof data.support_url === "string" &&
            /^https:\/\/t\.me\/[A-Za-z0-9_+/-]+$/.test(data.support_url)) {
            support.href = data.support_url;
        }
    } catch (err) {
        display.textContent = "Profil yüklənmədi: " + err.message;
    }
}

async function saveProfileLanguage() {
    const language = document.getElementById("profile-language").value;
    if (!["az", "en", "tr"].includes(language)) {
        alertUser("Yanlış dil seçimi.");
        return;
    }
    try {
        await api("/api/profile", {method: "POST", body: {language}});
        alertUser("✅ Dil seçimi bot hesabınıza saxlandı.");
        await fetchProfile();
    } catch (err) { alertUser(err.message); }
}

async function fetchLeaderboard() {
    const container = document.getElementById("leaderboard-list");
    try {
        const data = await api("/api/leaderboard");
        container.replaceChildren();
        const leaders = Array.isArray(data.leaders) ? data.leaders : [];
        if (!leaders.length) {
            clearAndText(container, "Bu gün nömrə aktivliyi yoxdur.");
            return;
        }
        leaders.forEach((leader, index) => {
            const row = node("div", null, "admin-user-line");
            row.appendChild(node("span", (index + 1) + ". 🏅 " + (leader.name || "İstifadəçi")));
            row.appendChild(node("b", String(leader.count || 0) + " nömrə"));
            container.appendChild(row);
        });
    } catch (err) { clearAndText(container, err.message); }
}

async function downloadOwnNumbers() {
    try {
        const response = await fetch(API_BASE + "/api/my-numbers", {
            method: "GET", headers: getAuthHeaders()
        });
        if (!response.ok) {
            const msg = await response.json().catch(() => ({}));
            throw new Error(msg.message || "Arxiv yüklənmədi.");
        }
        const blob = await response.blob();
        if (!blob.size) throw new Error("Saxlanmış nömrə yoxdur.");
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = "my_numbers.txt";
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);
        alertUser("📥 Şəxsi nömrə arxivi hazırlanıb.");
    } catch (err) {
        alertUser(err.message + " Alternativ: botun şəxsi çatında /numbers_txt yazın.");
    }
}

async function adminUserAction(action, userId) {
    if (!state.isAdmin || !["ban", "unban"].includes(action)) return;
    try {
        await api("/api/admin", {
            method: "POST", body: {action, user_id: String(userId)}
        });
        alertUser(action === "ban" ? "🚫 Hesab bloklandı." : "✅ Blok ləğv edildi.");
        await fetchAdminUsers();
    } catch (err) { alertUser(err.message); }
}

async function adminBalanceChange() {
    if (!state.isAdmin) return;
    const target = document.getElementById("admin-balance-id").value.trim();
    const amount = Number(document.getElementById("admin-balance-amount").value);
    if (!/^\d{1,20}$/.test(target) || !Number.isFinite(amount) ||
        amount === 0 || Math.abs(amount) > 10000) {
        alertUser("Düzgün Telegram ID və -10000 ilə +10000 arası məbləğ daxil edin.");
        return;
    }
    try {
        const result = await api("/api/admin", {
            method: "POST", body: {action: "balance", user_id: target, amount}
        });
        document.getElementById("admin-balance-result").textContent =
            "✅ İstifadəçi " + target + " · Yeni balans: " + result.balance + " AZN";
        await fetchAdminUsers();
    } catch (err) {
        document.getElementById("admin-balance-result").textContent = err.message;
        alertUser(err.message);
    }
}


async function fetchAdminUsers() {
    if (!state.isAdmin) return;
    const container = document.getElementById("admin-users-list");
    try {
        const data = await api("/api/admin");
        container.replaceChildren();
        container.appendChild(node("p", "İstifadəçilər: " + (data.user_count || 0),
            "notice-mini"));
        const monitor = data.monitor || {};
        const sys = document.getElementById("admin-system-status");
        sys.textContent = "🩺 SMS monitor: " + String(monitor.state || "naməlum") +
            " · HTTP: " + String(monitor.http_status ?? "—") +
            " · API: " + String(monitor.upstream_code ?? "—") +
            " · Yoxlanan: " + String(monitor.items_seen ?? 0);
        (data.users || []).forEach(user => {
            const row = node("div", null, "admin-user-line");
            row.appendChild(node("span", (user.name || "İstifadəçi") + " · ID " + user.id +
                (user.az_approved ? " ✅ +994" : " 🔒") +
                (user.banned ? " · 🚫 Bloklu" : "")));
            const actions = node("span", null, "quick-actions");
            const btn = node("button", user.az_approved ? "🇦🇿 Ləğv et" : "🇦🇿 İcazə",
                "action-small");
            btn.addEventListener("click", () => adminAzPermission(!user.az_approved, user.id));
            actions.appendChild(btn);
            const ban = node("button", user.banned ? "🔓 Aç" : "🚫 Blokla", "action-small");
            ban.addEventListener("click", () => adminUserAction(user.banned ? "unban" : "ban", user.id));
            actions.appendChild(ban);
            row.appendChild(actions);
            container.appendChild(row);
        });
    } catch (err) { clearAndText(container, err.message); }
}

async function adminAzPermission(approve, directId = null) {
    if (!state.isAdmin) return;
    const target = String(directId || document.getElementById("admin-target-id").value).trim();
    if (!/^\d{1,20}$/.test(target)) {
        alertUser("Düzgün Telegram istifadəçi ID-si yazın.");
        return;
    }
    try {
        await api("/api/admin", {
            method: "POST",
            body: { action: approve ? "az_approve" : "az_revoke", user_id: target }
        });
        document.getElementById("admin-result").textContent =
            (approve ? "✅ İcazə verildi: " : "🔒 İcazə ləğv edildi: ") + target;
        await fetchAdminUsers();
    } catch (err) {
        document.getElementById("admin-result").textContent = "⚠️ " + err.message;
        alertUser(err.message);
    }
}

document.addEventListener("DOMContentLoaded", async () => {
    const search = document.getElementById("country-search");
    search.addEventListener("input", () => {
        state.countryFilter = search.value.trim().toLocaleLowerCase();
        state.countryPage = 0;
        renderCountries();
    });
    await Promise.all([fetchDashboard(), fetchServices(), fetchCountries(), fetchOrders()]);
    if (state.authFailed) {
        setStatus("⚠️ Mini App-i Telegram-un içindən, botun düyməsi ilə açın.");
    }
    window.setInterval(() => {
        if (document.hidden) return;
        fetchDashboard();
        if (["services", "azerbaijan"].includes(state.activeTab)) fetchServices();
        if (state.activeTab === "countries") fetchCountries();
        if (state.activeTab === "active") fetchOrders();
        if (state.activeTab === "history") fetchIncomingSms();
        if (state.activeTab === "profile") fetchProfile();
        if (state.activeTab === "leaderboard") fetchLeaderboard();
    }, 30000);
});
