// STRUTHIO ARCADE · picks a jouster pose each frame from motion, flaps, landings and jousts.
import{SPRITE_RANGES as R}from './sprites.mjs';
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
export{BirdAnimation};
