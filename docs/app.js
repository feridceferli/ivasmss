(() => {
  'use strict';

  const tg = window.Telegram?.WebApp;
  const API_BASE = 'https://ivasmss.onrender.com';
  const $ = (id) => document.getElementById(id);
  const toast = $('toast');
  let toastTimer;
  let dashboard = null;
  let sandboxData = { orders: [], history: [] };

  if (tg) {
    tg.ready();
    tg.expand();
    tg.setHeaderColor?.('#0b1020');
    tg.setBackgroundColor?.('#0b1020');
  }

  function notify(text) {
    toast.textContent = text;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 2800);
    tg?.HapticFeedback?.notificationOccurred?.('success');
  }

  function node(tag, className, text) {
    const item = document.createElement(tag);
    if (className) item.className = className;
    if (text !== undefined && text !== null) item.textContent = String(text);
    return item;
  }

  function addEmpty(target, message) {
    target.replaceChildren(node('p', 'empty', message));
  }

  function sessionData() {
    return tg?.initData || '';
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set('X-Telegram-Init-Data', sessionData());
    if (options.body) headers.set('Content-Type', 'application/json');
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      cache: 'no-store',
    });
    if (!response.ok) {
      const errors = {
        401: 'Sessiya təsdiqlənmədi. Mini App-i botdan yenidən aç.',
        403: 'Bu əməliyyat üçün icazə yoxdur.',
        404: 'Məlumat tapılmadı.',
      };
      throw new Error(errors[response.status] || `Server xətası (${response.status}).`);
    }
    return response.status === 204 ? null : response.json();
  }

  function showTab(tabId) {
    const target = $(tabId);
    if (!target || target.hidden) return;
    document.querySelectorAll('.panel').forEach((panel) => panel.classList.toggle('active', panel.id === tabId));
    document.querySelectorAll('.tabs [data-tab]').forEach((button) => button.classList.toggle('active', button.dataset.tab === tabId));
    if (tabId === 'orders') loadOrders();
    if (tabId === 'history') loadOrders();
    if (tabId === 'admin') loadAdmin();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  document.querySelectorAll('[data-tab]').forEach((button) => {
    button.addEventListener('click', () => showTab(button.dataset.tab));
  });

  function setIdentity(user) {
    if (!user) return;
    const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ') || 'İstifadəçi';
    const initial = Array.from(fullName.trim())[0]?.toLocaleUpperCase('az') || 'A';
    $('hello').textContent = `Salam, ${user.first_name || 'istifadəçi'} 👋`;
    $('welcomeName').textContent = user.first_name ? `, ${user.first_name}` : '';
    $('avatar').textContent = initial;
    $('profileAvatar').textContent = initial;
    $('pName').textContent = fullName;
    $('pUser').textContent = user.username ? `@${user.username}` : 'Telegram istifadəçisi';
    $('pId').textContent = user.id || '—';
  }

  function addOrderCard(target, order, options = {}) {
    const card = node('article', 'order-card');
    const main = node('div', 'order-main');
    main.append(node('span', 'order-symbol', options.test ? '◇' : '▣'));
    const copy = node('div', 'order-copy');
    copy.append(node('b', '', order.label || 'Sifariş'));
    const details = [order.number_masked, order.range].filter(Boolean).join(' · ') || 'Əlavə məlumat yoxdur';
    copy.append(node('small', '', details));
    main.append(copy);
    const meta = node('div', 'order-meta');
    meta.append(node('span', 'status-badge', order.status || 'Aktiv'));
    if (Number.isFinite(Number(order.remaining_seconds))) {
      const minutes = Math.ceil(Math.max(0, Number(order.remaining_seconds)) / 60);
      meta.append(node('small', '', minutes > 0 ? `${minutes} dəq. qalıb` : 'Müddət bitib'));
    }
    card.append(main, meta);
    if (options.test && order.id) {
      const actions = node('div', 'order-actions');
      const sms = node('button', 'mini-button', 'Nümunəyə bax');
      sms.type = 'button';
      sms.addEventListener('click', () => loadTestSms(order.id));
      const cancel = node('button', 'mini-button danger', 'Ləğv et');
      cancel.type = 'button';
      cancel.addEventListener('click', () => cancelOrder(order.id));
      actions.append(sms, cancel);
      card.append(actions);
    }
    target.append(card);
  }

  function renderOrders() {
    const liveTarget = $('liveOrders');
    const live = dashboard?.orders || [];
    liveTarget.replaceChildren();
    if (!live.length) addEmpty(liveTarget, 'Hazırda aktiv sifariş yoxdur.');
    else live.forEach((order) => addOrderCard(liveTarget, order));
    $('activeCount').textContent = String(live.length);
    $('activeBadge').textContent = String(live.length);

    const sandboxTarget = $('sandboxOrders');
    const testOrders = sandboxData.orders || [];
    sandboxTarget.replaceChildren();
    if (!testOrders.length) addEmpty(sandboxTarget, 'Sınaq sifarişi yoxdur. “Test yarat” ilə əlavə edə bilərsən.');
    else testOrders.forEach((order) => addOrderCard(sandboxTarget, order, { test: true }));

    const historyTarget = $('historyList');
    const history = sandboxData.history || [];
    historyTarget.replaceChildren();
    if (!history.length) addEmpty(historyTarget, 'Hələ tarixçə qeydi yoxdur.');
    else history.forEach((order) => addOrderCard(historyTarget, order));
  }

  async function loadOrders() {
    try {
      sandboxData = await api('/api/orders');
      renderOrders();
    } catch (error) {
      addEmpty($('sandboxOrders'), error.message);
      addEmpty($('historyList'), error.message);
    }
  }

  async function loadDashboard(showMessage = false) {
    if (!sessionData()) {
      $('status').classList.add('offline');
      $('status').title = 'Telegram Mini App sessiyası tapılmadı';
      notify('Mini App-i Telegram botundan aç.');
      return;
    }
    $('status').classList.remove('offline');
    $('status').title = 'Bağlantı aktivdir';
    try {
      dashboard = await api('/api/dashboard');
      setIdentity(dashboard.user);
      const balance = `${dashboard.balance ?? '0'} AZN`;
      $('balance').textContent = balance;
      $('pBalance').textContent = balance;
      const stats = dashboard.stats || {};
      $('todayCount').textContent = String(stats.today_numbers ?? 0);
      $('totalCount').textContent = String(stats.total_numbers ?? 0);
      $('last24').textContent = String(stats.last24h_numbers ?? 0);
      $('last7').textContent = String(stats.last7d_numbers ?? 0);
      $('referralCount').textContent = String(dashboard.referrals?.count ?? 0);
      $('referralReward').textContent = `${dashboard.referrals?.reward ?? 0} AZN`;
      if (dashboard.support_url) {
        $('support').href = dashboard.support_url;
        $('profileSupport').href = dashboard.support_url;
      }
      $('adminTab').hidden = !dashboard.user?.is_admin;
      renderOrders();
      if (showMessage) notify('Məlumatlar yeniləndi.');
    } catch (error) {
      $('status').classList.add('offline');
      $('status').title = error.message;
      notify(error.message);
    }
  }

  async function refreshAll() {
    await Promise.all([loadDashboard(true), loadOrders()]);
  }

  async function createTestOrder() {
    try {
      await api('/api/orders', { method: 'POST', body: JSON.stringify({ action: 'create_test' }) });
      await loadOrders();
      notify('Sandbox test sifarişi yaradıldı.');
      showTab('orders');
    } catch (error) {
      notify(error.message);
    }
  }

  async function cancelOrder(id) {
    try {
      await api('/api/orders', { method: 'POST', body: JSON.stringify({ action: 'cancel', id }) });
      await loadOrders();
      notify('Test sifarişi ləğv edildi.');
    } catch (error) {
      notify(error.message);
    }
  }

  async function loadTestSms(id) {
    try {
      const result = await api(`/api/test-sms?order_id=${encodeURIComponent(id)}`);
      const target = $('smsList');
      target.replaceChildren();
      const messages = result.messages || [];
      if (!messages.length) addEmpty(target, 'Nümunə mesaj tapılmadı.');
      messages.forEach((message) => {
        const card = node('article', 'sms-message');
        card.append(node('b', '', message.sender || 'Sandbox'));
        card.append(node('p', '', message.text || message.label || 'Test məlumatı'));
        card.append(node('small', '', 'Yalnız nümunə məlumatıdır'));
        target.append(card);
      });
      showTab('sms');
    } catch (error) {
      notify(error.message);
    }
  }

  async function loadAdmin() {
    if (!dashboard?.user?.is_admin) return;
    try {
      const data = await api('/api/admin');
      $('userCount').textContent = String(data.user_count ?? 0);
      $('minWithdraw').textContent = `${data.config?.min_withdraw ?? '—'} AZN`;
      $('maxWithdraw').textContent = `${data.config?.max_withdraw ?? '—'} AZN`;
      const target = $('adminUsers');
      target.replaceChildren();
      const users = data.users || [];
      if (!users.length) return addEmpty(target, 'İstifadəçi siyahısı boşdur.');
      users.forEach((user) => {
        const row = node('article', 'admin-user');
        const info = node('div', 'admin-user-info');
        info.append(node('b', '', user.name || `İstifadəçi ${user.id}`));
        info.append(node('small', '', `ID ${user.id} · ${user.balance} AZN`));
        const actions = node('div', 'admin-actions');
        const ban = node('button', user.banned ? '' : 'ban', user.banned ? 'Banı aç' : 'Ban et');
        ban.type = 'button';
        ban.addEventListener('click', () => adminAction(user.id, user.banned ? 'unban' : 'ban'));
        const balance = node('button', '', 'Balans');
        balance.type = 'button';
        balance.addEventListener('click', () => changeBalance(user.id));
        actions.append(ban, balance);
        row.append(info, actions);
        target.append(row);
      });
    } catch (error) {
      addEmpty($('adminUsers'), error.message);
    }
  }

  async function adminAction(id, action) {
    try {
      await api('/api/admin', { method: 'POST', body: JSON.stringify({ action, user_id: id }) });
      notify('İstifadəçi məlumatı yeniləndi.');
      await loadAdmin();
    } catch (error) {
      notify(error.message);
    }
  }

  async function changeBalance(id) {
    const raw = window.prompt('Balansa əlavə və ya çıxılacaq məbləğ (məsələn: 5 və ya -5):');
    if (raw === null) return;
    const amount = Number(raw);
    if (!Number.isFinite(amount) || amount === 0) return notify('Sıfırdan fərqli düzgün məbləğ daxil et.');
    try {
      await api('/api/admin', { method: 'POST', body: JSON.stringify({ action: 'balance', user_id: id, amount }) });
      notify('Balans yeniləndi.');
      await loadAdmin();
    } catch (error) {
      notify(error.message);
    }
  }

  $('refresh').addEventListener('click', refreshAll);
  $('homeRefresh').addEventListener('click', refreshAll);
  $('ordersRefresh').addEventListener('click', () => { loadDashboard(true); loadOrders(); });
  $('historyRefresh').addEventListener('click', loadOrders);
  $('adminRefresh').addEventListener('click', loadAdmin);
  $('newTest').addEventListener('click', createTestOrder);
  $('newTestInline').addEventListener('click', createTestOrder);

  loadDashboard();
  loadOrders();
  window.setInterval(() => {
    if (document.visibilityState === 'visible') {
      loadDashboard();
      loadOrders();
    }
  }, 30000);
})();
async function fetchIncomingSms() {
    // Telegram WebApp initData-nı əldə edirik
    const initData = window.Telegram?.WebApp?.initData || '';
    
    try {
        const response = await fetch('/api/incoming-sms', {
            method: 'GET',
            headers: {
                'X-Telegram-Init-Data': initData,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Server xətası');
        }

        const data = await response.json();
        const container = document.getElementById('sms-list-container');

        if (!data.sms_list || data.sms_list.length === 0) {
            container.innerHTML = '<p style="color: #888;">Hələ ki aktiv gələn SMS yoxdur.</p>';
            return;
        }

        // SMS siyahısını HTML olaraq qururuq
        container.innerHTML = data.sms_list.map(sms => `
            <div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #4CAF50;">
                <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 5px;">
                    <span style="font-weight: bold; color: #4CAF50;">📡 ${sms.service}</span>
                    <span style="color: #aaa;">🕒 ${sms.time}</span>
                </div>
                <div style="font-size: 14px; margin-bottom: 5px;">📞 Nömrə: <code>${sms.number}</code></div>
                <div style="font-size: 15px; margin-bottom: 8px;">🔑 OTP Kod: <b style="background: #333; padding: 2px 6px; border-radius: 4px; color: #ffeb3b;">${sms.otp}</b></div>
                <div style="font-size: 12px; color: #ccc; background: rgba(0,0,0,0.2); padding: 6px; border-radius: 6px;">${sms.message}</div>
            </div>
        `).join('');

    } async (error) => {
        console.error('SMS yüklənmədi:', error);
        document.getElementById('sms-list-container').innerHTML = '<p style="color: #f44336;">SMS-ləri yükləmək mümkün olmadı.</p>';
    }
}

// Səhifə açıldıqda dərhal yüklə
fetchIncomingSms();

// Hər 4 saniyədən bir avtomatik yenilə (Real-time təcrübə üçün)
setInterval(fetchIncomingSms, 4000);
