"""Your words name it: the READ checker (0.8.7 "Kas's mind with the model, interwoven", slice B3, lane B; design 3.4).

The model proposes; the system disposes. A READ answer (understand.Reading) is checked here part by part, with no model and
no float, before anything uses it. Each step is OK, UNSETTLED (with candidates and why) or REFUSED (with why), in template
words, by these rules, in order:

    1  shape      at most two steps in core (the parser's), no step twice
    2  registry   the verb is in the turn's table (understand.VERBS over desk_acts.MODEL_VERBS: nothing owner-only, no
                  delete, rename or write, no App verb) and fits the thing; every act it ends in passes desk_acts.model_may
                  and desk_acts.check
    3  records    the handle is in this turn's numbered list; the record is still at the revision it was listed at (when
                  the desk can be read again: inputs.fresh); the kind fits (compare needs a sibling: desk_acts' NO_SIBLING
                  words; what if and set need a number; within needs a goal over it; the column is the thing's own)
    4  your words each quoted span is words you typed (case and punctuation between words aside), bound by offsets, inside
                  what READ was asked to read, and outside quoted text and pasted blocks (doorway.quoted_spans, the span
                  function the doorway shares): "That came from the text you pasted, not from you."
    5  naming     your agreed name for it (B5's Your words); or the most shared content-word stems with its title, kind or
                  columns, with no other listed thing sharing more; or a value in one of its columns. A tie is broken only
                  by fixed, visible rules, which the card names: your words, then the current revision over the archived
                  one, then the sheet you selected. Otherwise UNSETTLED, with its candidates
    6  a change   (set) needs a change word of yours outside quotes and a value written exactly in the row's unit; then it
                  is a proposal whose basis is model_pick (stacy_hand.proposal), so it always asks, at every dial. Without
                  the word: "I read a change you did not ask for in words, so I propose none."
    7  back-references point only backwards (the parser's); at most one change per request
    8  a reading you answered "Not that" to, for the same words, becomes her question instead
    (0.8.7 B8: a total settles rules 3 and 5 by total_plan, at the end of this file: the sheet, the column, your words for
    its rows exact or asked, never quietly matched, and a period by the dates core)

Then the steps that end in 0.8.6's desk goals are put to 0.8.6's answer_check.check_pick, composed rather than re-built:
its licence (the step's words name it in some clause of the request), coverage and joint plan (planner.plan on the desk).
Its authority rule (a pick that chose a revision the request does not name) is answered here by rule 5's fixed tie rule,
never by the model: such an option carries no revision for the model to have chosen. answer_check's WORDS check is the
card's: a number the card says of the desk ("now 40 ms") is shown only when check_words finds it on the desk exactly.

    check(found, inputs) -> turns.Verdict    (state TAKEN, TRIMMED, REFUSED or UNSETTLED; basis model_pick)
        value: {kind, steps: [one dict a step], readings: [0.8.6 readings of the OK steps], question, refused, held}
    CHANGE_WORDS, WHY (the words of each reason)

Each OK step becomes a 0.8.6 reading (frame DESK goals for show, trace, compare and tidy; VALUE and CHECK for value and
within; frame READ with its desk acts for card, doubt, what if, count and set), labelled origin MODEL_READ, and flows on
unchanged. If any step is UNSETTLED nothing runs: its readings are held until your one answer. Pure Python.
"""
from __future__ import annotations

import re
from fractions import Fraction

from . import answer_check, brief as brief_mod, desk_acts, doorway, hand_words, reading, stacy_hand
from .turns import Verdict

OK, UNSETTLED, REFUSED = 'OK', 'UNSETTLED', 'REFUSED'
CHANGE_WORDS = stacy_hand.CHANGE_WORDS | frozenset(('update', 'adjust', 'lower', 'raise', 'increase', 'decrease', 'reduce', 'bump'))
WHY = {
    'TWICE': 'That step was read twice.',
    'NOT_FOR_THIS': '“{title}” is {a_kind}, and “{verb}” does not apply to it.',
    'NOT_IN_TABLE': 'It would {why}.',
    'ARGUMENTS': '{why}',
    'NOT_LISTED': '“{title}” is not in the list I gave the model.',
    'CHANGED': '“{title}” changed while I was reading; ask me again.',
    'NO_SIBLING': desk_acts.REFUSALS['NO_SIBLING'],
    'NOT_A_NUMBER': '“{label}” of “{title}” holds no number for that.',
    'NO_GOAL': 'Nothing on the desk checks “{title}” against a limit.',
    'NOT_YOUR_WORDS': '“{words}” is not in what you typed.',
    'PASTED': 'That came from the text you pasted, not from you.',
    'READ_ALREADY': '“{words}” was read already, by my dictionary.',
    'NAMES_ANOTHER': '“{words}” names “{other}”, not “{title}”.',
    'TIE': '“{words}” names {others} alike.',
    'NOT_NAMED': 'I could not find what “{words}” means on the desk.',
    'YOU_SAID_NOT_THAT': 'You said “Not that” to this reading of these words, so which you meant is yours to say.',
    'NO_CHANGE_WORD': 'I read a change you did not ask for in words, so I propose none.',
    'NOT_A_VALUE': '“{value}” is not a number I can read exactly.',
    'UNIT': '“{value}” is not in the unit of “{label}”, {unit}.',
    'ONE_CHANGE': 'One change at a time: the first one waits for you.',
    'NOT_IN_COLUMN': '“{value}” is not in the column “{label}” of “{title}”.',
    'WOULD_NOT_ASK': 'That change would not ask you first, so I propose none.',
    'UNLICENSED': 'Nothing in your request asks for “{title}”.',
    'NO_JOINT_PLAN': '{why}',
}
RULE_WORDS = {'names': 'your words, agreed', 'current': 'the current revision', 'selected': 'the sheet you selected',
              'step1': 'what step 1 was about', 'pair': 'both revisions', 'value': 'a value in its column'}
KIND_WORDS = {'sheet': 'a sheet', 'typed': 'a typed sheet', 'calculation': 'a calculation', 'clause': 'a clause of a paper'}
VALUE = re.compile(r'\s*([+-]?\d{1,12}(?:\.\d{1,12})?)\s*([A-Za-zµΩ%]{1,3})?\s*')


