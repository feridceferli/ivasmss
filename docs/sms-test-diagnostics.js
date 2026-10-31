/* SMS test diagnostics: consent-gated, zero actual SMS or OTP API requests. */
(function () {
    "use strict";

    const $ = id => document.getElementById(id);
    let lastPublicEnabled = false;

    function errorText(error) {
        const messages = {
            consent_required: "Yalnız sizə məxsus və ya icazəli test nömrəsindən istifadə edin.",
            invalid_phone: "Nömrəni +994501234567 kimi beynəlxalq formatda daxil edin.",
            feature_disabled: "Bu simulyasiya bölməsi yalnız admin üçün aktivdir.",
            rate_limited: "Bir dəqiqədə maksimum 5 simulyasiya mümkündür.",
            daily_limit: "Günlük 50 simulyasiya limitinə çatdınız.",
            storage_not_ready: "Şəxsi yedək hələ hazır deyil. Heç nə yazılmadı.",
            storage_unavailable: "Diaqnostika arxivini oxumaq olmur.",
            backup_failed: "Lokal tarixçə saxlandı, lakin şəxsi yedəyə sinxronizasiya olmadı.",
            provider_not_configured: "Twilio aktiv deyil. Render-də hesab məlumatları, göndərən nömrəsi, icazəli nömrələr və SMS_LIVE_ENABLED=true təyin edin.",
            destination_not_allowlisted: "Bu nömrə Render-in SMS_LIVE_ALLOWED_NUMBERS siyahısında yoxdur.",
            live_daily_limit: "Canlı SMS üçün gündəlik 10 cəhd limiti tamamlanıb.",
            live_phone_cooldown: "Bu nömrəyə son 1 saatda artıq SMS cəhdi olub.",
            provider_auth_failed: "Twilio hesab məlumatları və ya göndəriş icazəsi rədd edildi.",
            provider_rate_limited: "Twilio hazırda sorğunu məhdudlaşdırır.",
            provider_rejected: "Twilio SMS sorğusunu qəbul etmədi. Hesab, göndərici və ölkə icazələrini yoxlayın.",
            provider_result_unknown: "Göndəriş nəticəsi qeyri-müəyyəndir; təkrar göndərməyin, Twilio jurnalını yoxlayın."
        };
        return messages[error.code] || error.message || "Naməlum xəta";
    }

    function renderHistory(data) {
        const target = $("sms-lab-history");
        if (!target) return;
        target.replaceChildren();
        const records = Array.isArray(data.history) ? data.history : [];
        if (!records.length) {
            const p = document.createElement("p");
            p.className = "notice-mini";
            p.textContent = "Hələ test qeydi yoxdur.";
            target.appendChild(p);
            return;
        }
        for (const item of records) {
            const row = document.createElement("div");
            row.className = "admin-user-line";
            const date = String(item.date || "").replace("T", " ").slice(0, 19);
            const owner = state.isAdmin ? " · UID " + String(item.user_id || "—") : "";
            row.textContent = "🧪 " + String(item.phone || "—") + owner + " · " +
                date + " · Simulyasiya (0 SMS göndərildi)";
            target.appendChild(row);
        }
    }

    function renderLiveHistory(data) {
        const target = $("admin-live-sms-history");
        if (!target || !state.isAdmin) return;
        target.replaceChildren();
        const records = Array.isArray(data.live_history) ? data.live_history : [];
        if (!records.length) {
            const item = document.createElement("p");
            item.className = "notice-mini";
            item.textContent = "Hələ canlı SMS sorğusu yoxdur.";
            target.appendChild(item);
            return;
        }
        for (const entry of records) {
            const div = document.createElement("div");
            div.className = "admin-user-line";
            const statuses = {
                accepted_by_provider: "✅ Provayder qəbul etdi (çatdırılma təsdiqi deyil)",
                provider_rejected: "❌ Provayder rədd etdi",
                delivery_unknown: "⚠️ Nəticə naməlum",
                sending_pending: "⏳ Cavab gözlənilir"
            };
            const date = String(entry.date || "").replace("T", " ").slice(0, 19);
            div.textContent = "📨 " + String(entry.phone || "—") + " · " + date +
                " · " + (statuses[entry.status] || String(entry.status)) +
                (entry.error_code ? " · " + entry.error_code : "");
            target.appendChild(div);
        }
    }

    async function refreshSmsDiagnostics() {
        if (!state.isAdmin && !state.smsDiagnosticsAvailable) return;
        try {
            const data = await api("/api/sms-diagnostics");
            if (state.isAdmin) {
                lastPublicEnabled = !!data.enabled_for_all;
                const status = $("admin-sms-lab-status");
                if (status) {
                    status.textContent = "Görünmə: " +
                        (lastPublicEnabled ? "✅ Bütün istifadəçilər" : "🔒 Yalnız admin") +
                        (data.backup_ready ? " · Şəxsi yedək hazırdır" : " · ⚠️ Şəxsi yedək hazır deyil");
                }
                const metrics = $("admin-sms-lab-metrics");
                if (metrics) metrics.textContent = "Simulyasiya qeydləri: " +
                    data.total_simulated_checks + " · Bloklanmış xarici OTP endpointləri: " +
                    data.third_party_endpoints_disabled + " · Provayderə qəbul edilən real SMS: " +
                    data.live_submitted_count + " (çatdırılma ayrıca təsdiqlənməlidir)";
                const live = data.live_sms || {};
                const liveStatus = $("admin-live-sms-status");
                if (liveStatus) liveStatus.textContent = live.configured ?
                    "✅ Twilio hazırdır · İcazəli nömrələr: " + live.allowlisted_number_count +
                    " · Real SMS yalnız admin üçün aktivdir." :
                    "⚠️ Real SMS hazır deyil. Render-də TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, SMS_LIVE_ALLOWED_NUMBERS və SMS_LIVE_ENABLED=true lazımdır.";
                const liveButton = $("admin-live-sms-send");
                if (liveButton) liveButton.disabled = !live.configured || !data.backup_ready;
                renderLiveHistory(data);
                const button = $("admin-sms-lab-toggle");
                if (button) {
                    button.disabled = !data.backup_ready;
                    button.textContent = lastPublicEnabled ?
                        "🔒 Hamıya bağla — yalnız admin" : "🌍 Hamı üçün aç (yalnız simulyasiya)";
                }
            }
            const availability = $("sms-lab-availability");
            if (availability) availability.textContent = data.available ?
                "✅ Təhlükəsiz simulyasiya aktivdir. Heç bir real SMS göndərilmir." :
                "🔒 Bu test bölməsi hazırda admin üçün ayrılıb.";
            renderHistory(data);
        } catch (err) {
            const target = $("sms-lab-results") || $("admin-sms-lab-status");
            if (target) target.textContent = "⚠️ " + errorText(err);
        }
    }

    async function loadSmsDiagnosticsAvailability() {
        try {
            const data = await api("/api/sms-diagnostics");
            state.smsDiagnosticsAvailable = !!data.available;
            const tab = $("sms-diagnostics-tab-button");
            if (tab) tab.hidden = !data.available;
            if (!data.available && state.activeTab === "sms-lab") {
                switchTab("services");
            }
            if (state.activeTab === "sms-lab" || state.activeTab === "admin") {
                await refreshSmsDiagnostics();
            }
        } catch (_) {
            if (!state.isAdmin) {
                state.smsDiagnosticsAvailable = false;
                const tab = $("sms-diagnostics-tab-button");
                if (tab) tab.hidden = true;
            }
        }
    }

    async function runSmsDiagnosticSimulation() {
        if (!state.smsDiagnosticsAvailable && !state.isAdmin) return;
        const number = $("sms-lab-phone")?.value.trim() || "";
        const consent = !!$("sms-lab-consent")?.checked;
        if (!consent) {
            toast("⚠️ Nömrə üzərində test icazənizi təsdiqləyin.", "error");
            return;
        }
        const resultNode = $("sms-lab-results");
        try {
            const result = await api("/api/sms-diagnostics", {
                method: "POST", body: {action: "simulate", number, consent: true}
            });
            if (resultNode) resultNode.textContent =
                "✅ Simulyasiya tamamlandı: " + result.result.phone +
                " · 0 real SMS göndərildi. Test tarixçəyə yazıldı.";
            if ($("sms-lab-phone")) $("sms-lab-phone").value = "";
            if ($("sms-lab-consent")) $("sms-lab-consent").checked = false;
            await refreshSmsDiagnostics();
        } catch (error) {
            if (resultNode) resultNode.textContent = "⚠️ " + errorText(error);
        }
    }

    async function sendAdminLiveTestSms() {
        if (!state.isAdmin) return;
        const number = $("admin-live-sms-phone")?.value.trim() || "";
        const consent = !!$("admin-live-sms-consent")?.checked;
        if (!consent) {
            toast("⚠️ Nömrə sahibinin test mesajına razılığını təsdiqləyin.", "error");
            return;
        }
        const button = $("admin-live-sms-send");
        const result = $("admin-live-sms-result");
        if (button) button.disabled = true;
        try {
            const response = await api("/api/sms-diagnostics", {
                method: "POST", body: {action: "send_live", number, consent: true}
            });
            const accepted = response.result?.entry;
            if (result) result.textContent = "✅ SMS sorğusu Twilio tərəfindən qəbul edildi: " +
                String(accepted?.phone || number) + " · Provayder statusu: " +
                String(accepted?.provider_status || "accepted") +
                ". Telefona çatdırılma hələ təsdiqlənməyib.";
            if ($("admin-live-sms-phone")) $("admin-live-sms-phone").value = "";
            if ($("admin-live-sms-consent")) $("admin-live-sms-consent").checked = false;
        } catch (error) {
            if (result) result.textContent = "⚠️ " + errorText(error);
        } finally {
            await refreshSmsDiagnostics();
        }
    }

    async function toggleSmsDiagnosticsPublic() {
        if (!state.isAdmin) return;
        const enabled = !lastPublicEnabled;
        try {
            await api("/api/sms-diagnostics", {
                method: "POST", body: {action: "visibility", enabled}
            });
            toast(enabled ? "✅ Simulyasiya bütün istifadəçilərə açıldı." :
                "🔒 Simulyasiya yalnız admin üçün aktivdir.", "success");
            await loadSmsDiagnosticsAvailability();
            await refreshSmsDiagnostics();
        } catch (error) {
            toast("⚠️ " + errorText(error), "error");
        }
    }

    window.loadSmsDiagnosticsAvailability = loadSmsDiagnosticsAvailability;
    window.refreshSmsDiagnostics = refreshSmsDiagnostics;
    window.runSmsDiagnosticSimulation = runSmsDiagnosticSimulation;
    window.toggleSmsDiagnosticsPublic = toggleSmsDiagnosticsPublic;
    window.sendAdminLiveTestSms = sendAdminLiveTestSms;
})();
