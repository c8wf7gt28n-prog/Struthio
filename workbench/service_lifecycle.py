"""Owner service-cycle state over the existing admission, work gate and journal.

These are trusted local presentation adapters, not new command permissions.
The coordinator stays available as the control plane. No host power is invoked.
"""
import json,os,re,sqlite3,time,uuid
from . import activity,ledger_control,work_trail
from .operation_stop import process_identity,TERMINAL,UNKNOWN

KEY='ledger.service_cycle'
ADMISSION='operations.services_enabled'
ACTIVE=frozenset(('DRAINING','STOPPING'))
PHASES=ACTIVE|{'OFF','ON','HELD','FAILED'}
RESTORE_STATES=('REQUESTED','SKIPPED_SLATE_OFF','FAILED','NOT_REQUESTED')
# Every saved row carries these; a row missing one is unreadable, never a KeyError later.
FIELDS={'id':(str,),'action':(str,),'actor':(str,),'desktop_id':(str,),'pid':(int,),'start':(str,),'started_at':(int,float),
    'phase':(str,),'gate_epoch':(int,),'admission_revision':(str,),'updated_at':(int,float)}
COUNTS=('queued','running','live_workers','protected_workers','stale_running')
SUMMARIES={'ADMISSION_ON':'New work enabled','ADMISSION_HELD':'New work held; full service stop not confirmed',
    'DRAINING':'Finishing running work; new work held','STOPPING':'Closing owned model, phone and tool services',
    'OFF':'Graphite services off; desktop stays open','ON':'New work enabled',
    'FAILED':'Service cycle incomplete; inspect before switching On','HELD':'A newer service decision interrupted this cycle',
    'CHANGED':'Admission or Stop changed; previous cycle is no longer current',
    'INTERRUPTED':'Service cycle interrupted; choose On or Off explicitly',
    'UNAVAILABLE':'Graphite service state unavailable; inspect before continuing'}
CONTROL_PLANE='Desktop and service controls stay available; the computer stays on'


def owner(principal):
    if not {'approve','execute'}<=principal.scopes or principal.mode=='Tutor':
        raise ValueError('SERVICE_CYCLE_REQUIRES_OWNER')


def read(db):
    value=ledger_control.stored(db,KEY,None)
    if value is None:return None
    if not (isinstance(value,dict) and value.get('schema')=='ledger.service-cycle/1' and value.get('phase') in PHASES
            and all(type(value.get(key)) in kinds for key,kinds in FIELDS.items()) and re.fullmatch('[a-f0-9]{32}',value['id'])
            and value['action'] in ('On','Off','Reboot') and value.get('model_restore','NOT_REQUESTED') in RESTORE_STATES):
        raise ValueError('SERVICE_CYCLE_UNAVAILABLE: inspect local service state before continuing')
    return value


def live(kernel,row):
    return bool(row and re.fullmatch(r'[A-Za-z0-9_-]{1,100}',row.get('desktop_id',''))
        and (kernel.state/'desktops'/(row['desktop_id']+'.json')).is_file()
        and row.get('start') not in (None,UNKNOWN) and process_identity(row.get('pid'))==row['start'])


def admission(db):
    value=ledger_control.stored(db,'ledger.'+ADMISSION,True)
    ledger_control.validate(ADMISSION,value)
    return value,ledger_control._revision(ADMISSION,value,ledger_control._history(db))


def jobs(kernel,db):
    """Existing durable non-terminal jobs plus owned worker observations, without a launcher.

    Finished rows keep their exited worker pid, and probing an exited pid scans
    /proc; only Queued, Running and waiting rows are read. ``stale_running``
    counts Running rows whose recorded worker is not observed live, less any
    protected worker run that may not have recorded its pid yet.
    """
    queued=[];running=[];live_workers=[];stale=0
    for raw, in db.execute('SELECT payload FROM jobs WHERE state IS NULL OR state NOT IN (?,?,?)',tuple(sorted(TERMINAL))):
        row=json.loads(raw);token=row.get('worker_start')
        alive=token not in (None,UNKNOWN) and process_identity(row.get('pid'))==token
        if row['state']=='Queued':queued.append(row['id'])
        if row['state']=='Running':
            running.append(row['id'])
            if not alive:stale+=1
        if alive:live_workers.append(row['id'])
    protected=db.execute("SELECT count(*) FROM worker_runs WHERE state IN ('STARTING','RUNNING','CLEANUP_REQUIRED')").fetchone()[0]
    return dict(queued=queued,running=running,live_workers=live_workers,protected_workers=protected,stale_running=max(0,stale-protected))


