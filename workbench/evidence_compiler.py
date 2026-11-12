"""Evidence Compiler under the existing Kernel and ref_packets authority.

No model, network, design mutation, source admission or engineering approval.
Each invocation publishes a distinct receipt; equivalent frozen inputs share a
context digest. A cancelled/failed job can never supply a usable packet.
"""
from __future__ import annotations
import argparse, hashlib, os, time, uuid
from pathlib import Path
from sdk.cli.arc1cli import engineering_packets as c,engineering_map as graph_core,knowledge_sources as sources,reference_extract as extract,record_store as records,evidence_contracts as evidence
from . import activity,engineering_map as maps,intake_service as intake,memory_service as memory,record_io

ID=intake.ID;SHA=intake.SHA
PAGE={'type':'object','additionalProperties':False,'properties':{'record_id':{'type':'string','minLength':1,'maxLength':600},'page_index':{'type':'integer','minimum':0,'maximum':10000}},'required':['record_id','page_index']}
PROPS={'map':ID,'expected_revision':SHA,'component':maps.REF,'question':{'type':'string','minLength':1,'maxLength':1200},
 'lookup':{'type':'string','minLength':1,'maxLength':200},'pages':{'type':'array','maxItems':4,'uniqueItems':True,'items':PAGE},
 'source_packets':{'type':'array','maxItems':3,'uniqueItems':True,'items':ID},'max_bytes':{'type':'integer','minimum':8192,'maximum':c.MAX_BYTES}}
REQUIRED=['map','expected_revision','component','question']
OPTIONS={'type':'object','additionalProperties':False,'properties':PROPS,'required':REQUIRED}
FIELDS={'references.packet.compile':({**PROPS,'request_key':intake.TEXT},REQUIRED),'references.packets':({},[]),
 'references.packet.source':({'id':ID,'source':SHA},['id','source']),
 'references.packet.export':({'id':ID,'destination':intake.TEXT},['id','destination'])}
SCOPES={op:'execute' if op=='references.packet.compile' else 'approve' if op=='references.packet.export' else 'read' for op in FIELDS}
JOB_TOOLS={'references.compile'}
def connections():
    from . import knowledge_service
    return knowledge_service
def fingerprint():return hashlib.sha256(Path(__file__).read_bytes()+c.fingerprint().encode()+extract.rule_hash().encode()+Path(connections().__file__).read_bytes()).hexdigest()
def ensure(db):db.execute('CREATE TABLE IF NOT EXISTS ekp_receipts(id TEXT PRIMARY KEY,owner TEXT,sha256 TEXT,job TEXT)')
def handles(kernel,ident):
    with kernel.db() as db:return db.execute('SELECT 1 FROM ekp_receipts WHERE id=?',(ident,)).fetchone() is not None
def read_principal(owner):return maps.connections_operator(owner)
def read(kernel,op,args,owner):
    result=kernel.dispatch(op,args,read_principal(owner))
    if not result['ok']:raise ValueError(result['error']['message'])
    return result['result']
def legacy(kernel,ident,owner):
    if handles(kernel,ident):raise ValueError('EKP_SOURCE_PACKET_MUST_BE_LEGACY_V1')
    value=read(kernel,'references.packet',{'id':ident},owner)
    if value.get('schema')!='arc.reference-ekp/1' or value['state']!='CURRENT':raise ValueError('EKP_SOURCE_PACKET_STALE_OR_VERSION')
    return value
def scope(kernel,opts,owner):
    with kernel.db() as db:row=maps.load(db,owner,opts['map'])
    b,r,graph=maps.fresh(kernel,row)
    if maps.revision(row)!=opts['expected_revision']:raise ValueError('EKP_MAP_SCOPE_CHANGED')
    part=read(kernel,'knowledge.map.part',{'id':row['id'],'component':opts['component'],'expected_revision':opts['expected_revision']},owner)
    if part['state']!='REFERENCE_MAP_AVAILABLE':raise ValueError('EKP_MAP_PART_UNAVAILABLE')
    return row,b,r,graph,part
