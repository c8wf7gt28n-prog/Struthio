import{VsLink,VsMatch}from './vs-net.mjs';
import{loadDecoder,decodeCentre}from './qr-cart.mjs';
import{openModal}from './modal.mjs';
import qrcode from './vendor/qrcode.mjs';
const CODE_RE=/^[BCDFGHJKLMNPQRSTVWXZ]{4}$/;
const SEAT_KEY='struthio.vs.seat.v1';
const SEAT_FRESH_MS=120000;
function saveSeat(v){try{if (v) sessionStorage.setItem(SEAT_KEY,JSON.stringify({...v,at:Date.now()}));else sessionStorage.removeItem(SEAT_KEY);}catch{}}
function loadSeat(){
try{const v=JSON.parse(sessionStorage.getItem(SEAT_KEY)||'null');return v&&Date.now()-v.at<SEAT_FRESH_MS&&CODE_RE.test(v.code)?v:null;}catch{return null;}
}
const REJECT_TEXT={
NO_ROOM:'NO MATCH WITH THAT CODE',
ROOM_FULL:'THAT MATCH ALREADY HAS TWO PLAYERS',
MISMATCH:'THE OTHER CONSOLE IS A DIFFERENT VERSION · UPDATE BOTH',
PROTOCOL:'THE OTHER CONSOLE IS A DIFFERENT VERSION · UPDATE BOTH',
NO_SEAT:'THAT MATCH HAS ENDED',
CODE_TAKEN:'TRY AGAIN',
CLOSED:'VS IS CLOSED RIGHT NOW',
UPDATE:'UPDATE YOUR CONSOLE TO PLAY VS',
BUSY:'THE NETWORK IS FULL · TRY AGAIN SOON',
ORIGIN:'THIS CONSOLE IS NOT ON THIS NETWORK’S LIST',
};
const adminWords=(m)=>(typeof m.message==='string'&&m.message.trim()?m.message.trim().slice(0,100).toUpperCase():'');
export function parseVsCode(text,origin=globalThis.location?.origin){
const t=String(text||'').trim();
const bare=t.toUpperCase().replace(/[^A-Z]/g,'');
if (CODE_RE.test(bare)&&t.length<=8) return bare;
try{
const u=new URL(t);
if (origin&&u.origin!==origin) return null;
const c=(u.searchParams.get('vs')||'').toUpperCase();
return CODE_RE.test(c)?c:null;
}catch{return null;}
}
export function relayUrlFor(base,override=''){
const u=new URL(override||'vs/ws',new URL(base,location.href));
u.protocol=u.protocol==='https:'?'wss:':u.protocol==='http:'?'ws:':u.protocol;
return u.href;
}
export function setupVs({base='./',relayUrl,vs,A,hello,onStart,onEvent,onExit,log=()=>{}}){
const el=(tag,attrs={},text='')=>{const n=document.createElement(tag);for (const[k,v] of Object.entries(attrs)) n.setAttribute(k,v);if (text) n.textContent=text;return n;};
const content=vs.vsContent(A);
const RINGS=content.rings.length;
let link=null,match=null,mode='IDLE',release=null,peerLostAt=0,peerWindow=45000,endShown=null,endTimer=0;
let rematchAsked=false,peerRematch=false;
const work=document.createElement('canvas');
let camera=null;
const root=el('section',{id:'vs-panel',role:'dialog','aria-modal':'true','aria-labelledby':'vs-title',hidden:''});
const card=el('div',{class:'vs-card'});
const kicker=el('p',{class:'vs-kicker'},'VS · TWO PHONES');
const title=el('h2',{id:'vs-title'},'VS');
const codeView=el('p',{class:'vs-code','aria-label':'Match code'},'····');
const qrBox=el('div',{class:'vs-qr',role:'img','aria-label':'QR code to join this match'});
const camFrame=el('div',{class:'vs-cam',hidden:''});
const video=el('video',{playsinline:'',muted:'','aria-label':'Camera preview'});video.muted=true;video.playsInline=true;
camFrame.append(video,el('i',{class:'vs-target','aria-hidden':'true'}));
const form=el('form',{class:'vs-join',autocomplete:'off'});
const input=el('input',{type:'text',inputmode:'text',autocapitalize:'characters',autocomplete:'off',spellcheck:'false',maxlength:'4',placeholder:'CODE','aria-label':'Match code (four letters)'});
const joinBtn=el('button',{type:'submit',class:'is-primary'},'JOIN');
form.append(input,joinBtn);
const stats=el('dl',{class:'vs-stats',hidden:''});
const status=el('p',{class:'vs-status',role:'status','aria-live':'polite'},'');
const actions=el('div',{class:'vs-actions'});
const scanBtn=el('button',{type:'button','data-vs':'scan'},'SCAN QR');
const rematchBtn=el('button',{type:'button','data-vs':'rematch',class:'is-primary'},'REMATCH');
const leaveBtn=el('button',{type:'button','data-vs':'leave'},'CANCEL');
actions.append(scanBtn,rematchBtn,leaveBtn);
card.append(kicker,title,codeView,qrBox,camFrame,form,stats,status,actions);
root.append(card);
const hud=el('div',{id:'vs-hud','aria-hidden':'true',hidden:''});
const hudYou=el('span',{class:'vs-side you'}),hudRival=el('span',{class:'vs-side rival'}),hudTime=el('b',{class:'vs-time'},'4:00');
const pips=(host,label)=>{host.append(el('small',{},label));const row=el('span',{class:'vs-pips'});for (let i=0;i<RINGS;i++) row.append(el('i'));host.append(row);return row;};
const youPips=pips(hudYou,'YOU'),rivalPips=pips(hudRival,'RIVAL');
hud.append(hudYou,hudTime,hudRival);
const center=el('div',{id:'vs-center','aria-live':'assertive',hidden:''});
const signal=el('div',{id:'vs-signal',role:'status','aria-live':'polite',hidden:''});
document.body.append(root,hud,center,signal);
form.addEventListener('submit',(e)=>{e.preventDefault();const c=parseVsCode(input.value);if (!c){say('ENTER THE FOUR LETTERS FROM THE OTHER PHONE','bad');return;}join(c);});
input.addEventListener('input',()=>{input.value=input.value.toUpperCase().replace(/[^A-Z]/g,'').slice(0,4);});
scanBtn.addEventListener('click',()=>(camera?stopCamera():startCamera()));
rematchBtn.addEventListener('click',()=>rematch());
leaveBtn.addEventListener('click',()=>leave());
function say(text,tone=''){status.textContent=text;status.dataset.tone=tone;}
function show(kind){
mode=kind;root.dataset.mode=kind;
const host=kind==='HOST',joining=kind==='JOIN',result=kind==='RESULT';
codeView.hidden=!host;qrBox.hidden=!host;form.hidden=!joining;scanBtn.hidden=!joining;
stats.hidden=!result;rematchBtn.hidden=!result;
leaveBtn.textContent=result?'MAIN MENU':'CANCEL';
if (!joining) stopCamera();
if (root.hidden){root.hidden=false;document.body.classList.add('vs-open');release=openModal(root,{onEscape:()=>leave(),initialFocus:joining?input:result?rematchBtn:leaveBtn});}
}
function noMatch(head){
codeView.hidden=true;qrBox.hidden=true;
title.textContent=head;kicker.textContent='VS · STRUTHIO NETWORK';
}
function hidePanel(){
stopCamera();
if (!root.hidden){root.hidden=true;document.body.classList.remove('vs-open');if (release){release();release=null;}}
}
function drawQr(text){
const q=qrcode(0,'M');q.addData(text);q.make();
const n=q.getModuleCount(),qz=3,size=n+qz*2;
let d='';for (let r=0;r<n;r++) for (let c=0;c<n;c++) if (q.isDark(r,c)) d+=`M${c+qz} ${r+qz}h1v1h-1z`;
qrBox.innerHTML=`<svg viewBox="0 0 ${size} ${size}" shape-rendering="crispEdges"><rect width="${size}" height="${size}" fill="#fff"/><path d="${d}" fill="#000"/></svg>`;
qrBox.dataset.payload=text;
}
async function startCamera(){
if (!navigator.mediaDevices?.getUserMedia){say('NO CAMERA HERE · TYPE THE CODE','bad');return;}
try{
say('ALLOW THE CAMERA…');
const jsQR=await loadDecoder(base);
const stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:'environment'}}});
camera={stream,raf:0,last:0};
video.srcObject=stream;await video.play();
camFrame.hidden=false;scanBtn.textContent='STOP CAMERA';say('POINT AT THE QR ON THE OTHER PHONE');
const loop=(t)=>{
if (!camera) return;
camera.raf=requestAnimationFrame(loop);
if (t-camera.last<125||video.readyState<2) return;
camera.last=t;
const hit=decodeCentre(jsQR,video,video.videoWidth,video.videoHeight,work);
const c=hit&&parseVsCode(hit.data);
if (c){stopCamera();input.value=c;join(c);}
};
camera.raf=requestAnimationFrame(loop);
}catch (e){
stopCamera();
say(e&&e.name==='NotAllowedError'?'CAMERA NOT ALLOWED · TYPE THE CODE':'CAMERA UNAVAILABLE · TYPE THE CODE','bad');
}
}
function stopCamera(){
if (!camera) return;
cancelAnimationFrame(camera.raf);
for (const t of camera.stream.getTracks()) t.stop();
camera=null;video.srcObject=null;camFrame.hidden=true;scanBtn.textContent='SCAN QR';
}
function freshLink(){
if (link) link.close();
link=new VsLink({url:relayUrl,build:hello().build,onMessage,onStatus});
match=new VsMatch({
makeGame:(seed)=>new vs.VsGame(A,{seed}),vs,
send:(o)=>link.send(o),toLocal:(ms)=>link.toLocal(ms),
onEvent:(e)=>{try{onEvent(e,match.seat);}catch (err){log('vs_event_error',String(err));}},
onEnd:(e)=>ended(e),
});
api.link=link;api.match=match;
}
function onStatus(s){
log('vs_link',s);
if (s==='FAILED'&&mode==='HOST') noMatch('NO NETWORK');
if (s==='FAILED'&&mode!=='PLAY') say('STRUTHIO NETWORK UNAVAILABLE · ONLY VS NEEDS IT — EVERYTHING ELSE STILL PLAYS','bad');
if (s==='FAILED'&&mode==='PLAY'){endShown=null;ended({winner:-3,reason:'LOST',local:true});}
if (s==='CLOSED'&&mode==='PLAY'&&!endShown) ended({winner:-3,reason:'LOST',local:true});
}
function onMessage(m){
switch (m.t){
case 'room':
saveSeat({code:m.code,seat:m.seat,token:m.token});
if (m.rejoined&&mode==='REJOIN'){say('REJOINED · CATCHING UP…','good');break;}
if (mode==='HOST'){
codeView.textContent=m.code;
const url=new URL(base,location.href);url.search='?vs='+m.code;url.hash='';
drawQr(url.href);
say('WAITING FOR THE OTHER PHONE…');
}else if (mode==='JOIN') say('JOINED · WAITING FOR THE HOST…');
break;
case 'reject':
if (mode==='REJOIN'){saveSeat(null);title.textContent='MATCH OVER';say('THAT MATCH HAS ENDED','bad');leaveBtn.textContent='MAIN MENU';break;}
if (mode==='HOST') noMatch(m.reason==='CLOSED'?'VS IS CLOSED':m.reason==='UPDATE'?'UPDATE NEEDED':m.reason==='BUSY'?'NETWORK FULL':'NO MATCH');
say(adminWords(m)||REJECT_TEXT[m.reason]||'COULD NOT JOIN','bad');break;
case 'paired':
if (mode==='HOST'||mode==='JOIN'){say('RIVAL CONSOLE FOUND · GET READY','good');link.send({t:'ready'});}
break;
case 'go':
endShown=null;clearTimeout(endTimer);rematchAsked=false;peerRematch=false;peerLostAt=0;
match.go(m,link.seat);
if (mode!=='PLAY'){hidePanel();mode='PLAY';hud.hidden=false;document.body.classList.add('vs-live');onStart(api);}
break;
case 'in':match.onInput(m);break;
case 'sendstate':match.onSendState(m);break;
case 'state':match.onState(m);break;
case 'result':match.onResult(m);break;
case 'peer':
if (m.state==='lost'){peerLostAt=performance.now();peerWindow=m.window||30000;if (match.active) match.pause();}
if (m.state==='back') peerLostAt=0;
if (m.state==='ready'&&mode==='RESULT'){peerRematch=true;say(rematchAsked?'STARTING…':'RIVAL WANTS A REMATCH','good');}
if (m.state==='left'&&mode==='RESULT'){rematchBtn.disabled=true;say('RIVAL LEFT THE MATCH');}
break;
case 'abandon':
if (mode==='HOST'||mode==='JOIN'){saveSeat(null);say(m.reason==='ADMIN'?'THE NETWORK CLOSED THIS MATCH':'THE OTHER PHONE LEFT','bad');break;}
endShown=null;ended({winner:-3,reason:m.reason,local:true});break;
default:break;
}
}
function resumeIfAny(){
const seat=loadSeat();
if (!seat) return false;
freshLink();
link.code=seat.code;link.seat=seat.seat;link.token=seat.token;
title.textContent='REJOINING';kicker.textContent='VS · MATCH '+seat.code;
show('REJOIN');say('RECONNECTING TO THE MATCH…');
link.open();
return true;
}
function host(){freshLink();codeView.textContent='····';qrBox.innerHTML='';title.textContent='MATCH CODE';kicker.textContent='VS · SHOW THIS TO THE OTHER PHONE';show('HOST');say('OPENING A MATCH…');link.create(hello());}
function openJoin(code=''){
freshLink();title.textContent='JOIN A MATCH';kicker.textContent='VS · SCAN OR TYPE THE CODE';input.value=code;show('JOIN');
if (code) join(code);else say('ON THE OTHER PHONE: VS · CREATE MATCH');
}
function join(code){say('CONNECTING…');if (!link||link.state!=='IDLE') freshLink();link.join(code,hello());}
function rematch(){if (!link) return;rematchAsked=true;rematchBtn.disabled=true;link.send({t:'ready'});say(peerRematch?'STARTING…':'WAITING FOR THE RIVAL…');}
function leave(){
stopCamera();clearTimeout(endTimer);stopPump();saveSeat(null);
if (link) link.close();
link=null;if (match) match.stop();
hidePanel();hud.hidden=true;center.hidden=true;signal.hidden=true;document.body.classList.remove('vs-live');
const wasPlaying=mode==='PLAY'||mode==='RESULT';
mode='IDLE';
onExit(wasPlaying);
}
function ended(e){
const key=`${e.winner}|${e.reason}`;
if (endShown===key) return;
endShown=key;
clearTimeout(endTimer);
const delay=e.local||e.confirmedByRelay?0:1100;
endTimer=setTimeout(()=>showResult(e),delay);
}
function showResult(e){
if (mode!=='PLAY'&&mode!=='RESULT') return;
const seat=match.seat,truth=match.truth;
const me=truth?truth.birds[seat]:null;
const head=e.winner===seat?'YOU WIN':e.winner===-2?'DRAW':e.winner===-3?'NO CONTEST':'RIVAL WINS';
title.textContent=head;
kicker.textContent=e.winner===-3?(e.reason==='PEER_QUIT'?'VS · THE RIVAL LEFT':e.reason==='ADMIN'?'VS · MATCH CLOSED BY THE NETWORK':'VS · THE CONNECTION WAS LOST')
:e.reason==='TIME'?'VS · TIME · MOST RINGS WINS':'VS · FIRST THROUGH ALL SIX RINGS';
const secs=truth?Math.max(0,Math.round((truth.tick-vs.VS_COUNTDOWN_TICKS)/60)):0;
stats.replaceChildren();
const row=(k,v)=>{stats.append(el('dt',{},k),el('dd',{},v));};
if (me){row('RINGS',`${me.rings}/${RINGS}`);row('JOUSTS WON',String(me.jousts));row('FALLS',String(me.deaths));}
row('TIME',`${Math.floor(secs/60)}:${String(secs%60).padStart(2,'0')}`);
rematchBtn.disabled=e.winner===-3;rematchAsked=false;
root.dataset.outcome=e.winner===seat?'win':e.winner===-2?'draw':'loss';
show('RESULT');
say(e.winner===-3?'':peerRematch?'RIVAL WANTS A REMATCH':'');
hud.hidden=true;center.hidden=true;signal.hidden=true;
stopPump();
}
let sampler=null,pumpTimer=0;
function pump(){if (match&&match.active&&sampler) match.update(sampler);}
function setSampler(fn){
sampler=fn;
if (!pumpTimer) pumpTimer=setInterval(pump,10);
}
function stopPump(){if (pumpTimer){clearInterval(pumpTimer);pumpTimer=0;}}
let lastHud='';
let seatStamp=0;
function frame(){
if (!match||!match.active) return null;
if (mode==='PLAY') pump();
const s=match.view;if (!s) return null;
if (mode!=='PLAY'){if (!signal.hidden) signal.hidden=true;if (!center.hidden) center.hidden=true;return s;}
const now=performance.now();
if (now-seatStamp>2000&&link&&link.seat>=0){seatStamp=now;saveSeat({code:link.code,seat:link.seat,token:link.token});}
const me=s.birds[match.seat],rival=s.birds[1-match.seat];
const left=Math.max(0,vs.VS_MAX_TICKS-Math.max(0,s.tick-vs.VS_COUNTDOWN_TICKS));
const secs=Math.ceil(left/60);
const key=`${me.rings}|${rival.rings}|${secs}`;
if (key!==lastHud){
lastHud=key;
[...youPips.children].forEach((p,i)=>p.classList.toggle('on',i<me.rings));
[...rivalPips.children].forEach((p,i)=>p.classList.toggle('on',i<rival.rings));
hudTime.textContent=`${Math.floor(secs/60)}:${String(secs%60).padStart(2,'0')}`;
hud.classList.toggle('is-late',secs<=30&&s.phase==='PLAY');
}
let call='';
if (s.phase==='COUNTDOWN') call=String(Math.ceil(s.countdown/60));
else if (s.phase==='PLAY'&&s.tick-vs.VS_COUNTDOWN_TICKS<45) call='GO!';
if (center.textContent!==call){center.textContent=call;center.hidden=!call;center.dataset.call=call;}
let sig='';
if (link.state==='RECONNECTING'||link.state==='CONNECTING') sig='SIGNAL LOST · RECONNECTING…';
else if (peerLostAt) sig=`RIVAL SIGNAL LOST · WAITING ${Math.max(0,Math.ceil((peerWindow-(performance.now()-peerLostAt))/1000))}`;
else if (match.waiting) sig='WAITING FOR THE RIVAL…';
if (signal.textContent!==sig){signal.textContent=sig;signal.hidden=!sig;}
return s;
}
const stampOnHide=()=>{if ((mode==='PLAY'||mode==='RESULT')&&link&&link.seat>=0) saveSeat({code:link.code,seat:link.seat,token:link.token});};
addEventListener('pagehide',stampOnHide);
document.addEventListener('visibilitychange',()=>{if (document.visibilityState==='hidden') stampOnHide();else if (link&&mode!=='IDLE') link.wake();});
const api={
get mode(){return mode;},
get playing(){return mode==='PLAY'&&!!match&&match.active;},
get seat(){return match?match.seat:0;},
link:null,match:null,
host,openJoin,leave,frame,setSampler,parseVsCode,resumeIfAny,
get view(){return match?match.view:null;},
};
return api;
}
