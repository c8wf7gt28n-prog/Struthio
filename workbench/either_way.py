"""Either way (0.8.6 S5, "Kas's mind, no model"): every sensible reading the desk knows of, worked out exactly, and what
they say together.

When a question can be read more than one way on the desk (which revision's limit applies, which row your words meant,
which event started a period), she works out every way exactly, with the 0.8.5 maths, and says one of four things:

  EITHER_WAY      "holds either way", "does not hold either way" (or "cannot tell either way"): every way agrees.
  DEPENDS_ON_ONE  "It depends on one thing: ...": one choice matters and each of its values settles it. The result of each
                  value is under its own button: the question (a mind_types.OpenPoint) carries one outcome per value.
  EXCEPT          "Holds, except in one case: ..." (or "Does not hold, except ..."): every way agrees but one group of
                  choices, named by the smallest group under which the answer differs.
  DEPENDS         more than one choice matters: the groups under which each answer stands.

Outside the four: CONFLICT, when a way's own records disagree (it is reported first and never combined with the others),
and TOO_MANY, when there are more ways than the budget (mind_types.BUDGET.ways, 64): nothing is combined, the state is
"cannot tell" and the one sentence for a partial answer says what was not reached. She also says which choices do not
matter. Every sentence says "under every reading the desk knows of", never "in every case".

The core is pure: combine(choices, ways) takes the ways' outcomes and gives the state, the form, the relevant and the
irrelevant choices and the groups (the smallest partial choices under which one answer stands, at most BUDGET.groups of
them examined). The ways' common state is the Belnap knowledge meet of their states (stac/evidence.knowledge_meet); two
ways agree when their state and their compared value are equal (for a "how far may it go", the exact end).

On the desk:

  field.either  {id, choose?, at?, reading?, unknown?, on?, model_loaded?}   read
      id 'goal:' and a goal's id or key, or a finding ('claim:…') that speaks of a goal: the goal judged under every way.
         Your word picks the revision when you have said one (a choice for this goal, for this desk, or the standing word
         "the current revision applies"); the receipt then names the word. choose: the revision asked here. at: an input
         taken at a value asked here ("can the rail settle at 340 mA?"), exactly, without its tolerance. reading: another
         row a symbol could read (a reading choice: which row your words meant). unknown: a symbol, to compare how far it
         may go before the goal stops holding instead of the state.
      id 'period:' and a clause ('period:§ 12(a)'): the last day of a period on the admitted papers, for each event that
         could have started it, and whether a payment was made by then: on a date asked here (on), or as the ledger sheet
         shows it (a credit of the amount the papers name), counting as "does not hold" only where your word says the
         sheet is complete.

Kasandra writes nothing here: it is a read, and her proposals are never records. No model is asked (model_calls: 0) and
none is imported. Every number is an exact Fraction or an int; no float.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from itertools import product

from .mind_types import (BUDGET, CONFLICT, DEPENDS, FAILS, HOLDS, UNDECIDED, Judgement, Leaf, OpenPoint, Way, ALONE, STATE_WORDS,
                         _plain, who as _who)
from .project_desk import digest

FORMS = ('EITHER_WAY', 'DEPENDS_ON_ONE', 'EXCEPT', 'DEPENDS', 'CONFLICT', 'TOO_MANY')
SETTLED = (HOLDS, FAILS)
RANK = {CONFLICT: 0, FAILS: 1, UNDECIDED: 2, HOLDS: 3}

# Her words for either way: fixed templates (design 3.6: plain, calm, no exclamation mark, at most 30 words a sentence).
WORDS = {
    'either_HOLDS': '{subject} holds either way, under every reading the desk knows of: {ways}.',
    'either_FAILS': '{subject} does not hold either way, under every reading the desk knows of: {ways}.',
    'either_UNDECIDED': 'Cannot tell, under every reading the desk knows of: {ways}.',
    'either_value': '{subject} comes to the same under every reading the desk knows of: {value}.',
    'one': '{subject} depends on one thing: {choice}.',
    'except_HOLDS': '{subject} holds, except in one case: {group}. There it {state}.',
    'except_FAILS': '{subject} does not hold, except in one case: {group}. There it {state}.',
    'depends': '{subject} depends on {n} things: {choices}.',
    'stands': 'Under {group}: {outcome}.',
    'conflict': 'Cannot tell under {group}: two readings cannot both be right. That way is shown first and is not combined with the others.',
    'too_many': 'There are {of} ways to read this, more than the {ways} I work out for one question, so I have combined none of them.',
    'not_matter': 'What does not matter here: {choices}.',
    'nobody': 'No one was asked.',
    'button': '{value} applies: {outcome}',
    'way': '{value}: {outcome}',
    'word': 'Your word decides {choice}: {statement}.',
    'asked': 'As asked here: {value}.',
    'named': 'The finding names {value}, so that is the revision read.',
    'at': '{name} taken at {value}, as asked here, without a tolerance.',
    'room_over': '{state}, {over} over',
    'undecided_over': 'cannot tell: {left} against {right}; at {witness} it would not hold',
    'last_day': 'the last day is {day}',
    'paid_on': 'paid on {day}',
    'credit_found': 'a credit of {amount} on {day}, by the last day',
    'credit_complete': 'no credit of {amount} by the last day, on your word that “{title}” is complete',
    'credit_unknown': 'nothing on “{title}” shows a credit of {amount} by the last day',
}


# =========================================================================================================================
# The core: ways combined (pure)
# =========================================================================================================================

@dataclass(frozen=True)
class Choice:
    """One open choice: its name, its values as they are said, the sort of premise it is (a key of mind_types.WHO_ANSWERS,
    which says who settles it) and the words that name it ("which revision applies")."""
    name: str
    values: tuple
    premise: str = 'REVISION'
    words: str = ''

    def as_record(self):return {'name': self.name, 'values': list(self.values), 'premise': self.premise, 'words': self.words}


def _support(state):
    from .stac.evidence import EvidenceSupport
    return {HOLDS: EvidenceSupport(True, False), FAILS: EvidenceSupport(False, True), CONFLICT: EvidenceSupport(True, True)}.get(state, EvidenceSupport())


def _state_of(support):
    return {(True, False): HOLDS, (False, True): FAILS, (True, True): CONFLICT}.get((support.positive, support.negative), UNDECIDED)


def meet(states):
    """The ways' common state: the Belnap knowledge meet of their states (what every way supports)."""
    from .stac.evidence import knowledge_meet
    states = list(states)
    if not states:return UNDECIDED
    found = _support(states[0])
    for state in states[1:]:found = knowledge_meet(found, _support(state))
    return _state_of(found)


