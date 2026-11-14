"""Working copies: work on a copy of any file in your home folder; the original changes only when you say so.

From the File-Management Plan (L&S-FS-PLAN-001), first slice:

  - Copy in, never move in. Starting work captures the file as it is (a protected snapshot) and puts an ordinary working
    copy in Files › Working copies. The original stays where it was, still yours to open and edit with any program.
  - The working copy can be edited freely, by you or (if you assign it) by Slate. Saving it never touches the original.
  - A proposal freezes the working copy as it is now (a protected object with its digest). Review compares exactly that.
  - Update original applies exactly one frozen proposal, and only if the original is still the file the work began from.
    If it changed outside Ledger, the update is refused, and you can compare with the changed original or save as a new file.
  - The update is journaled: intent, a private temporary file beside the original, flushed, then one rename, then the folder
    is flushed. The version before stays as a protected object. After a crash, recovery compares what is on disk with the
    journal and finishes, cancels, or says "recovery required"; it never overwrites a file that matches neither.
  - Undo is another update, refused if the original changed since.
  - Nothing is deleted: discarding a draft moves it to Trash; snapshots, proposals and the journal are kept.

Honest limits, as the plan requires: one file at a time; a regular local file; the check-then-rename is not a lock against a
program writing the original at the same instant (close the other program for the update). A protected object is protected
from Slate and his tools, not from the computer's owner.
"""
from __future__ import annotations
import contextlib
import hashlib
import os
import sqlite3
import stat
import time
import uuid
from pathlib import Path

from . import files_service

WORKING = 'Working copies'
MAX_BYTES = 64 * 1024 * 1024
ID = files_service.ID
FIELDS = {
    'copies.list': ({}, []),
    'copies.get': ({'id': ID}, ['id']),
    'copies.review': ({'id': ID}, ['id']),
    'copies.start': ({'source': {'type': 'string', 'minLength': 1, 'maxLength': 4096}, 'for_slate': {'type': 'boolean'}}, ['source']),
    'copies.propose': ({'id': ID, 'note': {'type': 'string', 'maxLength': 400}}, ['id']),
    'copies.apply': ({'id': ID, 'proposal': ID}, ['id', 'proposal']),
    'copies.save_new': ({'id': ID, 'proposal': ID, 'name': files_service.NAME}, ['id', 'proposal']),
    'copies.refresh': ({'id': ID}, ['id']),
    'copies.discard': ({'id': ID}, ['id']),
    'copies.undo': ({'id': ID}, ['id']),
    'copies.recover': ({'close': ID}, []),
    'copies.merge': ({'id': ID}, ['id']),
}
SCOPES = {op: 'read' if op in ('copies.list', 'copies.get', 'copies.review') else 'execute' if op in ('copies.propose', 'copies.discard') else 'approve'
          for op in FIELDS}
FINAL = ('DONE', 'CANCELLED', 'CLOSED')
CRASH_AT = None  # tests only: the stage at which a simulated controller crash stops an update


class Crash(Exception):
    """A simulated crash, for the recovery tests."""


def checkpoint(stage):
    if CRASH_AT == stage:raise Crash(stage)


# -- storage ---------------------------------------------------------------------------

@contextlib.contextmanager
def opened(kernel):
    with kernel.db() as db:
        db.row_factory = sqlite3.Row
        db.execute('''CREATE TABLE IF NOT EXISTS copies(id TEXT PRIMARY KEY, owner TEXT, source TEXT, base TEXT, base_size INTEGER,
                      base_mtime INTEGER, base_mode INTEGER, work TEXT, for_slate INTEGER, state TEXT, revision INTEGER, created REAL, updated REAL)''')
        db.execute('''CREATE TABLE IF NOT EXISTS copies_proposals(id TEXT PRIMARY KEY, copy TEXT, revision INTEGER, sha TEXT, base TEXT,
                      note TEXT, made_by TEXT, at REAL, state TEXT)''')
        if 'kind' not in [r[1] for r in db.execute('PRAGMA table_info(copies)')]:db.execute("ALTER TABLE copies ADD COLUMN kind TEXT DEFAULT 'file'")
        db.execute('''CREATE TABLE IF NOT EXISTS copies_journal(id TEXT PRIMARY KEY, copy TEXT, proposal TEXT, kind TEXT, target TEXT,
                      before TEXT, after TEXT, temp TEXT, stage TEXT, at REAL, finished REAL, outcome TEXT)''')
        yield db


def store(kernel):
    folder = Path(kernel.dbpath).parent / 'copies' / 'objects'
    folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    return folder


