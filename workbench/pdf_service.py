"""P17 page/citation/annotation adapters over existing intake and Kernel jobs."""
from __future__ import annotations
import base64, math, re, time, uuid
from pathlib import Path
from sdk.cli.arc1cli import pdf_evidence as pdf,record_store as records
from . import intake_service as intake,record_io,activity

ID=intake.ID;SHA=intake.SHA
INDEX={'type':'integer','minimum':0,'maximum':511}
REGION={'type':'array','items':{'type':'number','minimum':0,'maximum':1},'minItems':4,'maxItems':4}
SOURCE={'namespace':ID,'item':ID,'source_sha256':SHA}
ANNOTATION={**SOURCE,'page_index':INDEX,'rect':REGION,'kind':{'type':'string','enum':['NOTE','QUESTION','TABLE_CONTEXT','FIGURE_CONTEXT','PRINTED_PAGE']},
 'text':{'type':'string','minLength':1,'maxLength':8000},'printed_label':{'type':'string','maxLength':80},
 'id':ID,'expected_version':{'type':'integer','minimum':0},'writer':ID}
FIELDS={
 'references.pdf.citation.resolve':({'citation':{'type':'object','additionalProperties':False,'properties':{'schema':{'type':'string','enum':['arc.pdf-citation/1']},**SOURCE,'page_index':INDEX,'rect':REGION},'required':['schema',*SOURCE,'page_index','rect']}},['citation']),
 'references.pdf.info':({'namespace':ID,'item':ID,'source_sha256':SHA},['namespace','item']),
 'references.pdf.page':({**SOURCE,'page_index':INDEX,'ocr':{'type':'boolean'},'language':{'type':'string','enum':list(pdf.LANGUAGES)},'request_key':intake.TEXT},[*SOURCE,'page_index']),
 'references.pdf.result':({'job':ID},['job']),
 'references.pdf.annotations':({'namespace':ID,'item':ID},['namespace','item']),
 'references.pdf.annotation.save':(ANNOTATION,[*SOURCE,'page_index','rect','kind','text','expected_version']),
 'references.pdf.annotation.remove':({'namespace':ID,'id':ID,'expected_version':{'type':'integer','minimum':1}},['namespace','id','expected_version']),
 'references.pdf.draft.put':({**ANNOTATION,'text':{'type':'string','maxLength':8000}},[*SOURCE,'page_index','rect','kind','text','expected_version','writer']),
 'references.pdf.draft.get':({'namespace':ID,'item':ID,'source_sha256':SHA,'page_index':INDEX},[*SOURCE,'page_index'])}
SCOPES={op:'execute' if op in ('references.pdf.page','references.pdf.annotation.save','references.pdf.annotation.remove','references.pdf.draft.put') else 'read' for op in FIELDS}
JOB='references.page'
JOB_PROPERTIES={'source_sha256':SHA,'page_index':INDEX,'ocr':{'type':'boolean'},'language':{'type':'string','enum':list(pdf.LANGUAGES)}}

def ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS ref_pdf_annotations(id TEXT PRIMARY KEY,ns TEXT,owner TEXT,item TEXT,version INTEGER,payload TEXT,sha256 TEXT)')
    db.execute('CREATE INDEX IF NOT EXISTS ref_pdf_annotation_owner ON ref_pdf_annotations(ns,owner,item)')
    db.execute('CREATE TABLE IF NOT EXISTS ref_pdf_drafts(ns TEXT,owner TEXT,item TEXT,page_id TEXT,writer TEXT,payload TEXT,sha256 TEXT,PRIMARY KEY(ns,owner,item,page_id,writer))')

def original(db,args,actor,owner=False):
    ns=intake.namespace(db,args['namespace'],actor,owner);item=intake.load(db,'items',args['item'])
    if item['namespace']!=ns['id'] or Path(item['name']).suffix.lower()!='.pdf':raise ValueError('PDF_SOURCE_NAMESPACE_OR_TYPE_MISMATCH')
    raw,decision=intake.eligible(db,ns,item)
    if args.get('source_sha256') and item['sha256']!=args['source_sha256']:raise ValueError('PDF_ORIGINAL_CHANGED')
    return ns,item,raw,decision

