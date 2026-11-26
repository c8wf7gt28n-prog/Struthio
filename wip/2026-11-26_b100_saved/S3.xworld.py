"""S3 smoke helper (throwaway, never in the tree): plain X windows and, with --wm, a tiny stand-in EWMH window manager, all
in ONE process (one X connection for the manager, one for the windows), driven by lines appended to a command file.

  python xworld.py [--wm] --commands FILE --log FILE --window 'Title|instance|Class[|icon]' ...
  commands: 'dialog <title>' (a dialog transient for the first window), 'quit'

The stand-in manager keeps _NET_SUPPORTING_WM_CHECK, _NET_CLIENT_LIST, _NET_ACTIVE_WINDOW, WM_STATE and _NET_WM_STATE
(HIDDEN), and answers _NET_ACTIVE_WINDOW (raise, focus, de-iconify), _NET_CLOSE_WINDOW (WM_DELETE_WINDOW to the program,
never a kill) and WM_CHANGE_STATE iconic (unmap, WM_STATE iconic, HIDDEN). A plain window closes on WM_DELETE_WINDOW.
"""
import ctypes
import os
import select
import socket
import sys
import time
from ctypes import POINTER, byref, c_char_p, c_int, c_long, c_uint, c_ulong, c_void_p

x = ctypes.CDLL('libX11.so.6')


class Any(ctypes.Structure):
    _fields_ = [('type', c_int), ('serial', c_ulong), ('send_event', c_int), ('display', c_void_p), ('window', c_ulong)]


class MapReq(ctypes.Structure):
    _fields_ = [('type', c_int), ('serial', c_ulong), ('send_event', c_int), ('display', c_void_p), ('parent', c_ulong), ('window', c_ulong)]


class ConfReq(ctypes.Structure):
    _fields_ = [('type', c_int), ('serial', c_ulong), ('send_event', c_int), ('display', c_void_p), ('parent', c_ulong), ('window', c_ulong),
                ('x', c_int), ('y', c_int), ('width', c_int), ('height', c_int), ('border_width', c_int), ('above', c_ulong),
                ('detail', c_int), ('value_mask', c_ulong)]


class Unmap(ctypes.Structure):
    _fields_ = [('type', c_int), ('serial', c_ulong), ('send_event', c_int), ('display', c_void_p), ('event', c_ulong), ('window', c_ulong),
                ('from_configure', c_int)]


class Data(ctypes.Union):
    _fields_ = [('b', ctypes.c_char * 20), ('s', ctypes.c_short * 10), ('l', c_long * 5)]


class Client(ctypes.Structure):
    _fields_ = [('type', c_int), ('serial', c_ulong), ('send_event', c_int), ('display', c_void_p), ('window', c_ulong),
                ('message_type', c_ulong), ('format', c_int), ('data', Data)]


class Event(ctypes.Union):
    _fields_ = [('type', c_int), ('any', Any), ('mapreq', MapReq), ('confreq', ConfReq), ('unmap', Unmap), ('client', Client), ('pad', c_long * 24)]


class Changes(ctypes.Structure):
    _fields_ = [('x', c_int), ('y', c_int), ('width', c_int), ('height', c_int), ('border_width', c_int), ('sibling', c_ulong), ('stack_mode', c_int)]


ERR = ctypes.CFUNCTYPE(c_int, c_void_p, c_void_p)(lambda d, e: 0)
x.XSetErrorHandler.argtypes = [c_void_p]; x.XSetErrorHandler.restype = c_void_p
x.XSetErrorHandler(ctypes.cast(ERR, c_void_p))
x.XOpenDisplay.argtypes = [c_char_p]; x.XOpenDisplay.restype = c_void_p
for name in ('XDefaultRootWindow', 'XBlackPixel', 'XWhitePixel', 'XCreateSimpleWindow', 'XInternAtom'):
    getattr(x, name).restype = c_ulong
