"""Her voice lexicon (0.8.7 C4, "Kas's mind with the model, interwoven", lane C): the words a frame may not hold, and her
plain-word frames.

A frame is a sentence pattern of slot names and joining words: `{ANSWER}. {MARGIN}; {READING}.` Every slot is a whole clause
the desk wrote from the receipt (voice_facts), carrying its own numbers, units, dates and verdict. The joining words around
the slots are the only words a frame adds, and they may carry none of these (design 3.4, "FRAME: the gate"):

  VERDICT    holds, fails, passes, yes, inside, within, fine, ... (the verdict is the {ANSWER} slot's alone)
  NEGATION   not, no, never, nothing, cannot, ...n't (a negation turns a verdict over)
  HEDGE      probably, maybe, seems, should, might, likely, about, ... (she does not soften a receipt)
  BOOSTER    clearly, definitely, certainly, always, exactly, ... (nor harden one)
  NUMBER     number words, spelled out or not: one, twelve, forty-two, half, dozen, both, every, most, first, ...
             (the voice lens saw a 4B spell "forty-two" under a grammar that allowed no digit)
  CALENDAR   months, weekdays, today, tomorrow, week, ... (a date comes from the receipt or not at all)
  UNIT       unit words and unit symbols: volts, amps, watts, seconds, days, percent, V, mA, ms, ...
  ADVICE     should, must, recommend, suggest, better, safe, ... (the legal and medical line, design 5.7)
  LOGIC      because, so, therefore, since, unless, if, only, except, ... (a frame joins clauses; it does not argue
             from one to another: a causal word between two desk clauses claims a link nobody checked)
  APOLOGY    sorry, apologise, unfortunately, afraid, regret
plus the never-say floor (NEVER_SAY_FLOOR) and the never-say list of her character file (voice_character, 0.8.7 C5, when
it is in this program), and 0.8.6's banned words (mind_words.BANNED).

classify(words) gives every hit as (class, word or phrase). number_words(text) finds number words in any text (the second
net uses it after the fill). Signs (digits, currency, unit and percent signs, "!") are the gate's, by character.

Her plain-word frames (FRAMES) are 0.8.6 templates like any other: registered with mind_words as kind 'frame' and swept by
mind_words.check(). frame_for(sheet) picks hers for a fact sheet's shape; every extra caveat slot (a missing tolerance, a
tolerance to recheck, what is not seen) is its own short sentence after it. Pure Python: no Qt, no Kernel, no model.
"""
from __future__ import annotations

import re

from . import mind_words

