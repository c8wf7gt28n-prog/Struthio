'use strict';
const $=id=>document.getElementById(id);
function writingPrompt(element,hint){element.placeholder='poem';if(!element.title)element.title=hint;if(!element.hasAttribute('aria-label'))element.setAttribute('aria-label',hint);element.setAttribute('aria-description',hint);}
const state={session:null,online:false,page:'Clip',generation:0,mutating:false,cap:null,proof:null,reviewed:new Map(),clipGoal:'',clipPath:'software/struthio/game.c'};
const terminal=new Set(['Completed','Failed','Cancelled','Interrupted']);
function node(tag,value='',className=''){const n=document.createElement(tag);n.textContent=value;n.className=className;return n;}
function error(e){$('error').textContent=e.message||String(e);}
function clearSession(){window.SlateDeck.clear(true);state.generation++;state.session=null;state.cap=null;state.proof=null;state.reviewed.clear();$('records').replaceChildren();$('detail').close();$('detail-body').replaceChildren();$('content').hidden=true;$('pair').hidden=false;$('install-help').hidden=false;}
function availability(){document.querySelectorAll('[data-mutation]').forEach(b=>b.disabled=!state.online||!state.session||state.mutating||b.dataset.allowed==='false');}
function connection(online,message){state.online=online;$('connection').textContent=message;$('connection').className=online?'online':'offline';$('offline').hidden=online;if(!online)window.SlateDeck.clear(true);if(online)$('last-sync').textContent='Last host response · '+new Date().toLocaleTimeString();availability();}
async function request(path,body){
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000);
  let response;
  try{response=await fetch(path,{method:body===undefined?'GET':'POST',credentials:'same-origin',cache:'no-store',signal:controller.signal,headers:body===undefined?{}:{'Content-Type':'application/json','X-Ledger-CSRF':state.session?.csrf||''},body:body===undefined?undefined:JSON.stringify(body)});}
  catch(e){connection(false,'Laptop unreachable · reconnect when ready');e.uncertain=true;throw e;}
  finally{clearTimeout(timer);}
  const data=await response.json();
  if(!response.ok){
    if(response.status===401){clearSession();connection(true,'Pairing required · session expired or revoked');}
    if(response.status===503)connection(false,'Remote access disabled or host unavailable');
    const e=new Error(data.error?.message||data.error||('Request failed: '+response.status));e.status=response.status;throw e;
  }
  connection(true,'Connected · '+(state.session?.host_platform||'Graphite host'));return data;
}
async function call(operation,params={}){const r=await request('/api/call',{operation,params});if(!r.ok)throw Error(r.error.message);return r.result;}
function allowed(op){return Boolean(state.cap?.operations?.[op]);}
function button(parent,label,fn,op=null){const b=node('button',label);if(op){b.dataset.mutation='true';b.dataset.allowed=String(allowed(op));}
  b.onclick=async()=>{if(b.disabled)return;$('error').textContent='';if(op){state.mutating=true;availability();}
    try{await fn();}catch(e){error(e);}finally{state.mutating=false;availability();}};parent.append(b);return b;}
function jobButton(parent,label,tool){const b=button(parent,label,()=>submit(tool),'jobs.submit');
  b.dataset.allowed=String(allowed('jobs.submit')&&Boolean(state.cap?.tools?.includes(tool)));
  if(b.dataset.allowed==='false')b.title='This paired-device grant does not include '+tool+'.';return b;}
