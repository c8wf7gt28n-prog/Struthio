"""The resident agent loop (HATCH AGENT-01): an assignment becomes a durable investigation that Slate works one bounded step at a time.

CONTRACT (the integrator registered these operations; the implementer fills this module without changing the names, arguments
or return shapes below, because the Qt driver and the right column are written against them at the same time).

Record. One row per assignment in the table agent_assignments (same Kernel SQLite file as inv_*; created by ensure()):
  id, investigation (inv_investigations.id), owner, profile, request, context JSON, plan JSON, cursor INTEGER, state, reason,
  budget JSON, created, updated, paused_reason, model_job
The investigation holds the durable knowledge: the request is its question; each step is recorded in inv_steps (kind STEP,
program = the operation name and its arguments as JSON text, inputs = digests of what was read, outcome, summary, result
digest); findings become FINDING claims and open conditions become QUESTION claims; investigation.sheet shows all of it.

States: READY (assigned, nothing run), RUNNING (a driver is stepping it), PAUSED (owner closed Ledger or asked), WAITING
(needs the owner: a question, a refused step, units that differ), DONE (the profile finished), STOPPED (owner Stop),
FAILED (an unrecoverable error; the reason says what).

Profiles (agent_profiles.py). A profile plans a short sequence of operations for a request, interprets each actual
result into claims, and decides what comes next. The planner for a step is explicit code; where the profile offers
several reasonable next steps (at most four) the choice goes to choose_next(), which asks the local model when one is
READY (brain.ask, a tiny prompt listing the options; the answer is one option number) and otherwise takes the
profile's default. No model is available where this is built, so the model branch stays untested live and says so.

Operations:
  agent.assign  {request, profile?, context?, budget?}      -> {assignment, sheet}          execute
  agent.step    {id}                                          -> {assignment, step, next}      execute   one bounded step
  agent.run     {id, max_steps?, max_seconds?}                -> {assignment, ran:[...]}       execute   steps until not RUNNING or the limits
  agent.pause   {id, reason?}  agent.resume {id}  agent.stop {id, reason?}  -> {assignment}   execute
  agent.status  {id?}                                         -> {assignments:[status rows]}   read      the right column's five lines
  agent.list    {}                                            -> {assignments:[summaries]}     read
A status row: id, investigation, profile, state, reason, working_on (the request), doing_now (the running or next step's
purpose, or the WAITING/PAUSED reason), found (FINDING claims with evidence_state), needs_you (QUESTION claims and the
reason when WAITING), inspect ([{label, kind: investigation|document|condition, id}]), steps_used, budget, updated,
model_used (False until a model turn ran), paused_reason.
Rules: a step dispatches exactly one registered operation with a principal bounded by the budget's effects (read, or
read+execute), never approve; every step is recorded before its result is interpreted; a refused or failed step moves
the assignment to WAITING with the error in words; STOPPED and PAUSED assignments do not step; the request's words
choose the profile when 'auto' (request_profile()); nothing here starts a worker, a model or a native tool by itself.

How the loop keeps its word (WI-A):
  - plan JSON is {steps, used, seconds, model_turns, pending}: the profile's steps (each step that ran carries outcome, summary,
    step_id, seconds), the assignment's own step count and seconds against the budget, the model turns taken, and the open
    model choice. The 'assignment' every operation returns is the status row above.
  - A step that cannot be prepared, is refused by the Kernel (scope, schema, ownership) or fails is still recorded in
    inv_steps (outcome FAILED, the words in summary); the cursor stays on it, so agent.resume runs it again.
  - A WAITING assignment does not step either (it needs the owner); agent.resume moves PAUSED and WAITING to READY.
  - Budget: when steps or seconds reach the budget the assignment is STOPPED with 'Budget used: …' and so is its investigation.
  - The model branch (owner decision 6; the integrator's live trial with Qwen2.5-0.5B-Instruct showed the smallest model picks
    badly, so the profile's rule default stays primary): a profile's options carry an 'acceptable' mark; the model is asked only
    when more than one option is acceptable, through brain.ask in its schema-constrained choice mode (mode 'choice', 'choices' n:
    the answer is forced to one integer in 1..n). choose_next() submits through ask_model(); the following agent.step calls poll
    model_answer() (jobs.get, then brain.result: proposal {'choice': k}); the pick is taken only when that option is acceptable,
    otherwise the default is taken and the record says 'model chose k, not acceptable here, default taken' (or 'model answer
    unusable, default taken'). Every consultation is an inv_steps row of kind MODEL_CHOICE (operation 'brain.ask', the job id,
    the pick, the decision); a choice made without a model is a row of kind CHOICE. Both functions are module-level so tests
    patch them; the loop's live model path is not exercised by the tests here. Asking the model uses the caller's principal
    (brain.ask is an execute operation; the bounded principal runs the steps). Stopping an assignment records and drops its open
    model choice; it cancels no job.

Work that continues while Ledger is closed (HATCH AGENT-02 WI-A). The same record and the same agent.step; no new scheduler:
the resident Ledger service's existing 5 s tick (host_service.Coordinator.tick_agenda) calls pump() below.
  - Record: agent_assignments gains driver TEXT ('desktop' | 'service' | NULL when released), lease_until REAL,
    service_steps INTEGER and authority TEXT (JSON {scopes, paths, tools, mode}: what the owner granted, for the service's
    steps) (ALTER TABLE in ensure(): additive and idempotent; older files gain the columns on first use).
  - agent.step {id, driver?}: driver 'desktop' (the default: the owner's own window, agent.run and the command line) or
    'service' (the Ledger service's pump). A recorded extension of the AGENT-01 operation.
    LEASE RULE. A step by the desktop always proceeds and takes the lease (driver 'desktop', lease_until = now +
    LEASE_SECONDS): the owner's desktop has priority, so reopening Ledger takes the work back. A step by the service proceeds
    only when no desktop lease is live (driver 'desktop' with lease_until in the future); otherwise it is refused with
    ValueError('ASSIGNMENT_DRIVEN_BY_DESKTOP'). Every step renews the stepping driver's lease (LEASE_SECONDS = 20). A step
    the service takes increments service_steps and is recorded like any other; its inv_steps inputs carry
    {'driver': 'service'}, so the investigation sheet says who stepped. A step of either driver on a PAUSED, WAITING or
    finished assignment changes nothing, the lease included.
  - agent.release {id} (execute) -> {assignment, next}: clears driver and lease, so the service may continue the work (the
    desktop hands its running assignments over when it closes and the owner's setting agent.continue_when_closed is on). A
    READY assignment becomes RUNNING (the owner asked for it to run); PAUSED, WAITING and finished ones are refused.
  - pump(kernel, limit=8, guard=None, stop=None): one step each, driver 'service', for every RUNNING assignment of any owner
    whose desktop lease is not live, with the owner's principal reduced to read and execute and to the authority the owner
    granted (owner_principal: the scopes, paths, tools and mode recorded in the column authority at agent.assign and narrowed
    at agent.release, inside the operator's ceiling), so the service never acts with more than the owner who handed the work
    over. Nothing when the setting is off, work is held (work_trail.execution_held) or `stop()` says the service is closing;
    all three are checked again under the guard before every single step, so Master Stop (which holds work before it takes
    the dispatch lock), the setting turned off and the service's shutdown end a batch at the step in flight. It never raises.
    pause_all(kernel, reason) pauses every READY and RUNNING assignment of any owner (the service side of Master Stop).
"""
from __future__ import annotations
import contextlib
import json
import re
import sqlite3
import time
import uuid

