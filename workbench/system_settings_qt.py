"""Graphite 1.0 S5 · The Settings tree on real settings: "This computer".

The left pane's Settings tab keeps Graphite's own settings (Workspace, Assistant) and gains, first, a root of the
computer's own settings. Each row opens its page in the centre; every change there is your press, reads its effect back,
and says DONE only then:

  Default apps    which app opens each kind of file and address (S2, apps_catalog): the app in force and where that is
                  said (your own mimeapps.list or the system's), the apps that take the kind, Make it the default (the
                  Kernel's apps.default, approve scope, written to your own ~/.config/mimeapps.list and read back), and Use
                  the system's choice (your line taken back out).
  Sound           S4's Sound page (machine_room_qt): volume, mute, the output in use.
  Screens         S4's Screens page: each screen's mode, primary, on or off, mirror or extend, with Keep or go back.
  Network         S4's Network page: networking and Wi-Fi, the networks heard, Join (the password goes to NetworkManager).
  Power           S4's Power page: the battery and the mains.
  Session         S1's session: Lock, Suspend, Log out, Restart, Shut down, Return to Debian with whether each is available
                  and why (each press is the System menu's own), the permission prompt agent (polkit_agent), the app strip
                  as a dock (system_dock_qt), the notifications, the console route.
  Notifications   S5's notification server (notify_server): whether Graphite shows what apps send here and why not; Show a
                  toast or Only keep them in Log (urgent ones always show); the newest ones with their state, and Close or
                  their actions while they are open; Log opens the Events stream where every one is kept.

The S4 rows open S4's own pages (the same functions; the left pane stays on Settings while you came from it).
"""
from __future__ import annotations

import os
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox, QFrame, QGridLayout, QScrollArea, QVBoxLayout, QWidget

from . import boss_theme as bt
from .machine_room_qt import card, press, row, word, words

ROOT = 'settings:system'
MACHINE = ('sound', 'screens', 'network', 'power')
ROWS = (('apps', 'Default apps', 'Which app opens each kind of file and address. Written to your own mimeapps.list and read back.'),
        ('sound', 'Sound', 'Volume, mute and the output in use (PipeWire, through wpctl).'),
        ('screens', 'Screens', 'Which screens, their modes, primary, mirror or extend (xrandr), with Keep or go back.'),
        ('network', 'Network', 'Networking and Wi-Fi on or off, the networks heard, Join (NetworkManager keeps the password).'),
        ('power', 'Power', 'The battery and the mains (UPower).'),
        ('session', 'Session', 'Lock, Suspend, Log out, Restart, Shut down, Return to Debian; permission prompts; the app strip.'),
        ('notifications', 'Notifications', 'What apps tell you: shown as a toast at the foot of her column, and kept in Log.'),
        ('door', 'System changes', 'Software, services, date and time, the computer’s name and accounts, through the system’s own prompt.'))  # 1.1 KS3
TITLES = {key: label for key, label, _ in ROWS}
PAGE_SECONDS = 3
SESSION_SECONDS = 10     # the session page asks logind again this often while it shows
# The kinds of file and address the Default apps page offers (the owner's words); a web address sets http and https together.
KINDS = (('x-scheme-handler/https', 'Web addresses', ('x-scheme-handler/http',)),
         ('x-scheme-handler/mailto', 'Mail addresses', ()),
         ('application/pdf', 'PDF files', ()),
         ('text/plain', 'Plain text files', ()),
         ('text/markdown', 'Markdown files', ()),
         ('text/csv', 'CSV tables', ()),
         ('text/html', 'Web pages saved as files', ()),
         ('image/png', 'PNG pictures', ()),
         ('image/jpeg', 'JPEG pictures', ()),
         ('image/svg+xml', 'SVG drawings', ()),
         ('application/vnd.oasis.opendocument.text', 'OpenDocument texts', ()),
         ('application/vnd.oasis.opendocument.spreadsheet', 'OpenDocument spreadsheets', ()),
         ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'Word documents', ()),
         ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'Excel workbooks', ()),
         ('audio/mpeg', 'MP3 sound', ()),
         ('video/mp4', 'MP4 video', ()),
         ('inode/directory', 'Folders', ()))


