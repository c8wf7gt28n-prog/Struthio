"""Slate's Agenda: what he is doing, what comes next, what he is waiting for (Current Plans rev 1.3, section 05).

It is not a calendar and not a second scheduler. It shows the Kernel's own jobs and investigations beside a short list of
agenda items, and runs one item at a time, in order. Legacy items retain read-only
authority; Stage Five work rows use only their separately reviewed frozen grant.

  NOW        running Kernel jobs and the agenda item being run
  NEXT       items in your order; a Kernel job that is queued
  WAITING    whatever needs you: a job waiting for approval, an investigation waiting on a decision, a suggestion
  LATER      items with a time (once, or repeating by your explicit choice)
  SUGGESTED  next steps Slate proposed; they do nothing until you add them to Next
  DONE       what finished, failed or was cancelled, with the actual outcome

Niceness borrows from Unix nice(1): every item is 'now', 'normal' or 'background'. Items run in that order, and
background items wait until the computer is idle, so they yield to you and to everything else. (CPU priority for
Ledger's own worker processes stays the existing "Be nice" setting on Stop's menu.)

Rules the code enforces, not a model:
  - Slate can suggest; only you add a suggestion to Next (agenda.accept needs the approve scope).
  - A suggestion must say what is new. The same suggestion twice under one item is refused.
  - Each item has a round budget (default 4). Two rounds in a row that produce nothing new stop it with a reason.
  - A repeating item that was missed while the computer was off runs once on return, never once per missed time.
  - Running an item uses read-only authority. Pausing, cancelling and reordering never need code.
"""
from __future__ import annotations
import contextlib
import hashlib
import json
import sqlite3
import time
import uuid
from pathlib import Path

ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$', 'maxLength': 32}
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 400}
NICE = ('now', 'normal', 'background')
NICE_RANK = {'now': 0, 'normal': 1, 'background': 2}
OPEN = ('NEXT', 'LATER', 'RUNNING', 'PAUSED', 'SUGGESTED')
FINAL = ('DONE', 'FAILED', 'CANCELLED', 'DECLINED', 'STOPPED')
MAX_SUGGESTIONS = 3
QUIET_LIMIT = 2
MISSED_GRACE = 300.0
WHEN = {'type': 'object', 'additionalProperties': False,
        'properties': {'at': {'type': 'number', 'minimum': 0}, 'every_hours': {'type': 'number', 'minimum': 1, 'maximum': 24 * 366},
                       'after': ID, 'idle': {'type': 'boolean'}, 'timezone': {'type': 'string', 'maxLength': 64}}}
FIELDS = {
    'agenda.view': ({}, []),
    'agenda.add': ({'title': TEXT, 'program': {'type': 'string', 'minLength': 1, 'maxLength': 8192}, 'investigation': ID,
                    'nice': {'type': 'string', 'enum': list(NICE)}, 'when': WHEN, 'rounds': {'type': 'integer', 'minimum': 1, 'maximum': 20},
                    'watch': {'type': 'boolean'}, 'copy': ID}, ['title']),
    'agenda.suggest': ({'parent': ID, 'title': TEXT, 'why': TEXT, 'program': {'type': 'string', 'minLength': 1, 'maxLength': 8192}},
                       ['parent', 'title', 'why']),
    'agenda.accept': ({'id': ID}, ['id']),
    'agenda.decline': ({'id': ID}, ['id']),
    'agenda.nice': ({'id': ID, 'nice': {'type': 'string', 'enum': list(NICE)}}, ['id', 'nice']),
    'agenda.move': ({'id': ID, 'position': {'type': 'integer', 'minimum': 0, 'maximum': 1000}}, ['id', 'position']),
    'agenda.reorder': ({'id': ID, 'position': {'type':'integer','minimum':0,'maximum':1000}}, ['id','position']),
    'agenda.pause': ({'id': ID}, ['id']),
    'agenda.resume': ({'id': ID}, ['id']),
    'agenda.cancel': ({'id': ID, 'reason': {'type': 'string', 'maxLength': 400}}, ['id']),
    'agenda.run_next': ({'idle': {'type': 'boolean'}}, []),
    'agenda.seen': ({'id': ID}, ['id']),
}
SCOPES = {'agenda.view': 'read', 'agenda.add': 'execute', 'agenda.suggest': 'execute', 'agenda.accept': 'approve',
          'agenda.decline': 'approve', 'agenda.nice': 'approve', 'agenda.move': 'approve', 'agenda.reorder':'approve', 'agenda.pause': 'approve',
          'agenda.resume': 'approve', 'agenda.cancel': 'approve', 'agenda.run_next': 'execute', 'agenda.seen': 'approve'}


@contextlib.contextmanager
def opened(kernel):
    with kernel.db() as db:
        db.row_factory = sqlite3.Row;ensure(db);yield db


