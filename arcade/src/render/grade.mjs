// STRUTHIO ARCADE · colour grading for the background plates (depth) and island art.
const GRADE=Object.freeze({
STRENGTH:1.0,
EDGE_KEEP:0.42,
CORRIDOR:[0.20,0.80],
TARGET_L50:0.120,
HIGHLIGHT:0.60,
DESAT:0.14,
SHARPEN:0,
NEAR_SETTLE:0.10,
ISLAND_SETTLE:0.08,
});
const LR=0.2126,LG=0.7152,LB=0.0722;
const TO_LINEAR=new Float32Array(256);
for (let i=0;i<256;i++){const s=i/255;TO_LINEAR[i]=s<=0.04045?s/12.92:((s+0.055)/1.055)**2.4;}
function toSrgb(v){
const c=v<=0.0031308?v*12.92:1.055*v**(1/2.4)-0.055;
return Math.max(0,Math.min(255,Math.round(c*255)));
}
const SRGB_STEPS=16384;
const TO_SRGB=new Uint8Array(SRGB_STEPS+1);
for (let i=0;i<=SRGB_STEPS;i++) TO_SRGB[i]=toSrgb(i/SRGB_STEPS);
function toSrgbFast(v){
if (!(v>0)) return 0;
if (v>=1) return 255;
return TO_SRGB[(v*SRGB_STEPS+0.5)|0];
}
function columnWeight(x,w,g=GRADE){
const t=x/Math.max(1,w-1);
const[a,b]=g.CORRIDOR;
if (t>=a&&t<=b) return 1;
const d=t<a?(a-t)/a:(t-b)/(1-b);
const s=Math.min(1,Math.max(0,d));
return 1-(1-g.EDGE_KEEP)*(s*s*(3-2*s));
}
function solveGain(plate,g){
const[a,b]=g.CORRIDOR;
const x0=Math.round(plate.w*a),x1=Math.round(plate.w*b);
const lums=[];
const step=Math.max(2,Math.round(plate.w/128));
for (let y=0;y<plate.h;y+=step){
for (let x=x0;x<x1;x+=step){
const i=(y*plate.w+x)*4;
lums.push(LR*TO_LINEAR[plate.p[i]]+LG*TO_LINEAR[plate.p[i+1]]+LB*TO_LINEAR[plate.p[i+2]]);
}
}
if (!lums.length) return 1;
lums.sort((p,q)=>p-q);
const median=lums[lums.length>>1];
if (median<=g.TARGET_L50) return 1;
const target=g.TARGET_L50;
return (target/(1-g.HIGHLIGHT*target))/Math.max(1e-6,median);
}
const ALPHA_CLEAR=15,ALPHA_SOLID=240;
function settleAlpha(layer){
const out={w:layer.w,h:layer.h,p:new Uint8ClampedArray(layer.p)};
for (let i=3;i<out.p.length;i+=4){
if (out.p[i]<=ALPHA_CLEAR) out.p[i]=0;
else if (out.p[i]>=ALPHA_SOLID) out.p[i]=255;
}
return out;
}
function settle(layer,k,own=false){
if (!(k>0)) return layer;
const{w,h,p}=layer;
const step=Math.max(1,Math.round(w/128))*4;
let sum=0,weight=0;
for (let i=0;i<p.length;i+=step){
const a=p[i+3];
if (!a) continue;
sum+=(LR*p[i]+LG*p[i+1]+LB*p[i+2])*a;
weight+=a;
}
if (!weight) return layer;
const mean=sum/weight;
const out=own?layer:{w,h,p:new Uint8ClampedArray(p)};
const q=out.p;
for (let i=0;i<q.length;i+=4){
if (!q[i+3]) continue;
q[i]+=(mean-q[i])*k;
q[i+1]+=(mean-q[i+1])*k;
q[i+2]+=(mean-q[i+2])*k;
}
return out;
}
function compositeLayers(rear,near){
const out={w:rear.w,h:rear.h,p:new Uint8ClampedArray(rear.p.length)};
for (let i=0;i<out.p.length;i+=4){
const a=near.p[i+3]/255;
for (let k=0;k<3;k++) out.p[i+k]=near.p[i+k]*a+rear.p[i+k]*(1-a);
out.p[i+3]=255;
}
return out;
}
function unsharp(layer,amount){
if (!(amount>0)) return layer;
const{w,h,p}=layer;
const n=w*h;
const wa=new Float32Array(n);
const pre=new Float32Array(n*3);
for (let i=0;i<n;i++){
const a=p[i*4+3]/255;
wa[i]=a;
for (let c=0;c<3;c++) pre[i*3+c]=p[i*4+c]*a;
}
const tmpA=new Float32Array(n),tmpC=new Float32Array(n*3);
const blurA=new Float32Array(n),blurC=new Float32Array(n*3);
for (let y=0;y<h;y++) for (let x=0;x<w;x++){
const i=y*w+x,l=y*w+(x>0?x-1:0),r=y*w+(x<w-1?x+1:w-1);
tmpA[i]=(wa[l]+2*wa[i]+wa[r])/4;
for (let c=0;c<3;c++) tmpC[i*3+c]=(pre[l*3+c]+2*pre[i*3+c]+pre[r*3+c])/4;
}
for (let y=0;y<h;y++) for (let x=0;x<w;x++){
const i=y*w+x,u=(y>0?y-1:0)*w+x,d=(y<h-1?y+1:h-1)*w+x;
blurA[i]=(tmpA[u]+2*tmpA[i]+tmpA[d])/4;
for (let c=0;c<3;c++) blurC[i*3+c]=(tmpC[u*3+c]+2*tmpC[i*3+c]+tmpC[d*3+c])/4;
}
const out={w,h,p:new Uint8ClampedArray(p)};
for (let i=0;i<n;i++){
if (wa[i]<=0) continue;
const norm=blurA[i]>1e-4?1/blurA[i]:0;
for (let c=0;c<3;c++){
const v=p[i*4+c];
out.p[i*4+c]=v+(v-blurC[i*3+c]*norm)*amount;
}
}
return out;
}
function gradeLayers(rear,near,g=GRADE){
const alphaSettled=settleAlpha(near);
const crisp=(layer)=>unsharp(layer,g.SHARPEN);
const back=(layer)=>settle(crisp(layer),g.NEAR_SETTLE,true);
if (g.STRENGTH<=0) return{rear:crisp(rear),near:back(alphaSettled)};
const gain=solveGain(compositeLayers(rear,alphaSettled),g);
if (gain>=0.999) return{rear:crisp(rear),near:back(alphaSettled)};
return{rear:crisp(applyGrade(rear,gain,g)),near:back(applyGrade(alphaSettled,gain,g))};
}
function applyGrade(plate,gain,g){
const out={w:plate.w,h:plate.h,p:new Uint8ClampedArray(plate.p.length)};
const weights=new Float32Array(plate.w);
for (let x=0;x<plate.w;x++) weights[x]=columnWeight(x,plate.w,g)*g.STRENGTH;
for (let y=0;y<plate.h;y++){
for (let x=0;x<plate.w;x++){
const i=(y*plate.w+x)*4;
const w=weights[x];
const r=TO_LINEAR[plate.p[i]],gg=TO_LINEAR[plate.p[i+1]],b=TO_LINEAR[plate.p[i+2]];
const k=1+(gain-1)*w;
let nr=r*k,ng=gg*k,nb=b*k;
const L=LR*nr+LG*ng+LB*nb;
const roll=1/(1+g.HIGHLIGHT*L);
nr*=roll;ng*=roll;nb*=roll;
const d=g.DESAT*w;
if (d>0){
const L2=LR*nr+LG*ng+LB*nb;
nr+=(L2-nr)*d;ng+=(L2-ng)*d;nb+=(L2-nb)*d;
}
out.p[i]=toSrgbFast(nr);out.p[i+1]=toSrgbFast(ng);out.p[i+2]=toSrgbFast(nb);out.p[i+3]=plate.p[i+3];
}
}
return out;
}
const ARCADE_DEPTH=Object.freeze({
REAR:Object.freeze({gain:0.52,desat:0.36,haze:[0.010,0.016,0.034],hazeK:0.50}),
NEAR:Object.freeze({gain:0.80,desat:0.18,haze:[0.006,0.010,0.022],hazeK:0.25}),
});
function depthGrade(plate,d){
const out={w:plate.w,h:plate.h,p:new Uint8ClampedArray(plate.p.length)};
const q=plate.p,o=out.p;
for (let i=0;i<q.length;i+=4){
let r=TO_LINEAR[q[i]]*d.gain,g=TO_LINEAR[q[i+1]]*d.gain,b=TO_LINEAR[q[i+2]]*d.gain;
const L=LR*r+LG*g+LB*b;
r+=(L-r)*d.desat;g+=(L-g)*d.desat;b+=(L-b)*d.desat;
r+=(d.haze[0]-r)*d.hazeK*0.2;g+=(d.haze[1]-g)*d.hazeK*0.2;b+=(d.haze[2]-b)*d.hazeK*0.2;
o[i]=toSrgbFast(r);o[i+1]=toSrgbFast(g);o[i+2]=toSrgbFast(b);o[i+3]=q[i+3];
}
return out;
}
export{gradeLayers,settle,GRADE,depthGrade,ARCADE_DEPTH};
