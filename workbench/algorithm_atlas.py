"""Source-bound mathematical method discovery; no solver, job or grant authority.

Admission checks a finite, declared profile. It is not a proof of an owner's
interpretation, a solver result, or acceptance of a learned method version.
"""
from __future__ import annotations
import copy
import json
import shlex
from . import project_desk as desk, problem_service as problems
from . import math_model as math, math_backend, math_service, schedule_math, checked_methods, reason_graph
from .agent_operations import validate

CORPUS = 'workbench/algorithm_corpus.json'
SCHEMA = 'ledger.algorithm-atlas/1'
# The finite adapters are code, not executable strings supplied by the corpus.
PROFILES = {
    'dimensional_arithmetic': ('EVALUATE', ('math.evaluate',), ('math_model.py', 'math_units.py'), None),
    'interval_capacity': ('RESOURCE_PEAK', ('math.schedule', 'methods.preview'), ('schedule_math.py', 'math_units.py', 'checked_methods.py'), None),
    'linear_equalities': ('SOLVE_EQUALITIES', ('math.solve',), ('math_backend.py', 'math_model.py', 'math_units.py'), 'SYMPY'),
    'linear_feasibility': ('FEASIBILITY', ('math.solve',), ('math_backend.py', 'math_model.py', 'math_units.py'), 'Z3'),
    'rational_normalization': ('SIMPLIFY', ('math.solve',), ('math_backend.py', 'math_model.py', 'math_units.py'), 'SYMPY'),
    'dependency_impact': ('DEPENDENCY_IMPACT', ('reasons.impact',), ('reason_service.py', 'reason_graph.py'), None),
    'finite_reason_paths': ('REASON_PROPAGATION', ('reasons.evaluate',), ('reason_service.py', 'reason_graph.py', 'stac/evidence.py'), None),
    'linear_optimization': ('OPTIMIZE_LINEAR', (), (), None),
    'shortest_path': ('SHORTEST_PATH', (), (), None),
    'least_squares': ('FIT_LINEAR', (), (), None),
    'scalar_root': ('ROOT_SCALAR', (), (), None),
    'experimental_design': ('DESIGN_EXPERIMENT', (), (), None),
}
TASK = {'type': 'string', 'enum': [v[0] for v in PROFILES.values()]}
NAME = {'type': 'string', 'minLength': 1, 'maxLength': 80}
CONTEXT = {'type': 'object', 'additionalProperties': False, 'properties': {
    'task': TASK, 'model': {'type': 'object'}, 'graph': {'type': 'object'}, 'node': NAME,
    'problem': {'type': 'object', 'additionalProperties': False, 'properties': problems.BOUND, 'required': list(problems.BOUND)},
    'capacity': schedule_math.NAME,
    'allocations': {'type': 'array', 'minItems': 1, 'maxItems': 32, 'items': schedule_math.PAIR},
    'declarations': checked_methods.DECLARATIONS}, 'required': ['task']}
VERSION = {'expected_catalog_digest': problems.SHA}
FIELDS = {
    'algo.lookup': ({'query': {'type': 'string', 'maxLength': 180}, 'task': TASK, **VERSION}, []),
    'algo.get': ({'id': NAME, **VERSION}, ['id']),
    'algo.find_applicable': ({'context': CONTEXT, 'algorithm': NAME, **VERSION}, ['context']),
}
SCOPES = {op: 'read' for op in FIELDS}
NOTICE = 'Declared-profile admission only. No solver launched, no job submitted, no grant or engineering qualification issued.'


