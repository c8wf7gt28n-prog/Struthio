"""Private engineering-map records using existing Kernel jobs and source authority."""
from __future__ import annotations
import hashlib, time
from sdk.cli.arc1cli import engineering_map as core,knowledge_sources as sources,record_store as records
from . import activity,record_io,intake_service as intake

ID=intake.ID;SHA=intake.SHA;REF={'type':'string','minLength':1,'maxLength':51};NET={'type':'string','minLength':1,'maxLength':500}
FIELDS={
 'knowledge.map.build':({'baseline':ID,'rom':ID,'request_key':intake.TEXT},['baseline','rom']),
 'knowledge.map.list':({},[]),
 'knowledge.map.get':({'id':ID,'expected_revision':SHA},['id']),
 'knowledge.map.part':({'id':ID,'component':REF,'expected_revision':SHA},['id','component']),
 'knowledge.map.net':({'id':ID,'net':NET,'expected_revision':SHA},['id','net']),
 'knowledge.map.trace':({'id':ID,'start':REF,'end':REF,'net_prefix':{'type':'string','minLength':1,'maxLength':50},'expected_revision':SHA},['id','start','end']),
 'knowledge.map.configure':({'id':ID,'configuration':{'type':'object'},'expected_revision':SHA,'reason':intake.REASON},['id','configuration','expected_revision','reason']),
 'knowledge.map.evidence':({'id':ID,'component':REF,'expected_revision':SHA},['id'])}
SCOPES={op:'approve' if op in ('knowledge.map.build','knowledge.map.configure') else 'read' for op in FIELDS}
def _connections():
    from . import knowledge_service
    return knowledge_service

def ensure(db):db.execute('CREATE TABLE IF NOT EXISTS engineering_maps(owner TEXT,id TEXT,payload TEXT,sha256 TEXT,PRIMARY KEY(owner,id))')
def save(db,row):
    raw=records.canonical(row)
    if len(raw)>65536:raise ValueError('MAP_RECORD_BUDGET')
    db.execute('INSERT OR REPLACE INTO engineering_maps VALUES(?,?,?,?)',(row['owner'],row['id'],raw.decode(),hashlib.sha256(raw).hexdigest()))
    activity.append(db,activity.make_event(row['owner'],'knowledge.map',row['state'],source_generation=str(row['generation'])))
def load(db,owner,ident):
    r=db.execute('SELECT payload,sha256 FROM engineering_maps WHERE owner=? AND id=?',(owner,ident)).fetchone()
    if not r:raise ValueError('PRIVATE_MAP_NOT_FOUND')
    if hashlib.sha256(r[0].encode()).hexdigest()!=r[1]:raise ValueError('MAP_RECORD_CHANGED')
    return records.strict(r[0])
def revision(row):return sources.digest({k:row[k] for k in ('graph_sha256','generation','configuration','baseline','rom')})
def summary(row):return {k:v for k,v in row.items() if k not in ('owner','artifact')}|{'revision':revision(row)}
def connected(kernel,owner,opts):
    with kernel.db() as db:
        b=_connections().fresh(_connections().load(db,owner,opts['baseline']));r=_connections().fresh(_connections().load(db,owner,opts['rom']))
    if b['kind']!='BASELINE' or b['state']!='OWNER_SELECTED_REFERENCE_BASELINE':raise ValueError('MAP_OWNER_SELECTED_BASELINE_REQUIRED')
    if r['kind']!='ROM':raise ValueError('MAP_ROM_REQUIRED')
    return b,r
def authorize(kernel,opts,p):
    if not {'read','approve'}<=p.scopes:raise ValueError('MAP_OWNER_READ_AND_APPROVE_REQUIRED')
    if set(opts)!={'baseline','rom'}:raise ValueError('MAP_BUILD_OPTIONS')
    connected(kernel,p.identity,opts)
def artifact(kernel,job,path,expected=None):
    j=kernel.record('jobs',job);ev=kernel.record('evidence',j.get('evidence',''))
    if j['state']!='Completed' or ev.get('job')!=j['id'] or ev.get('id')!=j['evidence'] or ev.get('state')!='Completed' or ev.get('revision')!=j.get('revision'):raise ValueError('MAP_COMPLETED_EVIDENCE_REQUIRED')
    a=next((a for a in ev.get('artifacts',[]) if a['path']==path),None)
    if not a or a['bytes']>core.MAX_GRAPH:raise ValueError('MAP_ARTIFACT_NOT_REGISTERED_OR_LIMIT')
    p=records.inside(kernel.root,path);sources.regular(p)
    if p.stat().st_size!=a['bytes'] or records.sha(p)!=a['sha256'] or expected and a['sha256']!=expected:raise ValueError('MAP_ARTIFACT_CHANGED')
    return j,ev,a,p
