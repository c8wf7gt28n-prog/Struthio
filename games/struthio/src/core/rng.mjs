// STRUTHIO ARCADE · the seeded random number generator (deterministic gameplay).
const ZERO_REMAP=0x6d2b79f5;
function seedState(seed){
const s=Number(seed)>>>0;
return s===0?ZERO_REMAP:s;
}
function nextU32(box){
let x=box.state>>>0;
if (x===0) x=ZERO_REMAP;
x^=x<<13;
x>>>=0;
x^=x>>>17;
x^=x<<5;
x>>>=0;
box.state=x;
return x;
}
export{seedState,nextU32};
