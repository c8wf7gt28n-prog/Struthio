import{loadConfiguredEpisode,validateEpisodePack}from './console/episode-loader.mjs';
import{ensureCartridgeRouting,setupCartridgeManager}from './console/cartridge-installer.mjs';
import{selectSpriteProfile}from './console/sprite-profiles.mjs';
import{openModal}from './console/modal.mjs';
import{resolveSemanticPalette,resetCartridgePalette,applySemanticPalette}from './console/palette-bridge.mjs';
import{installViewportShim}from './console/viewport-shim.mjs';
import{setupQrCart}from './console/qr-cart.mjs';
import{setupVs,relayUrlFor}from './console/vs-ui.mjs';
import{setupTcsCalibration}from './console/tcs-cal.mjs';
import{setupNetworkPanel}from './console/net-panel.mjs';
const __modules=[];
__modules[0]=(()=>{
const K=new Uint32Array([
0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
const UTF8=new TextEncoder();
function utf8(str){
return UTF8.encode(str);
}
function sha256Bytes(bytes){
const len=bytes.length;
const bitLen=len*8;
const padLen=((len+9+63)>>6)<<6;
const buf=new Uint8Array(padLen);
buf.set(bytes);
buf[len]=0x80;
const dv=new DataView(buf.buffer);
dv.setUint32(padLen-8,Math.floor(bitLen/0x100000000),false);
dv.setUint32(padLen-4,bitLen>>>0,false);
let h0=0x6a09e667,h1=0xbb67ae85,h2=0x3c6ef372,h3=0xa54ff53a,h4=0x510e527f,h5=0x9b05688c,h6=0x1f83d9ab,h7=0x5be0cd19;
const w=new Uint32Array(64);
for (let off=0;off<padLen;off+=64){
for (let i=0,j=off;i<16;i++,j+=4) w[i]=((buf[j]<<24)|(buf[j+1]<<16)|(buf[j+2]<<8)|buf[j+3])>>>0;
for (let i=16;i<64;i++){
const a=w[i-15],b=w[i-2];
const s0=((a>>>7)|(a<<25))^((a>>>18)|(a<<14))^(a>>>3);
const s1=((b>>>17)|(b<<15))^((b>>>19)|(b<<13))^(b>>>10);
w[i]=(w[i-16]+s0+w[i-7]+s1)>>>0;
}
let a=h0,b=h1,c=h2,d=h3,e=h4,f=h5,g=h6,h=h7;
for (let i=0;i<64;i++){
const S1=((e>>>6)|(e<<26))^((e>>>11)|(e<<21))^((e>>>25)|(e<<7));
const ch=(e&f)^(~e&g);
const t1=(h+S1+ch+K[i]+w[i])>>>0;
const S0=((a>>>2)|(a<<30))^((a>>>13)|(a<<19))^((a>>>22)|(a<<10));
const maj=(a&b)^(a&c)^(b&c);
const t2=(S0+maj)>>>0;
h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;
}
h0=(h0+a)>>>0;h1=(h1+b)>>>0;h2=(h2+c)>>>0;h3=(h3+d)>>>0;h4=(h4+e)>>>0;h5=(h5+f)>>>0;h6=(h6+g)>>>0;h7=(h7+h)>>>0;
}
const out=new Uint8Array(32);
const ov=new DataView(out.buffer);
[h0,h1,h2,h3,h4,h5,h6,h7].forEach((v,i)=>ov.setUint32(i*4,v,false));
return out;
}
function toHex(bytes){
let s='';
for (const b of bytes) s+=(b<16?'0':'')+b.toString(16);
return s;
}
function sha256Hex(input){
const bytes=typeof input==='string'?utf8(input):input;
return toHex(sha256Bytes(bytes));
}
return{sha256Hex};
})();
__modules[1]=(()=>{
const{sha256Hex}=__modules[0];
const SURROGATE=/[\uD800-\uDFFF]/;
function sortKeys(keys){
if (!keys.some((k)=>SURROGATE.test(k))) return keys.slice().sort();
return keys.slice().sort((a,b)=>{
const ia=[...a],ib=[...b];
const n=Math.min(ia.length,ib.length);
for (let i=0;i<n;i++){
const ca=ia[i].codePointAt(0),cb=ib[i].codePointAt(0);
if (ca!==cb) return ca-cb;
}
return ia.length-ib.length;
});
}
function canonical(value){
if (value===null) return 'null';
if (value===true) return 'true';
if (value===false) return 'false';
const t=typeof value;
if (t==='number'){
if (!Number.isFinite(value)) throw new Error('CANONICAL_NONFINITE');
if (Object.is(value,-0)) throw new Error('CANONICAL_NEGATIVE_ZERO');
if (!Number.isSafeInteger(value)) throw new Error('CANONICAL_NONINTEGER');
return String(value);
}
if (t==='string') return JSON.stringify(value);
if (Array.isArray(value)) return '['+value.map(canonical).join(',')+']';
if (t==='object'){
const keys=sortKeys(Object.keys(value));
return '{'+keys.map((k)=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
}
throw new Error('CANONICAL_UNSUPPORTED_TYPE');
}
function digest(value){
return sha256Hex(canonical(value));
}
function checkpointChecksum(record){
const copy=structuredClone(record);
copy.checksum='0'.repeat(64);
return digest(copy);
}
return{digest,checkpointChecksum};
})();
__modules[2]=(()=>{
const{digest}=__modules[1];
const AUTHORITY_FILES=[
'sim_constants','lifecycle','input','bosses','campaign_levels','campaign.schema',
'arcade','cinema','audio','palette','font_5x7','story_strings','save_protocol',
'state.schema',
];
const PRESENTATION_FILES=new Set(['cinema','audio','palette','font_5x7','story_strings']);
const BUILD_ID='STRUTHIO-CONSOLE-3.5.4';
let ACTIVE_IDENTITY=Object.freeze({episodeId:'empty',buildId:BUILD_ID,saveNamespace:'struthio.console.empty.v1'});
function configureCartridge(manifest){
if (!manifest){ACTIVE_IDENTITY=Object.freeze({episodeId:'empty',buildId:BUILD_ID,saveNamespace:'struthio.console.empty.v1'});return ACTIVE_IDENTITY;}
ACTIVE_IDENTITY=Object.freeze({episodeId:manifest.id,buildId:manifest.buildId,saveNamespace:manifest.saveNamespace});
return ACTIVE_IDENTITY;
}
function getIdentity(){return ACTIVE_IDENTITY;}
function fail(msg){throw new Error(`AUTHORITY_INVALID: ${msg}`);}
function validateCampaign(levels,schema){
if (!Array.isArray(levels)||levels.length!==29) fail('campaign must contain 29 records');
levels.forEach((l,i)=>{
if (l.level!==i+1) fail(`level order ${l.level}`);
for (const k of schema.recordRequired) if (!(k in l)) fail(`L${l.level} missing ${k}`);
const req=l.kind==='BOSS'?schema.bossRequired:schema.normalRequired;
for (const k of req) if (!(k in l)) fail(`L${l.level} missing ${k}`);
const copy={...l};delete copy.contentHash;
if (digest(copy)!==l.contentHash) fail(`L${l.level} contentHash mismatch`);
if (l.kind==='BOSS'){if (![5,11,17,23,29].includes(l.level)||l.rings.length!==3) fail(`boss L${l.level}`);}
else{
if (l.rings.length!==6||l.enemySpawns.length!==6||l.platforms.length<7) fail(`normal L${l.level}`);
if (!Number.isInteger(l.openingPopulation)||l.openingPopulation<1||l.openingPopulation>l.maxMounted) fail(`L${l.level} openingPopulation`);
}
});
}
function validateAuthority(A){
validateCampaign(A.campaign_levels,A['campaign.schema']);
if (A.cinema.shots.length!==28) fail('cinema shots');
if (A.audio.voices.length!==8) fail('audio voices');
if (A.bosses.bosses.length!==5) fail('bosses');
if (A.arcade.routeBank.length!==8) fail('arcade routes');
const c=A.sim_constants;
if (c.tickHz!==60||c.subpixelsPerPixel!==256||c.logicalSize[0]!==256||c.logicalSize[1]!==384) fail('constants');
if (!Number.isInteger(c.openingStaggerTicks)||c.openingStaggerTicks<1||c.openingStaggerTicks>=c.waveIntroTicks) fail('openingStaggerTicks');
const buildConst=A['state.schema']?.properties?.buildId?.const;
const identity=getIdentity();
if (buildConst!==identity.buildId) fail(`state.schema buildId ${buildConst} is not ${identity.buildId}`);
if (A.save_protocol.namespace!==identity.saveNamespace) fail(`save_protocol namespace ${A.save_protocol.namespace} is not ${identity.saveNamespace}`);
if (A['state.schema']?.properties?.episodeId?.const!==identity.episodeId) fail('state.schema episodeId mismatch');
return true;
}
async function loadAuthority(readConsoleJson,readCartridgePresentationJson=null){
const loaded=await Promise.all(AUTHORITY_FILES.map(async (name)=>{
const consoleValue=await readConsoleJson(name);
if (!readCartridgePresentationJson||!PRESENTATION_FILES.has(name)) return consoleValue;
const cartridgeValue=await readCartridgePresentationJson(name);
return cartridgeValue===undefined||cartridgeValue===null?consoleValue:cartridgeValue;
}));
const A={};
AUTHORITY_FILES.forEach((name,i)=>{A[name]=loaded[i];});
const identity=getIdentity();
A.save_protocol={...A.save_protocol,namespace:identity.saveNamespace};
A['state.schema']=structuredClone(A['state.schema']);
A['state.schema'].properties.buildId.const=identity.buildId;
A['state.schema'].properties.episodeId.const=identity.episodeId;
validateAuthority(A);
deepFreeze(A);
return A;
}
function deepFreeze(o){
if (o&&typeof o==='object'&&!Object.isFrozen(o)){Object.freeze(o);for (const v of Object.values(o)) deepFreeze(v);}
return o;
}
return{loadAuthority,configureCartridge,getIdentity,BUILD_ID,AUTHORITY_FILES,PRESENTATION_FILES};
})();
__modules[3]=(()=>{
const ZERO_REMAP=0x6d2b79f5;
function seedState(seed){
const s=Number(seed)>>>0;
return s===0?ZERO_REMAP:s;
}
function nextU32(box){
let x=box.state>>>0;
if (x===0) x=ZERO_REMAP;
x^=x<<13;
x>>>=0;
x^=x>>>17;
x^=x<<5;
x>>>=0;
box.state=x;
return x;
}
return{seedState,nextU32};
})();
__modules[4]=(()=>{
const SUBPIXEL=256;
const WRAP=256*SUBPIXEL;
function assertInt(v,name='value'){
if (!Number.isSafeInteger(v)) throw new Error(`NON_INTEGER ${name}=${v}`);
return v;
}
function clamp(v,lo,hi){
assertInt(v);
return v<lo?lo:v>hi?hi:v;
}
function tdiv(a,b){
assertInt(a);assertInt(b);
const q=Math.trunc(a/b);
return q===0?0:q;
}
function mod(v,m){
assertInt(v);
const r=v%m;
return r<0?r+m:r;
}
function floorDiv(v,d){
assertInt(v);assertInt(d);
const q=Math.trunc(v/d);
const r=v%d;
const out=r!==0&&(r<0)!==(d<0)?q-1:q;
return out===0?0:out;
}
function px(logical){
return assertInt(logical)*SUBPIXEL;
}
function nearestWrapShift(dx){
assertInt(dx);
const c0=Math.abs(dx),cm=Math.abs(dx-WRAP),cp=Math.abs(dx+WRAP);
let best=0,bestAbs=c0;
if (cm<bestAbs){best=-WRAP;bestAbs=cm;}
if (cp<bestAbs){best=WRAP;bestAbs=cp;}
return best;
}
function wrappedDelta(from,to){
const dx=to-from;
return dx+nearestWrapShift(dx);
}
function compareRational(an,ad,bn,bd){
const l=an*bd,r=bn*ad;
if (!Number.isSafeInteger(l)||!Number.isSafeInteger(r)) throw new Error('RATIONAL_OVERFLOW');
return l===r?0:l<r?-1:1;
}
return{px,tdiv,mod,WRAP,wrappedDelta,clamp,compareRational,nearestWrapShift,floorDiv};
})();
__modules[5]=(()=>{
const{seedState}=__modules[3];
const{px}=__modules[4];
const BIRD_BOX={l:8,r:21,t:14,b:25};
const RIDER_BOX={l:11,r:17,t:15,b:25};
const EGG_BOX={l:11,r:18,t:17,b:25};
const LANCE_Y_SUB=(BIRD_BOX.t-5)*256;
const FLAP_COOLDOWN_TICKS=7;
const RESPAWN_HIDDEN_TICKS=84;
const SHIMMER_TICKS=90;
function emptyStory(){
return{version:2,seenMask:0,signalKnown:false,oldCircuitKnown:false,fractureKnown:false,warningKnown:false,circuitReleased:false,complete:false};
}
function emptyCinema(){
return{pending:0,filmId:'',shotIndex:0,shotTick:0,skipTicks:0,releaseLatched:false};
}
const BOSS_HITS_TO_DEFEAT=3;
const BOSS_HURT_TICKS=84;
function emptyBoss(){
return{milestone:0,phase:'NONE',ringsMask:0,refillConsumed:false,cleared:[],hits:0,hurt:0};
}
function emptyPlayer(x,y){
return{x:px(x),y:px(y),vx:0,vy:0,groundedPlatformId:null,facing:1,wing:64,flapCooldown:0,footingTicks:0,lavaPhase:'SAFE',lavaTicks:0,invulnerableTicks:0};
}
const SCORE_VERSION=2;
function freshScore(legacy=false){
return{version:SCORE_VERSION,legacy,eggChain:0,sectorClean:!legacy,bossChain:0,bossClean:!legacy,continuesUsed:0,deaths:0,carried:0,stageAwarded:0};
}
function startLivesFor(mode,C){
return mode==='ARCADE'&&C.scoring?C.scoring.arcade.startLives:C.startLives;
}
function newState(mode,seed,C){
return{
sim:{tick:0,mode,shell:'ATTRACT',nextActorId:1,eventSerial:0,score:0,lives:startLivesFor(mode,C)},
rng:{gameplayState:seedState(seed)},
player:emptyPlayer(32,310),
actors:[],
world:{contentId:'NONE',lavaY:px(C.lavaY),platforms:[]},
objectives:{routeId:'NONE',ringMask:0,waveId:'NONE',spawnCursor:0,authorizedActorIds:[],hostileClear:false,carry:[]},
circuit:{levelCursor:1,waveCursor:1,levelReady:false,waveReady:false,syncSerial:0},
boss:emptyBoss(),
story:emptyStory(),
cinema:emptyCinema(),
oneTime:{extraLifeBands:0,courseAwards:[],bossRewards:[]},
score:freshScore(),
};
}
function entityBox(x,y,box){
return{l:x+box.l*256,r:x+box.r*256,t:y+box.t*256,b:y+box.b*256};
}
return{newState,freshScore,SCORE_VERSION,emptyPlayer,entityBox,LANCE_Y_SUB,BIRD_BOX,RIDER_BOX,EGG_BOX,FLAP_COOLDOWN_TICKS,RESPAWN_HIDDEN_TICKS,SHIMMER_TICKS,BOSS_HITS_TO_DEFEAT,BOSS_HURT_TICKS};
})();
__modules[6]=(()=>{
const BOSS_MILESTONES=[5,11,17,23,29];
const BOSS_SET=new Set(BOSS_MILESTONES);
function actOf(n){
if (n<=5) return 1;
if (n<=11) return 2;
if (n<=17) return 3;
if (n<=23) return 4;
return 5;
}
const two=(n)=>String(n).padStart(2,'0');
function contentSelection(s){
const l=s.levelCursor,w=s.waveCursor;
if (s.bossPhase!=='NONE'){
return{arena:`BOSS_${two(l)}`,rings:'BOSS_RING_MASK',wave:'NONE',hazard:'BOSS_AUTHORED',audio:`BOSS_${actOf(l)}`};
}
if (l===w){
return{arena:`L${two(l)}`,rings:`L${two(l)}_PROGRESSION`,wave:`W${two(w)}_PROGRESSION`,hazard:`L${two(l)}`,audio:`ACT_${actOf(l)}`};
}
if (l>w){
return{arena:`L${two(w)}`,rings:`L${two(w)}_SCORE_ONLY`,wave:`W${two(w)}_PROGRESSION`,hazard:`L${two(w)}`,audio:`ACT_${actOf(w)}_COMBAT_DUE`};
}
return{arena:`L${two(l)}`,rings:`L${two(l)}_PROGRESSION`,wave:`W${two(l)}_SCORE_ONLY`,hazard:`L${two(l)}`,audio:`ACT_${actOf(l)}_FLIGHT_DUE`};
}
function reduceCircuit(pre,routeComplete,hostileClear){
const s=structuredClone(pre);
if (Math.abs(s.levelCursor-s.waveCursor)>1) return{legal:false,reason:'PRESTATE_FRONTIER'};
if (s.bossPhase!=='NONE'&&(routeComplete||hostileClear)) return{legal:false,reason:'ORDINARY_EVENT_DURING_BOSS'};
const pl=s.levelCursor,pw=s.waveCursor;
const events=[];
if (routeComplete){
if (pl<=pw){s.levelCursor+=1;events.push('LEVEL_COMMIT');}
else{s.levelReady=true;events.push('LEVEL_READY');}
}
if (hostileClear){
if (pw<=pl){s.waveCursor+=1;events.push('WAVE_COMMIT');}
else{s.waveReady=true;events.push('WAVE_READY');}
}
if (Math.abs(s.levelCursor-s.waveCursor)>1) return{legal:false,reason:'POST_PRIMARY_FRONTIER'};
const balanced=s.levelCursor===s.waveCursor;
if (balanced&&BOSS_SET.has(s.levelCursor)&&!s.bossCleared[String(s.levelCursor)]){
if (s.levelReady||s.waveReady) return{legal:false,reason:'READY_AT_BOSS_FRONTIER'};
s.bossPhase='RINGS';
events.push('BOSS_ENTER');
}else if (balanced&&(pl!==pw||(routeComplete&&hostileClear))){
s.score+=500;
s.wing=Math.min(64,s.wing+4);
s.syncSerial+=1;
events.push('CIRCUIT_SYNC');
if (pre.levelReady&&!routeComplete){s.levelReady=false;s.levelCursor+=1;events.push('LEVEL_READY_COMMIT');}
else if (pre.waveReady&&!hostileClear){s.waveReady=false;s.waveCursor+=1;events.push('WAVE_READY_COMMIT');}
}
if (Math.abs(s.levelCursor-s.waveCursor)>1) return{legal:false,reason:'POST_DRAIN_FRONTIER'};
s.activeContent=contentSelection(s);
return{legal:true,state:s,events};
}
return{reduceCircuit,contentSelection,actOf};
})();
__modules[7]=(()=>{
const{contentSelection,actOf}=__modules[6];
const{px,tdiv,mod}=__modules[4];
const{emptyPlayer}=__modules[5];
function levelRecord(A,n){return A.campaign_levels[n-1];}
function bossRecord(A,milestone){return A.bosses.bosses.find((b)=>b.milestone===milestone);}
function circuitPre(s){
const cleared={};
for (const m of[5,11,17,23,29]) cleared[String(m)]=s.boss.cleared.includes(m);
return{
levelCursor:s.circuit.levelCursor,waveCursor:s.circuit.waveCursor,
levelReady:s.circuit.levelReady,waveReady:s.circuit.waveReady,syncSerial:s.circuit.syncSerial,
bossPhase:s.boss.phase,bossCleared:cleared,score:s.sim.score,wing:s.player.wing,
};
}
function activeContent(s){return contentSelection(circuitPre(s));}
function clearRingPlacements(rings,platforms,clearance=2){
return rings.map((ring)=>{
const radius=ring.radius??11;
const x=ring.center[0];
let y=ring.center[1];
for (let pass=0;pass<=platforms.length;pass++){
let moved=false;
for (const platform of platforms){
const[px0,py0,pw,ph]=platform.rect;
const px1=px0+pw,py1=py0+ph;
const horizontal=x+radius>=px0&&x-radius<=px1;
const vertical=y+radius+clearance>py0&&y-radius-clearance<py1;
if (horizontal&&vertical){y=py0-radius-clearance;moved=true;}
}
if (!moved) break;
}
return y===ring.center[1]?ring:{...ring,center:[x,y]};
});
}
function arcadeTier(wave){return Math.min(5,1+Math.floor((wave-1)/6));}
function arcadeRoster(wave){
const tier=arcadeTier(wave);
return{
tier,
bounder:Math.max(1,4-Math.floor(tier/2)),
hunter:Math.min(5,1+Math.floor((wave-1)/3)),
shadow:Math.min(4,Math.floor((wave-1)/5)),
maxMounted:Math.min(6,2+tier),
spawnCadenceTicks:Math.max(48,96-8*tier),
};
}
function arcadeGhost(A,wave,spawnSerial){return A.arcade.waveGenerator.ghostOrder[mod(wave+spawnSerial,4)];}
function arcadeWorld(course,wave){
return{hazardAct:Math.min(5,1+Math.floor((Math.max(course,wave)-1)/8)),layoutIndex:mod(course-1,8),routeIndex:mod(course-1,8)};
}
const ARCADE_LAYOUT_LEVELS=[1,2,3,4,6,7,8,9];
const ACT_HAZARD_LEVELS={1:1,2:6,3:12,4:18,5:24};
function parseArcade(s){
const c=/^ARC_C(\d+)_R(\d+)$/.exec(s.objectives.routeId);
const w=/^ARC_W(\d+)$/.exec(s.objectives.waveId);
return{course:c?Number(c[1]):1,wave:w?Number(w[1]):1};
}
function carryEntries(s){
const carry=s.objectives&&Array.isArray(s.objectives.carry)?s.objectives.carry:[];
return carry.map((c)=>({class:c.class,tier:c.tier,ghost:c.ghost,paid:!!c.paid,carried:true}));
}
function arenaContent(A,s){
if (s.sim.mode==='ARCADE'){
const{course,wave}=parseArcade(s);
const ws=arcadeWorld(course,wave);
const layoutLevel=ARCADE_LAYOUT_LEVELS[ws.layoutIndex];
const layout=levelRecord(A,layoutLevel);
const hazardSrc=levelRecord(A,ACT_HAZARD_LEVELS[ws.hazardAct]).hazard;
const r=arcadeRoster(wave);
const carry=carryEntries(s);
const rosterList=[...carry];
for (let i=0;i<r.bounder;i++) rosterList.push({class:'BOUNDER',tier:r.tier});
for (let i=0;i<r.hunter;i++) rosterList.push({class:'HUNTER',tier:r.tier});
for (let i=0;i<r.shadow;i++) rosterList.push({class:'SHADOW',tier:r.tier});
const rings=layout.rings.map((x)=>({...x,id:`ARC_R${x.order}`}));
return{
kind:'ARCADE',contentId:`ARC_${String(ws.layoutIndex+1)}`,platforms:layout.platforms,playerSpawn:layout.playerSpawn,
enemySpawns:layout.enemySpawns,
rings:clearRingPlacements(rings,layout.platforms),ringsAnyOrder:false,
rosterList,ghostFor:(spawnSerial)=>rosterList[spawnSerial]?.ghost||arcadeGhost(A,wave,spawnSerial),maxMounted:r.maxMounted+carry.length,
spawnCadenceTicks:r.spawnCadenceTicks,hazard:hazardSrc,audioState:`ACT_${ws.hazardAct}`,course,wave,stage:course,tier:r.tier,
carried:carry.length,ringsProgression:true,combatProgression:true,
};
}
const ac=activeContent(s);
const victory=s.sim.shell==='WINNER'&&s.boss.cleared.includes(29);
if (s.boss.phase!=='NONE'||victory){
const m=victory?29:s.boss.milestone;
const rec=levelRecord(A,m);
const b=bossRecord(A,m);
const duel=s.boss.phase==='DUEL'||s.boss.phase==='CLEAR'||victory;
return{
kind:'BOSS',contentId:`BOSS_${String(m).padStart(2,'0')}`,milestone:m,record:rec,boss:b,
platforms:rec.platformsRingTrial,playerSpawn:rec.duel.playerSpawn,enemySpawns:[rec.duel.bossSpawn],
rings:clearRingPlacements(rec.rings,rec.platformsRingTrial),ringsAnyOrder:true,rosterList:duel?[{class:'BOSS',tier:rec.duel.tier,aiClass:rec.duel.bossClass,ghost:rec.duel.ghost}]:[],
ghostFor:()=>rec.duel.ghost,maxMounted:1,spawnCadenceTicks:0,hazard:rec.hazard,audioState:rec.audioState,
ringsProgression:false,combatProgression:false,
};
}
const n=Number(ac.arena.slice(1));
const rec=levelRecord(A,n);
const carry=carryEntries(s);
const authored=[];
for (const r of rec.roster) for (let i=0;i<r.count;i++) authored.push({class:r.class,tier:r.tier,ghost:r.ghost});
const carryStagger=A.sim_constants.scoring?.carry?.arrive!=='OPENING';
const cut=carryStagger?Math.min(authored.length,rec.openingPopulation):0;
const rosterList=[...authored.slice(0,cut),...carry,...authored.slice(cut)];
return{
kind:'NORMAL',contentId:ac.arena,level:n,record:rec,platforms:rec.platforms,playerSpawn:rec.playerSpawn,
enemySpawns:rec.enemySpawns,rings:clearRingPlacements(rec.rings,rec.platforms),ringsAnyOrder:false,rosterList,ghostFor:(i)=>rosterList[i].ghost,
maxMounted:rec.maxMounted+carry.length,openingPopulation:rec.openingPopulation+(carryStagger?0:carry.length),carried:carry.length,spawnCadenceTicks:rec.spawnCadenceTicks,hazard:rec.hazard,audioState:ac.audio,
ringsProgression:ac.rings.endsWith('_PROGRESSION'),combatProgression:ac.wave.endsWith('_PROGRESSION'),selection:ac,
};
}
function triangle(t,period){
const half=tdiv(period,2);
const u=mod(t,period);
return u<half?tdiv((u*512),Math.max(1,half))-256:256-tdiv(((u-half)*512),Math.max(1,half));
}
function easedMotion(motion,tick){
const period=Math.max(2,motion.period|0);
const dwell=Math.max(0,Math.min((period>>2)-1,motion.dwell|0));
const travel=Math.max(2,period-dwell*2),half=Math.max(1,travel>>1);
const u=mod(tick,period);
const ease=(age)=>{
const q=Math.max(0,Math.min(256,tdiv(age*256,half)));
return tdiv(q*q*(768-2*q),65536);
};
let q;
if (u<dwell) q=0;
else if (u<dwell+half) q=ease(u-dwell);
else if (u<dwell+half+dwell) q=256;
else q=256-ease(u-(dwell+half+dwell));
const amplitude=Math.max(0,motion.amplitude|0);
return{period,delta:-amplitude+tdiv(amplitude*2*q,256)};
}
function platformAt(p,h,t){
const[x0,y0,w0,h0]=p.rect;
const motion=p.motion||'STATIC';
if (motion&&typeof motion==='object'){
const{period,delta}=easedMotion(motion,t);
const u=mod(t,period),profile=motion.profile||'STATIC';
if (profile==='DRIFT_X_SOFT'||profile==='HOLD_SHIFT_X') return{id:p.id,phase:profile,tick:u,rect:[x0+delta,y0,w0,h0],collidable:true};
if (profile==='BOB_Y_SOFT') return{id:p.id,phase:profile,tick:u,rect:[x0,y0+delta,w0,h0],collidable:true};
return{id:p.id,phase:'STATIC',tick:u,rect:[x0,y0,w0,h0],collidable:true};
}
const period=Math.max(1,h.period||1),warning=h.warning||0,active=h.active||0,amp=h.amplitude||0;
const u=mod(t,period);
if (motion==='STATIC'||motion===undefined) return{id:p.id,phase:'STATIC',tick:u,rect:[x0,y0,w0,h0],collidable:true};
if (motion==='MOVE_X'){
const dx=tdiv(amp*triangle(u,period),256);
return{id:p.id,phase:'MOVE_X',tick:u,rect:[x0+dx,y0,w0,h0],collidable:true};
}
if (motion==='COLLAPSE'){
const gone=period-active,warn=gone-warning;
if (u>=gone) return{id:p.id,phase:'GONE',tick:u,rect:[x0,y0,w0,h0],collidable:false};
if (u>=warn) return{id:p.id,phase:'WARN',tick:u,rect:[x0,y0,w0,h0],collidable:true};
return{id:p.id,phase:'SOLID',tick:u,rect:[x0,y0,w0,h0],collidable:true};
}
if (motion==='GROW'){
if (u<warning){const dy=amp-tdiv(amp*u,Math.max(1,warning));return{id:p.id,phase:'RISING',tick:u,rect:[x0,y0+dy,w0,h0],collidable:false};}
if (u<warning+active) return{id:p.id,phase:'SOLID',tick:u,rect:[x0,y0,w0,h0],collidable:true};
if (u<warning+active+warning) return{id:p.id,phase:'WARN',tick:u,rect:[x0,y0,w0,h0],collidable:true};
return{id:p.id,phase:'ABSENT',tick:u,rect:[x0,y0+amp,w0,h0],collidable:false};
}
return{id:p.id,phase:'STATIC',tick:u,rect:[x0,y0,w0,h0],collidable:true};
}
function lavaAt(h,C,t){
const base=px(h.lavaY??C.lavaY);
if (h.kind!=='LAVA_PULSE'&&h.kind!=='COMBINED') return{lavaY:base,warning:false};
const u=mod(t,Math.max(1,h.period));
if (u<h.warning) return{lavaY:base,warning:true};
if (u<h.warning+h.active) return{lavaY:base-px(h.amplitude),warning:false};
return{lavaY:base,warning:false};
}
function stepWorld(A,s,content){
const C=A.sim_constants;
if (content.kind==='BOSS'){
return;
}
const h=content.hazard;
const byId=new Map(content.platforms.map((p)=>[p.id,p]));
for (const w of s.world.platforms){
const p=byId.get(w.id);
if (!p) continue;
const next=platformAt(p,h,w.tick+1);
w.phase=next.phase;w.tick=next.tick;w.rect=next.rect;w.collidable=next.collidable;
}
const lavaTick=s.world.platforms.length?s.world.platforms[0].tick:0;
const lv=lavaAt(h,C,lavaTick-(content.platforms[0].phaseOffset||0)+(h.phaseOffset||0));
s.world.lavaY=lv.lavaY;
return lv.warning;
}
function lavaWarningNow(A,s,content){
if (content.kind==='BOSS') return false;
const h=content.hazard;
const lavaTick=s.world.platforms.length?s.world.platforms[0].tick:0;
return lavaAt(h,A.sim_constants,lavaTick-(content.platforms[0].phaseOffset||0)+(h.phaseOffset||0)).warning;
}
function buildPlatforms(content){
const h=content.hazard||{kind:'STATIC'};
return content.platforms.map((p)=>{
if (content.kind==='BOSS') return{id:p.id,phase:'RING_TRIAL',tick:0,rect:p.rect.slice(),collidable:true};
return platformAt(p,h,p.phaseOffset||0);
});
}
function activateArena(A,s,events){
const content=arenaContent(A,s);
const C=A.sim_constants;
s.world.contentId=content.contentId;
s.world.platforms=buildPlatforms(content);
s.world.lavaY=px(content.hazard&&content.hazard.lavaY?content.hazard.lavaY:C.lavaY);
if (content.kind!=='BOSS'){
const lv=lavaAt(content.hazard,C,content.hazard.phaseOffset||0);
s.world.lavaY=lv.lavaY;
}
s.actors=[];
const keepWing=s.player.wing;
s.player=emptyPlayer(content.playerSpawn[0],content.playerSpawn[1]);
s.player.wing=keepWing;
if (s.sim.mode==='ARCADE'){
}else if (content.kind==='BOSS'){
s.objectives.routeId='BOSS_RING_MASK';
s.objectives.waveId='NONE';
}else{
s.objectives.routeId=content.selection.rings;
s.objectives.waveId=content.selection.wave;
}
s.objectives.ringMask=0;
s.objectives.spawnCursor=0;
s.objectives.authorizedActorIds=[];
s.objectives.hostileClear=false;
if (!Array.isArray(s.objectives.carry)) s.objectives.carry=[];
if (s.score){
s.score.eggChain=0;
s.score.carried=content.carried||0;
if (content.kind==='BOSS'){s.score.bossChain=0;s.score.bossClean=true;s.objectives.carry=[];}
else s.score.sectorClean=true;
}
events.push({type:'ARENA_ACTIVATE',contentId:content.contentId,audioState:content.audioState,carried:content.carried||0});
return content;
}
function filmIdFor(milestone){return `SKY_${actOf(milestone)}`;}
return{arenaContent,activateArena,stepWorld,circuitPre,parseArcade,lavaWarningNow,buildPlatforms,filmIdFor,ARCADE_LAYOUT_LEVELS};
})();
__modules[8]=(()=>{
const{clamp,tdiv,mod,WRAP,compareRational,nearestWrapShift}=__modules[4];
const{entityBox}=__modules[5];
const SHIFTS=[0,-WRAP,WRAP];
function overlapsX(l,r,pl,pr){
for (const sft of SHIFTS) if (l+sft<pr&&r+sft>pl) return true;
return false;
}
function platSpan(p){
return{pl:p.rect[0]*256,pr:(p.rect[0]+p.rect[2])*256,top:p.rect[1]*256,bottom:(p.rect[1]+p.rect[3])*256};
}
function integrate(e,box,ax,C,world,opts={}){
const maxVx=opts.grounded?C.maxGroundSpeed:C.maxAirSpeed;
e.vx=clamp(e.vx+ax,-maxVx,maxVx);
const wasGrounded=!!e.groundedPlatformId;
if (!wasGrounded||e.vy<0) e.vy=Math.min(e.vy+C.gravitySubpxPerTick2,C.maxFall);
else e.vy=0;
const oldX=e.x,oldY=e.y;
const ob=entityBox(oldX,oldY,box);
let newX=mod(oldX+e.vx,WRAP);
let newY=oldY+e.vy;
let nb=entityBox(newX,newY,box);
let landed=null,headBump=false;
const collidable=world.platforms.filter((p)=>p.collidable);
if (wasGrounded&&e.vy>=0){
const p=collidable.find((q)=>q.id===e.groundedPlatformId);
if (p){
const ps=platSpan(p);
if (overlapsX(nb.l,nb.r,ps.pl,ps.pr)){
newY=ps.top-box.b*256;
e.vy=0;
landed=p.id;
}
}
}
if (landed===null&&e.vy>0){
let best=null;
for (const p of collidable){
const ps=platSpan(p);
if (ob.b<=ps.top&&nb.b>=ps.top){
const num=ps.top-ob.b,den=nb.b-ob.b;
if (den<=0) continue;
const xc=oldX+tdiv(e.vx*num,den);
const cb=entityBox(xc,0,box);
if (!overlapsX(cb.l,cb.r,ps.pl,ps.pr)) continue;
if (best===null||compareRational(num,den,best.num,best.den)<0||(compareRational(num,den,best.num,best.den)===0&&p.id<best.id)) best={num,den,id:p.id,top:ps.top};
}
}
if (best){newY=best.top-box.b*256;e.vy=0;landed=best.id;}
}
if (landed===null&&e.vy<0){
for (const p of collidable){
const ps=platSpan(p);
if (ob.t>=ps.bottom&&nb.t<ps.bottom&&overlapsX(nb.l,nb.r,ps.pl,ps.pr)){
newY=ps.bottom-box.t*256;e.vy=C.headBumpVy;headBump=true;break;
}
}
}
const topLimit=(opts.topLimitPx??C.playTop)*256;
if (entityBox(newX,newY,box).t<topLimit){newY=topLimit-box.t*256;if (e.vy<0){e.vy=C.headBumpVy;headBump=true;}}
nb=entityBox(newX,newY,box);
for (const p of collidable){
const ps=platSpan(p);
if (landed===p.id) continue;
if (nb.b<=ps.top||nb.t>=ps.bottom) continue;
for (const sft of SHIFTS){
const l=nb.l+sft,r=nb.r+sft;
if (l<ps.pr&&r>ps.pl){
if (e.vx>0) newX=mod(ps.pl-box.r*256-sft,WRAP);else if (e.vx<0) newX=mod(ps.pr-box.l*256-sft,WRAP);
e.vx=tdiv(e.vx*C.wallBounceNumerator,C.wallBounceDenominator);
nb=entityBox(newX,newY,box);
break;
}
}
}
e.x=newX;e.y=newY;
if ('groundedPlatformId' in e) e.groundedPlatformId=landed;
const lava=entityBox(newX,newY,box).b>=world.lavaY;
return{landed,lava,headBump};
}
function inRing(box,ring){
const cx=tdiv(box.l+box.r,2),cy=tdiv(box.t+box.b,2);
const rx=ring.center[0]*256,ry=ring.center[1]*256;
let dx=cx-rx;dx+=nearestWrapShift(dx);
const dy=cy-ry;
const r=ring.radius*256;
return dx*dx+dy*dy<=r*r;
}
function boxesOverlap(a,b){
if (a.b<=b.t||a.t>=b.b) return false;
return overlapsX(a.l,a.r,b.l,b.r);
}
function standingPlatform(x,y,box,world){
const b=entityBox(x,y,box);
let best=null;
for (const p of world.platforms){
if (!p.collidable) continue;
const ps=platSpan(p);
if (b.b===ps.top&&overlapsX(b.l,b.r,ps.pl,ps.pr)&&(best===null||p.id<best)) best=p.id;
}
return best;
}
return{integrate,inRing,boxesOverlap,standingPlatform,overlapsX};
})();
__modules[9]=(()=>{
const{nextU32}=__modules[3];
const{wrappedDelta}=__modules[4];
const{LANCE_Y_SUB}=__modules[5];
const CENTER_X=128*256,CENTER_Y=192*256;
const CLYDE_RADIUS=72*256;
const CLASS_WINDOW={BOUNDER:24,HUNTER:12,SHADOW:8,BOSS:8};
const CLASS_FLAP_PERIOD={BOUNDER:10,HUNTER:8,SHADOW:8,BOSS:8};
function decodePhase(phase){
return{window:phase>>7,flapCd:(phase>>3)&15,flapWanted:!!(phase&4),dir:[0,-1,1][phase&3]||0};
}
function encodePhase(window,flapCd,flapWanted,dir){
return (window<<7)|((flapCd&15)<<3)|(flapWanted?4:0)|(dir===-1?1:dir===1?2:0);
}
function targetFor(ghost,s,actor,corner){
const p=s.player;
if (ghost==='PINKY') return{x:p.x+4*p.vx,y:p.y+4*p.vy};
if (ghost==='INKY'){const lx=p.x+4*p.vx,ly=p.y+4*p.vy;return{x:2*CENTER_X-lx,y:2*CENTER_Y-ly};}
if (ghost==='CLYDE'){
const dx=wrappedDelta(actor.x,p.x),dy=p.y-actor.y;
if (Math.abs(dx)>CLYDE_RADIUS||Math.abs(dy)>CLYDE_RADIUS) return{x:p.x,y:p.y};
return{x:corner[0]*256,y:corner[1]*256};
}
return{x:p.x,y:p.y};
}
function rivalIntent(A,s,actor,aiClass,corner,playerActive){
const C=A.sim_constants;
let ph=decodePhase(actor.phase);
const stall=actor.timer>=C.stallHuntTicks;
const ghost=stall?'BLINKY':actor.ghost;
if (ph.window===0){
const box={state:s.rng.gameplayState};
const draw=nextU32(box);
s.rng.gameplayState=box.state;
actor.rngDraws+=1;
const tier=Math.max(0,actor.tier);
let window=Math.max(4,(CLASS_WINDOW[aiClass]||12)+(5-tier)*3);
if (stall) window=4;
const t=targetFor(ghost,s,actor,corner);
const dx=wrappedDelta(actor.x,t.x);
let dir=dx>512?1:dx<-512?-1:0;
const lanceGap=(t.y+LANCE_Y_SUB)-(actor.y+LANCE_Y_SUB);
const climbThreshold=aiClass==='BOUNDER'?-10*256:aiClass==='HUNTER'?-2*256:4*256;
let flapWanted=lanceGap<climbThreshold;
const r=draw&15;
if (aiClass==='BOUNDER'&&r===0) dir=-dir;
if (aiClass==='SHADOW'&&(r&3)===0) dir=-dir;
if (r===15&&!flapWanted) flapWanted=true;
if (((draw>>>4)%6)>tier&&!stall) dir=0;
if (!playerActive){dir=0;flapWanted=actor.y>CENTER_Y;}
if (actor.y+25*256>s.world.lavaY-24*256) flapWanted=true;
ph={window,flapCd:0,flapWanted,dir};
}else{
ph.window-=1;
}
let flap=false;
if (ph.flapWanted){
if (ph.flapCd===0){flap=true;ph.flapCd=CLASS_FLAP_PERIOD[aiClass]||6;}else ph.flapCd-=1;
}else if (ph.flapCd>0) ph.flapCd-=1;
actor.phase=encodePhase(ph.window,ph.flapCd,ph.flapWanted,ph.dir);
return{dir:ph.dir,flap};
}
return{rivalIntent,decodePhase,CLASS_FLAP_PERIOD};
})();
__modules[10]=(()=>{
const{activateArena,filmIdFor}=__modules[7];
function filmShots(A,filmId){
return A.cinema.shots.filter((sh)=>sh.filmId===filmId).sort((a,b)=>a.shotIndex-b.shotIndex);
}
function enterCinema(s,milestone,events){
s.sim.shell='CINEMA_SKY';
s.cinema={pending:milestone,filmId:filmIdFor(milestone),shotIndex:0,shotTick:0,skipTicks:0,releaseLatched:true};
events.push({type:'CINEMA_START',filmId:s.cinema.filmId,milestone});
}
const STORY_FLAG={5:'signalKnown',11:'oldCircuitKnown',17:'fractureKnown',23:'warningKnown',29:'circuitReleased'};
const FILM_BIT={5:1,11:2,17:4,23:8,29:16};
function completeFilm(A,s,events,how){
if (s.cinema.pending===0) return false;
const m=s.cinema.pending;
s.story.seenMask|=FILM_BIT[m];
s.story[STORY_FLAG[m]]=true;
s.cinema={pending:0,filmId:'',shotIndex:0,shotTick:0,skipTicks:0,releaseLatched:true};
s.boss.phase='NONE';s.boss.milestone=0;s.boss.ringsMask=0;s.boss.refillConsumed=false;
events.push({type:'CINEMA_COMPLETE',milestone:m,how});
if (m===29){
s.story.complete=true;
const R=A.sim_constants.scoring;
if (R&&s.score&&s.score.continuesUsed===0){
const reserve=R.campaign.reservePerMark*Math.max(0,s.sim.lives|0);
s.sim.score+=R.campaign.noContinue;
events.push({type:'SCORE_AWARD',kind:'NO_CONTINUE',amount:R.campaign.noContinue});
if (reserve>0){s.sim.score+=reserve;events.push({type:'SCORE_AWARD',kind:'RESERVE',amount:reserve,marks:s.sim.lives|0});}
}
s.sim.shell='WINNER';
events.push({type:'WINNER'});
}else{
s.circuit.levelCursor=m+1;s.circuit.waveCursor=m+1;
s.circuit.levelReady=false;s.circuit.waveReady=false;
s.sim.shell='PLAY';
activateArena(A,s,events);
}
events.push({type:'CHECKPOINT_REQUEST',reason:'CINEMA_COMPLETE'});
return true;
}
function cinemaHolding(shot,c){return c.shotTick>=shot.durationTicks;}
function stepCinema(A,s,input,events){
const shots=filmShots(A,s.cinema.filmId);
const c=s.cinema;
const holdTicks=A.cinema.skipHoldTicks;
if (input.flapEdge&&!c.releaseLatched){
c.releaseLatched=true;
c.skipTicks=0;
const current=shots[c.shotIndex];
if (!cinemaHolding(current,c)){
c.shotTick=current.durationTicks;
events.push({type:'CINEMA_HOLD',shotIndex:c.shotIndex,shotId:current.shotId});
}else{
c.shotIndex+=1;c.shotTick=0;
events.push({type:'CINEMA_ADVANCE',shotIndex:c.shotIndex});
if (c.shotIndex>=shots.length) return completeFilm(A,s,events,'ADVANCED');
events.push({type:'CINEMA_SHOT',shotIndex:c.shotIndex,shotId:shots[c.shotIndex].shotId});
}
}
if (input.flapHeld){
c.skipTicks=Math.min(holdTicks,c.skipTicks+1);
if (c.skipTicks>=holdTicks) return completeFilm(A,s,events,'SKIPPED');
}else{
c.skipTicks=0;
c.releaseLatched=false;
}
const shot=shots[c.shotIndex];
if (cinemaHolding(shot,c)) return false;
if (shot.audioCueTick!==undefined){
const cues=Array.isArray(shot.audioCueTick)?shot.audioCueTick:[shot.audioCueTick];
if (cues.includes(c.shotTick)) events.push({type:'CINEMA_CUE',cue:shot.audioCue,shotId:shot.shotId});
}
c.shotTick+=1;
if (cinemaHolding(shot,c)) events.push({type:'CINEMA_HOLD',shotIndex:c.shotIndex,shotId:shot.shotId});
return false;
}
return{stepCinema,enterCinema,filmShots};
})();
__modules[11]=(()=>{
const clamp=(n,lo,hi)=>Math.max(lo,Math.min(hi,n));
function bitCount(mask){
let n=mask>>>0,count=0;
while (n){count+=n&1;n>>>=1;}
return count;
}
function campaignAscentActive(s,content){
return s.sim.mode==='CAMPAIGN'&&!!content&&(content.kind==='NORMAL'||content.kind==='BOSS');
}
function ascentGateActive(s,content){
return campaignAscentActive(s,content)||(s.sim.mode==='ARCADE'&&!!content&&content.kind==='ARCADE'&&!(s.score&&s.score.legacy));
}
function cumulativeSpawnCeiling(s,content){
const total=content.rosterList.length;
if (s.sim.mode!=='CAMPAIGN'||content.kind!=='NORMAL') return total;
const beat=content.ringsProgression?clamp(bitCount(s.objectives.ringMask),0,5):5;
const opening=Math.min(total,content.openingPopulation||1);
return total>0?opening+Math.floor((total-opening)*beat/5):0;
}
function courseSpawnAnchor(s,content,index){
const anchors=content.enemySpawns;
if (s.sim.mode!=='CAMPAIGN'||content.kind!=='NORMAL') return anchors[index%anchors.length];
const beat=content.ringsProgression?clamp(bitCount(s.objectives.ringMask),0,5):5;
const targetY=content.rings[beat].center[1]-25;
const ordered=anchors.map((anchor,order)=>({anchor,order,distance:Math.abs(anchor[1]-targetY)}))
.sort((a,b)=>a.distance-b.distance||a.order-b.order);
const minimum=index<(content.openingPopulation||1)?Math.min(ordered.length,content.openingPopulation):1;
const region=ordered.filter((a,i)=>i<minimum||a.distance<=ordered[0].distance+20);
return region[index%region.length].anchor;
}
function ascentMetrics(s,content){
if (!ascentGateActive(s,content)||(content.kind!=='NORMAL'&&content.kind!=='ARCADE')){
return{active:false,ringSteps:0,combatSteps:0,progressSteps:0,allowedOrder:0,resolved:0,total:0};
}
const total=content.rosterList.length;
const resolved=clamp(s.objectives.spawnCursor-s.objectives.authorizedActorIds.length,0,total);
const ringSteps=content.ringsProgression?clamp(bitCount(s.objectives.ringMask),0,6):6;
const combatSteps=content.combatProgression
?(total>0?clamp(Math.floor(resolved*6/total),0,6):6)
:6;
const progressSteps=Math.min(ringSteps,combatSteps);
return{
active:true,
ringSteps,
combatSteps,
progressSteps,
allowedOrder:clamp(progressSteps+1,1,6),
resolved,
total,
};
}
return{ascentMetrics,cumulativeSpawnCeiling,courseSpawnAnchor,bitCount,campaignAscentActive,ascentGateActive};
})();
__modules[12]=(()=>{
const{digest}=__modules[1];
const{px,mod,wrappedDelta}=__modules[4];
const{reduceCircuit}=__modules[6];
const{arenaContent,activateArena,stepWorld,circuitPre,parseArcade,buildPlatforms}=__modules[7];
const{integrate,inRing,boxesOverlap,standingPlatform}=__modules[8];
const{rivalIntent}=__modules[9];
const{stepCinema,enterCinema}=__modules[10];
const{ascentMetrics,cumulativeSpawnCeiling,courseSpawnAnchor}=__modules[11];
const{entityBox,BIRD_BOX,RIDER_BOX,EGG_BOX,LANCE_Y_SUB,FLAP_COOLDOWN_TICKS,RESPAWN_HIDDEN_TICKS,SHIMMER_TICKS,emptyPlayer,BOSS_HITS_TO_DEFEAT,BOSS_HURT_TICKS,freshScore}=__modules[5];
const EMPTY_INPUT=Object.freeze({left:false,right:false,flapEdge:false,flapHeld:false});
function playerActive(s){return s.player.invulnerableTicks<=SHIMMER_TICKS;}
function actorBox(a){return entityBox(a.x,a.y,a.kind==='RIDER'?RIDER_BOX:a.kind==='EGG'?EGG_BOX:BIRD_BOX);}
function rules(s){return s._C.scoring;}
function ensureScoreState(s){
if (!s.score){
s.score=freshScore(true);
s.score.deaths=0;
}
if (!Array.isArray(s.objectives.carry)) s.objectives.carry=[];
}
function lifeThreshold(R,k){return k===0?R.arcade.firstLife:R.arcade.lifeEvery*k;}
function addScore(s,amount,events,kind='OTHER',extra=null){
const R=rules(s);
const value=Math.max(0,Math.trunc(amount));
if (!value) return 0;
s.sim.score+=value;
events.push({type:'SCORE_AWARD',kind,amount:value,...(extra||{})});
if (s.sim.mode==='ARCADE'){
while (s.sim.score>=lifeThreshold(R,s.oneTime.extraLifeBands)){
s.oneTime.extraLifeBands+=1;
if (s.sim.lives<R.arcade.maxLives){s.sim.lives+=1;events.push({type:'EXTRA_LIFE',lives:s.sim.lives});}
}
}
return value;
}
function joustValue(R,actor){
const base=R.joustClassBase[actor.class]??R.joustClassBase.BOUNDER;
return base+R.joustTierStep*(Math.max(1,actor.tier|0)-1);
}
function eggValue(R,chain){return R.eggChain[Math.min(chain,R.eggChain.length-1)];}
function unresolvedRivals(s,content){
const live=s.actors.filter((a)=>a.kind!=='EGG'&&['SPAWNING','MOUNTED','HATCHING','REMOUNTING'].includes(a.lifecycle)&&a.class!=='BOSS')
.map((a)=>({class:a.class,tier:a.tier,ghost:a.ghost,paid:!!a.joustAwarded}));
const pending=content.rosterList.slice(s.objectives.spawnCursor).map((e)=>({class:e.class,tier:e.tier,ghost:e.ghost||'NONE',paid:!!e.paid}));
const forfeited=s.actors.filter((a)=>a.lifecycle==='DISMOUNTED'||a.lifecycle==='EGG').length;
return{list:[...live,...pending],forfeited};
}
function retireSector(A,s,content,events,intoBoss){
const R=rules(s);
const left=unresolvedRivals(s,content);
const unresolved=left.list.length+left.forfeited;
if (s.score.sectorClean) addScore(s,R.survival,events,'SURVIVAL');
if (unresolved===0) addScore(s,R.sweep,events,'SWEEP');
const cap=intoBoss&&!R.carry.intoBoss?0:R.carry.cap;
const carry=left.list.slice(0,cap);
s.objectives.carry=carry;
events.push({type:'SECTOR_RETIRED',clean:!!s.score.sectorClean,sweep:unresolved===0,carried:carry.length,dropped:left.list.length-carry.length,forfeitedEggs:left.forfeited,intoBoss:!!intoBoss});
if (carry.length) events.push({type:'CARRY_OVER',count:carry.length});
}
function playerDeath(A,s,events,content,cause){
events.push({type:'PLAYER_DEATH',cause});
if (s.score){
s.score.deaths+=1;
s.score.eggChain=0;
s.score.sectorClean=false;
s.score.bossChain=0;
s.score.bossClean=false;
}
s.sim.lives-=1;
s.player=emptyPlayer(content.playerSpawn[0],content.playerSpawn[1]);
s.player.invulnerableTicks=RESPAWN_HIDDEN_TICKS+SHIMMER_TICKS;
if (s.sim.lives<=0){s.sim.lives=0;s._pendingGameOver=true;}
s._deathThisTick=true;
}
function stageTimers(s){
const p=s.player;
if (p.flapCooldown>0) p.flapCooldown-=1;
if (p.invulnerableTicks>0) p.invulnerableTicks-=1;
if (p.lavaPhase==='SINK'&&p.lavaTicks>0) p.lavaTicks-=1;
if ((s.boss.hurt|0)>0) s.boss.hurt-=1;
for (const a of s.actors){
if (a.lifecycle==='MOUNTED'){if (a.timer<1200) a.timer+=1;}
else if (a.timer>0) a.timer-=1;
}
}
function playerIntent(A,s,input,events){
return humanIntent(A.sim_constants,s.player,playerActive(s)&&!s._locked,input,events);
}
function humanIntent(C,p,active,input,events){
if (!active) return{ax:0,flap:false,dart:false};
let h=0;
if (input.left&&!input.right) h=-1;else if (input.right&&!input.left) h=1;
if (h!==0) p.facing=h;
const grounded=!!p.groundedPlatformId;
let ax=0;
if (h!==0){
if (grounded&&Math.sign(p.vx)===-h&&p.vx!==0) ax=h*C.skidDecel;
else ax=h*(grounded?C.groundAccel:C.airAccel);
}else{
const d=grounded?C.groundFriction:C.airDrag;
ax=p.vx>0?-Math.min(d,p.vx):p.vx<0?Math.min(d,-p.vx):0;
}
let flap=false,chordCorrection=false;
const kind=input.flapKind||'LEGACY';
if (input.flapEdge&&p.flapCooldown===0&&p.wing>0){
flap=true;
p.wing-=1;
p.flapCooldown=FLAP_COOLDOWN_TICKS;
p.footingTicks=0;
events.push({type:'FLAP',kind});
}else if (input.flapEdge&&input.chordEdge&&kind==='STRAIGHT'&&p.flapCooldown>0){
flap=true;chordCorrection=true;
events.push({type:'FLAP_CHORD'});
}
const dart=!!input.dartEdge;
if (dart) events.push({type:'DART',side:input.dartSide||(p.facing<0?'LEFT':'RIGHT')});
if (flap&&kind==='STRAIGHT') ax=0;
return{ax,flap,h,kind,chordCorrection,dart,dartSide:input.dartSide||(p.facing<0?'LEFT':'RIGHT')};
}
function aiIntents(A,s,content){
const intents=new Map();
const bossRec=content.kind==='BOSS'?content.record:null;
for (const a of s.actors){
if (a.lifecycle!=='MOUNTED') continue;
const aiClass=a.class==='BOSS'?bossRec.duel.bossClass:a.class;
const corner=a.ghost==='CLYDE'&&content.kind==='NORMAL'&&s.sim.mode==='CAMPAIGN'
?courseSpawnAnchor(s,content,a.id-1):content.enemySpawns[0];
const intent=rivalIntent(A,s,a,aiClass,corner,playerActive(s));
if (a.class==='BOSS'&&(s.boss.hurt|0)>0){
intent.dir=wrappedDelta(a.x,s.player.x)>=0?-1:1;
intent.flap=(s.boss.hurt&7)===0&&a.y>140*256;
}
intents.set(a.id,intent);
}
return intents;
}
function integrateHuman(C,p,pIntent,world,dartTargets,events){
if (pIntent.flap){
if (pIntent.kind==='LEFT'||pIntent.kind==='RIGHT'){
const side=pIntent.kind==='LEFT'?-1:1;
p.vy=Math.max(p.vy-Math.trunc(C.flapImpulseSubpxPerTick*82/100),C.flapVyClamp);
p.vx=Math.max(-C.maxAirSpeed,Math.min(C.maxAirSpeed,p.vx+side*210));
p.facing=side;
}else if (pIntent.kind==='STRAIGHT'){
p.vy=Math.max(p.vy-(pIntent.chordCorrection?96:C.flapImpulseSubpxPerTick),C.flapVyClamp);
p.vx=0;
}else p.vy=Math.max(p.vy-C.flapImpulseSubpxPerTick,C.flapVyClamp);
p.groundedPlatformId=null;
}
if (pIntent.dart){
const side=pIntent.dartSide==='LEFT'?-1:1;
const candidates=dartTargets.map((actor)=>({
actor,dx:wrappedDelta(p.x,actor.x),dy:actor.y-p.y,
})).filter(({dx,dy})=>dx*side>0&&Math.abs(dx)<=72*256&&dy>=4*256&&dy<=104*256&&Math.abs(dx)<=dy);
candidates.sort((a,b)=>(a.dy+Math.abs(a.dx))-(b.dy+Math.abs(b.dx))||a.actor.id-b.actor.id);
const target=candidates[0];
p.vy=Math.max(p.vy,Math.min(C.maxFall,704));
p.vx=target?Math.max(-C.maxAirSpeed,Math.min(C.maxAirSpeed,Math.trunc(target.dx/12))):Math.max(-C.maxAirSpeed,Math.min(C.maxAirSpeed,p.vx+side*96));
p.facing=side;p.groundedPlatformId=null;p.footingTicks=0;
}
if (p.lavaPhase==='SINK'){
if (pIntent.flap){p.lavaPhase='RESCUED';p.vy=C.lavaRescueVy;p.invulnerableTicks=Math.max(p.invulnerableTicks,C.lavaInvulnerableTicks);p.lavaTicks=0;events.push({type:'LAVA_RESCUE'});}
else{p.vy=64;p.y+=p.vy;p.vx=0;return p.lavaTicks===0?'SINK_DEATH':'SINK';}
}
const wasGrounded=!!p.groundedPlatformId;
const r=integrate(p,BIRD_BOX,pIntent.ax,C,world,{grounded:wasGrounded});
if (r.landed){
p.footingTicks+=1;
if (p.footingTicks>=C.wingRechargeArmTicks&&(p.footingTicks-C.wingRechargeArmTicks)%C.wingRechargeIntervalTicks===0&&p.wing<C.wingMax) p.wing+=1;
}else p.footingTicks=0;
if (r.lava){
if (p.lavaPhase==='SAFE'){p.lavaPhase='SINK';p.lavaTicks=C.lavaRescueWindowTicks;events.push({type:'LAVA_CONTACT'});}
}else if (p.lavaPhase==='RESCUED') p.lavaPhase='SAFE';
return null;
}
function integrateAll(A,s,content,pIntent,intents,events){
const C=A.sim_constants,p=s.player;
const previousWorld={platforms:s.world.platforms.map((platform)=>({...platform,rect:platform.rect.slice()})),lavaY:s.world.lavaY};
const actorFooting=new Map();
for (const actor of s.actors){
const box=actor.lifecycle==='MOUNTED'?BIRD_BOX:actor.lifecycle==='DISMOUNTED'?RIDER_BOX:actor.lifecycle==='EGG'?EGG_BOX:null;
if (box) actorFooting.set(actor.id,standingPlatform(actor.x,actor.y,box,previousWorld));
}
const lavaWarning=stepWorld(A,s,content);
if (lavaWarning&&!s._lavaWarned) events.push({type:'LAVA_WARNING'});
s._lavaWarned=!!lavaWarning;
const oldById=new Map(previousWorld.platforms.map((platform)=>[platform.id,platform]));
const newById=new Map(s.world.platforms.map((platform)=>[platform.id,platform]));
const inherit=(entity,platformId)=>{
if (!platformId) return;
const before=oldById.get(platformId),after=newById.get(platformId);
if (!before||!after||!before.collidable||!after.collidable) return;
entity.x=mod(entity.x+(after.rect[0]-before.rect[0])*256,256*256);
entity.y+=(after.rect[1]-before.rect[1])*256;
};
inherit(p,p.groundedPlatformId);
for (const actor of s.actors) inherit(actor,actorFooting.get(actor.id));
if (playerActive(s)&&!s._locked){
const sink=integrateHuman(C,p,pIntent,s.world,s.actors.filter((actor)=>actor.lifecycle==='MOUNTED'),events);
if (sink){if (sink==='SINK_DEATH') playerDeath(A,s,events,content,'LAVA');return;}
}
for (const a of s.actors){
if (a.lifecycle==='REMOVED'||a.lifecycle==='SPAWNING'||a.lifecycle==='HATCHING'||a.lifecycle==='REMOUNTING') continue;
if (a.lifecycle==='MOUNTED'){
const it=intents.get(a.id)||{dir:0,flap:false};
if (it.dir!==0) a.facing=it.dir;
const grounded=standingPlatform(a.x,a.y,BIRD_BOX,s.world)!==null;
let ax=0;
if (it.dir!==0) ax=it.dir*(grounded?C.groundAccel:C.airAccel);
else{const d=grounded?C.groundFriction:C.airDrag;ax=a.vx>0?-Math.min(d,a.vx):a.vx<0?Math.min(d,-a.vx):0;}
if (it.flap){a.vy=Math.max(a.vy-C.flapImpulseSubpxPerTick,C.flapVyClamp);}
const e={x:a.x,y:a.y,vx:a.vx,vy:a.vy,groundedPlatformId:grounded?standingPlatform(a.x,a.y,BIRD_BOX,s.world):null};
const r=integrate(e,BIRD_BOX,ax,C,s.world,{grounded});
a.x=e.x;a.y=e.y;a.vx=e.vx;a.vy=e.vy;
if (r.lava){a.vy=C.lavaRescueVy;}
}else if (a.lifecycle==='DISMOUNTED'){
const g0=standingPlatform(a.x,a.y,RIDER_BOX,s.world);
const e={x:a.x,y:a.y,vx:a.vx,vy:a.vy,groundedPlatformId:g0};
const drag=e.vx>0?-Math.min(C.airDrag,e.vx):e.vx<0?Math.min(C.airDrag,-e.vx):0;
const r=integrate(e,RIDER_BOX,drag,C,s.world,{grounded:!!g0});
a.x=e.x;a.y=e.y;a.vx=e.vx;a.vy=e.vy;
if (r.lava) s._lifecycle.push({id:a.id,to:'REMOVED',why:'RIDER_LAVA'});
else if (r.landed&&a.timer===0) s._lifecycle.push({id:a.id,to:'EGG'});
}else if (a.lifecycle==='EGG'){
const g0=standingPlatform(a.x,a.y,EGG_BOX,s.world);
const e={x:a.x,y:a.y,vx:0,vy:a.vy,groundedPlatformId:g0};
const r=integrate(e,EGG_BOX,0,C,s.world,{grounded:!!g0});
a.x=e.x;a.y=e.y;a.vy=e.vy;
if (r.lava) s._lifecycle.push({id:a.id,to:'REMOVED',why:'EGG_LAVA'});
}
}
if (content.kind==='BOSS'&&s.boss.phase==='DUEL'&&Array.isArray(content.record.duel.spikes)){
const touches=(entity,box,spike)=>{
const hit=entityBox(entity.x,entity.y,box),[x,y,w,h]=spike.rect;
const top=y*256,bottom=(y+h)*256,left=x*256,right=(x+w)*256;
if (!(hit.b>top&&hit.t<bottom)) return false;
return[-256,0,256].some((shift)=>hit.r+shift*256>left&&hit.l+shift*256<right);
};
if (!s._deathThisTick&&content.record.duel.spikes.some((spike)=>touches(p,BIRD_BOX,spike))) playerDeath(A,s,events,content,'SPIKE');
for (const actor of s.actors) if (actor.lifecycle==='MOUNTED'&&content.record.duel.spikes.some((spike)=>touches(actor,BIRD_BOX,spike))){
s._lifecycle.push({id:actor.id,to:'REMOVED',why:'SPIKE'});
if (actor.class==='BOSS') s._bossDefeated=true;
}
}
}
function joustStage(A,s,content,events){
const C=A.sim_constants,p=s.player;
if (!playerActive(s)||s._locked||s._deathThisTick) return;
const pb=entityBox(p.x,p.y,BIRD_BOX);
const pairs=[];
for (const a of s.actors){
if (a.lifecycle!=='MOUNTED') continue;
if (boxesOverlap(pb,actorBox(a))) pairs.push([0,a.id]);
}
const mounted=s.actors.filter((a)=>a.lifecycle==='MOUNTED');
for (let i=0;i<mounted.length;i++) for (let j=i+1;j<mounted.length;j++){
if (boxesOverlap(actorBox(mounted[i]),actorBox(mounted[j]))) pairs.push([Math.min(mounted[i].id,mounted[j].id),Math.max(mounted[i].id,mounted[j].id)]);
}
pairs.sort((x,y)=>x[0]-y[0]||x[1]-y[1]);
const losers=new Set();
for (const[aId,bId] of pairs){
if (losers.has(aId)||losers.has(bId)) continue;
const ea=aId===0?p:s.actors.find((x)=>x.id===aId);
const eb=s.actors.find((x)=>x.id===bId);
const dx=wrappedDelta(ea.x,eb.x);
const bounce=()=>{ea.vx=dx>=0?-C.lanceBounceVx:C.lanceBounceVx;eb.vx=-ea.vx;ea.vy=C.lanceBounceVy;eb.vy=C.lanceBounceVy;if (aId===0) ea.groundedPlatformId=null;};
if (aId!==0){bounce();events.push({type:'JOUST_CLASH',a:aId,b:bId});continue;}
const delta=(p.y+LANCE_Y_SUB)-(eb.y+LANCE_Y_SUB);
let result;
if (Math.abs(delta)<=C.lanceTieBandSubpx) result='CLASH';
else if (delta>0) result=delta<=C.lanceTieBandSubpx+C.playerGraceSubpx?'CLASH':'PLAYER_LOSES';
else result='RIVAL_LOSES';
if (result==='PLAYER_LOSES'&&p.invulnerableTicks>0) result='CLASH';
if (eb.class==='BOSS'&&(s.boss.hurt|0)>0) result='CLASH';
if (result==='RIVAL_LOSES'&&eb.class==='BOSS'){
s.boss.hits=(s.boss.hits|0)+1;
if (s.boss.hits<BOSS_HITS_TO_DEFEAT){
s.boss.hurt=BOSS_HURT_TICKS;
eb.tier=Math.min(5,eb.tier+1);
bounce();
eb.vx*=2;eb.vy=C.lanceBounceVy*3;
events.push({type:'BOSS_HIT',rival:bId,hits:s.boss.hits,remaining:BOSS_HITS_TO_DEFEAT-s.boss.hits});
const R=rules(s);
addScore(s,R.boss.hitChain[Math.min(s.score.bossChain,R.boss.hitChain.length-1)],events,'BOSS_HIT',{chain:s.score.bossChain+1});
s.score.bossChain+=1;
continue;
}
}
if (result==='CLASH'){bounce();events.push({type:'JOUST_CLASH',a:0,b:bId});}
else if (result==='RIVAL_LOSES'){
losers.add(bId);
events.push({type:'JOUST_WIN',rival:bId,cls:eb.class});
const R=rules(s);
if (eb.class==='BOSS'){
addScore(s,R.boss.hitChain[Math.min(s.score.bossChain,R.boss.hitChain.length-1)],events,'BOSS_HIT',{chain:s.score.bossChain+1});
s.score.bossChain+=1;
}else{
if (!eb.joustAwarded) addScore(s,joustValue(R,eb),events,'JOUST',{cls:eb.class,tier:eb.tier});
eb.joustAwarded=true;
}
s._lifecycle.push({id:bId,to:eb.class==='BOSS'?'REMOVED':'DISMOUNTED',why:'JOUST'});
if (eb.class==='BOSS') s._bossDefeated=true;
bounce();
}else{
losers.add(0);
playerDeath(A,s,events,content,'JOUST');
return;
}
}
if (!s._deathThisTick) for (const a of s.actors){
if (a.lifecycle==='EGG'&&boxesOverlap(entityBox(p.x,p.y,BIRD_BOX),actorBox(a))){
s._lifecycle.push({id:a.id,to:'REMOVED',why:'EGG_COLLECTED'});
events.push({type:'EGG',actor:a.id,chain:s.score.eggChain+1});
addScore(s,eggValue(rules(s),s.score.eggChain),events,'EGG',{chain:s.score.eggChain+1});
s.score.eggChain+=1;
}
}
}
function lifecycleStage(A,s,content,events){
const C=A.sim_constants,L=A.lifecycle.timers;
for (const a of s.actors){
if (a.joustAwarded===undefined&&['DISMOUNTED','EGG','HATCHING','REMOUNTING'].includes(a.lifecycle)) a.joustAwarded=true;
if (a.timer!==0) continue;
if (a.lifecycle==='SPAWNING'){a.lifecycle='MOUNTED';a.timer=0;a.phase=0;events.push({type:'MOUNT',actor:a.id});}
else if (a.lifecycle==='EGG'){a.lifecycle='HATCHING';a.timer=L.hatching;events.push({type:'HATCH',actor:a.id});}
else if (a.lifecycle==='HATCHING'){a.lifecycle='REMOUNTING';a.timer=L.remounting;}
else if (a.lifecycle==='REMOUNTING'){a.lifecycle='MOUNTED';a.kind='RIVAL';a.timer=0;a.phase=0;a.vx=0;a.vy=0;events.push({type:'REMOUNT',actor:a.id});}
}
for (const req of s._lifecycle){
const a=s.actors.find((x)=>x.id===req.id);
if (!a||a.lifecycle==='REMOVED') continue;
if (req.to==='DISMOUNTED'){a.lifecycle='DISMOUNTED';a.kind='RIDER';a.timer=L.dismountMinimum;}
else if (req.to==='EGG'){a.lifecycle='EGG';a.kind='EGG';a.timer=L.egg;a.vx=0;}
else if (req.to==='REMOVED'){a.lifecycle='REMOVED';}
}
s._lifecycle=[];
s.actors=s.actors.filter((a)=>a.lifecycle!=='REMOVED');
s.objectives.authorizedActorIds=s.actors.map((a)=>a.id);
if (content.kind==='BOSS'&&s.boss.phase!=='DUEL') return;
if (s.objectives.spawnCursor<cumulativeSpawnCeiling(s,content)&&!s._locked){
const live=s.actors.filter((a)=>['SPAWNING','MOUNTED','REMOUNTING','HATCHING'].includes(a.lifecycle)).length;
const newest=s.actors.length?s.actors[s.actors.length-1]:null;
const opening=s.sim.mode==='CAMPAIGN'&&content.kind==='NORMAL'&&s.objectives.spawnCursor<(content.openingPopulation||1);
const spacingOk=!newest||newest.lifecycle!=='SPAWNING'||(opening
?newest.timer<=C.waveIntroTicks-C.openingStaggerTicks
:newest.timer<=SHIMMER_TICKS-content.spawnCadenceTicks);
const arrivalReady=opening||s.sim.mode!=='CAMPAIGN'||content.kind!=='NORMAL'||
s.objectives.spawnCursor===0||s.sim.tick%content.spawnCadenceTicks===0;
if (live<content.maxMounted&&spacingOk&&arrivalReady&&content.kind!=='BOSS'){
const idx=s.objectives.spawnCursor;
const entry=content.rosterList[idx];
const sp=courseSpawnAnchor(s,content,idx);
const firstOfWave=(s.actors.length===0&&idx===0)||opening;
const actor={id:s.sim.nextActorId,kind:'RIVAL',class:entry.class,ghost:content.ghostFor(idx),tier:entry.tier,lifecycle:'SPAWNING',x:px(sp[0]),y:px(sp[1]),vx:0,vy:0,facing:sp[0]<128?1:-1,phase:0,timer:firstOfWave||entry.carried?C.waveIntroTicks:SHIMMER_TICKS,rngDraws:0,joustAwarded:!!entry.paid};
s.sim.nextActorId+=1;
s.actors.push(actor);
s.objectives.spawnCursor+=1;
s.objectives.authorizedActorIds.push(actor.id);
events.push({type:'SPAWN',actor:actor.id,cls:actor.class,ghost:actor.ghost});
}
}
}
function objectivesStage(A,s,content,events){
const C=A.sim_constants,p=s.player;
let routeComplete=false,hostileClear=false;
if (playerActive(s)&&!s._locked&&!s._deathThisTick&&s.boss.phase!=='TRANSITION'&&s.boss.phase!=='DUEL'&&s.boss.phase!=='CLEAR'){
const pb=entityBox(p.x,p.y,BIRD_BOX);
if (content.kind==='BOSS'){
content.rings.forEach((ring,i)=>{
const bit=1<<i;
if (!(s.boss.ringsMask&bit)&&inRing(pb,ring)){
s.boss.ringsMask|=bit;
addScore(s,rules(s).boss.ring,events,'BOSS_RING');
events.push({type:'RING',ringId:ring.id,boss:true,mask:s.boss.ringsMask});
}
});
if (s.boss.ringsMask===A.bosses.common.ringMaskComplete){
s.boss.phase='TRANSITION';
for (const w of s.world.platforms){w.phase='TRANSITION';w.tick=0;}
s._transitionStarted=true;
events.push({type:'BOSS_RINGS_COMPLETE',milestone:s.boss.milestone});
}
}else{
const collected=s.objectives.ringMask;
const next=content.rings.find((r)=>!(collected&(1<<(r.order-1))));
const ascent=ascentMetrics(s,content);
const altitudeOpen=!ascent.active||next?.order<=ascent.allowedOrder;
if (next&&altitudeOpen&&inRing(pb,next)){
s.objectives.ringMask|=1<<(next.order-1);
if (content.ringsProgression) addScore(s,rules(s).ringStep*next.order,events,'RING',{order:next.order});
events.push({type:'RING',ringId:next.id,order:next.order,progression:content.ringsProgression});
if (next.order===content.rings.length){routeComplete=true;s.objectives.ringMask=0;}
}
}
}
if (content.kind!=='BOSS'&&!s.objectives.hostileClear&&s.objectives.spawnCursor===content.rosterList.length&&s.objectives.authorizedActorIds.length===0&&content.rosterList.length>0){
hostileClear=true;
s.objectives.hostileClear=true;
events.push({type:'HOSTILE_CLEAR',progression:content.combatProgression});
}
if (!routeComplete&&!hostileClear) return;
if (s.sim.mode==='ARCADE') return arcadeTransaction(A,s,content,routeComplete,hostileClear,events);
const pre=circuitPre(s);
if (rules(s).carry.enabled!==false&&pre.levelCursor===pre.waveCursor&&content.kind==='NORMAL'&&content.ringsProgression){
if (!routeComplete) return;
hostileClear=true;
}
const lead=Math.max(pre.levelCursor,pre.waveCursor);
const bossFrontier=[5,11,17,23,29].includes(lead)&&!pre.bossCleared[String(lead)];
if (bossFrontier&&pre.levelCursor>pre.waveCursor&&routeComplete){events.push({type:'ROUTE_SCORE_ONLY'});routeComplete=false;}
if (bossFrontier&&pre.waveCursor>pre.levelCursor&&hostileClear){events.push({type:'WAVE_SCORE_ONLY'});hostileClear=false;}
if (!routeComplete&&!hostileClear) return;
const r=reduceCircuit(pre,routeComplete,hostileClear);
if (!r.legal) throw new Error(`CIRCUIT_ILLEGAL ${r.reason}`);
const st=r.state;
s.circuit.levelCursor=st.levelCursor;s.circuit.waveCursor=st.waveCursor;
s.circuit.levelReady=st.levelReady;s.circuit.waveReady=st.waveReady;s.circuit.syncSerial=st.syncSerial;
if (st.score!==pre.score) addScore(s,st.score-pre.score,events,'SYNC');
s.player.wing=st.wing;
for (const e of r.events) events.push({type:e});
if (r.events.includes('BOSS_ENTER')){
s.boss.milestone=st.levelCursor;s.boss.phase='RINGS';s.boss.ringsMask=0;s.boss.refillConsumed=false;s.boss.hits=0;s.boss.hurt=0;
}
s._circuitEvents=r.events;
s._newArena=st.activeContent.arena!==s.world.contentId;
if (content.kind==='NORMAL'&&(s._newArena||r.events.includes('BOSS_ENTER'))) retireSector(A,s,content,events,r.events.includes('BOSS_ENTER'));
if (!s._newArena&&!r.events.includes('BOSS_ENTER')){s.objectives.routeId=st.activeContent.rings;s.objectives.waveId=st.activeContent.wave;}
events.push({type:'CHECKPOINT_REQUEST',reason:'CIRCUIT_TRANSACTION'});
}
function arcadeTransaction(A,s,content,routeComplete,hostileClear,events){
const R=rules(s);
let{course,wave}=parseArcade(s);
if (s.score.legacy) return legacyArcadeTransaction(A,s,content,routeComplete,hostileClear,events);
if (!routeComplete) return;
retireSector(A,s,content,events,false);
if (s.score.stageAwarded<course){s.score.stageAwarded=course;addScore(s,R.arcade.stageClear,events,'STAGE_CLEAR',{stage:course});events.push({type:'COURSE_BONUS',course});}
const next=Math.max(course,wave)+1;
s.objectives.routeId=`ARC_C${next}_R${mod(next-1,8)+1}`;
s.objectives.waveId=`ARC_W${next}`;
events.push({type:'COURSE_ADVANCE',course:next});
events.push({type:'WAVE_ADVANCE',wave:next});
s._newArena=true;
events.push({type:'CHECKPOINT_REQUEST',reason:'ARCADE_TRANSACTION'});
}
function legacyArcadeTransaction(A,s,content,routeComplete,hostileClear,events){
const C=A.sim_constants;
let{course,wave}=parseArcade(s);
if (routeComplete){
const award=`ARC_C${course}`;
if (!s.oneTime.courseAwards.includes(award)){s.oneTime.courseAwards.push(award);addScore(s,C.courseBonusBase,events,'STAGE_CLEAR');events.push({type:'COURSE_BONUS',course});}
course+=1;s.objectives.routeId=`ARC_C${course}_R${mod(course-1,8)+1}`;events.push({type:'COURSE_ADVANCE',course});
}
if (hostileClear){wave+=1;s.objectives.waveId=`ARC_W${wave}`;s.objectives.spawnCursor=0;s.objectives.hostileClear=false;events.push({type:'WAVE_ADVANCE',wave});}
s._arcadeCourseAdvance=routeComplete;
s._arcadeWaveAdvance=hostileClear;
events.push({type:'CHECKPOINT_REQUEST',reason:'ARCADE_TRANSACTION'});
}
function bossStage(A,s,content,events){
if (content.kind!=='BOSS') return;
const rec=content.record,b=s.boss;
if ((b.phase==='TRANSITION'||b.phase==='DUEL')&&!s._transitionStarted){
const t=s.world.platforms[0].tick+1;
for (const w of s.world.platforms) w.tick=t;
if (b.phase==='TRANSITION'){
s._locked=true;
const tr=rec.transition;
if (t===tr.removePlatformsAt){for (const w of s.world.platforms) if (w.id!=='GROUND'){w.collidable=false;w.phase='REMOVED';}events.push({type:'BOSS_PLATFORMS_REMOVED',phaseTick:t});}
if (t===tr.restoreGroundAt){const g=s.world.platforms.find((w)=>w.id==='GROUND');g.collidable=true;g.phase='DUEL_GROUND';events.push({type:'BOSS_GROUND_RESTORED',phaseTick:t});}
if (t===tr.placeActorsAt){
s.player={...emptyPlayer(rec.duel.playerSpawn[0],rec.duel.playerSpawn[1]),wing:s.player.wing};
s.actors=[];
const actor={id:s.sim.nextActorId,kind:'RIVAL',class:'BOSS',ghost:rec.duel.ghost,tier:rec.duel.tier,lifecycle:'MOUNTED',x:px(rec.duel.bossSpawn[0]),y:px(rec.duel.bossSpawn[1]),vx:0,vy:0,facing:-1,phase:0,timer:0,rngDraws:0};
s.sim.nextActorId+=1;s.actors.push(actor);s.objectives.authorizedActorIds=[actor.id];s.objectives.spawnCursor=1;
b.hits=0;b.hurt=0;
events.push({type:'BOSS_ACTORS_PLACED',phaseTick:t,actor:actor.id});
}
if (t>=tr.unlockAt){
b.phase='DUEL';
if (!b.refillConsumed){s.player.wing=rec.duel.wingRefill;b.refillConsumed=true;events.push({type:'WING_REFILL',wing:rec.duel.wingRefill});}
events.push({type:'BOSS_DUEL_UNLOCK',phaseTick:t});
events.push({type:'CHECKPOINT_REQUEST',reason:'BOSS_DUEL'});
}
}
}
}
function transitionsStage(A,s,content,events){
if (s._pendingGameOver){s.sim.shell='GAMEOVER';events.push({type:'GAMEOVER'});events.push({type:'CHECKPOINT_REQUEST',reason:'GAMEOVER'});return;}
if (s._deathThisTick){events.push({type:'RESPAWN_SCHEDULED'});events.push({type:'CHECKPOINT_REQUEST',reason:'DEATH'});}
if (s._bossDefeated){
const m=s.boss.milestone;
s.boss.phase='CLEAR';
if (!s.boss.cleared.includes(m)) s.boss.cleared.push(m);
if (!s.oneTime.bossRewards.includes(m)){
s.oneTime.bossRewards.push(m);
const R=rules(s);
addScore(s,R.boss.clear,events,'BOSS_CLEAR',{milestone:m});
if (s.score.bossClean) addScore(s,R.boss.perfect,events,'BOSS_PERFECT',{milestone:m});
}
events.push({type:'BOSS_CLEAR',milestone:m});
enterCinema(s,m,events);
events.push({type:'CHECKPOINT_REQUEST',reason:'BOSS_CLEAR',forced:true});
return;
}
if (s._circuitEvents&&s._circuitEvents.includes('BOSS_ENTER')){activateArena(A,s,events);events.push({type:'CHECKPOINT_REQUEST',reason:'BOSS_ENTER'});return;}
if (s._newArena){activateArena(A,s,events);events.push({type:'CHECKPOINT_REQUEST',reason:'ARENA_ACTIVATE'});return;}
if (s._arcadeCourseAdvance){const c=arenaContent(A,s);s.world.contentId=c.contentId;s.world.platforms=buildPlatforms(c);events.push({type:'ARENA_ACTIVATE',contentId:c.contentId,audioState:c.audioState});}
if (s._arcadeWaveAdvance){s.actors=[];s.objectives.authorizedActorIds=[];events.push({type:'WAVE_INTRO'});}
}
function applyUnlimitedContinue(state,C){
if (!state||!state.sim||state.sim.shell!=='GAMEOVER') return false;
if (state.sim.mode==='ARCADE') return false;
state.sim.shell='PLAY';
state.sim.lives=C.continueLives;
if (state.score){state.score.continuesUsed+=1;state.score.sectorClean=false;state.score.bossClean=false;state.score.eggChain=0;}
return true;
}
function stepTick(A,s,input=EMPTY_INPUT){
const events=[];
s._C=A.sim_constants;ensureScoreState(s);s._lifecycle=[];s._locked=false;s._deathThisTick=false;s._bossDefeated=false;s._pendingGameOver=false;s._circuitEvents=null;s._newArena=false;s._arcadeWaveAdvance=false;s._arcadeCourseAdvance=false;
const shell=s.sim.shell;
if (shell==='FATAL'||shell==='PAUSE'||shell==='GAMEOVER'||shell==='WINNER'||shell==='ATTRACT'){
return finish(s,events);
}
if (shell==='CINEMA_SKY'){
stepCinema(A,s,input,events);
return finish(s,events);
}
const content=arenaContent(A,s);
if (s.boss.phase==='TRANSITION') s._locked=true;
stageTimers(s);
const pIntent=playerIntent(A,s,input,events);
const intents=aiIntents(A,s,content);
integrateAll(A,s,content,pIntent,intents,events);
joustStage(A,s,content,events);
lifecycleStage(A,s,content,events);
objectivesStage(A,s,content,events);
bossStage(A,s,content,events);
transitionsStage(A,s,content,events);
return finish(s,events);
}
function finish(s,events){
const committed=events.map((e)=>({...e,serial:++s.sim.eventSerial}));
const checkpoint=committed.filter((e)=>e.type==='CHECKPOINT_REQUEST').map((e)=>e.reason);
s.sim.tick+=1;
for (const k of Object.keys(s)) if (k.startsWith('_')) delete s[k];
const d=digest({state:s,events:committed});
return{events:committed,checkpoint,digest:d};
}
function payloadOf(s){
const copy=structuredClone(s);
for (const k of Object.keys(copy)) if (k.startsWith('_')) delete copy[k];
return copy;
}
function startCampaign(A,s,events=[]){
s.sim.shell='PLAY';
s.circuit={levelCursor:1,waveCursor:1,levelReady:false,waveReady:false,syncSerial:0};
activateArena(A,s,events);
return events;
}
function startArcade(A,s,events=[]){
s.sim.shell='PLAY';
s.objectives.routeId='ARC_C1_R1';s.objectives.waveId='ARC_W1';
activateArena(A,s,events);
return events;
}
return{stepTick,startCampaign,startArcade,payloadOf,EMPTY_INPUT,applyUnlimitedContinue,retireSector,ensureScoreState,humanIntent,integrateHuman};
})();
__modules[13]=(()=>{
const{newState}=__modules[5];
const{stepTick,startCampaign,startArcade,payloadOf,EMPTY_INPUT}=__modules[12];
const{digest}=__modules[1];
const{seedState}=__modules[3];
class Game{
constructor(A,{mode='CAMPAIGN',seed=1,state=null}={}){
this.A=A;
this.C=A.sim_constants;
this.state=state||newState(mode,seed,this.C);
this.seed=seed;
this.events=[];
this.chain=digest({seed:seedState(seed),mode});
this.tickDigest=null;
}
start(){
const ev=this.state.sim.mode==='ARCADE'?startArcade(this.A,this.state):startCampaign(this.A,this.state);
this.pendingEvents=ev;
return ev;
}
tick(input=EMPTY_INPUT){
const r=stepTick(this.A,this.state,input);
if (this.pendingEvents&&this.pendingEvents.length){r.events.unshift(...this.pendingEvents.map((e)=>({...e,serial:0})));this.pendingEvents=null;}
this.tickDigest=r.digest;
this.chain=digest({prev:this.chain,tick:r.digest});
this.events=r.events;
return r;
}
payload(){return payloadOf(this.state);}
stateDigest(){return digest(this.payload());}
}
return{Game};
})();
__modules[41]=(()=>{
const{digest}=__modules[1];
const{seedState}=__modules[3];
const{px,mod,wrappedDelta}=__modules[4];
const{newState,entityBox,BIRD_BOX,LANCE_Y_SUB,RESPAWN_HIDDEN_TICKS,SHIMMER_TICKS}=__modules[5];
const{arenaContent,stepWorld,buildPlatforms}=__modules[7];
const{inRing,boxesOverlap,standingPlatform}=__modules[8];
const{rivalIntent}=__modules[9];
const{humanIntent,integrateHuman}=__modules[12];
const VS_VERSION=1;
const VS_COUNTDOWN_TICKS=180;
const VS_MAX_TICKS=60*240;
const AI=2;
const START_DX=44;
const KIND_CODE={LEGACY:0,LEFT:1,RIGHT:2,STRAIGHT:3};
const KIND_NAME=['LEGACY','LEFT','RIGHT','STRAIGHT'];
function encodeInput(f){
if (!f) return 0;
let b=0;
if (f.left) b|=1;
if (f.right) b|=2;
if (f.flapEdge) b|=4|((KIND_CODE[f.flapKind||'LEGACY']||0)<<5);
if (f.flapEdge&&f.chordEdge) b|=8;
if (f.dartEdge) b|=16|(f.dartSide==='LEFT'?128:0);
return b;
}
function decodeInput(b){
b|=0;
const flapEdge=!!(b&4),dartEdge=!!(b&16);
return{left:!!(b&1),right:!!(b&2),flapEdge,flapKind:flapEdge?KIND_NAME[(b>>5)&3]:null,chordEdge:flapEdge&&!!(b&8),
flapHeld:false,dartEdge,dartSide:dartEdge?((b&128)?'LEFT':'RIGHT'):null};
}
function predictInput(last){return (last|0)&3;}
const contentCache=new WeakMap();
function vsContent(A){
let c=contentCache.get(A);
if (!c){
const probe=newState('ARCADE',1,A.sim_constants);
probe.objectives.routeId='ARC_C1_R1';probe.objectives.waveId='ARC_W1';
c=arenaContent(A,probe);
contentCache.set(A,c);
}
return c;
}
const frameAt=(cx,cy)=>[mod(cx-14,256),cy-19];
function startSpots(A){
const r1=vsContent(A).rings[0];
const[cx,cy]=r1.center;
return[frameAt(cx-START_DX,cy),frameAt(cx+START_DX,cy),frameAt(cx+128,cy)];
}
function spawnSpots(A){
return[...startSpots(A),...vsContent(A).enemySpawns.map(([x,y])=>[x,y])];
}
function freshBird(C,[x,y],facing){
return{x:px(x),y:px(y),vx:0,vy:0,groundedPlatformId:null,facing,wing:C.wingMax??64,flapCooldown:0,footingTicks:0,
lavaPhase:'SAFE',lavaTicks:0,invulnerableTicks:0,hidden:0,rings:0,deaths:0,jousts:0};
}
function newVsState(A,seed){
const C=A.sim_constants,c=vsContent(A),spots=startSpots(A);
const birds=spots.map((sp,i)=>freshBird(C,sp,i===1?-1:1));
Object.assign(birds[AI],{phase:0,timer:0,rngDraws:0,tier:3,cls:'HUNTER',ghost:'BLINKY'});
birds[AI].facing=-1;
return{
vs:VS_VERSION,tick:0,phase:'COUNTDOWN',countdown:VS_COUNTDOWN_TICKS,winner:-1,endReason:'',eventSerial:0,
rng:{gameplayState:seedState(seed>>>0)},
world:{contentId:c.contentId,lavaY:px(c.hazard&&c.hazard.lavaY!=null?c.hazard.lavaY:C.lavaY),platforms:buildPlatforms(c)},
birds,
};
}
const present=(b)=>b.hidden===0;
const active=(b)=>b.hidden===0&&b.invulnerableTicks<=SHIMMER_TICKS;
function kill(s,i,cause,events){
const b=s.birds[i];
b.hidden=RESPAWN_HIDDEN_TICKS;b.deaths+=1;
b.vx=0;b.vy=0;b.groundedPlatformId=null;b.lavaPhase='SAFE';b.lavaTicks=0;b.flapCooldown=0;b.invulnerableTicks=0;
events.push({type:'VS_DEATH',who:i,cause});
}
function respawn(A,s,i,events){
const C=A.sim_constants,b=s.birds[i],spots=spawnSpots(A);
let best=0,bestD=-1;
spots.forEach(([x,y],k)=>{
let d=Infinity;
s.birds.forEach((o,j)=>{
if (j===i||!present(o)) return;
const dx=wrappedDelta(px(x),o.x)>>8,dy=(o.y>>8)-y;
d=Math.min(d,dx*dx+dy*dy);
});
if (d>bestD){bestD=d;best=k;}
});
const[x,y]=spots[best];
Object.assign(b,{x:px(x),y:px(y),vx:0,vy:0,groundedPlatformId:null,facing:x<128?1:-1,wing:C.wingMax??64,
flapCooldown:0,footingTicks:0,lavaPhase:'SAFE',lavaTicks:0,invulnerableTicks:SHIMMER_TICKS,hidden:0});
if (i===AI){b.phase=0;b.timer=0;}
events.push({type:'VS_RESPAWN',who:i});
}
function aiInput(A,s){
const ai=s.birds[AI];
if (!active(ai)) return 0;
let target=-1,bestD=Infinity;
for (let i=0;i<2;i++){
const h=s.birds[i];
if (!present(h)) continue;
const dx=wrappedDelta(ai.x,h.x)>>8,dy=(h.y-ai.y)>>8,d=dx*dx+dy*dy;
if (d<bestD||(d===bestD&&(s.tick&1)===i)){bestD=d;target=i;}
}
const prey=target>=0?s.birds[target]:s.birds[0];
const view={player:prey,rng:s.rng,world:s.world};
const intent=rivalIntent(A,view,ai,ai.cls,vsContent(A).enemySpawns[0],target>=0&&active(prey));
return encodeInput({left:intent.dir<0,right:intent.dir>0,flapEdge:intent.flap,flapKind:'LEGACY'});
}
function stepVs(A,s,inputs){
const C=A.sim_constants,content=vsContent(A),events=[];
if (s.phase==='OVER') return finishVs(s,events);
const previous=new Map(s.world.platforms.map((p)=>[p.id,p.rect.slice()]));
const footing=s.birds.map((b)=>(present(b)&&b.groundedPlatformId?b.groundedPlatformId:null));
stepWorld(A,s,content);
if (s.phase==='COUNTDOWN'){
s.countdown-=1;
if (s.countdown%60===0&&s.countdown>0) events.push({type:'VS_COUNT',n:s.countdown/60});
if (s.countdown<=0){s.phase='PLAY';events.push({type:'VS_GO'});}
return finishVs(s,events);
}
s.birds.forEach((b,i)=>{
if (b.hidden>0){b.hidden-=1;if (b.hidden===0) respawn(A,s,i,events);return;}
if (b.flapCooldown>0) b.flapCooldown-=1;
if (b.invulnerableTicks>0) b.invulnerableTicks-=1;
if (b.lavaPhase==='SINK'&&b.lavaTicks>0) b.lavaTicks-=1;
if (i===AI&&b.timer<1200) b.timer+=1;
});
const bytes=[inputs[0]|0,inputs[1]|0,aiInput(A,s)];
const intents=s.birds.map((b,i)=>{
const ev=[];
const it=humanIntent(C,b,active(b),decodeInput(bytes[i]),ev);
for (const e of ev) events.push({...e,type:'VS_'+e.type,who:i});
return it;
});
const now=new Map(s.world.platforms.map((p)=>[p.id,p]));
s.birds.forEach((b,i)=>{
const id=footing[i];if (!id||!present(b)) return;
const before=previous.get(id),after=now.get(id);
if (!before||!after||!after.collidable) return;
b.x=mod(b.x+(after.rect[0]-before[0])*256,256*256);
b.y+=(after.rect[1]-before[1])*256;
});
s.birds.forEach((b,i)=>{
if (!active(b)) return;
const targets=s.birds.map((o,j)=>({x:o.x,y:o.y,id:j+1,ok:j!==i&&active(o)})).filter((o)=>o.ok);
const ev=[];
const sink=integrateHuman(C,b,intents[i],s.world,targets,ev);
for (const e of ev) events.push({...e,type:'VS_'+e.type,who:i});
if (sink==='SINK_DEATH') kill(s,i,'LAVA',events);
});
const lost=new Set();
for (let i=0;i<3;i++) for (let j=i+1;j<3;j++){
const a=s.birds[i],b=s.birds[j];
if (lost.has(i)||lost.has(j)||!active(a)||!active(b)) continue;
if (!boxesOverlap(entityBox(a.x,a.y,BIRD_BOX),entityBox(b.x,b.y,BIRD_BOX))) continue;
const delta=(a.y+LANCE_Y_SUB)-(b.y+LANCE_Y_SUB);
let loser=Math.abs(delta)<=C.lanceTieBandSubpx?-1:delta>0?i:j;
if (loser>=0&&s.birds[loser].invulnerableTicks>0) loser=-1;
const dx=wrappedDelta(a.x,b.x);
a.vx=dx>=0?-C.lanceBounceVx:C.lanceBounceVx;b.vx=-a.vx;
if (loser<0){
a.vy=C.lanceBounceVy;b.vy=C.lanceBounceVy;a.groundedPlatformId=null;b.groundedPlatformId=null;
events.push({type:'VS_CLASH',a:i,b:j});
}else{
const winner=loser===i?j:i;
s.birds[winner].vy=C.lanceBounceVy;s.birds[winner].groundedPlatformId=null;s.birds[winner].jousts+=1;
lost.add(loser);
events.push({type:'VS_JOUST',winner,loser});
kill(s,loser,'JOUST',events);
}
}
const finished=[];
for (let i=0;i<2;i++){
const b=s.birds[i];
if (!active(b)||b.rings>=content.rings.length) continue;
const ring=content.rings[b.rings];
if (inRing(entityBox(b.x,b.y,BIRD_BOX),ring)){
b.rings+=1;
events.push({type:'VS_RING',who:i,order:b.rings,total:content.rings.length});
if (b.rings===content.rings.length) finished.push(i);
}
}
if (finished.length) endMatch(s,finished.length===2?-2:finished[0],'ROUTE',events);
else if (s.tick+1>=VS_COUNTDOWN_TICKS+VS_MAX_TICKS){
const[a,b]=[s.birds[0].rings,s.birds[1].rings];
endMatch(s,a===b?-2:a>b?0:1,'TIME',events);
}
return finishVs(s,events);
}
function endMatch(s,winner,reason,events){
s.phase='OVER';s.winner=winner;s.endReason=reason;
events.push({type:'VS_END',winner,reason});
}
function finishVs(s,events){
const committed=events.map((e)=>({...e,serial:++s.eventSerial,tick:s.tick}));
s.tick+=1;
return{events:committed};
}
function vsCompat(A){
const c=vsContent(A);
return digest({vs:VS_VERSION,constants:A.sim_constants,rings:c.rings,platforms:c.platforms,spawns:c.enemySpawns,hazard:c.hazard});
}
class VsGame{
constructor(A,{seed=1,state=null}={}){this.A=A;this.state=state||newVsState(A,seed);}
tick(inputs){return stepVs(this.A,this.state,inputs);}
snapshot(){return structuredClone(this.state);}
restore(snap){this.state=structuredClone(snap);}
digest(){return digest(this.state);}
}
return{VsGame,vsCompat,newVsState,stepVs,encodeInput,decodeInput,predictInput,vsContent,startSpots,spawnSpots,VS_VERSION,VS_COUNTDOWN_TICKS,VS_MAX_TICKS,AI};
})();
__modules[14]=(()=>{
const CINEMA_PANELS_PATH='generated/cinema-panels.webp';
const PANEL_SCALE=2;
const PANEL_W=256,WIDE_H=146,TALL_H=448;
const PANEL_SHEET_W=2048*PANEL_SCALE,PANEL_SHEET_H=1024*PANEL_SCALE;
const TALL_PANELS=Object.freeze(['C1_S5_CUT','C2_S1_WIDE','C3_S2_BIND','C4_S6_CUT','C5_S2_INSIDE','C5_S5_BRANCH']);
const WIDE_PANELS=Object.freeze([
'C1_S1_WIDE','C1_S2_CLOSE','C1_S3_SIGNAL','C1_S4_OPPOSITION',
'C2_S2_ALIGN','C2_S3_RELIEF','C2_S4_CLOSE','C2_S5_OVERLAY',
'C3_S1_SPLASH','C3_S3_OVERLOAD','C3_S4_BLACK_BREAK','C3_S5_PRESENT','C3_S6_LOOK',
'C4_S1_WIDE','C4_S2_REFUSAL','C4_S3_MEMORY','C4_S4_RELEASE','C4_S5_CONSENT',
'C5_S1_VICTORY','C5_S3_CONTROL','C5_S4_REFUSAL','C5_S6_CODA',
'P_S1_BREAK','P_S2_RIDERS','P_S3_BOND','P_S4_FIRST_RING',
]);
const PANEL_VARIANTS=Object.freeze({
C1_S2_CLOSE_B:Object.freeze({base:'C1_S2_CLOSE',rect:[128,34,32,24]}),
C1_S4_OPPOSITION_B:Object.freeze({base:'C1_S4_OPPOSITION',rect:[160,14,64,50]}),
C2_S4_CLOSE_B:Object.freeze({base:'C2_S4_CLOSE',rect:[60,6,150,106]}),
C3_S3_OVERLOAD_B:Object.freeze({base:'C3_S3_OVERLOAD',rect:[0,8,220,138]}),
C3_S6_LOOK_B:Object.freeze({base:'C3_S6_LOOK',rect:[86,36,66,26]}),
C4_S2_REFUSAL_B:Object.freeze({base:'C4_S2_REFUSAL',rect:[134,56,48,22]}),
C4_S4_RELEASE_B:Object.freeze({base:'C4_S4_RELEASE',rect:[120,40,60,80]}),
C5_S3_CONTROL_B:Object.freeze({base:'C5_S3_CONTROL',rect:[138,20,54,42]}),
});
function buildLayout(){
const S=PANEL_SCALE,PW=PANEL_W*S,WH=WIDE_H*S,TH=TALL_H*S;
const at={};
TALL_PANELS.forEach((id,i)=>{at[id]=[i*PW,0,PW,TH];});
const free=[];
let k=0;
for (let c=6;c<8;c++) for (let r=0;r<3;r++) at[WIDE_PANELS[k++]]=[c*PW,r*WH,PW,WH];
free.push([6*PW,3*WH,2*PW,TH-3*WH]);
for (let i=0;k<WIDE_PANELS.length;i++,k++) at[WIDE_PANELS[k]]=[(i%8)*PW,TH+Math.floor(i/8)*WH,PW,WH];
const used=WIDE_PANELS.length-6,rows=Math.ceil(used/8),last=used-(rows-1)*8;
if (last<8) free.push([last*PW,TH+(rows-1)*WH,(8-last)*PW,WH]);
const top=TH+rows*WH;
if (top<PANEL_SHEET_H) free.push([0,top,PANEL_SHEET_W,PANEL_SHEET_H-top]);
const order=Object.keys(PANEL_VARIANTS).sort((a,b)=>{
const[,,aw,ah]=PANEL_VARIANTS[a].rect,[,,bw,bh]=PANEL_VARIANTS[b].rect;
return bw*bh-aw*ah||(a<b?-1:1);
});
for (const id of order){
const w=PANEL_VARIANTS[id].rect[2]*S,h=PANEL_VARIANTS[id].rect[3]*S;
const slot=free.findIndex(([,,fw,fh])=>fw>=w&&fh>=h);
if (slot<0) throw new Error(`cinema panel sheet: no room for ${id}`);
const[fx,fy,fw,fh]=free[slot];
at[id]=[fx,fy,w,h];
free.splice(slot,1,[fx+w,fy,fw-w,h],[fx,fy+h,fw,fh-h]);
for (let i=free.length-1;i>=0;i--) if (free[i][2]<=0||free[i][3]<=0) free.splice(i,1);
}
return Object.freeze(Object.fromEntries(Object.entries(at).map(([id,r])=>[id,Object.freeze(r)])));
}
const PANEL_LAYOUT=buildLayout();
function panelsPresent(sheet){
const have=new Set();
if (!sheet||sheet.w!==PANEL_SHEET_W||sheet.h!==PANEL_SHEET_H) return have;
const opaque=(x,y)=>sheet.p[(y*PANEL_SHEET_W+x)*4+3]===255;
for (const id of[...TALL_PANELS,...WIDE_PANELS]){
const[x,y,w,h]=PANEL_LAYOUT[id];
if (opaque(x,y)&&opaque(x+w-1,y)&&opaque(x,y+h-1)&&opaque(x+w-1,y+h-1)&&opaque(x+(w>>1),y+(h>>1))) have.add(id);
}
for (const[id,v] of Object.entries(PANEL_VARIANTS)){
if (!have.has(v.base)) continue;
const[x,y,w,h]=PANEL_LAYOUT[id];
let any=false;
for (let yy=y;yy<y+h&&!any;yy++) for (let xx=x;xx<x+w;xx++) if (opaque(xx,yy)){any=true;break;}
if (any) have.add(id);
}
return have;
}
return{PANEL_SHEET_W,PANEL_SHEET_H,CINEMA_PANELS_PATH,panelsPresent,PANEL_LAYOUT,PANEL_VARIANTS,PANEL_W,WIDE_H,TALL_H,TALL_PANELS,PANEL_SCALE};
})();
__modules[15]=(()=>{
const BIRD_INKS=Object.freeze([
{shadow:[6,34,48],mid:[14,132,166],light:[60,216,238],highlight:[214,250,255],body:[238,244,250],bodyMix:0.70,horn:[246,206,92],hornMix:1.00,hornRamp:0},
{shadow:[28,14,9],mid:[104,62,32],light:[158,96,44],highlight:[214,162,110],body:[164,134,104],bodyMix:0.62,horn:[192,54,40],hornMix:0.95,hornRamp:0},
{shadow:[52,12,10],mid:[188,28,28],light:[232,70,44],highlight:[252,168,140],body:[154,112,96],bodyMix:0.62,horn:[240,142,40],hornMix:0.95,hornRamp:0},
{shadow:[68,14,10],mid:[224,104,16],light:[255,162,40],highlight:[255,220,156],body:[182,144,108],bodyMix:0.62,horn:[120,78,44],hornMix:0.95,hornRamp:0},
{shadow:[58,22,10],mid:[192,148,26],light:[252,216,74],highlight:[255,246,196],body:[232,206,146],bodyMix:0.84,horn:[214,74,34],hornMix:0.90,hornRamp:0},
{shadow:[96,44,12],mid:[230,168,52],light:[255,226,110],highlight:[255,252,224],body:[255,240,190],bodyMix:0.92,horn:[236,110,40],hornMix:0.95,hornRamp:0},
{shadow:[34,18,8],mid:[128,74,28],light:[226,168,58],highlight:[110,236,255],body:[250,204,80],bodyMix:0.96,horn:[214,44,36],hornMix:1.00,hornRamp:0},
]);
const ARCADE_PLAYER_GLOW=[110,245,255];
const PLAYER_BLUES=Object.freeze([
{mid:[14,132,166],light:[60,216,238]},
{mid:[22,96,190],light:[86,170,255]},
{mid:[58,74,196],light:[130,146,255]},
]);
const BLUE_CYCLE_RATE=1/540;
const BLUE_CYCLE_TRAVEL=1/1400;
const JOUSTER_LOOK=Object.freeze([
{plume:[150,206,226],rim:[120,246,255]},
{plume:[150,106,66],rim:[255,146,56]},
{plume:[170,40,44],rim:[255,86,70]},
{plume:[112,66,172],rim:[224,128,255]},
{plume:[190,136,36],rim:[255,226,120]},
{plume:[190,136,36],rim:[255,226,120]},
{plume:[176,214,228],rim:[120,246,255]},
]);
const v3=(rgb)=>`vec3f(${rgb.map((n)=>`${n}.0`).join(',')})/255.0`;
const inkLiteral=(k)=>`Ink(${v3(k.shadow)},${v3(k.mid)},${v3(k.light)},${v3(k.highlight)},${v3(k.body)},${k.bodyMix.toFixed(2)},${v3(k.horn)},${k.hornMix.toFixed(2)},${k.hornRamp},${v3(JOUSTER_LOOK[BIRD_INKS.indexOf(k)].plume)},${v3(JOUSTER_LOOK[BIRD_INKS.indexOf(k)].rim)})`;
const WAR_BIRD_PALETTE_WGSL=`
struct Ink { shadow: vec3f, mid: vec3f, light: vec3f, highlight: vec3f, body: vec3f, bodyMix: f32, horn: vec3f, hornMix: f32, hornRamp: i32, plume: vec3f, rim: vec3f }
fn birdInkFor(classId:i32) -> Ink {
  var k = ${inkLiteral(BIRD_INKS[0])};
  ${BIRD_INKS.slice(1).map((k,i)=>`if(classId==${i+1}) { k = ${inkLiteral(k)}; }`).join('\n  ')}
  return k;
}
// Three stops on a seamless loop. Rendering only: the phase comes from the
// render tick, which no simulation reads.
fn cycle3(a:vec3f, b:vec3f, c:vec3f, phase:f32) -> vec3f {
  let u = fract(phase) * 3.0;
  let i = floor(u);
  let f = smoothstep(0.0, 1.0, u - i);
  var p = a; var q = b;
  if (i > 1.5) { p = c; q = a; }
  else if (i > 0.5) { p = b; q = c; }
  return mix(p, q, f);
}
fn birdRamp(k:Ink, t:f32) -> vec3f {
  let lowc = mix(k.shadow, k.mid, smoothstep(0.06, 0.5, t));
  let highc = mix(k.mid, k.light, smoothstep(0.5, 0.95, t));
  return select(highc, lowc, t < 0.5);
}
fn birdInk(c:vec3f, classId:i32, phase:f32, jouster:f32) -> vec3f {
  var k = birdInkFor(classId);
  if (classId == 0) {
    k.mid = cycle3(${v3(PLAYER_BLUES[0].mid)},${v3(PLAYER_BLUES[1].mid)},${v3(PLAYER_BLUES[2].mid)}, phase);
    k.light = cycle3(${v3(PLAYER_BLUES[0].light)},${v3(PLAYER_BLUES[1].light)},${v3(PLAYER_BLUES[2].light)}, phase);
  }
  let mx = max(c.r, max(c.g, c.b));
  let d = mx - min(c.r, min(c.g, c.b));
  let sat = select(0.0, d / max(mx, 0.0001), mx > 0.0001);
  let dd = max(d, 0.00001);
  var h = ((c.r - c.g) / dd + 4.0) * 60.0;
  if (mx == c.g) { h = ((c.b - c.r) / dd + 2.0) * 60.0; }
  if (mx == c.r) { h = ((c.g - c.b) / dd) * 60.0; }
  if (h > 180.0) { h = h - 360.0; }
  let wF = (1.0 - smoothstep(14.0, 26.0, abs(h))) * smoothstep(0.30, 0.55, sat);
  let hornHue = smoothstep(16.0, 24.0, h) * (1.0 - smoothstep(58.0, 70.0, h));
  let wH = hornHue * max(smoothstep(0.40, 0.55, c.r - c.b), smoothstep(0.24, 0.34, c.g - c.b)) * (1.0 - wF);
  let bodyHue = smoothstep(12.0, 20.0, h) * (1.0 - smoothstep(62.0, 72.0, h));
  let wB = smoothstep(0.06, 0.14, sat) * smoothstep(0.08, 0.16, mx) * bodyHue * (1.0 - wF) * (1.0 - wH);
  let L = dot(c, vec3f(0.2126, 0.7152, 0.0722));
  var o = c;
  if (k.bodyMix > 0.0) { o = mix(o, clamp(k.body * (L / 0.80), vec3f(0.0), vec3f(1.0)), wB * k.bodyMix); }
  if (k.hornRamp == 1) { o = mix(o, birdRamp(k, mx), wH); }
  else if (k.hornMix > 0.0) { o = mix(o, clamp(k.horn * (L / 0.55) * 0.85, vec3f(0.0), vec3f(1.0)), wH * k.hornMix); }
  let feather = mix(birdRamp(k, mx), k.highlight, smoothstep(0.2, 0.6, 1.0 - sat) * smoothstep(0.6, 1.0, mx));
  var res = mix(o, feather, wF);
  if (classId == 6) { res = mix(res, ${v3(ARCADE_PLAYER_GLOW)}, wF * smoothstep(0.985, 0.998, mx) * smoothstep(0.72, 0.80, sat)); }
  // 3.4 jouster marks (markJousterRims): plumage (0,0,v) takes the class
  // plume at shade v, the outer outline (0,1,0) the class rim.
  let pl = jouster * step(c.r + c.g, 0.002) * step(0.1, c.b);
  let rm = jouster * step(0.9, c.g) * step(c.r, 0.1) * step(c.b, 0.1);
  res = mix(mix(res, k.plume * (0.40 + 0.95 * c.b), pl), k.rim, rm);
  return clamp(res, vec3f(0.0), vec3f(1.0));
}
`;
return{WAR_BIRD_PALETTE_WGSL,BLUE_CYCLE_RATE,BLUE_CYCLE_TRAVEL};
})();
__modules[16]=(()=>{
const{PANEL_SHEET_W,PANEL_SHEET_H}=__modules[14];
const{WAR_BIRD_PALETTE_WGSL,BLUE_CYCLE_RATE,BLUE_CYCLE_TRAVEL}=__modules[15];
const WATER_BLOOM='0.340';
const WATER_GLINT='0.950';
const WATER_TINT='vec3f(0.42, 0.88, 1.0)';
const LOGICAL_W=256,LOGICAL_H=384,SCENE_SCALE=3,SCENE_W=LOGICAL_W*SCENE_SCALE,SCENE_H=LOGICAL_H*SCENE_SCALE,LOGICAL_FORMAT='rgba8unorm',INSTANCE_STRIDE=40,ATLAS_SIZE=2048,MAX_INSTANCES=4096;
const WORLD_SCALE=3,WORLD_PLATE_W=256*WORLD_SCALE,WORLD_PLATE_H=768*WORLD_SCALE;
const WORLD_TEX_W=WORLD_PLATE_W*2,WORLD_TEX_H=WORLD_PLATE_H;
const MATERIAL_WORLD=8;
const WATER_MASK_W=WORLD_TEX_W/4,WATER_MASK_H=WORLD_TEX_H/4;
const RIDER_TEX_W=1536,RIDER_TEX_H=384;
const MATERIAL_RIDER=9;
const MATERIAL_ARCADE_PLAYER=10;
const MATERIAL_ARCADE_ISLAND=11;
const GLOBE_MAP_W=1536,GLOBE_MAP_H=768;
const SPRITE_WGSL=`struct Frame { logical: vec2f, invAtlas: vec2f, invPanels: vec2f, invWorld: vec2f, invBird: vec2f, invRider: vec2f, tick: vec2f, globe: vec4f, fx: vec4f, look: vec4f }
struct VOut { @builtin(position) position: vec4f, @location(0) uv: vec2f, @location(1) uvPanel: vec2f, @location(2) @interpolate(flat) material: f32, @location(3) uvWorld: vec2f, @location(4) uvBird: vec2f, @location(5) uvRider: vec2f }
@group(0) @binding(0) var<uniform> frame: Frame;
@group(0) @binding(1) var atlas: texture_2d<f32>;
@group(0) @binding(2) var nearestSampler: sampler;
@group(0) @binding(3) var panels: texture_2d<f32>;
@group(0) @binding(4) var world: texture_2d<f32>;
@group(0) @binding(5) var waterMask: texture_2d<f32>;
@group(0) @binding(6) var linearSampler: sampler;
@group(0) @binding(7) var bird: texture_2d<f32>;
@group(0) @binding(8) var rider: texture_2d<f32>;
@group(0) @binding(9) var globeMap: texture_2d<f32>;
@vertex fn vs(@location(0) corner: vec2f, @location(1) uvCorner: vec2f, @location(2) dst: vec4f, @location(3) src: vec4f, @location(4) zAndFlags: vec2f) -> VOut {
  let pixel = dst.xy + corner * dst.zw;
  let ndc = vec2f(pixel.x / frame.logical.x * 2.0 - 1.0, 1.0 - pixel.y / frame.logical.y * 2.0);
  var out: VOut;
  out.position = vec4f(ndc, clamp(zAndFlags.x, 0.0, 1.0), 1.0);
  let texel = src.xy + uvCorner * src.zw + vec2f(0.5);
  out.uv = texel * frame.invAtlas;
  out.uvPanel = texel * frame.invPanels;
  out.uvWorld = texel * frame.invWorld;
  out.uvBird = texel * frame.invBird;
  out.uvRider = texel * frame.invRider;
  out.material = zAndFlags.y;
  return out;
}
${WAR_BIRD_PALETTE_WGSL}
// Light on moving water, added over the plate rather than distorting it. Three
// wave trains at different scales and speeds give a swell with no visible
// period; the glints are where two of them agree, which is what the eye reads
// as flow. Everything scales by how lit the texel already is, so water in
// shadow stays dark and the sea does not glow at night.
fn waterLight(base: vec3f, wet: f32, wp: vec2f, t: f32) -> vec3f {
  // Wavelengths are in plate texels, and the rear plate is 1:1 with the scene,
  // so 0.085 rad/texel is a ~74 px band -- caustic scale. The first pass used
  // 0.021, a 300 px band, which read as slow blobs rather than moving water.
  // Deliberately incommensurate frequencies: two clean gratings beat into a
  // visible lattice, and the first tune at this scale looked like a regular
  // field of dots rather than water.
  let a = sin(wp.x * 0.0913 + wp.y * 0.0531 - t * 0.0900);
  let b = sin(wp.x * 0.0347 - wp.y * 0.1187 + t * 0.0600);
  let c = sin((wp.x - wp.y * 0.61) * 0.0193 + t * 0.0350);
  let swell = a * 0.46 + b * 0.34 + c * 0.20;
  // Glints are softened (power 4 rather than 5, so they are larger and fewer)
  // and their density is modulated by the slow band, which leaves open water
  // and sparkling water instead of an even field of identical dots. Gating them
  // on the fast swell instead killed them almost entirely -- the terms rarely
  // peak together.
  let crest = pow(max(0.0, a * b), 4.0) * (0.45 + 0.55 * max(0.0, c));
  let lit = smoothstep(0.10, 0.52, dot(base, vec3f(0.2126, 0.7152, 0.0722)));
  // pow() on the swell pushes the troughs toward nothing, so the light reads as
  // crests travelling over dark water rather than as an even lift.
  let glow = pow(swell * 0.5 + 0.5, 1.6) * ${WATER_BLOOM} + crest * ${WATER_GLINT};
  return base + ${WATER_TINT} * (glow * wet * lit);
}
// 2.3 ARCADE GLOBE: the battle station in the Arcade rear plate turns. The
// plate's own painted lighting (gold sun side, blue night side) stays fixed;
// only the surface detail -- grid, trench, dish -- rotates under it, read from
// a 360-degree longitude map built at boot from the same graded plate
// (buildArcadeGlobe). R = detail ratio / 4, GBA = the smooth painted light at
// the unrotated longitude. globe = (centre x, centre y, radius, radians/tick)
// in rear-plate texels; w = 0 disables it (any non-Arcade world).
// 3.1 COLOUR mode (radius negative): a neon wire globe has no smooth painted
// light to keep, and light x detail would grey its cyan and gold. The map's
// GBA then hold the plate's own colour at every longitude, and the whole
// surface -- lines, gold continent -- turns together.
fn globeSurface(base: vec3f, wp: vec2f, t: f32) -> vec3f {
  if (wp.x >= ${WORLD_PLATE_W}.0) { return base; }
  let colourMode = frame.globe.z < 0.0;
  let n = (wp - frame.globe.xy) / abs(frame.globe.z);
  if (dot(n, n) >= 1.0) { return base; }
  let lat = asin(clamp(n.y, -1.0, 1.0));
  let lon = asin(clamp(n.x / max(cos(lat), 0.0001), -1.0, 1.0));
  let dims = vec2f(textureDimensions(globeMap));
  let vy = clamp(i32((lat / ${Math.PI} + 0.5) * dims.y), 0, i32(dims.y) - 1);
  let spin = fract(frame.look.y);   // 3.5: the moon's turn, advanced by the music (moonPhase)
  let uL = clamp(i32((lon / ${2*Math.PI} + 0.5) * dims.x), 0, i32(dims.x) - 1);
  let uD = i32(fract(lon / ${2*Math.PI} + 0.5 - spin) * dims.x) % i32(dims.x);
  if (colourMode) { return textureLoad(globeMap, vec2i(uD, vy), 0).gba; }
  let light = textureLoad(globeMap, vec2i(uL, vy), 0).gba;
  let detail = textureLoad(globeMap, vec2i(uD, vy), 0).r * 4.0;
  return clamp(light * detail, vec3f(0.0), vec3f(1.0));
}
// 3.1 ARCADE AMBIENT (Pass 4 motion + light plan). fx = (on, rear horizon row,
// music beat 0..1, motion 0|1). Everything multiplies brightness only, never
// moves or adds geometry, and scales to nothing under Reduce Motion (w = 0).
//   rear sky  : ~15% of stars twinkle, 1.8-4.5 s, +-8-12%, calmer mid-corridor
//   rear floor: one broad energy band travels toward the viewer every 6.5 s, +13%
//   near      : a faint shimmer climbs the cyan edges every 8 s, +7%
//   islands   : red fissures and cyan cores pulse with the music, +4-12%
// Hash without trig (Hoskins hash12): cheap on every GPU.
fn fxHash(p: vec2f) -> f32 {
  var p3 = fract(vec3f(p.x, p.y, p.x) * 0.1031);
  p3 = p3 + dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
// sin(pi x) on [0,1) as a parabola (within 6%), and a sine-shaped wave on a
// cycle: no trig in the per-texel path.
fn hump(x: f32) -> f32 { return 4.0 * x * (1.0 - x); }
fn wave1(x: f32) -> f32 { let f = fract(x); return select(-hump(f * 2.0 - 1.0), hump(f * 2.0), f < 0.5); }
fn arcadeAmbient(base: vec3f, wp: vec2f, t: f32) -> vec3f {
  // Branch-free and short: every term is weighted by a 0/1 mask, so every GPU
  // (and software rasteriser) runs it as one straight line.
  let hi = max(base.r, max(base.g, base.b));
  let horizon = frame.fx.y;
  let rear = step(wp.x, ${WORLD_PLATE_W}.0 - 1.0);
  // near: a faint shimmer climbs the cyan edges (8 s)
  let cyan = clamp((min(base.g, base.b) - base.r - 0.12) * 3.333, 0.0, 1.0);
  let sn = hump(fract(t * 0.0020833 + wp.y * 0.0011111)); let sn2 = sn * sn; let sn4 = sn2 * sn2;
  let nearGain = (1.0 - rear) * 0.07 * sn4 * sn4 * sn2 * cyan;
  // rear floor: one broad energy band travelling toward the viewer (6.5 s)
  let sf = hump(fract(t * 0.0025641 - (wp.y - horizon) * 0.0013158)); let sf2 = sf * sf;
  let floorGain = rear * step(horizon, wp.y) * 0.13 * sf2 * sf2 * sf2 * clamp((hi - 0.18) * 3.125, 0.0, 1.0);
  // rear sky: ~15% of stars twinkle (1.8-4.5 s, 8-12%), none on the moon
  let h = fxHash(floor(wp * 0.1));
  let g = wp - frame.globe.xy;
  let star = rear * step(wp.y, horizon - 330.0) * step(0.42, hi) * step(20000.0, dot(g, g)) * step(h, 0.15);
  let k = h * 6.6667;                    // 0..1 within the chosen 15%
  let starGain = star * (0.08 + 0.04 * k) * wave1(t / ((1.8 + 2.7 * fract(k * 7.13)) * 60.0) + fract(k * 13.7));
  return base * (1.0 + frame.fx.w * (nearGain + floorGain + starGain));
}
fn arcadeIsland(c: vec3f, t: f32) -> vec3f {
  let red = select(0.0, 1.0, c.r > 0.55 && c.g < 0.40 && c.r > c.b * 1.4);
  let core = clamp((min(c.g, c.b) - c.r - 0.15) / 0.35, 0.0, 1.0) * step(0.6, c.b);
  let amp = frame.fx.w * (0.04 + 0.08 * frame.fx.z) * (0.75 + 0.25 * wave1(t * 0.0079577));
  return c * (1.0 + amp * max(red, core));
}
@fragment fn fs(in: VOut) -> @location(0) vec4f {
  // 2.4: one texture read per fragment. Through 2.3 every fragment sampled
  // all five textures (atlas, bird, rider, panels, world) and then picked one,
  // so the two full-screen world plates alone paid for ten reads a texel.
  // Branching on the (flat, per-instance) material and reading only the
  // texture it names is bit-identical: every sampler is nearest and no texture
  // has mips, so textureSampleLevel(.., 0) returns exactly what textureSample
  // did -- and it is legal inside non-uniform control flow.
  var c: vec4f;
  if (in.material == 8.0) {
    // A world plate: painted art, never recoloured. The linear sampler is what
    // expands the quarter-scale water mask.
    var w = textureSampleLevel(world, nearestSampler, in.uvWorld, 0.0);
    let wet = textureSampleLevel(waterMask, linearSampler, in.uvWorld, 0.0).r;
    if (wet > 0.004) {
      let wp = in.uvWorld * vec2f(${WORLD_TEX_W}.0, ${WORLD_TEX_H}.0);
      w = vec4f(waterLight(w.rgb, wet, wp, frame.tick.y), w.a);
    }
    if (frame.globe.w > 0.0) { w = vec4f(globeSurface(w.rgb, in.uvWorld * vec2f(${WORLD_TEX_W}.0, ${WORLD_TEX_H}.0), frame.tick.y), w.a); }
    if (frame.fx.x > 0.0) {
      let wp = in.uvWorld * vec2f(${WORLD_TEX_W}.0, ${WORLD_TEX_H}.0);
      w = vec4f(arcadeAmbient(w.rgb, wp, frame.tick.y), w.a);
    }
    c = w;
  } else if ((in.material > 1.5 && in.material < 7.5) || in.material == ${MATERIAL_ARCADE_PLAYER}.0) {
    // 2..7 are the six bird inks, 10 the Arcade jouster player (ink 6).
    let b = textureSampleLevel(bird, nearestSampler, in.uvBird, 0.0);
    let phase = frame.tick.y * ${BLUE_CYCLE_RATE} + in.position.y * ${BLUE_CYCLE_TRAVEL};
    let inkId = select(i32(in.material) - 2, 6, in.material == ${MATERIAL_ARCADE_PLAYER}.0);
    c = vec4f(birdInk(b.rgb, inkId, phase, frame.look.x), b.a);
  } else if (in.material == 1.0) {
    c = textureSampleLevel(panels, nearestSampler, in.uvPanel, 0.0);
  } else if (in.material == ${MATERIAL_RIDER}.0) {
    c = textureSampleLevel(rider, nearestSampler, in.uvRider, 0.0);
  } else if (in.material == ${MATERIAL_ARCADE_ISLAND}.0) {
    c = textureSampleLevel(atlas, nearestSampler, in.uv, 0.0);
    if (frame.fx.x > 0.0) { c = vec4f(arcadeIsland(c.rgb, frame.tick.y), c.a); }
  } else {
    c = textureSampleLevel(atlas, nearestSampler, in.uv, 0.0);
  }
  if (c.a < 0.0039215686) { discard; }
  return vec4f(c.rgb * c.a, c.a);
}`;
const BLOOM_GAIN='1.8',BLOOM_BRIGHT_GAIN='1.0',BLOOM_BRIGHT_KNEE=Object.freeze(['0.40','0.90']);
const POST_EXPOSURE='1.8',POST_WHITE='1.6',POST_LOW_RUNG_GLOW='0.35';
const POST_WGSL=`struct Post { viewport: vec2f, scene: vec2f, logical: vec2f, quality: u32, tick: u32, fx: vec4f, music: vec4f }
// The post pass reads exclusively through textureLoad, so it declares no
// sampler. A declared-but-unused sampler is dropped from the 'auto' bind group
// layout, and supplying one anyway invalidates the bind group and every command
// buffer built from it. Binding 1 stays vacant to keep the uniform at 2.
@group(0) @binding(0) var logicalTexture: texture_2d<f32>;
@group(0) @binding(2) var<uniform> post: Post;
@group(0) @binding(3) var glowTex: texture_2d<f32>;
@group(0) @binding(4) var glowSampler: sampler;
struct VOut { @builtin(position) p: vec4f, @location(0) uv: vec2f }
@vertex fn vs(@builtin(vertex_index) i:u32)->VOut { var pos=array<vec2f,3>(vec2f(-1.0,-1.0),vec2f(3.0,-1.0),vec2f(-1.0,3.0));var o:VOut;o.p=vec4f(pos[i],0.0,1.0);o.uv=vec2f((pos[i].x+1.0)*0.5,1.0-(pos[i].y+1.0)*0.5);return o; }
fn emission(c:vec3f,pulse:vec3f)->vec3f {
  let hi=max(c.r,max(c.g,c.b));
  let cyan=select(0.0,hi,c.b>0.34&&c.g>0.27&&c.b>c.r*1.20);
  // The green ceiling excludes the gold platform caps from red/orange bloom.
  let lava=select(0.0,hi,c.r>0.42&&c.g<0.48&&c.r>c.g*1.25&&c.r>c.b*1.45);
  let violet=select(0.0,hi,c.b>0.35&&c.r>0.35&&c.g<c.r*0.78);
  return c*(cyan*pulse.x+lava*pulse.y+violet*pulse.z);
}
fn glowAt(p:vec2i,pulse:vec3f)->vec3f {
  let dims=vec2i(post.scene);
  let q=clamp(p,vec2i(0),dims-vec2i(1));
  let c=textureLoad(logicalTexture,q,0).rgb;
  return emission(c,pulse);
}
@fragment fn fs(i:VOut)->@location(0) vec4f {
  let dims=vec2i(post.scene);
  let p=clamp(vec2i(floor(i.uv*post.scene)),vec2i(0),dims-vec2i(1));
  var c=textureLoad(logicalTexture,p,0);
  if(post.quality==0u){ let x0=c.rgb*${POST_EXPOSURE}; return vec4f(clamp(x0*(vec3f(1.0)+x0/(${POST_WHITE}*${POST_WHITE}))/(vec3f(1.0)+x0),vec3f(0.0),vec3f(1.0)),c.a); }
  let t=f32(post.tick&511u)*0.012271846;
  let pulse=vec3f(post.fx.x*(0.84+0.16*sin(t+f32(p.x+p.y)*0.018)),post.fx.y*(0.82+0.18*sin(t*0.73+f32(p.y)*0.025)),post.fx.z*(0.84+0.16*sin(t*1.13)));
  // Multi-radius contour halation: reduced quality keeps the tight four-tap
  // halo; full quality adds mid, diagonal, far and atmospheric bloom fields.
  var glow=(glowAt(p+vec2i(2,0),pulse)+glowAt(p+vec2i(-2,0),pulse)+glowAt(p+vec2i(0,2),pulse)+glowAt(p+vec2i(0,-2),pulse))*0.068;
  // 2.4: the mid, diagonal, far and atmospheric fields were 16 more full-res
  // reads a pixel (21 in all, ~1.1 billion a second at 60 Hz). They are now
  // computed once at quarter resolution (POST_EMIT_WGSL, POST_GLOW_WGSL) and
  // read back here with one filtered sample.
  if(post.quality>1u){ glow+=textureSampleLevel(glowTex,glowSampler,i.uv,0.0).rgb*${BLOOM_GAIN}; }
  glow+=emission(c.rgb,pulse)*(0.10+post.fx.w*0.10);
  if(post.quality<=1u){ glow+=emission(c.rgb,pulse)*${POST_LOW_RUNG_GLOW}; }
  // 3.5: the bloom swells on the music's beats (music.x, 0..1, decays between).
  glow*=1.0+0.6*post.music.x;
  let scale=max(1u,u32(round(post.scene.y/post.logical.y)));
  let scan=select(1.0,0.93,(u32(p.y)%scale)==scale-1u);
  let centered=i.uv*2.0-vec2f(1.0);
  let vignette=1.0-0.10*smoothstep(0.38,1.12,dot(centered,centered));
  let x=(c.rgb+glow)*${POST_EXPOSURE};
  let toned=x*(vec3f(1.0)+x/(${POST_WHITE}*${POST_WHITE}))/(vec3f(1.0)+x);
  return vec4f(clamp(toned*scan*vignette,vec3f(0.0),vec3f(1.0)),c.a);
}`;
const POST_SHARED_WGSL=POST_WGSL.slice(0,POST_WGSL.indexOf('@fragment'));
const POST_EMIT_WGSL=`${POST_SHARED_WGSL}
@fragment fn fs(i:VOut)->@location(0) vec4f {
  let dims=vec2i(post.scene);
  let base=vec2i(floor(i.p.xy))*4;
  let pc=base+vec2i(2);
  let t=f32(post.tick&511u)*0.012271846;
  let pulse=vec3f(post.fx.x*(0.84+0.16*sin(t+f32(pc.x+pc.y)*0.018)),post.fx.y*(0.82+0.18*sin(t*0.73+f32(pc.y)*0.025)),post.fx.z*(0.84+0.16*sin(t*1.13)));
  var e=vec3f(0.0);
  for(var y=0;y<4;y++){ for(var x=0;x<4;x++){
    let c=textureLoad(logicalTexture,min(base+vec2i(x,y),dims-vec2i(1)),0).rgb;
    // 2.7 bright-pass: beyond the cyan/lava/violet emitters, anything lit --
    // gold rims, stars, sprites, the moon -- blooms too, weighted by how far
    // it rises above the threshold, with the post pulse riding on it.
    let L=dot(c,vec3f(0.2126,0.7152,0.0722));
    e+=emission(c,pulse)+c*smoothstep(${BLOOM_BRIGHT_KNEE[0]},${BLOOM_BRIGHT_KNEE[1]},L)*${BLOOM_BRIGHT_GAIN}*(0.85+0.15*pulse.x);
  } }
  return vec4f(e*0.0625,1.0);
}`;
const POST_GLOW_WGSL=`@group(0) @binding(0) var emitTex: texture_2d<f32>;
@group(0) @binding(1) var emitSampler: sampler;
struct VOut { @builtin(position) p: vec4f, @location(0) uv: vec2f }
@vertex fn vs(@builtin(vertex_index) i:u32)->VOut { var pos=array<vec2f,3>(vec2f(-1.0,-1.0),vec2f(3.0,-1.0),vec2f(-1.0,3.0));var o:VOut;o.p=vec4f(pos[i],0.0,1.0);o.uv=vec2f((pos[i].x+1.0)*0.5,1.0-(pos[i].y+1.0)*0.5);return o; }
fn tap(uv:vec2f,o:vec2f,px:vec2f)->vec3f { return textureSampleLevel(emitTex,emitSampler,uv+o*px,0.0).rgb; }
fn ring(uv:vec2f,r:f32,px:vec2f)->vec3f { return tap(uv,vec2f(r,0.0),px)+tap(uv,vec2f(-r,0.0),px)+tap(uv,vec2f(0.0,r),px)+tap(uv,vec2f(0.0,-r),px); }
@fragment fn fs(i:VOut)->@location(0) vec4f {
  let px=1.0/vec2f(textureDimensions(emitTex));
  let uv=i.p.xy*px;
  var g=ring(uv,1.5,px)*0.028;
  g+=(tap(uv,vec2f(1.25,1.25),px)+tap(uv,vec2f(-1.25,1.25),px)+tap(uv,vec2f(1.25,-1.25),px)+tap(uv,vec2f(-1.25,-1.25),px))*0.022;
  g+=ring(uv,3.75,px)*0.014;
  g+=ring(uv,8.25,px)*0.007;
  // 2.7: a wide atmospheric field, so the whole screen breathes with light.
  g+=(ring(uv,16.0,px)+tap(uv,vec2f(11.3,11.3),px)+tap(uv,vec2f(-11.3,11.3),px)+tap(uv,vec2f(11.3,-11.3),px)+tap(uv,vec2f(-11.3,-11.3),px))*0.0045;
  return vec4f(g,1.0);
}`;
const BLOOM_DIV=4,BLOOM_FORMAT='rgba16float';
class FatalError extends Error{constructor(code,detail){super(code);this.code=code;this.detail=detail;}}
async function createRenderer(canvas,{atlasPixels,birdPixels,riderPixels,onFatal,onRecovered,onLost}){
if (!globalThis.isSecureContext) throw new FatalError('FATAL_SECURE_CONTEXT','Insecure context');
if (!navigator.gpu) throw new FatalError('FATAL_WEBGPU_UNAVAILABLE','navigator.gpu is absent');
const context=canvas.getContext('webgpu');
if (!context) throw new FatalError('FATAL_WEBGPU_CONTEXT','canvas.getContext(webgpu) returned null');
let lossCount=0,device=null,adapter=null,R=null,state='init',canvasFormat=null,quality=2;
let instanceData=new Float32Array((MAX_INSTANCES*INSTANCE_STRIDE)/4);
let instanceCount=0;
let uploadPending=true;
let birdUploadPending=true;
let riderUploadPending=true;
let globeMap=null,globeUploadPending=false;
const globeData=new Float32Array(4);
const fxData=new Float32Array(4);
const lookData=new Float32Array(4);
let panelSurface=null,panelPending=false,panelReload=null,panelsUploaded=false;
let worldSurface=null,worldPending=false,maskSurface=null;
let tickSeen=0;
const overflow={count:0,worst:0,lastTick:-1};
const uniformData=new Float32Array(16);
const tickData=new Float32Array(2);
const postData=new ArrayBuffer(64);
const postF=new Float32Array(postData),postU=new Uint32Array(postData);
async function compile(d,code,label){
const m=d.createShaderModule({code,label});
const info=await m.getCompilationInfo();
const errors=info.messages.filter((x)=>x.type==='error');
if (errors.length) throw new FatalError('FATAL_SHADER',`${label}: ${errors.map((e)=>`${e.lineNum}:${e.linePos} ${e.message}`).join('; ')}`);
return m;
}
async function acquire(){
adapter=await navigator.gpu.requestAdapter({powerPreference:'high-performance'});
if (!adapter) throw new FatalError('FATAL_ADAPTER','requestAdapter returned null');
device=await adapter.requestDevice({requiredFeatures:[],requiredLimits:{}});
if (!device) throw new FatalError('FATAL_DEVICE','requestDevice returned null');
const acquiredDevice=device;
acquiredDevice.addEventListener('uncapturederror',(event)=>{
if (device!==acquiredDevice||state==='destroyed'||state==='fatal') return;
if (typeof event.preventDefault==='function') event.preventDefault();
state='fatal';
const detail=event.error&&event.error.message?event.error.message:'Uncaptured WebGPU validation error';
onFatal&&onFatal(new FatalError('FATAL_GPU_VALIDATION',detail));
});
canvasFormat=navigator.gpu.getPreferredCanvasFormat();
context.configure({device,format:canvasFormat,alphaMode:'premultiplied'});
device.lost.then(async (info)=>{
if (state==='destroyed'||state==='fatal') return;
lossCount+=1;
state='recovering';
onLost&&onLost({lossCount,reason:info.reason,message:info.message});
if (lossCount>1){state='fatal';onFatal&&onFatal(new FatalError('FATAL_GPU_LOST_TWICE',info.message));return;}
try{await acquire();await build();uploadPending=true;birdUploadPending=true;riderUploadPending=true;globeUploadPending=!!globeMap;state='ready';onRecovered&&onRecovered({lossCount});}
catch (e){state='fatal';onFatal&&onFatal(e instanceof FatalError?e:new FatalError('FATAL_RECOVERY',String(e)));}
});
}
async function build(){
const d=device;
d.pushErrorScope('validation');
let scopeOpen=true;
try{
const spriteModule=await compile(d,SPRITE_WGSL,'sprite.wgsl');
const postModule=await compile(d,POST_WGSL,'post.wgsl');
const emitModule=await compile(d,POST_EMIT_WGSL,'post-emit.wgsl');
const glowModule=await compile(d,POST_GLOW_WGSL,'post-glow.wgsl');
const logical=d.createTexture({size:[SCENE_W,SCENE_H,1],format:LOGICAL_FORMAT,usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_SRC});
const depth=d.createTexture({size:[SCENE_W,SCENE_H,1],format:'depth24plus',usage:GPUTextureUsage.RENDER_ATTACHMENT});
const sampler=d.createSampler({magFilter:'nearest',minFilter:'nearest',mipmapFilter:'nearest'});
const quad=d.createBuffer({size:64,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});
d.queue.writeBuffer(quad,0,new Float32Array([0,0,0,0,1,0,1,0,0,1,0,1,1,1,1,1]));
const instances=d.createBuffer({size:INSTANCE_STRIDE*MAX_INSTANCES,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});
const uniform=d.createBuffer({size:112,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
const postUniform=d.createBuffer({size:64,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
const atlas=d.createTexture({size:[ATLAS_SIZE,ATLAS_SIZE,1],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
const birdTexture=d.createTexture({size:[1536,1152,1],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
const riderTexture=d.createTexture({size:[RIDER_TEX_W,RIDER_TEX_H,1],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
const globeTexture=d.createTexture({size:[GLOBE_MAP_W,GLOBE_MAP_H,1],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
const panels=d.createTexture({size:[PANEL_SHEET_W,PANEL_SHEET_H,1],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
const world=d.createTexture({size:[WORLD_TEX_W,WORLD_TEX_H,1],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
const waterMask=d.createTexture({size:[WATER_MASK_W,WATER_MASK_H,1],format:'r8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
const linearSampler=d.createSampler({magFilter:'linear',minFilter:'linear'});
const sprite=d.createRenderPipeline({
layout:'auto',
vertex:{module:spriteModule,entryPoint:'vs',buffers:[
{arrayStride:16,attributes:[{shaderLocation:0,offset:0,format:'float32x2'},{shaderLocation:1,offset:8,format:'float32x2'}]},
{arrayStride:INSTANCE_STRIDE,stepMode:'instance',attributes:[{shaderLocation:2,offset:0,format:'float32x4'},{shaderLocation:3,offset:16,format:'float32x4'},{shaderLocation:4,offset:32,format:'float32x2'}]}]},
fragment:{module:spriteModule,entryPoint:'fs',targets:[{format:LOGICAL_FORMAT,blend:{color:{srcFactor:'one',dstFactor:'one-minus-src-alpha',operation:'add'},alpha:{srcFactor:'one',dstFactor:'one-minus-src-alpha',operation:'add'}}}]},
primitive:{topology:'triangle-strip',stripIndexFormat:'uint16'},
depthStencil:{format:'depth24plus',depthWriteEnabled:true,depthCompare:'less-equal'},
});
const post=d.createRenderPipeline({layout:'auto',vertex:{module:postModule,entryPoint:'vs'},fragment:{module:postModule,entryPoint:'fs',targets:[{format:canvasFormat}]},primitive:{topology:'triangle-list'}});
const bloomSize=[Math.ceil(SCENE_W/BLOOM_DIV),Math.ceil(SCENE_H/BLOOM_DIV),1];
const emitTex=d.createTexture({size:bloomSize,format:BLOOM_FORMAT,usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.TEXTURE_BINDING});
const glowTex=d.createTexture({size:bloomSize,format:BLOOM_FORMAT,usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.TEXTURE_BINDING});
const emitPipe=d.createRenderPipeline({layout:'auto',vertex:{module:emitModule,entryPoint:'vs'},fragment:{module:emitModule,entryPoint:'fs',targets:[{format:BLOOM_FORMAT}]},primitive:{topology:'triangle-list'}});
const glowPipe=d.createRenderPipeline({layout:'auto',vertex:{module:glowModule,entryPoint:'vs'},fragment:{module:glowModule,entryPoint:'fs',targets:[{format:BLOOM_FORMAT}]},primitive:{topology:'triangle-list'}});
const spriteBind=d.createBindGroup({layout:sprite.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:uniform}},{binding:1,resource:atlas.createView()},{binding:2,resource:sampler},{binding:3,resource:panels.createView()},{binding:4,resource:world.createView()},{binding:5,resource:waterMask.createView()},{binding:6,resource:linearSampler},{binding:7,resource:birdTexture.createView()},{binding:8,resource:riderTexture.createView()},{binding:9,resource:globeTexture.createView()}]});
const postBind=d.createBindGroup({layout:post.getBindGroupLayout(0),entries:[{binding:0,resource:logical.createView()},{binding:2,resource:{buffer:postUniform}},{binding:3,resource:glowTex.createView()},{binding:4,resource:linearSampler}]});
const emitBind=d.createBindGroup({layout:emitPipe.getBindGroupLayout(0),entries:[{binding:0,resource:logical.createView()},{binding:2,resource:{buffer:postUniform}}]});
const glowBind=d.createBindGroup({layout:glowPipe.getBindGroupLayout(0),entries:[{binding:0,resource:emitTex.createView()},{binding:1,resource:linearSampler}]});
const validation=await d.popErrorScope();
scopeOpen=false;
if (validation) throw new FatalError('FATAL_GPU_VALIDATION',`renderer build: ${validation.message}`);
uniformData.set([LOGICAL_W,LOGICAL_H,1/ATLAS_SIZE,1/ATLAS_SIZE,1/PANEL_SHEET_W,1/PANEL_SHEET_H,1/WORLD_TEX_W,1/WORLD_TEX_H,1/1536,1/1152,1/RIDER_TEX_W,1/RIDER_TEX_H]);
d.queue.writeBuffer(uniform,0,uniformData);
d.queue.writeBuffer(uniform,64,globeData);
d.queue.writeBuffer(uniform,80,fxData);
d.queue.writeBuffer(uniform,96,lookData);
R={logical,depth,sampler,linearSampler,quad,instances,uniform,postUniform,atlas,birdTexture,riderTexture,globeTexture,panels,world,waterMask,sprite,post,spriteBind,postBind,emitTex,glowTex,emitPipe,glowPipe,emitBind,glowBind};
panelPending=!!panelSurface;
if (!panelSurface&&panelReload) panelReload().then((surface)=>{if (surface&&surface.w===PANEL_SHEET_W&&surface.h===PANEL_SHEET_H){panelSurface=surface;panelPending=true;}}).catch(()=>{});
worldPending=!!worldSurface;
}catch (error){
if (scopeOpen) await d.popErrorScope().catch(()=>null);
throw error;
}
}
function uploadAtlas(pixels,x=0,y=0,w=ATLAS_SIZE,h=ATLAS_SIZE){
if (!device||!R) return;
device.queue.writeTexture({texture:R.atlas,origin:[x,y,0]},pixels,{bytesPerRow:w*4,rowsPerImage:h},[w,h,1]);
}
function uploadPanels(surface,reload=null){
panelReload=reload;
if (!surface||surface.w!==PANEL_SHEET_W||surface.h!==PANEL_SHEET_H) return false;
panelSurface=surface;panelPending=true;
return true;
}
function uploadWorld(surface,mask=null){
if (!surface||surface.w!==WORLD_TEX_W||surface.h!==WORLD_TEX_H) return false;
if (mask&&(mask.w!==WATER_MASK_W||mask.h!==WATER_MASK_H)) return false;
worldSurface=surface;maskSurface=mask||maskSurface;worldPending=true;
return true;
}
function resize(cssW,cssH){
const fit=Math.min(cssW/LOGICAL_W,cssH/LOGICAL_H);
const displayW=Math.max(2,Math.floor(LOGICAL_W*fit/2)*2);
const displayH=displayW*LOGICAL_H/LOGICAL_W;
canvas.style.width=`${displayW}px`;
canvas.style.height=`${displayH}px`;
canvas.width=SCENE_W;
canvas.height=SCENE_H;
return fit;
}
function setInstances(list){
if (list.length>MAX_INSTANCES){
overflow.count+=1;
overflow.worst=Math.max(overflow.worst,list.length);
overflow.lastTick=tickSeen;
}
instanceCount=Math.min(list.length,MAX_INSTANCES);
for (let i=0;i<instanceCount;i++){
const o=i*10,it=list[i];
instanceData[o]=it.x;instanceData[o+1]=it.y;instanceData[o+2]=it.w;instanceData[o+3]=it.h;
if (it.sw>=0){instanceData[o+4]=it.sx;instanceData[o+6]=it.sw>1?it.sw-1:0;}
else{instanceData[o+4]=it.sx-1;instanceData[o+6]=-(-it.sw-1);}
instanceData[o+5]=it.sy;instanceData[o+7]=it.sh>1?it.sh-1:0;
instanceData[o+8]=it.z;instanceData[o+9]=it.flags||0;
}
}
function setGlobe(map,params=null){
if (map&&(map.w!==GLOBE_MAP_W||map.h!==GLOBE_MAP_H||!params)) return false;
if (map&&map!==globeMap){globeMap=map;globeUploadPending=true;}
globeData.set(map?params:[0,0,1,0]);
if (device&&R) device.queue.writeBuffer(R.uniform,64,globeData);
return true;
}
function setArcadeFx(horizon=null){fxData[0]=horizon===null?0:1;fxData[1]=horizon===null?0:horizon;return true;}
function setBird(pixels,jouster=false){
if (!pixels||pixels.w!==1536||pixels.h!==1152) return false;
birdPixels=pixels;birdUploadPending=true;
lookData[0]=jouster?1:0;
if (device&&R) device.queue.writeBuffer(R.uniform,96,lookData);
return true;
}
function frame(tick,effects={},clear=[0.027,0.075,0.122,1]){
if (state!=='ready'||!device||!R) return false;
tickSeen=tick;
const d=device;
if (uploadPending){uploadAtlas(atlasPixels.p);uploadPending=false;}
if (birdUploadPending){d.queue.writeTexture({texture:R.birdTexture},birdPixels.p,{bytesPerRow:1536*4,rowsPerImage:1152},[1536,1152,1]);birdUploadPending=false;}
if (globeUploadPending&&globeMap){d.queue.writeTexture({texture:R.globeTexture},globeMap.p,{bytesPerRow:GLOBE_MAP_W*4,rowsPerImage:GLOBE_MAP_H},[GLOBE_MAP_W,GLOBE_MAP_H,1]);globeUploadPending=false;}
if (riderUploadPending){d.queue.writeTexture({texture:R.riderTexture},riderPixels.p,{bytesPerRow:RIDER_TEX_W*4,rowsPerImage:RIDER_TEX_H},[RIDER_TEX_W,RIDER_TEX_H,1]);riderUploadPending=false;}
if (panelPending&&panelSurface){d.queue.writeTexture({texture:R.panels},panelSurface.p,{bytesPerRow:PANEL_SHEET_W*4,rowsPerImage:PANEL_SHEET_H},[PANEL_SHEET_W,PANEL_SHEET_H,1]);panelPending=false;panelsUploaded=true;if (panelReload) panelSurface=null;}
if (worldPending&&worldSurface){
d.queue.writeTexture({texture:R.world},worldSurface.p,{bytesPerRow:WORLD_TEX_W*4,rowsPerImage:WORLD_TEX_H},[WORLD_TEX_W,WORLD_TEX_H,1]);
if (maskSurface) d.queue.writeTexture({texture:R.waterMask},maskSurface.p,{bytesPerRow:WATER_MASK_W,rowsPerImage:WATER_MASK_H},[WATER_MASK_W,WATER_MASK_H,1]);
worldPending=false;
}
d.queue.writeBuffer(R.instances,0,instanceData,0,instanceCount*10);
tickData[0]=tick;
tickData[1]=Number.isFinite(effects.ambientTick)?effects.ambientTick:tick;
d.queue.writeBuffer(R.uniform,48,tickData);
fxData[2]=Number.isFinite(effects.beat)?Math.max(0,Math.min(1,effects.beat)):0;
fxData[3]=effects.motion===false?0:1;
d.queue.writeBuffer(R.uniform,80,fxData);
lookData[1]=Number.isFinite(effects.moonPhase)?effects.moonPhase%1:(tick*globeData[3]/(2*Math.PI))%1;
d.queue.writeBuffer(R.uniform,96,lookData);
postF[0]=canvas.width;postF[1]=canvas.height;postF[2]=SCENE_W;postF[3]=SCENE_H;postF[4]=LOGICAL_W;postF[5]=LOGICAL_H;postU[6]=quality;postU[7]=(Number.isFinite(effects.ambientTick)?effects.ambientTick:tick)>>>0;
postF[8]=Number.isFinite(effects.cyan)?effects.cyan:1;
postF[9]=Number.isFinite(effects.lava)?effects.lava:1;
postF[10]=Number.isFinite(effects.violet)?effects.violet:1;
postF[11]=Number.isFinite(effects.impact)?effects.impact:0;
postF[12]=Number.isFinite(effects.bloomBeat)?Math.max(0,Math.min(1,effects.bloomBeat)):0;
d.queue.writeBuffer(R.postUniform,0,postData);
const enc=d.createCommandEncoder();
const pass=enc.beginRenderPass({colorAttachments:[{view:R.logical.createView(),clearValue:{r:clear[0],g:clear[1],b:clear[2],a:1},loadOp:'clear',storeOp:'store'}],depthStencilAttachment:{view:R.depth.createView(),depthClearValue:1,depthLoadOp:'clear',depthStoreOp:'store'}});
pass.setPipeline(R.sprite);pass.setBindGroup(0,R.spriteBind);pass.setVertexBuffer(0,R.quad);pass.setVertexBuffer(1,R.instances);
if (instanceCount>0) pass.draw(4,instanceCount);
pass.end();
if (quality>1){
const e=enc.beginRenderPass({colorAttachments:[{view:R.emitTex.createView(),clearValue:{r:0,g:0,b:0,a:1},loadOp:'clear',storeOp:'store'}]});
e.setPipeline(R.emitPipe);e.setBindGroup(0,R.emitBind);e.draw(3,1);e.end();
const g=enc.beginRenderPass({colorAttachments:[{view:R.glowTex.createView(),clearValue:{r:0,g:0,b:0,a:1},loadOp:'clear',storeOp:'store'}]});
g.setPipeline(R.glowPipe);g.setBindGroup(0,R.glowBind);g.draw(3,1);g.end();
}
const post=enc.beginRenderPass({colorAttachments:[{view:context.getCurrentTexture().createView(),clearValue:{r:0,g:0,b:0,a:1},loadOp:'clear',storeOp:'store'}]});
post.setPipeline(R.post);post.setBindGroup(0,R.postBind);post.draw(3,1);post.end();
d.queue.submit([enc.finish()]);
return true;
}
async function readScene3x(){
if (state!=='ready') return null;
const d=device;
const bytesPerRow=SCENE_W*4;
const buf=d.createBuffer({size:bytesPerRow*SCENE_H,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
const enc=d.createCommandEncoder();
enc.copyTextureToBuffer({texture:R.logical},{buffer:buf,bytesPerRow,rowsPerImage:SCENE_H},[SCENE_W,SCENE_H,1]);
d.queue.submit([enc.finish()]);
await buf.mapAsync(GPUMapMode.READ);
const hi=new Uint8Array(buf.getMappedRange());
const out=hi.slice(0,SCENE_W*SCENE_H*4);
buf.unmap();buf.destroy();
return out;
}
async function readLogical(){
const hi=await readScene3x();
if (!hi) return null;
const out=new Uint8Array(LOGICAL_W*LOGICAL_H*4);
for (let y=0;y<LOGICAL_H;y++) for (let x=0;x<LOGICAL_W;x++){
const si=((y*SCENE_SCALE+1)*SCENE_W+x*SCENE_SCALE+1)*4;
out.set(hi.subarray(si,si+4),(y*LOGICAL_W+x)*4);
}
return out;
}
await acquire();
await build();
state='ready';
return{
get state(){return state;},get lossCount(){return lossCount;},get device(){return device;},get quality(){return quality;},
get instanceOverflow(){return{...overflow,cap:MAX_INSTANCES};},
get instanceCount(){return instanceCount;},
setQuality(q){quality=Math.max(0,Math.min(2,q|0));},
resize,setInstances,frame,readLogical,readScene3x,uploadAtlas,setBird,setGlobe,setArcadeFx,uploadPanels,uploadWorld,get panelsReady(){return panelsUploaded||!!panelSurface;},
simulateDeviceLoss(){if (device) device.destroy();},get worldReady(){return!!worldSurface;},
markAtlasDirty(){uploadPending=true;},markWorldDirty(){worldPending=!!worldSurface;},
simulateLoss(){if (device) device.destroy();},
destroy(){state='destroyed';if (device) device.destroy();},
};
}
return{createRenderer,FatalError,ATLAS_SIZE,WORLD_SCALE,WORLD_PLATE_W,WORLD_PLATE_H,WORLD_TEX_W,WORLD_TEX_H,MATERIAL_WORLD,RIDER_TEX_W,RIDER_TEX_H,MATERIAL_RIDER,MATERIAL_ARCADE_PLAYER,MATERIAL_ARCADE_ISLAND,GLOBE_MAP_W,GLOBE_MAP_H};
})();
__modules[17]=(()=>{
function surface(w,h,rgba=[0,0,0,0]){
const p=new Uint8Array(w*h*4);
for (let i=0;i<w*h;i++) p.set(rgba,i*4);
return{w,h,p};
}
function color(hex,a=255){
const s=hex.replace('#','');
return[parseInt(s.slice(0,2),16),parseInt(s.slice(2,4),16),parseInt(s.slice(4,6),16),a];
}
function pixel(s,x,y,c){
x=Math.floor(x);y=Math.floor(y);
if (x<0||y<0||x>=s.w||y>=s.h) return;
s.p.set(c,(y*s.w+x)*4);
}
function rect(s,x,y,w,h,c){
for (let yy=Math.max(0,y);yy<Math.min(s.h,y+h);yy++) for (let xx=Math.max(0,x);xx<Math.min(s.w,x+w);xx++) pixel(s,xx,yy,c);
}
function circle(s,cx,cy,r,c,thick=1){
const r2=r*r,inner=(r-thick)*(r-thick);
for (let y=-r;y<=r;y++) for (let x=-r;x<=r;x++){const d=x*x+y*y;if (d<=r2&&d>=inner) pixel(s,cx+x,cy+y,c);}
}
return{surface,color,rect,circle};
})();
__modules[18]=(()=>{
const ISLAND_SHEET=Object.freeze({w:1920,h:480});
const ISLAND_VARIANTS=Object.freeze([
{id:'SMALL',x:0,y:0,w:168,h:120,capTop:6},
{id:'MEDIUM',x:180,y:0,w:210,h:144,capTop:6},
{id:'LARGE',x:402,y:0,w:246,h:168,capTop:6},
{id:'WIDE',x:660,y:0,w:294,h:150,capTop:6},
{id:'TALL_SPIRE',x:966,y:0,w:174,h:228,capTop:6},
{id:'RUINED_ARCH',x:1152,y:0,w:234,h:174,capTop:12},
{id:'BOSS',x:1398,y:0,w:240,h:180,capTop:6},
{id:'GROUND_BAY',x:1650,y:0,w:192,h:120,capTop:6},
].map(Object.freeze));
function platformHash(platform){
let h=17;
for (const c of platform.id||'') h=(h*33+c.charCodeAt(0))&255;
return h;
}
function islandFamily(platform){
const w=platform.rect[2];
if (platform.id==='GROUND'||w>=200) return 'BASE_GROUND';
if (platform.id.startsWith('BOSS_')) return 'BOSS_DUEL';
return w<=64?'SMALL':w<=76?'MEDIUM':w<=90?'LARGE':'WIDE';
}
function canOverlap(a,b,amp){
const ax=a.rect[0],bx=b.rect[0];
const envelope=(p)=>p.motion==='MOVE_X'?amp:p.motion&&typeof p.motion==='object'&&(p.motion.profile==='DRIFT_X_SOFT'||p.motion.profile==='HOLD_SHIFT_X')?p.motion.amplitude||0:0;
const aa=envelope(a),ba=envelope(b);
for (let shift=-256;shift<=256;shift+=256)
if (ax-aa<bx+shift+b.rect[2]+ba&&ax+a.rect[2]+aa>bx+shift-ba) return true;
return false;
}
function visualClearanceBelow(platform,content,scaleY=1){
let gap=Infinity;
const amp=content.hazard?.amplitude||0;
const low=platform.rect[1]+(platform.motion==='GROW'?amp:0);
for (const other of content.platforms){
if (other.id===platform.id||other.rect[1]<=platform.rect[1]) continue;
if (canOverlap(platform,other,amp)) gap=Math.min(gap,(other.rect[1]-low)*scaleY-4);
}
return Math.max(0,gap);
}
const ACCENT_MASTERS=Object.freeze([]);
const LOOK_SCALE=Object.freeze([0.72,1.4]);
function lookCost(p,m,mirror,clearance,seed){
const w=p.rect[2],ratio=3*w/m.w;
if (ratio<LOOK_SCALE[0]||ratio>LOOK_SCALE[1]) return Infinity;
const natural=(m.h-m.capTop)*w/m.w;
const fit=Math.min(1,clearance/natural);
return 3*Math.abs(Math.log(ratio))+(fit<1?6*(1-fit):0)
+(m.id===islandFamily(p)?0:0.35)+(mirror===((seed&1)===1)?0:0.02);
}
function planFor(p,master,mirror,clearance,extra={}){
const naturalDepth=(master.h-master.capTop)*p.rect[2]/master.w;
return{family:islandFamily(p),id:master.id,master,mirror,seed:platformHash(p),clearance,naturalDepth,depth:Math.min(naturalDepth,clearance),ground:false,...extra};
}
function buildIslandLayout(content,masters,scaleY=1){
const map=new Map(),byId=new Map(masters.map(m=>[m.id,m]));
const standardMasters=masters.filter((master)=>master.role==='STANDARD');
const bossMasters=masters.filter((master)=>master.role==='BOSS');
const groundMaster=masters.find((master)=>master.role==='GROUND');
if (standardMasters.length!==9||bossMasters.length!==5||!groundMaster) throw new Error('ISLAND_MASTER_CONTRACT');
const floating=[];
for (const p of content.platforms){
if (islandFamily(p)==='BASE_GROUND'){
const master=groundMaster;
map.set(p.id,{family:'BASE_GROUND',id:master.id,master,mirror:false,seed:platformHash(p),clearance:38,naturalDepth:38,depth:38,ground:true});
}else floating.push(p);
}
if (content.kind==='BOSS'){
const milestones=[5,11,17,23,29];
const boss=bossMasters[Math.max(0,milestones.indexOf(content.milestone))]||bossMasters[0];
const flank=standardMasters[7]||standardMasters[0];
for (const p of floating){
const clearance=visualClearanceBelow(p,content,scaleY),centre=p.id==='BOSS_C';
const master=centre?boss:flank;
map.set(p.id,planFor(p,master,!centre&&p.rect[0]>128,clearance));
}
}else{
const options=floating.map((p)=>{
const clearance=visualClearanceBelow(p,content,scaleY),seed=platformHash(p);
const looks=[];
for (const master of standardMasters) for (const mirror of[false,true]){
const cost=lookCost(p,master,mirror,clearance,seed);
if (cost<Infinity) looks.push({id:master.id,mirror,cost});
}
return{p,clearance,looks};
}).sort((a,b)=>a.looks.length-b.looks.length||b.p.rect[2]-a.p.rect[2]||(a.p.id<b.p.id?-1:1));
const worn=new Set(),wearers=new Map();
for (const o of options){
let best=null,bestCost=Infinity;
for (const look of o.looks){
if (ACCENT_MASTERS.includes(look.id)&&wearers.get(look.id)) continue;
const key=look.id+(look.mirror?'/m':'');
const cost=look.cost+(worn.has(key)?50:0)+0.9*(wearers.get(look.id)||0);
if (cost<bestCost){best=look;bestCost=cost;}
}
if (!best) best={id:standardMasters[platformHash(o.p)%standardMasters.length].id,mirror:false};
worn.add(best.id+(best.mirror?'/m':''));
wearers.set(best.id,(wearers.get(best.id)||0)+1);
map.set(o.p.id,planFor(o.p,byId.get(best.id),best.mirror,o.clearance));
}
}
for (const[id,plan] of map) map.set(id,Object.freeze(plan));
return map;
}
const CAP_ROWS=22;
function islandGeometry(plan,width){
const m=plan.master,rows=m.h-m.capTop;
const H=Math.max(2,Math.round(plan.depth*3)),depth=H/3;
const capH=Math.max(1,Math.round(Math.min(7,depth*.5)*3)),capDepth=capH/3;
const decorH=m.topDecor?Math.max(1,Math.round(m.topDecor*width/m.w*3)):0;
return{W:width*3,H,capH,depth,capDepth,decorH,decorDepth:decorH/3,bodyScale:(depth-capDepth)/(rows-CAP_ROWS),sx:width/m.w,sy:depth/rows};
}
function areaTaps(nSrc,nDst){
const s=nSrc/nDst,taps=[];
for (let i=0;i<nDst;i++){
const a=i*s,b=(i+1)*s,row=[];
let sum=0;
for (let j=Math.floor(a);j<Math.min(nSrc,Math.ceil(b));j++){
const w=Math.min(b,j+1)-Math.max(a,j);
if (w>1e-6){row.push(j,w);sum+=w;}
}
for (let k=1;k<row.length;k+=2) row[k]/=sum;
taps.push(row);
}
return taps;
}
function resampleSlice(dst,dx,dy,W,H,sheet,sx,sy,sw,sh,mirror){
const tx=areaTaps(sw,W),ty=areaTaps(sh,H),tmp=new Float32Array(sh*W*4);
for (let y=0;y<sh;y++){
const row=((sy+y)*sheet.w+sx)*4;
for (let x=0;x<W;x++){
let r=0,g=0,b=0,a=0;
const t=tx[x];
for (let k=0;k<t.length;k+=2){
const i=row+(mirror?sw-1-t[k]:t[k])*4,al=sheet.p[i+3]*t[k+1];
r+=sheet.p[i]*al;g+=sheet.p[i+1]*al;b+=sheet.p[i+2]*al;a+=al;
}
const o=(y*W+x)*4;
tmp[o]=r;tmp[o+1]=g;tmp[o+2]=b;tmp[o+3]=a;
}
}
for (let y=0;y<H;y++){
const t=ty[y];
for (let x=0;x<W;x++){
let r=0,g=0,b=0,a=0;
for (let k=0;k<t.length;k+=2){
const i=(t[k]*W+x)*4,w=t[k+1];
r+=tmp[i]*w;g+=tmp[i+1]*w;b+=tmp[i+2]*w;a+=tmp[i+3]*w;
}
const o=((dy+y)*dst.w+dx+x)*4,alpha=Math.round(a);
if (alpha<2){dst.p[o]=dst.p[o+1]=dst.p[o+2]=dst.p[o+3]=0;continue;}
dst.p[o]=Math.round(r/a);dst.p[o+1]=Math.round(g/a);dst.p[o+2]=Math.round(b/a);dst.p[o+3]=alpha;
}
}
}
function bakeIslandLayout(layout,platforms,surface,origin,region){
const[rx,ry,rw,rh]=region;
for (let y=ry;y<ry+rh;y++) surface.p.fill(0,(y*surface.w+rx)*4,(y*surface.w+rx+rw)*4);
const items=platforms.map((p)=>({p,plan:layout.get(p.id)})).filter((it)=>it.plan&&!it.plan.ground)
.map((it)=>({...it,g:islandGeometry(it.plan,it.p.rect[2])}))
.sort((a,b)=>(b.g.H+b.g.decorH)-(a.g.H+a.g.decorH)||b.g.W-a.g.W);
const slots=new Map(),sheet={w:surface.w,p:surface.p};
let x=0,y=0,shelf=0;
for (const{p,plan,g}of items){
const tall=g.H+g.decorH;
if (x+g.W>rw){x=0;y+=shelf+2;shelf=0;}
if (y+tall>rh||g.W>rw) continue;
const m=plan.master,dx=rx+x,dy=ry+y;
const sx=origin[0]+m.x,capY=origin[1]+m.y+m.capTop;
if (g.decorH) resampleSlice(surface,dx,dy,g.W,g.decorH,sheet,sx,origin[1]+m.y,m.w,m.topDecor,plan.mirror);
const by=dy+g.decorH;
resampleSlice(surface,dx,by,g.W,g.capH,sheet,sx,capY,m.w,CAP_ROWS,plan.mirror);
resampleSlice(surface,dx,by+g.capH,g.W,g.H-g.capH,sheet,sx,capY+CAP_ROWS,m.w,m.h-m.capTop-CAP_ROWS,plan.mirror);
slots.set(p.id,Object.freeze({x:dx,y:by,w:g.W,h:g.H,decorY:dy,decorH:g.decorH}));
x+=g.W+2;shelf=Math.max(shelf,tall);
}
return slots;
}
function runsAt(plate,m,row){
const runs=[];let start=-1;
for (let x=0;x<=m.w;x++){
const i=((row+m.y)*plate.w+m.x+x)*4;
const yes=x<m.w&&plate.p[i+3]>=128;
if (yes&&start<0) start=x;
if (!yes&&start>=0){runs.push([start,x]);start=-1;}
}
return runs;
}
function lipFit(plate,m){
if (m.x<0||m.y<0||m.w<1||m.h<1||m.x+m.w>plate.w||m.y+m.h>plate.h) throw new Error(`ISLAND_MASTER_BOUNDS ${m.id}`);
let l=m.w,r=0;
for (let row=Math.max(0,m.capTop-1);row<=Math.min(m.h-1,m.capTop+1);row++){
for (let x=0;x<m.w;x++) if (plate.p[((m.y+row)*plate.w+m.x+x)*4+3]>=128){l=Math.min(l,x);r=Math.max(r,x+1);}
}
if (r-l<8) throw new Error(`ISLAND_LIP_MISSING ${m.id}`);
return{...m,x:m.x+l,w:r-l,box:{x:m.x,w:m.w},signalRects:(m.signalRects||[]).map((q)=>({...q,x:q.x-l}))};
}
function measureIslands(plate,metadata){
if (plate.w!==ISLAND_SHEET.w||plate.h!==ISLAND_SHEET.h) throw new Error('ISLANDS_SIZE');
const variants=metadata?.masters||ISLAND_VARIANTS;
const topDecorV1=metadata?.rendererExtension==='topDecorV1';
return variants.map(source=>{
const m=topDecorV1?lipFit(plate,source):source;
if (m.x<0||m.y<0||m.w<1||m.h<1||m.x+m.w>plate.w||m.y+m.h>plate.h) throw new Error(`ISLAND_MASTER_BOUNDS ${m.id}`);
const opaqueRuns=[];
for (let y=0;y<m.h;y++){
opaqueRuns.push(runsAt(plate,m,y));
}
const signalRects=(m.signalRects||[]).map((rect)=>({x:rect.x,y:rect.y,w:rect.w,h:rect.h}));
const topDecor=topDecorV1?Math.max(0,Math.min(m.capTop,Math.trunc(m.topDecorRows??m.capTop))):0;
return{...m,capRows:22,opaqueRuns,signalRects,topDecor};
});
}
return{measureIslands,ISLAND_SHEET,buildIslandLayout,bakeIslandLayout,islandGeometry};
})();
__modules[19]=(()=>{
const VISUAL_SPEC=Object.freeze({
palette:Object.freeze({
black:'#000000',
voidDeep:'#020406',
ink:'#090A0B',
navySoft:'#173A46',
chromeDark:'#62717B',
chromeLight:'#F3F4EC',
white:'#FFFDF3',
cyanDeep:'#083A44',
cyanDark:'#0D6875',
cyan:'#20C4D7',
cyanLight:'#7BEFFF',
earthDark:'#2A1914',
ochre:'#D69543',
gold:'#E2A93F',
goldLight:'#FFD56A',
lava:'#B91E18',
lavaHot:'#F24A22',
ember:'#FF9D3B',
green:'#48D78A',
goldDeep:'#4A2E08',
ringDeep:'#33060F',
ringDark:'#6E0D18',
ring:'#A5121E',
ringLight:'#D8303A',
ivoryDark:'#AC9F84',
ivory:'#DED2B4',
ivoryLight:'#F6ECD4',
kingdomCrimsonLight:'#D8342C',
kingdomGold:'#DAA94C',
kingdomGoldLight:'#F5E5C1',
}),
});
function visualPalette(authorityPalette={}){
return{...VISUAL_SPEC.palette,...authorityPalette};
}
return{visualPalette};
})();
__modules[20]=(()=>{
const RING_FX_ORIGIN=Object.freeze([0,904]);
const RING_BAND_FRAMES=10;
const RING_LOCKED_FRAME=RING_BAND_FRAMES;
const RING_HALO_FRAMES=4;
const RING_SHOCK_FRAMES=4;
const RING_SPARK_FRAMES=3;
const RING_KINDS=Object.freeze(['MAGENTA','GREEN']);
const BAND_PX=72,HALO_PX=96,SHOCK_PX=96,SPARK_PX=15;
const[OX,OY]=RING_FX_ORIGIN;
const BAND_Y=OY;
const HALO_Y=OY+BAND_PX*RING_KINDS.length;
const SHOCK_Y=HALO_Y+HALO_PX;
const SPARK_Y=SHOCK_Y+SHOCK_PX;
const TONES=Object.freeze({
MAGENTA:Object.freeze({deep:'cyanDeep',main:'cyan',light:'cyanLight',core:'white',glow:[64,214,232]}),
GREEN:Object.freeze({deep:'goldDeep',main:'gold',light:'goldLight',core:'white',glow:[226,169,63]}),
});
const LOCKED_TONES=Object.freeze({
MAGENTA:Object.freeze({deep:'cyanDeep',main:'cyanDeep',light:'cyanDark',core:'cyanDark',glow:[8,58,68]}),
GREEN:Object.freeze({deep:'goldDeep',main:'goldDeep',light:'ochre',core:'ochre',glow:[74,46,8]}),
});
const kindIndex=(kind)=>Math.max(0,RING_KINDS.indexOf(kind));
const ringKindFor=(color)=>(color==='GREEN'?'GREEN':'MAGENTA');
const ringBandSource=(kind,frame)=>[OX+(((frame%RING_BAND_FRAMES)+RING_BAND_FRAMES)%RING_BAND_FRAMES)*BAND_PX,BAND_Y+kindIndex(kind)*BAND_PX];
const ringLockedSource=(kind)=>[OX+RING_LOCKED_FRAME*BAND_PX,BAND_Y+kindIndex(kind)*BAND_PX];
const ringHaloSource=(kind,frame)=>[OX+(kindIndex(kind)*RING_HALO_FRAMES+clampInt(frame,0,RING_HALO_FRAMES-1))*HALO_PX,HALO_Y];
const ringShockSource=(kind,frame)=>[OX+(kindIndex(kind)*RING_SHOCK_FRAMES+clampInt(frame,0,RING_SHOCK_FRAMES-1))*SHOCK_PX,SHOCK_Y];
const ringSparkSource=(kind,frame)=>[OX+(kindIndex(kind)*RING_SPARK_FRAMES+clampInt(frame,0,RING_SPARK_FRAMES-1))*16,SPARK_Y];
function clampInt(n,lo,hi){return Math.max(lo,Math.min(hi,n|0));}
const smooth=(e0,e1,x)=>{const t=Math.max(0,Math.min(1,(x-e0)/(e1-e0)));return t*t*(3-2*t);};
const mix=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];
function over(s,x,y,rgb,a){
if (a<=0.004) return;
const i=(y*s.w+x)*4,p=s.p;
const da=p[i+3]/255,sa=Math.min(1,a);
const oa=sa+da*(1-sa);
for (let k=0;k<3;k++) p[i+k]=Math.round((rgb[k]*sa+p[i+k]*da*(1-sa))/Math.max(oa,1e-6));
p[i+3]=Math.round(oa*255);
}
function paintBand(s,C,x0,y0,tone,frame){
const deep=C[tone.deep],main=C[tone.main],light=C[tone.light],core=C[tone.core];
const phase=(frame/RING_BAND_FRAMES)*(Math.PI*2/8);
const c=BAND_PX/2;
for (let py=0;py<BAND_PX;py++) for (let px=0;px<BAND_PX;px++){
const dx=px+.5-c,dy=py+.5-c;
const d=Math.hypot(dx,dy),th=Math.atan2(dy,dx);
const rim=smooth(35.2,34.2,d)*smooth(22.2,23.2,d);
if (rim>0) over(s,x0+px,y0+py,deep,rim);
const band=smooth(33.4,32.4,d)*smooth(24.4,25.4,d);
if (band>0){
const seg=Math.pow(.5+.5*Math.cos(8*(th-phase)),3);
const lead=Math.pow(.5+.5*Math.cos(8*(th-phase)-.9),12);
const bevel=smooth(32.6,26.2,d);
let rgb=mix(main,light,Math.min(1,seg*.85+bevel*.25));
rgb=mix(rgb,core,lead*.55);
rgb=mix(rgb,deep,smooth(30.8,33.2,d)*.45);
over(s,x0+px,y0+py,rgb,band);
}
const lip=smooth(26.6,25.9,d)*smooth(24.3,25.0,d);
if (lip>0) over(s,x0+px,y0+py,light,lip*.95);
const track=smooth(20.6,19.8,d)*smooth(17.4,18.2,d);
if (track>0){
const dot=smooth(.55,.85,Math.cos(12*(th+phase*1.5)));
if (dot>0) over(s,x0+px,y0+py,light,track*dot*.82);
}
const g=Math.cos(th+2.35);
const glint=smooth(.86,.98,g)*smooth(31.6,30.2,d)*smooth(26.2,27.6,d);
if (glint>0) over(s,x0+px,y0+py,core,glint*.9);
const notch=smooth(1.6,.9,Math.abs(dx))*smooth(35.6,34.6,d)*smooth(31.8,32.8,d)*(Math.abs(dy)>30?1:0);
if (notch>0) over(s,x0+px,y0+py,light,notch);
}
}
const SCRIM_PEAK=0.62;
const SCRIM_RGB=[4,6,9];
function paintHalo(s,x0,y0,rgb,strength){
const c=HALO_PX/2;
for (let py=0;py<HALO_PX;py++) for (let px=0;px<HALO_PX;px++){
const d=Math.hypot(px+.5-c,py+.5-c);
const edge=smooth(48,42,d);
const scrim=Math.exp(-Math.pow(d/26,2.4))*SCRIM_PEAK*edge;
if (scrim>0) over(s,x0+px,y0+py,SCRIM_RGB,scrim);
const ringGlow=Math.exp(-Math.pow((d-29)/9.5,2));
const fill=Math.exp(-Math.pow(d/30,2))*.22;
const a=(ringGlow+fill)*strength*edge;
over(s,x0+px,y0+py,rgb,a);
}
}
function paintShock(s,C,x0,y0,tone,strength){
const c=SHOCK_PX/2,light=C[tone.light],core=C[tone.core];
for (let py=0;py<SHOCK_PX;py++) for (let px=0;px<SHOCK_PX;px++){
const d=Math.hypot(px+.5-c,py+.5-c);
const wave=smooth(47.5,45.8,d)*smooth(40.5,43.5,d);
const hot=smooth(46.4,45.4,d)*smooth(43.4,44.4,d);
if (wave>0) over(s,x0+px,y0+py,light,wave*strength*.75);
if (hot>0) over(s,x0+px,y0+py,core,hot*strength);
}
}
function paintSpark(s,C,x0,y0,tone,size){
const c=SPARK_PX/2,light=C[tone.light],core=C[tone.core];
const arm=[3.2,5.2,7.2][size];
for (let py=0;py<SPARK_PX;py++) for (let px=0;px<SPARK_PX;px++){
const dx=Math.abs(px+.5-c),dy=Math.abs(py+.5-c);
const cross=Math.max(smooth(arm,0,dx)*smooth(1.3,.3,dy),smooth(arm,0,dy)*smooth(1.3,.3,dx));
const diag=smooth(arm*.45,0,Math.hypot(dx,dy))*.8;
const a=Math.max(cross,diag);
if (a>0) over(s,x0+px,y0+py,mix(light,core,smooth(.5,1,a)),a);
}
}
function paintRingFx(s,C){
RING_KINDS.forEach((kind)=>{
const tone=TONES[kind];
for (let f=0;f<RING_BAND_FRAMES;f++){const[x,y]=ringBandSource(kind,f);paintBand(s,C,x,y,tone,f);}
{const[x,y]=ringLockedSource(kind);paintBand(s,C,x,y,LOCKED_TONES[kind],0);}
[.34,.48,.62,.78].forEach((k,f)=>{const[x,y]=ringHaloSource(kind,f);paintHalo(s,x,y,tone.glow,k);});
[1,.72,.46,.22].forEach((k,f)=>{const[x,y]=ringShockSource(kind,f);paintShock(s,C,x,y,tone,k);});
for (let f=0;f<RING_SPARK_FRAMES;f++){const[x,y]=ringSparkSource(kind,f);paintSpark(s,C,x,y,tone,f);}
});
}
const easeOutBack=(t)=>{const k=1.9;const u=t-1;return 1+(k+1)*u*u*u+k*u*u;};
const RING_INTRO_TICKS=22;
const RING_BURST_TICKS=22;
function quad(add,cx,cy,size,src,srcPx,z){
add(cx-size/2,cy-size/2,size,size,src[0],src[1],srcPx,srcPx,z);
}
function emitLiveRing(add,kind,cx,cy,tick,age,z){
const intro=age<RING_INTRO_TICKS?age/RING_INTRO_TICKS:1;
const scale=intro>=1?1:Math.max(.08,easeOutBack(Math.min(1,intro*1.35)));
const breath=[0,1,2,3,3,2,1,0][(tick>>3)&7];
quad(add,cx,cy,32*Math.max(scale,.4),ringHaloSource(kind,intro<1?3:breath),HALO_PX,z+.006);
quad(add,cx,cy,24*scale,ringBandSource(kind,Math.floor(tick/3)),BAND_PX,z);
if (intro<1){
const k=intro;
quad(add,cx,cy,80-52*k,ringShockSource(kind,Math.min(3,Math.floor(k*4))),SHOCK_PX,z-.004);
for (let i=0;i<4;i++){
const a=i*Math.PI/2+Math.PI/4+tick*.02;
const r=30*(1-k)+11;
quad(add,cx+Math.cos(a)*r,cy+Math.sin(a)*r,5,ringSparkSource(kind,2-Math.min(2,Math.floor(k*3))),SPARK_PX,z-.005);
}
return;
}
for (let i=0;i<3;i++){
const a=tick*.045+i*(Math.PI*2/3);
const front=Math.sin(a)>0;
const size=[0,1,2,1][((tick>>2)+i*2)&3];
quad(add,cx+Math.cos(a)*14.5,cy+Math.sin(a)*14.5,4+size*1.5,ringSparkSource(kind,size),SPARK_PX,front?z-.005:z+.003);
}
}
function emitLockedRing(add,kind,cx,cy,z){
quad(add,cx,cy,32,ringHaloSource(kind,0),HALO_PX,z+.006);
quad(add,cx,cy,24,ringLockedSource(kind),BAND_PX,z);
}
function emitRingBurst(add,kind,cx,cy,age,z){
if (age>=RING_BURST_TICKS) return;
const t=age/RING_BURST_TICKS;
const ease=1-(1-t)*(1-t);
if (age<7) quad(add,cx,cy,24+age*3.2,ringBandSource(kind,age),BAND_PX,z-.002);
quad(add,cx,cy,30+ease*62,ringShockSource(kind,Math.min(3,Math.floor(t*4))),SHOCK_PX,z-.003);
if (age>3){
const t2=(age-3)/(RING_BURST_TICKS-3);
quad(add,cx,cy,26+(1-(1-t2)*(1-t2))*40,ringShockSource(kind,Math.min(3,1+Math.floor(t2*3))),SHOCK_PX,z-.0035);
}
const size=age<7?2:age<14?1:0;
for (let i=0;i<8;i++){
const a=i*Math.PI/4+(i&1?.2:0);
const r=10+ease*(i&1?30:38);
quad(add,cx+Math.cos(a)*r,cy+Math.sin(a)*r,4+size*2,ringSparkSource(kind,size),SPARK_PX,z-.004);
}
}
return{paintRingFx,emitLiveRing,emitLockedRing,emitRingBurst,ringKindFor};
})();
__modules[21]=(()=>{
const GRADE=Object.freeze({
STRENGTH:1.0,
EDGE_KEEP:0.42,
CORRIDOR:[0.20,0.80],
TARGET_L50:0.120,
HIGHLIGHT:0.60,
DESAT:0.14,
SHARPEN:0,
NEAR_SETTLE:0.10,
ISLAND_SETTLE:0.08,
});
const LR=0.2126,LG=0.7152,LB=0.0722;
const TO_LINEAR=new Float32Array(256);
for (let i=0;i<256;i++){const s=i/255;TO_LINEAR[i]=s<=0.04045?s/12.92:((s+0.055)/1.055)**2.4;}
function toSrgb(v){
const c=v<=0.0031308?v*12.92:1.055*v**(1/2.4)-0.055;
return Math.max(0,Math.min(255,Math.round(c*255)));
}
const SRGB_STEPS=16384;
const TO_SRGB=new Uint8Array(SRGB_STEPS+1);
for (let i=0;i<=SRGB_STEPS;i++) TO_SRGB[i]=toSrgb(i/SRGB_STEPS);
function toSrgbFast(v){
if (!(v>0)) return 0;
if (v>=1) return 255;
return TO_SRGB[(v*SRGB_STEPS+0.5)|0];
}
function columnWeight(x,w,g=GRADE){
const t=x/Math.max(1,w-1);
const[a,b]=g.CORRIDOR;
if (t>=a&&t<=b) return 1;
const d=t<a?(a-t)/a:(t-b)/(1-b);
const s=Math.min(1,Math.max(0,d));
return 1-(1-g.EDGE_KEEP)*(s*s*(3-2*s));
}
function solveGain(plate,g){
const[a,b]=g.CORRIDOR;
const x0=Math.round(plate.w*a),x1=Math.round(plate.w*b);
const lums=[];
const step=Math.max(2,Math.round(plate.w/128));
for (let y=0;y<plate.h;y+=step){
for (let x=x0;x<x1;x+=step){
const i=(y*plate.w+x)*4;
lums.push(LR*TO_LINEAR[plate.p[i]]+LG*TO_LINEAR[plate.p[i+1]]+LB*TO_LINEAR[plate.p[i+2]]);
}
}
if (!lums.length) return 1;
lums.sort((p,q)=>p-q);
const median=lums[lums.length>>1];
if (median<=g.TARGET_L50) return 1;
const target=g.TARGET_L50;
return (target/(1-g.HIGHLIGHT*target))/Math.max(1e-6,median);
}
const ALPHA_CLEAR=15,ALPHA_SOLID=240;
function settleAlpha(layer){
const out={w:layer.w,h:layer.h,p:new Uint8ClampedArray(layer.p)};
for (let i=3;i<out.p.length;i+=4){
if (out.p[i]<=ALPHA_CLEAR) out.p[i]=0;
else if (out.p[i]>=ALPHA_SOLID) out.p[i]=255;
}
return out;
}
function settle(layer,k,own=false){
if (!(k>0)) return layer;
const{w,h,p}=layer;
const step=Math.max(1,Math.round(w/128))*4;
let sum=0,weight=0;
for (let i=0;i<p.length;i+=step){
const a=p[i+3];
if (!a) continue;
sum+=(LR*p[i]+LG*p[i+1]+LB*p[i+2])*a;
weight+=a;
}
if (!weight) return layer;
const mean=sum/weight;
const out=own?layer:{w,h,p:new Uint8ClampedArray(p)};
const q=out.p;
for (let i=0;i<q.length;i+=4){
if (!q[i+3]) continue;
q[i]+=(mean-q[i])*k;
q[i+1]+=(mean-q[i+1])*k;
q[i+2]+=(mean-q[i+2])*k;
}
return out;
}
function compositeLayers(rear,near){
const out={w:rear.w,h:rear.h,p:new Uint8ClampedArray(rear.p.length)};
for (let i=0;i<out.p.length;i+=4){
const a=near.p[i+3]/255;
for (let k=0;k<3;k++) out.p[i+k]=near.p[i+k]*a+rear.p[i+k]*(1-a);
out.p[i+3]=255;
}
return out;
}
function unsharp(layer,amount){
if (!(amount>0)) return layer;
const{w,h,p}=layer;
const n=w*h;
const wa=new Float32Array(n);
const pre=new Float32Array(n*3);
for (let i=0;i<n;i++){
const a=p[i*4+3]/255;
wa[i]=a;
for (let c=0;c<3;c++) pre[i*3+c]=p[i*4+c]*a;
}
const tmpA=new Float32Array(n),tmpC=new Float32Array(n*3);
const blurA=new Float32Array(n),blurC=new Float32Array(n*3);
for (let y=0;y<h;y++) for (let x=0;x<w;x++){
const i=y*w+x,l=y*w+(x>0?x-1:0),r=y*w+(x<w-1?x+1:w-1);
tmpA[i]=(wa[l]+2*wa[i]+wa[r])/4;
for (let c=0;c<3;c++) tmpC[i*3+c]=(pre[l*3+c]+2*pre[i*3+c]+pre[r*3+c])/4;
}
for (let y=0;y<h;y++) for (let x=0;x<w;x++){
const i=y*w+x,u=(y>0?y-1:0)*w+x,d=(y<h-1?y+1:h-1)*w+x;
blurA[i]=(tmpA[u]+2*tmpA[i]+tmpA[d])/4;
for (let c=0;c<3;c++) blurC[i*3+c]=(tmpC[u*3+c]+2*tmpC[i*3+c]+tmpC[d*3+c])/4;
}
const out={w,h,p:new Uint8ClampedArray(p)};
for (let i=0;i<n;i++){
if (wa[i]<=0) continue;
const norm=blurA[i]>1e-4?1/blurA[i]:0;
for (let c=0;c<3;c++){
const v=p[i*4+c];
out.p[i*4+c]=v+(v-blurC[i*3+c]*norm)*amount;
}
}
return out;
}
function gradeLayers(rear,near,g=GRADE){
const alphaSettled=settleAlpha(near);
const crisp=(layer)=>unsharp(layer,g.SHARPEN);
const back=(layer)=>settle(crisp(layer),g.NEAR_SETTLE,true);
if (g.STRENGTH<=0) return{rear:crisp(rear),near:back(alphaSettled)};
const gain=solveGain(compositeLayers(rear,alphaSettled),g);
if (gain>=0.999) return{rear:crisp(rear),near:back(alphaSettled)};
return{rear:crisp(applyGrade(rear,gain,g)),near:back(applyGrade(alphaSettled,gain,g))};
}
function applyGrade(plate,gain,g){
const out={w:plate.w,h:plate.h,p:new Uint8ClampedArray(plate.p.length)};
const weights=new Float32Array(plate.w);
for (let x=0;x<plate.w;x++) weights[x]=columnWeight(x,plate.w,g)*g.STRENGTH;
for (let y=0;y<plate.h;y++){
for (let x=0;x<plate.w;x++){
const i=(y*plate.w+x)*4;
const w=weights[x];
const r=TO_LINEAR[plate.p[i]],gg=TO_LINEAR[plate.p[i+1]],b=TO_LINEAR[plate.p[i+2]];
const k=1+(gain-1)*w;
let nr=r*k,ng=gg*k,nb=b*k;
const L=LR*nr+LG*ng+LB*nb;
const roll=1/(1+g.HIGHLIGHT*L);
nr*=roll;ng*=roll;nb*=roll;
const d=g.DESAT*w;
if (d>0){
const L2=LR*nr+LG*ng+LB*nb;
nr+=(L2-nr)*d;ng+=(L2-ng)*d;nb+=(L2-nb)*d;
}
out.p[i]=toSrgbFast(nr);out.p[i+1]=toSrgbFast(ng);out.p[i+2]=toSrgbFast(nb);out.p[i+3]=plate.p[i+3];
}
}
return out;
}
const ARCADE_DEPTH=Object.freeze({
REAR:Object.freeze({gain:0.52,desat:0.36,haze:[0.010,0.016,0.034],hazeK:0.50}),
NEAR:Object.freeze({gain:0.80,desat:0.18,haze:[0.006,0.010,0.022],hazeK:0.25}),
});
function depthGrade(plate,d){
const out={w:plate.w,h:plate.h,p:new Uint8ClampedArray(plate.p.length)};
const q=plate.p,o=out.p;
for (let i=0;i<q.length;i+=4){
let r=TO_LINEAR[q[i]]*d.gain,g=TO_LINEAR[q[i+1]]*d.gain,b=TO_LINEAR[q[i+2]]*d.gain;
const L=LR*r+LG*g+LB*b;
r+=(L-r)*d.desat;g+=(L-g)*d.desat;b+=(L-b)*d.desat;
r+=(d.haze[0]-r)*d.hazeK*0.2;g+=(d.haze[1]-g)*d.hazeK*0.2;b+=(d.haze[2]-b)*d.hazeK*0.2;
o[i]=toSrgbFast(r);o[i+1]=toSrgbFast(g);o[i+2]=toSrgbFast(b);o[i+3]=q[i+3];
}
return out;
}
return{gradeLayers,settle,GRADE,depthGrade,ARCADE_DEPTH};
})();
__modules[22]=(()=>{
const SPRITE_HD=3;
const SPRITE_CELL_PX=32*SPRITE_HD;
const SPRITE_DRAW_OFFSET=Object.freeze([1,4]);
const SPRITE_FRAME_COUNT=192;
const RIDER_CELL_PX=96;
const RIDER_STATE_COUNT=32;
const RIDER_ATLAS_W=1536;
const RIDER_ATLAS_H=384;
const RIDER_FRONT_ROW_OFFSET=2;
const SPRITE_IDLE=0;
const SPRITE_RANGES=Object.freeze({
NEUTRAL:[0,7],FLAP:[8,31],IMPULSE:[32,43],GLIDE:[44,53],CLIMB:[54,63],
DESCENT:[64,73],BANK_LEFT:[74,83],BANK_RIGHT:[84,93],RUN:[94,113],
TAKEOFF:[114,123],LANDING:[124,133],AIR_TRANSITION:[134,149],
GROUND_AIR:[150,161],DART:[162,171],HIT:[172,177],DEATH:[178,185],VERTICAL_ASCENT:[186,191],
});
function spriteSourceOrigin(_origin,_classRow,frame){
const n=((frame%SPRITE_FRAME_COUNT)+SPRITE_FRAME_COUNT)%SPRITE_FRAME_COUNT;
return[(n%16)*SPRITE_CELL_PX,Math.floor(n/16)*SPRITE_CELL_PX];
}
function idleSourceOrigin(classRow){return spriteSourceOrigin([0,0],classRow,SPRITE_IDLE);}
function riderSourceOrigin(state,front=false){
const n=Math.max(0,Math.min(RIDER_STATE_COUNT-1,state|0));
return[(n%16)*RIDER_CELL_PX,(Math.floor(n/16)+(front?RIDER_FRONT_ROW_OFFSET:0))*RIDER_CELL_PX];
}
function paintHdSprites(_surface,_origin,sheet){
if (!sheet||sheet.w!==1536||sheet.h!==1152) throw new Error('WAR_BIRD_ART_REQUIRED: expected 192 poses in a 1536x1152 RGBA sheet');
}
function validateRiderAttachments(sheet,spec,profile){
if (!sheet||sheet.w!==RIDER_ATLAS_W||sheet.h!==RIDER_ATLAS_H) throw new Error(`RIDER_ART_REQUIRED: expected ${RIDER_ATLAS_W}x${RIDER_ATLAS_H} RGBA attachment atlas`);
if (!profile||!spec||spec.owner!==profile.riderOwner||spec.profileId!==profile.id||spec.role!=='PLAYER_PRESENTATION_ATTACHMENT') throw new Error('RIDER_MAP_OWNER');
const stateCount=profile.riderStates|0;
if (stateCount<1||stateCount>RIDER_STATE_COUNT||spec.geometry?.states!==stateCount||!Array.isArray(spec.states)||spec.states.length!==stateCount) throw new Error('RIDER_STATE_COUNT');
if (!Array.isArray(spec.frames)||spec.frames.length!==SPRITE_FRAME_COUNT) throw new Error('RIDER_FRAME_MAP_COUNT');
if (!spec.invariants?.presentationOnly||!spec.invariants?.playerOnly||spec.invariants?.cartridgeOverrideAllowed!==false) throw new Error('RIDER_OWNERSHIP');
if (profile.id==='DEV00_SIMPLE'&&(!spec.invariants.internalRomOnly||!spec.invariants.consoleSelectionOnly)) throw new Error('RIDER_DEV00_EXCLUSIVITY');
const ids=new Set(spec.states.map((state)=>state.index));
if (ids.size!==stateCount||[...ids].some((id)=>!Number.isInteger(id)||id<0||id>=stateCount)) throw new Error('RIDER_STATE_INDEX');
spec.frames.forEach((record,frame)=>{
if (record.birdFrame!==frame||!ids.has(record.riderState)) throw new Error(`RIDER_FRAME_MAP_${frame}`);
for (const key of['socketX','socketY','contactX','contactY','dx','dy']) if (!Number.isInteger(record[key])) throw new Error(`RIDER_FRAME_${frame}_${key}`);
});
return spec;
}
return{paintHdSprites,validateRiderAttachments,SPRITE_CELL_PX,SPRITE_FRAME_COUNT,SPRITE_RANGES,SPRITE_DRAW_OFFSET,spriteSourceOrigin,SPRITE_IDLE,idleSourceOrigin,RIDER_CELL_PX,RIDER_STATE_COUNT,RIDER_ATLAS_W,RIDER_ATLAS_H,RIDER_FRONT_ROW_OFFSET,riderSourceOrigin};
})();
__modules[23]=(()=>{
const PROPS_ORIGIN=Object.freeze([1024,392]);
const[PX0,PY0]=PROPS_ORIGIN;
const EGG_CELL=36;
const EGG_FRAMES=Object.freeze({INTACT:0,CRACK1:1,CRACK2:2,OPEN:3,TILT_L:4,TILT_R:5});
const SHIMMER_CELL=96;
const CROWN_CELL=30;
const SHIMMER_Y=PY0+224;
const eggSource=(f)=>[PX0+f*EGG_CELL,PY0];
const crownSource=(f)=>[PX0+6*EGG_CELL+8+(f&1)*CROWN_CELL,PY0];
const shimmerSource=(f)=>[PX0+(f&3)*SHIMMER_CELL,SHIMMER_Y];
const SS=4;
function over(s,x,y,rgb,a){
if (a<=0.004||x<0||y<0||x>=s.w||y>=s.h) return;
const i=(y*s.w+x)*4,p=s.p;
const da=p[i+3]/255,sa=Math.min(1,a);
const oa=sa+da*(1-sa);
for (let k=0;k<3;k++) p[i+k]=Math.round((rgb[k]*sa+p[i+k]*da*(1-sa))/Math.max(oa,1e-6));
p[i+3]=Math.round(oa*255);
}
class Pen{
constructor(s,ox,oy,k,{clip=null,rot=0,pivot=[0,0]}={}){
this.s=s;this.ox=ox;this.oy=oy;this.k=k;this.clip=clip;
this.cos=Math.cos(rot);this.sin=Math.sin(rot);this.pivot=pivot;
}
map([x,y]){
const[px,py]=this.pivot;
const dx=x-px,dy=y-py;
return[this.ox+(px+dx*this.cos-dy*this.sin)*this.k,this.oy+(py+dx*this.sin+dy*this.cos)*this.k];
}
poly(points,c,alpha=1){
if (!c) return;
const pts=points.map((p)=>this.map(p));
let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
for (const[x,y] of pts){minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
const clip=this.clip;
const x0=Math.max(Math.floor(minX),clip?clip[0]:0),x1=Math.min(Math.ceil(maxX),clip?clip[0]+clip[2]:this.s.w);
const y0=Math.max(Math.floor(minY),clip?clip[1]:0),y1=Math.min(Math.ceil(maxY),clip?clip[1]+clip[3]:this.s.h);
for (let py=y0;py<y1;py++){
const rows=[];
for (let sy=0;sy<SS;sy++){
const yy=py+(sy+.5)/SS,xs=[];
for (let i=0,j=pts.length-1;i<pts.length;j=i++){
const a=pts[i],b=pts[j];
if ((a[1]>yy)!==(b[1]>yy)) xs.push(a[0]+(yy-a[1])*(b[0]-a[0])/(b[1]-a[1]));
}
xs.sort((p,q)=>p-q);
rows.push(xs);
}
for (let px=x0;px<x1;px++){
let cover=0;
for (const xs of rows) for (let sx=0;sx<SS;sx++){
const xx=px+(sx+.5)/SS;
let inside=false;
for (let i=0;i<xs.length;i+=2) if (xx>=xs[i]&&xx<xs[i+1]){inside=true;break;}
if (inside) cover++;
}
if (cover) over(this.s,px,py,c,alpha*cover/(SS*SS));
}
}
}
ellipse(cx,cy,rx,ry,c,alpha=1,n=28){
const pts=[];
for (let i=0;i<n;i++){const a=i/n*Math.PI*2;pts.push([cx+Math.cos(a)*rx,cy+Math.sin(a)*ry]);}
this.poly(pts,c,alpha);
}
line(x0,y0,x1,y1,w,c,alpha=1){
const dx=x1-x0,dy=y1-y0,len=Math.hypot(dx,dy)||1;
const nx=-dy/len*w/2,ny=dx/len*w/2;
this.poly([[x0+nx,y0+ny],[x1+nx,y1+ny],[x1-nx,y1-ny],[x0-nx,y0-ny]],c,alpha);
}
}
function paintEgg(s,C,f){
const[ox,oy]=eggSource(f);
const tilt=f===EGG_FRAMES.TILT_L?-.22:f===EGG_FRAMES.TILT_R?.22:0;
const pen=new Pen(s,ox,oy,3,{clip:[ox,oy,EGG_CELL,EGG_CELL],rot:tilt,pivot:[6,11.6]});
const cx=6,cy=7.6;
new Pen(s,ox,oy,3,{clip:[ox,oy,EGG_CELL,EGG_CELL]}).ellipse(6,11.55,3.6,.55,C.ink,.55);
const open=f===EGG_FRAMES.OPEN;
const shell=[];
for (let i=0;i<32;i++){
const a=i/32*Math.PI*2,sy=Math.sin(a);
const rx=3.45*(sy<0?1+sy*.16:1);
shell.push([cx+Math.cos(a)*rx,cy+sy*4.05]);
}
pen.poly(shell.map(([x,y])=>[cx+(x-cx)*1.08,cy+(y-cy)*1.05]),C.ink);
if (open){
pen.ellipse(cx,cy+.2,2.6,2.1,C.voidDeep);
pen.poly([[cx-2.4,cy-.6],[cx-1.2,cy-2.6],[cx-.5,cy-1.6],[cx+.5,cy-2.8],[cx+1.3,cy-1.5],[cx+2.4,cy-.6],[cx+2.2,cy+1],[cx-2.2,cy+1]],C.voidDeep);
}
pen.poly(open?[...shell.filter(([,y])=>y>cy-.2)].sort((a,b)=>Math.atan2(a[1]-cy,a[0]-cx)-Math.atan2(b[1]-cy,b[0]-cx)).concat([[cx-3.3,cy-.2],[cx-2,cy-1.4],[cx-1,cy-.5],[cx,cy-1.6],[cx+1.2,cy-.4],[cx+2.3,cy-1.3],[cx+3.3,cy-.2]]):shell,C.ivory);
pen.poly([[cx+1.6,cy-3],[cx+3.4,cy-.5],[cx+3.1,cy+2.6],[cx+1.2,cy+4],[cx-1.4,cy+4],[cx+1.6,cy+2.4],[cx+2.3,cy-.4]],C.ivoryDark,.85);
if (!open) pen.ellipse(cx-1.25,cy-2.1,.8,1.25,C.ivoryLight,.95);
for (const[x,y,c,r] of[[-1.6,.8,C.ring,.6],[1.1,-1.2,C.kingdomGold,.5],[.4,2.2,C.ringLight,.5],[-.4,-2.6,C.ring,.4],[2,1,C.ringLight,.38],[-2,-.6,C.ringDark,.34]]){
if (open&&y<-.3) continue;
pen.ellipse(cx+x,cy+y,r,r,c);
}
if (f===EGG_FRAMES.CRACK1||f===EGG_FRAMES.CRACK2){
const crack=[[cx-.4,cy-3.6],[cx+.4,cy-2.2],[cx-.6,cy-1.1],[cx+.6,cy+.3]];
for (let i=1;i<crack.length;i++) pen.line(...crack[i-1],...crack[i],.42,C.ink);
if (f===EGG_FRAMES.CRACK2){
for (let i=1;i<crack.length;i++) pen.line(...crack[i-1],...crack[i],.16,C.ringLight);
const b=[[cx+.6,cy+.3],[cx+1.8,cy+1],[cx+2.6,cy+.4]];
for (let i=1;i<b.length;i++) pen.line(...b[i-1],...b[i],.36,C.ink);
pen.line(cx-.6,cy-1.1,cx-2,cy-.3,.34,C.ink);
}
}
if (open){
pen.ellipse(cx,cy-.4,1.9,1.3,C.ringDeep);
pen.ellipse(cx,cy-.2,1.2,.8,C.ringDark,.8);
pen.line(cx-.8,cy-.4,cx+.8,cy-.4,.22,C.ring);
pen.poly([[cx-2.6,cy-4.2],[cx-.6,cy-5.2],[cx+1.6,cy-4.6],[cx+.4,cy-3.6],[cx-.8,cy-4]],C.ivoryLight);
}
}
function paintShimmer(s,C,f){
const[ox,oy]=shimmerSource(f);
const pen=new Pen(s,ox,oy,3,{clip:[ox,oy,SHIMMER_CELL,SHIMMER_CELL]});
const cx=15;
const segs=[[1,4],[6,3],[11,5],[18,3],[23,6],[30,2]];
segs.forEach(([y,h],i)=>{
const on=(i+f)%4!==0;
const jitter=((i*7+f*3)%5-2)*.35;
pen.line(cx+jitter,y,cx+jitter,y+h,on?1.5:.8,on?C.cyanLight:C.cyanDeep,on?.95:.7);
if (on) pen.line(cx+jitter,y,cx+jitter,y+h,3.6,C.cyan,.22);
});
const ticks=[[5,8,-1],[9,15,1],[3,22,-1],[7,27,1]];
ticks.forEach(([w,y,side],i)=>{
const k=(i+f)&3;
pen.line(cx+side*1.5,y,cx+side*(1.5+w*(k?1:.5)),y,.9,k===1?C.chromeLight:C.cyanDark,.9);
});
for (let i=0;i<7;i++){
const a=i*2.39+f*.7,r=5+((i*5+f*3)%7);
pen.ellipse(cx+Math.cos(a)*r*.8,16+Math.sin(a)*r*1.4,.45,.45,i%3?C.cyanLight:C.white,.9);
}
}
function paintCrown(s,C,f){
const[ox,oy]=crownSource(f);
const pen=new Pen(s,ox,oy,3,{clip:[ox,oy,CROWN_CELL,CROWN_CELL]});
const pts=[[1,8.6],[1.4,3.2],[3.2,5.6],[5,1.4],[6.8,5.6],[8.6,3.2],[9,8.6]];
pen.poly(pts.map(([x,y])=>[x,y]),C.ink);
pen.poly(pts.map(([x,y])=>[5+(x-5)*.82,5+(y-5)*.8+.2]),C.gold);
pen.poly([[1.9,7.2],[8.1,7.2],[8.1,8.2],[1.9,8.2]],C.goldLight);
pen.ellipse(5,5.6,1.05,1.05,C.ink);pen.ellipse(5,5.6,.75,.75,f?C.lavaHot:C.lava);
if (f) pen.ellipse(4.7,5.3,.28,.28,C.white);
for (const x of[1.4,5,8.6]) pen.ellipse(x,x===5?1.5:3.2,.45,.45,C.goldLight);
}
function paintHdProps(s,C){
for (let f=0;f<6;f++) paintEgg(s,C,f);
for (let f=0;f<4;f++) paintShimmer(s,C,f);
paintCrown(s,C,0);paintCrown(s,C,1);
}
return{paintHdProps,eggSource,shimmerSource,crownSource,EGG_FRAMES,EGG_CELL,SHIMMER_CELL,CROWN_CELL};
})();
__modules[24]=(()=>{
const{surface,color,rect,circle}=__modules[17];
const{ATLAS_SIZE,WORLD_PLATE_W,WORLD_TEX_W,WORLD_TEX_H}=__modules[16];
const{measureIslands}=__modules[18];
const{visualPalette}=__modules[19];
const{paintRingFx}=__modules[20];
const{gradeLayers,settle,GRADE,depthGrade,ARCADE_DEPTH}=__modules[21];
const{paintHdProps}=__modules[23];
const{paintHdSprites,SPRITE_CELL_PX,SPRITE_FRAME_COUNT,SPRITE_DRAW_OFFSET,spriteSourceOrigin,SPRITE_IDLE,idleSourceOrigin,RIDER_CELL_PX,RIDER_STATE_COUNT,RIDER_FRONT_ROW_OFFSET,riderSourceOrigin}=__modules[22];
const REGION=Object.freeze({
SPRITES:[0,0],
RING_DIM:[1536,520],
SWATCH:[1536,560],
ISLANDS:[0,1280],
ISLAND_BAKE:[0,0,1024,768],
});
const FONT_COLOURS=['white','cyanLight','lavaHot','goldLight','chromeDark'];
const MODERN_FONT=Object.freeze({x:1536,y:0,cols:16,cellW:18,cellH:24,rows:4,glyphW:15,glyphH:21});
function copyCanvas(s,canvas,dx,dy){
const pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
for (let y=0;y<canvas.height;y++) s.p.set(
pixels.subarray(y*canvas.width*4,(y+1)*canvas.width*4),
((dy+y)*s.w+dx)*4,
);
}
function paintModernFont(s,A,C){
const canvas=document.createElement('canvas');
canvas.width=MODERN_FONT.cols*MODERN_FONT.cellW;
canvas.height=FONT_COLOURS.length*MODERN_FONT.rows*MODERN_FONT.cellH;
const ctx=canvas.getContext('2d',{willReadFrequently:true});
if (!ctx) throw new Error('TEXT_RASTER_UNAVAILABLE');
ctx.textBaseline='alphabetic';
ctx.textAlign='center';
ctx.font='700 23px Arial, Helvetica, sans-serif';
const chars=Object.keys(A.font_5x7).sort();
for (let tone=0;tone<FONT_COLOURS.length;tone++){
const[r,g,b]=C[FONT_COLOURS[tone]];
ctx.fillStyle=`rgb(${r} ${g} ${b})`;
chars.forEach((ch,i)=>{
if (ch===' ') return;
const x=(i%MODERN_FONT.cols)*MODERN_FONT.cellW+1+MODERN_FONT.glyphW/2;
const y=tone*MODERN_FONT.rows*MODERN_FONT.cellH+Math.floor(i/MODERN_FONT.cols)*MODERN_FONT.cellH+20;
ctx.fillText(ch,x,y,MODERN_FONT.glyphW);
});
}
copyCanvas(s,canvas,MODERN_FONT.x,MODERN_FONT.y);
}
function paintSpentRing(s,C){
const[x,y]=REGION.RING_DIM;
circle(s,x+12,y+12,10,C.cyanDeep,1);rect(s,x+9,y+11,7,2,C.earthDark);
}
const WATER=Object.freeze({
BLUE_T:0.10,
BLUE_FULL:0.26,
SOLID:0.35,
FALL_LUM:0.62,
FALL_SAT:0.34,
FALL_W:0.85,
SHRINK:4,
});
function floodSky(solid,w,h,x0,x1){
const sky=new Uint8Array(w*h);
const stack=[];
for (let x=x0;x<x1;x++) if (solid[x]){sky[x]=1;stack.push(x);}
while (stack.length){
const i=stack.pop();
const x=i%w,y=(i/w)|0;
if (x>x0){const j=i-1;if (solid[j]&&!sky[j]){sky[j]=1;stack.push(j);}}
if (x<x1-1){const j=i+1;if (solid[j]&&!sky[j]){sky[j]=1;stack.push(j);}}
if (y>0){const j=i-w;if (solid[j]&&!sky[j]){sky[j]=1;stack.push(j);}}
if (y<h-1){const j=i+w;if (solid[j]&&!sky[j]){sky[j]=1;stack.push(j);}}
}
return sky;
}
function waterBoxBlur(src,w,h,r){
const tmp=new Float32Array(w*h),dst=new Float32Array(w*h),n=2*r+1;
for (let y=0;y<h;y++){
let acc=0;
for (let x=-r;x<=r;x++) acc+=src[y*w+Math.min(w-1,Math.max(0,x))];
for (let x=0;x<w;x++){
tmp[y*w+x]=acc/n;
acc+=src[y*w+Math.min(w-1,x+r+1)]-src[y*w+Math.min(w-1,Math.max(0,x-r))];
}
}
for (let x=0;x<w;x++){
let acc=0;
for (let y=-r;y<=r;y++) acc+=tmp[Math.min(h-1,Math.max(0,y))*w+x];
for (let y=0;y<h;y++){
dst[y*w+x]=acc/n;
acc+=tmp[Math.min(h-1,y+r+1)*w+x]-tmp[Math.min(h-1,Math.max(0,y-r))*w+x];
}
}
return dst;
}
function waterMorph(src,w,h,r,dilate){
const pick=dilate?Math.max:Math.min;
const tmp=new Float32Array(w*h),dst=new Float32Array(w*h);
for (let y=0;y<h;y++) for (let x=0;x<w;x++){
let v=src[y*w+x];
for (let k=-r;k<=r;k++) v=pick(v,src[y*w+Math.min(w-1,Math.max(0,x+k))]);
tmp[y*w+x]=v;
}
for (let y=0;y<h;y++) for (let x=0;x<w;x++){
let v=tmp[y*w+x];
for (let k=-r;k<=r;k++) v=pick(v,tmp[Math.min(h-1,Math.max(0,y+k))*w+x]);
dst[y*w+x]=v;
}
return dst;
}
function buildWaterMask(world){
const S=WATER.SHRINK,w=(world.w/S)|0,h=(world.h/S)|0;
const soft=new Float32Array(w*h),lum=new Float32Array(w*h),sat=new Float32Array(w*h);
const p=world.p,stride=world.w*4;
for (let y=0;y<h;y++){
for (let x=0;x<w;x++){
const o=(y*S+(S>>1))*stride+(x*S+(S>>1))*4;
const r=p[o]/255,g=p[o+1]/255,b=p[o+2]/255;
const i=y*w+x;
const mx=Math.max(r,g,b),mn=Math.min(r,g,b);
lum[i]=0.2126*r+0.7152*g+0.0722*b;
sat[i]=mx>0?(mx-mn)/mx:0;
soft[i]=Math.min(1,Math.max(0,((g+b)*0.5-r-WATER.BLUE_T)/(WATER.BLUE_FULL-WATER.BLUE_T)));
}
}
const solid=new Uint8Array(w*h);
for (let i=0;i<solid.length;i++) solid[i]=soft[i]>WATER.SOLID?1:0;
const half=(w/2)|0;
const skyA=floodSky(solid,w,h,0,half);
const skyB=floodSky(solid,w,h,half,w);
const m=new Float32Array(w*h);
for (let i=0;i<m.length;i++) m[i]=(skyA[i]||skyB[i])?0:soft[i];
const near=waterBoxBlur(m,w,h,6);
for (let i=0;i<m.length;i++){
if (near[i]>0.05&&!(skyA[i]||skyB[i])&&lum[i]>WATER.FALL_LUM&&sat[i]<WATER.FALL_SAT){
m[i]=Math.max(m[i],WATER.FALL_W);
}
}
let f=waterMorph(m,w,h,2,true);
f=waterMorph(f,w,h,2,false);
f=waterBoxBlur(f,w,h,2);f=waterBoxBlur(f,w,h,2);f=waterBoxBlur(f,w,h,2);
const out=new Uint8Array(w*h);
for (let i=0;i<out.length;i++) out[i]=Math.round(Math.min(1,Math.max(0,f[i]))*255);
return{w,h,p:out};
}
let ZERO_WATER=null;
function zeroWaterMask(){
if (!ZERO_WATER){const w=(WORLD_TEX_W/WATER.SHRINK)|0,h=(WORLD_TEX_H/WATER.SHRINK)|0;ZERO_WATER={w,h,p:new Uint8Array(w*h)};}
return ZERO_WATER;
}
function paintWorldPlates(atlas){
const stage=atlas.background;
if (stage.machine){
const s=atlas.world;
for (const[layer,ox] of[[stage.rear,0],[stage.near,WORLD_PLATE_W]]){
const rowBytes=layer.w*4;
for (let y=0;y<layer.h;y++) s.p.set(layer.p.subarray(y*rowBytes,(y+1)*rowBytes),(y*s.w+ox)*4);
}
atlas.waterMask=zeroWaterMask();
return;
}
if (!stage.graded){
const out=gradeLayers(stage.rear,stage.near);
stage.rear=out.rear;stage.near=out.near;stage.graded=true;
}
const s=atlas.world;
for (const[layer,ox] of[[stage.rear,0],[stage.near,WORLD_PLATE_W]]){
const rowBytes=layer.w*4;
for (let y=0;y<layer.h;y++) s.p.set(layer.p.subarray(y*rowBytes,(y+1)*rowBytes),(y*s.w+ox)*4);
}
atlas.waterMask=buildWaterMask(s);
}
function setBackgroundStage(atlas,index=0){
const stages=atlas.backgrounds;
const stage=Math.max(0,Math.min(stages.length-1,Math.trunc(Number.isFinite(index)?index:0)));
atlas.backgroundIndex=stage;
atlas.background=stages[stage];
return stage;
}
function paintWorld(atlas,backgroundIndex=atlas.backgroundIndex||0,art='STORY'){
selectArtSet(atlas,art);
if (atlas.artSet==='ARCADE') atlas.background=atlas.arcadeStage;
else setBackgroundStage(atlas,backgroundIndex);
paintWorldPlates(atlas);
}
function selectArtSet(atlas,art){
const key=art==='ARCADE'&&atlas.sets.ARCADE?'ARCADE':'STORY';
if (atlas.artSet===key) return false;
const set=atlas.sets[key];
atlas.surface.p=set.p;
atlas.swatch=set.swatch;atlas.C=set.C;atlas.palette=set.palette;atlas.islands=set.islands;atlas.fontIndex=set.fontIndex;
atlas.artSet=key;
return true;
}
function paintArtSet(A,paletteRecord,fontRecord,islands,islandSpec,heroSprites,islandSettle){
const palette=visualPalette(paletteRecord);
const C=Object.fromEntries(Object.entries(palette).map(([k,v])=>[k,color(v)]));
const s=surface(ATLAS_SIZE,ATLAS_SIZE,[0,0,0,0]);
paintHdSprites(s,REGION.SPRITES,heroSprites);
const swatchNames=Object.keys(palette).sort();
const swatch={};
swatchNames.forEach((name,i)=>{const x=REGION.SWATCH[0]+i*8;rect(s,x,REGION.SWATCH[1],8,8,C[name]);swatch[name]=[x,REGION.SWATCH[1]];});
const extra={
shade:[0,0,0,176],
cyanGhost:[32,196,215,82],
cyanWhisper:[32,196,215,38],
lavaGhost:[242,74,34,70],
lavaBloom:[242,74,34,18],
whiteGhost:[255,253,243,90],
};
for (const[name,rgba] of Object.entries(extra)){
const i=Object.keys(swatch).length;
const x=REGION.SWATCH[0]+i*8;
rect(s,x,REGION.SWATCH[1],8,8,rgba);
swatch[name]=[x,REGION.SWATCH[1]];
}
const[ix,iy]=REGION.ISLANDS;
const islandArt=settle(islands,islandSettle);
for (let y=0;y<islandArt.h;y++) s.p.set(islandArt.p.subarray(y*islandArt.w*4,(y+1)*islandArt.w*4),((iy+y)*s.w+ix)*4);
paintModernFont(s,{font_5x7:fontRecord},C);
const fontChars=Object.keys(fontRecord).sort();
const set={surface:s,p:s.p,swatch,C,palette,fontIndex:new Map(fontChars.map((c,i)=>[c,i])),islands:Object.freeze({origin:REGION.ISLANDS,masters:measureIslands(islands,islandSpec),bakeRegion:REGION.ISLAND_BAKE})};
paintSpentRing(s,C);
paintRingFx(s,C);
paintHdProps(s,C);
return set;
}
function buildAtlas(A,{backgrounds,islands,heroSprites,islandSpec,arcade=null}){
const story=paintArtSet(A,A.palette,A.font_5x7,islands,islandSpec,heroSprites,GRADE.ISLAND_SETTLE);
const sets={STORY:story};
let arcadeStage=null;
if (arcade){
sets.ARCADE=paintArtSet(A,arcade.palette,arcade.font||A.font_5x7,arcade.islands,arcade.islandSpec,heroSprites,0);
const graded=arcade.grade!==false;
arcadeStage={rear:graded?depthGrade(arcade.rear,ARCADE_DEPTH.REAR):arcade.rear,near:graded?depthGrade(arcade.near,ARCADE_DEPTH.NEAR):arcade.near,graded:true,machine:true,depthGraded:graded};
}
const atlas={surface:{w:story.surface.w,h:story.surface.h,p:story.p},world:surface(WORLD_TEX_W,WORLD_TEX_H,[0,0,0,0]),sets,artSet:'STORY',swatch:story.swatch,C:story.C,palette:story.palette,islands:story.islands,fontIndex:story.fontIndex,arcadeStage,backgrounds:[...backgrounds],background:backgrounds[0],backgroundIndex:0,modernFont:MODERN_FONT};
paintWorldPlates(atlas);
return atlas;
}
function fnv(bytes){let h=0x811c9dc5;for (let i=0;i<bytes.length;i++){h^=bytes[i];h=Math.imul(h,0x01000193);}return (h>>>0).toString(16).padStart(8,'0');}
function atlasDigest(atlas){
return{artSet:atlas.artSet,world:fnv(atlas.world.p),water:fnv(atlas.waterMask.p),atlas:fnv(atlas.surface.p),masters:atlas.islands.masters.map((m)=>m.id+':'+m.x+','+m.w+','+m.capTop+','+(m.topDecor||0)).join(' ')};
}
return{buildAtlas,paintWorld,selectArtSet,atlasDigest,REGION,SPRITE_CELL_PX,SPRITE_FRAME_COUNT,SPRITE_DRAW_OFFSET,spriteSourceOrigin,SPRITE_IDLE,idleSourceOrigin,RIDER_CELL_PX,RIDER_STATE_COUNT,RIDER_FRONT_ROW_OFFSET,riderSourceOrigin};
})();
__modules[25]=(()=>{
const FILM_TITLES=Object.freeze({
SKY_1:Object.freeze({numeral:"I",title:"CONTACT AND CARRY",boss:"DIAGNOSTIC GUARDIAN 1"}),
SKY_2:Object.freeze({numeral:"II",title:"MOTION ENVELOPES",boss:"DIAGNOSTIC GUARDIAN 2"}),
SKY_3:Object.freeze({numeral:"III",title:"PARALLAX AND CONTRAST",boss:"DIAGNOSTIC GUARDIAN 3"}),
SKY_4:Object.freeze({numeral:"IV",title:"SAVE AND RESTORE",boss:"DIAGNOSTIC GUARDIAN 4"}),
SKY_5:Object.freeze({numeral:"V",title:"CARTRIDGE RELEASE",boss:"DIAGNOSTIC GUARDIAN 5"}),
});
const SHOT_IDS=Object.freeze([
'C1_S1_WIDE','C1_S2_CLOSE','C1_S3_SIGNAL','C1_S4_OPPOSITION','C1_S5_CUT',
'C2_S1_WIDE','C2_S2_ALIGN','C2_S3_RELIEF','C2_S4_CLOSE','C2_S5_OVERLAY',
'C3_S1_SPLASH','C3_S2_BIND','C3_S3_OVERLOAD','C3_S4_BLACK_BREAK','C3_S5_PRESENT','C3_S6_LOOK',
'C4_S1_WIDE','C4_S2_REFUSAL','C4_S3_MEMORY','C4_S4_RELEASE','C4_S5_CONSENT','C4_S6_CUT',
'C5_S1_VICTORY','C5_S2_INSIDE','C5_S3_CONTROL','C5_S4_REFUSAL','C5_S5_BRANCH','C5_S6_CODA',
]);
const SHOT_CAPTIONS=Object.freeze(Object.fromEntries(SHOT_IDS.map((id,index)=>[id,{text:`DEV-00 DIAGNOSTIC PANEL ${String(index+1).padStart(2,'0')}. PRESENTATION CONTRACT VERIFIED.`}])));
const CAPTION_DELAY_TICKS=8;
const CAPTION_TICKS_PER_CHAR=0.8;
function filmTitle(A,filmId){
const authored=A?.story_strings?.CINEMA_TITLES?.[filmId];
if (authored&&typeof authored.title==='string') return{numeral:String(authored.numeral||FILM_TITLES[filmId]?.numeral||''),title:authored.title,boss:String(authored.boss||'')};
return FILM_TITLES[filmId]||null;
}
function captionFor(A,shotId){
const authored=A?.story_strings?.CINEMA_CAPTIONS?.[shotId];
if (typeof authored==='string') return authored?{text:authored}:null;
if (authored&&typeof authored.text==='string') return authored.text?authored:null;
return A?.story_strings?.EPISODE_BANNER==='DEV-00 SYSTEMS'?(SHOT_CAPTIONS[shotId]||null):null;
}
function bossLine(A,boss){
const authored=boss&&boss.lineId&&A.story_strings[boss.lineId];
return authored||(boss?boss.line:'');
}
function bossTitle(boss){
return boss?boss.title:'';
}
function typedText(text,t){
const n=Math.floor((t-CAPTION_DELAY_TICKS)/CAPTION_TICKS_PER_CHAR);
return n<=0?'':String(text).slice(0,n);
}
function wrapWords(text,maxChars){
const lines=[];let cur='';
for (const word of String(text).split(' ')){
const next=cur?`${cur} ${word}`:word;
if (next.length>maxChars&&cur){lines.push(cur);cur=word;}else cur=next;
}
if (cur) lines.push(cur);
return lines;
}
function speechRows(text,maxChars){
const s=String(text);
if (s.length<=maxChars) return[s];
const words=s.split(' ');
let best=null,bestScore=Infinity;
for (let i=1;i<words.length;i++){
const a=words.slice(0,i).join(' '),b=words.slice(i).join(' ');
if (a.length>maxChars||b.length>maxChars) continue;
const score=Math.max(a.length,b.length)-(/[.!?,;:-]$/.test(a)?6:0);
if (score<bestScore){bestScore=score;best=[a,b];}
}
return best||wrapWords(s,maxChars);
}
return{FILM_TITLES,filmTitle,bossLine,bossTitle,captionFor,typedText,wrapWords,speechRows,CAPTION_DELAY_TICKS,CAPTION_TICKS_PER_CHAR};
})();
__modules[26]=(()=>{
const{PANEL_LAYOUT,PANEL_VARIANTS,PANEL_W,WIDE_H,TALL_H,TALL_PANELS,PANEL_SCALE}=__modules[14];
const{filmTitle,bossLine,bossTitle,captionFor,typedText,wrapWords,speechRows,CAPTION_DELAY_TICKS,CAPTION_TICKS_PER_CHAR}=__modules[25];
const NG3_WINDOW=Object.freeze({x:0,y:84,w:256,h:146});
const NG3_CAPTION_Y=248;
const PANEL_FLAG=1;
const SHOT_DIRECTION=Object.freeze({
C1_S1_WIDE:{move:'push',to:1.06,focus:[60,80],fx:'embers'},
C1_S2_CLOSE:{move:'push',to:1.08,focus:[150,48],swap:{id:'C1_S2_CLOSE_B',mode:'hold',at:54,lead:8}},
C1_S3_SIGNAL:{move:'push',to:1.1,focus:[200,70],fx:'embers',beats:[{t:88,flash:'cyan'}]},
C1_S4_OPPOSITION:{move:'pan',zoom:1.1,from:[150,73],to:[178,60],glint:{at:84,x:172,y:29}},
C1_S5_CUT:{move:'down',beats:[{t:42,flash:'white'}]},
C2_S1_WIDE:{move:'down'},
C2_S2_ALIGN:{move:'pan',zoom:1.12,from:[110,73],to:[160,60],beats:[{t:108,flash:'cyan'}]},
C2_S3_RELIEF:{move:'push',to:1.08,focus:[150,60],fx:'embers'},
C2_S4_CLOSE:{move:'push',to:1.06,focus:[128,60],swap:{id:'C2_S4_CLOSE_B',mode:'blink',at:[78,104],len:7}},
C2_S5_OVERLAY:{move:'push',to:1.12,focus:[140,70],beats:[{t:108,shake:6}]},
C3_S1_SPLASH:{move:'push',to:1.05,focus:[110,60],fx:'sparks',beats:[{t:0,flash:'white',shake:12}]},
C3_S2_BIND:{move:'down',beats:[{t:48,flash:'cyan'}]},
C3_S3_OVERLOAD:{move:'push',to:1.06,focus:[170,60],swap:{id:'C3_S3_OVERLOAD_B',mode:'flicker',at:20},beats:[{t:72,shake:8},{t:78,flash:'white'}]},
C3_S4_BLACK_BREAK:{move:'push',to:1.05,focus:[128,110],fx:'embers',reveal:12,beats:[{t:12,flash:'red',shake:10}]},
C3_S5_PRESENT:{move:'pan',zoom:1.1,from:[110,60],to:[150,80],fx:'embers'},
C3_S6_LOOK:{move:'push',to:1.08,focus:[118,50],swap:{id:'C3_S6_LOOK_B',mode:'blink',at:[60,104],len:6}},
C4_S1_WIDE:{move:'push',to:1.06,focus:[140,80],fx:'embers'},
C4_S2_REFUSAL:{move:'push',to:1.05,focus:[150,60],swap:{id:'C4_S2_REFUSAL_B',mode:'talk'}},
C4_S3_MEMORY:{move:'still',beats:[{t:15,flash:'red'},{t:45,flash:'red'},{t:75,flash:'red'}]},
C4_S4_RELEASE:{move:'push',to:1.08,focus:[100,80],beats:[{t:72,shake:4}]},
C4_S5_CONSENT:{move:'push',to:1.05,focus:[128,70]},
C4_S6_CUT:{move:'up',beats:[{t:84,flash:'white'}]},
C5_S1_VICTORY:{move:'push',to:1.06,focus:[70,70],fx:'embers',beats:[{t:24,flash:'white',shake:6}]},
C5_S2_INSIDE:{move:'down',beats:[{t:132,flash:'white'}]},
C5_S3_CONTROL:{move:'push',to:1.12,focus:[165,42],swap:{id:'C5_S3_CONTROL_B',mode:'hold',at:120,lead:6},beats:[{t:120,shake:6}]},
C5_S4_REFUSAL:{move:'push',to:1.05,focus:[128,70],fx:'sparks',beats:[{t:75,flash:'white',shake:9}]},
C5_S5_BRANCH:{move:'up',beats:[{t:120,flash:'white'}]},
C5_S6_CODA:{move:'push',to:1.06,focus:[60,80],fx:'rain'},
});
const CRAWL_PANELS=Object.freeze([
Object.freeze({id:'P_S1_BREAK',from:0}),
Object.freeze({id:'P_S2_RIDERS',from:3}),
Object.freeze({id:'P_S3_BOND',from:6}),
Object.freeze({id:'P_S4_FIRST_RING',from:8}),
]);
const clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));
const THEATER_MAX_TICKS=540;
function theaterShotTicks(A,shot){
const cap=captionFor(A,shot.shotId);
if (!cap) return shot.durationTicks+60;
const chars=cap.text.length+(cap.who?cap.who.length:0);
const typedEnd=CAPTION_DELAY_TICKS+Math.ceil(cap.text.length*CAPTION_TICKS_PER_CHAR);
return clamp(Math.max(shot.durationTicks+90,typedEnd+90+Math.ceil(chars*3.5)),0,THEATER_MAX_TICKS);
}
const THEATER_ACTS=Object.freeze([
Object.freeze({film:'SKY_1',numeral:'I',boss:'GUARDIAN_1',legacy:'KEEPER',milestone:5}),
Object.freeze({film:'SKY_2',numeral:'II',boss:'GUARDIAN_2',legacy:'HEIR',milestone:11}),
Object.freeze({film:'SKY_3',numeral:'III',boss:'GUARDIAN_3',legacy:'BINDER',milestone:17}),
Object.freeze({film:'SKY_4',numeral:'IV',boss:'GUARDIAN_4',legacy:'WITNESS',milestone:23}),
Object.freeze({film:'SKY_5',numeral:'V',boss:'GUARDIAN_5',legacy:'WARDEN',milestone:29}),
]);
const theaterBossLog=[];
function resolveTheaterBoss(A,act){
const bosses=(A.bosses&&A.bosses.bosses)||[];
const byId=(id)=>bosses.find((b)=>b.id===id)||null;
const canonical=byId(act.boss);
if (canonical) return canonical;
const legacy=byId(act.legacy);
if (legacy) return legacy;
const fallback=bosses.find((b)=>b.milestone===act.milestone)||null;
const note={act:act.numeral,wanted:act.boss,resolved:fallback?fallback.id:null,via:'MILESTONE'};
theaterBossLog.push(note);
console.warn('THEATER_BOSS_FALLBACK',JSON.stringify(note));
return fallback;
}
const THEATER_BOSS_FREEZE=50;
function theaterSequence(A,reel){
const items=[{kind:'CRAWL'}];
const clips=new Map(((reel&&reel.clips)||[]).map((c)=>[c.id,c]));
const shots=theaterShots(A);
let firstPlay=true;
THEATER_ACTS.forEach((act,k)=>{
for (const id of[`A${k+1}_ROUND`,`A${k+1}_BOSS`]){
const clip=clips.get(id);
if (!clip) continue;
const boss=clip.what==='BOSS'?resolveTheaterBoss(A,act):null;
const line=boss?bossLine(A,boss).toUpperCase():'';
items.push({
kind:'PLAY',clip,first:firstPlay,act:`ACT ${act.numeral}`,
label:boss?`ROUND ${String(clip.level).padStart(2,'0')} - ${bossTitle(boss)}`:`ROUND ${String(clip.level).padStart(2,'0')}`,
boss:!!boss,line,lines:boss?speechRows(line,40):[],
length:clip.facts.ticks+(boss?THEATER_BOSS_FREEZE:0),
});
firstPlay=false;
}
for (const shot of shots.filter((x)=>x.filmId===act.film)) items.push({kind:'SHOT',shot,length:theaterShotTicks(A,shot)});
});
return items;
}
function theaterShots(A){
return[...A.cinema.shots].sort((a,b)=>(a.filmId<b.filmId?-1:a.filmId>b.filmId?1:a.shotIndex-b.shotIndex));
}
const smooth=(p)=>p*p*(3-2*p);
const hash=(n)=>{let x=Math.imul(n|0,374761393);x=Math.imul(x^(x>>>13),1274126177);return ((x^(x>>>16))>>>0)/4294967296;};
function panelCamera(id,dir,t,duration){
const H=TALL_PANELS.includes(id)?TALL_H:WIDE_H;
const p=smooth(clamp((t-6)/Math.max(1,duration-24),0,1));
const view=(zoom,cx,cy)=>{
const uw=PANEL_W/zoom,vh=WIDE_H/zoom;
return[clamp(cx-uw/2,0,PANEL_W-uw),clamp(cy-vh/2,0,H-vh),uw,vh];
};
switch (dir&&dir.move){
case 'down':return[0,(H-WIDE_H)*p,PANEL_W,WIDE_H];
case 'up':return[0,(H-WIDE_H)*(1-p),PANEL_W,WIDE_H];
case 'push':{
const z=1+((dir.to||1)-1)*p,[fx,fy]=dir.focus||[128,73];
return view(z,128+(fx-128)*p,73+(fy-73)*p);
}
case 'pan':{
const[ax,ay]=dir.from,[bx,by]=dir.to;
return view(dir.zoom||1.1,ax+(bx-ax)*p,ay+(by-ay)*p);
}
default:return[0,0,PANEL_W,WIDE_H];
}
}
function activeSwap(dir,t,captionTyping,holding=false,tick=0){
const s=dir&&dir.swap;
if (!s) return null;
switch (s.mode){
case 'hold':return t>=s.at||(t>=s.at-(s.lead||0)&&((t>>1)&1))?s.id:null;
case 'blink':return (holding?(tick%170)<(s.len||6):s.at.some((a)=>t>=a&&t<a+(s.len||6)))?s.id:null;
case 'flicker':return t>=s.at&&hash((holding?tick:t)>>1)<0.55?s.id:null;
case 'talk':return captionTyping&&((t>>2)&1)?s.id:null;
default:return null;
}
}
function drawPanel(scene,id,cam,dst,z,variant=null){
const S=PANEL_SCALE;
const[u0,v0,uw,vh]=cam,[dx,dy,dw,dh]=dst;
const[px,py]=PANEL_LAYOUT[id];
scene.add(dx,dy,dw,dh,px+u0*S,py+v0*S,uw*S,vh*S,z,PANEL_FLAG);
const v=variant&&PANEL_VARIANTS[variant];
if (!v||v.base!==id) return;
const[rx,ry,rw,rh]=v.rect,[qx,qy]=PANEL_LAYOUT[variant];
const x0=Math.max(rx,u0),x1=Math.min(rx+rw,u0+uw),y0=Math.max(ry,v0),y1=Math.min(ry+rh,v0+vh);
if (x1<=x0||y1<=y0) return;
const kx=dw/uw,ky=dh/vh;
scene.add(dx+(x0-u0)*kx,dy+(y0-v0)*ky,(x1-x0)*kx,(y1-y0)*ky,qx+(x0-rx)*S,qy+(y0-ry)*S,(x1-x0)*S,(y1-y0)*S,z-.001,PANEL_FLAG);
}
const SHAKE=[[2,-1],[-2,1],[1,2],[-1,-2],[2,0],[0,1],[-1,0],[1,-1],[0,0]];
function panelParticles(scene,fx,tick,W,z){
if (!fx) return;
const{x,y,w,h}=W;
if (fx==='embers'||fx==='sparks'){
const n=fx==='sparks'?22:16;
for (let i=0;i<n;i++){
const speed=fx==='sparks'?.9+(i%4)*.35:.3+(i%5)*.08;
const px=x+((i*53+Math.sin((tick+i*31)*.04)*5+512)%(w-1));
const py=y+h-2-((tick*speed+i*41)%(h-3));
const big=i%4===0;
scene.swatch(fx==='sparks'?(i%3?'goldLight':'white'):(i%3?'ember':'lavaHot'),px,py,big?1:2/3,big?1:2/3,z);
}
}else if (fx==='rain'){
for (let i=0;i<38;i++){
const px=x+2+((i*37+tick*2)%(w-3)),py=y+((i*53+tick*5)%(h-6));
for (let k=0;k<3;k++) scene.swatch(i%4?'cyanGhost':'chromeLight',px-k*2/3,py+k*2,1/3,2,z);
}
}
}
function buildPanelStage(scene,ctx,Z){
const{shot,t}=ctx;
const id=shot.shotId,dir=SHOT_DIRECTION[id]||{move:'still'};
const W=NG3_WINDOW;
scene.swatch('black',0,0,256,384,Z.BG);
let jx=0,jy=0,flash=null,flashStart=-1;
for (const b of dir.beats||[]){
if (b.shake&&t>=b.t&&t<b.t+b.shake)[jx,jy]=SHAKE[(t-b.t)%SHAKE.length];
if (b.flash&&t>=b.t&&t<b.t+3){flash=b.flash;flashStart=b.t;}
}
const cap=captionFor(scene.A,id);
const holding=t>=shot.durationTicks;
const length=ctx.theater?ctx.theater.length:shot.durationTicks;
const shownText=!cap?'':holding&&!ctx.theater?cap.text:typedText(cap.text,t);
const typing=!!cap&&shownText.length<cap.text.length;
if (!(dir.reveal&&t<dir.reveal)){
const cam=panelCamera(id,dir,t,length);
drawPanel(scene,id,cam,[W.x+jx,W.y+jy,W.w,W.h],Z.BG-.02,activeSwap(dir,t,typing,holding,ctx.tick));
const g=dir.glint;
if (g&&t>=g.at&&t<g.at+30&&((t-g.at)<6||((t>>3)&1))){
const[u0,v0,uw,vh]=cam;
const gx=W.x+jx+(g.x-u0)*(W.w/uw),gy=W.y+jy+(g.y-v0)*(W.h/vh);
if (gx>W.x+2&&gx<W.x+W.w-3&&gy>W.y+1&&gy<W.y+W.h-3){
scene.swatch('lavaHot',gx-1,gy,2,1,Z.BG-.04);
if ((t-g.at)<4) scene.swatch('lavaGhost',gx-2,gy-1,4,3,Z.BG-.035);
}
}
panelParticles(scene,dir.fx,ctx.tick,{x:W.x+jx,y:W.y+jy,w:W.w,h:W.h},Z.BG-.05);
}
if (flash){
scene.swatch(flash==='red'?'lavaGhost':flash==='cyan'?'cyanGhost':'whiteGhost',W.x,W.y,W.w,W.h,Z.BG-.06);
if (flash==='white'&&t===flashStart) scene.swatch('white',W.x,W.y,W.w,W.h,Z.BG-.065);
}
const film=filmTitle(scene.A,ctx.filmId);
if (film){
scene.text(film.numeral,10,40,Z.HUD,1,'CYAN');
scene.text(film.title,10+(film.numeral.length+1)*6,40,Z.HUD,1,'GOLD');
for (let i=0;i<ctx.shotCount;i++) scene.swatch(i===ctx.shotIndex?'cyanLight':i<ctx.shotIndex?'cyanDark':'navySoft',246-(ctx.shotCount-i)*6,42,4,3,Z.HUD);
}
if (film&&ctx.shotIndex===0&&t>4&&t<44&&(t<38||(t&1))){
const rows=speechRows(film.title,19);
const grow=(rows.length-1)*16;
scene.swatch('shade',0,W.y+50-grow/2,256,46+grow,Z.HUD+.02);
scene.textCentered(`CHAPTER ${film.numeral}`,W.y+58-grow/2,Z.HUD+.01,1,128,'CYAN');
rows.forEach((row,i)=>scene.textCentered(row,W.y+72-grow/2+i*16,Z.HUD+.01,2,128,'GOLD'));
}
if (cap){
let y=NG3_CAPTION_Y;
if (cap.who){scene.text(cap.who,10,y,Z.HUD,1,'GOLD');y+=12;}
const typed=shownText;
const lines=wrapWords(cap.text,39);
const top=y;
let used=0;
for (const line of lines){
const visible=typed.slice(used,used+line.length);
used+=line.length+1;
if (visible) scene.text(visible,10,y,Z.HUD,1,'WHITE');
y+=12;
}
if (typing&&typed.length>0&&(ctx.tick&8)){
let rem=typed.length,li=0;
while (li<lines.length-1&&rem>lines[li].length){rem-=lines[li].length+1;li++;}
scene.swatch('cyanLight',10+rem*6,top+li*12+6,5,1,Z.HUD);
}
}
const out=ctx.theater?length-t:Infinity;
if (t<3||out<=2) scene.swatch('black',0,0,256,384,Z.HUD+.04);
else if (t<7||out<=6) scene.swatch('shade',W.x,W.y,W.w,W.h,Z.HUD+.035);
drawAdvanceAffordance(scene,ctx,holding,Z);
}
function drawAdvanceAffordance(scene,ctx,holding,Z,[ax,ay]=[238,318]){
if (ctx.skipTicks>0){
scene.swatch('cyanDeep',186,368,62,3,Z.HUD+.01);
scene.swatch('cyan',187,369,Math.floor(60*ctx.skipTicks/ctx.skipHold),1,Z.HUD);
scene.text(ctx.theater?'EXIT':'SKIP',162,365,Z.HUD,1,'DIM');
return;
}
if (ctx.theater){
if (ctx.theater.first&&ctx.t<180) scene.text('HOLD TO EXIT',178,374,Z.HUD,1,'DIM');
return;
}
if (holding){
if ((ctx.tick>>4)&1||(ctx.tick&15)<10){
const bob=(ctx.tick>>3)&1;
for (let r=0;r<4;r++) scene.swatch('cyanLight',ax+r,ay+r+bob,7-r*2,1,Z.HUD);
}
if (ctx.shotIndex===0) scene.textCentered('FLAP: NEXT   HOLD: SKIP',374,Z.HUD,1,128,'DIM');
}else if (ctx.shotIndex===0&&ctx.t<150){
scene.text('HOLD TO SKIP',178,374,Z.HUD,1,'DIM');
}
}
function crawlPanel(paragraph){
let pick=null;
for (const p of CRAWL_PANELS) if (paragraph>=p.from) pick=p;
return pick;
}
return{theaterSequence,THEATER_BOSS_FREEZE,buildPanelStage,crawlPanel,drawPanel,panelParticles};
})();
__modules[27]=(()=>{
const{wrappedDelta}=__modules[4];
const{arenaContent}=__modules[7];
const OX=14*256,OY=19*256;
function createPilot(A,{lead=14,reserve=6,idle=false,lastEdge:startEdge=false}={}){
let lastEdge=startEdge;
const leadSub=lead*256;
const pilot=function pilot(s){
if (idle) return{left:false,right:false,flapEdge:false,flapHeld:false};
const content=arenaContent(A,s),p=s.player;
let tx=128*256,ty=150*256;
const rings=content.rings||[];
const dist=(x,y)=>Math.abs(wrappedDelta(p.x,x))+Math.abs(y-p.y);
const nearest=(list,at)=>{let best=null,bd=Infinity;for (const it of list){const[x,y]=at(it),d=dist(x,y);if (d<bd){bd=d;best=it;}}return best;};
const mounted=s.actors.filter((a)=>a.lifecycle==='MOUNTED'||a.lifecycle==='REMOUNTING');
const loose=s.actors.filter((a)=>a.lifecycle==='EGG'||a.lifecycle==='HATCHING'||a.kind==='RIDER');
const ringAt=(r)=>[r.center[0]*256-OX,r.center[1]*256-OY];
if (content.kind==='BOSS'&&s.boss.phase==='RINGS'){
const r=nearest(rings.filter((_,i)=>!(s.boss.ringsMask&(1<<i))),ringAt);
if (r)[tx,ty]=ringAt(r);
}else if (mounted.length){
const a=nearest(mounted,(m)=>[m.x,m.y]);tx=a.x;ty=a.y-leadSub;
}else if (loose.length){
const a=nearest(loose,(m)=>[m.x,m.y]);tx=a.x;ty=a.y;
}else if (content.kind!=='BOSS'){
const r=rings.find((q)=>!(s.objectives.ringMask&(1<<(q.order-1))));
if (r)[tx,ty]=ringAt(r);
}
const dx=wrappedDelta(p.x,tx);
const lava=p.y+25*256>s.world.lavaY-30*256;
let want=p.y>ty&&p.vy>-300;
if (p.wing<reserve&&!lava) want=false;
if (lava) want=true;
const edge=want&&p.flapCooldown===0&&!lastEdge;
lastEdge=edge;
return{left:dx<-3*256,right:dx>3*256,flapEdge:edge,flapHeld:edge};
};
pilot.lastEdge=()=>lastEdge;
return pilot;
}
return{createPilot};
})();
__modules[28]=(()=>{
const{Game}=__modules[13];
const{createPilot}=__modules[27];
const REEL_PATH='generated/theater-reel.json';
function validReel(reel){
return!!(reel&&reel.version===1&&Array.isArray(reel.clips)&&reel.clips.every((c)=>c&&c.id&&c.snapshot&&c.snapshot.sim&&c.ticks>0&&c.facts));
}
function createClipRunner(A,clip){
let game,pilot,t,ended,held=null;
const reset=()=>{
game=new Game(A,{mode:'CAMPAIGN',seed:clip.seed,state:JSON.parse(JSON.stringify(clip.snapshot))});
pilot=createPilot(A,{lead:clip.lead,idle:clip.idle,lastEdge:clip.lastEdge});
t=0;ended=false;held=null;
};
reset();
return{
clip,
get game(){return game;},
get lastEdge(){return pilot.lastEdge();},
get t(){return t;},
get ended(){return ended;},
get state(){return held||game.state;},
step(){
if (ended) return null;
const before=clip.what==='BOSS'?structuredClone(game.state):null;
const r=game.tick(pilot(game.state));
t+=1;
if (t>=clip.ticks||game.state.sim.shell!=='PLAY'){
ended=true;
if (before&&game.state.sim.shell!=='PLAY') held=before;
}
return r;
},
};
}
return{REEL_PATH,validReel,createClipRunner};
})();
__modules[29]=(()=>{
const{SPRITE_RANGES:R}=__modules[22];
const clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));
const wrappedPixels=(dx)=>dx>128?dx-256:dx<-128?dx+256:dx;
const pose=(range,phase)=>range[0]+clamp(Math.floor(clamp(phase,0,.999999)*(range[1]-range[0]+1)),0,range[1]-range[0]);
class BirdAnimation{
constructor(){this.actors=new Map();}
forget(key){this.actors.delete(key);}
sample(key,input){
const{tick,world,x=0,vx=0,vy=0,facing=1,grounded=false,
flapAge=-1,landingGap=Infinity,hurt=false,
tumble=false,victory=false,threat=false,joust=false,
verticalAscent=false,footingTicks}=input;
let m=this.actors.get(key);
if (m&&m.tick===tick&&m.world===world) return m.frame;
if (!m||m.world!==world||tick<m.tick||tick-m.tick>120){
m={tick,world,x,vx,vy,facing,grounded,runPhase:0,
launchAt:-Infinity,dropAt:-Infinity,landAt:-Infinity,turnAt:-Infinity,
flapAt:-Infinity,hurtAt:-Infinity,bankAt:-Infinity,
hurt:false,frame:R.NEUTRAL[0]};
if (grounded&&footingTicks>0&&footingTicks<=10) m.landAt=tick-footingTicks+1;
}
const dt=Math.max(0,tick-m.tick);
const newFlapAt=flapAge>=0?tick-flapAge:-Infinity;
const newFlap=newFlapAt>m.flapAt;
if (newFlap) m.flapAt=newFlapAt;
if (dt>0){
if (m.grounded&&!grounded){
if (vy<0||newFlap) m.launchAt=tick;
else m.dropAt=tick;
}
if (!m.grounded&&grounded) m.landAt=tick;
if (facing!==m.facing) m.turnAt=tick;
if (grounded&&m.grounded) m.runPhase+=Math.abs(wrappedPixels((x-m.x)/256))/4;
if (!grounded&&!newFlap){
if (Math.abs(vx-m.vx)/dt>=10||facing!==m.facing){
m.bankAt=tick;
}
}
}
if (hurt&&!m.hurt) m.hurtAt=tick;
const age=(name)=>tick-m[name];
const beatAge=age('flapAt');
let frame;
if (tumble) frame=pose(R.DEATH,(tick%24)/24);
else if (age('hurtAt')<12) frame=pose(R.HIT,age('hurtAt')/12);
else if (victory) frame=pose(R.FLAP,(tick%48)/48);
else if (grounded){
if (age('landAt')<10) frame=pose(R.LANDING,age('landAt')/10);
else if (age('turnAt')<6) frame=pose(R.GROUND_AIR,age('turnAt')/6);
else if (Math.abs(vx)>20) frame=pose(R.RUN,m.runPhase/20%1);
else if (threat) frame=pose(R.NEUTRAL,.25+(tick%12)/48);
else frame=pose(R.NEUTRAL,((tick+(typeof key==='number'?key*17:0))%96)/96);
}else if (verticalAscent&&vy<-360&&Math.abs(vx)<140) frame=pose(R.VERTICAL_ASCENT,(tick%18)/18);
else if (age('launchAt')<10&&m.flapAt<=m.launchAt) frame=pose(R.TAKEOFF,age('launchAt')/10);
else if (age('dropAt')<8&&m.flapAt<m.dropAt) frame=pose(R.GROUND_AIR,age('dropAt')/8);
else if (beatAge<4) frame=pose(R.IMPULSE,beatAge/4);
else if (beatAge<12) frame=pose(R.FLAP,(beatAge-4)/8);
else if (beatAge<18) frame=pose(R.AIR_TRANSITION,(beatAge-12)/6);
else if (landingGap<30&&vy>0){
frame=pose(R.LANDING,1-landingGap/30);
}else if (vy>=650) frame=pose(R.DART,((tick-Math.max(m.flapAt,0))%10)/10);
else if (joust) frame=pose(R.DART,Math.abs(vx)>180?.8:.25);
else if (age('bankAt')<10&&Math.abs(vx)>60) frame=pose(vx<0?R.BANK_LEFT:R.BANK_RIGHT,age('bankAt')/10);
else if (vy<-90) frame=pose(R.CLIMB,clamp((-vy-90)/600,0,1));
else if (vy>150) frame=pose(R.DESCENT,clamp((vy-150)/550,0,1));
else frame=pose(R.GLIDE,(tick%40)/40);
Object.assign(m,{tick,world,x,vx,vy,facing,grounded,hurt,frame});
this.actors.set(key,m);
if (this.actors.size>128) for (const[id,old] of this.actors) if (tick-old.tick>300) this.actors.delete(id);
return frame;
}
}
return{BirdAnimation};
})();
__modules[30]=(()=>{
const{actOf}=__modules[6];
const{floorDiv}=__modules[4];
const{ascentMetrics,bitCount,campaignAscentActive}=__modules[11];
const{SHIMMER_TICKS}=__modules[5];
const ASCENT_NORMAL_SCALE=2;
const ASCENT_CAMERA_TRAVEL=336;
const ASCENT_SECTOR_SPAN=ASCENT_CAMERA_TRAVEL;
const ASCENT_FALL_FOLLOW_Y=230;
const ASCENT_RISE_FOLLOW_Y=48;
const PLAYER_SPRITE_ANCHOR_Y=25;
const clamp=(n,lo,hi)=>Math.max(lo,Math.min(hi,n));
const ACTS=Object.freeze([
Object.freeze({act:1,start:1,boss:5}),
Object.freeze({act:2,start:6,boss:11}),
Object.freeze({act:3,start:12,boss:17}),
Object.freeze({act:4,start:18,boss:23}),
Object.freeze({act:5,start:24,boss:29}),
]);
function actRecord(level){
const act=actOf(level);
return ACTS[act-1];
}
function actCameraBounds(record){
const normalCount=record.boss-record.start;
return{
actInitialTop:ASCENT_CAMERA_TRAVEL,
actSummitTop:-((normalCount-1)*ASCENT_SECTOR_SPAN),
};
}
function ascentProfile(A,s,content){
if (!campaignAscentActive(s,content)) return arcadeAscentProfile(A,s,content);
const level=content.kind==='BOSS'?content.milestone:content.level;
const act=actOf(level);
const record=actRecord(level);
const bounds=actCameraBounds(record);
if (content.kind==='BOSS'){
const baseY=bounds.actSummitTop;
return{
active:true,
key:'A'+act+':B'+level,
act,
level,
kind:'BOSS',
scaleY:1,
baseY,
initialTop:baseY,
summitTop:baseY,
targetTop:baseY,
travel:0,
progressSteps:bitCount(s.boss.ringsMask),
maxSteps:3,
metrics:null,
bounds,
};
}
const sector=level-record.start;
const baseY=-(sector*ASCENT_SECTOR_SPAN);
const initialTop=baseY+ASCENT_CAMERA_TRAVEL;
const metrics=ascentMetrics(s,content);
const progressSteps=metrics.progressSteps;
let targetTop=initialTop-Math.round(ASCENT_CAMERA_TRAVEL*progressSteps/6);
if (s.player.invulnerableTicks>SHIMMER_TICKS) targetTop=initialTop;
return{
active:true,
key:'A'+act+':L'+level,
act,
level,
kind:'NORMAL',
scaleY:ASCENT_NORMAL_SCALE,
baseY,
initialTop,
summitTop:baseY,
targetTop,
travel:initialTop-targetTop,
progressSteps,
maxSteps:6,
metrics,
bounds,
};
}
function withCamera(profile,cameraTop=profile?.targetTop??0){
if (!profile) return null;
const range=Math.max(1,profile.bounds.actInitialTop-profile.bounds.actSummitTop);
const backgroundProgress=clamp((profile.bounds.actInitialTop-cameraTop)/range,0,1);
return{...profile,cameraTop,travel:profile.initialTop-cameraTop,backgroundProgress};
}
function ascentCameraTarget(A,s,profile){
if (!profile||profile.kind!=='NORMAL') return profile?.targetTop??0;
const subpixels=A.sim_constants.subpixelsPerPixel||256;
const playerTop=floorDiv(s.player.y,subpixels);
const fallSpeed=Math.max(0,floorDiv(s.player.vy,subpixels));
const followLine=ASCENT_FALL_FOLLOW_Y-clamp(fallSpeed*3,0,12);
const fallFollowTop=profile.baseY
+(playerTop+PLAYER_SPRITE_ANCHOR_Y)*profile.scaleY
-PLAYER_SPRITE_ANCHOR_Y
-followLine;
const riseFollowTop=profile.baseY
+(playerTop+PLAYER_SPRITE_ANCHOR_Y)*profile.scaleY
-PLAYER_SPRITE_ANCHOR_Y-ASCENT_RISE_FOLLOW_Y;
const readableTop=Math.min(profile.targetTop,riseFollowTop);
return clamp(Math.max(readableTop,fallFollowTop),profile.summitTop,profile.initialTop);
}
function projectY(profile,localY){
return profile?profile.baseY+localY*profile.scaleY-profile.cameraTop:localY;
}
function projectAnchoredY(profile,localTop,anchorY){
return profile?profile.baseY+(localTop+anchorY)*profile.scaleY-profile.cameraTop-anchorY:localTop;
}
class AscentCamera{
constructor(A){this.A=A;this.top=null;this.key='';this.act=0;this.lastTick=null;}
reset(){this.top=null;this.key='';this.act=0;this.lastTick=null;}
resolve(s,content){
const profile=ascentProfile(this.A,s,content);
if (!profile){this.reset();return null;}
const cameraTarget=ascentCameraTarget(this.A,s,profile);
const changedAct=this.top===null||this.act!==profile.act;
const changedKey=this.key!==profile.key;
if (changedAct||(changedKey&&profile.kind==='BOSS')) this.top=cameraTarget;
this.key=profile.key;
this.act=profile.act;
const elapsed=this.lastTick===null?0:Math.max(0,Math.min(5,s.sim.tick-this.lastTick));
this.lastTick=s.sim.tick;
for (let i=0;i<elapsed;i++){
const delta=cameraTarget-this.top;
if (delta===0) break;
const followingFall=delta>0;
const step=followingFall
?Math.max(3,Math.min(16,Math.ceil(Math.abs(delta)*.32)))
:Math.max(1,Math.min(10,Math.ceil(Math.abs(delta)*.18)));
this.top+=Math.sign(delta)*Math.min(Math.abs(delta),step);
}
return{...withCamera(profile,Math.round(this.top)),cameraTarget};
}
}
const ARCADE_CLIMB_COURSES=8;
function arcadeAscentProfile(A,s,content){
if (!s||s.sim.mode!=='ARCADE'||!content||content.kind!=='ARCADE') return null;
const course=Math.max(1,content.course||1);
const lap=Math.floor((course-1)/ARCADE_CLIMB_COURSES);
const sector=(course-1)%ARCADE_CLIMB_COURSES;
const bounds={actInitialTop:ASCENT_CAMERA_TRAVEL,actSummitTop:-((ARCADE_CLIMB_COURSES-1)*ASCENT_SECTOR_SPAN)};
const baseY=-(sector*ASCENT_SECTOR_SPAN);
const initialTop=baseY+ASCENT_CAMERA_TRAVEL;
const rings=Math.max(1,content.rings.length);
const taken=Math.min(rings,bitCount((s.objectives.ringMask>>>0)&((2**rings)-1)));
const metrics=ascentMetrics(s,content);
const steps=metrics.active?metrics.progressSteps:taken,maxSteps=metrics.active?6:rings;
let targetTop=initialTop-Math.round(ASCENT_CAMERA_TRAVEL*steps/maxSteps);
if (s.player.invulnerableTicks>SHIMMER_TICKS) targetTop=initialTop;
return{
active:true,arcade:true,
key:'ARC'+lap+':C'+course,
act:1000+lap,
level:course,
kind:'NORMAL',
scaleY:ASCENT_NORMAL_SCALE,
baseY,initialTop,summitTop:baseY,targetTop,
travel:initialTop-targetTop,
progressSteps:steps,maxSteps,
metrics:metrics.active?metrics:null,
bounds,
};
}
return{ascentProfile,withCamera,projectY,projectAnchoredY,AscentCamera};
})();
__modules[31]=(()=>{
const{ascentMetrics,bitCount}=__modules[11];
const{arenaContent}=__modules[7];
const JOUST_MAX=11;
const two=(n)=>String(Math.max(0,n|0)).padStart(2,'0');
function hudModel(A,view){
const s=view.state;
const live=view.screen==='GAME'&&s.sim.shell!=='CINEMA_SKY'&&s.sim.shell!=='ATTRACT';
const content=view.content||(live?arenaContent(A,s):null);
const arcade=s.sim.mode==='ARCADE';
const trueScore=Math.max(0,Math.trunc(s.sim.score||0));
const carry=Math.floor(trueScore/1000000);
const score=String(trueScore%1000000).padStart(6,'0');
const position=arcade
?{a:'S',av:two(view.arcade?.course||0),b:'T',bv:String(content?.tier||1)}
:{a:'L',av:two(s.circuit.levelCursor),b:'W',bv:two(s.circuit.waveCursor)};
const ring={visible:false,value:0,max:6,due:false,subdued:false,boss:false};
const rival={visible:false,value:0,max:0,due:false,subdued:false};
const boss={visible:false,phase:'',remaining:0,hits:3,text:''};
if (content&&content.kind==='BOSS'){
const hitsToDefeat=3;
if (s.boss.phase==='RINGS') Object.assign(ring,{visible:true,value:bitCount(s.boss.ringsMask),max:content.rings.length,boss:true});
else if (s.boss.phase==='TRANSITION') Object.assign(boss,{visible:true,phase:'TRANSITION',text:A.story_strings.BOSS_READY});
else if (s.boss.phase==='DUEL'){
const remaining=Math.max(0,hitsToDefeat-(s.boss.hits|0));
Object.assign(boss,{visible:true,phase:'DUEL',remaining,hits:hitsToDefeat,text:'◆'.repeat(remaining)+'◇'.repeat(hitsToDefeat-remaining)});
}
}else if (content){
if (!arcade){
const m=view.ascent?.metrics||ascentMetrics(s,content);
Object.assign(ring,{visible:true,value:m.ringSteps,max:6});
Object.assign(rival,{visible:true,value:m.resolved,max:m.total});
const legacyCombatDue=s.circuit.levelCursor>s.circuit.waveCursor,legacyFlightDue=s.circuit.waveCursor>s.circuit.levelCursor;
const gateShut=m.active&&m.ringSteps<6&&m.ringSteps+1>m.allowedOrder;
const combatDue=legacyCombatDue||gateShut,flightDue=legacyFlightDue;
ring.due=flightDue;ring.subdued=combatDue;
rival.due=combatDue;rival.subdued=flightDue;
}else{
const total=content.rosterList?content.rosterList.length:0;
const m=view.ascent?.metrics||ascentMetrics(s,content);
Object.assign(ring,{visible:true,value:bitCount(s.objectives.ringMask),max:(content.rings||[]).length||6});
Object.assign(rival,{visible:true,value:Math.max(0,Math.min(total,s.objectives.spawnCursor-s.objectives.authorizedActorIds.length)),max:total});
const gateShut=m.active&&m.ringSteps<6&&m.ringSteps+1>m.allowedOrder;
rival.due=gateShut;ring.subdued=gateShut;
}
}
const joust={value:Math.max(0,Math.min(JOUST_MAX,s.sim.lives|0)),max:JOUST_MAX};
let toast='',toastKind='';
if (view.banner&&view.banner.until>view.renderTick){toast=view.banner.text;toastKind='event';}
if (view.saveWarning){toast='SAVE NOT UPDATED';toastKind='warning';}
if (s.sim.shell==='PAUSE'){toast='PAUSED';toastKind='pause';}
return{live,paused:s.sim.shell==='PAUSE',score,trueScore,carry,mode:s.sim.mode,position,ring,rival,boss,joust,toast:live?toast:'',toastKind:live?toastKind:''};
}
function hudAriaLabel(m){
const parts=[`Score ${m.trueScore}.`,...(m.mode==='ARCADE'?[`Stage ${Number(m.position.av)}.`,`Tier ${Number(m.position.bv)}.`]:[`Level ${Number(m.position.av)}.`,`Wave ${Number(m.position.bv)}.`])];
if (m.ring.visible) parts.push(`${m.ring.boss?'Boss ring':'Ring'} ${m.ring.value} of ${m.ring.max}${m.ring.due?', due':''}.`);
if (m.rival.visible) parts.push(`Rivals ${m.rival.value} of ${m.rival.max}${m.rival.due?', due':''}.`);
if (m.boss.visible) parts.push(m.boss.phase==='DUEL'?`Boss: ${m.boss.remaining} of ${m.boss.hits} hits remaining.`:'Boss ready.');
parts.push(`${m.joust.value} of ${m.joust.max} Joust Marks remaining.`);
return parts.join(' ');
}
function createExternalHud(root,{toastRoot=null,srRoot=null}={}){
const $=(sel)=>root.querySelector(sel);
const score=$('#hud-score b')||$('#hud-score'),crown=$('#hud-crown'),scoreBox=$('#hud-score'),posA=$('#hud-pos-a'),posB=$('#hud-pos-b'),posAv=$('#hud-pos-av'),posBv=$('#hud-pos-bv');
let lastCarry=null,glitchTimer=null;
function rollover(finalText){
if (!scoreBox) return;
clearInterval(glitchTimer);
const glyphs='0123456789#%&$@';
let n=0;
scoreBox.classList.add('is-rollover');
glitchTimer=setInterval(()=>{
n+=1;
if (n>8){clearInterval(glitchTimer);glitchTimer=null;score.textContent=finalText;scoreBox.classList.remove('is-rollover');return;}
score.textContent=Array.from(finalText,()=>glyphs[Math.floor(Math.random()*glyphs.length)]).join('');
},32);
}
const ringEl=$('#hud-ring'),ringVal=$('#hud-ring b'),rivalEl=$('#hud-rival'),rivalVal=$('#hud-rival b');
const bossEl=$('#hud-boss'),bossVal=$('#hud-boss b');
const joustVal=$('#hud-joust b'),joustBar=$('#hud-joust i');
let signature='',ariaSig='',lastJoust=null,lastToast='';
return{
update(model){
const next=JSON.stringify(model);
if (next===signature) return;
signature=next;
root.classList.toggle('is-live',model.live);
root.setAttribute('aria-hidden',model.live?'false':'true');
if (!glitchTimer) score.textContent=model.score;
if (crown){crown.hidden=!(model.carry>0);crown.dataset.carry=model.carry>1?String(model.carry):'';}
if (model.live&&lastCarry!==null&&model.carry>lastCarry) rollover(model.score);
lastCarry=model.live?model.carry:null;
posA.textContent=model.position.a;if (posB) posB.textContent=model.position.b;posAv.textContent=model.position.av;posBv.textContent=model.position.bv;
ringEl.hidden=!model.ring.visible;
ringEl.classList.toggle('is-due',model.ring.due);ringEl.classList.toggle('is-subdued',model.ring.subdued);ringEl.classList.toggle('is-boss',model.ring.boss);
ringVal.textContent=`${two(model.ring.value)}/${two(model.ring.max)}`;
rivalEl.hidden=!model.rival.visible;
rivalEl.classList.toggle('is-due',model.rival.due);rivalEl.classList.toggle('is-subdued',model.rival.subdued);
rivalVal.textContent=`${two(model.rival.value)}/${two(model.rival.max)}`;
bossEl.hidden=!model.boss.visible;
bossVal.textContent=model.boss.text;
joustVal.textContent=`${two(model.joust.value)}/${model.joust.max}`;
if (joustBar) joustBar.style.setProperty('--joust',String(model.joust.value/model.joust.max));
root.classList.toggle('is-low',model.joust.value<=2);
const aria=hudAriaLabel(model);
if (aria!==ariaSig){ariaSig=aria;root.setAttribute('aria-label',aria);}
if (model.live&&lastJoust!==null&&model.joust.value<lastJoust&&srRoot) srRoot.textContent=`${model.joust.value} Joust Marks remaining.`;
lastJoust=model.live?model.joust.value:null;
if (toastRoot&&model.toast!==lastToast){
lastToast=model.toast;
toastRoot.textContent=model.toast;
toastRoot.dataset.kind=model.toastKind;
toastRoot.classList.toggle('is-on',!!model.toast);
}
},
};
}
return{hudModel,createExternalHud};
})();
__modules[32]=(()=>{
const{buildIslandLayout,bakeIslandLayout,islandGeometry}=__modules[18];
const{REGION,SPRITE_CELL_PX,SPRITE_FRAME_COUNT,SPRITE_DRAW_OFFSET,spriteSourceOrigin,SPRITE_IDLE,idleSourceOrigin,RIDER_CELL_PX,RIDER_STATE_COUNT,riderSourceOrigin}=__modules[24];
const{WORLD_SCALE,WORLD_PLATE_W,MATERIAL_WORLD,MATERIAL_ARCADE_ISLAND}=__modules[16];
const{floorDiv,wrappedDelta}=__modules[4];
const{BirdAnimation}=__modules[29];
const{SHIMMER_TICKS,FLAP_COOLDOWN_TICKS}=__modules[5];
const{decodePhase,CLASS_FLAP_PERIOD}=__modules[9];
const{arenaContent}=__modules[7];
const{crawlPanel,drawPanel,panelParticles,buildPanelStage}=__modules[26];
const{bossLine,bossTitle,speechRows}=__modules[25];
const{filmShots}=__modules[10];
const{eggSource,shimmerSource,crownSource,EGG_FRAMES,EGG_CELL,SHIMMER_CELL,CROWN_CELL}=__modules[23];
const{standingPlatform,overlapsX}=__modules[8];
const{BIRD_BOX}=__modules[5];
const{emitLiveRing,emitLockedRing,emitRingBurst,ringKindFor}=__modules[20];
const{ascentProfile,withCamera,projectY,projectAnchoredY}=__modules[30];
const NEAR_ZOOM=4/3;
const NEAR_WINDOW=Object.freeze([256/NEAR_ZOOM,384/NEAR_ZOOM]);
const NEAR_TRAVEL=768-NEAR_WINDOW[1];
const REAR_TRAVEL=96;
const Z=Object.freeze({BG:0.95,WORLD:0.9,GEOLOGY:0.84,PLATFORM:0.76,RING:0.68,EGG:0.6,ACTOR:0.5,PLAYER:0.4,HUD:0.2,OVERLAY:0.1,TOP:0.05});
const CLASS_ROW=Object.freeze({PLAYER:0,BOUNDER:1,HUNTER:2,SHADOW:3,GUARDIAN_CAPTAIN:4,WARDEN:5,BOSS:4});
const WARDEN_MILESTONE=29;
function bossSpriteRow(record){
if (!record) return CLASS_ROW.GUARDIAN_CAPTAIN;
return record.level===WARDEN_MILESTONE?CLASS_ROW.WARDEN:CLASS_ROW.GUARDIAN_CAPTAIN;
}
const EPISODE_BANNER='STRUTHIO CONSOLE';
const MODERN_TONE=Object.freeze({WHITE:0,CYAN:1,LAVA:2,GOLD:3,DIM:4});
class Scene{
constructor(A,atlas){
this.A=A;
this.atlas=atlas;
this.fontChars=Object.keys(A.font_5x7).sort();
this.fontIndex=new Map(this.fontChars.map((c,i)=>[c,i]));
this.list=[];
this.birdMotion=new BirdAnimation();
this.attachmentSets=Object.freeze({HERO_RIDER:atlas.riderAttachments});
this.riderEnabled=false;
this.verticalAscent=false;
this.panels=null;
}
reset(){this.list.length=0;}
add(x,y,w,h,sx,sy,sw,sh,z,flags=0){this.list.push({x,y,w,h,sx,sy,sw,sh,z,flags});}
swatch(name,x,y,w,h,z){
const[sx,sy]=this.atlas.swatch[name]||this.atlas.swatch.white;
this.add(x,y,w,h,sx+1,sy+1,1,1,z);
}
text(str,x,y,z=Z.HUD,scale=1,tone='WHITE'){
let cx=x;
const font=this.atlas.modernFont;
const index=this.atlas.fontIndex||this.fontIndex;
for (const ch of String(str).toUpperCase()){
const i=index.has(ch)?index.get(ch):index.get('?')??index.get(' ');
if (i!==undefined&&ch!==' '){
this.add(cx,y,5*scale,7*scale,
font.x+(i%font.cols)*font.cellW+1,
font.y+(MODERN_TONE[tone]??0)*font.rows*font.cellH+Math.floor(i/font.cols)*font.cellH,
font.glyphW,font.glyphH,z);
}
cx+=6*scale;
}
return cx;
}
textCentered(str,y,z=Z.HUD,scale=1,cx=128,tone='WHITE'){
const w=Math.max(0,String(str).length*6*scale-scale);
return this.text(str,Math.floor(cx-w/2),y,z,scale,tone);
}
world(ascent=null){
const rest=1-(ascent?Math.max(0,Math.min(1,ascent.backgroundProgress||0)):0);
const S=WORLD_SCALE;
const snap=(v)=>Math.round(v*S);
const arcade=!!ascent?.arcade;
if (arcade){
this.add(0,0,256,384,0,snap(rest*384),256*S,384*S,Z.WORLD+0.02,MATERIAL_WORLD);
this.add(0,0,256,384,WORLD_PLATE_W,snap(rest*512),256*S,256*S,Z.WORLD,MATERIAL_WORLD);
return;
}
const[nw,nh]=NEAR_WINDOW;
this.add(0,0,256,384,0,snap(rest*REAR_TRAVEL),256*S,384*S,Z.WORLD+0.02,MATERIAL_WORLD);
this.add(0,0,256,384,WORLD_PLATE_W+snap((256-nw)/2),snap(rest*NEAR_TRAVEL),nw*S,nh*S,Z.WORLD,MATERIAL_WORLD);
}
sprite(row,frame,x,y,facing,z,flags=0){
const resolved=((frame%SPRITE_FRAME_COUNT)+SPRITE_FRAME_COUNT)%SPRITE_FRAME_COUNT;
const[sx,sy]=frame===SPRITE_IDLE?idleSourceOrigin(row):spriteSourceOrigin(REGION.SPRITES,row,resolved);
const material=flags||2+row;
if (facing<0) this.add(x,y,32,32,sx+SPRITE_CELL_PX,sy,-SPRITE_CELL_PX,SPRITE_CELL_PX,z,material);
else this.add(x,y,32,32,sx,sy,SPRITE_CELL_PX,SPRITE_CELL_PX,z,material);
}
rider(state,front,x,y,facing,z){
const resolved=Math.max(0,Math.min(RIDER_STATE_COUNT-1,state|0));
const[sx,sy]=riderSourceOrigin(resolved,front);
if (facing<0) this.add(x,y,32,32,sx+RIDER_CELL_PX,sy,-RIDER_CELL_PX,RIDER_CELL_PX,z,9);
else this.add(x,y,32,32,sx,sy,RIDER_CELL_PX,RIDER_CELL_PX,z,9);
}
spentRing(cx,cy,z=Z.RING){
const[sx,sy]=REGION.RING_DIM;
this.add(cx-12,cy-12,24,24,sx,sy,24,24,z);
}
}
const toPx=(v)=>floorDiv(v,256);
function lerpPos(prev,cur,alpha){
if (!prev) return cur;
let dx=cur-prev;
if (dx>32768) dx-=65536;
else if (dx<-32768) dx+=65536;
return prev+Math.trunc(dx*alpha);
}
function birdLandingGap(entity,world){
if (entity.vy<=0) return Infinity;
const feet=entity.y/256+BIRD_BOX.b;
let nearest=Infinity;
for (const p of world.platforms){
if (!p.collidable) continue;
const gap=p.rect[1]-feet;
if (gap<0||gap>=30) continue;
const lead=Math.min(12,gap/Math.max(.25,entity.vy/256));
const x=entity.x+entity.vx*lead;
if (overlapsX(x+BIRD_BOX.l*256,x+BIRD_BOX.r*256,p.rect[0]*256,(p.rect[0]+p.rect[2])*256)) nearest=Math.min(nearest,gap);
}
return nearest;
}
function joustAligned(entity,target){
if (!target) return false;
const dx=wrappedDelta(entity.x,target.x),dy=target.y-entity.y;
return Math.abs(dx)<40*256&&dx*entity.facing>0&&dy>=0&&dy<30*256;
}
function playerStroke(player){return player.flapCooldown>0?FLAP_COOLDOWN_TICKS-player.flapCooldown:-1;}
function actorStroke(actor){
const{flapCd}=decodePhase(actor.phase|0);
const period=CLASS_FLAP_PERIOD[actor.class]||6;
return flapCd>0?period-flapCd:-1;
}
function buildScene(scene,view){
const{A}=scene;
const s=view.state;
scene.reset();
if (view.screen==='MANUAL') return scene.list;
if (view.screen==='CRAWL') return buildCrawl(scene,view);
if (view.screen==='THEATER') return buildTheater(scene,view);
if (s.sim.shell==='ATTRACT') return scene.list;
if (s.sim.shell==='CINEMA_SKY'){
const c=s.cinema;
const shots=filmShots(A,c.filmId);
const shotIndex=Math.min(c.shotIndex,shots.length-1);
buildPanelStage(scene,{
shot:shots[shotIndex],t:c.shotTick,filmId:c.filmId,shotIndex,shotCount:shots.length,
tick:view.renderTick|0,skipTicks:c.skipTicks,skipHold:A.cinema.skipHoldTicks,
},Z);
return scene.list;
}
return buildWorldScene(scene,view);
}
function buildWorldScene(scene,view){
const{A}=scene;
const s=view.state;
const alpha=view.alpha??1;
const content=view.content||arenaContent(A,s);
const ascent=view.ascent||withCamera(ascentProfile(A,s,content));
const worldView=ascent===view.ascent?view:{...view,ascent};
scene.world(ascent);
for (const platform of s.world.platforms) drawPlatform(scene,platform,content,view.renderTick,ascent,view.musicDrive||{});
drawBossSpikes(scene,content,ascent);
drawAscentGate(scene,content,ascent);
drawRings(scene,s,content,ascent,view.renderTick|0);
drawActors(scene,worldView,alpha);
drawPlayer(scene,worldView,alpha);
applyWorldJolt(scene,worldView);
drawFeelFeedback(scene,worldView);
drawScorePopups(scene,worldView);
buildOverlays(scene,worldView,content);
return scene.list;
}
function islandPlan(scene,platform,content,ascent){
const scaleY=ascent?ascent.scaleY:1;
if (scene.islandLayoutSource!==content.platforms||scene.islandLayoutId!==content.contentId||scene.islandLayoutScale!==scaleY||scene.islandLayoutArt!==scene.atlas.artSet){
const islands=scene.atlas.islands;
scene.islandLayout=buildIslandLayout(content,islands.masters,scaleY);
scene.islandSlots=bakeIslandLayout(scene.islandLayout,content.platforms,scene.atlas.surface,islands.origin,islands.bakeRegion);
scene.islandLayoutSource=content.platforms;
scene.islandLayoutId=content.contentId;
scene.islandLayoutScale=scaleY;
scene.islandLayoutArt=scene.atlas.artSet;
scene.atlasDirty=true;
}
return scene.islandLayout.get(platform.id);
}
function drawBossSpikes(scene,content,ascent){
const spikes=content.kind==='BOSS'&&content.record?.duel?.spikes;
if (!Array.isArray(spikes)) return;
for (const spike of spikes){
const[x,authoredY,w,h]=spike.rect,y=projectY(ascent,authoredY);
scene.swatch('earthDark',x,y,w,h,Z.RING);
for (let row=0;row<h;row+=8){
const tooth=Math.min(w,4+(row%8));
const left=spike.side==='LEFT'?x:x+w-tooth;
scene.swatch('lava',left,y+row,tooth,Math.min(7,h-row),Z.RING-.006);
scene.swatch('lavaHot',spike.side==='LEFT'?left+tooth-2:left,y+row+2,2,Math.min(3,h-row-2),Z.RING-.009);
}
}
}
function drawPlatform(scene,platform,content,tick,ascent=null,drive=null){
if (platform.phase==='ABSENT'||platform.phase==='GONE'||platform.phase==='REMOVED') return;
const[x,y,width]=platform.rect;
const screenY=projectY(ascent,y);
const plan=islandPlan(scene,platform,content,ascent);
if (!plan) return;
if (plan.ground) drawGroundCourt(scene,platform,plan,x,screenY,width,tick,drive);
else drawIslandArt(scene,platform,plan,x,screenY,width,tick,drive);
}
function phaseOf(platform,tick,ground){
if (platform.phase==='RISING') return 2;
return (platform.phase==='WARN'||(platform.phase==='TRANSITION'&&!ground))&&((tick>>2)&1)?1:0;
}
function drawIslandArt(scene,platform,plan,x,y,width,tick,drive){
const phase=phaseOf(platform,tick,false);
const slot=scene.islandSlots?scene.islandSlots.get(platform.id):null;
for (let shift=-256;shift<=256;shift+=256){
const dx=x+shift;
if (dx+width<=0||dx>=256) continue;
drawIslandMaster(scene,plan,dx,y,width,plan.depth,plan.mirror,phase,tick,drive,slot);
}
}
const DECOR_Z=.004;
function drawGroundCourt(scene,platform,plan,x,y,width,tick,drive){
const phase=phaseOf(platform,tick,true);
if (plan.master.topDecor){
for (let shift=-256;shift<=256;shift+=256){
const dx=x+shift;
if (dx+width<=0||dx>=256) continue;
drawIslandMaster(scene,plan,dx,y,width,38,false,phase,tick,drive);
}
return;
}
for (let shift=-256;shift<=256;shift+=256){
for (let bay=0;bay*64<width;bay++){
const dx=x+shift+bay*64,w=Math.min(64,width-bay*64);
if (dx+w<=0||dx>=256) continue;
drawIslandMaster(scene,plan,dx,y,w,38,(bay&1)!==0,phase,tick+bay*7,drive);
}
}
}
function drawIslandMaster(scene,plan,x,y,width,depth,mirror,phase,tick,drive,slot=null){
const m=plan.master,[ox,oy]=scene.atlas.islands.origin;
const mat=scene.atlas.artSet==='ARCADE'?MATERIAL_ARCADE_ISLAND:0;
if (slot&&phase!==2){
const g=islandGeometry(plan,width);
if (slot.decorH) scene.add(x,y-g.decorDepth,width,g.decorDepth,slot.x,slot.decorY,slot.w,slot.decorH,Z.PLATFORM+DECOR_Z,mat);
scene.add(x,y,width,g.depth,slot.x,slot.y,slot.w,slot.h,Z.PLATFORM,mat);
scene.swatch(phase===1?'lavaHot':'kingdomGoldLight',x,y,width,phase===1?2/3:1/3,Z.PLATFORM-.012);
islandCurrent(scene,plan,x,y,g.sx,g.capDepth,g.bodyScale,mirror,phase,drive,tick);
return;
}
const rows=m.h-m.capTop,sx=width/m.w,sy=depth/rows;
const capRows=22,capDepth=Math.min(7,depth*.5),bodyScale=(depth-capDepth)/(rows-capRows);
if (phase===2){
for (let row=m.capTop;row<m.h;row+=9){
for (const run of m.opaqueRuns[row]){
const left=mirror?m.w-run[1]:run[0];
scene.swatch('lavaGhost',x+left*sx,y+(row-m.capTop)*sy,(run[1]-run[0])*sx,Math.min(sy,1/3),Z.PLATFORM);
}
}
for (let xx=0;xx<width;xx+=6) scene.swatch('kingdomCrimsonLight',x+xx,y,Math.min(3,width-xx),1/3,Z.PLATFORM-.01);
return;
}
const srcX=ox+m.x+(mirror?m.w:0),srcW=mirror?-m.w:m.w;
if (m.topDecor){const decorDepth=m.topDecor*sx;scene.add(x,y-decorDepth,width,decorDepth,srcX,oy+m.y+m.capTop-m.topDecor,srcW,m.topDecor,Z.PLATFORM+DECOR_Z,mat);}
scene.add(x,y,width,capDepth,srcX,oy+m.y+m.capTop,srcW,capRows,Z.PLATFORM,mat);
scene.add(x,y+capDepth,width,depth-capDepth,srcX,oy+m.y+m.capTop+capRows,srcW,rows-capRows,Z.PLATFORM,mat);
scene.swatch(phase===1?'lavaHot':'kingdomGoldLight',x,y,width,phase===1?2/3:1/3,Z.PLATFORM-.012);
islandCurrent(scene,plan,x,y,sx,capDepth,bodyScale,mirror,phase,drive,tick);
}
function islandCurrent(scene,plan,x,y,sx,capDepth,bodyScale,mirror,phase,drive,tick){
const beat=Math.max(drive?.downbeat||0,drive?.beat||0,(drive?.low||0)*.85);
if (!phase&&beat<.18) return;
const strong=phase===1||(beat>.7&&Math.sin((tick+plan.seed)*.09)>0);
const m=plan.master;
for (const r of m.signalRects){
const left=mirror?m.w-r.x-r.w:r.x;
const dy=signalY(r.y-m.capTop,capDepth,bodyScale),bottom=signalY(r.y+r.h-m.capTop,capDepth,bodyScale);
scene.swatch(strong?'lavaGhost':'lavaBloom',x+left*sx,y+dy,r.w*sx,bottom-dy,Z.PLATFORM-.006);
}
}
function signalY(row,capDepth,bodyScale){
return row<=22?row*capDepth/22:capDepth+(row-22)*bodyScale;
}
const ASCENT_GATE_LABEL=false;
function drawAscentGate(scene,content,ascent){
if (!ascent||ascent.kind!=='NORMAL'||!content.ringsProgression||!ascent.metrics||ascent.metrics.allowedOrder>=6) return;
const ring=content.rings[Math.min(content.rings.length-1,ascent.metrics.allowedOrder-1)];
const y=Math.round(projectY(ascent,ring.center[1]-8));
if (y<18||y>356) return;
for (let x=0;x<256;x+=16){
const hot=((x>>4)+ascent.metrics.allowedOrder)%3===0;
scene.swatch(hot?'cyanDark':'cyanWhisper',x,y,hot?9:6,1,Z.GEOLOGY-.055);
}
if (ASCENT_GATE_LABEL) scene.text('ALT '+String(ascent.metrics.allowedOrder).padStart(2,'0'),5,Math.max(5,y-10),Z.RING+.015,1,'DIM');
}
function ringAge(scene,key,tick){
const memo=scene.ringIntro||(scene.ringIntro=new Map());
if (!memo.has(key)){
if (memo.size>32) memo.clear();
memo.set(key,tick);
}
const age=tick-memo.get(key);
return age<0?Infinity:age;
}
function drawRings(scene,s,content,ascent=null,tick=0){
const add=scene.add.bind(scene);
if (content.kind==='BOSS'){
if (s.boss.phase!=='RINGS') return;
content.rings.forEach((r,i)=>{
const cy=projectY(ascent,r.center[1]);
if (s.boss.ringsMask&(1<<i)) scene.spentRing(r.center[0],cy);
else emitLiveRing(add,'GREEN',r.center[0],cy,tick+i*7,ringAge(scene,`${s.world.contentId}:${r.id??i}`,tick),Z.RING);
});
return;
}
const next=content.rings.find((r)=>!(s.objectives.ringMask&(1<<(r.order-1))));
if (!next) return;
const metrics=ascent&&ascent.metrics;
const open=!metrics||!metrics.active||next.order<=metrics.allowedOrder;
const cy=projectY(ascent,next.center[1]);
const kind=ringKindFor(next.color);
if (open) emitLiveRing(add,kind,next.center[0],cy,tick,ringAge(scene,`${s.world.contentId}:${next.id??next.order}`,tick),Z.RING);
else emitLockedRing(add,kind,next.center[0],cy,Z.RING);
}
function drawActors(scene,view,alpha){
const s=view.state;
const ascent=view.ascent;
for (const actor of s.actors){
if (actor.lifecycle==='REMOVED') continue;
const prev=view.prev&&view.prev.get(actor.id);
const x=toPx(lerpPos(prev&&prev.x,actor.x,alpha));
const y=projectAnchoredY(ascent,toPx(lerpPos(prev&&prev.y,actor.y,alpha)),25);
if (actor.vsBird){drawVsBird(scene,view,actor,x,y);continue;}
if (actor.lifecycle==='SPAWNING'||actor.lifecycle==='REMOUNTING'){
const f=((view.renderTick>>2)+actor.id)&3;
if (actor.timer>8||(view.renderTick&2)){const[sx,sy]=shimmerSource(f);scene.add(x,y-4,32,32,sx,sy,SHIMMER_CELL,SHIMMER_CELL,Z.ACTOR);}
continue;
}
if (actor.lifecycle==='HATCHING'){
const k=1-Math.max(0,Math.min(1,actor.timer/60));
const[ex,ey]=eggSource(EGG_FRAMES.OPEN);
scene.add(x+8.5,y+13.5,12,12,ex,ey,EGG_CELL,EGG_CELL,Z.EGG);
if (k>.45&&(view.renderTick>>1&1)) scene.swatch('ringLight',x+13,y+15.5-k*2,2,2,Z.EGG-.005);
continue;
}
if (actor.lifecycle==='EGG'){
const t=actor.timer;
let f=t>240?EGG_FRAMES.INTACT:t>120?EGG_FRAMES.CRACK1:EGG_FRAMES.CRACK2;
if (t<=60&&((view.renderTick>>2)&3)!==0) f=((view.renderTick>>3)&1)?EGG_FRAMES.TILT_L:EGG_FRAMES.TILT_R;
const[ex,ey]=eggSource(f);
scene.add(x+8.5,y+13.5,12,12,ex,ey,EGG_CELL,EGG_CELL,Z.EGG);
continue;
}
if (actor.lifecycle==='DISMOUNTED'){
const f=((view.renderTick>>2)+actor.id)&1?EGG_FRAMES.TILT_L:EGG_FRAMES.TILT_R;
const[ex,ey]=eggSource(f);
scene.add(x+8.5,y+12.5,12,12,ex,ey,EGG_CELL,EGG_CELL,Z.ACTOR);
continue;
}
const row=actor.class==='BOSS'?bossSpriteRow(view.content?.record):(CLASS_ROW[actor.class]??1);
const hurt=actor.class==='BOSS'?(s.boss.hurt|0):0;
const nearGroundCadence=standingPlatform(actor.x,actor.y,BIRD_BOX,s.world)!==null;
const frame=scene.birdMotion.sample(actor.id,{
...actor,tick:s.sim.tick,world:s.world.contentId,grounded:nearGroundCadence,
flapAge:actorStroke(actor),flapPeriod:CLASS_FLAP_PERIOD[actor.class]||8,
landingGap:birdLandingGap(actor,s.world),hurt:hurt>0,
threat:actor.class==='BOSS'&&s.boss.phase==='DUEL',joust:joustAligned(actor,s.player),
verticalAscent:scene.verticalAscent,
});
if (hurt>0&&(s.sim.tick&4)){drawBossPips(scene,s,x,y);continue;}
drawMount(scene,row,frame,x,y,actor.facing,Z.ACTOR);
if (actor.class==='BOSS'){
const[cx0,cy0]=crownSource((view.renderTick>>4)&1);
scene.add(x+11,y-8,10,10,cx0,cy0,CROWN_CELL,CROWN_CELL,Z.ACTOR-0.01);
drawBossPips(scene,s,x,y);
}
}
}
function drawVsBird(scene,view,b,x,y){
const s=view.state;
const frame=scene.birdMotion.sample(b.id,{
...b,tick:s.sim.tick,world:s.world.contentId,grounded:!!b.groundedPlatformId,
flapAge:playerStroke(b),flapPeriod:FLAP_COOLDOWN_TICKS,
landingGap:birdLandingGap(b,s.world),tumble:b.lavaPhase==='SINK',
joust:joustAligned(b,s.player),verticalAscent:scene.verticalAscent,
});
if (b.invulnerableTicks>0&&(s.sim.tick&2)) return;
drawMount(scene,0,frame,x,y,b.facing,Z.ACTOR,null,scene.playerMaterial||0);
}
function drawBossPips(scene,s,x,y){
if (s.boss.phase!=='DUEL') return;
const left=3-Math.max(0,Math.min(3,s.boss.hits|0));
for (let i=0;i<3;i++){
const px=x+8+i*6,py=y-15,lit=i<left;
scene.swatch(lit?'lavaHot':'shade',px+1,py,2,4,Z.ACTOR-.012);
scene.swatch(lit?'goldLight':'chromeDark',px,py+1,4,2,Z.ACTOR-.013);
}
}
function drawPlayer(scene,view,alpha){
const player=view.state.player;
if (player.invulnerableTicks>SHIMMER_TICKS){scene.birdMotion.forget('player');return;}
const prev=view.prevPlayer;
const x=toPx(lerpPos(prev&&prev.x,player.x,alpha));
const y=projectAnchoredY(view.ascent,toPx(lerpPos(prev&&prev.y,player.y,alpha)),25);
const s=view.state;
const frame=scene.birdMotion.sample('player',{
...player,tick:s.sim.tick,world:s.world.contentId,grounded:!!player.groundedPlatformId,
flapAge:playerStroke(player),flapPeriod:FLAP_COOLDOWN_TICKS,
landingGap:birdLandingGap(player,s.world),tumble:player.lavaPhase==='SINK',
victory:s.sim.shell==='WINNER',hurt:view.feel?.active&&view.feel.kind==='CLASH',
joust:s.actors.some(actor=>actor.lifecycle==='MOUNTED'&&joustAligned(player,actor)),
verticalAscent:scene.verticalAscent,
});
if (player.invulnerableTicks>0&&(s.sim.tick&2)) return;
drawMount(scene,0,frame,x,y,player.facing,Z.PLAYER,scene.riderEnabled?'HERO_RIDER':null,scene.playerMaterial||0);
}
function applyWorldJolt(scene,view){
const feel=view.feel;
if (!feel?.active||(!feel.joltX&&!feel.joltY)) return;
for (const item of scene.list){
if (item.z>=Z.PLAYER&&item.z<Z.WORLD){
item.x+=feel.joltX;
item.y+=feel.joltY;
}
}
}
function feelSwatch(scene,tone,x,y,w=1,h=1,z=Z.PLAYER-.015){
for (const shift of[-256,0,256]){
const sx=x+shift;
if (sx+w>0&&sx<256&&y+h>0&&y<384) scene.swatch(tone,sx,y,w,h,z);
}
}
function drawFeelFeedback(scene,view){
const feel=view.feel;
if (!feel?.active||(feel.contentId&&feel.contentId!==view.state.world.contentId)) return;
const playerTop=feel.space==='WORLD'?null:projectAnchoredY(view.ascent,feel.y,25);
const cx=Math.round(feel.x+(feel.joltX||0));
const cy=Math.round((feel.space==='WORLD'
?projectY(view.ascent,feel.y)
:playerTop+(feel.space==='PLAYER_FEET'?25:13))+(feel.joltY||0));
const age=feel.age|0;
if (feel.kind==='LAND'){
const spread=4+age*2;
feelSwatch(scene,age<2?'cyanLight':'cyanDeep',cx-spread,cy,Math.max(2,7-age),1);
feelSwatch(scene,age<2?'cyan':'cyanWhisper',cx+spread-Math.max(2,7-age),cy,Math.max(2,7-age),1);
if (age<4){feelSwatch(scene,'goldLight',cx-2,cy-1,1,1);feelSwatch(scene,'goldLight',cx+2,cy-1,1,1);}
return;
}
if (feel.kind==='FLAP'){
const spread=3+age;
feelSwatch(scene,'cyanLight',cx-spread,cy+6+age,2,1);
feelSwatch(scene,'cyan',cx+spread-1,cy+5+age,2,1);
return;
}
if (feel.kind==='RING'||feel.kind==='RING_GREEN'){
emitRingBurst(scene.add.bind(scene),feel.kind==='RING_GREEN'?'GREEN':'MAGENTA',cx,cy,age,Z.RING-.02);
return;
}
const winning=feel.kind==='JOUST_WIN'||feel.kind==='BOSS_HIT';
const death=feel.kind==='DEATH';
const primary=death?'lavaHot':winning?'goldLight':'chromeLight';
const secondary=death?'ember':winning?'cyanLight':'cyan';
const reach=4+age*(death||feel.kind==='BOSS_HIT'?2:1);
feelSwatch(scene,primary,cx-reach,cy,Math.max(1,5-(age>>1)),1);
feelSwatch(scene,primary,cx+reach-Math.max(1,5-(age>>1)),cy,Math.max(1,5-(age>>1)),1);
feelSwatch(scene,secondary,cx,cy-reach,1,Math.max(1,5-(age>>1)));
feelSwatch(scene,secondary,cx,cy+reach-Math.max(1,5-(age>>1)),1,Math.max(1,5-(age>>1)));
if (age<6){
feelSwatch(scene,secondary,cx-reach+2,cy-reach+2,2,1);
feelSwatch(scene,secondary,cx+reach-3,cy+reach-2,2,1);
}
}
function drawMount(scene,row,frame,x,y,facing,z,attachmentSet=null,material=0){
const attach=attachmentSet?scene.attachmentSets?.[attachmentSet]?.frames?.[frame]:null;
for (const shift of[0,-256,256]){
const xx=x+shift-SPRITE_DRAW_OFFSET[0];
const yy=y-SPRITE_DRAW_OFFSET[1];
if (xx>-32&&xx<256){
const dx=attach?(facing<0?-attach.dx:attach.dx)/3:0;
const dy=attach?attach.dy/3:0;
if (attach) scene.rider(attach.riderState,false,xx+dx,yy+dy,facing,z+.003);
scene.sprite(row,frame,xx,yy,facing,z,material);
if (attach) scene.rider(attach.riderState,true,xx+dx,yy+dy,facing,z-.003);
}
}
}
function drawChevron(scene,cx,cy,dir,colour,z){
for (let i=0;i<7;i++){
const x=dir<0?cx+Math.abs(i-3):cx-Math.abs(i-3);
scene.swatch(colour,x,cy-3+i,2,1,z);
}
}
function buildOverlays(scene,view,content){
const s=view.state;
if (content.kind==='BOSS'&&(s.boss.phase==='TRANSITION'||s.boss.phase==='DUEL')){
const t=s.world.platforms[0].tick;
const boss=content.boss;
if (t>=boss.lineWindowTicks[0]&&t<=boss.lineWindowTicks[1]){
scene.swatch('shade',12,112,232,58,Z.OVERLAY+0.02);
scene.textCentered(bossTitle(boss),120,Z.OVERLAY,2,128,'GOLD');
speechRows(bossLine(scene.A,boss),37).forEach((row,i)=>scene.textCentered(row,146+i*9,Z.OVERLAY,1,128,'WHITE'));
}
}
if ((s.sim.mode==='CAMPAIGN'||s.sim.mode==='ARCADE')&&s.boss.phase==='NONE'){
const lead=s.actors[0];
const first=!!lead&&lead.lifecycle==='SPAWNING'&&lead.timer>SHIMMER_TICKS&&
s.objectives.spawnCursor===s.actors.length&&s.objectives.spawnCursor<=(content.openingPopulation||1);
if (first) scene.textCentered(s.sim.mode==='ARCADE'?`STAGE ${content.stage||1}`:`WAVE ${s.circuit.waveCursor}`,181,Z.OVERLAY,2,128,'GOLD');
if (first&&content.carried) scene.textCentered(`+${content.carried} CARRIED`,202,Z.OVERLAY,1,128,'LAVA');
}
if (s.player.invulnerableTicks>SHIMMER_TICKS&&s.sim.shell==='PLAY') scene.textCentered('READY',182,Z.OVERLAY,2,128,'CYAN');
if (s.sim.shell==='PAUSE'){
shade(scene);
scene.textCentered('PAUSED',164,Z.TOP,2,128,'CYAN');
scene.textCentered('BOTH WINGS TO RESUME',191,Z.TOP,1,128,'WHITE');
scene.textCentered(`SCORE ${fmt(s.sim.score)}`,210,Z.TOP,1,128,'GOLD');
}
if (s.sim.shell==='GAMEOVER'){
shade(scene);
scene.textCentered('GAME OVER',150,Z.TOP,2,128,'LAVA');
const info=view.gameOverInfo;
if (s.sim.mode==='ARCADE'){
scene.textCentered(`FINAL ${fmt(s.sim.score)}`,118,Z.TOP,1,128,'WHITE');
if (info&&info.isNew){if ((view.renderTick>>4)&1) scene.textCentered('NEW HIGH SCORE',130,Z.TOP,1,128,'GOLD');}
else if (info&&info.best) scene.textCentered(`HI ${fmt(info.best.score)}`,130,Z.TOP,1,128,'DIM');
if (info&&info.legacy) scene.textCentered('LEGACY RUN - NOT RECORDED',240,Z.TOP,1,128,'DIM');
}
const items=view.gameOverItems||['CONTINUE'];
const sel=view.gameOverIndex|0;
items.forEach((label,i)=>{
const y=180+i*16,on=i===sel;
if (on){
scene.swatch('shade',64,y-4,128,15,Z.TOP+.005);
scene.swatch('cyanDark',64,y-4,128,1,Z.TOP+.004);scene.swatch('cyanDark',64,y+10,128,1,Z.TOP+.004);
const blink=(view.renderTick>>4)&1;
drawChevron(scene,75+blink,y+3,1,'gold',Z.TOP);
drawChevron(scene,179-blink,y+3,-1,'gold',Z.TOP);
}
scene.textCentered(label,y,Z.TOP,1,128,on?'WHITE':'DIM');
});
scene.textCentered(items.length>1?'WINGS CHOOSE  BOTH SELECTS':'BOTH WINGS CONTINUE',222,Z.TOP,1,128,'DIM');
}
if (s.sim.shell==='WINNER'){
shade(scene);
wrapText(scene,scene.A.story_strings.WINNER,147,Z.TOP,1,224,'GOLD');
const w=view.winnerInfo;
scene.textCentered(`FINAL SCORE ${fmt(s.sim.score)}`,214,Z.TOP,1,128,'WHITE');
if (w&&w.isNew) scene.textCentered('NEW CAMPAIGN BEST',226,Z.TOP,1,128,'GOLD');
else if (w&&w.best) scene.textCentered(`BEST ${fmt(w.best.score)}`,226,Z.TOP,1,128,'DIM');
if (w&&w.continuesUsed===0) scene.textCentered('NO CONTINUE + RESERVE PAID',238,Z.TOP,1,128,'CYAN');
scene.textCentered('FLAP FOR TITLE',260,Z.TOP,1,128,'WHITE');
}
}
function shade(scene){scene.swatch('shade',0,0,256,384,Z.TOP+0.01);}
const POPUP_TICKS=48;
function drawScorePopups(scene,view){
const list=view.popups;
if (!list||!list.length) return;
const now=view.renderTick|0;
for (const p of list){
const age=now-p.tick;
if (age<0||age>POPUP_TICKS||(p.contentId&&p.contentId!==view.state.world.contentId)) continue;
if (age>POPUP_TICKS*.7&&(age&1)) continue;
const y=Math.round(projectY(view.ascent,p.y)-age*0.3);
if (y<4||y>370) continue;
scene.textCentered(p.text,y,Z.OVERLAY+.01,p.big?2:1,Math.max(14,Math.min(242,p.x)),p.tone);
}
}
const fmt=(n)=>Math.max(0,Math.trunc(n||0)).toLocaleString('en-US');
function wrapText(scene,text,y,z,scale,maxWidth,tone='WHITE'){
const words=String(text).split(' ');
const lines=[];
let current='';
for (const word of words){
const next=current?`${current} ${word}`:word;
if (next.length*6*scale>maxWidth&&current){lines.push(current);current=word;}
else current=next;
}
if (current) lines.push(current);
lines.forEach((line,i)=>scene.textCentered(line,y+i*9*scale,z,scale,128,tone));
return lines.length;
}
function buildTheater(scene,view){
const th=view.theater,item=th.item;
if (item.kind==='CRAWL') return buildCrawl(scene,view);
if (item.kind==='PLAY') return buildTheaterPlay(scene,view);
const{A}=scene;
const shot=item.shot;
const film=A.cinema.shots.filter((x)=>x.filmId===shot.filmId);
buildPanelStage(scene,{
shot,t:th.t,filmId:shot.filmId,shotIndex:shot.shotIndex,shotCount:film.length,
tick:view.renderTick|0,skipTicks:th.hold,skipHold:A.cinema.skipHoldTicks,
theater:{length:item.length,first:!!item.first},
},Z);
return scene.list;
}
function buildTheaterPlay(scene,view){
const th=view.theater,item=th.item;
buildWorldScene(scene,view);
const t=th.t,out=item.length-t;
if (t<30||(item.boss&&t<150)){
const lines=item.lines&&item.lines.length?item.lines:[item.line];
scene.swatch('shade',0,0,256,item.boss?22+12*lines.length:22,Z.TOP+.02);
scene.text(item.label,8,8,Z.TOP,1,'GOLD');
scene.text(item.act,248-item.act.length*6,8,Z.TOP,1,'CYAN');
if (item.boss){
let typed=Math.max(0,Math.floor((t-20)/2));
lines.forEach((row,i)=>{
const shown=row.slice(0,typed);
typed=Math.max(0,typed-row.length-1);
if (shown) scene.text(shown,Math.floor(128-(row.length*6-1)/2),22+i*12,Z.TOP,1,'WHITE');
});
}
}
if (th.hold>0){
scene.swatch('cyanDeep',186,368,62,3,Z.TOP+.01);
scene.swatch('cyan',187,369,Math.floor(60*th.hold/scene.A.cinema.skipHoldTicks),1,Z.TOP);
scene.text('EXIT',162,365,Z.TOP,1,'DIM');
}
else if (item.first&&t<180) scene.text('HOLD TO EXIT',178,374,Z.TOP,1,'DIM');
if (t<3||out<=2) scene.swatch('black',0,0,256,384,Z.TOP-.01);
else if (t<8||out<=8) scene.swatch('shade',0,0,256,384,Z.TOP-.005);
return scene.list;
}
const CRAWL_WINDOW=Object.freeze({x:0,y:44,w:256,h:146});
const CRAWL_READ_Y=270,CRAWL_TEXT_TOP=200;
function buildCrawl(scene,view){
const W=CRAWL_WINDOW;
scene.swatch('black',0,0,256,384,Z.BG);
const crawl=scene.A.story_strings.CRAWL;
const offset=Math.floor(view.crawlTicks/3);
let y=384-offset;
let reading=0;
const paraY=[];
for (let p=0;p<crawl.length;p++){
paraY.push(y);
if (y<=CRAWL_READ_Y) reading=p;
const lines=wrapLines(crawl[p],34);
for (const line of lines){
if (y>CRAWL_TEXT_TOP-8&&y<372) scene.textCentered(line,y,Z.HUD,1,128,p===crawl.length-1?'GOLD':'WHITE');
y+=10;
}
if (p===0||p===6){
if (y>CRAWL_TEXT_TOP&&y<368) scene.swatch('cyanDark',104,y+2,48,1,Z.HUD);
y+=12;
}else y+=10;
}
const pick=crawlPanel(reading);
const started=pick.from===0?offset:CRAWL_READ_Y-paraY[pick.from];
const zoom=1+Math.min(1,started/180)*0.06;
const uw=W.w/zoom,vh=W.h/zoom;
drawPanel(scene,pick.id,[(256-uw)/2,(146-vh)*0.6,uw,vh],[W.x,W.y,W.w,W.h],Z.BG-.02);
if (started<2) scene.swatch('black',W.x,W.y,W.w,W.h,Z.BG-.06);
else if (started<6) scene.swatch('shade',W.x,W.y,W.w,W.h,Z.BG-.06);
if (pick.id==='P_S1_BREAK') panelParticles(scene,'embers',view.crawlTicks,W,Z.BG-.05);
scene.swatch('black',0,W.y+W.h,256,CRAWL_TEXT_TOP-(W.y+W.h),Z.HUD-0.005);
scene.textCentered(scene.A.story_strings.EPISODE_BANNER||EPISODE_BANNER,16,Z.HUD-0.01,2,128,'GOLD');
scene.swatch('black',0,365,256,19,Z.HUD-0.005);
scene.textCentered(view.theater?'HOLD FLAP TO EXIT':'HOLD FLAP TO SKIP',374,Z.HUD-0.01,1,128,'DIM');
view.crawlDone=y<236;
return scene.list;
}
function wrapLines(text,columns){
const words=String(text).split(' ');
const lines=[];
let current='';
for (const word of words){
const next=current?`${current} ${word}`:word;
if (next.length>columns&&current){lines.push(current);current=word;}
else current=next;
}
if (current) lines.push(current);
return lines;
}
return{Scene,buildScene};
})();
__modules[33]=(()=>{
const KEY_MAP={
ArrowLeft:'LEFT_WING',KeyA:'LEFT_WING',
ArrowRight:'RIGHT_WING',KeyD:'RIGHT_WING',
Space:'BOTH_WINGS',ArrowUp:'BOTH_WINGS',KeyW:'BOTH_WINGS',Enter:'BOTH_WINGS',
};
const PAD_FLAP_BUTTONS=Object.freeze([0,1,2,3,4,5,6,7]);
const PAD_START_STANDARD=Object.freeze([8,9]);
const PAD_START_RAW=Object.freeze([8,9,10,11]);
const PAD_DPAD=Object.freeze({up:12,down:13,left:14,right:15});
const PAD_AXIS_ON=0.5;
const PAD_AXIS_CENTRED=0.25;
const PAD_AXIS_STUCK_POLLS=45;
const PAD_HAT_IDLE=1.05;
function hatDirections(v){
if (!(Math.abs(v)<=1.001)) return null;
const step=Math.max(0,Math.min(7,Math.round((v+1)*3.5)));
return{up:step===7||step<=1,right:step>=1&&step<=3,down:step>=3&&step<=5,left:step>=5};
}
class GamepadReader{
constructor(){this.profiles=new Map();}
profile(pad){
const key=`${pad.index}:${pad.id}`;
if (!this.profiles.has(key)) this.profiles.set(key,[]);
const profile=this.profiles.get(key);
pad.axes.forEach((v,i)=>{
const axis=profile[i]||(profile[i]={centred:false,hat:false,offPolls:0});
if (Math.abs(v)>PAD_HAT_IDLE) axis.hat=true;
else if (Math.abs(v)<PAD_AXIS_CENTRED) axis.centred=true;
else if (!axis.centred) axis.offPolls+=1;
});
return profile;
}
read(pads){
const out={connected:0,ids:[],left:false,right:false,up:false,down:false,flap:false,start:false};
for (const pad of pads||[]){
if (!pad||pad.connected===false) continue;
out.connected+=1;
out.ids.push(pad.id);
const profile=this.profile(pad);
const pressed=(i)=>!!(pad.buttons[i]&&pad.buttons[i].pressed);
const usable=(a)=>a&&!a.hat&&(a.centred||a.offPolls<=PAD_AXIS_STUCK_POLLS);
const axis=(i)=>(usable(profile[i])?pad.axes[i]:0);
const x=axis(0),y=axis(1);
const dir={left:x<-PAD_AXIS_ON,right:x>PAD_AXIS_ON,up:y<-PAD_AXIS_ON,down:y>PAD_AXIS_ON};
if (pad.mapping==='standard'||pad.buttons.length>=16){
for (const k of['left','right','up','down']) dir[k]=dir[k]||pressed(PAD_DPAD[k]);
}
profile.forEach((a,i)=>{
const hat=a.hat?hatDirections(pad.axes[i]):null;
if (hat) for (const k of['left','right','up','down']) dir[k]=dir[k]||hat[k];
});
for (const k of['left','right','up','down']) out[k]=out[k]||dir[k];
out.flap=out.flap||PAD_FLAP_BUTTONS.some(pressed);
out.start=out.start||(pad.mapping==='standard'?PAD_START_STANDARD:PAD_START_RAW).some(pressed);
}
return out;
}
}
class InputNormalizer{
constructor(inputAuthority){
this.regions=inputAuthority.regions;
this.queueMax=4;
this.flapBufferTicks=inputAuthority.flapBufferTicks||8;
this.chordWindowMs=inputAuthority.chordWindowMs||100;
this.flapQueue=[];
this.flapWaitTicks=0;
this.pointerOwner=new Map();
this.keysHeld=new Set();
this.padHeld=new Set();
this.padBlocked=new Set();
this.dartQueue=[];
this.dartedPointers=new Set();
this.lastWingPress=null;
this.mode='ATTRACT';
}
now(){return globalThis.performance?.now?.()??Date.now();}
queueFlap(kind='STRAIGHT',chord=false){
if (this.flapQueue.length>=this.queueMax) return false;
this.flapQueue.push({kind,chord});
this.flapWaitTicks=0;
return true;
}
queueWing(region){
const side=region==='LEFT_WING'?'LEFT':'RIGHT';
const now=this.now();
const last=this.lastWingPress;
if (last&&last.side!==side&&now-last.at<=this.chordWindowMs){
const pending=this.flapQueue[this.flapQueue.length-1];
if (pending&&pending.kind===last.side&&!pending.chord) Object.assign(pending,{kind:'STRAIGHT',chord:true});
else this.queueFlap('STRAIGHT',true);
this.lastWingPress=null;
return true;
}
this.lastWingPress={side,at:now};
return this.queueFlap(side,false);
}
queueDart(pointerId,side){
if (this.dartedPointers.has(pointerId)||this.dartQueue.length>=this.queueMax) return false;
this.dartedPointers.add(pointerId);
this.dartQueue.push(side==='LEFT_WING'?'LEFT':'RIGHT');
return true;
}
setMode(mode){if (mode!==this.mode){this.mode=mode;this.cleanup();}}
regionAt(lx,ly){
if (lx<0||ly<0||lx>=256||ly>=384) return null;
for (const r of this.regions){
if (!r.modes.includes(this.mode)) continue;
const[x,y,w,h]=r.rect;
if (lx>=x&&ly>=y&&lx<x+w&&ly<y+h) return r.id;
}
return null;
}
regionEnabled(region){
return this.regions.some((r)=>r.id===region&&r.modes.includes(this.mode));
}
bindPointer(pointerId,region){
if (this.pointerOwner.has(pointerId)) this.pointerOwner.delete(pointerId);
if (!this.regionEnabled(region)) return null;
this.pointerOwner.set(pointerId,region);
this.press(region);
return region;
}
pointerDown(pointerId,lx,ly){
const region=this.regionAt(lx,ly);
return region?this.bindPointer(pointerId,region):null;
}
controlPointerDown(pointerId,region){return this.bindPointer(pointerId,region);}
controlPointerMove(pointerId,region){
const from=this.pointerOwner.get(pointerId);
return from||region||null;
}
controlDart(pointerId,region){return this.queueDart(pointerId,region);}
pointerUp(pointerId){this.pointerOwner.delete(pointerId);this.dartedPointers.delete(pointerId);}
pointerCancel(pointerId){this.pointerOwner.delete(pointerId);this.dartedPointers.delete(pointerId);}
lostPointerCapture(pointerId){this.pointerOwner.delete(pointerId);this.dartedPointers.delete(pointerId);}
press(region){
if (region==='LEFT_WING'||region==='RIGHT_WING') this.queueWing(region);
else if (region==='BOTH_WINGS') this.queueFlap('STRAIGHT',true);
}
keyDown(code,repeat=false){
if (repeat) return;
const region=KEY_MAP[code];
if (!region) return;
if (region==='BOTH_WINGS'){
if (this.keysHeld.has('LEFT_WING')&&this.keysHeld.has('RIGHT_WING')) return;
this.keysHeld.add('LEFT_WING');this.keysHeld.add('RIGHT_WING');this.queueFlap('STRAIGHT',true);
return;
}
if (this.keysHeld.has(region)) return;
this.keysHeld.add(region);this.queueWing(region);
}
keyUp(code){
if (code==='MetaLeft'||code==='MetaRight'){this.keysHeld.clear();return;}
const region=KEY_MAP[code];
if (region==='BOTH_WINGS'){this.keysHeld.delete('LEFT_WING');this.keysHeld.delete('RIGHT_WING');}
else if (region) this.keysHeld.delete(region);
}
releaseAllPointers(){this.pointerOwner.clear();}
gamepad(snapshot){
for (const[k,region] of[['left','LEFT_WING'],['right','RIGHT_WING'],['flap','BOTH_WINGS']]){
if (!snapshot[k]){this.padHeld.delete(region);this.padBlocked.delete(region);continue;}
if (this.padHeld.has(region)||this.padBlocked.has(region)) continue;
this.padHeld.add(region);
if (region==='BOTH_WINGS') this.queueFlap('STRAIGHT',true);else this.queueWing(region);
}
}
gamepadDisconnect(){this.padHeld.clear();this.padBlocked.clear();}
cleanup(){
for (const region of this.padHeld) this.padBlocked.add(region);
this.pointerOwner.clear();this.keysHeld.clear();this.padHeld.clear();this.flapQueue.length=0;this.dartQueue.length=0;this.dartedPointers.clear();this.lastWingPress=null;this.flapWaitTicks=0;
}
held(region){
for (const r of this.pointerOwner.values()) if (r===region) return true;
return this.keysHeld.has(region)||this.padHeld.has(region);
}
frame({acceptFlap=true}={}){
const l=this.held('LEFT_WING'),r=this.held('RIGHT_WING');
const play=this.mode==='PLAY';
let flap=null;
if (acceptFlap){
flap=this.flapQueue.shift()||null;
if (flap) this.flapWaitTicks=0;
}else if (this.flapQueue.length>0){
this.flapWaitTicks+=1;
if (this.flapWaitTicks>=this.flapBufferTicks){
this.flapQueue.length=0;
this.flapWaitTicks=0;
}
}else this.flapWaitTicks=0;
const dartSide=this.dartQueue.shift()||null;
return{
left:play&&l&&!r,right:play&&r&&!l,
flapEdge:!!flap,flapKind:flap?.kind||null,chordEdge:!!flap?.chord,
flapHeld:l||r||this.held('BOTH_WINGS'),dartEdge:!!dartSide,dartSide,
};
}
}
return{InputNormalizer,KEY_MAP,GamepadReader};
})();
__modules[34]=(()=>{
function typeOf(v){
if (v===null) return 'null';
if (Array.isArray(v)) return 'array';
if (typeof v==='number') return Number.isInteger(v)&&!Object.is(v,-0)?'integer':'number';
return typeof v;
}
function typeMatches(want,v){
const t=typeOf(v);
if (want==='number') return t==='number'||t==='integer';
if (want==='integer') return t==='integer';
return want===t;
}
function resolveRef(root,ref){
if (!ref.startsWith('#/')) throw new Error(`UNSUPPORTED_REF ${ref}`);
let node=root;
for (const part of ref.slice(2).split('/')) node=node[part];
if (!node) throw new Error(`BAD_REF ${ref}`);
return node;
}
function validate(schema,value,root=schema,path='$',errors=[]){
if (schema===false){errors.push(`${path}: schema false`);return errors;}
if (schema===true) return errors;
if (schema.$ref) return validate(resolveRef(root,schema.$ref),value,root,path,errors);
if (schema.type!==undefined){
const types=Array.isArray(schema.type)?schema.type:[schema.type];
if (!types.some((t)=>typeMatches(t,value))){errors.push(`${path}: expected ${types.join('|')} got ${typeOf(value)}`);return errors;}
}
if (schema.const!==undefined&&value!==schema.const) errors.push(`${path}: const ${JSON.stringify(schema.const)}`);
if (schema.enum!==undefined&&!schema.enum.some((e)=>e===value)) errors.push(`${path}: not in enum`);
if (typeof value==='number'){
if (schema.minimum!==undefined&&value<schema.minimum) errors.push(`${path}: < minimum ${schema.minimum}`);
if (schema.maximum!==undefined&&value>schema.maximum) errors.push(`${path}: > maximum ${schema.maximum}`);
}
if (typeof value==='string'&&schema.pattern!==undefined){
if (!new RegExp(schema.pattern).test(value)) errors.push(`${path}: pattern ${schema.pattern}`);
}
if (Array.isArray(value)){
if (schema.maxItems!==undefined&&value.length>schema.maxItems) errors.push(`${path}: > maxItems`);
if (schema.minItems!==undefined&&value.length<schema.minItems) errors.push(`${path}: < minItems`);
if (schema.uniqueItems){
const seen=new Set();
for (const item of value){const k=JSON.stringify(item);if (seen.has(k)){errors.push(`${path}: duplicate item`);break;}seen.add(k);}
}
const prefix=schema.prefixItems||[];
value.forEach((item,i)=>{
if (i<prefix.length) validate(prefix[i],item,root,`${path}[${i}]`,errors);
else if (schema.items!==undefined) validate(schema.items,item,root,`${path}[${i}]`,errors);
});
}
if (value!==null&&typeof value==='object'&&!Array.isArray(value)){
const props=schema.properties||{};
for (const r of schema.required||[]) if (!(r in value)) errors.push(`${path}: missing ${r}`);
for (const[k,v] of Object.entries(value)){
if (k in props) validate(props[k],v,root,`${path}.${k}`,errors);
else if (schema.additionalProperties===false) errors.push(`${path}: unknown property ${k}`);
else if (schema.additionalProperties&&typeof schema.additionalProperties==='object') validate(schema.additionalProperties,v,root,`${path}.${k}`,errors);
}
}
return errors;
}
return{validate};
})();
__modules[35]=(()=>{
const{validate}=__modules[34];
const{checkpointChecksum}=__modules[1];
const{getIdentity}=__modules[2];
const KEYS=new Proxy({},{get(_target,key){
const suffix={A:'checkpoint.A',B:'checkpoint.B',ACTIVE:'checkpoint.active',WARNING:'warning'}[key];
return suffix?`${getIdentity().saveNamespace}.${suffix}`:undefined;
}});
function keysFor(mode='CAMPAIGN'){
const ns=getIdentity().saveNamespace,p=mode==='ARCADE'?'arcade.':'';
return{A:`${ns}.${p}checkpoint.A`,B:`${ns}.${p}checkpoint.B`,ACTIVE:`${ns}.${p}checkpoint.active`};
}
function buildRecord(payload){
const identity=getIdentity();
const record={schema:2,buildId:identity.buildId,episodeId:identity.episodeId,payload:structuredClone(payload),checksum:'0'.repeat(64)};
record.checksum=checkpointChecksum(record);
return record;
}
function validateRecordText(schema,text){
if (text===null||text===undefined) return{ok:false,reason:'ABSENT'};
let record;
try{record=JSON.parse(text);}catch{return{ok:false,reason:'PARSE'};}
if (!record||typeof record!=='object') return{ok:false,reason:'PARSE'};
const identity=getIdentity();
if (record.schema!==2) return{ok:false,reason:'UNKNOWN_SCHEMA'};
if (record.buildId!==identity.buildId||record.episodeId!==identity.episodeId) return{ok:false,reason:'UNKNOWN_CARTRIDGE'};
const errors=validate(schema,record);
if (errors.length) return{ok:false,reason:'SCHEMA',errors};
let sum;
try{sum=checkpointChecksum(record);}catch{return{ok:false,reason:'CHECKSUM'};}
if (sum!==record.checksum) return{ok:false,reason:'CHECKSUM'};
return{ok:true,record};
}
const SIBLING_CARTRIDGE_KEY=/^struthio1982\.(?:ep\d+\.)?clean\.v\d+\./;
const CONSOLE_PREF_KEY=/^struthio\.console\.presentation\./;
function foreignNamespaces(storage){
const namespace=getIdentity().saveNamespace;
return storage.keys().filter((k)=>/struthio/i.test(k)&&!k.startsWith(namespace+'.')&&!SIBLING_CARTRIDGE_KEY.test(k)&&!CONSOLE_PREF_KEY.test(k));
}
function writeCheckpoint(storage,schema,payload,opts={}){
const{hidden=false,budgetMs=120,now=()=>Date.now()}=opts;
const t0=now();
const K=keysFor(payload?.sim?.mode);
const active=storage.getItem(K.ACTIVE);
const slot=active==='A'?'B':'A';
const record=buildRecord(payload);
const text=JSON.stringify(record);
storage.setItem(K[slot],text);
const reread=storage.getItem(K[slot]);
const v=validateRecordText(schema,reread);
if (!v.ok||v.record.checksum!==record.checksum) return{committed:false,slot,reason:v.reason||'REREAD_MISMATCH'};
if (hidden&&now()-t0>budgetMs){
storage.setItem(KEYS.WARNING,'SAVE NOT UPDATED');
return{committed:false,slot,reason:'HIDDEN_BUDGET'};
}
storage.setItem(K.ACTIVE,slot);
return{committed:true,slot,checksum:record.checksum,event:'CHECKPOINT_COMMIT'};
}
function restoreCheckpoint(storage,schema,mode='CAMPAIGN'){
const foreign=foreignNamespaces(storage);
const K=keysFor(mode);
const ofMode=(v)=>(v.ok&&v.record.payload.sim.mode!==mode?{ok:false,reason:'ABSENT'}:v);
const a=ofMode(validateRecordText(schema,storage.getItem(K.A)));
const b=ofMode(validateRecordText(schema,storage.getItem(K.B)));
const pointer=storage.getItem(K.ACTIVE);
const pointed=pointer==='A'?a:pointer==='B'?b:null;
if (pointed&&pointed.ok) return{status:'RESTORE',record:pointed.record,slot:pointer,foreign};
if (a.ok&&b.ok){
const slot=a.record.payload.sim.tick>=b.record.payload.sim.tick?'A':'B';
return{status:'RESTORE',record:slot==='A'?a.record:b.record,slot,repairPointer:slot,foreign};
}
if (a.ok) return{status:'RESTORE',record:a.record,slot:'A',repairPointer:pointer==='A'?undefined:'A',foreign};
if (b.ok) return{status:'RESTORE',record:b.record,slot:'B',repairPointer:pointer==='B'?undefined:'B',foreign};
const present=[a.reason,b.reason].filter((r)=>r!=='ABSENT');
if (present.length===0&&foreign.length===0) return{status:'NONE',foreign};
return{status:'REJECTED',reasons:{A:a.reason,B:b.reason},foreign};
}
function resetData(storage){
const namespace=getIdentity().saveNamespace;
for (const k of storage.keys()) if (k.startsWith(namespace+'.')) storage.removeItem(k);
}
function memoryStorage(init={}){
const m=new Map(Object.entries(init));
return{getItem:(k)=>(m.has(k)?m.get(k):null),setItem:(k,v)=>{m.set(k,String(v));},removeItem:(k)=>{m.delete(k);},keys:()=>[...m.keys()]};
}
return{writeCheckpoint,restoreCheckpoint,resetData,KEYS,keysFor,memoryStorage};
})();
__modules[36]=(()=>{
const PROTECTED=new Set(['joust-win','player-death','boss-clear','circuit-sync']);
const EVENT_TO_SFX={FLAP:'flap',RING:'ring',CIRCUIT_SYNC:'circuit-sync',JOUST_CLASH:'joust-clash',JOUST_WIN:'joust-win',BOSS_HIT:'joust-win',PLAYER_DEATH:'player-death',EGG:'egg',HATCH:'hatch',BOSS_CLEAR:'boss-clear',LAVA_WARNING:'lava-warning'};
const SFX_MIDI={flap:68,ring:76,'circuit-sync':80,'joust-clash':40,'joust-win':83,'player-death':36,egg:64,hatch:59,'boss-clear':88,'lava-warning':37};
const SFX_LEN={flap:0.06,ring:0.18,'circuit-sync':0.5,'joust-clash':0.08,'joust-win':0.35,'player-death':0.4,egg:0.12,hatch:0.3,'boss-clear':0.9,'lava-warning':0.6};
const CONSOLE_VOICES=Object.freeze([
{id:'C_FLAP',wave:'XORSHIFT_NOISE',filter:'LP1',coefQ15:5200,attack:72,decay:1300,sustainQ15:0,release:900,gainQ15:10400,glide:-7},
{id:'C_RING',wave:'SINE',filter:'LP1',coefQ15:30000,attack:60,decay:5200,sustainQ15:6000,release:5600,gainQ15:8600,glide:5},
{id:'C_CLASH',wave:'XORSHIFT_NOISE',filter:'LP1',coefQ15:2600,attack:24,decay:2200,sustainQ15:0,release:700,gainQ15:9800,glide:-12},
{id:'C_WIN',wave:'TRIANGLE',filter:'LP1',coefQ15:20000,attack:60,decay:5400,sustainQ15:7000,release:6000,gainQ15:9000,glide:7},
{id:'C_DEATH',wave:'TRIANGLE',filter:'LP1',coefQ15:9000,attack:120,decay:9000,sustainQ15:4000,release:7200,gainQ15:9800,glide:-19},
{id:'C_PLINK',wave:'SINE',filter:'LP1',coefQ15:30000,attack:48,decay:2600,sustainQ15:0,release:1800,gainQ15:6200,glide:3},
{id:'C_STING',wave:'PULSE_25',filter:'LP1',coefQ15:7000,attack:240,decay:7200,sustainQ15:9000,release:9600,gainQ15:6200,glide:0},
{id:'C_WARN',wave:'TRIANGLE',filter:'LP1',coefQ15:5000,attack:1200,decay:6000,sustainQ15:14000,release:6000,gainQ15:7800,glide:-2},
].map(Object.freeze));
const CONSOLE_SFX=Object.freeze({
flap:{voice:'C_FLAP',midi:84,len:0.05,jitter:2,minGap:0.085},
ring:{voice:'C_RING',midi:81,len:0.16,jitter:0},
'joust-clash':{voice:'C_CLASH',midi:52,len:0.07,jitter:1},
'joust-win':{voice:'C_WIN',midi:76,len:0.22,jitter:0},
'player-death':{voice:'C_DEATH',midi:60,len:0.42,jitter:0},
egg:{voice:'C_PLINK',midi:79,len:0.08,jitter:1},
hatch:{voice:'C_PLINK',midi:72,len:0.14,jitter:1},
'circuit-sync':{voice:'C_STING',midi:76,len:0.45,jitter:0},
'boss-clear':{voice:'C_STING',midi:84,len:0.8,jitter:0},
'lava-warning':{voice:'C_WARN',midi:43,len:0.55,jitter:0},
});
function consoleAudio(audio){
return{...audio,voices:[...audio.voices,...CONSOLE_VOICES],buses:{...audio.buses,sfxGainQ15:Math.round(audio.buses.sfxGainQ15*0.71)}};
}
class Conductor{
constructor(audioAuthority,{context,send}){
this.A=audioAuthority;this.ctx=context;this.send=send;this.now=()=>context.currentTime;
const bpm=audioAuthority.transportBpmQ16/65536;
this.eighth=60/bpm/2;this.beat=this.eighth*2;
this.origin=this.now();
this.late=0;this.scheduled=0;this.dropped=0;this.lastAt={};
}
schedule(note){
const t=this.now();
if (note.atSeconds<t){
const lateMs=(t-note.atSeconds)*1000;this.late+=1;
if (lateMs<50) note.atSeconds=t;else if (note.priority<7){this.dropped+=1;return;}else note.atSeconds=t;
}
this.scheduled+=1;
this.send({type:'note',...note});
}
quantized(q){
const t=this.now();const rel=t-this.origin;
if (q==='NEXT_EIGHTH') return this.origin+Math.ceil(rel/this.eighth)*this.eighth;
if (q==='NEXT_BEAT') return this.origin+Math.ceil(rel/this.beat)*this.beat;
return t;
}
onEvents(events){
for (const ev of events){
const key=EVENT_TO_SFX[ev.type];if (!key) continue;
const map=this.A.eventMap[key];if (!map) continue;
const at=this.quantized(map.quantize);
const c=CONSOLE_SFX[key];
if (c){
if (c.minGap){const last=this.lastAt[key]||-1;if (at-last<c.minGap) continue;this.lastAt[key]=at;}
const midi=c.midi+(c.jitter?Math.round((Math.random()*2-1)*c.jitter):0);
this.schedule({voiceId:c.voice,midi,len:Math.round(c.len*this.ctx.sampleRate),atSeconds:at,priority:map.priority,bus:'sfx',protectedNote:PROTECTED.has(key)});
continue;
}
this.schedule({voiceId:map.patch,midi:SFX_MIDI[key],len:Math.round(SFX_LEN[key]*this.ctx.sampleRate),atSeconds:at,priority:map.priority,bus:'sfx',protectedNote:PROTECTED.has(key)});
}
}
stats(){return{scheduled:this.scheduled,late:this.late,dropped:this.dropped,latePercent:this.scheduled?(100*this.late)/this.scheduled:0};}
}
return{Conductor,consoleAudio,CONSOLE_SFX,CONSOLE_VOICES};
})();
__modules[37]=(()=>{
const clamp=(value,lo,hi)=>Math.max(lo,Math.min(hi,value));
class MediaLoopTrack{
constructor(element,{gain=0.56,bpm=95.703,beatsPerBar=4}={}){
if (!element||typeof element.play!=='function') throw new Error('MUSIC_ELEMENT_UNAVAILABLE');
this.element=element;
this.baseGain=clamp(gain,0,1);
this.bpm=Math.max(1,bpm);
this.beatsPerBar=Math.max(1,beatsPerBar|0);
this.playing=false;
this.lastError=null;
this.restoreTimer=null;
element.loop=true;
element.preload='auto';
element.volume=this.baseGain;
}
start(){
this.playing=true;
this.element.loop=true;
if (!this.element.paused&&!this.element.ended) return Promise.resolve(this);
this.element.volume=this.baseGain;
let attempt;
try{attempt=this.element.play();}
catch (error){this.lastError=String(error);return Promise.reject(error);}
return Promise.resolve(attempt).then(()=>{this.lastError=null;return this;},(error)=>{
this.lastError=String(error);
throw error;
});
}
visualState(){
if (!this.playing||this.element.paused||this.element.ended) return{active:false,low:0,high:0,beat:0,downbeat:0};
const beatSeconds=60/this.bpm;
const time=Math.max(0,Number(this.element.currentTime)||0);
const beatIndex=Math.floor(time/beatSeconds);
const beatPhase=(time%beatSeconds)/beatSeconds;
const eighthPhase=(time%(beatSeconds*0.5))/(beatSeconds*0.5);
const beat=Math.exp(-beatPhase*9.2);
const high=clamp(0.14+Math.exp(-eighthPhase*12)*0.48+beat*0.16,0,1);
const low=clamp(0.12+beat*0.68,0,1);
return{active:true,low,high,beat,downbeat:beatIndex%this.beatsPerBar===0?beat:0};
}
duck({depth=0.55,attack=0.012,hold=0.025,release=0.2}={}){
if (!this.playing) return;
clearTimeout(this.restoreTimer);
this.element.volume=this.baseGain*(1-(1-clamp(depth,0.1,1))*0.5);
this.restoreTimer=setTimeout(()=>{this.element.volume=this.baseGain;},Math.max(0,(attack+hold+release)*1000));
}
stop(){
this.playing=false;
clearTimeout(this.restoreTimer);
this.restoreTimer=null;
this.element.volume=this.baseGain;
this.element.pause();
}
}
function createMediaLoopTrack(element,options){return new MediaLoopTrack(element,options);}
return{createMediaLoopTrack};
})();
__modules[38]=(()=>{
function setupPwa({base='./',onUpdateReady,onOffline}){
const state={registration:null,waiting:null,offlineNote:'',reloaded:false,supported:'serviceWorker' in navigator};
if (!state.supported) return{state,acceptUpdate(){},get offlineNote(){return state.offlineNote;}};
const sw=navigator.serviceWorker;
sw.register(base+'sw.js',{scope:base}).then((reg)=>{
state.registration=reg;
const track=(w)=>{if (!w) return;w.addEventListener('statechange',()=>{if (w.state==='installed'&&sw.controller){state.waiting=reg.waiting;onUpdateReady&&onUpdateReady();}if (w.state==='redundant'&&!reg.waiting&&!reg.active) state.offlineNote='UPDATE FAILED - CURRENT VERSION KEPT';});};
if (reg.waiting&&sw.controller){state.waiting=reg.waiting;onUpdateReady&&onUpdateReady();}
track(reg.installing);
reg.addEventListener('updatefound',()=>track(reg.installing));
let lastCheck=Date.now();
document.addEventListener('visibilitychange',()=>{
if (document.visibilityState!=='visible'||!navigator.onLine||Date.now()-lastCheck<600000) return;
lastCheck=Date.now();
reg.update().catch(()=>{});
});
}).catch((e)=>{state.offlineNote='SERVICE WORKER UNAVAILABLE';state.error=String(e);});
sw.addEventListener('controllerchange',()=>{if (state.accepting&&!state.reloaded){state.reloaded=true;location.reload();}});
if (!navigator.onLine&&!sw.controller){state.offlineNote='OFFLINE INSTALL REQUIRED';onOffline&&onOffline(state.offlineNote);}
return{
state,
get offlineNote(){return state.offlineNote;},
acceptUpdate(){const w=state.waiting||(state.registration&&state.registration.waiting);if (!w) return false;state.accepting=true;w.postMessage({type:'SKIP_WAITING'});return true;},
};
}
return{setupPwa};
})();
__modules[39]=(()=>{
const DIRECTIONS=new Set(['LEFT_WING','RIGHT_WING']);
function setAttr(el,name,value){if (el.getAttribute(name)!==value) el.setAttribute(name,value);}
function directionForX(clientX,leftRect,rightRect,current=null,hysteresis=8){
const split=(leftRect.right+rightRect.left)/2;
if (clientX<split-hysteresis) return 'LEFT_WING';
if (clientX>split+hysteresis) return 'RIGHT_WING';
return DIRECTIONS.has(current)?current:(clientX<split?'LEFT_WING':'RIGHT_WING');
}
function distanceToRect(x,y,r){
const dx=Math.max(r.left-x,0,x-r.right);
const dy=Math.max(r.top-y,0,y-r.bottom);
return Math.hypot(dx,dy);
}
function nearestControl(clientX,clientY,entries,slop=16){
let best=null;
for (const entry of entries){
const distance=distanceToRect(clientX,clientY,entry.rect);
if (distance<=slop&&(!best||distance<best.distance)) best={...entry,distance};
}
return best&&best.region;
}
function installSmartControls({root,input,ensureAudio=()=>{},controlEnabled=null,onPresentationPress=null,labelFor=null,shellActive=null,onShellAction=null}){
const buttons=new Map([...root.querySelectorAll('button[data-control]')]
.map((button)=>[button.dataset.control,button]));
const active=new Map();
const gesture=new Map();
const presentationOwned=new Set();
const pointerKey=(id)=>`deck:${id}`;
const shell={pointers:new Map(),latched:false};
const shellOn=()=>!!(shellActive&&onShellAction&&shellActive());
function shellReset(){shell.pointers.clear();shell.latched=false;}
function entries(){
return[...buttons].map(([region,button])=>({region,button,rect:button.getBoundingClientRect()}));
}
function zoneControl(clientX,clientY){
const left=buttons.get('LEFT_WING'),right=buttons.get('RIGHT_WING');
const deck=root.getBoundingClientRect();
const inDeck=clientX>=deck.left&&clientX<=deck.right&&clientY>=deck.top&&clientY<=deck.bottom;
if (!left||!right||!inDeck) return nearestControl(clientX,clientY,entries(),18);
return directionForX(clientX,left.getBoundingClientRect(),right.getBoundingClientRect());
}
function controlAt(e){
const direct=e.target.closest&&e.target.closest('button[data-control]');
if (direct&&buttons.get(direct.dataset.control)===direct) return direct.dataset.control;
return zoneControl(e.clientX,e.clientY);
}
function paintContact(button,e){
const r=button.getBoundingClientRect();
button.style.setProperty('--touch-x',`${Math.max(0,Math.min(r.width,e.clientX-r.left))}px`);
button.style.setProperty('--touch-y',`${Math.max(0,Math.min(r.height,e.clientY-r.top))}px`);
}
function sync(){
const presentationHeld=new Set([...presentationOwned].map((id)=>active.get(id)));
for (const[region,button] of buttons){
const held=input.held(region)||presentationHeld.has(region);
const enabled=controlEnabled?!!controlEnabled(region):input.regionEnabled(region);
button.classList.toggle('is-held',held);
if (button.hasAttribute('aria-pressed')) button.removeAttribute('aria-pressed');
if (button.dataset.held!==String(held)) button.dataset.held=String(held);
button.classList.toggle('is-unavailable',!enabled);
button.disabled=false;
setAttr(button,'aria-disabled',enabled?'false':'true');
if (labelFor) setAttr(button,'aria-label',labelFor(region));
}
}
function forget(pointerId,cancelled=true){
if (!active.has(pointerId)) return false;
const key=pointerKey(pointerId);
if (presentationOwned.has(pointerId)) presentationOwned.delete(pointerId);
else if (cancelled) input.pointerCancel(key);
else input.pointerUp(key);
active.delete(pointerId);
gesture.delete(pointerId);
return true;
}
function forgetAll(){
shellReset();
let any=false;
for (const id of[...active.keys()]) any=forget(id)||any;
root.classList.remove('is-darting');
if (any) sync();
}
function down(e){
if (e.pointerType==='mouse'&&e.button!==0) return;
if (active.has(e.pointerId)){forget(e.pointerId);sync();}
const region=controlAt(e);
if (!region) return;
e.preventDefault();
ensureAudio();
const key=pointerKey(e.pointerId);
if (DIRECTIONS.has(region)&&shellOn()){
active.set(e.pointerId,region);
presentationOwned.add(e.pointerId);
shell.pointers.set(e.pointerId,region);
const button=buttons.get(region);
if (button) paintContact(button,e);
try{root.setPointerCapture(e.pointerId);}catch{}
if (!shell.latched&&new Set(shell.pointers.values()).size===2){
shell.latched=true;
onShellAction('BOTH');
}
sync();
return;
}
if (onPresentationPress&&onPresentationPress(region)){
active.set(e.pointerId,region);
presentationOwned.add(e.pointerId);
const button=buttons.get(region);
if (button) paintContact(button,e);
try{root.setPointerCapture(e.pointerId);}catch{}
sync();
return;
}
if (!input.controlPointerDown(key,region)){sync();return;}
active.set(e.pointerId,region);
const rect=buttons.get(region)?.getBoundingClientRect();
gesture.set(e.pointerId,{x:e.clientX,y:e.clientY,diameter:Math.max(1,Math.min(rect?.width||80,rect?.height||80)),darted:false});
const button=buttons.get(region);
if (button) paintContact(button,e);
try{root.setPointerCapture(e.pointerId);}catch{}
sync();
}
function move(e){
const current=active.get(e.pointerId);
if (!current) return;
if (e.pointerType==='mouse'&&e.buttons===0){forget(e.pointerId,false);sync();return;}
e.preventDefault();
if (presentationOwned.has(e.pointerId)){
const button=buttons.get(current);
if (button) paintContact(button,e);
return;
}
let next=current;
if (DIRECTIONS.has(current)){
const g=gesture.get(e.pointerId);
if (g&&!g.darted){
const dx=e.clientX-g.x,dy=e.clientY-g.y;
const threshold=g.diameter*.12;
if (dy>=threshold&&Math.abs(dx)<=dy*Math.tan(35*Math.PI/180)){
g.darted=input.controlDart(pointerKey(e.pointerId),current);
if (g.darted) root.classList.add('is-darting');
}
}
next=input.controlPointerMove(pointerKey(e.pointerId),current)||current;
}
const button=buttons.get(next);
if (button) paintContact(button,e);
sync();
}
function release(e,cancelled=false){
if (!active.has(e.pointerId)) return;
if (e.cancelable) e.preventDefault();
if (!cancelled) ensureAudio();
if (shell.pointers.has(e.pointerId)){
const region=shell.pointers.get(e.pointerId);
shell.pointers.delete(e.pointerId);
if (cancelled) shell.latched=true;
else if (!shell.latched&&shellOn()) onShellAction(region==='LEFT_WING'?'PREV':'NEXT');
if (shell.pointers.size===0) shell.latched=false;
}
forget(e.pointerId,cancelled);
if (![...gesture.values()].some((g)=>g.darted)) root.classList.remove('is-darting');
sync();
}
root.addEventListener('pointerdown',down);
root.addEventListener('pointermove',move);
root.addEventListener('pointerup',(e)=>release(e));
root.addEventListener('pointercancel',(e)=>release(e,true));
root.addEventListener('lostpointercapture',(e)=>release(e,true));
root.addEventListener('contextmenu',(e)=>e.preventDefault());
const noLoupe=(e)=>{if (e.cancelable) e.preventDefault();};
root.addEventListener('touchstart',noLoupe,{passive:false});
root.addEventListener('touchmove',noLoupe,{passive:false});
const view=root.ownerDocument?.defaultView||(typeof window!=='undefined'?window:null);
if (view){
view.addEventListener('pointerup',(e)=>release(e),true);
view.addEventListener('pointercancel',(e)=>release(e,true),true);
const allLifted=(e)=>{if (!e.touches||e.touches.length===0) forgetAll();};
view.addEventListener('touchend',allLifted,{capture:true,passive:true});
view.addEventListener('touchcancel',allLifted,{capture:true,passive:true});
}
return{
sync,
releaseAll:forgetAll,
cleanup(){
for (const id of active.keys()) if (!presentationOwned.has(id)) input.pointerCancel(pointerKey(id));
active.clear();
presentationOwned.clear();
gesture.clear();
shellReset();
root.classList.remove('is-darting');
sync();
},
};
}
return{installSmartControls};
})();
__modules[40]=(()=>{
const{loadAuthority,configureCartridge,getIdentity,BUILD_ID}=__modules[2];
const{Game}=__modules[13];
const{newState}=__modules[5];
const{payloadOf,EMPTY_INPUT,applyUnlimitedContinue}=__modules[12];
const{arenaContent,lavaWarningNow,parseArcade}=__modules[7];
const{createRenderer,FatalError,WORLD_PLATE_W,WORLD_PLATE_H,MATERIAL_WORLD,MATERIAL_ARCADE_PLAYER,GLOBE_MAP_W,GLOBE_MAP_H}=__modules[16];
const{buildAtlas,paintWorld,atlasDigest}=__modules[24];
const{RIDER_ATLAS_W,RIDER_ATLAS_H,validateRiderAttachments}=__modules[22];
const{ISLAND_SHEET}=__modules[18];
const{CINEMA_PANELS_PATH,PANEL_SHEET_W,PANEL_SHEET_H,PANEL_LAYOUT,panelsPresent}=__modules[14];
const{theaterSequence,THEATER_BOSS_FREEZE}=__modules[26];
const{REEL_PATH,validReel,createClipRunner}=__modules[28];
const{Scene,buildScene}=__modules[32];
const{AscentCamera}=__modules[30];
const{InputNormalizer,KEY_MAP,GamepadReader}=__modules[33];
const{writeCheckpoint,restoreCheckpoint,resetData,KEYS,keysFor,memoryStorage}=__modules[35];
const{Conductor,consoleAudio}=__modules[36];
const{createMediaLoopTrack}=__modules[37];
const{setupPwa}=__modules[38];
const{installSmartControls}=__modules[39];
const{createExternalHud,hudModel}=__modules[31];
const VS_SIM=__modules[41];
const{SHIMMER_TICKS:VS_SHIMMER}=__modules[5];
async function decodeArtwork(buf){
const blob=new Blob([buf],{type:'image/webp'});
let bitmap;
try{bitmap=await createImageBitmap(blob,{colorSpaceConversion:'none',premultiplyAlpha:'none'});}
catch{bitmap=await createImageBitmap(blob);}
try{
const canvas=document.createElement('canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;
const ctx=canvas.getContext('2d',{willReadFrequently:true});
if (!ctx) throw new Error('ART_DECODER_UNAVAILABLE');
ctx.drawImage(bitmap,0,0);
return{w:canvas.width,h:canvas.height,p:new Uint8Array(ctx.getImageData(0,0,canvas.width,canvas.height).data)};
}finally{bitmap.close();}
}
const MUSIC_PRESENTATION_BPM=110;
const CONSOLE_AUTHORITY_PATH='episodes/dev-00/authority.json';
const TICK_MS=1000/60;
const BOSS_BACKGROUND_MILESTONES=Object.freeze([5,11,17,23,29]);
const HOME_ITEMS=Object.freeze(['CARTRIDGE','ARCADE SCORE ATTACK','VS','QUICK REFERENCE','DEVELOPMENT']);
const VS_ITEMS=Object.freeze(['CREATE MATCH','JOIN MATCH','BACK']);
function arcadeItems(active){return active?['RESUME RUN','NEW RUN','BACK']:['NEW RUN','BACK'];}
const SCORE_POPUP=Object.freeze({EGG:'GOLD',JOUST:'WHITE',RING:'CYAN',BOSS_RING:'CYAN',BOSS_HIT:'LAVA'});
const RECORDS_KEY='struthio.console.presentation.records.v1';
const fmtScore=(n)=>Math.max(0,Math.trunc(n||0)).toLocaleString('en-US');
function retireBannerText(e,mode){
const parts=[mode==='ARCADE'?'STAGE CLEAR':'SECTOR CLEAR'];
if (e.clean) parts.push('SURVIVAL +3000');
if (e.sweep) parts.push('SWEEP +1000');
if (e.carried) parts.push(`${e.carried} RIVAL${e.carried>1?'S':''} CARRY OVER`);
else if (e.dropped&&e.intoBoss) parts.push('STRAYS LEFT BEHIND');
return parts.join(' · ');
}
const DEV_ITEMS=Object.freeze(['DEV-00','NETWORK','CARTRIDGE WORKSHOP','QR LOADER','TCS CAD FILES','TCS CALIBRATION','GAME SOURCE','BACK']);
const LOCK_ITEMS=Object.freeze(['UNLOCK','BACK']);
const FRESH_TITLE_ITEMS=Object.freeze(['NEW CAMPAIGN','CINEMA','EJECT']);
const SAVED_TITLE_ITEMS=Object.freeze(['NEW CAMPAIGN','CONTINUE','CINEMA','EJECT']);
const REJECTED_TITLE_ITEMS=Object.freeze(['NEW CAMPAIGN','CINEMA','EJECT']);
const DEV_CODE_SHA256='d1cadfb3734a15e4bf9d7d337f94e60b2f39c40fcf0c99c71ad0229009ef7fc4';
const DEV_UNLOCK_KEY='struthio.console.presentation.dev-unlocked.v1';
function titleItemsForRestore(status){
return status==='RESTORE'?[...SAVED_TITLE_ITEMS]:status==='REJECTED'?[...REJECTED_TITLE_ITEMS]:[...FRESH_TITLE_ITEMS];
}
function itemsForLevel(level,status){
if (level==='HOME') return[...HOME_ITEMS];
if (level==='DEV') return[...DEV_ITEMS];
if (level==='LOCK') return[...LOCK_ITEMS];
if (level==='ARCADE') return arcadeItems(status==='ARCADE_ACTIVE');
if (level==='VS') return[...VS_ITEMS];
return titleItemsForRestore(status);
}
function canAcceptBufferedFlap(s,C){
if (!s||s.sim.shell!=='PLAY') return true;
return s.boss.phase!=='TRANSITION'
&&s.player.flapCooldown===0
&&s.player.wing>0
&&s.player.invulnerableTicks<=C.spawnShimmerTicks;
}
function worldArtFor(state){
return state?.sim?.mode==='ARCADE'?'ARCADE':'STORY';
}
function backgroundStageFor(state){
if (!state||state.sim?.mode!=='CAMPAIGN') return 0;
const cleared=new Set(Array.isArray(state.boss?.cleared)?state.boss.cleared:[]);
return BOSS_BACKGROUND_MILESTONES.reduce((stage,milestone)=>stage+(cleared.has(milestone)?1:0),0);
}
function primeAudioContext(context){
if (!context||context.state==='closed') return null;
if (context.state!=='running'){
try{
const source=context.createBufferSource();
source.buffer=context.createBuffer(1,1,context.sampleRate||44100);
source.connect(context.destination);
source.start(0);
}catch{}
}
try{return context.state==='running'?Promise.resolve():context.resume();}
catch (error){return Promise.reject(error);}
}
function freshFeelState(){
return{kind:'',start:-1,until:-1,shakeUntil:-1,strength:0,priority:0,x:128,y:192,space:'WORLD',contentId:''};
}
function resetFeelState(feel){Object.assign(feel,freshFeelState());}
function triggerFeel(feel,{kind,tick,duration,shake=0,strength=1,priority=1,x=128,y=192,space='WORLD',contentId=''}){
if (feel.start===tick&&feel.priority>priority) return;
Object.assign(feel,{kind,start:tick,until:tick+duration,shakeUntil:tick+shake,strength,priority,x,y,space,contentId});
}
function sampleFeelState(feel,tick){
if (!feel||tick>=feel.until) return{active:false,impact:0,joltX:0,joltY:0};
const span=Math.max(1,feel.until-feel.start);
const age=Math.max(0,tick-feel.start);
const life=Math.max(0,1-age/span);
let joltX=0,joltY=0;
if (tick<feel.shakeUntil){
const pattern=[[1,0],[-1,1],[0,-1],[1,1],[-1,0],[0,1]];
const[px,py]=pattern[age%pattern.length];
const amplitude=feel.strength>=1.2&&age<3?2:1;
joltX=px*amplitude;joltY=py*amplitude;
}
return{active:true,kind:feel.kind,age,life,impact:life*feel.strength,joltX,joltY,x:feel.x,y:feel.y,space:feel.space,contentId:feel.contentId};
}
function pulseHaptic(pattern){
try{
if (typeof navigator!=='undefined'&&typeof navigator.vibrate==='function') navigator.vibrate(pattern);
}catch{}
}
const FATAL_HINT={
FATAL_SECURE_CONTEXT:'Open the game over https or from localhost.',
FATAL_WEBGPU_UNAVAILABLE:'This browser does not support WebGPU, which the game needs. Play in a current Chrome or Edge (desktop or Android), or Safari on iPhone, iPad or Mac running version 26 or later.',
FATAL_WEBGPU_CONTEXT:'This browser does not support WebGPU, which the game needs. Play in a current Chrome or Edge (desktop or Android), or Safari on iPhone, iPad or Mac running version 26 or later.',
FATAL_ADAPTER:'WebGPU is present but no graphics adapter answered. Turn on hardware acceleration in your browser settings, update your graphics driver, then reload.',
FATAL_DEVICE:'WebGPU is present but no graphics adapter answered. Turn on hardware acceleration in your browser settings, update your graphics driver, then reload.',
FATAL_GPU_VALIDATION:'The renderer failed a WebGPU validation check. Reload to retry; your last checkpoint is safe.',
FATAL_GPU_LOST_TWICE:'The graphics device was lost twice. Reload to start a new session; your last checkpoint is safe.',
FATAL_RECOVERY:'The graphics device was lost and could not be rebuilt. Reload to start a new session.',
OFFLINE_INSTALL_REQUIRED:'This build has not been installed for offline play yet. Reconnect once to finish installing.',
};
const FATAL_HINT_DEFAULT='Reload to start a new session. Your last checkpoint is safe.';
const UNSUPPORTED=new Set(['FATAL_SECURE_CONTEXT','FATAL_WEBGPU_UNAVAILABLE','FATAL_WEBGPU_CONTEXT','FATAL_ADAPTER','FATAL_DEVICE']);
const CONSOLE_BOOT_STARTED=typeof performance!=='undefined'?performance.now():0;
const RIDER_PREF_KEY='struthio.console.presentation.hd-rider.v1';
function finishConsoleBoot(message='CONSOLE READY'){
const boot=document.getElementById('console-boot');
if (!boot||boot.hidden) return;
const status=boot.querySelector('[data-boot-status]');
if (status) status.textContent=message;
const elapsed=(typeof performance!=='undefined'?performance.now():0)-CONSOLE_BOOT_STARTED;
const delay=Math.max(0,520-elapsed);
setTimeout(()=>{
document.body.classList.remove('is-booting');
document.body.classList.add('console-ready');
setTimeout(()=>{boot.hidden=true;},560);
},delay);
}
function showFatal(code,detail){
const el=document.getElementById('fatal');
el.hidden=false;
const unsupported=UNSUPPORTED.has(code);
const h1=el.querySelector('h1');
if (h1) h1.textContent=unsupported?'THIS BROWSER CANNOT RUN STRUTHIO CONSOLE':'STRUTHIO CONSOLE CANNOT START';
el.querySelector('.code').textContent=code;
el.querySelector('.detail').textContent=unsupported?'':(detail||'');
const hint=el.querySelector('.hint');
if (hint) hint.textContent=FATAL_HINT[code]||FATAL_HINT_DEFAULT;
document.getElementById('game').setAttribute('aria-hidden','true');
window.__struthio&&(window.__struthio.fatal={code,detail});
const boot=document.getElementById('console-boot');
if (boot) boot.hidden=true;
document.body.classList.remove('is-booting');
document.body.classList.add('console-ready');
}
function localStorageAdapter(){
try{const probe='__struthio_console_probe';localStorage.setItem(probe,'1');localStorage.removeItem(probe);}catch{return null;}
const guard=(fn,fallback)=>{try{return fn();}catch{return fallback;}};
return{
getItem:(k)=>guard(()=>localStorage.getItem(k),null),
setItem:(k,v)=>guard(()=>{localStorage.setItem(k,v);},undefined),
removeItem:(k)=>guard(()=>{localStorage.removeItem(k);},undefined),
keys:()=>guard(()=>{const out=[];for (let i=0;i<localStorage.length;i++) out.push(localStorage.key(i));return out;},[]),
};
}
async function fetchBytes(base,path){
const response=await fetch(base+path,{cache:'no-cache'});
if (!response.ok) throw new Error(`FETCH ${path} ${response.status}`);
return new Uint8Array(await response.arrayBuffer());
}
async function loadArt(base,path,w,h){
const art=await decodeArtwork(await fetchBytes(base,path));
if (art.w!==w||art.h!==h) throw new Error(`ART_SIZE ${path} ${art.w}x${art.h}, expected ${w}x${h}`);
return art;
}
const ARCADE_MUSIC=Object.freeze({url:'console-assets/arcade/tarmac-at-midnight-loop.mp3',bpm:120});
const ARCADE_ART=Object.freeze({
rear:'console-assets/arcade/arcade-background-rear.webp',
near:'console-assets/arcade/arcade-middle-near.webp',
islands:'console-assets/arcade/arcade-islands-v4.webp',
metadata:'console-assets/arcade/arcade-islands.metadata.json',
bird:'console-assets/arcade/arcade-jouster-48.webp',
});
function validateArcadeArt({rear,near,islands,metadata}){
const fail=(code)=>{throw new Error('ARCADE_ART '+code);};
if (rear.w!==WORLD_PLATE_W||rear.h!==WORLD_PLATE_H||near.w!==WORLD_PLATE_W||near.h!==WORLD_PLATE_H) fail('PLATE_SIZE');
if (islands.w!==ISLAND_SHEET.w||islands.h!==ISLAND_SHEET.h) fail('ISLAND_SIZE');
for (let i=3;i<rear.p.length;i+=4*97) if (rear.p[i]!==255) fail('REAR_NOT_OPAQUE');
const colAlpha=(x0,x1)=>{let sum=0,n=0;for (let y=0;y<near.h;y+=8) for (let x=x0;x<x1;x+=4){sum+=near.p[(y*near.w+x)*4+3];n++;}return sum/n;};
const w=near.w,centre=colAlpha(Math.round(w*.375),Math.round(w*.625)),sides=(colAlpha(0,Math.round(w*.125))+colAlpha(Math.round(w*.875),w))/2;
if (!(centre<24)) fail('NEAR_CENTRE_NOT_OPEN');
if (!(sides>64)) fail('NEAR_SIDES_EMPTY');
if (!metadata||metadata.rendererExtension!=='topDecorV1'||!Array.isArray(metadata.masters)) fail('METADATA');
const count=(role)=>metadata.masters.filter((m)=>m.role===role).length;
if (count('STANDARD')!==9||count('BOSS')!==5||count('GROUND')!==1) fail('MASTER_CONTRACT');
for (const m of metadata.masters){
if (!(m.capTop>0&&m.capTop+22<m.h)) fail('CAP_TOP '+m.id);
if (m.topDecorRows!==undefined&&!(m.topDecorRows>=0&&m.topDecorRows<=m.capTop)) fail('TOP_DECOR '+m.id);
}
return{centreAlpha:+centre.toFixed(1),sideAlpha:+sides.toFixed(1),masters:metadata.masters.length};
}
function markJousterRims(sheet){
const{w,h,p}=sheet;
const a=new Uint8Array(w*h);
for (let i=0;i<w*h;i++) a[i]=p[i*4+3];
const clear=(x,y)=>x<0||y<0||x>=w||y>=h||a[y*w+x]<128;
let n=0;
for (let y=0;y<h;y++) for (let x=0;x<w;x++){
const i=y*w+x,k=i*4;
if (a[i]<128) continue;
const r=p[k],g=p[k+1],b=p[k+2],mx=Math.max(r,g,b);
if (mx<=17){
if (clear(x+2,y)||clear(x-2,y)||clear(x,y+2)||clear(x,y-2)){p[k]=0;p[k+1]=255;p[k+2]=0;n++;}
}else if (r+20<b&&g<=b*0.8&&mx>=38&&mx<=158){
const t=Math.min(1,Math.max(0,(mx/255-0.10)/0.35)),sm=t*t*(3-2*t);
p[k]=0;p[k+1]=0;p[k+2]=Math.round(40+215*sm);
}
}
sheet.rimTexels=n;
return sheet;
}
async function loadArcadeArt(base,fetchJson,consolePalette,consoleFont){
try{
const[rear,near,islands,metadata,bird]=await Promise.all([
loadArt(base,ARCADE_ART.rear,WORLD_PLATE_W,WORLD_PLATE_H),
loadArt(base,ARCADE_ART.near,WORLD_PLATE_W,WORLD_PLATE_H),
loadArt(base,ARCADE_ART.islands,ISLAND_SHEET.w,ISLAND_SHEET.h),
fetchJson(ARCADE_ART.metadata),
loadArt(base,ARCADE_ART.bird,1536,1152).then(markJousterRims).catch(()=>null),
]);
const report=validateArcadeArt({rear,near,islands,metadata});
return{art:{rear,near,islands,islandSpec:metadata,palette:consolePalette,font:consoleFont,bird},report:{status:'CONSOLE',owner:'CONSOLE_MACHINE',bird:bird?'ARCADE_JOUST_48':'PROFILE',...report}};
}catch (error){
console.warn('ARCADE_ART_REJECTED',String(error&&error.message||error));
return{art:null,report:{status:'REJECTED',owner:'CARTRIDGE_FALLBACK',reason:String(error&&error.message||error)}};
}
}
async function loadCinemaPanels(base,app,path=CINEMA_PANELS_PATH){
const plate=await loadArt(base,path,PANEL_SHEET_W,PANEL_SHEET_H);
const present=panelsPresent(plate);
const expected=Object.keys(PANEL_LAYOUT).length;
if (present.size!==expected) throw new Error(`CINEMA_PANELS_INCOMPLETE ${present.size}/${expected}`);
app.cinemaPanels={status:'READY',path,panels:present.size};
return{plate,present};
}
async function loadReel(base,app,path=REEL_PATH){
const reel=JSON.parse(new TextDecoder().decode(await fetchBytes(base,path)));
if (!validReel(reel)) throw new Error('REEL_INVALID');
app.reel={status:'READY',path,clips:reel.clips.length};
return reel;
}
function showEmptyConsole(config){
resetCartridgePalette(document.documentElement);
document.body.classList.remove('is-internal-rom');
document.body.classList.add('is-empty-console');
const panel=document.getElementById('empty-console');
if (panel){
panel.hidden=false;
const build=panel.querySelector('[data-console-build]');
if (build) build.textContent=config.consoleBuildId;
}
for (const id of['title-screen','manual-screen','fatal']){
const element=document.getElementById(id);
if (element) element.hidden=true;
}
finishConsoleBoot('SLOT A · EMPTY · DEV-00 READY');
}
function applyEpisodePresentation(episode,source='deployed'){
const asset=episode.assets,presentation=episode.presentation||{},ui=presentation.ui||{},palette=presentation.palette||{};
const setSource=(id,record)=>{const element=document.getElementById(id);if (element&&record?.url) element.src='./'+record.url;};
setSource('title-art',asset.startScreen);
{const manualImage=document.getElementById('manual-image');if (manualImage) manualImage.src='./console-assets/console-manual.webp';}
setSource('music-track',asset.audio);
const internal=source==='internal';
document.body.classList.remove('is-empty-console');
document.body.classList.toggle('is-internal-rom',internal);
const title=document.getElementById('title-screen');
if (title){title.setAttribute('aria-label',`${episode.title} start screen`);title.style.setProperty('--title-art',`url("${new URL('./'+asset.startScreen.url,document.baseURI).href}")`);}
const heading=document.querySelector('#title-menu h2');if (heading&&ui.heading) heading.textContent=ui.heading;
const note=document.getElementById('title-note');if (note&&ui.startNote) note.textContent=ui.startNote;
const credit=document.getElementById('episode-credit');if (credit&&ui.credit) credit.textContent=ui.credit;
const powerLabel=document.getElementById('title-power-label');if (powerLabel) powerLabel.textContent=internal?'SYSTEM ROM':'CARTRIDGE ON';
const cartridgeButton=document.getElementById('cartridge-open');if (cartridgeButton) cartridgeButton.textContent=internal?'OPEN CARTRIDGE SLOT':'CHANGE CARTRIDGE';
document.title=`STRUTHIO CONSOLE — ${episode.title}`;
const root=document.documentElement;
resetCartridgePalette(root);
const roles=palette.roles||[];
const vars={
'--ui-bone':palette.text||roles[0],'--ui-cyan':palette.hudAccent,'--ui-gold':palette.edge,
'--ui-gold-lit':palette.edge,'--ui-crimson':palette.alarm,'--ui-ink':palette.ink,
};
for (const[name,value] of Object.entries(vars)) if (value) root.style.setProperty(name,value);
const semantic=resolveSemanticPalette(presentation);
applySemanticPalette(root,semantic);
if (semantic.rejected.length) console.warn('PALETTE_FALLBACK',JSON.stringify(semantic.rejected));
return semantic;
}
const LAYOUT_DEBUG_KEY='struthio.console.presentation.layout-debug.v1';
async function boot({base='./',storage=localStorageAdapter(),flags={}}={}){
const storageBlocked=!storage;
if (storageBlocked) storage=memoryStorage();
const app={fatal:null,flags,buildId:BUILD_ID,releaseBuild:(document.querySelector('meta[name=build]')||{}).content||'',storageBlocked};
window.__struthio=app;
const deviceDebug=storage.getItem(LAYOUT_DEBUG_KEY)||'off';
if (deviceDebug==='on'||deviceDebug==='on-noshim') app.flags={...flags,debug:'layout',...(deviceDebug==='on-noshim'?{shim:'off'}:{})};
app.viewportShim=installViewportShim({disabled:app.flags.shim==='off'});
try{
let loaded=await loadConfiguredEpisode(base,{
forceEmpty:flags.episode==='none',
useInternalRom:flags.rom==='dev-00',
});
if (!loaded.episode&&flags.episode!=='none'&&loaded.internalAvailable){
loaded=await loadConfiguredEpisode(base,{useInternalRom:true});
app.slotEmptyFallback=true;
}
app.slot=loaded.slot?{title:loaded.slot.title,source:loaded.slot.source,id:loaded.slot.id}:null;
app.console=loaded.config;
app.cartridgeSource=loaded.source;
if (loaded.source==='installed') await ensureCartridgeRouting(base);
app.cartridgeManager=setupCartridgeManager({base,loaded,validateManifest:validateEpisodePack});
app.qrLog=[];
app.qrCart=setupQrCart({base,validateManifest:validateEpisodePack,log:(e,d)=>{app.qrLog.push([e,d]);if (app.qrLog.length>40) app.qrLog.shift();}});
if (!loaded.episode){
configureCartridge(null);
showEmptyConsole(loaded.config);
app.empty=true;
return{empty:true,game:null,stop(){}};
}
const episode=loaded.episode;
configureCartridge(episode);
app.episode={id:episode.id,title:episode.title,buildId:episode.buildId,manifestPath:loaded.manifestPath};
app.cartridgeBuildId=episode.buildId;
const spriteProfile=selectSpriteProfile({source:loaded.source,episodeId:episode.id});
app.spriteProfile={
id:spriteProfile.id,
availability:spriteProfile.availability,
birdOwner:spriteProfile.birdOwner,
riderOwner:spriteProfile.riderOwner,
verticalAscent:spriteProfile.verticalAscent,
};
app.riderEnabled=spriteProfile.id==='CONSOLE_FULL'
?storage.getItem(RIDER_PREF_KEY)==='on'
:spriteProfile.riderDefault;
app.palette=applyEpisodePresentation(episode,loaded.source);
if (!globalThis.isSecureContext) throw new FatalError('FATAL_SECURE_CONTEXT','A secure context (https or localhost) is required.');
if (!navigator.gpu) throw new FatalError('FATAL_WEBGPU_UNAVAILABLE','WebGPU is not available in this browser. There is no fallback renderer.');
const fetchJson=async (p)=>{const r=await fetch(base+p,{cache:'no-cache'});if (!r.ok) throw new Error(`FETCH ${p} ${r.status}`);return r.json();};
const consoleAuthorityData=fetchJson(CONSOLE_AUTHORITY_PATH);
const cartridgePresentationData=episode.assets.authority?.url?fetchJson(episode.assets.authority.url):Promise.resolve(null);
const A=await loadAuthority(
async (name)=>(await consoleAuthorityData)[name],
async (name)=>(await cartridgePresentationData)?.[name],
);
const canvas=document.getElementById('game');
const[backgrounds,islands,cinemaPanels,reel,heroSprites,riderSprites,riderMap,arcadeArt]=await Promise.all([
(()=>{
const shared=new Map();
return Promise.all(episode.assets.backgrounds.map((stage)=>{
const key=`${stage.rear.url}|${stage.near.url}`;
if (!shared.has(key)) shared.set(key,Promise.all([loadArt(base,stage.rear.url,WORLD_PLATE_W,WORLD_PLATE_H),loadArt(base,stage.near.url,WORLD_PLATE_W,WORLD_PLATE_H)]).then(([rear,near])=>({rear,near})));
return shared.get(key);
}));
})(),
loadArt(base,episode.assets.islands.url,ISLAND_SHEET.w,ISLAND_SHEET.h),
loadCinemaPanels(base,app,episode.assets.cinemaPanels.url),
loadReel(base,app,episode.assets.theaterReel.url),
loadArt(base,spriteProfile.birdPath,1536,1152),
loadArt(base,spriteProfile.riderPath,RIDER_ATLAS_W,RIDER_ATLAS_H),
fetchJson(spriteProfile.riderMapPath),
app.flags.arcadeArt==='cartridge'?Promise.resolve({art:null,report:{status:'DISABLED',owner:'CARTRIDGE_FALLBACK'}})
:loadArcadeArt(base,fetchJson,(await consoleAuthorityData).palette,(await consoleAuthorityData).font_5x7),
]);
app.arcadeArt=arcadeArt.report;
if (arcadeArt.art){arcadeArt.art.grade=app.flags.arcadeGrade!=='off';app.arcadeArt.depthGrade=arcadeArt.art.grade;}
validateRiderAttachments(riderSprites,riderMap,spriteProfile);
const atlas=buildAtlas(A,{backgrounds,islands,heroSprites,islandSpec:episode.assets.islands.metadata,arcade:arcadeArt.art});
atlas.riderAttachments=riderMap;
app.riderSystem={
profile:spriteProfile.id,
buildId:riderMap.buildId,
states:riderMap.states.length,
frames:riderMap.frames.length,
owner:riderMap.owner,
enabled:app.riderEnabled,
defaultEnabled:spriteProfile.riderDefault,
};
const renderer=await createRenderer(canvas,{
atlasPixels:atlas.surface,
birdPixels:heroSprites,
riderPixels:riderSprites,
onLost:(info)=>{app.lost=info;},
onRecovered:(info)=>{app.recovered=info;renderer.markAtlasDirty();renderer.markWorldDirty();},
onFatal:(e)=>{
app.fatal={code:e.code,detail:e.detail};
app.stopped=true;
if (app.session) app.session.stop();
showFatal(e.code,e.detail);
},
});
app.renderer=renderer;
if (!renderer.uploadPanels(cinemaPanels.plate,()=>loadArt(base,episode.assets.cinemaPanels.url,PANEL_SHEET_W,PANEL_SHEET_H))) throw new Error('CINEMA_PANELS_UPLOAD_REJECTED');
cinemaPanels.plate=null;
if (!renderer.uploadWorld(atlas.world,atlas.waterMask)) throw new Error('WORLD_PLATES_UPLOAD_REJECTED');
const session=createSession({A,atlas,renderer,canvas,storage,app,base,panels:cinemaPanels.present,reel,episode,heroSprites,arcadeBirdSheet:arcadeArt.art?.bird||null});
app.session=session;
await session.start();
finishConsoleBoot(`${episode.title} · ${loaded.source==='internal'?'INTERNAL ROM READY':'CARTRIDGE READY'}`);
return session;
}catch (e){
let code=e instanceof FatalError?e.code:'FATAL_BOOT';
if (!(e instanceof FatalError)&&/FETCH|Failed to fetch|NetworkError/.test(String(e.message))&&!(navigator.serviceWorker&&navigator.serviceWorker.controller)) code='OFFLINE_INSTALL_REQUIRED';
app.fatal={code,detail:e.detail||e.message};
showFatal(code,e.detail||e.message);
throw e;
}
}
const ARCADE_REAR_HORIZON=1682;
const ARCADE_GLOBE=Object.freeze({cx:608,cy:254,r:118,homeFrom:-50,homeSpan:88,periods:18,turnSeconds:120,crossfade:7,mode:'COLOUR'});
const MOON_TURN_PER_TICK=1/(ARCADE_GLOBE.turnSeconds*60),MOON_BEAT_SURGE=5;
function buildArcadeGlobe(rear){
if (!rear||rear.w!==768||rear.h!==2304) return null;
const G=ARCADE_GLOBE,W=GLOBE_MAP_W,H=GLOBE_MAP_H;
const x0=Math.max(0,Math.floor(G.cx-G.r-40)),x1=Math.min(rear.w,Math.ceil(G.cx+G.r+40));
const y0=Math.max(0,Math.floor(G.cy-G.r-40)),y1=Math.min(rear.h,Math.ceil(G.cy+G.r+40));
const bw=x1-x0,bh=y1-y0,n=bw*bh;
const col=new Float32Array(n*3),lum=new Float32Array(n),mask=new Float32Array(n);
for (let y=0;y<bh;y++) for (let x=0;x<bw;x++){
const i=y*bw+x,q=((y+y0)*rear.w+x+x0)*4;
const r=rear.p[q]/255,g=rear.p[q+1]/255,b=rear.p[q+2]/255;
const nx=(x+x0+0.5-G.cx)/G.r,ny=(y+y0+0.5-G.cy)/G.r;
const m=nx*nx+ny*ny<1?1:0;
mask[i]=m;col[i*3]=r*m;col[i*3+1]=g*m;col[i*3+2]=b*m;
lum[i]=0.2126*r+0.7152*g+0.0722*b;
}
const blur=(src,k,rad)=>{
let a=src,out=new Float32Array(a.length);
for (let pass=0;pass<2;pass++){
for (const horiz of[true,false]){
const len=horiz?bw:bh,lines=horiz?bh:bw;
for (let l=0;l<lines;l++) for (let c=0;c<k;c++){
const idx=(t)=>(horiz?l*bw+Math.min(len-1,Math.max(0,t)):Math.min(len-1,Math.max(0,t))*bw+l)*k+c;
let acc=0;
for (let t=-rad;t<=rad;t++) acc+=a[idx(t)];
for (let t=0;t<len;t++){
out[idx(t)]=acc/(2*rad+1);
acc+=a[idx(t+rad+1)]-a[idx(t-rad)];
}
}
[a,out]=[out,a===src?new Float32Array(a.length):a];
}
}
return a;
};
const num=blur(col,3,16),den=blur(mask,1,16);
const light=new Float32Array(n*3),detail=new Float32Array(n);
for (let i=0;i<n;i++){
const d=Math.max(den[i],1e-3);
light[i*3]=num[i*3]/d;light[i*3+1]=num[i*3+1]/d;light[i*3+2]=num[i*3+2]/d;
const lb=0.2126*light[i*3]+0.7152*light[i*3+1]+0.0722*light[i*3+2];
detail[i]=lum[i]/Math.max(lb,0.02);
}
const at=(arr,lon,lat,k=1,c=0)=>{
const x=Math.floor(G.cx+G.r*Math.cos(lat)*Math.sin(lon))-x0;
const y=Math.floor(G.cy+G.r*Math.sin(lat))-y0;
const i=Math.min(bh-1,Math.max(0,y))*bw+Math.min(bw-1,Math.max(0,x));
return arr[i*k+c];
};
const D2R=Math.PI/180,P=2*Math.PI/G.periods,X=G.crossfade*D2R;
const home0=G.homeFrom*D2R,home1=home0+G.homeSpan*D2R,end=home0+2*Math.PI;
const regions=[[home0,home1,0]];
for (let d=home1,k=3;d<end-1e-6;d+=2*P,k+=2) regions.push([d,Math.min(d+2*P,end),k*P]);
const out={w:W,h:H,p:new Uint8Array(W*H*4)};
for (let v=0;v<H;v++){
const lat=((v+0.5)/H-0.5)*Math.PI;
for (let u=0;u<W;u++){
const lon0=((u+0.5)/W)*2*Math.PI-Math.PI;
const lon=((lon0-home0)%(2*Math.PI)+2*Math.PI)%(2*Math.PI)+home0;
let ri=0;
while (ri<regions.length-1&&lon>=regions[ri][1]) ri++;
const[,b,off]=regions[ri];
const nextOff=ri+1<regions.length?regions[ri+1][2]:2*Math.PI;
const w=Math.min(1,Math.max(0,(lon-(b-X))/X));
const dv=at(detail,lon-off,lat)*(1-w)+at(detail,lon-nextOff,lat)*w;
const o=(v*W+u)*4;
if (G.mode==='COLOUR'){
out.p[o]=255;
for (let c=0;c<3;c++) out.p[o+1+c]=Math.round(Math.min(1,at(col,lon-off,lat,3,c)*(1-w)+at(col,lon-nextOff,lat,3,c)*w)*255);
continue;
}
out.p[o]=Math.round(Math.min(1,dv/4)*255);
if (Math.abs(lon0)<=Math.PI/2){
out.p[o+1]=Math.round(Math.min(1,at(light,lon0,lat,3,0))*255);
out.p[o+2]=Math.round(Math.min(1,at(light,lon0,lat,3,1))*255);
out.p[o+3]=Math.round(Math.min(1,at(light,lon0,lat,3,2))*255);
}
}
}
out.params=[G.cx,G.cy,G.mode==='COLOUR'?-G.r:G.r,2*Math.PI/(G.turnSeconds*60)];
return out;
}
function createSession({A,atlas,renderer,canvas,storage,app,base,panels,reel,episode,heroSprites=null,arcadeBirdSheet=null}){
const C=A.sim_constants;
let currentBird=heroSprites;
const schema=A['state.schema'];
const scene=new Scene(A,atlas);
scene.panels=panels;
scene.riderEnabled=app.riderEnabled;
scene.verticalAscent=app.spriteProfile.verticalAscent===true;
const ascentCamera=new AscentCamera(A);
const input=new InputNormalizer(A.input);
let game=null;
let screen='ATTRACT';
let theater=null;
let menu={items:[...FRESH_TITLE_ITEMS],index:0,note:''};
let renderTick=0,crawlTicks=0,crawlHold=0,acc=0,last=performance.now();
let prev=new Map(),prevPlayer=null;
let banner=null,saveWarning=!!storage.getItem(KEYS.WARNING);
const popups=[];
let gameOverInfo=null,winnerInfo=null;
function readRecords(){try{const r=JSON.parse(storage.getItem(RECORDS_KEY)||'{}');return r&&typeof r==='object'?r:{};}catch{return{};}}
function writeRecords(r){try{storage.setItem(RECORDS_KEY,JSON.stringify(r));}catch{}}
function recordArcadeRun(s){
const recs=readRecords(),prevBest=recs.arcade||null,legacy=!!s.score?.legacy;
const stage=parseArcadeStage(s);
const run={score:s.sim.score,stage,deaths:s.score?.deaths||0,build:BUILD_ID,scoreVersion:2,date:new Date().toISOString().slice(0,10)};
const isNew=!legacy&&(!prevBest||run.score>prevBest.score);
if (isNew){recs.arcade=run;writeRecords(recs);}
app.arcadeRecord=recs.arcade||null;
return{final:run.score,stage,best:(isNew?run:prevBest),isNew,legacy};
}
function recordCampaignRun(s){
const recs=readRecords();recs.campaign=recs.campaign||{};
const id=app.episode?.id||'unknown',prevBest=recs.campaign[id]||null,legacy=!!s.score?.legacy;
const run={score:s.sim.score,deaths:s.score?.deaths||0,continuesUsed:s.score?.continuesUsed||0,build:BUILD_ID,scoreVersion:2,date:new Date().toISOString().slice(0,10)};
const isNew=!legacy&&(!prevBest||run.score>prevBest.score);
if (isNew){recs.campaign[id]=run;writeRecords(recs);}
return{final:run.score,best:isNew?run:prevBest,isNew,legacy,continuesUsed:run.continuesUsed};
}
function parseArcadeStage(s){const m=/^ARC_C(\d+)_/.exec(s.objectives.routeId);return m?Number(m[1]):1;}
function arcadeRestore(){
const r=restoreCheckpoint(storage,schema,'ARCADE');
const p=r.status==='RESTORE'?r.record.payload:null;
const active=!!p&&p.sim.shell!=='GAMEOVER'&&!!p.score&&!p.score.legacy;
return{...r,active};
}
function arcadeNote(){
const best=readRecords().arcade;
return best?`HI ${fmtScore(best.score)} · STAGE ${best.stage}`:'NO RECORD YET';
}
const feel=freshFeelState();
const musicElement=document.getElementById('music-track');
let music=musicElement&&app.flags.music!=='off'?createMediaLoopTrack(musicElement,{
gain:0.56,
bpm:episode.presentation?.musicBpm||MUSIC_PRESENTATION_BPM,
beatsPerBar:A.audio.beatsPerBar,
}):null;
const MUSIC_SOURCES=Object.freeze({
CARTRIDGE:episode.assets.audio?.url?Object.freeze({url:new URL('./'+episode.assets.audio.url,document.baseURI).href,bpm:episode.presentation?.musicBpm||MUSIC_PRESENTATION_BPM}):null,
ARCADE:Object.freeze({url:new URL('./'+ARCADE_MUSIC.url,document.baseURI).href,bpm:ARCADE_MUSIC.bpm}),
});
let musicKey='NONE';
app.musicTrack=musicKey;
function musicKeyFor(){
if (screen==='THEATER'||screen==='CRAWL') return 'CARTRIDGE';
if (game&&screen!=='ATTRACT'&&screen!=='MANUAL') return game.state.sim.mode==='ARCADE'?'ARCADE':'CARTRIDGE';
return 'NONE';
}
function selectMusic(key=musicKeyFor(),trusted=false){
if (key===musicKey){if (trusted&&key!=='NONE') startMusicFromGesture();return;}
musicKey=key;
app.musicTrack=key;
if (!music) return;
music.stop();
const source=MUSIC_SOURCES[key];
if (!source) return;
if (music.element.src!==source.url) music.element.src=source.url;
music.bpm=source.bpm;
app.musicBpm=source.bpm;
if (musicWanted||trusted) startMusicFromGesture();
}
let audio=null,audioContext=null,conductor=null,audioStarting=null;
let musicHeld=false;
const seededQuality=Number(app.flags.quality);
const qualityPinned=Number.isInteger(seededQuality)&&seededQuality>=0&&seededQuality<=2;
const frameTimes=[];let quality=qualityPinned?seededQuality:2,qualityCounter=0;
const pwa=setupPwa({base,onUpdateReady:()=>{app.updateReady=true;},onOffline:(msg)=>{menu.note=msg;}});
app.pwa=pwa;
const cabinet=document.getElementById('cabinet');
const hudRoot=document.getElementById('top-hud');
const externalHud=hudRoot?createExternalHud(hudRoot,{toastRoot:document.getElementById('hud-toast'),srRoot:document.getElementById('hud-sr')}):null;
const titleRoot=document.getElementById('title-screen');
const titleActions=document.getElementById('title-actions');
const titleNote=document.getElementById('title-note');
const riderToggle=document.getElementById('rider-toggle');
const manualRoot=document.getElementById('manual-screen');
const manualClose=document.getElementById('manual-close');
const TITLE_LABEL=Object.freeze({
'CONTINUE':'CONTINUE','NEW CAMPAIGN':'NEW GAME','CINEMA':'CINEMA','EJECT':'EJECT',
'CARTRIDGE':'CARTRIDGE','ARCADE SCORE ATTACK':'ARCADE','VS':'VS','QUICK REFERENCE':'MANUAL','DEVELOPMENT':'DEVELOPMENT',
'CREATE MATCH':'CREATE MATCH','JOIN MATCH':'JOIN MATCH',
'DEV-00':'DEV-00','CARTRIDGE WORKSHOP':'CARTRIDGE WORKSHOP','QR LOADER':'QR LOADER','TCS CAD FILES':'TCS CAD FILES','TCS CALIBRATION':'TCS CALIBRATION','NETWORK':'NETWORK','GAME SOURCE':'GAME SOURCE','BACK':'BACK',
'UNLOCK':'UNLOCK','RESET DATA':'ERASE SAVE','NEW RUN':'NEW RUN','RESUME RUN':'RESUME RUN',
});
const LEVEL_HEADING=Object.freeze({HOME:'MAIN MENU',DEV:'DEVELOPMENT',LOCK:'DEVELOPER CODE',ARCADE:'ARCADE',VS:'VS · TWO PHONES'});
const titleScreenRoot=document.getElementById('title-screen');
const titleHeading=document.querySelector('#title-menu h2');
const cartridgeHeading=titleHeading?titleHeading.textContent:'SELECT';
const devForm=document.getElementById('dev-code');
const devInput=document.getElementById('dev-code-input');
const homeButton=document.getElementById('home-button');
const slotInfo=app.slot||null;
const runtimeIsSlot=app.cartridgeSource==='installed'||app.cartridgeSource==='deployed';
let menuLevel=app.flags.menu==='cartridge'?'CARTRIDGE':'HOME';
let returnLevel='CARTRIDGE';
let devUnlocked=storage.getItem(DEV_UNLOCK_KEY)==='yes';
let tcsCal=null;
let netPanel=null;
{const v=document.getElementById('home-version');if (v) v.textContent='v'+BUILD_ID.replace(/^STRUTHIO-CONSOLE-/,'');}
let renderedMenuItems='';
function syncRiderToggle(){
if (!riderToggle) return;
const available=app.spriteProfile.id==='CONSOLE_FULL';
riderToggle.hidden=!available;
if (!available) return;
const enabled=scene.riderEnabled===true;
riderToggle.setAttribute('aria-pressed',String(enabled));
riderToggle.textContent=`HD RIDER · ${enabled?'ON':'OFF'}`;
}
function syncShellUi(){
const titleVisible=screen==='ATTRACT'&&!game;
const manualVisible=screen==='MANUAL';
if (titleRoot&&titleRoot.hidden===titleVisible) titleRoot.hidden=!titleVisible;
if (manualRoot&&manualRoot.hidden===manualVisible) manualRoot.hidden=!manualVisible;
document.body.classList.toggle('manual-open',manualVisible);
if (!titleActions) return;
const itemsKey=menu.items.join('|');
if (itemsKey!==renderedMenuItems){
titleActions.replaceChildren(...menu.items.map((item)=>{
const button=document.createElement('button');
button.type='button';button.dataset.titleItem=item;
const primary=menuLevel==='HOME'?'CARTRIDGE':menuLevel==='VS'?'CREATE MATCH':menuLevel==='DEV'?'DEV-00':menuLevel==='LOCK'?'UNLOCK':menuLevel==='ARCADE'?(menu.items.includes('RESUME RUN')?'RESUME RUN':'NEW RUN'):(menu.items.includes('CONTINUE')?'CONTINUE':'NEW CAMPAIGN');
button.className=item===primary?'is-primary':item==='QR LOADER'?'is-beta':'';
button.textContent=TITLE_LABEL[item]||item;
return button;
}));
titleActions.classList.toggle('has-save',menu.items.includes('CONTINUE'));
renderedMenuItems=itemsKey;
}
for (const button of titleActions.children){
const current=String(button.dataset.titleItem===menu.items[menu.index]);
if (button.getAttribute('aria-current')!==current) button.setAttribute('aria-current',current);
const label=button.dataset.titleItem==='RESET DATA'?(resetArmed?'CONFIRM ERASE':'ERASE SAVE'):null;
if (label&&button.textContent!==label) button.textContent=label;
}
const homeLike=menuLevel!=='CARTRIDGE';
if (titleScreenRoot){
titleScreenRoot.classList.toggle('is-home',homeLike);
if (titleScreenRoot.dataset.level!==menuLevel) titleScreenRoot.dataset.level=menuLevel;
}
if (titleHeading){const h=homeLike?LEVEL_HEADING[menuLevel]:cartridgeHeading;if (titleHeading.textContent!==h) titleHeading.textContent=h;}
if (devForm&&devForm.hidden===(menuLevel==='LOCK')) devForm.hidden=menuLevel!=='LOCK';
if (homeButton&&homeButton.hidden===(menuLevel==='CARTRIDGE')) homeButton.hidden=menuLevel!=='CARTRIDGE';
const note=menu.note||(saveWarning?'SAVE NOT UPDATED':app.updateReady?'UPDATE READY':pwa.offlineNote||'');
if (titleNote&&titleNote.textContent!==note) titleNote.textContent=note;
syncRiderToggle();
}
let controlDeck=null;
function resizeRenderer(){
const bounds=cabinet?cabinet.getBoundingClientRect():{width:window.innerWidth,height:window.innerHeight};
renderer.resize(Math.max(256,bounds.width),Math.max(384,bounds.height));
recordLayout(bounds);
}
const layoutProbe=document.createElement('div');
layoutProbe.style.cssText='position:fixed;left:0;top:env(safe-area-inset-top);bottom:env(safe-area-inset-bottom);width:0;visibility:hidden;pointer-events:none';
document.body.appendChild(layoutProbe);
let layoutPanel=null;
{
let taps=0,lastTap=0;
document.querySelector('#cartridge-card .slot-card-header')?.addEventListener('click',()=>{
const now=performance.now();taps=now-lastTap<900?taps+1:1;lastTap=now;
if (taps<5) return;
taps=0;
const order=['off','on','on-noshim'];
const current=storage.getItem(LAYOUT_DEBUG_KEY)||'off';
storage.setItem(LAYOUT_DEBUG_KEY,order[(order.indexOf(current)+1)%order.length]);
location.reload();
});
}
function recordLayout(bounds){
const rect=(el)=>{if (!el) return null;const r=el.getBoundingClientRect();return{x:+r.x.toFixed(1),y:+r.y.toFixed(1),w:+r.width.toFixed(1),h:+r.height.toFixed(1)};};
const probe=layoutProbe.getBoundingClientRect();
const canvasBox=rect(canvas);
const widthFit=bounds.width/256,heightFit=bounds.height/384;
app.layout={
viewport:{w:window.innerWidth,h:window.innerHeight},screen:{w:window.screen.width,h:window.screen.height},
standalone:navigator.standalone===true||!!window.matchMedia?.('(display-mode: standalone)').matches,
safe:{top:+probe.top.toFixed(1),bottom:+(window.innerHeight-probe.bottom).toFixed(1)},
safeBottomUsed:parseFloat(getComputedStyle(document.getElementById('controls')||document.body).getPropertyValue('--safe-bottom'))||0,
iosShim:parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ios-shim'))||0,
shimReport:app.viewportShim?app.viewportShim.report:null,
hud:rect(document.getElementById('top-hud')),deck:rect(document.getElementById('controls')),
cabinet:{w:+bounds.width.toFixed(1),h:+bounds.height.toFixed(1)},display:canvasBox,
backing:{w:canvas.width,h:canvas.height},
limitingAxis:widthFit<=heightFit+1e-6?'width':'height',
widthDeficit:canvasBox?+(bounds.width-canvasBox.w).toFixed(1):null,
};
if (app.flags.debug==='layout'){
if (!layoutPanel){
layoutPanel=document.createElement('pre');
layoutPanel.setAttribute('aria-hidden','true');
layoutPanel.style.cssText='position:fixed;z-index:90;left:4px;top:calc(env(safe-area-inset-top) + 46px);margin:0;padding:6px 8px;max-width:calc(100% - 8px);box-sizing:border-box;background:rgba(0,0,0,.82);color:#9df6fa;font:10px/1.35 monospace;pointer-events:none;white-space:pre-wrap';
document.body.appendChild(layoutPanel);
}
const L=app.layout,f=(b)=>b?`${b.w}x${b.h}@${b.x},${b.y}`:'-';
layoutPanel.textContent=`LAYOUT ${BUILD_ID}\nviewport ${L.viewport.w}x${L.viewport.h}  screen ${L.screen.w}x${L.screen.h}\nstandalone ${L.standalone}  safe ${L.safe.top}/${L.safe.bottom} (bottom used ${Math.max(0,L.safe.bottom-L.iosShim)})  iosShim ${L.iosShim}${L.shimReport&&L.shimReport.disabled?' (OFF)':''}  gap ${L.shimReport?L.shimReport.gap:'-'}\nhud ${f(L.hud)}\ndeck ${f(L.deck)}\ncabinet ${L.cabinet.w}x${L.cabinet.h}\ndisplay ${f(L.display)}  backing ${L.backing.w}x${L.backing.h}\nlimiting ${L.limitingAxis}  widthDeficit ${L.widthDeficit}px`;
}
}
function restoreAvailable(){return restoreCheckpoint(storage,schema);}
function refreshTitleMenu(note=menu.note,preferContinue=false){
const restore=restoreAvailable();
const arcadeActive=menuLevel==='ARCADE'&&arcadeRestore().active;
const selected=preferContinue&&restore.status==='RESTORE'?'CONTINUE':menuLevel==='ARCADE'?(arcadeActive?'RESUME RUN':'NEW RUN'):menu.items[menu.index];
const items=itemsForLevel(menuLevel,menuLevel==='ARCADE'?(arcadeActive?'ARCADE_ACTIVE':'NONE'):restore.status);
if (menuLevel==='ARCADE'&&!note) note=arcadeNote();
const preserved=items.indexOf(selected);
menu={items,index:preserved>=0?preserved:0,note};
app.restore={status:restore.status,foreign:restore.foreign};
if (controlDeck) controlDeck.sync();
return restore;
}
function moveTitle(delta){
if (!menu.items.length) return;
menu.index=(menu.index+delta+menu.items.length)%menu.items.length;
menu.note='';
resetArmed=false;ejectArmed=false;
if (controlDeck) controlDeck.sync();
syncShellUi();
if (titleRoot&&!titleRoot.hidden) titleActions?.children[menu.index]?.focus({preventScroll:true});
}
let resetArmed=false;
function setLevel(level,note='',select=null){
menuLevel=level;
resetArmed=false;ejectArmed=false;
refreshTitleMenu(note,level==='CARTRIDGE');
if (select&&menu.items.includes(select)) menu.index=menu.items.indexOf(select);
syncShellUi();
if (level==='LOCK'&&devInput){devInput.value='';devInput.focus({preventScroll:true});}
else if (titleRoot&&!titleRoot.hidden) titleActions?.children[menu.index]?.focus({preventScroll:true});
}
function gotoRuntime(internal){
const next=new URL(location.href);
if (internal) next.searchParams.set('rom','dev-00');else next.searchParams.delete('rom');
next.searchParams.delete('episode');
next.searchParams.set('menu','cartridge');
location.href=next.href;
}
async function tryUnlock(){
const code=(devInput?.value||'').trim().toLowerCase();
let hex='';
try{hex=[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(code)))].map((b)=>b.toString(16).padStart(2,'0')).join('');}catch{hex='';}
if (hex===DEV_CODE_SHA256){devUnlocked=true;storage.setItem(DEV_UNLOCK_KEY,'yes');setLevel('DEV','DEVELOPMENT UNLOCKED');}
else{menu.note=code?'WRONG CODE':'ENTER THE DEVELOPER CODE';if (devInput){devInput.value='';devInput.focus({preventScroll:true});}syncShellUi();}
}
let ejectArmed=false;
function selectTitle(){
const item=menu.items[menu.index];
if (item==='RESET DATA'&&!resetArmed){resetArmed=true;menu.note='FLAP AGAIN TO ERASE YOUR SAVE';if (controlDeck) controlDeck.sync();return;}
resetArmed=false;
if (item==='CARTRIDGE'){
if (!slotInfo){if (app.cartridgeManager) app.cartridgeManager.pick();return;}
if (runtimeIsSlot) setLevel('CARTRIDGE');else gotoRuntime(false);
}else if (item==='ARCADE SCORE ATTACK') setLevel('ARCADE');
else if (item==='VS') setLevel('VS');
else if (item==='CREATE MATCH'){if (vsUi) vsUi.host();}
else if (item==='JOIN MATCH'){if (vsUi) vsUi.openJoin();}
else if (item==='NEW RUN'){returnLevel='ARCADE';startNewGame('ARCADE');}
else if (item==='RESUME RUN'){returnLevel='ARCADE';resumeArcade();}
else if (item==='QUICK REFERENCE') openManual();
else if (item==='DEVELOPMENT') setLevel(devUnlocked?'DEV':'LOCK');
else if (item==='DEV-00'){if (app.cartridgeSource==='internal') setLevel('CARTRIDGE');else gotoRuntime(true);}
else if (item==='CARTRIDGE WORKSHOP') location.href=new URL('factory/',location.href).href;
else if (item==='QR LOADER'){if (app.qrCart) app.qrCart.open();}
else if (item==='TCS CAD FILES') location.href=new URL('tcs/',location.href).href;
else if (item==='NETWORK'){if (!netPanel) netPanel=setupNetworkPanel({relayUrl:app.relayUrl||relayUrlFor('./',''),build:BUILD_ID,openModal});netPanel.open();app.netPanel=netPanel;}
else if (item==='TCS CALIBRATION'){if (!tcsCal) tcsCal=setupTcsCalibration({build:BUILD_ID,openModal});tcsCal.open();app.tcsCal=tcsCal;}
else if (item==='GAME SOURCE') location.href=new URL('source/',location.href).href;
else if (item==='UNLOCK') tryUnlock();
else if (item==='BACK') setLevel('HOME','',menuLevel==='DEV'||menuLevel==='LOCK'?'DEVELOPMENT':menuLevel==='ARCADE'?'ARCADE SCORE ATTACK':menuLevel==='VS'?'VS':null);
else if (item==='CONTINUE'){returnLevel='CARTRIDGE';continueGame();}
else if (item==='NEW CAMPAIGN'){returnLevel='CARTRIDGE';screen='CRAWL';crawlTicks=0;crawlHold=0;input.setMode('CINEMA_SKY');}
else if (item==='CINEMA'){returnLevel='CARTRIDGE';startTheater();}
else if (item==='EJECT'){
const removable=app.cartridgeSource==='installed';
if (!removable){setLevel('HOME',app.cartridgeSource==='internal'?'DEV-00 ROM PUT AWAY':'','CARTRIDGE');return;}
if (!ejectArmed){ejectArmed=true;menu.note='PRESS AGAIN TO EJECT · YOUR SAVES STAY ON THIS DEVICE';syncShellUi();return;}
ejectArmed=false;menu.note='EJECTING…';syncShellUi();
if (app.cartridgeManager) app.cartridgeManager.eject();
}
else if (item==='RESET DATA'){resetData(storage);saveWarning=false;storage.removeItem(KEYS.WARNING);refreshTitleMenu('DATA RESET');}
}
let releaseManual=null;
function openManual(){
screen='MANUAL';
input.setMode('ATTRACT');
if (controlDeck) controlDeck.sync();
syncShellUi();
if (manualRoot) releaseManual=openModal(manualRoot,{onEscape:closeManual,initialFocus:manualRoot});
}
function closeManual(){
if (screen!=='MANUAL') return false;
screen='ATTRACT';
input.setMode('ATTRACT');
if (controlDeck) controlDeck.sync();
syncShellUi();
const action=titleActions?.querySelector('[data-title-item="QUICK REFERENCE"]')||titleActions?.children[menu.index];
if (releaseManual){const release=releaseManual;releaseManual=null;release.call(null);}
if (action) action.focus({preventScroll:true});
return true;
}
function startTheater(){
screen='THEATER';
selectMusic(undefined,true);
const seq=theaterSequence(A,reel);
theater={seq,index:0,item:seq[0],t:0,ticks:0,hold:0,runner:null};
view.crawlDone=false;
input.setMode('CINEMA_SKY');
}
function endTheater(){
theater=null;
screen='ATTRACT';
selectMusic();
input.setMode('ATTRACT');
menuLevel=returnLevel;
refreshTitleMenu('',false);
}
function paintReelWorld(s){
applyWorldArt(s);
}
function enterTheaterItem(index){
theater.index=index;theater.t=0;theater.runner=null;
theater.item=theater.seq[index];
if (!theater.item) return endTheater();
if (theater.item.kind==='PLAY'){
theater.runner=createClipRunner(A,theater.item.clip);
ascentCamera.reset();
resetFeelState(feel);
banner=null;
prev=new Map();prevPlayer=null;
paintReelWorld(theater.runner.game.state);
}
}
function stepTheater(frame){
theater.hold=frame.flapHeld?theater.hold+1:0;
if (theater.hold>=C.cinemaSkipHoldTicks) return endTheater();
const item=theater.item;
if (item.kind==='CRAWL'){
theater.ticks+=1;
if (view.crawlDone){view.crawlDone=false;enterTheaterItem(theater.index+1);}
return;
}
if (item.kind==='PLAY') stepReel(theater.runner);
theater.t+=1;
if (theater.t>=item.length) enterTheaterItem(theater.index+1);
}
function stepReel(runner){
const s=runner.game.state;
if (runner.ended) return;
prev=new Map(s.actors.map((a)=>[a.id,{x:a.x,y:a.y}]));prevPlayer={x:s.player.x,y:s.player.y};
const before=s.world.contentId;
const r=runner.step();
if (!r) return;
const g=runner.game.state,playerX=Math.floor(g.player.x/256)+14,playerTop=Math.floor(g.player.y/256);
for (const e of r.events){
if (e.type==='ARENA_ACTIVATE') paintReelWorld(g);
if (e.type==='RING') triggerFeel(feel,{kind:e.boss||e.order===6?'RING_GREEN':'RING',tick:renderTick,duration:22,strength:.92,priority:3,x:playerX,y:playerTop,space:'PLAYER_CENTER',contentId:before});
if (e.type==='JOUST_CLASH') triggerFeel(feel,{kind:'CLASH',tick:renderTick,duration:8,shake:5,strength:.9,priority:4,x:playerX,y:playerTop,space:'PLAYER_CENTER',contentId:before});
if (e.type==='JOUST_WIN') triggerFeel(feel,{kind:'JOUST_WIN',tick:renderTick,duration:14,shake:8,strength:1.35,priority:5,x:playerX,y:playerTop,space:'PLAYER_CENTER',contentId:before});
if (e.type==='BOSS_HIT'){
triggerFeel(feel,{kind:'BOSS_HIT',tick:renderTick,duration:24,shake:12,strength:1.5,priority:5,x:playerX,y:playerTop,space:'PLAYER_CENTER',contentId:before});
banner={text:e.remaining===1?'ONE MORE HIT':`BOSS HIT - ${e.remaining} TO GO`,until:renderTick+75};
}
if (e.type==='BOSS_CLEAR') triggerFeel(feel,{kind:'BOSS_HIT',tick:renderTick,duration:THEATER_BOSS_FREEZE,shake:14,strength:1.6,priority:6,x:playerX,y:playerTop,space:'PLAYER_CENTER',contentId:before});
if (e.type==='PLAYER_DEATH') triggerFeel(feel,{kind:'DEATH',tick:renderTick,duration:18,shake:11,strength:1.45,priority:6,x:playerX,y:playerTop,space:'PLAYER_CENTER',contentId:before});
}
}
function checkpoint(reason,forced=false){
if (!game||game.vs) return null;
const hidden=document.visibilityState==='hidden';
const r=writeCheckpoint(storage,schema,payloadOf(game.state),{hidden,budgetMs:A.save_protocol.interruptions.hiddenBudgetMs,now:()=>performance.now()});
if (!r.committed) saveWarning=true;
app.lastCheckpoint={reason,forced,...r,tick:game.state.sim.tick};
return r;
}
function startMusicFromGesture(){
if (music) musicWanted=true;
if (!music||musicHeld||musicKey==='NONE') return;
if (music.element.paused) music.playing=false;
try{
const attempt=music.start();
if (attempt&&typeof attempt.catch==='function') attempt.catch((error)=>{app.musicError=String(error);});
}catch (error){app.musicError=String(error);}
}
function wakeAudioContext(context){
const attempt=primeAudioContext(context);
if (attempt&&typeof attempt.catch==='function') attempt.catch((error)=>{app.audioResumeError=String(error);});
}
function ensureAudio(){
startMusicFromGesture();
if (audio){
if (!musicHeld) wakeAudioContext(audio.ctx);
return Promise.resolve(audio);
}
if (audioStarting){if (!musicHeld) wakeAudioContext(audioContext);return audioStarting;}
const AudioContextClass=window.AudioContext||window.webkitAudioContext;
if (!AudioContextClass){
app.audio={conductor:null,music,ctx:null,warnings:['WEB_AUDIO_UNAVAILABLE'],mode:music?'NATIVE_MP3':'SILENT'};
return Promise.resolve(music?app.audio:null);
}
audioContext=new AudioContextClass({latencyHint:'interactive'});
wakeAudioContext(audioContext);
audioStarting=(async ()=>{
const ctx=audioContext;
const warnings=[];
try{
const master=ctx.createGain();
const limiter=ctx.createDynamicsCompressor();
master.gain.value=0.92;
limiter.threshold.value=-12;
limiter.knee.value=12;
limiter.ratio.value=8;
limiter.attack.value=0.003;
limiter.release.value=0.25;
master.connect(limiter).connect(ctx.destination);
let node=null;
try{
await ctx.audioWorklet.addModule(base+'src/audio/worklet.mjs');
node=new AudioWorkletNode(ctx,'struthio-synth',{outputChannelCount:[2]});
const sfxGain=ctx.createGain();
sfxGain.gain.value=0.68;
node.connect(sfxGain).connect(master);
node.port.postMessage({type:'init',audio:consoleAudio(A.audio)});
conductor=new Conductor(A.audio,{context:ctx,send:(message)=>node.port.postMessage(message)});
}catch (error){
warnings.push(`SFX ${error}`);
}
if (!music&&!conductor) throw new Error(warnings.join(' | ')||'AUDIO_UNAVAILABLE');
audio={ctx,node,master,limiter};
app.audio={conductor,music,ctx,warnings,mode:music?'NATIVE_MP3':'SYNTH'};
return audio;
}catch (error){
app.audioError=String(error);
if (ctx&&ctx.state!=='closed') await ctx.close().catch(()=>{});
if (audioContext===ctx) audioContext=null;
return null;
}finally{
audioStarting=null;
}
})();
return audioStarting;
}
function holdMusic(held){
if (musicHeld===held) return;
musicHeld=held;
if (held){if (music) music.stop();}
else{startMusicFromGesture();const ctx=audio?audio.ctx:audioContext;if (ctx) wakeAudioContext(ctx);}
app.musicHeld=musicHeld;
}
let musicWanted=false,musicRetryAt=0,musicFailures=0;
function musicShouldPlay(){return!!music&&musicKey!=='NONE'&&musicWanted&&!musicHeld&&!app.stopped&&document.visibilityState==='visible';}
function reviveMusic(now=performance.now(),force=false){
if (!musicShouldPlay()) return;
const el=music.element;
if (!el.paused&&!el.ended&&el.readyState>=2){musicFailures=0;return;}
if (!force&&now<musicRetryAt) return;
musicRetryAt=now+1500;
try{
if (el.error||(el.networkState===3)||musicFailures>=3){el.load();musicFailures=0;}
music.playing=false;
const attempt=music.start();
if (attempt&&typeof attempt.then==='function') attempt.then(()=>{musicFailures=0;app.musicRevived=(app.musicRevived||0)+1;},(error)=>{musicFailures+=1;app.musicError=String(error);});
}catch (error){musicFailures+=1;app.musicError=String(error);}
}
function startNewGame(mode){
const seed=mode==='ARCADE'?(app.flags.seed>>>0||(crypto.getRandomValues(new Uint32Array(1))[0]>>>0)):(app.flags.seed>>>0||1);
holdMusic(false);
game=new Game(A,{mode,seed});
ascentCamera.reset();
resetFeelState(feel);
gameOverInfo=null;winnerInfo=null;popups.length=0;
game.start();
app.game=game;
onArena();
screen='GAME';
selectMusic(undefined,true);
input.setMode('PLAY');
checkpoint('NEW_GAME');
}
function resumeArcade(){
const r=arcadeRestore();
if (!r.active){setLevel('ARCADE','NO RUN TO RESUME');return;}
holdMusic(false);
game=new Game(A,{state:structuredClone(r.record.payload)});
ascentCamera.reset();
resetFeelState(feel);
gameOverInfo=null;winnerInfo=null;popups.length=0;
app.game=game;
if (r.repairPointer) storage.setItem(keysFor('ARCADE').ACTIVE,r.repairPointer);
onArena();
screen='GAME';
selectMusic(undefined,true);
if (game.state.sim.shell==='PAUSE') game.state.sim.shell='PLAY';
input.setMode('PLAY');
app.resumedArcade={tick:game.state.sim.tick,digest:game.stateDigest()};
}
function continueGame(){
const r=restoreAvailable();
if (r.status!=='RESTORE'){
refreshTitleMenu(r.status==='REJECTED'?'SAVE REJECTED: RESET OR START AGAIN':'NO CHECKPOINT');
return;
}
holdMusic(false);
game=new Game(A,{state:structuredClone(r.record.payload)});
ascentCamera.reset();
resetFeelState(feel);
app.game=game;
if (r.repairPointer) storage.setItem(KEYS.ACTIVE,r.repairPointer);
onArena();
screen='GAME';
selectMusic(undefined,true);
if (game.state.sim.shell==='PAUSE') game.state.sim.shell='PLAY';
input.setMode(game.state.sim.shell==='CINEMA_SKY'?'CINEMA_SKY':'PLAY');
app.continued={slot:r.slot,tick:game.state.sim.tick,digest:game.stateDigest()};
}
function toTitle(){
if (vsUi&&vsUi.mode!=='IDLE'){vsUi.leave();return;}
scene.vsUniform=false;
holdMusic(false);
game=null;
ascentCamera.reset();
resetFeelState(feel);
app.game=null;
screen='ATTRACT';
selectMusic();
input.setMode('ATTRACT');
menuLevel=returnLevel;
refreshTitleMenu('',true);
syncShellUi();
}
const CAMPAIGN_GAMEOVER_ITEMS=Object.freeze(['CONTINUE','MAIN MENU']);
const ARCADE_GAMEOVER_ITEMS=Object.freeze(['NEW RUN','MAIN MENU']);
const gameOverItems=()=>(game&&game.state.sim.mode==='ARCADE'?ARCADE_GAMEOVER_ITEMS:CAMPAIGN_GAMEOVER_ITEMS);
let gameOverIndex=0;
function moveGameOver(delta){const n=gameOverItems().length;gameOverIndex=(gameOverIndex+delta+n)%n;if (controlDeck) controlDeck.sync();}
function confirmGameOver(){
const choice=gameOverItems()[gameOverIndex];
gameOverIndex=0;
if (choice==='MAIN MENU'){toTitle();return 'MENU';}
if (choice==='NEW RUN'){startNewGame('ARCADE');return 'NEW_RUN';}
unlimitedContinue();
return 'CONTINUE';
}
const isGameOver=()=>!!game&&game.state.sim.shell==='GAMEOVER';
function unlimitedContinue(){
if (!game||!applyUnlimitedContinue(game.state,C)) return false;
input.cleanup();
input.setMode('PLAY');
banner={text:'CONTINUE',until:renderTick+Math.min(C.waveClearTicks,90)};
saveWarning=false;
storage.removeItem(KEYS.WARNING);
checkpoint('UNLIMITED_CONTINUE',true);
if (controlDeck) controlDeck.sync();
app.lastContinue={tick:game.state.sim.tick,lives:game.state.sim.lives,digest:game.stateDigest()};
return true;
}
function onArena(){
applyWorldArt(game.state);
}
function applyWorldArt(s){
const art=worldArtFor(s);
const backgroundStage=backgroundStageFor(s);
paintWorld(atlas,backgroundStage,art);
app.backgroundStage=backgroundStage;
app.worldArt=atlas.artSet;
renderer.markAtlasDirty();
renderer.markWorldDirty();
const jousters=atlas.artSet==='ARCADE'&&!!arcadeBirdSheet;
const want=jousters?arcadeBirdSheet:heroSprites;
if (currentBird!==want){currentBird=want;renderer.setBird(want,jousters);}
scene.verticalAscent=jousters?true:app.spriteProfile.verticalAscent===true;
scene.riderEnabled=jousters?false:app.riderEnabled;
app.birdProfile=jousters?'ARCADE_JOUST_48':app.spriteProfile.id;
scene.playerMaterial=jousters?MATERIAL_ARCADE_PLAYER:0;
const globeOn=atlas.artSet==='ARCADE'&&app.flags.globe!=='off'&&!!atlas.arcadeStage?.rear;
if (globeOn&&atlas.arcadeStage.globe===undefined) atlas.arcadeStage.globe=buildArcadeGlobe(atlas.arcadeStage.rear);
const globe=globeOn?atlas.arcadeStage.globe:null;
renderer.setGlobe(globe,globe?globe.params:null);
app.globe=globe?'TURNING':'OFF';
const fxOn=atlas.artSet==='ARCADE'&&app.flags.arcadeFx!=='off'&&!!atlas.arcadeStage?.rear;
renderer.setArcadeFx(fxOn?ARCADE_REAR_HORIZON:null);
app.arcadeFx=fxOn?'ON':'OFF';
}
let vsUi=null;
const vsGame={vs:true,state:null};
let vsBase=null;
const VS_RINGS=VS_SIM.vsContent(A).rings.length;
function vsViewOf(v,seat){
if (!vsBase){
vsBase=newState('ARCADE',1,C);
vsBase.objectives.routeId='ARC_C1_R1';vsBase.objectives.waveId='ARC_W1';
vsBase.objectives.spawnCursor=arenaContent(A,vsBase).rosterList.length;
vsBase.objectives.hostileClear=true;
vsBase.sim.shell='PLAY';
}
const b=vsBase,me=v.birds[seat];
b.sim.tick=v.tick;
b.world=v.world;
b.objectives.ringMask=(1<<Math.min(me.rings,VS_RINGS))-1;
b.player={x:me.x,y:me.y,vx:me.vx,vy:me.vy,groundedPlatformId:me.groundedPlatformId,facing:me.facing,wing:me.wing,
flapCooldown:me.flapCooldown,footingTicks:me.footingTicks,lavaPhase:me.lavaPhase,lavaTicks:me.lavaTicks,
invulnerableTicks:me.hidden>0?VS_SHIMMER+me.hidden:me.invulnerableTicks};
b.actors=[];
v.birds.forEach((o,i)=>{
if (i===seat||o.hidden>0) return;
b.actors.push({id:i+1,vsBird:true,kind:'RIVAL',class:'HUNTER',tier:1,ghost:'BLINKY',lifecycle:'MOUNTED',timer:0,phase:0,
x:o.x,y:o.y,vx:o.vx,vy:o.vy,facing:o.facing,groundedPlatformId:o.groundedPlatformId,flapCooldown:o.flapCooldown,
invulnerableTicks:o.invulnerableTicks,lavaPhase:o.lavaPhase});
});
return b;
}
function vsSample(){
const pilot=app.flags.vsPilot==='1'&&typeof window.__vsPilot==='function'?window.__vsPilot:null;
if (pilot) return VS_SIM.decodeInput(pilot(vsUi.view,vsUi.seat)|0);
const v=vsUi.view,me=v&&v.birds[vsUi.seat];
const ready=!me||(v.phase==='PLAY'&&me.hidden===0&&me.flapCooldown<=2&&me.wing>0);
return input.frame({acceptFlap:ready});
}
function vsFrame(){
const v=vsUi.frame();
if (v) vsGame.state=vsViewOf(v,vsUi.seat);
prev=new Map();prevPlayer=null;
}
function vsStart(){
holdMusic(false);
ascentCamera.reset();
resetFeelState(feel);
gameOverInfo=null;winnerInfo=null;popups.length=0;banner=null;
vsGame.state=vsViewOf(vsUi.view,vsUi.seat);
game=vsGame;app.game=game;
vsUi.setSampler(vsSample);
returnLevel='VS';
onArena();
scene.vsUniform=true;
screen='GAME';
selectMusic(undefined,true);
input.cleanup();
input.setMode('PLAY');
app.vs={seat:vsUi.seat,started:performance.now()};
}
function vsExit(){
scene.vsUniform=false;
if (game&&game.vs){returnLevel='VS';toTitle();}
else{menuLevel='VS';refreshTitleMenu('',true);syncShellUi();}
}
function vsEvent(e,seat){
const s=vsGame.state;if (!s) return;
const before=s.world.contentId;
const px=Math.floor(s.player.x/256)+14,top=Math.floor(s.player.y/256);
const sfx=(type)=>{if (conductor) conductor.onEvents([{type}]);};
if (e.type==='VS_FLAP'&&e.who===seat){triggerFeel(feel,{kind:'FLAP',tick:renderTick,duration:5,strength:.32,priority:1,x:px,y:top,space:'PLAYER_CENTER',contentId:before});sfx('FLAP');}
else if (e.type==='VS_RING'&&e.who===seat){
const ring=VS_SIM.vsContent(A).rings[e.order-1];
triggerFeel(feel,{kind:e.order===e.total?'RING_GREEN':'RING',tick:renderTick,duration:22,strength:.92,priority:3,x:ring?.center[0]??px,y:ring?.center[1]??top,space:ring?'WORLD':'PLAYER_CENTER',contentId:before});
sfx('RING');if (music) music.duck({depth:.82,attack:.006,hold:.012,release:.11});pulseHaptic(8);
}else if (e.type==='VS_CLASH'&&(e.a===seat||e.b===seat)){
triggerFeel(feel,{kind:'CLASH',tick:renderTick,duration:8,shake:5,strength:.9,priority:4,x:px,y:top,space:'PLAYER_CENTER',contentId:before});
sfx('JOUST_CLASH');pulseHaptic(12);
}else if (e.type==='VS_JOUST'&&e.winner===seat){
triggerFeel(feel,{kind:'JOUST_WIN',tick:renderTick,duration:14,shake:8,strength:1.35,priority:5,x:px,y:top,space:'PLAYER_CENTER',contentId:before});
sfx('JOUST_WIN');if (music) music.duck({depth:.42,attack:.004,hold:.035,release:.24});pulseHaptic([14,18,22]);
}else if (e.type==='VS_JOUST'&&e.loser===seat){
triggerFeel(feel,{kind:'DEATH',tick:renderTick,duration:18,shake:11,strength:1.45,priority:6,x:px,y:top,space:'PLAYER_CENTER',contentId:before});
sfx('PLAYER_DEATH');input.cleanup();if (music) music.duck({depth:.3,attack:.006,hold:.06,release:.38});pulseHaptic([26,24,34]);
}else if (e.type==='VS_JOUST') sfx('JOUST_CLASH');
else if (e.type==='VS_DEATH'&&e.who===seat&&e.cause==='LAVA'){sfx('PLAYER_DEATH');input.cleanup();}
else if (e.type==='VS_GO'){sfx('CIRCUIT_SYNC');pulseHaptic(10);}
}
{
const relayOverride=app.flags.relay||(document.querySelector('meta[name="struthio-vs-relay"]')?.content||'').trim();
app.relayUrl=relayUrlFor(base,relayOverride);
vsUi=setupVs({
base,relayUrl:app.relayUrl,vs:VS_SIM,A,
hello:()=>({proto:1,vs:VS_SIM.VS_VERSION,compat:VS_SIM.vsCompat(A),build:BUILD_ID}),
onStart:vsStart,onEvent:vsEvent,onExit:vsExit,
log:(k,d)=>{app.vsLog=app.vsLog||[];app.vsLog.push([Math.round(performance.now()),k,d]);if (app.vsLog.length>200) app.vsLog.shift();},
});
app.vsUi=vsUi;
const deep=vsUi.parseVsCode(new URLSearchParams(location.search).get('vs')||'');
if (!deep&&vsUi.resumeIfAny()){menuLevel='VS';refreshTitleMenu('',true);}
else if (deep){
const clean=new URL(location.href);clean.searchParams.delete('vs');history.replaceState(null,'',clean.href);
menuLevel='VS';refreshTitleMenu('',true);
setTimeout(()=>vsUi.openJoin(deep),0);
}
}
function stepGame(){return stepGameWith(input.frame({acceptFlap:canAcceptBufferedFlap(game.state,C)}));}
function stepGameWith(frame){
const s=game.state;
const shell=s.sim.shell;
prev=new Map(s.actors.map((a)=>[a.id,{x:a.x,y:a.y}]));prevPlayer={x:s.player.x,y:s.player.y};
if (shell==='PAUSE'){if (frame.flapEdge) resume('FLAP');return;}
if (shell==='GAMEOVER'){if (frame.flapEdge) confirmGameOver();return;}
if (shell==='WINNER'){if (frame.flapEdge) toTitle();return;}
const before=s.world.contentId;
const contentBefore=arenaContent(A,s);
const wasGrounded=!!s.player.groundedPlatformId;
const r=game.tick(frame);
if (conductor) conductor.onEvents(r.events);
for (const e of r.events){
if (e.type==='ARENA_ACTIVATE') onArena();
if (e.type==='BOSS_CLEAR') onArena();
if (['LEVEL_READY','ROUTE_SCORE_ONLY'].includes(e.type)) banner={text:'FLIGHT COMPLETE - RIVALS REMAIN',until:renderTick+C.waveClearTicks};
if (['WAVE_READY','WAVE_SCORE_ONLY'].includes(e.type)) banner={text:'RIVALS CLEARED - RINGS REMAIN',until:renderTick+C.waveClearTicks};
if (e.type==='HOSTILE_CLEAR'&&!contentBefore.kind.startsWith('BOSS')) banner={text:'SKY CLEAR - FLY THE RINGS',until:renderTick+90};
if (e.type==='CIRCUIT_SYNC') banner={text:A.story_strings.SYNC,until:renderTick+C.waveClearTicks};
if (e.type==='SECTOR_RETIRED') banner={text:retireBannerText(e,game.state.sim.mode),until:renderTick+150};
if (e.type==='EXTRA_LIFE') banner={text:'EXTRA JOUST MARK',until:renderTick+100};
if (e.type==='SCORE_AWARD'){
if (e.kind==='BOSS_PERFECT') banner={text:`PERFECT BOSS +${e.amount}`,until:renderTick+120};
const pop=SCORE_POPUP[e.kind];
if (pop){
const ring=e.kind==='RING'?contentBefore.rings.find((q)=>q.order===e.order):null;
const px=ring?ring.center[0]:Math.floor(game.state.player.x/256)+14;
const py=ring?ring.center[1]-14:Math.floor(game.state.player.y/256)+4;
popups.push({text:String(e.amount),tone:pop,x:px,y:py,tick:renderTick,contentId:before,big:e.kind==='EGG'&&e.chain>=4});
if (popups.length>8) popups.shift();
}
}
if (e.type==='PLAYER_DEATH'||e.type==='CINEMA_START'||e.type==='GAMEOVER'||e.type==='WINNER') input.cleanup();
if (e.type==='GAMEOVER'){gameOverIndex=0;if (game.state.sim.mode==='ARCADE') gameOverInfo=recordArcadeRun(game.state);}
if (e.type==='WINNER') winnerInfo=recordCampaignRun(game.state);
if (e.type==='CINEMA_START') input.setMode('CINEMA_SKY');
if (e.type==='CINEMA_COMPLETE'){input.setMode(game.state.sim.shell==='WINNER'?'ATTRACT':'PLAY');if (game.state.sim.shell==='PLAY') onArena();}
const playerX=Math.floor(game.state.player.x/256)+14;
const playerTop=Math.floor(game.state.player.y/256);
if (e.type==='FLAP') triggerFeel(feel,{kind:'FLAP',tick:renderTick,duration:5,strength:.32,priority:1,x:playerX,y:playerTop,space:'PLAYER_CENTER',contentId:before});
if (e.type==='RING'){
const ring=contentBefore.rings.find((candidate)=>candidate.id===e.ringId);
triggerFeel(feel,{kind:e.boss||e.order===6?'RING_GREEN':'RING',tick:renderTick,duration:22,strength:.92,priority:3,x:ring?.center[0]??playerX,y:ring?.center[1]??playerTop,space:ring?'WORLD':'PLAYER_CENTER',contentId:before});
if (music) music.duck({depth:.82,attack:.006,hold:.012,release:.11});
pulseHaptic(8);
}
if (e.type==='JOUST_CLASH'){
triggerFeel(feel,{kind:'CLASH',tick:renderTick,duration:8,shake:5,strength:.9,priority:4,x:playerX,y:playerTop,space:'PLAYER_CENTER',contentId:before});
if (music) music.duck({depth:.68,attack:.004,hold:.018,release:.14});
pulseHaptic(12);
}
if (e.type==='BOSS_HIT'){
const bossActor=game.state.actors.find((a)=>a.id===e.rival);
const bx=bossActor?Math.floor(bossActor.x/256)+14:playerX,by=bossActor?Math.floor(bossActor.y/256):playerTop;
triggerFeel(feel,{kind:'BOSS_HIT',tick:renderTick,duration:24,shake:12,strength:1.5,priority:5,x:bx,y:by,space:'PLAYER_CENTER',contentId:before});
banner={text:e.remaining===1?'ONE MORE HIT':`BOSS HIT - ${e.remaining} TO GO`,until:renderTick+75};
if (music) music.duck({depth:.38,attack:.004,hold:.05,release:.3});
pulseHaptic([18,22,30]);
}
if (e.type==='JOUST_WIN'){
triggerFeel(feel,{kind:'JOUST_WIN',tick:renderTick,duration:14,shake:8,strength:1.35,priority:5,x:playerX,y:playerTop,space:'PLAYER_CENTER',contentId:before});
if (music) music.duck({depth:.42,attack:.004,hold:.035,release:.24});
pulseHaptic([14,18,22]);
}
if (e.type==='PLAYER_DEATH'){
triggerFeel(feel,{kind:'DEATH',tick:renderTick,duration:18,shake:11,strength:1.45,priority:6,x:Math.floor(prevPlayer.x/256)+14,y:Math.floor(prevPlayer.y/256),space:'PLAYER_CENTER',contentId:before});
if (music) music.duck({depth:.3,attack:.006,hold:.06,release:.38});
pulseHaptic([26,24,34]);
}
}
if (!wasGrounded&&game.state.player.groundedPlatformId&&!r.events.some((e)=>e.type==='PLAYER_DEATH')){
triggerFeel(feel,{kind:'LAND',tick:renderTick,duration:7,shake:3,strength:.58,priority:2,x:Math.floor(game.state.player.x/256)+14,y:Math.floor(game.state.player.y/256),space:'PLAYER_FEET',contentId:game.state.world.contentId});
pulseHaptic(6);
}
if (r.checkpoint.length) checkpoint(r.checkpoint.join('+'),r.checkpoint.includes('BOSS_CLEAR')||r.checkpoint.includes('CINEMA_COMPLETE'));
return r;
}
function stepShell(){
const frame=input.frame();
if (screen==='ATTRACT'){
if (app.qrCart?.isOpen) return;
if (frame.flapEdge) selectTitle();
}else if (screen==='MANUAL'){
if (frame.flapEdge) closeManual();
}else if (screen==='THEATER'){
stepTheater(frame);
}else if (screen==='CRAWL'){
crawlTicks+=1;
crawlHold=frame.flapHeld?crawlHold+1:0;
if (view.crawlDone||crawlHold>=C.cinemaSkipHoldTicks) startNewGame('CAMPAIGN');
}
}
const reducedMotion=typeof window.matchMedia==='function'?window.matchMedia('(prefers-reduced-motion: reduce)'):{matches:false};
const view={state:null,prev,prevPlayer,alpha:1,renderTick:0,screen,menu,buildId:BUILD_ID,releaseBuild:app.releaseBuild,reducedMotion:reducedMotion.matches};
function render(alpha){
if (app.flags.visualFreeze!=='1') renderTick+=1;
else if (Number.isFinite(Number(app.flags.renderTick))) renderTick=Math.max(0,Number(app.flags.renderTick)|0);
const reelPlay=screen==='THEATER'&&theater&&theater.item.kind==='PLAY'?theater.runner:null;
const s=reelPlay?reelPlay.state:game?game.state:attractState;
view.state=s;view.prev=prev;view.prevPlayer=prevPlayer;view.alpha=alpha;view.renderTick=renderTick;view.screen=screen;view.menu=menu;view.banner=banner;view.reducedMotion=reducedMotion.matches;
syncShellUi();
view.saveWarning=saveWarning;view.gameOverItems=gameOverItems();view.gameOverIndex=gameOverIndex;view.gameOverInfo=gameOverInfo;view.winnerInfo=winnerInfo;view.popups=popups;view.crawlTicks=theater&&theater.item.kind==='CRAWL'?theater.ticks:crawlTicks;view.theater=theater;
selectMusic();
view.musicDrive=music?music.visualState():null;
view.content=reelPlay?arenaContent(A,s):game&&s.sim.shell!=='CINEMA_SKY'&&s.sim.shell!=='ATTRACT'?arenaContent(A,s):null;
view.ascent=view.content?ascentCamera.resolve(s,view.content):null;
view.feel=sampleFeelState(feel,renderTick);
view.lavaWarning=view.content&&view.content.kind!=='BOSS'?lavaWarningNow(A,s,view.content):false;
view.arcade=s.sim.mode==='ARCADE'?parseArcade(s):null;
if (externalHud&&!(game&&game.vs)) externalHud.update(hudModel(A,view));
if (controlsRoot){
const wingLevel=Math.max(0,Math.min(1,s.player.wing/(A.sim_constants.wingMax||64)));
const wingText=wingLevel.toFixed(3);
if (controlsRoot.dataset.wingLevel!==wingText){controlsRoot.dataset.wingLevel=wingText;controlsRoot.style.setProperty('--wing-level',wingText);}
const wingLow=String(wingLevel<=0.2);
if (controlsRoot.dataset.wingLow!==wingLow) controlsRoot.dataset.wingLow=wingLow;
controlsRoot.classList.toggle('is-title',screen==='ATTRACT'&&!game);
document.body.classList.toggle('arena-live',!(screen==='ATTRACT'&&!game)&&screen!=='MANUAL');
}
if (controlDeck) controlDeck.sync();
if (((screen==='ATTRACT'&&!game)||screen==='MANUAL')&&app.flags.renderCovered!=='1'){app.renderSkipped=(app.renderSkipped||0)+1;return;}
buildScene(scene,view);
if (scene.atlasDirty){scene.atlasDirty=false;renderer.markAtlasDirty();}
renderer.setInstances(scene.list);
const covered=(screen==='ATTRACT'&&!game)||screen==='MANUAL';
renderer.setQuality(covered||s.sim.shell==='CINEMA_SKY'||screen==='THEATER'?0:quality);
const drive=view.musicDrive||{};
renderer.frame(renderTick,{
ambientTick:reducedMotion.matches?0:renderTick,
cyan:Math.max(.9,Math.min(2.25,1.02+(drive.high||0)*.72+(drive.beat||0)*.48+(drive.downbeat||0)*.12)),
lava:Math.max(.92,Math.min(2.35,1.02+(drive.low||0)*.62+(drive.downbeat||0)*.66+(view.lavaWarning?.24:0))),
violet:Math.max(.82,Math.min(1.95,.96+(drive.beat||0)*.55+(drive.high||0)*.18)),
impact:Math.max(view.banner&&view.banner.until>renderTick?1:0,view.feel?.impact||0),
beat:Math.max(drive.downbeat||0,drive.beat||0),
motion:!reducedMotion.matches,
bloomBeat:reducedMotion.matches?0:Math.max(drive.downbeat||0,(drive.beat||0)*0.7),
moonPhase:(moonPhase=(moonPhase+MOON_TURN_PER_TICK*(1+(reducedMotion.matches?0:MOON_BEAT_SURGE*Math.max(drive.downbeat||0,drive.beat||0))))%1),
});
}
const attractState=newState('CAMPAIGN',1,C);
let moonPhase=0;
let lastDrawAt=-Infinity;
const MIN_DRAW_MS=1000/60-3;
function loop(now){
const dt=Math.min(250,now-last);last=now;
frameTimes.push(dt);if (frameTimes.length>600) frameTimes.shift();
qualityLadder();
acc+=dt;
let steps=0;
if (sideways&&sideways.matches&&game&&game.state.sim.shell==='PLAY') pause('ROTATE');
pollGamepad();
while (acc>=TICK_MS&&steps<5){acc-=TICK_MS;steps+=1;if (app.flags.freeze==='1') continue;if (game){if (!game.vs) stepGame();}else stepShell();}
if (game&&game.vs){vsFrame();acc=TICK_MS;}
if (steps===5) acc=0;
reviveMusic(now);
if (now-lastDrawAt>=MIN_DRAW_MS||app.flags.fpsCap==='off'){lastDrawAt=now;render(Math.min(1,acc/TICK_MS));}
app.frame=(app.frame||0)+1;
if (!app.stopped) requestAnimationFrame(loop);
}
function qualityLadder(){
if (qualityPinned){app.quality=quality;return;}
if (frameTimes.length<300) return;
const sorted=frameTimes.slice(-300).sort((a,b)=>a-b);const p95=sorted[Math.floor(sorted.length*0.95)];
if (quality===2&&p95>18){qualityCounter++;if (qualityCounter>=300){quality=1;qualityCounter=0;}}
else if (quality===1&&p95>20){qualityCounter++;if (qualityCounter>=300){quality=0;qualityCounter=0;}}
else if (quality<2&&p95<15){qualityCounter++;if (qualityCounter>=(quality===0?900:600)){quality+=1;qualityCounter=0;}}
else qualityCounter=0;
app.quality=quality;
}
function logical(ev){
const r=canvas.getBoundingClientRect();
const lx=Math.floor((ev.clientX-r.left)/r.width*256),ly=Math.floor((ev.clientY-r.top)/r.height*384);
return[lx,ly];
}
canvas.addEventListener('touchstart',(ev)=>{if (ev.cancelable) ev.preventDefault();},{passive:false});
canvas.addEventListener('touchmove',(ev)=>{if (ev.cancelable) ev.preventDefault();},{passive:false});
canvas.addEventListener('pointerdown',(ev)=>{
ev.preventDefault();ensureAudio();
if (controlDeck&&game) return;
const[lx,ly]=logical(ev);
if (input.pointerDown(ev.pointerId,lx,ly)){try{canvas.setPointerCapture(ev.pointerId);}catch{}}
});
window.addEventListener('pointerup',(ev)=>input.pointerUp(ev.pointerId),true);
window.addEventListener('pointercancel',(ev)=>input.pointerCancel(ev.pointerId),true);
canvas.addEventListener('pointerup',(ev)=>{ensureAudio();input.pointerUp(ev.pointerId);});
canvas.addEventListener('pointercancel',(ev)=>{input.pointerCancel(ev.pointerId);});
canvas.addEventListener('lostpointercapture',(ev)=>{input.lostPointerCapture(ev.pointerId);});
window.addEventListener('keydown',(ev)=>{
if (app.qrCart?.isOpen) return;
if (screen==='MANUAL'){
if (!ev.repeat&&ev.code==='Escape'){ev.preventDefault();closeManual();return;}
if (ev.target.closest?.('#manual-screen button')) return;
if (!ev.repeat&&(ev.code==='Enter'||ev.code==='Space')){ev.preventDefault();closeManual();return;}
if (ev.target.closest?.('#manual-screen')||ev.code.startsWith('Arrow')) return;
}
if (document.body.classList.contains('cartridge-open')) return;
if (ev.target.closest?.('#dev-code')){if (ev.key==='Escape'){ev.preventDefault();setLevel('HOME','','DEVELOPMENT');}return;}
if (!ev.repeat&&ev.code==='Escape'&&screen==='ATTRACT'&&!game&&menuLevel!=='HOME'){ev.preventDefault();setLevel('HOME','',menuLevel==='CARTRIDGE'?'CARTRIDGE':menuLevel==='ARCADE'?'ARCADE SCORE ATTACK':menuLevel==='VS'?'VS':'DEVELOPMENT');return;}
if ((ev.code==='Enter'||ev.code==='Space')&&ev.target.closest?.('button')&&!ev.target.closest('#title-actions, #controls')) return;
if (ev.code in{ArrowLeft:1,ArrowRight:1,ArrowDown:1,Space:1,ArrowUp:1,KeyA:1,KeyD:1,KeyW:1,Enter:1,KeyM:1,KeyC:1,Escape:1}) ev.preventDefault();
ensureAudio();
const title=screen==='ATTRACT'&&!game;
if (title&&ev.target.closest?.('#title-actions button')&&(ev.code==='Enter'||ev.code==='Space')){
if (!ev.repeat){menu.index=menu.items.indexOf(ev.target.dataset.titleItem);selectTitle();syncShellUi();}
return;
}
if (title&&!ev.repeat&&(ev.code==='ArrowLeft'||ev.code==='ArrowUp'||ev.code==='KeyA')) moveTitle(-1);
else if (title&&!ev.repeat&&(ev.code==='ArrowRight'||ev.code==='ArrowDown'||ev.code==='KeyD'||ev.code==='KeyM')) moveTitle(1);
else if (title&&!ev.repeat&&ev.code==='KeyC'&&menuLevel==='CARTRIDGE') continueGame();
else if (!ev.repeat&&isGameOver()&&(ev.code==='ArrowLeft'||ev.code==='KeyA'||ev.code==='ArrowUp'||ev.code==='KeyW')) moveGameOver(-1);
else if (!ev.repeat&&isGameOver()&&(ev.code==='ArrowRight'||ev.code==='KeyD'||ev.code==='ArrowDown'||ev.code==='KeyS')) moveGameOver(1);
else if (!ev.repeat&&isGameOver()&&(ev.code==='Space'||ev.code==='Enter')) confirmGameOver();
else if (ev.code==='Escape'&&!ev.repeat&&game&&game.state.sim.shell==='PLAY') pause('KEY');
else if (!ev.repeat&&isPaused()&&(ev.code==='Escape'||KEY_MAP[ev.code])) resume('KEY');
else input.keyDown(ev.code,ev.repeat);
});
window.addEventListener('keyup',(ev)=>input.keyUp(ev.code));
function cleanupControls(){if (controlDeck) controlDeck.cleanup();input.cleanup();if (controlDeck) controlDeck.sync();}
window.addEventListener('blur',()=>{cleanupControls();if (game&&game.state.sim.shell==='PLAY') pause('BLUR');});
window.addEventListener('pagehide',cleanupControls);
const reviveSoon=()=>{musicRetryAt=0;reviveMusic(performance.now(),true);};
window.addEventListener('pageshow',reviveSoon);
window.addEventListener('focus',reviveSoon);
document.addEventListener('visibilitychange',()=>{if (document.visibilityState==='visible') reviveSoon();});
if (musicElement) for (const type of['pause','stalled','emptied','error']) musicElement.addEventListener(type,()=>{app.musicLastEvent=type;musicRetryAt=Math.min(musicRetryAt,performance.now()+400);});
document.addEventListener('visibilitychange',()=>{if (document.visibilityState==='hidden'){cleanupControls();if (game&&game.state.sim.shell==='PLAY') pause('HIDDEN');if (game) checkpoint('HIDDEN');}});
window.addEventListener('gamepaddisconnected',()=>input.gamepadDisconnect());
window.addEventListener('resize',resizeRenderer);
const sideways=window.matchMedia?window.matchMedia('(orientation:landscape) and (max-height:500px) and (pointer:coarse)'):null;
if (sideways) sideways.addEventListener('change',(e)=>{if (e.matches&&game&&game.state.sim.shell==='PLAY') pause('ROTATE');});
function pause(why){
if (!game||game.vs) return;
game.state.sim.shell='PAUSE';
input.setMode('PAUSE');
if (controlDeck) controlDeck.cleanup();
holdMusic(true);
app.paused=why;
}
function resume(why){
if (!game||game.state.sim.shell!=='PAUSE') return false;
game.state.sim.shell='PLAY';
input.setMode('PLAY');
saveWarning=false;
storage.removeItem(KEYS.WARNING);
holdMusic(false);
app.paused=null;
app.resumed=why;
if (controlDeck) controlDeck.sync();
return true;
}
const isPaused=()=>!!game&&game.state.sim.shell==='PAUSE';
const padReader=new GamepadReader();
const NO_PAD=Object.freeze({connected:0,ids:[],left:false,right:false,up:false,down:false,flap:false,start:false});
let pad=NO_PAD;
let padStartSpent=false;
const titleHint=document.getElementById('title-hint');
const TITLE_HINT=titleHint?titleHint.textContent:'';
function syncPadHint(){
const text=pad.connected?'Controller ready: D-pad chooses, any face button selects, Start pauses.':TITLE_HINT;
if (titleHint&&titleHint.textContent!==text) titleHint.textContent=text;
}
function padStart(){
if (game&&game.state.sim.shell==='PLAY'){pause('PAD');return true;}
if (isPaused()){resume('PAD');return true;}
if (isGameOver()){confirmGameOver();return true;}
if (game&&game.state.sim.shell==='WINNER'){toTitle();return true;}
if (screen==='ATTRACT'&&!game){selectTitle();syncShellUi();return true;}
if (screen==='MANUAL'){closeManual();return true;}
return false;
}
function pollGamepad(){
const was=pad;
pad=navigator.getGamepads?padReader.read(navigator.getGamepads()):NO_PAD;
app.pad=pad;
if (!pad.connected){
if (was.connected){input.gamepadDisconnect();syncPadHint();}
padStartSpent=false;
return;
}
if (!was.connected) syncPadHint();
const edge=(k)=>pad[k]&&!was[k];
if (edge('flap')||edge('start')) ensureAudio();
if (screen==='ATTRACT'&&!game){
if (edge('left')||edge('up')) moveTitle(-1);
else if (edge('right')||edge('down')) moveTitle(1);
}else if (screen==='MANUAL'){
if (edge('left')||edge('right')||edge('up')||edge('down')) closeManual();
}else if (isGameOver()){
if (edge('left')||edge('up')) moveGameOver(-1);
else if (edge('right')||edge('down')) moveGameOver(1);
}
let startFlaps=false;
if (!pad.start) padStartSpent=false;
else if (!padStartSpent){
if (edge('start')&&padStart()) padStartSpent=true;
else startFlaps=true;
}
input.gamepad({left:pad.left,right:pad.right,flap:pad.flap||startFlaps});
}
const controlsRoot=document.getElementById('controls');
if (controlsRoot) controlDeck=installSmartControls({
root:controlsRoot,
input,
ensureAudio,
controlEnabled(region){
return input.regionEnabled(region)
||(screen==='ATTRACT'&&!game&&(region==='LEFT_WING'||region==='RIGHT_WING'))
||(isPaused()&&(region==='LEFT_WING'||region==='RIGHT_WING'))
||(isGameOver()&&(region==='LEFT_WING'||region==='RIGHT_WING'));
},
shellActive(){return (screen==='ATTRACT'&&!game)||isPaused()||isGameOver();},
onShellAction(action){
if (isPaused()){if (action==='BOTH') resume('DECK');return;}
if (isGameOver()){
if (action==='BOTH') confirmGameOver();else moveGameOver(action==='PREV'?-1:1);
syncShellUi();
return;
}
if (screen!=='ATTRACT'||game) return;
if (action==='BOTH') selectTitle();else moveTitle(action==='PREV'?-1:1);
syncShellUi();
},
labelFor(region){
if (screen==='ATTRACT'&&!game){
const count=Math.max(1,menu.items.length),i=menu.index;
const both=`; press both wings together to select ${menu.items[i]}`;
if (region==='LEFT_WING') return `Left wing: previous option, ${menu.items[(i-1+count)%count]}${both}`;
if (region==='RIGHT_WING') return `Right wing: next option, ${menu.items[(i+1)%count]}${both}`;
}
if (screen==='CRAWL') return 'Hold either wing to skip story';
if (screen==='THEATER') return 'Hold either wing to leave the cinema';
if (game&&game.state.sim.shell==='CINEMA_SKY') return 'Tap to continue the film; hold to skip it';
if (isPaused()) return 'Paused: press both wings together to resume';
if (isGameOver()) return `${region==='RIGHT_WING'?'Next':'Previous'} option; press both wings together to select ${gameOverItems()[gameOverIndex]}`;
return region==='LEFT_WING'?'Left wing: up-left flap; slide down to DART':'Right wing: up-right flap; slide down to DART';
},
});
if (devForm) devForm.addEventListener('submit',(ev)=>{ev.preventDefault();tryUnlock();});
if (homeButton) homeButton.addEventListener('click',()=>{if (screen==='ATTRACT'&&!game) setLevel('HOME','','CARTRIDGE');});
if (titleActions) titleActions.addEventListener('click',(ev)=>{
const button=ev.target.closest('button[data-title-item]');
if (!button||screen!=='ATTRACT'||game) return;
ensureAudio();
menu.index=menu.items.indexOf(button.dataset.titleItem);
selectTitle();
syncShellUi();
});
if (riderToggle) riderToggle.addEventListener('click',(event)=>{
event.stopPropagation();
if (app.spriteProfile.id!=='CONSOLE_FULL') return;
scene.riderEnabled=!scene.riderEnabled;
app.riderEnabled=scene.riderEnabled;
app.riderSystem.enabled=scene.riderEnabled;
storage.setItem(RIDER_PREF_KEY,scene.riderEnabled?'on':'off');
syncRiderToggle();
});
if (manualClose) manualClose.addEventListener('click',(event)=>{event.stopPropagation();closeManual();});
if (manualRoot) manualRoot.addEventListener('click',(event)=>{
if (screen!=='MANUAL'||event.target.closest?.('button')) return;
closeManual();
});
const updateBtn=document.getElementById('update');
if (updateBtn) updateBtn.addEventListener('click',()=>pwa.acceptUpdate());
return{
A,input,get game(){return game;},view,renderer,storage,
async start(){
resizeRenderer();
input.setMode('ATTRACT');
const r=refreshTitleMenu('',true);
if (r.status==='REJECTED') menu.note='SAVE REJECTED: RESET OR START AGAIN';
if (app.storageBlocked) menu.note='SAVES ARE OFF: THIS BROWSER BLOCKS STORAGE';
if (controlDeck) controlDeck.sync();
requestAnimationFrame(loop);
},
startNewGame,continueGame,checkpoint,toTitle,startTheater,get theater(){return theater;},theaterJump(i){if (theater) enterTheaterItem(i);},pause,resume,ensureAudio,unlimitedContinue,moveGameOver,confirmGameOver,
tickOnce(frame=EMPTY_INPUT){if (game){const r=stepGameWith(frame);return r;}return null;},
refreshWorld(){if (game) onArena();},
worldDigest(){return atlasDigest(atlas);},
sceneStats(){const by={};let area=0;for (const q of scene.list){const k=q.flags||0;const a=Math.abs(q.w*q.h);by[k]=(by[k]||0)+a;area+=a;}return{instances:scene.list.length,overdraw:+(area/(256*384)).toFixed(2),byMaterial:by};},
sceneProbe(){return{ascent:view.ascent?{kind:view.ascent.kind,arcade:!!view.ascent.arcade,cameraTop:view.ascent.cameraTop,baseY:view.ascent.baseY,targetTop:view.ascent.targetTop,backgroundProgress:view.ascent.backgroundProgress,scaleY:view.ascent.scaleY}:null,world:scene.list.filter((q)=>q.flags===MATERIAL_WORLD).map((q)=>({...q})),platforms:scene.list.filter((q)=>q.z>=.76&&q.z<.77&&q.sw>1).map((q)=>({...q}))};},
async readLogical(){return renderer.readLogical();},
async readScene3x(){return renderer.readScene3x();},
setUpdateReadyForTest(){app.updateReady=true;},
stop(){
app.stopped=true;
if (music) music.stop();
if (audioContext&&audioContext.state!=='closed') audioContext.close().catch(()=>{});
},
};
}
return{boot,showFatal};
})();
export const boot=__modules[40].boot;
export const showFatal=__modules[40].showFatal;
export const __sim={get Game(){return __modules[13].Game;},get authority(){return __modules[2];},get content(){return __modules[7];},get state(){return __modules[5];},get ascent(){return __modules[11];},get validate(){return __modules[34].validate;},get checkpoint(){return __modules[35];},get circuit(){return __modules[6];},get step(){return __modules[12];},get vs(){return __modules[41];},get reel(){return __modules[28];},get islands(){return __modules[18];}};
