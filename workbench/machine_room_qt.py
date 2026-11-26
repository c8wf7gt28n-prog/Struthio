"""Graphite 1.0 S4 · The Machine tab's real rows and their pages in the centre.

The left pane's Machine tab (machine_qt.MachinePage) opens with five rows read from the system's own services
(machine_real): Storage, Power, Network, Sound, Screens, each with its few words ("Storage · 1 drive", "Power · battery
76 %, charging", "Network · not available"). Below them the overview's rows that still mean something: Processor, Memory,
Devices, Installed tools; the overview's disks, mounts and Graphite's folders sit under Storage, its interfaces under
Network. Choosing one of the five opens its page in the centre (MachineRoom, a room tab like This Computer):

  Storage   each removable drive, its filesystems and whether each is mounted; Mount, Open in Files, Unmount, Eject safely.
            "SAFE TO REMOVE" shows only after machine_real.eject read it back.
  Power     each battery (its percent, charging or not, the time left) and the mains; where Lock and Suspend are.
  Network   the state; networking and Wi-Fi on or off; the Wi-Fi networks heard, strongest first; Join (a secured new network
            asks for its password in a field on the page: the words go to NetworkManager in the call, which keeps them;
            the field is emptied at once, Graphite keeps no copy); Disconnect; the wired connections.
  Sound     the volume and mute of the output in use; the outputs, and Use this output.
  Screens   each screen with its modes; Use this mode, Make primary, Turn off or on; Mirror or Extend. After a change:
            "Keep this arrangement?", and it goes back by itself in 15 seconds unless kept.

Each page says where its words come from and when they were read; with its service absent it says "Not available on this
computer" and why. Every change is the owner's press on the page (none is a Kernel operation), runs off the window's
thread, and is said DONE only when machine_real read its effect back; otherwise NOT DONE with the reason. Every state is a
word (MOUNTED, CONNECTED, IN USE, MUTED, PRIMARY, ...), never a colour alone. A page re-reads every few seconds while it is
in front (a drive plugged in shows by itself) and is redrawn only when what it reads changed, never under the owner's
typing or a pending Keep.
"""
from __future__ import annotations

import json
import threading
import time

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QSlider, QVBoxLayout,
                               QWidget)

from . import boss_theme as bt
from . import machine_real as real

ROW_SECONDS = 10       # the Machine tab's five rows re-read this often while the tab shows
PAGE_SECONDS = 3       # a page in front re-reads this often; it is redrawn only when what it reads changed
KEEP_SECONDS = 15      # a change to the screens goes back by itself unless kept
CACHE_SECONDS = 2      # the rows and a page opened together share one reading
SYSTEM_MENU = 'Lock, Suspend, Log out, Restart and Shut down are in the System menu, the symbol at the right of the head.'


def clock(stamp):
    return time.strftime('%H:%M:%S', time.localtime(stamp)) if stamp else 'not read'


# ---- one reading shared by the rows and the pages --------------------------------------------------------------------------
def reading(host, key, fresh=False, keep=False):
    """The section's last reading, read again when it is older than CACHE_SECONDS (fresh: always; keep: never, unless there is
    none yet: a row's words and its tooltip say the same reading)."""
    store = getattr(host, '_machine_real', None)
    if store is None:
        store = {};setattr(host, '_machine_real', store)
    held = store.get(key)
    if held is None:      # the first reading of a section: at once (the Machine tab or its page was just opened)
        held = real.read(key);store[key] = held
    elif fresh or (not keep and time.time() - held['sampled_at'] > CACHE_SECONDS):
        from . import floor      # 1.0 F2: read again off the window's thread (a service may be slow to answer); drawn when it lands
        floor.read_later(('machine', id(host), key), lambda: real.read(key), landed=lambda data: landed(host, key, data))
    return held


def landed(host, key, data):
    """1.0 F2: a section read off the window's thread: kept, and the page that shows it drawn from it (never read again here)."""
    store = getattr(host, '_machine_real', None)
    if store is None or getattr(host, '_closing', False):return
    store[key] = data
    for room in list(getattr(host, '_machine_rooms', ()) or ()):
        try:
            if room.key == key and room.isVisible():room.reload(read=False)
        except RuntimeError:      # a page that has gone
            pass


def digest(data):
    return json.dumps({k: v for k, v in data.items() if k != 'sampled_at'}, sort_keys=True, default=str)