from . import investigations
from .agent_profiles import PROFILES as REGISTRY, UNAVAILABLE, step as planned_step

ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$', 'maxLength': 32}
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 2000}
STATES = ('READY', 'RUNNING', 'PAUSED', 'WAITING', 'DONE', 'STOPPED', 'FAILED')
PROFILES = ('auto',) + tuple(sorted(REGISTRY))  # AGENT-02: every registered profile (agent_profiles imports the profile modules); 'auto' chooses by the request's words
CONTEXT = {'type': 'object', 'additionalProperties': False, 'properties': {
    'document': ID, 'record': {'type': 'string', 'maxLength': 300},
    'selection': {'type': 'object', 'additionalProperties': False, 'properties': {'block': {'type': 'integer', 'minimum': 0}, 'start': {'type': 'integer', 'minimum': 0},
                                                                                   'end': {'type': 'integer', 'minimum': 0}, 'text': {'type': 'string', 'maxLength': 32768}}},
    'steps': {'type': 'array', 'maxItems': 32, 'items': {'type': 'object'}}}}  # steps: the operation_sequence profile's explicit plan (tests)
BUDGET = {'type': 'object', 'additionalProperties': False, 'properties': {
    'max_steps': {'type': 'integer', 'minimum': 1, 'maximum': 200}, 'max_seconds': {'type': 'integer', 'minimum': 1, 'maximum': 28800},
    'effects': {'type': 'string', 'enum': ['read', 'execute']}}}
FIELDS = {
    'agent.assign': ({'request': TEXT, 'profile': {'type': 'string', 'enum': list(PROFILES)}, 'context': CONTEXT, 'budget': BUDGET}, ['request']),
    'agent.step': ({'id': ID, 'driver': {'type': 'string', 'enum': ['desktop', 'service']}}, ['id']),  # AGENT-02: driver (recorded extension)
    'agent.run': ({'id': ID, 'max_steps': {'type': 'integer', 'minimum': 1, 'maximum': 200}, 'max_seconds': {'type': 'number', 'minimum': 0.1, 'maximum': 28800}}, ['id']),
    'agent.pause': ({'id': ID, 'reason': {'type': 'string', 'maxLength': 300}}, ['id']),
    'agent.resume': ({'id': ID}, ['id']),
    'agent.stop': ({'id': ID, 'reason': {'type': 'string', 'maxLength': 300}}, ['id']),
    'agent.status': ({'id': ID}, []),
    'agent.list': ({}, []),
    'agent.release': ({'id': ID}, ['id']),  # AGENT-02: hand a running assignment to the Ledger service (recorded addition)
}
SCOPES = {op: 'read' if op in ('agent.status', 'agent.list') else 'execute' for op in FIELDS}
OBSERVERS = ('agent.status', 'agent.list')

DEFAULT_BUDGET = {'max_steps': 40, 'max_seconds': 600, 'effects': 'execute'}  # owner decision 2: free action inside the assignment
NO_FIT = 'No supported procedure fits this request without a model; ask again when a model is loaded or say it differently'
NOT_STEPPING = ('PAUSED', 'STOPPED', 'DONE', 'FAILED', 'WAITING')
FINISHED = ('DONE', 'STOPPED', 'FAILED')
SECRET = re.compile(r'(password|passphrase|secret|token|api_key|apikey|credential|private_key)', re.I)
PROGRAM_LIMIT = 8192        # the recorded program text stays within investigation.step's own bound
MODEL_PATIENCE = 180.0      # seconds a pending model choice may stay unanswered before the default is taken
MODEL_PROMPT_LIMIT = 600
CHOICE_OPERATION = 'agent:choose_next'
LEASE_SECONDS = 20          # AGENT-02: a driver's lease, renewed by every step it takes
DRIVERS = ('desktop', 'service')
SETTING = 'agent.continue_when_closed'   # AGENT-02: the owner's setting (settings_registry; Kernel settings ledger.agent.continue_when_closed)
DRIVEN_BY_DESKTOP = 'ASSIGNMENT_DRIVEN_BY_DESKTOP'
STEPPABLE = ('READY', 'RUNNING')

# request_profile: the words an owner uses for "numbers on the page" (owner decision 8). All three groups must be present.
_VERB = re.compile(r'\b(add(?:s|ed|ing)?\s+up|total(?:s|led|ling)?|sum(?:s|med|ming)?(?:\s+up)?|how\s+much|count(?:s|ed|ing)?|tally|tot\s+up)\b')
_NOUN = re.compile(r'\b(numbers?|quantit(?:y|ies)|values?|amounts?|figures?)\b')
_PLACE = re.compile(r'\b(on\s+(?:this|the)\s+page|(?:this|the)\s+page|here|in\s+this\s+document|on\s+this\s+sheet)\b')


def request_profile(text):
    """The profile a plain request earns without a model, or None: add up / total / sum / how much / count + numbers / quantities /
    values / amounts + on this page / the page / here -> 'numbers_on_page'. Explicit words, no model. AGENT-02: any other
    registered profile may claim a request through its own fits(words) (explicit words again, never a model); the first
    profile that fits, in registry order, wins after the numbers rule."""
    words = ' '.join(str(text or '').casefold().replace('’', "'").split())
    if not words: return None
    if _VERB.search(words) and _NOUN.search(words) and _PLACE.search(words): return 'numbers_on_page'
    for name, profile in REGISTRY.items():
        fits = getattr(profile, 'fits', None)
        if callable(fits):
            try:
                if fits(words): return name
            except Exception: continue
    return None


# -- the record --------------------------------------------------------------------------------------------------------------

@contextlib.contextmanager
def opened(kernel):
    with kernel.db() as db:
        db.row_factory = sqlite3.Row; yield db


def ensure(db):
    investigations.ensure(db)
    db.execute('''CREATE TABLE IF NOT EXISTS agent_assignments(id TEXT PRIMARY KEY, investigation TEXT, owner TEXT, profile TEXT, request TEXT,
        context TEXT, plan TEXT, cursor INTEGER, state TEXT, reason TEXT, budget TEXT, created REAL, updated REAL, paused_reason TEXT, model_job TEXT)''')
    db.execute('CREATE INDEX IF NOT EXISTS agent_assignments_by ON agent_assignments(owner, updated)')
    # AGENT-02: who steps it and until when (additive; an older file gains the columns here, once)
    have = {row[1] for row in db.execute('PRAGMA table_info(agent_assignments)')}
    for name, kind in (('driver', 'TEXT'), ('lease_until', 'REAL'), ('service_steps', 'INTEGER DEFAULT 0'), ('authority', 'TEXT')):
        if name in have: continue
        try: db.execute('ALTER TABLE agent_assignments ADD COLUMN %s %s' % (name, kind))
        except sqlite3.OperationalError as exc:
            if 'duplicate column' not in str(exc).lower(): raise   # another process added it a moment ago


