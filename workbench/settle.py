"""What would settle it, and whose move it is (0.8.6 S5, "Kas's mind, no model").

Any "cannot tell" gets a short list of what would settle it: the things that decide it alone first, then pairs. Each item
says who can settle it, from the closed table (mind_types.WHO_ANSWERS): your records (she reads them), the maths (she
works it out), you (anything that is yours to say: which revision applies, a tolerance, how a rule's words read, whether
a sheet is complete, your own account, and anything stacy_hand.ALWAYS_ASKS covers), a new reading (a measurement or a
document not yet on the desk), and the model (only which numbered thing your words meant; you when no model is loaded).
Each open premise is one mind_types.OpenPoint, computed on read and never stored.

The core is pure: weigh(formula, values) over a four-valued formula of leaves (('leaf', name), ('not', f), ('and', f, ...),
('or', f, ...), ('const', state)), each leaf HOLDS, FAILS, CONFLICT or open (UNDECIDED). It is exact by enumeration of
the completions: every way of settling the open leaves (each holds or does not), evaluated with stac/evidence.py's Belnap
operations, at most BUDGET.settle_leaves (12) open leaves, as bit sets over the 2**n completions. For each open leaf it
gives what settling it alone would do, whether it decides alone (ALONE), only together with one other leaf (PAIR) or not
within the budget, whether alone it decides both ways, and the smallest sets of leaves that would make it hold and that
would make it not hold (at most BUDGET.make_hold_sets each; supersets of a set already found are not listed). Past a
budget she says the one sentence for a partial answer.

On the desk:

  field.settle  {id, choose?, at?, reading?, accuracy?, on?, sheet?, model_loaded?}   read
      a goal ('goal:…', or a finding that speaks of one): the ways of either_way.judge_goal, worked out with the settle
      stage of the maths (math_zones): a choice that is still open (which revision applies: you; which row your words
      meant: the model, or you), and each reading with a range (a new reading): the share of its range a reading of it
      settles, the zones and, with a meter's accuracy, the readings that settle it each way and the band where they do not.
      'period:' and a clause: which event started the period (you), whether the ledger sheet is complete (you), and a
      payment not yet on the desk (a new reading).

next_step(points, brain=None) is what she does next. When exactly one decisive leaf is open, nobody is asked anything that
is not needed: she says what she will read, works it out, or asks the one question, and no model is called. Where the best
steps truly tie, the NEXT options are the tied steps (at most three) and "none of these": at most four, put to the model
only when one is loaded and a brain is given, otherwise as buttons for you. A brain's answer is checked before it is used.
0.8.7 B2: worth asking? (judgment.gate) stands in front of the brain. The tied steps are weighed (settles: the share a step
decides; undo class: her own read or working out 0, a question to you or a new reading 3, neither being a step she can take
back; authority: anything only you can settle), and a tie that holds a step only you can settle goes to you as buttons,
never to the model; a step the others dominate is dropped, and one step left is taken. The result carries the gate's
decision ('gate') and, as before, model_calls.

Kasandra writes nothing here: every operation is a read. No model is imported; a brain is only ever a callable passed in.
No float: shares and ends are exact Fractions.
"""
from __future__ import annotations

from fractions import Fraction
from itertools import combinations, product

from .mind_types import (ALONE, AUTHORITY, BUDGET, CONFLICT, FAILS, FACT_MISSING, HOLDS, MATHS, MODEL, NOT_DECISIVE, PAIR, RECORDS, STATE_WORDS,
                         UNDECIDED, WHO_WORDS, WORLD, YOU, Leaf, OpenPoint, Way, _plain, who as _who)
from .project_desk import digest

SETTLED = (HOLDS, FAILS)
DECISIVE_RANK = {ALONE: 0, PAIR: 1, NOT_DECISIVE: 2}
WHO_RANK = {RECORDS: 0, MATHS: 0, WORLD: 1, YOU: 1, MODEL: 1}       # what she can do herself comes before any question
WORK = 1 << 15                     # cube checks for the smallest sets; past it, the budget sentence
NEXT_OPTIONS = 3                   # tied steps put as NEXT options, before "none of these": at most four in all
NONE_OF_THESE = 'None of these'

# Her words for what would settle it: fixed templates (design 3.6). No "chance", "likely", "probability", "risk of" or
# "safe": a share of a range is a share of the range.
WORDS = {
    'nothing_open': 'Nothing is open: it {state} under every reading the desk knows of.',
    'too_many': 'There are more ways to read this than I work out for one question, so I have not weighed what would settle it.',
    'count': '{n} thing{s} would settle this.',
    'alone': '{what} settles it alone: {outcomes}.',
    'pair': '{what} settles it together with {other}: {outcomes}.',
    'not_decisive': '{what} does not settle it alone or in a pair.',
    'make_hold': 'Together, these would make it hold: {sets}.',
    'make_fail': 'Any one of these would make it not hold: {sets}.',
    'make_fail_sets': 'These would make it not hold: {sets}.',
    'none_hold': 'No one or two of them settle it both ways.',
    'who': 'Who: {who}.',
    'meter': 'With a meter good to {accuracy}, a reading settles it, unless it lies between {lo} and {hi}.',
    'meter_holds': 'With a meter good to {accuracy}, a reading at or {side} {reading} settles it: it holds.',
    'meter_fails': 'With a meter good to {accuracy}, a reading at or {side} {reading} settles it: it does not hold.',
    'first': 'Measure {name} first.',
    'read': 'I read {about}.',
    'work': 'I work out {about}.',
    'ask': '{about}: yours to say.',
    'world': 'A new reading of {about} would settle it.',
    'model': 'Which one your words meant: {about}.',
    'tie': 'These steps weigh the same, so I put them to you: {options}.',
    'tie_model': 'These steps weigh the same, so the model was asked which comes first, and its pick was checked.',
    'one_step': 'One thing is open, so I ask nothing else: {step}',
    'tie_yours': 'These steps weigh the same, and settling one of them is yours to say, so I put them to you: {options}.',   # 0.8.7 B2
    'complete': 'whether “{title}” is complete from {start} to the last day',
    'credit': 'a credit of {amount} dated by the last day, from a statement not yet on the desk',
}


