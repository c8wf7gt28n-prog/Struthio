"""The door's mechanics (Graphite 1.0, F1): one stop rule for her hand wherever it drives, the window put back as it was, and
her changes at your dial with one Undo.

The owner's paper, section 13: "A task should also be stoppable ... An interrupted task should retain enough evidence for the
owner to understand what completed, what remains uncertain, and whether restarting is safe." The plan's F1: "A touch stops
her: any owner input in the window while her hand drives it pauses the hand at once (the stop between presses); she puts the
window back as it was (focus, tab, selection, scroll) when she finishes or stops; changes through her hand at the owner's
dial with one Undo."

"The window" is either of two, and one rule covers both (DOOR, one per process):
  desk      Graphite's own window, driven by her hand on the desk (her_hand_qt.HerHand, her door in desk_doers). Your input
            there is a press of the mouse, a key or a touch that the window system delivers (her own presses go to widgets,
            never to a window), seen by her_hand_qt's filter.
  program   a program window of yours that her hand drives (a11y_hand, K9). Your input is any key, button or pointer move
            the X server sees that is not in her ledger of synthetic events (a11y_hand.Touch).

THE STOP RULE. While her hand drives (begin() .. finish()), your input pauses it at once: touched() marks the door paused, and
her next press is refused (check(), the stop between presses: never halfway through a click, never between the two halves of
a replace). A paused hand holds the window exactly as it is, and waits for your word:
  Continue  (carry_on(), your press: her column's Continue, a press of yours that carries her work on) — she goes on from
            where the window is now; nothing she did is repeated without being looked at first (K1's resume does that).
  Stop      (stop(), your press: her card's or her column's Stop, door.stop) — the window is put back as it was when she
            began: what she opened over it is closed, the focus, the tab, the selection, the text cursor and the scroll are
            back. What she changed stays changed (a change is taken back by its own Undo, below); the words say what came back
            and what could not.
HALT stops her the same way (its words: stopped by HALT), and nothing is put back while HALT holds: putting back is acting.
When she finishes a sequence herself (finish()), she gives back what was yours and not hers to keep: your keyboard focus and
the text cursor in it, the window that was in front, and anything she left open over it. What she was asked to show stays.

PUTTING A PROGRAM WINDOW BACK (program_snapshot, program_put_back; through accessibility, as K9 acts):
  - the menus she opened are closed: a menu is open when its node is SELECTED; it is closed with the Escape key (XTest, in her
    ledger, so it is never taken for your touch), one level at a time, looking again after each, and only while her program
    has the keyboard (else her window is brought forward first, and yours brought back after). Never one Escape more than a
    menu is open (one more would clear your selection in the document);
  - the control that had the focus gets it back (Component.GrabFocus); the text cursor (Text.SetCaretOffset) and the
    selection (Text.SetSelection / AddSelection) come back where they were, read back to be sure;
  - its place on the screen (Component.GetExtents of that control: how far the view is scrolled) is compared, and scrolled
    back (Text.ScrollSubstringTo) where the program offers it;
  - the window that was in front is in front again (windows_x11, _NET_ACTIVE_WINDOW).
  A dialog open over her window is never answered or closed by a put back: it stays yours.
Its own allow-list (PUT_BACK): the reader's reads, a few reads of the text cursor and selection, and four acts that only put
back (GrabFocus, SetCaretOffset, SetSelection, AddSelection); nothing here presses a control or types a word.

PUTTING GRAPHITE'S WINDOW BACK is hand_door_qt's (focus and its text cursor, the work tabs, the selection in the lists and
trees, every scroll, the Field's zoom), after the planner's own put back (what is in front, the selected sheet, what is over
the work: her_hand_qt.HerHand.put_back).

CHANGES AT YOUR DIAL, WITH ONE UNDO (the desk; 0.8.8's "Changes through her hand"): her door lets a change act through only as
her dial says (desk_acts.desk_hers, stacy_hand.hers): at Do and show and Free hand an ordinary change is done at once, with its
card and its line in her trail; at Ask first, or for what always asks, or on the model's pick alone, the change waits on its
card for your Approve, whatever she planned. Each change she made in a turn can be taken back, and her card's "Undo my
changes" takes back all of that turn's changes at once, the latest first, each by its own guarded Undo line (changes_of,
undo_lines): one Undo.

Kernel operations (registered in engineering_kernel and engineering_cli under "1.0 F1"):
  door.state           {}   read     where her hand drives, whether it is paused and why, what it did, what came back
  door.continue  {}   approve  your Continue: a paused hand may go on
  door.stop      {}   approve  your Stop: the window put back as it was

No floating point in anything checked: times are whole milliseconds, places and scrolls whole pixels and whole steps.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

SCHEMA = 'graphite.hand-door/1'
HANDS = ('desk', 'program')
STATES = ('resting', 'driving', 'paused', 'stopped', 'finished')
WHERE = {'desk': "The computer's window", 'program': 'your program'}
FINISH_PARTS = ('menus', 'focus', 'caret', 'selection', 'window')       # what she gives back when she finishes herself
ALL_PARTS = ('menus', 'focus', 'caret', 'selection', 'place', 'window', 'tabs', 'scroll', 'zoom', 'lists')
SETTLE_MS = 250
ESCAPES_MOST = 6
KEPT_ACTS = 24


class Paused(Exception):
    """Her next press is refused: your input paused her hand (or HALT stopped it). Nothing more is pressed."""

    def __init__(self, why, words):
        super().__init__(words);self.why = why;self.words = words


def _now_ms():
    return time.time_ns() // 1000000


def _word(key):
    try:
        from . import state_words
        return state_words.said(key)
    except Exception:  # noqa: BLE001 - the words without the shape are still the words
        return {'stopped': 'stopped by you', 'stopped_halt': 'stopped by HALT', 'done': 'done (verified)'}.get(key, key)


class Door:
    """Her hand's door in this process: which window she drives, whether your input paused her, and what puts it back."""

    def __init__(self):
        self.lock = threading.RLock();self.watchers = []
        self._reset()

    def _reset(self):
        self.hand = '';self.state = 'resting';self.why = '';self.what = '';self.words = '';self.program = '';self.title = ''
        self.acts = [];self.snapshot = None;self.restore = None;self.carry = None;self.since = 0;self.touched_at = 0;self.touches = 0
        self.back = None;self.assignment = '';self.step = '';self.paused_after = None

    # ---------------------------------------------------------------- her hand takes the window
    def begin(self, hand, words='', snapshot=None, restore=None, carry=None, program='', title='', assignment='', step=''):
        """Her hand starts a sequence of presses in this window. A pause not yet answered holds: she does not start again
        until you said Continue or Stop (PAUSED). `restore(snapshot, parts)` puts the window back; `carry()` goes on."""
        if hand not in HANDS:raise ValueError('HAND: her hand drives the desk or a program window')
        with self.lock:
            if self.state == 'paused':
                raise Paused(self.why or 'touch', 'PAUSED: my hand waits for your word since %s (%s): Continue, or Stop to put the window back'
                             % ('HALT stopped it' if self.why == 'halt' else 'your touch', self.what or WHERE.get(self.hand, 'the window')))
            self._reset()
            self.hand = hand;self.state = 'driving';self.words = str(words or '')[:300];self.snapshot = snapshot;self.restore = restore
            self.carry = carry;self.program = str(program or '')[:120];self.title = str(title or '')[:300];self.since = _now_ms()
            self.assignment = str(assignment or '');self.step = str(step or '')
        self._tell()
        return self.view()

    def driving(self, hand=None):
        with self.lock:return self.state == 'driving' and (hand is None or self.hand == hand)

    def paused(self, hand=None):
        with self.lock:return self.state == 'paused' and (hand is None or self.hand == hand)

    # ---------------------------------------------------------------- your input, between two of her presses
    def touched(self, hand, what='your touch'):
        """Your input in the window her hand drives: paused at once (her next press is refused). True when it paused her
        now; a touch while she rests, or in a window she does not drive, is yours alone and changes nothing."""
        with self.lock:
            if self.state != 'driving' or (hand and self.hand != hand):
                if self.state == 'paused' and (not hand or self.hand == hand):self.touches += 1
                return False
            self.state = 'paused';self.why = 'touch';self.what = str(what or 'your touch')[:120];self.touched_at = _now_ms()
            self.touches += 1;self.paused_after = len(self.acts)
        self._tell()
        return True

    def halted(self, hand=None):
        """HALT: her hand is stopped before its next press, like a touch, with HALT's words; nothing is put back while HALT holds."""
        with self.lock:
            if self.state != 'driving' or (hand and self.hand != hand):return False
            self.state = 'paused';self.why = 'halt';self.what = 'HALT';self.touched_at = _now_ms();self.paused_after = len(self.acts)
        self._tell()
        return True

    def check(self, act=''):
        """Before each of her presses: Paused when your input paused her, with what was done and what was not."""
        with self.lock:
            if self.state != 'paused':return
            done = ('done: ' + '; '.join(self.acts[-3:])) if self.acts else 'nothing of it was done'
            words = '%s (%s): %s; “%s” was not done' % (_word('stopped_halt' if self.why == 'halt' else 'stopped'), self.what, done, act or 'the next press')
            raise Paused(self.why or 'touch', words)

    def acted(self, words):
        with self.lock:
            self.acts.append(str(words or '')[:160]);self.acts = self.acts[-KEPT_ACTS:]
        self._tell()

    # ---------------------------------------------------------------- your word
    def carry_on(self, hand=None):
        """Your Continue: a paused hand goes on from where the window is now (its own carry, when it has one)."""
        with self.lock:
            if self.state != 'paused' or (hand and self.hand != hand):return {'carried': False, 'words': 'My hand is not paused; nothing to carry on.'}
            if self.why == 'halt' and _halt_holds():return {'carried': False, 'words': 'HALT holds my work: lift it first (RESUME), then Continue.'}
            carry = self.carry;self.state = 'driving' if carry is not None else 'resting';self.why = '';self.what = ''
        out = {'carried': True, 'words': 'My hand goes on from where the window is now.', 'hand': self.hand}
        if carry is not None:
            try:
                said = carry()
                if said:out['words'] = str(said)[:300]
            except Exception as exc:  # noqa: BLE001 - her hand going on never takes the window down
                out['words'] = 'My hand could not go on: %s' % str(exc)[:200]
        self._tell()
        return out

    def stop(self, parts=ALL_PARTS):
        """Your Stop: she stops for good and the window is put back as it was when she began (what came back, in words)."""
        with self.lock:
            if self.state not in ('driving', 'paused'):
                return {'back': None, 'words': 'My hand is not moving; the window is yours as it is.', 'state': self.state}
            if self.why == 'halt' and _halt_holds():
                return {'back': False, 'words': 'HALT holds my work, and putting the window back is acting: lift HALT first, then Stop.', 'state': self.state}
            restore, snap = self.restore, self.snapshot
            self.state = 'stopped';self.why = self.why or 'stop'
        back = _run_restore(restore, snap, parts)
        with self.lock:self.back = back
        self._tell()
        return dict(back, state='stopped')

    def finish(self, words='', parts=FINISH_PARTS):
        """Her sequence ended by itself: what was yours is given back (your focus, your cursor, the window in front, anything
        she left open over it); what she was asked to show stays."""
        with self.lock:
            if self.state != 'driving':return {'back': None, 'words': '', 'state': self.state}
            restore, snap = self.restore, self.snapshot
            self.state = 'finished';self.words = str(words or self.words)[:300]
        back = _run_restore(restore, snap, parts)
        with self.lock:self.back = back
        self._tell()
        return dict(back, state='finished')

    def leave(self, hand=None):
        """Her sequence ends with nothing to give back (a refusal before her first press): the door rests."""
        with self.lock:
            if self.state == 'driving' and (hand is None or self.hand == hand):self.state = 'finished'
        self._tell()

    def forget(self):
        """Your own new request starts afresh: an earlier pause is settled as it stands (nothing more is put back)."""
        with self.lock:
            if self.state == 'paused':self.state = 'stopped';self.why = self.why or 'touch'
        self._tell()

    # ---------------------------------------------------------------- what her column and the Kernel read
    def view(self):
        with self.lock:
            key = {'paused': 'stopped_halt' if self.why == 'halt' else 'stopped', 'stopped': 'stopped', 'finished': 'done'}.get(self.state, '')
            if self.state == 'driving':said = '▸ my hand drives %s' % (self.program or WHERE.get(self.hand, 'the window'))
            elif self.state == 'paused':said = '%s, in %s: Continue, or Stop to put the window back' % (_word(key), self.program or WHERE.get(self.hand, 'the window'))
            elif self.state == 'stopped':said = (self.back or {}).get('words') or _word('stopped')
            elif self.state == 'finished':said = (self.back or {}).get('words') or ''
            else:said = ''
            return {'schema': SCHEMA, 'hand': self.hand, 'state': self.state, 'why': self.why, 'what': self.what, 'word': _word(key) if key else '',
                    'words': said, 'doing': self.words, 'program': self.program, 'title': self.title, 'acts': list(self.acts),
                    'paused_after': self.paused_after, 'touches': self.touches, 'since': self.since, 'back': self.back,
                    'assignment': self.assignment, 'step': self.step, 'snapshot': _said_snapshot(self.snapshot)}

    def _tell(self):
        view = self.view()
        for hook in list(self.watchers):
            try:hook(view)
            except Exception:  # noqa: BLE001 - a watcher of the door never stops it
                pass


