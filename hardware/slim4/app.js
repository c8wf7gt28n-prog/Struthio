(() => {
  'use strict';
  const $ = s => document.querySelector(s);
  const canvas = $('#view');
  const ctx = canvas.getContext('2d', { alpha: true });
  const baseModel = structuredClone(window.STRUTHIO_MODEL);
  let model = structuredClone(baseModel);

  const state = {
    yaw: -0.64,
    pitch: 0.82,
    dist: 290,
    target: {x:0,y:0,z:0},
    mode: 'SOLID',
    grid: true,
    labels: false,
    shell: true,
    explode: 0,
    slice: 14,
    layers: {pcb:true,parts:true,frontParts:true,backParts:true,copper:true,display:false,lens:false,acrylic:true,battery:false,speakers:false,controls:false,rear:false,routes:false},
    groupVisibility: {case:true,pcb:true,acrylic:true},
    authority: {pcb:true,case:true,art:true},
    referenceMode: false,
    partSideFilter: 'all',
    copperFilter: 'all',
    stackKey: 'build.assembled',
    selected: {type:'board', ref:'BOARD'},
    pointers: new Map(),
    gestureMoved: false,
    pinchStart: null,
    dirty: true,
    renderQueued: false,
    centers: []
  };

  const COLORS = {
    bg:'#061416', grid:'rgba(66,217,210,.14)', axisX:'#ef6a56', axisY:'#9bdc68', axisZ:'#42d9d2',
    pcb:'#496f58', pcbEdge:'#98c59a', shell:'#c9c2ae', display:'#5eb7c7', battery:'#b8b9b3', speaker:'#252c31', control:'#e48725',
    ic:'#2d343a', connector:'#707881', switch:'#d67b21', capacitor:'#7fa58f', resistor:'#b6a77b', inductor:'#8c6f49', diode:'#835d67', transistor:'#586574', other:'#67727a', selected:'#ffd66a', copperF:'#e0a34a', copperB:'#b87943', copperI:'#725d91', via:'#d8b56c', pad:'#e5bc67'
  };

  function clone(o){ return JSON.parse(JSON.stringify(o)); }
  function clamp(v,a,b){ return Math.max(a,Math.min(b,v)); }
  function vsub(a,b){ return {x:a.x-b.x,y:a.y-b.y,z:a.z-b.z}; }
  function vadd(a,b){ return {x:a.x+b.x,y:a.y+b.y,z:a.z+b.z}; }
  function vmul(a,s){ return {x:a.x*s,y:a.y*s,z:a.z*s}; }
  function dot(a,b){ return a.x*b.x+a.y*b.y+a.z*b.z; }
  function cross(a,b){ return {x:a.y*b.z-a.z*b.y,y:a.z*b.x-a.x*b.z,z:a.x*b.y-a.y*b.x}; }
  function norm(a){ const m=Math.hypot(a.x,a.y,a.z)||1; return {x:a.x/m,y:a.y/m,z:a.z/m}; }

  function modelCenter(){
    const b=model.board.bbox; return {x:(b[0]+b[2])/2,y:(b[1]+b[3])/2};
  }
  function W(x,y,z){ const c=modelCenter(); return {x:x-c.x,y:-(y-c.y),z}; }

  function cameraBasis(){
    const cp=Math.cos(state.pitch), sp=Math.sin(state.pitch);
    const cam = {
      x:state.target.x + state.dist*cp*Math.sin(state.yaw),
      y:state.target.y + state.dist*cp*Math.cos(state.yaw),
      z:state.target.z + state.dist*sp
    };
    const f=norm(vsub(state.target,cam));
    // Roll-free orbit: screen-right comes straight from yaw, so the view never snaps near the top or bottom pole.
    const r={x:-Math.cos(state.yaw),y:Math.sin(state.yaw),z:0};
    const u=norm(cross(r,f));
    return {cam,f,r,u};
  }

  function project(p,basis,w,h){
    const rel=vsub(p,basis.cam);
    const depth=dot(rel,basis.f);
    if(depth<2) return null;
    const fpx=(Math.min(w,h)*0.5)/Math.tan(34*Math.PI/360);
    const sc=fpx/depth;
    return {x:w/2+dot(rel,basis.r)*sc,y:h/2-dot(rel,basis.u)*sc,depth,scale:sc};
  }

  function rgba(hex,a){
    const h=hex.replace('#',''); const n=parseInt(h,16); return `rgba(${(n>>16)&255},${(n>>8)&255},${n&255},${a})`;
  }

  function faceColor(hex, shade){
    const h=hex.replace('#',''); const n=parseInt(h,16);
    const r=clamp(((n>>16)&255)*shade,0,255)|0, g=clamp(((n>>8)&255)*shade,0,255)|0, b=clamp((n&255)*shade,0,255)|0;
    return `rgb(${r},${g},${b})`;
  }

  function rotatedRect(cx,cy,w,h,deg){
    const a=deg*Math.PI/180,c=Math.cos(a),s=Math.sin(a), hw=w/2,hh=h/2;
    return [[-hw,-hh],[hw,-hh],[hw,hh],[-hw,hh]].map(([x,y])=>[cx+x*c-y*s,cy+x*s+y*c]);
  }

  function boxFaces(o){
    let z0=o.z0, z1=o.z1;
    if(z0>=state.slice) return [];
    z1=Math.min(z1,state.slice);
    if(z1<=z0) return [];
    const pts=rotatedRect(o.x,o.y,o.w,o.h,o.rot||0);
    const b=pts.map(p=>W(p[0],p[1],z0)), t=pts.map(p=>W(p[0],p[1],z1));
    const faces=[
      {pts:t,shade:1.04},{pts:[b[3],b[2],b[1],b[0]],shade:.62},
      {pts:[b[0],b[1],t[1],t[0]],shade:.77},{pts:[b[1],b[2],t[2],t[1]],shade:.68},
      {pts:[b[2],b[3],t[3],t[2]],shade:.72},{pts:[b[3],b[0],t[0],t[3]],shade:.84}
    ];
    return faces;
  }

  function cylinderFaces(o, n=20){
    let z0=o.z0,z1=o.z1;
    if(z0>=state.slice) return [];
    z1=Math.min(z1,state.slice); if(z1<=z0)return [];
    const ring=[]; for(let i=0;i<n;i++){const a=i*Math.PI*2/n;ring.push([o.x+o.r*Math.cos(a),o.y+o.r*Math.sin(a)]);}
    const b=ring.map(p=>W(p[0],p[1],z0)),t=ring.map(p=>W(p[0],p[1],z1));
    const f=[{pts:t,shade:1.06},{pts:[...b].reverse(),shade:.58}];
    for(let i=0;i<n;i++){let j=(i+1)%n;f.push({pts:[b[i],b[j],t[j],t[i]],shade:.72+.12*Math.cos(i*Math.PI*2/n)});}
    return f;
  }

  function prismFaces(outer,holes,z0,z1){
    if(z0>=state.slice)return [];
    z1=Math.min(z1,state.slice); if(z1<=z0)return [];
    const ot=outer.map(p=>W(p[0],p[1],z1)), ob=outer.map(p=>W(p[0],p[1],z0));
    const ht=holes.map(h=>h.map(p=>W(p[0],p[1],z1))), hb=holes.map(h=>h.map(p=>W(p[0],p[1],z0)));
    const faces=[{special:'topWithHoles',outer:ot,holes:ht,shade:1.0},{special:'bottomWithHoles',outer:[...ob].reverse(),holes:hb.map(h=>[...h].reverse()),shade:.6}];
    for(let i=0;i<outer.length;i++){let j=(i+1)%outer.length;faces.push({pts:[ob[i],ob[j],ot[j],ot[i]],shade:.72});}
    holes.forEach((h,hi)=>{for(let i=0;i<h.length;i++){let j=(i+1)%h.length;faces.push({pts:[hb[hi][i],ht[hi][i],ht[hi][j],hb[hi][j]],shade:.52});}});
    return faces;
  }

  function addObjectFaces(cmds,obj,faces,color,alpha,ref,type,group){
    faces.forEach(f=>{
      const all=f.pts || (f.outer ? f.outer.concat(...f.holes):[]);
      const depth=all.length?all.reduce((s,p)=>s+p.z,0):0; // placeholder; replaced after projection
      cmds.push({...f,color,alpha,ref,type,group,obj,depth});
    });
  }

  function partColor(cat){return COLORS[cat]||COLORS.other;}
  function partHeight(p){return p.z||1;}
  function explodeOffset(group,side){
    const e=state.explode;
    if(group==='acrylic')return e*1.0;
    if(group==='controls')return e*.9;
    if(group==='shell')return e*.75;
    if(group==='lens')return e*.62;
    if(group==='display')return e*.55;
    if(group==='routes')return e*.2;
    if(group==='battery')return -e*.55;
    if(group==='speakers')return -e*.34;
    if(group==='rear')return -e*.9;
    if(group==='parts')return (side==='back'?-1:1)*e*.13;
    return 0;
  }

  function buildCommands(){
    const cmds=[];
    if(state.groupVisibility.pcb && state.layers.pcb){
      const zoff=0;
      const faces=prismFaces(model.board.outer,model.board.holes||[],0+zoff,model.board.thickness+zoff);
      addObjectFaces(cmds,{ref:'BOARD'},faces,COLORS.pcb,1,'BOARD','board','pcb');
    }
    if(state.groupVisibility.pcb && state.layers.parts){
      for(const p of model.parts){
        const side=p.side||'front'; if(state.partSideFilter!=='all' && side!==state.partSideFilter)continue; if(side==='front'&&!state.layers.frontParts || side==='back'&&!state.layers.backParts)continue; const off=explodeOffset('parts',side);
        const h=partHeight(p); let z0,z1;
        if(side==='back'){z1=0+off;z0=-h+off;}else{z0=model.board.thickness+off;z1=z0+h;}
        const o={x:p.x,y:p.y,w:p.w,h:p.h,rot:p.rot||0,z0,z1};
        addObjectFaces(cmds,p,boxFaces(o),partColor(p.category),.96,p.ref,'part','parts');
      }
    }
    const m=model.mechanical||{};
    const allowMechanical=state.groupVisibility.case&&(state.authority.case||state.referenceMode);
    const cad=cadParts();
    if(cad){
      const enabled={shell:state.shell,display:state.layers.display,lens:state.layers.lens,acrylic:state.authority.art&&state.groupVisibility.acrylic&&state.layers.acrylic,battery:state.layers.battery,speakers:state.layers.speakers,controls:state.layers.controls,rear:state.layers.rear,routes:state.layers.routes};
      for(const item of cad){if(!enabled[item.group])continue;const off=explodeOffset(item.group);const faces=[];for(const tri of item.triangles){if(!tri.p.every(v=>v[2]<state.slice))continue;const pts=tri.p.map(v=>W(v[0],v[1],v[2]+off));faces.push({pts,shade:tri.s});}addObjectFaces(cmds,{ref:item.name},faces,item.color,item.opacity??1,item.name,'mechanical',item.group);}
    }else{
      if(allowMechanical && state.layers.display && m.display){const d=m.display,off=explodeOffset('display');addObjectFaces(cmds,{ref:'DISPLAY'},boxFaces({...d,z0:d.z0+off,z1:d.z0+d.d+off}),COLORS.display,.24,'DISPLAY','mechanical','display');}
      if(allowMechanical && state.layers.battery && m.battery){const d=m.battery,off=explodeOffset('battery');addObjectFaces(cmds,{ref:'BATTERY'},boxFaces({...d,z0:d.z0+off,z1:d.z0+d.d+off}),COLORS.battery,.88,'BATTERY','mechanical','battery');}
      if(allowMechanical && state.layers.speakers && m.speakers){m.speakers.forEach((d,i)=>{const off=explodeOffset('speakers');addObjectFaces(cmds,{ref:`SPK${i+1}`},boxFaces({...d,z0:d.z0+off,z1:d.z0+d.d+off}),COLORS.speaker,.98,`SPK${i+1}`,'mechanical','speakers');});}
      if(allowMechanical && state.layers.controls && m.buttons){m.buttons.forEach((d,i)=>{const off=explodeOffset('controls');const faces=d.kind==='round'?cylinderFaces({x:d.x,y:d.y,r:d.r,z0:d.z0+off,z1:d.z0+d.d+off}):boxFaces({x:d.x,y:d.y,w:d.w,h:d.h,rot:d.rot||0,z0:d.z0+off,z1:d.z0+d.d+off});addObjectFaces(cmds,{ref:d.label||`CTRL${i+1}`},faces,COLORS.control,1,d.label||`CTRL${i+1}`,'mechanical','controls');});}
    }
    return cmds;
  }

  function line3(a,b,color,width=1,alpha=1,basis=null,w=null,h=null){
    basis=basis||cameraBasis(); w=w||canvas.clientWidth; h=h||canvas.clientHeight;
    const p=project(a,basis,w,h),q=project(b,basis,w,h); if(!p||!q)return;
    ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);ctx.strokeStyle=rgba(color,alpha);ctx.lineWidth=width;ctx.stroke();
  }

  function drawGrid(basis,w,h){
    if(!state.grid)return;
    const b=model.board.bbox; const c=modelCenter();
    const minX=Math.floor((b[0]-15)/10)*10,maxX=Math.ceil((b[2]+15)/10)*10;
    const minY=Math.floor((b[1]-15)/10)*10,maxY=Math.ceil((b[3]+15)/10)*10;
    const z=-5.2;
    ctx.save();
    for(let x=minX;x<=maxX;x+=10)line3(W(x,minY,z),W(x,maxY,z),'#42d9d2',x===0?1.5:.65,x===0?.48:.16,basis,w,h);
    for(let y=minY;y<=maxY;y+=10)line3(W(minX,y,z),W(maxX,y,z),'#42d9d2',y===0?1.5:.65,y===0?.48:.16,basis,w,h);
    line3(W(minX,c.y,z),W(maxX,c.y,z),COLORS.axisX,1.6,.7,basis,w,h);
    line3(W(c.x,minY,z),W(c.x,maxY,z),COLORS.axisY,1.6,.7,basis,w,h);
    line3(W(c.x,c.y,-6),W(c.x,c.y,18),COLORS.axisZ,1.7,.8,basis,w,h);
    ctx.restore();
  }

  function copperLayerZ(layer){
    const t=model.board.thickness||1.2;
    const order={'F.Cu':1.02,'In1.Cu':.84,'In2.Cu':.67,'In3.Cu':.50,'In4.Cu':.33,'In5.Cu':.16,'B.Cu':-.02};
    const q=order[layer];
    if(q===undefined)return t*.5;
    if(layer==='F.Cu')return t+.025;
    if(layer==='B.Cu')return -.025;
    return t*q;
  }

  function drawCopper(basis,w,h){
    if(!state.groupVisibility.pcb || !state.layers.copper)return;
    const segs=model.segments||[], vias=model.vias||[], pads=model.pads||[];
    if(!segs.length && !vias.length && !pads.length)return;
    const copperMode=state.mode==='COPPER', xray=state.mode==='XRAY';
    const viewerSide=basis.cam.z>=state.target.z?'front':'back';
    ctx.save();
    ctx.lineCap='round';ctx.lineJoin='round';
    // Copper pours: the filled zones stored in the board file (model.zones), drawn under the tracks.
    for(const zn of model.zones||[]){
      const isFront=zn.layer==='F.Cu',isBack=zn.layer==='B.Cu',isInternal=!isFront&&!isBack;
      if(state.copperFilter==='F.Cu'&&!isFront)continue;
      if(state.copperFilter==='B.Cu'&&!isBack)continue;
      if(state.copperFilter==='internal'&&!isInternal)continue;
      if(state.copperFilter==='pads')continue;
      if(state.mode==='SOLID' && ((viewerSide==='front'&&!isFront)||(viewerSide==='back'&&!isBack)))continue;
      if(state.mode==='WIRE' && isInternal)continue;
      const z=copperLayerZ(zn.layer); if(z>state.slice)continue;
      let ok=true;ctx.beginPath();
      for(const poly of zn.polys)for(const r of poly){
        for(let i=0;i<r.length;i+=2){const q=project(W(r[i],r[i+1],z),basis,w,h);if(!q){ok=false;break;}if(i)ctx.lineTo(q.x,q.y);else ctx.moveTo(q.x,q.y);}
        ctx.closePath();
      }
      if(!ok)continue;
      const col=isFront?COLORS.copperF:isBack?COLORS.copperB:COLORS.copperI;
      ctx.fillStyle=rgba(col,copperMode?.3:xray?.12:.08);ctx.fill('evenodd');
      ctx.strokeStyle=rgba(col,copperMode?.6:.3);ctx.lineWidth=.6;ctx.stroke();
    }
    for(const s of segs){
      const isFront=s.layer==='F.Cu',isBack=s.layer==='B.Cu',isInternal=!isFront&&!isBack;
      if(state.copperFilter==='F.Cu'&&!isFront)continue;
      if(state.copperFilter==='B.Cu'&&!isBack)continue;
      if(state.copperFilter==='internal'&&!isInternal)continue;
      if(state.copperFilter==='pads')continue;
      if(state.mode==='SOLID' && ((viewerSide==='front'&&!isFront)||(viewerSide==='back'&&!isBack)))continue;
      if(state.mode==='WIRE' && isInternal)continue;
      const z=copperLayerZ(s.layer); if(z>state.slice)continue;
      const p=project(W(s.x1,s.y1,z),basis,w,h),q=project(W(s.x2,s.y2,z),basis,w,h);if(!p||!q)continue;
      const col=isFront?COLORS.copperF:isBack?COLORS.copperB:COLORS.copperI;
      const alpha=copperMode?(isInternal?.54:.94):xray?(isInternal?.34:.67):.27;
      ctx.strokeStyle=rgba(col,alpha);
      ctx.lineWidth=clamp(s.w*(p.scale+q.scale)*.52,.45,copperMode?3.1:1.8);
      ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);ctx.stroke();
    }
    // Pads are deliberately simplified from KiCad pad definitions but preserve location, size, side, ref and net.
    for(const pd of pads){
      if(!['all','pads'].includes(state.copperFilter))continue;
      if(state.mode==='SOLID' && pd.side!=='both' && pd.side!==viewerSide)continue;
      const sides=pd.side==='both'?[viewerSide]:[pd.side];
      for(const side of sides){
        const z=side==='back'?-0.04:(model.board.thickness+.04);if(z>state.slice)continue;
        const pts=rotatedRect(pd.x,pd.y,pd.w,pd.h,pd.rot||0).map(v=>project(W(v[0],v[1],z),basis,w,h));
        if(pts.some(v=>!v))continue;
        const selected=state.selected?.type==='part' && pd.ref===state.selected.ref;
        ctx.beginPath();ctx.moveTo(pts[0].x,pts[0].y);for(let i=1;i<pts.length;i++)ctx.lineTo(pts[i].x,pts[i].y);ctx.closePath();
        ctx.fillStyle=rgba(selected?COLORS.selected:COLORS.pad,copperMode?.86:.34);ctx.fill();
      }
    }
    for(const v of vias){
      if(!['all','pads'].includes(state.copperFilter))continue;
      const z=Math.min(model.board.thickness+.055,state.slice);const p=project(W(v.x,v.y,z),basis,w,h);if(!p)continue;
      const r=clamp(v.size*p.scale*.5,.55,copperMode?4.2:2.4);
      ctx.beginPath();ctx.arc(p.x,p.y,r,0,Math.PI*2);ctx.fillStyle=rgba(COLORS.via,copperMode?.96:.47);ctx.fill();
      const rh=clamp(v.drill*p.scale*.5,.25,2.1);ctx.beginPath();ctx.arc(p.x,p.y,rh,0,Math.PI*2);ctx.fillStyle='rgba(4,11,12,.85)';ctx.fill();
    }
    ctx.restore();
  }

  function drawShell(basis,w,h){
    if(!state.groupVisibility.case || !state.shell || !(state.authority.case||state.referenceMode) || window.STRUTHIO_CASE_LAYER || window.STRUTHIO_CASE_R3 || !model.mechanical?.shell)return;
    const sh=model.mechanical.shell,o=sh.outline,z0=sh.z0,z1=Math.min(sh.z1,state.slice);
    if(z1<=z0)return;
    ctx.save();ctx.strokeStyle=rgba(COLORS.shell,.55);ctx.lineWidth=1.1;ctx.setLineDash([5,4]);
    for(const z of [z0,z1]){
      ctx.beginPath();let first=true;
      o.forEach(p=>{const q=project(W(p[0],p[1],z),basis,w,h);if(!q)return;if(first){ctx.moveTo(q.x,q.y);first=false}else ctx.lineTo(q.x,q.y);});ctx.closePath();ctx.stroke();
    }
    for(let i=0;i<o.length;i+=4){line3(W(o[i][0],o[i][1],z0),W(o[i][0],o[i][1],z1),COLORS.shell,.9,.38,basis,w,h);}
    ctx.restore();
  }

  function render(){
    state.renderQueued=false;state.dirty=false;
    const rect=canvas.getBoundingClientRect(); const dpr=Math.min(window.devicePixelRatio||1,2); const w=Math.max(1,Math.round(rect.width)),h=Math.max(1,Math.round(rect.height));
    if(canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)){canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);}
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
    const basis=cameraBasis();
    drawGrid(basis,w,h);
    let cmds=buildCommands(); state.centers=[];
    // Project commands and compute camera depth.
    cmds=cmds.map(c=>{
      const src=c.pts || (c.outer?c.outer.concat(...c.holes):[]); const pp=src.map(p=>project(p,basis,w,h)).filter(Boolean);
      c.cameraDepth=pp.length?pp.reduce((s,p)=>s+p.depth,0)/pp.length:-Infinity; return c;
    }).filter(c=>Number.isFinite(c.cameraDepth));
    cmds.sort((a,b)=>b.cameraDepth-a.cameraDepth);

    for(const c of cmds){
      let alpha=c.alpha;
      if(state.mode==='XRAY')alpha *= (c.group === 'parts' ? 0.48 : 0.24);
      if(state.mode==='COPPER')alpha *= (c.group==='pcb'?.55:(c.group==='parts'?.20:.10));
      const selected=state.selected && c.ref===state.selected.ref;
      const stroke=selected?COLORS.selected:(c.group==='pcb'?COLORS.pcbEdge:'#9aa3a8');
      const fill=faceColor(c.color,c.shade||1);
      ctx.save();
      ctx.globalAlpha=state.mode==='WIRE'?1:alpha;
      ctx.strokeStyle=stroke;ctx.lineWidth=selected?2.4:(state.mode==='WIRE'?1.05:.55);
      if(c.special){
        const path=new Path2D();
        function addLoop(arr){arr.forEach((v,i)=>{const p=project(v,basis,w,h);if(!p)return;if(i===0)path.moveTo(p.x,p.y);else path.lineTo(p.x,p.y)});path.closePath();}
        addLoop(c.outer); c.holes.forEach(addLoop);
        if(state.mode!=='WIRE'){ctx.fillStyle=fill;ctx.fill(path,'evenodd');}
        ctx.stroke(path);
      }else{
        const pts=c.pts.map(p=>project(p,basis,w,h)); if(pts.some(p=>!p)){ctx.restore();continue;}
        ctx.beginPath();ctx.moveTo(pts[0].x,pts[0].y);for(let i=1;i<pts.length;i++)ctx.lineTo(pts[i].x,pts[i].y);ctx.closePath();
        if(state.mode!=='WIRE'){ctx.fillStyle=fill;ctx.fill();}ctx.stroke();
      }
      ctx.restore();
    }
    drawCopper(basis,w,h);
    drawShell(basis,w,h);
    collectCenters(basis,w,h);
    if(state.labels)drawLabels(basis,w,h);
    updateReadout();
    if(window.STRUDIO_AFTER)window.STRUDIO_AFTER(w,h,dpr);
  }

  function objCenter3(p){
    if(p.ref==='BOARD'){const b=model.board.bbox;return W((b[0]+b[2])/2,(b[1]+b[3])/2,model.board.thickness/2);}
    if(p.type==='part'){
      const d=p.data,off=explodeOffset('parts',d.side||'front'); const z=(d.side==='back'?-partHeight(d)/2:model.board.thickness+partHeight(d)/2)+off; return W(d.x,d.y,z);
    }
    return W(p.x,p.y,p.z||0);
  }

  // CAD part list on screen, or null when the legacy mechanical envelopes are used instead.
  function cadParts(){
    if(!state.groupVisibility.case)return null;
    if(state.referenceMode)return window.STRUTHIO_CASE_R3?.parts||null;
    if(!state.authority.case||!window.STRUTHIO_CASE_LAYER)return null;
    return [...window.STRUTHIO_CASE_LAYER.parts,...(window.STRUTHIO_ACRYLIC_LAYER?.parts||[])];
  }
  // Short labels for the discrete CAD parts; shells, film, lens and routes are not pick targets.
  function cadLabel(item){
    const n=item.name;
    if(/LCD MODULE|DISPLAY ENVELOPE/.test(n))return 'DISPLAY';
    if(/^LIPO|BATTERY CANDIDATE/.test(n))return 'BATTERY';
    if(/^SPEAKER L ·|LEFT SPEAKER/.test(n))return 'SPK1';
    if(/^SPEAKER R ·|RIGHT SPEAKER/.test(n))return 'SPK2';
    if(/FLAP CAP L|LEFT BUTTON CAP/.test(n))return 'LEFT';
    if(/FLAP CAP R|RIGHT BUTTON CAP/.test(n))return 'RIGHT';
    if(/DART ROCKER/.test(n))return 'DART';
    if(/POWER PLUNGER/.test(n))return 'POWER';
    return null;
  }
  function cadCenter(item){
    if(!item._c){let mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];for(const t of item.triangles)for(const v of t.p)for(let i=0;i<3;i++){if(v[i]<mn[i])mn[i]=v[i];if(v[i]>mx[i])mx[i]=v[i];}item._c=[(mn[0]+mx[0])/2,(mn[1]+mx[1])/2,(mn[2]+mx[2])/2];}
    return item._c;
  }
  function collectCenters(basis,w,h){
    const arr=[];
    if(state.groupVisibility.pcb&&state.layers.parts){for(const p of model.parts){if(state.partSideFilter!=='all'&&(p.side||'front')!==state.partSideFilter)continue;if((p.side||'front')==='front'&&!state.layers.frontParts||(p.side||'front')==='back'&&!state.layers.backParts)continue;const off=explodeOffset('parts',p.side||'front');const z=(p.side==='back'?-partHeight(p)/2:model.board.thickness+partHeight(p)/2)+off;const q=project(W(p.x,p.y,z),basis,w,h);if(q)arr.push({ref:p.ref,type:'part',data:p,screen:q});}}
    const m=model.mechanical||{};
    const allowMechanical=state.groupVisibility.case&&(state.authority.case||state.referenceMode);
    const cad=cadParts();
    if(cad){
      const on={display:state.layers.display,battery:state.layers.battery,speakers:state.layers.speakers,controls:state.layers.controls};
      for(const item of cad){const ref=cadLabel(item);if(!ref||!on[item.group])continue;const c=cadCenter(item);if(c[2]>=state.slice)continue;const q=project(W(c[0],c[1],c[2]+explodeOffset(item.group)),basis,w,h);if(q)arr.push({ref,type:'mechanical',data:{confidence:item.name},screen:q});}
      state.centers=arr;return;
    }
    if(allowMechanical && state.layers.display&&m.display){let d=m.display,off=explodeOffset('display'),q=project(W(d.x,d.y,d.z0+d.d/2+off),basis,w,h);if(q)arr.push({ref:'DISPLAY',type:'mechanical',data:d,screen:q});}
    if(allowMechanical&&state.layers.battery&&m.battery){let d=m.battery,off=explodeOffset('battery'),q=project(W(d.x,d.y,d.z0+d.d/2+off),basis,w,h);if(q)arr.push({ref:'BATTERY',type:'mechanical',data:d,screen:q});}
    if(allowMechanical&&state.layers.speakers&&m.speakers)m.speakers.forEach((d,i)=>{let off=explodeOffset('speakers'),q=project(W(d.x,d.y,d.z0+d.d/2+off),basis,w,h);if(q)arr.push({ref:`SPK${i+1}`,type:'mechanical',data:d,screen:q});});
    if(allowMechanical&&state.layers.controls&&m.buttons)m.buttons.forEach((d,i)=>{let off=explodeOffset('controls'),q=project(W(d.x,d.y,d.z0+d.d/2+off),basis,w,h);if(q)arr.push({ref:d.label||`CTRL${i+1}`,type:'mechanical',data:d,screen:q});});
    state.centers=arr;
  }

  function drawLabels(){
    const major=/^(U1|J1|J2|J3|J4|J5|SW1|SW2|SW3|SW4|DISPLAY|BATTERY|SPK1|SPK2|LEFT|RIGHT|DART)$/;
    ctx.save();ctx.font='10px ui-monospace, monospace';ctx.textAlign='center';ctx.textBaseline='middle';
    for(const p of state.centers){if(!major.test(p.ref) && p.ref!==state.selected?.ref)continue;const {x,y}=p.screen;const txt=p.ref;const mw=ctx.measureText(txt).width+7;ctx.fillStyle=p.ref===state.selected?.ref?'rgba(255,214,106,.95)':'rgba(2,10,12,.76)';ctx.fillRect(x-mw/2,y-8,mw,15);ctx.fillStyle=p.ref===state.selected?.ref?'#101214':'#b8e6e1';ctx.fillText(txt,x,y-.5);}
    ctx.restore();
  }

  function schedule(){ if(state.renderQueued)return; state.renderQueued=true; requestAnimationFrame(render); }
  function updateReadout(){
    $('#viewReadout').textContent=`θ ${Math.round(state.yaw*180/Math.PI)}° · φ ${Math.round(state.pitch*180/Math.PI)}° · Z ${Math.round(state.dist)}`;
    $('#modeReadout').textContent=state.mode;
    const st=model.stats||{};$('#fpsReadout').textContent=`${model.parts.length} PARTS · ${st.tracks??(model.segments||[]).length} TRACKS`;
  }
  function resetView(kind='home'){
    if(kind==='home'){state.yaw=-.64;state.pitch=.82;state.dist=290;state.target={x:0,y:0,z:0};}
    if(kind==='top'){state.yaw=Math.PI;state.pitch=1.48;state.dist=290;state.target={x:0,y:0,z:0};}
    if(kind==='back'){state.yaw=0;state.pitch=-1.48;state.dist=290;state.target={x:0,y:0,z:0};}
    if(kind==='front'){state.yaw=Math.PI;state.pitch=.04;state.dist=300;state.target={x:0,y:0,z:0};}
    if(kind==='side'){state.yaw=-Math.PI/2;state.pitch=.04;state.dist=305;state.target={x:0,y:0,z:0};}
    if(kind==='edge'){state.yaw=0;state.pitch=.02;state.dist=280;state.target={x:0,y:0,z:0};}
    schedule();
  }

  function selectObject(item){
    if(!item)return;
    if(window.STRUDIO_SELECT)window.STRUDIO_SELECT(item);
    state.selected={ref:item.ref,type:item.type,data:item.data};$('#selectedReadout').textContent=`SEL: ${item.ref}`;
    if(item.type==='part'){
      const p=item.data;const pp=(model.pads||[]).filter(x=>x.ref===p.ref);const nets=[...new Set(pp.map(x=>x.netName).filter(Boolean))];const padMap=pp.slice(0,8).map(x=>`${x.num||'?'}:${x.netName||'NC'}`);
      const vip=(model.fab?.vias?.in_smd_pads||[]).filter(v=>v.ref===p.ref).map(v=>`pad ${v.pad} (${v.net})`);
      const bom=p.mpn!==undefined?`<br><span class="accent">BOM</span> ${escapeHTML(p.mpn||p.value||'')} · ${escapeHTML(p.package||'')}<br><span class="accent">SOURCE</span> ${escapeHTML(p.sourcing||'')} · ${p.land==='vendor'?'VENDOR LAND PATTERN':p.land==='audited'?'LAND AUDITED IN R22 REVIEW':'PROXY LAND · AUDIT AT DFM'}${vip.length?`<br><span class="accent">VIA IN PAD</span> ${escapeHTML(vip.join(', '))} · fill and cap`:''}`:'';
      $('#partInfo').innerHTML=`<b>${escapeHTML(p.ref)}</b> · ${escapeHTML(p.value||'')}<br><span class="cyan">${escapeHTML((p.category||'part').toUpperCase())}</span> · ${p.side.toUpperCase()} · ROT ${Number(p.rot||0).toFixed(0)}°<br>X ${p.x.toFixed(2)} · Y ${p.y.toFixed(2)} mm · ${p.w.toFixed(2)}×${p.h.toFixed(2)} mm<br>HEIGHT ≈ ${partHeight(p).toFixed(2)} mm · PADS ${p.padCount??pp.length}${nets.length?`<br><span class="accent">NETS</span> ${escapeHTML(nets.slice(0,6).join(' · '))}${nets.length>6?' …':''}`:''}${padMap.length?`<br><span class="accent">PAD MAP</span> ${escapeHTML(padMap.join(' · '))}${pp.length>8?' …':''}`:''}${bom}`;
    }else if(item.ref==='BOARD'){
      const st=model.stats||{};const lc={},ll={};let routeLen=0;for(const q of model.segments||[]){lc[q.layer]=(lc[q.layer]||0)+1;const len=Math.hypot(q.x2-q.x1,q.y2-q.y1);ll[q.layer]=(ll[q.layer]||0)+len;routeLen+=len;}const ls=Object.entries(lc).map(([k,v])=>`${k.replace('.Cu','')} ${v}/${(ll[k]||0).toFixed(1)}mm`).join(' · ');
      $('#partInfo').innerHTML=`<b>PCB / ${escapeHTML(model.name||'STRUTHIO')}</b><br>${(st.boardW??(model.board.bbox[2]-model.board.bbox[0])).toFixed(2)} × ${(st.boardH??(model.board.bbox[3]-model.board.bbox[1])).toFixed(2)} × ${(model.board.thickness||0).toFixed(2)} mm<br>${model.parts.length} footprints · ${(model.pads||[]).length} pads · ${(model.segments||[]).length} routed segments · ${(model.vias||[]).length} vias · ${st.nets??Object.keys(model.nets||{}).length} nets<br><span class="accent">ROUTED LENGTH</span> ${routeLen.toFixed(1)} mm${ls?`<br><span class="accent">COPPER</span> ${escapeHTML(ls)}`:''}${(model.zones||[]).length?`<br><span class="accent">POURS</span> ${escapeHTML(model.zones.map(z=>`${z.layer.replace('.Cu','')} ${z.net}`).join(' · '))}`:''}${fabSummary()}`;
    }else if(item.type==='trace'){
      const d=item.data;$('#partInfo').innerHTML=`<b>${escapeHTML(d.netName||('NET '+d.net))}</b> · COPPER TRACE<br><span class="cyan">${escapeHTML(d.layer)}</span> · WIDTH ${Number(d.w).toFixed(3)} mm · LENGTH ${Math.hypot(d.x2-d.x1,d.y2-d.y1).toFixed(2)} mm<br>(${d.x1.toFixed(2)}, ${d.y1.toFixed(2)}) → (${d.x2.toFixed(2)}, ${d.y2.toFixed(2)})`;
    }else if(item.type==='via'){
      const d=item.data;$('#partInfo').innerHTML=`<b>${escapeHTML(d.netName||('NET '+d.net))}</b> · VIA<br>AT X ${d.x.toFixed(2)} · Y ${d.y.toFixed(2)} mm<br>Ø ${d.size.toFixed(2)} mm · DRILL ${d.drill.toFixed(2)} mm`;
    }else{
      const d=item.data||{};$('#partInfo').innerHTML=`<b>${escapeHTML(item.ref)}</b><br>Mechanical visualization envelope${d.confidence?` · ${escapeHTML(d.confidence)}`:''}`;
    }
    schedule();
  }
  function fabSummary(){
    const f=model.fab;if(!f)return'';
    return `<br><span class="accent">FAB FILES</span> Gerber ×${f.gerber_layers.length} · drill · BOM ${f.bom.lines} lines (${f.bom.with_lcsc}/${f.bom.placements} with LCSC) · CPL ${f.cpl_placements}<br><span class="accent">DRC</span> KiCad ${escapeHTML(f.kicad)} · ${f.drc.violations} violations · ${f.drc.unconnected_pads} unconnected · vias ${f.vias.tented?'tented':'open'} · EVT PROTOTYPE`;
  }
  function escapeHTML(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

  function pointSegDist(px,py,ax,ay,bx,by){const vx=bx-ax,vy=by-ay,wx=px-ax,wy=py-ay;const l=vx*vx+vy*vy;if(!l)return Math.hypot(px-ax,py-ay);const t=clamp((wx*vx+wy*vy)/l,0,1);return Math.hypot(px-(ax+t*vx),py-(ay+t*vy));}
  function pick(x,y){
    let best=null,bd=34;
    for(const p of state.centers){const d=Math.hypot(p.screen.x-x,p.screen.y-y);if(d<bd){bd=d;best=p;}}
    if(state.mode==='COPPER'&&state.layers.copper){
      const basis=cameraBasis(),w=canvas.clientWidth,h=canvas.clientHeight;
      for(const v of model.vias||[]){const q=project(W(v.x,v.y,Math.min(model.board.thickness+.055,state.slice)),basis,w,h);if(!q)continue;const d=Math.hypot(q.x-x,q.y-y);if(d<Math.min(bd,15)){bd=d;best={ref:v.netName||`VIA ${v.net}`,type:'via',data:v,screen:q};}}
      for(const tr of model.segments||[]){const z=copperLayerZ(tr.layer);if(z>state.slice)continue;const a=project(W(tr.x1,tr.y1,z),basis,w,h),b=project(W(tr.x2,tr.y2,z),basis,w,h);if(!a||!b)continue;const d=pointSegDist(x,y,a.x,a.y,b.x,b.y);if(d<Math.min(bd,11)){bd=d;best={ref:tr.netName||`NET ${tr.net}`,type:'trace',data:tr,screen:{x:(a.x+b.x)/2,y:(a.y+b.y)/2}};}}
    }
    if(best)selectObject(best);
  }

  // Gestures: 1 finger orbit; 2-finger centroid drag pans; pinch zooms.
  let lastTap=0;
  canvas.addEventListener('pointerdown',e=>{
    canvas.setPointerCapture(e.pointerId);state.pointers.set(e.pointerId,{x:e.clientX,y:e.clientY,sx:e.clientX,sy:e.clientY});state.gestureMoved=false;if(state.pointers.size>=2)state.multi=true;
    if(state.pointers.size===2){const a=[...state.pointers.values()];state.pinchStart={dist:Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y),cameraDist:state.dist,cx:(a[0].x+a[1].x)/2,cy:(a[0].y+a[1].y)/2};}
    $('#gestureHint').classList.add('hide');
  });
  canvas.addEventListener('pointermove',e=>{
    const old=state.pointers.get(e.pointerId);if(!old)return;
    const dx=e.clientX-old.x,dy=e.clientY-old.y; if(Math.hypot(e.clientX-old.sx,e.clientY-old.sy)>4)state.gestureMoved=true;
    state.pointers.set(e.pointerId,{...old,x:e.clientX,y:e.clientY});
    const vals=[...state.pointers.values()];
    if(vals.length===1){if(!state.multi){state.yaw-=dx*.0085;state.pitch=clamp(state.pitch+dy*.0085,-1.50,1.50);}}
    else if(vals.length>=2){
      const a=vals[0],b=vals[1];const d=Math.hypot(a.x-b.x,a.y-b.y);const cx=(a.x+b.x)/2,cy=(a.y+b.y)/2;
      if(!state.pinchStart)state.pinchStart={dist:d,cameraDist:state.dist,cx,cy};
      state.dist=clamp(state.pinchStart.cameraDist*(state.pinchStart.dist/Math.max(20,d)),105,540);
      const dcx=cx-state.pinchStart.cx,dcy=cy-state.pinchStart.cy; const basis=cameraBasis(); const worldPerPx=state.dist/560;
      state.target=vadd(state.target,vadd(vmul(basis.r,-dcx*worldPerPx),vmul(basis.u,dcy*worldPerPx)));
      state.pinchStart={dist:d,cameraDist:state.dist,cx,cy};
    }
    schedule();
  });
  function pointerEnd(e){
    const p=state.pointers.get(e.pointerId);state.pointers.delete(e.pointerId);if(state.pointers.size<2)state.pinchStart=null;if(state.pointers.size===0)state.multi=false;
    if(p && !state.gestureMoved && state.pointers.size===0){const r=canvas.getBoundingClientRect();pick(e.clientX-r.left,e.clientY-r.top);const now=performance.now();if(now-lastTap<320)resetView('home');lastTap=now;}
  }
  canvas.addEventListener('pointerup',pointerEnd);canvas.addEventListener('pointercancel',pointerEnd);
  canvas.addEventListener('wheel',e=>{e.preventDefault();state.dist=clamp(state.dist*Math.exp(e.deltaY*.0011),105,540);schedule();},{passive:false});

  function updateBoardStats(){
    const st=model.stats||{};const bw=st.boardW??(model.board.bbox[2]-model.board.bbox[0]);const bh=st.boardH??(model.board.bbox[3]-model.board.bbox[1]);
    const routeLen=(model.segments||[]).reduce((a,q)=>a+Math.hypot(q.x2-q.x1,q.y2-q.y1),0);const cells=[['SIZE',`${bw.toFixed(1)}×${bh.toFixed(1)}`],['PCB',`${(model.board.thickness||0).toFixed(2)}mm`],['PARTS',model.parts.length],['PADS',(model.pads||[]).length],['TRACKS',(model.segments||[]).length],['VIAS',(model.vias||[]).length],['NETS',st.nets??Object.keys(model.nets||{}).length],['ROUTE',`${routeLen.toFixed(0)}mm`]];
    $('#boardStats').innerHTML=cells.map(([k,v])=>`<div class="stat"><b>${escapeHTML(v)}</b><span>${k}</span></div>`).join('');
  }


  const STACK_META={
    'build.assembled':{label:'BUILD · PCB + FRONT STACK',source:'build'},'build.back':{label:'BUILD · BACK',source:'build'},
    'art.clear':{label:'ACRYLIC · CLEAR FACE FILM',source:'art'},'art.relief':{label:'ACRYLIC · RELIEF',source:'art'},'art.print':{label:'ACRYLIC · PRINT',source:'art'},'art.white':{label:'ACRYLIC · WHITE BACK',source:'art'},'art.adhesive':{label:'ACRYLIC · ADHESIVE',source:'art'},
    'case.front':{label:'CASE · FRONT SHELL',source:'case'},'case.window':{label:'CASE · LCD MODULE',source:'case'},'case.lens':{label:'CASE · PROTECTIVE LENS',source:'case'},'case.controls':{label:'CASE · CONTROLS / MECH',source:'case'},'case.audio':{label:'CASE · AUDIO / CHAMBERS',source:'case'},'case.battery':{label:'CASE · BATTERY / POCKET',source:'case'},'case.structure':{label:'CASE · STRUCTURE',source:'case'},'case.rear':{label:'CASE · REAR SHELL',source:'case'},
    'pcb.top':{label:'PCB · TOP COMPONENTS',source:'pcb'},'pcb.fcu':{label:'PCB · F.Cu',source:'pcb'},'pcb.inner':{label:'PCB · INNER COPPER',source:'pcb'},'pcb.core':{label:'PCB · CORE / SUBSTRATE',source:'pcb'},'pcb.bcu':{label:'PCB · B.Cu',source:'pcb'},'pcb.bottom':{label:'PCB · BOTTOM COMPONENTS',source:'pcb'},'pcb.pads':{label:'PCB · PADS / VIAS',source:'pcb'}
  };
  function sourceAvailable(src){if(src==='build'||src==='pcb')return true;if(src==='case')return state.authority.case||state.referenceMode;if(src==='art')return state.authority.art;return false;}
  function syncLayerPanel(){
    document.querySelectorAll('#layerPanel [data-parent]').forEach(el=>el.checked=!!state.groupVisibility[el.dataset.parent]);
    document.querySelectorAll('#layerPanel [data-layer]').forEach(el=>el.checked=el.dataset.layer==='shell'?!!state.shell:!!state.layers[el.dataset.layer]);
  }
  function setAllOff(){state.layers={pcb:false,parts:false,frontParts:false,backParts:false,copper:false,display:false,lens:false,acrylic:false,battery:false,speakers:false,controls:false,rear:false,routes:false};state.shell=false;state.partSideFilter='all';state.copperFilter='all';}
  $('#layersBtn').addEventListener('click',()=>{const panel=$('#layerPanel');panel.hidden=!panel.hidden;$('#layersBtn').setAttribute('aria-expanded',String(!panel.hidden));if(!panel.hidden)syncLayerPanel();});
  $('#layersClose').addEventListener('click',()=>{$('#layerPanel').hidden=true;$('#layersBtn').setAttribute('aria-expanded','false');});
  $('#layerPanel').addEventListener('change',e=>{
    const el=e.target;if(el.matches('[data-parent]'))state.groupVisibility[el.dataset.parent]=el.checked;
    else if(el.matches('[data-layer]')){
      const key=el.dataset.layer;if(key==='shell')state.shell=el.checked;
      else if(key==='frontParts'||key==='backParts'){state.layers[key]=el.checked;state.layers.parts=state.layers.frontParts||state.layers.backParts;}
      else state.layers[key]=el.checked;
    }
    syncLayerPanel();schedule();
  });
  function setAuthorityStatus(){
    const pcbName=(model.source||model.name||'PCB').replace(/^.*[\\/]/,'');
    $('#pcbSource').textContent=(state.authority.pcb?`${pcbName} · SOURCE FILE`:'SOURCE MISSING');
    $('#caseSource').textContent=state.authority.case?'R12 · FULL CAD':(state.referenceMode?'R3 CAD · REFERENCE':'SOURCE MISSING');
    $('#artSource').textContent=state.authority.art?'CLEAR FILM R2 · 0.20':'SOURCE MISSING';
    const ss=$('#sourceStatus');if(ss)ss.innerHTML=`<span class="srcCase">CASE ${state.authority.case?'R12':(state.referenceMode?'R3':'—')}</span><span class="srcPCB">R27 · ORDER READY</span><span class="srcArt">FILM ${state.authority.art?'✓':'—'}</span>`;
    document.querySelectorAll('#stackWheel button').forEach(b=>{const src=b.dataset.source;b.classList.toggle('missing',src==='art'&&!state.authority.art || src==='case'&&!state.authority.case&&!state.referenceMode);b.classList.toggle('reference',src==='case'&&!state.authority.case&&state.referenceMode);});
  }
  function applyStack(key){
    const meta=STACK_META[key]||STACK_META['build.assembled'];state.stackKey=key;setAllOff();
    if(!sourceAvailable(meta.source)){
      $('#stackState').textContent=meta.source==='case'?'CASE SOURCE MISSING':'ACRYLIC SOURCE MISSING';
      $('#stackSourceBadge').textContent='?';$('#stackSourceBadge').style.color='#ee9a31';$('#stackReadout').textContent=`${meta.label} · SOURCE MISSING`;schedule();return;
    }
    if(meta.source==='build' && (!state.authority.case || !state.authority.art)){$('#stackSourceBadge').textContent='PART';$('#stackSourceBadge').style.color='#ee9a31';}
    else{$('#stackSourceBadge').textContent=meta.source==='case'&&!state.authority.case?'REF':'FILE';$('#stackSourceBadge').style.color='';}
    if(key==='build.assembled'){
      state.layers.pcb=state.layers.parts=state.layers.copper=true;state.layers.frontParts=state.layers.backParts=true;
      if(state.authority.case||state.referenceMode){state.shell=true;state.layers.display=state.layers.lens=state.layers.acrylic=state.layers.controls=true;}
      state.partSideFilter='all';state.copperFilter='all';
    }else if(key==='build.back'){
      state.layers.pcb=state.layers.parts=state.layers.copper=true;state.layers.backParts=true;state.layers.frontParts=false;state.partSideFilter='back';state.copperFilter='B.Cu';state.yaw=0;state.pitch=-.7;
      if(state.authority.case||state.referenceMode){state.shell=true;state.layers.display=state.layers.lens=true;}
    }else if(key==='pcb.top'){state.layers.pcb=state.layers.parts=state.layers.frontParts=true;state.layers.backParts=false;state.partSideFilter='front';}
    else if(key==='pcb.fcu'){state.layers.pcb=state.layers.copper=true;state.copperFilter='F.Cu';state.mode='COPPER';modeWheel?.choose('COPPER',true,false);}
    else if(key==='pcb.inner'){state.layers.pcb=state.layers.copper=true;state.copperFilter='internal';state.mode='COPPER';modeWheel?.choose('COPPER',true,false);}
    else if(key==='pcb.core'){state.layers.pcb=true;}
    else if(key==='pcb.bcu'){state.layers.pcb=state.layers.copper=true;state.copperFilter='B.Cu';state.mode='COPPER';modeWheel?.choose('COPPER',true,false);}
    else if(key==='pcb.bottom'){state.layers.pcb=state.layers.parts=state.layers.backParts=true;state.layers.frontParts=false;state.partSideFilter='back';}
    else if(key==='pcb.pads'){state.layers.pcb=state.layers.copper=true;state.copperFilter='pads';state.mode='COPPER';modeWheel?.choose('COPPER',true,false);}
    else if(key.startsWith('case.')){
      if(['case.front','case.window','case.lens','case.controls'].includes(key))state.shell=true;
      if(key==='case.window'){state.layers.display=true;state.layers.lens=true;}
      else if(key==='case.lens')state.layers.lens=true;
      else if(key==='case.controls')state.layers.controls=true;
      if(key==='case.rear'){state.layers.rear=true;state.shell=false;}
      else if(key==='case.audio'){state.layers.rear=true;state.layers.speakers=true;state.layers.routes=true;state.layers.pcb=true;}
      else if(key==='case.battery'){state.layers.rear=true;state.layers.battery=true;state.layers.routes=true;state.layers.pcb=true;}
      else if(key==='case.structure'){state.shell=true;state.layers.rear=true;state.layers.pcb=true;}
    }
    if(key==='art.clear')state.layers.acrylic=true;
    else if(key==='case.window')state.layers.display=true;
    else if(key==='case.lens'){state.layers.lens=true;}
    const pendingArt=meta.source==='art'&&key!=='art.clear';
    const pendingCase=false;
    const partialBuild=meta.source==='build'&&(!state.authority.case||!state.authority.art);
    $('#stackState').textContent=pendingArt?(key==='art.adhesive'?'OCA 0.025 mm · PART OF THE 0.20 mm FILM':'NOT USED · PROTOTYPE FILM IS UNPRINTED'):pendingCase?'':partialBuild?'PARTIAL · SOURCE INCOMPLETE':key==='build.assembled'?'FRONT STACK + PCB · R12 REAR IN CASE.REAR':meta.label.replace(' · ',' / ');
    $('#stackReadout').textContent=meta.label+(pendingArt?' · NOT USED':pendingCase?' · PENDING':partialBuild?' · PARTIAL':'');
    syncLayerPanel();schedule();
  }
  function initVerticalWheel(id,initial,onChange){
    const el=$(id),items=[...el.querySelectorAll('button')];let current=null,timer=0;
    function choose(value,scroll=true,fire=true){const item=items.find(x=>x.dataset.value===value)||items[0];if(!item)return;items.forEach(x=>{const a=x===item;x.classList.toggle('active',a);x.setAttribute('aria-selected',a?'true':'false');});if(scroll)item.scrollIntoView({behavior:'smooth',block:'center',inline:'nearest'});if(current!==item.dataset.value){current=item.dataset.value;if(fire)onChange(current);}}
    function nearest(){const r=el.getBoundingClientRect(),cy=r.top+r.height/2;let best=items[0],bd=Infinity;for(const it of items){const q=it.getBoundingClientRect(),d=Math.abs((q.top+q.bottom)/2-cy);if(d<bd){bd=d;best=it;}}choose(best.dataset.value,false,true);}
    items.forEach(it=>it.addEventListener('click',()=>choose(it.dataset.value,true,true)));el.addEventListener('scroll',()=>{clearTimeout(timer);timer=setTimeout(nearest,85);},{passive:true});requestAnimationFrame(()=>choose(initial,true,false));return{choose,nearest};
  }

  function initWheel(id,initial,onChange){
    const el=$(id),items=[...el.querySelectorAll('button')];let current=null,timer=0;
    function choose(value,scroll=true,fire=true){
      const item=items.find(x=>x.dataset.value===value)||items[0];if(!item)return;
      items.forEach(x=>{const a=x===item;x.classList.toggle('active',a);x.setAttribute('aria-selected',a?'true':'false');});
      if(scroll)item.scrollIntoView({behavior:'smooth',inline:'center',block:'nearest'});
      if(current!==item.dataset.value){current=item.dataset.value;if(fire)onChange(current);}
    }
    function nearest(){
      const r=el.getBoundingClientRect(),cx=r.left+r.width/2;let best=items[0],bd=Infinity;
      for(const it of items){const q=it.getBoundingClientRect();const d=Math.abs((q.left+q.right)/2-cx);if(d<bd){bd=d;best=it;}}
      choose(best.dataset.value,false,true);
    }
    items.forEach(it=>it.addEventListener('click',()=>choose(it.dataset.value,true,true)));
    el.addEventListener('scroll',()=>{clearTimeout(timer);timer=setTimeout(nearest,90);},{passive:true});
    requestAnimationFrame(()=>choose(initial,true,false));
    return {choose,nearest};
  }

  const viewWheel=initWheel('#viewWheel','home',v=>resetView(v));
  const modeWheel=initWheel('#modeWheel','SOLID',v=>{state.mode=v;schedule();});
  const stackWheel=initVerticalWheel('#stackWheel','build.assembled',v=>applyStack(v));
  applyStack('build.assembled');
  $('#referenceToggle').addEventListener('change',e=>{state.referenceMode=e.target.checked;setAuthorityStatus();applyStack(state.stackKey);});
  $('#explode').addEventListener('input',e=>{state.explode=+e.target.value;$('#explodeOut').value=state.explode;schedule();});
  $('#slice').addEventListener('input',e=>{state.slice=+e.target.value;$('#sliceOut').value=state.slice;schedule();});

  // Movable inspector window: drag the title bar; snap-back button restores the studio corner.
  const win=$('#viewWindow'),bar=$('#windowBar');let dragWin=null;
  function homeWindow(){win.style.left='6px';win.style.top='42px';win.style.right='auto';}
  bar.addEventListener('pointerdown',e=>{
    if(e.target.closest('button'))return;
    const stage=$('#viewport').getBoundingClientRect(),r=win.getBoundingClientRect();
    win.style.left=(r.left-stage.left)+'px';win.style.top=(r.top-stage.top)+'px';win.style.right='auto';
    dragWin={id:e.pointerId,ox:e.clientX-r.left,oy:e.clientY-r.top};bar.setPointerCapture(e.pointerId);e.preventDefault();
  });
  bar.addEventListener('pointermove',e=>{
    if(!dragWin||e.pointerId!==dragWin.id)return;const stage=$('#viewport').getBoundingClientRect();const r=win.getBoundingClientRect();
    const x=clamp(e.clientX-stage.left-dragWin.ox,4,Math.max(4,stage.width-r.width-4));
    const y=clamp(e.clientY-stage.top-dragWin.oy,4,Math.max(4,stage.height-r.height-68));
    win.style.left=x+'px';win.style.top=y+'px';
  });
  const stopWin=e=>{if(dragWin&&e.pointerId===dragWin.id)dragWin=null;};bar.addEventListener('pointerup',stopWin);bar.addEventListener('pointercancel',stopWin);
  $('#windowHome').addEventListener('click',homeWindow);
  $('#windowMin').addEventListener('click',e=>{const c=win.classList.toggle('collapsed');e.currentTarget.textContent=c?'+':'−';e.currentTarget.setAttribute('aria-expanded',c?'false':'true');});
  updateBoardStats();
  selectObject({type:'board',ref:'BOARD',data:{}});

  function focusItem(item){
    if(item?.type==='part'&&item.data){const p=item.data;const off=explodeOffset('parts',p.side||'front');const z=(p.side==='back'?-partHeight(p)/2:model.board.thickness+partHeight(p)/2)+off;state.target=W(p.x,p.y,z);state.dist=Math.min(state.dist,155);}
    else if(item?.data&&Number.isFinite(item.data.x)){const d=item.data;state.target=W(d.x,d.y,(d.z0||0)+(d.d||0)/2);state.dist=Math.min(state.dist,165);}
  }
  function findRef(){const q=$('#partSearch').value.trim().toUpperCase();if(!q)return;const raw=model.parts.find(p=>p.ref.toUpperCase()===q);const item=raw?{ref:raw.ref,type:'part',data:raw}:state.centers.find(p=>p.ref.toUpperCase()===q);if(item){selectObject(item);focusItem(item);schedule();}else $('#partInfo').textContent=`${q}: not found in this model.`;}
  $('#findPart').addEventListener('click',findRef);$('#partSearch').addEventListener('keydown',e=>{if(e.key==='Enter')findRef();});

  $('#resetModel').addEventListener('click',()=>{model=clone(baseModel);state.groupVisibility={case:true,pcb:true,acrylic:true};state.authority.pcb=true;state.authority.case=true;state.authority.art=true;state.referenceMode=false;$('#referenceToggle').checked=false;state.selected={type:'board',ref:'BOARD'};$('#selectedReadout').textContent='SEL BOARD';updateBoardStats();setAuthorityStatus();stackWheel.choose('build.assembled',true,true);selectObject({type:'board',ref:'BOARD',data:{}});resetView('home');});

  $('#fileInput').addEventListener('change',async e=>{
    const file=e.target.files?.[0];if(!file)return;
    try{
      const text=await file.text();
      if(file.name.toLowerCase().endsWith('.json')){const j=JSON.parse(text);validateModel(j);model=j;}
      else model=parseKicad(text,file.name);
      state.authority.pcb=true;setAuthorityStatus();
      state.selected={type:'board',ref:'BOARD'};$('#selectedReadout').textContent='SEL BOARD';updateBoardStats();
      $('#partInfo').innerHTML=`Loaded <b>${escapeHTML(file.name)}</b><br>${model.parts.length} footprints · ${(model.segments||[]).length} routed segments · ${(model.vias||[]).length} vias.<br>The bundled R12 case and R1 clear acrylic film remain visible as separate, fixed-datum design layers; compare fit before relying on loaded-board alignment.`;
      resetView('home');
    }catch(err){$('#partInfo').textContent='Load failed: '+err.message;}
    e.target.value='';
  });

  function validateModel(j){if(!j?.board?.outer||!Array.isArray(j.parts))throw new Error('JSON is not a CALC-3D model.');}

  function parseKicad(text,name){
    const edge=[];
    for(const g of balancedBlocks(text,'(gr_line ')){
      if(!/\(layer\s+"Edge\.Cuts"\)/.test(g))continue;
      const lm=g.match(/\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)/);
      if(lm)edge.push([[+lm[1],+lm[2]],[+lm[3],+lm[4]]]);
    }
    if(edge.length<4)throw new Error('No usable Edge.Cuts line geometry found.');
    const loops=chainLoops(edge);if(!loops.length)throw new Error('Could not chain Edge.Cuts into a loop.');
    loops.sort((a,b)=>Math.abs(polyArea(b))-Math.abs(polyArea(a)));const outer=loops[0],holes=loops.slice(1);
    const xs=outer.map(p=>p[0]),ys=outer.map(p=>p[1]);
    const netNames={};for(const m of text.matchAll(/^\s*\(net\s+(\d+)\s+"([^"]*)"\)/gm))netNames[+m[1]]=m[2];
    const parts=[],pads=[];const fblocks=balancedBlocks(text,'(footprint ');
    for(const b of fblocks){
      const ref=(b.match(/\(fp_text\s+reference\s+"([^"]+)"/)||[])[1];
      const at=b.match(/\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)/);if(!ref||!at)continue;
      const x=+at[1],y=+at[2],rot=+(at[3]||0);const val=(b.match(/\(fp_text\s+value\s+"([^"]*)"/)||[])[1]||'';
      const layer=(b.match(/\(layer\s+"([FB]\.Cu)"\)/)||[])[1]||'F.Cu';
      let w=1.8,h=1.8;const rr=[...b.matchAll(/\(fp_rect\s+\(start\s+([-\d.]+)\s+([-\d.]+)\)\s+\(end\s+([-\d.]+)\s+([-\d.]+)\)[\s\S]*?\(layer\s+"[FB]\.CrtYd"\)/g)];
      if(rr.length){const xx=[],yy=[];rr.forEach(r=>{xx.push(+r[1],+r[3]);yy.push(+r[2],+r[4]);});w=Math.max(...xx)-Math.min(...xx);h=Math.max(...yy)-Math.min(...yy);}
      w=clamp(w,.5,24);h=clamp(h,.5,24);
      const pblocks=balancedBlocks(b,'(pad ');let padCount=0;
      for(const pb of pblocks){
        const pa=pb.match(/\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)/),sz=pb.match(/\(size\s+([\d.]+)\s+([\d.]+)\)/);if(!pa||!sz)continue;padCount++;
        const lx=+pa[1],ly=+pa[2],pr=+(pa[3]||0),a=rot*Math.PI/180;const gx=x+lx*Math.cos(a)-ly*Math.sin(a),gy=y+lx*Math.sin(a)+ly*Math.cos(a);
        const layers=(pb.match(/\(layers\s+([^\)]*)\)/)||[])[1]||'';const nm=pb.match(/\(net\s+(\d+)\s+"([^"]*)"\)/);const no=(pb.match(/^\(pad\s+"([^"]*)"/)||[])[1]||'';
        pads.push({ref,num:no,x:gx,y:gy,w:+sz[1],h:+sz[2],rot:rot+pr,side:layers.includes('*.Cu')?'both':(layers.includes('F.Cu')?'front':'back'),net:nm?+nm[1]:0,netName:nm?nm[2]:''});
      }
      parts.push({ref,value:val,x,y,rot,side:layer==='B.Cu'?'back':'front',w,h,z:estimateHeight(ref),category:category(ref),padCount});
    }
    const segments=[];for(const sb of balancedBlocks(text,'(segment ')){
      const sm=sb.match(/\(start\s+([-\d.]+)\s+([-\d.]+)\)/),em=sb.match(/\(end\s+([-\d.]+)\s+([-\d.]+)\)/),wm=sb.match(/\(width\s+([\d.]+)\)/),lm=sb.match(/\(layer\s+"([^"]+\.Cu)"\)/),nm=sb.match(/\(net\s+(\d+)\)/);if(!sm||!em||!wm||!lm||!nm)continue;const ni=+nm[1];segments.push({x1:+sm[1],y1:+sm[2],x2:+em[1],y2:+em[2],w:+wm[1],layer:lm[1],net:ni,netName:netNames[ni]||''});
    }
    const vias=[];for(const vb of balancedBlocks(text,'(via ')){
      const am=vb.match(/\(at\s+([-\d.]+)\s+([-\d.]+)\)/),sm=vb.match(/\(size\s+([\d.]+)\)/),dm=vb.match(/\(drill\s+([\d.]+)\)/),nm=vb.match(/\(net\s+(\d+)\)/);if(!am||!sm||!dm||!nm)continue;const ni=+nm[1];vias.push({x:+am[1],y:+am[2],size:+sm[1],drill:+dm[1],net:ni,netName:netNames[ni]||''});
    }
    const thick=+(text.match(/\(thickness\s+([\d.]+)\)/)||[])[1]||1.2;const bw=Math.max(...xs)-Math.min(...xs),bh=Math.max(...ys)-Math.min(...ys);
    return {name:name.replace(/\.kicad_pcb$/i,''),source:name,status:'Locally parsed visualization',units:'mm',board:{outer,holes,thickness:thick,bbox:[Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)]},parts,pads,segments,vias,nets:netNames,stats:{parts:parts.length,pads:pads.length,tracks:segments.length,vias:vias.length,nets:Object.keys(netNames).length,boardW:bw,boardH:bh,thickness:thick},mechanical:clone(baseModel.mechanical),notes:['Parsed locally in STRUTHIO Visualization Studio.','Edge.Cuts, footprints, tracks and vias come from the loaded KiCad board.','Mechanical data is a separate non-authority reference and is hidden by default.']};
  }

  function balancedBlocks(text,token){const out=[];let pos=0;while(true){const i=text.indexOf(token,pos);if(i<0)break;let depth=0,str=false,esc=false,j=i;for(;j<text.length;j++){const c=text[j];if(str){if(esc)esc=false;else if(c==='\\')esc=true;else if(c==='"')str=false;}else{if(c==='"')str=true;else if(c==='(')depth++;else if(c===')'){depth--;if(depth===0){j++;break;}}}}out.push(text.slice(i,j));pos=j;}return out;}
  function keyPt(p){return `${p[0].toFixed(4)},${p[1].toFixed(4)}`;}
  function chainLoops(segments){
    const unused=segments.map((s,i)=>({s,i}));const loops=[];
    while(unused.length){let cur=unused.pop().s;const loop=[cur[0],cur[1]];let guard=0;
      while(guard++<segments.length+5){const end=loop[loop.length-1];if(keyPt(end)===keyPt(loop[0])&&loop.length>3){loop.pop();break;}let found=-1,rev=false;for(let i=0;i<unused.length;i++){const s=unused[i].s;if(keyPt(s[0])===keyPt(end)){found=i;break;}if(keyPt(s[1])===keyPt(end)){found=i;rev=true;break;}}if(found<0)break;const n=unused.splice(found,1)[0].s;loop.push(rev?n[0]:n[1]);}
      if(loop.length>=3)loops.push(loop);
    }return loops;
  }
  function polyArea(p){let a=0;for(let i=0,j=p.length-1;i<p.length;j=i++)a+=(p[j][0]*p[i][1]-p[i][0]*p[j][1]);return a/2;}
  function category(ref){if(ref.startsWith('SW'))return'switch';if(ref.startsWith('J'))return'connector';if(ref.startsWith('U'))return'ic';if(ref.startsWith('C'))return'capacitor';if(ref.startsWith('R'))return'resistor';if(ref.startsWith('L'))return'inductor';if(ref.startsWith('D'))return'diode';if(ref.startsWith('Q'))return'transistor';return'other';}
  function estimateHeight(ref){if(ref.startsWith('SW'))return 4.6;if(ref.startsWith('J'))return 3;if(ref==='U1')return 1.2;if(ref.startsWith('U'))return 1.4;if(ref.startsWith('L'))return 1.6;if(ref.startsWith('Q')||ref.startsWith('D'))return 1.1;if(ref.startsWith('C')||ref.startsWith('R'))return .75;return 1;}

  $('#snapBtn').addEventListener('click',()=>{
    render();canvas.toBlob(blob=>{if(!blob)return;const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`STRUTHIO_VISSTUDIO_${Date.now()}.png`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);},'image/png');
  });

  // Studio 1.0 release shell: portrait-first, local-first, and explicit project identity.
  const aboutSheet=$('#aboutSheet'),aboutBtn=$('#aboutBtn'),aboutClose=$('#aboutClose');
  function openAbout(){aboutSheet.hidden=false;aboutClose?.focus();}
  function closeAbout(){aboutSheet.hidden=true;aboutBtn?.focus();}
  aboutBtn?.addEventListener('click',openAbout);aboutClose?.addEventListener('click',closeAbout);
  aboutSheet?.addEventListener('pointerdown',e=>{if(e.target===aboutSheet)closeAbout();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!aboutSheet?.hidden)closeAbout();});
  async function requestPortrait(){try{if(screen.orientation?.lock)await screen.orientation.lock('portrait-primary');}catch(_){/* iOS may ignore orientation lock; CSS gate remains authoritative. */}}
  requestPortrait();

  new ResizeObserver(schedule).observe(canvas);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden){requestPortrait();schedule();}});
  if('serviceWorker' in navigator && location.protocol.startsWith('http'))navigator.serviceWorker.register('./sw.js').catch(()=>{});
  // Shared Sight bridge (additive): lets eye.js read the camera, project points and drive views. No geometry or authority logic is touched.
  window.STRUDIO={
    state,canvas,schedule,
    render:()=>render(),
    model:()=>model,
    project:(x,y,z)=>{const r=canvas.getBoundingClientRect();return project(W(x,y,z),cameraBasis(),r.width,r.height);},
    world:(x,y,z)=>W(x,y,z),
    copperLayerZ:l=>copperLayerZ(l),
    partHeight:p=>partHeight(p),
    setStack:k=>{stackWheel.choose(k,false,false);applyStack(k);},
    setMode:m=>{modeWheel.choose(m,false,false);state.mode=m;schedule();},
    stackLabel:()=>(STACK_META[state.stackKey]||{}).label||state.stackKey,
    select:item=>selectObject(item),
    authority:()=>({case:state.authority.case||false,reference:state.referenceMode,pcb:state.authority.pcb,art:state.authority.art})
  };
  setAuthorityStatus();applyStack('build.assembled');
  setTimeout(()=>$('#gestureHint').classList.add('hide'),6500);
  schedule();
})();
