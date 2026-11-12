"""Private versioned inquiries over Desk history, Atlases and checked readers.

No mutation/execution plan is compiled from an inquiry, and no free-text claim
is promoted to a checked fact. Only fixed mathematical predicate adapters exist.
"""
import copy
import json
import shlex
from . import project_desk as desk, discovery_ir as ir, algorithm_atlas, math_model, math_service, problem_service

EDIT = {'id': desk.ID, 'expected_revision': desk.REV}
PREDICATE = {'type': 'object', 'additionalProperties': False, 'properties': {
    'kind': {'type': 'string', 'enum': ['BOOLEAN_OUTPUT', 'CAPACITY_FITS']},
    'expected': {'type': 'boolean'}, 'output': {'type': 'integer', 'minimum': 0, 'maximum': 15}},
    'required': ['kind', 'expected']}
FIELDS = {
    'discovery.schema': ({}, []), 'discovery.validate': ({'document': ir.IR}, ['document']),
    'discovery.create': ({'document': ir.IR, 'project': desk.ID}, ['document']),
    'discovery.revise': ({**EDIT, 'document': ir.IR}, [*EDIT, 'document']),
    'discovery.list': ({**desk.PAGE, 'project': desk.ID}, []),
    'discovery.get': ({'id': desk.ID, 'revision': desk.REV}, ['id']),
    'discovery.history': ({'id': desk.ID, **desk.PAGE}, ['id']),
    'discovery.observe': ({**EDIT, 'target': ir.KEY, 'method': ir.KEY,
        'reader': {'type': 'string', 'enum': ['MATH', 'SCHEDULE']}, 'receipt': desk.ID,
        'predicate': PREDICATE, 'note': ir.TEXT}, [*EDIT, 'target', 'method', 'reader', 'receipt', 'predicate', 'note']),
}
SCOPES = {op: 'execute' if op in ('discovery.create', 'discovery.revise', 'discovery.observe') else 'read' for op in FIELDS}
NOTICE = 'Inquiry proposals and checked predicates are separate. No job, grant, solver call or acceptance promotion is issued by Discovery.'


def protocol(kernel):
    from .capability_catalog import source
    paths = ('workbench/discovery_ir.py', 'workbench/discovery_service.py', 'workbench/project_desk.py',
             'workbench/math_service.py', 'workbench/schedule_math.py')
    sources = {name: source(kernel.root, name) for name in paths}
    if any(v['state'] != 'PRESENT' for v in sources.values()): raise ValueError('DISCOVERY_PROTOCOL_SOURCE_UNAVAILABLE')
    return {'schema': ir.SCHEMA, 'schema_digest': desk.digest(ir.IR), 'direct_sources': sources}


def read(kernel, ident, principal, revision=None):
    with kernel.db() as db:
        latest = desk.read(db, 'discovery_inquiry', ident, principal)
        if revision is None or revision == latest['revision']: return latest, latest['revision']
        row = db.execute('SELECT payload,digest FROM desk_history WHERE id=? AND revision=?', (ident, revision)).fetchone()
    if row is None: raise ValueError('DISCOVERY_REVISION_UNAVAILABLE')
    value = json.loads(row[0])
    if desk.digest(value) != row[1] or value['owner'] != principal.identity or value['kind'] != 'discovery_inquiry':
        raise ValueError('DISCOVERY_HISTORY_DAMAGED')
    return value, latest['revision']


def method(kernel, algorithm, context, principal):
    result = desk.result_of(kernel, 'algo.find_applicable', {'algorithm': algorithm, 'context': context}, principal)
    candidate = copy.deepcopy(result['candidates'][0]); candidate.pop('applicability')
    for operation in candidate['implementation']['operations']: operation.pop('scope_eligible', None)
    return {'algorithm': algorithm, 'catalog_digest': result['catalog_digest'],
            'definition_digest': desk.digest(candidate), 'definition': candidate,
            'admission': result['candidates'][0]['applicability']}