def every_way(choices, budget=BUDGET):
    """Every way the choices can be taken, as [{name: value}], or None when there are more than budget.ways; and how many."""
    choices = sorted(choices, key=lambda c: c.name)
    count = 1
    for c in choices:count *= max(1, len(c.values))
    if count > budget.ways:return None, count
    return [dict(zip([c.name for c in choices], picked)) for picked in product(*[c.values for c in choices])], count


def _key(way):
    return (way['state'], way.get('value'))


def _fixed(group):
    return tuple(sorted(group.items()))


def _canon(value):
    return str(value)


def _groups(names, domains, ways, budget):
    """The smallest partial choices under which one answer stands: {outcome key: [group]}, each group a sorted tuple of
    (name, value). Cubes are examined fewest choices first, at most budget.groups of them; a way no examined group
    covers keeps its whole choice as its group. (groups, examined, of)."""
    cubes = [()]
    for name in names:cubes = [c + ((name, v),) for c in cubes for v in (None,) + domains[name]]
    cubes = [tuple((n, v) for n, v in c if v is not None) for c in cubes]
    cubes.sort(key=lambda c: (len(c), [(n, _canon(v)) for n, v in c]))
    of = len(cubes);found = {}
    for cube in cubes[:budget.groups]:
        matched = [w for w in ways if all(w['choice'].get(n) == v for n, v in cube)]
        if not matched:continue
        keys = {_key(w) for w in matched}
        if len(keys) != 1:continue
        key = keys.pop();have = found.setdefault(key, [])
        if any(set(g) <= set(cube) for g in have):continue
        have.append(cube)
    for w in ways:                                  # past the budget: a way keeps its whole choice
        key = _key(w);have = found.setdefault(key, [])
        if not any(all(w['choice'].get(n) == v for n, v in g) for g in have):have.append(_fixed(w['choice']))
    return found, min(of, budget.groups), of


