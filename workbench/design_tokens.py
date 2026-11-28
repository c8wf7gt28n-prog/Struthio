"""Graphite 1.0 P4 · the launch look's design tokens: Day, and Night made from the same tokens.

The owner, 26 Nov 2026: "Day or other modes, I want you to create a default version that is apple/microsoft level refined
for the 1.0 launch." DESIGN_DIRECTION_1.0.md section 9 is the source; this module is its one source of truth. Every colour,
size, radius, shadow, duration and font role of Day and Night is here, and nowhere else: boss_theme builds the two looks'
palettes from it (palette), the board, the column and the dock read their marks from it (marks), and the window's style
sheet for the two looks is written from it (sheet). No colour of Day or Night is written outside this file.

Colours are given as text (#rrggbb) or, where a colour lies over what is under it, as (r, g, b, alpha) with alpha a whole
number from 0 to 255. Tints laid on a known ground are worked out here once, in whole numbers (over), so a style sheet gets
an opaque colour and never mixes paint. Every text pair a look lays down (TEXT_PAIRS) is measured at 4.5:1 or more; the
measuring is the builder's check, not the program's: nothing here decides anything at run time from a ratio.

Section 9 gave the hues; three were darkened or added so every text pair measures 4.5:1 or more:
  Day live #1E8A4C measured 4.4:1 on white; it is #18773F here (5.5:1 on white, 5.0:1 on the window). Day waiting
      #A35A00 measured 4.4:1 on a raised plate; it is #9A5400 here. Tertiary words (#626268 Day, #A0A0A7 Night) are a
      step under secondary and still 4.5:1 on every ground they are laid on.
  Day accent text: accent words on a selected row (accent 12 % over the sidebar) measured 4.3:1; words on a tint use
      accent_text #0857B8 (5.5:1 or more on every tint).
  Night accent fill: white on #4C93FF is 3.0:1; a primary button's fill is accent_fill #2563C9 (5.7:1 with white), the
      accent itself stays #4C93FF for wires, rings, links and focus.
"""
from __future__ import annotations

LOOKS = ('day', 'night')

# ------------------------------------------------------------------------------------------------------------ colour
COLOUR = {
    'day': dict(
        window='#f5f5f7', surface='#ffffff', sidebar='#f7f7f9', raised='#ececf0', pressed='#e2e2e7', terminal='#ffffff',
        hairline=(0, 0, 0, 20), stroke=(0, 0, 0, 36), stroke_strong=(0, 0, 0, 92),
        text='#1d1d1f', secondary='#5a5a60', tertiary='#626268', disabled='#9a9aa0',
        accent='#0a66d8', accent_text='#0857b8', accent_fill='#0a66d8', on_accent='#ffffff',
        live='#18773f', live_text='#146a37', on_live='#ffffff',
        waiting='#9a5400', waiting_text='#8f4f00', on_waiting='#ffffff',
        danger='#c62828', danger_text='#b02020', on_danger='#ffffff',
        recheck='#6a4bb5', violet_text='#5a3fa0',
        shadow=(0, 0, 0, 255), scrim=(0, 0, 0, 96),
    ),
}

# ------------------------------------------------------------------- 1.1 N1: Night is a phosphor monitor (Amber, Green)
# The owner, 28 Nov 2026: night mode is "to look like old computers that only had orange and black / green and black
# monitors....but updated to 2026 but still old school modern". Night is one phosphor on a warm near-black ground; hierarchy
# is the brightness of that one phosphor, never another hue. The steps are shares (out of 255) of the phosphor laid over
# the ground. The plan's "about 70 % and 45 %" measured 2.9:1 for 45 % amber on the ground, under 4.5:1, so the steps are
# the lowest shares that keep 4.5:1 on every ground a word is laid on (the builder's measure, NIGHT_PAIRS):
#   Amber #ffb000: words 255 (10.8:1 on the ground), secondary 220 (8.1:1), tertiary 200 (6.9:1); 5.2:1 or more on the
#                  heaviest tint.   Green #33ff66: 255 (14.8:1), 205 (9.6:1), 180 (7.5:1); 5.3:1 or more on the heaviest tint.
#   (A step a little above the lowest that passes, so the CRT effects' scanline and vignette, crt_qt, never take a word under.)
# What is selected, the pressed button, the active window on the bar, HALT and anything destructive are inverse video: a
# block of the phosphor with words in the ground. State colours become the phosphor; every state keeps its word and shape.
PHOSPHORS = ('duo', 'amber', 'green')      # 1.1 N1duo: Duo first, the default
MONO_PHOSPHORS = ('amber', 'green')        # 1.1 N1duo: the two one-hue monitors N1 built, kept as choices
PHOSPHOR_DEFAULT = 'duo'      # 1.1 N1duo (N1: amber)
PHOSPHOR = [PHOSPHOR_DEFAULT]      # the phosphor in force: boss_theme sets it once, at its import, as it chooses the look
IN_FORCE = ['day']                 # the look in force (boss_theme sets it too): face() reads it
PHOSPHOR_WORDS = {'duo': 'Duo', 'amber': 'Amber', 'green': 'Green'}      # 1.1 N1duo: Duo
NIGHT_GROUND = '#0a0a08'
# phosphor: (full, secondary share, tertiary share, disabled share)
PHOSPHOR_INK = {'amber': ('#ffb000', 220, 200, 130), 'green': ('#33ff66', 205, 180, 115)}


