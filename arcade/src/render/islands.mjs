// STRUTHIO ARCADE · island art: fit the island masters to platforms and bake
// resampled copies into the atlas (identical islands share one bake).
const ISLAND_SHEET=Object.freeze({w:1920,h:480});
function platformHash(platform){
let h=17;
for (const c of platform.id||'') h=(h*33+c.charCodeAt(0))&255;
return h;
}
function islandFamily(platform){
const w=platform.rect[2];
if (platform.id==='GROUND'||w>=200) return 'BASE_GROUND';
return w<=64?'SMALL':w<=76?'MEDIUM':w<=90?'LARGE':'WIDE';
}
function canOverlap(a,b,amp){
const ax=a.rect[0],bx=b.rect[0];
const envelope=(p)=>p.motion==='MOVE_X'?amp:p.motion&&typeof p.motion==='object'&&(p.motion.profile==='DRIFT_X_SOFT'||p.motion.profile==='HOLD_SHIFT_X')?p.motion.amplitude||0:0;
const aa=envelope(a),ba=envelope(b);
for (let shift=-256;shift<=256;shift+=256)
if (ax-aa<bx+shift+b.rect[2]+ba&&ax+a.rect[2]+aa>bx+shift-ba) return true;
return false;
}
function visualClearanceBelow(platform,content,scaleY=1){
let gap=Infinity;
const amp=content.hazard?.amplitude||0;
const low=platform.rect[1]+(platform.motion==='GROW'?amp:0);
for (const other of content.platforms){
if (other.id===platform.id||other.rect[1]<=platform.rect[1]) continue;
if (canOverlap(platform,other,amp)) gap=Math.min(gap,(other.rect[1]-low)*scaleY-4);
}
return Math.max(0,gap);
}
function planFor(p,master,mirror,clearance,extra={}){
const naturalDepth=(master.h-master.capTop)*p.rect[2]/master.w;
return{family:islandFamily(p),id:master.id,master,mirror,seed:platformHash(p),clearance,naturalDepth,depth:Math.min(naturalDepth,clearance),ground:false,...extra};
}
// Every tower island names its art master (p.look) and mirroring; the ground
// uses the GROUND master. Depth is clipped to the clear space below.
function buildIslandLayout(content,masters,scaleY=1){
const map=new Map(),byId=new Map(masters.map(m=>[m.id,m]));
const groundMaster=masters.find((master)=>master.role==='GROUND');
if (!groundMaster) throw new Error('ISLAND_MASTER_CONTRACT');
for (const p of content.platforms){
if (islandFamily(p)==='BASE_GROUND'){
map.set(p.id,Object.freeze({family:'BASE_GROUND',id:groundMaster.id,master:groundMaster,mirror:false,seed:platformHash(p),clearance:38,naturalDepth:38,depth:38,ground:true}));
continue;
}
const master=byId.get(p.look);
if (!master) throw new Error(`ISLAND_LOOK_MISSING ${p.id}`);
map.set(p.id,Object.freeze(planFor(p,master,!!p.mirror,visualClearanceBelow(p,content,scaleY))));
}
return map;
}
const CAP_ROWS=22;
function islandGeometry(plan,width){
const m=plan.master,rows=m.h-m.capTop;
const H=Math.max(2,Math.round(plan.depth*3)),depth=H/3;
const capH=Math.max(1,Math.round(Math.min(7,depth*.5)*3)),capDepth=capH/3;
const decorH=m.topDecor?Math.max(1,Math.round(m.topDecor*width/m.w*3)):0;
return{W:width*3,H,capH,depth,capDepth,decorH,decorDepth:decorH/3,bodyScale:(depth-capDepth)/(rows-CAP_ROWS),sx:width/m.w,sy:depth/rows};
}
function areaTaps(nSrc,nDst){
const s=nSrc/nDst,taps=[];
for (let i=0;i<nDst;i++){
const a=i*s,b=(i+1)*s,row=[];
let sum=0;
for (let j=Math.floor(a);j<Math.min(nSrc,Math.ceil(b));j++){
const w=Math.min(b,j+1)-Math.max(a,j);
if (w>1e-6){row.push(j,w);sum+=w;}
}
for (let k=1;k<row.length;k+=2) row[k]/=sum;
taps.push(row);
}
return taps;
}
function resampleSlice(dst,dx,dy,W,H,sheet,sx,sy,sw,sh,mirror){
const tx=areaTaps(sw,W),ty=areaTaps(sh,H),tmp=new Float32Array(sh*W*4);
for (let y=0;y<sh;y++){
const row=((sy+y)*sheet.w+sx)*4;
for (let x=0;x<W;x++){
let r=0,g=0,b=0,a=0;
const t=tx[x];
for (let k=0;k<t.length;k+=2){
const i=row+(mirror?sw-1-t[k]:t[k])*4,al=sheet.p[i+3]*t[k+1];
r+=sheet.p[i]*al;g+=sheet.p[i+1]*al;b+=sheet.p[i+2]*al;a+=al;
}
const o=(y*W+x)*4;
tmp[o]=r;tmp[o+1]=g;tmp[o+2]=b;tmp[o+3]=a;
}
}
for (let y=0;y<H;y++){
const t=ty[y];
for (let x=0;x<W;x++){
let r=0,g=0,b=0,a=0;
for (let k=0;k<t.length;k+=2){
const i=(t[k]*W+x)*4,w=t[k+1];
r+=tmp[i]*w;g+=tmp[i+1]*w;b+=tmp[i+2]*w;a+=tmp[i+3]*w;
}
const o=((dy+y)*dst.w+dx+x)*4,alpha=Math.round(a);
if (alpha<2){dst.p[o]=dst.p[o+1]=dst.p[o+2]=dst.p[o+3]=0;continue;}
dst.p[o]=Math.round(r/a);dst.p[o+1]=Math.round(g/a);dst.p[o+2]=Math.round(b/a);dst.p[o+3]=alpha;
}
}
}
function bakeIslandLayout(layout,platforms,surface,origin,region){
const[rx,ry,rw,rh]=region;
for (let y=ry;y<ry+rh;y++) surface.p.fill(0,(y*surface.w+rx)*4,(y*surface.w+rx+rw)*4);
const items=platforms.map((p)=>({p,plan:layout.get(p.id)})).filter((it)=>it.plan&&!it.plan.ground)
.map((it)=>({...it,g:islandGeometry(it.plan,it.p.rect[2])}))
.sort((a,b)=>(b.g.H+b.g.decorH)-(a.g.H+a.g.decorH)||b.g.W-a.g.W);
const slots=new Map(),sheet={w:surface.w,p:surface.p},shared=new Map();
let x=0,y=0,shelf=0;
for (const{p,plan,g}of items){
const key=`${plan.id}/${plan.mirror?1:0}/${g.W}x${g.H}+${g.decorH}`;
if (shared.has(key)){slots.set(p.id,shared.get(key));continue;}
const tall=g.H+g.decorH;
if (x+g.W>rw){x=0;y+=shelf+2;shelf=0;}
if (y+tall>rh||g.W>rw) continue;
const m=plan.master,dx=rx+x,dy=ry+y;
const sx=origin[0]+m.x,capY=origin[1]+m.y+m.capTop;
if (g.decorH) resampleSlice(surface,dx,dy,g.W,g.decorH,sheet,sx,origin[1]+m.y,m.w,m.topDecor,plan.mirror);
const by=dy+g.decorH;
resampleSlice(surface,dx,by,g.W,g.capH,sheet,sx,capY,m.w,CAP_ROWS,plan.mirror);
resampleSlice(surface,dx,by+g.capH,g.W,g.H-g.capH,sheet,sx,capY+CAP_ROWS,m.w,m.h-m.capTop-CAP_ROWS,plan.mirror);
const slot=Object.freeze({x:dx,y:by,w:g.W,h:g.H,decorY:dy,decorH:g.decorH});
slots.set(p.id,slot);shared.set(key,slot);
x+=g.W+2;shelf=Math.max(shelf,tall);
}
return slots;
}
function runsAt(plate,m,row){
const runs=[];let start=-1;
for (let x=0;x<=m.w;x++){
const i=((row+m.y)*plate.w+m.x+x)*4;
const yes=x<m.w&&plate.p[i+3]>=128;
if (yes&&start<0) start=x;
if (!yes&&start>=0){runs.push([start,x]);start=-1;}
}
return runs;
}
function lipFit(plate,m){
if (m.x<0||m.y<0||m.w<1||m.h<1||m.x+m.w>plate.w||m.y+m.h>plate.h) throw new Error(`ISLAND_MASTER_BOUNDS ${m.id}`);
let l=m.w,r=0;
for (let row=Math.max(0,m.capTop-1);row<=Math.min(m.h-1,m.capTop+1);row++){
for (let x=0;x<m.w;x++) if (plate.p[((m.y+row)*plate.w+m.x+x)*4+3]>=128){l=Math.min(l,x);r=Math.max(r,x+1);}
}
if (r-l<8) throw new Error(`ISLAND_LIP_MISSING ${m.id}`);
return{...m,x:m.x+l,w:r-l,box:{x:m.x,w:m.w},signalRects:(m.signalRects||[]).map((q)=>({...q,x:q.x-l}))};
}
function measureIslands(plate,metadata){
if (plate.w!==ISLAND_SHEET.w||plate.h!==ISLAND_SHEET.h) throw new Error('ISLANDS_SIZE');
const variants=metadata.masters;
const topDecorV1=metadata?.rendererExtension==='topDecorV1';
return variants.map(source=>{
const m=topDecorV1?lipFit(plate,source):source;
if (m.x<0||m.y<0||m.w<1||m.h<1||m.x+m.w>plate.w||m.y+m.h>plate.h) throw new Error(`ISLAND_MASTER_BOUNDS ${m.id}`);
const opaqueRuns=[];
for (let y=0;y<m.h;y++){
opaqueRuns.push(runsAt(plate,m,y));
}
const signalRects=(m.signalRects||[]).map((rect)=>({x:rect.x,y:rect.y,w:rect.w,h:rect.h}));
const topDecor=topDecorV1?Math.max(0,Math.min(m.capTop,Math.trunc(m.topDecorRows??m.capTop))):0;
return{...m,capRows:22,opaqueRuns,signalRects,topDecor};
});
}
export{measureIslands,ISLAND_SHEET,buildIslandLayout,bakeIslandLayout,islandGeometry};
