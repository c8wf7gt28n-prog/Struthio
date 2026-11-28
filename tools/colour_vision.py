"""The colour-vision check: no colour on the desk carries its meaning alone for eyes with weak red or weak green sight.

Every look's palette (workbench/boss_theme.PALETTES) gives each meaning a colour: what is chosen, what is ready, what
waits for the owner, what does not hold, what must be worked again, what is stopped or deleted, what is hers, the desk's
quiet structure, a line, a wire, plain words, what is held. Two of them can stand side by side anywhere on the desk (the
Field's sheets beside her column, a menu over both), so every pair is taken.

  simulate(colour, sight, severity)   the colour as weak red (protan) or weak green (deutan) sight takes it: the matrices
                                      of Machado, Oliveira and Fernandes, "A Physiologically-based Model for Simulation
                                      of Color Vision Deficiency", IEEE Transactions on Visualization and Computer
                                      Graphics 15(6), 2009, as published by the authors for severities 0.6 and 1.0
                                      (1.0 is the eye with that cone missing), applied to linear sRGB.
  difference(a, b)                    how far apart two colours are: CIEDE2000 (Sharma, Wu and Dalal, "The CIEDE2000
                                      Color-Difference Formula", Color Research and Application 30(1), 2005) between
                                      their CIELAB values under D65. Not CIE76: plain distance in Lab overstates
                                      differences between saturated colours, and these are saturated.
  THRESHOLD                           10, this check's own choice and not a published constant. A just-noticeable
                                      difference is about 1 in CIEDE2000 for two colours side by side (2.3 in CIE76:
                                      Mahy, Van Eycken and Oosterlinck, Color Research and Application 19(2), 1994);
                                      two small marks seen apart (a badge here, an edge there) need several times that
                                      to be named as two colours at a glance, and 10 is taken as that margin.
  SIGHTS                              full sight, and each of the two at 0.6 and at 1.0
  MEANINGS                            meaning -> (the palette's names for its colours, what it says): a meaning can
                                      wear more than one colour (what is chosen is an edge and, in a menu, a bar), and a
                                      pair of meanings is as close as its two closest colours
  HALO                                the pointer's halo where it is not the pointer's own green (workbench/pointer.drawn)
  SIGNS                               meaning -> (its word or its shape, where that is drawn): what tells it without colour
  REVIEWED[look]                      the pairs under THRESHOLD in some sight that a person has looked at: for each, the
                                      two signs tell the pair apart on screen. A pair under THRESHOLD that is not here
                                      fails the check (tests_integrated/test_colour_vision.py), so a palette that moves
                                      two meanings together is seen, and so is a meaning that has no sign.
  table(look)                         every pair: its difference in each sight, the least of them, and what tells it apart
  unreviewed(look)                    the pairs under THRESHOLD that are not in REVIEWED[look]

  python3 tools/colour_vision.py           the pairs under THRESHOLD in both looks, with what tells each apart; exit 1 when one is unreviewed
  python3 tools/colour_vision.py --all     every pair
"""
import math
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0, str(ROOT))

THRESHOLD = 10.0

# Machado, Oliveira and Fernandes (2009), the authors' published matrices. Each row sums to 1: white stays white.
MACHADO = {
    ('protan', 0.6): ((0.385450, 0.769005, -0.154455), (0.100526, 0.829802, 0.069673), (-0.007442, -0.022190, 1.029632)),
    ('protan', 1.0): ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    ('deutan', 0.6): ((0.498864, 0.674741, -0.173604), (0.205199, 0.754872, 0.039929), (-0.011131, 0.030969, 0.980162)),
    ('deutan', 1.0): ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
}
SIGHTS = (('full', None, 0.0), ('weak red 0.6', 'protan', 0.6), ('weak red 1.0', 'protan', 1.0), ('weak green 0.6', 'deutan', 0.6), ('weak green 1.0', 'deutan', 1.0))

