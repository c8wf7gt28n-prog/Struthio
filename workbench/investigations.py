"""Continuing investigations: repeat useful work, not confident prose (datasheet rev 1.2, sections 04 to 06).

An investigation keeps one question and continues it in bounded steps:

  question and snapshot → useful gap → permitted action → actual result → scoped check → updated understanding
  → continue, wait, or stop

Records, all in the Kernel's database and owned by the person who made them:

  sources   staC addresses read into the investigation, each with the digest of what was read (the snapshot)
  claims    findings, candidate explanations and open questions; a claim's evidence state is computed, never typed:
            UNKNOWN, SUPPORTED, REFUTED or CONFLICT, within the investigation's scope
  evidence  a source or a check result that supports or opposes a claim
  checks    a claim bound to a staC program and an oracle (what counts as success). A check passes only when the Kernel
            ran the program and the oracle held on the actual result. Nobody, Slate included, can mark a check passed.
  steps     every action that ran: its staC, the digests of its inputs, its outcome and a digest of its result

Rules the code enforces:
  - A repeat with unchanged inputs is recorded as a duplicate and adds no independent support.
  - When a source changes, old conclusions are kept, the evidence that depended on it stops counting, and the
    affected claims are marked for review. Nothing is overwritten.
  - Continuing is bounded by steps and seconds, and runs with read-only authority unless the owner widened it.
    The limit is enforced by the Kernel's permission checks, not by asking a model to behave.
  - A useful-answer rating or an approval is a decision, not evidence: no operation here turns one into support.
"""
from __future__ import annotations
import contextlib
import hashlib
import json
import re
import sqlite3
import time
import uuid
from .stac_bridge import route_program as run_with
from .stac_bridge import blocked_reason

ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$', 'maxLength': 32}
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 4000}
ROLES = ('FINDING', 'CANDIDATE', 'QUESTION')
DIRECTIONS = ('SUPPORTS', 'OPPOSES')
EXPECT = ('NONEMPTY', 'CONTAINS', 'NOT_CONTAINS', 'COUNT_AT_LEAST')
STATES = ('OPEN', 'WAITING', 'CRITERIA_SATISFIED', 'STOPPED')
ADDRESS = re.compile(r'@([a-z][a-z0-9_]*:[^\s|]+)')
BUDGET = {'type': 'object', 'additionalProperties': False,
          'properties': {'max_steps': {'type': 'integer', 'minimum': 1, 'maximum': 200},
                         'max_seconds': {'type': 'integer', 'minimum': 1, 'maximum': 3600},
                         'effects': {'type': 'string', 'enum': ['read', 'execute']}}}
FIELDS = {
    'investigation.create': ({'question': TEXT, 'objective': {'type': 'string', 'maxLength': 4000}, 'budget': BUDGET}, ['question']),
    'investigation.list': ({}, []),
    'investigation.sheet': ({'id': ID}, ['id']),
    'investigation.path': ({'claim': ID}, ['claim']),
    'investigation.add_source': ({'id': ID, 'address': {'type': 'string', 'minLength': 3, 'maxLength': 300}}, ['id', 'address']),
    'investigation.claim': ({'id': ID, 'text': TEXT, 'role': {'type': 'string', 'enum': list(ROLES)}}, ['id', 'text', 'role']),
    'investigation.evidence': ({'claim': ID, 'direction': {'type': 'string', 'enum': list(DIRECTIONS)}, 'source': ID,
                                'note': {'type': 'string', 'maxLength': 2000}}, ['claim', 'direction', 'source']),
    'investigation.check': ({'claim': ID, 'program': {'type': 'string', 'minLength': 1, 'maxLength': 8192}, 'oracle': TEXT,
                             'expect': {'type': 'string', 'enum': list(EXPECT)}, 'value': {'type': 'string', 'maxLength': 2000},
                             'refutes_on_fail': {'type': 'boolean'}}, ['claim', 'program', 'oracle', 'expect']),
    'investigation.step': ({'id': ID, 'program': {'type': 'string', 'minLength': 1, 'maxLength': 8192}, 'purpose': TEXT}, ['id', 'program', 'purpose']),
    'investigation.continue': ({'id': ID}, ['id']),
    'investigation.refresh': ({'id': ID}, ['id']),
    'investigation.review': ({'claim': ID, 'decision': {'type': 'string', 'enum': ['ACCEPT_CHANGE', 'RETIRE']}}, ['claim', 'decision']),
    'investigation.stop': ({'id': ID, 'reason': TEXT}, ['id', 'reason']),
}
SCOPES = {op: 'read' if op in ('investigation.list', 'investigation.sheet', 'investigation.path') else
          'approve' if op == 'investigation.review' else 'execute' for op in FIELDS}


