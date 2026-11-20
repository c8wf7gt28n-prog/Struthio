"""Kept briefs: prompt reuse for the turn contract (0.8.7, "Kas's mind with the model, interwoven"; slice A2, lane A).

Every question Kas puts to the model is laid out in four messages (turns.layout): the kind's fixed brief, the stable
part, one fixed line 'Ready.', then the question. The worker runs one slot with context checkpoints and a bounded RAM
prompt cache (local_brain.launch_arguments, sized and counted by the memory rule), and on these hybrid models the
runtime resumes a kept prompt at the start of its last user message (measured by the speed lens). So:

- Priming. After a model is Ready, each registered kind's brief is read once with no answer (max_tokens 0), laid out as
  [brief, PRIME_LINE]: the checkpoint lands where that last user message starts, at the end of the brief, so the first
  real question of the kind re-reads only from there. Nothing is recorded as a turn: nothing was asked.
- Kept. Per worker and per brief (by its sha256): the brief's own tokens once primed, and messages 1 to 3 when the same
  ones were the last asked of that kind. turns.ask prices a question on its new tokens only (LocalPort.kept).
- The watchdog. Every turn compares the server's cache_n with what was expected kept; cache_n more than TOLERANCE short
  is a miss. Two misses in a row re-prime that kind, in the background, and the turn record counts the miss. Misses are
  never errors: they show in the turn record ('reuse') and in the account.
- Forget. The RAM cache and the checkpoints hold the owner's words and pages in the worker's memory. Forgetting a turn
  marks the worker that holds it: from then no question is sent to it (turns: NOT_SENT, FORGETTING), and it is restarted
  once it is idle (local_brain.forget_restart: a brain.activate job of the same selection, so the queue keeps queued
  work and a hold holds it). The new worker is primed with briefs only. Nothing forgotten is sent again: this store
  keeps digests and counts, never text, and a brief is fixed text with no owner data.

The worker writes nothing to disk (no --slot-save-path, no --log-prompts-dir: the seal refuses both); kept briefs are
its memory, nothing else. Only turns.LocalPort calls local_brain.completion on behalf of this module (the turn
contract's rule), through LocalPort.read_prime.
"""
from __future__ import annotations

import copy
import hashlib
import json
import queue
import re
import threading
import time
from fractions import Fraction
from pathlib import Path

SCHEMA = 'brain.kept/1'
KEY = 'kept'                       # local_brain's settings row brain.kept: the live worker's kept briefs
TOLERANCE = 4                      # cache_n this many tokens short of the expected kept prefix is still a hit
MISSES = 2                         # misses in a row that re-prime a kind
PRIME_LINE = 'The question follows.'            # message 2 of a priming read: fixed, no owner data
PRIME_OTHER = 'Another question follows.'       # only tokenized, to find where the brief's shared prefix ends
BACKGROUND = True                  # re-priming runs on one background thread; a smoke script may set False to run inline
OFF_BY = Fraction(1, 10)           # a measured term off by more than this is flagged after a load (design 4.5)
_MEMORY: dict = {}
_LOCK = threading.Lock()


def identity(worker):
    return [worker.get('pid'), worker.get('start'), worker.get('model_id'), worker.get('started')]


def empty(worker):
    return {'schema': SCHEMA, 'worker': identity(worker), 'kinds': {}, 'forget': None, 'readback': None}


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def brief_sha(messages):
    return digest(messages[0]['content'])


def prefix_sha(messages):
    return digest(json.dumps([[m['role'], m['content']] for m in messages[:3]], ensure_ascii=False, separators=(',', ':')))


