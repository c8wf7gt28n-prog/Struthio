"""Graphite 1.0 S5 · The strip as a dock: the open app windows and a "Graphite" entry in a slim window of their own.

S3's strip lives inside Graphite's window, so an app in front of Graphite hides it. In the dedicated session the strip
therefore also stands in a slim window of its own across the top of the screen, of the dock type with a strut:

  _NET_WM_WINDOW_TYPE   _NET_WM_WINDOW_TYPE_DOCK: the window manager keeps it above the apps, never gives it the focus,
                        never decorates it, and keeps it on every desktop (_NET_WM_DESKTOP 0xFFFFFFFF as well);
  _NET_WM_STRUT_PARTIAL its band at the top of the screen (and _NET_WM_STRUT, for managers that read only that), so the
                        window manager places and maximises the apps below it.

Both are written on the dock's own X window through ctypes on the system's libX11 (as windows_x11 reads), before the window
is shown, then read back; Qt's own dock attribute says the same. Its first entry is "Graphite" (Graphite's mark and the
word; ▸ and a rule under it while Graphite's window is the active one): one press always brings Graphite's window forward
(the window manager is asked, as a task list asks, and it is verified active). After it, S3's strip: each app window, one
press brings it forward, the right-click minimises or closes it politely; Graphite's own open dialogs stand apart at the
right end. With no app window open it says so in quiet words.

When it stands: in the dedicated session (ARC_LEDGER_XSESSION=1), or wherever GRAPHITE_DOCK=1; never with GRAPHITE_DOCK=0;
only when Graphite's window is on X (the xcb platform) and libX11 answers. Otherwise the strip stays inside Graphite's
window exactly as S3 built it, and status() says why there is no dock.

Graphite's window in the dedicated session is full screen: while it is in front it covers the dock (a full-screen window
stands above docks), so S3's strip inside it still shows the windows; while an app is in front, the dock shows. When
Graphite's window is not full screen it sits below the dock like any app, and its own strip gives way to the dock's
(windows_strip_qt.WindowStrip.room asks carries_strip()).
"""
from __future__ import annotations

import ctypes
import os
import time

from PySide6.QtCore import QEvent, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFontMetrics, QGuiApplication, QPainter
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel, QWidget

from . import boss_theme as bt
from . import windows_x11 as wx
from .windows_strip_qt import WindowStrip, hub, slim

ENV = 'GRAPHITE_DOCK'
ALL_DESKTOPS = 0xFFFFFFFF
PropModeReplace = 0
DOCK_TYPE = '_NET_WM_WINDOW_TYPE_DOCK'


def wanted(environ=None, platform=None):
    """(stand, why not): whether the dock should stand here."""
    environ = os.environ if environ is None else environ
    said = str(environ.get(ENV, '')).strip().lower()
    if said in ('0', 'off', 'no'):return False, 'The app strip stays in Graphite\'s window: GRAPHITE_DOCK is off.'
    if said not in ('1', 'on', 'yes') and environ.get('ARC_LEDGER_XSESSION') != '1':
        return False, ('The app strip stays in Graphite\'s window: Graphite was started inside another desktop, whose own '
                       'panel keeps the apps reachable.')
    platform = platform if platform is not None else (QGuiApplication.platformName() if QGuiApplication.instance() else '')
    if platform != 'xcb':
        return False, ('The app strip stays in Graphite\'s window: Graphite\'s window is not on an X display here (it is drawn %s).'
                       % ('offscreen' if platform == 'offscreen' else 'by ' + (platform or 'no window system')))
    reason = wx.why_not(environ)
    if reason:return False, 'The app strip stays in Graphite\'s window: ' + reason + '.'
    return True, ''


# ---- the X properties, through ctypes ----------------------------------------------------------------------------------------
def _declare(lib):
    c_void_p, c_ulong, c_int = ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int
    sig = {'XChangeProperty': ([c_void_p, c_ulong, c_ulong, c_ulong, c_int, c_int, c_void_p, c_int], c_int),
           'XMapWindow': ([c_void_p, c_ulong], c_int), 'XUnmapWindow': ([c_void_p, c_ulong], c_int)}
    for name, (args, result) in sig.items():
        f = getattr(lib, name);f.argtypes = args;f.restype = result
    return lib


def _put(xb, window, name, kind, values):
    data = (ctypes.c_long * len(values))(*[int(v) for v in values])
    xb.x.XChangeProperty(xb.dpy, int(window), xb.atom(name), int(kind), 32, PropModeReplace, ctypes.cast(data, ctypes.c_void_p), len(values))