function card(parent,title,description=''){const c=node('article','','card');c.append(node('h3',title));if(description)c.append(node('p',description));parent.append(c);return c;}
function actions(parent){const a=node('div','','actions');parent.append(a);return a;}
function badge(parent,value){parent.append(node('span',value,'badge '+(value==='Completed'||value==='PASS'?'good':value==='Failed'||value==='INVALID'?'bad':'')));}
function details(parent,title,data){const d=document.createElement('details');d.append(node('summary',title),node('pre',typeof data==='string'?data:JSON.stringify(data,null,2)));parent.append(d);return d;}
function modal(title){$('detail-title').textContent=title;$('detail-body').replaceChildren();if(!$('detail').open)$('detail').showModal();return $('detail-body');}
function pendingRead(){try{return JSON.parse(localStorage.getItem('ledger.pending.1_9')||'null');}catch{return null;}}
function pendingWrite(p){try{if(p)localStorage.setItem('ledger.pending.1_9',JSON.stringify(p));else localStorage.removeItem('ledger.pending.1_9');}catch{}}
function pendingView(){const box=$('pending');box.replaceChildren();const p=pendingRead();if(!p)return;
  const same=p.identity===state.session?.identity;
  const c=card(box,same?'Request awaiting confirmation':'Receipt from a previous pairing',same?'Resume with the same request key to avoid a duplicate job. The receipt survives closing the PWA.':'Ask the owner to locate this request in Graphite before starting it again. A new pairing cannot silently replay another device identity.');
  if(same)button(c,'Resume request',()=>p.operation==='clip.prepare'?prepareClip(p.params):p.operation==='clip.submit'?submitClip(p.params):submit(p.tool),p.operation||'jobs.submit');
  button(c,'Dismiss receipt',()=>{if(confirm('Dismiss the local receipt? This does not stop or delete any job on the host.')){pendingWrite(null);pendingView();}});
}
async function prepareClip(params){
  let p=pendingRead();if(p&&p.identity!==state.session.identity)throw Error('Resolve the receipt from the previous pairing first.');
  if(p&&(p.operation!=='clip.prepare'||JSON.stringify(p.params)!==JSON.stringify(params)))throw Error('Resolve the pending request first.');
  if(!p){p={key:crypto.randomUUID(),operation:'clip.prepare',params,identity:state.session.identity};pendingWrite(p);}
  try{const j=await call('clip.prepare',{...p.params,request_key:p.key});pendingWrite(null);await render();await showJob(j.id);}
  catch(e){if(!e.uncertain)pendingWrite(null);pendingView();throw e;}
}
async function submitClip(params){
  let p=pendingRead();if(p&&p.identity!==state.session.identity)throw Error('Resolve the receipt from the previous pairing first.');
  if(p&&(p.operation!=='clip.submit'||JSON.stringify(p.params)!==JSON.stringify(params)))throw Error('Resolve the pending request first.');
  if(!p){p={key:crypto.randomUUID(),operation:'clip.submit',params,identity:state.session.identity};pendingWrite(p);}
  try{const j=await call('clip.submit',{...p.params,request_key:p.key});pendingWrite(null);state.page='Jobs';await render();await showJob(j.id);}
  catch(e){if(!e.uncertain)pendingWrite(null);pendingView();throw e;}
}
async function submit(tool){
  let p=pendingRead();if(p&&p.identity!==state.session.identity)throw Error('Resolve the receipt from the previous pairing first.');
  if(p&&(p.operation||p.tool!==tool))throw Error('Resolve the pending '+p.tool+' request first.');
  if(!p){p={key:crypto.randomUUID(),tool,identity:state.session.identity};pendingWrite(p);}
  try{const j=await call('jobs.submit',{tool,request_key:p.key,timeout:300,goal:'iPhone requested '+tool});pendingWrite(null);state.page='Clip';await render();await showJob(j.id);return j;}
  catch(e){if(!e.uncertain)pendingWrite(null);pendingView();throw e;}
}
function download(name,data){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}

