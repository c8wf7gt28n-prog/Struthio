"""The turn contract: every question Kas puts to a local model goes through ask() (0.8.7, "Kas's mind with the model,
interwoven"; slice E0, lane A).

Her rule is "the model proposes; the system disposes". A model turn here is a short question with a short answer: a number,
a line reference, a reading the desk checks part by part, a frame the desk fills. Every answer is parsed into a desk object
and checked by its kind's checker before anything uses it; free model text survives only as model_words.ModelSaid, which
cannot be shown as her words. A wrong answer is refused before the owner sees it; a late one is not waited for.

====================================================================================================================
THE FROZEN INTERFACE (slice E0). Lanes B and C register their kinds against it and never edit it; it changes only by
agreement, in lane A.
--------------------------------------------------------------------------------------------------------------------
TurnKind(name, version, switch, brief, stable, last, grammar, caps, parse, check, fallback,
         deadline=standard_deadline, paper='')
    name      one of KNOWN_KINDS (READ GOAL PICK BIND NEXT ORDER MARKS ASK COLUMNS FRAME TALK), or another upper-case
              name for an exam shape or a stand-in (fake_worker.FAKE)
    version   int; the brief's sha256 and the version together are the kind's identity in every record
    switch    the owner's switch it belongs to: understanding, choosing, reading, wording, talk (SWITCH_OF fixes it
              for the eleven known kinds)
    brief()                -> str   message 1: fixed rules and tables, no owner data; must give the same text every call
    stable(inputs)         -> str   message 2: session-stable context (the numbered things, a page, agreed examples)
    last(inputs)           -> str   message 4: everything that varies (the now line, the request, the options)
    grammar(inputs)        -> str or None   GBNF from grammars.py, no free whitespace (None for Talk only)
    caps: Caps(new_tokens, answer_tokens, deadline_ms, foreground=True, desk_ms=50, odds=0, stop_only=False)
    parse(said, inputs)    -> a desk object, or raises model_words.Invalid       (said is a ModelSaid)
    check(obj, inputs)     -> Verdict(state, value=None, why=(), checks=(), basis='model_pick', second_view=None)
                              state: TAKEN, TRIMMED, REFUSED, UNSETTLED or TRIPPED
    fallback(inputs)       -> Fallback(code, value): the exact no-model answer; code: ASK_OWNER, DEFAULT_READ,
                              PLAIN_WORDS, CANNOT_TELL, NOT_OFFERED, PATTERNS (the pattern pass), PLACES (the places)
    deadline(price_ms, caps) -> int ms (standard_deadline: max(3 s, 2 x price + 1 s), capped by the kind)
    paper     the exam paper the kind sits (section 5.5), a name

register(kind) -> kind            once per kind, at import of the module that owns it (idempotent for the same kind)
ask(kind, inputs, request) -> Answer
    kind is a registered TurnKind or its name; request is a TurnRequest (one per owner request: the ceiling lives in it).
    In order: the switch and the per-request ceiling; the layout; the grammar; the tokens and the price from her clock;
    the deadline; the call (local_brain.completion, through the request's port); parse; check; one brain.turn/1 record;
    then the checked desk object, or the fallback.
Answer(value, by_model, outcome, fallback, why, verdict, turn, said, price_ms, deadline_ms, elapsed_ms, late_view)
    by_model   True when value is the checked model answer (TAKEN, TRIMMED, UNSETTLED); else value is the fallback's
    outcome    TAKEN TRIMMED REFUSED UNSETTLED TRIPPED LATE FAILED (a turn was sent and recorded), or NOT_SENT
    why        for NOT_SENT: SWITCH_OFF, AI_OFF, NO_MODEL, STOPPED, CEILING_TURNS, CEILING_TIME, OVER_CAP, OVER_CONTEXT;
               for a sent turn the first reason code of its verdict, or LATE, or the worker's error code
    late_view  a late answer's checked value (TAKEN or TRIMMED), offered beside hers, never taken
TurnRequest(port=None, ledger=None, clock=None, switches=None, owner='', foreground_turns=3, budget_ms=25000,
            now_ms=None, cancelled=None, on_progress=None, off_reason='NO_MODEL')
    .take_card() -> bool   at most one question card per request (the one question, lane B)
    request_for(kernel, principal, ...) builds one for the live, selected local model; with none, port is None.
layout(kind, inputs) -> the four messages: system brief | user stable | assistant "Ready." | user last
The record: brain.turn/1 (record()), kept local in its own table, bounded (KEEP_DAYS, KEEP_TURNS); Forget leaves a
tombstone (forget()); read through the Kernel as brain.turns and brain.turn.get (read scope).
The worker port (LocalPort here; fake_worker.FakeWorker for smoke scripts): live(), model(), key(), count(messages),
kept(messages), the attribute context (tokens, or None), complete(messages, *, answer_tokens, grammar, deadline_ms, odds,
prompt_tokens, on_progress) -> dict(text, finish, timings, odds, elapsed_ms); raises Late past the deadline, PortError
when the worker fails. on_progress(tokens_written, elapsed_ms), when given, is called as the answer streams (A3).
Her clock (brain_clock.py, lane A's A3, when it exists; FixedClock until then): price_ms(key, kind, new_tokens,
answer_tokens, desk_ms) and observe(key, kind, record).
Added by A3 (backward compatible: new names only, nothing above changed meaning):
    NOT_SENT also RECEIPT_FIRST: a wording kind (FRAME) is never sent before her receipt sentence is on screen
             (request.receipt_on_screen()); OVER_CAP also for a grammar that admits an answer over the kind's cap
             (grammars.fits; a grammar outside grammars.py's subset is a contract error)
    the port's complete() also takes cancelled (the request's Stop): the turn streams and is closed past its deadline
    TurnRequest.receipt_on_screen(), .card(buttons) (the one question card, then None), .ceiling() (what is left),
               .now_asking ({kind, price_ms, deadline_ms, began_ms} while a turn runs: brain_clock.asking_now's line)
    set_switches(kernel, changes, undo) and the operation brain.help.set (execute, with Undo): the owner's switch per
    kind; with every switch off no turn is sent, no record is written, and every answer is the kind's 0.8.6 fallback.
====================================================================================================================

Only this module calls local_brain.completion (local_brain's own ready probe excepted). This module, model_words.py and
every registered checker never import clip or gemini_engineer, so Kas's checked questions can never go to a cloud model.
Nothing here writes a fact, a decision or a change: ask() returns a checked desk object or the fallback, and what the
caller does with it still passes the dial (stacy_hand), where a change whose only basis is the model's pick is never hers.
"""
from __future__ import annotations

