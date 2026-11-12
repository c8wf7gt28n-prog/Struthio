"""Frozen multi-file proposals, explicit owner apply/publish, recovery and undo.

Updates are atomic per file, recoverable as a batch, never claimed globally
atomic. Linux exchange/no-replace renames retain displaced bytes until journal
acknowledgment. External writers must be closed: Ledger cannot lock other apps.
"""
from __future__ import annotations
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from . import edit_storage as store, import_profiles as imports, project_desk as records, working_copies as copies, files_service, cell_edits

SHA = {'type': 'string', 'minLength': 64, 'maxLength': 64}
PATH = {'type': 'string', 'minLength': 1, 'maxLength': 1000}
EDIT = {'type': 'object', 'additionalProperties': False, 'properties': {
    'start': {'type': 'integer', 'minimum': 0}, 'end': {'type': 'integer', 'minimum': 0},
    'old': {'type': 'string', 'maxLength': 16000}, 'new': {'type': 'string', 'maxLength': 16000}}, 'required': ['start', 'end', 'old', 'new']}
OP = {'type': 'object', 'additionalProperties': False, 'properties': {
    'op': {'type': 'string', 'enum': ['WRITE', 'PATCH', 'CREATE', 'DELETE', 'RENAME', 'CELLS']},
    'path': PATH, 'base_sha256': SHA, 'text': {'type': 'string', 'maxLength': 1048576}, 'to': PATH,
    'edits': {'type': 'array', 'items': EDIT}, 'sheet': {'type': 'string', 'maxLength': 200},
    'cells': {'type': 'array', 'items': cell_edits.CELL}}, 'required': ['op', 'path']}
BOUND = {'copy': records.ID}
APPLY = {'id': records.ID, 'expected_digest': SHA}
FIELDS = {
    'changes.workspaces': ({'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100}, 'offset': {'type': 'integer', 'minimum': 0}}, []),
    'changes.workspace': ({'id': records.ID}, ['id']),
    'changes.file': ({**BOUND, 'path': PATH}, ['copy', 'path']),
    'changes.cell': ({**BOUND, 'path': PATH, 'sheet': {'type': 'string', 'maxLength': 200}, 'cell': {'type': 'string', 'maxLength': 12}}, ['copy', 'path', 'cell']),
    'changes.propose': ({**BOUND, 'operations': {'type': 'array', 'items': OP}, 'note': {'type': 'string', 'maxLength': 4000},
        'origin': {'type': 'string', 'enum': ['HUMAN', 'SLATE', 'IMPORTED']}}, ['copy', 'operations']),
    'changes.from_slate': ({**BOUND, 'job': records.ID}, ['copy', 'job']),
    'changes.original.preview': ({**BOUND, 'note': {'type': 'string', 'maxLength': 4000}}, ['copy']),
    'changes.review': ({'id': records.ID}, ['id']),
    'changes.content': ({'id': records.ID, 'path': PATH, 'side': {'type': 'string', 'enum': ['BEFORE', 'AFTER']},
        'offset': {'type': 'integer', 'minimum': 0, 'maximum': store.MAX_FILE}, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 65536}}, ['id', 'path', 'side']),
    'changes.apply': (APPLY, list(APPLY)), 'changes.publish': (APPLY, list(APPLY)),
    'changes.commits': ({**BOUND, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100}, 'offset': {'type': 'integer', 'minimum': 0}}, ['copy']), 'changes.commit': ({'id': records.ID}, ['id']),
    'changes.recover': ({'id': records.ID, 'action': {'type': 'string', 'enum': ['RESUME', 'ROLLBACK']}}, ['id', 'action']),
    'changes.undo': ({'id': records.ID}, ['id']),
    'changes.report': ({**BOUND, 'assignment': records.ID, 'name': PATH, 'format': {'type': 'string', 'enum': ['MARKDOWN', 'CSV']}}, ['copy', 'assignment', 'name', 'format']),
    'changes.export': ({**BOUND, 'name': files_service.NAME}, ['copy']),
}
READ = {'changes.workspaces', 'changes.workspace', 'changes.file', 'changes.cell', 'changes.review', 'changes.content', 'changes.commits', 'changes.commit'}
SCOPES = {op: 'read' if op in READ else 'approve' if op in ('changes.apply', 'changes.publish', 'changes.recover', 'changes.undo') else 'execute' for op in FIELDS}
CRASH_AT = None
OPAQUE_FORMATS = frozenset({'.pdf', '.docx', '.odt', '.xlsx', '.ods', '.zip', '.png', '.jpg', '.jpeg', '.gif', '.webp',
    '.mp3', '.wav', '.mp4', '.exe', '.dll', '.so', '.gguf', '.sqlite', '.sqlite3', '.db', '.step', '.stp', '.stl', '.dxf'})


class Crash(BaseException): pass


def checkpoint(stage):
    if CRASH_AT == stage: raise Crash(stage)


def sha(raw): return hashlib.sha256(raw).hexdigest()


def load_base(kernel, row): return json.loads(copies.object_bytes(kernel, row['base']))


def tree(kernel, root, meta, capture=False, tracked=None):
    value = imports.folder_scan(root, meta['profile'], meta['limits'], kernel if capture else None)
    for item in value['entries']:
        if item['state'] != 'INCLUDED' and item['path'] in (tracked or {}):
            raise ValueError('A tracked file is now excluded/unreadable; it cannot be treated as a deletion')
    return value


