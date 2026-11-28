"""Graphite 1.1 B5 · A quieter bar: network, sound and power are one Quick Settings button, as Windows 11's.

PLAN_1.1.md, B5. B1's tray gave network, sound and power a button each, and B4 put the meters beside them; at 1366x768 they
took room the app windows want. Here the three are one button on the bar: their three glyphs side by side (each state its
own shape, bar_qt.paint_glyph), every word in its tip and its accessible name. One press opens one panel above it with the
three Machine sections stacked (machine_room_qt's own pages, compact, each with its way to the whole page: nothing the
flyouts did is lost) and, once the foot has folded (foot_fold_qt), the meters as a fourth section: CPU, GPU, RAM, TXT and
NET, each row the door its meter was (meter_cards). A second press, Esc or a press elsewhere closes it.

The readings are B1's (machine_real, off the window's thread, every TRAY_SECONDS; kept in host._machine_real for the Machine
page); nothing changes but by the owner's press on a section's own controls, each change DONE only when read back.

Graphite's head, while the bar stands: Apps and its plus leave it (Start does that job; "Add an app to the list" is beside
Start's Apps heading), and the menus start at the head's left edge, as a Windows app's; the equalizer stands after them.
Without the bar the head stays as K0 left it.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QPainter
from PySide6.QtWidgets import QFrame, QGridLayout, QPushButton, QScrollArea, QVBoxLayout, QWidget

from . import bar_qt

NAME = 'Quick Settings'
TITLES = {'network': 'Network', 'sound': 'Sound', 'power': 'Power'}
SECTIONS = bar_qt.TRAY + ('meters',)
PANEL_KEY = 'quick'                   # bar.open_key and bar.flyouts' key while the panel is open
METERS_NOTE = 'This computer, now. Each opens its card, as the foot\'s meters did.'


class Reading:
    """One section's reading as the tray holds it: tray_words' word, tip and glyph (B1's TrayItem without a button of its own)."""

    def __init__(self, tray, key):
        self.tray = tray;self.key = key;self.data = None
        self.word, self.tip, self.glyph = bar_qt.tray_words(key, None)

    def show_reading(self, data):
        self.data = data;self.word, self.tip, self.glyph = bar_qt.tray_words(self.key, data)
        self.tray.button.show_words()

    def update(self):
        self.tray.button.update()


class QuickButton(bar_qt.BarButton):
    """The one button: the three glyphs side by side in a fixed width (nothing shifts); its words in the tip and the name."""

    def __init__(self, tray):
        super().__init__(tray, NAME);self.tray = tray
        self.clicked.connect(lambda: tray.open_panel())
        self.show_words()

    def natural(self, h):
        side = round(h * 0.42)
        return 2 * round(h * 0.25) + 3 * side + 2 * round(h * 0.2)

    def words(self):
        """Every section in words, one line each (the tip), and the short form (the accessible name)."""
        items = self.tray.items
        lines = ['%s: %s' % (TITLES[key], items[key].tip.split('\n')[0].split(': ', 1)[-1]) for key in bar_qt.TRAY]
        short = ', '.join('%s %s' % (TITLES[key].lower(), items[key].word) for key in bar_qt.TRAY)
        if self.tray.with_meters:
            try:
                from .foot_fold_qt import meters_words, readings
                lines.append('Meters: ' + meters_words(readings(self.tray.bar.host)))
            except RuntimeError:
                pass
        return lines, short

    def show_words(self):
        lines, short = self.words()
        more = 'network, sound, power and the meters' if self.tray.with_meters else 'network, sound and power'
        self.setToolTip('%s\n%s\nA press opens %s.' % (NAME, '\n'.join(lines), more))
        self.setAccessibleName('%s: %s' % (NAME, short));self.update()

    def event(self, event):
        if event.type() == QEvent.ToolTip:self.show_words()      # the meters' words as they read now
        return super().event(event)

    def paintEvent(self, event):
        c = bar_qt.ink();p = QPainter(self);h = self.height()
        self.ground(p, c, self.tray.bar.open_key == PANEL_KEY)
        side = round(h * 0.42);x = round(h * 0.25);gap = round(h * 0.2)
        for key in bar_qt.TRAY:
            bar_qt.paint_glyph(p, self.tray.items[key].glyph, x, h / 2.0, side, c['text'], c['tertiary']);x += side + gap
        p.end()


class QuickTray(QWidget):
    """The bar's tray slot: the one Quick Settings button. items holds the three readings (B1's tray reads them, read/landed)."""
    with_meters = False      # foot_fold_qt.MetersTray: the meters are its fourth section once the foot has folded
    read = bar_qt.Tray.read
    landed = bar_qt.Tray.landed

    def __init__(self, bar):
        super().__init__(bar);self.bar = bar;self.panel = None
        self.items = {key: Reading(self, key) for key in bar_qt.TRAY}
        self.button = QuickButton(self)
        self.setAccessibleName('The tray: ' + NAME)
        self.timer = QTimer(self);self.timer.setInterval(bar_qt.TRAY_SECONDS * 1000);self.timer.timeout.connect(self.read);self.timer.start()
        QTimer.singleShot(0, self.read)

    def bar_width(self, h):
        return self.button.natural(h)

    def resizeEvent(self, event):
        self.button.setGeometry(0, 0, self.button.natural(self.height()), self.height())

    def gone(self, panel):
        if self.bar.flyouts.get(PANEL_KEY) is panel:self.bar.flyouts.pop(PANEL_KEY, None)
        if self.panel is panel:self.panel = None

    def open_panel(self, key=None):
        """The panel above the button, `key`'s section in sight; a second press on an open one closes it."""
        bar = self.bar
        try:
            if self.panel is not None and self.panel.isVisible():self.panel.close();return None
        except RuntimeError:
            self.panel = None
        for other in list(bar.flyouts.values()):
            try:other.close()
            except RuntimeError:pass
        panel = QuickPanel(self);panel.setAttribute(Qt.WA_DeleteOnClose, True)
        panel.destroyed.connect(lambda *_, panel=panel: self.gone(panel))
        self.panel = panel;bar.flyouts[PANEL_KEY] = panel;bar.open_key = PANEL_KEY;self.button.update()
        panel.open_above(self.button)
        if key in panel.sections:panel.scroll.ensureWidgetVisible(panel.sections[key], 0, 0)
        return panel


def machine_room(host, key):
    """machine_room_qt's page of `key`, made compact for the panel (B1's flyout's own)."""
    from .machine_room_qt import MachineRoom

    class QuickRoom(MachineRoom):
        def draw(self):
            self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)      # the page wraps to the panel's width
            super().draw()
            page = self.scroll.widget()
            if page is not None and page.layout() is not None:
                page.layout().setContentsMargins(16, 10, 16, 4);page.layout().setSpacing(8)
    return QuickRoom(host, key)


