"""Worth asking? The gate in front of every model question, and the late rule (0.8.7, "Kas's mind with the model,
interwoven"; slice B2, lane B).

Her rule is "the model proposes; the system disposes", and asking must pay (design 3.1, rule 3). Before a model is asked
which of several next steps comes first, the desk asks itself whether asking pays. It scores each option on five exact
measures from 0.8.5 and 0.8.6 and removes the options another one dominates (the front), then, in order (design 3.4,
judgment lens J1):

  1  FORCED      one option is left: "the only way"
  2  EITHER_WAY  every option left gives the same verdict: the rule's default, "either way"
  3  BOTH_READ   only reads, at most 3, at most 5 s together: do them all
  4  DEFAULT     only reads or navigation that can be put back, and the worst loss is at most the cost of asking: the
                 rule's default, said as such
  5  OWNER       an option needs an authority (which revision, a tolerance, a counting rule, any permission): you, through
                 her one question; the model never sees it
  6  NEXT        otherwise the model is asked (when one is loaded); with none, the caller's no-model answer

When she decides without the model she says so in one line ("Either would do; I took the read (2 seconds)."), and the
fold "How I chose" names the route: the only way · either way · both read · the rule's default · yours to say · asked the
model.

The five measures (all exact, never a float; None where the desk does not know it, and an unknown measure is never
assumed to be good):
  settles    the exact share of the open outcomes the option would move out of "cannot tell" (a Fraction, higher better)
  ms         its predicted time in whole milliseconds (lower better)
  undo       its undo class: READ 0, NAVIGATION 1 (can be put back), CHANGE 2 (a change with Undo), ASKS 3 (a change that
             always asks or cannot be undone) (lower better)
  licensed   the owner's words back it (True better)
  unblocks   how many open goals have a precondition it meets (higher better)
An option dominates another when every measure of both is known, it is at least as good on all five and better on one.
An option with any unknown measure is never dominated and dominates nothing: the gate is only as good as its inputs, and
it never hides a choice it cannot weigh.

The rule's default (no model, and the late default): the lowest undo class, then the most settled, then the fewest
milliseconds, then the option's key (the planner's fixed name order). It is a total order on the options themselves, so
it never depends on the order they came in.

Late (design 4.4, J6): past the deadline of her clock the rule's default is taken only if it is a read, or navigation that
can be put back; otherwise the buttons ("The model is late. This needs you:"). A late answer is still checked: when it
agrees she says so quietly; when it differs it is offered beside hers and changes nothing.

Pure Python: no Qt, no Kernel, no model (the deadline helpers take her clock and only read it). At most a few hundred
comparisons per decision (at most 8 options, 5 measures), well inside the 5 ms the design allows.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import permutations

READ, NAVIGATION, CHANGE, ASKS = 0, 1, 2, 3
UNDO_CLASSES = (READ, NAVIGATION, CHANGE, ASKS)
UNDO_WORDS = {READ: 'a read', NAVIGATION: 'navigation that can be put back', CHANGE: 'a change with Undo', ASKS: 'a change that always asks'}
MEASURES = ('settles', 'ms', 'undo', 'licensed', 'unblocks')
ROUTES = ('NONE', 'FORCED', 'EITHER_WAY', 'BOTH_READ', 'DEFAULT', 'OWNER', 'NEXT')
FOLD = {'NONE': 'nothing to choose', 'FORCED': 'the only way', 'EITHER_WAY': 'either way', 'BOTH_READ': 'both read',
        'DEFAULT': "the rule's default", 'OWNER': 'yours to say', 'NEXT': 'asked the model'}
COVERING_READS = 3                 # rung 3: at most this many reads ...
COVERING_MS = 5000                 # ... at most this long together
OPTIONS_MOST = 8                   # the gate weighs at most 8 options (NEXT itself shows at most 4)
LEAVE = 'leave'                    # the last button of every question: Leave it
LEAVE_WORDS = 'Leave it'

WORDS = {
    'forced': 'Only one way is left: {what}.',
    'either_read': 'Either would do; I took the read ({time}).',
    'either_other': 'Either would do; I took {what}.',
    'both': 'Both are quick reads, so I did both ({time}).',
    'all': 'These are quick reads, so I did all {n} ({time}).',
    'default_read': 'Either would do; I took the read ({time}).',
    'default_nav': 'Either would do; I took {what}, which can be put back.',
    'owner': 'This is yours to say:',
    'next': 'Each of these wins on something, so the model is asked which comes first.',
    'next_no_model': 'Each of these wins on something, and no model is asked, so it is yours to say:',
    'none': 'There is nothing to choose between.',
    'late_read': 'The model is late. I took the read by default: {what}.',
    'late_nav': 'The model is late. I took the default, which can be put back: {what}.',
    'late_buttons': 'The model is late. This needs you:',
    'late_agreed': 'The model answered late and agreed.',
    'late_offer': 'The model answered late: it would have taken “{what}”. Shall I?',
    'late_unusable': 'The model answered late, and its answer could not be used.',
}


# =========================================================================================================================
# The options and their measures
# =========================================================================================================================

def _fraction(value):
    if value is None:return None
    if isinstance(value, bool):raise ValueError('JUDGMENT_MEASURE: settles is a share, not a yes or no')
    if isinstance(value, float):raise ValueError('JUDGMENT_MEASURE: no floating point; give settles as a fraction')
    found = Fraction(value) if not isinstance(value, Fraction) else value
    if not 0 <= found <= 1:raise ValueError('JUDGMENT_MEASURE: settles is a share from 0 to 1')
    return found


def _whole(value, name, most=None):
    if value is None:return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:raise ValueError('JUDGMENT_MEASURE: %s is a whole number' % name)
    if most is not None and value > most:raise ValueError('JUDGMENT_MEASURE: %s is at most %d' % (name, most))
    return value


@dataclass(frozen=True)
class Option:
    """One next step the desk built, with its five measures (None where unknown) and what the gate needs besides."""
    key: str
    words: str = ''
    settles: Fraction | None = None
    ms: int | None = None
    undo: int | None = None
    licensed: bool | None = None
    unblocks: int | None = None
    verdict: str | None = None         # the verdict the desk reaches after it, when known (rung 2: either way)
    authority: bool = False            # it needs the owner's authority (rung 5)
    put_back_ms: int | None = None     # navigation: the time to put it back if it was the wrong one (a read needs none)
    acceptable: bool = True

    def __post_init__(self):
        if not isinstance(self.key, str) or not self.key or len(self.key) > 200:raise ValueError('JUDGMENT_OPTION_KEY')
        object.__setattr__(self, 'settles', _fraction(self.settles))
        _whole(self.ms, 'ms');_whole(self.undo, 'undo', ASKS);_whole(self.unblocks, 'unblocks');_whole(self.put_back_ms, 'put_back_ms')
        if self.licensed is not None and not isinstance(self.licensed, bool):raise ValueError('JUDGMENT_MEASURE: licensed is yes or no')

    def measured(self):
        """True when all five measures are known (only then can it dominate or be dominated)."""
        return all(getattr(self, name) is not None for name in MEASURES)

    def loss_ms(self):
        """Its worst loss if it was the wrong pick: its time, plus putting it back (a read puts nothing back); None when
        that is not known, or when it is a change (a change is never a bounded loss)."""
        if self.ms is None or self.undo is None or self.undo > NAVIGATION:return None
        if self.undo == READ:return self.ms
        return None if self.put_back_ms is None else self.ms + self.put_back_ms

    def as_record(self):
        return {'key': self.key, 'words': self.words, 'settles': None if self.settles is None else str(self.settles), 'ms': self.ms,
                'undo': self.undo, 'licensed': self.licensed, 'unblocks': self.unblocks, 'verdict': self.verdict, 'authority': self.authority,
                'put_back_ms': self.put_back_ms, 'acceptable': self.acceptable}


def option_of(row):
    """An Option from a plain row ({'key', 'words' or 'purpose', and any of the measures; settles as an int or 'n/d'})."""
    if isinstance(row, Option):return row
    settles = row.get('settles')
    if isinstance(settles, str):settles = Fraction(settles)
    return Option(key=str(row.get('key') or ''), words=str(row.get('words') or row.get('purpose') or ''), settles=settles,
                  ms=row.get('ms'), undo=row.get('undo'), licensed=row.get('licensed'), unblocks=row.get('unblocks'),
                  verdict=row.get('verdict'), authority=bool(row.get('authority', False)), put_back_ms=row.get('put_back_ms'),
                  acceptable=bool(row.get('acceptable', True)))


def dominates(a, b):
    """True when a dominates b: every measure of both known, a at least as good on all five and better on one."""
    if not (a.measured() and b.measured()):return False
    at_least = (a.settles >= b.settles and a.ms <= b.ms and a.undo <= b.undo and a.licensed >= b.licensed and a.unblocks >= b.unblocks)
    better = (a.settles > b.settles or a.ms < b.ms or a.undo < b.undo or a.licensed > b.licensed or a.unblocks > b.unblocks)
    return at_least and better


def rank(option):
    """The rule's default order: the lowest undo class, the most settled, the fewest ms, then the key. Unknown sorts last."""
    return (option.undo is None, option.undo if option.undo is not None else 0,
            option.settles is None, -(option.settles or 0),
            option.ms is None, option.ms if option.ms is not None else 0,
            option.key)


