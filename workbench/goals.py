"""What must be true when her hand is done: goals, their evidence, and the finish rule. Desk goals here; goals over data
(the relation form, ledger.goal/1 and the goals.* operations, 0.8.6 S1) are at the end of the module.

A goal is made from a template and its parameters, never from a model's words: its statement is the template's words with
the sheet's title put in. Its test is the same {path: matcher} a scene's step expects (desk_scene.lookup and matches), so a
scene's expect and a desk goal are one language; the planner reads the same paths from a predicted state (desk_ops.view).

Two modes. A "seen" goal is a milestone: it is met once a read of the window shows it, and the read is kept as its evidence
(the paths that matched, and a digest of what read.desk said of the window and the Field at that moment). It is not checked
again unless it is `persist`. A `persist` goal must still hold at the final read: the standing tidy goal, nothing left open
over the owner's window, ends every turn.

States, inside: OPEN, HOLDS, FAILS, UNDECIDED, SEEN, and a `stale` flag. On screen: open, holds, does not hold, cannot tell,
shown, recheck. The words "held", "BROKEN", "condition" and "interval" are not used here: Graphite gives them other meanings.

Pure Python: no Qt.
"""
import hashlib
import json
from dataclasses import dataclass, field

from .desk_scene import lookup, matches

OPEN, HOLDS, FAILS, UNDECIDED, SEEN = 'OPEN', 'HOLDS', 'FAILS', 'UNDECIDED', 'SEEN'
SHOWN_WORDS = {OPEN: 'open', HOLDS: 'holds', FAILS: 'does not hold', UNDECIDED: 'cannot tell', SEEN: 'shown'}
ORIGINS = ('OWNER', 'HER', 'DEDUCED', 'WORK_ORDER')

# template -> (statement, the paths it reads). Each statement is fixed words with the sheet's title put in.
TEMPLATES = {
    'traced': 'The trace of “{s}” is shown',
    'side_by_side': '“{a}” and “{b}” are side by side',
    'shown': '“{s}” is selected in the Field',
    'tidy': 'Nothing is left open over your window',
    'field': 'The Field is in front',
}
DESK_PARTS = ('where', 'field')         # the read.desk parts a desk goal's evidence digests


@dataclass
class Goal:
    id: str
    statement: str
    template: str
    params: dict
    aim: str = 'achieve'                # achieve, or decide
    mode: str = 'seen'                  # seen (a desk milestone) or hold
    persist: bool = False
    form: str = 'desk'
    bind: dict = field(default_factory=dict)
    bounds: list = field(default_factory=list)
    evidence: object = None
    state: str = OPEN
    stale: bool = False
    slack: object = None
    depends: tuple = ()
    origin: str = 'OWNER'
    agreed: bool = False
    agreed_by: str = ''
    test: object = None                 # its own {path: value}, for a goal over another table's acts (an App's); None: the template's

    @property
    def expect(self):
        return dict(self.test) if self.test is not None else expect_of(self.template, self.params)

    def predicate(self):
        """What makes it true, for the model's list and for its dedup: the template and the sorted parameters."""
        return (self.template, tuple(sorted(self.params.items())))

    def words(self):
        """Its state on her card."""
        word = SHOWN_WORDS.get(self.state, 'open')
        if self.persist and self.state == HOLDS:word = 'holds'
        return 'recheck' if self.stale else word

    def as_record(self):
        return {'id': self.id, 'statement': self.statement, 'template': self.template, 'params': dict(self.params), 'mode': self.mode,
                'persist': self.persist, 'state': self.state, 'stale': self.stale, 'origin': self.origin, 'agreed': self.agreed,
                'evidence': self.evidence}