class MetersSection(QWidget):
    """The meters as the panel's fourth section: B4's rows, each the door its meter was (meter_cards.open_card, above the
    Quick Settings button)."""

    def __init__(self, panel):
        super().__init__(panel);self.panel = panel;self.host = panel.bar.host
        from .foot_fold_qt import METER_KEYS, DoorWords, readings
        from .machine_room_qt import words
        from .meter_cards import DOORS
        self.keys = METER_KEYS;self.readings = readings
        self.setAccessibleName('Meters')
        box = QVBoxLayout(self);box.setContentsMargins(16, 10, 16, 6);box.setSpacing(6)
        box.addWidget(words('Meters', 'title'));box.addWidget(words(METERS_NOTE, 'quiet'))
        grid = QGridLayout();grid.setHorizontalSpacing(12);grid.setVerticalSpacing(2);box.addLayout(grid)
        self.rows = {};self.doors = DOORS
        for r, key in enumerate(METER_KEYS):
            b = QPushButton(self);b.setObjectName('QuickMeter');b.setCursor(Qt.PointingHandCursor);b.setMinimumWidth(124)
            b.clicked.connect(lambda checked=False, key=key: self.door(key))
            door = DoorWords(DOORS[key], lambda key=key: self.door(key), self);door.setProperty('role', 'quiet');door.setWordWrap(True)
            door.setCursor(Qt.PointingHandCursor);door.setToolTip('Opens: ' + DOORS[key])
            grid.addWidget(b, r, 0);grid.addWidget(door, r, 1);grid.setColumnStretch(1, 1);self.rows[key] = b
        self.show_readings()
        self.timer = QTimer(self);self.timer.setInterval(2000);self.timer.timeout.connect(self.show_readings);self.timer.start()

    def show_readings(self):
        try:read = self.readings(self.host)
        except RuntimeError:return
        for key, b in self.rows.items():
            words = read[key][0];b.setText('%s   %s' % (key, words));b.setAccessibleName('%s %s: %s' % (key, words, self.doors[key]))

    def door(self, key):
        """A meter's card, above the Quick Settings button (the same card as 1.0's meter opened)."""
        anchor = self.panel.tray.button;host = self.host
        self.panel.close()
        from .meter_cards import open_card
        return open_card(host, anchor, key)


