"""Graphite 1.0 S3 · Program windows: the open program windows, read from the X11 window properties; the window controller
(bring forward, minimise, close politely); and Kasandra's observation of windows, as plain records for K2.

What it reads. The window manager's list of windows (_NET_CLIENT_LIST on the root window; the hidden Fluxbox keeps it) and
the active one (_NET_ACTIVE_WINDOW); for each window its title (_NET_WM_NAME, else WM_NAME), its program (WM_CLASS), its
process (_NET_WM_PID, with WM_CLIENT_MACHINE), its state (_NET_WM_STATE, WM_STATE), its kind (_NET_WM_WINDOW_TYPE,
WM_TRANSIENT_FOR), whether it takes a polite close (WM_PROTOCOLS) and its own icon (_NET_WM_ICON, read once). All of it
through ctypes on the system's libX11: no new wheel. On a bare X server with no window manager that keeps the list, the
top-level windows are the root's mapped children (a child with WM_STATE when a manager reparents them) and the active one
is the one with the keyboard. When libX11 cannot be loaded, `xprop` (x11-utils) reads the same properties, more slowly
(the strip reads it off the window's thread), and only reads: acting then needs `wmctrl` or `xdotool`.

How it learns of a change. Its own X connection selects PropertyNotify on the root (the list, the active window) and on
each listed window (its title, its state); the window strip (windows_strip_qt) watches that connection's socket, drains the
events through pending() and reads again a fraction of a second later, and polls lightly every few seconds as a backstop.
Nothing here runs a loop or a thread of its own.

What it may do, and who decides. Bring forward (_NET_ACTIVE_WINDOW, the source given as a pager, as a task list is),
minimise (WM_CHANGE_STATE iconic, as XIconifyWindow sends it) and close politely (_NET_CLOSE_WINDOW, only to a program that
takes WM_DELETE_WINDOW; with no window manager, WM_DELETE_WINDOW is sent to the program itself): the program is asked and
may ask to save; nothing is ever killed or forced. These run only on the owner's press in the strip. A tool that lets
Kasandra use them (K2) must pass the Kernel's grant first (K3), never the model's word alone. Each answer says what was
asked and whether its effect was seen ('verified'); being sent is never being done.

Kasandra's observation (K2 receives it later): observe() returns a plain record (the tool, when, from what, complete or
not): the windows (title, program, process, active, minimised, a dialog or not, Graphite's own or not), the active one,
and the events since a sequence number ('a new window appeared', 'a new dialog appeared' with their titles, 'closed',
'became active', 'title changed', 'minimised', 'restored'). Reading a window property is an observation; what a title
means (a "Save changes?" prompt) is an inference and is left to the reader.

Without X (Windows, a Mac, a Wayland session, no DISPLAY, an X display that cannot be opened) every answer says "no window
list on this computer" and why, and nothing else changes.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import datetime
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from array import array
from contextlib import contextmanager

NO_LIST = 'no window list on this computer'
TOOL = 'windows_x11'
POLL_SECONDS = 3.0                 # the strip's light poll, the backstop under PropertyNotify
EVENTS_KEPT = 200                  # the observation's memory of events (the oldest go first)
ICON_PX = 32                       # the size of the window's own icon chosen from _NET_WM_ICON (the nearest at least this)

# A task list shows the ordinary windows and dialogs; never docks, desktops, menus, splashes, tool palettes, tooltips or
# notifications, nor a window that asks to be left off (_NET_WM_STATE_SKIP_TASKBAR).
UNLISTED_TYPES = frozenset({
    '_NET_WM_WINDOW_TYPE_DESKTOP', '_NET_WM_WINDOW_TYPE_DOCK', '_NET_WM_WINDOW_TYPE_TOOLBAR', '_NET_WM_WINDOW_TYPE_MENU',
    '_NET_WM_WINDOW_TYPE_UTILITY', '_NET_WM_WINDOW_TYPE_SPLASH', '_NET_WM_WINDOW_TYPE_DROPDOWN_MENU',
    '_NET_WM_WINDOW_TYPE_POPUP_MENU', '_NET_WM_WINDOW_TYPE_TOOLTIP', '_NET_WM_WINDOW_TYPE_NOTIFICATION',
    '_NET_WM_WINDOW_TYPE_COMBO', '_NET_WM_WINDOW_TYPE_DND'})
EVENT_WORDS = ('a new window appeared', 'a new dialog appeared', 'closed', 'became active', 'title changed', 'minimised', 'restored')


class Unavailable(Exception):
    """There is no window list here; str() is the plain reason, starting with NO_LIST."""


def why_not(env=None, platform=None):
    """The plain reason there can be no window list on this computer, or None when an X display is named (opening it may
    still fail, and then its own reason is given)."""
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    if platform.startswith('win') or platform == 'cygwin':
        return NO_LIST + ': Graphite reads the open windows from X11, and Windows has no X11'
    if platform == 'darwin':
        return NO_LIST + ': Graphite reads the open windows from X11, which this Mac does not run'
    if not env.get('DISPLAY'):
        if env.get('WAYLAND_DISPLAY'):
            return NO_LIST + ': this is a Wayland session, and Graphite reads the open windows from X11'
        return NO_LIST + ': there is no X display here (DISPLAY is not set)'
    return None


def hex_id(window):
    return '0x%07x' % int(window)


def _decode(raw):
    if not raw:return ''
    if isinstance(raw, str):return raw
    raw = bytes(raw).rstrip(b'\0')
    if b'\x1b' in raw:      # 1.0 K9: COMPOUND_TEXT (a WM_NAME as LibreOffice's own X windows give it): its UTF-8 runs read as UTF-8
        raw = raw.replace(b'\x1b%G', b'').replace(b'\x1b%@', b'').replace(b'\x1b(B', b'').replace(b'\x1b-A', b'')
    try:return raw.decode('utf-8')
    except UnicodeDecodeError:return raw.decode('latin-1')


def program_words(klass, instance=''):
    """The program's name in words from WM_CLASS when no installed app names it: 'org.gnome.Nautilus' -> 'Nautilus',
    'libreoffice-writer' -> 'Libreoffice writer', 'XTerm' as it is."""
    name = (klass or instance or '').strip()
    if not name:return 'an app'
    if name.count('.') >= 2:name = name.rsplit('.', 1)[-1]
    name = re.sub(r'[-_.]+', ' ', name).strip() or name
    return name[:1].upper() + name[1:] if name[:1].islower() else name


def now_words(stamp=None):
    return datetime.datetime.fromtimestamp(time.time() if stamp is None else stamp).isoformat(timespec='seconds')


# ---- libX11 through ctypes --------------------------------------------------------------------------------------------------
c_int, c_uint, c_long, c_ulong, c_void_p = ctypes.c_int, ctypes.c_uint, ctypes.c_long, ctypes.c_ulong, ctypes.c_void_p
byref, POINTER = ctypes.byref, ctypes.POINTER

XA_ATOM, XA_CARDINAL, XA_STRING, XA_WINDOW = 4, 6, 31, 33
AnyPropertyType = 0
PropertyChangeMask = 1 << 22
StructureNotifyMask = 1 << 17
SubstructureNotifyMask = 1 << 19
SubstructureRedirectMask = 1 << 20
CreateNotify, DestroyNotify, UnmapNotify, MapNotify, ReparentNotify = 16, 17, 18, 19, 21
PropertyNotify, ClientMessage = 28, 33
IsViewable = 2
RevertToParent = 2
CurrentTime = 0
NormalState, IconicState = 1, 3
SOURCE_PAGER = 2                   # EWMH source indication: a pager or task list acting on the owner's press


class XAnyEvent(ctypes.Structure):
    _fields_ = [('type', c_int), ('serial', c_ulong), ('send_event', c_int), ('display', c_void_p), ('window', c_ulong)]


class XPropertyEvent(ctypes.Structure):
    _fields_ = [('type', c_int), ('serial', c_ulong), ('send_event', c_int), ('display', c_void_p), ('window', c_ulong),
                ('atom', c_ulong), ('time', c_ulong), ('state', c_int)]


class _ClientData(ctypes.Union):
    _fields_ = [('b', ctypes.c_char * 20), ('s', ctypes.c_short * 10), ('l', c_long * 5)]


class XClientMessageEvent(ctypes.Structure):
    _fields_ = [('type', c_int), ('serial', c_ulong), ('send_event', c_int), ('display', c_void_p), ('window', c_ulong),
                ('message_type', c_ulong), ('format', c_int), ('data', _ClientData)]


class XEvent(ctypes.Union):
    _fields_ = [('type', c_int), ('xany', XAnyEvent), ('xproperty', XPropertyEvent), ('xclient', XClientMessageEvent),
                ('pad', c_long * 24)]


class XWindowAttributes(ctypes.Structure):
    _fields_ = [('x', c_int), ('y', c_int), ('width', c_int), ('height', c_int), ('border_width', c_int), ('depth', c_int),
                ('visual', c_void_p), ('root', c_ulong), ('c_class', c_int), ('bit_gravity', c_int), ('win_gravity', c_int),
                ('backing_store', c_int), ('backing_planes', c_ulong), ('backing_pixel', c_ulong), ('save_under', c_int),
                ('colormap', c_ulong), ('map_installed', c_int), ('map_state', c_int), ('all_event_masks', c_long),
                ('your_event_mask', c_long), ('do_not_propagate_mask', c_long), ('override_redirect', c_int),
                ('screen', c_void_p)]


class XErrorEvent(ctypes.Structure):
    _fields_ = [('type', c_int), ('display', c_void_p), ('resourceid', c_ulong), ('serial', c_ulong),
                ('error_code', ctypes.c_ubyte), ('request_code', ctypes.c_ubyte), ('minor_code', ctypes.c_ubyte)]


_ERRORS = []                       # the X errors met while this module's calls ran (a window that went away: BadWindow)
_HANDLER_TYPE = ctypes.CFUNCTYPE(c_int, c_void_p, POINTER(XErrorEvent))


def _on_error(display, event):
    """Xlib's default answer to an error is to end the process; a window that closed while it was being read is no reason."""
    try:_ERRORS.append(int(event.contents.error_code))
    except Exception:  # noqa: BLE001 - an error handler never raises into C
        pass
    return 0