def combine(choices, ways, budget=BUDGET):
    """The ways' outcomes said together. choices: [Choice]; ways: [{'choice': {name: value}, 'state', 'value'?, ...}] (one
    per way, normally every way). {'state' (the common state, DEPENDS, CONFLICT, or UNDECIDED when there are too many),
    'form' (FORMS), 'choices', 'relevant', 'irrelevant', 'groups': [{'state', 'value', 'groups': [[(name, value)]]}],
    'except': the one group of an EXCEPT, 'conflict': the ways whose records disagree, 'ways' (conflict first, then in
    the canonical order), 'budget': (tried, of, sentence)}. The order the choices or the ways come in changes nothing."""
    choices = sorted(choices, key=lambda c: c.name);names = [c.name for c in choices]
    domains = {c.name: tuple(sorted(c.values, key=_canon)) for c in choices}
    count = 1
    for c in choices:count *= max(1, len(c.values))
    count = max(count, len(ways))
    if count > budget.ways:
        sentence = budget.sentence(0, count, 'the ways of reading this; nothing is combined')   # none was worked out
        return {'state': UNDECIDED, 'form': 'TOO_MANY', 'choices': names, 'relevant': [], 'irrelevant': [], 'groups': [], 'except': None,
                'conflict': [], 'ways': [], 'budget': (0, count, sentence)}
    ways = sorted([dict(w, choice=dict(w.get('choice') or {})) for w in ways], key=lambda w: [(n, _canon(w['choice'].get(n))) for n in names])
    conflict = [w for w in ways if w['state'] == CONFLICT]
    keys = {_key(w) for w in ways}
    relevant = []
    for name in names:
        rest = {}
        for w in ways:rest.setdefault(_fixed({k: v for k, v in w['choice'].items() if k != name}), set()).add(_key(w))
        if any(len(k) > 1 for k in rest.values()):relevant.append(name)
    found, examined, of = _groups(names, domains, ways, budget)
    groups = [{'state': key[0], 'value': key[1], 'groups': [list(g) for g in sorted(found[key], key=lambda g: (len(g), [(n, _canon(v)) for n, v in g]))]}
              for key in sorted(found, key=lambda k: (RANK.get(k[0], 2), _canon(k[1])))]
    sentence = '' if examined >= of else budget.sentence(examined, of, 'the larger groups; each way left over is named by its whole choice')
    out = {'choices': names, 'relevant': relevant, 'irrelevant': [n for n in names if n not in relevant], 'groups': groups, 'except': None,
           'conflict': conflict, 'ways': conflict + [w for w in ways if w['state'] != CONFLICT], 'budget': (examined, of, sentence)}
    if conflict:return {**out, 'state': CONFLICT, 'form': 'CONFLICT'}
    if len(keys) <= 1:return {**out, 'state': meet(w['state'] for w in ways), 'form': 'EITHER_WAY'}
    states = {w['state'] for w in ways}
    if len(relevant) == 1 and states <= set(SETTLED):return {**out, 'state': DEPENDS, 'form': 'DEPENDS_ON_ONE'}
    if len(keys) == 2:
        for rest_state in SETTLED:                   # "holds, except in one case" first, then "does not hold, except"
            rest = [k for k in keys if k[0] == rest_state]
            if len(rest) != 1:continue
            odd = next(k for k in keys if k != rest[0])
            if len(found.get(odd, ())) == 1:
                return {**out, 'state': DEPENDS, 'form': 'EXCEPT', 'except': {'state': odd[0], 'value': odd[1], 'group': list(found[odd][0]),
                                                                              'rest': rest_state}}
    return {**out, 'state': DEPENDS, 'form': 'DEPENDS'}


def question(about, choice, ways, model_loaded=False, proof=''):
    """The one question of a DEPENDS_ON_ONE: an OpenPoint whose outcomes are the buttons, one per value of the choice,
    each with the exact state and room of its way. Who asks it comes from the closed table (mind_types.who)."""
    who, kind = _who(choice.premise, model_loaded)
    outcomes = []
    for value in sorted(choice.values, key=_canon):
        way = next((w for w in ways if w['choice'].get(choice.name) == value), None)
        if way is None:continue
        outcomes.append(Way(choices=((choice.name, value),), state=way['state'], room=way.get('room'), unit=way.get('unit', ''),
                            answer=way.get('answer', ''), words=WORDS['button'].format(value=value, outcome=way.get('words') or STATE_WORDS.get(way['state'], ''))))
    leaf = Leaf(id=choice.name, about=tuple(about), premise=choice.premise, who=who, decisive=ALONE, values=tuple(sorted(choice.values, key=_canon)),
                words=choice.words)
    return OpenPoint(about=tuple(about), kind=kind, who=who, leaves=(leaf,), outcomes=tuple(outcomes), proof=proof)


def _group_words(group, labels=None):
    labels = labels or {}
    return ', '.join(labels.get((n, v), '%s' % v) for n, v in group) or 'every reading'


def sentences(found, subject, choices, labels=None):
    """Her sentences for a combined answer."""
    by = {c.name: c for c in choices};lines = []
    ways = found['ways'];form = found['form']
    if form == 'TOO_MANY':
        return [WORDS['too_many'].format(of=found['budget'][1], ways=BUDGET.ways), found['budget'][2]]
    if form == 'CONFLICT':
        for w in found['conflict']:lines.append(WORDS['conflict'].format(group=_group_words(_fixed(w['choice']), labels)))
    listed = '; '.join((WORDS['way'].format(value=_group_words(_fixed(w['choice']), labels), outcome=w.get('words') or STATE_WORDS.get(w['state'], ''))
                        if w['choice'] else (w.get('words') or STATE_WORDS.get(w['state'], ''))) for w in ways if w['state'] != CONFLICT)
    if form == 'EITHER_WAY':
        if ways and ways[0].get('value') is not None and ways[0].get('value_words'):
            lines.append(WORDS['either_value'].format(subject=subject, value=ways[0]['value_words']))
        else:
            lines.append(WORDS['either_' + (found['state'] if found['state'] in SETTLED else UNDECIDED)].format(subject=subject, ways=listed or 'one way'))
    elif form == 'DEPENDS_ON_ONE':
        c = by.get(found['relevant'][0]);lines.append(WORDS['one'].format(subject=subject, choice=(c.words if c and c.words else found['relevant'][0])))
    elif form == 'EXCEPT':
        odd = found['except'];odd_way = next(w for w in ways if all(w['choice'].get(n) == v for n, v in odd['group']))
        lines.append(WORDS['except_' + odd['rest']].format(subject=subject, group=_group_words(odd['group'], labels),
                                                          state=odd_way.get('words') or STATE_WORDS.get(odd['state'], '')))
    elif form == 'DEPENDS':
        rel = [by[n].words if n in by and by[n].words else n for n in found['relevant']]
        lines.append(WORDS['depends'].format(subject=subject, n=len(rel), choices='; '.join(rel)))
        for g in found['groups']:
            for group in g['groups']:
                way = next(w for w in ways if all(w['choice'].get(n) == v for n, v in group))
                lines.append(WORDS['stands'].format(group=_group_words(group, labels), outcome=way.get('words') or STATE_WORDS.get(g['state'], '')))
    if found['irrelevant'] and form != 'TOO_MANY' and len(found['choices']) > 1:
        lines.append(WORDS['not_matter'].format(choices='; '.join(by[n].words if n in by and by[n].words else n for n in found['irrelevant'])))
    if found['budget'][2]:lines.append(found['budget'][2])
    return lines


