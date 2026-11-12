"""Reviewed research exchange in the existing Ledger Kernel; no new executor."""
from __future__ import annotations
import hashlib, re, time, uuid, urllib.request, urllib.error
from pathlib import Path
from sdk.cli.arc1cli import research_packets as c,record_store as records
from . import memory_service as memory,intake_service as intake,activity,clip
ID=intake.ID;TEXT=intake.TEXT;SHA=intake.SHA
FIELDS={
 'research.status':({},[]),'research.policy':({},[]),
 'research.policy.set':({'namespaces':{'type':'array','items':ID,'maxItems':32},'manual':{'type':'boolean'},'gemini':{'type':'boolean'},'max_calls':{'type':'integer','minimum':0,'maximum':100},'max_input_bytes':{'type':'integer','minimum':1024,'maximum':60000},'max_output_tokens':{'type':'integer','minimum':128,'maximum':8192}},['namespaces','manual','gemini','max_calls','max_input_bytes','max_output_tokens']),
 'research.create':({'question':{'type':'string','maxLength':1500},'constraints':{'type':'array'},'attempts':{'type':'array'},'unknowns':{'type':'array'},'why':{'type':'string','maxLength':1500},'references':{'type':'array'}},['question','constraints','attempts','unknowns','why','references']),
 'research.list':({},[]),'research.request':({'id':ID},['id']),
 'research.export':({'id':ID,'expected_digest':SHA,'destination':TEXT},['id','expected_digest','destination']),
 'research.import':({'path':TEXT},['path']),
 'research.return':({'id':SHA},['id']),
 'research.review':({'id':SHA,'disposition':{'type':'string','enum':['approved_for_evaluation','rejected','inconclusive']},'reason':intake.REASON},['id','disposition','reason']),
 'research.evaluate':({'id':SHA,'index':{'type':'integer','minimum':0,'maximum':7}},['id','index']),
 'research.gemini':({'id':ID,'expected_digest':SHA},['id','expected_digest'])}
APPROVE={'research.policy.set','research.export','research.import','research.review','research.evaluate','research.gemini'}
SCOPES={op:'approve' if op in APPROVE else 'execute' if op=='research.create' else 'read' for op in FIELDS}
DEFAULT={'revision':0,'namespaces':[],'manual':False,'gemini':False,'max_calls':0,'max_input_bytes':12000,'max_output_tokens':1024}
def ensure(db):db.execute('CREATE TABLE IF NOT EXISTS stacy_research(owner TEXT,kind TEXT,id TEXT,payload TEXT,sha256 TEXT,PRIMARY KEY(owner,kind,id))')
def put(db,owner,kind,ident,value):
    raw=records.canonical(value)
    if len(raw)>512*1024:raise ValueError('RESEARCH_RECORD_BOUND')
    if db.execute('SELECT count(*) FROM stacy_research WHERE owner=?',(owner,)).fetchone()[0]>=2000 and not db.execute('SELECT 1 FROM stacy_research WHERE owner=? AND kind=? AND id=?',(owner,kind,ident)).fetchone():raise ValueError('RESEARCH_OWNER_RECORD_BOUND')
    db.execute('INSERT OR REPLACE INTO stacy_research VALUES(?,?,?,?,?)',(owner,kind,ident,raw.decode(),hashlib.sha256(raw).hexdigest()))
def get(db,owner,kind,ident,default=None):
    row=db.execute('SELECT payload,sha256 FROM stacy_research WHERE owner=? AND kind=? AND id=?',(owner,kind,ident)).fetchone()
    if row is None:
        if default is not None:return dict(default)
        raise ValueError('RESEARCH_NOT_FOUND_OR_NOT_OWNED')
    if hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise ValueError('RESEARCH_RECORD_CORRUPT')
    return records.strict(row[0])
def rows(db,owner,kind):return [get(db,owner,kind,r[0]) for r in db.execute('SELECT id FROM stacy_research WHERE owner=? AND kind=? ORDER BY rowid',(owner,kind)).fetchall()]
def event(db,owner,state):activity.append(db,activity.make_event(owner,'research.state',state))
def policy(db,owner):return get(db,owner,'policy','current',DEFAULT)
def current(db,owner,request):
    passages,gaps=memory.recheck_references(db,owner,request['bindings'])
    if gaps:raise ValueError('RESEARCH_ORIGINALS_UNAVAILABLE_OR_CHANGED')
    return passages

