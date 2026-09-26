// STRUTHIO ARCADE · sound effects: game events become short synth notes sent
// to the audio worklet, prioritised and (for stings) quantized to the beat.
const PROTECTED=new Set(['joust-win','player-death','round-clear','gold-open']);
const EVENT_TO_SFX={FLAP:'flap',RING:'ring',JOUST_CLASH:'joust-clash',JOUST_WIN:'joust-win',PLAYER_DEATH:'player-death',EGG:'egg',HATCH:'hatch',GOLD_RING_OPEN:'gold-open',ROUND_START:'gold-open',ROUND_CLEAR:'round-clear'};
const VOICES=Object.freeze([
{id:'C_FLAP',wave:'XORSHIFT_NOISE',filter:'LP1',coefQ15:5200,attack:72,decay:1300,sustainQ15:0,release:900,gainQ15:10400,glide:-7},
{id:'C_RING',wave:'SINE',filter:'LP1',coefQ15:30000,attack:60,decay:5200,sustainQ15:6000,release:5600,gainQ15:8600,glide:5},
{id:'C_CLASH',wave:'XORSHIFT_NOISE',filter:'LP1',coefQ15:2600,attack:24,decay:2200,sustainQ15:0,release:700,gainQ15:9800,glide:-12},
{id:'C_WIN',wave:'TRIANGLE',filter:'LP1',coefQ15:20000,attack:60,decay:5400,sustainQ15:7000,release:6000,gainQ15:9000,glide:7},
{id:'C_DEATH',wave:'TRIANGLE',filter:'LP1',coefQ15:9000,attack:120,decay:9000,sustainQ15:4000,release:7200,gainQ15:9800,glide:-19},
{id:'C_PLINK',wave:'SINE',filter:'LP1',coefQ15:30000,attack:48,decay:2600,sustainQ15:0,release:1800,gainQ15:6200,glide:3},
{id:'C_STING',wave:'PULSE_25',filter:'LP1',coefQ15:7000,attack:240,decay:7200,sustainQ15:9000,release:9600,gainQ15:6200,glide:0},
].map(Object.freeze));
const SFX=Object.freeze({
flap:{voice:'C_FLAP',midi:84,len:0.05,jitter:2,minGap:0.085},
ring:{voice:'C_RING',midi:81,len:0.16,jitter:0},
'joust-clash':{voice:'C_CLASH',midi:52,len:0.07,jitter:1},
'joust-win':{voice:'C_WIN',midi:76,len:0.22,jitter:0},
'player-death':{voice:'C_DEATH',midi:60,len:0.42,jitter:0},
egg:{voice:'C_PLINK',midi:79,len:0.08,jitter:1},
hatch:{voice:'C_PLINK',midi:72,len:0.14,jitter:1},
'gold-open':{voice:'C_STING',midi:76,len:0.45,jitter:0},
'round-clear':{voice:'C_STING',midi:84,len:0.8,jitter:0},
});
export function synthConfig(audio){
return{...audio,voices:[...VOICES],buses:{...audio.buses,sfxGainQ15:Math.round(audio.buses.sfxGainQ15*0.71)}};
}
export class Conductor{
constructor(audioAuthority,{context,send}){
this.A=audioAuthority;this.ctx=context;this.send=send;this.now=()=>context.currentTime;
const bpm=audioAuthority.transportBpmQ16/65536;
this.eighth=60/bpm/2;this.beat=this.eighth*2;
this.origin=this.now();
this.late=0;this.scheduled=0;this.dropped=0;this.lastAt={};
}
schedule(note){
const t=this.now();
if (note.atSeconds<t){
const lateMs=(t-note.atSeconds)*1000;this.late+=1;
if (lateMs<50) note.atSeconds=t;else if (note.priority<7){this.dropped+=1;return;}else note.atSeconds=t;
}
this.scheduled+=1;
this.send({type:'note',...note});
}
quantized(q){
const t=this.now();const rel=t-this.origin;
if (q==='NEXT_EIGHTH') return this.origin+Math.ceil(rel/this.eighth)*this.eighth;
if (q==='NEXT_BEAT') return this.origin+Math.ceil(rel/this.beat)*this.beat;
return t;
}
onEvents(events){
for (const ev of events){
const key=EVENT_TO_SFX[ev.type];if (!key) continue;
const map=this.A.eventMap[key];if (!map) continue;
const at=this.quantized(map.quantize);
const c=SFX[key];
if (c){
if (c.minGap){const last=this.lastAt[key]||-1;if (at-last<c.minGap) continue;this.lastAt[key]=at;}
const midi=c.midi+(c.jitter?Math.round((Math.random()*2-1)*c.jitter):0);
this.schedule({voiceId:c.voice,midi,len:Math.round(c.len*this.ctx.sampleRate),atSeconds:at,priority:map.priority,bus:'sfx',protectedNote:PROTECTED.has(key)});
}
}
}
stats(){return{scheduled:this.scheduled,late:this.late,dropped:this.dropped,latePercent:this.scheduled?(100*this.late)/this.scheduled:0};}
}