# =========================================================================================================================
# On the desk: a goal over data, judged every way
# =========================================================================================================================

def row_ref(sheet, cell):
    """A row of a reviewed sheet as goals refer to it ({address, sheet, cell, parameter, title}), read as it stands."""
    from .office_service import store
    from .tolerances import sheet_cell
    try:saved = store().get(sheet)
    except (ValueError, OSError, KeyError):saved = None
    found = sheet_cell(saved, cell) if saved else None
    if not found or not found['parameter']:raise ValueError('That row is not a reviewed row of a sheet on the desk.')
    return {'address': found['address'], 'sheet': found['sheet'], 'cell': found['cell'], 'parameter': found['parameter'], 'title': found['title']}


def _row_label(ref, others=()):
    from .your_word import short_name
    return '%s (%s, row %d)' % (ref['parameter'], short_name(ref['title'], [o['title'] for o in others]), int(ref['cell'][1:]))


def _symbol_words(symbol):
    return symbol.replace('_', ' ')


def _room(result, relation):
    slack = (result or {}).get('slack')
    if not slack:return None, ''
    lo, hi = Fraction(slack[0]['rational']), Fraction(slack[1]['rational'])
    return ((lo, hi) if relation in ('le', 'lt') else (-hi, -lo)), slack[0]['unit']


def _way_words(answer, room, unit, relation, unknown):
    """One way's outcome in her words: 'holds, 15/16 to 17/16 W to spare', 'cannot tell: 3.995 to 4.165 W against 4 W; at
    4.165 W it would not hold', or for an unknown, how far it may go."""
    from .math_answers import figure, span_words
    from .reasons import room_words
    state = answer.get('state');result = answer.get('result') or {}
    if unknown:
        move = next((m for m in result.get('moves') or () if m['name'] == unknown), None)
        upper = ((move or {}).get('upper') or {}).get('value');step = ((move or {}).get('rise') or {}).get('on_step')
        if upper:
            whole = (' so %s on whole steps' % figure(Fraction(step['rational']), step['unit'])) if step else ''
            return 'at most %s%s' % (figure(Fraction(upper['rational']), upper['unit']), whole)
        return STATE_WORDS.get(state, str(state).lower())
    if state in SETTLED:
        rw = room_words(room, unit, state) if room else ''
        return STATE_WORDS[state] + ((', ' + rw) if rw else '')
    if state == UNDECIDED and result.get('left') and result.get('right'):
        left = [Fraction(x['rational']) for x in result['left']];right = [Fraction(x['rational']) for x in result['right']]
        lu = result['left'][0]['unit'];ru = result['right'][0]['unit']
        witness = left[1] if relation in ('le', 'lt') else left[0]
        return WORDS['undecided_over'].format(left=span_words(left[0], left[1], lu), right=span_words(right[0], right[1], ru), witness=figure(witness, lu))
    return STATE_WORDS.get(state, str(state).lower().replace('_', ' '))


def _value_of(answer, unknown):
    """The exact end an unknown may go to (its compared value), or None."""
    if not unknown:return None
    move = next((m for m in (answer.get('result') or {}).get('moves') or () if m['name'] == unknown), None)
    upper = ((move or {}).get('upper') or {}).get('value')
    return (str(Fraction(upper['rational'])), upper['unit']) if upper else (answer.get('state'), '')


