// STRUTHIO ARCADE · the top HUD: score, round, rings 0/6, rivals defeated and
// Joust Marks (lives). hudModel is pure; createHud writes it into the DOM only
// when something changed.
const LIVES_MAX=11;
const two=(n)=>String(Math.max(0,n|0)).padStart(2,'0');
function bitCount(mask){let n=mask>>>0,c=0;while (n){c+=n&1;n>>>=1;}return c;}

export function hudModel(view){
const s=view.state;
const live=view.screen==='GAME'&&!!s&&s.sim.shell!=='ATTRACT';
const trueScore=Math.max(0,Math.trunc(s?.sim.score||0));
const mask=(s?.tower.ringMask||0)>>>0;
let toast='',toastKind='';
if (view.banner&&view.banner.until>view.renderTick){toast=view.banner.text;toastKind='event';}
if (view.saveWarning){toast='SAVE NOT UPDATED';toastKind='warning';}
if (s?.sim.shell==='PAUSE'){toast='PAUSED';toastKind='pause';}
return{
live,paused:s?.sim.shell==='PAUSE',
score:String(trueScore%1000000).padStart(6,'0'),trueScore,carry:Math.floor(trueScore/1000000),
round:two(s?.tower.round||1),
rings:{value:bitCount(mask&63),max:6,gold:(mask&63)===63&&!(mask&64)},
kills:s?.tower.kills||0,
lives:{value:Math.max(0,Math.min(LIVES_MAX,s?.sim.lives|0)),max:LIVES_MAX},
toast:live?toast:'',toastKind:live?toastKind:'',
};
}
export function hudAriaLabel(m){
return[`Score ${m.trueScore}.`,`Round ${Number(m.round)}.`,`Rings ${m.rings.value} of ${m.rings.max}${m.rings.gold?', gold ring open':''}.`,
`Rivals defeated ${m.kills}.`,`${m.lives.value} Joust Marks remaining.`].join(' ');
}
export function createHud(root,{toastRoot=null,srRoot=null}={}){
const $=(sel)=>root.querySelector(sel);
const scoreBox=$('#hud-score'),score=$('#hud-score b'),crown=$('#hud-crown');
const round=$('#hud-pos-av'),ringsEl=$('#hud-ring'),rings=$('#hud-ring b'),kills=$('#hud-rival b');
const lives=$('#hud-joust b'),livesBar=$('#hud-joust i');
let signature='',ariaSig='',lastLives=null,lastToast='',lastCarry=null,glitch=null;
function rollover(finalText){
clearInterval(glitch);
const glyphs='0123456789#%&$@';
let n=0;
scoreBox.classList.add('is-rollover');
glitch=setInterval(()=>{
n+=1;
if (n>8){clearInterval(glitch);glitch=null;score.textContent=finalText;scoreBox.classList.remove('is-rollover');return;}
score.textContent=Array.from(finalText,()=>glyphs[Math.floor(Math.random()*glyphs.length)]).join('');
},32);
}
return{
update(model){
const next=JSON.stringify(model);
if (next===signature) return;
signature=next;
root.classList.toggle('is-live',model.live);
root.setAttribute('aria-hidden',model.live?'false':'true');
if (!glitch) score.textContent=model.score;
if (crown){crown.hidden=!(model.carry>0);crown.dataset.carry=model.carry>1?String(model.carry):'';}
if (model.live&&lastCarry!==null&&model.carry>lastCarry) rollover(model.score);
lastCarry=model.live?model.carry:null;
round.textContent=model.round;
rings.textContent=`${two(model.rings.value)}/${two(model.rings.max)}`;
ringsEl.classList.toggle('is-due',model.rings.gold);
kills.textContent=model.kills>99?String(model.kills):two(model.kills);
lives.textContent=`${two(model.lives.value)}/${model.lives.max}`;
if (livesBar) livesBar.style.setProperty('--joust',String(model.lives.value/model.lives.max));
root.classList.toggle('is-low',model.lives.value<=2);
const aria=hudAriaLabel(model);
if (aria!==ariaSig){ariaSig=aria;root.setAttribute('aria-label',aria);}
if (model.live&&lastLives!==null&&model.lives.value<lastLives&&srRoot) srRoot.textContent=`${model.lives.value} Joust Marks remaining.`;
lastLives=model.live?model.lives.value:null;
if (toastRoot&&model.toast!==lastToast){
lastToast=model.toast;
toastRoot.textContent=model.toast;
toastRoot.dataset.kind=model.toastKind;
toastRoot.classList.toggle('is-on',!!model.toast);
}
},
};
}
