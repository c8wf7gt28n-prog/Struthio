"""Her hand in other programs (Graphite 1.0, K9): she operates the owner's programs the way a person would, while they watch.

The owner, 26 Nov 2026: "Kas is meant to be an AI agentic user of the system also"; and the earlier road: "she takes the mouse
in your programs while you watch". The paper, section 10: "When she must use the visible interface, she needs confirmation
that the intended window received the action. 'Clicked Save' and 'the expected revision exists on disk' are different
observations; reliable completion requires the latter."

HOW SHE ACTS, in this order:
  1. Through the program's accessibility (AT-SPI, over D-Bus with PySide6's QtDBus, the bus K7's reader reaches): press a
     named button (Action.DoAction), choose a menu item by its path ("File > Save": each menu opened as a person would),
     type into a named field or replace a passage found through the accessible text (EditableText), move the focus to a
     control of the window she was given (Component.GrabFocus).
  2. Only where the program exposes nothing for that control (no Action, no EditableText): synthetic pointer and keys (XTest,
     libXtst through ctypes), aimed at the accessible object's own place on the screen (Component.GetExtents), never at
     guessed pixels. No extents, or another window over that place: she refuses.
  3. Nothing else: no blind clicking, no screen reading by pixels.

ACTING is its own module: the reader (a11y_reader, K7) stays READ ONLY by its allow-list. This module's allow-list (ALLOWED)
holds the reader's reads, three reads of its own (GetInterfaces, Action.GetActions, Component.GetExtents) and five acting
methods (ACTING: DoAction, SetTextContents, InsertText, DeleteText, GrabFocus); an acting method is sent only by act(), after
the guard.

THE GUARD (every act, at dispatch, in the Kernel's path, whatever the dial says):
  - Her window only: a window she opened (program.open records it) or one you showed her (program.shown, your press). The
    control must be inside that window, or inside a dialog of the same program that is open over it.
  - Never a password: a field whose role is "password text", or whose name says password or passphrase, is never typed into,
    focused or read; keys are never sent while one has the focus.
  - Always asks: a button or menu item whose name begins with one of ALWAYS_ASKS (Send, Pay, Buy, Delete, Remove, Erase,
    Install, Uninstall, Format, Sign, Submit, in English, any case) is pressed only by your own press on that very act, at
    every place of the dial; a grant never covers it (stacy_hand.ARGUMENT_ASKS says so to K1 and K3).
  - HALT holds her work: nothing is pressed or typed (halt_gate), and a sequence stops at once.
  - Your touch stops her: Touch watches the X server's raw input (XInput2 raw events through libXi; polling the pointer and
    the keymap where XInput2 is absent) and tells her own synthetic events apart by their ledger. Any key or pointer move of
    yours, in any window, after her last act and before her next one, stops her between the two: the step is left "stopped
    by your touch", her column says so, nothing more is pressed. A touch before she started does not count.
  - With no X display there is nothing to watch for your touch, so she does not act at all.

VERIFIED, NEVER ASSUMED (K2's receipts through K1's checks): a replaced passage is read back through the accessible text; a
save is verified by the file on disk (a new digest, and the new words in the saved file read directly), and its revision is
recorded (revisions.record, L4); a dialog answered is verified gone and the save behind it on disk.

A DIALOG ANSWERED ONLY AS GRANTED. When a dialog opens over her window ("Keep current format?", LibreOffice's "Confirm File
Format"), she reads it (its title, words and buttons) and presses nothing, unless the answer was given: in the step itself,
from your own words ("keep its format"), or by your own press on that answer (program.answer, marked for your approval).
Otherwise the step needs review and the dialog is yours.

Kernel operations (registered in engineering_kernel and engineering_cli under "1.0 K9"):
  program.status  {live?}                          read     whether her hand can work here (accessibility, keys, your touch),
                                                            her windows, and what her hand is doing now
  program.look    {path}                           read     her window for that file: its menus, buttons and fields by name
  program.find    {path, passage}                  read     the passage found through the accessible text of her window
  program.open    {path, program?}                 execute  open a file in its program, in a visible window of its own; that
                                                            window is hers from then on
  program.type    {path, text, passage?, field?}   execute  replace a passage, or type into a named field
  program.press   {path, control? | menu?, expect?} execute press a named button, or choose a menu item by its path
  program.save    {path, expect?, answer?}         execute  save with the menu's Save; verified by the file on disk
  program.answer  {path, button, dialog?}          approve  answer the dialog open over her window with the named button
  program.shown   {path, window}                   approve  your press: this window of yours shows that file; she may work in it

Registry tools (K2, numbers never moved or reused): 31 program.open, 32 program.read (look, find), 33 program.type,
34 program.save (and press), 35 program.answer. Grants (K3): the family "programs.work", "work in a program", on a file (or a
folder), for this assignment.

No floating point in anything checked: times are whole milliseconds, positions whole pixels, digests compared as text.
"""
from __future__ import annotations

import contextlib
import ctypes
import ctypes.util
import hashlib
import json
import os
import re
import select
import subprocess
import threading
import time
import zipfile
from pathlib import Path

from . import a11y_reader as reader
from . import assignments as _asg

SCHEMA = 'graphite.hand-in-programs/1'
ACCESSIBLE, TEXT, PROPS = reader.ACCESSIBLE, reader.TEXT, reader.PROPS
ACTION, EDITABLE, COMPONENT = 'org.a11y.atspi.Action', 'org.a11y.atspi.EditableText', 'org.a11y.atspi.Component'
HAND_READS = frozenset({(ACCESSIBLE, 'GetInterfaces'), (ACTION, 'GetActions')})   # Component.GetExtents goes typed, below
ACTING = frozenset({(ACTION, 'DoAction'), (EDITABLE, 'SetTextContents'), (EDITABLE, 'InsertText'), (EDITABLE, 'DeleteText'),
                    (COMPONENT, 'GrabFocus')})
ALLOWED = reader.READ_ONLY | HAND_READS | ACTING
# Always asks, at every place of the dial: a button or menu item whose name begins with one of these words. One place only.
ALWAYS_ASKS = ('Send', 'Pay', 'Buy', 'Delete', 'Remove', 'Erase', 'Install', 'Uninstall', 'Format', 'Sign', 'Submit')
PASSWORD_WORDS = re.compile(r'pass\s*word|passphrase|\bpin\b', re.I)
PASSWORD_ROLES = frozenset({'password text'})
PRESSABLE = frozenset({'push button', 'toggle button', 'button', 'check box', 'radio button', 'menu item', 'check menu item',
                       'radio menu item', 'menu', 'link', 'page tab'})
FIELD_ROLES = frozenset({'text', 'entry', 'editbar', 'combo box', 'spin button', 'password text'})
TEXTUAL = frozenset({'paragraph', 'text', 'heading', 'entry', 'document text', 'label', 'static', 'caption'})
SKIP_FOR_TEXT = frozenset({'menu bar', 'menu', 'tool bar', 'status bar', 'popup menu', 'combo box', 'list', 'tree', 'page tab list'})
SKIP_FOR_CONTROLS = frozenset({'menu', 'popup menu', 'document text', 'paragraph', 'list', 'tree'})
DIALOG_ROLES = reader.DIALOG_ROLES
# What a "Keep current format?" dialog reads like (LibreOffice calls it "Confirm File Format"), and its two answers.
KEEP_FORMAT = re.compile(r'keep (the )?current format|confirm file format|currently selected file format|default odf file format', re.I)
ANSWERS = {'keep': ('keep the current format', re.compile(r'^(keep|use (?!odf)).*', re.I)),
           'odf': ('save in the ODF format instead', re.compile(r'\bodf\b', re.I))}
SAVE_MENU = {'default': 'File > Save'}
CALL_MS = 1500                # one call through accessibility (a program busy saving answers late)
FIND_BUDGET_MS = 12000        # one look for a passage or a control in her window
FIND_NODES = 2500
FRAME_WAIT_MS = 8000          # a program just started: how long its window is given to show itself to accessibility
MENU_WAIT_MS = 2500           # a menu opened: how long its items are given to show their names
OPEN_WAIT_MS = 45000          # a program started: how long its window is looked for
SAVE_WAIT_MS = 20000          # a save pressed: how long the file on disk (or a dialog) is looked for
GONE_WAIT_MS = 6000           # a dialog answered: how long it is given to close
SETTLE_MS = 250               # after an act, before the next look
SEQUENCE_GAP_MS = 8000        # a touch counts against her next act when her last act ended less than this before it
MOVE_SETTLE_MS = 150          # after her synthetic pointer moves, her own raw motion events still arrive

# AT-SPI's states (AtspiStateType), by number.
ST_ACTIVE, ST_EDITABLE, ST_ENABLED, ST_FOCUSABLE, ST_FOCUSED, ST_MODAL, ST_SENSITIVE, ST_SHOWING, ST_VISIBLE, ST_DEFAULT = 1, 7, 8, 11, 12, 16, 24, 25, 30, 39


class Refused(ValueError):
    """Her hand will not do it: the words say why. Nothing was pressed or typed."""


class Stopped(Exception):
    """A sequence stopped between two acts (your touch, HALT): what was done is said."""

    def __init__(self, why, words):
        super().__init__(words);self.why = why;self.words = words


def _now_ms():
    return time.time_ns() // 1000000


def _mono_ms():
    return time.monotonic_ns() // 1000000


def plain_name(name):
    """A control's name compared as a person reads it: no mnemonic marks, no trailing dots, one space, any case."""
    name = reader._button_name(name or '')
    name = re.sub(r'(\.\.\.|…)\s*$', '', name).replace('~', '')
    return re.sub(r'\s+', ' ', name).strip().casefold()


def always_asks(name):
    """Why pressing a control of this name always asks, or ''. Its first word is one of ALWAYS_ASKS."""
    words = plain_name(name).split()
    if words and words[0].strip('!.:') in {w.casefold() for w in ALWAYS_ASKS}:
        return 'pressing “%s” in another program always asks you, at every place of the dial' % reader._button_name(name)[:60]
    return ''


def private(node):
    """A password field: never typed into, focused or read."""
    return node.get('role') in PASSWORD_ROLES or bool(PASSWORD_WORDS.search(node.get('name') or ''))


def _menu_parts(menu):
    parts = [p.strip() for p in re.split(r'\s*(?:>|›|→)\s*', str(menu or '')) if p.strip()]
    if not 1 <= len(parts) <= 6:raise Refused('MENU_PATH: a menu item is named by its path, such as “File > Save”')
    return parts


def argument_asks(operation, arguments):
    """stacy_hand.ARGUMENT_ASKS: a press, a save or an answer naming a control that always asks."""
    if not str(operation or '').startswith('program.') or not isinstance(arguments, dict):return ''
    names = []
    for key in ('control', 'button'):
        if isinstance(arguments.get(key), str):names.append(arguments[key])
    if isinstance(arguments.get('menu'), str):
        try:names.append(_menu_parts(arguments['menu'])[-1])
        except Refused:pass
    for name in names:
        why = always_asks(name)
        if why:return why
    return ''


# ================================================================== the accessibility bus, acting

def _send(conn, service, path, iface, method, *args, timeout=CALL_MS):
    """One call on the accessibility bus. Only ALLOWED methods; an acting one only through act()."""
    if (iface, method) not in ALLOWED:
        raise PermissionError('HAND_ALLOWED: %s.%s is not one of her hand\'s methods' % (iface, method))
    from PySide6.QtDBus import QDBus, QDBusMessage
    message = QDBusMessage.createMethodCall(service, path, iface, method)
    if args:message.setArguments(list(args))
    reply = conn.call(message, QDBus.CallMode.Block, max(1, int(timeout)))
    if reply.type() == QDBusMessage.MessageType.ErrorMessage:
        raise reader.CallFailed(reply.errorName() or '', (reply.errorMessage() or '').strip()[:200])
    return [reader.plain(v) for v in reply.arguments()]


EXTENTS_WHY = {'last': ''}


