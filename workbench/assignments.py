"""Assignments and the journal: an objective in your words, a plan of steps, and a record of every effect (Graphite 1.0, K1).

The owner's paper, sections 12 and 13: a serious assignment is a durable plan of steps, each with a status (proposed,
authorised, running, done, blocked, needs review). A step is done only when its effect is verified ("the new revision is on
disk"), never because a command was sent. A crash, a suspend or a Stop leaves a journal of which effects occurred and which
were only prepared, and on resume she inspects what is already there before she repeats anything.

What an assignment holds (graphite.assignment/1, in the Kernel's own database: asg_assignments, asg_journal):

  objective   the owner's words, as they gave them.
  steps       each: the tool and its Kernel operation (a registered one; nothing else runs); its inputs, each with where it
              came from (a span of your words, a record at a revision, a source line, a deduction, or the output of an earlier
              step); the expected output (in words, the named values later steps read, and checks on them); how its effect is
              verified; the grant it needs; its status; the time it should take (her clock's estimate).
  journal     append-only, one row per event. PREPARED is written and committed before an effect is sent; SENT when the call
              came back; DONE with the observation that proves it, or NOT_VERIFIED. The owner's words are in it too
              (AUTHORISED, STOPPED, RESUMED) and so is every inspection on resume (STILL_DONE, FOUND_DONE, NOT_FOUND).

Operations (registered in engineering_kernel under "1.0 K1"; reads are observers, so showing them is not an event):

  assignment.start   {objective, title?, steps?}                     execute  a new assignment; the steps given are proposed
  assignment.plan    {id, steps?, authorise?, expected_digest?}      execute  propose steps (those not started are replaced);
                                                                              authorise is your press: it needs the approve
                                                                              scope and the digest of the plan you saw
  assignment.step    {id, until?}                                    execute  run the next authorised step ('next', the default)
                                                                              or carry on until a step needs you ('end')
  assignment.status  {id}                                            read     the assignment, its steps, its journal, time left
  assignment.stop    {id}                                            execute  stopped by you: nothing more starts; a call in
                                                                              flight is recorded as it ends, never hidden
  assignment.resume  {id, carry_on?}                                 execute  inspect every step's output, then carry on
  assignment.list    {limit?, offset?, open?}                        read     your assignments, newest first

The rules the code keeps (her rules: the model proposes, the system disposes):
  - A read never asks: a read step is authorised as it is planned. A change waits for your press (assignment.plan with
    authorise). "all" never covers a change whose only basis is the model's pick (stacy_hand's pick, never write), one that
    always asks (stacy_hand.ALWAYS_ASKS: sending out, deleting, stopping) or one the records mark for your approval: each of
    those is authorised by its own name or not at all.
  - Every input says where it came from (stacy_hand.origin: never the model's words) or names an earlier step's output.
  - A step runs with only the scope its operation needs ({read, that scope}), through Kernel.dispatch like any caller.
  - Before an effect is sent its expected output is looked for: an effect already made is recorded, not made twice.
  - No floating point in anything checked: time is whole milliseconds, progress whole percent, values compared as text or
    Decimal.

Reused, not duplicated:
  - The Night Shift's gate (work_trail.work_status: held and its epoch): Stop all and HALT hold her managed work, and an
    assignment never starts an effect while work is held, nor carries on across a hold.
  - The Night Shift's discipline (continuing_work): an intent is written before the effect and the outcome after it; step
    references are the same {"$step", "path"} values; resume is explicit and inspects before it repeats.
  - The Agenda (agenda.view): an assignment that waits for you shows among its WAITING rows, a running one under NOW.
  - Her hand (stacy_hand): the origins of inputs, the bases of a change and what always asks.
  - Her clock (brain_clock): estimates are rolling medians of measured times (its WINDOW and LEAST), and a step that is a
    model turn is priced by the clock itself.
  Night Shift work orders stay as they are (working copies, frozen calls, one grant); an assignment may use their
  operations as steps.

Hooks for the slices after this one: GRANT_CHECK (K3: a callable(kernel, assignment, step, arguments, principal) that
returns '' or why the step needs a grant; such a step is blocked, "needs your grant"), CHECKS (K2: the check of an
operation's effect, by operation name), and active_work() for her column's ACTIVE WORK (P1).
"""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import threading
import time
import uuid
from decimal import Decimal, InvalidOperation

SCHEMA = 'graphite.assignment/1'
STATUSES = ('proposed', 'authorised', 'running', 'done', 'blocked', 'needs review')
OPEN, RUNNING, STOPPED, HELD, DONE = 'open', 'running', 'stopped', 'held', 'done'
STOPPED_BY_YOU = 'stopped by you'
MAX_STEPS = 32
MAX_ARGUMENTS = 65536        # bytes of one step's arguments, canonical
MAX_OUTPUT = 16384           # bytes of one step's named outputs and observation
JOURNAL_SHOWN = 200          # journal rows a status carries
NOT_HERE = ('assignment.', 'ledger.work.', 'jobs.recover', 'remote.disable', 'grant.', 'halt.')   # never a step: her own controls and the owner's (1.0 K3: grants and HALT)
KEY_RE = re.compile(r'^[a-z][a-z0-9_]{0,31}$')
FIELD_RE = re.compile(r'\{([a-z][a-z0-9_]{0,31})\}')
GRANT_CHECK = None           # K3 sets it: callable(kernel, assignment, step, arguments, principal) -> '' or why
# 1.0 K3 (grants and HALT): grants.install() sets these. GRANTED(kernel, assignment, step, arguments, principal) -> the context
# around a step's own dispatch (the permit Files reads); AUTHORISE(kernel, id, principal, runner) authorises the proposed
# steps a grant covers, or stops the reached one "needs your grant" (called outside this module's transactions);
# GRANT_ACTION(kernel, assignment, next step, principal) -> the one press for a step that needs your grant, or None.
GRANTED = None
AUTHORISE = None
GRANT_ACTION = None
DIALOG_WATCH = None          # 1.0 K7 sets it (a11y_reader.DialogWatch): mark() before a change is sent, notice() after its check: a
                             # dialog that appeared in a program meanwhile ({'words', 'dialogs', 'receipts'}); the step then needs review

ID = {'type': 'string', 'minLength': 32, 'maxLength': 32}
SHA = {'type': 'string', 'minLength': 64, 'maxLength': 64}
STEPS = {'type': 'array', 'items': {'type': 'object'}}
FIELDS = {
    'assignment.start': ({'objective': {'type': 'string', 'minLength': 1, 'maxLength': 4000},
                          'title': {'type': 'string', 'minLength': 1, 'maxLength': 200}, 'steps': STEPS}, ['objective']),
    'assignment.plan': ({'id': ID, 'steps': STEPS, 'expected_digest': SHA,
                         'authorise': {'type': 'array', 'items': {'type': 'string', 'minLength': 1, 'maxLength': 32}}}, ['id']),
    'assignment.step': ({'id': ID, 'until': {'type': 'string', 'enum': ['next', 'end']}}, ['id']),
    'assignment.status': ({'id': ID}, ['id']),
    'assignment.stop': ({'id': ID, 'why': {'type': 'string', 'enum': ['halt']}}, ['id']),  # 1.0 K3: why, when HALT stops it
    'assignment.resume': ({'id': ID, 'carry_on': {'type': 'boolean'}}, ['id']),
    'assignment.list': ({'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100},
                         'offset': {'type': 'integer', 'minimum': 0, 'maximum': 100000}, 'open': {'type': 'boolean'}}, []),
}
SCOPES = {'assignment.start': 'execute', 'assignment.plan': 'execute', 'assignment.step': 'execute', 'assignment.status': 'read',
          'assignment.stop': 'execute', 'assignment.resume': 'execute', 'assignment.list': 'read'}
OBSERVERS = ('assignment.status', 'assignment.list')

# The tool an operation belongs to, in the words the window uses.
TOOL_WORDS = {'office': 'Sheets', 'documents': 'Pages', 'files': 'Files', 'field': 'the desk', 'investigation': 'Investigations',
              'library': 'the Library', 'references': 'the Library', 'math': 'the calculator', 'intake': 'Bring in',
              'agenda': 'the Agenda', 'programs': 'Apps', 'work': 'the Night Shift', 'changes': 'Changes', 'goals': 'Goals',
              'quotes': 'Quotes', 'rules': 'Rules', 'words': 'Words', 'brain': 'her model', 'voice': 'her voice'}
# What a change does, in the words of its grant (any other: "use <tool> (<operation>)").
GRANT_WORDS = {'files.write': 'write a file', 'files.mkdir': 'make a folder', 'files.cells': 'change cells of a workbook',
               'office.datasheet.recheck': 'work a calculation again', 'field.set': 'set a value on a sheet',
               'documents.create': 'make a page', 'documents.save': 'save a page', 'investigation.claim': 'add a finding',
               'investigation.continue': 'run an investigation\'s checks', 'agenda.add': 'add to the Agenda'}
# A model turn, priced by her clock: operation -> the clock's kind.
CLOCK_KINDS = {'library.ask': 'ASK', 'library.table': 'COLUMNS', 'library.read': 'MARKS'}

MIGRATIONS = [(1, (
    'CREATE TABLE asg_assignments(id TEXT PRIMARY KEY, owner TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL, '
    'payload TEXT NOT NULL, digest TEXT NOT NULL, updated REAL NOT NULL)',
    'CREATE INDEX asg_owner ON asg_assignments(owner, updated)',
    'CREATE TABLE asg_journal(seq INTEGER PRIMARY KEY AUTOINCREMENT, assignment TEXT NOT NULL, step TEXT NOT NULL, '
    'operation TEXT NOT NULL, entry TEXT NOT NULL, words TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL, at REAL NOT NULL)',
    'CREATE INDEX asg_journal_of ON asg_journal(assignment, seq)',
    'CREATE INDEX asg_journal_timing ON asg_journal(operation, entry, seq)',
))]


class NotVerified(ValueError):
    """The effect was sent and its check did not find it: the step needs review, it is not done."""


class Unknowable(ValueError):
    """Graphite cannot tell whether an effect was made: it is never repeated blindly."""


class Blocked(ValueError):
    """A step cannot start: its inputs or its preconditions do not hold. Nothing was sent."""


# ---------------------------------------------------------------- records

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _now_ms():
    return time.monotonic_ns() // 1000000