DOOR = Door()


def _halt_holds():
    """Whether HALT holds her work now (read through K3's gate where a Kernel is at hand; else the door's own word)."""
    kernel = _KERNEL.get('kernel')
    if kernel is None:return False
    try:
        from . import halt_gate
        return bool(halt_gate.held(kernel))
    except Exception:  # noqa: BLE001
        return False


_KERNEL = {}


def _run_restore(restore, snap, parts):
    if restore is None or snap is None:return {'back': None, 'words': 'There was nothing to put back.', 'parts': {}}
    try:
        out = restore(snap, tuple(parts)) or {}
    except Exception as exc:  # noqa: BLE001 - a put back that fails says so; the window is never taken down by it
        out = {'back': False, 'words': 'I could not put the window back: %s' % (str(exc)[:200] or type(exc).__name__), 'parts': {}}
    out.setdefault('parts', {})
    if 'back' not in out:out['back'] = all(v.get('back', True) for v in out['parts'].values()) if out['parts'] else True
    if not out.get('words'):out['words'] = _words_of(out)
    return out


def _words_of(out):
    parts = out.get('parts') or {}
    back = [p['words'] for p in parts.values() if p.get('back') and p.get('words')]
    not_back = [p['words'] for p in parts.values() if p.get('back') is False and p.get('words')]
    if out.get('back') and back:return 'The window is back as it was: %s.' % '; '.join(back)
    if out.get('back'):return 'The window is back as it was.'
    return 'I put back what I could%s; not back: %s.' % ((': ' + '; '.join(back)) if back else '', '; '.join(not_back) or 'the window is not as it was')


