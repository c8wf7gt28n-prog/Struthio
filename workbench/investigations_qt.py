"""Investigations on the Desk: the top sheet of a continuing investigation, and the few forms that move it along.

Everything here goes through the Kernel's investigation.* operations. The sheet shows what was read, attempted,
checked, learned and left unresolved; a claim's evidence path opens in the Context panel.
"""
from __future__ import annotations
from functools import partial
from .text_prompts import writing_prompt
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QScrollArea, QSizePolicy, QStackedLayout, QVBoxLayout, QWidget)
from . import boss_theme as ink
from .boss_qt import PanelInk
from .document_qt import WordRow
from .shell2 import ERASER, QUIET, TEXT, button, call, call_write, mono_font, role, sentence

STATE_WORDS = {'OPEN': 'Open', 'WAITING': 'Waiting', 'CRITERIA_SATISFIED': 'Criteria satisfied', 'STOPPED': 'Stopped'}
EVIDENCE_WASH = {'SUPPORTED': ink.TEAL_SOFT, 'REFUTED': ERASER, 'CONFLICT': ERASER}
STOP = TEXT
OUTCOME_WORDS = {'PASSED': 'passed', 'CHECK_FAILED': 'did not hold', 'FAILED': 'could not run', 'NOT_RUN': 'not run yet', 'STALE': 'inputs changed',
                 'DONE': 'done'}


class JournalArt(PanelInk):
    def plate_height(self):
        return 160


class JournalTitle(QLabel):
    """Keep the saved question legible beside the illustration at narrower widths."""

    def __init__(self, text):
        super().__init__(text)
        self.setTextFormat(Qt.PlainText)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def resizeEvent(self, event):
        pixels = 28 if self.width() >= 330 else 20
        if getattr(self, '_pixels', None) != pixels:
            self._pixels = pixels
            self.setStyleSheet('font-family:"IBM Plex Mono";font-size:%dpx;font-weight:600;background:transparent;border:0;' % pixels)
        height = self.heightForWidth(self.width())
        if height > 0 and self.minimumHeight() != height:
            self.setMinimumHeight(height)
        super().resizeEvent(event)


def plain(text, quiet=False, mono=False, wrap=True):
    label = QLabel(text);label.setTextFormat(Qt.PlainText);label.setWordWrap(wrap);label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    if quiet:label.setStyleSheet('color:%s' % QUIET)
    if mono:label.setFont(mono_font(12))
    return label


