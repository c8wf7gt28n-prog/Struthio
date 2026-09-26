const FOCUSABLE='a[href],button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
function visible(el){
if (el.hidden||el.closest('[hidden]')) return false;
const style=getComputedStyle(el);
return style.display!=='none'&&style.visibility!=='hidden';
}
export function focusablesIn(root){
return[...root.querySelectorAll(FOCUSABLE)].filter(visible);
}
export function openModal(dialog,{onEscape=null,initialFocus=null,returnFocus=null}={}){
const doc=dialog.ownerDocument;
const prior=doc.activeElement;
const inerted=[];
for (const el of doc.body.children){
if (el===dialog||el.contains(dialog)||el.inert||el.tagName==='SCRIPT') continue;
el.inert=true;
inerted.push(el);
}
function onKey(event){
if (event.key==='Escape'){
if (onEscape){event.preventDefault();event.stopPropagation();onEscape();}
return;
}
if (event.key!=='Tab') return;
const items=focusablesIn(dialog);
if (!items.length){event.preventDefault();dialog.focus({preventScroll:true});return;}
const first=items[0],last=items[items.length-1];
const here=doc.activeElement;
if (event.shiftKey&&(here===first||!dialog.contains(here))){event.preventDefault();last.focus();}
else if (!event.shiftKey&&(here===last||!dialog.contains(here))){event.preventDefault();first.focus();}
}
doc.addEventListener('keydown',onKey,true);
const start=initialFocus||focusablesIn(dialog)[0]||dialog;
if (start===dialog&&!dialog.hasAttribute('tabindex')) dialog.setAttribute('tabindex','-1');
start.focus({preventScroll:true});
let released=false;
return function release(){
if (released) return;
released=true;
doc.removeEventListener('keydown',onKey,true);
for (const el of inerted) el.inert=false;
const target=(returnFocus&&returnFocus())||prior;
if (target&&target.isConnected&&typeof target.focus==='function'&&visible(target)) target.focus({preventScroll:true});
};
}