def authorize_job(kernel,tool,opts,principal):
    if tool not in JOB_TOOLS or not {'read','execute'}<=principal.scopes:raise ValueError('EKP_OWNER_READ_AND_EXECUTE_REQUIRED')
    if not set(REQUIRED)<=set(opts) or set(opts)-set(PROPS):raise ValueError('EKP_OPTIONS')
    # Kernel's JSON schema is the public boundary; repeat it for direct submit callers.
    from .agent_operations import validate
    validate(opts,OPTIONS)
    for key in ('map','expected_revision'):
        if not __import__('re').fullmatch('[0-9a-f]{'+str(64 if key=='expected_revision' else 32)+'}',opts[key]):raise ValueError('EKP_INPUT_IDENTITY')
    for key,cap in (('pages',4),('source_packets',3)):
        values=opts.get(key,[])
        if len(values)>cap or len({records.canonical(x) for x in values})!=len(values):raise ValueError('EKP_INPUT_LIST_BOUND')
    scope(kernel,opts,principal.identity)
    for ident in opts.get('source_packets',[]):legacy(kernel,ident,principal.identity)
def check(kernel,job):connections().check(kernel,job)
def capture_evidence(kernel,row,part):
    value=read(kernel,'knowledge.map.evidence',{'id':row['id'],'component':part['reference'],'expected_revision':maps.revision(row)},row['owner'])
    if value['state']!='REFERENCE_MAP_AVAILABLE':raise ValueError('EKP_EVIDENCE_SCOPE_CHANGED')
    return value['evidence']
def select_pages(r,part,opts):
    allowed={x['record_id'] for x in part['documents']}|{x['record_id'] for x in part['owner_document_declarations']}
    pages=opts.get('pages',[])
    if pages:
        if any(x['record_id'] not in allowed for x in pages):raise ValueError('EKP_DOCUMENT_NOT_ASSOCIATED_WITH_PART')
    else:
        lookup=opts.get('lookup',part['part']['mpn'])
        hits=sources.search(r['path'],r['report'],lookup,40)['hits'] if lookup else []
        pages=[{'record_id':h['record_id'],'page_index':h['page_index']} for h in hits if h['record_id'] in allowed and h['state']=='ARCHIVE_ORIGINAL_VERIFIED'][:2]
    return c.ordered(pages)
