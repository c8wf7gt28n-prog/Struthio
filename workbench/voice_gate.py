"""The voice gate (0.8.7 C4, "Kas's mind with the model, interwoven", lane C): a wording cannot hold a number, a date or a
verdict.

A frame (her plain words, a phrasing kept from the model later, or your own) joins the slots of a fact sheet
(voice_facts). Before it is filled, the gate checks every character and word of it (design 3.4, "FRAME: the gate"):

  characters  no line break, control, zero-width or direction character, and no letter outside plain Latin (a homoglyph
              cannot carry a banned word past the word lists)                                      FRAME_CHARACTERS
  slots       only the sheet's slots, written {NAME}; no other brace (no format tricks)            FRAME_BRACES
              each slot apart from the words beside it                                              FRAME_GLUE
              none unknown, none twice, every must slot present, {ANSWER} first                   FRAME_UNKNOWN_SLOT,
                                                                                                    FRAME_SLOT_TWICE,
                                                                                                    FRAME_MISSING_SLOT,
                                                                                                    FRAME_ANSWER_FIRST
  signs       outside the slots no digit, no quotation mark (quoted words would be read as the source's), no currency,
              unit or percent sign, no "!", only plain punctuation                                FRAME_DIGIT, FRAME_QUOTE,
                                                                                                    FRAME_SIGN, FRAME_EXCLAMATION
  words       none of voice_lexicon's classes (verdict, negation, hedge, booster, number words, calendar, units, advice,
              logic connectives, apology): WORD_<CLASS>; her never-say floor and her character's never-say list:
              NEVER_SAY; 0.8.6's banned words (mind_words.BANNED): BANNED. "sorry", "probably" and "it should be fine" are
              refused whatever the sheet.
  lengths     after the fill, no sentence over her character's most words (never over mind_words.MAX_WORDS), and no more
              sentences than her register allows (or than her own frame for the sheet needs)       LENGTH, SENTENCES

Then the desk fills the frame from the sheet, and **the second net** checks the words again (design 3.4):
  every number, spelled number, date and amount lies inside a slot span                            NET_NUMBER_OUTSIDE
  and is one the receipt gives that slot                                                            NET_NUMBER_UNDECLARED
  each slot reads exactly as the desk wrote it                                                      NET_SLOT_TEXT
  the first sentence opens with {ANSWER}, whose verdict is the heading's                           NET_HEADING
  her style rules hold on the whole (mind_words.scan_text)                                          NET_STYLE
  0.8.6's WORDS check (answer_check.check_words, 0.8.6 S7) takes the words against the sheet's desk values, when it is in
  this program (guarded: until it lands, the check is recorded as not run)                          NET_WORDS
If the second net fires, the frame passed the gate and the words still went wrong: that is a Graphite defect, recorded as
such (defect=True), and nothing is shown from it.

speak(sheet, frame=None) is what she says: the frame if it is given and kept, else her plain-word frame for the sheet
(voice_lexicon.frame_for), filled. A model's frame comes as model_words.ModelSaid and leaves only as model_words.marked()
(*worded by the model · every fact from the receipt*); her plain words carry no mark. Pure Python: no Qt, no Kernel, no
model, no float. model_calls is 0.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from . import mind_words, voice_facts, voice_lexicon

SLOT = re.compile(r'\{([A-Z][A-Z_]{0,23})\}')
PUNCTUATION = frozenset(" .,;:-'’—–()")
QUOTES = frozenset('"“”‘„«»‹›`')
EXCLAIM = frozenset('!¡')
DIGIT = re.compile(r'\d')
NUMBER = re.compile(r'\d+(?:[.,]\d+)*(?:/\d+)?')
DATE_WORDS = re.compile(r'(?<![A-Za-z])(?:%s)(?![A-Za-z])' % '|'.join(
    [m for m in voice_facts.MONTH_NAMES] + ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']), re.I)
FLOOR_BUDGETS = {'plain': 3, 'formal': 4, 'warm': 3}     # the starter's, used when her character file is not in this program
SOURCES = ('TEMPLATE', 'MODEL', 'OWNER')
OWNER_MARK = 'your wording'


@dataclass(frozen=True)
class Gate:
    """The gate's verdict on one frame against one fact sheet."""
    state: str                       # KEPT or REFUSED
    why: tuple = ()                  # the rules that refused it, in the order found
    checks: tuple = ()               # (name, passed, detail) for every check run
    text: str = ''                   # the filled words, when kept
    spans: tuple = ()                # (slot, start, end) in text
    defect: bool = False             # the second net fired: the gate passed it and the words still went wrong
    frame: str = ''

    def as_record(self):
        return {'state': self.state, 'why': list(self.why), 'reasons': [voice_lexicon.REASONS.get(w, w) for w in dict.fromkeys(self.why)],
                'checks': [list(c) for c in self.checks], 'text': self.text, 'spans': [list(s) for s in self.spans],
                'defect': self.defect, 'frame': self.frame}


