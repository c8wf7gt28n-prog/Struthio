"""Graphite 1.0 F2 · The floor: the window never waits on her work.

PLAN_1.0.md, F2: "The window never stalls over 100 ms for her work (her model turns, assignments, the board's layout,
relevance and the Machine's D-Bus reads off the window's thread)".

Why the window waited. Every Kernel connection of a workspace is serialised (database_guard: one at a time across threads
and processes), so while her work holds the workspace (a step, its journal, a carry in a worker), any read the window made
on its own thread waited for it, and the reads themselves (a fresh connection each, the schema check, the trail) cost tens
of milliseconds each. Her column read the work every 2.5 s, the head's control every 0.75 s, the Machine and the network
asked the system's services with a timeout of their own, all on the window's thread.

What is here:

  submit(fn, done, key)    fn() runs on one of the floor's worker threads; done(result, error) runs on the window's thread
                           (a queued signal back, never a poll). With a key, one at a time: a second submit while the first
                           runs is kept (the latest only) and runs after it.
  kernel_for(root)         the worker thread's own Kernel on that workspace (each worker keeps one per workspace).
  gather(host, plan, done) the reads a part of the window needs, made off the window's thread through the worker's Kernel
                           (plan(read) calls read(op, args) as the part would), then answered once on the window's thread:
                           while done() runs, answered(host, op, args) gives what was read (MISS for anything not read),
                           so the part draws exactly as it did, from reads that were already made. Observers only: a read
                           changes nothing, so reading it a moment earlier on another thread changes nothing either.
  column_tick(column)      her column's reading (K1's ACTIVE WORK, the working step, her hand, HALT, the grants; the
                           findings and the desk's waiting cards every DESK_EVERY ticks) gathered, then drawn.
  column_soon(column)      the same after a press (forced: with the findings and the desk).
  read_later(key, fn, ...) a slow read of the system (the Machine's D-Bus, the network's state) made on a worker; the part
                           shows what it read last until the new reading lands.
  Heartbeat                with GRAPHITE_STALL_LOG=<file>: a 5 ms beat on the window's thread; every gap over 100 ms is
                           written to the file with what the window's thread was doing (sampled while it was late), for the
                           owner's evening on the ThinkPad. Off by default: nothing is measured or written without it.

Nothing here decides anything: it moves where a read is made, never what is read or what is shown.
"""
from __future__ import annotations

import collections
import json
import os
import queue
import sys
import threading
import time

from PySide6.QtCore import QObject, QTimer, Qt, Signal, Slot

WORKERS = 2                  # at most two of the floor's threads read at once (the window's thread is the third)
MISS = object()              # answered(): not read in this gathering
STALL_MS = 100               # the floor: a gap of the window's event loop over this is a stall
BEAT_MS = 5

_jobs = queue.Queue()
_threads = []
_local = threading.local()
_lock = threading.Lock()
_relay = None
_inflight = {}               # key -> the (fn, done) kept to run after the one in flight (or None)


class _Relay(QObject):
    """Lives on the window's thread: a worker's answer reaches done() through its queued signal."""
    landed = Signal(object)

    def __init__(self):
        super().__init__()
        self.landed.connect(self.deliver, Qt.QueuedConnection)

    @Slot(object)
    def deliver(self, item):
        done, result, error, key = item
        try:
            if done is not None:done(result, error)
        except Exception as exc:  # noqa: BLE001 - a part that cannot draw its reading never takes the window down
            sys.stderr.write('graphite floor: %s\n' % exc)
        finally:
            if key is not None:
                with _lock:
                    following = _inflight.pop(key, None)
                if following is not None:submit(following[0], following[1], key)


def _relay_now():
    global _relay
    if _relay is None:
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError('the floor is started from the window\'s thread')
        _relay = _Relay()
    return _relay


def _work():
    while True:
        fn, done, key = _jobs.get()
        result = error = None
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001 - said to done(), never raised in a worker
            error = exc
        relay = _relay
        if relay is not None:
            try:relay.landed.emit((done, result, error, key))
            except RuntimeError:      # the window has gone: nobody to answer
                pass


