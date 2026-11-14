"""Admission and foreground turns over the existing Kernel jobs/settings.

No second queue or model service. Reservations describe future headroom, not
physical allocations. MemAvailable already includes resident work; only the
unmaterialized portion of an owned budget is subtracted from it.

One memory rule (budget_room) decides admission here, the model's configuration
at submit and at run (local_brain.configuration) and the launch check
(model_room), so a model admitted is never refused at launch for the same numbers.
"""
import contextlib,contextvars,json,os,time
from . import memory_forecast
from .operation_stop import process_identity,owned_tree,UNKNOWN

MIB=1024**2
PRIORITIES=('foreground','normal','background')
_priority=contextvars.ContextVar('graphite_resource_priority',default='foreground')
KEYS={'reserve_mb':2048,'compute_slots':1,'background_threads':2}
FORECAST_KEY = 'resources.memory_forecast'
UNMEASURED='Host memory could not be measured'
UNMEASURED_WAIT_SECONDS=30  # a request whose memory reading is lost waits this long for it, then fails saying why
HELD='Work is held: waiting for the owner to resume work'


def current_priority():return _priority.get()


@contextlib.contextmanager
def scope(priority):
    if priority not in PRIORITIES:raise ValueError('Unknown resource priority')
    token=_priority.set(priority)
    try:yield
    finally:_priority.reset(token)


def read(db,key,default=None):
    row=db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
    return json.loads(row[0]) if row else default


def policy(db,host):
    from .ledger_control import validate
    values={}
    for key,default in KEYS.items():
        value=read(db,'ledger.operations.'+key,default);validate('operations.'+key,value);values[key]=value
    values['reserve_bytes']=reserve_bytes(values['reserve_mb'],host.get('total_ram_bytes'))
    values['background_threads']=min(values['background_threads'],max(1,(host.get('logical_cpus') or 2)-1))
    return values


