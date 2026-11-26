"""Grants: what Kasandra may change without asking you again, where, and for how long (Graphite 1.0, K3).

The owner's paper, section 13: "Permission should attach to a specific operation, target, and scope. Granting Kasandra
authority to reorganize a working-copy folder does not imply permission to delete the original or publish the result to
the internet. A permission may also be time-bound or limited to a particular assignment." And: these boundaries are
enforced by Graphite's operation machinery, not by instructions given to the model.

A grant (graphite.grant/1, in the Kernel's own database: kas_grants, and kas_grant_uses for what was done under it):

  operation  a family (FAMILIES: "edit files", "set values on a sheet", ...), a tool of the registry (tools_registry, by its
             key) or one registered Kernel operation; it covers exactly the Kernel operations it names.
  target     a folder inside Files ("Rail Demo/notes": that folder and what is in it), or an object: a Kernel record (a
             sheet, a page), an App, a window. Every target of a call must be inside it. 1.0 L6: a folder may be any folder
             in your home ("~/Rail notes"), named from ~ or /; never one outside your home, never all of it, never
             Graphite's own records or program ("outside your home: never", home_reach).
  scope      this assignment (it ends when the assignment is done), until a time (whole milliseconds), or always (until
             you revoke it).
  words      what you read before you give it, e.g. "edit files in Rail Demo/notes, for this assignment".

Operations (registered in engineering_kernel under "1.0 K3"):

  grant.words   {operation, folder | object, scope, assignment?, until?}   read     the words and their digest, or why no
                                                                                   grant can be given for it
  grant.give    {... the same, expected_digest, step?}                    approve  your press: refused unless the digest is
                                                                                   the one of the words you were shown; with
                                                                                   step, that step is authorised by it
  grant.list    {all?, assignment?}                                       read     grants in force (all: ended ones too) with
                                                                                   their uses; the steps that wait for one
  grant.revoke  {id}                                                      approve  it ends now; nothing done under it is undone

Where it is enforced, at dispatch, in the Kernel's own path:
  - an assignment's step (K1, assignments.GRANT_CHECK, before anything is prepared): a change runs only when your press on
    that very step covers it as it was shown to you, or a grant of yours in force covers its operation and every target
    it resolves to. Otherwise it stops: "needs your grant", with one press, "Grant this for this assignment".
  - a tool's use (K2, tools_registry.GRANT_CHECK): a change through tools.use needs a grant in force (it has no
    assignment, so only "until" and "always" grants reach it).
  - Files (files_service.may_change): a write outside her own area is let through only for the one call a grant (or your
    press) covers, by a permit that lives for that call alone (in_force).
  - A grant authorises the proposed steps it covers (AUTHORISE), so routine work inside it does not ask again.

The model can never create or widen a grant: giving and revoking take the approve scope (your press; never her bounded
steps, never Tutor), the words are the desk's own (a target is named from the records, never from text handed in), the
digest of the words you saw must match, grant.* is never a step, a tool or the model's choice, and a grant is never given
from inside her work (a call inside a step's dispatch is refused).

1.0 L6, her reach: a change of hers lands only inside your home (and the workspace's Files, by its own rules), at every
place of the dial: a step, a tool use or her hand's card whose target is outside it stops as "outside your home: never",
before any grant or press is asked for (check_step, authorise, check_tool, and Files' own may_change at dispatch).

The floor stays under all of this (a grant never widens it): what always asks (stacy_hand.ALWAYS_ASKS: sending,
deleting, stopping, the session) is never granted; a change whose only basis is the model's pick is never authorised by
a grant; what the records mark for your approval stays yours by its own name; reading needs no grant; her hand on the
desk follows the dial; every change keeps its Undo where it had one (the version kept, her trail). Her own area
(Files/Slate) is hers by the Files rules, as before: it is shown as a standing line, it covers a dispatch, and it never
authorises a step by itself.
"""
from __future__ import annotations

import contextlib
import contextvars
import hashlib
import json
import re
import time
import uuid
from pathlib import PurePosixPath

SCHEMA = 'graphite.grant/1'
SCOPE_KINDS = ('assignment', 'until', 'always')
NEEDS = 'needs your grant: '
ONE_PRESS = 'Grant this for this assignment'
MOST = 200                    # grants listed at most
# A family: (what she may do, in words; the Kernel operations it covers).
FAMILIES = {
    'files.edit': ('edit files', ('files.write', 'files.mkdir', 'files.cells')),
    'files.organise': ('rename, move and copy files and make folders', ('files.rename', 'files.move', 'files.copy', 'files.mkdir')),
    'sheets.set': ('set values', ('field.set',)),
    'windows.arrange': ('bring forward or minimise program windows', ('windows.activate', 'windows.minimise')),
    'apps.open': ('open', ('apps.open',)),
    'utilities.try': ('try utilities on copies of files', ('sandbox.run',)),  # 1.0 K6 (coordinator): the sandbox's grant
    'web.read': ('fetch pages from the web', ('web.get',)),  # 1.0 K8: a page's address you typed, or a page already in quarantine, from one site
    'programs.work': ('work in a program', ('program.open', 'program.type', 'program.press', 'program.save')),  # 1.0 K9: her hand in your programs, on a file
}
OP_WORDS = {'files.write': 'write files', 'files.mkdir': 'make folders', 'files.cells': 'change cells of workbooks',
            'files.rename': 'rename files', 'files.move': 'move files', 'files.copy': 'copy files', 'field.set': 'set values',
            'windows.activate': 'bring forward', 'windows.minimise': 'minimise', 'apps.open': 'open',
            'documents.create': 'make pages', 'investigation.claim': 'add findings', 'agenda.add': 'add to the Agenda',
            'sandbox.run': 'try utilities on copies of files',  # 1.0 K6 (coordinator)
            'web.get': 'fetch pages from the web',  # 1.0 K8
            'program.open': 'open in its program', 'program.type': 'type in a program', 'program.press': 'press in a program',
            'program.save': 'save in a program'}  # 1.0 K9