def info(kernel,args,principal):
    with kernel.db() as db:ns,item,raw,decision=original(db,args,principal.identity)
    try:result=pdf.bounded('inspect',intake.vault(ns).path(item['sha256']),item['sha256'])
    except ValueError as exc:return {'state':'UNAVAILABLE','item':item['id'],'name':item['name'],'source_sha256':item['sha256'],'gaps':[str(exc)],'pages':[]}
    with kernel.db() as db:original(db,{**args,'source_sha256':item['sha256']},principal.identity)
    return {**result,'state':'CURRENT','item':item['id'],'name':item['name'],'decision':decision['id']}

def authorize_job(kernel,opts,principal):
    required={*SOURCE,'page_index'};allowed=required|{'ocr','language'}
    if not required<=set(opts) or set(opts)-allowed:raise ValueError('PDF_JOB_OPTIONS')
    with kernel.db() as db:original(db,opts,principal.identity,True)

def render(kernel,job):
    opts=job['request_spec']['references'];actor=job['owner']
    with kernel.db() as db:ns,item,raw,decision=original(db,opts,actor,True)
    if kernel.record('jobs',job['id']).get('cancel'):raise ValueError('PDF_JOB_CANCELLED')
    result=pdf.bounded('page',intake.vault(ns).path(item['sha256']),item['sha256'],opts['page_index'],opts.get('ocr',False),opts.get('language','eng'))
    image=base64.b64decode(result.pop('image_b64'),validate=True)
    if len(image)>pdf.MAX_IMAGE or pdf.sha(image)!=result['image_sha256']:raise ValueError('PDF_RENDER_DERIVATIVE_CHANGED')
    with kernel.db() as db:
        original(db,opts,actor,True)
        if kernel.record('jobs',job['id']).get('cancel'):raise ValueError('PDF_JOB_CANCELLED')
        target='build/references/runs/'+job['id']+'/page.png';records.atomic(kernel.root/target,image)
        activity.append(db,activity.make_event(actor,'references.pdf.page','PAGE_RENDERED'))
    return {**result,'status':'RENDERED','namespace':ns['id'],'item':item['id'],'name':item['name'],'decision':decision['id'],'image':target}

def result(kernel,args,principal):
    job=kernel.record('jobs',args['job']);kernel.require_owner(job,principal)
    if job['tool']!=JOB:raise ValueError('PDF_PAGE_JOB_REQUIRED')
    path=kernel.root/'build/references/runs'/job['id']/'result.json'
    value=record_io.strict_json(path.read_bytes()) if path.is_file() else None
    if value and value.get('status')=='RENDERED':
        try:
            if job['state']!='Completed' or not job.get('evidence'):raise ValueError('PDF_RESULT_DOES_NOT_MATCH_JOB_EVIDENCE')
            evidence=kernel.record('evidence',job['evidence'])
            if evidence.get('job')!=job['id'] or evidence.get('diagnostics')!=value:raise ValueError('PDF_RESULT_DOES_NOT_MATCH_JOB_EVIDENCE')
            with kernel.db() as db:original(db,job['request_spec']['references'],principal.identity)
            image=kernel.safe(value['image'])
            if records.sha(image)!=value['image_sha256']:raise ValueError('PDF_RENDER_DERIVATIVE_CHANGED')
        except (ValueError,OSError):
            value={'status':'LOCATED_BUT_UNAVAILABLE','source_sha256':value['source_sha256'],'page':value['page'],
                'native':None,'ocr':None,'image':None,'gaps':['ORIGINAL_ADMISSION_OR_DERIVATIVE_CHANGED']}
    return {'state':job['state'],'result':value}

def anchor(args):
    return {'source_sha256':args['source_sha256'],'page_index':args['page_index'],
        'page_id':pdf.page_id(args['source_sha256'],args['page_index']),'rect':pdf.rect(args['rect']),
        'coordinate_basis':'NORMALIZED_TOP_LEFT_CROPPED_RENDER'}

def load(payload,expected_sha):
    value=record_io.strict_json(payload)
    if pdf.digest(value)!=expected_sha:raise ValueError('PDF_ANNOTATION_INTEGRITY_FAILED')
    return value