def keep_object(kernel, data):
    sha = hashlib.sha256(data).hexdigest();path = store(kernel) / sha
    if not path.is_file():
        temporary = path.with_name('.' + sha + '.part')
        with open(temporary, 'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.chmod(temporary, 0o400);os.replace(temporary, path)
    return sha


def object_bytes(kernel, sha):
    data = (store(kernel) / sha).read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:raise ValueError('COPIES_OBJECT_DAMAGED: a kept snapshot no longer matches its digest')
    return data


def sha_of(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda:f.read(1 << 20), b''):h.update(block)
    return h.hexdigest()


# -- the original ------------------------------------------------------------------------

def allowed_place(kernel, text):
    """A place in your home folder, named by its full path: not hidden, not through a link, not inside Ledger's own folders."""
    path = Path(os.path.expanduser(text))
    if not path.is_absolute():raise ValueError('COPIES_SOURCE_NOT_ABSOLUTE: give the full path of the file')
    path = Path(os.path.normpath(path));home = Path.home().resolve()
    if path == home:raise ValueError('COPIES_SOURCE_IS_HOME: choose a project folder or a file, not the whole home folder')
    if home not in path.parents:raise ValueError('COPIES_SOURCE_OUTSIDE_HOME: working copies start from files in your home folder')
    if any(part.startswith('.') for part in path.relative_to(home).parts):raise ValueError('COPIES_SOURCE_HIDDEN: hidden files and folders are not copied')
    if Path(os.path.realpath(path)) != path:raise ValueError('COPIES_SOURCE_LINK: the path goes through a link; open the real file')
    for inside in (files_service.root(kernel, create=False), Path(kernel.dbpath).parent, Path(kernel.root)):
        inside = Path(os.path.realpath(inside))
        if path == inside or inside in path.parents or path in inside.parents:raise ValueError('COPIES_SOURCE_INSIDE_LEDGER: this is already Graphite\'s, or holds it; use Files and its versions')
    return path


def allowed_source(kernel, text):
    """An ordinary file in a place allowed_place accepts."""
    path = allowed_place(kernel, text)
    try:info = os.lstat(path)
    except FileNotFoundError:raise ValueError('COPIES_SOURCE_NOT_FOUND: ' + str(path)[:300]) from None
    if not stat.S_ISREG(info.st_mode):raise ValueError('COPIES_SOURCE_NOT_A_FILE: only ordinary files (not folders, devices or links)')
    if info.st_size > MAX_BYTES:raise ValueError('COPIES_SOURCE_TOO_LARGE: up to 64 MB for now')
    return path


def capture(path):
    """The file's bytes, read through a descriptor that does not follow links, checked unchanged while read (three tries)."""
    for _ in range(3):
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0))
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):raise ValueError('COPIES_SOURCE_NOT_A_FILE')
            chunks = []
            while True:
                block = os.read(fd, 1 << 20)
                if not block:break
                chunks.append(block)
                if sum(map(len, chunks)) > MAX_BYTES:raise ValueError('COPIES_SOURCE_TOO_LARGE: up to 64 MB for now')
            after = os.fstat(fd)
        finally:os.close(fd)
        if (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns) == (os.stat(path).st_size, os.stat(path).st_mtime_ns):
            return b''.join(chunks), after
        time.sleep(0.2)
    raise ValueError('COPIES_SOURCE_CHANGING: the file kept changing while it was copied; close the program writing it and try again')


def original_state(row):
    """'same', 'changed' or 'missing': quick by size and time, then by digest when those moved."""
    try:info = os.lstat(row['source'])
    except FileNotFoundError:return 'missing'
    if not stat.S_ISREG(info.st_mode):return 'changed'
    if (info.st_size, info.st_mtime_ns) == (row['base_size'], row['base_mtime']):return 'same'
    return 'same' if sha_of(row['source']) == row['base'] else 'changed'


# -- the careful update ------------------------------------------------------------------