def expect_of(template, params):
    """The goal's test as {path: value}: read.desk paths, the same as a scene step's expect."""
    if template == 'traced':return {'where.surface': 'field', 'field.route.owner_title': params['s']}
    if template == 'side_by_side':return {'where.surface': 'field', 'field.revisions.a': params['a'], 'field.revisions.b': params['b']}
    if template == 'shown':return {'where.surface': 'field', 'field.selected.title': params['s']}
    if template == 'tidy':return {'where.popups': []}
    if template == 'field':return {'where.surface': 'field'}
    raise ValueError('no goal template named %r' % template)


def make(template, params, n=1, origin='OWNER', persist=None):
    """A goal from its template: its words are the template's, never anyone's free words."""
    if template not in TEMPLATES:raise ValueError('no goal template named %r' % template)
    params = {k: str(v) for k, v in dict(params or {}).items()}
    statement = TEMPLATES[template].format(**params)
    keep = template == 'tidy' if persist is None else bool(persist)
    return Goal('C%d' % n, statement, template, params, mode='hold' if keep else 'seen', persist=keep, origin=origin)


def tidy(n):
    return make('tidy', {}, n, origin='DEDUCED')


def holds(goal, tree):
    """Whether the goal is true on a read.desk tree (or a predicted state's view)."""
    return all(matches(want, lookup(tree, path)) for path, want in goal.expect.items())


def digest(desk):
    """A digest of what read.desk said of the window and the Field."""
    part = {k: desk.get(k) for k in DESK_PARTS if isinstance(desk, dict)}
    return hashlib.sha256(json.dumps(part, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str).encode('utf-8')).hexdigest()


def observe(goals, desk, act=0):
    """Mark what this read shows: a seen goal that holds now is SEEN, with its evidence (once); a persist goal holds or is
    open again. Returns the goals that were newly seen."""
    seen = []
    for g in goals:
        if g.state == SEEN and not g.persist:continue      # a milestone met is not checked again
        if holds(g, desk):
            if g.persist:g.state = HOLDS
            else:g.state = SEEN;seen.append(g)
            g.evidence = {'paths': {p: lookup(desk, p) for p in g.expect}, 'digest': digest(desk), 'act': act}
        elif g.persist:
            g.state = OPEN
    return seen


def open_goals(goals):
    """The goals a plan still has to reach: every seen goal not yet seen, and every persist goal."""
    return [g for g in goals if g.persist or g.state != SEEN]


def finished(goals, desk):
    """The finish rule: every seen goal was seen, with its evidence; every persist goal holds at this final read.
    (whether done, the goals that are not)."""
    missing = []
    for g in goals:
        if g.persist:
            if not holds(g, desk):missing.append(g)
        elif g.state != SEEN or not g.evidence:missing.append(g)
    return not missing, missing


def phi(goals):
    """Progress, lower is nearer: twice each open goal, once each that cannot be told or must be checked again."""
    total = 0
    for g in goals:
        if g.stale:total += 1
        elif g.state == UNDECIDED:total += 1
        elif g.state in (OPEN, FAILS) and not (g.persist and g.state == HOLDS):total += 2
    return total


def closing(goals, acts):
    """The card's last line: how many acts, and what holds."""
    kept = [g for g in goals if not g.persist]
    met = sum(1 for g in kept if g.state == SEEN)
    if not kept:return 'Done in %d act%s.' % (acts, '' if acts == 1 else 's')
    what = ('both are shown' if met == 2 == len(kept) else 'it is shown' if met == 1 == len(kept) else
            'all %d are shown' % met if met == len(kept) else '%d of %d are shown' % (met, len(kept)))
    return 'Done in %d act%s; %s.' % (acts, '' if acts == 1 else 's', what)


