"""Reviewed content grants over SW-001 identities; no borrowed owner Principal.

Owner capture uses that actual caller's existing reads. Device reads use only
the exact approved projection and revalidate source, grant and renderer seals.
"""
from __future__ import annotations
import base64, hashlib, secrets
from pathlib import Path
from sdk.cli.arc1cli import window_views as core,slate_windows as legacy
from . import record_io as io,object_context,record_access,pdf_service,intake_service

ID={'type':'string','minLength':35,'maxLength':35};SHA=object_context.SHA
VIEW={'type':'string','enum':list(core.VIEWS)}
BOUND={'window_id':ID,'view':VIEW,'expected_revision':SHA}
EXACT={**BOUND,'content_sha256':SHA}
FIELDS={
 'ledger.windows.pdf':({'job':{'type':'string','pattern':'^[a-f0-9]{32}$'}},['job']),
 'ledger.deck.preview':(BOUND,list(BOUND)),
 'ledger.deck.publish':({**EXACT,'device':{'type':'string','minLength':1,'maxLength':100}},[*EXACT,'device']),
 'ledger.deck.list':({},[]),
 'ledger.deck.read':(EXACT,list(EXACT)),
 'ledger.deck.image':(EXACT,list(EXACT)),
 'ledger.deck.present':({**EXACT,'presentation':{'type':'object'}},[*EXACT,'presentation'])}
SCOPES={op:'read' if op in core.REMOTE_OPERATIONS else 'approve' for op in FIELDS}
ERROR='WINDOW_UNAVAILABLE'

def ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS slate_view_previews(window_id TEXT,view TEXT,payload TEXT,sha256 TEXT,seal TEXT,resource TEXT,PRIMARY KEY(window_id,view))')
    db.execute('CREATE TABLE IF NOT EXISTS slate_view_grants(window_id TEXT,device TEXT,view TEXT,session TEXT,sha256 TEXT,PRIMARY KEY(window_id,device,view))')
    db.execute('CREATE TABLE IF NOT EXISTS slate_view_layouts(window_id TEXT,device TEXT,view TEXT,payload TEXT,PRIMARY KEY(window_id,device,view))')
def prune(db,ident,device=None):
    ensure(db)
    for table in ('slate_view_grants','slate_view_layouts'):
        db.execute('DELETE FROM '+table+' WHERE window_id=?'+(' AND device=?' if device else ''),(ident,device) if device else (ident,))
    if device is None:db.execute('DELETE FROM slate_view_previews WHERE window_id=?',(ident,))
def fingerprint():return io.digest([io.sha(Path(__file__)),io.sha(Path(core.__file__))])
def document(kernel,job_id,owner):
    """Private dependency check by stored owner, never dispatch as that owner."""
    job=kernel.record('jobs',job_id)
    if job.get('owner')!=owner or job.get('tool')!=pdf_service.JOB or job.get('state')!='Completed' or not job.get('evidence'):raise ValueError(ERROR)
    ev=kernel.record('evidence',job['evidence']);value=io.strict_json((kernel.root/'build/references/runs'/job_id/'result.json').read_bytes())
    if ev.get('job')!=job_id or ev.get('diagnostics')!=value or value.get('status')!='RENDERED':raise ValueError(ERROR)
    args=job['request_spec']['references']
    with kernel.db() as db:ns,item,raw,decision=pdf_service.original(db,args,owner,True)
    image=kernel.safe(value['image'])
    if image.stat().st_size>6*1024*1024 or io.sha(image)!=value['image_sha256']:raise ValueError(ERROR)
    seal=io.digest([job,ev,args,item['sha256'],decision['id'],value['image_sha256']])
    return value,seal
def document_seal(kernel,selector,owner):return document(kernel,selector['target'],owner)[1]
def capture_document(kernel,principal,job_id,expected=None):
    value,seal=document(kernel,job_id,principal.identity)
    identity=io.digest({'schema':'arc.pdf-view-identity/1','namespace':value['namespace'],'item':value['item'],'source_sha256':value['source_sha256'],'page_index':value['page']['page_index']})
    if expected and expected!=identity:raise ValueError('WINDOW_CONTEXT_NEEDS_REFRESH')
    overview={'object':{'kind':'pdf','target':job_id},'object_id':identity,
        'source_revision':io.digest([identity,seal]),'title':value['name']+' · physical page '+str(value['page']['physical_page']),
        'authority':'ORIGINAL_BOUND_PDF_DERIVATIVE','source_count':1,'evidence_count':1,
        'gaps':['PRINTED_LABEL_NOT_INFERRED','OCR_UNVERIFIED','NO_FACT_ACCEPTANCE']}
    return overview,seal