# -- her character (0.8.7 C5), when it is in this program ------------------------------------------------------------------
def _character():
    try:
        from . import voice_character
    except ImportError:
        return None
    return voice_character


def never_say():
    """Her character's never-say phrases and marks ([] without the character file)."""
    vc = _character()
    if vc is None:return []
    try:return [x.get('phrase') or x.get('mark') or '' for x in vc.never_say() if x.get('phrase') or x.get('mark')]
    except (OSError, ValueError, AttributeError, TypeError):return []


def budgets(register):
    """{'sentences', 'words'} for a register: her character's, never past the 0.8.6 floor."""
    vc = _character()
    found = None
    if vc is not None:
        try:found = vc.budgets(register)
        except (OSError, ValueError, AttributeError, TypeError):found = None
    found = found or {'sentences': FLOOR_BUDGETS.get(register, 3), 'words': mind_words.MAX_WORDS}
    return {'sentences': int(found['sentences']), 'words': min(int(found['words']), mind_words.MAX_WORDS)}


# -- the frame, before the fill --------------------------------------------------------------------------------------------
def _text_of(frame):
    """(text, source) of a frame: a ModelSaid is read for the check only."""
    try:
        from .model_words import ModelSaid
    except ImportError:
        ModelSaid = None
    if ModelSaid is not None and isinstance(frame, ModelSaid):return frame.for_check(), 'MODEL'
    if not isinstance(frame, str):raise TypeError('VOICE_FRAME: a frame is text')
    return frame, None


def check_frame(frame, sheet, never=None):
    """[(rule, detail)]: every rule the frame breaks before it is filled; [] when it may be filled."""
    out = []
    if not frame or not frame.strip():return [('FRAME_EMPTY', 'nothing to fill')]
    bad = [ch for ch in frame if ch in '\n\r\t\v\f' or unicodedata.category(ch) in ('Cc', 'Cf', 'Zl', 'Zp', 'Co', 'Cs', 'Cn')
           or (unicodedata.category(ch) == 'Zs' and ch != ' ') or (not ch.isascii() and unicodedata.category(ch).startswith('L'))]
    if bad:out.append(('FRAME_CHARACTERS', ', '.join('U+%04X' % ord(ch) for ch in dict.fromkeys(bad))))
    names = [m.group(1) for m in SLOT.finditer(frame)]
    rest = SLOT.sub('', frame)
    if '{' in rest or '}' in rest:out.append(('FRAME_BRACES', 'a brace that is not a slot name'))
    for m in SLOT.finditer(frame):
        before = frame[m.start() - 1] if m.start() else ' ';after = frame[m.end()] if m.end() < len(frame) else ' '
        if before.isalnum() or after.isalnum():out.append(('FRAME_GLUE', '{%s} touches a word' % m.group(1)));break
    have = set(sheet.names)
    unknown = [n for n in names if n not in have]
    if unknown:out.append(('FRAME_UNKNOWN_SLOT', ', '.join(dict.fromkeys(unknown))))
    twice = [n for n in dict.fromkeys(names) if names.count(n) > 1]
    if twice:out.append(('FRAME_SLOT_TWICE', ', '.join(twice)))
    missing = [s.name for s in sheet.slots if s.must and s.name not in names]
    if missing:out.append(('FRAME_MISSING_SLOT', ', '.join(missing)))
    if not frame.lstrip().startswith('{ANSWER}'):out.append(('FRAME_ANSWER_FIRST', 'the frame starts %r' % frame.lstrip()[:12]))
    joining = SLOT.sub(' ', frame)
    if DIGIT.search(joining):out.append(('FRAME_DIGIT', ''.join(DIGIT.findall(joining))[:12]))
    if any(ch in QUOTES for ch in joining):out.append(('FRAME_QUOTE', 'a quotation mark outside the slots'))
    if any(ch in EXCLAIM for ch in joining):out.append(('FRAME_EXCLAMATION', '!'))
    # anything else that is not a letter or plain punctuation is a sign (the digits, quotes, "!", braces and the
    # characters above have their own rules)
    signs = [ch for ch in joining if not ch.isalpha() and not ch.isdigit() and ch not in PUNCTUATION and ch not in QUOTES
             and ch not in EXCLAIM and ch not in '{}' and unicodedata.category(ch) not in ('Cc', 'Cf', 'Zl', 'Zp', 'Zs')]
    if signs:out.append(('FRAME_SIGN', ''.join(dict.fromkeys(signs))))
    seen = set()
    for cls, word in voice_lexicon.classify(joining, tuple(never_say()) + tuple(never or ())):
        rule = 'NEVER_SAY' if cls == 'NEVER_SAY' else 'WORD_' + cls
        if (rule, word) in seen:continue
        seen.add((rule, word));out.append((rule, word))
    for word in mind_words.banned(joining):
        if ('BANNED', word) not in seen:seen.add(('BANNED', word));out.append(('BANNED', word))
    return out