def authorize(db,owner,request,channel,expected):
    p=policy(db,owner)
    if request['digest']!=expected:raise ValueError('RESEARCH_PREVIEW_CHANGED')
    if request['policy_revision']!=p['revision']:raise ValueError('RESEARCH_POLICY_CHANGED_RECREATE_PREVIEW')
    if not p[channel] or any(v['namespace'] not in p['namespaces'] for v in request['bindings']):raise ValueError('RESEARCH_DISCLOSURE_NOT_AUTHORIZED')
    current(db,owner,request)
    return p

def create(kernel,owner,args):
    with kernel.db() as db:
        p=policy(db,owner);bindings=memory.capture_references(db,owner,args['references'])
        if any(b['namespace'] not in p['namespaces'] for b in bindings):raise ValueError('RESEARCH_SELECT_PERMITTED_LIBRARY_FIRST')
        passages,gaps=memory.recheck_references(db,owner,bindings)
        if gaps:raise ValueError('RESEARCH_SOURCE_GAPS')
        excerpts=[{k:v[k] for k in ('id','name','locator','text','source_sha256','text_sha256')} for v in passages]
        if sum(len(v['text'].encode()) for v in excerpts)>24000:raise ValueError('RESEARCH_EXCERPT_BUDGET')
        ekp={'bindings':bindings,'excerpts':excerpts}
        value={'schema':c.REQUEST,'id':uuid.uuid4().hex,'created':time.time(),'question':c.text(args['question']),
          'constraints':c.texts(args['constraints']),'attempts':c.texts(args['attempts']),'unknowns':c.texts(args['unknowns']),
          'why':c.text(args['why']),'bindings':bindings,'excerpts':excerpts,'source_generation':c.digest(bindings),'ekp_digest':c.digest(ekp),
          'policy_revision':p['revision'],'includes_activity':False,'includes_personality':False,'authority':'RESEARCH_DATA_NOT_EXECUTION_GRANT'}
        value['digest']=c.digest(value)
        if len(records.canonical(value))>50000:raise ValueError('RESEARCH_REQUEST_BUDGET')
        put(db,owner,'request',value['id'],value);event(db,owner,'DRAFT_CREATED_PRIVATE')
        return value

