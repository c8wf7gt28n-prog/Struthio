"""Graphite 1.0 S3 · The window strip: the program windows that are open, in a slim row directly under the head band.

It is shown only while at least one program window is open. Each entry is the program's icon (the installed app's icon
from the Apps catalogue (S2) when one names it, else the window's own icon, else the program's name in words from its
WM_CLASS) and the window's title cut short. The active window is marked by a shape and a word, never by colour alone: a ▸
before its title and a rule under it, and its tooltip and accessible name say "active"; a minimised window's title stands
in brackets and says "minimised". One press brings a window forward; the right-click offers Bring forward, Minimise and
Close (polite): the program is asked, and may ask to save first; nothing is forced.

Graphite's own windows are never listed among the programs. Graphite's own open dialogs stay reachable: they stand apart
at the strip's right end, after a rule, each with Graphite's mark, and one press brings the dialog forward.

The reading (windows_x11) is one per process (Hub): its X connection's socket wakes it on PropertyNotify, it reads again a
moment later, and a light poll every few seconds is the backstop; the first opening of the display, and every xprop
reading, run off the window's thread. Graphite's window must itself be on X (the xcb platform): drawn offscreen, or with no
X at all, the strip stays hidden and words() says "no window list on this computer" and why. Nothing else changes.
"""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, QRect, QSize, QSocketNotifier, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QAbstractButton, QApplication, QLabel, QMenu, QToolButton, QToolTip, QWidget

from . import boss_theme as bt
from . import windows_x11 as wx

POLL_MS = round(wx.POLL_SECONDS * 1000)   # the light poll: the backstop under PropertyNotify
SETTLE_MS = 120                           # a burst of property changes is read once, this long after the first
ENTRY_MOST, ENTRY_LEAST = 340, 110        # an entry's width at 14 pt: at most, and the least before the rest fold into ⋯
CAPTION = 'Windows'
CLOSE_WORDS = 'Close (polite)'
CLOSE_TIP = 'Asks the app to close its window. It may ask you to save first; nothing is forced.'


def slim(scale):
    """The strip's height at the interface scale: a slim row, about half the head band."""
    from .desk_qt import scaled
    return max(24, scaled(30, scale))


def installed_app(klass, instance):
    """The installed app (Apps, S2's apps_catalog) that this window's WM_CLASS names: (name, icon file) or None. Guarded: with
    no catalogue here, the window's own icon or the program's words stand in."""
    try:
        from . import apps_catalog
        catalog = apps_catalog.scan()
    except Exception:  # noqa: BLE001 - S2 absent or a catalogue that cannot be read: the words stand in
        return None
    keys = {str(k).casefold() for k in (klass, instance) if k}
    if not keys:return None

    def stem(app):
        ident = str(getattr(app, 'id', '') or '')
        return (ident[:-8] if ident.endswith('.desktop') else ident).casefold()

    def program(app):
        try:return Path(app.exec_program()).name.casefold()
        except Exception:  # noqa: BLE001
            return ''

    apps = list(getattr(catalog, 'apps', {}).values())
    tests = (lambda a: str(getattr(a, 'wm_class', '') or '').casefold() in keys, lambda a: stem(a) in keys,
             lambda a: stem(a).rsplit('.', 1)[-1] in keys, lambda a: program(a) in keys)
    for test in tests:
        for app in apps:
            try:
                if test(app):
                    try:path = apps_catalog.icon_path(getattr(app, 'icon', ''), 32)
                    except Exception:  # noqa: BLE001
                        path = None
                    return str(getattr(app, 'name', '') or ''), path
            except Exception:  # noqa: BLE001
                continue
    return None


