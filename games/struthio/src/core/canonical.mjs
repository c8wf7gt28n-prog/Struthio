// STRUTHIO ARCADE · canonical JSON and SHA-256 digests (state fingerprints and save checksums).
import{sha256Hex}from './sha256.mjs';
const SURROGATE=/[\uD800-\uDFFF]/;
function sortKeys(keys){
if (!keys.some((k)=>SURROGATE.test(k))) return keys.slice().sort();
return keys.slice().sort((a,b)=>{
const ia=[...a],ib=[...b];
const n=Math.min(ia.length,ib.length);
for (let i=0;i<n;i++){
const ca=ia[i].codePointAt(0),cb=ib[i].codePointAt(0);
if (ca!==cb) return ca-cb;
}
return ia.length-ib.length;
});
}
function canonical(value){
if (value===null) return 'null';
if (value===true) return 'true';
if (value===false) return 'false';
const t=typeof value;
if (t==='number'){
if (!Number.isFinite(value)) throw new Error('CANONICAL_NONFINITE');
if (Object.is(value,-0)) throw new Error('CANONICAL_NEGATIVE_ZERO');
if (!Number.isSafeInteger(value)) throw new Error('CANONICAL_NONINTEGER');
return String(value);
}
if (t==='string') return JSON.stringify(value);
if (Array.isArray(value)) return '['+value.map(canonical).join(',')+']';
if (t==='object'){
const keys=sortKeys(Object.keys(value));
return '{'+keys.map((k)=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
}
throw new Error('CANONICAL_UNSUPPORTED_TYPE');
}
function digest(value){
return sha256Hex(canonical(value));
}
function checkpointChecksum(record){
const copy=structuredClone(record);
copy.checksum='0'.repeat(64);
return digest(copy);
}
export{digest,checkpointChecksum};
