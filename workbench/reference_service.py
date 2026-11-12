"""Exact-reference, evidence and packet services over the existing Kernel DB/jobs.

Intake remains the admission authority. Rebuildable derivatives never replace an
original, and a located index row is not permission or evidence of availability.
"""
from __future__ import annotations
import argparse,hashlib,io,json,os,re,shutil,sqlite3,subprocess,tempfile,time,uuid,zipfile
from pathlib import Path
from sdk.cli.arc1cli import document_extract as extract,evidence_contracts as evidence,record_store as records,intake_files
from . import intake_service as intake,activity,record_io,project_context,locations
from . import pdf_service

ID=intake.ID;SHA=intake.SHA;TEXT=intake.TEXT;NS=intake.NS
SHORT={'type':'string','minLength':1,'maxLength':120}
CONDITIONS={'type':'object','additionalProperties':{'type':'string','maxLength':300},'maxProperties':20}
FIELDS={
 **pdf_service.FIELDS,
 'references.collection':(NS,['namespace']),
 'references.status':(NS,['namespace']),
 'references.index':({**NS,'request_key':TEXT},['namespace']),
 'references.sources':(NS,['namespace']),
 'references.search':({**NS,'query':{'type':'string','minLength':1,'maxLength':300},'limit':{'type':'integer','minimum':1,'maximum':40},'include_historical':{'type':'boolean'}},['namespace','query']),
 'references.passages':({**NS,'item':ID,'offset':{'type':'integer','minimum':0,'maximum':16000},'limit':{'type':'integer','minimum':1,'maximum':100}},['namespace','item']),
 'references.resolve':({**NS,'id':SHA,'item':ID,'include_historical':{'type':'boolean'}},['namespace','id']),
 'references.original':({**NS,'id':SHA,'item':ID},['namespace','id']),
 'references.render':({**NS,'id':SHA,'item':ID,'request_key':TEXT},['namespace','id']),
 'references.render.result':({'job':ID},['job']),
 'references.fact.add':({**NS,'id':SHA,'subject':SHORT,'property':SHORT,'variant':{'type':'string','maxLength':120},'conditions':CONDITIONS,
   'value':{'type':'string','maxLength':60},'unit':{'type':'string','maxLength':12},'polarity':{'type':'string','enum':['SUPPORT','REFUTE']},
   'role':{'type':'string','enum':['REQUIREMENT','SOURCE_CLAIM','HYPOTHESIS']},'quote':{'type':'string','minLength':1,'maxLength':1800},'reason':intake.REASON},
   ['namespace','id','subject','property','variant','conditions','value','unit','polarity','role','quote','reason']),
 'references.facts':({**NS,'subject':SHORT},['namespace']),
 'references.question':({**NS,'subject':SHORT,'property':SHORT,'variant':{'type':'string','maxLength':120},'conditions':CONDITIONS},['namespace','subject','property','variant','conditions']),
 'references.link.add':({**NS,'id':SHA,'subject':SHORT,'relation':{'type':'string','enum':['CITES','REQUIREMENT_FOR','RELATED_SOURCE','JOB_RESULT_FOR']},
   'basis':{'type':'string','enum':['OWNER_DECLARED','INFERRED']},'job':ID,'reason':intake.REASON},['namespace','id','subject','relation','basis','reason']),
 'references.atlas':({**NS,'subject':SHORT},['namespace','subject']),
 'references.native':({'component':SHORT},['component']),
 'references.impact':({**NS,'item':ID,'hypothetical_sha256':SHA},['namespace','item']),
 'references.packet.create':({**NS,'passages':{'type':'array','items':SHA,'minItems':1,'maxItems':8,'uniqueItems':True},'subject':SHORT,
   'question':{'type':'string','maxLength':500}},['namespace','passages']),
 'references.packet':({'id':ID},['id']),
 'references.answer.validate':({'packet':ID,'answer':{'type':'object'}},['packet','answer']),
 'references.volume.export':({**NS,'destination':TEXT,'expected_generation':{'type':'integer','minimum':0},
   'project':ID,'readable':{'type':'boolean'},'request_key':TEXT},['namespace','destination','expected_generation']),
 'references.volume.publish':({'job':ID},['job']),
 'references.volume.verify':({'path':TEXT,'request_key':TEXT},['path'])}
APPROVE={'references.original','references.fact.add','references.link.add','references.volume.export','references.volume.publish','references.volume.verify'}
EXECUTE={'references.index','references.render','references.packet.create'}
SCOPES={name:pdf_service.SCOPES.get(name,'approve' if name in APPROVE else 'execute' if name in EXECUTE else 'read') for name in FIELDS}
JOB_TOOLS={'references.index','references.render','references.export','references.verify',pdf_service.JOB}
OPTIONS={'type':'object','additionalProperties':False,'properties':{'namespace':ID,'id':SHA,'item':ID,'destination':TEXT,'path':TEXT,
 'expected_generation':{'type':'integer','minimum':0},'project':ID,'readable':{'type':'boolean'},**pdf_service.JOB_PROPERTIES}}
ANSWER_SCHEMA={'type':'object','additionalProperties':False,'properties':{
 'state':{'type':'string','enum':['ANSWER','INSUFFICIENT_EVIDENCE']},'text':{'type':'string','maxLength':8000},
 'citations':{'type':'array','maxItems':20,'items':{'type':'string','pattern':'^[0-9a-f]{64}$'}}},'required':['state','text','citations']}

def fingerprint():
    # Export and navigation changes leave the reviewed extraction protocol intact.
    from inspect import getsource
    driver=''.join(getsource(fn) for fn in (current,resolve,quantity_in_quote,build_index)).encode()
    profile=hashlib.sha256(extract.rule_hash().encode()+Path(evidence.__file__).read_bytes()+driver).hexdigest()
    if profile=='9afeeba8eb9bc923d1a61efacbd4b214509aff0fbeee2586ecee9c7d0190e672':
        return '6831d53da1287eedca019ab1ba0c7c807e471363a548b414ca5a39ddacccd37d'
    return profile
def conditions(value):
    if not isinstance(value,dict) or len(value)>20 or any(not isinstance(k,str) or not 1<=len(k)<=120 or not isinstance(v,str) or len(v)>300 for k,v in value.items()):raise ValueError('REFERENCE_CONDITIONS_REQUIRE_BOUNDED_STRING_FIELDS')
    return value
def quantity_in_quote(quantity,quote):
    for match in re.finditer(r'([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(µs|μs|us|ns|ms|ps|GHz|MHz|kHz|Hz|mV|mA|MiB|KiB|s|V|A|B)(?![A-Za-z])',quote):
        candidate=evidence.quantity(match[1],match[2])
        if all(candidate[k]==quantity[k] for k in ('dimension','numerator','denominator')):return True
    return False
