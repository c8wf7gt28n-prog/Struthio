"""Ledger & Slate 2: the window built around what the program is now. Arrive → Read → Ask → Keep.

  Top bar    the workspace, the one box (ask Slate, run staC, find files and commands), the brain, running work, Master Stop
  Library    Today · Arrive (Ingress, Deliveries) · Library by kind · Keep · Slate · Projects, above the Concern catalog
  Desk       open items as tabs; every item has the same header
  Context    details of what is open, or Slate: the conversation about it, with proposals you run
  Timeline   what happened in plain words

It is a presentation layer over the existing window: every service, action, tab and dock is kept and reused.
"""
from __future__ import annotations
from .assistant_identity import named
from .text_prompts import writing_prompt
import json
import re
from pathlib import Path
from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QToolButton, QTreeWidgetItem, QVBoxLayout, QWidget

# BOSS presentation; public names remain for existing room imports.
from . import boss_theme as bt
from .boss_theme import (GROUND, PANEL, CARD, RAISED, LINE, LINE_STRONG, TEXT, QUIET, FAINT,
    AMBER, AMBER_SOFT, AMBER_EDGE, AMBER_TEXT, PENCIL_DEEP, ERASER, ERASER_DEEP, ERASER_MARK,
    TEAL, TEAL_SOFT, TEAL_EDGE, TEAL_TEXT, READY, STOP)
SANS, MONO = bt.PALETTES[bt.APPEARANCE]['FACE'] if hasattr(bt, 'PALETTES') else 'IBM Plex Sans', 'IBM Plex Mono'      # SANS: the window's words (boss_theme.FACE)
PLEX_SANS = 'IBM Plex Sans'
PLEX = ('IBMPlexSans-Regular.ttf', 'IBMPlexSans-Medium.ttf', 'IBMPlexSans-SemiBold.ttf', 'IBMPlexMono-Regular.ttf', 'IBMPlexMono-Medium.ttf')
from .stac_bridge import route_program

# Library kinds: what a file is, by its name. The universal viewer decides by contents when it opens.
KINDS = (('documents', 'Documents', ('.pdf', '.docx', '.doc', '.odt', '.rtf', '.txt', '.md', '.markdown', '.pptx', '.xlsx', '.ods', '.csv', '.tsv', '.html', '.htm')),
         ('code', 'Code', ('.c', '.h', '.cpp', '.hpp', '.cc', '.py', '.js', '.ts', '.rs', '.go', '.java', '.cs', '.sh', '.v', '.sv', '.vhd', '.s', '.asm', '.ld', '.json', '.yaml', '.yml', '.toml', '.ini', '.xml', '.sql', '.lua')),
         ('boards', 'Boards & CAD', ('.gbr', '.ger', '.gtl', '.gbl', '.gto', '.gbo', '.gts', '.gbs', '.gko', '.gm1', '.drl', '.xln', '.kicad_pcb', '.kicad_sch', '.step', '.stp', '.stl')),
         ('images', 'Images', ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg')),
         ('containers', 'Archives & disk images', ('.zip', '.tar', '.gz', '.tgz', '.bz2', '.xz', '.7z', '.rar', '.img', '.iso', '.bin', '.dd', '.raw', '.elf', '.sqlite', '.db')))


def kind_of(name):
    lower = name.lower()
    for key, _, suffixes in KINDS:
        if lower.endswith(suffixes):return key
    return 'other'


SCRIPT = 'Parisienne'


def load_fonts(root):
    """Register the bundled Plex fonts, and the one script, once. Missing files fall back to the system fonts."""
    from . import locations
    folder = locations.program(root) / 'branding' / 'fonts' / 'plex'
    for name in PLEX:
        path = folder / name
        if path.is_file():QFontDatabase.addApplicationFont(str(path))
    script = locations.program(root) / 'branding' / 'fonts' / 'script' / 'Parisienne-Regular.ttf'
    if script.is_file():QFontDatabase.addApplicationFont(str(script))
    typewriter = locations.program(root) / 'branding' / 'fonts' / 'typewriter' / 'SpecialElite-Regular.ttf'
    if typewriter.is_file():QFontDatabase.addApplicationFont(str(typewriter))      # Kasandra's headings (boss_theme.DISPLAY)
    return PLEX_SANS in QFontDatabase.families()


SCRIPT_ON = [False]  # the owner's choice, for words drawn without a window at hand (card notes)


def cursive_on(host):
    # Preserve the stored paper-theme preference; BOSS uses readable terminal lettering.
    SCRIPT_ON[0] = False
    return False


def script_room(text, px):
    """(left, right, bottom): how far the Paper script's ink reaches past its words' advance at px (D1-fix: Parisienne's G, S, E
    and i reach left of their origin, a last letter's swash right of its advance, a descender below the line's descent),
    word by word (any word may start or end a wrapped line), each with a pixel of air: the room a label keeps round the
    script so its own edges cut none of it. Keys and numbers in the words are printed (quiet_html) and need none."""
    import math
    from PySide6.QtGui import QFontMetricsF
    font = QFont(SCRIPT);font.setPixelSize(int(px));fm = QFontMetricsF(font);left = right = bottom = 0.0
    for word in str(text).split():
        if KEYS_AND_NUMBERS.fullmatch(word.strip('.,;:·()')):continue
        r = fm.tightBoundingRect(word);left = max(left, -r.left());right = max(right, r.right() - fm.horizontalAdvance(word))
        bottom = max(bottom, r.bottom() - fm.descent())
    return tuple(math.ceil(max(0.0, v)) + 1 for v in (left, right, bottom))


def quiet_script(label, pixels=15):
    """The rule for script: print is for what you read first and act on; script is for the quieter words around it
    (the corner note of a card, a greeting, a signature) and for a little grace. Numbers stay printed, so a count
    is read at a glance. D1-fix: the label keeps room round the script's swashes (script_room), so none is cut."""
    text = label.text()
    if SCRIPT_ON[0] and SCRIPT in QFontDatabase.families() and text and not any(c.isdigit() for c in text):
        size = round(pixels * 1.3);left, right, bottom = script_room(text, size)
        label.setStyleSheet('QLabel {font-family:"%s";font-size:%dpx;color:%s;font-weight:400;padding:0 %dpx %dpx %dpx;}' % (SCRIPT, size, QUIET, right, bottom, left))
        label.setIndent(0)  # with a padding Qt would add its own indent (half an x) to the room: the room is exactly the swash's
    else:label.setStyleSheet('QLabel {color:%s;}' % QUIET)
    label.setProperty('quiet_script', True)


class QuietNote(QLabel):
    def setText(self, text):
        super().setText(text);quiet_script(self)


def _script_ready():
    return SCRIPT_ON[0] and SCRIPT in QFontDatabase.families()


def script_span(text, px, colour=None):
    """Words in the Paper script as rich text, at px (already the script's size), quiet graphite unless colour is given."""
    import html
    return '<span style="font-family:\'%s\';font-size:%dpx;font-weight:400;color:%s;">%s</span>' % (
        SCRIPT, px, colour or QUIET, html.escape(text).replace('\n', '<br>'))


class QuietWords(QLabel):
    """One label whose words are, by turns, a status, a value or a result (setText: print, as before) or an explanation you
    may skip (explain: the Paper script by the quiet-script rule). The desk's panes use it (HATCH DESK D1b; the owner,
    2026-11-06: "Don't we like cursive font for 'less necessary to read' text"). explain(note, lead) keeps a printed lead
    (a heading, a status) in print and sets only the note in script, after it on the same line (sep ' · ') or under it
    (sep '\\n'). Numbers stay printed: a note with a digit is print. View ▸ Pleasantries in script off makes it all print.
    The print size is the window's own (base None) or base px at 14 pt; the script is 1.3 times the print size, and never
    under quiet_script's 1.3 times 15 px (the script's x-height is small), both following the interface size. The words as
    plain text are `words()`."""

    def __init__(self, host, text='', base=None, wrap=True):
        super().__init__();self.host = host;self.base = base;self.note = None;self.lead = '';self.sep = '\n';self._css = None
        self.setTextFormat(Qt.PlainText);self.setWordWrap(wrap);self.setMinimumWidth(0);self.setProperty('quiet_words', True)
        if text:self.setText(text)

    def setText(self, text):
        self.note = None;self.lead = '';self.setTextFormat(Qt.PlainText);super().setText(text);self.restyle()

    def explain(self, note, lead='', sep='\n'):
        self.note = str(note);self.lead = str(lead or '');self.sep = sep;self.restyle()  # the words are set only when they change

    def scripted(self):
        """True when the note is drawn in the script now."""
        return bool(self.note) and _script_ready() and not any(c.isdigit() for c in self.note)

    def words(self):
        return (self.lead + self.sep + self.note) if self.note is not None and self.lead else (self.note if self.note is not None else self.text())

    def print_px(self):
        s = scale_of(self.host)
        if self.base is not None:return max(10, round(self.base * s))
        return max(10, round(16 * s))  # chrome_css: controls and rows are 16 px at 14 pt

    def script_px(self):
        return round(max(self.print_px(), 15 * scale_of(self.host)) * 1.3)

    def overhang(self, px):
        """(left, right, bottom): the room the note's script needs round it (script_room)."""
        return script_room(self.note, px)

    def restyle(self, force=False):
        px = self.print_px();css = 'QLabel {font-size:%dpx;}' % px if self.base is not None else ''
        if css != self._css:self._css = css;self.setStyleSheet(css)
        if self.note is None:return
        if self.scripted():
            import html
            size = self.script_px();left, right, bottom = self.overhang(size)
            script = quiet_html(self.note, size, px)  # the keys to press in it stay print (Ctrl+Enter), the words are the script
            # The script's ink is kept inside the label: its block is inset by the overhang (a hanging indent when a printed lead
            # starts the same line, so the lead stays on the column's edge and only the script's wrapped lines are inset).
            margins = 'margin-top:0;margin-bottom:%dpx;margin-left:%dpx;margin-right:%dpx;' % (bottom, left, right)
            lead = html.escape(self.lead).replace('\n', '<br>') if self.lead else ''
            if lead and self.sep == "\n":text = '<p style="margin-top:0;margin-bottom:0;margin-left:0;margin-right:0;">%s</p><p style="%s">%s</p>' % (lead, margins, script)
            elif lead:text = '<p style="%stext-indent:-%dpx;">%s%s%s</p>' % (margins, left, lead, html.escape(self.sep), script)
            elif KEYS_AND_NUMBERS.match(self.note):text = '<p style="%stext-indent:-%dpx;">%s</p>' % (margins, left, script)  # a printed key starts it
            else:text = '<p style="%s">%s</p>' % (margins, script)
            if force or self.textFormat() != Qt.RichText or super().text() != text:self.setTextFormat(Qt.RichText);QLabel.setText(self, text)
        else:
            text = self.words()
            if force or self.textFormat() != Qt.PlainText or super().text() != text:self.setTextFormat(Qt.PlainText);QLabel.setText(self, text)


class Note(str):
    """A Context row's words that are a note you may skip (rooms' inspector sections): arc_desktop draws them in the script,
    the keys and numbers in them printed (quiet_html)."""


KEYS_AND_NUMBERS = re.compile(r'(?:(?:Ctrl|Alt|Shift|Meta|Super)\+)+[A-Za-z0-9]+|\d[\d.,:]*')


def quiet_html(text, px, print_px):
    """A note in the Paper script as rich text, with the keys to press and the numbers in it printed (what you act on and
    read at a glance stays print). Plain escaped text when the script is off or missing."""
    import html
    if not _script_ready():return html.escape(text).replace('\n', '<br>')
    out = [];at = 0
    for m in KEYS_AND_NUMBERS.finditer(text):
        if m.start() > at:out.append(script_span(text[at:m.start()], px))
        out.append('<span style="font-size:%dpx;">%s</span>' % (print_px, html.escape(m.group(0))));at = m.end()
    if at < len(text):out.append(script_span(text[at:], px))
    return ''.join(out)


class Wordmark(QLabel):
    """The word Graphite alone at the upper left of the head band (the owner, 2026-11-06: "upper left Graphite should be
    cursive"): the Paper script in the bands' erased paper, as if rubbed out of the shading, with a hairline of the same paper
    round its outline so the thin strokes hold on the grain; Plex SemiBold when View ▸ Pleasantries in script is off or the
    face is missing. It is drawn by its outline (QPainterPath), so the widget is the word's ink: the script's G reaches left of
    its origin and its descenders fall below the line, so the ink's left edge is put on the widget's left edge (the band's
    inset) and the ink is centred in the band's height, on the symbol's centre line; the pair measured on the boxes is the
    pair seen. Still a QLabel named GraphiteWord whose text is Graphite, for callers and checks."""

    def __init__(self, parent=None):
        super().__init__('Graphite', parent);self.setObjectName('GraphiteWord');self.setTextFormat(Qt.PlainText)
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter);self.setAccessibleName('Graphite');self.setProperty('paperFunctionalInk', True)
        self.script = False;self.stroke = 0.0;self._path = None

    def set_face(self, script, stroke):
        self.script = bool(script);self.stroke = float(stroke);self._path = None;self.updateGeometry();self.update()

    def outline(self):
        from PySide6.QtGui import QPainterPath
        key = (self.font().key(), self.text())
        if self._path is None or self._path[0] != key:
            path = QPainterPath();path.addText(0, 0, self.font(), self.text());self._path = (key, path)
        return self._path[1]

    def changeEvent(self, event):
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):self._path = None;self.updateGeometry()
        super().changeEvent(event)

    def ink_size(self):
        b = self.outline().boundingRect();return b.width() + self.stroke, b.height() + self.stroke

    def ink_rect(self):
        """The word's ink in the widget's coordinates: its left edge on the widget's, centred in the widget's height."""
        from PySide6.QtCore import QRectF
        w, h = self.ink_size();return QRectF(0.0, (self.height() - h) / 2.0, w, h)

    def sizeHint(self):
        import math
        w, h = self.ink_size()
        return QSize(math.ceil(max(w, self.fontMetrics().horizontalAdvance(self.text()))), math.ceil(max(h, self.fontMetrics().height())))

    def minimumSizeHint(self):return self.sizeHint()

    def paintEvent(self, event):
        from .desk_qt import ERASED
        path = self.outline();b = path.boundingRect();ink = self.ink_rect();half = self.stroke / 2.0
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.translate(ink.left() + half - b.left(), ink.top() + half - b.top())
        pen = QPen(QColor(ERASED), self.stroke, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)  # round: nothing beyond half the hairline
        p.setPen(pen if self.stroke > 0 else Qt.NoPen);p.setBrush(QColor(ERASED));p.drawPath(path);p.end()


def pleasantry(label, host, pixels):
    """A short greeting or pleasantry in Paper's script, graphite; plain Plex italic when script is off or missing.
    Only short words get this: menus, words to act on, file names, status and prose stay typeset."""
    if cursive_on(host) and SCRIPT in QFontDatabase.families():
        size = round(pixels * 1.25);left, right, bottom = script_room(label.text(), size)  # D1-fix: room round its swashes
        label.setStyleSheet('QLabel {font-family:\"%s\";font-size:%dpx;color:%s;font-weight:400;padding:0 %dpx %dpx %dpx;}' % (SCRIPT, size, TEXT, right, bottom, left))
        label.setIndent(0)  # the room is exactly the swash's (with a padding Qt would add half an x of its own)
    else:
        from .boss_theme import DISPLAY      # Plex Mono in Graphite; in Kasandra, the typewriter face her headings are set in
        from .boss_theme import VIOLET_PALE      # Graphite: the text colour; Kasandra: pale violet
        label.setStyleSheet('QLabel {font-family:\"%s\";font-size:%dpx;color:%s;font-weight:%d;}' % (DISPLAY, pixels, VIOLET_PALE, 500 if DISPLAY == MONO else 400))
    label.setProperty('pleasantry', True);label.setProperty('pleasantry_px', pixels)
    return label


def mono_font(size=16):
    font = QFont(MONO if MONO in QFontDatabase.families() else 'DejaVu Sans Mono');font.setPointSizeF(size * 0.75);font.setStyleHint(QFont.Monospace)
    return font


SECTION_SCALE = [1.0]  # the interface scale the Library's section labels are drawn at


def scale_of(host):
    """The interface scale: 1.0 at the default 14 pt, 2.0 at 28 pt (Paper v1.1's 200% text)."""
    return float((getattr(host, 'reading_profile', None) or {}).get('ui_pt', 14.0)) / 14.0


def role(widget, name):
    """A text role from the design scale: title 26, item 20, card 15, section 11 (at the default reading size)."""
    widget.setProperty('arcRole2', name);return widget


def chrome_css(profile, assets):
    """The window's own text on the Paper v1.1 scale (at the default interface size): controls, menus, tabs and rows 16,
    reading and Slate prose 18, titles 28, section headings 20, metadata 14, code and staC 16. What you read keeps the
    reading sizes; everything scales with the interface size in Settings › Appearance. Never shrunk to fit a window."""
    s = float(profile.get('ui_pt', 14.0)) / 14.0
    def px(v):return '%dpx' % max(10, round(v * s))
    controls = ('QLabel, QPushButton, QToolButton, QLineEdit, QComboBox, QCheckBox, QRadioButton, QSpinBox, QTabBar, QTreeView, QTreeWidget, '
                'QListView, QListWidget, QTableView, QTableWidget, QHeaderView, QMenuBar, QMenu, QDockWidget, QGroupBox')
    folder = Path(assets).as_posix()
    return ''.join([
        '%s {font-size:%s;}' % (controls, px(16)),
        'QTreeWidget#hardwareTree {font-size:%s;}' % px(16),
        'QTreeWidget#hardwareTree::item {padding:8px 8px;}',
        'QTreeWidget#hardwareTree::branch {image:none;border-image:none;background:transparent;}',
        'QTreeWidget#hardwareTree::branch:has-children:closed {image:url(%s/chevron-right.svg);}' % folder,
        'QTreeWidget#hardwareTree::branch:has-children:open {image:url(%s/chevron-down.svg);}' % folder,
        'QTabBar::close-button {image:url(%s/close.svg);subcontrol-position:right;width:18px;height:18px;margin:3px;}' % folder,      # a place the hand can hit: 24 px a side
        'QTabBar::close-button:hover {background:%s;border-radius:0;}' % TEAL_SOFT,
        "QLabel[arcReadingRole='heading'] {font-size:%s;font-weight:600;}" % px(20),
        'QLabel#homeTitle {font-size:%s;font-weight:500;}' % px(28),
        'QLabel[arcRole2="title"], QLabel[arcRole2="hero"] {font-size:%s;font-weight:500;}' % px(28),
    ] + ([  # Page headings (Files, Library, Slate's Agenda, Trash…) are in script: each says where you are with grace, once,
        # while the words to read and act on stay in print. Plain Plex when the owner turns script off.
        'QLabel[arcRole2="title"], QLabel[arcRole2="hero"] {font-family:"%s";font-size:%s;font-weight:400;color:%s;}' % (SCRIPT, px(38), TEXT),
    ] if SCRIPT_ON[0] and SCRIPT in QFontDatabase.families() else []) + [
        'QLabel[arcRole2="lead"] {font-size:%s;color:%s;}' % (px(18), QUIET),
        'QPushButton:focus, QToolButton:focus {border:0;border-bottom:3px solid %s;}' % TEXT,  # a word is focused by its underline, never a box
        'QComboBox:focus {border:2px solid %s;}' % AMBER_EDGE,
        'QTreeWidget:focus, QListWidget:focus {border:0;}',  # a list shows focus by its current row, marked in graphite
        'QLabel[arcRole2="item"], QLabel#ItemTitle {font-size:%s;font-weight:600;}' % px(20),
        'QLabel[arcRole2="card"] {font-size:%s;font-weight:600;}' % px(20),
        'QLabel[arcRole2="section"] {font-size:%s;letter-spacing:1px;color:%s;font-weight:500;}' % (px(13), bt.VIOLET),      # Graphite: quiet; Kasandra: violet
        'QWidget#LibraryFoot QPushButton {border:0;border-bottom:3px solid %s;background:transparent;color:%s;text-align:left;padding:4px 2px;}' % (ERASER_MARK, TEXT),
        'QWidget#LibraryFoot QPushButton:hover {background:%s;border-bottom:3px solid %s;}' % (TEAL_SOFT, TEAL_EDGE),
        'QLabel[arcRole2="quiet"] {font-size:%s;color:%s;}' % (px(14), QUIET),
        'QLabel#KindChip, QPushButton#AddressChip {font-size:%s;}' % px(14),
        'QLineEdit#OneBox {font-size:%s;}' % px(16),
        'QTextBrowser#ArcContext {font-size:%s;border:0;background:transparent;}' % px(16),
        'QListWidget#LedgerActivityTail {font-size:%s;background:transparent;border:0;}' % px(14),
        'QStatusBar, QStatusBar QLabel {font-size:%s;color:%s;}' % (px(14), QUIET),
        'QWidget#CommandRow2 QToolButton, QWidget#CommandRow2 QPushButton {font-size:%s;color:%s;padding:6px 10px;border:1px solid transparent;}' % (px(16), TEXT),
        'QWidget#CommandRow2 QToolButton:hover {background:%s;}' % RAISED,
        'QWidget#TimelineHead QLabel {font-size:%s;color:%s;}' % (px(14), QUIET),
        'QWidget#TimelineHead QPushButton, QWidget#TimelineHead QCheckBox {font-size:%s;color:%s;background:transparent;border:0;padding:4px 2px;margin:0 6px;}' % (px(14), TEXT),
        'QWidget#TimelineHead QPushButton {border-bottom:3px solid %s;} QWidget#TimelineHead QPushButton:hover {background:%s;border-bottom:3px solid %s;}' % (ERASER_MARK, TEAL_SOFT, TEAL_EDGE),
        'QWidget#SlateFace QLabel, QFrame#SlateMine QLabel, QFrame#SlateTheirs QLabel {font-size:%s;}' % px(18),
        'QLineEdit#SlateInput, QPlainTextEdit#SlateInput, QPlainTextEdit#Capture {font-size:%s;}' % px(18),
    ])


def line_icon(kind, color=QUIET, size=16):
    """Thin line icons for the few Library rows that carry one (Today, Ingress, Deliveries)."""
    from PySide6.QtGui import QIcon, QPixmap, QPolygonF
    from PySide6.QtCore import QPointF, QRectF
    scale = 2;pix = QPixmap(size * scale, size * scale);pix.fill(Qt.transparent);pix.setDevicePixelRatio(scale)
    p = QPainter(pix);p.setRenderHint(QPainter.Antialiasing);pen = QPen(QColor(color), 1.5);pen.setJoinStyle(Qt.RoundJoin);pen.setCapStyle(Qt.RoundCap);p.setPen(pen)
    if kind == 'home':
        p.drawPolyline(QPolygonF([QPointF(2.5, 7.5), QPointF(8, 2.5), QPointF(13.5, 7.5)]));p.drawPolyline(QPolygonF([QPointF(4, 6.5), QPointF(4, 13.5), QPointF(12, 13.5), QPointF(12, 6.5)]))
    elif kind == 'inbox':
        p.drawPolyline(QPolygonF([QPointF(2.5, 9), QPointF(5.5, 9), QPointF(6.5, 11), QPointF(9.5, 11), QPointF(10.5, 9), QPointF(13.5, 9)]))
        p.drawRoundedRect(QRectF(2.5, 3, 11, 10.5), 2, 2)
    elif kind == 'search':
        p.drawEllipse(QRectF(2.5, 2.5, 8, 8));p.drawLine(QPointF(9.5, 9.5), QPointF(13.5, 13.5))
    else:
        p.drawRoundedRect(QRectF(2.5, 4, 11, 9.5), 1.5, 1.5);p.drawLine(QPointF(2.5, 7), QPointF(13.5, 7));p.drawLine(QPointF(6.5, 9.5), QPointF(9.5, 9.5))
    p.end();return QIcon(pix)


def stop_icon():
    from PySide6.QtGui import QIcon, QPixmap
    pix = QPixmap(28, 28);pix.fill(Qt.transparent);pix.setDevicePixelRatio(2)
    p = QPainter(pix);p.setRenderHint(QPainter.Antialiasing);p.setPen(Qt.NoPen);p.setBrush(QColor(TEXT));p.drawRoundedRect(1.5, 1.5, 11, 11, 2, 2);p.end()
    return QIcon(pix)


def quiet_icon(icon, size=18):
    """The command row's icons in quiet greys, so the row reads as one line under the top bar."""
    from PySide6.QtGui import QIcon, QImage, QPixmap
    source = icon.pixmap(size * 2, size * 2)
    if source.isNull():return icon
    image = source.toImage().convertToFormat(QImage.Format_ARGB32)
    for y in range(image.height()):
        for x in range(image.width()):
            c = image.pixelColor(x, y)
            if c.alpha():
                v = int(96 + 0.55 * (0.3 * c.red() + 0.59 * c.green() + 0.11 * c.blue()));c.setRgb(v, min(255, v + 4), min(255, v + 10), c.alpha());image.setPixelColor(x, y, c)
    pix = QPixmap.fromImage(image);pix.setDevicePixelRatio(2);return QIcon(pix)


from PySide6.QtWidgets import QStyle, QStyledItemDelegate, QStyleOptionViewItem  # noqa: E402

COUNT_ROLE, BADGE_ROLE = Qt.UserRole + 5, Qt.UserRole + 6


class LibraryDelegate(QStyledItemDelegate):
    """Library rows show their count on the right, quietly; the Arrived count is an amber badge."""

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        extra = index.data(COUNT_ROLE)
        if not extra:return
        painter.save();font = QFont(option.font);font.setPixelSize(max(9, round(pixels(option.font) * 0.86)))
        painter.setFont(font);metrics = painter.fontMetrics();rect = option.rect.adjusted(0, 0, -10, 0)
        if index.data(BADGE_ROLE):
            width = metrics.horizontalAdvance(extra) + 14;from PySide6.QtCore import QRectF
            pill = QRectF(rect.right() - width, rect.center().y() - 10, width, 20)
            painter.setRenderHint(QPainter.Antialiasing);painter.setPen(Qt.NoPen);painter.setBrush(QColor(AMBER));painter.drawRoundedRect(pill, 9, 9);painter.setPen(QPen(QColor(LINE), 1));painter.setBrush(Qt.NoBrush);painter.drawRoundedRect(pill, 9, 9)
            painter.setPen(QColor(TEXT));painter.drawText(pill, Qt.AlignCenter, extra)
        else:
            painter.setPen(QColor(FAINT));painter.drawText(rect, Qt.AlignRight | Qt.AlignVCenter, extra)
        painter.restore()


def pixels(font):
    return font.pixelSize() if font.pixelSize() > 0 else round(font.pointSizeF() * 96 / 72)


class TimelineDelegate(QStyledItemDelegate):
    """A Timeline line: the time in Plex Mono, faint; then what happened, in plain words."""

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option);self.initStyleOption(opt, index);text = opt.text;opt.text = ''
        (opt.widget.style() if opt.widget else None).drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)
        stamp, _, words = text.partition('  ')
        if not re.fullmatch(r'\d\d:\d\d(:\d\d)?', stamp):stamp, words = '', text
        painter.save();rect = option.rect.adjusted(8, 0, -6, 0)
        if stamp:
            mono = mono_font();mono.setPixelSize(max(9, pixels(option.font) - 1));painter.setFont(mono)
            painter.setPen(QColor(FAINT));painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, stamp)
            rect = rect.adjusted(painter.fontMetrics().horizontalAdvance(stamp) + 12, 0, 0, 0)
        painter.setFont(option.font);painter.setPen(QColor(TEXT if not option.state & QStyle.State_Selected else AMBER_TEXT))
        painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, painter.fontMetrics().elidedText(words, Qt.ElideRight, rect.width()))
        painter.restore()


def call(host, op, args=None):
    """A Kernel read with the owner's principal; None when it is refused or unavailable."""
    from .engine import engineering
    from .engineering_kernel import operator
    try:
        r = engineering(host.root).dispatch(op, args or {}, operator())
        return r['result'] if r.get('ok') else None
    except Exception:
        return None


def chip(text, fg=TEXT, bg=RAISED, edge=LINE, mono=False, radius=13):
    label = QLabel(text)
    label.setStyleSheet('QLabel {color:%s;background:%s;border:1px solid %s;border-radius:%dpx;padding:3px 10px;%s}' %
                        (fg, bg, edge, radius, ('font-family:"%s";' % MONO) if mono else ''))
    return label


def escape_text(text):
    from html import escape
    return escape(str(text))


def sentence(html, actions, label=None):
    """4.1: an action is a word inside the sentence that needs it, not a box beside it. {name} marks a word; actions maps name -> (words, callable)."""
    from html import escape
    label = label or QLabel()
    def word(name):
        words, _ = actions[name]
        return '<a href="%s" style="color:%s;text-decoration:underline;text-decoration-color:%s;">%s</a>' % (name, TEXT, ERASER_MARK, escape(words))  # graphite word, pink underline
    import re
    label.setText(re.sub(r'\{(\w+)\}', lambda m:word(m.group(1)), html));label.setTextFormat(Qt.RichText);label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextBrowserInteraction);label.setOpenExternalLinks(False)
    label._actions = actions
    if not getattr(label, '_wired', False):
        label.linkActivated.connect(lambda name, l=label:l._actions[name][1]());label._wired = True
    return label


