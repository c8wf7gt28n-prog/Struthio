"""Graphite 1.0 S5 · The leave flow's open apps: before Return to Debian, Log out, Restart or Shut down, which apps are still
open, and asking them to close politely first.

The apps you opened run in sessions of their own (session_launch), so they outlive Graphite's window; they end only with
the session itself, and work not saved in them would be lost. So before the session or the computer ends:

  Log out, Restart, Shut down   the System menu's confirmation names the apps still open (confirm_words); after you confirm,
                                this dialog asks each to close (S3's polite close, _NET_CLOSE_WINDOW: the app may ask you
                                to save) and waits for them; then Graphite closes the ordinary way and asks the system.
  Return to Debian              (the dedicated session only: elsewhere the apps belong to the desktop you came from) the same
                                dialog first, as the question itself.

The dialog lists each app window (its program, its title) with its state in words: OPEN, ASKED TO CLOSE, CLOSED, ASKING YOU
(a dialog of that app appeared, "Save changes?" perhaps: Show brings it forward, you answer it there), CANNOT BE ASKED (the app
takes no polite close: close it from inside it). Its answers: Ask them to close (then it goes on by itself once every app
has closed), Go on without closing them (they end with the session), Cancel (nothing more is done; an app already closed
stays closed). Nothing is ever killed or forced.

Without a window list (no X, Graphite's window drawn offscreen) there is nothing to say and the leave goes on as before.
"""
from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import boss_theme as bt
from . import windows_x11 as wx

WORDS = {'logout': 'log out', 'restart': 'restart', 'shutdown': 'shut down', 'leave': 'return to Debian'}
THEN = {'logout': 'your login session ends', 'restart': 'this computer restarts', 'shutdown': 'this computer shuts down',
        'leave': 'this session ends'}
WAIT_SECONDS = 12            # after asking, how long before the dialog says which apps are still open, and why perhaps
TICK_MS = 400                # how often the dialog reads the windows while it waits
CLOSED, GO_ON, CANCEL, NONE = 'closed', 'go_on', 'cancel', 'none'


def reading(watcher=None):
    """(the app windows open now, read fresh; why there is no list). Only when Graphite's window is on X (as the strip)."""
    if watcher is None:
        app = QApplication.instance()
        if app is None or QApplication.platformName() != 'xcb':
            return [], 'The computer\'s window is not on an X display here, so it cannot see the apps\' windows'
        watcher = wx.shared()
    if not watcher.start():return [], watcher.reason
    snap = watcher.refresh()
    if not snap.get('available'):return [], snap.get('reason', '')
    return [r for r in snap['windows'] if r['listed'] and not r['graphite']], ''


def mains(rows):
    """The apps' own windows (a dialog is answered in its app, never closed from here)."""
    return [r for r in rows if not r['dialog']]


def name(row):
    return '%s (%s)' % (row['program'], row['title']) if row['title'] and row['title'] != row['program'] else row['program']


def confirm_words(action, watcher=None):
    """The line the confirmation adds when apps are open ('' when none, or no list)."""
    rows, _ = reading(watcher)
    apps = mains(rows)
    if not apps:return ''
    listed = ', '.join(name(r) for r in apps[:6]) + (' and %d more' % (len(apps) - 6) if len(apps) > 6 else '')
    return ('\n\nApps still open: %s. After you confirm, Kas asks each to close, the polite way (an app may ask you to '
            'save first), before %s.' % (listed, THEN.get(action, 'the session ends')))


def word(text, tone):
    colour = {'live': bt.READY, 'wait': bt.AMBER_TEXT, 'stop': bt.STOP}.get(tone, bt.QUIET)
    label = QLabel(text.upper());label.setTextFormat(Qt.PlainText)
    label.setStyleSheet('QLabel {color:%s; font-family:"%s"; letter-spacing:1px;}' % (colour, bt.MONO))
    return label