def _said_snapshot(snap):
    """The snapshot as plain words and values (no live objects, no text of yours)."""
    if not isinstance(snap, dict):return None
    keep = {}
    for k, v in snap.items():
        if k.startswith('_'):continue
        if isinstance(v, (str, int, bool)) or v is None:keep[k] = v
        elif isinstance(v, dict):keep[k] = {kk: vv for kk, vv in v.items() if isinstance(vv, (str, int, bool, list, tuple)) or vv is None}
        elif isinstance(v, (list, tuple)):keep[k] = [x for x in v if isinstance(x, (str, int, list, tuple))][:16]
    return keep


# ================================================================== a program window, through accessibility (K9's window)

TEXT, COMPONENT = 'org.a11y.atspi.Text', 'org.a11y.atspi.Component'
PUT_BACK_READS = frozenset({(TEXT, 'GetNSelections'), (TEXT, 'GetSelection')})
PUT_BACK_ACTS = frozenset({(COMPONENT, 'GrabFocus'), (TEXT, 'SetCaretOffset'), (TEXT, 'SetSelection'), (TEXT, 'AddSelection')})
ST_FOCUSED, ST_SELECTED, ST_SHOWING = 12, 23, 25
SNAP_NODES = 900              # the focus looked for in at most this many objects of her window
SNAP_MS = 4000


