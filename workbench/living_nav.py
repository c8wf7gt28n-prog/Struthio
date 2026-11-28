"""One navigation state (Graphite 1.0 L1): what a thing is, wherever it is shown, and where the owner has been.

The owner's paper, section 4: "The left tree and center should share a canonical object identifier, not infer their
correspondence from whatever filename happens to be displayed. Two files may share a name, and a file may be renamed or
moved while open." And section 3: "At any moment it has a focused object, a presentation depth, a navigation history".

Two things live here, neither of them Qt:

    the identity    of every object the centre and the tree can show.
                    A Kernel record keeps its own id, as the Field already names it ('office:…' a sheet, 'document:…' a
                    page or a calculation, 'claim:…' a finding, 'intake:…' an admitted source, 'goal:…', …).
                    A plain file or folder in Files gets a stable id here, 'fileid:<32 hex>', kept in the Kernel's own
                    database (table living_objects) and keyed by the device and inode it lives on, with its content digest
                    as the check:
                      - the same inode at a new path, its size and time unchanged or its digest the same: renamed or moved,
                        the same object (its earlier paths are kept, the last few);
                      - the same inode at a new path with other content: the inode was used again by another file, a new
                        object;
                      - a new inode at a known path whose old inode is gone: a program saved it by writing a new file over
                        it, the same object;
                      - a new inode whose digest is that of an object no longer found anywhere: moved across a disk, the same
                        object;
                      - anything else is a new object. Two files of the same name are two objects; a copy is a new object.
                    Graphite's own file operations (files.rename, files.move, files.trash, files.restore) tell the store at
                    once (moved()); a rename by another program is seen by the window's file watcher, which reads Files
                    again (objects.files). A file over 32 MB is checked by a sampled digest (its size, its first and its last
                    MB), said as such ('sampled'); nothing else is ever read of a file here. A digest is read at once only
                    where it decides something; the others are taken a few at a time (at most DIGEST_BUDGET bytes each
                    time Files is read, the smallest files first), 'pending' until then, the inode alone deciding meanwhile,
                    so a large Files never holds the window up the first time it is read.
    the history     Navigator: the focused object, the depth (board, work, split), the active pane, and each entry of the
                    history with the board's zoom and centre, the place in the document and how the owner got there (the tree,
                    the board, a search, the breadcrumb, opening it, a tab). Back and Forward restore an entry whole; the
                    window does the restoring (living_nav_qt).

Kernel operations (one block in engineering_kernel.py and engineering_cli.py, commented 1.0 L1):
    objects.files  {path?, depth?, limit?}  read   Files with a stable id for every file and folder, the renames seen since
                                                   the last reading; writes nothing but the identity index (no file is
                                                   touched)
    objects.get    {id? | path?}            read   one object's identity: its kind, its name and path now, its trail of folders,
                                                   whether it is still there, its earlier paths
Both are observers (activity.OBSERVER_OPERATIONS): the tree reads them each time it is drawn.

1.0 L6, the whole computer: the ids extend to any path lazily. objects.get {path} also takes a path named from / or ~
(home_reach): a file or folder outside Files is given its id when it is focused, opened or linked (that one call), never
by scanning the disk; it is kept under its whole path ('/home/…'), by the same rules (its inode, its digest), and a
reading of Files never marks it missing. The system folders (/proc, /sys, /dev, /run) are never given an id.

No floating point is used for anything that is checked: sizes and times are integers (nanoseconds), digests are hex.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import stat as statmod
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

VERSION = 'living_nav/1'
PREFIX = 'fileid:'
FULL_DIGEST = 32 * 1024 * 1024        # a file up to this size is checked by its whole SHA-256
SAMPLE = 1024 * 1024                  # a larger one by its size, its first and its last MB ('sampled')
DIGEST_BUDGET = 48 * 1024 * 1024      # bytes one reading of Files may read for digests not taken yet ('pending' until then)
PENDING = 'pending'
MOST = 4000                           # entries one reading of Files lists, at most
DEEPEST = 12                          # folders deep, at most
KEPT_NAMES = 8                        # earlier paths kept for each object
HISTORY = 100                         # entries Back can reach
DEPTHS = ('board', 'work', 'split', 'explorer')  # 1.1 E1: a folder in the Explorer is a place in the history too
WAYS = ('tree', 'board', 'search', 'breadcrumb', 'open', 'tab', 'start', 'her')     # how the owner reached a place

REL = {'type': 'string', 'maxLength': 1000}
ID = {'type': 'string', 'pattern': '^fileid:[0-9a-f]{32}$', 'maxLength': 39}
FIELDS = {
    'objects.files': ({'path': REL, 'depth': {'type': 'integer', 'minimum': 1, 'maximum': DEEPEST},
                       'limit': {'type': 'integer', 'minimum': 10, 'maximum': MOST}}, []),
    'objects.get': ({'id': ID, 'path': REL}, []),
}
SCOPES = {op: 'read' for op in FIELDS}

PRESENT, MISSING, DELETED = 'present', 'missing', 'deleted'
STATE_WORDS = {PRESENT: 'here', MISSING: 'not found where it was', DELETED: 'in DELETE'}


# ---- the store -----------------------------------------------------------------------------------------------------------
def ensure(db):
    db.execute('''CREATE TABLE IF NOT EXISTS living_objects(id TEXT PRIMARY KEY, dev INTEGER, ino INTEGER, path TEXT, kind TEXT,
                  digest TEXT, digest_kind TEXT, size INTEGER, mtime_ns INTEGER, state TEXT, names TEXT, first INTEGER, seen INTEGER)''')
    db.execute('CREATE INDEX IF NOT EXISTS living_objects_inode ON living_objects(dev, ino)')
    db.execute('CREATE INDEX IF NOT EXISTS living_objects_path ON living_objects(path)')


def _rows(db):
    db.row_factory = sqlite3.Row
    return {r['id']: dict(r) for r in db.execute('SELECT * FROM living_objects')}


def _save(db, row):
    db.execute('INSERT OR REPLACE INTO living_objects(id, dev, ino, path, kind, digest, digest_kind, size, mtime_ns, state, names, first, seen) '
               'VALUES(:id, :dev, :ino, :path, :kind, :digest, :digest_kind, :size, :mtime_ns, :state, :names, :first, :seen)', row)


def new_id():
    return PREFIX + uuid.uuid4().hex


def is_file_id(ident):
    return isinstance(ident, str) and ident.startswith(PREFIX) and len(ident) == len(PREFIX) + 32


def content_digest(path, size):
    """(hex, 'sha256') for the whole file, or (hex, 'sampled') over its size and its first and last MB when it is large."""
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        if size <= FULL_DIGEST:
            for chunk in iter(lambda: stream.read(1 << 20), b''):
                h.update(chunk)
            return h.hexdigest(), 'sha256'
        h.update(b'size:%d;' % size);h.update(stream.read(SAMPLE))
        stream.seek(max(0, size - SAMPLE));h.update(stream.read(SAMPLE))
        return h.hexdigest(), 'sampled'


def files_root(kernel, create=True):
    from . import files_service
    return files_service.root(kernel, create)


def rel_of(base, path):
    rel = Path(path).relative_to(base).as_posix()
    return '' if rel == '.' else rel


def name_of(rel, base=None):
    return PurePosixPath(rel).name if rel else (Path(base).name if base is not None else 'Files')


def parent_rel(rel):
    if not rel:return None
    parent = PurePosixPath(rel).parent.as_posix()
    return '' if parent == '.' else parent


def under(rel, folder):
    """Whether rel is folder itself or inside it ('' is the Files folder)."""
    if str(rel).startswith('/') and not str(folder).startswith('/'):return False  # 1.0 L6: a path outside Files is in no folder of it
    return folder == '' or rel == folder or rel.startswith(folder + '/')


def outside(path):
    """1.0 L6: whether a path as the store keeps it is outside Files (kept whole, from /)."""
    return str(path or '').startswith('/')


def in_delete(rel):
    from .files_service import TRASH
    if str(rel).startswith('/'):  # 1.0 L6b: in your home's Trash (freedesktop)
        from .home_trash import in_trash
        return in_trash(rel)
    return rel == TRASH or rel.startswith(TRASH + '/')


# ---- reading Files ---------------------------------------------------------------------------------------------------------
def _observe(path, st, base):
    folder = statmod.S_ISDIR(st.st_mode)
    return {'abs': str(path), 'rel': rel_of(base, path), 'dev': int(st.st_dev), 'ino': int(st.st_ino), 'kind': 'folder' if folder else 'file',
            'size': 0 if folder else int(st.st_size), 'mtime_ns': int(st.st_mtime_ns)}


def walk(base, start='', depth=DEEPEST, limit=MOST):
    """What is in Files (or one folder of it), shallow first, folders before files, by name: (observations, left out). Links,
    machine files (caches, lock files, hidden names) and DELETE's and the versions' own folders are not objects here."""
    from .files_service import TRASH, VERSIONS, machine
    base = Path(base);top = base.joinpath(*[p for p in PurePosixPath(start).parts if p not in ('', '/', '.')]) if start else base
    try:st = os.lstat(top)
    except OSError:return [], 0
    seen = [_observe(top, st, base)];left = 0
    if not statmod.S_ISDIR(st.st_mode):return seen, 0
    level = [(top, 0)]
    while level:
        following = []
        for folder, d in level:
            try:entries = list(os.scandir(folder))
            except OSError:continue
            rows = []
            for entry in entries:
                path = Path(entry.path)
                if folder == base and entry.name in (TRASH, VERSIONS):continue
                if entry.is_symlink() or machine(path):continue
                try:est = entry.stat(follow_symlinks=False)
                except OSError:continue
                if not (statmod.S_ISDIR(est.st_mode) or statmod.S_ISREG(est.st_mode)):continue
                rows.append((not statmod.S_ISDIR(est.st_mode), entry.name.casefold(), path, est))
            for _, _, path, est in sorted(rows, key=lambda r: (r[0], r[1])):
                if len(seen) >= limit:left += 1;continue
                seen.append(_observe(path, est, base))
                if statmod.S_ISDIR(est.st_mode):
                    if d + 1 < depth:following.append((path, d + 1))
        level = following
    return seen, left


def _earlier(row, old_path):
    """The object's earlier paths with old_path added (the path it is leaving), the last KEPT_NAMES."""
    names = json.loads(row.get('names') or '[]')
    if old_path is not None and (not names or names[-1] != old_path):names.append(old_path)
    return json.dumps(names[-KEPT_NAMES:], ensure_ascii=False)


