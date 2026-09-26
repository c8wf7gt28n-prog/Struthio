// STRUTHIO ARCADE · the running game: the fixed-step loop, the title menu,
// pause and game over, saves and the high-score table, music and sound
// effects, touch / keyboard / gamepad input, and rendering each frame.
import{Game}from '../sim/game.mjs';
import{newState,SHIMMER_TICKS}from '../sim/state.mjs';
import{payloadOf,EMPTY_INPUT}from '../sim/step.mjs';
import{towerContent}from '../sim/tower.mjs';
import{Scene,buildScene}from '../render/scene.mjs';
import{TowerCamera}from '../render/camera.mjs';
import{MATERIAL_WORLD}from '../render/renderer.mjs';
import{atlasDigest}from '../render/atlas.mjs';
import{InputNormalizer,KEY_MAP,GamepadReader}from '../input/input.mjs';
import{writeCheckpoint,restoreCheckpoint,KEYS}from '../save/checkpoint.mjs';
import SAVE_SCHEMA from '../save/save-schema.mjs';
import{Conductor,synthConfig}from '../audio/conductor.mjs';
import{createMediaLoopTrack}from '../audio/music.mjs';
import{setupPwa}from '../ui/pwa.mjs';
import{installSmartControls}from '../ui/controls.mjs';
import{createHud,hudModel}from '../ui/hud.mjs';
import{ART,ARCADE_REAR_HORIZON,MOON_TURN_PER_TICK,MOON_BEAT_SURGE,buildArcadeGlobe}from './art.mjs';
import{primeAudioContext,freshFeelState,resetFeelState,triggerFeel,sampleFeelState,pulseHaptic}from './feel.mjs';

export const TICK_MS=1000/60;
const SCORE_POPUP=Object.freeze({EGG:'GOLD',JOUST:'WHITE',RING:'CYAN'});
const BANNER_TICKS=150;
const HIDDEN_SAVE_BUDGET_MS=120;
const GAMEOVER_ITEMS=Object.freeze(['NEW RUN','TITLE']);
const fmtScore=(n)=>Math.max(0,Math.trunc(n||0)).toLocaleString('en-US');

function canAcceptBufferedFlap(s){
if (!s||s.sim.shell!=='PLAY') return true;
return s.player.flapCooldown===0&&s.player.wing>0&&s.player.invulnerableTicks<=SHIMMER_TICKS;
}

