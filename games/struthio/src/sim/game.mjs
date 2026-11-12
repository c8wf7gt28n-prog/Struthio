// STRUTHIO ARCADE · a game session: the state, its tick, and a running digest
// chain (every tick's state+events hashed into the previous link).
import{newState}from './state.mjs';
import{stepTick,startRun,payloadOf,EMPTY_INPUT}from './step.mjs';
import{digest}from '../core/canonical.mjs';
import{seedState}from '../core/rng.mjs';
export class Game{
constructor(R,{seed=1,state=null}={}){
this.R=R;
this.state=state||newState(seed,R);
this.seed=seed;
this.events=[];
this.chain=digest({seed:seedState(seed),game:'STRUTHIO-ARCADE'});
this.tickDigest=null;
}
start(){this.pendingEvents=startRun(this.state);return this.pendingEvents;}
tick(input=EMPTY_INPUT){
const r=stepTick(this.R,this.state,input);
if (this.pendingEvents&&this.pendingEvents.length){r.events.unshift(...this.pendingEvents.map((e)=>({...e,serial:0})));this.pendingEvents=null;}
this.tickDigest=r.digest;
this.chain=digest({prev:this.chain,tick:r.digest});
this.events=r.events;
return r;
}
payload(){return payloadOf(this.state);}
stateDigest(){return digest(this.payload());}
}