@contextlib.contextmanager
def opened(kernel):
    with kernel.db() as db:
        db.row_factory = sqlite3.Row;yield db


def ensure(db):
    db.executescript('''
      CREATE TABLE IF NOT EXISTS inv_investigations(id TEXT PRIMARY KEY, owner TEXT, created REAL, updated REAL, question TEXT,
        objective TEXT, state TEXT, reason TEXT, budget TEXT, steps_used INTEGER, seconds_used REAL);
      CREATE TABLE IF NOT EXISTS inv_sources(id TEXT PRIMARY KEY, investigation TEXT, address TEXT, digest TEXT, current TEXT,
        state TEXT, added REAL);
      CREATE TABLE IF NOT EXISTS inv_claims(id TEXT PRIMARY KEY, investigation TEXT, role TEXT, text TEXT, review TEXT, retired INTEGER,
        created REAL);
      CREATE TABLE IF NOT EXISTS inv_checks(id TEXT PRIMARY KEY, claim TEXT, program TEXT, oracle TEXT, expect TEXT, value TEXT,
        refutes INTEGER, created REAL);
      CREATE TABLE IF NOT EXISTS inv_steps(id TEXT PRIMARY KEY, investigation TEXT, seq INTEGER, kind TEXT, purpose TEXT, program TEXT,
        inputs TEXT, input_key TEXT, check_id TEXT, outcome TEXT, result_digest TEXT, summary TEXT, duplicate_of TEXT,
        authority TEXT, started REAL, finished REAL);
      CREATE TABLE IF NOT EXISTS inv_evidence(id TEXT PRIMARY KEY, claim TEXT, direction TEXT, source TEXT, step TEXT, note TEXT,
        independence TEXT, created REAL, stale INTEGER DEFAULT 0);
      CREATE INDEX IF NOT EXISTS inv_steps_by ON inv_steps(investigation, seq);
      CREATE INDEX IF NOT EXISTS inv_evidence_by ON inv_evidence(claim);''')
    if 'stale' not in [r[1] for r in db.execute('PRAGMA table_info(inv_steps)')]:db.execute('ALTER TABLE inv_steps ADD COLUMN stale INTEGER DEFAULT 0')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def items_of(result):
    if isinstance(result, dict):
        for key in ('rows', 'hits', 'items', 'results', 'records', 'matches'):
            if isinstance(result.get(key), list):return result[key]
        if isinstance(result.get('result'), (dict, list)):return items_of(result['result'])
    return result if isinstance(result, list) else None


def oracle_holds(expect, value, result):
    """The check's oracle, applied mechanically to what actually came back."""
    text = json.dumps(result, sort_keys=True, default=str).casefold()
    found = items_of(result)
    if expect == 'NONEMPTY':return bool(found) if found is not None else bool(result) and text not in ('{}', '[]', 'null', '""')
    if expect == 'CONTAINS':return (value or '').casefold() in text
    if expect == 'NOT_CONTAINS':return (value or '').casefold() not in text
    if expect == 'COUNT_AT_LEAST':
        try:need = int(value or '1')
        except ValueError:raise ValueError('INVESTIGATION_CHECK_COUNT_IS_A_NUMBER')
        return found is not None and len(found) >= need
    raise ValueError('INVESTIGATION_UNKNOWN_EXPECTATION')


def summary(result, limit=600):
    try:
        from .office_building_qt import readable_result  # plain words when the desktop is present
        return readable_result(result)[:limit] if isinstance(result, dict) else str(result)[:limit]
    except Exception:
        return json.dumps(result, sort_keys=True, default=str)[:limit]