def annotations(db,ns,item,actor):
    rows=[]
    for version,payload,check in db.execute('SELECT version,payload,sha256 FROM ref_pdf_annotations WHERE ns=? AND owner=? AND item=? ORDER BY rowid',(ns['id'],actor,item['id'])):
        value=load(payload,check)
        try:
            _,decision=intake.eligible(db,ns,item)
            state='CURRENT' if value['anchor']['source_sha256']==item['sha256'] else 'SOURCE_CHANGED'
        except (ValueError,OSError):state='ORIGINAL_UNAVAILABLE'
        rows.append({**value,'binding_state':state,'fact_verification':'OWNER_ANNOTATION_NOT_AN_ACCEPTED_FACT'})
    return rows

def export_annotations(db,ns,items,actor):
    result=[]
    for item_id in items:
        item=intake.load(db,'items',item_id)
        result.extend(annotations(db,ns,item,actor))
    if len(result)>2000 or len(records.canonical(result))>8*1024*1024:raise ValueError('PDF_ANNOTATION_EXPORT_BUDGET')
    return result

def validate_export(rows,sources):
    if not isinstance(rows,list) or len(rows)>2000:raise ValueError('PDF_ANNOTATION_VOLUME_SCHEMA')
    by_item={v['item']:v for v in sources};seen=set()
    for row in rows:
        fields={'schema','id','namespace','item','version','anchor','kind','text','printed_label','created','modified','binding_state','fact_verification'}
        if not isinstance(row,dict) or set(row)!=fields:raise ValueError('PDF_ANNOTATION_VOLUME_SCHEMA')
        if row.get('id') in seen or row.get('schema')!='arc.pdf-annotation/1' or row.get('item') not in by_item:raise ValueError('PDF_ANNOTATION_VOLUME_ANCHOR')
        if any(not isinstance(row[k],str) or not re.fullmatch(r'[a-f0-9]{32}',row[k]) for k in ('id','namespace','item')) or type(row['version']) is not int or row['version']<1:raise ValueError('PDF_ANNOTATION_VOLUME_SCHEMA')
        if row['kind'] not in ANNOTATION['kind']['enum'] or not isinstance(row['printed_label'],str) or len(row['printed_label'])>80 or any(type(row[k]) not in (int,float) or not math.isfinite(row[k]) for k in ('created','modified')):raise ValueError('PDF_ANNOTATION_VOLUME_CONTENT')
        seen.add(row['id']);a=row['anchor']
        if not isinstance(a,dict) or set(a)!={'source_sha256','page_index','page_id','rect','coordinate_basis'} or a['coordinate_basis']!='NORMALIZED_TOP_LEFT_CROPPED_RENDER':raise ValueError('PDF_ANNOTATION_VOLUME_ANCHOR')
        pdf.rect(a['rect'])
        if type(a['page_index']) is not int or not 0<=a['page_index']<pdf.MAX_PAGES or a['source_sha256']!=by_item[row['item']]['sha256'] or a['page_id']!=pdf.page_id(a['source_sha256'],a['page_index']):raise ValueError('PDF_ANNOTATION_VOLUME_ANCHOR')
        source=by_item[row['item']];count=source.get('metadata',{}).get('pages')
        if Path(source['name']).suffix.lower()!='.pdf' or type(count) is not int or a['page_index']>=count:raise ValueError('PDF_ANNOTATION_VOLUME_ANCHOR')
        if not isinstance(row.get('text'),str) or not row['text'].strip() or len(row['text'])>8000 or row.get('fact_verification')!='OWNER_ANNOTATION_NOT_AN_ACCEPTED_FACT' or row['binding_state']!='CURRENT':raise ValueError('PDF_ANNOTATION_VOLUME_CONTENT')
    return len(rows)

