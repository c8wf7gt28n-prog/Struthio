import{installCartridgeZip,ensureCartridgeRouting,readInstalledEpisode}from './cartridge-installer.mjs';
export const CARD_ID=/^[A-Z0-9]{2,8}-[A-Z0-9]{3,8}$/;
export const REGISTRY_PATH='cart/registry.json';
const SCHEME='STRUTHIO-CART:';
export function parseCardPayload(text,{origin=globalThis.location?.origin,basePath='/'}={}){
const raw=String(text||'').trim();
if (!raw||raw.length>256) throw new Error('QR_NOT_A_CARD');
const upper=raw.toUpperCase();
if (CARD_ID.test(upper)) return{cardId:upper,via:'CODE'};
if (upper.startsWith(SCHEME)&&CARD_ID.test(upper.slice(SCHEME.length))) return{cardId:upper.slice(SCHEME.length),via:'SCHEME'};
let url;
try{url=new URL(raw);}catch{throw new Error('QR_NOT_A_CARD');}
if (url.protocol!=='https:'&&!(url.hostname==='127.0.0.1'||url.hostname==='localhost')) throw new Error('QR_UNTRUSTED_HOST');
if (url.origin!==origin) throw new Error('QR_UNTRUSTED_HOST');
const prefix=(basePath.endsWith('/')?basePath:basePath+'/')+'cart/';
if (!url.pathname.startsWith(prefix)||url.search||url.hash) throw new Error('QR_UNTRUSTED_PATH');
const id=url.pathname.slice(prefix.length).replace(/\/(index\.html)?$/,'').toUpperCase();
if (!CARD_ID.test(id)) throw new Error('QR_UNTRUSTED_PATH');
return{cardId:id,via:'URL'};
}
export async function resolveCard(cardId,{base='./',fetchImpl=fetch}={}){
const r=await fetchImpl(new URL(REGISTRY_PATH,new URL(base,location.href)).href,{cache:'no-cache'});
if (!r.ok) throw new Error('RESOLVER_HTTP_'+r.status);
const reg=await r.json();
if (!reg||reg.kind!=='struthio-cart-registry'||reg.schema!==1||typeof reg.cards!=='object') throw new Error('RESOLVER_INVALID');
const entry=reg.cards[cardId];
if (!entry) throw new Error('CARD_UNKNOWN');
if (entry.revoked) throw new Error('CARD_REVOKED');
if (typeof entry.pack!=='string'||!/^cart\/packs\/[a-z0-9._-]+\.zip$/.test(entry.pack)||!/^[0-9a-f]{64}$/.test(entry.packSha256||'')) throw new Error('RESOLVER_INVALID');
return{cardId,...entry};
}
async function sha256Hex(buffer){
const d=await crypto.subtle.digest('SHA-256',buffer);
return[...new Uint8Array(d)].map((b)=>b.toString(16).padStart(2,'0')).join('');
}
export async function fetchVerifiedPack(entry,{base='./',fetchImpl=fetch,maxBytes=25*1024*1024}={}){
const r=await fetchImpl(new URL(entry.pack,new URL(base,location.href)).href,{cache:'no-cache'});
if (!r.ok) throw new Error('PACK_HTTP_'+r.status);
const bytes=await r.arrayBuffer();
if (bytes.byteLength>maxBytes) throw new Error('PACK_TOO_LARGE');
if (await sha256Hex(bytes)!==entry.packSha256) throw new Error('PACK_HASH_FAIL');
return new Blob([bytes],{type:'application/zip'});
}
const FRIENDLY={
QR_NOT_A_CARD:'THAT QR IS NOT A STRUTHIO CARD',QR_UNTRUSTED_HOST:'CARD POINTS OUTSIDE THIS CONSOLE',QR_UNTRUSTED_PATH:'CARD ADDRESS NOT RECOGNISED',
CARD_UNKNOWN:'UNKNOWN CARD CODE',CARD_REVOKED:'THIS CARD RELEASE WAS WITHDRAWN',RESOLVER_INVALID:'CARD REGISTRY UNREADABLE',
PACK_HASH_FAIL:'CARTRIDGE FAILED ITS CHECK · NOT INSTALLED',PACK_TOO_LARGE:'CARTRIDGE TOO LARGE',CAMERA_DENIED:'CAMERA NOT ALLOWED · USE PHOTO OR CODE',
CAMERA_UNAVAILABLE:'NO CAMERA HERE · USE PHOTO OR CODE',CAMERA_TIMEOUT:'CAMERA DID NOT START · USE PHOTO OR CODE',NO_QR_IN_PHOTO:'NO QR FOUND IN THAT PHOTO',
};
export function friendlyQrError(error){
const m=String(error&&error.message||error);
const key=Object.keys(FRIENDLY).find((k)=>m.startsWith(k));
if (key) return FRIENDLY[key];
if (/^RESOLVER_HTTP|^PACK_HTTP|Failed to fetch|NetworkError/.test(m)) return 'NETWORK NEEDED FOR A NEW CARD';
return 'CARTRIDGE NOT READ';
}
let jsQRLoad=null;
export function loadDecoder(base){
if (globalThis.jsQR) return Promise.resolve(globalThis.jsQR);
if (!jsQRLoad) jsQRLoad=new Promise((resolve,reject)=>{
const s=document.createElement('script');
s.src=new URL('console/vendor/jsQR.js',new URL(base,location.href)).href;
s.onload=()=>(globalThis.jsQR?resolve(globalThis.jsQR):reject(new Error('DECODER_MISSING')));
s.onerror=()=>{jsQRLoad=null;reject(new Error('DECODER_MISSING'));};
document.head.appendChild(s);
});
return jsQRLoad;
}
export function decodeCentre(jsQR,source,w,h,canvas,crop=0.8,size=480){
const side=Math.floor(Math.min(w,h)*crop);
const sx=Math.floor((w-side)/2),sy=Math.floor((h-side)/2);
const n=Math.min(size,side);
canvas.width=n;canvas.height=n;
const ctx=canvas.getContext('2d',{willReadFrequently:true});
ctx.drawImage(source,sx,sy,side,side,0,0,n,n);
const img=ctx.getImageData(0,0,n,n);
return jsQR(img.data,n,n,{inversionAttempts:'attemptBoth'});
}
function decodeWhole(jsQR,source,canvas,max=1000){
const k=Math.min(1,max/Math.max(source.width,source.height));
const w=Math.max(1,Math.round(source.width*k)),h=Math.max(1,Math.round(source.height*k));
canvas.width=w;canvas.height=h;
const ctx=canvas.getContext('2d',{willReadFrequently:true});
ctx.drawImage(source,0,0,w,h);
return jsQR(ctx.getImageData(0,0,w,h).data,w,h,{inversionAttempts:'attemptBoth'});
}
export function setupQrCart({base='./',validateManifest,basePath=new URL(base,location.href).pathname,log=null}={}){
const trace=(e,d='')=>{try{(log||(()=>{}))(e,d);}catch{}};
let root=null,video=null,stream=null,raf=0,state='READY',busy=false,lastTry=0,startTimer=0;
const work=document.createElement('canvas');
const el=(tag,attrs={},text='')=>{const n=document.createElement(tag);for (const[k,v] of Object.entries(attrs)) n.setAttribute(k,v);if (text) n.textContent=text;return n;};
function build(){
root=el('section',{id:'qr-cart',role:'dialog','aria-modal':'true','aria-labelledby':'qr-cart-title',hidden:''});
const card=el('div',{class:'qr-card'});
card.append(el('p',{class:'qr-kicker'},'DEVELOPMENT · QR-CART v0.1'),el('h2',{id:'qr-cart-title'},'INSERT A CARD'));
const frame=el('div',{class:'qr-frame'});
video=el('video',{playsinline:'',muted:'','aria-label':'Camera preview'});
video.muted=true;video.playsInline=true;
frame.append(video,el('i',{class:'qr-target','aria-hidden':'true'}),el('b',{class:'qr-hint'},'ALIGN THE CARD QR HERE'));
const status=el('p',{id:'qr-status',role:'status','aria-live':'polite'},'READY');
const actions=el('div',{class:'qr-actions'});
const scan=el('button',{type:'button','data-qr':'scan',class:'is-primary'},'SCAN CARD');
const photo=el('button',{type:'button','data-qr':'photo'},'SCAN FROM PHOTO');
const codeBtn=el('button',{type:'button','data-qr':'code'},'ENTER CARD CODE');
const printBtn=el('button',{type:'button','data-qr':'print'},'PRINT DEMO CARD');
const close=el('button',{type:'button','data-qr':'close'},'CLOSE');
const file=el('input',{type:'file',accept:'image/*',hidden:''});
const form=el('form',{class:'qr-code-form',hidden:''});
const input=el('input',{type:'text',inputmode:'text',autocapitalize:'characters',autocomplete:'off',spellcheck:'false',placeholder:'DEMO-0001','aria-label':'Card code',maxlength:'17'});
form.append(input,el('button',{type:'submit'},'LOAD'));
actions.append(scan,photo,codeBtn,printBtn,close);
card.append(frame,status,form,actions,file);
root.append(card);
document.body.appendChild(root);
scan.addEventListener('click',()=>startCamera());
photo.addEventListener('click',()=>{stopCamera();file.value='';file.click();});
file.addEventListener('change',()=>scanPhoto(file.files?.[0]));
codeBtn.addEventListener('click',()=>{stopCamera();form.hidden=false;input.focus();});
form.addEventListener('submit',(e)=>{e.preventDefault();handleText(input.value,'CODE');});
printBtn.addEventListener('click',()=>{location.href=new URL('qr/card.html?code=DEMO-0001',new URL(base,location.href)).href;});
close.addEventListener('click',()=>api.close());
root.addEventListener('keydown',(e)=>{if (e.key==='Escape'){e.preventDefault();api.close();}});
return{status};
}
let ui=null;
const setState=(s,text)=>{state=s;if (root) root.dataset.state=s;if (ui) ui.status.textContent=text||s;api.state=s;};
async function startCamera(){
if (busy) return;
stopCamera();
if (!navigator.mediaDevices?.getUserMedia){setState('FAILED',FRIENDLY.CAMERA_UNAVAILABLE);trace('camera_stream_failure','no mediaDevices');return;}
setState('REQUESTING','ALLOW THE CAMERA…');
trace('scanner_start');
try{
const jsQR=await loadDecoder(base);
startTimer=setTimeout(()=>{if (state==='REQUESTING'){stopCamera();setState('FAILED',FRIENDLY.CAMERA_TIMEOUT);trace('camera_stream_failure','timeout');}},9000);
stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:720}}});
clearTimeout(startTimer);
video.srcObject=stream;
await video.play();
root.classList.add('is-live');
setState('SCANNING','SCANNING…');
trace('scanner_ready');
const loop=(t)=>{
if (state!=='SCANNING') return;
raf=requestAnimationFrame(loop);
if (t-lastTry<125||video.readyState<2) return;
lastTry=t;
const hit=decodeCentre(jsQR,video,video.videoWidth,video.videoHeight,work);
if (hit&&hit.data){trace('scanner_decode');stopCamera();setState('DECODED','CARD READ');handleText(hit.data,'CAMERA');}
};
raf=requestAnimationFrame(loop);
}catch (error){
clearTimeout(startTimer);
stopCamera();
const denied=error&&(error.name==='NotAllowedError'||error.name==='SecurityError');
setState('FAILED',denied?FRIENDLY.CAMERA_DENIED:FRIENDLY.CAMERA_UNAVAILABLE);
trace(denied?'camera_permission_denied':'camera_stream_failure',String(error&&error.name));
}
}
function stopCamera(){
cancelAnimationFrame(raf);raf=0;clearTimeout(startTimer);
if (stream) for (const track of stream.getTracks()) track.stop();
stream=null;
if (video){video.pause?.();video.srcObject=null;}
root?.classList.remove('is-live');
if (state==='SCANNING'||state==='REQUESTING') setState('READY','READY');
}
async function scanPhoto(fileObj){
if (!fileObj) return;
try{
const jsQR=await loadDecoder(base);
const bmp=await createImageBitmap(fileObj);
let hit=decodeWhole(jsQR,bmp,work);
for (const crop of[1,0.8,0.6]){if (hit) break;hit=decodeCentre(jsQR,bmp,bmp.width,bmp.height,work,crop,900);}
bmp.close?.();
if (!hit) throw new Error('NO_QR_IN_PHOTO');
setState('DECODED','CARD READ');
handleText(hit.data,'PHOTO');
}catch (error){setState('FAILED',friendlyQrError(error));}
}
async function handleText(text,via){
if (busy) return;
busy=true;
try{
const{cardId}=parseCardPayload(text,{origin:location.origin,basePath});
setState('RESOLVING',`CARD ${cardId} · LOOKING UP…`);
const entry=await resolveCard(cardId,{base});
trace('resolver_ok',cardId);
const installed=await readInstalledEpisode(base).catch(()=>null);
if (installed&&installed.manifest&&installed.manifest.id===entry.cartridgeId&&installed.manifest.buildId===entry.buildId){
setState('MOUNTED',`${entry.title} · ALREADY IN SLOT A`);
trace('mounted_from_cache',cardId);
setTimeout(()=>openCartridgeMenu(),700);
return;
}
setState('DOWNLOADING',`${entry.title} · DOWNLOADING…`);
const blob=await fetchVerifiedPack(entry,{base});
setState('VERIFYING',`${entry.title} · CHECKING EVERY FILE…`);
await ensureCartridgeRouting(base);
const result=await installCartridgeZip(blob,{base,validateManifest});
trace('install_complete',result.id);
setState('MOUNTED',`${result.title} · IN SLOT A · OFFLINE READY`);
setTimeout(()=>openCartridgeMenu(),900);
}catch (error){
trace('qr_fail',String(error&&error.message));
setState('FAILED',friendlyQrError(error));
busy=false;
}
}
function openCartridgeMenu(){
const next=new URL(location.href);
next.searchParams.delete('rom');next.searchParams.delete('episode');
next.searchParams.set('menu','cartridge');
location.href=next.href;
}
let opener=null;
const api={
state,
open(){
if (!root) ui=build();
opener=document.activeElement;
root.hidden=false;document.body.classList.add('qr-open');
busy=false;setState('READY','READY · SCAN, PHOTO OR CODE');
root.querySelector('[data-qr="scan"]').focus({preventScroll:true});
},
close(){
stopCamera();
if (root) root.hidden=true;
document.body.classList.remove('qr-open');
setState('READY','READY');
if (opener&&opener.focus) opener.focus({preventScroll:true});
},
get isOpen(){return!!root&&!root.hidden;},
handleText,parse:(t)=>parseCardPayload(t,{origin:location.origin,basePath}),
};
document.addEventListener('visibilitychange',()=>{if (document.visibilityState!=='visible') stopCamera();});
addEventListener('pagehide',stopCamera);
return api;
}