def _save(db,row):
    row={**row,'updated_at':time.time()}
    db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(KEY,json.dumps(row)))
    return row


def _new(kernel,action,principal,desktop_id):
    if not isinstance(desktop_id,str) or not re.fullmatch('[A-Za-z0-9_-]{1,100}',desktop_id):raise ValueError('Invalid desktop identity')
    token=process_identity(os.getpid())
    if token in (None,UNKNOWN) or not (kernel.state/'desktops'/(desktop_id+'.json')).is_file():
        raise ValueError('SERVICE_DESKTOP_NOT_LIVE: reconnect the desktop before changing services')
    return dict(schema='ledger.service-cycle/1',id=uuid.uuid4().hex,action=action,actor=principal.identity,
        desktop_id=desktop_id,pid=os.getpid(),start=token,started_at=time.time(),model_restore='NOT_REQUESTED')


def _setting(db,value,principal):
    old,_=admission(db)
    record=dict(id=uuid.uuid4().hex,key=ADMISSION,before=old,after=value,actor=principal.identity,
        at=time.time(),undone=False,scope=ledger_control.BY_KEY[ADMISSION]['scope_id'])
    db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('ledger.'+ADMISSION,json.dumps(value)))
    db.execute('INSERT INTO settings VALUES(?,?)',('ledger.change.'+record['id'],json.dumps(record)))
    activity.append(db,activity.make_event(principal.identity,'ledger.settings.set','APPLIED',ADMISSION,correlation_id=record['id']))
    ledger_control._trim_history(db)
    return ledger_control._revision(ADMISSION,value,[record])


def _guard(db,kernel,receipt):
    current=read(db);enabled,revision=admission(db);gate=work_trail.work_status(kernel,db)
    if not current or current['id']!=receipt['id']:raise ValueError('SERVICE_CYCLE_SUPERSEDED: another service decision exists')
    if not live(kernel,current):raise ValueError('SERVICE_DESKTOP_NOT_LIVE: interrupted cycles require an explicit new decision')
    if current['admission_revision']!=revision or current['gate_epoch']!=gate['epoch']:
        raise ValueError('SERVICE_CYCLE_CHANGED: a newer Stop, Resume or admission change exists; no automatic restart')
    return current,enabled,gate


def begin(kernel,action,principal,desktop_id):
    owner(principal)
    if action not in ('Off','Reboot'):raise ValueError('Choose Off or Reboot')
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');previous=read(db)
        if previous and previous['phase'] in ACTIVE and live(kernel,previous):raise ValueError('SERVICE_CYCLE_BUSY: services are already draining')
        row=_new(kernel,action,principal,desktop_id)
        # The receipt and admission hold commit together; no crash gap can leave
        # a recorded stop accepting new jobs. The work epoch stays unchanged
        # until running work has actually drained.
        row.update(phase='DRAINING',gate_epoch=work_trail.work_status(kernel,db)['epoch'],admission_revision=_setting(db,False,principal))
        activity.append(db,activity.make_event(principal.identity,'ledger.services',action.upper()+'_REQUESTED',correlation_id=row['id']))
        return _save(db,row)


def stop_gate(kernel,receipt,principal):
    owner(principal)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');row,enabled,gate=_guard(db,kernel,receipt);pending=jobs(kernel,db)
        if row['phase']!='DRAINING' or enabled:raise ValueError('SERVICE_CYCLE_PHASE_CHANGED')
        if any(pending.values()):raise ValueError('SERVICE_WORK_STILL_ACTIVE')
        gate=dict(held=True,epoch=gate['epoch']+1)
        db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('ledger.work_gate',json.dumps(gate)))
        activity.append(db,activity.make_event(principal.identity,'ledger.work.hold','HELD'))
        return _save(db,{**row,'phase':'STOPPING','gate_epoch':gate['epoch']})