def _allowed():
    from . import a11y_reader as reader
    return reader.READ_ONLY | PUT_BACK_READS | PUT_BACK_ACTS


def _call(conn, ref, iface, method, *args, timeout=1500):
    """One call on the accessibility bus, only from PUT_BACK's own list (and the reader's reads)."""
    if (iface, method) not in _allowed():raise PermissionError('PUT_BACK_ALLOWED: %s.%s is not one of the put back\'s methods' % (iface, method))
    from PySide6.QtDBus import QDBus, QDBusMessage
    from . import a11y_reader as reader
    message = QDBusMessage.createMethodCall(ref[0], ref[1], iface, method)
    if args:message.setArguments(list(args))
    reply = conn.call(message, QDBus.CallMode.Block, max(1, int(timeout)))
    if reply.type() == QDBusMessage.MessageType.ErrorMessage:
        raise reader.CallFailed(reply.errorName() or '', (reply.errorMessage() or '').strip()[:200])
    return [reader.plain(v) for v in reply.arguments()]


def _caret(conn, ref):
    from . import a11y_reader as reader
    try:return int((_call(conn, ref, reader.PROPS, 'Get', TEXT, 'CaretOffset') or [-1])[0])
    except (reader.CallFailed, TypeError, ValueError):return None


def _selections(conn, ref):
    from . import a11y_reader as reader
    try:n = int((_call(conn, ref, TEXT, 'GetNSelections') or [0])[0] or 0)
    except (reader.CallFailed, TypeError, ValueError):return None
    out = []
    for i in range(min(n, 4)):
        try:got = _call(conn, ref, TEXT, 'GetSelection', int(i))
        except reader.CallFailed:break
        try:
            start, end = (int(got[0]), int(got[1])) if len(got) >= 2 else (int(got[0][0]), int(got[0][1]))
        except (TypeError, ValueError, IndexError):continue
        if 0 <= start < end:out.append([start, end])
    return out