def describe_workspace(kernel, ident, principal):
    meta, row, root = store.workspace(kernel, ident, principal, False)
    base = load_base(kernel, row); unavailable = None
    try: current = tree(kernel, root, meta, tracked=base['files'])
    except (ValueError, OSError) as exc:
        unavailable = str(exc); current = {'files': {}, 'directories': [], 'entries': []}
    with kernel.db() as db: proposals = store.listing(db, principal.identity, 'proposal', ident, 20)
    return {**meta, 'name': root.name, 'work': row['work'], 'address': 'files:' + row['work'], 'source': row['source'],
        'for_slate': bool(row['for_slate']), 'base_manifest': row['base'], 'files': current['files'],
        'unavailable': unavailable,
        'directories': current['directories'], 'excluded': [e for e in current['entries'] if e['state'] != 'INCLUDED'],
        'proposals': [{'id': p['id'], 'target': p['target'], 'note': p['note'], 'changes': len(p['changes']), 'content_digest': p['content_digest']} for p in proposals],
        'master_update': meta['original_update'], 'notice': 'Work in this copy. Updating originals is a separate owner action.'}


def target_root(kernel, row, meta, target):
    if target == 'WORKING': return files_service.root(kernel, create=False) / row['work']
    if meta['source_kind'] == 'PILL': raise ValueError('A received pill has no local master; return a signed result to its owner')
    if meta['source_kind'] != 'FOLDER': raise ValueError('ZIP originals are not rewritten; export the working folder as new')
    path = imports.source_place(kernel, row['source'])
    if not path.is_dir(): raise ValueError('The original project folder is unavailable')
    return path


def check_path(meta, rel):
    store.relative(rel)
    reason = imports.eligibility(rel, meta['profile'])
    if reason: raise ValueError('Edit target is excluded by this import profile: ' + reason)


def file_value(kernel, ident, rel, principal):
    meta, row, root = store.workspace(kernel, ident, principal); check_path(meta, rel)
    info = store.inspect_file(root, rel, meta['limits']['file_bytes'])
    if not info: raise ValueError('Working file not found')
    value = {'path': rel, **info, 'text': None, 'adapter': 'OPAQUE_OR_LARGE_BYTES', 'sheets': []}
    if info['bytes'] <= 1048576 and Path(rel).suffix.casefold() not in OPAQUE_FORMATS:
        raw, measured = store.read_bytes(root, rel, 1048576)
        if measured['sha256'] != info['sha256']: raise ValueError('Working file changed during inspection')
        try:
            text = raw.decode('utf-8')
            if '\x00' not in text: value.update(text=text, adapter='EXACT_UTF8_TEXT')
        except UnicodeError: pass
    if Path(rel).suffix.casefold() in ('.csv', '.tsv', '.xlsx'):
        try:
            raw, measured = store.read_bytes(root, rel, 16 * 1024 * 1024)
            if measured['sha256'] != info['sha256']: raise ValueError('Working file changed during inspection')
            value.update(cell_edits.describe(raw, Path(rel).suffix.casefold()))
        except (ValueError, KeyError, IndexError, UnicodeError, OSError) as exc: value['adapter_limit'] = str(exc)
    return value


def patch_text(raw, edits):
    from .agent_operations import validate
    base = raw.decode('utf-8')
    if '\x00' in base or not 1 <= len(edits) <= 200: raise ValueError('Use one to 200 exact text ranges')
    ordered = sorted(edits, key=lambda e: e['start']); last_end = 0; last_start = -1; result = []
    for edit in ordered:
        validate(edit, EDIT); start, end = edit['start'], edit['end']
        if start < last_end or start == last_start or start > end or end > len(base) or base[start:end] != edit['old']:
            raise ValueError('Text patch ranges are ambiguous or their exact old text changed')
        result.extend((base[last_end:start], edit['new'])); last_start, last_end = start, end
    result.append(base[last_end:]); output = ''.join(result).encode()
    if len(output) > 4194304: raise ValueError('Text patch output exceeds 4 MiB')
    return output