def ensure(db):
    db.execute('''CREATE TABLE IF NOT EXISTS agenda_items(id TEXT PRIMARY KEY, owner TEXT, title TEXT, why TEXT, program TEXT,
        investigation TEXT, nice TEXT, position REAL, state TEXT, origin TEXT, parent TEXT, rounds INTEGER, rounds_used INTEGER,
        quiet INTEGER, last_digest TEXT, due REAL, every REAL, after TEXT, idle INTEGER, timezone TEXT, missed INTEGER,
        outcome TEXT, reason TEXT, created REAL, updated REAL, finished REAL)''')
    db.execute('CREATE INDEX IF NOT EXISTS agenda_by_owner ON agenda_items(owner, state, position)')
    columns = [r[1] for r in db.execute('PRAGMA table_info(agenda_items)')]
    if 'job' not in columns:db.execute('ALTER TABLE agenda_items ADD COLUMN job TEXT')
    for name, kind in (('watch', 'INTEGER DEFAULT 0'), ('changed', 'INTEGER DEFAULT 0'), ('last_rows', 'TEXT'), ('copy', 'TEXT')):  # 4.6 watches; Pass B copies
        if name not in columns:db.execute('ALTER TABLE agenda_items ADD COLUMN %s %s' % (name, kind))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()


def owned(db, ident, owner):
    row = db.execute('SELECT * FROM agenda_items WHERE id=? AND owner=?', (ident, owner)).fetchone()
    if row is None:raise ValueError('AGENDA_ITEM_NOT_FOUND')
    return row


def last_position(db, owner):
    return (db.execute("SELECT max(position) FROM agenda_items WHERE owner=? AND state IN ('NEXT','LATER','PAUSED')", (owner,)).fetchone()[0] or 0) + 1


def item(row):
    value = dict(row)
    value['origin_words'] = 'Graphite suggested' if value['origin'] == 'slate' else 'you added'
    return value


def kernel_rows(kernel, principal):
    """The Kernel's own jobs and investigations, as Agenda rows. Read-only: nothing here starts or changes work."""
    from .operation_stop import TERMINAL, WAITING
    rows = {'now': [], 'next': [], 'waiting': []}
    from . import record_access
    try:jobs = record_access.listing(kernel,'jobs',principal)
    except (OSError, ValueError, sqlite3.Error):jobs = []
    for job in jobs:
        state = job.get('state')
        if state in TERMINAL:continue
        from .job_priority import describe
        row = {'kind': 'job', 'id': job.get('id'), 'title': str(job.get('tool', 'Job')), 'state': state, 'started': job.get('started'),'created':job.get('created'),
               'resource_request':job.get('resource_request'),'resource_wait':job.get('resource_wait'),
               'reason':(job.get('resource_wait') or {}).get('reason'),
               **describe(kernel,job,principal)}
        if state == 'Running':rows['now'].append(row)
        elif state in WAITING:rows['waiting'].append({**row, 'reason': state})
        else:rows['next'].append(row)
    try:
        from . import investigations
        with investigations.opened(kernel) as db:
            investigations.ensure(db)
            for inv in db.execute("SELECT id, question, reason FROM inv_investigations WHERE owner=? AND state='WAITING' ORDER BY updated DESC LIMIT 5",
                                  (principal.identity,)):
                rows['waiting'].append({'kind': 'investigation', 'id': inv['id'], 'title': inv['question'], 'reason': inv['reason']})
    except (OSError, ValueError, sqlite3.Error):pass
    try:
        from . import files_service
        with files_service.opened(kernel) as db:
            for row in db.execute("SELECT id, path, why FROM files_proposals WHERE owner=? AND state='WAITING' ORDER BY at", (principal.identity,)):
                rows['waiting'].append({'kind': 'proposal', 'id': row['id'], 'title': 'Change ' + row['path'], 'reason': 'Graphite proposed it: ' + row['why'],
                                        'path': row['path']})
    except (OSError, ValueError, sqlite3.Error):pass
    return rows