def judge_goal(kernel, principal, goal, *, choose=(), readings=None, at=None, unknown=None, stage='check', accuracy=(), said=None,
               words=None, model_loaded=False, ident='', named=None):
    """A relation goal judged under every way the desk knows of: each revision of its limit (unless your word, the finding
    or the question names one), and each row a symbol could read (readings: {symbol: [ref]}, the goal's own row first).
    at: {symbol: exact value in its row's unit}, taken as asked, without a tolerance. unknown: a symbol, whose end is
    compared instead of the state. stage: 'check', 'room' or 'settle' (settle takes accuracy, as goals.check does).
    Reads only. The dict of combine() and: 'goal', 'key', 'statement', 'subject', 'question', 'words', 'receipt',
    'judgement' (mind_types.Judgement), 'choice_objects', 'model_calls': 0."""
    from . import goals as G, math_answers as answers, tolerances, your_word
    from .math_ranges import RangeError
    from .office_service import store
    if unknown and stage == 'check':stage = 'room'
    said = tolerances.on_cells(kernel, principal) if said is None else said
    words = your_word.standing(kernel, principal) if words is None else words
    symbol = next(iter((goal.get('alternatives') or {}).keys()), None);options = your_word._alternatives_of(goal)
    receipt = {'word': None, 'asked': None, 'named': None, 'at': {}, 'answers': []}
    fixed = {};choices = [];labels = {}
    if symbol and options:
        chosen = [a for a in options if a['sheet'] in set(choose or ())]
        if named:
            fixed[symbol] = named;receipt['named'] = your_word.short_name(named['title'], [a['title'] for a in options])
        elif chosen:
            fixed[symbol] = chosen[0];receipt['asked'] = your_word.short_name(chosen[0]['title'], [a['title'] for a in options])
        else:
            way, word = your_word.choice_for(words, goal, ident or (goal.get('id', '') if len(goal.get('id', '')) == 32 else ''), goal.get('key', ''))
            if way:
                fixed[symbol] = way
                receipt['word'] = {'id': word['id'], 'sort': word['sort'], 'statement': word['statement'], 'scope': word.get('scope', ''),
                                   'name': your_word.short_name(way['title'], [a['title'] for a in options])}
            else:
                names = {your_word.short_name(a['title'], [o['title'] for o in options]): a for a in options}
                choices.append(Choice('revision', tuple(sorted(names)), 'REVISION', 'which revision applies'))
                fixed['__revision'] = names
    reading_refs = {}
    for name, refs in sorted((readings or {}).items()):
        if name not in goal['cells']:raise ValueError('The goal does not read %s.' % _symbol_words(name))
        rows = [goal['cells'][name]] + [r for r in refs if (r['sheet'], r['cell']) != (goal['cells'][name]['sheet'], goal['cells'][name]['cell'])]
        if len(rows) < 2:continue
        named_rows = {_row_label(r, rows): r for r in rows}
        reading_refs[name] = named_rows
        choices.append(Choice('reading:' + name, tuple(sorted(named_rows)), 'WHICH_GOAL', 'which row %s means' % _symbol_words(name)))
    for name in (at or {}):
        if name not in goal['cells']:raise ValueError('The goal does not read %s.' % _symbol_words(name))
    taken, count = every_way(choices)
    subject = ('How far %s may go' % _symbol_words(unknown)) if unknown else goal['statement'].split(' is ')[0]
    base = {'goal': goal.get('id') if len(goal.get('id', '')) == 32 else None, 'key': goal.get('key'), 'statement': goal['statement'], 'subject': subject,
            'choice_objects': choices, 'model_calls': 0}
    if taken is None:
        found = combine(choices, [], BUDGET)
        lines = sentences(found, subject, choices)
        judgement = Judgement(about=(goal.get('id') or goal.get('key'),), state=UNDECIDED, budget=found['budget'])
        return {**base, **found, 'question': None, 'words': lines, 'receipt': receipt, 'judgement': judgement.as_record()}
    sheets = {};fresh_of = {}

    def saved_of(sheet):
        if sheet not in sheets:
            try:sheets[sheet] = store().get(sheet)
            except (ValueError, OSError, KeyError):sheets[sheet] = None
        return sheets[sheet]

    def fresh(sheet):
        if sheet not in fresh_of:
            saved = saved_of(sheet);fresh_of[sheet] = G._freshness(kernel, principal, saved) if saved else 'MISSING'
        return fresh_of[sheet]

    rows_out = []
    for picked in taken:
        bound = {**goal['cells']}
        for s, ref in fixed.items():
            if not s.startswith('__'):bound[s] = ref
        if 'revision' in picked:bound[symbol] = fixed['__revision'][picked['revision']]
        for name, by in reading_refs.items():bound[name] = by[picked['reading:' + name]]
        cells = {};missing = [];state_fresh = 'CURRENT';drop = set()
        for s, ref in bound.items():
            saved = saved_of(ref['sheet'])
            cell = tolerances.sheet_cell(saved, ref['cell']) if saved else None
            if not cell or cell['parameter'] != ref['parameter']:missing.append(ref);continue
            if s in (at or {}):
                cell = dict(cell, value=str(at[s]));drop.add((cell['address'], cell['cell']))
                receipt['at'][s] = '%s %s' % (at[s], cell['unit'])
            cells[s] = cell
            if fresh(ref['sheet']) != 'CURRENT':state_fresh = 'REVIEW_REQUIRED'
        asked = {'expression': goal['expression'], **({'accuracy': list(accuracy)} if accuracy and stage == 'settle' else {})}
        if missing:
            answer = answers.refused(stage, asked, 'MISSING_INPUT', 'A row this goal reads is no longer where it was: %s' % ', '.join(
                '%s %s' % (r['title'], r['cell']) for r in missing), state_fresh)
        else:
            use = {k: v for k, v in said.items() if k not in drop}
            try:ir, inputs = answers.bindings_from_cells(goal['expression'], cells, use, roles=goal.get('roles'))
            except (RangeError, ValueError) as exc:answer = answers.refused(stage, asked, getattr(exc, 'code', 'UNSUPPORTED'), str(exc), state_fresh)
            else:answer = answers.answer(stage, ir, inputs, asked, state_fresh)
        state = answer['state'] if answer['state'] in (HOLDS, FAILS, UNDECIDED, CONFLICT) else UNDECIDED
        room, unit = _room(answer.get('result'), goal['relation'])
        value = _value_of(answer, unknown)
        row = {'choice': dict(picked), 'state': state, 'room': room, 'unit': unit, 'answer': answer['digest'], 'answer_state': answer['state'],
               'words': _way_words(answer, room, unit, goal['relation'], unknown), 'value': value, 'record': answer,
               'bound': {s: {'sheet': r['sheet'], 'cell': r['cell'], 'title': r['title']} for s, r in bound.items()}}
        if unknown and value and value[1]:row['value_words'] = row['words']
        rows_out.append(row);receipt['answers'].append(answer['digest'])
    found = combine(choices, rows_out, BUDGET)
    for name, by in reading_refs.items():
        for label in by:labels[('reading:' + name, label)] = label
    for c in choices:
        if c.name == 'revision':
            for v in c.values:labels[('revision', v)] = v
    proof = digest({'goal': goal.get('key') or goal.get('id'), 'ways': [(w['choice'], w['answer']) for w in found['ways']], 'word': receipt['word'],
                    'asked': receipt['asked'], 'named': receipt['named'], 'at': receipt['at']})
    asked_q = None
    if found['form'] == 'DEPENDS_ON_ONE':
        c = next(c for c in choices if c.name == found['relevant'][0])
        asked_q = question((goal.get('id') or goal.get('key'),), c, found['ways'], model_loaded, proof)
    lines = sentences(found, subject, choices, labels)
    if receipt['word']:lines.append(WORDS['word'].format(choice='which revision applies', statement=receipt['word']['statement']))
    if receipt['asked']:lines.append(WORDS['asked'].format(value=receipt['asked']))
    if receipt['named']:lines.append(WORDS['named'].format(value=receipt['named']))
    for s, v in sorted(receipt['at'].items()):lines.append(WORDS['at'].format(name=_symbol_words(s).capitalize(), value=v))
    if found['form'] in ('EITHER_WAY', 'EXCEPT') and asked_q is None:lines.append(WORDS['nobody'])
    rests = sorted({'%s %s' % (ref['title'], ref['cell']) for ref in goal['cells'].values()})
    if receipt['word']:rests.append('your word: ' + receipt['word']['statement'])
    shapes = tuple(Way(choices=tuple(sorted((k, str(v)) for k, v in w['choice'].items())), state=w['state'], room=w['room'], unit=w['unit'],
                       answer=w['answer'], words=w['words']) for w in found['ways'])
    judgement = Judgement(about=(goal.get('id') or goal.get('key'),), state=found['state'], ways=shapes,
                          open_points=(asked_q,) if asked_q else (), proof=proof, rests_on=tuple(rests), budget=found['budget'])
    public = [{k: v for k, v in w.items() if k != 'record'} for w in found['ways']]
    return {**base, **found, 'ways': public, 'records': [w['record'] for w in found['ways']], 'question': asked_q.as_record() if asked_q else None,
            'words': lines, 'receipt': receipt, 'judgement': judgement.as_record(), 'proof': proof}


