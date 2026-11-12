"""Private reviewed memory and verified context transitions in the shared Kernel.

No background collection, weight training, scheduler or alternate authority.
Original source bindings are rechecked whenever a checkpoint is resumed.
"""
from __future__ import annotations
import base64,hashlib,hmac,io,json,math,os,re,secrets,tempfile,time,uuid,zipfile
from pathlib import Path
from sdk.cli.arc1cli import learning_contracts as c,record_store as records,intake_files
from . import activity,intake_service as intake,reference_service as refs,local_brain,record_io

ID=intake.ID;SHA=intake.SHA;TEXT=intake.TEXT;REASON=intake.REASON
CONTEXT={'type':'string','enum':list(c.CONTEXTS)}
FIELDS={
 'memory.status':({},[]),'memory.profile':({},[]),'memory.profile.import':({'path':TEXT},['path']),
 'memory.profile.enable':({'enabled':{'type':'boolean'}},['enabled']),
 'memory.profile.configure':({'parameters':{'type':'object'}},['parameters']),
 'memory.profile.delete':({'reason':REASON},['reason']),
 'memory.preferences':({'context':CONTEXT},['context']),
 'memory.feedback':({'id':ID,'preference':{'type':'string','maxLength':48},'context':CONTEXT,'feedback':{'type':'number','minimum':0,'maximum':1},
    'instruction':{'type':'string','maxLength':300},'source_reference':{'type':'string','maxLength':300},'kind':{'type':'string','enum':list(c.WEIGHTS)},'soft':{'type':'boolean'},'supersedes':{'type':'array','items':ID}},['id','preference','context','feedback','instruction','source_reference','kind','soft']),
 'memory.feedback.list':({},[]),'memory.feedback.undo':({'id':ID},['id']),'memory.feedback.forget':({'id':ID},['id']),
 'memory.task.create':({'title':{'type':'string','minLength':1,'maxLength':120}},['title']),
 'memory.tasks':({},[]),'memory.task':({'id':ID},['id']),
 'memory.checkpoint.save':({'task':ID,'expected_previous':intake.RECEIPT,'note':{'type':'object'},'references':{'type':'array'},'jobs':{'type':'array','items':ID},'conversation':ID},['task','expected_previous','note','references','jobs']),
 'memory.checkpoint':({'id':ID},['id']),
 'memory.checkpoint.context':({'id':ID,'context':CONTEXT},['id']),
 'memory.checkpoint.rebind':({'id':ID,'namespace':ID,'reason':REASON},['id','namespace','reason']),
 'memory.conversation':({'id':ID},['id']),
 'memory.context.clear':({'checkpoint':ID,'expected_context':SHA},['checkpoint','expected_context']),
 'memory.answer.validate':({'checkpoint':ID,'context_digest':SHA,'context':CONTEXT,'answer':{'type':'object'}},['checkpoint','context_digest','answer']),
 'memory.lesson.propose':({'title':{'type':'string','maxLength':120},'body':{'type':'string','maxLength':1500},'references':{'type':'array'}},['title','body','references']),
 'memory.lesson.review':({'id':ID,'approved':{'type':'boolean'},'reason':REASON},['id','approved','reason']),
 'memory.lessons':({'query':{'type':'string','maxLength':200}},[]),
 'memory.archive.export':({'destination':TEXT,'key_path':TEXT},['destination','key_path']),
 'memory.archive.restore':({'path':TEXT,'key_path':TEXT},['path','key_path'])}
APPROVE={'memory.profile.import','memory.profile.enable','memory.profile.configure','memory.profile.delete','memory.feedback','memory.feedback.undo','memory.feedback.forget','memory.context.clear','memory.checkpoint.save','memory.checkpoint.rebind','memory.lesson.review','memory.archive.export','memory.archive.restore'}
EXECUTE={'memory.task.create','memory.checkpoint.save','memory.lesson.propose'}
SCOPES={op:'approve' if op in APPROVE else 'execute' if op in EXECUTE else 'read' for op in FIELDS}
KINDS={'profile','feedback','task','checkpoint','receipt','transition','lesson','observation'}