# -- the word classes a frame's joining words may not hold ----------------------------------------------------------------
CLASSES = {
    'VERDICT': ('hold', 'holds', 'holding', 'held', 'fail', 'fails', 'failing', 'failed', 'pass', 'passes', 'passed', 'passing',
                'yes', 'yeah', 'true', 'false', 'inside', 'outside', 'within', 'exceed', 'exceeds', 'exceeded', 'meet', 'meets',
                'met', 'ok', 'okay', 'fine', 'good', 'bad', 'correct', 'incorrect', 'wrong', 'right', 'valid', 'invalid',
                'compliant', 'breaks', 'broken', 'violates', 'violated', 'settled', 'proven', 'proves', 'confirmed', 'confirms',
                'agrees', 'disagrees', 'allowed', 'forbidden', 'over', 'beyond', 'short'),
    'NEGATION': ('not', 'no', 'never', 'nothing', 'none', 'nobody', 'nowhere', 'neither', 'nor', 'cannot', 'without',
                 "can't", "won't", "isn't", "doesn't", "don't", "didn't", "wasn't", "aren't", "weren't", "hasn't",
                 "haven't", "shouldn't", "wouldn't", "couldn't", "mustn't", "ain't", 'cant', 'wont', 'isnt', 'doesnt', 'dont'),
    'HEDGE': ('probably', 'probable', 'possibly', 'possible', 'perhaps', 'maybe', 'likely', 'unlikely', 'seems', 'seem',
              'seemingly', 'appears', 'appear', 'apparently', 'presumably', 'roughly', 'about', 'around', 'approximately',
              'approx', 'nearly', 'almost', 'circa', 'should', 'might', 'could', 'may', 'would', 'guess', 'think', 'believe',
              'suppose', 'assume', 'expect', 'hopefully', 'somewhat', 'fairly', 'quite', 'rather', 'arguably', 'chance',
              'odds', 'probability', 'risk', 'suspect', 'estimate', 'estimated', 'ish'),
    'BOOSTER': ('definitely', 'certainly', 'clearly', 'obviously', 'absolutely', 'surely', 'sure', 'guaranteed',
                'guarantee', 'always', 'completely', 'totally', 'entirely', 'fully', 'very', 'really', 'indeed', 'undoubtedly',
                'exactly', 'precisely', 'truly', 'perfectly', 'extremely', 'highly', 'utterly', 'plainly', 'easily',
                'comfortably', 'well'),
    'NUMBER': ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve',
               'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty', 'thirty', 'forty',
               'fourty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety', 'hundred', 'hundreds', 'thousand', 'thousands',
               'million', 'millions', 'billion', 'dozen', 'dozens', 'score', 'half', 'halves', 'quarter', 'quarters', 'third',
               'thirds', 'double', 'twice', 'triple', 'thrice', 'once', 'single', 'pair', 'couple', 'few', 'several', 'many',
               'most', 'all', 'every', 'each', 'both', 'some', 'more', 'less', 'fewer', 'least', 'much', 'whole', 'first',
               'second', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'last', 'percent', 'nil', 'none'),
    'CALENDAR': ('january', 'february', 'march', 'april', 'june', 'july', 'august', 'september', 'october', 'november',
                 'december', 'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec', 'monday',
                 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'today', 'tomorrow', 'yesterday',
                 'tonight', 'weekend', 'weekday', 'week', 'weeks', 'month', 'months', 'year', 'years', 'day', 'days',
                 'daily', 'weekly', 'monthly', 'yearly', 'annual', 'annually', 'deadline', 'christmas', 'easter'),
    'UNIT': ('volt', 'volts', 'voltage', 'millivolt', 'millivolts', 'amp', 'amps', 'ampere', 'amperes', 'milliamp',
             'milliamps', 'current', 'watt', 'watts', 'milliwatt', 'kilowatt', 'kilowatts', 'power', 'ohm', 'ohms',
             'second', 'seconds', 'millisecond', 'milliseconds', 'minute', 'minutes', 'hour', 'hours', 'hertz', 'kilohertz',
             'metre', 'metres', 'meter', 'meters', 'gram', 'grams', 'kilogram', 'kilograms', 'litre', 'litres', 'degree',
             'degrees', 'celsius', 'kelvin', 'joule', 'joules', 'pound', 'pounds', 'euro', 'euros', 'dollar', 'dollars',
             'cent', 'cents', 'pence', 'penny', 'percentage', 'per', 'mph', 'kph'),
    'ADVICE': ('should', 'must', 'ought', 'recommend', 'recommends', 'recommended', 'advise', 'advice', 'advised', 'suggest',
               'suggests', 'suggested', 'better', 'best', 'worse', 'worst', 'safe', 'safely', 'unsafe', 'danger',
               'dangerous', 'warning', 'beware', 'careful', 'entitled', 'liable', 'guilty', 'please', 'consider', 'urge'),
    'LOGIC': ('because', 'so', 'therefore', 'thus', 'hence', 'since', 'consequently', 'accordingly', 'implies', 'imply',
              'implied', 'unless', 'if', 'only', 'except', 'otherwise', 'whereas', 'despite', 'although', 'though',
              'however', 'nevertheless', 'nonetheless', 'means', 'meaning', 'proving', 'follows', 'whether', 'either', 'or',
              'while', 'when', 'whenever', 'until', 'provided', 'assuming', 'given'),
    'APOLOGY': ('sorry', 'apologise', 'apologize', 'apologies', 'apology', 'unfortunately', 'afraid', 'regret', 'regrettably',
                'alas', 'sadly', 'oops', 'excuse', 'pardon'),
}
CLASS_ORDER = ('APOLOGY', 'HEDGE', 'ADVICE', 'VERDICT', 'NEGATION', 'BOOSTER', 'NUMBER', 'CALENDAR', 'UNIT', 'LOGIC')
# Phrases caught whole (and named in the reason), each under its class. "it should be fine" is the design's own example.
PHRASES = (('it should be fine', 'HEDGE'), ('should be fine', 'HEDGE'), ('should be ok', 'HEDGE'), ('no problem', 'HEDGE'),
           ('i think', 'HEDGE'), ('i believe', 'HEDGE'), ('as far as i know', 'HEDGE'), ('more or less', 'HEDGE'),
           ('of course', 'BOOSTER'), ('for sure', 'BOOSTER'), ('without doubt', 'BOOSTER'), ('per cent', 'NUMBER'),
           ('a lot', 'NUMBER'), ('you need to', 'ADVICE'), ('you have to', 'ADVICE'), ('make sure', 'ADVICE'),
           ('which means', 'LOGIC'), ('it follows', 'LOGIC'), ('i am sorry', 'APOLOGY'), ("i'm sorry", 'APOLOGY'))
