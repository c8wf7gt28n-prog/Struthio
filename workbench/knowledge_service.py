"""Owner-scoped source connections over existing Kernel jobs and activity."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,tempfile,time,uuid
from pathlib import Path
from sdk.cli.arc1cli import knowledge_sources as sources,record_store as records,reference_extract as extract
from . import activity,intake_service as intake,record_io

ID=intake.ID;SHA=intake.SHA;TEXT=intake.TEXT
FIELDS={
 'knowledge.status':({},[]),
 'knowledge.get':({'id':ID},['id']),
 'knowledge.sources':({'id':ID,'offset':{'type':'integer','minimum':0,'maximum':20000},'limit':{'type':'integer','minimum':1,'maximum':200}},['id']),
 'knowledge.search':({'id':ID,'query':{'type':'string','minLength':1,'maxLength':200},'limit':{'type':'integer','minimum':1,'maximum':40}},['id','query']),
 'knowledge.attach':({'path':TEXT,'manifest_sha256':SHA,'request_key':TEXT},['path','manifest_sha256']),
 'knowledge.baseline.inspect':({'path':TEXT,'archive_sha256':SHA,'request_key':TEXT},['path','archive_sha256']),
 'knowledge.baseline.select':({'id':ID,'reason':intake.REASON},['id','reason']),
 'knowledge.revoke':({'id':ID,'reason':intake.REASON},['id','reason']),
 'knowledge.page':({'id':ID,'record_id':{'type':'string','minLength':1,'maxLength':600},'page_index':{'type':'integer','minimum':0,'maximum':10000},'render':{'type':'boolean'},'request_key':TEXT},['id','record_id','page_index']),
 'knowledge.page.result':({'job':ID},['job'])}
SCOPES={op:'approve' if op in ('knowledge.attach','knowledge.baseline.inspect','knowledge.baseline.select','knowledge.revoke') else 'execute' if op=='knowledge.page' else 'read' for op in FIELDS}
JOB_TOOLS={'knowledge.verify','knowledge.page'}
OPTIONS={'type':'object','additionalProperties':False,'properties':{
 'kind':{'type':'string','enum':['ROM','BASELINE']},'path':TEXT,'expected_sha256':SHA,'id':ID,
 'record_id':{'type':'string','minLength':1,'maxLength':600},'page_index':{'type':'integer','minimum':0,'maximum':10000},'render':{'type':'boolean'}}}

from . import engineering_map as map_service
FIELDS.update(map_service.FIELDS);SCOPES.update(map_service.SCOPES);JOB_TOOLS.add('knowledge.map')
OPTIONS['properties'].update({'baseline':ID,'rom':ID})

def ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS knowledge_sources(owner TEXT,id TEXT,kind TEXT,payload TEXT,sha256 TEXT,PRIMARY KEY(owner,id))')
    map_service.ensure(db)
def encoded(value):return records.canonical(value).decode()
def load(db,owner,ident):
    row=db.execute('SELECT payload,sha256 FROM knowledge_sources WHERE owner=? AND id=?',(owner,ident)).fetchone()
    if not row:raise ValueError('PRIVATE_KNOWLEDGE_SOURCE_NOT_FOUND')
    if hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise ValueError('KNOWLEDGE_PRIVATE_RECORD_CHANGED')
    return json.loads(row[0])
def save(db,value):
    raw=encoded(value)
    if len(raw.encode())>512*1024:raise ValueError('KNOWLEDGE_PRIVATE_RECORD_LIMIT')
    db.execute('INSERT OR REPLACE INTO knowledge_sources VALUES(?,?,?,?,?)',(value['owner'],value['id'],value['kind'],raw,hashlib.sha256(raw.encode()).hexdigest()))
    activity.append(db,activity.make_event(value['owner'],'knowledge.state',value['state'],source_generation=str(value['generation'])))
def fresh(row):
    if row['state']=='REVOKED':raise ValueError('KNOWLEDGE_SOURCE_REVOKED')
    if row['report']['reader']!=sources.fingerprint():raise ValueError('KNOWLEDGE_READER_CHANGED_REVERIFY_REQUIRED')
    if row['kind']=='ROM':sources.header(row['path'],row['report']['manifest_sha256'])
    elif records.sha(sources.regular(row['path']))!=row['report']['archive_sha256']:raise ValueError('KNOWLEDGE_BASELINE_CHANGED')
    return row
def public(row):
    return {k:v for k,v in row.items() if k not in ('path','owner')}
def check(kernel,job):
    if kernel.record('jobs',job['id']).get('cancel'):raise ValueError('KNOWLEDGE_JOB_CANCELLED')

def authorize_job(kernel,tool,opts,principal):
    if tool=='knowledge.map':return map_service.authorize(kernel,opts,principal)
    if tool=='knowledge.verify':
        if 'approve' not in principal.scopes:raise ValueError('KNOWLEDGE_CONNECTION_REQUIRES_OWNER_APPROVAL')
        if set(opts)!={'kind','path','expected_sha256'}:raise ValueError('KNOWLEDGE_VERIFY_OPTIONS')
    elif tool=='knowledge.page':
        if 'read' not in principal.scopes:raise ValueError('KNOWLEDGE_PAGE_REQUIRES_READ_SCOPE')
        if not {'id','record_id','page_index'}<=set(opts) or set(opts)-{'id','record_id','page_index','render'}:raise ValueError('KNOWLEDGE_PAGE_OPTIONS')
        with kernel.db() as db:
            row=fresh(load(db,principal.identity,opts['id']))
            if row['kind']!='ROM':raise ValueError('KNOWLEDGE_ROM_REQUIRED')
            sources.original(row['path'],row['report'],opts['record_id'])
    else:raise ValueError('KNOWLEDGE_TOOL_UNKNOWN')

def dispatch(kernel,op,args,principal):
    owner=principal.identity
    if op in map_service.FIELDS:return map_service.dispatch(kernel,op,args,principal)
    if op in ('knowledge.attach','knowledge.baseline.inspect','knowledge.page'):
        if op=='knowledge.page':opts={k:v for k,v in args.items() if k!='request_key'};tool='knowledge.page'
        else:
            opts={'kind':'ROM' if op=='knowledge.attach' else 'BASELINE','path':args['path'],
                  'expected_sha256':args['manifest_sha256' if op=='knowledge.attach' else 'archive_sha256']};tool='knowledge.verify'
        return kernel.submit({'tool':tool,'knowledge':opts,'request_key':args.get('request_key',uuid.uuid4().hex),'timeout':600},principal)
    if op=='knowledge.status':
        with kernel.db() as db:
            rows=[load(db,owner,r[0]) for r in db.execute('SELECT id FROM knowledge_sources WHERE owner=? ORDER BY rowid',(owner,))]
        summaries=[]
        for row in rows:
            try:fresh(row);state=row['state']
            except (ValueError,OSError):state='UNAVAILABLE_OR_STALE'
            summaries.append({'id':row['id'],'kind':row['kind'],'state':state,'generation':row['generation'],
              'title':row['title'],'report':row['report']})
        return {'schema':'arc.knowledge-status/1','sources':summaries,'current_project_promoted':False,
          'model_calls':0,'physical_qualification':False}
    if op=='knowledge.page.result':
        job=kernel.record('jobs',args['job']);kernel.require_owner(job,principal)
        if job['tool']!='knowledge.page':raise ValueError('KNOWLEDGE_PAGE_JOB_REQUIRED')
        if job['state']!='Completed':return {'state':job['state'],'text':None,'image':None}
        name='build/knowledge/runs/'+job['id']+'/result.json'
        evidence=kernel.record('evidence',job['evidence'])
        if evidence.get('job')!=job['id'] or evidence.get('state')!='Completed':raise ValueError('KNOWLEDGE_PAGE_EVIDENCE_REQUIRED')
        binding=next((a for a in evidence.get('artifacts',[]) if a['path']==name),None)
        raw=sources.regular(kernel.root/name).read_bytes()
        if not binding or len(raw)!=binding['bytes'] or hashlib.sha256(raw).hexdigest()!=binding['sha256']:raise ValueError('KNOWLEDGE_PAGE_RESULT_CHANGED')
        result=record_io.strict_json(raw)
        if result.get('job_id')!=job['id'] or result.get('source_connection')!=job['request_spec']['knowledge']['id']:raise ValueError('KNOWLEDGE_PAGE_JOB_BINDING_CHANGED')
        with kernel.db() as db:
            try:
                row=fresh(load(db,owner,result['source_connection']))
                if row['generation']!=result['connection_generation']:raise ValueError('KNOWLEDGE_CONNECTION_CHANGED')
                sources.original(row['path'],row['report'],result['record_id'])
                if result.get('image') and records.sha(kernel.root/result['image'])!=result['image_sha256']:raise ValueError('KNOWLEDGE_IMAGE_CHANGED')
            except (ValueError,OSError):return {'state':'UNAVAILABLE_OR_STALE','text':None,'image':None}
        return result
    with kernel.db() as db:
        row=load(db,owner,args['id'])
        if op=='knowledge.revoke':
            row.update(state='REVOKED',generation=row['generation']+1,reason=args['reason']);save(db,row);return public(row)
        fresh(row)
        if op=='knowledge.baseline.select':
            if row['kind']!='BASELINE':raise ValueError('KNOWLEDGE_BASELINE_REQUIRED')
            row.update(state='OWNER_SELECTED_REFERENCE_BASELINE',generation=row['generation']+1,reason=args['reason'])
            row['report']['selection_state']=row['state'];save(db,row);return public(row)
        if op=='knowledge.get':return public(row)
        if row['kind']!='ROM':raise ValueError('KNOWLEDGE_ROM_REQUIRED')
    if op=='knowledge.sources':return sources.source_rows(row['path'],row['report'],args.get('offset',0),args.get('limit',100))
    if op=='knowledge.search':return sources.search(row['path'],row['report'],args['query'],args.get('limit',30))
    raise ValueError('KNOWLEDGE_OPERATION_UNKNOWN')

def verify(kernel,job):
    opts=job['request_spec']['knowledge'];check(kernel,job)
    if opts['kind']=='ROM':
        if records.sha(records.inside(opts['path'],'VOLUME.json'))!=opts['expected_sha256']:raise ValueError('KNOWLEDGE_EXPECTED_MANIFEST_MISMATCH')
        report=sources.verify_rom(opts['path'],lambda:check(kernel,job));identity=report['manifest_sha256'];title=report['volume_id'];state='ARCHIVE_VERIFIED_NOT_CURRENT_PROJECT'
    else:
        report=sources.scan_baseline(opts['path'],opts['expected_sha256'],lambda:check(kernel,job));identity=report['archive_sha256'];title='ARC-1 V1 reference snapshot';state='REFERENCE_SNAPSHOT_REQUIRES_OWNER_SELECTION'
    ident=sources.digest({'owner':job['owner'],'kind':opts['kind'],'source':identity})[:32]
    row={'id':ident,'owner':job['owner'],'kind':opts['kind'],'path':str(Path(opts['path']).absolute()),
       'title':title,'report':report,'state':state,'created':time.time(),'generation':1,'job':job['id']}
    with kernel.db() as db:
        old=db.execute('SELECT id FROM knowledge_sources WHERE owner=? AND id=?',(job['owner'],ident)).fetchone()
        if old:row['generation']=load(db,job['owner'],ident)['generation']+1
        count=db.execute('SELECT count(*) FROM knowledge_sources WHERE owner=?',(job['owner'],)).fetchone()[0]
        if not old and count>=32:raise ValueError('KNOWLEDGE_CONNECTION_LIMIT')
        check(kernel,job);fresh(row);save(db,row)
    return {'state':'VERIFIED','connection':public(row),'source_promotion':False,'model_calls':0}

def page(kernel,job):
    return original_page(kernel,job,job['request_spec']['knowledge'])

def original_page(kernel,job,opts):
    """Shared bounded original reader; caller supplies its actual registered job."""
    with kernel.db() as db:row=fresh(load(db,job['owner'],opts['id']))
    if row['kind']!='ROM':raise ValueError('KNOWLEDGE_ROM_REQUIRED')
    generation=row['generation'];path,source=sources.original(row['path'],row['report'],opts['record_id']);check(kernel,job)
    result=extract.bounded(opts['record_id'],path,source['sha256'])
    selected=[s for s in result['segments'] if s['locator'].get('kind')=='pdf_page' and s['locator'].get('page_index')==opts['page_index']]
    if not selected:raise ValueError('KNOWLEDGE_ORIGINAL_PAGE_TEXT_GAP')
    text=''.join(s['text'] for s in selected)
    if len(text)>16000:raise ValueError('KNOWLEDGE_ORIGINAL_PAGE_TEXT_LIMIT')
    answer={'state':'ORIGINAL_PAGE_REEXTRACTED','source_connection':row['id'],'connection_generation':generation,
      'record_id':opts['record_id'],'source_sha256':source['sha256'],'page_index':opts['page_index'],
      'page_label':selected[0]['locator']['page_label'],'locator':selected[0]['locator'],'text':text,'segments':selected,
      'reader':result['parser'],'extractor_hash':extract.rule_hash(),'metadata':result['metadata'],
      'current_design_authority':False,'engineering_claim_review':'NOT_GRANTED','translation':'NOT_PROVIDED','ocr':'NOT_PERFORMED',
      'gaps':result['gaps'],'image':None}
    if opts.get('render'):
        executable=shutil.which('pdftoppm')
        if not executable:answer['render_gap']='POPPLER_NOT_AVAILABLE_ON_THIS_HOST'
        else:
            executable=Path(executable).resolve();tool_hash=records.sha(executable)
            with tempfile.TemporaryDirectory(prefix='knowledge-page-') as tmp:
                pdf=Path(tmp)/'original.pdf';shutil.copyfile(path,pdf)
                if records.sha(pdf)!=source['sha256']:raise ValueError('KNOWLEDGE_RENDER_SOURCE_CHANGED')
                number=opts['page_index']+1
                proc=subprocess.run([str(executable),'-f',str(number),'-l',str(number),'-singlefile','-scale-to','1500','-png',str(pdf),str(Path(tmp)/'page')],capture_output=True,timeout=20)
                image=Path(tmp)/'page.png'
                if proc.returncode or not image.is_file() or image.stat().st_size>12*1024*1024:raise ValueError('KNOWLEDGE_RENDER_FAILED_OR_LIMIT')
                raw=image.read_bytes()
            if records.sha(executable)!=tool_hash:raise ValueError('KNOWLEDGE_RENDER_TOOL_CHANGED')
            answer.update(image='build/knowledge/runs/'+job['id']+'/page.png',image_sha256=hashlib.sha256(raw).hexdigest(),render_tool_sha256=tool_hash)
            records.atomic(kernel.root/answer['image'],raw)
    with kernel.db() as db:
        current=fresh(load(db,job['owner'],row['id']))
        if current['generation']!=generation:raise ValueError('KNOWLEDGE_CONNECTION_CHANGED_DURING_READ')
        sources.original(current['path'],current['report'],opts['record_id']);check(kernel,job)
        activity.append(db,activity.make_event(job['owner'],'knowledge.state','ORIGINAL_PAGE_REEXTRACTED',source_generation=str(generation)))
    return answer

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--job',required=True);args=parser.parse_args()
    if os.name!='nt':
        import resource
        resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(90,95))
    from .engineering_kernel import Kernel
    kernel=Kernel(args.root);job=kernel.record('jobs',args.job)
    try:result={'knowledge.verify':verify,'knowledge.page':page,'knowledge.map':map_service.build}[job['tool']](kernel,job);code=0
    except Exception as exc:result={'state':'FAILED','reason':activity.redact(exc)};code=1
    result.update(schema='arc.knowledge-job-result/1',job_id=job['id'],created=time.time(),network_calls=0)
    result['class']='STATIC_CHECK'
    record_io.write_json(kernel.root/'build/knowledge/runs'/job['id']/'result.json',result)
    print(encoded(result));return code
if __name__=='__main__':raise SystemExit(main())
