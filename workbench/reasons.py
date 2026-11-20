"""Her reasons (0.8.6 S3, "Kas's mind, no model"): Why, Rests on and Without it, over the Field's own records.

Every card on the Field can be asked why it stands as it does. The answer is a short proof: what it needs, each premise
with its state word and where it came from, For and Against, and what it rests on. The graph is the Field's, not a second
one: each premise is a record already on the desk (a reviewed row of a sheet, a check the Kernel ran, a source admitted
here, your tolerance, your word), and the wires the proof lights are exactly the Field's wires between the proof's records.

  field.why      {id}                    read   the proof of one card ('claim:…', 'office:…', 'document:…', …) or of a goal
                                                ('goal:' and a kept goal's id or a candidate's key): its state, at most 12
                                                lines, its leaves, For and Against, the wires to light and the walk
  field.rests    {id}                    read   what the answer rests on that is not a reviewed reading (your tolerances,
                                                your word, her own defaults shown as "mine, not agreed"), each with what
                                                the answer is without it, and for a choice between revisions, with the
                                                other one
  field.without  {id, leaf, other?}      read   the answer without one of those, or with the other revision

The logic is four-valued, through stac/evidence.py (truth_and, negate, knowledge_join): a premise that is not settled
leaves the conclusion "cannot tell", never "does not hold"; two sides with support each give CONFLICT, and both are kept.
The proof is a finite graph in reason_graph's own shape (ATOM, ASSUMPTION and CLAIM nodes, positive and negative rules),
and paths() works out its support and refutation paths with its own code. reason_graph.compute is not called here and is
not edited (its hash is bound into lab results): it is the oracle a differential check compares paths() with.

What counts is worked out without her proposals. Where a choice between revisions is not yet yours, the answer that
counts is "cannot tell", and the answer under her proposal is said beside it: "It would hold if you agree that Rev B
applies." Nothing here writes a record; a proof is computed with a digest and never stored. No model is asked
(model_calls: 0), and nothing here imports one. Every number is an exact Fraction; no float.

Budgets (mind_types.BUDGET): a proof closure of more than 64 records or 128 rules is not worked out ("cannot tell", with
the one sentence for a partial answer); at most 12 lines are shown.
"""
from __future__ import annotations

import re
from fractions import Fraction
from itertools import product

from .mind_types import BUDGET, CONFLICT, FAILS, HOLDS, UNDECIDED
from .project_desk import digest

SUPPORTED, REFUTED, UNKNOWN = 'SUPPORTED', 'REFUTED', 'UNKNOWN'
JUDGED = {SUPPORTED: HOLDS, REFUTED: FAILS, UNKNOWN: UNDECIDED, 'CONFLICT': CONFLICT}
STATE_SAID = {SUPPORTED: 'holds', REFUTED: 'does not hold', UNKNOWN: 'cannot tell', 'CONFLICT': 'cannot tell: the records disagree'}
RELATION_WORDS = {'le': 'at most', 'lt': 'below', 'ge': 'at least', 'gt': 'above'}
LEAF_ROLES = ('row', 'tolerance', 'choice', 'check')        # what a proof's leaves are: premises you can look at or say
ASSUMED = 'Rows as reviewed on this desk, and the maths worked out exactly on them.'
PATH_COMBINATIONS = 4096                                     # reason_graph's own limits on one rule and on one node's paths
PATH_LIMIT = 256

FIELDS = {
    'field.why': ({'id': {'type': 'string', 'minLength': 1, 'maxLength': 200}}, ['id']),
    'field.rests': ({'id': {'type': 'string', 'minLength': 1, 'maxLength': 200}}, ['id']),
    'field.without': ({'id': {'type': 'string', 'minLength': 1, 'maxLength': 200}, 'leaf': {'type': 'string', 'pattern': '^[a-z][a-z0-9_]{0,39}$'},
                       'other': {'type': 'string', 'pattern': '^owner:[a-f0-9]{32}$'}}, ['id', 'leaf']),
}
SCOPES = {op: 'read' for op in FIELDS}
OBSERVERS = tuple(FIELDS)

# Her words here: fixed templates (design 3.6: no exclamation mark, no sentence over 30 words, a number with its record).
WORDS = {
    'heading_SUPPORTED': 'Holds. All of these are needed, and each holds.',
    'heading_REFUTED': 'Does not hold. All of these are needed, and one does not hold.',
    'heading_UNKNOWN': 'Cannot tell. All of these are needed, and one is not settled.',
    'heading_CONFLICT': 'Cannot tell: two readings cannot both be right. Both sides are kept.',
    'heading_evidence': '{state}. This is what the records say for it and against it.',
    'heading_trace': '{state}. It stands on what it was made from.',
    'heading_root': 'It comes from nothing else on the desk, so there is nothing for it to agree with.',
    'maths': '{label}: {state}{room} (the maths, receipt {receipt}).',
    'maths_waits': 'The maths waits for which revision applies.',
    'row': '{value}: {title}, row {row}, {where}.',
    'row_gone': 'Row {row} of {title} is no longer where it was.',
    'tolerance': 'Your {said} tolerance on {parameter} ({title}, row {row}).',
    'tolerance_recheck': 'Your tolerance on {parameter} is to recheck: its row changed, so it is not applied.',
    'choice_said': '{name} applies: your word.',
    'choice_asked': '{name} applies: as you asked here.',
    'choice_open': '{name} applies: not yet said by you; it is the revision marked CURRENT.',
    'choice_unmarked': 'Which revision applies is not yet said by you, and none is marked CURRENT.',
    'choice_named_open': '{name}: the finding names it; which revision applies is not yet said by you.',
    'choice_named_other': '{other} applies: your word; this finding speaks of {name}.',
    'check': '{note}: {outcome} (a check the Kernel ran).',
    'for_against': 'For it: {pro}. Against it: {con}.',
    'rests': 'Rests on: {parts}. Model calls: 0.',
    'would': 'It would {state} if you agree that {name} applies.',
    'change_fails': 'What would change it: a reading or a limit that moves it by more than {room}.',
    'change_holds': 'What would change it: a reading or a limit that uses up the {room} to spare.',
    'change_choice': 'What would settle it: your word on which revision applies.',
    'change_open': 'What would settle it: a new reading of a row it rests on.',
    'change_evidence': 'What would change it: evidence from another source, or a check run again.',
    'change_trace': 'What would change it: a change to what it was made from.',
    'trace': '{title}: {state}{by}.',
    'unset_holds': 'Judged at the reading itself: no tolerance is recorded for {parameter}. A tolerance {edge} would turn this to cannot tell.',
    'unset_fails': 'With no tolerance recorded for {parameter}, {room}. A tolerance {edge} would make it cannot tell.',
    'mine': 'mine, not agreed: {name} is marked current',
    'none': 'nothing',
}


