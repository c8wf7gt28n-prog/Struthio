"""Grounded Gemini and external-agent tasks over the existing candidate lifecycle.

The worker can investigate and revise a bounded candidate. Existing Kernel
acceptance and required-test gates remain the only source-promotion authority.
"""
from __future__ import annotations
import json
from pathlib import Path
import time
import uuid
from sdk.cli.arc1cli import workshop_contract as contract
from .project_inventory import hashes, revision
from . import workshop_sandbox, gemini_engineer

S={'type':'string','maxLength':4000}
ID={'type':'string','minLength':32,'maxLength':32}
FIELDS={
 'workshop.status':({},[]),
 'workshop.component_context':({'component':S,'expected_revision':S},['component']),
 'workshop.prepare':({'goal':S,'paths':{'type':'array','items':S},'profile':{'type':'string','enum':['arcos','ledger']},
    'provider':{'type':'string','enum':['gemini','external']},'execution':{'type':'string','enum':['isolated','reviewed']},
    'share_source':{'type':'boolean'},'component':S,'max_calls':{'type':'integer','minimum':1,'maximum':12},
    'max_runtime':{'type':'integer','minimum':30,'maximum':600},'request_key':S},['goal','paths','profile','provider','execution','request_key']),
 'workshop.context':({'id':ID},['id']),
 'workshop.inspect':({'id':ID},['id']),
 'workshop.act':({'id':ID,'request_key':S,'action':{'type':'object'}},['id','request_key','action']),
 **{('workshop.'+op):({'id':ID},['id']) for op in ('start','resume','pause','cancel')},
}
SCOPES={name:('read' if name in ('workshop.status','workshop.context','workshop.inspect','workshop.component_context') else
               'approve' if name in ('workshop.start','workshop.resume') else
               'execute' if name in ('workshop.pause','workshop.cancel') else 'candidate') for name in FIELDS}
READ_ROOTS=('workbench/','software/arcos/','software/struthio/','sdk/include/',
 'hardware/compact-arc1/R10_WORK/firmware/','hardware/compact-arc1/R10_WORK/f133/graphics_link/',
 'hardware/compact-arc1/R10_WORK/d213/fpga45_loader/','hardware/compact-arc1/R10_WORK/d213/gpu_driver/',
 'hardware/compact-arc1/R10_WORK/fpga12/rtl/','hardware/compact-arc1/R10_WORK/fpga45/rtl/')
AUTHORITY={'engineering_kernel.py','engineering_cli.py','agent_operations.py','baseline_repair.py',
 'stacy_foundation.py','stacy_contracts.py','stacy_awareness.py','activity.py','project_context.py','ledger_control.py','file_delivery.py',
 'local_brain.py','brain_runtime.py','brain_worker.py','stacy_language.py',
 'kicad_tools.py', 'kibot_tools.py', 'spice_tools.py', 'yosys_tools.py', 'pnr_tools.py', 'hdl_tools.py', 'surfer_tools.py',
 'clip_workshop.py','clip_jobs.py','clip_external.py','gemini_engineer.py','workshop_sandbox.py',
 'remote_service.py','remote_sessions.py','update_service.py','setup_arc1.py','record_io.py','project_inventory.py',
 'desktop_services.py'}

def actor(j):
    from .engineering_kernel import Principal
    return Principal(j['owner'],frozenset({'read','candidate','execute'}),tuple(j['scope']),tuple(j['authorized_tools']),mode='Autonomous')

def task(k,id,p,write=False):
    j=k.record('jobs',id)
    if j['tool']!='clip.workshop':raise ValueError('Not a workshop task')
    if write:
        k.require_owner(j,p)
        if not {'candidate','execute'}<=p.scopes:raise ValueError('Candidate and execute delegation required')
        if not all(any(n.startswith(s) if s.endswith('/') else n==s for s in p.paths) for n in j['scope']):raise ValueError('Task paths no longer delegated')
        if not set(j['authorized_tools'])<=set(p.tools):raise ValueError('Task tools no longer delegated')
    return j