NEVER = ('assignment.', 'grant.', 'halt.', 'ledger.', 'jobs.', 'remote.', 'master.', 'workers.', 'kasandra.', 'brain.help')
OWN_AREA = 'Slate'            # files_service.SLATE: her own area, hers by the Files rules
OWN_OPERATIONS = ('files.write', 'files.mkdir', 'files.cells')
FIELDS = {
    'grant.words': ({'operation': {'type': 'string', 'minLength': 1, 'maxLength': 120},
                     'folder': {'type': 'string', 'maxLength': 1000}, 'object': {'type': 'string', 'minLength': 1, 'maxLength': 200},
                     'scope': {'type': 'string', 'enum': list(SCOPE_KINDS)},
                     'assignment': {'type': 'string', 'minLength': 32, 'maxLength': 32},
                     'until': {'type': 'integer', 'minimum': 0, 'maximum': 1 << 50}}, ['operation', 'scope']),
    'grant.give': ({'operation': {'type': 'string', 'minLength': 1, 'maxLength': 120},
                    'folder': {'type': 'string', 'maxLength': 1000}, 'object': {'type': 'string', 'minLength': 1, 'maxLength': 200},
                    'scope': {'type': 'string', 'enum': list(SCOPE_KINDS)},
                    'assignment': {'type': 'string', 'minLength': 32, 'maxLength': 32},
                    'until': {'type': 'integer', 'minimum': 0, 'maximum': 1 << 50},
                    'expected_digest': {'type': 'string', 'minLength': 64, 'maxLength': 64},
                    'step': {'type': 'string', 'minLength': 1, 'maxLength': 32}}, ['operation', 'scope', 'expected_digest']),
    'grant.list': ({'all': {'type': 'boolean'}, 'assignment': {'type': 'string', 'minLength': 32, 'maxLength': 32},
                    'waiting': {'type': 'boolean'}}, []),
    'grant.revoke': ({'id': {'type': 'string', 'minLength': 32, 'maxLength': 32}}, ['id']),
}
SCOPES = {'grant.words': 'read', 'grant.list': 'read', 'grant.give': 'approve', 'grant.revoke': 'approve'}
OBSERVERS = ('grant.words', 'grant.list')
MIGRATIONS = [(1, (
    'CREATE TABLE kas_grants(id TEXT PRIMARY KEY, owner TEXT NOT NULL, given INTEGER NOT NULL, ended INTEGER, '
    'payload TEXT NOT NULL, digest TEXT NOT NULL)',
    'CREATE INDEX kas_grants_owner ON kas_grants(owner, given)',
    'CREATE TABLE kas_grant_uses(seq INTEGER PRIMARY KEY AUTOINCREMENT, grant_id TEXT NOT NULL, assignment TEXT NOT NULL, '
    'step TEXT NOT NULL, operation TEXT NOT NULL, target TEXT NOT NULL, at INTEGER NOT NULL)',
    'CREATE INDEX kas_grant_uses_of ON kas_grant_uses(grant_id, seq)',
))]

_PERMIT = contextvars.ContextVar('kas_grant_permit', default=None)


class NotGrantable(ValueError):
    """No grant can be given for this: the words say why."""


# ---------------------------------------------------------------- records

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def now_ms():
    return time.time_ns() // 1000000


def ensure(db):
    """Forward-only migrations of this slice's tables; other tables are left alone."""
    if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS kas_grants_migrations(version INTEGER PRIMARY KEY, digest TEXT NOT NULL, applied INTEGER NOT NULL)')
    applied = dict(db.execute('SELECT version, digest FROM kas_grants_migrations'))
    known = {version: digest(list(sql)) for version, sql in MIGRATIONS}
    if any(known.get(v) != d for v, d in applied.items()) or sorted(applied) != list(range(1, len(applied) + 1)):
        raise ValueError('GRANT_MIGRATION_UNSUPPORTED: use a compatible program')
    for version, statements in MIGRATIONS:
        if version in applied:continue
        for statement in statements:db.execute(statement)
        db.execute('INSERT INTO kas_grants_migrations VALUES(?,?,?)', (version, known[version], now_ms()))


