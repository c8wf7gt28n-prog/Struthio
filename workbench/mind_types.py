"""The shapes of her mind (0.8.6, "Kas's mind, no model"): the open point, a way the desk could be, an open leaf, a
judgement and the one budget. Written first and frozen: either_way, settle, reasons, rules and her words all read these,
and they change only by agreement between the lanes.

  OpenPoint   one "cannot tell", with who settles it and what would settle it. Computed on read and never stored.
  Leaf        one open premise of a judgement: is it decisive alone, or only in a pair, and the zone or the candidate values
              it could take.
  Way         one way the desk could be read (a choice of revision, of limit, of reading), and the state under it.
  Judgement   a goal or a rule judged over every way the desk knows: the state, the ways, the open points, the proof's
              digest, what it rests on, and the budget used. model_calls is 0 in 0.8.6.
  Budget      every limit of her mind in one place, and the one sentence for a partial answer.

WHO_ANSWERS is the closed table of who answers which open premise; who() reads it, and a premise that is not in it goes to
you. The words a sort carries on screen are WHO_WORDS: "your records", "the maths", "you", "the model", "a new reading".

Pure Python: no Qt, no Kernel, no model. Every number in these shapes is an exact Fraction or an int, never a float.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from fractions import Fraction

# The four values of a judgement, as stac/evidence.py's Belnap lattice names them on the maths' side.
HOLDS, FAILS, UNDECIDED, CONFLICT = 'HOLDS', 'FAILS', 'UNDECIDED', 'CONFLICT'
STATES = (HOLDS, FAILS, UNDECIDED, CONFLICT)
STATE_WORDS = {HOLDS: 'holds', FAILS: 'does not hold', UNDECIDED: 'cannot tell', CONFLICT: 'cannot tell: two readings cannot both be right'}

# What sort of thing is open.
FACT_MISSING, AUTHORITY, MEANING, TIE, DECISION = 'FACT_MISSING', 'AUTHORITY', 'MEANING', 'TIE', 'DECISION'
KINDS = (FACT_MISSING, AUTHORITY, MEANING, TIE, DECISION)

# Who settles it, and how that is said on screen.
RECORDS, MATHS, YOU, MODEL, WORLD = 'RECORDS', 'MATHS', 'YOU', 'MODEL', 'WORLD'
WHO = (RECORDS, MATHS, YOU, MODEL, WORLD)
WHO_WORDS = {RECORDS: 'your records', MATHS: 'the maths', YOU: 'you', MODEL: 'the model', WORLD: 'a new reading'}

# Whether a leaf decides the point by itself, only together with one other leaf, or not within the budget.
ALONE, PAIR, NOT_DECISIVE = 'ALONE', 'PAIR', 'NOT_DECISIVE'
DECISIVE = (ALONE, PAIR, NOT_DECISIVE)

# The closed table of who answers what (design section 3.1). premise sort -> (who, kind).
WHO_ANSWERS = {
    'ROW_NOT_READ': (RECORDS, FACT_MISSING),           # a row or cell already on the desk, not yet read: "I read row 3 of Rev B"
    'VALUE_TO_WORK_OUT': (MATHS, FACT_MISSING),        # she works it out; no question
    'REVISION': (YOU, AUTHORITY),                      # which revision or limit applies
    'TOLERANCE': (YOU, AUTHORITY),
    'CONVENTION': (YOU, AUTHORITY),                    # a counting, calendar or unit convention
    'SOURCE_GOVERNS': (YOU, AUTHORITY),                # which source governs
    'RULE_READING': (YOU, MEANING),                    # how a rule's words read
    'SHEET_COMPLETE': (YOU, AUTHORITY),                # whether a sheet is complete
    'OWN_ACCOUNT': (YOU, FACT_MISSING),                # your own account
    'ALWAYS_ASKS': (YOU, AUTHORITY),                   # anything stacy_hand.ALWAYS_ASKS covers
    'WHICH_GOAL': (MODEL, MEANING),                    # which numbered goal or row your words pointed at: the model if loaded, else you
    'NEW_READING': (WORLD, FACT_MISSING),              # a measurement or document not yet on the desk
    'SHOULD_I': (YOU, DECISION),                       # "should I ...": the fixed decline, and everything she can compute
}


def who(premise, model_loaded=False):
    """(who, kind) for an open premise of this sort. A sort that only the model could read goes to you when no model is
    loaded; a sort not in the table goes to you, as an authority."""
    found_who, kind = WHO_ANSWERS.get(premise, (YOU, AUTHORITY))
    if found_who == MODEL and not model_loaded:found_who = YOU
    return found_who, kind


def _plain(value):
    """A shape as plain JSON-ready data: a Fraction as its exact text, tuples as lists."""
    if isinstance(value, Fraction):return str(value)
    if isinstance(value, dict):return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):return [_plain(v) for v in value]
    return value


@dataclass(frozen=True)
class Budget:
    """Every limit of her mind (design section 3.5). Past any of them she says sentence(): what was tried, what is sound,
    and what she could not reach."""
    ways: int = 64                       # ways of reading the desk worked out for one question
    groups: int = 729                    # groups of ways
    proof_nodes: int = 64                # proof closure: reason_graph's own budgets
    proof_rules: int = 128
    settle_leaves: int = 12              # open leaves weighed by settle; pairs only when no single leaf decides
    make_hold_sets: int = 3              # "would make it hold" sets
    planner_expansions: int = 4096
    planner_acts: int = 12
    proof_lines: int = 12                # proof lines shown

    @staticmethod
    def sentence(tried, of, unreached=''):
        """The one sentence for a partial answer."""
        said = 'I tried %d of %d; this much is sound' % (tried, of)
        return said + ('; this is what I could not reach: %s.' % unreached if unreached else '.')

    def as_record(self):return asdict(self)


BUDGET = Budget()


@dataclass(frozen=True)
class Leaf:
    """One open premise: what it is about, its sort in WHO_ANSWERS, who settles it, whether it decides alone or in a pair,
    and its zone (a numeric leaf: the values that settle it each way) or its candidate values (a choice)."""
    id: str
    about: tuple = ()                    # record ids, or (sheet, cell) references as text
    premise: str = 'VALUE_TO_WORK_OUT'   # a key of WHO_ANSWERS
    who: str = MATHS
    decisive: str = NOT_DECISIVE
    share: Fraction | None = None        # for a numeric leaf: the share of its range a reading of it settles
    zone: dict = field(default_factory=dict)          # {'holds': end, 'fails': end} of a numeric leaf
    values: tuple = ()                   # the candidate values of a choice
    words: str = ''

    def as_record(self):return _plain(asdict(self))


@dataclass(frozen=True)
class Way:
    """One way the desk could be read: the choices that make it ((what was chosen, the choice), ...) and the state under
    it, with the room and the digest of the answer it came from."""
    choices: tuple = ()
    state: str = UNDECIDED
    room: tuple | None = None            # (lo, hi) to spare, exact, in `unit`; negative: over by
    unit: str = ''
    answer: str = ''                     # the digest of the ledger.math-answer/1 (or the rule's evaluation) it rests on
    words: str = ''

    def as_record(self):return _plain(asdict(self))


@dataclass(frozen=True)
class OpenPoint:
    """One "cannot tell": what it is about, its kind and who settles it, the open leaves, for each way it could be
    settled the state and the room, the digest of the proof it came from, and what was tried."""
    about: tuple
    kind: str = FACT_MISSING
    who: str = YOU
    leaves: tuple = ()                   # Leaf, decisive alone first, then pairs
    outcomes: tuple = ()                 # Way: "Rev B applies: does not hold, 2 to 8 ms over"
    proof: str = ''
    budget: tuple = (0, 0, '')           # (tried, of, the sentence when it is a partial answer)

    @property
    def who_words(self):return WHO_WORDS[self.who]

    def as_record(self):return _plain({**asdict(self), 'who_words': self.who_words})


@dataclass(frozen=True)
class Judgement:
    """A goal or a rule judged over every way the desk knows: its state (one of STATES, or DEPENDS when the ways disagree),
    the ways, the open points, the proof's digest, what it rests on and the budget used. Kasandra asks no model in 0.8.6."""
    about: tuple
    state: str = UNDECIDED
    ways: tuple = ()
    open_points: tuple = ()
    proof: str = ''
    rests_on: tuple = ()
    budget: tuple = (0, 0, '')
    model_calls: int = 0

    def as_record(self):return _plain(asdict(self))


DEPENDS = 'DEPENDS'                      # a Judgement's state when its ways disagree: "it depends on one thing"
