/* AZE SMS PANEL Mini App — Telegram-verified, mobile-first interface.
   All country/range metadata comes from the same Render backend as the bot.
   No referral gate, no invented stock, no secrets in the browser.
*/
const tg = window.Telegram.WebApp;
tg.expand();

const API_BASE = "https://ivasmss.onrender.com";
const TABS = ["services", "countries", "azerbaijan", "active", "history", "twofa", "leaderboard", "profile", "withdrawals", "guide", "admin"];
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
    serviceQuery: ""
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
    } else if (tab === "twofa") {
        document.getElementById("totp-output").textContent = "— — — — — —";
        document.getElementById("totp-secret").value = "";
        lastLocal2faCode = "";
    } else if (tab === "leaderboard") {
        fetchLeaderboard();
    } else if (tab === "profile") {
        fetchProfile();
    } else if (tab === "withdrawals") {
        fetchWithdrawals();
    } else if (tab === "admin") {
        fetchAdminUsers();
        loadAdminTools();
        fetchAdminWithdrawals();
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

function addRangeButton(container, label, options) {
    const button = node("button", label + (options.isAz ? " · 10 AZN" : ""), "catalog-row catalog-range");
    button.type = "button";
    const locked = options.isAz && !state.azApproved;
    if (locked) button.title = "10 AZN · +994 üçün admin təsdiqi tələb olunur";
    button.addEventListener("click", () => {
        if (locked) {
            alertUser("🔒 +994 range qiyməti: 10 AZN. İstifadə üçün admin icazəsi alın: @lacin_0411.");
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
                "🇦🇿 +994 range qiyməti: 10 AZN. İstifadə üçün admin icazəsi lazımdır. " +
                "Bu panel avtomatik balans çıxmır.", "az-price-note"));
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
        document.getElementById("country-az-pricing").hidden = c.prefix !== "994";
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
    if (String(range).startsWith("994")) {
        if (!state.azApproved) {
            alertUser("+994 nömrəsi üçün admin icazəsi lazımdır. Qiymət: 10 AZN. Admin: @lacin_0411.");
            switchTab("azerbaijan");
            return;
        }
        if (!window.confirm(
            "🇦🇿 +994 range qiyməti 10 AZN olaraq göstərilir. Bu Mini App avtomatik ödəniş tutmur. " +
            "Seçilmiş range üçün nömrə sorğusu göndərilsin?"
        )) return;
    }
    // A separate authenticated API request is made only on an explicit click.
    try {
        const data = await api("/api/get-number", {
            method: "POST",
            body: { service, country, range, country_iso: countryIso }
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



function renderWithdrawals(container, records, admin) {
    container.replaceChildren();
    if (!records.length) {
        clearAndText(container, "Çıxarış sorğusu yoxdur.");
        return;
    }
    for (const r of records) {
        const row = node("div", null, "sms-item");
        const header = admin ? "İstifadəçi: " + String(r.user_id || "—") + " · " : "";
        row.appendChild(node("strong", header + String(r.method || "Çıxarış") +
            " · " + String(r.amount || "0") + " AZN"));
        row.appendChild(node("p", "Status: " + String(r.status || "pending") +
            " · " + String(r.time || "—") + " · ID " + String(r.id || ""), "notice-mini"));
        container.appendChild(row);
    }
}

async function fetchWithdrawals() {
    const container = document.getElementById("withdrawals-list");
    try {
        const result = await api("/api/withdrawals");
        renderWithdrawals(container, result.withdrawals || [], false);
    } catch (err) {
        clearAndText(container, "Sorğular yüklənmədi: " + err.message);
    }
}

async function fetchAdminWithdrawals() {
    if (!state.isAdmin) return;
    const container = document.getElementById("admin-withdrawals-list");
    try {
        const result = await api("/api/withdrawals?scope=admin");
        renderWithdrawals(container, result.withdrawals || [], true);
    } catch (err) {
        clearAndText(container, "Admin sorğuları yüklənmədi: " + err.message);
    }
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
        const wa = adminTools.whatsapp || {};
        const archive = adminTools.archive_sync || {};
        status.textContent = "📡 WhatsApp: " + (wa.status === "configured" ? "✅ Ayarlanıb" : "⚠️ Ayarlanmayıb") +
            (wa.test_recipient ? " · " + wa.test_recipient : "") +
            " · 📥 Arxiv: " + (archive.status || "naməlum") +
            " · 📨 Bildiriş qrupu: " +
            (adminTools.notification_group_configured ? "✅" : "⚠️ Ayarlanmayıb");
    } catch (err) {
        status.textContent = "⚠️ Admin alətləri: " + err.message;
    }
}

async function sendAdminToolAction(action, details = {}) {
    if (!state.isAdmin) return null;
    return api("/api/admin-tools", {method: "POST", body: {action, ...details}});
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
        if (state.activeTab === "withdrawals") fetchWithdrawals();
    }, 30000);
});