# Unit symbols, matched as whole tokens with their case (a capital A is also the article, so it is left to the sign check
# of the slot facts and is not listed; "s" alone is not a word she joins with either way).
UNIT_SYMBOLS = frozenset(('V', 'mV', 'kV', 'mA', 'uA', 'W', 'mW', 'kW', 'MW', 'Wh', 'kWh', 'ms', 'us', 'ns', 'Hz', 'kHz',
                          'MHz', 'GHz', 'Ah', 'mAh', 'dB', 'K', 'C', 'F', 'J', 'kJ', 'N', 'Pa', 'kPa', 'bar', 'kg', 'g', 'mg',
                          'km', 'cm', 'mm', 'm', 'l', 'ml', 'h', 'min', 'pc', 'pct', 'EUR', 'USD', 'GBP'))
# What she never writes, whatever her character file says (the file adds to this and never lifts it).
NEVER_SAY_FLOOR = ('as an ai', 'as a language model', 'language model', 'i apologise', 'i apologize', 'trust me', 'no worries',
                   'rest assured', 'do not worry', "don't worry")

_WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
_LOOKUP = {}
for _cls in CLASS_ORDER:
    for _w in CLASSES[_cls]:_LOOKUP.setdefault(_w, _cls)
# Spelled-out numbers anywhere in a text (the second net): a number word, hyphenated or not ("forty-two", "twenty one").
_NUMBERISH = tuple(w for w in CLASSES['NUMBER'] if w not in ('most', 'all', 'every', 'each', 'some', 'more', 'less', 'fewer',
                                                               'least', 'much', 'whole', 'few', 'several', 'many', 'last',
                                                               'second', 'single', 'pair', 'couple', 'score', 'none', 'both',
                                                               'once', 'first'))
_ALT = '|'.join(sorted(_NUMBERISH, key=len, reverse=True))
NUMBER_WORD = re.compile(r"(?<![A-Za-z])(?:%s)(?:[-\s](?:%s))*(?![A-Za-z])" % (_ALT, _ALT), re.IGNORECASE)


def words_of(text):
    """The words of a text, lower case, apostrophes made plain: [(word, (start, end))]."""
    return [(m.group(0).lower().replace('’', "'"), m.span()) for m in _WORD.finditer(str(text or ''))]


