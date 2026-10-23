const tg = window.Telegram.WebApp;
tg.expand();

const urlParams = new URLSearchParams(window.location.search);
let userId = urlParams.get('user_id');

if (!userId && tg.initDataUnsafe && tg.initDataUnsafe.user) {
    userId = tg.initDataUnsafe.user.id;
}

if (!userId) {
    document.getElementById('user-greeting').innerText = "⚠️ ID müəyyən olunmadı";
} else {
    document.getElementById('user-greeting').innerText = `ID: ${userId}`;
    loadUserData(userId);
}

async function loadUserData(id) {
    try {
        const response = await fetch(`/api/user?user_id=${id}`);
        const data = await response.json();

        const invitedCount = data.invited_count || 0;
        const statusIndicator = document.getElementById('status-indicator');
        const refBox = document.getElementById('ref-box');
        const contentCard = document.getElementById('content-card');
        const lockedBanner = document.getElementById('locked-banner');

        document.getElementById('ref-link-input').value = data.ref_link || '';

        if (invitedCount >= 1) {
            statusIndicator.innerHTML = `✅ Dəvət sayı: <b>${invitedCount}/1</b> (Aktiv)`;
            statusIndicator.style.color = '#4cd964';
            refBox.style.display = 'block';
            contentCard.style.display = 'block';
            lockedBanner.style.display = 'none';
            renderMessages(data.messages);
        } else {
            statusIndicator.innerHTML = `❌ Dəvət sayı: <b>${invitedCount}/1</b> (Kilidli)`;
            statusIndicator.style.color = '#ff6b6b';
            refBox.style.display = 'block';
            contentCard.style.display = 'none';
            lockedBanner.style.display = 'block';
        }
    } catch (err) {
        console.error("Yüklənmə xətası:", err);
    }
}

function renderMessages(messages) {
    const listEl = document.getElementById('messages-list');
    if (!messages || messages.length === 0) {
        listEl.innerHTML = '<p class="empty">Hələ ki OTP / SMS mesajı daxil olmayıb.</p>';
        return;
    }

    listEl.innerHTML = messages.map(m => `
        <div class="message-item">
            <p>📱 <b>Nömrə:</b> ${m.phone || 'Nisbi'}</p>
            <p>💬 <b>Mesaj:</b> <code>${m.sms_text}</code></p>
        </div>
    `).join('');
}

document.getElementById('copy-btn').addEventListener('click', () => {
    const input = document.getElementById('ref-link-input');
    input.select();
    navigator.clipboard.writeText(input.value);
    if (tg.showAlert) {
        tg.showAlert("🔗 Dəvət linki kopyalandı!");
    } else {
        alert("🔗 Dəvət linki kopyalandı!");
    }
});

document.getElementById('refresh-btn').addEventListener('click', () => {
    if (userId) loadUserData(userId);
});