def button(text, kind='quiet', tip=''):
    b = QPushButton(text);b.setCursor(Qt.PointingHandCursor);b.setToolTip(tip);b.setProperty('arcButton', kind)
    return b


def hand_menu(host, face=None):
    """Rules ▸ Stacy's hand, and the same menu from the words under her name: how far she acts by herself (stacy_hand)."""
    from PySide6.QtGui import QActionGroup
    from PySide6.QtWidgets import QMenu
    from . import stacy_hand
    menu = QMenu(named("Stacy's hand"), host);group = QActionGroup(menu);group.setExclusive(True);lines = {}
    tips = {'ask': 'As before: every change waits for your Approve',
            'show': 'She makes ordinary changes at once and shows them, each with an Undo where it can be taken back',
            'free': 'She also makes the changes the records mark for approval. What cannot be undone still asks'}
    def choose(key):
        stacy_hand.choose(host, key);host.session.save()
        talk = getattr(getattr(host, 'shell2', None), 'face', None)
        if talk is not None:talk.show_hand()
    for key, word in stacy_hand.LEVELS:
        line = menu.addAction(word);line.setCheckable(True);line.setToolTip(tips[key]);group.addAction(line);lines[key] = line
        line.triggered.connect(lambda checked=False, key=key:choose(key))
    menu.setToolTipsVisible(True)
    mark = lambda:lines[stacy_hand.level(host)].setChecked(True)
    menu.aboutToShow.connect(mark);mark()
    def said(what):                              # her pane is found when the line is chosen: the menus are built before it is
        shell = getattr(host, 'shell2', None);talk = face or getattr(shell, 'face', None)
        if talk is None:return
        if shell is not None and callable(getattr(shell, 'show_slate_face', None)):shell.show_slate_face()      # her own face, not a worksheet's preview
        getattr(talk, what)()
    menu.addSeparator()
    menu.addAction('What she did…').triggered.connect(lambda checked=False:said('say_trail'))
    menu.addAction('What always asks…').triggered.connect(lambda checked=False:said('say_always'))
    return menu


def approve_button(run, host):
    """The owner's Approve of a change that waits, in Talk: the same filled amber button the Field shows at its foot, so one
    waiting change looks the same in both places, and lit in amber while it waits (boss_qt.waits). Under the pointer its
    edge answers in the pointer's green; once pressed it is spent and plain."""
    from .boss_qt import waits
    run.setStyleSheet('QPushButton {background:%s;color:%s;border:1px solid %s;border-radius:0;padding:4px 12px;font-weight:600;} '
                      'QPushButton:hover {border:1px solid %s;} QPushButton:focus {border:1px solid %s;} '
                      'QPushButton:disabled {background:transparent;color:%s;border:1px solid transparent;font-weight:400;}'
                      % (bt.OWNER, bt.ON_OWNER, bt.OWNER, READY, TEXT, QUIET))      # the owner's decision: amber in Graphite, raspberry in Kasandra
    waits(run, host)
    return run


# Top bar ---------------------------------------------------------------------

class Mark(QWidget):
    """The Ledger mark: a pencil on a pale pencil-yellow tile. Drawn, so it stays sharp at any scale."""

    def __init__(self, size=28):
        super().__init__();self.setFixedSize(size, size);self.setAccessibleName('Graphite')

    def paintEvent(self, event):
        from PySide6.QtCore import QPointF, QRectF
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing);s = self.width() / 28.0
        p.setPen(QPen(QColor(LINE_STRONG), 1 * s));p.setBrush(QColor(AMBER));p.drawRoundedRect(QRectF(3.5 * s, 3.5 * s, 21 * s, 21 * s), 5 * s, 5 * s)
        pen = QPen(QColor(TEXT), 1.75 * s);pen.setCapStyle(Qt.RoundCap);pen.setJoinStyle(Qt.RoundJoin);p.setPen(pen);p.setBrush(Qt.NoBrush)
        from PySide6.QtGui import QPolygonF
        p.drawPolygon(QPolygonF([QPointF(9 * s, 19 * s), QPointF(9.5 * s, 16.5 * s), QPointF(17 * s, 9 * s), QPointF(19 * s, 11 * s),
                                 QPointF(11.5 * s, 18.5 * s)]))  # a pencil, drawn: ledger and slate are written