# =========================================================================================================================
# The paths: the same support and refutation paths as reason_graph.compute, worked out by this module's own code
# =========================================================================================================================

def _closure(nodes, by, target):
    seen = [];stack = [target];found = set()
    while stack:
        name = stack.pop()
        if name in found:continue
        found.add(name);seen.append(name)
        for rule in by.get(name, ()):
            for premise in rule['premises']:stack.append(premise['id'])
    return found


def paths(graph, observations, budget=BUDGET):
    """The support and refutation paths of graph['target'] and its four-valued state, over a finite graph in reason_graph's
    shape: {'state' (UNKNOWN, SUPPORTED, REFUTED or CONFLICT), 'judged', 'target', 'paths': {'positive', 'negative'},
    'states', 'closure', 'reason_digest', 'complete', 'budget'}. A closure past the budget is not worked out: UNKNOWN with
    the budget sentence. The state never depends on how many paths were listed: it is the four-valued value itself."""
    from .stac.evidence import EvidenceSupport, knowledge_join, negate, truth_and
    nodes = {}
    for node in graph['nodes']:
        if node['id'] in nodes:raise ValueError('REASON_NODE_ID')
        nodes[node['id']] = node
    target = graph['target']
    if target not in nodes or nodes[target]['kind'] != 'CLAIM':raise ValueError('REASON_TARGET')
    by = {}
    for rule in graph['rules']:
        if rule['conclusion'] not in nodes or nodes[rule['conclusion']]['kind'] != 'CLAIM':raise ValueError('REASON_RULE_CONCLUSION')
        if any(premise['id'] not in nodes for premise in rule['premises']):raise ValueError('REASON_UNKNOWN_PREMISE')
        by.setdefault(rule['conclusion'], []).append(rule)
    closure = _closure(nodes, by, target)
    rules_in = sum(len(by.get(name, ())) for name in closure)
    if len(closure) > budget.proof_nodes or rules_in > budget.proof_rules:
        over_nodes = len(closure) > budget.proof_nodes
        tried, of = (budget.proof_nodes, len(closure)) if over_nodes else (budget.proof_rules, rules_in)
        sentence = budget.sentence(tried, of, 'the reasons past the first %d %s' % (tried, 'records' if over_nodes else 'rules'))
        none = {'positive': [], 'negative': []}
        return {'state': UNKNOWN, 'judged': UNDECIDED, 'target': target, 'paths': none, 'states': {}, 'closure': sorted(closure),
                'reason_digest': digest(none), 'complete': False, 'budget': (tried, of, sentence)}
    values = {};found = {};active = set();counts = {'listed': 0, 'combinations': 0, 'complete': True}

    def visit(name):
        if name in found:return
        if name in active:raise ValueError('REASON_UNSUPPORTED_CYCLE')
        active.add(name)
        node = nodes[name];positive = [];negative = []
        if node['kind'] == 'ASSUMPTION':
            value = EvidenceSupport(True, False);positive.append({'atoms': [], 'assumptions': [name], 'rules': []})
        elif node['kind'] == 'ATOM':
            seen = observations.get(name) or {}
            if seen.get('applicability') == 'CURRENT' and seen.get('state') == 'OBSERVED':
                agrees = seen.get('value') == node.get('expected')
                value = EvidenceSupport(agrees, not agrees)
                (positive if agrees else negative).append({'atoms': [name], 'assumptions': [], 'rules': []})
            else:value = EvidenceSupport()
        else:
            value = EvidenceSupport()
            for rule in by.get(name, ()):
                for premise in rule['premises']:visit(premise['id'])
                held = EvidenceSupport(True, False)
                for premise in rule['premises']:
                    said = values[premise['id']]
                    held = truth_and(held, said if premise['polarity'] == 'positive' else negate(said))
                fired = held.positive
                value = knowledge_join(value, EvidenceSupport(fired, False) if rule['polarity'] == 'positive' else EvidenceSupport(False, fired))
                if not fired:continue
                choices = [found[premise['id']][premise['polarity']] for premise in rule['premises']]
                many = 1
                for options in choices:many *= len(options)
                counts['combinations'] += many
                if many > PATH_COMBINATIONS:counts['complete'] = False;continue
                into = positive if rule['polarity'] == 'positive' else negative
                for combination in product(*choices):
                    path = {key: sorted(set(x for part in combination for x in part[key])) for key in ('atoms', 'assumptions', 'rules')}
                    path['rules'] = sorted(set(path['rules'] + [rule['id']]))
                    if path not in into:into.append(path)
                    if len(positive) + len(negative) > PATH_LIMIT:counts['complete'] = False;break
        positive.sort(key=digest);negative.sort(key=digest)
        values[name] = value;found[name] = {'positive': positive, 'negative': negative}
        active.discard(name)

    visit(target)
    state = values[target].state.value;listed = found[target]
    tried = len(listed['positive']) + len(listed['negative'])
    sentence = '' if counts['complete'] else budget.sentence(tried, counts['combinations'], 'the other ways these reasons combine; the state is exact')
    return {'state': state, 'judged': JUDGED[state], 'target': target, 'paths': listed, 'states': {n: values[n].state.value for n in sorted(closure)},
            'closure': sorted(closure), 'reason_digest': digest(listed), 'complete': counts['complete'],
            'budget': (tried, tried if counts['complete'] else counts['combinations'], sentence)}


def graph_digest(graph, observations):
    """The proof's digest: the graph and what was observed, in canonical JSON. Node ids, labels and receipts are made
    from the records' content, so the same records give the same digest in any build and any process."""
    return digest({'graph': graph, 'observations': {name: {k: seen.get(k) for k in ('state', 'applicability', 'value')} for name, seen in sorted(observations.items())}})