def dispatch(kernel,op,args,principal):
    actor=principal.identity
    if op=='references.pdf.citation.resolve':
        citation=args['citation'];source={k:citation[k] for k in SOURCE};value=info(kernel,source,principal)
        if value['state']!='CURRENT' or citation['page_index']>=value['page_count']:raise ValueError('PDF_CITATION_ORIGINAL_UNAVAILABLE')
        return {'state':'CURRENT','citation':pdf.citation(citation['namespace'],citation['item'],citation['source_sha256'],citation['page_index'],citation['rect']),'document':value}
    if op=='references.pdf.info':return info(kernel,args,principal)
    if op=='references.pdf.page':
        opts={k:v for k,v in args.items() if k!='request_key'}
        return kernel.submit({'tool':JOB,'references':opts,'request_key':args.get('request_key',uuid.uuid4().hex),'timeout':120},principal)
    if op=='references.pdf.result':return result(kernel,args,principal)
    with kernel.db() as db:
        ensure(db)
        if op in ('references.pdf.annotation.save','references.pdf.annotation.remove','references.pdf.draft.put'):db.execute('BEGIN IMMEDIATE')
        ns=intake.namespace(db,args['namespace'],actor,op!='references.pdf.annotations')
        if op=='references.pdf.annotation.remove':
            row=db.execute('SELECT version FROM ref_pdf_annotations WHERE ns=? AND owner=? AND id=?',(ns['id'],actor,args['id'])).fetchone()
            if not row or row[0]!=args['expected_version']:raise ValueError('PDF_ANNOTATION_CONFLICT_RELOAD')
            db.execute('DELETE FROM ref_pdf_annotations WHERE id=?',(args['id'],));return {'removed':args['id']}
        item=intake.load(db,'items',args['item'])
        if item['namespace']!=ns['id']:raise ValueError('PDF_SOURCE_NAMESPACE_MISMATCH')
        if op=='references.pdf.annotations':return {'annotations':annotations(db,ns,item,actor),'source_sha256':item['sha256']}
        if op=='references.pdf.draft.get':
            ident=pdf.page_id(args['source_sha256'],args['page_index'])
            rows=[load(p,s) for p,s in db.execute('SELECT payload,sha256 FROM ref_pdf_drafts WHERE ns=? AND owner=? AND item=? AND page_id=? ORDER BY rowid DESC LIMIT 10',(ns['id'],actor,item['id'],ident))]
            return {'drafts':rows,'committed':False}
        a=anchor(args)
        if op=='references.pdf.draft.put':
            draft={k:v for k,v in args.items() if k!='namespace'};draft['saved_at']=time.time()
            db.execute('INSERT OR REPLACE INTO ref_pdf_drafts VALUES(?,?,?,?,?,?,?)',(ns['id'],actor,item['id'],a['page_id'],args['writer'],records.canonical(draft).decode(),pdf.digest(draft)))
            db.execute('DELETE FROM ref_pdf_drafts WHERE ns=? AND owner=? AND item=? AND rowid NOT IN (SELECT rowid FROM ref_pdf_drafts WHERE ns=? AND owner=? AND item=? ORDER BY rowid DESC LIMIT 32)',(ns['id'],actor,item['id'],ns['id'],actor,item['id']))
            return {'saved_recovery_draft':True,'committed':False}
        if not args['text'].strip():raise ValueError('PDF_ANNOTATION_TEXT_REQUIRED')
        original(db,args,actor,True)
        checked=pdf.bounded('inspect',intake.vault(ns).path(item['sha256']),item['sha256'])
        if not 0<=args['page_index']<checked['page_count']:raise ValueError('PDF_PHYSICAL_PAGE_OUT_OF_RANGE')
        ident=args.get('id',uuid.uuid4().hex);old=db.execute('SELECT version,payload,sha256,owner FROM ref_pdf_annotations WHERE id=?',(ident,)).fetchone()
        if old and old[3]!=actor or old and (old[0]!=args['expected_version'] or load(old[1],old[2])['item']!=item['id']) or not old and args['expected_version']!=0:raise ValueError('PDF_ANNOTATION_CONFLICT_RELOAD')
        created=load(old[1],old[2])['created'] if old else time.time();version=(old[0] if old else 0)+1
        value={'schema':'arc.pdf-annotation/1','id':ident,'namespace':ns['id'],'item':item['id'],'version':version,
            'anchor':a,'kind':args['kind'],'text':args['text'],'printed_label':args.get('printed_label',''),
            'created':created,'modified':time.time()}
        db.execute('INSERT OR REPLACE INTO ref_pdf_annotations VALUES(?,?,?,?,?,?,?)',(ident,ns['id'],actor,item['id'],version,records.canonical(value).decode(),pdf.digest(value)))
        if args.get('writer'):db.execute('DELETE FROM ref_pdf_drafts WHERE ns=? AND owner=? AND item=? AND page_id=? AND writer=?',(ns['id'],actor,item['id'],a['page_id'],args['writer']))
        activity.append(db,activity.make_event(actor,'references.pdf.annotation.save','NOTE_SAVED'))
        return {**value,'fact_verification':'OWNER_ANNOTATION_NOT_AN_ACCEPTED_FACT'}