# meaning -> (the palette's names for its colours, what it says). boss_theme's roles and mockup CANON.md's "each means one
# thing". 'halo' is the pointer's halo (HALO). 0.8.4's review: the menu's bar, the pointer's halo and the cue were missing.
MEANINGS = {
    'chosen': (('AMBER_EDGE', 'BAR'), 'selected, or holds the keyboard; the menu row under the pointer or the keyboard'),
    'ready': (('READY', 'halo'), 'ready, at work, live; the pointer and what it is over'),
    'cue': (('CUE_EDGE',), 'a cue that is not a selection: a status word, a heading\'s rule, a primary button (send, 0.8.6), a band\'s rule, a prompt'),
    'waits': (('OWNER',), 'waits for the owner'),
    'fails': (('STOP',), 'does not hold; an error'),
    'recheck': (('RECHECK',), 'must be worked again'),
    'stopped': (('RED',), 'DELETE, Forget, stopped'),      # the send arrow left red for the cue colour in 0.8.6
    'hers': (('HONEY',), 'hers: her cards, her proposals, done'),
    'quiet': (('VIOLET',), 'the desk\'s structure, her quiet, cannot tell'),
    'line': (('ROYAL',), 'a line that can be run'),
    'wire': (('TEAL_EDGE',), 'a wire: what feeds what'),
    'words': (('TEXT',), 'plain words: the colour says nothing'),
    'held': (('QUIET',), 'held, or not there to be read: quiet ink'),
}

# meaning -> (its word or its shape, where that is drawn). What says the meaning to an eye that cannot see the colour.
SIGNS = {
    'cue': ('its own words or rule: a heading with its rule, a button with its word, a prompt in a box with its caret; it marks no state on a row or a sheet',
            'boss_theme (CUE, CUE_EDGE, CUE_TEXT: what a status word, a heading\'s rule, a primary button, a band\'s rule or a prompt wears)'),
    'chosen': ('its own ground filled and a 2 px edge on the row, tab or word; corner ticks on the Field\'s selected sheet; in her menus a solid bar under the row',
               'boss_theme.CHROME_OVERRIDES and HIGHLIGHTS; field_qt._sheet (the ticks)'),
    'ready': ('the word "current" or "ready", and a filled square; her state word "at work"; under the pointer, the pointer itself',
              'field_qt.STATE_WORD and _mark (settled); hologram.STATE_LOOK; pointer.drawn'),
    'waits': ('the words "waits for you", and a square with a dot inside it',
              'hologram.STATE_LOOK (her column\'s top and her caption); field_qt._mark (waiting)'),
    'fails': ('the words "does not hold", and a cross (on a finding, a crossed square)',
              'field_qt._mark (failed, refuted); the finding\'s own words on its sheet'),
    'recheck': ('the word "recheck", a half-filled square, and in her look a dashed edge',
                'field_qt.STATE_WORD, _mark (recheck) and _sheet (the dashed edge)'),
    'stopped': ('the word DELETE beside the can, the word Forget, her state word "stopped"',
                'shell2 (DELETE); hologram.STATE_LOOK'),
    'hers': ('her name over it, and a bar down the left edge of her cards; her state word "done"',
             'shell2 (her cards\' left edge, the mark under her name); hologram.STATE_LOOK'),
    'quiet': ('a heading in capitals with a rule after it; her state word "quiet"; the words "cannot tell"',
              'field_qt._columns (the column\'s name and its rule); hologram.STATE_LOOK'),
    'line': ('the line\'s own words in the fixed-pitch face; in her look on a slab with a bar down its left edge',
             'boss_theme.line_sheet'),
    'wire': ('a curve drawn from one sheet to another, never a mark or a word',
             'field_qt._wires'),
    'words': ('words, with no mark: nothing is said by their colour',
              'every page'),
    'held': ('the word "held", and a square crossed corner to corner',
             'field_qt.STATE_WORD and _mark (held)'),
}

