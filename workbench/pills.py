"""Ledger's side of pills (docs/PILLS.md): paired computers, request pills in, result pills out.

    pills.identity   read     this Ledger's pill card (name, public key) and its paired computers
    pills.pair       approve  pair with another computer from its card; both sides show the same pairing code
    pills.unpair     approve  forget a paired computer
    pills.open       read     check a pill and describe it, without accepting anything
    pills.accept     approve  accept a request pill: quarantined, then a working copy (for you, or assigned to Slate)
    pills.list       read     pills received and returned
    pills.return     approve  freeze a pill's working copy and package the result pill, into Egress › Pills

The rule: a pill requests; Ledger's own policy decides. A request may ask only to inspect, analyze, propose revisions or
test; it can never widen a scope, run a program, or change anything outside its own working copy. Its original lives on
the computer that sent it, so this Ledger cannot change that original at all (copies.apply refuses pill copies). Returning a
result is your approval to export, and only that: the workstation decides, separately, whether to apply it.
"""
from __future__ import annotations
import contextlib
import os
import sqlite3
import stat
import time
import uuid
from pathlib import Path
from . import files_service

ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$'}
PLACE = {'type': 'string', 'minLength': 1, 'maxLength': 4096}
FIELDS = {
    'pills.identity': ({}, []),
    'pills.pair': ({'name': {'type': 'string', 'minLength': 1, 'maxLength': 80}, 'public': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}}, ['name', 'public']),
    'pills.unpair': ({'key': ID}, ['key']),
    'pills.open': ({'path': PLACE}, ['path']),
    'pills.accept': ({'path': PLACE, 'for_slate': {'type': 'boolean'}}, ['path']),
    'pills.list': ({}, []),
    'pills.return': ({'copy': ID, 'findings': {'type': 'string', 'maxLength': 200000}}, ['copy']),
    'pills.fetch': ({'address': {'type': 'string', 'minLength': 3, 'maxLength': 300}}, ['address']),
    'pills.send': ({'path': {'type': 'string', 'minLength': 1, 'maxLength': 4096}, 'address': {'type': 'string', 'minLength': 3, 'maxLength': 300}}, ['path', 'address']),
}
SCOPES = {'pills.identity': 'read', 'pills.open': 'read', 'pills.list': 'read',
          'pills.pair': 'approve', 'pills.unpair': 'approve', 'pills.accept': 'approve', 'pills.return': 'approve',
          'pills.fetch': 'approve', 'pills.send': 'approve'}
POLICY = {'inspect', 'analyze', 'propose_revisions', 'test'}   # what this Ledger agrees to be asked; anything else is refused
EXPORTS = 'Pills'


def kit():
    from pillkit import pill
    return pill


def ring(kernel):
    return kit().Keyring(Path(kernel.dbpath).parent / 'pills', 'Ledger')


@contextlib.contextmanager
def opened(kernel):
    with kernel.db() as db:
        db.row_factory = sqlite3.Row
        db.execute('''CREATE TABLE IF NOT EXISTS pills(id TEXT PRIMARY KEY, kind TEXT, sender TEXT, sender_name TEXT, task TEXT, title TEXT,
                      revision TEXT, copy TEXT, answers TEXT, file TEXT, object TEXT, state TEXT, at REAL)''')
        yield db


def pill_file(text):
    """A pill to read: an ordinary file in your home folder (Arrived, Downloads, a USB stick mounted there), not a link."""
    path = Path(os.path.expanduser(text))
    if not path.is_absolute():path = Path.home() / path
    path = Path(os.path.normpath(path))
    try:info = os.lstat(path)
    except FileNotFoundError:raise ValueError('PILLS_NOT_FOUND: ' + str(path)[:300]) from None
    if not stat.S_ISREG(info.st_mode):raise ValueError('PILLS_NOT_A_FILE: a pill is one ordinary file (not a link or a folder)')
    if info.st_size > kit().MAX_PILL:raise ValueError('PILLS_TOO_LARGE: up to 256 MB')
    return path


def read(kernel, text, replay=True):
    path = pill_file(text);raw = path.read_bytes()
    return path, raw, kit().open_pill(raw, ring(kernel), replay=replay)