import ast
import hashlib
import importlib
import json
import math
import time
import uuid
from dataclasses import dataclass, field, is_dataclass, asdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable

from . import grammars
from .model_words import MOST as MODEL_SAID_MOST, Invalid, ModelSaid

SCHEMA = 'brain.turn/1'
READY = 'Ready.'                         # message 3, one fixed line, never changes (the layout contract)
STABLE_EMPTY = 'Nothing is kept for this question.'
KNOWN_KINDS = ('READ', 'GOAL', 'PICK', 'BIND', 'NEXT', 'ORDER', 'MARKS', 'ASK', 'COLUMNS', 'FRAME', 'TALK')
SWITCHES = {'understanding': True, 'choosing': True, 'reading': True, 'wording': False, 'talk': True}   # defaults (design 9)
SWITCH_OF = {'READ': 'understanding', 'GOAL': 'understanding', 'PICK': 'understanding', 'BIND': 'understanding',
             'NEXT': 'choosing', 'ORDER': 'choosing', 'MARKS': 'reading', 'ASK': 'reading', 'COLUMNS': 'reading',
             'FRAME': 'wording', 'TALK': 'talk'}
VERDICTS = ('TAKEN', 'TRIMMED', 'REFUSED', 'UNSETTLED', 'TRIPPED')
OUTCOMES = VERDICTS + ('LATE', 'FAILED')
USED = ('TAKEN', 'TRIMMED', 'UNSETTLED')         # verdicts whose value the caller receives
FALLBACKS = ('ASK_OWNER', 'DEFAULT_READ', 'PLAIN_WORDS', 'CANNOT_TELL', 'NOT_OFFERED', 'PATTERNS', 'PLACES')
NOT_SENT = ('SWITCH_OFF', 'AI_OFF', 'NO_MODEL', 'STOPPED', 'CEILING_TURNS', 'CEILING_TIME', 'OVER_CAP', 'OVER_CONTEXT',
            'RECEIPT_FIRST')     # A3: a wording turn waits for her receipt sentence on screen
RECEIPT_FIRST_SWITCHES = ('wording',)   # A3: kinds of these switches are sent only after request.receipt_on_screen()
BASES = ('owner_words', 'owner_click', 'deduction', 'model_pick')
FOREGROUND_TURNS = 3                     # at most 3 foreground model turns per request (design 4.4)
FOREGROUND_BUDGET_MS = 25000             # the 4B here; the 35B's 8 s is a target the model check replaces (design 4.4)
DEADLINE_FLOOR_MS = 3000
FOREGROUND_DEADLINE_MOST_MS = 20000      # no foreground deadline exceeds 20 s (design 4.3)
NEW_TOKENS_MOST = 1600                   # no foreground question reads more than 1,600 new tokens (design 4.3)
KEEP_DAYS = 30
KEEP_TURNS = 2000
FORBIDDEN_IMPORTS = ('clip', 'gemini_engineer')
KINDS: dict = {}
_DIGESTS: dict = {}


# -- the shapes -------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Caps:
    new_tokens: int                      # most new (not re-read) prompt tokens a question may carry; one over is never sent
    answer_tokens: int                   # the answer cap (max_tokens)
    deadline_ms: int                     # the kind's cap on its deadline; 0 only with stop_only (Talk: no deadline, Stop)
    foreground: bool = True              # foreground turns count against the request's ceiling
    desk_ms: int = 50                    # the desk's own share of the price
    odds: int = 0                        # alternatives per answer token to record (0: none)
    stop_only: bool = False


@dataclass(frozen=True)
class Fallback:
    code: str
    value: Any = None

    def __post_init__(self):
        if self.code not in FALLBACKS:raise ValueError('TURN_FALLBACK_CODE: %s' % self.code)


@dataclass(frozen=True)
class Verdict:
    state: str
    value: Any = None
    why: tuple = ()
    checks: tuple = ()                   # (name, passed, detail) for every check run, for the record and the fold
    basis: str = 'model_pick'
    second_view: Any = None              # {'hers': ..., 'model': ..., 'why': ...} when the model's view differs from hers

    def __post_init__(self):
        if self.state not in VERDICTS:raise ValueError('TURN_VERDICT_STATE: %s' % self.state)
        if self.basis not in BASES:raise ValueError('TURN_BASIS: %s' % self.basis)


def standard_deadline(price_ms, caps):
    """max(3 s, 2 x price + 1 s), capped by the kind (design 4.4). Integer milliseconds; 0 for a Stop-only kind."""
    if caps.stop_only:return 0
    return min(caps.deadline_ms, max(DEADLINE_FLOOR_MS, 2 * int(price_ms) + 1000))