def missed(db, owner, clock):
    """A time that passed while the computer was off or asleep: shown, then run once, never replayed in a burst."""
    found = []
    for row in db.execute("SELECT * FROM agenda_items WHERE owner=? AND state='LATER' AND due IS NOT NULL AND due < ?", (owner, clock - MISSED_GRACE)):
        if row['every']:
            step = row['every'];skipped = int((clock - row['due']) // step)
            nxt = row['due'] + (skipped + 1) * step
            db.execute("UPDATE agenda_items SET state='NEXT', missed=missed+?, due=?, reason=?, updated=? WHERE id=?",
                       (skipped + 1, nxt, 'Missed %d time%s while the computer was unavailable; runs once now.' % (skipped + 1, '' if skipped == 0 else 's'), clock, row['id']))
        else:
            db.execute("UPDATE agenda_items SET state='NEXT', missed=missed+1, reason=?, updated=? WHERE id=?",
                       ('Its time passed while the computer was unavailable; runs once now.', clock, row['id']))
        found.append(row['id'])
    for row in db.execute("SELECT id FROM agenda_items WHERE owner=? AND state='LATER' AND due IS NOT NULL AND due <= ? AND due >= ?",
                          (owner, clock, clock - MISSED_GRACE)):
        db.execute("UPDATE agenda_items SET state='NEXT', updated=? WHERE id=?", (clock, row['id']))
    return found


def view(kernel, principal, clock=None):
    clock = time.time() if clock is None else clock
    with opened(kernel) as db:
        missed(db, principal.identity, clock)
        rows = [item(r) for r in db.execute('SELECT * FROM agenda_items WHERE owner=? ORDER BY position, created', (principal.identity,))]
    live = kernel_rows(kernel, principal)
    from . import continuing_work
    live['waiting'] += continuing_work.agenda_rows(kernel,principal)
    by_id = {r['id']: r for r in rows}
    for r in rows:  # an item waiting on one that failed says so, instead of waiting silently
        before = by_id.get(r['after']) if r['after'] else None
        if r['state'] == 'NEXT' and before and before['state'] in ('FAILED', 'CANCELLED', 'STOPPED', 'DECLINED'):
            r['reason'] = 'Waits for "%s", which %s. Remove this, or add that again.' % (
                before['title'][:80], {'FAILED': 'could not run', 'CANCELLED': 'was cancelled', 'STOPPED': 'was stopped'}.get(before['state'], 'was declined'))
    order = lambda r:(NICE_RANK.get(r['nice'], 1), r['position'] or 0, r['created'])
    out = {'schema': 'arc.agenda/1',
           'now': live['now'] + [r for r in rows if r['state'] == 'RUNNING'],
           'next': sorted([r for r in rows if r['state'] in ('NEXT', 'PAUSED')], key=order) + live['next'],
           'waiting': live['waiting'],
           'later': sorted([r for r in rows if r['state'] == 'LATER'], key=lambda r:r['due'] or 0),
           'suggested': [r for r in rows if r['state'] == 'SUGGESTED'],
           'done': sorted([r for r in rows if r['state'] in FINAL and r['state'] != 'DECLINED'], key=lambda r:-(r['finished'] or 0))[:20],
           'rules': {'max_suggestions': MAX_SUGGESTIONS, 'quiet_limit': QUIET_LIMIT, 'authority': 'read',
                     'continuing_work_authority':'SEPARATE_EXACT_OWNER_GRANT'}}
    out['waiting'] = [{'kind': 'watch', 'id': r['id'], 'title': 'A watched question changed: ' + r['title'][:120], 'reason': r['outcome'], 'program': r['program']}
                      for r in rows if r.get('watch') and r.get('changed')] + out['waiting']
    if out['suggested']:out['waiting'] = out['waiting'] + [{'kind': 'suggestions', 'title': '%d suggestion%s from Graphite' % (
        len(out['suggested']), '' if len(out['suggested']) == 1 else 's'), 'reason': 'Add them to Next, or say not now.'}]
    out['counts'] = {k: len(out[k]) for k in ('now', 'next', 'waiting', 'later', 'suggested')}
    return out


COLUMNS = ('id', 'owner', 'title', 'why', 'program', 'investigation', 'nice', 'position', 'state', 'origin', 'parent', 'rounds', 'rounds_used',
           'quiet', 'last_digest', 'due', 'every', 'after', 'idle', 'timezone', 'missed', 'outcome', 'reason', 'created', 'updated', 'finished', 'job', 'copy')


def add(kernel, args, principal, origin='you', parent=None, why='', state=None):
    when = args.get('when') or {}
    if args.get('investigation'):
        from . import investigations
        with investigations.opened(kernel) as idb:
            investigations.ensure(idb);investigations.owned(idb, 'inv_investigations', args['investigation'], principal.identity)
    if args.get('copy'):  # Pass B: Slate works on a working copy you gave him; his result waits as a revision for your review
        from . import working_copies
        with working_copies.opened(kernel) as cdb:
            c = working_copies.the_copy(cdb, args['copy'])
        if not c['for_slate'] or c['state'] != 'WORKING':raise ValueError('AGENDA_COPY_NOT_GIVEN: give Graphite this working copy first')
        if (c['kind'] or 'file') != 'file':raise ValueError('AGENDA_COPY_ONE_FILE: Graphite rewrites one file at a time')
        if args.get('program'):raise ValueError('AGENDA_COPY_IN_WORDS: say in words what Graphite should do with the copy')
    with opened(kernel) as db:
        if when.get('after'):owned(db, when['after'], principal.identity)
        ident = uuid.uuid4().hex;clock = time.time()
        due = when.get('at');every = when.get('every_hours')
        state = state or ('LATER' if due and due > clock + 1 else 'NEXT')
        db.execute('INSERT INTO agenda_items(' + ','.join(COLUMNS) + ') VALUES(' + ','.join('?' * len(COLUMNS)) + ')',  # named: later columns keep their defaults
                   (ident, principal.identity, args['title'], why, args.get('program'), args.get('investigation'), args.get('nice', 'normal'),
                    last_position(db, principal.identity), state, origin, parent, args.get('rounds', 4), 0, 0, None,
                    due, every * 3600.0 if every else None, when.get('after'), int(bool(when.get('idle'))), when.get('timezone'), 0,
                    None, None, clock, clock, None, None, args.get('copy')))
        if args.get('watch'):  # a watch: asked now for a first answer, then again on its schedule; it tells you only about changes
            if not args.get('program'):raise ValueError('AGENDA_WATCH_NEEDS_STAC: a watch keeps asking a staC question')
            db.execute("UPDATE agenda_items SET watch=1, every=?, due=?, state='NEXT' WHERE id=?", ((every or WATCH_HOURS) * 3600.0, clock, ident))
        return item(owned(db, ident, principal.identity))


def suggest(kernel, args, principal):
    """Slate proposes a next step under an item. It runs nothing; it waits for you."""
    with opened(kernel) as db:
        parent = owned(db, args['parent'], principal.identity)
        if parent['state'] == 'STOPPED':raise ValueError('AGENDA_STOPPED: ' + (parent['reason'] or 'stopped'))
        if parent['quiet'] >= QUIET_LIMIT:raise ValueError('AGENDA_NO_NEW_PROGRESS: two rounds found nothing new; ask before going on')
        if parent['rounds_used'] >= parent['rounds']:raise ValueError('AGENDA_ROUND_BUDGET_USED: %d of %d rounds' % (parent['rounds_used'], parent['rounds']))
        open_ = db.execute("SELECT count(*) FROM agenda_items WHERE parent=? AND state='SUGGESTED'", (parent['id'],)).fetchone()[0]
        if open_ >= MAX_SUGGESTIONS:raise ValueError('AGENDA_ENOUGH_SUGGESTIONS: answer the open ones first')
        key = digest([args['title'].strip().casefold(), (args.get('program') or '').strip()])
        for row in db.execute('SELECT title, program FROM agenda_items WHERE parent=?', (parent['id'],)):
            if digest([row['title'].strip().casefold(), (row['program'] or '').strip()]) == key:
                raise ValueError('AGENDA_SAME_SUGGESTION: already suggested once under this item')
    return add(kernel, {'title': args['title'], 'program': args.get('program'), 'nice': parent['nice']}, principal,
               origin='slate', parent=parent['id'], why=args['why'], state='SUGGESTED')


def finish(db, row, state, outcome, reason=None):
    db.execute('UPDATE agenda_items SET state=?, outcome=?, reason=?, finished=?, updated=? WHERE id=?',
               (state, outcome, reason, time.time(), time.time(), row['id']))


def ready(db, row, idle, clock):
    if row['after']:
        before = db.execute('SELECT state FROM agenda_items WHERE id=? AND owner=?', (row['after'],row['owner'])).fetchone()
        if before is None or before['state'] != 'DONE':return False
    if row['due'] and row['due'] > clock and not (row['state']=='NEXT' and (row['reason'] or '').startswith('Missed ')):return False
    if (row['idle'] or row['nice'] == 'background') and not idle:return False
    return True


def run_next(kernel, args, principal, clock=None, work_only=False, selected_work=None):
    """Run the first ready item, once, with read-only authority. Returns what ran, or why nothing did."""
    from .engineering_kernel import Principal
    clock = time.time() if clock is None else clock
    from . import continuing_work, work_trail
    if work_trail.execution_held(kernel):return {'ran':None,'reason':'WORK_HELD_USE_EXPLICIT_RESUME'}
    from .ledger_control import value
    if not value(kernel,'operations.services_enabled'):return {'ran':None,'reason':'LEDGER_SERVICES_OFF'}
    slate_on = value(kernel,'stacy.enabled')
    # The Agenda execution lock proves a lingering work row has no live runner.
    with opened(kernel) as db:
        for agenda_id,work_id in db.execute("SELECT a.id,f.work FROM agenda_items a JOIN flow_agenda f ON f.agenda=a.id WHERE a.owner=? AND a.state='RUNNING'",(principal.identity,)).fetchall():
            plan,state=continuing_work.load(db,work_id,principal)
            state.update(state='PAUSED',reason='INTERRUPTED_STEP_REQUIRES_EXPLICIT_RESUME')
            continuing_work.save(db,plan,state,'INTERRUPTION_OBSERVED')
        missed(db,principal.identity,clock)
        for row in db.execute("SELECT * FROM agenda_items WHERE owner=? AND state='RUNNING' AND job IS NOT NULL",(principal.identity,)).fetchall():collect(kernel,db,row,principal)
        if db.execute("SELECT 1 FROM agenda_items WHERE owner=? AND state='RUNNING'",(principal.identity,)).fetchone():return {'ran':None,'reason':'Another agenda item is running.'}
        candidates=sorted(db.execute("SELECT * FROM agenda_items WHERE owner=? AND state='NEXT'",(principal.identity,)),
            key=lambda r:(NICE_RANK.get(r['nice'],1),r['position'] or 0,r['created']))
        selected=None;work_id=None
        for row in candidates:
            linked=continuing_work.linked(db,row['id'])
            if not slate_on and linked:continue  # keep AI continuations queued while the owner has Slate off
            if work_only and not linked or selected_work is not None and linked!=selected_work:continue
            if not ready(db,row,bool(args.get('idle')),clock):continue
            selected=row;work_id=linked;break
    from .resource_control import scope
    priority={'now':'foreground','normal':'normal','background':'background'}
    if work_id is not None:
        with scope(priority[selected['nice']]):return continuing_work.advance(kernel,work_id,principal)
    if work_only or selected_work is not None:return {'ran':None,'reason':'No granted continuing assignment is ready.'}
    with opened(kernel) as db:
        missed(db, principal.identity, clock)
        for row in db.execute("SELECT * FROM agenda_items WHERE owner=? AND state='RUNNING' AND job IS NOT NULL", (principal.identity,)).fetchall():
            collect(kernel, db, row, principal)
        if db.execute("SELECT 1 FROM agenda_items WHERE owner=? AND state='RUNNING'", (principal.identity,)).fetchone():
            return {'ran': None, 'reason': 'Another agenda item is running.'}
        candidates = sorted(db.execute("SELECT * FROM agenda_items WHERE owner=? AND state='NEXT'", (principal.identity,)),
                            key=lambda r:(NICE_RANK.get(r['nice'], 1), r['position'] or 0, r['created']))
        row = next((r for r in candidates if ready(db, r, bool(args.get('idle')), clock)
                    and (slate_on or not continuing_work.linked(db,r['id'])
                         and (r['program'] or r['investigation']) and not r['copy'])), None)
        if row is None:return {'ran': None, 'reason': 'Nothing is ready.' if candidates else 'Nothing is next.'}
        if row['copy']:
            with scope(priority[row['nice']]):return work_on_copy(kernel, db, row, principal, clock)
        if not row['program'] and not row['investigation']:
            with scope(priority[row['nice']]):return ask_slate(kernel, db, row, principal, clock)
        db.execute("UPDATE agenda_items SET state='RUNNING', updated=? WHERE id=?", (clock, row['id']))
    bounded = Principal(principal.identity, frozenset({'read'}), principal.paths, principal.tools, principal.mode)
    try:
        if row['investigation']:
            with scope(priority[row['nice']]):
                envelope = kernel.dispatch('investigation.continue', {'id': row['investigation']}, Principal(principal.identity, frozenset({'read', 'execute'}),
                                           principal.paths, principal.tools, principal.mode))
            result = envelope.get('result') if envelope.get('ok') else None
            fresh = [s for s in (result or {}).get('ran', []) if not s.get('duplicate_of')]
            progress = bool(fresh)
        else:
            from .investigations import run_with
            from .stac_bridge import blocked_reason
            op, op_args = run_with(row['program'])
            with scope(priority[row['nice']]):envelope = kernel.dispatch(op, op_args, bounded)
            result = envelope.get('result') if envelope.get('ok') else None
            blocked = blocked_reason(result)
            if blocked:envelope, result = {'ok': False, 'error': {'message': blocked}}, None
            progress = None
    except Exception as exc:  # a failure is recorded as a failure, never as done
        envelope, result, progress = {'ok': False, 'error': {'message': str(exc)}}, None, False
    with opened(kernel) as db:
        row = owned(db, row['id'], principal.identity)
        if row['state'] != 'RUNNING':return {'ran': row['id'], 'state': row['state']}  # cancelled while it ran
        result_digest = digest(result) if result is not None else None
        if progress is None:progress = result_digest is not None and result_digest != row['last_digest']
        quiet = 0 if progress else row['quiet'] + 1
        db.execute('UPDATE agenda_items SET rounds_used=rounds_used+1, quiet=?, last_digest=coalesce(?, last_digest) WHERE id=?',
                   (quiet, result_digest, row['id']))
        watched = row['watch'] and envelope.get('ok') and watch_words(db, row, result)
        if not envelope.get('ok'):
            finish(db, row, 'FAILED', (envelope.get('error') or {}).get('message', 'did not run'))
        elif row['every'] and (row['due'] or row['watch']):  # repeating, and every watch, comes back on its schedule
            nxt = row['due'] if row['due'] and row['due']>clock else (row['due'] or clock) + row['every']
            while nxt <= clock:nxt += row['every']
            db.execute("UPDATE agenda_items SET state='LATER', due=?, outcome=?, reason=NULL, updated=? WHERE id=?",
                       (nxt, watched or outcome_words(result, progress), clock, row['id']))
        elif quiet >= QUIET_LIMIT:
            finish(db, row, 'STOPPED', outcome_words(result, progress), 'Stopped: %d rounds found nothing new.' % quiet)
        else:
            finish(db, row, 'DONE', outcome_words(result, progress))
        state = owned(db, row['id'], principal.identity)['state']
    suggested = propose(kernel, principal, row) if state == 'DONE' else []
    return {'ran': row['id'], 'state': state, 'progress': progress, 'authority': ['read'], 'suggested': suggested}


RETRY_AFTER = 600.0
WATCH_HOURS = 6
WATCH_ROWS = 200


def watch_words(db, row, result):
    """What changed in a watched answer since last time: rows that came and went. Sets the changed flag only for a real change."""
    rows = (result or {}).get('rows', []) if isinstance(result, dict) else []
    now = [json.dumps(r, sort_keys=True, default=str) for r in rows[:WATCH_ROWS]]
    before = json.loads(row['last_rows']) if row['last_rows'] else None
    db.execute('UPDATE agenda_items SET last_rows=? WHERE id=?', (json.dumps(now), row['id']))
    if before is None:return 'Watching: %d row%s now. You will hear only when this changes.' % (len(now), '' if len(now) == 1 else 's')
    came = [r for r in now if r not in before];went = [r for r in before if r not in now]
    if not came and not went:return 'No change: %d row%s, as before.' % (len(now), '' if len(now) == 1 else 's')
    db.execute('UPDATE agenda_items SET changed=1 WHERE id=?', (row['id'],))
    sample = lambda rows:'; '.join(', '.join('%s %s' % (k, v) for k, v in json.loads(r).items())[:80] for r in rows[:3])
    return 'Changed: %d new%s%s.' % (len(came), (' (' + sample(came) + ')') if came else '',
                                       (', %d gone (%s)' % (len(went), sample(went))) if went else '')


def ask_slate(kernel, db, row, principal, clock):
    """An item in plain words is a question for Slate's brain, asked in plan mode: he answers and may propose staC; nothing runs."""
    from .engineering_kernel import Principal
    brain = kernel.dispatch('brain.status', {}, principal)
    if not brain.get('ok') or (brain.get('result') or {}).get('state') != 'READY':
        db.execute("UPDATE agenda_items SET due=?, reason=?, updated=? WHERE id=?",
                   (clock + RETRY_AFTER, "Waiting for Graphite's brain: choose a model in Brain, and it will take it up.", clock, row['id']))
        return {'ran': None, 'reason': 'Graphite has no brain running for a question in words.'}
    asked = kernel.dispatch('brain.ask', {'message': row['title'], 'mode': 'plan'},
                            Principal(principal.identity, frozenset({'read', 'execute'}), principal.paths, principal.tools, principal.mode))
    if not asked.get('ok'):
        finish(db, row, 'FAILED', (asked.get('error') or {}).get('message', 'could not ask'));return {'ran': row['id'], 'state': 'FAILED'}
    job = (asked.get('result') or {}).get('job') or (asked.get('result') or {}).get('id')
    db.execute("UPDATE agenda_items SET state='RUNNING', job=?, due=NULL, reason=NULL, updated=? WHERE id=?", (job, clock, row['id']))
    return {'ran': row['id'], 'state': 'RUNNING', 'job': job, 'authority': ['read']}


COPY_TEXT = 6000
FENCE = '```file'


def work_on_copy(kernel, db, row, principal, clock):
    """Slate rewrites a working copy you gave him, as the item asks. He answers with the whole file; nothing else changes."""
    from .engineering_kernel import Principal
    from . import files_service, working_copies
    brain = kernel.dispatch('brain.status', {}, principal)
    if not brain.get('ok') or (brain.get('result') or {}).get('state') != 'READY':
        db.execute("UPDATE agenda_items SET due=?, reason=?, updated=? WHERE id=?",
                   (clock + RETRY_AFTER, "Waiting for Graphite's brain: choose a model in Brain, and it will take it up.", clock, row['id']))
        return {'ran': None, 'reason': 'Graphite has no brain running to work on the copy.'}
    with working_copies.opened(kernel) as cdb:c = working_copies.the_copy(cdb, row['copy'])
    data = (files_service.root(kernel) / c['work']).read_bytes()
    if str(c['work']).lower().endswith('.xlsx'):  # a workbook: he sees its cells and answers with only the cells to change
        from . import sheet_edit
        try:cells = sheet_edit.as_text(data, COPY_TEXT)
        except (ValueError, KeyError, OSError) as exc:
            finish(db, row, 'FAILED', 'The workbook could not be read as cells (%s).' % str(exc)[:120]);return {'ran': row['id'], 'state': 'FAILED'}
        message = ('Work on the workbook %s as asked: %s\nIts cells are below, one per line, as Sheet!Cell = value (text in quotes, formulas start with =).\n'
                   'Reply with only the cells to change, in the same form, between a line %s and a line ```. An empty value clears a cell.\n\n%s'
                   % (Path(c['work']).name, row['title'], sheet_edit.FENCE, cells))
        asked = kernel.dispatch('brain.ask', {'message': message[:8000], 'mode': 'chat'},
                                Principal(principal.identity, frozenset({'read', 'execute'}), principal.paths, principal.tools, principal.mode))
        if not asked.get('ok'):
            finish(db, row, 'FAILED', (asked.get('error') or {}).get('message', 'could not ask'));return {'ran': row['id'], 'state': 'FAILED'}
        job = (asked.get('result') or {}).get('job') or (asked.get('result') or {}).get('id')
        db.execute("UPDATE agenda_items SET state='RUNNING', job=?, due=NULL, reason=NULL, updated=? WHERE id=?", (job, clock, row['id']))
        return {'ran': row['id'], 'state': 'RUNNING', 'job': job, 'authority': ['read', 'execute']}
    if b'\x00' in data[:8192] or len(data) > COPY_TEXT * 2:
        finish(db, row, 'FAILED', 'Graphite rewrites text files up to about %d characters; this one is not.' % COPY_TEXT);return {'ran': row['id'], 'state': 'FAILED'}
    text = data.decode('utf-8', 'replace')
    if len(text) > COPY_TEXT:
        finish(db, row, 'FAILED', 'Graphite rewrites text files up to about %d characters; this one is longer.' % COPY_TEXT);return {'ran': row['id'], 'state': 'FAILED'}
    message = ('Work on the file %s as asked: %s\nReply with the whole new file, and nothing else, between a line %s and a line ```.\n\n%s\n%s\n```'
               % (Path(c['source']).name, row['title'], FENCE, FENCE, text))
    asked = kernel.dispatch('brain.ask', {'message': message[:8000], 'mode': 'chat'},
                            Principal(principal.identity, frozenset({'read', 'execute'}), principal.paths, principal.tools, principal.mode))
    if not asked.get('ok'):
        finish(db, row, 'FAILED', (asked.get('error') or {}).get('message', 'could not ask'));return {'ran': row['id'], 'state': 'FAILED'}
    job = (asked.get('result') or {}).get('job') or (asked.get('result') or {}).get('id')
    db.execute("UPDATE agenda_items SET state='RUNNING', job=?, due=NULL, reason=NULL, updated=? WHERE id=?", (job, clock, row['id']))
    return {'ran': row['id'], 'state': 'RUNNING', 'job': job, 'authority': ['read', 'execute']}


def finish_copy(kernel, db, row, principal, text):
    """Slate's answer becomes the working copy's content and a frozen revision for your review, or a failure that says why."""
    from .engineering_kernel import Principal
    from . import working_copies
    with working_copies.opened(kernel) as cdb:c0 = working_copies.the_copy(cdb, row['copy'])
    if str(c0['work']).lower().endswith('.xlsx'):return finish_cells(kernel, db, row, principal, text, c0)
    start = text.find(FENCE)
    if start < 0:finish(db, row, 'FAILED', "Graphite's answer did not contain a whole file, so nothing was changed.");return
    body = text[start + len(FENCE):]
    body = body[2:] if body.startswith('\r\n') else body[1:] if body.startswith('\n') else body  # the line break after the fence
    end = body.rfind('```')
    if end < 0:finish(db, row, 'FAILED', "Graphite's answer did not close the file, so nothing was changed.");return
    body = body[:end]
    slate = Principal(principal.identity, frozenset({'read', 'execute'}), principal.paths, principal.tools, principal.mode)
    with working_copies.opened(kernel) as cdb:c = working_copies.the_copy(cdb, row['copy'])
    wrote = kernel.dispatch('files.write', {'path': c['work'], 'text': body}, slate)
    if not wrote.get('ok'):finish(db, row, 'FAILED', (wrote.get('error') or {}).get('message', 'could not write'));return
    frozen = kernel.dispatch('copies.propose', {'id': row['copy'], 'note': row['title'][:400]}, slate)
    if not frozen.get('ok'):finish(db, row, 'FAILED', (frozen.get('error') or {}).get('message', 'could not freeze'));return
    db.execute('UPDATE agenda_items SET rounds_used=rounds_used+1 WHERE id=?', (row['id'],))
    finish(db, row, 'DONE', 'Revision %d of %s waits for your review.' % (frozen['result']['revision'], Path(c['source']).name))


def finish_cells(kernel, db, row, principal, text, c):
    """Slate's cell changes, applied to his workbook copy and frozen for your review; or a failure that says why."""
    from .engineering_kernel import Principal
    from . import sheet_edit
    start = text.find(sheet_edit.FENCE)
    if start < 0:finish(db, row, 'FAILED', "Graphite's answer did not list cells to change, so nothing was changed.");return
    body = text[start + len(sheet_edit.FENCE):].lstrip('\r\n');end = body.rfind('```')
    if end < 0:finish(db, row, 'FAILED', "Graphite's answer did not close the list of cells, so nothing was changed.");return
    slate = Principal(principal.identity, frozenset({'read', 'execute'}), principal.paths, principal.tools, principal.mode)
    wrote = kernel.dispatch('files.cells', {'path': c['work'], 'changes': body[:end]}, slate)
    if not wrote.get('ok'):finish(db, row, 'FAILED', (wrote.get('error') or {}).get('message', 'could not change the cells'));return
    frozen = kernel.dispatch('copies.propose', {'id': row['copy'], 'note': row['title'][:400]}, slate)
    if not frozen.get('ok'):finish(db, row, 'FAILED', (frozen.get('error') or {}).get('message', 'could not freeze'));return
    db.execute('UPDATE agenda_items SET rounds_used=rounds_used+1 WHERE id=?', (row['id'],))
    finish(db, row, 'DONE', '%d cell(s) changed; revision %d of %s waits for your review.' % (wrote['result']['cells'], frozen['result']['revision'], Path(c['work']).name))


def collect(kernel, db, row, principal):
    """A question Slate is answering: when his job finishes, the item is done with his actual answer (or failed, with why)."""
    from .operation_stop import TERMINAL
    job = kernel.dispatch('jobs.get', {'id': row['job']}, principal)
    state = (job.get('result') or {}).get('state') if job.get('ok') else 'Failed'
    if state not in TERMINAL:return
    if state != 'Completed':finish(db, row, 'FAILED', (job.get('result') or {}).get('error') or state);return
    answer = kernel.dispatch('brain.result', {'id': row['job']}, principal)
    value = (answer.get('result') or {}).get('result') or {} if answer.get('ok') else {}
    if row['copy']:return finish_copy(kernel, db, row, principal, value.get('text') or '')
    text = ((value.get('proposal') or {}).get('text') or value.get('text') or 'Answered.')[:600]
    db.execute('UPDATE agenda_items SET rounds_used=rounds_used+1 WHERE id=?', (row['id'],))
    finish(db, row, 'DONE', text)


def outcome_words(result, progress):
    try:
        from .investigations import summary
        text = summary(result, 300) if result is not None else 'No result.'
    except Exception:
        text = 'Finished.'
    return text if progress else 'Nothing new: ' + text


def propose(kernel, principal, row):
    """Slate's next steps after an investigation round: taken from the investigation's own next action, never invented."""
    if not row['investigation']:return []
    try:
        from . import investigations
        with investigations.opened(kernel) as db:
            inv = investigations.owned(db, 'inv_investigations', row['investigation'], principal.identity)
            nxt = investigations.sheet(db, inv)['next']
    except (ValueError, sqlite3.Error, KeyError):return []
    if nxt.get('kind') in ('NONE', 'STOPPED', None):return []
    try:
        return [suggest(kernel, {'parent': row['id'], 'title': nxt['text'][:400], 'why': 'The investigation says this is the useful gap now.'}, principal)['id']]
    except ValueError:return []


def set_state(kernel, args, principal, wanted, allowed, reason=None):
    with opened(kernel) as db:
        row = owned(db, args['id'], principal.identity)
        if row['state'] not in allowed:raise ValueError('AGENDA_NOT_%s: it is %s' % (wanted, row['state'].lower()))
        if wanted in FINAL:finish(db, row, wanted, row['outcome'], reason)
        else:db.execute('UPDATE agenda_items SET state=?, updated=?, reason=? WHERE id=?', (wanted, time.time(), reason, row['id']))
        return item(owned(db, row['id'], principal.identity))


def dispatch(kernel, op, args, principal):
    if op in ('agenda.pause','agenda.resume','agenda.cancel'):
        from . import continuing_work
        with opened(kernel) as db:row=owned(db,args['id'],principal.identity);work=continuing_work.linked(db,row['id'])
        if work:
            operation={'agenda.pause':'work.pause','agenda.resume':'work.resume','agenda.cancel':'work.revoke'}[op]
            values={'id':work}
            if op=='agenda.cancel':values['reason']=args.get('reason') or 'Owner removed this Agenda work item'
            reply=kernel.dispatch(operation,values,principal)
            if not reply['ok']:raise ValueError(reply['error']['message'])
            with opened(kernel) as db:return item(owned(db,args['id'],principal.identity))
    if op == 'agenda.view':return view(kernel, principal)
    if op == 'agenda.add':return add(kernel, args, principal)
    if op == 'agenda.suggest':return suggest(kernel, args, principal)
    if op == 'agenda.accept':return set_state(kernel, args, principal, 'NEXT', ('SUGGESTED',))
    if op == 'agenda.decline':return set_state(kernel, args, principal, 'DECLINED', ('SUGGESTED',), 'Not now.')
    if op == 'agenda.pause':return set_state(kernel, args, principal, 'PAUSED', ('NEXT', 'LATER'))
    if op == 'agenda.resume':
        with opened(kernel) as db:row = owned(db, args['id'], principal.identity)
        return set_state(kernel, args, principal, 'LATER' if row['due'] and row['due'] > time.time() else 'NEXT', ('PAUSED',))
    if op == 'agenda.cancel':
        return set_state(kernel, args, principal, 'CANCELLED', OPEN, args.get('reason') or 'Cancelled by you.')
    if op == 'agenda.nice':
        with opened(kernel) as db:
            row = owned(db, args['id'], principal.identity)
            db.execute('UPDATE agenda_items SET nice=?, updated=? WHERE id=?', (args['nice'], time.time(), row['id']))
            return item(owned(db, row['id'], principal.identity))
    if op == 'agenda.move':
        with opened(kernel) as db:
            row = owned(db, args['id'], principal.identity)
            others = [r['id'] for r in db.execute("SELECT id FROM agenda_items WHERE owner=? AND state IN ('NEXT','PAUSED') AND id<>? "
                                                  "ORDER BY position, created", (principal.identity, row['id']))]
            others.insert(min(args['position'], len(others)), row['id'])
            for i, ident in enumerate(others):db.execute('UPDATE agenda_items SET position=? WHERE id=?', (i + 1, ident))
            return item(owned(db, row['id'], principal.identity))
    if op == 'agenda.reorder':
        with opened(kernel) as db:
            db.execute('BEGIN IMMEDIATE')
            row = owned(db,args['id'],principal.identity)
            if row['state'] not in ('NEXT','PAUSED'):raise ValueError('Only queued Agenda work can be reordered; refresh the work list')
            rows = sorted([dict(r) for r in db.execute("SELECT * FROM agenda_items WHERE owner=? AND state IN ('NEXT','PAUSED') AND id<>?",
                          (principal.identity,row['id']))], key=lambda r:(NICE_RANK.get(r['nice'],1),r['position'] or 0,r['created']))
            position = min(args['position'],len(rows))
            tier = rows[position]['nice'] if position < len(rows) else rows[-1]['nice'] if rows else row['nice']
            rows.insert(position,dict(row));stamp = time.time()
            for i,r in enumerate(rows):db.execute('UPDATE agenda_items SET position=?,updated=? WHERE id=?',(i+1,stamp,r['id']))
            db.execute('UPDATE agenda_items SET nice=? WHERE id=?',(tier,row['id']))
            return item(owned(db,row['id'],principal.identity))
    if op == 'agenda.run_next':
        from .continuing_work import agenda_lock
        with agenda_lock(kernel):return run_next(kernel, args, principal)
    if op == 'agenda.seen':
        with opened(kernel) as db:
            row = owned(db, args['id'], principal.identity)
            db.execute('UPDATE agenda_items SET changed=0, updated=? WHERE id=?', (time.time(), row['id']))
            return item(owned(db, row['id'], principal.identity))
    raise ValueError('AGENDA_UNKNOWN_OPERATION')