x.XDefaultRootWindow.argtypes = [c_void_p]
x.XBlackPixel.argtypes = [c_void_p, c_int]; x.XWhitePixel.argtypes = [c_void_p, c_int]
x.XCreateSimpleWindow.argtypes = [c_void_p, c_ulong, c_int, c_int, c_uint, c_uint, c_uint, c_ulong, c_ulong]
x.XInternAtom.argtypes = [c_void_p, c_char_p, c_int]
x.XChangeProperty.argtypes = [c_void_p, c_ulong, c_ulong, c_ulong, c_int, c_int, c_void_p, c_int]
x.XDeleteProperty.argtypes = [c_void_p, c_ulong, c_ulong]
x.XGetWindowProperty.argtypes = [c_void_p, c_ulong, c_ulong, c_long, c_long, c_int, c_ulong, POINTER(c_ulong), POINTER(c_int),
                                 POINTER(c_ulong), POINTER(c_ulong), POINTER(c_void_p)]
x.XFree.argtypes = [c_void_p]
for name in ('XMapWindow', 'XUnmapWindow', 'XDestroyWindow', 'XRaiseWindow', 'XMapRaised'):
    getattr(x, name).argtypes = [c_void_p, c_ulong]
x.XSelectInput.argtypes = [c_void_p, c_ulong, c_long]
x.XSetInputFocus.argtypes = [c_void_p, c_ulong, c_int, c_ulong]
x.XConfigureWindow.argtypes = [c_void_p, c_ulong, c_uint, POINTER(Changes)]
x.XSendEvent.argtypes = [c_void_p, c_ulong, c_int, c_long, POINTER(Event)]
x.XPending.argtypes = [c_void_p]; x.XNextEvent.argtypes = [c_void_p, POINTER(Event)]
x.XFlush.argtypes = [c_void_p]; x.XConnectionNumber.argtypes = [c_void_p]
x.XStoreName.argtypes = [c_void_p, c_ulong, c_char_p]

XA_ATOM, XA_CARDINAL, XA_STRING, XA_WINDOW = 4, 6, 31, 33
LOG = None


def log(*words):
    with open(LOG, 'a') as f:f.write(' '.join(str(w) for w in words) + '\n')


class Conn:
    def __init__(self):
        self.d = x.XOpenDisplay(None)
        if not self.d:raise SystemExit('no display')
        self.root = x.XDefaultRootWindow(self.d);self.atoms = {}

    def atom(self, name):
        if name not in self.atoms:self.atoms[name] = x.XInternAtom(self.d, name.encode(), 0)
        return self.atoms[name]

    def set32(self, w, name, kind, values):
        arr = (c_long * max(1, len(values)))(*values)
        x.XChangeProperty(self.d, w, self.atom(name), kind, 32, 0, arr, len(values))

    def set8(self, w, name, kind, raw):
        buf = ctypes.create_string_buffer(raw, len(raw))
        x.XChangeProperty(self.d, w, self.atom(name), kind, 8, 0, buf, len(raw))

    def get32(self, w, name):
        actual, fmt, n, after, data = c_ulong(), c_int(), c_ulong(), c_ulong(), c_void_p()
        if x.XGetWindowProperty(self.d, w, self.atom(name), 0, 64, 0, 0, byref(actual), byref(fmt), byref(n), byref(after), byref(data)) or not data.value:
            return []
        try:return list((c_ulong * n.value).from_address(data.value)) if fmt.value == 32 else []
        finally:x.XFree(data)