_HANDLER = _HANDLER_TYPE(_on_error)
_XLOCK = threading.RLock()         # every libX11 call of this module, from any thread, one at a time
_LIB = []


def _libx11():
    """The system's libX11, its functions declared; Unavailable with the reason when it cannot be loaded."""
    if _LIB:return _LIB[0]
    lib = None
    for name in ('libX11.so.6', ctypes.util.find_library('X11')):
        if not name:continue
        try:lib = ctypes.CDLL(name);break
        except OSError:continue
    if lib is None:raise Unavailable('libX11 could not be loaded')
    sig = {
        'XOpenDisplay': ([ctypes.c_char_p], c_void_p), 'XCloseDisplay': ([c_void_p], c_int),
        'XDefaultRootWindow': ([c_void_p], c_ulong), 'XDefaultScreen': ([c_void_p], c_int),
        'XConnectionNumber': ([c_void_p], c_int), 'XInternAtom': ([c_void_p, ctypes.c_char_p, c_int], c_ulong),
        'XGetAtomName': ([c_void_p, c_ulong], c_void_p), 'XFree': ([c_void_p], c_int),
        'XGetWindowProperty': ([c_void_p, c_ulong, c_ulong, c_long, c_long, c_int, c_ulong, POINTER(c_ulong), POINTER(c_int),
                                POINTER(c_ulong), POINTER(c_ulong), POINTER(c_void_p)], c_int),
        'XSelectInput': ([c_void_p, c_ulong, c_long], c_int), 'XPending': ([c_void_p], c_int),
        'XNextEvent': ([c_void_p, POINTER(XEvent)], c_int), 'XSendEvent': ([c_void_p, c_ulong, c_int, c_long, POINTER(XEvent)], c_int),
        'XFlush': ([c_void_p], c_int), 'XSync': ([c_void_p, c_int], c_int), 'XSetErrorHandler': ([c_void_p], c_void_p),
        'XQueryTree': ([c_void_p, c_ulong, POINTER(c_ulong), POINTER(c_ulong), POINTER(c_void_p), POINTER(c_uint)], c_int),
        'XGetWindowAttributes': ([c_void_p, c_ulong, POINTER(XWindowAttributes)], c_int),
        'XMapRaised': ([c_void_p, c_ulong], c_int), 'XSetInputFocus': ([c_void_p, c_ulong, c_int, c_ulong], c_int),
        'XGetInputFocus': ([c_void_p, POINTER(c_ulong), POINTER(c_int)], c_int),
        'XIconifyWindow': ([c_void_p, c_ulong, c_int], c_int)}
    try:
        for fn, (args, result) in sig.items():
            f = getattr(lib, fn);f.argtypes = args;f.restype = result
    except AttributeError as exc:
        raise Unavailable('libX11 lacks %s' % exc) from exc
    _LIB.append(lib)
    return lib


