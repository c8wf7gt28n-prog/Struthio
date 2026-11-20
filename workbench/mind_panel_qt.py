"""Her column panel (0.8.6 W, "Kas's mind, no model"): Why, Rests on, Either way and What would settle it, for one card.

One panel in her column, the window side of her reasons (reasons.py, either_way.py, settle.py). Every card on the Field has
"Why" in its right-click (context_menu.field_entries), and a goal, rule or word card opens to it; show_why(host, card) puts
the panel in her column, in place of the one shown before.

  Why                   the short proof (at most 12 lines, reasons.BUDGET), each line with its state word and where it came
                        from, For and Against, ending with what would change the conclusion. A click on a line selects its
                        card on the Field and lights the proof's wires there with the Field's own trace light (light_proof);
                        the selection steps the rest of the desk back. Next and Back walk the proof card by card from the
                        source end, the wires lit as far as the walk has come.
  Rests on              what the answer rests on that is not a reviewed reading (field.rests), each with Without it, and for
                        a choice between revisions With the other one; the answer that counts is said without her proposals.
  Either way            every reading the desk knows of, worked out (field.either); for a choice that decides it, one button
                        per value with its exact outcome; a press selects that revision's sheet on the Field.
  What would settle it  what would settle a cannot tell, and who can settle it (field.settle).

Nothing here writes a record: every call is a read (field.why, field.rests, field.either, field.settle, observer operations,
so asking is not an event). No model is asked: the words are her templates (WORDS, registered with mind_words, and the
reasons modules' own), and the foot says the model calls, 0. Every text shown goes through model_words.plain_only first, as
her column's plain renderer does: model words can never be shown here as hers. Every colour that means something also has
a word or a shape: the line chosen carries a rule at its left and a mark, the section shown its mark.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from . import boss_theme as bt
from . import mind_words

SECTIONS = (('why', 'tab_why'), ('rests', 'tab_rests'), ('either', 'tab_either'), ('settle', 'tab_settle'))

# Her words here: fixed templates, scanned with the rest of hers (mind_words.check): no exclamation mark, no sentence over
# 30 words, no digit in the fixed words, every number through a slot that names its record.
WORDS = {
    'head': 'Why “{title}” stands as it does',
    'tab_why': 'Why',
    'tab_rests': 'Rests on',
    'tab_either': 'Either way',
    'tab_settle': 'What would settle it',
    'foot': 'My own templates, worked out on your records with no model. Model calls: {count}.',
    'not_goal': 'This card is not a goal over the desk’s data, so there is no other way of reading it to work out. Why gives its reasons.',
    'next': 'Next',
    'back': 'Back',
    'away': 'Put it away',
    'walk': 'Card {n} of {count} from the source end: “{title}”.',
    'walk_start': 'Next walks the proof card by card from the source end, lighting its wires on the Field.',
    'walk_none': 'There are no wires to walk: nothing else on the desk feeds it.',
    'for': 'For it:',
    'against': 'Against it:',
    'nothing': 'nothing',
    'counted': 'The answer that counts: {words}.',
    'proposed': 'With my proposal, not agreed: {words}.',
    'without': 'Without it',
    'with_other': 'With {name} instead',
    'without_said': 'Without it: {words}.',
    'other_said': 'With {name} instead: {words}.',
    'whose': 'Whose: {whose}.',
    'nothing_rests': 'It rests on nothing but reviewed readings and what Why shows.',
    'way_pressed': 'Its sheet, “{title}”, is selected on the Field. Which revision applies stays yours to say.',
    'could_not': 'I could not work this out: {why}',
    'no_field': 'The Field is not open in this window, so no wires can be lit.',
    'worked': 'Worked out when you asked. Nothing was written.',
}
NUMBERS = {'foot': {'count': 'the reads behind this panel: field.why, field.rests, field.either, field.settle'},
           'walk': {'n': 'the proof’s walk (reasons.why)', 'count': 'the proof’s walk (reasons.why)'}}
mind_words.register('mind_panel', WORDS, kind='sentence', numbers=NUMBERS)

# Where a line came from, in words (reasons.why's 'from' is the premise's role).
FROM_WORDS = {'row': 'a reviewed row', 'tolerance': 'your tolerance', 'choice': 'which revision applies', 'check': 'a check the Kernel ran',
              'maths': 'the maths', 'source': 'a source admitted here', 'made': 'what it was made from', 'evidence': 'the evidence',
              'rests': 'what it rests on', 'change': 'what would change it', 'budget': 'the budget', 'subject': 'the card itself'}


def say(key, **slots):
    return WORDS[key].format(**slots)


def plain(text):
    """Her plain words, checked first: model words are refused here exactly as her column's plain renderer refuses them."""
    from .model_words import plain_only
    return plain_only(text)