# =========================================================================================================================
# The core: a four-valued formula, weighed over the completions of its open leaves (pure)
# =========================================================================================================================

def _support(state):
    from .stac.evidence import EvidenceSupport
    return {HOLDS: EvidenceSupport(True, False), FAILS: EvidenceSupport(False, True), CONFLICT: EvidenceSupport(True, True)}.get(state, EvidenceSupport())


def _state(support):
    return {(True, False): HOLDS, (False, True): FAILS, (True, True): CONFLICT}.get((support.positive, support.negative), UNDECIDED)


def leaves_of(formula):
    """The leaves of a formula, each once, in the order they first appear."""
    found = []

    def walk(f):
        if f[0] == 'leaf':
            if f[1] not in found:found.append(f[1])
        elif f[0] in ('not', 'and', 'or'):
            for part in f[1:]:walk(part)
        elif f[0] != 'const':raise ValueError('FORMULA_SHAPE: a formula is leaf, not, and, or or const')
    walk(formula)
    return found


def evaluate(formula, values):
    """The formula's four-valued state under `values` ({leaf: state}; a leaf not given is open), with stac/evidence.py's
    Belnap operations (truth_and, truth_or, negate)."""
    from .stac.evidence import negate, truth_and, truth_or

    def go(f):
        if f[0] == 'leaf':return _support(values.get(f[1], UNDECIDED))
        if f[0] == 'const':return _support(f[1])
        if f[0] == 'not':return negate(go(f[1]))
        parts = [go(p) for p in f[1:]]
        if not parts:raise ValueError('FORMULA_SHAPE: and and or need at least one part')
        found = parts[0]
        for p in parts[1:]:found = truth_and(found, p) if f[0] == 'and' else truth_or(found, p)
        return found
    return _state(go(formula))


def _outcome(bits, cube):
    present = [s for s in (HOLDS, FAILS, CONFLICT, UNDECIDED) if bits[s] & cube]
    return present[0] if len(present) == 1 else UNDECIDED


def weigh(formula, values=None, budget=BUDGET):
    """What would settle the formula, exactly, by its completions. {'state' (the state over every completion: HOLDS or
    FAILS when they all agree), 'four_valued' (the formula's own Belnap value), 'open', 'beyond' (open leaves past the
    budget, left open), 'leaves': {leaf: {'alone': {HOLDS: outcome if it holds, FAILS: outcome if it does not},
    'settles', 'both_ways', 'decisive'}}, 'pairs': [{'leaves', 'values', 'outcome'}] (pairs that settle it where neither
    of the two alone with that value does), 'pairs_both_ways' (pairs whose four settings give both answers), 'make_hold', 'make_fail': [{'leaves', 'values': [[...]]}] (the smallest sets),
    'budget': (tried, of, sentence)}."""
    values = dict(values or {})
    names = leaves_of(formula)
    open_ = [n for n in names if values.get(n, UNDECIDED) == UNDECIDED]
    weighed = open_[:budget.settle_leaves];beyond = open_[budget.settle_leaves:]
    n = len(weighed);size = 1 << n;full = (1 << size) - 1
    bits = {HOLDS: 0, FAILS: 0, CONFLICT: 0, UNDECIDED: 0};ones = [0] * n
    for mask in range(size):
        here = dict(values)
        for i, name in enumerate(weighed):
            set_ = (mask >> i) & 1
            here[name] = HOLDS if set_ else FAILS
            if set_:ones[i] |= 1 << mask
        bits[evaluate(formula, here)] |= 1 << mask
    cube_of = [[full ^ ones[i], ones[i]] for i in range(n)]            # [does not hold, holds]
    now = _outcome(bits, full);notes = []
    if beyond:notes.append(budget.sentence(budget.settle_leaves, len(open_), 'the open leaves past the first %d, left open' % budget.settle_leaves))
    leaves = {}
    for i, name in enumerate(weighed):
        alone = {HOLDS: _outcome(bits, cube_of[i][1]), FAILS: _outcome(bits, cube_of[i][0])}
        settles = sorted({o for o in alone.values() if o in SETTLED})
        leaves[name] = {'alone': alone, 'settles': settles, 'both_ways': settles == [FAILS, HOLDS], 'decisive': ALONE if settles and now not in SETTLED else NOT_DECISIVE}
    pairs = [];both = []
    if now not in SETTLED and now != CONFLICT:
        for i, j in combinations(range(n), 2):
            if {_outcome(bits, cube_of[i][a] & cube_of[j][b]) for a, b in product((1, 0), repeat=2)} >= set(SETTLED):both.append([weighed[i], weighed[j]])
            for a, b in product((1, 0), repeat=2):
                o = _outcome(bits, cube_of[i][a] & cube_of[j][b])
                if o not in SETTLED:continue
                ai = leaves[weighed[i]]['alone'][HOLDS if a else FAILS];bj = leaves[weighed[j]]['alone'][HOLDS if b else FAILS]
                if o in (ai, bj):continue                       # one of the two alone already gives it
                pairs.append({'leaves': [weighed[i], weighed[j]], 'values': [HOLDS if a else FAILS, HOLDS if b else FAILS], 'outcome': o})
                for k in (i, j):
                    if leaves[weighed[k]]['decisive'] == NOT_DECISIVE:leaves[weighed[k]]['decisive'] = PAIR
    checks = [0]

    def smallest(target):
        found = [];complete = True
        if now in SETTLED or now == CONFLICT:return found, complete
        for k in range(1, n + 1):
            level = []
            for combo in combinations(range(n), k):
                if any(set(s) <= set(combo) for s, _ in found):continue
                works = []
                for assign in product((1, 0), repeat=k):
                    checks[0] += 1
                    if checks[0] > WORK:complete = False;break
                    cube = full
                    for i, v in zip(combo, assign):cube &= cube_of[i][v]
                    if cube and not (cube & (full ^ bits[target])):works.append(assign)
                if not complete:break
                if works:level.append((combo, works))
            found.extend(level)
            if not complete or len(found) >= budget.make_hold_sets:break
        return found, complete

    def shown(found):
        return [{'leaves': [weighed[i] for i in combo], 'values': [[HOLDS if v else FAILS for v in a] for a in works]} for combo, works in found]
    hold, hold_ok = smallest(HOLDS);fail, fail_ok = smallest(FAILS)
    for found, label in ((hold, 'make it hold'), (fail, 'make it not hold')):
        if len(found) > budget.make_hold_sets:
            notes.append(budget.sentence(budget.make_hold_sets, len(found), 'the other smallest sets that would %s' % label))
    if not (hold_ok and fail_ok):notes.append(budget.sentence(min(checks[0], WORK), checks[0], 'the larger sets of leaves'))
    return {'state': now, 'four_valued': evaluate(formula, values), 'open': weighed, 'beyond': beyond, 'leaves': leaves, 'pairs': pairs, 'pairs_both_ways': both,
            'make_hold': shown(hold[:budget.make_hold_sets]), 'make_fail': shown(fail[:budget.make_hold_sets]),
            'budget': (n, len(open_), ' '.join(notes))}