def export(kernel,owner,args):
    path=memory.fresh_destination(kernel,args['destination'],'.zip')
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');r=get(db,owner,'request',args['id']);p=authorize(db,owner,r,'manual',args['expected_digest'])
        raw=c.pack({'request.json':records.canonical(r),'response_template.json':records.canonical(c.template(r)),'INSTRUCTIONS.txt':c.INSTRUCTIONS.encode()})
        receipt={'id':uuid.uuid4().hex,'request':r['id'],'request_digest':r['digest'],'channel':'manual','policy_revision':p['revision'],
          'archive_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'created':time.time(),'state':'PREPARED_POSSIBLE_DISCLOSURE','activity_shared':False,'personality_shared':False}
        put(db,owner,'disclosure',receipt['id'],receipt);event(db,owner,'MANUAL_EXPORT_PREPARED')
    memory.publish(path,raw)
    with kernel.db() as db:
        receipt['state']='EXPORTED_FOR_OWNER_UPLOAD';put(db,owner,'disclosure',receipt['id'],receipt);event(db,owner,'MANUAL_EXPORT_COMMITTED')
    return {**receipt,'path':str(path),'encrypted':False,'upload_performed':False}

def return_dir(kernel,owner):
    from .session import config_dir
    return config_dir()/'research_returns'/hashlib.sha256(owner.encode()).hexdigest()

def import_bytes(kernel,owner,raw):
    members=c.unpack(raw)
    if 'response.json' not in members:raise ValueError('RESEARCH_RESPONSE_REQUIRED')
    try:v=records.strict(members['response.json']);c.ident(v['request_id'])
    except (KeyError,TypeError,UnicodeError,RecursionError) as exc:raise ValueError('RESEARCH_RESPONSE_SCHEMA') from exc
    ident=hashlib.sha256(raw).hexdigest()
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');r=get(db,owner,'request',v['request_id']);c.validate_response(v,r,members);current(db,owner,r)
        disclosed=any(x['request']==r['id'] for x in rows(db,owner,'disclosure'))
        if not disclosed:raise ValueError('RESEARCH_REQUEST_NOT_DISCLOSED')
        old=get(db,owner,'return',ident,{})
        if old:return {**old,'duplicate':True}
        # Canonical response identity also catches ZIP metadata/recompression replays.
        semantic=c.digest({'response':v,'sources':{n:hashlib.sha256(b).hexdigest() for n,b in members.items() if n!='response.json'}})
        for old in rows(db,owner,'return'):
            if old['semantic_digest']==semantic:return {**old,'duplicate':True}
        folder=return_dir(kernel,owner);folder.mkdir(parents=True,exist_ok=True);path=folder/(ident+'.zip')
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest()!=ident:raise ValueError('RESEARCH_ORIGINAL_RETURN_CORRUPT')
        else:memory.publish(path,raw)
        value={'id':ident,'semantic_digest':semantic,'request':r['id'],'created':time.time(),'response':v,'disposition':'awaiting_owner_review','reviews':[],
          'new_source_admissions':0,'evaluations':[],'truth':'UNVERIFIED_EXTERNAL_FINDINGS','raw_archive_sha256':ident}
        put(db,owner,'return',ident,value);event(db,owner,'RETURN_IMPORTED_UNREVIEWED_DATA')
    return value

def checked_return(kernel,db,owner,ident):
    v=get(db,owner,'return',ident);p=return_dir(kernel,owner)/(ident+'.zip')
    if not p.is_file() or p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=v['raw_archive_sha256']:raise ValueError('RESEARCH_ORIGINAL_RETURN_MISSING_OR_CHANGED')
    return v

def validate_proposal(kernel,principal,proposal,request):
    from .engineering_cli import schemas
    from .agent_operations import validate
    from . import stac_bridge
    op=proposal['operation'];args=proposal['arguments']
    if op not in c.READS:raise ValueError('RESEARCH_PROPOSAL_READ_ONLY')
    validate(args,schemas()[op])
    # A foreign namespace cannot be smuggled through an otherwise read-only proposal.
    namespaces={b['namespace'] for b in request['bindings']}
    actual_op,actual_args=op,args
    if op.startswith('stac.'):
        compiled=stac_bridge.compile_program(args['program'])
        if compiled['kind']!='REFERENCE':raise ValueError('RESEARCH_STAC_REQUIRES_BOUND_LIBRARY_QUERY')
        actual_op=compiled['ir']['operation'];actual_args=compiled['ir']['arguments']
    if actual_args.get('namespace') not in namespaces:raise ValueError('RESEARCH_PROPOSAL_OUTSIDE_SHARED_LIBRARY')
    if actual_op=='references.resolve' and actual_args.get('id') not in {b['id'] for b in request['bindings']}:raise ValueError('RESEARCH_PROPOSAL_UNSHARED_PASSAGE')

def evaluate(kernel,principal,args):
    owner=principal.identity
    with kernel.db() as db:
        v=checked_return(kernel,db,owner,args['id']);r=get(db,owner,'request',v['request'])
        if v['disposition']!='approved_for_evaluation':raise ValueError('RESEARCH_OWNER_REVIEW_REQUIRED')
        current(db,owner,r)
        if args['index']>=len(v['response']['proposals']):raise ValueError('RESEARCH_PROPOSAL_INDEX')
        prop=v['response']['proposals'][args['index']];validate_proposal(kernel,principal,prop,r)
        for prior in v['evaluations']:
            if prior['index']==args['index']:return {**prior,'duplicate':True}
    result=kernel.dispatch(prop['operation'],prop['arguments'],principal)
    receipt={'id':uuid.uuid4().hex,'index':args['index'],'at':time.time(),'operation':prop['operation'],'result':result,'truth':'READ_RESULT_NOT_ACCEPTED_ENGINEERING_PROOF'}
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');v=checked_return(kernel,db,owner,args['id'])
        if v['disposition']!='approved_for_evaluation':raise ValueError('RESEARCH_REVIEW_CHANGED')
        current(db,owner,r)
        for prior in v['evaluations']:
            if prior['index']==args['index']:return {**prior,'duplicate':True}
        v['evaluations'].append(receipt);put(db,owner,'return',v['id'],v);event(db,owner,'OWNER_REVIEWED_READ_EVALUATED')
    return receipt

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args):return None

