"""Depths (Graphite 1.0 L4): the working view of an object, and its revisions when another program saves it.

The owner's paper, section 7: "A single click selects an item and shows its relationships. A double-click opens its working
interface ... Ordinary Save should save the current work without closing the editor. Closing the working view should
return to the board, after appropriate handling of unsaved changes. A deliberate Save and Return action could also provide
that transition." And: "An Open full application action is available when the compact editor does not support a necessary
feature, but the file identity and revision must remain recognizable when returning from the native program. Detecting an
external save should refresh or flag the compact view, not silently display a stale copy."

The window's side is workbench/depths_qt.py. What lives here has no Qt:

    the revisions of a plain file in Files that another program saved (the full program, opened from its working view, or
    any other program while the view was open). Each revision Graphite sees is recorded with its digest, the one before it,
    the program that saved it (when Graphite started that program) and when; the file's identity is L1's (living_nav), so a
    rename does not break the chain. The Kernel reads the file itself before it records anything: a revision is recorded
    only when the bytes on disk are the ones named (the effect is verified, never assumed from a program having run).
    The record is also a 'files.save' event in the activity journal, as Graphite's own saves are (file_delivery), with the
    new digest as its source generation.

    what rested on the earlier revision: an admitted source (an intake item, a snapshot of the file as it was) whose bytes
    are an earlier revision of a file in Files is that file's earlier revision. On the board (L2) the file is wired to it
    "saved again", the source and what rests on it directly are marked to recheck (mark_board). Nothing is changed in their
    records: the admitted source stays what it was (a snapshot), and bringing the new revision in is the owner's, through
    Intake as always.

Kernel operations (one block in engineering_kernel.py and engineering_cli.py, commented 1.0 L4):
    revisions.record  {path | id, expected_sha256, previous_sha256?, how?, program?}   execute   record the revision now on
                      disk (refused when the bytes on disk are not the ones named: "verified", or nothing is recorded)
    revisions.list    {id? | path?, limit?}                                            read      the revisions recorded
revisions.list is an observer (activity.OBSERVER_OPERATIONS): the board reads it each time it is drawn.

No floating point anywhere here: sizes and times are integers (nanoseconds), digests are hex.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import time
import uuid
from dataclasses import replace
from pathlib import Path

SCHEMA = 'graphite.revisions/1'
SHA = {'type': 'string', 'pattern': '^[0-9a-f]{64}$', 'maxLength': 64}
ID = {'type': 'string', 'pattern': '^fileid:[0-9a-f]{32}$', 'maxLength': 39}
PATH = {'type': 'string', 'minLength': 1, 'maxLength': 4000}
HOW = ('outside', 'full program')
FIELDS = {
    'revisions.record': ({'path': PATH, 'id': ID, 'expected_sha256': SHA, 'previous_sha256': SHA,
                          'how': {'type': 'string', 'enum': list(HOW)}, 'program': {'type': 'string', 'maxLength': 120}}, ['expected_sha256']),
    'revisions.list': ({'path': PATH, 'id': ID, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 500}}, []),
}
SCOPES = {'revisions.record': 'execute', 'revisions.list': 'read'}
OBSERVERS = ('revisions.list',)
BIGGEST = 512 * 1024 * 1024          # a file larger than this is not read whole to record its revision
COMPARE_LIMIT = 2 * 1024 * 1024      # a text compared line by line is at most this large on either side
MARKED = ('sheet', 'calculation', 'finding', 'document')     # what rests on an earlier revision and is marked to recheck
SETTLED = ('', 'current', 'supported', 'holds')               # the states a changed source puts in doubt (the Field's own words)


# ---- the store ---------------------------------------------------------------------------------------------------------------
def ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS work_revisions(id TEXT PRIMARY KEY, object TEXT NOT NULL, n INTEGER NOT NULL, digest TEXT NOT NULL, '
               'size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, previous TEXT NOT NULL, how TEXT NOT NULL, program TEXT NOT NULL, '
               'path TEXT NOT NULL, at_ns INTEGER NOT NULL, earlier TEXT NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS work_revisions_object ON work_revisions(object, n)')


def _row(row):
    keys = ('id', 'object', 'n', 'digest', 'size', 'mtime_ns', 'previous', 'how', 'program', 'path', 'at_ns', 'earlier')
    out = dict(zip(keys, row))
    try:out['earlier'] = json.loads(out['earlier'] or '[]')
    except ValueError:out['earlier'] = []
    return out


def sha256_of(path):
    """The whole file's SHA-256 (hex) and its size, read in pieces."""
    h = hashlib.sha256();size = 0
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk);size += len(chunk)
    return h.hexdigest(), size