def encode(value):return records.canonical(value).decode()
def event(db,actor,state,ns):activity.append(db,activity.make_event(actor,'references.state',state,source_generation=str(ns.get('generation',0))))
def ensure(db):
    pdf_service.ensure(db)
    for sql in (
      'CREATE TABLE IF NOT EXISTS ref_sources(ns TEXT,item TEXT,payload TEXT,PRIMARY KEY(ns,item))',
      'CREATE TABLE IF NOT EXISTS ref_segments(ns TEXT,item TEXT,id TEXT,body TEXT,norm TEXT,payload TEXT,PRIMARY KEY(ns,item,id))',
      'CREATE INDEX IF NOT EXISTS ref_locator_lookup ON ref_segments(ns,id)',
      'CREATE TABLE IF NOT EXISTS ref_meta(ns TEXT PRIMARY KEY,generation INTEGER,payload TEXT)',
      'CREATE TABLE IF NOT EXISTS ref_facts(id TEXT PRIMARY KEY,ns TEXT,payload TEXT)',
      'CREATE TABLE IF NOT EXISTS ref_links(id TEXT PRIMARY KEY,ns TEXT,payload TEXT)',
      'CREATE TABLE IF NOT EXISTS ref_packets(id TEXT PRIMARY KEY,ns TEXT,payload TEXT)'):db.execute(sql)
    try:db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS ref_fts USING fts5(ns UNINDEXED,item UNINDEXED,id UNINDEXED,body)')
    except sqlite3.OperationalError:db.execute('CREATE TABLE IF NOT EXISTS ref_fts(ns TEXT,item TEXT,id TEXT,body TEXT)')

def meta(db,ns):
    row=db.execute('SELECT generation,payload FROM ref_meta WHERE ns=?',(ns,)).fetchone()
    return (row[0],json.loads(row[1])) if row else (0,{})
def bump(db,ns,detail=None):
    generation,old=meta(db,ns['id']);db.execute('INSERT OR REPLACE INTO ref_meta VALUES(?,?,?)',(ns['id'],generation+1,encode(detail or old)));return generation+1
def source(db,ns,item):
    row=db.execute('SELECT payload FROM ref_sources WHERE ns=? AND item=?',(ns['id'],item)).fetchone()
    if not row:raise ValueError('REFERENCE_INDEX_REQUIRED')
    return json.loads(row[0])
def current(db,ns,item,cache=None,historical=True):
    if cache is not None and item in cache:return cache[item]
    original=intake.load(db,'items',item)
    if original['namespace']!=ns['id']:raise ValueError('REFERENCE_NAMESPACE_MISMATCH')
    raw,decision=intake.eligible(db,ns,original,include_historical=historical)
    row=source(db,ns,item)
    if row['source_sha256']!=original['sha256'] or row['decision']!=decision['id'] or row['extractor_hash']!=fingerprint():raise ValueError('REFERENCE_INDEX_BINDING_STALE_REBUILD_REQUIRED')
    value=(original,row,raw)
    if cache is not None:cache[item]=value
    return value

def resolve(db,ns,ident,item=None,cache=None,historical=False):
    if cache is None:cache={}
    query='SELECT item,payload FROM ref_segments WHERE ns=? AND id=?';params=[ns['id'],ident]
    if item:query+=' AND item=?';params.append(item)
    found=db.execute(query+' ORDER BY item',params).fetchall()
    if not found:return {'state':'NOT_LOCATED','id':ident,'text':None,'gaps':['INDEX_ADMITTED_ORIGINALS_OR_CHECK_LOCATOR']}
    failures=[]
    for item_id,payload in found:
        try:
            original,row,raw=current(db,ns,item_id,cache,historical);segment=json.loads(payload)
            if hashlib.sha256(segment['text'].encode()).hexdigest()!=segment['text_sha256']:raise ValueError('REFERENCE_DERIVATIVE_TEXT_CHANGED')
            if extract.digest({'source_sha256':original['sha256'],'locator':segment['locator']})!=segment['locator_id'] or extract.digest({'locator_id':segment['locator_id'],'text_sha256':segment['text_sha256']})!=segment['id']:raise ValueError('REFERENCE_LOCATOR_INTEGRITY')
            key='projection:'+item_id
            if key not in cache:
                projection=extract.bounded(original['name'],intake.vault(ns).path(original['sha256']),original['sha256'])
                cache[key]={'segments':{v['id']:v for v in projection['segments']},'metadata':projection['metadata'],'parser':projection['parser']}
            actual=cache[key]['segments'].get(ident)
            if actual is None or actual['text']!=segment['text'] or actual['locator']!=segment['locator']:raise ValueError('REFERENCE_DERIVATIVE_DOES_NOT_MATCH_ORIGINAL')
            segment=actual
            return {**segment,'state':'CURRENT','item':item_id,'name':original['name'],'decision':original['decision_id'],
              'parser':cache[key]['parser'],'metadata':cache[key]['metadata'],'qualification':original.get('qualification',{}),'fact_verification':'NOT_IMPLIED_BY_LOCATION'}
        except (ValueError,OSError) as exc:failures.append(activity.redact(exc))
    return {'state':'LOCATED_BUT_UNAVAILABLE','id':ident,'text':None,'gaps':list(dict.fromkeys(failures))}

def require_current(value):
    if value['state']!='CURRENT':raise ValueError('REFERENCE_NOT_AVAILABLE: '+'; '.join(value.get('gaps',[])))
    return value

def facts(db,ns,subject=None):
    result=[];cache={}
    for row in db.execute('SELECT payload FROM ref_facts WHERE ns=? ORDER BY rowid',(ns['id'],)):
        fact=json.loads(row[0])
        if subject and fact['subject']!=subject:continue
        try:
            current(db,ns,fact['item'],cache)
            citation=resolve(db,ns,fact['passage'],fact['item'],cache,True)
            if citation['state']!='CURRENT' or fact['quote'] not in citation['text'] or fact['decision']!=citation['decision'] or fact['extractor_hash']!=fingerprint():raise ValueError('FACT_CITATION_STALE')
            if not quantity_in_quote(fact['quantity'],fact['quote']):raise ValueError('FACT_QUANTITY_NO_LONGER_MATCHES_QUOTE')
            result.append({**fact,'applicability':'CURRENT_REFERENCE'})
        except (ValueError,OSError):result.append({**{k:v for k,v in fact.items() if k not in ('quote','quantity')},'applicability':'STALE','support':'UNKNOWN','gap':'REQUALIFY_CURRENT_SOURCE_AND_LOCATOR'})
    return result

