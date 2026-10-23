/* World phone-code diagnostics — read-only, owner-scoped, all countries.

   /api/countries provides every country and the provider's advertised range
   counts; /api/dashboard returns only this Telegram user's active allocations.
   A catalog entry is not proof of an available phone number or SMS delivery.
   No OTP, unassigned number, or third-party user's number is accessed.
*/
(function () {
    "use strict";

    const API = "https://ivasmss.onrender.com";
    const PAGE_SIZE = 25;
    const state = {
        countries: [],
        assignedByCode: new Map(),
        query: "",
        page: 0,
        totalMyNumbers: 0,
        lastRefresh: null,
        loaded: false,
        selectedIso: null
    };

    const get = id => document.getElementById(id);
    const create = (tag, text, cls) => {
        const element = document.createElement(tag);
        if (text !== undefined && text !== null) element.textContent = String(text);
        if (cls) element.className = cls;
        return element;
    };
    const cleanDigits = value => String(value ?? "").replace(/\D/g, "");

    async function request(path) {
        const initData = window.Telegram?.WebApp?.initData;
        if (!initData) throw new Error("Mini App-i Telegram botunun içindən açın.");
        const response = await fetch(API + path, {
            headers: {"X-Telegram-Init-Data": initData},
            cache: "no-store"
        });
        if (!response.ok) {
            throw new Error(response.status === 401
                ? "Telegram girişi təsdiqlənmədi. Mini App-i botdan açın."
                : "Server cavabı: HTTP " + response.status);
        }
        return response.json();
    }

    function mapMyActiveNumbers(orders, countries) {
        // This list comes only from the authenticated user's /api/dashboard.
        // Do not use masked values to guess a number or use third-party data.
        const unique = new Map();
        for (const order of Array.isArray(orders) ? orders : []) {
            if (!order || typeof order !== "object") continue;
            const phone = String(order.number || "");
            if (!/^\+[1-9]\d{3,14}$/.test(phone)) continue;
            const remaining = Number(order.remaining_seconds);
            if (!Number.isFinite(remaining) || remaining <= 0) continue;
            const created = Number(order.created_at) || 0;
            const previous = unique.get(phone);
            if (previous && previous.created >= created) continue;
            unique.set(phone, {
                number: phone,
                digits: cleanDigits(phone),
                range: String(order.range || ""),
                remaining: Math.max(0, Math.floor(remaining)),
                created
            });
        }

        // Longest-code matching prevents +1246 from being treated as +1.
        const codes = [...new Set(countries.map(c => String(c.prefix || "")))]
            .filter(code => /^[1-9]\d{0,3}$/.test(code))
            .sort((a, b) => b.length - a.length || a.localeCompare(b));
        const group = new Map();
        for (const order of unique.values()) {
            const code = codes.find(c => order.digits.startsWith(c));
            if (!code) continue;
            if (!group.has(code)) group.set(code, []);
            group.get(code).push(order);
        }
        for (const values of group.values()) {
            values.sort((a, b) => b.created - a.created);
        }
        return {group, total: unique.size};
    }

    function ownNumbersFor(country) {
        return state.assignedByCode.get(String(country.prefix)) || [];
    }

    async function copyOne(number, button) {
        // Reuse the same clipboard fallback as the Mini App Active tab.
        try {
            if (typeof copyPhoneNumber === "function") {
                const copied = await copyPhoneNumber(number, false);
                button.textContent = copied ? "✅ Kopyalandı" : "⚠️ Aktivlərdən kopyala";
                return;
            }
            await navigator.clipboard.writeText(number);
            button.textContent = "✅ Kopyalandı";
        } catch (_) {
            button.textContent = "⚠️ Aktivlərdən kopyala";
        }
    }

    function makeNumberRow(item) {
        const row = create("div", null, "admin-user-line");
        const minutes = Math.ceil(item.remaining / 60);
        const label = create("span", "📱 " + item.number + " · " +
            minutes + " dəq qalıb");
        label.className = "full-phone-number";
        row.appendChild(label);
        const button = create("button", "📋 Kopyala", "action-small");
        button.type = "button";
        button.addEventListener("click", () => copyOne(item.number, button));
        row.appendChild(button);
        return row;
    }

    async function countryDetails(country) {
        const host = get("world-diagnostic-detail");
        if (!host) return;
        const iso = country.iso;
        state.selectedIso = iso;
        host.hidden = false;
        host.replaceChildren();
        host.appendChild(create("h4", country.flag + " " + country.name +
            " (+" + country.prefix + ")"));

        const own = ownNumbersFor(country);
        host.appendChild(create("p", "📡 API range: " + Number(country.count || 0) +
            " · 📱 Mənim aktiv nömrələrim: " + own.length, "notice-mini"));
        if (country.is_shared) {
            host.appendChild(create("p",
                "⚠️ Bu telefon kodunu bir neçə ölkə paylaşır. Göstərilən " +
                "nömrənin konkret hansı ölkəyə aid olduğu təsdiqlənmir; " +
                "eyni nömrə ortaq kodlu ölkələrin bölmələrində görünə bilər.",
                "notice-mini"));
        }
        if (!own.length) {
            host.appendChild(create("p", "Bu kod üzrə hesabımda aktiv nömrə yoxdur.",
                "notice-mini"));
        }
        for (const item of own) host.appendChild(makeNumberRow(item));

        if (Number(country.count) > 0) {
            const rangeList = create("div");
            rangeList.appendChild(create("p", "API range-ləri yoxlanılır...", "notice-mini"));
            host.appendChild(rangeList);
            try {
                const response = await request("/api/countries?iso=" + encodeURIComponent(iso));
                if (state.selectedIso !== iso) return;
                rangeList.replaceChildren();
                const ranges = response.country?.ranges || [];
                if (!ranges.length) {
                    rangeList.appendChild(create("p", "API-də elan olunmuş range yoxdur.",
                        "notice-mini"));
                } else {
                    const heading = create("details", null, "operator-group");
                    heading.appendChild(create("summary", "📡 Xidmət və range-lər (" +
                        ranges.length + ")"));
                    const scroll = create("div", null, "catalog-scroll");
                    for (const entry of ranges) {
                        // Advertised range metadata, not real unassigned phone numbers.
                        scroll.appendChild(create("p", String(entry.rid || "") +
                            " · " + String(entry.service || ""), "notice-mini"));
                    }
                    heading.appendChild(scroll);
                    rangeList.appendChild(heading);
                }
            } catch (error) {
                if (state.selectedIso === iso) {
                    rangeList.replaceChildren(create("p", "Range detalları: " +
                        error.message, "notice-mini"));
                }
            }
        }
        const back = create("button", "✕ Detalları bağla", "action-small");
        back.addEventListener("click", () => {
            host.hidden = true;
            state.selectedIso = null;
        });
        host.appendChild(back);
        host.scrollIntoView?.({behavior: "smooth", block: "nearest"});
    }

    function render() {
        const list = get("world-diagnostic-list");
        if (!list || !state.loaded) return;
        const query = state.query.toLocaleLowerCase();
        const normalized = query.replace(/^\+/, "");
        const matches = state.countries.filter(c =>
            !query || String(c.name).toLocaleLowerCase().includes(query) ||
            String(c.iso).toLocaleLowerCase().includes(query) ||
            String(c.prefix).includes(normalized));
        const totalPages = Math.max(1, Math.ceil(matches.length / PAGE_SIZE));
        state.page = Math.min(Math.max(state.page, 0), totalPages - 1);

        list.replaceChildren();
        if (!matches.length) list.appendChild(create("p",
            "Bu axtarış üzrə ölkə tapılmadı.", "notice-mini"));
        for (const country of matches.slice(state.page * PAGE_SIZE,
                                              (state.page + 1) * PAGE_SIZE)) {
            const row = create("button", null, "catalog-row");
            row.type = "button";
            const ownCount = ownNumbersFor(country).length;
            row.appendChild(create("span", country.flag + " " + country.name +
                " (+" + country.prefix + ")" +
                (country.is_shared ? " ⚠️ ortaq kod" : "")));
            row.appendChild(create("small", "📡 " + Number(country.count || 0) +
                " · 📱 " + ownCount));
            row.addEventListener("click", () => countryDetails(country));
            list.appendChild(row);
        }
        get("world-diagnostic-page").textContent = state.page + 1 + " / " + totalPages;
        get("world-diagnostic-prev").disabled = state.page === 0;
        get("world-diagnostic-next").disabled = state.page + 1 >= totalPages;
    }

    async function load() {
        const button = get("world-diagnostic-refresh");
        const list = get("world-diagnostic-list");
        if (!button || !list) return;
        button.disabled = true;
        state.loaded = false;
        list.replaceChildren(create("p",
            "🌍 Bütün ölkələr və şəxsi aktiv nömrələr yoxlanılır...", "notice-mini"));
        try {
            const [countriesRes, dashboard] = await Promise.all([
                request("/api/countries"), request("/api/dashboard")
            ]);
            if (!Array.isArray(countriesRes.countries) ||
                !Array.isArray(dashboard.orders)) {
                throw new Error("Ölkə siyahısı və ya aktiv sifariş cavabı düzgün deyil.");
            }

            state.countries = countriesRes.countries;
            const mapped = mapMyActiveNumbers(dashboard.orders, state.countries);
            state.assignedByCode = mapped.group;
            state.totalMyNumbers = mapped.total;
            state.lastRefresh = new Date();
            state.loaded = true;
            state.page = 0;
            const providerListed = state.countries.filter(c => Number(c.count) > 0).length;
            get("world-diagnostic-summary").textContent =
                "🌍 " + state.countries.length + " ölkə və ərazi · 📡 " +
                providerListed + " ölkə kodunda API range-i qeyd olunub · 📱 " +
                state.totalMyNumbers + " fərqli aktiv nömrəm var. " +
                "Yoxlama: " + state.lastRefresh.toLocaleTimeString("az-AZ");
            const detail = get("world-diagnostic-detail");
            if (detail) {
                detail.hidden = true;
                state.selectedIso = null;
            }
            render();
        } catch (error) {
            list.replaceChildren(create("p", "⚠️ " +
                (error?.message || "Ölkə diaqnostikası aparılmadı."),
                "notice-mini"));
            get("world-diagnostic-summary").textContent =
                "Ölkə və aktiv nömrə yoxlaması uğursuz oldu.";
        } finally {
            button.disabled = false;
        }
    }

    function changePage(direction) {
        if (!state.loaded) return;
        state.page += direction;
        render();
    }

    function init() {
        const search = get("world-diagnostic-search");
        if (search) search.addEventListener("input", () => {
            state.query = search.value.trim();
            state.page = 0;
            render();
        });
    }

    window.refreshWorldProviderDiagnostics = load;
    window.changeWorldDiagnosticPage = changePage;
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
