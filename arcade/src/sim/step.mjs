// STRUTHIO ARCADE · one 60 Hz tick: input, physics, jousts, eggs, arrivals,
// rings, the gold ring and round changes. Pure and deterministic: the same
// state and inputs always produce the same next state.
import{digest}from '../core/canonical.mjs';
import{nextU32}from '../core/rng.mjs';
import{px,mod,wrappedDelta}from '../core/fixed.mjs';
import{integrate,inRing,boxesOverlap,standingPlatform}from './physics.mjs';
import{rivalIntent}from './ai.mjs';
import{stepWorld,activateTower}from './world.mjs';
import * as T from './tower.mjs';
import{entityBox,BIRD_BOX,RIDER_BOX,EGG_BOX,LANCE_Y_SUB,FLAP_COOLDOWN_TICKS,RESPAWN_HIDDEN_TICKS,SHIMMER_TICKS,emptyPlayer,emptyTower}from './state.mjs';

export const EMPTY_INPUT=Object.freeze({left:false,right:false,flapEdge:false,flapHeld:false});
const LIVE=['SPAWNING','MOUNTED','REMOUNTING','HATCHING'];

function playerActive(s){return s.player.invulnerableTicks<=SHIMMER_TICKS;}
function actorBox(a){return entityBox(a.x,a.y,a.kind==='RIDER'?RIDER_BOX:a.kind==='EGG'?EGG_BOX:BIRD_BOX);}
function bitCount(mask){let n=mask>>>0,c=0;while (n){c+=n&1;n>>>=1;}return c;}

// The tower's ceiling is the moon; every other constant is the rulebook's.
const PHYSICS=new WeakMap();
function physicsOf(R){
let c=PHYSICS.get(R);
if (!c){c=Object.freeze({...R.sim,playTop:T.TOWER_PLAY_TOP});PHYSICS.set(R,c);}
return c;
}

function addScore(s,R,amount,events,kind='OTHER',extra=null){
const value=Math.max(0,Math.trunc(amount));
if (!value) return 0;
s.sim.score+=value;
events.push({type:'SCORE_AWARD',kind,amount:value,...(extra||{})});
const S=R.scoring;
while (s.sim.score>=(s.run.lifeBands===0?S.firstLife:S.lifeEvery*s.run.lifeBands)){
s.run.lifeBands+=1;
if (s.sim.lives<S.maxLives){s.sim.lives+=1;events.push({type:'EXTRA_LIFE',lives:s.sim.lives});}
}
return value;
}
function joustValue(S,actor){
const base=S.joustClassBase[actor.class]??S.joustClassBase.BOUNDER;
return base+S.joustTierStep*(Math.max(1,actor.tier|0)-1);
}
function eggValue(S,chain){return S.eggChain[Math.min(chain,S.eggChain.length-1)];}

function playerDeath(s,events,content,cause){
events.push({type:'PLAYER_DEATH',cause});
s.run.deaths+=1;s.run.eggChain=0;s.run.clean=false;
// Quiet assist (after Nintendo's Super Guide / Invincibility Leaf): deaths since
// the last ring are counted; from the third, one fewer rival is in play until
// the next ring.
s.tower.mercy=Math.min(9,(s.tower.mercy|0)+1);
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
for (const a of s.actors){
if (a.lifecycle==='MOUNTED'){if (a.timer<1200) a.timer+=1;}
else if (a.timer>0) a.timer-=1;
}
}