def _open_menus(look, top):
    """The menus open now in her window's menu bar, outermost first: a menu is open while its node is SELECTED."""
    from . import a11y_hand as H
    bars = H._bfs(look, top, lambda n: n['role'] == 'menu bar', skip=frozenset({'document text', 'tool bar', 'menu', 'paragraph'}), most=1)
    if not bars:return []
    out = [];holder = bars[0]
    for _ in range(ESCAPES_MOST):
        kids = [look.node(r) for r in look.children(holder['ref'])[:80]]
        nxt = next((k for k in kids if k is not None and k['role'] == 'menu' and ST_SELECTED in k['states']), None)
        if nxt is None:break
        out.append({'ref': list(nxt['ref']), 'name': nxt['name']})
        holder = nxt
    return out


def _focus_node(look, top):
    """The control with the focus in her window (its node), or None."""
    from . import a11y_reader as reader
    queue = [(top, 0)];start = look.nodes
    while queue:
        node, depth = queue.pop(0)
        if node is not top and ST_FOCUSED in node['states']:return node
        if look.nodes - start >= SNAP_NODES:return None
        if depth >= 20 or (node is not top and node['role'] in ('menu', 'menu bar', 'popup menu', 'tool bar', 'status bar', 'scroll bar')) or reader.DEFUNCT in node['states']:continue
        if node is not top and node['states'] and ST_SHOWING not in node['states']:continue
        try:kids = look.children(node['ref'])[:400]
        except reader.OutOfTime:return None
        for ref in kids:
            try:child = look.node(ref)
            except reader.OutOfTime:return None
            if child is not None:queue.append((child, depth + 1))
    return None


def _active_window():
    try:
        from . import windows_x11
        watcher = windows_x11.shared()
        if not watcher.start():return 0, ''
        snap = watcher.refresh()
        active = int(snap.get('active') or 0)
        title = next((w['title'] for w in snap.get('windows') or () if w['window'] == active), '')
        return active, title
    except Exception:  # noqa: BLE001 - no window list: the window in front is not looked after
        return 0, ''


def program_snapshot(look, top, row, rel=''):
    """Her program window as it is before her first press: the control with the focus, its text cursor and selection, its
    place on the screen, the menus open (yours, left alone), and the window in front. Read only."""
    from . import a11y_hand as H
    from . import a11y_reader as reader
    from .a11y_hand import extents
    look = H.Look(look.conn, budget_ms=SNAP_MS, max_nodes=SNAP_NODES)      # a look of its own, bounded: the snapshot never holds her up long
    focus = None
    try:node = _focus_node(look, top)
    except reader.OutOfTime:node = None
    if node is not None and not H.private(node):
        ifaces = look.interfaces(node['ref'])
        focus = {'ref': list(node['ref']), 'role': node['role'], 'name': node['name'][:120], 'caret': None, 'selections': None, 'place': None}
        if TEXT in ifaces:
            focus['caret'] = _caret(look.conn, node['ref']);focus['selections'] = _selections(look.conn, node['ref'])
        box = extents(tuple(node['ref']))
        focus['place'] = list(box) if box else None
    try:menus = _open_menus(look, top)
    except reader.OutOfTime:menus = []
    active, active_title = _active_window()
    return {'kind': 'program', 'window': row.get('id'), 'pid': row.get('pid'), 'title': str(row.get('title') or '')[:200], 'path': rel,
            'focus': focus, 'menus': [m['name'] for m in menus], 'active': active, 'active_title': active_title[:200], 'at': _now_ms()}