@dataclass(frozen=True)
class TurnKind:
    name: str
    version: int
    switch: str
    brief: Callable[[], str]
    stable: Callable[[Any], str]
    last: Callable[[Any], str]
    grammar: Callable[[Any], Any]
    caps: Caps
    parse: Callable[[ModelSaid, Any], Any]
    check: Callable[[Any, Any], Verdict]
    fallback: Callable[[Any], Fallback]
    deadline: Callable[[int, Caps], int] = standard_deadline
    paper: str = ''

    def brief_digest(self):
        return hashlib.sha256(self.brief().encode('utf-8')).hexdigest()

    def ident(self):
        """name/version#brief sha256 (12): what every record and the exam key name the kind by."""
        return '%s/%d#%s' % (self.name, self.version, self.brief_digest()[:12])


@dataclass(frozen=True)
class Answer:
    value: Any
    by_model: bool
    outcome: str
    fallback: Any = None                 # the fallback code when value is the fallback's
    why: str = ''
    verdict: Any = None
    turn: str = ''                       # the brain.turn/1 record id when a turn was sent
    said: Any = None                     # the raw answer, as ModelSaid
    price_ms: int = 0
    deadline_ms: int = 0
    elapsed_ms: int = 0
    late_view: Any = None


class Late(Exception):
    """The worker did not answer by the deadline. `text` is a late answer if one arrived (it is recorded and checked)."""

    def __init__(self, elapsed_ms, text=None, timings=None):
        super().__init__('LATE');self.elapsed_ms = int(elapsed_ms);self.text = text;self.timings = timings or {}


class PortError(Exception):
    """The worker failed (not live, an HTTP error, a malformed reply). `code` is a short reason, never the worker's log."""

    def __init__(self, code):
        super().__init__(code);self.code = str(code)[:120]


# -- the registry -----------------------------------------------------------------------------------------------------------
def register(kind):
    """Add a kind to the one registry. The same kind again is a no-op; another kind under a taken name is refused."""
    if not isinstance(kind, TurnKind):raise TypeError('TURN_KIND: register a TurnKind')
    if not kind.name.isupper() or not kind.name.replace('_', '').isalpha() or not 2 <= len(kind.name) <= 16:
        raise ValueError('TURN_KIND_NAME: upper-case letters, 2 to 16')
    if kind.switch not in SWITCHES:raise ValueError('TURN_KIND_SWITCH: %s' % kind.switch)
    if kind.name in SWITCH_OF and SWITCH_OF[kind.name] != kind.switch:
        raise ValueError('TURN_KIND_SWITCH: %s belongs to %s' % (kind.name, SWITCH_OF[kind.name]))
    if not isinstance(kind.version, int) or kind.version < 1:raise ValueError('TURN_KIND_VERSION')
    caps = kind.caps
    if not 1 <= caps.answer_tokens <= 600:raise ValueError('TURN_CAPS_ANSWER: 1 to 600 tokens')
    if not 1 <= caps.new_tokens <= NEW_TOKENS_MOST:raise ValueError('TURN_CAPS_NEW_TOKENS: 1 to %d' % NEW_TOKENS_MOST)
    if caps.stop_only:
        if caps.deadline_ms != 0:raise ValueError('TURN_CAPS_DEADLINE: a Stop-only kind has no deadline')
    elif caps.foreground and not DEADLINE_FLOOR_MS <= caps.deadline_ms <= FOREGROUND_DEADLINE_MOST_MS:
        raise ValueError('TURN_CAPS_DEADLINE: a foreground deadline is 3 to 20 s')
    elif not caps.foreground and not DEADLINE_FLOOR_MS <= caps.deadline_ms <= 120000:
        raise ValueError('TURN_CAPS_DEADLINE: a background deadline is 3 to 120 s')
    if not 0 <= caps.odds <= 8 or caps.desk_ms < 0:raise ValueError('TURN_CAPS_ODDS_OR_DESK')
    brief = kind.brief()
    if not isinstance(brief, str) or not brief.strip() or brief != kind.brief():raise ValueError('TURN_BRIEF_NOT_FIXED')
    digest = kind.brief_digest()
    held = KINDS.get(kind.name)
    if held is not None:
        if held is kind or (held.version == kind.version and _DIGESTS[kind.name] == digest and held.caps == kind.caps):
            return held
        raise ValueError('TURN_KIND_TAKEN: %s is registered already' % kind.name)
    KINDS[kind.name] = kind;_DIGESTS[kind.name] = digest
    return kind


def kind_of(kind):
    if isinstance(kind, TurnKind):
        if KINDS.get(kind.name) is not kind:raise ValueError('TURN_KIND_NOT_REGISTERED: %s' % kind.name)
        return kind
    if kind not in KINDS:raise ValueError('TURN_KIND_UNKNOWN: %s' % kind)
    return KINDS[kind]


def checker_modules():
    """The modules of every registered kind's builders, parser and checker (for the no-cloud-import scan)."""
    out = set()
    for kind in KINDS.values():
        for fn in (kind.brief, kind.stable, kind.last, kind.grammar, kind.parse, kind.check, kind.fallback, kind.deadline):
            module = getattr(fn, '__module__', None)
            if module:out.add(module)
    return sorted(out)


def discover(root=None):
    """Import every workbench module that registers a kind, found by reading the sources (no list to keep by hand), so a
    check over "every registered kind" sees them all. Returns the module names imported."""
    root = Path(root or Path(__file__).resolve().parent)
    found = []
    for path in sorted(root.glob('*.py')):
        text = path.read_text(encoding='utf-8', errors='replace')
        if 'register(' not in text or 'turns' not in text or path.name == 'turns.py':continue
        try:tree = ast.parse(text)
        except SyntaxError:continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                if (isinstance(f, ast.Attribute) and f.attr == 'register' and isinstance(f.value, ast.Name) and f.value.id == 'turns') or \
                   (isinstance(f, ast.Name) and f.id == 'register' and 'from .turns import' in text):
                    found.append('workbench.' + path.stem);break
    for name in found:importlib.import_module(name)
    return found