def resolve(db, observed, base, scope='', now=None, full=True, budget=None):
    """Give every observation its object's id (the rules in this module's words). Returns (entries, moved): entries in the
    order observed, each the observation with its 'id', 'state' and 'was' (its path before, when it moved since it was last
    seen); moved [(id, was, now)]. With full, objects of the scope that were not observed and are not where they were are
    marked missing (kept: one that comes back, by inode or by digest, keeps its id).

    A digest is read only where it decides something (an inode at a new place whose size or time changed; a new inode of the
    size of an object no longer found) and, for the rest, a few at a time: each reading reads at most `budget` bytes of the
    digests still to be taken (DIGEST_BUDGET), so a large Files never holds the window up the first time it is read. An
    object whose digest is not taken yet is 'pending': its inode alone decides, as it does for every folder."""
    now = int(now if now is not None else time.time());budget = [DIGEST_BUDGET if budget is None else budget]
    rows = _rows(db)
    by_inode = {};by_path = {}
    for row in rows.values():
        by_inode.setdefault((row['dev'], row['ino']), []).append(row);by_path.setdefault(row['path'], []).append(row['id'])
    claimed = {};results = [None] * len(observed);moved = []

    def take(index, row, obs, digest=None):
        was = row['path'] if row['path'] != obs['rel'] else None
        if obs['kind'] == 'file' and digest is None and row['digest'] and (row['size'], row['mtime_ns']) != (obs['size'], obs['mtime_ns']):
            digest = content_digest(obs['abs'], obs['size'])
        updated = dict(row, dev=obs['dev'], ino=obs['ino'], path=obs['rel'], size=obs['size'], mtime_ns=obs['mtime_ns'],
                       state=PRESENT, names=_earlier(row, was))
        if digest is not None:updated['digest'], updated['digest_kind'] = digest
        elif obs['kind'] == 'file' and (row['size'], row['mtime_ns']) != (obs['size'], obs['mtime_ns']):
            updated['digest'], updated['digest_kind'] = '', PENDING      # changed and not read yet: taken later, a few at a time
        if updated != row:      # nothing is written for an object found as it was (the tree reads Files often)
            updated['seen'] = now;_save(db, updated)
        claimed[row['id']] = index;rows[row['id']] = updated
        if was is not None:moved.append((row['id'], was, obs['rel']))
        results[index] = dict(obs, id=row['id'], state=PRESENT, was=was)

    # pass 1: the same inode
    rest = []
    for index, obs in enumerate(observed):
        found = None
        for row in by_inode.get((obs['dev'], obs['ino']), ()):
            if row['id'] in claimed or row['kind'] != obs['kind']:continue
            if row['path'] == obs['rel'] or obs['kind'] == 'folder':found = (row, None);break
            if (row['size'], row['mtime_ns']) == (obs['size'], obs['mtime_ns']):found = (row, None);break      # renamed, untouched
            if not row['digest']:found = (row, None);break        # no digest yet to check it by: the inode decides
            digest = content_digest(obs['abs'], obs['size'])
            if digest[0] == row['digest']:found = (row, digest);break
            # same inode, other content, another place: the inode was used again; not this object
        if found:take(index, found[0], obs, found[1])
        else:rest.append(index)
    # pass 2: a new inode at a known place (an editor's save), or the content of an object no longer found (a move across disks)
    observed_paths = {obs['rel'] for obs in observed}
    gone = {}
    for row in rows.values():
        if row['id'] not in claimed and row['kind'] == 'file' and row['digest'] and row['path'] not in observed_paths:
            gone.setdefault(row['size'], []).append(row)
    for index in rest:
        obs = observed[index];row = None;digest = None
        for ident in by_path.get(obs['rel'], ()):          # an object found by its inode elsewhere was claimed in pass 1
            candidate = rows[ident]
            if candidate['id'] not in claimed and candidate['kind'] == obs['kind'] and candidate['path'] == obs['rel']:row = candidate;break
        if row is None and obs['kind'] == 'file' and gone.get(obs['size']):       # a move keeps the size: only then is it read
            digest = content_digest(obs['abs'], obs['size'])
            same = [c for c in gone[obs['size']] if c['id'] not in claimed and c['digest'] == digest[0] and not _exists(base, c)]
            if same:row = max(same, key=lambda c: (c['seen'] or 0, c['id']))
        if row is not None:
            take(index, row, obs, digest);continue
        ident = new_id()
        made = {'id': ident, 'dev': obs['dev'], 'ino': obs['ino'], 'path': obs['rel'], 'kind': obs['kind'],
                'digest': digest[0] if digest else '', 'digest_kind': digest[1] if digest else (PENDING if obs['kind'] == 'file' else ''),
                'size': obs['size'], 'mtime_ns': obs['mtime_ns'], 'state': PRESENT, 'names': '[]', 'first': now, 'seen': now}
        _save(db, made);rows[ident] = made;claimed[ident] = index
        results[index] = dict(obs, id=ident, state=PRESENT, was=None)
    # the digests still to be taken, a few at a time (the smallest first: many are done for little reading)
    for index in sorted((i for i in claimed.values() if observed[i]['kind'] == 'file'), key=lambda i: observed[i]['size']):
        row = rows[results[index]['id']]
        if row['digest_kind'] != PENDING:continue
        cost = 2 * SAMPLE if row['size'] > FULL_DIGEST else row['size']
        if cost > budget[0]:break
        budget[0] -= cost
        try:digest = content_digest(observed[index]['abs'], observed[index]['size'])
        except OSError:continue
        row = dict(row, digest=digest[0], digest_kind=digest[1]);rows[row['id']] = row;_save(db, row)
    if full:
        for row in rows.values():
            if row['id'] in claimed or row['state'] != PRESENT or outside(row['path']) or not under(row['path'], scope) or in_delete(row['path']):continue  # 1.0 L6
            _save(db, dict(row, state=MISSING))
    return results, moved


