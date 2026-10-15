// Telegram WebApp Başlatma
const tg = window.Telegram.WebApp;
tg.expand();

// Backend API URL (Kendi Render servis URL'nizi veya relative path kullanın)
const API_BASE = "https://ivasmss.onrender.com"; // Aynıdomain üzerinde çalışıyorsa boş bırakılabilir

// Telegram initData bilgisini header olarak almak için
function getAuthHeaders() {
    return {
        'X-Telegram-Init-Data': tg.initData || '',
        'Content-Type': 'application/json'
    };
}

// Kullanıcı ve Panel Verilerini Çekme (Dashboard)
async function fetchDashboardData() {
    try {
        const response = await fetch(`${ivas_sms_session}/api/dashboard`, {
            method: 'GET',
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            throw new Error('Yetkilendirme hatası veya sunucu yanıt vermedi.');
        }

        const data = await response.json();
        
        // Arayüzü Güncelle
        document.getElementById('user-name').innerText = data.user.first_name || 'Kullanıcı';
        document.getElementById('user-id').innerText = `ID: ${data.user.id}`;
        document.getElementById('user-balance').innerText = `${data.balance} AZN`;

        // Aktif Siparişleri Listele
        renderActiveOrders(data.orders || []);

    } catch (error) {
        console.error('Dashboard verisi alınamadı:', error);
    }
}

// Gelen SMS / OTP Listesini Çekme
async function fetchIncomingSms() {
    try {
        const response = await fetch(`${API_BASE}/api/incoming-sms`, {
            method: 'GET',
            headers: getAuthHeaders()
        });

        if (!response.ok) return;

        const data = await response.json();
        renderSmsList(data.sms_list || []);

    } catch (error) {
        console.error('SMS listesi alınamadı:', error);
    }
}

// Aktif Siparişleri Ekrana Basma
function renderActiveOrders(orders) {
    const container = document.getElementById('active-orders-container');
    if (!orders || orders.length === 0) {
        container.innerHTML = '<p style="color: var(--hint-color); text-align: center; margin: 10px 0;">Aktif numara bulunmuyor.</p>';
        return;
    }

    container.innerHTML = orders.map(order => `
        <div style="background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-weight: bold; font-size: 15px;">${order.number_masked}</div>
                <div style="font-size: 12px; color: var(--hint-color);">Range: ${order.range} | ${order.status}</div>
            </div>
            <div style="font-size: 13px; color: #ffeb3b;">⏳ ${Math.floor(order.remaining_seconds / 60)}d</div>
        </div>
    `).join('');
}

// Gelen SMS'leri Ekrana Basma
function renderSmsList(smsList) {
    const container = document.getElementById('sms-list-container');
    if (!smsList || smsList.length === 0) {
        container.innerHTML = '<p style="color: var(--hint-color); text-align: center; margin: 10px 0;">Henüz gelen mesaj yok...</p>';
        return;
    }

    container.innerHTML = smsList.map(sms => `
        <div class="sms-item">
            <div class="sms-header">
                <span style="font-weight: bold; color: var(--success-color);">📡 ${sms.service}</span>
                <span>🕒 ${sms.time}</span>
            </div>
            <div style="font-size: 14px; margin-bottom: 4px;">Numara: <code>${sms.number}</code></div>
            <div style="font-size: 14px; margin-bottom: 6px;">OTP Kod: <span class="otp-code">${sms.otp}</span></div>
            <div style="font-size: 12px; color: #ccc; background: rgba(0,0,0,0.3); padding: 6px; border-radius: 4px;">${sms.message}</div>
        </div>
    `).join('');
}

// Bot içerisindeki numara alma menüsüne yönlendirme
function openBotGetNumber() {
    tg.sendData(JSON.stringify({ action: "get_number" }));
}

// Sayfa yüklendiğinde verileri çek
document.addEventListener('DOMContentLoaded', () => {
    fetchDashboardData();
    fetchIncomingSms();

    // Her 4 saniyede bir otomatik yenile (Real-time güncelleme için)
    setInterval(() => {
        fetchDashboardData();
        fetchIncomingSms();
    }, 4000);
});