class WM(Conn):
    def __init__(self):
        super().__init__()
        x.XSelectInput(self.d, self.root, (1 << 20) | (1 << 19))      # SubstructureRedirect | SubstructureNotify
        self.check = x.XCreateSimpleWindow(self.d, self.root, -10, -10, 1, 1, 0, 0, 0)
        for w in (self.root, self.check):self.set32(w, '_NET_SUPPORTING_WM_CHECK', XA_WINDOW, [self.check])
        self.set8(self.check, '_NET_WM_NAME', self.atom('UTF8_STRING'), b'Stand-in WM')
        self.set32(self.root, '_NET_SUPPORTED', XA_ATOM, [self.atom(n) for n in ('_NET_CLIENT_LIST', '_NET_ACTIVE_WINDOW', '_NET_CLOSE_WINDOW',
                                                                                  '_NET_WM_STATE', '_NET_WM_STATE_HIDDEN', '_NET_WM_NAME', '_NET_WM_PID')])
        self.clients, self.iconic, self.active = [], set(), 0
        self.publish()

    def publish(self):
        self.set32(self.root, '_NET_CLIENT_LIST', XA_WINDOW, self.clients)
        self.set32(self.root, '_NET_ACTIVE_WINDOW', XA_WINDOW, [self.active])
        x.XFlush(self.d)

    def hidden(self, w, on):
        states = [s for s in self.get32(w, '_NET_WM_STATE') if s != self.atom('_NET_WM_STATE_HIDDEN')]
        if on:states.append(self.atom('_NET_WM_STATE_HIDDEN'))
        self.set32(w, '_NET_WM_STATE', XA_ATOM, states)
        self.set32(w, 'WM_STATE', self.atom('WM_STATE'), [3 if on else 1, 0])

    def activate(self, w):
        if w in self.iconic:
            self.iconic.discard(w);x.XMapWindow(self.d, w);self.hidden(w, False)
        x.XRaiseWindow(self.d, w);x.XSetInputFocus(self.d, w, 1, 0);self.active = w;self.publish()

    def handle(self, ev):
        t = ev.type
        if t == 20:      # MapRequest
            w = ev.mapreq.window
            x.XMapWindow(self.d, w)
            if w not in self.clients:self.clients.append(w)
            self.iconic.discard(w);self.hidden(w, False);self.activate(w);log('wm mapped', hex(w))
        elif t == 23:    # ConfigureRequest
            c = ev.confreq;ch = Changes(c.x, c.y, c.width, c.height, c.border_width, c.above, c.detail)
            x.XConfigureWindow(self.d, c.window, c.value_mask & 0x7f, byref(ch))
        elif t == 18:    # UnmapNotify
            w = ev.unmap.window
            if w in self.clients and w not in self.iconic:
                self.clients.remove(w);self.active = 0 if self.active == w else self.active;self.publish();log('wm withdrawn', hex(w))
        elif t == 17:    # DestroyNotify
            w = ev.unmap.window
            if w in self.clients:
                self.clients.remove(w);self.iconic.discard(w);self.active = 0 if self.active == w else self.active;self.publish();log('wm destroyed', hex(w))
        elif t == 33:    # ClientMessage
            c = ev.client;w = c.window;kind = c.message_type
            if kind == self.atom('_NET_ACTIVE_WINDOW') and w in self.clients:
                self.activate(w);log('wm activate', hex(w), 'source', c.data.l[0])
            elif kind == self.atom('_NET_CLOSE_WINDOW') and w in self.clients:
                protocols = self.get32(w, 'WM_PROTOCOLS')
                if self.atom('WM_DELETE_WINDOW') in protocols:
                    out = Event();m = out.client;m.type = 33;m.send_event = 1;m.window = w;m.message_type = self.atom('WM_PROTOCOLS');m.format = 32
                    m.data.l[0] = self.atom('WM_DELETE_WINDOW');m.data.l[1] = 0
                    x.XSendEvent(self.d, w, 0, 0, byref(out));x.XFlush(self.d);log('wm close asked', hex(w))
                else:log('wm close refused (no WM_DELETE_WINDOW): never killed', hex(w))
            elif kind == self.atom('WM_CHANGE_STATE') and c.data.l[0] == 3 and w in self.clients:
                self.iconic.add(w);x.XUnmapWindow(self.d, w);self.hidden(w, True)
                if self.active == w:self.active = 0
                self.publish();log('wm iconified', hex(w))


