/* Standalone site enhancements. Mini App stays fully unchanged.
   Uses the existing app.js API and navigation functions, not a second backend. */
(() => {
    if (!document.documentElement.classList.contains("site-mode")) return;

    const sections = {
        services: ["İdarəetmə paneli", "Xidmətlərdən nömrə seçin və hesabınızı idarə edin"],
        countries: ["Bütün ölkələr", "Ölkə kodlarını, range-ləri və mövcudluğu araşdırın"],
        azerbaijan: ["Azərbaycan nömrələri", "Operatorlar, icazələr və qiymətlər"],
        active: ["Aktiv nömrələr", "Nömrələriniz və geri sayım bir yerdə"],
        history: ["Tarixçə", "Hesabınıza aid OTP və fəaliyyət qeydləri"],
        "api-sales": ["API Satışı", "Balansınızla API əldə edin və əvvəlki alışlarınıza baxın"],
        leaderboard: ["OTP liderləri", "Bugünkü və bütün dövrlər üzrə sıralamalar"],
        profile: ["Profilim", "Telegram profiliniz və hesab statistikanız"],
        guide: ["İstifadə bələdçisi", "Sistem haqqında qısa və aydın məlumat"],
        admin: ["İdarəçi paneli", "Yalnız icazəli hesablar üçün sazlamalar"]
    };

    const html = document.documentElement;
    const byId = id => document.getElementById(id);
    const closeNav = () => {
        html.classList.remove("site-nav-open");
        const menu = byId("site-menu-toggle");
        if (menu) menu.setAttribute("aria-expanded", "false");
    };
    const toggleNav = () => {
        const expanded = html.classList.toggle("site-nav-open");
        const menu = byId("site-menu-toggle");
        if (menu) menu.setAttribute("aria-expanded", String(expanded));
        if (expanded) document.querySelector(".tabs .tab-btn.active")?.focus({preventScroll: true});
    };

    function setSection(name) {
        const [title, subtitle] = sections[name] || sections.services;
        if (byId("site-current-title")) byId("site-current-title").textContent = title;
        if (byId("site-current-subtitle")) byId("site-current-subtitle").textContent = subtitle;
        document.title = title + " | AZE SMS PANEL";
        document.querySelectorAll(".tabs .tab-btn").forEach(button => {
            const isCurrent = button.classList.contains("active");
            if (isCurrent) button.setAttribute("aria-current", "page");
            else button.removeAttribute("aria-current");
        });
        closeNav();
    }

    // Wrap the existing navigation without modifying Telegram's Mini App code.
    const originalSwitchTab = window.switchTab;
    if (typeof originalSwitchTab === "function") {
        window.switchTab = function (name) {
            originalSwitchTab(name);
            if (window.state?.activeTab === name || document.getElementById("tab-" + name)?.classList.contains("active")) {
                setSection(name);
            }
        };
    }

    window.websiteDesktop = {toggleNav, closeNav};

    document.addEventListener("DOMContentLoaded", () => {
        document.querySelector(".app-brand-caption")?.replaceChildren(
            document.createTextNode("Veb idarəetmə paneli")
        );
        const date = byId("site-local-date");
        if (date) {
            date.textContent = new Intl.DateTimeFormat("az-AZ", {
                timeZone: "Asia/Baku", day: "numeric", month: "long", year: "numeric"
            }).format(new Date());
        }
        byId("site-nav-backdrop")?.addEventListener("click", closeNav);
        byId("site-menu-toggle")?.addEventListener("click", toggleNav);
        document.addEventListener("keydown", event => {
            if (event.key === "Escape") closeNav();
            // Quick find: Ctrl/Command + K opens the existing service search.
            if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
                event.preventDefault();
                window.switchTab?.("services");
                byId("service-search")?.focus();
            }
        });
        setSection("services");
    });
})();
