"""Her clock: the price of a model turn before it is sent, its deadline, and the line under her card while it runs (0.8.7,
"Kas's mind with the model, interwoven"; slice A3, lane A).

Asking must pay (design 3.1, rule 3): no turn is sent unless the desk needs one, it fits its price, and its kind is switched
on; every turn has a deadline, and past it the safe default or the buttons. This module is the price and the deadline.

    price    = the desk's share + new tokens / read rate + answer tokens / write rate                  (design 4.4)
    deadline = max(3 s, 2 x price + 1 s), capped by the kind (turns.standard_deadline; the caps are BUDGETS below)

The rates are rolling medians per model key (model file, runtime, backend, context: the port's key), per kind, from the
timings every turn already returns (prompt_n, prompt_ms, predicted_n, predicted_ms on its brain.turn/1 record), with reads
kept in size bands: small reads are slower per token (30 to 43 a second against 70 cold on the 4B, measured). Where a kind
has fewer than three timings, the key's other kinds stand in; where the key has none, the rates the model check measured
for that key (1.0 M1: its tuning stage, runtime_tuning.measured; a small read at three fifths of them), and where it never
ran, the 4B's quiet rates here (rounded down). All of it is whole milliseconds and exact fractions: no floating point.
1.0 M1: the stand-ins were measured again with llama.cpp v1.0.0 (b12359) and the 4B on this processor, quiet: 43 to 47
tokens a second reading 830 tokens cold, 4 to 5 writing; they stand.

Also here: the line under her card while a turn runs ("Asking the model: 2 s of about 3"), why a turn three times its price
was slow, from the meters ("Slow today: memory is tight."), the lates (two in a row narrow the question; three in a session
raise her cost of asking to the measured median, so she asks less), and BUDGETS, the design's table of budgets per kind
(4.3), from which a kind's Caps are built (caps()).
"""
from __future__ import annotations

import json
import math
import os
from collections import deque
from fractions import Fraction
from pathlib import Path
from statistics import median_low

from . import turns

WINDOW = 31                               # timings kept per (key, kind, band)
LEAST = 3                                 # timings a median needs before it replaces the stand-in
BANDS = ((256, 'small'), (1024, 'medium'), (None, 'large'))     # new prompt tokens of a read
DEFAULT_READ = {'small': Fraction(30), 'medium': Fraction(50), 'large': Fraction(70)}    # tokens a second (4B, quiet)
DEFAULT_WRITE = Fraction(5)
SLOW_TIMES = 3                            # a turn this many times its price says why
LATES_NARROW = 2                          # lates in a row of a kind that narrow its question
LATES_SESSION = 3                         # lates in a session that raise her cost of asking

# Budgets per kind (design 4.3): the brief kept (tokens), new tokens typical and cap, the answer cap, the deadline cap (ms),
# foreground. The 4B column is the bench here; the 35B's are estimates until the model check measures them.
BUDGETS = {
    'GOAL':    dict(brief=450, new_typical=120, new_cap=300, answer=6, deadline=6000, foreground=True),
    'PICK':    dict(brief=450, new_typical=120, new_cap=300, answer=4, deadline=6000, foreground=True),
    'READ':    dict(brief=700, new_typical=60, new_cap=250, answer=24, deadline=10000, foreground=True),
    'BIND':    dict(brief=0, new_typical=150, new_cap=300, answer=6, deadline=6000, foreground=True),
    'NEXT':    dict(brief=450, new_typical=150, new_cap=600, answer=8, deadline=6000, foreground=True),
    'ORDER':   dict(brief=0, new_typical=97, new_cap=200, answer=4, deadline=6000, foreground=True),
    'MARKS':   dict(brief=500, new_typical=700, new_cap=1000, answer=140, deadline=20000, foreground=True),
    'ASK':     dict(brief=0, new_typical=30, new_cap=60, answer=48, deadline=6000, foreground=True),
    'COLUMNS': dict(brief=500, new_typical=300, new_cap=400, answer=30, deadline=10000, foreground=True),
    'FRAME':   dict(brief=450, new_typical=180, new_cap=250, answer=90, deadline=10000, foreground=False),
    'TALK':    dict(brief=300, new_typical=60, new_cap=600, answer=256, deadline=0, foreground=True),
}