def fresh(kernel,row):
    if row['reader']!=core.fingerprint():raise ValueError('MAP_READER_CHANGED')
    b,r=connected(kernel,row['owner'],row)
    if b['generation']!=row['baseline_generation'] or r['generation']!=row['rom_generation']:raise ValueError('MAP_SOURCE_GENERATION_CHANGED')
    j,ev,a,p=artifact(kernel,row['job'],row['artifact'],row['graph_sha256'])
    if j['owner']!=row['owner'] or j['tool']!='knowledge.map' or j['request_spec']['knowledge']!={'baseline':row['baseline'],'rom':row['rom']}:raise ValueError('MAP_JOB_BINDING_CHANGED')
    return b,r,records.load(p)
def build(kernel,job):
    opts=job['request_spec']['knowledge'];owner=job['owner'];b,r=connected(kernel,owner,opts);check=lambda:_connections().check(kernel,job)
    graph=core.build(b['path'],b['report'],check);sources.header(r['path'],r['report']['manifest_sha256']);check()
    name='build/knowledge/runs/'+job['id']+'/graph.json';raw=records.canonical(graph);records.atomic(kernel.root/name,raw)
    ident=sources.digest({'owner':owner,'baseline':b['id'],'rom':r['id'],'reader':core.fingerprint(),'invocation':job['id']})[:32]
    row={'id':ident,'owner':owner,'baseline':b['id'],'rom':r['id'],'baseline_generation':b['generation'],'rom_generation':r['generation'],
      'job':job['id'],'artifact':name,'graph_sha256':hashlib.sha256(raw).hexdigest(),'source_digest':graph['source_digest'],'reader':core.fingerprint(),
      'state':'SOURCE_MAP_CANDIDATE','generation':1,'configuration':{'conditions':[],'documents':[],'evidence':[]},'created':time.time(),
      'components':len(graph['components']),'nets':len(graph['nets']),'pin_count':graph['pin_count'],'pad_net_disagreements':len(graph['pad_net_disagreements']),
      'current_project_promoted':False,'physical_qualification':False}
    with kernel.db() as db:
        old=db.execute('SELECT id FROM engineering_maps WHERE owner=? AND id=?',(owner,ident)).fetchone()
        if old:raise ValueError('MAP_INVOCATION_ALREADY_PUBLISHED')
        if db.execute('SELECT count(*) FROM engineering_maps WHERE owner=?',(owner,)).fetchone()[0]>=16:raise ValueError('MAP_COUNT_LIMIT')
        b2,r2=connected(kernel,owner,opts)
        if (b2['generation'],r2['generation'])!=(b['generation'],r['generation']):raise ValueError('MAP_SOURCES_CHANGED_DURING_BUILD')
        check();save(db,row)
    return {'state':'SOURCE_MAP_COMPILED','map':summary(row),'oracle':{'schema':'arc.source-map-oracle/1','source_digest':graph['source_digest'],
       'claim':'Parse preserved native identities and compare declared net endpoints with native PCB pads','outcome':'CORRESPONDENCE_REPORTED','pad_net_disagreements':len(graph['pad_net_disagreements']),'engineering_compliance_approved':False},'model_calls':0}
def evidence(kernel,row,binding):
    j=kernel.record('jobs',binding['job'])
    if j['owner']!=row['owner']:raise ValueError('PRIVATE_MAP_EVIDENCE_NOT_OWNED')
    from .stac import kernel_witness
    def read(op,args):return kernel.dispatch(op,args,connections_operator(row['owner']))['result']
    candidate=kernel_witness.inspect_job(j['id'],read);w=kernel_witness.verify_test({'type':'KernelJobInspection','payload':candidate},read)
    path=binding['oracle'];j,ev,a,p=artifact(kernel,j['id'],path,binding['sha256'])
    # Corroborate all registered bytes, not just a model-supplied hash or success string.
    for item in ev.get('artifacts',[]):artifact(kernel,j['id'],item['path'],item['sha256'])
    oracle=records.load(p)
    if record_io.digest(kernel.record('jobs',j['id']))!=record_io.digest(j) or record_io.digest(kernel.record('evidence',ev['id']))!=record_io.digest(ev):raise ValueError('MAP_EVIDENCE_RECORD_DRIFT')
    return {'job':j['id'],'evidence_id':ev['id'],'source_revision':j.get('revision'),'candidate':j.get('candidate'),'record_witness':w,
       'oracle':{'path':path,'sha256':a['sha256'],'state':'REGISTERED_ARTIFACT_BYTES_VERIFIED','declared_oracle':oracle.get('oracle'),
         'review':'ENGINEERING_ORACLE_APPROVAL_NOT_GRANTED'},'artifacts':[{'path':x['path'],'sha256':x['sha256'],'bytes':x['bytes']} for x in ev['artifacts']],
       'requirement_binding':'UNVERIFIED','physical_qualification':False}