class Hub(QObject):
    """The one reading of the open windows for this process: the X connection's socket, the settle and poll timers, the
    threads that open the display and read through xprop. Every strip listens to `read`."""
    read = Signal(object)
    _done = Signal(object)
    _opened = Signal()

    def __init__(self):
        super().__init__(QApplication.instance())
        self.watcher = wx.shared();self.state = 'new';self.reason = '';self.last = None;self.notifier = None;self.busy = False
        self.poll = QTimer(self);self.poll.setInterval(POLL_MS);self.poll.timeout.connect(self.refresh)
        self.settle = QTimer(self);self.settle.setSingleShot(True);self.settle.setInterval(SETTLE_MS);self.settle.timeout.connect(self.refresh)
        self._done.connect(self.deliver);self._opened.connect(self.opened)

    def ensure(self):
        """Start reading once: only when Graphite's own window is on X; the display is opened off the window's thread."""
        if self.state != 'new':return
        platform = QApplication.platformName() if QApplication.instance() is not None else ''
        reason = wx.why_not()
        if reason is None and platform != 'xcb':
            reason = wx.NO_LIST + ": the computer's window is not on the X display here (it is drawn %s)" % (
                'offscreen' if platform == 'offscreen' else 'by ' + (platform or 'no window system'))
        if reason:
            self.state = 'none';self.reason = reason;return
        self.state = 'opening'
        threading.Thread(target=self._open, name='graphite-windows-open', daemon=True).start()

    def _open(self):
        try:self.watcher.start()
        finally:self._opened.emit()

    def opened(self):
        if not self.watcher.available:
            self.state = 'none';self.reason = self.watcher.reason or wx.NO_LIST;self.deliver(self.watcher.snapshot());return
        self.state = 'open'
        try:fd = self.watcher.fileno()
        except Exception:  # noqa: BLE001 - no socket to watch: the poll alone
            fd = None
        if fd is not None:
            self.notifier = QSocketNotifier(fd, QSocketNotifier.Read, self);self.notifier.activated.connect(self.wake)
        self.poll.start();self.refresh()

    def wake(self, *_):
        if self.watcher.pending():self.settle.start()

    def own_windows(self):
        """The X ids of Graphite's own top-level windows (those already made; asking never makes one)."""
        out = set()
        for w in QApplication.topLevelWidgets():
            try:
                ident = int(w.internalWinId() or 0)
                if ident:out.add(ident)
            except (RuntimeError, TypeError, ValueError):
                continue
        return out

    def refresh(self):
        """Read now (on this thread with libX11; on a thread of its own with xprop) and tell every strip."""
        if self.state != 'open':
            if self.state == 'new':self.ensure()
            return self.last
        self.watcher.own_windows = self.own_windows()
        backend = self.watcher.backend
        if backend is not None and getattr(backend, 'blocking', False):
            if not self.busy:
                self.busy = True
                threading.Thread(target=lambda: self._done.emit(self.watcher.refresh()), name='graphite-windows-read', daemon=True).start()
            return self.last
        snap = self.watcher.refresh()
        if self.watcher.pending():self.settle.start()      # what arrived while reading, and was not read yet
        self.deliver(snap)
        return snap

    def deliver(self, snap):
        self.busy = False;self.last = snap
        if snap is not None and not snap.get('available') and snap.get('reason'):self.reason = snap['reason']
        self.read.emit(snap)


_HUB = []


def hub():
    """The process's one Hub, made again for a new application."""
    try:fresh = not _HUB or _HUB[0].parent() is not QApplication.instance()
    except RuntimeError:fresh = True      # the application it belonged to is gone
    if fresh:_HUB[:] = [Hub()]
    return _HUB[0]