async function showEvidence(id){
  const e=await call('evidence.read',{id}),body=modal('Engineering result');badge(body,e.state);
  body.append(node('h3',e.tool),node('p',e.class+' · host evidence; not physical-console proof'),node('p','Revision '+e.revision,'mono'),node('p','Exit '+e.exit_status+' · '+Number(e.duration_seconds||0).toFixed(2)+' seconds'));
  if(e.tool.startsWith('proof.')){const bound=await call('hardware.proof.result',{id});body.append(node('p',bound.source_current?'Hardware/checker hashes are current.':'STALE hardware/checker hashes — rerun qualification.','notice'));}
  const d=e.diagnostics;
  if(d?.cases||d?.checks){for(const c of (d.cases||d.checks)){const row=node('p');badge(row,(c.passed??c.pass)?'PASS':'FAIL');row.append(document.createTextNode(' '+(c.id||c.name)));body.append(row);}}
  if(d?.blockers)body.append(node('h3','Blocked checks'),node('pre',d.blockers.join('\n')));
  details(body,'Standard output',e.stdout||'No output');details(body,'Errors',e.stderr||e.error||'No errors recorded');details(body,'Artifacts',e.artifacts||[]);
  details(body,'Full reproducible record',e);button(body,'Download evidence JSON',()=>download('ledger-evidence-'+e.id+'.json',e));
}
async function showJob(id){const j=await call('jobs.get',{id}),body=modal('Graphite · job progress');badge(body,j.state);body.append(node('h3',j.goal||j.tool),node('p',j.tool),node('p',j.id,'mono'),node('p','Step: '+j.current_operation),node('p','Requested by '+j.owner),node('p','Runtime limit: '+j.timeout+' s'));if(j.error)body.append(node('p',j.error,'error'));details(body,'Scope and job record',j);if(j.evidence)button(body,'Read test evidence',()=>showEvidence(j.evidence));
  button(body,'Refresh this job',()=>showJob(id));
  if(j.owner===state.session.identity||state.session.scopes.includes('approve'))for(const [label,op] of (['Queued','Running'].includes(j.state)?[['Pause','pause'],['Stop','cancel']]:['Paused','Interrupted'].includes(j.state)?[['Resume after checks','resume']]:[]))button(body,label,async()=>{await call('jobs.'+op,{id});await showJob(id);},'jobs.'+op);
  if(j.tool==='clip.external'){await externalTask(body,j);}
  if(j.tool==='clip.loop'&&j.state==='Waiting for Approval'&&!j.authorized_by){
    body.append(node('h3','Review bounded scope'),node('pre',JSON.stringify({files:j.scope,tools:j.authorized_tools,iterations:j.iteration_limit,seconds:j.timeout,provider:j.task.provider,budget:j.provider_budget,share_source:j.task.share_source},null,2)));
    if(allowed('clip.authorize'))button(body,'Authorize this scope',async()=>{if(confirm('Authorize exactly these files, tools and provider limits? This may send approved source to the listed provider.')){await call('clip.authorize',{id:j.id});await showJob(j.id);}},'clip.authorize');
    else body.append(node('p','This task stays paused until an authorized laptop operator approves its scope.'));
  }
}

async function externalTask(body,j){
  const status=await call('clip.inspect',{id:j.id});
  body.append(node('p',status.source_current?'Source snapshot is current.':'Source has changed. This recorded task needs a new snapshot.','notice'));
  body.append(node('p','External AI task · no automatic model call. One ARC-OS implementation file, fixed tests, independent source acceptance. Runtime names in proposals are agent declarations.','muted'));
  button(body,'Read agent handoff',async()=>{const ctx=await call('clip.context',{id:j.id}),v=modal('Graphite · agent handoff');details(v,'Exact source and scope',ctx);button(v,'Download handoff JSON',()=>download('clip-task-'+j.id+'.json',ctx));});
  button(body,'Review candidate diff',async()=>{const rows=await call('candidates.list'),c=rows.find(x=>x.id===j.candidate);await reviewCandidate(c);});
  for(const test of status.tests){const row=card(body,test.phase+' · '+test.state);button(row,'Follow '+test.phase+' test',()=>showJob(test.id));}
  if(j.owner!==state.session.identity&&!state.session.scopes.includes('approve'))return;
  if(['Completed','Cancelled','Failed'].includes(j.state))return;
  if(status.source_current){
    button(body,'Run task baseline',async()=>{const child=await call('clip.test',{id:j.id,phase:'baseline'});await showJob(child.id);},'clip.test');
    if(j.state==='Waiting for Agent'){
      const d=document.createElement('details');d.append(node('summary','Attach an external agent proposal'));body.append(d);
      const proposal=document.createElement('textarea');proposal.setAttribute('aria-label','Agent proposal JSON');writingPrompt(proposal, 'binding, agent, explanation, patch {path, sha256, content}');d.append(proposal);
      button(d,'Attach bounded proposal',async()=>{const data=JSON.parse(proposal.value);await call('clip.propose',{id:j.id,proposal:data});await showJob(j.id);},'clip.propose');
    }
    if(j.proposal&&status.candidate_state==='Draft'){
      body.append(node('p',status.native_execution_authorized?'This exact candidate revision has execution authorization.':'Review the diff on the owner device and authorize this exact revision before running native tests.','notice'));
      button(body,'Run task candidate',async()=>{const child=await call('clip.test',{id:j.id,phase:'candidate'});await showJob(child.id);},'clip.test');
      button(body,'Submit passing candidate for source review',async()=>{await call('clip.finish',{id:j.id});await showJob(j.id);},'clip.finish');
    }
  }
}

