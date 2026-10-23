const tg = window.Telegram.WebApp;
tg.expand();

const urlParams = new URLSearchParams(window.location.search);
let userId = urlParams.get('user_id');

if (!userId && tg.initDataUnsafe && tg.initDataUnsafe.user) {
    userId = tg.initDataUnsafe.user.id;
}

if (!userId) {
    document.getElementById('user-greeting').innerText = "İstifadəçi tapılmadı!";
} else {
    document.getElementById('user-greeting').innerText = `Xoş gəldin, ID: ${userId}`;
    loadUserData(userId);
}

async function loadUserData(id) {
    try {
        const response = await fetch(`/api/user?user_id=${id}`);
        const data = await response.json();

        const invitedCount = data.invited_count;
        const refBox = document.getElementById('ref-box');
        const contentCard = document.getElementById('content-card');
        const lockedBanner = document.getElementById('locked-banner');
        const statusText = document.getElementById('status-text');

        document.getElementById('ref-link-input').value = data.ref_link;

        if (invitedCount >= 1) {
            statusText.innerHTML = `✅ Dəvət sayı: <b>${invitedCount}/1</b>. Şərt ödəndi!`;
            refBox.style.display = 'block';
            contentCard.style.display = 'block';
            lockedBanner.style.display = 'none';
            renderMessages(data.messages);
        } else {
            statusText.innerHTML = `❌ Dəvət sayı: <b>${invitedCount}/1</b>. Paneli açmaq üçün 1 dostunu dəvət et!`;
            refBox.style.display = 'block';
            contentCard.style.display = 'none';
            lockedBanner.style.display = 'block';
        }
    } catch (err) {
        console.error("Xəta:", err);
    }
}

function renderMessages(messages) {
    const listEl = document.getElementById('messages-list');
    if (!messages || messages.length === 0) {
        listEl.innerHTML = '<p class="empty">Hələ ki mesaj yoxdur.</p>';
        return;
    }

    listEl.innerHTML = messages.map(m => `
        <div class="message-item">
            <p>📱 <b>Nömrə:</b> ${m.phone || 'Naməlum'}</p>
            <p>💬 <b>Mesaj:</b> <code>${m.sms_text}</code></p>
        </div>
    `).join('');
}

document.getElementById('copy-btn').addEventListener('click', () => {
    const input = document.getElementById('ref-link-input');
    input.select();
    navigator.clipboard.writeText(input.value);
    tg.showAlert("🔗 Dəvət linki kopyalandı!");
});
