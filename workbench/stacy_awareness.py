"""Deterministic awareness over the existing journal; no model or scheduler."""
import json, re, hashlib, csv, io
from . import activity,project_context

TEXT={'type':'string','maxLength':180}
CONSUMER={'type':'string','pattern':'^[a-zA-Z0-9_.-]{1,48}$','maxLength':48}
FIELDS={
 'ledger.project.status':({},[]),
 'ledger.journal.status':({},[]),
 'ledger.journal.read':({'after':TEXT,'limit':{'type':'integer','minimum':1,'maximum':200}},[]),
 'ledger.journal.recover':({},[]),
 'ledger.awareness':({'consumer':CONSUMER},[]),
 'ledger.awareness.catch_up':({'consumer':CONSUMER,'limit':{'type':'integer','minimum':1,'maximum':200}},[]),
 'ledger.capabilities.search':({'query':TEXT,'limit':{'type':'integer','minimum':1,'maximum':50}},[]),
 'ledger.capabilities.describe':({'operation':TEXT},['operation']),
 'ledger.workflow.describe':({'tool':TEXT},['tool']),
 'ledger.object.reference':({'object':{'type':'string','enum':['J14']}},['object']),
}
SCOPES={op:('approve' if op=='ledger.journal.recover' else 'execute' if op.endswith('catch_up') else 'read') for op in FIELDS}

def name(consumer):
    if not isinstance(consumer,str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,48}',consumer):raise ValueError('Invalid consumer name')
    return consumer

def checkpoint(kernel,consumer='stacy'):
    name(consumer)
    with kernel.db() as db:
        row=db.execute('SELECT cursor,event_id,projection FROM activity_consumers WHERE name=?',(consumer,)).fetchone()
    return {'cursor':row[0],'event_id':row[1],'projection':json.loads(row[2])} if row else {'cursor':0,'event_id':None,'projection':{'processed':0,'jobs':{},'last_event':None}}

def live_jobs(kernel):
    # Unlike the human history list, this must not silently stop at 100 jobs.
    with kernel.db() as db:rows=db.execute('SELECT payload FROM jobs ORDER BY rowid').fetchall()
    return [json.loads(row[0]) for row in rows]

def inspect(kernel,consumer='stacy'):
    point=checkpoint(kernel,consumer);health=activity.status(kernel.root)
    state='INCOMPLETE' if health['state']=='INCOMPLETE' or point['cursor']>health['head'] else 'CURRENT' if point['cursor']==health['head'] else 'CATCHING_UP'
    if point['cursor']:
        with kernel.db() as db:row=db.execute('SELECT event_id FROM activity_journal WHERE seq=?',(point['cursor'],)).fetchone()
        if not row or row[0]!=point['event_id']:state='INCOMPLETE'
    from .operation_stop import process_identity,UNKNOWN
    jobs=[]
    for job in live_jobs(kernel):
        if job['state'] in ('Completed','Failed','Cancelled'):continue
        actual=process_identity(job.get('pid')) if job.get('pid') else None
        token=job.get('worker_start')
        health_state='WAITING_OR_QUEUED'
        if job['state']=='Running':
            health_state='UNKNOWN' if actual==UNKNOWN or not token else 'OWNED_WORKER_LIVE' if actual==token else 'WORKER_MISSING_OR_REPLACED'
        jobs.append({'id':job['id'],'tool':job['tool'],'recorded_state':job['state'],'process_health':health_state})
    return {'schema':'arc.stacy-awareness/1','consumer':consumer,'state':state,'cursor':point['cursor'],
            'head':health['head'],'backlog':max(0,health['head']-point['cursor']),'projection':point['projection'],
            'journal':health,'jobs':jobs,'project':project_context.status(kernel.root),
            'model_calls':0,'notice':'CURRENT means journal events processed through the watermark. Live job health is reconciled separately; it does not prove physical outcomes.'}

def catch_up(kernel,consumer='stacy',limit=200):
    name(consumer);limit=max(1,min(int(limit),200))
    health=activity.status(kernel.root)
    if health['state']=='INCOMPLETE':return inspect(kernel,consumer)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT cursor,event_id,projection FROM activity_consumers WHERE name=?',(consumer,)).fetchone()
        cursor,event_id,projection=(row[0],row[1],json.loads(row[2])) if row else (0,None,{'processed':0,'jobs':{},'last_event':None})
        rows=db.execute('SELECT seq,event_id,payload FROM activity_journal WHERE seq>? ORDER BY seq LIMIT ?',(cursor,limit)).fetchall()
        for seq,ident,raw in rows:
            if seq!=cursor+1:raise ValueError('Journal gap: consumer checkpoint was not advanced')
            event=json.loads(raw)
            if event.get('job_id'):projection['jobs'][event['job_id']]={'state':event['state'],'seq':seq,'evidence_id':event.get('evidence_id')}
            projection['processed']+=1;projection['last_event']={k:event.get(k) for k in ('operation','state','detail')}
            cursor,event_id=seq,ident
        # Materialized projection and watermark either both commit or neither.
        db.execute('INSERT OR REPLACE INTO activity_consumers VALUES(?,?,?,?)',(consumer,cursor,event_id,json.dumps(projection)))
    return inspect(kernel,consumer)