class XlibBackend:
    """One X connection of Graphite's own, read and acted on through libX11. Every call holds _XLOCK and this module's error
    handler, and ends with an XSync so an error is met inside the call that caused it."""
    source = 'libX11'
    blocking = False               # fast enough for the window's own thread (a few round trips a window)

    def __init__(self, display=None):
        self.x = _libx11()
        name = display or os.environ.get('DISPLAY') or ''
        self.name = name
        with _XLOCK:
            self.dpy = self.x.XOpenDisplay(name.encode() if name else None)
        if not self.dpy:raise Unavailable(NO_LIST + ': the X display %s could not be opened' % (name or '(none named)'))
        self.root = int(self.x.XDefaultRootWindow(self.dpy));self.screen = int(self.x.XDefaultScreen(self.dpy))
        self.atoms = {};self.names = {};self.event = XEvent();self.root_mask = None;self.selected = set()
        self.icon_dirty = set()

    # -- the plumbing
    @contextmanager
    def calls(self):
        with _XLOCK:
            before = self.x.XSetErrorHandler(ctypes.cast(_HANDLER, c_void_p))
            del _ERRORS[:]
            try:yield
            finally:
                try:self.x.XSync(self.dpy, 0)
                finally:self.x.XSetErrorHandler(before)

    def atom(self, name):
        if name not in self.atoms:self.atoms[name] = int(self.x.XInternAtom(self.dpy, name.encode(), 0))
        return self.atoms[name]

    def atom_name(self, atom):
        atom = int(atom)
        if atom not in self.names:
            ptr = self.x.XGetAtomName(self.dpy, atom)
            if not ptr:return ''
            try:self.names[atom] = ctypes.string_at(ptr).decode('latin-1')
            finally:self.x.XFree(ptr)
        return self.names[atom]

    def prop(self, window, name, kind=AnyPropertyType, longs=4096):
        """A property's value: a list of numbers (format 32 or 16), bytes (format 8), or None when it is not set or the window
        is gone."""
        actual, fmt, count, after, data = c_ulong(), c_int(), c_ulong(), c_ulong(), c_void_p()
        status = self.x.XGetWindowProperty(self.dpy, int(window), self.atom(name), 0, int(longs), 0, int(kind), byref(actual),
                                           byref(fmt), byref(count), byref(after), byref(data))
        if status != 0 or not data.value:return None
        try:
            n = int(count.value)
            if fmt.value == 32:return list((c_ulong * n).from_address(data.value))      # 32-bit items arrive as C longs
            if fmt.value == 16:return list((ctypes.c_ushort * n).from_address(data.value))
            if fmt.value == 8:return ctypes.string_at(data.value, n)
            return None
        finally:self.x.XFree(data)

    def children(self, window):
        root, parent, kids, n = c_ulong(), c_ulong(), c_void_p(), c_uint()
        if not self.x.XQueryTree(self.dpy, int(window), byref(root), byref(parent), byref(kids), byref(n)):return [], 0
        try:return (list((c_ulong * int(n.value)).from_address(kids.value)) if kids.value and n.value else []), int(parent.value)
        finally:
            if kids.value:self.x.XFree(kids)

    def attributes(self, window):
        a = XWindowAttributes()
        return a if self.x.XGetWindowAttributes(self.dpy, int(window), byref(a)) else None

    def fileno(self):
        with _XLOCK:return int(self.x.XConnectionNumber(self.dpy))

    def pending(self):
        """Drain the events waiting on this connection; True when one says the list, the active window, a title, a state or
        an icon may have changed."""
        relevant = False
        with _XLOCK:
            watched = {self.atom(n) for n in ('_NET_CLIENT_LIST', '_NET_ACTIVE_WINDOW', '_NET_WM_NAME', 'WM_NAME', '_NET_WM_STATE',
                                              'WM_STATE', '_NET_SUPPORTING_WM_CHECK', '_NET_WM_ICON', 'WM_CLASS')}
            icon = self.atom('_NET_WM_ICON')
            while self.x.XPending(self.dpy):
                self.x.XNextEvent(self.dpy, byref(self.event));kind = self.event.type
                if kind == PropertyNotify:
                    if self.event.xproperty.atom in watched:relevant = True
                    if self.event.xproperty.atom == icon:self.icon_dirty.add(int(self.event.xproperty.window))
                elif kind in (CreateNotify, DestroyNotify, UnmapNotify, MapNotify, ReparentNotify):relevant = True
        return relevant

    # -- reading
    def manager(self):
        """The EWMH window manager's name ('Fluxbox'), or None when no manager keeps the list."""
        check = self.prop(self.root, '_NET_SUPPORTING_WM_CHECK', XA_WINDOW)
        if not check:return None
        again = self.prop(check[0], '_NET_SUPPORTING_WM_CHECK', XA_WINDOW)
        if not again or int(again[0]) != int(check[0]):return None      # a stale mark left by a manager that is gone
        return _decode(self.prop(check[0], '_NET_WM_NAME')) or 'a window manager'

    def tree_clients(self):
        """With no manager's list: the top-level windows as a task list would find them (a root child with WM_STATE, else its
        child with WM_STATE when a manager reparents, else a mapped child that has a name or a class)."""
        out = []
        for child in self.children(self.root)[0]:
            a = self.attributes(child)
            if a is None or a.override_redirect:continue
            if self.prop(child, 'WM_STATE') is not None:out.append(int(child));continue
            inner = next((c for c in self.children(child)[0] if self.prop(c, 'WM_STATE') is not None), None)
            if inner is not None:out.append(int(inner));continue
            if a.map_state == IsViewable and (self.prop(child, 'WM_CLASS') or self.prop(child, '_NET_WM_NAME') or self.prop(child, 'WM_NAME')):
                out.append(int(child))
        return out

    def focused_client(self, clients):
        focus, revert = c_ulong(), c_int()
        self.x.XGetInputFocus(self.dpy, byref(focus), byref(revert))
        w = int(focus.value);listed = set(clients)
        for _ in range(16):      # up from the focused widget to its top-level window
            if w in (0, 1) or w == self.root:return 0      # None, PointerRoot, the root
            if w in listed:return w
            w = self.children(w)[1]
        return 0

    def title(self, window):
        raw = self.prop(window, '_NET_WM_NAME', self.atom('UTF8_STRING'))
        return _decode(raw) if raw else _decode(self.prop(window, 'WM_NAME'))

    def icon(self, window, want=ICON_PX):
        """(width, height, ARGB32 bytes in the machine's order, as QImage.Format_ARGB32 reads them) from _NET_WM_ICON, the
        size nearest `want` that is at least as large (else the largest); None when the window gives none."""
        data = self.prop(window, '_NET_WM_ICON', XA_CARDINAL, longs=1 << 19)
        if not data:return None
        best, i, n = None, 0, len(data)
        while i + 2 <= n:
            w, h = int(data[i]), int(data[i + 1])
            if not (0 < w <= 1024 and 0 < h <= 1024) or i + 2 + w * h > n:break
            score = (w < want, abs(w - want))
            if best is None or score < best[0]:best = (score, w, h, i + 2)
            i += 2 + w * h
        if best is None:return None
        _, w, h, start = best
        return w, h, array('I', (int(v) & 0xFFFFFFFF for v in data[start:start + w * h])).tobytes()

    def read(self, cache):
        """(manager, window ids in the manager's order, the active window, {id: row}, complete) for this moment. `cache` keeps
        what a window does not change (its program, process, kind, protocols) between readings."""
        with self.calls():
            manager = self.manager()
            mask = PropertyChangeMask | (0 if manager else SubstructureNotifyMask)
            if mask != self.root_mask:self.x.XSelectInput(self.dpy, self.root, mask);self.root_mask = mask
            ids = self.prop(self.root, '_NET_CLIENT_LIST', XA_WINDOW) if manager else None
            ids = [int(w) for w in ids] if ids is not None else self.tree_clients()
            active = None
            if manager:
                value = self.prop(self.root, '_NET_ACTIVE_WINDOW', XA_WINDOW)
                if value is not None:active = int(value[0]) if value else 0
            if active is None:active = self.focused_client(ids)
            rows, complete = {}, True
            for w in ids:
                del _ERRORS[:]
                a = self.attributes(w)
                if a is None:complete = False;continue      # gone between the list and now
                if w not in self.selected:self.x.XSelectInput(self.dpy, w, PropertyChangeMask);self.selected.add(w)
                row = dict(cache.get(w) or {})
                if not row:
                    parts = (self.prop(w, 'WM_CLASS') or b'').split(b'\0')
                    pid = self.prop(w, '_NET_WM_PID', XA_CARDINAL)
                    transient = self.prop(w, 'WM_TRANSIENT_FOR', XA_WINDOW)
                    row = dict(instance=_decode(parts[0]) if parts else '', klass=_decode(parts[1]) if len(parts) > 1 else '',
                               pid=int(pid[0]) if pid else None, machine=_decode(self.prop(w, 'WM_CLIENT_MACHINE')),
                               types=[self.atom_name(t) for t in self.prop(w, '_NET_WM_WINDOW_TYPE', XA_ATOM) or []],
                               transient_for=int(transient[0]) if transient else 0,
                               protocols=[self.atom_name(t) for t in self.prop(w, 'WM_PROTOCOLS', XA_ATOM) or []])
                    cache[w] = dict(row)
                row['title'] = self.title(w)
                row['states'] = [self.atom_name(t) for t in self.prop(w, '_NET_WM_STATE', XA_ATOM) or []]
                state = self.prop(w, 'WM_STATE')
                row['wm_state'] = int(state[0]) if state else None
                row['mapped'] = a.map_state == IsViewable
                if _ERRORS:complete = False
                rows[w] = row
            gone = self.selected - set(ids)
            self.selected -= gone
            return manager, ids, active, rows, complete

    # -- acting (the owner's press)
    def _message(self, target, window, message, data, mask):
        ev = XEvent();cm = ev.xclient
        cm.type = ClientMessage;cm.send_event = 1;cm.display = self.dpy;cm.window = int(window)
        cm.message_type = self.atom(message);cm.format = 32
        for i, v in enumerate(list(data)[:5]):cm.data.l[i] = int(v)
        ok = self.x.XSendEvent(self.dpy, int(target), 0, mask, byref(ev))
        self.x.XFlush(self.dpy)
        return bool(ok)

    def activate(self, window, managed, protocols=()):
        with self.calls():
            if managed:
                ok = self._message(self.root, window, '_NET_ACTIVE_WINDOW', (SOURCE_PAGER, CurrentTime, 0),
                                   SubstructureRedirectMask | SubstructureNotifyMask)
                return dict(asked=ok, how='_NET_ACTIVE_WINDOW to the window manager', reason='' if ok else 'the X server refused the request')
            self.x.XMapRaised(self.dpy, int(window));self.x.XSetInputFocus(self.dpy, int(window), RevertToParent, CurrentTime)
        failed = bool(_ERRORS)
        return dict(asked=not failed, how='raised and given the keyboard (no window manager here)',
                    reason='the window could not take the keyboard' if failed else '')

    def minimise(self, window, managed, protocols=()):
        if not managed:
            return dict(asked=False, how='', reason='there is no window manager here to keep a minimised window')
        with self.calls():ok = bool(self.x.XIconifyWindow(self.dpy, int(window), self.screen))
        return dict(asked=ok, how='WM_CHANGE_STATE (iconic) to the window manager', reason='' if ok else 'the X server refused the request')

    def close(self, window, managed, protocols=()):
        if 'WM_DELETE_WINDOW' not in protocols:
            return dict(asked=False, how='', reason='this app cannot be asked to close politely; close it from inside it '
                                                    '(Graphite never forces a window closed)')
        with self.calls():
            if managed:
                ok = self._message(self.root, window, '_NET_CLOSE_WINDOW', (CurrentTime, SOURCE_PAGER),
                                   SubstructureRedirectMask | SubstructureNotifyMask)
                how = '_NET_CLOSE_WINDOW to the window manager'
            else:
                ok = self._message(window, window, 'WM_PROTOCOLS', (self.atom('WM_DELETE_WINDOW'), CurrentTime), 0)
                how = 'WM_DELETE_WINDOW to the app itself (no window manager here)'
        return dict(asked=ok, how=how, reason='' if ok else 'the X server refused the request')

    def close_display(self):
        with _XLOCK:
            if self.dpy:self.x.XCloseDisplay(self.dpy);self.dpy = None


