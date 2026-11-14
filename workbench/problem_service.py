"""I01 shared problem sheets and source-bound read receipts.

Uses Project Desk's owner-scoped records/history. No scheduler, grant, model
profile or generic execution endpoint is introduced. Only work.read is admitted
by this first action profile; all calls go through the existing Kernel.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import time
from . import project_desk as records, edit_storage

SHA = {'type': 'string', 'minLength': 64, 'maxLength': 64}
SMALL = {'type': 'string', 'minLength': 1, 'maxLength': 200}
VARIABLE = {'type': 'object', 'additionalProperties': False, 'properties': {
    'name': SMALL, 'type': {'type': 'string', 'enum': ['quantity', 'interval', 'boolean', 'text']},
    'unit': {'type': 'string', 'maxLength': 40},
    'state': {'type': 'string', 'enum': ['KNOWN', 'UNKNOWN']},
    'value': {'type': 'string', 'maxLength': 500},
    'basis': {'type': 'string', 'maxLength': 1000}},
    'required': ['name', 'type', 'unit', 'state', 'basis']}
SOURCE = {'type': 'object', 'additionalProperties': False, 'properties': {
    'copy': records.ID, 'path': {'type': 'string', 'minLength': 1, 'maxLength': 1000},
    'label': SMALL}, 'required': ['copy', 'path', 'label']}
CONTENT = {'title': records.TITLE, 'goals': records.STRINGS,
    'variables': {'type': 'array', 'items': VARIABLE}, 'assumptions': records.STRINGS,
    'questions': records.STRINGS, 'candidates': records.STRINGS,
    'sources': {'type': 'array', 'items': SOURCE}}
BOUND = {'id': records.ID, 'expected_revision': records.REV, 'expected_context_digest': SHA}
FIELDS = {
    'problems.create': ({'request': records.TEXT, 'project': records.ID, 'assignment': records.ID, **CONTENT},
        ['request', 'title', 'goals', 'variables', 'sources']),
    'problems.revise': ({**BOUND, **CONTENT}, list(BOUND)),
    'problems.list': ({**records.PAGE, 'project': records.ID}, []),
    'problems.get': ({'id': records.ID}, ['id']),
    'problems.history': ({'id': records.ID, **records.PAGE}, ['id']),
    'problems.tools': ({'id': records.ID}, ['id']),
    'problems.prepare': ({**BOUND, 'source': {'type': 'integer', 'minimum': 0, 'maximum': 7}},
        [*BOUND, 'source']),
    'problems.run': ({'action': records.ID}, ['action']),
}
SCOPES = {op: 'read' if op in ('problems.list', 'problems.get', 'problems.history', 'problems.tools')
          else 'execute' for op in FIELDS}
PROFILE = 'arc.problem-source-read/1'
CONTEXT_KEYS = ('id', 'owner', 'revision', 'project', 'assignment', 'original_request',
                'title', 'goals', 'variables', 'assumptions', 'questions', 'candidates', 'sources')


def context_digest(value):
    return records.digest({k: value[k] for k in CONTEXT_KEYS if k in value})


def load(db, ident, principal):
    value = records.read(db, 'problem', ident, principal)
    if value['context_digest'] != context_digest(value): raise ValueError('PROBLEM_CONTEXT_DAMAGED')
    return value


def check_bound(value, args):
    if value['revision'] != args['expected_revision']: raise ValueError('PROBLEM_REVISION_CHANGED: reopen the problem')
    if value['context_digest'] != args['expected_context_digest']: raise ValueError('PROBLEM_CONTEXT_CHANGED: reopen the problem')


def source_read(kernel, source, principal):
    return records.result_of(kernel, 'work.read', {k: source[k] for k in ('copy', 'path')}, principal)


def bind_sources(kernel, sources, principal):
    if len(sources) > 8: raise ValueError('Choose at most eight text sources')
    result = []; seen = set()
    for source in sources:
        key = (source['copy'], source['path'])
        if key in seen: raise ValueError('Duplicate problem source')
        seen.add(key)
        _, row, _ = edit_storage.workspace(kernel, source['copy'], principal)
        if not row['for_slate']: raise ValueError('Delegate this working copy to Graphite before binding it to a problem')
        actual = source_read(kernel, source, principal)
        result.append({**source, 'sha256': actual['sha256'], 'bytes': actual['bytes'],
                       'operation': 'work.read'})
    return result


def content(kernel, args, principal):
    value = {}
    for key in CONTENT:
        if key not in args: continue
        if key == 'sources': value[key] = bind_sources(kernel, args[key], principal)
        elif key == 'variables':
            variables = args[key]
            if len(variables) > 64: raise ValueError('At most 64 variable placeholders')
            names = set()
            for variable in variables:
                if not variable['name'].strip() or variable['name'] in names: raise ValueError('Variable names must be nonblank and unique')
                names.add(variable['name'])
                if variable['state'] == 'UNKNOWN' and 'value' in variable: raise ValueError('An unknown variable must have no value')
                if variable['state'] == 'KNOWN' and not variable.get('value', '').strip(): raise ValueError('A known variable needs an explicit value')
            value[key] = variables
        elif isinstance(args[key], list): value[key] = records.bounded(args[key])
        else:
            if not args[key].strip(): raise ValueError('Use a meaningful title')
            value[key] = args[key]
    return json.loads(records.canonical(value))


def operation_binding():
    from .engineering_kernel import CAPABILITIES
    from .engineering_cli import schemas
    from . import continuing_work
    return {'operation': 'work.read', 'scope': CAPABILITIES['work.read'],
        'arguments_schema': schemas()['work.read'], 'handler': 'workbench/continuing_work.py',
        'handler_sha256': hashlib.sha256(Path(continuing_work.__file__).read_bytes()).hexdigest()}


def prepare(kernel, args, principal):
    with kernel.db() as db: value = load(db, args['id'], principal)
    check_bound(value, args)
    if 'read' not in principal.scopes: raise ValueError('Source reads require read scope')
    if args['source'] >= len(value['sources']): raise ValueError('Select a bound source')
    binding = operation_binding()
    if binding['scope'] != 'read': raise ValueError('SOURCE_READ_PROFILE_CHANGED')
    source = value['sources'][args['source']]
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE'); check_bound(load(db, value['id'], principal), args)
        action = records.new('problem_action', principal, schema='arc.tool-action/1', profile=PROFILE,
            problem=value['id'], problem_revision=value['revision'], context_digest=value['context_digest'],
            source=source, operation=binding, arguments={k: source[k] for k in ('copy', 'path')},
            effects=['read'], result=None, origin='EXPLICIT_COORDINATOR', model_selected=False)
        action['binding_digest'] = records.digest({k: action[k] for k in
            ('profile', 'problem', 'problem_revision', 'context_digest', 'source', 'operation', 'arguments', 'effects', 'owner')})
        records.write(db, action, principal, 'PREPARED_WITHOUT_EXECUTION')
    return action


def run(kernel, ident, principal):
    with kernel.db() as db:
        action = records.read(db, 'problem_action', ident, principal)
        if action['result']:
            return {'receipt': records.read(db, 'problem_result', action['result'], principal), 'replayed': True}
        value = load(db, action['problem'], principal)
    check_bound(value, {'expected_revision': action['problem_revision'], 'expected_context_digest': action['context_digest']})
    if action['profile'] != PROFILE or action['operation'] != operation_binding() or action['effects'] != ['read']:
        raise ValueError('ACTION_CONTRACT_CHANGED: prepare another action')
    _, row, _ = edit_storage.workspace(kernel, action['source']['copy'], principal)
    if not row['for_slate']: raise ValueError('This working copy is no longer delegated to Graphite')
    started = time.time()
    # Registered read, with existing path/owner/scope checks and an exact UTF-8
    # snapshot. A changed input is refused, never silently rebound.
    actual = source_read(kernel, action['source'], principal)
    if actual['sha256'] != action['source']['sha256'] or actual['bytes'] != action['source']['bytes']:
        raise ValueError('PROBLEM_SOURCE_CHANGED: explicitly save updated source bindings')
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        check_bound(load(db, action['problem'], principal),
            {'expected_revision': action['problem_revision'], 'expected_context_digest': action['context_digest']})
        live = records.read(db, 'problem_action', ident, principal)
        if live['result']: return {'receipt': records.read(db, 'problem_result', live['result'], principal), 'replayed': True}
        receipt = records.new('problem_result', principal, schema='arc.tool-result/1',
            problem=value['id'], problem_revision=value['revision'], context_digest=value['context_digest'],
            action=ident, action_binding_digest=action['binding_digest'], operation='work.read',
            operation_binding=action['operation'], arguments=action['arguments'], effects=['read'],
            started=started, completed=time.time(), status='SUCCEEDED', snapshot=actual,
            output_digest=records.digest(actual), model_calls=0, native_invocations=0)
        records.write(db, receipt, principal, 'ACTUAL_SOURCE_READ')
        records.edit(live, live['revision']); live['result'] = receipt['id']
        records.write(db, live, principal, 'RESULT_BOUND', expected=1)
    return {'receipt': receipt, 'replayed': False}


def related(db, value, kind, principal):
    ids = [row[0] for row in db.execute('SELECT id FROM desk_records WHERE owner=? AND kind=? ORDER BY rowid DESC',
                                      (principal.identity, kind))]
    return [r for ident in ids if (r := records.read(db, kind, ident, principal)).get('problem') == value['id']]


def get(kernel, ident, principal):
    with kernel.db() as db:
        value = load(db, ident, principal)
        actions = related(db, value, 'problem_action', principal)
        receipts = related(db, value, 'problem_result', principal)
    states = []
    for source in value['sources']:
        try:
            actual = source_read(kernel, source, principal)
            state = 'CURRENT' if (actual['sha256'], actual['bytes']) == (source['sha256'], source['bytes']) else 'CHANGED'
            states.append({'copy': source['copy'], 'path': source['path'], 'state': state, 'sha256': actual['sha256']})
        except (ValueError, OSError) as exc:
            states.append({'copy': source['copy'], 'path': source['path'], 'state': 'UNAVAILABLE', 'reason': str(exc)})
    return {'problem': value, 'actions': actions, 'receipts': receipts,
        'freshness': {'state': 'CURRENT' if all(r['state'] == 'CURRENT' for r in states) else 'REVIEW_REQUIRED', 'sources': states},
        'unknowns': [v['name'] for v in value['variables'] if v['state'] == 'UNKNOWN'],
        'automatic_resume': False, 'notice': 'Saved results are observations, not a solved problem or tool qualification.'}


DESCRIPTIONS = {
    'work.read': ('Read selected working-copy text (UTF-8, 64 KiB)', 'copy ID and relative path', 'exact text, byte count and SHA-256'),
    'work.query': ('Query selected working-copy text', 'Ledger query', 'query result'),
    'copies.get': ('Inspect a working copy', 'copy ID', 'copy metadata'),
    'language.parse': ('Inspect a proposed query', 'query text', 'parsed operation and transforms'),
    'stac.compile': ('Compile a proposal as a line', 'program text', 'typed IR or compile diagnostics'),
    'ledger.capabilities.catalog': ('Inspect the complete installed catalogue', 'optional search', 'declared, installed, available, permitted and qualified states'),
}


def tools(kernel, ident, principal):
    from .capability_catalog import catalogue
    with kernel.db() as db: value = load(db, ident, principal)
    full = catalogue(kernel, principal, include_tools=False)
    selected = []
    for row in full['operations']:
        if row['operation'] not in DESCRIPTIONS: continue
        description, inputs, outputs = DESCRIPTIONS[row['operation']]
        selected.append({**row, 'description': description, 'input_description': inputs, 'output_description': outputs,
            'problem_profile': 'ADMITTED_SOURCE_READ' if row['operation'] == 'work.read' else 'DISCOVERY_ONLY'})
    return {'schema': 'arc.problem-tools/1', 'problem': ident, 'context_digest': value['context_digest'],
        'operations': selected, 'registered_operations': full['registered_operations'],
        'registered_job_tools': full['registered_job_tools'], 'action_profile': PROFILE,
        'notice': 'Six relevant operations. Full catalogue remains available. Dispatch checks selected arguments again; discovery grants no authority.'}


def dispatch(kernel, op, args, principal):
    if op == 'problems.prepare': return prepare(kernel, args, principal)
    if op == 'problems.run': return run(kernel, args['action'], principal)
    if op == 'problems.get': return get(kernel, args['id'], principal)
    if op == 'problems.tools': return tools(kernel, args['id'], principal)
    if op == 'problems.list':
        with kernel.db() as db:
            where = 'owner=? AND kind=?'; values = [principal.identity, 'problem']
            if 'project' in args: where += ' AND project=?'; values.append(args['project'])
            ids = [r[0] for r in db.execute('SELECT id FROM desk_records WHERE ' + where + ' ORDER BY rowid DESC LIMIT ? OFFSET ?',
                (*values, args.get('limit', 100), args.get('offset', 0)))]
            return {'records': [load(db, ident, principal) for ident in ids]}
    if op == 'problems.history':
        with kernel.db() as db:
            load(db, args['id'], principal)
            result = []
            for raw, sha in db.execute('SELECT payload,digest FROM desk_history WHERE id=? ORDER BY revision DESC LIMIT ? OFFSET ?',
                    (args['id'], args.get('limit', 100), args.get('offset', 0))):
                value = json.loads(raw)
                if records.digest(value) != sha: raise ValueError('PROBLEM_HISTORY_DAMAGED')
                result.append(value)
            return {'records': result}
    if op == 'problems.create':
        changes = content(kernel, args, principal)
        if not args['request'].strip() or not changes['goals']: raise ValueError('A problem needs its original request and a goal')
        with kernel.db() as db:
            if 'project' in args: records.read(db, 'project', args['project'], principal)
            if 'assignment' in args:
                assignment = records.read(db, 'assignment', args['assignment'], principal)
                if assignment['project'] != args.get('project'): raise ValueError('Assignment belongs to another project')
                if assignment['original_request'] != args['request']: raise ValueError('Keep the assignment original request exactly')
            value = records.new('problem', principal, schema='arc.problem/1', original_request=args['request'],
                project=args.get('project'), assignment=args.get('assignment'),
                **{'assumptions': [], 'questions': [], 'candidates': [], **changes})
            value['context_digest'] = context_digest(value)
            return records.write(db, value, principal, 'PROBLEM_CREATED')
    if op == 'problems.revise':
        with kernel.db() as db: check_bound(load(db, args['id'], principal), args)
        changes = content(kernel, args, principal)
        if not changes: raise ValueError('Supply at least one problem change')
        if changes.get('goals') == []: raise ValueError('Keep at least one goal')
        with kernel.db() as db:
            db.execute('BEGIN IMMEDIATE'); value = load(db, args['id'], principal); check_bound(value, args)
            records.edit(value, args['expected_revision']); value.update(changes)
            value['context_digest'] = context_digest(value)
            return records.write(db, value, principal, 'PROBLEM_REVISED', expected=args['expected_revision'])
    raise ValueError('Unknown problem operation')
