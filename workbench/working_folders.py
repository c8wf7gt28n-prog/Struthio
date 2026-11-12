"""Working copies of folders (Pass B): a project worked on as a copy, updated as one reviewed proposal.

A folder's snapshot is a manifest: every ordinary file in it, by relative path, with its digest, size, time and mode. Each
file's bytes are kept as a protected object, and so is the manifest. Hidden files, machine files (caches, object files…),
links and special files are left out and named, never followed. Up to 500 files and 256 MB.

A proposal is a list of operations: replace, create and delete (a rename is a delete and a create). Review shows every
operation, with line differences for text. Update applies them one file at a time, each journaled like a single-file update
(a replace uses the same private-temporary-then-rename step; a create never overwrites; a delete happens only if the file
still holds what the work began from, and its bytes stay kept). This is a recoverable multi-file update, not an atomic
one: if it stops part-way, each file says what happened, nothing is guessed, and the same approved proposal can be resumed
(files already done are recognised and skipped).
"""
from __future__ import annotations
import hashlib
import json
import os
import stat
import time
import uuid
from pathlib import Path

from . import files_service

MAX_FILES = 500
MAX_TOTAL = 256 * 1024 * 1024


def allowed_folder(kernel, text):
    from .working_copies import allowed_place  # the same rules for where it may be as for a file; then: a folder
    if Path(os.path.normpath(Path(os.path.expanduser(text)))) == Path.home().resolve():
        raise ValueError('COPIES_SOURCE_IS_HOME: choose a project folder, not the whole home folder')
    path = allowed_place(kernel, text)
    if not path.is_dir() or path.is_symlink():raise ValueError('COPIES_SOURCE_NOT_A_FOLDER')
    if path == Path.home().resolve():raise ValueError('COPIES_SOURCE_IS_HOME: choose a project folder, not the whole home folder')
    return path


def scan(root):
    """Ordinary files under root, without following links. Returns ({rel: path}, [skipped with reason])."""
    found, skipped, total = {}, [], 0
    for folder, dirs, files in os.walk(root, followlinks=False):
        here = Path(folder)
        keep = []
        for d in sorted(dirs):
            p = here / d
            if p.is_symlink():skipped.append((p.relative_to(root).as_posix(), 'a link'))
            elif files_service.machine(p):skipped.append((p.relative_to(root).as_posix() + '/', 'hidden or machine folder'))
            else:keep.append(d)
        dirs[:] = keep
        for name in sorted(files):
            p = here / name;rel = p.relative_to(root).as_posix()
            info = os.lstat(p)
            if stat.S_ISLNK(info.st_mode):skipped.append((rel, 'a link'));continue
            if not stat.S_ISREG(info.st_mode):skipped.append((rel, 'not an ordinary file'));continue
            if files_service.machine(p):skipped.append((rel, 'hidden or machine file'));continue
            found[rel] = p;total += info.st_size
            if len(found) > MAX_FILES:raise ValueError('COPIES_FOLDER_TOO_LARGE: up to %d files for now' % MAX_FILES)
            if total > MAX_TOTAL:raise ValueError('COPIES_FOLDER_TOO_LARGE: up to 256 MB for now')
    return found, skipped


def capture_folder(kernel, root):
    from .working_copies import capture, keep_object
    found, skipped = scan(root);files = {}
    for rel, path in found.items():
        data, info = capture(path)
        files[rel] = {'sha': keep_object(kernel, data), 'size': info.st_size, 'mtime': info.st_mtime_ns, 'mode': stat.S_IMODE(info.st_mode)}
    return {'schema': 'arc.copies-folder/1', 'files': files, 'skipped': skipped}


def keep_manifest(kernel, manifest):
    from .working_copies import keep_object
    return keep_object(kernel, json.dumps(manifest, sort_keys=True).encode())


def load(kernel, sha):
    from .working_copies import object_bytes
    return json.loads(object_bytes(kernel, sha))


def now_digests(root, base_files):
    """What the folder holds now, {rel: sha}; byte identity always requires a full hash."""
    from .working_copies import sha_of
    found, _ = scan(root);out = {}
    for rel, path in found.items():
        info = os.lstat(path);old = base_files.get(rel)
        out[rel] = sha_of(path)
    return out


