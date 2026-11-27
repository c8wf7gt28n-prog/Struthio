"""“Waits for you”: the band at the top of her column, under her hologram (Graphite 1.0 D1; the design direction's section 4).

Her column orders by what needs you. Under her hologram, her name and her state word, this band appears only when something
waits for you, and each thing in it has its one press:

    ◆ NEEDS YOUR WORD     a step of an assignment proposed and not yet authorised: "Authorise step n" (assignment.plan with
                          that step's name and the plan's digest, your press)
    ◆ NEEDS YOUR GRANT    a step that stopped for a grant (K3): the grant in plain words, exactly as it would be given, and
                          "Grant this for this assignment" (grant.give, then the assignment carries on)
    ◆ NEEDS REVIEW        a step whose effect was not verified, or a dialog seen in a program while it ran (K7): what it saw,
                          and "Review it" (its steps and journal, in the exchange)
    ◆ NEEDS YOUR WORD     her one question (0.8.7 B4), when a request of yours waits on it: "Answer it" (her card in the
                          exchange, with its choices)

The shapes are state_words' (◆, ◆ with a key, ◆ with an eye), so what waits never rests on colour. What is here is said only
here: NEXT STEPS no longer repeats an Authorise or a grant, and the grants' fold keeps only its "GRANTS [n] · see them".
When space is short (1366x768) the exchange gives way first and findings fold; this band never folds.

Every press is the owner's and goes through the same call her column always made (HerColumn.take_step, show_journal);
nothing here writes a record by being shown. No key is named in any of its words.
"""
from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from . import boss_theme as bt
from . import state_words as sw
from .her_column_qt import heading, ink, plain, px, row_label, small_button

MOST = 3                # at most this many rows; the rest are counted (they stand in ACTIVE WORK too)
WORDS = {'head': 'WAITS FOR YOU', 'head_count': 'WAITS FOR YOU [{count}]', 'more': 'and {count} more in ACTIVE WORK',
         'grant': 'Grant this for this assignment', 'review': 'Review it', 'answer': 'Answer it',
         'grant_words': 'It asks to {words}. Nothing was sent.', 'question': 'Her question: {words}',
         'no_model': 'No model is loaded. She still reads the records, checks the desk and plans from it. Her model is added in the Brain room → Add file.',
         'brain_room': 'Brain room', 'grant_short': 'Grant it',
         'grant_words_set': 'It asks for {count} grants in one press, {scope}: {words}. Nothing was sent.',  # 1.0 K10
         'held': 'Held by your HALT. Its own Resume checks every step first, then carries on.', 'resume': 'Resume'}  # 1.0 F3
GRANT_OPS = ('grant.give', 'grant.give.set')      # 1.0 K10: one grant, or several in one press (home_plan), each its own record