def update(k,id,**values):
    with k.db() as db:
        db.execute('BEGIN IMMEDIATE')
        live=k.record('jobs',id)
        if live['state']=='Cancelled' and values.get('state') not in (None,'Cancelled'):raise ValueError('Task cancelled')
        live.update(values);k.save('jobs',live,db)
    return live

def current(k,j):
    if revision(hashes(k.root))!=j['revision']:raise ValueError('Accepted source changed; prepare a fresh task')
    c=k.record('candidates',j['candidate'])
    if c['state']!='Draft':raise ValueError('Candidate is no longer editable')
    return c

def prepare(k,a,p):
    if not {'candidate','execute'}<=p.scopes:raise ValueError('Candidate and execute delegation required')
    scope=a['paths']
    if not isinstance(scope,list) or not 1<=len(scope)<=5 or len(set(scope))!=len(scope):raise ValueError('Choose one to five distinct implementation files')
    if not a['goal'].strip() or len(a['goal'])>2000:raise ValueError('State one observable, bounded engineering goal')
    for name in scope:
        path=k.safe(name)
        if not any(name.startswith(s) if s.endswith('/') else name==s for s in p.paths):raise ValueError('File is outside current delegation')
        valid=(name.startswith(('software/arcos/src/','software/arcos/games/')) and path.suffix=='.c') if a['profile']=='arcos' else (
            name.startswith('workbench/') and path.suffix=='.py' and path.name not in AUTHORITY)
        if not valid or path.name.startswith('test_') or path.is_symlink() or path.stat().st_size>60000:
            raise ValueError('Select a small allowed implementation file; tests, policy and authority modules require a separate review route')
    if a['provider']=='gemini' and not a.get('share_source'):raise ValueError('Approve sharing the declared source context and diagnostics with Gemini')
    required=['arcos.test'] if a['profile']=='arcos' else ['ledger.kernel_tests','ledger.desktop_tests']
    if not set(required)<=set(p.tools):raise ValueError('Required checks not delegated')
    key=a['request_key']
    if not 1<=len(key)<=128:raise ValueError('Bounded request key required')
    spec={key:value for key,value in a.items() if key!='request_key'}
    with k.db() as db:
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT job FROM requests WHERE owner=? AND key=?',(p.identity,key)).fetchone()
        if old:
            j=k.record('jobs',old[0])
            if j.get('request_spec')!=spec:raise ValueError('Request key reused with different task')
            return j
        c=k.create_candidate({'goal':a['goal'],'paths':scope,'required_tools':required},p,db=db)
        id=uuid.uuid4().hex
        saved=json.loads(db.execute('SELECT payload FROM candidates WHERE id=?',(c['id'],)).fetchone()[0])
        saved['external_agent_task']=id
        k.save('candidates',saved,db)
        j={'id':id,'tool':'clip.workshop','owner':p.identity,'state':'Waiting for Approval',
           'goal':a['goal'],'scope':scope,'profile':a['profile'],'provider':a['provider'],'execution':a['execution'],
           'component':a.get('component',''),'share_source':bool(a.get('share_source')),'candidate':c['id'],
           'revision':c['revision'],'authorized_tools':required,'timeout':a.get('max_runtime',300),
           'provider_budget':{'max_calls':a.get('max_calls',6),'max_context_bytes':contract.MAX_CONTEXT,'max_output_bytes':contract.MAX_ACTION},
           'provider_calls':0,'runtime_used':0,'created':time.time(),'pid':None,'cancel':False,'pause':False,
           'request_spec':spec,'checks':{},'actions':[],'history':[],'findings':[],
           'approval_required':True,'current_operation':'Review source-sharing, paths, tools, execution mode and budgets',
           'binding':contract.binding(id,c['revision'],scope)}
        k.save('jobs',j,db);db.execute('INSERT INTO requests VALUES(?,?,?)',(p.identity,key,id))
    return j