class Windows(Conn):
    def __init__(self):
        super().__init__();self.made = {};self.first = None

    def make(self, title, instance, klass, icon=False, dialog_for=0):
        scr = 0
        w = x.XCreateSimpleWindow(self.d, self.root, 40 + 60 * len(self.made), 60 + 40 * len(self.made), 420, 240, 1,
                                  x.XBlackPixel(self.d, scr), x.XWhitePixel(self.d, scr))
        x.XStoreName(self.d, w, title.encode('latin-1', 'replace'))
        self.set8(w, '_NET_WM_NAME', self.atom('UTF8_STRING'), title.encode('utf-8'))
        self.set8(w, 'WM_CLASS', XA_STRING, instance.encode() + b'\0' + klass.encode() + b'\0')
        self.set8(w, 'WM_CLIENT_MACHINE', XA_STRING, socket.gethostname().encode())
        self.set32(w, '_NET_WM_PID', XA_CARDINAL, [os.getpid()])
        self.set32(w, 'WM_PROTOCOLS', XA_ATOM, [self.atom('WM_DELETE_WINDOW')])
        if icon:
            px = []
            for yy in range(16):
                for xx in range(16):
                    edge = xx in (0, 15) or yy in (0, 15)
                    px.append(0xFF2E5E3A if edge else (0xFF8FD18A if (xx + yy) % 5 else 0xFFF0F4E8))
            self.set32(w, '_NET_WM_ICON', XA_CARDINAL, [16, 16] + [v - (1 << 32) if v >= 1 << 31 else v for v in px])
        if dialog_for:
            self.set32(w, '_NET_WM_WINDOW_TYPE', XA_ATOM, [self.atom('_NET_WM_WINDOW_TYPE_DIALOG')])
            self.set32(w, 'WM_TRANSIENT_FOR', XA_WINDOW, [dialog_for])
        x.XSelectInput(self.d, w, 1 << 17)
        x.XMapWindow(self.d, w);x.XFlush(self.d)
        self.made[w] = title;self.first = self.first or w
        log('window', hex(w), title)
        return w

    def handle(self, ev):
        if ev.type == 33 and ev.client.message_type == self.atom('WM_PROTOCOLS') and ev.client.data.l[0] == self.atom('WM_DELETE_WINDOW'):
            w = ev.client.window
            log('closed', hex(w), self.made.pop(w, '?'), '(asked politely)')
            x.XDestroyWindow(self.d, w);x.XFlush(self.d)


def main(argv):
    global LOG
    wm_on = '--wm' in argv
    commands = argv[argv.index('--commands') + 1];LOG = argv[argv.index('--log') + 1]
    specs = [argv[i + 1] for i, a in enumerate(argv) if a == '--window']
    wm = WM() if wm_on else None
    if wm:log('stand-in window manager on')
    wins = Windows()
    for spec in specs:
        parts = spec.split('|')
        wins.make(parts[0], parts[1], parts[2], icon=len(parts) > 3 and parts[3] == 'icon')
    log('ready')
    done = 0;conns = [c for c in (wm, wins) if c]
    fds = {x.XConnectionNumber(c.d): c for c in conns}
    ev = Event()
    while True:
        select.select(list(fds), [], [], 0.2)
        for c in conns:
            while x.XPending(c.d):
                x.XNextEvent(c.d, byref(ev));c.handle(ev)
            x.XFlush(c.d)
        try:
            with open(commands) as f:lines = f.read().splitlines()
        except OSError:
            lines = []
        for line in lines[done:]:
            if line.startswith('dialog '):wins.make(line[7:], 'raildemo-dialog', 'RailDemoDialog', dialog_for=wins.first or 0)
            elif line.startswith('window '):wins.make(line[7:], 'railsketch', 'RailSketch')
            elif line == 'quit':log('quit');return 0
        done = len(lines)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