def capture(kernel, document, principal):
    nodes, order = ir.validate(document); sources = {}; methods = {}
    for key in order:
        node = nodes[key]; body = node['body']
        if node['kind'] == 'sources': sources[key] = desk.snapshots(kernel, [body['address']], principal)[0]
        if node['kind'] == 'candidate_methods':
            context = nodes[body['constraint']]['body']['context']
            methods[key] = method(kernel, body['algorithm'], context, principal)
    if len(desk.canonical({'sources': sources, 'methods': methods}).encode()) > 1024 * 1024:
        raise ValueError('DISCOVERY_BINDING_SIZE_BOUND')
    version = protocol(kernel)
    return {'sources': sources, 'methods': methods, 'protocol': version,
            'node_digests': ir.digests(nodes, order, sources, methods, version)}


def current_nodes(kernel, value, principal):
    nodes, order = ir.validate(value['document']); status = {}; roots = {}
    for key in order:
        node = nodes[key]; body = node['body']; kind = node['kind']
        item = {'key': key, 'kind': kind, 'depends_on': node['depends_on'], 'status': 'PROPOSED', 'causes': [], 'reasons': []}
        if key == 'goal':
            try:
                if protocol(kernel) != value['bindings']['protocol']:
                    item.update(status='STALE', causes=[key], reasons=['Inquiry schema or direct validation/receipt-reader code changed.'])
            except (ValueError, OSError) as exc: item.update(status='STALE', causes=[key], reasons=[str(exc)])
        elif kind == 'sources':
            checked = desk.freshness(kernel, [value['bindings']['sources'][key]], principal)['sources'][0]
            item['source'] = checked; item['status'] = 'CURRENT' if checked['state'] == 'CURRENT' else 'STALE'
            if item['status'] == 'STALE': item['causes'] = [key]; item['reasons'] = ['Source binding changed or is unavailable.']
        elif kind == 'assumptions':
            item['status'] = 'UNKNOWN_ASSUMPTION' if body['certainty'] == 'UNKNOWN' else 'DECLARED_NOT_PROVEN'
        elif kind == 'constraints' and body['context'].get('problem'):
            try:
                binding = body['context']['problem']; problem = math_service.current(kernel, binding['id'], principal)
                problem_service.check_bound(problem, binding); item['status'] = 'BOUND_TO_CURRENT_PROBLEM'
            except (ValueError, OSError) as exc:
                item.update(status='STALE', causes=[key], reasons=[str(exc)])
        elif kind == 'candidate_methods':
            try:
                current = method(kernel, body['algorithm'], nodes[body['constraint']]['body']['context'], principal)
                if current['definition_digest'] != value['bindings']['methods'][key]['definition_digest']:
                    item.update(status='STALE', causes=[key], reasons=['Atlas definition, implementation or runtime binding changed.'])
                else:
                    state = current['admission']['state']; item['admission'] = current['admission']
                    item['status'] = 'DECLARED_PROFILE_MATCH' if state.startswith('MATCH_') else state
            except (ValueError, OSError) as exc:
                item.update(status='STALE', causes=[key], reasons=[str(exc)])
        elif kind in ('claims', 'hypotheses'): item['status'] = 'HYPOTHESIS'
        if item['status'] == 'STALE': roots[key] = item['reasons']
        changed = sorted({cause for parent in node['depends_on'] for cause in status[parent]['causes']})
        if changed:
            item['status'] = 'STALE'; item['causes'] = sorted(set(item['causes']) | set(changed))
            item['reasons'].append('Declared upstream dependency changed: ' + ', '.join(changed))
        status[key] = item
    return nodes, order, status, roots


def checked_reader(kernel, reader, ident, principal):
    operation = 'math.get' if reader == 'MATH' else 'math.schedule.get'
    binding = desk.call_binding(kernel, operation, {'id': ident}, principal)
    if binding['snapshot'].get('applicability') != 'CURRENT': raise ValueError('DISCOVERY_RECEIPT_STALE')
    if not binding['snapshot'].get('receipt'): raise ValueError('DISCOVERY_RECEIPT_NOT_EXECUTED')
    return binding