def gemini_transport(model,key,payload):
    if not re.fullmatch('[A-Za-z0-9_.-]{1,120}',model):raise ValueError('RESEARCH_CONFIGURE_EXPLICIT_GEMINI_MODEL')
    req=urllib.request.Request(clip.API+'/models/'+model+':generateContent',data=records.canonical(payload),headers={'Content-Type':'application/json','x-goog-api-key':key},method='POST')
    try:
        with urllib.request.build_opener(NoRedirect()).open(req,timeout=30) as response:raw=response.read(256*1024+1)
    except (urllib.error.URLError,TimeoutError,OSError) as exc:raise ValueError('RESEARCH_PROVIDER_NETWORK_FAILED_NO_AUTO_RETRY') from exc
    if len(raw)>256*1024:raise ValueError('RESEARCH_PROVIDER_RESPONSE_BOUND')
    return records.strict(raw)

def gemini(kernel,owner,args):
    settings=clip.Settings.load()
    if not settings.api_key() or not settings.model:raise ValueError('RESEARCH_CONFIGURE_KEY_AND_EXPLICIT_MODEL_FIRST')
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');r=get(db,owner,'request',args['id']);p=authorize(db,owner,r,'gemini',args['expected_digest'])
        payload={'contents':[{'role':'user','parts':[{'text':c.INSTRUCTIONS+'\nReturn only response.json, no attachments. new_sources must be empty.\nREQUEST:\n'+records.canonical(r).decode()+'\nRESPONSE TEMPLATE:\n'+records.canonical(c.template(r)).decode()}]}],
          'generationConfig':{'maxOutputTokens':p['max_output_tokens'],'responseMimeType':'application/json','temperature':0.2}}
        if len(records.canonical(payload))>p['max_input_bytes']:raise ValueError('RESEARCH_PROVIDER_INPUT_BUDGET')
        # Lifetime counter persists independently of changing limits: policy edits never reset spend.
        counter=get(db,owner,'usage','lifetime',{'calls':0})
        if counter['calls']>=p['max_calls']:raise ValueError('RESEARCH_PROVIDER_CALL_LIMIT')
        counter['calls']+=1;put(db,owner,'usage','lifetime',counter)
        receipt={'id':uuid.uuid4().hex,'request':r['id'],'request_digest':r['digest'],'channel':'gemini','policy_revision':p['revision'],'created':time.time(),
          'state':'RESERVED_POSSIBLE_DISCLOSURE','model':settings.model,'input_bytes':len(records.canonical(payload)),'input_sha256':c.digest(payload),'max_output_tokens':p['max_output_tokens'],'activity_shared':False,'personality_shared':False}
        put(db,owner,'disclosure',receipt['id'],receipt);event(db,owner,'GEMINI_DISCLOSURE_RESERVED')
    try:
        data=gemini_transport(settings.model,settings.api_key(),payload)
        if not isinstance(data,dict):raise ValueError('RESEARCH_PROVIDER_SCHEMA')
        candidates=data.get('candidates',[])
        if not isinstance(candidates,list) or any(not isinstance(v,dict) for v in candidates):raise ValueError('RESEARCH_PROVIDER_SCHEMA')
        if not candidates or candidates[0].get('finishReason')!='STOP':raise ValueError('RESEARCH_PROVIDER_INCOMPLETE_RETURN')
        content=candidates[0].get('content',{})
        if not isinstance(content,dict):raise ValueError('RESEARCH_PROVIDER_SCHEMA')
        parts=content.get('parts',[])
        if not isinstance(parts,list) or any(not isinstance(v,dict) or 'text' in v and not isinstance(v['text'],str) for v in parts):raise ValueError('RESEARCH_PROVIDER_SCHEMA')
        if any('functionCall' in v for v in parts):raise ValueError('RESEARCH_PROVIDER_TOOL_CALL_FORBIDDEN')
        raw=''.join(v.get('text','') for v in parts if not v.get('thought')).encode()
        if len(raw)>c.MAX_JSON:raise ValueError('RESEARCH_PROVIDER_RESPONSE_BOUND')
        result=import_bytes(kernel,owner,c.pack({'response.json':raw}));receipt.update(state='RETURN_VALIDATED_AWAITING_REVIEW',return_id=result['id'])
    except (ValueError,KeyError,TypeError,UnicodeError,RecursionError):
        with kernel.db() as db:
            receipt['state']='FAILED_OR_INVALID_CALL_CHARGED_TO_LIMIT';put(db,owner,'disclosure',receipt['id'],receipt);event(db,owner,'GEMINI_RETURN_FAILED')
        raise ValueError('RESEARCH_GEMINI_FAILED_OR_INVALID_RECEIPT_RETAINED_NO_AUTO_RETRY')
    with kernel.db() as db:put(db,owner,'disclosure',receipt['id'],receipt);event(db,owner,'GEMINI_RETURN_VALIDATED')
    return {'disclosure':receipt,'return':result}