def _exists(base, row):
    """Whether something with this row's inode is still at its path (used only for objects the reading did not see)."""
    try:st = os.lstat(Path(base) / row['path'])
    except OSError:return False
    return (int(st.st_dev), int(st.st_ino)) == (row['dev'], row['ino'])


def files(kernel, path='', depth=DEEPEST, limit=MOST):
    """objects.files: Files (or one folder of it) with an id for every file and folder."""
    base = files_root(kernel)
    observed, left = walk(base, path or '', depth, limit)
    if not observed:raise ValueError('OBJECTS_NOT_FOUND: ' + str(path or '')[:200])
    with kernel.db() as db:
        ensure(db);entries, moved = resolve(db, observed, base, scope=path or '', full=not left and depth >= DEEPEST)
    ids = {e['rel']: e['id'] for e in entries}
    rows = [{'id': e['id'], 'kind': e['kind'], 'name': name_of(e['rel'], base), 'path': e['rel'], 'parent': ids.get(parent_rel(e['rel'])),
             'size': e['size'], 'modified_ns': e['mtime_ns'], 'state': e['state'], 'was': e['was']} for e in entries]
    return {'schema': 'living.files/1', 'root': str(base), 'path': path or '', 'entries': rows, 'partial': bool(left), 'left_out': left,
            'moved': [{'id': i, 'was': w, 'now': n} for i, w, n in moved]}