class QuickPanel(QFrame):
    """One panel above the button: Network, Sound and Power (each the Machine page's own section and its way to the whole
    page), then the meters when the foot has folded."""

    def __init__(self, tray):
        super().__init__(None, Qt.Popup | Qt.FramelessWindowHint)
        self.tray = tray;self.bar = bar = tray.bar;c = bar_qt.ink()
        self.setObjectName('GraphiteQuickSettings');self.setAccessibleName(NAME + ', from the bar')
        self.setStyleSheet('QFrame#GraphiteQuickSettings {background:%s; border:1px solid %s;}'
                           ' QFrame#QuickRule {background:%s; border:0;}'
                           ' QPushButton#QuickMore {color:%s; background:transparent; border:0; padding:2px 16px 6px 16px; text-align:left;}'
                           ' QPushButton#QuickMore:hover {text-decoration:underline;}'
                           ' QPushButton#QuickMeter {color:%s; background:transparent; border:0; text-align:left; padding:5px 8px;}'
                           ' QPushButton#QuickMeter:hover {background:%s;}'
                           % (c['surface'], c['stroke'], c['hairline'], c['accent_text'], c['text'], c['hover_side']))
        outer = QVBoxLayout(self);outer.setContentsMargins(1, 1, 1, 1);outer.setSpacing(0)
        self.scroll = QScrollArea(self);self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);outer.addWidget(self.scroll)
        body = QWidget();body.setObjectName('QuickBody');body.setStyleSheet('QWidget#QuickBody {background:%s;}' % c['surface'])
        col = QVBoxLayout(body);col.setContentsMargins(0, 0, 0, 0);col.setSpacing(0)
        self.sections = {};self.rooms = {};self.more = {}
        keys = SECTIONS if tray.with_meters else bar_qt.TRAY
        for at, key in enumerate(keys):
            if at:
                rule = QFrame(body);rule.setObjectName('QuickRule');rule.setFixedHeight(1);col.addWidget(rule)
            if key == 'meters':
                section = MetersSection(self)
            else:
                section = QWidget(body);section.setAccessibleName(TITLES[key]);box = QVBoxLayout(section)
                box.setContentsMargins(0, 0, 0, 0);box.setSpacing(0)
                room = machine_room(bar.host, key);self.rooms[key] = room;box.addWidget(room)
                more = QPushButton(bar_qt.MORE_WORDS, section);more.setObjectName('QuickMore');more.setFlat(True)
                more.setCursor(Qt.PointingHandCursor);more.setAccessibleName('%s: %s' % (TITLES[key], bar_qt.MORE_WORDS))
                more.clicked.connect(lambda checked=False, key=key: self.whole_page(key));box.addWidget(more);self.more[key] = more
            self.sections[key] = section;col.addWidget(section)
        col.addStretch(1)
        self.scroll.setWidget(body)

    def whole_page(self, key):
        self.close();return self.bar.open_machine(key)

    def open_above(self, anchor):
        bar = self.bar;width = 460 if bar.height() >= bar_qt.TALL else 440
        screen = (bar.screen() or QGuiApplication.primaryScreen()).geometry()
        top = bar.mapToGlobal(bar.rect().topLeft()).y()
        room_for = max(240, top - screen.top() - 12)      # the panel never reaches above the screen
        whole = 2
        for key, section in self.sections.items():
            if key in self.rooms:
                room = self.rooms[key];page = room.scroll.widget();need = 160
                if page is not None and page.layout() is not None:
                    lay = page.layout()
                    need = lay.heightForWidth(width - 4) if lay.hasHeightForWidth() else lay.sizeHint().height()
                room.setFixedHeight(min(max(120, need + 4), round(room_for * 0.6)))
                whole += room.height() + self.more[key].sizeHint().height() + 1
            else:
                lay = section.layout()
                whole += (lay.heightForWidth(width - 4) if lay.hasHeightForWidth() else section.sizeHint().height()) + 1
        self.setFixedWidth(width);self.scroll.setFixedHeight(min(whole, room_for));self.adjustSize()
        right = anchor.mapToGlobal(anchor.rect().topRight()).x() + 1
        x = max(screen.left(), min(right, screen.right() + 1) - self.width())
        self.move(x, top - self.height() - 6);self.show();self.raise_()
        return self

    def hideEvent(self, event):
        if self.bar.open_key == PANEL_KEY:
            self.bar.open_key = None
            try:self.tray.button.update()
            except RuntimeError:pass
        super().hideEvent(event)


def quick_tray(bar):
    """The bar's own tray (bar_qt.DEFAULTS): Quick Settings."""
    return QuickTray(bar)


# ---- Graphite's head while the bar stands ---------------------------------------------------------------------------------------
def head_free(top):
    """shell2's head: True while the bar stands (Start is there): Apps and its plus leave the head and the menus start at its
    left edge. They are hidden here; the objects stay for their callers."""
    bar = getattr(getattr(top, 'host', None), 'graphite_bar', None)
    try:free = bool(bar is not None and getattr(bar, 'standing', False))
    except RuntimeError:free = False
    if free:
        for widget in (getattr(top, 'programs', None), getattr(top, 'apps_add', None)):
            if widget is not None and widget.isVisible():widget.hide()
    return free


def place_equalizer(top, d, left, right, gap):
    """With the head free, the equalizer stands after the menus (as wide as over the left column, at most), unless the address
    line has the keyboard there."""
    eq = getattr(top, 'equalizer', None)
    if eq is None or getattr(eq, 'in_column', False):return
    h = d.band;tall = max(16, h - 2 * round(4 * min(d.scale, 1.4)))
    x = left + 2 * gap;wide = max(0, min(d.pane - 2 * d.inset, right - x - gap))
    eq.setGeometry(x, (h - tall) // 2, wide, tall);eq.setVisible(wide >= 48 and not top.path.isVisible())


def bar_stood(host):
    """bar_qt.install, once the bar stands: the head is placed again (Apps leaves it, the menus go to its left edge)."""
    top = getattr(getattr(host, 'shell2', None), 'top', None)
    place = getattr(top, 'place', None)
    if callable(place):QTimer.singleShot(0, lambda: place(getattr(host, 'desk', None)))