def operations(base_files, now):
    ops = []
    for rel in sorted(set(base_files) | set(now)):
        before = base_files.get(rel, {}).get('sha') if rel in base_files else None;after = now.get(rel)
        if before == after:continue
        ops.append({'op': 'create' if before is None else 'delete' if after is None else 'replace', 'path': rel, 'before': before or '', 'after': after or '',
                    'mode': base_files.get(rel, {}).get('mode')})
    return ops


def start(kernel, db, source, for_slate, principal):
    from .working_copies import object_bytes
    manifest = capture_folder(kernel, source);sha = keep_manifest(kernel, manifest)
    folder = files_service.root(kernel) / 'Working copies';folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    work = files_service.free_name(folder, source.name);work.mkdir(mode=0o700)
    for rel, entry in manifest['files'].items():
        target = work / rel;target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        with open(target, 'xb') as f:f.write(object_bytes(kernel, entry['sha']))
    ident = uuid.uuid4().hex;now = time.time()
    db.execute("INSERT INTO copies(id, owner, source, base, base_size, base_mtime, base_mode, work, for_slate, state, revision, created, updated, kind) "
               "VALUES(?,?,?,?,?,?,?,?,?,'WORKING',0,?,?,'folder')",
               (ident, principal.identity, str(source), sha, len(manifest['files']), 0, stat.S_IMODE(os.stat(source).st_mode),
                files_service.rel_of(kernel, work), int(bool(for_slate)), now, now))
    return ident


def state_of(kernel, row):
    """(original: same|changed|missing, work operations, base files)"""
    base = load(kernel, row['base'])['files']
    source = Path(row['source'])
    if str(row['source']).startswith('pill:'):original = 'same'  # the pill's revision is the frozen original, as received
    elif not source.is_dir():original = 'missing'
    else:original = 'same' if now_digests(source, base) == {k: v['sha'] for k, v in base.items()} else 'changed'
    work = files_service.root(kernel) / row['work']
    ops = operations(base, now_digests(work, base)) if work.is_dir() else None
    return original, ops, base


def propose(kernel, db, row, note, principal):
    from .working_copies import keep_object
    base = load(kernel, row['base'])['files'];work = files_service.root(kernel) / row['work']
    if not work.is_dir():raise ValueError('COPIES_WORK_MISSING: the working copy was moved or put in Trash')
    found, _ = scan(work);now = {}
    for rel, path in found.items():now[rel] = keep_object(kernel, path.read_bytes())  # every file of the proposal is frozen
    ops = operations(base, now)
    if not ops:raise ValueError('COPIES_NOTHING_CHANGED: the working copy is the same as the original')
    for op in ops:
        if op['op'] == 'create':op['mode'] = stat.S_IMODE(os.stat(found[op['path']]).st_mode) & 0o777
    sha = keep_manifest(kernel, {'schema': 'arc.copies-proposal/1', 'base': row['base'], 'ops': ops})
    latest = db.execute("SELECT * FROM copies_proposals WHERE copy=? AND state='READY' ORDER BY revision DESC LIMIT 1", (row['id'],)).fetchone()
    if latest is not None and latest['sha'] == sha:return dict(latest)
    db.execute("UPDATE copies_proposals SET state='SUPERSEDED' WHERE copy=? AND state='READY'", (row['id'],))
    revision = row['revision'] + 1;ident = uuid.uuid4().hex
    db.execute("INSERT INTO copies_proposals VALUES(?,?,?,?,?,?,?,?,'READY')", (ident, row['id'], revision, sha, row['base'], (note or '')[:400], principal.identity, time.time()))
    db.execute('UPDATE copies SET revision=?, updated=? WHERE id=?', (revision, time.time(), row['id']))
    return {**dict(db.execute('SELECT * FROM copies_proposals WHERE id=?', (ident,)).fetchone()), 'operations': len(ops)}


def words(op):
    return {'replace': 'change', 'create': 'add', 'delete': 'remove'}[op['op']] + ' ' + op['path']