def extents(ref):
    """Component.GetExtents(SCREEN) of an object: (x, y, width, height) in whole pixels, or None. Its argument is an unsigned
    32-bit number, which QtDBus cannot send from Python, so it goes through dbus-send (registered on that bus: --bus), typed."""
    address = reader._BUS.get('address')
    if not address:
        EXTENTS_WHY['last'] = 'the accessibility bus was not reached';return None
    try:
        done = subprocess.run(['dbus-send', '--bus=' + address, '--print-reply=literal', '--reply-timeout=%d' % CALL_MS,
                               '--dest=' + ref[0], ref[1], COMPONENT + '.GetExtents', 'uint32:0'],
                              capture_output=True, text=True, timeout=CALL_MS // 1000 + 2)
    except (OSError, subprocess.TimeoutExpired) as exc:
        EXTENTS_WHY['last'] = str(exc)[:200];return None
    numbers = [int(n) for n in re.findall(r'int32\s+(-?\d+)', done.stdout or '')]      # the four int32 of the struct, never the "32" of int32
    EXTENTS_WHY['last'] = (done.stderr or done.stdout or '').strip()[:200]
    if done.returncode != 0 or len(numbers) < 4:return None
    x, y, w, h = numbers[-4:]
    return (x, y, w, h) if w > 0 and h > 0 else None


class Look(reader.Reading):
    """One look inside her window, with the hand's own reads (interfaces, actions); bounded like the reader's."""

    def __init__(self, conn, budget_ms=FIND_BUDGET_MS, max_nodes=FIND_NODES):
        super().__init__(conn, budget_ms=budget_ms, max_nodes=max_nodes);self.ifaces = {}

    def own(self, service, path, iface, method, *args):
        left = self.left_ms()
        if left <= 0:raise reader.OutOfTime('the look took its whole time')
        self.calls += 1
        return _send(self.conn, service, path, iface, method, *args, timeout=min(CALL_MS, left))

    def interfaces(self, ref):
        if ref not in self.ifaces:
            try:self.ifaces[ref] = set((self.own(ref[0], ref[1], ACCESSIBLE, 'GetInterfaces') or [[]])[0] or ())
            except reader.CallFailed:self.ifaces[ref] = set()
        return self.ifaces[ref]

    def actions(self, ref):
        try:found = (self.own(ref[0], ref[1], ACTION, 'GetActions') or [[]])[0] or []
        except reader.CallFailed:return []
        return [str((a or [''])[0] or '') for a in found]


def _bfs(look, top, want, skip=frozenset(), most=None):
    """Nodes under `top` (not itself) for which want(node) is true, breadth first, within the look's bounds."""
    out, queue = [], [(top, 0)]
    while queue:
        node, depth = queue.pop(0)
        if node is not top and want(node):
            out.append(node)
            if most and len(out) >= most:break
        if depth >= 24 or (node is not top and node['role'] in skip) or reader.DEFUNCT in node['states']:continue
        try:
            for ref in look.children(node['ref'])[:400]:      # a document that manages its descendants is still read, within the look's bounds
                child = look.node(ref)
                if child is not None:queue.append((child, depth + 1))
        except reader.OutOfTime:
            look.short('her window has more objects than one look reads');break
    return out


# ================================================================== her windows

MIGRATIONS = [(1, (
    'CREATE TABLE hand_windows(window TEXT NOT NULL, owner TEXT NOT NULL, path TEXT NOT NULL, program TEXT NOT NULL, pid INTEGER, '
    'how TEXT NOT NULL, title TEXT NOT NULL, assignment TEXT NOT NULL, at INTEGER NOT NULL, ended INTEGER, PRIMARY KEY(window, owner, path))',
))]


def ensure(db):
    if not db.in_transaction:db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS hand_windows_migrations(version INTEGER PRIMARY KEY, digest TEXT NOT NULL, applied INTEGER NOT NULL)')
    applied = dict(db.execute('SELECT version, digest FROM hand_windows_migrations'))
    known = {version: _asg.digest(list(sql)) for version, sql in MIGRATIONS}
    if any(known.get(v) != d for v, d in applied.items()):raise ValueError('HAND_MIGRATION_UNSUPPORTED: use a compatible program')
    for version, statements in MIGRATIONS:
        if version in applied:continue
        for statement in statements:db.execute(statement)
        db.execute('INSERT INTO hand_windows_migrations VALUES(?,?,?)', (version, known[version], _now_ms()))


def _remember(kernel, owner, row, path, how, program, assignment=''):
    with kernel.db() as db:
        db.execute('BEGIN IMMEDIATE');ensure(db)
        db.execute('INSERT OR REPLACE INTO hand_windows VALUES(?,?,?,?,?,?,?,?,?,NULL)',
                   (row['id'], owner, path, program[:120], row.get('pid'), how, str(row.get('title') or '')[:300], assignment or '', _now_ms()))


def _theirs(kernel, owner, path=None):
    try:
        with kernel.db() as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='hand_windows'").fetchone() is None:return []
            sql = 'SELECT window, path, program, pid, how, title, assignment, at FROM hand_windows WHERE owner=? AND ended IS NULL'
            rows = db.execute(sql + (' AND path=?' if path else '') + ' ORDER BY at DESC', (owner, path) if path else (owner,)).fetchall()
    except Exception:  # noqa: BLE001 - none can be read: she has none
        return []
    return [dict(zip(('window', 'path', 'program', 'pid', 'how', 'title', 'assignment', 'at'), r)) for r in rows]


def _windows():
    from . import windows_x11
    watcher = windows_x11.shared()
    if not watcher.start():raise Refused('NO_WINDOWS: %s' % (watcher.reason or windows_x11.NO_LIST))
    return watcher, watcher.refresh()


def her_window(kernel, owner, rel):
    """(her window's row in the window list, its record) for the file, or Refused: she works only in a window she opened or
    you showed her, while it is open."""
    _, snap = _windows()
    rows = {w['id']: w for w in snap.get('windows') or ()}
    for rec in _theirs(kernel, owner, rel):
        row = rows.get(rec['window'])
        if row is not None and not row.get('graphite'):return row, rec
    if _theirs(kernel, owner, rel):
        raise Refused('NOT_HERS: the window I opened for %s is closed now; I work only in a window I opened or you showed me' % Path(rel).name)
    raise Refused('NOT_HERS: no window of %s is mine: I work only in a window I opened (program.open) or you showed me' % Path(rel).name)


# ================================================================== X: her synthetic pointer and keys, and your touch

def _lib(name, soname):
    try:return ctypes.CDLL(soname)
    except OSError:
        found = ctypes.util.find_library(name)
        return ctypes.CDLL(found) if found else None


class XIEventMask(ctypes.Structure):
    _fields_ = [('deviceid', ctypes.c_int), ('mask_len', ctypes.c_int), ('mask', ctypes.POINTER(ctypes.c_ubyte))]


class XGenericEventCookie(ctypes.Structure):
    _fields_ = [('type', ctypes.c_int), ('serial', ctypes.c_ulong), ('send_event', ctypes.c_int), ('display', ctypes.c_void_p),
                ('extension', ctypes.c_int), ('evtype', ctypes.c_int), ('cookie', ctypes.c_uint), ('data', ctypes.c_void_p)]


class XEvent(ctypes.Union):
    _fields_ = [('type', ctypes.c_int), ('cookie', XGenericEventCookie), ('pad', ctypes.c_long * 24)]


class XIRawHead(ctypes.Structure):
    """The head of XIRawEvent (what she needs of it: which device, which key or button)."""
    _fields_ = [('type', ctypes.c_int), ('serial', ctypes.c_ulong), ('send_event', ctypes.c_int), ('display', ctypes.c_void_p),
                ('extension', ctypes.c_int), ('evtype', ctypes.c_int), ('time', ctypes.c_ulong), ('deviceid', ctypes.c_int),
                ('sourceid', ctypes.c_int), ('detail', ctypes.c_int), ('flags', ctypes.c_int)]


class XIDeviceInfo(ctypes.Structure):
    _fields_ = [('deviceid', ctypes.c_int), ('name', ctypes.c_char_p), ('use', ctypes.c_int), ('attachment', ctypes.c_int),
                ('enabled', ctypes.c_int), ('num_classes', ctypes.c_int), ('classes', ctypes.c_void_p)]


GENERIC_EVENT = 35
XI_RAW = {13: 'key', 15: 'button', 17: 'motion'}      # XI_RawKeyPress, XI_RawButtonPress, XI_RawMotion


def _x11():
    x = _lib('X11', 'libX11.so.6')
    if x is None:return None
    x.XOpenDisplay.argtypes = [ctypes.c_char_p];x.XOpenDisplay.restype = ctypes.c_void_p
    x.XDefaultRootWindow.argtypes = [ctypes.c_void_p];x.XDefaultRootWindow.restype = ctypes.c_ulong
    x.XQueryExtension.argtypes = [ctypes.c_void_p, ctypes.c_char_p] + [ctypes.POINTER(ctypes.c_int)] * 3
    x.XFlush.argtypes = [ctypes.c_void_p];x.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
    x.XPending.argtypes = [ctypes.c_void_p];x.XNextEvent.argtypes = [ctypes.c_void_p, ctypes.POINTER(XEvent)]
    x.XConnectionNumber.argtypes = [ctypes.c_void_p];x.XCloseDisplay.argtypes = [ctypes.c_void_p]
    x.XGetEventData.argtypes = [ctypes.c_void_p, ctypes.POINTER(XGenericEventCookie)]
    x.XFreeEventData.argtypes = [ctypes.c_void_p, ctypes.POINTER(XGenericEventCookie)]
    x.XQueryPointer.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong)] + \
        [ctypes.POINTER(ctypes.c_int)] * 4 + [ctypes.POINTER(ctypes.c_uint)]
    x.XQueryKeymap.argtypes = [ctypes.c_void_p, ctypes.c_char * 32]
    x.XQueryTree.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong), ctypes.POINTER(ctypes.c_ulong),
                             ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_uint)]
    x.XFree.argtypes = [ctypes.c_void_p]
    x.XStringToKeysym.argtypes = [ctypes.c_char_p];x.XStringToKeysym.restype = ctypes.c_ulong
    x.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong];x.XKeysymToKeycode.restype = ctypes.c_ubyte
    x.XkbKeycodeToKeysym.argtypes = [ctypes.c_void_p, ctypes.c_ubyte, ctypes.c_int, ctypes.c_int];x.XkbKeycodeToKeysym.restype = ctypes.c_ulong
    return x