class InvestigationTab(QWidget):
    """One place to keep a question going: read, claim, check, continue."""

    def __init__(self, host, ident=None):
        super().__init__();self.host = host;self.ident = ident;self.sheet = None;self.selected_claim = None
        self.setProperty('ledgerRoom', True);self.setObjectName('LibraryTab')
        self.setStyleSheet('''
            QWidget#JournalPage {background:%(GROUND)s;}
            QFrame#JournalHeading {background:%(GROUND)s;border:1px solid %(LINE_STRONG)s;border-top:2px solid %(AMBER_EDGE)s;}
            QWidget#JournalHeadingWords, QWidget#JournalHeadingWords QLabel {background:transparent;border:0;}
            QLabel#JournalSection, QLabel#JournalKicker {font-family:"IBM Plex Mono";font-size:14px;font-weight:600;}
            QLabel#JournalKicker {color:%(TEXT)s;}
            QLabel#JournalSection {color:%(TEXT)s;background:%(PANEL)s;border:1px solid %(LINE)s;padding:6px 10px;}
            QLabel#JournalSection[priority="true"] {color:%(AMBER_TEXT)s;border-left:2px solid %(AMBER_EDGE)s;}
            QLabel#JournalClaim {font-family:"IBM Plex Mono";font-size:13px;}
            QLabel#JournalClaim:focus {background:%(AMBER_SOFT)s;}
            QFrame#JournalState {border-bottom:1px solid %(LINE)s;}
            QFrame#JournalNext {background:%(PANEL)s;border:1px solid %(LINE)s;}
            QPushButton#JournalContinue {background:%(AMBER_EDGE)s;color:%(TERMINAL_GROUND)s;border-radius:0;
                font-family:"IBM Plex Mono";font-weight:600;padding:6px 9px;}
            QPushButton#JournalContinue:focus {border:1px solid %(TEXT)s;}
        ''' % vars(ink))
        outer = QHBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0);outer.setSpacing(0)
        side = QFrame();side.setObjectName('JournalIndex');side.setFixedWidth(176)
        side.setStyleSheet('''
            QFrame#JournalIndex {background:%(PANEL)s;border:1px solid %(LINE)s;}
            QListWidget#JournalList {background:transparent;border:0;font-family:"IBM Plex Mono";font-size:13px;}
            QListWidget#JournalList::item {padding:6px 4px;border-left:2px solid transparent;}
            QListWidget#JournalList::item:selected {color:%(TEXT)s;background:%(AMBER_SOFT)s;border-left-color:%(AMBER_EDGE)s;}
        ''' % vars(ink))
        self.index_panel = side
        self.index_layout = outer
        col = QVBoxLayout(side);col.setContentsMargins(10, 12, 10, 12);col.setSpacing(9)
        index = plain('[ JOURNALS ]', mono=True)
        col.addWidget(index)
        self.list = QListWidget();self.list.setObjectName('JournalList');self.list.setAccessibleName('Investigations');self.list.itemClicked.connect(lambda item:self.open(item.data(Qt.UserRole)))
        self.list.setWordWrap(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        col.addWidget(self.list, 1)
        self.new_question = QLineEdit();writing_prompt(self.new_question, 'A question to keep going…');self.new_question.returnPressed.connect(self.create)
        col.addWidget(self.new_question)
        new = button('New investigation', 'primary');new.clicked.connect(self.create);col.addWidget(new)
        outer.addWidget(side)
        self.scroll = QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(self.scroll, 1);self.message = ('', QUIET)
        self.clear()
        self.reload()
        if ident:self.open(ident)
        else:self.empty()

    def title(self):return 'Investigations'
    def centre_title(self):      # for the centre's bar: the question that is open, by its own name
        sheet = self.sheet if isinstance(self.sheet, dict) else {}
        return str(sheet.get('question') or 'Investigations')

    def info(self):return 'Continuing investigations · the top sheet'

    def place_index(self, layout=None, position=0):
        """Dock the active journal list in Files, or return it to this tab."""
        if layout is None:
            self.index_panel.setFixedWidth(176)
            self.index_layout.insertWidget(0, self.index_panel)
        else:
            self.index_panel.setMinimumWidth(0)
            self.index_panel.setMaximumWidth(self.maximumWidth())
            layout.insertWidget(position, self.index_panel, 1)
        self.index_panel.show()

    # data ------------------------------------------------------------------
    def reload(self):
        self.list.clear()
        for row in (call(self.host, 'investigation.list') or {}).get('investigations', []):
            item = QListWidgetItem(row['question'][:80] + '\n' + STATE_WORDS.get(row['state'], row['state']));item.setData(Qt.UserRole, row['id'])
            self.list.addItem(item)
            if row['id'] == self.ident:self.list.setCurrentItem(item)

    def act(self, op, args, then=None):
        r = call_write(self.host, op, args)
        if not r.get('ok'):
            self.message = ('That did not work: ' + (r.get('error') or {}).get('message', 'unknown'), STOP);self.render();return None
        self.message = ('', QUIET)
        if then:then(r['result'])
        self.open(self.ident);self.reload()
        return r['result']

    def create(self):
        question = self.new_question.text().strip()
        if not question:self.new_question.setFocus();return
        r = call_write(self.host, 'investigation.create', {'question': question})
        if r.get('ok'):self.new_question.clear();self.ident = r['result']['id'];self.reload();self.open(self.ident)
        else:self.message = ('That did not work: ' + r['error']['message'], STOP);self.render()

    def open(self, ident):
        self.ident = ident;self.sheet = call(self.host, 'investigation.sheet', {'id': ident}) if ident else None
        self.render();self.tell_inspector()

    # the sheet -------------------------------------------------------------
    def clear(self):
        """A fresh page each time: the scroll area deletes the old one, so nothing stale is ever drawn."""
        self.body = QWidget();self.body.setObjectName('JournalPage')
        self.page = QVBoxLayout(self.body);self.page.setContentsMargins(14, 12, 12, 16);self.page.setSpacing(9)
        self.status = plain(self.message[0], quiet=True);self.status.setStyleSheet('color:%s' % self.message[1]);self.status.setVisible(bool(self.message[0]))
        self.scroll.setWidget(self.body)

    def empty(self):
        self.clear()
        self.page.addWidget(role(QLabel('Investigations'), 'title'))
        self.page.addWidget(role(plain('Keep a question going. Read sources into it, write down what you think is true, say what check would show it, '
                                       'and continue. Graphite keeps what was read, tried, checked and learned, and what is still open.'), 'lead'))
        self.page.addWidget(self.status);self.page.addStretch(1)

    def render(self):
        if not self.sheet:return self.empty()
        s = self.sheet;self.clear()
        mast = QFrame();mast.setObjectName('JournalHeading')
        layers = QStackedLayout(mast)
        layers.setContentsMargins(1, 2, 1, 1)
        layers.setStackingMode(QStackedLayout.StackAll)
        art = JournalArt(self.host, 'journal')
        layers.addWidget(art)
        words = QWidget();words.setObjectName('JournalHeadingWords')
        band = QHBoxLayout(words);band.setContentsMargins(15, 10, 8, 10)
        title = QVBoxLayout();title.setSpacing(8);title.setAlignment(Qt.AlignVCenter)
        kicker = plain('[*] RESEARCH JOURNAL', mono=True);kicker.setObjectName('JournalKicker')
        title.addWidget(kicker)
        name = JournalTitle(s['question'])
        name.setObjectName('JournalTitle')
        title.addWidget(name)
        band.addLayout(title, 4);band.addStretch(2)
        layers.addWidget(words);layers.setCurrentWidget(words);art.set_available(True)
        self.page.addWidget(mast)
        used = s['used'];budget = s['budget']
        state = QFrame();state.setObjectName('JournalState')
        state_row = QHBoxLayout(state);state_row.setContentsMargins(3, 0, 3, 6)
        status_word = plain('[' + STATE_WORDS.get(s['state'], s['state']).upper() + ']', mono=True)
        status_word.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        status_word.setStyleSheet('font-family:"IBM Plex Mono";font-size:13px;color:' + {'WAITING': ink.AMBER_TEXT, 'CRITERIA_SATISFIED': ink.READY}.get(s['state'], QUIET))
        state_row.addWidget(status_word)
        state_row.addWidget(plain('%d of %d steps used  ·  %s authority' % (used['steps'], budget.get('max_steps', 20),
                                  budget.get('effects', 'read')), quiet=True, mono=True), 4)
        self.page.addWidget(state)
        if s['state'] == 'STOPPED' and s['reason']:
            self.page.addWidget(plain(s['reason'], quiet=True))
        self.claims('[ 01 ] WHAT WE KNOW', s['learned'], 'Findings will appear here as the investigation progresses.')
        self.claims('[ 02 ] WHAT IS STILL OPEN', s['unresolved'], 'No open questions recorded.')
        self.section_heading('[ 03 ] NEXT USEFUL ACTION', priority=True)
        next_panel = QFrame();next_panel.setObjectName('JournalNext')
        next_page = QVBoxLayout(next_panel);next_page.setContentsMargins(10, 8, 10, 8);next_page.setSpacing(8)
        next_page.addWidget(plain(s['next']['text'], mono=True))
        nxt = WordRow(spacing=18, line_spacing=6)
        go = button('Continue', 'primary');go.setToolTip('Run what is due, within the budget, with read-only authority')
        go.setObjectName('JournalContinue')
        go.clicked.connect(lambda:self.act('investigation.continue', {'id': s['id']}));nxt.addWidget(go)
        again = button('Compare sources again', 'quiet');again.clicked.connect(lambda:self.act('investigation.refresh', {'id': s['id']}));nxt.addWidget(again)
        stop = button('Stop', 'quiet');stop.clicked.connect(lambda:self.act('investigation.stop', {'id': s['id'], 'reason': 'Stopped from the sheet'}));nxt.addWidget(stop)
        from .theme2 import tool        # beside Continue, the two other things that can be done now are buttons too
        tool(again, 'Read the sources again and compare them with what was read before');tool(stop, 'Stop this investigation where it is; what it found is kept')
        next_page.addLayout(nxt);self.page.addWidget(next_panel);self.page.addWidget(self.status)
        self.section('[ SOURCES ]', [(r['address'], 'snapshot ' + r['digest'][:12] + ('' if r['state'] == 'CURRENT' else '  ·  ' + r['state'].lower()), True) for r in s['read']],
                     'Nothing read yet. Add a staC address below, or press Investigate on an open file.')
        self.section('[ ATTEMPTED ]', [('%d.  %s' % (r['seq'], r['purpose']), OUTCOME_WORDS.get(r['outcome'], r['outcome']) +
                                    ('  ·  repeat, adds no support' if r['duplicate_of'] else ''), False) for r in s['attempted']], 'No steps yet.')
        self.section('[ CHECKED ]', [(k['oracle'], 'for: ' + k['claim_text'][:80] + '  ·  ' + OUTCOME_WORDS.get(k['last_outcome'], k['last_outcome']) +
                                  ('  ·  ran with ' + k['last_authority'] if k.get('last_authority') else ''), False) for k in s['checked']],
                     'No checks yet. A check binds a claim to a staC program and what counts as success.')
        self.page.addWidget(plain(s['notice'], quiet=True))
        self.forms(s);self.page.addStretch(1)

    def section_heading(self, title, priority=False):
        label = plain(title, mono=True)
        label.setObjectName('JournalSection')
        label.setProperty('priority', priority)
        label.setMinimumHeight(34)
        self.page.addWidget(label)

    def section(self, title, rows, empty):
        self.section_heading(title)
        if not rows:self.page.addWidget(plain(empty, quiet=True));return
        for main, note, mono in rows:
            row = QHBoxLayout();row.addWidget(plain(main, mono=mono), 3);row.addWidget(plain(note, quiet=True), 2);self.page.addLayout(row)

    def claims(self, title, claims, empty):
        self.section_heading(title, priority=True)
        if not claims:self.page.addWidget(plain(empty, quiet=True));return
        for c in claims:
            row = QHBoxLayout()
            show_claim = partial(self.show_path, c['id'])
            text = sentence('{claim}', {'claim': (c['text'], show_claim)})
            text.setObjectName('JournalClaim')
            text.setAccessibleName(c['text'])
            text.setToolTip('Show why: the evidence path opens in Context')
            text.setContentsMargins(0, 3, 0, 3)
            text.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            text.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
            text.setFocusPolicy(Qt.StrongFocus)
            shortcut = QShortcut(text)
            shortcut.setKeys([QKeySequence(key) for key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space)])
            shortcut.setContext(Qt.WidgetShortcut)
            shortcut.activated.connect(show_claim)
            row.addWidget(text, 3, Qt.AlignTop)
            state = c.get('evidence_state', 'UNKNOWN') if c['role'] != 'QUESTION' else 'QUESTION'
            words = {'QUESTION': 'open question'}.get(state, state.lower() + ('  ·  %d independent' % c.get('independent_support', 0) if c.get('independent_support') else ''))
            if c.get('review') == 'NEEDS_REVIEW':words += '  ·  a source changed'
            note = plain(c['role'].lower() + '  ·  ' + words, mono=True)
            note.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            wash = EVIDENCE_WASH.get(state)
            colour = ink.READY if state == 'SUPPORTED' else TEXT
            note.setStyleSheet(('background:%s;border:1px solid %s;padding:4px 8px;color:%s' % (wash, ink.TEAL_EDGE if state == 'SUPPORTED' else ink.LINE_STRONG, colour))
                               if wash else 'color:%s' % QUIET)
            row.addWidget(note, 2, Qt.AlignTop)
            self.page.addLayout(row)
            if c.get('review') == 'NEEDS_REVIEW':
                review = WordRow(spacing=18, line_spacing=6)
                for label, decision in (('Accept the change', 'ACCEPT_CHANGE'), ('Retire', 'RETIRE')):
                    b = button(label, 'quiet');b.clicked.connect(lambda checked=False, i=c['id'], d=decision:self.act('investigation.review', {'claim': i, 'decision': d}))
                    review.addWidget(b)
                self.page.addLayout(review)

    def forms(self, s):
        self.page.addSpacing(10);self.page.addWidget(role(QLabel('WORK ON IT'), 'section'))
        row = QHBoxLayout();address = QLineEdit();writing_prompt(address, '@intake:… or any staC address to read into this investigation')
        address.setFont(mono_font(12));row.addWidget(address, 1)
        add = button('Read source', 'quiet');add.clicked.connect(lambda:address.text().strip() and self.act('investigation.add_source', {'id': s['id'], 'address': address.text().strip()}))
        row.addWidget(add);self.page.addLayout(row)
        claim = QLineEdit();writing_prompt(claim, 'What you think is true, or what you need to find out');self.page.addWidget(claim)
        row = WordRow(spacing=9, line_spacing=6)
        kind = QComboBox();kind.addItems(['Finding', 'Candidate', 'Question']);row.addWidget(kind)
        write = button('Write it down', 'quiet')
        write.clicked.connect(lambda:claim.text().strip() and self.act('investigation.claim', {'id': s['id'], 'text': claim.text().strip(), 'role': kind.currentText().upper()}))
        row.addWidget(write);self.page.addLayout(row)
        claims = [c for c in s['learned'] + s['unresolved'] if c['role'] != 'QUESTION']
        if claims:
            box = QVBoxLayout();box.setSpacing(6)
            row = QHBoxLayout();which = QComboBox()
            which.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            which.setMinimumContentsLength(12)
            for c in claims:which.addItem(c['text'][:70], c['id'])
            which.setToolTip(which.currentText());which.currentTextChanged.connect(which.setToolTip)
            row.addWidget(QLabel('Check'));row.addWidget(which, 1);box.addLayout(row)
            program = QLineEdit();program.setFont(mono_font(12));writing_prompt(program, 'staC that would show it, e.g. @intake:… | select text');box.addWidget(program)
            oracle = QLineEdit();writing_prompt(oracle, 'What counts as success, in words');box.addWidget(oracle)
            row = QHBoxLayout()
            expect = QComboBox()
            for label, key in (('result is not empty', 'NONEMPTY'), ('result contains', 'CONTAINS'), ('result does not contain', 'NOT_CONTAINS'), ('at least N results', 'COUNT_AT_LEAST')):
                expect.addItem(label, key)
            row.addWidget(expect);value = QLineEdit();writing_prompt(value, 'text or N');value.setMaximumWidth(160);row.addWidget(value)
            box.addLayout(row)
            refutes = QCheckBox('failing refutes it');box.addWidget(refutes, 0, Qt.AlignLeft)      # as wide as its words: a click far to its right ticks nothing
            bind = button('Bind the check', 'quiet')
            bind.clicked.connect(lambda:program.text().strip() and oracle.text().strip() and self.act('investigation.check', {
                'claim': which.currentData(), 'program': program.text().strip(), 'oracle': oracle.text().strip(), 'expect': expect.currentData(),
                'value': value.text().strip(), 'refutes_on_fail': refutes.isChecked()}))
            box.addWidget(bind, 0, Qt.AlignLeft);self.page.addLayout(box)
        row = QHBoxLayout();step = QLineEdit();step.setFont(mono_font(12));writing_prompt(step, 'staC to try now (it runs with your authority and is recorded)')
        row.addWidget(step, 1);run = button('Run step', 'stac')
        run.clicked.connect(lambda:step.text().strip() and self.act('investigation.step', {'id': s['id'], 'program': step.text().strip(), 'purpose': 'Tried from the sheet'}))
        row.addWidget(run);self.page.addLayout(row)

    # Context ---------------------------------------------------------------
    def show_path(self, claim):
        self.selected_claim = claim;self.tell_inspector()
        face = getattr(self.host, 'shell2', None)
        if face is not None:face.show_context_face()

    def inspector(self):
        if self.selected_claim:
            p = call(self.host, 'investigation.path', {'claim': self.selected_claim})
            if p:
                rows = [('Evidence state', p['evidence_state'].lower() + ' · %d independent support, %d against' % (p['independent_support'], p['independent_opposition']))]
                for link in p['path']:
                    where = (link.get('address', '') + ' @ ' + link.get('digest', '')[:12]) if link['kind'] == 'SOURCE' else \
                            (link.get('program', '') + '\n→ ' + link.get('outcome', '').lower() + ' · result ' + (link.get('result_digest') or '')[:12] + ' · ran with ' + link.get('ran_with', ''))
                    rows.append((link['direction'].lower() + (' · counts' if link['counts'] else ' · kept, not counted'), where))
                if not p['path']:rows.append(('Path', 'No evidence yet.'))
                return 'Why: ' + p['text'][:60], rows
        if self.sheet:
            s = self.sheet
            return s['question'], [('State', STATE_WORDS.get(s['state'], s['state'])), ('Next', s['next']['text']),
                                     ('Read', '%d sources' % len(s['read'])), ('Checked', '%d checks' % len(s['checked']))]
        return 'Investigations', [('What this is', 'A question kept going: sources, claims, checks and steps, recorded by the Kernel.')]

    def tell_inspector(self):
        inspector = getattr(self.host, 'arc_inspector', None)
        if inspector is not None and self.host.tabs.currentWidget() is self:inspector.refresh()