# =========================================================================================================================
# On the desk: a period on the admitted papers, for every event that could have started it
# =========================================================================================================================

AMOUNT = re.compile(r'^-?[0-9][0-9,]*(?:\.[0-9]+)?$')
ISO = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def _papers(kernel, principal):
    from .reading import _passages, papers
    passages = _passages(kernel, principal)
    return papers(passages), passages


def _amount_named(passages, words=('deposit',)):
    """The amount the papers name for the thing the period is about ("Deposit held by the landlord: 1200.00"), or None."""
    for passage in passages:
        for line in str(passage.get('text') or '').splitlines():
            for w in words:
                found = re.search(r'%s[^0-9]{0,60}([0-9][0-9,]*\.[0-9]{2})\b' % re.escape(w), line, re.I)
                if found:return found.group(1).replace(',', '')
    return None


def ledger_rows(sheet):
    """The dated rows of a reviewed ledger sheet: [(date, description, amount)], each row's ISO day, its words and its
    amount (the Value column), as the sheet holds them now; rows without a day or an amount are left out."""
    from .office_service import store
    try:saved = store().get(sheet)
    except (ValueError, OSError, KeyError):raise ValueError('That sheet cannot be read.') from None
    cells = ((saved.get('document') or {}).get('sheets') or [{}])[0].get('cells') or {};rows = {}
    for address, cell in cells.items():
        found = re.fullmatch(r'([A-Z]+)(\d+)', address)
        if found:rows.setdefault(int(found.group(2)), {})[found.group(1)] = str((cell or {}).get('value') if (cell or {}).get('value') is not None else '').strip()
    out = []
    for n in sorted(rows):
        row = rows[n];day = next((v for v in row.values() if ISO.match(v)), None)
        amount = row.get('B', '')
        if day is None or not AMOUNT.match(amount.replace(',', '')):continue
        out.append((day, row.get('A', ''), amount.replace(',', '')))
    return out, (saved.get('document') or {}).get('title') or ''


