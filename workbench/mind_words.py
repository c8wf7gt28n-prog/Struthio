"""Her words (0.8.6 S6, "Kas's mind, no model", lane C): with no model, every sentence Kasandra says is a fixed template,
and her templates are kept and scanned here.

In 0.8.6 no model writes a word to you, so her templates are her character. The style sheet, from your three references:

  Marie Curie's precision           every number carries its receipt; she says what was measured and what was not;
                                    "cannot tell" is said plainly, never softened.
  Elizabeth II's composure          calm and brief; no alarm words and no exclamation marks; she says what is hers to do
  and sense of duty                 and what is yours, and never takes your decisions.
  Eleanor Roosevelt's plain warmth  plain words with the person first; she always offers the next step ("what would settle
                                    it is ...").

A module registers its templates with register(module, words, kind, numbers): `words` is {key: template}, `kind` says
where they show (a sentence, a card title, a Doubt row, a button, the footer), and `numbers` names, for each template, the
slots that carry a number and the record each number is read from. check() scans every registered template:

  - no exclamation mark;
  - no sentence over 30 words (a slot counts as one word);
  - every number slot carries a record reference, and no digit is written into a template's fixed words (a number only
    ever arrives through a slot that names its record);
  - none of the banned words of the design's section 5, outside quoted source words: "you should", "you must", "you will",
    "you have until", "entitled", "liable", "guilty", "safe", "safely", "recommend", "advice" (except in the fixed
    footer), "chance", "likely", "probability", "risk of", "odds".

0.8.7 C5: her character file (voice_character) feeds these rules. never_said() finds its never-say phrases and marks in
her own words, max_words() is the shorter of MAX_WORDS and the file's sentence length; check() and scan_text() read both.
The file adds to this floor and never lifts it. When voice_character is not in the program, the floor alone applies.

banned() and style() scan any text the same way (a finished card, its title, a Doubt row): what stands inside quotation
marks is the source's own words and is not hers, and the fixed footer is the one place "advice" is said.

FOOTER is the fixed footer of every card that rests on a CONTRACT or STATUTE_TEXT rule (footer_for), and INTRO the words
that introduce a rule's own quoted conclusion. Pure Python: no Qt, no Kernel, no model, no float.
"""
from __future__ import annotations

import importlib
import re
import string

FOOTER = 'Your reasoning over your records and the text you admitted. Not legal advice.'
FOOTED = ('STATUTE_TEXT', 'CONTRACT')            # the rule sorts whose cards always carry FOOTER
INTRO = 'On the rules you recorded, against the text you admitted:'
BANNED = ('you should', 'you must', 'you will', 'you have until', 'entitled', 'liable', 'guilty',
          'safe', 'safely', 'recommend', 'advice',
          'chance', 'likely', 'probability', 'risk of', 'odds')
MAX_WORDS = 30
KINDS = ('sentence', 'title', 'doubt', 'button', 'footer')
# Slot names that carry a number wherever they appear: each must name the record it is read from (numbers=).
NUMBER_SLOTS = frozenset(('value', 'amount', 'total', 'parts', 'over', 'spare', 'bound', 'end', 'limit', 'rows', 'n', 'count',
                          'start', 'day', 'room', 'low', 'high'))
STYLE = ("Marie Curie's precision: every number carries its receipt; cannot tell is said plainly.",
         "Elizabeth II's composure: calm and brief, no alarm words, no exclamation marks; yours is yours to decide.",
         "Eleanor Roosevelt's plain warmth: plain words, the person first, and always the next step.")
# Modules whose templates are registered here when they are imported (collect() imports them; a module that is not in
# this program yet is passed over, so a lane's templates join the scan the day its module lands).
MODULES = ('workbench.mind_words', 'workbench.rules', 'workbench.quotes', 'workbench.page_marks',  # 0.8.7 C2: pencil words
           'workbench.voice_character',            # 0.8.7 C5: her character file's own plain words
           'workbench.mind_panel_qt', 'workbench.demo_try',      # 0.8.6 W: her column panel's words, and the demos' card
           'workbench.one_question')                            # 0.8.7 B4: the one question's words

QUOTED = re.compile(r'“[^”]*”|"[^"]*"')
SENTENCE = re.compile(r'(?<=[.?!])\s+')
DIGIT = re.compile(r'\d')

_REGISTRY = {}           # (module, key) -> {'text', 'kind', 'numbers': {slot: record reference}}


def register(module, words, kind='sentence', numbers=None):
    """Keep `words` ({key: template}) as `module`'s templates of this kind. numbers: {key: {slot: the record it is read
    from}} for every slot that carries a number. Registering again replaces what was there."""
    if kind not in KINDS:raise ValueError('MIND_WORDS_KIND: one of %s' % ', '.join(KINDS))
    numbers = numbers or {}
    for key, text in words.items():
        if not isinstance(text, str):raise ValueError('MIND_WORDS_TEXT: a template is text')
        _REGISTRY[(module, key)] = {'text': text, 'kind': kind, 'numbers': dict(numbers.get(key) or {})}
    return words


def registered():
    """{(module, key): {'text', 'kind', 'numbers'}}, every template registered so far."""
    return dict(_REGISTRY)


def collect():
    """Import every module that registers templates, then return registered()."""
    for name in MODULES:
        try:importlib.import_module(name)
        except ImportError:continue
    return registered()


def say(module, key, **slots):
    """A registered template with its slots filled."""
    entry = _REGISTRY.get((module, key))
    if entry is None:raise KeyError('MIND_WORDS_UNKNOWN: %s.%s is not a registered template' % (module, key))
    return entry['text'].format(**slots)


