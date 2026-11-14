"""BOSS desk colours. Presentation only; document formats keep their own ink (a page may be shown in the desk's
light, page_light, which changes how brightly it is seen here and nothing of the document).

A control looks like a control (13 November 2026: "bring in buttons where useful ... make it look more complete and
untied to the work"). An action is a button: a word on a dark plate with a quiet edge (arcButton "tool", made with
theme2.tool) that answers the pointer in green and the keyboard in amber. Nothing on the desk is outlined in the pale ink:
the owner, of the first cut of these buttons, "No ugly white boxes that stand out like a sore thumb". A button, a field and
a scroll thumb are told from the ground by a plate a shade lighter and an edge a shade lighter again, never by a bright line. A word that only goes somewhere stays an underlined word. The work itself
(a page, a table, a sheet) has neither look, so the two are never mistaken for each other.

Amber is for what is selected, what has the keyboard, and what waits for the owner. Green is for what is live: readings,
what is current, staC, the pointer, and whatever the pointer is over (13 November 2026: "the mouse pointer to be the systems
green ... more green glowing").

In Kasandra (0.8.3, the owner: "I'm kinda thinking that highlighting should be in our burnt yellow??? Like especially in
menus???") what is selected and what has the keyboard is burnt yellow: the row you are on in a menu is a solid bar (BAR,
with ON_BAR the dark ink on it and BAR_EDGE its 2 px edge); every other highlight is an edge and words (AMBER_EDGE,
AMBER_TEXT) on a fill (AMBER_SOFT). Every highlight fill is opaque, and yellow light is only ever added to what lies under
it (lays_light), never mixed over her cyan: mixed, yellow and cyan make green. Her cyan keeps what it says there: the
pointer, what is ready, the line, the bands' rule, and the cues that are not a selection (CUE, CUE_EDGE, CUE_TEXT, which
are Graphite's amber and her old cyan)."""
import json
import os
import re

