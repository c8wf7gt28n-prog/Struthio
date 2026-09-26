export const TICK_MS=1000/60;
export const INPUT_DELAY=2;
export const MAX_AHEAD=20;
const DIGEST_EVERY=120;
const KEEP_SNAPSHOTS=12;
const RESEND_MAX=90;
const CONFIRMED_ONLY=new Set(['VS_JOUST','VS_DEATH','VS_RESPAWN','VS_END','VS_COUNT','VS_GO']);
export class VsLink{
constructor({url,build='',WebSocketImpl=globalThis.WebSocket,now=()=>performance.now(),onMessage=()=>{},onStatus=()=>{},setTimer=(fn,ms)=>setTimeout(fn,ms),clearTimer=(h)=>clearTimeout(h)}){
Object.assign(this,{url,build,WebSocketImpl,now,onMessage,onStatus,setTimer,clearTimer});
this.ws=null;this.state='IDLE';this.seat=-1;this.token='';this.code='';
this.offset=0;this.bestRtt=Infinity;this.rtt=0;this.pingTimer=null;this.retry=null;this.retries=0;
this.intent=null;
this.closedByUs=false;
}
toLocal(serverMs){return serverMs-this.offset;}
create(hello){this.intent={t:'create',...hello};this.open();}
join(code,hello){this.intent={t:'join',code,...hello};this.open();}
open(){
this.closedByUs=false;
this.setStatus(this.seat>=0?'RECONNECTING':'CONNECTING');
const code=this.intent&&this.intent.t==='join'?this.intent.code:this.code;
const build=(this.intent&&this.intent.build)||this.build||'';
const url=this.url+(this.url.includes('?')?'&':'?')+(code?'code='+encodeURIComponent(code):'create=1')+(build?'&build='+encodeURIComponent(build):'')+(this.seat>=0?'&rejoin=1':'');
let ws;
try{ws=new this.WebSocketImpl(url);}catch (e){this.lost('OPEN_FAILED');return;}
this.ws=ws;
if (this.openTimer) this.clearTimer(this.openTimer);
this.openTimer=this.setTimer(()=>{this.openTimer=null;if (this.ws===ws&&ws.readyState!==1){this.ws=null;try{ws.close();}catch{}this.lost('TIMEOUT');}},5000);
ws.onopen=()=>{
if (this.ws!==ws) return;
if (this.openTimer){this.clearTimer(this.openTimer);this.openTimer=null;}
this.retries=0;this.lastRx=this.now();
if (this.seat>=0) this.send({t:'rejoin',seat:this.seat,token:this.token});
else if (this.intent) this.send(this.intent);
this.syncClock();
};
ws.onmessage=(ev)=>{
if (this.ws!==ws) return;
this.lastRx=this.now();
let m;try{m=JSON.parse(typeof ev.data==='string'?ev.data:String(ev.data));}catch{return;}
if (m.t==='pong') return this.onPong(m);
if (m.t==='room'){this.seat=m.seat;this.token=m.token;this.code=m.code;this.setStatus('CONNECTED');}
if (m.t==='reject'&&m.reason==='CODE_TAKEN'&&this.intent&&this.intent.t==='create'&&(this.codeRetries||0)<5){this.codeRetries=(this.codeRetries||0)+1;this.ws=null;try{ws.close();}catch{}this.open();return;}
if (m.t==='reject'&&this.seat<0){this.closedByUs=true;this.setStatus('REJECTED');}
this.onMessage(m);
};
ws.onclose=(ev)=>{
if (this.ws!==ws) return;
this.ws=null;
if (ev&&(ev.code===4000||ev.code===4001)&&this.seat>=0){this.closedByUs=true;this.stopPings();this.setStatus('CLOSED');return;}
this.lost('CLOSED');
};
ws.onerror=()=>{};
}
lost(why){
this.stopPings();
if (this.closedByUs){this.setStatus(this.state==='REJECTED'?'REJECTED':'CLOSED');return;}
if (this.retries>=(this.seat>=0?12:3)){this.setStatus('FAILED');return;}
const wait=Math.min(4000,400*2**this.retries);this.retries+=1;
this.setStatus(this.seat>=0?'RECONNECTING':'CONNECTING');
this.retry=this.setTimer(()=>{this.retry=null;this.open();},wait);
}
send(obj){
if (!this.ws||this.ws.readyState!==1) return false;
try{this.ws.send(JSON.stringify(obj));return true;}catch{return false;}
}
syncClock(){
this.stopPings();
let n=0;
const tick=()=>{
if (this.ws&&this.ws.readyState===1&&this.now()-this.lastRx>6000){const dead=this.ws;this.ws=null;try{dead.close();}catch{}this.lost('SILENT');return;}
this.send({t:'ping',c:this.now()});
n+=1;
this.pingTimer=this.setTimer(tick,n<5?90:2000);
};
tick();
}
stopPings(){if (this.pingTimer){this.clearTimer(this.pingTimer);this.pingTimer=null;}}
onPong(m){
const t=this.now(),rtt=t-m.c;
this.rtt=this.rtt?this.rtt*0.8+rtt*0.2:rtt;
this.bestRtt=Math.min(this.bestRtt*1.02+0.5,Infinity);
if (rtt<=this.bestRtt){this.bestRtt=rtt;this.offset=m.s-(m.c+rtt/2);}
}
setStatus(s){if (this.state!==s){this.state=s;this.onStatus(s);}}
wake(){
if (this.closedByUs) return;
if (!this.ws&&!this.retry){this.open();return;}
if (this.ws&&this.ws.readyState===1){this.send({t:'ping',c:this.now()});if (this.now()-this.lastRx>6000){const dead=this.ws;this.ws=null;try{dead.close();}catch{}this.lost('SILENT');}}
}
close(){
this.closedByUs=true;this.stopPings();
if (this.openTimer){this.clearTimer(this.openTimer);this.openTimer=null;}
if (this.retry){this.clearTimer(this.retry);this.retry=null;}
if (this.ws){try{this.send({t:'bye'});this.ws.close(1000,'bye');}catch{}}
this.ws=null;this.setStatus('CLOSED');
}
}
export class VsMatch{
constructor({makeGame,vs,send,onEvent=()=>{},onEnd=()=>{},clock=()=>performance.now(),toLocal=(ms)=>ms}){
Object.assign(this,{makeGame,vs,send,onEvent,onEnd,clock,toLocal});
this.active=false;this.stats={rollbacks:0,maxDepth:0,stalls:0,stallMs:0,desyncs:0,resims:0,gos:0};
}
go(m,seat){
this.seat=seat;this.peer=1-seat;this.matchN=m.match;this.epoch=m.epoch;this.seed=m.seed;
this.inputs=[m.logs[0].slice(),m.logs[1].slice()];
const T=m.tick;
this.confirmed=this.makeGame(this.seed);
this.snapshots=new Map();
this.ended=null;this.endSent=false;this.result=null;
this.confirmedTick=0;
while (this.confirmedTick<T) this.stepConfirmed(false);
const own=this.inputs[this.seat];
const fill=[];
for (let t=T;t<T+INPUT_DELAY;t++){own[t]=0;fill.push(0);}
this.peerAck=T;
this.sendInputs(T);
this.localTick=T;
this.goAt=m.at;this.goTick=T;this.shift=0;
this.pred=null;this.predTick=-1;
this.seen=new Map();
this.remoteNow=T;this.remoteNowAt=this.clock();
this.stalledSince=0;this.paused=false;
this.pending=[];
this.active=true;this.stats.gos+=1;
this.rebuildPrediction();
}
pause(){this.paused=true;this.pausedAt=this.clock();}
onInput(m){
if (!this.active||m.match!==this.matchN||m.epoch!==this.epoch||m.s!==this.peer) return;
const log=this.inputs[this.peer];
for (let i=0;i<m.b.length;i++){const t=m.f+i;if (t===log.length) log.push(m.b[i]&255);}
if (Number.isFinite(m.now)){this.remoteNow=m.now;this.remoteNowAt=this.clock();}
if (Number.isFinite(m.ack)&&m.ack>this.peerAck) this.peerAck=m.ack;
}
sendInputs(now){
const own=this.inputs[this.seat];
const from=Math.max(this.peerAck,own.length-RESEND_MAX);
this.send({t:'in',match:this.matchN,epoch:this.epoch,f:from,b:own.slice(from),now,ack:this.confirmedTick});
}
onSendState(m){
if (!this.active||m.match!==this.matchN) return;
const snap=this.snapshots.get(m.tick);
if (snap) this.send({t:'state',match:this.matchN,tick:m.tick,state:snap});
}
onState(m){
if (!this.active||m.match!==this.matchN||m.tick>this.confirmedTick) return;
const upTo=this.confirmedTick;
this.confirmed.restore(m.state);
this.confirmedTick=m.tick;
this.ended=null;this.endSent=false;
while (this.confirmedTick<upTo) this.stepConfirmed(true);
this.stats.desyncs+=1;
this.pred=null;
}
onResult(m){if (m.match===this.matchN){this.result=m;this.onEnd({...m,confirmedByRelay:true});}}
update(sample){
if (!this.active) return;
const now=this.clock();
if (this.paused) return;
const own=this.inputs[this.seat];
const remoteEst=this.remoteNow+(now-this.remoteNowAt)/TICK_MS;
const advantage=this.localTick-remoteEst;
if (advantage>1.5) this.shift+=Math.min(4,advantage-1.5);
else if (advantage<-1.5) this.shift-=Math.min(2,-advantage-1.5);
const startLocal=this.toLocal(this.goAt)-this.goTick*TICK_MS+this.shift;
let target=Math.max(this.localTick,Math.floor((now-startLocal)/TICK_MS));
const cap=this.confirmedTick+MAX_AHEAD;
if (target>cap){
if (!this.stalledSince){this.stalledSince=now;this.stats.stalls+=1;}
this.shift+=(target-cap)*TICK_MS;
target=cap;
}else if (this.stalledSince){this.stats.stallMs+=now-this.stalledSince;this.stalledSince=0;}
let released=false;
while (this.localTick<target){
own[this.localTick+INPUT_DELAY]=this.vs.encodeInput(sample());
this.localTick+=1;released=true;
}
if (released) this.sendInputs(this.localTick);
const before=this.confirmedTick;
while (this.confirmedTick<own.length&&this.confirmedTick<this.inputs[this.peer].length) this.stepConfirmed(true);
if (this.confirmedTick!==before||!this.pred) this.rebuildPrediction();
while (this.predTick<this.localTick) this.stepPrediction();
this.pruneSeen();
}
stepConfirmed(live){
const t=this.confirmedTick;
const r=this.confirmed.tick([this.inputs[0][t]|0,this.inputs[1][t]|0]);
this.confirmedTick+=1;
const tick=this.confirmed.state.tick;
if (live){
for (const e of r.events) if (CONFIRMED_ONLY.has(e.type)) this.present(e);
if (tick%DIGEST_EVERY===0){
const snap=this.confirmed.snapshot();
this.snapshots.set(tick,snap);
if (this.snapshots.size>KEEP_SNAPSHOTS) this.snapshots.delete(this.snapshots.keys().next().value);
this.send({t:'dg',match:this.matchN,tick,d:this.confirmed.digest()});
}
}
const s=this.confirmed.state;
if (s.phase==='OVER'&&!this.ended){
this.ended={tick:s.tick,winner:s.winner,reason:s.endReason,d:this.confirmed.digest()};
if (live&&!this.endSent){
this.endSent=true;
this.send({t:'end',match:this.matchN,tick:s.tick,winner:s.winner,reason:s.endReason,d:this.ended.d});
this.onEnd({...this.ended,confirmedByRelay:false});
}
}
}
rebuildPrediction(){
const depth=this.predTick>=0?this.predTick-this.confirmedTick:0;
if (depth>0){this.stats.rollbacks+=1;this.stats.maxDepth=Math.max(this.stats.maxDepth,depth);this.stats.resims+=depth;}
this.pred=this.makeGame(this.seed);
this.pred.state=this.confirmed.snapshot();
this.predTick=this.confirmedTick;
}
stepPrediction(){
const t=this.predTick,peerLog=this.inputs[this.peer];
const guess=t<peerLog.length?peerLog[t]:this.vs.predictInput(peerLog.length?peerLog[peerLog.length-1]:0);
const own=this.inputs[this.seat][t]|0;
const inputs=this.seat===0?[own,guess]:[guess,own];
const r=this.pred.tick(inputs);
this.predTick+=1;
for (const e of r.events) if (!CONFIRMED_ONLY.has(e.type)) this.present(e);
}
present(e){
const key=`${e.type}|${e.tick}|${e.who??''}|${e.a??''}|${e.b??''}|${e.order??''}|${e.winner??''}|${e.loser??''}`;
if (this.seen.has(key)) return;
this.seen.set(key,e.tick);
this.onEvent(e);
}
pruneSeen(){
if (this.seen.size<400) return;
const floor=this.confirmedTick-240;
for (const[k,t] of this.seen) if (t<floor) this.seen.delete(k);
}
get view(){return this.pred?this.pred.state:this.confirmed?this.confirmed.state:null;}
get truth(){return this.confirmed?this.confirmed.state:null;}
get waiting(){return!!this.stalledSince&&this.clock()-this.stalledSince>250;}
stop(){this.active=false;}
}