# -- the fill -----------------------------------------------------------------------------------------------------------------
def fill(frame, sheet):
    """(text, spans): the frame with each slot replaced by its clause, a clause that opens a sentence capitalised. spans:
    ((slot, start, end), ...) in the text."""
    out, spans, at = [], [], 0
    for m in SLOT.finditer(frame):
        out.append(frame[at:m.start()])
        slot = sheet.slot(m.group(1))
        if slot is None:raise ValueError('VOICE_SLOT: the sheet has no {%s}' % m.group(1))
        so_far = ''.join(out).rstrip()
        text = slot.text
        if not so_far or so_far[-1] in '.?':text = text[:1].upper() + text[1:]
        start = len(''.join(out));out.append(text);spans.append((slot.name, start, start + len(text)))
        at = m.end()
    out.append(frame[at:])
    return ''.join(out), tuple(spans)


def _inside(spans, start, end):
    return next((s for s in spans if s[1] <= start and end <= s[2]), None)


def second_net(text, spans, sheet):
    """[(rule, detail)]: what is wrong with the filled words against the sheet; [] when they stand. Run after every fill."""
    out = []
    for name, start, end in spans:
        slot = sheet.slot(name);said = text[start:end]
        if slot is None or (said[:1].lower() + said[1:]) != (slot.text[:1].lower() + slot.text[1:]):out.append(('NET_SLOT_TEXT', name))
    declared = {}
    for slot in sheet.slots:
        declared[slot.name] = {t for f in slot.facts for t in NUMBER.findall(f.said)}
        declared[slot.name] |= {f.said.lower() for f in slot.facts if f.kind == 'count'}
    for m in NUMBER.finditer(text):
        span = _inside(spans, *m.span())
        if span is None:out.append(('NET_NUMBER_OUTSIDE', m.group(0)))
        elif m.group(0) not in declared.get(span[0], ()):out.append(('NET_NUMBER_UNDECLARED', '%s in {%s}' % (m.group(0), span[0])))
    for said, at in voice_lexicon.number_words(text):
        span = _inside(spans, *at)
        if span is None:out.append(('NET_NUMBER_OUTSIDE', said))
        elif said.lower() not in declared.get(span[0], ()):out.append(('NET_NUMBER_UNDECLARED', '%s in {%s}' % (said, span[0])))
    for m in DATE_WORDS.finditer(text):
        if _inside(spans, *m.span()) is None:out.append(('NET_NUMBER_OUTSIDE', m.group(0)))
    answer = sheet.slot('ANSWER')
    first = next((s for s in spans if s[0] == 'ANSWER'), None)
    if (answer is None or first is None or answer.state != sheet.state or sheet.heading != voice_facts.HEADINGS.get(sheet.state)
            or text[:first[1]].strip()):
        out.append(('NET_HEADING', 'the heading says %s; the first sentence does not open with that verdict' % sheet.heading))
    for problem in mind_words.scan_text(text):out.append(('NET_STYLE', problem))
    return out