def reserve_bytes(reserve_mb,total):
    """The foreground reserve: the owner's setting, at most a quarter of installed RAM on a small machine (never under
    128 MiB). When installed RAM cannot be read the whole setting stays: not knowing the machine is no reason to keep
    less room for the desk."""
    if not total:return reserve_mb*MIB
    return min(reserve_mb*MIB,max(128*MIB,total//4))


def reserve_setting(kernel,db=None):
    """The owner's foreground reserve setting in MiB (ledger.operations.reserve_mb), for local_brain.configuration."""
    if db is None:
        with kernel.db() as connection:return reserve_setting(kernel,connection)
    return policy(db,{})['reserve_mb']


def budget_room(available,reserve,future=0,credit=0):
    """The one memory rule. A budget fits when it is no larger than this: what is available, less the foreground
    reserve and the unmaterialized budgets already admitted, plus what a sequential model handover frees. Admission
    (decision), the model's configuration (local_brain.configuration) and the launch check (model_room) all compare
    a budget against it the same way: more than the room waits or is refused."""
    return max(0,(available or 0)-reserve-future)+max(0,credit)


def touch(kernel,owner,db=None):
    """A short activity lease: no keystrokes, text, pointer positions or journal flood."""
    if db is None:
        with kernel.db() as connection:return touch(kernel,owner,connection)
    value=dict(owner=owner,until=time.time()+8)
    db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('resources.foreground',json.dumps(value)))


def foreground(db):
    value=read(db,'resources.foreground',{}) or {};remaining=value.get('until',0)-time.time()
    return 0<remaining<=10


def request(job,priority=None):
    from . import local_brain
    tool=job.get('tool','');spec=job.get('request_spec',{})
    priority=priority or _priority.get();lane='compute';budget=512*MIB;basis='CONSERVATIVE_TOOL_ESTIMATE'
    handover=tool in ('brain.activate','brain.qualify')
    if handover:
        options=(job.get('brain_launch') or {}).get('options') or spec.get('brain',{})
        budget=options.get('memory_mb',1024)*MIB;lane='inference';basis='FROZEN_MODEL_MEMORY_BUDGET'
    elif tool in local_brain.JOB_TOOLS and tool!='brain.inspect':
        lane='inference';budget=128*MIB;basis='MODEL_TURN_OVERHEAD_MODEL_BUDGET_ACCOUNTED_SEPARATELY'
        if tool=='brain.change_draft':budget=max(budget,spec.get('brain',{}).get('memory_mb',1024)*MIB)
    elif tool=='brain.inspect' or tool.startswith(('intake.','knowledge.','network.','references.')):
        lane='io';budget=256*MIB
    elif tool in ('clip.loop','clip.workshop'):
        lane='control';budget=256*MIB  # These coordinators may submit a child; never hold its compute lane.
    for group in ('study','lab','office','investigation'):
        limits=spec.get(group,{})
        if isinstance(limits,dict):
            for row in (limits,limits.get('limits',{})):
                if not isinstance(row,dict):continue
                for key in ('memory_mb','max_rss_mb'):
                    value=row.get(key)
                    if type(value) is int and 64<=value<=262144:budget=max(budget,value*MIB);basis='DECLARED_TOOL_BUDGET'
    return dict(priority=priority,lane=lane,memory_bytes=budget,basis=basis,model_handover=handover)


def process_memory(pid,token,private=False):
    """Owned process-tree RSS, and private pages eligible for sequential reclaim."""
    result=dict(rss_bytes=0,private_bytes=0,observed=False)
    if not pid or token in (None,UNKNOWN) or process_identity(pid)!=token:return result
    try:
        from .operation_stop import _linux_path
        refs=owned_tree([pid])
        for ref in refs:
            if process_identity(ref.pid)!=ref.token:continue
            path,_=_linux_path(ref.pid)
            values=dict(line.split(':',1) for line in (path/'status').read_text().splitlines() if ':' in line)
            result['rss_bytes']+=int(values.get('VmRSS','0').split()[0])*1024
            if private:
                try:
                    roll=dict(line.split(':',1) for line in (path/'smaps_rollup').read_text().splitlines() if ':' in line)
                    result['private_bytes']+=sum(int(roll.get(key,'0').split()[0])*1024 for key in ('Private_Clean','Private_Dirty'))
                except (OSError,ValueError):pass
            result['observed']=True
    except (OSError,ValueError,KeyError,TypeError,AttributeError):pass
    if process_identity(pid)!=token:return dict(rss_bytes=0,private_bytes=0,observed=False)
    return result


def reclaimable(kernel,db=None):
    if db is None:
        with kernel.db() as connection:return reclaimable(kernel,connection)
    worker=read(db,'brain.worker',{}) or {}
    return process_memory(worker.get('pid'),worker.get('start'),private=True)['private_bytes']


def _view(kernel,db,host,exclude=None,handover=False):
    from . import local_brain
    settings=policy(db,host)
    jobs=[json.loads(r[0]) for r in db.execute("SELECT payload FROM jobs WHERE state IN ('Running','Queued')")]
    def still_owned(job):
        token=job.get('worker_start')
        if token in (None,UNKNOWN):return True  # Legacy/unknown ownership is not guessed away.
        current=process_identity(job.get('pid'))
        if current in (token,UNKNOWN):return True
        child=process_identity(job.get('tool_pid'))
        return bool(child and child in (job.get('tool_start'),UNKNOWN))
    running=[j for j in jobs if j['state']=='Running' and j['id']!=exclude and still_owned(j)]
    commitments=[];loading={j['id'] for j in running if (j.get('resource_request') or request(j,'normal'))['model_handover']}
    for job in running:
        demand=job.get('resource_request') or request(job,'normal')
        observed=process_memory(job.get('pid'),job.get('worker_start'))
        commitments.append(dict(kind='job',id=job['id'],owner=job['owner'],tool=job['tool'],lane=demand['lane'],
            priority=demand['priority'],budget_bytes=demand['memory_bytes'],**observed))
    model_seen=set()
    for key in ('brain.worker','brain.trial_worker'):
        worker=read(db,key,{}) or {};identity=(worker.get('pid'),worker.get('start'))
        if identity in model_seen or not local_brain.worker_live(worker):continue
        model_seen.add(identity)
        if worker.get('job_id') in loading or worker.get('job_id')==exclude:continue
        if handover and key=='brain.worker':continue  # Its unused reservation ends at sequential handover.
        config=worker.get('config',{})
        commitments.append(dict(kind='model',id=worker.get('model_id'),owner=worker.get('owner'),lane='resident_model',
            budget_bytes=config.get('memory_mb',0)*MIB,**process_memory(worker['pid'],worker['start'])))
    future=sum(max(0,row['budget_bytes']-row['rss_bytes']) for row in commitments)
    available=host.get('available_ram_bytes')
    return dict(policy=settings,jobs=jobs,running=running,commitments=commitments,
                reserved_future_bytes=future,available_bytes=available,total_bytes=host.get('total_ram_bytes'),
                headroom_bytes=budget_room(available,settings['reserve_bytes'],future),foreground_active=foreground(db))


def decision(kernel,job,db,host):
    demand=job.get('resource_request') or request(job,'normal')
    view=_view(kernel,db,host,job['id'],demand['model_handover']);reason=None
    if view['available_bytes'] is None:reason=UNMEASURED
    elif demand['priority']!='foreground' and view['foreground_active']:reason='Foreground interaction has the next turn'
    elif len(view['running'])>=4:reason='Four native job slots are occupied'
    elif demand['lane']=='inference' and any((j.get('resource_request') or request(j,'normal'))['lane']=='inference' for j in view['running']):reason='Another model turn or handover is in progress'
    elif demand['lane']=='compute' and sum((j.get('resource_request') or request(j,'normal'))['lane']=='compute' for j in view['running'])>=view['policy']['compute_slots']:reason='CPU calculation slots are occupied'
    elif demand['lane']=='control' and any((j.get('resource_request') or request(j,'normal'))['lane']=='control' for j in view['running']):reason='Another coordinator is in progress; child capacity is reserved'
    rank=lambda j:(PRIORITIES.index((j.get('resource_request') or request(j,'normal'))['priority']),j.get('created',0),j['id'])
    if reason is None and any(j['state']=='Queued' and j['id']!=job['id'] and
        (j.get('resource_request') or request(j,'normal'))['lane']==demand['lane'] and rank(j)<rank(job) for j in view['jobs']):
        reason='An earlier eligible request has the next '+demand['lane']+' turn'
    credit=reclaimable(kernel,db) if demand['model_handover'] else 0
    room=budget_room(view['available_bytes'],view['policy']['reserve_bytes'],view['reserved_future_bytes'],credit)
    if reason is None and demand['memory_bytes']>room:reason='Waiting for shared-memory headroom'
    return dict(allowed=reason is None,reason=reason,priority=demand['priority'],lane=demand['lane'],
                requested_bytes=demand['memory_bytes'],available_bytes=view['available_bytes'],
                reserved_future_bytes=view['reserved_future_bytes'],reserve_bytes=view['policy']['reserve_bytes'],
                reclaimable_private_bytes=credit,headroom_bytes=room,policy=view['policy'])


def _forecast_admission(db, job, admission, observed_at, clock_origin):
    """Reuse the hard gate's observation inside the worker's admission transaction."""
    if admission['available_bytes'] is None or job['resource_request']['model_handover']:
        return
    prior = _forecast_sample(db, clock_origin)
    room = admission['headroom_bytes']
    sample = memory_forecast.observe(prior, observed_at, room)
    if sample is not prior:
        db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',
                   (FORECAST_KEY, json.dumps(dict(clock_origin=clock_origin, sample=sample))))
    if not admission['allowed'] or admission['priority'] != 'background':
        return
    wait = job.get('resource_forecast_wait')
    since = wait.get('since') if _same_clock(wait, clock_origin) else None
    forecast = memory_forecast.evaluate(sample, observed_at, room, admission['requested_bytes'], since)
    admission['memory_forecast'] = forecast
    if forecast['outcome'] == 'defer':
        job['resource_forecast_wait'] = dict(clock_origin=clock_origin, since=forecast['deferred_since'])
        admission.update(allowed=False, reason=forecast['reason'])


