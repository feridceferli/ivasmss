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

    window.loadAdminProviderFeeds = loadAdminProviderFeeds;
    window.refreshProviderFeed = refreshProviderFeed;
})();
