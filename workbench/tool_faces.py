"""How a tool button is drawn: its words on a plate, or one of Graphite's own glyphs.

The owner, 13 November 2026, after "No ugly white boxes that stand out like a sore thumb": "Or graphite themed icons can
be tried as an option also." And, the same evening: "mostly focus on how it looks ... and fun to use. Think apple
simplicity but still very powerful." So a workspace that has never chosen opens with icons, and words are one choice away:

    Work ▸ Rules ▸ Buttons ▸ Words | Icons            (kept in the session as "buttons")

Words: the button is what the desk's style sheet makes it, a dark plate with a quiet edge (boss_theme).

Icons: the button wears a glyph (glyph_set) and has no plate at all. A control every program has (find, undo, save, the
page before) is its glyph alone, and its tip begins with its name. A control particular to one page keeps its words
beside its glyph, because no drawing says "Copy citation". Under the pointer it answers in green, as everything on the
desk does; pressed, chosen or holding the keyboard it is amber; when it cannot be used it is dim.

Only two things about the button change: how it is painted and how wide it is. Its words, its name for a screen reader,
its tip, its click and its place are the same, so the keys, Stacy, More and the window checks still find it by its words.
A tool with no glyph of its own keeps its plate and its words in either choice.
"""
from PySide6.QtCore import QEvent, QObject, QRectF, Qt, QTimer
from PySide6.QtGui import QActionGroup, QColor, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton, QMenu, QToolTip

from . import boss_theme as t
from .glyph_set import GLYPHS

MODES = ('words', 'icons')
KEY = 'buttons'                 # the session's name for the choice
SIDE = 20                       # a glyph's box, in pixels: the size it was drawn to be read at
WIDEST = 16777215               # Qt's "no limit" for a widget's width
OPENS_WITH = 'icons'            # what a workspace that has never chosen is shown (0.5: the owner asked for the look of it first)
STATE = {'mode': 'words'}       # a button made outside a window (a test, a tool) is its words until a window says otherwise

# What a tool wears, by the words on it. A button made with a glyph of its own (the bar above the work) says so itself.
FOR_WORDS = {
    '‹ Field': 'field', 'Find': 'find', '−': 'smaller', '+': 'larger', 'Undo': 'undo', 'Redo': 'redo', 'Save': 'save',
    '‹ Previous': 'previous', 'Next ›': 'next', 'Copy citation': 'cite', 'Review table': 'table', 'More ▾': 'more',
    'New note': 'note', 'Calculate and write report…': 'report', 'Recalculate': 'recalc', 'Preview export': 'export',
    'Export…': 'export', 'Edit cell': 'cell', 'Open source row': 'source', 'New document': 'document',
    'Compare sources again': 'again', 'Stop': 'stop', 'Bold': 'bold', 'Italic': 'italic', 'Underline': 'underline',
    'Heading': 'h1', 'Subheading': 'h2', 'Minor heading': 'h3', 'Body': 'body', 'Code': 'code', 'Plain': 'plain',
    'Pin / Unpin': 'pin', 'Close': 'close',
}
# The glyphs that stand alone: what every program draws the same way. Every other glyph keeps its words beside it.
BARE = frozenset(('find', 'smaller', 'larger', 'undo', 'redo', 'save', 'previous', 'next', 'more', 'pin', 'close',
                  'bold', 'italic', 'underline', 'h1', 'h2', 'h3', 'body', 'code', 'plain'))
NAMES = {'−': 'Smaller', '+': 'Larger'}         # what a bare sign is called in its tip


def mode():
    return STATE['mode']


def glyph_of(button):
    """The glyph this button wears when icons are chosen, or None: it keeps its plate and its words."""
    key = button.property('glyph') or FOR_WORDS.get(button.text().strip())
    return key if key in GLYPHS else None


def said(text):
    """A button's words as they stand beside a glyph: without the arrow or the dots the glyph has taken the place of."""
    return text.strip().lstrip('‹').rstrip('›▾…').strip()


def signature(button, key):
    return '%s|%s|%s|%s' % (STATE['mode'], key, button.text(), button.font().toString())


