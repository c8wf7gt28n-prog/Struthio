"""The utility sandbox in the window (Graphite 1.0, K6): a utility shown before it runs, run sealed on copies, what it
printed and made against your files, and Apply's question.

One working tab in the centre ("Utility · <its name>"), opened from Tools ▸ A Utility on Copies… (on the file in focus,
when it is a file in Files), or by her (show_utility, for a utility she drafted when no registered tool fits). Top to
bottom:

    the head        the utility's name, and whose it is as a word in a box whose edge is its shape: DRAFTED BY THE DESK
                    (a solid edge), DRAFTED BY THE MODEL (dashed, with the model's mark line under its text), WRITTEN BY YOU
                    (dotted)
    your words      what it is for, in your words; with no utility yet, the line to say it, the files it will read, Draft
    what it reads   each file of Files it reads, as the copy it gets (in/<name>) and the revision copied
    what it writes  what it says it makes, in its own folder only
    the seal        no network, only its own folder, no other program; its limits
    what the desk   its imports, a network or a program asked for, a path outside its folder named: words, never the seal
    saw in its text
    its text        read-only, as it will run
    Run sealed on copies · Stop · Close
then, once it has run:
    what happened   a word and a shape (✓ RAN SEALED, ■ STOPPED, ✕ ENDED WITH AN ERROR, ○ NOT RUN), and why
    what it printed
    what the seal stopped    one line each (■ …)
    what it made, against your files   each output with its target, and the difference line by line ('+' added, '-' taken
                    away: a sign before each line as well as its colour)
    Apply to your files… · Keep as a tool… · Throw away the copies
Apply's question is a band in the tab, in plain words, with Apply and Cancel; nothing else in the tab acts while it is up.
It asks every time, whatever her hand's dial says (the Kernel's sandbox.apply is approve scope and always asks). Keep asks
the same way, with the tool's name.

A run and a model's draft go on in a worker of their own (a fresh Kernel on the same workspace), so the window stays live;
Stop (and HALT) end the run's process group.
"""
from __future__ import annotations

import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy,
                               QVBoxLayout, QWidget)

from . import boss_theme as bt
from . import utility_sandbox as us

EDGES = {'desk': 'solid', 'model': 'dashed', 'you': 'dotted'}
SHAPES = {'finished': '✓', 'stopped': '■', 'failed': '✕', 'refused': '○', 'applied': '✓', 'closed': '○', 'running': '…', 'undone': '↶'}      # 1.0 L6c: ↶ PUT BACK
INK = {'finished': 'READY', 'applied': 'READY', 'stopped': 'STOP', 'failed': 'STOP', 'refused': 'QUIET', 'closed': 'QUIET', 'running': 'QUIET', 'undone': 'QUIET'}


def _kernel(host):
    from .engineering_kernel import operator
    kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None:
        from .engine import engineering
        kernel = engineering(host.root)
    return kernel, operator()


def _scale(host):
    try:return float((getattr(host, 'reading_profile', None) or {}).get('ui_pt', 14.0)) / 14.0
    except (TypeError, ValueError):return 1.0


def _colour(name):
    return getattr(bt, name, '#888888')


class Section(QFrame):
    """A heading in small capitals and what follows it."""

    def __init__(self, title, parent=None):
        super().__init__(parent);self.setObjectName('K6Section')
        box = self.box = QVBoxLayout(self);box.setContentsMargins(0, 6, 0, 2);box.setSpacing(3)
        self.title = QLabel(title.upper(), self);self.title.setObjectName('K6Heading');box.addWidget(self.title)

    def line(self, text, name='K6Line', rich=False):
        label = QLabel(self);label.setObjectName(name);label.setWordWrap(True)
        label.setTextFormat(Qt.RichText if rich else Qt.PlainText);label.setText(text)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse);label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.box.addWidget(label)
        return label

    def clear(self):
        while self.box.count() > 1:
            item = self.box.takeAt(1)
            if item.widget() is not None:item.widget().deleteLater()


def _mono(parent, lines=12):
    view = QPlainTextEdit(parent);view.setObjectName('K6Mono');view.setReadOnly(True)
    view.setLineWrapMode(QPlainTextEdit.NoWrap);view.setFocusPolicy(Qt.TabFocus)
    view.setMinimumHeight(60);view.setProperty('lines', lines)
    return view