def route(edges):
    """The wires to light, each with its hop from the source end: a wire leaving a record no other wire of the proof feeds
    is hop 0. [{'source', 'target', 'hop'}], in hop order."""
    into = {}
    for source, target in edges:into.setdefault(target, []).append(source)
    depth = {}

    def deep(name, trail=()):
        if name in depth:return depth[name]
        if name in trail:return 0
        depth[name] = 0 if not into.get(name) else 1 + max(deep(s, trail + (name,)) for s in into[name])
        return depth[name]

    rows = [{'source': s, 'target': t, 'hop': deep(s)} for s, t in edges]
    return sorted(rows, key=lambda r: (r['hop'], r['source'], r['target']))


# =========================================================================================================================
# The desk, read once per question
# =========================================================================================================================

class _Desk:
    """What one question to her reasons reads: the Field, your words, your tolerances, the goals and the sheets, each read
    once. Reads only: Kernel reads that are observers, and the records' own read functions."""

    def __init__(self, kernel, principal):
        from . import tolerances, your_word
        from .field_source import read_field
        self.kernel, self.principal = kernel, principal
        self.field, _ = read_field(kernel, principal)
        self.words = your_word.standing(kernel, principal)
        self.said = tolerances.on_cells(kernel, principal)
        self._goals = None;self._saved = {};self._fresh = {};self._judged = {}

    def call(self, operation, arguments):
        answer = self.kernel.dispatch(operation, arguments, self.principal)
        if not answer.get('ok'):raise ValueError('%s could not be read: %s' % (operation, str((answer.get('error') or {}).get('message', ''))[:160]))
        return answer['result']

    def goals(self):
        """The relation goals on the desk: every candidate, with the id of the kept goal that has its key (if any)."""
        if self._goals is None:
            from . import goals
            kept = {g.get('key'): g for g in goals._records(self.kernel, self.principal) if g.get('state') == 'IN'}
            self._goals = [dict(kept[c['key']]) if c['key'] in kept else dict(c) for c in goals.candidates(self.kernel, self.principal)]
        return self._goals

    def goal(self, ref):
        if len(ref) == 32:
            from . import goals
            found = next((g for g in goals._records(self.kernel, self.principal) if g['id'] == ref), None)
        else:found = next((g for g in self.goals() if g.get('key') == ref), None)
        if found is None:raise ValueError('No goal on the desk has that id. goals.list and goals.candidates list them.')
        return found

    def saved(self, sheet):
        if sheet not in self._saved:
            from .office_service import store
            try:self._saved[sheet] = store().get(sheet)
            except (ValueError, OSError, KeyError):self._saved[sheet] = None
        return self._saved[sheet]

    def fresh(self, sheet):
        if sheet not in self._fresh:
            from . import goals
            saved = self.saved(sheet)
            self._fresh[sheet] = goals._freshness(self.kernel, self.principal, saved) if saved else 'MISSING'
        return self._fresh[sheet]

    def judge(self, goal, way, drop=(), stages=('check',)):
        """goals.judge under one way (an alternative ref, or None for a goal with no alternatives), with the tolerances in
        `drop` left out: (the answer of the first stage, the room (lo, hi) or None, its unit, every stage's answer)."""
        key = (goal.get('key') or goal.get('id'), way['sheet'] if way else '', tuple(sorted(drop)), tuple(stages))
        if key not in self._judged:
            from . import goals
            said = {k: v for k, v in self.said.items() if k not in set(drop)}
            judged = goals.judge(self.kernel, self.principal, goal, (way['sheet'],) if way else (), stages, said=said)
            row = judged['ways'][0];shape = judged['judgement']['ways'][0]
            room = tuple(Fraction(x) for x in shape['room']) if shape.get('room') else None
            self._judged[key] = (row['answers'][stages[0]], room, shape.get('unit') or '', row['answers'])
        return self._judged[key]


# =========================================================================================================================
# Building one proof
# =========================================================================================================================

def _receipt(value):
    return digest(value)[:32]


def _limit_symbol(goal):
    return next(iter((goal.get('alternatives') or {}).keys()), None)


def _alternatives(goal):
    from .your_word import _alternatives_of
    return _alternatives_of(goal)


def _name(ref, goal):
    from .your_word import short_name
    return short_name(ref['title'], [a['title'] for a in _alternatives(goal)])


def _quantity(record):
    return Fraction(record['rational']), record['unit']


def _span(pair):
    from .math_answers import span_words
    (lo, unit), (hi, _) = _quantity(pair[0]), _quantity(pair[1])
    return span_words(lo, hi, unit)


def room_words(room, unit, state):
    """The room as she says it: '5 ms over', '2 to 8 ms over', '1 W to spare', '15/16 to 17/16 W to spare'."""
    from .math_answers import span_words
    if room is None:return ''
    lo, hi = room
    if hi < 0:return '%s over' % span_words(-hi, -lo, unit)
    if lo >= 0 and state != FAILS:return '%s to spare' % span_words(lo, hi, unit)
    return 'from %s over to %s to spare' % (span_words(-lo, -lo, unit), span_words(hi, hi, unit))


def _goal_for(desk, text, evidence):
    """The relation goal a finding speaks of, or None: a check's row (its sheet and parameter) names the reading, or the
    goal's own name (what is compared) is in the finding's words. Two equally good goals: none (she does not guess)."""
    lowered = ' '.join(re.findall(r'[a-z0-9]+', text.lower()))
    checked = []
    for link in evidence:
        if link.get('kind') != 'CHECK':continue
        program = str(link.get('program') or '')
        sheet = re.search(r'@office:(owner:[a-f0-9]{32})', program);parameter = re.search(r'parameter=([^|]+)', program)
        if sheet and parameter:checked.append((sheet.group(1), parameter.group(1).strip().strip('"').lower()))
    scored = []
    for goal in desk.goals():
        roles = goal.get('roles') or {};score = 0
        measured = [ref for symbol, ref in goal['cells'].items() if roles.get(symbol) == 'measured']
        if any(ref['sheet'] == sheet and ref['parameter'].lower() == parameter for sheet, parameter in checked for ref in measured):score += 4
        stem = ' '.join(re.findall(r'[a-z0-9]+', goal['statement'].split(' is ')[0].lower()))
        if stem and re.search(r'\b%s\b' % re.escape(stem), lowered):score += 2
        if score:scored.append((score, goal))
    scored.sort(key=lambda pair: -pair[0])
    if not scored or (len(scored) > 1 and scored[0][0] == scored[1][0]):return None
    return scored[0][1]