def unpack(row):
    """The stored row as the state dict profiles read (see agent_profiles: id, investigation, profile, request, state, reason, cursor,
    budget, context, plan, and the loop's own used, seconds, model_turns, pending)."""
    state = dict(row)
    state['context'] = json.loads(state.get('context') or '{}')
    plan = json.loads(state.get('plan') or '{}')
    state['plan'] = list(plan.get('steps') or []); state['used'] = int(plan.get('used') or 0); state['seconds'] = float(plan.get('seconds') or 0.0)
    state['model_turns'] = int(plan.get('model_turns') or 0); state['pending'] = plan.get('pending')
    state['budget'] = json.loads(state.get('budget') or '{}')
    state['cursor'] = int(state.get('cursor') or 0)
    state['driver'] = state.get('driver') if state.get('driver') in DRIVERS else None
    state['lease_until'] = float(state['lease_until']) if state.get('lease_until') is not None else None
    state['service_steps'] = int(state.get('service_steps') or 0)
    try: authority = json.loads(state.get('authority') or 'null')
    except (TypeError, ValueError): authority = None
    state['authority'] = authority if isinstance(authority, dict) else None   # None: recorded before the column (owner_principal's fallback)
    return state


def plan_json(state):
    return json.dumps({'steps': state['plan'], 'used': state['used'], 'seconds': round(state['seconds'], 3), 'model_turns': state['model_turns'],
                       'pending': state.get('pending')}, sort_keys=True, default=str)


def load(db, ident, owner):
    row = db.execute('SELECT * FROM agent_assignments WHERE id=? AND owner=?', (ident, owner)).fetchone()
    if row is None: raise ValueError('ASSIGNMENT_NOT_FOUND')
    return unpack(row)


def store(db, state):
    state['updated'] = time.time()
    db.execute('UPDATE agent_assignments SET context=?, plan=?, cursor=?, state=?, reason=?, updated=?, paused_reason=?, model_job=?, driver=?, lease_until=?, '
               'service_steps=? WHERE id=?',
               (json.dumps(state['context'], sort_keys=True, default=str), plan_json(state), state['cursor'], state['state'], state['reason'] or '',
                state['updated'], state.get('paused_reason'), state.get('model_job'), state.get('driver'), state.get('lease_until'),
                int(state.get('service_steps') or 0), state['id']))


def lease_live(state, now=None, driver=None):
    """True while the assignment can step and its driver's lease has not run out (only that driver's lease, when one is named)."""
    if state.get('state') not in STEPPABLE or state.get('lease_until') is None: return False
    if driver is not None and state.get('driver') != driver: return False
    return float(state['lease_until']) > (time.time() if now is None else now)


def profile_of(state):
    return REGISTRY.get(state.get('profile'))


def words_of(exc):
    text = str(exc).strip() or type(exc).__name__
    return text[:600]


def bound(principal, budget):
    """The principal a step runs with: read only, or the caller's own read+execute; never approve or candidate."""
    from .engineering_kernel import Principal
    scopes = frozenset({'read'}) if budget.get('effects', 'read') == 'read' else principal.scopes & frozenset({'read', 'execute'})
    return Principal(principal.identity, scopes, principal.paths, principal.tools, principal.mode)