def replace_original(kernel, db, journal, target, expected, data, mode, copy=None, proposal=None, kind='update'):
    """Replace target with data only if it still holds `expected`. Journaled stage by stage; see the module notes."""
    target = Path(target);after = hashlib.sha256(data).hexdigest()
    flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_CLOEXEC', 0)
    if Path(os.path.realpath(target.parent)) != target.parent:raise ValueError('COPIES_DESTINATION_MOVED: the folder is now reached through a link')
    folder = os.open(target.parent, flags)
    try:
        def current():
            try:info = os.stat(target.name, dir_fd=folder, follow_symlinks=False)
            except FileNotFoundError:raise ValueError('COPIES_ORIGINAL_MISSING: the original is no longer there') from None
            if not stat.S_ISREG(info.st_mode):raise ValueError('COPIES_ORIGINAL_CHANGED: the original is no longer an ordinary file')
            fd = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=folder)
            try:
                h = hashlib.sha256()
                for block in iter(lambda:os.read(fd, 1 << 20), b''):h.update(block)
            finally:os.close(fd)
            return h.hexdigest(), info
        now, info = current()
        if now != expected:raise ValueError('COPIES_ORIGINAL_CHANGED: the original changed outside Graphite since the work began; compare again or save as a new file')
        temp = '.%s.ledger-%s.tmp' % (target.name[:120], journal[:12])
        db.execute("INSERT INTO copies_journal VALUES(?,?,?,?,?,?,?,?,'INTENT',?,NULL,NULL)",
                   (journal, copy, proposal, kind, str(target), expected, after, temp, time.time()))
        db.commit();checkpoint('INTENT')
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0), 0o600, dir_fd=folder)
        try:
            view = memoryview(data)
            while view:view = view[os.write(fd, view):]
            os.fchmod(fd, stat.S_IMODE(mode if mode is not None else info.st_mode) & 0o777)  # never set-id bits
            os.fsync(fd)
        finally:os.close(fd)
        db.execute("UPDATE copies_journal SET stage='PREPARED' WHERE id=?", (journal,));db.commit();checkpoint('PREPARED')
        if current()[0] != expected:  # looked at once more, immediately before the one rename
            os.unlink(temp, dir_fd=folder)
            db.execute("UPDATE copies_journal SET stage='CANCELLED', finished=?, outcome='Original changed during the update; nothing replaced' WHERE id=?", (time.time(), journal))
            db.commit();raise ValueError('COPIES_ORIGINAL_CHANGED: the original changed during the update; nothing was replaced')
        os.replace(temp, target.name, src_dir_fd=folder, dst_dir_fd=folder)
        db.execute("UPDATE copies_journal SET stage='REPLACED' WHERE id=?", (journal,));db.commit();checkpoint('REPLACED')
        os.fsync(folder)
        if current()[0] != after:
            db.execute("UPDATE copies_journal SET stage='RECOVERY', outcome='After the rename the original does not hold the approved bytes' WHERE id=?", (journal,))
            db.commit();raise ValueError('COPIES_RECOVERY_REQUIRED: the result could not be confirmed')
        db.execute("UPDATE copies_journal SET stage='DONE', finished=?, outcome='Applied' WHERE id=?", (time.time(), journal));db.commit()
        return after
    finally:os.close(folder)


def recover(kernel, db, close=None):
    """Reconcile every update that did not finish. Idempotent: running it twice changes nothing more."""
    if close:
        db.execute("UPDATE copies_journal SET stage='CLOSED', finished=?, outcome=coalesce(outcome,'')||' · closed by the owner after looking' "
                   "WHERE id=? AND stage='RECOVERY'", (time.time(), close))
    found = []
    for row in db.execute("SELECT * FROM copies_journal WHERE stage NOT IN ('DONE','CANCELLED','CLOSED')").fetchall():
        target = Path(row['target']);temp = target.parent / row['temp'] if row['temp'] else None
        try:now = sha_of(target) if target.is_file() and not target.is_symlink() else None
        except OSError:now = None
        want_after, want_before = row['after'] or None, row['before'] or None  # '' is "absent": a create's before, a delete's after
        if now == want_after:
            stage, outcome = 'DONE', 'Applied (finished by recovery)'
            with contextlib.suppress(OSError):
                fd = os.open(target.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0));os.fsync(fd);os.close(fd)
            settle(db, row)
        elif now == want_before:
            stage, outcome = 'CANCELLED', 'Not applied: the original is unchanged'
        else:
            stage, outcome = 'RECOVERY', ('The original is missing' if now is None else 'The original matches neither the version before nor the approved one') + \
                '; nothing was overwritten. Look at it, then close this.'
        if stage != 'RECOVERY' and temp is not None and temp.is_file() and not temp.is_symlink():
            try:ours = sha_of(temp) == row['after']
            except OSError:ours = False
            if ours:temp.unlink()  # only our own verified temporary file is removed
        db.execute('UPDATE copies_journal SET stage=?, outcome=?, finished=? WHERE id=?', (stage, outcome, None if stage == 'RECOVERY' else time.time(), row['id']))
        found.append({'id': row['id'], 'target': row['target'], 'stage': stage, 'outcome': outcome})
    return found