def _same_clock(record, clock_origin):
    # Monotonic time is shared by workers. Reject a prior boot or a changed wall clock.
    origin = record.get('clock_origin') if isinstance(record, dict) else None
    return type(origin) in (float, int) and clock_origin - 1 < origin < clock_origin + 1


def _forecast_sample(db, clock_origin):
    stored = read(db, FORECAST_KEY, {})
    return stored.get('sample') if _same_clock(stored, clock_origin) else None


def claim(kernel,ident):
    """The existing queued worker waits here, before starting a tool or its deadline."""
    from . import brain_runtime,local_brain,work_trail,ledger_control
    stamp=process_identity(os.getpid());last_reason=None;last_save=0;unmeasured_since=None
    while True:
        host=brain_runtime.host(profile=False)
        observed_at = time.monotonic()
        clock_origin = time.time() - observed_at
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE')
            job=json.loads(db.execute('SELECT payload FROM jobs WHERE id=?',(ident,)).fetchone()[0])
            if job['state']!='Queued':return None
            other=job.get('pid')
            if other and other!=os.getpid() and job.get('worker_start') not in (None,UNKNOWN) and process_identity(other)==job['worker_start']:return None
            reason='Owner work hold prevented execution' if job.get('cancel') or not ledger_control.value(kernel,'operations.services_enabled') else None
            if not reason and job['tool'] in local_brain.JOB_TOOLS and job['tool']!='brain.inspect':
                try:local_brain.require_enabled(kernel)
                except ValueError as exc:reason=str(exc)
            if reason:
                job.update(state='Cancelled',cancel=True,finished=time.time(),current_operation='work held',error=reason)
                job.pop('resource_forecast_wait',None)
                kernel.save('jobs',job,db);return None
            job['pid']=os.getpid();job['worker_start']=stamp
            job.setdefault('resource_request',request(job,'normal'))
            admission=decision(kernel,job,db,host)
            if work_trail.work_status(kernel,db)['held']:
                # A hold holds: queued work waits here, before it starts anything, and continues from this step when
                # the owner resumes work (work_trail.resume). Cancel and Master Stop still end it.
                admission.update(allowed=False,reason=HELD)
            else:_forecast_admission(db,job,admission,observed_at,clock_origin)
            if admission['reason']!=UNMEASURED:unmeasured_since=None
            elif unmeasured_since is None:unmeasured_since=observed_at
            elif observed_at-unmeasured_since>=UNMEASURED_WAIT_SECONDS:
                # A reading lost after submit does not keep the request waiting for ever: it fails, saying why.
                job.update(state='Failed',finished=time.time(),current_operation='not started',
                           error='HOST_MEMORY_COULD_NOT_BE_MEASURED: available memory could not be read for %d s, so '
                                 'this request was not started' % UNMEASURED_WAIT_SECONDS)
                job.pop('resource_forecast_wait',None)
                kernel.save('jobs',job,db);return None
            if admission['allowed']:
                job.update(state='Running',started=time.time(),current_operation=job['tool'],resource_admission=admission)
                job.pop('resource_wait',None)
                job.pop('resource_forecast_wait',None)
                if job.get('cpu_nice') is None and admission['priority']=='background':job['cpu_nice']=10
                from .job_priority import apply_worker
                apply_worker(job);kernel.save('jobs',job,db);return job
            if admission['reason']!=last_reason or time.monotonic()-last_save>5:
                job.update(resource_wait=admission,current_operation=admission['reason'],resource_wait_updated=time.time())
                kernel.save('jobs',job,db);last_reason=admission['reason'];last_save=time.monotonic()
        time.sleep(.4)


