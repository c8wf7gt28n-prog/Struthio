const Q15=1/32768;
const TWO_32=4294967296;
const PULSE_WIDTH=Object.freeze({PULSE_50:0x80000000,PULSE_25:0x40000000,PULSE_12_5:0x20000000});
const NOISE_CLOCK=8;
const ENV_FLOOR=0.0005;
export class Mixer{
constructor(audio,sampleRate){
this.rate=sampleRate;
this.timeScale=sampleRate/(audio.sampleRate||48000);
this.voices=new Map(audio.voices.map((v)=>[v.id,v]));
this.increments=audio.phaseIncrementQ32||{};
this.buses=audio.buses;
this.frame=0;
this.notes=[];
this.noise=0x6d2b79f5;
this.dcIn=0;
this.dcOut=0;
}
increment(midi){
const authored=this.increments[String(midi)];
const at48k=authored!==undefined?authored:440*2**((midi-69)/12)/48000*TWO_32;
return at48k/this.timeScale;
}
noteOn({voiceId,midi,len,at,priority=1,bus='sfx',protectedNote=false}){
const voice=this.voices.get(voiceId);
if (!voice) return false;
const k=this.timeScale;
const note={
voice,bus,priority,protectedNote,
start:at,
gateEnd:at+Math.max(1,len|0),
attack:Math.max(1,Math.round(voice.attack*k)),
decay:Math.max(1,Math.round(voice.decay*k)),
release:Math.max(1,Math.round(voice.release*k)),
sustain:voice.sustainQ15*Q15,
gain:voice.gainQ15*Q15,
coef:voice.coefQ15*Q15,
inc:this.increment(midi),
inc0:this.increment(midi),
glide:Number(voice.glide)||0,
phase:0,
noisePhase:0,
noiseValue:0,
filter:0,
releaseFrom:-1,
done:false,
};
if (!this.makeRoom(note)) return false;
this.notes.push(note);
return true;
}
makeRoom(incoming){
const cap=(list,limit)=>{
while (list.length>=limit){
let victim=null;
for (const n of list){
if (n.protectedNote) continue;
if (!victim||n.priority<victim.priority||(n.priority===victim.priority&&n.start<victim.start)) victim=n;
}
if (!victim||victim.priority>incoming.priority) return false;
victim.done=true;
this.notes=this.notes.filter((n)=>n!==victim);
list.splice(list.indexOf(victim),1);
}
return true;
};
if (!cap([...this.notes],this.buses.transientPoolCap||32)) return false;
return incoming.sustain<=0||cap(this.notes.filter((n)=>n.sustain>0),this.buses.sustainedVoiceCap||10);
}
allNotesOff(bus){
for (const n of this.notes) if (!bus||n.bus===bus) n.gateEnd=Math.min(n.gateEnd,this.frame);
}
envelope(n,f){
const t=f-n.start;
let level;
if (t<n.attack) level=t/n.attack;
else level=n.sustain+(1-n.sustain)*Math.exp(-(t-n.attack)/n.decay);
if (f<n.gateEnd){
if (t>=n.attack&&level<ENV_FLOOR) n.done=true;
return level;
}
if (n.releaseFrom<0) n.releaseFrom=level;
const out=n.releaseFrom*Math.exp(-(f-n.gateEnd)/n.release);
if (out<ENV_FLOOR){n.done=true;return 0;}
return out;
}
wave(n){
const kind=n.voice.wave;
const phase=n.phase;
if (kind==='TRIANGLE'){const saw=phase/0x80000000-1;return 2*Math.abs(saw)-1;}
if (kind==='SAW') return phase/0x80000000-1;
if (kind==='SINE') return Math.sin(phase*(2*Math.PI/TWO_32));
if (kind==='XORSHIFT_NOISE'){
const next=n.noisePhase+n.inc*NOISE_CLOCK;
if (next>=TWO_32||n.noiseValue===0){
let x=this.noise;
x^=x<<13;x>>>=0;x^=x>>>17;x^=x<<5;x>>>=0;
this.noise=x;
n.noiseValue=x/0x80000000-1;
}
n.noisePhase=next%TWO_32;
return n.noiseValue;
}
return phase<(PULSE_WIDTH[kind]||PULSE_WIDTH.PULSE_50)?1:-1;
}
render(out){
if (typeof currentFrame==='number') this.frame=currentFrame;
const b=this.buses;
const master=b.masterGainQ15*Q15,ceiling=b.limiterCeilingQ15*Q15,dcR=b.dcBlockR_Q15*Q15;
const busGain={sfx:b.sfxGainQ15*Q15,music:b.musicGainQ15*Q15};
for (let i=0;i<out.length;i++){
const f=this.frame+i;
let mix=0;
for (const n of this.notes){
if (n.done||f<n.start) continue;
const env=this.envelope(n,f);
if (n.glide&&((f-n.start)&31)===0){
const k=Math.min(1,(f-n.start)/Math.max(1,n.gateEnd-n.start));
n.inc=n.inc0*2**(n.glide*k/12);
}
let s=this.wave(n);
n.filter+=(s-n.filter)*n.coef;
s=n.voice.filter==='HP1'?s-n.filter:n.filter;
mix+=s*env*n.gain*(busGain[n.bus]??busGain.sfx);
n.phase=(n.phase+n.inc)%TWO_32;
}
let y=mix*master;
const dc=y-this.dcIn+dcR*this.dcOut;
this.dcIn=y;this.dcOut=dc;y=dc;
if (y>ceiling) y=ceiling;else if (y<-ceiling) y=-ceiling;
out[i]=Math.round(y*32767);
}
this.frame+=out.length;
if (this.notes.some((n)=>n.done)) this.notes=this.notes.filter((n)=>!n.done);
}
}
