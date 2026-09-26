// STRUTHIO ARCADE · the moving world: island motion (eased drift and bob)
// and setting the tower up at the start of a run.
import{px,tdiv,mod}from '../core/fixed.mjs';
import{emptyPlayer}from './state.mjs';

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
export function platformAt(p,t){
const[x0,y0,w0,h0]=p.rect;
const motion=p.motion;
if (motion&&typeof motion==='object'){
const{period,delta}=easedMotion(motion,t);
const u=mod(t,period),profile=motion.profile||'STATIC';
if (profile==='DRIFT_X_SOFT'||profile==='HOLD_SHIFT_X') return{id:p.id,phase:profile,tick:u,rect:[x0+delta,y0,w0,h0],collidable:true};
if (profile==='BOB_Y_SOFT') return{id:p.id,phase:profile,tick:u,rect:[x0,y0+delta,w0,h0],collidable:true};
return{id:p.id,phase:'STATIC',tick:u,rect:[x0,y0,w0,h0],collidable:true};
}
return{id:p.id,phase:'STATIC',tick:0,rect:[x0,y0,w0,h0],collidable:true};
}
export function buildPlatforms(content){
return content.platforms.map((p)=>platformAt(p,p.phaseOffset||0));
}
export function stepWorld(s,content){
const byId=new Map(content.platforms.map((p)=>[p.id,p]));
for (const w of s.world.platforms){
const p=byId.get(w.id);
if (!p) continue;
const next=platformAt(p,w.tick+1);
w.phase=next.phase;w.tick=next.tick;w.rect=next.rect;w.collidable=next.collidable;
}
s.world.lavaY=px(content.hazard.lavaY);
}
export function activateTower(s,content,events){
s.world.platforms=buildPlatforms(content);
s.world.lavaY=px(content.hazard.lavaY);
s.actors=[];
const keepWing=s.player.wing;
s.player=emptyPlayer(content.playerSpawn[0],content.playerSpawn[1]);
s.player.wing=keepWing;
s.tower.ringMask=0;
s.tower.cooldown=0;
s.run.eggChain=0;
s.run.clean=true;
events.push({type:'ARENA_ACTIVATE',contentId:content.contentId});
}
