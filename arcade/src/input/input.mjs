// STRUTHIO ARCADE · input normalisation: wings, chords, darts, keyboard and gamepad.
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
export{InputNormalizer,KEY_MAP,GamepadReader};