# =========================================================================================================================
# 0.8.6 S1 · the relation form: goals over data (ledger.goal/1) and the goals.* operations
#
# A relation goal says that a reading (a Value cell of a reviewed sheet, or a calculation that already exists over such
# cells) is at most, below, at least or above a limit row. Its limit may have alternatives: the same row in two revisions
# of the limits (Rev A and Rev B). Which one applies is never deduced here: each alternative is a way, judged exactly,
# and the choice stays the owner's (her word, a later slice).
#
#   goals.candidates  {}                                       read     what she would propose from the desk: only rows
#                                                                       whose units fit, never stored ("mine, not agreed")
#   goals.keep        {candidate} | {id, expected_revision, state}  execute  the owner's press: keep a candidate as a
#                                                                       ledger.goal/1 record, or set one aside (OUT) and
#                                                                       back (IN); nothing is deleted
#   goals.list        {all?}                                   read     the kept goals (IN; with all, OUT too)
#   goals.get         {id}                                     read
#   goals.check       {id | candidate | (none: every kept goal), choose?, stages?, accuracy?}   read
#                     each way judged through math_answers.answer in process, with bindings to the cells as they stand
#                     (bindings_from_cells) and the owner's tolerances on them; several goals come back in her card's
#                     order (math_zones.order). model_calls: 0.
#
# Kasandra writes nothing here: goals.keep is execute scope and not among what her hand does by herself (stacy_hand
# HERS_SHOW, HERS_FREE), so it is always the owner's press. Every read leaves the records as they were.
# =========================================================================================================================
import re as _re
from fractions import Fraction as _Fraction

KIND = 'goal'
SCHEMA = 'ledger.goal/1'
GOAL_STATES = ('IN', 'OUT')
LIMIT_WORDS = {'limit': 'le', 'ceiling': 'le', 'maximum': 'le', 'max': 'le', 'minimum': 'ge', 'min': 'ge', 'floor': 'ge'}
RELATION_TEMPLATES = {'le': '{left} is at most the {limit}', 'lt': '{left} is below the {limit}',
                      'ge': '{left} is at least the {limit}', 'gt': '{left} is above the {limit}'}
SIGNS = {'le': '<=', 'lt': '<', 'ge': '>=', 'gt': '>'}
STAGES = ('check', 'room', 'settle')
_ID = {'type': 'string', 'minLength': 32, 'maxLength': 32}
_KEY = {'type': 'string', 'pattern': '^[a-f0-9]{64}$'}
_SHEET = {'type': 'string', 'pattern': '^owner:[a-f0-9]{32}$'}
_ACCURACY = {'type': 'object', 'additionalProperties': False, 'required': ['name', 'amount'],
             'properties': {'name': {'type': 'string', 'minLength': 1, 'maxLength': 64}, 'amount': {'type': 'string', 'minLength': 1, 'maxLength': 100}}}
FIELDS = {
    'goals.candidates': ({}, []),
    'goals.keep': ({'candidate': _KEY, 'id': _ID, 'expected_revision': {'type': 'integer', 'minimum': 1},
                    'state': {'type': 'string', 'enum': list(GOAL_STATES)}}, []),
    'goals.list': ({'all': {'type': 'boolean'}}, []),
    'goals.get': ({'id': _ID}, ['id']),
    'goals.check': ({'id': _ID, 'candidate': _KEY, 'choose': {'type': 'array', 'maxItems': 8, 'items': _SHEET},
                     'stages': {'type': 'array', 'maxItems': 3, 'items': {'type': 'string', 'enum': list(STAGES)}},
                     'accuracy': {'type': 'array', 'maxItems': 4, 'items': _ACCURACY}}, []),
}
SCOPES = {op: 'execute' if op == 'goals.keep' else 'read' for op in FIELDS}


def _symbol(parameter, taken):
    """An expression name from a row's parameter: 'Startup duration limit' -> startup_duration_limit."""
    name = _re.sub(r'[^a-z0-9]+', '_', str(parameter).lower()).strip('_')[:56] or 'value'
    if name[0].isdigit():name = 'q_' + name
    base, n = name, 2
    while name in taken:name = '%s_%d' % (base, n);n += 1
    taken.add(name)
    return name


def _limit(parameter):
    """(stem, relation) of a limit row's parameter ('Startup power ceiling' -> ('startup power', 'le')); None otherwise."""
    words = str(parameter).strip().split()
    if len(words) < 2 or words[-1].lower() not in LIMIT_WORDS:return None
    return ' '.join(words[:-1]).lower(), LIMIT_WORDS[words[-1].lower()]


