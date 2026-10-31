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
            backup_failed: "Lokal tarixçə saxlandı, lakin şəxsi yedəyə sinxronizasiya olmadı."
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
                    data.total_simulated_checks + " · Bloklanmış xarici SMS endpointləri: " +
                    data.third_party_endpoints_disabled + " · Real göndərilən SMS: 0";
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
})();
