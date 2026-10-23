/* Azerbaijan SMS provider diagnostics: metadata only.
   This does not request OTP contents, allocate numbers or expose phone numbers.
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

    async function load() {
        const panel = output();
        const button = document.getElementById("az-provider-refresh");
        if (!panel || !button) return;
        button.disabled = true;
        panel.replaceChildren(node("p", "API range siyahısı yoxlanılır...", "notice-mini"));
        try {
            const initData = window.Telegram?.WebApp?.initData;
            if (!initData) throw new Error("Bu yoxlama üçün Mini App-i Telegram botundan açın.");
            const response = await fetch(API_URL + "/api/services", {
                headers: {"X-Telegram-Init-Data": initData},
                cache: "no-store"
            });
            if (!response.ok) {
                throw new Error("API bağlantısı: HTTP " + response.status);
            }
            const result = await response.json();
            if (!result.services || typeof result.services !== "object") {
                throw new Error("API-nin xidmət siyahısı boşdur və ya düzgün deyil.");
            }
            const present = new Set();
            let services = 0;
            for (const ranges of Object.values(result.services)) {
                if (!Array.isArray(ranges)) continue;
                services++;
                for (const range of ranges) {
                    const rid = digits(range);
                    if (/^994\d{2,7}$/.test(rid)) present.add(rid);
                }
            }
            const az = [...present].sort();
            panel.replaceChildren();
            panel.appendChild(node("p",
                "Mini App kataloq sorğusu: HTTP 200 · " + services + " xidmət · " +
                az.length + " fərqli +994 range qeyd edilib.",
                "notice-mini"));
            panel.appendChild(node("p",
                "Bunlar API-nin xidmət kataloqundan gəlir. SMS qəbulunu, " +
                "təsdiq kodunun çatmasını və boş nömrə ehtiyatını sübut etmir.",
                "notice-mini"));

            for (const [name, prefixes] of OPERATORS) {
                const found = az.filter(r => prefixes.some(p => r.startsWith(p)));
                const section = node("details", undefined, "operator-group");
                section.appendChild(node("summary", name + " — " + found.length + " API range"));
                for (const prefix of prefixes) {
                    const row = node("p", "+" + prefix + " → " +
                        ["210", "211"].map(suffix => {
                            const exact = prefix + suffix;
                            return exact + (present.has(exact) ? " ✅" : " ❔ API-də yoxdur");
                        }).join(" | "), "notice-mini");
                    section.appendChild(row);
                }
                section.appendChild(node("p",
                    found.length ? "Digər API range-ləri: " + found.join(", ") :
                        "Bu operator üçün API kataloqunda range tapılmadı.",
                    "notice-mini"));
                panel.appendChild(section);
            }
            panel.appendChild(node("p", "Son siyahı yoxlaması: " +
                new Date().toLocaleTimeString("az-AZ"), "notice-mini"));
        } catch (err) {
            panel.replaceChildren(node("p",
                "⚠️ " + (err?.message || "Provayder siyahısı yoxlana bilmədi."),
                "notice-mini"));
        } finally {
            button.disabled = false;
        }
    }

    // Deliberately read-only. The user requests a refresh with an explicit click.
    window.refreshAzProviderDiagnostics = load;
})();
