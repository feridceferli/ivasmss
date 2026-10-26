/* Browser sign-in: Telegram bot deep link + explicit approval + HttpOnly cookie.
   Telegram Mini Apps keep using cryptographically validated initData. */
(() => {
    const isTelegramMiniApp = Boolean(window.Telegram?.WebApp?.initData);
    const sameSite = window.location.origin === "https://ivasmss.onrender.com";
    const $ = (id) => document.getElementById(id);
    let pollTimer = null;
    let challenge = null;

    function setMessage(message, isError = false) {
        const target = $("web-login-message");
        if (!target) return;
        target.textContent = message;
        target.dataset.error = String(Boolean(isError));
    }

    function showOverlay() {
        if ($("web-login-overlay")) return;
        const wrap = document.createElement("div");
        wrap.id = "web-login-overlay";
        wrap.className = "web-login-overlay";
        wrap.setAttribute("role", "dialog");
        wrap.setAttribute("aria-modal", "true");
        wrap.setAttribute("aria-label", "Telegram ilə təhlükəsiz giriş");
        wrap.innerHTML = `
            <div class="web-login-card">
                <div class="web-login-symbol" aria-hidden="true">✦</div>
                <div class="web-login-eyebrow">AZE SMS PANEL</div>
                <h1>Telegram hesabınızla daxil olun</h1>
                <p>Saytda istifadə etmək üçün Telegram hesabınızı bot vasitəsilə bir dəfə təsdiqləyin. Profiliniz, balansınız və tarixçəniz botla eyni hesabda olacaq.</p>
                <div class="web-login-steps">
                    <span>1. Telegram-a keçin</span>
                    <span>2. Botda təsdiqləyin</span>
                    <span>3. Sayta qayıdın</span>
                </div>
                <button id="web-login-start" type="button">✈ Telegram hesabımı bağla</button>
                <a id="web-login-bot-link" target="_blank" rel="noopener noreferrer" hidden>Telegram botunu aç</a>
                <p id="web-login-message" role="status" aria-live="polite">Giriş üçün düyməyə toxunun.</p>
                <small>Şifrə və OTP kodu tələb edilmir. İcazəni yalnız botun şəxsi çatında təsdiqləyin.</small>
            </div>`;
        document.body.appendChild(wrap);
        $("web-login-start").addEventListener("click", beginLogin);
        document.body.classList.add("web-login-pending");
    }

    async function beginLogin() {
        const button = $("web-login-start");
        button.disabled = true;
        setMessage("Təhlükəsiz giriş bağlantısı hazırlanır...");
        if (pollTimer) clearTimeout(pollTimer);
        try {
            const res = await fetch("/api/web-auth/start", {
                method: "POST",
                headers: { "X-Website-Request": "1" },
                credentials: "same-origin",
                cache: "no-store"
            });
            if (!res.ok) throw new Error("Server bağlantısı açıla bilmədi.");
            challenge = await res.json();
            const link = $("web-login-bot-link");
            link.href = challenge.bot_url;
            link.hidden = false;
            button.textContent = "↗ Telegram-da təsdiqlə";
            button.disabled = false;
            button.onclick = () => window.open(challenge.bot_url, "_blank", "noopener,noreferrer");
            setMessage("Bot açıldıqdan sonra «Sayta girişi təsdiqlə» düyməsinə toxunun. Sayt burada avtomatik yenilənəcək.");
            window.open(challenge.bot_url, "_blank", "noopener,noreferrer");
            pollTimer = setTimeout(pollStatus, 1200);
        } catch (err) {
            button.disabled = false;
            setMessage(err.message || "Giriş xətası baş verdi.", true);
        }
    }

    async function pollStatus() {
        if (!challenge) return;
        try {
            const res = await fetch("/api/web-auth/status?token=" +
                encodeURIComponent(challenge.token), {
                credentials: "same-origin", cache: "no-store"
            });
            if (res.status === 410) {
                challenge = null;
                setMessage("Giriş linkinin müddəti bitib. Yenidən cəhd edin.", true);
                resetButton();
                return;
            }
            if (!res.ok) throw new Error("Giriş təsdiqlənmədi.");
            const data = await res.json();
            if (data.status === "connected") {
                setMessage("✅ Hesab bağlandı. Panel açılır...");
                window.location.reload();
                return;
            }
        } catch (_) {
            setMessage("Bağlantı yoxlanılır. Telegram-da təsdiqlədikdən sonra buraya qayıdın.");
        }
        pollTimer = setTimeout(pollStatus, 2000);
    }

    function resetButton() {
        const button = $("web-login-start");
        if (!button) return;
        button.onclick = null;
        button.disabled = false;
        button.textContent = "✈ Telegram hesabımı bağla";
        const link = $("web-login-bot-link");
        if (link) link.hidden = true;
    }

    function addLogoutButton(user) {
        const header = document.querySelector(".app-brand-tag");
        if (!header) return;
        header.replaceChildren();
        const button = document.createElement("button");
        button.className = "web-logout-button";
        button.type = "button";
        button.textContent = "Çıxış";
        button.title = "@" + (user.username || String(user.id)) + " hesabından çıxış";
        button.addEventListener("click", async () => {
            const res = await fetch("/api/web-auth/logout", {
                method: "POST", headers: { "X-Website-Request": "1" },
                credentials: "same-origin"
            });
            if (res.ok) window.location.reload();
        });
        header.appendChild(button);
    }

    window.websiteAuth = {
        async ensureAuthenticated() {
            if (isTelegramMiniApp) return true;
            if (!sameSite) {
                window.location.replace("https://ivasmss.onrender.com/");
                return false;
            }
            try {
                const res = await fetch("/api/web-auth/me", {
                    credentials: "same-origin", cache: "no-store"
                });
                if (res.ok) {
                    const data = await res.json();
                    addLogoutButton(data.user);
                    return true;
                }
            } catch (_) { /* Show retryable login interface. */ }
            showOverlay();
            return false;
        },
        requireLogin() {
            if (!isTelegramMiniApp && sameSite) showOverlay();
        }
    };
})();