def redact(value, depth=0):
    """Arguments as they may be recorded: secret-looking keys withheld, long strings and lists cut."""
    if depth > 12: return '…'
    if isinstance(value, dict): return {str(k): ('[withheld]' if SECRET.search(str(k)) else redact(v, depth + 1)) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [redact(v, depth + 1) for v in list(value)[:200]]
    if isinstance(value, str) and len(value) > 2000: return value[:2000] + '…'
    return value


def recorded_arguments(arguments):
    safe = redact(arguments)
    if len(json.dumps({'arguments': safe}, sort_keys=True, default=str)) > PROGRAM_LIMIT:
        safe = {'_digest': investigations.digest(safe), '_truncated': True, '_keys': sorted(str(k) for k in arguments)[:64]}
    return safe


# -- the status row ---------------------------------------------------------------------------------------------------------

def doing_now(state, profile):
    name = state['state']
    if name == 'PAUSED': return 'Paused: ' + (state.get('paused_reason') or 'by you')
    if name in ('WAITING', 'STOPPED', 'FAILED'): return state.get('reason') or name.capitalize()
    if name == 'DONE': return state.get('reason') or 'Finished'
    if state.get('pending'): return 'Waiting for the model to pick the next step'
    if profile is None: return state.get('reason') or 'No procedure available'
    try: return str(profile.describe(state))[:300]
    except Exception as exc: return 'The procedure could not describe its step: ' + words_of(exc)


def status_row(db, state, profile=None):
    profile = profile or profile_of(state)
    inv = db.execute('SELECT * FROM inv_investigations WHERE id=?', (state['investigation'],)).fetchone()
    claims = []
    if inv is not None:
        sheet = investigations.sheet(db, inv); seen = set()
        claims = [c for c in sheet['learned'] + sheet['unresolved'] if not (c['id'] in seen or seen.add(c['id']))]
    found = [{'id': c['id'], 'text': c['text'], 'evidence_state': c['evidence_state']} for c in claims if c['role'] == 'FINDING']
    needs = [{'id': c['id'], 'text': c['text'], 'kind': 'QUESTION'} for c in claims if c['role'] == 'QUESTION']
    if state['state'] == 'WAITING' and state.get('reason'): needs.append({'id': None, 'text': state['reason'], 'kind': 'WAITING'})
    context = state['context'] or {}
    inspect = [{'label': 'Investigation', 'kind': 'investigation', 'id': state['investigation']}]
    documents = [d for d in [context.get('document')] + list(context.get('documents') or []) if isinstance(d, str)]
    for ident in dict.fromkeys(documents): inspect.append({'label': 'Document', 'kind': 'document', 'id': ident})
    conditions = list(context.get('conditions') or []) + ([context['condition']] if isinstance(context.get('condition'), str) else [])
    for ident in dict.fromkeys(c for c in conditions if isinstance(c, str)): inspect.append({'label': 'Condition', 'kind': 'condition', 'id': ident})
    return {'id': state['id'], 'investigation': state['investigation'], 'profile': state['profile'], 'state': state['state'], 'reason': state.get('reason') or '',
            'working_on': state['request'], 'doing_now': doing_now(state, profile), 'found': found, 'needs_you': needs, 'inspect': inspect,
            'steps_used': state['used'], 'budget': state['budget'], 'updated': state['updated'], 'model_used': state['model_turns'] > 0,
            'paused_reason': state.get('paused_reason'), **driver_fields(state)}


def driver_fields(state):
    """AGENT-02: who steps the assignment (desktop, service, or None when released or never stepped), whether that driver's lease
    is live and when it ends (None when not live: a reopened window looks again then, agent_qt.AgentDriver.adopt), and how
    many steps the Ledger service took."""
    live = lease_live(state)
    return {'driver': state.get('driver'), 'lease_live': live, 'lease_until': state.get('lease_until') if live else None,
            'service_steps': int(state.get('service_steps') or 0)}


def summary_row(state):
    return {'id': state['id'], 'investigation': state['investigation'], 'profile': state['profile'], 'state': state['state'], 'reason': state.get('reason') or '',
            'working_on': state['request'], 'steps_used': state['used'], 'updated': state['updated'], 'created': state['created'], 'paused_reason': state.get('paused_reason'),
            **driver_fields(state)}


def report(kernel, state, step_row=None, words=''):
    """Store the state and answer with the status row (every execute operation returns the same 'assignment' shape)."""
    with opened(kernel) as db:
        store(db, state); fresh = load(db, state['id'], state['owner']); row = status_row(db, fresh)
    return {'assignment': row, 'step': step_row, 'next': words}


# -- assign -----------------------------------------------------------------------------------------------------------------

def normalise(row):
    if not isinstance(row, dict): raise ValueError('A planned step is an object')
    return planned_step(row.get('key') or 'step', row.get('purpose'), row.get('operation'), row.get('arguments') or {}, row.get('inputs'),
                        **{k: v for k, v in row.items() if k not in ('key', 'purpose', 'operation', 'arguments', 'inputs')})


def assign(kernel, args, principal):
    request = ' '.join(str(args['request']).split())
    if not request: raise ValueError('ASSIGNMENT_REQUEST_REQUIRED')
    name = args.get('profile', 'auto'); context = dict(args.get('context') or {})
    budget = {**DEFAULT_BUDGET, **(args.get('budget') or {})}
    if name == 'auto': name = request_profile(request)
    profile = REGISTRY.get(name) if name else None
    reason = None
    if name is None: reason = NO_FIT
    elif profile is None: reason = 'The procedure %s is not available in this build%s' % (name, ': ' + UNAVAILABLE[name] if name in UNAVAILABLE else '')
    plan = []
    if profile is not None:
        missing = [k for k in profile.needs if k not in context]
        if missing: reason = 'This procedure needs %s in the request context' % ', '.join(missing)
        else:
            try: plan = [normalise(s) for s in (profile.plan(context, kernel, principal) or [])]
            except Exception as exc: reason = words_of(exc); plan = []
            if not plan and not reason: reason = 'The procedure planned no steps for this request'
    objective = profile.words if profile else 'No procedure planned: ' + reason
    sheet = investigations.dispatch(kernel, 'investigation.create', {'question': request[:4000], 'objective': objective[:4000],
                                    'budget': {'max_steps': budget['max_steps'], 'max_seconds': min(int(budget['max_seconds']), 3600), 'effects': budget['effects']}}, principal)
    ident = uuid.uuid4().hex; now = time.time()
    state = {'id': ident, 'investigation': sheet['id'], 'owner': principal.identity, 'profile': name or 'auto', 'request': request, 'context': context, 'plan': plan,
             'cursor': 0, 'state': 'WAITING' if reason else 'READY', 'reason': reason or '', 'budget': budget, 'created': now, 'updated': now, 'paused_reason': None,
             'model_job': None, 'used': 0, 'seconds': 0.0, 'model_turns': 0, 'pending': None, 'driver': None, 'lease_until': None, 'service_steps': 0}
    with opened(kernel) as db:
        ensure(db)
        # named columns: the AGENT-02 columns follow the AGENT-01 ones in an older file and in a new one alike; authority is
        # what this owner grants the work (owner_principal bounds the Ledger service's steps by it)
        db.execute('INSERT INTO agent_assignments(id, investigation, owner, profile, request, context, plan, cursor, state, reason, budget, created, updated, '
                   'paused_reason, model_job, driver, lease_until, service_steps, authority) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (ident, sheet['id'], principal.identity, state['profile'], request, json.dumps(context, sort_keys=True, default=str), plan_json(state), 0,
                    state['state'], state['reason'], json.dumps(budget, sort_keys=True), now, now, None, None, None, None, 0,
                    json.dumps(authority_of(principal), sort_keys=True)))
        fresh = load(db, ident, principal.identity); row = status_row(db, fresh, profile)
        sheet = investigations.sheet(db, db.execute('SELECT * FROM inv_investigations WHERE id=?', (sheet['id'],)).fetchone())
    return {'assignment': row, 'sheet': sheet}


# -- one bounded step ---------------------------------------------------------------------------------------------------------

def write_claims(kernel, state, claims, principal):
    written = []
    for claim in claims or []:
        if not isinstance(claim, dict): continue
        role = claim.get('role'); text = ' '.join(str(claim.get('text') or '').split())[:4000]
        if role not in investigations.ROLES or not text: continue
        out = investigations.dispatch(kernel, 'investigation.claim', {'id': state['investigation'], 'text': text, 'role': role}, principal)
        written.append(out['claim'])
    return written


def apply_outcome(kernel, state, out, principal, failed=False):
    """What a profile asked for after a step: claims, context, inserted steps. Returns the dict (never None)."""
    out = out if isinstance(out, dict) else {}
    write_claims(kernel, state, out.get('claims'), principal)
    updates = out.get('context_updates')
    if isinstance(updates, dict): state['context'].update(updates)
    steps = out.get('steps')
    if steps:
        new = [normalise(s) for s in steps]
        if failed:
            # the failed step keeps its record and place; what came after it is replaced by the profile's new steps
            state['cursor'] += 1; state['plan'][state['cursor']:] = new
        else: state['plan'][state['cursor']:state['cursor']] = new
    return out


def stop_investigation(kernel, state, reason):
    with opened(kernel) as db:
        db.execute("UPDATE inv_investigations SET state='STOPPED', reason=?, updated=? WHERE id=?", (reason, time.time(), state['investigation']))


def complete(kernel, state, reason=None):
    state.update(state='DONE', reason=reason or ('Finished: %d step%s ran' % (state['used'], '' if state['used'] == 1 else 's')), pending=None, model_job=None)
    with opened(kernel) as db: investigations.settle(db, state['investigation'])