class TopBar(QWidget):
    """The head band (HATCH DESK D1a): shaded edge to edge like a graphite pencil (desk_qt.paint_band), in the desk's three
    columns. The left slot holds the word Graphite alone at the band's inset; the centre column holds the eight menus,
    centred on the window's axis with equal gaps and the writing line's inset (desk_qt.menu_row); the right slot holds CPU ·
    GPU · RAM · TXT in four columns and, at the band's inset from the right edge, the erased Graphite symbol, the System
    menu (desktop_header_qt.SystemButton, still `nice` for callers). Every position is set by place(desk), called by
    desk_qt.apply; nothing here is laid out by a box layout, so each mirrored pair lands on whole pixels."""
    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('TopBar2');self.setProperty('paperFunctionalInk', True)
        rows = QVBoxLayout(self);rows.setContentsMargins(0, 0, 0, 0);rows.setSpacing(0)
        first = QWidget();first.setObjectName('HeadRow');rows.addWidget(first);self.first_row = first
        from .boss_qt import WorkshopStrip
        self.workshop_strip = WorkshopStrip(host)
        self.workshop_strip.setParent(self);self.workshop_strip.hide()
        row = QHBoxLayout(first);row.setContentsMargins(0, 0, 0, 0);row.setSpacing(0);self.row = row  # empty: place() sets every position
        self._style_key = None;self.plan = None
        # The left slot: the word Graphite alone, pale, as if erased from the shading (the mark lives at the far right now), in
        # the Paper script (the owner, 2026-11-06: "upper left Graphite should be cursive"; Wordmark).
        holder = QWidget(first);holder.setObjectName('HeadLeftSlot');self.brand_holder = holder
        brand = QHBoxLayout(holder);brand.setContentsMargins(0, 0, 0, 0);self.brand = brand  # empty, kept for callers
        self.mark = Mark(28);self.mark.setParent(holder);self.mark.hide()  # the old pencil tile: kept for callers, out of sight
        self.wordmark = Wordmark(holder);self.wordmark.hide();holder.hide()
        self.workspace = QToolButton(first);self.workspace.setObjectName('WorkspaceSwitch');self.workspace.setPopupMode(QToolButton.InstantPopup)
        self.workspace.setAccessibleName('Choose workspace');self.workspace.setMenu(QMenu(self.workspace));self.workspace.menu().aboutToShow.connect(self.fill_workspaces)
        self.workspace.hide()  # the workspace is chosen from the path's first word; this keeps the same choice for callers
        self.box = OneBox(host)  # the one place to type: it lives in the lower band (typebar_qt.TypeBar)
        self.path = PathBar(host, self);self.path.setParent(first)
        QShortcut(QKeySequence('Ctrl+L'), host, activated=self.path.edit_location)
        self.menus = QWidget(first);self.menus.setObjectName('CommandRow2')
        self.brain = QPushButton(first);self.brain.setObjectName('BrainChip');self.brain.setCursor(Qt.PointingHandCursor);self.brain.setAccessibleName('Graphite brain')
        self.brain.clicked.connect(lambda:host.shell2.show_slate_face())
        self.running = QPushButton(first);self.running.setObjectName('RunningChip');self.running.setFlat(True);self.running.setCursor(Qt.PointingHandCursor)
        self.running.clicked.connect(lambda:host.ledger_bridge.navigation()['trail']())
        # The right slot: the four monitors (UI-03; host.operations_monitors is their holder) and the System menu's symbol.
        right = QWidget(first);right.setObjectName('HeadRightSlot');self.right_holder = right
        rlay = QHBoxLayout(right);rlay.setContentsMargins(0, 0, 0, 0)  # empty: operations_qt takes the AI switch out of it by name
        from .desktop_header_qt import DesktopMonitors, SlateSwitch, SystemButton, MONITORS_NOTE
        self.pulse = DesktopMonitors(host);self.brain.hide();self.running.hide()
        self.pulse_holder = QWidget(right);self.pulse_holder.setObjectName('OperationsMonitors');self.pulse_holder.setToolTip(MONITORS_NOTE)
        self.pulse_holder.setAccessibleName(MONITORS_NOTE)
        hold = QHBoxLayout(self.pulse_holder);hold.setContentsMargins(0, 0, 0, 0);hold.setSpacing(0);hold.addWidget(self.pulse)
        self.date = pleasantry(QLabel(first), host, 19);self.date.setAlignment(Qt.AlignCenter);self.date.setObjectName('LedgerDate')
        self.date_timer = QTimer(self, interval=60000);self.date_timer.timeout.connect(self.show_date);self.date.hide()
        host.master_stop_button.hide()  # the controller's own button stays hidden: the kill switch is the first row of the System menu's list
        self.slate_switch = SlateSwitch(host);self.slate_switch.setParent(right);self.slate_switch.hide()  # operations_qt moves it to the right pane
        self.nice = SystemButton(host);self.nice.setParent(right);self.system = self.nice  # the erased symbol; `nice` for older callers
        # The menus: the existing command row (host.ribbon_scroll over host.ribbon_commands, the same QMenu objects).
        ribbon = getattr(host, 'ribbon_scroll', None)
        if ribbon is not None:
            parent_layout = host.toolbar.layout()
            if parent_layout is not None:parent_layout.removeWidget(ribbon)
            ribbon.setParent(self.menus);ribbon.show();ribbon.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            ribbon.viewport().setAutoFillBackground(False);ribbon.setAutoFillBackground(False)
            commands = getattr(host, 'ribbon_commands', None)
            if commands is not None:
                commands.setAutoFillBackground(False);commands.setProperty('paperFunctionalInk', True)
                if commands.layout() is not None:commands.layout().setAlignment(Qt.AlignVCenter)
        self.update_workspace_label()
        QTimer.singleShot(0, self.ledger_head)
        # G-B: the menu words fold into ⋯ (the rightmost first) before they would clip; ⋯ opens the same menus.
        self.more_menus = QToolButton();self.more_menus.setObjectName('MoreMenus');self.more_menus.setText('Work ▾');self.more_menus.setAccessibleName('Work commands')
        self.more_menus.setPopupMode(QToolButton.InstantPopup);self.more_menus.setToolButtonStyle(Qt.ToolButtonTextOnly);self.more_menus.setMenu(QMenu(self.more_menus))
        self.more_menus.menu().aboutToShow.connect(self.fill_more_menus);self.more_menus.setParent(first);self.more_menus.show();self.folded_menus = []
        self.programs = QToolButton(first);self.programs.setObjectName('BossPrograms');self.programs.setText('[#] Apps ▾')      # 0.8.1: the owner, "We'll change the name programs to apps"
        self.programs.setAccessibleName('Apps');self.programs.setToolTip('Installed apps and capabilities')
        from . import boss_theme as _bt
        if _bt.APPEARANCE == 'kasandra':      # 0.8.0, the owner's monogram for Programs: "kp", kasandra protocol, in her colours
            from PySide6.QtGui import QIcon
            from .kasandra_art import folder as kasandra_folder
            mark = QIcon(str(kasandra_folder(host.root) / 'kp_monogram.png'))
            if not mark.isNull():
                side = round(36 * scale_of(host))      # 0.8.2, the owner: "Probably don't need to call it Apps menu, just a bigger kp icon"
                self.programs.setIcon(mark);self.programs.setIconSize(QSize(side, side))
                self.programs.setProperty('paperIcon', True)      # its own colours: menus2 makes other pictures one graphite colour
                self.programs.setToolButtonStyle(Qt.ToolButtonIconOnly);self.programs.setText('')      # its name stays for readers (Apps)
        self.programs.clicked.connect(lambda checked=False:self.host.type_bar.hatch.open_list())
        # 0.5.3: the middle of the head. The owner: "Let's just leave it out in the middle. Free up the space ... an
        # equalizer, and make its style pulse up and down to represent something." The name and address of what is open
        # no longer stand here (the bar above the work says the name; Ctrl+L still brings the address, here, to be typed);
        # in their place, this computer at work (equalizer_qt).
        from .equalizer_qt import Equalizer
        self.equalizer = Equalizer(host);self.equalizer.setParent(first)

        def calm():
            from .document_qt import profile_of
            return bool(profile_of(self.host).get('reduce_motion'))
        self.equalizer.still = calm
        for watched in (self, getattr(host, 'ribbon_commands', None)):
            if watched is not None:watched.installEventFilter(self)

    def sizeHint(self):return QSize(800, 60)

    def minimumSizeHint(self):return QSize(480, 60)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Resize, QEvent.LayoutRequest) and not getattr(self.host, '_closing', False) and not getattr(self, '_placing', False):
            bar = getattr(self.host, 'type_bar', None);d = getattr(self.host, 'desk', None)
            if watched is self and event.type() == QEvent.Resize and bar is not None and d is not None and d.width != self.width():
                QTimer.singleShot(0, bar.align)  # the window's width changed: the desk again (the panes' width may change), now
            elif d is not None:QTimer.singleShot(0, lambda:self.place(getattr(self.host, 'desk', None)))
        return False

    def band_style(self, scale):
        from .boss_theme import CHROME_OVERRIDES
        key = round(scale, 4)
        if key == self._style_key:return
        self._style_key = key
        self.setStyleSheet(CHROME_OVERRIDES + 'QWidget#TopBar2 {background:transparent;border:0;}')
        font = mono_font(max(14, round(16 * scale)))
        if bt.DISPLAY != MONO:      # Kasandra: the menus across the head in her typewriter face, a little larger to read as well
            font = QFont(bt.DISPLAY);font.setPixelSize(max(15, round(18 * scale)))
        for widget in [self.path, self.more_menus, self.programs, self.nice] + list(getattr(self, 'bar_menus', [])):
            widget.setFont(font)
        self.pulse.restyle()

    def slot_needs(self, scale, d=None):
        # The head spans the window; its address must not widen the side columns.
        return 0, 0

    def fill_more_menus(self):
        menu = self.more_menus.menu();menu.clear()
        for heading in self.folded_menus:
            if heading.menu() is not None:menu.addMenu(heading.menu())

    def headings(self):
        return list(getattr(self.host, 'command_menus', {}).values())

    def menu_words(self):
        """The familiar menus in the open, one word each, across the head (0.5.1). The owner, with 0.4.6 on the ThinkPad:
        "The work menu, I don't know if I like that. It's just an extra click to get to the familiar ... file, edit, tools,
        arrange, command, rules, property, guide ... I almost wonder if we should just have those at the top, kind of like
        Apple does, instead of hidden away in a menu." Each word opens the very menu that was inside Work: the same QMenu
        objects, so nothing is listed twice and every key still works."""
        heads = [heading for heading in self.headings() if heading.menu() is not None]
        if len(getattr(self, 'bar_menus', [])) != len(heads):
            for old in getattr(self, 'bar_menus', []):old.deleteLater()
            self.bar_menus = []
            for heading in heads:
                word = QToolButton(self.first_row);word.setObjectName('HeadMenu');word.setPopupMode(QToolButton.InstantPopup)
                word.setToolButtonStyle(Qt.ToolButtonTextOnly);word.setCursor(Qt.PointingHandCursor);word.setFont(self.more_menus.font())
                self.bar_menus.append(word)
        from .tool_faces import dress
        for word, heading in zip(self.bar_menus, heads):
            if word.menu() is not heading.menu():
                word.setMenu(heading.menu())
                if not heading.menu().property('glyphDressed'):      # with icons chosen, a line that names a drawn thing carries its glyph
                    heading.menu().setProperty('glyphDressed', True);heading.menu().aboutToShow.connect(lambda menu=heading.menu(): dress(menu))
            if word.text() != heading.text():
                word.setText(heading.text());word.setAccessibleName(heading.text() + ' menu')
        return self.bar_menus

    def plan_menus(self, d, reach):
        """The menu row for desk d: (kept headings, left edges, gaps, widths, inset on the column or None). The words lie on
        the centre column with the writing line's inset and equal gaps when they fit there; else they are centred on the
        axis with the least gap, as far into both slots as the nearer slot's own words allow (`reach`: the least distance from
        either window edge); else the rightmost fold into ⋯ (G-B), which opens the same menus."""
        from .desk_qt import menu_gap, menu_row, tight_row, ink_air, ink_width
        headings = self.headings()
        if not headings:return None
        a = ink_air(d.scale)  # D1-fix: each menu's box is its ink and the air each side, so the row's drawn ends are its ink
        widths = [ink_width(h.font(), h.text()) + 2 * a for h in headings];more = ink_width(self.more_menus.font(), self.more_menus.text()) + 2 * a
        start, end = d.pane + d.inset - a, d.width - d.pane - d.inset + a;least = menu_gap(d.scale)
        for keep in range(len(headings), -1, -1):
            ws = widths[:keep] + ([more] if keep < len(headings) else [])
            row = menu_row(ws, d.width, start, end, least)
            if row is not None:return keep, row[0], row[1], row[2], row[0][0] + a - d.pane  # the line's inset: the first menu's ink
            xs, gaps, ws2 = tight_row(ws, d.width, least)
            if xs[0] + a >= reach:return keep, xs, gaps, ws2, (xs[0] + a - d.pane if xs[0] + a >= d.pane else None)
        return 0, [], [], [], None

    def place(self, d):
        if d is None or getattr(self, '_placing', False) or getattr(self.host, '_closing', False):return
        self._placing = True
        try:
            self.band_style(d.scale)
            self.command_band_height = d.band
            self.first_row.setGeometry(0, 0, d.width, d.band)
            strip = max(0, self.height() - d.band)
            self.workshop_strip.setGeometry(d.inset, d.band, d.width - 2 * d.inset, strip)
            self.workshop_strip.setVisible(strip > 0)
            if strip:self.workshop_strip.raise_()
            self.brand_holder.hide();self.wordmark.hide();self.menus.hide();self.right_holder.hide()
            self.pulse_holder.hide() if self.pulse_holder.parentWidget() is self.right_holder else None
            self.nice.setParent(self.first_row)
            h, o, gap = d.band, d.inset, max(6, d.gap // 2)
            x = d.width - o
            # 0.7.0: the System menu is gone from the head (the owner: "Could we eliminate the system menu if we got creative").
            # Its things are behind the four meters at the foot (meter_cards), at the foot of the Work menu (leaving) and
            # among the programs (the game). The button and its menu stay alive, out of sight, for what still calls them.
            self.nice.setGeometry(0, 0, 0, 0);self.nice.hide()
            for widget in (self.programs,):
                width = widget.fontMetrics().horizontalAdvance(widget.text()) + round(26 * min(d.scale, 1.4)) if widget.text() else round(18 * min(d.scale, 1.4))
                if not widget.icon().isNull():width += widget.iconSize().width() + (round(8 * min(d.scale, 1.4)) if widget.text() else 0)      # Kasandra's kp, now alone
                x -= width;widget.setGeometry(x, 0, width, h);widget.show();x -= gap
            # The familiar menus stand in the open from the left edge; the name of what is open follows them. In a window too
            # narrow for all of them and a name, the rightmost fold into ⋯, which lists every menu.
            words = self.menu_words();air = round(22 * min(d.scale, 1.4));name_room = round(180 * d.scale)
            widths = [word.fontMetrics().horizontalAdvance(word.text()) + air for word in words]
            fold = self.more_menus.fontMetrics().horizontalAdvance('⋯') + round(26 * min(d.scale, 1.4));kept = 0
            for keep in range(len(words), -1, -1):
                if o + sum(widths[:keep]) + (fold if keep < len(words) else 0) + gap + name_room <= x or keep == 0:
                    kept = keep;break
            left = max(0, o - air // 2)
            for at, word in enumerate(words):
                if at < kept:
                    word.setGeometry(left, 0, widths[at], h);word.show();left += widths[at]
                else:word.hide()
            if kept < len(words) or not words:
                self.more_menus.setText('⋯' if words else 'Work ▾');width = fold if words else self.more_menus.fontMetrics().horizontalAdvance('Work ▾') + round(26 * min(d.scale, 1.4))
                self.more_menus.setGeometry(left, 0, width, h);self.more_menus.show();left += width
            else:
                self.more_menus.setText('Work ▾');self.more_menus.hide()      # still there, and still lists every menu, for what reads it
            # The middle: the equalizer, centred in what is left. The address line lies under it, out of sight, and comes
            # up in its place only while it has the keyboard (Ctrl+L).
            room = max(0, x - left - 2 * gap);self.path.setGeometry(left + gap, 0, max(40, room), h)
            typing = self.path.hasFocus();self.path.setVisible(typing)
            wide = min(room, round(self.equalizer.sizeHint().width() * min(d.scale, 1.5)));tall = min(h - 16, round(40 * min(d.scale, 1.3)))
            self.equalizer.setGeometry(left + gap + (room - wide) // 2, (h - tall) // 2 - 1, max(0, wide), tall)
            self.equalizer.setVisible(not typing and wide >= 48)
            self.folded_menus = self.headings()
            self.plan = None
        finally:self._placing = False

    def paintEvent(self, event):
        """The head band: shaded edge to edge with the desk's grain (desk_qt.paint_band), the same tile as the lower band."""
        from .desk_qt import paint_band
        p = QPainter(self);paint_band(self, p);p.end()

    def show_date(self):
        import datetime
        today = datetime.date.today();self.date.setText('%d %s' % (today.day, today.strftime('%b')))
        self.date.setToolTip(today.strftime('%A, %d %B %Y'))

    def ledger_head(self):
        """The menu words in the head's band lettering (HATCH DESK D1a: pale paper, the interface's control size; until then
        small capitals in graphite on paper)."""
        self._style_key = None;self.band_style(scale_of(self.host))
        d = getattr(self.host, 'desk', None)
        if d is not None:self.place(d)

    def update_workspace_label(self):
        from . import locations
        try:value = locations.marker(self.host.root)
        except ValueError:value = None
        name = (value or {}).get('name') or ('Program' if locations.contains_program(self.host.root) else Path(self.host.root).name)
        self.workspace.setText(name + '  ▾');self.workspace.setToolTip(str(self.host.root))

    def fill_workspaces(self):
        from . import locations
        menu = self.workspace.menu();menu.clear()
        here = Path(self.host.root).resolve();home = locations.concern_home()
        found = []
        if home.is_dir():
            for folder in sorted(home.iterdir()):
                try:value = locations.marker(folder) if folder.is_dir() else None
                except ValueError:value = None
                if value:found.append((value.get('name') or folder.name, folder))
        for name, folder in found:
            action = menu.addAction(('✓  ' if folder.resolve() == here else '     ') + name + '   ' + short(folder))
            action.triggered.connect(lambda checked=False, f=folder:self.switch(f))
        if not found:menu.addAction('No other workspaces in ' + short(home)).setEnabled(False)
        menu.addSeparator()
        menu.addAction('New workspace…').triggered.connect(self.new_workspace)

    def switch(self, folder):
        if Path(folder).resolve() == Path(self.host.root).resolve():return
        if QMessageBox.question(self, 'Switch workspace', 'Open ' + short(folder) + '? Graphite saves this window and starts again there.') != QMessageBox.Yes:return
        relaunch(self.host, folder)

    def new_workspace(self):
        from PySide6.QtWidgets import QInputDialog
        from . import locations
        name, ok = QInputDialog.getText(self, 'New workspace', 'Name (a folder in ' + short(locations.concern_home()) + ')')
        if not ok or not name.strip():return
        try:folder = locations.ensure_workspace(locations.concern_home() / re.sub(r'[^\w .-]+', '_', name.strip()), name=name.strip())
        except (OSError, ValueError) as exc:QMessageBox.warning(self, 'New workspace', str(exc));return
        self.switch(folder)

    def fit_menus(self):
        """The menus for the current desk (G-B's name for it: the rightmost fold into ⋯ before a word would clip)."""
        self.place(getattr(self.host, 'desk', None))

    def refresh(self):
        self.fit_menus()  # the 5 s tick is a backstop for a size change no event announced
        brain = call(self.host, 'brain.status') or {}
        words = {'READY': 'ready', 'MODEL_STOPPED': 'stopped', 'NO_MODEL_SELECTED': 'no brain yet'}.get(brain.get('state'), 'unknown')
        status_words = {'READY': 'ready', 'MODEL_STOPPED': 'stopped', 'NO_MODEL_SELECTED': 'none yet'}.get(brain.get('state'), 'unknown')
        model = (self.host.shell2.model_name(brain) or 'Graphite') if brain.get('state') == 'READY' else 'Graphite'
        dot = READY if brain.get('state') == 'READY' else (AMBER if brain.get('state') == 'MODEL_STOPPED' else FAINT)
        ready = brain.get('state') == 'READY'
        self.brain.setText(('●  ' + model) if ready else ('○  Graphite · ' + words))
        self.brain.setStyleSheet('QPushButton#BrainChip {color:%s;}' % (TEXT if ready else QUIET))
        self.brain.setToolTip(named('Stacy\'s brain, the model, runs on this computer · click to talk to her'));self.host._status_brain = status_words
        jobs = call(self.host, 'jobs.list') or []
        active = [j for j in jobs if j.get('state') in ('Queued', 'Running')] if isinstance(jobs, list) else []
        self.running.setText(('◐  %d running' % len(active)) if active else '');self.running.setVisible(False)  # the pulse shows it, on its own 2 s sample
        equalizer = getattr(self, 'equalizer', None)
        if equalizer is not None and equalizer.busy != bool(active):
            equalizer.busy = bool(active);equalizer.update()      # amber along its bottom while Graphite itself has work running
        self.running.setToolTip('\n'.join(j.get('tool', '') for j in active[:8]))
        _ = dot


def short(path):
    try:return '~/' + Path(path).resolve().relative_to(Path.home().resolve()).as_posix()
    except ValueError:return str(path)


def relaunch(host, folder, drop=()):
    """Start Ledger again on another workspace, then close this window normally (it saves and asks about unsaved work).
    `drop`: names taken out of the new start's environment (an appearance chosen in the menu must not be outranked by one
    this start was given)."""
    import os
    import sys
    from PySide6.QtCore import QProcess
    from . import locations
    env = dict(os.environ);env['ARC_LEDGER_WORKSPACE'] = str(folder);env.pop('ARC_LEDGER_EDITION', None)
    for name in drop:env.pop(name, None)
    if not host.close():return
    process = QProcess();process.setProgram(sys.executable);process.setArguments(['-m', 'workbench.launch'])
    process.setWorkingDirectory(str(locations.PACKAGE))
    from PySide6.QtCore import QProcessEnvironment
    environment = QProcessEnvironment()
    for key, value in env.items():environment.insert(key, value)
    process.setProcessEnvironment(environment);process.startDetached()


# Where you are --------------------------------------------------------------------

class PathBar(QLineEdit):
    """The active address on the head itself. Ctrl+L, Enter, Escape, Copy.

    0.5: at rest the head says the name of what is open and, quietly, where it is, not the address. A page opened from a
    record has an address like graphite://open/5ab8a3fd..., which is honest and typeable and tells a person nothing.
    The address is still the line's text, and it is what is shown the moment the line has the keyboard (a click, or
    Ctrl+L), whole and selected, to be read, copied or typed over; its tip always carries it."""
    def __init__(self, host, top):
        super().__init__();self.host = host;self.top = top;self.words = self
        self.setObjectName('WorkspacePath');self.setFrame(False);self.setMinimumWidth(0)
        self.setProperty('paperFunctionalInk', True)
        self.setAccessibleName('Active workspace path')
        self.setAccessibleDescription('Full path. Type an address here and it opens; leave it and it is put back.')
        self.returnPressed.connect(self.navigate)
        self.timer = QTimer(self, interval=400);self.timer.timeout.connect(self.refresh);self.timer.start()
        self.refresh(force=True)

    def refresh(self, force=False):
        if getattr(self.host, '_closing', False):return
        from .work_location import location
        address, description = location(self.host)
        if (address, description) != (getattr(self, '_address', None), getattr(self, '_kind', None)):self.update()
        self._address = address;self._kind = description
        if force or not self.hasFocus():
            if self.text() != address:
                self.setText(address);self.setCursorPosition(0)
        self.setToolTip(address + '\n' + description)      # 0.5.2: no keys beside it

    def friendly(self):
        """(the name of what is open, and quietly where or what it is), as the head says them at rest."""
        host = self.host;address = getattr(self, '_address', None) or self.text();kind = getattr(self, '_kind', '') or ''
        if getattr(host, '_field_active', False):return 'The Field', Path(host.root).name
        tabs = getattr(host, 'tabs', None);title = tabs.tabText(tabs.currentIndex()).replace('&', '').replace('◆ ', '').strip() if tabs is not None and tabs.currentIndex() >= 0 else ''
        bar = getattr(host, 'centre_bar', None)       # the bar above the work knows the name of what is open; the tab knows what kind of room it is in
        name = getattr(bar, '_name', '') if bar is not None and not bar.isHidden() else ''
        if name:
            room = title.replace(name, '').strip(' ·•') if name in title else title
            state = str(getattr(bar, '_said', ''))[len(name):].strip(' ·')      # "not saved yet", "read only", or nothing
            return name, ' · '.join(part for part in ('' if room == name else room, state) if part)
        if address.startswith('graphite://'):
            if address.startswith('graphite://documents/'):return title or 'Document', kind
            return (kind or title or 'Work'), ''
        if kind.startswith('Workspace'):return ('Today' if 'Today' in kind else Path(address).name or 'Workspace'), short(address)
        path = Path(address)
        return path.name or address, short(path.parent)

    def paintEvent(self, event):
        if self.hasFocus():return super().paintEvent(event)      # being typed in: the address itself, as it is
        from PySide6.QtGui import QFontMetrics, QPalette
        from PySide6.QtWidgets import QStyle, QStyleOptionFrame
        name, where = self.friendly();option = QStyleOptionFrame();self.initStyleOption(option)
        box = self.style().subElementRect(QStyle.SE_LineEditContents, option, self).adjusted(2, 0, -2, 0)
        p = QPainter(self);p.setRenderHint(QPainter.TextAntialiasing);p.setFont(self.font());fm = QFontMetrics(self.font())
        said = fm.elidedText(name, Qt.ElideMiddle, box.width());ink_now = self.palette().color(QPalette.Text)
        try:
            from .boss_qt import glows
            from .boss_theme import glow
            level = glow() if glows(self.host) else 0.0
        except Exception:  # noqa: BLE001 - a name is drawn whatever else is the matter
            level = 0.0
        if level > 0:       # the name of what is open is lit: the same word, faintly, a little off all round
            halo = QColor(ink_now);halo.setAlphaF(min(0.28, 0.07 * level));p.setPen(halo)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1), (2, 0), (-2, 0)):
                p.drawText(box.translated(dx, dy), Qt.AlignVCenter | Qt.AlignLeft, said)
        p.setPen(ink_now);p.drawText(box, Qt.AlignVCenter | Qt.AlignLeft, said)
        left = box.left() + fm.horizontalAdvance(said) + fm.horizontalAdvance('   ')
        if where and box.right() - left > fm.horizontalAdvance('mmmmmm'):
            p.setPen(QColor(QUIET));p.drawText(box.adjusted(left - box.left(), 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft, fm.elidedText(where, Qt.ElideMiddle, box.right() - left))
        p.end()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if event.reason() == Qt.MouseFocusReason:QTimer.singleShot(0, self.selectAll)      # a click shows the whole address, ready to copy or type over

    def edit_location(self):
        equalizer = getattr(self.top, 'equalizer', None)      # 0.5.3: the address comes up in the equalizer's place while it is typed
        if equalizer is not None:equalizer.hide()
        self.show();self.raise_()
        self.refresh(force=True);self.setFocus(Qt.ShortcutFocusReason);self.selectAll()

    def navigate(self):
        from .work_location import navigate
        try:
            navigate(self.host, self.text())
        except (OSError, ValueError) as exc:
            self.host.statusBar().showMessage(str(exc), 8000)
            self.setAccessibleDescription(str(exc));self.selectAll();return
        self.clearFocus();self.refresh(force=True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.refresh(force=True);self.clearFocus();event.accept();return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        if event.reason() == Qt.PopupFocusReason:     # its own right-click menu opened (Paste is there): the line stays as it is
            super().focusOutEvent(event);return
        super().focusOutEvent(event);self.refresh(force=True)
        equalizer = getattr(self.top, 'equalizer', None)
        if equalizer is not None:                     # the address is done with: it goes, and this computer at work comes back
            self.hide();equalizer.setVisible(equalizer.width() >= 48)


# The one box -------------------------------------------------------------------
# HATCH DESK D3: the one box is the writing line in the lower band, with four modes (typebar_qt.TARGETS): Assignment (words go
# to Graphite on Enter; typed staC runs only on Ctrl+Enter), Shell (every line to the configured shell), Search (results as
# you type, Enter searches the workspace) and Log (the line filters the Log view's stream). The lead characters keep their
# meaning: @ staC and / an operation by name (in Assignment), ? Search, $ Shell; typed first into an empty line they choose
# the mode (typebar_qt.JUMPS); in Shell every character is the shell's.

KEYS_TO_PRESS = re.compile(r'(?:(?:Ctrl|Alt|Shift)\+)*(?:Enter|Esc|Tab|Return)\b|↑ ↓|(?<![\w])[@/?$](?=\s)')


def keyed_html(text, px, print_px, notes=None):
    """A note in the Paper script with the keys to press printed: quiet_html's keys and numbers, and the writing line's own keys
    (Enter, Esc, Tab, ↑ ↓) and lead characters (@ / ? $). Plain escaped text when the script is off or missing."""
    import html
    notes = notes or quiet_html
    if not _script_ready():return html.escape(text).replace('\n', '<br>')
    out = [];at = 0
    for m in KEYS_TO_PRESS.finditer(text):
        if m.start() > at:out.append(notes(text[at:m.start()], px, print_px))
        out.append('<span style="font-size:%dpx;">%s</span>' % (print_px, html.escape(m.group(0))));at = m.end()
    if at < len(text):out.append(notes(text[at:], px, print_px))
    return ''.join(out)


class KeyedWords(QuietWords):
    """QuietWords whose note prints the writing line's keys too (keyed_html): the results' caption, the Log view's note. Its
    restyle is QuietWords' own, with keyed_html in quiet_html's place for that call."""

    def restyle(self, force=False):
        global quiet_html
        plain = quiet_html;quiet_html = lambda text, px, print_px:keyed_html(text, px, print_px, plain)
        try:super().restyle(force)
        finally:quiet_html = plain


# 0.5.3: what the list under the line is, with no key named (the keys work as they did).
CAPTIONS = {'slate': named('Your words go to Stacy · a line you type is run by the arrow · / an operation'),
            'find': 'Choose a result, or search the whole workspace',
            'shell': 'Runs in your shell',
            'log': 'Filters the stream'}
KEY_WORDS = ('Enter',)      # a row's old note of the key that takes it: no longer written beside it


class OneBox(QLineEdit):
    """The writing line: give Graphite an assignment, run typed staC (Ctrl+Enter) or an operation (/), type to the shell, search
    the workspace, or filter the Log (HATCH DESK D3)."""

    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('OneBox')
        writing_prompt(self, 'Run a line, a command, or search · @ / ? $')
        self.setToolTip(named('The one line you type on. The name lit at its left says who the words go to: Stacy, the Terminal, Search, the Web or the Log.'))
        self.setAccessibleName('Writing line: Assignment, Shell, Search and Log');self.setClearButtonEnabled(True);self.setMinimumWidth(220)
        self.popup = ResultsPopup(host, self);self.textEdited.connect(self.update_results);self.returnPressed.connect(self.popup.activate_current)
        self._catalog = [];self._catalog_at = 0
        self.preview_timer = QTimer(self, singleShot=True, interval=350);self.preview_timer.timeout.connect(self.show_preview)

    def mode(self):
        return getattr(self.host, 'type_target', 'slate')

    def focusInEvent(self, event):
        super().focusInEvent(event)
        if self.text():self.update_results(self.text())

    def focusNextPrevChild(self, forward):
        if self.console_page(self.text()):return False  # Tab completes a console line; it does not leave the box
        return super().focusNextPrevChild(forward)

    def console_page(self, text):
        """Which console page a line goes to (None: Graphite in Assignment, the filter in Log). Shell: every line is the
        shell's. Elsewhere a lead character says it (@ staC, / an operation, ? Search, $ Shell), then the mode (Search: find)."""
        mode = self.mode()
        if mode == 'shell':return 'shell'
        text = text.strip()
        lead = 'stac' if text.startswith('@') else {'/': 'kernel', '?': 'find', '$': 'shell'}.get(text[:1]) if text else None
        if lead:return lead
        return 'find' if mode == 'find' else None

    _walked = None  # (mode, page, line): the line Up or Down last recalled, so the next Up or Down walks on in that page's history

    def history_page(self, text):
        """Whose history Up and Down walk: a console line's own page (console_page); in Assignment, the typed staC's (the old
        staC target's history, D3-fix: it could no longer be walked) from an empty line or from a line the walk recalled, as
        the staC target walked it. Typed words in Assignment keep Up and Down for the results under the line."""
        page = self.console_page(text)
        if page:return page
        walked = self._walked
        if walked is not None and walked[0] == self.mode() and walked[2] == text:return walked[1]
        if self.mode() == 'slate' and not text.strip():return 'stac'
        return None

    def keyPressEvent(self, event):
        bar = getattr(self.host, 'type_bar', None);mode = self.mode()
        enter = event.key() in (Qt.Key_Return, Qt.Key_Enter);control = bool(event.modifiers() & Qt.ControlModifier)
        if enter and control and bar is not None:  # the deliberate key: typed staC (Assignment), a capture (Log ▸ Network)
            if bar.ctrl_enter():self.popup.hide();return
        elif enter and mode == 'log' and bar is not None:bar.log_enter();return
        if (bar is not None and mode != 'shell' and not self.text() and event.text() in ('@', '/', '?', '$')
                and not event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier)):
            jump = {'@': 'slate', '/': 'slate', '?': 'find', '$': 'shell'}[event.text()]
            bar.set_target(jump, focus=False)
            if event.text() in '?$':return  # the mode is chosen; its character is not part of the line
        console = getattr(self.host, 'console', None);page = self.console_page(self.text()) if console is not None else None
        walk = self.history_page(self.text()) if console is not None and event.key() in (Qt.Key_Up, Qt.Key_Down) else None
        if walk and walk != 'find' or (walk == 'find' and not self.popup.isVisible()):
            line = console.recall(walk, -1 if event.key() == Qt.Key_Up else 1, self.text())  # a console line: its page's history, as in a terminal
            if line is not None:self.setText(line);self.update_results(line);self._walked = (self.mode(), walk, line)
            return
        if page and event.key() == Qt.Key_Tab:
            self.setText(console.complete_line(page, self.text()));self.update_results(self.text());return
        if event.key() in (Qt.Key_Down, Qt.Key_Up) and self.popup.isVisible():self.popup.move_selection(1 if event.key() == Qt.Key_Down else -1);return
        if event.key() == Qt.Key_Escape:self.popup.hide();self.clearFocus();return
        super().keyPressEvent(event)

    def update_results(self, text):
        text = text.replace('\u200b', '').strip()  # break points copied out of a Graphite bubble
        if not text or self.mode() == 'log':self.popup.hide();return
        self.popup.show_results(self.results(text))
        if text.startswith('@') and '|' in text and self.mode() == 'slate':self.preview_timer.start()  # a pause in typing runs it once, read-only

    def show_preview(self):
        text = self.text().replace('\u200b', '').strip()
        if self.hasFocus() and text.startswith('@') and '|' in text and self.mode() == 'slate':self.popup.show_results(self.results(text, preview=True))

    def catalog(self):
        """Cataloged files by name, refreshed at most every 15 seconds."""
        import time
        if time.monotonic() - self._catalog_at < 15:return self._catalog
        self._catalog_at = time.monotonic();self._catalog = library_files(self.host, limit=400)
        return self._catalog

    def use_program(self, program):
        """A staC program that worked before goes into the line, ready for Ctrl+Enter (D3: only Ctrl+Enter runs typed staC)."""
        bar = getattr(self.host, 'type_bar', None)
        if bar is not None:bar.set_target('slate', focus=False)
        self.setText(program);self.setFocus();self.end(False);self.popup.hide()

    def results(self, text, preview=False):
        """What the line offers under it, by mode (HATCH DESK D3). Assignment: ask Stacy (Enter), keep it as a note, staC that
        worked before (into the line for Ctrl+Enter), files and commands by name; a line that parses as staC says that
        Ctrl+Enter runs it, and Enter still gives it to Graphite. Search: search the workspace (Enter), then files, cabinet
        records, settings and commands by name, each opening where it belongs. Shell: the line for the shell. / lines: the
        operation. Log: nothing (the line filters the stream)."""
        from .typebar_qt import parses_as_stac
        rows = [];mode = self.mode();page = self.console_page(text)
        if mode in ('log', 'web'):return rows      # Web has no list: Enter opens or searches in the browser, and the list must not offer another thing
        if page == 'find':return self.search_rows(text[1:].strip() if text.startswith('?') else text)
        if page in ('kernel', 'shell'):
            word = {'kernel': 'Operation  ', 'shell': (getattr(getattr(self.host, 'type_bar', None), 'labels', {}).get('shell', 'Shell')) + '  '}[page]
            rows.append(('section', 'IN THE WORKING AREA', None))
            rows.append(('stac', word + text, ('Enter', lambda:to_console(self.host, page, text))))
            return rows
        if page == 'stac' or parses_as_stac(text):
            rows.append(('section', 'A LINE · THE ARROW RUNS IT', None))
            if preview and text.startswith('@'):rows += preview_rows(self.host, text)
        rows.append(('section', named('ASK STACY'), None))
        rows.append(('ask', named('Ask Stacy · ') + (text if len(text) < 48 else text[:46] + '…'), ('Enter', lambda:self.host.shell2.ask(text))))
        rows.append(('keep', 'Keep as a note in Notes', ('', lambda:capture(self.host, text))))
        learned = call(self.host, 'matrix.examples', {'text': text[:600]}) or {}
        worked = learned.get('worked') or []
        if worked:
            rows.append(('section', 'WORKED BEFORE · FROM THE INSTRUCTION MATRIX', None))
            for row in worked[:2]:
                program = row['program']
                rows.append(('stac', program, ('Use', lambda p=program:self.use_program(p))))
        needle = text.casefold()
        files = self.file_rows(needle)
        if files:
            rows.append(('section', 'FILES', None))
            rows += files[:6]
        commands = self.commands(text)
        if commands:
            rows.append(('section', 'COMMANDS', None))
            rows += [('command', label, (hint, fn)) for label, hint, fn in commands[:6]]
        return rows

    def file_rows(self, needle):
        """Files by name: what was viewed, recent documents and the received catalog; each opens in its viewer."""
        files = []
        if not needle:return files
        for path in getattr(self.host, '_viewer_recent', []):
            if needle in Path(path).name.casefold():files.append((Path(path).name, 'viewed · ' + short(Path(path).parent), lambda p=path:self.host.open_in_viewer(p)))
        for rel in self.host.session.state.get('recent', []):
            if needle in rel.casefold():files.append((Path(rel).name, rel, lambda r=rel:self.host.open_document(self.host.root / r)))
        for entry in self.catalog():
            if needle in entry['name'].casefold():files.append((Path(entry['name']).name, entry['delivery'], lambda e=entry:self.host.shell2.open_library_file(e)))
        return [('file', name + '      ' + where, (KIND_SHORT.get(kind_of(name), ''), fn)) for name, where, fn in files]

    def search_rows(self, text):
        """Search's results as you type (D3; the cabinet's query box and the settings filter came here in D1b): first the
        search itself (Enter: files and their words, received files, the cabinet, settings, commands and the Timeline in the
        working area, Console.run_find), then what matches by name, each opening where it belongs."""
        from .console_qt import cabinet_records, reveal_record, setting_rows
        rows = [('section', 'SEARCH', None)]
        if not text:return rows
        rows.append(('search', 'Search the workspace for “%s”' % (text if len(text) < 48 else text[:46] + '…'), ('Enter', lambda:to_console(self.host, 'find', text))))
        files = self.file_rows(text.casefold())
        if files:rows.append(('section', 'FILES', None));rows += files[:5]
        records = cabinet_records(self.host, text, 5)
        if records:
            rows.append(('section', 'CABINET', None))
            rows += [('file', n['label'] + '      ' + n['role'].replace('_', ' '), ('', lambda i=n['id']:reveal_record(self.host, i))) for n in records]
        found = setting_rows(text, 4)
        if found:
            rows.append(('section', 'SETTINGS', None))
            rows += [('command', n['label'] + '      ' + n['target'], ('', lambda k=n['target']:self.host.ledger_bridge.show_settings(key=k))) for n in found]
        commands = self.commands(text)
        if commands:
            rows.append(('section', 'COMMANDS', None))
            rows += [('command', label, (hint, fn)) for label, hint, fn in commands[:4]]
        return rows

    def commands(self, query):
        needle = query.casefold();found = [];seen = set()
        places = (('Jot it down', 'capture'), ('Go to Today', 'home'), ('Go to the Office', 'office'), (named('Talk to Stacy'), 'slate'), ('Open the Library', 'library:all'),
                  ('Project Desk', 'project_desk'), ('Changes', 'changes'), ('Continuing work', 'continuing'), ('Exchange & deployment', 'deployment'), ('Investigations', 'investigations'), ('New investigation', 'investigations'), ("Graphite's Agenda", 'agenda'), ('Files', 'files'), ('Trash', 'trash'), ('Egress', 'files:Egress'),
                  ('Night Shift', 'continuing'), ('Work on a copy of a file', 'work_copy'), ('Working copies', 'files:Working copies'),
                  ('Settings', 'settings'), ('All commands', 'commands'), ('Organizer', 'organizer'), ('Memory', 'memory'))
        for label, destination in places:
            if needle in label.casefold():found.append((label, '', lambda d=destination:open_destination(self.host, d)));seen.add(label)
        for action in self.host.actions():
            label = action.text().replace('&', '').strip()
            if not label or label in seen or not action.isEnabled() or needle not in label.casefold():continue
            seen.add(label);found.append((label, action.shortcut().toString(), action.trigger))
        return found


def shaped_rows(rows):
    """Rows of the shapes Stacy answers in most, written for a narrow column: a line that names the thing, then what the
    records say of it, a blank line between rows. A doubt leads with its verdict; a what-if with what it says now and what it
    would say; a trace with which way and how far. None for any other shape (the caller's own layout then stands)."""
    if not rows or not all(isinstance(row, dict) for row in rows):return None
    keys = set(rows[0])
    if any(set(row) != keys for row in rows):return None
    say = lambda value: value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    out = []
    if {'verdict', 'about', 'why'} <= keys:
        for row in rows[:50]:
            head = '%s · %s' % (say(row['verdict']).upper(), say(row['about']))
            out.append((head + '\n“%s”' % say(row['title']) if row.get('title') else head) + '\n' + say(row['why']))
    elif {'title', 'says_now', 'would_be', 'why'} <= keys:
        for row in rows[:50]:
            now = say(row['says_now']).strip();then = say(row['would_be']).strip()
            change = ('%s  →  %s' % (now, then)) if now and then and now != then else (('%s, as now' % now) if now else then)
            out.append('%s\n%s\n%s' % (say(row['title']), change, say(row['why'])))
    elif {'way', 'steps', 'kind', 'title'} <= keys:
        for row in rows[:50]:
            way = say(row['way']);far = row.get('steps') if isinstance(row.get('steps'), int) else 0
            lead = '•' if way == 'this' else ('←' if way == 'from' else '→') * max(1, min(3, far))
            line = '%s %s · %s%s' % (lead, say(row['kind']), say(row['title']), (' (%s)' % say(row['state'])) if row.get('state') else '')
            out.append(line + (' · ' + say(row['by']) if row.get('by') else ''))
        return '\n'.join(out) + ('\n… %d more rows' % (len(rows) - 50) if len(rows) > 50 else '')
    else:
        return None
    return '\n\n'.join(out) + ('\n\n… %d more rows' % (len(rows) - 50) if len(rows) > 50 else '')


def to_console(host, page, text):
    """Hand a typed line from the box to the console page it belongs to, and run it there. Only the page's own lead character
    is dropped (D3: in Shell a path such as /usr/bin/env or a pattern such as ?.txt is the shell's)."""
    console = getattr(host, 'console', None)
    if console is None:return host.shell2.run_stac(text) if page == 'stac' else None
    if console.mode != page:console.set_mode(page)  # changing page would forget an approval waiting for its second Enter
    console.open(focus=False)
    lead = {'kernel': '/', 'find': '?', 'shell': '$'}.get(page)
    console.prompt.setText(text[1:].strip() if lead and text.startswith(lead) else text);console.enter()
    if console.pending_approval:  # an approve-scope operation waits for a second Enter: the line goes back into the box
        box = host.shell2.top.box;box.setText('/' + console.pending_approval);box.setFocus()


def preview_rows(host, text, shown=4):
    """What a staC pipeline would answer, as a few quiet lines under the box. It runs through language.run, which only reads."""
    from .engine import engineering
    from .engineering_kernel import operator
    try:
        from .field_page import expand_this
        from .stac_words import command, expand, known_to
        made = command(text)
        if made is not None and made.startswith('/'):      # keeping or forgetting a word changes something: it is not previewed, it is said
            return [('section', 'PREVIEW', None), ('note', ('Ctrl+Enter keeps this word' if made.startswith('/words.keep') else 'Ctrl+Enter forgets this word'), None)]
        text = expand_this(host, made or expand(known_to(host), text))        # the owner's words, then `this`: the sheet selected in the Field
    except ValueError as exc:
        return [('section', 'PREVIEW', None), ('note', str(exc)[:110], None)]
    try:r = engineering(host.root).dispatch('language.run', {'text': text}, operator())
    except Exception as exc:r = {'ok': False, 'error': {'message': str(exc)}}
    if not r.get('ok'):return [('section', 'PREVIEW', None), ('note', 'Not yet: ' + str((r.get('error') or {}).get('message', ''))[:110], None)]
    rows = r['result']['rows']
    out = [('section', 'PREVIEW · %d ROW%s · READ ONLY' % (len(rows), '' if len(rows) == 1 else 'S'), None)]
    for row in rows[:shown]:
        line = '   '.join('%s %s' % (k, v) for k, v in row.items()) if isinstance(row, dict) else str(row)
        out.append(('note', line if len(line) < 110 else line[:108] + '…', None))
    if len(rows) > shown:out.append(('note', '… and %d more' % (len(rows) - shown), None))
    return out


KIND_SHORT = {'documents': 'DOC', 'code': 'CODE', 'boards': 'BOARD', 'images': 'IMG', 'containers': 'ARCHIVE', 'other': 'FILE'}


class ResultsPopup(QFrame):
    """The one box's results, under the box, inside the window (so typing never loses focus)."""

    def __init__(self, host, box):
        super().__init__(host);self.host = host;self.box = box;self.setObjectName('OneBoxResults');self.hide()
        layout = QVBoxLayout(self);layout.setContentsMargins(6, 6, 6, 6)
        self.list = QListWidget();self.list.setObjectName('OneBoxList');self.list.setFocusPolicy(Qt.NoFocus)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.list.setTextElideMode(Qt.ElideMiddle)  # a long pipeline is shortened, never scrolled
        self.list.itemClicked.connect(lambda item:self.activate(item));layout.addWidget(self.list)
        hint = KeyedWords(host, wrap=True, base=14);hint.setObjectName('OneBoxCaption');hint.setContentsMargins(8, 4, 8, 4);layout.addWidget(hint)
        self.hint = hint;self.actions = {}  # D3: the caption says what the keys do in the mode, in the script with its keys printed

    def show_results(self, rows):
        caption = CAPTIONS.get(getattr(self.host, 'type_target', 'slate'), CAPTIONS['slate'])
        if self.hint.note != caption:self.hint.explain(caption)
        self.list.clear();self.actions = {};first = None
        for kind, text, extra in rows:
            item = QListWidgetItem(text)
            if kind == 'note':
                item.setFlags(Qt.NoItemFlags);item.setForeground(QColor(QUIET));item.setFont(mono_font(14))
            elif kind == 'section':
                item.setFlags(Qt.NoItemFlags);item.setForeground(QColor(FAINT));font = QFont(SANS);font.setPixelSize(13);font.setWeight(QFont.Medium);font.setLetterSpacing(QFont.AbsoluteSpacing, 1.0);item.setFont(font)
            else:
                hint, fn = extra
                if hint and hint not in KEY_WORDS:item.setText(text + '      ' + hint)
                if kind == 'stac':item.setFont(mono_font(16));item.setForeground(QColor(TEAL_TEXT))
                if kind in ('ask', 'search'):item.setForeground(QColor(AMBER_TEXT))
                self.actions[id(item)] = fn;item.setData(Qt.UserRole, id(item))
                first = first or item
            self.list.addItem(item)
        if first is None:self.hide();return
        self.list.setCurrentItem(first)
        below = self.box.mapTo(self.host, self.box.rect().bottomLeft());above = self.box.mapTo(self.host, self.box.rect().topLeft())
        width = max(self.box.width(), 560);height = min(460, 24 + sum(self.list.sizeHintForRow(i) + 2 for i in range(self.list.count())) + 40)
        x = min(below.x(), max(0, self.host.width() - width - 8))
        y = below.y() + 6 if below.y() + 6 + height <= self.host.height() else max(0, above.y() - height - 6)  # at the foot, results open upward
        self.setGeometry(x, y, width, height);self.raise_();self.show()

    def move_selection(self, step):
        row = self.list.currentRow()
        for _ in range(self.list.count()):
            row = (row + step) % self.list.count()
            if self.list.item(row).flags() & Qt.ItemIsEnabled:self.list.setCurrentRow(row);return

    def activate_current(self):
        item = self.list.currentItem()
        if item is not None and self.isVisible():self.activate(item);return
        text = self.box.text().replace('\u200b', '').strip()  # Enter before the list appeared: do what its first line would do
        if not text:return
        rows = [r for r in self.box.results(text) if r[0] not in ('section', 'note')]
        if rows:self.hide();self.box.clear();rows[0][2][1]()

    def activate(self, item):
        fn = self.actions.get(item.data(Qt.UserRole))
        if fn is None:return
        self.hide();self.box.clear();self.box.clearFocus();fn()


# Library -----------------------------------------------------------------------

def library_files(host, limit=1000):
    """Every cataloged file the Office received: name, kind, delivery, its address and where its received copy lives."""
    out = []
    deliveries = (call(host, 'receiving.deliveries', {'limit': 100}) or {}).get('deliveries', [])
    for d in deliveries:
        if not d.get('accepted') or not d.get('batch'):continue
        accepted = set(d['accepted']);offset = 0
        while len(out) < limit:
            page = call(host, 'intake.items', {'namespace': d['namespace'], 'batch': d['batch'], 'limit': 200, 'offset': offset}) or {}
            items = page.get('items', [])
            for item in items:
                if item['id'] not in accepted:continue
                folder = d.get('folder') or ''
                name = item['name'][len(folder) + 1:] if folder and item['name'].startswith(folder + '/') else item['name']
                out.append({'name': name, 'kind': kind_of(name), 'delivery': d['label'], 'delivery_id': d['id'], 'address': 'intake:' + item['id'],
                            'bytes': item.get('bytes'), 'copy': str(host.root / '.ledger' / 'receiving' / d['id'] / 'delivery' / item['name']),
                            'stored_copy': str(Path(d.get('staging', '')) / item['name']), 'item_name': item['name']})
            offset += len(items)
            if not items or offset >= page.get('total', 0):break
    return out


def capture(host, text):
    """Keep a rough idea in Notes, in exactly the words it was written: no wizard, no rewording.
    The first line becomes its title; the whole text, unchanged, is its note. Returns the catalog id."""
    text = (text or '').replace('\u200b', '')
    if not text.strip():raise ValueError('Write something first')
    store = getattr(getattr(host, 'concern', None), 'store', None)
    if store is None:raise ValueError('The catalog is not available, so nothing was kept')
    first = text.strip().splitlines()[0].strip()
    ident = store.create('note', first if len(first) <= 80 else first[:79].rstrip() + '…', 'inbox')
    store.save_note(ident, text, 0)
    try:host.concern.rebuild()
    except Exception:pass  # the note is kept; the tree catches up on its next rebuild
    host.statusBar().showMessage('Kept in Notes · ' + first[:80], 5000)
    return ident


CAPTURE_HINT = 'Keep it, and it goes to Notes exactly as written'      # 0.8.0: no key is printed (the keys still work)


class CaptureBox(QWidget):
    """Jot it down: a sheet for a rough idea, kept in your own words."""

    def __init__(self, host, compact=False):
        super().__init__();self.host = host
        from PySide6.QtWidgets import QPlainTextEdit
        box = QVBoxLayout(self);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(8)
        label = role(QLabel('JOT IT DOWN'), 'section');box.addWidget(label)
        self.text = QPlainTextEdit();self.text.setObjectName('Capture');self.text.setProperty('arcReadingRole', 'prose');self.text.setAccessibleName('Jot down an idea, in your own words')
        writing_prompt(self.text, 'A rough idea, in your own words. It is kept exactly as written.');self.text.setTabChangesFocus(True)
        self.text.setMinimumHeight(round((96 if compact else 72) * scale_of(host)));self.text.setMaximumHeight(round(160 * scale_of(host)));box.addWidget(self.text);label.setBuddy(self.text)
        row = QHBoxLayout();row.setSpacing(8)
        # The hint is a note you may skip (the quiet-script rule, D1-fix): the Paper script with its keys printed; a result of
        # keeping ("Kept in Notes…") or a refusal is print (QuietWords.setText). It wraps in a narrow workspace (HATCH DESK D1a).
        self.note = role(QuietWords(host), 'quiet');self.note.explain(CAPTURE_HINT);row.addWidget(self.note, 1)
        # The word to keep it appears only once there is something to keep.
        self.keep = button('Keep it', 'primary');self.keep.clicked.connect(self.save);row.addWidget(self.keep);box.addLayout(row)
        self.keep.setVisible(False);self.text.textChanged.connect(lambda:self.keep.setVisible(bool(self.text.toPlainText().strip())))
        QShortcut(QKeySequence('Ctrl+Return'), self.text, activated=self.save)
        from .writing_marker import attach
        attach(host, self.text)  # the New Idea sheet is a yellow passage now (theme2) and opts into the writing marker (VS03)

    def save(self):
        try:capture(self.host, self.text.toPlainText())
        except ValueError as exc:self.note.setText(str(exc));return None
        self.text.clear();self.note.setText('Kept in Notes, exactly as written.')
        return True


def capture_dialog(host):
    """Ctrl Shift N, Hatch's New Idea and the capture destination: one sheet, over whatever is open; raised if it is already open."""
    from PySide6.QtWidgets import QDialog
    existing = getattr(host, '_capture_dialog', None)
    try:visible = existing is not None and existing.isVisible()
    except RuntimeError:visible = False  # the previous sheet's Qt object is gone
    if visible:
        existing.raise_();existing.activateWindow();existing.sheet.text.setFocus();return existing
    from PySide6.QtCore import Qt as _Qt
    dialog = QDialog(host);dialog.setWindowTitle('Jot it down');dialog.resize(560, 220);dialog.setAttribute(_Qt.WA_DeleteOnClose)
    box = QVBoxLayout(dialog);box.setContentsMargins(24, 20, 24, 20)
    sheet = CaptureBox(host, compact=True);box.addWidget(sheet);dialog.sheet = sheet
    sheet.keep.clicked.disconnect();sheet.keep.clicked.connect(lambda:sheet.save() and dialog.accept())
    sheet.text.setFocus();dialog.open();host._capture_dialog = dialog
    return dialog


def open_destination(host, destination):
    """Where a Library row or a command goes."""
    if destination == 'home':
        page = host.show_start()
        if hasattr(page, 'show_place'):page.show_place('today')  # UI-04: the Today row is the Finder's Today place; other places stay in its history
        return page
    if destination.startswith('library:'):return host.shell2.show_library(destination.split(':', 1)[1])
    if destination == 'capture':return capture_dialog(host)
    if destination.startswith('program:'):
        from .program_rooms_qt import show
        return show(host, destination.partition(':')[2])
    if destination == 'deployment':
        from .deployment_qt import show
        return show(host)
    if destination == 'continuing':
        from .continuing_work_qt import show
        return show(host)
    if destination == 'changes':
        from .change_sets_qt import show
        return show(host)
    if destination == 'project_desk':
        from .project_desk_qt import show
        return show(host)
    if destination == 'investigations':
        from .investigations_qt import show
        return show(host)
    if destination == 'agenda':
        from .agenda_qt import show
        return show(host)
    if destination == 'work_copy':
        from .files_qt import show
        tab = show(host);tab.work_on_copy();return tab
    if destination == 'files' or destination.startswith('files:'):
        from .files_qt import show
        return show(host, destination.partition(':')[2])
    if destination == 'documents' or destination.startswith('documents:'):
        from .document_qt import show
        return show(host, destination.partition(':')[2] or None)
    if destination.startswith('smart:'):
        from .files_qt import show
        rel = destination.partition(':')[2];tab = show(host, rel.rpartition('/')[0])
        tab.open_smart({'path': rel, 'name': rel.rpartition('/')[2]});return tab
    if destination == 'trash':
        from .files_qt import show_trash
        return show_trash(host)
    if destination == 'matrix':
        slate = host.ledger_bridge.navigation()['slate']();slate.rooms.setCurrentIndex(1);return slate
    if destination == 'project':
        from .project_context import detached
        if detached(host.root):return host.project_required('A project')
        return host.show_brain_link()
    navigation = host.ledger_bridge.navigation()
    if destination in navigation:return navigation[destination]()
    return None


from .navigator_catalog import paper_sections, FOLD_ORDER, SECTION_ROLES, shortcut_id
SECTIONS = paper_sections(KINDS)


def build_library(host):
    """The Library above the Concern catalog. Rows are 'nav_live': the Concern rebuild leaves them alone."""
    nav = host.nav
    for i in range(nav.topLevelItemCount() - 1, -1, -1):
        if nav.topLevelItem(i).data(0, Qt.UserRole + 2) == 'nav_live':nav.takeTopLevelItem(i)
    host._library_rows = {};position = 0
    def add(item):
        nonlocal position
        nav.insertTopLevelItem(position, item);position += 1
    today = QTreeWidgetItem(['Today']);today.setData(0, Qt.UserRole + 2, 'nav_live');today.setData(0, Qt.UserRole + 4, 'home')
    add(today)
    for title, rows in SECTIONS:
        header = section_row(title);add(header)
        for label, destination, icon_name, key in rows:
            row = QTreeWidgetItem([label]);row.setData(0, Qt.UserRole + 2, 'nav_live');row.setData(0, Qt.UserRole + 4, destination)
            row.setData(0, Qt.UserRole + 81, {'id': shortcut_id(title, destination, key), 'role': SECTION_ROLES[title]})
            header.addChild(row)
            if key:host._library_rows[key] = (row, label)
        header.setExpanded(True)
    concern = section_row('CONCERN');add(concern)
    host._library_sections = {header.text(0): header for header in (nav.topLevelItem(i) for i in range(nav.topLevelItemCount()))
                              if header.data(0, Qt.UserRole + 2) == 'nav_live' and not header.data(0, Qt.UserRole + 4)}
    host._library_sections['CONCERN'] = concern
    if not isinstance(nav.itemDelegate(), LibraryDelegate):nav.setItemDelegate(LibraryDelegate(nav))
    if not getattr(host, '_library_folding', False):
        host._library_folding = True;nav.itemClicked.connect(lambda item, column=0, host=host:toggle_section(host, item))
        nav.setStyleSheet('QTreeView::item {padding: 3px 8px;}')  # tighter rows: the whole Library fits more often
        timer = QTimer(nav, singleShot=True, interval=150);timer.timeout.connect(lambda host=host:fit_library(host));host._library_fit = timer
        class Resized(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Resize:timer.start()
                return False
        host._library_resized = Resized(nav);nav.viewport().installEventFilter(host._library_resized)
    refresh_library(host);QTimer.singleShot(0, lambda host=host:fit_library(host))


def toggle_section(host, item):
    """Click a section's name to fold or open it. Your choice is remembered, and the fitting never overrides it."""
    sections = getattr(host, '_library_sections', {})
    title = next((t for t, h in sections.items() if h is item), None)
    if title is None:return
    item.setExpanded(not item.isExpanded())
    host.session.state.setdefault('library_open', {})[title] = item.isExpanded()
    mark_folded(host)


def mark_folded(host):
    """A folded section still says what matters inside it: the first count one of its rows carries."""
    for title, header in getattr(host, '_library_sections', {}).items():
        counts = [header.child(i).data(0, COUNT_ROLE) for i in range(header.childCount())]
        header.setData(0, COUNT_ROLE, (next((c for c in counts if c), None) or ('%d' % header.childCount() if header.childCount() else None)) if not header.isExpanded() else None)


def fit_library(host):
    """Less scrolling: when the Library is taller than its column, the least-needed sections fold, bottom first. A section
    you opened yourself, and the one you are in, stay open."""
    nav = host.nav;sections = getattr(host, '_library_sections', {})
    if not sections:return
    chosen = host.session.state.get('library_open', {})
    for title, header in sections.items():
        if title in chosen:header.setExpanded(bool(chosen[title]))
    current = nav.currentItem();holding = current.parent() if current is not None else None
    def height():
        total, it = 0, nav.topLevelItem(0)
        while it is not None:
            total += nav.visualItemRect(it).height() or nav.sizeHintForRow(0);it = nav.itemBelow(it)
        return total
    room = nav.viewport().height()
    for title in FOLD_ORDER:
        if height() <= room:break
        header = sections.get(title)
        if header is None or title in chosen or header is holding or not header.isExpanded():continue
        header.setExpanded(False)
    mark_folded(host)


def section_row(title):
    """A section label in the Library: small, tracked, faint; it opens nothing."""
    header = QTreeWidgetItem([title]);header.setData(0, Qt.UserRole + 2, 'nav_live');header.setFlags(Qt.ItemIsEnabled)
    font = QFont(SANS);font.setPixelSize(round(13 * SECTION_SCALE[0]));font.setWeight(QFont.Medium);font.setLetterSpacing(QFont.AbsoluteSpacing, 1.2);header.setFont(0, font)
    header.setForeground(0, QColor(FAINT))
    return header


def smart_twigs(host, files_row):
    """4.6: saved questions (smart folders) at the top of Files grow as twigs under Files; each opens its answer."""
    found = [e for e in (call(host, 'files.list', {'path': ''}) or {}).get('entries', []) if e.get('kind') == 'smart'][:12]
    wanted = [e['path'] for e in found]
    if [files_row.child(i).data(0, Qt.UserRole + 4) for i in range(files_row.childCount())] == ['smart:' + w for w in wanted]:return
    files_row.takeChildren()
    for e in found:
        name = e['name'][:-len('.find')] if e['name'].endswith('.find') else e['name']
        twig = QTreeWidgetItem([name]);twig.setData(0, Qt.UserRole + 2, 'nav_live');twig.setData(0, Qt.UserRole + 4, 'smart:' + e['path'])
        twig.setToolTip(0, 'A smart folder: a saved question that finds its files when you open it');files_row.addChild(twig)
    files_row.setExpanded(bool(found))


def refresh_library(host):
    if hasattr(host,'cabinet_page') and not host.cabinet_page.using_legacy:return
    rows = getattr(host, '_library_rows', None)
    if not rows or getattr(host, '_closing', False):return
    try:
        status = call(host, 'receiving.status') or {};waiting = len(status.get('inbox_waiting') or [])
        deliveries = (call(host, 'receiving.deliveries', {'limit': 30}) or {}).get('deliveries', [])
        yours = sum(1 for d in deliveries if d['stage'] == 'REVIEWED')
        def label(key, extra):
            item, text = rows[key];item.setText(0, text);item.setData(0, COUNT_ROLE, extra or None);item.setData(0, BADGE_ROLE, key == 'inbox')
        label('inbox', str(waiting) if waiting else '');host._status_inbox = waiting
        label('deliveries', ('%d for you' % yours) if yours else (str(len(deliveries)) if deliveries else ''))
        counts = {}
        for entry in getattr(host, '_library_cache', []):counts[entry['kind']] = counts.get(entry['kind'], 0) + 1
        for key, _, _ in KINDS:label(key, str(counts.get(key, '')) if counts.get(key) else '')
        label('all', str(sum(counts.values())) if counts else '')
        brain = call(host, 'brain.status') or {}
        label('brain', {'READY': 'ready', 'MODEL_STOPPED': 'stopped', 'NO_MODEL_SELECTED': 'none yet'}.get(brain.get('state'), ''))
        matrix = (call(host, 'matrix.status') or {}).get('counts', {})
        label('matrix', ('%d worked' % matrix.get('SUCCESS', 0)) if matrix.get('SUCCESS') else '')
        lessons = call(host, 'memory.lessons', {}) or {}
        waiting_lessons = [l for l in lessons.get('lessons', []) if l.get('review') not in ('OWNER_REVIEWED_PROCEDURE',)] if isinstance(lessons, dict) else []
        label('lessons', ('%d to review' % len(waiting_lessons)) if waiting_lessons else '')
        waiting = ((call(host, 'agenda.view') or {}).get('counts') or {}).get('waiting', 0)
        label('agenda', ('%d for you' % waiting) if waiting else '')
        trash = len((call(host, 'files.trash_list') or {}).get('trash', []))
        if getattr(host, 'trash_can', None) is not None:host.trash_can.set_count(trash)
        area = (call(host, 'files.list', {'path': 'Slate'}) or {}).get('entries', [])
        label('slate_area', str(len(area)) if area else '')
        smart_twigs(host, rows['files'][0])
        copies = [c for c in (call(host, 'copies.list') or {}).get('copies', []) if c['state'] == 'WORKING']
        notable = sum(1 for c in copies if c['status'].startswith(('Ready', 'Original changed', 'Recovery', 'Original is missing')))
        label('working', ('%d to look at' % notable) if notable else (str(len(copies)) if copies else ''))
        open_ones = [i for i in (call(host, 'investigation.list') or {}).get('investigations', []) if i['state'] != 'STOPPED']
        label('investigations', ('%d open' % len(open_ones)) if open_ones else '')
        from .project_context import detached
        from . import locations
        item, _ = rows['project']
        try:value = locations.marker(host.root)
        except ValueError:value = None
        item.setText(0, 'No project attached' if detached(host.root) else ((value or {}).get('project') or (value or {}).get('name') or 'Attached project'))
        item.setData(0, COUNT_ROLE, None)
        mark_folded(host)
    except RuntimeError:
        return  # the tree was rebuilt meanwhile; the next refresh uses the new rows


class LibraryTab(QWidget):
    """Everything the Office cataloged, by kind. Open a file to read it in the universal viewer."""

    def __init__(self, host, kind='all'):
        super().__init__();self.host = host;self.kind = kind;self.setProperty('ledgerRoom', True);self.setObjectName('LibraryTab')
        from PySide6.QtWidgets import QTreeWidget
        box = QVBoxLayout(self);box.setContentsMargins(24, 18, 24, 12);box.setSpacing(12)
        head = QHBoxLayout();self.heading = role(QLabel('Library'), 'title');head.addWidget(self.heading, 1)
        head.addWidget(sentence('{receive}', {'receive': ('Receive files', lambda:host.ledger_bridge.navigation()['office']().pick_files())}))
        box.addLayout(head)
        filters = QHBoxLayout();filters.setSpacing(6);self.filters = {}
        for key, label in (('all', 'Everything'),) + tuple((k, l) for k, l, _ in KINDS):
            b = QPushButton(label.replace('&', '&&'));b.setCheckable(True);b.setProperty('arcButton', 'filter');b.clicked.connect(lambda checked=False, k=key:self.set_kind(k))
            filters.addWidget(b);self.filters[key] = b
        filters.addStretch(1)
        self.search = QLineEdit();writing_prompt(self.search, 'Filter by name');self.search.setClearButtonEnabled(True);self.search.textChanged.connect(self.fill)
        self.search.setMaximumWidth(260);filters.addWidget(self.search);box.addLayout(filters);self.search.hide()  # ? in the box finds by name
        self.table = QTreeWidget();self.table.setHeaderLabels(['Name', 'Kind', 'Delivery', 'Size']);self.table.setRootIsDecorated(False)
        self.table.setColumnWidth(0, 360);self.table.setColumnWidth(1, 150);self.table.setColumnWidth(2, 220);self.table.setAccessibleName('Cataloged files')
        self.table.itemActivated.connect(self.open_item);self.table.itemSelectionChanged.connect(self.tell_inspector);box.addWidget(self.table, 1)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu);self.table.customContextMenuRequested.connect(self.menu)
        self.empty = QLabel('Nothing here yet. Drop files on the Office, or press Receive files.');self.empty.setStyleSheet('color:%s' % QUIET);box.addWidget(self.empty)
        self.entries = [];self.reload();self.set_kind(kind)

    def title(self):return 'Library'

    def menu(self, point):
        """HATCH DESK D4: the right-click menu (workbench/context_menu.py): Open and Keep a copy in Files as before, Ask Stacy,
        Copy the name; on the empty place, Receive files (where material enters)."""
        from .context_menu import open_at
        return open_at(self.host, self.table.viewport(), point)

    def keep(self, entries):
        kept = []
        for e in entries:
            r = call_write(self.host, 'files.keep', {'delivery': e['delivery_id'], 'name': e.get('item_name') or e['name']})
            if r.get('ok'):kept.append(r['result']['path'])
            else:self.host.statusBar().showMessage((r.get('error') or {}).get('message', 'Not kept'), 7000);return
        self.host.statusBar().showMessage(('Kept in Files › ' + kept[0]) if len(kept) == 1 else 'Kept %d files in Files › Received' % len(kept), 7000)

    def info(self):return 'Cataloged files by kind'

    def reload(self):
        self.entries = library_files(self.host);self.host._library_cache = self.entries;refresh_library(self.host)

    def set_kind(self, kind):
        self.kind = kind
        for key, b in self.filters.items():b.setChecked(key == kind)
        label = dict((k, l) for k, l, _ in KINDS).get(kind, 'Everything')
        self.heading.setText('Library · ' + label);self.fill()

    def fill(self):
        from PySide6.QtWidgets import QTreeWidgetItem as Row
        from .universal_view import human
        needle = self.search.text().casefold();self.table.clear();shown = 0
        names = dict((k, l) for k, l, _ in KINDS)
        for entry in self.entries:
            if self.kind != 'all' and entry['kind'] != self.kind:continue
            if needle and needle not in entry['name'].casefold():continue
            row = Row([entry['name'], names.get(entry['kind'], 'Other'), entry['delivery'], human(entry['bytes']) if entry.get('bytes') is not None else ''])
            row.setData(0, Qt.UserRole, entry);self.table.addTopLevelItem(row);shown += 1
        self.empty.setVisible(shown == 0)

    def open_item(self, item):
        self.host.shell2.open_library_file(item.data(0, Qt.UserRole))

    def selected(self):
        item = self.table.currentItem()
        return item.data(0, Qt.UserRole) if item else None

    def inspector(self):
        entry = self.selected()
        if not entry:
            counts = {}
            for e in self.entries:counts[e['kind']] = counts.get(e['kind'], 0) + 1
            return 'Library', [('Cataloged', '%d files' % len(self.entries))] + [(l, str(counts.get(k, 0))) for k, l, _ in KINDS]
        return 'Library · ' + Path(entry['name']).name, [('Delivery', entry['delivery']), ('Address', '@' + entry['address']),
                                                         ('Read it', '@' + entry['address'] + ' | select text'), ('Open', 'Double-click to open it in the viewer.')]

    def tell_inspector(self):
        inspector = getattr(self.host, 'arc_inspector', None)
        if inspector is not None and self.host.tabs.currentWidget() is self:inspector.refresh()


# Slate, in the right panel ----------------------------------------------------------

def breakable(text):
    """Long unbroken tokens (addresses, hashes) get invisible break points, so a narrow panel can wrap them."""
    return re.sub(r'(\S{18})(?=\S)', '\\1\u200b', str(text))


def program_detail(layout, title, text):
    details = QPlainTextEdit()
    details.setReadOnly(True)
    details.setPlainText(text)
    details.setMaximumHeight(150)
    details.setAccessibleName(title)
    details.hide()
    toggle = button(title, 'quiet')
    toggle.setCheckable(True)
    toggle.toggled.connect(details.setVisible)
    layout.addWidget(toggle, 0, Qt.AlignLeft)
    layout.addWidget(details)


class Bubble(QFrame):
    def __init__(self, text='', mine=False, code=False):
        super().__init__();self.setObjectName('SlateMine' if mine else 'SlateTheirs')
        self.box = QVBoxLayout(self);self.box.setContentsMargins(12, 9, 12, 9);self.box.setSpacing(8)
        self.text = QLabel(breakable(text));self.text.setWordWrap(True);self.text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.text.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        if code:self.text.setFont(mono_font(16));self.text.setStyleSheet('color:%s' % TEAL_TEXT)
        self.box.addWidget(self.text)

    def set_text(self, text):self.text.setText(breakable(text))


from PySide6.QtCore import Signal  # noqa: E402
from PySide6.QtWidgets import QPlainTextEdit  # noqa: E402


class Composer(QPlainTextEdit):
    """Slate's composer: a sheet with room to write. Enter sends; Shift+Enter starts a new line."""
    returnPressed = Signal()

    def __init__(self):
        super().__init__();self.setTabChangesFocus(True);self.setProperty('arcReadingRole', 'prose')

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers() & Qt.ShiftModifier:self.returnPressed.emit();return
        super().keyPressEvent(event)

    def text(self):return self.toPlainText()

    def setText(self, value):
        self.setPlainText(value);self.moveCursor(self.textCursor().MoveOperation.End)


POINTING = re.compile(r"\b(this|it|its|it's|that|here|these|those)\b", re.IGNORECASE)      # the words that point at the selected sheet


def marked(layout, widget, host, glyph, align=None):
    """Put a line of her column into its layout. In Kasandra (0.8.0, the owner: "maybe icons in kasandra column if they
    look good and kool") the two lines under her face have one of Graphite's own glyphs at their left, in her cyan:
    select for This (what is open), running for Now (what runs and waits). The lines beside her face carry none: the
    face is their mark, and the room there is short. In Graphite the line stands alone, as before."""
    from . import boss_theme as _bt
    if _bt.APPEARANCE != 'kasandra':
        layout.addWidget(widget, 0, align) if align is not None else layout.addWidget(widget);return None
    from .tool_faces import icon
    side = round(17 * scale_of(host))
    mark = QLabel();mark.setObjectName('KasandraMark');mark.setFixedSize(side, side + 4);mark.setAttribute(Qt.WA_TransparentForMouseEvents)
    mark.setPixmap(icon(glyph).pixmap(side, side));mark.setAlignment(Qt.AlignTop | Qt.AlignHCenter);mark.setContentsMargins(0, 3, 0, 0)
    row = QHBoxLayout();row.setSpacing(round(7 * scale_of(host)));row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(mark, 0, Qt.AlignTop)
    if align is not None:row.addWidget(widget, 0, align);row.addStretch(1)
    else:row.addWidget(widget, 1)
    layout.addLayout(row);widget.kasandra_mark = mark
    return mark


class SlateFace(QWidget):
    """The assistant in the right panel. Her face is Stacy (12 November 2026: "Stacy should be the face of the assistant as
    communicated through the language of Stacy") and her language is staC: ask about the open item, or about the selected
    sheet of the Field; what she reads she shows as a staC line you can run, change or keep; proposals arrive as staC you run;
    your marks teach her. With no model she still answers what the records can answer."""

    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('SlateFace');self.job = None;self.pending = None;self.about = None
        outer = QVBoxLayout(self);outer.setContentsMargins(14, 10, 14, 12);outer.setSpacing(10)
        # Her face, still, in its own place (Illustrated: the portrait; ASCII: the same in characters; Clean: none), and her name, signed.
        from .boss_qt import PanelInk
        top = QHBoxLayout();top.setSpacing(12);names = QVBoxLayout();names.setSpacing(4)
        self.portrait = PanelInk(host, 'face');self.portrait.setParent(self);top.addWidget(self.portrait, 0, Qt.AlignTop)
        self.signature = pleasantry(QLabel(named('Stacy')), host, 26);names.addWidget(self.signature)
        self.model = QLabel(named('Stacy'));self.model.setWordWrap(True);self.model.setStyleSheet('color:%s' % QUIET);names.addWidget(self.model)
        # 0.6.0: her hand, in two words, under what she speaks with; a click changes it (stacy_hand: asks first, does and shows, a free hand).
        self.hand = QPushButton();self.hand.setProperty('arcButton', 'link');self.hand.setObjectName('StacyHand');self.hand.setCursor(Qt.PointingHandCursor)
        self.hand.clicked.connect(self.open_hand);names.addWidget(self.hand, 0, Qt.AlignLeft);self.show_hand()
        names.addStretch(1);top.addLayout(names, 1);outer.addLayout(top)
        self.portrait.set_available(True)      # only once it is inside this pane: shown before that, it would be a window of its own
        self.thing = None      # the thing a question is about, when the asker knows it: {'title', 'stac', 'kind'} (a sheet of the Field)
        # 0.7.0: "Brain room" and "Full chat" stood here as two links. They are behind the meters now: the Brain room on
        # GPU (the model is what the graphics processor is for), the Full chat on TXT (the text she holds). (meter_cards)
        # 0.5.3, the right pane as one view (the owner: "I don't think we need three options. Context and activity almost
        # seem like they could be merged ... talk seems like that could be merged with activity too"): under her face,
        # two lines carry what the other two views were for. This: what is open or selected, which is what "this" means
        # to her; its word opens the whole of it (Context). Now: what she is doing and what waits for you; its words open
        # the whole of that (Activity, the Agenda). Then the conversation. The three tabs above are gone.
        self.this = role(QLabel(), 'quiet');self.this.setWordWrap(True);marked(outer, self.this, host, 'select')
        # Her Agenda in one line: what she is doing now and what needs you; the words open it.
        self.agenda = role(QLabel(), 'quiet');self.agenda.setWordWrap(True);marked(outer, self.agenda, host, 'running')
        self.agenda_timer = QTimer(self);self.agenda_timer.setInterval(4000);self.agenda_timer.timeout.connect(self.show_agenda);self.agenda_timer.start()
        QTimer.singleShot(0, self.show_agenda)
        # AGENT-01: under the agenda line, what Slate is working on (five lines; Stop and Pause are words there) and the
        # owner's own records that share the open page's words (quiet connections, each dismissable).
        from .agent_qt import RelatedBlock, WorkBlock
        self.work = WorkBlock(host);outer.addWidget(self.work)
        self.related = RelatedBlock(host);outer.addWidget(self.related)
        self.scroll = QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.thread = QWidget();self.lines = QVBoxLayout(self.thread);self.lines.setContentsMargins(0, 0, 14, 0);self.lines.setSpacing(10);self.lines.addStretch(1)
        self.scroll.setWidget(self.thread);outer.addWidget(self.scroll, 1)
        self.say('Ask about what is open. In the Field, say “this” and I take the selected sheet. What I read, I show as a line you can run yourself.')
        self.input = Composer();self.input.setObjectName('SlateInput');writing_prompt(self.input, 'Ask about the open item, or anything')
        self.input.returnPressed.connect(self.send);self.input.setAccessibleName(named('Message Stacy'));self.input.setMinimumHeight(round(112 * scale_of(host)));self.input.setMaximumHeight(round(144 * scale_of(host)));outer.addWidget(self.input)
        hint = role(QLabel('Write in your own words; finishing the line sends it'), 'quiet');hint.setWordWrap(True);outer.addWidget(hint)  # 4.1: Enter is the send; no button
        quiet_script(hint)  # a note you may skip: the Paper script (the quiet-script rule)
        self.input_hint = hint  # with the typing bar, both are hidden: you write to Slate at the foot of the window
        self.timer = QTimer(self);self.timer.setInterval(800);self.timer.timeout.connect(self.poll)

    def this_is(self):
        """The name of what "this" means to her now: the page open in the centre, or the sheet selected in the Field."""
        host = self.host
        try:
            if getattr(host, '_field_active', False):
                chosen = host.field_page.view.selected()
                return (chosen.title if chosen is not None else ''), 'selected in the Field'
            bar = getattr(host, 'centre_bar', None)
            if bar is not None and not bar.isHidden() and getattr(bar, '_name', ''):return bar._name, 'open'
        except Exception:  # noqa: BLE001 - a name is never worth an error
            pass
        return '', ''

    def show_this(self):
        from html import escape
        name, how = self.this_is();shell = getattr(self.host, 'shell2', None)
        if not name:
            if self.this.text() != 'This: nothing is open.':
                self.this.setText('This: nothing is open.');self.this.setProperty('said', '')      # so the same thing, opened again, is said again
            return
        name = name.replace('{', '(').replace('}', ')')
        said = 'This: %s · {more}' % escape(name if len(name) <= 46 else name[:45] + '…')
        if self.this.property('said') == said:return
        self.this.setProperty('said', said)
        sentence(said, {'more': ('more', lambda: shell.show_context_face() if shell is not None else None)}, self.this)
        self.this.setToolTip(named('What “this” means to Stacy now: %s, %s. The word opens everything Graphite knows about it.') % (name, how))

    def show_agenda(self):
        self.show_this()
        if not self.isVisible() and self.agenda.text():return
        from .agenda_qt import summary
        found = summary(self.host);shell = getattr(self.host, 'shell2', None)
        if not found:self.agenda.hide();return
        text, waiting = found
        sentence('Now: ' + text + ' · {activity}', {'waiting': ('%d waiting for you' % waiting, lambda:open_destination(self.host, 'agenda')),
                                     'open': ('open', lambda:open_destination(self.host, 'agenda')),
                                     'activity': ('activity', lambda: shell.show_operations_face() if shell is not None else None)}, self.agenda);self.agenda.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.pending is not None:
            review = self.pending.findChild(QPushButton, 'ProgramReviewRun')
            if review is not None and review.isEnabled():
                QTimer.singleShot(30, self, lambda:self.scroll.ensureWidgetVisible(review, 12, 24))

    # conversation ---------------------------------------------------------------
    KEEP_BUBBLES = 8

    def add(self, widget):
        self.lines.insertWidget(self.lines.count() - 1, widget);self.fold_earlier()
        QTimer.singleShot(0, self.fold_earlier);QTimer.singleShot(120, self.fold_earlier)      # again once the card has its rows
        QTimer.singleShot(30, lambda:self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))
        return widget

    def fold_earlier(self):
        """Less scrolling: the latest exchanges stay in view; earlier ones fold behind one word, until you ask for them."""
        fold = getattr(self, 'fold', None)
        items = [self.lines.itemAt(i).widget() for i in range(self.lines.count())]
        items = [w for w in items if w is not None and w is not fold]
        if getattr(self, 'unfolded', False):return
        # 0.8.0 (the owner: "if we can really try to eliminate or reduce [scrolling] as much as possible"): the latest
        # exchanges that fit in the pane's height stay in view, at most KEEP_BUBBLES; the latest one always does.
        room = max(160, self.scroll.viewport().height() - 24);width = max(120, self.thread.width() - 14);used = 0;kept = 0
        for w in reversed(items):
            if kept >= self.KEEP_BUBBLES:break
            box = w.layout()
            tall = box.totalHeightForWidth(width) if box is not None and box.hasHeightForWidth() else w.sizeHint().height()
            if kept and used + tall > room:break
            used += tall + self.lines.spacing();kept += 1
        if kept >= len(items):return
        hidden = items[:-kept]
        for w in hidden:w.hide()
        if fold is None:self.fold = fold = QLabel();self.lines.insertWidget(0, fold)
        sentence('{show}', {'show': ('%d earlier · show them' % len(hidden), self.unfold)}, fold);fold.show()

    def unfold(self):
        self.unfolded = True
        for i in range(self.lines.count()):
            w = self.lines.itemAt(i).widget()
            if w is not None:w.show()
        if getattr(self, 'fold', None) is not None:self.fold.hide()

    def say(self, text):return self.add(Bubble(text))

    def mine(self, text, code=False):
        # The bubble's text may shrink to wrap, so it needs a share of the row, or it collapses to nothing.
        bubble = Bubble(text, mine=True, code=code);row = QHBoxLayout();row.addStretch(1);row.addWidget(bubble, 5)
        holder = QWidget();holder.setLayout(row);row.setContentsMargins(30, 0, 0, 0);self.add(holder);return bubble

    def send(self):
        text = self.input.text().replace('\u200b', '').strip()
        if text:self.input.clear();self.ask(text)

    def thing_asked_about(self, text):
        """The thing this question is about, when it is known exactly: the sheet the owner chose "Ask Stacy about this" on (its
        name is in the question), or the sheet selected in the Field while the Field is in front and the question points at it
        (this, it, that, here, these). Anything else typed in the Field goes the ordinary way. None otherwise."""
        thing, self.thing = self.thing, None
        if thing and thing.get('title') and thing['title'] in text:return thing
        view = getattr(getattr(self.host, 'field_page', None), 'view', None)
        chosen = view.selected() if view is not None and getattr(self.host, '_field_active', False) else None
        if chosen is not None and chosen.stac and POINTING.search(text):
            from .field_page import thing_of
            return thing_of(self.host, chosen)
        return None

    def answer_in_stac(self, thing, intro):
        """Stacy's own way of answering: the staC line that reads the thing, said, then run, with what the records answered.
        It is a read through the Kernel like any other; a refusal is said as one. The line can go to the writing strip, be
        watched or kept, and a table of rows can be saved as a sheet."""
        from .engine import engineering
        from .engineering_kernel import operator
        from .office_building_qt import readable_result
        from .field_do import call as line_call
        line = thing['stac'];operation, arguments = line_call(line)
        card = self.say(intro)
        # A stage a line, as her rail in the Field shows it, with long record numbers shortened for the eye as the rail does.
        # The line itself stays exact: it is what runs, what "in the line" gives, and the label's tooltip.
        code = QLabel(breakable(re.sub(r'([0-9a-f]{6})[0-9a-f]{20,}', '\\1…', line).replace(' | ', '\n| ')));code.setTextFormat(Qt.PlainText);code.setWordWrap(True);code.setFont(mono_font(15))
        code.setToolTip(line)
        code.setStyleSheet(bt.line_sheet());code.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        code.setTextInteractionFlags(Qt.TextSelectableByMouse);code.setAccessibleName('The line: ' + line)
        answer_first = bool(thing.get('whole'))       # when the rows are the whole answer (a doubt, a what-if, a brief), they are read first and the line that read them comes after
        if not answer_first:card.box.addWidget(code)
        r = engineering(self.host.root).dispatch(operation, arguments, operator())
        rows = (r['result'].get('rows') or []) if r.get('ok') and isinstance(r.get('result'), dict) else []
        if r.get('ok') and rows and all(isinstance(row, dict) for row in rows):  # a row a block, a field a line; what is empty is not said
            said = '\n\n'.join('\n'.join('%s: %s' % (key, value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))[:400]
                                           for key, value in row.items() if value not in (None, '', [], {})) for row in rows[:50])
            if len(rows) > 50:said += '\n… %d more rows' % (len(rows) - 50)
        else:
            said = (readable_result(r['result']) if isinstance(r['result'], dict) else str(r['result'])[:2000]) if r.get('ok') \
                else 'The records did not answer: ' + r['error']['message']
            if r.get('ok') and said == 'Done.' and isinstance(r['result'], dict):      # a read whose answer is a record, not rows: the record itself, in short
                said = json.dumps(r['result'], indent=1, ensure_ascii=False, default=str)[:1500]
        shown = said;shaped = shaped_rows(rows) if r.get('ok') else None
        if shaped is not None:                # a doubt, a what-if, a trace: each row a few short lines, made for this column
            shown = shaped
        elif r.get('ok') and rows and all(isinstance(row, dict) and len(row) == 1 for row in rows):
            # Rows of one field are lines of writing (a page's words, a brief): each on its own line, with nothing in front of it.
            shown = '\n'.join(str(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))[:600] for row in rows[:120] for value in row.values())
            if len(rows) > 120:shown += '\n… %d more lines' % (len(rows) - 120)
        elif r.get('ok') and len(rows) > 1 and all(isinstance(row, dict) and len(row) >= 3 for row in rows):
            # Several rows of several fields read better as lines than as blocks: the fields once, then a row a line.
            # (What the model is given stays field by field: card.said.)
            # A field is cut where a table would run away, and the cut is marked. Rows that are whole sentences (a doubt's reason)
            # are what the owner came to read, so they are given their length.
            keys = list(rows[0]);text = lambda value:value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            cut = 400 if thing.get('whole') else 120
            short = lambda value:value if len(value) <= cut else value[:cut - 1].rstrip() + '…'
            shown = ' · '.join(keys) + '\n' + '\n'.join(' · '.join(short(str(text(row.get(key, '')))) or '—' for key in keys) for row in rows[:50])
            if len(rows) > 50:shown += '\n… %d more rows' % (len(rows) - 50)
        answer = QLabel(breakable(shown));answer.setTextFormat(Qt.PlainText);answer.setWordWrap(True)
        answer.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);answer.setTextInteractionFlags(Qt.TextSelectableByMouse);card.box.addWidget(answer)
        if answer_first:
            code.setFont(mono_font(13));card.box.addWidget(code)
        from .context_menu import inspect_in_line
        words = {'line': ('in the line', lambda p=line:inspect_in_line(self.host, p)), 'watch': ('watch it', lambda p=line:self.watch(p)),
                 'keep': ('add to the Agenda', lambda p=line:self.keep_in_agenda(p))}
        if rows:words['save'] = ('save as a sheet', lambda p=line, rs=rows:self.save_rows(p, rs))
        card.box.addWidget(sentence('{line}  ·  {watch}  ·  {keep}' + ('  ·  {save}' if rows else ''), words))
        card.stac = line;card.answered = bool(r.get('ok'));card.said = said
        QTimer.singleShot(60, lambda:self.scroll.verticalScrollBar().setValue(max(0, card.y() - 8)))      # her answer from its first line, not its last
        return card

    # ---- doing: the steps the records offer for a thing (workbench/field_do.py), said and carried out here ---------------------
    def say_steps(self, title, steps, take):
        """What can be done about a thing: each step a word to choose, numbered as the Field numbers them. `take(n)` takes one."""
        from .field_page import _waits
        asks = [step.kind == 'write' and _waits(self.host, step) for step in steps[:9]];writes = [step.kind == 'write' for step in steps[:9]]
        rule = ('' if not any(writes) else ' One that changes something asks first.' if asks == writes else
                ' A step marked “asks first” waits for you; any other that changes something I do at once and show.')
        card = self.say('What can be done about “%s”. A number in the Field takes a step, or choose it here.%s' % (title, rule))
        for n, step in enumerate(steps[:9]):
            words = '%d  %s' % (n + 1, step.words) + ('  ·  asks first' if asks[n] else '')
            card.box.addWidget(sentence('{go}', {'go': (words, lambda n=n, line=step.line:take(n, line))}))      # the word takes this step, not whatever stands at its number later
        card.steps = steps
        QTimer.singleShot(60, lambda:self.scroll.verticalScrollBar().setValue(max(0, card.y() - 8)))
        return card

    def stage(self, title, step, done=None, asked=False, word=''):
        """A step that changes something: what it does, what it leaves behind and the exact line. `done(ok, result)` is told
        how it went, so the Field can read the records again.

        Until 0.5.3 every such step waited here for the owner's Approve. Since 0.6.0 a change the owner asked for (`asked`:
        "set B3 to 300" said to her, a step taken from her list) follows her hand (stacy_hand): with the dial at Do and
        show or Free hand, and the operation hers to do, she does it at once, says what she did, writes it in her trail
        and offers one Undo where it can be taken back exactly. A step that was only offered (the brief's "keep it as a
        page") still waits, and so does anything that cannot be undone. `card.ran` is None while it waits."""
        from . import stacy_hand
        from .context_menu import inspect_in_line
        from .field_do import call as line_call
        try:operation, arguments = line_call(step.line)
        except Exception:  # noqa: BLE001 - a line she cannot read is never hers to run; it waits, and Approve says why it is refused
            operation, arguments = '', {}
        place = stacy_hand.level(self.host)
        mine = bool(asked and operation and stacy_hand.hers(place, step.scope, operation, arguments))
        if mine:lead = 'For “%s”: %s.' % (title, step.words[:1].lower() + step.words[1:])
        elif asked and place != 'ask':
            lead = 'For “%s”: %s. This waits for you: %s.' % (title, step.words[:1].lower() + step.words[1:], stacy_hand.why_waits(place, step.scope, operation, arguments))
        else:lead = 'For “%s”: %s. This changes something, so it waits for you.' % (title, step.words[:1].lower() + step.words[1:])
        card = self.say(lead)
        if step.why:
            why = QLabel(breakable(step.why[:1].upper() + step.why[1:] + '.'));why.setWordWrap(True);why.setStyleSheet('color:%s' % QUIET)
            why.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(why)
        code = QLabel(breakable(bt.eye(step.line)));code.setTextFormat(Qt.PlainText);code.setWordWrap(True);code.setFont(mono_font(15));code.setToolTip(step.line)
        code.setStyleSheet(bt.line_sheet());code.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        code.setTextInteractionFlags(Qt.TextSelectableByMouse);code.setAccessibleName('The line: ' + step.line);card.box.addWidget(code)
        row = QHBoxLayout();run = button('Approve', 'stac');run.setObjectName('StagedRun');row.addWidget(run)
        run.setToolTip('Apply this change. Nothing is changed until you do; in the Field, G does the same')
        row.addWidget(sentence('{line}', {'line': ('in the line', lambda:inspect_in_line(self.host, step.line))}));row.addStretch(1);card.box.addLayout(row)
        card.step = step;card.run = run;card.ran = None;card.hers = mine;card.word = word;card.title = title;card.row = row;card.entry = None
        QTimer.singleShot(60, lambda:self.scroll.verticalScrollBar().setValue(max(0, card.y() - 8)))
        if mine:
            run.hide()                          # nothing waits: she does it now
            self.run_staged(card, done)
            return card
        approve_button(run, self.host)          # it waits for the owner: the Field's own Approve, lit in amber
        run.clicked.connect(lambda:self.run_staged(card, done))
        return card

    def run_staged(self, card, done=None):
        from .engine import engineering
        from .engineering_kernel import operator
        from .field_do import call as line_call
        if card.ran is not None:return           # one go, one run
        try:
            operation, arguments = line_call(card.step.line)
            r = engineering(self.host.root).dispatch(operation, arguments, operator())
        except Exception as exc:  # noqa: BLE001 - a line that cannot be run is said as a refusal, never raised into the window
            r = {'ok': False, 'error': {'message': str(exc)[:300]}}
        card.ran = bool(r.get('ok'));card.run.setEnabled(False);card.run.setText('Approved' if card.ran else 'Refused')
        from .boss_qt import waits
        waits(card.run, self.host, False)        # it no longer waits
        from .kasandra_art import note_outcome
        note_outcome(self.host, card.ran)        # Kasandra puts her pencil down, or checks the cable
        if card.ran:
            result = r['result'] if isinstance(r['result'], dict) else {}
            if isinstance(result.get('document'), dict) and result['document'].get('title'):said = 'Done: “%s”.' % result['document']['title']
            elif isinstance(result.get('words'), str) and result['words']:said = 'Done. ' + result['words']
            elif isinstance(result.get('changed'), list):said = 'Done: %s.' % ('nothing had changed' if not result['changed'] else '%d changed' % len(result['changed']))
            elif isinstance(result.get('ran'), list):said = 'Done: %d check%s ran%s.' % (len(result['ran']), '' if len(result['ran']) == 1 else 's', (': ' + ', '.join(str(x.get('outcome')) for x in result['ran'][:6])) if result['ran'] else '')
            elif isinstance(result.get('trashed'), str):said = 'Done: “%s” is in the Trash, which gives it back.' % result['trashed']
            elif result.get('state') == 'STARTED' and result.get('pid'):said = 'Done: its own window was started on “%s”.' % str(result.get('path') or card.title)
            elif isinstance(result.get('path'), str) and result.get('kind'):said = 'Done: “%s” is in Files.' % result['path']
            elif isinstance(result.get('title'), str) and result['title']:said = 'Done: “%s”.' % result['title']
            else:said = 'Done.'
        else:
            said = 'It was refused, and nothing was changed: ' + str((r.get('error') or {}).get('message'))[:400]
        note = QLabel(breakable(said));note.setWordWrap(True);note.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(note)
        if getattr(card, 'hers', False):         # her own act: one line in her trail, and one Undo where it can be taken back exactly
            from . import stacy_hand
            back = stacy_hand.takes_back(operation, arguments, r.get('result')) if card.ran else ''
            guards = stacy_hand.guard(operation, arguments, r.get('result')) if card.ran else []
            card.entry = stacy_hand.record(self.host.session.state, '%s · “%s”' % (card.step.words, card.title), card.step.line, back, card.word, card.ran, guards=guards)
            back = card.entry['undo']                # only a line an Undo may run is kept (stacy_hand.undo_allowed)
            try:self.host.session.save()
            except Exception:  # noqa: BLE001 - the act is done and said; a trail that could not be written is not worth an error
                pass
            if back:
                undo = button('Undo', 'stac', 'Put it back as it was');undo.setObjectName('StagedUndo');card.back = undo;card.undone = None
                undo.clicked.connect(lambda:self.undo_staged(card, done));card.row.insertWidget(0, undo)
            elif card.ran and not operation.startswith('programs.'):      # opening a program made nothing: there is nothing to take back
                kept = QLabel('There is no exact Undo for this: what it made is kept beside what was there.');kept.setWordWrap(True);kept.setStyleSheet('color:%s' % FAINT)
                kept.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(kept)
        if done is not None:done(card.ran, r.get('result') if card.ran else None)

    def run_line(self, line):
        """One line through the Kernel with the owner's authority: the answer, or a refusal in the same shape."""
        from .engine import engineering
        from .engineering_kernel import operator
        from .field_do import call as line_call
        try:
            operation, arguments = line_call(line)
            return engineering(self.host.root).dispatch(operation, arguments, operator())
        except Exception as exc:  # noqa: BLE001 - said as a refusal, never raised into the window
            return {'ok': False, 'error': {'message': str(exc)[:300]}}

    def undo_staged(self, card, done=None):
        """Undo on one of her acts: the line that puts it back as it was, once. If what she changed was changed again since,
        the Kernel refuses and nothing is touched."""
        from . import stacy_hand
        if getattr(card, 'undone', None) is not None or not card.entry or not card.entry.get('undo'):return
        changed = self.changed_since(card.entry)
        r = {'ok': False, 'error': {'message': changed}} if changed else self.run_line(card.entry['undo'])
        card.undone = bool(r.get('ok'));card.back.setEnabled(False);card.back.setText('Undone' if card.undone else 'Not undone')
        from .kasandra_art import note_outcome
        note_outcome(self.host, card.undone)
        if card.undone:
            stacy_hand.taken_back(self.host.session.state, card.entry)
            result = r['result'] if isinstance(r.get('result'), dict) else {}
            said = 'Taken back. ' + str(result.get('words') or ('“%s” is in the Trash, which gives it back.' % result['trashed'] if isinstance(result.get('trashed'), str) else ''))
        else:
            said = 'It could not be taken back, and nothing was changed: ' + str((r.get('error') or {}).get('message'))[:400]
        try:self.host.session.save()
        except Exception:  # noqa: BLE001
            pass
        note = QLabel(breakable(said.strip()));note.setWordWrap(True);note.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(note)
        if card.undone and done is not None:done(True, r.get('result'))

    def changed_since(self, entry):
        """Why an Undo must not run, in words, or '' when it may. An Undo is one of the two lines her rule writes and no
        other (stacy_hand.undo_allowed); and what she made must still be as she made it: a file still holding exactly her
        words, a folder still holding exactly what she put in it. Otherwise it is the owner's work now, and stays."""
        import hashlib
        from . import files_service, stacy_hand
        from .engine import engineering
        guards = entry.get('guard') or []
        if not stacy_hand.undo_allowed(entry.get('undo'), guards):return 'that is not a line I may undo with'
        if not guards:return ''                    # a number set back names the revision it expects: the Kernel is its guard
        try:
            kernel = engineering(self.host.root)
            for g in guards:
                path = files_service.resolve(kernel, g['path'])
                if 'sha256' in g:
                    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != g['sha256']:
                        return '“%s” was changed after I made it, so it is yours now and I leave it. Move it to the Trash yourself if you want it gone' % g['path']
                elif not path.is_dir() or sum(1 for p in path.iterdir() if not files_service.machine(p)) != g['items']:
                    return '“%s” no longer holds just what I put in it, so it is yours now and I leave it. Move it to the Trash yourself if you want it gone' % g['path']
        except (OSError, ValueError) as exc:
            return 'what I made is no longer where I made it (%s)' % str(exc)[:120]
        return ''

    def show_hand(self):
        """Her hand, in two words under what she speaks with."""
        from . import stacy_hand
        place = stacy_hand.level(self.host)
        self.hand.setText(stacy_hand.SAYS[place]);self.hand.setAccessibleName(named("Stacy's hand: ") + dict(stacy_hand.LEVELS)[place])
        self.hand.setToolTip(named('How far Stacy acts by herself: %s. Click to change it.') % dict(stacy_hand.LEVELS)[place])

    def open_hand(self):
        menu = hand_menu(self.host, self)
        try:
            from .tool_faces import dress
            dress(menu)
        except Exception:  # noqa: BLE001 - a menu without its glyphs is still the menu
            pass
        menu.popup(self.hand.mapToGlobal(self.hand.rect().bottomLeft()));self._hand_menu = menu

    def say_trail(self):
        """What she did by herself, the latest first, each with its Undo where one is left."""
        from . import stacy_hand
        acts = stacy_hand.trail(self.host.session.state)
        card = self.say('What I did by myself, the latest first:' if acts else 'I have not done anything by myself yet. With my hand at “Do and show”, a change you ask me for is done at once and listed here.')
        marks = {'done': '', 'undone': ' · taken back', 'refused': ' · refused, nothing changed'}
        for entry in acts[:12]:
            line = QLabel(breakable('%s  %s%s' % (entry['at'], entry['words'], marks.get(entry['state'], ''))));line.setWordWrap(True)
            line.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(line)
            if entry.get('word'):
                word = QLabel(breakable('at your word: “%s”' % entry['word']));word.setWordWrap(True);word.setStyleSheet('color:%s' % FAINT)
                word.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(word)
            if entry['state'] == 'done' and entry.get('undo'):
                card.box.addWidget(sentence('{undo}', {'undo': ('Undo this', lambda entry=entry:self.undo_entry(entry))}))
        if len(acts) > 12:card.box.addWidget(QLabel('… and %d before them' % (len(acts) - 12)))
        return card

    def undo_entry(self, entry):
        """Undo from the trail: the same line, once."""
        from . import stacy_hand
        if entry.get('state') != 'done' or not entry.get('undo'):return self.say('That one has already been taken back.')
        changed = self.changed_since(entry)
        r = {'ok': False, 'error': {'message': changed}} if changed else self.run_line(entry['undo'])
        if r.get('ok'):
            stacy_hand.taken_back(self.host.session.state, entry)
            result = r['result'] if isinstance(r.get('result'), dict) else {}
            card = self.say(('Taken back: %s. ' % entry['words']) + str(result.get('words') or ('“%s” is in the Trash, which gives it back.' % result['trashed'] if isinstance(result.get('trashed'), str) else '')))
            page = getattr(self.host, 'field_page', None)
            if page is not None:
                try:page.refresh(force=True)
                except Exception:  # noqa: BLE001 - the change is undone; the Field reads again on its next look
                    pass
        else:
            card = self.say('It could not be taken back, and nothing was changed: ' + str((r.get('error') or {}).get('message'))[:400])
        try:self.host.session.save()
        except Exception:  # noqa: BLE001
            pass
        return card

    def say_always(self):
        """What asks on every place of the dial, and the Terminal commands that are hers."""
        from . import stacy_hand
        card = self.say('Wherever my hand is set, these wait for you, because they cannot be undone:')
        for _, why in stacy_hand.ALWAYS_ASKS:
            line = QLabel(breakable('· ' + why[:1].upper() + why[1:]));line.setWordWrap(True);line.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(line)
        more = QLabel(breakable('In the Terminal I run by myself only commands that read and change nothing: %s and the like, one at a time, with nothing piped or redirected. '
                                'Any other command is put in the line for you.' % ', '.join(stacy_hand.TERMINAL_READS[:9])))
        more.setWordWrap(True);more.setStyleSheet('color:%s' % QUIET);more.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(more)
        return card

    def start_asked(self, text):
        """“Start a Godot project called Lander”, “get me started in Godot”: a starting point in another program (the owner,
        13 November 2026: "get me started on a project in a program that I may not be particularly familiar with"). She
        makes a folder in Files with the smallest project that runs, written for the Godot on this computer, and a page of
        first steps; the Godot room's own read then says what it is; and opening it in Godot is put up as a step, which
        waits for Approve unless her hand is free. One act, one line in her trail, one Undo (the folder to the Trash).
        True when the words were such a request."""
        from . import stacy_hand, stacy_start
        from .field_do import Step, op
        asked = stacy_start.asked(text)
        if asked is None:return False
        program, name = asked;folder = stacy_start.folder_name(name)
        self.thing = None;self.mine(text)
        if stacy_start.reserved(folder):
            self.say('“%s” is a name Graphite keeps for a folder of its own. Give the project another: start a Godot project called …' % folder);return True
        if self.run_line(op('files.get', path=folder)).get('ok'):
            self.say('There is already something called “%s” in Files, and I do not write over what is there. Give it another name: start a Godot project called …' % folder);return True
        tool = stacy_start.godot_tool();files = stacy_start.start_files(name, tool)
        holder = type('Started', (), {'title': folder})()
        parts = [(holder, Step('Make the folder', 'write', op('files.mkdir', path='', name=folder), '', 'execute'))]
        parts += [(holder, Step('Write %s' % file, 'write', op('files.write', path=folder + '/' + file, text=words), '', 'execute')) for file, words in files]
        mine = stacy_hand.level(self.host) != 'ask' and all(stacy_hand.hers(stacy_hand.level(self.host), 'execute', line.split(' ', 1)[0][1:]) for line in (step.line for _, step in parts))
        holding = []
        done = lambda results:self.started(holding[0], name, folder, tool, results, text.strip())
        card = self.say_plan(parts, done=done, hers=mine, word=text.strip(), brief=True,
                             title='To start “%s” in Godot %d I make a folder in Files with the smallest project that runs, and a page of first steps.' % (name, tool['major']))
        card.one_entry = True;holding.append(card)
        if mine:self.run_plan(card, done)
        return True

    def started(self, card, name, folder, tool, results, word):
        """After the starting files were written: one line in her trail with one Undo, what the Godot room reads the project
        as, the step that opens it in Godot, and the ways into it from here."""
        from . import stacy_hand
        from .engine import engineering
        from .field_do import Step, op
        went = sum(1 for _, ok, _ in results if ok)
        if went < len(card.plan):
            self.made_done(False, None)
            if not went:                           # the first step was refused: this start made nothing
                self.say('Nothing was made: the folder “%s” could not be made (%s).' % (folder, str(results[0][2])[:160] if results else 'refused'));return
            if card.hers:                          # an act of hers that stopped part-way is still a line in her trail; it has no Undo
                stacy_hand.record(self.host.session.state, 'Started a Godot %d project and stopped part-way · “%s”' % (tool['major'], folder), card.plan[0][1].line, '', word, True)
                try:self.host.session.save()
                except Exception:  # noqa: BLE001
                    pass
            self.say('I stopped at the step that was refused, after %d of %d. What this start made is in “%s” in Files; move that folder to the Trash if you do not want it.' % (went, len(card.plan), folder));return
        if card.hers:
            undo = '/files.trash ' + json.dumps({'path': folder}, ensure_ascii=False, separators=(', ', ': '))
            import hashlib
            wrote = [(json.loads(step.line.split(' ', 1)[1])['path'], json.loads(step.line.split(' ', 1)[1])['text']) for _, step in card.plan[1:]]
            guards = [{'path': folder, 'items': len(wrote)}] + [{'path': path, 'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()} for path, text in wrote]
            card.entry = stacy_hand.record(self.host.session.state, 'Started a Godot %d project · “%s”' % (tool['major'], folder), card.plan[0][1].line, undo, word, True, guards=guards)
            back = button('Undo', 'stac', 'Move the whole folder to the Trash, which gives it back, while it is still as I made it');back.setObjectName('StagedUndo');card.back = back;card.undone = None
            back.clicked.connect(lambda:self.undo_staged(card, self.made_done));card.row.insertWidget(0, back)
            try:self.host.session.save()
            except Exception:  # noqa: BLE001 - the project is made and said
                pass
        self.made_done(True, None)
        project = folder + '/project.godot'
        r = self.run_line(op('programs.godot.inspect', path=project))
        result = r['result'] if r.get('ok') and isinstance(r.get('result'), dict) else None
        root = None
        try:
            from . import files_service
            root = files_service.root(engineering(self.host.root))
        except Exception:  # noqa: BLE001 - without the folder's place the links are left out; the project is in Files
            pass
        def show(file):
            from .work_location import navigate
            try:navigate(self.host, str(root / folder / file))
            except Exception as exc:  # noqa: BLE001 - said, never raised into the window
                self.host.statusBar().showMessage(str(exc), 8000)
        said = ('“%s” is in Files and runs as it is. ' % folder) + (
            'The Godot room reads it as the project “%s”, main scene %s. ' % (result.get('title'), str(result.get('main_scene') or 'not set').replace('res://', '')) if result else
            'The Godot room could not read it: %s. ' % str((r.get('error') or {}).get('message'))[:200])
        if result and result.get('state') != 'READY':
            said += ('Godot is not on this computer (I looked for godot4, godot and godot3), so I cannot open it there yet. On Debian it is the package godot3, '
                     'which is what I wrote these files for. Once it is installed, Apps ▸ Godot opens this project.')
        after = self.say(said)
        if root is not None:
            after.box.addWidget(sentence('{steps}  ·  {script}  ·  {room}', {
                'steps': ('Read the first steps', lambda:show('START_HERE.md')), 'script': ('Read main.gd here', lambda:show('main.gd')),
                'room': ('The Godot room', lambda:open_destination(self.host, 'program:godot'))}))
        if result and result.get('state') == 'READY' and result.get('sha256'):
            step = Step('Open it in Godot', 'write', op('programs.godot.open', path=project, expected_sha256=result['sha256']),
                        "Godot's own window opens on this project, in its editor", 'approve')
            self.stage(folder, step, done=None, asked=True, word=word)

    def made_asked(self, text):
        """“Make a folder called Bracket”, “write a file called plan.txt saying …”, “start a page called Bench plan”: an
        artifact asked of her (the owner: "an artifact is made just as if I had saved a file"). It goes through the same
        operation the owner's own New Folder, save and New Document use, follows her hand (done at once, or waiting for
        Approve), and is marked as hers where the records have a place for it. She never writes over a file by herself.
        True when the words were such a request."""
        from . import stacy_hand
        from .field_do import Step, op
        asked = stacy_hand.made(text)
        if asked is None:return False
        kind, name, words = asked
        self.thing = None;self.mine(text)
        if kind in ('file', 'folder'):
            from .stacy_start import reserved
            if reserved(name):
                self.say('“%s” begins with a name Graphite keeps for a folder of its own. Give it another name.' % name);return True
            if self.run_line(op('files.get', path=name)).get('ok'):
                self.say('There is already something called “%s” in Files. I do not write over what is there by myself: say another name.' % name);return True
            parent, _, leaf = name.rpartition('/')
            step = (Step('Make a folder called “%s”' % name, 'write', op('files.mkdir', path=parent, name=leaf), 'a new, empty folder in Files; Undo moves it to the Trash', 'execute') if kind == 'folder' else
                    Step('Make a file called “%s”' % name, 'write', op('files.write', path=name, text=words), 'a new file in Files with those words; Undo moves it to the Trash', 'execute'))
            title = 'Files'
        elif kind == 'page':
            step = Step('Start a page called “%s”' % name, 'write', op('documents.create', title=name, text=words, origin='SLATE'),
                        'a page in Documents and on the Field, marked as started by me', 'execute');title = 'Documents'
        else:
            step = Step('Keep a note: “%s”' % name, 'write', op('ideas.capture', text=name + ('\n\n' + words if words else ''), origin='SLATE'),
                        'a note in Notes, marked as kept by me', 'execute');title = 'Notes'
        self.stage(title, step, done=self.made_done, asked=True, word=text.strip())
        return True

    def made_done(self, ok, result):
        """After an artifact of hers was made or taken back: the tree and the Field read again, so it is where the owner's own would be."""
        host = self.host
        for look in (lambda:host.concern.rebuild(), lambda:host.field_page.refresh(force=True), lambda:host.field_page.view.update()):
            try:look()
            except Exception:  # noqa: BLE001 - the thing is made; a view that could not be read again catches up on its next look
                pass

    def run_asked(self, text):
        """“run df -h”, “in the terminal: ls Documents”: a Terminal command asked of her. One that only reads is hers to run
        (stacy_hand.terminal_hers) unless her hand is at Ask first; any other is put in the line, with Terminal chosen, for
        the owner to run. True when the words were such a request."""
        from . import stacy_hand
        named = re.match(r'^\s*(?:in|on)\s+the\s+terminal[,:]?\s*(?:run\s+)?(.+)$', text, re.IGNORECASE | re.DOTALL)
        plain = re.match(r'^\s*(?:run\s+|\$\s*)(.+)$', text, re.IGNORECASE | re.DOTALL)
        command = (named or plain).group(1).strip() if (named or plain) else ''
        if not command or (not named and not stacy_hand.terminal_hers(command)):return False      # "run the numbers again" is not a command
        self.thing = None;self.mine(text)
        bar = getattr(self.host, 'type_bar', None)
        if stacy_hand.terminal_hers(command) and stacy_hand.level(self.host) != 'ask':
            console = getattr(self.host, 'console', None)
            if console is None or getattr(console, 'process', None) is not None:      # nothing to run it in, or a command is still running there
                if bar is not None:
                    bar.set_target('shell', focus=False);bar.box.setText(command)
                self.say('The Terminal is still running a command, so I have not run this one: it is in the line, with Terminal chosen, for when that one has ended.'
                         if console is not None else 'There is no Terminal in this window, so I have not run it.')
                return True
            to_console(self.host, 'shell', command)
            stacy_hand.record(self.host.session.state, 'Ran in the Terminal: ' + command, '$ ' + command, '', text.strip(), True)
            try:self.host.session.save()
            except Exception:  # noqa: BLE001
                pass
            self.say('I ran it in the Terminal: %s. It only reads; what it answered is above the line.' % command)
            return True
        if bar is not None:
            bar.set_target('shell', focus=False);bar.box.setText(command)
        self.say(('My hand is at “Ask first”, so' if stacy_hand.terminal_hers(command) else 'That command may change something, or I cannot tell that it only reads, so')
                 + ' it is yours to run: it is in the line, with Terminal chosen.')
        return True

    def say_desk(self, count, waiting, lines, go, plan=(), settle=None, doubts=(), look=None, hers=False):
        """The desk, checked: how many things were read, which wait for the owner and why, and the reads that were made.
        `go(object)` goes to one of them in the Field and says what can be done about it. `plan` is the changes that would
        settle what can be settled without a decision of the owner's; `settle()` puts them up for one Run."""
        if not waiting:
            card = self.say('I read the desk: %d thing%s. Nothing waits for you.' % (count, '' if count == 1 else 's'))
        else:
            card = self.say('I read the desk: %d thing%s. %d wait%s for you:' % (count, '' if count == 1 else 's', len(waiting), 's' if len(waiting) == 1 else ''))
            for n, (obj, why, steps) in enumerate(waiting[:12]):
                card.box.addWidget(sentence('{go}', {'go': ('“%s”' % obj.title, lambda obj=obj:go(obj))}))
                first = next((step for step in steps if step.kind == 'write'), None)
                said = QLabel(breakable(why + ((' · next: ' + first.words[:1].lower() + first.words[1:]) if first else '')));said.setWordWrap(True)
                said.setStyleSheet('color:%s' % QUIET);said.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(said)
            if len(waiting) > 12:card.box.addWidget(QLabel('… and %d more' % (len(waiting) - 12)))
        if plan and settle is not None:
            card.box.addWidget(sentence('{settle}', {'settle': (('Settle what I can: %d change%s, done at once' if hers else 'Settle what I can: %d change%s, one Run') % (len(plan), '' if len(plan) == 1 else 's'), settle)}))
        if doubts:                           # what a plausible result may hide: looked for on everything, said beside what waits
            head = QLabel('I doubt %d thing%s that look%s right:' % (len(doubts), '' if len(doubts) == 1 else 's', 's' if len(doubts) == 1 else ''));head.setWordWrap(True);card.box.addWidget(head)
            for row in doubts[:8]:
                if look is not None:card.box.addWidget(sentence('{go}', {'go': ('“%s”' % row['title'], lambda ident=row['id']:look(ident))}))
                said = QLabel(breakable(row['why']));said.setWordWrap(True);said.setStyleSheet('color:%s' % QUIET);said.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(said)
            if len(doubts) > 8:card.box.addWidget(QLabel('… and %d more: X on a sheet doubts it' % (len(doubts) - 8)))
        if lines:program_detail(card.box, 'The %d reads I made' % len(lines), '\n'.join(lines))
        card.waiting = waiting;card.plan = plan;card.doubts = list(doubts)
        QTimer.singleShot(60, lambda:self.scroll.verticalScrollBar().setValue(max(0, card.y() - 8)))
        return card

    def say_plan(self, plan, done=None, title=None, hers=False, word='', brief=False):
        """Several changes put up together: each named, with its exact line, and one Run. Run is the owner's go for the whole
        list as written. They run in order through the Kernel and stop at the first that is refused; each says how it went.
        `done(results)` is told, so the desk can be checked again: finished means the check finds nothing waiting.
        `hers` (0.6.0, her hand at Free hand): there is no Run to wait for; the caller runs the list at once (run_plan), and
        each change is one line in her trail."""
        card = self.say((title or 'To settle the desk I would make %d change%s.' % (len(plan), '' if len(plan) == 1 else 's'))
                        + ((' I am doing it now, as written here.' if len(plan) == 1 else ' I am doing them in order, as written here, and stop at the first that is refused.') if hers else
                           ' One Run does them in order, as written here, and stops at the first that is refused.'))
        card.rows = []
        for n, (obj, step) in enumerate(plan):
            said = QLabel(breakable('%d  “%s”: %s' % (n + 1, obj.title, step.words[:1].lower() + step.words[1:])));said.setWordWrap(True)
            said.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);card.box.addWidget(said)
            shown = step.line if not brief or len(step.line) <= 96 else step.line[:95] + '…'      # brief: a line that carries a whole file is shown by its start
            code = QLabel(breakable(bt.eye(shown)));code.setTextFormat(Qt.PlainText);code.setWordWrap(True);code.setFont(mono_font(14));code.setToolTip(step.line)
            code.setStyleSheet(bt.line_sheet());code.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);code.setTextInteractionFlags(Qt.TextSelectableByMouse)
            card.box.addWidget(code);card.rows.append(said)
        row = QHBoxLayout();run = button('Approve all %d' % len(plan) if len(plan) > 1 else 'Approve', 'stac');run.setObjectName('PlanRun');row.addWidget(run);row.addStretch(1);card.box.addLayout(row)
        run.setToolTip('Apply these changes in the order listed, stopping at the first that is refused. Nothing is changed until you do; in the Field, G does the same')
        card.plan = plan;card.run = run;card.results = None;card.hers = bool(hers);card.word = word;card.row = row;card.one_entry = False
        if hers:run.hide()
        else:
            approve_button(run, self.host)
            run.clicked.connect(lambda:self.run_plan(card, done))
        QTimer.singleShot(60, lambda:self.scroll.verticalScrollBar().setValue(max(0, card.y() - 8)))
        return card

    def run_plan(self, card, done=None):
        from .engine import engineering
        from .engineering_kernel import operator
        from .field_do import call as line_call
        if card.results is not None:return        # one go, one run
        card.results = [];card.run.setEnabled(False)
        from .boss_qt import waits
        waits(card.run, self.host, False)
        for n, (obj, step) in enumerate(card.plan):
            try:
                operation, arguments = line_call(step.line)
                r = engineering(self.host.root).dispatch(operation, arguments, operator())
            except Exception as exc:  # noqa: BLE001 - said as a refusal; the list stops here
                r = {'ok': False, 'error': {'message': str(exc)[:300]}}
            ok = bool(r.get('ok'));card.results.append((step.line, ok, r.get('result') if ok else (r.get('error') or {}).get('message')))
            result = r.get('result') if ok and isinstance(r.get('result'), dict) else {}
            title = (result.get('document') or {}).get('title') if isinstance(result.get('document'), dict) else None
            card.rows[n].setText(breakable(card.rows[n].text() + ('  ·  done' + (': “%s”' % title if title else '') if ok else '  ·  REFUSED: ' + str((r.get('error') or {}).get('message'))[:200])))
            if getattr(card, 'hers', False) and not getattr(card, 'one_entry', False):     # her own act: a line in her trail (a page worked again is kept beside the old one, so there is no exact Undo)
                from . import stacy_hand
                stacy_hand.record(self.host.session.state, '%s · “%s”' % (step.words, obj.title), step.line, '', getattr(card, 'word', ''), ok)
            if not ok:break
        went = sum(1 for _, ok, _ in card.results if ok)
        card.run.setText('Ran %d of %d' % (went, len(card.plan)))
        from .kasandra_art import note_outcome
        note_outcome(self.host, went == len(card.plan))
        if getattr(card, 'hers', False):
            try:self.host.session.save()
            except Exception:  # noqa: BLE001 - the changes are made and said
                pass
        if done is not None:done(card.results)

    def what_if(self, text):
        """“What if B3 were 320?”, asked while a sheet or a calculation is selected in the Field: that cell set to that value
        and followed along the wires, changing nothing (field.ripple, a read). Every calculation that reads the cell is worked
        again exactly with its own recipe; every finding, page and check that would move is named, and the Field marks them
        until Esc. A cell is named by its address, by its row's words, or (for a calculation) by its symbol; several go
        together with "and". Returns the thing to answer about, a dict with 'refusal' when the question is a what-if but
        names no number of this sheet, or None when it is not a what-if about a sheet or a calculation."""
        asked = re.match(r'^\s*what\s+if\b(.*)$', text, re.IGNORECASE | re.DOTALL)
        view = getattr(getattr(self.host, 'field_page', None), 'view', None)
        chosen = view.selected() if asked and view is not None and getattr(self.host, '_field_active', False) else None
        if chosen is None or chosen.kind not in ('calculation', 'sheet') or not isinstance(chosen.target, dict):return None
        from .engine import engineering
        from .engineering_kernel import operator
        from .field_ripple import cells_named
        _, names = cells_named(engineering(self.host.root), operator(), chosen)
        if not names:return None
        inputs = []
        if chosen.kind == 'calculation':
            got = call(self.host, 'documents.get', {'id': chosen.target.get('id')}) or {}
            inputs = ((got.get('document') or {}).get('derivation') or {}).get('inputs') or []
        filler = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'to', 'at', 'of', 'became', 'becomes', 'goes', 'went', 'equals', 'equal', 'cell', 'value', 'in', 'it', 'its'}
        setting = {}
        for part in re.split(r'\band\b|[,;]', asked.group(1).replace('=', ' ').replace('?', ' ')):
            tokens = part.split();at = next((i for i in range(len(tokens) - 1, -1, -1) if re.fullmatch(r'-?\d+(?:\.\d+)?', tokens[i])), None)
            if at is None:continue
            name = ' '.join(t for t in tokens[:at] if t.lower() not in filler).lower()
            cell = names.get(name) or next((c for n, c in names.items() if name and all(word in n.split() for word in name.split())), None)
            if cell:setting[cell] = tokens[at]
        if not setting:
            if inputs:
                said = ', '.join('%s (%s, in %s)' % (i['cell'], i.get('parameter') or i['symbol'], i['unit']) for i in inputs)
                return {'refusal': 'Say which input and its new value, for example “what if %s were” and a number. This calculation reads %s.' % (inputs[-1]['cell'], said)}
            cells = sorted({cell for cell in names.values()}, key=lambda cell: (len(cell), cell))
            return {'refusal': 'Say which cell and its new value, for example “what if %s were” and a number. The numbers of this sheet are in %s.' % (cells[-1], ', '.join(cells[:12]))}
        from .field_do import js
        from .field_page import show_would, thing_of
        said = ', '.join('%s = %s' % pair for pair in setting.items())
        show_would(self.host, chosen.id, setting, said)
        return {**thing_of(self.host, chosen), 'stac': 'field.ripple %s | pick rows | select way,title,says_now,would_be,why' % js(id=chosen.id, set=setting),
                'explicit': True, 'whole': True,
                'intro': 'What if %s on “%s”. Nothing is changed:' % (said, chosen.title if len(chosen.title) <= 44 else chosen.title[:43].rstrip() + '…')}

    def own_word(self, text):
        """A line that is one of the owner's own staC words (or says something about them), asked in conversation: she does
        what the line says. `word NAME = LINE` keeps and `forget NAME` lets go, said in a sentence; a word, or `words`, is
        read and shown as any staC line is. True when the line was one of these."""
        from .stac_words import command, expand, known_to
        made = command(text)
        if made is not None and made.startswith('/'):
            from .engine import engineering
            from .engineering_kernel import operator
            from .field_do import call as line_call
            self.thing = None;self.mine(text)
            operation, arguments = line_call(made)
            r = engineering(self.host.root).dispatch(operation, arguments, operator())
            self.host._stac_words = None
            self.say(str(r['result'].get('words') or 'Done.') if r.get('ok') else 'I could not: ' + str((r.get('error') or {}).get('message'))[:300])
            return True
        line = made if made is not None else expand(known_to(self.host), text)
        if line == text or str(line).lower().startswith('explain '):return False
        try:
            from .field_page import expand_this
            line = expand_this(self.host, line)
        except ValueError as exc:
            self.thing = None;self.mine(text);self.say(str(exc));return True
        self.thing = None;self.mine(text)
        name = text.strip().split()[0]
        self.answer_in_stac({'title': name, 'stac': line, 'kind': 'word'}, 'Your words, each with its line:' if made is not None else 'Your word “%s” is this line:' % name)
        return True

    def set_asked(self, text):
        """“Set B3 to 300”, “change the settled current to 300”, “make B3 300”: asked with a sheet or a calculation selected
        in the Field. The change is put up for approval (workbench/field_page.py, stage_set); nothing is changed by asking.
        True when the line was such a request, whether or not a change could be put up."""
        asked = re.match(r'^\s*(?:set|change|make)\b(.*)$', text, re.IGNORECASE | re.DOTALL)
        view = getattr(getattr(self.host, 'field_page', None), 'view', None)
        chosen = view.selected() if asked and view is not None and getattr(self.host, '_field_active', False) else None
        if chosen is None or chosen.kind not in ('calculation', 'sheet') or not isinstance(chosen.target, dict):return False
        from .engine import engineering
        from .engineering_kernel import operator
        from .field_ripple import cells_named
        _, names = cells_named(engineering(self.host.root), operator(), chosen)
        tokens = asked.group(1).replace('=', ' ').replace('?', ' ').split()
        at = next((i for i in range(len(tokens) - 1, -1, -1) if re.fullmatch(r'-?\d+(?:\.\d+)?', tokens[i])), None)
        if not names or at is None:return False
        filler = {'the', 'a', 'an', 'is', 'to', 'be', 'at', 'of', 'cell', 'value', 'in', 'it', 'its', 'equal', 'equals'}
        name = ' '.join(t for t in tokens[:at] if t.lower() not in filler).lower()
        cell = names.get(name) or next((c for n, c in names.items() if name and all(word in n.split() for word in name.split())), None)
        self.thing = None;self.mine(text)
        if cell is None:
            cells = sorted({c for c in names.values()}, key=lambda c: (len(c), c))
            self.say('Say which number and its new value, for example “set %s to” and a number. The numbers here are in %s.' % (cells[-1], ', '.join(cells[:12])));return True
        from .field_page import stage_set
        stage_set(self.host, chosen, cell, tokens[at], word=text.strip())
        return True

    def ask(self, text, about=None):
        if self.own_word(text):return
        if self.start_asked(text):return      # before "set": "make a folder called Rev 2" has a number in it and is not a number to set
        if self.made_asked(text):return
        if self.set_asked(text):return
        if self.run_asked(text):return
        thing = self.what_if(text)
        if thing and thing.get('refusal'):
            self.thing = None;self.mine(text);self.say(thing['refusal']);return
        thing = thing or self.thing_asked_about(text)
        if thing and not about:about = '%s “%s”, read with the line: %s' % (thing['kind'], thing['title'], thing['stac'])
        about = about or self.current_item()
        self.mine(text)
        if self.job:self.say('I am still answering the last question. Stop it from the Brain room, or wait a moment.');return
        # A question whose thing was named exactly (its menu, T, a what-if) is hers to read; any other may be the open page's to do.
        direct = None if thing and thing.get('explicit') else self.direct_request(text)
        if direct is not None:self.say(direct);return
        brain = call(self.host, 'brain.status') or {}
        selected = self.selected_file()
        if thing and thing.get('whole'):          # the rows are already plain sentences written by exact rules: a model is not asked to say them again
            self.answer_in_stac(thing, thing.get('intro') or 'What the records say about “%s”:' % thing['title'])
            return
        if brain.get('state') == 'READY' and thing:  # she reads first, exactly, then says it in her own words from what she read
            card = self.answer_in_stac(thing, thing.get('intro') or 'The records about “%s”, and the line that reads them:' % thing['title'])
            if not card.answered:return
            from .engine import engineering
            from .engineering_kernel import operator
            from .local_brain import RECORDS_HINT
            import uuid
            rows = card.said if len(card.said) <= 1500 else card.said[:1500].rsplit('\n', 1)[0] + '\n(more rows are not shown here)'
            question = text if thing['title'] in text else 'About the %s “%s”: %s' % (thing['kind'], thing['title'], text)
            facts = ['It is a %s named “%s”.' % (thing['kind'], thing['title'])]
            if thing.get('state'):facts.append('Its state: %s.' % thing['state'])
            if thing.get('lines'):facts.append('Recorded about it: %s.' % '; '.join(thing['lines'][:4]))
            if thing.get('fed_by'):facts.append('It comes from: %s.' % '; '.join(thing['fed_by'][:8]))
            if thing.get('feeds'):facts.append('It feeds: %s.' % '; '.join(thing['feeds'][:8]))
            r = engineering(self.host.root).dispatch('brain.ask', {'message': question + '\n\n' + RECORDS_HINT + '\n' + '\n'.join(facts) + '\nRows read from it:\n' + rows, 'mode': 'chat',
                                                                   'request_key': uuid.uuid4().hex}, operator())
            if not r.get('ok'):self.say('I read it, but I could not put it in words: ' + r['error']['message']);return
            self.job = r['result']['id'];self.job_epoch = self.host._operation_epoch;self.grounded = True
            self.pending = self.say('In my words…');self.timer.start()
            return
        if brain.get('state') != 'READY' and thing:  # no model, but the records can answer about this thing, and she says how she read them
            card = self.answer_in_stac(thing, thing.get('intro') or 'No model is loaded, so this is not in my own words. This is what the records say about “%s”, and the line that reads it:' % thing['title'])
            if not thing.get('intro'):         # a trace or a what-if is whole without a model; an open question about a sheet is not
                card.box.addWidget(sentence('{choose}', {'choose': ('Choose a model', lambda:open_destination(self.host, 'slate').pick_model())}))
            return
        if brain.get('state') != 'READY':
            if selected:  # no brain, but Ledger can still say what it knows about the file
                self.explain_file(selected, 'I have no brain running yet, so this is what Graphite itself knows about it.')
            card = self.say('For answers in my own words, choose a model; I run on this computer.' if selected else
                            'I have no brain running yet. Drop a GGUF model on the Brain room, or choose one.')
            if hasattr(self.host.tabs.currentWidget(), 'slate_request'):
                note = QLabel('On this page I still make direct edits without a model: bold, italic, underline, heading, subheading, body, code, plain, “replace x with y”, undo. '
                              '“Add up the numbers on this page” I work out myself: the total goes under your words and stays bound to them.')
                note.setWordWrap(True);card.box.addWidget(note)
            card.box.addWidget(sentence('{choose}', {'choose': ('Choose a model', lambda:open_destination(self.host, 'slate').pick_model())}))
            return
        message = text if not about else text + '\n\n(About the open item: ' + about + ')'
        if selected:
            from .explain import explain
            value = call(self.host, 'files.get', {'path': selected})
            if value:message += '\n(What Graphite knows: ' + explain(value)['text'][:1200] + ')'
        from .engine import engineering
        from .engineering_kernel import operator
        import uuid
        from .stacy_foundation_qt import selected_program
        args = {'message': message, 'mode': 'plan', 'request_key': uuid.uuid4().hex}
        context = selected_program(self.host.tabs.currentWidget())
        if context:args['program'] = context
        if getattr(self, 'program_receipt', None):args['program_receipt'] = self.program_receipt
        if context or 'program_receipt' in args:
            if not getattr(self, 'program_conversation', None):self.program_conversation = uuid.uuid4().hex
            args['conversation'] = self.program_conversation
        r = engineering(self.host.root).dispatch('brain.ask', args, operator())
        if not r.get('ok'):self.say('I could not start: ' + r['error']['message']);return
        self.job = r['result']['id'];self.job_epoch = self.host._operation_epoch
        self.pending = self.say('Reading…');self.timer.start()

    def poll(self):
        if not self.job:self.timer.stop();return
        job = call(self.host, 'jobs.get', {'id': self.job})
        if not job:return
        if job.get('state') not in ('Completed', 'Failed', 'Cancelled', 'Interrupted'):
            progress = call(self.host, 'slate.progress', {'job': self.job})
            if progress and progress.get('display_text'):self.pending.set_text('Draft · checking…\n' + progress['display_text'])
            return
        ident = self.job;self.job = None;self.timer.stop()
        if job['state'] != 'Completed':
            self.grounded = False
            from .kasandra_art import note_outcome
            note_outcome(self.host, False)
            self.pending.set_text('I stopped: ' + (job.get('error') or job['state']) + '. This is recorded so I learn from it.');return
        result = (call(self.host, 'brain.result', {'id': ident}) or {}).get('result') or {}
        proposal = result.get('proposal') or {}
        self.pending.set_text(proposal.get('text') or result.get('text') or 'Done.')
        if getattr(self, 'grounded', False):  # her words about rows she has just shown: nothing is proposed, and the words are the model's
            self.grounded = False
            note = QLabel('From the rows above · the words are the model’s and are not checked');note.setWordWrap(True);note.setStyleSheet('color:%s' % FAINT)
            note.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);self.pending.box.addWidget(note)
            QTimer.singleShot(60, lambda:self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))
            return
        actions = proposal.get('actions') or []
        observations = result.get('program_observations') or []
        if observations:
            from .stacy_control import merge_program_receipts, program_observation_text
            self.program_receipt = merge_program_receipts(observations, getattr(self, 'program_receipt', None))
            evidence = QLabel(breakable('\n'.join(program_observation_text(row, compact=True) for row in observations)))
            evidence.setTextFormat(Qt.PlainText)
            evidence.setWordWrap(True)
            evidence.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            self.pending.box.addWidget(evidence)
            program_detail(self.pending.box, 'Local evidence · %d' % len(observations),
                           json.dumps(observations, ensure_ascii=False, indent=2))
        if not actions and not observations:
            self.pending.box.addWidget(QLabel('No line proposed this time. The matrix records that too.'))
        # AGENT-02 (D19): a documents.edit for the open page applies at once, visibly and undoably; every other action keeps Run/Edit.
        # The request recorded on the page is the owner's words (the job's message before the open-item context).
        message = str(((job.get('request_spec') or {}).get('brain') or {}).get('message') or '')
        request = message.split('\n\n(About the open item:')[0].split('\n(What Graphite knows:')[0].split('\n(What Ledger knows:')[0].strip();chain = {}
        plans = result.get('action_plans') or []
        for index, action in enumerate(actions):
            seed_id = plans[index].get('seed_id') if index < len(plans) else None
            self.pending.box.addWidget(self.proposal_card(action, result.get('model_id'), request, chain, seed_id))
        QTimer.singleShot(60, lambda:self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))  # the cards stay in view

    def proposal_card(self, action, model_id=None, request='', chain=None, seed_id=None):
        from .instruction_matrix import program_of
        program = program_of(action['operation'], action['arguments'])
        page = self.apply_on_page(action, model_id, request, chain) if chain is not None else None
        if page and page['applied']:return self.applied_card(action, program, page['words'], page['tab'])
        card = QFrame();card.setObjectName('StacCard');box = QVBoxLayout(card);box.setContentsMargins(10, 8, 10, 8);box.setSpacing(6)
        is_program = action['operation'].startswith('programs.')
        label = QLabel('REVIEW ACTION' if is_program else 'PROPOSED LINE');label.setStyleSheet('color:%s;font-size:9pt;letter-spacing:1px' % TEAL);box.addWidget(label)
        summary = program
        if is_program:
            from .stacy_control import program_operation_title
            arguments = action['arguments']
            lines = [program_operation_title(action['operation'])]
            source = arguments.get('path') or arguments.get('url')
            if source:lines.append(source)
            if 'entries' in arguments:lines.append('%d reviewed files' % len(arguments['entries']))
            if 'destination' in arguments:lines.append('Save to ' + arguments['destination'])
            summary = '\n'.join(lines)
        code = QLabel(breakable(bt.eye(summary)));code.setTextFormat(Qt.PlainText);code.setWordWrap(True);code.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);code.setFont(mono_font(16));code.setStyleSheet(bt.line_sheet());code.setToolTip(summary);code.setTextInteractionFlags(Qt.TextSelectableByMouse);box.addWidget(code)
        if page:  # a page edit that could not apply by itself says why, above the review words
            why = QLabel(breakable(page['words']));why.setWordWrap(True);why.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);why.setStyleSheet('color:%s' % QUIET);box.addWidget(why)
            card.setProperty('modelTurn', 'not_applied');card.words = why
        row = QHBoxLayout();run = button('Run', 'stac');row.addWidget(run)
        if is_program:
            run.setObjectName('ProgramReviewRun')
            run.setStyleSheet('QPushButton {background:%s;color:%s;padding:4px 12px;font-weight:600;} '
                              'QPushButton:disabled {background:%s;color:%s;}' % (bt.OWNER, bt.ON_OWNER, PANEL, QUIET))
            epoch = getattr(self, 'job_epoch', self.host._operation_epoch)
            run.clicked.connect(lambda:self.run_program_proposal(action, seed_id, epoch, run))
        else:
            edit = button('Edit', 'quiet');row.addWidget(edit)
            run.clicked.connect(lambda:(run.setEnabled(False), run.setText('Ran'), self.execute(action['operation'], action['arguments'], program)))
            edit.clicked.connect(lambda:(self.host.shell2.top.box.setText(program), self.host.shell2.top.box.setFocus()))
        row.addStretch(1);box.addLayout(row)
        if is_program:
            program_detail(box, 'Exact command', program)
        return card

    def run_program_proposal(self, action, seed_id, epoch, button):
        from . import stacy_control
        from .stacy_foundation import seed_status
        bridge = self.host.ledger_bridge
        if bridge.busy:
            self.say('Wait for the current command to finish.')
            return
        seed = seed_status(bridge.kernel.root)
        if (not seed_id or seed.get('state') != 'VERIFIED_SOURCE_BINDINGS' or seed.get('seed_id') != seed_id
                or epoch != self.host._operation_epoch or self.host._closing):
            button.setEnabled(False)
            self.say('This plan expired. Ask for a fresh plan.')
            return
        button.setEnabled(False)
        button.setText('Running…')
        from .program_rooms_qt import ProgramRoom
        from .stacy_foundation_qt import selected_program
        room = self.host.tabs.currentWidget()
        matching_room = isinstance(room, ProgramRoom) and not room.busy and action['operation'].split('.')[1] == room.key
        room_context = selected_program(room) if matching_room else None

        def observed(results):
            receipt = stacy_control.program_receipt(results, getattr(self, 'program_receipt', None))
            if receipt:self.program_receipt = receipt
            result = results[0] if results else {}
            button.setText('Done' if result.get('ok') else 'Refused')
            if result.get('ok'):
                saved = result['result']
                if (matching_room and self.host.tabs.currentWidget() is room and room_context == selected_program(room)
                        and saved.get('state') in ('EXPORTED', 'EXTRACTED', 'DRAFT_SAVED', 'RETRIEVED')):
                    room.completed(saved)
                    room.sync_actions()
                line = json.loads(stacy_control.program_receipt(results) or '[]')
                if line:self.say(stacy_control.program_observation_text(line[-1]))
            else:
                self.say('Command refused · ' + result.get('error', {}).get('message', 'No result returned.'))

        bridge.run([action], provider=True, private_local=True, when_done=observed)

    def apply_on_page(self, action, model_id=None, request='', chain=None):
        """AGENT-02 (D19): a documents.edit proposed for the page open in the centre lands there now (DocumentsTab.
        apply_model_edit decides, writes the revision and shows it). None for any other operation. ``chain`` carries what
        this same proposal's earlier edits did to the page: {'base': the revision the proposal was made for, 'now': the
        revision they made, 'places_kept': whether every one of them only marked or styled}. A later edit made for the base
        revision follows them onto 'now' ONLY while places_kept holds (model_turn.keeps_places: no words changed, no
        paragraph added, so every paragraph index and offset means exactly what it meant when the model wrote it). After a
        replace or an append it stays made for the base revision, decide refuses it as stale, and its card keeps Run/Edit
        with that reason: a stale revision is refused, never rebased."""
        if not isinstance(action, dict) or action.get('operation') != 'documents.edit' or not isinstance(action.get('arguments'), dict):return None
        from .model_turn import not_applied_words, keeps_places
        tab = self.host.tabs.currentWidget()
        if not hasattr(tab, 'apply_model_edit'):
            return {'applied': False, 'tab': None, 'words': not_applied_words({'reason': 'no document page is open in the centre'})}
        arguments = dict(action['arguments']);ident = arguments.get('id', tab.document_id);seen = (chain or {}).get(ident)
        if seen and arguments.get('expected_revision') is None:arguments['expected_revision'] = seen['base']   # written with the rest of the proposal
        follows = bool(seen and arguments['expected_revision'] == seen['base'] and tab.revision == seen['now'])
        if follows and seen['places_kept']:arguments['expected_revision'] = seen['now']
        try:words = tab.apply_model_edit(arguments, request, model_id);outcome = getattr(tab, 'model_edit', None) or {}
        except Exception as exc:return {'applied': False, 'tab': tab, 'words': not_applied_words({'reason': 'the page could not take it (%s)' % exc})}
        if outcome.get('applied') and chain is not None:
            done = outcome['verdict']['arguments']
            chain[ident] = {'base': seen['base'] if seen else done['expected_revision'], 'now': tab.revision,
                            'places_kept': (seen['places_kept'] if seen else True) and keeps_places(done['change'])}
        elif follows and not seen['places_kept']:
            words += ' (An earlier edit in this proposal changed the page’s words, so the places this one names were not moved onto the new revision.)'
        return {'applied': bool(outcome.get('applied')), 'tab': tab, 'words': words}

    def applied_card(self, action, program, words, tab):
        """AGENT-02 (D19): the card for a page edit that already landed: what the model proposed, what changed on the page,
        the word undo (the page's one undo stack) and the owner's mark, which the instruction matrix keeps (as for a Run)."""
        card = QFrame();card.setObjectName('StacCard');card.setProperty('modelTurn', 'applied');box = QVBoxLayout(card);box.setContentsMargins(10, 8, 10, 8);box.setSpacing(6)
        label = QLabel('APPLIED ON THE PAGE');label.setStyleSheet('color:%s;font-size:9pt;letter-spacing:1px' % TEAL);box.addWidget(label)
        code = QLabel(breakable(bt.eye(program)));code.setWordWrap(True);code.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);code.setFont(mono_font(16));code.setStyleSheet(bt.line_sheet());code.setToolTip(program);code.setTextInteractionFlags(Qt.TextSelectableByMouse);box.addWidget(code)
        said = QLabel(breakable(words));said.setWordWrap(True);said.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);box.addWidget(said)
        def undo():
            try:answer = tab.slate_request('undo')
            except RuntimeError:answer = 'That page is closed; reopen it and use Undo there.'
            self.say(answer or 'Nothing to undo on this page.');return answer
        box.addWidget(sentence('{undo}', {'undo': ('undo', undo)}))   # the sentence above already says Ctrl Z or “undo” takes it back
        row = QHBoxLayout();ask = QLabel('Was this right?');ask.setStyleSheet('color:%s' % QUIET);row.addWidget(ask, 1)
        def marked(m):
            self.mark(program, m, row)
            for i in range(row.count()):  # the note mark() leaves wraps inside the narrow column
                w = row.itemAt(i).widget()
                if isinstance(w, QLabel):w.setWordWrap(True);w.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        for text, mark in (('Right', 'GOOD'), ('Wrong', 'BAD')):
            b = button(text, 'quiet');b.clicked.connect(lambda checked=False, m=mark:marked(m));row.addWidget(b)
        box.addLayout(row);card.words = said;card.undo = undo;card.marks = row
        return card

    def run_stac(self, text):
        op, args = route_program(text)
        text = args.get('program', args.get('text'))
        if not text:return
        self.mine(text, code=True)
        self.execute(op, args, text)

    def execute(self, operation, arguments, program):
        from .engine import engineering
        from .engineering_kernel import operator
        r = engineering(self.host.root).dispatch(operation, arguments, operator())
        if r.get('ok'):
            from .office_building_qt import readable_result
            bubble = self.say(readable_result(r['result']) if isinstance(r['result'], dict) else str(r['result'])[:2000])
        else:
            bubble = self.say('That did not work: ' + r['error']['message'])
        row = QHBoxLayout();ask = QLabel('Was this right?');ask.setStyleSheet('color:%s' % QUIET);row.addWidget(ask, 1)
        for text, mark in (('Right', 'GOOD'), ('Wrong', 'BAD')):
            b = button(text, 'quiet');b.clicked.connect(lambda checked=False, m=mark, w=row:self.mark(program, m, w));row.addWidget(b)
        bubble.box.addLayout(row)
        if r.get('ok') and operation == 'language.run':  # any staC answer can be watched: Slate asks again and tells you when it changes
            rows = r['result'].get('rows') or []
            words = {'watch': ('watch it', lambda p=program:self.watch(p)), 'keep': ('add to the Agenda', lambda p=program:self.keep_in_agenda(p))}
            if rows:words['save'] = ('save as a sheet', lambda p=program, rs=rows:self.save_rows(p, rs))
            bubble.box.addWidget(sentence('{watch}  ·  {keep}' + ('  ·  {save}' if rows else ''), words))

    def save_rows(self, program, rows):
        """A staC answer kept as a CSV in Files › Slate, so it opens in Sheets and can be compared later."""
        import time
        from .files_service import as_csv
        name = 'Slate/answer ' + time.strftime('%Y-%m-%d %H%M%S') + '.csv'
        r = call_write(self.host, 'files.write', {'path': name, 'text': as_csv(rows)})
        self.host.statusBar().showMessage(('Saved as Files › ' + name + '  (from: ' + program[:80] + ')') if r.get('ok')
                                          else (r.get('error') or {}).get('message', 'Not saved'), 8000)

    def watch(self, program):
        r = call_write(self.host, 'agenda.add', {'title': program[:400], 'program': program, 'watch': True, 'nice': 'background'})
        self.host.statusBar().showMessage('Watching it: Graphite asks again every 6 hours and tells you only when the answer changes.' if r.get('ok')
                                          else (r.get('error') or {}).get('message', 'Not watched'), 7000)

    def mark(self, program, mark, row):
        rows = (call(self.host, 'matrix.list', {'query': program[:200], 'limit': 5}) or {}).get('rows', [])
        target = next((r for r in rows if r['program'] == program), rows[0] if rows else None)
        if target:call_write(self.host, 'matrix.mark', {'id': target['id'], 'mark': mark})
        for i in range(row.count()):
            w = row.itemAt(i).widget()
            if w is not None:w.hide()
        note = QLabel('Marked ' + ('right' if mark == 'GOOD' else 'wrong') + ' · the instruction matrix remembers this');note.setStyleSheet('color:%s' % FAINT)
        note.setWordWrap(True);note.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);row.addWidget(note)  # AGENT-02: the note wraps instead of widening the column

    def direct_request(self, text):
        """A workspace that can resolve the request itself (a document page's formatting rules) answers first; then a
        request a profile fits (AGENT-01: “add up the numbers on this page”) becomes an assignment on the open document,
        worked by the driver between events; None leaves the request to the model path."""
        tab = self.host.tabs.currentWidget()
        if hasattr(tab, 'slate_request'):
            try:answer = tab.slate_request(text)
            except Exception as exc:return 'I could not make that change: ' + str(exc)
            if answer is not None:return answer
        from .agent_qt import assign_from_page
        try:return assign_from_page(self.host, tab, text)
        except Exception as exc:return 'I could not take that on: ' + str(exc)

    def current_item(self):
        tab = self.host.tabs.currentWidget()
        if hasattr(tab, 'slate_context'):return tab.slate_context()  # Files: the selected file, with its address
        address = getattr(tab, 'address', None)
        if isinstance(address, str) and address:return getattr(tab, 'root_path', Path('item')).name + ' (@' + address + ')'
        if tab is not None and tab.property('ledgerTitle'):      # a sheet's page keeps a cell box under that name: say the page by its title instead
            return str(tab.property('ledgerTitle'))
        return None

    def selected_file(self):
        tab = self.host.tabs.currentWidget()
        return tab.slate_file() if hasattr(tab, 'slate_file') else None

    def explain_file(self, rel, intro=None):
        """What Ledger knows about a file in Files, in words, with staC questions to run or keep in the Agenda."""
        from .explain import explain
        value = call(self.host, 'files.get', {'path': rel})
        if not value:self.say('I cannot read ' + rel + ' right now.');return None
        found = explain(value)
        card = self.say((intro + '\n\n' if intro else '') + found['text'])
        for program in found['suggestions']:
            code = QLabel(breakable(bt.eye(program)));code.setWordWrap(True);code.setFont(mono_font(15));code.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            code.setStyleSheet(bt.line_sheet());code.setToolTip(program);card.box.addWidget(code)
            card.box.addWidget(sentence('{run}  ·  {watch}  ·  {keep}', {'run': ('run it', lambda p=program:self.run_stac(p)),
                                                                        'watch': ('watch it', lambda p=program:self.watch(p)),
                                                                        'keep': ('add to the Agenda', lambda p=program:self.keep_in_agenda(p))}))
        return found

    def keep_in_agenda(self, program):
        r = call_write(self.host, 'agenda.add', {'title': program[:400], 'program': program})
        self.host.statusBar().showMessage('Added to the Agenda.' if r.get('ok') else (r.get('error') or {}).get('message', 'Not added'), 5000)

    def refresh(self, brain=None):
        brain = brain or call(self.host, 'brain.status') or {}
        name = self.host.shell2.model_name(brain)
        counts = (call(self.host, 'matrix.status') or {}).get('counts', {})
        learned = sum(v for k, v in counts.items() if k != 'PROPOSED')
        self.model.setText(((name or 'a model') if brain.get('state') == 'READY' else 'no model yet'))      # 0.8.0: the language is never named
        self.model.setToolTip('Learning from %d outcomes you marked or ran' % learned)
        for block in (getattr(self, 'work', None), getattr(self, 'related', None)):
            if block is not None:block.refresh()


