// STRUTHIO ARCADE · game feel: short screen jolts and flashes on hits, rings and
// deaths, phone haptics, and waking the audio context on a gesture.
export function primeAudioContext(context){
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
export function freshFeelState(){
return{kind:'',start:-1,until:-1,shakeUntil:-1,strength:0,priority:0,x:128,y:192,space:'WORLD',contentId:''};
}
export function resetFeelState(feel){Object.assign(feel,freshFeelState());}
export function triggerFeel(feel,{kind,tick,duration,shake=0,strength=1,priority=1,x=128,y=192,space='WORLD',contentId=''}){
if (feel.start===tick&&feel.priority>priority) return;
Object.assign(feel,{kind,start:tick,until:tick+duration,shakeUntil:tick+shake,strength,priority,x,y,space,contentId});
}
export function sampleFeelState(feel,tick){
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
export function pulseHaptic(pattern){
try{
if (typeof navigator!=='undefined'&&typeof navigator.vibrate==='function') navigator.vibrate(pattern);
}catch{}
}
