"""Ledger & Slate theme, "Paper" v1.1: a quiet place to think.

Warm paper surfaces, a brighter sheet for the work, soft graphite for every label and edge, and two gentle washes:
pencil yellow for the primary action and selection, eraser pink for attention and revisions. No blue, black, red
or green; no dark slabs; no thick outlines. Accents are faces, never the only cue: states also carry a word or a mark.

Sizes here are padding and radii (8 for controls, 10 for panels and cards, 12 for dialogs). The shell's design scale
chooses text sizes. Older panels that still carry their own colors are re-lit to paper by `relight`.
"""
import re
from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget
from .shell2 import (AMBER, AMBER_EDGE, AMBER_SOFT, CARD, ERASER, ERASER_DEEP, ERASER_MARK, GROUND, LINE, LINE_STRONG, PANEL, PENCIL_DEEP, QUIET, RAISED,
                     TEAL_EDGE, TEAL_SOFT, TEAL_TEXT, TEXT)

PALETTE = (('Window', GROUND), ('Base', CARD), ('AlternateBase', GROUND), ('Button', CARD), ('WindowText', TEXT), ('Text', TEXT),
           ('ButtonText', TEXT), ('BrightText', TEXT), ('Light', CARD), ('Midlight', LINE), ('Dark', LINE_STRONG), ('Mid', LINE),
           ('Shadow', LINE), ('Highlight', AMBER_SOFT), ('HighlightedText', TEXT), ('PlaceholderText', QUIET), ('ToolTipBase', CARD),
           ('ToolTipText', TEXT), ('Link', TEXT), ('LinkVisited', TEXT))