def _place(kernel, args):
    """(object id, the file's path in Files, its whole path) for the file named by id or by path; refused outside Files."""
    from . import living_nav
    from .files_service import resolve, root
    base = root(kernel).resolve()
    if args.get('id'):
        found = living_nav.get(kernel, ident=args['id'])
        rel = found['path']
    else:
        raw = str(args.get('path') or '')
        given = Path(raw)
        if given.is_absolute():
            try:rel = given.resolve().relative_to(base).as_posix()
            except ValueError:raise ValueError('REVISIONS_OUTSIDE: only a file in Files has its revisions recorded') from None
        else:rel = raw
        found = living_nav.get(kernel, path=rel)
    target = resolve(kernel, found['path'])
    if found.get('kind') != 'file' or not target.is_file():raise ValueError('REVISIONS_NOT_A_FILE: %s is not a file in Files' % found['path'][:200])
    return found['id'], found['path'], target


def earlier_admitted(db, name, digests):
    """The admitted sources (intake items) of this file's name whose bytes are one of these earlier digests."""
    out = []
    try:rows = db.execute('SELECT id, ns, name, payload FROM intake_items WHERE name=?', (name,)).fetchall()
    except Exception:  # noqa: BLE001 - no Intake in this workspace: nothing was admitted
        return out
    for ident, ns, nm, payload in rows:
        try:sha = (json.loads(payload) or {}).get('sha256')
        except ValueError:continue
        if sha in digests:out.append({'item': ident, 'namespace': ns, 'name': nm, 'sha256': sha})
    return out