def connections_operator(owner):
    from .engineering_kernel import Principal
    return Principal(owner,frozenset({'read'}),mode='Tutor')
def configuration(value,graph,documents):
    if not isinstance(value,dict) or set(value)!={'conditions','documents','evidence'}:raise ValueError('MAP_CONFIGURATION_FIELDS')
    from sdk.cli.arc1cli import learning_contracts as c
    c.strings(value['conditions'],8,200)
    if not isinstance(value['documents'],list) or len(value['documents'])>24 or not isinstance(value['evidence'],list) or len(value['evidence'])>24:raise ValueError('MAP_CONFIGURATION_LIMIT')
    seen=set()
    for x in value['documents']:
        if not isinstance(x,dict) or set(x)!={'component','record_id','mpn','package','grade','conditions'}:raise ValueError('MAP_DOCUMENT_BINDING_FIELDS')
        part=graph['components'].get(x['component']);doc=documents.get(x['record_id'])
        if not part or not doc or not x['record_id'].lower().endswith('.pdf') or doc['kind']!='vendor-original':raise ValueError('MAP_DOCUMENT_SOURCE_REQUIRED')
        if x['mpn']!=part['mpn'] or x['package']!=part['package']:raise ValueError('MAP_DOCUMENT_FITMENT_MISMATCH')
        key=(x['component'],x['record_id'])
        if key in seen:raise ValueError('MAP_DUPLICATE_DOCUMENT_BINDING')
        seen.add(key);c.text(x['grade'],100,False);c.strings(x['conditions'],8,200)
    for x in value['evidence']:
        if not isinstance(x,dict) or set(x)!={'component','job','oracle','sha256'} or x['component'] not in graph['components']:raise ValueError('MAP_EVIDENCE_BINDING_FIELDS')
        c.ident(x['job']);c.ident(x['sha256'],64);records.safe_name(x['oracle'])
    return value