class Touch:
    """Your touch: the X server's raw key presses, button presses and pointer moves, read on a connection of its own, in a
    thread of its own. Her own synthetic events (XTest) are written in a ledger before she sends them and are not counted as
    yours; anything else is your touch (a keyboard, a mouse, a touchpad, an on-screen keyboard of yours)."""

    def __init__(self):
        self.lock = threading.Lock();self.thread = None;self.running = False;self.how = '';self.reason = ''
        self.count = 0;self.last = None;self.expect = {};self.moving_until = 0;self.xtest_ids = set();self.started = False
        self.poll = None

    def start(self):
        with self.lock:
            if self.started:return self.running
            self.started = True
        display = os.environ.get('DISPLAY')
        if not display:
            self.reason = 'there is no X display here, so there is nothing of yours to feel';return False
        x = _x11()
        if x is None:
            self.reason = 'libX11 is not installed here';return False
        dpy = x.XOpenDisplay(display.encode())
        if not dpy:
            self.reason = 'the X display %s did not let Graphite in' % display;return False
        opcode, event, error = ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
        xi = _lib('Xi', 'libXi.so.6')
        if xi is not None and x.XQueryExtension(dpy, b'XInputExtension', ctypes.byref(opcode), ctypes.byref(event), ctypes.byref(error)):
            xi.XIQueryVersion.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
            major, minor = ctypes.c_int(2), ctypes.c_int(0)
            if xi.XIQueryVersion(dpy, ctypes.byref(major), ctypes.byref(minor)) == 0:
                self._xi(x, xi, dpy, opcode.value);return True
        self._polling(x, dpy)
        return True

    def _xi(self, x, xi, dpy, opcode):
        xi.XIQueryDevice.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_int)];xi.XIQueryDevice.restype = ctypes.POINTER(XIDeviceInfo)
        xi.XIFreeDeviceInfo.argtypes = [ctypes.POINTER(XIDeviceInfo)]
        xi.XISelectEvents.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(XIEventMask), ctypes.c_int]
        n = ctypes.c_int()
        info = xi.XIQueryDevice(dpy, 0, ctypes.byref(n))      # XIAllDevices
        for i in range(n.value):
            name = (info[i].name or b'').decode('utf-8', 'replace')
            if 'XTEST' in name.upper():self.xtest_ids.add(info[i].deviceid)
        if info:xi.XIFreeDeviceInfo(info)
        bits = (ctypes.c_ubyte * 4)()
        for evtype in XI_RAW:bits[evtype >> 3] |= 1 << (evtype & 7)
        mask = XIEventMask(1, 4, ctypes.cast(bits, ctypes.POINTER(ctypes.c_ubyte)))      # XIAllMasterDevices
        xi.XISelectEvents(dpy, x.XDefaultRootWindow(dpy), ctypes.byref(mask), 1)
        x.XFlush(dpy)
        self.how = 'XInput2 raw events';self.running = True
        self.thread = threading.Thread(target=self._loop, args=(x, dpy, opcode), name='graphite-k9-touch', daemon=True)
        self.thread.start()

    def _loop(self, x, dpy, opcode):
        fd = x.XConnectionNumber(dpy);ev = XEvent()
        while self.running:
            try:select.select([fd], [], [], 0.25)
            except (OSError, ValueError):break
            while x.XPending(dpy):
                x.XNextEvent(dpy, ctypes.byref(ev))
                if ev.type != GENERIC_EVENT or ev.cookie.extension != opcode:continue
                if not x.XGetEventData(dpy, ctypes.byref(ev.cookie)):continue
                try:
                    raw = ctypes.cast(ev.cookie.data, ctypes.POINTER(XIRawHead)).contents
                    self._seen(XI_RAW.get(ev.cookie.evtype), raw.sourceid, raw.detail)
                finally:
                    x.XFreeEventData(dpy, ctypes.byref(ev.cookie))

    def _seen(self, kind, source, detail):
        if kind is None:return
        with self.lock:
            if source in self.xtest_ids:
                if kind == 'motion' and _mono_ms() <= self.moving_until:return
                key = (kind, int(detail))
                if kind != 'motion' and self.expect.get(key, 0) > 0:
                    self.expect[key] -= 1;return
            self.count += 1
            self.last = {'kind': kind, 'at': _mono_ms(), 'xtest': source in self.xtest_ids}

    def _polling(self, x, dpy):
        """No XInput2: the pointer's place and the keys held down, read before each of her acts."""
        self.how = 'the pointer and the keyboard, looked at before each act';self.running = True
        self.poll = (x, dpy)
        self.base = self._sample()

    def _sample(self):
        x, dpy = self.poll
        root = x.XDefaultRootWindow(dpy)
        r, c = ctypes.c_ulong(), ctypes.c_ulong();rx, ry, wx, wy = (ctypes.c_int() for _ in range(4));m = ctypes.c_uint()
        x.XQueryPointer(dpy, root, ctypes.byref(r), ctypes.byref(c), ctypes.byref(rx), ctypes.byref(ry), ctypes.byref(wx), ctypes.byref(wy), ctypes.byref(m))
        keys = (ctypes.c_char * 32)();x.XQueryKeymap(dpy, keys)
        return (rx.value, ry.value, m.value & 0x1f00, bytes(keys))

    def mark(self):
        """A mark of now: touches after it count."""
        with self.lock:
            if self.poll is not None:self.base = self._sample()
            return self.count

    def since(self, mark):
        """Whether you touched since the mark: (True, words) or (False, '')."""
        with self.lock:
            if self.poll is not None:
                now = self._sample()
                if now != self.base and _mono_ms() > self.moving_until:
                    self.count += 1;self.last = {'kind': 'key' if now[3] != self.base[3] else 'pointer', 'at': _mono_ms(), 'xtest': False}
                    self.base = now
            if self.count > mark:
                kind = (self.last or {}).get('kind', 'key')
                return True, {'key': 'a key of yours', 'button': 'a press of your mouse', 'motion': 'your pointer moving',
                              'pointer': 'your pointer moving'}.get(kind, 'your touch')
            return False, ''

    def expecting(self, kind, detail, n=1):
        with self.lock:self.expect[(kind, int(detail))] = self.expect.get((kind, int(detail)), 0) + n

    def moving(self, ms=MOVE_SETTLE_MS):
        with self.lock:self.moving_until = _mono_ms() + ms

    def after_mine(self):
        """After her own synthetic events have arrived: the polling sample takes them in as the new base."""
        with self.lock:
            if self.poll is not None:self.base = self._sample()

    def stop(self):
        self.running = False


TOUCH = Touch()


class Keys:
    """Her synthetic pointer and keys (XTest), on a connection of their own; each event written in the touch ledger first."""

    def __init__(self):
        self.x = None;self.t = None;self.dpy = None;self.reason = ''

    def ready(self):
        if self.dpy:return True
        display = os.environ.get('DISPLAY')
        if not display:self.reason = 'there is no X display here';return False
        self.x = _x11();self.t = _lib('Xtst', 'libXtst.so.6')
        if self.x is None or self.t is None:self.reason = 'libXtst (the X server\'s test extension) is not installed here';return False
        self.dpy = self.x.XOpenDisplay(display.encode())
        if not self.dpy:self.reason = 'the X display did not let Graphite in';return False
        t = self.t
        t.XTestQueryExtension.argtypes = [ctypes.c_void_p] + [ctypes.POINTER(ctypes.c_int)] * 4
        t.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
        t.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
        t.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
        a, b, c, d = (ctypes.c_int() for _ in range(4))
        if not t.XTestQueryExtension(self.dpy, ctypes.byref(a), ctypes.byref(b), ctypes.byref(c), ctypes.byref(d)):
            self.reason = 'the X server has no XTest extension';self.dpy = None;return False
        return True

    def window_at(self, x, y):
        """The top-level window under a point (the root's child there), moving her pointer there first."""
        TOUCH.moving()
        self.t.XTestFakeMotionEvent(self.dpy, -1, int(x), int(y), 0);self.x.XSync(self.dpy, 0)
        root = self.x.XDefaultRootWindow(self.dpy)
        r, c = ctypes.c_ulong(), ctypes.c_ulong();rx, ry, wx, wy = (ctypes.c_int() for _ in range(4));m = ctypes.c_uint()
        self.x.XQueryPointer(self.dpy, root, ctypes.byref(r), ctypes.byref(c), ctypes.byref(rx), ctypes.byref(ry), ctypes.byref(wx),
                             ctypes.byref(wy), ctypes.byref(m))
        return int(c.value), (rx.value, ry.value)

    def top_of(self, window):
        """The root's child that holds a window (its frame, under a window manager that frames)."""
        root = self.x.XDefaultRootWindow(self.dpy);w = int(window)
        for _ in range(16):
            r, p = ctypes.c_ulong(), ctypes.c_ulong();kids = ctypes.c_void_p();n = ctypes.c_uint()
            if not self.x.XQueryTree(self.dpy, w, ctypes.byref(r), ctypes.byref(p), ctypes.byref(kids), ctypes.byref(n)):return w
            if kids.value:self.x.XFree(kids)
            if p.value in (0, root):return w
            w = int(p.value)
        return w

    def click(self, x, y, button=1):
        self.window_at(x, y)
        TOUCH.expecting('button', button)
        self.t.XTestFakeButtonEvent(self.dpy, button, 1, 0);self.t.XTestFakeButtonEvent(self.dpy, button, 0, 0)
        self.x.XSync(self.dpy, 0)

    def keycode(self, char):
        sym = ord(char) if 0x20 <= ord(char) <= 0x7e else None
        if sym is None:return None, False
        code = self.x.XKeysymToKeycode(self.dpy, sym)
        if not code:return None, False
        if self.x.XkbKeycodeToKeysym(self.dpy, code, 0, 0) == sym:return code, False
        if self.x.XkbKeycodeToKeysym(self.dpy, code, 0, 1) == sym:return code, True
        return None, False

    def named(self, name):
        sym = self.x.XStringToKeysym(name.encode())
        return self.x.XKeysymToKeycode(self.dpy, sym) if sym else None

    def press(self, code, shift=False):
        shift_code = self.named('Shift_L') if shift else None
        if shift_code:TOUCH.expecting('key', shift_code);self.t.XTestFakeKeyEvent(self.dpy, shift_code, 1, 0)
        TOUCH.expecting('key', code)
        self.t.XTestFakeKeyEvent(self.dpy, code, 1, 0);self.t.XTestFakeKeyEvent(self.dpy, code, 0, 0)
        if shift_code:self.t.XTestFakeKeyEvent(self.dpy, shift_code, 0, 0)
        self.x.XSync(self.dpy, 0)

    def type(self, text):
        codes = [self.keycode(ch) for ch in text]
        if any(code is None for code, _ in codes):raise Refused('KEYS_PLAIN: through keys I type only plain letters, digits and signs')
        for code, shift in codes:self.press(code, shift)


KEYS = Keys()


# ================================================================== what her hand is doing (her column reads it)

AFTER_ACT = []                # callables(state dict): her column's live line; a stand-in for checks
_LIVE = {'state': 'resting', 'words': '', 'program': '', 'title': '', 'act': '', 'how': '', 'at': 0}
_LAST = {'end': 0, 'mark': 0}
_HALTED = {'flag': False}


def _live_file(kernel):
    return Path(kernel.state) / 'hand_in_programs.json'


def live_state(kernel=None):
    """What her hand is doing now: from this process, else from the last one that wrote it."""
    if _LIVE.get('at') or kernel is None:return dict(_LIVE)
    try:return json.loads(_live_file(kernel).read_text(encoding='utf-8'))
    except (OSError, ValueError):return dict(_LIVE)


def _tell(kernel, **state):
    _LIVE.update(state);_LIVE['at'] = _now_ms()
    try:
        path = _live_file(kernel);tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(_LIVE, ensure_ascii=False), encoding='utf-8');os.replace(tmp, path)
    except OSError:
        pass
    for hook in list(AFTER_ACT):
        try:hook(dict(_LIVE))
        except Exception:  # noqa: BLE001 - a watcher of her hand never stops it
            pass


def owner_pressed():
    """Your press in Graphite's window that starts or carries on her work (her column calls it): that press is not a touch
    against her next act."""
    if TOUCH.running:_LAST['mark'] = TOUCH.mark()


def _halt_stop(kernel, principal):
    """halt_gate's stop hook: a sequence running in this process stops before its next act."""
    _HALTED['flag'] = True
    return 'her hand in your programs stopped' if _LIVE.get('state') == 'acting' else ''


class Hand:
    """One sequence of acts in her window: each act checked (HALT, your touch) before it is done, and said as it is done."""

    def __init__(self, kernel, principal, row, rec, program):
        self.kernel = kernel;self.principal = principal;self.row = row;self.rec = rec;self.program = program
        self.done = [];self.how = set()
        try:
            from . import halt_gate
            self.epoch = halt_gate.epoch(kernel)
        except Exception:  # noqa: BLE001
            self.epoch = None
        if not TOUCH.start():raise Refused('NO_TOUCH: I act in your programs only where I can feel your touch: %s' % TOUCH.reason)
        if _mono_ms() - _LAST['end'] > SEQUENCE_GAP_MS:_LAST['mark'] = TOUCH.mark()      # a touch before she started does not count
        _HALTED['flag'] = False

    def _gate(self, act):
        held = _HALTED['flag']
        try:
            from . import halt_gate
            held = held or halt_gate.held(self.kernel)
        except Exception:  # noqa: BLE001
            pass
        if held:
            raise Stopped('halt', 'HALT holds her work: %s' % self._said(act))
        touched, what = TOUCH.since(_LAST['mark'])
        if touched:
            _LAST['mark'] = TOUCH.mark()      # this touch is answered by stopping; the next press of yours starts afresh
            raise Stopped('touch', 'stopped by your touch (%s): %s' % (what, self._said(act)))

    def _said(self, act):
        done = ('done: ' + '; '.join(self.done[-3:])) if self.done else 'nothing of this step was done'
        return '%s; “%s” was not done' % (done, act)

    def act(self, words, how, do):
        """One act: the gate, the act, what it is said to be. `do` sends it (an acting method, or her synthetic events)."""
        self._gate(words)
        _tell(self.kernel, state='acting', words=words, program=self.program, title=self.row.get('title', ''), act=words, how=how)
        try:
            out = do()
        finally:
            _LAST['end'] = _mono_ms()
        self.done.append(words);self.how.add(how)
        TOUCH.after_mine()
        _tell(self.kernel, state='acting', words=words, program=self.program, title=self.row.get('title', ''), act=words, how=how)
        return out

    def end(self, state, words):
        _tell(self.kernel, state=state, words=words, program=self.program, title=self.row.get('title', ''), act='', how=', '.join(sorted(self.how)))


