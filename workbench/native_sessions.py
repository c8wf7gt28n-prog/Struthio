"""Owned visible Calc sessions; the existing Kernel owns every process group."""
from pathlib import Path
from contextlib import contextmanager
import base64, fcntl, hashlib, json, os, socket, subprocess, time, uuid
from . import project_desk as records, problem_service as problems, typed_artifacts as artifacts
from . import office_math_runtime as native, office_runtime, math_units as units, math_service

LEASE = 540
EDIT = {'id': records.ID, 'expected_revision': records.REV}
FIELDS = {
    'joined.session.open': ({'job': records.ID}, ['job']),
    'joined.session.get': ({'id': records.ID}, ['id']),
    'joined.session.pause': (EDIT, list(EDIT)),
    'joined.session.takeover': (EDIT, list(EDIT)),
    'joined.session.resume': (EDIT, list(EDIT)),
    'joined.session.recalculate': (EDIT, list(EDIT)),
    'joined.session.close': (EDIT, list(EDIT)),
    'joined.session.edit': ({**EDIT, 'cell': {'type':'string','pattern':'^B[1-9][0-9]{0,3}$','maxLength':5},
                             'value': {'type':'string','minLength':1,'maxLength':80}}, [*EDIT, 'cell', 'value']),
    'joined.session.refresh': ({**EDIT, 'note': records.TEXT}, [*EDIT, 'note']),
}
SCOPES = {op: 'read' if op.endswith('.get') else 'approve' if op.endswith(('.takeover','.edit','.refresh')) else 'execute' for op in FIELDS}


def read(kernel, ident, p):
    with kernel.db() as db: return records.read(db, 'native_session', ident, p)


def guard_copies(kernel, copies, p):
    with kernel.db() as db:
        for (raw,) in db.execute("SELECT payload FROM desk_records WHERE owner=? AND kind='native_session'", (p.identity,)):
            row = json.loads(raw)
            if row['copy'] in copies and row['mode'] in ('TAKEOVER','REFRESH_REQUIRED'):
                raise ValueError('OWNER_TAKEOVER: resume or recheck the owned working file before automatic actions')


@contextmanager
def locked(kernel, ident):
    path = kernel.state/'native-session-locks'; path.mkdir(exist_ok=True)
    with (path/ident).open('a+b') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def update(kernel, value, p, expected, **changes):
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE'); live = records.read(db, 'native_session', value['id'], p)
        records.edit(live, expected); live.update(changes)
        records.write(db, live, p, 'OWNED_SESSION_' + live['mode'], expected=expected)
    return live


def parse_report(path, ident):
    lines = Path(path).read_text().splitlines()
    if not lines: raise ValueError('SESSION_EMPTY_REPLY')
    header = lines[0].split('\t')
    if header[0] == 'ERROR': raise ValueError('SESSION_NATIVE_COMMAND: ' + base64.b64decode(header[2]).decode())
    if len(header) != 6 or header[0] != 'SESSION' or header[1] != ident or header[3] != 'true' or int(header[4]) <= 0:
        raise ValueError('SESSION_NO_OWNED_VISIBLE_WINDOW')
    rows = {}
    for line in lines[1:]:
        f = line.split('\t')
        if len(f)!=7 or f[0]!='CELL' or f[1] in rows: raise ValueError('SESSION_MEASUREMENT_SCHEMA')
        rows[f[1]] = {'cell':f[1], 'formula':base64.b64decode(f[2]).decode(), 'value':f[3],
                     'cell_type':int(f[4]), 'unit':base64.b64decode(f[5]).decode(), 'error':f[6]}
    return {'mode':header[2], 'window_id':int(header[4]), 'title':base64.b64decode(header[5]).decode(), 'cells':rows}


def directory(kernel, value):
    if not value.get('job'): raise ValueError('SESSION_STARTING')
    return kernel.state/'jobs'/value['job']/'session'


