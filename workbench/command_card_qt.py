"""Graphite 1.1 B4 · Command…: the exact line a file or a folder is, or runs, with Copy and "Put it in the line".

The design direction's section 1 (Power's graft: "anything visible answers Command… with the exact line it is or runs") and its
right-click rule ("Properties last and Command… above it"). On a file or a folder in Files (a row of List, a tile of Icons, or
the folder itself on the empty space) the right-click's Command… (Ctrl+.) shows:

  What Open runs     a file: the Debian command its Open starts, word for word as the app's desktop entry gives it with this
                     file put in (app_files.choose and apps_catalog.command: the very code Open runs); a file whose family
                     opens through Graphite's own bridge names the Kernel operation instead; a file no app here opens says so
  What it is         the Graphite line that reads it (@files:…): Enter on it in the bar's line reads it on the line page
  In the Terminal    a folder: cd to it

Each line has Copy and Put it in the line (the bar's line, with its rows: Enter there does what its first row says). Nothing
runs from the card itself.
"""
from __future__ import annotations

import os
import shlex
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


def shown_path(path):
    """A path as the owner reads it: ~/… inside the home."""
    text = str(path);home = str(Path.home())
    return '~' + text[len(home):] if text == home or text.startswith(home + os.sep) else text


def graphite_line(path):
    """The Graphite line that reads a file or folder: @files:<path> (a path with spaces or a | in quotes)."""
    shown = shown_path(path)
    return '@files:' + ('"%s"' % shown if any(ch in shown for ch in ' |"') else shown)


def open_line(path):
    """(line, words) for what Open runs on a file: the app's own command line with the file in it, as Open starts it."""
    from . import app_files, apps_catalog
    target = Path(path).resolve()
    try:route, app, program, name, reason = app_files.choose(target)
    except Exception as exc:  # noqa: BLE001 - the card says why, never guesses
        return '', 'What Open runs could not be read here: %s.' % (str(exc)[:120] or type(exc).__name__)
    if route == 'bridge':
        bridge = getattr(program, 'bridge', '') or 'its bridge'
        return ('/appfile.open path=%s' % shlex.quote(str(target)),
                'Open goes through Kas\'s own %s bridge (%s), not a command line: this is the Kernel\'s operation that does it.' % (name, bridge))
    if route != 'app' or app is None:
        why = str(reason or 'no app here says it opens this').split(':')[0].strip()
        return '', 'Open asks you to choose an app (Open with): %s.' % why
    try:
        if getattr(app, 'kind', '') == 'pin':argvs = apps_catalog.command([(a, False) for a in app.argv], [str(target)], (), app.name, app.icon, '')
        else:argvs = apps_catalog.command(app.exec, [str(target)], (), app.name, app.icon, app.path)
    except ValueError as exc:
        return '', '%s\'s command line cannot be read: %s.' % (app.name, exc)
    if not argvs:return '', 'Open gives %s no command line.' % app.name
    argv = argvs[0]
    if getattr(app, 'terminal', False):argv = apps_catalog.terminal_argv(argv) or argv
    return (shlex.join(argv), '%s (%s), the app for it here. Put in the line, Enter runs it in the Terminal.'
            % (app.name, getattr(app, 'id', '') or 'its desktop entry'))


def lines_for(path):
    """[{title, line, words}] for a file or a folder: the exact lines it is or runs (see the module note)."""
    path = Path(path);out = []
    if path.is_dir():
        out.append(dict(title='What it is', line=graphite_line(path),
                        words='As a Kas line: Enter on it in the bar\'s line lists this folder on the line page.'))
        out.append(dict(title='In the Terminal', line='cd %s' % shlex.quote(str(path)), words='Goes there in the Terminal (DOS\'s cd too).'))
        return out
    line, words = open_line(path)
    out.append(dict(title='What Open runs', line=line, words=words))
    out.append(dict(title='What it is', line=graphite_line(path),
                    words='As a Kas line: Enter on it in the bar\'s line reads it on the line page.'))
    return out


