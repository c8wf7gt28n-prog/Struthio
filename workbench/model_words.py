"""Whose words: the type every string a model wrote is held in (0.8.7, "Kas's mind with the model, interwoven"; slice E0).

Her rule is "the model proposes; the system disposes". Free model text survives only as `ModelSaid`, which is not a `str`:
`str()`, `format()`, f-strings, `%s`, `+` with a string, iteration and `in` all raise, so no code can show it as her words
by accident. It reaches the screen only through `marked()`, which pairs it with its mark line in words, and it reaches a
checker only through `ModelSaid.for_check()`. Her column's plain renderer (shell2.leaded, shell2.Bubble) calls
`plain_only()`, which refuses a `ModelSaid` and a `Marked`. Thinking text, if a model ever produces any, is ModelSaid too.

The marks (design 5.1), one quiet line per reply, in words, never an icon alone:
  CHECKED  read by the model, checked against your desk
  WORDED   worded by the model · every fact from the receipt
  KEPT     worded by the model, kept by you
  YOURS    your wording
  OWN      the model's own words, from its memory, not from your files      (Talk only)
Her plain words carry no mark at all.

The strict parsers below read the terse answer lines the kinds' grammars allow (no free whitespace); anything else is
`Invalid`, and nothing acts on it. They are shared by the kinds lanes B and C register; a kind with its own answer shape
writes its parser in its own module and raises `Invalid` the same way.

This module, turns.py and every registered checker never import clip or gemini_engineer: Kas's checked questions can never
go to a cloud model.
"""
from __future__ import annotations

import hashlib
import re

MARKS = {
    'CHECKED': 'read by the model, checked against your desk',
    'WORDED': 'worded by the model · every fact from the receipt',
    'KEPT': 'worded by the model, kept by you',
    'YOURS': 'your wording',
    'OWN': "the model's own words, from its memory, not from your files",
}
MOST = 32000          # characters: local_brain.completion refuses a longer answer before it is wrapped


class Invalid(ValueError):
    """A model answer that is not in its kind's shape. Nothing acts on it; the turn is REFUSED and the fallback stands."""


class ModelSaid:
    """Text a model wrote. Not a str; it has no string form. `kind` is the turn kind that asked; `turn` its record id."""
    __slots__ = ('_text', '_kind', '_turn')

    def __init__(self, text, kind='', turn=''):
        if isinstance(text, ModelSaid):text = text._text
        if not isinstance(text, str):raise TypeError('MODEL_SAID_TEXT: a model answer is text')
        if len(text) > MOST:raise ValueError('MODEL_SAID_TOO_LONG')
        object.__setattr__(self, '_text', text);object.__setattr__(self, '_kind', str(kind or ''))
        object.__setattr__(self, '_turn', str(turn or ''))

    def __setattr__(self, name, value):raise AttributeError('ModelSaid is fixed once written')

    # -- no string form: these all refuse ---------------------------------------------------------------------------------
    def __str__(self):raise TypeError('MODEL_SAID_NOT_HER_WORDS: show it with model_words.marked(), never as her words')

    def __format__(self, spec):raise TypeError('MODEL_SAID_NOT_HER_WORDS: show it with model_words.marked(), never as her words')

    def __add__(self, other):raise TypeError('MODEL_SAID_NOT_HER_WORDS: it cannot be joined to her words')

    __radd__ = __add__
    __mod__ = __add__
    __rmod__ = __add__
    __iter__ = None       # iteration and `in` raise TypeError: the text cannot be taken out letter by letter

    def __repr__(self):
        """No words in the repr (logs and tracebacks are screens too): its length, kind and a short digest."""
        return 'ModelSaid(%d characters%s, sha256 %s)' % (len(self._text), ' of ' + self._kind if self._kind else '',
                                                          self.digest()[:12])

    # -- what may be asked of it --------------------------------------------------------------------------------------------
    def __len__(self):return len(self._text)

    def __bool__(self):return bool(self._text)

    def __eq__(self, other):return isinstance(other, ModelSaid) and other._text == self._text and other._kind == self._kind

    def __hash__(self):return hash(('ModelSaid', self._text, self._kind))

    @property
    def kind(self):return self._kind

    @property
    def turn(self):return self._turn

    def digest(self):return hashlib.sha256(self._text.encode('utf-8')).hexdigest()

    def for_check(self):
        """The raw text, for a parser or a checker only (it never goes to a screen from here)."""
        return self._text

    def with_turn(self, turn):return ModelSaid(self._text, self._kind, turn)

    def __copy__(self):return self      # fixed once written, so a copy is itself (dataclasses.asdict deep-copies values)

    def __deepcopy__(self, memo):return self

    def __reduce__(self):return (ModelSaid, (self._text, self._kind, self._turn))

    def for_record(self):
        """The stored form in a brain.turn/1 record: tagged, so whatever reads it back wraps it again (from_record)."""
        return {'model_said': self._text, 'kind': self._kind}

    @classmethod
    def from_record(cls, value, turn=''):
        if value is None:return None
        if not isinstance(value, dict) or set(value) - {'model_said', 'kind'} or not isinstance(value.get('model_said'), str):
            raise ValueError('MODEL_SAID_RECORD: not a stored model answer')
        return cls(value['model_said'], value.get('kind', ''), turn)


