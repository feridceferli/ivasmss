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
function orderHtml(o){const min=Math.floor((o.remaining_seconds||0)/60);return '<div class="order"><div><b>'+String(o.label||'Sifariş')+'</b><small>'+String(o.number_masked||'')+' · '+String(o.range||'—')+'</small></div><div><b>'+String(o.status||'Aktiv')+'</b><small>'+min+' dəq.</small><button onclick="cancelOrder(\''+o.id+'\')">Ləğv et</button><button onclick="testSms(\''+o.id+'\')">Test SMS</button></div></div>'}
async function api(path,opt={}){opt.headers={...(opt.headers||{}),'X-Telegram-Init-Data':tg.initData,'Content-Type':'application/json'};const r=await fetch(API_BASE+path,opt);if(!r.ok)throw new Error('HTTP '+r.status+' '+await r.text());return r.json()}
async function loadOrders(){try{const d=await api('/api/orders');el('ordersList').innerHTML=d.orders.length?d.orders.map(orderHtml).join(''):'<p class="muted">Aktiv sifariş yoxdur.</p>';el('historyList').innerHTML=d.history.length?d.history.map(x=>'<div class="order"><div><b>'+x.label+'</b><small>'+x.number_masked+'</small></div><b>'+x.status+'</b></div>').join(''):'<p class="muted">Tarixçə boşdur.</p>'}catch(e){msg('Sifariş xətası: '+e.message)}}
async function cancelOrder(id){try{await api('/api/orders',{method:'POST',body:JSON.stringify({action:'cancel',id})});msg('Sifariş ləğv edildi');loadOrders();load()}catch(e){msg(e.message)}}
async function testSms(id){try{const d=await api('/api/test-sms?order_id='+encodeURIComponent(id));el('smsList').innerHTML=d.messages.map(x=>'<div class="order"><div><b>'+x.sender+'</b><small>'+x.text+'</small><small><b>'+x.label+'</b></small></div></div>').join('');tab('sms')}catch(e){msg(e.message)}}
async function load(){
 if(!tg?.initData){msg('Telegram məlumatı tapılmadı. Mini App-i botun menyusundan yenidən açın.');return}
 try{
  el('status').textContent='●';
  const r=await fetch(API_BASE+'/api/dashboard',{headers:{'X-Telegram-Init-Data':tg.initData}});
  if(!r.ok){let detail='';try{detail=JSON.stringify(await r.json())}catch(_){detail=await r.text()}throw new Error('HTTP '+r.status+' '+detail)}
  const d=await r.json();
  el('balance').textContent=(d.balance??'0')+' AZN';
  const orders=d.orders||[];el('activeCount').textContent=orders.length;
  el('ordersList').innerHTML=orders.length?orders.map(orderHtml).join(''):'<p class="muted">Aktiv sifariş yoxdur.</p>';
  if(d.user){el('pName').textContent=[d.user.first_name,d.user.last_name].filter(Boolean).join(' ')||'—';el('pUser').textContent=d.user.username?'@'+d.user.username:'—';el('pId').textContent=d.user.id||'—'}
 }catch(e){el('status').textContent='○';console.error('Dashboard API:',e);msg('Backend xətası: '+(e?.message||'naməlum xəta'));}
}
el('newTest').onclick=async()=>{try{await api('/api/orders',{method:'POST',body:JSON.stringify({action:'create_test'})});msg('Test sifarişi yaradıldı');await loadOrders();await load()}catch(e){msg(e.message)}};
el('refresh').onclick=()=>{load();loadOrders()};load();loadOrders();setInterval(()=>{load();loadOrders()},10000);