def _named(goal, text):
    """The alternative a finding names by its own words ('the Rev B limit'), or None."""
    lowered = ' '.join(re.findall(r'[a-z0-9]+', text.lower()));hits = []
    for ref in _alternatives(goal):
        name = ' '.join(re.findall(r'[a-z0-9]+', _name(ref, goal).lower()))
        if name and re.search(r'\b%s\b' % re.escape(name), lowered):hits.append(ref)
    return hits[0] if len(hits) == 1 else None


class _Proof:
    """One proof as it is built: nodes and rules in reason_graph's shape, what was observed, and for each node its role,
    its words and the Field record it stands for."""

    def __init__(self, target, label):
        self.target = target
        self.nodes = [{'id': target, 'kind': 'CLAIM', 'label': label[:500] or 'This card'}]
        self.rules = [];self.observations = {};self.meta = {target: {'role': 'subject'}};self.n = {}

    def next_id(self, stem):
        self.n[stem] = self.n.get(stem, 0) + 1
        return stem if stem in ('choice', 'maths') else '%s%d' % (stem, self.n[stem])

    def atom(self, stem, label, receipt, seen, role, source='EXPERIMENT', **meta):
        ident = self.next_id(stem)
        node = {'id': ident, 'kind': 'ATOM', 'label': label[:500], 'source': source, 'receipt': receipt, 'expected': True}
        node.update({'index': 0} if source == 'MATH' else {'measurement': stem})
        self.nodes.append(node);self.observations[ident] = seen;self.meta[ident] = {'role': role, **meta}
        return ident

    def rule(self, stem, polarity, premises):
        self.rules.append({'id': self.next_id(stem), 'conclusion': self.target, 'polarity': polarity,
                           'premises': [{'id': name, 'polarity': way} for name, way in premises]})

    def graph(self):
        return {'nodes': self.nodes, 'rules': self.rules, 'target': self.target, 'assumptions': [ASSUMED], 'coverage': 'DECLARED_FINITE_GRAPH'}


def _seen(value=True, state='OBSERVED', applicability='CURRENT'):
    return {'state': state, 'applicability': applicability, 'value': value if state == 'OBSERVED' else None}


def _tolerance_said(t, unit):
    from .math_answers import figure
    lo, hi = Fraction(str(t['lo'])), Fraction(str(t['hi']))
    if t.get('said') == 'plus_minus':return '±%s' % figure((hi - lo) / 2, unit)
    return '%s to %s' % (figure(lo, ''), figure(hi, unit))


def _relation_part(desk, proof, goal, way, way_said, drop, choice_premise, choice_line):
    """Rows, tolerances, the choice and the maths of a relation goal under one way, added to `proof`; returns (the maths
    answer or None, room, unit, the premise names, the lines)."""
    from .tolerances import sheet_cell
    lines = [];premises = [];symbol = _limit_symbol(goal)
    bound = dict(goal['cells'])
    if symbol and way:bound[symbol] = way
    roles = goal.get('roles') or {}
    order = sorted(bound, key=lambda s: (roles.get(s) == 'limit', s))
    for name in order:
        if symbol and name == symbol and not way:continue
        ref = bound[name];saved = desk.saved(ref['sheet'])
        cell = sheet_cell(saved, ref['cell']) if saved else None
        row = int(ref['cell'][1:]);pdf = ((saved or {}).get('origin') or {}).get('pdf') or {}
        if not cell or cell['parameter'] != ref['parameter']:
            ident = proof.atom('row', 'Row %d of %s' % (row, ref['title']), _receipt([ref['title'], ref['cell'], 'gone']), _seen(state='MISSING', applicability='MISSING_SOURCE'),
                               'row', field='office:' + ref['sheet'], sheet=ref['sheet'], cell=ref['cell'], words=WORDS['row_gone'].format(row=row, title=ref['title']))
            premises.append((ident, 'positive'));lines.append((ident, proof.meta[ident]['words']));continue
        value = ('%s %s' % (cell['value'], cell['unit'])).strip()
        fresh = desk.fresh(ref['sheet'])
        seen = _seen() if fresh == 'CURRENT' else _seen(applicability='STALE')
        where = ('reviewed from page %d of %s' % (int(pdf.get('page_index', 0)) + 1, pdf.get('name'))) if pdf.get('name') else 'on the sheet'
        if fresh != 'CURRENT':where += '; its source changed, so it does not count until it is reviewed again'
        ident = proof.atom('row', '%s: %s, row %d' % (value, ref['title'], row), _receipt([ref['title'], ref['cell'], cell['parameter'], cell['value'], cell['unit']]), seen,
                           'row', field='office:' + ref['sheet'], sheet=ref['sheet'], cell=ref['cell'], parameter=cell['parameter'],
                           fingerprint=pdf.get('source_sha256', ''), pdf=pdf.get('name', ''), page=int(pdf.get('page_index', 0)) + 1,
                           words=WORDS['row'].format(value=value, title=ref['title'], row=row, where=where))
        premises.append((ident, 'positive'));lines.append((ident, proof.meta[ident]['words']))
        t = desk.said.get((ref['address'], ref['cell']))
        if t and (ref['address'], ref['cell']) not in set(drop):
            if t['state'] in ('APPLIES', 'CARRIED_OVER'):
                said = _tolerance_said(t, t.get('unit') or cell['unit'])
                tid = proof.atom('tol', 'Your %s tolerance on %s' % (said, cell['parameter']), _receipt([ref['title'], ref['cell'], t['lo'], t['hi']]), _seen(),
                                 'tolerance', field='office:' + ref['sheet'], sheet=ref['sheet'], cell=ref['cell'], parameter=cell['parameter'],
                                 key=[ref['address'], ref['cell']], said=said, tolerance=t['id'],
                                 words=WORDS['tolerance'].format(said=said, parameter=cell['parameter'], title=ref['title'], row=row))
                premises.append((tid, 'positive'));lines.append((tid, proof.meta[tid]['words']))
            else:lines.append((None, WORDS['tolerance_recheck'].format(parameter=cell['parameter'])))
    if symbol:
        cid = proof.atom('choice', choice_line[1], _receipt(['choice', way['title'] if way else '', way_said]), _seen() if way_said else _seen(state='NOT_SAID', applicability='NOT_ASSESSED'),
                         'choice', field=('office:' + way['sheet']) if way else '', sheet=way['sheet'] if way else '', words=choice_line[1], said=way_said,
                         how=choice_line[0], open=choice_line[0] in ('mine', 'open', 'named_open'), name=choice_line[2] if len(choice_line) > 2 else '')
        if choice_premise:premises.append((cid, 'positive'))
        lines.append((cid, choice_line[1]))
    answer = room = None;unit = ''
    if symbol and not way:
        mid = proof.atom('maths', 'The maths waits for which revision applies', _receipt(['maths', goal['expression'], 'waits']), _seen(state='WAITS_FOR_CHOICE', applicability='NOT_ASSESSED'),
                         'maths', words=WORDS['maths_waits'])
        lines.insert(0, (mid, WORDS['maths_waits']))
    else:
        answer, room, unit, _ = desk.judge(goal, way, drop)
        result = answer.get('result') or {}
        if result.get('left') and result.get('right'):
            label = '%s is %s %s' % (_span(result['left']), RELATION_WORDS.get(goal['relation'], 'at most'), _span(result['right']))
        else:label = goal['statement']
        state = answer['state']
        if state in (HOLDS, FAILS):seen = _seen(state == HOLDS, applicability='CURRENT' if answer.get('freshness') == 'CURRENT' else 'STALE')
        else:seen = _seen(state=str(state), applicability='CURRENT')
        receipt = _receipt({'state': state, 'result': result})
        said_state = {HOLDS: 'holds', FAILS: 'does not hold', UNDECIDED: 'cannot tell'}.get(state, (answer.get('words') or {}).get('answer', str(state)).rstrip('.'))
        rw = room_words(room, unit, state)
        words = WORDS['maths'].format(label=label, state=said_state, room=(', ' + rw) if rw else '', receipt=receipt[:12])
        mid = proof.atom('maths', label, receipt, seen, 'maths', source='MATH', words=words, answer=answer.get('digest', ''), via=goal.get('via') or '',
                         state=state, room=[str(room[0]), str(room[1])] if room else None, unit=unit)
        lines.insert(0, (mid, words))
    proof.rule('by_the_maths', 'positive', premises + [(mid, 'positive')])
    proof.rule('against_by_the_maths', 'negative', premises + [(mid, 'negative')])
    return answer, room, unit, lines