# The pairs under THRESHOLD in some sight, each looked at (0.8.4): pair -> what tells the two apart on screen, in words; where
# each sign is drawn is in SIGNS. Graphite gives one amber to everything that asks for attention and one green to what is
# live and to a line, so there the sign was always the only thing between them. Her look parts most of them by colour; what
# it leaves is below, and the first of them is the reason this check exists: to weak red sight her cyan is her plain ink.
ONE_AMBER = 'one amber for both in this look: '
CUE_IS = 'a cue is a heading\'s rule, a button\'s word or a prompt, and marks no row or sheet'
REVIEWED = {
    'graphite': {
        ('chosen', 'waits'): ONE_AMBER + 'an edge and a filled ground on what is chosen; the words "waits for you" and a dotted square on what waits',
        ('chosen', 'fails'): ONE_AMBER + 'an edge and a filled ground on what is chosen; "does not hold" and a cross on what fails',
        ('chosen', 'recheck'): ONE_AMBER + 'an edge and a filled ground on what is chosen; the word "recheck" and a half-filled square',
        ('chosen', 'stopped'): ONE_AMBER + 'an edge and a filled ground on what is chosen; the word DELETE, Forget or "stopped", or the arrow\'s shape',
        ('waits', 'fails'): ONE_AMBER + '"waits for you" and a dotted square; "does not hold" and a cross',
        ('waits', 'recheck'): ONE_AMBER + '"waits for you" and a dotted square; "recheck" and a half-filled square',
        ('waits', 'stopped'): ONE_AMBER + 'her state word says which ("waits for you", "stopped"); DELETE and Forget are words',
        ('fails', 'recheck'): ONE_AMBER + 'a cross and "does not hold"; a half-filled square and "recheck"',
        ('fails', 'stopped'): ONE_AMBER + 'a cross and "does not hold" on a finding; DELETE, Forget and "stopped" are words elsewhere',
        ('recheck', 'stopped'): ONE_AMBER + 'a half-filled square and "recheck"; DELETE, Forget and "stopped" are words',
        ('quiet', 'held'): 'one quiet ink for both in this look: a heading is in capitals with a rule after it; what is held says "held" and has a crossed square',
        ('ready', 'line'): 'two greens three steps apart: what is ready has its word and a filled square; a line is its own words in the fixed-pitch face',
        ('chosen', 'hers'): 'amber and her pencil: what is chosen has its ground filled and an edge; hers has her name over it and a bar on the card\'s left edge only',
        ('waits', 'hers'): 'amber and her pencil: "waits for you" and a dotted square; her name over her card',
        ('fails', 'hers'): 'amber and her pencil: "does not hold" and a cross; her name over her card',
        ('recheck', 'hers'): 'amber and her pencil: "recheck" and a half-filled square; her name over her card',
        ('stopped', 'hers'): 'amber and her pencil: her state word says "stopped" or "done"; DELETE and Forget are words',
        ('ready', 'hers'): 'to weak green sight: "current" and a filled square, or her state word "at work"; her name over her card, or "done"',
        ('hers', 'wire'): 'to weak red sight: a bar on a card in her column; a curve between sheets in the Field',
        ('hers', 'line'): 'to weak green sight: her name over her card; a line is its own words in the fixed-pitch face',
        ('chosen', 'ready'): 'to weak green sight: the keyboard\'s place has an edge and no pointer; what the pointer is over has the pointer on it, what is ready its word and a filled square',
        ('ready', 'waits'): 'to weak green sight: "current" and a filled square; "waits for you" and a dotted square',
        ('ready', 'fails'): 'to weak green sight: "current" and a filled square; "does not hold" and a cross',
        ('ready', 'recheck'): 'to weak green sight: a filled square and "current"; a half-filled square and "recheck"',
        ('ready', 'stopped'): 'to weak green sight: her state word says "at work" or "stopped"; DELETE and Forget are words',
        # 0.8.4's review: the cue was not in the table. Graphite's cue is its one amber too.
        ('chosen', 'cue'): ONE_AMBER + 'what is chosen has its ground filled and an edge on the row, tab or word; %s' % CUE_IS,
        ('cue', 'waits'): ONE_AMBER + '%s; what waits says "waits for you" and has a dotted square' % CUE_IS,
        ('cue', 'fails'): ONE_AMBER + '%s; what fails says "does not hold" and has a cross' % CUE_IS,
        ('cue', 'recheck'): ONE_AMBER + '%s; a recheck says "recheck" and has a half-filled square' % CUE_IS,
        ('cue', 'stopped'): ONE_AMBER + '%s; DELETE, Forget or "stopped" are words, the send arrow a shape' % CUE_IS,
        ('cue', 'hers'): 'amber and her pencil, close to weak green sight: %s; hers has her name over it and a bar on the card\'s left edge' % CUE_IS,
        ('ready', 'cue'): 'to weak green sight: what is ready has "current" and a filled square, the pointer its own shape; %s' % CUE_IS,
    },
    'kasandra': {
        ('waits', 'fails'): 'one pink for both: "waits for you" and a dotted square; "does not hold" and a cross',
        ('ready', 'words'): 'to weak red sight her cyan is her plain ink (1.0 apart): what is ready says "current" or "at work" and has a filled square; plain words have no mark',
        ('quiet', 'wire'): 'to weak red sight: a heading in capitals with a rule after it; a curve between sheets',
        ('ready', 'held'): 'the pointer\'s pale violet halo and her quiet ink, close in every sight: the halo lies round the pointer\'s own shape; what is ready has "current" and a filled square; "held" and a crossed square',
        ('recheck', 'held'): 'close in every sight: "recheck", a half-filled square and a dashed edge; "held" and a crossed square',
        ('ready', 'recheck'): 'the pointer\'s pale violet halo and lavender, close in every sight: the halo lies round the pointer\'s own shape; a filled square and "current"; a half-filled square, "recheck" and a dashed edge',
        ('waits', 'stopped'): 'pink and red, close in every sight: her state word says "waits for you" or "stopped"; DELETE and Forget are words',
        ('fails', 'stopped'): 'pink and red, close in every sight: "does not hold" and a cross on a finding; DELETE, Forget and "stopped" are words',
        ('words', 'held'): 'her ink and her quiet ink: what is held says "held" and has a crossed square',
        ('chosen', 'hers'): 'her yellow and her honey: what is chosen has its ground filled (a solid bar in a menu) and corner ticks on a sheet; hers has her name over it and a bar on the card\'s left edge only',
        ('recheck', 'quiet'): 'lavender and violet: what must be worked again says "recheck", with a half-filled square and a dashed edge; violet is a heading in capitals, her state word "quiet", or the words "cannot tell"',
        # 0.8.4's review: the cue was not in the table. Her cue is her old cyan, the colour of what is ready.
        ('ready', 'cue'): 'one cyan for both: what is ready says "current" or "at work" and has a filled square, the pointer its own shape; %s' % CUE_IS,
        ('cue', 'words'): 'to weak red sight her cyan is her plain ink: %s; plain words have no rule, no button and no mark' % CUE_IS,
        ('cue', 'held'): 'to weak green sight: %s; what is held says "held" and has a crossed square' % CUE_IS,
        ('cue', 'recheck'): 'to weak green sight: %s; a recheck says "recheck" and has a half-filled square and a dashed edge' % CUE_IS,
    },
}