def fit(button):
    """Give the button the width its face needs. Done again when the choice, its words or its letters change."""
    key = glyph_of(button) if STATE['mode'] == 'icons' else None
    now = signature(button, key)
    if button.property('facedFor') == now:return
    button.setProperty('facedFor', now)
    if key is None:
        if button.property('facedWidths'):      # back to its words: the widths it had before it wore a glyph
            low, high = (int(n) for n in str(button.property('facedWidths')).split(','))
            button.setMinimumWidth(low);button.setMaximumWidth(high);button.setProperty('facedWidths', None)
    else:
        if not button.property('facedWidths'):button.setProperty('facedWidths', '%d,%d' % (button.minimumWidth(), button.maximumWidth()))
        wide = SIDE + 10 if key in BARE else 7 + SIDE + 6 + button.fontMetrics().horizontalAdvance(said(button.text())) + 9
        button.setFixedWidth(wide);button.setAttribute(Qt.WA_Hover, True)
    button.updateGeometry();button.update()


def later(button):
    """Fit once the event in hand is over (a widget is not resized from inside its own paint or polish)."""
    def go():
        try:fit(button)
        except RuntimeError:      # the button was taken away in the meantime
            pass
    QTimer.singleShot(0, go)


def glows(button):
    try:
        from .boss_qt import glows as desk_glows
        return desk_glows(button.window())
    except Exception:  # noqa: BLE001 - a glow is never worth an error
        return False


def paint(button, key):
    p = QPainter(button);p.setRenderHint(QPainter.Antialiasing)
    r = QRectF(button.rect());on = button.isEnabled();down = on and button.isDown()
    chosen = on and button.isCheckable() and button.isChecked();over = on and button.underMouse();keys = on and button.hasFocus()
    if down or chosen:ground, edge, ink, accent = t.AMBER_SOFT, t.AMBER_EDGE, t.AMBER_TEXT, t.AMBER_EDGE
    elif over:ground, edge, ink, accent = t.TEAL_SOFT, t.TEAL_EDGE, t.TEAL_TEXT, t.TEAL_EDGE
    elif not on:ground, edge, ink, accent = None, None, t.LINE_MID, t.LINE
    elif button.property('faceTone') == 'live':ground, edge, ink, accent = None, None, t.TEAL_TEXT, t.TEAL_EDGE
    else:ground, edge, ink, accent = None, None, t.TEXT, t.FAINT
    if keys and not (down or chosen):edge = t.AMBER_EDGE      # the keyboard is here
    if ground:p.fillRect(r, QColor(ground))
    if edge:
        p.setPen(QPen(QColor(edge), 1));p.setBrush(Qt.NoBrush);p.drawRect(r.adjusted(0.5, 0.5, -0.5, -0.5))
    size = min(SIDE, int(r.height()) - 4);bare = key in BARE
    x = round((r.width() - size) / 2) if bare else 7;y = round((r.height() - size) / 2)
    draw = GLYPHS[key]

    def glyph(dx, dy, line, fill):
        p.save();p.translate(x + dx, y + dy);p.scale(size / 20.0, size / 20.0);p.setPen(Qt.NoPen);p.setBrush(Qt.NoBrush)
        try:draw(p, line, fill)
        finally:p.restore()

    if over and not down and glows(button):       # what the pointer is over glows a little, as on the rest of the desk
        level = t.glow();halo = QColor(t.READY);halo.setAlphaF(min(0.3, 0.09 * level))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):glyph(dx, dy, halo, halo)
        if level >= 1.5:
            far = QColor(t.READY);far.setAlphaF(min(0.16, 0.035 * level))
            for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)):glyph(dx, dy, far, far)
    glyph(0, 0, QColor(ink), QColor(accent))
    if not bare:
        p.setFont(button.font());p.setPen(QColor(ink))
        p.drawText(QRectF(x + size + 6, 0, r.width() - x - size - 6, r.height()), Qt.AlignVCenter | Qt.AlignLeft, said(button.text()))
    p.end()


class Face(QObject):
    """One watcher for every tool: it paints the button when icons are chosen, and leaves it alone when they are not."""

    def eventFilter(self, button, event):
        kind = event.type()
        if kind in (QEvent.Polish, QEvent.FontChange, QEvent.StyleChange, QEvent.Show):
            later(button);return False
        if STATE['mode'] != 'icons':return False
        if kind == QEvent.Paint:
            key = glyph_of(button)
            if key is None:return False
            if button.property('facedFor') != signature(button, key):later(button)     # its words changed since it was fitted
            paint(button, key);return True
        if kind == QEvent.ToolTip:
            key = glyph_of(button)
            if key in BARE:                       # a glyph alone says its name first
                name = NAMES.get(button.text().strip(), said(button.text()));tip = button.toolTip()
                words = tip if tip.lower().startswith(name.lower()) else (name + ' · ' + tip if tip else name)
                QToolTip.showText(event.globalPos(), words, button);return True
        return False


