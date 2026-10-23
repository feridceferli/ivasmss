const tg = window.Telegram.WebApp;
tg.expand();

// Render backend ünvanınızı bura yazın (məsələn: https://ivasmss.onrender.com)
const API_BASE = "https://ivasmss.onrender.com";

function getAuthHeaders() {
    return {
        'X-Telegram-Init-Data': tg.initData || '',
        'Content-Type': 'application/json'
    };
}

// Tab dəyişdirmə məntiqi
function switchTab(tabName) {
    const tabs = ['services', 'active', 'history'];
    const index = tabs.indexOf(tabName);
    if (index < 0) return;
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + tabName).classList.add('active');
    const tabButton = document.querySelectorAll('.tab-btn')[index];
    if (tabButton) tabButton.classList.add('active');

    if (tabName === 'active') fetchOrders();
    if (tabName === 'history') fetchIncomingSms();
}

// Dashboard və Profil Məlumatları
async function fetchDashboard() {
    try {
        const res = await fetch(`${API_BASE}/api/dashboard`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error();
        const data = await res.json();
        
        document.getElementById('user-name').innerText = data.user.first_name || 'İstifadəçi';
        document.getElementById('user-id').innerText = `ID: ${data.user.id}`;
        document.getElementById('user-balance').innerText = `${data.balance} AZN`;

        // Logo / Avatar yaratma
        const avatarEl = document.getElementById('user-avatar');
        if (data.user.photo_url) {
            avatarEl.innerHTML = `<img src="${data.user.photo_url}" alt="Avatar">`;
        } else {
            avatarEl.innerText = (data.user.first_name || 'İ').charAt(0).toUpperCase();
        }
    } catch (e) {
        console.error("Dashboard xətası:", e);
    }
}

// Show actual provider ranges by service. +994 is visible, but requires approval.
async function fetchServices() {
    const container = document.getElementById('services-grid-container');
    try {
        const response = await fetch(`${API_BASE}/api/services`, { headers: getAuthHeaders() });
        if (!response.ok) throw new Error("services_unavailable");
        const data = await response.json();
        container.replaceChildren();
        const services = Object.entries(data.services || {});
        if (!services.length && !(data.az_catalog || []).length) {
            container.textContent = 'Hazırda aktiv xidmət yoxdur.';
            return;
        }
        const addService = (service, country, locked) => {
            const tile = document.createElement('div');
            tile.className = 'service-card';
            tile.style.cursor = 'pointer';
            tile.textContent = country === '994'
                ? `🇦🇿 ${service.toUpperCase()} — Azərbaycan ${locked ? '🔒' : '✅'}`
                : `📡 ${service.toUpperCase()}`;
            tile.addEventListener('click', () => {
                if (locked) {
                    tg.showAlert?.('🔒 +994 nömrələrindən istifadə üçün admin icazəsi lazımdır. Bota /az_request yazın.');
                    return;
                }
                selectService(service, country);
            });
            container.appendChild(tile);
        };
        for (const [service, ranges] of services) {
            const prefixes = Array.isArray(ranges)
                ? ranges.map(rid => String(rid).replace(/\D/g, ''))
                : [];
            if (prefixes.some(rid => rid && !rid.startsWith('994'))) {
                addService(service, null, false);
            }
        }

        // Configured 210/211 plus all extra range metadata announced by the API.
        for (const operator of (data.az_catalog || [])) {
            const heading = document.createElement('div');
            heading.style.gridColumn = '1 / -1';
            heading.style.marginTop = '12px';
            heading.style.fontWeight = '700';
            heading.textContent = '🇦🇿 ' + operator.name;
            container.appendChild(heading);

            for (const prefix of (operator.prefixes || [])) {
                const tile = document.createElement('div');
                tile.className = 'service-card';
                tile.style.display = 'block';
                tile.style.cursor = 'default';
                const label = document.createElement('div');
                label.style.fontWeight = '700';
                label.style.marginBottom = '8px';
                label.textContent = '+' + prefix.prefix;
                tile.appendChild(label);

                for (const item of (prefix.ranges || [])) {
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.style.display = 'block';
                    button.style.width = '100%';
                    button.style.marginTop = '6px';
                    button.style.padding = '8px';
                    button.style.borderRadius = '8px';
                    button.style.border = '1px solid #ffffff33';
                    button.style.color = 'var(--text-color)';
                    button.style.background = 'var(--card-bg)';
                    const status = item.listed_in_api ? ' · 📡 API' : ' · ❔';
                    button.textContent = item.rid + status + (data.az_approved ? '' : ' 🔒');
                    button.title = item.listed_in_api
                        ? 'API siyahısında qeyd olunub; nömrə mövcudluğu zəmanətli deyil'
                        : 'API siyahısında təsdiqlənməyib';
                    button.addEventListener('click', () => {
                        if (!data.az_approved) {
                            tg.showAlert?.('🔒 +994 üçün admin təsdiqi lazımdır: /az_request');
                            return;
                        }
                        selectService('az', '994', item.rid);
                    });
                    tile.appendChild(button);
                }
                container.appendChild(tile);
            }
        }
    } catch (error) {
        container.textContent = 'Xidmətləri yükləmək olmadı.';
    }
}

// Server allocates only ranges declared by the API and checks +994 permissions.
async function selectService(serviceName, country = null, range = null) {
    const container = document.getElementById('active-orders-container');
    switchTab('active');
    container.textContent = '📡 Nömrə axtarılır...';
    try {
        const response = await fetch(`${API_BASE}/api/get-number`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ service: serviceName, country, range })
        });
        const data = await response.json();
        if (!response.ok || !data.success) {
            tg.showAlert?.(data.message || 'Bu xidmət üçün hazırda uyğun nömrə yoxdur.');
        } else {
            tg.showAlert?.('✅ Nömrə ayrıldı: ' + data.number);
        }
    } catch (error) {
        tg.showAlert?.('Bağlantı xətası. Yenidən yoxlayın.');
    }
    await fetchOrders();
    await fetchDashboard();
}