def policy(pill):
    """This Ledger's own rule on what it is asked; a request cannot change it."""
    asked = set(pill.contract['requested'])
    if asked - POLICY:raise ValueError('PILLS_NOT_PERMITTED: this Graphite does not accept requests for ' + ', '.join(sorted(asked - POLICY)))


def described(kernel, row):
    value = dict(row)
    value['words'] = {'RECEIVED': 'received; a working copy holds it', 'RETURNED': 'answered with a result pill', 'SENT': 'a result pill, sent'}.get(row['state'], row['state'].lower())
    return value


def accept(kernel, db, args, principal):
    """Quarantine first: the pill's own bytes are kept as an object; its files become a working copy (never opened, never
    run on the way in). The copy's 'original' is the pill's revision, so Ledger has nothing it could overwrite."""
    from .working_copies import keep_object, the_copy, described as copy_described
    path, raw, pill = read(kernel, args['path'])
    if pill.kind != 'request':raise ValueError('PILLS_KIND: this is a result pill; results are applied on the computer that asked')
    policy(pill)
    c = pill.contract
    files = {}
    for rel, entry in c['source']['files'].items():
        files[rel] = {'sha': keep_object(kernel, pill.files[rel]), 'size': entry['bytes'], 'mtime': 0, 'mode': 0o600}
    manifest = {'schema': 'arc.copies-folder/1', 'files': files, 'skipped': []}
    from .working_folders import keep_manifest
    from .working_copies import object_bytes
    base = keep_manifest(kernel, manifest);kept = keep_object(kernel, raw)
    folder = files_service.root(kernel) / 'Working copies';folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    work = files_service.free_name(folder, ('%s · %s' % (c['task']['title'], c['sender']['name']))[:120].replace('/', '-'));work.mkdir(mode=0o700)
    for rel, entry in files.items():
        target = work / rel;target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        with open(target, 'xb') as f:f.write(object_bytes(kernel, entry['sha']))
        os.chmod(target, 0o600)  # never executable here, whatever it was there
    ident = uuid.uuid4().hex;now = time.time()
    db.execute("INSERT INTO copies(id, owner, source, base, base_size, base_mtime, base_mode, work, for_slate, state, revision, created, updated, kind) "
               "VALUES(?,?,?,?,?,?,?,?,?,'WORKING',0,?,?,'folder')",
               (ident, principal.identity, 'pill:' + c['id'], base, len(files), 0, 0o700, files_service.rel_of(kernel, work), int(bool(args.get('for_slate'))), now, now))
    db.execute('INSERT INTO pills(id, kind, sender, sender_name, task, title, revision, copy, answers, file, object, state, at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (c['id'], 'request', c['sender']['key'], c['sender']['name'], c['task']['id'], c['task']['title'], c['source']['revision'], ident,
                None, str(path), kept, 'RECEIVED', now))
    ring(kernel).remember(c['sender']['key'], c['id'], c['sequence'])
    copy = copy_described(kernel, db, the_copy(db, ident))
    return {'pill': pill.summary(), 'copy': copy, 'purpose': c['task']['purpose']}