# -- your words: where they are in what you typed ---------------------------------------------------------------------------------
def places(text, words):
    """Every (start, end) where `words` stand in `text`: the same words in order, case aside, with only spaces or
    punctuation between them, at word edges."""
    toks = re.findall(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)?|[^\sA-Za-z0-9]", str(words or ''))
    toks = [t for t in toks if re.match(r'[A-Za-z0-9]', t)]
    if not toks:return []
    pattern = r'(?<![A-Za-z0-9])' + r"[\s,;:.!?'’\"“”()-]+".join(re.escape(t) for t in toks) + r'(?![A-Za-z0-9])'
    return [m.span() for m in re.finditer(pattern, text, re.IGNORECASE)]


def locate(text, words, i):
    """(span, why): the first place of your words inside the target and outside quotes; else why not (NOT_YOUR_WORDS,
    PASTED or READ_ALREADY)."""
    found = places(text, words)
    if not found:return None, 'NOT_YOUR_WORDS'
    outside = [s for s in found if doorway.outside_quotes(text, s[0], s[1], list(i.spans))]
    if not outside:return None, 'PASTED'
    inside = [s for s in outside if any(a <= s[0] and s[1] <= b for a, b in i.target)]
    if not inside:return None, 'READ_ALREADY'
    return inside[0], ''


def change_words(i):
    """Your change words (CHANGE_WORDS) outside quotes and pasted blocks, inside what READ reads: [(word, start, end)]."""
    out = []
    for m in re.finditer(r"[A-Za-z]+", i.text):
        if m.group(0).casefold() not in CHANGE_WORDS:continue
        if not doorway.outside_quotes(i.text, m.start(), m.end(), list(i.spans)):continue
        if any(a <= m.start() and m.end() <= b for a, b in i.target):out.append((m.group(0), m.start(), m.end()))
    return out


# -- naming ---------------------------------------------------------------------------------------------------------------------
def _current(top):
    marked = [x for x in top if x.mark == 'CURRENT']
    if len(marked) == 1:return marked[0]
    newer = [x for x in top if x.kind == 'sheet' and not x.older and x.sibling]
    return newer[0] if len(newer) == 1 else None


def naming(step, i):
    """(state, why, candidates, rule): whether your words name this step's thing, by rule 5."""
    t = step.thing;w = reading.stems(step.words)
    agreed = i.names.get(reading.said_key(step.words))
    if agreed:
        if agreed == t.id:return OK, '', [], 'names'
        other = next((x for x in i.things if x.id == agreed), None)
        return UNSETTLED, 'NAMES_ANOTHER', [other] if other else [], ''
    if step.handle.startswith('S'):
        said = {x.casefold() for x in re.findall(r"[A-Za-z]+", step.words)}
        if said <= (REFERENCE | reading.STOP) or (w & t.stems):return OK, '', [], 'step1'
        return UNSETTLED, 'NAMES_ANOTHER', [t], ''
    if not w:return UNSETTLED, 'NOT_NAMED', [], ''
    score = {x.handle: 2 * len(w & x.stems) + len(w & x.column_stems) for x in i.things}
    best = max(score.values()) if score else 0
    if best == 0:
        if w <= t.value_stems:return OK, '', [], 'value'
        return UNSETTLED, 'NOT_NAMED', [], ''
    top = [x for x in i.things if score[x.handle] == best]
    if t not in top:return UNSETTLED, 'NAMES_ANOTHER', top, ''
    if len(top) == 1:return OK, '', [], ''
    if step.verb == 'compare' and all(x.title in (t.title, t.sibling) for x in top):return OK, '', [], 'pair'
    if len({x.base.casefold() for x in top}) == 1 and all(x.rev for x in top):
        current = _current(top)
        if current is t:return OK, '', [], 'current'
        if current is not None:return UNSETTLED, 'NAMES_ANOTHER', [current] + [x for x in top if x is not current], ''
    if i.selected and any(x.title == i.selected for x in top):
        if t.title == i.selected:return OK, '', [], 'selected'
        return UNSETTLED, 'NAMES_ANOTHER', [x for x in top if x.title == i.selected] + [x for x in top if x.title != i.selected], ''
    ranked = sorted(top, key=lambda x: (x.mark != 'CURRENT', x.older, x.handle))
    return UNSETTLED, 'TIE', ranked, ''


REFERENCE = frozenset(('it', 'its', 'that', 'this', 'them', 'their', 'those', 'these', 'one', 'same'))


# -- what a step becomes -----------------------------------------------------------------------------------------------------
def _value_text(value, unit):
    """The value as the act takes it: the number as written (its unit, if any, matched to the row's)."""
    m = VALUE.fullmatch(value or '')
    return m.group(1) if m else ''


def acts(step, value=''):
    """The desk acts a step ends in ([name, args]), for the verbs that end in acts."""
    t = step.thing;v = step.verb;pick = ['point.sheet', {'title': t.title}]
    if v == 'card':return [pick, ['sheet.steps', {}]]
    if v == 'doubt':return [pick, ['sheet.doubt', {}]]
    if v == 'what if':return [pick, ['sheet.whatif', {'cell': step.column.cell, 'value': value}]]
    if v == 'set':return [pick, ['hand.cell', {'cell': step.column.cell, 'value': value}]]
    if v == 'count':
        keep = [['then.keep', {'column': step.column.label, 'words': step.value}]] if step.column is not None and step.value else []
        return keep + [['then.count', {}]]
    return []


def _goals_over(t, i, column=None):
    out = []
    for g in getattr(i.lex, 'goals', ()) or ():
        cells = list((g.get('cells') or {}).values()) + list(g.get('_alternatives') or ())
        hit = [c for c in cells if c.get('sheet') == t.id or c.get('title') == t.title]
        if column is not None:hit = [c for c in hit if c.get('cell') == column.cell or c.get('parameter') == column.label]
        if hit:out.append({'key': g['key'], 'statement': g['statement']})
    return out