# -- the layout -------------------------------------------------------------------------------------------------------------
def layout(kind, inputs):
    """The four messages (design 3.2). Everything that varies lives in message 4, so a kept brief is re-used up to there."""
    kind = kind_of(kind)
    brief = kind.brief()
    if hashlib.sha256(brief.encode('utf-8')).hexdigest() != _DIGESTS[kind.name]:
        raise ValueError('TURN_BRIEF_CHANGED: %s gave another brief; its sha256 is part of the kind' % kind.name)
    stable = kind.stable(inputs);last = kind.last(inputs)
    if not isinstance(stable, str) or not isinstance(last, str):
        raise TypeError('TURN_MESSAGE_TEXT: a message is plain text the desk built (never model words)')
    if not last.strip():raise ValueError('TURN_LAST_EMPTY: message 4 holds the question')
    return [{'role': 'system', 'content': brief}, {'role': 'user', 'content': stable if stable.strip() else STABLE_EMPTY},
            {'role': 'assistant', 'content': READY}, {'role': 'user', 'content': last}]


# -- her clock until brain_clock.py --------------------------------------------------------------------------------------------
class FixedClock:
    """Fixed rates for the price until her clock (brain_clock.py, A3) measures them: tokens a second, read cold and read in
    small kept pieces, and written. The defaults are the 4B's quiet rates here (design 4.3), rounded down."""
    SMALL = 256

    def __init__(self, read_small=30, read_large=70, write=5):
        self.read_small = Fraction(read_small);self.read_large = Fraction(read_large);self.write = Fraction(write)

    def price_ms(self, key, kind, new_tokens, answer_tokens, desk_ms):
        """desk share + new tokens / read rate + answer tokens / write rate, in whole milliseconds, rounded up."""
        read = self.read_small if new_tokens <= self.SMALL else self.read_large
        return int(desk_ms) + math.ceil(Fraction(new_tokens * 1000) / read) + math.ceil(Fraction(answer_tokens * 1000) / self.write)

    def observe(self, key, kind, record):
        pass


def default_clock(kernel=None):
    """Her clock when lane A has built it (brain_clock.clock(kernel)), else FixedClock."""
    try:
        from . import brain_clock
    except ImportError:
        return FixedClock()
    return brain_clock.clock(kernel)


# -- the request: one per owner request, with its ceiling ---------------------------------------------------------------------
def _monotonic_ms():
    return time.monotonic_ns() // 1000000


class TurnRequest:
    def __init__(self, port=None, ledger=None, clock=None, switches=None, owner='', foreground_turns=FOREGROUND_TURNS,
                 budget_ms=FOREGROUND_BUDGET_MS, now_ms=None, cancelled=None, on_progress=None, off_reason='NO_MODEL'):
        self.id = uuid.uuid4().hex
        self.port = port
        self.ledger = ledger if ledger is not None else MemoryLedger()
        self.clock = clock if clock is not None else FixedClock()
        self.switches = {**SWITCHES, **(switches or {})}
        self.owner = owner
        self.foreground_turns = int(foreground_turns)
        self.budget_ms = int(budget_ms)
        self.now_ms = now_ms or _monotonic_ms
        self.cancelled = cancelled or (lambda: False)
        self.on_progress = on_progress
        self.off_reason = off_reason
        self.turns_used = 0
        self.spent_ms = 0
        self.cards_used = 0
        self.receipt_shown = False          # A3: her receipt sentence is on screen (a wording turn waits for it)
        self.now_asking = None              # A3: {kind, price_ms, deadline_ms, began_ms} while a turn runs

    def switch_on(self, name):return bool(self.switches.get(name, False))

    def remaining_ms(self):return max(0, self.budget_ms - self.spent_ms)

    def take_card(self):
        """At most one question card per request (design 4.4): True the first time, False after."""
        if self.cards_used >= 1:return False
        self.cards_used += 1
        return True

    # -- 0.8.7 A3: the ceiling, the receipt first -----------------------------------------------------------------------------
    def card(self, buttons):
        """The buttons as this request's one question card, or None when a card was shown already: past the ceiling she
        stops asking, says what she has, and the buttons appear, once (never two question cards in one request)."""
        return buttons if buttons and self.take_card() else None

    def ceiling(self):
        """What is left of this request's ceiling: model turns, model time, the one card."""
        return {'turns_used': self.turns_used, 'turns_most': self.foreground_turns, 'spent_ms': self.spent_ms,
                'budget_ms': self.budget_ms, 'cards_used': self.cards_used, 'cards_most': 1,
                'reached': self.turns_used >= self.foreground_turns or self.remaining_ms() < DEADLINE_FLOOR_MS}

    def receipt_on_screen(self):
        """Her column calls this once the receipt's sentence (a kept phrasing or her plain words) is painted: her facts never
        wait for her wording, so no wording turn is sent before it."""
        self.receipt_shown = True


def stored_switches(kernel):
    """The owner's switches per kind (brain.help.set writes them, a later slice); the defaults where none is stored."""
    try:
        with kernel.db() as db:row = db.execute("SELECT value FROM settings WHERE key='brain.help'").fetchone()
        stored = json.loads(row[0]) if row else {}
    except Exception:  # noqa: BLE001 - no settings to read: the defaults
        stored = {}
    return {name: bool(stored.get(name, on)) for name, on in SWITCHES.items()}