# 1.1 T1: Day and Night (1.0 P2, P4) were never put through this check. Their tokens give one green to what is ready, a cue,
# a line and a wire, one red to what fails and what is stopped, and one grey to the desk's quiet and what is held; their
# amber (waits) and her honey (hers) are close in every sight. Each close pair is told apart by the same words and shapes as
# in the other looks (SIGNS, drawn whatever the look): said here per meaning, and the pairs looked at listed per look.
SAID = {
    'chosen': 'what is chosen has its ground filled and an edge',
    'ready': 'what is ready says "current" or "at work" and has a filled square',
    'cue': CUE_IS,
    'waits': 'what waits says "waits for you" and has a dotted square',
    'fails': 'what fails says "does not hold" and has a cross',
    'recheck': 'a recheck says "recheck" and has a half-filled square',
    'stopped': 'DELETE, Forget and "stopped" are words',
    'hers': 'hers has her name over it and a bar on the card\'s left edge',
    'quiet': 'the quiet is a heading in capitals with a rule after it, or the words "cannot tell"',
    'line': 'a line is its own words in the fixed-pitch face',
    'wire': 'a wire is a curve between sheets, never a mark or a word',
    'held': 'what is held says "held" and has a crossed square',
}
ONE_OF = {('ready', 'cue', 'line', 'wire'): 'one green for both in this look: ', ('fails', 'stopped'): 'one red for both in this look: ',
          ('quiet', 'held'): 'one grey for both in this look: '}


def _told(pair):
    one = next((words for group, words in ONE_OF.items() if set(pair) <= set(group)), '')
    return one + '; '.join(SAID[meaning] for meaning in pair)