export function humanIntent(C,p,active,input,events){
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
function aiIntents(R,s){
const intents=new Map();
for (const a of s.actors){
if (a.lifecycle!=='MOUNTED') continue;
const corner=[a.x<128*256?24:232,Math.floor(s.player.y/256)-70];
intents.set(a.id,rivalIntent(R,s,a,a.class,corner,playerActive(s),s.player.y-40*256));
}
return intents;
}
// Head corner correction (as in Celeste): clipping an island's underside by up
// to 4 px slides the player round the edge instead of bonking.
const CORNER_CORRECT_PX=4;
export function integrateHuman(C,p,pIntent,world,dartTargets,events){
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
const r=integrate(p,BIRD_BOX,pIntent.ax,C,world,{grounded:wasGrounded,cornerPx:CORNER_CORRECT_PX});
if (r.landed){
p.footingTicks+=1;
if (p.footingTicks>=C.wingRechargeArmTicks&&(p.footingTicks-C.wingRechargeArmTicks)%C.wingRechargeIntervalTicks===0&&p.wing<C.wingMax) p.wing+=1;
}else p.footingTicks=0;
if (r.lava){
if (p.lavaPhase==='SAFE'){p.lavaPhase='SINK';p.lavaTicks=C.lavaRescueWindowTicks;events.push({type:'LAVA_CONTACT'});}
}else if (p.lavaPhase==='RESCUED') p.lavaPhase='SAFE';
return null;
}
function integrateAll(R,s,content,pIntent,intents,events){
const C=physicsOf(R),p=s.player;
const previousWorld={platforms:s.world.platforms.map((platform)=>({...platform,rect:platform.rect.slice()})),lavaY:s.world.lavaY};
const actorFooting=new Map();
for (const actor of s.actors){
const box=actor.lifecycle==='MOUNTED'?BIRD_BOX:actor.lifecycle==='DISMOUNTED'?RIDER_BOX:actor.lifecycle==='EGG'?EGG_BOX:null;
if (box) actorFooting.set(actor.id,standingPlatform(actor.x,actor.y,box,previousWorld));
}
stepWorld(s,content);
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
if (sink){if (sink==='SINK_DEATH') playerDeath(s,events,content,'LAVA');return;}
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
}
function joustStage(R,s,content,events){
const C=R.sim,S=R.scoring,p=s.player;
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
if (result==='CLASH'){bounce();events.push({type:'JOUST_CLASH',a:0,b:bId});}
else if (result==='RIVAL_LOSES'){
losers.add(bId);
events.push({type:'JOUST_WIN',rival:bId,cls:eb.class});
if (!eb.joustAwarded) addScore(s,R,joustValue(S,eb),events,'JOUST',{cls:eb.class,tier:eb.tier});
eb.joustAwarded=true;
s._lifecycle.push({id:bId,to:'DISMOUNTED',why:'JOUST'});
bounce();
}else{
losers.add(0);
playerDeath(s,events,content,'JOUST');
return;
}
}
if (!s._deathThisTick) for (const a of s.actors){
if (a.lifecycle==='EGG'&&boxesOverlap(entityBox(p.x,p.y,BIRD_BOX),actorBox(a))){
s._lifecycle.push({id:a.id,to:'REMOVED',why:'EGG_COLLECTED'});
events.push({type:'EGG',actor:a.id,chain:s.run.eggChain+1});
addScore(s,R,eggValue(S,s.run.eggChain),events,'EGG',{chain:s.run.eggChain+1});
s.run.eggChain+=1;
}
}
}
function lifecycleStage(R,s,content,events){
const L=R.lifecycle;
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
else if (req.to==='EGG'){a.lifecycle='EGG';a.kind='EGG';a.timer=content.rules.eggTicks;a.vx=0;}
else if (req.to==='REMOVED'){a.lifecycle='REMOVED';}
}
s._lifecycle=[];
s.actors=s.actors.filter((a)=>a.lifecycle!=='REMOVED');
arrivals(s,content,events);
}

