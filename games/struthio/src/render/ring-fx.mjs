// STRUTHIO ARCADE · ring art: the live ring bands, halo, sparks, intro shockwave and collect burst.
const RING_FX_ORIGIN=Object.freeze([0,904]);
const RING_BAND_FRAMES=10;
const RING_LOCKED_FRAME=RING_BAND_FRAMES;
const RING_HALO_FRAMES=4;
const RING_SHOCK_FRAMES=4;
const RING_SPARK_FRAMES=3;
const RING_KINDS=Object.freeze(['MAGENTA','GREEN']);
const BAND_PX=72,HALO_PX=96,SHOCK_PX=96,SPARK_PX=15;
const[OX,OY]=RING_FX_ORIGIN;
const BAND_Y=OY;
const HALO_Y=OY+BAND_PX*RING_KINDS.length;
const SHOCK_Y=HALO_Y+HALO_PX;
const SPARK_Y=SHOCK_Y+SHOCK_PX;
const TONES=Object.freeze({
MAGENTA:Object.freeze({deep:'cyanDeep',main:'cyan',light:'cyanLight',core:'white',glow:[64,214,232]}),
GREEN:Object.freeze({deep:'goldDeep',main:'gold',light:'goldLight',core:'white',glow:[226,169,63]}),
});
const LOCKED_TONES=Object.freeze({
MAGENTA:Object.freeze({deep:'cyanDeep',main:'cyanDeep',light:'cyanDark',core:'cyanDark',glow:[8,58,68]}),
GREEN:Object.freeze({deep:'goldDeep',main:'goldDeep',light:'ochre',core:'ochre',glow:[74,46,8]}),
});
const kindIndex=(kind)=>Math.max(0,RING_KINDS.indexOf(kind));
const ringKindFor=(color)=>(color==='GREEN'?'GREEN':'MAGENTA');
const ringBandSource=(kind,frame)=>[OX+(((frame%RING_BAND_FRAMES)+RING_BAND_FRAMES)%RING_BAND_FRAMES)*BAND_PX,BAND_Y+kindIndex(kind)*BAND_PX];
const ringLockedSource=(kind)=>[OX+RING_LOCKED_FRAME*BAND_PX,BAND_Y+kindIndex(kind)*BAND_PX];
const ringHaloSource=(kind,frame)=>[OX+(kindIndex(kind)*RING_HALO_FRAMES+clampInt(frame,0,RING_HALO_FRAMES-1))*HALO_PX,HALO_Y];
const ringShockSource=(kind,frame)=>[OX+(kindIndex(kind)*RING_SHOCK_FRAMES+clampInt(frame,0,RING_SHOCK_FRAMES-1))*SHOCK_PX,SHOCK_Y];
const ringSparkSource=(kind,frame)=>[OX+(kindIndex(kind)*RING_SPARK_FRAMES+clampInt(frame,0,RING_SPARK_FRAMES-1))*16,SPARK_Y];
function clampInt(n,lo,hi){return Math.max(lo,Math.min(hi,n|0));}
const smooth=(e0,e1,x)=>{const t=Math.max(0,Math.min(1,(x-e0)/(e1-e0)));return t*t*(3-2*t);};
const mix=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t];
function over(s,x,y,rgb,a){
if (a<=0.004) return;
const i=(y*s.w+x)*4,p=s.p;
const da=p[i+3]/255,sa=Math.min(1,a);
const oa=sa+da*(1-sa);
for (let k=0;k<3;k++) p[i+k]=Math.round((rgb[k]*sa+p[i+k]*da*(1-sa))/Math.max(oa,1e-6));
p[i+3]=Math.round(oa*255);
}
function paintBand(s,C,x0,y0,tone,frame){
const deep=C[tone.deep],main=C[tone.main],light=C[tone.light],core=C[tone.core];
const phase=(frame/RING_BAND_FRAMES)*(Math.PI*2/8);
const c=BAND_PX/2;
for (let py=0;py<BAND_PX;py++) for (let px=0;px<BAND_PX;px++){
const dx=px+.5-c,dy=py+.5-c;
const d=Math.hypot(dx,dy),th=Math.atan2(dy,dx);
const rim=smooth(35.2,34.2,d)*smooth(22.2,23.2,d);
if (rim>0) over(s,x0+px,y0+py,deep,rim);
const band=smooth(33.4,32.4,d)*smooth(24.4,25.4,d);
if (band>0){
const seg=Math.pow(.5+.5*Math.cos(8*(th-phase)),3);
const lead=Math.pow(.5+.5*Math.cos(8*(th-phase)-.9),12);
const bevel=smooth(32.6,26.2,d);
let rgb=mix(main,light,Math.min(1,seg*.85+bevel*.25));
rgb=mix(rgb,core,lead*.55);
rgb=mix(rgb,deep,smooth(30.8,33.2,d)*.45);
over(s,x0+px,y0+py,rgb,band);
}
const lip=smooth(26.6,25.9,d)*smooth(24.3,25.0,d);
if (lip>0) over(s,x0+px,y0+py,light,lip*.95);
const track=smooth(20.6,19.8,d)*smooth(17.4,18.2,d);
if (track>0){
const dot=smooth(.55,.85,Math.cos(12*(th+phase*1.5)));
if (dot>0) over(s,x0+px,y0+py,light,track*dot*.82);
}
const g=Math.cos(th+2.35);
const glint=smooth(.86,.98,g)*smooth(31.6,30.2,d)*smooth(26.2,27.6,d);
if (glint>0) over(s,x0+px,y0+py,core,glint*.9);
const notch=smooth(1.6,.9,Math.abs(dx))*smooth(35.6,34.6,d)*smooth(31.8,32.8,d)*(Math.abs(dy)>30?1:0);
if (notch>0) over(s,x0+px,y0+py,light,notch);
}
}
const SCRIM_PEAK=0.62;
const SCRIM_RGB=[4,6,9];
function paintHalo(s,x0,y0,rgb,strength){
const c=HALO_PX/2;
for (let py=0;py<HALO_PX;py++) for (let px=0;px<HALO_PX;px++){
const d=Math.hypot(px+.5-c,py+.5-c);
const edge=smooth(48,42,d);
const scrim=Math.exp(-Math.pow(d/26,2.4))*SCRIM_PEAK*edge;
if (scrim>0) over(s,x0+px,y0+py,SCRIM_RGB,scrim);
const ringGlow=Math.exp(-Math.pow((d-29)/9.5,2));
const fill=Math.exp(-Math.pow(d/30,2))*.22;
const a=(ringGlow+fill)*strength*edge;
over(s,x0+px,y0+py,rgb,a);
}
}
function paintShock(s,C,x0,y0,tone,strength){
const c=SHOCK_PX/2,light=C[tone.light],core=C[tone.core];
for (let py=0;py<SHOCK_PX;py++) for (let px=0;px<SHOCK_PX;px++){
const d=Math.hypot(px+.5-c,py+.5-c);
const wave=smooth(47.5,45.8,d)*smooth(40.5,43.5,d);
const hot=smooth(46.4,45.4,d)*smooth(43.4,44.4,d);
if (wave>0) over(s,x0+px,y0+py,light,wave*strength*.75);
if (hot>0) over(s,x0+px,y0+py,core,hot*strength);
}
}
function paintSpark(s,C,x0,y0,tone,size){
const c=SPARK_PX/2,light=C[tone.light],core=C[tone.core];
const arm=[3.2,5.2,7.2][size];
for (let py=0;py<SPARK_PX;py++) for (let px=0;px<SPARK_PX;px++){
const dx=Math.abs(px+.5-c),dy=Math.abs(py+.5-c);
const cross=Math.max(smooth(arm,0,dx)*smooth(1.3,.3,dy),smooth(arm,0,dy)*smooth(1.3,.3,dx));
const diag=smooth(arm*.45,0,Math.hypot(dx,dy))*.8;
const a=Math.max(cross,diag);
if (a>0) over(s,x0+px,y0+py,mix(light,core,smooth(.5,1,a)),a);
}
}
function paintRingFx(s,C){
RING_KINDS.forEach((kind)=>{
const tone=TONES[kind];
for (let f=0;f<RING_BAND_FRAMES;f++){const[x,y]=ringBandSource(kind,f);paintBand(s,C,x,y,tone,f);}
{const[x,y]=ringLockedSource(kind);paintBand(s,C,x,y,LOCKED_TONES[kind],0);}
[.34,.48,.62,.78].forEach((k,f)=>{const[x,y]=ringHaloSource(kind,f);paintHalo(s,x,y,tone.glow,k);});
[1,.72,.46,.22].forEach((k,f)=>{const[x,y]=ringShockSource(kind,f);paintShock(s,C,x,y,tone,k);});
for (let f=0;f<RING_SPARK_FRAMES;f++){const[x,y]=ringSparkSource(kind,f);paintSpark(s,C,x,y,tone,f);}
});
}
const easeOutBack=(t)=>{const k=1.9;const u=t-1;return 1+(k+1)*u*u*u+k*u*u;};
const RING_INTRO_TICKS=22;
const RING_BURST_TICKS=22;
function quad(add,cx,cy,size,src,srcPx,z){
add(cx-size/2,cy-size/2,size,size,src[0],src[1],srcPx,srcPx,z);
}
function emitLiveRing(add,kind,cx,cy,tick,age,z){
const intro=age<RING_INTRO_TICKS?age/RING_INTRO_TICKS:1;
const scale=intro>=1?1:Math.max(.08,easeOutBack(Math.min(1,intro*1.35)));
const breath=[0,1,2,3,3,2,1,0][(tick>>3)&7];
quad(add,cx,cy,32*Math.max(scale,.4),ringHaloSource(kind,intro<1?3:breath),HALO_PX,z+.006);
quad(add,cx,cy,24*scale,ringBandSource(kind,Math.floor(tick/3)),BAND_PX,z);
if (intro<1){
const k=intro;
quad(add,cx,cy,80-52*k,ringShockSource(kind,Math.min(3,Math.floor(k*4))),SHOCK_PX,z-.004);
for (let i=0;i<4;i++){
const a=i*Math.PI/2+Math.PI/4+tick*.02;
const r=30*(1-k)+11;
quad(add,cx+Math.cos(a)*r,cy+Math.sin(a)*r,5,ringSparkSource(kind,2-Math.min(2,Math.floor(k*3))),SPARK_PX,z-.005);
}
return;
}
for (let i=0;i<3;i++){
const a=tick*.045+i*(Math.PI*2/3);
const front=Math.sin(a)>0;
const size=[0,1,2,1][((tick>>2)+i*2)&3];
quad(add,cx+Math.cos(a)*14.5,cy+Math.sin(a)*14.5,4+size*1.5,ringSparkSource(kind,size),SPARK_PX,front?z-.005:z+.003);
}
}
function emitLockedRing(add,kind,cx,cy,z){
quad(add,cx,cy,32,ringHaloSource(kind,0),HALO_PX,z+.006);
quad(add,cx,cy,24,ringLockedSource(kind),BAND_PX,z);
}
function emitRingBurst(add,kind,cx,cy,age,z){
if (age>=RING_BURST_TICKS) return;
const t=age/RING_BURST_TICKS;
const ease=1-(1-t)*(1-t);
if (age<7) quad(add,cx,cy,24+age*3.2,ringBandSource(kind,age),BAND_PX,z-.002);
quad(add,cx,cy,30+ease*62,ringShockSource(kind,Math.min(3,Math.floor(t*4))),SHOCK_PX,z-.003);
if (age>3){
const t2=(age-3)/(RING_BURST_TICKS-3);
quad(add,cx,cy,26+(1-(1-t2)*(1-t2))*40,ringShockSource(kind,Math.min(3,1+Math.floor(t2*3))),SHOCK_PX,z-.0035);
}
const size=age<7?2:age<14?1:0;
for (let i=0;i<8;i++){
const a=i*Math.PI/4+(i&1?.2:0);
const r=10+ease*(i&1?30:38);
quad(add,cx+Math.cos(a)*r,cy+Math.sin(a)*r,4+size*2,ringSparkSource(kind,size),SPARK_PX,z-.004);
}
}
export{paintRingFx,emitLiveRing,emitLockedRing,emitRingBurst,ringKindFor};