def put(label, text):
    """Her words into a label: through plain_only, then leaded in Kasandra (room between the lines), as she speaks there."""
    text = plain(text)
    if bt.APPEARANCE == 'kasandra':
        from .shell2 import leaded
        leaded(label, text)
    else:
        label.setProperty('plain', str(text));label.setTextFormat(Qt.PlainText);label.setText(str(text))
    return label


def words_label(text='', quiet=False):
    label = QLabel();label.setWordWrap(True);label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    if quiet:label.setStyleSheet('color:%s;' % bt.QUIET)
    if text:put(label, text)
    return label


class Line(QFrame):
    """One line of the proof: her words, and under them its state word and where it came from. A line about a card is a
    place to click: that card is selected on the Field and the proof's wires are lit."""

    def __init__(self, panel, line):
        super().__init__();self.panel = panel;self.line = line;self.setObjectName('KasMindLine')
        box = QVBoxLayout(self);box.setContentsMargins(8, 3, 4, 3);box.setSpacing(1)
        from .model_words import is_model      # 0.8.7 A4: a line that is model words shows with its mark (model_marks_qt)
        if is_model(line.get('text')):
            from .model_marks_qt import ModelWords
            self.text = ModelWords(line['text'], line.get('mark') or 'CHECKED')
        else:
            self.text = words_label(line.get('text', ''))
        if isinstance(self.text, QLabel):self.text.setTextInteractionFlags(Qt.NoTextInteraction)
        meta = ' · '.join(x for x in (line.get('state') or '', self._from(line)) if x)
        self.meta = words_label(meta, quiet=True) if meta else None
        self.text.setAttribute(Qt.WA_TransparentForMouseEvents)
        box.addWidget(self.text)
        if self.meta is not None:self.meta.setAttribute(Qt.WA_TransparentForMouseEvents);box.addWidget(self.meta)
        self.card = line.get('field') or ''
        if self.card or line.get('leaf'):
            self.setCursor(Qt.PointingHandCursor)
            self.setToolTip('Select this card on the Field and light the proof’s wires' if self.card else 'Light the proof’s wires on the Field')
        self.set_chosen(False)

    @staticmethod
    def _from(line):
        said = str(line.get('from') or '')
        return FROM_WORDS.get(said, said)

    def set_chosen(self, chosen):
        """The line chosen: a rule at its left and a mark before its words (a shape, not only a colour)."""
        self.chosen = chosen
        edge = bt.AMBER_EDGE if chosen else 'transparent'
        self.setStyleSheet('QFrame#KasMindLine {border:0; border-left:3px solid %s;}' % edge)
        from .model_words import is_model      # 0.8.7 A4: model words are named by their mark, never as her words
        said = self.text.line.text() if is_model(self.line.get('text')) else str(self.line.get('text', ''))
        self.setAccessibleName(('Chosen: ' if chosen else '') + said[:200])

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and (self.card or self.line.get('leaf')):
            self.panel.choose_line(self);return
        super().mousePressEvent(event)


