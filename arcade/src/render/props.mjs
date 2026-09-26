// STRUTHIO ARCADE · props painted into the atlas: eggs (whole, cracking, open)
// and the arrival shimmer.
const PROPS_ORIGIN=Object.freeze([1024,392]);
const[PX0,PY0]=PROPS_ORIGIN;
const EGG_CELL=36;
const EGG_FRAMES=Object.freeze({INTACT:0,CRACK1:1,CRACK2:2,OPEN:3,TILT_L:4,TILT_R:5});
const SHIMMER_CELL=96;
const SHIMMER_Y=PY0+224;
const eggSource=(f)=>[PX0+f*EGG_CELL,PY0];
const shimmerSource=(f)=>[PX0+(f&3)*SHIMMER_CELL,SHIMMER_Y];
const SS=4;
function over(s,x,y,rgb,a){
if (a<=0.004||x<0||y<0||x>=s.w||y>=s.h) return;
const i=(y*s.w+x)*4,p=s.p;
const da=p[i+3]/255,sa=Math.min(1,a);
const oa=sa+da*(1-sa);
for (let k=0;k<3;k++) p[i+k]=Math.round((rgb[k]*sa+p[i+k]*da*(1-sa))/Math.max(oa,1e-6));
p[i+3]=Math.round(oa*255);
}
class Pen{
constructor(s,ox,oy,k,{clip=null,rot=0,pivot=[0,0]}={}){
this.s=s;this.ox=ox;this.oy=oy;this.k=k;this.clip=clip;
this.cos=Math.cos(rot);this.sin=Math.sin(rot);this.pivot=pivot;
}
map([x,y]){
const[px,py]=this.pivot;
const dx=x-px,dy=y-py;
return[this.ox+(px+dx*this.cos-dy*this.sin)*this.k,this.oy+(py+dx*this.sin+dy*this.cos)*this.k];
}
poly(points,c,alpha=1){
if (!c) return;
const pts=points.map((p)=>this.map(p));
let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
for (const[x,y] of pts){minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
const clip=this.clip;
const x0=Math.max(Math.floor(minX),clip?clip[0]:0),x1=Math.min(Math.ceil(maxX),clip?clip[0]+clip[2]:this.s.w);
const y0=Math.max(Math.floor(minY),clip?clip[1]:0),y1=Math.min(Math.ceil(maxY),clip?clip[1]+clip[3]:this.s.h);
for (let py=y0;py<y1;py++){
const rows=[];
for (let sy=0;sy<SS;sy++){
const yy=py+(sy+.5)/SS,xs=[];
for (let i=0,j=pts.length-1;i<pts.length;j=i++){
const a=pts[i],b=pts[j];
if ((a[1]>yy)!==(b[1]>yy)) xs.push(a[0]+(yy-a[1])*(b[0]-a[0])/(b[1]-a[1]));
}
xs.sort((p,q)=>p-q);
rows.push(xs);
}
for (let px=x0;px<x1;px++){
let cover=0;
for (const xs of rows) for (let sx=0;sx<SS;sx++){
const xx=px+(sx+.5)/SS;
let inside=false;
for (let i=0;i<xs.length;i+=2) if (xx>=xs[i]&&xx<xs[i+1]){inside=true;break;}
if (inside) cover++;
}
if (cover) over(this.s,px,py,c,alpha*cover/(SS*SS));
}
}
}
ellipse(cx,cy,rx,ry,c,alpha=1,n=28){
const pts=[];
for (let i=0;i<n;i++){const a=i/n*Math.PI*2;pts.push([cx+Math.cos(a)*rx,cy+Math.sin(a)*ry]);}
this.poly(pts,c,alpha);
}
line(x0,y0,x1,y1,w,c,alpha=1){
const dx=x1-x0,dy=y1-y0,len=Math.hypot(dx,dy)||1;
const nx=-dy/len*w/2,ny=dx/len*w/2;
this.poly([[x0+nx,y0+ny],[x1+nx,y1+ny],[x1-nx,y1-ny],[x0-nx,y0-ny]],c,alpha);
}
}
function paintEgg(s,C,f){
const[ox,oy]=eggSource(f);
const tilt=f===EGG_FRAMES.TILT_L?-.22:f===EGG_FRAMES.TILT_R?.22:0;
const pen=new Pen(s,ox,oy,3,{clip:[ox,oy,EGG_CELL,EGG_CELL],rot:tilt,pivot:[6,11.6]});
const cx=6,cy=7.6;
new Pen(s,ox,oy,3,{clip:[ox,oy,EGG_CELL,EGG_CELL]}).ellipse(6,11.55,3.6,.55,C.ink,.55);
const open=f===EGG_FRAMES.OPEN;
const shell=[];
for (let i=0;i<32;i++){
const a=i/32*Math.PI*2,sy=Math.sin(a);
const rx=3.45*(sy<0?1+sy*.16:1);
shell.push([cx+Math.cos(a)*rx,cy+sy*4.05]);
}
pen.poly(shell.map(([x,y])=>[cx+(x-cx)*1.08,cy+(y-cy)*1.05]),C.ink);
if (open){
pen.ellipse(cx,cy+.2,2.6,2.1,C.voidDeep);
pen.poly([[cx-2.4,cy-.6],[cx-1.2,cy-2.6],[cx-.5,cy-1.6],[cx+.5,cy-2.8],[cx+1.3,cy-1.5],[cx+2.4,cy-.6],[cx+2.2,cy+1],[cx-2.2,cy+1]],C.voidDeep);
}
pen.poly(open?[...shell.filter(([,y])=>y>cy-.2)].sort((a,b)=>Math.atan2(a[1]-cy,a[0]-cx)-Math.atan2(b[1]-cy,b[0]-cx)).concat([[cx-3.3,cy-.2],[cx-2,cy-1.4],[cx-1,cy-.5],[cx,cy-1.6],[cx+1.2,cy-.4],[cx+2.3,cy-1.3],[cx+3.3,cy-.2]]):shell,C.ivory);
pen.poly([[cx+1.6,cy-3],[cx+3.4,cy-.5],[cx+3.1,cy+2.6],[cx+1.2,cy+4],[cx-1.4,cy+4],[cx+1.6,cy+2.4],[cx+2.3,cy-.4]],C.ivoryDark,.85);
if (!open) pen.ellipse(cx-1.25,cy-2.1,.8,1.25,C.ivoryLight,.95);
for (const[x,y,c,r] of[[-1.6,.8,C.ring,.6],[1.1,-1.2,C.kingdomGold,.5],[.4,2.2,C.ringLight,.5],[-.4,-2.6,C.ring,.4],[2,1,C.ringLight,.38],[-2,-.6,C.ringDark,.34]]){
if (open&&y<-.3) continue;
pen.ellipse(cx+x,cy+y,r,r,c);
}
if (f===EGG_FRAMES.CRACK1||f===EGG_FRAMES.CRACK2){
const crack=[[cx-.4,cy-3.6],[cx+.4,cy-2.2],[cx-.6,cy-1.1],[cx+.6,cy+.3]];
for (let i=1;i<crack.length;i++) pen.line(...crack[i-1],...crack[i],.42,C.ink);
if (f===EGG_FRAMES.CRACK2){
for (let i=1;i<crack.length;i++) pen.line(...crack[i-1],...crack[i],.16,C.ringLight);
const b=[[cx+.6,cy+.3],[cx+1.8,cy+1],[cx+2.6,cy+.4]];
for (let i=1;i<b.length;i++) pen.line(...b[i-1],...b[i],.36,C.ink);
pen.line(cx-.6,cy-1.1,cx-2,cy-.3,.34,C.ink);
}
}
if (open){
pen.ellipse(cx,cy-.4,1.9,1.3,C.ringDeep);
pen.ellipse(cx,cy-.2,1.2,.8,C.ringDark,.8);
pen.line(cx-.8,cy-.4,cx+.8,cy-.4,.22,C.ring);
pen.poly([[cx-2.6,cy-4.2],[cx-.6,cy-5.2],[cx+1.6,cy-4.6],[cx+.4,cy-3.6],[cx-.8,cy-4]],C.ivoryLight);
}
}
function paintShimmer(s,C,f){
const[ox,oy]=shimmerSource(f);
const pen=new Pen(s,ox,oy,3,{clip:[ox,oy,SHIMMER_CELL,SHIMMER_CELL]});
const cx=15;
const segs=[[1,4],[6,3],[11,5],[18,3],[23,6],[30,2]];
segs.forEach(([y,h],i)=>{
const on=(i+f)%4!==0;
const jitter=((i*7+f*3)%5-2)*.35;
pen.line(cx+jitter,y,cx+jitter,y+h,on?1.5:.8,on?C.cyanLight:C.cyanDeep,on?.95:.7);
if (on) pen.line(cx+jitter,y,cx+jitter,y+h,3.6,C.cyan,.22);
});
const ticks=[[5,8,-1],[9,15,1],[3,22,-1],[7,27,1]];
ticks.forEach(([w,y,side],i)=>{
const k=(i+f)&3;
pen.line(cx+side*1.5,y,cx+side*(1.5+w*(k?1:.5)),y,.9,k===1?C.chromeLight:C.cyanDark,.9);
});
for (let i=0;i<7;i++){
const a=i*2.39+f*.7,r=5+((i*5+f*3)%7);
pen.ellipse(cx+Math.cos(a)*r*.8,16+Math.sin(a)*r*1.4,.45,.45,i%3?C.cyanLight:C.white,.9);
}
}
function paintHdProps(s,C){
for (let f=0;f<6;f++) paintEgg(s,C,f);
for (let f=0;f<4;f++) paintShimmer(s,C,f);

}
export{paintHdProps,eggSource,shimmerSource,EGG_FRAMES,EGG_CELL,SHIMMER_CELL};