def owned(db, table, ident, owner):
    if table == 'inv_investigations':
        row = db.execute('SELECT * FROM inv_investigations WHERE id=? AND owner=?', (ident, owner)).fetchone()
    elif table == 'inv_claims':
        row = db.execute('SELECT c.* FROM inv_claims c JOIN inv_investigations i ON i.id=c.investigation WHERE c.id=? AND i.owner=?', (ident, owner)).fetchone()
    else:
        row = db.execute('SELECT s.* FROM inv_sources s JOIN inv_investigations i ON i.id=s.investigation WHERE s.id=? AND i.owner=?', (ident, owner)).fetchone()
    if row is None:raise ValueError('INVESTIGATION_RECORD_NOT_FOUND')
    return dict(row)


def read_address(kernel, address, principal):
    from . import addresses
    value = addresses.read(kernel, address.strip().removeprefix('@'), principal)
    return value['address'], digest(value['object'])


def inputs_of(kernel, investigation, program, principal):
    """The digests of every address a program reads, taken now: the step's input snapshot."""
    found = {}
    for address in sorted(set(ADDRESS.findall(program))):
        try:found[address] = read_address(kernel, address, principal)[1]
        except ValueError:found[address] = 'UNAVAILABLE'
    return found


def execute(kernel, investigation, program, principal, purpose, kind='STEP', check=None):
    """Run one staC program through the Kernel and record it. Returns the step row."""
    op, args = run_with(program)
    started = time.time()
    with opened(kernel) as db:
        ensure(db)
    inputs = inputs_of(kernel, investigation, program, principal)
    key = digest([program.strip(), inputs, check['id'] if check else None])
    with opened(kernel) as db:
        earlier = db.execute('SELECT id FROM inv_steps WHERE investigation=? AND input_key=? AND stale=0 AND outcome IN (?,?) ORDER BY seq LIMIT 1',
                             (investigation, key, 'PASSED', 'DONE')).fetchone()
    envelope = kernel.dispatch(op, args, principal)
    result = envelope.get('result') if envelope.get('ok') else None
    blocked = blocked_reason(result)
    if not envelope.get('ok'):outcome, text = 'FAILED', (envelope.get('error') or {}).get('message', 'did not run')
    elif blocked:outcome, text = 'FAILED', blocked
    elif check:
        held = oracle_holds(check['expect'], check['value'], result)
        outcome, text = ('PASSED' if held else 'CHECK_FAILED'), summary(result)
    else:outcome, text = 'DONE', summary(result)
    authority = ','.join(sorted(principal.scopes))
    with opened(kernel) as db:
        seq = (db.execute('SELECT max(seq) FROM inv_steps WHERE investigation=?', (investigation,)).fetchone()[0] or 0) + 1
        row = {'id': uuid.uuid4().hex, 'investigation': investigation, 'seq': seq, 'kind': kind, 'purpose': purpose, 'program': program,
               'inputs': json.dumps(inputs, sort_keys=True), 'input_key': key, 'check_id': check['id'] if check else None, 'outcome': outcome,
               'result_digest': digest(result) if result is not None else None, 'summary': text,
               'duplicate_of': earlier[0] if earlier else None, 'authority': authority, 'started': started, 'finished': time.time(), 'stale': 0}
        db.execute('INSERT INTO inv_steps(' + ','.join(row) + ') VALUES(' + ','.join('?' * len(row)) + ')', tuple(row.values()))
        if check and not earlier and outcome in ('PASSED', 'CHECK_FAILED'):
            direction = 'SUPPORTS' if outcome == 'PASSED' else ('OPPOSES' if check['refutes'] else None)
            if direction:
                db.execute('INSERT INTO inv_evidence VALUES(?,?,?,?,?,?,?,?,0)', (uuid.uuid4().hex, check['claim'], direction, None, row['id'],
                           'Check: ' + check['oracle'], 'check:' + key, time.time()))
        db.execute('UPDATE inv_investigations SET updated=?, steps_used=steps_used+1, seconds_used=seconds_used+? WHERE id=?',
                   (time.time(), row['finished'] - started, investigation))
    return row