def _input_in(row):
    """Whether her program's window has the keyboard now (the X input focus is in it)."""
    import ctypes
    from . import a11y_hand as H
    if not H.KEYS.ready():return False
    x = H.KEYS.x
    x.XGetInputFocus.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_int)]
    w = ctypes.c_ulong();r = ctypes.c_int()
    x.XGetInputFocus(H.KEYS.dpy, ctypes.byref(w), ctypes.byref(r))
    if w.value in (0, 1):return False      # None, PointerRoot
    try:return H.KEYS.top_of(int(w.value)) == H.KEYS.top_of(int(str(row.get('id')), 16))
    except (TypeError, ValueError):return False


def _escape():
    from . import a11y_hand as H
    code = H.KEYS.named('Escape')
    if not code:raise RuntimeError('this keyboard has no key that closes a menu')
    H.KEYS.press(code)      # written in her ledger first (Touch.expecting): never taken for your touch


def _close_menus(look, top, row, before):
    """Close the menus she left open over her window (one Escape a level, looked at after each); yours stay."""
    from . import a11y_hand as H
    menus = _open_menus(look, top)
    mine = [m for m in menus if m['name'] not in (before or [])] if before else menus
    if not mine:return {'back': True, 'words': ''}
    brought = 0
    if not _input_in(row):
        try:
            from . import windows_x11
            got = windows_x11.shared().activate(int(str(row.get('id')), 16), wait=1.0)
            brought = 1 if got.get('verified') else 0
        except Exception:  # noqa: BLE001
            brought = 0
        if not _input_in(row):
            return {'back': False, 'words': 'the menu “%s” I opened is still open: my program does not have the keyboard, so I sent no key' % mine[-1]['name'][:40]}
    if not H.KEYS.ready():return {'back': False, 'words': 'the menu “%s” is still open: %s' % (mine[-1]['name'][:40], H.KEYS.reason)}
    sent = 0
    for _ in range(min(ESCAPES_MOST, len(menus) + 1)):
        H._fresh(look)
        menus = _open_menus(look, top)
        if not [m for m in menus if m['name'] not in (before or [])]:break
        _escape();sent += 1
        time.sleep(SETTLE_MS / 1000)
    H._fresh(look)
    left = [m for m in _open_menus(look, top) if m['name'] not in (before or [])]
    if left:return {'back': False, 'words': 'the menu “%s” is still open after I tried %d time%s to close it' % (left[-1]['name'][:40], sent, '' if sent == 1 else 's'), 'escapes': sent}
    return {'back': True, 'words': 'the %s menu I opened is closed' % ' › '.join(m['name'] for m in mine)[:80], 'escapes': sent, 'brought_forward': brought}


