"""Tabs and the split (Graphite 1.0 L5): several working tabs, and at most two panes side by side in the centre.

    working tabs    a view opened through the navigation (a double click on the board, Open in the tree, a Search result,
                    Back and Forward) is a named working tab: it stays open beside the others and is never the Preview the
                    next opening replaces (workspace_tabs.WorkspaceTabs.working). An object already open is never opened a
                    second time: its tab, in either pane, comes to the front instead (bring, and the window's own openers).
    the split       two panes: the window's own tab widget (host.tabs) and a second one beside it (PaneTabs). Split on the
                    centre bar, on a tab's right-click, or Open beside on a tile's right-click; or drag a tab out of its strip,
                    or a tile off the board, onto the empty half. The divider moves; each pane keeps its own tabs; One pane
                    puts them back together and keeps every tab.
    one point of attention
                    only the pane in focus drives the tree's highlight and her "this". The window's tab widget is always
                    the pane in focus: a click (or the keyboard) in the other pane exchanges the two panes' tabs and their
                    places in the divider, so nothing moves on the screen, and every part of the window that reads "the tab
                    in front" (the tree through the one navigation state, her "this", the centre bar, Save, Board, Close)
                    reads the pane the owner is working in. The other pane keeps its place (its scroll and page) and says so
                    quietly: "◇ Beside · another object".
    a narrow centre two panes need about 560 px each side by side; on a narrower centre (1366 wide) they are stacked, one
                    above the other, and the passive pane offers Side by side anyway.

Nothing here writes a file or a record; it only arranges the window's views.
"""
from __future__ import annotations

import weakref
from pathlib import Path

from PySide6.QtCore import QEvent, QMimeData, QObject, QPoint, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QDrag, QFontMetrics, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QMenu, QPushButton, QSizePolicy, QTabWidget, QToolButton, QVBoxLayout,
                               QWidget)

from . import boss_theme as bt

MIN_PANE = 560              # a pane side by side is readable from about this width (the coordinator's measure)
MOST_PANES = 2              # at most two panes; more views stay in the tabs
TAB_MIME = 'application/x-graphite-tab'
OBJECT_MIME = 'application/x-graphite-object'
SAY = {
    'focus': 'In focus',
    'focus_tip': 'The pane in focus: the tree\'s highlight and Kasandra\'s “this” follow it.',
    'beside': 'Beside · another object',
    'beside_same': 'Beside · the same object',
    'beside_empty': 'Beside · empty',
    'beside_tip': ('This pane shows another object: “%s”. The tree\'s highlight and Kasandra\'s “this” follow the pane in focus; '
                   'a click here brings this pane into focus. Until then it keeps its place.'),
    'empty_tip': 'The other half is empty: drag a tab here, or a tile from the board, or choose a view below.',
    'stack': 'Stack', 'side': 'Side by side', 'one': 'One pane', 'split': 'Split',
    'stack_tip': 'Set the two panes one above the other.',
    'side_tip': ('The centre is too narrow for two panes of about %d px side by side, so they are stacked. Side by side sets '
                 'them next to each other anyway, each narrower.') % MIN_PANE,
    'side_tip_wide': 'Set the two panes next to each other.',
    'one_tip': 'One pane: the two panes become one again; both keep their tabs.',
    'split_tip': 'Split: the view you had before beside this one (at most two panes). A tab or a tile dragged onto the empty half does the same.',
    'split_none': 'Nothing is open to set beside this one: open another view, then Split.',
    'empty': 'The other half',
    'empty_words': 'Drag a tab here, or a tile from the board; or show one of these here:',
    'drop_tab': 'Drop here: “%s” beside “%s”',
    'drop_tab_alone': 'Drop here: “%s” in its own half',
    'drop_tile': 'Drop here: open “%s” beside “%s”',
    'drop_tile_alone': 'Drop here: open “%s”',
    'opened_alone': 'Opened “%s”. Nothing else is open to set beside it.',
}


# ---- the hooks the window calls ----------------------------------------------------------------------------------------------
def split_of(host):
    return getattr(host, 'l5_split', None)


def is_on(host):
    sp = split_of(host)
    return bool(sp is not None and sp.on)


def all_tabs(host):
    """Every working view of the window: the pane in focus's tabs, then the other pane's."""
    tabs = getattr(host, 'tabs', None)
    found = [tabs.widget(i) for i in range(tabs.count())] if tabs is not None else []
    sp = split_of(host)
    if sp is not None:found += [sp.other.widget(i) for i in range(sp.other.count())]
    return [w for w in found if w is not None]


def other_tabs(host):
    """The views in the other pane (none with one pane)."""
    sp = split_of(host)
    if sp is None or not sp.on:return []
    return [w for w in (sp.other.widget(i) for i in range(sp.other.count())) if w is not None]


def pane_of(host):
    """Which pane is in focus, as the navigation state records it: 'main' with one pane, else left/right (top/bottom stacked)."""
    sp = split_of(host)
    return sp.active_side() if sp is not None and sp.on else 'main'


def keys_of(tab):
    """What a view shows, as keys two views of one object share: its object (the navigation's id), its file, its sheet, its
    reference, or its room (a room is one room wherever it looks)."""
    keys = set()
    if tab is None:return keys
    try:
        oid = getattr(tab, '_living_oid', None)
        if oid:keys.add(('oid', str(oid)))
        for name in ('path', 'root_path'):
            value = getattr(tab, name, None)
            if isinstance(value, Path) or (isinstance(value, str) and value.startswith('/')):
                try:keys.add(('path', str(Path(value).resolve())))
                except (OSError, RuntimeError, ValueError):pass
        kind = type(tab).__name__
        if kind == 'OfficePanel' and getattr(tab, 'ident', None):keys.add(('office', str(tab.ident)))
        if kind == 'PdfDocumentTab':
            source = getattr(tab, 'source', None) or {}
            if source.get('item'):keys.add(('pdf', str(source.get('namespace')), str(source.get('item'))))
        from .workspace_tabs import ROOMS
        if kind in ROOMS or tab.property('ledgerRoom'):keys.add(('room', kind))
    except RuntimeError:          # a view being taken away
        return set()
    return keys


