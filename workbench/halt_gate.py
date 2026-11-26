"""HALT's own hold, in the Kernel (Graphite 1.0, K3): the master stop of her managed work, and nothing else.

The owner's paper, section 13: "The Master Kill Switch must stop Kasandra's managed activity without disabling the
owner's desktop or unrelated applications. Individual tasks need their own cancellation controls. An interrupted task
should retain enough evidence for the owner to understand what completed, what remains uncertain, and whether
restarting is safe."

HALT and Stop all are two things, and each reads its own state:
  HALT       her managed work: her assignments, her hand, her model's turns, her sandboxes. Its hold is this module's
             (the setting kas.halt: held, epoch, when, by whom). Graphite's own jobs (an index, a build, a reading you
             started) go on; the desktop, Graphite's window and your programs are never touched.
  Stop all   Graphite's jobs (qt_master_stop, the work gate of work_trail). It still holds her assignments too (they obey
             both holds, assignments._gate), and since 1.0 K3 it spares every process in a session of its own: your
             program windows (spared(), below).

Operations (registered in engineering_kernel under "1.0 K3"):
  halt.status   {}   read     held or not, since when, the epoch
  halt.press    {}   approve  your press. In this order: the hold (no step starts, no model turn is sent); every running
                              assignment is stopped through assignment.stop with HALT's words (its journal says what was
                              done, what was only prepared and that a step was running when you pressed HALT, what it does
                              recorded as it ends); every other open assignment is held, its journal saying the same; her
                              model's reply jobs are cancelled and a model turn running in this process is closed (its
                              request's Stop, guard_request); each stop hook runs (STOP_HOOKS: K6's sandboxes). Returns what
                              it stopped, in titles and counts.
  halt.release  {}   approve  RESUME: lifts this hold only. Nothing stopped is restarted: each assignment has its own Resume,
                              which inspects every step first.

A running step is stopped at its next safe point: an effect not yet sent is not sent (prepared, not done); a model turn in
flight is closed; a wait for an effect (an App's window) ends and the step is "not verified", never "done"; a call
already in the desk's hands finishes and is recorded as it ends, never hidden. Nothing here kills a process.
"""
from __future__ import annotations

import json
import os
import threading
import time
import weakref

KEY = 'kas.halt'
FIELDS = {'halt.status': ({}, []), 'halt.press': ({}, []), 'halt.release': ({}, [])}
SCOPES = {'halt.status': 'read', 'halt.press': 'approve', 'halt.release': 'approve'}
OBSERVERS = ('halt.status',)
STOP_HOOKS = []               # (name, callable(kernel, principal) -> words or ''): K6's sandboxes register here
READ_EVERY_S = 0.5            # a running turn or wait reads the hold at most this often from the database
_LOCAL = {}                   # workspace root -> {'epoch', 'held', 'read'}: this process's last knowledge of the hold
_LOCK = threading.Lock()
_LIVE = weakref.WeakSet()     # her model's turn requests in this process (guard_request)


def register_stop(name, stop):
    """A piece of her managed work that HALT must stop (K6: the sandboxes). stop(kernel, principal) -> words or ''."""
    STOP_HOOKS[:] = [(n, s) for n, s in STOP_HOOKS if n != name] + [(name, stop)]


def now_ms():
    return time.time_ns() // 1000000


def _read(db):
    row = db.execute('SELECT value FROM settings WHERE key=?', (KEY,)).fetchone()
    value = json.loads(row[0]) if row else {'held': False, 'epoch': 0}
    if type(value.get('held')) is not bool or type(value.get('epoch')) is not int:raise ValueError('HALT_STATE_UNREADABLE')
    return value


def status(kernel, db=None):
    """HALT's hold: {'held', 'epoch', 'at', 'by'}. Raises when it cannot be read (the callers decide what that means)."""
    if db is not None:value = _read(db)
    else:
        with kernel.db() as conn:value = _read(conn)
    _note(kernel, value)
    return value


def held(kernel):
    try:return bool(status(kernel)['held'])
    except Exception:  # noqa: BLE001 - a hold that cannot be read is not said to be HALT (the button); K1 holds on it
        return False