def submit(fn, done=None, key=None):
    """fn() on a worker; done(result, error) on the window's thread. Returns False when kept to run after the one in flight."""
    _relay_now()
    with _lock:
        if key is not None:
            if key in _inflight:
                _inflight[key] = (fn, done);return False
            _inflight[key] = None
        while len(_threads) < WORKERS:
            thread = threading.Thread(target=_work, name='graphite-floor-%d' % (len(_threads) + 1), daemon=True)
            _threads.append(thread);thread.start()
    _jobs.put((fn, done, key))
    return True


def busy(key):
    with _lock:
        return key in _inflight


def kernel_for(root):
    """This worker thread's own Kernel on the workspace (never shared between threads: each connection is its own)."""
    kernels = getattr(_local, 'kernels', None)
    if kernels is None:kernels = _local.kernels = {}
    key = str(root)
    if key not in kernels:
        from .engineering_kernel import Kernel
        kernels[key] = Kernel(root)
    return kernels[key]


def held_elsewhere(kernel):
    """Whether another thread of this process holds the workspace's database now (her step, its journal, a carry): a part of
    the window that reads on a timer waits for its next tick rather than for her (database_guard serialises connections)."""
    path = getattr(kernel, 'dbpath', None)
    if path is None:return False
    from pathlib import Path
    from . import database_guard
    try:
        key = str(Path(path).resolve())
        with database_guard._registry_lock:
            lock = database_guard._locks.get(key)
        if lock is None:return False
        if lock.acquire(blocking=False):
            lock.release();return False
        return True
    except Exception:  # noqa: BLE001 - not known: read as before
        return False


def kernel_of(host):
    return getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)


def when_free(host, fn):
    """A window's timer: fn() now, unless her work holds the workspace's database (then at its next tick). host is the
    window, or a part of it (its window is asked at the tick)."""
    def tick():
        window = host
        if not hasattr(window, 'ledger_bridge') and hasattr(window, 'window'):
            try:window = host.window()
            except RuntimeError:      # gone
                return
        if getattr(window, '_closing', False):return
        if held_elsewhere(kernel_of(window)):return
        fn()
    return tick


def head(root):
    """The workspace's change mark: the activity journal's last number (every Kernel request that changes something adds
    to it), read without the guard on a read-only connection (one index lookup). None when it cannot be read."""
    import sqlite3
    from pathlib import Path
    from . import read_beside      # 1.0 F2b: on this thread's kept reader (no path walk, no schema read each time)
    got = read_beside.mark(root)
    if got is not read_beside.MISSING:return got
    try:
        path = Path(root).resolve() / '.ledger/engineering.sqlite3'
        db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=1)
        try:
            row = db.execute('SELECT MAX(seq) FROM activity_journal').fetchone()
        finally:
            db.close()
        return int(row[0] or 0)
    except Exception:  # noqa: BLE001 - not known: read as before
        return None


# ---- reads made off the window's thread, answered on it -----------------------------------------------------------------
def _key(operation, arguments):
    return operation + ' ' + json.dumps(arguments or {}, sort_keys=True, default=str)


def answered(host, operation, arguments=None):
    """What was read for this part in the gathering being drawn now, else MISS (the part reads it itself, as before)."""
    store = getattr(host, '_f2_answers', None)
    if not store:return MISS
    return store.get(_key(operation, arguments), MISS)


def _root_of(host):
    kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    root = getattr(kernel, 'root', None) if kernel is not None else None
    if root is None or getattr(kernel, 'is_host_client', False):root = getattr(host, 'root', None)
    return root