def program_put_back(snap, parts=ALL_PARTS):
    """Her program window put back as the snapshot says, as far as accessibility and the window list allow: each part read
    back to be sure. Returns {'back', 'parts': {part: {'back', 'words'}}, 'words'}."""
    from . import a11y_hand as H
    from . import a11y_reader as reader
    out = {}
    try:
        _, winsnap = H._windows()
        row = next((w for w in winsnap.get('windows') or () if w['id'] == snap.get('window')), None)
    except H.Refused as why:
        return {'back': False, 'parts': {'window': {'back': False, 'words': str(why).split(': ', 1)[-1][:160]}}}
    if row is None:
        return {'back': False, 'parts': {'window': {'back': False, 'words': 'my window “%s” is closed' % snap.get('title', '')[:60]}}}
    look = H.Look(H._conn())
    try:app, top = H._frame(look, row, snap.get('path') or '')
    except H.Refused as why:
        return {'back': False, 'parts': {'window': {'back': False, 'words': str(why).split(': ', 1)[-1][:160]}}}
    if 'menus' in parts:
        try:out['menus'] = _close_menus(look, top, row, snap.get('menus'))
        except (reader.CallFailed, reader.OutOfTime, RuntimeError) as why:out['menus'] = {'back': False, 'words': 'the menus could not be looked at (%s)' % str(why)[:80]}
        if not out['menus'].get('words'):out.pop('menus')
    dialogs = []
    try:
        H._fresh(look);dialogs = H._dialogs(look, app, top)
    except (reader.CallFailed, reader.OutOfTime):
        pass
    if dialogs:
        out['dialog'] = {'back': None, 'words': 'the dialog “%s” is open over the window: it stays yours' % (dialogs[0]['name'] or '')[:60]}
    focus = snap.get('focus')
    if focus and not dialogs:
        ref = tuple(focus['ref']);conn = look.conn
        H._fresh(look)
        node = look.node(ref)
        if node is None:
            if 'focus' in parts:out['focus'] = {'back': False, 'words': 'the %s that had the focus is gone' % (focus['role'] or 'control')}
        else:
            if 'focus' in parts and ST_FOCUSED not in node['states']:
                try:_call(conn, ref, COMPONENT, 'GrabFocus')
                except reader.CallFailed:pass
                time.sleep(SETTLE_MS / 1000);H._fresh(look);node = look.node(ref) or node
            if 'focus' in parts:
                ok = ST_FOCUSED in node['states']
                out['focus'] = {'back': ok, 'words': ('the focus is back in the %s%s' % (focus['role'], (' “%s”' % focus['name'][:40]) if focus['name'] and focus['role'] not in ('paragraph', 'text') else ''))
                                if ok else 'the focus did not come back to the %s' % focus['role']}
            sels = focus.get('selections')
            if 'selection' in parts and sels is not None:
                now = _selections(conn, ref)
                if now != sels:
                    try:
                        if sels:
                            if now:_call(conn, ref, TEXT, 'SetSelection', 0, int(sels[0][0]), int(sels[0][1]))
                            else:_call(conn, ref, TEXT, 'AddSelection', int(sels[0][0]), int(sels[0][1]))
                        elif focus.get('caret') is not None and focus['caret'] >= 0:
                            _call(conn, ref, TEXT, 'SetCaretOffset', int(focus['caret']))      # a caret set clears a selection
                    except reader.CallFailed:
                        pass
                    time.sleep(SETTLE_MS / 1000);now = _selections(conn, ref)
                if sels:out['selection'] = {'back': now == sels, 'words': ('your selection is back (characters %d to %d)' % (sels[0][0], sels[0][1])) if now == sels
                                            else 'your selection did not come back'}
            caret = focus.get('caret')
            if 'caret' in parts and caret is not None and caret >= 0:
                now = _caret(conn, ref)
                if now != caret and not sels:
                    try:_call(conn, ref, TEXT, 'SetCaretOffset', int(caret))
                    except reader.CallFailed:pass
                    time.sleep(SETTLE_MS / 1000);now = _caret(conn, ref)
                out['caret'] = {'back': now == caret, 'words': ('the text cursor is back at character %d' % caret) if now == caret else
                                'the text cursor is at %s, not %d' % (now, caret)}
            if 'place' in parts and focus.get('place'):
                from .a11y_hand import extents
                box = extents(ref)
                if box and list(box) != focus['place']:
                    _scroll_to(ref, caret if caret is not None and caret >= 0 else 0)
                    time.sleep(SETTLE_MS / 1000);box = extents(ref)
                same = bool(box) and list(box) == focus['place']
                out['place'] = {'back': same, 'words': 'the view is scrolled as it was' if same else 'the view is not scrolled as it was'}
    if 'window' in parts and snap.get('active'):
        now, _ = _active_window()
        if now != snap['active']:
            try:
                from . import windows_x11
                got = windows_x11.shared().activate(snap['active'], wait=1.0)
                ok = bool(got.get('verified'))
            except Exception:  # noqa: BLE001
                ok = False
            out['window'] = {'back': ok, 'words': ('“%s” is in front again' % (snap.get('active_title') or 'your window')[:60]) if ok else
                             'the window that was in front (“%s”) could not be brought back' % (snap.get('active_title') or '')[:60]}
        else:
            out['window'] = {'back': True, 'words': '“%s” is in front, as it was' % (snap.get('active_title') or 'the window')[:60]}
    back = all(p.get('back') is not False for p in out.values())
    return {'back': back, 'parts': out}


