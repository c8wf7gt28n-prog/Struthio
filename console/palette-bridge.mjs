export const SHELL_ROLES=Object.freeze({
accent:'--machine-cyan',
edge:'--machine-yellow',
text:'--machine-paper',
textDim:'--machine-paper-dim',
danger:'--machine-red',
ink:'--machine-black',
graphite:'--machine-graphite',
});
export const CONTROLLER_ROLES=Object.freeze({
accent:'--control-accent',
edge:'--control-edge',
});
export const ROLE_LABELS=Object.freeze({
shell:{accent:'Shell accent / power light',edge:'Primary action edge',text:'Shell text',textDim:'Secondary shell text',danger:'Danger / alarm',ink:'Shell background ink',graphite:'Panel graphite'},
controller:{accent:'Wing glyph accent',edge:'Wing ring edge'},
});
export const CONSOLE_DEFAULTS=Object.freeze({
shell:{accent:'#1CB2E0',edge:'#FACA3A',text:'#FBF6D1',textDim:'#D8CFA8',danger:'#FA381D',ink:'#050505',graphite:'#17120D'},
controller:{accent:'#4FE8F0',edge:'#E7BE68'},
});
const SHELL_PAIRS=Object.freeze([
{fg:'text',bg:'ink',min:4.5},
{fg:'textDim',bg:'ink',min:4.5},
{fg:'text',bg:'graphite',min:4.5},
{fg:'accent',bg:'ink',min:3},
{fg:'edge',bg:'ink',min:3},
{fg:'danger',bg:'ink',min:3},
]);
const CONTROLLER_PAIRS=Object.freeze([
{fg:'accent',min:3},
{fg:'edge',min:3},
]);
export const HEX_TOKEN=/^#[0-9A-Fa-f]{6}$/;
function channel(v){const c=v/255;return c<=0.03928?c/12.92:((c+0.055)/1.055)**2.4;}
export function luminance(hex){
const n=parseInt(hex.slice(1),16);
return 0.2126*channel((n>>16)&255)+0.7152*channel((n>>8)&255)+0.0722*channel(n&255);
}
export function contrast(a,b){
const[x,y]=[luminance(a),luminance(b)].sort((p,q)=>q-p);
return (x+0.05)/(y+0.05);
}
function tokens(request,roles,group,report){
const out={};
if (request===undefined||request===null) return out;
if (typeof request!=='object'||Array.isArray(request)){report.push({group,role:'*',reason:'NOT_AN_OBJECT'});return out;}
for (const[role,value] of Object.entries(request)){
if (!(role in roles)){report.push({group,role,reason:'UNKNOWN_ROLE'});continue;}
if (typeof value!=='string'||!HEX_TOKEN.test(value)){report.push({group,role,reason:'MALFORMED_TOKEN',value:String(value).slice(0,24)});continue;}
out[role]=value.toUpperCase();
}
return out;
}
export function resolveSemanticPalette(presentation={}){
const rejected=[];
const shell=tokens(presentation.shellPalette,SHELL_ROLES,'shell',rejected);
const controller=tokens(presentation.controllerPalette,CONTROLLER_ROLES,'controller',rejected);
const effective=(role)=>shell[role]||CONSOLE_DEFAULTS.shell[role];
for (const bg of['ink','graphite']){
if (!shell[bg]) continue;
const bad=SHELL_PAIRS.filter((p)=>p.bg===bg).find((p)=>contrast(CONSOLE_DEFAULTS.shell[p.fg],shell[bg])<p.min);
if (bad){rejected.push({group:'shell',role:bg,reason:'CONTRAST',against:bad.fg,ratio:+contrast(CONSOLE_DEFAULTS.shell[bad.fg],shell[bg]).toFixed(2),min:bad.min});delete shell[bg];}
}
for (const pair of SHELL_PAIRS){
if (!shell[pair.fg]) continue;
const ratio=contrast(shell[pair.fg],effective(pair.bg));
if (ratio<pair.min){rejected.push({group:'shell',role:pair.fg,reason:'CONTRAST',against:pair.bg,ratio:+ratio.toFixed(2),min:pair.min});delete shell[pair.fg];}
}
for (const pair of CONTROLLER_PAIRS){
if (!controller[pair.fg]) continue;
const ratio=contrast(controller[pair.fg],effective('ink'));
if (ratio<pair.min){rejected.push({group:'controller',role:pair.fg,reason:'CONTRAST',against:'ink',ratio:+ratio.toFixed(2),min:pair.min});delete controller[pair.fg];}
}
return{shell,controller,rejected};
}
export const CARTRIDGE_OWNED_VARS=Object.freeze([
'--ui-bone','--ui-cyan','--ui-gold','--ui-gold-lit','--ui-crimson','--ui-ink',
...Object.values(SHELL_ROLES),...Object.values(CONTROLLER_ROLES),
]);
export function resetCartridgePalette(root){
for (const name of CARTRIDGE_OWNED_VARS) root.style.removeProperty(name);
}
export function applySemanticPalette(root,resolved){
for (const[role,value] of Object.entries(resolved.shell)) root.style.setProperty(SHELL_ROLES[role],value);
for (const[role,value] of Object.entries(resolved.controller)) root.style.setProperty(CONTROLLER_ROLES[role],value);
}