def words_check(text, sheet):
    """0.8.6's WORDS check (answer_check.check_words, S7) against the sheet's desk values: (ran, refused, detail)."""
    try:
        from . import answer_check
        check = answer_check.check_words
    except (ImportError, AttributeError):
        return False, False, 'not run: answer_check is not in this program yet'
    verdict = check(text, voice_facts.desk_values(sheet), None, sheet.complete)
    refused = getattr(verdict, 'state', '') == 'REFUSED'
    return True, refused, '%s %s' % (getattr(verdict, 'state', ''), ', '.join(getattr(verdict, 'why', ()) or ()))


def gate(frame, sheet, never=None):
    """Gate: the frame checked, filled from the sheet and checked again. KEPT with its words, or REFUSED with its rules."""
    text, _ = _text_of(frame)
    found = check_frame(text, sheet, never)
    checks = [('frame', not found, '; '.join('%s %s' % f for f in found) or 'every character, slot and word allowed')]
    if found:return Gate('REFUSED', tuple(r for r, _ in found), tuple(checks), frame=text)
    filled, spans = fill(text, sheet)
    most = budgets(sheet.register)
    _, own = voice_lexicon.frame_for(sheet)
    allowed = max(most['sentences'], len(mind_words.sentences(SLOT.sub('x', own))))
    said = mind_words.sentences(filled);why = []
    long = [s for s in said if len(s.split()) > most['words']]
    if long:why.append(('LENGTH', '%d words: %s' % (len(long[0].split()), long[0][:50])))
    if len(said) > allowed:why.append(('SENTENCES', '%d sentences, %d allowed' % (len(said), allowed)))
    checks.append(('lengths', not why, '; '.join('%s %s' % w for w in why) or '%d sentences, at most %d words each' % (len(said), most['words'])))
    if why:return Gate('REFUSED', tuple(r for r, _ in why), tuple(checks), frame=text)
    net = second_net(filled, spans, sheet)
    _, refused, detail = words_check(filled, sheet)
    if refused:net.append(('NET_WORDS', detail))
    checks.append(('second net', not net, '; '.join('%s %s' % n for n in net) or 'every number, date and verdict in its slot'))
    checks.append(('words check', not refused, detail))
    if net:return Gate('REFUSED', tuple(r for r, _ in net), tuple(checks), frame=text, defect=True)
    return Gate('KEPT', (), tuple(checks), filled, spans, False, text)


def speak(sheet, frame=None, source=None):
    """What she says for a fact sheet: {'heading', 'text', 'mark', 'source', 'frame_key', 'gate', 'refused', 'shape',
    'model_calls'}. A given frame (str, or a model's ModelSaid) is used only if the gate keeps it; otherwise, and with no
    frame, her plain-word frame for the sheet. A model's words come back as model_words.Marked (shown only with their mark);
    hers as plain text with no mark. text is None, and defect True, only if even her own frame fails the second net."""
    refused = None
    if frame is not None:
        raw, given = _text_of(frame)
        source = given or source or 'OWNER'
        if source not in SOURCES:raise ValueError('VOICE_SOURCE: one of %s' % ', '.join(SOURCES))
        kept = gate(frame, sheet)
        if kept.state == 'KEPT':
            if source == 'MODEL':
                from .model_words import ModelSaid, marked
                text = marked(ModelSaid(kept.text, 'FRAME'), 'WORDED');mark = text.mark
            else:text, mark = kept.text, (OWNER_MARK if source == 'OWNER' else '')
            return {'heading': sheet.heading, 'text': text, 'mark': mark, 'source': source, 'frame_key': None, 'gate': kept.as_record(),
                    'refused': None, 'shape': sheet.shape, 'defect': False, 'model_calls': 0}
        refused = kept.as_record()
    key, own = voice_lexicon.frame_for(sheet)
    kept = gate(own, sheet)
    if kept.state != 'KEPT' and key != 'generic':
        key, own = 'generic', ' '.join('{%s}.' % n for n in sheet.names);kept = gate(own, sheet)
    ok = kept.state == 'KEPT'
    return {'heading': sheet.heading, 'text': kept.text if ok else None, 'mark': '', 'source': 'TEMPLATE', 'frame_key': key,
            'gate': kept.as_record(), 'refused': refused, 'shape': sheet.shape, 'defect': not ok, 'model_calls': 0}


def says(receipt, **kw):
    """Her words for a receipt in one call: the fact sheet (voice_facts.sheet) spoken in her plain words."""
    return speak(voice_facts.sheet(receipt, **kw))
