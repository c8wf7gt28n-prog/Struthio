"""Deterministic reference intake. All authority remains in the shared Kernel.

Originals live in private, content-addressed quarantine outside the program.
Acceptance is a reference decision, never source promotion or board qualification.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,time,uuid,zipfile,io,tempfile
from pathlib import Path
from sdk.cli.arc1cli import package_transport, intake_files as files,intake_profiles as profiles,record_store as records
from . import activity,record_io
from .session import config_dir
from . import locations

TEXT={'type':'string','minLength':1,'maxLength':4096}
ID={'type':'string','pattern':'^[0-9a-f]{32}$','maxLength':32}
SHA={'type':'string','pattern':'^[0-9a-f]{64}$','maxLength':64}
REASON={'type':'string','minLength':3,'maxLength':1000}
RECEIPT={'type':'string','pattern':'^(|[0-9a-f]{32})$','maxLength':32}
NS={'namespace':ID}
PAGE={'offset':{'type':'integer','minimum':0,'maximum':100000},'limit':{'type':'integer','minimum':1,'maximum':200}}
VARIANTS=('F133-B','D213ECV','ECP5-12F','ECP5-45F')
OPTIONS={'type':'object','additionalProperties':False,'properties':{
 'namespace':ID,'path':TEXT,'mode':{'type':'string','enum':['snapshot','external']},'batch':ID,
 'destination':TEXT,'expected_archive_sha256':SHA,'expected_generation':{'type':'integer','minimum':0}},'required':['namespace']}
FIELDS={
 'intake.status':({},[]),'intake.namespaces':({},[]),
 'intake.namespace.create':({'name':{'type':'string','pattern':'^[A-Za-z0-9][A-Za-z0-9 _-]{0,63}$'}},['name']),
 'intake.namespace.grant':({**NS,'reader':{'type':'string','minLength':1,'maxLength':128},'enabled':{'type':'boolean'}},['namespace','reader','enabled']),
 'intake.policy':(NS,['namespace']),
 'intake.policy.set':({**NS,'auto_profiles':{'type':'array','items':{'type':'string','enum':list(profiles.AUTO_PROFILES)},'maxItems':5,'uniqueItems':True},
     'variants':{'type':'array','items':{'type':'string','enum':list(VARIANTS)},'maxItems':4,'uniqueItems':True},
     'scope':{'type':'string','enum':['current','historical']},'reason':REASON,'expected_policy_hash':SHA},['namespace','auto_profiles','variants','scope','reason','expected_policy_hash']),
 'intake.import':({**NS,'path':TEXT,'mode':{'type':'string','enum':['snapshot','external']},'request_key':TEXT},['namespace','path']),
 'intake.batches':({**NS,**PAGE},['namespace']),
 'intake.items':({**NS,**PAGE,'batch':ID,'state':{'type':'string','enum':['UNREVIEWED','ACCEPTED','HELD','REJECTED','REVOKED']}},['namespace']),
 'intake.item':({'id':ID},['id']),
 'intake.review':({**NS,'batch':ID,'request_key':TEXT},['namespace','batch']),
 'intake.decide':({'id':ID,'decision':{'type':'string','enum':['ACCEPTED','HELD','REJECTED']},'expected_sha256':SHA,
      'expected_policy_hash':SHA,'expected_decision':RECEIPT,'reason':REASON},['id','decision','expected_sha256','expected_policy_hash','expected_decision','reason']),
 'intake.revoke':({'id':ID,'expected_decision':ID,'reason':REASON},['id','expected_decision','reason']),
 'intake.bundle.decide':({**NS,'items':{'type':'array','items':ID,'minItems':1,'maxItems':50,'uniqueItems':True},'expected_generation':{'type':'integer','minimum':0},'expected_policy_hash':SHA,'reason':REASON},['namespace','items','expected_generation','expected_policy_hash','reason']),
 'intake.catalog':({**NS,**PAGE,'include_historical':{'type':'boolean'}},['namespace']),
 'intake.search':({**NS,'query':{'type':'string','minLength':1,'maxLength':300},'include_historical':{'type':'boolean'},'limit':{'type':'integer','minimum':1,'maximum':50}},['namespace','query']),
 'intake.read':({'id':ID,'include_historical':{'type':'boolean'}},['id']),
 'intake.packet.create':({**NS,'items':{'type':'array','items':ID,'minItems':1,'maxItems':25,'uniqueItems':True}},['namespace','items']),
 'intake.packet':({'id':ID},['id']),
 'intake.checkpoint':({**NS,'label':{'type':'string','minLength':1,'maxLength':100}},['namespace','label']),
 'intake.checkpoints':(NS,['namespace']),
 'intake.catalog.restore':({'id':ID,'expected_generation':{'type':'integer','minimum':0},'reason':REASON},['id','expected_generation','reason']),
 'intake.recover':(NS,['namespace']),
 'intake.export':({**NS,'destination':TEXT,'expected_generation':{'type':'integer','minimum':0},'request_key':TEXT},['namespace','destination','expected_generation'])}
READS={'intake.status','intake.namespaces','intake.policy','intake.batches','intake.items','intake.catalog','intake.search','intake.read','intake.packet','intake.checkpoints'}
EXECUTES={'intake.review','intake.packet.create','intake.checkpoint','intake.recover'}
SCOPES={op:'read' if op in READS else 'execute' if op in EXECUTES else 'approve' for op in FIELDS}
JOB_TOOLS={'intake.scan','intake.review','intake.export'}

def encoded(value):return records.canonical(value).decode()
def fingerprint():
    h=hashlib.sha256()
    for path in (Path(__file__),Path(files.__file__),Path(profiles.__file__),Path(package_transport.__file__)):h.update(path.read_bytes())
    return h.hexdigest()

def ensure(db):
    for statement in (
      'CREATE TABLE IF NOT EXISTS intake_namespaces(id TEXT PRIMARY KEY,owner TEXT,generation INTEGER,payload TEXT)',
      'CREATE TABLE IF NOT EXISTS intake_batches(id TEXT PRIMARY KEY,ns TEXT,state TEXT,payload TEXT)',
      'CREATE TABLE IF NOT EXISTS intake_items(id TEXT PRIMARY KEY,batch TEXT,ns TEXT,name TEXT,admission TEXT,payload TEXT)',
      'CREATE INDEX IF NOT EXISTS intake_item_lookup ON intake_items(ns,batch,name)',
      'CREATE TABLE IF NOT EXISTS intake_decisions(id TEXT PRIMARY KEY,item TEXT,ns TEXT,payload TEXT)',
      'CREATE TABLE IF NOT EXISTS intake_catalog(ns TEXT,name TEXT,item TEXT UNIQUE,decision TEXT,PRIMARY KEY(ns,name))',
      'CREATE TABLE IF NOT EXISTS intake_packets(id TEXT PRIMARY KEY,ns TEXT,state TEXT,payload TEXT)',
      'CREATE TABLE IF NOT EXISTS intake_checkpoints(id TEXT PRIMARY KEY,ns TEXT,payload TEXT)'):
        db.execute(statement)
    # Standard SQLite builds have FTS5. The fallback preserves launch and ACLs.
    try:db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS intake_search USING fts5(item UNINDEXED,ns UNINDEXED,body)')
    except Exception:db.execute('CREATE TABLE IF NOT EXISTS intake_search(item TEXT,ns TEXT,body TEXT)')

def load(db,table,ident):
    if table not in ('namespaces','batches','items','decisions','packets','checkpoints'):raise ValueError('INTAKE_TABLE')
    row=db.execute('SELECT payload FROM intake_'+table+' WHERE id=?',(ident,)).fetchone()
    if not row:raise ValueError('INTAKE_RECORD_NOT_FOUND')
    return json.loads(row[0])

def namespace(db,ident,actor,owner=False):
    value=load(db,'namespaces',ident)
    if value['owner']!=actor and (owner or actor not in value['readers']):raise ValueError('PRIVATE_NAMESPACE_ACCESS_DENIED')
    return value

def save_namespace(db,value):
    db.execute('INSERT OR REPLACE INTO intake_namespaces VALUES(?,?,?,?)',(value['id'],value['owner'],value['generation'],encoded(value)))

def save_batch(db,value):
    db.execute('INSERT OR REPLACE INTO intake_batches VALUES(?,?,?,?)',(value['id'],value['namespace'],value['state'],encoded(value)))

def save_item(db,value):
    db.execute('INSERT OR REPLACE INTO intake_items VALUES(?,?,?,?,?,?)',(value['id'],value['batch'],value['namespace'],value['name'],value['admission'],encoded(value)))

def policy_hash(policy):return hashlib.sha256(records.canonical(policy)).hexdigest()
def current_policy(ns):
    if ns['policy']['rule_hash']!=fingerprint():raise ValueError('INTAKE_RULES_CHANGED_REVIEW_POLICY_REQUIRED')
    return policy_hash(ns['policy'])

def vault(ns):return files.Vault(config_dir()/'libraries'/hashlib.sha256(ns['owner'].encode()).hexdigest()[:24]/'quarantine')
def event(db,actor,state,ns):
    activity.append(db,activity.make_event(actor,'intake.decision',state,source_generation=str(ns['generation'])))

def public_namespace(value):
    return {k:value[k] for k in ('id','name','owner','generation','readers','policy')}
def public_batch(value):
    return {k:value.get(k) for k in ('id','namespace','state','job','files','runtime_resources_retained','created','source_generation','failure')}
def item_summary(value):
    return {k:value.get(k) for k in ('id','batch','namespace','name','sha256','bytes','profile','admission','decision_id','reasons','qualification','working_version','duplicate_of')}

def rows_in_batch(db,batch):return [json.loads(r[0]) for r in db.execute('SELECT payload FROM intake_items WHERE batch=? ORDER BY name',(batch,))]

def original(db,ns,item,checked=None):
    batch=load(db,'batches',item['batch'])
    if batch['state']!='READY':raise ValueError('INTAKE_BATCH_NOT_READY')
    if batch['source']['mode']=='external' and (checked is None or batch['id'] not in checked):
        files.verify_source(batch['source'],rows_in_batch(db,batch['id']),vault(ns))
        if checked is not None:checked.add(batch['id'])
    return vault(ns).read(item['sha256'])

def assess(db,ns,item,checked=None,pending=None):
    raw=original(db,ns,item,checked)
    available={r['name']:r for r in rows_in_batch(db,item['batch'])}
    result=parse(ns,item,raw,available)
    result['rule_hash']=fingerprint();deps=[]
    for dep in result['dependencies']:
        target=available.get(dep['path'])
        row={**dep,'item':target['id'] if target else None,'sha256':target['sha256'] if target else None,'decision':target.get('decision_id') if target else None}
        deps.append(row)
        if target:
            if pending and target['id'] in pending:
                row['decision']=pending[target['id']];original(db,ns,target,checked);continue
            try:eligible(db,ns,target,checked=checked)
            except ValueError:
                result['eligible']=False
                if result['recommendation']!='REJECTED':result['recommendation']='HELD'
                result['reasons'].append('DEPENDENCY_NOT_ADMITTED: '+dep['path'])
    result['dependencies']=deps
    conflict=db.execute('SELECT item FROM intake_catalog WHERE ns=? AND name=?',(ns['id'],item['name'])).fetchone()
    if conflict and conflict[0]!=item['id']:
        result['eligible']=False;result['recommendation']='HELD';result['reasons'].append('CURRENT_CATALOG_PATH_CONFLICT')
    return result

def parse(ns,item,raw,available):
    if profiles.profile_for(item['name']) in ('pdf_document','image_reference'):
        return profiles.inspect_optional(item['name'],vault(ns).path(item['sha256']),item['sha256'],available,ns['policy']['variants'],ns['policy']['scope'])
    return profiles.evaluate(item['name'],raw,available,ns['policy']['variants'],ns['policy']['scope'])

def eligible(db,ns,item,seen=None,checked=None,include_historical=True):
    expected=current_policy(ns)
    if not include_historical and ns['policy']['scope']=='historical':raise ValueError('HISTORICAL_REFERENCE_EXCLUDED')
    row=db.execute('SELECT decision FROM intake_catalog WHERE item=? AND ns=?',(item['id'],ns['id'])).fetchone()
    if not row or item['admission']!='ACCEPTED' or row[0]!=item.get('decision_id'):raise ValueError('REFERENCE_NOT_CURRENTLY_ADMITTED')
    receipt=load(db,'decisions',row[0])
    if receipt['policy_hash']!=expected or receipt['rule_hash']!=fingerprint():raise ValueError('REFERENCE_POLICY_OR_RULES_STALE')
    seen=set() if seen is None else set(seen)
    if item['id'] in seen:return original(db,ns,item,checked),receipt
    if len(seen)>=128:raise ValueError('REFERENCE_DEPENDENCY_DEPTH_LIMIT')
    seen.add(item['id']);raw=original(db,ns,item,checked)
    for dep in receipt['assessment']['dependencies']:
        target=load(db,'items',dep['item'])
        if target.get('decision_id')!=dep['decision'] or target['sha256']!=dep['sha256']:raise ValueError('REFERENCE_DEPENDENCY_RECEIPT_STALE')
        eligible(db,ns,target,seen,checked)
    return raw,receipt

def stale_packets(db,ns,items=None):
    for row in db.execute('SELECT payload FROM intake_packets WHERE ns=? AND state=?',(ns['id'],'CURRENT')).fetchall():
        packet=json.loads(row[0])
        if items is None or any(v['id'] in items for v in packet['inputs']):
            packet.update(state='STALE',stale_reason='ADMISSION_OR_POLICY_CHANGED')
            db.execute('UPDATE intake_packets SET state=?,payload=? WHERE id=?',('STALE',encoded(packet),packet['id']))

def remove_admission(db,ns,item):
    db.execute('DELETE FROM intake_catalog WHERE item=?',(item['id'],))
    db.execute('DELETE FROM intake_search WHERE item=?',(item['id'],))
    stale_packets(db,ns,{item['id']})

def receipt(db,ns,item,decision,reason,actor,assessment,automatic=False,ident=None):
    previous=item.get('decision_id');remove_admission(db,ns,item)
    ns['generation']+=1
    result={'schema':'arc.intake-decision/1','id':ident or uuid.uuid4().hex,'item':item['id'],'namespace':ns['id'],
      'actor':actor,'automatic':automatic,'decision':decision,'reason':reason,'at':time.time(),
      'input_sha256':item['sha256'],'source_generation':load(db,'batches',item['batch'])['source_generation'],
      'policy_hash':policy_hash(ns['policy']),'rule_version':profiles.VERSION,'rule_hash':fingerprint(),
      'assessment':{k:v for k,v in assessment.items() if k!='index_text'},'previous_decision':previous,'catalog_generation':ns['generation'],
      'working_version':1,'qualification':assessment.get('qualification',{}),'source_promotion':'NOT_GRANTED'}
    db.execute('INSERT INTO intake_decisions VALUES(?,?,?,?)',(result['id'],item['id'],ns['id'],encoded(result)))
    item.update(admission=decision,decision_id=result['id'],profile=assessment.get('profile',profiles.profile_for(item['name'])),
        reasons=assessment.get('reasons',[]),qualification=result['qualification'],working_version=1)
    save_item(db,item);save_namespace(db,ns)
    if decision=='ACCEPTED':
        used=db.execute('SELECT coalesce(sum(length(body)),0) FROM intake_search WHERE ns=?',(ns['id'],)).fetchone()[0]
        if used+len(assessment.get('index_text',''))>64*1024*1024:raise ValueError('INTAKE_INDEX_RESOURCE_LIMIT')
        db.execute('INSERT INTO intake_catalog VALUES(?,?,?,?)',(ns['id'],item['name'],item['id'],result['id']))
        db.execute('INSERT INTO intake_search(item,ns,body) VALUES(?,?,?)',(item['id'],ns['id'],assessment.get('index_text','')))
    event(db,actor,decision,ns)
    return result

def cascade(db,ns,changed,actor):
    pending={changed}
    while pending:
        last=pending;pending=set()
        for row in db.execute('SELECT i.payload FROM intake_items i JOIN intake_catalog c ON c.item=i.id WHERE c.ns=?',(ns['id'],)).fetchall():
            item=json.loads(row[0]);prior=load(db,'decisions',item['decision_id'])
            if any(dep['item'] in last for dep in prior['assessment']['dependencies']):
                assessment={**prior['assessment'],'eligible':False,'recommendation':'HELD','reasons':['DEPENDENCY_ADMISSION_REVERSED']}
                receipt(db,ns,item,'HELD','Dependency admission changed; reevaluation required',actor,assessment)
                pending.add(item['id'])

def decide(db,ns,item,args,actor,automatic=False,checked=None):
    if item['sha256']!=args['expected_sha256'] or item.get('decision_id','')!=args['expected_decision']:raise ValueError('INTAKE_ITEM_REVIEW_CHANGED_REFRESH_REQUIRED')
    if current_policy(ns)!=args['expected_policy_hash']:raise ValueError('INTAKE_POLICY_CHANGED_REFRESH_REQUIRED')
    assessment=assess(db,ns,item,checked)
    decision=args['decision']
    if decision=='ACCEPTED' and not assessment['eligible']:raise ValueError('INTAKE_NOT_ELIGIBLE: '+ '; '.join(assessment['reasons']))
    if automatic and decision=='ACCEPTED' and assessment['profile'] not in ns['policy']['auto_profiles']:raise ValueError('AUTO_ADMISSION_NOT_GRANTED')
    prior=item['admission'];result=receipt(db,ns,item,decision,args['reason'],actor,assessment,automatic)
    if prior=='ACCEPTED':cascade(db,ns,item['id'],actor)
    return result

def begin(db):db.execute('BEGIN IMMEDIATE')

def authorize_job(kernel,tool,options,principal):
    if tool not in JOB_TOOLS:raise ValueError('INTAKE_JOB_NOT_REGISTERED')
    if tool in ('intake.scan','intake.export') and 'approve' not in principal.scopes:raise ValueError('INTAKE_IMPORT_EXPORT_REQUIRE_OWNER_APPROVAL')
    required={'intake.scan':{'namespace','path'},'intake.review':{'namespace','batch'},'intake.export':{'namespace','destination','expected_generation'}}[tool]
    allowed=required|({'mode','expected_archive_sha256'} if tool=='intake.scan' else set())
    if not required.issubset(options) or set(options)-allowed:raise ValueError('INTAKE_JOB_OPTIONS')
    with kernel.db() as db:
        ns=namespace(db,options['namespace'],principal.identity,owner=True);current_policy(ns)
        if tool=='intake.review' and load(db,'batches',options['batch'])['namespace']!=ns['id']:raise ValueError('INTAKE_BATCH_NAMESPACE_MISMATCH')
        if tool=='intake.export' and options['expected_generation']!=ns['generation']:raise ValueError('INTAKE_CATALOG_CHANGED_REFRESH_REQUIRED')

def submit(kernel,tool,args,principal):
    options={k:v for k,v in args.items() if k!='request_key'}
    return kernel.submit({'tool':tool,'intake':options,'request_key':args.get('request_key',uuid.uuid4().hex),'timeout':600},principal)

def scan(kernel,job):
    options=job['request_spec']['intake'];ident=hashlib.sha256((job['owner']+job['id']).encode()).hexdigest()[:32]
    with kernel.db() as db:
        begin(db);ns=namespace(db,options['namespace'],job['owner'],True)
        batch={'id':ident,'namespace':ns['id'],'state':'SCANNING','job':job['id'],'created':time.time(),'files':0}
        save_batch(db,batch);event(db,job['owner'],'SCAN_STARTED',ns)
    try:
        config=records.strict((locations.program(kernel.root)/'MANIFEST.json').read_bytes()) if (locations.program(kernel.root)/'MANIFEST.json').exists() else {}
        # The pinned seal is program-owned configuration; an imported file cannot assert it.
        pinned=config.get('archive_sha256')
        if not pinned and (kernel.root/'PROGRAM_MANIFEST.json').exists():pinned=records.strict((kernel.root/'PROGRAM_MANIFEST.json').read_bytes()).get('archive_sha256')
        inspection=None
        if Path(options['path']).suffix.lower()=='.zip':
            from .package_service import inspect_path
            _,inspection=inspect_path(options['path'],lambda:kernel.record('jobs',job['id']).get('cancel',False))
            if inspection['state']!='READY':raise ValueError('PACKAGE_PREFLIGHT_'+inspection['state']+': '+', '.join(inspection['issues']))
        if options.get('expected_archive_sha256') and (not inspection or inspection['sha256']!=options['expected_archive_sha256']):raise ValueError('PACKAGE_CHANGED_INSPECT_AGAIN')
        # A separate workspace is not the program, but its live state must never be swept into a snapshot.
        if kernel.state.resolve().is_relative_to(Path(options['path']).expanduser().resolve()):raise ValueError('INTAKE_SOURCE_CONTAINS_LEDGER_STATE: choose a folder that does not hold .ledger')
        result=files.snapshot(options['path'],vault(ns),options.get('mode','snapshot'),pinned_archive=pinned,
             cancelled=lambda:kernel.record('jobs',job['id']).get('cancel',False),program_root=locations.program(kernel.root))
        if inspection and result['source'].get('sha256')!=inspection['sha256']:raise ValueError('PACKAGE_CHANGED_DURING_COPY')
        with kernel.db() as db:
            begin(db);ns=namespace(db,ns['id'],job['owner'],True)
            batch.update(state='READY',source=result['source'],source_generation=result['source']['manifest_sha256'],
                         files=len(result['items']),runtime_resources_retained=result['runtime_resources_retained'])
            for row in result['items']:
                item_id=hashlib.sha256((ident+row['name']+row['sha256']).encode()).hexdigest()[:32]
                duplicate=db.execute('SELECT id FROM intake_items WHERE ns=? AND json_extract(payload,\'$.sha256\')=? LIMIT 1',(ns['id'],row['sha256'])).fetchone()
                save_item(db,{**row,'id':item_id,'namespace':ns['id'],'batch':ident,'profile':profiles.profile_for(row['name']),
                    'admission':'UNREVIEWED','decision_id':'','reasons':[],'duplicate_of':duplicate[0] if duplicate else None})
            save_batch(db,batch);event(db,job['owner'],'SCAN_READY',ns)
        return {'status':'READY','batch':public_batch(batch),'accepted':0,'source_promotion':'NOT_GRANTED'}
    except Exception as exc:
        with kernel.db() as db:
            begin(db);batch.update(state='INTERRUPTED' if 'CANCELLED' in str(exc) else 'FAILED',failure=activity.redact(exc));save_batch(db,batch);event(db,job['owner'],batch['state'],ns)
        raise

def review(kernel,job):
    opts=job['request_spec']['intake'];checked=set();counts={'ACCEPTED':0,'HELD':0,'REJECTED':0}
    with kernel.db() as db:
        ns=namespace(db,opts['namespace'],job['owner'],True);batch=load(db,'batches',opts['batch']);current_policy(ns)
        if batch['namespace']!=ns['id'] or batch['state']!='READY':raise ValueError('INTAKE_BATCH_NOT_READY')
        pending=[v['id'] for v in rows_in_batch(db,batch['id']) if v['admission']!='ACCEPTED']
    # Dependencies resolve in bounded topological rounds. Cycles stay held.
    for turn in range(min(100,len(pending)+1)):
        again=[];progress=False
        for ident in pending:
            if kernel.record('jobs',job['id']).get('cancel'):raise ValueError('INTAKE_CANCELLED')
            with kernel.db() as db:
                begin(db);ns=namespace(db,ns['id'],job['owner'],True);item=load(db,'items',ident);current_policy(ns)
                if item['admission']=='ACCEPTED':continue
                try:assessment=assess(db,ns,item,checked)
                except (ValueError,OSError) as exc:assessment=profiles.held(item['profile'],activity.redact(exc))
                decision='ACCEPTED' if assessment['eligible'] and assessment['profile'] in ns['policy']['auto_profiles'] else 'REJECTED' if assessment['recommendation']=='REJECTED' else 'HELD'
                dependency_wait=any(r.startswith('DEPENDENCY_NOT_ADMITTED') for r in assessment['reasons'])
                if dependency_wait and turn<min(99,len(pending)):
                    again.append(ident);continue
                if decision=='HELD' and assessment['eligible']:assessment['reasons'].append('OWNER_REVIEW_REQUIRED')
                prior=load(db,'decisions',item['decision_id']) if item.get('decision_id') else None
                if prior and prior['decision']==decision and prior['policy_hash']==policy_hash(ns['policy']) and prior['assessment']=={k:v for k,v in assessment.items() if k!='index_text'}:continue
                receipt(db,ns,item,decision,'Deterministic review under owner policy',job['owner'],assessment,automatic=True)
                counts[decision]+=1;progress|=decision=='ACCEPTED'
        if not again:break
        if not progress:
            for ident in again:
                with kernel.db() as db:
                    begin(db);ns=namespace(db,ns['id'],job['owner'],True);item=load(db,'items',ident)
                    assessment=assess(db,ns,item,checked);receipt(db,ns,item,'HELD','Dependency admission incomplete or cyclic',job['owner'],assessment,True);counts['HELD']+=1
            break
        pending=again
    return {'status':'REVIEWED','batch':batch['id'],'decisions':counts,'native_checks':'NOT_RUN','source_promotion':'NOT_GRANTED'}

def catalog(db,ns,include_historical=False):
    result=[];unavailable=[];checked=set()
    for row in db.execute('SELECT i.payload FROM intake_catalog c JOIN intake_items i ON c.item=i.id WHERE c.ns=? ORDER BY c.name',(ns['id'],)).fetchall():
        item=json.loads(row[0])
        try:eligible(db,ns,item,checked=checked,include_historical=include_historical);result.append(item)
        except (ValueError,OSError) as exc:unavailable.append({'id':item['id'],'name':item['name'],'reason':activity.redact(exc)})
    return result,unavailable

def read_reference(db,ns,item,include_historical=False):
    raw,decision=eligible(db,ns,item,include_historical=include_historical)
    # Reparse the verified bytes rather than trusting cached snippets as originals.
    available={v['name']:v for v in rows_in_batch(db,item['batch'])}
    parsed=parse(ns,item,raw,available)
    if not parsed['eligible']:raise ValueError('REFERENCE_PARSER_NO_LONGER_ELIGIBLE')
    return {'id':item['id'],'name':item['name'],'sha256':item['sha256'],'decision':decision['id'],'working_version':1,
        'locator':{'kind':'FILE_PREVIEW','path':item['name'],'preview_truncated':parsed.get('index_preview_truncated',False)},
        'text':parsed['index_text'],'qualification':decision['qualification'],'content_trust':'UNTRUSTED_REFERENCE_DATA'}

def packet_status(db,ns,packet):
    if packet['state']=='CURRENT':
        try:
            if packet['policy_hash']!=current_policy(ns):raise ValueError('PACKET_POLICY_STALE')
            for row in packet['inputs']:
                item=load(db,'items',row['id'])
                if row['decision']!=item.get('decision_id') or row['sha256']!=item['sha256']:raise ValueError('PACKET_INPUT_STALE')
                eligible(db,ns,item)
        except (ValueError,OSError):
            packet.update(state='STALE',stale_reason='SOURCE_OR_ADMISSION_UNAVAILABLE')
            db.execute('UPDATE intake_packets SET state=?,payload=? WHERE id=?',('STALE',encoded(packet),packet['id']))
    return {**packet,'content':None if packet['state']!='CURRENT' else packet['content']}

def export_catalog(kernel,job):
    opts=job['request_spec']['intake'];destination=Path(opts['destination']).expanduser().absolute()
    if any(p.is_symlink() for p in (destination,*destination.parents)):raise ValueError('INTAKE_EXPORT_LINKED_PATH')
    destination=destination.resolve()
    with kernel.db() as db:
        begin(db);ns=namespace(db,opts['namespace'],job['owner'],True)
        if ns['generation']!=opts['expected_generation']:raise ValueError('INTAKE_CATALOG_CHANGED_REFRESH_REQUIRED')
        selected,unavailable=catalog(db,ns,True)
        if unavailable:raise ValueError('INTAKE_EXPORT_HAS_UNAVAILABLE_REFERENCES')
        if not selected:raise ValueError('INTAKE_EXPORT_EMPTY')
        if destination.suffix.lower()!='.zip' or destination.exists() or destination.is_relative_to(kernel.root) or destination.is_relative_to(config_dir()):raise ValueError('INTAKE_EXPORT_DESTINATION_MUST_BE_NEW_EXTERNAL_ZIP')
        if any(p.is_symlink() for p in (destination,*destination.parents)):raise ValueError('INTAKE_EXPORT_LINKED_PATH')
        for row in db.execute('SELECT payload FROM intake_batches WHERE ns=?',(ns['id'],)):
            source=json.loads(row[0]).get('source',{});origin=Path(source.get('origin','/nonexistent')).resolve()
            if destination.resolve()==origin or source.get('origin_kind')=='folder' and destination.resolve().is_relative_to(origin):raise ValueError('INTAKE_EXPORT_CANNOT_REPLACE_ORIGINAL')
        output=io.BytesIO();manifest={'schema':'arc.accepted-reference-catalog/1','edition':1,'namespace':ns['name'],'generation':ns['generation'],
            'encryption':'NONE','dependency_status':'CHECKED_WITH_ACCEPTED_CATALOG','policy_hash':current_policy(ns),'legacy_working_history':'NOT_IMPORTED','source_promotion':'NOT_GRANTED','files':{}}
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
            total=0
            for item in selected:
                if kernel.record('jobs',job['id']).get('cancel'):raise ValueError('INTAKE_CANCELLED')
                raw,decision=eligible(db,ns,item);total+=len(raw)
                if total>files.MAX_BUNDLE:raise ValueError('INTAKE_EXPORT_RESOURCE_LIMIT')
                archive.writestr('V1/originals/'+item['name'],raw)
                clean={k:v for k,v in decision.items() if k not in ('actor','previous_decision')}
                clean['assessment']={k:v for k,v in clean['assessment'].items() if k!='index_text'}
                archive.writestr('V1/decisions/'+item['id']+'.json',records.canonical(clean))
                manifest['files'][item['name']]={'sha256':item['sha256'],'bytes':len(raw),'working_version':1,'decision':decision['id'],'qualification':decision['qualification']}
            archive.writestr('V1/catalog.json',records.canonical(manifest))
        raw=output.getvalue()
        checked=package_transport.inspect_bytes(raw,'catalog.zip',lambda:kernel.record('jobs',job['id']).get('cancel',False))
        if checked['state']!='READY' or checked['transport']['state']!='VERIFIED':raise ValueError('INTAKE_EXPORT_TRANSPORT_READBACK_FAILED')
        # Publish complete bytes atomically, without replacing any destination.
        destination.parent.mkdir(parents=True,exist_ok=True)
        fd,temporary=tempfile.mkstemp(prefix='.arc-v1-export-',dir=destination.parent);temporary=Path(temporary);linked=False
        try:
            with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
            if records.sha(temporary)!=hashlib.sha256(raw).hexdigest():raise ValueError('INTAKE_EXPORT_READBACK_FAILED')
            if kernel.record('jobs',job['id']).get('cancel'):raise ValueError('INTAKE_CANCELLED')
            os.link(temporary,destination);linked=True
            event(db,job['owner'],'V1_EXPORTED',ns)
        except Exception:
            if linked and destination.exists() and os.path.samefile(temporary,destination):destination.unlink()
            raise
        finally:temporary.unlink(missing_ok=True)
    return {'status':'EXPORTED','files':len(selected),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'edition':1,'encryption':'NONE','transport':checked['transport']}

def dispatch(kernel,op,args,principal):
    actor=principal.identity
    if op in ('intake.import','intake.review','intake.export'):
        return submit(kernel,{'intake.import':'intake.scan','intake.review':'intake.review','intake.export':'intake.export'}[op],args,principal)
    with kernel.db() as db:
        if op not in READS:begin(db)
        if op=='intake.status':
            owned=[json.loads(r[0]) for r in db.execute('SELECT payload FROM intake_namespaces WHERE owner=?',(actor,))]
            return {'schema':'arc.intake/1','state':'READY','namespaces':len(owned),'automatic_admission':'OWNER_POLICY_REQUIRED',
              'project_attachment':'UNCHANGED','qualification':'SOURCE_REFERENCES_ONLY','rule_hash':fingerprint()}
        if op=='intake.namespaces':
            return {'namespaces':[public_namespace(v) for r in db.execute('SELECT payload FROM intake_namespaces') if (v:=json.loads(r[0]))['owner']==actor or actor in v['readers']]}
        if op=='intake.namespace.create':
            ident=hashlib.sha256((actor+'\0'+args['name']).encode()).hexdigest()[:32]
            if db.execute('SELECT 1 FROM intake_namespaces WHERE id=?',(ident,)).fetchone():return public_namespace(namespace(db,ident,actor,True))
            value={'id':ident,'name':args['name'],'owner':actor,'readers':[],'generation':0,
              'policy':{'schema':'arc.intake-policy/1','auto_profiles':[],'variants':list(VARIANTS),'scope':'current','rule_version':profiles.VERSION,'rule_hash':fingerprint()}}
            save_namespace(db,value);event(db,actor,'NAMESPACE_CREATED',value);return public_namespace(value)
        item=None
        if op in ('intake.item','intake.decide','intake.revoke','intake.read'):
            item=load(db,'items',args['id']);ns=namespace(db,item['namespace'],actor,owner=op!='intake.read')
        elif op=='intake.packet':
            packet=load(db,'packets',args['id']);ns=namespace(db,packet['namespace'],actor);return packet_status(db,ns,packet)
        elif op=='intake.catalog.restore':
            checkpoint=load(db,'checkpoints',args['id']);ns=namespace(db,checkpoint['namespace'],actor,True)
        else:ns=namespace(db,args['namespace'],actor,owner=op not in READS)
        if op=='intake.namespace.grant':
            ns['readers']=sorted((set(ns['readers'])|{args['reader']}) if args['enabled'] else (set(ns['readers'])-{args['reader']}))
            save_namespace(db,ns);event(db,actor,'READ_ACCESS_CHANGED',ns);return public_namespace(ns)
        if op=='intake.policy':return {**ns['policy'],'policy_hash':policy_hash(ns['policy']),'rules_current':ns['policy']['rule_hash']==fingerprint()}
        if op=='intake.policy.set':
            if policy_hash(ns['policy'])!=args['expected_policy_hash']:raise ValueError('INTAKE_POLICY_CHANGED_REFRESH_REQUIRED')
            ns['policy']={**ns['policy'],**{k:args[k] for k in ('auto_profiles','variants','scope')},'rule_hash':fingerprint()};ns['generation']+=1
            # Existing admissions must be explicitly reevaluated under the new policy.
            for row in db.execute('SELECT payload FROM intake_items WHERE ns=? AND admission=?',(ns['id'],'ACCEPTED')).fetchall():
                value=json.loads(row[0]);prior=load(db,'decisions',value['decision_id']);assessment={**prior['assessment'],'eligible':False,'reasons':['POLICY_CHANGED_REVIEW_REQUIRED']}
                receipt(db,ns,value,'HELD',args['reason'],actor,assessment)
            stale_packets(db,ns);save_namespace(db,ns);event(db,actor,'POLICY_CHANGED',ns)
            return {**ns['policy'],'policy_hash':policy_hash(ns['policy'])}
        if op=='intake.batches':
            values=[public_batch(json.loads(r[0])) for r in db.execute('SELECT payload FROM intake_batches WHERE ns=? ORDER BY rowid DESC',(ns['id'],))]
            return {'total':len(values),'batches':values[args.get('offset',0):args.get('offset',0)+args.get('limit',100)]}
        if op=='intake.items':
            clauses=['ns=?'];params=[ns['id']]
            for key,column in (('batch','batch'),('state','admission')):
                if key in args:clauses.append(column+'=?');params.append(args[key])
            where=' AND '.join(clauses)
            total=db.execute('SELECT count(*) FROM intake_items WHERE '+where,params).fetchone()[0]
            values=[item_summary(json.loads(r[0])) for r in db.execute('SELECT payload FROM intake_items WHERE '+where+' ORDER BY name LIMIT ? OFFSET ?',params+[args.get('limit',100),args.get('offset',0)])]
            return {'total':total,'items':values,'generation':ns['generation']}
        if op=='intake.item':
            try:assessment=assess(db,ns,item)
            except (ValueError,OSError) as exc:assessment=profiles.held(item['profile'],activity.redact(exc))
            return {**item_summary(item),'assessment':assessment,'policy_hash':policy_hash(ns['policy']),
              'decisions':[json.loads(r[0]) for r in db.execute('SELECT payload FROM intake_decisions WHERE item=? ORDER BY rowid DESC LIMIT 30',(item['id'],))]}
        if op=='intake.decide':return decide(db,ns,item,args,actor)
        if op=='intake.bundle.decide':
            if ns['generation']!=args['expected_generation'] or current_policy(ns)!=args['expected_policy_hash']:raise ValueError('INTAKE_BUNDLE_REVIEW_CHANGED_REFRESH_REQUIRED')
            selected=[load(db,'items',ident) for ident in args['items']]
            if any(v['namespace']!=ns['id'] for v in selected) or len({v['batch'] for v in selected})!=1:raise ValueError('INTAKE_BUNDLE_MUST_SHARE_NAMESPACE_AND_BATCH')
            if any(v['admission']=='ACCEPTED' for v in selected):raise ValueError('INTAKE_BUNDLE_SELECT_UNADMITTED_ITEMS_ONLY')
            planned={v['id']:uuid.uuid4().hex for v in selected};checked=set();assessments={}
            for value in selected:
                assessment=assess(db,ns,value,checked,planned)
                if not assessment['eligible']:raise ValueError('INTAKE_BUNDLE_NOT_ELIGIBLE: '+value['name']+'; '+ '; '.join(assessment['reasons']))
                assessments[value['id']]=assessment
            decisions=[receipt(db,ns,value,'ACCEPTED',args['reason'],actor,assessments[value['id']],ident=planned[value['id']]) for value in selected]
            event(db,actor,'BUNDLE_ADMITTED',ns)
            return {'status':'ACCEPTED','files':len(decisions),'generation':ns['generation'],'decisions':decisions,'source_promotion':'NOT_GRANTED'}
        if op=='intake.revoke':
            if item['admission']!='ACCEPTED' or item['decision_id']!=args['expected_decision']:raise ValueError('INTAKE_CURRENT_ACCEPTANCE_REQUIRED')
            prior=load(db,'decisions',item['decision_id']);assessment={**prior['assessment'],'eligible':False,'recommendation':'HELD','reasons':['OWNER_REVOKED']}
            result=receipt(db,ns,item,'REVOKED',args['reason'],actor,assessment);cascade(db,ns,item['id'],actor);return result
        if op in ('intake.catalog','intake.search'):
            values,unavailable=catalog(db,ns,args.get('include_historical',False))
            if op=='intake.catalog':return {'edition':1,'generation':ns['generation'],'total':len(values),'items':[item_summary(v) for v in values[args.get('offset',0):args.get('offset',0)+args.get('limit',100)]],'unavailable':unavailable}
            terms=re.findall(r'[^\W_]+',args['query'],re.UNICODE)[:20]
            if not terms:return {'hits':[],'unavailable':unavailable,'generation':ns['generation']}
            allowed={v['id']:v for v in values}
            sql=db.execute("SELECT sql FROM sqlite_master WHERE name='intake_search'").fetchone()[0]
            if 'fts5' in sql.lower():
                match=' AND '.join('"'+v.replace('"','""')+'"' for v in terms)
                matches=db.execute('SELECT item FROM intake_search WHERE ns=? AND intake_search MATCH ? LIMIT 100',(ns['id'],match)).fetchall()
            else:
                matches=db.execute('SELECT item FROM intake_search WHERE ns=? AND '+ ' AND '.join('body LIKE ?' for _ in terms)+' LIMIT 100',[ns['id']]+['%'+v+'%' for v in terms]).fetchall()
            hits=[read_reference(db,ns,allowed[r[0]],args.get('include_historical',False)) for r in matches if r[0] in allowed][:args.get('limit',20)]
            return {'hits':hits,'unavailable':unavailable,'generation':ns['generation'],'search':'LEXICAL_ACCEPTED_ONLY'}
        if op=='intake.read':return read_reference(db,ns,item,args.get('include_historical',False))
        if op=='intake.packet.create':
            content=[]
            for ident in args['items']:
                value=load(db,'items',ident)
                if value['namespace']!=ns['id']:raise ValueError('PACKET_CANNOT_CROSS_NAMESPACE')
                content.append(read_reference(db,ns,value,True))
            packet={'schema':'arc.reference-packet/1','id':uuid.uuid4().hex,'namespace':ns['id'],'state':'CURRENT','created':time.time(),
                'policy_hash':current_policy(ns),'catalog_generation':ns['generation'],'inputs':[{k:v[k] for k in ('id','sha256','decision')} for v in content],
                'content':content,'content_trust':'UNTRUSTED_REFERENCE_DATA','network_calls':0}
            db.execute('INSERT INTO intake_packets VALUES(?,?,?,?)',(packet['id'],ns['id'],packet['state'],encoded(packet)));event(db,actor,'PACKET_CREATED',ns);return packet
        if op=='intake.checkpoint':
            values,unavailable=catalog(db,ns,True)
            if unavailable:raise ValueError('CHECKPOINT_HAS_UNAVAILABLE_REFERENCES')
            checkpoint={'id':uuid.uuid4().hex,'namespace':ns['id'],'label':args['label'],'created':time.time(),'generation':ns['generation'],
              'policy_hash':current_policy(ns),'items':[{k:v[k] for k in ('id','sha256','decision_id')} for v in values]}
            db.execute('INSERT INTO intake_checkpoints VALUES(?,?,?)',(checkpoint['id'],ns['id'],encoded(checkpoint)));event(db,actor,'CATALOG_CHECKPOINTED',ns);return checkpoint
        if op=='intake.checkpoints':return {'checkpoints':[json.loads(r[0]) for r in db.execute('SELECT payload FROM intake_checkpoints WHERE ns=? ORDER BY rowid DESC LIMIT 100',(ns['id'],))]}
        if op=='intake.catalog.restore':
            if ns['generation']!=args['expected_generation'] or checkpoint['policy_hash']!=current_policy(ns):raise ValueError('CATALOG_RESTORE_POLICY_OR_GENERATION_CHANGED')
            # All changes and receipts roll back if any original/dependency is unavailable.
            keep={v['id'] for v in checkpoint['items']}
            for row in db.execute('SELECT i.payload FROM intake_items i JOIN intake_catalog c ON c.item=i.id WHERE c.ns=?',(ns['id'],)).fetchall():
                value=json.loads(row[0])
                if value['id'] not in keep:
                    prior=load(db,'decisions',value['decision_id']);receipt(db,ns,value,'REVOKED',args['reason'],actor,{**prior['assessment'],'eligible':False,'reasons':['CATALOG_CHECKPOINT_RESTORE']});cascade(db,ns,value['id'],actor)
            selected=[load(db,'items',v['id']) for v in checkpoint['items']]
            expected={v['id']:v['sha256'] for v in checkpoint['items']}
            planned={};assessments={};checked=set()
            for value in selected:
                if value['sha256']!=expected[value['id']]:raise ValueError('RESTORE_INPUT_HASH_CHANGED')
                try:eligible(db,ns,value,checked=checked)
                except (ValueError,OSError):planned[value['id']]=uuid.uuid4().hex
            for value in selected:
                if value['id'] not in planned:continue
                assessment=assess(db,ns,value,checked,planned)
                if not assessment['eligible']:raise ValueError('RESTORE_DEPENDENCIES_OR_ORIGINALS_NOT_ELIGIBLE')
                assessments[value['id']]=assessment
            for value in selected:
                if value['id'] in planned:receipt(db,ns,value,'ACCEPTED',args['reason'],actor,assessments[value['id']],ident=planned[value['id']])
            event(db,actor,'CATALOG_RESTORED',ns);return {'status':'RESTORED','edition':1,'generation':ns['generation'],'items':len(keep),'old_packets':'REMAIN_STALE'}
        if op=='intake.recover':
            recovered=[]
            for row in db.execute('SELECT payload FROM intake_batches WHERE ns=? AND state=?',(ns['id'],'SCANNING')).fetchall():
                batch=json.loads(row[0])
                try:job=kernel.record('jobs',batch['job'])
                except Exception:job={'state':'Interrupted'}
                if job['state'] not in ('Queued','Running'):
                    batch.update(state='INTERRUPTED',failure='Worker ended before immutable scan committed; start a new import request')
                    save_batch(db,batch);recovered.append(batch['id'])
            if recovered:event(db,actor,'SCAN_INTERRUPTION_RECORDED',ns)
            return {'recovered':recovered,'accepted':0,'resume':'NEW_IMPORT_REQUEST_REUSES_HASHED_OBJECTS'}
        raise ValueError('UNKNOWN_INTAKE_OPERATION')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--job',required=True)
    args=parser.parse_args()
    if os.name!='nt':
        import resource
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
    from .engineering_kernel import Kernel
    kernel=Kernel(args.root);job=kernel.record('jobs',args.job)
    try:
        response={'intake.scan':scan,'intake.review':review,'intake.export':export_catalog}[job['tool']](kernel,job)
        code=0
    except Exception as exc:response={'status':'FAILED','reason':activity.redact(exc)};code=1
    response.update(schema='arc.intake-job-result/1',created=time.time(),job_id=job['id'],network_calls=0)
    response['class']='STATIC_CHECK'
    record_io.write_json(kernel.root/'build/intake/runs'/job['id']/'result.json',response)
    print(encoded(response));return code

if __name__=='__main__':raise SystemExit(main())
