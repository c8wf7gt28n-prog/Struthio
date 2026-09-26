// STRUTHIO ARCADE · the looping soundtrack: playback, ducking and beat tracking for visuals.
const clamp=(value,lo,hi)=>Math.max(lo,Math.min(hi,value));
class MediaLoopTrack{
constructor(element,{gain=0.56,bpm=95.703,beatsPerBar=4}={}){
if (!element||typeof element.play!=='function') throw new Error('MUSIC_ELEMENT_UNAVAILABLE');
this.element=element;
this.baseGain=clamp(gain,0,1);
this.bpm=Math.max(1,bpm);
this.beatsPerBar=Math.max(1,beatsPerBar|0);
this.playing=false;
this.lastError=null;
this.restoreTimer=null;
element.loop=true;
element.preload='auto';
element.volume=this.baseGain;
}
start(){
this.playing=true;
this.element.loop=true;
if (!this.element.paused&&!this.element.ended) return Promise.resolve(this);
this.element.volume=this.baseGain;
let attempt;
try{attempt=this.element.play();}
catch (error){this.lastError=String(error);return Promise.reject(error);}
return Promise.resolve(attempt).then(()=>{this.lastError=null;return this;},(error)=>{
this.lastError=String(error);
throw error;
});
}
visualState(){
if (!this.playing||this.element.paused||this.element.ended) return{active:false,low:0,high:0,beat:0,downbeat:0};
const beatSeconds=60/this.bpm;
const time=Math.max(0,Number(this.element.currentTime)||0);
const beatIndex=Math.floor(time/beatSeconds);
const beatPhase=(time%beatSeconds)/beatSeconds;
const eighthPhase=(time%(beatSeconds*0.5))/(beatSeconds*0.5);
const beat=Math.exp(-beatPhase*9.2);
const high=clamp(0.14+Math.exp(-eighthPhase*12)*0.48+beat*0.16,0,1);
const low=clamp(0.12+beat*0.68,0,1);
return{active:true,low,high,beat,downbeat:beatIndex%this.beatsPerBar===0?beat:0};
}
duck({depth=0.55,attack=0.012,hold=0.025,release=0.2}={}){
if (!this.playing) return;
clearTimeout(this.restoreTimer);
this.element.volume=this.baseGain*(1-(1-clamp(depth,0.1,1))*0.5);
this.restoreTimer=setTimeout(()=>{this.element.volume=this.baseGain;},Math.max(0,(attack+hold+release)*1000));
}
stop(){
this.playing=false;
clearTimeout(this.restoreTimer);
this.restoreTimer=null;
this.element.volume=this.baseGain;
this.element.pause();
}
}
function createMediaLoopTrack(element,options){return new MediaLoopTrack(element,options);}
export{createMediaLoopTrack};