def nodes():
    """The tree's nodes for this computer, in settings_registry.nodes()' shape (role 'system_page', the page's key in 'page')."""
    out = [dict(id=ROOT, parent=None, role='settings_root', label='This computer', target=None, scope=None, provider='system_settings',
                tip='Settings of this computer: default apps, sound, screens, network, power, the session and notifications.')]
    for key, label, tip in ROWS:
        out.append(dict(id='system:' + key, parent=ROOT, role='system_page', label=label, target=None, scope=None,
                        provider='system_settings', page=key, tip=tip + '\nChoose it to open its page in the centre.'))
    return out


def open_page(host, key):
    """A row of This computer chosen: its page in the centre (S4's own page for sound, screens, network and power)."""
    if key in MACHINE:
        from . import machine_room_qt
        return machine_room_qt.show(host, key)
    if key == 'door':      # 1.1 KS3 (the system door): its own page (system_door_qt)
        from . import system_door_qt
        return system_door_qt.show_page(host)
    return show(host, key)


def select_row(host, key):
    """Show the row of this page in the Settings tree, without opening anything again."""
    nav = getattr(host, 'settings_navigator', None);item = getattr(nav, 'items', {}).get('system:' + key) if nav is not None else None
    if item is None:return
    from PySide6.QtCore import QSignalBlocker
    with QSignalBlocker(nav.tree):
        parent = item.parent()
        while parent:parent.setExpanded(True);parent = parent.parent()
        nav.tree.setCurrentItem(item);nav.tree.scrollToItem(item)


def clock(stamp):
    return time.strftime('%H:%M:%S', time.localtime(stamp)) if stamp else 'not read'


