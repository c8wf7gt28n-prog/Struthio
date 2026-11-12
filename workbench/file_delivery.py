"""Recovery receipts for explicit file saves outside SQLite's transaction."""
import hashlib,json,os,uuid
from . import activity

def prepare(kernel,path,before,after):
    relative=path.resolve().relative_to(kernel.root).as_posix()
    receipt={'id':uuid.uuid4().hex,'path':relative,'before':before,'after':after}
    base=kernel.state/'file_delivery';base.mkdir(mode=0o700,exist_ok=True)
    target=base/(receipt['id']+'.json');tmp=target.with_suffix('.tmp')
    tmp.write_text(json.dumps(receipt));tmp.chmod(0o600);os.replace(tmp,target)
    return receipt,target

def event(receipt,state='SAVED'):
    return activity.make_event('GUI','files.save',state,receipt['path'],
        correlation_id=receipt['id'],source_generation=receipt['after'])

def reconcile(kernel):
    results=[]
    for receipt_path in sorted((kernel.state/'file_delivery').glob('*.json')):
        receipt=json.loads(receipt_path.read_text());path=kernel.safe(receipt['path'],must_exist=False)
        actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        state='RECONCILED_SAVED' if actual==receipt['after'] else 'NOT_APPLIED' if actual==receipt['before'] else 'CONFLICT'
        if state=='CONFLICT':results.append({'id':receipt['id'],'state':state});continue
        with kernel.db() as db:activity.append(db,event(receipt,state))
        receipt_path.unlink();results.append({'id':receipt['id'],'state':state})
    return results