def classify(text, never=()):
    """Every word or phrase of `text` a frame may not hold: [(class, word)], classes as CLASSES names, 'UNIT' for a unit
    symbol, 'NEVER_SAY' for the floor and for `never` (her character's never-say phrases), in the order found."""
    raw = str(text or '')
    plain = ' %s ' % ' '.join(w for w, _ in words_of(raw))
    hits = []
    for phrase, cls in PHRASES:
        if (' %s ' % phrase) in plain:hits.append((cls, phrase))
    for phrase in tuple(NEVER_SAY_FLOOR) + tuple(never or ()):
        p = ' '.join(w for w, _ in words_of(phrase))
        if p and (' %s ' % p) in plain:hits.append(('NEVER_SAY', phrase))
        elif not p and phrase and phrase in raw:hits.append(('NEVER_SAY', phrase))     # a mark with no letter, such as "!"
    for word, _ in words_of(raw):
        if word in _LOOKUP:hits.append((_LOOKUP[word], word));continue
        if word.endswith("n't"):hits.append(('NEGATION', word));continue
        for part in word.split("'"):
            if part in _LOOKUP:hits.append((_LOOKUP[part], word));break
    for token in re.findall(r"[A-Za-zµΩ]+", raw):
        if token in UNIT_SYMBOLS:hits.append(('UNIT', token))
    return hits


def number_words(text):
    """The spelled-out numbers in `text`: [(said, (start, end))]."""
    return [(m.group(0), m.span()) for m in NUMBER_WORD.finditer(str(text or ''))]


# -- her plain-word frames: one per fact-sheet shape (kind and core slots), registered with mind_words ---------------------
# Each is her own manner (0.8.6 section 3.6): the answer first, then what the desk measured, then the next step. A caveat
# slot the sheet adds (TOLERANCE, RECHECK, UNSEEN) follows as its own sentence.
FRAMES = {
    'check.full': '{ANSWER}. {MARGIN}; {READING}.',
    'check.short': '{ANSWER}. {MARGIN}.',
    'undecided.full': '{ANSWER}. {WHY}: {WITNESS}. {DECIDER}, and {KEEPS}.',
    'undecided.decider': '{ANSWER}. {WHY}: {WITNESS}. {DECIDER}.',
    'undecided.keeps': '{ANSWER}. {WHY}: {WITNESS}. {KEEPS}.',
    'undecided.witness': '{ANSWER}. {WHY}: {WITNESS}.',
    'undecided.short': '{ANSWER}. {WHY}.',
    'changed.full': '{ANSWER}. {CHANGED}. {WAS}.',
    'period.next': '{ANSWER}. {LAST_DAYS}. {CREDIT}. {NEXT}.',
    'period.short': '{ANSWER}. {LAST_DAYS}. {CREDIT}.',
    'search.next': '{ANSWER}. {LOOKED}. {NEXT}.',
    'search.short': '{ANSWER}. {LOOKED}.',
}
SHAPES = {('check', ('ANSWER', 'MARGIN', 'READING')): 'check.full', ('check', ('ANSWER', 'MARGIN')): 'check.short',
          ('undecided', ('ANSWER', 'WHY', 'WITNESS', 'DECIDER', 'KEEPS')): 'undecided.full',
          ('undecided', ('ANSWER', 'WHY', 'WITNESS', 'DECIDER')): 'undecided.decider',
          ('undecided', ('ANSWER', 'WHY', 'WITNESS', 'KEEPS')): 'undecided.keeps',
          ('undecided', ('ANSWER', 'WHY', 'WITNESS')): 'undecided.witness', ('undecided', ('ANSWER', 'WHY')): 'undecided.short',
          ('changed', ('ANSWER', 'CHANGED', 'WAS')): 'changed.full',
          ('period', ('ANSWER', 'LAST_DAYS', 'CREDIT', 'NEXT')): 'period.next', ('period', ('ANSWER', 'LAST_DAYS', 'CREDIT')): 'period.short',
          ('search', ('ANSWER', 'LOOKED', 'NEXT')): 'search.next', ('search', ('ANSWER', 'LOOKED')): 'search.short'}
