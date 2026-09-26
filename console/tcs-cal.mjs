export const TCS_DEVICES=Object.freeze([
{id:'apple/iphone_13_mini',model:'iPhone 13 mini',note:'verified'},
{id:'apple/iphone_13',model:'iPhone 13',note:'official specs'},
{id:'apple/iphone_17',model:'iPhone 17',note:'official specs'},
{id:'samsung/galaxy_s25',model:'Galaxy S25',note:'official specs'},
]);
const CSS=`
#tcs-panel{position:fixed;z-index:70;left:0;right:0;top:0;bottom:calc(var(--deck-h) + var(--safe-bottom));display:flex;justify-content:center;align-items:flex-start;padding:max(10px,env(safe-area-inset-top)) 10px 8px;box-sizing:border-box;background:rgba(5,5,5,.92);overflow:auto}
#tcs-panel[hidden]{display:none!important}
#tcs-panel .tcs-card{width:min(100%,380px);box-sizing:border-box;display:flex;flex-direction:column;gap:9px;background:#0b0908;border:2px solid var(--machine-yellow,#faca3a);border-radius:12px;padding:12px;color:var(--machine-paper,#f2e8d2);font:700 13px Arial,Helvetica,sans-serif}
#tcs-panel h2{margin:0;color:var(--machine-yellow,#faca3a);font:900 20px/1.1 "Arial Narrow",Arial,sans-serif;letter-spacing:.06em}
#tcs-panel .tcs-kicker{margin:0;color:var(--machine-cyan,#1cb2e0);font-size:11px;letter-spacing:.16em}
#tcs-panel label{display:flex;flex-direction:column;gap:4px;font-size:11px;letter-spacing:.1em;color:#b8ab90}
#tcs-panel select,#tcs-panel input{font:700 15px Arial,sans-serif;background:#000;color:#f2e8d2;border:2px solid #3a3226;border-radius:8px;padding:8px}
#tcs-panel dl{display:grid;grid-template-columns:auto 1fr;gap:3px 10px;margin:0;font:700 12px "Courier New",monospace}
#tcs-panel dt{color:#8f846d}#tcs-panel dd{margin:0;color:#f2e8d2;text-align:right}
#tcs-panel .tcs-warn{margin:0;color:#ff7b5c;font-size:12px;line-height:1.35}
#tcs-panel .tcs-ok{margin:0;color:#7fe08a;font-size:12px}
#tcs-panel .tcs-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px}
#tcs-panel button{min-height:46px;border-radius:8px;border:2px solid var(--machine-yellow,#faca3a);background:#140f06;color:#f2e8d2;font:900 14px Arial,sans-serif;letter-spacing:.06em}
#tcs-panel button.is-primary{background:var(--machine-yellow,#faca3a);color:#140f05}
#tcs-panel .tcs-status{margin:0;min-height:1em;color:var(--machine-cyan,#1cb2e0);font-size:12px}
body.tcs-measuring #controls button[data-control$="_WING"]{outline:3px dashed #ff5a3c;outline-offset:2px}
`;
function rect(el){
const r=el.getBoundingClientRect();
const q=(v)=>Math.round(v*100)/100;
return{x:q(r.x),y:q(r.y),width:q(r.width),height:q(r.height),centerX:q(r.x+r.width/2),centerY:q(r.y+r.height/2)};
}
function insets(){
const probe=document.createElement('div');
probe.style.cssText='position:fixed;visibility:hidden;pointer-events:none;top:0;left:0;padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)';
document.body.append(probe);
const s=getComputedStyle(probe);
const out={top:parseFloat(s.paddingTop)||0,right:parseFloat(s.paddingRight)||0,bottom:parseFloat(s.paddingBottom)||0,left:parseFloat(s.paddingLeft)||0};
probe.remove();
return out;
}
export function measureCalibration({build,model='',caseMode='bare'}={}){
const left=document.querySelector('#controls button[data-control="LEFT_WING"]');
const right=document.querySelector('#controls button[data-control="RIGHT_WING"]');
const vv=window.visualViewport;
const mm=(q)=>{try{return!!window.matchMedia?.(q).matches;}catch{return false;}};
const displayMode=mm('(display-mode: fullscreen)')?'fullscreen':mm('(display-mode: standalone)')?'standalone':navigator.standalone===true?'standalone':'browser';
const cs=getComputedStyle(document.documentElement);
return{
schema:'struthio-tcs-calibration-1',
build,
capturedAt:new Date().toISOString(),
device:{model,case_mode:caseMode,userAgent:navigator.userAgent},
viewport:{
innerWidth:window.innerWidth,innerHeight:window.innerHeight,
screen:{w:window.screen.width,h:window.screen.height,availW:window.screen.availWidth,availH:window.screen.availHeight},
visual:vv?{w:Math.round(vv.width*100)/100,h:Math.round(vv.height*100)/100,offsetTop:vv.offsetTop,scale:vv.scale}:null,
visualScale:vv?vv.scale:1,
dpr:window.devicePixelRatio,
orientation:window.screen.orientation?.type||(window.innerHeight>=window.innerWidth?'portrait':'landscape'),
standalone:displayMode!=='browser',
displayMode,
},
insets:insets(),
iosShim:parseFloat(cs.getPropertyValue('--ios-shim'))||0,
wingCss:cs.getPropertyValue('--wing-d').trim(),
controls:{leftWing:left?rect(left):null,rightWing:right?rect(right):null},
deck:document.getElementById('controls')?rect(document.getElementById('controls')):null,
};
}
export function setupTcsCalibration({build,openModal=null}){
const el=(tag,attrs={},text='')=>{const n=document.createElement(tag);for (const[k,v] of Object.entries(attrs)) n.setAttribute(k,v);if (text) n.textContent=text;return n;};
const style=el('style');style.textContent=CSS;document.head.append(style);
const root=el('section',{id:'tcs-panel',role:'dialog','aria-modal':'true','aria-labelledby':'tcs-title',hidden:''});
const card=el('div',{class:'tcs-card'});
const kicker=el('p',{class:'tcs-kicker'},'TCS FACTORY · STEP 1 OF 2');
const title=el('h2',{id:'tcs-title'},'TCS CALIBRATION');
const intro=el('p',{class:'tcs-status'},'Measures where the two wings sit on this phone’s screen, so Claude can make a TCS that fits it.');
const modelLabel=el('label',{},'PHONE MODEL');
const select=el('select',{'aria-label':'Phone model'});
for (const d of TCS_DEVICES) select.append(el('option',{value:d.model},`${d.model} (${d.note})`));
select.append(el('option',{value:''},'Other — type it below'));
const other=el('input',{type:'text',placeholder:'Exact model, e.g. iPhone 16 Pro','aria-label':'Other phone model',hidden:''});
modelLabel.append(select,other);
const caseLabel=el('label',{},'CASE');
const caseSel=el('select',{'aria-label':'Case'});
caseSel.append(el('option',{value:'bare'},'No case (bare phone)'),el('option',{value:'case'},'In a case'));
caseLabel.append(caseSel);
const readout=el('dl');
const warn=el('p',{class:'tcs-warn',role:'alert'});
const ok=el('p',{class:'tcs-ok'});
const status=el('p',{class:'tcs-status',role:'status','aria-live':'polite'});
const actions=el('div',{class:'tcs-actions'});
const copyBtn=el('button',{type:'button',class:'is-primary','data-tcs':'copy'},'COPY FOR CLAUDE');
const shareBtn=el('button',{type:'button','data-tcs':'share'},'SHARE');
const closeBtn=el('button',{type:'button','data-tcs':'close'},'CLOSE');
const againBtn=el('button',{type:'button','data-tcs':'again'},'MEASURE AGAIN');
actions.append(copyBtn,shareBtn,againBtn,closeBtn);
card.append(kicker,title,intro,modelLabel,caseLabel,readout,warn,ok,status,actions);
root.append(card);
document.body.append(root);
let release=null,last=null;
const model=()=>(select.value||other.value.trim());
function measure(){
last=measureCalibration({build,model:model(),caseMode:caseSel.value});
const v=last.viewport,L=last.controls.leftWing,R=last.controls.rightWing;
readout.replaceChildren();
const row=(k,val)=>readout.append(el('dt',{},k),el('dd',{},val));
row('SCREEN',`${v.screen.w} × ${v.screen.h} CSS px @ ${v.dpr}x`);
row('VIEWPORT',`${v.innerWidth} × ${v.innerHeight} · ${v.displayMode}`);
row('LEFT WING',L?`${L.centerX}, ${L.centerY} · d ${L.width}`:'NOT FOUND');
row('RIGHT WING',R?`${R.centerX}, ${R.centerY} · d ${R.width}`:'NOT FOUND');
row('SAFE AREA',`${last.insets.top} / ${last.insets.bottom}${last.iosShim?` · iOS shim ${last.iosShim}`:''}`);
const problems=[];
if (!v.standalone) problems.push('Open STRUTHIO from its Home Screen icon (not in a browser tab), then measure again.');
if (v.screen.h<v.screen.w) problems.push('Hold the phone upright (portrait).');
if (Math.abs((v.visualScale||1)-1)>0.01) problems.push('Pinch back to normal zoom first.');
if (!L||!R) problems.push('The wing controls were not found on screen.');
if (!model()) problems.push('Choose or type the exact phone model.');
if (caseSel.value==='case') problems.push('A case changes the fit: Claude will treat it as a separate, unverified profile.');
warn.textContent=problems.join(' ');
ok.textContent=problems.length?'':'Looks good. Copy it and paste it to Claude with the phone model.';
return last;
}
function text(){return JSON.stringify(measure(),null,2);}
async function copy(){
const t=text();
try{await navigator.clipboard.writeText(t);status.textContent='COPIED · PASTE IT TO CLAUDE';}
catch{status.textContent='COPY BLOCKED · USE SHARE';}
}
async function share(){
const t=text();
try{
if (navigator.share){await navigator.share({title:'STRUTHIO TCS calibration',text:t});status.textContent='SHARED';}
else{await navigator.clipboard.writeText(t);status.textContent='COPIED · PASTE IT TO CLAUDE';}
}catch (e){if (e&&e.name!=='AbortError') status.textContent='SHARE FAILED · TRY COPY';}
}
select.addEventListener('change',()=>{other.hidden=!!select.value;if (!select.value) other.focus();measure();});
other.addEventListener('input',()=>measure());
caseSel.addEventListener('change',()=>measure());
copyBtn.addEventListener('click',copy);
shareBtn.addEventListener('click',share);
againBtn.addEventListener('click',()=>{measure();status.textContent='MEASURED AGAIN';});
closeBtn.addEventListener('click',()=>api.close());
window.addEventListener('resize',()=>{if (!root.hidden) measure();});
const api={
open(){
root.hidden=false;document.body.classList.add('tcs-measuring');status.textContent='';
measure();
if (openModal&&!release) release=openModal(root,{onEscape:()=>api.close(),initialFocus:copyBtn});
},
close(){
root.hidden=true;document.body.classList.remove('tcs-measuring');
if (release){release();release=null;}
},
get isOpen(){return!root.hidden;},
get last(){return last;},
measure,
};
return api;
}