async function inspectProof(){
  const r=await call('hardware.proof.inspect');state.proof=r;const body=modal('Hardware proof · six domains');
  body.append(node('p','Design feasibility: '+r.design_feasibility.replaceAll('_',' '),'notice'),node('p','Fabrication HOLD. Host checks cannot close physical gates.'));
  for(const f of r.findings){const c=card(body,f.id+' · '+f.component,f.claim);badge(c,f.status);c.append(node('p',f.evidence_state,'muted'));const d=document.createElement('details');d.append(node('summary','Missing proof & next check'),node('pre',f.missing_proof.join('\n')),node('p',f.next_executable_check));
    for(const s of f.sources){button(d,s.path.split('/').pop(),async()=>{const x=await call('files.read',{path:s.path});const v=modal(s.path.split('/').pop());v.append(node('p',x.path,'mono'),node('p','SHA-256 '+x.sha256,'mono'),node('pre',x.content));});}c.append(d);}
  jobButton(body,'Run hardware qualification','proof.qualify');
  button(body,'Trace missing FPGA bitstream',async()=>{const t=await call('hardware.proof.trace',{fault:'missing_fpga_bitstream',expected_sources:r.source_hashes}),v=modal('Dependency fault trace');v.append(node('p','Declared dependency model only; physical recovery remains unproven.','notice'));for(const n of t.graph.nodes){const c=card(v,n.title,n.missing_proof);badge(c,t.graph.fault.unavailable.includes(n.id)?'UNAVAILABLE (model)':n.status);}details(v,'Graph and source binding',t);});
}

