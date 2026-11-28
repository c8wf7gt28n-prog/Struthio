"""The mark line and the fold (0.8.7, "Kas's mind with the model, interwoven"; slice A4, lane A).

Whose words, on screen (design 5.1). Model words reach her column only here, never through her plain renderer (shell2's
leaded and Bubble, mind_panel_qt.put refuse them: model_words.plain_only):

  ModelWords     the model's words with one quiet mark line above them, in words, never an icon alone (model_words.MARKS):
                 read by the model, checked against your desk · worded by the model · every fact from the receipt ·
                 worded by the model, kept by you · your wording · the model's own words, from its memory, not from your
                 files (Talk) · the model's answer, exactly as it gave it (in the fold). The words stand inside a frame with
                 a dotted rule at its left (a shape, not only a colour); the frame and its words carry the property
                 'modelMarked', so a sweep can tell every model-marked span on screen. In Talk, numbers in the model's
                 words are underlined and one quiet line says they are not on the desk.
  Fold           "What I asked the model": exactly the stored turn (brain.turn/1, read with brain.turn.get), never the
                 model's account of itself: what she sent (the four messages as stored, withheld lines shown as withheld),
                 what it answered (the raw answer, model-marked), what she checked (her verdict and each check), two views
                 when hers and the model's differ, how long it took (the time, her price and deadline, the tokens read,
                 re-read and written) and the model's key; and Forget this turn (brain.turn.forget, approve: your press is
                 the approval), after which only the tombstone is shown.
  MarkLine       the mark line alone, for a card of hers that carries model words placed elsewhere on it.

Placed in her column by mind_panel_qt (place(), and Line for a line that is model words), her_hand_qt (the GOAL turn's
mark and fold), shell2 (Talk: show_in()) and brain_qt (the ledger and the account in the Brain room).

Every word of hers here is a template registered with mind_words (WORDS); no template carries a mark's words. A string in
the fold that echoes the model's answer (a check's detail, a second view) is shown model-marked, not as hers.
"""
from __future__ import annotations

import html
import json
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSizePolicy, QVBoxLayout,
                               QWidget)

from . import boss_theme as bt
from . import mind_words, model_words
from .model_words import MARKS, Marked, ModelSaid

WORDS = {
    'fold': 'What I asked the model',
    'sent': 'What I sent',
    'answered': 'What it answered',
    'checked': 'What I checked',
    'views': 'Two views',
    'took': 'How long it took',
    'model': 'The model',
    'forget': 'Forget this turn',
    'role_system': 'My fixed rules for this kind of question',
    'role_stable': 'What I kept for it',
    'role_ready': 'Its line before the question',
    'role_last': 'The question',
    'no_answer': 'It gave no answer.',
    'verdict': 'My check: {state}.',
    'outcome': 'How it ended: {outcome}.',
    'instead': 'What I did instead: {fallback}.',
    'why': 'The reason, as recorded: {why}.',
    'passed': '{name}: passed.',
    'not_passed': '{name}: did not pass.',
    'detail': 'Detail: {detail}',
    'hers': 'Mine: {view}',
    'its': 'The model’s: {view}',
    'views_why': 'Why they differ: {why}',
    'time': 'It took {elapsed}. I had priced it at {price}, with a deadline of {deadline}.',
    'time_stop': 'It took {elapsed}. It had no deadline; Stop was yours.',
    'tokens': 'Tokens read: {prompt}, of which {kept} were kept from before and {new} were new. At most {cap} to write.',
    'timings': 'The worker counted {read} read, {reused} re-used and {written} written.',
    'key': 'Model {model}, key {key}.',
    'forgotten': 'Forgotten. Only this is kept: a {kind} question was asked, and how it ended: {outcome}.',
    'could_not': 'I could not read that turn: {why}',
    'not_forgotten': 'I did not forget it: {why}',
    'numbers': 'Numbers in its words are not on the desk.',
    'forget_tip': 'Forget this turn: its messages, its answer and my checks go. Only that it was asked, and how it ended, stays',
}
_TURN = 'the stored turn (brain.turn/1, brain.turn.get)'
NUMBERS = {key: {slot: _TURN for slot in mind_words.slots(text)} for key, text in WORDS.items()}
mind_words.register('model_marks_qt', WORDS, kind='sentence', numbers=NUMBERS)