def get(kernel, ident=None, path=None):
    """objects.get: one object by its id, or the object at a path of Files (given an id there if it has none yet)."""
    base = files_root(kernel)
    if ident is None and path is None:raise ValueError('OBJECTS_ASK: give an id or a path')
    if path is not None and str(path).startswith(('/', '~')):      # 1.0 L6: anywhere on this computer
        found = elsewhere(kernel, base, path)
        if found is not None:return found
        from . import home_reach
        path = home_reach.real(home_reach.expand(path)).relative_to(Path(base).resolve()).as_posix()      # inside Files after all
    with kernel.db() as db:
        ensure(db)
        if path is not None:
            from .files_service import resolve as inside
            target = inside(kernel, path)
            rel = rel_of(base, target);chain = [rel]
            while chain[-1]:chain.append(parent_rel(chain[-1]))
            observed = [_observe(base / p if p else base, os.lstat(base / p if p else base), base) for p in reversed(chain)]
            resolve(db, observed, base, full=False)
            row = next(r for r in _rows(db).values() if r['path'] == rel and r['state'] == PRESENT)
        else:
            row = _rows(db).get(ident)
            if row is None:raise ValueError('OBJECTS_UNKNOWN: no object has this id here')
        state = row['state']
        if state == PRESENT and not _exists(base, row):state = MISSING
        if outside(row['path']):return described(row, base, state)      # 1.0 L6: kept outside Files: its folders by name
        rows = _rows(db)
    by_path = {r['path']: r for r in rows.values() if r['state'] == PRESENT}
    trail = [];folder = parent_rel(row['path'])
    while folder is not None:
        here = by_path.get(folder)
        trail.insert(0, {'id': here['id'] if here else None, 'name': name_of(folder, base), 'path': folder})
        folder = parent_rel(folder)
    return {'schema': 'living.object/1', 'id': row['id'], 'kind': row['kind'], 'name': name_of(row['path'], base), 'path': row['path'],
            'state': state, 'state_words': STATE_WORDS.get(state, state), 'trail': trail, 'size': row['size'],
            'digest': row['digest'], 'digest_kind': row['digest_kind'], 'earlier': json.loads(row['names'] or '[]'), 'root': str(base)}