def _note(kernel, value):
    with _LOCK:
        _LOCAL[str(getattr(kernel, 'root', ''))] = {'epoch': value['epoch'], 'held': value['held'], 'read': time.monotonic()}


def epoch(kernel):
    try:return status(kernel)['epoch']
    except Exception:  # noqa: BLE001
        return -1


def pressed_since(kernel, since):
    """Whether HALT was pressed (or released) since `since` (an epoch): what this process knows at once, else the database
    at most every READ_EVERY_S. Cheap enough for a stream's every token."""
    root = str(getattr(kernel, 'root', ''))
    with _LOCK:
        local = dict(_LOCAL.get(root) or {})
    if local and local['epoch'] != since:return True
    if local and time.monotonic() - local['read'] < READ_EVERY_S:return False
    try:return status(kernel)['epoch'] != since
    except Exception:  # noqa: BLE001 - unreadable: a running turn is not closed for that alone
        return False


def _owner_only(principal):
    if 'approve' not in principal.scopes or principal.mode == 'Tutor':
        raise ValueError('HALT_IS_YOURS: only your own press holds or lifts her work')


def _write(kernel, principal, held_now, event):
    from . import activity
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE')
        state = _read(db)
        state = {'held': held_now, 'epoch': state['epoch'] + 1, 'at': now_ms(), 'by': principal.identity}
        db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (KEY, json.dumps(state)))
        activity.append(db, activity.make_event(principal.identity, event, 'HELD' if held_now else 'RELEASED'))
    _note(kernel, state)
    return state


def _held_words(value, entries):
    from . import assignments as A
    return A._stopped_words(value, entries, []).replace('Stopped by you. ', 'Held by your HALT. ', 1)


def _hold_one(kernel, ident, principal):
    """An open assignment that was not running: held, and its journal says what was done and what was only prepared."""
    from . import assignments as A
    with A._writing(kernel) as db:
        value = A._load(db, ident, principal)
        if value['state'] in (A.DONE, A.STOPPED, A.RUNNING):return False
        words = _held_words(value, A._entries(db, ident))
        value.update(state=A.HELD, reason='Held by your HALT: resume it once the hold is lifted.', runner=None)
        A._save(db, value);A._journal(db, value, None, 'HALTED', words)
    return True


def _reply_jobs(kernel, principal):
    """Her model's reply jobs (local_brain.REPLY_TOOLS), queued or running: cancelled. Graphite's other jobs go on."""
    out = []
    try:
        from .local_brain import REPLY_TOOLS
        from .operation_stop import TERMINAL
        jobs = kernel.listing('jobs')
    except Exception:  # noqa: BLE001 - no jobs here
        return out
    for job in jobs:
        if job.get('tool') not in REPLY_TOOLS or job.get('state') in TERMINAL:continue
        try:
            answer = kernel.dispatch('jobs.cancel', {'id': job['id']}, principal)
            if answer.get('ok'):out.append(job['tool'])
        except Exception:  # noqa: BLE001
            pass
    return out