def _phosphor_colours(name):
    full, second, third, off = PHOSPHOR_INK[name];g = NIGHT_GROUND;r, gg, b = rgb(full)
    lay = lambda share: over(full, g, share)
    return dict(
        window=g, surface=lay(12), sidebar=lay(8), raised=lay(22), pressed=lay(40), terminal='#080806',
        hairline=(r, gg, b, 46), stroke=(r, gg, b, 80), stroke_strong=(r, gg, b, 150),
        text=full, secondary=lay(second), tertiary=lay(third), disabled=lay(off),
        accent=full, accent_text=full, accent_fill=full, on_accent=g,
        live=full, live_text=full, on_live=g,
        waiting=full, waiting_text=full, on_waiting=g,
        danger=full, danger_text=full, on_danger=g,
        recheck=lay(second), violet_text=lay(second),
        shadow=(0, 0, 0, 255), scrim=(0, 0, 0, 160),
    )


# ------------------------------------------------------------- 1.1 N1duo: Night: Duo, two phosphors and the grey of the past
# The owner, 28 Nov 2026: "But both the orange and green working together with grey (like screen burns)". One system:
#   GREEN is the computer: files, text, lists, the tree, the board, the terminal, the system pages, the meters.
#   AMBER is Kas and the owner's word: her chip, panel, words and cards, Waits for you, HALT, the selected row and the
#         pressed button (inverse video in amber), the bar's active window, the focus.
#   GREY  is the past: the burn-in ghosts, what is disabled, tertiary words, lines and borders.
# The panels' grounds are the grey laid faintly over the near-black, so neither phosphor tints the other's words; her panel
# is a second tube with a ground a shade warmer (kas_ground, amber 6 %). Measured by tests_integrated/test_night_phosphor.py:
#   green words 14.8:1 on the ground, secondary 9.6:1; amber 10.8:1, her quiet 8.1:1; grey tertiary 7.6:1; 5 : 1 or more
#   on every tint and under Full's scanline and vignette.
DUO_INK = dict(computer='#33ff66', kas='#ffb000', past='#a3a39b')


def _duo_colours():
    g, green, amber, grey = NIGHT_GROUND, DUO_INK['computer'], DUO_INK['kas'], DUO_INK['past']
    lay = lambda colour, share: over(colour, g, share);r, gg, b = rgb(grey)
    return dict(
        window=g, surface=lay(grey, 12), sidebar=lay(grey, 8), raised=lay(grey, 22), pressed=lay(amber, 40), terminal='#080806',
        hairline=(r, gg, b, 46), stroke=(r, gg, b, 80), stroke_strong=(r, gg, b, 150),
        text=green, secondary=lay(green, 205), tertiary=grey, disabled=lay(grey, 150),
        accent=amber, accent_text=amber, accent_fill=amber, on_accent=g,
        live=green, live_text=green, on_live=g,
        waiting=amber, waiting_text=amber, on_waiting=g,
        danger=amber, danger_text=amber, on_danger=g,
        recheck=lay(green, 205), violet_text=lay(green, 205),
        shadow=(0, 0, 0, 255), scrim=(0, 0, 0, 160),
        kas_text=amber, kas_quiet=lay(amber, 220), kas_ground=lay(amber, 15), burn=grey, halt=amber, peak=amber,
    )


def phosphor(look=None):
    """'amber' or 'green': the one a look name asks for ('night-green', 'night-amber'), else the one in force."""
    look = str(look or '')
    for name in PHOSPHORS:
        if look == 'night-' + name:return name
    return PHOSPHOR[0] if PHOSPHOR[0] in PHOSPHORS else PHOSPHOR_DEFAULT


def set_phosphor(name):
    PHOSPHOR[0] = name if name in PHOSPHORS else PHOSPHOR_DEFAULT
    return PHOSPHOR[0]


def is_phosphor(look=None):
    """Whether a look (the one in force when None) is the phosphor Night."""
    return look_of(IN_FORCE[0] if look is None else look) == 'night'


