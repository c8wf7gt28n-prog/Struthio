"""Owner-private inspection receipts; copy uses the existing intake job authority."""
from pathlib import Path
import hashlib
import json
import time
from sdk.cli.arc1cli import package_transport as contract, intake_files as files
from . import activity, intake_service as intake, record_io as io

ID={'type':'string','pattern':'^[0-9a-f]{32}$','maxLength':32}
FIELDS={
    'intake.package.inspect':({'path':intake.TEXT},['path']),
    'intake.package.list':({},[]),
    'intake.package.get':({'id':ID,'offset':{'type':'integer','minimum':0,'maximum':10000},
                           'limit':{'type':'integer','minimum':1,'maximum':200}},['id']),
    'intake.package.copy':({'id':ID,'namespace':ID},['id','namespace']),
}
SCOPES={op:'approve' if op in ('intake.package.inspect','intake.package.copy') else 'read' for op in FIELDS}
MAX_RECEIPTS=32
MAX_RECORD=16*1024*1024


def rules():
    return hashlib.sha256(Path(contract.__file__).read_bytes()+Path(__file__).read_bytes()).hexdigest()


def ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS package_inspections(id TEXT PRIMARY KEY,owner TEXT,path TEXT,payload TEXT,sha256 TEXT)')
    db.execute('CREATE INDEX IF NOT EXISTS package_inspection_owner ON package_inspections(owner)')
    db.execute("CREATE INDEX IF NOT EXISTS package_copied_hash ON intake_batches(json_extract(payload,'$.source.sha256'))")


def read(db,ident,owner):
    row=db.execute('SELECT path,payload,sha256 FROM package_inspections WHERE id=? AND owner=?',(ident,owner)).fetchone()
    if not row or len(row[1].encode())>MAX_RECORD:raise ValueError('PACKAGE_UNAVAILABLE')
    value=io.strict_json(row[1])
    if io.digest(value)!=row[2]:raise ValueError('PACKAGE_UNAVAILABLE')
    return row[0],value


def summary(value):
    return {k:value.get(k) for k in ('id','name','sha256','bytes','state','format','encryption','member_count','expanded_bytes','issues','observed_at','inventory_sha256')}


def copy_observation(db,owner,digest):
    rows=db.execute("SELECT b.id,b.ns FROM intake_batches b JOIN intake_namespaces n ON n.id=b.ns WHERE n.owner=? AND b.state='READY' AND json_extract(b.payload,'$.source.sha256')=? ORDER BY b.rowid DESC LIMIT 2",(owner,digest)).fetchall()
    return {'state':'READY_BATCH' if rows else 'NOT_ESTABLISHED','batch':rows[0][0] if rows else None,
            'namespace':rows[0][1] if rows else None,'scope':'EXISTING_OWNER_REVIEW_COPY_NOT_ADMISSION'}


def get(kernel,principal,ident,offset=0,limit=100):
    with kernel.db() as db:
        _,value=read(db,ident,principal.identity)
        copied=copy_observation(db,principal.identity,value['sha256'])
    return {**summary(value),'members':value['members'][offset:offset+limit],
            'offset':offset,'total':len(value['members']),'transport':value['transport'],
            'rules_current':value['rules']==rules(),'accepted':0,'source_promotion':'NOT_GRANTED',
            'copy_observation':copied,
            'notice':'Inspection observes bytes; copying to quarantine and admission are separate choices.'}


def listing(kernel,principal):
    with kernel.db() as db:
        ids=[r[0] for r in db.execute('SELECT id FROM package_inspections WHERE owner=? ORDER BY rowid DESC LIMIT ?',(principal.identity,MAX_RECEIPTS))]
        rows=[]
        for ident in ids:
            value=read(db,ident,principal.identity)[1]
            rows.append({**summary(value),'copy_observation':copy_observation(db,principal.identity,value['sha256'])})
    return {'inspections':rows,'retention':MAX_RECEIPTS,'scope':'THIS_OWNER_ONLY'}


def inspect_path(path,cancelled=lambda:False):
    source=files.regular(path)
    last=0.;stopped=False
    def checkpoint():
        nonlocal last,stopped
        now=time.monotonic()
        if now-last>=.1:last=now;stopped=cancelled()
        return stopped
    raw=files.read_stable(source,contract.MAX_INPUT,checkpoint)
    return source,contract.inspect_bytes(raw,source.name,checkpoint)