def dispatch(kernel,op,args,principal):
    owner=principal.identity
    if op=='research.create':return create(kernel,owner,args)
    if op=='research.export':return export(kernel,owner,args)
    if op=='research.gemini':return gemini(kernel,owner,args)
    if op=='research.import':
        path=Path(args['path'])
        if not path.is_file() or path.is_symlink() or path.stat().st_size>c.MAX_ARCHIVE:raise ValueError('RESEARCH_ARCHIVE_BOUND_OR_LINK')
        with path.open('rb') as stream:raw=stream.read(c.MAX_ARCHIVE+1)
        return import_bytes(kernel,owner,raw)
    if op=='research.evaluate':return evaluate(kernel,principal,args)
    with kernel.db() as db:
        if op=='research.status':return {'schema':'arc.research-exchange/1','state':'LOCAL_REVIEWED_EXCHANGE','live_provider_qualified':False,'default_disclosure':'DENIED','background_uploads':False,'scripts_executed':False,'idle_study':'PASS_8','budget':'LIFETIME_CALLS_INPUT_BYTES_OUTPUT_TOKEN_CAP; NOT_A_PROVIDER_BILLING_CAP'}
        if op=='research.policy':return {**policy(db,owner),'usage':get(db,owner,'usage','lifetime',{'calls':0})}
        if op=='research.policy.set':
            db.execute('BEGIN IMMEDIATE')
            for ns in args['namespaces']:intake.namespace(db,ns,owner)
            if len(args['namespaces'])>32 or len(set(args['namespaces']))!=len(args['namespaces']):raise ValueError('RESEARCH_DUPLICATE_LIBRARY')
            value={**args,'revision':policy(db,owner)['revision']+1};put(db,owner,'policy','current',value);event(db,owner,'OWNER_DISCLOSURE_POLICY_SET');return value
        if op=='research.list':return {'requests':rows(db,owner,'request'),'returns':rows(db,owner,'return'),'disclosures':rows(db,owner,'disclosure')}
        if op=='research.request':
            r=get(db,owner,'request',args['id']);passages,gaps=memory.recheck_references(db,owner,r['bindings']);return {'request':r,'applicability':'CURRENT' if not gaps else 'STALE_OR_UNAVAILABLE','gaps':gaps}
        if op=='research.return':
            v=checked_return(kernel,db,owner,args['id']);r=get(db,owner,'request',v['request']);_,gaps=memory.recheck_references(db,owner,r['bindings']);return {**v,'applicability':'CURRENT' if not gaps else 'STALE_OR_UNAVAILABLE','gaps':gaps}
        if op=='research.review':
            db.execute('BEGIN IMMEDIATE');v=checked_return(kernel,db,owner,args['id']);r=get(db,owner,'request',v['request'])
            if args['disposition']=='approved_for_evaluation':current(db,owner,r)
            v['disposition']=args['disposition'];v['reviews'].append({'disposition':args['disposition'],'reason':args['reason'],'at':time.time(),'actor':owner})
            if len(v['reviews'])>100:raise ValueError('RESEARCH_REVIEW_HISTORY_BOUND')
            put(db,owner,'return',v['id'],v);event(db,owner,'OWNER_RETURN_DISPOSITION');return v
    raise ValueError('RESEARCH_OPERATION')