def settle(db, row):
    """After an update is known to have happened: the copy's base is the new original, its proposal is applied."""
    if not row['copy']:return
    copy = db.execute('SELECT * FROM copies WHERE id=?', (row['copy'],)).fetchone()
    if copy is None or (copy['kind'] or 'file') == 'folder':return  # a folder settles as a whole, when its proposal completes
    info = os.stat(copy['source'])
    db.execute('UPDATE copies SET base=?, base_size=?, base_mtime=?, base_mode=?, updated=? WHERE id=?',
               (row['after'], info.st_size, info.st_mtime_ns, info.st_mode, time.time(), copy['id']))
    if row['proposal']:db.execute("UPDATE copies_proposals SET state='APPLIED' WHERE id=?", (row['proposal'],))


# -- what the window shows -----------------------------------------------------------------

def described(kernel, db, row, look=True):
    from .edit_storage import is_profiled
    if is_profiled(db,row['id']):
        return {'id':row['id'],'name':Path(row['work']).name,'kind':'folder','source':row['source'],
            'source_words':row['source'].replace(str(Path.home()),'~',1),'work':row['work'],'address':'@files:'+row['work'],
            'for_slate':bool(row['for_slate']),'state':row['state'],'status':'Profiled working copy — review in Changes',
            'original':'NOT_MEASURED_OPEN_CHANGES','edited':None,'proposal':None,'recovery':None,'last_update':None,
            'created':row['created'],'updated':row['updated'],'profiled':True,'change_review':'changes.workspace'}
    if (row['kind'] or 'file') == 'folder':return described_folder(kernel, db, row)
    work = files_service.root(kernel) / row['work']
    latest = db.execute("SELECT * FROM copies_proposals WHERE copy=? ORDER BY revision DESC LIMIT 1", (row['id'],)).fetchone()
    pending = db.execute("SELECT * FROM copies_journal WHERE copy=? AND stage='RECOVERY' ORDER BY at DESC LIMIT 1", (row['id'],)).fetchone()
    applied = db.execute("SELECT * FROM copies_journal WHERE copy=? AND stage='DONE' ORDER BY at DESC LIMIT 1", (row['id'],)).fetchone()
    original = original_state(row) if look else 'same'
    work_sha = sha_of(work) if work.is_file() else None
    if row['state'] == 'DISCARDED':status = 'Discarded — original unchanged'
    elif pending is not None:status = 'Recovery required'
    elif original == 'missing':status = 'Original is missing'
    elif original == 'changed':status = 'Original changed — review required'
    elif work_sha is None:status = 'Working copy missing (moved or deleted)'
    elif latest is not None and latest['state'] == 'READY' and latest['sha'] == work_sha:status = 'Ready for review — revision %d' % latest['revision']
    elif work_sha == row['base']:status = ('Same as the original — updated' if applied else 'Working copy — same as the original')
    else:status = 'Working copy — original unchanged'
    return {'id': row['id'], 'name': Path(row['source']).name, 'source': row['source'], 'source_words': row['source'].replace(str(Path.home()), '~', 1),
            'work': row['work'], 'address': '@files:' + row['work'], 'for_slate': bool(row['for_slate']), 'state': row['state'], 'status': status,
            'original': original, 'edited': work_sha is not None and work_sha != row['base'],
            'proposal': dict(latest) if latest is not None else None, 'recovery': dict(pending) if pending is not None else None,
            'last_update': dict(applied) if applied is not None else None, 'created': row['created'], 'updated': row['updated']}


def described_folder(kernel, db, row):
    from . import working_folders
    latest = db.execute("SELECT * FROM copies_proposals WHERE copy=? ORDER BY revision DESC LIMIT 1", (row['id'],)).fetchone()
    pending = db.execute("SELECT * FROM copies_journal WHERE copy=? AND stage='RECOVERY' ORDER BY at DESC LIMIT 1", (row['id'],)).fetchone()
    partial = latest is not None and latest['state'] == 'READY' and db.execute(
        "SELECT 1 FROM copies_journal WHERE proposal=? AND stage='DONE'", (latest['id'],)).fetchone() is not None
    try:original, ops, _ = working_folders.state_of(kernel, row)
    except (ValueError, OSError):original, ops = 'missing', None
    frozen = None
    if latest is not None and latest['state'] == 'READY' and ops is not None:
        try:frozen = {(o['op'], o['path'], o['after']) for o in working_folders.load(kernel, latest['sha'])['ops']} == {(o['op'], o['path'], o['after']) for o in ops}
        except (ValueError, OSError):frozen = False
    if row['state'] == 'DISCARDED':status = 'Discarded — original unchanged'
    elif pending is not None:status = 'Recovery required'
    elif partial:status = 'Partially applied — review required'
    elif original == 'missing':status = 'Original is missing'
    elif original == 'changed':status = 'Original changed — review required'
    elif ops is None:status = 'Working copy missing (moved or deleted)'
    elif frozen:status = 'Ready for review — revision %d' % latest['revision']
    elif not ops:status = 'Same as the original' + (' — updated' if db.execute("SELECT 1 FROM copies_proposals WHERE copy=? AND state='APPLIED'", (row['id'],)).fetchone() else '')
    else:status = 'Working copy — original unchanged'
    pill = str(row['source']).startswith('pill:')
    if pill and status == 'Working copy — original unchanged':status = 'Working copy — return it as a pill'
    name = Path(row['work']).name if pill else Path(row['source']).name
    words = 'came in a pill; its original is on the computer that sent it' if pill else row['source'].replace(str(Path.home()), '~', 1)
    return {'id': row['id'], 'kind': 'folder', 'name': name, 'source': row['source'], 'source_words': words, 'pill': pill,
            'work': row['work'], 'address': '@files:' + row['work'], 'for_slate': bool(row['for_slate']), 'state': row['state'], 'status': status,
            'original': original, 'edited': bool(ops), 'changes': len(ops or []), 'files': row['base_size'],
            'proposal': dict(latest) if latest is not None else None, 'recovery': dict(pending) if pending is not None else None,
            'last_update': None, 'created': row['created'], 'updated': row['updated']}