class CommandCard(QDialog):
    """The card: each line in mono, selectable, with what it does in words, Copy and Put it in the line."""

    def __init__(self, host, path):
        super().__init__(host);self.host = host;self.path = str(path);self.lines = lines_for(path);self.done_words = ''
        self.setWindowTitle('Command · %s' % (Path(path).name or str(path)));self.setObjectName('GraphiteCommandCard')
        self.setAccessibleName('Command: the exact line it is or runs')
        box = QVBoxLayout(self);box.setContentsMargins(18, 16, 18, 12);box.setSpacing(6)
        head = QLabel(shown_path(path), self);head.setObjectName('CommandCardPath');head.setTextInteractionFlags(Qt.TextSelectableByMouse)
        f = head.font();f.setBold(True);head.setFont(f);box.addWidget(head)
        from .shell2 import mono_font
        from .boss_theme import MONO
        from .bar_qt import ink
        c = ink();self.copies = {};self.puts = {}
        for n, row in enumerate(self.lines):
            title = QLabel(row['title'].upper(), self);title.setObjectName('CommandCardTitle')
            t = title.font();t.setPixelSize(max(11, t.pixelSize() - 1) if t.pixelSize() > 0 else 11);t.setLetterSpacing(QFont.AbsoluteSpacing, 0.8);title.setFont(t)
            box.addSpacing(6 if n else 2);box.addWidget(title)
            line = QLabel(row['line'] or '(no line)', self);line.setObjectName('CommandCardLine');line.setFont(mono_font(14))
            line.setStyleSheet("QLabel#CommandCardLine {font-family:'%s'; font-size:14px; color:%s; background:%s; border:1px solid %s;"
                               " border-radius:4px; padding:6px 8px;}" % (MONO, c['text'], c['sidebar'], c['stroke']))      # a line reads as code
            line.setTextFormat(Qt.PlainText);line.setWordWrap(True);line.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
            line.setAccessibleName('%s: %s' % (row['title'], row['line'] or 'none'));box.addWidget(line)
            words = QLabel(row['words'], self);words.setWordWrap(True);words.setObjectName('CommandCardWords');box.addWidget(words)
            presses = QHBoxLayout();presses.setSpacing(8)
            copy = QPushButton('Copy', self);copy.clicked.connect(lambda checked=False, text=row['line']: self.copy(text))
            put = QPushButton('Put it in the line', self);put.clicked.connect(lambda checked=False, text=row['line']: self.put(text))
            for b in (copy, put):
                b.setEnabled(bool(row['line']));b.setAutoDefault(False);presses.addWidget(b)
            presses.addStretch(1);box.addLayout(presses);self.copies[row['title']] = copy;self.puts[row['title']] = put
        note = QLabel('Nothing runs from here: a line runs only when you press Enter on it in the line.', self)
        note.setObjectName('CommandCardNote');note.setWordWrap(True);box.addSpacing(6);box.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, self);buttons.rejected.connect(self.reject);box.addWidget(buttons)
        self.setMinimumWidth(560);self.adjustSize()

    def copy(self, text):
        QApplication.clipboard().setText(text);self.done_words = 'Copied: %s' % text
        try:self.host.statusBar().showMessage(self.done_words, 6000)
        except (AttributeError, RuntimeError):pass
        return text

    def put(self, text):
        from .foot_fold_qt import put_in_line
        self.accept();self.done_words = 'In the line: %s' % text
        return put_in_line(self.host, text)


def show(host, path):
    """The right-click's Command… on `path` (a file or folder). The card, shown; None when the path is not there."""
    if not path or not os.path.exists(str(path)):
        try:host.statusBar().showMessage('Command…: choose a file or folder first.', 6000)
        except (AttributeError, RuntimeError):pass
        return None
    card = CommandCard(host, path);card.show();card.raise_();host._command_card = card
    return card
