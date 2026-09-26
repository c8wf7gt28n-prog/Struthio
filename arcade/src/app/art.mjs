// STRUTHIO ARCADE · loading the art: decode WebP to RGBA, check the Arcade plates
// and island sheet, drop the jouster sheet's dark outline, and
// build the turning moon globe from the rear plate.
import{WORLD_PLATE_W,WORLD_PLATE_H,GLOBE_MAP_W,GLOBE_MAP_H}from '../render/renderer.mjs';
import{ISLAND_SHEET}from '../render/islands.mjs';
export const ART=Object.freeze({
rear:'assets/art/background-rear.webp',
near:'assets/art/background-near.webp',
islands:'assets/art/islands.webp',
metadata:'assets/art/islands.json',
bird:'assets/art/jousters.webp',
music:'assets/audio/tarmac-at-midnight-loop.mp3',
musicBpm:120,
});
async function decodeArtwork(buf){
const blob=new Blob([buf],{type:'image/webp'});
let bitmap;
try{bitmap=await createImageBitmap(blob,{colorSpaceConversion:'none',premultiplyAlpha:'none'});}
catch{bitmap=await createImageBitmap(blob);}
try{
const canvas=document.createElement('canvas');canvas.width=bitmap.width;canvas.height=bitmap.height;
const ctx=canvas.getContext('2d',{willReadFrequently:true});
if (!ctx) throw new Error('ART_DECODER_UNAVAILABLE');
ctx.drawImage(bitmap,0,0);
return{w:canvas.width,h:canvas.height,p:new Uint8Array(ctx.getImageData(0,0,canvas.width,canvas.height).data)};
}finally{bitmap.close();}
}
async function fetchBytes(base,path){
const response=await fetch(base+path,{cache:'no-cache'});
if (!response.ok) throw new Error(`FETCH ${path} ${response.status}`);
return new Uint8Array(await response.arrayBuffer());
}
async function loadImage(base,path,w,h){
const art=await decodeArtwork(await fetchBytes(base,path));
if (art.w!==w||art.h!==h) throw new Error(`ART_SIZE ${path} ${art.w}x${art.h}, expected ${w}x${h}`);
return art;
}
function validateArcadeArt({rear,near,islands,metadata}){
const fail=(code)=>{throw new Error('ARCADE_ART '+code);};
if (rear.w!==WORLD_PLATE_W||rear.h!==WORLD_PLATE_H||near.w!==WORLD_PLATE_W||near.h!==WORLD_PLATE_H) fail('PLATE_SIZE');
if (islands.w!==ISLAND_SHEET.w||islands.h!==ISLAND_SHEET.h) fail('ISLAND_SIZE');
for (let i=3;i<rear.p.length;i+=4*97) if (rear.p[i]!==255) fail('REAR_NOT_OPAQUE');
const colAlpha=(x0,x1)=>{let sum=0,n=0;for (let y=0;y<near.h;y+=8) for (let x=x0;x<x1;x+=4){sum+=near.p[(y*near.w+x)*4+3];n++;}return sum/n;};
const w=near.w,centre=colAlpha(Math.round(w*.375),Math.round(w*.625)),sides=(colAlpha(0,Math.round(w*.125))+colAlpha(Math.round(w*.875),w))/2;
if (!(centre<24)) fail('NEAR_CENTRE_NOT_OPEN');
if (!(sides>64)) fail('NEAR_SIDES_EMPTY');
if (!metadata||metadata.rendererExtension!=='topDecorV1'||!Array.isArray(metadata.masters)) fail('METADATA');
const count=(role)=>metadata.masters.filter((m)=>m.role===role).length;
if (count('STANDARD')!==9||count('GROUND')!==1) fail('MASTER_CONTRACT');
for (const m of metadata.masters){
if (!(m.capTop>0&&m.capTop+22<m.h)) fail('CAP_TOP '+m.id);
if (m.topDecorRows!==undefined&&!(m.topDecorRows>=0&&m.topDecorRows<=m.capTop)) fail('TOP_DECOR '+m.id);
}
return{centreAlpha:+centre.toFixed(1),sideAlpha:+sides.toFixed(1),masters:metadata.masters.length};
}
function markJousterRims(sheet){
const{w,h,p}=sheet;
const a=new Uint8Array(w*h);
for (let i=0;i<w*h;i++) a[i]=p[i*4+3];
const clear=(x,y)=>x<0||y<0||x>=w||y>=h||a[y*w+x]<128;
let n=0;
for (let y=0;y<h;y++) for (let x=0;x<w;x++){
const i=y*w+x,k=i*4;
if (a[i]<128) continue;
const r=p[k],g=p[k+1],b=p[k+2],mx=Math.max(r,g,b);
if (mx<=17){
// the dark outer outline is dropped: birds read without an outline.
if (clear(x+2,y)||clear(x-2,y)||clear(x,y+2)||clear(x,y-2)){p[k+3]=0;n++;}
}else if (r+20<b&&g<=b*0.8&&mx>=38&&mx<=158){
const t=Math.min(1,Math.max(0,(mx/255-0.10)/0.35)),sm=t*t*(3-2*t);
p[k]=0;p[k+1]=0;p[k+2]=Math.round(40+215*sm);
}
}
sheet.rimTexels=n;
return sheet;
}
export async function loadArt(base,fetchJson){

const[rear,near,islands,metadata,bird]=await Promise.all([
loadImage(base,ART.rear,WORLD_PLATE_W,WORLD_PLATE_H),
loadImage(base,ART.near,WORLD_PLATE_W,WORLD_PLATE_H),
loadImage(base,ART.islands,ISLAND_SHEET.w,ISLAND_SHEET.h),
fetchJson(ART.metadata),
loadImage(base,ART.bird,1536,1152).then(markJousterRims),
]);
validateArcadeArt({rear,near,islands,metadata});
return{rear,near,islands,islandSpec:metadata,bird};
}
export const ARCADE_REAR_HORIZON=1682;
const ARCADE_GLOBE=Object.freeze({cx:608,cy:254,r:118,homeFrom:-50,homeSpan:88,periods:18,turnSeconds:120,crossfade:7,mode:'COLOUR'});
export const MOON_TURN_PER_TICK=1/(ARCADE_GLOBE.turnSeconds*60),MOON_BEAT_SURGE=5;
export function buildArcadeGlobe(rear){
if (!rear||rear.w!==768||rear.h!==2304) return null;
const G=ARCADE_GLOBE,W=GLOBE_MAP_W,H=GLOBE_MAP_H;
const x0=Math.max(0,Math.floor(G.cx-G.r-40)),x1=Math.min(rear.w,Math.ceil(G.cx+G.r+40));
const y0=Math.max(0,Math.floor(G.cy-G.r-40)),y1=Math.min(rear.h,Math.ceil(G.cy+G.r+40));
const bw=x1-x0,bh=y1-y0,n=bw*bh;
const col=new Float32Array(n*3),lum=new Float32Array(n),mask=new Float32Array(n);
for (let y=0;y<bh;y++) for (let x=0;x<bw;x++){
const i=y*bw+x,q=((y+y0)*rear.w+x+x0)*4;
const r=rear.p[q]/255,g=rear.p[q+1]/255,b=rear.p[q+2]/255;
const nx=(x+x0+0.5-G.cx)/G.r,ny=(y+y0+0.5-G.cy)/G.r;
const m=nx*nx+ny*ny<1?1:0;
mask[i]=m;col[i*3]=r*m;col[i*3+1]=g*m;col[i*3+2]=b*m;
lum[i]=0.2126*r+0.7152*g+0.0722*b;
}
const blur=(src,k,rad)=>{
let a=src,out=new Float32Array(a.length);
for (let pass=0;pass<2;pass++){
for (const horiz of[true,false]){
const len=horiz?bw:bh,lines=horiz?bh:bw;
for (let l=0;l<lines;l++) for (let c=0;c<k;c++){
const idx=(t)=>(horiz?l*bw+Math.min(len-1,Math.max(0,t)):Math.min(len-1,Math.max(0,t))*bw+l)*k+c;
let acc=0;
for (let t=-rad;t<=rad;t++) acc+=a[idx(t)];
for (let t=0;t<len;t++){
out[idx(t)]=acc/(2*rad+1);
acc+=a[idx(t+rad+1)]-a[idx(t-rad)];
}
}
[a,out]=[out,a===src?new Float32Array(a.length):a];
}
}
return a;
};
const num=blur(col,3,16),den=blur(mask,1,16);
const light=new Float32Array(n*3),detail=new Float32Array(n);
for (let i=0;i<n;i++){
const d=Math.max(den[i],1e-3);
light[i*3]=num[i*3]/d;light[i*3+1]=num[i*3+1]/d;light[i*3+2]=num[i*3+2]/d;
const lb=0.2126*light[i*3]+0.7152*light[i*3+1]+0.0722*light[i*3+2];
detail[i]=lum[i]/Math.max(lb,0.02);
}
const at=(arr,lon,lat,k=1,c=0)=>{
const x=Math.floor(G.cx+G.r*Math.cos(lat)*Math.sin(lon))-x0;
const y=Math.floor(G.cy+G.r*Math.sin(lat))-y0;
const i=Math.min(bh-1,Math.max(0,y))*bw+Math.min(bw-1,Math.max(0,x));
return arr[i*k+c];
};
const D2R=Math.PI/180,P=2*Math.PI/G.periods,X=G.crossfade*D2R;
const home0=G.homeFrom*D2R,home1=home0+G.homeSpan*D2R,end=home0+2*Math.PI;
const regions=[[home0,home1,0]];
for (let d=home1,k=3;d<end-1e-6;d+=2*P,k+=2) regions.push([d,Math.min(d+2*P,end),k*P]);
const out={w:W,h:H,p:new Uint8Array(W*H*4)};
for (let v=0;v<H;v++){
const lat=((v+0.5)/H-0.5)*Math.PI;
for (let u=0;u<W;u++){
const lon0=((u+0.5)/W)*2*Math.PI-Math.PI;
const lon=((lon0-home0)%(2*Math.PI)+2*Math.PI)%(2*Math.PI)+home0;
let ri=0;
while (ri<regions.length-1&&lon>=regions[ri][1]) ri++;
const[,b,off]=regions[ri];
const nextOff=ri+1<regions.length?regions[ri+1][2]:2*Math.PI;
const w=Math.min(1,Math.max(0,(lon-(b-X))/X));
const dv=at(detail,lon-off,lat)*(1-w)+at(detail,lon-nextOff,lat)*w;
const o=(v*W+u)*4;
if (G.mode==='COLOUR'){
out.p[o]=255;
for (let c=0;c<3;c++) out.p[o+1+c]=Math.round(Math.min(1,at(col,lon-off,lat,3,c)*(1-w)+at(col,lon-nextOff,lat,3,c)*w)*255);
continue;
}
out.p[o]=Math.round(Math.min(1,dv/4)*255);
if (Math.abs(lon0)<=Math.PI/2){
out.p[o+1]=Math.round(Math.min(1,at(light,lon0,lat,3,0))*255);
out.p[o+2]=Math.round(Math.min(1,at(light,lon0,lat,3,1))*255);
out.p[o+3]=Math.round(Math.min(1,at(light,lon0,lat,3,2))*255);
}
}
}
out.params=[G.cx,G.cy,G.mode==='COLOUR'?-G.r:G.r,2*Math.PI/(G.turnSeconds*60)];
return out;
}
