// STRUTHIO ARCADE · the on-screen wing controller (touch ownership, chords, dart slides, menus).
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
// DART: a downward flick on a wing. Anything within 60 degrees of straight
// down counts, checked while moving and again on release (so a fast flick that
// lifts off early still darts). A diagonal flick picks the dart's side; a
// straight-down one darts to that wing's side.
const DART_CONE=Math.tan(60*Math.PI/180),DART_SIDE_CONE=Math.tan(20*Math.PI/180);
function tryDart(e,region){
const g=gesture.get(e.pointerId);
if (!g||g.darted||!DIRECTIONS.has(region)) return;
const dx=e.clientX-g.x,dy=e.clientY-g.y;
if (dy<g.diameter*.10||Math.abs(dx)>dy*DART_CONE) return;
const side=Math.abs(dx)>dy*DART_SIDE_CONE?(dx<0?'LEFT_WING':'RIGHT_WING'):region;
g.darted=input.controlDart(pointerKey(e.pointerId),side);
if (g.darted) root.classList.add('is-darting');
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
tryDart(e,current);
next=input.controlPointerMove(pointerKey(e.pointerId),current)||current;
}
const button=buttons.get(next);
if (button) paintContact(button,e);
sync();
}
function release(e,cancelled=false){
if (!active.has(e.pointerId)) return;
if (!cancelled) tryDart(e,active.get(e.pointerId));
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
export{installSmartControls};