def give_back(kernel, db, args, principal):
    """The result pill for a pill's working copy: what changed from the revision received, the changed files themselves,
    and your findings. It is written to Egress › Pills; carrying it back is up to you."""
    from .working_copies import the_copy
    from .working_folders import load, now_digests, operations
    copy = the_copy(db, args['copy']);source = str(copy['source'])
    if not source.startswith('pill:'):raise ValueError('PILLS_NOT_A_PILL_COPY: this working copy did not come in a pill')
    row = db.execute('SELECT * FROM pills WHERE id=?', (source[5:],)).fetchone()
    if row is None:raise ValueError('PILLS_UNKNOWN: the pill this copy came in is not recorded')
    pk = kit();keys = ring(kernel)
    request = pk.open_pill(object_of(kernel, row['object']), keys, replay=False)  # the request as it was accepted, checked again
    base = load(kernel, copy['base'])['files'];work = files_service.root(kernel) / copy['work']
    ops = operations(base, now_digests(work, base))
    changes, carried = [], {}
    for op in ops:
        rel = op['path']
        try:pk.safe_rel(rel)
        except pk.PillError:raise ValueError('PILLS_NAME: %s cannot travel in a pill; rename it first' % rel[:200]) from None
        before = request.contract['source']['files'].get(rel, {}).get('sha256', '')
        if op['op'] == 'delete':changes.append({'op': 'delete', 'path': rel, 'before': before, 'after': ''});continue
        data = (work / rel).read_bytes();after = pk.sha256(data)
        changes.append({'op': 'create' if op['op'] == 'create' else 'replace', 'path': rel, 'before': before, 'after': after});carried[rel] = data
    findings = (args.get('findings') or '').strip()
    notes = {'findings.md': findings.encode()} if findings else {}
    c = pk.contract(keys, row['sender'], 'result', request.contract['task'], request.contract['source']['label'], request.contract['source']['files'],
                    in_reply_to=row['id'], result={'findings': findings, 'changes': changes, 'evidence': sorted(notes)})
    raw = pk.build(keys, c, carried, notes)
    folder = files_service.root(kernel) / files_service.EXPORTS / EXPORTS;folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    target = files_service.free_name(folder, ('%s · result.pill' % row['title'])[:120].replace('/', '-'))
    with open(target, 'xb') as f:f.write(raw)
    now = time.time()
    db.execute('INSERT INTO pills(id, kind, sender, sender_name, task, title, revision, copy, answers, file, object, state, at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
               (c['id'], 'result', keys.key, keys.name, c['task']['id'], row['title'], c['source']['revision'], copy['id'], row['id'],
                str(target), None, 'SENT', now))
    db.execute("UPDATE pills SET state='RETURNED' WHERE id=?", (row['id'],))
    return {'pill': c['id'], 'path': files_service.rel_of(kernel, target), 'changes': len(changes), 'to': row['sender_name']}


def object_of(kernel, sha):
    from .working_copies import object_bytes
    return object_bytes(kernel, sha)


def dispatch(kernel, op, args, principal):
    if op == 'pills.identity':
        keys = ring(kernel)
        return {'card': keys.card(), 'peers': [{'key': k, 'name': v['name'], 'code': kit().pairing_code(keys.public, v['public'])} for k, v in keys.peers().items()]}
    if op == 'pills.pair':
        keys = ring(kernel)
        return keys.pair({'schema': kit().IDENTITY, 'name': args['name'], 'public': args['public']})
    if op == 'pills.unpair':ring(kernel).unpair(args['key']);return {'unpaired': args['key']}
    if op == 'pills.fetch':  # this Ledger connects out; it never listens. What comes in lands in quarantine, unaccepted.
        from pillkit import link
        into = files_service.root(kernel) / 'Received' / 'Pills'
        got = link.fetch(ring(kernel), args['address'], into)
        return {'from': got['from'], 'saved': [files_service.rel_of(kernel, Path(p)) for p in got['saved']],
                'note': 'Fetched pills wait in Files › Received › Pills; open one to check and accept it.'}
    if op == 'pills.send':
        from pillkit import link
        path = files_service.resolve(kernel, args['path'])
        if path.suffix != '.pill' or not path.is_file():raise ValueError('PILLS_NOT_A_PILL: only .pill files travel on the link')
        return link.send(ring(kernel), args['address'], path)
    if op == 'pills.open':
        path, _, pill = read(kernel, args['path'], replay=False)
        value = {'path': str(path), 'pill': pill.summary(), 'purpose': pill.contract['task']['purpose'], 'checks': [
            'signed by %s, a paired computer' % pill.contract['sender']['name'], 'every file matches its hash', 'meant for this Graphite']}
        try:
            if pill.kind == 'request':policy(pill)
            value['permitted'] = True
        except ValueError as exc:value['permitted'] = False;value['why_not'] = str(exc)
        try:ring(kernel).seen(pill.contract['sender']['key'], pill.id, pill.contract['sequence']);value['new'] = True
        except kit().PillError:value['new'] = False
        return value
    with opened(kernel) as db:
        if op == 'pills.list':return {'pills': [described(kernel, r) for r in db.execute('SELECT * FROM pills ORDER BY at DESC LIMIT 200')]}
        from .working_copies import opened as copies_opened
        with copies_opened(kernel):pass  # the copies tables exist before a pill makes a copy
        if op == 'pills.accept':return accept(kernel, db, args, principal)
        if op == 'pills.return':return give_back(kernel, db, args, principal)
    raise ValueError('UNKNOWN_OPERATION')