def decides(formula, values, settle):
    """The outcome when the leaves in `settle` ({leaf: HOLDS or FAILS}) are settled and the rest stay open, over every
    completion: HOLDS or FAILS when they all agree, else UNDECIDED (CONFLICT when every completion is a conflict)."""
    values = {**dict(values or {}), **dict(settle)}
    open_ = [n for n in leaves_of(formula) if values.get(n, UNDECIDED) == UNDECIDED]
    if len(open_) > BUDGET.settle_leaves:raise ValueError(BUDGET.sentence(BUDGET.settle_leaves, len(open_), 'the other open leaves'))
    seen = set()
    for picked in product((HOLDS, FAILS), repeat=len(open_)):
        seen.add(evaluate(formula, {**values, **dict(zip(open_, picked))}))
        if len(seen) > 1:return UNDECIDED
    return seen.pop() if seen else UNDECIDED


# =========================================================================================================================
# Open points: one per open premise, ordered (pure)
# =========================================================================================================================

def _who_of(premise, model_loaded):
    return _who(premise, model_loaded)


def _cover(leaf):
    """How much of what is open a leaf settles: a reading's share of its range, or the share of a choice's values that settle."""
    if leaf.share is not None:return leaf.share
    return Fraction(1) if leaf.values else Fraction(0)


def order(points):
    """Open points in the order her card lists them: what decides alone, then pairs; what she can do herself before any
    question; the larger share first; then by name."""
    def key(p):
        leaf = p.leaves[0]
        return (DECISIVE_RANK.get(leaf.decisive, 2), WHO_RANK.get(leaf.who, 1), -_cover(leaf), leaf.id)
    return sorted(points, key=key)