def context(k,j):
    c=k.record('candidates',j['candidate']);source=k.candidate_root(c['id'])
    source_hashes=hashes(source)
    files=[{'path':n,'sha256':source_hashes.get(n),'bytes':(source/n).stat().st_size} for n in j['scope']]
    return {'schema':contract.CONTRACT,'task':j['id'],'binding':j['binding'],'goal':j['goal'],
      'revision':j['revision'],'source_current':revision(hashes(k.root))==j['revision'],
      'files':files,'read_roots':READ_ROOTS,'component':j['component'],'checks':j['checks'],
      'required_tools':j['authorized_tools'],'findings':j['findings'][-3:],'execution':j['execution'],
      'limits':j['provider_budget'],'calls_used':j['provider_calls'],
      'instructions':'Use tools to read actual source and diagnostics. Propose only scoped changes. Tests and authority modules are protected. Host/model results never close a physical gate. Finish with current required evidence and independent acceptance. No shell or paid fallback.'}

def diagnostics(k,j):
    result=[]
    for phase,entries in j['checks'].items():
        for tool,id in entries.items():
            child=k.record('jobs',id)
            row={'phase':phase,'tool':tool,'id':id,'state':child['state'],'revision':child['revision']}
            if child.get('evidence'):
                e=k.record('evidence',child['evidence'])
                row.update(evidence=e['id'],exit_status=e['exit_status'],stdout=e['stdout'][-7000:],
                           stderr=e['stderr'][-5000:],error=e.get('error'),environment=e['environment'])
            result.append(row)
    return result

def inspect(k,j):
    c=k.record('candidates',j['candidate'])
    return {'task':j,'source_current':revision(hashes(k.root))==j['revision'],'candidate_state':c['state'],
      'candidate_revision':revision(hashes(k.candidate_root(c['id']))),'diagnostics':diagnostics(k,j),
      'source_acceptance_requires_operator':True,'isolation':workshop_sandbox.status()}

def component_context(k,a):
    from .brain_link import dispatch
    r=dispatch(k,'links.inspect',a)
    if r['state']=='STALE':return r
    component=dict(r['component']);component['pins']=component.get('pins',[])[:24]
    return {'schema':'arc-ledger.component-context/1','state':r['state'],'revision':r['revision'],
        'component':component,'source_links':r['source_links'],'issues':r['issues'],
        'requirements':r['requirements'],'evidence_class':'DESIGN','physical_measurements':False,
        'fabrication':'HOLD','context_kind':'Native-source facts and explicit software intent; no vendor originals',
        'pins_truncated':len(r['component'].get('pins',[]))>24}

def checks(k,j):
    began=time.monotonic()
    def spent():
        live=k.record('jobs',j['id'])
        active=time.time()-live.get('run_started',time.time()) if live['state']=='Running' else time.monotonic()-began
        return live.get('runtime_used',0)+active
    c=current(k,j);phase='candidate' if c['changes'] else 'baseline'
    rev=revision(hashes(k.candidate_root(c['id']))) if phase=='candidate' else j['revision']
    if j['execution']=='isolated' and not workshop_sandbox.status()['available']:
        update(k,j['id'],state='Paused',current_operation='Automatic execution blocked: '+workshop_sandbox.status()['reason'])
        return {'state':'ISOLATION_UNAVAILABLE','phase':phase,'executed':False}
    if phase=='candidate':
        if j['execution']=='isolated':
            c['execution_approval']={'by':j['authorized_by'],'task':j['id'],'revision':rev,'at':time.time(),'isolation':workshop_sandbox.PROFILE}
            k.save('candidates',c)
        elif c.get('execution_approval',{}).get('revision')!=rev:
            update(k,j['id'],state='Waiting for Execution Approval',current_operation='Review and authorize this exact revision, then resume the task')
            return {'state':'WAITING_FOR_EXACT_EXECUTION_APPROVAL','phase':phase,'executed':False}
    jobs={}
    for tool in j['authorized_tools']:
        remaining=j['timeout']-spent()
        if remaining<=0:raise ValueError('Task runtime budget reached')
        args={'tool':tool,'timeout':max(1,min(120,remaining)),'goal':j['goal'],
              'request_key':'workshop:'+j['id']+':'+phase+':'+rev+':'+tool}
        if phase=='candidate':args['candidate']=c['id']
        if j['execution']=='isolated':args['isolation']=workshop_sandbox.PROFILE
        # Sequential fixed tools share one source workspace. Subsequent calls
        # poll the prior job instead of duplicating it after reconnect.
        prior=j['checks'].get(phase,{}).get(tool)
        old=k.record('jobs',prior) if prior else None
        child=old if old and old['revision']==rev else k.submit(args,actor(j))
        jobs[tool]=child['id']
        new=dict(k.record('jobs',j['id'])['checks']);new[phase]=dict(jobs)
        update(k,j['id'],checks=new,current_operation='Follow '+phase+' check '+tool)
        # One check at a time; ledger profile has two existing required suites.
        while k.record('jobs',child['id'])['state'] in ('Queued','Running'):
            live=k.record('jobs',j['id'])
            if live.get('cancel') or live.get('pause'):
                k.dispatch('jobs.cancel',{'id':child['id']},actor(j));raise ValueError('Task paused or cancelled during its check')
            if spent()>j['timeout']:
                k.dispatch('jobs.cancel',{'id':child['id']},actor(j));raise ValueError('Task runtime budget reached')
            time.sleep(.1)
    new=dict(k.record('jobs',j['id'])['checks']);new[phase]=jobs;update(k,j['id'],checks=new)
    return {'phase':phase,'jobs':jobs,'diagnostics':diagnostics(k,k.record('jobs',j['id']))}