_GREEN = (('ready', 'cue'), ('ready', 'line'), ('ready', 'wire'), ('cue', 'line'), ('cue', 'wire'), ('line', 'wire'))
_RED_GREEN = tuple((a, b) for a in ('ready', 'cue') for b in ('fails', 'stopped')) + tuple((a, b) for a in ('fails', 'stopped') for b in ('line', 'wire'))
_AMBER_GREEN = (('ready', 'waits'), ('cue', 'waits'), ('waits', 'line'), ('waits', 'wire'))
_HONEY_GREEN = (('ready', 'hers'), ('cue', 'hers'), ('hers', 'line'), ('hers', 'wire'))
_SHARED = _GREEN + _RED_GREEN + _AMBER_GREEN + _HONEY_GREEN + (('fails', 'stopped'), ('quiet', 'held'), ('waits', 'hers'), ('chosen', 'recheck'),
                                                               ('waits', 'fails'), ('waits', 'stopped'))
REVIEWED['day'] = {pair: _told(pair) for pair in _SHARED + (('fails', 'hers'), ('stopped', 'hers'))}
REVIEWED['night'] = {pair: _told(pair) for pair in _SHARED}


def rgb(colour):
    """'#rrggbb' -> (r, g, b), each 0 to 1."""
    return tuple(int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _linear(v):
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _encoded(v):
    v = min(1.0, max(0.0, v));return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def simulate(colour, sight=None, severity=1.0):
    """`colour` ('#rrggbb') as this sight takes it, as '#rrggbb'. sight None, or severity 0: as it is."""
    if sight is None or not severity:return colour.lower()
    matrix = MACHADO[(sight, severity)];linear = [_linear(v) for v in rgb(colour)]
    seen = [_encoded(sum(m * v for m, v in zip(row, linear))) for row in matrix]
    return '#%02x%02x%02x' % tuple(round(255 * v) for v in seen)


def lab(colour):
    """CIELAB (L*, a*, b*) of an sRGB colour under D65."""
    r, g, b = (_linear(v) for v in rgb(colour))
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def ciede2000(one, two):
    """CIEDE2000 between two CIELAB colours (kL = kC = kH = 1), as Sharma, Wu and Dalal give it."""
    l1, a1, b1 = one;l2, a2, b2 = two
    c_mean = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(c_mean ** 7 / (c_mean ** 7 + 25.0 ** 7)))
    a1, a2 = (1 + g) * a1, (1 + g) * a2
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    h1 = math.degrees(math.atan2(b1, a1)) % 360 if c1 else 0.0
    h2 = math.degrees(math.atan2(b2, a2)) % 360 if c2 else 0.0
    dl, dc = l2 - l1, c2 - c1
    if c1 * c2 == 0:dh = 0.0
    elif abs(h2 - h1) <= 180:dh = h2 - h1
    elif h2 - h1 > 180:dh = h2 - h1 - 360
    else:dh = h2 - h1 + 360
    dH = 2 * math.sqrt(c1 * c2) * math.sin(math.radians(dh / 2))
    l_mean, c_mean = (l1 + l2) / 2, (c1 + c2) / 2
    if c1 * c2 == 0:h_mean = h1 + h2
    elif abs(h1 - h2) <= 180:h_mean = (h1 + h2) / 2
    elif h1 + h2 < 360:h_mean = (h1 + h2 + 360) / 2
    else:h_mean = (h1 + h2 - 360) / 2
    t = (1 - 0.17 * math.cos(math.radians(h_mean - 30)) + 0.24 * math.cos(math.radians(2 * h_mean))
         + 0.32 * math.cos(math.radians(3 * h_mean + 6)) - 0.20 * math.cos(math.radians(4 * h_mean - 63)))
    spin = 30 * math.exp(-((h_mean - 275) / 25) ** 2)
    rc = 2 * math.sqrt(c_mean ** 7 / (c_mean ** 7 + 25.0 ** 7))
    sl = 1 + 0.015 * (l_mean - 50) ** 2 / math.sqrt(20 + (l_mean - 50) ** 2)
    sc, sh = 1 + 0.045 * c_mean, 1 + 0.015 * c_mean * t
    rt = -math.sin(math.radians(2 * spin)) * rc
    return math.sqrt((dl / sl) ** 2 + (dc / sc) ** 2 + (dH / sh) ** 2 + rt * (dc / sc) * (dH / sh))


