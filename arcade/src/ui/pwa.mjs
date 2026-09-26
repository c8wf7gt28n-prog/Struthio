// STRUTHIO ARCADE · service-worker registration and the update-ready prompt.
function setupPwa({base='./',onUpdateReady,onOffline}){
const state={registration:null,waiting:null,offlineNote:'',reloaded:false,supported:'serviceWorker' in navigator};
if (!state.supported) return{state,acceptUpdate(){},get offlineNote(){return state.offlineNote;}};
const sw=navigator.serviceWorker;
sw.register(base+'sw.js',{scope:base}).then((reg)=>{
state.registration=reg;
const track=(w)=>{if (!w) return;w.addEventListener('statechange',()=>{if (w.state==='installed'&&sw.controller){state.waiting=reg.waiting;onUpdateReady&&onUpdateReady();}if (w.state==='redundant'&&!reg.waiting&&!reg.active) state.offlineNote='UPDATE FAILED - CURRENT VERSION KEPT';});};
if (reg.waiting&&sw.controller){state.waiting=reg.waiting;onUpdateReady&&onUpdateReady();}
track(reg.installing);
reg.addEventListener('updatefound',()=>track(reg.installing));
let lastCheck=Date.now();
document.addEventListener('visibilitychange',()=>{
if (document.visibilityState!=='visible'||!navigator.onLine||Date.now()-lastCheck<600000) return;
lastCheck=Date.now();
reg.update().catch(()=>{});
});
}).catch((e)=>{state.offlineNote='SERVICE WORKER UNAVAILABLE';state.error=String(e);});
sw.addEventListener('controllerchange',()=>{if (state.accepting&&!state.reloaded){state.reloaded=true;location.reload();}});
if (!navigator.onLine&&!sw.controller){state.offlineNote='OFFLINE INSTALL REQUIRED';onOffline&&onOffline(state.offlineNote);}
return{
state,
get offlineNote(){return state.offlineNote;},
acceptUpdate(){const w=state.waiting||(state.registration&&state.registration.waiting);if (!w) return false;state.accepting=true;w.postMessage({type:'SKIP_WAITING'});return true;},
};
}
export{setupPwa};
