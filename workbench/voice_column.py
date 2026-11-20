"""Her voice floor in her column (0.8.7 W7, the window wiring): her answers said through the fact sheet and the gate.

0.8.7 C4 built her voice floor (voice_facts cuts a receipt into slots; voice_gate checks a frame, fills it and checks the
words again), but her column still said 0.8.6's words. Here the column's panel (mind_panel_qt) asks, beside its own reads,
for the same answers said through the floor, and puts them where 0.8.6's templates said them:

  Why          the proof's maths line ("45 ms is at most 40 ms: does not hold, 5 ms over (the maths, receipt ...)") is said
               as the fact sheet says it ("No. Startup duration is over Rev B's 40 ms limit by 5 ms; ..."); its state word
               and its place in the proof stay, and where it came from names the receipt.
  Either way   each way of the goal (each revision, each row a symbol could read) is said through the floor, one line a
               way ("Rev A applies: Yes. ..."), under the head of 0.8.6's sentence; "cannot tell" is the floor's own
               (whose tolerance reaches both sides of which limit, where it would not hold, where it holds, what keeps).
  A period     'period:§ 12(a)' with a day paid or a ledger sheet: the period's fact sheet (its last days, the credit).

Only plain words of hers come back as text. A frame the model worded would come back as a stored model answer beside the
mark model_marks_qt.place expects ('WORDED'), never as text: her column's plain renderer refuses model words.

**With every 0.8.7 switch off, her words stay 0.8.6's** (design 2.12: with all off, Kas is exactly 0.8.6): the read says
it is off and the panel shows 0.8.6's words untouched. The floor itself asks no model either way (model_calls 0).

Kernel operation (one block in engineering_kernel.py and engineering_cli.py, commented 0.8.7 W7):
  voice.say  {id, choose?, at?, reading?, on?, sheet?}   read   a goal's ways (or a finding's, or a period's) said through
                                                                her voice floor; nothing written, no model
Pure apart from the reads it makes: no Qt, no float, no clock in what is said.
"""
from __future__ import annotations

import re

from . import mind_words

VERSION = 'voice-column/1'
RECEIPT = re.compile(r'\(the maths, receipt ([0-9a-f]{12})\)')
REV = re.compile(r'\bRev\.?\s*([A-Z0-9]{1,3})\b')

# Her words here (templates, swept with the rest of hers: no digit in the fixed words, nothing but a slot carries a number)
WORDS = {
    'way': '{value} applies: {said}',
    'way_plain': '{said}',
    'from_maths': 'the maths, receipt {receipt}',
}
NUMBERS = {'way': {'said': 'voice.say: the way said through her voice floor (voice_gate.speak of voice_facts.math_sheet)',
                   'value': 'voice.say: the way\'s choice (either_way.judge_goal ways[].choice)'},
           'way_plain': {'said': 'voice.say: the way said through her voice floor (voice_gate.speak of voice_facts.math_sheet)'},
           'from_maths': {'receipt': 'field.why: the maths line\'s receipt'}}
mind_words.register('voice_column', WORDS, kind='sentence', numbers=NUMBERS)


def switched_on(kernel):
    """Whether any 0.8.7 switch is on (the owner's, or the defaults): with every one off, her words stay 0.8.6's."""
    from . import turns
    try:return any(turns.stored_switches(kernel).values())
    except Exception:  # noqa: BLE001 - no settings to read: the defaults, which are on
        return any(turns.SWITCHES.values())


# -- the labels a fact sheet reads: each symbol's name in the desk's words, and whose limit it is -----------------------------
def _name(ref, symbol):
    words = str((ref or {}).get('parameter') or symbol.replace('_', ' ')).strip()
    if len(words) > 1 and not words[:2].isupper():words = words[:1].lower() + words[1:]
    return words


def _owner(way, found):
    """Whose limit: the revision this way reads ('Rev B'), from the way's choice, your word, the finding or the question."""
    choice = way.get('choice') or {}
    if choice.get('revision'):return str(choice['revision'])
    receipt = found.get('receipt') or {}
    for said in ((receipt.get('word') or {}).get('name'), receipt.get('named'), receipt.get('asked')):
        if said:return str(said)
    for ref in (way.get('bound') or {}).values():
        m = REV.search(str(ref.get('title') or ''))
        if m:return 'Rev ' + m.group(1)
    return ''