# Two appearances (0.8.0). Graphite is the desk as it was: warm ink on near-black glass, amber for what is selected and
# what waits for the owner, green for what is live. Kasandra is the owner's second direction (13 November 2026, "I think
# I really like the LAIN/kasandra idea"; the pack's palette.json): ink and pale blue on dark indigo, burnt yellow for
# what is selected and has the keyboard (cyan until 0.8.3), cyan for what is ready, raspberry for a decision that waits for
# the owner, lavender with a dashed edge for a recheck.
#
# The appearance is chosen once, when this module is first imported, which is inside qt_app.make_app before any window
# exists, so every module that copies a colour at import sees the chosen one. A change (Rules ▸ Desk artwork ▸
# Appearance) is kept in the session and takes effect at the next start. GRAPHITE_APPEARANCE in the environment wins,
# so a check or a test can choose without touching anyone's profile.
APPEARANCES = (('graphite', 'Graphite'), ('kasandra', 'Kasandra'))
APPEARANCE_KEY = 'appearance'
PALETTES = {
    'graphite': dict(
        GROUND='#0b0e0d', PANEL='#111513', CARD='#151a17', RAISED='#202520', TERMINAL_GROUND='#080a09',
        LINE='#474436', LINE_STRONG='#bcac8e', LINE_MID='#6b6550', TEXT='#f4e8ce', QUIET='#c8baa0', FAINT='#a89b84',
        AMBER='#4b2a14', AMBER_SOFT='#4b2a14', AMBER_EDGE='#ff9a36', AMBER_TEXT='#ffba72',
        PENCIL_DEEP='#443527', ERASER='#493225', ERASER_DEEP='#593a29', ERASER_MARK='#dd854b',
        TEAL='#c3ed74', TEAL_SOFT='#1b2817', TEAL_EDGE='#789654', TEAL_TEXT='#cbf08b', READY='#c3ed74', STOP='#ff9a36',
        OWNER='#ff9a36', ON_OWNER='#0b0e0d', RECHECK='#ff9a36',
        BAND=(12, 15, 14), ERASED='#efeae0', ERASED_QUIET='#b0bcb9', BAND_MARK='#dd854b', BAND_PENCIL='#f2a369',
        DESK_LIGHT='#8c826b', VEIL='#000000', DISPLAY='IBM Plex Mono', FACE='IBM Plex Sans', MONO='IBM Plex Mono',
        HONEY='#f2a369', VIOLET='#c8baa0', VIOLET_DEEP='#474436', VIOLET_PALE='#f4e8ce', VIOLET_SOFT='#4b2a14',
        ROYAL='#cbf08b', ROYAL_SOFT='#1b2817', ROYAL_INK='#cbf08b', ROYAL_TEXT='#cbf08b', RED='#ff9a36', ON_RED='#0b0e0d',
        CUE='#4b2a14', CUE_EDGE='#ff9a36', CUE_TEXT='#ffba72',
        BAR='#4b2a14', ON_BAR='#f4e8ce', BAR_EDGE='#4b2a14', ON_BAR_QUIET='#c8baa0', ON_AMBER='#f4e8ce'),
    'kasandra': dict(
        GROUND='#171b3c', PANEL='#1b1f45', CARD='#1f234d', RAISED='#292d56', TERMINAL_GROUND='#11132c',
        LINE='#3b4479', LINE_STRONG='#8796cb', LINE_MID='#5969a1', TEXT='#e3e3ff', QUIET='#c1c6e8', FAINT='#9ca3d2',
        AMBER='#5a3f0c', AMBER_SOFT='#5a3f0c', AMBER_EDGE='#e2a72e', AMBER_TEXT='#ffd27a',
        PENCIL_DEEP='#2b2f63', ERASER='#2e2a5c', ERASER_DEEP='#3b3474', ERASER_MARK='#a9b6ee',
        TEAL='#83eaff', TEAL_SOFT='#1f3560', TEAL_EDGE='#5a8fc4', TEAL_TEXT='#b9f4ff', READY='#83eaff', STOP='#fa507c',
        OWNER='#fa507c', ON_OWNER='#171b3c', RECHECK='#c3b6f4',
        BAND=(20, 23, 52), ERASED='#e3e3ff', ERASED_QUIET='#aeb4dc', BAND_MARK='#e2a72e', BAND_PENCIL='#ffd27a',
        DESK_LIGHT='#8f97c9', VEIL='#11132c', DISPLAY='Kasandra Elite', FACE='Kasandra Elite', MONO='Kasandra Elite Mono',
        HONEY='#e9b872', VIOLET='#ab8eda', VIOLET_DEEP='#5f4fa8', VIOLET_PALE='#d2c4f5', VIOLET_SOFT='#2b2660',
        ROYAL='#7b4fd8', ROYAL_SOFT='#271a58', ROYAL_INK='#ebe2ff', ROYAL_TEXT='#b9a1f6', RED='#ff3b5c', ON_RED='#fff1f4',
        CUE='#1d3d63', CUE_EDGE='#83eaff', CUE_TEXT='#b9f4ff',
        BAR='#e2a72e', ON_BAR='#171b3c', BAR_EDGE='#ffd27a', ON_BAR_QUIET='#4a3d2a', ON_AMBER='#ffd27a'),
}
# 0.8.3, the owner: "I'm kinda thinking that highlighting should be in our burnt yellow??? Like especially in menus???",
# "You measure what is visually pleasing", and "we have to be careful how that makes the graphite not look green". So, in
# Kasandra only (Graphite keeps every colour it had):
#   the row you are on in a menu   BAR #e2a72e, solid, with ON_BAR #171b3c (7.79:1) and a 2 px BAR_EDGE #ffd27a; ON_BAR_QUIET
#                                  (4.9:1) for a row that says why it cannot act. In Graphite these are its menus' amber wash
#                                  and their own inks, and the edge is the wash itself (no edge shows).
#   every other highlight          AMBER_SOFT #5a3f0c with AMBER_EDGE #e2a72e and words in AMBER_TEXT #ffd27a (6.86:1);
#                                  ON_AMBER is the words on a highlight (Graphite: its ink, as before).
#   the bands' marks               BAND_MARK (the keyboard's place on a band word or a tab) #e2a72e, BAND_PENCIL (the chosen
#                                  one) #ffd27a.
#   cues that are not a selection  CUE, CUE_EDGE, CUE_TEXT: what a status word, a heading's rule, a primary button, a band's
#                                  rule or a prompt was before, Graphite's amber and her old cyan.
# Burnt yellow is laid on opaque fills, or added as light (lays_light), never mixed over cyan: measured, 30-50 % of it over
# #83eaff or #1d3d63 gives hues of 86-156 degrees, green; over her indigo grounds even half of it stays warm (28-37).