def _dimension(unit):
    from .math_answers import cell_unit
    from .math_units import unit_spec
    from .math_ranges import RangeError
    try:return unit_spec(cell_unit(unit)[0])[0]
    except (RangeError, ValueError):return None


def _sheets():
    """The reviewed PDF sheets of the office store: [saved]."""
    from .office_service import store
    from .datasheet_work import SHEET
    found = []
    for row in store().listing():
        try:saved = store().get(row['id'])
        except (ValueError, OSError, KeyError):continue
        if (saved.get('origin') or {}).get('profile') == SHEET:found.append(saved)
    return found


def _rows(saved):
    """The sheet's Value rows as tolerances.sheet_cell gives them."""
    from .tolerances import sheet_cell
    cells = ((saved.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {}
    rows = []
    for key in sorted(cells, key=lambda k: (len(k), k)):
        if not _re.fullmatch(r'B[1-9][0-9]{0,2}', key) or key == 'B1':continue
        found = sheet_cell(saved, key)
        if found and found['parameter']:rows.append(found)
    return rows


def _calculations(kernel, principal):
    """The calculations worked out from reviewed sheets that stand now (not replaced): [{'id', 'title', 'sheet',
    'expression', 'inputs': [{symbol, cell, parameter}], 'unit'}]."""
    from . import project_desk as records, documents
    from .datasheet_work import REPORT
    with kernel.db() as db:
        records.ensure(db)
        ids = [row[0] for row in db.execute('SELECT id FROM desk_records WHERE owner=? AND kind=? ORDER BY rowid', (principal.identity, documents.KIND))]
        docs = [records.read(db, documents.KIND, ident, principal) for ident in ids]
    replaced = {(d.get('derivation') or {}).get('replaces') for d in docs}
    found = []
    for d in docs:
        derivation = d.get('derivation') or {}
        if derivation.get('profile') != REPORT or d['id'] in replaced or not derivation.get('recipe'):continue
        value = (((derivation.get('calculation') or {}).get('outputs') or [{}])[0] or {}).get('value') or {}
        found.append({'id': d['id'], 'title': d.get('title') or '', 'sheet': derivation.get('sheet'), 'expression': derivation['recipe'].get('expression', ''),
                      'inputs': [{'symbol': i['symbol'], 'cell': i['cell'], 'parameter': i.get('parameter', '')} for i in derivation.get('inputs') or ()],
                      'unit': value.get('unit') or derivation['recipe'].get('output_unit') or ''})
    return found


def _key(goal):
    part = {k: goal[k] for k in ('relation', 'expression', 'cells', 'alternatives')}
    return hashlib.sha256(json.dumps(part, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def _ref(cell):
    return {'address': cell['address'], 'sheet': cell['sheet'], 'cell': cell['cell'], 'parameter': cell['parameter'], 'title': cell['title']}


def candidates(kernel, principal):
    """The relation goals she would propose from the desk, as data and never stored: each limit row (a parameter ending in
    limit, ceiling, maximum or minimum), its alternatives (the same row on other sheets: the revisions), and a reading row or
    an existing calculation whose name is the limit's and whose unit is of the same kind. Rows whose units do not fit are
    never paired."""
    sheets = _sheets();limits = {};readings = []
    for saved in sheets:
        for row in _rows(saved):
            found = _limit(row['parameter'])
            if found:limits.setdefault((row['parameter'], found[1]), []).append(row)
            else:readings.append(row)
    by_id = {saved['id']: saved for saved in sheets}
    calcs = [c for c in _calculations(kernel, principal) if c['sheet'] in by_id]
    proposed = []
    for (parameter, relation), alternatives in sorted(limits.items()):
        stem = _limit(parameter)[0];want = _dimension(alternatives[0]['unit'])
        if want is None or any(_dimension(a['unit']) != want for a in alternatives):continue
        lefts = []
        for row in readings:
            if row['parameter'].lower() == stem and _dimension(row['unit']) == want:lefts.append(('cell', row))
        for calc in calcs:
            if stem in calc['title'].lower() and _dimension(calc['unit']) == want:lefts.append(('calculation', calc))
        for sort, left in lefts:
            taken = set();cells = {};roles = {}
            if sort == 'cell':
                name = _symbol(left['parameter'], taken);cells[name] = _ref(left);roles[name] = 'measured';expression = name;via = None
            else:
                from .tolerances import sheet_cell
                sheet = by_id[left['sheet']];via = left['id'];names = {}
                for item in left['inputs']:
                    cell = sheet_cell(sheet, item['cell'])
                    if not cell:continue
                    name = _symbol(cell['parameter'], taken);cells[name] = _ref(cell);roles[name] = 'measured';names[item['symbol']] = name
                if len(cells) != len(left['inputs']):continue        # a cell the calculation read is no longer on its sheet
                expression = _re.sub(r'\b[A-Za-z_][A-Za-z0-9_]*\b', lambda m: names.get(m.group(0), m.group(0)), left['expression'])
            limit = _symbol(parameter, taken);roles[limit] = 'limit'
            options = [_ref(a) for a in alternatives]
            goal = {'statement': RELATION_TEMPLATES[relation].format(left=stem[:1].upper() + stem[1:], limit=parameter[:1].lower() + parameter[1:]),
                    'form': 'relation', 'relation': relation, 'expression': '%s %s %s' % (expression, SIGNS[relation], limit),
                    'cells': {**cells, limit: options[0]}, 'alternatives': {limit: options} if len(options) > 1 else {}, 'roles': roles,
                    'via': via, 'origin': 'HER'}
            goal['key'] = _key(goal)
            proposed.append(goal)
    return proposed


def _ways(goal, choose=()):
    """Every way the goal's alternatives can be read: [{symbol: alternative}], the choice in `choose` (sheet ids) taken where
    one is named. At most mind_types.BUDGET.ways of them, and how many there were."""
    from .mind_types import BUDGET
    from itertools import product as _product
    options = []
    for symbol, alternatives in sorted((goal.get('alternatives') or {}).items()):
        chosen = [a for a in alternatives if a['sheet'] in set(choose or ())]
        options.append([(symbol, a) for a in (chosen or alternatives)])
    every = [dict(choice) for choice in _product(*options)] if options else [{}]
    return every[:BUDGET.ways], len(every)


def _freshness(kernel, principal, saved):
    from .datasheet_work import sheet_state
    try:return 'CURRENT' if sheet_state(kernel, principal, saved['origin'])['state'] == 'CURRENT_PDF_SOURCE' else 'REVIEW_REQUIRED'
    except (ValueError, OSError, KeyError):return 'REVIEW_REQUIRED'


def judge(kernel, principal, goal, choose=(), stages=('check',), accuracy=()):
    """A relation goal judged under every way the desk knows (each alternative of its limit), each through
    math_answers.answer in process: {'goal', 'statement', 'state' (the ways' common state, or DEPENDS), 'ways': [{'choice',
    'state', 'answers': {stage: ledger.math-answer/1}}], 'judgement' (mind_types.Judgement), 'model_calls': 0}."""
    from . import math_answers as answers, tolerances
    from .math_ranges import RangeError
    from .mind_types import Judgement, Way, BUDGET, DEPENDS
    from .office_service import store
    said = tolerances.on_cells(kernel, principal);ways, every = _ways(goal, choose);rows = [];shapes = []
    stages = tuple(stages or ('check',));sheets = {}
    def saved_of(sheet):
        if sheet not in sheets:
            try:sheets[sheet] = store().get(sheet)
            except (ValueError, OSError, KeyError):sheets[sheet] = None
        return sheets[sheet]
    for choice in ways:
        bound = {**goal['cells'], **choice};cells = {};fresh = 'CURRENT';missing = []
        for symbol, ref in bound.items():
            saved = saved_of(ref['sheet'])
            cell = tolerances.sheet_cell(saved, ref['cell']) if saved else None
            if not cell or cell['parameter'] != ref['parameter']:missing.append(ref);continue
            cells[symbol] = cell
            if _freshness(kernel, principal, saved) != 'CURRENT':fresh = 'REVIEW_REQUIRED'
        asked = {'expression': goal['expression'], **({'accuracy': list(accuracy)} if accuracy else {})}
        if missing:
            found = {stage: answers.refused(stage, asked, 'MISSING_INPUT', 'A row this goal reads is no longer where it was: %s' % ', '.join(
                '%s %s' % (r['title'], r['cell']) for r in missing), fresh) for stage in stages}
        else:
            try:ir, inputs = answers.bindings_from_cells(goal['expression'], cells, said, roles=goal.get('roles'))
            except (RangeError, ValueError) as exc:
                found = {stage: answers.refused(stage, asked, getattr(exc, 'code', 'UNSUPPORTED'), str(exc), fresh) for stage in stages}
            else:
                found = {stage: answers.answer(stage, ir, inputs, asked, fresh) for stage in stages}
        main = found[stages[0]]
        picked = {symbol: {'sheet': ref['sheet'], 'title': ref['title'], 'cell': ref['cell']} for symbol, ref in choice.items()}
        rows.append({'choice': picked, 'state': main['state'], 'answers': found})
        room = None;unit = ''
        slack = (main.get('result') or {}).get('slack')
        if slack:
            from .math_units import rational
            lo, hi = rational(slack[0]['rational']), rational(slack[1]['rational']);unit = slack[0]['unit']
            room = (lo, hi) if goal['relation'] in ('le', 'lt') else (-hi, -lo)
        shapes.append(Way(choices=tuple(sorted((s, c['title']) for s, c in picked.items())), state=main['state'], room=room, unit=unit,
                          answer=main['digest'], words=main['words']['answer']))
    states = {row['state'] for row in rows}
    state = rows[0]['state'] if len(states) == 1 else DEPENDS
    budget = (len(ways), every, BUDGET.sentence(len(ways), every, 'the other ways of reading the limits') if every > len(ways) else '')
    judgement = Judgement(about=(goal.get('id') or goal.get('key'),), state=state, ways=tuple(shapes), budget=budget,
                          rests_on=tuple(sorted({'%s %s' % (ref['title'], ref['cell']) for ref in goal['cells'].values()})))
    return {'goal': goal.get('id'), 'key': goal.get('key'), 'statement': goal['statement'], 'state': state, 'ways': rows,
            'judgement': judgement.as_record(), 'model_calls': 0}


def _rank(judged):
    """The card's order key of a judged goal: its least favourable way."""
    from .math_units import rational
    worst = None
    for row in judged['ways']:
        for stage in ('room', 'settle', 'check'):
            said = row['answers'].get(stage)
            if said and said.get('result'):break
        result = (said or {}).get('result') or {}
        share = result.get('share_of_limit');margin = result.get('worst')
        key = {'state': row['state'], 'share_of_limit': rational(share['rational']) if share else None,
               'worst': rational(margin['rational']) if margin else None}
        if worst is None or _order_key(key) < _order_key(worst):worst = key
    return worst or {'state': 'UNDECIDED'}


def _order_key(said):
    from .math_zones import RANK
    share = said.get('share_of_limit');share = said.get('worst') if share is None else share
    return (RANK.get(said.get('state'), 1), share if share is not None else _Fraction(0))


def _records(kernel, principal):
    from . import project_desk as records
    with kernel.db() as db:
        records.ensure(db)
        ids = [row[0] for row in db.execute('SELECT id FROM desk_records WHERE owner=? AND kind=? ORDER BY rowid', (principal.identity, KIND))]
        return [records.read(db, KIND, ident, principal) for ident in ids]


def keep(kernel, args, principal):
    """The owner's press: keep a candidate as a ledger.goal/1 record, or set a kept goal aside (OUT) and back (IN), each a
    new revision; nothing is deleted."""
    from . import project_desk as records
    if args.get('candidate'):
        if set(args) - {'candidate'}:raise ValueError('GOAL_KEEP_FIELDS: keep a candidate by its key alone')
        found = next((c for c in candidates(kernel, principal) if c['key'] == args['candidate']), None)
        if found is None:raise ValueError('GOAL_CANDIDATE_GONE: the desk no longer proposes that goal; ask for the candidates again')
        with kernel.db() as db:
            records.ensure(db)                      # its migrations check begins the write transaction (BEGIN IMMEDIATE)
            for old in [records.read(db, KIND, row[0], principal) for row in db.execute(
                    'SELECT id FROM desk_records WHERE owner=? AND kind=?', (principal.identity, KIND))]:
                if old.get('key') == found['key']:raise ValueError('GOAL_ALREADY_KEPT: that goal is kept already')
            value = records.new(KIND, principal, schema=SCHEMA, **found, state='IN', set_by='owner', agreed=True, agreed_by='owner')
            return records.write(db, value, principal, 'GOAL_KEPT')
    if not {'id', 'expected_revision', 'state'} <= set(args):raise ValueError('GOAL_KEEP_FIELDS: give a candidate, or a goal with its revision and IN or OUT')
    with kernel.db() as db:
        records.ensure(db)                          # begins the write transaction (BEGIN IMMEDIATE)
        value = records.read(db, KIND, args['id'], principal);expected = args['expected_revision']
        records.edit(value, expected);value['state'] = args['state']
        return records.write(db, value, principal, 'GOAL_SET_ASIDE' if args['state'] == 'OUT' else 'GOAL_KEPT_AGAIN', expected=expected)


def dispatch(kernel, op, args, principal):
    from .office_service import owner
    owner(principal)                 # the sheets live in the owner's profile, as for office.get
    if op == 'goals.candidates':return {'candidates': candidates(kernel, principal), 'model_calls': 0}
    if op == 'goals.keep':return {'goal': keep(kernel, args, principal)}
    if op == 'goals.list':
        rows = _records(kernel, principal)
        return {'goals': [g for g in rows if args.get('all') or g.get('state') == 'IN']}
    if op == 'goals.get':
        from . import project_desk as records
        with kernel.db() as db:records.ensure(db);return {'goal': records.read(db, KIND, args['id'], principal)}
    if op == 'goals.check':
        stages = tuple(args.get('stages') or ('check',));choose = args.get('choose') or ();accuracy = args.get('accuracy') or ()
        if args.get('id') and args.get('candidate'):raise ValueError('GOAL_CHECK_FIELDS: check a kept goal or a candidate, not both')
        if args.get('id'):
            from . import project_desk as records
            with kernel.db() as db:records.ensure(db);goal = records.read(db, KIND, args['id'], principal)
            return judge(kernel, principal, goal, choose, stages, accuracy)
        if args.get('candidate'):
            goal = next((c for c in candidates(kernel, principal) if c['key'] == args['candidate']), None)
            if goal is None:raise ValueError('GOAL_CANDIDATE_GONE: the desk no longer proposes that goal; ask for the candidates again')
            return judge(kernel, principal, goal, choose, stages, accuracy)
        if 'room' not in stages and 'settle' not in stages:stages = stages + ('room',)      # the card's order needs the room
        judged = [judge(kernel, principal, g, choose, stages, accuracy) for g in _records(kernel, principal) if g.get('state') == 'IN']
        judged.sort(key=lambda j: (_order_key(_rank(j)), j['statement']))
        from .math_zones import WORDS
        return {'goals': judged, 'order': WORDS['order'], 'model_calls': 0}
    raise ValueError('Unknown goal operation')