class UtilityTab(QWidget):
    """One utility: shown before it runs, run sealed, what it did, and Apply's question."""

    def __init__(self, host, utility=None, inputs=(), objective=''):
        super().__init__();self.host = host;self.setObjectName('K6Utility')
        self.setProperty('ledgerRoom', True)      # a tab of its own until Close: never the Preview, never replaced by another
        self.utility = utility;self.run_view = None;self.inputs = list(inputs);self.worker = None;self.before = set()
        self.question = None
        outer = QVBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self);scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);outer.addWidget(scroll)
        page = QWidget();page.setObjectName('K6Page');scroll.setWidget(page)
        box = self.box = QVBoxLayout(page);box.setContentsMargins(28, 18, 28, 18);box.setSpacing(6)
        head = QHBoxLayout();head.setSpacing(10)
        self.kicker = QLabel('A UTILITY ON COPIES', page);self.kicker.setObjectName('K6Kicker');head.addWidget(self.kicker)
        self.mark = QLabel('', page);self.mark.setObjectName('K6Mark');head.addWidget(self.mark)
        self.state = QLabel('', page);self.state.setObjectName('K6State');head.addWidget(self.state)
        head.addStretch(1);box.addLayout(head)
        self.name = QLabel('', page);self.name.setObjectName('K6Name');self.name.setWordWrap(True);box.addWidget(self.name)
        self.words = QLabel('', page);self.words.setObjectName('K6Words');self.words.setWordWrap(True);box.addWidget(self.words)
        # with no utility yet: say it, and Draft
        self.ask = QFrame(page);self.ask.setObjectName('K6Ask');ab = QVBoxLayout(self.ask);ab.setContentsMargins(0, 4, 0, 4);ab.setSpacing(4)
        self.ask_files = QLabel('', self.ask);self.ask_files.setObjectName('K6Line');self.ask_files.setWordWrap(True);ab.addWidget(self.ask_files)
        row = QHBoxLayout();self.objective = QLineEdit(objective, self.ask);self.objective.setObjectName('K6Field')
        self.objective.setPlaceholderText('What should it do? (total the current_mA column, count the rows, sort by time_ms, …)')
        self.objective.returnPressed.connect(self.draft);row.addWidget(self.objective, 1)
        self.draft_button = self._button('Draft', self.draft, self.ask);row.addWidget(self.draft_button);ab.addLayout(row)
        self.ask_note = QLabel('', self.ask);self.ask_note.setObjectName('K6Quiet');self.ask_note.setWordWrap(True);ab.addWidget(self.ask_note)
        box.addWidget(self.ask)
        self.reads = Section('What it reads', page);box.addWidget(self.reads)
        self.writes = Section('What it writes', page);box.addWidget(self.writes)
        self.seal = Section('The seal', page);box.addWidget(self.seal)
        self.saw = Section('What the desk saw in its text', page);box.addWidget(self.saw)
        self.text = Section('Its text', page);box.addWidget(self.text)
        self.code = _mono(self.text, 16);self.text.box.addWidget(self.code)
        self.model_mark = None
        row = QHBoxLayout();row.setSpacing(8)
        self.run_button = self._button('Run sealed on copies', self.run, page, primary=True);row.addWidget(self.run_button)
        self.stop_button = self._button('Stop', self.stop, page);row.addWidget(self.stop_button);self.stop_button.hide()
        row.addStretch(1);self.close_button = self._button('Close', self.close_tab, page);row.addWidget(self.close_button)
        box.addLayout(row)
        # after it ran
        self.after = QFrame(page);self.after.setObjectName('K6After');af = QVBoxLayout(self.after);af.setContentsMargins(0, 8, 0, 0);af.setSpacing(4)
        self.happened = Section('What happened', self.after);af.addWidget(self.happened)
        self.printed = Section('What it printed', self.after);af.addWidget(self.printed)
        self.out = _mono(self.printed, 6);self.printed.box.addWidget(self.out)
        self.stopped = Section('What the seal stopped', self.after);af.addWidget(self.stopped)
        self.made = Section('What it made, against your files', self.after);af.addWidget(self.made)
        self.made_list = QWidget(self.made);ml = self.made_lines = QVBoxLayout(self.made_list);ml.setContentsMargins(0, 0, 0, 0);ml.setSpacing(3)
        self.made.box.addWidget(self.made_list)
        self.diff = _mono(self.made, 12);self.made.box.addWidget(self.diff)
        self.question = QFrame(self.after);self.question.setObjectName('K6Question')
        qb = QVBoxLayout(self.question);qb.setContentsMargins(14, 10, 14, 10);qb.setSpacing(6)
        self.q_title = QLabel('', self.question);self.q_title.setObjectName('K6QTitle');self.q_title.setWordWrap(True);qb.addWidget(self.q_title)
        self.q_words = QLabel('', self.question);self.q_words.setObjectName('K6Line');self.q_words.setWordWrap(True);qb.addWidget(self.q_words)
        self.q_name = QLineEdit(self.question);self.q_name.setObjectName('K6Field');qb.addWidget(self.q_name);self.q_name.hide()
        qr = QHBoxLayout();qr.setSpacing(8)
        self.q_yes = self._button('Apply', lambda: None, self.question, primary=True);qr.addWidget(self.q_yes)
        self.q_no = self._button('Cancel', self.put_question_away, self.question);qr.addWidget(self.q_no);qr.addStretch(1);qb.addLayout(qr)
        self.question.hide();af.addWidget(self.question)
        self.actions = QWidget(self.after);row = QHBoxLayout(self.actions);row.setContentsMargins(0, 0, 0, 0);row.setSpacing(8)
        self.apply_button = self._button('Apply to your files…', self.ask_apply, self.actions, primary=True);row.addWidget(self.apply_button)
        self.keep_button = self._button('Keep as a tool…', self.ask_keep, self.actions);row.addWidget(self.keep_button)
        self.throw_button = self._button('Throw away the copies', self.throw_away, self.actions);row.addWidget(self.throw_button)
        row.addStretch(1);af.addWidget(self.actions)
        self.undo_row = QWidget(self.after);undo_row = QHBoxLayout(self.undo_row);undo_row.setContentsMargins(0, 0, 0, 0)      # 1.0 L6c: on a row of its own
        self.undo_button = self._button('Undo the apply', self.do_undo, self.undo_row);undo_row.addWidget(self.undo_button);undo_row.addStretch(1)
        self.undo_button.setToolTip('What Apply made new goes into DELETE; a file it changed gets the revision before back. '
                                    'Anything changed since is left as it is, and named.');self.undo_row.hide();af.addWidget(self.undo_row)
        self.after_note = QLabel('', self.after);self.after_note.setObjectName('K6Quiet');self.after_note.setWordWrap(True);af.addWidget(self.after_note)
        box.addWidget(self.after);self.after.hide()
        box.addStretch(1)
        self.restyle()
        if utility:self.show_utility(utility)
        else:self.show_ask()

    # -- look ---------------------------------------------------------------------------------------------------------------
    def _button(self, text, fn, parent, primary=False):
        b = QPushButton(text, parent);b.setObjectName('K6Primary' if primary else 'K6Button');b.setCursor(Qt.PointingHandCursor)
        b.setFocusPolicy(Qt.TabFocus);b.clicked.connect(lambda _=False: fn());return b

    def restyle(self):
        s = _scale(self.host);px = lambda n: max(10, round(n * s))   # noqa: E731
        self.setStyleSheet(
            'QWidget#K6Page {background:%(CARD)s;} QScrollArea {background:%(CARD)s;border:0;} '
            'QLabel {background:transparent;color:%(TEXT)s;font-family:"%(FACE)s";font-size:%(body)dpx;} '
            'QLabel#K6Kicker {color:%(QUIET)s;font-size:%(small)dpx;letter-spacing:1px;} '
            'QLabel#K6Name {font-family:"%(DISPLAY)s";font-size:%(big)dpx;font-weight:600;} '
            'QLabel#K6Words, QLabel#K6Quiet {color:%(QUIET)s;} '
            'QLabel#K6Heading {color:%(VIOLET)s;font-size:%(small)dpx;font-weight:600;letter-spacing:1px;} '
            'QLabel#K6Flag {color:%(AMBER_TEXT)s;} QLabel#K6Stop {color:%(STOP)s;} '
            'QLabel#K6QTitle {font-size:%(title)dpx;font-weight:600;color:%(TEXT)s;} '
            'QFrame#K6Question {background:%(RAISED)s;border:2px solid %(OWNER)s;border-radius:2px;} '
            'QPlainTextEdit#K6Mono {font-family:"%(MONO)s";font-size:%(mono)dpx;color:%(TEXT)s;background:%(PANEL)s;'
            'border:1px solid %(LINE)s;border-radius:0;selection-background-color:%(AMBER_SOFT)s;} '
            'QLineEdit#K6Field {font-family:"%(FACE)s";font-size:%(body)dpx;color:%(TEXT)s;background:%(PANEL)s;border:1px solid %(LINE_STRONG)s;'
            'padding:4px 6px;} '
            'QPushButton#K6Button, QPushButton#K6Primary {font-family:"%(FACE)s";font-size:%(body)dpx;color:%(TEXT)s;background:%(RAISED)s;'
            'border:1px solid %(LINE_STRONG)s;border-radius:2px;padding:5px 14px;} '
            'QPushButton#K6Primary {border:1px solid %(TEAL_EDGE)s;color:%(TEAL_TEXT)s;background:%(TEAL_SOFT)s;font-weight:600;} '
            'QPushButton#K6Button:hover, QPushButton#K6Primary:hover {background:%(TEAL_SOFT)s;border-color:%(TEAL_EDGE)s;color:%(TEAL_TEXT)s;} '
            'QPushButton#K6Button:disabled, QPushButton#K6Primary:disabled {color:%(FAINT)s;border-color:%(LINE)s;background:%(PANEL)s;'
            'font-weight:400;}' % dict(
                {k: _colour(k) for k in ('CARD', 'TEXT', 'QUIET', 'FAINT', 'VIOLET', 'AMBER_TEXT', 'AMBER_SOFT', 'STOP', 'RAISED', 'OWNER', 'PANEL',
                                         'LINE', 'LINE_STRONG', 'TEAL_EDGE', 'TEAL_TEXT', 'TEAL_SOFT')},
                FACE=bt.FACE, DISPLAY=bt.DISPLAY, MONO=bt.MONO, body=px(14), small=px(12), big=px(22), title=px(16), mono=px(13)))
        for view in (self.code, self.out, self.diff):
            fm = view.fontMetrics();view.setFixedHeight(fm.lineSpacing() * int(view.property('lines') or 8) + 14)

    def _chip(self, label, word, edge, ink):
        label.setText(word)
        label.setStyleSheet('QLabel {color:%s;border:1px %s %s;padding:1px 8px;font-size:%dpx;letter-spacing:1px;font-weight:600;}'
                            % (_colour(ink), edge, _colour(ink if ink != 'QUIET' else 'LINE_STRONG'), max(10, round(12 * _scale(self.host)))))
        label.setVisible(bool(word))

    def title(self):
        return 'Utility · %s' % ((self.utility or {}).get('name') or 'new')[:40]

    # -- before it runs -----------------------------------------------------------------------------------------------------
    def show_ask(self):
        self.name.setText('A utility, when no tool of hers fits');self._chip(self.mark, '', 'solid', 'QUIET');self._chip(self.state, '', 'solid', 'QUIET')
        self.words.setText('Say what it should do with the file. The desk drafts it when your words read as one of its own (total a column, '
                           'count the rows, sort by a column); otherwise the model drafts it, when one is running. Either way you see it '
                           'before it runs, and it runs only sealed, on copies.')
        files = ', '.join(self.inputs) if self.inputs else 'none yet: select a file in Files first'
        if len(self.inputs) > 6:      # 1.0 L6c: a folder's worth: the first few, and how many in all
            files = '%s and %d more (%d files in all)' % (', '.join(self.inputs[:4]), len(self.inputs) - 4, len(self.inputs))
        self.ask_files.setText('It will read a copy of: ' + files);self.ask.show();self.draft_button.setEnabled(bool(self.inputs))
        for part in (self.reads, self.writes, self.seal, self.saw, self.text, self.run_button):part.hide()

    def draft(self):
        words = self.objective.text().strip()
        if not words or not self.inputs:return
        self.draft_button.setEnabled(False);self.ask_note.setText('Drafting…')
        from .engineering_kernel import Kernel, operator
        root = _kernel(self.host)[0].root;result = {};inputs = list(self.inputs)

        def work():
            try:result['answer'] = Kernel(root).dispatch('sandbox.draft', {'objective': words, 'inputs': inputs}, operator())
            except Exception as exc:  # noqa: BLE001
                result['answer'] = {'ok': False, 'error': {'message': str(exc)}}
        self.worker = threading.Thread(target=work, name='k6-draft', daemon=True);self.worker.start()

        def check():
            if self.worker is not None and self.worker.is_alive():QTimer.singleShot(250, check);return
            self.worker = None;answer = result.get('answer') or {}
            self.draft_button.setEnabled(True)
            if not answer.get('ok'):
                self.ask_note.setText(str((answer.get('error') or {}).get('message', '')).split(': ', 1)[-1]);return
            self.ask_note.setText('');self.show_utility(answer['result'])
        QTimer.singleShot(250, check)

    def show_utility(self, u):
        self.utility = u;self.ask.hide()
        for part in (self.reads, self.writes, self.seal, self.saw, self.text, self.run_button):part.show()
        self.name.setText(u.get('name') or 'A utility')
        self._chip(self.mark, u.get('mark') or u.get('by_words', '').upper(), EDGES.get(u.get('by'), 'solid'), 'HONEY' if u.get('by') == 'model' else 'QUIET')
        self._chip(self.state, '', 'solid', 'QUIET')
        self.words.setText('Your words: “%s”. It runs only sealed, on copies of what it reads; nothing of yours changes unless you apply '
                           'what it makes, and Apply always asks.' % (u.get('objective') or '')[:300])
        self.reads.clear()
        for r in u.get('reads', ()):
            self.reads.line('%s — a copy, as %s (revision %s…, %d bytes)' % (r['path'], r['copy'], r['sha256'][:12], r['bytes']))
        self.writes.clear();self.writes.line(u.get('writes_words', ''))
        self.seal.clear()
        for w in u.get('seal', ()):self.seal.line(w)
        self.seal.line(u.get('limit_words', ''), 'K6Quiet')
        self.saw.clear()
        flags = u.get('flags') or ()
        if not flags:self.saw.line('Only Python: %s. Nothing in its text asks for the network, another program or a place outside its folder.'
                                   % (', '.join(u.get('imports') or ()) or 'no imports'))
        for f in flags:self.saw.line('▲ ' + f['words'], 'K6Flag')
        self.code.setPlainText(u.get('source') or '')
        if self.model_mark is not None:self.model_mark.deleteLater();self.model_mark = None
        if u.get('by') == 'model':
            try:
                from .model_marks_qt import MarkLine
                self.model_mark = MarkLine('DRAFTED');self.text.box.addWidget(self.model_mark)
            except Exception:  # noqa: BLE001 - the chip above still says whose it is
                self.model_mark = None
        self.run_button.setEnabled(True);self.after.hide()
        self._seen(u)
        self._retitle()

    def _seen(self, u):
        """The window showed it: its text, what it reads and writes (sandbox.run's precondition)."""
        try:
            kernel, owner = _kernel(self.host)
            kernel.dispatch('sandbox.seen', {'utility': u['id'], 'source_sha256': u['sha256']}, owner)
        except Exception:  # noqa: BLE001 - a run that finds it not shown is refused, and says so
            pass

    def _retitle(self):
        tabs = getattr(self.host, 'tabs', None)
        try:
            at = tabs.indexOf(self) if tabs is not None else -1
            if at >= 0:tabs.setTabText(at, self.title())
        except RuntimeError:
            pass

    # -- the run ------------------------------------------------------------------------------------------------------------
    def run(self):
        u = self.utility
        if not u or self.worker is not None:return
        self.run_button.setEnabled(False);self.stop_button.show();self._chip(self.state, '… RUNNING', 'dotted', 'QUIET')
        from .engineering_kernel import Kernel, operator
        root = _kernel(self.host)[0].root;result = {};self.before = set(us.running())
        args = {'utility': u['id'], 'expected_source_sha256': u['sha256']}

        def work():
            try:result['answer'] = Kernel(root).dispatch('sandbox.run', args, operator())
            except Exception as exc:  # noqa: BLE001
                result['answer'] = {'ok': False, 'error': {'message': str(exc)}}
        self.worker = threading.Thread(target=work, name='k6-run', daemon=True);self.worker.start()

        def check():
            if self.worker is not None and self.worker.is_alive():QTimer.singleShot(250, check);return
            self.worker = None;self.stop_button.hide();self.run_button.setEnabled(True)
            answer = result.get('answer') or {}
            if not answer.get('ok'):
                self._chip(self.state, '○ NOT RUN', 'solid', 'QUIET')
                self.show_run({'state': 'refused', 'state_word': 'NOT RUN', 'words': str((answer.get('error') or {}).get('message', '')).split(': ', 1)[-1],
                               'stdout': '', 'stopped': [], 'outputs': [], 'applicable': False, 'why_not': ''})
                return
            self.show_run(answer['result'])
        QTimer.singleShot(250, check)

    def stop(self):
        for run_id in set(us.running()) - self.before:us.stop(run_id)

    def show_run(self, r):
        self.run_view = r;self.after.show();self.put_question_away()
        state = r.get('state', 'refused')
        word = '%s %s' % (SHAPES.get(state, '·'), r.get('state_word', state.upper()))
        self._chip(self.state, word, 'solid', INK.get(state, 'QUIET'))
        self.happened.clear()
        self.happened.line(word, 'K6Stop' if state in ('stopped', 'failed') else 'K6Line')
        self.happened.line(r.get('words', ''))
        if r.get('ms'):self.happened.line('%d ms, exit %s, sealed with %s.' % (r['ms'], r.get('exit'), {'landlock': 'Landlock, a network of its own and a call filter',
                                                                                     'bubblewrap': 'bubblewrap and a call filter'}.get(r.get('mechanism'), '—')), 'K6Quiet')
        for i in r.get('inputs', ()):
            if i.get('since'):self.happened.line('%s: %s.' % (i['path'], i['since']), 'K6Quiet')
        text = r.get('stdout') or ''
        if r.get('stderr') and state != 'finished':
            last = '\n'.join(r['stderr'].strip().splitlines()[-6:])
            text += ('\n' if text else '(it printed nothing)\n') + 'Its error, last lines:\n' + last
        self.out.setPlainText(text or '(it printed nothing)')
        self.stopped.clear()
        for s in r.get('stopped', ()):self.stopped.line('■ ' + s['words'], 'K6Stop')
        if r.get('killed'):self.stopped.line('■ ' + r['killed'][0].upper() + r['killed'][1:] + '.', 'K6Stop')
        self.stopped.setVisible(bool(r.get('stopped') or r.get('killed')))
        while self.made_lines.count():
            item = self.made_lines.takeAt(0)
            if item.widget() is not None:item.widget().deleteLater()
        outs = r.get('outputs') or ()
        for m in outs:self.made_lines.addWidget(self._made_line(m))
        if not outs:
            none = QLabel('It made no file.', self.made_list);none.setObjectName('K6Quiet');self.made_lines.addWidget(none)
        self.show_diff(outs)
        self.diff.setVisible(any((m.get('diff') or {}).get('lines') for m in outs))
        self.sync_buttons()
        self.after_note.setText('' if r.get('applicable') else (r.get('why_not') or ''))

    def sync_buttons(self):
        r = self.run_view or {};state = r.get('state')
        self.run_button.setEnabled(bool(self.utility) and self.worker is None);self.close_button.setEnabled(True)
        self.apply_button.setEnabled(bool(r.get('applicable')))
        self.keep_button.setEnabled(state in ('finished', 'applied') and not (self.utility or {}).get('kept'))
        self.throw_button.setEnabled(bool(r.get('id')) and state not in ('refused', 'closed', 'running') and not r.get('thrown'))
        self.undo_row.setVisible(bool(r.get('undoable')));self.undo_button.setEnabled(bool(r.get('undoable')))      # 1.0 L6c

    def _made_line(self, m):
        label = QLabel(('↻ ' if m.get('kind') == 'revision' else '+ ') + m.get('words', m.get('name', '')), self.made_list)
        label.setWordWrap(True);label.setObjectName('K6Line');label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        return label

    def show_diff(self, outs):
        self.diff.clear();cursor = self.diff.textCursor()
        plain = QTextCharFormat();plain.setForeground(QColor(_colour('TEXT')))
        added = QTextCharFormat();added.setForeground(QColor(_colour('READY')));added.setFontWeight(QFont.DemiBold)
        removed = QTextCharFormat();removed.setForeground(QColor(_colour('STOP')))
        quiet = QTextCharFormat();quiet.setForeground(QColor(_colour('QUIET')))
        first = True
        for m in outs:
            lines = (m.get('diff') or {}).get('lines') or ()
            if not lines:continue
            for line in lines:
                if not first:cursor.insertText('\n', plain)
                first = False
                fmt = quiet if line.startswith(('+++', '---', '@@')) else added if line.startswith('+') else removed if line.startswith('-') else plain
                cursor.insertText(line, fmt)
        self.diff.moveCursor(QTextCursor.Start)

    # -- Apply's question, and Keep's ---------------------------------------------------------------------------------------
    def _enable_all(self, on):
        for b in (self.run_button, self.apply_button, self.keep_button, self.throw_button, self.close_button, self.undo_button):b.setEnabled(on)  # 1.0 L6c: and Undo

    def ask_apply(self):
        r = self.run_view
        if not r or not r.get('applicable'):return
        plan = us.plan_apply(None, r)
        self.q_title.setText('Apply what the utility made to your real files?')
        lines = ['• ' + p['words'] for p in plan]
        if len(lines) > 6:lines = lines[:5] + ['• and %d more, each as above' % (len(lines) - 5)]      # 1.0 L6c: a folder's worth
        self.q_words.setText('\n'.join(lines) + '\n\nIt was %s and ran sealed on copies. The new revision is recorded and '
                             'read back from the disk. This always asks, whatever her hand\'s dial says.' % (self.utility or {}).get('by_words', 'drafted'))
        self.q_name.hide();self.q_yes.setText('Apply')
        self._reconnect(lambda: self.do_apply(plan));self._show_question()

    def ask_keep(self):
        u = self.utility or {}
        self.q_title.setText('Keep this utility as a tool of yours?')
        self.q_words.setText('It becomes a registered tool with a number of its own and its own grant: “run it on copies of its inputs”. '
                             'It still runs only sealed, on copies, and applying what it makes still asks every time. Its name:')
        self.q_name.setText((u.get('name') or 'my utility')[:60]);self.q_name.show();self.q_yes.setText('Keep')
        self._reconnect(self.do_keep);self._show_question()

    def _reconnect(self, fn):
        try:self.q_yes.clicked.disconnect()
        except (RuntimeError, TypeError):pass
        self.q_yes.clicked.connect(lambda _=False: fn())

    def _show_question(self):
        self._enable_all(False);self.actions.hide();self.question.show();self.q_yes.setEnabled(True);self.q_no.setEnabled(True)
        QTimer.singleShot(0, lambda: self.q_no.setFocus())

    def put_question_away(self):
        if self.question is not None:self.question.hide();self.actions.show()
        self.sync_buttons()

    def do_apply(self, plan):
        kernel, owner = _kernel(self.host)
        answer = kernel.dispatch('sandbox.apply', {'run': self.run_view['id'], 'outputs': [{'name': p['name'], 'sha256': p['sha256']} for p in plan]}, owner)
        self.put_question_away()
        if answer.get('ok'):
            self.run_view = dict(self.run_view, applicable=False, state='applied', state_word='APPLIED', undoable=True)      # 1.0 L6c: and its Undo
            self._chip(self.state, '✓ APPLIED', 'solid', 'READY');self.apply_button.setEnabled(False);self.sync_buttons()
            self.after_note.setText(answer['result'].get('words', ''))
            self._tell(answer['result'].get('words', ''))
        else:
            self.after_note.setText('Not applied: ' + str((answer.get('error') or {}).get('message', '')).split(': ', 1)[-1])

    def do_undo(self):
        """1.0 L6c: Undo the apply, your press: the files Apply made new into DELETE, the revisions it replaced back."""
        r = self.run_view or {}
        if not r.get('undoable'):return
        kernel, owner = _kernel(self.host)
        answer = kernel.dispatch('sandbox.undo', {'run': r['id']}, owner)
        if answer.get('ok'):
            got = answer['result'];whole = got.get('state') == 'undone'
            self.run_view = dict(r, state=got.get('state', 'applied'), undoable=not whole, state_word='PUT BACK' if whole else 'APPLIED')
            if whole:self._chip(self.state, '↶ PUT BACK', 'solid', 'QUIET')
            self.sync_buttons();self.after_note.setText(got.get('words', ''));self._tell(got.get('words', ''))
        else:
            self.after_note.setText('Not put back: ' + str((answer.get('error') or {}).get('message', '')).split(': ', 1)[-1])

    def do_keep(self):
        kernel, owner = _kernel(self.host)
        answer = kernel.dispatch('sandbox.keep', {'utility': self.utility['id'], 'name': self.q_name.text().strip() or 'my utility'}, owner)
        self.put_question_away()
        if answer.get('ok'):
            self.utility = dict(self.utility, kept=answer['result']['key']);self.keep_button.setEnabled(False)
            self.after_note.setText(answer['result'].get('words', ''));self._tell(answer['result'].get('words', ''))
        else:
            self.after_note.setText('Not kept: ' + str((answer.get('error') or {}).get('message', '')).split(': ', 1)[-1])

    def throw_away(self):
        r = self.run_view or {}
        if not r.get('id'):return
        kernel, owner = _kernel(self.host)
        answer = kernel.dispatch('sandbox.close', {'run': r['id']}, owner)
        if answer.get('ok'):
            self.run_view = dict(r, applicable=False, thrown=True);self.sync_buttons()
            self.after_note.setText(answer['result'].get('words', ''))

    def _tell(self, words):
        column = getattr(self.host, 'her_column', None)
        try:
            if column is not None:column.say_words(words);return
        except Exception:  # noqa: BLE001
            pass
        try:self.host.statusBar().showMessage(words, 10000)
        except Exception:  # noqa: BLE001
            pass

    def close_tab(self):
        if self.worker is not None:self.stop()
        tabs = getattr(self.host, 'tabs', None)
        if tabs is not None and tabs.indexOf(self) >= 0:tabs.removeTab(tabs.indexOf(self))
        self.deleteLater()