def keys_of_object(host, ident):
    """The keys of the view an object of the navigation (a file in Files, a record of the desk) is opened in."""
    keys = {('oid', str(ident))} if ident else set()
    nav = getattr(host, 'living_nav', None)
    if nav is None or not ident:return keys
    entry = nav.files_by_id.get(ident)
    if entry is not None and nav.files:
        try:keys.add(('path', str((Path(nav.files['root']) / entry['path']).resolve())))
        except (OSError, ValueError):pass
    obj = desk_object(host, ident)
    target = getattr(obj, 'target', None) if obj is not None else None
    if isinstance(target, dict):
        kind = target.get('kind')
        if kind == 'office' and target.get('id'):keys.add(('office', str(target['id'])))
        elif kind == 'pdf' and target.get('item'):keys.add(('pdf', str(target.get('namespace')), str(target['item'])))
        elif kind == 'document':keys.add(('room', 'DocumentsTab'))
        elif kind == 'investigation':keys.add(('room', 'InvestigationTab'))
        elif kind == 'file' and target.get('path'):
            try:keys.add(('path', str(Path(target['path']).resolve())))
            except (OSError, ValueError):pass
    return keys


def desk_object(host, ident):
    """The board's object of this id (the Field's, the navigation's reading of the desk, or one only the board draws), or None."""
    if not ident:return None
    page = getattr(host, 'field_page', None);nav = getattr(host, 'living_nav', None)
    try:
        obj = page.view.field.get(ident) if page is not None and getattr(page.view, 'field', None) is not None else None
        if obj is None and nav is not None and nav.desk_raw is not None:obj = nav.desk_raw.get(ident)
        board = getattr(page, 'board', None) if page is not None else None
        if obj is None and board is not None and getattr(board, 'desk', None) is not None:obj = board.desk.objects.get(ident)
        return obj
    except (AttributeError, RuntimeError):
        return None


def bring(host, keys):
    """A view of these keys open in the other pane: that pane comes into focus with it in front. Returns the view, or None."""
    sp = split_of(host)
    if sp is None or not sp.on or not keys:return None
    for i in range(sp.other.count()):
        tab = sp.other.widget(i)
        if keys & keys_of(tab):
            sp.activate(tab);return tab
    return None


def bring_object(host, ident):
    """The navigation is about to open an object (living_nav_qt.open, field_page.open_object): when it is open in the other pane,
    that pane comes into focus first, so the opener finds its tab in front instead of opening a second one."""
    if not is_on(host):return None
    try:return bring(host, keys_of_object(host, ident))
    except Exception:  # noqa: BLE001 - finding a tab never stops an opening
        return None


def bring_tab(host, tab):
    """Back or Forward to a view in the other pane: that pane comes into focus. True when the view is in the pane in focus."""
    sp = split_of(host)
    if tab is None:return False
    try:
        if sp is not None and sp.on and sp.other.indexOf(tab) >= 0:sp.activate(tab)
        return host.tabs.indexOf(tab) >= 0
    except RuntimeError:
        return False


def duplicate(host, widget):
    """workspace_tabs.addTab, first: a new view of an object already open in the other pane is not added (that pane comes into
    focus with its view instead). Returns the index of the view brought, or None."""
    sp = split_of(host)
    if sp is None or not sp.on or sp.busy or sp.other.count() == 0:return None
    keys = {k for k in keys_of(widget) if k[0] != 'oid'}
    if not keys:return None
    found = bring(host, keys)
    return host.tabs.indexOf(found) if found is not None else None


def tab_removed(host):
    """workspace_tabs.tabRemoved: the pane in focus lost its last tab while the other still has some: one pane again, so the
    window never falls back to Home (or the board) with a view still open beside it."""
    sp = split_of(host)
    if sp is None or not sp.on or sp.busy:return
    if host.tabs.count() == 0 and sp.other.count() > 0:sp.collapse()


def keeps_split(host, tab):
    """depths_qt.closing: a view closed while the split is on gives its place to the views still open in the split, not to the
    board."""
    sp = split_of(host)
    try:return bool(sp is not None and sp.on and (sp.other.count() > 0 or host.tabs.count() > 1))
    except RuntimeError:
        return False


def before_old_split(host):
    """qt_app.toggle_split_editor: the old split of one text into two editors and this split are never on together."""
    sp = split_of(host)
    if sp is not None and sp.on:sp.collapse()


def collapse(host):
    sp = split_of(host)
    if sp is not None and sp.on:sp.collapse()


def this_object(host):
    """What “this” means to her now, as an object of the desk: the board's focus at board depth (the Field's selection, which
    the board keeps in step), else the object of the view in the pane in focus. None when it is not a desk object."""
    try:
        if getattr(host, '_field_active', False):
            page = getattr(host, 'field_page', None)
            return page.view.selected() if page is not None else None
        if getattr(host, '_home_active', False) or host.central_stack.currentWidget() is not getattr(host, 'workspace_split', None):return None
        nav = getattr(host, 'living_nav', None)
        tab = host.tabs.currentWidget()
        ident = nav.oid_of_tab(tab) if nav is not None and tab is not None else ''
        return desk_object(host, ident) if ident else None
    except (AttributeError, RuntimeError):
        return None


def open_beside(host, ident):
    """Open an object's working view beside the view in front (a tile's Open beside, or a tile dropped on the empty half)."""
    sp = split_of(host);nav = getattr(host, 'living_nav', None)
    if sp is None or nav is None or not ident:return None
    return sp.open_beside(ident)


# ---- pieces --------------------------------------------------------------------------------------------------------------------
def scale_of(host):
    return float((getattr(host, 'reading_profile', None) or {}).get('ui_pt', 14.0)) / 14.0