def _choice(desk, goal, ident, key, view):
    """(the way to read the limit, whether the choice counts as said, (how, its line), her proposal, your word) for a view:
    'counted' (your word only), 'proposed' (your word, else her proposal), ('other', sheet), or 'without' (no choice)."""
    from .your_word import choice_for, marked_current
    options = _alternatives(goal)
    if not options:return None, True, ('none', '', ''), None, None
    word_way, word = choice_for(desk.words, goal, ident, key)
    proposal = marked_current(options)
    if isinstance(view, tuple):
        way = next((a for a in options if a['sheet'] == view[1]), None)
        if way is None:raise ValueError('That sheet is not one of the revisions this reads.')
        return way, True, ('asked', WORDS['choice_asked'].format(name=_name(way, goal)), _name(way, goal)), proposal, word
    if word_way and view != 'without':
        return word_way, True, ('word', WORDS['choice_said'].format(name=_name(word_way, goal)), _name(word_way, goal)), proposal, word
    way = word_way or proposal
    line = WORDS['choice_open'].format(name=_name(way, goal)) if way else WORDS['choice_unmarked']
    return way, view == 'proposed' and way is not None, ('mine' if way else 'open', line, _name(way, goal) if way else ''), proposal, word


def _assess(desk, subject, view='counted', drop=()):
    """One proof of a subject under a view: {'graph', 'observations', 'meta', 'lines', 'answer', 'room', 'unit', 'paths',
    'digest', 'objects' (its Field records), 'evidence' (For and Against)}."""
    kind = subject['kind']
    proof = _Proof('subject', subject['label'])
    lines = [];answer = room = None;unit = '';objects = set();pro = [];con = []
    goal = subject.get('goal')
    if kind in ('goal', 'claim') and goal is not None:
        named = subject.get('named')
        if named:
            from .your_word import choice_for, marked_current
            word_way, _ = choice_for(desk.words, goal, subject.get('goal_id', ''), goal.get('key', ''))
            way, choice_premise = named, False
            way_said = bool(word_way) and word_way['sheet'] == named['sheet']
            name = _name(named, goal)
            if word_way and word_way['sheet'] == named['sheet']:how = ('word', WORDS['choice_said'].format(name=name), name)
            elif word_way:how = ('word', WORDS['choice_named_other'].format(other=_name(word_way, goal), name=name), name)
            elif (marked_current(_alternatives(goal)) or {}).get('sheet') == named['sheet']:how = ('named_open', WORDS['choice_open'].format(name=name), name)
            else:how = ('named_open', WORDS['choice_named_open'].format(name=name), name)
        else:
            way, way_said, how, _, _ = _choice(desk, goal, subject.get('goal_id', ''), goal.get('key', ''), view)
            choice_premise = True
        answer, room, unit, part = _relation_part(desk, proof, goal, way, way_said, drop, choice_premise, how)
        lines.extend(part)
        if goal.get('via'):objects.add('document:' + goal['via'])
    if kind == 'claim':
        for link in subject['evidence']:
            counts = link.get('counts', True) is not False
            supports = link.get('direction') == 'SUPPORTS'
            if link.get('kind') == 'CHECK':
                outcome = str(link.get('outcome') or '').upper()
                said = {'PASSED': 'held', 'CHECK_FAILED': 'did not hold'}.get(outcome, outcome.lower().replace('_', ' ') or 'not run')
                note = str(link.get('note') or 'A check').strip()
                seen = _seen(outcome == 'PASSED', applicability='CURRENT' if counts else 'STALE')
                inputs = sorted((link.get('inputs') or {}).keys())
                ident = proof.atom('check', note, _receipt([note, outcome]), seen, 'check', field=inputs[0] if inputs else '', inputs=inputs,
                                   direction=link.get('direction'), counts=counts, words=WORDS['check'].format(note=note, outcome=said))
                proof.rule('check', 'positive' if supports else 'negative', [(ident, 'positive' if supports else 'negative')])
                lines.append((ident, proof.meta[ident]['words']));objects.update(inputs)
            else:
                address = str(link.get('address') or '').lstrip('@');obj = desk.field.get(address)
                title = obj.title if obj else address;sha = ((obj.target or {}).get('sha256') if obj and isinstance(obj.target, dict) else '') or ''
                ident = proof.atom('source', '%s %s it' % (title, 'supports' if supports else 'speaks against'), _receipt([title, sha, link.get('direction')]),
                                   _seen(supports, applicability='CURRENT' if counts else 'STALE'), 'source', field=address, title=title,
                                   fingerprint=sha, independence=link.get('independence', ''), direction=link.get('direction'), counts=counts)
                proof.rule('source', 'positive' if supports else 'negative', [(ident, 'positive' if supports else 'negative')])
                (pro if supports else con).append(ident);objects.add(address)
    if kind == 'trace':
        for row in subject['upstream']:
            ok = row['stale'] != 'yes' and row['state'] in ('', 'current', 'admitted source')
            ident = proof.atom('made', row['title'], _receipt([row['kind'], row['title'], row['state']]), _seen(True, applicability='CURRENT' if ok else 'STALE'),
                               'made', field=row['id'], words=WORDS['trace'].format(title=row['title'], state=row['state'] or 'current',
                                                                                   by=(' (%s)' % row['by']) if row['by'] else ''))
            lines.append((ident, proof.meta[ident]['words']));objects.add(row['id'])
        made = [name for name, meta in proof.meta.items() if meta.get('role') == 'made']
        if made:proof.rule('made_from', 'positive', [(name, 'positive') for name in made])
    for name, meta in proof.meta.items():
        if meta.get('field'):objects.add(meta['field'])
        if meta.get('role') == 'row':      # the source the row was reviewed from, when it is admitted here
            for link in desk.field.fed_by('office:' + meta['sheet']):
                if link.source.startswith('intake:'):objects.add(link.source)
    graph = proof.graph();worked = paths(graph, proof.observations)
    return {'graph': graph, 'observations': proof.observations, 'meta': proof.meta, 'lines': lines, 'answer': answer, 'room': room, 'unit': unit,
            'paths': worked, 'digest': graph_digest(graph, proof.observations), 'objects': objects, 'for': pro, 'against': con}