def show(host, ident=None):
    """Open (or reuse) the Investigations tab, optionally on one investigation."""
    host._close_start()
    for i in range(host.tabs.count()):
        tab = host.tabs.widget(i)
        if isinstance(tab, InvestigationTab):
            host.tabs.setCurrentWidget(tab);tab.reload()
            if ident:tab.open(ident)
            return tab
    tab = InvestigationTab(host, ident);host.tabs.addTab(tab, tab.title());host.tabs.setCurrentWidget(tab);return tab


def investigate(host, address, name):
    """Start an investigation from an open item: its address becomes the first source."""
    from PySide6.QtWidgets import QInputDialog, QMessageBox
    if not address:
        QMessageBox.information(host, 'Investigate', 'Receive this file into the Office first, so it has a staC address an investigation can read.')
        return None
    question, ok = QInputDialog.getText(host, 'Investigate ' + name, 'The question to keep going:', text='What does ' + name + ' establish?')
    if not ok or not question.strip():return None
    r = call_write(host, 'investigation.create', {'question': question.strip()})
    if not r.get('ok'):QMessageBox.warning(host, 'Investigate', r['error']['message']);return None
    ident = r['result']['id']
    call_write(host, 'investigation.add_source', {'id': ident, 'address': '@' + address.removeprefix('@')})
    return show(host, ident)
