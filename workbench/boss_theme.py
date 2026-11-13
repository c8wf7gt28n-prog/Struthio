"""BOSS desk colours. Presentation only; document formats keep their own ink.

Amber is for what is selected, what has the keyboard, and what waits for the owner. Green is for what is live: readings,
what is current, staC, the pointer, and whatever the pointer is over (13 November 2026: "the mouse pointer to be the systems
green ... more green glowing")."""
import re

GROUND, PANEL, CARD, RAISED = '#0b0e0d', '#111513', '#151a17', '#202520'
TERMINAL_GROUND = '#080a09'
LINE, LINE_STRONG = '#474436', '#bcac8e'
TEXT, QUIET, FAINT = '#f4e8ce', '#c8baa0', '#a89b84'
AMBER, AMBER_SOFT, AMBER_EDGE, AMBER_TEXT = '#4b2a14', '#4b2a14', '#ff9a36', '#ffba72'
PENCIL_DEEP, ERASER, ERASER_DEEP, ERASER_MARK = '#443527', '#493225', '#593a29', '#dd854b'
TEAL, TEAL_SOFT, TEAL_EDGE, TEAL_TEXT = '#c3ed74', '#1b2817', '#789654', '#cbf08b'
READY, STOP = '#c3ed74', '#ff9a36'

TOKENS = {v for k, v in tuple(globals().items()) if isinstance(v, str) and v.startswith('#')}
LEGACY = {
    '#f6f3eb': GROUND, '#fffdf8': CARD, '#eee9df': RAISED,
    '#dad4c8': LINE, '#7d776d': LINE_STRONG, '#504d46': TEXT,
    '#6c675e': QUIET, '#f8edc9': AMBER_SOFT, '#d4b56a': AMBER_EDGE,
    '#f3e3af': PENCIL_DEEP, '#f3e3e2': ERASER, '#ecd7d5': ERASER_DEEP,
    '#cba5a4': ERASER_MARK, '#d9d2c4': LINE, '#885e64': TEXT,
}


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
                return LINE_STRONG
            if prop.strip() in ('color', 'selection-color', 'placeholder-text-color'):
                return QUIET if max(rgb) - min(rgb) < 32 and 85 < sum(rgb) / 3 < 190 else TEXT
            return c
        return prop + ':' + re.sub(r'#[0-9a-fA-F]{6}\b', colour, value)
    return re.sub(r'([^{};:]+):([^;{}]+)', declaration, css)


CHROME_OVERRIDES = '''
QMenu, QToolTip, QLineEdit, QComboBox, QPlainTextEdit, QTextEdit, QTextBrowser,
QFrame#Card2, QFrame#OneBoxResults, QTabBar::tab {border-radius:0;}
QMainWindow::separator {background:%(LINE_STRONG)s;width:1px;height:1px;}
QMenu {padding:6px 0; border:1px solid %(LINE_STRONG)s;}
QMenu::item {padding:9px 28px 9px 16px; border-radius:0;}
QMenu::item:selected {color:%(AMBER_TEXT)s; border-left:2px solid %(AMBER_EDGE)s;}
QPushButton {border-bottom:1px solid transparent; padding:5px 7px;}
QPushButton:hover, QToolButton:hover {background:%(TEAL_SOFT)s; border-bottom-color:%(READY)s;}
QPushButton:checked, QToolButton:checked, QTabBar::tab:selected {border-bottom:2px solid %(AMBER_EDGE)s;}
QTabBar::tab:selected {color:%(AMBER_TEXT)s;}
QTreeView::item, QListView::item {border-radius:0;}
QTreeView::item:selected, QListView::item:selected {border-left:2px solid %(AMBER_EDGE)s;}
QScrollBar::handle {background:%(LINE_STRONG)s;}
QScrollBar::handle:hover {background:%(TEAL_EDGE)s;}
QLabel[arcRole2="title"], QLabel[arcRole2="hero"], QLabel[arcRole2="section"],
QHeaderView::section {font-family:"IBM Plex Mono";}
QLineEdit#WorkspacePath, QLineEdit#WorkspacePath:focus {
    background:transparent; color:%(AMBER_TEXT)s; border:0; border-radius:0;
    padding:0; font-family:"IBM Plex Mono"; selection-background-color:%(AMBER_SOFT)s; selection-color:%(TEXT)s;
}
QToolButton#MoreMenus, QToolButton#BossPrograms, QToolButton#SystemMenu {
    font-family:"IBM Plex Mono"; color:%(TEXT)s; background:transparent;
    border:0; border-bottom:2px solid transparent; border-radius:0; padding:5px 10px;
}
QToolButton#MoreMenus:focus, QToolButton#BossPrograms:focus, QToolButton#SystemMenu:focus {
    color:%(AMBER_TEXT)s; border-bottom:2px solid %(AMBER_EDGE)s; background:%(AMBER_SOFT)s;
}
QToolButton#MoreMenus:hover, QToolButton#BossPrograms:hover, QToolButton#SystemMenu:hover {
    color:%(TEAL_TEXT)s; border-bottom:2px solid %(READY)s; background:%(TEAL_SOFT)s;
}
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