def footer_for(sort):
    """The fixed footer a card resting on a rule of this sort carries, or ''."""
    return FOOTER if sort in FOOTED else ''


def slots(text):
    """The names of a template's slots, in order."""
    return [name for _, name, _, _ in string.Formatter().parse(text) if name]


def unquoted(text):
    """Her own words in `text`: quoted source words and the fixed footer set aside."""
    return QUOTED.sub(' ', str(text).replace(FOOTER, ' '))


def banned(text):
    """The banned words found in `text` outside quoted source words and the fixed footer, in BANNED's order."""
    plain = ' %s ' % ' '.join(unquoted(text).lower().replace('’', "'").split())
    return [word for word in BANNED if re.search(r'(?<![\w-])%s(?![\w-])' % re.escape(word), plain)]


def character():
    """Her character in force (0.8.7 C5, voice_character), or None when it is not in this program."""
    try:from . import voice_character
    except ImportError:return None
    return voice_character.current()


def max_words():
    """The most words in one of her sentences: MAX_WORDS, or fewer when her character file says so."""
    found = character()
    return min(MAX_WORDS, found['lengths']['sentence_words']) if found else MAX_WORDS


def never_said(text):
    """Her character file's never-say phrases and marks found in her own words in `text` (quoted source words and the fixed
    footer set aside), in the file's order; what BANNED and the exclamation-mark rule already catch is not said twice."""
    found = character()
    if not found:return []
    plain = ' %s ' % ' '.join(unquoted(text).lower().replace('’', "'").split())
    out = []
    for item in found['never_say']:
        phrase = item['phrase'].lower().replace('’', "'")
        if phrase in BANNED or phrase == '!':continue
        hit = (phrase in plain) if item['mark'] else re.search(r'(?<![\w-])%s(?![\w-])' % re.escape(phrase), plain)
        if hit:out.append(item['phrase'])
    return out


def sentences(text):
    return [s for s in SENTENCE.split(' '.join(str(text).split())) if s]


def style(text):
    """What in `text` breaks the style rules: an exclamation mark, a sentence over MAX_WORDS words (a slot is one word)."""
    problems = []
    plain = re.sub(r'\{[^{}]*\}', 'x', str(text))
    if '!' in unquoted(plain):problems.append('an exclamation mark')
    most = max_words()
    for sentence in sentences(plain):
        if len(sentence.split()) > most:problems.append('a sentence of %d words: %s' % (len(sentence.split()), sentence[:60]))
    return problems


def check(entries=None):
    """Every problem found in the registered templates: [(module, key, what)]. Empty when all is well."""
    entries = collect() if entries is None else entries
    out = []
    for (module, key), entry in sorted(entries.items()):
        text = entry['text']
        for word in banned(text):out.append((module, key, 'banned word: %s' % word))
        for problem in style(text):out.append((module, key, problem))
        for phrase in never_said(text):out.append((module, key, 'never-say (her character file): %s' % phrase))
        fixed = re.sub(r'\{[^{}]*\}', ' ', text)
        if DIGIT.search(unquoted(fixed)):out.append((module, key, 'a digit in the fixed words: a number arrives only through a slot'))
        for name in slots(text):
            base = name.split('.')[0].split('[')[0]
            if base in NUMBER_SLOTS and not entry['numbers'].get(base):out.append((module, key, 'number slot {%s} names no record' % base))
    return out


def scan_text(text):
    """What a finished card, title or Doubt row breaks: banned words outside quotes, and the style rules."""
    return (['banned word: %s' % w for w in banned(text)] + ['never-say (her character file): %s' % p for p in never_said(text)]
            + style(text))


register('mind_words', {'footer': FOOTER, 'intro': INTRO}, kind='footer')


# ---- 0.8.7 C4, her voice floor (voice_facts, voice_gate, voice_lexicon) ---------------------------------------------------
# Her plain-word frames are templates of a kind of their own, 'frame': a sentence pattern of slot names ({ANSWER},
# {MARGIN}) and joining words, each slot a clause the fact sheet (voice_facts) cut from a receipt. They and the fact sheet's
# clauses are registered here like every other template and swept by check(); frames() hands the frames to the voice gate,
# which checks every word of a frame before it is filled (one store, not a parallel one).
KINDS = KINDS + ('frame',)
MODULES = MODULES + ('workbench.voice_lexicon', 'workbench.voice_facts')
MODULES = MODULES + ('workbench.model_account', 'workbench.model_marks_qt')      # 0.8.7 A4: the account's and the fold's words
MODULES = MODULES + ('workbench.tables',)      # 0.8.7 C6a: tables that check themselves
MODULES = MODULES + ('workbench.crossrefs',)   # 0.8.7 C6b: cross-references


def frames(module=None):
    """{(module, key): text} of every registered frame (kind 'frame'), or one module's."""
    return {k: e['text'] for k, e in _REGISTRY.items() if e['kind'] == 'frame' and (module is None or k[0] == module)}
# ---- end of 0.8.7 C4 --------------------------------------------------------------------------------------------------------


# ---- 0.8.7 C3, Ask the Library (library_service) ------------------------------------------------------------------------------
# Her Library words (places, the desk's cut quote, "the places I looked at do not say") join the sweep like every other module's.
MODULES = MODULES + ('workbench.library_service',)
# ---- end of 0.8.7 C3 --------------------------------------------------------------------------------------------------------


# ---- 0.8.7 W7, the window wiring: her voice floor in her column; Ask the Library, tables and cross-references on screen ------
MODULES = MODULES + ('workbench.voice_column', 'workbench.library_qt')
# ---- end of 0.8.7 W7 --------------------------------------------------------------------------------------------------------