def native_preview(kernel,row,principal,kind):
    s=row['selector'];resource=None;blocks=[];image=None
    if s['kind']=='pdf':
        if kind!='pdf':raise ValueError('WINDOW_VIEW_NOT_SUPPORTED_FOR_OBJECT')
        value,unused=document(kernel,s['target'],principal.identity)
        blocks=[core.block('Original page identity',{'original_sha256':value['source_sha256'],'physical_page':value['page']['physical_page'],'pdf_label':value['page']['pdf_label'],'printed_label':'NOT_ESTABLISHED','coordinate_basis':value['coordinate_basis']},collapsed=True),
            core.block('Native text · compare symbols and reading order with the image',value['native']['text'])]
        if value.get('ocr'):
            o=value['ocr'];blocks.append(core.block('OCR · all text unverified',o['text']));blocks.append(core.block('OCR provenance',{'tool':o['tool'],'language':o['language'],'lower_score_words':o['uncertain_words'],'score_meaning':o['score_meaning']},collapsed=True))
        image={'sha256':value['image_sha256'],'width':value['image_width'],'height':value['image_height'],'type':'image/png'}
        resource={'job':s['target'],'image':value['image'],'sha256':value['image_sha256']}
    else:
        context=object_context.inspect(kernel,{'selector':s,'expected_revision':row['overview']['source_revision'],'expected_object_id':row['overview']['object_id']},principal)
        if context.get('state')!='AVAILABLE':raise ValueError('WINDOW_CONTEXT_NEEDS_REFRESH')
        technical=context['technical']
        if kind=='object':
            if s['kind']=='job':
                j=technical['job'];data={k:j.get(k) for k in ('id','tool','state','goal','revision','created','started','ended','error')}
            elif s['kind']=='file':data=technical
            else:data=technical
            blocks=[core.block('Object and source authority',{'object':s,'authority':context['authority'],'physical_qualification':False}),core.block('Technical context',data),core.block('Gaps',context['gaps'])]
        elif kind=='sources':
            blocks=[core.block('Source identities',context['sources'],collapsed=True)]
            if s['kind']=='file':
                path=record_access.file_read(kernel,s['target'],principal)
                with path.open('rb') as f:raw=f.read(core.MAX_TEXT+1)
                prefix=raw[:core.MAX_TEXT]
                try:body=prefix.decode('utf-8')
                except UnicodeDecodeError as exc:
                    if len(raw)>core.MAX_TEXT and exc.reason=='unexpected end of data':body=prefix[:exc.start].decode('utf-8')
                    else:raise ValueError('WINDOW_SOURCE_TEXT_PROFILE_UNAVAILABLE') from None
                b=core.block('Saved original text · no unsaved editor buffer',body);b['truncated']=len(raw)>core.MAX_TEXT;blocks.append(b)
            elif s['kind'] in ('component','net'):blocks.append(core.block('Native relationships',technical))
            elif s['kind']=='job':blocks.append(core.block('Bound source hashes',technical['job'].get('input_hashes',{})))
        elif kind=='evidence':
            blocks=[core.block('Evidence references',context['evidence'])]
            if s['kind']=='job' and technical.get('evidence'):
                e=technical['evidence'];blocks.append(core.block('Recorded result',{k:e.get(k) for k in ('id','job','tool','state','class','outcome','revision','exit_status','duration_seconds','artifacts','error')}))
            blocks.append(core.block('Qualification','A recorded source or host result grants no physical qualification or source acceptance.'))
        elif kind=='review':
            if s['kind']!='job' or not technical['job'].get('candidate'):raise ValueError('WINDOW_REVIEW_CANDIDATE_REQUIRED')
            candidate=technical['job']['candidate'];reply=kernel.dispatch('candidates.diff',{'id':candidate},principal)
            if not reply['ok']:raise ValueError(ERROR)
            d=reply['result'];blocks=[core.block('Read-only candidate review',{'candidate':candidate,'job':s['target'],'source_revision':context['revision'],'job_facts':technical['facts'],'acceptance':'SEPARATE_OWNER_ACTION'})]
            for change in d['changes'][:core.MAX_BLOCKS-1]:blocks.append(core.block(change['path'],change['diff']))
            if len(d['changes'])>=core.MAX_BLOCKS:blocks[-1]['truncated']=True
        else:raise ValueError('WINDOW_VIEW_NOT_SUPPORTED_FOR_OBJECT')
    return core.projection(row,kind,blocks,image),resource