def freeze(kernel, meta, row, changes, principal, target, note='', operations=None, provenance=None, baseline_after=None, fixed_id=None):
    from . import work_scope
    work_scope.check()
    if fixed_id:
        with kernel.db() as db:
            if db.execute('SELECT 1 FROM edit_records WHERE id=? AND owner=? AND kind=?',(fixed_id,principal.identity,'proposal')).fetchone():return store.get(db,principal.identity,'proposal',fixed_id)
    if not changes or len(changes) > 200: raise ValueError('A proposal needs one to 200 file changes')
    paths = [c['path'] for c in changes]
    if len({p.casefold() for p in paths}) != len(paths): raise ValueError('Overlapping or case-colliding proposal paths')
    for path in paths:
        check_path(meta, path)
        if any(other.startswith(path + '/') or path.startswith(other + '/') for other in paths if other != path):
            raise ValueError('A proposal path cannot also be another target\'s parent')
    checks = []; review = []
    for change in changes:
        item = {**change}; suffix = Path(change['path']).suffix.casefold()
        if change['after']:
            length = (copies.store(kernel) / change['after']).stat().st_size
            if length > meta['limits']['file_bytes']: raise ValueError('Proposed file exceeds reviewed limits')
            if length <= 4194304:
                raw = store.object_bytes(kernel, change['after'])
                if imports.SENSITIVE.search(raw): raise ValueError('Sensitive content cannot be added by this proposal')
                if suffix == '.json':
                    from .record_io import strict_json
                    strict_json(raw); checks.append({'path': change['path'], 'check': 'JSON_PARSE', 'state': 'PASSED'})
                if suffix in ('.csv', '.tsv'):
                    cell_edits.csv_table(raw, suffix); checks.append({'path': change['path'], 'check': 'CSV_PARSE_NO_EVALUATION', 'state': 'PASSED'})
                if suffix == '.py':
                    try: ast.parse(raw)
                    except SyntaxError as exc: raise ValueError('Python parse check failed at line ' + str(exc.lineno)) from None
                    checks.append({'path': change['path'], 'check': 'PYTHON_PARSE_NO_EXECUTION', 'state': 'PASSED'})
        if change.get('adapter_report'): checks.append({'path': change['path'], 'check': 'CELL_BASE_AND_FORMAT_PROFILE', 'state': 'PASSED', **change['adapter_report']})
        diff = ''
        try:
            before = store.object_bytes(kernel, change['before']).decode('utf-8') if change['before'] else ''
            after = store.object_bytes(kernel, change['after']).decode('utf-8') if change['after'] else ''
            if '\x00' not in before + after:
                diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), 'before/' + change['path'], 'after/' + change['path']))
        except (ValueError, UnicodeError): pass
        item.update(diff=diff[:24000], diff_cut=len(diff) > 24000); review.append(item)
    value = {'schema': 'arc.change-set/1', 'id': fixed_id or work_scope.proposal_id() or uuid.uuid4().hex, 'owner': principal.identity, 'copy': row['id'],
        'created': time.time(), 'target': target, 'changes': review, 'operations': operations or [], 'note': note,
        'checks': checks, 'provenance': provenance or {'origin': 'HUMAN'}, 'baseline_before': row['base'],
        'baseline_after': baseline_after, 'complete': True, 'authority': 'FROZEN_PROPOSAL_NOT_PERMISSION',
        'atomicity': 'RECOVERABLE_PER_FILE_NOT_GLOBALLY_ATOMIC'}
    value['content_digest'] = records.digest(value)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE'); work_scope.check(db)
        if work_scope.current():
            existing=db.execute('SELECT 1 FROM edit_records WHERE id=?',(value['id'],)).fetchone()
            if existing:return store.get(db,principal.identity,'proposal',value['id'])
            value['provenance']={**value['provenance'],'work_order':work_scope.current()['work'],'work_step':work_scope.current()['step']}
            value.pop('content_digest'); value['content_digest']=records.digest(value)
            if len(records.canonical(value).encode())>work_scope.current()['output_bytes']:raise ValueError('BUDGET_OUTPUT_BYTES')
        return store.put(db, principal.identity, 'proposal', value)


def propose(kernel, args, principal, provenance=None):
    if len(records.canonical(args).encode()) > 1048576: raise ValueError('Proposal requests are limited to 1 MiB; use exact patches or a native editor for large files')
    meta, row, root = store.workspace(kernel, args['copy'], principal)
    operations = args['operations']
    if not 1 <= len(operations) <= 100: raise ValueError('Use one to 100 explicit operations')
    changes = []
    for operation in operations:
        kind = operation['op']; rel = operation['path']; check_path(meta, rel)
        if kind in ('CREATE', 'WRITE', 'PATCH') and Path(rel).suffix.casefold() in OPAQUE_FORMATS:
            raise ValueError('This format needs its declared cell adapter or a native application; plain-text rewriting is refused')
        required = {'op', 'path'} | ({'text'} if kind == 'CREATE' else {'base_sha256'})
        permitted = required | {'WRITE': {'text'}, 'PATCH': {'edits'}, 'CREATE': set(), 'DELETE': set(), 'RENAME': {'to'}, 'CELLS': {'cells', 'sheet'}}[kind]
        if set(operation) - permitted or not required <= set(operation): raise ValueError('Unknown or missing fields for ' + kind)
        if kind != 'CREATE':
            old = store.keep_file(kernel, root, rel, meta['limits']['file_bytes'])
            if old['sha256'] != operation['base_sha256']: raise ValueError('STALE_BASE: ' + rel)
            before = old['sha256']; mode = old['mode']
        else:
            if store.inspect_file(root, rel): raise ValueError('Create target already exists')
            before = None; mode = 0o644
        after = None; report = None
        if kind in ('CREATE', 'WRITE'):
            if 'text' not in operation: raise ValueError('Text is required')
            if kind == 'WRITE':
                original = store.object_bytes(kernel, before, 4194304).decode('utf-8')
                if '\x00' in original: raise ValueError('Write supports UTF-8 text only')
            text = operation['text']
            if '\x00' in text: raise ValueError('Text contains a NUL')
            if kind == 'WRITE' and original.startswith('\ufeff') and not text.startswith('\ufeff'): text = '\ufeff' + text
            after = store.keep_bytes(kernel, text.encode())
        elif kind == 'PATCH':
            after = store.keep_bytes(kernel, patch_text(store.object_bytes(kernel, before, 4194304), operation.get('edits', [])))
        elif kind == 'CELLS':
            raw = store.object_bytes(kernel, before, 16 * 1024 * 1024)
            edited, report = cell_edits.apply(raw, Path(rel).suffix.casefold(), operation.get('cells', []), operation.get('sheet'))
            after = store.keep_bytes(kernel, edited)
        elif kind == 'RENAME':
            target = operation.get('to'); check_path(meta, target)
            if store.inspect_file(root, target): raise ValueError('Rename destination exists')
            changes.append({'path': target, 'before': None, 'after': before, 'before_mode': None, 'after_mode': mode, 'operation': 'RENAME_TO', 'rename_from': rel})
        if before == after: raise ValueError('An operation does not change any bytes')
        changes.append({'path': rel, 'before': before, 'after': after, 'before_mode': mode if before else None,
                        'after_mode': mode if after else None, 'operation': kind, 'adapter_report': report})
    return freeze(kernel, meta, row, changes, principal, 'WORKING', args.get('note', ''), operations,
                  provenance or {'origin': args.get('origin', 'HUMAN')})