# ================================================================== reading her window

def _conn():
    try:return reader.connection()
    except reader.Unavailable as why:
        raise Refused('NO_ACCESSIBILITY: ' + reader.said_unavailable(why)) from None


def _frame(look, row, rel=''):
    """Her window's accessible frame (app, top), by the window list's row (its program's process, its title); else the one
    top window, among the programs that show themselves, whose name holds the file's name (a title the X server gives in
    another encoding than the accessible name)."""
    try:apps = reader.programs(look)
    except (reader.CallFailed, reader.OutOfTime) as failed:
        reader.forget();raise Refused('NO_ACCESSIBILITY: the accessibility bus does not answer (%s)' % str(failed)[:120]) from None
    end = _mono_ms() + FRAME_WAIT_MS
    while True:
        app, top = reader._match(row, apps)
        if top is None and rel:
            named = [(a, t) for a in apps for t in a['tops'] if Path(rel).name in (t['name'] or '') and not reader._is_dialog(t)]
            if len(named) == 1:app, top = named[0]
        if top is not None or _mono_ms() > end:break
        time.sleep(0.5)      # a program just started may show its insides a moment after its window
        look.nodes = 0;look.end = time.monotonic_ns() + FIND_BUDGET_MS * 1000000
        try:apps = reader.programs(look)
        except (reader.CallFailed, reader.OutOfTime):break
    if top is None:
        raise Refused('NOT_SHOWN: %s' % reader.said_unavailable('it does not show its window “%s” to accessibility' % str(row.get('title') or '')[:80],
                                                                'that program'))
    return app, top


def _dialogs(look, app, top):
    """The dialogs of her program open now (not her window itself)."""
    out = []
    for ref in look.children(app['ref']):
        node = look.node(ref)
        if node is None or node['ref'] == top['ref'] or not reader._shown(node):continue
        if node['role'] in DIALOG_ROLES or reader.MODAL in node['states']:out.append(node)
    return out


def _dialog_view(look, node, program):
    inside = reader._inside(look, node)
    words = list(inside['text'])
    if not words:      # a toolkit that names its message as a notification: her own look, inside this dialog only
        for n in _bfs(look, node, lambda n: n['role'] in ('notification', 'static', 'label') and n['name'], most=reader.MAX_TEXT):
            words.append(n['name'][:reader.MAX_LINE])
    return {'title': inside['title'], 'role': inside['role'], 'text': words, 'buttons': inside['buttons'], 'fields': inside['fields'],
            'program': program, 'modal': inside['modal'], 'complete': inside['complete'], 'node': node}


def _fresh(look):
    """A look that waits (for a save, a dialog to close) reads again within fresh bounds each time."""
    look.nodes = 0;look.end = time.monotonic_ns() + FIND_BUDGET_MS * 1000000


def _texts(look, top):
    """The objects with text in her window (paragraphs, fields), never a password field."""
    return _bfs(look, top, lambda n: n['role'] in TEXTUAL and not private(n) and TEXT in look.interfaces(n['ref']), skip=SKIP_FOR_TEXT)


def _find(look, top, passage):
    found = []
    for node in _texts(look, top):
        text = look.text(node['ref'])
        start = text.find(passage)
        while start >= 0:
            found.append({'node': node, 'start': start, 'end': start + len(passage), 'text': text})
            start = text.find(passage, start + 1)
    return found


def _named(look, top, name, roles, skip=SKIP_FOR_CONTROLS):
    want = plain_name(name)
    return _bfs(look, top, lambda n: n['role'] in roles and plain_name(n['name']) == want, skip=skip)


def _same_text_digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


# ================================================================== the file on disk

def _resolve(kernel, rel, must_exist=True):
    from . import files_service, home_reach
    try:path = files_service.resolve(kernel, rel, must_exist=must_exist)
    except (ValueError, OSError) as why:raise Refused('NOT_IN_FILES: %s' % str(why)[:160]) from None
    never = home_reach.her_change(kernel, path)  # 1.0 L6b: her hand works only on a file of Files or of your home
    if never:raise Refused('OUTSIDE_HOME: %s' % never[:300])
    return path


def file_sha(path):
    from .tools_registry import file_sha as sha
    return sha(Path(path))


def saved_text(path):
    """The saved file's words, read directly (no program): an OpenDocument's paragraphs, a Word document's, plain text; None
    when Graphite cannot read this kind of file."""
    path = Path(path);suffix = path.suffix.lower()
    try:
        if suffix in ('.odt', '.ods', '.odp'):
            from .office_bridge import read_odf
            doc = read_odf(path)
            return '\n'.join(doc.get('paragraphs') or [])
        if suffix == '.docx':
            with zipfile.ZipFile(path) as archive:xml = archive.read('word/document.xml').decode('utf-8', 'replace')
            paragraphs = []
            for p in re.findall(r'<w:p[ >].*?</w:p>', xml, re.S):
                paragraphs.append(''.join(re.findall(r'<w:t(?: [^>]*)?>([^<]*)</w:t>', p)))
            import html
            return '\n'.join(html.unescape(p) for p in paragraphs)
        if suffix in ('.txt', '.md', '.csv'):
            return path.read_text(encoding='utf-8', errors='replace')
    except (OSError, ValueError, KeyError, zipfile.BadZipFile):
        return None
    return None


def _record_revision(kernel, rel, after, before, program):
    from . import depths
    from .engineering_kernel import operator
    try:
        return depths.record(kernel, {'path': rel, 'expected_sha256': after, 'previous_sha256': before or '', 'how': 'full program',
                                      'program': ('%s (Kasandra\'s hand)' % program)[:120]}, operator())
    except Exception as exc:  # noqa: BLE001 - the save is on disk either way: it is said, not hidden
        return {'recorded': False, 'revision': None, 'why': str(exc)[:200]}


# ================================================================== the operations

def _program_of(row, rec=None):
    """The program in words: the App she opened it with, else what the window list calls it."""
    return str((rec or {}).get('program') or row.get('program') or 'its program')


def status(kernel, principal, live_only=False):
    out = {'schema': SCHEMA, 'live': live_state(kernel)}
    if live_only:return out
    access = reader.status()
    keys = KEYS.ready()
    touch = TOUCH.start()
    out.update(accessibility={'available': access['available'], 'enabled': access.get('enabled'), 'words': access['words']},
               keys={'available': keys, 'words': 'XTest, aimed by the accessible position only' if keys else KEYS.reason},
               touch={'available': touch, 'how': TOUCH.how, 'words': ('I feel your touch through %s' % TOUCH.how) if touch else TOUCH.reason},
               windows=_theirs(kernel, principal.identity), always_asks=list(ALWAYS_ASKS))
    able = access['available'] and touch
    words = ['My hand can work in your programs here: through their accessibility%s, and I stop at your touch.' % (
        ', and through keys where a program shows nothing' if keys else '')] if able else []
    if not access['available']:words.append(access['words'])
    elif access.get('enabled') is False:
        words.append('Accessibility is off in this session, so some programs (Firefox and Qt programs among them) do not show their insides; '
                     'turning it on is your setting (Settings, on your press).')
    if not touch:words.append('I act in your programs only where I can feel your touch: %s.' % TOUCH.reason)
    out['available'] = bool(able);out['words'] = ' '.join(words)
    return out


def look_at(kernel, principal, rel):
    row, rec = her_window(kernel, principal.identity, rel)
    look = Look(_conn())
    app, top = _frame(look, row, rel)
    menus = [n['name'] for n in _bfs(look, top, lambda n: n['role'] == 'menu' and n['name'], skip=frozenset({'menu'}) | SKIP_FOR_TEXT - {'menu bar'})][:16]
    buttons = [n['name'] for n in _bfs(look, top, lambda n: n['role'] in PRESSABLE - {'menu', 'menu item'} and n['name'], skip=frozenset({'menu bar', 'document text', 'paragraph'}))][:40]
    fields = [n['name'] or n['role'] for n in _bfs(look, top, lambda n: n['role'] in FIELD_ROLES and not private(n), skip=frozenset({'menu bar', 'document text'}))][:16]
    dialogs = [_dialog_view(look, d, _program_of(row, rec)) for d in _dialogs(look, app, top)]
    for d in dialogs:d.pop('node', None)
    return {'schema': SCHEMA, 'window': row['id'], 'title': row['title'], 'program': _program_of(row, rec), 'how': rec['how'], 'menus': menus,
            'buttons': buttons, 'fields': fields, 'dialogs': dialogs, 'partial': list(look.partial),
            'words': 'In %s (“%s”): menus %s; %d buttons and %d fields shown to accessibility%s.' % (
                _program_of(row, rec), row['title'][:80], ', '.join(menus[:8]) or 'none', len(buttons), len(fields),
                ('; a dialog is open: “%s”' % dialogs[0]['title']) if dialogs else '')}


def find(kernel, principal, rel, passage):
    row, rec = her_window(kernel, principal.identity, rel)
    look = Look(_conn())
    app, top = _frame(look, row, rel)
    places = _find(look, top, passage)
    sha = file_sha(_resolve(kernel, rel))
    out = {'schema': SCHEMA, 'path': rel, 'passage': passage, 'found': len(places), 'window': row['id'], 'title': row['title'],
           'program': _program_of(row, rec), 'revision': sha, 'partial': list(look.partial),
           'places': [{'role': p['node']['role'], 'start': p['start'], 'end': p['end']} for p in places[:8]]}
    if len(places) == 1:
        out['words'] = 'Found through the accessible text of “%s” in %s: once, in a %s.' % (row['title'][:80], _program_of(row, rec), places[0]['node']['role'])
    elif places:
        out['words'] = 'The passage is in %d places of “%s”, not one: say which.' % (len(places), row['title'][:80])
    else:
        out['words'] = 'The passage is not in the accessible text of “%s”%s.' % (row['title'][:80], ' (read in part: %s)' % look.partial[0] if look.partial else '')
    return out


def _permit_assignment():
    try:
        from . import grants
        permit = grants._PERMIT.get()
        return str((permit or {}).get('assignment') or '')
    except Exception:  # noqa: BLE001
        return ''