def the_copy(db, ident):
    row = db.execute('SELECT * FROM copies WHERE id=?', (ident,)).fetchone()
    if row is None:raise ValueError('COPIES_NOT_FOUND')
    return row


def assigned_to_slate(kernel, path):
    """True for a working copy you gave to Slate: he may edit it like his own area."""
    try:rel = files_service.rel_of(kernel, path)
    except ValueError:return False
    if not rel.startswith(WORKING + '/'):return False
    with opened(kernel) as db:
        works = [r[0] for r in db.execute("SELECT work FROM copies WHERE for_slate=1 AND state='WORKING'")]
    return any(rel == w or rel.startswith(w + '/') for w in works)  # a file, or anything inside a folder you gave him


# -- the operations --------------------------------------------------------------------------

def dispatch(kernel, op, args, principal):
    from .edit_storage import is_profiled
    with opened(kernel) as db:
        if op == 'copies.list':
            rows = db.execute("SELECT * FROM copies ORDER BY updated DESC").fetchall()
            rows=[r for r in rows if not is_profiled(db,r['id']) or r['owner']==principal.identity]
            recovering = db.execute("SELECT id, target, outcome FROM copies_journal WHERE stage NOT IN ('DONE','CANCELLED','CLOSED')").fetchall()
            return {'copies': [described(kernel, db, r) for r in rows], 'unfinished': [dict(r) for r in recovering], 'folder': WORKING}
        if op in ('copies.get','copies.review'):
            row=the_copy(db,args['id'])
            if is_profiled(db,row['id']):
                if row['owner']!=principal.identity:raise ValueError('Working copy unavailable to this caller')
                if op=='copies.review':raise ValueError('Use Changes to review this profiled copy, including its configuration files')
            return described(kernel,db,row) if op=='copies.get' else review(kernel,db,row)
        if op == 'copies.recover':return {'reconciled': recover(kernel, db, args.get('close'))}
        if op == 'copies.start':
            place = allowed_place(kernel, args['source'])
            if place.is_dir() and not place.is_symlink():
                from . import working_folders
                return described(kernel, db, the_copy(db, working_folders.start(kernel, db, working_folders.allowed_folder(kernel, args['source']), args.get('for_slate'), principal)))
            source = allowed_source(kernel, args['source'])
            data, info = capture(source);sha = keep_object(kernel, data)
            folder = files_service.root(kernel) / WORKING;folder.mkdir(parents=True, mode=0o700, exist_ok=True)
            work = files_service.free_name(folder, source.name)
            with open(work, 'xb') as f:f.write(data)
            ident = uuid.uuid4().hex;now = time.time()
            db.execute("INSERT INTO copies(id, owner, source, base, base_size, base_mtime, base_mode, work, for_slate, state, revision, created, updated, kind) "
                       "VALUES(?,?,?,?,?,?,?,?,?,'WORKING',0,?,?,'file')",
                       (ident, principal.identity, str(source), sha, info.st_size, info.st_mtime_ns, info.st_mode,
                        files_service.rel_of(kernel, work), int(bool(args.get('for_slate'))), now, now))
            return described(kernel, db, the_copy(db, ident))
        row = the_copy(db, args['id'])
        if is_profiled(db,row['id']):raise ValueError('Use Changes for profiled-copy proposals, updates, recovery and undo')
        folder = (row['kind'] or 'file') == 'folder'
        if folder:
            from . import working_folders
        if str(row['source']).startswith('pill:') and op in ('copies.apply', 'copies.undo', 'copies.refresh', 'copies.merge'):
            # Its original is on the other computer: only that computer may change it. The way back is a result pill.
            raise ValueError('COPIES_ORIGINAL_ELSEWHERE: this copy came in a pill; its original is on the computer that sent it. Return it as a pill (Files › Working copies › Return as a pill), or save it as new here')
        if op == 'copies.merge':
            if folder:raise ValueError('COPIES_MERGE_ONE_FILE: merging works on one text file at a time; review the folder file by file')
            return merge_copy(kernel, db, row)
        if op == 'copies.propose' and folder:
            if row['state'] != 'WORKING':raise ValueError('COPIES_NOT_WORKING: this draft was discarded')
            if not row['for_slate'] and 'approve' not in principal.scopes:raise ValueError('COPIES_NOT_ASSIGNED: this working copy is the owner\'s')
            return working_folders.propose(kernel, db, row, args.get('note'), principal)
        if op == 'copies.propose':
            if row['state'] != 'WORKING':raise ValueError('COPIES_NOT_WORKING: this draft was discarded')
            if not row['for_slate'] and 'approve' not in principal.scopes:raise ValueError('COPIES_NOT_ASSIGNED: this working copy is the owner\'s')
            work = files_service.root(kernel) / row['work']
            if not work.is_file() or work.is_symlink():raise ValueError('COPIES_WORK_MISSING: the working copy was moved or deleted')
            data = work.read_bytes()
            if len(data) > MAX_BYTES:raise ValueError('COPIES_SOURCE_TOO_LARGE: up to 64 MB for now')
            if CONFLICT_START.encode() in data:raise ValueError('COPIES_CONFLICTS_LEFT: settle the marked places from the merge first')
            sha = keep_object(kernel, data)
            if sha == row['base']:raise ValueError('COPIES_NOTHING_CHANGED: the working copy is the same as the original')
            latest = db.execute("SELECT * FROM copies_proposals WHERE copy=? AND state='READY' ORDER BY revision DESC LIMIT 1", (row['id'],)).fetchone()
            if latest is not None and latest['sha'] == sha and latest['base'] == row['base']:return {**dict(latest), 'note': latest['note']}
            db.execute("UPDATE copies_proposals SET state='SUPERSEDED' WHERE copy=? AND state='READY'", (row['id'],))
            revision = row['revision'] + 1;ident = uuid.uuid4().hex
            db.execute("INSERT INTO copies_proposals VALUES(?,?,?,?,?,?,?,?,'READY')", (ident, row['id'], revision, sha, row['base'], (args.get('note') or '')[:400], principal.identity, time.time()))
            db.execute('UPDATE copies SET revision=?, updated=? WHERE id=?', (revision, time.time(), row['id']))
            return dict(db.execute('SELECT * FROM copies_proposals WHERE id=?', (ident,)).fetchone())
        if op in ('copies.apply', 'copies.save_new'):
            proposal = db.execute('SELECT * FROM copies_proposals WHERE id=? AND copy=?', (args['proposal'], row['id'])).fetchone()
            if proposal is None:raise ValueError('COPIES_PROPOSAL_NOT_FOUND')
            if proposal['state'] != 'READY':raise ValueError('COPIES_PROPOSAL_' + proposal['state'] + ': review the latest revision')
            if folder:
                if op == 'copies.save_new':return working_folders.save_new(kernel, row, proposal, args.get('name'))
                recover(kernel, db)
                if db.execute("SELECT 1 FROM copies_journal WHERE copy=? AND stage='RECOVERY'", (row['id'],)).fetchone():
                    raise ValueError('COPIES_RECOVERY_REQUIRED: an earlier update of this folder needs a look first')
                result = working_folders.apply(kernel, db, row, proposal)
                return {**described(kernel, db, the_copy(db, row['id'])), **result}
            data = object_bytes(kernel, proposal['sha'])  # the frozen bytes, verified against their digest
            if op == 'copies.save_new':
                source = Path(row['source']);name = files_service.clean_name(args.get('name') or (source.stem + ' (from Graphite)' + source.suffix))
                if Path(os.path.realpath(source.parent)) != source.parent:raise ValueError('COPIES_DESTINATION_MOVED: the folder is now reached through a link')
                folder = os.open(source.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
                try:
                    try:fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, stat.S_IMODE(row['base_mode']) & 0o666 or 0o600, dir_fd=folder)
                    except FileExistsError:raise ValueError('COPIES_NAME_TAKEN: a file with that name is already there; nothing was overwritten') from None
                    try:
                        view = memoryview(data)
                        while view:view = view[os.write(fd, view):]
                        os.fsync(fd)
                    finally:os.close(fd)
                    os.fsync(folder)
                finally:os.close(folder)
                return {'saved': str(source.parent / name), 'saved_words': str(source.parent / name).replace(str(Path.home()), '~', 1), 'original': 'unchanged'}
            recover(kernel, db)
            if db.execute("SELECT 1 FROM copies_journal WHERE target=? AND stage='RECOVERY'", (row['source'],)).fetchone():
                raise ValueError('COPIES_RECOVERY_REQUIRED: an earlier update of this file needs a look first')
            if proposal['base'] != row['base']:raise ValueError('COPIES_PROPOSAL_STALE: the original moved on since this was proposed; review again')
            journal = uuid.uuid4().hex
            replace_original(kernel, db, journal, row['source'], row['base'], data, row['base_mode'], row['id'], proposal['id'], 'update')
            settle(db, db.execute('SELECT * FROM copies_journal WHERE id=?', (journal,)).fetchone())
            return {**described(kernel, db, the_copy(db, row['id'])), 'applied': proposal['revision'], 'kept_before': proposal['base']}
        if op == 'copies.undo' and folder:
            result = working_folders.undo(kernel, db, row)
            return {**described(kernel, db, the_copy(db, row['id'])), **result}
        if op == 'copies.refresh' and folder:
            manifest = working_folders.capture_folder(kernel, Path(row['source']));sha = working_folders.keep_manifest(kernel, manifest)
            db.execute('UPDATE copies SET base=?, base_size=?, updated=? WHERE id=?', (sha, len(manifest['files']), time.time(), row['id']))
            db.execute("UPDATE copies_proposals SET state='SUPERSEDED' WHERE copy=? AND state='READY'", (row['id'],))
            return {**described(kernel, db, the_copy(db, row['id'])), 'note': 'Compared with the changed original now. Your working copy is as it was; review before updating.'}
        if op == 'copies.undo':
            last = db.execute("SELECT * FROM copies_journal WHERE copy=? AND stage='DONE' AND kind='update' ORDER BY at DESC LIMIT 1", (row['id'],)).fetchone()
            if last is None:raise ValueError('COPIES_NOTHING_TO_UNDO')
            if row['base'] != last['after']:raise ValueError('COPIES_ORIGINAL_CHANGED: the original changed since the update; compare first')
            data = object_bytes(kernel, last['before']);journal = uuid.uuid4().hex
            replace_original(kernel, db, journal, row['source'], last['after'], data, row['base_mode'], row['id'], None, 'undo')
            settle(db, db.execute('SELECT * FROM copies_journal WHERE id=?', (journal,)).fetchone())
            db.execute("UPDATE copies_proposals SET state='SUPERSEDED' WHERE copy=? AND state='READY'", (row['id'],))
            return {**described(kernel, db, the_copy(db, row['id'])), 'undone': True}
        if op == 'copies.refresh':
            data, info = capture(allowed_source(kernel, row['source']));sha = keep_object(kernel, data)
            db.execute('UPDATE copies SET base=?, base_size=?, base_mtime=?, base_mode=?, updated=? WHERE id=?', (sha, info.st_size, info.st_mtime_ns, info.st_mode, time.time(), row['id']))
            db.execute("UPDATE copies_proposals SET state='SUPERSEDED' WHERE copy=? AND state='READY'", (row['id'],))
            return {**described(kernel, db, the_copy(db, row['id'])), 'note': 'Compared with the changed original now. Your working copy is as it was; review before updating.'}
        if op == 'copies.discard':
            if not row['for_slate'] and 'approve' not in principal.scopes:raise ValueError('COPIES_NOT_ASSIGNED: this working copy is the owner\'s')
            work = files_service.root(kernel) / row['work']
            trashed = None
            if work.is_file() or work.is_dir():trashed = files_service.dispatch(kernel, 'files.trash', {'path': row['work']}, principal)
            db.execute("UPDATE copies SET state='DISCARDED', updated=? WHERE id=?", (time.time(), row['id']))
            db.execute("UPDATE copies_proposals SET state='SUPERSEDED' WHERE copy=? AND state='READY'", (row['id'],))
            return {**described(kernel, db, the_copy(db, row['id'])), 'trash': trashed}
    raise ValueError('COPIES_UNKNOWN_OPERATION')