def links(db,ns,subject=None):
    result=[]
    for row in db.execute('SELECT payload FROM ref_links WHERE ns=? ORDER BY rowid',(ns['id'],)):
        link=json.loads(row[0])
        if subject and link['subject']!=subject:continue
        citation=resolve(db,ns,link['passage'],link['item'],historical=True)
        applicable=citation['state']=='CURRENT' and citation.get('decision')==link['decision'] and link['extractor_hash']==fingerprint()
        if link.get('job_id'):
            job=db.execute('SELECT owner,state,payload FROM jobs WHERE id=?',(link['job_id'],)).fetchone()
            applicable=bool(applicable and job and job[0]==ns['owner'] and job[1]=='Completed' and json.loads(job[2]).get('revision')==link['job_revision'])
        result.append({**link,'applicability':'CURRENT_REFERENCE' if applicable else 'STALE',
           'verified_connectivity':False,'physical_qualification':False})
    return result

def native(kernel,principal,component):
    r=kernel.dispatch('links.inspect',{'component':component},principal)
    if not r['ok'] or r['result'].get('status')=='PROJECT_NOT_ATTACHED':return {'state':'BLOCKED','component':component,'pins':[],
      'gaps':['ATTACH_REVIEWED_CURRENT_NATIVE_PROJECT','VERIFY_ROM_ORIGINALS_AND_CURRENT_VARIANT','PHYSICAL_BOARD_TEST_REQUIRED'],
      'qualification':'NOT_ESTABLISHED','source_promotion':'NOT_GRANTED'}
    result=r['result']
    return {'state':result['state'],'component':result.get('component'),'neighbors':result.get('neighbors',[]),'requirements':result.get('requirements',[]),
       'source_manifest':result['source_manifest'],'revision':result['revision'],'basis':'NATIVE_SCHEMATIC_SOURCE_NOT_ROUTED_OR_PHYSICAL_CONNECTIVITY',
       'physical_measurements':False,'fabrication':'HOLD','gaps':['ROUTED_AND_PHYSICAL_CONNECTIVITY_NOT_ESTABLISHED']}

def packet(db,ns,value):
    if value['state']=='CURRENT':
        cache={};refreshed=[]
        try:
            for row in value['inputs']:
                citation=require_current(resolve(db,ns,row['passage'],row['item'],cache,True))
                if citation['decision']!=row['decision'] or citation['source_sha256']!=row['sha256'] or citation['text_sha256']!=row['text_sha256']:raise ValueError('EKP_INPUT_CHANGED')
                refreshed.append(citation)
            fresh_facts=[]
            for fact in value['facts']:
                original=next((v for v in facts(db,ns) if v['id']==fact['id']),None)
                if original is None or original['applicability']!='CURRENT_REFERENCE':raise ValueError('EKP_FACT_STALE')
                fresh_facts.append(original)
            fresh_context={**value['context'],'passages':[{k:v[k] for k in ('id','name','source_sha256','locator','label','text')} for v in refreshed],'facts':fresh_facts}
            if value['facts']!=fresh_facts:raise ValueError('EKP_FACT_DERIVATIVE_CHANGED')
            if evidence.digest(fresh_context)!=value['program_id'] or value['context']['passages']!=fresh_context['passages']:raise ValueError('EKP_DERIVATIVE_CONTENT_CHANGED')
            if any(old['text']!=new['text'] or old['locator']!=new['locator'] for old,new in zip(value['passages'],refreshed)) or len(value['passages'])!=len(refreshed):raise ValueError('EKP_PASSAGES_CHANGED')
        except (ValueError,OSError,KeyError,TypeError):
            value={**value,'state':'STALE','stale_reason':'SOURCE_ADMISSION_EXTRACTION_OR_REVIEW_CHANGED'}
            db.execute('UPDATE ref_packets SET payload=? WHERE id=?',(encode(value),value['id']))
    if value['state']!='CURRENT':return {**{k:v for k,v in value.items() if k not in ('passages','facts','context')},'passages':None,'facts':None,'context':None}
    return value

def authorize_job(kernel,tool,opts,principal):
    if tool==pdf_service.JOB:return pdf_service.authorize_job(kernel,opts,principal)
    required={'references.index':{'namespace'},'references.render':{'namespace','id'},'references.export':{'namespace','destination','expected_generation'},'references.verify':{'path'}}[tool]
    optional={'references.render':{'item'},'references.export':{'project','readable'}}
    allowed=required|optional.get(tool,set())
    if not required.issubset(opts) or set(opts)-allowed:raise ValueError('REFERENCE_JOB_OPTIONS')
    if tool in ('references.export','references.verify') and 'approve' not in principal.scopes:raise ValueError('REFERENCE_VOLUME_REQUIRES_OWNER_APPROVAL')
    with kernel.db() as db:
        if 'namespace' in opts:intake.namespace(db,opts['namespace'],principal.identity,True)

def submit(kernel,tool,args,principal):
    return kernel.submit({'tool':tool,'references':{k:v for k,v in args.items() if k!='request_key'},'request_key':args.get('request_key',uuid.uuid4().hex),'timeout':600},principal)

def cancelled(kernel,job):
    if kernel.record('jobs',job['id']).get('cancel'):raise ValueError('REFERENCE_JOB_CANCELLED')