def _subject(desk, ident):
    """What is asked about: a goal ('goal:' and its id or key), a finding on the Field, or any other card (its trace)."""
    ident = str(ident).strip()
    if ident.startswith('goal:'):
        goal = desk.goal(ident[5:])
        return {'kind': 'goal', 'id': ident, 'label': goal['statement'], 'goal': goal, 'goal_id': goal.get('id', '') if len(goal.get('id', '')) == 32 else '', 'field': ''}
    obj = desk.field.get(ident)
    if obj is None:raise ValueError('Nothing on the desk has the id %s. field.read lists the ids.' % ident[:80])
    if ident.startswith('claim:') and obj.kind in ('finding', 'question'):
        path = desk.call('investigation.path', {'claim': ident.split(':', 1)[1]})
        evidence = list(path.get('path') or ())
        goal = _goal_for(desk, obj.title, evidence) if obj.kind == 'finding' else None
        named = _named(goal, obj.title) if goal else None
        return {'kind': 'claim', 'id': ident, 'label': obj.title, 'goal': goal, 'goal_id': (goal or {}).get('id', '') if len((goal or {}).get('id', '')) == 32 else '',
                'named': named, 'evidence': evidence, 'field': ident, 'evidence_state': path.get('evidence_state')}
    rows = []
    for link in desk.field.fed_by(ident):
        up = desk.field.get(link.source)
        if up is not None:rows.append({'id': up.id, 'kind': up.kind, 'title': up.title, 'state': up.state, 'by': link.label, 'stale': 'yes' if link.stale else 'no'})
    return {'kind': 'trace', 'id': ident, 'label': obj.title, 'upstream': rows, 'field': ident, 'state': obj.state}


def _wires(desk, subject, worked):
    """The Field's own wires between the proof's records (and the card itself): the edges the proof lights."""
    ids = set(worked['objects']) | ({subject['field']} if subject.get('field') else set())
    ids = {i for i in ids if i and desk.field.get(i) is not None}
    return sorted({(link.source, link.target) for link in desk.field.links if link.source in ids and link.target in ids})


def _leaf_state(worked, name):
    """A premise's own state: what was observed of it (an atom does not depend on the rest of the proof)."""
    if name in worked['paths']['states']:return worked['paths']['states'][name]
    seen = worked['observations'].get(name) or {}
    if seen.get('state') == 'OBSERVED' and seen.get('applicability') == 'CURRENT':return SUPPORTED if seen.get('value') is True else REFUTED
    return UNKNOWN


def _line_state(worked, leaf):
    """The state word a proof line carries, by what the premise is."""
    m = worked['meta'].get(leaf) or {};st = _leaf_state(worked, leaf);role = m.get('role')
    if role == 'row':return 'reviewed' if st == SUPPORTED else 'not counted'
    if role == 'tolerance':return 'yours'
    if role == 'choice':return 'yours to say' if m.get('open') else ('your word' if m.get('how') == 'word' else 'as asked here')
    if role == 'check':return {SUPPORTED: 'held', REFUTED: 'did not hold'}.get(st, 'not counted')
    if role == 'made':return 'agrees' if st == SUPPORTED else 'to recheck'
    return STATE_SAID[st]