def dispatch_step(kernel, profile, current, state, bounded):
    """Prepare and run one step. Returns (ok, result, arguments, error words)."""
    try: arguments = profile.arguments(current, state, kernel, bounded)
    except Exception as exc: return False, None, dict(current.get('arguments') or {}), 'Could not prepare the step: ' + words_of(exc)
    if not isinstance(arguments, dict): return False, None, {}, 'Could not prepare the step: the procedure gave no argument object'
    operation = current['operation']
    if operation.startswith('helpers:'):
        try: return True, profile.local(current, state, kernel, bounded), arguments, None
        except Exception as exc: return False, None, arguments, words_of(exc)
    try: envelope = kernel.dispatch(operation, arguments, bounded)
    except Exception as exc: envelope = {'ok': False, 'error': {'code': type(exc).__name__, 'message': words_of(exc)}}
    if envelope.get('ok'): return True, envelope.get('result'), arguments, None
    return False, None, arguments, (envelope.get('error') or {}).get('message') or 'did not run'


def step_once(kernel, ident, principal, driver='desktop'):
    from . import resource_control
    with resource_control.scope('background' if driver=='service' else 'foreground'):
        return _step_once(kernel,ident,principal,driver)


def _step_once(kernel, ident, principal, driver='desktop'):
    """One bounded step. driver 'desktop' always proceeds and takes the lease; driver 'service' is refused with
    ASSIGNMENT_DRIVEN_BY_DESKTOP while a desktop lease is live (the lease rule in the module docstring)."""
    if driver not in DRIVERS: raise ValueError('ASSIGNMENT_DRIVER_UNKNOWN: ' + str(driver)[:40])
    with opened(kernel) as db:
        ensure(db); state = load(db, ident, principal.identity)
    profile = profile_of(state)
    if state['state'] in NOT_STEPPING:
        return report(kernel, state, None, 'Not stepping: the assignment is %s%s' % (state['state'], (' · ' + state['reason']) if state.get('reason') else ''))
    now = time.time()
    if driver == 'service' and lease_live(state, now, 'desktop'):
        raise ValueError(DRIVEN_BY_DESKTOP + ': the desktop is stepping it (its lease runs %.0f s more)' % (state['lease_until'] - now))
    if driver=='service':
        from .resource_control import background_reason
        reason=background_reason(kernel)
        if reason:return report(kernel,state,None,reason+' · continue at the next step boundary')
    state.update(driver=driver, lease_until=now + LEASE_SECONDS)   # the stepping driver takes or renews the lease
    if profile is None:
        state.update(state='WAITING', reason='The procedure %s is not available in this build' % state['profile'])
        return report(kernel, state, None, state['reason'])
    budget = state['budget']
    if state['used'] >= int(budget.get('max_steps', DEFAULT_BUDGET['max_steps'])) or state['seconds'] >= float(budget.get('max_seconds', DEFAULT_BUDGET['max_seconds'])):
        words = 'Budget used: %d steps, %.1f seconds' % (state['used'], state['seconds'])
        state.update(state='STOPPED', reason=words, pending=None, model_job=None); stop_investigation(kernel, state, words)
        return report(kernel, state, None, words)
    if state['state'] == 'READY': state.update(state='RUNNING', reason='')
    bounded = bound(principal, budget)
    if state.get('pending'):
        if resolve_choice(kernel, principal, state) is None:
            return report(kernel, state, None, 'Waiting for the model to answer which step comes next')
    try: current = profile.next(state)
    except Exception as exc:
        state.update(state='FAILED', reason='The procedure could not say what comes next: ' + words_of(exc))
        return report(kernel, state, None, state['reason'])
    if current is None:
        complete(kernel, state)
        return report(kernel, state, None, state['reason'])
    started = time.time()
    ok, result, arguments, error = dispatch_step(kernel, profile, current, state, bounded)
    finished = time.time()
    summary = investigations.summary(result) if ok else error
    try: inputs = dict(profile.inputs(current, state) or {})
    except Exception as exc: inputs = {'inputs': 'UNAVAILABLE: ' + words_of(exc)}
    inputs.setdefault('arguments', investigations.digest(redact(arguments)))
    if driver == 'service': inputs['driver'] = 'service'   # AGENT-02: the sheet says the Ledger service took this step
    row = investigations.record_step(kernel, state['investigation'], current['operation'], recorded_arguments(arguments), bounded, current['purpose'],
                                     'DONE' if ok else 'FAILED', summary, result, inputs, started=started, finished=finished)
    current.update(outcome=row['outcome'], summary=row['summary'], step_id=row['id'], seconds=round(finished - started, 3), duplicate_of=row['duplicate_of'])
    state['used'] += 1; state['seconds'] += finished - started
    if driver == 'service': state['service_steps'] = int(state.get('service_steps') or 0) + 1
    step_row = {'seq': row['seq'], 'id': row['id'], 'key': current['key'], 'operation': current['operation'], 'purpose': current['purpose'], 'outcome': row['outcome'],
                'summary': row['summary'], 'seconds': current['seconds'], 'authority': row['authority'], 'driver': driver}
    if not ok:
        words = 'Step %s (%s) did not run: %s' % (current['key'], current['purpose'], error)
        try: out = apply_outcome(kernel, state, profile.failed(current, error, state, kernel, bounded), principal, failed=True)
        except Exception as exc: out = {'waiting': words + ' · and the procedure could not read the failure: ' + words_of(exc)}
        state.update(state='WAITING', reason=str(out.get('waiting') or words)[:600], pending=None, model_job=None)
        return report(kernel, state, step_row, state['reason'])
    state['cursor'] += 1
    try: out = apply_outcome(kernel, state, profile.interpret(current, result, state, kernel, bounded), principal)
    except Exception as exc:
        state.update(state='FAILED', reason='The procedure failed while reading the result of step %s: %s' % (current['key'], words_of(exc)))
        return report(kernel, state, step_row, state['reason'])
    if out.get('waiting'):
        state.update(state='WAITING', reason=str(out['waiting'])[:600])
        return report(kernel, state, step_row, state['reason'])
    if out.get('done') or (profile.done(state) and not out.get('options')):   # AGENT-02: a profile's options after its last planned step are taken, not dropped
        complete(kernel, state, out.get('reason'))
        return report(kernel, state, step_row, state['reason'])
    words = None
    if out.get('options'): words = choose_next(kernel, principal, state, out['options'], out.get('situation'))
    if words is None:
        following = profile.next(state)
        words = 'Next: ' + following['purpose'] if following else 'Nothing further planned'
    return report(kernel, state, step_row, words)


# -- choosing among options (the only place a model is consulted) --------------------------------------------------------------

def normalise_options(options):
    """At most four {key, purpose, step, acceptable}; 'acceptable' (default True) is the profile's mark for the current state."""
    out = []
    for row in options or []:
        if not isinstance(row, dict) or not isinstance(row.get('step'), dict): continue
        step = normalise(row['step'])
        out.append({'key': str(row.get('key') or step['key']), 'purpose': str(row.get('purpose') or step['purpose'])[:300], 'step': step,
                    'acceptable': bool(row.get('acceptable', True))})
    return out[:4]


def default_of(options):
    """The profile's rule default: the first acceptable option (the first option when none is marked)."""
    return next((o for o in options if o['acceptable']), options[0])