def _dispatch(kernel,op,args,p):
    if op=='knowledge.map.build':return kernel.submit({'tool':'knowledge.map','knowledge':{k:args[k] for k in ('baseline','rom')},'request_key':args.get('request_key',__import__('uuid').uuid4().hex),'timeout':600},p)
    if op=='knowledge.map.list':
        with kernel.db() as db:rows=[load(db,p.identity,x[0]) for x in db.execute('SELECT id FROM engineering_maps WHERE owner=? ORDER BY rowid',(p.identity,))]
        out=[]
        for row in rows:
            try:fresh(kernel,row);state='SOURCE_IDENTITIES_AVAILABLE'
            except (ValueError,OSError,KeyError):state='STALE_OR_UNAVAILABLE'
            out.append({**summary(row),'availability':state})
        return {'maps':out,'engineering_acceptance':False}
    with kernel.db() as db:row=load(db,p.identity,args['id'])
    try:b,r,graph=fresh(kernel,row)
    except (ValueError,OSError,KeyError) as exc:return {'state':'STALE_OR_UNAVAILABLE','id':row['id'],'revision':revision(row),'reason':activity.redact(exc),'result':None,'physical_qualification':False}
    expected=args.get('expected_revision');rev=revision(row)
    if expected and expected!=rev:return {'state':'STALE','id':row['id'],'revision':rev,'expected_revision':expected,'result':None,'reason':'SOURCE_CONDITIONS_DOCUMENT_BINDINGS_OR_ORACLES_CHANGED'}
    _,documents=sources.header(r['path'],r['report']['manifest_sha256']);documents=documents['records']
    identity={'schema':core.VERSION,'state':'REFERENCE_MAP_AVAILABLE','id':row['id'],'revision':rev,'source_digest':row['source_digest'],
      'conditions':row['configuration']['conditions'],'current_project_promoted':False,'physical_qualification':False,'routed_copper_verified':False}
    if op=='knowledge.map.configure':
        cfg=configuration(args['configuration'],graph,documents)
        for item in cfg['documents']:sources.original(r['path'],r['report'],item['record_id'])
        for item in cfg['evidence']:evidence(kernel,row,item)
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE');live=load(db,p.identity,row['id'])
            if revision(live)!=rev:raise ValueError('MAP_CONFIGURATION_CHANGED_DURING_REVIEW')
            fresh(kernel,live);live.update(configuration=cfg,generation=live['generation']+1,reason=args['reason']);save(db,live)
        return {**summary(live),'scope':'OWNER_DECLARATIONS_NOT_ACCEPTED_ENGINEERING_FACTS','prior_revision_stale':rev}
    if op=='knowledge.map.get':return {**identity,'summary':summary(row),'native_export':graph['native_export'],'components':[{'reference':c['reference'],'mpn':c['mpn'],'value':c['value'],'id':c['id'],'gaps':c['gaps']} for c in graph['components'].values()],
       'source_manifest':graph['source_manifest'],'gaps':['REFERENCE_BASELINE_NOT_ACCEPTED_CURRENT_PROJECT','FITMENT_GRADE_CONDITIONS_AND_TEST_ORACLE_REVIEW_REQUIRED']}
    if op=='knowledge.map.net':
        net=graph['nets'].get(args['net'])
        if net is None:raise ValueError('MAP_NET_NOT_FOUND')
        endpoints=[pin for node in net['pins'] for pin in graph['components'][node['reference']]['pins'] if pin['pin']==node['pin'] and pin['net']==net['name']]
        return {**identity,'net':{k:v for k,v in net.items() if k!='pins'},'endpoints':endpoints,'relation':'NATIVE_NET_MEMBERSHIP_NOT_SIGNAL_DIRECTION'}
    if op=='knowledge.map.trace':return {**identity,'trace':core.trace(graph,args['start'],args['end'],args.get('net_prefix'))}
    if op=='knowledge.map.evidence':
        bindings=[x for x in row['configuration']['evidence'] if not args.get('component') or x['component']==args['component']]
        own={'job':row['job'],'oracle':'build/knowledge/runs/'+row['job']+'/result.json'}
        j=kernel.record('jobs',row['job']);ev=kernel.record('evidence',j['evidence']);own['sha256']=next(x['sha256'] for x in ev['artifacts'] if x['path']==own['oracle']);bindings=[own,*bindings];results=[]
        for item in bindings:
            try:results.append(evidence(kernel,row,item))
            except (ValueError,OSError,KeyError) as exc:results.append({'job':item['job'],'state':'STALE_OR_UNAVAILABLE','reason':activity.redact(exc)})
        return {**identity,'evidence':results,'scope':'SOURCE_MAP_AND_EXPLICIT_REFERENCES_NOT_CONTROLLER_COMPLIANCE'}
    if op=='knowledge.map.part':
        part=graph['components'].get(args['component'])
        if not part:raise ValueError('MAP_COMPONENT_NOT_FOUND')
        candidates=core.document_candidates(part,documents);selected=[x for x in row['configuration']['documents'] if x['component']==part['reference']]
        for doc in candidates:
            try:sources.original(r['path'],r['report'],doc['record_id']);doc['availability']='ORIGINAL_HASH_VERIFIED'
            except (ValueError,OSError):doc['availability']='ORIGINAL_UNAVAILABLE'
        for doc in selected:
            try:sources.original(r['path'],r['report'],doc['record_id'])
            except (ValueError,OSError):return {**identity,'state':'STALE_OR_UNAVAILABLE','result':None,'reason':'SELECTED_DOCUMENT_CHANGED_OR_REVOKED'}
        return {**identity,'part':part,'documents':candidates,'owner_document_declarations':selected,'document_review':'UNREVIEWED_APPLICABILITY','gaps':[*part['gaps'],'FITTED_GRADE_AND_OPERATING_CONDITIONS_NOT_VERIFIED','CURRENT_IMPLEMENTATION_AND_REVIEWED_TEST_ORACLE_NOT_BOUND','PHYSICAL_MEASUREMENT_UNAVAILABLE']}
    raise ValueError('MAP_OPERATION_UNKNOWN')

def dispatch(kernel,op,args,p):
    result=_dispatch(kernel,op,args,p)
    if op in ('knowledge.map.get','knowledge.map.part','knowledge.map.net','knowledge.map.trace','knowledge.map.evidence') and result.get('state')=='REFERENCE_MAP_AVAILABLE':
        try:
            with kernel.db() as db:live=load(db,p.identity,args['id'])
            if revision(live)!=result['revision']:raise ValueError('MAP_SCOPE_CHANGED_DURING_READ')
            fresh(kernel,live)
        except (ValueError,OSError,KeyError) as exc:
            return {'state':'STALE_OR_UNAVAILABLE','id':args['id'],'result':None,'reason':activity.redact(exc),'physical_qualification':False}
    return result
