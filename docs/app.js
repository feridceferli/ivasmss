const tg=window.Telegram?.WebApp;
const toast=document.getElementById('toast');
const API_BASE='https://ivasmss.onrender.com';
function el(id){return document.getElementById(id)}
function msg(s){toast.textContent=s;toast.classList.add('show');setTimeout(()=>toast.classList.remove('show'),2200)}
if(tg){tg.ready();tg.expand();tg.setHeaderColor?.('#070b16');tg.setBackgroundColor?.('#070b16')}
const u=tg?.initDataUnsafe?.user;
if(u){el('hello').textContent='Salam, '+(u.first_name||'istifadəçi')+' 👋';el('avatar').textContent=(u.first_name||'A')[0].toUpperCase();el('pName').textContent=[u.first_name,u.last_name].filter(Boolean).join(' ');el('pUser').textContent=u.username?'@'+u.username:'—';el('pId').textContent=u.id}
function tab(id){document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x.id===id));document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('active',x.dataset.tab===id))}
document.querySelectorAll('[data-tab]').forEach(x=>x.onclick=()=>tab(x.dataset.tab));
function orderHtml(o){const min=Math.floor((o.remaining_seconds||0)/60);return '<div class="order"><div><b>'+String(o.label||'Sifariş')+'</b><small>'+String(o.number_masked||'')+' · '+String(o.range||'—')+'</small></div><div><b>'+String(o.status||'Aktiv')+'</b><small>'+min+' dəq.</small></div></div>'}
async function load(){
 if(!tg?.initData){msg('Telegram məlumatı tapılmadı. Mini App-i botun menyusundan yenidən açın.');return}
 try{
  el('status').textContent='●';
  const r=await fetch(API_BASE+'/api/dashboard',{headers:{'X-Telegram-Init-Data':tg.initData}});
  if(!r.ok)throw new Error('HTTP '+r.status);
  const d=await r.json();
  el('balance').textContent=(d.balance??'0')+' BDT';
  const orders=d.orders||[];el('activeCount').textContent=orders.length;
  el('ordersList').innerHTML=orders.length?orders.map(orderHtml).join(''):'<p class="muted">Aktiv sifariş yoxdur.</p>';
  if(d.user){el('pName').textContent=[d.user.first_name,d.user.last_name].filter(Boolean).join(' ')||'—';el('pUser').textContent=d.user.username?'@'+d.user.username:'—';el('pId').textContent=d.user.id||'—'}
 }catch(e){el('status').textContent='○';msg('Backend bağlantısı alınmadı');}
}
el('refresh').onclick=load;load();setInterval(load,10000);