def model_room(kernel,config,ident):
    from .brain_runtime import host
    with kernel.db() as db:view=_view(kernel,db,host(),ident)
    # budget_room, as at admission; the previous worker has stopped by now, so no handover credit is left to add.
    if view['available_bytes'] is None or config['memory_mb']*MIB>budget_room(
            view['available_bytes'],view['policy']['reserve_bytes'],view['reserved_future_bytes']):
        raise ValueError('GRAPHITE_HOST_MEMORY_LIMIT: model launch no longer has admitted shared-memory headroom')
    return view['policy']


def background_reason(kernel):
    from .brain_runtime import host
    with kernel.db() as db:
        view=_view(kernel,db,host())
        if view['foreground_active']:return 'Foreground interaction has the next turn'
        if view['available_bytes'] is None or view['headroom_bytes']<128*MIB:return 'Waiting for shared-memory headroom'
        if any(j['state']=='Queued' and (j.get('resource_request') or request(j,'normal'))['priority']=='foreground' for j in view['jobs']):return 'Foreground work is queued'
    return None


def snapshot(kernel,principal,host=None):
    from .brain_runtime import host as observe
    with kernel.db() as db:view=_view(kernel,db,host or observe())
    jobs=[dict(id=j['id'],tool=j['tool'],state=j['state'],request=j.get('resource_request'),waiting=j.get('resource_wait'))
          for j in view['jobs'] if j.get('owner')==principal.identity]
    return dict(schema='graphite.resource-control/1',state='PRESSURE' if view['available_bytes'] is None or view['available_bytes']<view['policy']['reserve_bytes'] else 'FOREGROUND_TURN' if view['foreground_active'] else 'WAITING_FOR_HEADROOM' if view['headroom_bytes']<128*MIB else 'ACCEPTING',
                total_bytes=view['total_bytes'],available_bytes=view['available_bytes'],reserve_bytes=view['policy']['reserve_bytes'],
                reserved_future_bytes=view['reserved_future_bytes'],headroom_bytes=view['headroom_bytes'],
                foreground_active=view['foreground_active'],policy=view['policy'],jobs=jobs,
                commitments=[{k:v for k,v in row.items() if k!='owner'} for row in view['commitments'] if row.get('owner')==principal.identity],
                scope='This workspace owned workers and current whole-host availability. Other applications are reflected in available RAM.',
                limits='Advisory admission, not a global OS memory cap. GPU allocations are not completely visible in process RSS; unknown memory stays conservative. Active tools finish at their boundary; CPU nice and library thread limits do not preempt GPU kernels.')