def _rests_parts(meta, choice_open):
    rows = sum(1 for m in meta.values() if m.get('role') == 'row')
    tols = sum(1 for m in meta.values() if m.get('role') == 'tolerance')
    words = sum(1 for m in meta.values() if m.get('role') == 'choice' and m.get('how') == 'word')
    parts = []
    if rows:parts.append('%d reviewed row%s' % (rows, '' if rows == 1 else 's'))
    if tols:parts.append('%d tolerance%s of yours' % (tols, '' if tols == 1 else 's'))
    if words:parts.append('your word on which revision applies')
    if choice_open:parts.append('1 choice still yours to make')
    return ', '.join(parts) or 'nothing but what is shown'


def why(kernel, principal, ident):
    """The proof of one card or goal (see the module's words). Reads only."""
    desk = _Desk(kernel, principal);subject = _subject(desk, ident)
    worked = _assess(desk, subject, 'counted')
    state = worked['paths']['state'];meta = worked['meta']
    lines = []
    if subject['kind'] == 'trace':heading = WORDS['heading_trace'].format(state=STATE_SAID[state].capitalize()) if subject['upstream'] else WORDS['heading_root']
    elif subject['kind'] == 'claim' and not subject.get('goal'):heading = WORDS['heading_evidence'].format(state=STATE_SAID[state].capitalize())
    else:heading = WORDS['heading_' + state]
    lines.append({'text': heading, 'state': STATE_SAID[state], 'from': '', 'field': subject.get('field', ''), 'leaf': ''})
    for leaf, text in worked['lines']:
        m = meta.get(leaf) or {}
        lines.append({'text': text, 'state': _line_state(worked, leaf) if leaf else '', 'from': m.get('role', ''), 'field': m.get('field', ''), 'leaf': leaf or ''})
    pro = [meta[n] for n in worked['for'] if meta[n]['counts']];con = [meta[n] for n in worked['against'] if meta[n]['counts']]
    n_pro = len({m['independence'] for m in pro});n_con = len({m['independence'] for m in con})

    def said(rows, n):
        if not rows:return WORDS['none']
        names = sorted({m['title'] for m in rows})
        return '%s (%s independent source%s)' % (', '.join(names), 'one' if n == 1 else str(n), '' if n == 1 else 's')
    if subject['kind'] == 'claim':
        lines.append({'text': WORDS['for_against'].format(pro=said(pro, n_pro), con=said(con, n_con)), 'state': '', 'from': 'evidence', 'field': '', 'leaf': ''})
    choice = next((m for m in meta.values() if m.get('role') == 'choice'), None)
    choice_open = bool(choice) and bool(choice.get('open'))
    if subject['kind'] != 'trace':
        lines.append({'text': WORDS['rests'].format(parts=_rests_parts(meta, choice_open)), 'state': '', 'from': 'rests', 'field': '', 'leaf': ''})
    if subject.get('goal') is not None and not subject.get('named') and choice and choice.get('how') == 'mine':
        proposed = _assess(desk, subject, 'proposed')
        if proposed['paths']['state'] != state and proposed['paths']['state'] in (SUPPORTED, REFUTED):
            name = choice.get('name') or 'that revision'
            lines.append({'text': WORDS['would'].format(state='hold' if proposed['paths']['state'] == SUPPORTED else 'not hold', name=name),
                          'state': STATE_SAID[proposed['paths']['state']], 'from': WORDS['mine'].format(name=name), 'field': '', 'leaf': 'choice'})
    lines.append({'text': _change(subject, worked, state, choice_open), 'state': '', 'from': 'change', 'field': '', 'leaf': ''})
    shown = lines
    if len(lines) > BUDGET.proof_lines:
        shown = lines[:BUDGET.proof_lines - 1] + [{'text': BUDGET.sentence(BUDGET.proof_lines - 1, len(lines), 'the other lines, which Rests on lists'),
                                                   'state': '', 'from': 'budget', 'field': '', 'leaf': ''}]
    edges = _wires(desk, subject, worked)
    leaves = [{'leaf': name, 'role': m['role'], 'words': m.get('words', ''), 'field': m.get('field', ''), 'sheet': m.get('sheet', ''), 'cell': m.get('cell', ''),
               'fingerprint': m.get('fingerprint', ''), 'source': m.get('pdf', ''), 'state': STATE_SAID[_leaf_state(worked, name)]}
              for name, m in meta.items() if m.get('role') in LEAF_ROLES]
    admitted = {(o.target or {}).get('sha256') for o in desk.field.objects if o.kind == 'source' and isinstance(o.target, dict)}
    slack = None
    maths = meta.get('maths') or {}
    if maths.get('room'):slack = {'lo': maths['room'][0], 'hi': maths['room'][1], 'unit': maths.get('unit', '')}
    hop = route(edges)
    walk = []
    for wire in hop:
        for end in (wire['source'], wire['target']):
            if end not in walk and end != subject.get('field'):walk.append(end)
    if subject.get('field'):walk.append(subject['field'])
    return {'id': subject['id'], 'statement': subject['label'], 'kind': subject['kind'], 'state': state, 'judged': JUDGED[state], 'words': heading,
            'lines': shown, 'leaves': leaves, 'slack': slack,
            'for': [{'title': m['title'], 'field': m['field'], 'independence': m['independence']} for m in pro],
            'against': [{'title': m['title'], 'field': m['field'], 'independence': m['independence']} for m in con],
            'independent': {'for': n_pro, 'against': n_con},
            'sources': [{'source': l['source'], 'fingerprint': l['fingerprint'], 'admitted': l['fingerprint'] in admitted} for l in leaves if l['role'] == 'row'],
            'edges': [{'source': s, 'target': t} for s, t in edges], 'route': hop, 'walk': walk,
            'graph': worked['graph'], 'observations': worked['observations'], 'paths': worked['paths'], 'digest': worked['digest'],
            'budget': worked['paths']['budget'], 'model_calls': 0}


def _change(subject, worked, state, choice_open):
    """The last line: what would change the conclusion."""
    if subject['kind'] == 'trace':return WORDS['change_trace']
    maths = worked['meta'].get('maths') or {}
    if state == UNKNOWN and choice_open and subject.get('goal') is not None and not subject.get('named'):return WORDS['change_choice']
    rw = room_words(worked['room'], worked['unit'], maths.get('state')) if worked.get('room') else ''
    if maths.get('state') == FAILS and rw:return WORDS['change_fails'].format(room=rw.replace(' over', ''))
    if maths.get('state') == HOLDS and rw:return WORDS['change_holds'].format(room=rw.replace(' to spare', ''))
    if subject.get('goal') is None:return WORDS['change_evidence']
    return WORDS['change_open']