# 0.8.2, the owner, of Kasandra's typewriter face: "I want as much font in that LAIN font as what looks kool, but still
# readable, but I like that font … Try hard to make LAIN font work all over." And 0.8.3: all the window's faces in that
# typewriter face. FACE is the face of the window's words (the reading profile's interface and prose families while the owner has
# not chosen others, every menu, tab, tree, button and card title); DISPLAY is the face of headings; MONO is the face of what
# must be read exactly and line up: code and lines, the typing line, Terminal, addresses, numbers in a table, small tags.
# In Kasandra all three are the typewriter face, built from Special Elite (tools/derive_typewriter.py): Kasandra Elite for
# words, with a slashed zero, a sloped one, a tailed l and figures of one width; Kasandra Elite Mono for MONO, the same letters
# on a fixed pitch and on Plex Mono's line, so every row measured in Plex Mono keeps its height. In Graphite they are Plex.

# 0.8.0, the owner: "Should we welcome more colors like a yellow that matches her hair and more shades of violet". Each has
# one job, so that a colour still says something: HONEY is hers (the edge of her answers, the mark under her name when
# she is the one typed to); the violets are the desk's structure (section headings and the Field's column titles in
# VIOLET, the greeting in VIOLET_PALE, your own messages on VIOLET_SOFT with a VIOLET_DEEP edge, the equalizer's bars).
# In Graphite each of them is the colour that place already had (pencil, quiet, line, text, amber-soft): nothing moves.
# And: "If royal purple could add anything valuable it might look nice." ROYAL is the line, the desk's quiet power: a line
# you can run stands on a royal-purple slab (ROYAL_SOFT, with a ROYAL edge and ROYAL_INK letters) wherever she shows one,
# the arrow turns royal purple when what you typed is a line it will run, and the Field's line is said in ROYAL_TEXT.
# Graphite keeps its green for all of these.
# 0.8.1, the owner: "Maybe the send arrow for when we type something. I should experiment with that being red. Experiment
# with the trash can being red." RED (Kasandra only) is on the arrow that sends what you typed and on the Trash can; with
# ON_RED the ink on it. In Graphite RED is its amber, and neither place changes there.


def line_sheet():
    """The look of a line you can run, shown as words: Graphite's green letters; in Kasandra a royal-purple slab."""
    if APPEARANCE == 'graphite':return 'color:%s' % TEAL_TEXT
    return 'color:%s;background:%s;border:0;border-left:3px solid %s;padding:6px 8px' % (ROYAL_INK, ROYAL_SOFT, ROYAL)


def face_css(family, px):
    """A widget's own face, family and size together: the window's sheet (reading_preferences.apply) sets both on every
    widget, and a widget's setFont loses to it, so a face that must hold is given in the widget's own sheet."""
    return 'font-family:"%s";font-size:%dpx;' % (family, int(px))


def eye(line):
    """A line as it is shown: long record numbers shortened for the eye (the line itself stays exact, in its tip)."""
    return re.sub(r'([0-9a-f]{6})[0-9a-f]{20,}', '\\1…', str(line))


def chosen_appearance(environ=None, path=None):
    """'graphite' or 'kasandra': GRAPHITE_APPEARANCE in the environment, else the session file's 'appearance', else
    Graphite. Reads the file with plain json (the session module imports far more than a colour needs)."""
    environ = os.environ if environ is None else environ
    wanted = str(environ.get('GRAPHITE_APPEARANCE', '')).strip().lower()
    if wanted in PALETTES:return wanted
    try:
        if path is None:
            override = environ.get('ARC1_WORKBENCH_CONFIG_HOME')
            base = override if override else os.path.join(environ.get('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config')), 'arc1-workbench')
            path = os.path.join(base, 'session-r10.json')
        with open(path, encoding='utf-8') as stream:
            value = json.load(stream).get(APPEARANCE_KEY)
        return value if value in PALETTES else 'graphite'
    except (OSError, ValueError, AttributeError):
        return 'graphite'


APPEARANCE = chosen_appearance()
globals().update(PALETTES[APPEARANCE])
# The roles, by meaning (0.8.0). In Graphite they are the colours they always were; in Kasandra they part:
# FOCUS what is selected or has the keyboard; LIVE what is current, the pointer, what the pointer is over;
# OWNER a decision that waits for the owner (Approve), with ON_OWNER the ink on it; RECHECK what must be worked again.
FOCUS, LIVE = AMBER_EDGE, READY