def request_for(kernel, principal, **options):
    """A TurnRequest for this owner request, on the live, selected local model; with none (or Graphite AI off), the port is
    None and every ask() returns its fallback without a turn."""
    port = None;off = 'NO_MODEL'
    options.setdefault('switches', stored_switches(kernel))
    try:
        from . import local_brain
    except ImportError:
        local_brain = None
    if not any({**SWITCHES, **options['switches']}.values()):
        local_brain = None;off = 'SWITCH_OFF'     # A3: every switch off: Kas is exactly 0.8.6; the worker is not looked at
    if local_brain is not None:
        try:
            local_brain.require_enabled(kernel)
        except ValueError:
            off = 'AI_OFF'
        else:
            worker = local_brain.get(kernel, 'worker', {});selection = local_brain.get(kernel, 'selection', {})
            if local_brain.worker_live(worker) and worker.get('model_id') == selection.get('model_id'):
                try:
                    local_brain.verify_resident(local_brain.model(kernel, worker['model_id']), worker)
                    port = LocalPort(worker)
                except (ValueError, OSError):
                    port = None
    options.setdefault('clock', default_clock(kernel))
    return TurnRequest(port=port, ledger=KernelLedger(kernel, principal.identity), owner=principal.identity, off_reason=off,
                       **options)


# -- the local worker port: the only caller of local_brain.completion -----------------------------------------------------------
class LocalPort:
    """Graphite's own local model worker (local_brain). Prompt reuse is off until A2 turns it on (cache_prompt false,
    --cache-ram 0), so kept() is 0 and every token of a question is new."""
    GRACE_MS = 500

    def __init__(self, worker):
        self.worker = worker;self.context = worker.get('context')

    def live(self):
        from . import local_brain
        return local_brain.worker_live(self.worker)

    def model(self):return self.worker.get('model_id', '')

    def key(self):
        """The qualification key until A5's seven-part exam key: model file, runtime, backend, context, template options."""
        from . import local_brain, record_io
        return record_io.digest({'model': self.worker.get('model_id'), 'runtime': self.worker.get('runtime'),
                                 'backend': self.worker.get('backend'), 'context': self.worker.get('context'),
                                 'template': local_brain.TEMPLATE_OPTIONS})

    def count(self, messages):
        from . import local_brain
        try:
            prompt = local_brain.request(self.worker, '/apply-template', {'messages': messages, 'add_generation_prompt': True,
                                         'chat_template_kwargs': local_brain.TEMPLATE_OPTIONS}, timeout=10)['prompt']
            tokens = local_brain.request(self.worker, '/tokenize', {'content': prompt, 'add_special': False}, timeout=10)['tokens']
        except (ValueError, OSError, KeyError, TypeError) as exc:
            raise PortError(_code(exc)) from None
        if not isinstance(tokens, list):raise PortError('LOCAL_TOKENIZER_RESPONSE_INVALID')
        return len(tokens)

    def kept(self, messages):
        return 0

    def complete(self, messages, *, answer_tokens, grammar, deadline_ms, odds=0, prompt_tokens=None, on_progress=None,
                 cancelled=None):
        from . import local_brain
        began = _monotonic_ms()
        timeout = 90 if not deadline_ms else (deadline_ms + self.GRACE_MS) / 1000
        try:   # A3: every turn streams, so it is closed at its deadline (reading included) or on Stop
            got = local_brain.completion(self.worker, messages, answer_tokens, grammar=grammar, timeout=timeout,
                                         t_max_predict_ms=deadline_ms or None, odds=odds, prompt_tokens=prompt_tokens,
                                         on_progress=on_progress or _quiet, cancelled=cancelled or _never)
        except TimeoutError:
            raise Late(_monotonic_ms() - began) from None
        except OSError as exc:      # URLError is an OSError; a timeout while connecting arrives as one
            if 'timed out' in str(exc):raise Late(_monotonic_ms() - began) from None
            raise PortError(_code(exc)) from None
        except (ValueError, KeyError, TypeError) as exc:
            if 'MODEL_OPERATION_CANCELLED' in str(exc):raise PortError('STOPPED') from None
            raise PortError(_code(exc)) from None
        return {'text': got['text'], 'finish': got.get('finish_reason'), 'timings': got.get('timings') or {},
                'odds': got.get('odds'), 'elapsed_ms': _monotonic_ms() - began}


def _quiet(tokens_written, elapsed_ms):
    pass


def _never():
    return False


def _code(exc):
    text = str(exc) or type(exc).__name__
    return text.split(':', 1)[0].strip()[:120] or type(exc).__name__


# -- ask --------------------------------------------------------------------------------------------------------------------
def _without(kind, inputs, why):
    fb = kind.fallback(inputs)
    if not isinstance(fb, Fallback):raise TypeError('TURN_FALLBACK: a kind returns a Fallback')
    return Answer(value=fb.value, by_model=False, outcome='NOT_SENT', fallback=fb.code, why=why)


