import{clamp,tdiv,mod,WRAP,compareRational,nearestWrapShift}from '../core/fixed.mjs';
import{entityBox}from './state.mjs';
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
export{integrate,inRing,boxesOverlap,standingPlatform,overlapsX};
