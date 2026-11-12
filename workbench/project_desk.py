"""Durable ideas, projects, assignments and frozen plans in the shared Kernel.

Planning and review never execute a program or issue a grant. Source snapshots
are registered reads made with the caller's own principal. This is a versioned
record protocol, not another scheduler, grammar, evidence store or catalog.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid

ID = {'type': 'string', 'minLength': 32, 'maxLength': 32}
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 16000}
TITLE = {'type': 'string', 'minLength': 1, 'maxLength': 200}
ADDRESS = {'type': 'string', 'minLength': 3, 'maxLength': 600}
REV = {'type': 'integer', 'minimum': 1}
STRINGS = {'type': 'array', 'items': TEXT}
INPUTS = {'type': 'array', 'items': ADDRESS}
ORIGIN = {'type': 'string', 'enum': ['HUMAN', 'SLATE', 'IMPORTED']}
PAGE = {'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100},
        'offset': {'type': 'integer', 'minimum': 0}}
EDIT = {'id': ID, 'expected_revision': REV}
INTERPRETATION = {'interpretation': TEXT, 'intended_output': TEXT,
                  'questions': STRINGS, 'success': STRINGS, 'stop': STRINGS, 'inputs': INPUTS}
BUDGET = {'type': 'object', 'additionalProperties': False, 'properties': {
    'seconds': {'type': 'integer', 'minimum': 1, 'maximum': 86400},
    'steps': {'type': 'integer', 'minimum': 1, 'maximum': 200},
    'tokens': {'type': 'integer', 'minimum': 0, 'maximum': 1000000},
    'memory_mb': {'type': 'integer', 'minimum': 64, 'maximum': 131072},
    'output_bytes': {'type': 'integer', 'minimum': 1, 'maximum': 104857600},
    'files': {'type': 'integer', 'minimum': 0, 'maximum': 1000}},
    'required': ['seconds', 'steps', 'tokens', 'memory_mb', 'output_bytes', 'files']}
PERMISSIONS = {'type': 'object', 'additionalProperties': False, 'properties': {
    'operations': {'type': 'array', 'items': {'type': 'string', 'maxLength': 100}},
    'effects': {'type': 'array', 'items': {'type': 'string', 'enum': ['read', 'execute', 'candidate', 'approve']}},
    'working_roots': {'type': 'array', 'items': ADDRESS},
    'network': {'type': 'boolean'}, 'expires': {'type': 'number', 'minimum': 1}},
    'required': ['operations', 'effects', 'working_roots', 'network', 'expires']}
FIELDS = {
    'desk.sources.read': ({'address': ADDRESS}, ['address']),
    'projects.create': ({'title': TITLE, 'intent': TEXT, 'origin': ORIGIN}, ['title', 'intent']),
    'projects.list': (PAGE, []), 'projects.get': ({'id': ID}, ['id']),
    'projects.link': ({**EDIT, 'role': {'type': 'string', 'enum': [
        'SOURCE', 'QUESTION', 'DECISION', 'ALTERNATIVE', 'TASK', 'WORKING_COPY', 'OUTPUT']},
        'address': ADDRESS, 'text': TEXT}, ['id', 'expected_revision', 'role']),
    'ideas.capture': ({'text': TEXT, 'project': ID, 'origin': ORIGIN}, ['text']),
    'ideas.list': ({**PAGE, 'project': ID}, []), 'ideas.get': ({'id': ID}, ['id']),
    'ideas.promote': ({**EDIT, 'title': TITLE}, ['id', 'expected_revision', 'title']),
    'assignments.create': ({'project': ID, 'request': TEXT, 'origin': ORIGIN, **INTERPRETATION},
                           ['project', 'request', 'interpretation', 'intended_output', 'success', 'stop']),
    'assignments.list': ({**PAGE, 'project': ID}, []),
    'assignments.get': ({'id': ID}, ['id']),
    'assignments.revise': ({**EDIT, **INTERPRETATION}, ['id', 'expected_revision']),
    'assignments.plan': ({**EDIT, 'language': {'type': 'string', 'enum': ['QUERY', 'STAC', 'CALL']},
        'program': {'type': 'string', 'minLength': 1, 'maxLength': 4096},
        'operation': {'type': 'string', 'maxLength': 100}, 'arguments': {'type': 'object'},
        'permissions': PERMISSIONS, 'budget': BUDGET},
        ['id', 'expected_revision', 'language', 'permissions', 'budget']),
    'plans.get': ({'id': ID}, ['id']),
    'assignments.review': ({**EDIT, 'plan': ID, 'decision': {'type': 'string',
        'enum': ['ACCEPT', 'CHANGES_REQUESTED', 'DEFER']}, 'note': TEXT,
        'outputs': INPUTS, 'unresolved': STRINGS},
        ['id', 'expected_revision', 'plan', 'decision', 'note', 'outputs', 'unresolved']),
    'reviews.get': ({'id': ID}, ['id']),
    'assignments.reopen': ({'id': ID}, ['id']),
}
SCOPES = {op: 'read' if op == 'desk.sources.read' or op.endswith(('.get', '.list', '.reopen')) else
          'approve' if op == 'assignments.review' else 'execute' for op in FIELDS}
DEFAULT_BUDGET = {'seconds': 300, 'steps': 10, 'tokens': 0, 'memory_mb': 1024,
                  'output_bytes': 1048576, 'files': 10}
MAX_SNAPSHOT = 524288
MAX_BINDINGS = 32


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


MIGRATIONS = [(1, (
    'CREATE TABLE desk_records(id TEXT PRIMARY KEY, kind TEXT NOT NULL, owner TEXT NOT NULL, project TEXT, revision INTEGER NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL)',
    'CREATE INDEX desk_owner ON desk_records(owner, kind, project)',
    'CREATE TABLE desk_history(id TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, PRIMARY KEY(id,revision))',
    'CREATE TABLE desk_events(id TEXT PRIMARY KEY, record TEXT NOT NULL, revision INTEGER NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, at REAL NOT NULL)',
    'CREATE INDEX desk_event_record ON desk_events(record, at)',
))]


def ensure(db):
    """Atomic, forward-only component migrations; leave other Kernel tables alone."""
    if not db.in_transaction: db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS desk_migrations(version INTEGER PRIMARY KEY, digest TEXT NOT NULL, applied REAL NOT NULL)')
    applied = dict(db.execute('SELECT version,digest FROM desk_migrations'))
    known = {version: digest(sql) for version, sql in MIGRATIONS}
    if any(version not in known or known[version] != sha for version, sha in applied.items()):
        raise ValueError('PROJECT_DESK_MIGRATION_UNSUPPORTED: use a compatible program')
    if sorted(applied) != list(range(1, len(applied) + 1)):
        raise ValueError('PROJECT_DESK_MIGRATION_GAP')
    for version, statements in MIGRATIONS:
        if version in applied: continue
        for statement in statements: db.execute(statement)
        db.execute('INSERT INTO desk_migrations VALUES(?,?,?)', (version, known[version], time.time()))


def read(db, kind, ident, principal):
    from .engineering_kernel import identifier
    identifier(ident)
    row = db.execute('SELECT payload,digest FROM desk_records WHERE id=? AND kind=? AND owner=?',
                     (ident, kind, principal.identity)).fetchone()
    if not row: raise ValueError('Project Desk record unavailable to this caller')
    value = json.loads(row[0])
    if digest(value) != row[1]: raise ValueError('PROJECT_DESK_RECORD_DAMAGED')
    return value


def write(db, value, principal, action, expected=None):
    raw = canonical(value); sha = digest(value)
    if expected is None:
        db.execute('INSERT INTO desk_records VALUES(?,?,?,?,?,?,?)',
                   (value['id'], value['kind'], value['owner'], value.get('project'), value['revision'], raw, sha))
    else:
        changed = db.execute('UPDATE desk_records SET project=?,revision=?,payload=?,digest=? WHERE id=? AND owner=? AND revision=?',
            (value.get('project'), value['revision'], raw, sha, value['id'], principal.identity, expected)).rowcount
        if changed != 1: raise ValueError('REVISION_CHANGED: reopen before saving')
    db.execute('INSERT INTO desk_history VALUES(?,?,?,?)', (value['id'], value['revision'], raw, sha))
    db.execute('INSERT INTO desk_events VALUES(?,?,?,?,?,?)',
               (uuid.uuid4().hex, value['id'], value['revision'], principal.identity, action, time.time()))
    return value


def new(kind, principal, **values):
    return {'schema': 'arc.project-desk.' + kind + '/1', 'kind': kind, 'id': uuid.uuid4().hex,
            'owner': principal.identity, 'actor': principal.identity, 'revision': 1,
            'created': time.time(), **values}


def edit(value, expected):
    if value['revision'] != expected: raise ValueError('REVISION_CHANGED: reopen before saving')
    value['revision'] += 1; value['updated'] = time.time()
    return value


def bounded(items, maximum=32):
    if len(items) > maximum: raise ValueError('Too many Project Desk items')
    if any(isinstance(item, str) and not item.strip() for item in items):
        raise ValueError('Use meaningful text for each item')
    return items


def result_of(kernel, operation, arguments, principal):
    response = kernel.dispatch(operation, arguments, principal)
    if not response['ok']: raise ValueError(response['error']['message'])
    result = response['result']
    if isinstance(result, dict) and result.get('status') == 'PROJECT_NOT_ATTACHED':
        raise ValueError('Source project is not attached')
    return result


def call_binding(kernel, operation, arguments, principal, address=None):
    from .engineering_kernel import CAPABILITIES
    from .engineering_cli import schemas
    if CAPABILITIES.get(operation) != 'read': raise ValueError('Snapshots require a registered read operation')
    # A Files projection can omit bytes and include volatile metadata. Freeze
    # its actual content identity through the registered source reader instead.
    if operation in ('files.get', 'files.read'):
        address = ('files:' if operation == 'files.get' else 'file:') + arguments['path']
        operation, arguments = 'desk.sources.read', {'address': address}
    elif operation == 'ledger.address.read':
        from .addresses import parse
        kind, ident = parse(arguments['address'])
        if kind in ('files', 'file'):
            operation, arguments = 'desk.sources.read', {'address': kind + ':' + ident}
    value = json.loads(canonical(result_of(kernel, operation, arguments, principal)))
    if len(canonical(value).encode()) > MAX_SNAPSHOT: raise ValueError('Source snapshot too large; select a smaller source')
    return {'operation': operation, 'arguments': arguments, 'address': address,
            'operation_schema': schemas()[operation], 'revision': value['content_revision'] if operation == 'desk.sources.read' else digest(value), 'snapshot': value,
            'captured': time.time(), 'actor': principal.identity}


def snapshots(kernel, addresses, principal):
    from .addresses import parse
    bounded(addresses, MAX_BINDINGS)
    result = []
    for address in addresses:
        kind, ident = parse(address); normal = kind + ':' + ident
        if any(row['address'] == normal for row in result): continue
        result.append(call_binding(kernel, 'ledger.address.read', {'address': normal}, principal, normal))
    if len(canonical(result).encode()) > 2097152: raise ValueError('Combined source snapshots exceed 2 MiB')
    return result


def freshness(kernel, bindings, principal):
    from .engineering_cli import schemas
    states = []
    for binding in bindings:
        state = {'address': binding.get('address'), 'operation': binding['operation'],
                 'frozen_revision': binding['revision']}
        try:
            if schemas().get(binding['operation']) != binding['operation_schema']:
                raise ValueError('Operation schema changed')
            current = call_binding(kernel, binding['operation'], binding['arguments'], principal, binding.get('address'))
            state.update(state='CURRENT' if current['revision'] == binding['revision'] else 'CHANGED',
                         current_revision=current['revision'])
        except (ValueError, OSError) as exc: state.update(state='UNAVAILABLE', reason=str(exc)[:300])
        states.append(state)
    return {'state': 'CURRENT' if all(row['state'] == 'CURRENT' for row in states) else 'REVIEW_REQUIRED', 'sources': states}


def compile_plan(kernel, args, principal):
    """Preserve native IR and types. Only parse and read sources; never run it."""
    from .engineering_cli import schemas
    from .engineering_kernel import CAPABILITIES
    from .agent_operations import validate
    language = args['language']; bindings = []; gaps = []
    if language == 'CALL':
        if 'program' in args or not {'operation', 'arguments'} <= args.keys(): raise ValueError('CALL requires operation and arguments only')
        operation = args['operation']; arguments = args['arguments']
        if operation not in CAPABILITIES: raise ValueError('Unknown planned operation')
        definition = schemas()[operation]
        validate(arguments, definition)
        native = {'schema': 'arc.registered-call/1', 'operation': operation, 'arguments': arguments}
        calls = [{'operation': operation, 'arguments': arguments}]; result_type = 'RegisteredKernelResult'
        if CAPABILITIES[operation] == 'read': bindings.append(call_binding(kernel, operation, arguments, principal))
    else:
        if 'operation' in args or 'arguments' in args or 'program' not in args: raise ValueError('QUERY and STAC require program only')
        op = 'language.parse' if language == 'QUERY' else 'stac.compile'
        native = result_of(kernel, op, {'text' if language == 'QUERY' else 'program': args['program']}, principal)
        if language == 'QUERY':
            calls = [native['call']]; result_type = 'List<StacyQueryRow>'
            bindings.append(call_binding(kernel, native['call']['operation'], native['call']['arguments'], principal))
            for transform in native['transforms']:
                if transform['kind'] in ('join', 'missing'):
                    other = result_of(kernel, 'language.parse', {'text': transform['source']}, principal)
                    if any(t['kind'] in ('join', 'missing') for t in other['transforms']): raise ValueError('Nested joined sources are unsupported')
                    calls.append(other['call']); bindings.append(call_binding(kernel, other['call']['operation'], other['call']['arguments'], principal))
        else:
            ir = native['ir']; result_type = ir.get('result_type', 'EngineeringResult')
            if native['kind'] == 'ENGINEERING':
                calls = [{'operation': node['op'], 'arguments': node['arguments']} for node in ir['nodes'] if node['op'] in CAPABILITIES]
                gaps.append('Engineering IR remains symbolic; its runtime source generation is not frozen by Stage Two.')
            else:
                calls = [{'operation': ir['operation'], 'arguments': ir['arguments']}]
                bindings.append(call_binding(kernel, ir['operation'], ir['arguments'], principal))
    operations = sorted({call['operation'] for call in calls})
    definitions = [{'operation': op, 'scope': CAPABILITIES[op], 'arguments': schemas()[op]} for op in operations]
    if any(CAPABILITIES[op] not in principal.scopes for op in operations): raise ValueError('Planned operation exceeds caller scope')
    return json.loads(canonical(native)), definitions, bindings, gaps, result_type


def permission_request(args, definitions, principal):
    from pathlib import PurePosixPath
    from .engineering_kernel import CAPABILITIES
    value = args['permissions']
    bounded(value['operations']); bounded(value['effects'], 4); bounded(value['working_roots'])
    if set(value['operations']) != {row['operation'] for row in definitions}: raise ValueError('Requested operations must match this plan exactly')
    if set(value['effects']) != {row['scope'] for row in definitions}: raise ValueError('Requested effects must match the registered scopes')
    if any(CAPABILITIES[op] not in principal.scopes for op in value['operations']): raise ValueError('Requested permissions exceed caller scope')
    if value['network']: raise ValueError('Stage Two plans have no network permission')
    if not time.time() < value['expires'] <= time.time() + 30 * 86400: raise ValueError('Plan expiry must be within the next 30 days')
    for root in value['working_roots']:
        path = PurePosixPath(root)
        if path.is_absolute() or '\\' in root or ':' in root or any(p in ('', '.', '..') for p in root.split('/')) or path.parts[0] != 'Files':
            raise ValueError('Working roots must name relative folders under Files')
    return {**value, 'authority': 'REQUEST_ONLY_NO_GRANT', 'caller_scopes_at_save': sorted(principal.scopes)}


def listing(db, kind, args, principal):
    where = 'kind=? AND owner=?'; values = [kind, principal.identity]
    if args.get('project'):
        read(db, 'project', args['project'], principal)
        where += ' AND project=?'; values.append(args['project'])
    rows = db.execute('SELECT id FROM desk_records WHERE ' + where + ' ORDER BY rowid DESC LIMIT ? OFFSET ?',
                      (*values, args.get('limit', 100), args.get('offset', 0)))
    return {'records': [read(db, kind, ident, principal) for ident, in rows],
            'limit': args.get('limit', 100), 'offset': args.get('offset', 0)}


def history(db, value):
    rows = []
    for raw, sha in db.execute('SELECT payload,digest FROM desk_history WHERE id=? ORDER BY revision', (value['id'],)):
        item = json.loads(raw)
        if digest(item) != sha: raise ValueError('PROJECT_DESK_HISTORY_DAMAGED')
        rows.append(item)
    return rows


def dispatch(kernel, op, args, principal):
    if op == 'desk.sources.read': return source_read(kernel, args['address'], principal)
    kind = {'projects': 'project', 'ideas': 'idea', 'assignments': 'assignment', 'plans': 'plan', 'reviews': 'review'}[op.split('.')[0]]
    if op.endswith('.list'):
        with kernel.db() as db: return listing(db, kind, args, principal)
    if op.endswith('.get'):
        with kernel.db() as db: return read(db, kind, args['id'], principal)
    if op == 'assignments.reopen': return reopen(kernel, args['id'], principal)
    # Source reads happen before the write transaction: nested Kernel reads use
    # their own DB connections. Revision checks below make concurrent edits fail.
    captured = snapshots(kernel, args.get('inputs', []), principal) if op in ('assignments.create', 'assignments.revise') and 'inputs' in args else None
    linked = snapshots(kernel, [args['address']], principal)[0] if op == 'projects.link' and 'address' in args else None
    compiled = compile_plan(kernel, args, principal) if op == 'assignments.plan' else None
    output = snapshots(kernel, args['outputs'], principal) if op == 'assignments.review' else None
    with kernel.db() as db:
        # Validate ownership before further reads and recheck it after capture.
        value = read(db, kind, args['id'], principal) if 'id' in args else None
    current = freshness(kernel, value['inputs'], principal) if op == 'assignments.plan' else None
    review_fresh = None
    if op == 'assignments.review':
        with kernel.db() as db: frozen = read(db, 'plan', args['plan'], principal)
        review_fresh = freshness(kernel, frozen['inputs'], principal)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        value = read(db, kind, args['id'], principal) if 'id' in args else None
        if value is not None: edit(value, args['expected_revision'])
        if op == 'projects.create':
            if not args['title'].strip() or not args['intent'].strip(): raise ValueError('A project needs a title and original intent')
            return write(db, new('project', principal, title=args['title'], original_intent=args['intent'],
                origin=args.get('origin', 'HUMAN'), links=[]), principal, 'PROJECT_CREATED')
        if op == 'ideas.capture':
            if not args['text'].strip(): raise ValueError('An idea needs its original words')
            if args.get('project'): read(db, 'project', args['project'], principal)
            return write(db, new('idea', principal, text=args['text'], project=args.get('project'),
                origin=args.get('origin', 'HUMAN')), principal, 'IDEA_CAPTURED')
        if op == 'ideas.promote':
            if value.get('project'): raise ValueError('Idea already has a project')
            project = new('project', principal, title=args['title'], original_intent=value['text'],
                          origin=value['origin'], idea=value['id'], links=[])
            write(db, project, principal, 'PROJECT_FROM_IDEA')
            value['project'] = project['id']; write(db, value, principal, 'IDEA_LINKED', args['expected_revision'])
            return {'idea': value, 'project': project}
        if op == 'projects.link':
            if ('address' in args) == ('text' in args): raise ValueError('Link either an address or written text')
            if len(value['links']) >= 200: raise ValueError('Project link limit reached')
            value['links'].append({'id': uuid.uuid4().hex, 'role': args['role'], 'actor': principal.identity,
                                   'created': time.time(), 'source': linked, 'text': args.get('text')})
            return write(db, value, principal, 'PROJECT_LINKED', args['expected_revision'])
        if op == 'assignments.create':
            read(db, 'project', args['project'], principal)
            if not args['request'].strip(): raise ValueError('Keep the original request in meaningful words')
            fields = {key: args.get(key, []) for key in INTERPRETATION if key != 'inputs'}
            validate_interpretation(fields)
            return write(db, new('assignment', principal, project=args['project'], original_request=args['request'],
                origin=args.get('origin', 'HUMAN'), inputs=captured or [], state='DRAFT', plan=None,
                **fields), principal, 'ASSIGNMENT_CREATED')
        if op == 'assignments.revise':
            fields = {key: args[key] for key in INTERPRETATION if key in args and key != 'inputs'}
            if not fields and captured is None: raise ValueError('No interpretation changes supplied')
            value.update(fields)
            if captured is not None: value['inputs'] = captured
            validate_interpretation(value); value.update(state='DRAFT', plan=None)
            return write(db, value, principal, 'INTERPRETATION_REVISED', args['expected_revision'])
        if op == 'assignments.plan':
            if current['state'] != 'CURRENT': raise ValueError('INPUTS_CHANGED: revise inputs explicitly before freezing a plan')
            native, definitions, sources, gaps, result_type = compiled
            permission = permission_request(args, definitions, principal)
            bindings = value['inputs'] + sources
            if any(b.get('address') == 'assignment:' + value['id'] or
                   b['arguments'].get('address') == 'assignment:' + value['id'] for b in bindings):
                raise ValueError('A plan cannot freeze its own changing assignment as an input')
            if len(bindings) > MAX_BINDINGS or len(canonical(bindings).encode()) > 2097152: raise ValueError('Plan source bound exceeded')
            from .stacy_foundation import seed_status
            seed = seed_status(kernel.root)
            if seed['state'] != 'VERIFIED_SOURCE_BINDINGS': raise ValueError('Program source binding is not current')
            plan = new('plan', principal, project=value['project'], assignment=value['id'],
                assignment_revision=value['revision'], original_request=value['original_request'],
                interpretation=value['interpretation'], intended_output=value['intended_output'], questions=value['questions'],
                success=value['success'], stop=value['stop'], inputs=bindings, source_gaps=gaps,
                language=args['language'], program=args.get('program'), native=native, operations=definitions,
                effects=permission['effects'], caller={'identity': principal.identity, 'mode': principal.mode,
                    'source_paths': list(principal.paths), 'job_tools': list(principal.tools)},
                permissions=permission, budget=args['budget'], result_type=result_type, seed_id=seed['seed_id'],
                execution='NOT_RUN', authority='PLAN_IS_NOT_PERMISSION', origin=value['origin'])
            plan['content_digest'] = digest(plan)
            write(db, plan, principal, 'PLAN_FROZEN'); value.update(plan=plan['id'], state='PLANNED')
            write(db, value, principal, 'PLAN_ATTACHED', args['expected_revision']); return {'assignment': value, 'plan': plan}
        if op == 'assignments.review':
            plan = read(db, 'plan', args['plan'], principal)
            if plan['assignment'] != value['id'] or value['plan'] != plan['id']: raise ValueError('Review requires this assignment\'s current plan')
            unresolved = bounded(args['unresolved'])
            if args['decision'] == 'ACCEPT':
                if not output or unresolved or plan['questions'] or plan['source_gaps'] or review_fresh['state'] != 'CURRENT':
                    raise ValueError('Accept requires frozen outputs, current inputs and resolved questions/source gaps')
                if time.time() >= plan['permissions']['expires']: raise ValueError('Plan expired; save a fresh plan before accepting')
                from .stacy_foundation import seed_status
                seed = seed_status(kernel.root)
                if seed['state'] != 'VERIFIED_SOURCE_BINDINGS' or seed.get('seed_id') != plan['seed_id']:
                    raise ValueError('Program source changed; inspect and save a fresh plan')
            review = new('review', principal, project=value['project'], assignment=value['id'], plan=plan['id'],
                plan_digest=plan['content_digest'], decision=args['decision'], note=args['note'], outputs=output,
                unresolved=unresolved, input_freshness=review_fresh, judgment='OWNER_REVIEW_NOT_EXECUTION_OR_PROOF')
            write(db, review, principal, 'REVIEW_RECORDED'); value.update(state='REVIEWED', review=review['id'])
            write(db, value, principal, 'REVIEW_ATTACHED', args['expected_revision']); return {'assignment': value, 'review': review}
    raise ValueError('Unknown Project Desk operation')


def validate_interpretation(value):
    for key in ('interpretation', 'intended_output'):
        if not value[key].strip(): raise ValueError('An assignment needs an interpretation and intended output')
    for key in ('questions', 'success', 'stop'): bounded(value[key])
    if not value['success'] or not value['stop']: raise ValueError('Define success and when to stop')


def reopen(kernel, ident, principal):
    with kernel.db() as db:
        value = read(db, 'assignment', ident, principal); revisions = history(db, value)
        plans = [read(db, 'plan', row[0], principal) for row in db.execute(
            "SELECT id FROM desk_records WHERE kind='plan' AND owner=? AND project=? ORDER BY rowid", (principal.identity, value['project']))
                 if read(db, 'plan', row[0], principal)['assignment'] == ident]
        reviews = [read(db, 'review', row[0], principal) for row in db.execute(
            "SELECT id FROM desk_records WHERE kind='review' AND owner=? AND project=? ORDER BY rowid", (principal.identity, value['project']))
                   if read(db, 'review', row[0], principal)['assignment'] == ident]
        project = read(db, 'project', value['project'], principal)
        records = [ident] + [p['id'] for p in plans] + [r['id'] for r in reviews]
        placeholders = ','.join('?' for _ in records)
        events = [dict(zip(('id', 'record', 'revision', 'actor', 'action', 'at'), row)) for row in db.execute(
            'SELECT id,record,revision,actor,action,at FROM desk_events WHERE record IN (' + placeholders + ') ORDER BY rowid', records)]
    latest = next((plan for plan in plans if plan['id'] == value['plan']), None)
    fresh = freshness(kernel, latest['inputs'] if latest else value['inputs'], principal)
    outputs = freshness(kernel, reviews[-1]['outputs'], principal) if reviews else None
    open_questions = list(value['questions'])
    if reviews and reviews[-1]['plan'] == value['plan']:
        open_questions = list(dict.fromkeys(open_questions + reviews[-1]['unresolved']))
    from .stacy_foundation import seed_status
    seed = seed_status(kernel.root)
    reasons = []
    if fresh['state'] != 'CURRENT': reasons.append('INPUTS_CHANGED_OR_UNAVAILABLE')
    if open_questions: reasons.append('UNRESOLVED_QUESTIONS')
    if outputs and outputs['state'] != 'CURRENT': reasons.append('OUTPUTS_CHANGED_OR_UNAVAILABLE')
    if latest:
        if latest['source_gaps']: reasons.append('UNBOUND_RUNTIME_SOURCES')
        if latest['permissions']['expires'] <= time.time(): reasons.append('PLAN_EXPIRED')
        if seed.get('seed_id') != latest['seed_id'] or seed['state'] != 'VERIFIED_SOURCE_BINDINGS': reasons.append('PROGRAM_SOURCE_CHANGED')
    return {'schema': 'arc.assignment-reopened/1', 'project': project, 'assignment': value, 'interpretation_history': revisions,
            'plans': plans, 'reviews': reviews, 'journal': events, 'freshness': fresh, 'latest_output_freshness': outputs,
            'unresolved': reasons, 'unresolved_questions': open_questions,
            'restart': 'REOPENED_WITHOUT_EXECUTION', 'automatic_resume': False,
            'authority': 'EXISTING_KERNEL_SCOPES_REQUIRED_FOR_ANY_FUTURE_ACTION'}


def source_read(kernel, address, principal):
    """Read an existing address; file revisions use complete bytes, not mtime."""
    import base64
    from . import addresses, files_service, record_access
    kind, ident = addresses.parse(address)
    if kind not in ('files', 'file'): raise ValueError('Use Files or project-file addresses for byte-bound sources')
    # Preserve the existing read boundary before touching the file itself.
    path = files_service.resolve(kernel, ident) if kind == 'files' else record_access.file_read(kernel, ident, principal)
    if not path.is_file(): raise ValueError('Choose individual files for frozen inputs; folders are navigation')
    before = path.stat()
    if before.st_size > 134217728: raise ValueError('Source exceeds the 128 MiB hashing bound; select a smaller source')
    visible = addresses.read(kernel, kind + ':' + ident, principal)
    sha = hashlib.sha256(); small = bytearray()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            sha.update(block)
            if before.st_size <= 131072: small.extend(block)
    after = path.stat()
    signature = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    if signature(before) != signature(after): raise ValueError('Source changed while being frozen; try again')
    identity = {'address': kind + ':' + ident, 'bytes': after.st_size, 'sha256': sha.hexdigest()}
    return {'schema': 'arc.desk-file-source/1', **identity, 'content_revision': digest(identity),
            'projection': visible, 'exact_bytes_base64': base64.b64encode(small).decode() if after.st_size <= 131072 else None,
            'availability': 'FROZEN_BYTES' if after.st_size <= 131072 else 'HASH_AND_PROJECTION_ONLY',
            'gap': None if after.st_size <= 131072 else 'Full bytes exceed the inline bound; retain this revision in a complete workspace backup.'}