def compile_packet(kernel,job):
    opts=job['request_spec']['packet'];owner=job['owner'];row,b,r,graph,view=scope(kernel,opts,owner);part=view['part'];reader=fingerprint();check(kernel,job)
    passages=[];gaps=list(view['gaps']);facts=[];legacy_deps=[];page_deps=[]
    pins=part['pins'][:32]
    if len(part['pins'])>32:gaps.append('NATIVE_PIN_LIST_TRUNCATED_TO_32_USE_MAP_FOR_ALL_PINS')
    native={k:part[k] for k in ('reference','id','value','mpn','manufacturer','package','grade','operating_conditions','native_uuid','pcb_uuid','review_state')}
    native['pins']=pins
    locator={'kind':'native_component','archive_sha256':b['report']['archive_sha256'],'board_path':graph_core.PCB,'board_sha256':graph['source_manifest'][graph_core.PCB]['sha256'],
      'schematic':part['symbol'],'reference':part['reference'],'symbol_uuid':part['native_uuid'],'pcb_uuid':part['pcb_uuid'],'map_artifact':row['artifact'],'map_sha256':row['graph_sha256'],'json_pointer':'/components/'+part['reference']}
    native_passage=c.passage('Native reference '+part['reference'],row['graph_sha256'],locator,records.canonical(native).decode(),'REFERENCE_NATIVE_IDENTITIES_NOT_ACCEPTED_CURRENT_PROJECT');passages.append(native_passage)
    pages=select_pages(r,view,opts)
    if not pages:gaps.append('NO_APPLICABLE_ORIGINAL_PDF_PAGE_SELECTED')
    for page in pages:
        check(kernel,job);value=connections().original_page(kernel,job,{'id':r['id'],**page,'render':False})
        locator={k:v for k,v in value['locator'].items() if k not in ('text_start','text_end','offset_basis')}
        locator['extracted_segments']=[s['locator'] for s in value['segments']]
        p=c.passage(value['record_id'],value['source_sha256'],locator,value['text'],'VENDOR_ORIGINAL_APPLICABILITY_UNREVIEWED');passages.append(p)
        page_deps.append({'record_id':value['record_id'],'source_sha256':value['source_sha256'],'page_index':value['page_index'],'passage':p['id']});gaps.extend(value['gaps'])
    code=part['code_candidates'][:3]
    if len(part['code_candidates'])>len(code):gaps.append('CODE_MENTIONS_TRUNCATED_TO_3_NOT_PROVEN_IMPLEMENTATION')
    if code:
        content,manifest,_=graph_core.read_archive(b['path'],b['report'],lambda:check(kernel,job))
        for item in code:
            raw=content.get(item['path'])
            if raw is None or hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('EKP_CODE_SOURCE_CHANGED')
            lines=raw.decode('utf-8-sig').splitlines();start=max(1,item['line']-2);end=min(len(lines),item['line']+2);text='\n'.join(lines[start-1:end])
            if len(text)>4000:gaps.append('CODE_EXCERPT_OMITTED_LINE_BYTE_BUDGET');continue
            passages.append(c.passage(item['path'],item['sha256'],{'kind':'source_lines','path':item['path'],'line_start':start,'line_end':end,'archive_sha256':b['report']['archive_sha256']},text,'LEXICAL_MENTION_UNREVIEWED_IMPLEMENTATION'))
    for ident in sorted(opts.get('source_packets',[])):
        old=legacy(kernel,ident,owner);legacy_deps.append({'id':ident,'sha256':c.digest(old)})
        for p in old['passages']:
            # Preserve v1 IDs so reviewed facts retain their exact source locators.
            passages.append({k:p[k] for k in ('id','name','source_sha256','locator','text')}|{'authority':'REVIEWED_REFERENCE_ADMISSION_NOT_FITTED_PART_APPROVAL','content_trust':'REFERENCE_DATA_NOT_INSTRUCTIONS'})
        facts.extend(old['facts'])
    unique={}
    for p in passages:
        if p['id'] in unique and unique[p['id']]!=p:raise ValueError('EKP_CONFLICTING_PASSAGE_IDENTITY')
        unique[p['id']]=p
    unique_facts={}
    for fact in facts:
        if fact['id'] in unique_facts and unique_facts[fact['id']]!=fact:raise ValueError('EKP_CONFLICTING_FACT_IDENTITY')
        unique_facts[fact['id']]=fact
    evidence_refs=capture_evidence(kernel,row,part)
    gaps.extend(['DOCUMENT_GRADE_PACKAGE_AND_OPERATING_CONDITIONS_REVIEW_REQUIRED','SOURCE_FACTS_NOT_AUTOMATICALLY_EXTRACTED_FROM_PDF_TABLES','REVIEWED_REFERENCE_FACTS_NOT_AUTOMATICALLY_BOUND_TO_SELECTED_PART','CURRENT_IMPLEMENTATION_TO_ORACLE_REQUIREMENT_BINDING_UNPROVEN','PHYSICAL_BEHAVIOR_UNPROVEN'])
    if len(part['software'])>12:gaps.append('SOFTWARE_DECLARATIONS_TRUNCATED_TO_12')
    if not facts:gaps.append('NO_REVIEWED_QUANTITATIVE_SOURCE_FACTS_IMPORTED')
    if any(x.get('state')=='STALE_OR_UNAVAILABLE' for x in evidence_refs):gaps.append('BOUND_KERNEL_EVIDENCE_STALE_OR_UNAVAILABLE')
    requirements=[{'record':v,'state':'ARCHIVED_REQUIREMENT_NOT_ACCEPTED_CURRENT_ORACLE','source_passage':native_passage['id'],
      'source_path':'project/register/bindings.json','source_sha256':graph['source_manifest'].get('project/register/bindings.json',{}).get('sha256')} for v in part['requirements'][:12]]
    if len(part['requirements'])>12:gaps.append('REQUIREMENT_LIST_TRUNCATED_TO_12')
    limit=opts.get('max_bytes',65536)
    context=c.context(question=opts['question'],scope={'map':row['id'],'view_revision':maps.revision(row),'component':part['reference'],'mpn':part['mpn'],'package':part['package'],'grade':'UNVERIFIED',
      'owner_conditions':row['configuration']['conditions'],'owner_document_declarations':view['owner_document_declarations'],'source_digest':row['source_digest'],'source_revision_authority':'OWNER_SELECTED_REFERENCE_BASELINE_V1'},
      passages=list(unique.values()),facts=list(unique_facts.values()),relationships={'native':native,'source_passage':native_passage['id'],'relation':'NATIVE_NET_MEMBERSHIP_NOT_SIGNAL_DIRECTION','software_declarations':part['software'][:12]},
      requirements=requirements,evidence_refs=evidence_refs,gaps=gaps,budget={'max_bytes':limit,'max_original_pages':4,'selected_original_pages':len(pages),'max_pins':32,'max_code_mentions':3,'network_calls':0})
    deps={'map':row['id'],'view_revision':maps.revision(row),'baseline_generation':b['generation'],'rom_generation':r['generation'],'pages':c.ordered(page_deps),'legacy_packets':legacy_deps,'evidence_digest':c.digest(evidence_refs)}
    value=c.envelope(context,uuid.uuid4().hex,job['id'],time.time(),deps,reader,limit);raw=records.canonical(value)
    # Final source/condition/oracle boundary after all potentially slow reads.
    validate_inputs(kernel,value,owner);check(kernel,job)
    artifact='build/references/runs/'+job['id']+'/packet.json';records.atomic(kernel.root/artifact,raw)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');check(kernel,job)
        if db.execute('SELECT count(*) FROM ekp_receipts WHERE owner=?',(owner,)).fetchone()[0]>=256:raise ValueError('EKP_PRIVATE_PACKET_COUNT_LIMIT')
        db.execute('INSERT INTO ref_packets VALUES(?,?,?)',(value['id'],'map:'+row['id'],raw.decode()))
        db.execute('INSERT INTO ekp_receipts VALUES(?,?,?,?)',(value['id'],owner,hashlib.sha256(raw).hexdigest(),job['id']))
        activity.append(db,activity.make_event(owner,'references.packet','EKP_V2_COMPILED',source_generation=str(row['generation'])))
    return {'state':'EVIDENCE_PACKET_COMPILED','packet':value['id'],'context_digest':value['context_digest'],'artifact':artifact,'bytes':len(raw),'gaps':len(context['gaps']),'model_calls':0,'physical_qualification':False}