class Marked(tuple):
    """(text, mark): model words with their mark line in words. Made only by marked(); shown only by a renderer that draws
    the mark beside the words (model_marks_qt, lane A). Her column's plain renderer refuses it (plain_only)."""
    __slots__ = ()

    def __new__(cls, text, mark):return tuple.__new__(cls, (text, mark))

    @property
    def text(self):return self[0]

    @property
    def mark(self):return self[1]


def marked(said, mark='CHECKED'):
    """The one way ModelSaid becomes text for a screen: paired with its mark line (MARKS)."""
    if not isinstance(said, ModelSaid):raise TypeError('MARKED_NEEDS_MODEL_SAID: only model words are marked')
    if mark not in MARKS:raise ValueError('MARK_UNKNOWN: %s' % mark)
    return Marked(said.for_check(), MARKS[mark])


def is_model(value):
    """True for model words in either form (ModelSaid, Marked)."""
    return isinstance(value, (ModelSaid, Marked))


def plain_only(value):
    """Her column's plain renderer calls this first: her plain words pass through unchanged; model words are refused."""
    if is_model(value):
        raise TypeError('MODEL_SAID_NOT_HER_WORDS: her column shows model words only with their mark (model_words.marked)')
    return value


# -- strict parsers for terse answer lines ----------------------------------------------------------------------------------
NUMBER = re.compile(r'(?:0|[1-9][0-9]{0,3})')


def _text(said):
    if not isinstance(said, ModelSaid):raise TypeError('PARSE_NEEDS_MODEL_SAID: a parser reads only model words')
    text = said.for_check()
    if text.endswith('\n'):text = text[:-1]         # one closing line break is the only whitespace forgiven
    return text


def option(said, count, none=True):
    """One option number from 1 to `count`, or 0 for "none of these" when `none` allows it. The whole answer is the number."""
    text = _text(said)
    if not NUMBER.fullmatch(text):raise Invalid('NOT_ONE_NUMBER')
    n = int(text)
    if n == 0 and none:return 0
    if not 1 <= n <= count:raise Invalid('OUT_OF_RANGE')
    return n


def options(said, count, most, none=True):
    """1 to `most` different option numbers separated by single spaces, in the order written; (0,) alone for none."""
    text = _text(said)
    parts = text.split(' ')
    if not parts or any(not NUMBER.fullmatch(p) for p in parts):raise Invalid('NOT_NUMBERS')
    picked = tuple(int(p) for p in parts)
    if picked == (0,) and none:return ()
    if 0 in picked:raise Invalid('NONE_WITH_OTHERS')
    if len(picked) > most:raise Invalid('TOO_MANY')
    if len(set(picked)) != len(picked):raise Invalid('REPEATED')
    if any(not 1 <= n <= count for n in picked):raise Invalid('OUT_OF_RANGE')
    return picked


def word(said, allowed):
    """One word from `allowed`, exactly."""
    text = _text(said)
    if text not in allowed:raise Invalid('NOT_AN_ALLOWED_WORD')
    return text


def lines(said, most):
    """The answer cut at line breaks: 1 to `most` non-empty lines with no leading or trailing spaces."""
    text = _text(said)
    rows = text.split('\n')
    if not rows or len(rows) > most:raise Invalid('LINE_COUNT')
    if any(not r or r != r.strip(' \t') for r in rows):raise Invalid('LINE_SPACING')
    return tuple(rows)