QSS2 = r"""
QMainWindow, QDialog { background: %(GROUND)s; }
QWidget { color: %(TEXT)s; }
QToolTip { background: %(CARD)s; color: %(TEXT)s; border: 1px solid %(LINE_STRONG)s; padding: 6px 10px; border-radius: 8px; }

QMenuBar { background: %(GROUND)s; border: 0; }
QMenu { background: %(CARD)s; border: 1px solid %(LINE)s; padding: 6px; border-radius: 10px; }
QMenu::item { padding: 8px 28px 8px 14px; border-radius: 8px; }
QMenu::item:selected { background: %(AMBER_SOFT)s; color: %(TEXT)s; }
QMenu::item:disabled { color: %(QUIET)s; }
QMenu::separator { height: 1px; background: %(LINE)s; margin: 6px 10px; }

QPushButton { background: transparent; color: %(TEXT)s; border: 0; border-bottom: 3px solid %(ERASER_MARK)s; border-radius: 0; padding: 4px 2px; text-align: left; }
QPushButton:hover { background: %(AMBER_SOFT)s; border-bottom: 3px solid %(AMBER_EDGE)s; }
QPushButton:pressed { background: %(ERASER)s; border-bottom: 3px solid %(ERASER_MARK)s; }
QPushButton:disabled { color: %(LINE_STRONG)s; border-bottom-color: transparent; }
QPushButton:checked { border-bottom: 3px solid %(TEXT)s; font-weight: 600; }
QPushButton:focus { border-bottom: 3px solid %(TEXT)s; }
QPushButton[arcButton="primary"] { font-weight: 600; }
QPushButton[arcButton="primary"]:hover { background: %(AMBER_SOFT)s; }
QPushButton[arcButton="primary"]:focus { border-bottom: 3px solid %(TEXT)s; }
QPushButton[arcButton="warm"]:hover { border-bottom: 3px solid %(ERASER_MARK)s; background: %(ERASER)s; }
QPushButton[arcButton="stac"] { font-family: "IBM Plex Mono", monospace; }
QPushButton[arcButton="link"] { padding: 3px 0; }
QPushButton[arcButton="link"]:hover { background: %(AMBER_SOFT)s; }
QPushButton[arcButton="filter"] { padding: 8px 4px; margin-right: 10px; color: %(QUIET)s; border-bottom: 2px solid transparent; }
QPushButton[arcButton="filter"]:hover { color: %(TEXT)s; }
QPushButton[arcButton="filter"]:checked { color: %(TEXT)s; background: %(AMBER_SOFT)s; border-bottom: 2px solid %(TEXT)s; }
QPushButton[arcButton="segment"] { background: transparent; border: 0; border-bottom: 2px solid transparent; border-radius: 0; padding: 9px 2px; color: %(QUIET)s; }
QPushButton[arcButton="segment"]:checked { color: %(TEXT)s; border-bottom: 2px solid %(TEXT)s; background: transparent; font-weight: 600; }

QToolButton { background: transparent; border: 0; border-bottom: 2px solid transparent; border-radius: 0; padding: 4px 4px; color: %(TEXT)s; }
QToolButton:hover { border-bottom: 2px solid %(AMBER_EDGE)s; }
QToolButton:checked { border-bottom: 2px solid %(TEXT)s; }
QToolButton:focus { border-bottom: 2px solid %(TEXT)s; }
QToolButton::menu-indicator { width: 0; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateTimeEdit { background: %(CARD)s; border: 1px solid %(LINE_STRONG)s; border-radius: 8px; padding: 7px 12px;
    selection-background-color: %(AMBER_SOFT)s; selection-color: %(TEXT)s; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 2px solid %(TEXT)s; padding: 6px 11px; }
QComboBox::drop-down { border: 0; width: 24px; }
QComboBox QAbstractItemView { background: %(CARD)s; border: 1px solid %(LINE)s; selection-background-color: %(AMBER_SOFT)s; selection-color: %(TEXT)s; }

QPlainTextEdit, QTextEdit, QTextBrowser { background: %(CARD)s; border: 1px solid %(LINE)s; border-radius: 10px;
    selection-background-color: %(AMBER_SOFT)s; selection-color: %(TEXT)s; }
QPlainTextEdit:focus, QTextEdit:focus { border: 2px solid %(TEXT)s; }

QTreeView, QTreeWidget, QListView, QListWidget, QTableView, QTableWidget { background: %(GROUND)s; border: 0; border-radius: 0;
    alternate-background-color: %(CARD)s; outline: 0; selection-background-color: %(AMBER_SOFT)s; selection-color: %(TEXT)s; }
QTreeView::item, QListView::item { padding: 6px 8px; border-radius: 8px; border-left: 2px solid transparent; }
QTreeView::item:hover, QListView::item:hover { background: %(RAISED)s; }
QTreeView::item:selected, QListView::item:selected { background: %(AMBER_SOFT)s; color: %(TEXT)s; }
QListView::item:selected, QTreeWidget#hardwareTree::item:selected { border-left: 2px solid %(TEXT)s; }
QHeaderView::section { background: %(GROUND)s; color: %(QUIET)s; border: 0; border-bottom: 1px solid %(LINE)s; padding: 8px 10px; }
QTableView { gridline-color: %(LINE)s; }

QTabWidget::pane { border: 0; border-top: 1px solid %(LINE)s; background: %(GROUND)s; }
QTabBar::tab { background: transparent; color: %(QUIET)s; min-height: 24px; padding: 8px 6px; margin-right: 18px; border: 0; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: %(TEXT)s; border-bottom: 2px solid %(TEXT)s; background: %(AMBER_SOFT)s; border-top-left-radius: 8px; border-top-right-radius: 8px; }
QTabBar::tab:hover:!selected { color: %(TEXT)s; background: %(RAISED)s; border-top-left-radius: 8px; border-top-right-radius: 8px; }

QScrollBar:vertical { background: %(GROUND)s; width: 10px; margin: 2px; }
QScrollBar:horizontal { background: %(GROUND)s; height: 10px; margin: 2px; }
QScrollBar::handle { background: %(ERASER_MARK)s; border-radius: 4px; min-height: 32px; min-width: 32px; }
QScrollBar::handle:hover, QScrollBar::handle:pressed { background: %(ERASER_MARK)s; border: 1px solid %(LINE_STRONG)s; }
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page { width: 0; height: 0; background: none; }

QCheckBox, QRadioButton { spacing: 8px; }
QCheckBox::indicator, QRadioButton::indicator { width: 16px; height: 16px; border: 1px solid %(LINE_STRONG)s; background: %(CARD)s; }
QCheckBox::indicator { border-radius: 4px; } QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked { background: %(AMBER)s; border: 2px solid %(TEXT)s; }
QProgressBar { background: %(RAISED)s; border: 1px solid %(LINE)s; border-radius: 4px; text-align: center; color: %(TEXT)s; max-height: 8px; }
QProgressBar::chunk { background: %(AMBER_EDGE)s; border-radius: 3px; }
QSplitter::handle { background: %(LINE)s; }
QMainWindow::separator { background: %(LINE)s; width: 1px; height: 1px; }
QDockWidget::title { background: %(GROUND)s; padding: 8px 12px; color: %(QUIET)s; }
QStatusBar { background: %(GROUND)s; border-top: 1px solid %(LINE)s; color: %(QUIET)s; }
QStatusBar::item { border: 0; }
QGroupBox { border: 0; border-top: 1px solid %(LINE)s; margin-top: 18px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 0; color: %(QUIET)s; }

QWidget#TopBar2 { background: %(GROUND)s; border-bottom: 1px solid %(LINE)s; }
QLineEdit#OneBox { background: %(RAISED)s; border: 1px solid %(LINE)s; border-radius: 8px; padding: 8px 14px; color: %(TEXT)s; }
QLineEdit#OneBox:focus { background: %(CARD)s; border: 2px solid %(TEXT)s; padding: 7px 13px; }
QFrame#OneBoxResults { background: %(CARD)s; border: 1px solid %(LINE_STRONG)s; border-radius: 12px; }
QListWidget#OneBoxList { background: transparent; border: 0; }
QListWidget#OneBoxList::item { padding: 9px 12px; border-radius: 8px; }
QListWidget#OneBoxList::item:selected { background: %(AMBER_SOFT)s; border-left: 2px solid %(TEXT)s; }
QToolButton#WorkspaceSwitch { background: transparent; border: 1px solid transparent; padding: 6px 8px; color: %(TEXT)s; }
QToolButton#WorkspaceSwitch:hover { background: %(RAISED)s; }
QPushButton#RunningChip { background: transparent; border: 0; color: %(QUIET)s; }
QPushButton#BrainChip { background: transparent; border: 1px solid transparent; color: %(TEXT)s; padding: 6px 8px; }
QPushButton#BrainChip:hover { background: %(RAISED)s; }
QWidget#FaceSwitch { background: transparent; }
QFrame#Card2 { background: %(CARD)s; border: 1px solid %(LINE)s; border-radius: 10px; }
QFrame#TodaySide { background: %(GROUND)s; border: 0; }
QWidget#TodayPage, QWidget#LibraryTab, QWidget#ItemView, QWidget#SlateFace { background: %(GROUND)s; }
QLabel#KindChip { background: %(CARD)s; color: %(TEXT)s; border: 1px solid %(LINE_STRONG)s; border-radius: 8px; padding: 3px 10px; }
QPushButton#AddressChip { background: %(TEAL_SOFT)s; color: %(TEAL_TEXT)s; border: 1px solid %(LINE)s; border-radius: 8px; padding: 4px 10px;
    font-family: "IBM Plex Mono", "DejaVu Sans Mono", monospace; }
QPushButton#AddressChip:hover { background: %(AMBER_SOFT)s; }
QFrame#SlateMine { background: %(AMBER_SOFT)s; border: 1px solid %(LINE)s; border-radius: 10px; }
QFrame#SlateTheirs { background: %(CARD)s; border: 1px solid %(LINE)s; border-radius: 10px; }
QFrame#StacCard { background: %(TEAL_SOFT)s; border: 1px solid %(LINE)s; border-radius: 10px; }
/* Writable passages (companion line 65/69, DESKTOP-01 V-02): the New Idea sheet, the Slate composer and the New Project title are
   yellow passages like the cabinet's writing, not bordered boxes. Focus is a bottom rule; the selection is eraser pink because
   AMBER_SOFT equals AMBER and would be invisible on the passage. */
QLineEdit#SlateInput, QPlainTextEdit#SlateInput, QPlainTextEdit#Capture, QLineEdit#ProjectTitle { background: %(AMBER)s; color: %(TEXT)s; border: 0; border-radius: 0;
    padding: 10px 14px; selection-background-color: %(ERASER_DEEP)s; selection-color: %(TEXT)s; }
QLineEdit#SlateInput:focus, QPlainTextEdit#SlateInput:focus, QPlainTextEdit#Capture:focus, QLineEdit#ProjectTitle:focus { border: 0; border-bottom: 2px solid %(TEXT)s;
    padding: 10px 14px 8px 14px; }
""" % dict(GROUND=GROUND, PANEL=PANEL, CARD=CARD, RAISED=RAISED, LINE=LINE, LINE_STRONG=LINE_STRONG, TEXT=TEXT, QUIET=QUIET,
           AMBER=AMBER, AMBER_SOFT=AMBER_SOFT, AMBER_EDGE=AMBER_EDGE, PENCIL_DEEP=PENCIL_DEEP, ERASER=ERASER, ERASER_DEEP=ERASER_DEEP, ERASER_MARK=ERASER_MARK,
           TEAL_SOFT=TEAL_SOFT, TEAL_EDGE=TEAL_EDGE, TEAL_TEXT=TEAL_TEXT)