def ensure(db):db.execute('CREATE TABLE IF NOT EXISTS stacy_memory(owner TEXT,kind TEXT,id TEXT,payload TEXT,sha256 TEXT,PRIMARY KEY(owner,kind,id))')
def event(db,actor,state):activity.append(db,activity.make_event(actor,'memory.state',state))
def store(db,actor,kind,ident,value):
    if kind not in KINDS:raise ValueError('MEMORY_KIND')
    raw=records.canonical(value)
    if len(raw)>128*1024:raise ValueError('MEMORY_RECORD_RESOURCE_LIMIT')
    if db.execute('SELECT count(*) FROM stacy_memory WHERE owner=?',(actor,)).fetchone()[0]>=4000 and not db.execute('SELECT 1 FROM stacy_memory WHERE owner=? AND kind=? AND id=?',(actor,kind,ident)).fetchone():raise ValueError('MEMORY_OWNER_RECORD_LIMIT')
    db.execute('INSERT OR REPLACE INTO stacy_memory VALUES(?,?,?,?,?)',(actor,kind,ident,raw.decode(),hashlib.sha256(raw).hexdigest()))
def get(db,actor,kind,ident,optional=False):
    row=db.execute('SELECT payload,sha256 FROM stacy_memory WHERE owner=? AND kind=? AND id=?',(actor,kind,ident)).fetchone()
    if not row:
        if optional:return None
        raise ValueError('PRIVATE_MEMORY_NOT_FOUND_OR_NOT_OWNED')
    if hashlib.sha256(row[0].encode()).hexdigest()!=row[1]:raise ValueError('PRIVATE_MEMORY_RECORD_CORRUPT')
    return records.strict(row[0])
def listing(db,actor,kind):
    return [get(db,actor,kind,r[0]) for r in db.execute('SELECT id FROM stacy_memory WHERE owner=? AND kind=? ORDER BY rowid',(actor,kind)).fetchall()]
def original_seed(profile):
    raw=base64.b64decode(profile['original_b64'],validate=True)
    if hashlib.sha256(raw).hexdigest()!=profile['original_sha256']:raise ValueError('PERSONALITY_ORIGINAL_CHANGED')
    return c.seed(raw)
def profile_view(db,actor):
    p=get(db,actor,'profile','current',True)
    return {'state':'NOT_IMPORTED','enabled':False} if p is None else {k:v for k,v in p.items() if k!='original_b64'}|{'expression':original_seed(p)}
