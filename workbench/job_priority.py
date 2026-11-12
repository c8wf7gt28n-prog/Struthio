"""Owner-only Linux niceness for a tracked Ledger job and its verified descendants."""
import os
import sys
import time
from .operation_stop import process_identity, owned_tree, ProcessRef, UNKNOWN

FIELDS = {'jobs.nice':({'id':{'type':'string','pattern':'^[0-9a-f]{32}$','maxLength':32},
                       'value':{'type':'integer','minimum':0,'maximum':19}},['id','value'])}
SCOPES = {'jobs.nice':'approve'}
FIELDS['jobs.priority']=({'id':FIELDS['jobs.nice'][0]['id'],'priority':{'type':'string','enum':['foreground','normal','background']}},['id','priority'])
SCOPES['jobs.priority']='approve'


def describe(kernel, job, principal):
    supported = sys.platform.startswith('linux')
    value = job.get('cpu_nice')
    note = job.get('cpu_priority_note','')
    basis='NEXT_START_REQUEST' if job.get('state')=='Queued' else 'UNVERIFIED_PROCESS'
    live = job.get('pid') and job.get('worker_start') not in (None,UNKNOWN)
    if live and supported and job.get('state')=='Running':
        try:
            if process_identity(job['pid']) != job['worker_start']:raise ValueError('Tracked job process has exited or changed')
            value = os.getpriority(os.PRIO_PROCESS,job['pid'])
            basis='OBSERVED_PROCESS'
        except (OSError,ValueError) as exc:return {'cpu_nice':None,'can_adjust_nice':False,'cpu_priority_note':str(exc),'cpu_priority_basis':'UNAVAILABLE'}
    if value is None:
        from .operation_priority import policy
        value = 10 if policy(kernel.root) == 'background' else 0
    if not supported:basis='UNSUPPORTED'
    if basis in ('UNVERIFIED_PROCESS','UNSUPPORTED'):value=None
    return {'cpu_nice':value,'can_adjust_nice':bool(supported and 'approve' in principal.scopes and principal.mode!='Tutor' and job.get('owner') == principal.identity
            and job.get('state') in ('Queued','Running') and (job.get('state') == 'Queued' or live)),
            'cpu_priority_note':note,'cpu_priority_basis':basis}


def change(kernel,args,principal):
    if not sys.platform.startswith('linux'):raise ValueError('Per-job niceness requires Linux')
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        job = kernel.record('jobs',args['id'])
        if job.get('owner') != principal.identity:raise ValueError('Only the job owner can change its niceness')
        if job['state'] not in ('Queued','Running'):raise ValueError('This job has finished; refresh Nice')
        requested = args['value'];results = []
        if job['state'] == 'Running':
            pid = job.get('pid');token = job.get('worker_start')
            if not pid or pid == os.getpid() or token in (None,UNKNOWN) or process_identity(pid) != token:
                raise ValueError('The running job process could not be verified')
            refs = owned_tree([pid])
            if not any(ref.pid == pid for ref in refs):refs.append(ProcessRef(pid,token))
            # Change only the tracked worker and processes proven to descend from it.
            for ref in refs:
                if ref.pid == os.getpid() or process_identity(ref.pid) != ref.token:continue
                try:
                    os.setpriority(os.PRIO_PROCESS,ref.pid,requested)
                    results.append({'pid':ref.pid,'state':'applied','nice':os.getpriority(os.PRIO_PROCESS,ref.pid)})
                except OSError as exc:results.append({'pid':ref.pid,'state':'denied','reason':str(exc)})
            if not results:raise ValueError('The job processes have exited; refresh Nice')
            try:actual = os.getpriority(os.PRIO_PROCESS,pid)
            except OSError:actual = None
        else:actual = requested
        failures = [r for r in results if r['state'] == 'denied']
        job['cpu_nice'] = actual if actual is not None else job.get('cpu_nice',0)
        job['cpu_priority_note'] = ('OS refused %d process priority change(s): ' % len(failures) + '; '.join(r['reason'] for r in failures)) if failures else ''
        job['cpu_priority_updated'] = time.time();kernel.save('jobs',job,db)
    return {'id':job['id'],'state':'PARTIAL_OR_REFUSED' if failures else 'QUEUED' if job['state']=='Queued' else 'APPLIED',
            'requested':requested,'actual':actual,'processes':results,'notice':job['cpu_priority_note']}


def apply_worker(job):
    """Apply a queued request before children start; preserve an OS refusal as data."""
    if not sys.platform.startswith('linux') or job.get('cpu_nice') is None:return
    try:os.setpriority(os.PRIO_PROCESS,os.getpid(),job['cpu_nice'])
    except OSError as exc:job['cpu_priority_note']='OS refused the queued niceness: '+str(exc)
    job['cpu_nice']=os.getpriority(os.PRIO_PROCESS,os.getpid())


def dispatch(kernel,op,args,principal):
    if op == 'jobs.nice':return change(kernel,args,principal)
    if op=='jobs.priority':
        from . import resource_control
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE');job=kernel.record('jobs',args['id'])
            if job.get('owner')!=principal.identity:raise ValueError('Only the job owner can change its scheduling priority')
            if job['state']!='Queued':raise ValueError('Scheduling priority changes at a queued boundary; a running tool is not preempted')
            demand=job.get('resource_request') or resource_control.request(job,'normal')
            job['resource_request']={**demand,'priority':args['priority']}
            job.pop('resource_wait',None);job.pop('resource_wait_updated',None)
            job['current_operation']='Priority updated; awaiting admission'
            if args['priority']=='foreground':resource_control.touch(kernel,principal.identity,db)
            kernel.save('jobs',job,db)
        return dict(id=job['id'],priority=args['priority'],state='QUEUED',notice='Next admission order changed. CPU niceness is a separate control.')
    raise ValueError('Unknown job priority operation')