def ask(kind, inputs, request):
    """Ask the model one question of this kind, or give the fallback. Never raises for anything the model or the worker
    does; raises only for a kind that breaks the contract (an unregistered kind, a brief that changed, a message that is
    not plain text)."""
    kind = kind_of(kind)
    caps = kind.caps
    # 1 · the switch and the per-request ceiling
    if not request.switch_on(kind.switch):return _without(kind, inputs, 'SWITCH_OFF')
    if kind.switch in RECEIPT_FIRST_SWITCHES and not request.receipt_shown:return _without(kind, inputs, 'RECEIPT_FIRST')
    port = request.port
    if port is None or not port.live():return _without(kind, inputs, request.off_reason if port is None else 'NO_MODEL')
    if request.cancelled():return _without(kind, inputs, 'STOPPED')
    if caps.foreground and request.turns_used >= request.foreground_turns:return _without(kind, inputs, 'CEILING_TURNS')
    # 2 · the layout and the grammar
    messages = layout(kind, inputs)
    grammar = grammars.check(kind.grammar(inputs))
    if grammar is None and kind.name != 'TALK' and not caps.stop_only:raise ValueError('TURN_GRAMMAR: only Talk has none')
    if grammar is not None and not grammars.fits(grammar, caps.answer_tokens):return _without(kind, inputs, 'OVER_CAP')  # A3
    # 3 · the tokens and the price from her clock; the deadline
    try:
        prompt = port.count(messages)
    except PortError as exc:
        return _without(kind, inputs, 'OVER_CONTEXT' if 'CONTEXT' in exc.code else 'NO_MODEL')
    context = getattr(port, 'context', None)
    if context and prompt + caps.answer_tokens + 32 > context:return _without(kind, inputs, 'OVER_CONTEXT')
    kept = max(0, min(int(port.kept(messages)), prompt));new = prompt - kept
    if new > caps.new_tokens:return _without(kind, inputs, 'OVER_CAP')
    key = port.key()
    price = int(request.clock.price_ms(key, kind.name, new, caps.answer_tokens, caps.desk_ms))
    deadline = int(kind.deadline(price, caps))
    if caps.foreground and not caps.stop_only:
        remaining = request.remaining_ms()
        if price > remaining or remaining < DEADLINE_FLOOR_MS:return _without(kind, inputs, 'CEILING_TIME')
        deadline = min(deadline, remaining)
    # 4 · the call
    if caps.foreground:request.turns_used += 1
    began = request.now_ms();late = False;failed = None;text = None;finish = None;timings = {};odds = None
    request.now_asking = {'kind': kind.name, 'price_ms': price, 'deadline_ms': deadline, 'began_ms': began}   # A3: her line
    try:
        got = port.complete(messages, answer_tokens=caps.answer_tokens, grammar=grammar, deadline_ms=deadline,
                            odds=caps.odds, prompt_tokens=prompt, on_progress=request.on_progress,
                            cancelled=request.cancelled)
        text = got.get('text');finish = got.get('finish');timings = got.get('timings') or {};odds = got.get('odds')
        elapsed = int(got['elapsed_ms']) if got.get('elapsed_ms') is not None else request.now_ms() - began
        late = bool(deadline) and elapsed > deadline
    except Late as exc:
        late = True;elapsed = max(exc.elapsed_ms, deadline);text = exc.text;timings = exc.timings
    except PortError as exc:
        failed = exc.code;elapsed = request.now_ms() - began
    finally:
        request.now_asking = None
    if caps.foreground:request.spent_ms += min(elapsed, deadline) if deadline else elapsed
    if isinstance(text, str) and len(text) > MODEL_SAID_MOST and failed is None:failed = 'MODEL_OUTPUT_LIMIT';text = None
    # 5 · parse and check (a late answer is checked too, for the record and the offer beside hers)
    said = ModelSaid(text, kind.name) if isinstance(text, str) else None
    verdict = None;invalid = None
    if said is not None and failed is None:
        if finish == 'length':
            invalid = 'LENGTH'
        else:
            try:
                obj = kind.parse(said, inputs)
            except Invalid as exc:
                invalid = str(exc) or 'INVALID'
            except Exception as exc:  # noqa: BLE001 - a parser that breaks refuses the answer (fails closed)
                invalid = 'PARSE_ERROR:' + type(exc).__name__
            else:
                try:
                    verdict = kind.check(obj, inputs)
                    if not isinstance(verdict, Verdict):raise TypeError('not a Verdict')
                except Exception as exc:  # noqa: BLE001 - a checker that breaks refuses the answer (fails closed)
                    verdict = Verdict('REFUSED', why=('CHECK_ERROR:' + type(exc).__name__,))
        if invalid is not None:verdict = Verdict('REFUSED', why=('INVALID:' + invalid,), checks=(('shape', False, invalid),))
    if failed is not None:outcome = 'FAILED'
    elif late:outcome = 'LATE'
    elif verdict is None:outcome = 'FAILED';failed = 'NO_ANSWER'
    else:outcome = verdict.state
    use = outcome in USED
    fb = None if use else kind.fallback(inputs)
    if fb is not None and not isinstance(fb, Fallback):raise TypeError('TURN_FALLBACK: a kind returns a Fallback')
    why = failed or ('LATE' if late else (verdict.why[0] if verdict and verdict.why else ''))
    # 6 · one record
    value = record(kind=kind, request=request, messages=messages, grammar=grammar, said=said, finish=finish, odds=odds,
                   verdict=verdict, outcome=outcome, fallback=None if fb is None else fb.code, why=why, price=price,
                   deadline=deadline, elapsed=elapsed, timings=timings, prompt=prompt, kept=kept, key=key, model=port.model())
    ident = request.ledger.write(value)
    try:
        request.clock.observe(key, kind.name, value)
    except Exception:  # noqa: BLE001 - her clock never stops an answer
        pass
    said = said.with_turn(ident) if said is not None else None
    late_view = verdict.value if late and verdict is not None and verdict.state in ('TAKEN', 'TRIMMED') else None
    return Answer(value=verdict.value if use else fb.value, by_model=use, outcome=outcome,
                  fallback=None if fb is None else fb.code, why=why, verdict=verdict, turn=ident, said=said,
                  price_ms=price, deadline_ms=deadline, elapsed_ms=elapsed, late_view=late_view)