def becomes(step, i, value=''):
    """The 0.8.6 reading an OK step flows on as (origin MODEL_READ)."""
    t = step.thing;v = step.verb
    base = {'clause': step.words, 'origin': 'MODEL_READ', 'step': step.n, 'basis': stacy_hand.MODEL_PICK}
    if v == 'tidy':return {**base, 'clause': 'tidy', 'frame': 'DESK', 'route': 'DESK', 'goals': [{'template': 'tidy', 'params': {}}]}
    if v == 'show' and t.kind == 'clause':
        return {**base, 'frame': 'READ', 'route': 'PLACE', 'place': {'id': t.id, 'title': t.title, 'words': t.words}}
    if v in ('show', 'trace'):
        return {**base, 'frame': 'DESK', 'route': 'DESK', 'goals': [{'template': 'shown' if v == 'show' else 'traced', 'params': {'s': t.title}}]}
    if v == 'compare':
        pair = i.world.pair(t.title) if i.world is not None else None
        return {**base, 'frame': 'DESK', 'route': 'DESK', 'goals': [{'template': 'side_by_side', 'params': {'a': pair[0], 'b': pair[1]}}]}
    if v == 'value':
        if t.kind == 'calculation':
            calc = next((c for c in i.lex.calculations if c.get('title') == t.title), {})
            rows = [{'calculation': calc.get('id') or t.id, 'title': t.title, 'unit': calc.get('unit', '')}]
        else:
            rows = [{**r.ref(), 'value': r.value, 'unit': r.unit, 'revision': i.lex.sheet_words(r.sheet) if r.rev else ''}
                    for r in i.lex.rows if r.sheet == t.id and (step.column is None or r.cell == step.column.cell)]
        return {**base, 'frame': 'VALUE', 'route': 'VALUE', 'rows': rows, 'unit': '', 'choose': []}
    if v == 'total':                                          # 0.8.7 B8: the rows his words name, added up by the maths core
        plan = total_plan(step, i)
        if plan['state'] != OK:raise ValueError('TOTAL_NOT_SETTLED: %s' % plan['code'])
        return {**base, **plan['reading']}
    if v == 'within':
        goals = _goals_over(t, i, step.column)
        return {**base, 'frame': 'CHECK', 'route': 'CHECK', 'goals': goals, 'covering': len(goals) > 1, 'choose': [], 'choice_words': ''}
    return {**base, 'frame': 'READ', 'route': 'DESK', 'verb': v, 'acts': acts(step, value), 'thing': {'id': t.id, 'title': t.title}}


# -- one step ---------------------------------------------------------------------------------------------------------------------
def _words(code, step, **more):
    t = step.thing
    fill = {'title': t.title if t else '', 'verb': step.verb, 'words': step.words, 'value': step.value,
            'label': step.column.label if step.column else '', 'unit': step.column.unit if step.column else '',
            'a_kind': KIND_WORDS.get(t.kind, 'a thing') if t else 'nothing', **more}
    return WHY[code].format(**fill)


def check_step(step, i, ctx):
    """One step by rules 1 to 8 -> a dict (see the module's words). `ctx` carries what earlier steps took (seen, changes)."""
    t = step.thing
    out = {'n': step.n, 'verb': step.verb, 'handle': step.handle, 'thing': t.id if t else '', 'title': t.title if t else '',
           'kind': t.kind if t else '', 'words': step.words, 'column': step.column.name if step.column else '',
           'column_label': step.column.label if step.column else '', 'value': step.value, 'state': OK, 'why': [], 'said': [],
           'candidates': [], 'rule': '', 'checks': []}

    def _say(words):
        if words not in out['said']:out['said'].append(words)

    def refuse(code, **more):
        out['state'] = REFUSED;out['why'].append(code);_say(_words(code, step, **more));out['checks'].append((code, False))

    def unsettle(code, candidates=(), **more):
        if out['state'] != REFUSED:out['state'] = UNSETTLED
        out['why'].append(code);_say(_words(code, step, **more));out['checks'].append((code, False))
        out['candidates'] = [c.handle for c in candidates]
    if step.verb == 'tidy':
        if 'tidy' in ctx['seen']:refuse('TWICE')
        ctx['seen'].add('tidy');out['reading'] = becomes(step, i);out['checks'].append(('shape', True))
        return out
    # 1 · shape
    key = (step.verb, t.id, out['column'], step.value)
    if key in ctx['seen']:refuse('TWICE')
    ctx['seen'].add(key)
    # 2 · registry
    from . import understand
    row = understand.VERBS[step.verb]
    if t.kind not in row['applies']:refuse('NOT_FOR_THIS')
    value = ''
    if step.verb in ('what if', 'set') and step.column is not None:value = _value_text(step.value, step.column.unit)
    if out['state'] == OK and row['becomes'] == 'acts':
        for name, args in acts(step, value or step.value):
            ok, why = desk_acts.model_may(name, args)
            if not ok:refuse('NOT_IN_TABLE', why=why);break
            try:desk_acts.check(name, args)
            except desk_acts.Refusal as refusal:refuse('ARGUMENTS', why=refusal.words);break
    # 3 · records
    if i.thing(t.handle) is not t:refuse('NOT_LISTED')            # never: the parser gives only listed things
    if i.fresh is not None:
        now = i.fresh() or {}
        if now.get(t.id) != t.version:refuse('CHANGED')
    if step.verb == 'compare' and (not t.sibling or i.world is None or not i.world.pair(t.title)):refuse('NO_SIBLING')
    if step.verb in ('what if', 'set') and step.column is not None and not (step.column.number and step.column.cell):refuse('NOT_A_NUMBER')
    if step.verb == 'within' and not _goals_over(t, i, step.column):refuse('NO_GOAL')
    # 4 · your words
    span, why = locate(i.text, step.words, i)
    if why:refuse(why)
    else:out['at'] = list(span)
    if step.value:
        vspan, vwhy = locate(i.text, step.value, i)
        if vwhy:refuse(vwhy, words=step.value)
        else:out['value_at'] = list(vspan)
    # 5 · naming (only words that are yours, of a thing the verb fits)
    if out['state'] == OK and step.verb == 'total':          # 0.8.7 B8: a total names its sheet and its rows (total_plan)
        _total_check(step, i, out, refuse, unsettle)
    elif out['state'] == OK:
        state, code, candidates, rule = naming(step, i)
        if state == OK:
            out['rule'] = RULE_WORDS.get(rule, '') if rule in ('names', 'current', 'selected') else ''
            day = (getattr(i, 'agreed', None) or {}).get(reading.said_key(step.words)) if rule == 'names' else ''
            if day:out['rule'] = '%s %s' % (RULE_WORDS['names'], day)          # 0.8.7 B5: 'your words, agreed 20 Nov'
        else:
            other = candidates[0].title if candidates else ''
            unsettle(code, candidates, other=other, others=' and '.join('“%s”' % c.title for c in candidates))
    # 6 · a change
    if step.verb == 'set':
        if not change_words(i):refuse('NO_CHANGE_WORD')
        if ctx['changes']:refuse('ONE_CHANGE')
    if step.verb in ('what if', 'set') and step.column is not None and step.value:
        m = VALUE.fullmatch(step.value)
        if not m:refuse('NOT_A_VALUE')
        elif m.group(2) and m.group(2) != step.column.unit:refuse('UNIT')
    if step.verb == 'count' and step.column is not None and step.value:
        if step.value.casefold() not in {v.casefold() for v in step.column.values}:unsettle('NOT_IN_COLUMN')
    # 8 · what you said Not that to
    if out['state'] == OK and (reading.said_key(i.text), step.verb, t.id) in set(map(tuple, i.refused)):
        unsettle('YOU_SAID_NOT_THAT', [x for x in i.things if x is not t and x.base == t.base])
    if out['state'] == OK:
        out['reading'] = becomes(step, i, value)
        out['meant'] = t.title
        if step.verb == 'compare':
            out['pair'] = list(out['reading']['goals'][0]['params'].values())
            out['meant'] = '%s with %s' % (out['pair'][1], out['pair'][0])
        if step.verb == 'within':out['statements'] = [g['statement'] for g in out['reading']['goals']]
        if step.column is not None and step.column.value:out['column_now'] = ('%s %s' % (step.column.value, step.column.unit)).strip()
        if step.value:out['value_meant'] = '%s, as %s' % (step.value, step.column.label) if step.column else step.value
        if step.verb == 'set':
            ctx['changes'] += 1
            out['proposal'] = _proposal(step, i, out, value)
            out['asks'] = not out['proposal']['hers_at']
            if out['proposal']['hers_at']:
                refuse('WOULD_NOT_ASK');out.pop('reading', None);out.pop('proposal', None)
        if step.verb == 'total' and out['state'] == OK:_total_ok(out)          # 0.8.7 B8: her words for the total
        out['checks'].append(('all', out['state'] == OK))
    return out