def key_of(base, path):
    """1.0 L6: how the store keeps a path: inside Files, its path there; elsewhere, its whole path (links followed)."""
    from . import home_reach
    actual = home_reach.real(Path(path))
    try:return rel_of(Path(base).resolve(), actual)
    except ValueError:
        return str(actual)


def elsewhere(kernel, base, path):
    """objects.get for a path named from / or ~ outside Files: its object, given an id now if it has none (this one file or
    folder, never what is around it); None when the path is inside Files (the caller reads it as Files)."""
    from . import home_reach
    named = home_reach.expand(path)
    if named is None:raise ValueError('OBJECTS_PATH: a path with no ".."')
    refusal = home_reach.read_refusal(named)
    if refusal:raise ValueError('OBJECTS_SYSTEM: ' + refusal)
    key = key_of(base, named)
    if not outside(key):return None
    try:st = os.lstat(key)
    except OSError:
        raise ValueError('OBJECTS_NOT_FOUND: ' + home_reach.tilde(named)[:200]) from None
    if not (statmod.S_ISDIR(st.st_mode) or statmod.S_ISREG(st.st_mode)):raise ValueError('OBJECTS_KIND: only a file or a folder has an id here')
    obs = dict(_observe(Path(key), st, Path(key)), rel=key)
    with kernel.db() as db:
        ensure(db)
        entries, _ = resolve(db, [obs], base, full=False)
        row = _rows(db).get(entries[0]['id'])
    return described(row, base, PRESENT if row['state'] == PRESENT else row['state'])