// Aktiv sifarişlər
async function fetchOrders() {
    try {
        const res = await fetch(`${API_BASE}/api/orders`, { headers: getAuthHeaders() });
        const data = await res.json();
        const container = document.getElementById('active-orders-container');
        
        if (!data.orders || data.orders.length === 0) {
            container.innerHTML = '<p class="hint">Aktiv nömrə tapılmadı.</p>';
            return;
        }

        container.innerHTML = data.orders.map(o => `
            <div style="background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px; margin-bottom: 6px;">
                <div style="font-weight: bold;">${o.number_masked}</div>
                <div style="font-size: 12px; color: var(--hint-color);">Range: ${o.range} | ${o.status}</div>
            </div>
        `).join('');
    } catch (e) {}
}

// Gələn SMS / OTP Siyahısı (Tarixçə)
async function fetchIncomingSms() {
    try {
        const res = await fetch(`${API_BASE}/api/incoming-sms`, { headers: getAuthHeaders() });
        const data = await res.json();
        const container = document.getElementById('sms-list-container');
        
        if (!data.sms_list || data.sms_list.length === 0) {
            container.innerHTML = '<p class="hint">Hələ ki gələn mesaj yoxdur.</p>';
            return;
        }

        container.innerHTML = data.sms_list.map(sms => `
            <div class="sms-item">
                <div style="display: flex; justify-content: space-between; font-size: 12px; color: var(--hint-color); margin-bottom: 4px;">
                    <span style="color: var(--success); font-weight: bold;">📡 ${sms.service}</span>
                    <span>🕒 ${sms.time}</span>
                </div>
                <div style="font-size: 13px; margin-bottom: 4px;">Nömrə: <code>${sms.number}</code></div>
                <div style="font-size: 13px; margin-bottom: 6px;">OTP Kod: <span class="otp-code">${sms.otp}</span></div>
                <div style="font-size: 11px; color: #cbd5e1; background: rgba(0,0,0,0.3); padding: 6px; border-radius: 4px;">${sms.message}</div>
            </div>
        `).join('');
    } catch (e) {}
}


// Initial load and periodic refresh. Referral-based access checks have been removed.
document.addEventListener('DOMContentLoaded', () => {
    fetchDashboard();
    fetchServices();
    fetchOrders();
    fetchIncomingSms();

    setInterval(() => {
        if (!document.hidden) {
            fetchDashboard();
            fetchServices();
            fetchOrders();
            fetchIncomingSms();
        }
    }, 30000);
});