def original_preview(kernel, args, principal):
    meta, row, root = store.workspace(kernel, args['copy'], principal); target_root(kernel, row, meta, 'ORIGINAL')
    base = load_base(kernel, row); working = tree(kernel, root, meta, True, base['files'])
    changes = []
    for rel in sorted(set(base['files']) | set(working['files'])):
        old = base['files'].get(rel); new = working['files'].get(rel)
        before = old['sha'] if old else None; after = new['sha256'] if new else None
        if before != after:
            changes.append({'path': rel, 'before': before, 'after': after, 'before_mode': old['mode'] if old else None,
                'after_mode': old['mode'] if old and new else new['mode'] if new else None,
                'operation': 'REPLACE' if old and new else 'CREATE' if new else 'DELETE'})
    value = {**working, 'profile': meta['profile'], 'limits': meta['limits']}
    after_manifest = imports.manifest(value)
    # Existing-file permissions belong to the original, not an unnoticed chmod in a draft.
    for rel, entry in after_manifest['files'].items():
        if rel in base['files']: entry['mode'] = base['files'][rel]['mode']
    frozen_base = store.keep_bytes(kernel, json.dumps(after_manifest, sort_keys=True).encode())
    return freeze(kernel, meta, row, changes, principal, 'ORIGINAL', args.get('note', 'Update original from the frozen working revision'), baseline_after=frozen_base)


def entry_state(root, entry):
    current = store.inspect_file(root, entry['path']); current_sha = current['sha256'] if current else None
    temp = store.inspect_file(root, entry['path'].rsplit('/', 1)[0] + '/' + entry['temp'] if '/' in entry['path'] else entry['temp']) if entry.get('temp') else None
    temp_sha = temp['sha256'] if temp else None
    before, after = entry['before'], entry['after']; state = entry.get('stage', 'PENDING')
    if current_sha == before and temp_sha in (None, after): observed = 'PENDING'
    elif current_sha == after and (temp_sha == before if before else temp_sha is None): observed = 'APPLIED'
    elif current_sha == after and temp_sha is None and state == 'FILE_DONE': observed = 'APPLIED'
    else: observed = 'CONFLICT'
    expected_mode = entry.get('after_mode') if observed == 'APPLIED' else entry.get('before_mode')
    if current and expected_mode is not None and current['mode'] != expected_mode: observed = 'CONFLICT'
    return {'path': entry['path'], 'state': observed, 'current': current_sha, 'temporary': temp_sha,
            'journal_stage': state, 'temporary_name': entry.get('temp')}


def read_commit(kernel, ident, principal, observed=True):
    with kernel.db() as db: commit = store.get(db, principal.identity, 'commit', ident)
    if observed:
        meta, row, _ = store.workspace(kernel, commit['copy'], principal, False)
        try:
            root = target_root(kernel, row, meta, commit['target'])
            with store.directory(root): pass
            commit['observed'] = [entry_state(root, e) for e in commit['entries']]
        except (ValueError, OSError): commit['observed'] = [{'path': e['path'], 'state': 'UNAVAILABLE'} for e in commit['entries']]
    return commit


def journal(kernel, commit, actor, stage, detail=None):
    commit['updated'] = time.time()
    with kernel.db() as db:
        store.put(db, actor, 'commit', commit, replace=True)
        db.execute('INSERT INTO edit_journal(commit_id,actor,stage,payload,at) VALUES(?,?,?,?,?)',
            (commit['id'], actor, stage, records.canonical(detail or {}), time.time()))


