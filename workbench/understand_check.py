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
    if out['state'] == OK:
        state, code, candidates, rule = naming(step, i)
        if state == OK:out['rule'] = RULE_WORDS.get(rule, '') if rule in ('names', 'current', 'selected') else ''
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