HEX = re.compile(r'#([0-9a-fA-F]{6})\b')
DARK_BACKGROUND = re.compile(r'(?:background(?:-color)?)\s*:\s*#([0-9a-fA-F]{6})')
LIGHT_TEXT = re.compile(r'(?<![-\w])color\s*:\s*#([0-9a-fA-F]{6})')
TOKENS = {c.lower() for c in (GROUND, CARD, RAISED, LINE, LINE_STRONG, TEXT, QUIET, AMBER, AMBER_SOFT, AMBER_EDGE, PENCIL_DEEP, ERASER, ERASER_DEEP)}


def lightness(hex6):return QColor('#' + hex6).lightnessF()


def paper(color):
    """One color moved into the Paper family: saturated hues become graphite (if read) or a pencil wash (if a face);
    neutrals keep their lightness with a warm, nearly grey tint."""
    h, s, l, a = color.getHslF()
    if s > 0.3 and 0.12 < l < 0.9:return TEXT if l < 0.72 else AMBER_SOFT
    return QColor.fromHslF(0.11, min(s, 0.12), max(0.0, min(1.0, l)), a).name()


def flip(match):
    """A dark-theme color at the opposite lightness, then moved into the Paper family."""
    if '#' + match.group(1).lower() in TOKENS:return '#' + match.group(1)
    color = QColor('#' + match.group(1));h, s, l, a = color.getHslF()
    light = 1.0 - l
    if light > 0.9:light = 0.955 + (light - 0.9) * 0.3   # the darkest panels become warm paper, not glare
    if s > 0.3 and 0.25 < l < 0.85:return TEXT            # an old accent read as text becomes graphite
    if light < 0.32:return TEXT                           # pale text from a dark panel becomes graphite, never black
    return paper(QColor.fromHslF(h if h >= 0 else 0.0, s, max(0.0, min(1.0, light)), a))