# ---- xprop (x11-utils), the fallback when libX11 cannot be loaded ------------------------------------------------------------
_PROP_LINE = re.compile(r'^(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\((?P<type>[A-Za-z0-9_]+)\))?(?P<rest>.*)$')


def _xprop_values(text):
    """The comma-separated values after '=' in xprop's output: quoted strings (with xprop's escapes), numbers, atom names."""
    out, i, n = [], 0, len(text)
    while i < n:
        while i < n and text[i] in ' \t,':i += 1
        if i >= n:break
        if text[i] == '"':
            i += 1;buf = bytearray()
            while i < n and text[i] != '"':
                c = text[i]
                if c == '\\' and i + 1 < n:
                    nxt = text[i + 1]
                    if nxt in '01234567':
                        m = re.match(r'[0-7]{1,3}', text[i + 1:i + 4]);buf.append(int(m.group(0), 8) & 0xFF);i += 1 + len(m.group(0));continue
                    buf.extend({'n': b'\n', 't': b'\t'}.get(nxt, nxt.encode('utf-8')));i += 2;continue
                buf.extend(c.encode('utf-8'));i += 1
            i += 1;out.append(_decode(bytes(buf)) if buf else '')
        else:
            j = text.find(',', i);j = n if j < 0 else j
            word = text[i:j].strip()
            out.append(int(word, 0) if re.fullmatch(r'-?(0x[0-9a-fA-F]+|\d+)', word) else word)
            i = j
    return out