def formula_points(about, formula, values, info=None, model_loaded=False, budget=BUDGET, proof=''):
    """The open points of a rule's conditions (or any four-valued formula): one per open leaf, its who from the closed
    table by its premise (info: {leaf: {'premise', 'about', 'words', 'holds', 'fails'}} where 'holds' and 'fails' name what
    settling it each way would be), each with what settling it alone gives. Returns (points, weighed, sentences)."""
    info = dict(info or {});found = weigh(formula, values, budget);points = []
    for name in found['open']:
        m = info.get(name) or {};row = found['leaves'][name]
        who, kind = _who_of(m.get('premise', 'VALUE_TO_WORK_OUT'), model_loaded)
        outcomes = tuple(Way(choices=((name, m.get('holds' if v == HOLDS else 'fails') or ('holds' if v == HOLDS else 'does not hold')),), state=row['alone'][v],
                             words='%s: %s' % (m.get('holds' if v == HOLDS else 'fails') or name, STATE_WORDS[row['alone'][v]])) for v in (HOLDS, FAILS))
        leaf = Leaf(id=name, about=tuple(m.get('about') or ()), premise=m.get('premise', 'VALUE_TO_WORK_OUT'), who=who, decisive=row['decisive'],
                    values=(HOLDS, FAILS), words=m.get('words', name))
        points.append(OpenPoint(about=tuple(about), kind=kind, who=who, leaves=(leaf,), outcomes=outcomes, proof=proof,
                                budget=found['budget'] if found['budget'][2] else (0, 0, '')))
    points = order(points);lines = []
    if found['state'] in SETTLED:
        lines.append(WORDS['nothing_open'].format(state=STATE_WORDS[found['state']]))
        return points, found, lines

    def what(name):return (info.get(name) or {}).get('words') or name

    def setting(name, v):
        m = info.get(name) or {}
        return m.get('holds' if v == HOLDS else 'fails') or ('%s, %s' % (what(name), 'yes' if v == HOLDS else 'no'))
    lines.append(WORDS['count'].format(n=len(points), s='' if len(points) == 1 else 's'))
    if found['make_fail'] and all(len(x['leaves']) == 1 for x in found['make_fail']):
        lines.append(WORDS['make_fail'].format(sets='; '.join(setting(x['leaves'][0], x['values'][0][0]) for x in found['make_fail'])))
    elif found['make_fail']:
        lines.append(WORDS['make_fail_sets'].format(sets='; '.join(' and '.join(setting(n, v) for n, v in zip(x['leaves'], x['values'][0])) for x in found['make_fail'])))
    if found['make_hold']:
        lines.append(WORDS['make_hold'].format(sets='; '.join(' and '.join(setting(n, v) for n, v in zip(x['leaves'], x['values'][0])) for x in found['make_hold'])))
    if len(found['open']) > 2 and not any(r['both_ways'] for r in found['leaves'].values()) and not found['pairs_both_ways']:
        lines.append(WORDS['none_hold'])
    whos = sorted({p.who for p in points}, key=lambda w: (WHO_RANK.get(w, 1), w))
    lines.append(WORDS['who'].format(who='; '.join(WHO_WORDS[w] for w in whos)))
    if found['budget'][2]:lines.append(found['budget'][2])
    return points, found, lines


# =========================================================================================================================
# Her next step: deduce where only one step is possible
# =========================================================================================================================

def _leaf(leaf):
    """A Leaf from a Leaf or its record (as_record: lists for tuples, a share as its exact text)."""
    if isinstance(leaf, Leaf):return leaf
    found = {k: (tuple(v) if isinstance(v, list) else v) for k, v in leaf.items() if k in Leaf.__dataclass_fields__}
    if found.get('share') is not None:found['share'] = Fraction(str(found['share']))
    return Leaf(**found)


def _point(point):
    if isinstance(point, OpenPoint):return point
    return OpenPoint(about=tuple(point.get('about') or ()), kind=point.get('kind', FACT_MISSING), who=point.get('who', YOU),
                     leaves=tuple(_leaf(l) for l in point.get('leaves') or ()), outcomes=(), proof=point.get('proof', ''))


def step_words(leaf):
    """What the step is, as she says it, by who settles it."""
    about = leaf.words or ', '.join(leaf.about) or leaf.id
    if leaf.who == RECORDS:return WORDS['read'].format(about=about)
    if leaf.who == MATHS:return WORDS['work'].format(about=about)
    if leaf.who == WORLD:return WORDS['world'].format(about=about)
    if leaf.who == MODEL:return WORDS['model'].format(about=about)
    return WORDS['ask'].format(about=about[:1].upper() + about[1:])


def _pick(answer, count):
    """A brain's answer checked: one number from 1 to count (count + 1 is "none of these"), as an int, {"pick": [n]} or
    "n"; anything else is refused (None)."""
    if isinstance(answer, dict):answer = answer.get('pick')
    if isinstance(answer, (list, tuple)):answer = answer[0] if len(answer) == 1 else None
    if isinstance(answer, str) and answer.strip().isdigit():answer = int(answer.strip())
    if isinstance(answer, bool) or not isinstance(answer, int):return None
    return answer if 1 <= answer <= count + 1 else None


def _option(leaf):
    """0.8.7 B2: a tied leaf as a step the gate weighs. settles: the share it decides (_cover); undo: her own read or working
    out 0, a question to you or a new reading 3 (neither is a step she can take back); authority: anything only you can
    settle (who YOU). Time is not known here, so no step is assumed quick and none is dominated."""
    from . import judgment
    own = leaf.who in (RECORDS, MATHS)
    return judgment.Option(key=leaf.id, words=step_words(leaf), settles=min(Fraction(1), max(Fraction(0), _cover(leaf))),
                           undo=judgment.READ if own else judgment.ASKS, authority=leaf.who == YOU)