CONFLICT_START, CONFLICT_MIDDLE, CONFLICT_END = '<<<<<<< your working copy', '=======', '>>>>>>> the original, as changed elsewhere'


def merge3(base, mine, theirs):
    """Lines of three texts: what the work began from, the working copy, and the original as it is now. Changes from
    one side are taken; the same change on both is taken once; different changes to the same lines are a conflict,
    written with both versions between marker lines for you to settle. Returns (lines, conflicts)."""
    import difflib
    def hunks(other, side):
        matcher = difflib.SequenceMatcher(None, base, other, autojunk=False)
        return [(i1, i2, other[j1:j2], side) for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != 'equal']
    every = sorted(hunks(mine, 'mine') + hunks(theirs, 'theirs'), key=lambda h:(h[0], h[1]))
    out, conflicts, at, k = [], 0, 0, 0
    def ends(lines):
        return lines if not lines or lines[-1].endswith('\n') else lines[:-1] + [lines[-1] + '\n']
    while k < len(every):
        lo, hi = every[k][0], every[k][1];group = [every[k]];k += 1
        while k < len(every) and (every[k][0] < hi or every[k][0] == lo or (every[k][0] == hi and every[k][0] == every[k][1])):
            group.append(every[k]);hi = max(hi, every[k][1]);k += 1
        out += base[at:lo]
        def render(side):
            pos, seg = lo, []
            for a, b, r, s in group:
                if s != side:continue
                seg += base[pos:a] + r;pos = b
            return seg + base[pos:hi]
        sides = {h[3] for h in group}
        if len(sides) == 1:out += render(sides.pop())
        else:
            m, th = render('mine'), render('theirs')
            if m == th:out += m
            else:
                conflicts += 1
                out += [CONFLICT_START + '\n'] + ends(m) + [CONFLICT_MIDDLE + '\n'] + ends(th) + [CONFLICT_END + '\n']
        at = hi
    return out + base[at:], conflicts