class Entry(QAbstractButton):
    """One window in the strip, drawn here so its width is exact: the program's icon (or, with no icon, the program's
    words from WM_CLASS in the quiet ink, a letter tile when the entry is narrow), then the title cut short at the right;
    the active one with a ▸ before it, its words in the brighter ink and a rule under it; a minimised one in brackets."""

    def __init__(self, strip):
        super().__init__(strip);self.strip = strip;self.row = None;self.target = None
        self.icon_ = None;self.active = False;self.minimised = False;self.icon_px = 16;self.pad = 6;self.shown = '';self.tag = ''
        self.setObjectName('WindowEntry');self.setCursor(Qt.PointingHandCursor);self.setFocusPolicy(Qt.TabFocus)
        self.setAttribute(Qt.WA_Hover)

    def face(self, text, icon, active, minimised, icon_px, pad, tag=''):
        """The entry's words and marks; its letters are the look's own (the chrome's style sheet decides them, as for every
        word in the head), so they are measured as they will be drawn."""
        self.ensurePolished()
        self.setText(text);self.icon_ = icon;self.active = bool(active);self.minimised = bool(minimised);self.tag = '' if icon is not None else tag
        self.icon_px = icon_px;self.pad = pad;self.update()

    def ink_font(self):
        font = QFont(self.font())
        if self.active:font.setWeight(QFont.DemiBold)
        return font

    def dressed(self, inner):
        return '(%s)' % inner if self.minimised else inner

    def mark_width(self, fm):
        return fm.horizontalAdvance('▸ ') if self.active else 0

    def natural(self):
        """The width that shows the whole title."""
        fm = QFontMetrics(self.ink_font())
        lead = self.icon_px + self.pad if self.icon_ is not None else (QFontMetrics(self.font()).horizontalAdvance(self.tag) + self.pad if self.tag else 0)
        return 2 * self.pad + self.mark_width(fm) + lead + fm.horizontalAdvance(self.dressed(self.text())) + 2

    def sizeHint(self):
        return QSize(self.natural(), max(20, self.icon_px + 8))

    def paintEvent(self, event):
        p = QPainter(self);w, h = self.width(), self.height()
        if self.isDown():p.fillRect(self.rect(), QColor(bt.LINE))
        elif self.underMouse():p.fillRect(self.rect(), QColor(bt.RAISED))
        x = self.pad;lead = ''
        font = self.ink_font();fm = QFontMetrics(font)
        if self.active:      # the shape that says "active" before everything else (with the rule under it, and the word in its tooltip)
            p.setFont(font);p.setPen(QColor(bt.TEXT));p.drawText(QRect(x, 0, self.mark_width(fm), h - 2), Qt.AlignLeft | Qt.AlignVCenter, '▸')
            x += self.mark_width(fm);lead = '▸ '
        if self.icon_ is not None:
            self.icon_.paint(p, QRect(x, (h - self.icon_px) // 2, self.icon_px, self.icon_px));x += self.icon_px + self.pad
        elif self.tag:      # the program's words from WM_CLASS stand where its icon would; a letter tile when room is short
            quiet = QFontMetrics(self.font());tw = quiet.horizontalAdvance(self.tag)
            p.setFont(self.font());p.setPen(QColor(bt.FAINT))
            if w - 2 * self.pad - tw - self.pad >= min(fm.horizontalAdvance(self.dressed(self.text())), 4 * self.icon_px):
                p.drawText(QRect(x, 0, tw, h - 2), Qt.AlignLeft | Qt.AlignVCenter, self.tag);x += tw + self.pad;lead += self.tag + ' · '
            else:
                box = QRect(x, (h - self.icon_px) // 2, self.icon_px, self.icon_px)
                p.setPen(QColor(bt.LINE_MID));p.drawRoundedRect(box.adjusted(0, 0, -1, -1), 3, 3)
                p.setPen(QColor(bt.QUIET));p.drawText(box, Qt.AlignCenter, self.tag[:1].upper());x += self.icon_px + self.pad
                lead += '[%s] ' % self.tag[:1].upper()
        p.setFont(font)
        room = max(8, w - x - self.pad)
        frame = fm.horizontalAdvance(self.dressed(''))
        drawn = self.dressed(fm.elidedText(self.text(), Qt.ElideRight, max(4, room - frame)))
        self.shown = lead + drawn
        ink = bt.TEXT if self.active or self.underMouse() else (bt.FAINT if self.minimised else bt.QUIET)
        p.setPen(QColor(ink));p.drawText(QRect(x, 0, room, h - 2), Qt.AlignLeft | Qt.AlignVCenter, drawn)
        if self.active:p.fillRect(0, h - 2, w, 2, QColor(bt.FOCUS))      # the rule under the active one (with the ▸ and the word)
        if self.hasFocus():
            p.setPen(QColor(bt.LINE_STRONG));p.drawRect(0, 0, w - 1, h - 3)
        p.end()


class WindowStrip(QWidget):
    """The slim row of open program windows under the head band (TopBar.place lays it; desk_qt.apply gives the head its
    height while it is shown)."""

    def __init__(self, host, parent=None):
        super().__init__(parent);self.host = host
        self.setObjectName('WindowStrip');self.setProperty('paperFunctionalInk', True);self.setAccessibleName('Open windows')
        self.programs, self.dialogs, self.buttons, self.signature = [], [], {}, None
        self.wanted = False;self.scale = 1.0;self.desk = None;self.snap = None
        self.caption = QLabel(CAPTION, self);self.caption.setObjectName('WindowCaption')
        self.more = QToolButton(self);self.more.setObjectName('WindowMore');self.more.setPopupMode(QToolButton.InstantPopup)
        self.more.setMenu(QMenu(self.more));self.more.menu().aboutToShow.connect(self.fill_more);self.more.hide();self.folded = []
        self.more.setAccessibleName('More windows')
        self.hide()
        self.hub = hub();self.hub.read.connect(self.show_snapshot)
        QTimer.singleShot(0, self.begin)

    # -- the reading
    def begin(self):
        if getattr(self.host, '_closing', False):return
        self.hub.ensure()
        if self.hub.last is not None:self.show_snapshot(self.hub.last)
        elif self.hub.state == 'open':self.hub.refresh()

    def refresh(self):
        """Read the windows now (the smoke script's and a caller's way to not wait for the poll)."""
        return self.hub.refresh()

    def words(self):
        """The strip in words: the reason there is no list, or what is open and which is active."""
        if self.hub.state == 'none' or (self.snap is not None and not self.snap.get('available')):
            return self.hub.reason or wx.NO_LIST
        if self.hub.state in ('new', 'opening'):return 'the window list is being read'
        if not self.programs:return 'no app windows are open'
        active = next((r for r in self.programs if r['active']), None)
        names = '; '.join('%s (%s)' % (r['title'] or r['program'], r['program']) for r in self.programs)
        return '%d app window%s open: %s%s' % (len(self.programs), '' if len(self.programs) == 1 else 's', names,
                                                  ('; active: ' + (active['title'] or active['program'])) if active else '')

    def graphite_dialogs(self):
        """Graphite's own open windows other than the main one (dialogs, a window of its own), so they stay reachable."""
        out = []
        for w in QApplication.topLevelWidgets():
            try:
                if w is self.host or w is self.window() or not w.isVisible() or not w.isWindow():continue
                kind = w.windowType()
                if kind not in (Qt.Dialog, Qt.Window, Qt.Sheet):continue
                if w.testAttribute(Qt.WA_DontShowOnScreen) or w.testAttribute(Qt.WA_ShowWithoutActivating):continue
                if kind == Qt.Window and w.windowFlags() & Qt.FramelessWindowHint:continue      # an overlay, not a window to reach
                out.append(w)
            except RuntimeError:
                continue
        return out

    def show_snapshot(self, snap):
        if snap is None or getattr(self.host, '_closing', False):return
        self.snap = snap
        self.programs = [r for r in snap.get('windows', []) if r['listed'] and not r['graphite']] if snap.get('available') else []
        self.dialogs = self.graphite_dialogs() if self.programs else []
        want = bool(self.programs)
        icons = self.__dict__.get('_own_icons')
        if icons:
            listed = {r['window'] for r in self.programs}
            for gone in [w for w in icons if w not in listed]:icons.pop(gone, None)
        signature = (tuple((r['window'], r['title'], r['active'], r['minimised'], r['program'], r['dialog']) for r in self.programs),
                     tuple((id(w), w.windowTitle()) for w in self.dialogs))
        if signature != self.signature:
            self.signature = signature
            if self.isVisible():self.lay_out()
        if want != self.wanted:
            self.wanted = want;self.relayout()

    def relayout(self):
        """The head's height changes with the strip: the desk is laid out again (TypeBar.align, or desk_qt.apply)."""
        def again():
            host = self.host
            if getattr(host, '_closing', False):return
            try:
                bar = getattr(host, 'type_bar', None)
                if bar is not None and hasattr(bar, 'align'):bar.align()
                elif getattr(host, 'desk', None) is not None:
                    from .desk_qt import apply
                    apply(host)
            except Exception:  # noqa: BLE001 - a strip that cannot make room stays out of sight
                self.setVisible(False)
        QTimer.singleShot(0, again)

    # -- the layout (called by TopBar.place)
    def room(self, scale):
        dock = getattr(self.host, 'system_dock', None)  # 1.0 S5: the dock (system_dock_qt) carries the strip while it is the one in sight
        if dock is not None and not getattr(self, 'in_dock', False) and dock.carries_strip():return 0  # 1.0 S5
        return slim(scale) if self.wanted else 0

    def place(self, d, y, height):
        self.desk = d;self.scale = d.scale
        if not height or not self.wanted:
            self.hide();return
        self.setGeometry(0, y, d.width, height);self.show();self.raise_();self.lay_out()

    def label(self, row):
        """The entry's words: the title, or the program's name for a window with none."""
        return row['title'] or row['program']

    def lay_out(self):
        d = self.desk
        if d is None or not self.wanted:return
        from .desk_qt import edge
        from .graphite_brand import mark_icon
        s = min(self.scale, 1.6);h = self.height();self.ensurePolished();fm = QFontMetrics(self.font())
        gap = round(4 * s);pad = round(7 * s);icon_px = max(14, round(16 * s))
        # The caption over the left column; the entries from the middle column's left edge, as the menus above them (from
        # the inset when they are many).
        self.caption.setStyleSheet('QLabel {color:%s;background:transparent;}' % bt.FAINT);self.caption.ensurePolished()
        slot = d.left + edge(d.scale) - d.inset - gap
        x1 = d.width - d.inset
        crowded = len(self.programs) * (round(ENTRY_LEAST * s) + gap) > x1 - (d.left + edge(d.scale))
        self.caption.setGeometry(d.inset, 0, max(0, slot), h)
        self.caption.setVisible(not crowded and slot >= self.caption.fontMetrics().horizontalAdvance(CAPTION) + 2)
        x0 = d.left + edge(d.scale) if self.caption.isVisible() or not crowded else d.inset
        keep = set()
        # Graphite's own dialogs at the right end, apart.
        for w in reversed(self.dialogs):
            key = ('own', id(w));keep.add(key);b = self.entry(key);b.target = w;b.row = None
            title = w.windowTitle() or 'Kas'
            b.face(title, mark_icon(icon_px), False, w.isMinimized(), icon_px, pad)
            width = min(round(ENTRY_MOST * s * 0.8), b.natural())
            b.setToolTip("Kas's own window: %s\nPress to bring it forward." % title);b.setAccessibleName("The computer's window " + title)
            x1 -= width;b.setGeometry(x1, 0, width, h);b.show();x1 -= gap
        self.rule_x = x1 if self.dialogs else None
        if self.dialogs:x1 -= gap * 2
        # The program windows, in the order they were first seen (tiles do not jump).
        rows = list(self.programs);room = max(0, x1 - x0)
        least, most = round(ENTRY_LEAST * s), round(ENTRY_MOST * s)
        more_w = fm.horizontalAdvance('⋯ 99 more') + 2 * pad
        shown = rows
        if rows and len(rows) * (least + gap) > room:
            shown = rows[:max(0, (room - more_w - gap) // (least + gap))]
        self.folded = rows[len(shown):]
        each = min(most, (room - (more_w + gap if self.folded else 0)) // max(1, len(shown)) - gap) if shown else 0
        x = x0
        for row in shown:
            key = ('x', row['window']);keep.add(key);b = self.entry(key);b.row = row;b.target = None
            icon, name = self.icon_for(row, icon_px)
            b.face(self.label(dict(row, program=name)), icon, row['active'], row['minimised'], icon_px, pad, tag=name[:24])
            words = [w for w, on in (('active', row['active']), ('minimised', row['minimised']), ('a dialog', row['dialog'])) if on]
            b.setToolTip('%s · %s%s\nPress to bring it forward; right-click to minimise or close it.' % (
                name, row['title'] or '(no title)', (' · ' + ', '.join(words)) if words else ''))
            b.setAccessibleName(', '.join([row['title'] or name, name] + words))
            width = max(min(least, b.natural()), min(each, b.natural()))
            b.setGeometry(x, 0, width, h);b.show();b.update();x += width + gap
        if self.folded:
            self.more.setText('⋯ %d more' % len(self.folded))
            self.more.setStyleSheet('QToolButton {color:%s;background:transparent;border:0;padding:0 %dpx;} QToolButton::menu-indicator {image:none;width:0;}'
                                    ' QToolButton:hover {color:%s;background:%s;}' % (bt.QUIET, pad, bt.TEXT, bt.RAISED))
            self.more.setToolTip('%d more windows: press to choose one' % len(self.folded))
            self.more.setGeometry(x, 0, more_w, h);self.more.show()
        else:self.more.hide()
        for key in [k for k in self.buttons if k not in keep]:
            b = self.buttons.pop(key);b.hide();b.deleteLater()
        self.update()

    def entry(self, key):
        b = self.buttons.get(key)
        if b is None:
            b = Entry(self)
            b.clicked.connect(lambda checked=False, b=b: self.pressed(b))
            b.setContextMenuPolicy(Qt.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda pos, b=b: self.menu_for(b, pos))
            self.buttons[key] = b
        return b

    def icon_for(self, row, px):
        """(QIcon or None, the program's name): the installed app's icon and name (S2), else the window's own icon
        (_NET_WM_ICON), else no icon and the program's words from WM_CLASS."""
        cache = self.__dict__.setdefault('_apps', {})
        key = (row['klass'], row['instance'])
        if key not in cache:cache[key] = installed_app(*key)
        found = cache[key];name = (found[0] if found and found[0] else row['program'])
        if found and found[1]:
            icon = QIcon(found[1])
            if not icon.isNull():return icon, name
        own = self.__dict__.setdefault('_own_icons', {})
        if row['window'] not in own:
            data = self.hub.watcher.icon(row['window'])
            own[row['window']] = None
            if data:
                w, h, raw = data
                image = QImage(raw, w, h, QImage.Format_ARGB32).copy()
                if not image.isNull():own[row['window']] = QIcon(QPixmap.fromImage(image))
        return own[row['window']], name

    # -- acting (the owner's press)
    def pressed(self, b):
        if b.target is not None:self.bring_own(b.target)
        elif b.row is not None:self.act('activate', b.row, b)

    def bring_own(self, w):
        try:
            if w.isMinimized():w.showNormal()
            w.raise_();w.activateWindow()
        except RuntimeError:
            pass

    def act(self, kind, row, anchor=None):
        watcher = self.hub.watcher
        answer = getattr(watcher, kind)(row['window'])
        if not answer.get('asked') and answer.get('reason') and anchor is not None:
            QToolTip.showText(anchor.mapToGlobal(anchor.rect().bottomLeft()), answer['reason'], anchor)
        self.hub.settle.start()
        return answer

    def menu_for(self, b, pos):
        menu = QMenu(self);menu.setToolTipsVisible(True)
        if b.target is not None:
            menu.addAction('Bring forward').triggered.connect(lambda checked=False: self.bring_own(b.target))
        elif b.row is not None:
            row = b.row
            head = menu.addAction('%s · %s' % (self.icon_for(row, 16)[1], row['title'] or '(no title)'));head.setEnabled(False)
            menu.addSeparator()
            menu.addAction('Bring forward').triggered.connect(lambda checked=False: self.act('activate', row, b))
            m = menu.addAction('Minimise');m.setEnabled(not row['minimised']);m.triggered.connect(lambda checked=False: self.act('minimise', row, b))
            c = menu.addAction(CLOSE_WORDS);c.setToolTip(CLOSE_TIP);c.triggered.connect(lambda checked=False: self.act('close', row, b))
        else:return
        menu.exec(b.mapToGlobal(pos))

    def fill_more(self):
        menu = self.more.menu();menu.clear()
        for row in self.folded:
            words = ('▸ ' if row['active'] else '') + (row['title'] or row['program']) + (' (minimised)' if row['minimised'] else '')
            menu.addAction(words).triggered.connect(lambda checked=False, row=row: self.act('activate', row, self.more))

    def paintEvent(self, event):
        p = QPainter(self)
        ground = QColor(bt.GROUND);ground.setAlphaF(0.72);p.fillRect(self.rect(), ground)
        p.fillRect(0, self.height() - 1, self.width(), 1, QColor(bt.LINE))
        if getattr(self, 'rule_x', None) is not None:
            p.fillRect(self.rule_x, round(self.height() * 0.22), 1, round(self.height() * 0.56), QColor(bt.LINE_MID))
        p.end()


def install(host, top):
    """The strip in the head (TopBar), below the band; host.window_strip for callers and the smoke script."""
    strip = WindowStrip(host, top);top.window_strip = strip;host.window_strip = strip
    return strip