def _scroll_to(ref, at):
    """Text.ScrollSubstringTo(start, end, ANYWHERE): its type is an unsigned number, which QtDBus cannot send from Python, so it
    goes through dbus-send on the accessibility bus, typed (as K9's GetExtents). A program that does not offer it says no."""
    from . import a11y_reader as reader
    address = reader._BUS.get('address')
    if not address:return False
    try:
        done = subprocess.run(['dbus-send', '--bus=' + address, '--print-reply=literal', '--reply-timeout=1500', '--dest=' + ref[0], ref[1],
                               TEXT + '.ScrollSubstringTo', 'int32:%d' % int(at), 'int32:%d' % (int(at) + 1), 'uint32:6'],
                              capture_output=True, text=True, timeout=4)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def carry_assignment(call, ident):
    """Your Continue for her hand in a program (her column's press): the step of her assignment that your touch stopped is
    authorised again by that press and the assignment carries on; K1 looks at what was done before anything is repeated.
    `call(op, args)` is your press through the Kernel: (result, why). Returns her words, or '' when nothing waited."""
    if not ident:return ''
    view, why = call('assignment.status', {'id': ident})
    if not view:return ''
    step = next((s for s in view.get('steps') or () if s.get('status') == 'needs review' and 'stopped by your touch' in str(s.get('reason') or '')), None)
    if step is None:return ''
    planned, why = call('assignment.plan', {'id': ident, 'authorise': [step['key']], 'expected_digest': view.get('plan_digest')})
    if planned is None:return 'Step %s could not be authorised again: %s' % (step.get('n'), why)
    ran, why = call('assignment.step', {'id': ident, 'until': 'end'})
    if ran is None:return 'My hand could not go on: %s' % why
    said = [str(w) for w in ran.get('said') or () if w]
    return ' '.join(said)[:400] or 'My hand went on from step %s.' % step.get('n')


# ================================================================== her changes in a turn, and the one Undo (the desk)

def changes_of(trail_entries):
    """Her changes of one turn that can be taken back: the trail's entries (stacy_hand.trail order, latest first) that are done
    and carry an Undo line."""
    return [e for e in trail_entries if isinstance(e, dict) and e.get('state') == 'done' and e.get('undo')]


def undo_words(n_back, n_left, said=()):
    if not n_back and not n_left:return 'Nothing I changed in this turn can be taken back.'
    words = 'Taken back: %d change%s of mine, the latest first.' % (n_back, '' if n_back == 1 else 's')
    if n_left:words += ' %d could not be taken back: %s' % (n_left, '; '.join(s for s in said if s)[:200] or 'it changed since')
    return words


# ================================================================== the Kernel's operations (1.0 F1)

FIELDS = {'door.state': ({}, []), 'door.continue': ({}, []), 'door.stop': ({}, [])}
SCOPES = {'door.state': 'read', 'door.continue': 'approve', 'door.stop': 'approve'}
OBSERVERS = ('door.state',)


def dispatch(kernel, op, args, principal):
    _KERNEL['kernel'] = kernel
    if op == 'door.state':return DOOR.view()
    if op == 'door.continue':
        out = DOOR.carry_on()
        _tell_program(kernel, out)
        return dict(out, door=DOOR.view())
    if op == 'door.stop':
        out = DOOR.stop()
        _tell_program(kernel, out, stopped=True)
        return dict(out, door=DOOR.view())
    raise ValueError('Unknown hand door operation')


def _tell_program(kernel, out, stopped=False):
    """Her column's hand line (K9's live state) says what your word did, for a program window."""
    if DOOR.hand != 'program':return
    try:
        from . import a11y_hand as H
        if stopped:H._tell(kernel, state='done' if out.get('back') else 'not verified', words=out.get('words') or '', program=DOOR.program,
                           title=DOOR.title, act='', how='put back')
        elif out.get('carried'):H._tell(kernel, state='resting', words=out.get('words') or '', program=DOOR.program, title=DOOR.title, act='', how='')
    except Exception:  # noqa: BLE001
        pass


def _halt_stop(kernel, principal):
    """halt_gate's stop hook: her hand, wherever it drives, stops before its next press."""
    _KERNEL['kernel'] = kernel
    return ('her hand stopped in %s' % (DOOR.program or WHERE.get(DOOR.hand, 'the window'))) if DOOR.halted() else ''


def _join():
    try:
        from . import halt_gate
        halt_gate.register_stop('her hand, wherever it drives', _halt_stop)
    except Exception:  # noqa: BLE001
        pass
    return True


JOINED = _join()