def record(kernel, args, principal):
    """revisions.record: the revision on disk now, recorded only when its bytes are the ones named."""
    from . import activity
    ident, rel, target = _place(kernel, args)
    st = target.stat()
    if st.st_size > BIGGEST:raise ValueError('REVISIONS_TOO_LARGE: %s is larger than Graphite reads whole to record a revision' % target.name)
    digest, size = sha256_of(target)
    if digest != args['expected_sha256']:
        raise ValueError('REVISIONS_NOT_ON_DISK: the bytes of %s on disk are not the revision named (it changed again, or was not saved); nothing is recorded'
                         % target.name)
    how = args.get('how') or 'outside';program = str(args.get('program') or '').strip()[:120]
    now = time.time_ns()
    with kernel.db() as db:
        ensure(db)
        chain = [_row(r) for r in db.execute('SELECT * FROM work_revisions WHERE object=? ORDER BY n', (ident,)).fetchall()]
        if chain and chain[-1]['digest'] == digest:
            last = chain[-1]
            return {'schema': SCHEMA, 'recorded': False, 'object': ident, 'path': rel, 'revision': last['n'], 'digest': digest,
                    'previous': last['previous'], 'program': last['program'], 'how': last['how'], 'earlier_admitted': last['earlier'],
                    'verified': 'the bytes on disk are revision %d, recorded already' % last['n'],
                    'words': '%s is as it was recorded (revision %d): nothing new to record.' % (target.name, last['n'])}
        previous = chain[-1]['digest'] if chain else str(args.get('previous_sha256') or '')
        if not chain and previous and previous != digest:      # the revision the window saw first is revision 1
            db.execute('INSERT INTO work_revisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                       ('rev:' + uuid.uuid4().hex, ident, 1, previous, 0, 0, '', 'seen', '', rel, now, '[]'))
            chain = [{'n': 1, 'digest': previous}]
        n = (chain[-1]['n'] + 1) if chain else 1
        digests = {r['digest'] for r in chain} - {digest}
        earlier = earlier_admitted(db, target.name, digests)
        row_id = 'rev:' + uuid.uuid4().hex
        db.execute('INSERT INTO work_revisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                   (row_id, ident, n, digest, int(size), int(st.st_mtime_ns), previous, how, program, rel, now, json.dumps(earlier)))
        try:
            activity.ensure(db)
            activity.append(db, activity.make_event('GUI', 'files.save', 'SAVED_ELSEWHERE', rel, correlation_id=row_id.replace('rev:', ''),
                                                    source_generation=digest))
        except Exception:  # noqa: BLE001 - the journal's event is a second record of the same fact; the revision row stands
            pass
    who = (' in ' + program) if program else (' by another program' if how == 'outside' else '')
    return {'schema': SCHEMA, 'recorded': True, 'object': ident, 'path': rel, 'revision': n, 'digest': digest, 'previous': previous,
            'program': program, 'how': how, 'earlier_admitted': earlier, 'size': int(size),
            'verified': 'the new revision is on disk (SHA-256 %s…)' % digest[:16],
            'words': '%s was saved%s: revision %d is recorded.' % (target.name, who, n)}


def listing(kernel, args):
    """revisions.list: the revisions recorded for one file (oldest first), or the latest few of every file."""
    limit = int(args.get('limit') or 200)
    ident = None
    if args.get('id') or args.get('path'):
        ident, _, _ = _place(kernel, args)
    with kernel.db() as db:
        ensure(db)
        if ident:rows = db.execute('SELECT * FROM work_revisions WHERE object=? ORDER BY n', (ident,)).fetchall()
        else:rows = db.execute('SELECT * FROM work_revisions ORDER BY at_ns DESC, n DESC LIMIT ?', (limit,)).fetchall()
    out = [_row(r) for r in rows]
    if not ident:out.sort(key=lambda r: (r['object'], r['n']))
    return {'schema': SCHEMA, 'revisions': out[-limit:] if ident else out}


def dispatch(kernel, op, args, principal):
    if op == 'revisions.record':return record(kernel, args, principal)
    if op == 'revisions.list':return listing(kernel, args)
    raise ValueError('Unknown revisions operation')


# ---- the board (L2): a file saved again, and what rested on its earlier revision ---------------------------------------------
def chains(rows):
    out = {}
    for row in rows or ():
        out.setdefault(row.get('object'), []).append(row)
    for chain in out.values():chain.sort(key=lambda r: int(r.get('n') or 0))
    return out


def mark_board(desk):
    """board_model.Desk: a plain file of Files saved again in another program. Its FILE tile says which revision it is; an
    admitted source holding one of its earlier revisions is wired to it "saved again", and that source and what rests on it
    directly are marked to recheck (their wires too). Reads only (revisions.list, through the desk's own reader)."""
    reader = getattr(desk, 'reader', None)
    if reader is None or not hasattr(reader, 'call'):return 0
    answer = reader.call('revisions.list', {'limit': 500})
    found = chains((answer or {}).get('revisions'))
    if not found:return 0
    from .board_model import Edge, file_object
    from .field_model import STATE_RECHECK
    entries = {e.get('id'): e for e in ((desk.files or {}).get('entries') or ())}
    root = (desk.files or {}).get('root')
    marked = 0
    for ident, chain in found.items():
        latest = chain[-1]
        if latest.get('n', 0) < 2:continue
        earlier = {r.get('digest') for r in chain[:-1]} | {r.get('previous') for r in chain if r.get('previous')}
        earlier.discard(latest.get('digest'));earlier.discard('')
        entry = entries.get(ident)
        name = entry.get('name') if entry else Path(str(latest.get('path') or '')).name
        said = 'revision %d%s' % (latest['n'], (', saved in ' + latest['program']) if latest.get('program') else ', saved elsewhere')
        if ident in desk.objects:
            obj = desk.objects[ident]
            desk.objects[ident] = replace(obj, lines=(said,) + tuple(obj.lines[1:3]))
        for obj in list(desk.objects.values()):
            target = obj.target if isinstance(obj.target, dict) else {}
            if obj.kind != 'source' or obj.id == ident or target.get('sha256') not in earlier or obj.title != name:continue
            if ident not in desk.objects:
                if entry is None:continue
                fobj = file_object(entry, root)
                desk.objects[ident] = replace(fobj, lines=(said,) + tuple(fobj.lines[1:3]))
            if obj.state != STATE_RECHECK:
                desk.objects[obj.id] = replace(obj, state=STATE_RECHECK, lines=tuple(obj.lines[:2]) + ('a newer revision is in Files',))
            for edge in desk.edges:
                if edge.source == obj.id and edge.target != ident:
                    edge.stale = True
                    rests = desk.objects.get(edge.target)
                    # a settled one is to recheck now; a refuted finding or an open question keeps its own word (its wire says recheck)
                    if rests is not None and rests.kind in MARKED and rests.state in SETTLED:
                        desk.objects[edge.target] = replace(rests, state=STATE_RECHECK)
            desk.edges = [e for e in desk.edges if not (e.relation == 'same bytes' and {e.source, e.target} == {ident, obj.id})]
            desk.edges.append(Edge(ident, obj.id, 'saved again', 'saved again' + ((' in ' + latest['program']) if latest.get('program') else ''), True,
                                   said='revision %d' % latest['n']))
            marked += 1
    if marked:desk._df = None
    return marked


def saved_again_basis(desk, edge):
    """The inspector's sentences for a "saved again" wire (board_model.basis)."""
    a = desk.objects.get(edge.source);b = desk.objects.get(edge.target)
    an = a.title if a else edge.source;bn = b.title if b else edge.target
    sha = (b.target or {}).get('sha256') if b is not None and isinstance(b.target, dict) else ''
    return edge.label or 'saved again', [
        'The file %s in Files was saved again%s: it is %s now.' % (an, edge.label[len('saved again'):] if edge.label.startswith('saved again') else '', edge.said or 'a newer revision'),
        'The admitted source %s holds an earlier revision of it%s.' % (bn, (' (SHA-256 %s…)' % str(sha)[:16]) if sha else ''),
        'What rests on that source is marked to recheck; the source itself is unchanged. Bring the new revision in through Intake when you want it read.']


# ---- comparing two texts (the line's Compare) ----------------------------------------------------------------------------------
def compare(mine, theirs, mine_name='yours, not saved', theirs_name='on disk now'):
    """The two texts line by line: [(mark, line)] with mark ' ' same, '-' only in yours, '+' only on disk, '@' a place."""
    a = (mine or '')[:COMPARE_LIMIT].splitlines();b = (theirs or '')[:COMPARE_LIMIT].splitlines()
    out = []
    import re
    for line in difflib.unified_diff(a, b, mine_name, theirs_name, n=2, lineterm=''):
        if line.startswith('---') or line.startswith('+++'):continue
        place = re.match(r'^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
        if place:      # the place in words, not the diff's own notation
            out.append(('@', 'from line %s of yours, line %s on disk:' % (place.group(1), place.group(2))));continue
        out.append((line[:1] if line[:1] in '+- ' else ' ', line[1:] if line[:1] in '+- ' else line))
    return out


def cells_compare(mine, theirs):
    """Two revisions of a sheet's cells: [(cell, yours, saved)] for each cell that differs (the first sheet of each)."""
    def cells(doc):
        sheets = (doc or {}).get('sheets') or [{}]
        return {k: (v or {}) for k, v in ((sheets[0] or {}).get('cells') or {}).items()}
    a = cells(mine);b = cells(theirs);out = []
    def shown(v):
        if not v:return '(blank)'
        value = v.get('formula') if v.get('formula') is not None else v.get('value')
        return ('%s %s' % (value, v.get('unit') or '')).strip()
    for key in sorted(set(a) | set(b), key=lambda k: (len(k), k)):
        if shown(a.get(key)) != shown(b.get(key)):out.append((key, shown(a.get(key)), shown(b.get(key))))
    return out


def file_state(path):
    """(size, mtime_ns, inode) of a file, or None: the cheap look before a digest is read."""
    try:st = os.stat(path)
    except OSError:return None
    return (int(st.st_size), int(st.st_mtime_ns), int(st.st_ino))