# -- the record: brain.turn/1 ------------------------------------------------------------------------------------------------
def _jsonable(value):
    """A desk object as JSON for the record: dataclasses as dicts, tuples and sets as lists, model words tagged."""
    def norm(v):
        if isinstance(v, ModelSaid):return v.for_record()
        if is_dataclass(v) and not isinstance(v, type):return norm(asdict(v))
        if isinstance(v, dict):return {str(k): norm(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):return [norm(x) for x in v]
        if isinstance(v, (set, frozenset)):return sorted((norm(x) for x in v), key=lambda x: json.dumps(x, sort_keys=True))
        if isinstance(v, Fraction):return str(v)
        if v is None or isinstance(v, (str, int, bool)):return v
        if isinstance(v, float):return v if math.isfinite(v) else None
        return {'unrecorded': type(v).__name__}
    return norm(value)


def _timings(timings):
    out = {}
    for name in ('prompt_n', 'cache_n', 'predicted_n', 'prompt_ms', 'predicted_ms'):
        v = timings.get(name) if isinstance(timings, dict) else None
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):out[name] = int(round(v))
    return out


def record(*, kind, request, messages, grammar, said, finish, odds, verdict, outcome, fallback, why, price, deadline,
           elapsed, timings, prompt, kept, key, model):
    """One brain.turn/1 record (design 3.5)."""
    if outcome not in OUTCOMES:raise ValueError('TURN_OUTCOME: %s' % outcome)
    return {
        'schema': SCHEMA, 'id': uuid.uuid4().hex, 'owner': request.owner, 'at': time.time(), 'state': 'KEPT',
        'request': request.id, 'kind': kind.name, 'version': kind.version, 'brief_sha256': _DIGESTS[kind.name],
        'switch': kind.switch, 'foreground': kind.caps.foreground, 'paper': kind.paper,
        'messages': [{'role': m['role'], 'content': m['content']} for m in messages],
        'grammar_sha256': hashlib.sha256(grammar.encode('utf-8')).hexdigest() if grammar else None,
        'answer': said.for_record() if said is not None else None, 'finish': finish,
        'odds': _jsonable(odds) if odds is not None else None,
        'verdict': None if verdict is None else {'state': verdict.state, 'why': [str(w) for w in verdict.why],
                                                 'checks': _jsonable(list(verdict.checks)), 'kept': _jsonable(verdict.value)},
        'basis': verdict.basis if verdict is not None else None,
        'second_view': _jsonable(verdict.second_view) if verdict is not None and verdict.second_view is not None else None,
        'outcome': outcome, 'fallback': fallback, 'why': why,
        'price_ms': int(price), 'deadline_ms': int(deadline), 'elapsed_ms': int(elapsed),
        'tokens': {'prompt': int(prompt), 'kept_expected': int(kept), 'new': int(prompt - kept),
                   'answer_cap': kind.caps.answer_tokens},
        'timings': _timings(timings), 'key': key, 'model': model,
    }


def tombstone(value, at=None):
    """What Forget leaves: that a turn of this kind was asked and how it ended; no messages, answer, checks or views."""
    return {'schema': SCHEMA, 'id': value['id'], 'owner': value['owner'], 'at': value['at'], 'state': 'FORGOTTEN',
            'forgotten_at': at or time.time(), 'kind': value['kind'], 'version': value['version'],
            'outcome': value['outcome'], 'elapsed_ms': value['elapsed_ms'], 'foreground': value['foreground']}


def said_of(value):
    """The raw answer of a stored turn, as ModelSaid again (None for a tombstone or a turn with no answer)."""
    return ModelSaid.from_record(value.get('answer'), value.get('id', ''))


class MemoryLedger:
    """Turn records held in memory (smoke scripts, a request with no Kernel)."""

    def __init__(self):
        self.rows = {}

    def write(self, value):
        self.rows[value['id']] = json.loads(json.dumps(value));return value['id']

    def get(self, ident):return self.rows[ident]

    def forget(self, ident):
        self.rows[ident] = tombstone(self.rows[ident]);return self.rows[ident]


def ensure(db):
    db.execute('CREATE TABLE IF NOT EXISTS brain_turns(id TEXT PRIMARY KEY, owner TEXT NOT NULL, at REAL NOT NULL, '
               'kind TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL, digest TEXT NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS brain_turns_owner ON brain_turns(owner, at)')


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def prune(db, owner, now=None):
    """Bounded: turns older than KEEP_DAYS and beyond the newest KEEP_TURNS go."""
    now = time.time() if now is None else now
    db.execute('DELETE FROM brain_turns WHERE owner=? AND at<?', (owner, now - KEEP_DAYS * 86400))
    db.execute('DELETE FROM brain_turns WHERE owner=? AND id NOT IN (SELECT id FROM brain_turns WHERE owner=? '
               'ORDER BY at DESC, rowid DESC LIMIT ?)', (owner, owner, KEEP_TURNS))


class KernelLedger:
    """Turn records in the Kernel's database, in their own table: local only, never a desk record, never in a receipt bundle."""

    def __init__(self, kernel, owner):
        self.kernel = kernel;self.owner = owner

    def write(self, value):
        if value['owner'] != self.owner:raise ValueError('TURN_OWNER')
        raw = _canonical(value)
        with self.kernel.db() as db:
            db.execute('BEGIN IMMEDIATE');ensure(db)
            db.execute('INSERT INTO brain_turns VALUES(?,?,?,?,?,?,?)', (value['id'], value['owner'], value['at'], value['kind'],
                       value['state'], raw, hashlib.sha256(raw.encode('utf-8')).hexdigest()))
            prune(db, self.owner, value['at'])
        return value['id']

    def get(self, ident):return get(self.kernel, self.owner, ident)

    def forget(self, ident):return forget(self.kernel, self.owner, ident)