def call_write(host, op, args):
    from .engine import engineering
    from .engineering_kernel import operator
    try:return engineering(host.root).dispatch(op, args, operator())
    except Exception as exc:return {'ok': False, 'error': {'message': str(exc)}}


# Today ----------------------------------------------------------------------------

class Card(QFrame):
    def __init__(self, title, note=''):
        super().__init__();self.setObjectName('Card2')
        self.box = QVBoxLayout(self);self.box.setContentsMargins(18, 14, 18, 14);self.box.setSpacing(10)
        head = QHBoxLayout();name = role(QLabel(title), 'card');head.addWidget(name, 1)
        self.note = QuietNote();self.note.setText(note);head.addWidget(self.note);self.box.addLayout(head)
        self.body = QVBoxLayout();self.body.setSpacing(7);self.box.addLayout(self.body);self.box.addStretch(1)
        self.actions = QHBoxLayout();self.actions.setSpacing(8);self.box.addLayout(self.actions)

    def clear(self):
        while self.body.count():
            item = self.body.takeAt(0)
            if item.widget():item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():child.widget().deleteLater()

    def say(self, html, **actions):
        label = sentence(html, actions);label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);self.body.addWidget(label)
        return label

    def line(self, text, tag=None, right='', on_click=None):
        row = QHBoxLayout();row.setSpacing(10)
        if tag:
            t = QLabel(tag);t.setFixedWidth(44);t.setStyleSheet('color:%s;font-family:"%s";' % (FAINT, MONO));row.addWidget(t)
        # G-B: a row never widens its card past its longest word: plain words wrap (a path may break after each '/'), a row you
        # can open is the same words as a wrapping link, and the note beside it (a folder) wraps the same way. Each keeps its
        # longest word as its least width, so a deep folder can no longer squeeze the name beside it to nothing.
        label = sentence('{go}', {'go': (text, on_click)}) if on_click else QLabel(str(text).replace('/', '/\u200b'))
        label.setWordWrap(True);row.addWidget(label, 1)
        if right:
            note = QLabel(str(right).replace('/', '/\u200b'));note.setWordWrap(True);note.setStyleSheet('color:%s' % FAINT);row.addWidget(note)
        self.body.addLayout(row)


