"""Owner-granted continuing assignments on the existing Agenda and Kernel.

Frozen calls are data, not authority. The grant names the exact order digest,
operations, copies and budgets. Original publication, exports, arbitrary native
commands, grants and scheduler mutation are deliberately outside this executor.
"""
from __future__ import annotations
import contextlib
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid
from . import project_desk as records, edit_storage as store, change_sets, work_trail, work_scope

ID = records.ID
SHA = change_sets.SHA
KEY = {'type': 'string', 'minLength': 1, 'maxLength': 64, 'pattern': '^[A-Za-z][A-Za-z0-9_]*$'}
PATH = change_sets.PATH
OPS = {'work.read': 'read', 'work.query': 'read', 'changes.propose': 'draft', 'changes.report': 'draft',
       'changes.apply': 'working_write', 'workers.inspect': 'parse', 'workers.check': 'check', 'workers.draft': 'model_draft'}
ASSERTION = {'type': 'object', 'additionalProperties': False, 'properties': {
    'path': {'type': 'array', 'maxItems': 12, 'items': {'type': 'string', 'maxLength': 100}},
    'equals': {}}, 'required': ['path', 'equals']}
STEP = {'type': 'object', 'additionalProperties': False, 'properties': {
    'key': KEY, 'operation': {'type': 'string', 'enum': list(OPS)}, 'arguments': {'type': 'object'},
    'after': {'type': 'array', 'maxItems': 16, 'items': KEY},
    'seconds': {'type': 'integer', 'minimum': 1, 'maximum': 600},
    'retries': {'type': 'integer', 'minimum': 0, 'maximum': 2},
    'require': {'type': 'array', 'maxItems': 16, 'items': ASSERTION}}, 'required': ['key', 'operation', 'arguments', 'after']}
BUDGET = {**records.BUDGET, 'properties': {**records.BUDGET['properties'],
    'output_bytes': {'type': 'integer', 'minimum': 1, 'maximum': 4194304},
    'failures': {'type': 'integer', 'minimum': 1, 'maximum': 10},
    'quiet': {'type': 'integer', 'minimum': 1, 'maximum': 10}}}
CREATE = {'assignment': ID, 'copies': {'type': 'array', 'minItems': 1, 'maxItems': 4, 'items': ID},
    'steps': {'type': 'array', 'minItems': 1, 'maxItems': 64, 'items': STEP}, 'budget': BUDGET,
    'expires': {'type': 'number', 'minimum': 1}, 'title': records.TITLE}
FIELDS = {
    'work.create': (CREATE, ['assignment', 'copies', 'steps', 'budget', 'expires', 'title']),
    'work.list': (records.PAGE, []), 'work.get': ({'id': ID}, ['id']),
    'work.authorize': ({'id': ID, 'expected_digest': SHA}, ['id', 'expected_digest']),
    'work.pause': ({'id': ID}, ['id']), 'work.resume': ({'id': ID}, ['id']),
    'work.revoke': ({'id': ID, 'reason': records.TITLE}, ['id', 'reason']),
    'work.advance': ({'id': ID}, ['id']),
    'work.review': ({'id': ID, 'decision': {'type': 'string', 'enum': ['ACCEPT', 'CHANGES_REQUESTED', 'DEFER']},
                     'note': records.TEXT}, ['id', 'decision', 'note']),
    'work.read': ({'copy': ID, 'path': PATH}, ['copy', 'path']),
    'work.query': ({'text': {'type': 'string', 'minLength': 1, 'maxLength': 4096}}, ['text']),
    'procedures.save': ({'work': ID, 'title': records.TITLE, 'parameters': {'type': 'object'}}, ['work', 'title', 'parameters']),
    'procedures.list': (records.PAGE, []), 'procedures.get': ({'id': ID}, ['id']),
    'procedures.instantiate': ({'id': ID, 'assignment': ID, 'copies': CREATE['copies'], 'values': {'type': 'object'},
        'budget': BUDGET, 'expires': CREATE['expires'], 'title': records.TITLE},
        ['id', 'assignment', 'copies', 'values', 'budget', 'expires', 'title']),
}
SCOPES = {op: 'read' if op in ('work.list','work.get','work.read','work.query','procedures.list','procedures.get') else
          'approve' if op in ('work.authorize','work.revoke','work.resume','work.review','procedures.save') else 'execute' for op in FIELDS}
FINAL = {'REVIEW', 'ACCEPTED', 'CHANGES_REQUESTED', 'REVOKED', 'LIMIT'}
CRASH_AT = None


class Crash(BaseException): pass


def fault(point):
    if CRASH_AT == point: raise Crash(point)


MIGRATIONS = [(1, (
    'CREATE TABLE flow_orders(id TEXT PRIMARY KEY,owner TEXT NOT NULL,plan TEXT NOT NULL,digest TEXT NOT NULL,state TEXT NOT NULL,payload TEXT NOT NULL)',
    'CREATE INDEX flow_owner ON flow_orders(owner,state)',
    'CREATE TABLE flow_grants(id TEXT PRIMARY KEY,work TEXT NOT NULL UNIQUE,owner TEXT NOT NULL,payload TEXT NOT NULL,digest TEXT NOT NULL,revoked REAL)',
    'CREATE TABLE flow_steps(work TEXT NOT NULL,key TEXT NOT NULL,state TEXT NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(work,key))',
    'CREATE TABLE flow_events(seq INTEGER PRIMARY KEY AUTOINCREMENT,work TEXT NOT NULL,actor TEXT NOT NULL,event TEXT NOT NULL,payload TEXT NOT NULL,at REAL NOT NULL)',
    'CREATE TABLE flow_agenda(agenda TEXT PRIMARY KEY,work TEXT NOT NULL UNIQUE)',
    'CREATE TABLE flow_procedures(id TEXT PRIMARY KEY,owner TEXT NOT NULL,payload TEXT NOT NULL,digest TEXT NOT NULL)',
))]