# ---- the Machine tab's rows (MachinePage.build's hooks) -------------------------------------------------------------------
def row_words(data):
    return '%s · %s' % (data['title'], data['short'] or ('not available' if not data['available'] else ''))


def drive_words(drive):
    mounted = sum(1 for v in drive['volumes'] if v['mounted'])
    return '%s · %s' % (drive['name'], ('%d mounted' % mounted) if mounted else 'not mounted')


def tree_rows(page, machine):
    """The five rows first under Machine, with a removable drive's row under Storage. Returns {overview section id: row} for
    the overview sections whose rows now sit under one of them (storage under Storage, connections under Network)."""
    host = page.host;rows = {}
    for key in real.SECTIONS:
        data = reading(host, key)
        item = page.add(machine, key, row_words(data), dict(kind='real', id=key, real=key))
        if key == 'storage' and data['available']:
            for drive in data['drives']:
                page.add(item, 'real:drive:' + drive['id'], drive_words(drive), dict(kind='real_item', id='real:drive:' + drive['id'], real='storage', target=drive['id']))
        rows[key] = item
    page._real_seen = {key: row_words(reading(host, key)) for key in real.SECTIONS}
    page._real_drives = drives_key(reading(host, 'storage'))
    timer = getattr(page, '_real_timer', None)
    if timer is None:
        timer = QTimer(page);timer.setInterval(ROW_SECONDS * 1000);timer.timeout.connect(lambda: refresh_rows(page));timer.start()
        page._real_timer = timer
    return {'storage': rows['storage'], 'connections': rows['network']}


def adopt(rows, section):
    """The real row that takes an overview section's rows (storage, connections), now holding that section too; else None."""
    item = rows.get(section['id'])
    if item is None:return None
    data = dict(item.data(0, Qt.UserRole) or {});data['section'] = section;item.setData(0, Qt.UserRole, data)
    return item


def drives_key(data):
    return tuple((d['id'], drive_words(d)) for d in data.get('drives') or [])


def refresh_rows(page):
    """While the Machine tab shows: the rows' words follow the services; a drive come or gone rebuilds the tree."""
    if getattr(page.host, '_closing', False) or not page.isVisible() or not page.items:return
    seen = getattr(page, '_real_seen', {})
    for key in real.SECTIONS:
        data = reading(page.host, key)
        words = row_words(data);item = page.items.get(key)
        if item is not None and seen.get(key) != words:item.setText(0, words);seen[key] = words
        if item is not None:item.setToolTip(0, page.describe(item.data(0, Qt.UserRole) or {}))
    if drives_key(reading(page.host, 'storage')) != getattr(page, '_real_drives', None):page.build(force=True)


def describe(page, data):
    """A real row's words (its tooltip): what it is, where it was read, when, and why it is not available when it is not."""
    key = data.get('real');held = reading(page.host, key, keep=True) if key else None
    if held is None:return ''
    if data.get('kind') == 'real_item':
        drive = next((d for d in held.get('drives') or [] if d['id'] == data.get('target')), None)
        if drive is None:return 'This drive has gone from udisks2\'s list.'
        lines = ['%s · %s%s' % (drive['name'], drive['bus'].upper() or 'removable', (' · ' + real.size_words(drive['size'])) if drive['size'] else '')]
        for volume in drive['volumes']:
            lines.append(real.volume_words(volume) + ' · ' + (('mounted at ' + ', '.join(volume['mounted'])) if volume['mounted'] else 'locked (encrypted)' if volume['encrypted'] and not volume['can_mount'] else 'not mounted'))
        lines.append('Choose it to open Storage in the centre: Mount, Open in Files, Unmount, Eject safely.')
        return '\n'.join(lines)
    lines = [row_words(held), 'Read from %s at %s.' % (held['source'], clock(held['sampled_at']))]
    if not held['available']:lines.append(held['why'])
    lines.append('Choose it to open %s in the centre.' % held['title'])
    section = data.get('section')
    if section:
        lines += ['', 'Also here, from the overview:', 'Observed ' + clock(section['sampled_at']), 'Sources: ' + ' · '.join(section['sources'])]
        lines += ['%s' % row['label'] for row in section['items'][:8]] + (['and %d more' % (len(section['items']) - 8)] if len(section['items']) > 8 else [])
    return '\n'.join(lines)


def activate(page, data):
    """A real row chosen in the Machine tab: its page in the centre."""
    return show(page.host, data.get('real') or 'storage', data.get('target'))