def ensure(db):
    """Forward-only migrations of this slice's tables; other Kernel tables are left alone."""
    if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS asg_migrations(version INTEGER PRIMARY KEY, digest TEXT NOT NULL, applied REAL NOT NULL)')
    applied = dict(db.execute('SELECT version, digest FROM asg_migrations'))
    known = {version: digest(list(sql)) for version, sql in MIGRATIONS}
    if any(known.get(v) != d for v, d in applied.items()) or sorted(applied) != list(range(1, len(applied) + 1)):
        raise ValueError('ASSIGNMENT_MIGRATION_UNSUPPORTED: use a compatible program')
    for version, statements in MIGRATIONS:
        if version in applied:continue
        for statement in statements:db.execute(statement)
        db.execute('INSERT INTO asg_migrations VALUES(?,?,?)', (version, known[version], time.time()))


def _present(db):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='asg_journal'").fetchone() is not None


@contextlib.contextmanager
def _writing(kernel):
    """One short transaction that may change this slice's tables (never held across a Kernel call)."""
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');ensure(db)
        yield db


def _ident(value):
    if not isinstance(value, str) or len(value) != 32 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('Invalid identifier')
    return value


def _load(db, ident, principal):
    _ident(ident)
    row = db.execute('SELECT payload, digest, state, revision FROM asg_assignments WHERE id=? AND owner=?',
                     (ident, principal.identity)).fetchone() if _present(db) else None
    if not row:raise ValueError('ASSIGNMENT_UNAVAILABLE: there is no such assignment of yours')
    value = json.loads(row[0])
    if digest(value) != row[1] or value.get('state') != row[2] or value.get('revision') != row[3]:
        raise ValueError('ASSIGNMENT_DAMAGED: its record does not match its digest')
    return value


def _save(db, value, new=False):
    before = value.get('revision', 0)
    value['revision'] = before + 1;value['updated'] = time.time()
    raw = canonical(value);sha = hashlib.sha256(raw.encode()).hexdigest()
    if new:
        db.execute('INSERT INTO asg_assignments VALUES(?,?,?,?,?,?,?)',
                   (value['id'], value['owner'], value['state'], value['revision'], raw, sha, value['updated']))
    elif db.execute('UPDATE asg_assignments SET state=?, revision=?, payload=?, digest=?, updated=? WHERE id=? AND revision=?',
                    (value['state'], value['revision'], raw, sha, value['updated'], value['id'], before)).rowcount != 1:
        raise ValueError('ASSIGNMENT_CHANGED: it changed meanwhile; read it again')
    return value


def _journal(db, value, step, entry, words, detail=None):
    """One journal row: committed with the change it records, in the same transaction."""
    payload = {'entry': entry, 'step': step['key'] if step else '', 'words': words, 'detail': detail or {},
               'revision': value['revision']}
    if len(canonical(payload).encode()) > 4 * MAX_OUTPUT:payload['detail'] = {'note': 'detail too long to keep; its digest',
                                                                              'digest': digest(detail)}
    row = db.execute('INSERT INTO asg_journal(assignment, step, operation, entry, words, payload, digest, at) VALUES(?,?,?,?,?,?,?,?)',
                     (value['id'], payload['step'], step['operation'] if step else '', entry, words, canonical(payload), digest(payload),
                      time.time()))
    # 1.0 K2: the row's observation receipts (dispatched, verified, ...), in the same transaction, linked by the row's number
    try:
        from . import tools_registry
        tools_registry.journalled(db, value, step, entry, payload, row.lastrowid)
    except Exception:  # noqa: BLE001 - a receipt that cannot be written never undoes the journal row: the row is the record
        pass
    return row.lastrowid  # 1.0 K7: the row's number, for receipts written with it


def _watch(kind, *args):
    """1.0 K7: the dialog watch (DIALOG_WATCH), when it is here. A watch that fails never changes what the step did."""
    if DIALOG_WATCH is None:return None
    try:return getattr(DIALOG_WATCH, kind)(*args)
    except Exception:  # noqa: BLE001
        return None


def _entries(db, ident, limit=None):
    if not _present(db):return []
    rows = db.execute('SELECT seq, step, entry, words, payload, digest, at FROM asg_journal WHERE assignment=? ORDER BY seq', (ident,)).fetchall()
    out = []
    for seq, step, entry, words, payload, sha, at in rows:
        value = json.loads(payload)
        out.append({'seq': seq, 'step': step, 'entry': entry, 'words': words, 'detail': value.get('detail') or {}, 'at': at,
                    'intact': digest(value) == sha})
    return out[-limit:] if limit else out


# ---------------------------------------------------------------- the plan's steps

def _references(value, found=None):
    """The earlier steps a value reads ({'$step': key, 'path': [...]}, and those inside {'$text': ..., 'with': {...}})."""
    found = set() if found is None else found
    if isinstance(value, dict):
        if '$step' in value:
            if set(value) != {'$step', 'path'} or not isinstance(value['path'], list) or len(value['path']) > 12 \
                    or any(not isinstance(p, str) or len(p) > 100 for p in value['path']):
                raise ValueError('PLAN_REFERENCE: an earlier step is read as {"$step": its key, "path": [names]}')
            found.add(value['$step'])
        elif '$text' in value:
            if set(value) != {'$text', 'with'} or not isinstance(value['$text'], str) or not isinstance(value['with'], dict):
                raise ValueError('PLAN_TEXT: a text made from earlier outputs is {"$text": "... {name} ...", "with": {name: value}}')
            names = set(FIELD_RE.findall(value['$text']))
            if names - set(value['with']):raise ValueError('PLAN_TEXT: %s is named in the text and not given' % sorted(names - set(value['with']))[0])
            for item in value['with'].values():_references(item, found)
        else:
            for item in value.values():_references(item, found)
    elif isinstance(value, list):
        for item in value:_references(item, found)
    return found


def _pick(value, path):
    for part in path:
        if isinstance(value, dict) and part in value:value = value[part]
        elif isinstance(value, list) and part.isdecimal() and int(part) < len(value):value = value[int(part)]
        else:raise ValueError('the value at %s is not there' % '/'.join(path))
    return value


def _words_of(value):
    if isinstance(value, bool) or value is None:return canonical(value)
    if isinstance(value, (str, int)):return str(value)
    if isinstance(value, float):raise ValueError('a value with a floating point is not put into words here')
    return canonical(value)


def _resolve(value, outputs):
    """Arguments with earlier steps' outputs put in (outputs: {key: {name: value}})."""
    if isinstance(value, dict):
        if '$step' in value:
            if value['$step'] not in outputs:raise Blocked('it reads step %s, which is not done' % value['$step'])
            try:return json.loads(canonical(_pick(outputs[value['$step']], value['path'])))
            except ValueError as missing:raise Blocked('step %s did not give it: %s' % (value['$step'], missing)) from None
        if '$text' in value:
            given = {k: _resolve(v, outputs) for k, v in value['with'].items()}
            return FIELD_RE.sub(lambda m: _words_of(given[m.group(1)]), value['$text'])
        return {k: _resolve(v, outputs) for k, v in value.items()}
    if isinstance(value, list):return [_resolve(v, outputs) for v in value]
    return value


def _from_words(origin):
    """Where an input came from, in words."""
    kind = origin.get('kind')
    if kind == 'STEP':
        ns = origin.get('numbers') or origin.get('steps') or []
        return ('the output of step ' if len(ns) == 1 else 'the outputs of steps ') + _numbers(ns)
    if kind == 'OWNER_WORDS':return 'your words: "%s"' % origin.get('text', '')
    if kind == 'RECORD':return 'the record %s at revision %s%s' % (origin['id'], str(origin['rev'])[:12], (', cell ' + origin['cell']) if origin.get('cell') else '')
    if kind == 'SOURCE':return 'line %d of %s at revision %s%s' % (origin['line'], origin['id'], str(origin['rev'])[:12], ' (a line the doorway flagged)' if origin['flagged'] else '')
    if kind == 'DEDUCTION':return 'a deduction: ' + origin['proof']
    return 'the plan'


def _target(operation, arguments):
    """What a step's effect lands on, and the words for it: a folder in Files, or a record; ('', '') when the earlier steps
    give it."""
    path, ident = arguments.get('path'), arguments.get('id')
    if isinstance(path, str):
        folder = path.rsplit('/', 1)[0] + '/' if '/' in path else ''
        return 'files:' + folder, ('in Files, in ' + folder) if folder else 'in Files, at the top'
    if isinstance(ident, str):return ident, 'on the record ' + ident
    return '', ''


def _tool(operation):
    head = operation.split('.', 1)[0]
    return TOOL_WORDS.get(head, head.replace('_', ' ').capitalize())