def items(column):
    """What waits for you now, in the order it is shown: (state key, title, words, press words, press, tip)."""
    out = []
    for row in getattr(column, 'rows', None) or ():
        title = plain(row.get('title') or '');words_ = str(row.get('state_words') or '');line = plain(row.get('line') or '')
        actions = list(row.get('actions') or ())
        grant = next((a for a in actions if a.get('operation') in GRANT_OPS), None)      # 1.0 K10
        authorise = next((a for a in actions if str(a.get('words') or '').startswith('Authorise')), None)
        if grant is not None:
            said = plain(grant.get('grant_words') or '')
            if column.compact():said = re.sub(r' \(“[^”]*”\)', '', said)
            several = grant.get('operation') == 'grant.give.set'      # 1.0 K10: each grant's operation and folder, their one scope once, one press
            scope = plain(grant.get('grant_scope') or 'for this assignment')
            if column.compact():scope = re.sub(r' \(“[^”]*”\)', '', scope)
            said = WORDS['grant_words_set'].format(count=grant.get('grant_count') or 2, scope=scope, words=said) if several and said else \
                (WORDS['grant_words'].format(words=said) if said else line)
            out.append(('needs_grant', title, said, str(grant.get('words')) if several else WORDS['grant'],
                        lambda r=row, a=grant: column.take_step({'kind': 'assignment', 'call': a, 'title': plain(r.get('title') or '')}),
                        'Your press: gives exactly the grant in these words, for this assignment only, and carries on. What always asks still asks.'))
        elif words_ == 'needs review':
            short = line.replace(' needs review: ', ': ', 1) if line.startswith('Step ') else line
            out.append(('needs_review', title, short if len(short) <= 220 else short[:219] + '…', WORDS['review'],
                        lambda r=row: column.show_journal(r['id']), 'Its steps and its journal, in the exchange: what it did and what it saw'))
        elif authorise is not None:
            out.append(('needs_word', title, line, str(authorise.get('words')),
                        lambda r=row, a=authorise: column.take_step({'kind': 'assignment', 'call': a, 'title': plain(r.get('title') or '')}),
                        '%s of “%s”: your press. Nothing runs until you give it.' % (authorise.get('words'), title)))
        elif words_ == 'held' and not getattr(column, 'seen_held', False):      # 1.0 F3: after RESUME, what HALT held waits for its own Resume here
            resume = next((a for a in actions if a.get('words') == 'Resume'), None)
            if resume is not None:
                out.append(('held', title, WORDS['held'], WORDS['resume'],
                            lambda r=row, a=resume: column.take_step({'kind': 'assignment', 'call': a, 'title': plain(r.get('title') or '')}),
                            'Resume “%s”: every step is checked first; a step done is never done again; then it carries on under your grants.' % title))
    question = her_question(column.host)
    if question:
        out.append(('needs_word', '', WORDS['question'].format(words=question), WORDS['answer'], lambda: show_question(column),
                    'Her one question, in the exchange with its choices: your answer, or Leave it'))
    return out


def her_question(host):
    """The words of her one question when a request of yours waits on it, else ''. Reads her hand as it is; never makes it."""
    hand = getattr(host, 'her_hand', None);turn = getattr(hand, 'turn', None) if hand is not None else None
    question = getattr(turn, 'question', None) if turn is not None else None
    if question is None or getattr(turn, 'answered', False) or getattr(turn, 'state', '') == 'finished':return ''
    return plain(str(getattr(question, 'words', '') or ''))[:200]


def show_question(column):
    """Answer it: her exchange in front, at its newest turn, where the card with the choices stands."""
    try:
        shell = column.host.shell2
        if column.host.console_pages.currentWidget() is not column.face:shell.show_slate_face()
        bar = column.face.scroll.verticalScrollBar();bar.setValue(bar.maximum())
    except Exception:  # noqa: BLE001
        pass


