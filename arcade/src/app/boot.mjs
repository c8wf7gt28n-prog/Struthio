// STRUTHIO ARCADE · start-up: check the browser, load the rulebook and art, build
// the atlas and renderer, start the session; and the error screen.
import R from '../data/rules.mjs';
import{buildAtlas}from '../render/atlas.mjs';
import{createRenderer,FatalError}from '../render/renderer.mjs';
import{installViewportShim}from '../ui/viewport-shim.mjs';
import{loadArt}from './art.mjs';
import{createSession}from './session.mjs';
import{memoryStorage}from '../save/checkpoint.mjs';

export const BUILD_ID='STRUTHIO-ARCADE-1.4.0';
const FATAL_HINT={
FATAL_SECURE_CONTEXT:'Open the game over https or from localhost.',
FATAL_WEBGPU_UNAVAILABLE:'This browser does not support WebGPU, which the game needs. Play in a current Chrome or Edge (desktop or Android), or Safari on iPhone, iPad or Mac running version 26 or later.',
FATAL_WEBGPU_CONTEXT:'This browser does not support WebGPU, which the game needs. Play in a current Chrome or Edge (desktop or Android), or Safari on iPhone, iPad or Mac running version 26 or later.',
FATAL_ADAPTER:'WebGPU is present but no graphics adapter answered. Turn on hardware acceleration in your browser settings, update your graphics driver, then reload.',
FATAL_DEVICE:'WebGPU is present but no graphics adapter answered. Turn on hardware acceleration in your browser settings, update your graphics driver, then reload.',
FATAL_GPU_VALIDATION:'The renderer failed a WebGPU validation check. Reload to retry; your saved run is safe.',
FATAL_GPU_LOST_TWICE:'The graphics device was lost twice. Reload to start again; your saved run is safe.',
FATAL_RECOVERY:'The graphics device was lost and could not be rebuilt. Reload to start again.',
OFFLINE_INSTALL_REQUIRED:'The game has not finished installing for offline play. Reconnect once to finish.',
};
const FATAL_HINT_DEFAULT='Reload to start again. Your saved run is safe.';
const UNSUPPORTED=new Set(['FATAL_SECURE_CONTEXT','FATAL_WEBGPU_UNAVAILABLE','FATAL_WEBGPU_CONTEXT','FATAL_ADAPTER','FATAL_DEVICE']);
const BOOT_STARTED=typeof performance!=='undefined'?performance.now():0;

function finishBoot(){
const boot=document.getElementById('boot');
if (!boot||boot.hidden) return;
const delay=Math.max(0,520-(performance.now()-BOOT_STARTED));
setTimeout(()=>{
document.body.classList.remove('is-booting');
document.body.classList.add('is-ready');
setTimeout(()=>{boot.hidden=true;},560);
},delay);
}
export function showFatal(code,detail){
const el=document.getElementById('fatal');
el.hidden=false;
const unsupported=UNSUPPORTED.has(code);
el.querySelector('h1').textContent=unsupported?'THIS BROWSER CANNOT RUN STRUTHIO':'STRUTHIO CANNOT START';
el.querySelector('.code').textContent=code;
el.querySelector('.detail').textContent=unsupported?'':(detail||'');
el.querySelector('.hint').textContent=FATAL_HINT[code]||FATAL_HINT_DEFAULT;
document.getElementById('game').setAttribute('aria-hidden','true');
const boot=document.getElementById('boot');
if (boot) boot.hidden=true;
document.body.classList.remove('is-booting');
document.body.classList.add('is-ready');
}
function localStorageAdapter(){
try{const probe='__struthio_arcade_probe';localStorage.setItem(probe,'1');localStorage.removeItem(probe);}catch{return null;}
const guard=(fn,fallback)=>{try{return fn();}catch{return fallback;}};
return{
getItem:(k)=>guard(()=>localStorage.getItem(k),null),
setItem:(k,v)=>guard(()=>{localStorage.setItem(k,v);},undefined),
removeItem:(k)=>guard(()=>{localStorage.removeItem(k);},undefined),
keys:()=>guard(()=>{const out=[];for (let i=0;i<localStorage.length;i++) out.push(localStorage.key(i));return out;},[]),
};
}
export async function boot({base='./',flags={},local=false}={}){
let storage=localStorageAdapter();
const storageBlocked=!storage;
if (storageBlocked) storage=memoryStorage();
const app={fatal:null,flags,local,buildId:BUILD_ID,storageBlocked};
if (local) window.__struthio=app;
installViewportShim({});
try{
if (!globalThis.isSecureContext) throw new FatalError('FATAL_SECURE_CONTEXT','A secure context (https or localhost) is required.');
if (!navigator.gpu) throw new FatalError('FATAL_WEBGPU_UNAVAILABLE','WebGPU is not available in this browser.');
const fetchJson=async (p)=>{const r=await fetch(base+p,{cache:'no-cache'});if (!r.ok) throw new Error(`FETCH ${p} ${r.status}`);return r.json();};
const art=await loadArt(base,fetchJson);
const atlas=buildAtlas(R,art);
const canvas=document.getElementById('game');
let session=null;
const renderer=await createRenderer(canvas,{
atlasPixels:atlas.surface,
birdPixels:art.bird,
onLost:(info)=>{app.lost=info;},
onRecovered:(info)=>{app.recovered=info;renderer.markAtlasDirty();renderer.markWorldDirty();},
onFatal:(e)=>{app.fatal={code:e.code,detail:e.detail};app.stopped=true;if (session) session.stop();showFatal(e.code,e.detail);},
});
if (!renderer.uploadWorld(atlas.world)) throw new Error('WORLD_PLATES_UPLOAD_REJECTED');
session=createSession({R,atlas,art,renderer,canvas,storage,app,base});
app.session=session;
session.start();
finishBoot();
return session;
}catch (e){
let code=e instanceof FatalError?e.code:'FATAL_BOOT';
if (!(e instanceof FatalError)&&/FETCH|Failed to fetch|NetworkError/.test(String(e.message))&&!(navigator.serviceWorker&&navigator.serviceWorker.controller)) code='OFFLINE_INSTALL_REQUIRED';
app.fatal={code,detail:e.detail||e.message};
showFatal(code,e.detail||e.message);
throw e;
}
}