def check_predicate(binding, reader, predicate):
    value = binding['snapshot']; actual = None; snapshot = value.get('receipt', {}).get('snapshot') if value.get('receipt') else None
    if predicate['kind'] == 'BOOLEAN_OUTPUT':
        if reader != 'MATH' or set(predicate) != {'kind', 'expected', 'output'}: raise ValueError('DISCOVERY_BOOLEAN_PREDICATE_FIELDS')
        if snapshot and snapshot.get('state') in ('FEASIBLE', 'INFEASIBLE'):
            evaluation = snapshot.get('evaluation') or snapshot; outputs = evaluation.get('outputs', [])
            if predicate['output'] < len(outputs):
                output = outputs[predicate['output']]
                if output.get('state') == 'EXACT' and type(output.get('value')) is bool: actual = output['value']
    else:
        if reader != 'SCHEDULE' or set(predicate) != {'kind', 'expected'}: raise ValueError('DISCOVERY_CAPACITY_PREDICATE_FIELDS')
        if snapshot and snapshot.get('state') in ('FEASIBLE', 'INFEASIBLE') and snapshot.get('observed') is True and type(snapshot.get('fits')) is bool:
            actual = snapshot['fits']
    return {'grade': 'CHECKED_NUMERIC' if actual is not None else 'OBSERVED_ONLY',
            'state': 'UNRESOLVED' if actual is None else 'MATCH' if actual == predicate['expected'] else 'MISMATCH',
            'expected': predicate['expected'], 'actual': actual,
            'scope': 'THIS_BOUND_DECLARED_PREDICATE_ONLY; free-text interpretation and physical truth remain unreviewed.'}


def match_method(nodes, method_key, binding, reader):
    proposal = nodes[method_key]['body']; context = nodes[proposal['constraint']]['body']['context']
    definition = algorithm_atlas.PROFILES[proposal['algorithm']]
    value = binding['snapshot']
    if reader == 'SCHEDULE':
        if definition[0] != 'RESOURCE_PEAK': raise ValueError('DISCOVERY_READER_METHOD_MISMATCH')
        expected = {**context['problem'], 'capacity': context['capacity'], 'allocations': context['allocations']}
        if value['receipt']['arguments'] != expected: raise ValueError('DISCOVERY_RECEIPT_INPUT_MISMATCH')
    else:
        if definition[0] not in ('EVALUATE', 'SOLVE_EQUALITIES', 'FEASIBILITY', 'SIMPLIFY'):
            raise ValueError('DISCOVERY_READER_METHOD_MISMATCH')
        action = value['action']
        if action['model_digest'] != math_model.validate(context['model'])['model_digest']:
            raise ValueError('DISCOVERY_RECEIPT_MODEL_MISMATCH')
        if action['backend'] != (definition[3] or 'EXACT'): raise ValueError('DISCOVERY_RECEIPT_BACKEND_MISMATCH')


def observations(kernel, value, nodes, status, principal):
    results = []
    for ident in value['observations']:
        with kernel.db() as db: observed = desk.read(db, 'discovery_observation', ident, principal)
        target = observed['target']; state = 'CURRENT'; reasons = []
        for key, digest in observed['dependency_digests'].items():
            if value['bindings']['node_digests'].get(key) != digest or key not in status or status[key]['status'] == 'STALE':
                state = 'STALE'; reasons.append('Relevant declaration/binding changed: ' + key)
        if state == 'CURRENT':
            try:
                current = checked_reader(kernel, observed['reader'], observed['receipt'], principal)
                if current['revision'] != observed['binding']['revision']: raise ValueError('Receipt projection changed')
            except (ValueError, OSError) as exc: state = 'STALE'; reasons.append(str(exc))
        results.append({'id': ident, 'target': target, 'method': observed['method'], 'reader': observed['reader'],
            'receipt': observed['receipt'], 'inquiry_revision_at_capture': observed['inquiry_revision'],
            'status': state, 'reasons': reasons, 'check': observed['check'], 'predicate': observed['predicate'],
            'note': observed['note'], 'reader_revision': observed['binding']['revision']})
    return results