def merge_copy(kernel, db, row):
    """The original changed elsewhere: bring that change into the working copy, keep yours, and mark where both changed
    the same lines. The working copy keeps its previous version; the copy now compares with the original as it is."""
    from .universal_view import decode
    work = files_service.root(kernel) / row['work']
    if not work.is_file():raise ValueError('COPIES_WORK_MISSING: the working copy was moved or deleted')
    if original_state(row) != 'changed':raise ValueError('COPIES_NOTHING_TO_MERGE: the original has not changed since the work began')
    source = allowed_source(kernel, row['source'])
    theirs_bytes, info = capture(source)
    texts = []
    for data in (object_bytes(kernel, row['base']), work.read_bytes(), theirs_bytes):
        if b'\x00' in data[:8192]:raise ValueError('COPIES_MERGE_TEXT_ONLY: merging works on text; for other files, compare and choose')
        texts.append(decode(data)[0].splitlines(keepends=True))
    merged, conflicts = merge3(*texts)
    files_service.write_text(kernel, work, ''.join(merged))  # the working copy's version before the merge is kept
    sha = keep_object(kernel, theirs_bytes)
    db.execute('UPDATE copies SET base=?, base_size=?, base_mtime=?, base_mode=?, updated=? WHERE id=?', (sha, info.st_size, info.st_mtime_ns, info.st_mode, time.time(), row['id']))
    db.execute("UPDATE copies_proposals SET state='SUPERSEDED' WHERE copy=? AND state='READY'", (row['id'],))
    return {**described(kernel, db, the_copy(db, row['id'])), 'conflicts': conflicts,
            'note': ('Merged. %d place%s where both changed the same lines are marked in the working copy; settle them, then freeze it for review.'
                     % (conflicts, '' if conflicts == 1 else 's')) if conflicts else 'Merged cleanly. Review it, then freeze it for review.'}


def review(kernel, db, row):
    """Exactly what Update original would do: the original as the work began, against the frozen proposal (or the draft so far)."""
    info = described(kernel, db, row)
    if (row['kind'] or 'file') == 'folder':
        from . import working_folders
        return working_folders.review(kernel, db, row, info)
    proposal = info['proposal'] if info['proposal'] and info['proposal']['state'] == 'READY' else None
    before = store(kernel) / row['base']
    after = store(kernel) / proposal['sha'] if proposal else files_service.root(kernel) / row['work']
    if not after.is_file():raise ValueError('COPIES_WORK_MISSING: the working copy was moved or deleted')
    label = ('revision %d, frozen for review' % proposal['revision']) if proposal else 'the working copy as it is now (not yet frozen)'
    out = files_service.compare_paths(before, after, info['source_words'] + ' (as the work began)', label, name=info['name'])
    out.update(copy=info, frozen=bool(proposal), paths={'before': str(before), 'after': str(after)})
    if info['original'] == 'changed':
        outside = files_service.compare_paths(before, Path(row['source']), 'as the work began', 'the original now', name=info['name'])
        out['outside'] = {k: outside.get(k) for k in ('added', 'removed', 'same_bytes')}
    return out