def strut_values(x, y, width, height):
    """(_NET_WM_STRUT, _NET_WM_STRUT_PARTIAL) for a band across the top of a screen at (x, y) of `width`, `height` tall, in
    the root window's pixels."""
    top = y + height
    return [0, 0, top, 0], [0, 0, top, 0, 0, 0, 0, 0, x, x + width - 1, 0, 0]


def mark_dock(window, rect, display=None):
    """Write the dock's type, its desktop (all) and its strut on X window `window` for `rect` (x, y, w, h in the root's
    pixels), through Graphite's own X connection; read them back. Returns dict(ok, type, strut, partial, why)."""
    try:
        xb = wx.XlibBackend(display)
    except wx.Unavailable as exc:
        return dict(ok=False, why=str(exc), type=None, strut=None, partial=None)
    try:
        _declare(xb.x)
        strut, partial = strut_values(*rect)
        with xb.calls():
            _put(xb, window, '_NET_WM_WINDOW_TYPE', wx.XA_ATOM, [xb.atom(DOCK_TYPE)])
            _put(xb, window, '_NET_WM_DESKTOP', wx.XA_CARDINAL, [ALL_DESKTOPS])
            _put(xb, window, '_NET_WM_STRUT', wx.XA_CARDINAL, strut)
            _put(xb, window, '_NET_WM_STRUT_PARTIAL', wx.XA_CARDINAL, partial)
        return read_marks(window, xb)
    finally:
        xb.close_display()


def read_marks(window, xb=None, display=None):
    """What the dock's X window says it is, read from the X server: its type, its strut, its desktop."""
    own = xb is None
    if own:
        try:xb = wx.XlibBackend(display)
        except wx.Unavailable as exc:return dict(ok=False, why=str(exc), type=None, strut=None, partial=None)
    try:
        with xb.calls():
            types = [xb.atom_name(t) for t in xb.prop(window, '_NET_WM_WINDOW_TYPE', wx.XA_ATOM) or []]
            strut = [int(v) for v in xb.prop(window, '_NET_WM_STRUT', wx.XA_CARDINAL) or []]
            partial = [int(v) for v in xb.prop(window, '_NET_WM_STRUT_PARTIAL', wx.XA_CARDINAL) or []]
            desktop = [int(v) & 0xFFFFFFFF for v in xb.prop(window, '_NET_WM_DESKTOP', wx.XA_CARDINAL) or []]
        ok = DOCK_TYPE in types and len(partial) == 12 and partial[2] > 0
        return dict(ok=ok, type=types[0] if types else None, types=types, strut=strut, partial=partial,
                    desktop=desktop[0] if desktop else None, why='' if ok else 'the X server does not show the dock\'s marks')
    finally:
        if own:xb.close_display()


def remap(window, display=None):
    """Unmap and map the window again, so a window manager that read its type before reads it again."""
    try:xb = wx.XlibBackend(display)
    except wx.Unavailable:return False
    try:
        _declare(xb.x)
        with xb.calls():
            xb.x.XUnmapWindow(xb.dpy, int(window));xb.x.XSync(xb.dpy, 0);xb.x.XMapWindow(xb.dpy, int(window))
        return True
    finally:
        xb.close_display()


# ---- the window ----------------------------------------------------------------------------------------------------------------
class DockStrip(WindowStrip):
    """S3's strip, standing in the dock: laid out by the dock instead of the head."""
    in_dock = True

    def __init__(self, host, dock, parent):
        self.dock = dock
        super().__init__(host, parent)

    def relayout(self):
        QTimer.singleShot(0, self.dock.arrange)

    def show_snapshot(self, snap):
        super().show_snapshot(snap)
        if snap is not None:self.dock.follow(snap)