def gather(host, plan, done, key=None, own_thread=False):
    """plan(read) runs on a worker with the worker's Kernel; done() runs on the window's thread with what was read in force
    (answered()). False when nothing could be started (no workspace): the caller reads as before. 1.0 F3: own_thread, on a
    thread of its own (her column's first reading after a start, never behind the floor's queue)."""
    root = _root_of(host)
    if root is None:return False

    def work():
        from .engineering_kernel import operator
        kernel = kernel_for(root);owner = operator();got = {};extra = {}

        def read(operation, arguments=None):
            try:
                answer = kernel.dispatch(operation, arguments or {}, owner)
                value = answer.get('result') if isinstance(answer, dict) and answer.get('ok') else None
            except Exception:  # noqa: BLE001 - read as the part reads it: None when it cannot be read
                value = None
            got[_key(operation, arguments)] = value
            return value
        read.kernel = kernel;read.extra = extra;read.got = got;read.root = root
        plan(read)
        return got, extra

    def landed(result, error):
        if error is not None or result is None:
            done(None);return
        got, extra = result
        host._f2_answers = got;host._f2_extra = extra
        try:done(extra)
        finally:
            host._f2_answers = None;host._f2_extra = None

    if own_thread:      # 1.0 F3
        relay = _relay_now()

        def alone():
            result = error = None
            try:result = work()
            except Exception as exc:  # noqa: BLE001 - said to done(), never raised in a thread
                error = exc
            try:relay.landed.emit((landed, result, error, None))
            except RuntimeError:      # the window has gone
                pass
        threading.Thread(target=alone, name='graphite-floor-first', daemon=True).start()
        return True
    return submit(work, landed, key) or True


def extra(host, name, default=MISS):
    """A value the plan kept beside its reads (read.extra[name]) while its gathering is drawn."""
    store = getattr(host, '_f2_extra', None)
    if not store or name not in store:return default
    return store[name]


# ---- her column ----------------------------------------------------------------------------------------------------------
QUIET_EVERY = 4              # nothing changed and nothing working: her column reads again only every this many ticks
_column_kept = {}            # id(column) -> what its last gathering read: the change mark, the work's reads, the desk's


def column_plan(ident, seen, desk, force=False, work=True, findings=True, cards=True):
    """The reads her column's refresh makes (her_column_qt: read_work, the grants' fold, read_desk), in its own words. When
    the workspace's change mark has not moved and nothing of hers is working, the last reading is drawn again instead (at
    most QUIET_EVERY ticks running), so a quiet desk costs nothing; a press (force) always reads. 1.0 F3: work=False reads
    the desk alone (her work is read in a quick gathering of its own); the work's and the desk's marks are kept apart, a read
    that failed is never kept as "nothing", and two gatherings at once each keep only their own part."""
    def plan(read):
        mark = head(read.root)
        with _lock:
            kept = dict(_column_kept.get(ident) or {})
        mine = {}      # 1.0 F3: what this gathering keeps (merged under the lock at its end)
        same = not force and mark is not None and kept.get('head') == mark
        same_desk = not force and mark is not None and kept.get('desk_head', kept.get('head')) == mark
        if not work:
            pass
        elif same and not kept.get('working') and kept.get('work') is not None and kept.get('work_age', 0) < QUIET_EVERY:
            read.got.update(kept['work']);mine['work_age'] = kept.get('work_age', 0) + 1
            if kept.get('halt') is not None:read.extra['halt'] = kept['halt']
            if (read('brain.status') or {}).get('state') == 'READY':read('brain.models')      # 1.0 F3: her model's state, every tick (a model can stop with nothing else changed)
        else:
            before = set(read.got)
            listing = read('assignment.list', {'open': True, 'limit': 5}) or {}
            rows = list(listing.get('assignments') or ())
            working = next((r for r in rows if r.get('state_words') == 'working'), None)
            if working is not None:read('assignment.status', {'id': working['id']})
            live = read('program.status', {'live': True})
            here = {r.get('id') for r in rows}
            for gone in seen or ():
                if gone not in here:read('assignment.status', {'id': gone})
            read('grant.list', {'waiting': False})
            read('agent.list')      # 1.0 F2b: a 0.8.x assignment left running, listed in ACTIVE WORK (older_work)
            try:
                from . import halt_gate
                read.extra['halt'] = halt_gate.status(read.kernel)
            except Exception:  # noqa: BLE001 - read on the window's thread as before
                pass
            if (read('brain.status') or {}).get('state') == 'READY':read('brain.models')      # 1.0 F3: her model line follows the brain's state
            reads = {k: v for k, v in read.got.items() if k not in before}
            failed = any(v is None for k, v in reads.items() if k.startswith('assignment.list'))
            mine.update(work=None if failed else reads, work_age=0, halt=read.extra.get('halt'), head=mark,
                        working=working is not None or bool((live or {}).get('live')))
        if desk and findings and cards:
            if same_desk and kept.get('desk') is not None and kept.get('desk_age', 0) < QUIET_EVERY:
                read.got.update(kept['desk']);mine['desk_age'] = kept.get('desk_age', 0) + 1
            else:
                before = set(read.got)
                listing = read('investigation.list') or {}
                for inv in list(listing.get('investigations') or ())[:4]:
                    read('investigation.sheet', {'id': inv['id']})
                read('field.read')
                reads = {k: v for k, v in read.got.items() if k not in before}
                failed = any(v is None for k, v in reads.items() if k.startswith(('investigation.list', 'field.read')))
                mine.update(desk=None if failed else reads, desk_age=0, desk_head=mark)
        elif desk:      # 1.0 F3: the findings alone, or the desk's cards alone (each its own gathering, after a press or at a start)
            if findings:
                listing = read('investigation.list') or {}
                for inv in list(listing.get('investigations') or ())[:4]:
                    read('investigation.sheet', {'id': inv['id']})
            if cards:read('field.read')
        with _lock:
            now = dict(_column_kept.get(ident) or {});now.update(mine)
            _column_kept[ident] = now
    return plan