def build_index(kernel,job):
    opts=job['request_spec']['references'];owner=job['owner'];nsid=opts['namespace']
    with kernel.db() as db:
        ns=intake.namespace(db,nsid,owner,True);selected,unavailable=intake.catalog(db,ns,True);initial=ns['generation']
        if unavailable:raise ValueError('REFERENCE_ORIGINALS_UNAVAILABLE_BEFORE_INDEX')
        if len(selected)>1000:raise ValueError('REFERENCE_SOURCE_COUNT_LIMIT')
        sources=[]
        for item in selected:sources.append({'item':item['id'],'name':item['name'],'sha256':item['sha256'],'decision':item['decision_id']})
    extracted=[];gaps=[];total=0
    for row in sources:
        cancelled(kernel,job)
        try:
            result=extract.bounded(row['name'],intake.vault(ns).path(row['sha256']),row['sha256'])
        except (ValueError,OSError) as exc:
            gaps.append({'item':row['item'],'kind':activity.redact(exc)});continue
        total+=result.get('text_bytes',0)
        if total>32*1024*1024:raise ValueError('REFERENCE_NAMESPACE_TEXT_BUDGET')
        extracted.append((row,result));gaps.extend({'item':row['item'],**gap} for gap in result['gaps'])
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');ns=intake.namespace(db,nsid,owner,True)
        if ns['generation']!=initial:raise ValueError('REFERENCE_ADMISSIONS_CHANGED_DURING_INDEX')
        for row in sources:
            item=intake.load(db,'items',row['item']);intake.eligible(db,ns,item)
            if item['decision_id']!=row['decision']:raise ValueError('REFERENCE_DECISION_CHANGED_DURING_INDEX')
        cancelled(kernel,job)
        for table in ('ref_segments','ref_sources','ref_fts'):db.execute('DELETE FROM '+table+' WHERE ns=?',(nsid,))
        count=0
        for row,result in extracted:
            description={'source_sha256':row['sha256'],'decision':row['decision'],'extractor_hash':fingerprint(),'parser':result['parser'],'metadata':result['metadata'],'gaps':result['gaps'],'segments':len(result['segments'])}
            db.execute('INSERT INTO ref_sources VALUES(?,?,?)',(nsid,row['item'],encode(description)))
            for segment in result['segments']:
                db.execute('INSERT INTO ref_segments VALUES(?,?,?,?,?,?)',(nsid,row['item'],segment['id'],segment['text'],extract.search_text(segment['text']),encode(segment)))
                db.execute('INSERT INTO ref_fts VALUES(?,?,?,?)',(nsid,row['item'],segment['id'],extract.search_text(segment['text'])));count+=1
        version=bump(db,ns,{'created':time.time(),'sources':len(extracted),'passages':count,'gaps':gaps,'admission_generation':initial,'extractor_hash':fingerprint()})
        event(db,owner,'INDEX_COMMITTED',ns)
    return {'status':'INDEXED_WITH_GAPS' if gaps else 'INDEXED','sources':len(extracted),'passages':count,'gaps':gaps,'generation':version,'model_calls':0}

def render(kernel,job):
    opts=job['request_spec']['references']
    with kernel.db() as db:
        ns=intake.namespace(db,opts['namespace'],job['owner'],True);citation=require_current(resolve(db,ns,opts['id'],opts.get('item'),historical=True));item=intake.load(db,'items',citation['item']);original,row,raw=current(db,ns,item['id'])
    if citation['locator']['kind']!='pdf_page':raise ValueError('REFERENCE_RENDER_REQUIRES_PDF_PAGE')
    executable=shutil.which('pdftoppm')
    if not executable:raise ValueError('POPPLER_NOT_AVAILABLE_OR_QUALIFIED_ON_THIS_HOST')
    executable=Path(executable).resolve();version=subprocess.run([str(executable),'-v'],capture_output=True,text=True,timeout=5)
    if version.returncode:raise ValueError('PDF_RENDER_TOOL_VERSION_FAILED')
    with tempfile.TemporaryDirectory(prefix='reference-page-') as tmp:
        folder=Path(tmp);pdf=folder/'original.pdf';pdf.write_bytes(raw);page=citation['locator']['page_index']+1
        result=subprocess.run([str(executable),'-f',str(page),'-l',str(page),'-singlefile','-scale-to','1500','-png',str(pdf),str(folder/'page')],capture_output=True,timeout=20)
        image=folder/'page.png'
        if result.returncode or not image.is_file() or image.stat().st_size>12*1024*1024:raise ValueError('PDF_PAGE_RENDER_FAILED_OR_LIMIT')
        image_raw=image.read_bytes()
    with kernel.db() as db:
        ns=intake.namespace(db,opts['namespace'],job['owner'],True);require_current(resolve(db,ns,citation['id'],citation['item'],historical=True));event(db,job['owner'],'ORIGINAL_PAGE_RENDERED',ns)
    target=kernel.root/'build/references/runs'/job['id']/'page.png';records.atomic(target,image_raw)
    return {'status':'RENDERED','citation':citation['id'],'source_sha256':citation['source_sha256'],'page_index':page-1,'image':'build/references/runs/'+job['id']+'/page.png',
      'image_sha256':hashlib.sha256(image_raw).hexdigest(),'tool':{'name':'pdftoppm','sha256':records.sha(executable),'version':(version.stdout+version.stderr).splitlines()[0][:150]},'image_is_derivative':True}

def safe_new_destination(kernel,ns,destination,db,allow_existing=False):
    path=Path(destination).expanduser().absolute()
    if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('REFERENCE_EXPORT_LINKED_PATH')
    path=path.resolve()
    from .session import config_dir
    from .files_service import root as files_root, EXPORTS
    egress=(files_root(kernel)/EXPORTS).resolve()
    protected=(path.is_relative_to(kernel.root) and not path.is_relative_to(egress)
               or path.is_relative_to(config_dir()) or path.is_relative_to(locations.program(kernel.root)))
    if (path.exists() and not allow_existing) or path.suffix.lower()!='.zip' or protected:
        raise ValueError('Choose a new ZIP in Egress or an external destination')
    for row in db.execute('SELECT payload FROM intake_batches WHERE ns=?',(ns['id'],)):
        src=json.loads(row[0]).get('source',{});origin=Path(src.get('origin','/nonexistent')).resolve()
        if path==origin or src.get('origin_kind')=='folder' and path.is_relative_to(origin):raise ValueError('REFERENCE_EXPORT_CANNOT_WRITE_IN_ORIGINAL_SOURCE')
    return path

def write_volume(raw,destination,check=lambda:None):
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.arc-reference-',dir=destination.parent)
    temp=Path(tmp)
    try:
        with os.fdopen(fd,'wb') as output:
            output.write(raw);output.flush();os.fsync(output.fileno())
        if records.sha(temp)!=hashlib.sha256(raw).hexdigest():raise ValueError('REFERENCE_EXPORT_READBACK_FAILED')
        check()
        os.link(temp,destination)
    finally:
        temp.unlink(missing_ok=True)