def command(kernel, value, op, p, cell=None, data=None):
    from . import record_access, work_trail
    if work_trail.execution_held(kernel) and op != 'CLOSE': raise ValueError('SESSION_WORK_HELD')
    job = record_access.read(kernel, 'jobs', value['job'], p)
    if job['state'] not in ('Running','Queued'): raise ValueError('SESSION_ENDED: explicitly open another owned session')
    folder = directory(kernel, value); until = time.monotonic()+30
    while not (folder/'ready.tsv').is_file():
        if kernel.record('jobs', job['id'])['state'] not in ('Running','Queued') or time.monotonic()>until:
            raise ValueError('SESSION_NOT_READY')
        time.sleep(.05)
    ident = uuid.uuid4().hex
    content = ident+'\t'+op
    if cell is not None: content += '\t'+cell+'\t'+base64.b64encode(data.encode()).decode()
    temp = folder/'command.tmp'; temp.write_text(content+'\n'); os.replace(temp, folder/'command.tsv')
    target = folder/('reply-'+ident+'.tsv')
    while not target.is_file():
        if kernel.record('jobs', job['id'])['state'] not in ('Running','Queued') or time.monotonic()>until:
            raise ValueError('SESSION_NATIVE_REPLY_INCOMPLETE')
        time.sleep(.04)
    return parse_report(target, ident)


def authorize(kernel, options, p):
    from . import joined_work
    value = read(kernel, options['action'], p)
    if value['binding_digest'] != options['expected_digest'] or value['components'] != joined_work.components():
        raise ValueError('SESSION_ACTION_OR_IMPLEMENTATION_CHANGED')
    if value['expires'] <= time.time(): raise ValueError('SESSION_LEASE_EXPIRED')
    if not os.environ.get('DISPLAY'): raise ValueError('SESSION_REQUIRES_X11_DISPLAY: XWayland is supported through DISPLAY')
    if native.probe() != value['office']: raise ValueError('SESSION_OFFICE_ENGINE_CHANGED')
    return value


def open_session(kernel, args, p):
    from . import joined_work
    result = joined_work.result(kernel, args['job'], p)
    if result['state'] != 'AVAILABLE': raise ValueError('SESSION_NEEDS_CURRENT_CHECKED_WORKING_CALC')
    artifact = artifacts.read(kernel, result['receipt']['artifacts'][0]['id'], p)
    artifacts.require_current(kernel, artifact, p)
    if not os.environ.get('DISPLAY'): raise ValueError('SESSION_REQUIRES_X11_DISPLAY')
    with kernel.db() as db:
        for (raw,) in db.execute("SELECT payload FROM desk_records WHERE owner=? AND kind='native_session'", (p.identity,)):
            old = json.loads(raw)
            if old['artifact']['id']==artifact['id'] and old.get('job') and kernel.record('jobs',old['job'])['state'] in ('Queued','Running'):
                raise ValueError('An owned session already has this working file')
    value = records.new('native_session', p, schema='ledger.owned-calc-session/1',
        source_job=args['job'], copy=artifact['copy'], artifact=artifacts.reference(artifact),
        mode='PAUSED', job=None, expires=time.time()+LEASE, components=joined_work.components(), office=native.probe(),
        notice='Owned working copy; the session autosaves owner edits and saves before its bounded lease ends.')
    value['binding_digest'] = records.digest(value)
    with kernel.db() as db: records.write(db, value, p, 'OWNED_SESSION_PREPARED')
    job = records.result_of(kernel, 'jobs.submit', {'tool':'math.session',
        'calculation':{'action':value['id'],'expected_digest':value['binding_digest']},
        'request_key':'math-office:'+value['id'], 'timeout':600}, p)
    value = update(kernel, value, p, 1, job=job['id'])
    return get(kernel, value['id'], p)


def get(kernel, ident, p):
    from . import record_access
    value = read(kernel, ident, p); job = record_access.read(kernel, 'jobs', value['job'], p) if value.get('job') else None
    status = None
    if job:
        ready = directory(kernel, value)/'ready.tsv'
        if ready.is_file(): status = parse_report(ready, 'READY')
    return {'session':value, 'job_state':job['state'] if job else 'STARTING', 'reason':job.get('error') if job else None,
            'native':status, 'lease_remaining':max(0,int(value['expires']-time.time()))}