async function workspace(view){
  const [info,jobs,candidates]=await Promise.all([call('project.inspect'),call('jobs.list'),call('candidates.list')]);
  const c=card(view,'ARC-1 Console','Your canonical project, running on '+state.session.host_platform+'.');badge(c,'FABRICATION HOLD');c.append(node('p','Revision '+info.revision,'mono'));
  const grid=node('div','','metric-grid');view.append(grid);
  for(const [label,value] of [['Active jobs',jobs.filter(j=>['Running','Queued'].includes(j.state)).length],['Awaiting review',candidates.filter(c=>c.state==='Waiting for Approval').length]]){const m=node('div','','metric');m.append(node('b',String(value)),node('small',label));grid.append(m);}
  const proof=card(view,'Hardware Proof Laboratory','Inspect power, exact pins, timing, boot, interchip links and physical proof gaps.');const a=actions(proof);button(a,'Inspect findings',inspectProof);jobButton(a,'Run qualification','proof.qualify');
  const os=card(view,'ARC-OS · Host development','Controller launcher, portable SDK and separate games. F133 boot remains unproven.');const oa=actions(os);
  for(const [label,tool] of [['Build launcher','arcos.build'],['Test ARC-OS','arcos.test'],['Inspect dependencies','arcos.dependencies'],['Kernel host probe','arcos.kernel_probe']])jobButton(oa,label,tool);
  const source=card(view,'Find in project','Search real engineering sources.');const input=document.createElement('input');writingPrompt(input, 'Signal, filename or source text');input.setAttribute('aria-label','Search source');source.append(input);button(source,'Search source',async()=>{const rows=await call('files.search',{query:input.value.trim()});const body=modal('Search results');for(const hit of (Array.isArray(rows)?rows:rows.matches||[])){const c=card(body,hit.path,hit.text||hit.line_text||JSON.stringify(hit));button(c,'Open file',async()=>{const f=await call('files.read',{path:hit.path}),v=modal(hit.path);v.append(node('p',f.sha256,'mono'),node('pre',f.content));});}if(!body.childNodes.length)body.append(node('p','No matches.'));});
  const device=card(view,state.session.device_name,'Session expires '+new Date(state.session.expires*1000).toLocaleTimeString());device.append(node('p',state.session.scopes.includes('approve')?'Review approvals enabled by laptop operator.':'Approvals stay on the laptop.','muted'));
  device.append(node('p','Add to Home Screen: open this private address in Safari, tap Share → Add to Home Screen. Keep the laptop awake.','muted'));
  button(device,'Disconnect & revoke this device',async()=>{await request('/api/revoke',{});pendingWrite(null);state.session=null;state.cap=null;state.reviewed.clear();$('records').replaceChildren();$('detail').close();$('detail-body').replaceChildren();$('content').hidden=true;$('pair').hidden=false;connection(true,'Disconnected · pair again to continue');});
}
async function jobsPage(view){const rows=await call('jobs.list');if(!rows.length)view.append(node('p','No engineering jobs yet. Start a supported check from Workspace or STRUTHIO.','empty'));
  for(const j of rows){const c=card(view,j.tool,j.goal);badge(c,j.state);c.append(node('p',j.id,'mono'),node('p',j.current_operation||'Queued','muted'));const a=actions(c);button(a,'Details',()=>showJob(j.id));if(j.evidence)button(a,'Evidence',()=>showEvidence(j.evidence));
    if(j.owner===state.session.identity||state.session.scopes.includes('approve')){for(const [label,op] of (['Queued','Running'].includes(j.state)?[['Pause','pause'],['Stop','cancel']]:['Paused','Interrupted'].includes(j.state)?[['Resume after checks','resume']]:[]))button(a,label,async()=>{await call('jobs.'+op,{id:j.id});await render();},'jobs.'+op);}
  }
}
async function struthio(view){const c=card(view,'STRUTHIO · native C','Build, test and replay the portable game on your laptop. Physical ARC-1 cartridge execution remains unverified.');const a=actions(c);
  for(const [label,tool] of [['Build','struthio.build'],['Run parity tests','struthio.test'],['Run replay','struthio.replay'],['Package host artifact','struthio.package']])jobButton(a,label,tool);
  const f=card(view,'Last captured host frame','A recorded frame from the laptop, not a live video stream.');const img=document.createElement('img');img.className='frame';img.alt='Host-rendered STRUTHIO frame';img.src='/api/frame';img.onerror=()=>{img.remove();f.append(node('p','No captured frame available. Capture one in the desktop STRUTHIO workspace.','muted'));};f.append(img);
  const list=(await call('evidence.list')).filter(e=>e.tool.startsWith('struthio.'));if(!list.length)view.append(node('p','No STRUTHIO evidence recorded yet.','empty'));for(const e of list.slice(0,5)){const r=card(view,e.tool);badge(r,e.state);button(r,'Read result',()=>showEvidence(e.id));}
}
async function reviewCandidate(c){
  const d=await call('candidates.diff',{id:c.id}),body=modal('Candidate review');body.append(node('h3',c.goal),node('p',c.id,'mono'));badge(body,c.state);
  const diffText=d.changes.map(x=>x.diff).join('\n');const pre=node('pre');for(const line of diffText.split('\n')){const s=node('span',line+'\n',line.startsWith('+')?'diff-add':line.startsWith('-')?'diff-remove':'');pre.append(s);}body.append(pre);
  state.reviewed.set(c.id,JSON.stringify(d));const evidence=await call('evidence.list');const candidate=evidence.find(e=>e.candidate===c.id),baseline=candidate&&evidence.find(e=>e.candidate===null&&e.tool===candidate.tool);
  if(candidate)button(body,'Candidate test result',()=>showEvidence(candidate.id));
  if(candidate&&baseline)button(body,'Compare with baseline',async()=>{const result=await call('evidence.compare',{baseline:baseline.id,candidate:candidate.id});const v=modal('Baseline / candidate');v.append(node('p','Baseline: '+(result.baseline_passed?'PASS':'FAIL')+' · Candidate: '+(result.candidate_passed?'PASS':'FAIL')));v.append(node('p','Accepted source current: '+result.accepted_source_current+' · Candidate current: '+result.candidate_current));details(v,'Source-bound comparison',result);});
  if(c.state==='Draft'&&allowed('candidates.authorize_execution'))button(body,'Authorize this exact candidate for native tests',async()=>{const current=await call('candidates.diff',{id:c.id});if(JSON.stringify(current)!==state.reviewed.get(c.id))throw Error('Diff changed. Review again.');if(confirm('Run this exact native candidate under your host account? This is not an OS sandbox.'))await call('candidates.authorize_execution',{id:c.id});},'candidates.authorize_execution');
  if(c.state==='Waiting for Approval'){
    body.append(node('p','Acceptance requires fresh tests. A failing baseline needs a separately reviewed, source-bound repair authorization; the kernel checks every gate again.','notice'));
    const repair=await call('repairs.inspect',{id:c.id});
    if(repair.repair){details(body,'Failing baseline repair record',repair);if(repair.current&&!repair.authorized&&repair.repair.review&&allowed('repairs.authorize'))button(body,'Authorize independently reviewed repair',async()=>{if(confirm('Authorize this exact failing-baseline exception? Failed evidence is retained. Source acceptance is a separate action.')){await call('repairs.authorize',{id:c.id,binding:repair.repair.binding});await reviewCandidate(c);}},'repairs.authorize');}
    if(allowed('candidates.accept'))button(body,'Accept reviewed candidate',async()=>{const current=await call('candidates.diff',{id:c.id});if(JSON.stringify(current)!==state.reviewed.get(c.id))throw Error('Candidate changed. Reopen and review the new diff.');if(confirm('Apply this reviewed candidate to accepted source?')){await call('candidates.accept',{id:c.id});$('detail').close();await render();}},'candidates.accept');
    else body.append(node('p','This session cannot accept source. Review and approve from the laptop.'));
    if(c.owner===state.session.identity||state.session.scopes.includes('approve'))button(body,'Reject candidate',async()=>{if(confirm('Reject this candidate and retain its evidence?')){await call('candidates.reject',{id:c.id});$('detail').close();await render();}},'candidates.reject');
  }
}
async function clip(view){
  const [overview,templates]=await Promise.all([call('clip.overview'),call('tasks.templates')]);
  const welcome=card(view,'What shall we build next?','Carry the same jobs, source and evidence from the ThinkPad to your phone.');welcome.classList.add('clip-welcome');const mascot=window.SlateDeck.bird('clip-mascot');welcome.prepend(mascot);
  welcome.append(node('span','STACY · OWNER-HOSTED','eyebrow'),node('p','Your chosen AI agent proposes. Graphite isolates, tests and records. You review the change.','muted'));
  const task=card(view,'One bounded AI task','Prepare an ARC-OS source handoff for your authorized Claude, Codex or other external agent. Graphite does not invoke a model automatically.');
  const taskGoal=document.createElement('textarea');writingPrompt(taskGoal, 'Which observable defect should the agent investigate?');taskGoal.setAttribute('aria-label','Bounded task goal');task.append(taskGoal);
  const taskPath=document.createElement('input');taskPath.value='software/arcos/src/host.c';taskPath.setAttribute('aria-label','ARC-OS implementation file');task.append(taskPath);
  button(task,'Prepare isolated AI task',()=>prepareClip({goal:taskGoal.value.trim(),path:taskPath.value.trim()}),'clip.prepare').classList.add('primary');
  button(welcome,'Inspect hardware coverage',async()=>{
    const r=await call('hardware.coverage.inspect'),v=modal('ARC-1 hardware coverage');
    v.append(node('p',r.totals.components+' components · '+r.totals.interfaces+' interface/mechanical records'),node('p',r.totals.unmapped+' unmapped · '+r.totals.with_gaps+' with open validation gaps','notice'),node('p','Revision '+r.revision,'mono'));
    button(v,'Plan source reconciliation',()=>showPlan('hardware-coverage','Reconcile current hardware sources'));
    details(v,'All inventory records and check requirements',r);
  });
  const chooser=document.createElement('select');chooser.setAttribute('aria-label','Graphite task');
  for(const t of templates.templates){const opt=node('option',t.title);opt.value=t.id;chooser.append(opt);}welcome.append(chooser);
  const goal=document.createElement('textarea');writingPrompt(goal, 'Tell Graphite the specific problem');goal.setAttribute('aria-label','Task goal');goal.value=state.clipGoal;goal.oninput=()=>state.clipGoal=goal.value;const goalDetails=document.createElement('details');goalDetails.append(node('summary','Add a specific goal (optional)'),goal);welcome.append(goalDetails);
  const planButton=button(welcome,'Plan with Graphite',()=>showPlan(chooser.value,goal.value));planButton.classList.add('primary');
  const follow=card(view,'Continue your work',overview.active_jobs.length+' active or paused jobs · '+overview.pending_candidates.length+' candidates awaiting review');
  for(const j of overview.active_jobs.slice(0,4)){const r=card(follow,j.goal||j.tool,j.current_operation);badge(r,j.state);button(r,'Follow job',()=>showJob(j.id));}
  for(const c of overview.pending_candidates.slice(0,4)){const r=card(follow,c.goal,'Source is unchanged until an authorized operator accepts.');button(r,'Review source diff',()=>reviewCandidate(c));}
  if(!overview.active_jobs.length&&!overview.pending_candidates.length)follow.append(node('p','No pending work. Start with a read-only plan above.','muted'));
  for(const e of overview.recent_results.slice(0,3)){const row=card(view,(e.state==='Completed'?'Check completed: ':'Needs attention: ')+e.tool);badge(row,e.state);button(row,'Open result',()=>showEvidence(e.id));}
  const map=actions(view);button(map,'Where does this file belong?',()=>showAuthority());button(map,'Agent handoff',async()=>{const h=await call('agent.handoff');const v=modal('Agent handoff');v.append(node('p','Same project and permissions for Graphite, CLI, MCP and this phone.'));details(v,'Current handoff',h);button(v,'Download handoff',()=>download('ledger-agent-handoff.json',h));});
  const advanced=document.createElement('details');advanced.className='card';advanced.append(node('summary','Advanced · local commands and cloud proposal'));view.append(advanced);
  await clipAdvanced(advanced);
}
async function showPlan(template,goal){
  const plan=await call('tasks.plan',{template,goal}),v=modal('Graphite · review the plan');
  v.append(node('h3',plan.title),node('p',plan.goal),node('p','Read-only plan. Nothing has run or changed.','notice'),node('p','Baseline limit: '+plan.limits.runtime_seconds+' seconds · no provider calls.'));
  v.append(node('p','Candidate scope: '+(plan.candidate_scope.join(', ')||'Read/review only'),'mono'));
  const steps=node('ol');for(const step of plan.steps)steps.append(node('li',step));const workflow=document.createElement('details');workflow.append(node('summary','Engineering workflow'),steps);v.append(workflow);
  for(const blocker of plan.blockers)v.append(node('p',blocker,'error'));
  details(v,'Scope, limits and approvals',plan);
  for(const path of plan.source_reads)button(v,'Read '+path.split('/').pop(),()=>openSource(path));
  if(template==='hardware-dependency')button(v,'Inspect source-linked hardware findings',inspectProof);
  if(template==='review-candidate')button(v,'Open candidates',async()=>{const rows=await call('candidates.list'),body=modal('Candidates');for(const c of rows){const r=card(body,c.goal,c.state);button(r,'Review source diff',()=>reviewCandidate(c));}if(!rows.length)body.append(node('p','No candidates yet.'));});
  if(plan.proposed_job){const b=button(v,'Run this baseline check',async()=>{const current=await call('project.inspect');if(current.revision!==plan.source_revision)throw Error('Source changed. Ask Graphite for a fresh plan.');await submit(plan.proposed_job.params.tool);},'jobs.submit');if(plan.blockers.length){b.dataset.allowed='false';b.disabled=true;}}
  availability();
}
async function openSource(path){const f=await call('files.read',{path}),v=modal(path);v.append(node('p',f.sha256,'mono'),node('pre',f.content));}
async function showAuthority(prefix='',offset=0){
  const doc=await call('project.authority',{prefix,offset,limit:20}),v=modal('Project file authority');
  v.append(node('p',doc.total+' matching source/reference files. Historical snapshots are retained, not competing implementations.'));
  const input=document.createElement('input');input.setAttribute('aria-label','File prefix');writingPrompt(input, 'workbench/ or software/struthio/');input.value=prefix;v.append(input);button(v,'Find files',()=>showAuthority(input.value));
  for(const row of doc.files){const c=card(v,row.path,row.authority_reason);badge(c,row.classification);c.append(node('p',row.protected?'Protected / reference':'Editable only within delegated scope','muted'));details(c,'Ownership, hashes and references',row);button(c,'Read source',()=>openSource(row.path));}
  if(doc.next_offset!==null)button(v,'Next files',()=>showAuthority(prefix,doc.next_offset));
}
async function clipAdvanced(view){
  const local=card(view,'Graphite · local investigation','These commands read actual Graphite records; they do not call a cloud model.');const a=actions(local);button(a,'Investigate hardware',inspectProof);jobButton(a,'Run STRUTHIO tests','struthio.test');
  const command=document.createElement('input');writingPrompt(command, '/status · /jobs · /search text · /read path');command.setAttribute('aria-label','Graphite local command');local.append(command);button(local,'Send local command',async()=>{const [name,...args]=command.value.trim().split(/\s+/),arg=args.join(' '),ops={'/status':['project.inspect',{}],'/jobs':['jobs.list',{}],'/search':['files.search',{query:arg}],'/read':['files.read',{path:arg}]};if(!ops[name])throw Error('Use /status, /jobs, /search text or /read path.');const r=await call(...ops[name]),v=modal('Graphite · local result');v.append(node('p','Deterministic local service, no cloud provider used.','muted'),node('pre',JSON.stringify(r,null,2)));});
  const form=card(view,'Bounded cloud investigation','Gemini must be configured on the laptop. One file, one proposal, one provider call, 300 seconds. Laptop scope approval comes first.');
  const goal=document.createElement('textarea');writingPrompt(goal, 'Describe one testable problem');goal.value=state.clipGoal;goal.setAttribute('aria-label','Engineering goal');goal.oninput=()=>state.clipGoal=goal.value;form.append(goal);
  const path=document.createElement('input');path.value=state.clipPath;path.setAttribute('aria-label','Permitted file');path.oninput=()=>state.clipPath=path.value;form.append(path);
  const label=node('label','','consent'),consent=document.createElement('input');consent.type='checkbox';label.append(consent,document.createTextNode('I authorize sending this file and diagnostics to Gemini.'));form.append(label);
  button(form,'Submit for scope approval',async()=>{if(!goal.value.trim()||!consent.checked)throw Error('Enter a goal and authorize source sharing.');await submitClip({goal:goal.value,paths:[path.value],provider:'gemini',max_iterations:1,max_provider_calls:1,max_runtime:300,share_source:true});},'clip.submit');
  for(const c of await call('candidates.list')){const row=card(view,c.goal);badge(row,c.state);row.append(node('p',c.id,'mono'));button(row,'Review source diff',()=>reviewCandidate(c));}
}
async function evidencePage(view){const list=await call('evidence.list');if(!list.length)view.append(node('p','No results recorded yet. Run a supported check to create reproducible evidence.','empty'));for(const e of list){const c=card(view,e.tool);badge(c,e.state);c.append(node('p',e.class+' · '+new Date(e.created*1000).toLocaleString(),'muted'),node('p',e.revision,'mono'));button(c,'Inspect result',()=>showEvidence(e.id));}}