class GraphiteEntry(QAbstractButton):
    """"Graphite": the mark and the word; ▸ and a rule under it while Graphite's window is the active one."""

    def __init__(self, dock):
        super().__init__(dock);self.dock = dock;self.active = False
        self.setText('Graphite');self.setCursor(Qt.PointingHandCursor);self.setFocusPolicy(Qt.NoFocus);self.setAttribute(Qt.WA_Hover)
        self.setAccessibleName('Graphite: bring Graphite\'s window forward')
        self.setToolTip('Graphite\nPress to bring Graphite\'s window forward.')

    def natural(self, h):
        fm = QFontMetrics(self.font())
        return h + fm.horizontalAdvance('▸ Graphite') + 24

    def sizeHint(self):
        return QSize(self.natural(30), 30)

    def paintEvent(self, event):
        from .graphite_brand import mark_icon
        p = QPainter(self);w, h = self.width(), self.height()
        if self.isDown():p.fillRect(self.rect(), QColor(bt.LINE))
        elif self.underMouse():p.fillRect(self.rect(), QColor(bt.RAISED))
        x = 8;fm = QFontMetrics(self.font())
        if self.active:
            p.setPen(QColor(bt.TEXT));p.drawText(QRect(x, 0, fm.horizontalAdvance('▸ '), h - 2), Qt.AlignLeft | Qt.AlignVCenter, '▸')
            x += fm.horizontalAdvance('▸ ')
        px = max(14, h - 12)
        mark_icon(px).paint(p, QRect(x, (h - px) // 2, px, px));x += px + 6
        p.setPen(QColor(bt.TEXT if self.active or self.underMouse() else bt.QUIET))
        p.drawText(QRect(x, 0, w - x, h - 2), Qt.AlignLeft | Qt.AlignVCenter, 'Graphite')
        if self.active:p.fillRect(0, h - 2, w, 2, QColor(bt.FOCUS))
        p.fillRect(w - 1, round(h * 0.22), 1, round(h * 0.56), QColor(bt.LINE_MID))
        p.end()


class Dock(QWidget):
    """The slim window of the dock type across the top of the screen."""

    def __init__(self, host):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus | Qt.WindowStaysOnTopHint)
        self.host = host;self.marks = {};self.last = None;self.standing = False;self.why = ''
        self.setObjectName('GraphiteDock');self.setWindowTitle('Graphite · app windows');self.setAccessibleName('Open windows and Graphite')
        self.setAttribute(Qt.WA_X11NetWmWindowTypeDock, True);self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_X11DoNotAcceptFocus, True);self.setFocusPolicy(Qt.NoFocus)
        self.entry = GraphiteEntry(self);self.entry.clicked.connect(self.bring_graphite)
        self.box = QWidget(self);self.strip = DockStrip(host, self, self.box)
        self.quiet = QLabel(self);self.quiet.setTextFormat(Qt.PlainText)
        host.installEventFilter(self)

    # -- standing
    def band(self):
        """(the screen's rect in logical pixels, the dock's height, the device pixel ratio)."""
        screen = self.host.screen() or QGuiApplication.primaryScreen()
        scale = getattr(getattr(self.host, 'desk', None), 'scale', 1.0) or 1.0
        return screen.geometry(), slim(scale), screen.devicePixelRatio()

    def stand(self):
        """Mark the dock's X window, show it, read its marks back. True when it stands as a dock."""
        g, h, dpr = self.band()
        self.setGeometry(g.x(), g.y(), g.width(), h);self.setFixedSize(g.width(), h)
        window = int(self.winId())
        rect = (round(g.x() * dpr), round(g.y() * dpr), round(g.width() * dpr), round(h * dpr))
        self.marks = mark_dock(window, rect)
        self.show();self.move(g.x(), g.y())
        QApplication.processEvents()
        self.marks = read_marks(window)
        if self.marks.get('ok'):
            self.standing, self.why = True, ''
        elif self.marks.get('type') != DOCK_TYPE and not self.marks.get('why', '').startswith(wx.NO_LIST):
            mark_dock(window, rect);remap(window);QApplication.processEvents()      # Qt wrote another type at the map: say it again
            self.marks = read_marks(window);self.standing = bool(self.marks.get('ok'))
            self.why = '' if self.standing else self.marks.get('why', 'the dock could not be marked')
        else:
            self.standing, self.why = False, self.marks.get('why', 'the dock could not be marked')
        self.arrange();self.strip.begin()
        screen = self.host.screen() or QGuiApplication.primaryScreen()
        try:screen.geometryChanged.connect(lambda *_: QTimer.singleShot(0, self.again))
        except (RuntimeError, AttributeError):pass
        return self.standing

    def again(self):
        """The screen changed: the band and the strut follow it."""
        if not self.isVisible():return
        g, h, dpr = self.band()
        self.setFixedSize(g.width(), h);self.setGeometry(g.x(), g.y(), g.width(), h)
        self.marks = mark_dock(int(self.winId()), (round(g.x() * dpr), round(g.y() * dpr), round(g.width() * dpr), round(h * dpr)))
        self.arrange()

    def carries_strip(self):
        """Whether the dock is the one the owner sees while Graphite's window is in front: it stands, and Graphite's window is
        not full screen (a full-screen window covers the dock while it is active)."""
        try:return self.standing and self.isVisible() and not self.host.isFullScreen()
        except RuntimeError:return False

    def status(self):
        return dict(standing=self.standing, why=self.why, type=self.marks.get('type'), strut=self.marks.get('strut'),
                    partial=self.marks.get('partial'), desktop=self.marks.get('desktop'), carries=self.carries_strip(),
                    geometry=(self.x(), self.y(), self.width(), self.height()))

    # -- the layout
    def arrange(self):
        if getattr(self.host, '_closing', False):return
        from .desk_qt import Desk
        h = self.height();s = min(max(getattr(getattr(self.host, 'desk', None), 'scale', 1.0) or 1.0, 1.0), 1.6)
        self.entry.ensurePolished();ew = self.entry.natural(h)
        self.entry.setGeometry(0, 0, ew, h)
        x0 = ew + round(4 * s);w = max(0, self.width() - x0)
        self.box.setGeometry(x0, 0, w, h)
        d = Desk(width=w, pane=0, workspace=w, band=h, inset=round(8 * s), gap=0, symbol=0, scale=s, left=0, right=w, line=0)
        self.strip.place(d, 0, h if self.strip.wanted else 0)
        words = '' if self.strip.wanted else self.strip.words()
        self.quiet.setText(words);self.quiet.setVisible(bool(words))
        self.quiet.setStyleSheet('QLabel {color:%s;background:transparent;}' % bt.FAINT)
        self.quiet.setGeometry(x0 + round(12 * s), 0, max(0, w - round(24 * s)), h)
        self.update()

    def follow(self, snap):
        """Each reading of the windows: whether Graphite's window is the active one (▸ on the entry)."""
        try:own = int(self.host.winId())
        except RuntimeError:return
        active = bool(snap.get('available')) and int(snap.get('active') or 0) == own
        if active != self.entry.active:self.entry.active = active;self.entry.update()
        if snap.get('active') != getattr(self, '_seen_active', None):      # another window came forward: the dock stays on top of it
            self._seen_active = snap.get('active')                          # (a dock-aware manager keeps it there anyway)
            if self.isVisible():self.raise_()
        if not self.strip.wanted:self.arrange()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(bt.GROUND))
        p.fillRect(0, self.height() - 1, self.width(), 1, QColor(bt.LINE))
        p.end()

    # -- the press
    def bring_graphite(self):
        """Bring Graphite's window forward: Qt raises and activates it, and the window manager is asked as a task list asks
        (_NET_ACTIVE_WINDOW); verified when Graphite's window is the active one."""
        host = self.host
        try:
            if host.isMinimized():host.setWindowState(host.windowState() & ~Qt.WindowMinimized)
            host.show();host.raise_();host.activateWindow()
            window = int(host.winId())
        except RuntimeError:
            return None
        watcher = hub().watcher
        answer = watcher.activate(window, wait=0.5) if watcher.available else dict(asked=True, verified=False, how='Qt only', reason=watcher.reason)
        self.last = dict(answer, at=time.time())
        hub().settle.start()
        return self.last

    def eventFilter(self, obj, event):
        if obj is self.host and event.type() == QEvent.WindowStateChange:
            strip = getattr(self.host, 'window_strip', None)
            if strip is not None:strip.relayout()      # full screen or not: the head's own strip gives way to the dock, or not
        return False


