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


# -- 0.8.7 A2 · the memory sum: exact terms for hybrid models, from the GGUF metadata gguf_inspect already reads ---------
# budget = weights x 1.3 + 384 MiB                                     (unchanged)
#        + KV over attention layers only x context
#        + one recurrent state
#        + checkpoints x one state
#        + the RAM prompt cache
# A model without full_attention_interval is dense: its estimate is today's, to the byte (the same expression), and it
# keeps reuse without checkpoints or a RAM cache (a dense KV prefix is kept by the slot itself), so nothing is added.
# Checked here against the server's log: one state is 50.251 MiB on the 4B and 19.266 MiB on the 2B; KV is 32 KiB a token
# on the 4B (design 4.5). Integer arithmetic for every hybrid term.
BASE_BYTES=384*MIB
# 1.0 M1: the RAM prompt cache is sized from the memory sum so every kept prompt fits (runtime_tuning.cache_mb: each
# entry its KV over 1,024 tokens and its checkpoints), then four of them (PLAN's, READ's, the slot's save and one more),
# then two checkpoints and 256 MiB, then reuse off. With 0.8.7's fixed 512 MiB on the 4B only two entries fitted, and the
# first PLAN question after Ready found PLAN's primed menu evicted (K4b's finding).
REUSE_LADDER_MB=((6,'ALL'),(6,'FEW'),(2,256),(0,0))  # (checkpoints, RAM prompt cache): the first rung the rule admits is taken
PROMPT_CACHE_LARGE_MB=1024                # 0.8.7's fixed caches, kept for reference: 1,024 MiB on a large model, 512 small
PROMPT_CACHE_SMALL_MB=512
LARGE_WEIGHTS_BYTES=8*1024*MIB
MTP_CONTEXT_BYTES=512*MIB                 # 1.0 M1: the MTP draft context's own buffers, an estimate the readback checks


def memory_shape(inspection):
    """The memory shape of a model from its GGUF metadata (gguf_inspect.inspect's 'metadata' and 'architecture'):
    DENSE (today's KV formula) or HYBRID (attention layers every full_attention_interval blocks, the rest recurrent).
    Raises MODEL_MEMORY_ESTIMATE_UNAVAILABLE when a term it needs is missing or not a positive whole number."""
    metadata=inspection['metadata'];architecture=inspection['architecture']
    def whole(key,default=None):
        value=metadata.get(architecture+'.'+key,default)
        if type(value) is not int or value<=0:raise ValueError('MODEL_MEMORY_ESTIMATE_UNAVAILABLE')
        return value
    layers=whole('block_count');embedding=whole('embedding_length');heads=whole('attention.head_count')
    kv_heads=whole('attention.head_count_kv',heads)
    shape={'kind':'DENSE','layers':layers,'embedding':embedding,'heads':heads,'kv_heads':kv_heads}
    if architecture+'.full_attention_interval' not in metadata:return shape
    interval=whole('full_attention_interval')
    head=embedding//heads
    key_length=whole('attention.key_length',head);value_length=whole('attention.value_length',key_length)
    inner=whole('ssm.inner_size');state=whole('ssm.state_size');groups=whole('ssm.group_count');conv=whole('ssm.conv_kernel')
    attention=layers//interval;recurrent=layers-attention        # llama.cpp: block i is attention when (i+1) % interval == 0
    shape.update(kind='HYBRID',interval=interval,attention_layers=attention,recurrent_layers=recurrent,
                 key_length=key_length,value_length=value_length,inner=inner,state=state,groups=groups,conv_kernel=conv,
                 # f16 K and V on the attention layers only
                 kv_bytes_per_token=attention*kv_heads*(key_length+value_length)*2,
                 # one recurrent state: the f32 SSM state and the f32 convolution window, on every recurrent layer
                 state_bytes=recurrent*(inner*state*4+(conv-1)*(inner+2*groups*state)*4))
    return shape


def preferred_cache_mb(total_bytes):
    return PROMPT_CACHE_LARGE_MB if total_bytes>LARGE_WEIGHTS_BYTES else PROMPT_CACHE_SMALL_MB