def option_keys(options):
    return [{'key': o['key'], 'purpose': o['purpose'], 'acceptable': o['acceptable']} for o in options]


def shorten(text, limit):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= limit else text[:limit - 1] + '…'


def choice_prompt(situation, options):
    """The situation and the numbered options, one per line, under MODEL_PROMPT_LIMIT characters (built for the smallest models)."""
    head = 'Graphite is working on: ' + shorten(situation, 160) + '\nWhich step comes next?\n'
    lines = '\n'.join('%d. %s' % (n, shorten(o['purpose'], 90)) for n, o in enumerate(options, 1))
    return (head + lines)[:MODEL_PROMPT_LIMIT - 1]


def pick(answer, count):
    """The option number in a model's answer: the structured choice when it lies in 1..count, else the first integer in the text
    when it lies in 1..count, else None."""
    if isinstance(answer, dict):
        choice = answer.get('choice')
        if isinstance(choice, int) and not isinstance(choice, bool) and 1 <= choice <= count: return choice
        answer = answer.get('text') or ''
    found = re.search(r'\d+', str(answer or ''))
    if not found: return None
    value = int(found.group())
    return value if 1 <= value <= count else None


def ask_model(kernel, principal, prompt, choices):
    """Submit the choice to the local model when one is READY (brain.ask, mode 'choice', the answer forced to one integer in
    1..choices); returns the job id, or None when no model is loaded. Tests patch this function; the loop's live path is not
    exercised by the tests here."""
    status = kernel.dispatch('brain.status', {}, principal)
    if not (status.get('ok') and (status.get('result') or {}).get('state') == 'READY'): return None
    envelope = kernel.dispatch('brain.ask', {'message': prompt, 'mode': 'choice', 'choices': int(choices), 'request_key': uuid.uuid4().hex}, principal)
    if not envelope.get('ok'): raise ValueError((envelope.get('error') or {}).get('message') or 'brain.ask was refused')
    job = envelope.get('result') or {}
    return job.get('id') or job.get('job_id')


def model_answer(kernel, principal, job):
    """The model's answer for a submitted choice: None while the job is still queued or running; otherwise
    {'choice': k or None, 'text': words, 'state': job state} from brain.result (proposal {'choice': k}, text 'Option k').
    Tests patch this function; the loop's live path is not exercised by the tests here."""
    envelope = kernel.dispatch('jobs.get', {'id': job}, principal)
    if not envelope.get('ok'): return {'choice': None, 'text': '', 'state': 'UNAVAILABLE'}
    state = (envelope.get('result') or {}).get('state')
    if state in ('Queued', 'Running', 'Paused', 'AwaitingApproval'): return None
    if state != 'Completed': return {'choice': None, 'text': '', 'state': state}
    outcome = kernel.dispatch('brain.result', {'id': job}, principal)
    value = ((outcome.get('result') or {}).get('result') or {}) if outcome.get('ok') else {}
    value = value if isinstance(value, dict) else {}
    proposal = value.get('proposal') if isinstance(value.get('proposal'), dict) else {}
    choice = proposal.get('choice')
    return {'choice': choice if isinstance(choice, int) and not isinstance(choice, bool) else None, 'text': str(value.get('text') or ''), 'state': state}


def take(state, option):
    """Insert the chosen option's step at the cursor (it runs next) and close the open choice."""
    state['plan'].insert(state['cursor'], normalise(option['step']))
    state['pending'] = None; state['model_job'] = None


def record_choice(kernel, state, principal, kind, operation, arguments, outcome, note, chosen, result=None):
    """The choice as an inv_steps row: kind CHOICE (no model) or MODEL_CHOICE (operation brain.ask, the job, the pick, the decision)."""
    inputs = {'job': arguments['job']} if arguments.get('job') else {}
    return investigations.record_step(kernel, state['investigation'], operation, arguments, principal, 'Choose the next step', outcome,
                                      note + ': ' + chosen['purpose'], {'chosen': chosen['key'], 'decision': note, **(result or {})}, inputs, kind=kind)


def choose_next(kernel, principal, state, options, situation=None):
    """At most four candidate next steps. The default is the first acceptable option. The model is asked only when more than one
    option is acceptable and one is READY (ask_model); otherwise, or when asking fails, the default is taken and the record says
    why. Returns words for the caller; a pending model answer is resolved by the next agent.step."""
    options = normalise_options(options)
    if not options: return None
    default = default_of(options); acceptable = [o for o in options if o['acceptable']]
    note = 'no model loaded; default taken'
    if len(acceptable) > 1:
        prompt = choice_prompt(situation or state['request'], options)
        try: job = ask_model(kernel, principal, prompt, len(options))
        except Exception as exc: job, note = None, 'the model could not be asked (%s); default taken' % words_of(exc)
        if job:
            state['pending'] = {'job': str(job), 'options': options, 'asked': time.time(), 'prompt': prompt}; state['model_job'] = str(job)
            return 'Asked the model to pick among %d steps' % len(options)
    else: note = 'one acceptable option; taken' if acceptable else 'no option marked acceptable; the first taken'
    take(state, default)
    record_choice(kernel, state, principal, 'CHOICE', CHOICE_OPERATION, {'options': option_keys(options), 'chosen': default['key']}, 'DONE', note, default)
    return 'Next: ' + default['purpose']


def resolve_choice(kernel, principal, state):
    """Poll the open model choice. None while the answer is pending; otherwise the option taken (the model's when acceptable,
    else the default), after the MODEL_CHOICE row is recorded."""
    pending = state.get('pending') or {}; options = normalise_options(pending.get('options')); job = pending.get('job')
    if not options or not job:
        state['pending'] = None; state['model_job'] = None; return {'key': None}
    failure = None
    try: answer = model_answer(kernel, principal, job)
    except Exception as exc: answer, failure = {'choice': None, 'text': '', 'state': 'UNREADABLE'}, 'the model answer could not be read (%s)' % words_of(exc)
    if answer is None:
        if time.time() - float(pending.get('asked') or 0) < MODEL_PATIENCE: return None
        answer, failure = {'choice': None, 'text': '', 'state': 'TIMED_OUT'}, 'the model did not answer in time'
    if not isinstance(answer, dict): answer = {'choice': None, 'text': str(answer or ''), 'state': 'Completed'}
    answered = bool(answer.get('text')) or answer.get('choice') is not None
    if answered: state['model_turns'] += 1
    default = default_of(options); number = pick(answer, len(options)); outcome = 'DONE'
    if failure: chosen, note, outcome = default, failure + '; default taken', 'FAILED'
    elif number is None:
        chosen = default
        if answered: note = 'model answer unusable, default taken'
        else: note, outcome = 'the model job ended without an answer; default taken', 'FAILED'
    elif not options[number - 1]['acceptable']: chosen, note = default, 'model chose %d, not acceptable here, default taken' % number
    else: chosen, note = options[number - 1], 'model chose option %d' % number
    take(state, chosen)
    record_choice(kernel, state, principal, 'MODEL_CHOICE', 'brain.ask',
                  {'job': job, 'mode': 'choice', 'choices': len(options), 'message': pending.get('prompt'), 'options': option_keys(options)},
                  outcome, note, chosen, {'job': job, 'pick': number, 'answer': answer})
    return chosen