def ensure(db):
    if not db.in_transaction: db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS flow_migrations(version INTEGER PRIMARY KEY,digest TEXT NOT NULL,at REAL NOT NULL)')
    applied = dict(db.execute('SELECT version,digest FROM flow_migrations'))
    known = {v: records.digest(sql) for v, sql in MIGRATIONS}
    if sorted(applied) != list(range(1, len(applied)+1)) or any(known.get(v) != d for v,d in applied.items()):
        raise ValueError('WORK_MIGRATION_UNSUPPORTED')
    for v, sql in MIGRATIONS:
        if v in applied: continue
        for statement in sql: db.execute(statement)
        db.execute('INSERT INTO flow_migrations VALUES(?,?,?)', (v, known[v], time.time()))


def event(db, plan, action, detail=None):
    db.execute('INSERT INTO flow_events(work,actor,event,payload,at) VALUES(?,?,?,?,?)',
        (plan['id'], plan['owner'], action, records.canonical(detail or {}), time.time()))


def load(db, ident, principal):
    from .engineering_kernel import identifier
    identifier(ident)
    row = db.execute('SELECT plan,digest,state,payload FROM flow_orders WHERE id=? AND owner=?', (ident, principal.identity)).fetchone()
    if not row: raise ValueError('Work order unavailable to this caller')
    plan = json.loads(row[0]); state = json.loads(row[3])
    if records.digest(plan) != row[1]: raise ValueError('WORK_PLAN_DAMAGED')
    if state['state'] != row[2]: raise ValueError('WORK_STATE_DAMAGED')
    return plan, state


def save(db, plan, state, action, detail=None):
    state['updated'] = time.time()
    db.execute('UPDATE flow_orders SET state=?,payload=? WHERE id=?', (state['state'], records.canonical(state), plan['id']))
    event(db, plan, action, detail)
    agenda_sync(db, plan, state)


def step_row(db, work, key):
    row = db.execute('SELECT payload FROM flow_steps WHERE work=? AND key=?', (work, key)).fetchone()
    if not row: raise ValueError('Work step unavailable')
    return json.loads(row[0])


def step_save(db, work, step):
    db.execute('INSERT OR REPLACE INTO flow_steps VALUES(?,?,?,?)', (work, step['key'], step['state'], records.canonical(step)))


def agenda_sync(db, plan, state):
    row = db.execute('SELECT agenda FROM flow_agenda WHERE work=?', (plan['id'],)).fetchone()
    if not row: return
    target = {'READY':'NEXT', 'RUNNING':'RUNNING', 'RETRY':'LATER', 'REVIEW':'DONE', 'ACCEPTED':'DONE',
              'REVOKED':'CANCELLED', 'LIMIT':'STOPPED', 'CHANGES_REQUESTED':'DONE'}.get(state['state'], 'PAUSED')
    db.execute('UPDATE agenda_items SET state=?,due=?,reason=?,outcome=?,updated=?,finished=? WHERE id=?',
        (target, state.get('retry_at') if target=='LATER' else None, state.get('reason'),
         'Continuing assignment · '+state['state'].lower(), time.time(), time.time() if target in ('DONE','STOPPED','CANCELLED') else None, row[0]))


def signatures(kernel, copies, principal):
    result = {}
    for ident in copies:
        meta, row, root = store.workspace(kernel, ident, principal)
        current = change_sets.tree(kernel, root, meta, tracked=change_sets.load_base(kernel,row)['files'])
        result[ident] = {'work': row['work'], 'profile': meta['profile'], 'files': {
            p: {'sha256': f['sha256'], 'mode': f['mode']} for p,f in current['files'].items()}}
    return result


def executor_identity():
    import hashlib
    root=Path(__file__).resolve().parent
    return records.digest({name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
        ('continuing_work.py','work_scope.py','engineering_kernel.py','engineering_cli.py','change_sets.py','worker_boundary.py',
         'adaptive_work.py','adaptive_contract.py','slate_action.py','schedule_math.py','slate_stream.py',
         'local_brain.py','brain_worker.py','brain_runtime.py','math_service.py','math_model.py','math_backend.py','math_units.py',
         'joined_work.py','typed_artifacts.py','checked_methods.py','native_sessions.py','LedgerSession.java','project_context.py')})


def reference_dependencies(value):
    found = set()
    if isinstance(value, dict):
        if '$step' in value:
            if set(value) != {'$step','path'} or not isinstance(value['path'],list) or len(value['path'])>12:
                raise ValueError('Use a typed step reference with $step and path')
            if any(not isinstance(p,str) or len(p)>100 for p in value['path']): raise ValueError('Invalid reference path')
            found.add(value['$step'])
        else:
            for child in value.values(): found |= reference_dependencies(child)
    elif isinstance(value,list):
        for child in value: found |= reference_dependencies(child)
    return found