def _checked(options):
    found = [option_of(o) for o in options]
    keys = [o.key for o in found]
    if len(set(keys)) != len(keys):raise ValueError('JUDGMENT_OPTION_KEY: two options share a key')
    if len(found) > OPTIONS_MOST:raise ValueError('JUDGMENT_OPTIONS: the gate weighs at most %d options' % OPTIONS_MOST)
    return found


def front(options):
    """The acceptable options no other acceptable option dominates, in the rule's default order; and what was removed,
    as ((key, the key of an option that dominates it), ...)."""
    found = [o for o in _checked(options) if o.acceptable]
    kept = [];removed = []
    for o in found:
        by = sorted((p for p in found if p is not o and dominates(p, o)), key=rank)
        if by:removed.append((o.key, by[0].key))
        else:kept.append(o)
    return sorted(kept, key=rank), tuple(sorted(removed))


def default(options):
    """The rule's default among the acceptable options (None when none is acceptable): it never depends on their order."""
    found = sorted((o for o in _checked(options) if o.acceptable), key=rank)
    return found[0] if found else None


# =========================================================================================================================
# The gate
# =========================================================================================================================

def time_words(ms):
    """'2 seconds' (whole seconds, rounded up), '1 second', or 'under a second'."""
    if ms is None:return 'time not known'
    whole = -(-int(ms) // 1000)
    if whole <= 0:return 'under a second'
    return '%d second%s' % (whole, '' if whole == 1 else 's')


@dataclass(frozen=True)
class Decision:
    """What the gate decided: the route, the keys taken now (in order), the default, the front, what was removed, her one
    line, whether the model is asked, and the buttons (keys, then Leave it) when it is yours to say."""
    route: str
    take: tuple = ()
    default: str | None = None
    front: tuple = ()
    removed: tuple = ()
    words: str = ''
    ask: bool = False
    buttons: tuple = ()
    fold: str = ''
    model_calls: int = 0

    def as_record(self):
        return {'route': self.route, 'take': list(self.take), 'default': self.default, 'front': list(self.front),
                'removed': [list(r) for r in self.removed], 'words': self.words, 'ask': self.ask, 'buttons': list(self.buttons),
                'fold': self.fold, 'model_calls': 0}


def gate(options, cost_ms=None, model_ready=False):
    """Worth asking? options: Options or rows (at most 8). cost_ms: the cost of asking the model a NEXT question on this
    machine, in whole ms (her clock: asking_cost_ms), or None when not known (rung 4 then never applies). model_ready:
    a model is loaded and its choosing switch is on. Never calls a model."""
    kept, removed = front(options)
    keys = tuple(o.key for o in kept)

    def made(route, take=(), words='', buttons=()):
        return Decision(route=route, take=tuple(take), default=kept[0].key if kept else None, front=keys, removed=removed, words=words,
                        ask=route == 'NEXT' and model_ready, buttons=tuple(buttons), fold=FOLD[route])
    if not kept:return made('NONE', words=WORDS['none'])
    first = kept[0]
    # 1 · forced
    if len(kept) == 1:return made('FORCED', (first.key,), WORDS['forced'].format(what=first.words or first.key))
    # 2 · either way: every option left gives the same verdict
    verdicts = {o.verdict for o in kept}
    if None not in verdicts and len(verdicts) == 1:
        if first.undo == READ and first.ms is not None:said = WORDS['either_read'].format(time=time_words(first.ms))
        else:said = WORDS['either_other'].format(what=first.words or first.key)
        return made('EITHER_WAY', (first.key,), said)
    # 3 · covering reads: only reads, at most 3, at most 5 s together: do them all
    if len(kept) <= COVERING_READS and all(o.undo == READ and o.ms is not None for o in kept):
        total = sum(o.ms for o in kept)
        if total <= COVERING_MS:
            said = WORDS['both'].format(time=time_words(total)) if len(kept) == 2 else WORDS['all'].format(n=len(kept), time=time_words(total))
            return made('BOTH_READ', keys, said)
    # 4 · only reads or navigation, and the worst loss is at most the cost of asking: the rule's default
    losses = [o.loss_ms() for o in kept]
    if cost_ms is not None and all(o.undo in (READ, NAVIGATION) for o in kept) and None not in losses and max(losses) <= int(cost_ms):
        if first.undo == READ:said = WORDS['default_read'].format(time=time_words(first.ms))
        else:said = WORDS['default_nav'].format(what=first.words or first.key)
        return made('DEFAULT', (first.key,), said)
    # 5 · an authority: you, through her one question (the model never sees it)
    if any(o.authority for o in kept):return made('OWNER', (), WORDS['owner'], keys + (LEAVE,))
    # 6 · otherwise the model, when one is ready; else the caller's no-model answer (the buttons by default)
    if model_ready:return made('NEXT', (), WORDS['next'])
    return made('NEXT', (), WORDS['next_no_model'], keys + (LEAVE,))


# =========================================================================================================================
# Late: a read by default, a change never
# =========================================================================================================================

@dataclass(frozen=True)
class Late:
    """What she does when the model is late: TAKE the default (a read, or navigation that can be put back) or BUTTONS."""
    action: str
    key: str | None
    words: str
    buttons: tuple = ()


def is_late(asked_ms, now_ms, deadline_ms):
    """Late exactly at the deadline: True when now - asked >= deadline (a deadline of 0 is Stop only: never late)."""
    return bool(deadline_ms) and int(now_ms) - int(asked_ms) >= int(deadline_ms)


def late(options, default_key=None):
    """The late rule over the options the model was asked about: the default (the rule's default, or default_key when the
    caller's own rule names it, as a profile's first acceptable option does) is taken when it is a read or navigation
    that can be put back (its put-back time known); otherwise the buttons (the default first, then the rule's order, then
    Leave it), and nothing is done."""
    found = sorted((o for o in _checked(options) if o.acceptable), key=rank)
    pick = next((o for o in found if o.key == default_key), None) if default_key is not None else None
    pick = pick or (found[0] if found else None)
    buttons = ((pick.key,) if pick else ()) + tuple(o.key for o in found if o is not pick) + (LEAVE,)
    if pick is not None and pick.undo == READ:
        return Late('TAKE', pick.key, WORDS['late_read'].format(what=pick.words or pick.key))
    if pick is not None and pick.undo == NAVIGATION and pick.put_back_ms is not None:
        return Late('TAKE', pick.key, WORDS['late_nav'].format(what=pick.words or pick.key))
    return Late('BUTTONS', None, WORDS['late_buttons'], buttons)


def late_answer(options, taken, picked):
    """A late answer, checked: ('AGREED', words) when the model picked what was taken; ('OFFER', words) when it picked
    another acceptable option (offered beside hers, nothing done); ('UNUSABLE', words) otherwise. taken may be None
    (the buttons were shown): then any usable pick is an OFFER beside the buttons."""
    by = {o.key: o for o in _checked(options)}
    chosen = by.get(picked) if picked is not None else None
    if chosen is None or not chosen.acceptable:return 'UNUSABLE', WORDS['late_unusable']
    if taken is not None and chosen.key == taken:return 'AGREED', WORDS['late_agreed']
    return 'OFFER', WORDS['late_offer'].format(what=chosen.words or chosen.key)


# =========================================================================================================================
# Her clock: the deadline of a NEXT question and the cost of asking it (brain_clock, lane A)
# =========================================================================================================================

def next_price_ms(clock, key):
    """The price of a NEXT question on this key: her clock's price for the kind's typical new tokens and answer cap."""
    from .brain_clock import BUDGETS
    b = BUDGETS['NEXT']
    return int(clock.price_ms(key, 'NEXT', b['new_typical'], b['answer'], 50))


def next_deadline_ms(clock, key):
    """max(3 s, 2 x price + 1 s), capped by the kind (turns.standard_deadline over brain_clock.caps('NEXT'))."""
    from . import brain_clock
    return int(brain_clock.deadline_ms(next_price_ms(clock, key), brain_clock.caps('NEXT')))


def asking_cost_ms(clock, key):
    """The cost of asking a NEXT question here: the measured median NEXT time on this key when there is one, else the
    price (the specification's estimate); after three lates in a session her clock raises it to the measured median."""
    measured = clock.measured_ms(key, 'NEXT') if hasattr(clock, 'measured_ms') else None
    rule = int(measured) if measured is not None else next_price_ms(clock, key)
    return int(clock.asking_cost_ms(key, 'NEXT', rule)) if hasattr(clock, 'asking_cost_ms') else rule


# =========================================================================================================================
# 0.8.6's either way: who a question of the ways goes to
# =========================================================================================================================

def ways_route(form, premise=None, model_loaded=False):
    """How a judgement of every way was settled, for the fold "How I chose": EITHER_WAY (no one asked), OWNER (a choice
    that is yours to say: which revision, a counting rule, whether a sheet is complete), NEXT (which numbered thing your
    words meant, with a model loaded: its GOAL turn), or NONE (nothing is asked: the answer depends on more than one
    thing, or the ways could not be combined). Never calls a model."""
    from .mind_types import AUTHORITY, MODEL, who
    if form == 'EITHER_WAY':return {'route': 'EITHER_WAY', 'fold': FOLD['EITHER_WAY'], 'model_calls': 0}
    if form != 'DEPENDS_ON_ONE' or premise is None:return {'route': 'NONE', 'fold': FOLD['NONE'], 'model_calls': 0}
    found_who, kind = who(premise, model_loaded)
    if found_who == MODEL and kind != AUTHORITY:return {'route': 'NEXT', 'fold': 'which one your words meant: the model', 'model_calls': 0}
    return {'route': 'OWNER', 'fold': FOLD['OWNER'], 'model_calls': 0}


# =========================================================================================================================
# Self-checks the smoke script calls (brute force; no test file, by the owner's rule for 0.8.6 and 0.8.7)
# =========================================================================================================================

def front_is_undominated(options):
    """Brute force: no option in the front is dominated by any acceptable option, and every removed one is."""
    kept, removed = front(options)
    found = [o for o in _checked(options) if o.acceptable]
    by = {o.key: o for o in found}
    if any(dominates(p, o) for o in kept for p in found):return False
    return all(dominates(by[b], by[r]) for r, b in removed)


def order_free(options, cost_ms=None, model_ready=False):
    """Every order of the options gives the same default and the same decision (checked over all permutations)."""
    found = _checked(options)
    first = None
    for order in permutations(found):
        d = gate(order, cost_ms, model_ready);here = (d.route, d.take, d.default, d.front, d.removed, d.buttons, getattr(default(order), 'key', None))
        if first is None:first = here
        elif here != first:return False
    return True


__all__ = ['Option', 'Decision', 'Late', 'option_of', 'dominates', 'rank', 'front', 'default', 'gate', 'late', 'late_answer', 'is_late',
           'next_price_ms', 'next_deadline_ms', 'asking_cost_ms', 'ways_route', 'time_words', 'READ', 'NAVIGATION', 'CHANGE', 'ASKS']