def guard_stopping(kernel,cycle_id,principal):
    owner(principal)
    with kernel.db() as db:
        row=read(db)
        if not row or row['id']!=cycle_id:raise ValueError('SERVICE_CYCLE_SUPERSEDED')
        row,enabled,gate=_guard(db,kernel,row)
        if row['phase']!='STOPPING' or enabled or not gate['held'] or not live(kernel,row):raise ValueError('SERVICE_STOP_NOT_OWNED')
        if any(jobs(kernel,db).values()):raise ValueError('SERVICE_WORK_STILL_ACTIVE')
        return row


def stopped(kernel,receipt,principal):
    owner(principal)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');row,enabled,gate=_guard(db,kernel,receipt)
        if row['phase']!='STOPPING' or enabled or not gate['held'] or any(jobs(kernel,db).values()):raise ValueError('SERVICE_WORK_STILL_ACTIVE')
        activity.append(db,activity.make_event(principal.identity,'ledger.services','OFF',correlation_id=row['id']))
        return _save(db,{**row,'phase':'OFF'})


def start(kernel,principal,desktop_id,receipt=None):
    """Explicit On, or the guarded second half of this exact Reboot.

    Admission, gate release, ordinary setting history and cycle readback share
    one SQLite transaction. This cannot release a later Master Stop epoch.
    """
    owner(principal)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');previous=read(db)
        if receipt:
            row,enabled,gate=_guard(db,kernel,receipt)
            if row['action']!='Reboot' or row['phase']!='OFF' or not live(kernel,row):raise ValueError('SERVICE_REBOOT_NOT_OWNED')
        else:
            if previous and previous['phase'] in ACTIVE and live(kernel,previous):raise ValueError('SERVICE_CYCLE_BUSY: let running work finish')
            row=_new(kernel,'On',principal,desktop_id);enabled,_=admission(db);gate=work_trail.work_status(kernel,db)
        if gate['held']:
            pending=jobs(kernel,db)
            if any(pending.values()):raise ValueError('WORK_STILL_ACTIVE_RECONCILE_FIRST')
            gate=dict(held=False,epoch=gate['epoch']+1)
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('ledger.work_gate',json.dumps(gate)))
            activity.append(db,activity.make_event(principal.identity,'ledger.work.resume','ACCEPTING_NEW_WORK'))
        revision=_setting(db,True,principal)
        activity.append(db,activity.make_event(principal.identity,'ledger.services','ON',correlation_id=row['id']))
        return _save(db,{**row,'phase':'ON','gate_epoch':gate['epoch'],'admission_revision':revision})


def restore_note(kernel,receipt,principal,state,job_id=None,model_id=None):
    """Record what was asked of the model, and which job and model id, so readback can later observe the outcome."""
    owner(principal)
    if state not in RESTORE_STATES:raise ValueError('Invalid restore state')
    if job_id is not None and not (isinstance(job_id,str) and re.fullmatch('[a-f0-9]{32}',job_id)):raise ValueError('Invalid restore job identity')
    if model_id is not None and not (isinstance(model_id,str) and 0<len(model_id)<=200):raise ValueError('Invalid restore model identity')
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');row,enabled,gate=_guard(db,kernel,receipt)
        if row['phase']!='ON' or not enabled or gate['held']:raise ValueError('SERVICE_CYCLE_CHANGED')
        extra={key:value for key,value in (('model_restore_job',job_id),('model_restore_model',model_id)) if value is not None}
        return _save(db,{**row,'model_restore':state,**extra})


def fail(kernel,receipt,principal):
    owner(principal)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');row=read(db)
        if not row or row['id']!=receipt['id']:return # Never replace a newer cycle.
        if row['phase'] not in ACTIVE:
            # ON and OFF were committed only after their checks passed; a later
            # step's failure is journaled, never a downgrade of confirmed state.
            activity.append(db,activity.make_event(principal.identity,'ledger.services','INCOMPLETE_AFTER_'+row['phase'],correlation_id=row['id']))
            return row
        # Do not override a newer owner's admission value or work epoch.
        try:_guard(db,kernel,receipt);phase='FAILED'
        except ValueError:phase='HELD'
        activity.append(db,activity.make_event(principal.identity,'ledger.services',phase,correlation_id=row['id']))
        return _save(db,{**row,'phase':phase})