def preview_row(db,ident,kind):
    found=db.execute('SELECT payload,sha256,seal,resource FROM slate_view_previews WHERE window_id=? AND view=?',(ident,kind)).fetchone()
    if not found:raise ValueError(ERROR)
    value=io.strict_json(found[0]);core.validate(value)
    if core.digest(value)!=found[1]:raise ValueError(ERROR)
    return value,found[1],found[2],io.strict_json(found[3]) if found[3] else None
def stale(ident,kind):return {'schema':core.VERSION,'window_id':ident,'view':kind,'state':'STALE','content':None,'summary':'Sources or reviewed content changed. Ask the desktop owner to refresh, review and publish again.'}
def content_access(kernel,principal,args):
    from . import slate_windows as windows
    ident=legacy.window_id(args['window_id']);kind=core.view(args['view']);row,ticket,owner=windows.access(kernel,principal,ident)
    with kernel.db() as db:
        value,check,seal,resource=preview_row(db,ident,kind);grant=None
        if not owner:
            grant=db.execute('SELECT session,sha256 FROM slate_view_grants WHERE window_id=? AND device=? AND view=?',(ident,principal.identity,kind)).fetchone()
            if grant!=(windows.session(db,principal.identity,principal),check):raise ValueError(ERROR)
    token=io.digest([ticket,check,seal,resource,grant])
    if args['expected_revision']!=row['overview']['source_revision'] or args['content_sha256']!=check:return row,token,None,None
    if value['window_id']!=row['id'] or value['view']!=kind or value['object_id']!=row['overview']['object_id'] or value['source_revision']!=row['overview']['source_revision'] or value['state_revision']!=row['generation'] or seal!=io.digest([row['source_seal'],fingerprint()]):return row,token,None,None
    if windows.source_seal(kernel,row['selector'],row['owner'])!=row['source_seal']:return row,token,None,None
    return row,token,value,resource
def read(kernel,principal,args,image=False):
    try:row,ticket,value,resource=content_access(kernel,principal,args)
    except (ValueError,OSError,KeyError,TypeError):
        # No distinction between guessed and inaccessible content.
        raise ValueError(ERROR) from None
    if value is None:return stale(args['window_id'],args['view'])
    if image:
        if value['image'] is None or not resource:raise ValueError(ERROR)
        try:path=kernel.safe(resource['image']);raw=path.read_bytes()
        except (ValueError,OSError):raise ValueError(ERROR) from None
        if len(raw)>6*1024*1024 or hashlib.sha256(raw).hexdigest()!=resource['sha256']:raise ValueError(ERROR)
        result={'schema':core.VERSION,'image_b64':base64.b64encode(raw).decode(),'sha256':resource['sha256'],'type':'image/png'}
    else:
        with kernel.db() as db:
            found=db.execute('SELECT payload FROM slate_view_layouts WHERE window_id=? AND device=? AND view=?',(args['window_id'],principal.identity,args['view'])).fetchone()
        result={'state':'AVAILABLE','content':value,'content_sha256':core.digest(value),'presentation':core.presentation(io.strict_json(found[0])) if found else dict(core.DEFAULT_LAYOUT)}
    try:after=content_access(kernel,principal,args)
    except (ValueError,OSError,KeyError,TypeError):raise ValueError(ERROR) from None
    if after[1]!=ticket:raise ValueError(ERROR)
    if after[2] is None:return stale(args['window_id'],args['view'])
    return result

