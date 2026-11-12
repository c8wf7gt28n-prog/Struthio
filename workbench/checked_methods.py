"""Checked procedure descriptors; templates never carry execution permission."""
import json, time
from . import project_desk as records, problem_service as problems, math_service, schedule_math

PROFILE = 'ledger.additive-capacity-method/1'
DECLARATIONS = {'type': 'object', 'additionalProperties': False, 'properties': {
    'additive': {'type': 'boolean'}, 'constant_capacity': {'type': 'boolean'},
    'interval_semantics': {'type': 'string', 'enum': ['HALF_OPEN', 'CLOSED', 'UNKNOWN']},
    'overhead': {'type': 'string', 'enum': ['NONE', 'PRESENT', 'UNKNOWN']},
    'fragmentation': {'type': 'string', 'enum': ['NOT_APPLICABLE', 'REQUIRED', 'UNKNOWN']},
    'indivisibility': {'type': 'string', 'enum': ['NOT_APPLICABLE', 'REQUIRED', 'UNKNOWN']},
    'basis': records.TEXT}, 'required': ['additive', 'constant_capacity', 'interval_semantics',
        'overhead', 'fragmentation', 'indivisibility', 'basis']}
EXPECTED = {'additive': True, 'constant_capacity': True, 'interval_semantics': 'HALF_OPEN',
            'overhead': 'NONE', 'fragmentation': 'NOT_APPLICABLE', 'indivisibility': 'NOT_APPLICABLE'}
MAPPING = {'method': records.ID, 'method_revision': records.REV, **problems.BOUND,
           'capacity': schedule_math.NAME,
           'allocations': {'type': 'array', 'minItems': 1, 'maxItems': 32, 'items': schedule_math.PAIR},
           'declarations': DECLARATIONS}
OPTIONS = math_service.OPTIONS['properties']
FIELDS = {
    'methods.propose': ({'job': records.ID, 'title': records.TITLE}, ['job', 'title']),
    'methods.get': ({'id': records.ID}, ['id']), 'methods.list': ({}, []),
    'methods.accept': ({'id': records.ID, 'expected_revision': records.REV, 'note': records.TEXT},
                       ['id', 'expected_revision', 'note']),
    'methods.revise': ({'id': records.ID, 'expected_revision': records.REV, 'title': records.TITLE, 'note': records.TEXT},
                       ['id', 'expected_revision', 'title', 'note']),
    'methods.preview': (MAPPING, list(MAPPING)),
    'methods.instantiate': (MAPPING, list(MAPPING)),
    'methods.run': (OPTIONS, list(OPTIONS)),
    'methods.result': ({'job': records.ID}, ['job']),
}
SCOPES = {op: 'approve' if op in ('methods.accept', 'methods.revise') else 'read'
          if op in ('methods.get', 'methods.list', 'methods.preview', 'methods.result') else 'execute' for op in FIELDS}


def read(kernel, kind, ident, p):
    with kernel.db() as db:
        return records.read(db, kind, ident, p)


def reference(value):
    return {'id': value['id'], 'revision': value['revision'], 'digest': records.digest(value)}


def require_accepted(kernel, ref, p):
    from . import joined_work
    value = read(kernel, 'checked_method', ref['id'], p)
    if reference(value) != ref or value['state'] != 'ACCEPTED':
        raise ValueError('METHOD_VERSION_OR_ACCEPTANCE_CHANGED')
    if value['profile'] != PROFILE or value['components'] != joined_work.components():
        raise ValueError('METHOD_IMPLEMENTATION_REQUIRES_REQUALIFICATION')
    evidence = joined_work.result(kernel, value['source_job'], p)
    if evidence['state'] != 'AVAILABLE':
        raise ValueError('METHOD_QUALIFYING_EVIDENCE_STALE')
    return value


def sync_procedure(db, value):
    """Use flow_procedures as the existing template catalogue, with Desk history."""
    template = {'schema': 'arc.stac-procedure/1', 'id': value['id'], 'owner': value['owner'],
        'title': value['title'], 'created': value['created'], 'steps': value['steps'],
        'parameters': {}, 'operations': ['math.schedule'], 'effects': ['calculate'],
        'copy_slots': [value['copy']], 'assignment': value['assignment'],
        'source_work': None, 'source_job': value['source_job'],
        'source_order_digest': value['evidence_digest'], 'checked_method': reference(value),
        'authority': 'TEMPLATE_ONLY_INSTANTIATION_RECHECKS_PRECONDITIONS_NO_GRANT'}
    db.execute('INSERT INTO flow_procedures VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,digest=excluded.digest',
               (value['id'], value['owner'], records.canonical(template), records.digest(template)))