class SystemSettingsRoom(QWidget):
    """One of This computer's own pages in the centre (a room tab): Default apps, Session or Notifications."""

    def __init__(self, host, key):
        super().__init__();self.host = host;self.key = key if key in ('apps', 'session', 'notifications') else 'session'
        self.setObjectName('LibraryTab');self.setProperty('ledgerRoom', True);self.setAccessibleName('Settings: ' + self.title())
        self.last = None;self.seen = None;self.data = None;self.choices = {};self.presses = {}
        outer = QVBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame);outer.addWidget(self.scroll)
        self.timer = QTimer(self);self.timer.setInterval((SESSION_SECONDS if self.key == 'session' else PAGE_SECONDS) * 1000)
        self.timer.timeout.connect(self.tick);self.timer.start()
        self.reload(force=True)

    def title(self):return TITLES[self.key]

    def settings_row(self):
        """navigation_qt: this page keeps the left pane on Settings, on its row."""
        return 'system:' + self.key

    def inspector(self):
        return self.title(), [(self.title(), (self.data or {}).get('short', ''))]

    # -- reading
    def tick(self):
        if getattr(self.host, '_closing', False):self.timer.stop();return
        if not self.isVisible():return
        focus = self.focusWidget()
        if isinstance(focus, QComboBox) and focus.hasFocus():return      # never redraw under the owner's hand
        self.reload()

    def reload(self, force=False):
        data = getattr(self, 'read_' + self.key)()
        seen = repr(sorted((k, v) for k, v in data.items() if k != 'read_at'))
        if not force and seen == self.seen:return
        self.data = data;self.seen = seen;self.draw()

    def read_apps(self):
        from . import apps_catalog as ac
        try:catalog = ac.scan()
        except (OSError, ValueError) as exc:return dict(error=str(exc), kinds=[], short='not read', read_at=time.time())
        mine = str(ac.config_home() / 'mimeapps.list');kinds = []
        home = os.path.expanduser('~')
        for mime, label, also in KINDS:
            try:
                ident, said_by = ac.default_for(mime, catalog)
                apps = [(app.id, app.name, how) for app, how in ac.apps_for(mime, catalog)]
            except (OSError, ValueError):
                ident, said_by, apps = None, '', []
            app = catalog.get(ident) if ident else None
            kinds.append(dict(type=mime, label=label, also=also, default=ident, name=app.name if app else '', said_by=tilde(said_by, home),
                              yours=bool(said_by) and said_by == mine, apps=apps))
        chosen = sum(1 for k in kinds if k['default'])
        return dict(kinds=kinds, mine=tilde(mine, home), short='%d of %d kinds have an app' % (chosen, len(kinds)), read_at=time.time(), error='')

    def read_session(self):
        from . import polkit_agent, session_power
        try:states = session_power.availability()
        except Exception as exc:  # noqa: BLE001 - the page says what went wrong; the window goes on
            states = {key: dict(available=False, reason='Could not read: %s' % exc) for key in session_power.GROUP}
        notes = getattr(self.host, 'notifications', None)
        dock = self.host.dock_status() if callable(getattr(self.host, 'dock_status', None)) else dict(standing=False, why='The app strip stays in Graphite\'s window.')
        return dict(dedicated=session_power.dedicated(), restarts=os.environ.get('ARC_LEDGER_SESSION_RESTARTS', ''),
                    states={k: dict(available=v['available'], reason=v['reason'], label=v.get('label')) for k, v in states.items()},
                    agent=polkit_agent.agent(), dock=dict(standing=dock.get('standing'), why=dock.get('why', '')),
                    notes=notes.status() if notes is not None else dict(state='off', why='Graphite\'s notifications are not installed in this window.'),
                    short='Graphite is this session' if session_power.dedicated() else 'inside another desktop', read_at=time.time())

    def read_notifications(self):
        from .notify_qt import toasts_on
        notes = getattr(self.host, 'notifications', None)
        status = notes.status() if notes is not None else dict(state='off', why='Graphite\'s notifications are not installed in this window.')
        recent = notes.notes.recent(12) if notes is not None else []
        return dict(status=status, toasts=toasts_on(self.host),
                    recent=[dict(id=n['id'], app=n['app'], summary=n['summary'], at=n['at'], closed=n['closed'], urgency=n['urgency'],
                                 actions=n['actions'], logged=n.get('logged'), transient=n.get('transient')) for n in recent],
                    short={'serving': 'shown here, kept in Log'}.get(status['state'], 'not shown here'), read_at=time.time())

    # -- drawing
    def draw(self):
        self.choices = {};self.presses = {}
        page = QWidget();box = QVBoxLayout(page);box.setContentsMargins(40, 26, 40, 20);box.setSpacing(14)
        box.addWidget(words(self.title(), 'title'))
        box.addWidget(words('SETTINGS / THIS COMPUTER / ' + self.title().upper(), 'quiet'))
        if self.last:
            done = self.last.get('ok') and self.last.get('verified')
            box.addLayout(row(word('done' if done else 'not done', 'live' if done else 'stop'), words(self.last.get('said', '')), stretch_at=1))
        getattr(self, 'draw_' + self.key)(box)
        box.addStretch(1)
        old = self.scroll.takeWidget();self.scroll.setWidget(page)
        if old is not None:old.deleteLater()

    # Default apps -------------------------------------------------------------------------------------------------------------
    def draw_apps(self, box):
        data = self.data
        box.addWidget(words('Which app opens each kind of file and address. A change is written to your own %s and read back '
                            'before it is said; the system\'s own lists are never written. Read at %s.' % (data.get('mine', 'mimeapps.list'), clock(data['read_at'])), 'quiet'))
        if data.get('error'):
            frame, inner = card();inner.addWidget(word('not read', 'stop'));inner.addWidget(words(data['error']));box.addWidget(frame);return
        for kind in data['kinds']:
            frame, inner = card()
            if kind['default']:
                state = word('your choice' if kind['yours'] else 'the system\'s', 'live' if kind['yours'] else 'quiet')
                said = 'Opens with %s.' % kind['name']
            else:
                state = word('none chosen', 'quiet');said = 'No app is chosen: Open with asks each time.'
            inner.addLayout(row(words(kind['label'], 'card'), state, stretch_at=0))
            inner.addWidget(words(said + ((' Said by ' + kind['said_by'] + '.') if kind['said_by'] and not kind['yours'] else ''), 'quiet'))
            if not kind['apps']:
                inner.addWidget(words('No installed app says it opens these.', 'quiet'))
            else:
                choice = QComboBox();choice.setAccessibleName('Apps for ' + kind['label'])
                for ident, name, how in kind['apps']:choice.addItem('%s%s' % (name, ' (in force)' if ident == kind['default'] else ''), ident)
                self.choices[kind['type']] = choice
                make = press('Make it the default', lambda checked=False, k=kind, c=choice: self.make_default(k, c.currentData()),
                             'Open %s with this app from now on' % kind['label'].lower())
                self.presses[('make', kind['type'])] = make;acts = [choice, make]
                if kind['yours']:
                    back = press('Use the system\'s choice', lambda checked=False, k=kind: self.make_default(k, ''),
                                 'Take your own line for %s back out of your mimeapps.list' % kind['label'].lower())
                    self.presses[('back', kind['type'])] = back;acts.append(back)
                inner.addLayout(row(*acts))
            box.addWidget(frame)

    def make_default(self, kind, ident):
        """Your press: apps.default through the Kernel (S2: approve scope, read back), for the kind and its companions."""
        from . import apps_qt
        results = []
        for mime in (kind['type'], *kind['also']):
            try:results.append(apps_qt.call(self.host, 'apps.default', {'type': mime, 'id': ident}))
            except ValueError as exc:results.append(dict(verified=False, words=str(exc)))
        ok = all(r.get('verified') for r in results)
        said = results[0].get('words', '') if results else ''
        if ok and kind['also']:said = '%s now open with %s.' % (kind['label'], next((n for i, n, _ in kind['apps'] if i == ident), ident)) if ident else '%s: your own choice is taken out.' % kind['label']
        self.last = dict(ok=ok, verified=ok, said=said or ('Done.' if ok else 'Not done.'))
        self.reload(force=True)
        return self.last

    # Session ------------------------------------------------------------------------------------------------------------------
    def draw_session(self, box):
        from . import session_power as power
        data = self.data
        if data['dedicated']:
            lead = ('Graphite is this session: Fluxbox stays hidden, and if Graphite\'s window ends unexpectedly the session starts '
                    'it again while your apps stay open%s.' % ((' (started again %s time%s so far)' % (data['restarts'], '' if data['restarts'] == '1' else 's')) if data['restarts'] not in ('', '0') else ''))
        else:
            lead = 'Graphite runs inside another desktop here: these act on that desktop\'s session.'
        box.addWidget(words(lead + ' Read at %s.' % clock(data['read_at']), 'quiet'))
        frame, inner = card();inner.addWidget(words('Leave and power', 'card'))
        grid = QGridLayout();grid.setHorizontalSpacing(14);grid.setVerticalSpacing(8)
        for i, (key, state) in enumerate(data['states'].items()):
            label = state.get('label') or power.WORDS.get(key, key)
            act = press(label, lambda checked=False, key=key: self.session_act(key), power.SCOPES.get(key, ''), state['available'])
            reason = words(short(state['reason']));reason.setToolTip(state['reason'])
            grid.addWidget(act, i, 0);grid.addWidget(word('available' if state['available'] else 'unavailable', 'live' if state['available'] else 'stop'), i, 1)
            grid.addWidget(reason, i, 2)
        grid.setColumnStretch(2, 1);inner.addLayout(grid)
        box.addWidget(frame)
        agent = data['agent']
        frame, inner = card()
        inner.addLayout(row(words('Permission prompts', 'card'), word('answered' if agent['running'] else 'none here', 'live' if agent['running'] else 'stop'), stretch_at=0))
        inner.addWidget(words(agent['words'] + ' When an app or Graphite asks the system for something that needs your permission, '
                              'the system\'s own prompt asks for your password: you type it there, never into Graphite.'))
        box.addWidget(frame)
        dock = data['dock']
        frame, inner = card()
        inner.addLayout(row(words('The app strip', 'card'), word('a dock' if dock['standing'] else 'in the window', 'live' if dock['standing'] else 'quiet'), stretch_at=0))
        inner.addWidget(words('The app windows and Graphite stand in a slim dock across the top of the screen, above every app; '
                              'apps are placed below it, and its first entry always brings Graphite back.' if dock['standing'] else
                              (dock['why'] or 'The app strip stays in Graphite\'s window.')))
        box.addWidget(frame)
        notes = data['notes']
        frame, inner = card()
        inner.addLayout(row(words('Notifications', 'card'), word('shown here' if notes['state'] == 'serving' else 'not shown here',
                                                                 'live' if notes['state'] == 'serving' else 'quiet'), stretch_at=0))
        inner.addWidget(words(notes['why']))
        inner.addLayout(row(press('Notifications…', lambda: open_page(self.host, 'notifications'), 'Open the Notifications page')))
        box.addWidget(frame)
        frame, inner = card();inner.addWidget(words('The console route', 'card'))
        inner.addWidget(words('Return to Debian ends this session at the text login; the computer stays on. From the text login, '
                              'START_MINIMAL_DEBIAN.sh in Graphite\'s folder starts this session again.'))
        box.addWidget(frame)

    def session_act(self, key):
        """Your press: the System menu's own action (the same questions, confirmation and order)."""
        from . import session_power as power
        if key == 'leave':return power.leave(self.host)
        if key == 'lock':return power.run_lock(self.host)
        if key == 'suspend':return power.run_suspend(self.host)
        return power.run_action(self.host, key)

    # Notifications ------------------------------------------------------------------------------------------------------------
    def draw_notifications(self, box):
        data = self.data;status = data['status']
        frame, inner = card()
        serving = status['state'] == 'serving'
        inner.addLayout(row(words('Graphite as the notification server', 'card'), word('serving' if serving else 'not serving', 'live' if serving else 'quiet'), stretch_at=0))
        inner.addWidget(words(status['why']))
        if serving:
            inner.addWidget(words('Apps send their notifications to Graphite on the session bus (org.freedesktop.Notifications). '
                                  'What they say is shown as plain words, never acted on, and kept in Log (Events).', 'quiet'))
        box.addWidget(frame)
        frame, inner = card();inner.addWidget(words('How they are shown', 'card'))
        on = data['toasts']
        inner.addLayout(row(press(('● ' if on else '○ ') + 'Show a toast', lambda: self.set_toasts(True), 'At the foot of her column; it never takes the keyboard'),
                            word('chosen', 'live') if on else None,
                            press(('● ' if not on else '○ ') + 'Only keep them in Log', lambda: self.set_toasts(False), 'Nothing shows; Log keeps each one'),
                            word('chosen', 'live') if not on else None))
        inner.addWidget(words('Urgent notifications always show, and stay until you close them.', 'quiet'))
        box.addWidget(frame)
        frame, inner = card()
        inner.addLayout(row(words('The newest', 'card'), press('Log', self.open_log, 'Open Log\'s Events, where every notification is kept'), stretch_at=0))
        if not data['recent']:inner.addWidget(words('None yet.', 'quiet'))
        for n in data['recent']:
            state = (n['closed'] or 'open')
            parts = [words('%s · “%s” · %s' % (time.strftime('%H:%M', time.localtime(n['at'])), n['app'] or 'an app', n['summary'] or '(no title)')),
                     word(('urgent · ' if n['urgency'] == 2 else '') + state, 'wait' if n['urgency'] == 2 and not n['closed'] else 'live' if not n['closed'] else 'quiet')]
            if not n['closed'] and serving:
                notes = self.host.notifications
                for key, label in n['actions']:
                    if key != 'default':parts.append(press(label, lambda checked=False, i=n['id'], k=key: (notes.invoke(i, k), self.reload(force=True)), 'Tell the app: ' + label))
                parts.append(press('Close', lambda checked=False, i=n['id']: (notes.dismiss(i), self.reload(force=True)), 'Close this notification'))
            inner.addLayout(row(*parts, stretch_at=0))
        box.addWidget(frame)

    def set_toasts(self, on):
        from .notify_qt import set_toasts, toasts_on
        set_toasts(self.host, on)
        ok = toasts_on(self.host) == bool(on)
        self.last = dict(ok=ok, verified=ok, said='Notifications now show as a toast and are kept in Log.' if on else 'Notifications are now only kept in Log (urgent ones still show).')
        self.reload(force=True)

    def open_log(self):
        bar = getattr(self.host, 'type_bar', None);console = getattr(self.host, 'console', None)
        try:
            if bar is not None:bar.set_target('log', focus=False)
            if console is not None:console.open('log', focus=False)
        except (TypeError, AttributeError, RuntimeError):
            if bar is not None:bar.set_target('log')


def tilde(path, home):
    """A path under your home folder said from ~ (as you would write it)."""
    path = str(path or '')
    return '~' + path[len(home):] if home and home != '/' and path.startswith(home + os.sep) else path


def short(text, most=150):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= most else text[:most - 1].rstrip() + '…'


def show(host, key):
    """Open (or bring forward) one of This computer's own pages in the centre."""
    close = getattr(host, '_close_start', None)
    if callable(close):close()
    tabs = host.tabs
    for i in range(tabs.count()):
        widget = tabs.widget(i)
        if isinstance(widget, SystemSettingsRoom) and widget.key == key:
            tabs.setCurrentIndex(i);widget.reload(force=True);return widget
    tab = SystemSettingsRoom(host, key);tabs.addTab(tab, tab.title());tabs.setCurrentWidget(tab)
    return tab


def reopen(host, row):
    """workspace_tabs: a saved page comes back by its title."""
    key = {v: k for k, v in TITLES.items()}.get(str(row.get('title') or ''), 'session')
    return open_page(host, key)