def _plan_step(source, objective, earlier, index):
    """One proposed step, checked and completed; refuses what cannot be a step. `earlier`: the keys before it."""
    from .engineering_kernel import CAPABILITIES
    from . import stacy_hand
    if not isinstance(source, dict):raise ValueError('PLAN_STEP: a step is an object')
    allowed = {'key', 'title', 'operation', 'arguments', 'origins', 'outputs', 'expected', 'require', 'basis', 'estimate_ms', 'tool_key'}  # 1.0 K2: tool_key
    if set(source) - allowed:raise ValueError('PLAN_STEP: a step does not take %s' % sorted(set(source) - allowed)[0])
    key = source.get('key') or 's%d' % index
    if not isinstance(key, str) or not KEY_RE.match(key):raise ValueError('PLAN_KEY: a step key is a short lower-case name')
    if key in earlier:raise ValueError('PLAN_KEY: %s is used twice' % key)
    operation = source.get('operation')
    if not isinstance(operation, str) or operation not in CAPABILITIES:
        raise ValueError('PLAN_OPERATION: %s is not a registered operation; nothing else runs' % str(operation)[:80])
    if operation.startswith(NOT_HERE):raise ValueError('PLAN_OPERATION: %s is not a step of an assignment' % operation)
    tool_key = source.get('tool_key')  # 1.0 K2: the registry's tool the step uses (its preconditions); it must go through this operation
    if tool_key is not None:
        from . import tools_registry
        tool = tools_registry.entry(tool_key)
        if operation not in tools_registry.members(tool) or tool.family == 'desk':
            raise ValueError('PLAN_TOOL: the tool %s does not go through %s' % (str(tool_key)[:64], operation))
    scope = CAPABILITIES[operation]
    arguments = source.get('arguments', {})
    if not isinstance(arguments, dict):raise ValueError('PLAN_ARGUMENTS: arguments are named')
    if len(canonical(arguments).encode()) > MAX_ARGUMENTS:raise ValueError('PLAN_ARGUMENTS: too long')
    refs = _references(arguments)
    if refs - set(earlier):raise ValueError('PLAN_REFERENCE: step %s reads %s, which does not come before it' % (key, sorted(refs - set(earlier))[0]))
    if scope == 'approve' and refs:
        raise ValueError('PLAN_APPROVAL: %s is marked for your approval, so its inputs are fixed when you authorise it' % operation)
    if not refs:
        from .engineering_cli import schemas
        from .agent_operations import validate
        validate(arguments, schemas()[operation])
    origins = source.get('origins') or {}
    if not isinstance(origins, dict):raise ValueError('PLAN_ORIGINS: origins are named by argument')
    inputs = {}
    for name, value in arguments.items():
        mine = sorted(_references(value), key=earlier.index)
        if mine:
            inputs[name] = {'origin': {'kind': 'STEP', 'steps': mine, 'numbers': [earlier.index(k) + 1 for k in mine]}};continue
        given = origins.get(name)
        if not isinstance(given, dict):raise stacy_hand.NoOrigin('ORIGIN_MISSING: %s of step %s does not say where it came from' % (name, key))
        checked = stacy_hand.origin(given.get('kind'), **{k: v for k, v in given.items() if k != 'kind'})
        if checked['kind'] == 'OWNER_WORDS':
            if checked['end'] > len(objective):raise stacy_hand.NoOrigin('ORIGIN_SPAN: the span is past the end of your words')
            said = objective[checked['start']:checked['end']]
            if 'text' in checked and checked['text'] != said:raise stacy_hand.NoOrigin('ORIGIN_SPAN: the span does not say "%s"' % checked['text'][:60])
            checked['text'] = said
        inputs[name] = {'value': value, 'origin': checked}
    for name in inputs:inputs[name]['from'] = _from_words(inputs[name]['origin'])
    outputs = source.get('outputs') or {}
    if not isinstance(outputs, dict) or len(outputs) > 16 or any(
            not KEY_RE.match(str(n)) or not isinstance(p, list) or not 1 <= len(p) <= 12 or any(not isinstance(x, str) for x in p)
            for n, p in outputs.items()):
        raise ValueError('PLAN_OUTPUTS: an output is a short name and the path of names to its value')
    require = source.get('require') or []
    if not isinstance(require, list) or len(require) > 16 or any(
            not isinstance(r, dict) or set(r) != {'path', 'equals'} or not isinstance(r['path'], list) for r in require):
        raise ValueError('PLAN_REQUIRE: a check is {"path": [names], "equals": a value or an earlier output}')
    if _references(require) - set(earlier):raise ValueError('PLAN_REQUIRE: a check reads a step that does not come before it')
    basis = source.get('basis', stacy_hand.OWNER_WORDS)
    if basis not in stacy_hand.BASES:raise ValueError('PLAN_BASIS: %s is not why a step is on the table' % str(basis)[:40])
    estimate = source.get('estimate_ms')
    if estimate is not None and (type(estimate) is not int or not 0 < estimate <= 86400000):
        raise ValueError('PLAN_ESTIMATE: an estimate is whole milliseconds')
    check = check_for(operation)
    always = stacy_hand.why_asks(operation, arguments) if scope != 'read' else ''
    target, where = _target(operation, arguments)
    title = source.get('title') or '%s: %s' % (_tool(operation), operation)
    if scope == 'read':grant = {'needs': 'none', 'words': 'none: reading needs no grant'}
    else:
        doing = GRANT_WORDS.get(operation, 'use %s (%s)' % (_tool(operation), operation))
        grant = {'needs': 'grant', 'operation': operation, 'target': target or 'what the earlier steps give', 'scope': 'this assignment',
                 'words': '%s %s, for this assignment' % (doing, where or 'on what the earlier steps give')}
        if scope == 'approve':grant['words'] += ' (the records mark it for your approval)'
        if always:grant['words'] += ' (it always asks: %s)' % always
    if not isinstance(source.get('expected', ''), str) or len(source.get('expected', '')) > 400:raise ValueError('PLAN_EXPECTED: in words, short')
    return {'key': key, 'n': index, 'title': str(title)[:200], 'tool': _tool(operation), 'operation': operation, 'scope': scope,
            'arguments': arguments, 'inputs': inputs, 'outputs': outputs, 'require': require,
            'expected': source.get('expected') or check.expected, 'verify': {'kind': check.kind, 'words': check.how},
            'effect': check.effect, 'grant': grant, 'basis': basis, 'always_asks': always, 'estimate_ms': estimate,
            **({'tool_key': tool_key} if tool_key is not None else {}),  # 1.0 K2
            'status': 'authorised' if scope == 'read' else 'proposed', 'reason': '',
            'authorised': {'by': 'a read never asks', 'at': time.time(), 'explicit': False} if scope == 'read' else None,
            'prepared': None, 'resolved': None, 'observation': None, 'output': None, 'runner': None, 'attempts': 0,
            'elapsed_ms': None, 'estimate_now_ms': None, 'started': None, 'started_ns': None, 'finished': None}


def _definition(step):
    return {k: step[k] for k in ('key', 'title', 'operation', 'arguments', 'inputs', 'outputs', 'require', 'expected', 'basis', 'grant')
            + (('tool_key',) if step.get('tool_key') else ())}  # 1.0 K2: the tool, when the plan names it


def plan_digest(value):
    """The digest of the plan as it is shown to you: the objective and each step's definition (not its status)."""
    return digest({'objective': value['objective'], 'steps': [_definition(s) for s in value['steps']]})


def _started(step):
    return step['status'] in ('running', 'done', 'needs review') or step['prepared'] is not None


# ---------------------------------------------------------------- the checks of an effect (K2 widens CHECKS)

def _file_sha(kernel, rel):
    from . import files_service
    path = files_service.resolve(kernel, rel, must_exist=False)
    if not path.is_file():return None
    digest_ = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):digest_.update(block)
    return digest_.hexdigest()


NUMBER_RE = re.compile(r'^[+-]?\d+(\.\d+)?$')


def _same_number(a, b):
    """Two values written as text: the same number (exactly, as Decimal) when both are plain numbers, else the same text."""
    a, b = str(a).strip(), str(b).strip()
    if NUMBER_RE.match(a) and NUMBER_RE.match(b):
        try:return Decimal(a) == Decimal(b)
        except InvalidOperation:pass
    return a == b


class Check:
    """An operation Graphite has no check for: it can be sent, never called done. Resume cannot tell whether it was made."""
    kind = 'none';effect = 'an effect Graphite cannot check yet';standin_ms = 5000;repeatable = False
    how = 'Graphite has no check for this effect yet: it can be sent, not verified'
    expected = 'what the operation returns'

    def prepare(self, kernel, read, arguments):return {}

    def find(self, kernel, read, arguments, prepared):
        raise Unknowable('Graphite cannot tell whether it was done, so it is not done again: it is yours to look at')

    def verify(self, kernel, read, arguments, result, prepared, step):
        raise NotVerified('sent; Graphite has no check for this effect yet, so it is not called done')

    def still(self, kernel, read, step):
        return ''


class ReadCheck(Check):
    """A read: no effect. Verified by reading again and finding the same revision (or the same values)."""
    kind = 'read';effect = 'nothing (a read)';standin_ms = 1000;repeatable = True
    how = 'read again: the same revision'
    expected = 'what it reads, at the revision it was read'

    @staticmethod
    def identity(result, step):
        if isinstance(result, dict):
            for holder in (result, result.get('document') if isinstance(result.get('document'), dict) else {}):
                rev = holder.get('revision')
                if isinstance(rev, (str, int)) and not isinstance(rev, bool):return 'revision', rev
        if step.get('outputs'):
            try:return 'values', digest({n: _pick(result, p) for n, p in step['outputs'].items()})
            except ValueError:pass
        return 'digest', digest(result)

    def find(self, kernel, read, arguments, prepared):
        return None                                   # a read is simply read again

    def verify(self, kernel, read, arguments, result, prepared, step):
        how, first = self.identity(result, step)
        again = read(step['operation'], arguments)
        if self.identity(again, step) != (how, first):raise NotVerified('it changed while it was being read; read it again')
        return {'object': _object(step['operation'], arguments), 'revision': first, 'by': how, 'digest': digest(result),
                'complete': True, 'how': 'observed', 'words': 'read, and read again: the same %s' % ('revision' if how == 'revision' else 'values')}

    def still(self, kernel, read, step):
        obs = step['observation'] or {}
        try:again = read(step['operation'], step['resolved'])
        except ValueError as gone:return 'it cannot be read now (%s)' % str(gone)[:200]
        how, now = self.identity(again, step)
        if (how, now) != (obs.get('by'), obs.get('revision')):return 'it has changed since it was read (%s %s, was %s)' % (how, str(now)[:12], str(obs.get('revision'))[:12])
        return ''


class FileWrite(Check):
    """files.write: done when the file on disk has the digest of the prepared text."""
    kind = 'file';effect = 'a file written';standin_ms = 1000;repeatable = True
    how = 'the file on disk has the digest of the text prepared for it'
    expected = 'the file, holding exactly the prepared text'

    def prepare(self, kernel, read, arguments):
        text = arguments['text'].encode('utf-8')
        return {'path': arguments['path'], 'sha256': hashlib.sha256(text).hexdigest(), 'bytes': len(text),
                'before': _file_sha(kernel, arguments['path'])}

    def find(self, kernel, read, arguments, prepared):
        now = _file_sha(kernel, prepared['path'])
        return self._observed(prepared, now) if now == prepared['sha256'] else None

    @staticmethod
    def _observed(prepared, sha):
        return {'object': 'files:' + prepared['path'], 'revision': sha, 'by': 'sha256', 'complete': True, 'how': 'observed',
                'words': 'the file on disk has the digest %s' % sha[:12]}

    def verify(self, kernel, read, arguments, result, prepared, step):
        found = self.find(kernel, read, arguments, prepared)
        if not found:raise NotVerified('the file on disk does not hold the prepared text')
        return found

    def still(self, kernel, read, step):
        now = _file_sha(kernel, step['prepared']['path'])
        if now != step['observation']['revision']:return 'the file has changed since it was written' if now else 'the file is no longer there'
        return ''


