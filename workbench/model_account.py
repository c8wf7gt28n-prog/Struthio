"""What the model did for you, and what it cost (0.8.7, "Kas's mind with the model, interwoven"; slice A4, lane A).

A fixed account, a view over the turn ledger (brain.turn/1, turns.py) and nothing else, so it is exact by construction:
every model turn sits inside a checked question that has a deterministic no-model answer, and turns.ask records, for every
turn, the code of that answer ('without') and whether the value used differs from it ('differs'). Help is a used outcome
(TAKEN, TRIMMED, UNSETTLED) that differs; it counts differences, not their worth, and the account says so.

  "This week the model answered 41 of my questions. 29 changed what I did: you were asked 12 fewer questions, 9 answers
   were worded by the model, 8 places were found. 8 were refused by my checks. 4 were late, so I did what I do without
   it. It cost: you waited 3 min 40 s in all. I count what changed, not what it was worth."

  - answered:   every turn of hers that reached the model and did not fail (Talk is yours, not hers: counted apart)
  - changed:    differs; split by what it changed: a question you were not asked (the no-model answer was ASK_OWNER),
                wording (FRAME), places (MARKS, ASK, COLUMNS: the reading switch), a choice of next step (NEXT, ORDER),
                a reading of your words (READ, GOAL, PICK, BIND when they did not spare you a question)
  - the same:   used, but what she would have done without it
  - refused:    REFUSED or TRIPPED by her checks
  - late:       LATE: past the deadline, so she did what she does without it (the design's "the safe read"; "safe" is a
                banned word in her templates, mind_words.BANNED, so the sentence says what she did instead)
  - wait:       the seconds a foreground turn ran while you waited, each capped at its deadline
A forgotten turn's tombstone keeps its kind, outcome, switch, deadline, 'without' and 'differs' (counts, never words), so
Forget does not change the account.

The honest null (design 5.6): after NULL_TURNS answered turns of a kind this month (KEEP_DAYS) with none that differs,
she stops asking the model for that kind (turns.ask gives NOT_SENT, NO_HELP) and says so: "The model hasn't changed a
single choice of next step this month; I'll stop asking it for those." brain.help.set's ask_again (with Undo) asks again:
from then on only later turns count. ORDER (the tripwire's second asking) and TALK are never stopped this way: the one is a
check, not help; the other is yours.

With local_brain not importable at all, the account is the exact no-model sentence (design 4.7): "No model this week.
Everything I did, I did without it."

Operations (0.8.7 A4): brain.account (read): the account; brain.turn.forget (approve, and always asked: stacy_hand's
ALWAYS_ASKS covers '*.forget'): Forget one turn, which leaves only its tombstone (turns.forget).

Pure Python: no Qt, no model, no float in any count (seconds are whole numbers from whole milliseconds). Never imports
clip or gemini_engineer.
"""
from __future__ import annotations

import json
import time

from . import mind_words, turns

SCHEMA = 'brain.account/1'
NULL_TURNS = 20                      # answered turns of a kind this month with none that differs: she stops asking
NULL_DAYS = turns.KEEP_DAYS          # "this month": the ledger's own bound
PERIODS = {'week': 7, 'month': 30}
NEVER_STOPPED = ('ORDER', 'TALK')    # a check, not help; and yours
USED = turns.USED
REFUSED = ('REFUSED', 'TRIPPED')

# What a changed answer changed, in the order the account says them.
PARTS = ('fewer', 'worded', 'places', 'choices', 'readings')
# What the honest null names, per kind: "hasn't changed a single {thing}".
THINGS = {'NEXT': 'choice of next step', 'GOAL': 'pick between readings of your words', 'READ': 'reading of your words',
          'PICK': 'placing of your typed answer', 'BIND': 'match of your words to a value', 'MARKS': 'pencil mark on a page',
          'ASK': 'place found in your Library', 'COLUMNS': 'mapping of a table’s columns', 'FRAME': 'wording of an answer'}

NO_MODEL = 'No model this week. Everything I did, I did without it.'      # design 4.7, exactly