def install(host):
    """The dock, when it should stand here (after the window is shown); host.system_dock is the Dock or None, and
    host.dock_status() says whether it stands and why not."""
    host.system_dock = None
    stand, why = wanted()
    state = dict(standing=False, why=why)
    host.dock_status = lambda: host.system_dock.status() if host.system_dock is not None else dict(state)
    if not stand:return None
    made = []

    def begin():
        if getattr(host, '_closing', False):return
        try:
            dock = Dock(host);made.append(dock)
            if dock.stand():
                host.system_dock = dock
                strip = getattr(host, 'window_strip', None)
                if strip is not None:strip.relayout()
            else:
                state['why'] = 'The app strip stays in Graphite\'s window: the dock could not be made (%s).' % (dock.why or 'no reason given')
                dock.hide();dock.deleteLater()
        except Exception as exc:  # noqa: BLE001 - a dock that cannot stand leaves the strip where S3 put it
            state['why'] = 'The app strip stays in Graphite\'s window: %s.' % (str(exc)[:160] or type(exc).__name__)
            host.system_dock = None

    def gone(*_):
        while made:
            dock = made.pop()
            try:dock.hide();dock.deleteLater()
            except RuntimeError:pass
    QTimer.singleShot(0, begin)
    app = QApplication.instance()
    if app is not None:app.aboutToQuit.connect(gone)
    host.destroyed.connect(gone)
    return True