def labels(goal, way, found):
    """{symbol: {'name', 'owner'?}} for voice_facts.math_sheet."""
    out = {sym: {'name': _name(ref, sym)} for sym, ref in (goal.get('cells') or {}).items()}
    owner = _owner(way, found)
    for sym, role in (goal.get('roles') or {}).items():
        if role == 'limit' and owner:out.setdefault(sym, {'name': sym.replace('_', ' ')})['owner'] = owner
    return out


def _value(way, found):
    choice = way.get('choice') or {}
    return ' · '.join(str(v) for v in choice.values()) or _owner(way, found)


def _spoken(sheet):
    """(said, mark, record): her plain words as text, or a model's worded frame as its stored record with its mark."""
    from . import voice_gate
    from .model_words import Marked
    got = voice_gate.speak(sheet)
    text = got.get('text')
    if isinstance(text, Marked):
        from .model_words import ModelSaid
        return {'model_said': text.text, 'kind': 'FRAME'}, 'WORDED', got
    if not isinstance(text, str) and text is not None:
        text = None
    return text, '', got


def _receipt_of(record):
    from .reasons import _receipt
    return _receipt({'state': record.get('state'), 'result': record.get('result') or {}})[:12]


# -- the read -------------------------------------------------------------------------------------------------------------------
def say(kernel, principal, args):
    """voice.say: {'id', 'on', 'subject', 'form', 'ways': [{'choice', 'value', 'state', 'answer', 'receipt', 'heading',
    'said' (text, or a stored model answer), 'mark', 'source', 'frame_key', 'shape', 'defect', 'why'}], 'model_calls': 0}."""
    from . import either_way, voice_facts
    ident = str(args['id']).strip()
    out = {'id': ident, 'on': switched_on(kernel), 'subject': '', 'form': '', 'ways': [], 'model_calls': 0, 'version': VERSION}
    if not out['on']:
        out['why'] = 'SWITCHED_OFF'
        return out
    if ident.startswith('period:'):
        found = either_way.period_ways(kernel, principal, ident[7:].strip() or None, on=args.get('on'), sheet=args.get('sheet'))
        out.update(subject=found['period']['clause'], form=found.get('form', ''))
        try:sheet = voice_facts.period_sheet(found)
        except (ValueError, KeyError, TypeError) as exc:
            out['ways'].append({'choice': {}, 'value': '', 'state': found.get('state'), 'said': None, 'why': str(exc)[:200]})
            return out
        said, mark, got = _spoken(sheet)
        out['ways'].append({'choice': {}, 'value': '', 'state': sheet.state, 'heading': got['heading'], 'said': said, 'mark': mark,
                            'source': got['source'], 'frame_key': got['frame_key'], 'shape': got['shape'], 'defect': got['defect']})
        return out
    goal, goal_id, named, desk = either_way.goal_of(kernel, principal, ident)
    choose, at, readings = either_way.args_of(args)
    found = either_way.judge_goal(kernel, principal, goal, choose=choose, readings=readings, at=at, words=desk.words, said=desk.said,
                                  ident=goal_id, named=named)
    subject = found.get('subject') or goal.get('statement') or ''
    out.update(subject=subject, form=found.get('form', ''))
    settled = {}
    if any(way.get('state') == 'UNDECIDED' for way in found.get('ways') or ()):
        # cannot tell, said well: the settle stage's receipt carries where it holds (its zones) and what keeps (its moves)
        again = either_way.judge_goal(kernel, principal, goal, choose=choose, readings=readings, at=at, stage='settle', words=desk.words,
                                      said=desk.said, ident=goal_id, named=named)
        settled = {repr(sorted((w.get('choice') or {}).items())): r for w, r in zip(again.get('ways') or (), again.get('records') or ())
                   if r.get('state') == 'UNDECIDED'}
    for way, record in zip(found.get('ways') or (), found.get('records') or ()):
        row = {'choice': dict(way.get('choice') or {}), 'value': _value(way, found), 'state': way.get('state'),
               'answer': way.get('answer', ''), 'receipt': _receipt_of(record)}      # the receipt the proof's maths line names
        if way.get('state') == 'UNDECIDED':record = settled.get(repr(sorted((way.get('choice') or {}).items())), record)
        try:sheet = voice_facts.math_sheet(record, labels(goal, way, found), subject)
        except (ValueError, KeyError, TypeError) as exc:      # a receipt the floor does not cut: 0.8.6's words stand for it
            row.update(said=None, why=str(exc)[:200]);out['ways'].append(row);continue
        said, mark, got = _spoken(sheet)
        row.update(heading=got['heading'], said=said, mark=mark, source=got['source'], frame_key=got['frame_key'], shape=got['shape'],
                   defect=got['defect'])
        out['ways'].append(row)
    return out


