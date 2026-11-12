"""Typed, revisioned application handoffs in the existing Project Desk store."""
from pathlib import Path
import hashlib
from . import project_desk as records, problem_service as problems, math_service, edit_storage

FIELDS = {'artifacts.get': ({'id': records.ID}, ['id']),
          'artifacts.list': ({'problem': records.ID}, ['problem'])}
SCOPES = {op: 'read' for op in FIELDS}


def read(kernel, ident, p):
    with kernel.db() as db:
        return records.read(db, 'typed_artifact', ident, p)


def reference(value):
    return {'id': value['id'], 'revision': value['revision'], 'digest': records.digest(value),
            'type': value['type'], 'sha256': value['sha256']}


def path(kernel, value):
    target = kernel.state / 'jobs' / value['job'] / value['file']
    root = (kernel.state / 'jobs' / value['job']).resolve()
    if not target.resolve().is_relative_to(root) or any(p.is_symlink() for p in (target, *target.parents)):
        raise ValueError('ARTIFACT_PATH_CHANGED')
    return target


def create(kernel, p, *, job, file, type, problem, copy, data, parents=(), method=None):
    value = records.new('typed_artifact', p, schema='ledger.typed-artifact/1',
        project=problem.get('project'), problem=problem['id'], problem_revision=problem['revision'],
        context_digest=problem['context_digest'], copy=copy, job=job, file=file, type=type,
        parents=[reference(row) for row in parents], method=method, data=data, checked=True,
        authority='ACTUAL_CHECKED_APPLICATION_OUTPUT_NOT_MODEL_TEXT', physical_qualification=False)
    raw = path(kernel, value).read_bytes()
    value.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                 object=edit_storage.keep_bytes(kernel, raw))
    with kernel.db() as db:
        problems.check_bound(problems.load(db, problem['id'], p), {
            'expected_revision': problem['revision'], 'expected_context_digest': problem['context_digest']})
        return records.write(db, value, p, 'TYPED_APPLICATION_OUTPUT_CHECKED')


def require_current(kernel, value, p, seen=None):
    seen = set() if seen is None else seen
    if value['id'] in seen or len(seen) > 32:
        raise ValueError('ARTIFACT_DEPENDENCY_CYCLE_OR_LIMIT')
    seen = seen | {value['id']}
    if not value['checked']:
        raise ValueError('OWNER_EDIT_REQUIRES_RECHECK')
    problem = math_service.current(kernel, value['problem'], p)
    problems.check_bound(problem, {'expected_revision': value['problem_revision'],
                                  'expected_context_digest': value['context_digest']})
    if value.get('method'):
        from . import checked_methods
        checked_methods.require_accepted(kernel, value['method'], p)
    for ref in value['parents']:
        parent = read(kernel, ref['id'], p)
        if reference(parent) != ref:
            raise ValueError('ARTIFACT_PARENT_REVISION_CHANGED')
        require_current(kernel, parent, p, seen)
    current = path(kernel, value)
    if not current.is_file() or hashlib.sha256(current.read_bytes()).hexdigest() != value['sha256']:
        raise ValueError('ARTIFACT_WORKING_BYTES_CHANGED')
    return problem


def owner_revision(kernel, ident, p, digest, data):
    """Only the native-session coordinator calls this after an explicit takeover."""
    value = read(kernel, ident, p)
    raw = path(kernel, value).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('OWNER_EDIT_CHANGED_DURING_CAPTURE')
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        live = records.read(db, 'typed_artifact', ident, p)
        if live != value:
            raise ValueError('ARTIFACT_REVISION_CHANGED')
        previous = live['revision']; records.edit(live, previous)
        live.update(checked=False, authority='OWNER_EDIT_UNCHECKED', data=data,
                    sha256=digest, bytes=len(raw), object=edit_storage.keep_bytes(kernel, raw))
        return records.write(db, live, p, 'OWNER_WORKING_REVISION_REQUIRES_RECHECK', expected=previous)


def view(kernel, value, p):
    try:
        require_current(kernel, value, p); state, reason = 'CURRENT', None
    except (ValueError, OSError, KeyError) as exc:
        state, reason = 'STALE', str(exc)
    with kernel.db() as db:
        versions=[]
        for raw,sha in db.execute('SELECT payload,digest FROM desk_history WHERE id=? ORDER BY revision LIMIT 64',(value['id'],)):
            import json
            row=json.loads(raw)
            if records.digest(row)!=sha or row['owner']!=p.identity:raise ValueError('ARTIFACT_HISTORY_DAMAGED')
            versions.append({k:row[k] for k in ('revision','sha256','object','checked','authority')})
    return {'artifact': value, 'applicability': state, 'reason': reason, 'versions':versions,
            'working_file': str(path(kernel, value)), 'originals_changed': False}


def dispatch(kernel, op, args, p):
    if op == 'artifacts.get':
        return view(kernel, read(kernel, args['id'], p), p)
    with kernel.db() as db:
        problems.load(db, args['problem'], p)
        rows = [records.read(db, 'typed_artifact', row[0], p) for row in db.execute(
            "SELECT id FROM desk_records WHERE owner=? AND kind='typed_artifact' ORDER BY rowid DESC LIMIT 256", (p.identity,))]
    return {'artifacts': [view(kernel, row, p) for row in rows if row['problem'] == args['problem']]}