TAGS = {'.docx': 'DOCX', '.pdf': 'PDF', '.csv': 'CSV', '.zip': 'ZIP', '.c': 'C', '.h': 'C', '.md': 'MD', '.txt': 'TXT', '.gbr': 'GBR',
        '.img': 'IMG', '.json': 'JSON', '.png': 'PNG', '.jpg': 'JPG', '.xlsx': 'XLSX', '.tar': 'TAR', '.gz': 'GZ', '.iso': 'ISO'}


def greeting():
    import time
    hour = time.localtime().tm_hour
    return 'Good morning.' if 5 <= hour < 12 else ('Good afternoon.' if 12 <= hour < 18 else 'Good evening.')


def tag_for(name):return TAGS.get(Path(name).suffix.lower(), (Path(name).suffix[1:5] or 'FILE').upper())


class TodayPage(QWidget):
    """Today: what arrived, what waits for you, where you left off, and Slate."""

    def __init__(self, host):
        super().__init__();self.host = host;self.setObjectName('TodayPage')
        self.setContextMenuPolicy(Qt.CustomContextMenu)  # like a desktop: right-click on Today opens the empty place's menu (D4: the root chain menu folded in)
        self.customContextMenuRequested.connect(lambda point:__import__('workbench.context_menu', fromlist=['open_at']).open_at(self.host, self, point))
        outer = QHBoxLayout(self);outer.setContentsMargins(0, 0, 0, 0);outer.setSpacing(0)
        main = QVBoxLayout();main.setContentsMargins(28, 24, 28, 24);main.setSpacing(18)
        head = QHBoxLayout()
        titles = QVBoxLayout();titles.setSpacing(6);self.greeting = role(QLabel(greeting()), 'hero');titles.addWidget(self.greeting)
        self.where = role(QLabel(), 'lead');self.where.setWordWrap(True);titles.addWidget(self.where);head.addLayout(titles, 1)
        main.addLayout(head)  # 4.1: no buttons in the head; its sentence carries the two things you may want next
        from .boss_qt import ArtPanel
        self.art = ArtPanel(host);main.addWidget(self.art)
        self.capture = CaptureBox(host);main.addWidget(self.capture)
        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout();grid.setHorizontalSpacing(20);grid.setVerticalSpacing(18);self.grid = grid;self.columns = 2
        grid.setColumnStretch(0, 1);grid.setColumnStretch(1, 1)  # two columns share the width evenly, whatever their words ask for
        self.arrived = Card('Ingress');self.waiting = Card('Waiting for you');self.continue_ = Card('Continue', 'Recently open');self.slate = Card('Graphite')  # Ingress (D28): the owner's word for the folder files come in through
        for card, r, c in ((self.arrived, 0, 0), (self.waiting, 0, 1), (self.continue_, 1, 0), (self.slate, 1, 1)):grid.addWidget(card, r, c)
        self.cards = (self.arrived, self.waiting, self.continue_, self.slate)
        # 4.1: cards hold sentences; a card's action is a word in its sentence, and only when there is something to act on.
        self.accept = button('Accept', 'primary');self.accept.clicked.connect(self.accept_waiting);self.waiting.actions.addWidget(self.accept);self.waiting.actions.addStretch(1)
        main.addLayout(grid);main.addStretch(1)  # cards fit what they hold, as in the design
        holder = QWidget();holder.setLayout(main);holder.setObjectName('TodayPage')
        scroller = QScrollArea();scroller.setWidgetResizable(True);scroller.setFrameShape(QFrame.NoFrame);scroller.setWidget(holder);self.scroller = scroller
        outer.addWidget(scroller, 1)  # at large text the page scrolls down; nothing is squeezed or shrunk, and nothing scrolls sideways (fit_columns)
        side = QFrame();side.setObjectName('TodaySide');side.setFixedWidth(320);col = QVBoxLayout(side);col.setContentsMargins(18, 22, 18, 18);col.setSpacing(18)
        self.facts = {}
        for key, title in (('workspace', 'THIS WORKSPACE'), ('library', 'LIBRARY'), ('privacy', 'PRIVACY')):
            col.addWidget(role(QLabel(title), 'section'))
            value = QLabel();value.setWordWrap(True);value.setStyleSheet('color:%s' % QUIET);col.addWidget(value);self.facts[key] = value
        col.addStretch(1)
        col.addWidget(role(QLabel('MORE'), 'section'))
        for label, destination in (('Organizer', 'organizer'), ('Memory', 'memory'), ('Knowledge', 'stacy_knowledge'), ('References', 'references'), ('Commands', 'commands'), ('Settings', 'settings')):
            link = QPushButton(label);link.setFlat(True);link.setProperty('arcButton', 'link');link.setCursor(Qt.PointingHandCursor);link.clicked.connect(lambda checked=False, d=destination:open_destination(host, d));col.addWidget(link)
        from .version import title as product
        foot = QLabel(product());foot.setStyleSheet('color:%s' % FAINT);foot.setWordWrap(True);col.addWidget(foot)
        outer.addWidget(side);side.hide()  # 3.0: the facts are one sentence under the greeting; the links live in the one box
        self.timer = QTimer(self);self.timer.setInterval(4000);self.timer.timeout.connect(self.fill);self._waiting = None

    CARD_MIN = 260  # a card's narrowest comfortable width at 14 pt; under two of these Today's grid is one column (G-B; 320 until 0.8.0, which made Home one column at 1366 x 768)

    def fit_columns(self):
        """Two columns of cards while two fit at their own width and CARD_MIN, otherwise one: Today never scrolls sideways."""
        margins = self.grid.parentWidget().layout().contentsMargins() if self.grid.parentWidget() is not None else None
        room = self.width() - (margins.left() + margins.right() if margins is not None else 112) - self.scroller.verticalScrollBar().sizeHint().width()
        need = max([round(self.CARD_MIN * scale_of(self.host))] + [card.minimumSizeHint().width() for card in self.cards])
        columns = 2 if (room - self.grid.horizontalSpacing()) / 2 >= need else 1
        if columns == self.columns:return
        self.columns = columns;self.grid.setColumnStretch(1, 1 if columns == 2 else 0)
        for card in self.cards:self.grid.removeWidget(card)
        for i, card in enumerate(self.cards):self.grid.addWidget(card, i // columns, i % columns)

    def resizeEvent(self, event):
        super().resizeEvent(event);self.fit_columns();QTimer.singleShot(0, self.fit_art)

    def fit_art(self):
        """0.8.0, less scrolling: Home fits its window. The picture at its head gives up height (to ArtPanel.LEAST) before
        the page would scroll, and takes it back when there is room."""
        art = self.art;holder = self.scroller.widget()
        if holder is None or getattr(art, 'mode', '') != 'illustrated':return
        view = self.scroller.viewport().height();box = holder.layout()
        if view < 120 or box is None:return
        tall = box.totalHeightForWidth(holder.width()) if box.hasHeightForWidth() else box.sizeHint().height()
        limit = view - (tall - art.height())
        if getattr(art, 'limit', None) is None or abs(art.limit - limit) > 2:
            art.limit = limit;height = art.plate_height()
            if art.height() != height:art.setFixedHeight(height)
            # a short window: the jot box keeps three lines' room (it grows no taller than that until there is room again)
            self.capture.text.setMaximumHeight(round((112 if limit < art.LEAST else 160) * scale_of(self.host)))

    def office(self):return self.host.ledger_bridge.navigation()['office']()

    def also_waiting(self):
        """Besides deliveries: the Agenda's waiting rows (proposals, investigations, watches, suggestions) and working copies that need a look."""
        out = []
        for row in ((call(self.host, 'agenda.view') or {}).get('waiting') or []):
            if row.get('kind') == 'proposal':
                fn = lambda r=row:__import__('workbench.compare_qt', fromlist=['show']).show(self.host, path=r.get('path', ''), proposal=r['id'])
            else:fn = lambda:open_destination(self.host, 'agenda')
            title = row.get('title') or 'Agenda item'
            if row.get('kind') == 'job':  # V-27: a job in words (its capability family and state), not the raw tool id
                from .operations import tool_words
                title = tool_words(row.get('title'), row.get('reason') or row.get('state'))
            out.append((title, {'proposal': 'proposal', 'investigation': 'investigation', 'watch': 'changed', 'job': 'job'}.get(row.get('kind'), 'Agenda'), fn))
        from .agent_qt import today_rows
        out.extend(today_rows(self.host))  # AGENT-01: an assignment paused by closing Ledger or Master Stop, with its resume word; one that needs you
        for c in (call(self.host, 'copies.list') or {}).get('copies', []):
            if c['state'] == 'WORKING' and c['status'].startswith(('Ready', 'Original changed', 'Recovery', 'Original is missing')):
                out.append((c['name'] + ' · ' + c['status'].split(' — ')[0].lower(), 'working copy',
                            lambda c=c:__import__('workbench.compare_qt', fromlist=['show']).show(self.host, _op='copies.review', id=c['id'])))
        return out

    def showEvent(self, event):
        super().showEvent(event);self.fill();self.timer.start();self.fit_columns();QTimer.singleShot(0, self.fit_art);QTimer.singleShot(150, self.fit_art)

    def hideEvent(self, event):super().hideEvent(event);self.timer.stop()

    def look_first(self):
        inbox = (call(self.host, 'receiving.status') or {}).get('inbox')
        waiting = (call(self.host, 'receiving.status') or {}).get('inbox_waiting') or []
        if inbox and waiting:self.host.open_in_viewer(Path(inbox) / waiting[0])
        else:open_destination(self.host, 'office')

    def accept_waiting(self):
        if not self._waiting:return
        office = self.office()
        office.call('receiving.advance', {'id': self._waiting['id'], 'accept': True, 'reason': 'Owner accepted from Today'}, lambda value:(office.refresh(), self.fill()))

    def fill(self):
        from . import locations
        try:marker = locations.marker(self.host.root)
        except ValueError:marker = None
        name = (marker or {}).get('name') or 'Program'
        self.greeting.setText(greeting());pleasantry(self.greeting, self.host, round(34 * scale_of(self.host)))  # the greeting, in Paper's script
        status = call(self.host, 'receiving.status') or {};waiting = status.get('inbox_waiting') or []
        self.arrived.clear();self.arrived.note.setText(('%d new' % len(waiting)) if waiting else 'Nothing new')
        for file in waiting[:4]:self.arrived.line(file, tag_for(file))
        if waiting:self.arrived.say('{all}, or {look}.', all=('Receive them all', lambda:self.office().receive_inbox()), look=('look at the first one', self.look_first))
        else:self.arrived.line('Drop files on the Office, or copy them into ' + short(status.get('inbox') or '~/Concern/Office/Ingress') + '.')
        deliveries = (call(self.host, 'receiving.deliveries', {'limit': 30}) or {}).get('deliveries', [])
        self.waiting.clear();yours = [d for d in deliveries if d['stage'] == 'REVIEWED' and d.get('held')]
        moving = [d for d in deliveries if d['stage'] in ('SCANNING', 'REVIEWING', 'INDEXING')]
        self._waiting = yours[0] if yours else None
        others = self.also_waiting()  # Pass A: one list of what needs you, wherever it comes from
        if self._waiting:
            d = self._waiting;ready = sum(1 for h in d['held'] if h['reasons'] == ['OWNER_REVIEW_REQUIRED'])
            self.waiting.note.setText('%d deliveries' % len(yours) if len(yours) > 1 else '1 delivery')
            self.waiting.line(d['label'] + ' · %d files read' % d.get('files', 0))
            self.waiting.body.addWidget(StageBar(3))
            revived = [r for r in d.get('revived', []) if r['action'] in ('UNPACKED', 'REENCODED')]
            self.waiting.line('%d revived · %d held for a reason · %d not accepted' % (len(revived), len(d['held']) - ready, len(d['rejected'])), right='')
            self.accept.setText('Accept %d files' % ready);self.accept.setVisible(ready > 0)
            self.waiting.say('Or {each}.', each=('review each one in the Office', lambda:open_destination(self.host, 'office')))
        else:
            self.waiting.note.setText(('%d' % len(others)) if others else '');self.accept.hide()
            if moving or not others:self.waiting.line(('%d deliveries being read…' % len(moving)) if moving else 'Nothing is waiting for you.')
            done = [d for d in deliveries if d['stage'] == 'CATALOGED']
            if done and not others:self.waiting.line('Last cataloged: ' + done[0]['label'] + ' · %d files' % len(done[0]['accepted']))
        for text, where, fn in others[:5]:
            if where in ('resume', 'inspect'):self.waiting.say(escape_text(text) + ' · {%s}' % where, **{where: (where, fn)})  # AGENT-01: the word resumes the paused assignment; AGENT-02: long assignment rows wrap, the word inspects
            else:self.waiting.line(text, None, where, fn)
        if len(others) > 5:self.waiting.say('… and {more}.', more=('%d more in the Agenda' % (len(others) - 5), lambda:open_destination(self.host, 'agenda')))
        self.continue_.clear()
        recent = [(Path(p).name, 'viewed', lambda p=p:self.host.open_in_viewer(p)) for p in getattr(self.host, '_viewer_recent', [])[:4]]
        recent += [(Path(r).name, str(Path(r).parent) if str(Path(r).parent) != '.' else '', lambda r=r:self.host.open_document(self.host.root / r)) for r in self.host.session.state.get('recent', [])[:4]]
        for title, where, fn in recent[:5]:self.continue_.line(title, tag_for(title), where, fn)  # not `name`: that is the workspace's, used below
        if not recent:self.continue_.say('Nothing opened yet. {view}, or browse the {library}.', view=('Open any file', lambda:self.host.open_in_viewer()), library=('Library', lambda:open_destination(self.host, 'library:all')))
        else:self.continue_.say('{view} or browse the {library}.', view=('Open another file', lambda:self.host.open_in_viewer()), library=('Library', lambda:open_destination(self.host, 'library:all')))
        self.slate.clear()
        brain = call(self.host, 'brain.status') or {}
        counts = (call(self.host, 'matrix.status') or {}).get('counts', {})
        learned = sum(v for k, v in counts.items() if k != 'PROPOSED')
        self.slate.note.setText('learning from %d outcomes' % learned if learned else '')
        if brain.get('state') == 'READY':
            self.slate.line('Ask about what arrived. Graphite proposes a line; nothing runs until you say so.')
            asks = ('What arrived today?', 'Show the held files', 'Summarize the newest delivery')
            self.slate.say('Try: {a0} · {a1} · {a2}', **{'a%d' % i:(ask, lambda a=ask:self.host.shell2.ask(a)) for i, ask in enumerate(asks)})
        else:
            self.slate.say('Graphite has no brain running yet. {choose} to start one; it runs on this computer.', choose=('Choose a model', lambda:open_destination(self.host, 'slate').pick_model()))
        patterns = (call(self.host, 'matrix.patterns', {'limit': 10}) or {}).get('patterns', [])
        best = max((p for p in patterns if p['tries'] >= 2), key=lambda p:(p['success_rate'], p['tries']), default=None)
        if best:
            label = QLabel('Works best: %s · %d of %d' % (best['shape'], best['success'], best['tries']));label.setFont(mono_font(16));label.setStyleSheet('color:%s' % TEAL)
            label.setWordWrap(True);self.slate.body.addWidget(label)
        self.facts['workspace'].setText(name + '\n' + short(self.host.root) + ('\nno project attached' if (marker or {}).get('kind', 'NO_PROJECT') == 'NO_PROJECT' else '\nproject attached'))
        cache = self.host._library_cache = library_files(self.host, limit=2000)  # counted fresh: a delivery may have just finished
        self.facts['library'].setText(('%d files cataloged' % len(cache)) if cache is not None else '%d deliveries' % len(deliveries))
        self.facts['privacy'].setText('Cloud calls 0 · originals never changed')
        brain_words = 'Graphite is ready' if brain.get('state') == 'READY' else 'Graphite has no brain yet'
        sentence(escape_text(name + '  ·  %d files in the library  ·  %s  ·  nothing leaves this computer.' % (len(cache or []), brain_words)) + ' {receive} or {back}.',
                 {'receive': ('Receive files', lambda:self.office().pick_files()), 'back': ('go back to work', self.host.resume_workspace)}, self.where)
        self.fit_columns()  # G-B: new rows can change what a card needs; the columns follow now, not at the next resize


class StageBar(QWidget):
    """Revived · Snapshotted · Read · Your decision · Cataloged."""
    STEPS = ('Revived', 'Snapshotted', 'Read', 'Your decision', 'Cataloged')

    def __init__(self, done):
        super().__init__();self.done = done;self.setFixedHeight(30)

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing);w = (self.width() - 16) / 5.0
        f = QFont(self.font());f.setPixelSize(max(12, round(13 * SECTION_SCALE[0])));p.setFont(f);metrics = p.fontMetrics()  # metadata size, so the names never run together
        if self.height() != metrics.height() + 14:self.setFixedHeight(metrics.height() + 14)
        for i, name in enumerate(self.STEPS):
            color = QColor(TEAL if i < self.done else (AMBER if i == self.done else LINE))
            p.setPen(Qt.NoPen);p.setBrush(color);p.drawRoundedRect(int(i * (w + 4)), 0, int(w), 6, 3, 3)
            p.setPen(QColor(AMBER_TEXT if i == self.done else QUIET));p.drawText(int(i * (w + 4)), 10 + metrics.ascent(), metrics.elidedText(name, Qt.ElideRight, int(w) - 4))