def propose(kernel, args, p):
    from . import joined_work
    evidence = joined_work.result(kernel, args['job'], p)
    if evidence['state'] != 'AVAILABLE':
        raise ValueError('METHOD_NEEDS_CURRENT_CHECKED_APPLICATION_CHAIN')
    action = read(kernel, 'joined_action', evidence['receipt']['action'], p)
    problem, receipt = joined_work.check_action(kernel, action, p)
    value = records.new('checked_method', p, schema='ledger.checked-method/1', profile=PROFILE,
        project=problem.get('project'), title=args['title'], state='PROPOSED', source_job=args['job'],
        evidence_digest=records.digest(evidence['receipt']), copy=action['copy'], assignment=problem['assignment'],
        components=joined_work.components(), accepted_by=None,
        typed_inputs={'capacity': 'nonnegative scalar quantity', 'allocations': 'same quantity dimension as capacity',
                      'lifetimes': 'known nonnegative rational time intervals', 'units': 'exact compatible conversions'},
        preconditions=EXPECTED, expected_checks=['Exact half-open peak', 'Actual Calc recalculation and reopen',
            'Protected Python agreement', 'Native Writer content and dependency bindings'],
        failure_cases=['Unknown or incompatible units', 'Closed lifetimes', 'Variable capacity',
            'Nonadditive resources', 'Unmodeled overhead, fragmentation or indivisibility', 'Changed inputs or method'],
        steps=[{'key': 'Capacity', 'operation': 'math.schedule', 'arguments': receipt['arguments'], 'after': []}],
        qualification='DECLARED_ADDITIVE_MODEL_ONLY_NOT_A_PHYSICAL_GUARANTEE', notes=[])
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE'); records.write(db, value, p, 'CHECKED_METHOD_PROPOSED_NO_AUTHORITY')
        sync_procedure(db, value)
    return value


def mapping(kernel, args, p):
    from . import adaptive_contract
    method = read(kernel, 'checked_method', args['method'], p)
    if method['revision'] != args['method_revision']:
        raise ValueError('METHOD_REVISION_CHANGED')
    require_accepted(kernel, reference(method), p)
    adaptive_contract.validate_schema(args['declarations'], DECLARATIONS)
    if any(args['declarations'][key] != value for key, value in EXPECTED.items()):
        raise ValueError('METHOD_PRECONDITION_UNSUPPORTED: declare the admitted additive, constant-capacity, half-open profile explicitly')
    problem = math_service.current(kernel, args['id'], p); problems.check_bound(problem, args)
    snapshot = schedule_math.evaluate(problem, args['capacity'], args['allocations'])
    if snapshot['state'] not in ('FEASIBLE', 'INFEASIBLE'):
        raise ValueError('METHOD_MAPPING_NEEDS_KNOWN_LIFETIMES')
    return method, problem, snapshot


def instantiate(kernel, args, p):
    from . import joined_work
    method, problem, snapshot = mapping(kernel, args, p)
    value = records.new('method_action', p, schema='arc.tool-action/1', profile=PROFILE,
        project=problem.get('project'), problem=problem['id'], problem_revision=problem['revision'],
        context_digest=problem['context_digest'], method=reference(method), declarations=args['declarations'],
        capacity=args['capacity'], allocations=args['allocations'], components=joined_work.components(),
        copy=problem['sources'][0]['copy'] if problem['sources'] else method['copy'],
        effects=['read', 'calculate'], state='PREPARED_NO_EXECUTION_PERMISSION')
    value['binding_digest'] = records.digest(value)
    with kernel.db() as db:
        return records.write(db, value, p, 'METHOD_MAPPING_PREPARED_NO_GRANT')


def authorize(kernel, options, p):
    from . import joined_work, native_sessions
    action = read(kernel, 'method_action', options['action'], p)
    if action['binding_digest'] != options['expected_digest'] or action['components'] != joined_work.components():
        raise ValueError('METHOD_ACTION_OR_IMPLEMENTATION_CHANGED')
    problem = math_service.current(kernel, action['problem'], p)
    args = {'id': problem['id'], 'expected_revision': action['problem_revision'],
        'expected_context_digest': action['context_digest'], 'method': action['method']['id'],
        'method_revision': action['method']['revision'], 'declarations': action['declarations'],
        'capacity': action['capacity'], 'allocations': action['allocations']}
    mapping(kernel, args, p)
    from .lab_service import delegated
    delegated(kernel, action['copy'], p); native_sessions.guard_copies(kernel, [action['copy']], p)
    return action