def view(kernel, value, latest, principal):
    nodes, order, status, roots = current_nodes(kernel, value, principal)
    checks = observations(kernel, value, nodes, status, principal)
    for key, item in status.items():
        if item['kind'] not in ('claims', 'hypotheses') or item['status'] == 'STALE': continue
        related = [c for c in checks if c['target'] == key]
        item['checks'] = [c['id'] for c in related]
        current = [c for c in related if c['status'] == 'CURRENT']
        item['historical_checks'] = [c['id'] for c in related if c['status'] == 'STALE']
        if current:
            item['status'] = 'REVIEW_REQUIRED'
            item['reasons'].append('Checked predicates do not establish the meaning of the proposed claim text.')
            item['predicate_summary'] = 'MISMATCH_PRESENT' if any(c['check']['state'] == 'MISMATCH' for c in current) else 'MATCH_PRESENT' if any(c['check']['state'] == 'MATCH' for c in current) else 'UNRESOLVED'
        elif related: item.update(status='STALE', reasons=item['reasons'] + ['Only historical stale checks remain for this declaration.'])
    # Claims checked above may themselves be declared prerequisites of later
    # claims/actions. Forward their stale status through the same DAG.
    for key in order:
        parents = [p for p in nodes[key]['depends_on'] if status[p]['status'] == 'STALE']
        if parents and status[key]['status'] != 'STALE': status[key].update(status='STALE', reasons=['Upstream check/claim is stale: ' + ', '.join(parents)])
    for check in checks:
        if check['status'] == 'CURRENT' and status[check['target']]['status'] == 'STALE':
            check.update(status='STALE', reasons=check['reasons'] + ['A declared prerequisite of the target is stale.'])
    return {'schema': 'ledger.discovery-view/1', 'inquiry': value, 'latest_revision': latest,
        'historical_revision': value['revision'] != latest, 'nodes': [status[k] for k in order], 'observations': checks,
        'state': 'STALE' if any(n['status'] == 'STALE' for n in status.values()) else 'REVIEW_REQUIRED' if checks else 'DRAFT',
        'changed_roots': roots, 'completion': {'allowed': False, 'reason': 'No claim-interpretation review/compiler acceptance in this foundation.'},
        'notice': NOTICE, 'jobs_submitted': 0, 'model_calls': 0}


def observe(kernel, args, principal):
    value, latest = read(kernel, args['id'], principal)
    if latest != args['expected_revision']: raise ValueError('REVISION_CHANGED: reopen the inquiry')
    nodes, order, status, roots = current_nodes(kernel, value, principal)
    target, method_key = args['target'], args['method']
    if target not in nodes or nodes[target]['kind'] not in ('hypotheses', 'claims'): raise ValueError('DISCOVERY_CHECK_TARGET_REQUIRED')
    if method_key not in nodes or nodes[method_key]['kind'] != 'candidate_methods' or method_key not in ir.closure(nodes, target):
        raise ValueError('DISCOVERY_CHECK_METHOD_NOT_A_DEPENDENCY')
    if status[target]['status'] == 'STALE': raise ValueError('DISCOVERY_STALE_DEPENDENCIES')
    if not status[method_key].get('admission', {}).get('state', '').startswith('MATCH_'):
        raise ValueError('DISCOVERY_METHOD_PROFILE_NOT_ADMITTED')
    binding = checked_reader(kernel, args['reader'], args['receipt'], principal)
    match_method(nodes, method_key, binding, args['reader'])
    check = check_predicate(binding, args['reader'], args['predicate'])
    dependencies = {key: value['bindings']['node_digests'][key] for key in sorted(ir.closure(nodes, target))}
    signature = desk.digest({'target': target, 'method': method_key, 'reader': args['reader'], 'receipt': args['receipt'],
                             'predicate': args['predicate'], 'note': args['note'], 'reader_revision': binding['revision'], 'dependencies': dependencies})
    for ident in value['observations']:
        with kernel.db() as db: old = desk.read(db, 'discovery_observation', ident, principal)
        if old['signature'] == signature: return {'observation': ident, 'revision': latest, 'replayed': True, 'check': old['check']}
    if len(value['observations']) >= 32: raise ValueError('DISCOVERY_OBSERVATION_BOUND')
    observed = desk.new('discovery_observation', principal, schema='ledger.discovery-observation/1',
        inquiry=value['id'], inquiry_revision=latest, target=target, method=method_key,
        reader=args['reader'], receipt=args['receipt'], predicate=copy.deepcopy(args['predicate']), note=args['note'],
        binding=binding, dependency_digests=dependencies, signature=signature, check=check)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE'); live = desk.read(db, 'discovery_inquiry', value['id'], principal)
        desk.edit(live, args['expected_revision']); desk.write(db, observed, principal, 'DISCOVERY_PREDICATE_RECORDED')
        live['observations'].append(observed['id']); desk.write(db, live, principal, 'DISCOVERY_OBSERVATION_LINKED', expected=args['expected_revision'])
    return {'observation': observed['id'], 'revision': live['revision'], 'replayed': False, 'check': check}