def record_step(kernel, investigation, operation, arguments, principal, purpose, outcome, summary, result, inputs, kind='STEP', started=None, finished=None):
    """Record one step that already ran outside a staC program (HATCH AGENT-01: the agent loop's bounded operations and local helpers).

    Modelled on execute(): the program column holds {operation, arguments} as JSON text (the caller withholds secrets), inputs are
    the digests the caller took of what the step read, a repeat with the same program and inputs is marked a duplicate of the
    earlier DONE/PASSED row, and the investigation's steps_used and seconds_used advance. Nothing runs here; the row is the
    record of what ran, with the authority it ran with. Returns the step row."""
    program = json.dumps({'operation': operation, 'arguments': arguments}, sort_keys=True, default=str)
    inputs = dict(inputs or {})
    key = digest([program, inputs, None])
    finished = finished if finished is not None else time.time()
    started = started if started is not None else finished
    words = str(summary if summary is not None else '')[:600]
    with opened(kernel) as db:
        ensure(db)
        earlier = db.execute('SELECT id FROM inv_steps WHERE investigation=? AND input_key=? AND stale=0 AND outcome IN (?,?) ORDER BY seq LIMIT 1',
                             (investigation, key, 'PASSED', 'DONE')).fetchone()
        seq = (db.execute('SELECT max(seq) FROM inv_steps WHERE investigation=?', (investigation,)).fetchone()[0] or 0) + 1
        row = {'id': uuid.uuid4().hex, 'investigation': investigation, 'seq': seq, 'kind': kind, 'purpose': str(purpose or operation)[:4000], 'program': program,
               'inputs': json.dumps(inputs, sort_keys=True, default=str), 'input_key': key, 'check_id': None, 'outcome': outcome,
               'result_digest': digest(result) if result is not None else None, 'summary': words,
               'duplicate_of': earlier[0] if earlier else None, 'authority': ','.join(sorted(principal.scopes)), 'started': started, 'finished': finished, 'stale': 0}
        db.execute('INSERT INTO inv_steps(' + ','.join(row) + ') VALUES(' + ','.join('?' * len(row)) + ')', tuple(row.values()))
        db.execute('UPDATE inv_investigations SET updated=?, steps_used=steps_used+1, seconds_used=seconds_used+? WHERE id=?',
                   (time.time(), max(0.0, finished - started), investigation))
    return row


def claim_state(db, claim):
    """UNKNOWN, SUPPORTED, REFUTED or CONFLICT from current, independent evidence only."""
    current = [dict(r) for r in db.execute('SELECT * FROM inv_evidence WHERE claim=? AND stale=0', (claim['id'],))]
    positive = {r['independence'] for r in current if r['direction'] == 'SUPPORTS'}
    negative = {r['independence'] for r in current if r['direction'] == 'OPPOSES'}
    from sdk.cli.arc1cli.evidence_contracts import support as four_state
    return four_state(bool(positive), bool(negative)), len(positive), len(negative)