def shared(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:break
        n += 1
    return n


def new_entry(kind):
    return {'kind': kind.name if kind is not None else None, 'version': kind.version if kind is not None else None,
            'primed': False, 'brief_tokens': 0, 'primed_at': None, 'primes': 0, 'prime_cache_n': None,
            'last_prefix': None, 'prefix_tokens': 0, 'last_cache_n': None, 'misses': 0, 'missed': 0, 'reprimes': 0}


# -- the store: the live worker's kept briefs ----------------------------------------------------------------------------------
class MemoryStore:
    """In this process only (a smoke script, a port with no Kernel)."""

    def load(self, worker):
        with _LOCK:
            held = _MEMORY.get(json.dumps(identity(worker)))
        return copy.deepcopy(held) if held else empty(worker)

    def update(self, worker, change):
        with _LOCK:
            name = json.dumps(identity(worker))
            value = copy.deepcopy(_MEMORY.get(name)) or empty(worker)
            out = change(value)
            _MEMORY.clear();_MEMORY[name] = value          # one worker at a time, as in the app
        return out


class SettingsStore:
    """In the Kernel's settings (brain.kept), so the activation job, the app and the next request see the same thing."""

    def __init__(self, kernel):
        self.kernel = kernel

    def load(self, worker):
        from . import local_brain
        held = local_brain.get(self.kernel, KEY, {}) or {}
        return held if held.get('worker') == identity(worker) else empty(worker)

    def update(self, worker, change):
        from . import local_brain
        with self.kernel.db() as db:
            db.execute('BEGIN IMMEDIATE')
            held = local_brain.get(self.kernel, KEY, {}, db) or {}
            value = held if held.get('worker') == identity(worker) else empty(worker)
            out = change(value)
            local_brain.put(self.kernel, KEY, value, db=db)
        return out


def store_for(kernel):
    return SettingsStore(kernel) if kernel is not None else MemoryStore()


# -- kept: what a question can expect to re-use -------------------------------------------------------------------------------
def expected(store, worker, messages):
    """Tokens of this question the worker should already hold: messages 1 to 3 when they are the last its kind was asked
    with, else the brief when the kind is primed, else 0."""
    entry = store.load(worker)['kinds'].get(brief_sha(messages))
    if not entry:return 0
    if entry['last_prefix'] == prefix_sha(messages) and entry['prefix_tokens']:return int(entry['prefix_tokens'])
    return int(entry['brief_tokens']) if entry['primed'] else 0


def watch(port, kind, messages, kept, timings):
    """The watchdog, after a turn: a miss when cache_n is more than TOLERANCE short of what was expected kept; two in a
    row re-prime the kind. Returns the record's 'reuse' field."""
    cache_n = timings.get('cache_n') if isinstance(timings, dict) else None
    cache_n = int(cache_n) if isinstance(cache_n, (int, float)) and not isinstance(cache_n, bool) else None
    bsha = brief_sha(messages);psha = prefix_sha(messages)

    def change(value):
        entry = value['kinds'].setdefault(bsha, new_entry(kind))
        miss = bool(kept > 0 and cache_n is not None and cache_n < kept - TOLERANCE)
        if kept > 0 and cache_n is not None:
            entry['misses'] = entry['misses'] + 1 if miss else 0
        if miss:entry['missed'] += 1
        in_a_row = entry['misses'];reprime = in_a_row >= MISSES
        if reprime:
            entry['misses'] = 0;entry['primed'] = False;entry['reprimes'] += 1
            entry['last_prefix'] = None;entry['prefix_tokens'] = 0
        entry['last_cache_n'] = cache_n
        return {'expected': int(kept), 'cache_n': cache_n, 'miss': miss, 'misses_in_a_row': in_a_row,
                'reprime': reprime, 'known_prefix': entry['last_prefix'] == psha}

    out = port.store.update(port.worker, change)
    if not out.pop('known_prefix') and cache_n is not None:
        # messages 1 to 3 are now the worker's last prompt of this kind (with a checkpoint where message 4 starts): count them
        try:
            whole = port.tokens(messages)
            upto = port.tokens(list(messages[:3]) + [{'role': 'user', 'content': PRIME_LINE}])
            n = shared(whole, upto)
        except Exception:  # noqa: BLE001 - counting is for speed only; a failure leaves the kind priced cold
            n = 0
        if n:
            def keep(value):
                entry = value['kinds'].setdefault(bsha, new_entry(kind))
                entry['last_prefix'] = psha;entry['prefix_tokens'] = n
            port.store.update(port.worker, keep)
    return out


# -- priming ------------------------------------------------------------------------------------------------------------------
def prime_messages(brief):
    return [{'role': 'system', 'content': brief}, {'role': 'user', 'content': PRIME_LINE}]


def prime(port, kind):
    """Read one kind's brief with no answer. Returns what was kept, or raises turns.PortError."""
    brief = kind.brief()
    messages = prime_messages(brief)
    a = port.tokens(messages)
    b = port.tokens([messages[0], {'role': 'user', 'content': PRIME_OTHER}])
    brief_tokens = shared(a, b)
    got = port.read_prime(messages, prompt_tokens=len(a))
    timings = got.get('timings') or {}
    bsha = digest(brief)

    def change(value):
        entry = value['kinds'].setdefault(bsha, new_entry(kind))
        entry.update(kind=kind.name, version=kind.version, primed=True, brief_tokens=brief_tokens, primed_at=time.time(),
                     primes=entry['primes'] + 1, misses=0,
                     prime_cache_n=timings.get('cache_n') if isinstance(timings.get('cache_n'), int) else None)
        return {'kind': kind.name, 'brief_tokens': brief_tokens, 'prompt_n': timings.get('prompt_n'),
                'cache_n': timings.get('cache_n'), 'elapsed_ms': got.get('elapsed_ms')}
    return port.store.update(port.worker, change)


def kinds_to_prime():
    """Every registered kind, found the way the turn contract finds them (turns.discover)."""
    from . import turns
    try:
        turns.discover()
    except Exception:  # noqa: BLE001 - a module that fails to import primes nothing; the turn itself will say why
        pass
    return list(turns.KINDS.values())


def prime_all(port, kinds=None, cancelled=None):
    done = [];failed = []
    for kind in (kinds_to_prime() if kinds is None else kinds):
        if cancelled is not None and cancelled():break
        try:
            done.append(prime(port, kind))
        except Exception as exc:  # noqa: BLE001 - priming is for speed; a failure leaves that kind cold
            failed.append({'kind': kind.name, 'why': (str(exc) or type(exc).__name__).split(':', 1)[0][:80]})
    return {'primed': done, 'failed': failed}


_QUEUE: queue.Queue = queue.Queue()
_THREAD = None


def _run():
    while True:
        port, kind = _QUEUE.get()
        try:
            prime(port, kind)
        except Exception:  # noqa: BLE001 - the next miss tries again
            pass
        finally:
            _QUEUE.task_done()


def reprime_later(port, kind):
    """Re-prime one kind after two misses: on one background thread (one read at a time), or inline when BACKGROUND is
    False."""
    global _THREAD
    if not BACKGROUND:
        try:
            return prime(port, kind)
        except Exception:  # noqa: BLE001
            return None
    with _LOCK:
        if _THREAD is None or not _THREAD.is_alive():
            _THREAD = threading.Thread(target=_run, name='kept-briefs', daemon=True);_THREAD.start()
    _QUEUE.put((port, kind))
    return None


# -- after a model starts: prime, and read back the memory sum ---------------------------------------------------------------------
def after_start(kernel, worker, cancelled=None, kinds=None):
    """Called by local_brain once a worker is Ready (activation and restore). Primes every registered kind and puts the
    measured memory beside the computed terms. Never raises: priming and readback are for speed and for the record."""
    try:
        from . import turns
        port = turns.LocalPort(worker, kernel)
        primed = prime_all(port, kinds, cancelled)
    except Exception as exc:  # noqa: BLE001
        primed = {'primed': [], 'failed': [{'kind': '*', 'why': type(exc).__name__}]}
    try:
        back = readback(worker)
        store_for(kernel).update(worker, lambda value: value.__setitem__('readback', back))
    except Exception:  # noqa: BLE001
        back = None
    return {'primed': [p['kind'] for p in primed['primed']], 'failed': primed['failed'], 'readback': back}


CHECKPOINT_LOG = re.compile(r'context checkpoint[^\n]*?size\s*=\s*([0-9]+(?:\.[0-9]+)?)\s*MiB')


def readback(worker, log_text=None):
    """After a load (and its priming), the measured figures beside the computed terms (design 4.5): resident memory
    against the estimate, and the runtime's logged checkpoint size against one recurrent state. A term off by more than
    10 % is flagged; nothing changes the rule by itself."""
    from . import local_brain
    terms = worker.get('memory_sum') or (worker.get('config') or {}).get('memory_sum') or {}
    if log_text is None:
        try:
            with (Path(worker['key_file']).parent / 'runtime.log').open('rb') as stream:
                stream.seek(max(0, stream.seek(0, 2) - 1024 * 1024));log_text = stream.read().decode('utf-8', 'replace')
        except (OSError, KeyError, TypeError):
            log_text = ''
    logged = CHECKPOINT_LOG.findall(log_text or '')
    rss = local_brain.usage(worker).get('rss_bytes') if worker.get('pid') else None
    estimate = (worker.get('config') or {}).get('estimated_peak_bytes')
    flags = []
    state = terms.get('state') or 0
    logged_bytes = None
    if logged:
        logged_bytes = int(Fraction(logged[-1]) * 1024 * 1024)
        if state and abs(Fraction(logged_bytes - state, state)) > OFF_BY:flags.append('STATE_TERM_OFF')
    if isinstance(rss, int) and isinstance(estimate, int) and estimate and Fraction(rss - estimate, estimate) > OFF_BY:
        flags.append('RESIDENT_OVER_ESTIMATE')
    return {'at': time.time(), 'computed': terms, 'estimate_bytes': estimate, 'resident_bytes': rss,
            'logged_checkpoint_bytes': logged_bytes, 'logged_checkpoint': 'LOGGED' if logged else 'NOT_LOGGED',
            'flags': flags, 'scope': 'resident memory of the worker process tree; GPU memory is not in it'}


# -- Forget ----------------------------------------------------------------------------------------------------------------------
def forget_pending(kernel, worker):
    """True while the live worker holds something forgotten and has not been restarted."""
    if kernel is None or not worker:return False
    try:
        return bool(SettingsStore(kernel).load(worker).get('forget'))
    except Exception:  # noqa: BLE001 - no settings to read: nothing marked
        return False


def forgotten(kernel, turn, principal=None, reason='TURN_FORGOTTEN'):
    """A turn was forgotten. If the live worker may hold it (it was running when the turn was asked), mark it so no
    question is sent to it, and ask for its restart once idle. Returns NOTHING_HELD, RESTART_QUEUED or RESTART_WAITS
    (marked; the restart waits for the owner: no principal that may restart a model was given, or the queue refused)."""
    from . import local_brain
    worker = local_brain.get(kernel, 'worker', {}) or {}
    if not local_brain.worker_live(worker) or (worker.get('started') or 0) > (turn.get('at') or 0):
        return 'NOTHING_HELD'

    def mark(value):
        value['forget'] = {'at': time.time(), 'reason': reason}
        for entry in value['kinds'].values():           # what was last asked is no longer counted as kept
            entry['last_prefix'] = None;entry['prefix_tokens'] = 0
    SettingsStore(kernel).update(worker, mark)
    if principal is None:return 'RESTART_WAITS'
    try:
        queued = local_brain.forget_restart(kernel, principal, reason)
    except (ValueError, KeyError, TypeError):
        return 'RESTART_WAITS'
    return 'RESTART_QUEUED' if queued else 'RESTART_WAITS'


def summary(kernel, worker):
    """The Brain room's line: which kinds are kept ready, misses, and a pending restart."""
    value = store_for(kernel).load(worker)
    kinds = sorted({e['kind'] for e in value['kinds'].values() if e.get('primed') and e.get('kind')})
    return {'kept': kinds, 'missed': sum(e.get('missed', 0) for e in value['kinds'].values()),
            'reprimes': sum(e.get('reprimes', 0) for e in value['kinds'].values()),
            'forget_pending': bool(value.get('forget')), 'readback': value.get('readback')}