def _present(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='kas_grants'").fetchone() is not None


@contextlib.contextmanager
def _writing(kernel):
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');ensure(db)
        yield db


def _rows(db, owner, every=False):
    """The owner's grants, newest first; a row whose digest does not match is never taken as in force."""
    if not _present(db):return []
    sql = 'SELECT payload, digest FROM kas_grants WHERE owner=?' + ('' if every else ' AND ended IS NULL') + ' ORDER BY given DESC LIMIT ?'
    out = []
    for raw, sha in db.execute(sql, (owner, MOST)).fetchall():
        value = json.loads(raw)
        value['intact'] = hashlib.sha256(raw.encode()).hexdigest() == sha
        out.append(value)
    return out


# ---------------------------------------------------------------- paths and targets

def clean_folder(text, kernel=None):
    """A folder inside Files, as a relative path with no '..', or a refusal. 1.0 L6: named from ~ or /, a folder in your
    home ('~/Rail notes'; one inside Files is named as Files names it), never one outside it."""
    if str(text or '').strip().startswith(('/', '~')):  # 1.0 L6
        from . import home_reach
        if kernel is None:raise NotGrantable('GRANT_FOLDER: a folder in your home is named with its workspace')
        value, why = home_reach.grant_folder(kernel, str(text).strip())
        if why:raise NotGrantable(why)
        return value
    parts = [p for p in PurePosixPath(str(text or '').replace('\\', '/')).parts if p not in ('', '/', '.')]
    if not parts:raise NotGrantable('GRANT_FOLDER: name a folder inside Files (a grant over all of Files is never given)')
    if any(p == '..' or '\0' in p for p in parts):raise NotGrantable('GRANT_FOLDER: a folder inside Files, with no ".."')
    if parts[0] in ('.trash', '.versions'):raise NotGrantable('GRANT_FOLDER: DELETE and kept versions keep their own words')
    return '/'.join(parts)


def _clean_path(text):
    raw = str(text or '').replace('\\', '/')
    lead = '~' if raw == '~' or raw.startswith('~/') else '/' if raw.startswith('/') else ''  # 1.0 L6: from ~ or /, kept so
    parts = [p for p in PurePosixPath(raw[1:] if lead == '~' else raw).parts if p not in ('', '/', '.')]
    if any(p == '..' for p in parts):return None
    if lead == '~':return '~/' + '/'.join(parts) if parts else '~'
    return lead + '/'.join(parts)


def _bare(ident):
    ident = str(ident)
    return ident.split(':', 1)[1] if ident.startswith(('office:', 'documents:', 'record:')) else ident


def targets(operation, arguments):
    """What a call lands on: {'paths': [...], 'objects': [...]} from its arguments (paths inside Files, objects by id)."""
    a = arguments if isinstance(arguments, dict) else {}
    paths, objects = [], []
    if operation == 'files.mkdir':
        name = a.get('name')
        if isinstance(name, str):
            joined = _clean_path(((a.get('path') or '').rstrip('/') + '/' + name) if a.get('path') else name)  # 1.0 L6: '' + '/x' is not /x
            paths.append(joined)
    elif operation == 'sandbox.run':  # 1.0 K6 (coordinator): a utility's run lands on (copies of) its inputs
        for item in a.get('inputs') or ():
            if isinstance(item, str):paths.append(_clean_path(item))
    elif operation == 'web.get':  # 1.0 K8: a fetch lands on one site (site:<host>), never on a path in Files
        try:
            from .network_governed import check_address
            objects.append(check_address(a.get('page'))['site'])
        except (ValueError, ImportError):
            pass
        return {'paths': paths, 'objects': objects}
    else:
        for key in ('path', 'to'):
            if isinstance(a.get(key), str):paths.append(_clean_path(a[key]))
    for key in ('id', 'window', 'sheet', 'object'):
        if isinstance(a.get(key), str) and not operation.startswith('files.'):objects.append(_bare(a[key]))
    return {'paths': paths, 'objects': objects}


def inside(path, folder):
    return path is not None and (path == folder or path.startswith(folder.rstrip('/') + '/'))


def _within(kernel, path, folder):
    """1.0 L6: whether a path (as a call names it: inside Files, from ~ or from /) is the folder or inside it, compared as
    the places they are on this computer (a Files folder and the same folder named from ~ are one place)."""
    if path is None or folder is None:return False
    try:
        from . import home_reach
        a, b = home_reach.absolute(kernel, path), home_reach.absolute(kernel, folder)
    except Exception:  # noqa: BLE001 - a place that cannot be named is inside nothing
        return False
    return a is not None and b is not None and home_reach.within(a, b)


def _has_reference(value):
    if isinstance(value, dict):
        if '$step' in value:return True
        return any(_has_reference(v) for v in value.values())
    if isinstance(value, list):return any(_has_reference(v) for v in value)
    return False


def _fixed_targets(operation, arguments):
    """The targets of a planned call when none comes from an earlier step's output; None when one does."""
    a = arguments if isinstance(arguments, dict) else {}
    for key in ('path', 'to', 'name', 'id', 'window', 'sheet', 'object', 'inputs'):  # 'inputs': 1.0 K6 (coordinator)
        if key in a and _has_reference(a[key]):return None
    found = targets(operation, a)
    return found if (found['paths'] or found['objects']) and None not in found['paths'] else None


# ---------------------------------------------------------------- words

def _read(kernel, operation, arguments):
    from .engineering_kernel import operator, Principal
    reader = Principal(operator().identity, frozenset({'read'}))
    try:
        answer = kernel.dispatch(operation, arguments, reader)
    except Exception:  # noqa: BLE001 - words only
        return None
    return answer.get('result') if isinstance(answer, dict) and answer.get('ok') else None


def object_words(kernel, ident):
    """An object named from the records (never from words handed in): its kind and title."""
    ident = _bare(ident)
    got = _read(kernel, 'office.get', {'id': ident})
    if isinstance(got, dict):
        doc = got.get('document') or {}
        title = doc.get('title') or got.get('title')
        if title:return 'the sheet “%s”' % str(title)[:120]
    got = _read(kernel, 'documents.get', {'id': ident})
    if isinstance(got, dict):
        doc = got.get('document') or got
        if doc.get('title'):return 'the page “%s”' % str(doc['title'])[:120]
    got = _read(kernel, 'objects.get', {'id': ident})
    if isinstance(got, dict) and got.get('path'):
        if str(got['path']).startswith('/'):  # 1.0 L6: a file elsewhere on this computer
            from . import home_reach
            return '“%s”' % home_reach.tilde(got['path'])[:160]
        return '“%s” in Files' % str(got['path'])[:160]
    if ident.endswith('.desktop'):
        try:
            from . import apps_catalog
            app = apps_catalog.find_app(ident)
            if app is not None:return 'the App “%s”' % str(app.name)[:80]
        except Exception:  # noqa: BLE001
            pass
        return 'the App %s' % ident[:80]
    if re.match(r'^0x[0-9a-f]+$', ident):return 'the program window %s' % ident
    if ident.startswith('site:'):return 'the site %s' % ident[len('site:'):][:120]  # 1.0 K8: pages fetched from one site
    return 'the record %s' % ident[:16]


def _when(ms):
    return time.strftime('%d %b %Y, %H:%M', time.localtime(ms // 1000))


def scope_words(scope):
    if scope['kind'] == 'assignment':return 'for this assignment (“%s”)' % scope.get('title', '')[:120] if scope.get('title') else 'for this assignment'
    if scope['kind'] == 'until':return 'until %s' % _when(scope['until'])
    return 'always, until you revoke it'


def _operations(name):
    """(what she may do, the Kernel operations) for a family, a tool's key or one operation; NotGrantable when it is none
    of these, or one a grant never covers (the floor)."""
    from .engineering_kernel import CAPABILITIES
    from . import stacy_hand
    if name in FAMILIES:
        doing, ops = FAMILIES[name]
    elif name in CAPABILITIES:
        doing, ops = OP_WORDS.get(name) or _k1_words(name), (name,)
    else:
        try:
            from . import tools_registry
            tool = tools_registry.TOOLS.get(name)
        except Exception:  # noqa: BLE001
            tool = None
        if tool is None:raise NotGrantable('GRANT_OPERATION: %s is not a family, a tool or a registered operation' % str(name)[:80])
        if tool.family == 'desk':raise NotGrantable('GRANT_DESK: her hand on the desk follows the dial, not a grant')
        if tool.undo == 'read':raise NotGrantable('GRANT_READ: reading needs no grant')
        if tool.undo == 'send':raise NotGrantable('GRANT_SENDS: what is sent off this computer asks you every time; it is never granted')
        if tool.slice and not tool.operations:raise NotGrantable('GRANT_NOT_BUILT: %s is not built yet' % tool.key)
        doing = re.sub(r' (in the folder|on the sheet|in the folder and into the other| \(.*\))$', '', tool.grant or tool.words)
        ops = tuple(tool.operations)
    for op in ops:
        scope = CAPABILITIES.get(op)
        if scope is None:raise NotGrantable('GRANT_OPERATION: %s is not registered here' % op)
        if op.startswith(NEVER):raise NotGrantable('GRANT_OWN_CONTROLS: %s is one of her own controls or yours; it is never granted' % op)
        if scope == 'read':raise NotGrantable('GRANT_READ: %s only reads; reading needs no grant' % op)
        if scope == 'approve':raise NotGrantable('GRANT_APPROVE: the records mark %s for your approval: it is authorised by its own name, never by a grant' % op)
        why = stacy_hand.why_asks(op)
        if why:raise NotGrantable('GRANT_ALWAYS_ASKS: %s always asks (%s); it is never granted' % (op, why))
    return doing, tuple(ops)


def _k1_words(op):
    try:
        from . import assignments
        return assignments.GRANT_WORDS.get(op) or 'use %s' % op
    except Exception:  # noqa: BLE001
        return 'use %s' % op


def _assignment(kernel, ident, principal):
    from . import assignments
    with kernel.db() as db:
        value = assignments._load(db, ident, principal)
    if value['state'] == assignments.DONE:raise NotGrantable('GRANT_SCOPE: that assignment is done; a grant for it would cover nothing')
    return value


def describe(kernel, args, principal):
    """The grant as it would be given: its words, its digest and what it covers. NotGrantable says why not."""
    name = args['operation'];doing, ops = _operations(name)
    folder, obj = args.get('folder'), args.get('object')
    if bool(folder) == bool(obj):raise NotGrantable('GRANT_TARGET: name one target: a folder inside Files or in your home, or an object')
    if folder:
        if any(op.startswith(('windows.', 'apps.', 'field.')) for op in ops):raise NotGrantable('GRANT_TARGET: this works on an object, not a folder')
        value = clean_folder(folder, kernel)  # 1.0 L6: or a folder in your home
        target = {'kind': 'folder', 'value': value, 'words': 'in %s' % value}
    else:
        value = _bare(obj)
        if not re.match(r'^[A-Za-z0-9_.:\-]{1,200}$', value):raise NotGrantable('GRANT_TARGET: an object is named by its id')
        target = {'kind': 'object', 'value': value, 'words': 'on %s' % object_words(kernel, value)}
    kind = args['scope'];scope = {'kind': kind}
    if kind == 'assignment':
        if not args.get('assignment'):raise NotGrantable('GRANT_SCOPE: name the assignment')
        value_a = _assignment(kernel, args['assignment'], principal)
        scope.update(assignment=value_a['id'], title=value_a['title'][:120])
    elif kind == 'until':
        until = args.get('until')
        if type(until) is not int or until <= now_ms():raise NotGrantable('GRANT_SCOPE: until a time still to come (whole milliseconds)')
        scope['until'] = until
    words = '%s %s, %s' % (doing, target['words'], scope_words(scope))
    shown = {'words': words, 'operations': list(ops), 'target': {k: target[k] for k in ('kind', 'value')}, 'scope': scope}
    return {'schema': SCHEMA, 'operation': name, 'doing': doing, 'operations': list(ops), 'target': target, 'scope': scope,
            'words': words, 'digest': digest(shown), 'grantable': True,
            'floor': 'What always asks still asks; a change only the model chose is never done; Undo stays as it was.'}


# ---------------------------------------------------------------- the owner's press

def _owner_only(principal):
    if 'approve' not in principal.scopes or principal.mode == 'Tutor':
        raise ValueError('GRANT_IS_YOURS: only your own press gives or ends a grant')
    if _PERMIT.get() is not None:
        raise ValueError('GRANT_IS_YOURS: a grant is never given or ended from inside her work')


def give(kernel, args, principal):
    _owner_only(principal)
    shown = describe(kernel, args, principal)
    if args['expected_digest'] != shown['digest']:
        raise ValueError('GRANT_CHANGED: these are not the words you were shown; read the grant again')
    ident = uuid.uuid4().hex;given = now_ms()
    step = args.get('step')
    source = 'your press on the Grants page'
    if step and shown['scope']['kind'] == 'assignment':source = 'your press: %s' % ONE_PRESS
    value = {'schema': SCHEMA, 'id': ident, 'owner': principal.identity, 'operation': shown['operation'], 'doing': shown['doing'],
             'operations': shown['operations'], 'target': shown['target'], 'scope': shown['scope'], 'words': shown['words'],
             'shown': shown['digest'], 'given': given, 'given_by': principal.identity, 'source': source, 'ended': None}
    raw = canonical(value)
    with _writing(kernel) as db:
        db.execute('INSERT INTO kas_grants VALUES(?,?,?,?,?,?)', (ident, principal.identity, given, None, raw, hashlib.sha256(raw.encode()).hexdigest()))
        from . import activity
        activity.append(db, activity.make_event(principal.identity, 'grant.give', 'GIVEN'))
    said = ['You gave a grant: %s.' % shown['words']]
    if step and shown['scope']['kind'] == 'assignment':
        said.extend(_authorise_named(kernel, shown['scope']['assignment'], step, principal))
    else:      # the proposed steps it covers, in the assignment it is for (or in each open one, for a grant until a time or always)
        said.extend(_sweep(kernel, principal, shown['scope'].get('assignment')))
    return {'schema': SCHEMA, 'grant': _view(value), 'said': said}


def _sweep(kernel, principal, assignment=None):
    from . import assignments as A
    if assignment:ids = [assignment]
    else:
        try:
            with kernel.db() as db:
                ids = [r[0] for r in db.execute("SELECT id FROM asg_assignments WHERE owner=? AND state='open' ORDER BY updated DESC LIMIT 50",
                                                (principal.identity,))] if A._present(db) else []
        except Exception:  # noqa: BLE001
            ids = []
    said = []
    for ident in ids:
        try:said.extend(authorise(kernel, ident, principal))
        except Exception:  # noqa: BLE001 - one assignment that cannot be read never undoes the grant
            pass
    return said


def revoke(kernel, args, principal):
    _owner_only(principal)
    with _writing(kernel) as db:
        row = db.execute('SELECT payload, digest FROM kas_grants WHERE id=? AND owner=?', (args['id'], principal.identity)).fetchone()
        if not row:raise ValueError('GRANT_UNAVAILABLE: there is no such grant of yours')
        value = json.loads(row[0])
        if value.get('ended'):raise ValueError('GRANT_ENDED: it has ended already')
        value['ended'] = {'at': now_ms(), 'by': principal.identity, 'why': 'you revoked it'}
        raw = canonical(value)
        db.execute('UPDATE kas_grants SET ended=?, payload=?, digest=? WHERE id=?', (value['ended']['at'], raw, hashlib.sha256(raw.encode()).hexdigest(), args['id']))
        from . import activity
        activity.append(db, activity.make_event(principal.identity, 'grant.revoke', 'REVOKED'))
    return {'schema': SCHEMA, 'grant': _view(value), 'said': ['You revoked a grant: %s. What was done under it stays done, with its Undo.' % value['words']]}


# ---------------------------------------------------------------- what is in force

def _assignment_open(kernel, ident, owner, cache):
    if ident in cache:return cache[ident]
    state = None
    try:
        with kernel.db() as db:
            row = db.execute('SELECT state FROM asg_assignments WHERE id=? AND owner=?', (ident, owner)).fetchone()
        state = row[0] if row else None
    except Exception:  # noqa: BLE001 - no assignments yet
        state = None
    cache[ident] = state is not None and state != 'done'
    return cache[ident]


def live(kernel, grant, now=None, cache=None):
    """'' while a grant is in force, else why it is not (in words)."""
    if not grant.get('intact', True):return 'its record does not match its digest'
    if grant.get('ended'):return grant['ended'].get('why') or 'it ended'
    scope = grant['scope'];now = now if now is not None else now_ms()
    if scope['kind'] == 'until' and now >= scope['until']:return 'its time ran out (%s)' % _when(scope['until'])
    if scope['kind'] == 'assignment' and not _assignment_open(kernel, scope['assignment'], grant['owner'], cache if cache is not None else {}):
        return 'its assignment is done'
    return ''


def built_in(owner):
    return {'schema': SCHEMA, 'id': 'own-area', 'owner': owner, 'operation': 'files.edit', 'doing': 'edit files',
            'operations': list(OWN_OPERATIONS), 'target': {'kind': 'folder', 'value': OWN_AREA, 'words': 'in her own area (Files/Slate)'},
            'scope': {'kind': 'always'}, 'words': 'edit files in her own area (Files/Slate), always: the Files rules have always let her write there',
            'given': 0, 'source': 'the Files rules', 'ended': None, 'built_in': True}


def _covers(kernel, grant, operation, found):
    if operation not in grant['operations']:return False
    target = grant['target']
    if not found['paths'] and not found['objects']:return False
    if target['kind'] == 'folder':
        return not found['objects'] and all(_within(kernel, p, target['value']) for p in found['paths'])  # 1.0 L6: as places
    if found['objects']:return not found['paths'] and all(o == target['value'] for o in found['objects'])
    # a file object: every path is that file
    for path in found['paths']:
        got = _read(kernel, 'objects.get', {'path': path}) if path else None
        if not isinstance(got, dict) or got.get('id') != target['value']:return False
    return True


def covering(kernel, owner, operation, arguments, assignment=None, include_built_in=True):
    """The grant in force that covers this call (its operation and every target it lands on), or None. A grant for an
    assignment reaches only that assignment's steps."""
    found = targets(operation, arguments)
    if None in found['paths']:return None
    try:
        with kernel.db() as db:rows = _rows(db, owner)
    except Exception:  # noqa: BLE001 - grants that cannot be read cover nothing
        rows = []
    now = now_ms();cache = {}
    for grant in rows:
        if grant['scope']['kind'] == 'assignment' and grant['scope'].get('assignment') != assignment:continue
        if live(kernel, grant, now, cache):continue
        if _covers(kernel, grant, operation, found):return grant
    if include_built_in:
        own = built_in(owner)
        if _covers(kernel, own, operation, found):return own
    return None


def _where(kernel, operation, found):
    if found['paths']:
        folders = sorted({(p.rsplit('/', 1)[0] if '/' in p else '(the top of Files)') for p in found['paths'] if p is not None})
        return 'in ' + ', '.join(folders)
    if found['objects']:return 'on ' + ', '.join(object_words(kernel, o) for o in found['objects'][:2])
    return 'on what it names'


def need_words(kernel, operation, arguments):
    """What a call would do, where: "write files in Rail Demo sources"."""
    return '%s %s' % (OP_WORDS.get(operation) or _k1_words(operation), _where(kernel, operation, targets(operation, arguments)))


def _why(kernel, owner, operation, arguments, assignment=None):
    said = need_words(kernel, operation, arguments)
    try:
        with kernel.db() as db:rows = _rows(db, owner)
    except Exception:  # noqa: BLE001
        rows = []
    mine = [g['words'] for g in rows if not live(kernel, g) and (g['scope']['kind'] != 'assignment' or g['scope'].get('assignment') == assignment)]
    tail = ('; your grants here: ' + '; '.join(w.split(', for this assignment')[0] for w in mine[:2])) if mine else '; no grant of yours is in force here'
    return (said + tail)[:290]


# ---------------------------------------------------------------- enforcement (the Kernel's path)

def check_step(kernel, value, step, arguments, principal):
    """assignments.GRANT_CHECK: '' when this step may run as it is now, else why it needs your grant. 1.0 L6: a change
    outside your home stops here, whatever was pressed or granted: "outside your home: never"."""
    if step.get('scope') == 'read':return ''
    never = _never(kernel, step['operation'], arguments)  # 1.0 L6
    if never:raise ValueError(never)
    if step.get('scope') == 'approve':return ''      # K1 already requires your press on it by name, its inputs fixed then
    op = step['operation'];auth = step.get('authorised') or {}
    if auth.get('by') == principal.identity and not auth.get('grant'):      # your press on this step, as it was shown to you
        planned = _fixed_targets(op, step.get('arguments'))
        if planned is not None and planned == targets(op, arguments):return ''
    grant = covering(kernel, principal.identity, op, arguments, value['id'])
    if grant is not None and _from_the_owner(kernel, step, principal):return ''      # 1.0 K8: a page's address, never one taken from a page
    if grant is not None:return 'its address came from a page, not from you: fetching it needs your press on this step'
    return _why(kernel, principal.identity, op, arguments, value['id'])


def _never(kernel, operation, arguments):
    """1.0 L6: '' unless the call is a change that would land outside your home (or on Graphite's own): why it never may."""
    try:
        from . import home_reach
        return home_reach.never_words(kernel, operation, arguments)
    except Exception:  # noqa: BLE001 - a place that cannot be named is refused by Files' own check at dispatch
        return ''


def _from_the_owner(kernel, step, principal):
    """1.0 K8: a grant covers a fetch (web.get) only of an address you typed or of a page already kept in quarantine; an
    address that came from a page (a link) or anywhere else needs your press on the step. Every other operation: True."""
    if step.get('operation') != 'web.get':return True
    origin = ((step.get('inputs') or {}).get('page') or {}).get('origin') or {}
    if origin.get('kind') == 'OWNER_WORDS':return True
    if origin.get('kind') == 'RECORD':
        try:
            from .network_governed import admitted, check_address
            return admitted(kernel, principal.identity, check_address((step.get('arguments') or {}).get('page'))['address'])
        except (ValueError, ImportError):
            return False
    return False


def check_tool(kernel, tool, operation, arguments, principal):
    """tools_registry.GRANT_CHECK: a change through tools.use needs a grant in force ("until" or "always"; her own area
    is hers by the Files rules)."""
    if getattr(tool, 'undo', 'change') != 'change':return ''
    never = _never(kernel, operation, arguments)  # 1.0 L6: outside your home, never (tools_registry says it as it is)
    if never:return never
    if covering(kernel, principal.identity, operation, arguments, None) is not None:return ''
    return _why(kernel, principal.identity, operation, arguments)


@contextlib.contextmanager
def in_force(kernel, principal, operation, arguments, assignment='', step=''):
    """Around one dispatch that the check let through: a permit naming exactly what this call may change, read by Files
    (permitted()) and by nothing else; and a line in kas_grant_uses for the grant it used."""
    found = targets(operation, arguments)
    grant = None
    try:grant = covering(kernel, principal.identity, operation, arguments, assignment or None)
    except Exception:  # noqa: BLE001
        grant = None
    permit = {'root': str(getattr(kernel, 'root', '')), 'operation': operation, 'paths': [p for p in found['paths'] if p],
              'objects': list(found['objects']), 'grant': (grant or {}).get('id', 'your press'),
              'assignment': assignment or ''}  # 1.0 K9: her hand records which assignment opened a window
    token = _PERMIT.set(permit)
    try:
        yield permit
    finally:
        _PERMIT.reset(token)
        if grant is not None and not grant.get('built_in'):
            try:
                with _writing(kernel) as db:
                    db.execute('INSERT INTO kas_grant_uses(grant_id, assignment, step, operation, target, at) VALUES(?,?,?,?,?,?)',
                               (grant['id'], assignment or '', step or '', operation, canonical(found)[:1000], now_ms()))
            except Exception:  # noqa: BLE001 - a use that cannot be written never undoes the call
                pass


def step_in_force(kernel, value, step, arguments, principal):
    """assignments.GRANTED: the permit around a step's own dispatch."""
    if step.get('scope') == 'read':return contextlib.nullcontext()
    return in_force(kernel, principal, step['operation'], arguments, value['id'], step['key'])


def tool_in_force(kernel, tool, operation, arguments, principal):
    """tools_registry.GRANTED: the permit around a tool's own dispatch."""
    if getattr(tool, 'undo', 'change') != 'change':return contextlib.nullcontext()
    return in_force(kernel, principal, operation, arguments)


def permitted(kernel, path):
    """files_service.may_change: whether the call being made now is one a grant (or your press) let through for this path."""
    permit = _PERMIT.get()
    if not permit or permit['root'] != str(getattr(kernel, 'root', '')):return False
    return any(_within(kernel, str(path), p) for p in permit['paths'])  # 1.0 L6: as places (inside Files or in your home)


def permitted_object(kernel, operation, ident):
    """field.set's own save: whether the call being made now is this operation on this object, let through by a grant (or
    your press on the step)."""
    permit = _PERMIT.get()
    if not permit or permit['root'] != str(getattr(kernel, 'root', '')) or permit['operation'] != operation:return False
    return _bare(ident) in permit.get('objects', ())


# ---------------------------------------------------------------- a grant authorises the steps it covers

def _grantable(step):
    from . import stacy_hand
    return (step.get('scope') == 'execute' and not step.get('always_asks') and step.get('basis') != stacy_hand.MODEL_PICK
            and not step['operation'].startswith(NEVER))


TARGET_KEYS = ('path', 'to', 'name', 'id', 'window', 'sheet', 'object')


def _resolved(value, step):
    """The arguments that name a step's targets: as planned when none comes from an earlier step (the text it writes may
    still wait for one); else resolved from the outputs of the steps done; None when a target is not known yet."""
    a = step.get('arguments') if isinstance(step.get('arguments'), dict) else {}
    fixed = {k: a[k] for k in TARGET_KEYS if k in a}
    if fixed and not _has_reference(fixed):return fixed
    from . import assignments
    try:return assignments._resolve(a, assignments._outputs(value))
    except Exception:  # noqa: BLE001 - an input from a step not done yet: its target is not known now
        return None


def authorise(kernel, ident, principal, runner=False):
    """assignments.AUTHORISE, called by K1 outside its own transactions (when a plan is made, and when the runner reaches
    its next step): each proposed change that a grant of yours in force covers (never one that always asks, the model's
    pick alone, or one marked for your approval) is authorised by that grant, and the journal says so. With runner: a
    proposed change no grant covers, the one the runner has reached, stops: "needs your grant", with what it would do and
    where. Nothing is sent by this. Everything is read first; the record is written in one short transaction after."""
    from . import assignments as A
    try:
        with kernel.db() as db:
            value = A._load(db, ident, principal)
    except ValueError:
        return []
    if value['state'] != A.OPEN:return []      # running, held, stopped or done: nothing is authorised meanwhile
    nxt = A._next(value);plans = {}
    for step in value['steps']:
        if step['status'] != 'proposed' or not _grantable(step):continue
        if not _from_the_owner(kernel, step, principal):continue      # 1.0 K8: an address from a page waits for your press
        arguments = _resolved(value, step)
        if arguments is None:continue
        never = _never(kernel, step['operation'], arguments)  # 1.0 L6: outside your home it stops, before any grant is asked for
        if never:
            if runner and nxt is not None and step['key'] == nxt['key']:plans[step['key']] = ('never', never, A.digest(step['arguments']))
            continue
        grant = covering(kernel, principal.identity, step['operation'], arguments, value['id'], include_built_in=False)
        if grant is not None:
            plans[step['key']] = ('grant', grant, A.digest(step['arguments']))
        elif runner and nxt is not None and step['key'] == nxt['key']:
            plans[step['key']] = ('needs', _why(kernel, principal.identity, step['operation'], arguments, value['id']),
                                  step_request(kernel, value, step, arguments), A.digest(step['arguments']))
    if not plans:return []
    said = []
    with A._writing(kernel) as db:
        value = A._load(db, ident, principal)
        if value['state'] != A.OPEN:return []
        for step in value['steps']:
            plan = plans.get(step['key'])
            if plan is None or step['status'] != 'proposed' or A.digest(step['arguments']) != plan[-1]:continue
            if plan[0] == 'grant':
                grant = plan[1]
                step.update(status='authorised', reason='', authorised={'by': 'grant:' + grant['id'], 'grant': grant['id'], 'at': time.time(),
                                                                       'explicit': False, 'arguments': plan[2], 'again': False})
                words = 'Step %d (%s) is authorised by your grant: %s.' % (step['n'], step['title'], grant['words'])
                A._save(db, value);A._journal(db, value, step, 'AUTHORISED', words, {'grant': grant['id'], 'by_grant': True})
            elif plan[0] == 'never':  # 1.0 L6
                step.update(status='blocked', reason=plan[1])
                words = 'Step %d (%s) stops: %s. Nothing was sent.' % (step['n'], step['title'], plan[1])
                A._save(db, value);A._journal(db, value, step, 'BLOCKED', words)
            else:
                step.update(status='blocked', reason=NEEDS + plan[1])
                words = 'Step %d (%s) needs your grant: %s. Nothing was sent.' % (step['n'], step['title'], plan[1])
                A._save(db, value);A._journal(db, value, step, 'NEEDS_GRANT', words, {'needs': plan[2]})
            said.append(words)
    return said


def step_request(kernel, value, step, arguments=None):
    """The grant one press would give for this step ("Grant this for this assignment"): its operation on its exact target
    (a file's folder, or the object), for this assignment; None when it names no target or a grant can never cover it."""
    if not _grantable(step):return None
    arguments = arguments if arguments is not None else _resolved(value, step)
    if arguments is None:return None
    found = targets(step['operation'], arguments)
    args = {'operation': step['operation'], 'scope': 'assignment', 'assignment': value['id']}
    if found['paths'] and not found['objects']:
        folders = {p.rsplit('/', 1)[0] if '/' in p else '' for p in found['paths'] if p is not None}
        if len(folders) != 1 or '' in folders:return None
        args['folder'] = folders.pop()
    elif found['objects'] and not found['paths'] and len(set(found['objects'])) == 1:
        args['object'] = found['objects'][0]
    else:
        return None
    return args


def one_press(kernel, value, nxt, principal):
    """assignments.GRANT_ACTION: the press offered for a step that needs your grant, as a call with the words you read."""
    if nxt is None or nxt.get('status') != 'blocked' or not str(nxt.get('reason', '')).startswith(NEEDS):return None
    args = step_request(kernel, value, nxt)
    if args is None:return None
    try:shown = describe(kernel, args, principal)
    except (ValueError, KeyError):return None
    return {'words': ONE_PRESS, 'operation': 'grant.give', 'yours': True, 'grant_words': shown['words'],
            'arguments': dict(args, expected_digest=shown['digest'], step=nxt['key']),
            'then': {'operation': 'assignment.step', 'arguments': {'id': value['id'], 'until': 'end'}}}


def _authorise_named(kernel, assignment, key, principal):
    """After a one-press grant: that step, no longer waiting for a grant, is authorised by the new grant when it covers it
    (the caller carries on)."""
    from . import assignments as A
    with A._writing(kernel) as db:
        value = A._load(db, assignment, principal)
        step = next((s for s in value['steps'] if s['key'] == key), None)
        if step is None:raise ValueError('There is no step %s' % key)
        if step['status'] == 'blocked' and str(step.get('reason', '')).startswith(NEEDS):
            step.update(status='proposed', reason='');A._save(db, value)
    said = authorise(kernel, assignment, principal)
    with kernel.db() as db:
        value = A._load(db, assignment, principal)
    step = next(s for s in value['steps'] if s['key'] == key)
    if step['status'] != 'authorised':said.append('Step %d is not covered by that grant: it waits for your word.' % step['n'])
    return said


# ---------------------------------------------------------------- reading them

def _uses(db, ident):
    if not _present(db):return 0, None
    row = db.execute('SELECT count(*), max(at) FROM kas_grant_uses WHERE grant_id=?', (ident,)).fetchone()
    return int(row[0] or 0), row[1]


def _view(value, kernel=None, db=None, cache=None):
    out = {k: value.get(k) for k in ('id', 'operation', 'doing', 'operations', 'target', 'scope', 'words', 'given', 'source', 'ended')}
    out['built_in'] = bool(value.get('built_in'))
    out['scope_words'] = scope_words(value['scope'])
    out['given_words'] = _when(value['given']) if value.get('given') else 'from the start'
    if kernel is not None:
        why = live(kernel, value, cache=cache) if not value.get('built_in') else ''
        out['in_force'] = not why;out['ended_words'] = why
    if db is not None and not value.get('built_in'):
        out['uses'], last = _uses(db, value['id'])
        out['last_used'] = _when(last) if last else ''
    return out


def listing(kernel, args, principal):
    cache = {}
    with kernel.db() as db:
        rows = _rows(db, principal.identity, every=bool(args.get('all')))
        views = [_view(r, kernel, db, cache) for r in rows]
    if args.get('assignment'):
        views = [v for v in views if v['scope']['kind'] != 'assignment' or v['scope'].get('assignment') == args['assignment']]
    force = [v for v in views if v.get('in_force')]
    ended = [v for v in views if not v.get('in_force')]
    waiting = []
    try:
        from . import assignments
        rows = assignments.listing(kernel, {'open': True, 'limit': 20}, principal)['assignments'] if args.get('waiting', True) else []
        for row in rows:
            for action in row.get('actions') or ():
                if action.get('operation') == 'grant.give':
                    waiting.append({'assignment': row['id'], 'title': row['title'], 'line': row['line'], 'words': action.get('grant_words', ''),
                                    'press': action})
    except Exception:  # noqa: BLE001 - the list of grants is shown even when assignments cannot be read
        pass
    return {'schema': SCHEMA, 'in_force': force, 'ended': ended if args.get('all') else [], 'own_area': _view(built_in(principal.identity)),
            'waiting': waiting, 'families': {k: v[0] for k, v in FAMILIES.items()},
            'rule': 'A grant is given only by your press, in these words; she can never give or widen one. Reading needs no grant; '
                    'what always asks still asks; a change only the model chose is never done; Undo stays as it was.'}


def dispatch(kernel, op, args, principal):
    try:
        if op == 'grant.words':return describe(kernel, args, principal)
        if op == 'grant.give':return give(kernel, args, principal)
    except NotGrantable as why:
        if op == 'grant.words':return {'schema': SCHEMA, 'grantable': False, 'why_not': str(why).split(': ', 1)[-1], 'code': str(why).split(':', 1)[0]}
        raise
    if op == 'grant.list':return listing(kernel, args, principal)
    if op == 'grant.revoke':return revoke(kernel, args, principal)
    raise ValueError('Unknown grant operation')


# ---------------------------------------------------------------- wiring (the hooks K1 and K2 left for this slice)

def install():
    from . import assignments, tools_registry
    assignments.GRANT_CHECK = check_step
    assignments.GRANTED = step_in_force
    assignments.AUTHORISE = authorise
    assignments.GRANT_ACTION = one_press
    tools_registry.GRANT_CHECK = check_tool
    tools_registry.GRANTED = tool_in_force
    if 'NEEDS_GRANT' not in assignments.EFFECT_ENTRIES:
        assignments.EFFECT_ENTRIES = assignments.EFFECT_ENTRIES + ('NEEDS_GRANT',)
    assignments.SAYS.setdefault('NEEDS_GRANT', 'needs your grant')


install()
