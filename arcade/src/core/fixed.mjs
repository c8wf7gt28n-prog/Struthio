// STRUTHIO ARCADE · integer subpixel maths and the 256-px horizontal wrap.
const SUBPIXEL=256;
const WRAP=256*SUBPIXEL;
function assertInt(v,name='value'){
if (!Number.isSafeInteger(v)) throw new Error(`NON_INTEGER ${name}=${v}`);
return v;
}
function clamp(v,lo,hi){
assertInt(v);
return v<lo?lo:v>hi?hi:v;
}
function tdiv(a,b){
assertInt(a);assertInt(b);
const q=Math.trunc(a/b);
return q===0?0:q;
}
function mod(v,m){
assertInt(v);
const r=v%m;
return r<0?r+m:r;
}
function floorDiv(v,d){
assertInt(v);assertInt(d);
const q=Math.trunc(v/d);
const r=v%d;
const out=r!==0&&(r<0)!==(d<0)?q-1:q;
return out===0?0:out;
}
function px(logical){
return assertInt(logical)*SUBPIXEL;
}
function nearestWrapShift(dx){
assertInt(dx);
const c0=Math.abs(dx),cm=Math.abs(dx-WRAP),cp=Math.abs(dx+WRAP);
let best=0,bestAbs=c0;
if (cm<bestAbs){best=-WRAP;bestAbs=cm;}
if (cp<bestAbs){best=WRAP;bestAbs=cp;}
return best;
}
function wrappedDelta(from,to){
const dx=to-from;
return dx+nearestWrapShift(dx);
}
function compareRational(an,ad,bn,bd){
const l=an*bd,r=bn*ad;
if (!Number.isSafeInteger(l)||!Number.isSafeInteger(r)) throw new Error('RATIONAL_OVERFLOW');
return l===r?0:l<r?-1:1;
}
export{px,tdiv,mod,WRAP,wrappedDelta,clamp,compareRational,nearestWrapShift,floorDiv};
