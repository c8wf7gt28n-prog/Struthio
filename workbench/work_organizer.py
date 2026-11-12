"""A read model of existing tasks and the caller's next work, never a scheduler."""
import json
from sdk.cli.arc1cli import work_organizer as contract
from . import activity, package_service, record_access, work_trail

FIELDS={'ledger.organizer':({'query':{'type':'string','maxLength':200},
         'focus':{'type':'string','enum':['all',*contract.FOCUS]}},[])}
SCOPES={'ledger.organizer':'read'}


def read(kernel,principal,query='',focus='all'):
    tasks=contract.tasks(query,focus)
    from . import project_context
    attached=not project_context.detached(kernel.root)
    for task in tasks:
        task['state']='Project required' if task['id']=='engineering' and not attached else 'Open workspace'
    next_work=[]
    gate=work_trail.work_status(kernel)
    if gate['held']:
        next_work.append({'kind':'hold','title':'Work is held','detail':'Reconcile work, then explicitly Resume in Work trail.',
                          'destination':'trail','priority':0})
    for item in package_service.listing(kernel,principal)['inspections'][:8]:
        if item['state']=='READY' and item['copy_observation']['state']=='READY_BATCH':continue
        next_work.append({'kind':'package','id':item['id'],'title':item['name'],
                          'detail':'Inspection ready · choose next step' if item['state']=='READY' else 'Inspect package issues',
                          'state':item['state'],'destination':'packages','priority':1 if item['state']!='READY' else 3})
    with kernel.db() as db:
        jobs=[json.loads(r[0]) for r in db.execute('SELECT payload FROM jobs WHERE owner=? ORDER BY rowid DESC LIMIT 20',(principal.identity,))]
    for job in jobs:
        if job.get('owner')!=principal.identity:continue
        if not record_access.readable(kernel,'jobs',job,principal):continue
        if job['state'] not in ('Completed','Cancelled'):
            next_work.append({'kind':'job','id':job['id'],'title':activity.redact(job['tool'],120),
                              'detail':job['state'],'destination':'trail','priority':1 if job['state'] in ('Failed','Interrupted') else 2})
    with kernel.db() as db:
        namespaces=[json.loads(r[0]) for r in db.execute('SELECT payload FROM intake_namespaces WHERE owner=? ORDER BY rowid DESC LIMIT 16',(principal.identity,))]
        for ns in namespaces[:16]:
            count=db.execute("SELECT count(*) FROM intake_items WHERE ns=? AND admission IN ('UNREVIEWED','HELD')",(ns['id'],)).fetchone()[0]
            if count:next_work.append({'kind':'library','id':ns['id'],'title':activity.redact(ns['name'],120),
                                      'detail':str(count)+' reference(s) await review','destination':'intake','priority':2})
    if query:
        next_work=[r for r in next_work if query.casefold() in (' '.join(str(r.get(k,'')) for k in ('title','detail','kind'))).casefold()]
    if focus!='all':
        destinations={row[4] for row in contract.TASKS if row[1]==contract.FOCUS[focus]}
        next_work=[r for r in next_work if r['destination'] in destinations]
    next_work.sort(key=lambda r:(r['priority'],r['title'].casefold()))
    return {'schema':'arc.workbench-organizer/1','tasks':tasks,'next':next_work[:12],
            'next_total':len(next_work),'query':query,'focus':focus,'scope':'THIS_CALLER_ONLY',
            'project_attached':attached,'gate':gate,'staC':'desk' if focus=='all' else 'desk | focus '+focus,
            'executes':False,'automatic_reorganization':False,'physical_qualification':False,
            'notice':'Choosing a task opens its existing controls. Nothing runs from this overview.'}


def dispatch(kernel,op,args,principal):
    return read(kernel,principal,**args)