def create(kernel, args, principal, procedure=None, adaptive=None):
    from .engineering_cli import schemas
    from .agent_operations import validate
    if len(records.canonical(args).encode())>1048576: raise ValueError('Work orders are bounded at 1 MiB')
    if len(set(args['copies']))!=len(args['copies']): raise ValueError('Repeated working copy')
    if not time.time()<args['expires']<=time.time()+30*86400: raise ValueError('Work expiry must be within 30 days')
    with kernel.db() as db:
        assignment = records.read(db,'assignment',args['assignment'],principal)
        project=records.read(db,'project',assignment['project'],principal)
    seen=set(); ancestors={}; steps=[]
    for source in args['steps']:
        step = json.loads(records.canonical(source)); key=step['key']; op=step['operation']
        if key in seen or not set(step['after'])<=seen: raise ValueError('Steps must name unique keys and earlier prerequisites')
        deps=set(step['after']); closure=deps|set().union(*(ancestors[k] for k in deps)) if deps else set()
        if not reference_dependencies(step['arguments'])<=closure: raise ValueError('A result reference requires an explicit prerequisite')
        if op not in OPS: raise ValueError('Operation is outside the continuing-work allowlist')
        if op in ('changes.apply',) and not isinstance(step['arguments'].get('id'),dict):
            raise ValueError('An application must reference a proposal made by a prerequisite of this work order')
        if 'copy' in step['arguments'] and step['arguments']['copy'] not in args['copies']:
            raise ValueError('Step copy is outside this order; use a fixed selected copy')
        if 'assignment' in step['arguments'] and step['arguments']['assignment']!=args['assignment']:
            raise ValueError('A report must use this assignment')
        if not reference_dependencies(step['arguments']): validate(step['arguments'],schemas()[op])
        step.setdefault('seconds',120 if op=='workers.draft' else 30)
        step.setdefault('retries',0); step.setdefault('require',[])
        if step['retries'] and op not in ('work.read','work.query','workers.inspect','workers.check'):
            raise ValueError('Automatic retries are limited to read-only steps')
        if op=='work.query': check_query(kernel,step['arguments']['text'],principal,assignment,args['copies'])
        seen.add(key); ancestors[key]=closure; steps.append(step)
    budget={**args['budget'], 'failures':args['budget'].get('failures',2),'quiet':args['budget'].get('quiet',2)}
    if budget['steps']<len(steps): raise ValueError('Step budget is smaller than the frozen plan')
    current=signatures(kernel,args['copies'],principal)
    if len(records.canonical(current).encode())>2097152:raise ValueError('Selected working-copy identities exceed 2 MiB; use a smaller order')
    for ident in args['copies']:
        _, row, _=store.workspace(kernel,ident,principal)
        if not row['for_slate']: raise ValueError('Delegate each selected working copy to Graphite before preparing continuing work')
    plan={'schema':'arc.work-order/1','id':uuid.uuid4().hex,'owner':principal.identity,'created':time.time(),
        'assignment':assignment['id'],'assignment_revision':assignment['revision'],'assignment_digest':records.digest(assignment),
        'project':project['id'],'project_digest':records.digest(project),
        'original_request':assignment['original_request'],'title':args['title'],'steps':steps,'copies':args['copies'],
        'initial_copies':current,'sources':assignment['inputs'],'budget':budget,'expires':args['expires'],
        'operations':sorted({s['operation'] for s in steps}),'effects':sorted({OPS[s['operation']] for s in steps}),
        'network':False,'original_updates':False,'procedure':procedure,'restart':'EXPLICIT_RESUME_AFTER_IN_FLIGHT_INTERRUPTION',
        'operation_schemas':{op:schemas()[op] for op in sorted({s['operation'] for s in steps})},'executor_digest':executor_identity()}
    state={'state':'DRAFT','reason':'PERMISSION_NEEDED','used':{'steps':0,'seconds':0.0,'tokens':0,'output_bytes':0,'files':[]},
        'failures':0,'quiet':0,'last_progress':None,'copies':current,'source_successors':{},'epoch':None,'review':None}
    if adaptive is not None:
        from . import adaptive_work
        with kernel.db() as db: problem=records.read(db,'problem',adaptive['problem']['id'],principal)
        adaptive_work.initialize(plan,state,adaptive,problem)
    from . import agenda
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE'); agenda.ensure(db)
        now=records.read(db,'assignment',assignment['id'],principal)
        if records.digest(now)!=records.digest(assignment): raise ValueError('Assignment changed during work preparation')
        db.execute('INSERT INTO flow_orders VALUES(?,?,?,?,?,?)',
            (plan['id'],principal.identity,records.canonical(plan),records.digest(plan),state['state'],records.canonical(state)))
        # Reuse the Agenda row and its scheduling/dependency semantics; no extra timer/queue.
        ident=uuid.uuid4().hex; clock=time.time()
        db.execute('INSERT INTO agenda_items(id,owner,title,nice,position,state,origin,rounds,rounds_used,quiet,idle,missed,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (ident,principal.identity,args['title'],'normal',agenda.last_position(db,principal.identity),'PAUSED','you',20,0,0,0,0,clock,clock))
        db.execute('INSERT INTO flow_agenda VALUES(?,?)',(ident,plan['id']))
        for step in steps: step_save(db,plan['id'],{'key':step['key'],'state':'PENDING','attempts':0})
        event(db,plan,'PREPARED_NO_AUTHORITY')
    return get(kernel,plan['id'],principal)


def grant(db, plan):
    row=db.execute('SELECT payload,digest,revoked FROM flow_grants WHERE work=? AND owner=?',(plan['id'],plan['owner'])).fetchone()
    if not row: raise ValueError('PERMISSION_NEEDED')
    value=json.loads(row[0])
    if records.digest(value)!=row[1] or value['order_digest']!=records.digest(plan): raise ValueError('WORK_GRANT_DAMAGED')
    if row[2] is not None: raise ValueError('GRANT_REVOKED')
    if time.time()>=value['expires']: raise ValueError('GRANT_EXPIRED')
    return value


def guard(kernel, ident, principal, epoch, db=None):
    def inside(conn):
        plan,state=load(conn,ident,principal); grant(conn,plan)
        gate=work_trail.work_status(kernel,conn)
        if gate['held'] or gate['epoch']!=epoch: raise ValueError('WORK_HELD_OR_EPOCH_CHANGED')
        if state['state']!='RUNNING': raise ValueError('WORK_'+state['state'])
    if db is not None: return inside(db)
    with kernel.db() as conn: return inside(conn)


def foundations(kernel, plan, state, principal, check_copies=True):
    from . import native_sessions
    native_sessions.guard_copies(kernel,plan['copies'],principal)
    if plan['executor_digest']!=executor_identity():raise ValueError('EXECUTOR_CHANGED_PREPARE_A_NEW_REVIEWED_ORDER')
    from .engineering_cli import schemas
    if any(schemas().get(op)!=definition for op,definition in plan['operation_schemas'].items()):raise ValueError('WORK_OPERATION_SCHEMA_CHANGED')
    with kernel.db() as db:
        a=records.read(db,'assignment',plan['assignment'],principal)
        project=records.read(db,'project',plan['project'],principal)
    if records.digest(a)!=plan['assignment_digest']: raise ValueError('ASSIGNMENT_CHANGED')
    if records.digest(project)!=plan['project_digest']:raise ValueError('PROJECT_CHANGED')
    for binding in plan['sources']:
        successor=state.get('source_successors',{}).get(binding.get('address'))
        if successor:
            if schemas().get(binding['operation'])!=binding['operation_schema']:raise ValueError('SOURCE_SCHEMA_CHANGED')
            _,_,root=store.workspace(kernel,successor['copy'],principal)
            actual=store.inspect_file(root,successor['path'])
            if (actual['sha256'] if actual else None)!=successor['sha256']:raise ValueError('SOURCE_CHANGED_AFTER_OWNED_REVISION')
        elif records.freshness(kernel,[binding],principal)['state']!='CURRENT': raise ValueError('SOURCE_CHANGED_OR_UNAVAILABLE')
    if check_copies and signatures(kernel,plan['copies'],principal)!=state['copies']: raise ValueError('WORKING_COPY_CHANGED')
    if plan.get('profile')=='ledger.adaptive-investigation/1':
        from .adaptive_work import check_problem
        check_problem(kernel,plan,state,principal)


def get(kernel, ident, principal):
    with kernel.db() as db:
        plan,state=load(db,ident,principal)
        steps=[step_row(db,ident,key) for key in state.get('steps', [s['key'] for s in plan['steps']])]
        rows=db.execute('SELECT event,payload,at FROM flow_events WHERE work=? ORDER BY seq DESC LIMIT 100',(ident,)).fetchall()
        g=db.execute('SELECT id,revoked FROM flow_grants WHERE work=?',(ident,)).fetchone()
        row=db.execute('SELECT agenda FROM flow_agenda WHERE work=?',(ident,)).fetchone()
    return {'plan':plan,'content_digest':records.digest(plan),'state':state,'steps':steps,'agenda':row[0],
        'grant':{'id':g[0],'revoked':g[1]} if g else None,
        'events':[{'event':r[0],'detail':json.loads(r[1]),'at':r[2]} for r in reversed(rows)],
        'authority':'Only an owner grant authorizes the exact frozen calls; originals and network are excluded.'}


@contextlib.contextmanager
def agenda_lock(kernel):
    path=kernel.state/'agenda-run.lock'
    fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('AGENDA_BUSY') from None
        yield
    finally: os.close(fd)


def resolve(value, results):
    if isinstance(value,dict):
        if '$step' in value:
            result=results[value['$step']]
            for part in value['path']:
                if not isinstance(result,dict) or part not in result: raise ValueError('Referenced step result is unavailable')
                result=result[part]
            return json.loads(records.canonical(result))
        return {k:resolve(v,results) for k,v in value.items()}
    if isinstance(value,list): return [resolve(v,results) for v in value]
    return value


def read_file(kernel,args,principal):
    meta,row,root=store.workspace(kernel,args['copy'],principal)
    change_sets.check_path(meta,args['path'])
    raw,info=store.read_bytes(root,args['path'],65536)
    text=raw.decode('utf-8')
    if '\x00' in text: raise ValueError('Work text reads require UTF-8 without NULs')
    return {'copy':args['copy'],'path':args['path'],'sha256':info['sha256'],'bytes':len(raw),'text':text}


def check_query(kernel,text,principal,assignment=None,copies=None):
    plan=records.result_of(kernel,'language.parse',{'text':text},principal)
    allowed={'work.read','projects.get','assignments.get'}
    call=plan['call']; op=call['operation']; args=call['arguments']
    if op not in allowed: raise ValueError('Continuing queries read selected working text or this assignment/project')
    if copies is not None and op=='work.read' and args.get('copy') not in copies: raise ValueError('Query copy is outside this order')
    if assignment is not None:
        if op=='assignments.get' and args.get('id')!=assignment['id']: raise ValueError('Query assignment is outside this order')
        if op=='projects.get' and args.get('id')!=assignment['project']: raise ValueError('Query project is outside this order')
    for t in plan['transforms']:
        if t['kind'] in ('join','missing'): check_query(kernel,t['source'],principal,assignment,copies)
    return plan


def proposal_cache(kernel, proposal, principal):
    with kernel.db() as db:
        row=db.execute('SELECT 1 FROM edit_records WHERE id=? AND owner=? AND kind=?',(proposal,principal.identity,'proposal')).fetchone()
        return store.get(db,principal.identity,'proposal',proposal) if row else None


def expected_after(plan,state,proposal):
    expected=json.loads(records.canonical(state['copies'])); files=expected[proposal['copy']]['files']
    for c in proposal['changes']:
        if c['after'] is None: files.pop(c['path'],None)
        else: files[c['path']]={'sha256':c['after'],'mode':c['after_mode']}
    return expected


def source_successors(plan,state,proposal,commit):
    result=json.loads(records.canonical(state.get('source_successors',{})))
    prefix='files:'+state['copies'][proposal['copy']]['work']+'/'
    changed={c['path']:c for c in proposal['changes']}
    for binding in plan['sources']:
        address=binding.get('address')
        if address and address.startswith(prefix) and address[len(prefix):] in changed:
            path=address[len(prefix):]
            result[address]={'copy':proposal['copy'],'path':path,'sha256':changed[path]['after'],'commit':commit['id'],
                'predecessor_revision':binding['revision'],'actor_work':plan['id']}
    return result


def assert_result(step,result):
    for assertion in step['require']:
        value=result
        for part in assertion['path']:
            if not isinstance(value,dict) or part not in value:raise ValueError('CHECK_RESULT_PATH_MISSING')
            value=value[part]
        if records.canonical(value)!=records.canonical(assertion['equals']):raise ValueError('SUCCESS_CHECK_FAILED')


def validate_call(kernel,plan,step,args,results,principal):
    from .engineering_cli import schemas
    from .agent_operations import validate
    validate(args,schemas()[step['operation']]); op=step['operation']
    if args.get('copy') is not None and args['copy'] not in plan['copies']: raise ValueError('COPY_OUTSIDE_GRANT')
    if op=='changes.report' and args['assignment']!=plan['assignment']: raise ValueError('ASSIGNMENT_OUTSIDE_GRANT')
    if op=='changes.apply':
        # Only a prior completed proposal produced by this order can be applied.
        ids={v.get('id',v.get('proposal_id')) for v in results.values() if isinstance(v,dict)}
        if args['id'] not in ids: raise ValueError('PROPOSAL_OUTSIDE_GRANT')
        with kernel.db() as db: p=store.get(db,principal.identity,'proposal',args['id'])
        if p['target']!='WORKING' or p['copy'] not in plan['copies'] or p['content_digest']!=args['expected_digest']:
            raise ValueError('PROPOSAL_OUTSIDE_GRANT')
        if p['provenance'].get('work_order')!=plan['id']:raise ValueError('PROPOSAL_OUTSIDE_GRANT')
        return p
    if op=='work.query':
        with kernel.db() as db: a=records.read(db,'assignment',plan['assignment'],principal)
        check_query(kernel,args['text'],principal,a,plan['copies'])
    return None


def progress_identity(result):
    if isinstance(result,dict) and 'changes' in result:
        return records.digest([[c['path'],c['before'],c['after']] for c in result['changes']])
    if isinstance(result,dict) and 'sha256' in result: return result['sha256']
    if isinstance(result,dict) and 'checks' in result: return records.digest(result['checks'])
    return records.digest(result)


def reconcile_apply(kernel,plan,state,step,principal,checkpoint=None):
    if step['operation']!='changes.apply': return False
    with kernel.db() as db:
        item=step_row(db,plan['id'],step['key']); args=item.get('arguments')
        if not args:return False
        p=store.get(db,principal.identity,'proposal',args['id'])
        row=db.execute('SELECT commit_id FROM edit_applications WHERE proposal=?',(p['id'],)).fetchone()
        if not row:return False
        commit=store.get(db,principal.identity,'commit',row[0])
    if commit['state']!='DONE': raise ValueError('PARTIAL_APPLICATION_REQUIRES_CHANGES_RECOVERY')
    assert_result(step,commit)
    expected=expected_after(plan,state,p)
    if signatures(kernel,plan['copies'],principal)!=expected: raise ValueError('WORKING_COPY_CHANGED_AFTER_APPLICATION')
    size=len(records.canonical(commit).encode())
    if state['used']['output_bytes']+size>plan['budget']['output_bytes']:raise ValueError('BUDGET_OUTPUT_BYTES')
    state['source_successors']=source_successors(plan,state,p,commit)
    state['copies']=expected;state['used']['output_bytes']+=size
    item.update(state='DONE',result=commit,result_digest=records.digest(commit),recovered=True,finished=time.time())
    with kernel.db() as db:
        if checkpoint is not None:checkpoint(db)
        step_save(db,plan['id'],item); save(db,plan,state,'COMPLETED_APPLICATION_RECONCILED',{'step':step['key'],'commit':commit['id']})
    return True


def advance(kernel,ident,principal):
    """Called under the Agenda's one cross-process execution lock, one step per turn."""
    with kernel.db() as db: selected,_=load(db,ident,principal)
    if selected.get('profile')=='ledger.adaptive-investigation/1':
        from . import adaptive_work
        return adaptive_work.advance(kernel,ident,principal)
    from .engineering_kernel import Principal
    from . import worker_boundary
    with kernel.db() as db:
        plan,state=load(db,ident,principal)
        if state['state'] not in ('READY','RETRY'): return {'ran':None,'work':ident,'state':state['state'],'reason':state.get('reason')}
        if state.get('retry_at',0)>time.time(): return {'ran':None,'reason':'RETRY_BACKOFF'}
        try:
            grant(db,plan); gate=work_trail.work_status(kernel,db)
            if gate['held'] or gate['epoch']!=state['epoch']: raise ValueError('WORK_HELD_OR_EPOCH_CHANGED')
        except ValueError as exc:
            state.update(state='PAUSED',reason=str(exc));save(db,plan,state,'PAUSED'); return {'ran':ident,'state':state['state'],'reason':state['reason']}
        items={s['key']:step_row(db,ident,s['key']) for s in plan['steps']}
    pending=[s for s in plan['steps'] if items[s['key']]['state']!='DONE']
    if not pending:
        with kernel.db() as db: state.update(state='REVIEW',reason='FINISHED_PROPOSAL');save(db,plan,state,'AWAITING_REVIEW')
        return {'ran':ident,'state':'REVIEW'}
    step=next((s for s in pending if items[s['key']]['state'] in ('PENDING','RETRY') and all(items[k]['state']=='DONE' for k in s['after'])),None)
    if step is None:
        with kernel.db() as db: state.update(state='WAITING',reason='FAILED_OR_INTERRUPTED_PREREQUISITE');save(db,plan,state,'PREREQUISITE_BLOCKED')
        return {'ran':ident,'state':'WAITING','reason':state['reason']}
    results={k:v['result'] for k,v in items.items() if v['state']=='DONE'}
    item=items[step['key']]; op=step['operation']; began=time.monotonic()
    try:
        foundations(kernel,plan,state,principal)
        args=resolve(step['arguments'],results); proposal=validate_call(kernel,plan,step,args,results,principal)
        reserve_tokens=worker_boundary.model_reservation(kernel,args) if op=='workers.draft' else 0
        used=json.loads(records.canonical(state['used'])); budget=plan['budget']
        used['steps']+=1;used['seconds']+=step['seconds'];used['tokens']+=reserve_tokens
        if proposal:
            used['files']=sorted(set(used['files'])|{proposal['copy']+':'+c['path'] for c in proposal['changes']})
        for kind in ('steps','seconds','tokens','output_bytes','files'):
            measured=len(used[kind]) if kind=='files' else used[kind]
            if measured>budget[kind]: raise ValueError('BUDGET_'+kind.upper())
        if op.startswith('workers.'):
            worker_boundary.require_qualified(kernel,op)
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE'); current_plan,current_state=load(db,ident,principal)
            if current_state!=state: raise ValueError('WORK_STATE_CHANGED')
            grant(db,plan)
            gate=work_trail.work_status(kernel,db)
            if gate['held'] or gate['epoch']!=state['epoch']: raise ValueError('WORK_HELD_OR_EPOCH_CHANGED')
            state.update(state='RUNNING',reason=None,used=used)
            item.update(state='RUNNING',attempts=item['attempts']+1,arguments=args,started=time.time(),reserved_seconds=step['seconds'],
                proposal_id=uuid.uuid5(uuid.NAMESPACE_URL,ident+':'+step['key']).hex)
            step_save(db,ident,item);save(db,plan,state,'STEP_INTENT',{'step':step['key'],'operation':op,'attempt':item['attempts']})
        fault('INTENT')
        def check(db=None):
            if time.monotonic()-began>step['seconds']:raise ValueError('STEP_TIME_LIMIT')
            guard(kernel,ident,principal,state['epoch'],db)
        scope={'work':ident,'step':step['key'],'proposal':item['proposal_id'],'guard':check,
            'seconds':step['seconds'],'memory_mb':budget['memory_mb'],'output_bytes':min(1048576,budget['output_bytes']-used['output_bytes'])}
        # Internal principal carries only this registered call's required scope.
        from .engineering_kernel import CAPABILITIES
        bounded=Principal(principal.identity,frozenset({'read',CAPABILITIES[op]}),principal.paths,(),principal.mode)
        with work_scope.entered(scope):
            check()
            cached=proposal_cache(kernel,item['proposal_id'],principal) if op in ('changes.propose','changes.report','workers.draft') else None
            if cached:
                result=cached if op!='workers.draft' else {'proposal_id':cached['id'],'proposal_digest':cached['content_digest'],'recovered':True}
            else: result=records.result_of(kernel,op,args,bounded)
        fault('EFFECT')
        if proposal and result.get('state')!='DONE': raise ValueError('PARTIAL_APPLICATION_REQUIRES_CHANGES_RECOVERY')
        expected=expected_after(plan,state,proposal) if proposal else state['copies']
        if signatures(kernel,plan['copies'],principal)!=expected: raise ValueError('WORKING_COPY_CHANGED_DURING_STEP')
        # Revalidate non-working inputs too; outputs are never presented as current across a changed input.
        successor_state={**state,'source_successors':source_successors(plan,state,proposal,result)} if proposal else state
        foundations(kernel,plan,successor_state,principal,False)
        assert_result(step,result)
        size=len(records.canonical(result).encode())
        if used['output_bytes']+size>budget['output_bytes']: raise ValueError('BUDGET_OUTPUT_BYTES')
        progress=progress_identity(result)
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE'); check(db)
            state['used']['seconds']-=max(0,step['seconds']-min(step['seconds'],time.monotonic()-began))
            state['used']['output_bytes']+=size;state['copies']=expected
            state['source_successors']=successor_state.get('source_successors',{})
            state['quiet']=state['quiet']+1 if state['last_progress']==progress else 0;state['last_progress']=progress
            item.update(state='DONE',result=result,result_digest=records.digest(result),finished=time.time())
            step_save(db,ident,item)
            left=any(s['key']!=step['key'] and items[s['key']]['state']!='DONE' for s in plan['steps'])
            state.update(state='LIMIT' if state['quiet']>=budget['quiet'] else 'READY' if left else 'REVIEW',
                reason='NO_PROGRESS_LIMIT' if state['quiet']>=budget['quiet'] else None if left else 'FINISHED_PROPOSAL')
            save(db,plan,state,'STEP_DONE',{'step':step['key'],'result_digest':item['result_digest']})
        return {'ran':ident,'step':step['key'],'state':state['state']}
    except (ValueError,OSError,KeyError,TypeError,sqlite3.Error) as exc:
        reason=str(exc)[:400]
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE'); _,live=load(db,ident,principal);item=step_row(db,ident,step['key'])
            if live['state'] not in ('RUNNING','READY','RETRY'): return {'ran':ident,'state':live['state'],'reason':live.get('reason')}
            if item['state']=='RUNNING':
                live['failures']+=1;item.update(state='FAILED',reason=reason)
                # Reserved resources remain charged on failure/unknown outcome.
                retry=op in ('work.read','work.query','workers.inspect','workers.check') and item['attempts']<=step['retries'] and live['failures']<plan['budget']['failures']
                if retry:
                    item['state']='RETRY'; live['retry_at']=time.time()+min(60,5*2**item['attempts'])
                step_save(db,ident,item)
            else: retry=False
            limited=reason.startswith('BUDGET_') or live['failures']>=plan['budget']['failures']
            live.update(state='LIMIT' if limited else 'RETRY' if retry else 'WAITING',reason=reason)
            save(db,plan,live,'STEP_STOPPED',{'step':step['key'],'reason':reason})
        return {'ran':ident,'step':step['key'],'state':live['state'],'reason':reason}


def resume(kernel,ident,principal):
    with kernel.db() as db: selected,_=load(db,ident,principal)
    if selected.get('profile')=='ledger.adaptive-investigation/1':
        from . import adaptive_work
        return adaptive_work.resume(kernel,ident,principal)
    work_trail.accepting(kernel)
    with agenda_lock(kernel):
        with kernel.db() as db: plan,state=load(db,ident,principal);grant(db,plan)
        if state['state'] in FINAL or state['state']=='DRAFT': raise ValueError('This work order cannot resume in its current state')
        with kernel.db() as db: items={s['key']:step_row(db,ident,s['key']) for s in plan['steps']}
        for step in plan['steps']:
            item=items[step['key']]
            if item['state'] in ('RUNNING','FAILED'):
                if reconcile_apply(kernel,plan,state,step,principal): continue
                if step['operation']=='changes.apply':
                    with kernel.db() as db:
                        app=db.execute('SELECT 1 FROM edit_applications WHERE proposal=?',(item.get('arguments',{}).get('id'),)).fetchone()
                    if app: raise ValueError('Inspect/recover the matching batch in Changes before resuming this order')
                if item['state']=='FAILED': raise ValueError('A failed step needs a new reviewed order; automatic retries are fixed in its plan')
                # Read-only/retained-proposal work may repeat only after this explicit resumption, charged as another attempt.
                item['state']='PENDING'
                with kernel.db() as db:step_save(db,ident,item)
        foundations(kernel,plan,state,principal)
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE'); _,live=load(db,ident,principal);grant(db,plan)
            if live['state']=='REVOKED': raise ValueError('GRANT_REVOKED')
            state.update(state='READY',reason=None,epoch=work_trail.work_status(kernel,db)['epoch'])
            save(db,plan,state,'EXPLICIT_RESUME')
    return get(kernel,ident,principal)


def linked(db,agenda_id):
    row=db.execute('SELECT work FROM flow_agenda WHERE agenda=?',(agenda_id,)).fetchone()
    return row[0] if row else None


def agenda_rows(kernel,principal):
    with kernel.db() as db:
        rows=[]
        for ident,state,payload in db.execute('SELECT id,state,payload FROM flow_orders WHERE owner=?',(principal.identity,)):
            s=json.loads(payload)
            if state in ('WAITING','PAUSED','DRAFT','LIMIT','REVIEW'):
                rows.append({'kind':'work','id':ident,'title':load(db,ident,principal)[0]['title'],'state':state,
                    'reason':s.get('reason') or state,'address':'work:'+ident})
        return rows


def pump(kernel):
    """The headless host calls the same Agenda runner, for authorized work rows only."""
    from . import agenda
    from .engineering_kernel import Principal
    if work_trail.execution_held(kernel): return
    with kernel.db() as db:
        owners=[r[0] for r in db.execute("SELECT DISTINCT owner FROM flow_orders WHERE state IN ('READY','RETRY','RUNNING') ORDER BY rowid")]
    for owner in owners:
        p=Principal(owner,frozenset({'read','execute'}),(),())
        with agenda_lock(kernel):
            result=agenda.run_next(kernel,{},p,work_only=True)
        if result.get('ran') is not None:return result


def procedure(db,ident,principal):
    row=db.execute('SELECT payload,digest FROM flow_procedures WHERE id=? AND owner=?',(ident,principal.identity)).fetchone()
    if not row:raise ValueError('Procedure unavailable to this caller')
    value=json.loads(row[0])
    if records.digest(value)!=row[1]:raise ValueError('PROCEDURE_DAMAGED')
    return value


def parameter_parent(arguments,path):
    node=arguments
    for part in path[:-1]:
        if isinstance(node,list):
            if not part.isdecimal() or int(part)>=len(node):raise ValueError('Parameter array position unavailable')
            node=node[int(part)]
        elif isinstance(node,dict) and part in node:node=node[part]
        else:raise ValueError('Parameter argument path unavailable')
    part=path[-1]
    if isinstance(node,list):
        if not part.isdecimal() or int(part)>=len(node):raise ValueError('Parameter array position unavailable')
        return node,int(part)
    if not isinstance(node,dict) or part not in node:raise ValueError('Parameter argument path unavailable')
    return node,part


def procedure_save(kernel,args,principal):
    with kernel.db() as db:
        plan,state=load(db,args['work'],principal)
        if state['state']!='ACCEPTED':raise ValueError('Only an owner-accepted completed order becomes a reusable procedure')
    parameters=args['parameters']
    # A parameter replaces an exact literal at a named JSON path. Operation/dependency/grant fields are never parameterized.
    if len(parameters)>16:raise ValueError('At most sixteen procedure parameters')
    steps=json.loads(records.canonical(plan['steps'])); used=set()
    for name,spec in parameters.items():
        if not name.isidentifier() or not isinstance(spec,dict) or set(spec)!={'step','path','type'} or spec['type'] not in ('string','integer','number','boolean'):
            raise ValueError('Parameter requires a name, step, argument path and scalar type')
        if not isinstance(spec['path'],list) or not 1<=len(spec['path'])<=12 or any(not isinstance(p,str) for p in spec['path']):raise ValueError('Invalid parameter path')
        step=next((s for s in steps if s['key']==spec['step']),None)
        if step is None:raise ValueError('Unknown parameter step')
        node,index=parameter_parent(step['arguments'],spec['path'])
        target=(spec['step'],tuple(spec['path']))
        if target in used or isinstance(node[index],(dict,list)):raise ValueError('Parameter must replace one distinct scalar argument')
        used.add(target)
    value={'schema':'arc.stac-procedure/1','id':uuid.uuid4().hex,'owner':principal.identity,'title':args['title'],
        'source_work':plan['id'],'source_order_digest':records.digest(plan),'steps':steps,'parameters':parameters,
        'operations':plan['operations'],'effects':plan['effects'],'copy_slots':plan['copies'],'assignment':plan['assignment'],'created':time.time(),
        'authority':'TEMPLATE_ONLY_NEW_INSTANCE_REQUIRES_NEW_GRANT'}
    with kernel.db() as db:db.execute('INSERT INTO flow_procedures VALUES(?,?,?,?)',(value['id'],principal.identity,records.canonical(value),records.digest(value)))
    return value


def dispatch(kernel,op,args,principal):
    if op=='work.read':return read_file(kernel,args,principal)
    if op=='work.query':
        check_query(kernel,args['text'],principal)
        return records.result_of(kernel,'language.run',args,principal)
    if op=='work.create':return create(kernel,args,principal)
    if op=='work.get':return get(kernel,args['id'],principal)
    if op in ('work.list','procedures.list'):
        table='flow_orders' if op=='work.list' else 'flow_procedures'
        with kernel.db() as db:
            ids=[r[0] for r in db.execute('SELECT id FROM '+table+' WHERE owner=? ORDER BY rowid DESC LIMIT ? OFFSET ?',
                (principal.identity,args.get('limit',100),args.get('offset',0)))]
            if op=='procedures.list':return {'records':[procedure(db,i,principal) for i in ids]}
            return {'records':[{'id':i,'title':load(db,i,principal)[0]['title'],**load(db,i,principal)[1]} for i in ids]}
    if op=='procedures.get':
        with kernel.db() as db:return procedure(db,args['id'],principal)
    if op=='procedures.save':return procedure_save(kernel,args,principal)
    if op=='procedures.instantiate':
        with kernel.db() as db:value=procedure(db,args['id'],principal)
        if value.get('checked_method'):raise ValueError('Use methods.instantiate to recheck this checked method version and its preconditions; templates grant no authority')
        if set(args['values'])!=set(value['parameters']):raise ValueError('Supply exactly the declared parameters')
        steps=json.loads(records.canonical(value['steps']))
        for name,spec in value['parameters'].items():
            v=args['values'][name];kind=spec['type']
            if not ((kind=='string' and isinstance(v,str) and len(v)<=65536) or (kind=='integer' and type(v)==int) or
                    (kind=='number' and type(v) in (int,float)) or (kind=='boolean' and type(v)==bool)):raise ValueError('Procedure parameter type mismatch')
            arguments=next(s for s in steps if s['key']==spec['step'])['arguments']
            node,index=parameter_parent(arguments,spec['path']);node[index]=v
        if len(args['copies'])!=len(value['copy_slots']):raise ValueError('Supply one working copy per saved procedure slot')
        copy_map=dict(zip(value['copy_slots'],args['copies']))
        for step in steps:
            arguments=step['arguments']
            if 'copy' in arguments:arguments['copy']=copy_map.get(arguments['copy'],arguments['copy'])
            if arguments.get('assignment')==value['assignment']:arguments['assignment']=args['assignment']
        # Copy and assignment bindings remain explicit arguments and are validated like any new order.
        return create(kernel,{k:v for k,v in args.items() if k not in ('id','values')}|{'steps':steps},principal,value['id'])
    if op=='work.advance':
        from . import agenda
        with agenda_lock(kernel):return agenda.run_next(kernel,{},principal,selected_work=args['id'])
    if op=='work.resume':return resume(kernel,args['id'],principal)
    if op=='work.authorize':
        work_trail.accepting(kernel)
        with kernel.db() as db:plan,state=load(db,args['id'],principal)
        if args['expected_digest']!=records.digest(plan) or state['state']!='DRAFT':raise ValueError('Review this exact ungranted order before authorizing')
        if time.time()>=plan['expires']:raise ValueError('GRANT_EXPIRED_PREPARE_A_NEW_ORDER')
        foundations(kernel,plan,state,principal)
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE'); _,live=load(db,args['id'],principal)
            if live['state']!='DRAFT':raise ValueError('Work state changed')
            gate=work_trail.work_status(kernel,db)
            if gate['held']:raise ValueError('WORK_HELD_USE_EXPLICIT_RESUME')
            g={'schema':'arc.work-grant/1','id':uuid.uuid4().hex,'owner':principal.identity,'order_digest':records.digest(plan),
                'work':plan['id'],'operations':plan['operations'],'effects':plan['effects'],'copies':plan['copies'],
                'budget':plan['budget'],'expires':plan['expires'],'network':False,'original_updates':False,'created':time.time()}
            db.execute('INSERT INTO flow_grants VALUES(?,?,?,?,?,NULL)',(g['id'],plan['id'],principal.identity,records.canonical(g),records.digest(g)))
            state.update(state='READY',reason=None,epoch=gate['epoch']);save(db,plan,state,'OWNER_AUTHORIZED',{'grant':g['id']})
        return get(kernel,plan['id'],principal)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');plan,state=load(db,args['id'],principal)
        if op=='work.pause':
            if state['state'] in FINAL or state['state']=='DRAFT':raise ValueError('Only an unfinished authorized order can be paused')
            state.update(state='PAUSED',reason='OWNER_PAUSED');save(db,plan,state,'OWNER_PAUSED')
        elif op=='work.revoke':
            db.execute('UPDATE flow_grants SET revoked=? WHERE work=?',(time.time(),plan['id']))
            state.update(state='REVOKED',reason=args['reason']);save(db,plan,state,'OWNER_REVOKED')
        elif op=='work.review':
            if state['state'] not in ('REVIEW','ACCEPTED','CHANGES_REQUESTED'):raise ValueError('Finish the order before reviewing its result')
            state['review']={'decision':args['decision'],'note':args['note'],'actor':principal.identity,'at':time.time()}
            state.update(state={'ACCEPT':'ACCEPTED','CHANGES_REQUESTED':'CHANGES_REQUESTED','DEFER':'REVIEW'}[args['decision']],reason='OWNER_REVIEW')
            save(db,plan,state,'OWNER_REVIEW',state['review'])
        else:raise ValueError('Unknown continuing-work operation')
    if plan.get('profile')=='ledger.adaptive-investigation/1' and op in ('work.pause','work.revoke'):
        from .adaptive_work import stop_pending
        stop_pending(kernel,plan,state,principal)
    return get(kernel,args['id'],principal)