def inspect(kernel,principal,path):
    source=files.regular(path)
    if source.resolve().is_relative_to(kernel.root):raise ValueError('PACKAGE_CHOOSE_EXTERNAL_DATA_NOT_PROGRAM')
    from .work_trail import work_status
    gate=work_status(kernel)
    epoch=gate['epoch']
    def cancelled():
        from .work_trail import work_status
        return work_status(kernel)['epoch']!=epoch
    _,value=inspect_path(source,cancelled)
    if cancelled() or 'PACKAGE_INSPECTION_CANCELLED' in value['issues']:raise ValueError('PACKAGE_INSPECTION_CANCELLED')
    rule=rules();ident=hashlib.sha256((principal.identity+'\0'+value['sha256']+'\0'+rule).encode()).hexdigest()[:32]
    value.update(id=ident,name=activity.redact(source.name,240),observed_at=time.time(),rules=rule)
    raw=io.canonical(value)
    if len(raw)>MAX_RECORD:raise ValueError('PACKAGE_RECEIPT_LIMIT')
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT OR REPLACE INTO package_inspections VALUES(?,?,?,?,?)',(ident,principal.identity,str(source),raw.decode(),io.digest(value)))
        old=db.execute('SELECT id FROM package_inspections WHERE owner=? ORDER BY rowid DESC LIMIT -1 OFFSET ?',(principal.identity,MAX_RECEIPTS)).fetchall()
        db.executemany('DELETE FROM package_inspections WHERE id=?',old)
        activity.append(db,activity.make_event(principal.identity,'intake.package.inspect',value['state']))
    return get(kernel,principal,ident)


def copy_for_review(kernel,principal,ident,namespace):
    from .work_trail import accepting
    accepting(kernel)
    with kernel.db() as db:
        path,value=read(db,ident,principal.identity)
        intake.namespace(db,namespace,principal.identity,True)
    if value['rules']!=rules():raise ValueError('PACKAGE_RULES_CHANGED_INSPECT_AGAIN')
    if value['state']!='READY':raise ValueError('PACKAGE_NOT_READY_FOR_REVIEW_COPY')
    # The worker checks the exact archive again before publishing intake items.
    if hashlib.sha256(files.read_stable(path,contract.MAX_INPUT)).hexdigest()!=value['sha256']:raise ValueError('PACKAGE_CHANGED_INSPECT_AGAIN')
    with kernel.db() as db:
        # Content identity prevents a second route/key from duplicating the same copy.
        for raw, in db.execute("SELECT payload FROM intake_batches WHERE ns=? AND state='READY'",(namespace,)):
            batch=json.loads(raw)
            if batch.get('source',{}).get('sha256')==value['sha256']:
                return {'state':'ALREADY_COPIED','batch':batch['id'],'job':batch['job'],'accepted':0,'replayed':False}
    key='package:'+hashlib.sha256((namespace+value['sha256']).encode()).hexdigest()
    with kernel.db() as db:
        prior=db.execute('SELECT job FROM requests WHERE owner=? AND key=?',(principal.identity,key)).fetchone()
        if prior:
            from .work_trail import bind
            bind(db,kernel,principal.identity,prior[0])
            job=kernel.record('jobs',prior[0])
            return {'state':'COPY_REQUESTED','job':job['id'],'job_state':job['state'],'accepted':0,'replayed':False}
    job=intake.submit(kernel,'intake.scan',{'namespace':namespace,'path':path,'mode':'snapshot',
                      'expected_archive_sha256':value['sha256'],'request_key':key},principal)
    return {'state':'COPY_REQUESTED','job':job['id'],'job_state':job['state'],'accepted':0,'replayed':False}


def dispatch(kernel,op,args,principal):
    if op=='intake.package.inspect':return inspect(kernel,principal,args['path'])
    if op=='intake.package.list':return listing(kernel,principal)
    if op=='intake.package.get':return get(kernel,principal,args['id'],args.get('offset',0),args.get('limit',100))
    if op=='intake.package.copy':return copy_for_review(kernel,principal,args['id'],args['namespace'])
    raise ValueError('PACKAGE_OPERATION_UNKNOWN')