export function createSession({R,atlas,art,renderer,canvas,storage,app,base}){
const scene=new Scene(R,atlas);
const camera=new TowerCamera();
const input=new InputNormalizer(R.input);
let game=null;
let screen='TITLE';
let menu={items:['NEW RUN'],index:0,note:''};
let renderTick=0,acc=0,last=performance.now();
let prev=new Map(),prevPlayer=null;
let banner=null,saveWarning=!!storage.getItem(KEYS.WARNING);
let cameraOverride=null;
const popups=[];
let gameOverInfo=null,gameOverIndex=0;
const feel=freshFeelState();

// ---- records ----------------------------------------------------------------
function readRecords(){try{const r=JSON.parse(storage.getItem(KEYS.RECORDS)||'{}');return r&&typeof r==='object'?r:{};}catch{return{};}}
function writeRecords(r){try{storage.setItem(KEYS.RECORDS,JSON.stringify(r));}catch{}}
function recordRun(s){
const recs=readRecords(),prevBest=recs.best||null;
const run={score:s.sim.score,round:s.tower.round,kills:s.tower.kills,deaths:s.run.deaths,build:app.buildId,date:new Date().toISOString().slice(0,10)};
const isNew=!prevBest||run.score>prevBest.score;
if (isNew){recs.best=run;writeRecords(recs);}
return{final:run.score,round:run.round,best:isNew?run:prevBest,isNew};
}
function recordNote(){
const best=readRecords().best;
return best?`HI ${fmtScore(best.score)} · ROUND ${best.round}`:'NO RECORD YET';
}
function savedRun(){
const r=restoreCheckpoint(storage,SAVE_SCHEMA);
const p=r.status==='RESTORE'?r.record.payload:null;
return{...r,active:!!p&&p.sim.shell!=='GAMEOVER',round:p?.tower?.round||1};
}
function checkpoint(reason){
if (!game) return null;
const hidden=document.visibilityState==='hidden';
const r=writeCheckpoint(storage,SAVE_SCHEMA,payloadOf(game.state),{hidden,budgetMs:HIDDEN_SAVE_BUDGET_MS,now:()=>performance.now()});
if (!r.committed) saveWarning=true;
app.lastCheckpoint={reason,...r,tick:game.state.sim.tick};
return r;
}

// ---- music and sound --------------------------------------------------------
const musicElement=document.getElementById('music-track');
const music=musicElement&&app.flags.music!=='off'?createMediaLoopTrack(musicElement,{gain:0.56,bpm:ART.musicBpm,beatsPerBar:R.audio.beatsPerBar}):null;
if (music) music.element.src=new URL(base+ART.music,document.baseURI).href;
let audio=null,audioContext=null,conductor=null,audioStarting=null;
let musicHeld=false,musicWanted=false,musicRetryAt=0,musicFailures=0;
const inGame=()=>!!game&&screen==='GAME';
function startMusicFromGesture(){
if (music) musicWanted=true;
if (!music||musicHeld||!inGame()) return;
if (music.element.paused) music.playing=false;
try{const attempt=music.start();if (attempt&&typeof attempt.catch==='function') attempt.catch((error)=>{app.musicError=String(error);});}
catch (error){app.musicError=String(error);}
}
function wakeAudioContext(context){
const attempt=primeAudioContext(context);
if (attempt&&typeof attempt.catch==='function') attempt.catch((error)=>{app.audioResumeError=String(error);});
}
function ensureAudio(){
startMusicFromGesture();
if (audio){if (!musicHeld) wakeAudioContext(audio.ctx);return Promise.resolve(audio);}
if (audioStarting){if (!musicHeld) wakeAudioContext(audioContext);return audioStarting;}
const AudioContextClass=window.AudioContext||window.webkitAudioContext;
if (!AudioContextClass){app.audio={mode:music?'NATIVE_MP3':'SILENT'};return Promise.resolve(null);}
audioContext=new AudioContextClass({latencyHint:'interactive'});
wakeAudioContext(audioContext);
audioStarting=(async()=>{
const ctx=audioContext;
try{
const master=ctx.createGain(),limiter=ctx.createDynamicsCompressor();
master.gain.value=0.92;
limiter.threshold.value=-12;limiter.knee.value=12;limiter.ratio.value=8;limiter.attack.value=0.003;limiter.release.value=0.25;
master.connect(limiter).connect(ctx.destination);
await ctx.audioWorklet.addModule(base+'src/audio/worklet.mjs');
const node=new AudioWorkletNode(ctx,'struthio-synth',{outputChannelCount:[2]});
const sfxGain=ctx.createGain();sfxGain.gain.value=0.68;
node.connect(sfxGain).connect(master);
node.port.postMessage({type:'init',audio:synthConfig(R.audio)});
conductor=new Conductor(R.audio,{context:ctx,send:(message)=>node.port.postMessage(message)});
audio={ctx,node,master,limiter};
app.audio={mode:music?'NATIVE_MP3+SYNTH':'SYNTH'};
return audio;
}catch (error){
app.audioError=String(error);
if (ctx&&ctx.state!=='closed') await ctx.close().catch(()=>{});
if (audioContext===ctx) audioContext=null;
return null;
}finally{audioStarting=null;}
})();
return audioStarting;
}
function holdMusic(held){
if (musicHeld===held) return;
musicHeld=held;
if (held){if (music) music.stop();}
else{startMusicFromGesture();const ctx=audio?audio.ctx:audioContext;if (ctx) wakeAudioContext(ctx);}
}
function musicShouldPlay(){return!!music&&inGame()&&musicWanted&&!musicHeld&&!app.stopped&&document.visibilityState==='visible';}
function reviveMusic(now=performance.now(),force=false){
if (!musicShouldPlay()) return;
const el=music.element;
if (!el.paused&&!el.ended&&el.readyState>=2){musicFailures=0;return;}
if (!force&&now<musicRetryAt) return;
musicRetryAt=now+1500;
try{
if (el.error||el.networkState===3||musicFailures>=3){el.load();musicFailures=0;}
music.playing=false;
const attempt=music.start();
if (attempt&&typeof attempt.then==='function') attempt.then(()=>{musicFailures=0;},(error)=>{musicFailures+=1;app.musicError=String(error);});
}catch (error){musicFailures+=1;app.musicError=String(error);}
}

// ---- the world art (bird sheet, turning moon, horizon glow) -------------------
let worldReady=false;
function prepareWorld(){
if (worldReady) return;
worldReady=true;
renderer.markAtlasDirty();
renderer.markWorldDirty();
renderer.setBird(art.bird,true);
const globe=app.flags.globe==='off'?null:buildArcadeGlobe(atlas.background.rear);
renderer.setGlobe(globe,globe?globe.params:null);
renderer.setArcadeFx(app.flags.arcadeFx==='off'?null:ARCADE_REAR_HORIZON);
}

// ---- runs -------------------------------------------------------------------
function beginGame(g){
holdMusic(false);
game=g;
camera.reset();
resetFeelState(feel);
gameOverInfo=null;gameOverIndex=0;popups.length=0;banner=null;
app.game=game;
prepareWorld();
screen='GAME';
startMusicFromGesture();
input.setMode('PLAY');
}
function startNewGame(){
const seed=(app.flags.seed>>>0)||(crypto.getRandomValues(new Uint32Array(1))[0]>>>0)||1;
const g=new Game(R,{seed});
g.start();
beginGame(g);
checkpoint('NEW_GAME');
}
function resumeRun(){
const r=savedRun();
if (!r.active){refreshTitleMenu('NO RUN TO RESUME');syncShellUi();return;}
const g=new Game(R,{state:structuredClone(r.record.payload)});
if (r.repairPointer) storage.setItem(KEYS.ACTIVE,r.repairPointer);
if (g.state.sim.shell==='PAUSE') g.state.sim.shell='PLAY';
beginGame(g);
}
function toTitle(){
holdMusic(false);
if (music) music.stop();
musicWanted=false;
game=null;app.game=null;
camera.reset();
resetFeelState(feel);
screen='TITLE';
input.setMode('ATTRACT');
refreshTitleMenu('');
syncShellUi();
}
function moveGameOver(delta){const n=GAMEOVER_ITEMS.length;gameOverIndex=(gameOverIndex+delta+n)%n;if (controlDeck) controlDeck.sync();}
function confirmGameOver(){
const choice=GAMEOVER_ITEMS[gameOverIndex];
gameOverIndex=0;
if (choice==='TITLE'){toTitle();return 'TITLE';}
startNewGame();
return 'NEW_RUN';
}
const isGameOver=()=>!!game&&game.state.sim.shell==='GAMEOVER';
const isPaused=()=>!!game&&game.state.sim.shell==='PAUSE';
function pause(why){
if (!game||game.state.sim.shell!=='PLAY') return;
game.state.sim.shell='PAUSE';
input.setMode('PAUSE');
if (controlDeck) controlDeck.cleanup();
holdMusic(true);
app.paused=why;
}
function resume(why){
if (!isPaused()) return false;
game.state.sim.shell='PLAY';
input.setMode('PLAY');
saveWarning=false;
storage.removeItem(KEYS.WARNING);
holdMusic(false);
app.paused=null;app.resumed=why;
if (controlDeck) controlDeck.sync();
return true;
}

// ---- the tick ---------------------------------------------------------------
function stepGame(){return stepGameWith(input.frame({acceptFlap:canAcceptBufferedFlap(game.state)}));}
function stepGameWith(frame){
const s=game.state;
prev=new Map(s.actors.map((a)=>[a.id,{x:a.x,y:a.y}]));prevPlayer={x:s.player.x,y:s.player.y};
if (s.sim.shell==='PAUSE'){if (frame.flapEdge) resume('FLAP');return null;}
if (s.sim.shell==='GAMEOVER'){if (frame.flapEdge) confirmGameOver();return null;}
const contentBefore=towerContent(s);
const wasGrounded=!!s.player.groundedPlatformId;
const r=game.tick(frame);
if (conductor) conductor.onEvents(r.events);
const st=game.state;
const playerX=Math.floor(st.player.x/256)+14,playerTop=Math.floor(st.player.y/256);
for (const e of r.events){
if (e.type==='EXTRA_LIFE') banner={text:'EXTRA JOUST MARK',until:renderTick+100};
if (e.type==='GOLD_RING_OPEN') banner={text:'6/6 · THE GOLD RING IS AT THE MOON',until:renderTick+BANNER_TICKS};
if (e.type==='ROUND_CLEAR'){
banner={text:`ROUND ${e.round} CLEAR${e.clean?' · NO LOSSES':''}`,until:renderTick+BANNER_TICKS};
pulseHaptic([20,30,40]);
if (music) music.duck({depth:.35,attack:.004,hold:.08,release:.5});
}
if (e.type==='TOWER_BLAST'&&e.amount){
popups.push({text:String(e.amount),tone:'GOLD',x:Math.floor(e.x/256)+14,y:Math.floor(e.y/256)+4,tick:renderTick});
if (popups.length>12) popups.shift();
}
if (e.type==='SCORE_AWARD'&&SCORE_POPUP[e.kind]){
const ring=e.kind==='RING'?contentBefore.rings.find((q)=>q.order===e.order):null;
popups.push({text:String(e.amount),tone:SCORE_POPUP[e.kind],x:ring?ring.center[0]:playerX,y:ring?ring.center[1]-14:playerTop+4,tick:renderTick,big:e.kind==='EGG'&&e.chain>=4});
if (popups.length>12) popups.shift();
}
if (e.type==='PLAYER_DEATH'||e.type==='GAMEOVER') input.cleanup();
if (e.type==='GAMEOVER'){gameOverIndex=0;gameOverInfo=recordRun(st);}
if (e.type==='FLAP') triggerFeel(feel,{kind:'FLAP',tick:renderTick,duration:5,strength:.32,priority:1,x:playerX,y:playerTop,space:'PLAYER_CENTER'});
if (e.type==='RING'){
const ring=e.gold?contentBefore.goldRing:contentBefore.rings.find((q)=>q.id===e.ringId);
triggerFeel(feel,{kind:e.gold?'RING_GREEN':'RING',tick:renderTick,duration:22,strength:.92,priority:3,x:ring?.center[0]??playerX,y:ring?.center[1]??playerTop,space:ring?'WORLD':'PLAYER_CENTER'});
if (music) music.duck({depth:.82,attack:.006,hold:.012,release:.11});
pulseHaptic(8);
}
if (e.type==='JOUST_CLASH'&&(e.a===0||e.b===0)){
triggerFeel(feel,{kind:'CLASH',tick:renderTick,duration:8,shake:5,strength:.9,priority:4,x:playerX,y:playerTop,space:'PLAYER_CENTER'});
if (music) music.duck({depth:.68,attack:.004,hold:.018,release:.14});
pulseHaptic(12);
}
if (e.type==='JOUST_WIN'){
triggerFeel(feel,{kind:'JOUST_WIN',tick:renderTick,duration:14,shake:8,strength:1.35,priority:5,x:playerX,y:playerTop,space:'PLAYER_CENTER'});
if (music) music.duck({depth:.42,attack:.004,hold:.035,release:.24});
pulseHaptic([14,18,22]);
}
if (e.type==='PLAYER_DEATH'){
triggerFeel(feel,{kind:'DEATH',tick:renderTick,duration:18,shake:11,strength:1.45,priority:6,x:Math.floor(prevPlayer.x/256)+14,y:Math.floor(prevPlayer.y/256),space:'PLAYER_CENTER'});
if (music) music.duck({depth:.3,attack:.006,hold:.06,release:.38});
pulseHaptic([26,24,34]);
}
}
if (!wasGrounded&&st.player.groundedPlatformId&&!r.events.some((e)=>e.type==='PLAYER_DEATH')){
triggerFeel(feel,{kind:'LAND',tick:renderTick,duration:7,shake:3,strength:.58,priority:2,x:playerX,y:playerTop,space:'PLAYER_FEET'});
pulseHaptic(6);
}
if (r.checkpoint.length) checkpoint(r.checkpoint.join('+'));
return r;
}
function stepTitle(){
const frame=input.frame();
if (frame.flapEdge) selectTitle();
}

// ---- the title screen -------------------------------------------------------
const titleRoot=document.getElementById('title-screen');
const titleActions=document.getElementById('title-actions');
const titleNote=document.getElementById('title-note');
let renderedMenuItems='';
function refreshTitleMenu(note=menu.note){
const run=savedRun();
// Arcade title: one flashing START. It continues a run left mid-climb, else starts a new one.
menu={items:['START'],index:0,resume:run.active,note:note||(run.status==='REJECTED'?'SAVED RUN COULD NOT BE READ':run.active?`CONTINUE · ROUND ${run.round||1}`:recordNote())};
if (controlDeck) controlDeck.sync();
}
function moveTitle(delta){
if (!menu.items.length) return;
menu.index=(menu.index+delta+menu.items.length)%menu.items.length;
if (controlDeck) controlDeck.sync();
syncShellUi();
if (titleRoot&&!titleRoot.hidden) titleActions?.children[menu.index]?.focus({preventScroll:true});
}
function selectTitle(){
if (menu.resume) resumeRun();else startNewGame();
}
function syncShellUi(){
const titleVisible=screen==='TITLE';
if (titleRoot&&titleRoot.hidden===titleVisible) titleRoot.hidden=!titleVisible;
if (!titleActions) return;
const key=menu.items.join('|');
if (key!==renderedMenuItems){
titleActions.replaceChildren(...menu.items.map((item,i)=>{
const button=document.createElement('button');
button.type='button';button.dataset.titleItem=item;
button.className=i===0?'is-primary':'';
button.textContent=item;
return button;
}));
titleActions.classList.toggle('has-two',menu.items.length===2);
renderedMenuItems=key;
}
for (const button of titleActions.children){
const current=String(button.dataset.titleItem===menu.items[menu.index]);
if (button.getAttribute('aria-current')!==current) button.setAttribute('aria-current',current);
}
const note=saveWarning?'SAVE NOT UPDATED':app.updateReady?'UPDATE READY · RELOAD TO PLAY IT':app.storageBlocked?'SAVES ARE OFF: THIS BROWSER BLOCKS STORAGE':(pwa.offlineNote||menu.note);
if (titleNote&&titleNote.textContent!==note) titleNote.textContent=note;
}

// ---- rendering --------------------------------------------------------------
const hudRoot=document.getElementById('top-hud');
const hud=hudRoot?createHud(hudRoot,{toastRoot:document.getElementById('hud-toast'),srRoot:document.getElementById('hud-sr')}):null;
const controlsRoot=document.getElementById('controls');
const cabinet=document.getElementById('cabinet');
const reducedMotion=typeof window.matchMedia==='function'?window.matchMedia('(prefers-reduced-motion: reduce)'):{matches:false};
const view={state:null,prev,prevPlayer,alpha:1,renderTick:0,screen,buildId:app.buildId};
const titleState=newState(1,R);
let moonPhase=0;
const seededQuality=Number(app.flags.quality);
const qualityPinned=Number.isInteger(seededQuality)&&seededQuality>=0&&seededQuality<=2;
const frameTimes=[];let quality=qualityPinned?seededQuality:2,qualityCounter=0;
function render(alpha){
renderTick+=1;
const s=game?game.state:titleState;
Object.assign(view,{state:s,prev,prevPlayer,alpha,renderTick,screen,banner,saveWarning,popups,gameOverItems:GAMEOVER_ITEMS,gameOverIndex,gameOverInfo,reducedMotion:reducedMotion.matches});
syncShellUi();
view.musicDrive=music?music.visualState():null;
view.content=game?towerContent(s):null;
view.ascent=game?camera.resolve(s):null;
if (cameraOverride!==null&&view.ascent){const b=view.ascent.bounds,top=cameraOverride;view.ascent={...view.ascent,cameraTop:top,backgroundProgress:Math.max(0,Math.min(1,(b.bottom-top)/(b.bottom-b.top)))};}
view.feel=sampleFeelState(feel,renderTick);
if (hud) hud.update(hudModel(view));
if (controlsRoot){
const wingLevel=Math.max(0,Math.min(1,s.player.wing/(R.sim.wingMax||64)));
const wingText=wingLevel.toFixed(3);
if (controlsRoot.dataset.wingLevel!==wingText){controlsRoot.dataset.wingLevel=wingText;controlsRoot.style.setProperty('--wing-level',wingText);}
const wingLow=String(!!game&&wingLevel<=0.2);
if (controlsRoot.dataset.wingLow!==wingLow) controlsRoot.dataset.wingLow=wingLow;
controlsRoot.classList.toggle('is-title',screen==='TITLE');
document.body.classList.toggle('arena-live',screen==='GAME');
}
if (controlDeck) controlDeck.sync();
if (screen==='TITLE'){app.renderSkipped=(app.renderSkipped||0)+1;return;}
buildScene(scene,view);
if (scene.atlasDirty){scene.atlasDirty=false;renderer.markAtlasDirty();}
renderer.setInstances(scene.list);
renderer.setQuality(quality);
const drive=view.musicDrive||{};
const beat=Math.max(drive.downbeat||0,drive.beat||0);
renderer.frame(renderTick,{
ambientTick:reducedMotion.matches?0:renderTick,
cyan:Math.max(.9,Math.min(2.25,1.02+(drive.high||0)*.72+(drive.beat||0)*.48+(drive.downbeat||0)*.12)),
lava:Math.max(.92,Math.min(2.35,1.02+(drive.low||0)*.62+(drive.downbeat||0)*.66)),
violet:Math.max(.82,Math.min(1.95,.96+(drive.beat||0)*.55+(drive.high||0)*.18)),
impact:Math.max(view.banner&&view.banner.until>renderTick?1:0,view.feel?.impact||0),
beat,
motion:!reducedMotion.matches,
bloomBeat:reducedMotion.matches?0:Math.max(drive.downbeat||0,(drive.beat||0)*0.7),
moonPhase:(moonPhase=(moonPhase+MOON_TURN_PER_TICK*(1+(reducedMotion.matches?0:MOON_BEAT_SURGE*beat)))%1),
});
}
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
while (acc>=TICK_MS&&steps<5){acc-=TICK_MS;steps+=1;if (app.flags.freeze==='1') continue;if (game) stepGame();else stepTitle();}
if (steps===5) acc=0;
reviveMusic(now);
if (now-lastDrawAt>=MIN_DRAW_MS){lastDrawAt=now;render(Math.min(1,acc/TICK_MS));}
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
function resizeRenderer(){
const b=cabinet?cabinet.getBoundingClientRect():{width:window.innerWidth,height:window.innerHeight};
renderer.resize(Math.max(256,b.width),Math.max(384,b.height));
}
// The side rails' lines run exactly beside the game picture.
function syncGameBox(){
const r=canvas.getBoundingClientRect(),root=document.documentElement.style;
root.setProperty('--game-top',`${Math.round(r.top)}px`);
root.setProperty('--game-h',`${Math.round(r.height)}px`);
}
if (typeof ResizeObserver==='function') new ResizeObserver(syncGameBox).observe(canvas);
window.addEventListener('resize',()=>requestAnimationFrame(syncGameBox));

// ---- input ------------------------------------------------------------------
function logical(ev){
const r=canvas.getBoundingClientRect();
return[Math.floor((ev.clientX-r.left)/r.width*256),Math.floor((ev.clientY-r.top)/r.height*384)];
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
if ((ev.code==='Enter'||ev.code==='Space')&&ev.target.closest?.('button')&&!ev.target.closest('#title-actions, #controls')) return;
if (ev.code in{ArrowLeft:1,ArrowRight:1,ArrowDown:1,Space:1,ArrowUp:1,KeyA:1,KeyD:1,KeyW:1,Enter:1,Escape:1}) ev.preventDefault();
ensureAudio();
const title=screen==='TITLE';
if (title&&ev.target.closest?.('#title-actions button')&&(ev.code==='Enter'||ev.code==='Space')){
if (!ev.repeat){menu.index=menu.items.indexOf(ev.target.dataset.titleItem);selectTitle();syncShellUi();}
return;
}
if (title&&!ev.repeat&&(ev.code==='ArrowLeft'||ev.code==='ArrowUp'||ev.code==='KeyA')) moveTitle(-1);
else if (title&&!ev.repeat&&(ev.code==='ArrowRight'||ev.code==='ArrowDown'||ev.code==='KeyD')) moveTitle(1);
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
if (musicElement) for (const type of['pause','stalled','emptied','error']) musicElement.addEventListener(type,()=>{musicRetryAt=Math.min(musicRetryAt,performance.now()+400);});
document.addEventListener('visibilitychange',()=>{
if (document.visibilityState==='visible'){reviveSoon();return;}
cleanupControls();
if (game&&game.state.sim.shell==='PLAY') pause('HIDDEN');
if (game) checkpoint('HIDDEN');
});
window.addEventListener('gamepaddisconnected',()=>input.gamepadDisconnect());
window.addEventListener('resize',resizeRenderer);
const sideways=window.matchMedia?window.matchMedia('(orientation:landscape) and (max-height:500px) and (pointer:coarse)'):null;
if (sideways) sideways.addEventListener('change',(e)=>{if (e.matches&&game&&game.state.sim.shell==='PLAY') pause('ROTATE');});
const padReader=new GamepadReader();
const NO_PAD=Object.freeze({connected:0,ids:[],left:false,right:false,up:false,down:false,flap:false,start:false});
let pad=NO_PAD,padStartSpent=false;
function padStart(){
if (game&&game.state.sim.shell==='PLAY'){pause('PAD');return true;}
if (isPaused()){resume('PAD');return true;}
if (isGameOver()){confirmGameOver();return true;}
if (screen==='TITLE'){selectTitle();syncShellUi();return true;}
return false;
}
function pollGamepad(){
const was=pad;
pad=navigator.getGamepads?padReader.read(navigator.getGamepads()):NO_PAD;
if (!pad.connected){if (was.connected) input.gamepadDisconnect();padStartSpent=false;return;}
const edge=(k)=>pad[k]&&!was[k];
if (edge('flap')||edge('start')) ensureAudio();
if (screen==='TITLE'){
if (edge('left')||edge('up')) moveTitle(-1);
else if (edge('right')||edge('down')) moveTitle(1);
}else if (isGameOver()){
if (edge('left')||edge('up')) moveGameOver(-1);
else if (edge('right')||edge('down')) moveGameOver(1);
}
let startFlaps=false;
if (!pad.start) padStartSpent=false;
else if (!padStartSpent){if (edge('start')&&padStart()) padStartSpent=true;else startFlaps=true;}
input.gamepad({left:pad.left,right:pad.right,flap:pad.flap||startFlaps});
}
const pwa=setupPwa({base,onUpdateReady:()=>{app.updateReady=true;},onOffline:(msg)=>{menu.note=msg;}});
let controlDeck=null;
if (controlsRoot) controlDeck=installSmartControls({
root:controlsRoot,input,ensureAudio,
controlEnabled(region){
return input.regionEnabled(region)||((screen==='TITLE'||isPaused()||isGameOver())&&(region==='LEFT_WING'||region==='RIGHT_WING'));
},
shellActive(){return screen==='TITLE'||isPaused()||isGameOver();},
onShellAction(action){
if (isPaused()){if (action==='BOTH') resume('DECK');return;}
if (isGameOver()){if (action==='BOTH') confirmGameOver();else moveGameOver(action==='PREV'?-1:1);syncShellUi();return;}
if (screen!=='TITLE') return;
selectTitle();
syncShellUi();
},
labelFor(region){
if (screen==='TITLE') return 'Start';
if (isPaused()) return 'Paused: press both wings together to resume';
if (isGameOver()) return `${region==='RIGHT_WING'?'Next':'Previous'} option; press both wings together to select ${GAMEOVER_ITEMS[gameOverIndex]}`;
return region==='LEFT_WING'?'Left wing: up-left flap; slide down to DART':'Right wing: up-right flap; slide down to DART';
},
});
// Arcade title: a tap anywhere on the title screen starts.
if (titleRoot) titleRoot.addEventListener('click',(ev)=>{
if (screen!=='TITLE'||ev.target.closest('#title-actions')) return;
ensureAudio();selectTitle();syncShellUi();
});
if (titleActions) titleActions.addEventListener('click',(ev)=>{
const button=ev.target.closest('button[data-title-item]');
if (!button||screen!=='TITLE') return;
ensureAudio();
menu.index=menu.items.indexOf(button.dataset.titleItem);
selectTitle();
syncShellUi();
});
const updateBtn=document.getElementById('update');
if (updateBtn) updateBtn.addEventListener('click',()=>pwa.acceptUpdate());

const api={
get game(){return game;},get updateReady(){return!!app.updateReady;},view,
start(){
resizeRenderer();
input.setMode('ATTRACT');
refreshTitleMenu('');
syncShellUi();
requestAnimationFrame(loop);
},
startNewGame,resumeRun,toTitle,pause,resume,checkpoint,moveGameOver,confirmGameOver,
stop(){app.stopped=true;if (music) music.stop();if (audioContext&&audioContext.state!=='closed') audioContext.close().catch(()=>{});},
};
// Test hooks: only on a local development server (never on a published host).
if (app.local) Object.assign(api,{
renderer,storage,
tickOnce(frame=EMPTY_INPUT){return game?stepGameWith(frame):null;},
worldDigest(){return atlasDigest(atlas);},
sceneStats(){const by={};let area=0;for (const q of scene.list){const k=q.flags||0;const a=Math.abs(q.w*q.h);by[k]=(by[k]||0)+a;area+=a;}return{instances:scene.list.length,overdraw:+(area/(256*384)).toFixed(2),byMaterial:by,world:scene.list.filter((q)=>q.flags===MATERIAL_WORLD).length};},
setCameraOverrideForTest(top){cameraOverride=Number.isFinite(top)?Math.round(top):null;},
});
return api;
}