def _proposal(step, i, out, value):
    """The change as a proposal (stacy_hand.proposal): every argument with its origin, none the model; basis model_pick."""
    t = step.thing;col = step.column
    args = {'sheet': {'value': t.id, 'origin': {'kind': 'RECORD', 'id': t.id, 'rev': t.version}},
            'cell': {'value': col.cell, 'origin': {'kind': 'RECORD', 'id': t.id, 'rev': t.version, 'cell': col.cell}},
            'value': {'value': value, 'origin': {'kind': 'OWNER_WORDS', 'start': out['value_at'][0], 'end': out['value_at'][1],
                                                  'text': i.text[out['value_at'][0]:out['value_at'][1]]}}}
    from .understand import says
    return stacy_hand.proposal('field.set', args, stacy_hand.MODEL_PICK, says({**out, 'value': step.value}))


# -- composing 0.8.6's answer_check ---------------------------------------------------------------------------------------------
def _compose(results, i, checks):
    """The OK steps that end in desk goals, put to answer_check.check_pick as one brief: licence, coverage, joint plan."""
    desk = [r for r in results if r['state'] == OK and (r.get('reading') or {}).get('frame') == 'DESK' and r['verb'] != 'tidy']
    if not desk or i.world is None:return
    clauses, stems = brief_mod._clauses(i.text)
    titles = set(i.world.titles())
    options = []
    for n, r in enumerate(desk, 1):
        found = r['reading']
        names = frozenset(reading.stems(r['words']) | reading.stems(r.get('meant') or ''))
        named_by = tuple(k for k, s in enumerate(stems) if s & names)
        options.append(brief_mod.Option(n, r['title'], found, 'navigates', names, frozenset(), named_by, '', reading.authority_free(found)))
    world = i.world
    planned = all(v in titles for r in desk for g in r['reading']['goals'] for v in g['params'].values())
    b = brief_mod.Brief(hand_words.plain(i.text), clauses, stems, tuple(options), (), world if planned else None)
    verdict = answer_check.check_pick(b, tuple(range(1, len(options) + 1)))
    for name, passed, detail in verdict.checks:checks.append(('answer_check %s' % name, passed, detail))
    if verdict.state == 'TAKEN':return
    kept = set(verdict.value or ()) if verdict.state == 'TRIMMED' else set()
    for n, r in enumerate(desk, 1):
        if verdict.state == 'TRIMMED' and n in kept:continue
        code = 'UNLICENSED' if verdict.state == 'TRIMMED' or 'UNLICENSED' in verdict.why else 'NO_JOINT_PLAN'
        why = next((d for nm, p, d in verdict.checks if not p), '')
        r['state'] = REFUSED;r['why'].append(code);r['said'].append(WHY[code].format(title=r['title'], why=why));r.pop('reading', None)


# -- the whole reading ------------------------------------------------------------------------------------------------------------
def check(found, i):
    """A READ answer (understand.Reading) against the desk and your words -> turns.Verdict, basis model_pick."""
    checks = []
    if found.kind == 'talk':
        return Verdict('TAKEN', {'kind': 'talk', 'steps': [], 'readings': [], 'question': None, 'refused': []}, (), (('kind', True, 'talk'),))
    if found.kind in ('unclear', 'app'):
        why = 'APP' if found.kind == 'app' else 'UNCLEAR'
        return Verdict('REFUSED', {'kind': found.kind, 'steps': [], 'readings': [], 'question': None, 'refused': []}, (why,),
                       (('kind', False, found.kind),))
    ctx = {'seen': set(), 'changes': 0}
    results = [check_step(s, i, ctx) for s in found.steps]
    _compose(results, i, checks)
    for r in results:
        for code, passed in r.pop('checks'):checks.append(('step %d %s' % (r['n'], code), passed, ' '.join(r['said'])[:200]))
    readings = [r['reading'] for r in results if r['state'] == OK]
    refused = [{'n': r['n'], 'why': r['why'], 'words': ' '.join(r['said'])} for r in results if r['state'] == REFUSED]
    unsettled = [r for r in results if r['state'] == UNSETTLED]
    value = {'kind': 'desk', 'line': found.line, 'steps': results, 'readings': readings, 'question': None, 'refused': refused, 'held': []}
    if unsettled:
        value['held'] = readings;value['readings'] = [];value['question'] = question(unsettled[0], i)
        return Verdict('UNSETTLED', value, tuple(unsettled[0]['why']), tuple(checks))
    if readings:
        return Verdict('TRIMMED' if refused else 'TAKEN', value, ('TRIMMED',) if refused else (), tuple(checks))
    return Verdict('REFUSED', value, tuple(refused[0]['why']) if refused else ('NOTHING',), tuple(checks))