# -- opening it ---------------------------------------------------------------------------------------------------------------
def _focused_file(host):
    """The path in Files of the object in focus, when it is a file (L1's navigation), else ''."""
    try:
        living = getattr(host, 'living_nav', None)
        focus = living.nav.focus if living is not None else ''
        if not focus or not str(focus).startswith('fileid:'):return ''
        from . import living_nav
        kernel, _ = _kernel(host)
        found = living_nav.get(kernel, ident=focus)
        return found['path'] if found.get('kind') == 'file' else ''
    except Exception:  # noqa: BLE001 - no focus that is a file: the tab asks for one
        return ''


def _focused_files(host):
    """1.0 L6c: the files the tab reads: the file in focus, or, with a folder in focus, its files (a folder's worth: up to
    utility_sandbox.MOST_INPUTS, by name; dot-names and folders left out)."""
    one = _focused_file(host)
    if one:return [one]
    try:
        living = getattr(host, 'living_nav', None)
        focus = living.nav.focus if living is not None else ''
        if not focus or not str(focus).startswith('fileid:'):return []
        from pathlib import Path

        from . import files_service, living_nav
        kernel, _ = _kernel(host)
        found = living_nav.get(kernel, ident=focus)
        if found.get('kind') != 'folder':return []
        folder = files_service.resolve(kernel, found['path'])
        files = sorted(p for p in folder.iterdir() if p.is_file() and not p.is_symlink() and not p.name.startswith('.'))
        return [files_service.place_of(kernel, p) for p in files[:us.MOST_INPUTS]]
    except Exception:  # noqa: BLE001 - no folder in focus to read: the tab asks for a file
        return []


def _place(host, tab):
    try:host._close_start()
    except Exception:  # noqa: BLE001
        pass
    tabs = getattr(host, 'tabs', None)
    if tabs is None:
        tab.setWindowTitle(tab.title());tab.resize(1000, 760);tab.show();return tab
    tabs.addTab(tab, tab.title());tabs.setCurrentWidget(tab)
    return tab


def open_panel(host, inputs=None, objective=''):
    """Tools ▸ A Utility on Copies…: a new utility tab on the file in focus (or the files given)."""
    files = list(inputs or _focused_files(host))      # 1.0 L6c: a folder in focus gives its files
    return _place(host, UtilityTab(host, None, files, objective))


def show_utility(host, utility):
    """A utility she (or the desk) drafted, shown before it runs: `utility` is sandbox.draft's result, or its id."""
    if isinstance(utility, str):
        kernel, owner = _kernel(host)
        answer = kernel.dispatch('sandbox.get', {'utility': utility}, owner)
        if not answer.get('ok'):return None
        utility = answer['result']['utility']
    return _place(host, UtilityTab(host, utility))