STATE_WORDS = {'TAKEN': 'taken', 'TRIMMED': 'taken in part', 'REFUSED': 'refused', 'UNSETTLED': 'not settled, so it was yours to say',
               'TRIPPED': 'refused: asked the other way round, it answered differently'}
OUTCOME_WORDS = {**STATE_WORDS, 'LATE': 'late, past its deadline', 'FAILED': 'no answer came from the model'}
FALLBACK_WORDS = {'ASK_OWNER': 'I asked you', 'DEFAULT_READ': 'I took the read I take without it',
                  'PLAIN_WORDS': 'I said it in my plain words', 'CANNOT_TELL': 'I said I cannot tell',
                  'NOT_OFFERED': 'I did not offer it', 'PATTERNS': 'I read the page by its patterns',
                  'PLACES': 'I showed the places'}
ROLE_KEYS = ('role_system', 'role_stable', 'role_ready', 'role_last')
NUMBER = re.compile(r'\d[\d,.:/-]*\d|\d')
TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{3,}')
PIECE = re.compile(r'[A-Za-z0-9]{4,}')
TURN_ID = re.compile(r'[0-9a-f]{32}')


def say(which, /, **slots):
    return WORDS[which].format(**slots)


def _colour(name, default):
    return getattr(bt, name, default)


def _seconds(ms):
    """Whole milliseconds as '1.4 s' (tenths, integer arithmetic, rounded half up)."""
    tenths = (max(0, int(ms or 0)) + 50) // 100
    return '%d.%d s' % divmod(tenths, 10)


def plain_label(text, quiet=False):
    """Her words in a label (through plain_only: model words are refused here)."""
    label = QLabel();label.setWordWrap(True);label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse);label.setTextFormat(Qt.PlainText)
    text = model_words.plain_only(text)
    label.setProperty('plain', str(text));label.setText(str(text))
    if quiet:label.setStyleSheet('color:%s;' % _colour('QUIET', '#8a8a8a'))
    return label


# -- the mark line ------------------------------------------------------------------------------------------------------------
class MarkLine(QLabel):
    """One quiet line naming whose words follow (model_words.MARKS), in words."""

    def __init__(self, mark='CHECKED'):
        if mark not in MARKS:raise ValueError('MARK_UNKNOWN: %s' % mark)
        super().__init__(MARKS[mark]);self.mark = mark
        self.setObjectName('KasModelMark');self.setProperty('modelMark', mark);self.setWordWrap(True)
        self.setTextFormat(Qt.PlainText);self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setStyleSheet('color:%s; font-style:italic;' % _colour('QUIET', '#8a8a8a'))
        self.setAccessibleName('Whose words: ' + MARKS[mark])


def _as_marked(value, mark):
    if isinstance(value, Marked):
        key = next((k for k, words in MARKS.items() if words == value.mark), mark)
        return value.text, key
    if isinstance(value, ModelSaid):return model_words.marked(value, mark).text, mark
    raise TypeError('MODEL_WORDS_ONLY: ModelWords shows model words (ModelSaid or Marked), never her own')


class ModelWords(QFrame):
    """Model words with their mark line, in a frame with a dotted rule at its left. Not her words: the frame and the
    words carry 'modelMarked', and the words are never put in a label's 'plain' property (what reads her words back)."""

    def __init__(self, said, mark='CHECKED'):
        super().__init__();self.setObjectName('KasModelSaid');self.setProperty('modelMarked', True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet('QFrame#KasModelSaid {border:0; border-left:2px dotted %s; background:transparent;}'
                           % _colour('LINE_STRONG', '#999999'))
        box = self.box = QVBoxLayout(self);box.setContentsMargins(8, 2, 2, 2);box.setSpacing(2)
        self.line = None;self.body = QLabel();self.note = None
        self.body.setObjectName('KasModelWords');self.body.setProperty('modelMarked', True);self.body.setWordWrap(True)
        self.body.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);self.body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body.setTextFormat(Qt.RichText)        # rich text: her column's folding leaves it as it is
        box.addWidget(self.body)
        self.set_said(said, mark)

    def set_said(self, said, mark='CHECKED'):
        text, key = _as_marked(said, mark)
        if self.line is None or self.line.mark != key:
            if self.line is not None:self.line.deleteLater()
            self.line = MarkLine(key);self.line.setProperty('modelMarked', True);self.box.insertWidget(0, self.line)
        self.text = text;self.mark = key
        self.body.setProperty('model', text)
        numbers = key == 'OWN' and bool(NUMBER.search(text))
        self.body.setText(self.rich(text, underline=numbers))
        self.body.setAccessibleName(MARKS[key])
        if numbers and self.note is None:
            self.note = plain_label(say('numbers'), quiet=True);self.note.setProperty('modelMarked', True);self.box.addWidget(self.note)
        elif not numbers and self.note is not None:
            self.note.deleteLater();self.note = None
        return self

    @staticmethod
    def rich(text, underline=False):
        """The words escaped as they are (line breaks kept); with underline, each number underlined (a shape: they are
        not on the desk)."""
        out = [];at = 0
        for m in (NUMBER.finditer(text) if underline else ()):
            out.append(html.escape(text[at:m.start()], quote=False))
            out.append('<span style="text-decoration:underline">%s</span>' % html.escape(m.group(), quote=False));at = m.end()
        out.append(html.escape(text[at:], quote=False))
        return '<p style="margin:0;white-space:pre-wrap">' + ''.join(out).replace('\n', '<br>') + '</p>'


