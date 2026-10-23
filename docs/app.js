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
    const tabs = ['services', 'active', 'history', 'referrals'];
    const index = tabs.indexOf(tabName);
    if (index < 0) return;
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + tabName).classList.add('active');
    const tabButton = document.querySelectorAll('.tab-btn')[index];
    if (tabButton) tabButton.classList.add('active');

    if (tabName === 'active') fetchOrders();
    if (tabName === 'history') fetchIncomingSms();
    if (tabName === 'referrals') fetchReferrals();
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


function setReferralGate(unlocked) {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach((button, index) => {
        if (index < 3) {
            button.disabled = !unlocked;
            button.setAttribute('aria-disabled', String(!unlocked));
            button.style.opacity = unlocked ? '' : '0.45';
            button.title = unlocked ? '' : 'Əvvəlcə 1 dostunuzu dəvət edin';
        }
    });
    if (!unlocked && !document.getElementById('tab-referrals').classList.contains('active')) {
        switchTab('referrals');
    }
}

function referralStatusMessage(message, ready = null) {
    const node = document.getElementById('referral-status');
    node.textContent = message;
    node.classList.toggle('is-ready', ready === true);
    node.classList.toggle('is-locked', ready === false);
}

async function fetchReferrals() {
    const box = document.getElementById('referral-link-box');
    const locked = document.getElementById('referral-locked');
    if (!tg.initData) {
        box.hidden = true;
        locked.hidden = true;
        referralStatusMessage('⚠️ Bu bölməni Telegram botunun içindən açın.');
        setReferralGate(false);
        return;
    }
    referralStatusMessage('Dəvət statusu yenilənir...');
    try {
        const response = await fetch(`${API_BASE}/api/referrals`, { headers: getAuthHeaders() });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const data = await response.json();
        if (typeof data.ref_link !== 'string' || !data.ref_link.startsWith('https://t.me/')) {
            throw new Error('Invalid referral link');
        }
        const invited = Math.max(0, Number(data.invited_count) || 0);
        const needed = Math.max(1, Number(data.required) || 1);
        const unlocked = Boolean(data.unlocked);
        referralStatusMessage(
            unlocked
                ? `✅ Dəvət sayı: ${invited}/${needed} — Şərt ödənildi!`
                : `🔒 Dəvət sayı: ${invited}/${needed} — Hələ dost dəvəti gözlənilir.`,
            unlocked
        );
        document.getElementById('referral-link-input').value = data.ref_link;
        box.hidden = false;
        locked.hidden = unlocked;
        setReferralGate(unlocked);
        if (unlocked) { fetchDashboard(); fetchServices(); }
    } catch (err) {
        box.hidden = true;
        locked.hidden = true;
        referralStatusMessage('❌ Dəvət statusunu yükləmək olmadı. Yenidən cəhd edin.');
        setReferralGate(false);
    }
}

async function copyReferralLink() {
    const value = document.getElementById('referral-link-input').value;
    if (!value) return;
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(value);
        } else {
            const field = document.getElementById('referral-link-input');
            field.focus();
            field.select();
            if (!document.execCommand('copy')) throw new Error('Copy failed');
        }
        if (tg.showAlert) tg.showAlert('🔗 Dəvət linki kopyalandı!');
    } catch (err) {
        if (tg.showAlert) tg.showAlert('Linki seçib əl ilə kopyalayın.');
    }
}

function shareReferralLink() {
    const invite = document.getElementById('referral-link-input').value;
    if (!invite) return;
    const url = 'https://t.me/share/url?url=' + encodeURIComponent(invite)
        + '&text=' + encodeURIComponent('Bu Telegram botuna qoşul!');
    if (typeof tg.openTelegramLink === 'function') tg.openTelegramLink(url);
    else window.open(url, '_blank', 'noopener,noreferrer');
}

// İşə salınma
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('referral-copy-btn').addEventListener('click', copyReferralLink);
    document.getElementById('referral-share-btn').addEventListener('click', shareReferralLink);
    document.getElementById('referral-refresh-btn').addEventListener('click', fetchReferrals);

    fetchReferrals();
    
    // Real-time yenilənmə üçün interval
    setInterval(() => {
        if (!document.hidden) {
            fetchReferrals();
            if (!document.querySelector('.tab-btn:disabled')) {
                fetchDashboard();
                fetchIncomingSms();
            }
        }
    }, 30000);
});