EXTRAS = ('TOLERANCE', 'RECHECK', 'UNSEEN')          # caveat slots: each its own sentence after the frame


def frame_for(sheet):
    """(key, frame): her plain-word frame for this fact sheet, from the registered templates (mind_words), with a sentence
    for each caveat slot. A shape she has no frame for gets one sentence per slot, the answer first."""
    names = tuple(s.name for s in sheet.slots)
    core = tuple(n for n in names if n not in EXTRAS);extra = [n for n in names if n in EXTRAS]
    key = SHAPES.get((sheet.kind, core))
    frame = mind_words.frames('voice_lexicon').get(('voice_lexicon', key)) if key else None
    if frame is None:key, frame = 'generic', ' '.join('{%s}.' % n for n in core)
    return key, frame + ''.join(' {%s}.' % n for n in extra)


# -- the gate's reasons, in plain words (registered, so the sweep reads them too) --------------------------------------------
REASONS = {
    'FRAME_EMPTY': 'The frame is empty.',
    'FRAME_CHARACTERS': 'The frame holds a line break, a control, zero-width or direction character, or a letter outside plain Latin.',
    'FRAME_BRACES': 'The frame holds a brace that is not a slot name.',
    'FRAME_GLUE': 'A slot is joined to a word with no space or sign between them.',
    'FRAME_QUOTE': 'The frame holds a quotation mark: quoted words are the source, and a frame has none.',
    'FRAME_UNKNOWN_SLOT': 'The frame names a slot this fact sheet does not have.',
    'FRAME_SLOT_TWICE': 'The frame uses a slot twice.',
    'FRAME_MISSING_SLOT': 'The frame leaves out a slot that must be said.',
    'FRAME_ANSWER_FIRST': 'The frame does not start with the answer.',
    'FRAME_DIGIT': 'The frame writes a digit: a number comes from the receipt or not at all.',
    'FRAME_SIGN': 'The frame writes a currency, unit or percent sign, or a sign that is not punctuation.',
    'FRAME_EXCLAMATION': 'The frame writes an exclamation mark.',
    'WORD_VERDICT': 'The frame writes a verdict word: the verdict is the answer slot alone.',
    'WORD_NEGATION': 'The frame writes a negation, which would turn a verdict over.',
    'WORD_HEDGE': 'The frame softens the receipt with a hedge.',
    'WORD_BOOSTER': 'The frame hardens the receipt with a booster.',
    'WORD_NUMBER': 'The frame writes a number word: a number comes from the receipt or not at all.',
    'WORD_CALENDAR': 'The frame writes a month, weekday or span of days. A date comes from the receipt or not at all.',
    'WORD_UNIT': 'The frame writes a unit: units come from the receipt.',
    'WORD_ADVICE': 'The frame tells you what to do, which is not hers to tell.',
    'WORD_LOGIC': 'The frame argues from one clause to another, a link nobody checked.',
    'WORD_APOLOGY': 'The frame apologises: she says plainly what she cannot tell.',
    'NEVER_SAY': 'The frame holds a phrase her character never says.',
    'BANNED': 'The frame holds one of her banned words.',
    'LENGTH': 'A sentence is longer than her character allows.',
    'SENTENCES': 'The answer has more sentences than her character allows.',
    'NET_NUMBER_OUTSIDE': 'After the fill, a number, a date or an amount lies outside the slots.',
    'NET_NUMBER_UNDECLARED': 'After the fill, a number in a slot is not one the receipt gives it.',
    'NET_SLOT_TEXT': 'After the fill, a slot does not read as the desk wrote it.',
    'NET_HEADING': 'After the fill, the first sentence does not give the heading\'s verdict.',
    'NET_STYLE': 'After the fill, the words break her style rules.',
    'NET_WORDS': 'After the fill, the WORDS check refuses the words against the desk.',
}

mind_words.register('voice_lexicon', FRAMES, kind='frame')
mind_words.register('voice_lexicon', {'reason.' + k: v for k, v in REASONS.items()}, kind='doubt')