class WaitRow(QFrame):
    """One thing that waits: its shape and word and what it is about on the first line, with its one press where there is
    room (else under its words); its words under them: wrapped, or one line in a short column (whole in its tip). A grant's
    words are never shortened: they are the grant exactly as it would be given (K3)."""

    def __init__(self, band):
        super().__init__();self.band = band;host = band.column.host;self.press_fn = None;self.key = '';self.compact = False
        self.setObjectName('HerWaitRow')
        self.setStyleSheet('QFrame#HerWaitRow {border:1px solid %s;border-left:3px solid %s;border-radius:4px;background:transparent;}' % (bt.LINE_MID, bt.OWNER))
        box = QVBoxLayout(self);box.setContentsMargins(px(host, 8), px(host, 3), px(host, 4), px(host, 3));box.setSpacing(px(host, 1))
        self.top = top = QHBoxLayout();top.setSpacing(px(host, 5))
        self.mark = sw.Mark('needs_word', bt.OWNER, px(host, 13));top.addWidget(self.mark, 0, Qt.AlignVCenter)
        self.word = ink(QLabel(), px(host, 11), bt.OWNER, 600, bt.MONO, 'letter-spacing:1px;');self.word.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.title = row_label(host, '', quiet=True, size=12)
        self.press = small_button(host, '', '', primary=True);self.press.setObjectName('HerWaitPress')
        self.press.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed);self.press.clicked.connect(self.pressed)
        top.addWidget(self.word);top.addWidget(self.title, 10);box.addLayout(top)
        self.words = QLabel();self.words.setWordWrap(True);self.words.setTextFormat(Qt.PlainText)
        ink(self.words, px(host, 12), bt.TEXT, None, bt.FACE);self.words.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        box.addWidget(self.words)
        self.short = row_label(host, '', size=12);box.addWidget(self.short)      # a short column: one line, whole in its tip
        self.low = QHBoxLayout();self.low.setSpacing(0);box.addLayout(self.low)      # the press, when the first line has no room for it
        self.place_press(True)

    def place_press(self, beside):
        """The press on the first line (beside: True) or alone under the words."""
        if getattr(self, '_beside', None) is beside:return
        self._beside = beside
        for lay in (self.top, self.low):
            i = lay.indexOf(self.press)
            if i >= 0:lay.takeAt(i)
        while self.low.count():self.low.takeAt(0)
        if beside:self.top.addWidget(self.press, 0, Qt.AlignVCenter)
        else:self.low.addWidget(self.press, 0, Qt.AlignLeft);self.low.addStretch(1)

    def fit(self):
        """Room for the word whole and the press on the first line? Else the press goes under the words. A wrapped label is
        given the height its words need at its width."""
        room = self.width() - self.layout().contentsMargins().left() - self.layout().contentsMargins().right()
        need = self.mark.width() + self.word.sizeHint().width() + self.press.sizeHint().width() + 3 * self.top.spacing() + 40
        self.place_press(room >= need or room <= 0)
        if self.words.isVisible() and self.words.width() > 0:
            tall = self.words.heightForWidth(self.words.width())
            if tall > 0 and self.words.minimumHeight() != tall:self.words.setMinimumHeight(tall)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.fit)

    def show_item(self, item, compact):
        key, title, words, press, fn, tip = item
        self.key = key;self.compact = compact;whole = key == 'needs_grant' or not compact      # a grant is said whole, always
        self.mark.set(key, bt.OWNER);self.word.setText(sw.word(key).upper() if key == 'held' else sw.word(key))      # 1.0 F3: HELD, in capitals as the band's other words
        self.title.setText(title);self.title.setVisible(bool(title))
        self.words.setText(words);self.words.setVisible(bool(words) and whole);self.words.setAccessibleName(words)
        self.short.setText(words);self.short.setVisible(bool(words) and not whole);self.short.setToolTip(words)
        if compact and press == WORDS['grant']:press = WORDS['grant_short']      # a short column: its tip says it whole
        if self.press.text() != press:self.press.setText(press);self.press.adjustSize()
        self.press.setMinimumWidth(self.press.sizeHint().width())
        self.press.setToolTip(tip);self.press_fn = fn
        self.setAccessibleName('%s: %s. %s' % (sw.word(key), title, words))
        self.fit()

    def pressed(self):
        fn = self.press_fn
        if fn is None:return
        from . import floor;fn();floor.column_soon(self.band.column)      # 1.0 F2: read again off the window's thread