def staged_file(kernel, root, entry):
    with store.parent(root, entry['path'], create=True) as (fd, name):
        temporary = entry['temp']
        if entry['after']:
            try: out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            except FileExistsError:
                existing = store.inspect_file(root, entry['path'].rsplit('/', 1)[0] + '/' + temporary if '/' in entry['path'] else temporary)
                if existing['sha256'] != entry['after']: raise ValueError('Unexpected recovery temporary; no file was overwritten')
            else:
                try:
                    source = os.open(copies.store(kernel) / entry['after'], os.O_RDONLY | os.O_NOFOLLOW)
                    try:
                        with os.fdopen(os.dup(out), 'wb') as sink: actual = store.fingerprint_fd(source, sink)
                    finally: os.close(source)
                    if actual['sha256'] != entry['after']: raise ValueError('Protected proposed bytes are damaged')
                    os.fchmod(out, entry['after_mode'] if entry['after_mode'] is not None else 0o644); os.fsync(out); os.fsync(fd)
                finally: os.close(out)
        current = store.inspect_file(root, entry['path'])
        if (current['sha256'] if current else None) != entry['before']: raise ValueError('Target changed immediately before mutation')
        if entry['before'] and entry['after']: store.rename_linux(fd, temporary, name, exchange=True)
        elif entry['after']: store.rename_linux(fd, temporary, name)
        else: store.rename_linux(fd, name, temporary)


def cleanup_temporary(root, entry):
    if not entry['before']: return
    rel = entry['path'].rsplit('/', 1)[0] + '/' + entry['temp'] if '/' in entry['path'] else entry['temp']
    value = store.inspect_file(root, rel)
    if value is None: return
    if value['sha256'] != entry['before']: raise ValueError('Displaced bytes differ; temporary retained for manual recovery')
    with store.parent(root, entry['path']) as (fd, _): os.unlink(entry['temp'], dir_fd=fd); os.fsync(fd)


def execute_commit(kernel, commit, principal):
    meta, row, _ = store.workspace(kernel, commit['copy'], principal); root = target_root(kernel, row, meta, commit['target'])
    if commit['target'] == 'ORIGINAL' and row['base'] != commit['baseline_before']:
        raise ValueError('The original baseline changed; this approval cannot be reused')
    observations = [entry_state(root, entry) for entry in commit['entries']]
    if commit['target'] == 'ORIGINAL':
        base = load_base(kernel, row)
        expected = {path: (entry['sha'], entry['mode']) for path, entry in base['files'].items()}
        for entry, observed in zip(commit['entries'], observations):
            if observed['state'] == 'APPLIED':
                if entry['after']: expected[entry['path']] = (entry['after'], entry['after_mode'])
                else: expected.pop(entry['path'], None)
        actual = tree(kernel, root, meta, tracked=base['files'])
        if {p: (v['sha256'], v['mode']) for p, v in actual['files'].items()} != expected:
            commit['state'] = 'BLOCKED'; journal(kernel, commit, principal.identity, 'ORIGINAL_TREE_CHANGED')
            raise ValueError('Original project changed outside this frozen batch; no further file was changed')
    if any(o['state'] == 'CONFLICT' for o in observations):
        commit['state'] = 'BLOCKED'; journal(kernel, commit, principal.identity, 'PREFLIGHT_CONFLICT', {'observed': observations})
        raise ValueError('A target or recovery temporary changed; inspect the whole batch before continuing')
    commit['state'] = 'APPLYING'; journal(kernel, commit, principal.identity, 'BATCH_STARTED')
    try:
        for index, entry in enumerate(commit['entries']):
            from . import work_scope
            work_scope.check()
            from . import work_trail
            if work_trail.execution_held(kernel): raise ValueError('WORK_HELD: batch paused at a file boundary; explicitly resume work before recovery')
            state = entry_state(root, entry)
            if state['state'] == 'CONFLICT': raise ValueError('Target changed during the batch')
            if state['state'] == 'PENDING':
                entry['stage'] = 'INTENT'; journal(kernel, commit, principal.identity, 'FILE_INTENT', {'index': index, 'path': entry['path']}); checkpoint('INTENT')
                staged_file(kernel, root, entry); checkpoint('MUTATED')
                if entry_state(root, entry)['state'] != 'APPLIED': raise ValueError('Concurrent change detected; displaced bytes retained')
            entry['stage'] = 'FILE_DONE'; journal(kernel, commit, principal.identity, 'FILE_DONE', {'index': index, 'path': entry['path']}); checkpoint('FILE_DONE')
            cleanup_temporary(root, entry)
        checkpoint('BEFORE_BATCH_DONE')
        with copies.opened(kernel) as db:
            if commit['target'] == 'ORIGINAL':
                changed = db.execute('UPDATE copies SET base=?,updated=? WHERE id=? AND base=?',
                    (commit['baseline_after'], time.time(), row['id'], commit['baseline_before'])).rowcount
                if changed != 1: raise ValueError('Original baseline changed during commit')
            commit['state'] = 'DONE'; commit['finished'] = time.time(); store.put(db, principal.identity, 'commit', commit, replace=True)
            db.execute('INSERT INTO edit_journal(commit_id,actor,stage,payload,at) VALUES(?,?,?,?,?)', (commit['id'], principal.identity, 'BATCH_DONE', '{}', time.time()))
            if commit.get('parent'):
                parent = store.get(db, principal.identity, 'commit', commit['parent']); parent['state'] = 'UNDONE'
                store.put(db, principal.identity, 'commit', parent, replace=True)
        return commit
    except Exception:
        commit['state'] = 'RECOVERY_REQUIRED'; journal(kernel, commit, principal.identity, 'RECOVERY_REQUIRED')
        raise