FACE = Face()


def wear(button, key=None, tone=None):
    """Make this button one the choice reaches. `key` names its glyph when its words do not; `tone` 'live' draws it in the
    desk's green at rest (the way back to the Field). Returns the button."""
    button.setProperty('toolFace', True)
    if key:button.setProperty('glyph', key)
    if tone:button.setProperty('faceTone', tone)
    button.installEventFilter(FACE);fit(button)
    return button


# ---- glyphs in the menus ---------------------------------------------------------------------------------------------
# The owner, with 0.4.6 on the ThinkPad: "I love your icons. I wish we had more icons." With icons chosen, a line of a
# menu that names something a glyph was drawn for carries that glyph before its words. The words are what they were.
FOR_MENU = {
    'New File': 'document', 'New Idea': 'note', 'New Project': 'folder', 'Open': 'folder', 'Open in Universal Viewer': 'page',
    'Find a File': 'find', 'Receive Files': 'receive', 'Import (Ingress)': 'receive', 'Export (Egress)': 'export',
    'Work on a Copy of a File': 'copy', 'Save': 'save', 'Save All': 'save', 'Close': 'close', 'Recover Unsaved Work': 'undo',
    'Undo': 'undo', 'Redo': 'redo', 'Cut': 'cut', 'Copy': 'copy', 'Paste': 'paste', 'Select All': 'select', 'Find': 'find',
    'Find Next': 'next', 'Replace': 'recalc', 'Go to Line': 'source',
    'Explore capabilities': 'rooms', 'Inquiries': 'asked', 'System Check': 'found', 'STOP / KILL all Graphite operations': 'stop',
    'Engineering': 'chip', 'Today': 'home', 'Field': 'field', 'Files': 'folder', 'Library': 'stack', 'Changes': 'delta',
    'Continuing work': 'running', 'Graphite\'s Agenda': 'agenda', 'Console': 'prompt', 'Cabinet': 'folder',
    'Refresh Machine View': 'recalc', 'Full Screen': 'full', 'Reading and Layout': 'sliders', 'Larger prose': 'larger',
    'Smaller prose': 'smaller', 'Word Wrap': 'lines', 'Split Editor / Close Split': 'split', 'Pin / Unpin workspace': 'pin',
    'Reset Window Layout': 'undo', 'Graphite Commands': 'prompt', 'Run an operation': 'running', 'Chain Menu': 'chain',
    'Constructed chain': 'chain', 'Writing Line': 'cell', 'Command Palette': 'prompt', 'Favorite commands': 'star',
    'Graphite Settings': 'sliders', 'Desk artwork': 'picture', 'Buttons': 'rooms', 'Inspector': 'info', 'This Computer': 'chip',
    'Pills and Paired Computers': 'port', 'Getting Started': 'book', 'Keyboard Shortcuts': 'key', 'Installation Guide': 'receive',
    'The Orange Book': 'book', 'About Graphite': 'info', 'Assistant': 'asked', 'Terminal': 'prompt', 'Search': 'find', 'Log': 'lines',
}
_icons = {}


def icon(key):
    """A glyph as an icon a menu can show: its ink at rest, amber when its line is chosen, dim when it cannot be used."""
    kept = (key, t.glow())       # the light under a glyph follows the desk's dial
    if kept in _icons:return _icons[kept]
    from PySide6.QtGui import QIcon, QPixmap
    from .glyph_set import KIND
    draw = GLYPHS.get(key) or KIND.get(key);made = QIcon()
    if draw is None:return made
    # 0.5.2 (the owner: "the icons in the drop down menus could be neon green"): the desk's live green, with a little of
    # its own light under it; brighter on the line the pointer is on; dim on a line that cannot be used.
    level = t.glow()
    for state, line, fill, lit in ((QIcon.Normal, t.READY, t.TEAL_EDGE, 0.10), (QIcon.Active, t.TEAL_TEXT, t.READY, 0.18),
                                   (QIcon.Selected, t.TEAL_TEXT, t.READY, 0.18), (QIcon.Disabled, t.LINE_MID, t.LINE, 0.0)):
        for ratio in (1, 2):
            image = QPixmap(SIDE * ratio, SIDE * ratio);image.fill(Qt.transparent)
            p = QPainter(image);p.setRenderHint(QPainter.Antialiasing);p.scale(SIDE * ratio / 20.0, SIDE * ratio / 20.0)
            try:
                if lit and level > 0:
                    halo = QColor(t.READY);halo.setAlphaF(min(0.32, lit * level / 1.9))
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        p.save();p.translate(dx, dy);draw(p, halo, halo);p.restore()
                draw(p, QColor(line), QColor(fill))
            finally:p.end()
            image.setDevicePixelRatio(ratio);made.addPixmap(image, state)
    _icons[kept] = made;return made