def open_file(kernel, principal, rel, program=None):
    """program.open: the file in its program (the App you set for its type, or the one named), in a visible window of its
    own, started in a session of its own (S1); the window that shows it is hers from then on."""
    from . import apps_catalog
    path = _resolve(kernel, rel)
    if not path.is_file():raise Refused('NOT_A_FILE: %s is not a file in Files' % rel)
    watcher, snap = _windows()
    rows = [w for w in snap.get('windows') or () if not w.get('graphite')]
    mine = {r['window'] for r in _theirs(kernel, principal.identity, rel)}
    for w in rows:
        if w['id'] in mine and path.name in (w.get('title') or ''):
            return {'schema': SCHEMA, 'path': rel, 'window': w['id'], 'title': w['title'], 'program': w['program'], 'opened': False,
                    'words': '%s is open already in my window “%s”; it was not opened again.' % (path.name, w['title'][:80])}
    for w in rows:
        if path.name in (w.get('title') or '') and w['id'] not in mine:
            raise Refused('NOT_HERS: %s is open in a window of yours (“%s”): I do not work in it unless you show it to me' % (path.name, w['title'][:80]))
    mime = apps_catalog.mime_of(str(path))
    ident = program or apps_catalog.default_for(mime)[0]
    app = apps_catalog.find_app(ident) if ident else None
    if app is None:raise Refused('NO_PROGRAM: no App is set to open %s (%s) here; choose one in Apps' % (path.name, mime))
    started = _start(kernel, principal, rel, path, app, bool(program))
    pids = {s['pid'] for s in started.get('started') or () if s.get('pid')}
    end = _mono_ms() + OPEN_WAIT_MS;found = None
    while _mono_ms() < end and found is None:
        if _HALTED['flag']:break
        snap = watcher.refresh()
        for w in snap.get('windows') or ():
            if w.get('graphite') or w.get('dialog'):continue
            if path.name in (w.get('title') or '') and (w['id'] not in {r['id'] for r in rows} or _descends(w.get('pid'), pids)):
                found = w;break
        if found is None:time.sleep(0.3)
    if found is None:
        raise _asg.NotVerified('%s started and no window showing %s appeared within %d s' % (app.name, path.name, OPEN_WAIT_MS // 1000))
    _remember(kernel, principal.identity, found, rel, 'opened', app.name, _permit_assignment())
    return {'schema': SCHEMA, 'path': rel, 'window': found['id'], 'title': found['title'], 'program': found['program'] or app.name, 'opened': True,
            'app': app.id, 'pids': sorted(pids), 'session': started.get('session') or '', 'started_by': started.get('by') or '',
            'words': 'I opened %s in %s: its window “%s” is mine to work in, while you watch.' % (path.name, app.name, found['title'][:80])}


def _start(kernel, principal, rel, path, app, chosen):
    """The program started on the file: through A1's door (app_files.open_file, which also keeps the session that notices its
    saves and records their revisions) when it is in this Graphite; else through the Apps catalogue directly. Never twice."""
    try:
        from . import app_files
    except Exception:  # noqa: BLE001 - A1 is not in this Graphite: the Apps catalogue starts it (S2), in a session of its own (S1)
        app_files = None
    if app_files is not None:
        try:
            answer = app_files.open_file(kernel, {'path': rel, 'app': app.id, 'chosen': bool(chosen)}, principal)
        except ValueError as why:
            raise Refused('NOT_STARTED: %s' % str(why).split(': ', 1)[-1][:200]) from None
        return {'ok': True, 'started': answer.get('started') or [], 'session': answer.get('session'), 'by': 'appfile.open (A1)'}
    from . import apps_catalog
    started = apps_catalog.launch_app(app, files=[str(path)])
    if not started.get('ok'):raise Refused('NOT_STARTED: %s' % started.get('reason', 'it did not start'))
    return dict(started, by='the Apps catalogue')


def _descends(pid, ancestors):
    """Whether a process is one of `ancestors` or below one (a program's starter often hands over to its real process)."""
    try:pid = int(pid)
    except (TypeError, ValueError):return False
    for _ in range(12):
        if pid in ancestors:return True
        try:
            with open('/proc/%d/stat' % pid) as f:stat = f.read()
            pid = int(stat.rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            return False
        if pid <= 1:return False
    return False


def _guard_press(node, principal, by_owner):
    why = always_asks(node['name'])
    if why and not by_owner:raise Refused('ALWAYS_ASKS: %s; it is yours to press, or to authorise by its own name' % why)
    if private(node):raise Refused('PASSWORD: I never touch a password field')


def _by_owner(principal, operation):
    """Your own press on this very act: the approve scope (your press through the window, or a step marked for your approval
    and authorised by its own name). Her steps of the execute scope, and anything a grant let through, never are: what always
    asks is never pressed inside her work."""
    if 'approve' not in principal.scopes or principal.mode == 'Tutor':return False
    try:
        from . import grants
        permit = grants._PERMIT.get()
    except Exception:  # noqa: BLE001
        permit = None
    return permit is None or permit.get('grant') == 'your press'


def _press_node(hand, look, node, words, top_window):
    """Press one control: its accessible action; where it has none, your pointer's way (XTest), aimed at its own place."""
    ifaces = look.interfaces(node['ref'])
    if ACTION in ifaces:
        names = look.actions(node['ref'])
        if names:
            index = next((i for i, n in enumerate(names) if n.casefold() in ('click', 'press', 'activate', 'jump', 'open', 'select', 'toggle')), 0)
            return hand.act(words, 'accessibility', lambda: _send(look.conn, node['ref'][0], node['ref'][1], ACTION, 'DoAction', int(index)))
    return _click_node(hand, node, words, top_window)


def _click_node(hand, node, words, top_window):
    """XTest, only where the control exposes no action: at the centre of its accessible extents, after checking the window
    there is the one she was given."""
    if not KEYS.ready():raise Refused('NO_KEYS: “%s” shows no action to accessibility, and %s' % (node['name'][:60], KEYS.reason))
    box = extents(node['ref'])
    if box is None:
        raise Refused('NO_PLACE: “%s” shows no action and no place on the screen to accessibility; I never aim at guessed pixels' % node['name'][:60])
    x, y = box[0] + box[2] // 2, box[1] + box[3] // 2
    under, _ = KEYS.window_at(x, y)
    want = KEYS.top_of(int(top_window, 16))
    if under != want:
        try:
            _, snap = _windows()
            there = next((w['title'] for w in snap.get('windows') or () if KEYS.top_of(w['window']) == under), '')
        except Refused:
            there = ''
        raise Refused('NOT_THERE: another window%s is over “%s” at its place on the screen (0x%x, not 0x%x); nothing was pressed'
                      % ((' (“%s”)' % there[:60]) if there else '', node['name'][:60], under, want))
    return hand.act(words, 'keys and pointer (XTest), aimed at its accessible place', lambda: KEYS.click(x, y))


def _top_window_of(row, dialog_title):
    """The window-list id of her program's dialog (by its title, its program's process first), else her window's."""
    if not dialog_title:return row['id']
    try:
        _, snap = _windows()
    except Refused:
        return row['id']
    same = [w for w in snap.get('windows') or () if (w.get('title') or '') == dialog_title]
    mine = [w for w in same if w.get('pid') == row.get('pid')]
    return ((mine or same) or [row])[0]['id']


def type_text(kernel, principal, rel, text, passage=None, field=None):
    row, rec = her_window(kernel, principal.identity, rel)
    look = Look(_conn())
    app, top = _frame(look, row, rel)
    program = _program_of(row, rec)
    hand = Hand(kernel, principal, row, rec, program)
    try:
        if passage:
            places = _find(look, top, passage)
            if len(places) != 1:
                raise Refused('PASSAGE: “%s” is in %d places of “%s”, not one; nothing was typed' % (passage[:60], len(places), row['title'][:60]))
            place = places[0];node = place['node']
            if private(node):raise Refused('PASSWORD: I never type into a password field')
            if EDITABLE not in look.interfaces(node['ref']):
                raise Refused('NOT_EDITABLE: the passage is in text that shows no way to edit it to accessibility; I do not select text by guessed positions')
            service, path = node['ref'];start, end = place['start'], place['end']

            def replace():
                _send(look.conn, service, path, EDITABLE, 'DeleteText', int(start), int(end))
                return _send(look.conn, service, path, EDITABLE, 'InsertText', int(start), text, len(text.encode('utf-8')))
            hand.act('replace “%s” with “%s”' % (passage[:50], text[:50]), 'accessibility', replace)
            time.sleep(SETTLE_MS / 1000)
            now = look.text(node['ref'])
            ok = now[start:start + len(text)] == text
            hand.end('done' if ok else 'not verified', 'In %s: %s' % (program, 'the passage now reads as you said' if ok else 'the text does not read as typed'))
            return {'schema': SCHEMA, 'path': rel, 'window': row['id'], 'title': row['title'], 'program': program, 'how': 'accessibility',
                    'typed': ok, 'paragraph': now[:2000], 'revision': _same_text_digest(now), 'start': start, 'text': text, 'passage': passage,
                    'saved': False, 'acts': list(hand.done)}
        if not field:raise Refused('TYPE_WHERE: name the passage to replace, or the field to type into')
        nodes = _named(look, top, field, FIELD_ROLES)
        for d in _dialogs(look, app, top):nodes += _named(look, d, field, FIELD_ROLES)
        if len(nodes) != 1:raise Refused('FIELD: %d fields are called “%s” in my window, not one; nothing was typed' % (len(nodes), field[:60]))
        node = nodes[0]
        if private(node):raise Refused('PASSWORD: “%s” is a password field: a password is typed by you, never by me' % field[:60])
        if EDITABLE in look.interfaces(node['ref']):
            hand.act('type “%s” into “%s”' % (text[:50], field[:40]), 'accessibility',
                     lambda: _send(look.conn, node['ref'][0], node['ref'][1], EDITABLE, 'SetTextContents', text))
        else:
            _click_node(hand, node, 'click into “%s”' % field[:40], row['id'])
            focused = reader._focused(look, top)
            if focused and focused.get('role') in PASSWORD_ROLES:raise Refused('PASSWORD: the focus is in a password field; I send no keys')
            hand.act('type “%s” into “%s” through keys' % (text[:50], field[:40]), 'keys and pointer (XTest), aimed at its accessible place',
                     lambda: KEYS.type(text))
        time.sleep(SETTLE_MS / 1000)
        now = look.text(node['ref'])
        ok = now == text
        hand.end('done' if ok else 'not verified', 'In %s: “%s” %s' % (program, field[:40], 'holds what I typed' if ok else 'does not hold what I typed'))
        return {'schema': SCHEMA, 'path': rel, 'window': row['id'], 'title': row['title'], 'program': program, 'typed': ok, 'field': field,
                'revision': _same_text_digest(now), 'text': text, 'saved': False, 'acts': list(hand.done)}
    except Stopped as stop:
        hand.end('stopped by your touch' if stop.why == 'touch' else 'stopped by HALT', stop.words)
        return {'schema': SCHEMA, 'path': rel, 'stopped': stop.why, 'words': stop.words, 'acts': list(hand.done), 'typed': False, 'program': program}


def _open_menu_path(hand, look, top, parts, program):
    """Open each menu of the path as a person would, then the item: the item's node."""
    bars = _bfs(look, top, lambda n: n['role'] == 'menu bar', skip=frozenset({'document text', 'tool bar', 'menu'}), most=1)
    if not bars:raise Refused('NO_MENU: “%s” shows no menu bar to accessibility' % top['name'][:60])
    holder = bars[0]
    for depth, part in enumerate(parts):
        want = plain_name(part)
        last = depth == len(parts) - 1
        node = None;end = _mono_ms() + MENU_WAIT_MS
        while node is None:
            kids = [look.node(r) for r in look.children(holder['ref'])]
            node = next((k for k in kids if k is not None and plain_name(k['name']) == want), None)
            if node is not None or _mono_ms() > end:break
            time.sleep(0.15)
        if node is None:raise Refused('NO_ITEM: the menu has no item “%s” (looked for as a person reads it)' % part[:60])
        if last:return node
        _press_node(hand, look, node, 'open the %s menu' % reader._button_name(node['name']), hand.row['id'])
        holder = node
        time.sleep(SETTLE_MS / 1000)
    return None


def _answer_dialog(hand, look, dialog, choice, row):
    """A granted answer to a "Keep current format?" dialog: the button that keeps it (or that takes ODF)."""
    view = _dialog_view(look, dialog, hand.program)
    said = ' '.join([view['title']] + list(view['text']))
    if not KEEP_FORMAT.search(said):return None, view
    pattern = ANSWERS[choice][1]
    names = [b['name'] for b in view['buttons'] if pattern.search(b['name'])]
    if choice == 'keep':names = [n for n in names if 'odf' not in n.casefold()]
    if len(names) != 1:return None, view
    nodes = _named(look, dialog, names[0], PRESSABLE, skip=frozenset())
    if len(nodes) != 1:return None, view
    _guard_press(nodes[0], hand.principal, False)
    _press_node(hand, look, nodes[0], 'answer “%s” with “%s”, as you granted' % (view['title'][:50], names[0][:50]),
                _top_window_of(row, view['title']))
    return names[0], view


def save(kernel, principal, rel, expect=None, answer=None, menu=None):
    """program.save: the program's Save, through its menu, as a person would; done only when the file on disk is new (and
    holds `expect`). A dialog over her window is read; it is answered only as granted (answer: keep or odf, from your words)."""
    row, rec = her_window(kernel, principal.identity, rel)
    path = _resolve(kernel, rel)
    before = file_sha(path)
    look = Look(_conn())
    app, top = _frame(look, row, rel)
    program = _program_of(row, rec)
    hand = Hand(kernel, principal, row, rec, program)
    parts = _menu_parts(menu or SAVE_MENU['default'])
    answered = None;dialog_seen = None
    try:
        open_dialogs = _dialogs(look, app, top)
        if open_dialogs:
            dialog_seen = open_dialogs[0]
        else:
            item = _open_menu_path(hand, look, top, parts, program)
            _guard_press(item, principal, _by_owner(principal, 'program.save'))
            _press_node(hand, look, item, 'choose %s' % ' › '.join(parts), row['id'])
        end = _mono_ms() + SAVE_WAIT_MS
        while _mono_ms() < end:
            _fresh(look)
            now = file_sha(path)
            if now != before and now is not None:
                if not _dialogs(look, app, top):break
            if dialog_seen is None:
                found = _dialogs(look, app, top)
                dialog_seen = found[0] if found else None
            if dialog_seen is not None:
                if answer in ANSWERS and answered is None:
                    answered, view = _answer_dialog(hand, look, dialog_seen, answer, row)
                    if answered is None:break
                    dialog_seen = None;time.sleep(SETTLE_MS / 1000);continue
                break
            time.sleep(0.2)
        after = file_sha(path)
        out = {'schema': SCHEMA, 'path': rel, 'window': row['id'], 'title': row['title'], 'program': program, 'before': before,
               'after': after, 'saved': after != before and after is not None, 'answered': answered, 'acts': list(hand.done),
               'how': sorted(hand.how)}
        if dialog_seen is not None and not out['saved']:
            view = _dialog_view(look, dialog_seen, program);view.pop('node', None)
            out['dialog'] = view
            out['words'] = ('A dialog opened over my window in %s and holds the save: %s I pressed nothing: it is yours to answer, or '
                            'authorise my answer.' % (program, reader.dialog_words(view, 'In %s' % program, fields=False)))
            hand.end('waiting for you', out['words'])
        else:
            hand.end('done' if out['saved'] else 'not verified', 'In %s: %s' % (program, 'saved; the file on disk is new' if out['saved'] else 'the file on disk did not change'))
        return out
    except Stopped as stop:
        hand.end('stopped by your touch' if stop.why == 'touch' else 'stopped by HALT', stop.words)
        return {'schema': SCHEMA, 'path': rel, 'stopped': stop.why, 'words': stop.words, 'acts': list(hand.done), 'saved': False,
                'before': before, 'after': file_sha(path), 'program': program}


def press(kernel, principal, rel, control=None, menu=None, expect=None):
    """program.press: a named button of her window (or of a dialog of its program), or a menu item by its path."""
    row, rec = her_window(kernel, principal.identity, rel)
    look = Look(_conn())
    app, top = _frame(look, row, rel)
    program = _program_of(row, rec)
    hand = Hand(kernel, principal, row, rec, program)
    by_owner = _by_owner(principal, 'program.press')
    try:
        if menu:
            parts = _menu_parts(menu)
            item = _open_menu_path(hand, look, top, parts, program)
            _guard_press(item, principal, by_owner)
            _press_node(hand, look, item, 'choose %s' % ' › '.join(parts), row['id'])
            pressed = ' › '.join(parts);where = row['title']
        else:
            if not control:raise Refused('PRESS_WHAT: name the button, or the menu item by its path')
            nodes, where, window = _named(look, top, control, PRESSABLE - {'menu', 'menu item'}, skip=frozenset({'menu bar', 'document text', 'paragraph'})), row['title'], row['id']
            if not nodes:
                for d in _dialogs(look, app, top):
                    nodes = _named(look, d, control, PRESSABLE, skip=frozenset())
                    if nodes:where = d['name'];window = _top_window_of(row, d['name']);break
            if len(nodes) != 1:raise Refused('CONTROL: %d controls are called “%s” in my window, not one; nothing was pressed' % (len(nodes), control[:60]))
            _guard_press(nodes[0], principal, by_owner)
            _press_node(hand, look, nodes[0], 'press “%s”' % reader._button_name(nodes[0]['name'])[:60], window)
            pressed = reader._button_name(nodes[0]['name'])
        time.sleep(SETTLE_MS / 1000)
        hand.end('done', 'In %s: pressed “%s”' % (program, pressed))
        return {'schema': SCHEMA, 'path': rel, 'window': row['id'], 'title': row['title'], 'program': program, 'pressed': pressed, 'in': where,
                'acts': list(hand.done), 'how': sorted(hand.how), 'expect': expect or ''}
    except Stopped as stop:
        hand.end('stopped by your touch' if stop.why == 'touch' else 'stopped by HALT', stop.words)
        return {'schema': SCHEMA, 'path': rel, 'stopped': stop.why, 'words': stop.words, 'acts': list(hand.done), 'program': program}


def answer(kernel, principal, rel, button, dialog=None):
    """program.answer (your press, by its own name): the dialog open over her window answered with the button you named;
    verified gone, and a save it held verified on disk."""
    row, rec = her_window(kernel, principal.identity, rel)
    path = _resolve(kernel, rel);before = file_sha(path)
    look = Look(_conn())
    app, top = _frame(look, row, rel)
    program = _program_of(row, rec)
    dialogs = _dialogs(look, app, top)
    if dialog:dialogs = [d for d in dialogs if plain_name(d['name']) == plain_name(dialog)]
    if len(dialogs) != 1:raise Refused('NO_DIALOG: %d dialogs of %s%s are open over my window, not one; nothing was pressed' % (
        len(dialogs), program, (' called “%s”' % dialog[:60]) if dialog else ''))
    d = dialogs[0]
    nodes = _named(look, d, button, PRESSABLE, skip=frozenset())
    if len(nodes) != 1:raise Refused('NO_BUTTON: the dialog “%s” has %d buttons called “%s”, not one' % (d['name'][:60], len(nodes), button[:60]))
    hand = Hand(kernel, principal, row, rec, program)
    try:
        _guard_press(nodes[0], principal, _by_owner(principal, 'program.answer'))
        _press_node(hand, look, nodes[0], 'answer “%s” with “%s”' % (d['name'][:50], reader._button_name(nodes[0]['name'])[:50]),
                    _top_window_of(row, d['name']))
        end = _mono_ms() + GONE_WAIT_MS;gone = False
        while _mono_ms() < end:
            _fresh(look)
            if not any(x['ref'] == d['ref'] for x in _dialogs(look, app, top)):
                gone = True;break
            time.sleep(0.2)
        end = _mono_ms() + SAVE_WAIT_MS
        while gone and _mono_ms() < end and file_sha(path) == before:time.sleep(0.2)
        after = file_sha(path)
        recorded = _record_revision(kernel, rel, after, before, program) if gone and after not in (None, before) else {}
        hand.end('done' if gone else 'not verified', 'In %s: answered “%s”%s' % (program, d['name'][:60], '; it closed' if gone else '; it is still open'))
        return {'schema': SCHEMA, 'path': rel, 'window': row['id'], 'program': program, 'dialog': d['name'], 'button': reader._button_name(nodes[0]['name']),
                'gone': gone, 'before': before, 'after': after, 'saved': after != before and after is not None, 'acts': list(hand.done),
                'how': sorted(hand.how), 'revision_n': recorded.get('revision')}
    except Stopped as stop:
        hand.end('stopped by your touch' if stop.why == 'touch' else 'stopped by HALT', stop.words)
        return {'schema': SCHEMA, 'path': rel, 'stopped': stop.why, 'words': stop.words, 'acts': list(hand.done), 'gone': False, 'program': program}


def shown(kernel, principal, rel, window):
    """program.shown (your press): this open window of yours shows that file, and she may work in it."""
    _resolve(kernel, rel)
    _, snap = _windows()
    row = next((w for w in snap.get('windows') or () if w['id'] == window and not w.get('graphite')), None)
    if row is None:raise Refused('NO_WINDOW: the window %s is not open now' % window)
    _remember(kernel, principal.identity, row, rel, 'shown', row.get('program') or '', '')
    return {'schema': SCHEMA, 'path': rel, 'window': row['id'], 'title': row['title'], 'program': row['program'],
            'words': 'You showed me “%s” (%s) for %s: I may work in it, while you watch.' % (row['title'][:80], row['program'], Path(rel).name)}


# ================================================================== the checks of her acts (K1, K2's receipts)

class _HandCheck(_asg.Check):
    kind = 'program';standin_ms = 6000

    @staticmethod
    def _stopped(result):
        if (result or {}).get('stopped'):
            raise _asg.NotVerified(str(result.get('words') or 'stopped')[:400])


class OpenCheck(_HandCheck):
    effect = 'a file opened in its program, in a window of hers';repeatable = False;standin_ms = 15000
    how = 'a window showing the file appears in the window list, started by her'
    expected = 'the program open on the file, in a window she may work in'

    def prepare(self, kernel, read, arguments):
        _resolve(kernel, arguments['path'])
        return {'path': arguments['path']}

    def find(self, kernel, read, arguments, prepared):
        try:row, rec = her_window(kernel, _owner_of(read), prepared['path'])
        except Refused:return None
        return self._observed(row, prepared, 'already open in her window; not opened again: ', rec)

    @staticmethod
    def _observed(row, prepared, lead='', rec=None):
        program = _program_of(row, rec)
        return {'object': 'window:' + row['id'], 'revision': row['id'], 'by': 'window list', 'complete': True, 'how': 'observed',
                'window': row['id'], 'title': row['title'][:200], 'program': program, 'path': prepared['path'],
                'words': lead + '“%s” (%s) shows %s' % (row['title'][:80], program, Path(prepared['path']).name)}

    def verify(self, kernel, read, arguments, result, prepared, step):
        _, snap = _windows()
        row = next((w for w in snap.get('windows') or () if w['id'] == (result or {}).get('window')), None)
        if row is None:raise _asg.NotVerified('no window showing %s is open' % Path(prepared['path']).name)
        return self._observed(row, prepared, '', {'program': (result or {}).get('program')})

    def still(self, kernel, read, step):
        return ''


class FindCheck(_HandCheck):
    effect = 'nothing (a read)';repeatable = True;standin_ms = 4000
    how = 'the accessible text of her window, read now; the file on disk at its digest'
    expected = 'the passage, once, in her window'

    def find(self, kernel, read, arguments, prepared):
        return None

    def verify(self, kernel, read, arguments, result, prepared, step):
        if (result or {}).get('found') != 1:raise _asg.NotVerified(str((result or {}).get('words') or 'not found')[:400])
        return {'object': 'window:' + result['window'], 'revision': result['revision'], 'by': 'accessibility', 'complete': not result.get('partial'),
                'how': 'observed', 'window': result['window'], 'title': result['title'][:200], 'program': result['program'],
                'path': result['path'], 'found': 1, 'words': result['words']}

    def still(self, kernel, read, step):
        return ''


class TypeCheck(_HandCheck):
    effect = 'words typed in her window (not saved yet)';repeatable = False
    how = 'read back through the accessible text of her window'
    expected = 'the new words, in place, in her window'

    def prepare(self, kernel, read, arguments):
        return {'path': arguments['path'], 'text': arguments['text']}

    def find(self, kernel, read, arguments, prepared):
        if not arguments.get('passage'):raise _asg.Unknowable('a field cannot be looked at again without reading it')
        try:
            out = find(kernel, _principal_of(read), arguments['path'], arguments['text'])
            old = find(kernel, _principal_of(read), arguments['path'], arguments['passage']) if arguments['passage'] not in arguments['text'] else {'found': 0}
        except Refused:
            return None
        if out['found'] == 1 and old['found'] == 0:
            return {'object': 'window:' + out['window'], 'revision': out['revision'], 'by': 'accessibility', 'complete': True, 'how': 'observed',
                    'window': out['window'], 'title': out['title'][:200], 'program': out['program'], 'path': arguments['path'],
                    'words': 'already in place in “%s”: “%s”; not typed again' % (out['title'][:60], arguments['text'][:80])}
        return None

    def verify(self, kernel, read, arguments, result, prepared, step):
        self._stopped(result)
        if not (result or {}).get('typed'):raise _asg.NotVerified('the words read back are not the ones typed')
        return {'object': 'window:' + result['window'], 'revision': result['revision'], 'by': 'accessibility', 'complete': True, 'how': 'observed',
                'window': result['window'], 'title': result['title'][:200], 'program': result['program'], 'path': result['path'],
                'words': 'In %s, read back through its accessible text: “%s” is in place (not saved yet)' % (result['program'], result['text'][:100])}

    def still(self, kernel, read, step):
        return ''


class SaveCheck(_HandCheck):
    effect = 'a new revision of the file, saved by its program';repeatable = True;standin_ms = 8000
    how = 'the file on disk: a new digest, the new words in the saved file read directly; its revision recorded'
    expected = 'the new revision on disk'

    def prepare(self, kernel, read, arguments):
        return {'path': arguments['path'], 'before': file_sha(_resolve(kernel, arguments['path'])), 'expect': arguments.get('expect') or ''}

    def _observe(self, kernel, prepared, program, lead=''):
        path = _resolve(kernel, prepared['path']);now = file_sha(path)
        if now is None or now == prepared['before']:return None
        words = saved_text(path)
        if prepared['expect']:
            if words is None:complete = False
            elif prepared['expect'] in words:complete = True
            else:return None
        else:complete = True
        recorded = _record_revision(kernel, prepared['path'], now, prepared['before'], program)
        n = recorded.get('revision')
        said = '%sthe file on disk is new (SHA-256 %s…)%s%s' % (lead, now[:12], (', and it reads “%s”' % prepared['expect'][:80]) if prepared['expect'] and complete else
                                                              (' (its words could not be read directly)' if prepared['expect'] else ''),
                                                              ('; revision %s is recorded' % n) if n else '')
        return {'object': 'files:' + prepared['path'], 'revision': now, 'by': 'sha256', 'complete': complete, 'how': 'observed',
                'path': prepared['path'], 'revision_n': n, 'program': program, 'words': said}

    def find(self, kernel, read, arguments, prepared):
        """Already saved: the file on disk holds the new words (a save is looked for by its words, never by a digest taken now)."""
        if not prepared['expect']:return None
        path = _resolve(kernel, prepared['path'])
        words = saved_text(path)
        if words is None or prepared['expect'] not in words:return None
        now = file_sha(path)
        n = _record_revision(kernel, prepared['path'], now, prepared['before'], 'its program').get('revision')      # recorded once; again is a no-op
        return {'object': 'files:' + prepared['path'], 'revision': now, 'by': 'sha256', 'complete': True, 'how': 'observed', 'path': prepared['path'],
                'revision_n': n, 'words': 'already saved, not saved again: the file on disk (SHA-256 %s…) reads “%s”%s' % (
                    now[:12], prepared['expect'][:80], ('; revision %s is recorded' % n) if n else '')}

    def verify(self, kernel, read, arguments, result, prepared, step):
        self._stopped(result)
        found = self._observe(kernel, prepared, (result or {}).get('program') or 'its program')
        if found is None:
            if (result or {}).get('dialog'):raise _asg.NotVerified('the save waits on a dialog in %s; I pressed nothing' % result.get('program', 'its program'))
            raise _asg.NotVerified('the file on disk is as it was (or does not hold the new words): not saved')
        if (result or {}).get('answered'):found['words'] += '; the dialog was answered “%s”, as you granted' % result['answered'][:60]
        return found

    def still(self, kernel, read, step):
        now = file_sha(_resolve(kernel, step['prepared']['path'], must_exist=False))
        return '' if now == (step['observation'] or {}).get('revision') else 'it has been saved again since'


class PressCheck(_HandCheck):
    effect = 'a control pressed in her window';repeatable = False
    how = 'the press received (accessibility, or her pointer at its place); what it does is read back where it can be'
    expected = 'the control pressed'

    def find(self, kernel, read, arguments, prepared):
        raise _asg.Unknowable('a press cannot be looked for afterwards')

    def verify(self, kernel, read, arguments, result, prepared, step):
        self._stopped(result)
        return {'object': 'window:' + result['window'], 'revision': result['window'], 'by': ', '.join(result.get('how') or ()), 'complete': False,
                'how': 'observed', 'window': result['window'], 'title': result['title'][:200], 'program': result['program'],
                'words': 'In %s, “%s” was pressed; what it does is not established by the press' % (result['program'], result['pressed'][:80])}

    def still(self, kernel, read, step):
        return ''


class AnswerCheck(_HandCheck):
    effect = 'a dialog answered as you said';repeatable = False
    how = 'the dialog is gone; a save it held is on disk'
    expected = 'the dialog closed'

    def find(self, kernel, read, arguments, prepared):
        raise _asg.Unknowable('an answer cannot be looked for afterwards')

    def verify(self, kernel, read, arguments, result, prepared, step):
        self._stopped(result)
        if not (result or {}).get('gone'):raise _asg.NotVerified('the dialog is still open')
        return {'object': 'files:' + result['path'] if result.get('saved') else 'window:' + result['window'], 'revision': result.get('after') or '',
                'by': 'window list and the file on disk', 'complete': True, 'how': 'observed', 'path': result['path'], 'program': result['program'],
                'words': 'In %s, “%s” was answered “%s” and closed%s' % (result['program'], result['dialog'][:60], result['button'][:60],
                                                                       '; the file on disk is new (SHA-256 %s…)' % result['after'][:12] if result.get('saved') else '')}

    def still(self, kernel, read, step):
        return ''


def _owner_of(read):
    return _principal_of(read).identity


def _principal_of(read):
    """The principal a K1 reader reads as (its closure's), else the operator."""
    for cell in (getattr(read, '__closure__', None) or ()):
        value = cell.cell_contents
        if hasattr(value, 'identity') and hasattr(value, 'scopes'):return value
    from .engineering_kernel import operator
    return operator()


# ================================================================== the Kernel's operations (1.0 K9)

PATH = {'type': 'string', 'minLength': 1, 'maxLength': 1000}
WORDS = {'type': 'string', 'minLength': 1, 'maxLength': 2000}
NAME = {'type': 'string', 'minLength': 1, 'maxLength': 200}
FIELDS = {'program.status': ({'live': {'type': 'boolean'}}, []),
          'program.look': ({'path': PATH}, ['path']),
          'program.find': ({'path': PATH, 'passage': WORDS}, ['path', 'passage']),
          'program.open': ({'path': PATH, 'program': NAME}, ['path']),
          'program.type': ({'path': PATH, 'text': WORDS, 'passage': WORDS, 'field': NAME}, ['path', 'text']),
          'program.press': ({'path': PATH, 'control': NAME, 'menu': NAME, 'expect': NAME}, ['path']),
          'program.save': ({'path': PATH, 'expect': WORDS, 'answer': {'type': 'string', 'enum': sorted(ANSWERS)}, 'menu': NAME}, ['path']),
          'program.answer': ({'path': PATH, 'button': NAME, 'dialog': NAME}, ['path', 'button']),
          'program.shown': ({'path': PATH, 'window': {'type': 'string', 'minLength': 3, 'maxLength': 20}}, ['path', 'window'])}
SCOPES = {'program.status': 'read', 'program.look': 'read', 'program.find': 'read', 'program.open': 'execute', 'program.type': 'execute',
          'program.press': 'execute', 'program.save': 'execute', 'program.answer': 'approve', 'program.shown': 'approve'}
OBSERVERS = ('program.status', 'program.look', 'program.find')


def dispatch(kernel, op, args, principal):
    try:
        if op == 'program.status':return status(kernel, principal, bool(args.get('live')))
        if op == 'program.look':return look_at(kernel, principal, args['path'])
        if op == 'program.find':return find(kernel, principal, args['path'], args['passage'])
        if op == 'program.open':return open_file(kernel, principal, args['path'], args.get('program'))
        if op == 'program.type':return type_text(kernel, principal, args['path'], args['text'], args.get('passage'), args.get('field'))
        if op == 'program.press':return press(kernel, principal, args['path'], args.get('control'), args.get('menu'), args.get('expect'))
        if op == 'program.save':return save(kernel, principal, args['path'], args.get('expect'), args.get('answer'), args.get('menu'))
        if op == 'program.answer':return answer(kernel, principal, args['path'], args['button'], args.get('dialog'))
        if op == 'program.shown':return shown(kernel, principal, args['path'], args['window'])
    except Refused as why:
        _tell(kernel, state='refused', words=str(why).split(': ', 1)[-1][:300], program='', title='', act='', how='')
        raise ValueError(str(why)) from None
    raise ValueError('Unknown program operation')


# ================================================================== joined to K1, K2, K3, K4 and the dial

TOOLS = (
    (31, 'program.open', 'Open a file in its program, in a visible window of its own that is hers to work in while you watch.', 'change',
     ('program.open',), OpenCheck),
    (32, 'program.read', "Read inside her program window through accessibility: its menus, buttons and fields; a passage found in its text.",
     'read', ('program.find', 'program.look'), FindCheck),
    (33, 'program.type', 'Replace a passage, or type into a named field, in her program window (accessibility; keys only where it shows nothing).',
     'change', ('program.type',), TypeCheck),
    (34, 'program.save', "Save in her program window with its menu's Save, or press a named button or menu item; a save is done only when the "
     'file on disk is new.', 'change', ('program.save', 'program.press'), SaveCheck),
    (35, 'program.answer', 'Answer the dialog open over her program window with the button you name (your press, by its own name).', 'change',
     ('program.answer',), AnswerCheck),
)


def _join():
    """The registry's tools 31 to 35 (K2), their checks (K1), the grant family (K3), what always asks (the dial), HALT's stop
    hook (K3) and her planner's verbs and tools (K4). Guarded: what is not here is left as it is; a number or a key taken
    already is never taken over."""
    _asg.CHECKS.update({'program.open': OpenCheck(), 'program.find': FindCheck(), 'program.type': TypeCheck(), 'program.save': SaveCheck(),
                        'program.press': PressCheck(), 'program.answer': AnswerCheck()})
    _asg.TOOL_WORDS.setdefault('program', 'your programs')
    for op, words in (('program.open', 'open a file in its program'), ('program.type', 'type in a program window'),
                      ('program.press', 'press in a program window'), ('program.save', 'save in a program window'),
                      ('program.answer', 'answer a dialog in a program window')):
        _asg.GRANT_WORDS.setdefault(op, words)
    try:
        from . import stacy_hand
        if argument_asks not in getattr(stacy_hand, 'ARGUMENT_ASKS', []):stacy_hand.ARGUMENT_ASKS.append(argument_asks)
    except Exception:  # noqa: BLE001 - the dial without the hook: the Kernel's own guard still refuses
        pass
    try:
        from . import halt_gate
        halt_gate.register_stop('her hand in your programs', _halt_stop)
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import tools_registry as tr
    except Exception:  # noqa: BLE001 - K2 is not in this Graphite
        return False
    for number, key, words, undo, ops, _check in TOOLS:
        if key in tr.TOOLS or number in tr.BY_NUMBER:continue
        path = tr.Arg('path', 'the file in Files', tr.READ_FROM if undo == 'read' else ('RECORD', 'OWNER_WORDS', 'STEP', 'DEDUCTION'))
        args = {'program.open': (path, tr.Arg('program', 'the App (empty: the one set for its type)', ('OWNER_WORDS', 'RECORD'), required=False)),
                'program.read': (path, tr.Arg('passage', 'the words looked for', tr.READ_FROM, required=False)),
                'program.type': (path, tr.Arg('passage', 'the words replaced', ('OWNER_WORDS', 'RECORD', 'STEP'), required=False),
                                 tr.Arg('text', 'the new words', ('OWNER_WORDS', 'RECORD', 'STEP', 'DEDUCTION')),
                                 tr.Arg('field', 'the field, by its name', ('OWNER_WORDS',), required=False)),
                'program.save': (path, tr.Arg('expect', 'the words the saved file must hold', ('OWNER_WORDS', 'RECORD', 'STEP'), required=False),
                                 tr.Arg('answer', 'how a "Keep current format?" dialog is answered: only from your words', ('OWNER_WORDS',), required=False),
                                 tr.Arg('control', 'a button, by its name', ('OWNER_WORDS',), required=False),
                                 tr.Arg('menu', 'a menu item, by its path', ('OWNER_WORDS', 'DEDUCTION'), required=False)),
                'program.answer': (path, tr.Arg('button', 'the button you named', ('OWNER_WORDS',)),
                                   tr.Arg('dialog', 'the dialog, by its title', ('OWNER_WORDS', 'RECORD'), required=False))}[key]
        tool = tr.Tool(number, key, words, 'programs', undo, ops, arguments=args,
                       preconditions=('accessibility is here and your touch can be felt', 'the window is hers: she opened it or you showed it'),
                       effects={'read': 'nothing: a read', 'change': 'what the program does with the press: shown in its window, verified on disk'}[undo],
                       undone={'program.open': 'close the window: it is your program from then on', 'program.read': 'nothing to undo',
                               'program.type': "the program's own Undo, until it is saved", 'program.save': 'the version kept before; Revert is yours to press',
                               'program.answer': 'the program decides; Graphite cannot undo it'}[key],
                       grant={'read': '', 'change': 'work in a program on the file'}[undo] if key != 'program.answer' else 'your press, by its own name',
                       target='path', verify=_check.how, writes_files=key in ('program.save', 'program.answer'), slice='K9',
                       filled={'available': hand_available, 'at': _now_ms()})
        tr.TOOLS[key] = tool;tr.BY_NUMBER[number] = tool
    for op, key in (('program.open', 'program.open'), ('program.find', 'program.read'), ('program.look', 'program.read'),
                    ('program.type', 'program.type'), ('program.save', 'program.save'), ('program.press', 'program.save'),
                    ('program.answer', 'program.answer')):
        tr.KEY_OF.setdefault(op, key)
    try:
        tr.WRITES_FILES = frozenset(tr.WRITES_FILES) | {'program.save', 'program.answer'}
    except Exception:  # noqa: BLE001
        pass
    _join_planner()
    return True


_AVAIL = {}


def hand_available():
    """(whether her hand can work in programs here, why not): kept a few seconds, as the reader's own answer is."""
    now = _mono_ms()
    if _AVAIL and now - _AVAIL['at'] < reader.AVAILABLE_MS:return _AVAIL['answer']
    ok, why = reader.available()
    if ok and not os.environ.get('DISPLAY'):ok, why = False, 'there is no X display here, so she cannot feel your touch'
    _AVAIL.update(at=now, answer=(ok, why))
    return ok, why


# ---------------------------------------------------------------- K4: her planner's words and tools

REPLACE = r'replace|swap|change\s+the\s+(?:sentence|words|passage)'
QUOTED = re.compile(r'["“]([^"”]{1,400})["”]')
KEEP_WORDS = re.compile(r'keep(?:ing)?\s+(?:its|the|their)\s+(?:current\s+|own\s+)?format|keep(?:ing)?\s+it\s+as\s+(?:a\s+)?(?:word|docx)', re.I)
ODF_WORDS = re.compile(r'(?:as|in)\s+(?:the\s+)?odf(?:\s+format)?', re.I)
SAVE_WORDS = re.compile(r'\b(?:and\s+)?save\s+it\b|\band\s+save\b', re.I)
REF_WORDS = ('it', 'this', 'that', 'that one', 'this one', 'this document', 'that document')


def _join_planner():
    try:
        from . import objective_plan as op
    except Exception:  # noqa: BLE001 - K4 is not in this Graphite
        return
    if not any(v[0] == 'replace' for v in op.VERBS):
        op.VERBS = tuple(op.VERBS) + (('replace', REPLACE, (31, 32, 33, 34), True),)
    # The PLAN question shows two of her hand's tools, in few words, and only when their words call for a program's window: 33 (the
    # desk adds the open and the find before it) and 34. The prompt stays lean for every other objective (K4b).
    op.STEP_TOOLS = tuple(op.STEP_TOOLS) + tuple(n for n in (33, 34) if n not in op.STEP_TOOLS)
    op.TAKES.update({33: 'W old words, W new words', 34: 'S (the replace) or D'})
    op.SHORT.update({33: 'replace words in its program window', 34: 'save it there'})
    if hasattr(op, 'USES'):op.USES.update({33: (('document',),), 34: (('document',),)})  # 1.0 K9 (coordinator, at merge): K4b's menu rule
    if hasattr(op, 'TOOL_WHEN'):op.TOOL_WHEN.update({33: wants_hand, 34: wants_hand})
    if hasattr(op, 'PLAN_VERBS'):op.PLAN_VERBS['replace'] = plan_replace
    if hasattr(op, 'MODEL_TOOLS'):op.MODEL_TOOLS.update({33: model_step, 34: model_step})
    if hasattr(op, 'MORE_DOCUMENTS') and more_documents not in op.MORE_DOCUMENTS:op.MORE_DOCUMENTS.append(more_documents)


PROGRAM_WORDS = re.compile(r'\b(?:libreoffice|writer|its\s+(?:own\s+)?(?:program|window)|in\s+the\s+program)\b', re.I)


def wants_hand(objective, clauses):
    """Whether their words call for her hand in a program's window: the verb "replace", or a program named."""
    return any(c.verb == 'replace' for c in clauses or ()) or bool(PROGRAM_WORDS.search(objective or ''))


def more_documents(kernel, Thing):
    """K4's desk, widened: documents her hand can open in their program (Word and plain text files; OpenDocument files are K4's
    own), each at its SHA-256."""
    out = []
    try:
        from . import files_service
        top = files_service.root(kernel)
    except Exception:  # noqa: BLE001
        return out
    seen = 0
    for folder, dirs, names in os.walk(top):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
        for name in sorted(names):
            seen += 1
            if seen > 300:return out
            if name.startswith('.') or not name.lower().endswith(('.docx', '.doc', '.rtf')):continue
            path = Path(folder) / name
            rel = os.path.relpath(path, top).replace(os.sep, '/')
            text = saved_text(path)
            out.append(Thing('', 'document', name, rel, file_sha(path), {'path': rel, 'format': 'Word', 'paragraphs': (text or '').split('\n')}))
    return out


def _span(objective, start, end):
    return {'kind': 'OWNER_WORDS', 'start': start, 'end': end}


def _steps_for(b, doc, passage, text, spans, basis, objective, answer=None, answer_span=None, save=True):
    """The steps of a passage replaced in her program window: open, find, replace, save (each a registered tool)."""
    origin = doc.origin()
    stem = re.sub(r'[^a-z0-9]+', '_', doc.title.lower())[:12]
    keys = []
    keys.append(b.add({'key': b.key('open_' + stem), 'title': 'Open “%s” in its program, in a window of mine' % doc.title, 'operation': 'program.open',
                       'tool_key': 'program.open', 'arguments': {'path': doc.id}, 'origins': {'path': origin}, 'basis': basis,
                       'expected': 'the program open on %s, in a window she may work in' % doc.title}))
    keys.append(b.add({'key': b.key('find_' + stem), 'title': 'Find “%s” through its accessible text' % passage[:60], 'operation': 'program.find',
                       'tool_key': 'program.read', 'arguments': {'path': doc.id, 'passage': passage},
                       'origins': {'path': origin, 'passage': spans[0]}, 'basis': basis, 'expected': 'the passage, once, in her window'}))
    keys.append(b.add({'key': b.key('replace_' + stem), 'title': 'Replace it with “%s” in its window' % text[:60], 'operation': 'program.type',
                       'tool_key': 'program.type', 'arguments': {'path': doc.id, 'passage': passage, 'text': text},
                       'origins': {'path': origin, 'passage': spans[0], 'text': spans[1]}, 'basis': basis,
                       'expected': 'the new words in place in her window, read back'}))
    if save:
        args = {'path': doc.id, 'expect': text};origins = {'path': origin, 'expect': spans[1]}
        title = "Save “%s” with its menu's Save" % doc.title
        if answer:
            args['answer'] = answer;origins['answer'] = answer_span
            title += ', %s if it asks' % ANSWERS[answer][0]
        keys.append(b.add({'key': b.key('save_' + stem), 'title': title, 'operation': 'program.save', 'tool_key': 'program.save',
                           'arguments': args, 'origins': origins, 'basis': basis, 'expected': 'the new revision of %s on disk, holding the new words' % doc.title}))
    return keys


def plan_replace(b, clause, objective, desk, seen, thing):
    """K4's desk planner, the verb "replace": “old words” with “new words” in a document, in its program's window; "and save
    it" adds the save; "keeping its format" is your answer to a "Keep current format?" dialog."""
    from .objective_plan import Refusal
    words = objective[clause.words_start:clause.end]
    quoted = list(QUOTED.finditer(words))
    if len(quoted) < 2:raise Refusal('say the words to replace and the new words, each in quotes')
    a, c = quoted[0], quoted[1]
    spans = [_span(objective, clause.words_start + a.start(1), clause.words_start + a.end(1)),
             _span(objective, clause.words_start + c.start(1), clause.words_start + c.end(1))]
    rest = words[c.end():]
    where = re.split(r'\band\s+save\b|,', re.sub(r'^\s*(?:in|of)\s+', '', rest.strip()), maxsplit=1)[0].strip()
    low = where.casefold()
    if where and low not in REF_WORDS:
        doc, why = desk.find(where, ['document'])
    elif thing is not None and thing.kind == 'document':
        doc, why = thing, ''
    else:
        doc, why = None, 'say which document: replace “…” with “…” in <its name>'
    if doc is None:raise Refusal(why)
    tail = objective[clause.words_start:]
    keep, odf = KEEP_WORDS.search(tail), ODF_WORDS.search(tail)
    answer_span = None;choice = None
    if keep:choice, answer_span = 'keep', _span(objective, clause.words_start + keep.start(), clause.words_start + keep.end())
    elif odf:choice, answer_span = 'odf', _span(objective, clause.words_start + odf.start(), clause.words_start + odf.end())
    _steps_for(b, doc, a.group(1), c.group(1), spans, 'owner_words', objective, choice, answer_span, save=bool(SAVE_WORDS.search(tail)))
    return doc


def _named_document(i):
    """The document their words name after the new words ("… in Rail Demo summary report.docx"), found on the desk; None when
    they name none or more than one."""
    quoted = list(QUOTED.finditer(i.objective or ''))
    if len(quoted) < 2 or i.desk is None:return None
    where = re.split(r'\band\s+save\b|,', re.sub(r'^\s*(?:in|of)\s+', '', i.objective[quoted[1].end():].strip()), maxsplit=1)[0].strip()
    if not where:return None
    doc, _ = i.desk.find(where, ['document'])
    return doc


def model_step(b, number, things, spans, earlier, made, basis, i):
    """K4's model line for tools 33 and 34 (a step holds two handles at most): 33 W W, the old words and the new from their
    words, in the document their words name (the desk adds her window on it and the passage found before the replace); 34 S
    (the replace before it) or D (a document). The desk fills every argument; the model writes none."""
    from .objective_plan import Refusal
    span_of = {n: (s, e) for n, (_, s, e) in enumerate(i.words, 1)}
    picked = [span_of[int(h[1:])] for h in spans if int(h[1:]) in span_of]
    if number == 33:
        if len(picked) != 2:raise Refusal('a replace takes two spans of your words: the old words and the new')
        doc = things[0] if len(things) == 1 else _named_document(i)
        if doc is None or doc.kind != 'document':raise Refusal('your words name no one document for it')
        (s0, e0), (s1, e1) = picked
        spans_ = [_span(i.objective, s0, e0), _span(i.objective, s1, e1)]
        _steps_for(b, doc, i.objective[s0:e0], i.objective[s1:e1], spans_, basis, i.objective, save=False)
        b.k9_last = (doc, i.objective[s1:e1], spans_[1])
    elif number == 34:
        last = getattr(b, 'k9_last', None)
        if len(things) == 1:doc, new, span = things[0], None, None
        elif earlier and last is not None:doc, new, span = last
        else:raise Refusal('a save takes the replace before it (S), or a document (D)')
        if doc.kind != 'document':raise Refusal('her hand saves a document')
        keep = KEEP_WORDS.search(i.objective)
        args = {'path': doc.id};origins = {'path': doc.origin()}
        if new:args['expect'] = new;origins['expect'] = span
        if keep:args['answer'] = 'keep';origins['answer'] = _span(i.objective, keep.start(), keep.end())
        b.add({'key': b.key('save'), 'title': "Save “%s” with its menu's Save" % doc.title + (', keep the current format if it asks' if keep else ''),
               'operation': 'program.save', 'tool_key': 'program.save', 'arguments': args, 'origins': origins, 'basis': basis,
               'expected': 'the new revision on disk'})
    else:
        raise Refusal('%d is not one of her hand\'s tools' % number)


JOINED = _join()