def new_commit(kernel, proposal, principal):
    ident = uuid.uuid4().hex
    ordered = sorted(proposal['changes'], key=lambda c: (2 if c['after'] is None else 1 if c['before'] is None else 0, c['path']))
    value = {'schema': 'arc.change-commit/1', 'id': ident, 'owner': principal.identity, 'copy': proposal['copy'],
        'proposal': proposal['id'], 'proposal_digest': proposal['content_digest'], 'target': proposal['target'], 'state': 'PREPARED',
        'created': time.time(), 'baseline_before': proposal['baseline_before'], 'baseline_after': proposal['baseline_after'],
        'entries': [{k: c.get(k) for k in ('path', 'before', 'after', 'before_mode', 'after_mode')} |
            {'temp': '.ledger-edit-' + ident + '-' + str(i), 'stage': 'PENDING'} for i, c in enumerate(ordered)]}
    from . import work_scope
    work_scope.check()
    if work_scope.current() and len(records.canonical(value).encode())+1024+len(ordered)*128>work_scope.current()['output_bytes']:
        raise ValueError('BUDGET_OUTPUT_BYTES: reserve space for the completed commit receipt')
    with kernel.db() as db:
        store.put(db, principal.identity, 'commit', value)
        db.execute('INSERT INTO edit_applications VALUES(?,?)', (proposal['id'], ident))
    return value


def apply_proposal(kernel, args, principal, original=False):
    with kernel.db() as db: proposal = store.get(db, principal.identity, 'proposal', args['id'])
    if proposal.get('provenance',{}).get('origin')=='PAIRED_PILL_RESULT':
        from .pills import ring
        ring(kernel).peer(proposal['provenance']['sender'])
    if proposal['content_digest'] != args['expected_digest']: raise ValueError('Frozen proposal digest differs')
    if proposal['target'] != ('ORIGINAL' if original else 'WORKING'): raise ValueError('Use the separate original-publish action for original files')
    with store.lock(kernel, proposal['copy']):
        with kernel.db() as db: prior = db.execute('SELECT commit_id FROM edit_applications WHERE proposal=?', (proposal['id'],)).fetchone()
        if prior: return read_commit(kernel, prior[0], principal)
        with kernel.db() as db: active = store.listing(db, principal.identity, 'commit', proposal['copy'], 1000)
        if any(c['state'] not in ('DONE', 'UNDONE') for c in active): raise ValueError('Reconcile the unfinished batch before starting another update')
        commit = new_commit(kernel, proposal, principal)
        return execute_commit(kernel, commit, principal)


def undo(kernel, commit, principal):
    if commit.get('parent') or commit['state'] == 'UNDONE': raise ValueError('Freeze a new proposal for redo; this update has already been undone')
    with kernel.db() as db: related = store.listing(db, principal.identity, 'commit', commit['copy'], 1000)
    if any(c.get('parent') == commit['id'] and c['state'] not in ('DONE', 'UNDONE') for c in related):
        raise ValueError('Resume the unfinished rollback before creating another undo')
    meta, row, _ = store.workspace(kernel, commit['copy'], principal); root = target_root(kernel, row, meta, commit['target'])
    active = []
    for entry in commit['entries']:
        observed = entry_state(root, entry)
        if observed['state'] == 'CONFLICT': raise ValueError('Undo would overwrite a later outside edit; no rollback started')
        if observed['state'] == 'APPLIED': active.append(entry)
    if commit['target'] == 'ORIGINAL' and row['base'] not in (commit['baseline_before'], commit['baseline_after']):
        raise ValueError('A later original update exists; undo the latest update first')
    ident = uuid.uuid4().hex
    reverse = {'schema': 'arc.change-commit/1', 'id': ident, 'owner': principal.identity, 'copy': commit['copy'],
        'parent': commit['id'], 'proposal': commit['proposal'], 'proposal_digest': commit['proposal_digest'], 'target': commit['target'],
        'state': 'PREPARED', 'created': time.time(), 'baseline_before': row['base'], 'baseline_after': commit['baseline_before'],
        'entries': [{'path': e['path'], 'before': e['after'], 'after': e['before'], 'before_mode': e['after_mode'], 'after_mode': e['before_mode'],
            'temp': '.ledger-edit-' + ident + '-' + str(i), 'stage': 'PENDING'} for i, e in enumerate(reversed(active))]}
    # Retained original temporaries are no longer needed only after their bytes
    # are verified and the applied entry is durably acknowledged.
    for e in active:
        e['stage'] = 'FILE_DONE'; journal(kernel, commit, principal.identity, 'RECONCILED_FOR_UNDO', {'path': e['path']}); cleanup_temporary(root, e)
    for e in commit['entries']:
        if e in active or not e['after']: continue
        rel = e['path'].rsplit('/', 1)[0] + '/' + e['temp'] if '/' in e['path'] else e['temp']
        temporary = store.inspect_file(root, rel)
        if temporary:
            if temporary['sha256'] != e['after']: raise ValueError('Unexpected pending temporary retained for recovery')
            with store.parent(root, e['path']) as (fd, _): os.unlink(e['temp'], dir_fd=fd); os.fsync(fd)
    with kernel.db() as db: store.put(db, principal.identity, 'commit', reverse)
    return execute_commit(kernel, reverse, principal)