async function progressPage(view){
  const r=await call('deployment.progress');
  view.append(node('p',r.work_held?'Work is held on the owner computer.':'Read-only work summaries from the owner computer.','notice'));
  if(!r.tasks.length)view.append(node('p','No continuing assignments to display.','empty'));
  for(const t of r.tasks){const c=card(view,t.title);badge(c,t.state);if(t.reason)c.append(node('p',t.reason));c.append(node('p',t.attempts+' attempts · '+t.reserved_tokens+' reserved tokens','muted'));}
  view.append(node('p','This page contains no approval or execution controls.','muted'));
}

async function render(){
  if(!state.session)return;const generation=++state.generation,page=state.page,view=node('div');$('error').textContent='';
  try{await ({Progress:progressPage,Workspace:workspace,Clip:clip,STRUTHIO:struthio,Jobs:jobsPage,Evidence:evidencePage,Windows:(v)=>window.SlateDeck.render(v,{call,error})}[page])(view);
    if(generation!==state.generation)return;$('records').replaceChildren(...view.childNodes);$('heading').textContent=page==='Windows'?'Window Deck':page;$('note').textContent='Engineering runs on your laptop. Fabrication remains HOLD.';document.querySelectorAll('nav button').forEach(b=>{b.classList.toggle('active',b.dataset.page===page);b.setAttribute('aria-current',b.dataset.page===page?'page':'false');});pendingView();availability();
  }catch(e){if(generation===state.generation)error(e);}
}
async function connect(refresh=true){try{state.session=await request('/api/session');state.cap=await call('capabilities');connection(true,'Connected · '+state.session.host_platform);$('pair').hidden=true;$('install-help').hidden=true;$('content').hidden=false;if(refresh)await render();}catch(e){error(e);}}
$('pair-form').onsubmit=async e=>{e.preventDefault();const b=$('connect');b.disabled=true;try{await request('/api/pair',{code:$('code').value.trim(),device_name:$('device-name').value.trim()});$('code').value='';await connect();}catch(err){error(err);}finally{b.disabled=false;}};
$('reconnect').onclick=()=>connect();$('refresh').onclick=()=>render();$('close-detail').onclick=()=>$('detail').close();
const slateNav=document.querySelector('nav [data-page=Clip] img');if(slateNav)slateNav.replaceWith(window.SlateDeck.bird());
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{window.SlateDeck.clear(true);state.page=b.dataset.page;render();});
window.addEventListener('offline',()=>connection(false,'Laptop unreachable · phone offline'));
window.addEventListener('online',()=>connect());
if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js').catch(()=>{});
connect().finally(()=>{$('connect').disabled=false;});setInterval(async()=>{if(document.hidden||state.mutating||!state.session)return;try{state.session=await request('/api/session');if(state.page==='Windows')await window.SlateDeck.verify({call,error});if(['Jobs','Clip','Progress'].includes(state.page)&&!$('detail').open&&!$('records').contains(document.activeElement))await render();}catch(e){error(e);}},15000);