def sheet(db, investigation):
    """The useful top sheet: what was read, attempted, checked, learned and left unresolved, and the next useful action."""
    inv = dict(investigation)
    sources = [dict(r) for r in db.execute('SELECT * FROM inv_sources WHERE investigation=? ORDER BY added', (inv['id'],))]
    claims = [dict(r) for r in db.execute('SELECT * FROM inv_claims WHERE investigation=? ORDER BY created', (inv['id'],))]
    steps = [dict(r) for r in db.execute('SELECT * FROM inv_steps WHERE investigation=? ORDER BY seq', (inv['id'],))]
    checks = []
    for c in claims:
        state, plus, minus = claim_state(db, c);c.update(evidence_state=state, independent_support=plus, independent_opposition=minus)
        for k in db.execute('SELECT * FROM inv_checks WHERE claim=? ORDER BY created', (c['id'],)):
            k = dict(k);last = next((s for s in reversed(steps) if s['check_id'] == k['id']), None)
            outcome = 'NOT_RUN' if last is None else ('STALE' if last['stale'] else last['outcome'])
            k.update(claim_text=c['text'], last_outcome=outcome, last_step=last['id'] if last else None,
                     last_authority=last['authority'] if last else None);checks.append(k)
    live = [c for c in claims if not c['retired']]
    unresolved = ([c for c in live if c['role'] == 'QUESTION'] + [c for c in live if c['role'] != 'QUESTION' and c['evidence_state'] in ('UNKNOWN', 'CONFLICT')] +
                  [c for c in live if c['review'] == 'NEEDS_REVIEW'])
    seen = set();unresolved = [c for c in unresolved if not (c['id'] in seen or seen.add(c['id']))]
    nxt = next_action(inv, sources, live, checks)
    return {'id': inv['id'], 'question': inv['question'], 'objective': inv['objective'], 'state': inv['state'], 'reason': inv['reason'],
            'budget': json.loads(inv['budget']), 'used': {'steps': inv['steps_used'], 'seconds': round(inv['seconds_used'], 2)},
            'read': sources, 'attempted': [s for s in steps if s['kind'] == 'STEP'], 'checked': checks,
            'learned': [c for c in live if c['role'] != 'QUESTION' and c['evidence_state'] in ('SUPPORTED', 'REFUTED')],
            'unresolved': unresolved, 'retired': [c for c in claims if c['retired']], 'next': nxt,
            'notice': 'Evidence states are computed from current, independent evidence. A passed command, a useful answer, '
                      'a passed check and a justified conclusion are different things.'}


def next_action(inv, sources, live, checks):
    if inv['state'] == 'STOPPED':return {'kind': 'STOPPED', 'text': 'Stopped: ' + (inv['reason'] or '') + '. Continue to start again.'}
    changed = [s for s in sources if s['state'] == 'CHANGED']
    if changed:return {'kind': 'REVIEW', 'text': 'A source changed since it was read: ' + changed[0]['address'] + '. Review the affected claims.'}
    review = [c for c in live if c['review'] == 'NEEDS_REVIEW']
    if review:return {'kind': 'REVIEW', 'text': 'Decide whether to accept the change for: ' + review[0]['text'][:120]}
    pending = [k for k in checks if k['last_outcome'] in ('NOT_RUN', 'FAILED', 'STALE')]
    if pending:return {'kind': 'CHECK', 'text': 'Run the check: ' + pending[0]['oracle'][:160], 'check': pending[0]['id']}
    questions = [c for c in live if c['role'] == 'QUESTION']
    if questions:return {'kind': 'QUESTION', 'text': 'Find something that could answer: ' + questions[0]['text'][:160]}
    unchecked = [c for c in live if c['role'] != 'QUESTION' and not any(k['claim'] == c['id'] for k in checks)]
    if unchecked:return {'kind': 'BIND_CHECK', 'text': 'Say what would show this is true, as a check: ' + unchecked[0]['text'][:160]}
    if not live:return {'kind': 'CLAIM', 'text': 'Write down what you think is true, or what you need to find out.'}
    return {'kind': 'NONE', 'text': 'Every claim has a current check result. Continue only if something changes.'}


def settle(db, ident):
    """The investigation's state follows its sheet: criteria satisfied, waiting (and on what), or still open."""
    inv = db.execute('SELECT * FROM inv_investigations WHERE id=?', (ident,)).fetchone()
    if inv['state'] == 'STOPPED':return
    s = sheet(db, inv);live = [c for c in db.execute('SELECT * FROM inv_claims WHERE investigation=? AND retired=0', (ident,))]
    checked = s['checked']
    if s['next']['kind'] == 'NONE' and checked and all(k['last_outcome'] == 'PASSED' for k in checked if not k['refutes']) and live:
        state, reason = 'CRITERIA_SATISFIED', 'Declared checks hold on this snapshot. Exclusions stay visible.'
    elif s['next']['kind'] in ('REVIEW', 'QUESTION', 'BIND_CHECK', 'CLAIM'):
        state, reason = 'WAITING', s['next']['text']
    else:state, reason = 'OPEN', s['next']['text']
    db.execute('UPDATE inv_investigations SET state=?, reason=?, updated=? WHERE id=?', (state, reason, time.time(), ident))