def soften(match):
    """A light-theme color kept at its lightness, but never blue, red, green or orange."""
    value = '#' + match.group(1)
    return value if value.lower() in TOKENS else paper(QColor(value))


def dark_sheet(css):
    """True for a stylesheet written for the old dark theme: a dark background, or pale text meant to sit on one."""
    return any(lightness(m) < 0.3 for m in DARK_BACKGROUND.findall(css)) or any(lightness(m) > 0.62 for m in LIGHT_TEXT.findall(css))


def relight(css):
    from .boss_theme import relight as boss_relight
    return boss_relight(css)


def holding_layout(layout, widget):
    """The (sub)layout that holds widget directly."""
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget() is widget:return layout
        if item.layout() is not None:
            found = holding_layout(item.layout(), widget)
            if found is not None:return found
    return None


def as_words(button):
    """4.1: a button is a word. A row made only of buttons sits to the left at its natural width instead of spreading boxes across the panel."""
    from PySide6.QtWidgets import QBoxLayout, QPushButton, QSizePolicy, QSpacerItem
    from PySide6.QtCore import Qt
    if button.property('arcButton') in ('filter', 'segment') or button.property('paperWords'):return
    button.setProperty('paperWords', True)
    if button.cursor().shape() == Qt.ArrowCursor:button.setCursor(Qt.PointingHandCursor)
    parent = button.parentWidget()
    row = holding_layout(parent.layout(), button) if parent is not None and parent.layout() is not None else None
    if not isinstance(row, QBoxLayout) or row.direction() not in (QBoxLayout.LeftToRight, QBoxLayout.RightToLeft) or row is parent.layout():return
    items = [row.itemAt(i) for i in range(row.count())]
    if not items or not all(isinstance(it.widget(), QPushButton) or isinstance(it, QSpacerItem) or it.spacerItem() is not None for it in items):return
    for it in items:
        w = it.widget()
        if w is not None:w.setSizePolicy(QSizePolicy.Maximum, w.sizePolicy().verticalPolicy())
    row.setSpacing(max(row.spacing(), 18));row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)


class Relight(QObject):
    """Re-lights any widget whose own stylesheet was written for another palette, whenever it is set."""

    def eventFilter(self, obj, event):
        # A window's own sheet is the theme itself; rewriting it mid-polish would cut the font cascade to its children.
        if event.type() == QEvent.Show and type(obj).__name__ == 'QPushButton':as_words(obj)
        # Companion surfaces declare their functional ink explicitly. Keep the
        # legacy palette conversion for older panels without recoloring actions.
        if (event.type() == QEvent.Polish and isinstance(obj, QWidget) and not obj.isWindow()
                and not obj.property('paperFunctionalInk')):
            css = obj.styleSheet()
            if css and css != obj.property('paperSheet'):
                lit = relight(css)
                obj.setProperty('paperSheet', lit)
                if lit != css:
                    from PySide6.QtCore import QTimer
                    from shiboken6 import isValid
                    # After this polish, and only if the widget still has the sheet that was relit: a newer sheet set meanwhile
                    # (the shell restyling Stop, for example) must never be overwritten by a stale one.
                    QTimer.singleShot(0, lambda w=obj, old=css, s=lit:isValid(w) and w.styleSheet() == old and w.setStyleSheet(s))
        return False


def install(app):
    if getattr(app, '_paper_relight', None) is None:
        app._paper_relight = Relight(app);app.installEventFilter(app._paper_relight)

# The BOSS theme uses the same controls and reading scale.
from .boss_theme import CHROME_OVERRIDES
QSS2 += CHROME_OVERRIDES