def work(kernel, job, p):
    options = job['request_spec']['calculation']; value = authorize(kernel, options, p)
    # open_session may still be committing the job link. The action itself is frozen.
    artifact = artifacts.read(kernel, value['artifact']['id'], p); artifacts.require_current(kernel, artifact, p)
    info = value['office']; folder = kernel.state/'jobs'/job['id']/'session'; folder.mkdir()
    uri = office_runtime.profile(folder/'profile'); config = folder/'cells.tsv'
    addresses = sorted({r['cell'] for r in artifact['data']['measurements']})
    config.write_text(''.join(address+'\t'+('INPUT' if address in artifact['data']['profile']['inputs'] else 'OUTPUT')+'\n' for address in addresses))
    with socket.socket() as sock: sock.bind(('127.0.0.1',0)); port = sock.getsockname()[1]
    env = {**os.environ, 'LANG':'C.UTF-8', 'SAL_USE_VCLPLUGIN':'gen', 'FONTCONFIG_FILE':str(office_runtime.font_config(folder/'fonts'))}
    server = [info['engine']['executable'], '-env:UserInstallation='+uri, '--nologo', '--nodefault', '--norestore',
        '--nofirststartwizard', '--accept=socket,host=127.0.0.1,port='+str(port)+',tcpNoDelay=1;urp;StarOffice.ServiceManager']
    helper = Path(__file__).with_name('LedgerSession.java'); jar = native.PIN.parent/info['bridge']['jar']
    client = [info['java'],'-Xmx256m','-cp',str(jar),str(helper),str(port),artifacts.path(kernel,artifact).as_uri(),
              str(config),str(folder),str(LEASE),value['id'][:10]]
    processes = []
    with (folder/'stdout.log').open('wb') as out, (folder/'stderr.log').open('wb') as err:
        try:
            processes.append(subprocess.Popen(server,stdin=subprocess.DEVNULL,stdout=out,stderr=err,env=env))
            processes.append(subprocess.Popen(client,stdin=subprocess.DEVNULL,stdout=out,stderr=err,env=env))
            while processes[1].poll() is None:
                if kernel.record('jobs',job['id']).get('cancel'): raise ValueError('OWNED_SESSION_CANCELLED')
                time.sleep(.15)
            if processes[1].returncode: raise ValueError('OWNED_SESSION_FAILED: '+(folder/'stderr.log').read_text(errors='replace')[-1600:])
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=2)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()
    print(json.dumps({'outcome':'PASS','owned_session_closed':True,'originals_changed':False}))