def show_in(bubble, said, mark='OWN', lead=None):
    """Model words into one of her column's bubbles (shell2.Bubble): her own line (lead, her plain words) stays in the
    bubble's text, or is hidden when there is none, and the model's words go under it with their mark. Called again with
    more words (a streamed draft), the same ModelWords is updated."""
    found = getattr(bubble, 'model_words', None)
    if lead:
        bubble.set_text(lead);bubble.text.show()
    else:
        bubble.text.setProperty('plain', '');bubble.text.setText('');bubble.text.hide()
    if found is not None:
        try:return found.set_said(said, mark)
        except RuntimeError:  # it left with Talk's earlier exchanges
            pass
    words = ModelWords(said, mark);bubble.model_words = words
    bubble.box.insertWidget(bubble.box.indexOf(bubble.text) + 1, words)
    return words


def mark_card(card, mark='CHECKED'):
    """The mark line on a card of hers (a her_hand_qt card): the model's part in what the card says, in words."""
    line = MarkLine(mark)
    box = getattr(card, 'box', None) or card.layout()
    if box is not None:box.addWidget(line)
    return line


# -- the fold: what I asked the model -----------------------------------------------------------------------------------------
def _echoes(text, answer):
    """Whether `text` repeats words of the model's raw answer (a token of four or more letters or digits)."""
    if not answer or not text:return False
    tokens = set(TOKEN.findall(answer)) | set(PIECE.findall(answer))
    return any(t in text for t in tokens)


def _view(value):
    """A desk object as text for the fold (a stored ModelSaid shows as model words elsewhere, never here)."""
    if isinstance(value, str):return value
    try:return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):return str(type(value).__name__)


def _has_model(value):
    if isinstance(value, dict):
        return 'model_said' in value or any(_has_model(v) for v in value.values())
    if isinstance(value, list):return any(_has_model(v) for v in value)
    return False


def kernel_of(host):
    """The window's Kernel and the operator principal (as mind_panel_qt reads)."""
    from .engineering_kernel import operator
    kernel = getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)
    if kernel is None:
        from .engine import engineering
        kernel = engineering(host.root)
    return kernel, operator()