def described(row, base, state):
    """objects.get's answer for an object kept outside Files (1.0 L6): its trail is its folders, by name."""
    from . import home_reach
    folders = [str(p) for p in reversed(PurePosixPath(row['path']).parents)]
    trail = [{'id': None, 'name': home_reach.tilde(f) if f == str(home_reach.home()) else (PurePosixPath(f).name or 'This computer'), 'path': f}
             for f in folders]
    return {'schema': 'living.object/1', 'id': row['id'], 'kind': row['kind'], 'name': PurePosixPath(row['path']).name or '/', 'path': row['path'],
            'state': state, 'state_words': STATE_WORDS.get(state, state), 'trail': trail, 'size': row['size'],
            'digest': row['digest'], 'digest_kind': row['digest_kind'], 'earlier': json.loads(row['names'] or '[]'), 'root': str(base),
            'where': home_reach.role_words(row['path']), 'place': home_reach.tilde(row['path'])}


def known_outside(kernel):
    """1.0 L6: {whole path: id} of the objects outside Files that have an id and are where they were (the tree names its rows
    by them; nothing is made here)."""
    try:
        with kernel.db() as db:
            ensure(db)
            return {r[0]: r[1] for r in db.execute("SELECT path, id FROM living_objects WHERE state=? AND path LIKE '/%'", (PRESENT,))}
    except Exception:  # noqa: BLE001 - no store yet: no ids
        return {}


def entry_outside(found):
    """1.0 L6: an object outside Files (objects.get's answer) as an entry of a Files reading, so the board and the tree
    can hold it beside Files' own."""
    return {'id': found['id'], 'kind': found['kind'], 'name': found['name'], 'path': found['path'], 'parent': None, 'size': found.get('size') or 0,
            'modified_ns': 0, 'state': found['state'], 'was': None, 'outside': True}


def moved(kernel, old, new):
    """Graphite's own file operation moved or renamed something (files_service): its object, and everything inside it, keeps its
    id at the new place at once, without waiting for the next reading. Into DELETE it is 'deleted'; back out of it, present."""
    try:
        base = files_root(kernel, create=False)
        was = _kept_as(base, old);now = _kept_as(base, new)  # 1.0 L6: inside Files or elsewhere
    except (ValueError, OSError):
        return 0
    count = 0
    with kernel.db() as db:
        ensure(db)
        for row in _rows(db).values():
            if not under(row['path'], was) or was == '' or row['state'] == MISSING:continue
            path = now + row['path'][len(was):]
            state = DELETED if in_delete(path) else PRESENT
            _save(db, dict(row, path=path, state=state, names=_earlier(row, row['path'])));count += 1
    return count