def _outcome(worked):
    st = worked['paths']['state']
    rw = room_words(worked['room'], worked['unit'], (worked['meta'].get('maths') or {}).get('state')) if worked.get('room') and st in (SUPPORTED, REFUTED) else ''
    return {'state': st, 'judged': JUDGED[st], 'room': [str(worked['room'][0]), str(worked['room'][1])] if worked.get('room') and st in (SUPPORTED, REFUTED) else None,
            'unit': worked['unit'] if st in (SUPPORTED, REFUTED) else '', 'words': STATE_SAID[st] + ((', ' + rw) if rw else ''), 'digest': worked['digest']}


def _unset(desk, subject, way, drop):
    """One plain sentence for each measured row with no tolerance of yours, with the tolerance that would turn it."""
    from .math_answers import figure
    from .tolerances import sheet_cell
    goal = subject.get('goal')
    if goal is None:return []
    try:_, room, unit, every = desk.judge(goal, way, drop, stages=('check', 'settle'))
    except (ValueError, KeyError, TypeError):return []
    settle = every.get('settle') or {};check = every.get('check') or {}
    if check.get('state') not in (HOLDS, FAILS):return []
    rows = {row['name']: row for row in ((settle.get('result') or {}).get('break_even') or ())}
    out = [];roles = goal.get('roles') or {}
    for symbol, ref in sorted(goal['cells'].items()):
        if roles.get(symbol) != 'measured' or (ref['address'], ref['cell']) in desk.said:continue
        row = rows.get(symbol)
        if not row or not row.get('tolerance'):continue
        size = Fraction(row['tolerance']['rational'])
        saved = desk.saved(ref['sheet'])
        cell = sheet_cell(saved, ref['cell']) if saved else None
        unit_here = (cell or {}).get('unit') or ''
        edge = ('larger than %s' if row.get('closed') else 'of %s or more') % figure(size, unit_here)
        if check['state'] == HOLDS:out.append(WORDS['unset_holds'].format(parameter=ref['parameter'].lower(), edge=edge))
        else:out.append(WORDS['unset_fails'].format(parameter=ref['parameter'].lower(), room=room_words(room, unit, FAILS), edge=edge))
    return out


def rests(kernel, principal, ident):
    """What the answer rests on that is not a reviewed reading, each with the answer without it (and, for a choice between
    revisions, with the other one). The answer that counts is worked out without her proposals."""
    from .your_word import marked_current
    desk = _Desk(kernel, principal);subject = _subject(desk, ident)
    counted = _assess(desk, subject, 'counted');proposed = _assess(desk, subject, 'proposed')
    meta = proposed['meta'];items = []
    choice = meta.get('choice')
    goal = subject.get('goal')
    if choice is not None and goal is not None:
        mine = choice.get('how') in ('mine', 'named_open') and (marked_current(_alternatives(goal)) or {}).get('sheet') == choice.get('sheet')
        name = choice.get('name') or ''
        item = {'leaf': 'choice', 'what': 'choice', 'words': choice['words'], 'whose': WORDS['mine'].format(name=name) if mine else ('yours' if choice.get('how') == 'word' else 'still yours to say'),
                'decides': not subject.get('named')}
        if not subject.get('named'):
            item['without'] = _outcome(_assess(desk, subject, 'without'))
            item['with_other'] = []
            for ref in _alternatives(goal):
                if ref['sheet'] == choice.get('sheet'):continue
                other = _assess(desk, subject, ('other', ref['sheet']))
                item['with_other'].append({'sheet': ref['sheet'], 'title': ref['title'], 'name': _name(ref, goal), **_outcome(other)})
        items.append(item)
    for name, m in sorted(meta.items()):
        if m.get('role') != 'tolerance':continue
        without = _assess(desk, subject, 'proposed', drop=(tuple(m['key']),))
        items.append({'leaf': name, 'what': 'tolerance', 'words': m['words'], 'whose': 'yours', 'decides': True, 'without': _outcome(without)})
    way = None
    if goal is not None:
        way = subject.get('named') or _choice(desk, goal, subject.get('goal_id', ''), goal.get('key', ''), 'proposed')[0]
    return {'id': subject['id'], 'statement': subject['label'], 'state': counted['paths']['state'], 'judged': JUDGED[counted['paths']['state']],
            'counted': _outcome(counted), 'proposed': _outcome(proposed) if proposed['digest'] != counted['digest'] else None,
            'rests_on': items, 'unset': _unset(desk, subject, way, ()) if goal is not None else [], 'model_calls': 0}


def without(kernel, principal, ident, leaf, other=None):
    """The answer without one premise it rests on, or with the other revision ({leaf: 'choice', other: sheet})."""
    desk = _Desk(kernel, principal);subject = _subject(desk, ident)
    base = _assess(desk, subject, 'proposed')
    if leaf == 'choice':
        if (base['meta'].get('choice') is None) or subject.get('goal') is None:raise ValueError('This answer rests on no choice between revisions.')
        if subject.get('named'):raise ValueError('The finding names its revision; which applies on the desk does not change what it says.')
        worked = _assess(desk, subject, ('other', other) if other else 'without')
    else:
        m = base['meta'].get(leaf)
        if not m or m.get('role') != 'tolerance':raise ValueError('That is not something this answer rests on. field.rests lists them.')
        if other:raise ValueError('"other" goes with the choice between revisions only.')
        worked = _assess(desk, subject, 'proposed', drop=(tuple(m['key']),))
    out = _outcome(worked)
    return {'id': subject['id'], 'leaf': leaf, 'other': other or '', **out, 'changes': worked['paths']['state'] != base['paths']['state'], 'model_calls': 0}


def dispatch(kernel, op, args, principal):
    from .office_service import owner
    owner(principal)                 # the sheets live in the owner's profile, as for office.get
    if op == 'field.why':return why(kernel, principal, args['id'])
    if op == 'field.rests':return rests(kernel, principal, args['id'])
    if op == 'field.without':return without(kernel, principal, args['id'], args['leaf'], args.get('other'))
    raise ValueError('Unknown reasons operation')