def next_step(points, brain=None, model_loaded=False):
    """What she does next over a question's open points: {'route', 'step', 'options', 'words', 'model_calls'}.
    DEDUCED: exactly one decisive leaf is open, or one step weighs most; no one is asked anything that is not needed, and
    no brain is called. NEXT: the best steps truly tie; the options are the tied steps (at most three) and "none of
    these", put to the brain (one NEXT/1 turn, its pick checked) when a model is loaded and a brain is given, else
    BUTTONS for you. NOTHING: no open leaf decides anything."""
    leaves = [];seen = set()
    for p in points:
        for leaf in _point(p).leaves:
            if leaf.id in seen or leaf.decisive == NOT_DECISIVE:continue
            seen.add(leaf.id);leaves.append(leaf)
    if not leaves:return {'route': 'NOTHING', 'step': None, 'options': [], 'words': 'Nothing open here is settled by one more step.', 'model_calls': 0}

    def shown(leaf):return {'leaf': leaf.id, 'who': leaf.who, 'who_words': WHO_WORDS[leaf.who], 'decisive': leaf.decisive, 'words': step_words(leaf)}
    if len(leaves) == 1:
        return {'route': 'DEDUCED', 'step': shown(leaves[0]), 'options': [shown(leaves[0])],
                'words': WORDS['one_step'].format(step=step_words(leaves[0])), 'model_calls': 0}

    def key(leaf):return (DECISIVE_RANK.get(leaf.decisive, 2), WHO_RANK.get(leaf.who, 1), -_cover(leaf))
    ranked = sorted(leaves, key=lambda l: (key(l), l.id))
    top = [l for l in ranked if key(l) == key(ranked[0])]
    if len(top) == 1 or WHO_RANK.get(top[0].who, 1) == 0:
        return {'route': 'DEDUCED', 'step': shown(top[0]), 'options': [shown(top[0])], 'words': step_words(top[0]), 'model_calls': 0}
    # 0.8.7 B2: worth asking? The tied steps are weighed before any model is asked.
    from . import judgment
    tied = top[:NEXT_OPTIONS]
    decision = judgment.gate([_option(l) for l in tied], cost_ms=None, model_ready=brain is not None and model_loaded)
    by = {l.id: l for l in tied}
    if decision.route == 'FORCED':
        leaf = by[decision.take[0]]
        return {'route': 'DEDUCED', 'step': shown(leaf), 'options': [shown(leaf)], 'words': step_words(leaf), 'model_calls': 0, 'gate': decision.as_record()}
    options = [shown(by[k]) for k in decision.front] + [{'leaf': '', 'who': YOU, 'who_words': WHO_WORDS[YOU], 'decisive': '', 'words': NONE_OF_THESE}]
    if decision.route == 'OWNER':
        return {'route': 'BUTTONS', 'step': None, 'options': options, 'words': WORDS['tie_yours'].format(options='; '.join(o['words'].rstrip('.') for o in options)),
                'model_calls': 0, 'gate': decision.as_record()}
    if brain is not None and model_loaded:
        asked = {'turn': 'NEXT/1', 'options': ['%d. %s' % (n + 1, o['words']) for n, o in enumerate(options)]}
        pick = _pick(brain(asked), len(options) - 1)
        if pick is not None and pick <= len(options) - 1:
            return {'route': 'NEXT', 'step': options[pick - 1], 'options': options, 'words': WORDS['tie_model'], 'model_calls': 1, 'asked': asked}
        return {'route': 'BUTTONS', 'step': None, 'options': options, 'words': WORDS['tie'].format(options='; '.join(o['words'] for o in options)),
                'model_calls': 1, 'asked': asked, 'refused': pick is None}
    return {'route': 'BUTTONS', 'step': None, 'options': options, 'words': WORDS['tie'].format(options='; '.join(o['words'] for o in options)), 'model_calls': 0}


# =========================================================================================================================
# On the desk: a goal over data
# =========================================================================================================================

def _num(record):
    return None if record is None else Fraction(record['rational'])


def _piece(piece):
    """A zone from a math answer ({'lower', 'upper'} of {'value', 'closed'}) as ((value, closed) or None, ...), or None."""
    if piece is None:return None
    lower, upper = piece.get('lower'), piece.get('upper')
    return (None if lower is None else (_num(lower['value']), lower['closed']), None if upper is None else (_num(upper['value']), upper['closed']))


def _meet(a, b):
    """Two zones (intervals) met: the values in both, or None."""
    if a is None or b is None:return None
    lo = a[0] if b[0] is None else b[0] if a[0] is None else max(a[0], b[0], key=lambda e: (e[0], not e[1]))
    hi = a[1] if b[1] is None else b[1] if a[1] is None else min(a[1], b[1], key=lambda e: (e[0], e[1]))
    if lo is not None and hi is not None and (lo[0] > hi[0] or (lo[0] == hi[0] and not (lo[1] and hi[1]))):return None
    return (lo, hi)


def _length(piece, lo, hi):
    if piece is None:return Fraction(0)
    a = lo if piece[0] is None else max(lo, piece[0][0]);b = hi if piece[1] is None else min(hi, piece[1][0])
    return max(Fraction(0), b - a)


def _ranged(record):
    """{name: (lo, hi, unit)} of a math answer's inputs that have a range."""
    out = {}
    for row in record.get('inputs') or ():
        if row.get('range'):out[row['name']] = (_num(row['range'][0]), _num(row['range'][1]), row['unit'])
    return out


def _zone_row(record, name):
    return next((z for z in ((record.get('result') or {}).get('zones') or ()) if z.get('name') == name and z.get('state') == 'ANSWERED'), None)


