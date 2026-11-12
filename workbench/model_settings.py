"""Saved launch defaults and bounded, caller-scoped model readback.

Defaults are real Kernel preferences. They never rewrite a selected/live model.
New activation/qualification jobs freeze resolved options at submission; their
original request_spec stays intact for idempotent retries.
"""
import copy,hashlib,json,sqlite3
from .settings_registry import BY_KEY,MODEL_KEYS

OPTIONS={('brain.'+key):key for key in ('context','threads','memory_mb','backend','gpu_layers','cpu_fallback')}
LAUNCH_KEYS=tuple(OPTIONS.values())
MAX_RECORD=128*1024
MAX_JOURNAL=1024*1024


def preferences(kernel,db=None):
    if db is None:
        with kernel.db() as connection:return preferences(kernel,connection)
    from .ledger_control import validate
    result={}
    for key,option in OPTIONS.items():
        row=db.execute('SELECT value FROM settings WHERE key=?',('ledger.'+key,)).fetchone()
        try:value=json.loads(row[0]) if row else BY_KEY[key]['default'];validate(key,value)
        except (ValueError,TypeError):raise ValueError('Local-model launch defaults are unavailable or invalid; stored data was not replaced.') from None
        result[option]=value
    return result


def freeze_launch(kernel,value,supplied,db=None):
    from . import local_brain as brain
    saved=preferences(kernel,db)
    options={key:value for key,value in saved.items() if key!='memory_mb' or value}
    options.update(copy.deepcopy(supplied or {}))
    from .resource_control import reclaimable
    config=brain.configuration(value,options,kernel.root,reclaimable(kernel,db))
    resolved={**options,**{key:config[key] for key in ('context','threads','memory_mb')},'model_id':value['id']}
    return dict(schema='arc.brain-launch-settings/1',options=resolved,saved_defaults=saved,
                basis='SAVED_DEFAULTS_WITH_EXPLICIT_REQUEST_OVERRIDES')


def job_options(job):
    from . import local_brain as brain
    request=job.get('request_spec')
    if not isinstance(request,dict) or not isinstance(request.get('brain',{}),dict):raise ValueError('MODEL_LAUNCH_REQUEST_INVALID')
    original=request.get('brain',{})
    frozen=job.get('brain_launch')
    if frozen is None:return original  # Earlier queued requests keep their original defaults.
    if not isinstance(frozen,dict) or frozen.get('schema')!='arc.brain-launch-settings/1':
        raise ValueError('MODEL_LAUNCH_SNAPSHOT_INVALID')
    options=frozen.get('options')
    from .agent_operations import validate
    validate(options,brain.OPTIONS)
    if config(options) is None:raise ValueError('MODEL_LAUNCH_SNAPSHOT_INCOMPLETE')
    if options.get('model_id')!=original.get('model_id'):raise ValueError('MODEL_LAUNCH_IDENTITY_CHANGED')
    return options


def config(value):
    if not isinstance(value,dict):return None
    bounds={'context':(512,8192),'threads':(1,32),'memory_mb':(512,262144)}
    if any(type(value.get(k)) is not int or not lo<=value[k]<=hi for k,(lo,hi) in bounds.items()):return None
    result={k:value[k] for k in bounds}
    # Earlier saved selections remain usable; missing backend fields mean the old CPU contract.
    backend=value.get('backend','CPU');requested=value.get('requested_backend',backend)
    layers=value.get('gpu_layers',0);fallback=value.get('cpu_fallback',True)
    if backend not in ('AUTO','CPU','VULKAN') or requested not in ('AUTO','CPU','VULKAN'):return None
    if type(layers) is not int or not -1<=layers<=512 or type(fallback) is not bool:return None
    result.update(backend=backend,requested_backend=requested,gpu_layers=layers,cpu_fallback=fallback)
    for key in ('device','observed_gpu_layers','offload_evidence','fallback_reason','resource_guard'):
        if key in value:result[key]=copy.deepcopy(value[key])
    return result


def selection(value,actor):
    if not isinstance(value,dict) or not value.get('model_id') or value.get('owner') not in (None,actor):return None
    ident=value['model_id']
    if not isinstance(ident,str) or len(ident)!=64 or any(c not in '0123456789abcdef' for c in ident):return None
    return dict(model_id=value['model_id'],config=config(value.get('config')))