# -- where 0.8.6's templates said them --------------------------------------------------------------------------------------------
def restate(section, found, voiced):
    """The panel's read `found` (field.why or field.either) with her answers said through the voice floor. Returns (found, the
    number of answers said through it). Unchanged when the floor is off, said nothing, or the read is not one it restates."""
    if not isinstance(found, dict) or not isinstance(voiced, dict) or not voiced.get('on'):return found, 0
    ways = [w for w in voiced.get('ways') or () if w.get('said') and not w.get('defect')]
    if not ways:return found, 0
    if section == 'why':
        by = {w['receipt']: w for w in ways if w.get('receipt')}
        lines, n = [], 0
        for line in found.get('lines') or ():
            m = RECEIPT.search(str(line.get('text') or '')) if isinstance(line.get('text'), str) else None
            w = by.get(m.group(1)) if m else None
            if w is not None:
                from .model_words import ModelSaid
                text = w['said'] if isinstance(w['said'], str) else ModelSaid.from_record(w['said'])
                line = dict(line, text=text, voice=True, **{'from': WORDS['from_maths'].format(receipt=m.group(1))})
                if w.get('mark'):line['mark'] = w['mark']
                n += 1
            lines.append(line)
        return (dict(found, lines=lines), n) if n else (found, 0)
    if section == 'either':
        words = list(found.get('words') or ())
        if not words:return found, 0
        plain = [w for w in ways if isinstance(w['said'], str)]
        model = [{'said': w['said'], 'mark': w['mark'] or 'WORDED'} for w in ways if not isinstance(w['said'], str)]
        many = len(ways) > 1 or bool(ways[0].get('value'))
        said = [WORDS['way'].format(value=w['value'], said=w['said']) if many and w.get('value') else WORDS['way_plain'].format(said=w['said'])
                for w in plain]
        head = words[0]
        if found.get('form') == 'EITHER_WAY' and ': ' in head:
            head = head.split(': ', 1)[0] + ':'      # "... under every reading the desk knows of:" and then each way in her voice
        out = dict(found, words=[head] + said + words[1:])
        if model:out['voice'] = model                  # model words: placed with their mark by model_marks_qt.place
        return out, len(ways)
    return found, 0


# -- the Kernel ----------------------------------------------------------------------------------------------------------------
_ID = {'type': 'string', 'minLength': 1, 'maxLength': 200}
_SHEET = {'type': 'string', 'pattern': '^owner:[a-f0-9]{32}$'}
_DAY = {'type': 'string', 'pattern': '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'}
_NAME = {'type': 'string', 'pattern': '^[a-z][a-z0-9_]{0,63}$'}
_VALUE = {'type': 'string', 'pattern': '^-?[0-9]+(\\.[0-9]+)?(/[0-9]+)?$', 'maxLength': 60}
_CELL = {'type': 'string', 'pattern': '^B[1-9][0-9]{0,2}$'}
_AT = {'type': 'array', 'maxItems': 8, 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'value'],
                                                  'properties': {'name': _NAME, 'value': _VALUE}}}
_READING = {'type': 'array', 'maxItems': 8, 'items': {'type': 'object', 'additionalProperties': False, 'required': ['name', 'sheet', 'cell'],
                                                       'properties': {'name': _NAME, 'sheet': _SHEET, 'cell': _CELL}}}
FIELDS = {'voice.say': ({'id': _ID, 'choose': {'type': 'array', 'maxItems': 8, 'items': _SHEET}, 'at': _AT, 'reading': _READING,
                         'on': _DAY, 'sheet': _SHEET}, ['id'])}
SCOPES = {op: 'read' for op in FIELDS}
OBSERVERS = tuple(FIELDS)


def dispatch(kernel, op, args, principal):
    from .office_service import owner
    owner(principal)                 # the sheets live in the owner's profile, as for field.either
    if op == 'voice.say':return say(kernel, principal, args)
    raise ValueError('Unknown voice operation')