class Recheck(Check):
    """office.datasheet.recheck: a new calculation page that replaces the old one, worked from the sheet's current revision,
    with an exact result. Sending it twice makes two pages, so resume looks for the new page before it sends it again."""
    kind = 'calculation';effect = 'a calculation worked again';standin_ms = 3000;repeatable = True
    how = 'a new calculation page replaces the old one, worked from the sheet as it is now, with an exact result'
    expected = 'a new calculation page that replaces the one named, with an exact result'
    PAGE = 100

    def _replaced_by(self, read, page, since):
        """The page that replaces `page`, made at `since` or after; None when there is none."""
        offset = 0
        while offset < 2000:
            rows = read('documents.list', {'limit': self.PAGE, 'offset': offset}).get('documents') or []
            for row in rows:
                if since is not None and (row.get('updated') or 0) < since - 1:continue
                doc = read('documents.get', {'id': row['id']}).get('document') or {}
                if (doc.get('derivation') or {}).get('replaces') == page and (since is None or (doc.get('created') or 0) >= since - 1):return doc
            if len(rows) < self.PAGE:return None
            offset += self.PAGE
        return None

    def prepare(self, kernel, read, arguments):
        page = read('documents.get', {'id': arguments['id']}).get('document') or {}
        if page.get('revision') != arguments['expected_revision']:
            raise Blocked('the calculation page is at revision %s, not the %s the plan names' % (page.get('revision'), arguments['expected_revision']))
        later = self._replaced_by(read, arguments['id'], page.get('created'))
        if later:raise Blocked('the calculation was already worked again (page %s replaces it); the plan names an older page' % later['id'])
        return {'page': arguments['id'], 'page_revision': page.get('revision'), 'title': page.get('title'),
                'sheet': (page.get('derivation') or {}).get('sheet'), 'at': time.time()}

    def _observe(self, read, doc):
        derivation = doc.get('derivation') or {}
        outputs = (derivation.get('calculation') or {}).get('outputs') or []
        value = outputs[0].get('value') if outputs and isinstance(outputs[0], dict) else None
        if not isinstance(value, dict) or outputs[0].get('state') != 'EXACT' or not value.get('rational'):
            raise NotVerified('the new page has no exact result')
        sheet = read('office.get', {'id': derivation['sheet']})
        if sheet.get('revision') != derivation.get('sheet_revision'):raise NotVerified('the sheet changed after the calculation was worked')
        cells = ((sheet.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
        inputs = {}
        for item in derivation.get('inputs') or ():
            if not _same_number((cells.get(item['cell']) or {}).get('value'), item['value']):
                raise NotVerified('%s on the sheet is not the %s the calculation used' % (item['cell'], item['value']))
            inputs[item['cell']] = item['value']
        return {'object': 'documents:' + doc['id'], 'page': doc['id'], 'revision': doc.get('revision'), 'by': 'page',
                'replaces': derivation.get('replaces'), 'value': value.get('decimal'), 'exact': value.get('rational'),
                'unit': value.get('unit'), 'inputs': inputs, 'sheet': derivation['sheet'], 'sheet_revision': derivation['sheet_revision'],
                'complete': True, 'how': 'observed',
                'words': 'page %s replaces %s: %s %s exactly, from the sheet as it is now' % (doc['id'][:8], str(derivation.get('replaces'))[:8],
                                                                                          value.get('decimal'), value.get('unit'))}

    def find(self, kernel, read, arguments, prepared):
        doc = self._replaced_by(read, prepared['page'], prepared['at'])
        return self._observe(read, doc) if doc else None

    def verify(self, kernel, read, arguments, result, prepared, step):
        made = ((result or {}).get('document') or {}).get('id')
        doc = read('documents.get', {'id': made}).get('document') if made else None
        if not doc or (doc.get('derivation') or {}).get('replaces') != prepared['page']:
            raise NotVerified('no new page replacing %s was found' % prepared['page'][:8])
        return self._observe(read, doc)

    def still(self, kernel, read, step):
        obs = step['observation']
        try:doc = read('documents.get', {'id': obs['page']}).get('document') or {}
        except ValueError:return 'the calculation page is no longer there'
        if doc.get('revision') != obs['revision']:return 'the calculation page has changed since'
        later = self._replaced_by(read, obs['page'], doc.get('created'))
        return ('it was worked again since (page %s)' % later['id'][:8]) if later else ''


class CellSet(Check):
    """field.set on a sheet's cell: done when the sheet holds the value."""
    kind = 'cell';effect = 'a value set on a sheet';standin_ms = 1500;repeatable = True
    how = 'the sheet, read again, holds the value in that cell'
    expected = 'the sheet with the value in its cell'

    @staticmethod
    def _sheet(arguments):
        ident = str(arguments.get('id') or '')
        if not ident.startswith('office:'):raise Unknowable('only a sheet\'s cell is checked here')
        return ident[len('office:'):]

    def _cell(self, read, arguments):
        sheet = read('office.get', {'id': self._sheet(arguments)})
        cells = ((sheet.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
        return sheet.get('revision'), (cells.get(arguments['cell']) or {}).get('value')

    def prepare(self, kernel, read, arguments):
        revision, value = self._cell(read, arguments)
        if arguments.get('expected_revision') not in (None, revision):raise Blocked('the sheet changed since the plan was made')
        return {'sheet': self._sheet(arguments), 'cell': arguments['cell'], 'value': arguments['value'], 'was': value, 'revision': revision}

    def find(self, kernel, read, arguments, prepared):
        revision, value = self._cell(read, arguments)
        if revision != prepared['revision'] and _same_number(value, prepared['value']):
            return {'object': 'office:' + prepared['sheet'], 'revision': revision, 'by': 'revision', 'cell': prepared['cell'], 'value': value,
                    'complete': True, 'how': 'observed', 'words': '%s holds %s' % (prepared['cell'], value)}
        return None

    def verify(self, kernel, read, arguments, result, prepared, step):
        found = self.find(kernel, read, arguments, prepared)
        if not found:raise NotVerified('%s does not hold %s' % (prepared['cell'], prepared['value']))
        return found

    def still(self, kernel, read, step):
        revision, value = self._cell(read, step['resolved'])
        if revision != step['observation']['revision']:return 'the sheet has changed since'
        return ''


CHECKS = {'files.write': FileWrite(), 'office.datasheet.recheck': Recheck(), 'field.set': CellSet()}
_READ, _NONE = ReadCheck(), Check()


def check_for(operation):
    from .engineering_kernel import CAPABILITIES
    if operation in CHECKS:return CHECKS[operation]
    return _READ if CAPABILITIES.get(operation) == 'read' else _NONE


def _object(operation, arguments):
    if isinstance(arguments.get('path'), str):return 'files:' + arguments['path']
    if isinstance(arguments.get('id'), str):return operation.split('.', 1)[0] + ':' + arguments['id']
    return operation


# ---------------------------------------------------------------- her clock: how long a step takes

def _measured(db, operation):
    from .brain_clock import WINDOW, LEAST
    from statistics import median_low
    rows = db.execute("SELECT payload FROM asg_journal WHERE operation=? AND entry='DONE' ORDER BY seq DESC LIMIT ?", (operation, WINDOW)).fetchall()
    times = [v for v in ((json.loads(r[0]).get('detail') or {}).get('elapsed_ms') for r in rows) if type(v) is int and v >= 0]
    return median_low(times) if len(times) >= LEAST else None


def estimate_ms(kernel, step, db=None):
    """Her clock's estimate of a step, whole ms: what the plan said, else the median of the times this operation took
    (three at least, the last 31), else the clock's price of a model turn, else the stand-in for its kind of effect."""
    if step.get('estimate_ms'):return step['estimate_ms']
    measured = None
    if db is not None and _present(db):measured = _measured(db, step['operation'])
    if measured is not None:return max(1, measured)
    kind = CLOCK_KINDS.get(step['operation'])
    if kind:
        from . import brain_clock
        budget = brain_clock.BUDGETS[kind]
        return brain_clock.clock(kernel).price_ms(None, kind, budget['brief'] + budget['new_typical'], budget['answer'], 50)
    return check_for(step['operation']).standin_ms


def clock_words(ms):
    """Whole seconds, rounded up, as 00:18 (or 1:02:05 past an hour)."""
    seconds = max(0, -(-int(ms) // 1000))
    hours, rest = divmod(seconds, 3600)
    return ('%d:%02d:%02d' % (hours, rest // 60, rest % 60)) if hours else '%02d:%02d' % divmod(rest, 60)


# ---------------------------------------------------------------- who is running it

def _runner():
    from .operation_stop import process_identity
    pid = os.getpid()
    return {'pid': pid, 'start': process_identity(pid), 'thread': threading.get_ident(), 'at': time.time()}


def _alive(runner):
    if not runner:return False
    from .operation_stop import process_identity, UNKNOWN
    now = process_identity(runner.get('pid'))
    return now is not None and (now == UNKNOWN or now == runner.get('start'))


@contextlib.contextmanager
def _run_lock(kernel, ident):
    """One runner per assignment, across processes: held while a step is prepared, sent and recorded."""
    folder = kernel.state / 'assignments'
    folder.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(folder / (_ident(ident) + '.lock'), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        try:fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('ASSIGNMENT_BUSY: it is being worked on now') from None
        yield
    finally:
        os.close(fd)


def _gate(kernel):
    from . import work_trail
    try:
        jobs = work_trail.work_status(kernel)
        from . import halt_gate      # 1.0 K3: HALT's own hold, apart from Stop all's; her assignments obey both
        mine = halt_gate.status(kernel)
        return {'held': bool(jobs['held'] or mine['held']), 'epoch': (jobs['epoch'], mine['epoch']), 'halt': bool(mine['held'])}
    except Exception:  # noqa: BLE001 - a gate that cannot be read holds the work, as the Night Shift's does
        return {'held': True, 'epoch': -1}


# ---------------------------------------------------------------- the operations

def start(kernel, args, principal):
    objective = args['objective'].strip()
    if not objective:raise ValueError('An assignment starts from your words')
    ident = uuid.uuid4().hex
    value = {'schema': SCHEMA, 'id': ident, 'owner': principal.identity, 'objective': objective,
             'title': (args.get('title') or objective.split('\n', 1)[0])[:200], 'state': OPEN, 'reason': '', 'revision': 0,
             'created': time.time(), 'steps': [], 'stopped': None, 'runner': None}
    if args.get('steps'):value['steps'] = _plan_steps(args['steps'], objective, [])
    if len(value['steps']) > MAX_STEPS:raise ValueError('At most %d steps' % MAX_STEPS)
    with _writing(kernel) as db:
        _save(db, value, new=True)
        _journal(db, value, None, 'STARTED', 'You set the assignment: "%s"' % objective[:300], {'objective_digest': digest(objective)})
        if value['steps']:_journal(db, value, None, 'PLANNED', _planned_words(value['steps']), {'plan': plan_digest(value)})
    if AUTHORISE is not None and value['steps']:AUTHORISE(kernel, ident, principal)      # 1.0 K3: what your grants cover
    return status(kernel, ident, principal)


def _plan_steps(sources, objective, kept):
    if not isinstance(sources, list) or len(sources) + len(kept) > MAX_STEPS:raise ValueError('At most %d steps' % MAX_STEPS)
    keys = [s['key'] for s in kept];out = []
    for n, source in enumerate(sources, len(kept) + 1):
        step = _plan_step(source, objective, list(keys), n)
        keys.append(step['key']);out.append(step)
    return out


def _planned_words(steps):
    return 'Planned: ' + '; '.join('%d. %s' % (s['n'], s['title']) for s in steps)[:900]


def plan(kernel, args, principal):
    """Propose steps (replacing those that have not started) and/or authorise steps by your press."""
    if 'steps' not in args and 'authorise' not in args:raise ValueError('Give steps to propose, or the steps you authorise')
    said = []
    with _writing(kernel) as db:
        value = _load(db, args['id'], principal)
        if value['state'] == DONE:raise ValueError('This assignment is done; start another')
        if 'steps' in args:
            if value['state'] == RUNNING and _alive(value.get('runner')):raise ValueError('ASSIGNMENT_BUSY: a step is running; stop it first')
            kept = [s for s in value['steps'] if _started(s)]
            value['steps'] = kept + _plan_steps(args['steps'], value['objective'], kept)
            _save(db, value);_journal(db, value, None, 'PLANNED', _planned_words(value['steps']), {'plan': plan_digest(value)})
            said.append('planned')
        if 'authorise' in args:
            if 'approve' not in principal.scopes or principal.mode == 'Tutor':
                raise ValueError('AUTHORISE_IS_YOURS: only your own press authorises a step')
            if args.get('expected_digest') != plan_digest(value):
                raise ValueError('PLAN_CHANGED: authorise the plan as it is now (read it again; its digest changed)')
            said.extend(_authorise(db, value, args['authorise'], principal))
    if AUTHORISE is not None and 'steps' in args:said.extend(AUTHORISE(kernel, args['id'], principal))      # 1.0 K3: what your grants cover
    result = status(kernel, args['id'], principal);result['said'] = said
    return result


def _authorise(db, value, names, principal):
    from . import stacy_hand
    every = 'all' in names
    unknown = [n for n in names if n != 'all' and n not in {s['key'] for s in value['steps']}]
    if unknown:raise ValueError('There is no step %s' % unknown[0])
    said = [];left = []
    for step in value['steps']:
        named = step['key'] in names
        if not (named or every) or step['status'] in ('done', 'running'):continue
        if step['status'] in ('needs review', 'blocked') and not named:continue
        if step['status'] == 'authorised' and not named:continue
        if not named:
            why = ''
            if step['always_asks']:why = 'it always asks (%s)' % step['always_asks']
            elif step['basis'] == stacy_hand.MODEL_PICK and step['scope'] != 'read':why = stacy_hand.MODEL_PICK_WHY
            elif step['scope'] == 'approve':why = 'the records mark it for your approval'
            if why:
                left.append('step %d is authorised only by its own name: %s' % (step['n'], why));continue
        if step['status'] == 'authorised' and step['authorised'] and step['authorised'].get('by') == principal.identity:continue
        again = step['status'] in ('needs review', 'blocked')
        step.update(status='authorised', reason='',
                    authorised={'by': principal.identity, 'at': time.time(), 'explicit': named,
                                'arguments': digest(step['arguments']), 'again': again})
        words = 'You authorised step %d (%s)%s%s.' % (step['n'], step['title'], ' again' if again else '',
                                                    ': ' + stacy_hand.APPROVED_PICK if step['basis'] == stacy_hand.MODEL_PICK else '')
        _save(db, value);_journal(db, value, step, 'AUTHORISED', words, {'explicit': named, 'again': again});said.append(words)
    return said + left


def _outputs(value):
    return {s['key']: s['output'] or {} for s in value['steps'] if s['status'] == 'done'}


def _require(step, observation, outputs):
    for check in step['require']:
        expected = _resolve(check['equals'], outputs)
        try:found = _pick(observation, check['path'])
        except ValueError:raise NotVerified('the check of %s found nothing there' % '/'.join(check['path'])) from None
        same = _same_number(found, expected) if isinstance(found, (str, int)) and isinstance(expected, (str, int)) \
            and not isinstance(found, bool) and not isinstance(expected, bool) else canonical(found) == canonical(expected)
        if not same:raise NotVerified('%s is %s, not %s' % ('/'.join(check['path']), _words_of(found)[:80], _words_of(expected)[:80]))


def _bounded(principal, scope):
    from .engineering_kernel import Principal
    return Principal(principal.identity, frozenset({'read', scope}), principal.paths, principal.tools, principal.mode)


def _reader(kernel, principal):
    from .engineering_kernel import Principal
    reader = Principal(principal.identity, frozenset({'read'}), principal.paths, (), principal.mode)

    def read(operation, arguments):
        answer = kernel.dispatch(operation, arguments, reader)
        if not answer.get('ok'):raise ValueError(str((answer.get('error') or {}).get('message') or 'it could not be read')[:300])
        return answer['result']
    return read


def _next(value):
    return next((s for s in value['steps'] if s['status'] != 'done'), None)


def _finish_state(value):
    """After a step: done when every step is, else open (a Stop or a hold keeps its own state)."""
    value['runner'] = None
    if value['state'] in (STOPPED, HELD):return
    value['state'] = DONE if value['steps'] and all(s['status'] == 'done' for s in value['steps']) else OPEN


def _hold(db, value, step, words):
    value.update(state=HELD, reason=words, runner=None)
    _save(db, value);_journal(db, value, step, 'HELD', words)


def _output(step, observation, result):
    """A done step's named outputs: from what a read returned, or from the verified observation of an effect."""
    base = result if step['scope'] == 'read' else observation
    return {name: json.loads(canonical(_pick(base, path))) for name, path in (step['outputs'] or {}).items()}


def _run_one(kernel, ident, principal, epoch=None):
    """Run the next step, the lock held. Returns (what happened, carry on?). `epoch`: the gate's epoch when this run
    began; a hold since then (even one lifted again) stops the run, as it stops the Night Shift's."""
    read = _reader(kernel, principal)
    gate = _gate(kernel)
    if AUTHORISE is not None and not gate['held']:AUTHORISE(kernel, ident, principal, True)      # 1.0 K3: by your grant, or "needs your grant"
    with _writing(kernel) as db:
        value = _load(db, ident, principal)
        if value['state'] in (STOPPED, DONE):
            return ('This assignment is %s.' % (STOPPED_BY_YOU if value['state'] == STOPPED else 'done'), False)
        if value['state'] == HELD:return ('All of her work is held; resume this assignment once the hold is lifted.', False)
        interrupted = [s for s in value['steps'] if s['status'] == 'running']
        if interrupted:
            return ('Step %d was interrupted while it ran; resume the assignment so it is inspected first.' % interrupted[0]['n'], False)
        if gate['held']:
            _hold(db, value, None, 'All of her work is held (HALT or Stop all): nothing was started.')
            return (value['reason'], False)
        if epoch is not None and epoch != gate['epoch']:
            _hold(db, value, None, 'Her work was held while this ran; resume it to carry on.')
            return (value['reason'], False)
        step = _next(value)
        if step is None:
            _finish_state(value);_save(db, value);return ('Every step is done.', False)
        if step['status'] == 'proposed':return ('Step %d (%s) waits for your word.' % (step['n'], step['title']), False)
        if step['status'] in ('blocked', 'needs review'):return ('Step %d %s: %s' % (step['n'], step['status'], step['reason']), False)
        outputs = _outputs(value)
    check = check_for(step['operation'])
    # Inputs and preconditions, before anything is written as prepared.
    try:
        arguments = _resolve(step['arguments'], outputs)
        from .engineering_cli import schemas
        from .agent_operations import validate
        from .engineering_kernel import CAPABILITIES
        if CAPABILITIES.get(step['operation']) != step['scope']:raise Blocked('%s is no longer registered as it was planned' % step['operation'])
        try:validate(arguments, schemas()[step['operation']])
        except ValueError as bad:raise Blocked('its inputs do not fit %s (%s)' % (step['operation'], bad)) from None
        if step['scope'] == 'approve' and (not step['authorised'] or not step['authorised'].get('explicit')
                                           or step['authorised'].get('arguments') != digest(arguments)):
            raise Blocked('the records mark it for your approval: authorise this step by its name')
        if GRANT_CHECK is not None:
            why = GRANT_CHECK(kernel, value, step, arguments, principal)
            if why:raise Blocked('needs your grant: ' + str(why)[:300])
        from . import tools_registry  # 1.0 K2: the preconditions of the step's tool, from the registry
        unmet = tools_registry.step_unmet(kernel, step, arguments)
        if unmet:raise Blocked('its precondition does not hold: ' + unmet)
        prepared = check.prepare(kernel, read, arguments)
        try:found = check.find(kernel, read, arguments, prepared) if step['scope'] != 'read' else None
        except Unknowable:found = step['observation'] if step.get('dialog_seen') == step['attempts'] and step['observation'] else None  # 1.0 K7: verified before a dialog came; never made twice
    except Exception as why:  # noqa: BLE001 - whatever stops a step before it starts blocks it, with the reason; nothing was sent
        reason = str(why)[:400]
        with _writing(kernel) as db:
            value = _load(db, ident, principal);live = next(s for s in value['steps'] if s['key'] == step['key'])
            live.update(status='blocked', reason=reason)
            after = _after_step(kernel, db, value, live, 'BLOCKED')  # 1.0 K4: another registered route inside its scope, when there is one
            _save(db, value);_journal(db, value, live, 'BLOCKED', 'Step %d is blocked: %s. Nothing was sent.' % (live['n'], reason))
            for row in after:_journal(db, value, *row)  # 1.0 K4
        return ('Step %d is blocked: %s' % (step['n'], reason) + ''.join(' ' + row[2] for row in after), any(row[1] == 'REVISED' for row in after))
    # Written before the effect: prepared, with what it will be checked against.
    with _writing(kernel) as db:
        value = _load(db, ident, principal);live = next(s for s in value['steps'] if s['key'] == step['key'])
        if value['state'] in (STOPPED, HELD) or live['status'] != 'authorised':
            return ('It was stopped before step %d started.' % live['n'], False)
        estimate = estimate_ms(kernel, live, db)
        live.update(status='running', reason='', prepared={**prepared, 'at': prepared.get('at', time.time()), 'arguments': digest(arguments)},
                    resolved=arguments, runner=_runner(), attempts=live['attempts'] + 1, started=time.time(), started_ns=time.time_ns(),
                    finished=None, estimate_now_ms=estimate)
        value.update(state=RUNNING, runner=live['runner'])
        _save(db, value)
        _journal(db, value, live, 'PREPARED', 'Step %d prepared: %s, %s.' % (live['n'], live['title'], live['grant']['words'] if live['scope'] != 'read' else 'a read'),
                 {'arguments': digest(arguments), 'prepared': prepared, 'attempt': live['attempts'], 'estimate_ms': estimate})
    began = _now_ms();observation = None;result = None;sent = False;outcome = '';output = {}
    watch = None  # 1.0 K7: the windows and dialogs as they were before the change was sent
    try:
        if found is not None:
            observation = found;outcome = 'found'
        else:
            # The last look before the effect: a Stop or a hold that came meanwhile leaves it prepared, not sent.
            with kernel.db() as db:
                still = _load(db, ident, principal)
            gate_now = _gate(kernel)
            if still['state'] in (STOPPED, HELD) or gate_now['held'] or gate_now['epoch'] != gate['epoch']:
                outcome = 'not sent'
            else:
                from . import tools_registry  # 1.0 K2: a tool that writes a file holds off a suspend while it writes (S1's sleep lock)
                granted = GRANTED(kernel, value, step, arguments, principal) if GRANTED is not None else contextlib.nullcontext()  # 1.0 K3
                watch = _watch('mark', kernel, step)  # 1.0 K7
                with tools_registry.holding(step['operation'], step['title']), granted:
                    answer = kernel.dispatch(step['operation'], arguments, _bounded(principal, step['scope']))
                sent = True
                if not answer.get('ok'):
                    outcome = 'refused';result = answer.get('error') or {}
                else:
                    result = answer['result']
                    with _writing(kernel) as db:
                        value = _load(db, ident, principal);live = next(s for s in value['steps'] if s['key'] == step['key'])
                        _save(db, value);_journal(db, value, live, 'SENT', 'Step %d sent; checking it now.' % live['n'],
                                                  {'result': digest(result), 'elapsed_ms': _now_ms() - began})
                    observation = check.verify(kernel, read, arguments, result, live['prepared'], {**live, 'resolved': arguments})
                    outcome = 'verified'
            if observation is not None:
                _require(step, observation, outputs)
                output = _output(step, observation, result)
    except NotVerified as why:
        outcome = 'not verified';result = {'reason': str(why)[:400]}
    except Exception as why:  # noqa: BLE001 - a step that went wrong is recorded as such, never left running or called done
        outcome = 'not verified' if sent else 'failed';result = {'reason': str(why)[:400] or type(why).__name__}
    elapsed = _now_ms() - began
    noticed = _watch('notice', kernel, step, watch) if watch and outcome in ('verified', 'not verified') else None  # 1.0 K7: a dialog seen meanwhile
    # Written after the effect.
    with _writing(kernel) as db:
        value = _load(db, ident, principal);live = next(s for s in value['steps'] if s['key'] == step['key'])
        live.update(runner=None, elapsed_ms=elapsed)
        if outcome in ('verified', 'found'):
            if len(canonical([observation, output]).encode()) > MAX_OUTPUT:observation = {**{k: observation[k] for k in ('object', 'revision', 'by', 'how', 'complete', 'words') if k in observation}}
            live.update(status='done', reason='', observation=observation, output=output, finished=time.time())
            words = 'Step %d done (verified): %s. %s' % (live['n'], live['title'], observation.get('words', ''))
            if outcome == 'found':words = 'Step %d done (verified): its effect was already there and was not made again. %s' % (live['n'], observation.get('words', ''))
            entry = 'DONE' if outcome == 'verified' else 'FOUND_DONE'
            detail = {'observation': observation, 'output': output, 'elapsed_ms': elapsed}
        elif outcome == 'not sent':
            live.update(status='authorised', reason='', prepared=None)
            entry, words, detail = 'NOT_SENT', 'Step %d was prepared and not sent: %s.' % (
                live['n'], STOPPED_BY_YOU if value['state'] == STOPPED else 'her work was held'), {}
        elif outcome == 'refused':
            reason = str((result or {}).get('message') or (result or {}).get('code') or 'refused')[:400]
            live.update(status='blocked', reason='refused: ' + reason)
            entry, words, detail = 'REFUSED', 'Step %d was refused by the desk: %s. Nothing is called done.' % (live['n'], reason), {'error': result}
        elif outcome == 'failed':
            live.update(status='blocked', reason=(result or {}).get('reason', ''))
            entry, words, detail = 'BLOCKED', 'Step %d could not start: %s' % (live['n'], live['reason']), {}
        else:
            live.update(status='needs review', reason=(result or {}).get('reason', 'not verified'))
            entry, words, detail = 'NOT_VERIFIED', 'Step %d was sent and is not verified: %s. It is not called done.' % (live['n'], live['reason']), {'elapsed_ms': elapsed}
        after = _after_step(kernel, db, value, live, entry) if entry in ('DONE', 'FOUND_DONE', 'BLOCKED', 'REFUSED') else []  # 1.0 K4
        if noticed:  # 1.0 K7: a dialog appeared in a program while it ran: its words are yours to see, and the step waits for your review
            before = live['reason'] + ' ' if live['status'] == 'needs review' and live['reason'] else ''
            live.update(status='needs review', reason=(before + noticed['words'])[:900], dialog_seen=live['attempts'])
            words += ' It needs your review: ' + noticed['words']
        _finish_state(value)
        gate_after = _gate(kernel)
        if value['state'] not in (STOPPED, DONE) and (gate_after['held'] or gate_after['epoch'] != gate['epoch']):
            value.update(state=HELD, reason='Her work was held while step %d ran; what it did is recorded.' % live['n'])
        _save(db, value);_journal(db, value, live, entry, words, detail)
        for row in after:_journal(db, value, *row)  # 1.0 K4: the step that follows from it, or another route, journalled after it
        if noticed:  # 1.0 K7: its own journal row, and the dialog's receipts linked to it, in the same transaction
            seq = _journal(db, value, live, 'DIALOG_SEEN', noticed['words'], {'dialogs': noticed.get('dialogs') or []})
            _watch('keep', db, value, live, noticed, seq)
        if value['state'] == DONE:_journal(db, value, None, 'FINISHED', 'Every step is done (verified).')
        carry = (entry in ('DONE', 'FOUND_DONE') or any(row[1] == 'REVISED' for row in after)) and value['state'] == OPEN and not noticed  # 1.0 K4, K7
        words += ''.join(' ' + row[2] for row in after)  # 1.0 K4
    return (words, carry)


AFTER_STEP = None            # 1.0 K4 sets it: callable(kernel, db, assignment, step, entry) -> [(step, entry, words, detail)] to journal


def _after_step(kernel, db, value, step, entry):
    """1.0 K4: what follows from a step's outcome in a plan of hers (AFTER_STEP): rows to journal after the step's own; [] when
    nothing does. A hook that fails changes nothing: the plan stays as it was planned."""
    if AFTER_STEP is None:return []
    try:return list(AFTER_STEP(kernel, db, value, step, entry) or [])
    except Exception:  # noqa: BLE001 - a plan that cannot be carried further stays as it was planned
        return []


def run(kernel, ident, principal, until='next'):
    """Run the next authorised step, or carry on until a step needs you ('end'). The lock is this assignment's own."""
    work = [];epoch = _gate(kernel)['epoch']
    with _run_lock(kernel, ident):
        while True:
            said, carry = _run_one(kernel, ident, principal, epoch)
            work.append(said)
            if until != 'end' or not carry:break
    result = status(kernel, ident, principal);result['said'] = work
    return result


def stop(kernel, ident, principal, why=None):
    """Stopped by you: nothing more starts. A call already sent is recorded as it ends, never hidden. 1.0 K3: why='halt'
    when HALT stopped it (the journal says so)."""
    with _writing(kernel) as db:
        value = _load(db, ident, principal)
        if value['state'] == DONE:raise ValueError('This assignment is done; there is nothing to stop')
        in_flight = [s for s in value['steps'] if s['status'] == 'running']
        value.update(state=STOPPED, reason=STOPPED_BY_YOU, stopped={'by': principal.identity, 'at': time.time(), **({'why': why} if why else {})})
        _save(db, value)
        _journal(db, value, None, 'STOPPED', _stopped_words(value, _entries(db, ident), in_flight, halt=why == 'halt'))
    return status(kernel, ident, principal)


def _stopped_words(value, entries, in_flight, halt=False):
    """Stopped by you, with what was done, what was only prepared and what did not start. 1.0 K3: halt, by your HALT."""
    says = journal_says(value, entries)
    running = [s['n'] for s in in_flight if _alive(s.get('runner'))]
    done = [s['n'] for s in value['steps'] if s['status'] == 'done']
    words = ('Stopped by you with HALT. ' if halt else 'Stopped by you. ') + ('Done (verified): %s. ' % _steps(done) if done else 'Nothing was done yet. ')
    prepared = [s['n'] for s in value['steps'] if says.get(s['key'], '').startswith('prepared') and s['n'] not in running]
    if prepared:words += 'Prepared, not done: %s. ' % _steps(prepared)
    if running:words += 'Step %d was running%s: what it does is recorded as it ends. ' % (running[0], ' when you pressed HALT' if halt else '')
    sent = [s['n'] for s in value['steps'] if s['status'] != 'done' and s['n'] not in prepared and s['n'] not in running
            and says.get(s['key'], '').startswith(('sent', 'refused', 'done, changed'))]      # 1.0 K3: sent is never "not started"
    if sent:words += 'Sent, not verified: %s. ' % _steps(sent)
    rest = [s['n'] for s in value['steps'] if s['status'] != 'done' and s['n'] not in prepared and s['n'] not in running and s['n'] not in sent]
    if rest:words += 'Not started: %s.' % _steps(rest)
    return words.strip()


def _numbers(ns):
    ns = [str(n) for n in ns]
    if not ns:return ''
    return ns[0] if len(ns) == 1 else ', '.join(ns[:-1]) + ' and ' + ns[-1]


def _steps(ns):
    return ('step ' if len(ns) == 1 else 'steps ') + _numbers(ns)


def resume(kernel, ident, principal, carry_on=True):
    """Inspect every step's output before anything is repeated, then carry on (when carry_on)."""
    gate = _gate(kernel)
    if gate['held']:raise ValueError('WORK_HELD: all of her work is held; lift the hold first, then resume this assignment')
    read = _reader(kernel, principal)
    said = []
    with _run_lock(kernel, ident):
        with kernel.db() as db:
            value = _load(db, ident, principal)
        findings = {}
        for step in value['steps']:
            check = check_for(step['operation'])
            if step['status'] == 'done':
                try:changed = check.still(kernel, read, step)
                except (ValueError, KeyError, TypeError, OSError) as why:changed = 'it could not be checked (%s)' % str(why)[:200]
                findings[step['key']] = ('STILL_DONE', '') if not changed else ('CHANGED_SINCE', changed)
            elif step['status'] == 'running' or (step['prepared'] is not None and step['status'] in ('authorised', 'blocked')):
                try:
                    if step['scope'] == 'read':found = None
                    else:found = check.find(kernel, read, step.get('resolved') or {}, step['prepared'])
                    findings[step['key']] = ('FOUND_DONE', found) if found else ('NOT_FOUND', check.repeatable)
                except Unknowable as why:findings[step['key']] = ('CANNOT_TELL', str(why))
                except (ValueError, KeyError, TypeError, OSError) as why:findings[step['key']] = ('CANNOT_TELL', 'it could not be inspected (%s)' % str(why)[:200])
        with _writing(kernel) as db:
            value = _load(db, ident, principal)
            if value['state'] == RUNNING and _alive(value.get('runner')):raise ValueError('ASSIGNMENT_BUSY: it is running now')
            was = value['state']
            _save(db, value)
            _journal(db, value, None, 'RESUMED', 'You resumed it%s; each step is inspected before anything is repeated.' % (
                {STOPPED: ' after you stopped it', HELD: ' after the hold', RUNNING: ' after Graphite stopped mid-step'}.get(was, '')))
            outputs = _outputs(value)
            for step in value['steps']:
                finding = findings.get(step['key'])
                if not finding:continue
                entry, detail = finding
                if entry == 'STILL_DONE':
                    words = 'Step %d checked: its output is still there (%s); it is not done again.' % (step['n'], (step['observation'] or {}).get('words', ''))
                elif entry == 'CHANGED_SINCE':
                    step.update(status='needs review', reason=detail)
                    words = 'Step %d was done, and %s. It is not done again by itself: yours to look at.' % (step['n'], detail)
                elif entry == 'FOUND_DONE':
                    try:
                        _require(step, detail, outputs)
                        try:output = _output(step, detail, None)
                        except ValueError as missing:raise NotVerified('its output is not all there (%s)' % missing) from None
                        step.update(status='done', reason='', observation=detail, output=output, runner=None, finished=time.time())
                        outputs[step['key']] = output
                        words = 'Step %d done (verified): it was prepared before Graphite stopped, and its effect is there: %s. It is not made again.' % (step['n'], detail.get('words', ''))
                    except NotVerified as why:
                        entry = 'NOT_VERIFIED';step.update(status='needs review', reason=str(why), runner=None)
                        words = 'Step %d: an effect is there, and its check did not hold: %s.' % (step['n'], why)
                elif entry == 'NOT_FOUND':
                    if detail:
                        step.update(status='authorised', reason='', runner=None, prepared=None)
                        words = 'Step %d was prepared and its effect is not there: it will be done now.' % step['n']
                    else:
                        step.update(status='needs review', reason='its effect is not there, and it is not safe to repeat by itself', runner=None)
                        words = 'Step %d: %s.' % (step['n'], step['reason'])
                else:
                    step.update(status='needs review', reason=detail, runner=None)
                    words = 'Step %d: %s.' % (step['n'], detail)
                _save(db, value);_journal(db, value, step, entry, words, {'observation': detail} if entry == 'FOUND_DONE' else {})
                said.append(words)
            value.update(state=OPEN, reason='', runner=None, stopped=None)
            _finish_state(value);_save(db, value)
            if value['state'] == DONE and was != DONE:_journal(db, value, None, 'FINISHED', 'Every step is done (verified).')
        if carry_on and value['state'] == OPEN:
            while True:
                words, carry = _run_one(kernel, ident, principal, gate['epoch'])
                said.append(words)
                if not carry:break
    result = status(kernel, ident, principal);result['said'] = said
    return result


# ---------------------------------------------------------------- reading it

EFFECT_ENTRIES = ('PREPARED', 'NOT_SENT', 'SENT', 'DONE', 'FOUND_DONE', 'STILL_DONE', 'NOT_VERIFIED', 'REFUSED', 'CHANGED_SINCE',
                  'NOT_FOUND', 'CANNOT_TELL', 'BLOCKED')
SAYS = {'PREPARED': 'prepared', 'NOT_SENT': 'prepared, not sent', 'SENT': 'sent, not yet verified', 'DONE': 'done (verified)',
        'FOUND_DONE': 'done (verified)', 'STILL_DONE': 'done (verified)', 'NOT_VERIFIED': 'sent, not verified',
        'REFUSED': 'refused', 'CHANGED_SINCE': 'done, changed since', 'NOT_FOUND': 'prepared, not done (inspected)',
        'CANNOT_TELL': 'prepared, cannot tell', 'BLOCKED': 'blocked'}


def journal_says(value, entries):
    """For each step, what the journal says of its effect: done (verified), prepared, ... or its status when nothing was
    prepared (proposed, authorised)."""
    last = {}
    for row in entries:
        if row['entry'] in EFFECT_ENTRIES and row['step']:last[row['step']] = row['entry']
    out = {}
    for step in value['steps']:
        entry = last.get(step['key'])
        if entry in ('BLOCKED', 'NEEDS_GRANT') and step['status'] != 'blocked':entry = None      # 1.0 K3: NEEDS_GRANT too
        out[step['key']] = SAYS[entry] if entry else step['status']
    return out


def _interrupted(value):
    return value['state'] == RUNNING and not _alive(value.get('runner'))


def _state_words(value):
    if value['state'] == DONE:return 'done'
    if value['state'] == STOPPED:return STOPPED_BY_YOU
    if value['state'] == HELD:return 'held'
    if value['state'] == RUNNING:return 'interrupted' if _interrupted(value) else 'working'
    statuses = [s['status'] for s in value['steps']]
    if 'needs review' in statuses:return 'needs review'
    if any(s['status'] == 'blocked' and str(s.get('reason', '')).startswith('needs your grant') for s in value['steps']):
        return 'needs your grant'      # 1.0 K3
    if 'blocked' in statuses:return 'blocked'
    step = _next(value)
    if step is None:return 'no steps yet'
    return 'waiting for your word' if step['status'] == 'proposed' else 'ready'


def _progress(kernel, value, db):
    """Whole percent done and whole ms left, from her clock's estimates; the running step counts what it has used."""
    total = left = done = 0;rows = []
    for step in value['steps']:
        estimate = step.get('estimate_now_ms') or estimate_ms(kernel, step, db)
        total += estimate
        if step['status'] == 'done':
            done += estimate;remaining = 0
        elif step['status'] == 'running' and step.get('started_ns') and not _interrupted(value):
            used = max(0, (time.time_ns() - step['started_ns']) // 1000000)
            remaining = max(0, estimate - used);done += min(used, estimate * 95 // 100)
        else:
            remaining = estimate
        left += remaining;rows.append((estimate, remaining))
    percent = (done * 100 // total) if total else 0
    if value['state'] == DONE:percent = 100
    return percent, left, rows


def _step_view(step, says, timing):
    return {'key': step['key'], 'n': step['n'], 'title': step['title'], 'tool': step['tool'], 'operation': step['operation'],
            'scope': step['scope'], 'inputs': {k: {kk: vv for kk, vv in v.items() if kk in ('value', 'from', 'origin')} for k, v in step['inputs'].items()},
            'expected': step['expected'], 'verify': step['verify']['words'], 'grant': step['grant']['words'], 'basis': step['basis'],
            'status': step['status'], 'reason': step['reason'], 'journal_says': says,
            'observation': step['observation'], 'output': step['output'], 'authorised_by': (step['authorised'] or {}).get('by'),
            'estimate_ms': timing[0], 'time_left_ms': timing[1], 'time_left': clock_words(timing[1]), 'elapsed_ms': step['elapsed_ms']}


def status(kernel, ident, principal):
    with kernel.db() as db:
        value = _load(db, ident, principal)
        entries = _entries(db, ident)
        percent, left, timings = _progress(kernel, value, db)
        from . import tools_registry  # 1.0 K2: each step's observation receipts (dispatched and verified are two)
        receipts = tools_registry.of_assignment(db, ident)
    says = journal_says(value, entries)
    steps = [dict(_step_view(s, says[s['key']], t), receipts=receipts.get(s['key'], [])) for s, t in zip(value['steps'], timings)]
    nxt = _next(value)
    summary = '; '.join('step %d %s' % (s['n'], says[s['key']]) for s in value['steps'])
    words = _state_words(value)
    if words == 'interrupted':
        running = next((s for s in value['steps'] if s['status'] == 'running'), None)
        line = 'Graphite stopped while step %d was prepared; nothing after it ran. Resume inspects it first.' % running['n'] if running else 'Interrupted.'
    elif value['state'] == STOPPED:line = _stopped_words(value, entries, [s for s in value['steps'] if s['status'] == 'running'],
                                                         halt=(value.get('stopped') or {}).get('why') == 'halt')      # 1.0 K3
    elif value['state'] == HELD:line = value['reason']
    elif value['state'] == DONE:line = 'Every step is done (verified).'
    elif nxt is None:line = 'No steps are planned yet.'
    elif nxt['status'] == 'proposed':line = 'Step %d (%s) waits for your word.' % (nxt['n'], nxt['title'])
    elif nxt['status'] == 'blocked' and str(nxt['reason']).startswith('needs your grant: '):      # 1.0 K3
        line = 'Step %d (%s) needs your grant: %s. Nothing was sent.' % (nxt['n'], nxt['title'], nxt['reason'][len('needs your grant: '):])
    elif nxt['status'] in ('blocked', 'needs review'):line = 'Step %d %s: %s' % (nxt['n'], nxt['status'], nxt['reason'])
    elif nxt['status'] == 'running':line = 'Step %d of %d: %s, %s left.' % (nxt['n'], len(value['steps']), nxt['title'], clock_words(timings[nxt['n'] - 1][1]))
    else:line = 'Step %d (%s) is ready.' % (nxt['n'], nxt['title'])
    stop_call = {'operation': 'assignment.stop', 'arguments': {'id': value['id']}} if value['state'] not in (DONE, STOPPED) else None
    actions = _actions(value, words, nxt, stop_call)
    if GRANT_ACTION is not None and value['state'] not in (DONE, STOPPED, HELD):      # 1.0 K3: "Grant this for this assignment"
        try:
            one = GRANT_ACTION(kernel, value, nxt, principal)
            if one:actions.insert(0, one)
        except Exception:  # noqa: BLE001 - the press is offered when it can be worded; the step still says it needs your grant
            pass
    return {'schema': SCHEMA, 'id': value['id'], 'title': value['title'], 'objective': value['objective'], 'state': value['state'],
            'state_words': words, 'state_word': words.upper(), 'line': line, 'revision': value['revision'],
            'created': value['created'], 'updated': value['updated'], 'plan_digest': plan_digest(value), 'steps': steps,
            'journal_says': (summary[0].upper() + summary[1:] + '.') if summary else 'No steps yet.',
            'journal': entries[-JOURNAL_SHOWN:], 'journal_intact': all(e['intact'] for e in entries),
            'progress': percent, 'time_left_ms': left, 'time_left': clock_words(left), 'interrupted': words == 'interrupted',
            'stop': stop_call, 'actions': actions,
            'authority': 'A read never asks; every change waits for your press; nothing is done until its effect is verified.'}


def _actions(value, words, nxt, stop_call):
    """The presses this assignment offers now, as calls (her column's buttons): Stop, Resume, Authorise step n, Carry on."""
    ident = value['id'];out = []
    if nxt is not None and nxt['status'] == 'proposed' and words not in ('interrupted', 'held', STOPPED_BY_YOU):
        out.append({'words': 'Authorise step %d' % nxt['n'], 'operation': 'assignment.plan', 'yours': True,
                    'arguments': {'id': ident, 'authorise': [nxt['key']], 'expected_digest': plan_digest(value)}})
    if words in ('interrupted', 'held', STOPPED_BY_YOU):
        out.append({'words': 'Resume', 'operation': 'assignment.resume', 'arguments': {'id': ident}})
    elif words == 'ready':
        out.append({'words': 'Carry on', 'operation': 'assignment.step', 'arguments': {'id': ident, 'until': 'end'}})
    if stop_call:out.append({'words': 'Stop', **stop_call})
    return out


def listing(kernel, args, principal):
    with kernel.db() as db:
        if not _present(db):return {'assignments': [], 'total': 0}
        where = "owner=?" + (" AND state!='done'" if args.get('open') else '')
        total = db.execute('SELECT count(*) FROM asg_assignments WHERE ' + where, (principal.identity,)).fetchone()[0]
        ids = [r[0] for r in db.execute('SELECT id FROM asg_assignments WHERE ' + where + ' ORDER BY updated DESC LIMIT ? OFFSET ?',
                                        (principal.identity, args.get('limit', 20), args.get('offset', 0)))]
    rows = []
    for ident in ids:
        view = status(kernel, ident, principal)
        rows.append({k: view[k] for k in ('id', 'title', 'state', 'state_words', 'state_word', 'line', 'progress', 'time_left',
                                          'time_left_ms', 'journal_says', 'updated', 'stop', 'actions')})
    return {'assignments': rows, 'total': total}


def active_work(kernel, principal, limit=4):
    """Her column's ACTIVE WORK (P1): the open assignments, newest first, each with its progress, time left and Stop."""
    return listing(kernel, {'open': True, 'limit': limit}, principal)['assignments']


def agenda_rows(kernel, principal):
    """The Agenda's rows: a running assignment under NOW, one that needs you under WAITING. Reads only; nothing is created."""
    out = {'now': [], 'waiting': []}
    try:
        with kernel.db() as db:
            if not _present(db):return out
        for row in active_work(kernel, principal, limit=20):
            line = {'kind': 'assignment', 'id': row['id'], 'title': row['title'], 'state': row['state_words'], 'reason': row['line']}
            if row['state_words'] == 'working':out['now'].append(line)
            elif row['state_words'] != 'ready':out['waiting'].append(line)
    except Exception:  # noqa: BLE001 - the Agenda is shown whole even when this slice's records cannot be read
        pass
    return out


def dispatch(kernel, op, args, principal):
    if op == 'assignment.start':return start(kernel, args, principal)
    if op == 'assignment.plan':return plan(kernel, args, principal)
    if op == 'assignment.step':return run(kernel, args['id'], principal, args.get('until', 'next'))
    if op == 'assignment.status':return status(kernel, args['id'], principal)
    if op == 'assignment.stop':return stop(kernel, args['id'], principal, args.get('why'))      # 1.0 K3: why
    if op == 'assignment.resume':return resume(kernel, args['id'], principal, args.get('carry_on', True))
    if op == 'assignment.list':return listing(kernel, args, principal)
    raise ValueError('Unknown assignment operation')


# ---------------------------------------------------------------- Rail Demo's three-step assignment (invented data)

RAIL_DEMO_OBJECTIVE = 'Read the Rail Demo bench readings, recompute the settled power, and write a note of it.'
RAIL_DEMO_NOTE = 'Slate/Rail Demo/Settled power note.txt'


def rail_demo_plan(kernel, principal):
    """The acceptance's assignment on Rail Demo: read the readings; recompute settled power; write a note. Returns
    {'objective', 'title', 'steps'} for assignment.start (every input says where it came from)."""
    from . import rail_demo
    demo = rail_demo.find(kernel, principal);read = _reader(kernel, principal)
    sheet = read('office.get', {'id': demo['sheets']['readings']})
    page = read('documents.get', {'id': demo['calculations']['settled_power']})['document']
    cell = ['document', 'sheets', '0', 'cells']
    objective = RAIL_DEMO_OBJECTIVE
    steps = [
        {'key': 'read', 'title': 'Read the Rail Demo bench readings', 'operation': 'office.get',
         'arguments': {'id': demo['sheets']['readings']},
         'origins': {'id': {'kind': 'RECORD', 'id': demo['sheets']['readings'], 'rev': sheet['revision']}},
         'outputs': {'sheet_revision': ['revision'], 'voltage': cell + ['B2', 'value'], 'voltage_unit': cell + ['B2', 'unit'],
                     'current': cell + [rail_demo.SETTLED_CELL, 'value'], 'current_unit': cell + [rail_demo.SETTLED_CELL, 'unit']},
         'expected': 'the readings sheet with its rail voltage (B2) and settled current (B3), at its current revision'},
        {'key': 'recompute', 'title': 'Recompute the settled power', 'operation': 'office.datasheet.recheck',
         'arguments': {'id': page['id'], 'expected_revision': page['revision']},
         'origins': {'id': {'kind': 'RECORD', 'id': page['id'], 'rev': page['revision']},
                     'expected_revision': {'kind': 'RECORD', 'id': page['id'], 'rev': page['revision']}},
         'outputs': {'power': ['value'], 'exact': ['exact'], 'unit': ['unit'], 'page': ['page']},
         'require': [{'path': ['inputs', 'B2'], 'equals': {'$step': 'read', 'path': ['voltage']}},
                     {'path': ['inputs', rail_demo.SETTLED_CELL], 'equals': {'$step': 'read', 'path': ['current']}},
                     {'path': ['sheet_revision'], 'equals': {'$step': 'read', 'path': ['sheet_revision']}}],
         'expected': 'a new settled power page replacing the old one, worked from the readings read in step 1, exact'},
        {'key': 'note', 'title': 'Write a note of the settled power', 'operation': 'files.write',
         'arguments': {'path': RAIL_DEMO_NOTE, 'text': {'$text': 'Rail Demo settled power: {power} {unit} (exact value {exact} {unit}).\n'
                                                                  'Worked again from the bench readings: {voltage} {voltage_unit} and {current} {current_unit}.\n'
                                                                  + rail_demo.NOTICE + '\n',
                                                         'with': {'power': {'$step': 'recompute', 'path': ['power']},
                                                                  'exact': {'$step': 'recompute', 'path': ['exact']},
                                                                  'unit': {'$step': 'recompute', 'path': ['unit']},
                                                                  'voltage': {'$step': 'read', 'path': ['voltage']},
                                                                  'voltage_unit': {'$step': 'read', 'path': ['voltage_unit']},
                                                                  'current': {'$step': 'read', 'path': ['current']},
                                                                  'current_unit': {'$step': 'read', 'path': ['current_unit']}}}},
         'origins': {'path': {'kind': 'DEDUCTION', 'proof': 'her notes go in her own area in Files, where her hand may write'}},
         'expected': 'the note in her area in Files, holding the recomputed settled power'},
    ]
    return {'objective': objective, 'title': 'Rail Demo: settled power, read, recomputed and noted', 'steps': steps}