def caps(kind, **over):
    """The kind's turns.Caps from the budgets table (READ with four steps: answer=48). Talk has no deadline: Stop."""
    b = dict(BUDGETS[kind]);b.update(over)
    return turns.Caps(new_tokens=b['new_cap'], answer_tokens=b['answer'], deadline_ms=b['deadline'],
                      foreground=b['foreground'], stop_only=kind == 'TALK' or not b['deadline'],
                      desk_ms=b.get('desk_ms', 50), odds=b.get('odds', 0))


def band(new_tokens):
    for most, name in BANDS:
        if most is None or new_tokens <= most:return name
    return 'large'


def deadline_ms(price_ms, kind_caps):
    """max(3 s, 2 x price + 1 s), capped by the kind; 0 for Talk (no deadline, Stop)."""
    return turns.standard_deadline(price_ms, kind_caps)


def _int(value):
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and value >= 0 else None


class Clock:
    """Her clock for one Graphite session: rates from the turns it has seen (and, through clock(kernel), the ledger's)."""

    def __init__(self):
        self.read = {}                    # (key, kind, band) -> deque of tokens a second (Fraction)
        self.write = {}                   # (key, kind) -> deque of tokens a second
        self.elapsed = {}                 # (key, kind) -> deque of whole ms a turn took
        self.lates_in_row = {}            # (key, kind) -> lates in a row
        self.session_lates = 0

    # -- learning ------------------------------------------------------------------------------------------------------
    def _keep(self, table, slot, value):
        table.setdefault(slot, deque(maxlen=WINDOW)).append(value)

    def observe(self, key, kind, record, live=True):
        """Learn from one brain.turn/1 record (turns.ask calls it after every sent turn). `live` False when replaying the
        ledger at start: replays never count as this session's lates."""
        t = record.get('timings') or {}
        prompt_n, prompt_ms = _int(t.get('prompt_n')), _int(t.get('prompt_ms'))
        predicted_n, predicted_ms = _int(t.get('predicted_n')), _int(t.get('predicted_ms'))
        if prompt_n and prompt_ms:self._keep(self.read, (key, kind, band(prompt_n)), Fraction(prompt_n * 1000, prompt_ms))
        if predicted_n and predicted_ms:self._keep(self.write, (key, kind), Fraction(predicted_n * 1000, predicted_ms))
        outcome = record.get('outcome');elapsed = _int(record.get('elapsed_ms'))
        if outcome == 'LATE':
            self.lates_in_row[(key, kind)] = self.lates_in_row.get((key, kind), 0) + 1
            if live:self.session_lates += 1
        elif outcome not in (None, 'FAILED'):
            self.lates_in_row[(key, kind)] = 0
        if elapsed and outcome not in ('FAILED',):self._keep(self.elapsed, (key, kind), elapsed)

    # -- rates --------------------------------------------------------------------------------------------------------------
    def _median(self, table, key, kind, extra=()):
        mine = table.get((key, kind) + tuple(extra))
        if mine and len(mine) >= LEAST:return median_low(mine)
        pooled = [v for slot, values in table.items() if slot[0] == key and tuple(slot[2:]) == tuple(extra) for v in values]
        if len(pooled) >= LEAST:return median_low(pooled)
        return None

    def read_rate(self, key, kind, new_tokens):
        b = band(new_tokens)
        return self._median(self.read, key, kind, (b,)) or _measured(key, 0, b) or DEFAULT_READ[b]

    def write_rate(self, key, kind):
        return self._median(self.write, key, kind) or _measured(key, 1) or DEFAULT_WRITE

    def price_ms(self, key, kind, new_tokens, answer_tokens, desk_ms):
        """The price of a turn before it is sent, in whole ms (rounded up): desk + new / read rate + answer / write rate."""
        new_tokens = max(0, int(new_tokens));answer_tokens = max(0, int(answer_tokens))
        read = self.read_rate(key, kind, new_tokens);write = self.write_rate(key, kind)
        return int(desk_ms) + math.ceil(Fraction(new_tokens * 1000) / read) + math.ceil(Fraction(answer_tokens * 1000) / write)

    # -- lates and her cost of asking -----------------------------------------------------------------------------------
    def narrow(self, key, kind):
        """True after two lates in a row of this kind: the next question of it is narrowed (fewer options, one step)."""
        return self.lates_in_row.get((key, kind), 0) >= LATES_NARROW

    def measured_ms(self, key, kind):
        """The median time a turn of this kind took on this key (None before three)."""
        mine = self.elapsed.get((key, kind))
        return median_low(mine) if mine and len(mine) >= LEAST else None

    def asking_cost_ms(self, key, kind, rule_ms):
        """Her cost of asking the model this kind of question, for 'worth asking?' (judgment.front): the rule's figure, and
        after three lates in a session the measured median when that is higher, so she asks less."""
        rule_ms = int(rule_ms)
        if self.session_lates < LATES_SESSION:return rule_ms
        measured = self.measured_ms(key, kind)
        return max(rule_ms, int(measured)) if measured is not None else rule_ms