# ---- the pages ------------------------------------------------------------------------------------------------------------
class Runner(QObject):
    done = Signal(object)


def word(text, tone='quiet'):
    """A state word: the word always, its colour only beside it."""
    colour = {'live': bt.READY, 'wait': bt.AMBER_TEXT, 'stop': bt.STOP, 'quiet': bt.QUIET}.get(tone, bt.QUIET)
    label = QLabel(text.upper());label.setTextFormat(Qt.PlainText)
    label.setStyleSheet('QLabel {color:%s; font-family:"%s"; letter-spacing:1px;}' % (colour, bt.MONO))
    return label


def words(text, role=None, wrap=True):
    label = QLabel(text);label.setTextFormat(Qt.PlainText);label.setWordWrap(wrap)
    if role:label.setProperty('arcRole2', role)
    return label


def press(text, action, tip='', enabled=True):
    from .shell2 import button
    b = button(text, 'tool', tip);b.clicked.connect(action);b.setEnabled(enabled);b.setAccessibleName(text)
    return b


def card():
    frame = QFrame();frame.setObjectName('MachineCard')
    frame.setStyleSheet('QFrame#MachineCard {background:%s; border:1px solid %s; border-radius:6px;}' % (bt.CARD, bt.LINE))
    box = QVBoxLayout(frame);box.setContentsMargins(16, 12, 16, 12);box.setSpacing(8)
    return frame, box


def row(*parts, stretch_at=None):
    line = QHBoxLayout();line.setSpacing(12)
    for i, part in enumerate(parts):
        if part is None:continue
        if isinstance(part, QWidget):line.addWidget(part, 1 if i == stretch_at else 0)
        else:line.addLayout(part)
    if stretch_at is None:line.addStretch(1)
    return line