def review(kernel, proposal, principal):
    meta, row, _ = store.workspace(kernel, proposal['copy'], principal, False)
    conflicts = []
    try:
        root = target_root(kernel, row, meta, proposal['target'])
        with store.directory(root): pass
        for entry in proposal['changes']:
            actual = store.inspect_file(root, entry['path'])
            if (actual['sha256'] if actual else None) != entry['before'] or (actual and actual['mode'] != entry['before_mode']): conflicts.append(entry['path'])
        if proposal['target'] == 'ORIGINAL':
            baseline = load_base(kernel, row); current = tree(kernel, root, meta, tracked=baseline['files'])
            if {p: (v['sha256'], v['mode']) for p, v in current['files'].items()} != {p: (v['sha'], v['mode']) for p, v in baseline['files'].items()}:
                conflicts.append('ORIGINAL_SOURCE_TREE_CHANGED')
    except (ValueError, OSError): conflicts.append('SOURCE_OR_WORKING_FILES_UNAVAILABLE')
    if proposal['target'] == 'ORIGINAL' and row['base'] != proposal['baseline_before']: conflicts.append('ORIGINAL_BASELINE_CHANGED')
    return {'proposal': proposal, 'state': 'CONFLICT' if conflicts else 'READY_FOR_OWNER_REVIEW', 'conflicts': conflicts,
            'checks_meaning': 'Only named parser/cell/base checks ran; no build, engineering proof or formula calculation is implied.'}


def report_proposal(kernel, args, principal):
    import csv, io
    sheet = records.result_of(kernel, 'assignments.reopen', {'id': args['assignment']}, principal); a = sheet['assignment']
    if args['format'] == 'MARKDOWN':
        text = '# Assignment report\n\n## Original request\n\n' + a['original_request'] + '\n\n## Interpretation\n\n' + a['interpretation']
        text += '\n\n## Intended output\n\n' + a['intended_output'] + '\n\n## Sources\n\n'
        text += '\n'.join('- ' + str(b.get('address') or b['operation']) + ' · ' + b['revision'] for b in a['inputs'])
        text += '\n\n## Unresolved\n\n' + ('\n'.join(sheet['unresolved_questions'] + sheet['unresolved']) or 'No unresolved items recorded.') + '\n'
    else:
        out = io.StringIO(); writer = csv.writer(out); writer.writerow(['Address or reader', 'Frozen revision'])
        for b in a['inputs']: writer.writerow([b.get('address') or b['operation'], b['revision']])
        text = out.getvalue()
    return propose(kernel, {'copy': args['copy'], 'operations': [{'op': 'CREATE', 'path': args['name'], 'text': text}], 'note': 'Generated from selected assignment records'}, principal,
        {'origin': 'REGISTERED_REPORT_GENERATOR', 'operation': 'changes.report', 'assignment': a['id'], 'assignment_revision': a['revision'], 'source_digest': records.digest(sheet)})


def export_copy(kernel, args, principal):
    import zipfile
    meta, row, root = store.workspace(kernel, args['copy'], principal)
    value = tree(kernel, root, meta, True, load_base(kernel, row)['files'])
    identity = uuid.uuid4().hex; output = files_service.root(kernel) / files_service.EXPORTS
    output.mkdir(mode=0o700, exist_ok=True)
    name = files_service.clean_name(args.get('name', root.name + '-result-' + identity[:8] + '.zip'))
    if not name.casefold().endswith('.zip'): raise ValueError('Choose a ZIP export name')
    temp = output / ('.edit-export-' + identity)
    manifest = {'schema': 'arc.profile-export/1', 'copy': row['id'], 'profile': meta['profile'], 'limits': meta['limits'],
        'files': value['files'], 'directories': value['directories'], 'excluded': [e for e in value['entries'] if e['state'] != 'INCLUDED'],
        'generation': 'changes.export', 'authority': 'DATA_ONLY_NO_EXECUTION_OR_SOURCE_ACCEPTANCE'}
    try:
        with zipfile.ZipFile(temp, 'x', zipfile.ZIP_DEFLATED) as archive:
            os.chmod(temp, 0o600)
            for directory in value['directories']: archive.writestr(directory + '/', b'')
            for rel, info in value['files'].items():
                from . import work_trail
                if work_trail.execution_held(kernel): raise ValueError('Work is held; the export was not published')
                entry = zipfile.ZipInfo(rel); entry.compress_type = zipfile.ZIP_DEFLATED; entry.external_attr = (0o100000 | info['mode']) << 16
                with archive.open(entry, 'w') as destination:
                    source = os.open(copies.store(kernel) / info['sha256'], os.O_RDONLY | os.O_NOFOLLOW)
                    try: captured = store.fingerprint_fd(source, destination)
                    finally: os.close(source)
                    if captured['sha256'] != info['sha256']: raise ValueError('Export object no longer matches its digest')
            archive.writestr('.ledger-export-' + identity + '.json', records.canonical(manifest))
        current = tree(kernel, root, meta, tracked=load_base(kernel, row)['files'])
        if current['files'] != value['files'] or current['directories'] != value['directories']: raise ValueError('Copy changed while exporting; no export was published')
        with temp.open('rb') as stream: os.fsync(stream.fileno())
        with store.directory(output) as fd: store.rename_linux(fd, temp.name, name)
    finally: temp.unlink(missing_ok=True)
    receipt = {'schema': 'arc.profile-export-receipt/1', 'id': identity, 'copy': row['id'], 'owner': principal.identity,
        'created': time.time(), 'export': files_service.rel_of(kernel, output / name), 'sha256': copies.sha_of(output / name),
        'files': len(value['files']), 'manifest_digest': records.digest(manifest), 'profile': meta['profile'], 'originals_changed': False}
    with kernel.db() as db: return store.put(db, principal.identity, 'export', receipt)