# -- run, pause, resume, stop, status, list ------------------------------------------------------------------------------------

def run(kernel, args, principal):
    max_steps = int(args.get('max_steps') or 200); max_seconds = float(args.get('max_seconds') or 28800)
    started = time.time(); ran = []; last = None
    while len(ran) < max_steps and time.time() - started < max_seconds:
        last = step_once(kernel, args['id'], principal)
        if last['step'] is None: break   # finished, waiting, paused, stopped, or a model answer is pending
        ran.append(last['step'])
        if last['assignment']['state'] != 'RUNNING': break
    if last is None:
        with opened(kernel) as db: ensure(db); row = status_row(db, load(db, args['id'], principal.identity))
    else: row = last['assignment']
    return {'assignment': row, 'ran': ran}


def pause(kernel, args, principal):
    with opened(kernel) as db: ensure(db); state = load(db, args['id'], principal.identity)
    if state['state'] not in ('READY', 'RUNNING'): raise ValueError('ASSIGNMENT_NOT_RUNNING: it is ' + state['state'])
    reason = ' '.join(str(args.get('reason') or '').split()) or 'By you'
    state.update(state='PAUSED', paused_reason=reason, reason='Paused: ' + reason)
    return {'assignment': report(kernel, state)['assignment']}


def resume(kernel, args, principal):
    with opened(kernel) as db: ensure(db); state = load(db, args['id'], principal.identity)
    if state['state'] not in ('PAUSED', 'WAITING'): raise ValueError('ASSIGNMENT_NOT_RESUMABLE: it is ' + state['state'])
    state.update(state='READY', paused_reason=None, reason='')
    return {'assignment': report(kernel, state)['assignment']}


def stop(kernel, args, principal):
    with opened(kernel) as db: ensure(db); state = load(db, args['id'], principal.identity)
    if state['state'] in FINISHED: raise ValueError('ASSIGNMENT_FINISHED: it is ' + state['state'])
    reason = ' '.join(str(args.get('reason') or '').split()) or 'Stop'
    pending = state.get('pending') or {}; dropped = ''
    if pending.get('job'):
        # the consultation stays on the record even though nothing is taken; the job is left to the Brain (no cancel from here)
        investigations.record_step(kernel, state['investigation'], 'brain.ask', {'job': pending['job'], 'mode': 'choice', 'choices': len(pending.get('options') or []),
                                   'message': pending.get('prompt'), 'options': option_keys(normalise_options(pending.get('options')))}, principal, 'Choose the next step',
                                   'DROPPED', 'stopped before the model answered; nothing taken', {'job': pending['job'], 'decision': 'dropped'}, {'job': pending['job']}, kind='MODEL_CHOICE')
        dropped = ' · the open model choice was dropped'
    state.update(state='STOPPED', reason='By you: ' + reason + dropped, pending=None, model_job=None, paused_reason=None)
    investigations.dispatch(kernel, 'investigation.stop', {'id': state['investigation'], 'reason': reason[:4000]}, principal)
    return {'assignment': report(kernel, state)['assignment']}


def release(kernel, args, principal):
    """agent.release: the driver and its lease are cleared, so the Ledger service may continue the assignment (pump). A READY
    assignment becomes RUNNING (the owner asked for it to run); PAUSED, WAITING and finished ones are refused."""
    with opened(kernel) as db: ensure(db); state = load(db, args['id'], principal.identity)
    if state['state'] not in STEPPABLE: raise ValueError('ASSIGNMENT_NOT_RUNNING: it is ' + state['state'])
    if state['state'] == 'READY': state.update(state='RUNNING', reason='')
    state.update(driver=None, lease_until=None)
    # what the service may step it with: the authority recorded at agent.assign, narrowed to what the releasing principal
    # holds (the one handing it over); an assignment recorded before the column takes the releasing principal's own
    granted = narrowed(state.get('authority'), authority_of(principal))
    with opened(kernel) as db: db.execute('UPDATE agent_assignments SET authority=? WHERE id=?', (json.dumps(granted, sort_keys=True), state['id']))
    state['authority'] = granted
    words = ('Released: the Graphite service continues it while no desktop steps it' if continue_when_closed(kernel) else
             'Released, but Continue assignments while Graphite is closed is off: nothing steps it until a desktop does')
    return {'assignment': report(kernel, state)['assignment'], 'next': words}


# -- the Ledger service's side (AGENT-02) ------------------------------------------------------------------------------------

def continue_when_closed(kernel):
    """The owner's setting agent.continue_when_closed as stored in this workspace's Kernel settings (ledger.agent.continue_when_closed);
    the registry default (on) when nothing is stored. A row that cannot be read or is not a boolean reads as off, so the service
    never steps on a value it cannot vouch for."""
    try:
        from .settings_registry import BY_KEY
        default = bool(BY_KEY[SETTING]['default'])
    except Exception: default = True
    try:
        with kernel.db() as db: row = db.execute('SELECT value FROM settings WHERE key=?', ('ledger.' + SETTING,)).fetchone()
    except Exception: return False
    if row is None: return default
    try: value = json.loads(row[0])
    except (TypeError, ValueError): return False
    return value if isinstance(value, bool) else False


SERVICE_SCOPES = frozenset({'read', 'execute'})
MODES = ('Engineer', 'Tutor', 'Autonomous')


def authority_of(principal):
    """What a principal grants an assignment for the Ledger service's steps (recorded in the column authority): its read and
    execute scopes, its paths, tools and mode. Never approve or candidate."""
    return {'scopes': sorted(set(principal.scopes) & SERVICE_SCOPES), 'paths': [str(p) for p in principal.paths],
            'tools': [str(t) for t in principal.tools], 'mode': str(principal.mode)}


def within(path, ceiling):
    """The host's own delegation rule (host_ipc.delegation): inside an entry ending in '/' when it starts with it, else equal."""
    return any(path.startswith(c) if c.endswith('/') else path == c for c in ceiling)


def narrowed(recorded, other):
    """The authority both grant: the common scopes and tools, the paths inside both (a path of either that lies inside one of
    the other's), and Tutor when either is Tutor (else the recorded mode). With nothing recorded, the other's."""
    if not isinstance(recorded, dict): return dict(other)
    mine = [p for p in recorded.get('paths') or () if isinstance(p, str)]; theirs = [p for p in other.get('paths') or () if isinstance(p, str)]
    paths = list(dict.fromkeys([p for p in mine if within(p, theirs)] + [p for p in theirs if within(p, mine)]))
    tools = set(other.get('tools') or ())
    mode = 'Tutor' if 'Tutor' in (recorded.get('mode'), other.get('mode')) else (recorded.get('mode') or other.get('mode') or 'Engineer')
    return {'scopes': sorted(set(recorded.get('scopes') or ()) & set(other.get('scopes') or ()) & SERVICE_SCOPES), 'paths': paths,
            'tools': [t for t in recorded.get('tools') or () if t in tools], 'mode': mode}