# How strongly the desk glows. The owner, with 0.4.6 on the ThinkPad's own panel: "You asked me about the glow effect.
# It's not enough. I want way more glow effect." So there is one dial for all of it (Work ▸ Rules ▸ Desk artwork ▸ Glow),
# and it opens on Neon (0.5.1 opened on Bright): every light on the desk (the halo of what has the keyboard, the lamps of what is live, the
# wires, lit words, the pointer, the rule of each band, the live path in the tree, an icon under the pointer) is
# multiplied by this. Soft is what 0.5.0 had. The Clean desk has no glow whatever this says.
GLOW_LEVELS = (('soft', 'Soft', 1.0), ('bright', 'Bright', 1.9), ('neon', 'Neon', 3.0))
GLOW_OPENS = 'neon'         # 0.5.2: the owner, having seen the three: "I like neon setting"
GLOW = [3.0]        # the level in force (boss_qt.set_glow keeps it in step with the session)


def glow():
    return GLOW[0]


def lays_light(painter):
    """Kasandra (0.8.3): what is drawn next is light added to what lies under it (Screen), never paint mixed over it. Her
    burnt yellow mixed over her cyan is green (30-50 % of it over #83eaff is 86-156 degrees); added, it brightens cyan
    toward white and warms her indigo. Used for a translucent highlight light and for anything translucent laid over a
    highlight. Graphite: nothing changes (its painter keeps SourceOver). The caller saves and restores the painter."""
    if APPEARANCE == 'kasandra':
        from PySide6.QtGui import QPainter
        painter.setCompositionMode(QPainter.CompositionMode_Screen)
    return painter

TOKENS = {v for k, v in tuple(globals().items()) if isinstance(v, str) and v.startswith('#') and k.isupper()}
LEGACY = {
    '#f6f3eb': GROUND, '#fffdf8': CARD, '#eee9df': RAISED,
    '#dad4c8': LINE, '#7d776d': LINE_MID, '#504d46': TEXT,
    '#6c675e': QUIET, '#f8edc9': AMBER_SOFT, '#d4b56a': AMBER_EDGE,
    '#f3e3af': PENCIL_DEEP, '#f3e3e2': ERASER, '#ecd7d5': ERASER_DEEP,
    '#cba5a4': ERASER_MARK, '#d9d2c4': LINE, '#885e64': TEXT,
}
if APPEARANCE != 'graphite':      # a Graphite colour written into some older sheet becomes its Kasandra counterpart
    for _name, _value in PALETTES['graphite'].items():
        if isinstance(_value, str) and _value.startswith('#') and _value not in TOKENS:LEGACY.setdefault(_value, PALETTES[APPEARANCE][_name])


# Colours some older pages write by hand (settings, cabinet), by the role each one plays (0.8.0). In Graphite nothing is changed.
NEAR = {'#eee9dd': 'TEXT', '#14191b': 'PANEL', '#22292c': 'RAISED', '#394549': 'LINE', '#b0bcb9': 'ERASED_QUIET',
        '#cbf08b': 'TEAL_TEXT', '#493225': 'ERASER', '#593a29': 'ERASER_DEEP', '#ff9a32': 'AMBER_EDGE'}


def recolour(css):
    """A stylesheet written in Graphite's colours, in the colours of the appearance in force: each Graphite colour (and each
    near one in NEAR) becomes the colour of the same role. Unchanged in Graphite."""
    if APPEARANCE == 'graphite' or not isinstance(css, str):return css
    graphite = PALETTES['graphite']
    def one(found):
        c = found.group().lower()
        name = NEAR.get(c) or next((k for k, v in graphite.items() if v == c), None)
        return PALETTES[APPEARANCE][name] if name else found.group()
    return re.sub(r'#[0-9a-fA-F]{6}\b', one, css)


