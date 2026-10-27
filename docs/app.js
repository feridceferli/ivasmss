/* AZE SMS PANEL Mini App — Telegram-verified, mobile-first interface.
   All country/range metadata comes from the same Render backend as the bot.
   No referral gate, no invented stock, no secrets in the browser.
*/
const tg = window.Telegram?.WebApp || { initData: "", expand() {} };
tg.expand();

const API_BASE = "https://ivasmss.onrender.com";
const TABS = ["services", "countries", "azerbaijan", "active", "history", "leaderboard", "profile", "guide", "admin"];
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
    authFailed: false,
    serviceQuery: "",
    pricing: null
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

let uiToastTimeout = null;
function toast(message, kind = "info") {
    const toastNode = document.getElementById("ui-toast");
    if (!toastNode) return;
    toastNode.textContent = String(message);
    toastNode.className = "ui-toast show" + (kind === "error" ? " error" : kind === "success" ? " success" : "");
    if (uiToastTimeout) window.clearTimeout(uiToastTimeout);
    uiToastTimeout = window.setTimeout(() => {
        toastNode.className = "ui-toast";
        uiToastTimeout = null;
    }, 3100);
}
function alertUser(message) {
    toast(message, /uğurlu|kopyalandı|✅/i.test(String(message)) ? "success" : "info");
    if (tg.showAlert) tg.showAlert(String(message));
    else if (!document.getElementById("ui-toast")) window.alert(String(message));
}

function getAuthHeaders() {
    return {
        "X-Telegram-Init-Data": tg.initData || "",
        "X-Website-Request": tg.initData ? "0" : "1",
        "Content-Type": "application/json"
    };
}

async function api(path, options = {}) {
    const res = await fetch(API_BASE + path, {
        method: options.method || "GET",
        credentials: "same-origin",
        headers: getAuthHeaders(),
        ...(options.body ? { body: JSON.stringify(options.body) } : {})
    });
    let data = {};
    try { data = await res.json(); } catch (_) { /* unavailable */ }
    if (!res.ok) {
        if (res.status === 401) {
            state.authFailed = true;
            window.websiteAuth?.requireLogin();
        }
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
        const active = TABS[index] === tab;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", active ? "true" : "false");
        if (active && typeof button.scrollIntoView === "function") {
            button.scrollIntoView({block: "nearest", inline: "nearest", behavior: "smooth"});
        }
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
    } else if (tab === "leaderboard") {
        fetchLeaderboard();
    } else if (tab === "profile") {
        fetchProfile();
    } else if (tab === "admin") {
        fetchAdminUsers();
        loadAdminTools();
        fetchPrices();
    }
}

const telegramAvatarState = {
    userId: null,
    objectUrl: null,
    checkedAt: 0,
    loading: false
};

// Fetch only this signed-in Telegram user's own photo. The bot token, Telegram
// file_id and server-side file URL never reach the browser.
async function updateTelegramAvatar(user, force = false) {
    const id = String(user?.id || "");
    if (!id) return false;
    const sameUser = id === telegramAvatarState.userId;
    const now = Date.now();
    if (!force && sameUser &&
        (telegramAvatarState.loading || now - telegramAvatarState.checkedAt < 300000)) {
        return Boolean(telegramAvatarState.objectUrl);
    }

    telegramAvatarState.userId = id;
    telegramAvatarState.checkedAt = now;
    telegramAvatarState.loading = true;
    const avatars = ["user-avatar", "profile-avatar"]
        .map(key => document.getElementById(key))
        .filter(Boolean);
    const fallback = String(user.first_name || "İ").slice(0, 1).toUpperCase();

    if (!sameUser || !telegramAvatarState.objectUrl) {
        if (telegramAvatarState.objectUrl) URL.revokeObjectURL(telegramAvatarState.objectUrl);
        telegramAvatarState.objectUrl = null;
        for (const avatar of avatars) {
            avatar.replaceChildren();
            avatar.textContent = fallback;
        }
    }

    try {
        const response = await fetch(API_BASE + "/api/avatar", {
            method: "GET",
            headers: getAuthHeaders(),
            cache: "no-store"
        });
        if (!response.ok) return false;
        const photo = await response.blob();
        if (!photo.type.startsWith("image/") || !photo.size || photo.size > 512 * 1024) {
            return false;
        }
        if (telegramAvatarState.userId !== id) return false;
        const imageUrl = URL.createObjectURL(photo);
        const oldUrl = telegramAvatarState.objectUrl;
        telegramAvatarState.objectUrl = imageUrl;
        for (const avatar of avatars) {
            const image = document.createElement("img");
            image.src = imageUrl;
            image.alt = "Telegram profil şəkliniz";
            image.decoding = "async";
            image.loading = "lazy";
            image.addEventListener("error", () => {
                if (telegramAvatarState.userId !== id) return;
                avatar.replaceChildren();
                avatar.textContent = fallback;
            }, {once: true});
            avatar.replaceChildren(image);
        }
        if (oldUrl) URL.revokeObjectURL(oldUrl);
        return true;
    } catch (_) {
        // Telegram privacy settings or missing photos should not block profile.
        return false;
    } finally {
        if (telegramAvatarState.userId === id) telegramAvatarState.loading = false;
    }
}

async function refreshTelegramAvatar() {
    try {
        const dashboard = await api("/api/dashboard");
        const refreshed = await updateTelegramAvatar(dashboard.user || {}, true);
        toast(refreshed ? "✅ Telegram şəkliniz yeniləndi."
            : "Telegram şəkli əlçatan deyil, hərfli avatar göstərilir.",
            refreshed ? "success" : "info");
    } catch (_) {
        toast("Profil şəklini yeniləmək mümkün olmadı.", "error");
    }
}