def discovery(kernel,principal,query='',limit=20,operation=None):
    from .capability_catalog import by_operation
    from .engineering_kernel import CAPABILITIES
    assessed=by_operation(kernel,principal,operation or query)
    rows=[]
    detached=project_context.detached(kernel.root)
    for op,scope in CAPABILITIES.items():
        if scope not in principal.scopes or (principal.mode=='Tutor' and scope!='read'):continue
        if operation is not None and op!=operation:continue
        if operation is None and query.casefold() not in (op+' '+scope).casefold():continue
        current=assessed[op]
        blocked=detached and project_context.requires_project(op,{})
        row={'operation':op,'scope':scope,'status':'PROJECT_NOT_ATTACHED' if blocked else 'REGISTERED',
             'assessment':current['assessment'],'summary':current['summary'],
             'required':current['arguments']['required'],'handler':current['handler'],
             'qualification':'NOT_INFERRED'}
        if operation:row['arguments']=current['arguments']
        rows.append(row)
    if operation and not rows:raise ValueError('Operation unavailable to this principal')
    return {'schema':'arc.compact-capabilities/1','operations':rows[:limit], 'matches':len(rows),
            'has_more':len(rows)>limit,'notice':'Only scope-eligible commands are returned. Registration is not runtime qualification.'}

def object_reference(kernel):
    # Pilot resolves one exact source record; it never fabricates absent bytes.
    base=kernel.root/'hardware/compact-arc1/R10_WORK'
    # J14 is also a BGA ball label. Only the native reference column of this
    # current crossprobe table identifies the connector; substring hits do not.
    candidates=[base/'closure_p8/P8_PIN_CROSSPROBE.csv'] if base.is_dir() else []
    records=[]
    for source in candidates:
        if not source.is_file() or not source.resolve().is_relative_to(kernel.root) or any(p.is_symlink() for p in (source,*source.parents)) or source.stat().st_size>1_000_000:continue
        raw=source.read_bytes();reader=csv.reader(io.StringIO(raw.decode('utf-8-sig')))
        header=next(reader,None)
        if not header or header[0]!='component':raise ValueError('J14 reference column is not the expected native component schema')
        for row in reader:
            if row and row[0]=='J14':
                records.append({'path':source.relative_to(kernel.root).as_posix(),'line':reader.line_num,'sha256':hashlib.sha256(raw).hexdigest(),
                                'fields':dict(zip(header,row)),'reference':'J14'})
    return {'object':'J14','status':'SOURCE_BOUND_UNREVIEWED' if records else 'PROJECT_NOT_ATTACHED' if project_context.detached(kernel.root) else 'SOURCE_NOT_FOUND',
            'records':records[:10],'basis':'Exact CSV line and whole-file SHA256; independent engineering acceptance is separate.'}

def dispatch(kernel,op,args,principal):
    if op=='ledger.project.status':return project_context.status(kernel.root)
    if op=='ledger.journal.status':return activity.status(kernel.root)
    if op=='ledger.journal.read':return activity.stream(kernel.root,**args)
    if op=='ledger.journal.recover':
        from .ledger_control import reconcile_receipts
        from .file_delivery import reconcile
        settings=reconcile_receipts(kernel)
        files=reconcile(kernel)
        return {**activity.recover(kernel.root),'settings_reconciled':settings,'files_reconciled':files}
    if op=='ledger.awareness':return inspect(kernel,**args)
    if op=='ledger.awareness.catch_up':return catch_up(kernel,**args)
    if op=='ledger.capabilities.search':return discovery(kernel,principal,**args)
    if op=='ledger.capabilities.describe':return discovery(kernel,principal,operation=args['operation'])
    if op=='ledger.object.reference':return object_reference(kernel)
    if op=='ledger.workflow.describe':
        from .engineering_kernel import TOOLS
        tool=args['tool']
        if tool not in TOOLS:raise ValueError('Unknown registered tool')
        return {'tool':tool,'inspect':'ledger.capabilities.describe','launch':'jobs.submit','status':'jobs.get',
                'result':'evidence.read','cancel':'jobs.cancel','pause':None if tool.startswith('brain.') else 'jobs.pause','resume':None if tool.startswith('brain.') else 'jobs.resume',
                'control_basis':'Existing Kernel state and platform validation; external-driver pause/resume is unavailable.',
                'retry':'New jobs.submit request key after reviewing current sources; no automatic mutation retry.',
                'priority':'Existing operations.priority setting; not a per-job scheduler',
                'project':project_context.status(kernel.root),'qualified':False}
    raise ValueError('Unknown awareness operation')