class MachineRoom(QWidget):
    """One of the five pages in the centre (a room tab): Storage, Power, Network, Sound or Screens."""

    def __init__(self, host, key):
        super().__init__();self.host = host;self.key = key if key in real.SECTIONS else 'storage'
        self.setObjectName('LibraryTab');self.setProperty('ledgerRoom', True);self.setAccessibleName('Machine: ' + self.title())
        self.data = None;self.seen = None;self.busy = None;self.last = None;self.safe = None;self.asking = None;self.keep = None
        self.target = None;self.drawing = False;self.runners = []
        outer = QVBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame);outer.addWidget(self.scroll)
        self.timer = QTimer(self);self.timer.setInterval(PAGE_SECONDS * 1000);self.timer.timeout.connect(self.tick);self.timer.start()
        self.countdown = QTimer(self);self.countdown.setInterval(1000);self.countdown.timeout.connect(self.keep_tick)
        self.reload(force=True)

    def title(self):return real.TITLES[self.key]

    def inspector(self):
        data = self.data or {}
        return self.title(), [(self.title(), data.get('short') or ''), ('Read from', data.get('source', '')), ('Read at', clock(data.get('sampled_at')))]

    # ---------------------------------------------------------------- reading
    def holding(self):
        """Never redraw under the owner's hand: a password being typed, a list open, a change waiting to be kept."""
        if self.keep is not None or self.asking is not None:return True
        focus = self.focusWidget()
        return isinstance(focus, (QLineEdit, QComboBox, QSlider)) and focus.hasFocus()

    def tick(self):
        if getattr(self.host, '_closing', False):self.timer.stop();return
        if not self.isVisible() or self.busy or self.holding():return
        self.reload()

    def reload(self, force=False, read=True):
        rooms = getattr(self.host, '_machine_rooms', None)      # 1.0 F2: the pages a reading made off the window's thread is drawn on
        if rooms is None:
            import weakref
            rooms = weakref.WeakSet();setattr(self.host, '_machine_rooms', rooms)
        rooms.add(self)
        data = reading(self.host, self.key, fresh=read, keep=not read);seen = digest(data)
        if not force and seen == self.seen and self.data is not None:
            self.data = data;self.stamp.setText(self.lead_words());return
        self.data = data;self.seen = seen;self.draw()

    def lead_words(self):
        data = self.data
        return 'Read from %s at %s. Nothing is changed but by your press here.' % (data['source'], clock(data['sampled_at']))

    def focus_on(self, target):
        self.target = target;self.draw()

    # ---------------------------------------------------------------- acting (off the window's thread)
    def act(self, doing, fn, *args, after=None):
        if self.busy:return
        self.busy = doing;self.draw()
        runner = Runner();self.runners.append(runner)
        runner.done.connect(lambda result, runner=runner: self.finished(runner, result, after))

        def work():
            try:
                result = fn(*args)
            except Exception as exc:  # noqa: BLE001 - a change that broke says so on the page; the window goes on
                result = dict(ok=False, verified=False, said='%s: %s' % (type(exc).__name__, str(exc)[:200]))
            runner.done.emit(result)
        threading.Thread(target=work, name='graphite-machine-' + self.key, daemon=True).start()

    def finished(self, runner, result, after):
        if runner in self.runners:self.runners.remove(runner)
        self.busy = None;self.last = result
        if after is not None:after(result)
        self.reload(force=True)

    # ---------------------------------------------------------------- drawing
    def draw(self):
        if self.data is None:return
        self.drawing = True
        page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(40, 26, 40, 20);box.setSpacing(14)
        box.addWidget(words(self.title(), 'title'))
        self.stamp = words(self.lead_words(), 'quiet');box.addWidget(self.stamp)
        if self.busy:
            box.addLayout(row(word('working', 'wait'), words(self.busy + '…'), stretch_at=1))
        elif self.last:
            done = self.last.get('ok') and self.last.get('verified')
            box.addLayout(row(word('done' if done else 'not done', 'live' if done else 'stop'), words(self.last.get('said', '')), stretch_at=1))
        if not self.data['available']:
            why = self.data['why'];lead = real.NOT_HERE + ': '
            why = (why[len(lead):len(lead) + 1].upper() + why[len(lead) + 1:]) if why.startswith(lead) else why
            frame, inner = card();inner.addWidget(word(real.NOT_HERE, 'stop'));inner.addWidget(words(why))
            box.addWidget(frame)
        else:
            getattr(self, 'draw_' + self.key)(box)
        box.addWidget(self.again());box.addStretch(1)
        old = self.scroll.takeWidget()
        self.scroll.setWidget(page)
        if old is not None:old.deleteLater()
        self.drawing = False

    def again(self):
        from .shell2 import sentence
        return sentence('Read it {again} now.', {'again': ('again', lambda: self.reload(force=True))})

    # Storage -------------------------------------------------------------------------------------------------------------
    def draw_storage(self, box):
        drives = self.data['drives'];free = not self.busy
        if self.safe is not None:
            frame, inner = card();inner.addLayout(row(word('safe to remove', 'live'), words(self.safe, None), stretch_at=1));box.addWidget(frame)
        if not drives:
            box.addWidget(words('No removable drive is connected. Plug one in: it shows here by itself.'))
        for drive in drives:
            frame, inner = card()
            head = words('%s · %s%s' % (drive['name'], drive['bus'].upper() or 'REMOVABLE', (' · ' + real.size_words(drive['size'])) if drive['size'] else ''), 'card')
            inner.addLayout(row(head, press('Eject safely', lambda checked=False, d=drive: self.eject(d), 'Unmount everything on it, then power it off; '
                                            '"safe to remove" is said only once that is read back', free), stretch_at=0))
            if not drive['volumes']:inner.addWidget(words('No filesystem on it that Graphite can mount.', 'quiet'))
            for volume in drive['volumes']:
                inner.addWidget(words(real.volume_words(volume)))
                if volume['mounted']:
                    line = row(word('mounted', 'live'), words('at ' + ', '.join(volume['mounted']), 'quiet'),
                               press('Open in Files', lambda checked=False, v=volume: self.open_files(v), 'Show it in a Browse tab', free),
                               press('Unmount', lambda checked=False, v=volume: self.act('Unmounting ' + real.volume_words(v), real.unmount, v['id']), '', free), stretch_at=1)
                elif volume['encrypted'] and not volume['can_mount']:
                    line = row(word('locked', 'quiet'), words('encrypted: Graphite 1.0 does not unlock it; the system\'s own tools can.', 'quiet'), stretch_at=1)
                else:
                    line = row(word('not mounted', 'quiet'), press('Mount', lambda checked=False, v=volume: self.act('Mounting ' + real.volume_words(v), real.mount, v['id']), '', free))
                inner.addLayout(line)
            if self.target == drive['id']:frame.setStyleSheet(frame.styleSheet().replace(bt.LINE, bt.AMBER_EDGE))
            box.addWidget(frame)
        box.addWidget(words('The fixed disks and the folders Graphite keeps its work in are listed under Storage in the Machine tab.', 'quiet'))

    def eject(self, drive):
        def after(result):
            self.safe = result['said'] if result.get('safe') else None
        self.safe = None
        self.act('Ejecting %s safely' % drive['name'], real.eject, drive['id'], after=after)

    def open_files(self, volume):
        place = (volume['mounted'] or [None])[0]
        browse = getattr(self.host, 'browse', None)
        if place and callable(browse):browse(place)

    # Power ---------------------------------------------------------------------------------------------------------------
    def draw_power(self, box):
        data = self.data
        box.addLayout(row(word('on battery' if data['on_battery'] else 'on mains', 'wait' if data['on_battery'] else 'live'), stretch_at=0))
        if not data['batteries']:box.addWidget(words('No battery: this computer runs on the mains only.'))
        for battery in data['batteries']:
            frame, inner = card()
            inner.addWidget(words('Battery%s' % ((' · ' + battery['name']) if battery['name'] else ''), 'card'))
            inner.addLayout(row(Meter(battery['percent']), words(real.battery_words(battery)), stretch_at=1))
            box.addWidget(frame)
        for mains in data['mains']:
            box.addLayout(row(words('Mains%s' % ((' · ' + mains['name']) if mains['name'] else '')), word('plugged in' if mains['online'] else 'not plugged in', 'live' if mains['online'] else 'quiet'), stretch_at=0))
        others = [d for d in data['devices'] if d['kind'] not in ('battery', 'mains') or (d['kind'] == 'battery' and not d['supply'])]
        if others:
            box.addWidget(words('Other devices', 'section'))
            for d in others:box.addWidget(words('%s%s · %s' % (d['kind'].capitalize(), (' · ' + d['name']) if d['name'] else '', real.battery_words(d))))
        box.addWidget(words(SYSTEM_MENU, 'quiet'))

    # Network -------------------------------------------------------------------------------------------------------------
    def draw_network(self, box):
        data = self.data;free = not self.busy
        state = word(data['state'] if data['enabled'] else 'networking off', 'live' if data['state_number'] >= 50 and data['enabled'] else 'quiet')
        box.addLayout(row(state, stretch_at=0))
        acts = [press('Turn networking off' if data['enabled'] else 'Turn networking on',
                      lambda: self.act('Turning networking %s' % ('off' if data['enabled'] else 'on'), real.set_networking, not data['enabled']), '', free)]
        if data['wifi_devices']:
            acts.append(press('Turn Wi-Fi off' if data['wifi'] else 'Turn Wi-Fi on',
                              lambda: self.act('Turning Wi-Fi %s' % ('off' if data['wifi'] else 'on'), real.set_wifi, not data['wifi']), '', free))
            acts.append(press('Look for networks', lambda: self.act('Asking NetworkManager to look for networks', real.scan, data['wifi_devices'][0]['id']), '',
                              free and data['wifi'] and data['enabled']))
        box.addLayout(row(*acts))
        if data['wifi_devices'] and not data['wifi_switch']:box.addWidget(words('The Wi-Fi switch on this computer is off: no network is heard until it is on.'))
        for device in data['wifi_devices']:
            box.addWidget(words('Wi-Fi networks heard by %s' % (device['interface'] or 'the Wi-Fi device'), 'section'))
            if not data['wifi']:box.addWidget(words('Wi-Fi is off.', 'quiet'));continue
            if not device['networks']:box.addWidget(words('No network heard yet. Look for networks asks again.', 'quiet'))
            for net in device['networks']:box.addWidget(self.network_row(device, net, free))
        wired = [d for d in data['devices'] if d['kind'] == 'wired']
        if wired:
            box.addWidget(words('Wired', 'section'))
            for d in wired:box.addLayout(row(words(d['interface']), word('no cable' if d['state_number'] == 20 else d['state'], 'live' if d['state_number'] == 100 else 'quiet'), stretch_at=0))
        box.addWidget(words('A password you type here goes to NetworkManager, which keeps it with the network. Graphite keeps no copy.', 'quiet'))

    def network_row(self, device, net, free):
        frame, inner = card()
        marks = [word('connected', 'live')] if net['active'] else []
        details = '%s · %s %d %% · %s%s' % (net['ssid'], net['strength_word'], net['strength'], net['security'] if net['security'] != 'open' else 'open, not secured',
                                             ' · saved' if net['saved'] else '')
        asking = self.asking == (device['id'], net['ssid'])
        if net['active']:
            act = press('Disconnect', lambda checked=False: self.act('Disconnecting from ' + net['ssid'], real.disconnect, device['id']), '', free)
        else:
            act = None if asking else press('Join', lambda checked=False: self.join(device, net), '', free)
        inner.addLayout(row(words(details), *marks, act, stretch_at=0))
        if asking:
            field = QLineEdit();field.setEchoMode(QLineEdit.Password);field.setPlaceholderText('Password for ' + net['ssid'])
            field.setAccessibleName('Password for ' + net['ssid']);self.password = field
            go = press('Join', lambda checked=False: self.join_with(device, net), '', free)
            cancel = press('Cancel', lambda checked=False: self.cancel_join(), '', True)
            field.returnPressed.connect(lambda: self.join_with(device, net))
            inner.addLayout(row(field, go, cancel, stretch_at=0))
            QTimer.singleShot(0, field.setFocus)
        return frame

    def join(self, device, net):
        if net['saved'] or net['security'] == 'open':
            self.act('Joining ' + net['ssid'], real.join, device['id'], net['id'], net['ssid'])
        elif net['security'] in ('WPA', 'WPA3'):
            self.asking = (device['id'], net['ssid']);self.draw()
        else:
            self.act('Joining ' + net['ssid'], real.join, device['id'], net['id'], net['ssid'])

    def join_with(self, device, net):
        field = getattr(self, 'password', None)
        secret = field.text() if field is not None else ''
        if field is not None:field.clear()
        self.asking = None
        if not secret:self.last = dict(ok=False, verified=False, said='Type the password for %s, then Join.' % net['ssid']);self.draw();return
        self.act('Joining ' + net['ssid'], real.join, device['id'], net['id'], net['ssid'], secret)
        secret = None

    def cancel_join(self):
        field = getattr(self, 'password', None)
        if field is not None:field.clear()
        self.asking = None;self.draw()

    # Sound ---------------------------------------------------------------------------------------------------------------
    def draw_sound(self, box):
        data = self.data;free = not self.busy;current = data['current']
        if not data['sinks']:box.addWidget(words('No sound output is connected.'));return
        frame, inner = card()
        inner.addWidget(words('Volume of %s' % (current['name'] if current else 'the output in use'), 'card'))
        slider = QSlider(Qt.Horizontal);slider.setRange(0, 100);slider.setTracking(False);slider.setAccessibleName('Volume')
        slider.setValue(data['percent'] or 0);slider.setEnabled(free)
        shown = words('%s %%' % (data['percent'] if data['percent'] is not None else '?'), wrap=False)
        slider.sliderMoved.connect(lambda value: shown.setText('%d %%' % value))
        slider.valueChanged.connect(lambda value: None if self.drawing else self.act('Setting the volume to %d %%' % value, real.set_volume, value))
        mute = press('Sound on' if data['muted'] else 'Mute', lambda: self.act('Turning the sound on' if data['muted'] else 'Muting', real.set_mute, not data['muted']), '', free)
        inner.addLayout(row(slider, shown, word('muted' if data['muted'] else 'on', 'quiet' if data['muted'] else 'live'), mute, stretch_at=0))
        box.addWidget(frame)
        box.addWidget(words('Outputs', 'section'))
        for sink in data['sinks']:
            mark = word('in use', 'live') if sink['default'] else press('Use this output', lambda checked=False, s=sink: self.act('Playing sound through ' + s['name'], real.set_output, s['id']), '', free)
            box.addLayout(row(words(sink['name']), mark, stretch_at=0))

    # Screens -------------------------------------------------------------------------------------------------------------
    def draw_screens(self, box):
        data = self.data;free = not self.busy and self.keep is None
        if self.keep is not None:
            frame, inner = card()
            self.keep_words = words('Keep this arrangement? It goes back by itself in %d s.' % self.keep['left'])
            inner.addLayout(row(word('waiting for you', 'wait'), self.keep_words, press('Keep', self.kept), press('Go back', self.go_back), stretch_at=1))
            box.addWidget(frame)
        box.addLayout(row(words('Arrangement'), word(data['arrangement'], 'live')))
        if len(data['connected']) > 1:
            box.addLayout(row(press('Mirror', lambda: self.change('mirror'), 'The same picture on every screen', free and data['arrangement'] != 'mirror'),
                              press('Extend', lambda: self.change('extend'), 'One wide desk across the screens', free and data['arrangement'] != 'extend')))
        for output in data['connected']:
            frame, inner = card()
            marks = [word('primary', 'live')] if output['primary'] else []
            where = ('%s at %d, %d' % (output['current'], output['x'], output['y'])) if output['active'] else 'off'
            inner.addLayout(row(words('%s · %s' % (output['name'], where), 'card'), *marks, word('on' if output['active'] else 'off', 'live' if output['active'] else 'quiet'), stretch_at=0))
            modes = QComboBox();modes.setAccessibleName('Modes of ' + output['name'])
            for m in output['modes']:
                modes.addItem('%s%s' % (m['mode'], ' (preferred)' if m['preferred'] else ''), m['mode'])
            if output['current']:modes.setCurrentIndex(max(0, modes.findData(output['current'])))
            acts = [modes, press('Use this mode', lambda checked=False, o=output, c=modes: self.change('mode', o['name'], c.currentData()), '', free and bool(output['modes']))]
            if output['active'] and not output['primary']:acts.append(press('Make primary', lambda checked=False, o=output: self.change('primary', o['name']), '', free))
            acts.append(press('Turn off' if output['active'] else 'Turn on', lambda checked=False, o=output: self.change('off' if o['active'] else 'on', o['name']), '', free))
            inner.addLayout(row(*acts))
            box.addWidget(frame)
        loose = [o['name'] for o in data['outputs'] if not o['connected']]
        if loose:box.addWidget(words('Nothing connected at %s.' % ', '.join(loose), 'quiet'))

    def change(self, kind, name=None, mode=None):
        def after(result):
            if result.get('ok') and result.get('before'):
                self.keep = dict(before=result['before'], left=KEEP_SECONDS);self.countdown.start()
        self.act('Changing the screens', real.change_screens, kind, name, mode, after=after)

    def keep_tick(self):
        if self.keep is None:self.countdown.stop();return
        self.keep['left'] -= 1
        if self.keep['left'] <= 0:self.go_back();return
        label = getattr(self, 'keep_words', None)
        if label is not None:label.setText('Keep this arrangement? It goes back by itself in %d s.' % self.keep['left'])

    def kept(self):
        self.countdown.stop();self.keep = None
        self.last = dict(ok=True, verified=True, said='Kept the new arrangement.');self.reload(force=True)

    def go_back(self):
        self.countdown.stop();before = (self.keep or {}).get('before');self.keep = None
        self.act('Putting the screens back as they were', real.put_back, before)