def profile_context(db,actor,context):
    p=get(db,actor,'profile','current',True)
    if p is None or not p['enabled']:return {'state':'DISABLED_OR_NOT_IMPORTED','context':context,'data':None}
    seed=original_seed(p);events=listing(db,actor,'feedback');day=int(time.time()//86400)*86400;preferences=c.posterior(events,context,day,p['parameters']);selected=preferences[:6]
    expression={'character':seed['character'][:250],'inherit':seed['inherit'][:4],'retain':seed['retain'][:4]}
    return {'state':'ACTIVE','context':context,'seed_sha256':p['original_sha256'],'revision':p['revision'],
      'data':{'expression':expression,'preferences':[{'id':v['preference'],'mean':round(v['mean'],5),'owner_direction':v['instruction'],'event_ids':v['events']} for v in selected]},
      'omitted_preference_count':max(0,len(preferences)-6),'soft_decay_as_of_UTC_day':day,'authority':'PREFERENCES_NOT_PERMISSIONS_OR_ENGINEERING_FACTS','cloud_disclosure':'NOT_GRANTED'}
def conversation(db,actor,ident):
    c.ident(ident);value=local_brain.get(None,'dialogue.'+ident,None,db)
    if value is None:return {'id':ident,'owner':actor,'messages':[]}
    if value['owner']!=actor:raise ValueError('PRIVATE_CONVERSATION_NOT_OWNED')
    return value
def context_hash(value):return c.digest({'id':value['id'],'owner':value['owner'],'messages':value['messages']})
def capture_references(db,actor,bindings):
    if not isinstance(bindings,list) or len(bindings)>8:raise ValueError('CHECKPOINT_REFERENCE_BOUND')
    result=[];seen=set();cache={}
    for b in bindings:
        if not isinstance(b,dict) or set(b)-{'namespace','id','item'} or not {'namespace','id'}<=set(b):raise ValueError('CHECKPOINT_REFERENCE_FIELDS')
        c.ident(b['namespace']);c.ident(b['id'],64)
        if b.get('item'):c.ident(b['item'])
        ns=intake.namespace(db,b['namespace'],actor);citation=refs.require_current(refs.resolve(db,ns,b['id'],b.get('item'),cache,historical=True));key=(ns['id'],citation['item'],citation['id'])
        if key in seen:raise ValueError('CHECKPOINT_DUPLICATE_REFERENCE')
        seen.add(key);result.append({'namespace':ns['id'],'id':citation['id'],'item':citation['item'],'decision':citation['decision'],
          'source_sha256':citation['source_sha256'],'text_sha256':citation['text_sha256'],'locator':citation['locator'],'name':citation['name']})
    if len({v['namespace'] for v in result})>1:raise ValueError('CHECKPOINT_ONE_LIBRARY_PER_INVESTIGATION')
    return result
def recheck_references(db,actor,bindings):
    passages=[];gaps=[];cache={}
    for b in bindings:
        try:
            ns=intake.namespace(db,b['namespace'],actor);v=refs.require_current(refs.resolve(db,ns,b['id'],b['item'],cache,historical=True))
            if any(v[k]!=b[k] for k in ('decision','source_sha256','text_sha256','locator')):raise ValueError('CHECKPOINT_SOURCE_BINDING_CHANGED')
            passages.append(v)
        except (ValueError,OSError) as exc:gaps.append({'id':b['id'],'state':'LOCATED_BUT_UNAVAILABLE','reason':activity.redact(exc)})
    return passages,gaps
def capture_jobs(kernel,actor,ids):
    if not isinstance(ids,list) or len(ids)>20 or len(set(ids))!=len(ids):raise ValueError('CHECKPOINT_JOB_BOUND')
    result=[]
    for ident in ids:
        c.ident(ident);j=kernel.record('jobs',ident)
        if j['owner']!=actor:raise ValueError('PRIVATE_JOB_NOT_OWNED')
        result.append({'id':ident,'tool':j['tool'],'state':j['state'],'revision':j.get('revision'),'request_digest':c.digest(j.get('request_spec',{})),
          'evidence_class':'RECORDED_KERNEL_JOB_NOT_PHYSICAL_QUALIFICATION'})
    return result
def verified(db,actor,ident):
    cp=get(db,actor,'checkpoint',c.ident(ident));receipt=get(db,actor,'receipt',ident)
    if receipt['sha256']!=c.digest(cp):raise ValueError('CHECKPOINT_READBACK_RECEIPT_MISMATCH')
    return cp
def verify_readback(kernel,actor,ident,expected):
    # Separate connection: a transaction's own write is not durable readback.
    with kernel.db() as db:
        cp=get(db,actor,'checkpoint',ident)
        if c.digest(cp)!=expected:raise ValueError('CHECKPOINT_DURABLE_READBACK_FAILED')
        return cp
def commit_checkpoint(kernel,actor,cp,expected_previous):
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');task=get(db,actor,'task',cp['task'])
        if task['latest']!=expected_previous:raise ValueError('CHECKPOINT_HEAD_CHANGED')
        store(db,actor,'checkpoint',cp['id'],cp);event(db,actor,'CHECKPOINT_DRAFT_COMMITTED')
    verify_readback(kernel,actor,cp['id'],c.digest(cp))
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');task=get(db,actor,'task',cp['task']);saved=get(db,actor,'checkpoint',cp['id'])
        if task['latest']!=expected_previous or c.digest(saved)!=c.digest(cp):raise ValueError('CHECKPOINT_CHANGED_BEFORE_PUBLISH')
        store(db,actor,'receipt',cp['id'],{'checkpoint':cp['id'],'sha256':c.digest(cp),'verified_at':time.time()})
        task.update(latest=cp['id'],updated=time.time());store(db,actor,'task',task['id'],task);event(db,actor,'CHECKPOINT_READBACK_VERIFIED')
    return {**cp,'sha256':c.digest(cp),'verified_readback':True,'old_context_disposed':False}
def make_checkpoint(kernel,actor,args):
    with kernel.db() as db:
        task=get(db,actor,'task',c.ident(args['task']));c.text(args['expected_previous'],32)
        if task['latest']!=args['expected_previous']:raise ValueError('CHECKPOINT_HEAD_CHANGED')
        bindings=capture_references(db,actor,args['references']);note=c.note(args['note']);dialogue=conversation(db,actor,args['conversation']) if args.get('conversation') else None
        if sum(len(v['text']) for v in recheck_references(db,actor,bindings)[0])>10000:raise ValueError('CHECKPOINT_REFERENCE_CONTEXT_BUDGET')
        cp={'schema':c.VERSION,'id':uuid.uuid4().hex,'task':task['id'],'previous':task['latest'],'created':time.time(),'note':note,
          'references':bindings,'jobs':capture_jobs(kernel,actor,args['jobs']),'conversation':dialogue['id'] if dialogue else None,
          'transcript_digest':context_hash(dialogue) if dialogue else None,'transcript_messages':len(dialogue['messages']) if dialogue else 0,
          'transcript_characters':sum(len(v['content']) for v in dialogue['messages']) if dialogue else 0,
          'journal_cursor':db.execute('SELECT coalesce(max(seq),0) FROM activity_journal').fetchone()[0],
          'note_class':'OWNER_TASK_RECORD_NOT_ENGINEERING_PROOF','context_disposal':'SEPARATE_OWNER_ACTION_AFTER_READBACK'}
    return commit_checkpoint(kernel,actor,cp,args['expected_previous'])
def checkpoint_context(kernel,actor,ident,context='engineering_execution'):
    if context not in c.CONTEXTS:raise ValueError('MEMORY_CONTEXT')
    with kernel.db() as db:
        cp=verified(db,actor,ident);passages,gaps=recheck_references(db,actor,cp['references']);profile=profile_context(db,actor,context);jobs=[]
        for old in cp['jobs']:
            try:
                j=kernel.record('jobs',old['id'])
                if j['owner']!=actor:raise ValueError('PRIVATE_JOB_NOT_OWNED')
                jobs.append({'id':old['id'],'recorded_state':old['state'],'current_state':j['state'],'request_matches':c.digest(j.get('request_spec',{}))==old['request_digest'],'result_is_physical_proof':False})
            except ValueError:jobs.append({'id':old['id'],'recorded_state':old['state'],'current_state':'NOT_PRESENT_RECONCILE_EXPLICITLY','result_is_physical_proof':False})
        note=cp['note'] if not gaps else {**cp['note'],'summary':'WITHHELD_PENDING_CURRENT_ORIGINALS','findings':[],'contradictions':['Historical findings are withheld; current source review is required.']}
        # One failed source makes the compact technical account incomplete.
        if gaps:passages=[]
        lessons=[v for v in reviewed_lessons(db,actor,'') if v['review']=='OWNER_REVIEWED_PROCEDURE' and v['applicability']=='CURRENT'][:3]
        body={'schema':'arc.stacy-resume/1','checkpoint':cp['id'],'checkpoint_sha256':c.digest(cp),'state':'SOURCE_GAPS' if gaps else 'READY',
          'note':note,'passages':passages,'gaps':gaps,'jobs':jobs,'profile':profile,'lessons':lessons,'journal_cursor':cp['journal_cursor'],
          'fresh_conversation_required':True,'effects':['read'],'replay_executed':False,'authority':'TASK_RECOLLECTION_AND_CURRENT_SOURCES_NOT_NEW_EVIDENCE','cloud_disclosure':'NOT_GRANTED'}
        body['context_digest']=c.digest(body);return body
def reviewed_lessons(db,actor,query):
    result=[]
    for lesson in listing(db,actor,'lesson'):
        if query and query.casefold() not in (lesson['title']+' '+lesson['body']).casefold():continue
        _,gaps=recheck_references(db,actor,lesson['references'])
        value={**lesson,'applicability':'SOURCE_GAPS' if gaps else 'CURRENT','authority':'PROCEDURE_TEXT_NOT_EXECUTION_PERMISSION_OR_FACT_PROOF'}
        if gaps:value.update(body=None,gaps=gaps)
        result.append(value)
    return result
def fresh_destination(kernel,name,suffix):
    from .session import config_dir
    path=Path(name).expanduser().absolute()
    if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('MEMORY_EXPORT_LINKED_PATH')
    path=path.resolve()
    if path.exists() or path.suffix.lower()!=suffix or path.is_relative_to(kernel.root) or path.is_relative_to(config_dir()):raise ValueError('MEMORY_EXPORT_NEW_EXTERNAL_PATH_REQUIRED')
    with kernel.db() as db:
        for row in db.execute('SELECT payload FROM intake_batches'):
            source=json.loads(row[0]).get('source',{});origin=Path(source.get('origin','/nonexistent')).resolve()
            if path==origin or source.get('origin_kind')=='folder' and path.is_relative_to(origin):raise ValueError('MEMORY_EXPORT_CANNOT_WRITE_IN_ORIGINAL_SOURCE')
    return path
def publish(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix='.stacy-memory-',dir=path.parent);p=Path(tmp)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        if hashlib.sha256(p.read_bytes()).digest()!=hashlib.sha256(raw).digest():raise ValueError('MEMORY_EXPORT_READBACK_FAILED')
        os.link(p,path)
    finally:p.unlink(missing_ok=True)
def archive_export(kernel,actor,args):
    destination=fresh_destination(kernel,args['destination'],'.zip');key_path=fresh_destination(kernel,args['key_path'],'.key')
    members={};source_map={}
    with kernel.db() as db:
        rows=[]
        for kind,ident in db.execute('SELECT kind,id FROM stacy_memory WHERE owner=? ORDER BY kind,id',(actor,)):
            rows.append({'kind':kind,'id':ident,'value':get(db,actor,kind,ident)})
        if not rows:raise ValueError('MEMORY_ARCHIVE_EMPTY')
        for row in rows:
            if row['kind'] not in ('checkpoint','lesson'):continue
            for binding in row['value']['references']:
                if binding['source_sha256'] in source_map:continue
                try:
                    ns=intake.namespace(db,binding['namespace'],actor,True);item=intake.load(db,'items',binding['item']);raw,_=intake.eligible(db,ns,item)
                    if hashlib.sha256(raw).hexdigest()!=binding['source_sha256']:raise ValueError('SNAPSHOT_SOURCE_CHANGED')
                    basename=Path(item['name']).name;safe=re.sub('[^A-Za-z0-9_.-]','_',basename);name='sources/'+item['sha256'][:16]+'_'+safe
                    members[name]=raw;source_map[item['sha256']]={'path':name,'original_name':item['name'],'sha256':item['sha256']}
                except (ValueError,OSError):continue # Missing originals remain explicit gaps on restore.
        members['MEMORY.json']=records.canonical({'schema':'arc.stacy-private-archive/1','owner':actor,'rows':rows,'source_copies':list(source_map.values()),'admission_on_restore':'NONE_REVIEW_AND_REBIND_REQUIRED'})
    if sum(map(len,members.values()))>128*1024*1024:raise ValueError('MEMORY_ARCHIVE_BYTE_BUDGET')
    manifest={'schema':'arc.stacy-private-seal/1','files':{n:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in members.items()}}
    key=secrets.token_bytes(32);manifest_raw=records.canonical(manifest);members['MANIFEST.json']=manifest_raw;members['AUTH.txt']=hmac.new(key,manifest_raw,hashlib.sha256).hexdigest().encode()
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        for name,raw in sorted(members.items()):z.writestr(name,raw)
    key_raw=records.canonical({'schema':'arc.stacy-recovery-key/1','key_hex':key.hex()});publish(key_path,key_raw)
    try:publish(destination,stream.getvalue())
    except Exception:key_path.unlink(missing_ok=True);raise
    with kernel.db() as db:event(db,actor,'PRIVATE_ARCHIVE_EXPORTED')
    return {'state':'EXPORTED','rows':len(rows),'source_copies':len(source_map),'sha256':hashlib.sha256(stream.getvalue()).hexdigest(),'archive':str(destination),'recovery_key':str(key_path),'encrypted':False,'keep_key_separate':True,'contains_private_data':True}
def archive_restore(kernel,actor,args):
    raw=intake_files.read_stable(Path(args['path']),128*1024*1024)
    try:key=records.strict(intake_files.read_stable(Path(args['key_path']),1024))
    except ValueError as exc:raise ValueError('RECOVERY_KEY_SCHEMA: choose the recovery key file saved with this archive') from exc
    if not isinstance(key,dict) or key.get('schema')!='arc.stacy-recovery-key/1':raise ValueError('RECOVERY_KEY_SCHEMA')
    c.ident(key.get('key_hex'),64)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=intake_files.checked_zip(z)
        if sum(v.file_size for v in members)>128*1024*1024:raise ValueError('MEMORY_ARCHIVE_EXPANDED_BYTE_BUDGET')
        names={v.filename for v in members};manifest_raw=z.read('MANIFEST.json');manifest=records.strict(manifest_raw)
        if manifest.get('schema')!='arc.stacy-private-seal/1' or names!=set(manifest['files'])|{'MANIFEST.json','AUTH.txt'}:raise ValueError('MEMORY_ARCHIVE_MEMBERS')
        signature=z.read('AUTH.txt')
        if not hmac.compare_digest(signature,hmac.new(bytes.fromhex(key['key_hex']),manifest_raw,hashlib.sha256).hexdigest().encode()):raise ValueError('MEMORY_ARCHIVE_AUTHENTICATION_FAILED')
        data={n:z.read(n) for n in manifest['files']}
        for n,b in data.items():
            row=manifest['files'][n]
            if len(b)!=row['bytes'] or hashlib.sha256(b).hexdigest()!=row['sha256']:raise ValueError('MEMORY_ARCHIVE_MEMBER_CORRUPT')
    value=records.strict(data['MEMORY.json'])
    if value.get('schema')!='arc.stacy-private-archive/1' or value.get('owner')!=actor or len(value['rows'])>4000:raise ValueError('PRIVATE_ARCHIVE_OWNER_OR_SCHEMA')
    seen=set();checkpoints={};receipts={}
    for row in value['rows']:
        pair=(row['kind'],row['id'])
        if row['kind'] not in KINDS or pair in seen:raise ValueError('MEMORY_ARCHIVE_RECORDS')
        seen.add(pair)
        if row['kind']=='profile':original_seed(row['value'])
        if row['kind']=='checkpoint':c.note(row['value']['note']);checkpoints[row['id']]=row['value']
        if row['kind']=='receipt':receipts[row['id']]=row['value']
    for ident,r in receipts.items():
        if ident not in checkpoints or r['sha256']!=c.digest(checkpoints[ident]):raise ValueError('MEMORY_ARCHIVE_CHECKPOINT_CORRUPT')
    from .session import config_dir
    folder=config_dir()/'memory_recovery'/hashlib.sha256(actor.encode()).hexdigest()[:24]/hashlib.sha256(raw).hexdigest()[:24]
    if any(p.is_symlink() for p in (folder,*folder.parents)):raise ValueError('MEMORY_RECOVERY_LINKED_PATH')
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM stacy_memory WHERE owner=?',(actor,)).fetchone():raise ValueError('RESTORE_REQUIRES_EMPTY_OWNER_MEMORY')
        folder.mkdir(parents=True,mode=0o700,exist_ok=True)
        for source in value['source_copies']:
            name=source['path'];records.safe_name(name)
            if not name.startswith('sources/') or len(Path(name).parts)!=2 or name not in data or hashlib.sha256(data[name]).hexdigest()!=source['sha256']:raise ValueError('MEMORY_RECOVERY_SOURCE_INVALID')
            p=folder/Path(name).name
            if p.is_symlink():raise ValueError('MEMORY_RECOVERY_LINKED_PATH')
            if p.exists():
                if records.sha(p)!=source['sha256']:raise ValueError('MEMORY_RECOVERY_FILE_COLLISION')
            else:publish(p,data[name])
        for row in value['rows']:store(db,actor,row['kind'],row['id'],row['value'])
        event(db,actor,'PRIVATE_ARCHIVE_RESTORED_REFERENCES_UNADMITTED')
    return {'state':'RESTORED','rows':len(value['rows']),'source_copy_directory':str(folder),'reference_admissions':0,'jobs_replayed':0,'next':'Review restored source copies in Intake, index them, then explicitly rebind an identical checkpoint source. Existing historical bindings are preserved.'}

def commit_feedback(db,actor,args):
    """Original feedback commit, reusable inside an existing owner transaction."""
    c.ident(args['id']);name=args['preference']
    if not re.fullmatch('[a-z][a-z0-9_]{0,47}',name):raise ValueError('MEMORY_PREFERENCE_ID')
    feedback=args['feedback']
    if type(feedback) not in (int,float) or not math.isfinite(feedback) or not 0<=feedback<=1:raise ValueError('MEMORY_FEEDBACK_BOUND')
    if args['kind']=='owner_correction' and args['soft']:raise ValueError('MEMORY_DIRECT_CORRECTIONS_DO_NOT_DECAY')
    c.text(args['instruction'],300,False);c.text(args['source_reference'],300,False)
    input_value={k:args[k] for k in ('preference','context','feedback','instruction','source_reference','kind','soft')};input_value['supersedes']=args.get('supersedes',[]);input_digest=c.digest(input_value)
    old=get(db,actor,'feedback',args['id'],True)
    if old:
        if old.get('input_digest')!=input_digest:raise ValueError('FEEDBACK_EVENT_ID_CONFLICT')
        return {**old,'duplicate':True}
    events=listing(db,actor,'feedback');supersedes=c.strings(args.get('supersedes',[]),1000,32)
    if args['kind']=='owner_correction':supersedes=sorted(set(supersedes)|{e['id'] for e in events if e.get('preference')==name and e.get('context')==args['context']})
    by_id={e['id']:e for e in events}
    for ident in supersedes:
        c.ident(ident)
        if ident not in by_id or (by_id[ident].get('preference'),by_id[ident].get('context'))!=(name,args['context']):raise ValueError('FEEDBACK_SUPERSESSION_SCOPE')
    value={**input_value,'id':args['id'],'input_digest':input_digest,'supersedes':supersedes,'created':time.time(),'sequence':len(events)+1,'authenticated_owner':actor,'confirmation_basis':'OWNER_APPROVE_PRINCIPAL','undone':False,'forgotten':False}
    store(db,actor,'feedback',value['id'],value);event(db,actor,'OWNER_FEEDBACK_COMMITTED');return value


def commit_profile(db,actor,op,args):
    """Original profile update, reusable within the caller's transaction."""
    p=get(db,actor,'profile','current');p['revision']+=1
    if op.endswith('.enable'):p['enabled']=args['enabled']
    else:p['parameters']=c.parameters(args['parameters'])
    store(db,actor,'profile','current',p);event(db,actor,'PERSONALITY_CONFIGURATION_CHANGED');return profile_view(db,actor)


def dispatch(kernel,op,args,principal):
    actor=principal.identity
    if op=='memory.archive.export':return archive_export(kernel,actor,args)
    if op=='memory.archive.restore':
        try:return archive_restore(kernel,actor,args)
        except (zipfile.BadZipFile,KeyError,TypeError,UnicodeError) as exc:raise ValueError('MEMORY_ARCHIVE_CORRUPT_OR_UNSUPPORTED') from exc
    if op=='memory.checkpoint.save':return make_checkpoint(kernel,actor,args)
    if op in ('memory.checkpoint.context','memory.answer.validate'):
        value=checkpoint_context(kernel,actor,args.get('id',args.get('checkpoint')),args.get('context','engineering_execution'))
        if op.endswith('.context'):return value
        if value['context_digest']!=args['context_digest']:raise ValueError('RESUME_CONTEXT_CHANGED_DURING_INFERENCE')
        return refs.evidence.validate_answer(args['answer'],{'passages':value['passages']})
    if op=='memory.checkpoint.rebind':
        with kernel.db() as db:
            cp=verified(db,actor,args['id']);task=get(db,actor,'task',cp['task'])
            if task['latest']!=cp['id']:raise ValueError('REBIND_REQUIRES_LATEST_CHECKPOINT')
            new=capture_references(db,actor,[{'namespace':args['namespace'],'id':b['id']} for b in cp['references']])
            if any(any(a[k]!=b[k] for k in ('id','source_sha256','text_sha256','locator')) for a,b in zip(cp['references'],new)):raise ValueError('REBIND_REQUIRES_IDENTICAL_ORIGINAL_AND_LOCATOR')
            updated={**cp,'id':uuid.uuid4().hex,'previous':cp['id'],'created':time.time(),'references':new,'journal_cursor':db.execute('SELECT coalesce(max(seq),0) FROM activity_journal').fetchone()[0],'rebind':{'from':cp['id'],'reason':args['reason'],'authority':'EXPLICIT_OWNER_IDENTICAL_SOURCE_RELINK'}}
        return commit_checkpoint(kernel,actor,updated,cp['id'])
    with kernel.db() as db:
        if SCOPES[op]!='read':db.execute('BEGIN IMMEDIATE')
        if op=='memory.status':
            return {'schema':c.VERSION,'profile':profile_view(db,actor),'tasks':len(listing(db,actor,'task')),'lessons':len(listing(db,actor,'lesson')),'collection':'EXPLICIT_ONLY','weight_training':False,'cloud_disclosure':'NOT_GRANTED'}
        if op=='memory.profile':return profile_view(db,actor)
        if op=='memory.profile.import':
            raw=intake_files.read_stable(Path(args['path']),65536)
            try:expression=c.seed(raw)
            except ValueError as exc:raise ValueError('PERSONALITY_REFERENCE_FORMAT: choose a personality reference JSON file') from exc
            old=get(db,actor,'profile','current',True)
            p={'schema':c.VERSION,'original_b64':base64.b64encode(raw).decode(),'original_sha256':hashlib.sha256(raw).hexdigest(),'expression':expression,'enabled':True,'parameters':old['parameters'] if old else {'weights':c.WEIGHTS,'soft_half_life_days':90},'revision':old['revision']+1 if old else 1,'imported':time.time()}
            store(db,actor,'profile','current',p);event(db,actor,'PERSONALITY_REFERENCE_IMPORTED');return profile_view(db,actor)
        if op in ('memory.profile.enable','memory.profile.configure'):return commit_profile(db,actor,op,args)
        if op=='memory.profile.delete':
            db.execute("DELETE FROM stacy_memory WHERE owner=? AND kind IN ('profile','feedback')",(actor,));event(db,actor,'PROFILE_AND_FEEDBACK_DELETED');return {'state':'DELETED','task_memory_retained':True,'external_archive_deletion':'SEPARATE_OWNER_ACTION'}
        if op=='memory.preferences':
            p=get(db,actor,'profile','current',True);return {'context':args['context'],'preferences':c.posterior(listing(db,actor,'feedback'),args['context'],time.time(),p['parameters'] if p else None),'profile_context':profile_context(db,actor,args['context'])}
        if op=='memory.feedback.list':return {'events':listing(db,actor,'feedback')}
        if op=='memory.feedback':return commit_feedback(db,actor,args)
        if op in ('memory.feedback.undo','memory.feedback.forget'):
            value=get(db,actor,'feedback',c.ident(args['id']))
            if op.endswith('.undo'):value['undone']=True
            else:value={k:value[k] for k in ('id','input_digest','sequence','created')}|{'forgotten':True,'undone':False,'supersedes':[]}
            store(db,actor,'feedback',value['id'],value);event(db,actor,'FEEDBACK_REMOVED_FROM_ACTIVE_LEARNING');return value
        if op=='memory.task.create':
            value={'id':uuid.uuid4().hex,'title':c.text(args['title'],120,False),'created':time.time(),'latest':''};store(db,actor,'task',value['id'],value);event(db,actor,'TASK_CREATED');return value
        if op=='memory.tasks':return {'tasks':listing(db,actor,'task')}
        if op=='memory.task':
            task=get(db,actor,'task',c.ident(args['id']));return {**task,'checkpoints':[{k:cp[k] for k in ('id','previous','created','journal_cursor')} for cp in listing(db,actor,'checkpoint') if cp['task']==task['id'] and get(db,actor,'receipt',cp['id'],True)]}
        if op=='memory.checkpoint':
            cp=verified(db,actor,args['id']);transition=get(db,actor,'transition',cp['id'],True);return {**cp,'sha256':c.digest(cp),'historical_owner_notes':True,'verified_readback':True,'working_conversation':transition['conversation'] if transition else cp['conversation']}
        if op=='memory.conversation':
            value=conversation(db,actor,args['id']);return {'id':value['id'],'messages':len(value['messages']),'sha256':context_hash(value),'archived':value.get('context_archived',False)}
        if op=='memory.context.clear':
            cp=verified(db,actor,args['checkpoint']);old=get(db,actor,'transition',cp['id'],True)
            if old:return {**old,'duplicate':True}
            if not cp['conversation']:raise ValueError('CHECKPOINT_HAS_NO_CONVERSATION')
            dialogue=conversation(db,actor,cp['conversation'])
            if context_hash(dialogue)!=cp['transcript_digest'] or args['expected_context']!=cp['transcript_digest']:raise ValueError('CONTEXT_CHANGED_SAVE_NEW_CHECKPOINT')
            if any(j['owner']==actor and j['tool']=='brain.respond' and j['state'] in ('Running','Queued') for j in kernel.listing('jobs')):raise ValueError('WAIT_FOR_ACTIVE_REPLY_BEFORE_CONTEXT_TRANSITION')
            _,gaps=recheck_references(db,actor,cp['references'])
            if gaps:raise ValueError('SOURCE_CHANGED_KEEP_OLD_CONTEXT')
            new_id=uuid.uuid4().hex;dialogue.update(context_archived=True,successor=new_id);local_brain.put(kernel,'dialogue.'+dialogue['id'],dialogue,db=db)
            local_brain.put(kernel,'dialogue.'+new_id,{'id':new_id,'owner':actor,'messages':[],'created':time.time(),'checkpoint':cp['id']},db=db)
            value={'checkpoint':cp['id'],'old_conversation':dialogue['id'],'conversation':new_id,'old_context_preserved_in_private_history':True,'new_transcript_messages':0,'checkpoint_sha256':c.digest(cp)}
            store(db,actor,'transition',cp['id'],value);event(db,actor,'WORKING_CONTEXT_ROTATED_AFTER_READBACK');return value
        if op=='memory.lesson.propose':
            value={'id':uuid.uuid4().hex,'title':c.text(args['title'],120,False),'body':c.text(args['body'],1500,False),'references':capture_references(db,actor,args['references']),'review':'PROPOSED_UNREVIEWED','created':time.time()}
            store(db,actor,'lesson',value['id'],value);event(db,actor,'PROCEDURE_PROPOSED_NOT_APPROVED');return value
        if op=='memory.lesson.review':
            value=get(db,actor,'lesson',c.ident(args['id']));_,gaps=recheck_references(db,actor,value['references'])
            if args['approved'] and gaps:raise ValueError('REVIEW_REQUIRES_CURRENT_REFERENCE_ORIGINALS')
            value.update(review='OWNER_REVIEWED_PROCEDURE' if args['approved'] else 'REJECTED',reason=args['reason'],reviewed=time.time());store(db,actor,'lesson',value['id'],value);event(db,actor,'PROCEDURE_REVIEWED');return value
        if op=='memory.lessons':return {'lessons':reviewed_lessons(db,actor,args.get('query',''))}
    raise ValueError('MEMORY_OPERATION_UNKNOWN')
