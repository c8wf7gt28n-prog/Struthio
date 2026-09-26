import{openModal}from './modal.mjs';
export const CARTRIDGE_CACHE='struthio-cartridge-packs-v1';
export const CARTRIDGE_MARKER='__struthio_cartridges__/active.json';
const MAX_ENTRIES=512;
export const CARTRIDGE_BUDGET=Object.freeze({maxFileBytes:24*1024*1024,maxTotalBytes:64*1024*1024});
const MAX_FILE_BYTES=CARTRIDGE_BUDGET.maxFileBytes;
const MAX_TOTAL_BYTES=CARTRIDGE_BUDGET.maxTotalBytes;
const PACK_ROOT='__struthio_cartridges__/';
const ZIP_LOCAL=0x04034b50;
const ZIP_CENTRAL=0x02014b50;
const ZIP_END=0x06054b50;
const textDecoder=new TextDecoder('utf-8',{fatal:true});
function fail(code,detail=''){
const error=new Error(detail?`${code}: ${detail}`:code);
error.code=code;
throw error;
}
function bytesOf(value){
if (value instanceof Uint8Array) return value;
if (value instanceof ArrayBuffer) return new Uint8Array(value);
if (ArrayBuffer.isView(value)) return new Uint8Array(value.buffer,value.byteOffset,value.byteLength);
return null;
}
async function sourceBytes(source){
const direct=bytesOf(source);
if (direct) return direct;
if (source&&typeof source.arrayBuffer==='function') return new Uint8Array(await source.arrayBuffer());
fail('CARTRIDGE_FILE_UNREADABLE');
}
function normalizeZipPath(raw){
if (!raw||raw.includes('\\')||raw.includes('\0')||raw.startsWith('/')||/^[a-z]:/i.test(raw)) fail('CARTRIDGE_PATH_INVALID',raw);
const parts=raw.split('/');
const clean=[];
for (const part of parts){
if (!part||part==='.') continue;
if (part==='..') fail('CARTRIDGE_PATH_ESCAPE',raw);
clean.push(part);
}
if (!clean.length) fail('CARTRIDGE_PATH_INVALID',raw);
return clean.join('/');
}
function normalizeAssetPath(raw){
if (typeof raw!=='string'||!raw||raw.includes('\\')||raw.includes('\0')||/[?#]/.test(raw)||raw.startsWith('/')||/^[a-z]+:/i.test(raw)) fail('CARTRIDGE_ASSET_PATH_INVALID',String(raw));
return normalizeZipPath(raw);
}
let crcTable=null;
function crc32(bytes){
if (!crcTable){
crcTable=new Uint32Array(256);
for (let n=0;n<256;n++){
let c=n;
for (let k=0;k<8;k++) c=(c&1)?(0xedb88320^(c>>>1)):(c>>>1);
crcTable[n]=c>>>0;
}
}
let crc=0xffffffff;
for (const byte of bytes) crc=crcTable[(crc^byte)&0xff]^(crc>>>8);
return (crc^0xffffffff)>>>0;
}
async function inflateRaw(bytes,expectedSize){
if (typeof DecompressionStream!=='function') fail('CARTRIDGE_DEFLATE_UNAVAILABLE','This browser cannot open ZIP files.');
let stream;
try{stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate-raw'));}
catch (error){fail('CARTRIDGE_DEFLATE_UNAVAILABLE',error.message);}
const reader=stream.getReader(),chunks=[];
let total=0;
try{
while (true){
const{done,value}=await reader.read();
if (done) break;
total+=value.byteLength;
if (total>expectedSize||total>MAX_FILE_BYTES){
await reader.cancel();
fail('CARTRIDGE_ZIP_SIZE_MISMATCH','Expanded data exceeds its declared size.');
}
chunks.push(value);
}
}catch (error){
if (error?.code) throw error;
fail('CARTRIDGE_ZIP_DAMAGED',error.message);
}
const output=new Uint8Array(total);
let offset=0;
for (const chunk of chunks){output.set(chunk,offset);offset+=chunk.byteLength;}
return output;
}
function findZipEnd(view){
const first=Math.max(0,view.byteLength-22-0xffff);
for (let offset=view.byteLength-22;offset>=first;offset--) if (view.getUint32(offset,true)===ZIP_END) return offset;
fail('CARTRIDGE_ZIP_INVALID','End record not found.');
}
export async function openCartridgeZip(source){
const bytes=await sourceBytes(source);
if (bytes.byteLength<22) fail('CARTRIDGE_ZIP_INVALID','The file is too small.');
const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength);
const end=findZipEnd(view);
const disk=view.getUint16(end+4,true),centralDisk=view.getUint16(end+6,true);
const diskEntries=view.getUint16(end+8,true),count=view.getUint16(end+10,true);
const centralBytes=view.getUint32(end+12,true),centralOffset=view.getUint32(end+16,true);
if (disk||centralDisk||diskEntries!==count) fail('CARTRIDGE_ZIP_SPLIT');
if (count===0xffff||centralBytes===0xffffffff||centralOffset===0xffffffff) fail('CARTRIDGE_ZIP64_UNSUPPORTED');
if (!count||count>MAX_ENTRIES) fail('CARTRIDGE_ZIP_ENTRY_COUNT',String(count));
if (centralOffset+centralBytes>end) fail('CARTRIDGE_ZIP_INVALID','Central directory bounds.');
const entries=new Map();
let offset=centralOffset,declaredTotal=0;
for (let index=0;index<count;index++){
if (offset+46>bytes.byteLength||view.getUint32(offset,true)!==ZIP_CENTRAL) fail('CARTRIDGE_ZIP_INVALID',`Central entry ${index}.`);
const madeBy=view.getUint16(offset+4,true)>>>8;
const flags=view.getUint16(offset+8,true),method=view.getUint16(offset+10,true);
const checksum=view.getUint32(offset+16,true),compressedSize=view.getUint32(offset+20,true),size=view.getUint32(offset+24,true);
const nameLength=view.getUint16(offset+28,true),extraLength=view.getUint16(offset+30,true),commentLength=view.getUint16(offset+32,true);
const external=view.getUint32(offset+38,true),localOffset=view.getUint32(offset+42,true);
const next=offset+46+nameLength+extraLength+commentLength;
if (next>bytes.byteLength) fail('CARTRIDGE_ZIP_INVALID',`Entry ${index} bounds.`);
let rawName;
try{rawName=textDecoder.decode(bytes.subarray(offset+46,offset+46+nameLength));}
catch{fail('CARTRIDGE_FILENAME_ENCODING',`Entry ${index}.`);}
offset=next;
if (rawName.endsWith('/')) continue;
if (flags&1) fail('CARTRIDGE_ZIP_ENCRYPTED',rawName);
if (method!==0&&method!==8) fail('CARTRIDGE_ZIP_METHOD',`${rawName} uses method ${method}.`);
if (madeBy===3&&(((external>>>16)&0xf000)===0xa000)) fail('CARTRIDGE_ZIP_SYMLINK',rawName);
if (compressedSize===0xffffffff||size===0xffffffff||localOffset===0xffffffff) fail('CARTRIDGE_ZIP64_UNSUPPORTED');
if (size>MAX_FILE_BYTES) fail('CARTRIDGE_FILE_TOO_LARGE',rawName);
declaredTotal+=size;
if (declaredTotal>MAX_TOTAL_BYTES) fail('CARTRIDGE_ZIP_TOO_LARGE');
const name=normalizeZipPath(rawName);
if (entries.has(name)) fail('CARTRIDGE_DUPLICATE_PATH',name);
entries.set(name,{name,method,flags,checksum,compressedSize,size,localOffset,bytes:null});
}
if (offset!==centralOffset+centralBytes) fail('CARTRIDGE_ZIP_INVALID','Central directory length.');
async function read(name){
const entry=entries.get(name);
if (!entry) fail('CARTRIDGE_FILE_MISSING',name);
if (entry.bytes) return entry.bytes;
const at=entry.localOffset;
if (at+30>bytes.byteLength||view.getUint32(at,true)!==ZIP_LOCAL) fail('CARTRIDGE_ZIP_INVALID',`Local entry ${name}.`);
const localName=view.getUint16(at+26,true),localExtra=view.getUint16(at+28,true);
const start=at+30+localName+localExtra,finish=start+entry.compressedSize;
if (finish>bytes.byteLength) fail('CARTRIDGE_ZIP_INVALID',`Compressed data ${name}.`);
const compressed=bytes.subarray(start,finish);
const output=entry.method===0?new Uint8Array(compressed):await inflateRaw(compressed,entry.size);
if (output.byteLength!==entry.size) fail('CARTRIDGE_ZIP_SIZE_MISMATCH',name);
if (crc32(output)!==entry.checksum) fail('CARTRIDGE_ZIP_CRC_MISMATCH',name);
entry.bytes=output;
return output;
}
return{entries,read,compressedBytes:bytes.byteLength,uncompressedBytes:declaredTotal};
}
function assetRecords(value,output=[]){
if (Array.isArray(value)) for (const item of value) assetRecords(item,output);
else if (value&&typeof value==='object'){
if (typeof value.path==='string') output.push(value);
else for (const item of Object.values(value)) assetRecords(item,output);
}
return output;
}
async function sha256(bytes){
if (!globalThis.crypto?.subtle) fail('CARTRIDGE_HASH_UNAVAILABLE','Open the console over HTTPS.');
const digest=new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',bytes));
return[...digest].map((byte)=>byte.toString(16).padStart(2,'0')).join('');
}
function mime(path){
const extension=path.slice(path.lastIndexOf('.')+1).toLowerCase();
return ({json:'application/json',webp:'image/webp',png:'image/png',jpg:'image/jpeg',jpeg:'image/jpeg',wav:'audio/wav',mp3:'audio/mpeg',m4a:'audio/mp4',ogg:'audio/ogg'})[extension]||'application/octet-stream';
}
export async function inspectCartridgeZip(source,{validateManifest=(value)=>value}={}){
const zip=await openCartridgeZip(source);
const manifests=[...zip.entries.keys()].filter((name)=>/(^|\/)episode\.json$/.test(name));
if (manifests.length!==1) fail('CARTRIDGE_MANIFEST_COUNT',`Found ${manifests.length}; expected 1.`);
const manifestEntry=manifests[0],root=manifestEntry.slice(0,-'episode.json'.length);
let manifest;
try{manifest=validateManifest(JSON.parse(textDecoder.decode(await zip.read(manifestEntry))));}
catch (error){
if (error?.code||String(error?.message).startsWith('EPISODE_PACK_INVALID')) throw error;
fail('CARTRIDGE_MANIFEST_INVALID',error.message);
}
if (manifest.id==='dev-00') fail('CARTRIDGE_ID_RESERVED','DEV-00 belongs to the Console internal ROM.');
const files=new Map([['episode.json',await zip.read(manifestEntry)]]);
const records=assetRecords(manifest.assets);
for (const record of records){
const relative=normalizeAssetPath(record.path);
const bytes=await zip.read(root+relative);
if (record.sha256&&await sha256(bytes)!==record.sha256) fail('CARTRIDGE_ASSET_HASH_MISMATCH',relative);
files.set(relative,bytes);
}
return{
manifest,files,assetCount:records.length,
compressedBytes:zip.compressedBytes,
installedBytes:[...files.values()].reduce((sum,value)=>sum+value.byteLength,0),
};
}
function scopeUrl(base='./'){
const page=globalThis.location?.href||'https://struthio.invalid/';
return new URL(base||'./',page);
}
function generationId(){
const random=globalThis.crypto?.getRandomValues?[...globalThis.crypto.getRandomValues(new Uint8Array(8))].map((b)=>b.toString(16).padStart(2,'0')).join(''):Math.random().toString(16).slice(2,18);
return `g${Date.now().toString(36)}-${random}`;
}
function relativePackPath(manifest,generation=generationId()){
return `${PACK_ROOT}${encodeURIComponent(manifest.id)}/${encodeURIComponent(manifest.buildId)}/${generation}/`;
}
function isQuotaError(error){
return error?.name==='QuotaExceededError'||error?.code===22||/quota/i.test(String(error?.message||''));
}
async function cacheFor(cachesApi){
if (!cachesApi||typeof cachesApi.open!=='function') fail('CARTRIDGE_STORAGE_UNAVAILABLE');
return cachesApi.open(CARTRIDGE_CACHE);
}
export async function readInstalledEpisode(base='./',{cachesApi=globalThis.caches}={}){
if (!cachesApi||typeof cachesApi.open!=='function') return null;
const scope=scopeUrl(base),cache=await cacheFor(cachesApi);
const markerResponse=await cache.match(new URL(CARTRIDGE_MARKER,scope).href);
if (!markerResponse) return null;
let marker;
try{marker=await markerResponse.json();}
catch{fail('CARTRIDGE_INSTALL_INCOMPLETE','Active slot metadata is damaged.');}
if (marker?.schema!==1||typeof marker.manifestPath!=='string'||!marker.manifestPath.startsWith('__struthio_cartridges__/')) fail('CARTRIDGE_INSTALL_INCOMPLETE','Active slot metadata is invalid.');
const manifestResponse=await cache.match(new URL(marker.manifestPath,scope).href);
if (!manifestResponse) fail('CARTRIDGE_INSTALL_INCOMPLETE','episode.json is missing.');
let manifest;
try{manifest=await manifestResponse.json();}
catch{fail('CARTRIDGE_INSTALL_INCOMPLETE','episode.json is damaged.');}
const packPrefix=marker.manifestPath.slice(0,-'episode.json'.length);
for (const record of assetRecords(manifest?.assets)){
let relative;
try{relative=normalizeAssetPath(record.path);}catch{fail('CARTRIDGE_INSTALL_INCOMPLETE','An asset path is invalid.');}
if (!await cache.match(new URL(packPrefix+relative,scope).href)) fail('CARTRIDGE_INSTALL_INCOMPLETE',`${relative} is missing.`);
}
return{marker,manifest,manifestPath:marker.manifestPath};
}
export async function collectOrphanGenerations(base='./',{cachesApi=globalThis.caches}={}){
if (!cachesApi||typeof cachesApi.open!=='function') return 0;
const scope=scopeUrl(base),cache=await cacheFor(cachesApi);
const markerUrl=new URL(CARTRIDGE_MARKER,scope).href;
const markerResponse=await cache.match(markerUrl);
let keepPrefix=null;
if (markerResponse){
let marker;
try{marker=await markerResponse.json();}catch{return 0;}
const packPath=typeof marker?.packPath==='string'?marker.packPath:typeof marker?.manifestPath==='string'?marker.manifestPath.slice(0,-'episode.json'.length):null;
if (!packPath||!packPath.startsWith(PACK_ROOT)) return 0;
keepPrefix=new URL(packPath,scope).href;
}
const rootPrefix=new URL(PACK_ROOT,scope).href;
let removed=0;
for (const request of await cache.keys()){
if (request.url===markerUrl||!request.url.startsWith(rootPrefix)) continue;
if (keepPrefix&&request.url.startsWith(keepPrefix)) continue;
await cache.delete(request);removed+=1;
}
return removed;
}
export async function storagePreflight(neededBytes,{storage=globalThis.navigator?.storage}={}){
if (!storage?.estimate) return{ok:true,advisory:'ESTIMATE_UNAVAILABLE'};
try{
const{quota=0,usage=0}=await storage.estimate();
const free=Math.max(0,quota-usage);
return{ok:!quota||free>=neededBytes,quota,usage,free,neededBytes};
}catch{return{ok:true,advisory:'ESTIMATE_FAILED'};}
}
export async function slotDiagnostics(base='./',{cachesApi=globalThis.caches,storage=globalThis.navigator?.storage}={}){
const out={installedBytes:null,generations:0,quota:null,usage:null};
try{
if (cachesApi?.open){
const scope=scopeUrl(base),cache=await cacheFor(cachesApi);
const markerResponse=await cache.match(new URL(CARTRIDGE_MARKER,scope).href);
if (markerResponse){try{out.installedBytes=(await markerResponse.json()).installedBytes??null;}catch{}}
const gens=new Set();
for (const request of await cache.keys()){const m=request.url.match(/__struthio_cartridges__\/[^/]+\/[^/]+\/([^/]+)\//);if (m) gens.add(m[0]);}
out.generations=gens.size;
}
if (storage?.estimate){const e=await storage.estimate();out.quota=e.quota??null;out.usage=e.usage??null;}
}catch{}
return out;
}
export async function installCartridgeZip(source,{base='./',validateManifest,cachesApi=globalThis.caches,storage=globalThis.navigator?.storage,faults=null}={}){
const inspected=await inspectCartridgeZip(source,{validateManifest});
const scope=scopeUrl(base),cache=await cacheFor(cachesApi);
await collectOrphanGenerations(base,{cachesApi});
const preflight=await storagePreflight(Math.ceil(inspected.installedBytes*1.1),{storage});
if (!preflight.ok) fail('CARTRIDGE_STORAGE_LOW',`needs ${inspected.installedBytes} bytes; about ${preflight.free} free`);
const packPath=relativePackPath(inspected.manifest);
const stagedPrefix=new URL(packPath,scope).href;
const discardStaged=async ()=>{
for (const request of await cache.keys()) if (request.url.startsWith(stagedPrefix)){try{await cache.delete(request);}catch{}}
};
try{
let written=0;
for (const[relative,bytes] of inspected.files){
if (faults?.failAfterWrites!==undefined&&written>=faults.failAfterWrites) throw new DOMException('Simulated quota exhaustion','QuotaExceededError');
await cache.put(new URL(packPath+relative,scope).href,new Response(bytes,{headers:{'content-type':mime(relative),'cache-control':'private, max-age=31536000, immutable'}}));
written+=1;
}
for (const[relative,bytes] of inspected.files){
const response=await cache.match(new URL(packPath+relative,scope).href);
if (!response) fail('CARTRIDGE_STAGE_VERIFY',`${relative} missing after write`);
const stored=new Uint8Array(await response.arrayBuffer());
if (stored.byteLength!==bytes.byteLength||await sha256(stored)!==await sha256(bytes)) fail('CARTRIDGE_STAGE_VERIFY',relative);
}
if (faults?.crashBeforeCommit) return{crashed:true,packPath};
}catch (error){
await discardStaged();
if (isQuotaError(error)) fail('CARTRIDGE_STORAGE_FULL','Storage filled while staging; the previous cartridge is untouched.');
throw error;
}
const marker={
schema:1,
id:inspected.manifest.id,
title:inspected.manifest.title,
buildId:inspected.manifest.buildId,
manifestPath:packPath+'episode.json',
packPath,
installedAt:new Date().toISOString(),
installedBytes:inspected.installedBytes,
};
try{
await cache.put(new URL(CARTRIDGE_MARKER,scope).href,new Response(JSON.stringify(marker),{headers:{'content-type':'application/json','cache-control':'no-store'}}));
}catch (error){
await discardStaged();
if (isQuotaError(error)) fail('CARTRIDGE_STORAGE_FULL','Storage filled at commit; the previous cartridge is untouched.');
throw error;
}
await collectOrphanGenerations(base,{cachesApi});
try{await storage?.persist?.();}catch{}
return{...marker,assetCount:inspected.assetCount,compressedBytes:inspected.compressedBytes};
}
export async function removeInstalledCartridge(base='./',{cachesApi=globalThis.caches}={}){
if (!cachesApi||typeof cachesApi.open!=='function') return false;
const scope=scopeUrl(base),cache=await cacheFor(cachesApi),markerUrl=new URL(CARTRIDGE_MARKER,scope).href;
await cache.delete(markerUrl);
const rootPrefix=new URL(PACK_ROOT,scope).href;
for (const request of await cache.keys()) if (request.url.startsWith(rootPrefix)) await cache.delete(request);
return true;
}
function waitForWorker(worker,wanted,timeoutMs=15000){
if (!worker||wanted.has(worker.state)) return Promise.resolve();
return new Promise((resolve,reject)=>{
const timer=setTimeout(()=>{cleanup();reject(new Error('CARTRIDGE_SERVICE_WORKER_TIMEOUT'));},timeoutMs);
const change=()=>{if (wanted.has(worker.state)){cleanup();resolve();}else if (worker.state==='redundant'){cleanup();reject(new Error('CARTRIDGE_SERVICE_WORKER_REJECTED'));}};
const cleanup=()=>{clearTimeout(timer);worker.removeEventListener('statechange',change);};
worker.addEventListener('statechange',change);
});
}
export async function ensureCartridgeRouting(base='./'){
if (!globalThis.navigator?.serviceWorker) fail('CARTRIDGE_SERVICE_WORKER_UNAVAILABLE','Install over HTTPS in Safari, Chrome, or Edge.');
const registration=await navigator.serviceWorker.register(base+'sw.js',{scope:base});
try{await registration.update();}catch{}
if (registration.installing) await waitForWorker(registration.installing,new Set(['installed','activated']));
if (registration.waiting){
const waiting=registration.waiting;
waiting.postMessage({type:'SKIP_WAITING'});
await waitForWorker(waiting,new Set(['activated']));
}
await navigator.serviceWorker.ready;
return registration;
}
function friendly(error){
const message=String(error?.message||error||'CARTRIDGE_INSTALL_FAILED');
const code=(message.match(/(?:CARTRIDGE_[A-Z0-9_]+|EPISODE_PACK_INVALID)/)||[])[0]||'';
let explanation='The Console could not read this cartridge. Try the original ZIP again.';
if (/MANIFEST_COUNT|MANIFEST_INVALID|EPISODE_PACK_INVALID/.test(message)) explanation='This ZIP does not contain one valid STRUTHIO episode. Choose the finished cartridge ZIP, not an engineering folder.';
else if (/FILE_MISSING/.test(message)) explanation='A required game file is missing from this cartridge. Download the complete cartridge ZIP again.';
else if (/HASH_MISMATCH|CRC_MISMATCH|SIZE_MISMATCH|ZIP_INVALID/.test(message)) explanation='This cartridge appears damaged or incomplete. Download a fresh copy and try again.';
else if (/TOO_LARGE|ZIP64/.test(message)) explanation='This cartridge is too large for the Console slot. Use the compact player cartridge package.';
else if (/STORAGE_FULL|STORAGE_LOW/.test(message)) explanation='There is not enough free storage for this cartridge. Nothing was changed; free some space and try again.';
else if (/STAGE_VERIFY/.test(message)) explanation='The cartridge did not save correctly. Nothing was changed; try again.';
else if (/STORAGE_UNAVAILABLE/.test(message)) explanation='This browser will not let the Console save a cartridge. Check private-browsing and storage settings.';
else if (/ID_RESERVED/.test(message)) explanation='DEV-00 is already built into the Console. Choose a retail cartridge with its own episode ID.';
else if (/SERVICE_WORKER|secure|HTTPS|HASH_UNAVAILABLE/i.test(message)) explanation='The cartridge slot needs the secure published Console link. Open it over HTTPS, then try again.';
return code?`${explanation}\n${code}`:explanation;
}
export function setupCartridgeManager({base='./',loaded,validateManifest}={}){
if (typeof document==='undefined') return null;
const panel=document.getElementById('cartridge-panel');
if (!panel) return null;
const file=document.getElementById('cartridge-file');
const install=document.getElementById('cartridge-install');
const rom=document.getElementById('cartridge-play-rom');
const remove=document.getElementById('cartridge-remove');
const close=document.getElementById('cartridge-close');
const factory=document.getElementById('factory-open');
const status=document.getElementById('cartridge-status');
const current=document.getElementById('cartridge-current');
const card=document.getElementById('cartridge-card');
const heading=document.getElementById('cartridge-heading');
const label=document.getElementById('slot-label-title');
const openers=['cartridge-open'].map((id)=>document.getElementById(id)).filter(Boolean);
const directInsert=document.getElementById('empty-cartridge-open');
const romOpeners=[document.getElementById('empty-rom-open')].filter(Boolean);
const factoryOpeners=[factory,document.getElementById('factory-open-empty')].filter(Boolean);
let busy=false,releaseModal=null;
const playingInternal=loaded?.source==='internal';
const slot=loaded?.slot||null;
const local=slot?.source==='installed';
const hasCartridge=!!slot;
const description=hasCartridge
?`${slot.title}\n${local?'Saved in Slot A on this device.':'Mounted in Slot A by this release.'}${playingInternal?'\nDEV-00 is running; Slot A is unchanged.':''}`
:`Slot A is empty.${loaded?.internalAvailable?'\nDEV-00 remains ready in internal memory.':''}`;
const damaged=loaded?.damagedSlot||null;
if (current) current.textContent=damaged
?`Slot A is damaged and was skipped (${damaged.code}).\nEject it to clear the slot; DEV-00 and your saves are unaffected.`
:description;
if (remove) remove.hidden=!(local||damaged);
if (heading) heading.textContent=hasCartridge?'CARTRIDGE READY':'INSERT A CARTRIDGE';
if (label) label.textContent=hasCartridge?slot.title:'SLOT A · EMPTY';
if (install) install.textContent=hasCartridge?'INSERT A DIFFERENT CARTRIDGE':'CHOOSE CARTRIDGE ZIP';
if (close) close.textContent=loaded?.episode?'BACK TO GAME':'BACK TO CONSOLE';
if (rom) rom.textContent=playingInternal?(hasCartridge?'PLAY SLOT A CARTRIDGE':'RETURN TO EMPTY CONSOLE'):'PLAY BUILT-IN DEV-00';
if (rom) rom.hidden=true;
if (factory) factory.hidden=true;
if (card) card.dataset.state=damaged?'error':hasCartridge?'loaded':'empty';
if (damaged&&heading) heading.textContent='SLOT A NEEDS EJECT';
if (damaged&&remove){remove.textContent='EJECT DAMAGED CARTRIDGE';if (install) install.before(remove);}
const diagnostics={damaged,orphansRemoved:null,slot:null};
if (!damaged) collectOrphanGenerations(base).then((n)=>{diagnostics.orphansRemoved=n;}).catch(()=>{});
slotDiagnostics(base).then((d)=>{
diagnostics.slot=d;
if (status&&!status.textContent&&d.installedBytes) status.textContent=`SLOT A USES ${(d.installedBytes/1048576).toFixed(1)} MB`;
}).catch(()=>{});
function setState(value,title,labelText){
if (card) card.dataset.state=value;
if (heading&&title) heading.textContent=title;
if (label&&labelText) label.textContent=labelText;
}
function setBusy(value){
busy=value;
for (const button of[install,rom,factory,remove,close]) if (button) button.disabled=value;
panel.setAttribute('aria-busy',String(value));
}
function openPanel(initialStatus=''){
if (status) status.textContent=initialStatus;
panel.hidden=false;
document.body.classList.add('cartridge-open');
if (!releaseModal) releaseModal=openModal(panel,{onEscape:closePanel,initialFocus:(loaded?.damagedSlot&&remove)||install||close});
}
function closePanel(){
if (busy) return;
panel.hidden=true;
document.body.classList.remove('cartridge-open');
if (releaseModal){const release=releaseModal;releaseModal=null;release();}
}
for (const opener of openers) opener.addEventListener('click',()=>openPanel());
function openCartridgeMenu(){
const next=new URL(location.href);
next.searchParams.delete('rom');next.searchParams.delete('episode');
next.searchParams.set('menu','cartridge');
location.href=next.href;
}
async function ejectToHome(){
try{await removeInstalledCartridge(base);}catch{}
const next=new URL(location.href);
for (const key of['rom','episode','menu']) next.searchParams.delete(key);
location.href=next.href;
}
function setInternalRom(enabled){
const next=new URL(location.href);
if (enabled) next.searchParams.set('rom','dev-00');
else next.searchParams.delete('rom');
next.searchParams.delete('episode');
location.href=next.href;
}
for (const opener of romOpeners) opener.addEventListener('click',()=>setInternalRom(true));
rom?.addEventListener('click',()=>setInternalRom(!playingInternal));
for (const opener of factoryOpeners) opener.addEventListener('click',()=>{
location.href=new URL('factory/',new URL(base,location.href)).href;
});
close?.addEventListener('click',closePanel);
panel.addEventListener('click',(event)=>{if (event.target===panel) closePanel();});
function pickCartridge(){
if (!file||busy) return;
file.value='';
file.click();
}
install?.addEventListener('click',pickCartridge);
directInsert?.addEventListener('click',pickCartridge);
file?.addEventListener('change',async ()=>{
const selected=file.files?.[0];
if (!selected) return;
if (panel.hidden) openPanel();
setBusy(true);
setState('reading','READING CARTRIDGE','CHECKING THE WORLD');
if (current) current.textContent='Keep this screen open while the Console checks every game file.';
if (status) status.textContent=`READING ${selected.name}…`;
try{
await ensureCartridgeRouting(base);
const result=await installCartridgeZip(selected,{base,validateManifest});
setState('ready','CARTRIDGE LOCKED',result.title);
if (current) current.textContent=`${result.title} is safely loaded in Slot A.`;
if (status) status.textContent='CLICK! WORLD READY · STARTING…';
setTimeout(()=>openCartridgeMenu(),760);
}catch (error){
setState('error','TRY ANOTHER CARTRIDGE','CARTRIDGE NOT READ');
if (status) status.textContent=friendly(error);
if (current) current.textContent='Nothing was changed. Your previous cartridge, if any, is still safe.';
setBusy(false);
}
});
remove?.addEventListener('click',async ()=>{
if (busy) return;
setBusy(true);
setState('reading','EJECTING CARTRIDGE','RELEASING SLOT A');
if (status) status.textContent='SAVING THE SLOT · PLEASE WAIT…';
try{
await removeInstalledCartridge(base);
setState('empty','CARTRIDGE EJECTED','SLOT A · EMPTY');
if (status) status.textContent='SAFE TO LOAD ANOTHER WORLD · RESTARTING…';
setTimeout(()=>location.reload(),650);
}catch (error){
setState('error','CARTRIDGE STILL LOADED',slot?.title||'SLOT A');
if (status) status.textContent=friendly(error);
setBusy(false);
}
});
const handoff=new URL(location.href);
if (handoff.searchParams.get('cartridge')==='install'){
handoff.searchParams.delete('cartridge');
handoff.searchParams.delete('from');
history.replaceState(history.state,'',handoff.href);
setTimeout(()=>openPanel('CHOOSE THE FINISHED CARTRIDGE ZIP FROM FILES.'),0);
}
if (damaged) setTimeout(()=>openPanel('SLOT A WAS DAMAGED AND SKIPPED. EJECT IT, OR INSERT A CARTRIDGE TO REPLACE IT.'),0);
return{open:openPanel,close:closePanel,diagnostics,pick:pickCartridge,eject:ejectToHome};
}