def check_row(db, ident):
    row = db.execute('SELECT * FROM inv_checks WHERE id=?', (ident,)).fetchone()
    return dict(row) if row else None


def continue_(kernel, ident, principal):
    """Run what is due, within the budget and with the budget's authority; then stop, wait, or report satisfied."""
    from .engineering_kernel import Principal
    with opened(kernel) as db:
        inv = owned(db, 'inv_investigations', ident, principal.identity)
        budget = json.loads(inv['budget'])
        if inv['state'] == 'STOPPED':db.execute("UPDATE inv_investigations SET state='OPEN', reason='' WHERE id=?", (ident,))
    scopes = frozenset({'read'}) if budget.get('effects', 'read') == 'read' else principal.scopes & frozenset({'read', 'execute'})
    bounded = Principal(principal.identity, scopes, principal.paths, principal.tools, principal.mode)
    started, ran = time.time(), []
    while True:
        with opened(kernel) as db:
            inv = dict(db.execute('SELECT * FROM inv_investigations WHERE id=?', (ident,)).fetchone())
            if inv['steps_used'] >= budget.get('max_steps', 20) or time.time() - started > budget.get('max_seconds', 120):
                db.execute("UPDATE inv_investigations SET state='STOPPED', reason=? WHERE id=?", ('Budget used: ' + str(inv['steps_used']) + ' steps', ident))
                break
            due = sheet(db, inv)['next']
        if due['kind'] != 'CHECK':break
        check = None
        with opened(kernel) as db:check = check_row(db, due['check'])
        row = execute(kernel, ident, check['program'], bounded, 'Check: ' + check['oracle'], 'CHECK', check)
        ran.append({'step': row['id'], 'outcome': row['outcome'], 'duplicate_of': row['duplicate_of']})
        if row['outcome'] == 'FAILED':
            with opened(kernel) as db:
                db.execute("UPDATE inv_investigations SET state='WAITING', reason=? WHERE id=?", ('A check could not run: ' + row['summary'][:300], ident))
            break
    with opened(kernel) as db:
        if db.execute('SELECT state FROM inv_investigations WHERE id=?', (ident,)).fetchone()[0] not in ('STOPPED', 'WAITING') or not ran:settle(db, ident)
        out = sheet(db, db.execute('SELECT * FROM inv_investigations WHERE id=?', (ident,)).fetchone())
    out['ran'] = ran;out['authority'] = sorted(scopes)
    return out


def refresh(kernel, ident, principal):
    """Read every source again. A changed source keeps its old digest, stops counting, and marks dependent claims for review."""
    with opened(kernel) as db:
        owned(db, 'inv_investigations', ident, principal.identity)
        sources = [dict(r) for r in db.execute("SELECT * FROM inv_sources WHERE investigation=? AND state='CURRENT'", (ident,))]
    changed = []
    for s in sources:
        try:now = read_address(kernel, s['address'], principal)[1]
        except ValueError:now = 'UNAVAILABLE'
        if now != s['digest']:changed.append((s, now))
    with opened(kernel) as db:
        for s, now in changed:
            db.execute("UPDATE inv_sources SET state='CHANGED', current=? WHERE id=?", (now, s['id']))
            affected = {r[0] for r in db.execute('SELECT claim FROM inv_evidence WHERE source=?', (s['id'],))}
            db.execute('UPDATE inv_evidence SET stale=1 WHERE source=?', (s['id'],))
            for step in db.execute('SELECT id, inputs, check_id FROM inv_steps WHERE investigation=? AND stale=0', (ident,)).fetchall():
                if s['address'] in json.loads(step['inputs']):
                    db.execute('UPDATE inv_steps SET stale=1 WHERE id=?', (step['id'],))
                    db.execute('UPDATE inv_evidence SET stale=1 WHERE step=?', (step['id'],))
                    k = check_row(db, step['check_id']) if step['check_id'] else None
                    if k:affected.add(k['claim'])
            for claim in affected:db.execute("UPDATE inv_claims SET review='NEEDS_REVIEW' WHERE id=?", (claim,))
        settle(db, ident)
        out = sheet(db, db.execute('SELECT * FROM inv_investigations WHERE id=?', (ident,)).fetchone())
    out['changed'] = [s['address'] for s, _ in changed]
    return out