def _column_ok(column):
    host = getattr(column, 'host', None)
    return host is not None and not getattr(host, '_closing', False)


def column_tick(column):
    """Her column's timer: its reading gathered off the window's thread, then drawn (refresh) from it."""
    if not _column_ok(column):return
    face = getattr(column, 'face', None)
    if face is not None and not face.isVisible() and not getattr(column, 'reads_unseen', False):return      # 1.1 B3: her chip on the bar reads her work while her column is out of sight
    if busy(('her-column', id(column))):return      # a reading is on its way (a press's, perhaps): this tick is that one
    from .her_column_qt import DESK_EVERY
    desk = (column.ticks + 1) % DESK_EVERY == 1
    seen = set((getattr(column, 'seen_work', None) or {}).keys())
    gen = getattr(column, '_f3_gen', 0)      # 1.0 F3: a reading begun before your press is not drawn over what the press showed
    started = gather(column.host, column_plan(id(column), seen, desk), lambda extra: _column_draw(column, False, ('work', 'desk') if desk else ('work',))
                     if getattr(column, '_f3_gen', 0) == gen else None,      # 1.0 F3: drawn as gathered (the desk only when it was read)
                     key=('her-column', id(column)))
    if not started:column.refresh()


def column_soon(column, first=False):
    """After a press: her column read again off the window's thread, then drawn. 1.0 F3: her work first, in a quick gathering
    of its own (ACTIVE WORK follows a Stop at once), then the findings and the desk; at a start (first) each on a thread of
    its own, so what the journal and the desk hold is said at once, never "nothing" while it is being read."""
    if not _column_ok(column):return
    column._f3_gen = getattr(column, '_f3_gen', 0) + 1      # 1.0 F3: readings begun before this press are not drawn
    seen = set((getattr(column, 'seen_work', None) or {}).keys())
    started = gather(column.host, column_plan(id(column), seen, False, force=True), lambda extra: _column_draw(column, True, ('work',)),
                     key=('her-column-work', id(column)), own_thread=first)
    if not started:column.refresh(force=True);return
    gather(column.host, column_plan(id(column), seen, True, force=True, work=False, cards=False), lambda extra: _column_draw(column, True, ('findings',)),
           key=('her-column', id(column)), own_thread=first)      # FINDINGS, said before the whole desk is read
    gather(column.host, column_plan(id(column), seen, True, force=True, work=False, findings=False), lambda extra: _column_draw(column, True, ('cards',)),
           key=('her-column-cards', id(column)), own_thread=first)      # the desk's cards for NEXT STEPS