def corpus(kernel):
    from .stacy_foundation import project_file
    from .capability_catalog import source
    from .engineering_cli import schemas
    from .engineering_kernel import CAPABILITIES
    value = json.loads(project_file(kernel.root, CORPUS, 256 * 1024).read_text())
    if set(value) != {'schema', 'version', 'entries'} or value['schema'] != SCHEMA or value['version'] != '1.0.0':
        raise ValueError('ALGORITHM_CORPUS_VERSION_UNSUPPORTED')
    required = {'id', 'title', 'task', 'signature', 'domain', 'preconditions', 'guarantee',
                'non_guarantees', 'cost', 'counterexample', 'references', 'examples', 'licence'}
    seen = set()
    for row in value['entries']:
        if set(row) != required or row['id'] not in PROFILES or row['id'] in seen or row['task'] != PROFILES[row['id']][0]:
            raise ValueError('ALGORITHM_CORPUS_ENTRY_INVALID')
        seen.add(row['id'])
        if any(not isinstance(row[key], str) or not 1 <= len(row[key]) <= 4000
               for key in ('title', 'signature', 'domain', 'guarantee', 'cost', 'counterexample', 'licence')):
            raise ValueError('ALGORITHM_CORPUS_TEXT_INVALID')
        if any(not isinstance(row[key], list) or not 1 <= len(row[key]) <= 16
               or any(not isinstance(text, str) or not text or len(text) > 2000 for text in row[key])
               for key in ('preconditions', 'non_guarantees', 'references')):
            raise ValueError('ALGORITHM_CORPUS_LIST_INVALID')
        if not isinstance(row['examples'], list) or not 1 <= len(row['examples']) <= 3:
            raise ValueError('ALGORITHM_CORPUS_EXAMPLES_INVALID')
        for example in row['examples']:
            if set(example) != {'label', 'context', 'expected_state'} or not isinstance(example['label'], str):
                raise ValueError('ALGORITHM_CORPUS_EXAMPLE_INVALID')
            validate(example['context'], CONTEXT)
    if seen != set(PROFILES): raise ValueError('ALGORITHM_CORPUS_INCOMPLETE')
    paths = {'workbench/algorithm_atlas.py', CORPUS, 'docs/HATCH_ALGORITHM_ATLAS.md',
             'workbench/math_service.py', 'workbench/problem_service.py'}
    paths.update('workbench/' + name for _, _, files, _ in PROFILES.values() for name in files)
    sources = {name: source(kernel.root, name) for name in sorted(paths)}
    contracts = {op: {'scope': CAPABILITIES.get(op), 'arguments': schemas().get(op)}
                 for _, operations, _, _ in PROFILES.values() for op in operations}
    body = {'corpus': value, 'sources': sources, 'contracts': contracts}
    return value, sources, contracts, desk.digest(body)


def describe(row, sources, contracts, principal, backends):
    task, operations, files, backend = PROFILES[row['id']]
    required_paths = ['workbench/' + name for name in files]
    required_paths += ['workbench/algorithm_atlas.py', CORPUS]
    if operations: required_paths += ['workbench/math_service.py', 'workbench/problem_service.py']
    present = all(sources[p]['state'] == 'PRESENT' for p in required_paths)
    registered = all(contracts[op]['arguments'] and contracts[op]['scope'] for op in operations)
    dependencies = {k: backends[k] for k in (('sympy', 'mpmath') if backend == 'SYMPY' else ('z3-solver',) if backend == 'Z3' else ())}
    state = ('NOT_IMPLEMENTED' if not operations else 'SOURCE_MISSING' if not present else
             'CONTRACT_MISSING' if not registered else 'DEPENDENCY_UNAVAILABLE' if any(v['state'] != 'PINNED' for v in dependencies.values()) else 'LINKED')
    return {**copy.deepcopy(row), 'version': '1.0.0',
        'implementation': {'state': state, 'backend': backend, 'dependencies': dependencies,
            'sources': [sources[name] for name in required_paths],
            'operations': [{'operation': op, **contracts[op],
                'fixed_arguments': {'backend': backend} if backend else {},
                'scope_eligible': contracts[op]['scope'] in principal.scopes
                    and not (principal.mode == 'Tutor' and contracts[op]['scope'] != 'read')}
                for op in operations],
            'qualification': 'NOT_CURRENT_HOST_QUALIFIED',
            'notice': 'LINKED means source, registry and pinned packages are present; it does not predict successful execution.'},
        'source_authority': 'AUTHORED_PROFILE_BOUND_TO_EXISTING_ADAPTERS_NOT_A_GENERAL_THEOREM',
        'runtime_authorization': False}


