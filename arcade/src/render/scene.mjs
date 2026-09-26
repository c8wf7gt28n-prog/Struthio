// STRUTHIO ARCADE · builds the instance list for one frame: the two scrolling
// Arcade plates, islands, rings, rivals, eggs, the player, effects, popups and
// the in-world text (ROUND cards, READY, PAUSED, GAME OVER).
import{buildIslandLayout,bakeIslandLayout,islandGeometry}from './islands.mjs';
import{REGION,SPRITE_CELL_PX,SPRITE_FRAME_COUNT,SPRITE_DRAW_OFFSET,spriteSourceOrigin,SPRITE_IDLE,idleSourceOrigin}from './atlas.mjs';
import{WORLD_SCALE,WORLD_PLATE_W,MATERIAL_WORLD,MATERIAL_ARCADE_ISLAND,MATERIAL_ARCADE_PLAYER}from './renderer.mjs';
import{floorDiv,wrappedDelta}from '../core/fixed.mjs';
import{BirdAnimation}from './bird-animation.mjs';
import{SHIMMER_TICKS,FLAP_COOLDOWN_TICKS,BIRD_BOX}from '../sim/state.mjs';
import{decodePhase,CLASS_FLAP_PERIOD}from '../sim/ai.mjs';
import{towerContent}from '../sim/tower.mjs';
import{eggSource,shimmerSource,EGG_FRAMES,EGG_CELL,SHIMMER_CELL}from './props.mjs';
import{standingPlatform,overlapsX}from '../sim/physics.mjs';
import{emitLiveRing,emitRingBurst,ringKindFor}from './ring-fx.mjs';
import{towerProfile,withCamera,projectY,projectAnchoredY}from './camera.mjs';
const Z=Object.freeze({BG:0.95,WORLD:0.9,GEOLOGY:0.84,PLATFORM:0.76,RING:0.68,EGG:0.6,ACTOR:0.5,PLAYER:0.4,HUD:0.2,OVERLAY:0.1,TOP:0.05});
const CLASS_ROW=Object.freeze({PLAYER:0,BOUNDER:1,HUNTER:2,SHADOW:3});
const MODERN_TONE=Object.freeze({WHITE:0,CYAN:1,LAVA:2,GOLD:3,DIM:4});
class Scene{
constructor(R,atlas){
this.R=R;
this.atlas=atlas;
this.fontChars=Object.keys(R.font_5x7).sort();
this.fontIndex=new Map(this.fontChars.map((c,i)=>[c,i]));
this.list=[];
this.birdMotion=new BirdAnimation();
this.verticalAscent=true;
this.playerMaterial=MATERIAL_ARCADE_PLAYER;
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
this.add(0,0,256,384,0,snap(rest*384),256*S,384*S,Z.WORLD+0.02,MATERIAL_WORLD);
this.add(0,0,256,384,WORLD_PLATE_W,snap(rest*512),256*S,256*S,Z.WORLD,MATERIAL_WORLD);
}
sprite(row,frame,x,y,facing,z,flags=0){
const resolved=((frame%SPRITE_FRAME_COUNT)+SPRITE_FRAME_COUNT)%SPRITE_FRAME_COUNT;
const[sx,sy]=frame===SPRITE_IDLE?idleSourceOrigin(row):spriteSourceOrigin(REGION.SPRITES,row,resolved);
const material=flags||2+row;
if (facing<0) this.add(x,y,32,32,sx+SPRITE_CELL_PX,sy,-SPRITE_CELL_PX,SPRITE_CELL_PX,z,material);
else this.add(x,y,32,32,sx,sy,SPRITE_CELL_PX,SPRITE_CELL_PX,z,material);
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
scene.reset();
if (!view.state||view.state.sim.shell==='ATTRACT') return scene.list;
return buildWorldScene(scene,view);
}
function buildWorldScene(scene,view){
const s=view.state;
const alpha=view.alpha??1;
const content=view.content||towerContent(s);
const ascent=view.ascent||withCamera(towerProfile(s,content));
const worldView=ascent===view.ascent?view:{...view,ascent};
scene.world(ascent);
for (const platform of s.world.platforms) drawPlatform(scene,platform,content,view.renderTick,ascent,view.musicDrive||{});
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
scene.islandBakeStats={platforms:content.platforms.length,baked:scene.islandSlots.size,unique:new Set(scene.islandSlots.values()).size};
scene.atlasDirty=true;
}
return scene.islandLayout.get(platform.id);
}
function drawPlatform(scene,platform,content,tick,ascent=null,drive=null){
if (platform.phase==='ABSENT'||platform.phase==='GONE'||platform.phase==='REMOVED') return;
const[x,y,width]=platform.rect;
const screenY=projectY(ascent,y);
if (screenY>400||screenY<-130) return;
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
function ringAge(scene,key,tick){
const memo=scene.ringIntro||(scene.ringIntro=new Map());
if (!memo.has(key)){
if (memo.size>32) memo.clear();
memo.set(key,tick);
}
const age=tick-memo.get(key);
return age<0?Infinity:age;
}
// All six rings of the round are live at once; the gold ring appears on the
// moon at 6/6. The six share one intro, played at the start of the round.
function drawRings(scene,s,content,ascent=null,tick=0){
const add=scene.add.bind(scene);
const mask=s.tower.ringMask;
const age=ringAge(scene,`TOWER:${content.round}`,tick);
for (const r of content.rings){
if (mask&(1<<(r.order-1))) continue;
const cy=projectY(ascent,r.center[1]);
if (cy<-20||cy>404) continue;
emitLiveRing(add,ringKindFor(r.color),r.center[0],cy,tick+r.order*9,age,Z.RING);
}
const gold=content.goldRing;
if ((mask&63)===63&&!(mask&64)){
const cy=projectY(ascent,gold.center[1]);
if (cy>-20&&cy<404) emitLiveRing(add,ringKindFor(gold.color),gold.center[0],cy,tick,ringAge(scene,`TOWER:GOLD:${content.round}`,tick),Z.RING);
}
}
function drawActors(scene,view,alpha){
const s=view.state;
const ascent=view.ascent;
for (const actor of s.actors){
if (actor.lifecycle==='REMOVED') continue;
const prev=view.prev&&view.prev.get(actor.id);
const x=toPx(lerpPos(prev&&prev.x,actor.x,alpha));
const y=projectAnchoredY(ascent,toPx(lerpPos(prev&&prev.y,actor.y,alpha)),25);
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
const row=CLASS_ROW[actor.class]??1;
const nearGroundCadence=standingPlatform(actor.x,actor.y,BIRD_BOX,s.world)!==null;
const frame=scene.birdMotion.sample(actor.id,{
...actor,tick:s.sim.tick,world:'TOWER',grounded:nearGroundCadence,
flapAge:actorStroke(actor),flapPeriod:CLASS_FLAP_PERIOD[actor.class]||8,
landingGap:birdLandingGap(actor,s.world),hurt:false,
threat:false,joust:joustAligned(actor,s.player),
verticalAscent:scene.verticalAscent,
});
drawMount(scene,row,frame,x,y,actor.facing,Z.ACTOR);
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
...player,tick:s.sim.tick,world:'TOWER',grounded:!!player.groundedPlatformId,
flapAge:playerStroke(player),flapPeriod:FLAP_COOLDOWN_TICKS,
landingGap:birdLandingGap(player,s.world),tumble:player.lavaPhase==='SINK',
victory:false,hurt:view.feel?.active&&view.feel.kind==='CLASH',
joust:s.actors.some(actor=>actor.lifecycle==='MOUNTED'&&joustAligned(player,actor)),
verticalAscent:scene.verticalAscent,
});
if (player.invulnerableTicks>0&&(s.sim.tick&2)) return;
drawMount(scene,0,frame,x,y,player.facing,Z.PLAYER,scene.playerMaterial);
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
if (!feel?.active) return;
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
const winning=feel.kind==='JOUST_WIN';
const death=feel.kind==='DEATH';
const primary=death?'lavaHot':winning?'goldLight':'chromeLight';
const secondary=death?'ember':winning?'cyanLight':'cyan';
const reach=4+age*(death?2:1);
feelSwatch(scene,primary,cx-reach,cy,Math.max(1,5-(age>>1)),1);
feelSwatch(scene,primary,cx+reach-Math.max(1,5-(age>>1)),cy,Math.max(1,5-(age>>1)),1);
feelSwatch(scene,secondary,cx,cy-reach,1,Math.max(1,5-(age>>1)));
feelSwatch(scene,secondary,cx,cy+reach-Math.max(1,5-(age>>1)),1,Math.max(1,5-(age>>1)));
if (age<6){
feelSwatch(scene,secondary,cx-reach+2,cy-reach+2,2,1);
feelSwatch(scene,secondary,cx+reach-3,cy+reach-2,2,1);
}
}
function drawMount(scene,row,frame,x,y,facing,z,material=0){
for (const shift of[0,-256,256]){
const xx=x+shift-SPRITE_DRAW_OFFSET[0];
const yy=y-SPRITE_DRAW_OFFSET[1];
if (xx>-32&&xx<256) scene.sprite(row,frame,xx,yy,facing,z,material);
}
}
function drawChevron(scene,cx,cy,dir,colour,z){
for (let i=0;i<7;i++){
const x=dir<0?cx+Math.abs(i-3):cx-Math.abs(i-3);
scene.swatch(colour,x,cy-3+i,2,1,z);
}
}
function buildOverlays(scene,view,content){
const s=view.state,tower=s.tower;
if (s.sim.shell==='PLAY'){
if (tower.hold>0){
scene.swatch('shade',20,156,216,44,Z.OVERLAY+.02);
scene.textCentered(`ROUND ${tower.round} CLEAR`,164,Z.OVERLAY,2,128,'GOLD');
scene.textCentered('EVERY RIVAL DESTROYED',188,Z.OVERLAY,1,128,'WHITE');
}else if (!tower.go){
scene.swatch('shade',24,150,208,66,Z.OVERLAY+.02);
scene.textCentered(`ROUND ${tower.round}`,160,Z.OVERLAY,3,128,'GOLD');
scene.textCentered('FIND 6 RINGS',192,Z.OVERLAY,1,128,'WHITE');
scene.textCentered('THEN THE GOLD RING AT THE MOON',204,Z.OVERLAY,1,128,'CYAN');
}else if (s.player.invulnerableTicks>SHIMMER_TICKS) scene.textCentered('READY',182,Z.OVERLAY,2,128,'CYAN');
}
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
scene.textCentered(`FINAL ${fmt(s.sim.score)}`,118,Z.TOP,1,128,'WHITE');
if (info&&info.isNew){if ((view.renderTick>>4)&1) scene.textCentered('NEW HIGH SCORE',130,Z.TOP,1,128,'GOLD');}
else if (info&&info.best) scene.textCentered(`HI ${fmt(info.best.score)}`,130,Z.TOP,1,128,'DIM');
if (info&&info.round) scene.textCentered(`REACHED ROUND ${info.round}`,240,Z.TOP,1,128,'CYAN');
const items=view.gameOverItems||['NEW RUN'];
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
}
function shade(scene){scene.swatch('shade',0,0,256,384,Z.TOP+0.01);}
const POPUP_TICKS=48;
function drawScorePopups(scene,view){
const list=view.popups;
if (!list||!list.length) return;
const now=view.renderTick|0;
for (const p of list){
const age=now-p.tick;
if (age<0||age>POPUP_TICKS) continue;
if (age>POPUP_TICKS*.7&&(age&1)) continue;
const y=Math.round(projectY(view.ascent,p.y)-age*0.3);
if (y<4||y>370) continue;
scene.textCentered(p.text,y,Z.OVERLAY+.01,p.big?2:1,Math.max(14,Math.min(242,p.x)),p.tone);
}
}
const fmt=(n)=>Math.max(0,Math.trunc(n||0)).toLocaleString('en-US');
export{Scene,buildScene};
