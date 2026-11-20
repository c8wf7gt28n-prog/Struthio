"""The Brain room's "Check her model on this machine" (0.8.7, slice A5, lane A): one button, the run shown stage by stage,
the card, the exam card per model, and "Use the measured settings?", each a change at the owner's hand with Undo.

The check itself runs in a process of its own (python -B -m workbench.model_check), on an invented workspace. This
panel only: starts it with the selected model and the launch defaults on screen; pauses it while the desk is in use (a
pause file in the run folder, from the desk's own touch lease); measures its own event loop while the check reads 3,000
tokens (S4) and writes desk_stalls.json; shows what would leave (the card and the file) before anything does; and, on
the owner's click, applies a proposed setting (ledger.settings.set) or undoes it (ledger.settings.undo).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QProcess, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout,
                               QWidget)

from . import model_check

BUTTON = 'Check her model on this machine'
ROOT = Path(__file__).resolve().parent.parent


class CheckPanel(QWidget):
    def __init__(self, tab):
        super().__init__();self.tab = tab;self.kernel = tab.kernel;self.principal = tab.principal
        self.process = None;self.run = None;self.report = None;self.undo_ids = {}
        layout = QVBoxLayout(self);layout.setContentsMargins(6, 6, 6, 6)
        intro = QLabel('Measures her model on this computer with invented questions and an invented workspace: about 20 to 30 '
                       'minutes awake (estimated). It changes no setting of yours by itself, installs nothing, downloads nothing '
                       'and does not touch your workspace. Using the desk pauses it; it runs only on mains power. It ends with '
                       'one file to send back and a plain card.')
        intro.setWordWrap(True);layout.addWidget(intro)
        row = QHBoxLayout()
        self.start = QPushButton(BUTTON);self.start.setAccessibleName(BUTTON);self.start.clicked.connect(self.begin);row.addWidget(self.start)
        self.stop_button = QPushButton('Stop the check');self.stop_button.setAccessibleName('Stop the check')
        self.stop_button.clicked.connect(self.halt);self.stop_button.setEnabled(False);row.addWidget(self.stop_button)
        self.folder = QPushButton('Show the folder');self.folder.setAccessibleName('Show the folder the check wrote')
        self.folder.clicked.connect(self.show_folder);self.folder.setEnabled(False);row.addWidget(self.folder)
        row.addStretch(1);layout.addLayout(row)
        self.overnight = QCheckBox('Also overnight, on mains: the full exam and the I05 experiment (hours)')
        self.overnight.setAccessibleName('Also run the overnight part');layout.addWidget(self.overnight)
        self.own = QCheckBox('Include my own paper: questions I answered myself (its results stay on this computer)')
        self.own.setAccessibleName('Include my own paper');layout.addWidget(self.own)
        self.stage_line = QLabel('');self.stage_line.setWordWrap(True);self.stage_line.setAccessibleName('Model check progress')
        layout.addWidget(self.stage_line)
        self.card = QPlainTextEdit();self.card.setReadOnly(True);self.card.setAccessibleName('The model check card')
        self.card.setPlaceholderText('The card appears here when the check ends: exactly what the file for sending holds, in words.')
        layout.addWidget(self.card, 1)
        self.proposals = QVBoxLayout();layout.addLayout(self.proposals)
        exam_row = QHBoxLayout();exam = QPushButton('Show the exam card');exam.setAccessibleName('Show the exam card for this model')
        exam.clicked.connect(self.show_exam);exam_row.addWidget(exam);exam_row.addStretch(1);layout.addLayout(exam_row)
        self.exam_words = QLabel('');self.exam_words.setWordWrap(True);self.exam_words.setAccessibleName('The exam card');layout.addWidget(self.exam_words)
        self.pause_timer = QTimer(self);self.pause_timer.setInterval(1000);self.pause_timer.timeout.connect(self.desk_touch)
        self.meter = QTimer(self);self.meter.setInterval(10);self.meter.timeout.connect(self.tick);self.clock = QElapsedTimer()
        self.longest = 0;self.over = 0

    # -- start, stop -------------------------------------------------------------------------------------------------
    def model_file(self):
        from . import local_brain
        ident = getattr(self.tab, '_selected_id', None)
        if not ident:return None
        try:
            value = local_brain.model(self.kernel, ident)
        except (ValueError, KeyError):
            return None
        return next((Path(f['path']) for f in value.get('files') or [] if f.get('role') == 'weights'), None)

    def begin(self):
        model = self.model_file()
        if model is None or not model.is_file():
            self.stage_line.setText('Choose a registered model above first; the check measures that one.');return
        if model_check.power()['on_mains'] is False:
            self.stage_line.setText('The check runs on mains power only. Plug the computer in, then start it.');return
        text = model_check.plan_text(self.overnight.isChecked())
        if QMessageBox.question(self, BUTTON, text + '\n\nStart it now?') != QMessageBox.Yes:return
        self.run = model_check.default_out();self.run.mkdir(parents=True, exist_ok=True)
        args = ['-B', '-m', 'workbench.model_check', '--model', str(model), '--out', str(self.run), '--from-room', '--progress-json',
                '--pause-file', str(self.run / 'pause'), '--context', str(self.tab.context.value()), '--threads',
                str(self.tab.threads.value()), '--backend', str(self.tab.backend.currentData() or 'AUTO')]
        if self.tab.memory.value():args += ['--memory-mb', str(self.tab.memory.value())]
        if self.overnight.isChecked():args.append('--overnight')
        if self.own.isChecked():
            from . import model_exam
            paper, why = model_exam.own_paper(self.kernel, self.principal.identity)
            if paper is not None and paper.items:
                path = self.run / 'own_items.local.json';path.write_text(json.dumps(paper.items), encoding='utf-8');path.chmod(0o600)
                args += ['--own-items', str(path)]
            else:
                self.stage_line.setText('Your own paper cannot be made in this build yet; the check runs without it.')
        self.process = QProcess(self);self.process.setWorkingDirectory(str(ROOT))
        self.process.readyReadStandardOutput.connect(self.read);self.process.finished.connect(self.finished)
        self.process.start(sys.executable, args)
        self.start.setEnabled(False);self.stop_button.setEnabled(True);self.card.clear();self.clear_proposals()
        self.pause_timer.start();self.stage_line.setText('Started. ' + text.splitlines()[-2])

    def halt(self):
        if self.process is not None:self.process.kill()

    def desk_touch(self):
        """The desk's own touch lease (resource_control.foreground) sets the pause file; the check waits while it is there."""
        if self.run is None:return
        from .resource_control import foreground
        try:
            with self.kernel.db() as db:touched = foreground(db)
        except Exception:  # noqa: BLE001 - an unreadable lease pauses nothing
            touched = False
        pause = self.run / 'pause'
        if touched:pause.touch()
        else:pause.unlink(missing_ok=True)

    # -- its lines -----------------------------------------------------------------------------------------------------
    def read(self):
        for raw in bytes(self.process.readAllStandardOutput()).decode('utf-8', 'replace').splitlines():
            if raw.startswith('@@ '):
                try:
                    event = json.loads(raw[3:])
                except ValueError:
                    continue
                self.on_event(event)
            elif raw.strip():
                self.stage_line.setText(raw.strip()[:300])

    def on_event(self, event):
        if event.get('event') == 'desk_read_begins':
            self.longest = 0;self.over = 0;self.clock.start();self.meter.start()
        elif event.get('event') == 'desk_read_ends':
            self.meter.stop()
            (self.run / 'desk_stalls.json').write_text(json.dumps({'longest_ms': self.longest, 'over_50': self.over}), encoding='utf-8')
        elif event.get('stage') and event.get('event') == 'begins':
            words = dict((s[0], s[1]) for s in model_check.STAGES).get(event['stage'], '')
            self.stage_line.setText('%s · %s' % (event['stage'], words))

    def tick(self):
        gap = self.clock.restart() - 10
        if gap > self.longest:self.longest = int(gap)
        if gap > 50:self.over += 1

    def finished(self, *args):
        self.pause_timer.stop();self.meter.stop();self.start.setEnabled(True);self.stop_button.setEnabled(False)
        if self.run is None:return
        (self.run / 'pause').unlink(missing_ok=True)
        sent = sorted((self.run / 'for-sending').glob('model-check-*.json')) if (self.run / 'for-sending').is_dir() else []
        if not sent:
            self.stage_line.setText('The check ended without a file for sending (stopped, or the privacy scan held it back).');return
        self.report = json.loads(sent[-1].read_text(encoding='utf-8'))
        card = sent[-1].with_suffix('.txt')
        self.card.setPlainText(card.read_text(encoding='utf-8') if card.exists() else '')
        self.folder.setEnabled(True)
        self.stage_line.setText('Done. This is exactly what the file for sending holds; nothing has left this computer.')
        self.keep_exam()
        self.offer()

    def keep_exam(self):
        """The exam's results go into this computer's exam record for the model key (never into the file for sending)."""
        path = self.run / 'exam_results.local.json'
        if not path.exists():return
        from . import model_exam
        held = json.loads(path.read_text(encoding='utf-8'))
        if held.get('key'):model_exam.record(model_exam.KernelStore(self.kernel), held['key'], held.get('results') or [])

    def show_folder(self):
        if self.run is not None:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.run / 'for-sending')))

    # -- use the measured settings? -------------------------------------------------------------------------------------
    def clear_proposals(self):
        while self.proposals.count():
            item = self.proposals.takeAt(0);w = item.widget()
            if w is not None:w.deleteLater()

    def offer(self):
        self.clear_proposals()
        offered = model_check.offered(self.kernel, self.report or {})
        if not offered:return
        head = QLabel('Use the measured settings? Each is yours to apply, and Undo puts it back.');head.setWordWrap(True)
        self.proposals.addWidget(head)
        for p in offered:
            seen = model_check.current(self.kernel, p['key'])
            line = QWidget();row = QHBoxLayout(line);row.setContentsMargins(0, 0, 0, 0)
            words = QLabel(p['words']);words.setWordWrap(True);row.addWidget(words, 1)
            use = QPushButton('Use it');use.setAccessibleName('Use it: ' + p['words'])
            undo = QPushButton('Undo');undo.setAccessibleName('Undo: ' + p['words']);undo.setEnabled(False)
            use.clicked.connect(lambda checked=False, p=p, seen=seen, use=use, undo=undo, words=words: self.use(p, seen, use, undo, words))
            undo.clicked.connect(lambda checked=False, p=p, use=use, undo=undo, words=words: self.undo(p, use, undo, words))
            row.addWidget(use);row.addWidget(undo);self.proposals.addWidget(line)

    def use(self, p, seen, use, undo, words):
        try:
            change = model_check.use_setting(self.kernel, self.principal, p, seen)
        except ValueError as exc:
            words.setText(p['words'] + ' · not applied: ' + str(exc)[:160]);return
        self.undo_ids[p['id']] = change['id'];use.setEnabled(False);undo.setEnabled(True)
        words.setText(p['words'] + ' · applied; it takes effect at the next model start.')

    def undo(self, p, use, undo, words):
        try:
            model_check.undo_setting(self.kernel, self.principal, self.undo_ids.pop(p['id']))
        except (ValueError, KeyError) as exc:
            words.setText(p['words'] + ' · not undone: ' + str(exc)[:160]);return
        use.setEnabled(True);undo.setEnabled(False);words.setText(p['words'] + ' · undone; the setting is as it was.')

    # -- the exam card per model ----------------------------------------------------------------------------------------
    def show_exam(self):
        got = self.kernel.dispatch('brain.exam', {}, self.principal)
        lines = got['result']['card'] if got.get('ok') else ['The exam card could not be read.']
        self.exam_words.setText('\n'.join(lines))