def parse_xprop(text):
    """{property: value} from xprop's output: window lists and protocols as lists, '=' values as lists, WM_STATE's window
    state as a number (1 normal, 3 iconic). A property 'not found' is left out."""
    props, last = {}, None
    for line in str(text or '').splitlines():
        if line[:1] in ' \t':
            m = re.search(r'window state:\s*(\w+)', line)
            if last == 'WM_STATE' and m:props['WM_STATE'] = [{'Normal': NormalState, 'Iconic': IconicState, 'Withdrawn': 0}.get(m.group(1), 0)]
            continue
        m = _PROP_LINE.match(line.strip())
        if not m:continue
        name, rest = m.group('name'), m.group('rest').strip();last = name
        if 'not found' in rest or 'no such atom' in rest:continue
        if rest.startswith('='):props[name] = _xprop_values(rest[1:]);continue
        if rest.startswith(':'):
            body = rest[1:].strip()
            if '#' in body:props[name] = [int(x, 16) for x in re.findall(r'0x[0-9a-fA-F]+', body.split('#', 1)[1])]
            elif body.startswith('protocols'):props[name] = [w.strip() for w in body[len('protocols'):].split(',') if w.strip()]
            elif body:props[name] = [body]
            else:props[name] = []
    return props


class XpropBackend:
    """The same reading through the `xprop` program; slower (one run for the root and one for each window), so the strip
    reads it off the window's thread. Acting needs wmctrl (bring forward, close) or xdotool (minimise)."""
    source = 'xprop'
    blocking = True
    WINDOW_PROPS = ('_NET_WM_NAME', 'WM_NAME', 'WM_CLASS', '_NET_WM_PID', 'WM_CLIENT_MACHINE', '_NET_WM_STATE', 'WM_STATE',
                    '_NET_WM_WINDOW_TYPE', 'WM_TRANSIENT_FOR', 'WM_PROTOCOLS')

    def __init__(self, display=None, runner=None):
        self.exe = shutil.which('xprop')
        if not self.exe and runner is None:raise Unavailable('xprop is not installed')
        self.env = dict(os.environ, LC_ALL='C.UTF-8', **({'DISPLAY': display} if display else {}))
        self.runner = runner or self._run
        self.wmctrl, self.xdotool = shutil.which('wmctrl'), shutil.which('xdotool')
        self.icon_dirty = set()
        if runner is None and self.runner('-root', '_NET_SUPPORTING_WM_CHECK') is None:
            raise Unavailable(NO_LIST + ': xprop could not read the X display %s' % self.env.get('DISPLAY', ''))

    def _run(self, *args):
        try:done = subprocess.run([self.exe, *args], capture_output=True, timeout=3, env=self.env)
        except (OSError, subprocess.SubprocessError):return None
        return done.stdout.decode('utf-8', 'replace') if done.returncode == 0 else None

    def fileno(self):return None

    def pending(self):return False

    def icon(self, window, want=ICON_PX):return None      # _NET_WM_ICON through xprop would be thousands of numbers: not read

    def read(self, cache):
        root = parse_xprop(self.runner('-root', '_NET_SUPPORTING_WM_CHECK', '_NET_CLIENT_LIST', '_NET_ACTIVE_WINDOW') or '')
        manager = 'a window manager' if root.get('_NET_SUPPORTING_WM_CHECK') else None
        if not manager or '_NET_CLIENT_LIST' not in root:
            raise Unavailable(NO_LIST + ': read through xprop, the window list needs a window manager that keeps it')
        ids = [int(w) for w in root.get('_NET_CLIENT_LIST', [])]
        active = int((root.get('_NET_ACTIVE_WINDOW') or [0])[0])
        rows, complete = {}, True
        for w in ids:
            text = self.runner('-id', hex(w), *self.WINDOW_PROPS)
            if text is None:complete = False;continue
            p = parse_xprop(text);cls = [str(v) for v in p.get('WM_CLASS', [])]
            title = p.get('_NET_WM_NAME') or p.get('WM_NAME') or ['']
            rows[w] = dict(instance=cls[0] if cls else '', klass=cls[1] if len(cls) > 1 else '',
                           pid=int(p['_NET_WM_PID'][0]) if p.get('_NET_WM_PID') else None,
                           machine=str((p.get('WM_CLIENT_MACHINE') or [''])[0]), types=[str(t) for t in p.get('_NET_WM_WINDOW_TYPE', [])],
                           transient_for=int((p.get('WM_TRANSIENT_FOR') or [0])[0]), protocols=[str(t) for t in p.get('WM_PROTOCOLS', [])],
                           title=str(title[0]), states=[str(s) for s in p.get('_NET_WM_STATE', [])],
                           wm_state=int(p['WM_STATE'][0]) if p.get('WM_STATE') else None, mapped=True)
        return manager, ids, active, rows, complete

    def _tool(self, argv, how):
        try:done = subprocess.run(argv, capture_output=True, timeout=3, env=self.env)
        except (OSError, subprocess.SubprocessError) as exc:return dict(asked=False, how=how, reason=str(exc))
        return dict(asked=done.returncode == 0, how=how, reason='' if done.returncode == 0 else 'the tool said no')

    def activate(self, window, managed, protocols=()):
        if not self.wmctrl:return dict(asked=False, how='', reason='bringing a window forward needs libX11 or wmctrl, and neither is here')
        return self._tool([self.wmctrl, '-i', '-a', hex(window)], 'wmctrl -a')

    def minimise(self, window, managed, protocols=()):
        if not self.xdotool:return dict(asked=False, how='', reason='minimising needs libX11 or xdotool, and neither is here')
        return self._tool([self.xdotool, 'windowminimize', str(int(window))], 'xdotool windowminimize')

    def close(self, window, managed, protocols=()):
        if 'WM_DELETE_WINDOW' not in protocols:
            return dict(asked=False, how='', reason='this app cannot be asked to close politely; close it from inside it '
                                                    '(Graphite never forces a window closed)')
        if not self.wmctrl:return dict(asked=False, how='', reason='closing a window needs libX11 or wmctrl, and neither is here')
        return self._tool([self.wmctrl, '-i', '-c', hex(window)], 'wmctrl -c')

    def close_display(self):pass