def snapshot(kernel,actor):
    from . import local_brain as brain
    from sdk.cli.arc1cli.record_store import strict
    jobs=[];partial=False;budget=0
    with kernel.db() as db:
        db.execute('BEGIN')
        saved=preferences(kernel,db);selected=selection(brain.get(kernel,'selection',{},db),actor)
        previous=selection(brain.get(kernel,'previous',None,db),actor)
        worker=brain.get(kernel,'worker',{},db);handover=brain.get(kernel,'handover',None,db)
        if not isinstance(worker,dict):worker={};partial=True
        # Current requests are checked separately from bounded historical jobs.
        active=db.execute("SELECT length(CAST(payload AS BLOB)),CASE WHEN length(CAST(payload AS BLOB))<=? THEN payload END FROM jobs WHERE owner=? AND state IN ('Queued','Running') ORDER BY rowid DESC LIMIT 25",(MAX_RECORD,actor)).fetchall()
        recent=db.execute("SELECT length(CAST(payload AS BLOB)),CASE WHEN length(CAST(payload AS BLOB))<=? THEN payload END FROM jobs WHERE owner=? ORDER BY rowid DESC LIMIT 100",(MAX_RECORD,actor)).fetchall()
        seen=set()
        for size,raw in active+recent:
            budget+=size
            if not isinstance(raw,str) or budget>MAX_JOURNAL:partial=True;continue
            try:
                job=strict(raw)
                if not isinstance(job,dict) or job.get('owner')!=actor:raise ValueError('Invalid job')
                if job.get('tool') not in ('brain.activate','brain.qualify') or job.get('id') in seen:continue
                seen.add(job['id']);frozen=job.get('brain_launch')
                opts=job_options(job)
                jobs.append(dict(id=job['id'],tool=job['tool'],state=job['state'],model_id=opts.get('model_id'),
                                 options={key:opts.get(key) for key in LAUNCH_KEYS},
                                 frozen=frozen is not None))
            except (ValueError,KeyError,TypeError):partial=True
    owned=isinstance(worker,dict) and worker.get('owner')==actor
    live=owned and brain.worker_live(worker)
    same=bool(selected and worker and selected['model_id']==worker.get('model_id'))
    running=config(worker.get('config')) if live and same else None
    restored=worker.get('restored_after_job') if running else None
    if not isinstance(restored,str) or len(restored)!=32 or any(c not in '0123456789abcdef' for c in restored):restored=None
    state=('RESTORED_PREVIOUS' if restored else 'RUNNING_WORKER_READ_BACK') if running else (
        'WORKER_SELECTION_MISMATCH' if live and not same else 'WORKER_CONFIGURATION_UNAVAILABLE' if live else
        'OTHER_OWNER_WORKER' if worker and not owned else 'MODEL_STOPPED' if selected else 'NO_MODEL_SELECTED')
    pending=[row for row in jobs if row['state'] in ('Queued','Running')]
    value=dict(saved_defaults=saved,selection=selected,previous=previous,worker_config=running,state=state,
               pending=pending,last_operation=jobs[0] if jobs else None,restored_after_job=restored,
               handover=bool(isinstance(handover,dict) and any(j['id']==handover.get('job_id') for j in jobs)),
               recent_jobs_partial=partial,
               notice='Worker readback requires its owned process identity. Stored selection and queued requests are not running values. Recent history is bounded to 100 caller-owned jobs.')
    value['revision']=hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return value


def rows(kernel,actor,changes):
    from . import ledger_control as control
    try:runtime=snapshot(kernel,actor);error=None
    except (ValueError,TypeError,sqlite3.Error) as exc:runtime=None;error=str(exc)
    result={}
    for key in MODEL_KEYS:
        definition=BY_KEY[key];option=OPTIONS[key]
        current=runtime['saved_defaults'][option] if runtime else None
        running=runtime['worker_config'].get(option) if runtime and runtime['worker_config'] else None
        pending=runtime['pending'][0] if runtime and runtime['pending'] else None
        result[key]={**definition,'value':current,'stored':current,'effective':running,
            'revision':control._revision(key,current,changes),'store_revision':None,'editable':runtime is not None,
            'latest_change':next((r for r in changes if r['key']==key),None),'history_limit':100,
            'application_state':runtime['state'] if runtime else 'STORE_UNAVAILABLE',
            'effective_source':error or 'Saved launch default; effective is the owned live worker configuration. Apply/Undo change the default for a future explicit load, not a running reply.',
            'desktop_effects':[],'requested':pending['options'].get(option) if pending else None,
            'model_runtime':runtime,'runtime_revision':runtime['revision'] if runtime else None}
    return result