def question(r, i):
    """The one question an unsettled step leaves (B4's card shows it): its candidates as options, in the order the fixed
    rules rank them, each with the reading it would be; with no candidate, her guesses."""
    from . import understand
    if (r.get('rows_question') or {}).get('options'):return _rows_question(r)     # 0.8.7 B8: which rows his words name
    options = []
    for handle in r['candidates']:
        t = i.thing(handle)
        if t is None or (r['verb'] in understand.VERBS and understand.VERBS[r['verb']]['applies'] and t.kind not in understand.VERBS[r['verb']]['applies']):continue
        col = None
        if r['column']:
            col = t.column(r['column']) or next((c for c in t.columns if c.label == r['column_label']), None)
            if col is None:continue                       # a candidate without that column is no answer to this question
        if r['verb'] == 'compare' and not t.sibling:continue
        step = understand.Step(r['n'], r['verb'], t.handle, t, r['words'], col, r['value'] if col is not None else '')
        try:found = becomes(step, i, _value_text(r['value'], ''))
        except Exception:  # noqa: BLE001 - a candidate the desk cannot make a reading of is not offered
            continue
        options.append({'n': len(options) + 1, 'words': '“%s”' % t.title, 'thing': t.id, 'reading': found})
    if not options:
        return {'step': r['n'], 'words': ' '.join(r['said']) + ' Did you mean one of these?', 'why': r['why'],
                'options': [{'n': n, 'words': w, 'reading': f} for n, w, f in understand.guesses(i)]}
    return {'step': r['n'], 'why': r['why'], 'said': ' '.join(r['said']),
            'words': understand.WORDS['question'].format(words=r['words'], options=' or '.join(o['words'] for o in options)),
            'options': options}


# == 0.8.7 B8 · a total over one of your sheets: your words for its rows, exact or asked; a period by the dates core =======
# Design 2.5 and 7.3 item 4. "how much is still to pay this month?" reads as `desk|total D6 "still to pay" amount "this
# month"`. The checker settles each part by fixed rules, with no model and no float:
#   the sheet     his words name it by its title (or his agreed name); words that do not are words for its ROWS. A word
#                 another listed sheet's title shares more makes it B3's NAMES_ANOTHER question.
#   the column    the number column he named, else the one number column that is not a low or a high end; else he is asked.
#   the rows      his words (the words slot, less the sheet's own title words, or the value slot) against the values of the
#                 sheet's text columns: EXACT (the whole value, case and punctuation between words aside) takes them, and the
#                 card names the rule; a HALF match (a shared word: "rent" for "Rent, Demo Lettings", "due" for "due
#                 2026-11-22") is never taken quietly: he is asked, with those values; NO match is a BIND: the model is asked
#                 which of up to 8 listed values (ranked by spelling) his words mean, its answer shown for Do / Not that
#                 (understand.BIND); with no model, or a late, refused or "none" answer, the same values are his one question.
#   the period    value words such as "this month", "in October", "since September" go to the 0.8.5 dates core's calendar
#                 (math_dates.add_months) from this computer's clock, said in her words; rows are kept by the sheet's date
#                 column, or, with none, by the month its title names ("Household November"); with neither she says so.
#   the amounts   each row's exact decimal, or its low to high when the sheet holds both ends (the owner's own range), handed
#                 to the maths core (math_money) by understand.total(): the answer is the core's, with its receipt.
from datetime import date as _date, timedelta as _timedelta

LOW_WORDS = frozenset(('low', 'lowest', 'min', 'minimum', 'least'))
HIGH_WORDS = frozenset(('high', 'highest', 'max', 'maximum', 'most'))
TOTAL_WORDS = frozenset(('total', 'totals', 'sum', 'altogether', 'overall', 'much', 'whole', 'add', 'up'))
ISO_DAY = re.compile(r'\d{4}-\d{2}-\d{2}')
ROWS_MOST = 60               # rows one total adds (the expression stays well under the core's 1,000 characters)
RANGES_MOST = 8              # rows with a low and a high end (math_money's givens)
BIND_MOST = 8                # values a BIND lists (design 3.3)
ASK_MOST = 3                 # values on her one question (with "all of these" or "all its rows": four buttons)
WHY.update({
    'NO_ROWS_HERE': '“{title}” has no rows to add up.',
    'WHICH_COLUMN': '“{title}” has more than one column of numbers: {columns}.',
    'HALF': '“{words}” is not exactly a value of “{title}”; it shares words with {values}.',
    'BIND': '“{words}” is not a value of “{title}”.',
    'NO_DATES': 'Nothing in “{title}” carries a date, so I cannot tell which of its rows are of {period}.',
    'OTHER_PERIOD': '“{title}” is for {month}, and “{value}” is {period}: none of its rows are of that time.',
    'TOO_MANY_ROWS': 'That is more than %d rows of “{title}” to add up in one answer.' % ROWS_MOST,
    'TOO_MANY_RANGES': 'More than %d rows of “{title}” have a low and a high end.' % RANGES_MOST,
})
RULE_WORDS.update({'bound_owner': 'your choice'})
WORDS_B8 = {
    'says': 'The total of {column} in “{title}”{rows}{period}',
    'all_rows': ', over all its rows',
    'rows': ', over the rows where {where}',
    'where': '{column} is {values}',
    'period': ', {period}',
    'notes': ' ({notes})',
    'clock': '{said}, by this computer’s clock',
    'by_title': '“{title}” is for {month}',
    'bound_model': 'I took “{words}” as {values} (the model’s reading of your words).',
    'bound_owner': 'I took “{words}” as {values} (your choice).',
    'option': '{column}: {value}',
    'all_these': 'All of these: {values}',
    'all_its_rows': 'All rows of “{title}”',
    'which_rows': 'Which rows of “{title}” did you mean by “{words}”: {options}?',
}


def _today(i):
    day = getattr(i, 'today', None)
    if isinstance(day, str):
        try:day = _date.fromisoformat(day)
        except ValueError:day = None
    return day if isinstance(day, _date) else _date.today()      # this computer's clock (the Kernel passes its own day)


def norm(text):
    """A value or your words, case and punctuation between words aside: 'Rent, Demo Lettings' -> 'rent demo lettings'."""
    return ' '.join(re.findall(r'[0-9a-z]+', str(text or '').casefold()))


def _exact_number(text):
    m = re.fullmatch(r'\s*([+-]?)(\d{1,12})(?:\.(\d{1,12}))?\s*', str(text or ''))
    if not m:return None
    n = Fraction(int(m.group(2))) + (Fraction(int(m.group(3)), 10 ** len(m.group(3))) if m.group(3) else 0)
    return -n if m.group(1) == '-' else n


