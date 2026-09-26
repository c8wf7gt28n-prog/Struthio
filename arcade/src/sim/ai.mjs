// STRUTHIO ARCADE · rival AI by class, ghost personality and tier.
import{nextU32}from '../core/rng.mjs';
import{wrappedDelta}from '../core/fixed.mjs';
import{LANCE_Y_SUB}from './state.mjs';
const CENTER_X=128*256,CENTER_Y=192*256;
const CLYDE_RADIUS=72*256;
const CLASS_WINDOW={BOUNDER:24,HUNTER:12,SHADOW:8};
const CLASS_FLAP_PERIOD={BOUNDER:10,HUNTER:8,SHADOW:8};
function decodePhase(phase){
return{window:phase>>7,flapCd:(phase>>3)&15,flapWanted:!!(phase&4),dir:[0,-1,1][phase&3]||0};
}
function encodePhase(window,flapCd,flapWanted,dir){
return (window<<7)|((flapCd&15)<<3)|(flapWanted?4:0)|(dir===-1?1:dir===1?2:0);
}
function targetFor(ghost,s,actor,corner,centerY=CENTER_Y){
const p=s.player;
if (ghost==='PINKY') return{x:p.x+4*p.vx,y:p.y+4*p.vy};
if (ghost==='INKY'){const lx=p.x+4*p.vx,ly=p.y+4*p.vy;return{x:2*CENTER_X-lx,y:2*centerY-ly};}
if (ghost==='CLYDE'){
const dx=wrappedDelta(actor.x,p.x),dy=p.y-actor.y;
if (Math.abs(dx)>CLYDE_RADIUS||Math.abs(dy)>CLYDE_RADIUS) return{x:p.x,y:p.y};
return{x:corner[0]*256,y:corner[1]*256};
}
return{x:p.x,y:p.y};
}
function rivalIntent(A,s,actor,aiClass,corner,playerActive,centerY=CENTER_Y){
const C=A.sim;
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
const t=targetFor(ghost,s,actor,corner,centerY);
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
if (!playerActive){dir=0;flapWanted=actor.y>centerY;}
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
export{rivalIntent,decodePhase,CLASS_FLAP_PERIOD};