def face(look=None, role='ui'):
    """The chrome's face for a look (the one in force when None): Night's chrome is fixed-width (IBM Plex Mono)."""
    return FONT['mono'] if is_phosphor(look) else FONT[role]


def _key(look):
    return 'night-' + phosphor(look) if look_of(look) == 'night' else 'day'

# How much of a colour is laid over a ground for each tint, as a share of 255 (whole numbers: no floating point).
TINT = dict(selection=31, live=26, waiting=26, danger=22, recheck=26, hover=13, ring_accent=23, ring_live=28, yours=15)
# selection 12 %, live/waiting/recheck 10 %, danger 9 %, hover 5 %, rings: accent 9 %, live 11 % (section 9), your words 6 %

# ------------------------------------------------------------------------------------------------------------- type
FONT = dict(ui='Inter', display='Inter Display', mono='IBM Plex Mono')
FONT_FILES = dict(inter=('Inter-Regular.otf', 'Inter-Medium.otf', 'Inter-SemiBold.otf', 'InterDisplay-SemiBold.otf'))
# role: (px, line height px, weight, face role, tracking in hundredths of a px, capitals)
TYPE = dict(
    caption=(11, 14, 500, 'ui', 40, True),         # section labels in capitals, +0.4 tracking
    footnote=(12, 16, 400, 'ui', 0, False),
    body=(13, 18, 400, 'ui', 0, False),
    body_strong=(13, 18, 600, 'ui', 0, False),
    subhead=(15, 20, 600, 'ui', 0, False),
    title=(17, 22, 600, 'ui', 0, False),
    title2=(20, 26, 600, 'ui', 0, False),
    display=(26, 32, 600, 'display', 0, False),    # empty states only
    mono=(12, 16, 400, 'mono', 0, False),          # numbers, cells, lines, the Terminal (tabular figures)
)
LEAST_PX = 11            # nothing under 11 px; body never under 13 px at 1366x768

# ------------------------------------------------------------------------------------------------- space and shape
GRID = 4
PAD = dict(xs=8, s=12, m=16, l=24)
GUTTER = 16
RADIUS = dict(control=6, tile=10, panel=14, menu=14, popover=14, row=6, toast=10)
# elevation: (x, y, blur, alpha of the shadow colour out of 255), plus whether a hairline ring goes round it
ELEVATION = {1: (0, 1, 2, 15, True), 2: (0, 8, 24, 36, False)}
CONTROL = dict(button=28, field=28, row=26, tab_rule=2, focus_ring=3, focus_alpha=89, scroll=10, segment=28)
MOTION = dict(hover=160, panel=220, tile=240)      # ms, ease-out; Reduce motion turns all of it off
GLOW = 0                 # no glow in Day or Night: depth comes from elevation
GLASS = ('#0c1322', '#16233a', '#3a74b8')      # Day's dark projector glass (P3's): its top, its foot, its edge; no picture stands on it since 1.0 P4 no avatar

# ------------------------------------------------------------------------------------- 1.1 K0: tokens 1.1, the frame
# DESIGN_DIRECTION_1.1.md section 4: chrome cut from about 188 px to about 116 at 1920x1200. 1.0's window spent 187 on it
# (the head 60, the centre bar 34, the context row 33, the foot 60); 1.1 spends 114: the head 32 (File Edit View Go Tools
# Help), the centre bar 34 (E1's, unchanged), the foot 48 (44 in a window under 900 px tall), and the context row stands only
# over a code tab (details_pane_qt.ContextRow). The bar (B1, 44 px; 40 at 1366x768) is a window of its own below. Every look
# (Day, Night, Graphite, Kasandra) stands on this frame; each keeps its own faces and colours on it.
CHROME = dict(head=32, foot=48, foot_short=44, short_below=900)
HEAD_PX = dict(day=14, night=14, graphite=14, kasandra=15)      # the head's menu words (never under LEAST_PX)
DETAILS = dict(width=320, preview=180, pad=16)                  # the details pane: on call, at the right of the centre


def chrome(scale=1.0, window_height=1200):
    """(head, foot) in px for the interface scale (the window's, 14 pt = 1.0) and the window's height."""
    s = max(1.0, min(float(scale), 1.4))
    foot = CHROME['foot'] if int(window_height) >= CHROME['short_below'] else CHROME['foot_short']
    return round(CHROME['head'] * s), round(foot * s)


def head_px(look, scale=1.0):
    """The head's menu words in px for a look (day, night, graphite, kasandra) at the interface scale."""
    return max(LEAST_PX, round(HEAD_PX.get(str(look), HEAD_PX['day']) * max(1.0, min(float(scale), 1.4))))