def profile_admission(kernel, principal, ident, context):
    task = context['task']
    if task != PROFILES[ident][0]: return {'state': 'TASK_MISMATCH', 'reasons': ['The requested task has a different mathematical signature.'], 'obligations': []}
    if not PROFILES[ident][1]: return {'state': 'NOT_IMPLEMENTED', 'reasons': ['No registered implementation for this profile.'], 'obligations': []}
    allowed = {'task', 'model'} if task in ('EVALUATE', 'SIMPLIFY', 'SOLVE_EQUALITIES', 'FEASIBILITY') else {'task', 'graph', 'node'} if task == 'DEPENDENCY_IMPACT' else {'task', 'graph'} if task == 'REASON_PROPAGATION' else {'task', 'problem', 'capacity', 'allocations', 'declarations'}
    if set(context) - allowed: return {'state': 'REJECTED_INPUT', 'reasons': ['Fields from a different method profile were supplied.'], 'obligations': []}
    required = allowed - {'node'} if task != 'DEPENDENCY_IMPACT' else allowed
    if required - set(context):
        return {'state': 'NEEDS_INPUT', 'reasons': ['Required: ' + ', '.join(sorted(required - set(context)))], 'obligations': []}
    obligations = []; binding = {'kind': 'DECLARED_INPUT', 'digest': desk.digest(context)}
    # Owner/revision/source checks fail at the existing boundary, not as a
    # claim that a mathematical precondition was disproved.
    problem = None
    if task == 'RESOURCE_PEAK':
        problem = math_service.current(kernel, context['problem']['id'], principal)
        problems.check_bound(problem, context['problem'])
        binding = {'kind': 'OWNED_PROBLEM_REVISION', **context['problem']}
    try:
        if task in ('EVALUATE', 'SIMPLIFY', 'SOLVE_EQUALITIES', 'FEASIBILITY'):
            ir = math.validate(context['model']); values, missing = math.values(ir)
            if task == 'EVALUATE' and missing:
                return {'state': 'NEEDS_INPUT', 'reasons': ['Unknown quantities: ' + ', '.join(missing)], 'obligations': []}
            if task in ('SOLVE_EQUALITIES', 'FEASIBILITY'):
                math.affine(ir)
                if task == 'SOLVE_EQUALITIES':
                    nodes = {n['id']: n for n in ir['model']['nodes']}
                    if not ir['model']['constraints'] or any(nodes[n]['op'] != 'eq' for n in ir['model']['constraints']):
                        raise ValueError('LINEAR_EQUALITIES_REQUIRED; inequalities belong to the feasibility profile')
                    obligations.append('Actual solver must determine consistency and uniqueness; admission proves neither.')
                else: obligations.append('A solver witness or infeasibility decision is still required; no optimality claim.')
            if task == 'SIMPLIFY':
                if ir['model']['constraints'] or any(ir['signatures'][o]['kind'] != 'quantity' for o in ir['model']['outputs']):
                    raise ValueError('NORMALIZATION_REQUIRES_QUANTITY_OUTPUTS_WITHOUT_CONSTRAINTS')
                obligations.extend('Retain original nonzero denominator at node ' + g['denominator']
                                   for g in ir['domain_conditions'] if values[g['denominator']] is None)
            binding = {'kind': 'DECLARED_MATH_MODEL', 'digest': ir['model_digest']}
        elif task == 'RESOURCE_PEAK':
            declarations = context['declarations']
            if any(declarations[k] != value for k, value in checked_methods.EXPECTED.items()):
                raise ValueError('UNSUPPORTED_RESOURCE_ASSUMPTIONS: additive, fixed capacity, half-open, no unmodeled overhead/fragmentation/indivisibility required')
            if not declarations['basis'].strip(): raise ValueError('RESOURCE_DECLARATION_BASIS_REQUIRED')
            if not 1 <= len(context['allocations']) <= 32: raise ValueError('RESOURCE_ALLOCATION_BOUND')
            result = schedule_math.evaluate(problem, context['capacity'], context['allocations'])
            if result['state'] == 'UNKNOWN':
                return {'state': 'NEEDS_INPUT', 'reasons': ['Unknown lifetimes: ' + ', '.join(result['missing'])], 'obligations': []}
            obligations.append('Owner declarations need domain evidence; no allocator, voltage-rail, heat-flow or physical guarantee.')
        else:
            nodes, _, _, _ = reason_graph.validate(context['graph'])
            if task == 'DEPENDENCY_IMPACT' and context['node'] not in nodes:
                raise ValueError('DEPENDENCY_NODE_NOT_DECLARED; cannot infer no impact')
            obligations.append('Dependencies outside the declared graph remain unknown.')
            if task == 'REASON_PROPAGATION':
                obligations.append('Receipt ownership/freshness and rule meaning must be checked by reasons.evaluate on a saved graph.')
            binding = {'kind': 'DECLARED_REASON_GRAPH', 'digest': desk.digest(context['graph'])}
    except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
        return {'state': 'REJECTED_INPUT', 'reasons': [str(exc)], 'obligations': [], 'input_binding': binding}
    return {'state': 'MATCH_WITH_OBLIGATIONS' if obligations else 'MATCH_DECLARED_PROFILE',
            'reasons': ['Inputs fit the bounded declared profile; this is not an execution result.'],
            'obligations': obligations, 'input_binding': binding}


