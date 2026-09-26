import{readInstalledEpisode}from './cartridge-installer.mjs';
import{resolveSemanticPalette}from './palette-bridge.mjs';
export const EPISODE_API_VERSION=1;
const REQUIRED_ASSETS=Object.freeze([
'islands','cinemaPanels','theaterReel','startScreen','manual',
]);
const OPTIONAL_ASSETS=Object.freeze([
'authority','bird','rider','riderMap','icon192','icon512',
'appleTouchIcon','shareCard','audio',
]);
const fail=(message)=>{throw new Error(`EPISODE_PACK_INVALID: ${message}`);};
const record=(value)=>value&&typeof value==='object'&&!Array.isArray(value);
const string=(value,label)=>{
if (typeof value!=='string'||value.length===0) fail(`${label} must be a non-empty string`);
return value;
};
function assetRecord(value,label){
if (!record(value)) fail(`${label} must be an object`);
string(value.path,`${label}.path`);
if (value.sha256!==undefined&&!/^[0-9a-f]{64}$/.test(value.sha256)) fail(`${label}.sha256`);
if (value.width!==undefined&&(!Number.isInteger(value.width)||value.width<1)) fail(`${label}.width`);
if (value.height!==undefined&&(!Number.isInteger(value.height)||value.height<1)) fail(`${label}.height`);
}
export function validateEpisodePack(pack){
if (!record(pack)) fail('root must be an object');
if (pack.apiVersion!==EPISODE_API_VERSION) fail(`apiVersion ${pack.apiVersion}; expected ${EPISODE_API_VERSION}`);
if (!/^[a-z0-9][a-z0-9-]{1,31}$/.test(string(pack.id,'id'))) fail('id format');
string(pack.title,'title');
string(pack.buildId,'buildId');
if (!/^struthio\.console\.[a-z0-9.-]+\.v\d+$/.test(string(pack.saveNamespace,'saveNamespace'))) fail('saveNamespace format');
if (!record(pack.assets)) fail('assets');
for (const name of REQUIRED_ASSETS) assetRecord(pack.assets[name],`assets.${name}`);
for (const name of OPTIONAL_ASSETS) if (pack.assets[name]!==null&&pack.assets[name]!==undefined) assetRecord(pack.assets[name],`assets.${name}`);
if (!Array.isArray(pack.assets.backgrounds)||pack.assets.backgrounds.length!==6) fail('assets.backgrounds must contain six pairs');
pack.assets.backgrounds.forEach((pair,index)=>{
if (!record(pair)) fail(`assets.backgrounds[${index}]`);
assetRecord(pair.rear,`assets.backgrounds[${index}].rear`);
assetRecord(pair.near,`assets.backgrounds[${index}].near`);
});
if (!record(pack.assets.islands.metadata)||!Array.isArray(pack.assets.islands.metadata.masters)) fail('island master metadata');
const roles=pack.assets.islands.metadata.masters.map((master,index)=>{
if (!record(master)) fail(`island master ${index}`);
for (const key of['id','role']) string(master[key],`island master ${index}.${key}`);
for (const key of['x','y','w','h','capTop']) if (!Number.isInteger(master[key])||master[key]<0) fail(`island master ${index}.${key}`);
if (!Array.isArray(master.signalRects)) fail(`island master ${index}.signalRects`);
return master.role;
});
if (roles.filter((role)=>role==='STANDARD').length!==9) fail('nine STANDARD island masters required');
if (roles.filter((role)=>role==='BOSS').length!==5) fail('five BOSS island masters required');
if (roles.filter((role)=>role==='GROUND').length!==1) fail('one GROUND island master required');
if (!record(pack.presentation)||!record(pack.presentation.palette)||!record(pack.presentation.ui)) fail('presentation palette/ui');
resolveSemanticPalette(pack.presentation);
return pack;
}
export function episodePaletteReport(pack){
return resolveSemanticPalette(record(pack)&&record(pack.presentation)?pack.presentation:{});
}
function dirname(path){
const clean=path.split('#')[0].split('?')[0];
const slash=clean.lastIndexOf('/');
return slash<0?'':clean.slice(0,slash+1);
}
function join(prefix,path){
if (/^(?:[a-z]+:|\/)/i.test(path)) fail(`asset path must be cartridge-relative: ${path}`);
const parts=(prefix+path).split('/');
const out=[];
for (const part of parts){
if (!part||part==='.') continue;
if (part==='..') fail(`asset path escapes cartridge: ${path}`);
else out.push(part);
}
return out.join('/');
}
function resolveAssetTree(value,prefix){
if (Array.isArray(value)) return value.map((item)=>resolveAssetTree(item,prefix));
if (!record(value)) return value;
const out={};
for (const[key,item] of Object.entries(value)) out[key]=resolveAssetTree(item,prefix);
if (typeof out.path==='string') out.url=join(prefix,out.path);
return out;
}
async function readJson(base,path){
const response=await fetch(base+path,{cache:'no-cache'});
if (!response.ok) throw new Error(`FETCH ${path} ${response.status}`);
return response.json();
}
export async function loadConfiguredEpisode(base='./',{configPath='console.json',forceEmpty=false,useInternalRom=false}={}){
const config=await readJson(base,configPath);
if (!record(config)||config.consoleApiVersion!==EPISODE_API_VERSION) fail('console.json api version');
string(config.consoleBuildId,'consoleBuildId');
if (config.activeEpisode!==null&&config.activeEpisode!==undefined) string(config.activeEpisode,'activeEpisode');
if (config.internalRom!==null&&config.internalRom!==undefined) string(config.internalRom,'internalRom');
let damagedSlot=null;
let installedCandidate=null;
if (!forceEmpty){
try{
installedCandidate=await readInstalledEpisode(base);
if (installedCandidate&&installedCandidate.manifest?.id!=='dev-00') validateEpisodePack(installedCandidate.manifest);
}catch (error){
damagedSlot={code:error?.code||(String(error?.message).match(/[A-Z_]{8,}/)||['CARTRIDGE_INSTALL_INCOMPLETE'])[0],detail:String(error?.message||error)};
installedCandidate=null;
}
}
const retiredDevelopmentCartridge=installedCandidate?.manifest?.id==='dev-00';
const installed=retiredDevelopmentCartridge?null:installedCandidate;
const slotManifestPath=forceEmpty?null:(installed?.manifestPath??config.activeEpisode??null);
const slotSource=installed?'installed':slotManifestPath?'deployed':null;
let slotRaw=null;
if (slotManifestPath) slotRaw=validateEpisodePack(installed?installed.manifest:await readJson(base,slotManifestPath));
const slot=slotRaw?{
source:slotSource,
manifestPath:slotManifestPath,
id:slotRaw.id,
title:slotRaw.title,
buildId:slotRaw.buildId,
}:null;
if (forceEmpty) return{config,episode:null,manifestPath:null,source:'empty',slot:null,internalAvailable:!!config.internalRom,damagedSlot};
if (useInternalRom){
if (!config.internalRom) fail('internalRom is not configured');
const manifestPath=config.internalRom;
const raw=validateEpisodePack(await readJson(base,manifestPath));
if (raw.id!=='dev-00') fail('internalRom must identify dev-00');
const episode={...raw,assets:resolveAssetTree(raw.assets,dirname(manifestPath))};
return{config,episode,manifestPath,source:'internal',slot,internalAvailable:true,damagedSlot};
}
if (!slotManifestPath) return{config,episode:null,manifestPath:null,source:'empty',slot:null,internalAvailable:!!config.internalRom,damagedSlot};
const manifestPath=slotManifestPath;
const raw=slotRaw;
const episode={...raw,assets:resolveAssetTree(raw.assets,dirname(manifestPath))};
return{config,episode,manifestPath,source:slotSource,slot,internalAvailable:!!config.internalRom,damagedSlot};
}
