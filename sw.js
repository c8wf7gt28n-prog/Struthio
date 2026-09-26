const BUILD='STRUTHIO-CONSOLE-3.5.4';
const CACHE_PREFIX='struthio-console-';
const CACHE=`${CACHE_PREFIX}${BUILD}`;
const CARTRIDGE_CACHE='struthio-cartridge-packs-v1';
const CORE=[
'./','./index.html','./app.mjs','./console.json',
'./console/episode-loader.mjs','./console/cartridge-installer.mjs','./console-assets/console-shell.css','./console/sprite-profiles.mjs','./console/modal.mjs','./console/palette-bridge.mjs','./console/viewport-shim.mjs','./console/qr-cart.mjs','./console/vs-net.mjs','./console/vs-ui.mjs','./console/tcs-cal.mjs','./console/net-panel.mjs','./console/vendor/qrcode.mjs','./console/episode-pack.schema.json',
'./factory/','./factory/index.html','./factory/app.mjs','./factory/brief.mjs',
'./factory/style.css','./factory/manifest.webmanifest','./factory/README.txt',
'./manifest.webmanifest','./console-assets/icon-192.png',
'./console-assets/icon-512.png','./console-assets/apple-touch-icon.png',
'./console-assets/console-machine.css','./console-assets/console-moonrise.css','./console-assets/console-manual.webp','./console-assets/console-poster.webp',
'./console-assets/console-cartridge.webp',
'./console-assets/arcade/arcade-background-rear.webp','./console-assets/arcade/arcade-middle-near.webp','./console-assets/arcade/arcade-islands-v4.webp','./console-assets/arcade/arcade-islands.metadata.json','./console-assets/arcade/tarmac-at-midnight-loop.mp3','./console-assets/arcade/arcade-jouster-48.webp',
'./console-assets/full-bird-192.webp','./console-assets/rider-attachments.webp','./console-assets/rider-attachments.json',
'./src/audio/worklet.mjs','./src/audio/presentation.mjs','./src/audio/synth.mjs',
];
async function detachedResponse(response){
const body=await response.arrayBuffer();
const headers=new Headers(response.headers);
headers.delete('content-encoding');headers.delete('content-length');
return new Response(body,{status:response.status,statusText:response.statusText,headers});
}
async function rangedResponse(request,response){
const value=request.headers.get('range');
if (!value||response.status!==200) return response;
const match=/^bytes=(\d*)-(\d*)$/i.exec(value.trim());
const body=await response.arrayBuffer(),size=body.byteLength;
const headers=new Headers(response.headers);headers.delete('content-encoding');headers.set('accept-ranges','bytes');
let start=-1,end=-1;
if (match&&size>0){
if (match[1]===''){const suffix=Number(match[2]);if (Number.isSafeInteger(suffix)&&suffix>0){start=Math.max(0,size-suffix);end=size-1;}}
else{start=Number(match[1]);end=match[2]===''?size-1:Math.min(Number(match[2]),size-1);if (!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start<0||start>=size||end<start) start=end=-1;}
}
if (start<0){headers.set('content-range',`bytes */${size}`);headers.set('content-length','0');return new Response(null,{status:416,headers});}
const slice=body.slice(start,end+1);headers.set('content-range',`bytes ${start}-${end}/${size}`);headers.set('content-length',String(slice.byteLength));
return new Response(slice,{status:206,headers});
}
function collectAssetPaths(value,output=[]){
if (Array.isArray(value)) for (const item of value) collectAssetPaths(item,output);
else if (value&&typeof value==='object'){
if (typeof value.path==='string') output.push(value.path);
for (const item of Object.values(value)) collectAssetPaths(item,output);
}
return output;
}
async function installList(){
const urls=[...CORE];
const configResponse=await fetch('./console.json',{cache:'reload'});
if (!configResponse.ok) throw new Error(`console.json ${configResponse.status}`);
const config=await configResponse.clone().json();
for (const manifestPath of[...new Set([config.internalRom,config.activeEpisode].filter(Boolean))]){
const manifestUrl=new URL(manifestPath,self.registration.scope).href;
const manifestResponse=await fetch(manifestUrl,{cache:'reload'});
if (!manifestResponse.ok) throw new Error(`episode manifest ${manifestResponse.status}`);
const manifest=await manifestResponse.clone().json();
const prefix=new URL('./',manifestUrl);
urls.push(manifestUrl,...collectAssetPaths(manifest.assets).map((item)=>new URL(item,prefix).href));
}
return[...new Set(urls)];
}
self.addEventListener('install',(event)=>event.waitUntil((async ()=>{
const cache=await caches.open(CACHE);
try{
for (const url of await installList()){
const response=await fetch(url,{cache:'reload',redirect:'follow'});
if (!response.ok) throw new Error(`precache ${url} ${response.status}`);
await cache.put(url,await detachedResponse(response));
}
}catch (error){await caches.delete(CACHE);throw error;}
})()));
self.addEventListener('activate',(event)=>event.waitUntil((async ()=>{
const names=await caches.keys();
await Promise.all(names.filter((name)=>name!==CACHE&&name.startsWith(CACHE_PREFIX)).map((name)=>caches.delete(name)));
await self.clients.claim();
})()));
self.addEventListener('message',(event)=>{if (event.data?.type==='SKIP_WAITING') self.skipWaiting();});
self.addEventListener('fetch',(event)=>{
if (event.request.method!=='GET'||new URL(event.request.url).origin!==location.origin) return;
event.respondWith((async ()=>{
const cache=await caches.open(CACHE),navigation=event.request.mode==='navigate';
const pathname=new URL(event.request.url).pathname;
const factoryPath=new URL('factory/',self.registration.scope).pathname;
const isFactory=pathname===factoryPath.slice(0,-1)||pathname.startsWith(factoryPath);
if (pathname.includes('/__struthio_cartridges__/')){
const cartridge=await caches.open(CARTRIDGE_CACHE);
const hit=await cartridge.match(event.request,{ignoreSearch:true});
if (hit) return rangedResponse(event.request,hit);
return new Response('CARTRIDGE FILE NOT INSTALLED',{status:404,headers:{'content-type':'text/plain'}});
}
if (pathname.endsWith('/console.json')||pathname.endsWith('/episode.json')){
try{
const response=await fetch(event.request,{cache:'no-store'});
if (response.ok) await cache.put(event.request,response.clone());
return response;
}catch{
const fallback=await cache.match(event.request,{ignoreSearch:true});
if (fallback) return fallback;
throw new Error('CARTRIDGE_CONFIGURATION_UNAVAILABLE');
}
}
if (isFactory&&navigation){
const hit=await cache.match('./factory/index.html');
if (hit) return hit;
try{const response=await fetch(event.request);if (response.ok) return detachedResponse(response);}catch{}
return new Response('<!doctype html><meta charset="utf-8"><title>STRUTHIO FACTORY</title><body style="background:#050608;color:#e7be68;font:20px system-ui;display:grid;place-content:center;height:100vh;margin:0"><p role="alert">OFFLINE INSTALL REQUIRED</p></body>',{status:503,headers:{'content-type':'text/html'}});
}
const scopePath=new URL('./',self.registration.scope).pathname;
if (navigation&&['cart/','qr/','tcs/','source/'].some((p)=>pathname.startsWith(scopePath+p))){
try{const response=await fetch(event.request);if (response.ok){cache.put(event.request,response.clone()).catch(()=>{});return response;}return response;}
catch{const hit=await cache.match(event.request,{ignoreSearch:true});if (hit) return hit;}
return new Response('<!doctype html><meta charset="utf-8"><title>STRUTHIO</title><body style="background:#050505;color:#FACA3A;font:20px system-ui;display:grid;place-content:center;height:100vh;margin:0"><p role="alert">CONNECT TO OPEN THIS PAGE</p></body>',{status:503,headers:{'content-type':'text/html'}});
}
if (navigation){
const hit=await cache.match('./index.html');
if (hit) return hit;
try{const response=await fetch(event.request);if (response.ok) return detachedResponse(response);}catch{}
return new Response('<!doctype html><meta charset="utf-8"><title>STRUTHIO CONSOLE</title><body style="background:#02070b;color:#f24a22;font:20px system-ui;display:grid;place-content:center;height:100vh;margin:0"><p role="alert">OFFLINE INSTALL REQUIRED</p></body>',{status:503,headers:{'content-type':'text/html'}});
}
const hit=await cache.match(event.request,{ignoreSearch:true});
if (hit) return rangedResponse(event.request,hit);
const response=await fetch(event.request);
if (response.ok) cache.put(event.request,response.clone()).catch(()=>{});
return response;
})());
});