def _complete_word(words, sheet, start, end):
    """Your COMPLETE word on the sheet that covers start to end (ISO days), standing and current, or None."""
    for w in words:
        if w.get('sort') != 'COMPLETE' or w.get('state') != 'IN' or w.get('freshness', 'CURRENT') != 'CURRENT':continue
        if (w.get('subject') or {}).get('sheet') != sheet:continue
        value = w.get('value') or {}
        if value.get('from', '9999') <= start and value.get('to', '0000') >= end:return w
    return None


def period_ways(kernel, principal, clause=None, *, on=None, sheet=None, amount=None, words=None, model_loaded=False):
    """A period of days on the admitted papers ("within 21 days after a tenancy ends"), judged for every event the papers
    give that could have started it: the last day of each (math_dates, by the counting rules the papers quote), and
    whether the payment was made by then: on the day asked here (on), or as the ledger sheet shows it. A credit of the
    amount by the last day holds; with none, it does not hold only where your COMPLETE word covers the sheet from the
    event to the last day; otherwise she cannot tell. Reads only. The dict of combine() and 'period', 'question',
    'words', 'receipt'."""
    from . import math_dates, your_word
    (periods, counting, events), passages = _papers(kernel, principal)
    if clause:period = next((p for p in periods if p['clause'] == clause), None)
    else:period = periods[0] if len(periods) == 1 else None
    if period is None:raise ValueError('No period of days on the admitted papers has that clause.' if clause else 'Name the clause of the period.')
    starts = [e for e in events if e.get('ends')]
    if not starts:raise ValueError('No dated line on the admitted papers gives the day %s.' % period['event'])
    skips = tuple((counting.get('roll') or {}).get('skips') or ());yearly = math_dates.yearly_of(counting.get('yearly'))
    labels = {e['label']: e for e in starts}
    choice = Choice('event', tuple(sorted(labels)), 'RULE_READING', 'which day %s' % period['event'])
    words = your_word.standing(kernel, principal) if words is None else words
    amount = amount or _amount_named(passages)
    rows, title = (ledger_rows(sheet) if sheet else ([], ''))
    receipt = {'clause': period['clause'], 'words': period['words'], 'count': period['count'], 'skips': list(skips),
               'roll': (counting.get('roll') or {}).get('clause'), 'holidays': (counting.get('holiday_clause') or {}).get('clause'),
               'on': on, 'sheet': sheet, 'title': title, 'amount': amount, 'word': None}
    if on is None and not sheet:raise ValueError('Say the day it was paid (on), or the ledger sheet to read.')
    if on is not None:on_day = date.fromisoformat(on)
    ways = []
    for label, e in sorted(labels.items()):
        start = date.fromisoformat(e['day']);_, last, over = math_dates.last_day(start, period['count'], skips, (), yearly)
        lw = WORDS['last_day'].format(day=math_dates.words_of(last))
        if on is not None:
            spare = (last - on_day).days
            state = HOLDS if on_day <= last else FAILS
            words_here = '%s, %s: %s, %d day%s %s' % (lw, WORDS['paid_on'].format(day=math_dates.words_of(on_day)), STATE_WORDS[state], abs(spare),
                                                      '' if abs(spare) == 1 else 's', 'to spare' if state == HOLDS else 'late')
            room = (Fraction(spare), Fraction(spare));unit = 'days'
        else:
            credit = None
            if amount:
                want = Fraction(amount)
                credit = next((r for r in rows if Fraction(r[2]) == want and r[0] <= last.isoformat()), None)
            word = _complete_word(words, sheet, start.isoformat(), last.isoformat()) if credit is None else None
            if credit:state = HOLDS;told = WORDS['credit_found'].format(amount=amount, day=credit[0])
            elif word:
                state = FAILS;told = WORDS['credit_complete'].format(amount=amount, title=title)
                receipt['word'] = {'id': word['id'], 'sort': word['sort'], 'statement': word['statement']}
            else:state = UNDECIDED;told = WORDS['credit_unknown'].format(amount=amount or 'the amount', title=title or 'the sheet')
            words_here = '%s; %s' % (lw, told);room = None;unit = ''
        ways.append({'choice': {'event': label}, 'state': state, 'room': room, 'unit': unit, 'words': words_here, 'last_day': last.isoformat(),
                     'event_day': e['day'], 'passed_over': [(d.isoformat(), why) for d, why in over], 'answer': digest([label, e['day'], last.isoformat(), state])})
    found = combine([choice], ways, BUDGET)
    proof = digest({'period': receipt, 'ways': [(w['choice'], w['answer']) for w in found['ways']]})
    asked_q = question((period['clause'],), choice, found['ways'], model_loaded, proof) if found['form'] == 'DEPENDS_ON_ONE' else None
    subject = 'Paid within the period of %s' % period['clause']
    lines = sentences(found, subject, [choice], {('event', v): '%s (%s)' % (v, labels[v]['day']) for v in labels})
    if receipt['word']:lines.append(WORDS['word'].format(choice='whether the sheet is complete', statement=receipt['word']['statement']))
    if found['form'] == 'EITHER_WAY':lines.append(WORDS['nobody'])
    judgement = Judgement(about=(period['clause'],), state=found['state'], proof=proof, open_points=(asked_q,) if asked_q else (),
                          ways=tuple(Way(choices=(('event', w['choice']['event']),), state=w['state'], room=w['room'], unit=w['unit'], answer=w['answer'],
                                         words=w['words']) for w in found['ways']), budget=found['budget'])
    return {**found, 'period': {k: period[k] for k in ('clause', 'words', 'count', 'event', 'source')}, 'question': asked_q.as_record() if asked_q else None,
            'words': lines, 'receipt': receipt, 'judgement': judgement.as_record(), 'proof': proof, 'model_calls': 0}