# Her words here: fixed templates, scanned with the rest of hers (mind_words.check). Every number arrives through a slot
# that names its record (NUMBERS); none of them carries a model mark (model_words.MARKS).
WORDS = {
    'no_model': NO_MODEL,
    'nothing_asked': 'I asked the model nothing this {period}. Everything I did, I did without it.',
    'answered': 'This {period} the model answered {answered} of my questions.',
    'changed': '{changed} changed what I did: {parts}.',
    'changed_more': 'And {parts}.',
    'changed_none': 'None of them changed what I did.',
    'fewer': 'you were asked {fewer} fewer questions',
    'fewer_one': 'you were asked one question fewer',
    'worded': '{worded} answers were worded by the model',
    'worded_one': 'one answer was worded by the model',
    'places': '{places} places were found',
    'places_one': 'one place was found',
    'choices': '{choices} choices of next step were the model’s',
    'choices_one': 'one choice of next step was the model’s',
    'readings': '{readings} readings of your words were the model’s',
    'readings_one': 'one reading of your words was the model’s',
    'same': '{same} gave what I would have done without it.',
    'same_one': 'One gave what I would have done without it.',
    'refused': '{refused} were refused by my checks.',
    'refused_one': 'One was refused by my checks.',
    'late': '{late} were late, so I did what I do without it.',
    'late_one': 'One was late, so I did what I do without it.',
    'failed': '{failed} got no answer from the model.',
    'failed_one': 'One got no answer from the model.',
    'cost': 'It cost: you waited {wait} in all.',
    'worth': 'I count what changed, not what it was worth.',
    'talk': 'You also talked with it {talk} times, and it answered in its own words, from its memory.',
    'talk_one': 'You also talked with it once, and it answered in its own words, from its memory.',
    'null': "The model hasn't changed a single {thing} this month; I'll stop asking it for those.",      # design 2.12, exactly
    'asked_again': 'I will ask the model for each {thing} again, and count afresh from now.',
}
_LEDGER = 'brain.turn/1 records of this period (model_account.tally)'
NUMBERS = {key: {slot: _LEDGER for slot in mind_words.slots(text) if slot not in ('period', 'thing')}
           for key, text in WORDS.items()}
mind_words.register('model_account', WORDS, kind='sentence', numbers=NUMBERS)
BUTTONS = {'ask_again': 'Ask it again', 'count': 'Count again'}
mind_words.register('model_account_buttons', BUTTONS, kind='button')


def say(key, **slots):
    return WORDS[key].format(**slots)


def duration(ms):
    """Whole milliseconds as her words: '40 s', '3 min 40 s', '3 min', '1 h 5 min' (rounded to the second, half up)."""
    s = (max(0, int(ms)) + 500) // 1000
    if s < 60:return '%d s' % s
    if s < 3600:
        m, s = divmod(s, 60)
        return '%d min %d s' % (m, s) if s else '%d min' % m
    h, rest = divmod(s, 3600)
    m = rest // 60
    return '%d h %d min' % (h, m) if m else '%d h' % h


# -- reading the ledger -------------------------------------------------------------------------------------------------------
def rows(kernel, owner, since):
    """Every turn record (kept or a tombstone) of this owner since `since` (seconds), oldest first."""
    with kernel.db() as db:
        turns.ensure(db)
        found = db.execute('SELECT payload FROM brain_turns WHERE owner=? AND at>=? ORDER BY at, rowid', (owner, since)).fetchall()
    out = []
    for (payload,) in found:
        try:out.append(json.loads(payload))
        except ValueError:continue
    return out


def _switch(row):
    return row.get('switch') or turns.SWITCH_OF.get(row.get('kind'), '')


def part_of(row):
    """What a changed answer changed (one of PARTS)."""
    if row.get('without') == 'ASK_OWNER':return 'fewer'
    switch = _switch(row)
    return {'wording': 'worded', 'reading': 'places', 'choosing': 'choices'}.get(switch, 'readings')


def tally(records):
    """Exact counts over turn records (kept or tombstones): asked, answered, changed and its parts, same, refused, late,
    failed, wait_ms, talk."""
    c = {'asked': 0, 'answered': 0, 'changed': 0, 'same': 0, 'refused': 0, 'late': 0, 'failed': 0, 'wait_ms': 0, 'talk': 0,
         **{p: 0 for p in PARTS}}
    for row in records:
        if row.get('kind') == 'TALK':
            c['talk'] += 1;continue
        c['asked'] += 1
        outcome = row.get('outcome')
        if outcome == 'FAILED':
            c['failed'] += 1
        else:
            c['answered'] += 1
            if outcome == 'LATE':c['late'] += 1
            elif outcome in REFUSED:c['refused'] += 1
            elif outcome in USED and row.get('differs'):
                c['changed'] += 1;c[part_of(row)] += 1
            else:c['same'] += 1
        if row.get('foreground'):
            elapsed = int(row.get('elapsed_ms') or 0);deadline = int(row.get('deadline_ms') or 0)
            c['wait_ms'] += min(elapsed, deadline) if deadline else elapsed
    return c