def dispatch(kernel, op, args, principal):
    if op == 'discovery.schema': return {'schema': ir.SCHEMA, 'document_schema': ir.IR, 'template': ir.template(), 'notice': NOTICE}
    if op == 'discovery.validate':
        nodes, order = ir.validate(args['document'])
        return {'schema': ir.SCHEMA, 'state': 'VALID_STRUCTURE_NO_AUTHORITY', 'node_order': order,
                'nodes': len(nodes), 'document_digest': desk.digest(args['document']), 'notice': NOTICE}
    if op in ('discovery.create', 'discovery.revise'):
        current = None
        if op == 'discovery.revise':
            current, latest = read(kernel, args['id'], principal)
            if latest != args['expected_revision']: raise ValueError('REVISION_CHANGED: reopen the inquiry')
        bindings = capture(kernel, args['document'], principal)
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if current:
                value = desk.read(db, 'discovery_inquiry', args['id'], principal); desk.edit(value, args['expected_revision'])
            else:
                if args.get('project'): desk.read(db, 'project', args['project'], principal)
                value = desk.new('discovery_inquiry', principal, schema='ledger.discovery-inquiry/1', project=args.get('project'), observations=[])
            value.update(document=copy.deepcopy(args['document']), bindings=bindings, state='PROPOSED_NOT_AUTHORIZED')
            return desk.write(db, value, principal, 'DISCOVERY_DRAFT_SAVED', expected=args['expected_revision'] if current else None)
    if op == 'discovery.get':
        value, latest = read(kernel, args['id'], principal, args.get('revision'))
        return view(kernel, value, latest, principal)
    if op == 'discovery.list':
        with kernel.db() as db: result = desk.listing(db, 'discovery_inquiry', args, principal)
        return {'inquiries': [{k: v[k] for k in ('id', 'revision', 'created', 'project')} | {'title': v['document']['title']} for v in result['records']],
                'limit': result['limit'], 'offset': result['offset'], 'notice': 'Saved draft summaries; open an inquiry to check current bindings.'}
    if op == 'discovery.history':
        value, _ = read(kernel, args['id'], principal)
        with kernel.db() as db:
            rows = db.execute('SELECT revision,payload,digest FROM desk_history WHERE id=? ORDER BY revision DESC LIMIT ? OFFSET ?',
                              (value['id'], args.get('limit', 100), args.get('offset', 0))).fetchall()
        summaries = []
        for revision, raw, digest in rows:
            item = json.loads(raw)
            if desk.digest(item) != digest: raise ValueError('DISCOVERY_HISTORY_DAMAGED')
            summaries.append({'revision': revision, 'title': item['document']['title'], 'document_digest': desk.digest(item['document']), 'observations': len(item['observations'])})
        return {'id': value['id'], 'revisions': summaries}
    if op == 'discovery.observe': return observe(kernel, args, principal)
    raise ValueError('DISCOVERY_OPERATION_UNKNOWN')


def compile_read(program):
    tokens = shlex.split(program)
    if tokens == ['inquiries']: operation, arguments = 'discovery.list', {}
    elif len(tokens) == 4 and tokens[0] == 'inquiry' and tokens[2] == '|' and tokens[3] in ('inspect', 'history'):
        operation, arguments = ('discovery.get' if tokens[3] == 'inspect' else 'discovery.history'), {'id': tokens[1]}
    else: raise ValueError('STAC_DISCOVERY_READ_SYNTAX')
    from .engineering_cli import schemas
    from .adaptive_contract import validate_schema
    validate_schema(arguments, schemas()[operation])
    body = {'schema': 'ledger.stac-discovery-ir/1', 'operation': operation, 'arguments': arguments,
            'effects': ['read'], 'result_type': 'DiscoveryInquiry', 'authority': 'EXISTING_CALLER_PRINCIPAL_REQUIRED'}
    return {**body, 'program_id': desk.digest(body)}
