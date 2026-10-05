const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  const u = tg.initDataUnsafe?.user;
  if (u) document.getElementById("hello").textContent = `Salam, ${u.first_name || "istifadəçi"} 👋`;
  document.getElementById("tgStatus").textContent = tg.platform || "Telegram";
}
function sendAction(action) {
  if (!tg) { alert("Bu səhifəni Telegram botunun Mini App düyməsindən açın."); return; }
  tg.HapticFeedback?.impactOccurred("light");
  tg.sendData(JSON.stringify({action}));
  setTimeout(() => tg.close(), 180);
}