def validate_inputs(kernel,value,owner):
    if value['schema']!=c.VERSION or value['reader']!=fingerprint():raise ValueError('EKP_COMPILER_OR_EXTRACTOR_CHANGED')
    context=value['context'];deps=value['dependencies']
    if c.digest(context)!=value['context_digest'] or value['program_id']!=value['context_digest'] or value['passages']!=context['passages'] or value['facts']!=context['facts']:raise ValueError('EKP_CONTEXT_DERIVATIVE_CHANGED')
    opts={'map':deps['map'],'expected_revision':deps['view_revision'],'component':context['scope']['component']};row,b,r,graph,part=scope(kernel,opts,owner)
    if (b['generation'],r['generation'])!=(deps['baseline_generation'],deps['rom_generation']):raise ValueError('EKP_SOURCE_GENERATION_CHANGED')
    for p in deps['pages']:
        _,source=sources.original(r['path'],r['report'],p['record_id'])
        if source['sha256']!=p['source_sha256']:raise ValueError('EKP_PAGE_SOURCE_CHANGED')
    for old in deps['legacy_packets']:
        if c.digest(legacy(kernel,old['id'],owner))!=old['sha256']:raise ValueError('EKP_REVIEWED_SOURCE_PACKET_CHANGED')
    if c.digest(capture_evidence(kernel,row,part['part']))!=deps['evidence_digest']:raise ValueError('EKP_KERNEL_ORACLE_OR_EVIDENCE_CHANGED')
    # A slow evidence read must not publish an earlier source/condition view.
    with kernel.db() as db:live=maps.load(db,owner,deps['map'])
    b2,r2,_=maps.fresh(kernel,live)
    if maps.revision(live)!=deps['view_revision'] or (b2['generation'],r2['generation'])!=(b['generation'],r['generation']):raise ValueError('EKP_SCOPE_CHANGED_BEFORE_PUBLICATION')
    for p in deps['pages']:sources.original(r2['path'],r2['report'],p['record_id'])
    for old in deps['legacy_packets']:
        if c.digest(legacy(kernel,old['id'],owner))!=old['sha256']:raise ValueError('EKP_REVIEW_CHANGED_BEFORE_PUBLICATION')