def action(k,id,a,p,key):
    began=time.monotonic()
    j=task(k,id,p,True);c=current(k,j)
    if not j.get('authorized_by'):raise ValueError('Owner task authorization required')
    if j['state'] not in ('Running','Waiting for Agent','Waiting for Execution Approval'):raise ValueError('Task is not accepting actions')
    files={n:hashes(k.candidate_root(c['id']))[n] for n in j['scope']}
    # Reusing a completed receipt is idempotent even after its patch changed
    # the current source hash; it must never execute the old mutation again.
    with k.db() as db:
        db.execute('BEGIN IMMEDIATE');live=k.record('jobs',id)
        prior=next((x for x in live['actions'] if x['key']==key),None)
        if prior:
            if prior['action']!=a:raise ValueError('Action key reused with different arguments')
            if prior['state']!='done':raise ValueError('Interrupted action requires inspection; it will not be replayed automatically')
            return prior['result']
        if live.get('inflight'):raise ValueError('A task action is already in progress')
        name,args=contract.validate_action(a,expected_binding=j['binding'],files=files)
        if not isinstance(key,str) or not 1<=len(key)<=128:raise ValueError('Action key must be bounded')
        if len(live['actions'])>=80:raise ValueError('Task action budget reached')
        live['actions'].append({'key':key,'action':a,'state':'applying','at':time.time()})
        live['inflight']=key;k.save('jobs',live,db)
    try:
        source=k.candidate_root(c['id'])
        if name=='read_source':
            path=args['path']
            if not path.startswith(READ_ROOTS) or path not in c['base']:raise ValueError('Source is outside approved context roots')
            target=(source/path).resolve()
            if not target.is_relative_to(source) or target.is_symlink() or target.stat().st_size>200000:raise ValueError('Source read rejected')
            lines=target.read_text().splitlines();start=args.get('line',1)-1;count=args.get('count',100)
            result={'path':path,'sha256':hashes(source)[path],'start_line':start+1,'lines':lines[start:start+count],
                    'total_lines':len(lines),'truncated':start+count<len(lines)}
        elif name=='search_source':
            result=[]
            for path in c['base']:
                if not path.startswith(READ_ROOTS) or Path(path).suffix not in ('.py','.c','.h','.md','.json'):continue
                file=source/path
                if file.stat().st_size>200000:continue
                for number,line in enumerate(file.read_text(errors='replace').splitlines(),1):
                    if args['query'].casefold() in line.casefold():result.append({'path':path,'line':number,'text':line[:250]})
                    if len(result)>=20:break
                if len(result)>=20:break
        elif name=='inspect_component':
            if not j['component']:result={'state':'NO_COMPONENT_SELECTED'}
            else:result=component_context(k,{'component':j['component']})
        elif name=='read_diagnostics':result=diagnostics(k,j)
        elif name=='run_checks':result=checks(k,j)
        elif name=='propose':
            for patch in args['patches']:k.patch({'id':c['id'],**patch},p)
            findings=j['findings']+[{'explanation':args['explanation'],'at':time.time()}]
            update(k,id,findings=findings,current_operation='Candidate revised; run its required checks')
            result={'candidate':c['id'],'revision':revision(hashes(source)),'changed':[x['path'] for x in args['patches']],
                    'execution_review_required':j['execution']=='reviewed','accepted_source_changed':False}
        elif name=='finish':
            current_revision=revision(hashes(source))
            baseline_jobs=j['checks'].get('baseline',{})
            if set(baseline_jobs)!=set(j['authorized_tools']):raise ValueError('Run the required baseline checks first')
            for child in baseline_jobs.values():
                row=k.record('jobs',child)
                if row['state']!='Completed' or row['revision']!=j['revision']:raise ValueError('Passing source-bound baseline evidence or independent repair route required')
            candidate_jobs=j['checks'].get('candidate',{})
            if set(candidate_jobs)!=set(j['authorized_tools']):raise ValueError('Run every required candidate check first')
            for child in candidate_jobs.values():
                row=k.record('jobs',child)
                if row['state']!='Completed' or row['revision']!=current_revision:raise ValueError('Current passing candidate evidence required')
            k.transition('candidates.review',{'id':c['id']},p)
            update(k,id,state='Waiting for Approval',current_operation='Candidate passed; independent source acceptance required',summary=args['summary'])
            result={'state':'Waiting for Approval','candidate':c['id'],'accepted_source_changed':False}
        else:
            update(k,id,state='Paused',current_operation=args['reason']);result={'state':'Paused','reason':args['reason']}
        if len(json.dumps(result).encode())>24000:
            result={'state':'RESULT_TOO_LARGE','message':'Use a narrower source read or inspect evidence locally.'}
        with k.db() as db:
            db.execute('BEGIN IMMEDIATE');live=k.record('jobs',id)
            rec=next(x for x in live['actions'] if x['key']==key);rec.update(state='done',result=result)
            live.pop('inflight',None);k.save('jobs',live,db)
        return result
    except Exception as exc:
        with k.db() as db:
            db.execute('BEGIN IMMEDIATE');live=k.record('jobs',id)
            rec=next(x for x in live['actions'] if x['key']==key);rec.update(state='failed',error=str(exc))
            live.pop('inflight',None);k.save('jobs',live,db)
        raise
    finally:
        if j['state']!='Running':
            live=k.record('jobs',id)
            update(k,id,runtime_used=live.get('runtime_used',0)+time.monotonic()-began)

