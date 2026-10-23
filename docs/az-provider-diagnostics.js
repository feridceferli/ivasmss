/* Read-only operator diagnostics for Azerbaijan (+994).

   Data sources:
     /api/services  -> ranges ADVERTISED in the provider catalog
     /api/dashboard -> active numbers belonging to the signed-in Telegram user

   Neither source proves that an unallocated phone number is in stock or can
   receive SMS. This tool never calls allocation or OTP endpoints.
*/
(function () {
    "use strict";
    const API_URL = "https://ivasmss.onrender.com";
    const OPERATORS = [
        ["Bakcell", ["99455", "99499"]],
        ["Azercell", ["99450", "99451", "99410"]],
        ["Nar", ["99470", "99477"]],
        ["Naxtell", ["99460"]],
        ["Catel", ["99440"]],
        ["CDMA", ["99444"]]
    ];

    const node = (tag, value, className) => {
        const e = document.createElement(tag);
        if (value !== undefined) e.textContent = String(value);
        if (className) e.className = className;
        return e;
    };

    const digits = value => String(value ?? "").replace(/\D/g, "");
    const output = () => document.getElementById("az-provider-diagnostics");
    const belongsTo = (digitsValue, prefixes) =>
        prefixes.some(prefix => digitsValue.startsWith(prefix));

    function collectListedRanges(services) {
        const advertised = new Map();
        for (const [service, ranges] of Object.entries(services || {})) {
            if (!Array.isArray(ranges)) continue;
            for (const item of ranges) {
                const rid = digits(item);
                if (!/^994\d{2,7}$/.test(rid)) continue;
                if (!advertised.has(rid)) advertised.set(rid, new Set());
                advertised.get(rid).add(String(service));
            }
        }
        return advertised;
    }

    function myActiveAzNumbers(dashboard) {
        const unique = new Map();
        for (const order of (dashboard?.orders || [])) {
            if (!order || typeof order !== "object") continue;
            const raw = String(order.number || "");
            const number = digits(raw);
            // Dashboard is already Telegram-authenticated and owner-scoped.
            // Don't infer the full number from number_masked or other fields.
            if (!/^\+994\d{8,10}$/.test(raw) ||
                !/^994\d{8,10}$/.test(number)) continue;
            const remaining = Number(order.remaining_seconds);
            if (Number.isFinite(remaining) && remaining <= 0) continue;
            unique.set(number, {
                number: "+" + number,
                range: String(order.range || ""),
                remaining: Number.isFinite(remaining) ? remaining : null
            });
        }
        return [...unique.values()];
    }

    function displayOperator(panel, operator, ranges, ownNumbers) {
        const [name, prefixes] = operator;
        const listed = [...ranges.keys()].filter(rid => belongsTo(rid, prefixes)).sort();
        const mine = ownNumbers.filter(item => belongsTo(digits(item.number), prefixes));
        const section = node("details", undefined, "operator-group");
        section.appendChild(node("summary", name + " · API range: " + listed.length +
            " · Mənim aktiv nömrəm: " + mine.length));

        for (const prefix of prefixes) {
            const scoped = listed.filter(rid => rid.startsWith(prefix));
            const own = mine.filter(item => digits(item.number).startsWith(prefix));
            const sub = node("details", undefined, "operator-prefix");
            sub.appendChild(node("summary", "+" + prefix + " · API: " +
                scoped.length + " range · Mənim aktiv: " + own.length));

            const presets = ["210", "211"].map(suffix => {
                const id = prefix + suffix;
                return id + (ranges.has(id) ? " ✅ API siyahısında" : " ❔ API-də təsdiqlənmir");
            });
            sub.appendChild(node("p", presets.join(" | "), "notice-mini"));
            if (scoped.length) {
                const list = node("div", undefined, "catalog-scroll");
                for (const rid of scoped) {
                    const services = [...(ranges.get(rid) || [])].sort();
                    list.appendChild(node("p", "📡 " + rid +
                        " · Xidmətlər: " + services.join(", "), "notice-mini"));
                }
                sub.appendChild(list);
            } else {
                sub.appendChild(node("p", "Bu prefiks üçün API-də elan edilmiş range yoxdur.",
                    "notice-mini"));
            }

            if (!own.length) {
                sub.appendChild(node("p", "Bu prefiks üzrə hesabımda aktiv nömrə yoxdur.",
                    "notice-mini"));
            }
            for (const ownOrder of own) {
                const row = node("div", undefined, "admin-user-line");
                row.appendChild(node("span", "📱 " + ownOrder.number +
                    (ownOrder.remaining === null ? "" :
                        " · " + Math.ceil(ownOrder.remaining / 60) + " dəq qalıb")));
                const copy = node("button", "📋 Kopyala", "action-small");
                copy.type = "button";
                copy.addEventListener("click", async () => {
                    try {
                        await navigator.clipboard.writeText(ownOrder.number);
                        copy.textContent = "✅ Kopyalandı";
                    } catch (_) {
                        copy.textContent = "⚠️ Aktivlərdən kopyalayın";
                    }
                });
                row.appendChild(copy);
                sub.appendChild(row);
            }
            section.appendChild(sub);
        }
        panel.appendChild(section);
    }

    async function load() {
        const panel = output();
        const button = document.getElementById("az-provider-refresh");
        if (!panel || !button) return;
        button.disabled = true;
        panel.replaceChildren(node("p", "Bütün +994 operatorlarının statusu yoxlanılır...",
            "notice-mini"));
        try {
            const initData = window.Telegram?.WebApp?.initData;
            if (!initData) throw new Error("Yoxlama üçün Mini App-i Telegram botundan açın.");
            const headers = {"X-Telegram-Init-Data": initData};
            const [servicesResponse, dashboardResponse] = await Promise.all([
                fetch(API_URL + "/api/services", {headers, cache: "no-store"}),
                fetch(API_URL + "/api/dashboard", {headers, cache: "no-store"})
            ]);
            if (!servicesResponse.ok)
                throw new Error("Range kataloqu: HTTP " + servicesResponse.status);
            if (!dashboardResponse.ok)
                throw new Error("Şəxsi aktiv nömrələr: HTTP " + dashboardResponse.status);

            const [result, dashboard] = await Promise.all([
                servicesResponse.json(), dashboardResponse.json()
            ]);
            if (!result.services || typeof result.services !== "object" ||
                !Array.isArray(dashboard.orders)) {
                throw new Error("API cavabında xidmətlər və ya aktiv sifariş məlumatı yoxdur.");
            }

            const listed = collectListedRanges(result.services);
            const owned = myActiveAzNumbers(dashboard);
            const knownOperators = new Set(OPERATORS.flatMap(entry => entry[1]));
            const listedUnknown = [...listed.keys()].filter(r =>
                ![...knownOperators].some(prefix => r.startsWith(prefix)));

            panel.replaceChildren();
            panel.appendChild(node("p", "Kataloq sorğusu: HTTP 200 · " +
                listed.size + " fərqli +994 range · Mənim aktiv nömrələrim: " +
                owned.length, "notice-mini"));
            panel.appendChild(node("p",
                "⚠️ API siyahısındakı range aktiv/satışda nömrə olduğunu və SMS/OTP " +
                "çatdırılmasını təsdiqləmir. Burada yalnız sizə ayrılmış aktiv " +
                "nömrələr tam görünür; başqa istifadəçilərin nömrələri göstərilmir.",
                "notice-mini"));

            for (const operator of OPERATORS) displayOperator(panel, operator, listed, owned);

            if (listedUnknown.length) {
                const other = node("details", undefined, "operator-group");
                other.appendChild(node("summary", "🌍 Digər +994 range-lər · " +
                    listedUnknown.length));
                other.appendChild(node("p", listedUnknown.join(", "), "notice-mini"));
                panel.appendChild(other);
            }
            panel.appendChild(node("p", "Son kataloq yoxlaması: " +
                new Date().toLocaleTimeString("az-AZ"), "notice-mini"));
        } catch (error) {
            panel.replaceChildren(node("p", "⚠️ " +
                (error?.message || "Status yoxlana bilmədi."), "notice-mini"));
        } finally {
            button.disabled = false;
        }
    }

    window.refreshAzProviderDiagnostics = load;
})();