def table(t, i):
    """A sheet as rows of cells: {'columns', 'rows' [{label: text}], 'labels' (a row's name), 'number', 'text', 'dates',
    'low', 'high', 'filled'}. A typed sheet by its own headings; a reviewed sheet as Parameter, Value, Unit and Conditions."""
    if t.kind == 'typed':
        columns = [c.label for c in t.columns]
        n = max((len(c.values) for c in t.columns), default=0)
        rows = [{c.label: (c.values[k] if k < len(c.values) else '').strip() for c in t.columns} for k in range(n)]
        labels = [r.get(columns[0], '') if columns else '' for r in rows]
    else:
        columns = ['Parameter', 'Value', 'Unit', 'Conditions']
        got = [r for r in getattr(i.lex, 'rows', ()) or () if r.sheet == t.id]
        rows = [{'Parameter': r.parameter.strip(), 'Value': r.value.strip(), 'Unit': r.unit.strip(), 'Conditions': r.conditions.strip()} for r in got]
        labels = [('%s %s' % (r['Parameter'], r['Conditions'])).strip() if ISO_DAY.fullmatch(r['Conditions']) else r['Parameter'] for r in rows]
    filled = {c: [r[c] for r in rows if r.get(c)] for c in columns}
    number = [c for c in columns if filled[c] and all(_exact_number(v) is not None for v in filled[c])]
    dates = next((c for c in columns if filled[c] and all(ISO_DAY.fullmatch(v) for v in filled[c])), '')
    text = [c for c in columns if filled[c] and c not in number and c != dates]
    low = next((c for c in number if norm(c) in LOW_WORDS), '')
    high = next((c for c in number if norm(c) in HIGH_WORDS), '')
    return {'columns': columns, 'rows': rows, 'labels': labels, 'number': number, 'text': text, 'dates': dates,
            'low': low if high else '', 'high': high if low else '', 'filled': filled}


def _month_end(first):
    from .math_dates import add_months
    return add_months(first, 1)[0] - _timedelta(days=1)


def _month_words(first):
    from .math_dates import MONTHS
    return '%s %d' % (MONTHS[first.month - 1], first.year)


def _day_words(day):
    from .math_dates import MONTHS
    return '%d %s %d' % (day.day, MONTHS[day.month - 1], day.year)


def _month_number(word):
    """1 to 12 for a month's name or its first three letters ('sept' too); 0 otherwise."""
    from .math_dates import MONTHS
    w = str(word or '').casefold()
    for n, name in enumerate(MONTHS, 1):
        if w in (name.casefold(), name.casefold()[:3]) or (n == 9 and w == 'sept'):return n
    return 0


def period(text, today):
    """Your words for a time, as the dates core's calendar counts it: {'start', 'end' (ISO days, both inside), 'words' (her
    words: 'November 2026'), 'said' (yours), 'clock' (whether today's date decided it)}; None when they are not a period.
    A month named without a year is its latest one not after today's month (her words say which year)."""
    from .math_dates import add_months
    said = ' '.join(str(text or '').split());s = norm(said)
    s = re.sub(r'^(?:in|during|for|of|over)\s+', '', s)
    this = _date(today.year, today.month, 1)

    def month(first, clock):
        return {'start': first.isoformat(), 'end': _month_end(first).isoformat(), 'words': _month_words(first), 'phrase': 'in ' + _month_words(first),
                'said': said, 'clock': clock}
    m = re.fullmatch(r'(this|last|previous|next) month', s)
    if m:return month(add_months(this, {'this': 0, 'last': -1, 'previous': -1, 'next': 1}[m.group(1)])[0], True)
    if s == 'this year':
        return {'start': _date(today.year, 1, 1).isoformat(), 'end': _date(today.year, 12, 31).isoformat(), 'words': str(today.year), 'phrase': 'in %d' % today.year,
                'said': said, 'clock': True}
    m = re.fullmatch(r'(?:since|from) ([a-z]+)(?: (\d{4}))?', s)
    if m and _month_number(m.group(1)):
        n = _month_number(m.group(1))
        first = _date(int(m.group(2)) if m.group(2) else (today.year if n <= today.month else today.year - 1), n, 1)
        if first > today:return None
        return {'start': first.isoformat(), 'end': today.isoformat(), 'words': '%s to %s' % (_day_words(first), _day_words(today)),
                'phrase': 'from %s to %s' % (_day_words(first), _day_words(today)),
                'said': said, 'clock': True}
    m = re.fullmatch(r'([a-z]+)(?: (\d{4}))?', s)
    if m and _month_number(m.group(1)):
        n = _month_number(m.group(1))
        if m.group(2):return month(_date(int(m.group(2)), n, 1), False)
        return month(_date(today.year if n <= today.month else today.year - 1, n, 1), True)
    return None


def title_month(title):
    """(month, year or None) when a sheet's title names one month ('Household November'), else None."""
    from .math_dates import MONTHS
    found = {n for n, name in enumerate(MONTHS, 1) if re.search(r'\b%s\b' % name, title or '', re.I)}
    if len(found) != 1:return None
    year = re.search(r'\b(\d{4})\b', title or '')
    return found.pop(), (int(year.group(1)) if year else None)


def row_words(words, t):
    """Your words for rows: the words less the sheet's own title words and the words of adding up ('total', 'much'), with
    the small words at either end taken off; '' when they only name the sheet."""
    toks = re.findall(r"[A-Za-z0-9]+(?:[.'’-][A-Za-z0-9]+)*", str(words or ''))
    keep = [w for w in toks if reading.stem(w.lower()) not in t.stems and w.casefold() not in TOTAL_WORDS]
    while keep and keep[0].casefold() in reading.STOP:keep.pop(0)
    while keep and keep[-1].casefold() in reading.STOP:keep.pop()
    return ' '.join(keep)


def _distinct(tab, column):
    seen = []
    for r in tab['rows']:
        v = r.get(column, '')
        if v and v not in seen:seen.append(v)
    return seen


def match(text, tab):
    """([(column, value)] equal to your words, [(column, value)] sharing a word with them) over the sheet's text columns."""
    key, stems = norm(text), reading.stems(text)
    exact, half = [], []
    for c in tab['text']:
        for v in _distinct(tab, c):
            if norm(v) == key:exact.append((c, v))
            elif stems & reading.stems(v):half.append((c, v))
    return exact, half


def _grams(text):
    s = ' %s ' % norm(text)
    return {s[k:k + 3] for k in range(len(s) - 2)}