def control(k,op,id,p):
    j=task(k,id,p)
    k.require_owner(j,p)
    if op in ('pause','cancel'):
        if 'execute' not in p.scopes:raise ValueError('Execute scope required')
        state='Cancelled' if op=='cancel' else 'Paused'
        update(k,id,cancel=op=='cancel',pause=op=='pause',state=state,current_operation='Owner '+op)
        for entries in j['checks'].values():
            for child in entries.values():
                if k.record('jobs',child)['state'] in ('Queued','Running'):k.dispatch('jobs.cancel',{'id':child},actor(j))
        return k.record('jobs',id)
    if 'approve' not in p.scopes:raise ValueError('Owner task authorization required')
    current(k,j)
    if j['state'] not in ('Waiting for Approval','Paused','Interrupted','Waiting for Provider','Waiting for Execution Approval','Waiting for Agent'):
        raise ValueError('Task is not waiting for start or resume')
    if j.get('summary'):raise ValueError('This candidate is already awaiting source acceptance')
    if j.get('inflight'):raise ValueError('Inspect interrupted action before preparing a new task; mutations are not replayed')
    if j['runtime_used']>=j['timeout']:raise ValueError('Runtime budget exhausted; prepare a new task')
    j=update(k,id,state='Queued',authorized_by=j.get('authorized_by',p.identity),cancel=False,pause=False,
             current_operation='Resume bounded engineering',retry_after=None)
    k.launch(id)
    return j