// ---- the tower ---------------------------------------------------------------
function towerPre(R,s,input,events){
const t=s.tower;
if (t.hold>0){                                  // gold ring taken: hold at the moon
s._locked=true;
t.hold-=1;
if (t.hold===0) nextRound(R,s,events);
return;
}
// Rivals start flying in once the player first moves in a round.
if (!t.go&&playerActive(s)&&(input.flapEdge||input.left||input.right||input.dartEdge)){
t.go=true;
t.cooldown=T.TOWER_FIRST_ARRIVAL;
events.push({type:'TOWER_GO',round:t.round});
}
}
function nextRound(R,s,events){
const next=emptyTower(s.tower.round+1);
next.kills=s.tower.kills;
s.tower=next;
const[x,y]=T.towerSpawnFor(0);
s.player=emptyPlayer(x,y);
s.player.wing=R.sim.wingMax;
s.player.invulnerableTicks=RESPAWN_HIDDEN_TICKS+T.ROUND_SWEEP_TICKS+SHIMMER_TICKS;
s.actors=[];
s.run.clean=true;s.run.eggChain=0;
events.push({type:'ROUND_START',round:next.round});
events.push({type:'CHECKPOINT_REQUEST',reason:'ROUND_START'});
}
// An arrival point more than a screen (plus a sprite) above or below the
// player, so a rival never appears on screen: it flies in.
function arrivalPoint(s){
const p=s.player,py=Math.floor(p.y/256);
const box={state:s.rng.gameplayState};
const draw=()=>nextU32(box);
const[near,far]=T.TOWER_ARRIVAL;
const floor=T.TOWER_GROUND-30;
const up=py-far>=T.TOWER_PLAY_TOP,down=py+far<=floor;
if (!up&&!down){s.rng.gameplayState=box.state;return null;}
const fromAbove=up&&(!down||(draw()&1)===0);
const dist=near+(draw()%(far-near+1));
const y=fromAbove?py-dist:py+dist;
let x=-1;
for (let tries=0;tries<6&&x<0;tries++){
const cx=draw()&255;
const b=entityBox(px(cx),px(y),BIRD_BOX);
const blocked=s.world.platforms.some((q)=>{
if (!q.collidable) return false;
const top=(q.rect[1]-6)*256,bottom=(q.rect[1]+q.rect[3]+6)*256;
if (b.b<=top||b.t>=bottom) return false;
for (const sh of[0,-65536,65536]) if (b.l+sh<(q.rect[0]+q.rect[2])*256&&b.r+sh>q.rect[0]*256) return true;
return false;
});
if (!blocked) x=cx;
}
const pick=draw();
s.rng.gameplayState=box.state;
if (x<0) return null;
return{x,y,fromAbove,pick};
}
// The nearby zone: anything more than TOWER_DESPAWN px from the player is
// quietly retired; arrivals top the zone back up to the round's cap. Eggs and
// fallen riders count toward the cap, so a beaten rival returns by hatching
// or, once its egg is collected, as a fresh arrival after the delay.
function arrivals(s,content,events){
const t=s.tower,RR=content.rules,p=s.player;
let dropped=0;
s.actors=s.actors.filter((a)=>{
if (Math.abs(a.y-p.y)<=T.TOWER_DESPAWN*256) return true;
if (LIVE.includes(a.lifecycle)) dropped+=1;
events.push({type:'DESPAWN',actor:a.id});
return false;
});
if (dropped) t.cooldown=Math.max(t.cooldown,RR.fillGap);
if (!t.go||t.hold>0||s._locked||!playerActive(s)) return;
if (t.cooldown>0){t.cooldown-=1;return;}
if (s.actors.length>=Math.max(2,RR.cap-((t.mercy|0)>=3?1:0))) return;
const spot=arrivalPoint(s);
if (!spot){t.cooldown=12;return;}
const cls=T.towerClassFor(spot.y,RR,spot.pick);                  // higher is harder
const tier=Math.min(5,RR.tierBase+(T.towerBand(spot.y)===2?1:0));
const id=s.sim.nextActorId;
s.sim.nextActorId+=1;
s.actors.push({id,kind:'RIVAL',class:cls,ghost:T.GHOSTS[mod(id,4)],tier,lifecycle:'MOUNTED',x:px(spot.x),y:px(spot.y),
vx:0,vy:spot.fromAbove?192:-320,facing:spot.x<128?1:-1,phase:0,timer:0,rngDraws:0,joustAwarded:false});
t.cooldown=RR.fillGap;
events.push({type:'SPAWN',actor:id,cls,ghost:T.GHOSTS[mod(id,4)],fromAbove:spot.fromAbove});
}
// Six rings in any order; then the gold ring at the moon destroys every rival
// and clears the round.
// Rings are caught 2 px beyond their drawn radius: a graze counts.
const RING_SLACK_PX=2;
function rings(R,s,content,events){
const t=s.tower,p=s.player,S=R.scoring;
if (!playerActive(s)||s._locked||s._deathThisTick||t.hold>0) return;
const pb=entityBox(p.x,p.y,BIRD_BOX);
for (const ring of content.rings){
const bit=1<<(ring.order-1);
if ((t.ringMask&bit)||!inRing(pb,ring,RING_SLACK_PX)) continue;
t.ringMask|=bit;
t.mercy=0;
const count=bitCount(t.ringMask&63);
addScore(s,R,S.ring,events,'RING',{order:ring.order});
events.push({type:'RING',ringId:ring.id,order:ring.order,count,total:content.rings.length});
if (count===content.rings.length) events.push({type:'GOLD_RING_OPEN',round:t.round});
}
if ((t.ringMask&63)!==63||!inRing(pb,content.goldRing,RING_SLACK_PX)) return;
let blasted=0;
for (const a of s.actors){
const armed=LIVE.includes(a.lifecycle);
let amount=0;
if (armed){blasted+=1;amount=addScore(s,R,joustValue(S,a),events,'BLAST',{cls:a.class});}
events.push({type:'TOWER_BLAST',actor:a.id,x:a.x,y:a.y,armed,amount});
}
t.kills+=blasted;
s.actors=[];
t.ringMask|=64;
events.push({type:'RING',ringId:content.goldRing.id,order:7,gold:true,count:6,total:6});
const clean=!!s.run.clean;
if (clean) addScore(s,R,S.survival,events,'SURVIVAL');
addScore(s,R,content.rules.clearBonus,events,'ROUND_CLEAR',{round:t.round});
events.push({type:'ROUND_CLEAR',round:t.round,blasted,clean});
t.hold=T.ROUND_CLEAR_HOLD;
events.push({type:'CHECKPOINT_REQUEST',reason:'ROUND_CLEAR'});
}
// Kills and the respawn island (the last still island stood on).
function towerPost(s,content,events){
const t=s.tower,p=s.player;
const wins=events.filter((e)=>e.type==='JOUST_WIN').length;
if (wins){t.kills+=wins;t.cooldown=Math.max(t.cooldown,content.rules.replaceDelay);}
if (playerActive(s)&&!s._deathThisTick&&p.groundedPlatformId){
const idx=T.PLATFORM_INDEX.get(p.groundedPlatformId);
const plat=T.TOWER_PLATFORMS[idx];
if (plat&&plat.motion==='STATIC'&&idx!==t.check){t.check=idx;events.push({type:'TOWER_CHECK',island:plat.id});}
}
}
function transitions(s,events){
if (s._pendingGameOver){s.sim.shell='GAMEOVER';events.push({type:'GAMEOVER'});events.push({type:'CHECKPOINT_REQUEST',reason:'GAMEOVER'});return;}
if (s._deathThisTick){events.push({type:'RESPAWN_SCHEDULED'});events.push({type:'CHECKPOINT_REQUEST',reason:'DEATH'});}
}