def difference(a, b):
    """CIEDE2000 between two '#rrggbb' colours."""
    return ciede2000(lab(a), lab(b))


def palette(look):
    from workbench import boss_theme
    return boss_theme.PALETTES[look]


# The pointer's halo, as pointer.drawn draws it: pale violet in her look, where her cyan over her yellow bar read green
# (0.8.3); elsewhere the halo is the pointer's own green, READY.
HALO = {'kasandra': 'VIOLET_PALE'}


def colours_of(meaning, look, colours):
    """The colours `meaning` wears in `look`, read from `colours` (the look's palette, or a stand-in for it)."""
    return [colours[HALO.get(look, 'READY') if name == 'halo' else name] for name in MEANINGS[meaning][0]]


def table(look, colours=None):
    """Every pair of meanings in `look`: [{pair, colours, seen: {sight: difference}, least, sight, reviewed, told_apart}]
    with `least` the smallest difference over SIGHTS and `sight` where it is. `colours` stands in for the look's palette
    (a check of the check: a palette that moves two meanings together)."""
    colours = palette(look) if colours is None else colours;rows = []
    reviewed = {frozenset(pair): by for pair, by in REVIEWED.get(look, {}).items()}
    for one, two in combinations(MEANINGS, 2):
        seen = {};worn = {}      # in each sight, the two meanings' closest colours
        for name, sight, severity in SIGHTS:
            seen[name], worn[name] = min((difference(simulate(a, sight, severity), simulate(b, sight, severity)), (a, b))
                                         for a in colours_of(one, look, colours) for b in colours_of(two, look, colours))
        least = min(seen, key=seen.get);by = reviewed.get(frozenset((one, two)));a, b = worn[least]
        signed = one in SIGNS and two in SIGNS and SIGNS[one][0] != SIGNS[two][0]      # each has a sign of its own, and where it is drawn
        rows.append(dict(pair=(one, two), colours=(a, b), seen=seen, least=seen[least], sight=least, reviewed=by is not None,
                         told_apart=dict(by=by, signs=(SIGNS[one], SIGNS[two])) if by and signed else None))
    return rows


def unreviewed(look, colours=None):
    """The pairs under THRESHOLD in some sight that nothing reviewed tells apart."""
    return [row for row in table(look, colours) if row['least'] < THRESHOLD and row['told_apart'] is None]


def printed(look, everything=False):
    lines = ['%s: %d meanings, %d pairs, THRESHOLD %.0f (CIEDE2000)' % (look, len(MEANINGS), len(MEANINGS) * (len(MEANINGS) - 1) // 2, THRESHOLD),
             '  %-18s %-17s %s   least' % ('pair', 'colours', '  '.join('%-7s' % name.replace('weak ', '') for name, _, _ in SIGHTS))]
    for row in sorted(table(look), key=lambda r: r['least']):
        if row['least'] >= THRESHOLD and not everything:continue
        lines.append('  %-18s %s %s  %s   %5.1f in %s%s' % (' / '.join(row['pair']), row['colours'][0], row['colours'][1], '  '.join('%7.1f' % row['seen'][name] for name, _, _ in SIGHTS),
                                                           row['least'], row['sight'], '' if row['least'] >= THRESHOLD else '   REVIEWED' if row['told_apart'] else '   NOT REVIEWED'))
        if row['told_apart'] and row['least'] < THRESHOLD:
            lines.append('      told apart by: ' + row['told_apart']['by'])
            if everything:
                for meaning, (sign, where) in zip(row['pair'], row['told_apart']['signs']):lines.append('      %-8s %s  [%s]' % (meaning + ':', sign, where))
    return lines


if __name__ == '__main__':
    from workbench import boss_theme
    left = 0
    for look in boss_theme.PALETTES:
        print('\n'.join(printed(look, '--all' in sys.argv[1:])));left += len(unreviewed(look))
    print('COLOUR VISION: %d pair%s under %.0f not reviewed' % (left, '' if left == 1 else 's', THRESHOLD))
    sys.exit(1 if left else 0)