def owner_principal(identity, authority=None):
    """The principal the service steps an assignment with: its owner, read and execute at most (never approve or candidate), and
    no more than the owner granted: the scopes, paths, tools and mode recorded in `authority` (agent.assign, narrowed at
    agent.release), kept inside the operator's ceiling the way the host's own delegation is (host_ipc.delegation). A record
    from before the authority column steps with the operator's paths only when its owner is the desktop owner, and with the
    Principal defaults for any other identity, so a command-line or tool caller never gains the operator's paths through the
    service. Pausing (pause_all) needs only the identity."""
    from .engineering_kernel import Principal, operator
    ceiling = operator(identity)
    if not isinstance(authority, dict):
        if identity == operator().identity: return Principal(identity, SERVICE_SCOPES, ceiling.paths, ceiling.tools, ceiling.mode)
        return Principal(identity, SERVICE_SCOPES)
    scopes = frozenset(s for s in authority.get('scopes') or () if s in SERVICE_SCOPES)
    paths = tuple(dict.fromkeys(p for p in authority.get('paths') or () if isinstance(p, str) and p and within(p, ceiling.paths)))
    allowed = set(ceiling.tools)
    tools = tuple(dict.fromkeys(t for t in authority.get('tools') or () if t in allowed))
    mode = authority.get('mode') if authority.get('mode') in MODES else 'Engineer'
    return Principal(identity, scopes, paths, tools, mode)


def may_step(kernel, stop=None):
    """Whether the service may take a step now: `stop()` (the service's closing flag) is not set, the owner's setting is on and
    work is not held. Anything that cannot be read reads as no."""
    try:
        if stop is not None and stop(): return False
        if not continue_when_closed(kernel): return False
        from . import work_trail
        from .resource_control import background_reason
        return not work_trail.execution_held(kernel) and background_reason(kernel) is None
    except Exception: return False


def pump(kernel, limit=8, guard=None, stop=None):
    """Step every RUNNING assignment (all owners) whose desktop lease is not live, one step each, driver 'service'; at most
    `limit` per call. Nothing when the setting is off, work is held or `stop()` is true; the three are checked again under the
    guard before every step, so a batch under way ends at the step in flight when Master Stop holds work (it does so before it
    takes the dispatch lock), when the owner turns the setting off, or when the service begins to close. Returns
    [{id, state, step?}] for what it touched. `guard` (the service's dispatch lock) is held around each single step, so a
    desktop request never interleaves with one. Each step runs with owner_principal (the authority the owner granted).
    Never raises: a step's own failure lands in that assignment's reason through step_once; anything unexpected is recorded
    as WAITING with 'The Ledger service could not step it: …'."""
    out = []
    try:
        if not may_step(kernel, stop): return out
        now = time.time()
        with opened(kernel) as db:
            ensure(db)
            rows = [unpack(r) for r in db.execute("SELECT * FROM agent_assignments WHERE state='RUNNING' ORDER BY updated ASC").fetchall()]
    except Exception: return out
    for state in rows:
        if len(out) >= max(0, int(limit)): break
        if lease_live(state, now, 'desktop'): continue
        try:
            with (guard if guard is not None else contextlib.nullcontext()):
                if not may_step(kernel, stop): break   # Master Stop, the setting or the service's close arrived during the batch
                result = step_once(kernel, state['id'], owner_principal(state['owner'], state.get('authority')), driver='service')
            row = {'id': state['id'], 'state': result['assignment']['state']}
            if result.get('step') is not None: row['step'] = result['step']
            out.append(row)
        except ValueError as exc:
            if str(exc).startswith(DRIVEN_BY_DESKTOP):   # the desktop took it back between the listing and the step
                out.append({'id': state['id'], 'state': 'RUNNING', 'driven_by': 'desktop'}); continue
            out.append(service_trouble(kernel, state, exc))
        except Exception as exc:
            out.append(service_trouble(kernel, state, exc))
    return out


def service_trouble(kernel, state, exc):
    """An unexpected exception while the service stepped an assignment: WAITING with the words, never an exception."""
    words = ('The Graphite service could not step it: ' + words_of(exc))[:600]
    try:
        with opened(kernel) as db:
            ensure(db); fresh = load(db, state['id'], state['owner'])
            if fresh['state'] == 'RUNNING':
                fresh.update(state='WAITING', reason=words, pending=None, model_job=None); store(db, fresh)
    except Exception: pass
    return {'id': state['id'], 'state': 'WAITING', 'error': words}


def pause_all(kernel, reason):
    """Pause every READY and RUNNING assignment of any owner with the reason (Master Stop on the service side); returns the ids.
    Never raises: an assignment that cannot be paused is left as it was."""
    reason = ' '.join(str(reason or '').split())[:300] or 'Paused'
    try:
        with opened(kernel) as db:
            ensure(db)
            rows = db.execute("SELECT id, owner FROM agent_assignments WHERE state IN ('READY','RUNNING') ORDER BY updated ASC").fetchall()
    except Exception: return []
    paused = []
    for row in rows:
        try: pause(kernel, {'id': row['id'], 'reason': reason}, owner_principal(row['owner'])); paused.append(row['id'])
        except Exception: continue
    return paused


def status(kernel, ident, principal):
    with opened(kernel) as db:
        ensure(db)
        if ident: return [status_row(db, load(db, ident, principal.identity))]
        rows = db.execute('SELECT * FROM agent_assignments WHERE owner=? ORDER BY updated DESC', (principal.identity,)).fetchall()
        return [status_row(db, unpack(r)) for r in rows]


def listing(kernel, principal):
    with opened(kernel) as db:
        ensure(db)
        return [summary_row(unpack(r)) for r in db.execute('SELECT * FROM agent_assignments WHERE owner=? ORDER BY updated DESC', (principal.identity,)).fetchall()]


def dispatch(kernel, op, args, principal):
    if op == 'agent.assign': return assign(kernel, args, principal)
    if op == 'agent.step': return step_once(kernel, args['id'], principal, args.get('driver') or 'desktop')
    if op == 'agent.release': return release(kernel, args, principal)
    if op == 'agent.run': return run(kernel, args, principal)
    if op == 'agent.pause': return pause(kernel, args, principal)
    if op == 'agent.resume': return resume(kernel, args, principal)
    if op == 'agent.stop': return stop(kernel, args, principal)
    if op == 'agent.status': return {'assignments': status(kernel, args.get('id'), principal)}
    if op == 'agent.list': return {'assignments': listing(kernel, principal)}
    raise ValueError('Unknown agent operation')
