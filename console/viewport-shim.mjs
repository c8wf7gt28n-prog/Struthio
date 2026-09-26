export function measureViewportShim(win=globalThis.window){
const doc=win.document;
const standalone=win.navigator.standalone===true||!!win.matchMedia?.('(display-mode: standalone)').matches;
const probe=doc.createElement('div');
probe.style.cssText='position:fixed;left:0;top:0;width:0;height:env(safe-area-inset-top);visibility:hidden;pointer-events:none';
doc.documentElement.appendChild(probe);
const safeTop=probe.getBoundingClientRect().height;
probe.remove();
const screenLong=Math.max(win.screen.width,win.screen.height);
const screenShort=Math.min(win.screen.width,win.screen.height);
const portrait=win.innerHeight>win.innerWidth;
const gap=screenLong-win.innerHeight;
const affected=standalone&&portrait&&Math.abs(screenShort-win.innerWidth)<=1
&&gap>0&&safeTop>0&&Math.abs(gap-safeTop)<=6;
return{standalone,portrait,safeTop,gap,shim:affected?Math.round(gap):0};
}
export function installViewportShim({win=globalThis.window,disabled=false,onChange=null}={}){
const root=win.document.documentElement;
let report={disabled,shim:0};
function apply(){
report=disabled?{...measureViewportShim(win),disabled:true,shim:0}:{...measureViewportShim(win),disabled:false};
const value=`${report.shim}px`;
if (root.style.getPropertyValue('--ios-shim')!==value){
root.style.setProperty('--ios-shim',value);
if (onChange) onChange(report);
}
return report;
}
apply();
for (const type of['resize','orientationchange','pageshow']) win.addEventListener(type,apply);
win.visualViewport?.addEventListener?.('resize',apply);
return{get report(){return report;},apply};
}