def run(k,id):
    j=k.record('jobs',id);began=time.monotonic()
    update(k,id,run_started=time.time())
    try:
        current(k,j)
        if not j.get('authorized_by'):raise ValueError('Task has no owner authorization')
        if j['provider']=='gemini' and not gemini_engineer.available()['configured']:
            from .clip import ClipError
            raise ClipError('Configure Gemini key and model in Clip settings on this computer, then resume.','key')
        if not j['checks'].get('baseline'):
            checks(k,j)
            j=k.record('jobs',id)
            if j['state']!='Running':return
        if any(r['state']!='Completed' for r in diagnostics(k,j) if r['phase']=='baseline'):
            raise ValueError('Baseline failed; independent baseline-repair route required')
        if j['provider']=='external':
            update(k,id,state='Waiting for Agent',current_operation='Read the typed handoff and submit actual agent actions');return
        while True:
            j=k.record('jobs',id)
            if j['state']!='Running' or j.get('cancel') or j.get('pause'):break
            if j['runtime_used']+time.monotonic()-began>=j['timeout']:raise ValueError('Task runtime budget reached')
            if j['provider_calls']>=j['provider_budget']['max_calls']:
                update(k,id,state='Paused',current_operation='Provider-call budget exhausted; inspect findings and prepare another bounded task');break
            current(k,j)
            if not gemini_engineer.available()['configured']:
                from .clip import ClipError
                raise ClipError('Configure Gemini key and model in Clip settings on this computer, then resume.','key')
            # An explicit checkpoint precedes every request; a lost response
            # consumes its call budget and is never silently resubmitted.
            j=update(k,id,provider_calls=j['provider_calls']+1,current_operation='Gemini investigation turn')
            r=gemini_engineer.turn(context(k,j),j['history'],timeout=min(60,max(1,j['timeout']-j['runtime_used']-(time.monotonic()-began))))
            history=j['history']+[{'role':'model','parts':r['parts']}]
            update(k,id,history=history,model=r['model'],provider_usage=r['usage'],provider_summary=r['text'])
            responses=[]
            for index,call in enumerate(r['calls']):
                a={'binding':j['binding'],'name':call['name'],'arguments':call.get('args',{})}
                try:result=action(k,id,a,actor(j),'gemini:'+str(j['provider_calls'])+':'+str(index))
                except (ValueError,OSError,KeyError) as exc:result={'error':str(exc),'accepted_source_changed':False}
                response={'name':call['name'],'response':{'result':result}}
                if call.get('id'):response['id']=call['id']
                responses.append({'functionResponse':response})
                if k.record('jobs',id)['state']!='Running':break
            if responses:history+=[{'role':'user','parts':responses}]
            update(k,id,history=history)
            if not r['calls']:
                update(k,id,state='Paused',current_operation=r['text'] or 'Gemini stopped without another tool action');break
    except Exception as exc:
        from .clip import ClipError
        state='Waiting for Provider' if isinstance(exc,ClipError) and exc.kind in ('quota','network','key','model') else 'Paused'
        live=k.record('jobs',id)
        if live['state'] not in ('Cancelled','Paused'):
            update(k,id,state=state,current_operation=str(exc)[:1500],retry_after=time.time()+60 if state=='Waiting for Provider' else None)
    finally:
        live=k.record('jobs',id)
        update(k,id,runtime_used=live.get('runtime_used',0)+time.monotonic()-began,pid=None)

def dispatch(k,op,a,p):
    if op=='workshop.component_context':return component_context(k,a)
    if op=='workshop.status':return {'provider':gemini_engineer.available(),'isolation':workshop_sandbox.status(),
        'profiles':{'arcos':['arcos.test'],'ledger':['ledger.kernel_tests','ledger.desktop_tests']},
        'read_roots':READ_ROOTS,'automatic_source_acceptance':False,'phone_development':'DEFERRED'}
    if op=='workshop.prepare':return prepare(k,a,p)
    if op.split('.')[-1] in ('start','resume','pause','cancel'):return control(k,op.split('.')[-1],a['id'],p)
    j=task(k,a['id'],p,op=='workshop.act')
    if op=='workshop.context':return context(k,j)
    if op=='workshop.inspect':return inspect(k,j)
    return action(k,j['id'],a['action'],p,a['request_key'])