def get(kernel,ident,owner):
    with kernel.db() as db:
        receipt=db.execute('SELECT owner,sha256,job FROM ekp_receipts WHERE id=?',(ident,)).fetchone()
        if not receipt or receipt[0]!=owner:raise ValueError('PRIVATE_EKP_NOT_FOUND')
        stored=db.execute('SELECT payload FROM ref_packets WHERE id=?',(ident,)).fetchone()
    try:
        if not stored or hashlib.sha256(stored[0].encode()).hexdigest()!=receipt[1]:raise ValueError('EKP_PRIVATE_RECORD_CHANGED')
        value=records.strict(stored[0]);j,ev,a,p=maps.artifact(kernel,receipt[2],'build/references/runs/'+receipt[2]+'/packet.json',receipt[1])
        if j['owner']!=owner or j['tool']!='references.compile' or value['job']!=j['id'] or value['id']!=ident or records.load(p)!=value:raise ValueError('EKP_JOB_BINDING_CHANGED')
        request=j['request_spec']['packet']
        if any(request[k]!=value['context']['scope'][v] for k,v in (('map','map'),('expected_revision','view_revision'),('component','component'))) or request['question']!=value['context']['question']:raise ValueError('EKP_REQUEST_BINDING_CHANGED')
        validate_inputs(kernel,value,owner)
        return value
    except (ValueError,OSError,KeyError,TypeError) as exc:
        return {'schema':c.VERSION,'id':ident,'state':'STALE_OR_UNAVAILABLE','reason':activity.redact(exc),'context':None,'passages':None,'facts':None,'cloud_disclosure':'NOT_GRANTED','physical_qualification':False}
def dispatch(kernel,op,args,principal):
    owner=principal.identity
    if op=='references.packet.compile':return kernel.submit({'tool':'references.compile','packet':{k:v for k,v in args.items() if k!='request_key'},'request_key':args.get('request_key',uuid.uuid4().hex),'timeout':600},principal)
    if 'read' not in principal.scopes:raise ValueError('EKP_READ_SCOPE_REQUIRED')
    if op=='references.packets':
        with kernel.db() as db:ids=[r[0] for r in db.execute('SELECT id FROM ekp_receipts WHERE owner=? ORDER BY rowid DESC',(owner,))]
        values=[get(kernel,ident,owner) for ident in ids]
        return {'schema':'arc.ekp-list/1','packets':[{'id':v['id'],'state':v['state'],'context_digest':v.get('context_digest'),'question':v['context']['question'] if v['context'] else None} for v in values]}
    ident=args.get('id',args.get('packet'));value=get(kernel,ident,owner)
    if op=='references.packet':return value
    if value['state']!='CURRENT':raise ValueError('EKP_STALE_OR_UNAVAILABLE')
    if op=='references.packet.source':
        source=next((p for p in value['passages'] if p['id']==args['source']),None)
        if source is None:raise ValueError('EKP_SOURCE_NOT_IN_PACKET')
        result={'schema':'arc.ekp-source/1','packet':ident,'context_digest':value['context_digest'],'source':source,'applicability':'NOT_GRANTED'}
    elif op=='references.answer.validate':result=evidence.validate_answer(args['answer'],value)
    elif op=='references.packet.export':
        path=memory.fresh_destination(kernel,args['destination'],'.json');raw=records.canonical(value)
        if get(kernel,ident,owner)['state']!='CURRENT':raise ValueError('EKP_CHANGED_BEFORE_EXPORT')
        memory.publish(path,raw)
        with kernel.db() as db:activity.append(db,activity.make_event(owner,'references.packet','EKP_LOCAL_EXPORT'))
        return {'state':'EXPORTED','path':str(path),'bytes':len(raw),'context_digest':value['context_digest'],'cloud_disclosure':'NOT_GRANTED'}
    else:raise ValueError('EKP_OPERATION_UNKNOWN')
    if get(kernel,ident,owner)['state']!='CURRENT':raise ValueError('EKP_CHANGED_BEFORE_PUBLICATION')
    return result
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--job',required=True);args=parser.parse_args()
    if os.name!='nt':
        import resource
        resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(90,95))
    from .engineering_kernel import Kernel
    kernel=Kernel(args.root);job=kernel.record('jobs',args.job)
    try:result=compile_packet(kernel,job);code=0
    except Exception as exc:result={'state':'FAILED','reason':activity.redact(exc)};code=1
    result.update(schema='arc.reference-compiler-result/1',job_id=job['id'],created=time.time(),network_calls=0);result['class']='STATIC_CHECK'
    record_io.write_json(kernel.root/'build/references/runs'/job['id']/'result.json',result)
    print(records.canonical(result).decode());return code
if __name__=='__main__':raise SystemExit(main())