class WaitsBand(QWidget):
    """The band: a heading and up to MOST rows; hidden when nothing waits."""

    def __init__(self, column):
        super().__init__();self.column = column;host = column.host;self.setObjectName('HerWaits');self.shown = []
        box = QVBoxLayout(self);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(px(host, 3))
        self.head = heading(host, WORDS['head']);self.head.setStyleSheet(self.head.styleSheet() + 'color:%s;' % bt.OWNER)
        box.addWidget(self.head)
        self.list = QVBoxLayout();self.list.setSpacing(px(host, 3));box.addLayout(self.list);self.rows = []
        self.more = row_label(host, '', quiet=True, size=12);box.addWidget(self.more);self.more.hide()
        self.hide()

    def refresh(self):
        try:found = items(self.column)
        except Exception:  # noqa: BLE001 - the column is whole without the band
            found = []
        narrow = self.column.face.width() < px(self.column.host, 340)      # a narrow column (Graphite's): one line of words each
        self.shown = found;compact = self.column.squeezed() or narrow;most = MOST      # never folded for want of room: a squeezed column's rows are short
        while len(self.rows) < min(len(found), most):
            row = WaitRow(self);self.rows.append(row);self.list.addWidget(row)
        for i, row in enumerate(self.rows):
            if i < min(len(found), most):row.show_item(found[i], compact);row.show()
            else:row.hide()
        hidden = max(0, len(found) - most)
        self.more.setText(WORDS['more'].format(count=hidden) if hidden else '');self.more.setVisible(bool(hidden))
        self.head.setText(WORDS['head_count'].format(count=len(found)) if len(found) > 1 else WORDS['head'])
        self.setVisible(bool(found))
        no_model = getattr(self.column, 'no_model', None)
        if no_model is not None:no_model.refresh()
        return found

    def describe(self):
        return [(sw.word(k), t, w, p) for k, t, w, p, _, _ in self.shown]


class NoModel(QWidget):
    """Her column with no model (the design direction's section 7): what she can still do, and where her model is added."""

    def __init__(self, column):
        super().__init__();self.column = column;host = column.host;self.setObjectName('HerNoModel')
        row = QHBoxLayout(self);row.setContentsMargins(0, 0, 0, 0);row.setSpacing(px(host, 6))
        self.words = QLabel(WORDS['no_model']);self.words.setWordWrap(True);self.words.setTextFormat(Qt.PlainText)
        ink(self.words, px(host, 12), bt.QUIET, None, bt.FACE);self.words.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.words.setAccessibleName(WORDS['no_model']);row.addWidget(self.words, 1)
        self.room = small_button(host, WORDS['brain_room'], 'The Brain room: Add file there adds her model (a file on this computer); nothing is downloaded')
        self.room.setObjectName('HerNoModelRoom');self.room.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed);self.room.clicked.connect(self.open_room)
        row.addWidget(self.room, 0, Qt.AlignTop);self.hide()

    def refresh(self):
        said = str(getattr(self.column.host, '_status_brain', '') or '')
        ready = said.startswith('ready')
        known = bool(said) and said != 'unknown'      # said once the brain's state has been read, never before
        band = getattr(self.column, 'waits', None);busy = band is not None and bool(band.shown) and self.column.squeezed()
        self.setVisible(known and not ready and not busy)      # a short column gives its room to what waits for you (her head says "no model yet")

    def open_room(self):
        try:
            from .shell2 import open_destination
            open_destination(self.column.host, 'slate')
        except Exception:  # noqa: BLE001
            pass


def install(column, outer):
    """her_column_qt.HerColumn.rebuild: the band right under her head (her hologram, name and state); under it, with no model,
    what she can still do (NoModel)."""
    band = WaitsBand(column);outer.addWidget(band)
    column.no_model = NoModel(column);outer.addWidget(column.no_model)
    return band


def carried(column, action):
    """Whether NEXT STEPS should leave this assignment press to the band (it is said in one place)."""
    if getattr(column, 'waits', None) is None:return False
    if action.get('operation') == 'assignment.resume':      # 1.0 F3: a held assignment's Resume is in the band
        ident = (action.get('arguments') or {}).get('id')
        return any(r.get('id') == ident and r.get('state_words') == 'held' for r in getattr(column, 'rows', None) or ()) and not getattr(column, 'seen_held', False)
    return action.get('operation') in GRANT_OPS or str(action.get('words') or '').startswith('Authorise')      # 1.0 K10: a set too