def dispatch(kernel,op,args,principal):
    from . import slate_windows as windows
    if 'read' not in principal.scopes:raise ValueError(ERROR)
    with kernel.db() as db:ensure(db)
    if op=='ledger.windows.pdf':
        view,docseal=capture_document(kernel,principal,args['job']);selector=view['object'];seal=windows.source_seal(kernel,selector,principal.identity)
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if not windows.flag(db,principal.identity)[0]:raise ValueError('SLATE_WINDOWS_DISABLED')
            ident=None
            for old_id, in db.execute('SELECT id FROM slate_windows WHERE owner=?',(principal.identity,)):
                old=windows.load(db,old_id)
                if old['overview']['object_id']==view['object_id'] and old['overview']['source_revision']==view['source_revision']:ident=old_id;break
            if ident is None:
                if db.execute('SELECT count(*) FROM slate_windows WHERE owner=?',(principal.identity,)).fetchone()[0]>=legacy.MAX_WINDOWS:raise ValueError('WINDOW_REGISTRY_LIMIT')
                ident='sw_'+secrets.token_hex(16);windows.save(db,{'schema':legacy.VERSION,'id':ident,'owner':principal.identity,'selector':selector,'overview':view,'source_seal':seal,'generation':1})
        return windows.snapshot(kernel,principal,ident)
    if op=='ledger.deck.list':
        rows=windows.dispatch(kernel,'ledger.windows.list',{},principal)['windows'];out=[]
        for row in rows:
            views=[]
            with kernel.db() as db:
                kinds=[v for v, in db.execute('SELECT view FROM slate_view_previews WHERE window_id=?',(row['window_id'],))]
            for kind in kinds:
                try:
                    with kernel.db() as db:value,check,seal,resource=preview_row(db,row['window_id'],kind)
                    query={'window_id':row['window_id'],'view':kind,'expected_revision':row.get('source_revision','0'*64),'content_sha256':check}
                    if content_access(kernel,principal,query)[2] is not None:views.append({'view':kind,'content_sha256':check})
                except (ValueError,OSError,KeyError,TypeError):pass
            # Late grant/source changes must also remove overview metadata.
            try:final=windows.snapshot(kernel,principal,row['window_id'])
            except (ValueError,OSError,KeyError,TypeError):continue
            out.append({**final,'views':views if final.get('state')=='AVAILABLE' and final.get('source_revision')==row.get('source_revision') else []})
        return {'schema':core.VERSION,'windows':out,'limit':legacy.MAX_WINDOWS,'effects':['read']}
    if op in ('ledger.deck.read','ledger.deck.image'):return read(kernel,principal,args,op.endswith('.image'))
    if op=='ledger.deck.present':
        layout=core.presentation(args['presentation']);row,ticket,value,resource=content_access(kernel,principal,args)
        if value is None:raise ValueError('WINDOW_CONTEXT_NEEDS_REFRESH')
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE')
            checked=content_access(kernel,principal,args)
            if checked[1]!=ticket or checked[2] is None:raise ValueError(ERROR)
            db.execute('INSERT OR REPLACE INTO slate_view_layouts VALUES(?,?,?,?)',(args['window_id'],principal.identity,args['view'],io.canonical(layout).decode()))
        return {'presentation':layout,'engineering_state_changed':False}
    row,ticket,owner=windows.access(kernel,principal,args['window_id'],owner_only=True)
    if args['expected_revision']!=row['overview']['source_revision'] or windows.snapshot(kernel,principal,row['id'])['state']!='AVAILABLE':raise ValueError('WINDOW_CONTEXT_NEEDS_REFRESH')
    kind=core.view(args['view'])
    if op=='ledger.deck.preview':
        value,resource=native_preview(kernel,row,principal,kind)
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if windows.access(kernel,principal,row['id'],owner_only=True)[1]!=ticket or windows.source_seal(kernel,row['selector'],row['owner'])!=row['source_seal']:raise ValueError(ERROR)
            db.execute('INSERT OR REPLACE INTO slate_view_previews VALUES(?,?,?,?,?,?)',(row['id'],kind,io.canonical(value).decode(),core.digest(value),io.digest([row['source_seal'],fingerprint()]),io.canonical(resource).decode() if resource else None))
        return {'state':'PREVIEW_ONLY','content':value,'content_sha256':core.digest(value),'published':False}
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if windows.access(kernel,principal,row['id'],owner_only=True)[1]!=ticket:raise ValueError(ERROR)
        value,check,seal,resource=preview_row(db,row['id'],kind)
        if value['window_id']!=row['id'] or value['view']!=kind or value['object_id']!=row['overview']['object_id'] or check!=args['content_sha256'] or value['source_revision']!=args['expected_revision'] or value['state_revision']!=row['generation'] or seal!=io.digest([row['source_seal'],fingerprint()]):raise ValueError('WINDOW_REVIEW_PREVIEW_CHANGED')
        if windows.source_seal(kernel,row['selector'],row['owner'])!=row['source_seal']:raise ValueError('WINDOW_CONTEXT_NEEDS_REFRESH')
        binding=windows.session(db,args['device'])
        count=db.execute('SELECT count(*) FROM slate_window_grants WHERE window_id=?',(row['id'],)).fetchone()[0]
        exists=db.execute('SELECT 1 FROM slate_window_grants WHERE window_id=? AND device=?',(row['id'],args['device'])).fetchone()
        if count>=legacy.MAX_DEVICES and not exists:raise ValueError('WINDOW_PUBLICATION_LIMIT')
        db.execute('INSERT OR REPLACE INTO slate_window_grants VALUES(?,?,?,?)',(row['id'],args['device'],binding,args['expected_revision']))
        db.execute('INSERT OR REPLACE INTO slate_view_grants VALUES(?,?,?,?,?)',(row['id'],args['device'],kind,binding,check))
    return {'window_id':row['id'],'published_to':args['device'],'view':kind,'content_sha256':check,'execution_granted':False}