def listed(text, tab):
    """The values a BIND lists (at most BIND_MOST), ranked by spelling against your words (shared three-letter pieces, then
    the sheet's own order): the values of the columns that sort its rows (a value repeats), else of every short text column."""
    sorting = [c for c in tab['text'] if len(_distinct(tab, c)) < len(tab['filled'][c])]
    columns = sorting or [c for c in tab['text'] if all(len(v.split()) <= 4 for v in tab['filled'][c])]
    mine = _grams(text);out = []
    for ci, c in enumerate(columns):
        for vi, v in enumerate(_distinct(tab, c)):out.append((-len(mine & _grams(v)), ci, vi, c, v))
    return [(c, v) for _, _, _, c, v in sorted(out)[:BIND_MOST]]


def _amount_column(step, t, tab):
    """(column, extra where, code, fill): the number column a total adds up."""
    if t.kind != 'typed':
        if 'Value' not in tab['number']:return '', None, 'NOT_A_NUMBER', {'label': 'Value'}
        if step.column is not None:
            return 'Value', {'pairs': [['Parameter', step.column.label]], 'words': step.column.label, 'by': 'column'}, '', {}
        return 'Value', None, '', {}
    if step.column is not None:
        if step.column.label not in tab['number']:return '', None, 'NOT_A_NUMBER', {}
        return step.column.label, None, '', {}
    cands = [c for c in tab['number'] if c not in (tab['low'], tab['high'])]
    if len(cands) != 1:
        full = [c for c in cands if len(tab['filled'][c]) == len(tab['rows'])]
        if len(full) == 1:return full[0], None, '', {}
        if not cands:return '', None, 'NOT_A_NUMBER', {'label': 'any column'}
        return '', None, 'WHICH_COLUMN', {'columns': ', '.join(cands), 'choices': cands}
    return cands[0], None, '', {}


def _inside(p, title):
    """(whether the month the title names lies in the period, the month in words) for a sheet with no date column; (None, '')
    when the title names no one month."""
    from .math_dates import MONTHS
    tm = title_month(title)
    if tm is None:return None, ''
    n, year = tm
    start, end = _date.fromisoformat(p['start']), _date.fromisoformat(p['end'])
    words = '%s %d' % (MONTHS[n - 1], year) if year else MONTHS[n - 1]
    for y in ([year] if year else range(start.year, end.year + 1)):
        first = _date(y, n, 1)
        if first <= end and _month_end(first) >= start:return True, words
    return False, words


def _values_words(values):
    values = list(values)
    return values[0] if len(values) == 1 else ', '.join(values[:-1]) + ' or ' + values[-1]


def _where_words(where):
    out = []
    for w in where:
        cols = list(dict.fromkeys(c for c, _ in w['pairs']))
        out.append(' or '.join(WORDS_B8['where'].format(column=c, values=_values_words([v for cc, v in w['pairs'] if cc == c])) for c in cols))
    return ' and '.join(out)


def total_plan(step, i, force=None):
    """The total a step reads, settled by the rules above: {'state' OK, UNSETTLED or REFUSED, 'code', 'fill' (the words of
    why), 'candidates' (Things), 'ask' (what his one question, or the BIND, is about), 'reading' (the 0.8.6 reading, route
    TOTAL)}. `force` settles a part the way an option of her question would: {'column': label}, {'rows': {key: {'column',
    'values', 'by'}}} or {'all': key} (his words name the whole sheet)."""
    force = force or {}
    t = step.thing;tab = table(t, i)

    def stop(state, code, candidates=(), ask=None, **fill):
        return {'state': state, 'code': code, 'fill': fill, 'candidates': list(candidates), 'ask': ask, 'reading': None}
    if not tab['rows']:return stop(REFUSED, 'NO_ROWS_HERE')
    if force.get('column'):
        step = step.__class__(step.n, step.verb, step.handle, step.thing, step.words,
                              next((c for c in t.columns if c.label == force['column']), step.column), step.value)
    column, extra, code, fill = _amount_column(step, t, tab)
    if code == 'WHICH_COLUMN':
        return stop(UNSETTLED, code, ask={'kind': 'column', 'choices': fill.pop('choices')}, **fill)
    if code:return stop(REFUSED, code, **fill)
    where = [extra] if extra else []
    groups = []
    # the sheet, and his words for its rows
    agreed = i.names.get(reading.said_key(step.words))
    if agreed and agreed != t.id:
        other = next((x for x in i.things if x.id == agreed), None)
        return stop(UNSETTLED, 'NAMES_ANOTHER', [other] if other else [], other=other.title if other else '')
    if not agreed:
        from . import understand
        applies = understand.VERBS['total']['applies']
        w = reading.stems(step.words);mine = len(w & t.stems)
        better = [x for x in i.things if x is not t and x.kind in applies and len(w & x.stems) > mine]
        if better:
            most = max(len(w & x.stems) for x in better);top = [x for x in better if len(w & x.stems) == most]
            return stop(UNSETTLED, 'NAMES_ANOTHER', top, other=top[0].title)
        text = row_words(step.words, t)
        if text:groups.append(('words', text, step.words))
        elif not mine:return stop(UNSETTLED, 'NOT_NAMED')
    when = None
    if step.value:
        when = period(step.value, _today(i))
        if when is None:groups.append(('value', row_words(step.value, t) or step.value, step.value))
    # each group of his words for rows: bound (the model's BIND, or his click), exact, or asked
    for slot, text, said in groups:
        key = norm(text)
        if force.get('all') == key:continue
        bound = (force.get('rows') or {}).get(key) or (getattr(i, 'bound', None) or {}).get(key)
        if bound:
            where.append({'pairs': [[bound['column'], v] for v in bound['values']], 'words': said, 'by': bound.get('by', 'model')});continue
        exact, half = match(text, tab)
        if exact:
            where.append({'pairs': [list(p) for p in exact], 'words': said, 'by': 'exact'});continue
        if half:
            return stop(UNSETTLED, 'HALF', ask={'kind': 'half', 'key': key, 'words': said, 'slot': slot, 'pairs': half},
                        words=said, values=_values_words(['“%s”' % v for _, v in half[:ASK_MOST]]))
        values = listed(text, tab)
        if not values:return stop(UNSETTLED, 'NOT_NAMED', words=said)
        return stop(UNSETTLED, 'BIND', ask={'kind': 'bind', 'key': key, 'words': said, 'slot': slot, 'pairs': values}, words=said)
    # the rows his words name, in the period they name
    keep = list(range(len(tab['rows'])))
    for w in where:
        keep = [k for k in keep if any(tab['rows'][k].get(c, '') == v for c, v in w['pairs'])]
    if when is not None:
        if tab['dates']:
            keep = [k for k in keep if tab['rows'][k].get(tab['dates']) and when['start'] <= tab['rows'][k][tab['dates']] <= when['end']]
            when['by'] = 'dates'
        else:
            inside, month_words = _inside(when, t.title)
            if inside is None:return stop(REFUSED, 'NO_DATES', period='“%s”' % step.value)
            if not inside:return stop(REFUSED, 'OTHER_PERIOD', month=month_words, period=when['words'])
            when['by'] = 'title';when['month'] = month_words
    rows, skipped = [], []
    for k in keep:
        cells = tab['rows'][k];amount = cells.get(column, '')
        if _exact_number(amount) is None:
            skipped.append(tab['labels'][k]);continue
        row = {'label': tab['labels'][k], 'amount': amount}
        if tab['low'] and tab['high'] and column not in (tab['low'], tab['high']):
            lo, hi = cells.get(tab['low'], ''), cells.get(tab['high'], '')
            if _exact_number(lo) is not None and _exact_number(hi) is not None and _exact_number(lo) <= _exact_number(hi):
                row.update(lo=lo, hi=hi, low=tab['low'], high=tab['high'])
        rows.append(row)
    if len(rows) > ROWS_MOST:return stop(REFUSED, 'TOO_MANY_ROWS')
    if sum(1 for r in rows if 'lo' in r) > RANGES_MOST:return stop(REFUSED, 'TOO_MANY_RANGES')
    said_when = ''
    if when:
        notes = [WORDS_B8['clock'].format(said=when['said'])] if when['clock'] else []
        if when.get('by') == 'title':notes.append(WORDS_B8['by_title'].format(title=t.title, month=when['month']))
        said_when = WORDS_B8['period'].format(period=when['phrase']) + (WORDS_B8['notes'].format(notes='; '.join(notes)) if notes else '')
    says = WORDS_B8['says'].format(column=column, title=t.title, period=said_when,
                                   rows=WORDS_B8['rows'].format(where=_where_words(where)) if where else WORDS_B8['all_rows'])
    found = {'frame': 'TOTAL', 'route': 'TOTAL', 'verb': 'total', 'thing': {'id': t.id, 'title': t.title}, 'column': column,
             'rows': rows, 'skipped': skipped, 'where': where, 'period': when, 'words': step.words, 'says': says}
    return {'state': OK, 'code': '', 'fill': {}, 'candidates': [], 'ask': None, 'reading': found}