def _numeric(judged, model_loaded, accuracy):
    """The open readings of a goal: one OpenPoint for each input with a range, its zones met across the ways that are not
    settled; a way that holds whatever the reading leaves no reading that makes it fail in every way, and the other way
    round. With a meter's accuracy, the band of readings that would not settle it."""
    from .math_answers import figure
    from .math_zones import WORDS as ZONE_WORDS
    ways = list(zip(judged['ways'], judged['records']));names = {}
    for w, r in ways:
        for name, span in _ranged(r).items():names.setdefault(name, span)
    points = [];acc = {row['name']: Fraction(row['amount']) for row in accuracy or ()}
    if all(w['state'] in SETTLED for w, _ in ways):return points
    for name, (lo, hi, unit) in sorted(names.items()):
        holds = (None, None);fails = (None, None);one_share = Fraction(0);rows = []
        for w, r in ways:
            if w['state'] == HOLDS:fails = None;continue
            if w['state'] == FAILS:holds = None;continue
            z = _zone_row(r, name)
            if z is None:holds = fails = None;continue
            rows.append(z);holds = _meet(holds, _piece(z['holds']));fails = _meet(fails, _piece(z['fails']))
            if z.get('share'):one_share = max(one_share, Fraction(z['share']['rational']))
        width = hi - lo
        share = (_length(holds, lo, hi) + _length(fails, lo, hi)) / width if width else None
        decisive = ALONE if share else (PAIR if one_share and judged.get('relevant') else NOT_DECISIVE)
        who, kind = _who_of('NEW_READING', model_loaded)
        ref = next((w['bound'][name] for w, _ in ways if (w.get('bound') or {}).get(name)), {})
        about = ('%s, row %d' % (ref['title'], int(ref['cell'][1:])),) if ref else ()
        label = name.replace('_', ' ')
        words = [ZONE_WORDS['share'].format(name=label, share=str(share))] if share else []
        outcomes = []
        if holds is not None and holds[1] is not None:
            outcomes.append(Way(choices=((name, 'at or below %s' % figure(holds[1][0], unit)),), state=HOLDS, words='a reading %s %s: holds' % (
                'at or below' if holds[1][1] else 'below', figure(holds[1][0], unit))))
        if fails is not None and fails[0] is not None:
            outcomes.append(Way(choices=((name, 'above %s' % figure(fails[0][0], unit)),), state=FAILS, words='a reading %s %s: does not hold' % (
                'at or above' if fails[0][1] else 'above', figure(fails[0][0], unit))))
        if name in acc:words.extend(_meter_words(rows, acc[name], unit, holds, fails))
        leaf = Leaf(id=name, about=about, premise='NEW_READING', who=who, decisive=decisive, share=share,
                    zone={'holds': _ends(holds), 'fails': _ends(fails), 'range': [str(lo), str(hi)], 'unit': unit},
                    words=' '.join(words) or 'A new reading of %s.' % label)
        points.append(OpenPoint(about=(judged.get('key') or judged.get('goal') or '',), kind=kind, who=who, leaves=(leaf,), outcomes=tuple(outcomes),
                                proof=judged.get('proof', '')))
    return points


def _met_readings(pairs):
    """The readings that settle it the same way in every way still open: the maths core's settling readings ((lower,
    upper), each end a value or None) met across the ways, or None when any way has none."""
    if not pairs or any(p is None for p in pairs):return None
    lows = [p[0] for p in pairs if p[0] is not None];highs = [p[1] for p in pairs if p[1] is not None]
    lo = max(lows) if lows else None;hi = min(highs) if highs else None
    return None if lo is not None and hi is not None and lo > hi else (lo, hi)


def _meter_words(rows, accuracy, unit, holds, fails):
    """With a meter good to ±accuracy on a reading: the readings that settle it each way (the maths core's settling
    readings, rounded inward to whole steps, met across the ways still open) and the band where a reading does not.
    Where the core gave none, the band from the zones themselves, exactly."""
    from .math_answers import figure
    said = '±' + figure(accuracy, unit);ends = {'holds': [], 'fails': []}
    for z in rows:
        reading = z.get('reading') or {}
        for side in ends:
            got = reading.get(side)
            ends[side].append(None if not got else (_num(got.get('lower')), _num(got.get('upper'))))
    h, f = _met_readings(ends['holds']), _met_readings(ends['fails'])
    out = []
    if h and f:
        below = h[1] is not None and f[0] is not None and h[1] < f[0]          # holds below the band, fails above it
        above = h[0] is not None and f[1] is not None and h[0] > f[1]
        band = _band(holds, fails, accuracy, unit, said)
        if below:
            out.extend(band or [WORDS['meter'].format(accuracy=said, lo=figure(h[1], unit), hi=figure(f[0], unit))])
            out.append(WORDS['meter_holds'].format(accuracy=said, side='below', reading=figure(h[1], unit)))
        elif above:
            out.extend(band or [WORDS['meter'].format(accuracy=said, lo=figure(f[1], unit), hi=figure(h[0], unit))])
            out.append(WORDS['meter_holds'].format(accuracy=said, side='above', reading=figure(h[0], unit)))
        if out:return out
    if h is not None and (h[0] is None) != (h[1] is None):
        out.append(WORDS['meter_holds'].format(accuracy=said, side='below' if h[1] is not None else 'above', reading=figure(h[1] if h[1] is not None else h[0], unit)))
    if f is not None and (f[0] is None) != (f[1] is None):
        out.append(WORDS['meter_fails'].format(accuracy=said, side='above' if f[0] is not None else 'below', reading=figure(f[0] if f[0] is not None else f[1], unit)))
    return out or _band(holds, fails, accuracy, unit, said)