def _kept_as(base, path):
    """1.0 L6: a path Graphite just moved, as the store keeps it (inside Files: its path there; elsewhere: whole)."""
    try:return rel_of(base, path)
    except ValueError:
        try:return rel_of(Path(base).resolve(), Path(path))
        except ValueError:
            return str(Path(path))


def dispatch(kernel, op, args, principal):
    if op == 'objects.files':return files(kernel, args.get('path', ''), int(args.get('depth', DEEPEST)), int(args.get('limit', MOST)))
    if op == 'objects.get':return get(kernel, args.get('id'), args.get('path'))
    raise ValueError('Unknown object operation')


# ---- the navigation state --------------------------------------------------------------------------------------------------
@dataclass
class Entry:
    """One place in the history: what was in focus, at which depth and in which pane, how the board was seen (zoom and
    centre), where the document was (scroll, cursor) and how the owner got there."""
    focus: str = ''
    title: str = ''
    depth: str = 'board'
    pane: str = 'main'
    via: str = 'start'
    board: dict = field(default_factory=dict)       # {'zoom', 'x', 'y', 'face'}: the board's zoom and the corner of what it showed
    doc: dict = field(default_factory=dict)         # {'v', 'h', 'cursor', 'own'}: the place in the document at work depth
    tab: object = None                              # the window's tab at work depth (a weak reference, set by the window)
    node: str = ''                                  # the tree's row for it, when the tree has one


class Navigator:
    """The focused object, the depth, the active pane and the history. Back and Forward move along the entries; the caller
    keeps the current entry up to date (update) before it leaves it, so Back finds it as it was left."""

    def __init__(self, most=HISTORY):
        self.entries = [];self.index = -1;self.most = most

    @property
    def current(self):
        return self.entries[self.index] if 0 <= self.index < len(self.entries) else None

    @property
    def focus(self):
        return self.current.focus if self.current else ''

    @property
    def depth(self):
        return self.current.depth if self.current else 'board'

    @property
    def pane(self):
        return self.current.pane if self.current else 'main'

    def go(self, focus, via, depth='board', pane='main', title='', node='', board=None, doc=None, tab=None):
        """A new place: the forward entries are dropped, the board's state carries forward unless given. The same focus at the
        same depth and pane is not a new place (its title and row are brought up to date)."""
        if depth not in DEPTHS:raise ValueError('NAV_DEPTH: board, work or split')
        current = self.current
        if current is not None and (current.focus, current.depth, current.pane) == (focus, depth, pane) and (depth == 'board' or tab is None or current.tab is tab):
            if title:current.title = title
            if node:current.node = node
            if tab is not None:current.tab = tab
            return current
        del self.entries[self.index + 1:]
        entry = Entry(focus, title, depth, pane, via if via in WAYS else 'tab', dict(board if board is not None else (current.board if current else {})),
                      dict(doc or {}), tab, node)
        self.entries.append(entry)
        if len(self.entries) > self.most:del self.entries[:len(self.entries) - self.most]
        self.index = len(self.entries) - 1
        return entry

    def update(self, **values):
        current = self.current
        if current is None:return None
        for key, value in values.items():
            if value is not None:setattr(current, key, value)
        return current

    def can_back(self):
        return self.index > 0

    def can_forward(self):
        return 0 <= self.index < len(self.entries) - 1

    def back(self):
        if not self.can_back():return None
        self.index -= 1;return self.current

    def forward(self):
        if not self.can_forward():return None
        self.index += 1;return self.current

    def peek(self, step):
        at = self.index + step
        return self.entries[at] if 0 <= at < len(self.entries) else None

    def renamed(self, ident, title):
        """An object's name changed (a rename seen on disk): every entry that holds it says the new name."""
        for entry in self.entries:
            if entry.focus == ident:entry.title = title