def nulls(records, again=None):
    """{kind: answered turns} for every kind the honest null stops: at least NULL_TURNS answered turns (after the owner's
    ask_again for it, if any) and not one that differs."""
    again = again or {}
    seen = {};helped = set()
    for row in records:
        kind = row.get('kind')
        if kind in NEVER_STOPPED or kind not in turns.KNOWN_KINDS or row.get('outcome') == 'FAILED':continue
        if float(row.get('at') or 0) < again.get(kind, 0):continue
        seen[kind] = seen.get(kind, 0) + 1
        if row.get('outcome') in USED and row.get('differs'):helped.add(kind)
    return {kind: n for kind, n in sorted(seen.items()) if n >= NULL_TURNS and kind not in helped}


def stopped_kinds(kernel, owner, now=None):
    """The kinds she no longer asks the model about this month (turns.request_for reads this once per request)."""
    now = time.time() if now is None else now
    return sorted(nulls(rows(kernel, owner, now - NULL_DAYS * 86400), turns.asked_again(kernel)))


# -- the account ------------------------------------------------------------------------------------------------------------
def model_available():
    """Whether Graphite's local model code can be loaded at all (not whether a model is loaded)."""
    try:
        from . import local_brain  # noqa: F401
    except ImportError:
        return False
    return True


def _part(name, n):
    return say(name + '_one') if n == 1 else say(name, **{name: n})


def words_for(c, period='week', stopped=()):
    """The account's sentences for counts `c` (tally) and the kinds the honest null stopped."""
    if not c['asked'] and not c['talk']:
        out = [say('nothing_asked', period=period)]
    else:
        out = []
        if c['asked']:
            out.append(say('answered', period=period, answered=c['answered']))
            if c['answered']:
                parts = [_part(p, c[p]) for p in PARTS if c[p]]
                if parts:
                    out.append(say('changed', changed=c['changed'], parts=', '.join(parts[:3])))
                    if parts[3:]:out.append(say('changed_more', parts=', '.join(parts[3:])))
                else:
                    out.append(say('changed_none'))
                for name in ('same', 'refused', 'late'):
                    if c[name]:out.append(_part(name, c[name]))
            if c['failed']:out.append(_part('failed', c['failed']))
        if c['talk']:out.append(say('talk_one') if c['talk'] == 1 else say('talk', talk=c['talk']))
        if c['wait_ms']:out.append(say('cost', wait=duration(c['wait_ms'])))
        if c['changed']:out.append(say('worth'))
    things = []
    for kind in stopped:
        thing = THINGS.get(kind)
        if thing and thing not in things:things.append(thing)
    out += [say('null', thing=t) for t in things]
    return out


def account(kernel, owner, period='week', now=None):
    """The account for this period: {'schema', 'period', 'since', 'no_model', 'words', 'text', 'counts', 'nulls'}."""
    if period not in PERIODS:raise ValueError('BRAIN_ACCOUNT_PERIOD: week or month')
    now = time.time() if now is None else now
    since = now - PERIODS[period] * 86400
    if not model_available():
        return {'schema': SCHEMA, 'period': period, 'since': since, 'no_model': True, 'words': [NO_MODEL], 'text': NO_MODEL,
                'counts': None, 'nulls': []}
    c = tally(rows(kernel, owner, since))
    stopped = nulls(rows(kernel, owner, now - NULL_DAYS * 86400), turns.asked_again(kernel))
    words = words_for(c, period, sorted(stopped))
    return {'schema': SCHEMA, 'period': period, 'since': since, 'no_model': False, 'words': words, 'text': ' '.join(words),
            'counts': c, 'nulls': [{'kind': k, 'turns': n, 'thing': THINGS.get(k, k.lower()),
                                    'words': say('null', thing=THINGS.get(k, k.lower())),
                                    'again': {'op': 'brain.help.set', 'args': {'ask_again': k}}} for k, n in sorted(stopped.items())]}


# -- the Kernel's operations (0.8.7 A4) ---------------------------------------------------------------------------------------
FIELDS = {
    'brain.account': ({'period': {'type': 'string', 'enum': list(PERIODS)}}, []),
    'brain.turn.forget': ({'id': turns.TURN_ID}, ['id']),
}
SCOPES = {'brain.account': 'read', 'brain.turn.forget': 'approve'}
FORGOTTEN = 'Forgotten. Only this is kept: a question of this kind was asked, and how it ended.'
mind_words.register('model_account_forget', {'forgotten': FORGOTTEN}, kind='sentence')


def dispatch(kernel, op, args, principal):
    if op == 'brain.account':
        return account(kernel, principal.identity, args.get('period', 'week'))
    if op == 'brain.turn.forget':
        stone = turns.forget(kernel, principal.identity, args['id'], principal)
        return {'turn': stone, 'words': FORGOTTEN}
    raise ValueError('Unknown account operation')