def _band(holds, fails, accuracy, unit, said):
    """The readings that do not settle it, exactly: from the top of the holds zone less the accuracy to the bottom of the
    fails zone plus it (or the other way round), as one sentence; [] where the zones do not give one."""
    from .math_answers import figure
    if holds is not None and fails is not None and holds[1] is not None and fails[0] is not None and holds[1][0] <= fails[0][0]:
        return [WORDS['meter'].format(accuracy=said, lo=figure(holds[1][0] - accuracy, unit), hi=figure(fails[0][0] + accuracy, unit))]
    if holds is not None and fails is not None and holds[0] is not None and fails[1] is not None and fails[1][0] <= holds[0][0]:
        return [WORDS['meter'].format(accuracy=said, lo=figure(fails[1][0] - accuracy, unit), hi=figure(holds[0][0] + accuracy, unit))]
    return []


def _ends(piece):
    if piece is None:return None
    return [None if e is None else {'value': str(e[0]), 'closed': e[1]} for e in piece]


def _choices(judged, model_loaded):
    """One OpenPoint for each choice that matters: per value, the state its ways give, and whether it settles it alone,
    only together with another choice or a reading, or not at all."""
    points = [];ways = judged['ways'];records = judged.get('records') or [None] * len(ways)
    for c in judged.get('choice_objects') or ():
        if c.name not in judged['relevant']:continue
        outcomes = [];settles = False;in_pair = False
        for v in sorted(c.values, key=str):
            sub = [(w, r) for w, r in zip(ways, records) if w['choice'].get(c.name) == v]
            states = {w['state'] for w, _ in sub}
            state = states.pop() if len(states) == 1 else UNDECIDED
            if state in SETTLED:settles = True
            elif any(w['state'] in SETTLED for w, _ in sub) or any(z.get('share') and Fraction(z['share']['rational']) > 0
                                                                     for _, r in sub if r for z in ((r.get('result') or {}).get('zones') or ())):in_pair = True
            told = '; '.join(sorted({w['words'] for w, _ in sub}))
            outcomes.append(Way(choices=((c.name, v),), state=state, room=sub[0][0].get('room') if len(sub) == 1 else None, unit=sub[0][0].get('unit', '') if len(sub) == 1 else '',
                                answer=sub[0][0].get('answer', '') if len(sub) == 1 else '', words='%s applies: %s' % (v, told)))
        who, kind = _who_of(c.premise, model_loaded)
        decisive = ALONE if settles else PAIR if in_pair else NOT_DECISIVE
        leaf = Leaf(id=c.name, about=(judged.get('key') or '',), premise=c.premise, who=who, decisive=decisive, values=tuple(sorted(c.values, key=str)),
                    words=c.words)
        points.append(OpenPoint(about=(judged.get('key') or judged.get('goal') or '',), kind=kind, who=who, leaves=(leaf,), outcomes=tuple(outcomes),
                                proof=judged.get('proof', '')))
    return points


def _lines(points, state):
    """Her "What would settle it" list: each point in order, with who."""
    lines = [WORDS['count'].format(n=len(points), s='' if len(points) == 1 else 's')] if points else []
    for p in points:
        leaf = p.leaves[0];what = (leaf.words.split('. ')[0] if leaf.premise == 'NEW_READING' else leaf.words) or leaf.id
        if leaf.premise == 'NEW_READING' and leaf.zone:     # a reading with a range: its share, zones and meter, as the maths says them
            lines.append('%s Who: %s.' % (leaf.words, WHO_WORDS[leaf.who]))
            continue
        outcomes = '; '.join(o.words for o in p.outcomes)
        key = {ALONE: 'alone', PAIR: 'pair', NOT_DECISIVE: 'not_decisive'}[leaf.decisive]
        text = WORDS[key].format(what=what[:1].upper() + what[1:], other='a reading or another choice', outcomes=outcomes)
        lines.append('%s Who: %s.' % (text, WHO_WORDS[leaf.who]))
    return lines


def settle_goal(kernel, principal, goal, *, choose=(), readings=None, at=None, accuracy=(), words=None, said=None, model_loaded=False, ident='', named=None,
                brain=None):
    """What would settle a goal over data: the ways of either_way.judge_goal at the settle stage, a point for each choice
    that matters and for each reading with a range, in order, and her next step. Reads only."""
    from .either_way import judge_goal
    judged = judge_goal(kernel, principal, goal, choose=choose, readings=readings, at=at, stage='settle', accuracy=accuracy, said=said, words=words,
                        model_loaded=model_loaded, ident=ident, named=named)
    base = {'goal': judged['goal'], 'key': judged['key'], 'statement': judged['statement'], 'state': judged['state'], 'form': judged['form'],
            'either': judged['words'], 'receipt': judged['receipt'], 'proof': judged.get('proof', ''), 'model_calls': 0}
    if judged['form'] == 'TOO_MANY':
        return {**base, 'points': [], 'words': [WORDS['too_many'], judged['budget'][2]], 'next': next_step([]), 'budget': judged['budget']}
    if judged['form'] == 'EITHER_WAY' and judged['state'] in SETTLED:
        return {**base, 'points': [], 'words': [WORDS['nothing_open'].format(state=STATE_WORDS[judged['state']])], 'next': next_step([]), 'budget': judged['budget']}
    points = order(_choices(judged, model_loaded) + _numeric(judged, model_loaded, accuracy))
    numeric = [p for p in points if p.leaves[0].premise == 'NEW_READING' and p.leaves[0].decisive == ALONE]
    lines = _lines(points, judged['state'])
    if len(numeric) > 1 and numeric[0].leaves[0].share != numeric[1].leaves[0].share:
        lines.insert(1, WORDS['first'].format(name=numeric[0].leaves[0].id.replace('_', ' ')))
    step = next_step(points, brain, model_loaded)
    return {**base, 'points': [p.as_record() for p in points], 'words': lines, 'next': step, 'budget': judged['budget'],
            'model_calls': step['model_calls']}