def _dispatch(kernel, op, args, principal):
    if op == 'changes.content':
        import base64
        with kernel.db() as db: value = store.get(db, principal.identity, 'proposal', args['id'])
        change = next((c for c in value['changes'] if c['path'] == args['path']), None)
        if change is None: raise ValueError('Path is not in the frozen proposal')
        identity = change['before' if args['side'] == 'BEFORE' else 'after']
        if identity is None: return {'sha256': None, 'bytes': 0, 'offset': 0, 'text': '', 'base64': '', 'has_more': False}
        path = copies.store(kernel) / identity
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            measured = store.fingerprint_fd(fd)
            if measured['sha256'] != identity: raise ValueError('Frozen object is damaged')
            offset = args.get('offset', 0); os.lseek(fd, offset, os.SEEK_SET); raw = os.read(fd, args.get('limit', 65536))
        finally: os.close(fd)
        return {'sha256': identity, 'bytes': measured['bytes'], 'offset': offset, 'base64': base64.b64encode(raw).decode(),
            'text': raw.decode('utf-8', errors='replace') if b'\x00' not in raw else None, 'has_more': offset + len(raw) < measured['bytes'], 'chunk_bytes': len(raw)}
    if op == 'changes.workspaces':
        with copies.opened(kernel) as db:
            values = store.listing(db, principal.identity, 'workspace', limit=args.get('limit', 100), offset=args.get('offset', 0)); summaries = []
            for value in values:
                row = copies.the_copy(db, value['id'])
                summaries.append({**value, 'name': Path(row['work']).name, 'work': row['work'], 'for_slate': bool(row['for_slate']),
                                  'state': row['state'], 'imported_file_count': row['base_size']})
        return {'workspaces': summaries, 'limit': args.get('limit', 100), 'offset': args.get('offset', 0)}
    if op == 'changes.workspace': return describe_workspace(kernel, args['id'], principal)
    if op == 'changes.file': return file_value(kernel, args['copy'], args['path'], principal)
    if op == 'changes.cell':
        meta, _, root = store.workspace(kernel, args['copy'], principal); check_path(meta, args['path'])
        raw, value = store.read_bytes(root, args['path'], 16 * 1024 * 1024)
        return {**value, **cell_edits.describe(raw, Path(args['path']).suffix.casefold(), args.get('sheet'), args['cell'])}
    if op == 'changes.propose':
        with store.lock(kernel, args['copy']): return propose(kernel, args, principal)
    if op == 'changes.original.preview':
        with store.lock(kernel, args['copy']): return original_preview(kernel, args, principal)
    if op == 'changes.report':
        with store.lock(kernel, args['copy']): return report_proposal(kernel, args, principal)
    if op == 'changes.export':
        with store.lock(kernel, args['copy']): return export_copy(kernel, args, principal)
    if op in ('changes.apply', 'changes.publish'): return apply_proposal(kernel, args, principal, op == 'changes.publish')
    if op == 'changes.commits':
        store.workspace(kernel, args['copy'], principal, False)
        with kernel.db() as db: commits = store.listing(db, principal.identity, 'commit', args['copy'], args.get('limit', 100), args.get('offset', 0))
        return {'commits': [{k: c.get(k) for k in ('id', 'copy', 'proposal', 'proposal_digest', 'target', 'state', 'created', 'finished', 'parent')} |
                           {'file_operations': len(c['entries'])} for c in commits], 'limit': args.get('limit', 100), 'offset': args.get('offset', 0)}
    if op == 'changes.review':
        with kernel.db() as db: value = store.get(db, principal.identity, 'proposal', args['id'])
        return review(kernel, value, principal)
    if op == 'changes.commit': return read_commit(kernel, args['id'], principal)
    if op in ('changes.recover', 'changes.undo'):
        commit = read_commit(kernel, args['id'], principal, False)
        with store.lock(kernel, commit['copy']):
            if op == 'changes.undo' or args['action'] == 'ROLLBACK': return undo(kernel, commit, principal)
            if commit['state'] in ('DONE', 'UNDONE'): return commit
            with kernel.db() as db: others = store.listing(db, principal.identity, 'commit', commit['copy'], 1000)
            if any(c.get('parent') == commit['id'] and c['state'] not in ('DONE', 'UNDONE') for c in others):
                raise ValueError('Resume the rollback commit, not its parent update')
            return execute_commit(kernel, commit, principal)
    if op == 'changes.from_slate':
        from .edit_model import from_single_reply
        return from_single_reply(kernel, args, principal)
    raise ValueError('Unknown change-set operation')


def dispatch(kernel, op, args, principal):
    import csv, zipfile, xml.etree.ElementTree as ET
    try: return _dispatch(kernel, op, args, principal)
    except (csv.Error, zipfile.BadZipFile, ET.ParseError, IndexError, RecursionError, NotImplementedError) as exc:
        raise ValueError('Format exceeds this adapter\'s supported profile: ' + type(exc).__name__) from None