class MindPanel(QFrame):
    """The panel for one card. Reads on open (Why) and when a section is first shown; writes nothing."""

    def __init__(self, host, ident, title=''):
        super().__init__();self.host = host;self.ident = str(ident);self.title = str(title or ident)
        self.setObjectName('KasMindPanel');self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QFrame#KasMindPanel {border:1px solid %s; background:%s;}' % (bt.LINE, bt.CARD))
        self.why = None;self.answers = {};self.calls = 0;self.lines = [];self.step = -1;self.walk = [];self.wires = []
        box = self.box = QVBoxLayout(self);box.setContentsMargins(10, 8, 8, 8);box.setSpacing(6)
        from .shell2 import button
        head = QHBoxLayout();head.setSpacing(8)
        self.head = words_label(say('head', title=self.title[:160]));self.head.setStyleSheet('font-weight:600;')
        head.addWidget(self.head, 1)
        self.away = button(say('away'), 'quiet', 'The panel leaves her column; the Field stays as it is')
        self.away.setObjectName('KasMindAway');self.away.clicked.connect(self.put_away);head.addWidget(self.away, 0, Qt.AlignTop)
        box.addLayout(head)
        tabs = QHBoxLayout();tabs.setSpacing(4);self.tabs = {}
        for name, key in SECTIONS:
            b = button(WORDS[key], 'quiet', '');b.setObjectName('KasMindSection');b.setCheckable(True)
            b.clicked.connect(lambda checked=False, name=name: self.show_section(name))
            self.tabs[name] = b;tabs.addWidget(b)
        tabs.addStretch(1);box.addLayout(tabs)
        walk = QHBoxLayout();walk.setSpacing(6)        # the walk sits above the proof, so it is in reach without scrolling
        self.back = button(say('back'), 'quiet', 'One card back towards the source end');self.back.setObjectName('KasMindBack')
        self.next = button(say('next'), 'quiet', 'The next card from the source end, its wires lit');self.next.setObjectName('KasMindNext')
        self.back.clicked.connect(lambda: self.walk_by(-1));self.next.clicked.connect(lambda: self.walk_by(1))
        self.walk_words = words_label('', quiet=True)
        walk.addWidget(self.back, 0, Qt.AlignTop);walk.addWidget(self.next, 0, Qt.AlignTop);walk.addWidget(self.walk_words, 1);box.addLayout(walk)
        self.pages = {}                                  # one section shown at a time; a hidden one takes no room
        for name, _ in SECTIONS:
            page = QWidget();lay = QVBoxLayout(page);lay.setContentsMargins(0, 0, 0, 0);lay.setSpacing(3)
            self.pages[name] = (page, lay);page.hide();box.addWidget(page)
        self.foot = words_label('', quiet=True);box.addWidget(self.foot)

    # ---- reading --------------------------------------------------------------------------------------------------------------
    def kernel(self):
        from .engineering_kernel import operator
        kernel = getattr(getattr(self.host, 'ledger_bridge', None), 'kernel', None)
        if kernel is None:
            from .engine import engineering
            kernel = engineering(self.host.root)
        return kernel, operator()

    def read(self, operation, arguments):
        """One read through the Kernel: (result, '') or (None, her words for why it could not be read)."""
        from PySide6.QtWidgets import QApplication
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            kernel, principal = self.kernel()
            answer = kernel.dispatch(operation, arguments, principal)
        except Exception as exc:  # noqa: BLE001 - a panel never takes the window down
            answer = {'ok': False, 'error': {'message': str(exc)}}
        finally:
            QApplication.restoreOverrideCursor()
        if not isinstance(answer, dict) or not answer.get('ok'):
            error = (answer or {}).get('error') if isinstance(answer, dict) else answer
            message = error.get('message') if isinstance(error, dict) else str(error)
            return None, str(message or 'it could not be read').strip()[:300]
        result = answer.get('result') or {}
        self.calls += int(result.get('model_calls') or 0) if isinstance(result, dict) else 0
        return result, ''

    def start(self):
        self.show_section('why')
        return self

    def show_section(self, name):
        for other, b in self.tabs.items():
            b.setChecked(other == name)
            b.setText(('› ' if other == name else '') + WORDS[dict(SECTIONS)[other]])      # the section shown carries a mark
        if name not in self.answers:self.fill(name)
        for other, (page, _) in self.pages.items():page.setVisible(other == name)      # the panel is as tall as the section shown
        self.adjustSize()
        self.walk_row(name == 'why')
        self.foot.setText('');put(self.foot, say('foot', count=self.calls) + ' ' + say('worked'))

    def walk_row(self, shown):
        for w in (self.back, self.next, self.walk_words):w.setVisible(shown)
        if shown:self.said_walk()

    def fill(self, name):
        self._fill(name)
        found = self.answers.get(name)      # 0.8.7 A4: the model's part of a read, with its mark line and its fold
        if isinstance(found, dict):
            from . import model_marks_qt
            model_marks_qt.place(self, self.pages[name][1], found)

    def _fill(self, name):
        lay = self.pages[name][1]
        if name == 'why':
            found, why = self.read('field.why', {'id': self.ident});found = self.voiced(name, found);self.answers[name] = found   # 0.8.7 W7
            if found is None:lay.addWidget(words_label(say('could_not', why=why)));return
            self.why = found;self.lines = []
            for line in found.get('lines') or ():
                row = Line(self, line);self.lines.append(row);lay.addWidget(row)
            self.sides(lay, found)
            self.prepare_walk(found)
        elif name == 'rests':
            found, why = self.read('field.rests', {'id': self.ident});self.answers[name] = found
            if found is None:lay.addWidget(words_label(say('could_not', why=why)));return
            self.rests(lay, found)
        elif name == 'either':
            found, why = self.read('field.either', {'id': self.ident});found = self.voiced(name, found);self.answers[name] = found   # 0.8.7 W7
            if found is None:lay.addWidget(words_label(self.refusal(why)));return
            for text in found.get('words') or ():lay.addWidget(words_label(text))
            question = found.get('question') or {}
            for outcome in question.get('outcomes') or ():
                self.way_button(lay, outcome)
        else:
            found, why = self.read('field.settle', {'id': self.ident});self.answers[name] = found
            if found is None:lay.addWidget(words_label(self.refusal(why)));return
            for text in found.get('words') or ():lay.addWidget(words_label(text))
            step = found.get('next') or {}
            if step.get('words') and step.get('route') != 'NOTHING':lay.addWidget(words_label(step['words'], quiet=True))

    def voiced(self, name, found):
        """0.8.7 W7: her answers (the proof's maths line, each way) said through her voice floor where 0.8.6's templates said
        them (voice_column.restate). With every 0.8.7 switch off, or nothing the floor can say, 0.8.6's words stand."""
        if not isinstance(found, dict):return found
        try:
            if not hasattr(self, '_voice'):self._voice = self.read('voice.say', {'id': self.ident})[0]
            from . import voice_column
            found, n = voice_column.restate(name, found, self._voice)
        except Exception:  # noqa: BLE001 - her floor never takes the panel down: 0.8.6's words stand
            return found
        self.voice_said = getattr(self, 'voice_said', 0) + n
        return found

    @staticmethod
    def refusal(why):
        """Why a section could not be worked out, in her words (never an operation's name)."""
        if str(why).startswith('That card is not a goal'):return say('not_goal')
        return say('could_not', why=why)

    def sides(self, lay, found):
        """For and Against: the sources on each side, each a place to click that selects it on the Field."""
        if found.get('kind') != 'claim':return
        from .shell2 import sentence
        for key, rows in (('for', found.get('for') or ()), ('against', found.get('against') or ())):
            if not rows:
                lay.addWidget(words_label('%s %s' % (WORDS[key], WORDS['nothing']), quiet=True));continue
            actions = {}
            parts = []
            for n, row in enumerate(rows):
                name = 'c%d' % n;actions[name] = (plain(str(row.get('title') or '')), lambda f=row.get('field'): self.light(f))
                parts.append('{%s}' % name)
            label = sentence('%s %s' % (WORDS[key], ', '.join(parts)), actions)
            label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);lay.addWidget(label)

    def rests(self, lay, found):
        from .shell2 import button
        counted = (found.get('counted') or {}).get('words')
        if counted:lay.addWidget(words_label(say('counted', words=counted)))
        proposed = (found.get('proposed') or {}).get('words') if found.get('proposed') else ''
        if proposed:lay.addWidget(words_label(say('proposed', words=proposed), quiet=True))
        items = found.get('rests_on') or ()
        for item in items:
            lay.addWidget(words_label(item.get('words', '')))
            if item.get('whose'):lay.addWidget(words_label(say('whose', whose=item['whose']), quiet=True))
            row = QHBoxLayout();row.setSpacing(6);answers = []
            if item.get('without'):
                b = button(say('without'), 'quiet', 'The answer worked out without it; nothing is changed')
                b.setObjectName('KasMindWithout');shown = words_label('', quiet=True);shown.hide();answers.append(shown)
                b.clicked.connect(lambda checked=False, w=item['without'], s=shown: self.reveal(s, say('without_said', words=w.get('words', ''))))
                row.addWidget(b)
            for other in item.get('with_other') or ():
                b = button(say('with_other', name=other.get('name') or other.get('title', '')), 'quiet', 'The answer with the other revision; nothing is changed')
                b.setObjectName('KasMindWithOther');shown = words_label('', quiet=True);shown.hide();answers.append(shown)
                b.clicked.connect(lambda checked=False, o=other, s=shown: self.reveal(s, say('other_said', name=o.get('name') or o.get('title', ''), words=o.get('words', ''))))
                row.addWidget(b)
            row.addStretch(1);lay.addLayout(row)
            for shown in answers:lay.addWidget(shown)
        for text in found.get('unset') or ():lay.addWidget(words_label(text, quiet=True))
        if not items and not found.get('unset'):lay.addWidget(words_label(say('nothing_rests'), quiet=True))

    def reveal(self, label, text):
        put(label, text);label.show();self.adjustSize()

    def way_button(self, lay, outcome):
        """One way of a choice that decides it: the button carries its exact outcome; a press selects that revision's sheet."""
        from .shell2 import button
        b = button(plain(str(outcome.get('words') or '')), 'quiet', 'Select this revision’s sheet on the Field; nothing is changed')
        b.setObjectName('KasMindWay');b.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        titles = [str(v) for _, v in outcome.get('choices') or ()]
        shown = words_label('', quiet=True);shown.hide()

        def pressed():
            view = self.view()
            hit = next((o for o in (view.field.objects if view is not None else ()) if o.title in titles), None)
            if hit is not None:
                view.field.select(hit.id);view._layout();view._reveal();view._describe();view.update()
                self.reveal(shown, say('way_pressed', title=hit.title))
        b.clicked.connect(pressed);lay.addWidget(b, 0, Qt.AlignLeft);lay.addWidget(shown)

    # ---- the Field: selection, the lit wires, the walk -------------------------------------------------------------------------
    def view(self):
        """The Field's view, brought to the front if it is not (asking Why happens on the Field, but a goal's panel may stay
        open while you look elsewhere)."""
        page = getattr(self.host, 'field_page', None)
        if not getattr(self.host, '_field_active', False):
            try:
                from .field_page import show_field
                page = show_field(self.host)
            except Exception:  # noqa: BLE001 - no Field in this window: the panel still reads
                page = None
        return getattr(page, 'view', None)

    def prepare_walk(self, found):
        """The proof's wires on the Field, and the walk: the cards from the source end in to this one."""
        view = self.view()
        on = {o.id for o in view.field.objects} if view is not None else set()
        wires = [dict(w) for w in found.get('route') or () if w['source'] in on and w['target'] in on]
        walk = [card for card in found.get('walk') or () if card in on]
        if self.ident in on and view is not None:      # a card of her mind: the wires into it from the proof's own cards
            near = set(walk) | {l.get('field') for l in found.get('leaves') or () if l.get('field')}
            top = max([w['hop'] for w in wires] + [-1]) + 1
            for link in view.field.fed_by(self.ident):
                if link.source in near and not any(w['source'] == link.source and w['target'] == self.ident for w in wires):
                    wires.append({'source': link.source, 'target': self.ident, 'hop': top})
            if self.ident not in walk:
                walk = [c for c in walk if c in near] + [self.ident]
                for w in wires:
                    if w['source'] not in walk:walk.insert(0, w['source'])
        self.wires = wires;self.walk = walk;self.step = -1
        self.light(self.ident if self.ident in on else '', quiet=True)

    def light(self, card, upto=None, quiet=False):
        view = self.view()
        if view is None:
            if not quiet:put(self.walk_words, say('no_field'))
            return []
        wires = self.wires if upto is None else [w for w in self.wires if w['source'] in upto and w['target'] in upto]
        owner = card if card and view.field.get(card) is not None else (self.ident if view.field.get(self.ident) is not None else '')
        lit = view.light_proof(owner, wires)
        try:view._layout();view._reveal();view._describe();view.update()
        except Exception:  # noqa: BLE001 - bringing it into view is a nicety
            pass
        return lit

    def choose_line(self, row):
        for other in self.lines:other.set_chosen(other is row)
        card = row.card or self.ident
        if card in self.walk:self.step = self.walk.index(card);self.said_walk()
        self.light(card)

    def walk_by(self, step):
        if not self.walk:self.said_walk();return
        self.step = max(0, min(len(self.walk) - 1, self.step + step))
        card = self.walk[self.step]
        self.light(card, upto=set(self.walk[:self.step + 1]))
        for row in self.lines:row.set_chosen(bool(row.card) and row.card == card)
        self.said_walk()

    def said_walk(self):
        if not self.walk:
            put(self.walk_words, say('walk_none'));self.back.setEnabled(False);self.next.setEnabled(False);return
        self.back.setEnabled(self.step > 0);self.next.setEnabled(self.step < len(self.walk) - 1)
        if self.step < 0:put(self.walk_words, say('walk_start'));return
        view = self.view();card = self.walk[self.step]
        obj = view.field.get(card) if view is not None else None
        put(self.walk_words, say('walk', n=self.step + 1, count=len(self.walk), title=(obj.title if obj is not None else card)[:120]))

    def put_away(self):
        if getattr(self.host, 'mind_panel', None) is self:self.host.mind_panel = None
        self.hide();self.deleteLater()