def diamond(colour, px, filled):
    """The pane mark's shape, so its meaning never rests on colour alone: a filled diamond in focus, an open one beside."""
    pixmap = QPixmap(px, px);pixmap.fill(Qt.transparent)
    p = QPainter(pixmap);p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(colour), max(1.3, px / 9.0));p.setPen(pen);p.setBrush(QColor(colour) if filled else Qt.NoBrush)
    c = px / 2.0;r = px * 0.36
    from PySide6.QtGui import QPolygonF
    p.drawPolygon(QPolygonF([QPointF(c, c - r), QPointF(c + r, c), QPointF(c, c + r), QPointF(c - r, c)]))
    p.end()
    return pixmap


def name_of(host, tab):
    """A view's name as the owner reads it: what the centre bar would call it."""
    if tab is None:return ''
    try:
        if callable(getattr(tab, 'centre_title', None)):
            said = str(tab.centre_title() or '')
            if said:return said
        title = tab.property('ledgerTitle')
        if isinstance(title, str) and title:return title
        for owner in (host.tabs, getattr(split_of(host), 'other', None)):
            if owner is not None and owner.indexOf(tab) >= 0:return owner.tabText(owner.indexOf(tab)).replace('&', '').replace('Preview · ', '').lstrip('◆ ')
    except (RuntimeError, AttributeError):
        pass
    return ''


class PaneMark(QWidget):
    """A pane's quiet mark in the corner of its strip: ◆ In focus, or ◇ Beside · another object."""

    def __init__(self, host, active):
        super().__init__()
        self.host = host;self.active = active;self.setObjectName('SplitMarkFocus' if active else 'SplitMarkBeside')
        row = QHBoxLayout(self);row.setContentsMargins(8, 0, 10, 0);row.setSpacing(5)
        self.glyph = QLabel(self);self.words = QLabel(self);self.words.setTextFormat(Qt.PlainText)
        row.addWidget(self.glyph, 0, Qt.AlignVCenter);row.addWidget(self.words, 0, Qt.AlignVCenter)
        self.setAccessibleName('The pane in focus' if active else 'The other pane')
        self.restyle()

    def restyle(self):
        s = scale_of(self.host);px = max(11, round(13 * s));glyph = max(10, round(12 * s))
        colour = bt.TEAL_TEXT if self.active else bt.FAINT
        self.glyph.setPixmap(diamond(colour, glyph, self.active))
        self.words.setStyleSheet('QLabel {font-family:"%s";font-size:%dpx;color:%s;background:transparent;%s}' % (
            bt.FACE, px, colour, 'font-weight:600;' if self.active else ''))

    def say(self, words, tip):
        if self.words.text() != words:self.words.setText(words)
        self.setToolTip(tip);self.words.setToolTip(tip);self.glyph.setToolTip(tip)


class EmptyHalf(QWidget):
    """The other half while it shows nothing: what can be put there."""

    def __init__(self, split, parent):
        super().__init__(parent)
        self.split = split;self.setObjectName('SplitEmptyHalf');self.setAccessibleName(SAY['empty'])
        box = QVBoxLayout(self);box.setContentsMargins(28, 28, 28, 28);box.setSpacing(10);box.addStretch(1)
        self.title = QLabel(SAY['empty'], self);self.title.setAlignment(Qt.AlignCenter)
        self.words = QLabel(SAY['empty_words'], self);self.words.setWordWrap(True);self.words.setAlignment(Qt.AlignCenter)
        box.addWidget(self.title);box.addWidget(self.words)
        self.choices = QVBoxLayout();self.choices.setSpacing(6);box.addLayout(self.choices);box.addStretch(2)
        self.restyle()

    def restyle(self):
        s = scale_of(self.split.host)
        self.title.setStyleSheet('font-family:"%s";font-size:%dpx;color:%s;background:transparent;' % (bt.FACE, max(13, round(16 * s)), bt.QUIET))
        self.words.setStyleSheet('font-family:"%s";font-size:%dpx;color:%s;background:transparent;' % (bt.FACE, max(11, round(13 * s)), bt.FAINT))
        self.setStyleSheet('QPushButton#SplitEmptyChoice {font-family:"%s";font-size:%dpx;color:%s;background:%s;border:1px solid %s;padding:4px 14px;border-radius:2px;} '
                           'QPushButton#SplitEmptyChoice:hover {color:%s;background:%s;border-color:%s;}' % (
                               bt.FACE, max(12, round(14 * s)), bt.TEXT, bt.RAISED, bt.LINE_STRONG, bt.TEAL_TEXT, bt.TEAL_SOFT, bt.TEAL_EDGE))

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(bt.LINE_MID), 1.4, Qt.DashLine);p.setPen(pen);p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(10, 10, -10, -10), 6, 6);p.end()

    def show_choices(self):
        while self.choices.count():
            item = self.choices.takeAt(0)
            if item.widget() is not None:item.widget().deleteLater()
        host = self.split.host;shown = 0
        for i in range(host.tabs.count()):
            tab = host.tabs.widget(i)
            if tab is None or tab is host.tabs.currentWidget():continue
            button = QPushButton('Show “%s” here' % (name_of(host, tab)[:60] or 'this view'), self)
            button.setCursor(Qt.PointingHandCursor);button.setFocusPolicy(Qt.TabFocus);button.setObjectName('SplitEmptyChoice')
            button.clicked.connect(lambda _=False, r=weakref.ref(tab): self.split.move(alive(r), to_other=True))
            self.choices.addWidget(button, 0, Qt.AlignHCenter);shown += 1
            if shown >= 4:break