def observation(kernel):
    """Project the admission view into a content-free, typed local readback."""
    from . import brain_runtime, host_observations

    host = brain_runtime.host(profile=False)
    sampled_at = time.time()
    observed_at = time.monotonic()
    with kernel.db() as db:
        db.execute('BEGIN')
        view = _view(kernel, db, host)
        history = _forecast_sample(db, sampled_at - observed_at)
    available = view['available_bytes']
    headroom = view['headroom_bytes'] if available is not None else None
    forecast = memory_forecast.evaluate(history, observed_at, headroom, 0)
    gpu_busy = host_observations.gpu()
    return {
        'schema': 'graphite.resource-observation/1',
        'kind': 'LIVE_READBACK',
        'source': 'MEASURED_LOCAL',
        'scope': 'CURRENT_EXECUTION_HOST',
        'sampled_at_unix': sampled_at,
        'memory': {
            'state': 'MEASURED' if available is not None else 'UNAVAILABLE',
            'available_bytes': available,
            'reserve_bytes': view['policy']['reserve_bytes'],
            'reserved_future_bytes': view['reserved_future_bytes'],
            'headroom_bytes': headroom,
        },
        'forecast': {
            'state': 'ESTIMATED' if forecast['eligible'] else 'UNAVAILABLE',
            'basis': 'RECENT_ADMISSION_SAMPLES',
            'horizon_seconds': forecast['horizon_seconds'],
            'headroom_bytes': forecast['projected_headroom_bytes'] if forecast['eligible'] else None,
        },
        'gpu': {
            'state': 'MEASURED' if gpu_busy is not None else 'UNAVAILABLE',
            'busy_percent': gpu_busy,
        },
        'foreground_active': view['foreground_active'],
        'background_threads': view['policy']['background_threads'],
    }