export function stepTick(R,s,input=EMPTY_INPUT){
const events=[];
s._lifecycle=[];s._locked=false;s._deathThisTick=false;s._pendingGameOver=false;
if (s.sim.shell!=='PLAY') return finish(s,events);
const content=T.towerContent(s);
towerPre(R,s,input,events);
stageTimers(s);
const pIntent=humanIntent(R.sim,s.player,playerActive(s)&&!s._locked,input,events);
const intents=aiIntents(R,s);
integrateAll(R,s,content,pIntent,intents,events);
joustStage(R,s,content,events);
lifecycleStage(R,s,content,events);
rings(R,s,content,events);
towerPost(s,content,events);
transitions(s,events);
return finish(s,events);
}
function finish(s,events){
const committed=events.map((e)=>({...e,serial:++s.sim.eventSerial}));
const checkpoint=committed.filter((e)=>e.type==='CHECKPOINT_REQUEST').map((e)=>e.reason);
s.sim.tick+=1;
for (const k of Object.keys(s)) if (k.startsWith('_')) delete s[k];
return{events:committed,checkpoint,digest:digest({state:s,events:committed})};
}
export function payloadOf(s){
const copy=structuredClone(s);
for (const k of Object.keys(copy)) if (k.startsWith('_')) delete copy[k];
return copy;
}
export function startRun(s,events=[]){
s.sim.shell='PLAY';
activateTower(s,T.towerContent(s),events);
return events;
}