def control(kernel, op, args, p):
    from . import joined_work, continuing_work as flow
    with locked(kernel, args['id']):
        value = read(kernel, args['id'], p)
        if value['revision'] != args['expected_revision']: raise ValueError('SESSION_REVISION_CHANGED')
        artifact = artifacts.read(kernel, value['artifact']['id'], p)
        if op.endswith('.close') and value.get('job') and kernel.record('jobs',value['job'])['state'] not in ('Running','Queued'):
            update(kernel,value,p,value['revision'],mode='CLOSED')
            return get(kernel,value['id'],p)
        if op.endswith('.takeover'):
            # Install the lease before pausing work; a new intent sees the hold too.
            value = update(kernel, value, p, value['revision'], mode='TAKEOVER')
            for row in flow.dispatch(kernel, 'work.list', {}, p)['records']:
                if row['state'] in ('READY','RUNNING','RETRY'):
                    with kernel.db() as db: plan,_ = flow.load(db,row['id'],p)
                    if value['copy'] in plan['copies']: flow.dispatch(kernel,'work.pause',{'id':row['id']},p)
            observed = command(kernel, value, 'TAKEOVER', p)
        elif op.endswith('.edit'):
            if value['mode'] != 'TAKEOVER' or args['cell'] not in artifact['data']['profile']['inputs']:
                raise ValueError('OWNER_EDIT_REQUIRES_TAKEOVER_AND_DECLARED_INPUT')
            amount = units.rational(args['value'])
            if amount<0 or abs(amount)>10**15: raise ValueError('OWNER_INPUT_OUTSIDE_NUMERIC_PROFILE')
            observed = command(kernel,value,'EDIT',p,args['cell'],units.number_record(amount)['decimal'])
        elif op.endswith('.pause'):
            observed = command(kernel,value,'PAUSE',p)
            value = update(kernel,value,p,value['revision'],mode='PAUSED')
        elif op.endswith('.close'):
            observed = command(kernel,value,'CLOSE',p)
            value = update(kernel,value,p,value['revision'],mode='CLOSED')
        elif op.endswith('.resume'):
            observed = command(kernel,value,'SAVE_INSPECT' if value['mode'] in ('TAKEOVER','REFRESH_REQUIRED') else 'INSPECT',p)
            digest = hashlib.sha256(artifacts.path(kernel,artifact).read_bytes()).hexdigest()
            if digest != artifact['sha256'] or not artifact['checked']:
                revised = artifacts.owner_revision(kernel, artifact['id'], p, digest,
                    {**artifact['data'], 'owner_cells':observed['cells'], 'previous_checked_revision':value['artifact']}) if digest!=artifact['sha256'] else artifact
                value = update(kernel,value,p,value['revision'],mode='REFRESH_REQUIRED',changed_artifact=artifacts.reference(revised),observed=observed)
                return {**get(kernel,value['id'],p),'refresh_required':True}
            artifacts.require_current(kernel, artifact, p)
            observed = command(kernel,value,'RESUME',p)
            value = update(kernel,value,p,value['revision'],mode='AUTOMATION')
        elif op.endswith('.recalculate'):
            if value['mode'] != 'AUTOMATION': raise ValueError('SESSION_AUTOMATION_PAUSED')
            artifacts.require_current(kernel, artifact, p)
            observed = command(kernel,value,'RECALCULATE',p)
            expected = {r['cell']:r for r in artifact['data']['measurements'] if r['phase']=='REOPENED'}
            for address, row in observed['cells'].items():
                if address not in expected or row['error']!='0' or abs(units.rational(row['value'])-units.rational(expected[address]['value']))>FractionTolerance(expected[address]['value']):
                    raise ValueError('VISIBLE_CALC_DISAGREES_WITH_CHECKED_ARTIFACT')
            artifacts.require_current(kernel, artifact, p)
            from . import work_trail
            if work_trail.execution_held(kernel): raise ValueError('SESSION_WORK_HELD_BEFORE_OBSERVATION')
            receipt=records.new('native_session_observation',p,session=value['id'],artifact=artifacts.reference(artifact),
                native=observed,authority='ACTUAL_VISIBLE_CALC_RECALCULATION',physical_qualification=False)
            with kernel.db() as db: records.write(db,receipt,p,'VISIBLE_CALC_VALUES_CHECKED')
            observed=receipt
        elif op.endswith('.refresh'):
            return refresh(kernel,value,args,p)
        else: raise ValueError('Unknown owned session control')
        return {**get(kernel,value['id'],p), 'observation':observed}


def FractionTolerance(value):
    from fractions import Fraction
    return max(Fraction(1,10**10),abs(units.rational(value))/10**12)