async function fetchDashboard() {
    try {
        const data = await api("/api/dashboard");
        const user = data.user || {};
        document.getElementById("user-name").textContent = user.first_name || "İstifadəçi";
        document.getElementById("user-id").textContent = "ID: " + (user.id || "—");
        document.getElementById("user-balance").textContent = (data.balance || "0.00") + " AZN";
        // Avatar is served only for the authenticated Telegram account.
        // Do not reset the picture during the periodic dashboard refresh.
        void updateTelegramAvatar(user);
        state.isAdmin = !!user.is_admin;
        state.azApproved = !!user.az_approved;
        const adminButton = document.getElementById("admin-tab-button");
        adminButton.hidden = !state.isAdmin;
        document.getElementById("tab-admin").hidden = !state.isAdmin;
        const stats = data.stats || {};
        const todayCount = document.getElementById("ui-today-count");
        if (todayCount) todayCount.textContent = String(stats.today_numbers || 0);
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
        ? "✅ +994 icazəniz var. Qiymət: 10 AZN. API-də nömrə mövcudluğu ayrıca yoxlanır."
        : "🔒 +994 range qiyməti 10 AZN-dir. Nömrə almaq üçün admin təsdiqi lazımdır. Admin: @lacin_0411.";
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


// The browser displays public price rules; server independently verifies them.
function countryPriceRule(iso) {
    const p = state.pricing;
    if (!p) return null;
    return p.country?.[iso] || (iso === "AZ" ? {cents: 1000, free: false} : p.default);
}

function priceLabel(rule) {
    if (!rule) return "Qiymət yüklənir...";
    return rule.free ? "🆓 Pulsuz" : "💰 " + (Number(rule.cents) / 100).toFixed(2) + " AZN";
}

function quotePrice(rid, countryIso = null) {
    const p = state.pricing;
    if (!p || !state.countries.length) return {error: "Qiymət məlumatları hələ yüklənməyib."};
    const digits = String(rid || "").replace(/\D/g, "");
    const code = [...new Set(state.countries.map(c => String(c.prefix)))]
        .sort((a, b) => b.length - a.length).find(code => digits.startsWith(code));
    if (!code) return {error: "Bu range üçün ölkə müəyyən edilmir."};
    const regions = state.countries.filter(c => String(c.prefix) === code);
    if (countryIso && !regions.some(c => c.iso === countryIso))
        return {error: "Ölkə və range uyğun gəlmir."};
    let rule = p.range?.[digits];
    if (!rule) {
        const unique = [...new Set(regions.map(c => {
            const item = countryPriceRule(c.iso);
            return String(item?.cents) + "/" + String(item?.free);
        }))];
        if (unique.length > 1) return {error: "Eyni +kodlu ölkələrin qiymətləri fərqlidir. Admin bu range üçün ayrıca qiymət qoymalıdır."};
        rule = countryPriceRule(regions[0]?.iso);
    }
    return rule ? {cents: Number(rule.cents), free: !!rule.free, price: priceLabel(rule)} :
        {error: "Qiymət müəyyən edilmədi."};
}

function refreshAzPriceNotes() {
    const rule = countryPriceRule("AZ");
    for (const id of ["services-az-price", "country-az-pricing-text", "az-price-text"]) {
        const item = document.getElementById(id);
        if (item) item.textContent = "🇦🇿 Azərbaycan (+994): " + priceLabel(rule) +
            " (fərdi range qiymətləri fərqli ola bilər).";
    }
}

async function fetchPrices() {
    try {
        const response = await api("/api/prices");
        state.pricing = response.pricing || null;
        refreshAzPriceNotes();
        if (state.isAdmin) renderAdminPrices();
    } catch (err) {
        state.pricing = null;
        const status = document.getElementById("admin-prices-status");
        if (status) status.textContent = "⚠️ " + err.message;
        toast("Qiymətlər yüklənmədi: " + err.message, "error");
    }
}

function addRangeButton(container, label, options) {
    const quote = quotePrice(options.rid, options.iso || null);
    const button = node("button", label + " · " + (quote.error ? "⚠️ Qiymət" : quote.price), "catalog-row catalog-range");
    button.type = "button";
    const locked = options.isAz && !state.azApproved;
    button.disabled = !!quote.error;
    if (quote.error) button.title = quote.error;
    if (locked) button.title = "+994 üçün admin təsdiqi tələb olunur";
    button.addEventListener("click", () => {
        if (locked) {
            alertUser("🔒 +994 üçün admin icazəsi tələb olunur: @lacin_0411.");
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
    const query = String(state.serviceQuery || "").trim().toLocaleLowerCase();
    const services = Object.keys(state.services).sort().filter(service =>
        service.toLocaleLowerCase().includes(query)
    );
    if (!services.length) {
        clearAndText(container, "API hazırda heç bir xidmət göstərmir.");
        return;
    }
    services.forEach(service => {
        const offered = Array.isArray(state.services[service]) ? state.services[service] : [];
        const b = node("button", null, "service-card");
        b.appendChild(node("span", "◈", "service-icon"));
        b.appendChild(node("span", service.toUpperCase(), "service-name"));
        b.appendChild(node("span", offered.length + " range · Seçmək üçün toxun", "service-meta"));
        b.type = "button";
        b.addEventListener("click", () => showServiceRanges(service));
        container.appendChild(b);
    });
}

// Group offered service ranges under their longest matching world calling codes.
// Shared dial codes are labelled as shared; the provider must verify availability.
function serviceCountryGroups(service) {
    const available = Array.isArray(state.services[service]) ? state.services[service] : [];
    const ranges = [...new Set(available.map(item => String(item).replace(/\D/g, "")))]
        .filter(item => /^\d{1,10}$/.test(item));
    const codeMap = new Map();
    for (const country of state.countries) {
        const code = String(country.prefix);
        if (!codeMap.has(code)) codeMap.set(code, []);
        codeMap.get(code).push(country);
    }
    const codes = [...codeMap.keys()].sort((a, b) => b.length - a.length);
    const grouped = new Map();
    for (const rid of ranges) {
        const code = codes.find(item => rid.startsWith(item)) || "";
        if (!grouped.has(code)) grouped.set(code, []);
        grouped.get(code).push(rid);
    }
    return [...grouped.entries()].map(([code, items]) => {
        const countries = codeMap.get(code) || [];
        const shared = countries.length > 1;
        const label = countries.length
            ? countries.slice(0, 3).map(c => c.flag + " " + c.name).join(", ") +
              (countries.length > 3 ? " və digər ölkələr" : "")
            : "🌍 Digər kod";
        return {code, items, label, iso: shared ? null : (countries[0]?.iso || null), shared};
    }).sort((a, b) => a.label.localeCompare(b.label));
}

async function showServiceRanges(service) {
    const parent = document.getElementById("service-detail");
    if (!parent) return;
    parent.hidden = false;
    if (!state.countries.length) await fetchCountries();
    parent.replaceChildren();
    parent.appendChild(node("h4", "📡 " + service.toUpperCase() + " — ölkə və range seçimi"));
    parent.appendChild(node("p",
        "Əvvəl ölkə kodunu, sonra range-i seçin. Nömrə yalnız seçilmiş range üzrə bir dəfə soruşulur; mövcudluq API-dən asılıdır.",
        "notice-mini"));

    const groups = serviceCountryGroups(service);
    const controls = node("div", null, "service-filter-row");
    const label = node("label", "Ölkə kodu:");
    const picker = document.createElement("select");
    picker.setAttribute("aria-label", "Xidmət üçün ölkə kodu");
    const search = document.createElement("input");
    search.type = "search";
    search.placeholder = "Range axtar (məs. 99450)";
    search.setAttribute("aria-label", "Range axtarışı");
    controls.append(label, picker, search);
    parent.appendChild(controls);
    const listing = node("div", null, "catalog-scroll service-range-list");
    parent.appendChild(listing);
    const pricing = node("div");
    parent.appendChild(pricing);
    const close = node("button", "✕ Bağla", "action-small");
    close.type = "button";
    close.addEventListener("click", () => { parent.hidden = true; });
    parent.appendChild(close);

    for (const [i, group] of groups.entries()) {
        const option = document.createElement("option");
        option.value = String(i);
        option.textContent = group.label + (group.code ? " (+" + group.code + ")" : "") +
            " · " + group.items.length + " range";
        picker.appendChild(option);
    }
    if (!groups.length) {
        clearAndText(listing, "Bu xidmət üçün API-də uyğun range yoxdur.");
        return;
    }
    function renderChosenCountry() {
        listing.replaceChildren();
        pricing.replaceChildren();
        const selected = groups[Number(picker.value) || 0];
        if (!selected) return;
        const q = search.value.replace(/\D/g, "");
        const ranges = selected.items.filter(rid => rid.includes(q));
        for (const rid of ranges) {
            addRangeButton(listing, "📞 +" + rid + " — Nömrə al" +
                (rid.startsWith("994") && !state.azApproved ? " 🔒" : ""),
                {service, rid, country: selected.code, iso: selected.iso, isAz: rid.startsWith("994")});
        }
        if (!ranges.length) clearAndText(listing, "Bu ölkə və axtarış üçün range tapılmadı.");
        if (selected.items.some(rid => rid.startsWith("994"))) {
            pricing.appendChild(node("p",
                "🇦🇿 +994 üçün qiymətlər seçilmiş range-də göstərilir. " +
                "İcazə tələb olunur; ödənişli nömrə verilərsə məbləğ balansdan tutulur.", "az-price-note"));
            const link = node("a", "💬 Adminlə əlaqə — @lacin_0411", "support-cta");
            link.href = "https://t.me/lacin_0411";
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            pricing.appendChild(link);
        }
    }
    picker.addEventListener("change", renderChosenCountry);
    search.addEventListener("input", renderChosenCountry);
    renderChosenCountry();
    parent.scrollIntoView?.({block: "nearest", behavior: "smooth"});
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
        const countryCount = document.getElementById("ui-country-count");
        if (countryCount) countryCount.textContent = String(state.countries.length);
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
        b.appendChild(node("small", (c.count || 0) + " range · " + priceLabel(countryPriceRule(c.iso))));
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
        document.getElementById("country-az-pricing").hidden = c.prefix !== "994";
        document.getElementById("country-price-display").textContent = "Ölkə qiyməti: " +
            priceLabel(countryPriceRule(c.iso)) + " · Range üzrə ayrıca qiymət ola bilər.";
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
    const quote = typeof quotePrice === "function" ? quotePrice(range, countryIso) : {cents: 0, free: true};
    if (quote.error) {
        alertUser(quote.error);
        return;
    }
    if (String(range).startsWith("994") && !state.azApproved) {
        alertUser("+994 nömrəsi üçün admin icazəsi lazımdır. Admin: @lacin_0411.");
        switchTab("azerbaijan");
        return;
    }
    if (!quote.free && !window.confirm(
        "Bu nömrənin qiyməti " + (quote.cents / 100).toFixed(2) +
        " AZN-dir. Uğurlu ayrılma zamanı balansınızdan çıxılacaq. Davam edilsin?"
    )) return;
    // A separate authenticated API request is made only on an explicit click.
    try {
        const data = await api("/api/get-number", {
            method: "POST",
            body: { service, country, range, ...(countryIso ? {country_iso: countryIso} : {}),
                    expected_price_cents: quote.cents }
        });
        if (!data.success) {
            alertUser(data.message || "Hazırda bu range üzrə nömrə yoxdur.");
            return;
        }
        // The API may return bare digits or a +country-code number.
        // Only a successfully allocated number is eligible for copying.
        const digits = String(data.number || "").replace(/\D/g, "");
        const fullNumber = "+" + digits;
        const copied = /^\+\d{4,15}$/.test(fullNumber)
            ? await copyPhoneNumber(fullNumber, false)
            : false;
        // Keep the number visible even when Telegram's WebView blocks clipboard access.
        switchTab("active");
        await fetchOrders();
        await fetchDashboard();
        alertUser(copied
            ? "✅ Nömrə alındı və avtomatik kopyalandı: " + fullNumber
            : "✅ Nömrə alındı: " + (digits ? fullNumber : String(data.number || "")) +
              "\n📋 Avtomatik kopyalama mümkün olmadı. Aktivlər bölməsində Kopyala düyməsinə toxunun.");
    } catch (err) {
        alertUser(err.message);
    }
}

async function copyPhoneNumber(number, showFeedback = true) {
    if (!/^\+\d{4,15}$/.test(number)) {
        if (showFeedback) alertUser("Bu sifariş üçün tam nömrə mövcud deyil.");
        return false;
    }
    let copied = false;
    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(number);
            copied = true;
        }
    } catch (_) {
        // Telegram's embedded browser may deny Clipboard API access.
    }
    if (!copied) {
        // Compatibility fallback; can also be denied after an asynchronous request.
        const temp = document.createElement("textarea");
        temp.value = number;
        temp.readOnly = true;
        temp.style.position = "fixed";
        temp.style.opacity = "0";
        document.body.appendChild(temp);
        try {
            temp.focus();
            temp.select();
            copied = Boolean(document.execCommand("copy"));
        } catch (_) {
            copied = false;
        } finally {
            temp.remove();
        }
    }
    if (showFeedback) {
        alertUser(copied
            ? "📋 Nömrə kopyalandı!"
            : "Kopyalama mümkün olmadı. Nömrəni seçərək əl ilə kopyalaya bilərsiniz.");
    }
    return copied;
}

let activeOrderTimer = null;
let activeOrderRefreshBusy = false;
function formatOrderTime(seconds) {
    const value = Math.max(0, Math.ceil(Number(seconds) || 0));
    return String(Math.floor(value / 60)).padStart(2, "0") + ":" +
           String(value % 60).padStart(2, "0");
}
function startActiveOrderTimer() {
    if (activeOrderTimer) return;
    activeOrderTimer = window.setInterval(async () => {
        if (state.activeTab !== "active") return;
        let expired = false;
        document.querySelectorAll("[data-order-expires]").forEach(element => {
            const remaining = Math.max(0, Math.ceil(
                (Number(element.dataset.orderExpires) - Date.now()) / 1000
            ));
            element.textContent = "⏳ Qalan vaxt: " + formatOrderTime(remaining);
            if (!remaining) expired = true;
        });
        if (expired && !activeOrderRefreshBusy) {
            activeOrderRefreshBusy = true;
            try { await fetchOrders(); }
            finally { activeOrderRefreshBusy = false; }
        }
    }, 1000);
}
async function cancelNumberOrder(orderId, button) {
    if (!orderId) return;
    if (!window.confirm("Bu nömrəni ləğv edək? Provayder ödənişi geri qaytarılmır.")) return;
    button.disabled = true;
    try {
        await api("/api/orders", {method: "POST", body: {
            action: "cancel", id: String(orderId)
        }});
        toast("✅ Nömrənin gözlənilməsi ləğv edildi.", "success");
        await fetchOrders();
    } catch (error) {
        button.disabled = false;
        alertUser("Ləğv mümkün olmadı: " + error.message);
    }
}

async function fetchOrders() {
    const container = document.getElementById("active-orders-container");
    try {
        const [ordersRes, dashboard] = await Promise.all([
            api("/api/orders"), api("/api/dashboard")
        ]);
        const orders = Array.isArray(ordersRes.orders) ? ordersRes.orders : [];
        const botOrders = Array.isArray(dashboard.orders) ? dashboard.orders : [];
        // Both APIs supply Unix-second created_at timestamps. Sort across
        // both sources before removing duplicates so newest allocations lead.
        const createdAt = order => {
            const raw = order.created_at;
            if (typeof raw === "number" && Number.isFinite(raw)) return raw;
            if (typeof raw === "string") {
                const numeric = Number(raw);
                if (Number.isFinite(numeric) && raw.trim() !== "") return numeric;
                const parsed = Date.parse(raw);
                if (Number.isFinite(parsed)) return parsed / 1000;
            }
            return 0;
        };
        const combined = [...orders, ...botOrders]
            .sort((a, b) => createdAt(b) - createdAt(a));
        const activeCount = document.getElementById("ui-active-count");
        if (activeCount) activeCount.textContent = String(new Set(
            combined.map(order => String(order.number || order.id || ""))
        ).size);
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
            const remaining = Math.max(0, Number(order.remaining_seconds ?? 0));
            const timer = node("p", "⏳ Qalan vaxt: " + formatOrderTime(remaining), "notice-mini");
            timer.dataset.orderExpires = String(Date.now() + remaining * 1000);
            card.appendChild(timer);
            if (validNumber) {
                const button = node("button", "📋 Kopyala", "action-small copy-phone-button");
                button.type = "button";
                button.setAttribute("aria-label", display + " nömrəsini kopyala");
                button.addEventListener("click", () => copyPhoneNumber(fullNumber));
                card.appendChild(button);
            } else {
                card.appendChild(node("p", "Tam nömrə bu sifarişdə mövcud deyil.", "notice-mini"));
            }
            if (order.id && remaining > 0) {
                const cancel = node("button", "❌ Ləğv et", "action-small");
                cancel.type = "button";
                cancel.setAttribute("aria-label", display + " sifarişini ləğv et");
                cancel.addEventListener("click", () => cancelNumberOrder(order.id, cancel));
                card.appendChild(cancel);
            }
            container.appendChild(card);
        });
        startActiveOrderTimer();
    } catch (err) {
        clearAndText(container, "Aktiv nömrələr yüklənmədi. " + err.message);
    }
}

async function fetchActivityHistory() {
    const container = document.getElementById("activity-history-list");
    if (!container) return;
    try {
        const result = await api("/api/activity-history");
        const events = Array.isArray(result.history) ? result.history : [];
        container.replaceChildren();
        if (!events.length) {
            clearAndText(container, "Hələ saxlanmış fəaliyyət yoxdur.");
            return;
        }
        const actionNames = {
            "NUMBER_TAKEN": "📱 Nömrə alındı",
            "OTP_RECEIVED": "✅ OTP qəbul edildi",
            "OTP_RECEIVED_FREE": "✅ OTP qəbul edildi",
            "DEMO_OTP_SENT": "🧪 Test bildirişi"
        };
        events.slice(0, 100).forEach(event => {
            const row = node("div", null, "admin-user-line");
            row.appendChild(node("strong", actionNames[event.action] || "📋 " + String(event.action || "Hadisə")));
            row.appendChild(node("small", String(event.timestamp || "").replace("T", " "), "notice-mini"));
            container.appendChild(row);
        });
    } catch (err) {
        clearAndText(container, "Tarixçə yüklənmədi: " + err.message);
    }
}

// Poll the authenticated user's own inbox, never displaying codes in popups.
// The first snapshot is a baseline: reopening the app must not replay old OTPs.
const otpCelebrations = [
    "🎉 Təbriklər, qərdəş! Səndən əla xəbər var!",
    "💚 Ürəyimsən, sağ ol qaqaş!",
    "🔥 Nömrəvi ala, qaqaş! Uğurlar!",
    "🥳 Xoş gəldin, nəfəs! Yeni OTP gəldi!",
    "🤝 Öpürəm, brat! İşlər yolundadır!",
    "🚀 Halaldı sənə, qardaş! Bir uğur da gəldi!",
    "🎊 Qəşəng gedirsən, qaqa! Təbriklər!",
    "✨ Əhsən, dostum! Hər şey əladır!"
];
let otpSeenEvents = null;
let otpWatchBusy = false;
let otpCheerIndex = 0;
function incomingEventId(item) {
    return String(item.event_id || [
        item.service || "", item.number || "", item.time || "", item.message || ""
    ].join("|"));
}
async function checkNewOtpNotifications() {
    if (otpWatchBusy || state.authFailed || document.hidden) return;
    otpWatchBusy = true;
    try {
        const data = await api("/api/incoming-sms");
        const rows = Array.isArray(data.sms_list) ? data.sms_list : [];
        const ids = new Set(rows.map(incomingEventId));
        if (otpSeenEvents !== null) {
            const fresh = rows.filter(item => !otpSeenEvents.has(incomingEventId(item)));
            if (fresh.length) {
                const latest = fresh[0];
                const cheer = String(latest.congratulations || "").trim() ||
                    otpCelebrations[otpCheerIndex++ % otpCelebrations.length];
                toast("✅ Yeni OTP gəldi! " + cheer, "success");
                if (typeof tg.HapticFeedback?.notificationOccurred === "function") {
                    tg.HapticFeedback.notificationOccurred("success");
                }
                if (state.activeTab === "history") fetchIncomingSms();
            }
        }
        otpSeenEvents = ids;
    } catch (_) {
        // Offline polling must not interrupt other Mini App interactions.
    } finally {
        otpWatchBusy = false;
    }
}

async function fetchIncomingSms() {
    fetchActivityHistory();
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


async function fetchProfile() {
    const display = document.getElementById("profile-name");
    try {
        const data = await api("/api/profile");
        const u = data.user || {};
        void updateTelegramAvatar(u);
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

let otpLifetimeOffset = 0;
let otpLifetimeLoading = false;
let otpLifetimeHasMore = false;
const OTP_LEADERBOARD_PAGE_SIZE = 50;

function renderOtpLeaderRows(container, leaders, offset = 0) {
    leaders.forEach((leader, index) => {
        const rank = offset + index + 1;
        const marker = rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : "🏅";
        const row = node("div", null, "admin-user-line");
        row.appendChild(node("span", rank + ". " + marker + " " + (leader.name || "İstifadəçi")));
        row.appendChild(node("b", String(leader.count || 0) + " OTP"));
        container.appendChild(row);
    });
}

async function fetchLeaderboard() {
    const todayNode = document.getElementById("leaderboard-list");
    const todaySummary = document.getElementById("leaderboard-today-summary");
    const allNode = document.getElementById("leaderboard-all-list");
    const allSummary = document.getElementById("leaderboard-all-summary");
    const moreButton = document.getElementById("leaderboard-all-more");
    moreButton.hidden = true;
    otpLifetimeOffset = 0;
    otpLifetimeHasMore = false;
    try {
        const [today, all] = await Promise.all([
            api("/api/leaderboard?period=today&limit=10"),
            api("/api/leaderboard?period=all&limit=" + OTP_LEADERBOARD_PAGE_SIZE + "&offset=0")
        ]);
        todayNode.replaceChildren();
        const daily = Array.isArray(today.leaders) ? today.leaders : [];
        todaySummary.textContent = "📅 " + (today.date || "Bu gün") +
            " · Bakı vaxtı · " + (today.summary?.today_users || 0) + " istifadəçi · " +
            (today.summary?.today_otps || 0) + " OTP";
        if (daily.length) renderOtpLeaderRows(todayNode, daily);
        else clearAndText(todayNode, "Bu gün hələ OTP qeydi yoxdur.");

        allNode.replaceChildren();
        const lifetime = Array.isArray(all.leaders) ? all.leaders : [];
        allSummary.textContent = "👥 " + (all.summary?.total_users || 0) + " istifadəçi · " +
            "🔑 " + (all.summary?.total_otps || 0) + " OTP";
        if (lifetime.length) renderOtpLeaderRows(allNode, lifetime);
        else clearAndText(allNode, "Hələ OTP alan istifadəçi qeydə alınmayıb.");
        otpLifetimeOffset = lifetime.length;
        otpLifetimeHasMore = Boolean(all.has_more);
        moreButton.hidden = !otpLifetimeHasMore;
    } catch (err) {
        clearAndText(todayNode, err.message);
        clearAndText(allNode, err.message);
    }
}

async function loadMoreOtpLeaders() {
    if (!otpLifetimeHasMore || otpLifetimeLoading) return;
    const button = document.getElementById("leaderboard-all-more");
    const container = document.getElementById("leaderboard-all-list");
    otpLifetimeLoading = true;
    button.disabled = true;
    try {
        const data = await api("/api/leaderboard?period=all&limit=" +
            OTP_LEADERBOARD_PAGE_SIZE + "&offset=" + otpLifetimeOffset);
        const leaders = Array.isArray(data.leaders) ? data.leaders : [];
        renderOtpLeaderRows(container, leaders, otpLifetimeOffset);
        otpLifetimeOffset += leaders.length;
        otpLifetimeHasMore = Boolean(data.has_more);
        button.hidden = !otpLifetimeHasMore;
    } catch (err) {
        alertUser("Lider siyahısı yüklənmədi: " + err.message);
    } finally {
        otpLifetimeLoading = false;
        button.disabled = false;
    }
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


let adminUsersCache = [];

function adminJump(targetId) {
    if (!state.isAdmin) return;
    const target = document.getElementById(targetId);
    if (target) target.scrollIntoView({behavior: "smooth", block: "start"});
}

function filterAdminUsers() {
    if (!state.isAdmin) return;
    const term = (document.getElementById("admin-user-search")?.value || "").trim().toLocaleLowerCase();
    const container = document.getElementById("admin-users-list");
    if (!container) return;
    container.replaceChildren();
    const visible = adminUsersCache.filter(user => {
        const name = [user.first_name, user.last_name].filter(Boolean).join(" ") || user.name || "";
        return [name, user.username || "", String(user.id || "")].join(" ").toLocaleLowerCase().includes(term);
    });
    container.appendChild(node("p", "Göstərilən: " + visible.length + " / " + adminUsersCache.length + " istifadəçi", "notice-mini"));
    if (!visible.length) container.appendChild(node("p", "Uyğun istifadəçi tapılmadı.", "notice-mini"));
    visible.forEach(user => {
        const row = node("div", null, "admin-user-line");
        const identity = node("div", null, "admin-user-identity");
        const fullname = [user.first_name, user.last_name].filter(Boolean).join(" ").trim() || user.name || "Adsız istifadəçi";
        identity.appendChild(node("strong", "👤 " + fullname));
        identity.appendChild(node("small", (user.username ? "@" + user.username + " · " : "") + "ID: " + user.id));
        identity.appendChild(node("small", "💰 " + (user.balance ?? "0.00") + " AZN · 📱 " + (user.total_numbers ?? 0) + " nömrə"));
        identity.appendChild(node("small", (user.az_approved ? "✅ +994" : "🔒 +994 icazəsiz") + (user.banned ? " · 🚫 Bloklu" : "")));
        row.appendChild(identity);
        const actions = node("div", null, "quick-actions");
        const az = node("button", user.az_approved ? "🇦🇿 Ləğv et" : "🇦🇿 İcazə", "action-small");
        az.addEventListener("click", () => adminAzPermission(!user.az_approved, user.id));
        const ban = node("button", user.banned ? "🔓 Aç" : "🚫 Blokla", "action-small");
        ban.addEventListener("click", () => adminUserAction(user.banned ? "unban" : "ban", user.id));
        actions.appendChild(az);
        actions.appendChild(ban);
        row.appendChild(actions);
        container.appendChild(row);
    });
}

async function fetchAdminUsers() {
    if (!state.isAdmin) return;
    const container = document.getElementById("admin-users-list");
    try {
        const data = await api("/api/admin");
        adminUsersCache = data.users || [];
        const monitor = data.monitor || {};
        const sys = document.getElementById("admin-system-status");
        sys.textContent = "👥 Cəmi: " + (data.user_count || 0) +
            " · 🩺 SMS monitor: " + String(monitor.state || "naməlum") +
            " · HTTP: " + String(monitor.http_status ?? "—") +
            " · API: " + String(monitor.upstream_code ?? "—") +
            " · Yoxlanan: " + String(monitor.items_seen ?? 0);
        filterAdminUsers();
    } catch (err) { clearAndText(container, err.message); }
}


let adminTools = null;

async function loadAdminTools() {
    if (!state.isAdmin) return;
    const status = document.getElementById("admin-test-status");
    try {
        adminTools = await api("/api/admin-tools");
        const cfg = adminTools.config || {};
        document.getElementById("cfg-min-withdraw").value = cfg.min_withdraw ?? "";
        document.getElementById("cfg-max-withdraw").value = cfg.max_withdraw ?? "";
        const payment = document.getElementById("cfg-payment-methods");
        payment.replaceChildren();
        for (const [method, enabled] of Object.entries(cfg.payment_methods || {})) {
            const label = node("label", null, "notice-mini");
            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.checked = !!enabled;
            checkbox.dataset.method = method;
            label.appendChild(checkbox);
            label.appendChild(document.createTextNode(" " + method));
            payment.appendChild(label);
        }
        const channels = document.getElementById("admin-channels-list");
        channels.replaceChildren();
        if (!(adminTools.required_channels || []).length) {
            clearAndText(channels, "Tələb olunan kanal yoxdur.");
        }
        for (const channel of (adminTools.required_channels || [])) {
            const row = node("div", null, "admin-user-line");
            row.appendChild(node("span", (channel.label || "Kanal") + " · " + channel.link));
            const remove = node("button", "❌ Sil", "action-small");
            remove.addEventListener("click", () => adminRemoveChannel(channel.link));
            row.appendChild(remove);
            channels.appendChild(row);
        }
        const ai = adminTools.ai_posts || {};
        document.getElementById("ai-post-enabled").checked = !!ai.enabled;
        document.getElementById("ai-post-style").value = ai.style || "energetic";
        document.getElementById("ai-post-status").textContent =
            ai.mode === "off" ? "⏸️ AI paylaşımları söndürülüb." :
            ai.mode === "ai" ? "✅ Pulsuz Groq Llama AI aktivdir (limitlər tətbiq olunur)." :
            "⚠️ GROQ_API_KEY yoxdur — hazır şablonla paylaşımlar davam edir.";
        const worldNews = adminTools.world_news || {};
        document.getElementById("world-news-enabled").checked = !!worldNews.enabled;
        document.getElementById("world-news-interval").value = worldNews.interval_minutes || 120;
        document.getElementById("world-news-status").textContent =
            (worldNews.enabled ? "✅ Dünya xəbərləri aktivdir." : "⏸️ Dünya xəbərləri söndürülüb.") +
            " · " + (worldNews.interval_minutes || 120) + " dəqiqədən bir · linksiz qısa Azərbaycan xülasələri.";
        const wa = adminTools.whatsapp || {};
        const archive = adminTools.archive_sync || {};
        const archiveStatus = document.getElementById("admin-archive-status");
        if (archiveStatus) {
            const detail = archive.status || "Vəziyyət məlum deyil.";
            archiveStatus.textContent =
                /xəta|failed|http\s*[45]\d\d/i.test(detail) ? "❌ Yedəkləmə xətası: " + detail :
                /yeniləndi|yenidir/i.test(detail) ? "✅ " + detail :
                "ℹ️ " + detail;
        }
        const demo = adminTools.demo || {};
        const demoStatus = document.getElementById("admin-demo-status");
        if (demoStatus) demoStatus.textContent =
            (demo.running ? "🟢 Aktiv" : "⏸️ Dayandırılıb") +
            " · Test mesajları: " + String(demo.sent_count ?? 0);
        const userBackup = adminTools.user_backup || {};
        const userBackupStatus = document.getElementById("admin-user-backup-status");
        if (userBackupStatus) {
            const detail = userBackup.status || "Yedəkləmə vəziyyəti məlum deyil.";
            userBackupStatus.textContent = "👥 İstifadəçilər (ID, balans, nömrə sayı): " + detail;
        }
        status.textContent = "📡 WhatsApp: " + (wa.status === "configured" ? "✅ Ayarlanıb" : "⚠️ Ayarlanmayıb") +
            (wa.test_recipient ? " · " + wa.test_recipient : "") +
            " · 📥 Arxiv: " + (archive.status || "naməlum") +
            " · 📨 Bildiriş qrupu: " +
            (adminTools.notification_group_configured ? "✅" : "⚠️ Ayarlanmayıb");
    } catch (err) {
        status.textContent = "⚠️ Admin alətləri: " + err.message;
        const archiveStatus = document.getElementById("admin-archive-status");
        if (archiveStatus) archiveStatus.textContent = "⚠️ Arxiv statusu alınmadı: " + err.message;
        const userBackupStatus = document.getElementById("admin-user-backup-status");
        if (userBackupStatus) userBackupStatus.textContent = "⚠️ İstifadəçi yedəyi yoxlanmadı.";
    }
}


function setPriceFields(amountId, freeId, rule) {
    const amount = document.getElementById(amountId);
    const free = document.getElementById(freeId);
    if (!amount || !free) return;
    free.checked = !!rule?.free;
    amount.value = (Number(rule?.cents || 0) / 100).toFixed(2);
    amount.disabled = free.checked;
}

function onPriceFreeToggle(amountId, freeId) {
    const amount = document.getElementById(amountId);
    const free = document.getElementById(freeId);
    amount.disabled = free.checked;
    if (free.checked) amount.value = "0.00";
    else if (Number(amount.value) <= 0) amount.value = "0.01";
}

function countryPriceChanged() {
    const iso = document.getElementById("country-pricing-select").value;
    setPriceFields("country-pricing-amount", "country-pricing-free", countryPriceRule(iso));
}

function rangePriceChanged() {
    const rid = document.getElementById("range-pricing-id").value.trim();
    const rule = state.pricing?.range?.[rid] || {cents: 0, free: true};
    setPriceFields("range-pricing-amount", "range-pricing-free", rule);
}

function renderAdminPrices() {
    if (!state.isAdmin || !state.pricing) return;
    const status = document.getElementById("admin-prices-status");
    if (!status) return;
    status.textContent = "✅ Qiymətlər aktivdir · Valyuta: AZN · " +
        Object.keys(state.pricing.country || {}).length + " ölkə qaydası · " +
        Object.keys(state.pricing.range || {}).length + " range qaydası";
    const search = document.getElementById("country-pricing-search");
    const select = document.getElementById("country-pricing-select");
    const selected = select.value || "AZ";
    const term = String(search.value || "").trim().toLocaleLowerCase();
    const rows = state.countries.filter(c =>
        c.name.toLocaleLowerCase().includes(term) ||
        c.iso.toLocaleLowerCase().includes(term) ||
        String(c.prefix).includes(term.replace(/^\+/, "")));
    select.replaceChildren();
    for (const c of rows) {
        const option = document.createElement("option");
        option.value = c.iso;
        option.textContent = c.flag + " " + c.name + " (+" + c.prefix + ") · " + priceLabel(countryPriceRule(c.iso));
        select.appendChild(option);
    }
    if (rows.length) select.value = rows.some(c => c.iso === selected) ? selected : rows[0].iso;
    countryPriceChanged();
    setPriceFields("default-pricing-amount", "default-pricing-free", state.pricing.default);
    const list = document.getElementById("admin-range-prices-list");
    list.replaceChildren();
    const entries = Object.entries(state.pricing.range || {}).sort((a,b)=>a[0].localeCompare(b[0]));
    if (!entries.length) {
        list.appendChild(node("p", "Hələ ayrıca range qiyməti yoxdur.", "notice-mini"));
    }
    for (const [rid, rule] of entries) {
        const btn = node("button", "+" + rid + " · " + priceLabel(rule), "catalog-row");
        btn.type = "button";
        btn.addEventListener("click", () => {
            document.getElementById("range-pricing-id").value = rid;
            rangePriceChanged();
            document.getElementById("range-pricing-id").scrollIntoView?.({block:"nearest",behavior:"smooth"});
        });
        list.appendChild(btn);
    }
    rangePriceChanged();
}

async function submitAdminPrice(body) {
    if (!state.isAdmin) return;
    const status = document.getElementById("admin-prices-status");
    status.textContent = "Qiymət yadda saxlanır...";
    try {
        const result = await api("/api/prices", {method: "POST", body});
        state.pricing = result.pricing;
        refreshAzPriceNotes();
        renderAdminPrices();
        if (state.countries.length) renderCountries();
        alertUser("✅ Qiymət qaydası yeniləndi.");
    } catch (error) {
        status.textContent = "⚠️ " + error.message;
        alertUser(error.message);
    }
}

function chosenPrice(prefix) {
    const free = document.getElementById(prefix + "-free").checked;
    const amount = document.getElementById(prefix + "-amount").value.trim();
    if (!free && (!/^\d+(?:\.\d{1,2})?$/.test(amount) || Number(amount) <= 0 || Number(amount) > 10000)) {
        alertUser("Qiymət 0.01–10000 AZN arası, maksimum 2 onluq olmalıdır.");
        return null;
    }
    return {price: free ? "0" : amount, free};
}

function saveAdminCountryPrice() {
    const country_iso = document.getElementById("country-pricing-select").value;
    if (!country_iso) return alertUser("Ölkə seçin.");
    const rule = chosenPrice("country-pricing");
    if (rule) submitAdminPrice({action:"set_country",country_iso,...rule});
}
function resetAdminCountryPrice() {
    const country_iso = document.getElementById("country-pricing-select").value;
    if (country_iso) submitAdminPrice({action:"reset_country",country_iso});
}
function saveAdminRangePrice() {
    const range = document.getElementById("range-pricing-id").value.trim();
    if (!/^\d{1,10}$/.test(range)) return alertUser("API range kodu 1–10 rəqəm olmalıdır.");
    const rule = chosenPrice("range-pricing");
    if (rule) submitAdminPrice({action:"set_range",range,...rule});
}
function resetAdminRangePrice() {
    const range = document.getElementById("range-pricing-id").value.trim();
    if (!/^\d{1,10}$/.test(range)) return alertUser("Düzgün range daxil edin.");
    submitAdminPrice({action:"reset_range",range});
}
function saveAdminDefaultPrice() {
    const rule = chosenPrice("default-pricing");
    if (rule) submitAdminPrice({action:"set_default",...rule});
}

async function sendAdminToolAction(action, details = {}) {
    if (!state.isAdmin) return null;
    return api("/api/admin-tools", {method: "POST", body: {action, ...details}});
}

async function saveAiPostSettings() {
    if (!state.isAdmin) return;
    try {
        await sendAdminToolAction("ai_settings", {
            enabled: document.getElementById("ai-post-enabled").checked,
            style: document.getElementById("ai-post-style").value
        });
        await loadAdminTools();
        alertUser("✅ AI paylaşım parametrləri saxlanıldı.");
    } catch (err) { alertUser(err.message); }
}

async function previewAiPost() {
    if (!state.isAdmin) return;
    const preview = document.getElementById("ai-post-preview");
    preview.hidden = false;
    preview.textContent = "Nümunə hazırlanır...";
    try {
        const result = await sendAdminToolAction("ai_preview");
        preview.textContent = result.preview || "Nümunə mövcud deyil.";
    } catch (err) {
        preview.textContent = "⚠️ " + err.message;
    }
}

async function saveWorldNewsSettings() {
    if (!state.isAdmin) return;
    try {
        await sendAdminToolAction("world_news_settings", {
            enabled: document.getElementById("world-news-enabled").checked,
            interval_minutes: Number(document.getElementById("world-news-interval").value)
        });
        await loadAdminTools();
        alertUser("✅ Dünya xəbərləri üçün ayarlar saxlanıldı.");
    } catch (err) { alertUser(err.message); }
}

async function previewWorldNews() {
    if (!state.isAdmin) return;
    const area = document.getElementById("world-news-preview");
    area.hidden = false;
    area.textContent = "Son xəbərlər yoxlanılır...";
    try {
        const response = await sendAdminToolAction("world_news_preview");
        area.textContent = response.preview || "Xəbər nümunəsi mövcud deyil.";
    } catch (err) {
        area.textContent = "⚠️ " + err.message;
    }
}

async function saveAdminSettings() {
    if (!state.isAdmin) return;
    const min = Number(document.getElementById("cfg-min-withdraw").value);
    const max = Number(document.getElementById("cfg-max-withdraw").value);
    if (!Number.isInteger(min) || !Number.isInteger(max) || min < 1 || min > max || max > 100000) {
        alertUser("Minimum və maksimum üçün düzgün rəqəmlər seçin.");
        return;
    }
    const methods = {};
    document.querySelectorAll("#cfg-payment-methods input[data-method]").forEach(checkbox => {
        methods[checkbox.dataset.method] = !!checkbox.checked;
    });
    try {
        await sendAdminToolAction("save_settings",
            {min_withdraw: min, max_withdraw: max, payment_methods: methods});
        alertUser("✅ Ödəniş parametrləri yeniləndi.");
        await loadAdminTools();
    } catch (err) { alertUser(err.message); }
}

async function adminAddChannel() {
    if (!state.isAdmin) return;
    const link = document.getElementById("admin-channel-link").value.trim();
    const label = document.getElementById("admin-channel-label").value.trim();
    const chatId = document.getElementById("admin-channel-chat-id").value.trim();
    if (!/^https:\/\/t\.me\//.test(link)) {
        alertUser("Etibarlı t.me kanal keçidi daxil edin.");
        return;
    }
    try {
        await sendAdminToolAction("add_channel", {link, label, chat_id: chatId});
        alertUser("✅ Kanal əlavə edildi.");
        await loadAdminTools();
    } catch (err) { alertUser(err.message); }
}

async function adminRemoveChannel(link) {
    if (!state.isAdmin) return;
    if (!window.confirm("Bu kanalı siyahıdan silmək istəyirsiniz?")) return;
    try {
        await sendAdminToolAction("remove_channel", {link});
        alertUser("✅ Kanal silindi.");
        await loadAdminTools();
    } catch (err) { alertUser(err.message); }
}

async function adminSendGroupNotice() {
    if (!state.isAdmin) return;
    const field = document.getElementById("admin-group-notice");
    const message = field.value.trim();
    if (message.length < 5 || message.length > 600) {
        alertUser("5–600 simvol uzunluğunda məlumat yazın.");
        return;
    }
    if (!window.confirm("Bu mətni konfiqurasiya edilmiş məlumat qrupunda paylaşmaq istəyirsiniz?")) return;
    try {
        const result = await sendAdminToolAction("group_notice", {message});
        if (!result.ok) throw new Error(result.message || "Göndərilmədi.");
        field.value = "";
        alertUser("✅ " + (result.message || "Bildiriş göndərildi."));
    } catch (err) { alertUser(err.message); }
}

async function adminWhatsAppTest() {
    if (!state.isAdmin) return;
    if (!window.confirm("Yalnız əvvəlcədən razılaşdırılmış WhatsApp sınaq alıcısına 1 sabit test mesajı göndərilsin?")) return;
    try {
        const result = await sendAdminToolAction("whatsapp_test");
        alertUser(result.message || "WhatsApp testi tamamlandı.");
    } catch (err) { alertUser(err.message); }
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
    if (window.websiteAuth && !(await window.websiteAuth.ensureAuthenticated())) return;
    const serviceSearch = document.getElementById("service-search");
    if (serviceSearch) serviceSearch.addEventListener("input", () => {
        state.serviceQuery = serviceSearch.value;
        renderServices();
    });
    const search = document.getElementById("country-search");
    search.addEventListener("input", () => {
        state.countryFilter = search.value.trim().toLocaleLowerCase();
        state.countryPage = 0;
        renderCountries();
    });
    document.getElementById("country-pricing-search").addEventListener("input", renderAdminPrices);
    document.getElementById("country-pricing-select").addEventListener("change", countryPriceChanged);
    document.getElementById("range-pricing-id").addEventListener("input", rangePriceChanged);
    for (const prefix of ["country-pricing", "range-pricing", "default-pricing"]) {
        document.getElementById(prefix + "-free").addEventListener("change",
            () => onPriceFreeToggle(prefix + "-amount", prefix + "-free"));
    }
    await fetchPrices();
    await Promise.all([fetchDashboard(), fetchServices(), fetchCountries(), fetchOrders()]);
    await checkNewOtpNotifications();
    window.setInterval(checkNewOtpNotifications, 10000);
    if (state.isAdmin) renderAdminPrices();
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
