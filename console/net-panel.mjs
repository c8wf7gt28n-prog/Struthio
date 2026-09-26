const KEY_STORE='struthio.network.key';
const CSS=`
#net-panel{position:fixed;z-index:70;left:0;right:0;top:0;bottom:calc(var(--deck-h) + var(--safe-bottom));display:flex;justify-content:center;align-items:flex-start;padding:max(10px,env(safe-area-inset-top)) 10px 8px;box-sizing:border-box;background:rgba(5,5,5,.94);overflow:auto}
#net-panel[hidden]{display:none!important}
#net-panel .net-card{width:min(100%,380px);box-sizing:border-box;display:flex;flex-direction:column;gap:9px;background:#0b0908;border:2px solid var(--machine-yellow,#faca3a);border-radius:12px;padding:12px;color:var(--machine-paper,#f2e8d2);font:700 13px Arial,Helvetica,sans-serif}
#net-panel h2{margin:0;color:var(--machine-yellow,#faca3a);font:900 20px/1.1 "Arial Narrow",Arial,sans-serif;letter-spacing:.06em}
#net-panel .net-kicker{margin:0;color:var(--machine-cyan,#1cb2e0);font-size:11px;letter-spacing:.16em}
#net-panel .net-addr{margin:0;color:#b8ab90;font:700 11px/1.3 "Courier New",monospace;word-break:break-all}
#net-panel .net-state{display:flex;align-items:center;gap:8px;margin:0;font:900 15px Arial,sans-serif;letter-spacing:.05em}
#net-panel .net-state i{width:10px;height:10px;border-radius:50%;background:#6d6553;flex:none}
#net-panel .net-state[data-tone=good] i{background:#5fe07a;box-shadow:0 0 10px #5fe07a}
#net-panel .net-state[data-tone=warn] i{background:#ffb938;box-shadow:0 0 10px #ffb938}
#net-panel .net-state[data-tone=bad] i{background:#ff5a3c;box-shadow:0 0 10px #ff5a3c}
#net-panel .net-note{margin:0;color:#b8ab90;font-size:12px;line-height:1.35}
#net-panel .net-counts{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:0}
#net-panel .net-counts div{background:#000;border:1px solid #3a3226;border-radius:8px;padding:6px 4px;text-align:center}
#net-panel .net-counts b{display:block;color:var(--machine-yellow,#faca3a);font:900 20px/1 Arial,sans-serif}
#net-panel .net-counts small{color:#8f846d;font-size:10px;letter-spacing:.1em}
#net-panel label{display:flex;flex-direction:column;gap:4px;font-size:11px;letter-spacing:.1em;color:#b8ab90}
#net-panel input{font:700 15px Arial,sans-serif;background:#000;color:#f2e8d2;border:2px solid #3a3226;border-radius:8px;padding:8px;min-width:0}
#net-panel .net-row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
#net-panel button,#net-panel a.net-link{min-height:46px;border-radius:8px;border:2px solid var(--machine-yellow,#faca3a);background:#140f06;color:#f2e8d2;font:900 14px Arial,sans-serif;letter-spacing:.06em;display:flex;align-items:center;justify-content:center;text-decoration:none;box-sizing:border-box}
#net-panel button.is-primary{background:var(--machine-yellow,#faca3a);color:#140f05}
#net-panel button[aria-pressed=true]{background:var(--machine-cyan,#1cb2e0);border-color:var(--machine-cyan,#1cb2e0);color:#031014}
#net-panel button.is-danger{border-color:#ff5a3c;color:#ffb3a3}
#net-panel ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px}
#net-panel li{display:flex;align-items:center;gap:8px;background:#000;border:1px solid #3a3226;border-radius:8px;padding:4px 4px 4px 10px;font:700 12px Arial,sans-serif}
#net-panel li b{font:900 15px "Courier New",monospace;color:var(--machine-yellow,#faca3a);letter-spacing:.1em}
#net-panel li span{flex:1;color:#b8ab90}
#net-panel li button{min-height:38px;padding:0 12px;font-size:12px}
#net-panel .net-status{margin:0;min-height:1em;color:var(--machine-cyan,#1cb2e0);font-size:12px}
#net-panel .net-keybox,#net-panel .net-ctl{display:flex;flex-direction:column;gap:9px}
#net-panel [hidden]{display:none!important}
`;
export function networkOf(relayUrl){
const u=new URL(relayUrl,location.href);
const http=new URL(u.href);http.protocol=u.protocol==='wss:'?'https:':u.protocol==='ws:'?'http:':u.protocol;
const base=http.href.replace(/\/vs\/ws.*$/,'');
const m=/^struthio-network\.([a-z0-9-]+)\.workers\.dev$/.exec(http.hostname);
return{endpoint:u.href,host:http.host,base,health:base+'/vs/health',admin:base+'/vs/admin',adminApp:m?`https://struthio-admin.${m[1]}.workers.dev/`:null};
}
const ago=(ms)=>{const s=Math.max(0,Math.round(ms/1000));return s<60?`${s}s`:s<3600?`${Math.round(s/60)}m`:`${Math.round(s/3600)}h`;};
export function setupNetworkPanel({relayUrl,build,openModal=null,fetchImpl=(...a)=>fetch(...a),store=null}){
const net=networkOf(relayUrl);
const kv=store||{get:(k)=>{try{return localStorage.getItem(k);}catch{return null;}},set:(k,v)=>{try{v===null?localStorage.removeItem(k):localStorage.setItem(k,v);}catch{}}};
let memKey=kv.get(KEY_STORE)||'';
const el=(tag,attrs={},text='')=>{const n=document.createElement(tag);for (const[k,v] of Object.entries(attrs)) n.setAttribute(k,v);if (text) n.textContent=text;return n;};
const style=el('style');style.textContent=CSS;document.head.append(style);
const root=el('section',{id:'net-panel',role:'dialog','aria-modal':'true','aria-labelledby':'net-title',hidden:''});
const card=el('div',{class:'net-card'});
const kicker=el('p',{class:'net-kicker'},'DEVELOPMENT · STRUTHIO NETWORK');
const title=el('h2',{id:'net-title'},'NETWORK');
const addr=el('p',{class:'net-addr'},net.endpoint);
const state=el('p',{class:'net-state',role:'status','aria-live':'polite'});const dot=el('i');const stateText=el('span',{},'CHECKING…');state.append(dot,stateText);
const note=el('p',{class:'net-note'});
const keyBox=el('div',{class:'net-keybox'});
const keyLabel=el('label',{},'NETWORK KEY');
const keyInput=el('input',{type:'password',autocomplete:'off',autocapitalize:'off',spellcheck:'false',placeholder:'Paste from STRUTHIO ADMIN','aria-label':'Network key'});
keyLabel.append(keyInput);
const keyRow=el('div',{class:'net-row'});
const pasteBtn=el('button',{type:'button','data-net':'paste'},'PASTE KEY');
const saveKeyBtn=el('button',{type:'button',class:'is-primary','data-net':'save-key'},'USE KEY');
keyRow.append(pasteBtn,saveKeyBtn);
keyBox.append(el('p',{class:'net-note'},'To control the network from here: in STRUTHIO ADMIN tap COPY CONSOLE KEY, then paste it below. It stays on this phone only.'),keyLabel,keyRow);
const ctl=el('div',{class:'net-ctl',hidden:''});
const counts=el('div',{class:'net-counts'});
const seg=el('div',{class:'net-row',role:'group','aria-label':'VS open or closed'});
const openBtn=el('button',{type:'button','aria-pressed':'true','data-net':'open'},'VS OPEN');
const closeBtn=el('button',{type:'button','aria-pressed':'false','data-net':'closed'},'VS CLOSED');
seg.append(openBtn,closeBtn);
const msgLabel=el('label',{},'MESSAGE WHILE CLOSED');
const msgInput=el('input',{type:'text',maxlength:'100',placeholder:'e.g. BACK AT 9PM','aria-label':'Message while closed'});
msgLabel.append(msgInput);
const saveBtn=el('button',{type:'button',class:'is-primary','data-net':'save'},'SAVE');
const roomsHead=el('p',{class:'net-kicker'},'ROOMS');
const rooms=el('ul');
const forgetBtn=el('button',{type:'button',class:'is-danger','data-net':'forget'},'FORGET KEY ON THIS PHONE');
ctl.append(counts,seg,msgLabel,saveBtn,roomsHead,rooms,forgetBtn);
const status=el('p',{class:'net-status',role:'status','aria-live':'polite'});
const foot=el('div',{class:'net-row'});
const refreshBtn=el('button',{type:'button','data-net':'refresh'},'REFRESH');
const doneBtn=el('button',{type:'button','data-net':'close'},'CLOSE');
foot.append(refreshBtn,doneBtn);
const adminLink=net.adminApp?el('a',{class:'net-link',href:net.adminApp,target:'_blank',rel:'noopener','data-net':'admin'},'OPEN STRUTHIO ADMIN (DEPLOY)'):null;
card.append(kicker,title,addr,state,note,keyBox,ctl,status,...(adminLink?[adminLink]:[]),foot);
root.append(card);
document.body.append(root);
let release=null,openChoice=true,last=null,busy=false;
const tone=(t,text)=>{state.dataset.tone=t;stateText.textContent=text;};
const count=(n,label)=>{const d=el('div');d.append(el('b',{},String(n)),el('small',{},label));return d;};
const setSeg=()=>{openBtn.setAttribute('aria-pressed',String(openChoice));closeBtn.setAttribute('aria-pressed',String(!openChoice));};
async function call(path,body=null){
const r=await fetchImpl(net.admin+path,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+memKey,...(body?{'content-type':'application/json'}:{})},body:body?JSON.stringify(body):undefined,cache:'no-store'});
if (r.status===401){const e=new Error('KEY');e.key=true;throw e;}
const j=await r.json().catch(()=>null);
if (!r.ok||!j||!j.ok) throw new Error(`HTTP ${r.status}`);
return j;
}
async function refresh(say=''){
if (busy) return;busy=true;status.textContent=say;
let h=null;
try{const r=await fetchImpl(net.health,{cache:'no-store'});h=r.ok?await r.json():null;}catch{h=null;}
if (!h||!h.ok){tone('bad','NOT REACHABLE');note.textContent='No answer from the network. If it was never deployed, open STRUTHIO ADMIN and use DEPLOY NETWORK. Only VS needs it — everything else still plays.';}
else if (!h.open){tone('warn',`VS CLOSED${h.network?' · NETWORK '+h.network:''}`);note.textContent=h.message?`Players see: “${h.message}”`:'New matches are refused.';}
else{tone('good',`LIVE${h.network?' · NETWORK '+h.network:''}`);note.textContent=`Protocol ${h.protocol}${h.migration?' · '+h.migration:''} · this Console is ${build}.`;}
keyBox.hidden=!!memKey;ctl.hidden=!memKey||!h;
if (memKey&&h){
try{
last=await call('/state');
const s=last.settings;
counts.replaceChildren(count(last.live.rooms,'ROOMS'),count(last.live.playing,'PLAYING'),count(last.today.matches,'TODAY'));
if (!msgInput.matches(':focus')){openChoice=s.open;setSeg();msgInput.value=s.message||'';}
rooms.replaceChildren(...(last.live.list.length?last.live.list.map((r)=>{
const li=el('li');const end=el('button',{type:'button',class:'is-danger','data-room':r.code},'END');
end.addEventListener('click',()=>endRoom(r.code));
li.append(el('b',{},r.code),el('span',{},`${r.state} · ${ago(r.age)}${r.matches?` · ${r.matches} played`:''}`),end);
return li;
}):[Object.assign(el('li'),{textContent:'No rooms open.'})]));
}catch (e){
ctl.hidden=true;
if (e.key){keyBox.hidden=false;status.textContent='THE NETWORK DID NOT ACCEPT THIS KEY · COPY IT AGAIN FROM STRUTHIO ADMIN';}
else status.textContent=`CONTROLS DID NOT ANSWER (${e.message}) · IS THE NETWORK 1.3 OR NEWER?`;
}
}
busy=false;
}
async function save(){
try{await call('/settings',{open:openChoice,message:msgInput.value.trim()});msgInput.blur();await refresh(openChoice?'SAVED · VS IS OPEN':'SAVED · VS IS CLOSED');}
catch (e){status.textContent=e.key?'KEY REFUSED':`NOT SAVED (${e.message})`;}
}
async function endRoom(code){
if (typeof confirm==='function'&&!confirm(`End room ${code}? Both phones leave the match.`)) return;
try{const r=await call('/close',{code});await refresh(r.closed?`ROOM ${code} ENDED`:`ROOM ${code} WAS ALREADY GONE`);}
catch (e){status.textContent=`NOT ENDED (${e.message})`;}
}
function useKey(k){
k=String(k||'').trim();
if (!/^[0-9a-f]{32,128}$/i.test(k)){status.textContent='THAT IS NOT A NETWORK KEY · USE COPY CONSOLE KEY IN STRUTHIO ADMIN';return;}
memKey=k;kv.set(KEY_STORE,k);keyInput.value='';refresh('KEY SAVED ON THIS PHONE');
}
pasteBtn.addEventListener('click',async ()=>{
try{useKey(await navigator.clipboard.readText());}catch{status.textContent='PASTE BLOCKED · LONG-PRESS THE BOX AND PASTE';keyInput.focus();}
});
saveKeyBtn.addEventListener('click',()=>useKey(keyInput.value));
keyInput.addEventListener('keydown',(e)=>{if (e.key==='Enter') useKey(keyInput.value);});
openBtn.addEventListener('click',()=>{openChoice=true;setSeg();});
closeBtn.addEventListener('click',()=>{openChoice=false;setSeg();});
saveBtn.addEventListener('click',save);
forgetBtn.addEventListener('click',()=>{memKey='';kv.set(KEY_STORE,null);last=null;refresh('KEY FORGOTTEN ON THIS PHONE');});
refreshBtn.addEventListener('click',()=>refresh('UPDATED'));
doneBtn.addEventListener('click',()=>api.close());
const api={
open(){
root.hidden=false;status.textContent='';tone('','CHECKING…');
if (openModal&&!release) release=openModal(root,{onEscape:()=>api.close(),initialFocus:doneBtn});
return refresh();
},
close(){root.hidden=true;if (release){release();release=null;}},
refresh,
get isOpen(){return!root.hidden;},
get state(){return last;},
net,
};
return api;
}