class LeaveAppsDialog(QDialog):
    """The open apps before leaving; result() after exec: CLOSED, GO_ON or CANCEL (self.outcome)."""

    def __init__(self, host, action, rows, watcher=None):
        super().__init__(host);self.host = host;self.action = action;self.watcher = watcher
        self.rows = list(rows);self.asked = {};self.gone = {};self.refused = {};self.started = None;self.outcome = CANCEL
        self.setWindowTitle('Apps are still open');self.setModal(True);self.setMinimumWidth(640)
        box = QVBoxLayout(self);box.setContentsMargins(22, 18, 22, 16);box.setSpacing(10)
        self.heading = QLabel('Before you %s, these apps are still open:' % WORDS.get(action, 'leave'));self.heading.setWordWrap(True)
        self.heading.setProperty('arcRole2', 'card');box.addWidget(self.heading)
        self.list = QWidget();self.grid = QGridLayout(self.list);self.grid.setContentsMargins(0, 4, 0, 4);self.grid.setHorizontalSpacing(14)
        box.addWidget(self.list)
        self.explain = QLabel(('They end when %s, and work not saved in them is lost. Kas can ask each one to close first, '
                               'the polite way: an app with unsaved work may ask you to save it. Nothing is forced.') % THEN.get(action, 'the session ends'))
        self.explain.setWordWrap(True);box.addWidget(self.explain)
        self.status = QLabel('');self.status.setWordWrap(True);box.addWidget(self.status)
        line = QHBoxLayout();line.addStretch(1)
        self.ask = QPushButton('Ask them to close');self.go = QPushButton('Go on without closing them');self.cancel = QPushButton('Cancel')
        for b in (self.ask, self.go, self.cancel):b.setAutoDefault(False);line.addWidget(b)
        self.ask.setDefault(True)
        self.ask.clicked.connect(self.ask_all);self.go.clicked.connect(self.go_on);self.cancel.clicked.connect(self.reject)
        box.addLayout(line)
        self.timer = QTimer(self);self.timer.setInterval(TICK_MS);self.timer.timeout.connect(self.tick)
        self.draw()

    # -- reading
    def read(self):
        rows, why = reading(self.watcher)
        if why:return
        seen = {r['window'] for r in rows}
        for r in self.rows:
            if r['window'] not in seen and r['window'] not in self.gone:self.gone[r['window']] = time.monotonic()
        known = {r['window'] for r in self.rows}
        self.rows += [r for r in rows if r['window'] not in known]      # a new window (a "Save changes?" dialog) joins the list
        fresh = {r['window']: r for r in rows}
        self.rows = [fresh.get(r['window'], r) for r in self.rows]

    def open_rows(self):
        return [r for r in self.rows if r['window'] not in self.gone]

    def state(self, row):
        w = row['window']
        if w in self.gone:return 'closed', 'live'
        if row['dialog']:return 'asking you', 'wait'
        if w in self.refused:return 'cannot be asked', 'stop'
        if w in self.asked:return 'asked to close', 'wait'
        return 'open', 'quiet'

    def draw(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget() is not None:item.widget().deleteLater()
        for i, row in enumerate(self.rows):
            words, tone = self.state(row)
            label = QLabel(name(row) + ('   · a window of ' + self.owner_of(row) if row['dialog'] and self.owner_of(row) else ''))
            label.setTextFormat(Qt.PlainText);label.setWordWrap(True)
            self.grid.addWidget(label, i, 0);self.grid.addWidget(word(words, tone), i, 1)
            if row['window'] not in self.gone:
                show = QPushButton('Show');show.setAutoDefault(False);show.setToolTip('Bring this window forward, to answer it there')
                show.clicked.connect(lambda checked=False, w=row['window']: self.show_window(w))
                self.grid.addWidget(show, i, 2)
        self.grid.setColumnStretch(0, 1)
        self.adjustSize()      # every row in sight

    def owner_of(self, row):
        parent = next((r for r in self.rows if r['window'] == row.get('transient_for')), None)
        return parent['program'] if parent else ''

    # -- acting (your presses)
    def ask_all(self):
        watcher = self.watcher or wx.shared()
        for row in mains(self.open_rows()):
            answer = watcher.close(row['window'])
            if answer.get('asked'):self.asked[row['window']] = time.monotonic();self.refused.pop(row['window'], None)
            else:self.refused[row['window']] = answer.get('reason') or 'not asked'
        self.started = time.monotonic()
        self.ask.setEnabled(False);self.ask.setText('Asked');self.go.setText('Go on anyway')
        self.status.setText('Asked. Waiting for the apps to close…');self.adjustSize()
        self.timer.start();self.draw()

    def show_window(self, window):
        watcher = self.watcher or wx.shared()
        answer = watcher.activate(window)
        if not answer.get('asked'):self.status.setText('Could not bring it forward: ' + (answer.get('reason') or 'no reason given'))

    def go_on(self):
        self.outcome = GO_ON;self.timer.stop();self.accept()

    def reject(self):
        self.outcome = CANCEL;self.timer.stop();super().reject()

    def tick(self):
        self.read();self.draw()
        left = self.open_rows()
        if not left:
            self.timer.stop();self.status.setText('All the apps have closed.');self.ask.setEnabled(False);self.go.setEnabled(False)
            self.outcome = CLOSED;QTimer.singleShot(500, self.accept);return
        if self.started is not None and time.monotonic() - self.started > WAIT_SECONDS:
            asking = [r for r in left if r['dialog']]
            self.status.setText('%d window%s still open.%s' % (len(left), '' if len(left) == 1 else 's', (' An app is asking you something in its own window '
                                                                '(unsaved work, perhaps): press Show, answer it there, and Kas goes on once it has closed.')
                                                       if asking else ' An app may be asking you about unsaved work: press Show to see it.'))
            self.adjustSize()
            self.ask.setEnabled(True);self.ask.setText('Ask again');self.started = None


def before_leaving(host, action, watcher=None):
    """The apps step of the leave flow. NONE (no app open, or no list here: nothing asked), CLOSED (every app closed after
    being asked), GO_ON (you chose to go on with apps open) or CANCEL."""
    rows, _ = reading(watcher)
    if not rows:return NONE
    dialog = LeaveAppsDialog(host, action, rows, watcher)
    host.leave_apps_dialog = dialog
    try:
        dialog.exec()
        return dialog.outcome
    finally:
        host.leave_apps_dialog = None