def _total_check(step, i, out, refuse, unsettle):
    """Rules 3 and 5 for a total: total_plan's verdict on the step's dict; an unsettled part leaves her one question about it
    (rows_question) and, when no value matched at all, what a BIND would ask the model (bind)."""
    plan = total_plan(step, i)
    if plan['state'] == OK:
        by = [w['by'] for w in plan['reading']['where']]
        out['rule'] = RULE_WORDS['value'] if 'exact' in by else RULE_WORDS['bound_owner'] if 'owner' in by else ''
        return
    fill = dict(plan['fill'])
    if plan['state'] == REFUSED:refuse(plan['code'], **fill);return
    cands = plan['candidates']
    if plan['code'] == 'NAMES_ANOTHER':fill.setdefault('others', ' and '.join('“%s”' % c.title for c in cands))
    unsettle(plan['code'], cands, **fill)
    ask = plan['ask']
    if not ask:return
    t = step.thing;options = []
    if ask['kind'] == 'column':
        for c in ask['choices'][:ASK_MOST + 1]:
            got = total_plan(step, i, {'column': c})
            if got['state'] == OK:options.append({'words': '“%s”' % c, 'reading': got['reading']})
    else:
        pairs = ask['pairs'];key = ask['key']
        if ask['kind'] == 'half' and len(pairs) > 1 and len({c for c, _ in pairs}) == 1:
            got = total_plan(step, i, {'rows': {key: {'column': pairs[0][0], 'values': [v for _, v in pairs], 'by': 'owner'}}})
            if got['state'] == OK:
                options.append({'words': WORDS_B8['all_these'].format(values=_values_words([v for _, v in pairs])), 'reading': got['reading']})
        for c, v in pairs[:ASK_MOST]:
            got = total_plan(step, i, {'rows': {key: {'column': c, 'values': [v], 'by': 'owner'}}})
            if got['state'] == OK:options.append({'words': WORDS_B8['option'].format(column=c, value=v), 'reading': got['reading']})
        if ask['kind'] == 'bind' and ask['slot'] == 'words':
            got = total_plan(step, i, {'all': key})
            if got['state'] == OK:options.append({'words': WORDS_B8['all_its_rows'].format(title=t.title), 'reading': got['reading']})
        if ask['kind'] == 'bind':
            out['bind'] = {'key': key, 'words': ask['words'], 'title': t.title, 'listed': [list(p) for p in pairs]}
    out['rows_question'] = {'words': ask.get('words') or step.words, 'title': t.title, 'options': options[:ASK_MOST + 1]}


def _total_ok(out):
    """Her words for an OK total: the card's sentence (total_says), what your words were read as, and, when the rows came
    from a BIND or from your click, the sentence that says whose reading it was."""
    found = out.get('reading') or {}
    out['total_says'] = found.get('says') or ''
    when = found.get('period')
    if when:out['value_meant'] = when['words']
    for w in found.get('where') or ():
        if w['by'] in ('model', 'owner'):
            out.setdefault('bound_said', []).append(WORDS_B8['bound_%s' % w['by']].format(
                words=w['words'], values=_values_words([v for _, v in w['pairs']])))
        if w['words'] == out['words']:
            out['meant'] = _where_words([w]);out['rows_from_words'] = True
        elif w['words'] == out.get('value'):out['value_meant'] = _where_words([w])


def _rows_question(r):
    """Her one question about which rows his words name: the values (and "all of these" or "all its rows"), never guessed."""
    q = r['rows_question']
    options = [{'n': n, 'words': o['words'], 'reading': o['reading']} for n, o in enumerate(q['options'], 1)]
    return {'step': r['n'], 'why': r['why'], 'said': ' '.join(r['said']), 'bind': r.get('bind'),
            'words': WORDS_B8['which_rows'].format(title=q['title'], words=q['words'], options='; '.join(o['words'] for o in options)),
            'options': options}
# == end 0.8.7 B8 ==========================================================================================================