def dispatch(kernel, op, args, principal):
    value, sources, contracts, digest = corpus(kernel)
    if args.get('expected_catalog_digest', digest) != digest: raise ValueError('ALGORITHM_CATALOG_CHANGED: reopen before selecting a method')
    common = {'schema': SCHEMA, 'version': value['version'], 'catalog_digest': digest, 'notice': NOTICE,
              'model_calls': 0, 'solver_calls': 0, 'jobs_submitted': 0, 'runtime_authorization': False}
    backends = math_backend.status()
    def row(entry): return describe(entry, sources, contracts, principal, backends)
    if op == 'algo.lookup':
        terms = args.get('query', '').casefold().split()
        entries = [r for r in value['entries'] if (not args.get('task') or r['task'] == args['task'])
                   and all(t in desk.canonical(r).casefold() for t in terms)]
        return {**common, 'entries': [row(r) for r in entries], 'matches': len(entries)}
    if op == 'algo.get':
        entry = next((r for r in value['entries'] if r['id'] == args['id']), None)
        if entry is None: raise ValueError('ALGORITHM_NOT_REGISTERED')
        return {**common, 'entry': row(entry)}
    if op == 'algo.find_applicable':
        context = args['context']
        if len(desk.canonical(context).encode()) > 128 * 1024: raise ValueError('ALGORITHM_CONTEXT_BOUND')
        validate(context, CONTEXT)
        if args.get('algorithm') and args['algorithm'] not in PROFILES: raise ValueError('ALGORITHM_NOT_REGISTERED')
        entries = [r for r in value['entries'] if r['id'] == args['algorithm']] if args.get('algorithm') else [r for r in value['entries'] if r['task'] == context['task']]
        return {**common, 'candidates': [{**row(r), 'applicability': profile_admission(kernel, principal, r['id'], context)} for r in entries],
                'context_digest': desk.digest(context), 'interpretation': 'Structural compatibility is a hypothesis; outstanding obligations are not discharged by declarations.'}
    raise ValueError('ALGORITHM_OPERATION_UNKNOWN')


def compile_read(program):
    tokens = shlex.split(program)
    if tokens == ['algorithms']: operation, arguments = 'algo.lookup', {}
    elif len(tokens) == 4 and tokens[:2] == ['algorithms', '|'] and tokens[2] in ('find', 'method'):
        operation = 'algo.lookup' if tokens[2] == 'find' else 'algo.get'
        arguments = {'query' if tokens[2] == 'find' else 'id': tokens[3]}
    else: raise ValueError('STAC_ALGORITHM_READ_SYNTAX')
    from .engineering_cli import schemas
    validate(arguments, schemas()[operation])
    body = {'schema': 'ledger.stac-algorithm-ir/1', 'operation': operation, 'arguments': arguments,
            'effects': ['read'], 'result_type': 'AlgorithmAtlasObservation', 'authority': 'EXISTING_CALLER_PRINCIPAL_REQUIRED'}
    return {**body, 'program_id': desk.digest(body)}