# =========================================================================================================================
# The operation
# =========================================================================================================================

_ID = {'type': 'string', 'minLength': 1, 'maxLength': 200}
_SHEET = {'type': 'string', 'pattern': '^owner:[a-f0-9]{32}$'}
_CELL = {'type': 'string', 'pattern': '^B[1-9][0-9]{0,2}$'}
_NAME = {'type': 'string', 'pattern': '^[a-z][a-z0-9_]{0,63}$'}
_DAY = {'type': 'string', 'pattern': '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'}
_VALUE = {'type': 'string', 'pattern': '^-?[0-9]+(\\.[0-9]+)?(/[0-9]+)?$', 'maxLength': 60}
_AT = {'type': 'array', 'maxItems': 8, 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'value'],
                                                  'properties': {'name': _NAME, 'value': _VALUE}}}
_READING = {'type': 'array', 'maxItems': 8, 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'sheet', 'cell'],
                                                       'properties': {'name': _NAME, 'sheet': _SHEET, 'cell': _CELL}}}
FIELDS = {
    'field.either': ({'id': _ID, 'choose': {'type': 'array', 'maxItems': 8, 'items': _SHEET}, 'at': _AT, 'reading': _READING, 'unknown': _NAME,
                      'on': _DAY, 'sheet': _SHEET, 'model_loaded': {'type': 'boolean'}}, ['id']),
}
SCOPES = {op: 'read' for op in FIELDS}
OBSERVERS = tuple(FIELDS)


def goal_of(kernel, principal, ident):
    """(goal, its kept id or '', the revision a finding names or None, the subject's words) for 'goal:…' or a finding."""
    from .reasons import _Desk, _subject
    desk = _Desk(kernel, principal);subject = _subject(desk, ident)
    if subject.get('goal') is None:
        raise ValueError('That card is not a goal over the desk’s data, so there is no other way of reading it to work out. field.why gives its reasons.')
    return subject['goal'], subject.get('goal_id', ''), subject.get('named'), desk


def args_of(args):
    """The ways asked of a goal, from the operation's arguments: (choose, at, readings)."""
    at = {row['name']: row['value'] for row in args.get('at') or ()}
    readings = {}
    for row in args.get('reading') or ():readings.setdefault(row['name'], []).append(row_ref(row['sheet'], row['cell']))
    return tuple(args.get('choose') or ()), at, readings


def either(kernel, principal, args):
    ident = str(args['id']).strip()
    if ident.startswith('period:'):
        return _plain({'id': ident, **period_ways(kernel, principal, ident[7:].strip() or None, on=args.get('on'), sheet=args.get('sheet'),
                                                  model_loaded=bool(args.get('model_loaded')))})
    goal, goal_id, named, desk = goal_of(kernel, principal, ident)
    choose, at, readings = args_of(args)
    found = judge_goal(kernel, principal, goal, choose=choose, readings=readings, at=at, unknown=args.get('unknown'), words=desk.words, said=desk.said,
                       model_loaded=bool(args.get('model_loaded')), ident=goal_id, named=named)
    found.pop('choice_objects', None);found.pop('records', None)
    return _plain({'id': ident, **found})          # plain JSON-ready data: exact values as their text, tuples as lists


def dispatch(kernel, op, args, principal):
    from .office_service import owner
    owner(principal)                 # the sheets live in the owner's profile, as for office.get
    if op == 'field.either':return either(kernel, principal, args)
    raise ValueError('Unknown either-way operation')