def settle_period(kernel, principal, clause=None, *, on=None, sheet=None, model_loaded=False, brain=None):
    """What would settle a payment within a period on the admitted papers: which event started it (yours to say, where it
    matters), whether the ledger sheet is complete (yours to say), and a payment not yet on the desk (a new reading)."""
    from .either_way import period_ways
    judged = period_ways(kernel, principal, clause, on=on, sheet=sheet, model_loaded=model_loaded)
    base = {'period': judged['period'], 'state': judged['state'], 'form': judged['form'], 'either': judged['words'], 'receipt': judged['receipt'],
            'proof': judged['proof'], 'model_calls': 0}
    if judged['form'] == 'EITHER_WAY' and judged['state'] in SETTLED:
        return {**base, 'points': [], 'words': [WORDS['nothing_open'].format(state=STATE_WORDS[judged['state']])], 'next': next_step([])}
    about = (judged['period']['clause'],);points = []
    open_ways = [w for w in judged['ways'] if w['state'] == UNDECIDED]
    if 'event' in judged['relevant']:
        who, kind = _who_of('RULE_READING', model_loaded)
        outcomes = tuple(Way(choices=(('event', w['choice']['event']),), state=w['state'], words='%s: %s' % (w['choice']['event'], w['words'])) for w in judged['ways'])
        settles = any(w['state'] in SETTLED for w in judged['ways'])
        points.append(OpenPoint(about=about, kind=kind, who=who, outcomes=outcomes, proof=judged['proof'], leaves=(Leaf(
            id='event', about=about, premise='RULE_READING', who=who, decisive=ALONE if settles else PAIR, values=tuple(sorted(w['choice']['event'] for w in judged['ways'])),
            words='which day %s' % judged['period']['event']),)))
    if open_ways and sheet:
        title = judged['receipt'].get('title') or ''
        earliest = min(w['event_day'] for w in open_ways)
        who, kind = _who_of('SHEET_COMPLETE', model_loaded)
        all_open = len(open_ways) == len(judged['ways'])
        points.append(OpenPoint(about=about, kind=kind, who=who, proof=judged['proof'], outcomes=(Way(choices=(('complete', 'yes'),), state=FAILS,
                      words='complete, with no credit of %s by the last day: does not hold' % judged['receipt']['amount']),), leaves=(Leaf(
            id='complete', about=(sheet,), premise='SHEET_COMPLETE', who=who, decisive=ALONE if all_open else PAIR, values=('yes', 'no'),
            words=WORDS['complete'].format(title=title, start=earliest)),)))
        who, kind = _who_of('NEW_READING', model_loaded)
        points.append(OpenPoint(about=about, kind=kind, who=who, proof=judged['proof'], outcomes=(Way(choices=(('credit', 'found'),), state=HOLDS,
                      words='a credit of %s by the last day: holds' % judged['receipt']['amount']),), leaves=(Leaf(
            id='credit', about=(sheet,), premise='NEW_READING', who=who, decisive=ALONE if all_open else PAIR, values=('found', 'not found'),
            words=WORDS['credit'].format(amount=judged['receipt']['amount'])),)))
    points = order(points)
    step = next_step(points, brain, model_loaded)
    return {**base, 'points': [p.as_record() for p in points], 'words': _lines(points, judged['state']), 'next': step, 'model_calls': step['model_calls']}


# =========================================================================================================================
# The operation
# =========================================================================================================================

def _fields():
    from .either_way import FIELDS as EITHER
    shape = dict(EITHER['field.either'][0])
    shape.pop('unknown', None)
    shape['accuracy'] = {'type': 'array', 'maxItems': 4, 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'amount'],
                         'properties': {'name': {'type': 'string', 'pattern': '^[a-z][a-z0-9_]{0,63}$'},
                                        'amount': {'type': 'string', 'pattern': '^[0-9]+(\\.[0-9]+)?(/[0-9]+)?$', 'maxLength': 60}}}}
    return {'field.settle': (shape, ['id'])}


FIELDS = _fields()
SCOPES = {op: 'read' for op in FIELDS}
OBSERVERS = tuple(FIELDS)


def settle(kernel, principal, args):
    from .either_way import args_of, goal_of
    ident = str(args['id']).strip()
    if ident.startswith('period:'):
        return _plain({'id': ident, **settle_period(kernel, principal, ident[7:].strip() or None, on=args.get('on'), sheet=args.get('sheet'),
                                             model_loaded=bool(args.get('model_loaded')))})
    goal, goal_id, named, desk = goal_of(kernel, principal, ident)
    choose, at, readings = args_of(args)
    return _plain({'id': ident, **settle_goal(kernel, principal, goal, choose=choose, readings=readings, at=at, accuracy=args.get('accuracy') or (), words=desk.words,
                                       said=desk.said, model_loaded=bool(args.get('model_loaded')), ident=goal_id, named=named)})


def dispatch(kernel, op, args, principal):
    from .office_service import owner
    owner(principal)                 # the sheets live in the owner's profile, as for office.get
    if op == 'field.settle':return settle(kernel, principal, args)
    raise ValueError('Unknown settle operation')