def press(kernel, principal):
    """HALT, the Kernel's part: hold, stop, hold, close, cancel; nothing outside her managed work is touched."""
    _owner_only(principal)
    try:
        from .grants import _PERMIT
        if _PERMIT.get() is not None:raise ValueError('HALT_IS_YOURS: HALT is pressed by you, never from inside her work')
    except ImportError:
        pass
    from . import assignments as A
    try:      # the running ones first, read before the hold so they are stopped while their step still runs
        with kernel.db() as db:
            running = [tuple(r) for r in db.execute("SELECT id, json_extract(payload, '$.title') FROM asg_assignments WHERE owner=? AND state=?",
                                                    (principal.identity, A.RUNNING))] if A._present(db) else []
    except Exception:  # noqa: BLE001
        running = []
    report = {'held': True, 'epoch': None, 'stopped': [], 'held_work': [], 'turns': 0, 'jobs': [], 'hooks': [], 'errors': []}
    for ident, title in running:      # stopped first (nothing more of it starts; its journal says a step was running), then the hold
        try:
            A.stop(kernel, ident, principal, why='halt');report['stopped'].append(title or 'an assignment')
        except Exception as exc:  # noqa: BLE001 - one that cannot be stopped is said; the hold still holds it
            report['errors'].append('%s: %s' % (title, str(exc)[:160]))
    state = _write(kernel, principal, True, 'halt.press');report['epoch'] = state['epoch']
    try:rows = A.listing(kernel, {'open': True, 'limit': 100}, principal)['assignments']
    except Exception as exc:  # noqa: BLE001 - no assignments yet
        rows = [];report['errors'].append(str(exc)[:160])
    for row in rows:
        try:
            if row['state'] == A.RUNNING and row['id'] not in {i for i, _ in running}:
                A.stop(kernel, row['id'], principal, why='halt');report['stopped'].append(row['title'])
            elif row['state'] in (A.OPEN, A.HELD) and _hold_one(kernel, row['id'], principal):
                report['held_work'].append(row['title'])
        except Exception as exc:  # noqa: BLE001 - one that cannot be stopped is said; the hold still holds it
            report['errors'].append('%s: %s' % (row.get('title', ''), str(exc)[:160]))
    report['turns'] = sum(1 for request in list(_LIVE) if getattr(request, 'now_asking', None))
    report['jobs'] = _reply_jobs(kernel, principal)
    for name, stop in list(STOP_HOOKS):
        try:
            said = stop(kernel, principal)
            if said:report['hooks'].append(str(said)[:200])
        except Exception as exc:  # noqa: BLE001
            report['errors'].append('%s: %s' % (name, str(exc)[:160]))
    return report


def release(kernel, principal):
    """RESUME: HALT's hold lifted. Nothing is restarted; Stop all's hold, if any, stays its own."""
    _owner_only(principal)
    state = _write(kernel, principal, False, 'halt.release')
    waiting = []
    try:
        from . import assignments as A
        waiting = [r['title'] for r in A.listing(kernel, {'open': True, 'limit': 100}, principal)['assignments']
                   if r['state'] in (A.HELD, A.STOPPED)]
    except Exception:  # noqa: BLE001
        pass
    jobs_held = False
    try:
        from . import work_trail
        jobs_held = bool(work_trail.work_status(kernel)['held'])
    except Exception:  # noqa: BLE001
        pass
    return {'held': False, 'epoch': state['epoch'], 'waiting': waiting, 'jobs_held': jobs_held}


# ---------------------------------------------------------------- her model's turns

def guard_request(kernel, request):
    """turns.request_for: while HALT holds, no turn is sent (each answer is its no-model fallback, "STOPPED"); a turn that
    is running when HALT is pressed is closed through the request's own Stop (request.cancelled, read by the stream)."""
    try:state = status(kernel)
    except Exception:  # noqa: BLE001 - an unreadable hold changes nothing here
        return request
    if state['held']:
        request.port = None;request.off_reason = 'STOPPED'
    since = state['epoch'];before = getattr(request, 'cancelled', None) or (lambda: False)

    def cancelled():
        return bool(before()) or pressed_since(kernel, since)
    request.cancelled = cancelled
    try:_LIVE.add(request)
    except TypeError:  # a request that cannot be watched is still guarded
        pass
    return request


# ---------------------------------------------------------------- what Stop all spares

def spared(pid, own_sid=None, environ=None):
    """Stop all never ends the owner's programs: one started through the session's launch path (S1's session_launch), or
    any process in a session of its own (how programs.* and the Apps start program windows). Graphite's helpers that
    run in a session of their own are stopped by their own authority (jobs, workers, her model, consoles, debug tools)
    or end at their own time limit (a confined run, a capture)."""
    try:
        from . import session_launch
        if any(row.get('pid') == pid for row in session_launch.launched(environ)):return True
    except Exception:  # noqa: BLE001
        pass
    try:
        sid = os.getsid(pid);mine = own_sid if own_sid is not None else os.getsid(0)
    except OSError:
        return False
    return sid != mine


def dispatch(kernel, op, args, principal):
    if op == 'halt.status':
        value = status(kernel)
        return {'held': value['held'], 'epoch': value['epoch'], 'at': value.get('at'), 'by': value.get('by'),
                'words': 'HALT holds her managed work.' if value['held'] else 'HALT is not pressed.'}
    if op == 'halt.press':return press(kernel, principal)
    if op == 'halt.release':return release(kernel, principal)
    raise ValueError('Unknown HALT operation')
