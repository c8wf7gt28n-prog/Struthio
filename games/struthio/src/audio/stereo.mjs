export class StereoStage{
constructor(sampleRate,transportBpmQ16){
this.sampleRate=sampleRate;
this.bpm=transportBpmQ16/65536;
}
process(mono,left,right){
for (let i=0;i<mono.length;i++){
const s=mono[i]/32768;
left[i]=s;
right[i]=s;
}
}
}
