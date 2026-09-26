import{Mixer}from './synth.mjs';
import{StereoStage}from './stereo.mjs';
class StruthioProcessor extends AudioWorkletProcessor{
constructor(){
super();
this.mixer=null;this.stage=null;this.buf=new Int16Array(128);
this.left=new Float32Array(128);this.right=new Float32Array(128);this.underruns=0;
this.port.onmessage=(e)=>{
const m=e.data;
if (m.type==='init'){
this.mixer=new Mixer(m.audio,sampleRate);
this.stage=new StereoStage(sampleRate,m.audio.transportBpmQ16);
this.port.postMessage({type:'ready',sampleRate,presentation:'STEREO'});
}
else if (m.type==='note'&&this.mixer){const at=Math.max(this.mixer.frame,Math.round(m.atSeconds*sampleRate));this.mixer.noteOn({...m,at});}
else if (m.type==='off'&&this.mixer) this.mixer.allNotesOff(m.bus);
else if (m.type==='stats') this.port.postMessage({type:'stats',frame:this.mixer?this.mixer.frame:0,notes:this.mixer?this.mixer.notes.length:0});
};
}
process(inputs,outputs){
const out=outputs[0];
if (!this.mixer||!out||!out[0]) return true;
const n=out[0].length;
if (this.buf.length!==n){
this.buf=new Int16Array(n);
this.left=new Float32Array(n);
this.right=new Float32Array(n);
}
this.mixer.render(this.buf);
this.stage.process(this.buf,this.left,this.right);
if (out.length===1){
for (let i=0;i<n;i++) out[0][i]=(this.left[i]+this.right[i])*.5;
}else{
out[0].set(this.left);
out[1].set(this.right);
for (let c=2;c<out.length;c++) out[c].set((c&1)?this.right:this.left);
}
return true;
}
}
registerProcessor('struthio-synth',StruthioProcessor);