def _column_draw(column, force, parts=None):
    if not _column_ok(column):return
    try:column.refresh(force=force, parts=parts)      # 1.0 F3: parts
    except RuntimeError:      # the column went with its window
        pass


def halt_status(host, kernel):
    """HALT's hold for her column: as gathered, else read now (halt_gate.status)."""
    value = extra(host, 'halt')
    if value is not MISS:return value
    from . import halt_gate
    return halt_gate.status(kernel)


# ---- slow reads of the system (the Machine, the network) ----------------------------------------------------------------
_kept = {}


def read_later(key, fn, landed=None, most_ms=None):
    """The last reading of key now (MISS before the first), and fn() read again on a worker when none is in flight; landed()
    runs on the window's thread when the new reading is kept."""
    def done(result, error):
        if error is None:
            with _lock:
                _kept[key] = (time.monotonic(), result)
            if landed is not None:landed(result)
    with _lock:
        held = _kept.get(key)
    fresh = held is not None and most_ms is not None and (time.monotonic() - held[0]) * 1000 < most_ms
    if not fresh:submit(fn, done, key=('read-later', key))
    return held[1] if held is not None else MISS


def kept(key):
    with _lock:
        held = _kept.get(key)
    return held[1] if held is not None else MISS


def forget(key):
    with _lock:
        _kept.pop(key, None)


# ---- the application's event filters, shared (the cold start) -----------------------------------------------------------
class FilterHub(QObject):
    """One event filter on the application, in front of the window's own (a dozen and more: menus, the pointer, the reading
    size, the Agenda, the context menu, her hand's touch, ...). Qt called each of them from C++ for every event of the window,
    each asking the event its type (a Python enum made afresh every time): measured here, the window's first paint came
    2.9 s sooner without them (8.3 s against 5.4 s). Now Qt calls this one; it asks the type once, hands Qt's bookkeeping
    (QUIET) to none of them, and calls theirs from Python in Qt's own order (the last installed first; installed again, it
    moves to the front), stopping at the first that takes the event. A filter whose object has gone is dropped, as Qt drops
    it. Set GRAPHITE_FILTER_HUB=0 to have Qt call each of them again."""

    # Qt's own bookkeeping, sent by the tens of thousands while the window is made and laid out; not one of the window's
    # filters on the application looks at any of these (each looks at input, Show, Hide, Polish, Resize, focus or the
    # window's state), so they are not handed to them. A filter that must see them installs itself on the application with
    # QCoreApplication.installEventFilter(app, filter), past the hub.
    QUIET = ('ChildAdded', 'ChildPolished', 'ChildRemoved', 'DynamicPropertyChange', 'LayoutRequest', 'MetaCall', 'Timer',
             'UpdateRequest', 'UpdateLater', 'Paint', 'Move', 'StyleChange', 'FontChange', 'PaletteChange', 'ApplicationFontChange',
             'ApplicationPaletteChange', 'ZOrderChange', 'ParentChange', 'ParentAboutToChange', 'PolishRequest', 'DeferredDelete',
             'StyleAnimationUpdate', 'ToolTipChange', 'WindowTitleChange', 'WindowIconChange', 'ActionAdded', 'ActionChanged',
             'ActionRemoved', 'ShowToParent', 'HideToParent', 'PlatformSurface', 'LocaleChange', 'LanguageChange',
             'ScreenChangeInternal', 'ContentsRectChange', 'EnabledChange', 'ModifiedChange', 'ReadOnlyChange',
             'AccessibilityPrepare', 'Clipboard', 'SockAct', 'Quit', 'ThreadChange', 'UpdateSoftKeys', 'WinIdChange')

    def __init__(self, app):
        super().__init__(app)
        self.filters = []
        from PySide6.QtCore import QEvent
        self.quiet = frozenset(getattr(QEvent.Type, name) for name in self.QUIET if hasattr(QEvent.Type, name))

    def add(self, obj):
        if obj is None or obj is self:return None
        self.filters = [obj] + [f for f in self.filters if f is not obj]
        return None

    def remove(self, obj):
        self.filters = [f for f in self.filters if f is not obj]
        return None

    def eventFilter(self, obj, event):
        if not self.filters or event.type() in self.quiet:return False
        from shiboken6 import Shiboken
        for f in tuple(self.filters):
            if not Shiboken.isValid(f):
                self.remove(f);continue
            try:
                if f.eventFilter(obj, event):return True
            except Exception:  # noqa: BLE001 - as Qt does with a Python filter that raised: said, and the event goes on
                import traceback
                traceback.print_exc()
        return False


