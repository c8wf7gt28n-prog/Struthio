"""Dated authenticated private editions: memory, research and finite study data.

No jobs, grants, keys, model weights or source admissions are restored.
"""
from __future__ import annotations
import hashlib, hmac, io, re, secrets, time, zipfile
from pathlib import Path
from sdk.cli.arc1cli import record_store as records,intake_files
from . import study_service as study,memory_service as memory,research_service as research,intake_service as intake,activity
MAX=64*1024*1024

def export(kernel,owner,args):
    destination=memory.fresh_destination(kernel,args['destination'],'.zip');key_path=memory.fresh_destination(kernel,args['key_path'],'.key');members={};sources={};rows={}
    with kernel.db() as db:
        db.execute('BEGIN')
        for name,table,reader in [('memory','stacy_memory',memory.get),('research','stacy_research',research.get),('study','stacy_study',study.get)]:
            rows[name]=[{'kind':kind,'id':ident,'value':reader(db,owner,kind,ident)} for kind,ident in db.execute('SELECT kind,id FROM '+table+' WHERE owner=? ORDER BY kind,id',(owner,)) if not(name=='study' and kind=='presence')]
        bindings=[]
        for row in rows['memory']:
            if row['kind'] in ('checkpoint','lesson'):bindings.extend(row['value']['references'])
        for row in rows['study']:
            if row['kind']=='session':
                bindings.extend(row['value']['references'])
                if row['value'].get('procedure'):bindings.extend(t['reference'] for t in row['value']['procedure']['trials'])
        for row in rows['research']:
            if row['kind']=='request':bindings.extend(row['value']['bindings'])
            if row['kind']=='return':
                ident=row['id'];raw=(research.return_dir(kernel,owner)/(ident+'.zip')).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=row['value']['raw_archive_sha256']:raise ValueError('EDITION_RETURN_ORIGINAL_CHANGED')
                members['returns/'+ident+'.zip']=raw
        for b in bindings:
            if b['source_sha256'] in sources:continue
            try:
                ns=intake.namespace(db,b['namespace'],owner,True);item=intake.load(db,'items',b['item']);raw,_=intake.eligible(db,ns,item)
                if hashlib.sha256(raw).hexdigest()!=b['source_sha256']:raise ValueError('EDITION_SOURCE_CHANGED')
                suffix=Path(item['name']).suffix.lower()
                if not re.fullmatch(r'\.[a-z0-9]{1,12}',suffix):suffix='.bin'
                path='sources/'+b['source_sha256']+suffix;members[path]=raw;sources[b['source_sha256']]={'path':path,'sha256':b['source_sha256'],'original_name':item['name']}
            except (ValueError,OSError):continue
        if not any(rows.values()):raise ValueError('EDITION_EMPTY')
        body={'schema':'arc.stacy-private-edition/1','owner':owner,'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'rows':rows,'sources':list(sources.values()),'admissions_on_restore':0,'jobs_replayed':0,'idle_on_restore':False}
        members['EDITION.json']=records.canonical(body)
    if sum(map(len,members.values()))>MAX:raise ValueError('EDITION_BYTE_BUDGET')
    seal={'schema':'arc.stacy-edition-seal/1','members':{n:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for n,raw in members.items()}};manifest=records.canonical(seal);key=secrets.token_bytes(32);members['MANIFEST.json']=manifest;members['AUTH.txt']=hmac.new(key,manifest,hashlib.sha256).hexdigest().encode()
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for n,raw in sorted(members.items()):z.writestr(n,raw)
    raw=out.getvalue()
    if len(raw)>MAX:raise ValueError('EDITION_BYTE_BUDGET')
    # Two readbacks and index check happen before a caller can consider clearing context.
    verify(raw,key,owner)
    memory.publish(key_path,records.canonical({'schema':'arc.stacy-edition-key/1','key_hex':key.hex()}))
    try:memory.publish(destination,raw);verify(destination.read_bytes(),key,owner)
    except Exception:
        if not destination.exists():key_path.unlink(missing_ok=True)
        raise
    with kernel.db() as db:study.event(db,owner,'DATED_EDITION_SEALED_AND_READBACK_VERIFIED')
    return {'state':'SEALED','path':str(destination),'key_path':str(key_path),'sha256':hashlib.sha256(raw).hexdigest(),'created_utc':body['created_utc'],'source_copies':len(sources),'rows':{k:len(v) for k,v in rows.items()},'readbacks':2,'encrypted':False,'keep_key_separate':True,'context_cleared':False}

def verify(raw,key,owner):
    if len(raw)>MAX:raise ValueError('EDITION_BYTE_BUDGET')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            entries=intake_files.checked_zip(z)
            if len(entries)>12000 or sum(v.file_size for v in entries)>MAX:raise ValueError('EDITION_EXPANSION_BOUND')
            names={v.filename for v in entries}
            if not {'MANIFEST.json','AUTH.txt','EDITION.json'}<=names:raise ValueError('EDITION_REQUIRED_MEMBERS')
            manifest=z.read('MANIFEST.json');seal=records.strict(manifest)
            if set(seal)!={'schema','members'} or seal['schema']!='arc.stacy-edition-seal/1' or names!=set(seal['members'])|{'MANIFEST.json','AUTH.txt'}:raise ValueError('EDITION_MANIFEST')
            if not hmac.compare_digest(z.read('AUTH.txt'),hmac.new(key,manifest,hashlib.sha256).hexdigest().encode()):raise ValueError('EDITION_AUTHENTICATION_FAILED')
            members={n:z.read(n) for n in seal['members']}
        for n,b in members.items():
            if n!='EDITION.json' and not re.fullmatch(r'(sources/[a-f0-9]{64}\.[a-z0-9]{1,12}|returns/[a-f0-9]{64}\.zip)',n):raise ValueError('EDITION_MEMBER_NAME')
            if seal['members'][n]!={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}:raise ValueError('EDITION_MEMBER_CHANGED')
        value=records.strict(members['EDITION.json'])
        if not isinstance(value,dict) or value.get('schema')!='arc.stacy-private-edition/1' or value.get('owner')!=owner or set(value.get('rows',{}))!={'memory','research','study'}:raise ValueError('EDITION_OWNER_OR_SCHEMA')
        kinds={'memory':memory.KINDS,'research':{'policy','request','return','disclosure','usage'},'study':{'session','settings'}}
        bound={'memory':4000,'research':2000,'study':512};seen=set();cps={};receipts={}
        for name,rows in value['rows'].items():
            if not isinstance(rows,list) or len(rows)>bound[name]:raise ValueError('EDITION_ROW_BOUND')
            for r in rows:
                if not isinstance(r,dict) or set(r)!={'kind','id','value'} or r['kind'] not in kinds[name] or not isinstance(r['value'],dict) or not isinstance(r['id'],str) or len(r['id'])>64:raise ValueError('EDITION_ROW_SCHEMA')
                pair=(name,r['kind'],r['id'])
                if pair in seen:raise ValueError('EDITION_DUPLICATE_RECORD')
                seen.add(pair)
                if name=='memory':
                    if r['kind']=='profile':memory.original_seed(r['value'])
                    if r['kind']=='checkpoint':memory.c.note(r['value']['note']);cps[r['id']]=r['value']
                    if r['kind']=='receipt':receipts[r['id']]=r['value']
                elif name=='study':
                    if r['kind']=='settings':study.c.limits(r['value']['limits'])
                    else:
                        s=r['value'];study.c.limits(s['limits']);study.learning.ident(s['id'])
                        if s['id']!=r['id'] or not 0<=len(s['stages'])<=3:raise ValueError('EDITION_STUDY_SESSION')
                        for index,stage in enumerate(s['stages']):
                            if stage['stage']!=study.c.STAGES[index] or study.c.digest(stage['result'])!=stage['result_sha256']:raise ValueError('EDITION_STUDY_STAGE_DIGEST')
                elif r['kind']=='return':
                    path='returns/'+r['id']+'.zip'
                    if path not in members or hashlib.sha256(members[path]).hexdigest()!=r['value']['raw_archive_sha256']:raise ValueError('EDITION_RETURN_BINDING')
        for ident,r in receipts.items():
            if ident not in cps or r['sha256']!=study.c.digest(cps[ident]):raise ValueError('EDITION_CHECKPOINT_RECEIPT')
        sources=value['sources']
        if not isinstance(sources,list) or len(sources)>4000:raise ValueError('EDITION_SOURCE_BOUND')
        for s in sources:
            if set(s)!={'path','sha256','original_name'} or s['path'] not in members or not s['path'].startswith('sources/') or hashlib.sha256(members[s['path']]).hexdigest()!=s['sha256']:raise ValueError('EDITION_SOURCE_COPY')
        expected={'EDITION.json'}|{s['path'] for s in sources}|{'returns/'+r['id']+'.zip' for r in value['rows']['research'] if r['kind']=='return'}
        if set(members)!=expected:raise ValueError('EDITION_UNDECLARED_MEMBERS')
        return value,members
    except (zipfile.BadZipFile,KeyError,TypeError,UnicodeError,RecursionError) as exc:raise ValueError('EDITION_CORRUPT_OR_UNSUPPORTED') from exc

def restore(kernel,owner,args):
    raw=intake_files.read_stable(Path(args['path']),MAX)
    try:keydoc=records.strict(intake_files.read_stable(Path(args['key_path']),1024))
    except ValueError as exc:raise ValueError('EDITION_RECOVERY_KEY: choose the recovery key file saved with this edition') from exc
    if not isinstance(keydoc,dict) or set(keydoc)!={'schema','key_hex'} or keydoc['schema']!='arc.stacy-edition-key/1':raise ValueError('EDITION_RECOVERY_KEY')
    study.learning.ident(keydoc['key_hex'],64);value,members=verify(raw,bytes.fromhex(keydoc['key_hex']),owner)
    from .session import config_dir
    folder=config_dir()/'study_editions'/hashlib.sha256(owner.encode()).hexdigest()[:24]/hashlib.sha256(raw).hexdigest()[:24]
    if any(p.is_symlink() for p in (folder,*folder.parents)):raise ValueError('EDITION_LINKED_PATH')
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        for table in ('stacy_memory','stacy_research','stacy_study'):
            if db.execute('SELECT 1 FROM '+table+' WHERE owner=?',(owner,)).fetchone():raise ValueError('EDITION_REQUIRES_EMPTY_OWNER_PROFILE')
        for s in value['sources']:
            target=folder/Path(s['path']).name;target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():
                if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest()!=s['sha256']:raise ValueError('EDITION_RECOVERY_COLLISION')
            else:memory.publish(target,members[s['path']])
        for r in value['rows']['research']:
            if r['kind']=='return':
                target=research.return_dir(kernel,owner)/(r['id']+'.zip');target.parent.mkdir(parents=True,exist_ok=True)
                if any(p.is_symlink() for p in (target,*target.parents)):raise ValueError('EDITION_LINKED_RETURN_PATH')
                if target.exists():
                    if hashlib.sha256(target.read_bytes()).hexdigest()!=r['id']:raise ValueError('EDITION_RETURN_COLLISION')
                else:memory.publish(target,members['returns/'+r['id']+'.zip'])
        for name,writer in [('memory',memory.store),('research',research.put),('study',study.put)]:
            for r in value['rows'][name]:
                v=dict(r['value'])
                if name=='study':
                    if r['kind']=='settings':v['idle_enabled']=False;v['idle_session']=None
                    else:v.update(paused=True,active_job=None,reservation=None,pause_reason='RESTORED: re-admit identical source copies and explicitly rebind before resuming.');v['restored_from']=hashlib.sha256(raw).hexdigest()
                writer(db,owner,r['kind'],r['id'],v)
        study.event(db,owner,'EDITION_RESTORED_NO_ADMISSIONS_OR_JOBS_IDLE_OFF')
    return {'state':'RESTORED_HELD','source_copy_directory':str(folder),'rows':{k:len(v) for k,v in value['rows'].items()},'reference_admissions':0,'jobs_replayed':0,'idle_enabled':False,'research':'Historical returns retained; old bindings remain unavailable until separately reviewed new research requests.','next':'Intake review/index source copies, study.rebind on identical originals, then owner study.resume.'}

def dispatch(kernel,op,args,p):return export(kernel,p.identity,args) if op=='study.edition.export' else restore(kernel,p.identity,args)