class Meter(QWidget):
    """A battery's level: a bar with its number beside it (the number is the reading; the bar only shows it)."""

    def __init__(self, value):
        super().__init__();self.value = value if isinstance(value, int) else None
        self.setFixedSize(120, 14);self.setAccessibleName('Battery level %s %%' % (self.value if self.value is not None else 'unknown'))

    def paintEvent(self, event):
        from PySide6.QtGui import QColor, QPainter
        painter = QPainter(self);rect = self.rect().adjusted(0, 0, -1, -1)
        painter.setPen(QColor(bt.LINE_STRONG));painter.setBrush(Qt.NoBrush);painter.drawRect(rect)
        if self.value is not None:
            inner = rect.adjusted(2, 2, -1, -1);inner.setWidth(inner.width() * max(0, min(100, self.value)) // 100)
            painter.fillRect(inner, QColor(bt.READY if self.value > 20 else bt.STOP))
        painter.end()


def show(host, key='storage', target=None):
    """Open (or bring forward) a Machine page in the centre."""
    close = getattr(host, '_close_start', None)
    if callable(close):close()
    tabs = host.tabs
    for i in range(tabs.count()):
        widget = tabs.widget(i)
        if isinstance(widget, MachineRoom) and widget.key == key:
            tabs.setCurrentIndex(i);widget.reload(force=True);widget.focus_on(target);return widget
    tab = MachineRoom(host, key);tabs.addTab(tab, tab.title());tabs.setCurrentWidget(tab)
    if target:tab.focus_on(target)
    return tab


def reopen(host, row):
    """workspace_tabs: a saved Machine page comes back by its title."""
    key = {v: k for k, v in real.TITLES.items()}.get(str(row.get('title') or ''), 'storage')
    return show(host, key)