def restore_display(kernel,row):
    """Observed readback beside the stored request note; the request alone is never a running claim."""
    stored=row.get('model_restore','NOT_REQUESTED') if row else 'NOT_REQUESTED'
    if stored!='REQUESTED':return stored
    model_id=row.get('model_restore_model');job_id=row.get('model_restore_job')
    try:
        if model_id:
            from . import local_brain
            brain=local_brain.status(kernel)
            if brain['state']=='READY' and (brain.get('selection') or {}).get('model_id')==model_id:return 'OBSERVED_RUNNING'
        if job_id:
            state=kernel.record('jobs',job_id).get('state')
            if state in TERMINAL and state!='Completed':return 'REQUEST_FAILED'
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error):pass
    return stored


def unavailable(error):
    """Schema-shaped readback for an unreadable cycle row; conservative display values, never a closure claim."""
    return dict(schema='ledger.service-status/1',phase='UNAVAILABLE',summary=SUMMARIES['UNAVAILABLE'],admission_enabled=False,
        work_held=True,controller_live=False,cycle_id=None,action=None,updated_at=None,counts={key:0 for key in COUNTS},
        model_restore='NOT_REQUESTED',model_restore_display='NOT_REQUESTED',control_plane=CONTROL_PLANE,
        qualification='Cycle row unreadable; admission and work-gate values shown here are conservative placeholders, not readings',
        error=str(error))


def snapshot(kernel):
    """Read policy and controller provenance separately; never start a service."""
    with kernel.db() as db:
        row=read(db);enabled,revision=admission(db);gate=work_trail.work_status(kernel,db);pending=jobs(kernel,db)
    phase='ADMISSION_ON' if enabled and not gate['held'] else 'ADMISSION_HELD'
    connected=live(kernel,row)
    if row:
        matches=row['admission_revision']==revision and row['gate_epoch']==gate['epoch']
        if row['phase'] in ACTIVE:phase=row['phase'] if connected and matches else 'INTERRUPTED' if not connected else 'CHANGED'
        elif not matches:phase='CHANGED'
        else:phase=row['phase']
    return dict(schema='ledger.service-status/1',phase=phase,summary=SUMMARIES[phase],admission_enabled=enabled,
        work_held=gate['held'],controller_live=connected,cycle_id=row['id'] if row else None,
        action=row['action'] if row else None,updated_at=row['updated_at'] if row else None,
        counts={key:len(value) if isinstance(value,list) else value for key,value in pending.items()},
        model_restore=row.get('model_restore','NOT_REQUESTED') if row else 'NOT_REQUESTED',
        model_restore_display=restore_display(kernel,row),control_plane=CONTROL_PLANE,
        qualification='Controller and existing store readback; owner-host acceptance remains separate')


def require_admission(kernel):
    with kernel.db() as db:
        enabled,_=admission(db)
        if not enabled:raise ValueError('LEDGER_SERVICES_OFF: use Menu → Graphite services → On before starting work')
        work_trail.accepting(kernel,db)


def close_owned_services(kernel,principal,cycle_id,remote_stop=None):
    """Backend-owned handles only. The control coordinator remains reachable."""
    guard_stopping(kernel,cycle_id,principal)
    from . import local_brain,desktop_services
    local_brain.stop(kernel)
    if remote_stop is not None:remote_stop()
    else:
        reply=kernel.dispatch('remote.disable',{},principal)
        if not reply.get('ok'):raise ValueError('Phone access revocation needs reconciliation')
    for session in list(getattr(kernel,'console_sessions',{}).values()):
        if not session.closed:session.close()
        process=getattr(session,'process',None)
        if not session.closed or process is not None and process.poll() is None:raise ValueError('Console process exit is not confirmed')
    desktop_services.close_all(kernel.root)
    if desktop_services.active_processes(kernel.root):raise ValueError('Desktop tool exit is not confirmed')
    if local_brain.status(kernel).get('worker') is not None:raise ValueError('Model process exit is not confirmed')
    return dict(state='OWNED_SERVICES_CLOSED',model_stopped=True,phone_revoked=True,consoles_closed=True,desktop_tools_closed=True)