def named(text):
    """A menu line's words as they are looked up: without the mnemonic mark, the key beside them, or the dots."""
    return text.replace('&', '').split('\t')[0].rstrip('….').strip()


def dress(menu):
    """Give the lines of this menu their glyphs (or take them away again, with words chosen). Looked at each time the
    menu opens; a menu inside it is dressed when it opens in its turn."""
    from PySide6.QtGui import QIcon
    from .glyph_set import KIND
    on = STATE['mode'] == 'icons'
    if bool(menu.property('glyphs')) != on:      # the menu's own sheet makes room for a column of glyphs, or closes it
        menu.setProperty('glyphs', on);style = menu.style();style.unpolish(menu);style.polish(menu)
    for line in menu.actions():
        if line.isSeparator():continue
        # 0.5.2 ("We don't need to display keyboard shortcuts anywhere ... keep it sleek and tidy"): a line shows its words.
        # The key still does what it did; it is no longer printed beside them, nor written into the line after a tab.
        if line.isShortcutVisibleInContextMenu():line.setShortcutVisibleInContextMenu(False)
        if '\t' in line.text():line.setText(line.text().split('\t')[0])
        if '&' in line.text().replace('&&', ''):line.setText(line.text().replace('&&', '\0').replace('&', '').replace('\0', '&&'))      # nor an underlined letter
        inner = line.menu()
        if inner is not None and not inner.property('glyphDressed'):
            inner.setProperty('glyphDressed', True);inner.aboutToShow.connect(lambda inner=inner: dress(inner))
        key = FOR_MENU.get(named(line.text()))
        if key is None or (key not in GLYPHS and key not in KIND):continue
        if on and not line.property('glyphIcon'):           # some lines carry an older picture the menus never showed: it is kept, to be put back
            line.setProperty('iconBefore', line.icon());line.setProperty('shownBefore', line.isIconVisibleInMenu());line.setProperty('glyphIcon', True)
        if on:
            line.setIcon(icon(key));line.setIconVisibleInMenu(True)      # set each time: its light follows the dial
        elif line.property('glyphIcon'):
            before = line.property('iconBefore');line.setIcon(before if isinstance(before, QIcon) else QIcon())
            line.setIconVisibleInMenu(bool(line.property('shownBefore')));line.setProperty('glyphIcon', False)


def start(host):
    """Read the choice the session keeps. Called once, before the work pages are made."""
    chosen = getattr(getattr(host, 'session', None), 'state', {}).get(KEY, OPENS_WITH)
    STATE['mode'] = chosen if chosen in MODES else OPENS_WITH
    try:        # no menu anywhere in the program prints a key beside a line (0.5.2); the keys work as they did
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.setAttribute(Qt.AA_DontShowShortcutsInContextMenus, True)
    except Exception:  # noqa: BLE001 - how a menu is printed is never worth an error
        pass


def restyle(host):
    for button in host.findChildren(QAbstractButton):
        if button.property('toolFace'):fit(button)
    bar = getattr(host, 'centre_bar', None)
    if bar is not None:bar.sync()               # the name beside the controls has more or less room now


def choose(host, chosen):
    if chosen not in MODES:return
    STATE['mode'] = chosen;host.session.state[KEY] = chosen;host.session.save();restyle(host)


def menu(host):
    """Work ▸ Rules ▸ Buttons: Words or Icons."""
    choices = QMenu('Buttons', host);group = QActionGroup(choices);group.setExclusive(True);lines = {}
    for key, word, tip in ((MODES[0], 'Words', 'Each button is its words on a dark plate'),
                           (MODES[1], 'Icons', 'Each button is one of Graphite’s drawn glyphs; a button particular to a page keeps its words beside it')):
        line = choices.addAction(word);line.setCheckable(True);line.setToolTip(tip);group.addAction(line);lines[key] = line
        line.triggered.connect(lambda checked=False, key=key:choose(host, key))
    choices.setToolTipsVisible(True)
    choices.aboutToShow.connect(lambda:lines[STATE['mode']].setChecked(True))
    lines[STATE['mode']].setChecked(True)
    return choices
