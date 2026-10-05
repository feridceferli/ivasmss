const tg = window.Telegram?.WebApp;
const ADMIN_IDS = [5152261397]; // UI visibility only; backend performs the real authorization.
const toast = document.getElementById('toast');
function showToast(msg){ toast.textContent=msg; toast.classList.add('show'); setTimeout(()=>toast.classList.remove('show'),1800); }

if (tg) {
  tg.ready(); tg.expand();
  tg.setHeaderColor?.('#070b16'); tg.setBackgroundColor?.('#070b16');
  const u=tg.initDataUnsafe?.user;
  if(u){
    document.getElementById('hello').textContent=`Salam, ${u.first_name || 'istifadəçi'} 👋`;
    document.getElementById('avatar').textContent=(u.first_name || 'V').slice(0,1).toUpperCase();
    if(ADMIN_IDS.includes(Number(u.id))) document.getElementById('adminSection').classList.remove('hidden');
  }
  document.getElementById('tgStatus').textContent=tg.platform || 'Telegram';
} else {
  document.getElementById('tgStatus').textContent='Browser preview';
}

function sendAction(action){
  if(!tg || !tg.initData){ showToast('Bu əməliyyat yalnız Telegram Mini App daxilində işləyir.'); return; }
  tg.HapticFeedback?.impactOccurred('light');
  try { tg.sendData(JSON.stringify({action})); setTimeout(()=>tg.close(),220); }
  catch(e){ showToast('Əməliyyat göndərilmədi.'); }
}

document.querySelectorAll('[data-action]').forEach(btn=>btn.addEventListener('click',()=>sendAction(btn.dataset.action)));