def get(kernel, owner, ident):
    if not isinstance(ident, str) or len(ident) != 32 or any(c not in '0123456789abcdef' for c in ident):
        raise ValueError('TURN_ID_INVALID')
    with kernel.db() as db:
        ensure(db)
        row = db.execute('SELECT payload,digest FROM brain_turns WHERE id=? AND owner=?', (ident, owner)).fetchone()
    if not row:raise ValueError('TURN_UNAVAILABLE: no such turn for this owner')
    if hashlib.sha256(row[0].encode('utf-8')).hexdigest() != row[1]:raise ValueError('TURN_RECORD_DAMAGED')
    return json.loads(row[0])


def forget(kernel, owner, ident):
    """Forget a turn: its record becomes a tombstone. (The operation brain.turn.forget, approve and always asked, and the
    worker restart that clears its memory of the turn come with lane A's A2 and A4.)"""
    value = get(kernel, owner, ident)
    if value['state'] == 'FORGOTTEN':return value
    stone = tombstone(value);raw = _canonical(stone)
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE brain_turns SET state=?, payload=?, digest=? WHERE id=? AND owner=?',
                   ('FORGOTTEN', raw, hashlib.sha256(raw.encode('utf-8')).hexdigest(), ident, owner))
    return stone


def listing(kernel, owner, kind=None, limit=50, before=None):
    """The ledger, newest first: one summary row per turn (no messages, no answer)."""
    query = 'SELECT payload FROM brain_turns WHERE owner=?';params = [owner]
    if kind:query += ' AND kind=?';params.append(kind)
    if before is not None:query += ' AND at<?';params.append(before)
    query += ' ORDER BY at DESC, rowid DESC LIMIT ?';params.append(int(limit))
    with kernel.db() as db:
        ensure(db)
        rows = [json.loads(r[0]) for r in db.execute(query, params)]
    keep = ('id', 'at', 'state', 'kind', 'version', 'outcome', 'fallback', 'why', 'elapsed_ms', 'price_ms', 'deadline_ms',
            'foreground', 'model')
    return [{k: r.get(k) for k in keep if k in r} for r in rows]


# -- the Kernel's operations (0.8.7 E0: the turn ledger, read scope) ---------------------------------------------------------
TURN_ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$', 'minLength': 32, 'maxLength': 32}
FIELDS = {
    'brain.turns': ({'kind': {'type': 'string', 'pattern': '^[A-Z_]{2,16}$', 'maxLength': 16},
                     'limit': {'type': 'integer', 'minimum': 1, 'maximum': 200},
                     'before': {'type': 'number', 'minimum': 0}}, []),
    'brain.turn.get': ({'id': TURN_ID}, ['id']),
    # 0.8.7 A3: the owner's switch per kind (execute, with Undo)
    'brain.help.set': ({'switches': {'type': 'object', 'additionalProperties': False,
                                     'properties': {name: {'type': 'boolean'} for name in SWITCHES}},
                        'undo': {'type': 'boolean'}}, []),
}
SCOPES = {op: 'execute' if op == 'brain.help.set' else 'read' for op in FIELDS}


def dispatch(kernel, op, args, principal):
    if op == 'brain.turns':
        rows = listing(kernel, principal.identity, args.get('kind'), args.get('limit', 50), args.get('before'))
        return {'schema': SCHEMA, 'turns': rows, 'bounded': {'days': KEEP_DAYS, 'turns': KEEP_TURNS}}
    if op == 'brain.turn.get':
        return {'turn': get(kernel, principal.identity, args['id'])}
    if op == 'brain.help.set':
        return set_switches(kernel, args.get('switches'), bool(args.get('undo')))
    raise ValueError('Unknown turn operation')


# -- 0.8.7 A3: the owner's switches per kind ----------------------------------------------------------------------------------
HELP_KEY = 'brain.help'
HELP_PREVIOUS = 'brain.help.previous'
SWITCH_WORDS = {'understanding': 'Understanding your requests', 'reading': 'Reading pages', 'wording': 'Wording her answers',
                'choosing': 'Choosing between next steps', 'talk': 'Talk'}


def set_switches(kernel, changes=None, undo=False):
    """Set the owner's switches (changes: {switch: bool}), or Undo the last setting. With every switch off, Kas is exactly
    0.8.6: no turn is sent, no record written, and every answer is the kind's no-model fallback."""
    if undo and changes:raise ValueError('BRAIN_HELP_ONE_THING: switches or undo, not both')
    if not undo and not changes:raise ValueError('BRAIN_HELP_NOTHING: name a switch to set')
    if changes:
        unknown = sorted(set(changes) - set(SWITCHES))
        if unknown:raise ValueError('BRAIN_HELP_SWITCH: no switch named %s' % unknown[0])
        if any(not isinstance(v, bool) for v in changes.values()):raise ValueError('BRAIN_HELP_SWITCH: on or off')
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT value FROM settings WHERE key=?', (HELP_KEY,)).fetchone()
        current = {name: bool((json.loads(row[0]) if row else {}).get(name, on)) for name, on in SWITCHES.items()}
        if undo:
            prev = db.execute('SELECT value FROM settings WHERE key=?', (HELP_PREVIOUS,)).fetchone()
            if not prev:raise ValueError('BRAIN_HELP_NOTHING_TO_UNDO')
            new = {name: bool(json.loads(prev[0]).get(name, on)) for name, on in SWITCHES.items()}
        else:
            new = {**current, **{name: bool(v) for name, v in changes.items()}}
        db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (HELP_KEY, json.dumps(new, sort_keys=True)))
        db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (HELP_PREVIOUS, json.dumps(current, sort_keys=True)))
    return {'switches': new, 'previous': current, 'all_off': not any(new.values()),
            'words': {name: '%s: %s' % (SWITCH_WORDS[name], 'on' if on else 'off') for name, on in new.items()},
            'undo': {'op': 'brain.help.set', 'args': {'undo': True}}}