def _measured(key, which, read_band=None):
    """1.0 M1: the model check's measured rate for this model key (read: 0, write: 1), a small read at three fifths of it;
    None when the key was never measured."""
    try:
        from .runtime_tuning import measured
        got = measured(key)
    except Exception:  # noqa: BLE001 - no measurement: the stand-ins
        return None
    if not got:return None
    rate = got[which]
    return rate * Fraction(3, 5) if read_band == 'small' else rate


# -- one clock per Kernel database, rebuilt from the ledger --------------------------------------------------------------------
_CLOCKS = {}


def clock(kernel=None):
    """Her clock for this Kernel: built once per process from the newest turn records' timings, then kept up to date by
    turns.ask (observe). With no Kernel, a fresh clock on the stand-in rates."""
    if kernel is None:return Clock()
    slot = str(getattr(kernel, 'dbpath', id(kernel)))
    held = _CLOCKS.get(slot)
    if held is not None:return held
    made = Clock()
    try:
        with kernel.db() as db:
            turns.ensure(db)
            rows = db.execute("SELECT payload FROM brain_turns WHERE state='KEPT' ORDER BY at DESC, rowid DESC LIMIT 400").fetchall()
        for (payload,) in reversed(rows):
            value = json.loads(payload)
            made.observe(value.get('key'), value.get('kind'), value, live=False)
    except Exception:  # noqa: BLE001 - a clock that cannot read the ledger starts on the stand-in rates
        made = Clock()
    _CLOCKS[slot] = made
    return made


# -- the line under her card ---------------------------------------------------------------------------------------------
def asking_line(elapsed_ms, price_ms):
    """'Asking the model: 2 s of about 3' (whole seconds gone, the price rounded up; Stop is the button beside it)."""
    gone = max(0, int(elapsed_ms)) // 1000
    about = max(1, -(-int(price_ms) // 1000))
    return 'Asking the model: %d s of about %d' % (gone, about)


def asking_now(request, now_ms=None):
    """The line for a request whose turn is running (turns.TurnRequest.now_asking), or '' when none is."""
    asking = getattr(request, 'now_asking', None)
    if not asking:return ''
    now = request.now_ms() if now_ms is None else int(now_ms)
    line = asking_line(now - asking['began_ms'], asking['price_ms'])
    if asking.get('quick'):line = line.replace('Asking the model', 'Asking the quick model', 1)   # 1.0 M2: priced on the quick model
    return line


# -- why it was slow, from the meters -------------------------------------------------------------------------------------
def meters():
    """What the machine says now: memory tight, on battery, processor busy (each True, False or None for not measured)."""
    out = {'memory_tight': None, 'battery': None, 'processor_busy': None}
    try:
        from . import host_observations
        sample = host_observations.memory()
        if sample:out['memory_tight'] = sample['used'] * 10 >= sample['total'] * 9
    except Exception:  # noqa: BLE001 - a meter that cannot be read says nothing
        pass
    try:
        supplies = list(Path('/sys/class/power_supply').glob('*'))
        states = [(p / 'status').read_text().strip() for p in supplies if (p / 'type').read_text().strip() == 'Battery']
        if states:out['battery'] = 'Discharging' in states
    except OSError:
        pass
    try:
        with open('/proc/loadavg') as stream:load = stream.read().split()[0]
        whole, _, part = load.partition('.')
        hundredths = int(whole) * 100 + int((part + '00')[:2])
        out['processor_busy'] = hundredths * 10 >= (os.cpu_count() or 1) * 100 * 9
    except (OSError, ValueError, IndexError):
        pass
    return out


def slow_why(elapsed_ms, price_ms, readings=None):
    """When a turn took three times its price, why, in her words from the meters; None when it was not slow."""
    if int(price_ms) <= 0 or int(elapsed_ms) < SLOW_TIMES * int(price_ms):return None
    readings = meters() if readings is None else readings
    said = [words for name, words in (('memory_tight', 'memory is tight'), ('battery', 'on battery'),
                                      ('processor_busy', 'the processor is busy')) if readings.get(name)]
    if not said:return 'Slow today; the meters do not say why.'
    return 'Slow today: ' + '; '.join(said) + '.'