def review(kernel, db, row, info):
    from .working_copies import store
    proposal = info['proposal'] if info['proposal'] and info['proposal']['state'] == 'READY' else None
    base = load(kernel, row['base'])['files']
    if proposal:ops = load(kernel, proposal['sha'])['ops']
    else:
        work = files_service.root(kernel) / row['work']
        ops = operations(base, now_digests(work, base)) if work.is_dir() else []
    files = []
    for op in ops[:40]:
        entry = {'op': op['op'], 'path': op['path'], 'words': words(op)}
        if op['op'] == 'replace' and len(files) < 40:
            before = store(kernel) / op['before']
            after = store(kernel) / op['after'] if proposal else files_service.root(kernel) / row['work'] / op['path']
            try:
                diff = files_service.compare_paths(before, after, 'before', 'after', name=Path(op['path']).name)
                entry.update({k: diff.get(k) for k in ('lines', 'added', 'removed', 'cut', 'kind')})
            except Exception as exc:entry['note'] = 'No comparison: ' + str(exc)[:120]
        files.append(entry)
    return {'kind': 'folder', 'before': info['source_words'] + ' (as the work began)',
            'after': ('revision %d, frozen for review' % proposal['revision']) if proposal else 'the working copy as it is now (not yet frozen)',
            'operations': files, 'more': max(0, len(ops) - 40), 'frozen': bool(proposal), 'copy': info,
            'skipped': load(kernel, row['base']).get('skipped', [])[:20]}


def create_file(db, journal, root, rel, data, mode, copy, proposal):
    """A new file in the original folder: never over an existing one; its folders are made inside the original folder only."""
    target = root / rel;after = hashlib.sha256(data).hexdigest()
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    if Path(os.path.realpath(parent)) != parent or (parent != root and root not in parent.parents):raise ValueError('COPIES_DESTINATION_MOVED: ' + rel)
    db.execute("INSERT INTO copies_journal VALUES(?,?,?,?,?,?,?,?,'INTENT',?,NULL,NULL)", (journal, copy, proposal, 'create', str(target), '', after, '', time.time()))
    db.commit()
    from .working_copies import checkpoint
    checkpoint('INTENT')
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0), (mode or 0o644) & 0o777)
    try:
        view = memoryview(data)
        while view:view = view[os.write(fd, view):]
        os.fsync(fd)
    finally:os.close(fd)
    sync(parent)
    db.execute("UPDATE copies_journal SET stage='DONE', finished=?, outcome='Created' WHERE id=?", (time.time(), journal));db.commit()


def delete_file(db, journal, root, rel, expected, copy, proposal):
    from .working_copies import sha_of
    target = root / rel
    if target.is_symlink() or not target.is_file() or sha_of(target) != expected:raise ValueError('COPIES_ORIGINAL_CHANGED: ' + rel + ' changed outside Graphite')
    db.execute("INSERT INTO copies_journal VALUES(?,?,?,?,?,?,?,?,'INTENT',?,NULL,NULL)", (journal, copy, proposal, 'delete', str(target), expected, '', '', time.time()))
    db.commit()
    from .working_copies import checkpoint
    checkpoint('INTENT')
    os.unlink(target);sync(target.parent)  # its bytes stay kept as the protected object `expected`
    db.execute("UPDATE copies_journal SET stage='DONE', finished=?, outcome='Removed (its bytes are kept)' WHERE id=?", (time.time(), journal));db.commit()


