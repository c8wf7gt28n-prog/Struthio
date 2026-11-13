"""Finite supervised study and conservative idle admission via existing Kernel jobs."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, sys, time, uuid
from pathlib import Path
from sdk.cli.arc1cli import study_contracts as c,learning_contracts as learning,record_store as records
from . import intake_service as intake,reference_service as refs,memory_service as memory,activity,record_io,brain_runtime
ID=intake.ID;SHA=intake.SHA;TEXT=intake.TEXT
FIELDS={
 'study.status':({},[]),'study.configure':({'limits':{'type':'object'}},['limits']),
 'study.create':({'goal':{'type':'string','maxLength':500},'unknowns':{'type':'array'},'references':{'type':'array'}},['goal','unknowns','references']),
 'study.list':({},[]),'study.get':({'id':ID},['id']),
 'study.advance':({'id':ID},['id']), 'study.pause':({'id':ID,'reason':intake.REASON},['id','reason']),
 'study.resume':({'id':ID},['id']), 'study.rebind':({'id':ID,'namespace':ID,'reason':intake.REASON},['id','namespace','reason']),
 'study.idle.enable':({'id':ID,'enabled':{'type':'boolean'}},['id','enabled']), 'study.idle.poll':({},[]),
 'study.procedure.test':({'id':ID,'reference':{'type':'object'}},['id','reference']),
 'study.procedure.run':({'id':ID,'reference':{'type':'object'}},['id','reference']),
 'study.procedure.review':({'id':ID,'approved':{'type':'boolean'},'reason':intake.REASON},['id','approved','reason']),
 'study.radar':({},[]),
 'study.edition.export':({'destination':TEXT,'key_path':TEXT},['destination','key_path']),
 'study.edition.restore':({'path':TEXT,'key_path':TEXT},['path','key_path'])}
SCOPES={op:'read' if op in {'study.status','study.list','study.get','study.radar'} else 'execute' if op in {'study.advance','study.pause','study.idle.poll','study.procedure.test','study.procedure.run'} else 'approve' for op in FIELDS}
JOB_TOOLS={'study.read'}
OPTIONS={'type':'object','additionalProperties':False,'properties':{'id':ID,'attempt':ID,'idle':{'type':'boolean'}},'required':['id','attempt','idle']}
KINDS={'session','settings','presence'}
TERMINAL={'Completed','Failed','Cancelled','Interrupted'}
def ensure(db):db.execute('CREATE TABLE IF NOT EXISTS stacy_study(owner TEXT,kind TEXT,id TEXT,payload TEXT,sha256 TEXT,PRIMARY KEY(owner,kind,id))')
def put(db,owner,kind,ident,value):
    if kind not in KINDS:raise ValueError('STUDY_RECORD_KIND')
    raw=records.canonical(value)
    if len(raw)>262144:raise ValueError('STUDY_RECORD_BOUND')
    if db.execute('SELECT count(*) FROM stacy_study WHERE owner=?',(owner,)).fetchone()[0]>=512 and not db.execute('SELECT 1 FROM stacy_study WHERE owner=? AND kind=? AND id=?',(owner,kind,ident)).fetchone():raise ValueError('STUDY_OWNER_RECORD_BOUND')
    db.execute('INSERT OR REPLACE INTO stacy_study VALUES(?,?,?,?,?)',(owner,kind,ident,raw.decode(),hashlib.sha256(raw).hexdigest()))
def get(db,owner,kind,ident,default=None):
    row=db.execute('SELECT payload,sha256 FROM stacy_study WHERE owner=? AND kind=? AND id=?',(owner,kind,ident)).fetchone()
    if row is None:
        if default is not None:return dict(default)
        raise ValueError('STUDY_NOT_FOUND_OR_NOT_OWNED')
    if hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise ValueError('STUDY_RECORD_CORRUPT')
    return records.strict(row[0])
def listing(db,owner):return [get(db,owner,'session',r[0]) for r in db.execute("SELECT id FROM stacy_study WHERE owner=? AND kind='session' ORDER BY rowid",(owner,)).fetchall()]
def settings(db,owner):return get(db,owner,'settings','current',{'limits':c.DEFAULT,'idle_enabled':False,'idle_session':None})
def event(db,owner,state):activity.append(db,activity.make_event(owner,'study.state',state))
def registry():
    from .engineering_kernel import CAPABILITIES
    from .engineering_cli import schemas
    files={n:hashlib.sha256((Path(__file__).parent/n).read_bytes()).hexdigest() for n in ('study_service.py','study_editions.py','engineering_kernel.py','reference_service.py','memory_service.py')}
    files['study_contracts.py']=hashlib.sha256(Path(c.__file__).read_bytes()).hexdigest()
    return c.digest({'capabilities':CAPABILITIES,'schemas':schemas(),'readers':files})
def freeze(db,owner,bindings):
    captured=memory.capture_references(db,owner,bindings)
    if not captured:raise ValueError('STUDY_REQUIRES_CURRENT_ORIGINALS')
    ns=intake.namespace(db,captured[0]['namespace'],owner)
    index,meta=refs.meta(db,ns['id'])
    return captured,{'namespace':ns['id'],'admission_generation':ns['generation'],'reference_generation':index}
def current(db,owner,session):
    if session['registry_digest']!=registry():raise ValueError('STUDY_FROZEN_REGISTRY_CHANGED')
    ns=intake.namespace(db,session['frozen']['namespace'],owner);version,_=refs.meta(db,ns['id'])
    if ns['generation']!=session['frozen']['admission_generation'] or version!=session['frozen']['reference_generation']:raise ValueError('STUDY_FROZEN_SOURCE_GENERATION_CHANGED')
    passages,gaps=memory.recheck_references(db,owner,session['references'])
    if gaps:raise ValueError('STUDY_CURRENT_ORIGINALS_REQUIRED: '+str(gaps[0].get('reason','unavailable original')))
    if sum(len(p['text'].encode()) for p in passages)>24000:raise ValueError('STUDY_SOURCE_CONTEXT_BOUND')
    return passages

def measured_power():
    if not sys.platform.startswith('linux'):return 'NOT_INSTRUMENTED'
    batteries=[];online=[]
    for path in Path('/sys/class/power_supply').glob('*'):
        try:
            kind=(path/'type').read_text().strip()
            if kind=='Battery':batteries.append((path/'status').read_text().strip())
            elif (path/'online').is_file():online.append((path/'online').read_text().strip())
        except OSError:return 'NOT_INSTRUMENTED'
    if not batteries:return 'NO_BATTERY_REPORTED'
    if 'Discharging' in batteries:return 'BATTERY'
    if '1' in online:return 'AC'
    return 'BATTERY' if online else 'NOT_INSTRUMENTED'
def record_presence(kernel,owner,*,focused,busy,last_input,cpu):
    # Internal desktop bridge only: public commands cannot submit invented idle data.
    from .operation_stop import process_identity
    with kernel.db() as db:put(db,owner,'presence','desktop',{'pid':os.getpid(),'start':process_identity(os.getpid()),'at':time.time(),'focused':bool(focused),'busy':bool(busy),'last_input':last_input,'cpu':cpu})
def idle_reason(kernel,db,owner,config,ignore_job=None):
    from .operation_stop import process_identity
    p=get(db,owner,'presence','desktop',{})
    if not sys.platform.startswith('linux'):return 'IDLE_PLATFORM_NOT_QUALIFIED'
    if not p or time.time()-p['at']>12 or process_identity(p['pid'])!=p['start']:return 'NO_LIVE_DESKTOP_PRESENCE'
    if not p['focused']:return 'FOCUS_LOST_ACTIVE_USER_VETO'
    if p['busy'] or time.time()-p['last_input']<config['idle_seconds']:return 'ACTIVE_USER_OR_FOREGROUND_WORK_VETO'
    cpu=p['cpu']
    if cpu.get('status')!='MEASURED' or cpu.get('percent') is None or cpu.get('age_seconds') is None or cpu['age_seconds']+max(0,time.time()-p['at'])>7:return 'HOST_CPU_NOT_MEASURED'
    if cpu['percent']>config['max_host_cpu']:return 'HOST_CPU_BUDGET'
    ram=brain_runtime.host(profile=False)['available_ram_bytes']
    if ram is None or ram<config['min_available_mb']*1024**2:return 'HOST_RAM_BUDGET_OR_UNKNOWN'
    power=measured_power()
    if config['require_ac'] and power not in ('AC','NO_BATTERY_REPORTED'):return 'BATTERY_OR_POWER_UNKNOWN'
    if any(j['state'] not in TERMINAL and j['id']!=ignore_job for j in kernel.listing('jobs')):return 'OTHER_KERNEL_WORK_ACTIVE'
    return None

def authorize_job(kernel,tool,args,p):
    if tool!='study.read' or set(args)!={'id','attempt','idle'}:raise ValueError('STUDY_JOB_OPTIONS')
    learning.ident(args['id']);learning.ident(args['attempt'])
    with kernel.db() as db:
        s=get(db,p.identity,'session',args['id'])
        if not s.get('reservation') or (s['reservation']['attempt']!=args['attempt'] or s['reservation']['idle']!=args['idle']):raise ValueError('STUDY_EXPLICIT_STAGE_RESERVATION_REQUIRED')
        if s['paused'] or len(s['stages'])>=3:raise ValueError('STUDY_PAUSED_OR_FINISHED')
        current(db,p.identity,s)
        if args['idle'] and (not settings(db,p.identity)['idle_enabled'] or idle_reason(kernel,db,p.identity,s['limits'])):raise ValueError('STUDY_IDLE_VETO')

def view(kernel,owner,s):
    with kernel.db() as db:
        try:current(db,owner,s);status='CURRENT'
        except (ValueError,OSError) as exc:status=str(exc)
    active=None
    if s.get('active_job'):
        try:active=kernel.record('jobs',s['active_job'])['state']
        except ValueError:active='NOT_PRESENT_RECONCILE_EXPLICITLY'
    return {**s,'applicability':status,'active_job_state':active,'authority':'SOURCE_BOUND_READ_WORK_NOT_ENGINEERING_PROOF'}

def advance(kernel,owner,args,principal,idle=False):
    ident=args['id']
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');s=get(db,owner,'session',ident);current(db,owner,s)
        if s['paused']:raise ValueError('STUDY_PAUSED_OWNER_RESUME_REQUIRED')
        if len(s['stages'])>=3:return {'state':'FINISHED','session':s['id'],'replayed':False}
        if idle:
            cfg=settings(db,owner)
            if not cfg['idle_enabled'] or cfg['idle_session']!=ident:raise ValueError('STUDY_IDLE_NOT_ARMED')
            reason=idle_reason(kernel,db,owner,s['limits'])
            if reason:return {'state':'WAITING','reason':reason,'session':ident}
        if s.get('active_job'):
            try:j=kernel.record('jobs',s['active_job'])
            except ValueError:raise ValueError('STUDY_AMBIGUOUS_JOB_OWNER_RESUME_REQUIRED')
            if j['state'] not in TERMINAL:return {'state':'WAITING_FOR_KERNEL_JOB','job':j}
            if j['state']!='Completed' and not any(x['job']==j['id'] for x in s['stages']):raise ValueError('STUDY_INTERRUPTED_STAGE_OWNER_RESUME_REQUIRED')
        if s.get('reservation') and not s.get('active_job'):raise ValueError('STUDY_AMBIGUOUS_SUBMISSION_OWNER_RESUME_REQUIRED')
        if s['attempts']>=9:raise ValueError('STUDY_ATTEMPT_BUDGET')
        attempt=uuid.uuid4().hex;s['reservation']={'attempt':attempt,'stage':len(s['stages']),'idle':idle,'created':time.time()};s['attempts']+=1;s['active_job']=None;put(db,owner,'session',ident,s);event(db,owner,'STAGE_RESERVED')
    try:
        job=kernel.submit({'tool':'study.read','study':{'id':ident,'attempt':attempt,'idle':idle},'request_key':'study:'+ident+':'+attempt,'timeout':s['limits']['wall_seconds']},principal)
    except (ValueError,OSError):
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE');s=get(db,owner,'session',ident);s['paused']=True;s['pause_reason']='Submission uncertain or refused; owner must reconcile/resume.';put(db,owner,'session',ident,s)
        raise
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');s=get(db,owner,'session',ident);s['active_job']=job['id'];put(db,owner,'session',ident,s)
    return {'state':'SUBMITTED','job':job,'session':ident,'stage':len(s['stages'])}

def master_stop(kernel):
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        owners=[r[0] for r in db.execute('SELECT DISTINCT owner FROM stacy_study')]
        for owner in owners:
            cfg=settings(db,owner);cfg['idle_enabled']=False;put(db,owner,'settings','current',cfg)
            for s in listing(db,owner):
                if len(s['stages'])<3:s['paused']=True;s['pause_reason']='MASTER_STOP';put(db,owner,'session',s['id'],s)
            event(db,owner,'MASTER_STOP_DISARMED_IDLE')

def process_cpu():
    children=0
    if os.name!='nt':
        import resource
        usage=resource.getrusage(resource.RUSAGE_CHILDREN);children=usage.ru_utime+usage.ru_stime
    return time.process_time()+children

def run_stage(kernel,job):
    opts=job['request_spec']['study'];owner=job['owner'];began=time.monotonic();cpu_start=process_cpu()
    def guard(db,s):
        if kernel.record('jobs',job['id']).get('cancel') or s['paused']:raise ValueError('STUDY_CANCELLED_OR_PAUSED')
        cfg=s['limits']
        if time.monotonic()-began>cfg['wall_seconds'] or process_cpu()-cpu_start>cfg['cpu_seconds']:raise ValueError('STUDY_TIME_OR_CPU_BUDGET')
        if shutil.disk_usage(kernel.state).free<cfg['min_free_mb']*1024**2:raise ValueError('STUDY_DISK_FREE_BUDGET')
        if sys.platform.startswith('linux'):
            rss=int(next(v.split()[1] for v in Path('/proc/self/status').read_text().splitlines() if v.startswith('VmRSS:')))*1024
            if rss>cfg['max_rss_mb']*1024**2:raise ValueError('STUDY_RSS_BUDGET')
        if opts['idle']:
            if not settings(db,owner)['idle_enabled']:raise ValueError('STUDY_IDLE_DISARMED')
            reason=idle_reason(kernel,db,owner,cfg,job['id'])
            if reason:raise ValueError('STUDY_IDLE_'+reason)
        current(db,owner,s)
    with kernel.db() as db:
        s=get(db,owner,'session',opts['id']);guard(db,s)
        if not s.get('reservation') or s['reservation']['attempt']!=opts['attempt']:raise ValueError('STUDY_STAGE_RESERVATION_CHANGED')
        index=s['reservation']['stage']
        if len(s['stages'])!=index:raise ValueError('STUDY_STAGE_ALREADY_COMMITTED_OR_OUT_OF_ORDER')
        passages=current(db,owner,s);_,meta=refs.meta(db,s['frozen']['namespace']);stage=c.STAGES[index]
        if stage=='inventory':
            result={'source_ids':[v['id'] for v in passages],'literal_excerpts':[{'id':v['id'],'locator':v['locator'],'text':v['text'][:800]} for v in passages],
              'extraction_gaps':meta.get('gaps',[])[:12],'technical_entailment':'NOT_ASSESSED','repeated_questions':[r['note']['goal'] for r in memory.listing(db,owner,'checkpoint') if any(b['namespace']==s['frozen']['namespace'] for b in r['references'])][-8:]}
        elif stage=='questions':result=c.curriculum(s['goal'],s['unknowns'],passages,meta.get('gaps',[]))
        else:result={'title':'Reopen a source without losing its evidence identity','version':1,'operation':'references.resolve','prerequisites':['Current admitted original','Exact namespace, item and passage ID','Unchanged frozen source generation'],
              'scope':'Located source integrity only; no engineering conclusion or arbitrary code','counterexamples':['Revoked admission','Changed original','Changed extraction or locator','Cross-namespace query'],
              'oracle':'CURRENT_ORIGINAL_MATCHES_FROZEN_BINDING_V1','held_out_requirement':'A different private namespace','cost':'One registered read per trial or use'}
        guard(db,s)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');fresh=get(db,owner,'session',s['id']);guard(db,fresh)
        if len(fresh['stages'])!=index or fresh.get('reservation',{}).get('attempt')!=opts['attempt']:raise ValueError('STUDY_STAGE_HEAD_CHANGED')
        row={'stage':stage,'job':job['id'],'result':result,'result_sha256':c.digest(result),'created':time.time(),'wall_seconds':time.monotonic()-began,'cpu_seconds':process_cpu()-cpu_start,'model_tokens':0,'cloud_calls':0}
        fresh['stages'].append(row);fresh['reservation']=None
        if stage=='procedure':fresh['procedure']={'descriptor':result,'digest':c.digest(result),'review':'CANDIDATE_UNREVIEWED','trials':[],'uses':[]}
        if len(records.canonical(fresh))>fresh['limits']['max_payload_bytes']:raise ValueError('STUDY_PAYLOAD_DISK_BUDGET')
        put(db,owner,'session',fresh['id'],fresh)
        if len(fresh['stages'])==3:
            cfg=settings(db,owner);cfg['idle_enabled']=False;put(db,owner,'settings','current',cfg)
        event(db,owner,'STAGE_COMMITTED_'+stage.upper())
    # Independent connection readback, distinct from the transaction's own writes.
    with kernel.db() as db:
        saved=get(db,owner,'session',s['id'])
        if saved['stages'][index]['result_sha256']!=c.digest(result):raise ValueError('STUDY_DURABLE_READBACK_FAILED')
    return {'status':'STAGE_COMPLETED','session':s['id'],'stage':stage,'result_sha256':c.digest(result),'model_tokens':0,'cloud_calls':0,'source_count':len(passages)}

def dispatch(kernel,op,args,p):
    owner=p.identity
    if op.startswith('study.edition.'):
        from .study_editions import dispatch as edition_dispatch
        return edition_dispatch(kernel,op,args,p)
    if op=='study.advance':return advance(kernel,owner,args,p)
    if op=='study.idle.poll':
        with kernel.db() as db:cfg=settings(db,owner)
        if not cfg['idle_enabled']:return {'state':'DISABLED'}
        return advance(kernel,owner,{'id':cfg['idle_session']},p,True)
    if op in ('study.procedure.test','study.procedure.run'):
        with kernel.db() as db:
            s=get(db,owner,'session',args['id']);current(db,owner,s)
            if not s.get('procedure'):raise ValueError('STUDY_PROCEDURE_NOT_READY')
            binding=memory.capture_references(db,owner,[args['reference']])[0]
            if op=='study.procedure.test' and binding['namespace']==s['frozen']['namespace']:raise ValueError('STUDY_HELD_OUT_SEPARATE_LIBRARY_REQUIRED')
            if op=='study.procedure.run':
                lesson=memory.get(db,owner,'lesson',s['id'],{})
                if s['procedure']['review']!='OWNER_REVIEWED' or lesson.get('review')!='OWNER_REVIEWED_PROCEDURE' or memory.recheck_references(db,owner,lesson.get('references',[]))[1]:raise ValueError('STUDY_CURRENT_OWNER_ACTIVATED_PROCEDURE_REQUIRED')
        result=kernel.dispatch('references.resolve',{k:binding[k] for k in ('namespace','id','item')},p)
        passed=result['ok'] and all(result['result'].get(k)==binding[k] for k in ('id','source_sha256','text_sha256','locator')) and result['result'].get('state')=='CURRENT'
        trial={'id':uuid.uuid4().hex,'reference':binding,'oracle':'CURRENT_ORIGINAL_MATCHES_FROZEN_BINDING_V1','passed':bool(passed),'result_digest':c.digest(result),'created':time.time(),'quality_scope':'SOURCE_IDENTITY_NOT_MODEL_LEARNING_OR_DOMAIN_ENTAILMENT'}
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE');s=get(db,owner,'session',args['id']);current(db,owner,s)
            kind='trials' if op=='study.procedure.test' else 'uses'
            if len(s['procedure'][kind])>=20:raise ValueError('STUDY_TRIAL_OR_USE_BUDGET')
            s['procedure'][kind].append(trial);put(db,owner,'session',s['id'],s);event(db,owner,'HELD_OUT_SOURCE_TRIAL_RECORDED')
        return trial
    if op=='study.pause':
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE');s=get(db,owner,'session',args['id']);s['paused']=True;s['pause_reason']=args['reason'];put(db,owner,'session',s['id'],s)
            cfg=settings(db,owner);cfg['idle_enabled']=False;put(db,owner,'settings','current',cfg);event(db,owner,'OWNER_PAUSED_STUDY')
        if s.get('active_job'):
            try:
                job=kernel.record('jobs',s['active_job'])
                if job['state'] not in TERMINAL:kernel.dispatch('jobs.cancel',{'id':job['id']},p)
            except ValueError:pass
        return {'state':'PAUSED','stages_retained':len(s['stages'])}
    if op=='study.radar':
        from .engineering_kernel import CAPABILITIES
        from .engineering_cli import schemas
        return {'registry_digest':registry(),'proposals':c.radar(CAPABILITIES,schemas(),registry()),'automatic_execution':False}
    with kernel.db() as db:
        if SCOPES[op]!='read':db.execute('BEGIN IMMEDIATE')
        if op=='study.status':
            cfg=settings(db,owner);return {**cfg,'scope':'FINITE_READ_ONLY_STUDY_NO_MODEL_OR_CLOUD','sessions':len(listing(db,owner)),'idle_gate':idle_reason(kernel,db,owner,cfg['limits']) if cfg['idle_enabled'] else 'DISABLED','host_qualification':'LINUX_LEDGER_FOCUSED_IDLE_PILOT_ONLY'}
        if op=='study.configure':
            cfg=settings(db,owner);cfg['limits']=c.limits(args['limits']);cfg['idle_enabled']=False;put(db,owner,'settings','current',cfg);event(db,owner,'OWNER_LIMITS_CONFIGURED');return cfg
        if op=='study.create':
            learning.text(args['goal'],500,False);unknowns=args['unknowns']
            if not isinstance(unknowns,list) or len(unknowns)>12 or any(not isinstance(v,str) or len(v)>500 for v in unknowns):raise ValueError('STUDY_UNKNOWNS_BOUND')
            bindings,frozen=freeze(db,owner,args['references']);value={'schema':'arc.stacy-study/1','id':uuid.uuid4().hex,'created':time.time(),'goal':args['goal'],'unknowns':unknowns,'references':bindings,'frozen':frozen,'registry_digest':registry(),
              'limits':settings(db,owner)['limits'],'stages':[],'procedure':None,'paused':False,'active_job':None,'reservation':None,'attempts':0,'model_tokens':0,'cloud_calls':0}
            current(db,owner,value);put(db,owner,'session',value['id'],value);event(db,owner,'FROZEN_SUPERVISED_SESSION_CREATED');return value
        if op=='study.list':return {'sessions':listing(db,owner)}
        if op=='study.get':s=get(db,owner,'session',args['id'])
        elif op=='study.resume':
            s=get(db,owner,'session',args['id']);current(db,owner,s)
            if any(j['owner']==owner and j.get('tool')=='study.read' and j.get('request_spec',{}).get('study',{}).get('id')==s['id'] and j['state'] not in TERMINAL for j in kernel.listing('jobs')):raise ValueError('STUDY_WAIT_FOR_TERMINAL_JOB_BEFORE_RESUME')
            if s.get('active_job'):
                try:
                    j=kernel.record('jobs',s['active_job'])
                    if j['state'] not in TERMINAL:raise ValueError('STUDY_WAIT_FOR_TERMINAL_JOB_BEFORE_RESUME')
                except KeyError:raise ValueError('STUDY_JOB_RECORD_CORRUPT')
            s.update(paused=False,active_job=None,reservation=None,pause_reason='Owner reconciled persisted read stages; no side effects replayed.');put(db,owner,'session',s['id'],s);event(db,owner,'OWNER_RESUMED_FROM_PERSISTED_STAGE')
        elif op=='study.rebind':
            s=get(db,owner,'session',args['id'])
            if not s['paused'] or s.get('active_job'):raise ValueError('STUDY_REBIND_PAUSED_NO_LIVE_JOB_REQUIRED')
            bindings,frozen=freeze(db,owner,[{'namespace':args['namespace'],'id':b['id']} for b in s['references']])
            if len(bindings)!=len(s['references']) or any(any(a[k]!=b[k] for k in ('id','source_sha256','text_sha256','locator')) for a,b in zip(s['references'],bindings)):raise ValueError('STUDY_REBIND_IDENTICAL_ORIGINALS_REQUIRED')
            old=s['frozen'];s.update(references=bindings,frozen=frozen);current(db,owner,s);s['relink_history']=s.get('relink_history',[])+[{'previous_frozen':old,'new_frozen':frozen,'reason':args['reason'],'at':time.time()}]
            if len(s['relink_history'])>20:raise ValueError('STUDY_RELINK_HISTORY_BOUND')
            put(db,owner,'session',s['id'],s);event(db,owner,'OWNER_IDENTICAL_ORIGINAL_RELINK')
        elif op=='study.idle.enable':
            s=get(db,owner,'session',args['id']);current(db,owner,s)
            if args['enabled'] and (s['paused'] or len(s['stages'])>=3):raise ValueError('STUDY_IDLE_REQUIRES_UNFINISHED_UNPAUSED_SESSION')
            cfg=settings(db,owner);cfg.update(idle_enabled=args['enabled'],idle_session=s['id'],idle_armed_at=time.time());put(db,owner,'settings','current',cfg);event(db,owner,'OWNER_IDLE_ARMED' if args['enabled'] else 'OWNER_IDLE_DISARMED');return cfg
        elif op=='study.procedure.review':
            s=get(db,owner,'session',args['id']);proc=s['procedure']
            if not proc:raise ValueError('STUDY_PROCEDURE_NOT_READY')
            if args['approved']:
                current(db,owner,s)
                passing=[t for t in proc['trials'] if t['passed'] and not memory.recheck_references(db,owner,[t['reference']])[1]]
                if not passing:raise ValueError('STUDY_CURRENT_PASSING_HELD_OUT_TRIAL_REQUIRED')
            proc.update(review='OWNER_REVIEWED' if args['approved'] else 'REJECTED',reason=args['reason'],reviewed=time.time())
            lesson={'id':s['id'],'title':proc['descriptor']['title'],'body':json.dumps(proc['descriptor'],ensure_ascii=False)[:1500],'references':s['references']+([passing[-1]['reference']] if args['approved'] else []),'review':'OWNER_REVIEWED_PROCEDURE' if args['approved'] else 'REJECTED','reason':args['reason'],'created':s['created'],'reviewed':time.time(),'study_session':s['id']}
            memory.store(db,owner,'lesson',s['id'],lesson);put(db,owner,'session',s['id'],s);event(db,owner,'OWNER_PROCEDURE_REVIEWED')
        else:raise ValueError('STUDY_OPERATION')
    return view(kernel,owner,s)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--job',required=True);a=parser.parse_args();from .engineering_kernel import Kernel
    kernel=Kernel(a.root);job=kernel.record('jobs',a.job)
    with kernel.db() as db:cfg=get(db,job['owner'],'session',job['request_spec']['study']['id'])['limits']
    if os.name!='nt':
        import resource
        resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(cfg['max_rss_mb']*2*1024**2,cfg['max_rss_mb']*2*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(cfg['cpu_seconds']+1,cfg['cpu_seconds']+2))
        try:os.nice(10)
        except OSError:pass
    try:result=run_stage(kernel,job);code=0
    except Exception as exc:result={'status':'FAILED_OR_INTERRUPTED','reason':activity.redact(exc),'model_tokens':0,'cloud_calls':0};code=1
    record_io.write_json(kernel.root/'build/study/runs'/job['id']/'result.json',{'schema':'arc.study-job-result/1','job':job['id'],**result})
    print(json.dumps(result));return code
if __name__=='__main__':raise SystemExit(main())