# The controller -------------------------------------------------------------------

class Shell2(QObject):
    def __init__(self, host):
        super().__init__(host);self.host = host
        self.worksheet = None
        self.face_before_sheet = None

    def install(self):
        host = self.host
        # Top bar replaces the ribbon; the old toolbar stays alive (its actions are the window's) but hidden.
        self.top = TopBar(host);host.ribbon_dock.setWidget(self.top);host.toolbar.hide()
        host.setCorner(Qt.TopLeftCorner, Qt.TopDockWidgetArea)  # the top bar spans the whole window
        host.activity_rail.hide()
        if hasattr(host, 'navigator_logo'):host.navigator_logo.hide()
        # HATCH DESK D1a: no Library width here any more; desk_qt.apply gives both panes one width (typebar_qt.TypeBar.align).
        writing_prompt(host.tree_search, 'Filter the library…')
        # Right pane (HATCH DESK D1b): Conversation · Activity · Context, the desk's tabs (pane_qt), mirroring the left pane's.
        # Conversation is the Graphite face (SlateFace), Activity the Operations panel, Context the Context face; the three
        # buttons keep their old names (slate_button, operations_button, context_button) for callers.
        self.face = SlateFace(host);host.console_pages.addTab(self.face, 'Graphite')
        holder = host.console_pages.parentWidget();layout = holder.layout() if holder is not None else None
        from .pane_qt import PaneTabs
        self.face_tabs = PaneTabs(('Talk', 'Activity', 'Context'), 'Right pane views', host);self.face_tabs.setObjectName('FaceSwitch')
        self.slate_button, self.operations_button, self.context_button = self.face_tabs.buttons
        self.context_button.clicked.connect(self.show_context_face);self.slate_button.clicked.connect(self.show_primary_face)
        self.operations_button.clicked.connect(lambda checked=False:self.show_operations_face())
        if layout is not None:layout.insertWidget(0, self.face_tabs)
        host.console_pages.currentChanged.connect(self.face_changed);self.face_changed()
        # Timeline wording.
        tail = getattr(host.ledger_bridge, 'tail', None)
        if tail is not None:tail.trail.setText('Work trail')
        QShortcut(QKeySequence("Ctrl+K"), host, activated=self.search)  # the writing line in Search (HATCH DESK D3)
        QShortcut(QKeySequence('Ctrl+Shift+N'), host, activated=lambda:capture_dialog(host))
        # Home was built before the shell: replace the old landing page with Today.
        old = getattr(host, '_empty_home_page', None)
        if old is not None and not isinstance(old, TodayPage):
            active = host.central_stack.currentWidget() is old
            page = TodayPage(host);host.central_stack.addWidget(page);host._empty_home_page = page
            if active:host.central_stack.setCurrentWidget(page)  # the layout saved for leaving Home stays as it was
            host.central_stack.removeWidget(old);old.deleteLater()
        self.dress()
        from .operations_qt import install as install_operations
        install_operations(host)
        from .return_thread_qt import install as install_return_thread
        install_return_thread(host)
        from .navigation_qt import install as install_navigation
        install_navigation(host)
        from .pane_qt import install as install_panes
        install_panes(host)  # HATCH DESK D1b: both panes: three tabs, the active tree or face, the foot (Trash and its empty mirror)
        host.tabs.currentChanged.connect(self.sync_worksheet)
        host.central_stack.currentChanged.connect(self.sync_worksheet)
        from .graphite_brand import use_pointer
        use_pointer(host)  # HATCH DESK D1b: the pointer, the mark's two facets aimed at 11 o'clock
        self.restyle(getattr(host, 'reading_profile', None))
        self.timer = QTimer(self);self.timer.setInterval(5000);self.timer.timeout.connect(self.tick);self.timer.start()
        QTimer.singleShot(300, self.tick)
        QTimer.singleShot(0, self.stacy_first)

    def stacy_first(self):
        """0.5: the first thing on the right is Stacy, not the ledger of services. Activity is one word away, and is where
        the right pane goes by itself when work starts running."""
        host = self.host
        try:
            if self.worksheet is None and host.console_pages.currentWidget() is not self.face:
                host.console_pages.setCurrentWidget(self.face);self.face.refresh()
        except Exception:  # noqa: BLE001 - which face shows first is never worth an error
            pass

    def dress(self):
        """The frame from the mockups: quiet chrome, so the work stands out. Every control keeps working as before."""
        host = self.host
        # No bird in 3.0: Slate is the panel and the one box.
        clip = getattr(host, 'clip', None)
        if clip is not None:type(clip).retired = True;clip.hide()
        # Master Stop: one red square, always at the right edge. The advice score and details stay in its tooltip and menu.
        stop = host.master_stop_button
        stop.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);stop.setIcon(stop_icon());stop.setIconSize(QSize(14, 14));stop.setText('Stop')
        stop.setMinimumSize(QSize(84, 38));stop.setMaximumSize(QSize(16777215, 16777215))  # Paper v1.1: a graphite square and the word Stop; no red fill
        # Stop is the one control that must always be findable: a graphite square and the word, no box. It turns pink when
        # something recorded looks stuck, and while stopping; otherwise it stays graphite.
        stop.setStyleSheet('QToolButton#MasterStop {background:transparent;color:%s;border:0;border-bottom:2px solid transparent;border-radius:0;padding:0 8px;font-weight:600;} '
                           'QToolButton#MasterStop:hover {background:%s;border-bottom:2px solid %s;} QToolButton#MasterStop:focus {border-bottom:2px solid %s;} '
                           'QToolButton#MasterStop:pressed {background:%s;} '
                           'QToolButton#MasterStop[stuck="true"] {background:%s;border-bottom:2px solid %s;}' % (TEXT, ERASER, ERASER_MARK, TEXT, ERASER_DEEP, ERASER_DEEP, ERASER_MARK))
        stop.setProperty('paperFace', True)  # the face always says Stop; the advice score stays in the tooltip
        # The right panel needs no title bar: Context | Slate names it.
        host.sim_dock.setTitleBarWidget(QWidget())
        # The Library: no branch lines; a quiet filter; Settings and Commands at the foot, with the Concern view.
        host.nav.setRootIsDecorated(False);host.nav.setFrameShape(QFrame.NoFrame);host.nav.twig_branches = True;host.nav.reading_indent()  # 4.5: pencil twigs and buds, not file-manager lines
        host.ribbon_scroll.setMinimumHeight(40);self.hide_favorites()
        commands = getattr(host, 'ribbon_commands', None)
        if commands is not None and commands.layout() is not None:commands.layout().setContentsMargins(4, 2, 0, 2);commands.adjustSize()
        writing_prompt(host.tree_search, 'Filter…')
        host.global_search.setStyleSheet('QToolButton {background:transparent;border:0;}');host.global_search.setIcon(line_icon('search'))  # a quiet mark, never a box
        host.nav.setIconSize(QSize(0, 0))  # 3.0: words only in the Library
        pin = getattr(host.tabs, 'pin_button', None)
        if pin is not None:pin.setIcon(QIcon());pin.setProperty('arcButton', 'quiet')
        foot = QWidget();foot.setObjectName('LibraryFoot');col = QVBoxLayout(foot);col.setContentsMargins(10, 6, 10, 10);col.setSpacing(6)
        selector = getattr(host.concern, 'selector', None);overview = getattr(host.concern, 'overview_button', None)
        if selector is not None and overview is not None:
            parent_layout = selector.parentWidget().layout() if selector.parentWidget() else None
            if parent_layout is not None:
                for w in (selector, overview):find_and_take(parent_layout, w)
            # 4.1: no box and no buttons at the Library's foot. One quiet line names the view; the name is the word to change it.
            # Commands lives in Tools; the picker and Overview stay (hidden) so every existing path to them still works.
            col.addWidget(selector);col.addWidget(overview);selector.hide();overview.hide()
            line = role(QLabel(), 'quiet');self.view_line = line
            # Settings stays one quiet word at the end of that line: the one place people look for it from the Library.
            settings = QPushButton('Settings');settings.setCursor(Qt.PointingHandCursor);settings.clicked.connect(lambda:open_destination(host, 'settings'))
            from .trash_can_qt import TrashCan
            host.trash_can = TrashCan(host)
            row = QHBoxLayout();row.setSpacing(12);row.addWidget(line, 1);row.addWidget(settings);col.addLayout(row)
            trash_row = QHBoxLayout();trash_row.addStretch(1);trash_row.addWidget(host.trash_can);col.addLayout(trash_row)
            def pick(name, line=line):
                menu = QMenu(line)
                for i in range(selector.count()):
                    act = menu.addAction(selector.itemText(i));act.setCheckable(True);act.setChecked(i == selector.currentIndex())
                    act.triggered.connect(lambda checked=False, i=i:selector.setCurrentIndex(i))
                menu.addSeparator();menu.addAction('Concern overview', overview.click).setEnabled(overview.isEnabled())
                menu.exec(line.mapToGlobal(line.rect().bottomLeft()))
            def name(*_, line=line):sentence('Showing {view}', {'view': (selector.currentText(), lambda:pick('view'))}, line)
            selector.currentIndexChanged.connect(name);name();line.setEnabled(selector.isEnabled())
        body = QWidget();box = QVBoxLayout(body);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(0)
        host.nav_dock.setWidget(body);box.addWidget(host.nav, 1);box.addWidget(foot);host.nav.show()
        from .settings_qt import SettingsNavigator
        host.settings_navigator=SettingsNavigator(host,box,getattr(self,'view_line',None),settings if selector is not None and overview is not None else None)
        from .agenda_qt import install as install_agenda
        install_agenda(host)
        view = getattr(host, 'menu_groups', {}).get('View')
        if view is not None:  # the brief: script is an accent that yields to a plain-text preference
            script = view.addAction('Pleasantries in script');script.setCheckable(True);script.setChecked(cursive_on(host))
            def choose(on, host=host):
                from . import ledger_control
                from .engineering_kernel import operator
                row=next(r for r in ledger_control.settings(host.ledger_bridge.kernel)['settings'] if r['key']=='appearance.cursive')
                response=host.ledger_bridge.kernel.dispatch('ledger.settings.set',dict(key=row['key'],value=bool(on),expected_revision=row['revision']),operator())
                if response['ok']:host.ledger_bridge.sync_profile(force=True)
                else:
                    from PySide6.QtCore import QSignalBlocker
                    with QSignalBlocker(script):script.setChecked(row['value'])
                    host.statusBar().showMessage(response['error']['message'],6000)
            script.toggled.connect(choose);self.script_action = script  # works through Slate's Next quietly, one read-only item at a time
        # Desk tabs: names only, a quiet close mark.
        host.tabs.setIconSize(QSize(0, 0));host.tabs.setDocumentMode(True)
        # The Timeline: plain lines, the time in mono; its controls are quiet words.
        tail = getattr(host.ledger_bridge, 'tail', None)
        if tail is not None:
            tail.list.setStyleSheet('');tail.list.setItemDelegate(TimelineDelegate(tail.list));tail.list.setFrameShape(QFrame.NoFrame)
            tail.setObjectName('TimelineHead')
            def lines(tail=tail):
                tail.list.setFixedHeight((tail.list.fontMetrics().height() + 8) * (9 if tail.expand.isChecked() else 1) + 4)
            tail.resize_lines = lines;lines()
            for b in (tail.trail, tail.expand):b.setCursor(Qt.PointingHandCursor)
            from .console_qt import attach
            attach(host, tail)  # the Timeline strip becomes the console: Log, staC, Kernel, Find, Shell
            from .typebar_qt import install as install_typebar
            install_typebar(host, self.top.box, host.console)  # the one place to type: along the whole foot of the window
        else:self.top.layout().itemAt(0).widget().layout().insertWidget(3, self.top.box, 1)
        # The search mark moves from above the Library to the path at the top: it puts the cursor in the box, ready to find.
        gs = getattr(host, 'global_search', None)
        if gs is not None:
            try:gs.clicked.disconnect()
            except (RuntimeError, TypeError):pass
            for a in list(gs.actions()):gs.removeAction(a)
            # GRAPHITE-01 put the sharpened point on a small tile here, at the upper left, and one click opened the STRUTHIO game.
            # HATCH DESK D1a: the word Graphite stands alone at the upper left and the mark lives at the far right as the System
            # menu's symbol; the button stays (callers and checks hold it) out of sight, and the game opens from the System menu's
            # list (desktop_header_qt.NicePopup, Game) until D2 makes Game the System menu's first row.
            from .graphite_brand import mark_icon
            gs.setParent(self.top);gs.setFixedSize(54, 54);gs.setIconSize(QSize(44, 44));gs.setIcon(mark_icon(44))
            gs.setProperty('paperIcon', True);gs.setToolButtonStyle(Qt.ToolButtonIconOnly)
            gs.setToolTip('Graphite');gs.setAccessibleName('Graphite')
            gs.clicked.connect(lambda checked=False:__import__('workbench.struthio_qt', fromlist=['show']).show(host))  # every good program has an egg
            gs.hide();self.top.mark.hide()
        ts = getattr(host, 'tree_search', None)
        if ts is not None:ts.hide()  # no search above the Library: one place to type, at the foot
        from .chain_menu import install as install_chains
        install_chains(host)  # the Menu key opens the chain menu for what is selected
        from .menus2 import rebuild
        rebuild(host);QTimer.singleShot(0, lambda host=host:rebuild(host))  # once now, once after the other parts have added theirs
        self.hide_favorites()

    def hide_favorites(self):
        """3.0 keeps the top row to words: favorite icons are hidden (they are rebuilt when favorites change, so this repeats)."""
        for row in getattr(self.host, 'favorite_button_rows', {}).values():
            for b in row:
                if b.isVisible() or not b.isHidden():b.hide()
        commands = getattr(self.host, 'ribbon_commands', None);scroll = getattr(self.host, 'ribbon_scroll', None)
        if commands is not None and not commands.property('paperTight'):
            from PySide6.QtWidgets import QLayout
            for divider in commands.findChildren(QFrame, 'CommandDivider'):divider.hide()
            for lay in commands.findChildren(QLayout):lay.setContentsMargins(0, 0, 0, 0);lay.setSpacing(0)
            if commands.layout() is not None:commands.layout().setContentsMargins(0, 0, 0, 0);commands.layout().setSpacing(0)
            for heading in self.host.command_menus.values():heading.setMinimumHeight(0);heading.setMinimumWidth(0)
            commands.setProperty('paperTight', True)
        if commands is not None and scroll is not None and getattr(self.host, 'desk', None) is None:
            commands.adjustSize();scroll.setMaximumWidth(commands.sizeHint().width() + 4)  # before the desk exists only

    def scale(self, s):
        """Sizes that are not text: they grow with the interface size, so large text is never clipped."""
        host = self.host
        if SECTION_SCALE[0] != s:
            SECTION_SCALE[0] = s
            if getattr(host, '_library_rows', None):build_library(host)
        stop = host.master_stop_button;stop.setMinimumSize(QSize(round(84 * s), round(38 * s)));stop.setIconSize(QSize(round(14 * s), round(14 * s)))
        stop.setStyleSheet(stop.styleSheet().split('/*scale*/')[0] + '/*scale*/QToolButton#MasterStop {font-size:%dpx;}' % round(16 * s))
        f = stop.font();f.setPixelSize(round(16 * s));f.setWeight(QFont.DemiBold);stop.setFont(f)  # the one control that must always read clearly
        # HATCH DESK D1a: the panes' width and the bands' height are the desk's (desk_qt.apply); the word Graphite always shows.
        tail = getattr(getattr(host, 'ledger_bridge', None), 'tail', None)
        if tail is not None:QTimer.singleShot(0, tail.resize_lines)  # one line, measured in the new size
        face = getattr(self, 'face', None)
        if face is not None:face.input.setMinimumHeight(round(112 * s));face.input.setMaximumHeight(round(144 * s))
        for box in host.findChildren(CaptureBox):box.text.setMinimumHeight(round(112 * s));box.text.setMaximumHeight(round(160 * s))

    def restyle(self, profile=None):
        """Called after every reading-preference change: the window's own text stays on the design scale."""
        from . import locations
        from .reading_profile import DEFAULT
        profile = profile or DEFAULT
        assets = locations.program(self.host.root) / 'branding' / 'shell2'
        sheet = self.host.styleSheet();marker = '/*shell2*/'
        sheet = sheet.split(marker)[0]
        new = sheet + marker + chrome_css(profile, assets)
        if new != self.host.styleSheet():
            # Set it directly: clearing first leaves widgets with stale fonts. A later size change must still reach widgets
            # that were styled while hidden (Today, closed tabs), so those are re-polished explicitly.
            changed = marker in self.host.styleSheet()
            self.host.setStyleSheet(new)
            if changed:
                for w in self.host.findChildren(QWidget):w.style().unpolish(w);w.style().polish(w)
        self.scale(float(profile.get('ui_pt', 14.0)) / 14.0)
        context = getattr(getattr(self.host, 'arc_inspector', None), 'body', None)
        if context is not None:  # the Context face is part of the frame, not a document
            context.setProperty('arcReadingPreview', True)  # so the reading sizes do not reset it
            size = max(9, round(13 * float(profile.get('ui_pt', 14.0)) / 14.0))
            context.document().setDefaultStyleSheet("body,p,li {font-family:'%s';font-size:%dpx;}" % (SANS, size))
            font = QFont(SANS);font.setPixelSize(size);context.setFont(font)

    def tick(self):
        if getattr(self.host, '_closing', False):return
        self.top.refresh();refresh_library(self.host);self.hide_favorites()
        if self.host.console_pages.currentWidget() is self.face:self.face.refresh()
        if ((not hasattr(self.host,'cabinet_page') or self.host.cabinet_page.using_legacy)
                and (not hasattr(self.host, '_library_cache') or not getattr(self, '_cache_ticks', 0) % 6)):
            self.host._library_cache = library_files(self.host, limit=2000)
        self._cache_ticks = getattr(self, '_cache_ticks', 0) + 1

    def model_name(self, brain):
        model = (brain or {}).get('selection', {}).get('model_id')
        if not model:return None
        for m in (call(self.host, 'brain.models') or {}).get('models', []):
            if m['id'] == model:
                name = next((f['name'] for f in m.get('files', []) if f.get('role') == 'weights'), model[:12])
                return re.sub(r'(?i)[-_.]?(q\d.*|f16|bf16)?\.gguf$', '', name).replace('-', ' ')
        return model[:12]

    def face_changed(self, *args):
        current = self.host.console_pages.currentWidget()
        preview = self.worksheet.preview if self.worksheet is not None else None
        self.slate_button.setChecked(current is self.face or current is preview)
        self.slate_button.setText('Talk' if preview is None or current is self.face else 'Preview')
        self.slate_button.setAccessibleName(self.slate_button.text())
        self.context_button.setText('Sources' if preview is not None else 'Context')
        self.context_button.setAccessibleName(self.context_button.text())
        self.context_button.setChecked(current is getattr(self.host, 'arc_inspector', None))
        self.operations_button.setChecked(current is not None and current is getattr(self.host, 'operations_panel', None))
        for button in (self.slate_button, self.operations_button, self.context_button):
            button.setAccessibleDescription('Current view' if button.isChecked() else '')
            button.hide()       # 0.5.3: one view, no three tabs; the buttons stay for what calls them and are not shown
        self.pane_title(current, preview)

    def title_clicked(self):
        """The pane's title is a way back: from Activity or Context to what was there, and with a worksheet open, from Stacy
        to the sheet's Preview and from the Preview to her."""
        current = self.host.console_pages.currentWidget();preview = self.worksheet.preview if self.worksheet is not None else None
        if current is self.face:
            if preview is not None:self.show_worksheet_preview()
        elif preview is not None and current is preview:self.show_slate_face()
        else:self.show_primary_face()

    def pane_title(self, current, preview):
        """Where the three tabs stood: the name of the pane, Stacy; and, while Activity or Context is up, the way back to her."""
        title = getattr(self, 'title_word', None)
        if title is None:
            title = self.title_word = QPushButton(self.face_tabs);title.setObjectName('PaneTitle');title.setCursor(Qt.PointingHandCursor)
            title.setFocusPolicy(Qt.TabFocus);title.clicked.connect(lambda checked=False:self.title_clicked())
            self.face.signature.hide()      # her name is said once: the pane's title says it, so the line beside her face need not
            title.setStyleSheet('QPushButton#PaneTitle {font-family:"IBM Plex Mono";font-weight:600;color:%s;background:transparent;border:0;border-bottom:2px solid %s;padding:0 2px;text-align:left;} '
                                'QPushButton#PaneTitle:hover {color:%s;border-bottom:2px solid %s;}' % (TEXT, AMBER_EDGE, TEAL_TEXT, READY))
        other = 'Activity' if current is getattr(self.host, 'operations_panel', None) else ('Sources' if preview is not None else 'Context') if current is getattr(self.host, 'arc_inspector', None) else ''
        # With a spreadsheet's worksheet open the pane has two faces of its own, her and the sheet's Preview: the title is
        # then the way from one to the other, so neither is ever out of reach.
        pair = '' if preview is None or other else ('Preview  ›' if current is self.face else named('‹ Stacy') if current is preview else '')
        home = not other and not pair
        words = pair or (named('Stacy') if home else named('‹ Stacy  ·  %s') % other)
        if title.text() != words:
            title.setText(words);title.setAccessibleName(named('Stacy') if home else ('The sheet’s Preview' if pair.startswith('Preview') else named('Back to Stacy') + (' from ' + other if other else '')))
            title.setToolTip('' if home else ('The sheet’s Preview' if pair.startswith('Preview') else named('Back to Stacy')))
        tabs = self.face_tabs
        # 0.7.0 ("Probably don't even need the Stacy name tag taking up space"): at rest the pane has no title row at all;
        # her face is its top. The row comes back, as the way back, only while Activity or Context is up.
        if getattr(tabs, 'at_rest', None) != bool(home):
            tabs.at_rest = bool(home);tabs.setVisible(not home)
            body = tabs.parentWidget()
            if callable(getattr(body, 'arrange', None)):body.arrange()
        if getattr(tabs, 'title', None) is not title:
            tabs.title = title;tabs.placed = None      # the row places it where the tabs' words stood, at their size (pane_qt.PaneTabs.place)
            title.setGeometry(getattr(tabs, 'inset', 16), max(0, tabs.height() - 36), max(40, title.sizeHint().width() + 12), 30)
        else:
            title.resize(max(40, min(tabs.width() - 2 * getattr(tabs, 'inset', 16), title.sizeHint().width() + 12)), title.height())
        title.show();title.raise_()

    def sync_worksheet(self, *_):
        host = self.host
        if not hasattr(host, 'cabinet_page') or getattr(host, '_closing', False):
            return
        tab = host.tabs.currentWidget()
        sheet = None if host._home_active else getattr(tab, 'worksheet', None)
        if sheet is not None and tab.pages.currentWidget() is not sheet:
            sheet = None
        previous = self.worksheet
        if previous is sheet:
            self.sync_journal_index(tab)
            return
        pages = host.console_pages
        cabinet = host.cabinet_page
        layout = cabinet.stack.widget(0).layout()
        if previous is not None:
            pages.removeTab(pages.indexOf(previous.preview))
            previous.preview.setParent(previous)
            previous.bracket.set_available(False)
            for widget in (previous.folder, previous.workflow, previous.cabinet_button, previous.margin):
                layout.removeWidget(widget)
                widget.hide()
                widget.setParent(previous)
            host.desk_trees.remove(previous.folder)
            cabinet.tree.show()
        elif sheet is not None:
            self.face_before_sheet = pages.currentWidget()
        self.worksheet = sheet
        if sheet is not None:
            sheet.refresh_folder()
            at = layout.indexOf(cabinet.tree)
            for i, widget in enumerate((sheet.folder, sheet.workflow, sheet.cabinet_button, sheet.margin)):
                layout.insertWidget(at + i, widget, 1 if widget is sheet.margin else 0)
                widget.show()
            host.desk_trees.append(sheet.folder)
            sheet.folder.show()
            sheet.show_cabinet(sheet.cabinet_button.isChecked())
            sheet.bracket.set_available(sheet.stock_fields() is not None)
            pages.addTab(sheet.preview, 'Preview')
            pages.setCurrentWidget(sheet.preview)
        elif self.face_before_sheet is not None:
            pages.setCurrentWidget(self.face_before_sheet)
            self.face_before_sheet = None
        self.face_changed()
        self.sync_journal_index(tab)
        QTimer.singleShot(0, host.type_bar.align)

    def sync_journal_index(self, tab):
        """Use the Files rail for the open journal's own list and creation controls."""
        host = self.host
        active = None if host._home_active or not hasattr(tab, 'place_index') else tab
        previous = getattr(self, 'active_journal_index', None)
        if active is previous:
            return
        cabinet = host.cabinet_page
        if previous is not None:
            previous.place_index()
            if self.worksheet is None:
                cabinet.tree.show()
        self.active_journal_index = active
        if active is not None:
            layout = cabinet.stack.widget(0).layout()
            active.place_index(layout, layout.indexOf(cabinet.tree))
            cabinet.tree.hide()

    def show_primary_face(self):
        if self.worksheet is not None:
            return self.show_worksheet_preview()
        return self.show_slate_face()

    def show_worksheet_preview(self):
        if self.worksheet is not None:
            self.host.sim_dock.show()
            self.host.console_pages.setCurrentWidget(self.worksheet.preview)

    def search(self):
        """Ctrl+K: the writing line in Search (HATCH DESK D3: Search is one of the line's four modes, marked when chosen and
        remembered like any mode); its words are kept and selected, so typing replaces them (typebar_qt.TypeBar.search)."""
        bar = getattr(self.host, 'type_bar', None)
        if bar is not None:bar.search();return
        box = self.top.box;box.setText('?' + box.text().lstrip('@/?$'));box.setFocus();box.setSelection(1, len(box.text()) - 1)

    def show_slate_face(self):
        host = self.host
        if host._home_active:host.resume_workspace()
        host.sim_dock.show();host.console_pages.setCurrentWidget(self.face);self.face.refresh();self.face.input.setFocus();return self.face

    def show_context_face(self):
        self.host.sim_dock.show();self.host.console_pages.setCurrentWidget(self.host.arc_inspector);self.host.arc_inspector.refresh()

    def show_operations_face(self):
        self.host.sim_dock.show();self.host.console_pages.setCurrentWidget(self.host.operations_panel);self.host.operations_panel.refresh()

    def ask(self, text, about=None):
        self.show_slate_face();self.face.ask(text, about)

    def run_stac(self, text):
        self.show_slate_face();self.face.run_stac(text)

    def show_library(self, kind='all'):
        host = self.host;host._close_start()
        for i in range(host.tabs.count()):
            tab = host.tabs.widget(i)
            if isinstance(tab, LibraryTab):
                host.tabs.setCurrentWidget(tab);tab.reload();tab.set_kind(kind);return tab
        tab = LibraryTab(host, kind);host.tabs.addTab(tab, host.nav_icon('search'), tab.title());host.tabs.setCurrentWidget(tab);return tab

    def open_library_file(self, entry):
        path = Path(entry['copy']) if Path(entry['copy']).is_file() else Path(entry['stored_copy'])
        if not path.is_file():QMessageBox.information(self.host, 'Library', 'The received copy of ' + entry['name'] + ' is not available.');return None
        return self.host.open_in_viewer(path, address=entry['address'], origin=entry['delivery'] + '  ›  ' + entry['name'])


def find_and_take(layout, widget):
    """Take a widget out of a layout, looking inside nested layouts too."""
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item.widget() is widget:layout.takeAt(i);return True
        if item.layout() is not None and find_and_take(item.layout(), widget):return True
    return False


def install(host):
    if hasattr(host, 'shell2'):return host.shell2
    load_fonts(host.root)
    host.shell2 = Shell2(host);host.shell2.install()
    return host.shell2