def sync(folder):
    try:
        fd = os.open(folder, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:os.fsync(fd)
        finally:os.close(fd)
    except OSError:pass


def holds(path, sha):
    """Does path hold exactly sha ('' = absent)?"""
    from .working_copies import sha_of
    if not sha:return not path.exists() and not path.is_symlink()
    return path.is_file() and not path.is_symlink() and sha_of(path) == sha


def run_ops(kernel, db, row, ops, proposal_id, kind='update'):
    """Apply operations to the original folder. Files already holding their result are recognised (a resumed update);
    any file that holds neither its before nor its after stops everything before a single change is made."""
    from .working_copies import object_bytes, replace_original
    root = Path(row['source'])
    if Path(os.path.realpath(root)) != root:raise ValueError('COPIES_DESTINATION_MOVED: the folder is now reached through a link')
    todo, changed = [], []
    for op in ops:
        target = root / op['path']
        if holds(target, op['after']):continue  # done before (resume)
        if not holds(target, op['before']):changed.append(op['path'])
        else:todo.append(op)
    if changed:raise ValueError('COPIES_ORIGINAL_CHANGED: changed outside Graphite since the work began: ' + ', '.join(changed[:8]))
    done = 0
    for op in todo:
        journal = uuid.uuid4().hex
        if op['op'] == 'replace':
            replace_original(kernel, db, journal, root / op['path'], op['before'], object_bytes(kernel, op['after']), op.get('mode'), row['id'], proposal_id, kind)
        elif op['op'] == 'create':create_file(db, journal, root, op['path'], object_bytes(kernel, op['after']), op.get('mode'), row['id'], proposal_id)
        else:delete_file(db, journal, root, op['path'], op['before'], row['id'], proposal_id)
        done += 1
    return done, len(ops) - len(todo)


def after_files(kernel, base_files, ops, root):
    files = {k: dict(v) for k, v in base_files.items()}
    for op in ops:
        if op['op'] == 'delete':files.pop(op['path'], None);continue
        info = os.lstat(root / op['path'])
        files[op['path']] = {'sha': op['after'], 'size': info.st_size, 'mtime': info.st_mtime_ns, 'mode': stat.S_IMODE(info.st_mode)}
    return files


def apply(kernel, db, row, proposal):
    manifest = load(kernel, proposal['sha']);ops = manifest['ops']
    if manifest['base'] != row['base']:raise ValueError('COPIES_PROPOSAL_STALE: the original moved on since this was proposed; review again')
    base_files = load(kernel, row['base'])['files'];source = Path(row['source'])
    if not source.is_dir():raise ValueError('COPIES_ORIGINAL_MISSING: the original folder is no longer there')
    finished = {o['path']: o['after'] for o in ops}
    now = now_digests(source, base_files);was = {k: v['sha'] for k, v in base_files.items()}
    moved = [rel for rel in sorted(set(now) | set(was)) if now.get(rel) != was.get(rel) and not (rel in finished and (now.get(rel) or '') == finished[rel])]
    if moved:raise ValueError('COPIES_ORIGINAL_CHANGED: changed outside Graphite since the work began: ' + ', '.join(moved[:8]))  # the approval binds the whole folder
    done, resumed = run_ops(kernel, db, row, ops, proposal['id'])
    base = load(kernel, row['base'])
    new = keep_manifest(kernel, {**base, 'files': after_files(kernel, base['files'], ops, Path(row['source']))})
    db.execute('UPDATE copies SET base=?, base_size=?, updated=? WHERE id=?', (new, len(base['files']), time.time(), row['id']))
    db.execute("UPDATE copies_proposals SET state='APPLIED' WHERE id=?", (proposal['id'],))
    return {'applied': proposal['revision'], 'files_changed': done, 'already_done': resumed, 'kept_before': row['base']}


def undo(kernel, db, row):
    last = db.execute("SELECT * FROM copies_proposals WHERE copy=? AND state='APPLIED' ORDER BY revision DESC LIMIT 1", (row['id'],)).fetchone()
    if last is None:raise ValueError('COPIES_NOTHING_TO_UNDO')
    manifest = load(kernel, last['sha'])
    back = [{'op': {'create': 'delete', 'delete': 'create', 'replace': 'replace'}[op['op']], 'path': op['path'], 'before': op['after'], 'after': op['before'],
             'mode': op.get('mode')} for op in manifest['ops']]
    run_ops(kernel, db, row, back, None, 'undo')
    db.execute('UPDATE copies SET base=?, updated=? WHERE id=?', (manifest['base'], time.time(), row['id']))
    db.execute("UPDATE copies_proposals SET state='UNDONE' WHERE id=?", (last['id'],))
    db.execute("UPDATE copies_proposals SET state='SUPERSEDED' WHERE copy=? AND state='READY'", (row['id'],))
    return {'undone': last['revision']}


def save_new(kernel, row, proposal, name):
    """The proposed folder, written whole beside the original under a new name. Nothing existing is touched."""
    from .working_copies import object_bytes
    manifest = load(kernel, proposal['sha']);base = load(kernel, manifest['base'])['files']
    files = {k: v['sha'] for k, v in base.items()}
    for op in manifest['ops']:
        if op['op'] == 'delete':files.pop(op['path'], None)
        else:files[op['path']] = op['after']
    source = Path(row['source']);target = source.parent / files_service.clean_name(name or source.name + ' (from Graphite)')
    try:target.mkdir(mode=0o755)
    except FileExistsError:raise ValueError('COPIES_NAME_TAKEN: a folder with that name is already there; nothing was overwritten') from None
    for rel, sha in sorted(files.items()):
        p = target / rel;p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, 'xb') as f:f.write(object_bytes(kernel, sha));f.flush();os.fsync(f.fileno())
    sync(target)
    return {'saved': str(target), 'saved_words': str(target).replace(str(Path.home()), '~', 1), 'files': len(files), 'original': 'unchanged'}