def export_volume(kernel,job):
    opts=job['request_spec']['references']
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');ns=intake.namespace(db,opts['namespace'],job['owner'],True);generation,description=meta(db,ns['id'])
        if generation!=opts['expected_generation']:raise ValueError('REFERENCE_EXPORT_GENERATION_CHANGED')
        if description.get('admission_generation')!=ns['generation']:raise ValueError('REFERENCE_ADMISSIONS_CHANGED_REBUILD_BEFORE_EXPORT')
        destination=safe_new_destination(kernel,ns,opts['destination'],db);sources=[];segments=[];objects={};cache={};size=0
        staged=destination.is_relative_to(kernel.root)
        project=None
        if opts.get('project'):
            from . import project_desk
            from .engineering_kernel import Principal
            value=project_desk.read(db,'project',opts['project'],Principal(job['owner']))
            link=next((row for row in value['links'] if row['role']=='SOURCE' and
                       (row.get('source') or {}).get('address')=='collection:'+ns['id']),None)
            if link is None:raise ValueError('PROJECT_COLLECTION_LINK_UNAVAILABLE')
            project={'id':value['id'],'title':value['title'],'revision':value['revision'],'link':link['id'],'role':'SOURCE'}
        for item_id, in db.execute('SELECT item FROM ref_sources WHERE ns=? ORDER BY item',(ns['id'],)):
            cancelled(kernel,job);item,index,raw=current(db,ns,item_id,cache);size+=len(raw)
            if size>intake_files.MAX_BUNDLE:raise ValueError('REFERENCE_VOLUME_BUDGET')
            member=records.object_name(item['sha256'])
            if opts.get('readable'):
                member=f"Sources/{len(sources)+1:03d}/{item['name']}"
                records.safe_name(member)
            objects[member]=raw
            sources.append({'item':item_id,'name':item['name'],'sha256':item['sha256'],'bytes':len(raw),
                'decision':item['decision_id'],'metadata':index['metadata'],'parser':index['parser'],
                **({'archive_path':member} if opts.get('readable') else {})})
            for r in db.execute('SELECT id FROM ref_segments WHERE ns=? AND item=? ORDER BY id',(ns['id'],item_id)):
                verified=require_current(resolve(db,ns,r[0],item_id,cache,True))
                segments.append({'item':item_id,**{k:verified[k] for k in ('id','locator_id','locator','text','text_sha256')}})
        if not sources:raise ValueError('REFERENCE_VOLUME_EMPTY')
        public_facts=[{k:v for k,v in f.items() if k not in ('actor','reason')} for f in facts(db,ns) if f['applicability']=='CURRENT_REFERENCE']
        public_links=[{k:v for k,v in f.items() if k not in ('actor','reason')} for f in links(db,ns) if f['applicability']=='CURRENT_REFERENCE']
        with tempfile.TemporaryDirectory(prefix='reference-edition-') as tmp:
            folder=Path(tmp);working=sqlite3.connect(folder/'working.sqlite');working.execute('CREATE TABLE passages(id TEXT,item TEXT,locator_id TEXT,locator TEXT,text TEXT,text_sha256 TEXT)')
            working.executemany('INSERT INTO passages VALUES(?,?,?,?,?,?)',[(s['id'],s['item'],s['locator_id'],encode(s['locator']),s['text'],s['text_sha256']) for s in segments]);working.commit()
            target=sqlite3.connect(folder/'INDEX.sqlite');working.backup(target);assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok';target.close();working.close();objects['INDEX.sqlite']=(folder/'INDEX.sqlite').read_bytes()
        annotations=pdf_service.export_annotations(db,ns,[s['item'] for s in sources],job['owner'])
        included={src['item'] for src in sources}
        omitted=[{'name':name,'item':item,'reason':'No current indexed original in this export.'}
                 for name,item in db.execute('SELECT name,item FROM intake_catalog WHERE ns=? ORDER BY name',(ns['id'],))
                 if item not in included]
        catalog={'schema':'arc.reference-volume/1','edition':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'generation':generation,'sources':sources,'facts':public_facts,'links':public_links,'pdf_annotations':annotations,
           'extraction_rule_hash':fingerprint(),'namespace_rights':'OWNER_DIRECTED_LOCAL_REFERENCE_EDITION_SHARING_NOT_ASSUMED','translation':'NOT_PROVIDED','physical_hardware':'NOT_QUALIFIED'}
        if opts.get('readable') or project:
            catalog.update(collection={'id':ns['id'],'name':ns['name']},project=project,omitted=omitted)
            lines=[ns['name'],f'Reference index generation {generation}',f'{len(sources)} original sources']
            if project:lines.extend([f"Project {project['title']} · revision {project['revision']}", 'Relationship · project source collection'])
            lines.extend(['','Original files'])
            for src in sources:
                lines.append(f"{src['name']}  →  {src.get('archive_path') or records.object_name(src['sha256'])}")
            lines.extend(['','Source identities, reviewed facts, links and PDF annotations are in CATALOG.json.'])
            if omitted:lines.extend(['','Omitted material',*(f"{row['name']} · {row['reason']}" for row in omitted)])
            objects['COLLECTION.txt']=('\n'.join(lines)+'\n').encode()
        objects['CATALOG.json']=records.canonical(catalog);objects['README.txt']=b'ARC reference volume, version 1. Original objects use content hashes. INDEX.sqlite contains rebuildable exact locators and text derivatives. Use a compatible Ledger retrieval adapter; an arbitrary LLM cannot read this archive automatically. Source admission does not qualify hardware. Sharing rights are not inferred.\n'
        if sum(len(v) for v in objects.values())>intake_files.MAX_BUNDLE-1024*1024:raise ValueError('REFERENCE_VOLUME_EXPANDED_BUDGET')
        manifest={'schema':'arc.reference-volume-manifest/1','files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in objects.items()}}
        objects['MANIFEST.json']=records.canonical(manifest);stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,raw in sorted(objects.items()):archive.writestr('Reference_Volume/'+name,raw)
        raw=stream.getvalue()
        if len(raw)>min(records.BUDGET,intake_files.MAX_BUNDLE):raise ValueError('REFERENCE_VOLUME_MEDIA_BUDGET')
        artifact=f"build/references/runs/{job['id']}/volume.zip"
        # A workspace export goes through the existing job evidence boundary.
        # Publishing into Files happens after the worker has completed.
        write_volume(raw,kernel.root/artifact if staged else destination,lambda:cancelled(kernel,job))
        event(db,job['owner'],'REFERENCE_VOLUME_PREPARED' if staged else 'REFERENCE_VOLUME_EXPORTED',ns)
    return {'status':'PREPARED_EXPORT' if staged else 'EXPORTED','artifact':artifact if staged else None,
            'sources':len(sources),'passages':len(segments),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
            'physical_disc_verified':False,'iso_authoring':'NOT_PERFORMED'}

def publish_volume(kernel,ident,principal):
    job=kernel.record('jobs',ident);kernel.require_owner(job,principal)
    if job['tool']!='references.export' or job['state']!='Completed' or not job.get('evidence'):
        raise ValueError('A completed reference export is required')
    evidence=kernel.record('evidence',job['evidence'])
    receipt=evidence.get('diagnostics') or {}
    if evidence.get('job')!=ident or receipt.get('status') not in ('PREPARED_EXPORT','EXPORTED'):
        raise ValueError('Reference export evidence is unavailable')
    opts=job['request_spec']['references']
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        ns=intake.namespace(db,opts['namespace'],principal.identity,True)
        destination=safe_new_destination(kernel,ns,opts['destination'],db,allow_existing=True)
        if destination.is_file() and records.sha(destination)==receipt['sha256']:
            return {'status':'EXPORTED','path':str(destination),'sha256':receipt['sha256'],'replayed':True}
        artifact=f"build/references/runs/{ident}/volume.zip"
        if receipt.get('artifact')!=artifact or destination.exists():
            raise ValueError('The export destination or prepared volume changed')
        raw=intake_files.read_stable(kernel.safe(artifact),intake_files.MAX_BUNDLE)
        if len(raw)!=receipt['bytes'] or hashlib.sha256(raw).hexdigest()!=receipt['sha256']:
            raise ValueError('The prepared reference volume changed')
        write_volume(raw,destination)
        event(db,principal.identity,'REFERENCE_VOLUME_EXPORTED',ns)
    return {'status':'EXPORTED','path':str(destination),'sha256':receipt['sha256'],'replayed':False}

def verify_volume(kernel,job):
    path=Path(job['request_spec']['references']['path']);raw=intake_files.read_stable(path,intake_files.MAX_BUNDLE)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members=intake_files.checked_zip(archive);names={m.filename for m in members};prefix='Reference_Volume/'
        manifest=records.strict(archive.read(prefix+'MANIFEST.json'))
        if manifest.get('schema')!='arc.reference-volume-manifest/1' or names!={prefix+n for n in manifest['files']}|{prefix+'MANIFEST.json'}:raise ValueError('REFERENCE_VOLUME_MANIFEST_MEMBERS')
        for name,row in manifest['files'].items():
            records.safe_name(name);data=archive.read(prefix+name)
            if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('REFERENCE_VOLUME_MEMBER_CHANGED')
        catalog=records.strict(archive.read(prefix+'CATALOG.json'))
        if catalog.get('schema')!='arc.reference-volume/1':raise ValueError('REFERENCE_VOLUME_SCHEMA')
        annotation_count=pdf_service.validate_export(catalog.get('pdf_annotations',[]),catalog['sources'])
        originals={}
        for src in catalog['sources']:
            cancelled(kernel,job);name=src.get('archive_path',records.object_name(src['sha256']))
            if 'archive_path' in src and (not isinstance(name,str) or not name.startswith('Sources/')):
                raise ValueError('REFERENCE_VOLUME_SOURCE_PATH')
            records.safe_name(name)
            if name not in manifest['files']:raise ValueError('REFERENCE_VOLUME_ORIGINAL_MISSING')
            original=archive.read(prefix+name)
            if hashlib.sha256(original).hexdigest()!=src['sha256'] or len(original)!=src['bytes']:raise ValueError('REFERENCE_VOLUME_CONTENT_ADDRESS_CHANGED')
            if src['item'] in originals:raise ValueError('REFERENCE_VOLUME_DUPLICATE_SOURCE_ID')
            originals[src['item']]=original
        with tempfile.TemporaryDirectory(prefix='reference-volume-verify-') as tmp:
            projections={};same_rules=catalog.get('extraction_rule_hash')==fingerprint()
            if same_rules:
                for src in catalog['sources']:
                    cancelled(kernel,job);source_path=Path(tmp)/'original';source_path.write_bytes(originals[src['item']])
                    projections[src['item']]={v['id']:v for v in extract.bounded(src['name'],source_path,src['sha256'])['segments']}
            index=Path(tmp)/'INDEX.sqlite';index.write_bytes(archive.read(prefix+'INDEX.sqlite'));db=sqlite3.connect(index.as_uri()+'?mode=ro&immutable=1',uri=True)
            try:
                db.execute('PRAGMA trusted_schema=OFF');db.execute('PRAGMA query_only=ON')
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('REFERENCE_VOLUME_SQLITE_INTEGRITY')
                sources={v['item']:v for v in catalog['sources']};count=0
                for ident,item,locator_id,locator,text,text_sha in db.execute('SELECT id,item,locator_id,locator,text,text_sha256 FROM passages'):
                    loc=records.strict(locator)
                    if item not in sources or hashlib.sha256(text.encode()).hexdigest()!=text_sha or extract.digest({'source_sha256':sources[item]['sha256'],'locator':loc})!=locator_id or extract.digest({'locator_id':locator_id,'text_sha256':text_sha})!=ident:raise ValueError('REFERENCE_VOLUME_LOCATOR_INTEGRITY')
                    if same_rules:
                        actual=projections[item].get(ident)
                        if actual is None or actual['text']!=text or actual['locator']!=loc:raise ValueError('REFERENCE_VOLUME_DERIVATIVE_DOES_NOT_MATCH_ORIGINAL')
                    count+=1
            finally:db.close()
    return {'status':'VERIFIED' if same_rules else 'HASH_VERIFIED_DERIVATIVE_REVIEW_REQUIRED','sources':len(catalog['sources']),'passages':count,'sha256':hashlib.sha256(raw).hexdigest(),
      'derivatives_reextracted_from_originals':same_rules,'pdf_annotations':annotation_count,'imports_performed':0,'physical_disc_verified':False}

def dispatch(kernel,op,args,principal):
    if op in pdf_service.FIELDS:return pdf_service.dispatch(kernel,op,args,principal)
    actor=principal.identity
    if op=='references.volume.publish':return publish_volume(kernel,args['job'],principal)
    if op in ('references.index','references.render','references.volume.export','references.volume.verify'):
        tool={'references.index':'references.index','references.render':'references.render','references.volume.export':'references.export','references.volume.verify':'references.verify'}[op]
        return submit(kernel,tool,args,principal)
    if op=='references.native':return native(kernel,principal,args['component'])
    if op=='references.render.result':
        job=kernel.record('jobs',args['job']);kernel.require_owner(job,principal)
        if job['tool']!='references.render':raise ValueError('REFERENCE_RENDER_JOB_REQUIRED')
        path=kernel.root/'build/references/runs'/job['id']/'result.json'
        result=record_io.strict_json(path.read_bytes()) if path.is_file() else None;opts=job['request_spec']['references']
        with kernel.db() as db:
            ns=intake.namespace(db,opts['namespace'],actor)
            if result and result.get('image'):
                citation=resolve(db,ns,opts['id'],opts.get('item'),historical=True)
                if citation['state']!='CURRENT':result={**{k:v for k,v in result.items() if k!='image'},'status':'LOCATED_BUT_UNAVAILABLE','gaps':citation.get('gaps',[])}
        return {'state':job['state'],'result':result}
    with kernel.db() as db:
        if op in ('references.fact.add','references.link.add','references.packet.create'):db.execute('BEGIN IMMEDIATE')
        if op in ('references.packet','references.answer.validate'):
            ident=args.get('id',args.get('packet'));row=db.execute('SELECT ns,payload FROM ref_packets WHERE id=?',(ident,)).fetchone()
            if not row:raise ValueError('REFERENCE_PACKET_NOT_FOUND')
            ns=intake.namespace(db,row[0],actor);value=packet(db,ns,json.loads(row[1]))
            if op=='references.packet':return value
            if value['state']!='CURRENT':raise ValueError('REFERENCE_PACKET_STALE')
            return evidence.validate_answer(args['answer'],value)
        ns=intake.namespace(db,args['namespace'],actor,op in ('references.original','references.fact.add','references.link.add','references.packet.create'))
        if op=='references.collection':
            generation,index=meta(db,ns['id'])
            count=db.execute('SELECT COUNT(*) FROM intake_catalog WHERE ns=?',(ns['id'],)).fetchone()[0]
            return {'id':ns['id'],'name':ns['name'],'admission_generation':ns['generation'],
                    'index_generation':generation,'admitted_sources':count,
                    'index_current':bool(generation and index.get('admission_generation')==ns['generation'])}
        if op=='references.status':
            generation,data=meta(db,ns['id']);eligible_sources=0;unavailable=[];cache={}
            for item, in db.execute('SELECT item FROM ref_sources WHERE ns=?',(ns['id'],)):
                try:current(db,ns,item,cache);eligible_sources+=1
                except (ValueError,OSError) as exc:unavailable.append({'item':item,'reason':activity.redact(exc)})
            return {'schema':'arc.references/1','generation':generation,'index':data,'current_sources':eligible_sources,'unavailable':unavailable,
              'originals_required':True,'translation':'NOT_PROVIDED','physical_qualification':False,'search':'SQLITE_FTS5_WITH_CJK_SUBSTRING_FALLBACK'}
        if op=='references.sources':
            rows=[]
            for item,payload in db.execute('SELECT item,payload FROM ref_sources WHERE ns=?',(ns['id'],)):
                description=json.loads(payload);source_item=intake.load(db,'items',item)
                try:current(db,ns,item);state='CURRENT'
                except (ValueError,OSError):state='LOCATED_BUT_UNAVAILABLE'
                rows.append({'item':item,'name':source_item['name'],'state':state,**description})
            return {'sources':rows}
        if op=='references.passages':
            # Metadata remains locatable with an original absent. Excerpts require resolve.
            item=intake.load(db,'items',args['item'])
            if item['namespace']!=ns['id']:raise ValueError('REFERENCE_NAMESPACE_MISMATCH')
            rows=[json.loads(r[0]) for r in db.execute('SELECT payload FROM ref_segments WHERE ns=? AND item=? ORDER BY rowid LIMIT ? OFFSET ?',
              (ns['id'],item['id'],args.get('limit',50),args.get('offset',0)))];total=db.execute('SELECT count(*) FROM ref_segments WHERE ns=? AND item=?',(ns['id'],item['id'])).fetchone()[0]
            return {'total':total,'passages':[{k:v for k,v in row.items() if k!='text'} for row in rows]}
        if op in ('references.resolve','references.original'):
            value=resolve(db,ns,args['id'],args.get('item'),historical=args.get('include_historical',False) or op=='references.original')
            if op=='references.original':
                require_current(value);item=intake.load(db,'items',value['item']);value={**value,'path':str(intake.vault(ns).path(item['sha256'])),'original_suffix':Path(item['name']).suffix}
            return value
        if op=='references.search':
            query=extract.search_text(args['query']);terms=re.findall(r'[a-z0-9_]+|[\u3400-\u9fff]+|[^\W_]',query,re.UNICODE)[:20]
            if not terms:return {'hits':[],'gaps':['QUERY_HAS_NO_SEARCH_TERMS']}
            sql=db.execute("SELECT sql FROM sqlite_master WHERE name='ref_fts'").fetchone()[0];candidates=[]
            if re.fullmatch(r'[0-9a-f]{64}',query):
                candidates=db.execute('SELECT s.item,s.id FROM ref_segments s JOIN intake_catalog c ON c.item=s.item AND c.ns=s.ns WHERE s.ns=? AND s.id=? ORDER BY s.rowid LIMIT 120',(ns['id'],query)).fetchall()
            if 'fts5' in sql.lower():
                match=' OR '.join('"'+t.replace('"','""')+'"' for t in terms)
                candidates+=db.execute('SELECT ref_fts.item,ref_fts.id FROM ref_fts JOIN intake_catalog c ON c.item=ref_fts.item AND c.ns=ref_fts.ns WHERE ref_fts.ns=? AND ref_fts MATCH ? ORDER BY bm25(ref_fts) LIMIT 120',(ns['id'],match)).fetchall()
            if not candidates or re.search('[\u3400-\u9fff]',query):
                candidates+=db.execute('SELECT s.item,s.id FROM ref_segments s JOIN intake_catalog c ON c.item=s.item AND c.ns=s.ns WHERE s.ns=? AND '+ ' AND '.join('instr(s.norm,?)>0' for _ in terms)+' ORDER BY s.rowid LIMIT 120',[ns['id'],*terms]).fetchall()
            hits=[];missing=[];cache={};seen=set()
            for item,ident in candidates:
                if (item,ident) in seen:continue
                seen.add((item,ident));value=resolve(db,ns,ident,item,cache,args.get('include_historical',False))
                if value['state']=='CURRENT':hits.append(value)
                else:missing.append({'id':ident,'state':value['state'],'gaps':value.get('gaps',[])})
                if len(hits)>=args.get('limit',20):break
            return {'hits':hits,'unavailable':missing,'candidate_limit':120,'model_calls':0,'ranking':'LEXICAL_FTS_PLUS_CJK_EXACT_SUBSTRING','semantic_embeddings':'NOT_ENABLED_LEXICAL_BASELINE'}
        if op=='references.fact.add':
            conditions(args['conditions'])
            citation=require_current(resolve(db,ns,args['id'],historical=True));quantity=evidence.quantity(args['value'],args['unit'])
            if args['quote'] not in citation['text']:raise ValueError('FACT_QUOTE_NOT_IN_VERIFIED_PASSAGE')
            if not quantity_in_quote(quantity,args['quote']):raise ValueError('FACT_VALUE_AND_UNIT_NOT_PRESENT_IN_QUOTE')
            fact={k:args[k] for k in ('subject','property','variant','conditions','polarity','role','quote','reason')}
            fact.update(id=uuid.uuid4().hex,namespace=ns['id'],item=citation['item'],passage=citation['id'],source_sha256=citation['source_sha256'],quantity=quantity,
              decision=citation['decision'],extractor_hash=fingerprint(),
              actor=actor,review='OWNER_REVIEWED_SOURCE_RECORD',subject_binding='OWNER_DECLARED_NOT_FITTED_PART_VALIDATION',created=time.time(),support=evidence.support(args['polarity']=='SUPPORT',args['polarity']=='REFUTE'))
            db.execute('INSERT INTO ref_facts VALUES(?,?,?)',(fact['id'],ns['id'],encode(fact)));bump(db,ns);event(db,actor,'SOURCE_FACT_REVIEWED',ns);return fact
        if op=='references.facts':return {'facts':facts(db,ns,args.get('subject'))}
        if op=='references.question':return evidence.inquiry(args['subject'],args['property'],args['variant'],conditions(args['conditions']),facts(db,ns,args['subject']))
        if op=='references.link.add':
            citation=require_current(resolve(db,ns,args['id'],historical=True));link={k:args[k] for k in ('subject','relation','basis','reason')}
            if args['relation']=='JOB_RESULT_FOR':
                if not args.get('job'):raise ValueError('REFERENCE_JOB_ID_REQUIRED')
                job=kernel.record('jobs',args['job']);kernel.require_owner(job,principal)
                if job['state']!='Completed':raise ValueError('REFERENCE_JOB_HAS_NO_COMPLETED_RESULT')
                link.update(job_id=job['id'],job_revision=job.get('revision'),job_class='REGISTERED_HOST_JOB_NOT_PHYSICAL_QUALIFICATION')
            elif 'job' in args:raise ValueError('REFERENCE_JOB_RELATION_REQUIRED')
            link.update(id=uuid.uuid4().hex,namespace=ns['id'],item=citation['item'],passage=citation['id'],source_sha256=citation['source_sha256'],actor=actor,created=time.time(),decision=citation['decision'],extractor_hash=fingerprint())
            db.execute('INSERT INTO ref_links VALUES(?,?,?)',(link['id'],ns['id'],encode(link)));bump(db,ns);event(db,actor,'SOURCE_RELATION_REVIEWED',ns);return link
        if op=='references.atlas':
            return {'schema':'arc.evidence-atlas/1','subject':args['subject'],'facts':facts(db,ns,args['subject']),'links':links(db,ns,args['subject']),
              'native_project':native(kernel,principal,args['subject']),'source_scope':ns['policy']['scope'],'physical_qualification':'NOT_ESTABLISHED','model_inferences':'NOT_PROMOTED'}
        if op=='references.impact':
            item=intake.load(db,'items',args['item'])
            if item['namespace']!=ns['id']:raise ValueError('REFERENCE_NAMESPACE_MISMATCH')
            affected={item['id']};dependencies=set()
            for _ in range(128):
                added=set()
                for row in db.execute('SELECT i.payload FROM intake_catalog c JOIN intake_items i ON i.id=c.item WHERE c.ns=?',(ns['id'],)):
                    value=json.loads(row[0]);decision=intake.load(db,'decisions',value['decision_id'])
                    for dep in decision['assessment']['dependencies']:
                        if dep['item'] in affected:added.add(value['id']);dependencies.add((value['id'],dep['item']))
                if added<=affected:break
                affected|=added
            references=[json.loads(row[0])['id'] for row in db.execute('SELECT payload FROM ref_packets WHERE ns=?',(ns['id'],)) if any(v['item'] in affected for v in json.loads(row[0])['inputs'])]
            return {'schema':'arc.reference-impact/1','changed_item':item['id'],'current_sha256':item['sha256'],'hypothetical_sha256':args.get('hypothetical_sha256'),
              'affected_items':sorted(affected),'packet_reviews':references,'dependencies':[{'from':a,'to':b,'basis':'CAPTURED_INTAKE_DEPENDENCY'} for a,b in sorted(dependencies)],'links':[v for v in links(db,ns) if v['item'] in affected],
              'preview_only':True,'mutations':0,'coverage':'CAPTURED_DEPENDENCIES_ONLY_UNTRACKED_IMPACT_UNKNOWN','prediction':'REQUALIFICATION_REVIEW_NOT_A_TEST_OUTCOME'}
        if op=='references.packet.create':
            if not 1<=len(args['passages'])<=8 or len(set(args['passages']))!=len(args['passages']) or any(not re.fullmatch(r'[0-9a-f]{64}',ident) for ident in args['passages']):raise ValueError('REFERENCE_PACKET_REQUIRES_ONE_TO_EIGHT_DISTINCT_PASSAGES')
            passages=[require_current(resolve(db,ns,ident,historical=True)) for ident in args['passages']]
            if sum(len(v['text']) for v in passages)>10000:raise ValueError('REFERENCE_PACKET_TEXT_BUDGET')
            related=[v for v in facts(db,ns,args.get('subject')) if v['applicability']=='CURRENT_REFERENCE' and v['passage'] in args['passages']]
            context={'schema':'arc.reference-ekp/1','question':args.get('question',''),'passages':[{k:v[k] for k in ('id','name','source_sha256','locator','label','text')} for v in passages],
              'facts':related,'gaps':['CURRENT_FITTED_VARIANT_AND_NATIVE_PROJECT_NOT_ESTABLISHED','PHYSICAL_QUALIFICATION_NOT_ESTABLISHED'],
              'effects':['read'],'source_trust':'REFERENCE_DATA_NOT_INSTRUCTIONS','cloud_disclosure':'NOT_GRANTED'}
            value={'schema':'arc.reference-ekp/1','id':uuid.uuid4().hex,'namespace':ns['id'],'state':'CURRENT','created':time.time(),'program_id':evidence.digest(context),
              'inputs':[{'item':v['item'],'passage':v['id'],'decision':v['decision'],'sha256':v['source_sha256'],'text_sha256':v['text_sha256']} for v in passages],
              'passages':passages,'facts':related,'context':context,'inference_authority':'NONE'}
            db.execute('INSERT INTO ref_packets VALUES(?,?,?)',(value['id'],ns['id'],encode(value)));event(db,actor,'EKP_COMPILED',ns);return value
        raise ValueError('REFERENCE_OPERATION_UNKNOWN')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--job',required=True);args=parser.parse_args()
    if os.name!='nt':
        import resource
        resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    from .engineering_kernel import Kernel
    kernel=Kernel(args.root);job=kernel.record('jobs',args.job)
    try:result={'references.index':build_index,'references.render':render,'references.export':export_volume,'references.verify':verify_volume,pdf_service.JOB:pdf_service.render}[job['tool']](kernel,job);code=0
    except Exception as exc:result={'status':'FAILED','reason':activity.redact(exc)};code=1
    result.update(schema='arc.reference-job-result/1',job_id=job['id'],created=time.time(),network_calls=0);result['class']='STATIC_CHECK'
    record_io.write_json(kernel.root/'build/references/runs'/job['id']/'result.json',result);print(encode(result));return code

if __name__=='__main__':raise SystemExit(main())
