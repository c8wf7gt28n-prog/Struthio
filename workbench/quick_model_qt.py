"""Graphite 1.0 M2 · the Brain room's page "Quick model": which model answers which kind, and why.

One row a quick kind (quick_model.QUICK_KINDS): the kind and what it is, the model that answers it (a filled dot and
"quick" for the quick model, a ring for hers: a shape and a word beside the colour), why in her words ("passed its exam for
NEXT on this key, 2.1x faster"; "has not sat its exam for READ on this key"; "PLAN has no exam paper yet"), and her clock's
price of the kind's typical question on the model that answers it, with the other model's beside it. Above the rows: both
models, the memory sum with both in it, or why the quick model was not loaded (both do not fit, with the numbers). Under
them: load the model chosen above beside hers, stop the quick model, and one Undo that puts every kind back on her model
(and its way back). Nothing here is a picture of her.

Every colour and size is read from the look in force: the roles boss_theme draws with (Day and Night made from
design_tokens; Graphite and Kasandra their own) and design_tokens' type, space and radius. No keyboard shortcut is printed.
offer_split() gives the model check panel its proposal row (Use it, Undo) when the check measured a quick model beside hers.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout,
                               QWidget)

from . import boss_theme as bt
from . import design_tokens as dt
from . import quick_model

TITLE = 'Quick model'
INTRO = ('Her questions are short, so a second, small model beside hers can answer the quick kinds faster. A kind goes to it '
         'only after it has passed its exam for that kind on its own key and is measured faster on this computer; her model '
         'keeps everything else. Every answer is still checked before anything uses it, whichever model gave it.')
BUTTONS = {'load': 'Load the chosen model beside hers', 'stop': 'Stop the quick model',
           'undo': 'Put every kind back on her model', 'again': 'Offer the quick kinds again'}
QUICK_MARK = '●'          # the quick model answers (a filled dot, with the word "quick")
HERS_MARK = '○'           # her model answers (a ring)


def _font(role):
    px, _, weight, face, _, _ = dt.TYPE[role]
    return 'font-family:"%s";font-size:%dpx;font-weight:%d;' % (bt.FACE, px, weight)


def _label(text='', role='body', colour=None, wrap=True, name=None):
    w = QLabel(text);w.setTextFormat(Qt.PlainText);w.setWordWrap(wrap)
    if wrap:w.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)      # wraps to the room it is given; never widens the page
    w.setStyleSheet('QLabel {%scolor:%s;background:transparent;}' % (_font(role), colour or bt.TEXT))
    if name:w.setAccessibleName(name)
    return w


class QuickPanel(QWidget):
    """The page. refresh() reads brain.quick.status; the buttons dispatch brain.quick.use, .stop and .split."""

    def __init__(self, tab):
        super().__init__();self.tab = tab;self.kernel = tab.kernel;self.principal = tab.principal;self.job = None
        self.setObjectName('QuickModelPage')
        outer = QVBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame);outer.addWidget(scroll)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget();body.setObjectName('QuickModelBody');scroll.setWidget(body)
        body.setStyleSheet('QWidget#QuickModelBody {background:%s;}' % bt.CARD)
        lay = QVBoxLayout(body);lay.setContentsMargins(dt.PAD['m'], dt.PAD['m'], dt.PAD['m'], dt.PAD['m']);lay.setSpacing(dt.PAD['s'])
        lay.addWidget(_label('A QUICK MODEL BESIDE HERS', 'caption', bt.QUIET, name='A quick model beside hers'))
        lay.addWidget(_label(INTRO, 'body', bt.QUIET))
        self.models = _label('', 'body_strong', bt.TEXT, name='The two models');lay.addWidget(self.models)
        self.memory = _label('', 'footnote', bt.QUIET, name='The memory sum for the pair');lay.addWidget(self.memory)
        self.refused = _label('', 'body', bt.HONEY, name='Why the quick model was not loaded');lay.addWidget(self.refused)
        table = QFrame();table.setObjectName('QuickModelRows')
        table.setStyleSheet('QFrame#QuickModelRows {background:%s;border:1px solid %s;border-radius:%dpx;}' % (
            bt.CARD, bt.LINE_MID, dt.RADIUS['panel']))
        self.rows = QVBoxLayout(table);self.rows.setContentsMargins(dt.PAD['s'], dt.PAD['s'], dt.PAD['s'], dt.PAD['s'])
        self.rows.setSpacing(dt.PAD['s'])      # one block a kind: what it is and her clock, then who answers and why (any width)
        self.cells = []
        lay.addWidget(table)
        self.buttons = {}
        for pair in ((('load', self.load), ('stop', self.stop)), (('undo', self.undo), ('again', self.again))):
            row = QHBoxLayout();row.setSpacing(dt.PAD['s'])      # two rows of two: the page never widens past the room
            for key, fn in pair:
                b = QPushButton(BUTTONS[key]);b.setAccessibleName(BUTTONS[key]);b.clicked.connect(fn);row.addWidget(b);self.buttons[key] = b
            row.addStretch(1);lay.addLayout(row)
        self.note = _label('', 'body', bt.TEXT, name='What was done');lay.addWidget(self.note)
        self.scope = _label(quick_model.SCOPE_WORDS, 'footnote', bt.FAINT);lay.addWidget(self.scope)
        lay.addStretch(1)
        self.timer = QTimer(self);self.timer.setInterval(3000);self.timer.timeout.connect(self.tick);self.timer.start()
        self.value = None
        self.refresh()

    # -- reading ---------------------------------------------------------------------------------------------------------
    def tick(self):
        if self.isVisible() or self.job:self.refresh()

    def status(self):
        got = self.kernel.dispatch('brain.quick.status', {}, self.principal)
        return got['result'] if got.get('ok') else None

    def refresh(self):
        if getattr(getattr(self.tab, 'host', None), '_closing', False):return
        self.watch_job()
        value = self.status();self.value = value
        if value is None:
            self.models.setText('Which model answers which kind could not be read just now.');return
        big, quick = value.get('big'), value.get('quick')
        words = ['Her model: %s, running.' % big['name'] if big else 'Her model is not running, so neither model answers.']
        if quick:
            kept = (value.get('kept') or {}).get('kept') or []
            words.append('The quick model: %s, running beside it%s; it keeps its own prompts ready%s.' % (
                quick['name'], ' and sealed' if quick.get('seal') == 'SEALED' else '', (': ' + ', '.join(kept)) if kept else ''))
        elif big:
            words.append('No quick model is running. Choose a registered model above and load it beside hers.')
        self.models.setText(' '.join(words))
        pair = value.get('pair') or {}
        self.memory.setText(pair.get('words') or '')
        refused = value.get('refused') or {}
        self.refused.setText(value.get('stopped') or ('%s was not loaded: %s' % (refused.get('name') or 'The quick model', refused.get('why'))
                                                       if refused and not quick else ''))
        self.refused.setVisible(bool(self.refused.text()))
        self.show_rows(value.get('rows') or [], value)
        offered = value.get('offered') or []
        self.buttons['undo'].setEnabled(bool(offered));self.buttons['again'].setEnabled(not offered or len(offered) < len(quick_model.QUICK_KINDS))
        self.buttons['stop'].setEnabled(bool(quick));self.buttons['load'].setEnabled(bool(big) and not self.job)

    def show_rows(self, rows, value):
        names = {'quick': (value.get('quick') or {}).get('name'), 'big': (value.get('big') or {}).get('name')}
        seen = repr((rows, names))
        if seen == getattr(self, '_shown', None):return      # the same rows: nothing is redrawn
        self._shown = seen
        for w in self.cells:w.hide();w.deleteLater()
        self.cells = []
        for r in rows:
            block = QWidget();box = QVBoxLayout(block);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(2)
            top = QHBoxLayout();top.setSpacing(dt.PAD['xs'])
            top.addWidget(_label(r['kind'], 'body_strong', bt.TEXT, wrap=False))
            top.addWidget(_label(r.get('thing', ''), 'footnote', bt.QUIET), 1)      # it gives way first when the room is narrow
            clock = _label(self.clock_words(r, names), 'footnote', bt.QUIET, wrap=False);clock.setAccessibleName('Her clock for ' + r['kind'])
            top.addWidget(clock);box.addLayout(top)
            line = QHBoxLayout();line.setSpacing(dt.PAD['s'])
            if r['model'] == 'quick':
                by = _label('%s %s · quick' % (QUICK_MARK, r.get('answered_by') or 'the quick model'), 'body_strong', bt.TEAL_TEXT, wrap=False)
            else:
                by = _label('%s %s' % (HERS_MARK, r.get('answered_by') or 'her model'), 'body', bt.TEXT, wrap=False)
            by.setAccessibleName('%s is answered by %s' % (r['kind'], r.get('answered_by') or 'her model'))
            line.addWidget(by, 0, Qt.AlignTop);line.addWidget(_label(r['words'], 'body', bt.TEXT), 1);box.addLayout(line)
            self.rows.addWidget(block);self.cells.append(block)

    @staticmethod
    def clock_words(r, names):
        if r.get('price_ms') is None:return '—'
        here = 'about %s' % quick_model.seconds(r['price_ms'])
        if r.get('other_ms') is not None:
            other = names['big'] if r['model'] == 'quick' else names['quick']
            here += ' · %s on %s' % (quick_model.seconds(r['other_ms']), other or 'the other model')
        return 'Her clock: ' + here

    # -- acting ----------------------------------------------------------------------------------------------------------
    def say(self, words):
        self.note.setText(words)

    def act(self, op, args, done):
        got = self.kernel.dispatch(op, args, self.principal)
        if not got.get('ok'):
            message = (got.get('error') or {}).get('message') or 'not done'
            self.say(quick_model.refusal_words(message));self.refresh();return None
        self.say(done(got['result']));self.refresh()
        return got['result']

    def load(self):
        ident = getattr(self.tab, '_selected_id', None)
        if not ident:self.say('Choose a registered model above first.');return
        def done(r):
            if r.get('state') == 'NOT_LOADED':return 'Not loaded: ' + r.get('why', '')
            self.job = r.get('job_id');return 'Loading %s beside her model, through the same sealed start.' % quick_model.name_of(self.kernel, ident)
        self.act('brain.quick.use', {'id': ident}, done)

    def watch_job(self):
        if not self.job:return
        got = self.kernel.dispatch('brain.result', {'id': self.job}, self.principal)
        if not got.get('ok'):return
        state = got['result'].get('state')
        if state in ('Completed', 'Failed', 'Cancelled', 'Interrupted'):
            result = got['result'].get('result') or {}
            self.say('The quick model is running beside hers.' if state == 'Completed' else
                     'Not loaded: ' + quick_model.refusal_words(result.get('reason') or got['result'].get('error') or state))
            self.job = None

    def stop(self):
        self.act('brain.quick.stop', {}, lambda r: 'The quick model stopped. Her model answers every kind.')

    def undo(self):
        self.act('brain.quick.split', {'undo': True}, lambda r: 'Every kind is back on her model.')

    def again(self):
        self.act('brain.quick.split', {'again': True},
                 lambda r: 'Offered again: %s. Each still goes to the quick model only after its exam, and only when faster.' % (
                     ', '.join(r.get('offered') or ()) or 'none'))


# == the model check's proposal (model_check_qt.offer) ==================================================================
def offer_split(panel, report):
    """The check measured a quick model beside hers: its proposal as one row with Use it and Undo (brain.quick.split)."""
    stage = ((report or {}).get('stages') or {}).get('SQ') or {}
    given = stage.get('proposed')
    if stage.get('state') not in (None, 'PASSED') or given is None:return None
    words = ('Let the quick model answer %s? It passed their exams here and is faster.' % ', '.join(given) if given else
             'The quick model passed no exam here faster than her model: nothing to change.')
    line = QWidget();row = QHBoxLayout(line);row.setContentsMargins(0, 0, 0, 0)
    said = QLabel(words);said.setWordWrap(True);row.addWidget(said, 1)
    if given:
        use = QPushButton('Use it');use.setAccessibleName('Use it: ' + words)
        undo = QPushButton('Undo');undo.setAccessibleName('Undo: ' + words);undo.setEnabled(False)

        def apply():
            got = panel.kernel.dispatch('brain.quick.split', {'kinds': list(given)}, panel.principal)
            if got.get('ok'):use.setEnabled(False);undo.setEnabled(True);said.setText(words + ' · used; each kind still needs its exam on the running quick model.')
            else:said.setText(words + ' · not used: ' + quick_model.refusal_words((got.get('error') or {}).get('message')))

        def back():
            got = panel.kernel.dispatch('brain.quick.split', {'again': True}, panel.principal)
            if got.get('ok'):use.setEnabled(True);undo.setEnabled(False);said.setText(words + ' · undone; the split is as it was.')
        use.clicked.connect(apply);undo.clicked.connect(back);row.addWidget(use);row.addWidget(undo)
    panel.proposals.addWidget(line)
    return line
