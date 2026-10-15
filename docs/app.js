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
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    
    if (tabName === 'services') {
        document.getElementById('tab-services').classList.add('active');
        event.currentTarget.classList.add('active');
    } else if (tabName === 'active') {
        document.getElementById('tab-active').classList.add('active');
        event.currentTarget.classList.add('active');
        fetchOrders();
    } else if (tabName === 'history') {
        document.getElementById('tab-history').classList.add('active');
        event.currentTarget.classList.add('active');
        fetchIncomingSms();
    }
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

// API-dən avtomatik gələn xidmətləri (Facebook, TikTok və s.) oxumaq
async function fetchServices() {
    try {
        const res = await fetch(`${API_BASE}/api/services`, { headers: getAuthHeaders() });
        const data = await res.json();
        const container = document.getElementById('services-grid-container');
        
        if (!data.services || Object.keys(data.services).length === 0) {
            container.innerHTML = '<p class="hint">Hazırda aktiv xidmət yoxdur.</p>';
            return;
        }

        container.innerHTML = Object.keys(data.services).map(svc => `
            <div class="service-card" onclick="selectService('${svc}')">
                <span style="font-size: 18px;">📡</span>
                <div style="font-size: 13px; font-weight: 600; text-transform: uppercase; overflow: hidden; text-overflow: ellipsis;">${svc}</div>
            </div>
        `).join('');
    } catch (e) {
        document.getElementById('services-grid-container').innerHTML = '<p class="hint">Xidmətləri yükləmək olmadı.</p>';
    }
}

// Xidmət seçildikdə bota məlumat göndərmək
function selectService(serviceName) {
    tg.sendData(JSON.stringify({ action: "select_service", service: serviceName }));
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

// İşə salınma
document.addEventListener('DOMContentLoaded', () => {
    fetchDashboard();
    fetchServices();
    
    // Real-time yenilənmə üçün interval
    setInterval(() => {
        fetchDashboard();
        fetchIncomingSms();
    }, 4000);
});
<script>
// Servis seçildiğinde doğrudan Mini App üzerinden numara alır
async function selectService(serviceName) {
    tg.HapticFeedback.impactOccurred('medium');
    
    // Kullanıcıya yükleniyor bildirimi gösterelim
    const container = document.getElementById('active-orders-container');
    container.innerHTML = `<p class="hint">📡 ${serviceName.toUpperCase()} için numara aranıyor...</p>`;
    switchTab('active');

    try {
        const res = await fetch(`${API_BASE}/api/get-number`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ service: serviceName })
        });

        const data = await res.json();

        if (!res.ok || !data.success) {
            alert(data.message || "Numara alınamadı!");
            fetchOrders();
            return;
        }

        // Başarılı olursa kullanıcıya numara alındığını bildir ve aktifler sekmesini yenile
        tg.showAlert(`Numara başarıyla alındı!\n\nNumara: ${data.number}`);
        fetchOrders();
        fetchDashboard();
        
    } catch (e) {
        console.error("Numara alma xətası:", e);
        alert("Bağlantı hatası oluştu.");
        fetchOrders();
    }
}
</script>