def path(db, claim):
    """The evidence path: why a claim stands, back to the exact source digests and Kernel steps."""
    state, plus, minus = claim_state(db, claim)
    links = []
    for e in db.execute('SELECT * FROM inv_evidence WHERE claim=? ORDER BY created', (claim['id'],)):
        e = dict(e);link = {'direction': e['direction'], 'note': e['note'], 'independence': e['independence']}
        if e['source']:
            s = dict(db.execute('SELECT * FROM inv_sources WHERE id=?', (e['source'],)).fetchone())
            link.update(kind='SOURCE', address=s['address'], digest=s['digest'], counts=not e['stale'], source_state=s['state'])
        else:
            st = dict(db.execute('SELECT * FROM inv_steps WHERE id=?', (e['step'],)).fetchone())
            link.update(kind='CHECK', step=st['id'], program=st['program'], inputs=json.loads(st['inputs']), outcome=st['outcome'],
                        result_digest=st['result_digest'], ran_with=st['authority'], counts=not e['stale'])
        links.append(link)
    return {'claim': claim['id'], 'text': claim['text'], 'role': claim['role'], 'evidence_state': state, 'independent_support': plus,
            'independent_opposition': minus, 'review': claim['review'], 'path': links}


def dispatch(kernel, op, args, principal):
    owner = principal.identity
    with opened(kernel) as db:ensure(db)
    if op == 'investigation.create':
        budget = {'max_steps': 20, 'max_seconds': 120, 'effects': 'read', **args.get('budget', {})}
        ident = uuid.uuid4().hex
        with opened(kernel) as db:
            db.execute('INSERT INTO inv_investigations VALUES(?,?,?,?,?,?,?,?,?,?,?)', (ident, owner, time.time(), time.time(), args['question'],
                       args.get('objective', ''), 'WAITING', 'Write down what you think is true, or what you need to find out.', json.dumps(budget), 0, 0.0))
            return sheet(db, db.execute('SELECT * FROM inv_investigations WHERE id=?', (ident,)).fetchone())
    if op == 'investigation.list':
        with opened(kernel) as db:
            return {'investigations': [dict(r) for r in db.execute('SELECT id, question, state, reason, updated, steps_used FROM inv_investigations '
                                                                    'WHERE owner=? ORDER BY updated DESC', (owner,))]}
    if op == 'investigation.sheet':
        with opened(kernel) as db:return sheet(db, owned(db, 'inv_investigations', args['id'], owner))
    if op == 'investigation.path':
        with opened(kernel) as db:return path(db, owned(db, 'inv_claims', args['claim'], owner))
    if op == 'investigation.add_source':
        with opened(kernel) as db:owned(db, 'inv_investigations', args['id'], owner)
        address, value = read_address(kernel, args['address'], principal)
        with opened(kernel) as db:
            known = db.execute("SELECT id FROM inv_sources WHERE investigation=? AND address=? AND state IN ('CURRENT','CHANGED')", (args['id'], address)).fetchone()
            if known:raise ValueError('INVESTIGATION_SOURCE_ALREADY_READ: refresh to compare it again')
            ident = uuid.uuid4().hex
            db.execute('INSERT INTO inv_sources VALUES(?,?,?,?,?,?,?)', (ident, args['id'], address, value, value, 'CURRENT', time.time()))
            settle(db, args['id'])
            return {'source': ident, 'address': address, 'digest': value}
    if op == 'investigation.claim':
        with opened(kernel) as db:
            owned(db, 'inv_investigations', args['id'], owner);ident = uuid.uuid4().hex
            db.execute('INSERT INTO inv_claims VALUES(?,?,?,?,?,?,?)', (ident, args['id'], args['role'], args['text'], 'CURRENT', 0, time.time()))
            settle(db, args['id'])
            return {'claim': ident, 'evidence_state': 'UNKNOWN'}
    if op == 'investigation.evidence':
        with opened(kernel) as db:
            claim = owned(db, 'inv_claims', args['claim'], owner);source = owned(db, 'inv_sources', args['source'], owner)
            if source['investigation'] != claim['investigation']:raise ValueError('INVESTIGATION_SOURCE_FROM_ANOTHER_INVESTIGATION')
            if source['state'] != 'CURRENT':raise ValueError('INVESTIGATION_SOURCE_CHANGED: review it first')
            # Independence is the source's content: the same bytes cited twice are one piece of evidence.
            db.execute('INSERT INTO inv_evidence VALUES(?,?,?,?,?,?,?,?,0)', (uuid.uuid4().hex, claim['id'], args['direction'], source['id'], None,
                       args.get('note', ''), 'source:' + source['digest'], time.time()))
            settle(db, claim['investigation'])
            return path(db, claim)
    if op == 'investigation.check':
        with opened(kernel) as db:
            claim = owned(db, 'inv_claims', args['claim'], owner)
            if claim['role'] == 'QUESTION':raise ValueError('INVESTIGATION_QUESTION_HAS_NO_CHECK: write the claim it would establish')
            if args['expect'] == 'COUNT_AT_LEAST':int(args.get('value') or '1')
            run_with(args['program']);ident = uuid.uuid4().hex
            db.execute('INSERT INTO inv_checks VALUES(?,?,?,?,?,?,?,?)', (ident, claim['id'], args['program'], args['oracle'], args['expect'],
                       args.get('value', ''), int(bool(args.get('refutes_on_fail'))), time.time()))
            settle(db, claim['investigation'])
            return {'check': ident, 'claim': claim['id'], 'last_outcome': 'NOT_RUN'}
    if op == 'investigation.step':
        with opened(kernel) as db:owned(db, 'inv_investigations', args['id'], owner)
        row = execute(kernel, args['id'], args['program'], principal, args['purpose'])
        with opened(kernel) as db:settle(db, args['id'])
        return {'step': row['id'], 'outcome': row['outcome'], 'summary': row['summary'], 'duplicate_of': row['duplicate_of'],
                'inputs': json.loads(row['inputs'])}
    if op == 'investigation.continue':return continue_(kernel, args['id'], principal)
    if op == 'investigation.refresh':return refresh(kernel, args['id'], principal)
    if op == 'investigation.review':
        with opened(kernel) as db:
            claim = owned(db, 'inv_claims', args['claim'], owner)
            if args['decision'] == 'RETIRE':db.execute("UPDATE inv_claims SET retired=1, review='CURRENT' WHERE id=?", (claim['id'],))
            else:
                # Accept the change: the new contents become the snapshot. Evidence from the old contents keeps its record but stops counting.
                db.execute("UPDATE inv_claims SET review='CURRENT' WHERE id=?", (claim['id'],))
                for s in db.execute("SELECT * FROM inv_sources WHERE investigation=? AND state='CHANGED'", (claim['investigation'],)).fetchall():
                    db.execute("UPDATE inv_sources SET state='SUPERSEDED' WHERE id=?", (s['id'],))
                    db.execute('INSERT INTO inv_sources VALUES(?,?,?,?,?,?,?)', (uuid.uuid4().hex, s['investigation'], s['address'],
                               s['current'], s['current'], 'CURRENT', time.time()))
            settle(db, claim['investigation'])
            return path(db, dict(db.execute('SELECT * FROM inv_claims WHERE id=?', (claim['id'],)).fetchone()))
    if op == 'investigation.stop':
        with opened(kernel) as db:
            owned(db, 'inv_investigations', args['id'], owner)
            db.execute("UPDATE inv_investigations SET state='STOPPED', reason=?, updated=? WHERE id=?", ('By you: ' + args['reason'], time.time(), args['id']))
            return sheet(db, db.execute('SELECT * FROM inv_investigations WHERE id=?', (args['id'],)).fetchone())
    raise ValueError('Unknown investigation operation')
