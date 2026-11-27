"""Graphite 1.0 F3 · presses whose Kernel work is done off the window's thread (the walkthroughs' faults, item 5).

X4 measured the window's thread held for seconds by a few presses: TRACE and CHECK ALL (4.2 s), HALT and RESUME (1.5 to
1.8 s). Each press keeps its own logic; only where its reads and writes run changes:

    run_alone(fn, done)      fn() on a thread of its own (never behind the floor's queue: HALT must not wait for a reading);
                             done(result, error) on the window's thread, through the floor's relay.
    with_reads(host, rehearse, perform)
                             the press rehearsed on a floor worker with a Recorder on the worker's own Kernel (every read it
                             makes is kept, its answer as the Kernel gave it); then performed on the window's thread with the
                             window's Kernel answering those same reads from what was kept (a Replayer): the press's own code
                             runs unchanged, and its reads cost the window nothing. Only reads (CAPABILITIES 'read') are ever
                             kept or answered from what was kept; a change always runs for real, on the window's Kernel.
    prefetch(operation, arguments) / take(operation, arguments)
                             one read made on a worker before a press needs it (TRACE's line), taken once by the press.

Nothing here decides anything: what a press reads is what the Kernel answered a moment before, on the same workspace.
"""
from __future__ import annotations

import json
import threading
import time

from . import floor

KEEP_S = 30.0                # a prefetched answer is taken within this long, or read again
_LOCK = threading.Lock()


def _key(operation, arguments):
    return str(operation) + ' ' + json.dumps(arguments or {}, sort_keys=True, default=str)


def _reads(operation):
    try:
        from .engineering_kernel import CAPABILITIES
        return CAPABILITIES.get(operation) == 'read'
    except Exception:  # noqa: BLE001 - not known: never answered from what was kept
        return False


class Recorder:
    """A worker's Kernel that keeps what each read answered (a change is never made here: refused before it is sent)."""

    def __init__(self, kernel):
        self._kernel = kernel;self.seen = {}

    def dispatch(self, operation, arguments, principal, *a, **k):
        if not _reads(operation):
            return {'ok': False, 'error': {'code': 'REHEARSAL', 'message': 'a change is made only when the press is performed'}}
        answer = self._kernel.dispatch(operation, arguments, principal, *a, **k)
        self.seen.setdefault(_key(operation, arguments), answer)
        return answer

    def __getattr__(self, name):
        return getattr(self._kernel, name)


class Replayer:
    """The window's Kernel, answering each kept read once from what was kept; everything else as it always does."""

    def __init__(self, kernel, seen):
        self._kernel = kernel;self.seen = dict(seen or {});self.hits = 0;self.misses = 0

    def dispatch(self, operation, arguments, principal, *a, **k):
        if _reads(operation):
            hit = self.seen.pop(_key(operation, arguments), None)
            if hit is not None:
                self.hits += 1;return hit
        self.misses += 1
        return self._kernel.dispatch(operation, arguments, principal, *a, **k)

    def __getattr__(self, name):
        return getattr(self._kernel, name)


def run_alone(fn, done=None, name='graphite-press'):
    """fn() on a thread of its own; done(result, error) on the window's thread."""
    relay = floor._relay_now()

    def alone():
        result = error = None
        try:result = fn()
        except Exception as exc:  # noqa: BLE001 - said to done(), never raised in a thread
            error = exc
        try:relay.landed.emit((done, result, error, None))
        except RuntimeError:      # the window has gone
            pass
    threading.Thread(target=alone, name=name, daemon=True).start()
    return True


def kernel_root(host):
    kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    return getattr(kernel, 'root', None) or getattr(host, 'root', None)


def with_reads(host, rehearse, perform, key=None):
    """rehearse(recorder, principal) on a floor worker; then perform() on the window's thread with the window's Kernel (its
    ledger_bridge's) answering the reads rehearsed. Without a workspace Kernel, perform() at once, as before."""
    bridge = getattr(host, 'ledger_bridge', None)
    root = floor._root_of(host)
    if bridge is None or getattr(bridge, 'kernel', None) is None or root is None:
        return perform()

    def work():
        from .engineering_kernel import operator
        recorder = Recorder(floor.kernel_for(root))
        try:rehearse(recorder, operator())
        except Exception:  # noqa: BLE001 - what could not be rehearsed is read as before, when performed
            pass
        return recorder.seen

    def done(seen, error):      # (run on a thread of its own: a long rehearsal never holds her column's readings back)
        if getattr(host, '_closing', False):return
        real = bridge.kernel
        replay = Replayer(real, seen if error is None else {})
        bridge.kernel = replay
        try:perform()
        finally:
            if bridge.kernel is replay:bridge.kernel = real
        host._f3_replayed = (replay.hits, replay.misses)
    if key is not None:
        with _LOCK:
            if key in _BUSY:return None      # the same press already on its way
            _BUSY.add(key)

    def landed(seen, error):
        with _LOCK:_BUSY.discard(key)
        done(seen, error)
    run_alone(work, landed, name='graphite-rehearsal')
    return None


# ---- one read made before a press needs it ------------------------------------------------------------------------------
_KEPT = {}
_BUSY = set()


def prefetch(host, operation, arguments, then):
    """operation (a read) on a floor worker; then() on the window's thread once its answer is kept for take()."""
    root = floor._root_of(host)
    if root is None or not _reads(operation):
        then();return False

    def work():
        from .engineering_kernel import operator
        return floor.kernel_for(root).dispatch(operation, arguments or {}, operator())

    def done(answer, error):
        if error is None and isinstance(answer, dict):
            with _LOCK:_KEPT[_key(operation, arguments)] = (time.monotonic(), answer)
        if not getattr(host, '_closing', False):then()
    run_alone(work, done, name='graphite-prefetch')      # a thread of its own: never behind her column's readings
    return True


def take(operation, arguments):
    """The answer prefetched for this read (once), or None."""
    with _LOCK:
        held = _KEPT.pop(_key(operation, arguments), None)
    if held is None or time.monotonic() - held[0] > KEEP_S:return None
    return held[1]