def relight(css):
    """Translate old widget chrome by property, never by inverting a whole sheet.

    A dark background and a pale foreground can coexist in one legacy panel.
    New tokens and explicitly supplied artwork are kept exactly as supplied.
    """
    def declaration(match):
        prop, value = match.group(1), match.group(2)
        def colour(found):
            c = found.group().lower()
            if c in TOKENS:
                return c
            if c in LEGACY:
                return LEGACY[c]
            rgb = [int(c[i:i + 2], 16) for i in (1, 3, 5)]
            if 'background' in prop:
                return GROUND if sum(rgb) < 150 else CARD
            if 'border' in prop or 'gridline' in prop:
                return LINE_MID       # an old outline becomes a quiet edge: no box on the desk is drawn in the pale ink
            if prop.strip() in ('color', 'selection-color', 'placeholder-text-color'):
                return QUIET if max(rgb) - min(rgb) < 32 and 85 < sum(rgb) / 3 < 190 else TEXT
            return c
        return prop + ':' + re.sub(r'#[0-9a-fA-F]{6}\b', colour, value)
    return re.sub(r'([^{};:]+):([^;{}]+)', declaration, css)


CHROME_OVERRIDES = '''
QMenu, QToolTip, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QPlainTextEdit, QTextEdit, QTextBrowser,
QFrame#Card2, QFrame#OneBoxResults, QTabBar::tab {border-radius:0;}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit {border:1px solid %(LINE)s;}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateTimeEdit:focus {border:2px solid %(AMBER_EDGE)s;}
QPlainTextEdit:focus, QTextEdit:focus {border:2px solid %(AMBER_EDGE)s;}
QMainWindow::separator {background:%(LINE_STRONG)s;width:1px;height:1px;}
QMenu {padding:6px 0; border:1px solid %(LINE_MID)s;}
QMenu::item {padding:9px 28px 9px 16px; border-radius:0;}
QMenu::item:selected {color:%(AMBER_TEXT)s; border-left:2px solid %(AMBER_EDGE)s;}
QMenu[glyphs="true"]::item {padding-left:44px;}
QMenu[glyphs="true"]::icon {left:13px;}
QPushButton {border-bottom:1px solid transparent; padding:5px 7px;}
QPushButton:hover, QToolButton:hover {background:%(TEAL_SOFT)s; border-bottom-color:%(READY)s;}
QPushButton:checked, QToolButton:checked, QTabBar::tab:selected {border-bottom:2px solid %(AMBER_EDGE)s;}
QPushButton[arcButton="tool"], QToolButton[arcButton="tool"] {
    color:%(TEXT)s; background:%(RAISED)s; border:1px solid %(LINE)s; border-radius:0; padding:4px 11px; text-align:center;
}
QPushButton[arcButton="tool"]:hover, QToolButton[arcButton="tool"]:hover {background:%(TEAL_SOFT)s; border:1px solid %(TEAL_EDGE)s; color:%(TEAL_TEXT)s;}
QPushButton[arcButton="tool"]:pressed, QToolButton[arcButton="tool"]:pressed {background:%(AMBER_SOFT)s; border:1px solid %(AMBER_EDGE)s;}
QPushButton[arcButton="tool"]:focus, QToolButton[arcButton="tool"]:focus {border:1px solid %(AMBER_EDGE)s;}
QPushButton[arcButton="tool"]:checked, QToolButton[arcButton="tool"]:checked {border:1px solid %(AMBER_EDGE)s; color:%(AMBER_TEXT)s; background:%(AMBER_SOFT)s; font-weight:400;}
QPushButton[arcButton="tool"]:disabled, QToolButton[arcButton="tool"]:disabled {color:%(LINE_MID)s; border:1px solid %(LINE)s; background:transparent;}
QToolButton[arcButton="tool"]::menu-indicator {image:none; width:0;}
QPushButton[arcButton="link"] {text-decoration:underline;}
QTabBar::tab:selected {color:%(AMBER_TEXT)s;}
QTreeView::item, QListView::item {border-radius:0;}
QTreeView::item:selected, QListView::item:selected {border-left:2px solid %(AMBER_EDGE)s;}
QScrollBar::handle {background:%(LINE_MID)s;}
QScrollBar::handle:hover {background:%(TEAL_EDGE)s;}
QLabel[arcRole2="title"], QLabel[arcRole2="section"],
QHeaderView::section {font-family:"%(DISPLAY)s";}
QLabel[arcRole2="hero"] {font-family:"%(DISPLAY)s";}
QLineEdit#WorkspacePath, QLineEdit#WorkspacePath:focus {
    background:transparent; color:%(CUE_TEXT)s; border:0; border-radius:0;
    padding:0; font-family:"%(MONO)s"; selection-background-color:%(AMBER_SOFT)s; selection-color:%(ON_AMBER)s;
}
QToolButton#MoreMenus, QToolButton#HeadMenu, QToolButton#BossPrograms, QToolButton#SystemMenu {
    font-family:"%(DISPLAY)s"; color:%(TEXT)s; background:transparent;
    border:0; border-bottom:2px solid transparent; border-radius:0; padding:5px 10px;
}
QToolButton#MoreMenus:focus, QToolButton#HeadMenu:focus, QToolButton#HeadMenu:pressed, QToolButton#BossPrograms:focus, QToolButton#SystemMenu:focus {
    color:%(AMBER_TEXT)s; border-bottom:2px solid %(AMBER_EDGE)s; background:%(AMBER_SOFT)s;
}
QToolButton#MoreMenus:hover, QToolButton#HeadMenu:hover, QToolButton#BossPrograms:hover, QToolButton#SystemMenu:hover {
    color:%(TEAL_TEXT)s; border-bottom:2px solid %(READY)s; background:%(TEAL_SOFT)s;
}
QToolButton#HeadMenu {padding:5px 0; color:%(QUIET)s;}
QToolButton#HeadMenu::menu-indicator, QToolButton#MoreMenus::menu-indicator {image:none; width:0;}
QLabel#MonitorReading {color:%(QUIET)s; font-family:"%(MONO)s";}
QLabel#MonitorReading[liveReading="true"] {color:%(READY)s;}
QPlainTextEdit#Capture {background:%(CARD)s; border-bottom:1px solid %(LINE)s;}
QPlainTextEdit#Capture:focus {border-bottom:2px solid %(AMBER_EDGE)s;}
QFrame#BossChainTray {background:%(PANEL)s; border-top:1px solid %(CUE_EDGE)s;}
QLineEdit#ChainProgram {font-family:"%(MONO)s"; border:0; border-bottom:1px solid %(LINE)s;}
QTableWidget#ChainPreview {background:%(CARD)s; border:0;}
QLabel#BossArt {background:transparent; border:0;}
QTabWidget#ConsolePages::pane {background:%(GROUND)s; border:0;}
''' % globals()