def show_why(host, card):
    """Her panel for one card (a FieldObject, or a card's id such as 'claim:…' or 'goal:…'), in her column, in place of the one
    shown before. Returns the panel."""
    ident = getattr(card, 'id', None) or str(card)
    title = getattr(card, 'title', '') or ident
    old = getattr(host, 'mind_panel', None)
    if old is not None:
        try:old.hide();old.deleteLater()
        except RuntimeError:  # it left with Talk's earlier exchanges
            pass
    panel = MindPanel(host, ident, title)
    host.mind_panel = panel
    face = getattr(getattr(host, 'shell2', None), 'face', None)
    if face is not None:
        face.add(panel)
    else:                                  # a window with no column of hers: the panel stands on its own, beside the work
        panel.setParent(host, Qt.Tool);panel.setWindowTitle(WORDS['tab_why']);panel.resize(460, 620);panel.show()
    panel.start()
    for ms in (60, 200):QTimer.singleShot(ms, lambda: _into_view(face, panel))      # after her column's own scroll and fold
    return panel


def _into_view(face, panel):
    """Her column scrolled so the panel's head (its sections and the walk) is at the top, however long its proof."""
    try:
        scroll = getattr(face, 'scroll', None)
        if scroll is None or scroll.widget() is None:return
        from PySide6.QtCore import QPoint
        scroll.verticalScrollBar().setValue(max(0, panel.mapTo(scroll.widget(), QPoint(0, 0)).y() - 8))
    except RuntimeError:  # the panel was put away meanwhile
        pass