def open_backend(display=None, env=None):
    """libX11 first, xprop when libX11 cannot be loaded; Unavailable with the plain reason when neither reads the display."""
    env = dict(os.environ if env is None else env)
    if display:env['DISPLAY'] = display
    reason = why_not(env)
    if reason:raise Unavailable(reason)
    try:return XlibBackend(env.get('DISPLAY'))
    except Unavailable as first:
        if str(first).startswith(NO_LIST):raise      # the display itself could not be opened: xprop would fare no better
        try:return XpropBackend(env.get('DISPLAY'))
        except Unavailable as second:
            if str(second).startswith(NO_LIST):raise
            raise Unavailable(NO_LIST + ': neither libX11 nor xprop (x11-utils) is installed') from second


# ---- the watcher: the list, its events, the controller ------------------------------------------------------------------------
class Watcher:
    """The open windows as last read, the events between readings, and the three actions. One per process is enough
    (shared()); the strip and observe() use the same one. `own_windows` (a set of X window ids, set by the strip from the
    window's thread) and this process's id mark Graphite's own windows."""

    def __init__(self, display=None, backend=None, env=None):
        self.display, self.backend, self.env = display, backend, env
        self.reason = '';self.started = backend is not None
        self.lock = threading.RLock()
        self.cache, self.icons, self.order = {}, {}, []
        self.own_windows = set();self.pid = os.getpid();self.host = socket.gethostname()
        self.last = None;self.events = [];self.seq = 0;self.read_at = 0.0

    def start(self):
        """Open the X connection once (a slow display is met here, so the strip calls this off the window's thread). True
        when windows can be read."""
        with self.lock:
            if not self.started:
                self.started = True
                try:self.backend = open_backend(self.display, self.env)
                except Unavailable as exc:
                    self.reason = str(exc) if str(exc).startswith(NO_LIST) else NO_LIST + ': ' + str(exc)
            return self.backend is not None

    @property
    def available(self):
        return self.backend is not None and (self.last is None or bool(self.last.get('available', True)))

    def fileno(self):
        return self.backend.fileno() if self.backend is not None else None

    def pending(self):
        if self.backend is None:return False
        try:return self.backend.pending()
        except Exception:  # noqa: BLE001 - a bad event is never worth the window
            return True

    def _row(self, w, raw, manager, active):
        states = raw.get('states') or []
        types = raw.get('types') or []
        own = (raw.get('pid') == self.pid and raw.get('machine', '') in ('', self.host)) or w in self.own_windows
        minimised = '_NET_WM_STATE_HIDDEN' in states or raw.get('wm_state') == IconicState
        dialog = '_NET_WM_WINDOW_TYPE_DIALOG' in types or bool(raw.get('transient_for')) or '_NET_WM_STATE_MODAL' in states
        listed = '_NET_WM_STATE_SKIP_TASKBAR' not in states and not (set(types) & UNLISTED_TYPES)
        return dict(window=w, id=hex_id(w), title=raw.get('title') or '', program=program_words(raw.get('klass'), raw.get('instance')),
                    klass=raw.get('klass') or '', instance=raw.get('instance') or '', pid=raw.get('pid'), active=w == active and bool(w),
                    minimised=minimised, dialog=dialog, graphite=own, listed=listed, transient_for=raw.get('transient_for') or 0,
                    protocols=list(raw.get('protocols') or []), types=list(types), states=list(states))

    def refresh(self):
        """Read the windows now; returns the snapshot and keeps the events it shows against the last one."""
        if not self.start():return self.snapshot()
        with self.lock:
            try:manager, ids, active, raw, complete = self.backend.read(self.cache)
            except Unavailable as exc:
                self.reason = str(exc);self.last = dict(available=False, reason=self.reason, source=self.backend.source, manager=None,
                                                         windows=[], active=0, complete=False, read_at=time.time())
                return self.snapshot()
            except Exception:  # noqa: BLE001 - a reading that failed keeps the last one; the next poll reads again
                return self.snapshot()
            for w in ids:
                if w in raw and w not in self.order:self.order.append(w)
            self.order = [w for w in self.order if w in raw]
            for w in list(self.cache):
                if w not in raw:self.cache.pop(w, None);self.icons.pop(w, None)
            for w in getattr(self.backend, 'icon_dirty', ()):self.icons.pop(w, None)
            getattr(self.backend, 'icon_dirty', set()).clear()
            rows = [self._row(w, raw[w], manager, active) for w in self.order]
            snap = dict(available=True, reason='', source=self.backend.source, manager=manager, windows=rows,
                        active=active if any(r['window'] == active for r in rows) else 0, complete=complete, read_at=time.time())
            self._compare(self.last, snap)
            self.last = snap;self.read_at = snap['read_at']
            self.reason = ''
            return self.snapshot()

    def _event(self, word, row, **more):
        self.seq += 1
        record = dict(seq=self.seq, event=word, window=row['id'], title=row['title'], program=row['program'], graphite=row['graphite'],
                      dialog=row['dialog'], at=now_words(), **more)
        self.events.append(record)
        del self.events[:-EVENTS_KEPT]

    def _compare(self, before, after):
        if not before or not before.get('available'):return      # the first reading: what is open is listed, not announced
        old = {r['window']: r for r in before['windows']}
        new = {r['window']: r for r in after['windows']}
        for w, row in new.items():
            if w not in old:self._event('a new dialog appeared' if row['dialog'] else 'a new window appeared', row)
        for w, row in old.items():
            if w not in new:self._event('closed', row)
        for w, row in new.items():
            was = old.get(w)
            if was is None:continue
            if was['title'] != row['title']:self._event('title changed', row, before=was['title'])
            if was['minimised'] != row['minimised']:self._event('minimised' if row['minimised'] else 'restored', row)
        if after['active'] and after['active'] != before.get('active'):
            self._event('became active', new[after['active']])

    def snapshot(self):
        """The last reading (no X call); when there is no list, the reason."""
        with self.lock:
            if self.last is not None and self.backend is not None:return dict(self.last, windows=[dict(r) for r in self.last['windows']])
            return dict(available=False, reason=self.reason or (NO_LIST if self.started else ''), source=getattr(self.backend, 'source', ''),
                        manager=None, windows=[], active=0, complete=False, read_at=self.read_at)

    def icon(self, window):
        """The window's own icon (width, height, ARGB32 bytes) from _NET_WM_ICON, read once; None when it gives none."""
        if self.backend is None:return None
        with self.lock:
            if window not in self.icons:
                try:
                    with (self.backend.calls() if hasattr(self.backend, 'calls') else _nothing()):
                        self.icons[window] = self.backend.icon(window)
                except Exception:  # noqa: BLE001 - a window without a readable icon has the program's words instead
                    self.icons[window] = None
            return self.icons[window]

    def row(self, window):
        snap = self.snapshot()
        return next((r for r in snap['windows'] if r['window'] == int(window)), None)

    def _act(self, kind, window, wait):
        window = int(window)
        if not self.start():return dict(asked=False, verified=False, how='', reason=self.reason, window=hex_id(window), action=kind)
        row = self.row(window) or {}
        managed = bool((self.last or {}).get('manager'))
        with self.lock:
            try:answer = getattr(self.backend, kind)(window, managed, row.get('protocols') or ())
            except Exception as exc:  # noqa: BLE001 - the strip says why; the desktop goes on
                answer = dict(asked=False, how='', reason=str(exc))
        answer = dict(answer, window=hex_id(window), action=kind, title=row.get('title', ''), verified=False)
        if answer['asked'] and (wait > 0 or not getattr(self.backend, 'blocking', False)):      # xprop reads slowly: only when asked to wait
            answer['verified'] = self.verify(kind, window, wait)
        return answer

    def verify(self, kind, window, wait=0.0):
        """Whether the action's effect is seen in a fresh reading (within `wait` seconds): the window is the active one, is
        minimised, or is gone."""
        end = time.monotonic() + max(0.0, float(wait))
        while True:
            snap = self.refresh();row = next((r for r in snap['windows'] if r['window'] == int(window)), None)
            seen = (kind == 'activate' and row is not None and row['active']) or (kind == 'minimise' and row is not None and row['minimised']) \
                or (kind == 'close' and row is None and snap['available'])
            if seen or time.monotonic() >= end:return bool(seen)
            time.sleep(0.05)

    def activate(self, window, wait=0.0):return self._act('activate', window, wait)

    def minimise(self, window, wait=0.0):return self._act('minimise', window, wait)

    def close(self, window, wait=0.0):return self._act('close', window, wait)

    def observe(self, since=None, fresh=True):
        """Kasandra's observation of windows: a plain record for K2 (the tool, when, from what, complete or not), the windows,
        the active one, and the events after sequence number `since` (all kept when None); 'seq' is the next `since`."""
        snap = self.refresh() if fresh else self.snapshot()
        with self.lock:
            events = [dict(e) for e in self.events if since is None or e['seq'] > int(since)]
            seq = self.seq
        public = ('id', 'title', 'program', 'klass', 'instance', 'pid', 'active', 'minimised', 'dialog', 'graphite', 'listed')
        windows = [{k: r[k] for k in public} for r in snap['windows']]
        active = next((w for w in windows if w['active']), None)
        return dict(tool=TOOL, kind='windows', observed=True, observed_at=now_words(snap.get('read_at') or None),
                    basis=('the X11 window properties through %s' % snap['source']) if snap['available'] else '',
                    available=snap['available'], reason=snap['reason'], source=snap['source'], manager=snap['manager'],
                    complete=snap['complete'], windows=windows, active=active, events=events, seq=seq)


@contextmanager
def _nothing():
    yield


_SHARED = []
_SHARED_LOCK = threading.Lock()


def shared():
    """The process's one Watcher (the strip's and observe()'s)."""
    with _SHARED_LOCK:
        if not _SHARED:_SHARED.append(Watcher())
        return _SHARED[0]


def observe(since=None):
    """Kasandra's observation of the open windows (see Watcher.observe); without X, available False and the reason."""
    return shared().observe(since)


def status():
    """{'available', 'reason', 'source', 'manager'}: whether this computer has a window list, and why not."""
    w = shared()
    snap = w.refresh() if w.start() and w.last is None else w.snapshot()
    return dict(available=w.available, reason=w.reason if not w.available else '', source=snap.get('source', ''), manager=snap.get('manager'))