class PaneTabs(QTabWidget):
    """The other pane: a strip of its own and its views, beside (or under) the window's own tabs."""

    def __init__(self, split):
        super().__init__()
        self.split = split;self.setObjectName('SplitPane');self.setAccessibleName('The other pane')
        self.setDocumentMode(True);self.setTabsClosable(True);self.setMovable(True)
        self.empty = EmptyHalf(split, self);self.empty.hide()
        bar = self.tabBar()
        bar.setStyleSheet('QTabBar::tab:selected {color:%s;background:transparent;border-bottom:2px dashed %s;}' % (bt.QUIET, bt.LINE_MID))

    def resizeEvent(self, event):
        super().resizeEvent(event);self.place_empty()

    def place_empty(self):
        top = self.tabBar().height() if self.count() else 0
        self.empty.setGeometry(0, top, self.width(), max(0, self.height() - top))

    def tabInserted(self, index):
        super().tabInserted(index);self.empty.hide()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        if self.count() == 0 and self.split.on and not self.split.busy:QTimer.singleShot(0, self.split.sync)


class DropHalf(QWidget):
    """A half of the centre (or of the board) that takes a tab or a tile while one is being dragged."""

    def __init__(self, parent, words, on_drop, mime):
        super().__init__(parent)
        self.words = words;self.on_drop = on_drop;self.mime = mime;self.hot = False
        self.setObjectName('SplitDropHalf');self.setAcceptDrops(True);self.setAccessibleName(words)

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        fill = QColor(bt.TEAL_SOFT);fill.setAlpha(225 if self.hot else 190);p.fillRect(self.rect(), fill)
        pen = QPen(QColor(bt.TEAL_EDGE if self.hot else bt.LINE_STRONG), 2.0, Qt.DashLine);p.setPen(pen)
        p.drawRoundedRect(QRectF(self.rect()).adjusted(8, 8, -8, -8), 8, 8)
        p.setPen(QColor(bt.TEAL_TEXT if self.hot else bt.TEXT))
        font = p.font();font.setPixelSize(max(14, min(22, self.width() // 26)));p.setFont(font)
        p.drawText(QRectF(self.rect()).adjusted(28, 28, -28, -28), Qt.AlignCenter | Qt.TextWordWrap, '⇥  ' + self.words)
        p.end()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(self.mime):
            self.hot = True;self.update();event.acceptProposedAction()
        else:event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(self.mime):event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.hot = False;self.update()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(self.mime):return event.ignore()
        payload = bytes(event.mimeData().data(self.mime)).decode('utf-8', 'replace')
        event.acceptProposedAction()
        QTimer.singleShot(0, lambda p=payload: self.on_drop(p))


def alive(ref):
    try:
        widget = ref() if ref is not None else None
        if widget is not None:widget.objectName()
        return widget
    except RuntimeError:
        return None


class Watch(QObject):
    """While the split is on: a click let go in the other pane brings it into focus (after the click has done its own work)."""

    def __init__(self, split):
        super().__init__(split);self.split = split

    USER = (Qt.MouseFocusReason, Qt.TabFocusReason, Qt.BacktabFocusReason, Qt.ShortcutFocusReason)

    def eventFilter(self, obj, event):
        kind = event.type()
        user = ((kind == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton) or
                (kind == QEvent.FocusIn and event.reason() in self.USER))      # the owner's click or key, never a focus the window moved itself
        if user and isinstance(obj, QWidget):
            sp = self.split
            try:
                if sp.on and not sp.busy and sp.inside_other(obj):
                    ref = weakref.ref(obj);gen = sp.generation
                    QTimer.singleShot(0, lambda: sp.activate_from(ref, gen))
            except RuntimeError:
                pass
        return False


# ---- the split ---------------------------------------------------------------------------------------------------------------
class Split(QObject):
    """The window's two panes. host.tabs is always the pane in focus; `other` is the pane beside it."""

    def __init__(self, host):
        super().__init__(host)
        self.host = host;self.on = False;self.busy = 0;self.tabs_first = True;self.forced = None;self.ratio = None;self.generation = 0
        self.mru = [];self.press = None;self.drop = None
        self.other = PaneTabs(self);self.other.hide()
        self.ws = host.workspace_split
        self.ws.insertWidget(1, self.other)
        self.watch = Watch(self)
        self.focus_mark = PaneMark(host, True);self.focus_mark.hide()
        self.beside_mark = PaneMark(host, False)
        corner = QWidget();corner.setObjectName('SplitCorner');crow = QHBoxLayout(corner);crow.setContentsMargins(0, 0, 6, 0);crow.setSpacing(4)
        self.layout_button = QToolButton(corner)      # One pane is on the centre bar, beside Save and Return; here only how the two sit
        for button, does in ((self.layout_button, self.toggle_layout),):
            button.setAutoRaise(True);button.setCursor(Qt.PointingHandCursor);button.setFocusPolicy(Qt.TabFocus);button.clicked.connect(does)
            button.setObjectName('SplitCornerButton');crow.addWidget(button)
        self.corner = corner
        self.other.setCornerWidget(self.beside_mark, Qt.TopLeftCorner);self.other.setCornerWidget(corner, Qt.TopRightCorner)
        self.other.tabCloseRequested.connect(self.close_other)
        self.other.currentChanged.connect(lambda _=0: self.seen())
        host.tabs.currentChanged.connect(lambda _=0: self.seen())
        for bar in (host.tabs.tabBar(), self.other.tabBar()):
            bar.installEventFilter(self);bar.setContextMenuPolicy(Qt.CustomContextMenu)
            bar.customContextMenuRequested.connect(lambda point, b=bar: self.tab_menu(b, point))
        self.ws.installEventFilter(self)
        self.ws.splitterMoved.connect(self.divider_moved)
        self.button = self.make_button()
        self.restyle()

    # ---- the parts ---------------------------------------------------------------------------------------------------------
    def make_button(self):
        bar = getattr(self.host, 'centre_bar', None)
        row = bar.layout().itemAt(0).layout() if bar is not None and bar.layout() is not None and bar.layout().count() else None
        if row is None:return None
        button = QPushButton(SAY['split']);button.setObjectName('CentreSplit');button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.TabFocus);button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed);button.setAccessibleName('Split the centre')
        button.clicked.connect(self.toggle)
        from .tool_faces import wear
        wear(button, 'split')
        row.addSpacing(8);row.addWidget(button)
        original = bar.sync

        def sync(_original=original):
            _original();self.sync_button()
        bar.sync = sync
        return button

    def restyle(self):
        s = scale_of(self.host);px = max(11, round(13 * s))
        sheet = ('QToolButton#SplitCornerButton {font-family:"%s";font-size:%dpx;color:%s;background:transparent;border:1px solid %s;padding:1px 7px;border-radius:2px;} '
                 'QToolButton#SplitCornerButton:hover {color:%s;background:%s;border-color:%s;}') % (
                    bt.FACE, px, bt.QUIET, bt.LINE, bt.TEAL_TEXT, bt.TEAL_SOFT, bt.TEAL_EDGE)
        self.corner.setStyleSheet(sheet)
        self.focus_mark.restyle();self.beside_mark.restyle();self.other.empty.restyle()

    def sync_button(self):
        button = self.button
        if button is None:return
        try:
            words = SAY['one'] if self.on else SAY['split']
            if button.text() != words:
                button.setText(words)
                from .tool_faces import fit
                fit(button)
            button.setToolTip(SAY['one_tip'] if self.on else SAY['split_tip'])
            button.setEnabled(self.on or self.host.tabs.count() > 0)
        except RuntimeError:
            pass

    # ---- where things are ----------------------------------------------------------------------------------------------------
    def vertical(self):
        return self.ws.orientation() == Qt.Vertical

    def active_side(self):
        first, second = ('top', 'bottom') if self.vertical() else ('left', 'right')
        return first if self.tabs_first else second

    def inside_other(self, widget):
        """A widget of the other pane's views or strip (not its mark or its corner buttons)."""
        if widget is None:return False
        other = self.other
        if widget is other or not (other.isAncestorOf(widget)):return False
        for part in (self.beside_mark, self.corner):
            if widget is part or part.isAncestorOf(widget):return False
        return True

    def seen(self):
        """The tab in front of either pane changed: the newest first in the order of use; the marks say it."""
        if self.busy:return
        for widget in (self.host.tabs.currentWidget(),):
            if widget is None:continue
            self.mru = [r for r in self.mru if alive(r) is not None and alive(r) is not widget][:24]
            self.mru.insert(0, weakref.ref(widget))
        if self.on:self.sync()
        else:self.sync_button()

    def previous(self, exclude):
        """The view in front before `exclude`, in the window's tabs: the one Split sets beside it."""
        for ref in self.mru:
            widget = alive(ref)
            if widget is not None and widget is not exclude and self.host.tabs.indexOf(widget) >= 0:return widget
        for i in range(self.host.tabs.count() - 1, -1, -1):
            widget = self.host.tabs.widget(i)
            if widget is not exclude:return widget
        return None

    # ---- moving views between the panes -------------------------------------------------------------------------------------
    @staticmethod
    def take(owner, index):
        """A tab out of a tab widget, with what its strip showed of it. The view itself is kept."""
        widget = owner.widget(index)
        row = (widget, owner.tabText(index), owner.tabIcon(index), owner.tabToolTip(index))
        owner.removeTab(index)
        return row

    def take_all(self, owner):
        """Every tab out of a tab widget, the one in front last (so no other view is shown on the way): [row], its index.
        Taken from the end, a tab's place is still its first place when its turn comes; the one in front is then the first."""
        count = owner.count();current = owner.currentIndex();rows = [None] * count
        for index in range(count - 1, -1, -1):
            if index != current:rows[index] = self.take(owner, index)
        if 0 <= current < count:rows[current] = self.take(owner, 0)
        return [row for row in rows if row is not None], max(0, current)

    @staticmethod
    def put_all(owner, rows, current):
        """Tabs into a tab widget, the one in front first (so no other view is shown on the way), in their order."""
        if not rows:return
        current = current if 0 <= current < len(rows) else 0
        first = rows[current]
        QTabWidget.insertTab(owner, owner.count(), first[0], first[2], first[1])
        base = owner.indexOf(first[0])
        for offset, row in enumerate(rows[:current]):
            QTabWidget.insertTab(owner, base + offset, row[0], row[2], row[1])
        for row in rows[current + 1:]:
            QTabWidget.insertTab(owner, owner.count(), row[0], row[2], row[1])
        for row in rows:
            owner.setTabToolTip(owner.indexOf(row[0]), row[3])
        owner.setCurrentWidget(first[0])

    @staticmethod
    def working_title(row):
        """A tab set in the split is a working tab: its name without the Preview's word."""
        text = row[1]
        return text[len('Preview · '):] if text.startswith('Preview · ') else text

    def remember_places(self, widgets):
        from .living_nav_qt import doc_position
        places = {}
        for widget in widgets:
            if widget is None:continue
            try:places[widget] = doc_position(widget)
            except RuntimeError:pass
        return places

    def put_places(self, places):
        from .living_nav_qt import set_doc_position
        for widget, place in places.items():
            if place:
                try:set_doc_position(widget, place)
                except RuntimeError:pass
        refs = [(weakref.ref(w), p) for w, p in places.items() if p]
        QTimer.singleShot(0, lambda: [set_doc_position(alive(r), p) for r, p in refs if alive(r) is not None])

    def activate_from(self, ref, generation):
        """A click or the keyboard reached the other pane: it comes into focus, once. A click that also moved the keyboard asks
        twice; any ask made before the last exchange of the panes is stale and does nothing."""
        widget = alive(ref)
        if widget is None or generation != self.generation or not self.on or self.busy or not self.inside_other(widget):return False
        return self.activate(None, focus=widget)

    def activate(self, tab=None, focus=None):
        """Bring the other pane into focus (with `tab` in front of it, when given): the two panes exchange their tabs and their
        places in the divider, so on the screen nothing moves but which pane is in focus. The view the owner clicked keeps
        the keyboard. True when it was done."""
        host = self.host;tabs = host.tabs;other = self.other
        if not self.on or self.busy or other.count() == 0:return False
        if tab is not None and other.indexOf(tab) < 0:
            return tabs.indexOf(tab) >= 0
        nav = getattr(host, 'living_nav', None)
        if nav is not None:
            try:nav.snapshot()      # the view being left: its place in the history is the place it is left at
            except Exception:  # noqa: BLE001
                pass
        if tab is not None:other.setCurrentWidget(tab)
        a_front, b_front = tabs.currentWidget(), other.currentWidget()
        places = self.remember_places((a_front, b_front))
        sizes = self.ws.sizes()
        self.busy += 1;self.generation += 1;self.ws.setUpdatesEnabled(False);tabs.blockSignals(True)
        try:
            a_rows, a_cur = self.take_all(tabs)
            b_rows, b_cur = self.take_all(other)
            self.put_all(tabs, b_rows, b_cur)
            self.put_all(other, a_rows, a_cur)
            self.ws.insertWidget(0, other if self.tabs_first else tabs)
            self.tabs_first = not self.tabs_first
            if len(sizes) >= 2:self.ws.setSizes(sizes)      # the slots keep their sizes on the screen; only the panes in them changed
        finally:
            tabs.blockSignals(False);self.ws.setUpdatesEnabled(True);self.busy -= 1
        self.put_places(places)
        try:
            target = focus if focus is not None and tabs.isAncestorOf(focus) else tabs.currentWidget()
            if target is not None:target.setFocus(Qt.MouseFocusReason)
        except RuntimeError:
            pass
        self.seen()
        tabs.currentChanged.emit(tabs.currentIndex())      # one change: the centre bar, the tree's highlight, her "this", the line
        return True

    def move(self, tab, to_other=True):
        """One tab to the other pane (or back into the pane in focus). It becomes a working tab, never the Preview. A view moved
        out of the pane in focus leaves the one used before it in front there."""
        host = self.host;tabs = host.tabs;other = self.other
        if tab is None:return False
        source, target = (tabs, other) if to_other else (other, tabs)
        index = source.indexOf(tab)
        if index < 0:return False
        if not self.on:self.open_split()
        back_to = self.previous(tab) if to_other and tab is tabs.currentWidget() else tabs.currentWidget()
        places = self.remember_places((tab, back_to))
        self.busy += 1;self.generation += 1;tabs.blockSignals(True)
        try:
            row = self.take(source, index)
            QTabWidget.insertTab(target, target.count(), row[0], row[2], self.working_title(row));target.setTabToolTip(target.indexOf(row[0]), row[3])
            target.setCurrentWidget(row[0])
            if hasattr(tabs, 'working'):tabs.working(tab, retitle=False)
            if to_other and back_to is not None and tabs.indexOf(back_to) >= 0:tabs.setCurrentWidget(back_to)
        finally:
            tabs.blockSignals(False);self.busy -= 1
        if to_other and tabs.count() == 0:
            self.activate(tab)      # nothing left in focus: the moved view is the one in focus
        else:
            self.put_places(places);self.seen();self.sync()
            tabs.currentChanged.emit(tabs.currentIndex())
        return True

    # ---- on and off ----------------------------------------------------------------------------------------------------------
    def open_split(self):
        """The two panes, the window's own on the first side; the divider in the middle."""
        host = self.host
        if self.on:return True
        if getattr(host, 'split_editor', None) is not None and hasattr(host, '_close_split'):host._close_split()      # one split at a time
        self.on = True;self.tabs_first = True
        self.ws.insertWidget(0, host.tabs);self.ws.insertWidget(1, self.other)
        self.ws.setChildrenCollapsible(False)
        self.other.show();self.orient()
        host.tabs.setCornerWidget(self.focus_mark, Qt.TopLeftCorner);self.focus_mark.show()
        app = QApplication.instance()
        if app is not None:app.installEventFilter(self.watch)
        QTimer.singleShot(0, self.even)
        self.even()
        return True

    def even(self):
        sizes = self.ws.sizes()
        if len(sizes) >= 2 and self.on:
            whole = sizes[0] + sizes[1];first = whole // 2 if self.ratio is None else int(whole * self.ratio)
            self.ws.setSizes([first, whole - first] + [0] * (len(sizes) - 2))

    def split(self, tab=None):
        """Split: the view the owner names (or the one in front) and the one before it, side by side. A named view that is not
        the one in front goes beside it; the one in front goes to the second half, with the view before it in the first."""
        host = self.host;tabs = host.tabs
        if self.on:return True
        if tabs.count() == 0:
            host.statusBar().showMessage(SAY['split_none'], 7000);return False
        current = tabs.currentWidget()
        if tab is not None and tab is not current and tabs.indexOf(tab) >= 0:
            moving, front_second = tab, False
        else:
            moving, front_second = self.previous(current), True
        self.open_split()
        if moving is not None:
            self.busy += 1
            try:
                places = self.remember_places((moving,))
                row = self.take(tabs, tabs.indexOf(moving))
                QTabWidget.insertTab(self.other, 0, row[0], row[2], self.working_title(row));self.other.setTabToolTip(0, row[3]);self.other.setCurrentIndex(0)
                tabs.setCurrentWidget(current)
                if hasattr(tabs, 'working'):tabs.working(moving, retitle=False)
            finally:
                self.busy -= 1
            self.put_places(places)
            if front_second:
                self.ws.insertWidget(0, self.other);self.tabs_first = False
        self.even();self.sync()
        tabs.currentChanged.emit(tabs.currentIndex())
        return True

    def collapse(self):
        """One pane: the other pane's tabs join the window's, after its own; the view in front stays in front. Every tab kept."""
        host = self.host;tabs = host.tabs
        if not self.on:return False
        front = tabs.currentWidget()
        places = self.remember_places((front, self.other.currentWidget()))
        self.busy += 1;self.generation += 1;tabs.blockSignals(True)
        try:
            rows, current = self.take_all(self.other)
            for row in rows:
                if row is None:continue
                QTabWidget.insertTab(tabs, tabs.count(), row[0], row[2], row[1]);tabs.setTabToolTip(tabs.indexOf(row[0]), row[3])
            if front is not None and tabs.indexOf(front) >= 0:tabs.setCurrentWidget(front)
            elif rows and 0 <= current < len(rows) and rows[current] is not None:tabs.setCurrentWidget(rows[current][0])
            self.on = False
            self.other.hide();self.ws.insertWidget(0, tabs);self.ws.insertWidget(1, self.other);self.tabs_first = True
            self.ws.setOrientation(Qt.Horizontal)
            tabs.setCornerWidget(None, Qt.TopLeftCorner);self.focus_mark.hide()
        finally:
            tabs.blockSignals(False);self.busy -= 1
        app = QApplication.instance()
        if app is not None:app.removeEventFilter(self.watch)
        self.put_places(places)
        self.sync_button()
        tabs.currentChanged.emit(tabs.currentIndex())
        return True

    def toggle(self):
        if self.on:return self.collapse()
        return self.split()

    # ---- the narrow centre ----------------------------------------------------------------------------------------------------
    def too_narrow(self):
        return self.ws.width() < 2 * MIN_PANE + self.ws.handleWidth()

    def orient(self):
        if not self.on:return
        vertical = self.forced if self.forced is not None else self.too_narrow()
        want = Qt.Vertical if vertical else Qt.Horizontal
        if self.ws.orientation() != want:
            self.ws.setOrientation(want);QTimer.singleShot(0, self.even)
        self.sync_layout_button()

    def sync_layout_button(self):
        if self.vertical():
            self.layout_button.setText(SAY['side']);self.layout_button.setToolTip(SAY['side_tip'] if self.too_narrow() else SAY['side_tip_wide'])
        else:
            self.layout_button.setText(SAY['stack']);self.layout_button.setToolTip(SAY['stack_tip'])

    def toggle_layout(self):
        self.forced = not self.vertical()
        self.ratio = None;self.orient();self.even()

    def divider_moved(self, *_):
        if not self.on or self.busy:return
        sizes = self.ws.sizes()
        if len(sizes) >= 2 and sizes[0] + sizes[1] > 0:
            first = sizes[0] / float(sizes[0] + sizes[1])
            self.ratio = first if self.tabs_first else first      # the divider's place is the screen's, whichever pane is in focus

    # ---- the marks -------------------------------------------------------------------------------------------------------------
    def sync(self):
        """The marks say which pane is in focus and that the other shows another object; the empty half offers what to show."""
        if not self.on:
            self.sync_button();return
        host = self.host
        try:
            self.focus_mark.say(SAY['focus'], SAY['focus_tip'])
            other_front = self.other.currentWidget();front = host.tabs.currentWidget()
            if other_front is None:
                self.beside_mark.say(SAY['beside_empty'], SAY['empty_tip'])
                self.other.empty.show_choices();self.other.place_empty();self.other.empty.show();self.other.empty.raise_()
            else:
                self.other.empty.hide()
                same = bool({k for k in keys_of(other_front) if k[0] != 'room'} & {k for k in keys_of(front) if k[0] != 'room'})
                self.beside_mark.say(SAY['beside_same'] if same else SAY['beside'], SAY['beside_tip'] % (name_of(host, other_front) or 'a view'))
            self.sync_layout_button()
            self.sync_button()
            for owner in (host.tabs, self.other):
                owner.tabBar().setVisible(True)
        except RuntimeError:
            pass

    # ---- events ------------------------------------------------------------------------------------------------------------------
    def eventFilter(self, watched, event):
        kind = event.type()
        if watched is self.ws:
            if kind == QEvent.Resize and self.on:QTimer.singleShot(0, self.orient)
            return False
        if kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            index = watched.tabAt(event.position().toPoint())
            self.press = (watched, index, event.position().toPoint()) if index >= 0 else None
        elif kind == QEvent.MouseMove and self.press is not None and event.buttons() & Qt.LeftButton:
            bar, index, start = self.press
            if bar is watched and abs(event.position().toPoint().y() - start.y()) > max(28, bar.height()):
                self.press = None
                owner = self.host.tabs if bar is self.host.tabs.tabBar() else self.other
                tab = owner.widget(index)
                # the strip's own moving of the tab ends where it began; the tab is carried instead
                release = QMouseEvent(QEvent.MouseButtonRelease, QPointF(start), QPointF(bar.mapToGlobal(start)), Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
                QApplication.sendEvent(bar, release)
                if tab is not None:self.drag_tab(tab, owner)
                return True
        elif kind == QEvent.MouseButtonRelease:
            self.press = None
        return False

    # ---- dragging --------------------------------------------------------------------------------------------------------------
    def drop_half(self, parent, words, on_drop, mime, half='second'):
        """A drop target over the second half (right, or bottom when stacked) of `parent`, or over a whole pane."""
        self.end_drop()
        stacked = parent is self.ws and ((self.on and self.vertical()) or (not self.on and (self.forced if self.forced is not None else self.too_narrow())))
        r = parent.rect();x0 = y0 = 0
        if parent is self.ws and self.ws.parentWidget() is not None:      # a splitter takes a child as a pane of its own: the target sits over it instead
            x0, y0 = self.ws.geometry().x(), self.ws.geometry().y();parent = self.ws.parentWidget()
        drop = DropHalf(parent, words, on_drop, mime)
        if half == 'whole':drop.setGeometry(x0, y0, r.width(), r.height())
        elif stacked:drop.setGeometry(x0, y0 + r.height() // 2, r.width(), r.height() - r.height() // 2)
        else:drop.setGeometry(x0 + r.width() // 2, y0, r.width() - r.width() // 2, r.height())
        drop.show();drop.raise_();self.drop = drop
        return drop

    def end_drop(self):
        drop, self.drop = self.drop, None
        if drop is not None:
            try:drop.hide();drop.deleteLater()
            except RuntimeError:pass

    def tab_drop(self, tab, owner):
        """Where a tab dragged out of a strip goes: the other pane (or the empty half when there is one pane)."""
        host = self.host;ref = weakref.ref(tab);name = name_of(host, tab) or 'this view'
        if self.on:
            target = self.other if owner is host.tabs else host.tabs
            words = SAY['drop_tab'] % (name, name_of(host, target.currentWidget()) or 'the other view') if target.count() else SAY['drop_tab_alone'] % name
            return self.drop_half(target, words, lambda _p: self.move(alive(ref), to_other=owner is host.tabs), TAB_MIME, 'whole')
        front = host.tabs.currentWidget()
        beside = self.previous(tab) if tab is front else front
        words = SAY['drop_tab'] % (name, name_of(host, beside)) if beside is not None else SAY['drop_tab_alone'] % name
        return self.drop_half(self.ws, words, lambda _p: self.split(alive(ref)), TAB_MIME)

    def drag_tab(self, tab, owner):
        self.tab_drop(tab, owner)
        try:
            data = QMimeData();data.setData(TAB_MIME, str(id(tab)).encode('utf-8'))
            drag = QDrag(owner.tabBar());drag.setMimeData(data)
            drag.exec(Qt.MoveAction)
        finally:
            QTimer.singleShot(0, self.end_drop)

    def tile_drop(self, view, ident, title):
        """Where a tile dragged off the board goes: the board's second half, to open it beside the view in front."""
        host = self.host
        front = host.tabs.currentWidget() if host.tabs.count() else None
        words = SAY['drop_tile'] % (title, name_of(host, front)) if front is not None else SAY['drop_tile_alone'] % title
        return self.drop_half(view, words, lambda p: self.open_beside(p), OBJECT_MIME)

    def drag_tile(self, view, ident, title=''):
        self.tile_drop(view, ident, title or ident)
        try:
            data = QMimeData();data.setData(OBJECT_MIME, str(ident).encode('utf-8'));data.setText(title or ident)
            drag = QDrag(view);drag.setMimeData(data)
            drag.exec(Qt.CopyAction)
        finally:
            QTimer.singleShot(0, self.end_drop)
        return True

    # ---- opening beside -----------------------------------------------------------------------------------------------------------
    def open_beside(self, ident):
        """The object's working view beside the view in front: in the other pane when the split is on (that pane then in focus),
        else the split opens with the view in front in the first half and this one in the second. Nothing else open: it opens
        alone, and the status line says so."""
        host = self.host;nav = host.living_nav
        known = {id(w) for w in all_tabs(host)}
        before = host.tabs.currentWidget() if host.tabs.count() else None
        nav.open(ident)
        front = host.tabs.currentWidget()
        if front is None:return None
        new = id(front) not in known
        if self.on:
            if new and host.tabs.count() > 1:      # it opened in the pane in focus: it goes to the other half, which comes into focus
                self.move(front, to_other=True);self.activate(front)
            self.sync()
            return host.tabs.currentWidget()
        if before is None or before is front:
            host.statusBar().showMessage(SAY['opened_alone'] % (name_of(host, front) or 'it'), 7000)
            return front
        self.mru = [r for r in self.mru if alive(r) not in (before, front)]
        self.mru[0:0] = [weakref.ref(front), weakref.ref(before)]
        self.split()
        return front

    # ---- the tabs' own menu ------------------------------------------------------------------------------------------------------
    def tab_menu(self, bar, point):
        host = self.host
        mine = bar is host.tabs.tabBar();owner = host.tabs if mine else self.other
        index = bar.tabAt(point)
        if index < 0:return None
        tab = owner.widget(index);name = name_of(host, tab) or 'this view'
        menu = QMenu(bar);menu.setObjectName('SplitTabMenu')
        ref = weakref.ref(tab)
        if mine and not self.on:
            if tab is host.tabs.currentWidget():
                act = menu.addAction(SAY['split'], lambda: self.split())
                act.setEnabled(self.previous(tab) is not None)
            else:
                menu.addAction('Show beside the one in front', lambda: self.split(alive(ref)))
        elif mine:
            menu.addAction('Move to the other pane', lambda: self.move(alive(ref), to_other=True))
            menu.addAction(SAY['one'], self.collapse)
        else:
            menu.addAction('Bring into focus', lambda: self.activate(alive(ref)))
            menu.addAction('Move to the pane in focus', lambda: self.move(alive(ref), to_other=False))
            menu.addAction(SAY['one'], self.collapse)
        menu.addSeparator()
        menu.addAction('Close “%s”' % name[:50], lambda: self.close_view(alive(ref)))
        menu.popup(bar.mapToGlobal(point))
        self._menu = menu
        return menu

    def close_view(self, tab):
        if tab is None:return False
        if self.other.indexOf(tab) >= 0:self.activate(tab)
        index = self.host.tabs.indexOf(tab)
        return self.host.close_tab(index) if index >= 0 else False

    def close_other(self, index):
        """The close mark of a tab in the other pane: that pane comes into focus, and the window closes the view its own way
        (changes not saved are asked about)."""
        tab = self.other.widget(index)
        if tab is not None:QTimer.singleShot(0, lambda r=weakref.ref(tab): self.close_view(alive(r)))


def install(host):
    if getattr(host, 'l5_split', None) is not None:return host.l5_split
    if getattr(host, 'workspace_split', None) is None or getattr(host, 'tabs', None) is None:return None
    host.l5_split = Split(host)
    return host.l5_split
