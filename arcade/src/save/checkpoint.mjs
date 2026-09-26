// STRUTHIO ARCADE · checkpoints. Two slots (A/B) plus an active pointer: a save
// writes the inactive slot, re-reads and validates it (schema + SHA-256
// checksum), then flips the pointer, so a torn write never loses the last run.
import{validate}from './schema.mjs';
import{checkpointChecksum}from '../core/canonical.mjs';

export const SAVE_NAMESPACE='struthio.arcade.v1';
export const SAVE_FORMAT='struthio-arcade-save';
export const SAVE_VERSION=1;
export const KEYS=Object.freeze({
A:`${SAVE_NAMESPACE}.run.A`,B:`${SAVE_NAMESPACE}.run.B`,ACTIVE:`${SAVE_NAMESPACE}.run.active`,
WARNING:`${SAVE_NAMESPACE}.warning`,RECORDS:`${SAVE_NAMESPACE}.records`,
});
function buildRecord(payload){
const record={format:SAVE_FORMAT,version:SAVE_VERSION,payload:structuredClone(payload),checksum:'0'.repeat(64)};
record.checksum=checkpointChecksum(record);
return record;
}
function validateRecordText(schema,text){
if (text===null||text===undefined) return{ok:false,reason:'ABSENT'};
let record;
try{record=JSON.parse(text);}catch{return{ok:false,reason:'PARSE'};}
if (!record||typeof record!=='object') return{ok:false,reason:'PARSE'};
if (record.format!==SAVE_FORMAT||record.version!==SAVE_VERSION) return{ok:false,reason:'UNKNOWN_FORMAT'};
const errors=validate(schema,record);
if (errors.length) return{ok:false,reason:'SCHEMA',errors};
let sum;
try{sum=checkpointChecksum(record);}catch{return{ok:false,reason:'CHECKSUM'};}
if (sum!==record.checksum) return{ok:false,reason:'CHECKSUM'};
return{ok:true,record};
}
export function writeCheckpoint(storage,schema,payload,opts={}){
const{hidden=false,budgetMs=120,now=()=>Date.now()}=opts;
const t0=now();
const slot=storage.getItem(KEYS.ACTIVE)==='A'?'B':'A';
const record=buildRecord(payload);
storage.setItem(KEYS[slot],JSON.stringify(record));
const v=validateRecordText(schema,storage.getItem(KEYS[slot]));
if (!v.ok||v.record.checksum!==record.checksum) return{committed:false,slot,reason:v.reason||'REREAD_MISMATCH'};
if (hidden&&now()-t0>budgetMs){storage.setItem(KEYS.WARNING,'SAVE NOT UPDATED');return{committed:false,slot,reason:'HIDDEN_BUDGET'};}
storage.setItem(KEYS.ACTIVE,slot);
return{committed:true,slot,checksum:record.checksum};
}
export function restoreCheckpoint(storage,schema){
const a=validateRecordText(schema,storage.getItem(KEYS.A));
const b=validateRecordText(schema,storage.getItem(KEYS.B));
const pointer=storage.getItem(KEYS.ACTIVE);
const pointed=pointer==='A'?a:pointer==='B'?b:null;
if (pointed&&pointed.ok) return{status:'RESTORE',record:pointed.record,slot:pointer};
if (a.ok&&b.ok){
const slot=a.record.payload.sim.tick>=b.record.payload.sim.tick?'A':'B';
return{status:'RESTORE',record:slot==='A'?a.record:b.record,slot,repairPointer:slot};
}
if (a.ok) return{status:'RESTORE',record:a.record,slot:'A',repairPointer:'A'};
if (b.ok) return{status:'RESTORE',record:b.record,slot:'B',repairPointer:'B'};
const present=[a.reason,b.reason].filter((r)=>r!=='ABSENT');
return present.length?{status:'REJECTED',reasons:{A:a.reason,B:b.reason}}:{status:'NONE'};
}
export function clearRun(storage){for (const k of[KEYS.A,KEYS.B,KEYS.ACTIVE]) storage.removeItem(k);}
export function memoryStorage(init={}){
const m=new Map(Object.entries(init));
return{getItem:(k)=>(m.has(k)?m.get(k):null),setItem:(k,v)=>{m.set(k,String(v));},removeItem:(k)=>{m.delete(k);},keys:()=>[...m.keys()]};
}