def refresh(kernel, value, args, p):
    from . import joined_work, schedule_math, checked_methods
    artifact = artifacts.read(kernel,value['artifact']['id'],p)
    action = joined_work.read(kernel,'joined_action',joined_work.read(kernel,'joined_result',value['source_job'],p)['action'],p)
    if value['mode']=='REFRESH_REQUIRED':
        command(kernel,value,'PAUSE',p)
        observed=command(kernel,value,'INSPECT',p)
        digest=hashlib.sha256(artifacts.path(kernel,artifact).read_bytes()).hexdigest()
        if digest!=artifact['sha256']: raise ValueError('Owner edits changed again; Resume captures the new revision first')
        problem=math_service.current(kernel,action['problem'],p)
        problems.check_bound(problem,{'expected_revision':action['problem_revision'],'expected_context_digest':action['context_digest']})
        variables=json.loads(records.canonical(problem['variables']));byname={v['name']:v for v in variables};intervals={}
        for address,role in artifact['data']['profile']['inputs'].items():
            row=observed['cells'][address]
            if row['cell_type']!=1 or row['error']!='0' or row['unit']!=role['unit']:
                raise ValueError('Recheck accepts numeric declared inputs with unchanged units; other edits require explicit problem editing')
            amount=units.rational(row['value'])
            if amount<0: raise ValueError('Recheck requires nonnegative inputs')
            variable=byname[role['name']]
            if role['kind']=='quantity':
                _,oldfactor=units.unit_spec(variable['unit']);_,newfactor=units.unit_spec(role['unit'])
                variable['value']=str(amount*newfactor/oldfactor)
            else: intervals.setdefault(role['name'],{'unit':'s'})[role['field']]=str(amount)
            variable['basis']='Owner-edited Calc scenario: '+args['note']
        for name,interval in intervals.items(): byname[name]['value']=records.canonical(interval)
        original=joined_work.schedule(kernel,action['schedule'],p)
        schedule_math.evaluate({**problem,'variables':variables},original['arguments']['capacity'],original['arguments']['allocations'])
        if action.get('method'): checked_methods.require_accepted(kernel,action['method'],p)
        changes=problems.content(kernel,{'variables':variables,'assumptions':problem['assumptions']+
            ['Owner-supplied edited Calc scenario; original source assertions remain preserved.']},p)
        # The revised source scenario and its continuation cursor are atomic.
        # Retrying after a crash cannot silently make a second problem revision.
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE');live=records.read(db,'native_session',value['id'],p)
            if live!=value: raise ValueError('SESSION_CHANGED_DURING_RECHECK')
            revised=problems.load(db,problem['id'],p);problems.check_bound(revised,{'expected_revision':problem['revision'],'expected_context_digest':problem['context_digest']})
            records.edit(revised,problem['revision']);revised.update(changes);revised['context_digest']=problems.context_digest(revised)
            records.write(db,revised,p,'OWNER_CALC_SCENARIO_REVISED',expected=problem['revision'])
            records.edit(live,value['revision']);live.update(mode='PAUSED',recheck={
                'problem':{'id':revised['id'],'expected_revision':revised['revision'],'expected_context_digest':revised['context_digest']},
                'capacity':original['arguments']['capacity'],'allocations':original['arguments']['allocations'],
                'artifact_digest':digest,'schedule':None,'prepared':None})
            value=records.write(db,live,p,'OWNER_SCENARIO_AND_CONTINUATION_COMMITTED',expected=value['revision'])
    elif value['mode']!='PAUSED' or not value.get('recheck'):
        raise ValueError('No captured owner-edited revision requires rechecking')
    pending=value['recheck']
    if hashlib.sha256(artifacts.path(kernel,artifact).read_bytes()).hexdigest()!=pending['artifact_digest']:
        raise ValueError('WORKING_FILE_CHANGED_AFTER_OWNER_SCENARIO_COMMIT')
    current=math_service.current(kernel,pending['problem']['id'],p);problems.check_bound(current,pending['problem'])
    if pending['prepared']:
        prepared=joined_work.read(kernel,'joined_action',pending['prepared'],p)
        joined_work.check_action(kernel,prepared,p)
        receipt=joined_work.schedule(kernel,pending['schedule'],p)
    else:
        receipt=joined_work.schedule(kernel,pending['schedule'],p) if pending['schedule'] else records.result_of(kernel,'math.schedule',{
            **pending['problem'],'capacity':pending['capacity'],'allocations':pending['allocations']},p)
        pending={**pending,'schedule':receipt['id']}
        value=update(kernel,value,p,value['revision'],recheck=pending)
        prepared=joined_work.prepare(kernel,{'receipt':receipt['id'],'copy':action['copy']},p,method_ref=action.get('method'))
        pending={**pending,'prepared':prepared['id']};value=update(kernel,value,p,value['revision'],recheck=pending)
    return {**get(kernel,value['id'],p),'prepared':prepared,'schedule':receipt,
            'dependent_outputs':'STALE_UNTIL_NEW_CHAIN_COMPLETES','originals_changed':False}


def dispatch(kernel, op, args, p):
    if op=='joined.session.open': return open_session(kernel,args,p)
    if op=='joined.session.get': return get(kernel,args['id'],p)
    return control(kernel,op,args,p)