def share_app_filters(app):
    """qt_app.make_app: the window's filters on the application go through one FilterHub (the Python callers' install and
    remove reach it; Qt's own and those installed before this keep their place)."""
    if app is None or getattr(app, '_f2_hub', None) is not None:return None
    if os.environ.get('GRAPHITE_FILTER_HUB', '').strip() == '0':return None
    from PySide6.QtCore import QCoreApplication
    hub = FilterHub(app)
    QCoreApplication.installEventFilter(app, hub)
    app._f2_hub = hub
    app.installEventFilter = hub.add      # an attribute of this one object: the window's code calls these on the application
    app.removeEventFilter = hub.remove
    return hub


# ---- the heartbeat (the owner's measure; off unless GRAPHITE_STALL_LOG names a file) -----------------------------------
class Heartbeat(QObject):
    """A beat every BEAT_MS on the window's thread. A sampler thread reads the window's thread's stack while a beat is late;
    each gap over STALL_MS is written (JSON, one line) with its length and the part of Graphite the window's thread was in."""

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = str(path);self.last = time.perf_counter();self.samples = {};self.guard = threading.Lock();self.on = True
        self.main = threading.main_thread().ident;self.longest = 0.0;self.count = 0
        self.timer = QTimer(self);self.timer.setTimerType(Qt.PreciseTimer);self.timer.setInterval(BEAT_MS)
        self.timer.timeout.connect(self.beat);self.timer.start()
        threading.Thread(target=self.sample, name='graphite-heartbeat', daemon=True).start()

    def beat(self):
        now = time.perf_counter();gap = (now - self.last) * 1000.0
        with self.guard:
            stacks = self.samples.pop(self.last, [])
        if gap >= STALL_MS:
            self.count += 1;self.longest = max(self.longest, gap)
            row = {'at': time.strftime('%H:%M:%S'), 'ms': int(gap), 'in': offender(stacks)}
            try:
                with open(self.path, 'a', encoding='utf-8') as out:out.write(json.dumps(row) + '\n')
            except OSError:
                pass
        self.last = now

    def sample(self):
        while self.on:
            time.sleep(0.01)
            last = self.last
            if time.perf_counter() - last < 0.04:continue
            frame = sys._current_frames().get(self.main);stack = []
            while frame is not None:
                name = frame.f_code.co_filename
                if 'workbench' in name:stack.append('%s.%s' % (os.path.basename(name)[:-3], frame.f_code.co_name))
                frame = frame.f_back
            with self.guard:
                self.samples.setdefault(last, []).append(tuple(reversed(stack)))

    def stop(self):
        self.on = False;self.timer.stop()


def offender(stacks):
    """The part most often seen while the window was late: the outermost and innermost of Graphite's frames."""
    count = collections.Counter()
    for stack in stacks:
        if not stack:count['(Qt or the system)'] += 1;continue
        count[stack[0] if stack[0] == stack[-1] else stack[0] + ' .. ' + stack[-1]] += 1
    return count.most_common(1)[0][0] if count else '(not sampled)'


def install_heartbeat(host):
    """With GRAPHITE_STALL_LOG set, the window's heartbeat writes its stalls there (qt_app calls this once)."""
    path = os.environ.get('GRAPHITE_STALL_LOG', '').strip()
    if not path or getattr(host, '_f2_heartbeat', None) is not None:return None
    host._f2_heartbeat = Heartbeat(path, host)
    return host._f2_heartbeat
