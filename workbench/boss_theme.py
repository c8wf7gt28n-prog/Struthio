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
green ... more green glowing")."""
import json
import os
import re

# Two appearances (0.8.0). Graphite is the desk as it was: warm ink on near-black glass, amber for what is selected and
# what waits for the owner, green for what is live. Kasandra is the owner's second direction (13 November 2026, "I think
# I really like the LAIN/kasandra idea"; the pack's palette.json): ink and pale blue on dark indigo, cyan for focus and
# what is ready, raspberry for a decision that waits for the owner, lavender with a dashed edge for a recheck.
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
        DESK_LIGHT='#8c826b', VEIL='#000000', DISPLAY='IBM Plex Mono'),
    'kasandra': dict(
        GROUND='#171b3c', PANEL='#1b1f45', CARD='#1f234d', RAISED='#292d56', TERMINAL_GROUND='#11132c',
        LINE='#3b4479', LINE_STRONG='#8796cb', LINE_MID='#5969a1', TEXT='#e3e3ff', QUIET='#c1c6e8', FAINT='#9ca3d2',
        AMBER='#1d3d63', AMBER_SOFT='#1d3d63', AMBER_EDGE='#83eaff', AMBER_TEXT='#b9f4ff',
        PENCIL_DEEP='#2b2f63', ERASER='#2e2a5c', ERASER_DEEP='#3b3474', ERASER_MARK='#a9b6ee',
        TEAL='#83eaff', TEAL_SOFT='#1f3560', TEAL_EDGE='#5a8fc4', TEAL_TEXT='#b9f4ff', READY='#83eaff', STOP='#fa507c',
        OWNER='#fa507c', ON_OWNER='#171b3c', RECHECK='#c3b6f4',
        BAND=(20, 23, 52), ERASED='#e3e3ff', ERASED_QUIET='#aeb4dc', BAND_MARK='#83eaff', BAND_PENCIL='#83eaff',
        DESK_LIGHT='#8f97c9', VEIL='#11132c', DISPLAY='Special Elite'),
}


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
QHeaderView::section {font-family:"IBM Plex Mono";}
QLabel[arcRole2="hero"] {font-family:"%(DISPLAY)s";}
QLineEdit#WorkspacePath, QLineEdit#WorkspacePath:focus {
    background:transparent; color:%(AMBER_TEXT)s; border:0; border-radius:0;
    padding:0; font-family:"IBM Plex Mono"; selection-background-color:%(AMBER_SOFT)s; selection-color:%(TEXT)s;
}
QToolButton#MoreMenus, QToolButton#HeadMenu, QToolButton#BossPrograms, QToolButton#SystemMenu {
    font-family:"IBM Plex Mono"; color:%(TEXT)s; background:transparent;
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
QLabel#MonitorReading {color:%(QUIET)s; font-family:"IBM Plex Mono";}
QLabel#MonitorReading[liveReading="true"] {color:%(READY)s;}
QPlainTextEdit#Capture {background:%(CARD)s; border-bottom:1px solid %(LINE)s;}
QPlainTextEdit#Capture:focus {border-bottom:2px solid %(AMBER_EDGE)s;}
QFrame#BossChainTray {background:%(PANEL)s; border-top:1px solid %(AMBER_EDGE)s;}
QLineEdit#ChainProgram {font-family:"IBM Plex Mono"; border:0; border-bottom:1px solid %(LINE)s;}
QTableWidget#ChainPreview {background:%(CARD)s; border:0;}
QLabel#BossArt {background:transparent; border:0;}
QTabWidget#ConsolePages::pane {background:%(GROUND)s; border:0;}
''' % globals()