# 0.8.3, Kasandra's highlights in the sheets (none in Graphite, whose sheet above is what it was): the row you are on in a
# menu (the menus across the head and every menu dropped from them, and the writing line's results) is the solid bar;
# a selected row, a selected tab, a checked choice and selected words are the edge and words on their fill. A menu with a
# sheet of its own takes MENU_BAR_CSS after it.
MENU_BAR_CSS = ('QMenu::item:selected {background:%(BAR)s; color:%(ON_BAR)s; border:0; border-left:2px solid %(BAR_EDGE)s; border-radius:0;} '
                'QMenu::item:selected:disabled {color:%(ON_BAR_QUIET)s;} ' % globals()) if APPEARANCE == 'kasandra' else ''
HIGHLIGHTS = (MENU_BAR_CSS + '''
QListWidget#OneBoxList::item:selected {background:%(BAR)s; color:%(ON_BAR)s; border:0; border-left:2px solid %(BAR_EDGE)s; border-radius:0;}
QTreeView::item:selected, QListView::item:selected {background:%(AMBER_SOFT)s; color:%(AMBER_TEXT)s; border-left:2px solid %(AMBER_EDGE)s;}
QTabBar::tab:selected {background:%(AMBER_SOFT)s; color:%(AMBER_TEXT)s; border-bottom:2px solid %(AMBER_EDGE)s;}
QTreeView, QTreeWidget, QListView, QListWidget, QTableView, QTableWidget, QComboBox QAbstractItemView, QLineEdit, QComboBox,
QSpinBox, QDoubleSpinBox, QDateTimeEdit, QPlainTextEdit, QTextEdit, QTextBrowser {selection-background-color:%(AMBER_SOFT)s; selection-color:%(AMBER_TEXT)s;}
QPushButton[arcButton="filter"]:checked, QPushButton[arcButton="segment"]:checked {color:%(AMBER_TEXT)s; border-bottom:2px solid %(AMBER_EDGE)s;}
''' % globals()) if APPEARANCE == 'kasandra' else ''
CHROME_OVERRIDES += HIGHLIGHTS
