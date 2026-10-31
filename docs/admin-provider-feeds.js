/* Authorized, admin-only external feeds. Never expose API tokens to the browser. */
(function () {
    "use strict";

    const NAMES = {
        green_sms: "Green SMS",
        ivasmsper: "Ivasmsper"
    };

    const $ = (id) => document.getElementById(id);
    function block(text, className = "notice-mini") {
        const p = document.createElement("p");
        p.className = className;
        p.textContent = String(text);
        return p;
    }

    function sourceStatus(provider, meta) {
        const node = $("admin-" + provider + "-status");
        if (!node) return;
        if (!meta) {
            node.textContent = "⚠️ Provayderin vəziyyətini oxumaq mümkün olmadı.";
            return;
        }
        const active = meta.rest_configured || meta.websocket_configured;
        const pieces = [];
        if (meta.rest_configured) pieces.push("REST hazırdır");
        if (meta.websocket_configured) pieces.push(
            meta.live_connected ? "WebSocket qoşulub" : "WebSocket gözləyir"
        );
        node.textContent = active
            ? "✅ " + pieces.join(" · ") + " · Yalnız admin"
            : "⚙️ Render Environment-də bu mənbənin öz API məlumatlarını daxil edin.";
    }

    async function loadAdminProviderFeeds() {
        if (!state.isAdmin) return;
        try {
            const data = await api("/api/admin-provider-feeds");
            for (const name of Object.keys(NAMES)) {
                sourceStatus(name, (data.providers || {})[name]);
                loadAdminProviderNumbers(name);
            }
        } catch (error) {
            for (const name of Object.keys(NAMES)) sourceStatus(name, null);
        }
    }

    async function copyPrivate(value) {
        try {
            await navigator.clipboard.writeText(value);
            toast("✅ Kopyalandı.", "success");
        } catch (_) {
            toast("Kopyalama mümkün olmadı.", "error");
        }
    }

    function renderFeed(provider, records) {
        const container = $("admin-" + provider + "-messages");
        if (!container) return;
        container.replaceChildren();
        if (!Array.isArray(records) || !records.length) {
            container.appendChild(block("Bu mənbədən hazırda mesaj yoxdur."));
            return;
        }
        for (const record of records.slice(0, 30)) {
            const article = document.createElement("article");
            article.className = "admin-user-line";
            article.style.cssText = "display:block;overflow-wrap:anywhere;padding:12px;";

            const heading = document.createElement("div");
            const phone = String(record.number || "Nömrə yoxdur");
            const service = String(record.service || "SMS");
            const t = String(record.time || "");
            heading.textContent = phone + " · " + service + (t ? " · " + t : "");
            heading.style.fontWeight = "650";
            article.appendChild(heading);

            article.appendChild(block(record.source || NAMES[provider]));
            const message = document.createElement("p");
            message.className = "notice-mini";
            message.style.cssText = "white-space:pre-wrap;overflow-wrap:anywhere;";
            message.textContent = String(record.message || "Mesaj mətni yoxdur");
            article.appendChild(message);

            const actions = document.createElement("div");
            actions.className = "quick-actions";
            if (record.number) {
                const copyNumber = document.createElement("button");
                copyNumber.type = "button";
                copyNumber.className = "action-small";
                copyNumber.textContent = "📋 Nömrəni kopyala";
                copyNumber.addEventListener("click", () => copyPrivate(phone));
                actions.appendChild(copyNumber);
            }
            if (record.message) {
                const copyMessage = document.createElement("button");
                copyMessage.type = "button";
                copyMessage.className = "action-small";
                copyMessage.textContent = "📋 Mesajı kopyala";
                copyMessage.addEventListener("click",
                    () => copyPrivate(String(record.message)));
                actions.appendChild(copyMessage);
            }
            article.appendChild(actions);
            container.appendChild(article);
        }
    }

    async function refreshProviderFeed(provider) {
        if (!state.isAdmin || !Object.prototype.hasOwnProperty.call(NAMES, provider)) return;
        const container = $("admin-" + provider + "-messages");
        if (!container) return;
        container.replaceChildren(block("📡 Mənbəyə qoşulur..."));
        try {
            const data = await api("/api/admin-provider-feeds?provider=" +
                encodeURIComponent(provider) + "&limit=20");
            renderFeed(provider, data.records);
            await loadAdminProviderFeeds();
        } catch (error) {
            const map = {
                provider_not_configured: "Render Environment-də bu provayderin şəxsi API məlumatları yoxdur.",
                upstream_http_error: "Provayder HTTP xətası qaytardı. Açarı və icazələri yoxlayın.",
                upstream_redirect_rejected: "Provayder gözlənilməz yönləndirmə qaytardı.",
                upstream_unreachable_or_invalid: "Provayderdən düzgün cavab alınmadı.",
                invalid_provider_response: "Provayderin cavab formatı gözləniləndən fərqlidir."
            };
            container.replaceChildren(block("⚠️ " + (map[error.code] || error.message)));
        }
    }

    async function loadAdminProviderNumbers(provider) {
        if (!state.isAdmin || !Object.prototype.hasOwnProperty.call(NAMES, provider)) return;
        const box = $("admin-" + provider + "-numbers");
        const status = $("admin-" + provider + "-stock-status");
        if (!box || !status) return;
        try {
            const data = await api("/api/admin-provider-numbers?provider=" + encodeURIComponent(provider));
            status.textContent = "📱 Nömrə ehtiyatı: " + data.count +
                " · " + (data.backup_ready ? "Şəxsi yedək hazırdır" :
                           "⚠️ Şəxsi yedək hazır deyil — idxal bağlanıb");
            box.replaceChildren();
            if (!data.count) {
                box.appendChild(block("Bu provayderdə avtomatik nömrə yaradılmır. " +
                    "İcazəli nömrələrinizi aşağıdakı sahə ilə əlavə edin."));
                return;
            }
            for (const entry of (data.numbers || [])) {
                const row = document.createElement("div");
                row.className = "admin-user-line";
                row.style.cssText = "display:flex;align-items:center;flex-wrap:wrap;gap:8px";
                row.appendChild(block(entry.number, "notice-mini"));
                const copy = document.createElement("button");
                copy.type = "button";
                copy.className = "action-small";
                copy.textContent = "📋 Kopyala";
                copy.addEventListener("click", () => copyPrivate(entry.number));
                row.appendChild(copy);
                const remove = document.createElement("button");
                remove.type = "button";
                remove.className = "action-small";
                remove.textContent = "🗑 Sil";
                remove.addEventListener("click", () => deleteAdminProviderNumber(provider, entry.number));
                row.appendChild(remove);
                box.appendChild(row);
            }
        } catch (error) {
            status.textContent = "⚠️ Nömrə siyahısı alınmadı: " + error.message;
        }
    }

    async function importAdminProviderNumbers(provider) {
        if (!state.isAdmin || !Object.prototype.hasOwnProperty.call(NAMES, provider)) return;
        const input = $("admin-" + provider + "-number-import");
        const text = (input?.value || "").trim();
        if (!text) {
            toast("Əlavə ediləcək öz nömrələrinizi daxil edin.", "error");
            return;
        }
        try {
            const result = await api("/api/admin-provider-numbers?provider=" +
                encodeURIComponent(provider), {
                method: "POST", body: {action: "import", numbers: text}
            });
            input.value = "";
            toast("✅ " + result.added + " nömrə əlavə edildi.", "success");
            await loadAdminProviderNumbers(provider);
        } catch (error) {
            const messages = {
                invalid_count: "Bir dəfəyə 1–200 nömrə əlavə edin.",
                invalid_number: "Nömrələr beynəlxalq formatda olmalıdır (məs: +994501234567).",
                invalid_import: "Mətn faylı çox böyükdür.",
                stock_limit: "Bir mənbədə maksimum 4000 nömrə saxlanıla bilər.",
                backup_not_ready: "Şəxsi yedəkləmə hazır deyil. Render-də özəl arxiv bağlantısını yoxlayın.",
                backup_failed: "Yerli yaddaşda saxlanıldı, amma yedəyə yazılmadı. Təkrar idxal etməzdən əvvəl yedəyi yoxlayın."
            };
            toast("⚠️ " + (messages[error.code] || error.message), "error");
            await loadAdminProviderNumbers(provider);
        }
    }

    async function deleteAdminProviderNumber(provider, number) {
        if (!state.isAdmin || !Object.prototype.hasOwnProperty.call(NAMES, provider)) return;
        if (!window.confirm("Bu nömrəni yalnız " + NAMES[provider] + " siyahısından silək?")) return;
        try {
            await api("/api/admin-provider-numbers?provider=" + encodeURIComponent(provider), {
                method: "POST", body: {action: "delete", number}
            });
            toast("✅ Nömrə siyahıdan silindi.", "success");
            await loadAdminProviderNumbers(provider);
        } catch (error) {
            toast("⚠️ " + error.message, "error");
        }
    }

    async function importProviderTextFile(provider, input) {
        if (!state.isAdmin || !Object.prototype.hasOwnProperty.call(NAMES, provider)) return;
        const file = input.files?.[0];
        if (!file) return;
        if (file.size > 12000) {
            toast("TXT fayl 12 KB-dan böyük ola bilməz.", "error");
        } else {
            $("admin-" + provider + "-number-import").value = await file.text();
            toast("TXT oxundu; saxlanılması üçün 'Nömrələri əlavə et' düyməsinə basın.");
        }
        input.value = "";
    }

    window.loadAdminProviderFeeds = loadAdminProviderFeeds;
    window.loadAdminProviderNumbers = loadAdminProviderNumbers;
    window.importAdminProviderNumbers = importAdminProviderNumbers;
    window.importProviderTextFile = importProviderTextFile;
    window.refreshProviderFeed = refreshProviderFeed;
})();