# ------------------------------------------------------------------------------------------------------- the maths
def rgb(colour):
    """(r, g, b) of '#rrggbb'."""
    c = str(colour).lstrip('#')
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def hex_of(r, g, b):
    return '#%02x%02x%02x' % (r, g, b)


def over(colour, ground, alpha=None):
    """`colour` laid over the opaque `ground` at `alpha` (0-255; a 4-tuple carries its own), as an opaque '#rrggbb'. Whole
    numbers, rounded half up."""
    if isinstance(colour, tuple):
        r, g, b, a = colour
    else:
        (r, g, b), a = rgb(colour), 255
    if alpha is not None:a = alpha
    gr, gg, gb = rgb(ground)
    return hex_of(*((a * c + (255 - a) * d + 127) // 255 for c, d in ((r, gr), (g, gg), (b, gb))))


def rgba(colour, alpha=None):
    """A colour as a style sheet's rgba(r, g, b, a), alpha 0-255."""
    if isinstance(colour, tuple):
        r, g, b, a = colour
    else:
        (r, g, b), a = rgb(colour), 255
    return 'rgba(%d, %d, %d, %d)' % (r, g, b, a if alpha is None else alpha)


COLOUR.update(('night-' + _name, _phosphor_colours(_name)) for _name in MONO_PHOSPHORS)      # 1.1 N1
COLOUR['night-duo'] = _duo_colours()      # 1.1 N1duo


def look_of(look):
    return 'night' if str(look) in ('night',) + tuple('night-' + n for n in PHOSPHORS) else 'day'      # 1.1 N1 (N1duo: night-duo): a phosphor's name is Night


def colours(look):
    """Every colour of a look, the given ones and the ones made from them (tints, opaque hairlines), all '#rrggbb' except
    the ones with alpha (hairline_a, stroke_a, shadow, scrim)."""
    c = dict(COLOUR[_key(look)])      # 1.1 N1: Night in its phosphor
    surface, window, sidebar = c['surface'], c['window'], c['sidebar']
    made = dict(
        hairline_a=c['hairline'], stroke_a=c['stroke'], stroke_strong_a=c['stroke_strong'],
        hairline=over(c['hairline'], surface), hairline_window=over(c['hairline'], window),
        stroke=over(c['stroke'], surface), stroke_strong=over(c['stroke_strong'], surface),
        selection=over(c['accent'], surface, TINT['selection']), selection_side=over(c['accent'], sidebar, TINT['selection']),
        live_tint=over(c['live'], surface, TINT['live']), waiting_tint=over(c['waiting'], surface, TINT['waiting']),
        danger_tint=over(c['danger'], surface, TINT['danger']), recheck_tint=over(c['recheck'], surface, TINT['recheck']),
        hover=over(c['text'], surface, TINT['hover']), hover_side=over(c['text'], sidebar, TINT['hover']),
        yours=over(c['accent'], surface, TINT['yours']),
        ring_accent=over(c['accent'], surface, TINT['ring_accent']), ring_live=over(c['live'], surface, TINT['ring_live']),
        wire=c['accent'], wire_soft=over(c['accent'], surface, 170),
        focus_ring=rgba(c['accent'], CONTROL['focus_alpha']),
    )
    c.update(made, shadow_a=c['shadow'], scrim_a=c['scrim'])
    # 1.1 N1: the active window on the bar, the selected row and the pressed button: a plate and its words. Inverse video
    # (a block of the phosphor, the words in the ground) in Night; the selection's tint and the plain words in Day.
    night = look_of(look) == 'night'
    c.update(active_plate=c['accent_fill'] if night else c['selection_side'], on_active=c['on_accent'] if night else c['text'])
    for key, same in (('kas_text', 'text'), ('kas_quiet', 'secondary'), ('kas_ground', 'sidebar'), ('burn', 'text'), ('halt', 'live'), ('peak', 'live')):
        c.setdefault(key, c[same])      # 1.1 N1duo: her words, her ground, the burn's grey, HALT, a meter's peak: their own only in Duo
    return c


def is_duo(c):
    """1.1 N1duo: whether a look's colours (colours()) are Night: Duo's, where Kas and the computer have phosphors of their own."""
    return c.get('kas_text') != c.get('text')


# Every pair of words and the ground they are laid on, by token name: (words, ground, where). Measured by the builder
# (P4's smoke script): each must be 4.5:1 or more. 'disabled' words are an inactive control's and are listed apart
# (DISABLED_PAIRS: WCAG 1.4.3 asks no ratio of them; they read at 2.5:1 or more and always beside a word that says why).
_GROUNDS = ('window', 'surface', 'sidebar', 'raised')
TEXT_PAIRS = (
    [(ink, ground, 'text') for ink in ('text', 'secondary', 'tertiary') for ground in _GROUNDS + ('selection', 'selection_side', 'hover', 'yours', 'live_tint', 'waiting_tint', 'danger_tint', 'pressed')]
    + [(ink, ground, 'state') for ink in ('accent', 'live', 'waiting', 'danger', 'recheck') for ground in _GROUNDS]
    + [('accent_text', g, 'selected row') for g in _GROUNDS + ('selection', 'selection_side', 'hover', 'yours')]
    + [('live_text', g, 'live words') for g in _GROUNDS + ('live_tint',)]
    + [('waiting_text', g, 'waiting words') for g in _GROUNDS + ('waiting_tint',)]
    + [('danger_text', g, 'danger words') for g in _GROUNDS + ('danger_tint',)]
    + [('violet_text', g, 'recheck words') for g in _GROUNDS + ('recheck_tint',)]
    + [('on_accent', 'accent_fill', 'primary button'), ('on_live', 'live', 'live fill'), ('on_waiting', 'waiting', 'waiting fill'),
       ('on_danger', 'danger', 'danger fill'), ('text', 'terminal', 'terminal'), ('secondary', 'terminal', 'terminal')]
)
DISABLED_PAIRS = [('disabled', g, 'inactive control') for g in _GROUNDS]
# 1.1 N1: the phosphor Night's pairs: TEXT_PAIRS, and the ground's words on each inverse block (a selected row, a pressed or
# checked control in the style sheet, the active window on the bar, HALT). Measured by tests_integrated/test_night_phosphor.py
# for both phosphors. The bar's own buttons, pressed, lay a tint (pressed, 16 % of the phosphor) under their phosphor words.
NIGHT_PAIRS = TEXT_PAIRS + [('on_accent', g, 'inverse video') for g in ('accent_fill', 'active_plate', 'danger', 'live', 'waiting')]
NIGHT_PAIRS += [(ink, g, 'her words, on her tube') for ink in ('kas_text', 'kas_quiet', 'tertiary') for g in _GROUNDS + ('kas_ground', 'waiting_tint')]      # 1.1 N1duo


# ------------------------------------------------------------------------------- the roles boss_theme draws with
def palette(look):
    """The look's palette under boss_theme's role names (the names every surface of the window already reads), made from the
    tokens alone. What each role means is said in boss_theme; here is only which token plays it."""
    c = colours(look);night = look_of(look) == 'night'
    band = rgb(c['sidebar'])
    return dict(
        GROUND=c['window'], PANEL=c['sidebar'], CARD=c['surface'], RAISED=c['raised'], TERMINAL_GROUND=c['terminal'],
        LINE=c['hairline'], LINE_STRONG=c['stroke_strong'], LINE_MID=c['stroke'],
        TEXT=c['text'], QUIET=c['secondary'], FAINT=c['tertiary'],
        AMBER=c['selection'], AMBER_SOFT=c['selection'], AMBER_EDGE=c['accent'], AMBER_TEXT=c['accent_text'],
        PENCIL_DEEP=c['hover'], ERASER=c['waiting_tint'], ERASER_DEEP=over(c['waiting'], c['surface'], 46), ERASER_MARK=c['waiting'],
        TEAL=c['live'], TEAL_SOFT=c['live_tint'], TEAL_EDGE=c['live'], TEAL_TEXT=c['live_text'], READY=c['live'], STOP=c['danger'],
        OWNER=c['waiting'], ON_OWNER=c['on_waiting'], RECHECK=c['recheck'],
        BAND=band, ERASED=c['text'], ERASED_QUIET=c['secondary'], BAND_MARK=c['accent'], BAND_PENCIL=c['live'],
        DESK_LIGHT=c['surface'] if not night else '#ffffff', VEIL=c['window'],
        DISPLAY=face(look), FACE=face(look), MONO=FONT['mono'],      # 1.1 N1: Night's chrome is fixed-width
        HONEY=c['waiting_text'], VIOLET=c['secondary'], VIOLET_DEEP=c['stroke'], VIOLET_PALE=c['text'], VIOLET_SOFT=c['yours'],
        ROYAL=c['live'], ROYAL_SOFT=c['live_tint'], ROYAL_INK=c['live_text'], ROYAL_TEXT=c['live_text'],
        RED=c['danger'], ON_RED=c['on_danger'],
        CUE=c['live_tint'], CUE_EDGE=c['live'], CUE_TEXT=c['live_text'],
        BAR=c['accent_fill'], ON_BAR=c['on_accent'], BAR_EDGE=c['accent_fill'], ON_BAR_QUIET=c['on_accent'], ON_AMBER=c['accent_text'],
    )


def marks(look):
    """The board's and the head's own marks: the wires (WIRE solid, a recorded link; WIRE_SOFT for a possible one, dashed
    and said "not verified"), the rings round the focus (RING_BLUE accent 9 %, RING_GREEN live 11 %), HALT's triangle (the
    live green in both: red in Night would read as an error), the shadow under a tile (SHADOW, drawn with ELEVATION's alpha),
    and the equalizer's colours (EQ_LOW, EQ_MID accent, EQ_HIGH live, EQ_HOT waiting)."""
    c = colours(look);meter = c['live'] if is_duo(c) else c['accent']      # 1.1 N1duo: Duo's meters are the computer's green
    return dict(WIRE=c['wire'], WIRE_SOFT=c['wire_soft'], WIRE_WORDS=c['accent_text'], RING_BLUE=c['ring_accent'], RING_GREEN=c['ring_live'],
                HALT=c['halt'], HALT_HELD=c['waiting'], SHADOW=c['text'] if look_of(look) == 'day' else '#000000',      # 1.1 N1duo: HALT amber in Duo
                EQ_LOW=over(meter, c['surface'], 120), EQ_MID=meter, EQ_HIGH=c['live'], EQ_HOT=c['peak'],      # 1.1 N1duo: green bars, an amber peak
                SELECTION=c['selection'], HOVER=c['hover'], FOCUS_RING=c['focus_ring'])


def shadow_alpha(level):
    """The alpha (0-255) of a level's shadow."""
    return ELEVATION[level][3]


def type_css(role, look='day'):
    """A type role as CSS: family, size, weight and tracking."""
    px, _, weight, face, track, caps = TYPE[role]
    return 'font-family:"%s";font-size:%dpx;font-weight:%d;%s%s' % (
        FONT[face], px, weight, ('letter-spacing:%d.%02dpx;' % (track // 100, track % 100)) if track else '',
        '' if not caps else '')


# ------------------------------------------------------------------------------------------------ the style sheet
def sheet(look):
    """The window's style sheet for Day or Night: laid after the older sheets (theme2, boss_theme.CHROME_OVERRIDES), so it
    has the last word on every control. Controls 28 px, radius 6; menus and popovers radius 14 at level 2; tabs underlined
    2 px in the accent; tree and list rows 26 px, the selected row an inset rounded fill at accent 12 %; thin scroll bars; a
    focus ring a keyboard can follow on every control."""
    c = colours(look);night = look_of(look) == 'night'
    v = dict(c)
    v.update(R=RADIUS['control'], RM=RADIUS['menu'], RT=RADIUS['tile'], H=CONTROL['button'], F=CONTROL['field'], ROW=CONTROL['row'],
             FONT=face(look), MONO=FONT['mono'], body=TYPE['body'][0], foot=TYPE['footnote'][0], cap=TYPE['caption'][0],      # 1.1 N1: face
             sel_words=c['on_accent'] if night else c['accent_text'], scroll=CONTROL['scroll'],
             thumb=rgba(c['text'], 64), thumb_hover=rgba(c['text'], 110),
             focus=rgba(c['accent'], CONTROL['focus_alpha']))
    return '''
QMainWindow, QDialog {background:%(window)s;}
QWidget {color:%(text)s;}
QToolTip {background:%(surface)s; color:%(text)s; border:1px solid %(stroke)s; border-radius:%(R)dpx; padding:6px 10px;}
QMenu {background:%(surface)s; border:1px solid %(stroke)s; border-radius:%(RM)dpx; padding:6px;}
QMenu::item {padding:6px 28px 6px 12px; border:0; border-radius:%(R)dpx; color:%(text)s; background:transparent;}
QMenu[glyphs="true"]::item {padding-left:40px;}
QMenu::item:selected {background:%(accent_fill)s; color:%(on_accent)s; border:0;}
QMenu::item:disabled, QMenu::item:selected:disabled {color:%(disabled)s; background:transparent;}
QMenu::separator {height:1px; background:%(hairline)s; margin:6px 10px;}
QPushButton {color:%(text)s; background:transparent; border:1px solid transparent; border-radius:%(R)dpx; padding:4px 8px;}
QPushButton:hover {background:%(hover)s; border-color:transparent;}
QPushButton:pressed {background:%(pressed)s;}
QPushButton:checked {background:%(selection)s; color:%(accent_text)s; border:1px solid transparent; font-weight:600;}
QPushButton:focus {border:1px solid %(accent)s;}
QPushButton:disabled {color:%(disabled)s; background:transparent; border-color:transparent;}
QPushButton[arcButton="tool"], QToolButton[arcButton="tool"] {
    color:%(text)s; background:%(surface)s; border:1px solid %(stroke)s; border-radius:%(R)dpx; padding:3px 12px; min-height:20px;}
QPushButton[arcButton="tool"]:hover, QToolButton[arcButton="tool"]:hover {background:%(raised)s; border:1px solid %(stroke)s; color:%(text)s;}
QPushButton[arcButton="tool"]:pressed, QToolButton[arcButton="tool"]:pressed {background:%(pressed)s; border:1px solid %(stroke_strong)s;}
QPushButton[arcButton="tool"]:focus, QToolButton[arcButton="tool"]:focus {border:2px solid %(accent)s; padding:2px 11px;}
QPushButton[arcButton="tool"]:checked, QToolButton[arcButton="tool"]:checked {background:%(selection)s; color:%(accent_text)s; border:1px solid %(accent)s; font-weight:600;}
QPushButton[arcButton="tool"]:disabled, QToolButton[arcButton="tool"]:disabled {color:%(disabled)s; background:transparent; border:1px solid %(hairline)s;}
QPushButton[arcButton="primary"] {background:%(accent_fill)s; color:%(on_accent)s; border:1px solid %(accent_fill)s; font-weight:600; padding:3px 14px;}
QPushButton[arcButton="primary"]:hover {background:%(accent_fill)s; border:1px solid %(accent_text)s;}
QPushButton[arcButton="primary"]:focus {border:2px solid %(accent_text)s; padding:2px 13px;}
QPushButton[arcButton="link"] {color:%(accent_text)s; border:0; padding:2px 0; background:transparent; text-decoration:none;}
QPushButton[arcButton="link"]:hover {text-decoration:underline; background:transparent;}
QPushButton[arcButton="filter"], QPushButton[arcButton="segment"] {color:%(secondary)s; background:transparent; border:0; border-bottom:2px solid transparent; border-radius:0; padding:6px 6px;}
QPushButton[arcButton="filter"]:hover, QPushButton[arcButton="segment"]:hover {color:%(text)s;}
QPushButton[arcButton="filter"]:checked, QPushButton[arcButton="segment"]:checked {color:%(text)s; background:transparent; border-bottom:2px solid %(accent)s; font-weight:600;}
QToolButton {color:%(text)s; background:transparent; border:1px solid transparent; border-radius:%(R)dpx; padding:3px 6px;}
QToolButton:hover {background:%(hover)s;}
QToolButton:pressed {background:%(pressed)s;}
QToolButton:checked {background:%(selection)s; color:%(accent_text)s;}
QToolButton:focus {border:1px solid %(accent)s;}
QToolButton::menu-indicator {image:none; width:0;}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit {
    background:%(surface)s; color:%(text)s; border:1px solid %(stroke)s; border-radius:%(R)dpx; padding:3px 8px; min-height:20px;
    selection-background-color:%(selection)s; selection-color:%(text)s;}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {border:1px solid %(stroke_strong)s;}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus {border:2px solid %(accent)s; padding:2px 7px;}
QLineEdit:disabled, QComboBox:disabled {color:%(disabled)s; background:%(window)s;}
QComboBox::drop-down {border:0; width:20px;}
QComboBox QAbstractItemView {background:%(surface)s; border:1px solid %(stroke)s; border-radius:%(R)dpx; padding:4px; outline:0;
    selection-background-color:%(accent_fill)s; selection-color:%(on_accent)s;}
QPlainTextEdit, QTextEdit, QTextBrowser {background:%(surface)s; color:%(text)s; border:1px solid %(hairline)s; border-radius:%(R)dpx;
    selection-background-color:%(selection)s; selection-color:%(text)s;}
QPlainTextEdit:focus, QTextEdit:focus {border:2px solid %(accent)s;}
QTabBar::tab {color:%(secondary)s; background:transparent; border:0; border-bottom:2px solid transparent; padding:6px 10px; border-radius:0;}
QTabBar::tab:hover {color:%(text)s;}
QTabBar::tab:selected {color:%(text)s; border-bottom:2px solid %(accent)s; background:transparent; font-weight:600;}
QTreeView, QTreeWidget, QListView, QListWidget, QTableView, QTableWidget {
    background:%(surface)s; color:%(text)s; border:0; outline:0; show-decoration-selected:0;
    selection-background-color:%(selection)s; selection-color:%(sel_words)s; alternate-background-color:%(window)s;}
QTreeView::item, QListView::item {min-height:%(ROW)dpx; border:0; border-radius:%(R)dpx; padding:0 4px;}
QTreeView::item:hover, QListView::item:hover {background:%(hover)s;}
QTreeView::item:selected, QListView::item:selected {background:%(selection)s; color:%(sel_words)s; border:0;}
QHeaderView::section {background:%(window)s; color:%(secondary)s; border:0; border-bottom:1px solid %(hairline)s; padding:4px 8px; font-weight:600;}
QTableView {gridline-color:%(hairline)s;}
QScrollBar:vertical {background:transparent; width:%(scroll)dpx; margin:0; border:0;}
QScrollBar:horizontal {background:transparent; height:%(scroll)dpx; margin:0; border:0;}
QScrollBar::handle:vertical {background:%(thumb)s; border-radius:3px; min-height:28px; margin:2px 2px;}
QScrollBar::handle:horizontal {background:%(thumb)s; border-radius:3px; min-width:28px; margin:2px 2px;}
QScrollBar::handle:hover {background:%(thumb_hover)s;}
QScrollBar::add-line, QScrollBar::sub-line {width:0; height:0; border:0; background:transparent;}
QScrollBar::add-page, QScrollBar::sub-page {background:transparent;}
QCheckBox, QRadioButton {color:%(text)s; spacing:8px;}
QProgressBar {background:%(raised)s; border:0; border-radius:3px; color:%(text)s; text-align:center; max-height:6px;}
QProgressBar::chunk {background:%(accent)s; border-radius:3px;}
QSplitter::handle {background:%(hairline)s;}
QMainWindow::separator {background:%(hairline)s; width:1px; height:1px;}
QToolButton#MoreMenus, QToolButton#HeadMenu, QToolButton#BossPrograms, QToolButton#SystemMenu {
    font-family:"%(FONT)s"; color:%(text)s; background:transparent; border:0; border-radius:%(R)dpx; padding:4px 10px;}
QToolButton#HeadMenu {color:%(secondary)s; padding:4px 8px;}
QToolButton#MoreMenus:hover, QToolButton#HeadMenu:hover, QToolButton#BossPrograms:hover, QToolButton#SystemMenu:hover {
    color:%(text)s; background:%(hover)s; border:0;}
QToolButton#MoreMenus:focus, QToolButton#HeadMenu:focus, QToolButton#HeadMenu:pressed, QToolButton#BossPrograms:focus, QToolButton#SystemMenu:focus {
    color:%(text)s; background:%(selection)s; border:0;}
QLineEdit#WorkspacePath, QLineEdit#WorkspacePath:focus {background:transparent; color:%(secondary)s; border:0; padding:0; font-family:"%(MONO)s";}
QLabel#MonitorReading {color:%(secondary)s; font-family:"%(MONO)s";}
QLabel#MonitorReading[liveReading="true"] {color:%(live_text)s;}
QLineEdit#SlateInput, QPlainTextEdit#SlateInput, QPlainTextEdit#Capture, QLineEdit#ProjectTitle {
    background:%(surface)s; color:%(text)s; border:1px solid %(stroke)s; border-radius:%(R)dpx; padding:6px 10px;
    selection-background-color:%(selection)s; selection-color:%(text)s;}
QLineEdit#SlateInput:focus, QPlainTextEdit#SlateInput:focus, QPlainTextEdit#Capture:focus, QLineEdit#ProjectTitle:focus {
    border:2px solid %(accent)s; padding:5px 9px;}
QFrame#BossChainTray {background:%(sidebar)s; border-top:1px solid %(hairline)s;}
QTabWidget#ConsolePages::pane {background:%(window)s; border:0;}
QFrame#GraphiteToast {border-radius:%(RT)dpx;}
''' % v + (PHOSPHOR_SHEET % v if night else '')      # 1.1 N1


# 1.1 N1duo: the progress bar's chunk is a meter: the computer's (live) colour, the phosphor in Amber and Green.
# 1.1 N1: the phosphor Night's last word: inverse video for the selected row, the pressed and the checked button and the
# menu's row; the chrome in the fixed-width face, long prose (a page, her answers) in Inter.
PHOSPHOR_SHEET = '''
QWidget {font-family:"%(MONO)s";}
QTextBrowser, QTextEdit {font-family:"Inter";}
QPushButton:pressed, QPushButton:checked, QToolButton:pressed, QToolButton:checked,
QPushButton[arcButton="tool"]:pressed, QToolButton[arcButton="tool"]:pressed,
QPushButton[arcButton="tool"]:checked, QToolButton[arcButton="tool"]:checked {background:%(accent_fill)s; color:%(on_accent)s; border:1px solid %(accent_fill)s;}
QTreeView::item:selected, QListView::item:selected {background:%(accent_fill)s; color:%(on_accent)s;}
QTreeView, QTreeWidget, QListView, QListWidget, QTableView, QTableWidget {selection-background-color:%(accent_fill)s; selection-color:%(on_accent)s;}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QPlainTextEdit, QTextEdit, QTextBrowser {selection-background-color:%(accent_fill)s; selection-color:%(on_accent)s;}
QToolButton#MoreMenus:pressed, QToolButton#HeadMenu:pressed {background:%(accent_fill)s; color:%(on_accent)s;}
QProgressBar::chunk {background:%(live)s;}
'''