class Fold(QFrame):
    """'What I asked the model' for one stored turn: closed at first; opened, it shows the turn exactly as stored."""

    def __init__(self, record=None, dispatch=None, error=''):
        super().__init__();self.setObjectName('KasModelFold');self.record = record;self.dispatch = dispatch
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        box = self.box = QVBoxLayout(self);box.setContentsMargins(0, 2, 0, 2);box.setSpacing(3)
        self.toggle = QPushButton('› ' + say('fold'));self.toggle.setObjectName('KasModelFoldToggle')
        self.toggle.setCheckable(True);self.toggle.setProperty('arcButton', 'quiet');self.toggle.setCursor(Qt.PointingHandCursor)
        self.toggle.toggled.connect(self.open);box.addWidget(self.toggle, 0, Qt.AlignLeft)
        self.inner = QWidget();self.lay = QVBoxLayout(self.inner);self.lay.setContentsMargins(10, 0, 0, 0);self.lay.setSpacing(4)
        self.inner.hide();box.addWidget(self.inner)
        self.error = error;self.built = False

    @classmethod
    def for_turn(cls, host, ident, kernel=None, principal=None):
        """The fold for a turn by its id, read with brain.turn.get (a read: asking is not an event)."""
        try:
            if kernel is None:kernel, principal = kernel_of(host)
        except Exception as exc:  # noqa: BLE001 - no Kernel to read: the fold says so
            return cls(None, None, str(exc)[:200])

        def dispatch(op, args):
            return kernel.dispatch(op, args, principal)
        got = dispatch('brain.turn.get', {'id': ident}) if ident else {'ok': False, 'error': {'message': 'no turn was recorded'}}
        if not got.get('ok'):
            return cls(None, dispatch, str((got.get('error') or {}).get('message') or 'it could not be read')[:200])
        return cls(got['result']['turn'], dispatch)

    def open(self, shown):
        self.toggle.setText(('⌄ ' if shown else '› ') + say('fold'))
        if shown and not self.built:self.build()
        self.inner.setVisible(shown);self.adjustSize()

    def clear(self):
        while self.lay.count():
            item = self.lay.takeAt(0);w = item.widget()
            if w is not None:w.hide();w.setParent(None);w.deleteLater()

    def heading(self, key):
        label = plain_label(say(key));label.setStyleSheet('font-weight:600;');self.lay.addWidget(label)

    def words(self, text, quiet=False):
        self.lay.addWidget(plain_label(text, quiet));return text

    def exact(self, text, name):
        """Stored text shown exactly as stored, in a box that keeps every character."""
        box = QPlainTextEdit();box.setReadOnly(True);box.setPlainText(text);box.setObjectName('KasModelFoldText')
        box.setAccessibleName(name);box.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        lines = max(1, min(10, text.count('\n') + 1 + len(text) // 70))
        box.setFixedHeight(box.fontMetrics().lineSpacing() * lines + 12);self.lay.addWidget(box)
        return box

    def piece(self, key, slot, value, answer, quiet=True):
        """Her line with a stored string in its slot; when the string echoes the model's answer (or holds stored model
        words), her line names it and the string itself is shown model-marked under it, never as her words."""
        text = _view(value)
        if _has_model(value) or _echoes(text, answer):
            self.words(say(key, **{slot: '(its words, below)'}), quiet)
            self.lay.addWidget(ModelWords(ModelSaid(text, 'RAW'), 'RAW'))
        else:
            self.words(say(key, **{slot: text}), quiet)

    def build(self):
        self.built = True;self.clear();r = self.record
        if r is None:
            self.words(say('could_not', why=self.error or 'nothing was recorded'));return
        if r.get('state') == 'FORGOTTEN':
            self.words(say('forgotten', kind=r.get('kind', ''), outcome=OUTCOME_WORDS.get(r.get('outcome'), r.get('outcome', ''))));return
        from . import turns
        said = turns.said_of(r);answer = said.for_check() if said is not None else ''
        self.heading('sent')
        for n, m in enumerate(r.get('messages') or ()):
            self.words(say(ROLE_KEYS[n]) if n < len(ROLE_KEYS) else m.get('role', ''), quiet=True)
            self.exact(m.get('content', ''), say(ROLE_KEYS[n]) if n < len(ROLE_KEYS) else m.get('role', ''))
        self.heading('answered')
        if said is not None:self.lay.addWidget(ModelWords(said, 'RAW'))
        else:self.words(say('no_answer'), quiet=True)
        self.heading('checked')
        verdict = r.get('verdict') or {}
        if verdict:self.words(say('verdict', state=STATE_WORDS.get(verdict.get('state'), verdict.get('state', ''))))
        for check in verdict.get('checks') or ():
            name, passed = (list(check) + [None, None])[:2] if isinstance(check, (list, tuple)) else (str(check), None)
            detail = check[2] if isinstance(check, (list, tuple)) and len(check) > 2 else None
            self.piece('passed' if passed else 'not_passed', 'name', str(name), answer)
            if detail not in (None, '', [], {}):self.piece('detail', 'detail', detail, answer)
        self.words(say('outcome', outcome=OUTCOME_WORDS.get(r.get('outcome'), r.get('outcome', ''))))
        if r.get('fallback'):self.words(say('instead', fallback=FALLBACK_WORDS.get(r['fallback'], r['fallback'])))
        if r.get('why'):self.piece('why', 'why', r['why'], answer)
        views = r.get('second_view')
        if isinstance(views, dict) and views:
            self.heading('views')
            for key, name, slot in (('hers', 'hers', 'view'), ('model', 'its', 'view'), ('why', 'views_why', 'why')):
                if key in views:self.piece(name, slot, views[key], answer)
        self.heading('took')
        if r.get('deadline_ms'):
            self.words(say('time', elapsed=_seconds(r.get('elapsed_ms')), price=_seconds(r.get('price_ms')), deadline=_seconds(r.get('deadline_ms'))))
        else:
            self.words(say('time_stop', elapsed=_seconds(r.get('elapsed_ms'))))
        t = r.get('tokens') or {}
        if t:self.words(say('tokens', prompt=t.get('prompt', 0), kept=t.get('kept_expected', 0), new=t.get('new', 0), cap=t.get('answer_cap', 0)), quiet=True)
        timings = r.get('timings') or {}
        if timings:
            self.words(say('timings', read=timings.get('prompt_n', 0), reused=timings.get('cache_n', 0), written=timings.get('predicted_n', 0)), quiet=True)
        self.heading('model')
        self.words(say('key', model=r.get('model') or '', key=str(r.get('key') or '')[:12]), quiet=True)
        if self.dispatch is not None:
            row = QHBoxLayout();row.setContentsMargins(0, 0, 0, 0)
            forget = QPushButton(say('forget'));forget.setObjectName('KasModelForget');forget.setProperty('arcButton', 'quiet')
            forget.setToolTip(WORDS['forget_tip']);forget.clicked.connect(self.forget);row.addWidget(forget);row.addStretch(1)
            holder = QWidget();holder.setLayout(row);self.lay.addWidget(holder)

    def forget(self):
        """Your press is the approval (brain.turn.forget is approve scope and always asks): the turn becomes a tombstone."""
        got = self.dispatch('brain.turn.forget', {'id': self.record['id']})
        if not got.get('ok'):
            self.words(say('not_forgotten', why=str((got.get('error') or {}).get('message') or '')[:200]));return None
        self.record = got['result']['turn'];self.build();self.adjustSize()
        return self.record


# -- placing them in her column -----------------------------------------------------------------------------------------------
def _model_items(found):
    """(text-or-said, mark, turn) for every piece of model words in a read's result: a Marked or ModelSaid value, or a stored
    {'model_said': ...} beside an optional 'mark' (a MARKS key) and 'turn' id."""
    out = []

    def walk(value, mark='CHECKED', turn=''):
        if isinstance(value, (Marked, ModelSaid)):
            out.append((value, mark, turn));return
        if isinstance(value, dict):
            if 'model_said' in value and set(value) <= {'model_said', 'kind'}:
                out.append((ModelSaid.from_record(value), mark, turn));return
            here_mark = value.get('mark') if value.get('mark') in MARKS else mark
            here_turn = value.get('turn') if isinstance(value.get('turn'), str) else turn
            for k, v in value.items():
                if k not in ('mark', 'turn'):walk(v, here_mark, here_turn)
        elif isinstance(value, (list, tuple)):
            for v in value:walk(v, mark, turn)
    walk(found)
    return out


def place(panel, lay, found):
    """Her column panel (mind_panel_qt): the model's part of a read's result, each piece with its mark line, and a fold for
    every turn it names (its 'turns' ids and each piece's 'turn'). Returns the number of pieces placed."""
    if not isinstance(found, dict):return 0
    items = _model_items({k: v for k, v in found.items() if k not in ('turns', 'lines')})      # a line shows its own (Line)
    turns_named = [t for t in (found.get('turns') or ()) if isinstance(t, str)]
    for line in found.get('lines') or ():
        if isinstance(line, dict) and isinstance(line.get('turn'), str) and line['turn'] not in turns_named:
            turns_named.append(line['turn'])
    for said, mark, turn in items:
        lay.addWidget(ModelWords(said, mark))
        if turn and turn not in turns_named:turns_named.append(turn)
    host = getattr(panel, 'host', None)
    for ident in [t for t in turns_named if TURN_ID.fullmatch(t)]:
        try:
            kernel, principal = panel.kernel()
            lay.addWidget(Fold.for_turn(host, ident, kernel, principal))
        except Exception:  # noqa: BLE001 - a fold that cannot be read never takes the panel down
            lay.addWidget(Fold(None, None, 'it could not be read'))
    return len(items) + len([t for t in turns_named if TURN_ID.fullmatch(t)])