def _kv_per_token(shape,kv_type='f16',layers=None):
    """1.0 M1: K and V bytes a token for the attention layers (or `layers` of them) at the KV cache's type (f16 as before;
    q8_0 34 bytes a block of 32; f8_e4m3 one byte), rounded up to a whole byte."""
    from .runtime_tuning import kv_bytes
    if shape['kind']=='DENSE':
        count=shape['layers'] if layers is None else layers
        elements=count*(shape['embedding']*shape['kv_heads']//shape['heads'])       # K, and as many in V
        return kv_bytes(elements,kv_type)*2
    count=shape['attention_layers'] if layers is None else layers
    return kv_bytes(count*shape['kv_heads']*shape['key_length'],kv_type)+kv_bytes(count*shape['kv_heads']*shape['value_length'],kv_type)


def memory_sum(inspection,total_bytes,context,checkpoints=0,cache_mb=0,kv_type='f16',mtp=0):
    """The model's budget estimate in bytes, term by term. A dense model ignores checkpoints and cache (it has neither).
    1.0 M1: the KV cache's type (kv_type), and the MTP head when multi-token prediction is on (mtp: its layers, from the
    model's own file): its KV over the context and its draft context's buffers."""
    shape=memory_shape(inspection)
    if shape['kind']=='DENSE':
        kv=_kv_per_token(shape,kv_type)*context
        head=(_kv_per_token(shape,kv_type,mtp)*context+MTP_CONTEXT_BYTES) if mtp else 0
        return {'kind':'DENSE','estimate':int(total_bytes*1.3)+kv+BASE_BYTES+head,'weights':total_bytes,'kv':kv,'state':0,
                'checkpoints':0,'checkpoint_bytes':0,'cache_mb':0,'cache':0,'base':BASE_BYTES,'kv_type':kv_type,'mtp':head}
    weights=-(-total_bytes*13//10)                                   # x 1.3, rounded up, in whole bytes
    per=_kv_per_token(shape,kv_type);kv=per*context;state=shape['state_bytes']
    head=(_kv_per_token(shape,kv_type,mtp)*context+MTP_CONTEXT_BYTES) if mtp else 0
    if cache_mb in ('ALL','FEW'):
        from .runtime_tuning import KEPT_PROMPTS,KEPT_PROMPTS_FEW,cache_mb as sized
        cache_mb=sized(state,per,checkpoints,KEPT_PROMPTS if cache_mb=='ALL' else KEPT_PROMPTS_FEW)
    cache=cache_mb*MIB
    return {'kind':'HYBRID','estimate':weights+BASE_BYTES+kv+state+checkpoints*state+cache+head,'weights':total_bytes,
            'kv':kv,'kv_per_token':per,'state':state,'checkpoints':checkpoints,
            'checkpoint_bytes':checkpoints*state,'cache_mb':cache_mb,'cache':cache,'base':BASE_BYTES,'kv_type':kv_type,'mtp':head}


def reuse_ladder(inspection,total_bytes,context,kv_type='f16',mtp=0):
    """The rungs the memory rule tries, best first (1.0 M1): six checkpoints and a RAM cache for every kept prompt; six
    and a cache for four; two and 256 MiB; then reuse off (today's launch). A dense model has the one rung, today's."""
    if memory_shape(inspection)['kind']=='DENSE':return [memory_sum(inspection,total_bytes,context,kv_type=kv_type,mtp=mtp)]
    return [memory_sum(inspection,total_bytes,context,checkpoints,cache,kv_type,mtp) for checkpoints,cache in REUSE_LADDER_MB]
# -- end 0.8.7 A2 -------------------------------------------------------------------------------------------------------


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
        handover=options.get('slot')!='quick'      # 1.0 M2: the quick model starts beside hers: no handover, no credit
        if not handover:
            return dict(priority=priority,lane='inference',memory_bytes=options.get('memory_mb',1024)*MIB,
                        basis='FROZEN_MODEL_MEMORY_BUDGET',model_handover=False)
        headroom=(job.get('brain_launch') or {}).get('auto_headroom_mb') or 0      # Auto's headroom stays with its budget
        budget=(options.get('memory_mb',1024)+headroom)*MIB;lane='inference';basis='FROZEN_MODEL_MEMORY_BUDGET'
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
    for key in ('brain.worker','brain.trial_worker','brain.quick_worker'):   # 1.0 M2: the quick model counts in the sum too
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


LAUNCH_WAIT=8.0     # seconds a launch waits after a handover for the stopped model's memory to come back


def model_room(kernel,config,ident):
    from .brain_runtime import host
    with kernel.db() as db:view=_view(kernel,db,host(profile=False),ident)
    # budget_room, as at admission; the previous worker has stopped by now, so no handover credit is left to add.
    # Auto's headroom (config['headroom_mb']) is kept with its budget here too, as at admission.
    if view['available_bytes'] is None or (config['memory_mb']+(config.get('headroom_mb') or 0))*MIB>budget_room(
            view['available_bytes'],view['policy']['reserve_bytes'],view['reserved_future_bytes']):
        raise ValueError('GRAPHITE_HOST_MEMORY_LIMIT: model launch no longer has admitted shared-memory headroom')
    return view['policy']


def await_room(kernel,config,ident,seconds=None,check=None):
    """After a sequential handover stops the old worker, its memory comes back over a moment, not at the instant the
    process ends. Wait for the launch room (model_room), bounded, rather than refuse a launch admission allowed and lose
    the previous model with it. `check` (local_brain.check_job) is asked each round, so a cancel still ends the wait."""
    end=time.monotonic()+(LAUNCH_WAIT if seconds is None else seconds)
    while True:
        if check is not None:check()
        try:return model_room(kernel,config,ident)
        except ValueError:
            if time.monotonic()>=end:raise
            time.sleep(.25)


def background_reason(kernel):
    from .brain_runtime import host
    with kernel.db() as db:
        view=_view(kernel,db,host(profile=False))
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