def work(kernel, job, p):
    options = job['request_spec']['calculation']; action = authorize(kernel, options, p)
    receipt = records.result_of(kernel, 'math.schedule', {'id': action['problem'],
        'expected_revision': action['problem_revision'], 'expected_context_digest': action['context_digest'],
        'capacity': action['capacity'], 'allocations': action['allocations']}, p)
    authorize(kernel, options, p)
    from . import work_trail
    if kernel.record('jobs', job['id']).get('cancel') or work_trail.execution_held(kernel):
        raise ValueError('METHOD_CANCELLED_BEFORE_COMMIT')
    value = records.new('method_result', p, id=job['id'], schema='ledger.method-result/1',
        action=action['id'], method=action['method'], problem=action['problem'],
        problem_revision=action['problem_revision'], context_digest=action['context_digest'],
        receipt=receipt['id'], declarations=action['declarations'], snapshot=receipt['snapshot'],
        files=[], physical_qualification=False)
    with kernel.db() as db:
        records.write(db, value, p, 'CHECKED_METHOD_APPLIED_TO_NEW_BOUND_INPUTS')
    print(json.dumps({'outcome': 'PASS', 'verdict': receipt['snapshot']['state']}))


def result(kernel, ident, p):
    from . import record_access
    job = record_access.read(kernel, 'jobs', ident, p)
    if job['tool'] != 'math.method':
        raise ValueError('Not a checked-method job')
    if job['state'] != 'Completed':
        return {'job': ident, 'state': job['state'], 'error': job.get('error'), 'files': []}
    value = read(kernel, 'method_result', ident, p)
    try:
        authorize(kernel, job['request_spec']['calculation'], p); state, reason = 'AVAILABLE', None
    except (ValueError, OSError) as exc:
        state, reason = 'STALE', str(exc)
    return {'job': ident, 'state': state, 'reason': reason, 'receipt': value, 'snapshot': value['snapshot'], 'files': []}


def dispatch(kernel, op, args, p):
    if op == 'methods.propose': return propose(kernel, args, p)
    if op == 'methods.get':
        value=read(kernel,'checked_method',args['id'],p)
        with kernel.db() as db:
            history=[]
            for raw,sha in db.execute('SELECT payload,digest FROM desk_history WHERE id=? ORDER BY revision LIMIT 64',(value['id'],)):
                row=json.loads(raw)
                if records.digest(row)!=sha or row['owner']!=p.identity:raise ValueError('METHOD_HISTORY_DAMAGED')
                history.append(row)
        return {**value,'history':history}
    if op == 'methods.list':
        with kernel.db() as db:
            return {'methods': [records.read(db, 'checked_method', row[0], p) for row in db.execute(
                "SELECT id FROM desk_records WHERE owner=? AND kind='checked_method' ORDER BY rowid DESC LIMIT 100", (p.identity,))]}
    if op in ('methods.accept', 'methods.revise'):
        value = read(kernel, 'checked_method', args['id'], p)
        if op == 'methods.accept':
            from . import joined_work
            if joined_work.result(kernel, value['source_job'], p)['state'] != 'AVAILABLE':
                raise ValueError('METHOD_QUALIFYING_EVIDENCE_STALE')
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE'); value = records.read(db, 'checked_method', args['id'], p)
            records.edit(value, args['expected_revision'])
            value['state'] = 'ACCEPTED' if op == 'methods.accept' else 'PROPOSED'
            value['accepted_by'] = p.identity if op == 'methods.accept' else None
            if 'title' in args: value['title'] = args['title']
            value['notes'].append({'text': args['note'], 'actor': p.identity, 'at': time.time()})
            records.write(db, value, p, 'METHOD_' + value['state'], expected=args['expected_revision'])
            sync_procedure(db, value)
        return value
    if op == 'methods.preview':
        preview={'schema':'ledger.method-preview/1','kind':'method_preview','problem':args['id'],
            'problem_revision':args['expected_revision'],'context_digest':args['expected_context_digest'],'binding_current':False,
            'method_id':args['method'],'method_revision':args['method_revision'],'declarations':args['declarations'],
            'capacity':args['capacity'],'allocations':args['allocations'],'execution_started':False,
            'authority':'PREVIEW_NO_EXECUTION_PERMISSION'}
        try:
            problem=math_service.current(kernel,args['id'],p);problems.check_bound(problem,args);preview['binding_current']=True
            method, problem, snapshot = mapping(kernel, args, p)
            return {**preview,'state':'SUPPORTED','method':reference(method),'snapshot':snapshot,'precondition_rejected':False}
        except ValueError as exc:
            return {**preview,'state':'UNSUPPORTED','reason':str(exc),'precondition_rejected':preview['binding_current'] and str(exc).startswith('METHOD_PRECONDITION_UNSUPPORTED:')}
    if op == 'methods.instantiate': return instantiate(kernel, args, p)
    if op == 'methods.run':
        authorize(kernel, args, p)
        return records.result_of(kernel, 'jobs.submit', {'tool': 'math.method', 'calculation': args,
            'request_key': 'math-office:' + args['action'], 'timeout': 30}, p)
    if op == 'methods.result': return result(kernel, args['job'], p)
    raise ValueError('Unknown checked-method operation')
