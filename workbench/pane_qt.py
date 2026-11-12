"""The desk's two panes (HATCH DESK D1b; the owner's brief of 2026-11-06: "Left pane. Machine, Cabinet, and Settings each show a
tree with visible connecting branches. Pin a larger Trash at the lower right. The tabs, the active tree, and Trash are the
visible controls." and "Right pane. Conversation is for talking with the assistant. Activity shows the actions it took, the
results it got, and what it needs from me. Context shows the files, selections, and instructions in use"; and "Be obsessive
in symmetry").

    left pane, P wide                                   right pane, P wide
    | Machine · Cabinet · Settings |  (the tab row)     | Conversation · Activity · Context |
    | the active tree, inset I     |  (the content)     | the active face, inset I          |
    | ............... Trash        |  (the foot)        |          (Trash's mirror, empty)  |

Both panes are PaneBody widgets laid out by hand, on whole pixels, from the same numbers, so every part of one is the mirror of
the same part of the other: the tab rows (three equal tabs sharing the room between the insets, each row centred on its pane,
one word size for all six, the menus' size or less in a narrow pane so every word stays whole; the active tab's short yellow
mark one length and one offset under every tab of both panes), the content boxes, the feet. Trash sits at the left
pane's lower right, beside the workspace (D1-fix: its box is exactly its drawing, so its ink is the inset from the pane's inner
edge and bottom); the same place in the right pane is kept empty, so the panes' feet balance. A pane's least width counts each
face's scrolled page (content_minimum), so no face is wider than its pane. The three
left trees are BranchTree: one row height, one indentation, the same connecting branch lines. desk_qt.apply calls place().

The pure part (tab_row, tab_px, tab_mark, tree_metrics, trash_size, foot_height, pane_parts) needs no QApplication and is tested by
tests_integrated/test_desk.py; the live panes are measured by tools/check_desk_ui.py with tools/symmetry.py.
"""
from __future__ import annotations
from . import desk_qt

TAB_GAP = 0         # the gap between two tabs: none, the three tabs share the room between the insets (their words have the most room)
TAB_AIR = 4         # room each side of the widest tab word, drawn bold, inside its tab, at 14 pt, scaled
TAB_FLOOR = 0.70    # the tab words may be set this much smaller than the menu words (never under 11 px) to stay whole in a narrow pane
CONTENT_GAP = 8     # between the tab row and the content, and between the content and the foot, at 14 pt, scaled
ROW_PAD = 12        # a tree row is its line of text and this much, at 14 pt, scaled
INDENT = 22         # one tree level at 14 pt, scaled
TRASH_CAN = 30      # Trash's can at 14 pt, scaled (22 px before the desk)
TRASH_PAD = 8       # between Trash's can and its word, at 14 pt, scaled (the count keeps half of it)
MARK = 4            # the active tab's measured amber rail, in pixels
CENTRE_MIN_HEIGHT = 240  # the workspace's least height asked of the window (its pages scroll or yield inside it)
LEFT_WORDS = ('Files', 'Machine', 'Settings')
RIGHT_WORDS = ('Talk', 'Activity', 'Context')
# Paper v1.1 (shell2's palette, repeated so this module needs no window code): graphite words, quieter graphite for the tabs
# not chosen, a faint rule under each tab row, pencil-grey branch lines, eraser pink for a selected row.
from .boss_theme import TEXT, QUIET, LINE, LINE_STRONG as BRANCH, ERASER, GROUND
TREE_STYLE = ('QTreeWidget {border:0;background:transparent;color:%s;show-decoration-selected:0;} QTreeWidget::item {padding:0 2px;border:0;} '
              'QTreeWidget::item:selected {background:%s;color:%s;} QTreeWidget::branch, QTreeWidget::branch:selected {background:transparent;border:0;image:none;}'
              % (TEXT, ERASER, TEXT))


def tab_row(pane, inset, gap, n, least):
    """n tabs across a pane `pane` px wide: equal widths T (as wide as the room between the insets allows with `gap` between
    them, never under `least`; when `least` does not fit the gaps close up first), equal gaps, and the row centred on the
    pane: its spare pixels split evenly between the two ends (when they would split odd, the tabs give up a pixel, or take one
    when they are at `least`; with an even count the gaps do). Returns (left edges relative to the pane, T, gap)."""
    pane, inset, gap, n, least = int(pane), int(inset), int(gap), int(n), int(least)
    if n < 1:return [], 0, 0
    inner = pane - 2 * inset;g = gap if n > 1 else 0
    T = (inner - (n - 1) * g) // n
    if T < least:
        T = least;g = max(0, (inner - n * T) // (n - 1)) if n > 1 else 0
    if (pane - n * T - (n - 1) * g) % 2:
        if n % 2 and T - 1 >= least:T -= 1
        elif n % 2:T += 1;g = max(0, g - 2) if n > 1 else 0  # at `least`: a pixel more each, two less in each gap
        else:g = g - 1 if g > 0 else g + 1
    x0 = (pane - n * T - (n - 1) * g) // 2
    return [x0 + i * (T + g) for i in range(n)], T, g


def tab_px(T, top, floor, air, widest):
    """One size for all six tab words: the menus' size `top`, or the largest size down to `floor` at which the widest word,
    drawn bold (widest(px)), and `air` each side fit a tab T wide. Both panes take the same size, so they stay mirrored, and
    every word stays whole: a narrow pane sets its tab words smaller instead of eliding one."""
    for px in range(int(top), int(floor) - 1, -1):
        if widest(px) + 2 * int(air) <= int(T):return px
    return int(floor)


def tab_mark(T, word):
    """The active tab's short mark: (offset in the tab, length). One length for every tab (`word`, the shortest tab word, so
    the mark is never longer than the word above it), centred, on whole pixels (the length gives up a pixel when T - length
    is odd), so it has one offset in every tab and mirrors exactly."""
    T, length = int(T), max(0, min(int(word), int(T)))
    if (T - length) % 2:length -= 1
    return (T - length) // 2, length


def tree_metrics(line_px, scale):
    """(row height, indentation) shared by the three left trees: a line of text and ROW_PAD, and INDENT, both scaled."""
    return int(line_px) + desk_qt.scaled(ROW_PAD, scale), desk_qt.scaled(INDENT, scale)


def trash_size(scale, word_px, count_px, ink=None, count_gap=None):
    """Trash's box, exactly what it draws (D1-fix): the can's ink (`ink`, trash_can_qt.can_ink: left, top, right, bottom in its
    square), TRASH_PAD, the word Trash's ink (`word_px` wide), and room for a three-digit count (`count_gap` and `count_px`);
    as tall as the can's ink (a full can's sheet included). Scaled. Without `ink`, the can's square stands for it."""
    import math
    pad = desk_qt.scaled(TRASH_PAD, scale);can = desk_qt.scaled(TRASH_CAN, scale)
    left, top, right, bottom = ink if ink is not None else (0.0, 0.0, float(can), float(can))
    gap = max(4, pad // 2) if count_gap is None else int(count_gap)
    return math.ceil(right - left) + pad + int(word_px) + gap + int(count_px), math.ceil(bottom - top)


def foot_height(scale, trash_h, inset):
    """Both feet's height: the content gap above Trash's box and the inset below it (the right foot is as tall, and empty)."""
    return desk_qt.scaled(CONTENT_GAP, scale) + int(trash_h) + int(inset)


def pane_parts(width, height, inset, tabs_h, gap, foot_h):
    """The three parts of a pane `width` by `height`: (tabs, content, foot) as (x, y, w, h). The tab row spans the pane (its
    tabs are placed in it by tab_row), the content starts `gap` under it, inset by `inset` on both sides, and reaches the foot,
    which spans the pane at the bottom (its own top gap is inside it, foot_height)."""
    width, height = int(width), int(height)
    top = int(tabs_h) + int(gap);foot = int(foot_h)
    return ((0, 0, width, int(tabs_h)), (int(inset), top, max(0, width - 2 * int(inset)), max(0, height - top - foot)),
            (0, max(0, height - foot), width, foot))


# The Qt part ----------------------------------------------------------------------------------------------------------------

from PySide6.QtCore import QPointF, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QPushButton, QStyledItemDelegate, QTreeWidget, QWidget


def tab_font(scale, bold=False, px=None):
    """The tab words: the bands' menu size (desk_qt.menu_px) or `px`, Plex; the chosen tab drawn semi-bold."""
    font = QFont('IBM Plex Mono');font.setPixelSize(int(px) if px else desk_qt.menu_px(scale))
    if bold:font.setWeight(QFont.DemiBold)
    return font


def widest_bold(words):
    """widest(px): the widest of `words` drawn bold at px (for tab_px)."""
    return lambda px:max(QFontMetrics(tab_font(1.0, True, px)).horizontalAdvance(word) for word in words)


class PaneTab(QPushButton):
    """One tab of a pane: its word centred in a box of the shared width; the chosen tab in graphite, semi-bold, with the short
    pencil-yellow mark under it; keyboard focus and the pointer put the eraser-pink mark in the same place. A checkable push
    button, so callers keep click(), isChecked() and the accessible words."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent);self.setCheckable(True);self.setFocusPolicy(Qt.StrongFocus);self.setAccessibleName(text)
        self.setProperty('paneTab', True);self.mark = (0, 0);self.toggled.connect(lambda *_:self.update())

    def sizeHint(self):
        return QSize(max(self.width(), QFontMetrics(tab_font(1.0, True)).horizontalAdvance(self.text())), max(self.height(), 1))

    def minimumSizeHint(self):return QSize(0, 0)

    def enterEvent(self, event):super().enterEvent(event);self.update()

    def leaveEvent(self, event):super().leaveEvent(event);self.update()

    def mark_rect(self):
        """The mark's place in the tab (x, y, w, h), whether or not the tab is chosen."""
        x, length = self.mark;return QRect(x, self.height() - MARK, length, MARK)

    def mark_colour(self):
        """The colour the tab draws its mark in now, or None."""
        if self.hasFocus() or self.underMouse():return desk_qt.ERASER_MARK
        return desk_qt.PENCIL if self.isChecked() else None

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.TextAntialiasing)
        font = QFont(self.font());font.setWeight(QFont.DemiBold if self.isChecked() else QFont.Normal)
        p.setFont(font);p.setPen(QColor(TEXT if self.isChecked() else QUIET))
        p.drawText(self.rect().adjusted(0, MARK, 0, -MARK), Qt.AlignCenter, self.text())
        colour = self.mark_colour()
        if colour is not None and self.mark[1]:p.fillRect(self.mark_rect(), QColor(colour))
        p.end()


class PaneTabs(QWidget):
    """A pane's row of three tabs, placed by place() on whole pixels; a faint rule under the row from inset to inset."""

    def __init__(self, words, name, host=None):
        super().__init__();self.host = host;self.setObjectName('PaneTabs');self.setAccessibleName(name)
        self.buttons = [PaneTab(word, self) for word in words];self.inset = 16;self.need = 0
        self.setFixedHeight(56)

    def place(self, xs, top, T, h, mark, font, inset, need):
        key = (tuple(int(x) for x in xs), int(top), int(T), int(h), tuple(mark), font.family(), font.pixelSize(), int(inset), int(need), self.width())
        if key == getattr(self, 'placed', None):return  # the desk re-runs every half second: nothing to redo, nothing to repaint
        self.placed = key
        self.inset = int(inset);self.need = int(need);height = int(top) + int(h)
        if self.height() != height:self.setFixedHeight(height)
        # The tab words' size through a style sheet (the window's sheet sizes every push button; a widget's own sheet wins),
        # with no padding or border: the words' room is the whole tab, as the style reports it (tools/ui_fit measures it so).
        sheet = ("QPushButton[paneTab=\"true\"] {font-family:'%s';font-size:%dpx;padding:0;margin:0;border:0;background:transparent;}"
                 % (font.family(), font.pixelSize()))
        if self.styleSheet() != sheet:self.setStyleSheet(sheet)
        for button, x in zip(self.buttons, xs):
            button.mark = mark
            if button.geometry() != QRect(int(x), int(top), int(T), int(h)):button.setGeometry(int(x), int(top), int(T), int(h))
            button.update()
        self.update()

    def minimumSizeHint(self):return QSize(self.need, self.height())

    def sizeHint(self):return self.minimumSizeHint()

    def paintEvent(self, event):
        p = QPainter(self);p.setPen(QPen(QColor(LINE), 1));y = self.height() - 1
        p.drawLine(self.inset, y, self.width() - self.inset - 1, y);p.end()


class PaneFoot(QWidget):
    """A pane's foot: the left one holds Trash at its lower right, beside the workspace; the right one is as tall and empty."""

    def __init__(self, name):
        super().__init__();self.setObjectName('PaneFoot');self.setAccessibleName(name);self.trash = None;self.slot = QRect()
        self.setFixedHeight(70)

    def minimumSizeHint(self):
        return QSize(self.trash.width() if self.trash is not None else 0, self.height())


class PaneBody(QWidget):
    """A pane: the tab row, the content inset by the desk's inset, and the foot, laid out by hand (pane_parts)."""

    def __init__(self, tabs, content, foot, name):
        super().__init__();self.setObjectName('PaneBody');self.setAccessibleName(name)
        self.tabs, self.content, self.foot = tabs, content, foot;self.inset = 16;self.gap = 8
        for part in (tabs, content, foot):part.setParent(self);part.show()

    def arrange(self):
        tabs, content, foot = pane_parts(self.width(), self.height(), self.inset, self.tabs.height(), self.gap, self.foot.height())
        for part, box in ((self.tabs, tabs), (self.content, content), (self.foot, foot)):
            if part.geometry() != QRect(*box):part.setGeometry(*box)
        if self.foot.trash is not None and self.foot.trash.geometry() != self.foot.slot:self.foot.trash.setGeometry(self.foot.slot)

    def resizeEvent(self, event):super().resizeEvent(event);self.arrange()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QColor(BRANCH))
        x = self.width() - 1 if self.foot.trash is not None else 0
        painter.drawLine(x, 0, x, self.height() - 1)
        painter.end()

    def content_minimum(self):
        """The content's least width: its own, and (D1-fix) what each face's scrolled page needs, which a scroll area keeps
        from its own minimum. Every face counts, shown or not, so the pane's width does not change with the tab; a page that
        needs more than the pane would scroll sideways (Activity did at 1280 by 800 and 18 pt), so the desk's width learns it."""
        from PySide6.QtWidgets import QScrollArea, QSizePolicy
        policy = self.content.sizePolicy().horizontalPolicy()
        hint = 0 if policy == QSizePolicy.Ignored else self.content.minimumSizeHint().width()
        for area in self.content.findChildren(QScrollArea):
            inner = area.widget()
            if inner is None or not area.widgetResizable() or area.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOn:continue
            bar = 0 if area.verticalScrollBarPolicy() == Qt.ScrollBarAlwaysOff else area.verticalScrollBar().sizeHint().width()
            hint = max(hint, inner.minimumSizeHint().width() + bar + 2 * area.frameWidth())
        return max(hint, self.content.minimumWidth())

    def minimumSizeHint(self):
        width = max(self.tabs.minimumSizeHint().width(), self.content_minimum() + 2 * self.inset, self.foot.minimumSizeHint().width() + 2 * self.inset)
        return QSize(width, self.tabs.height() + 2 * self.gap + self.foot.height() + 60)

    def sizeHint(self):return self.minimumSizeHint()


# The trees ------------------------------------------------------------------------------------------------------------------

def next_visible(view, index):
    """Whether a row below `index` among its siblings is shown (so the branch line carries on past it)."""
    parent = index.parent();model = view.model()
    return any(not view.isRowHidden(row, parent) for row in range(index.row() + 1, model.rowCount(parent)))


def draw_branches(view, painter, rect, index):
    """The connecting branch lines and the open or closed chevron of one row, the same in every left tree: a one-pixel
    pencil-grey line down each level that has rows still to come, an elbow from the parent's line to the row (to its chevron,
    or toward its words for a row with nothing inside), a short stem from an open row's chevron down to its first child, and
    the chevron in graphite. Roots stand on their own (a chevron, no line)."""
    step = view.indentation()
    if step <= 0 or rect.width() < step:return
    model = view.model();own = rect.right() + 1 - step;mid = rect.top() + rect.height() // 2;cx = own + step // 2
    has = model.hasChildren(index);half = max(3, round(step * 0.18))
    painter.save();painter.setRenderHint(QPainter.Antialiasing, False)
    painter.fillRect(rect, QColor(GROUND))  # a chosen row is marked over its words only; the branches stay on plain paper
    line = QPen(QColor(BRANCH), 1);line.setCosmetic(True);painter.setPen(line)
    parent = index.parent()
    if parent.isValid() and own - step >= rect.left():
        px = own - step + step // 2
        painter.drawLine(px, rect.top(), px, mid)
        if next_visible(view, index):painter.drawLine(px, mid, px, rect.bottom())
        painter.drawLine(px, mid, (cx - half - 3) if has else (rect.right() - 3), mid)
        x = px - step;ancestor = parent
        while ancestor.parent().isValid() and x >= rect.left():
            if next_visible(view, ancestor):painter.drawLine(x, rect.top(), x, rect.bottom())
            ancestor = ancestor.parent();x -= step
    if has:
        if view.isExpanded(index):painter.drawLine(cx, mid + half + 2, cx, rect.bottom())  # down to the first child's elbow
        painter.setRenderHint(QPainter.Antialiasing, True)
        chevron = QPen(QColor(TEXT), 1.5);chevron.setCapStyle(Qt.RoundCap);chevron.setJoinStyle(Qt.RoundJoin);painter.setPen(chevron)
        if view.isExpanded(index):points = [QPointF(cx - half, mid - half / 2), QPointF(cx, mid + half / 2), QPointF(cx + half, mid - half / 2)]
        else:points = [QPointF(cx - half / 2, mid - half), QPointF(cx + half / 2, mid), QPointF(cx - half / 2, mid + half)]
        painter.drawPolyline(points)
    painter.restore()


class RowDelegate(QStyledItemDelegate):
    """Every row of a tree one height: the tree's row_height."""

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index);height = getattr(self.parent(), 'row_height', 0)
        return QSize(size.width(), height) if height else size


class BranchTree(QTreeWidget):
    """A left tree (Machine, the cabinet, Settings): one row height, one indentation and the same branch lines in all three."""

    def __init__(self, parent=None):
        super().__init__(parent);self.row_height = 0;self.setRootIsDecorated(True);self.setUniformRowHeights(True)
        self.setItemDelegate(RowDelegate(self));self.setStyleSheet(TREE_STYLE);self.setProperty('deskTree', True)

    def set_metrics(self, row, indent):
        if (self.row_height, self.indentation()) == (int(row), int(indent)):return
        self.row_height = int(row);self.setIndentation(int(indent));self.scheduleDelayedItemsLayout();self.viewport().update()

    def drawBranches(self, painter, rect, index):draw_branches(self, painter, rect, index)


# Activity's recent lines ------------------------------------------------------------------------------------------------------

class RecentLines(QListWidget):
    """The last few Timeline lines in Activity (what Graphite did, in words), copied from the Timeline as it refreshes;
    activating one opens it as the Timeline would. Its rows are the left trees' row height (the plan's symmetry rule 7: the
    right pane's lists use the trees' row metrics); place() sets it."""
    SHOWN = 5

    def __init__(self, host, tail):
        super().__init__();self.host = host;self.tail = tail;self.setObjectName('ActivityRecent');self.setAccessibleName('Recent activity')
        self.setFrameShape(QListWidget.NoFrame);self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFocusPolicy(Qt.NoFocus);self.texts = None;self.row_height = 0
        try:
            from .shell2 import TimelineDelegate
            self.setItemDelegate(type('RecentDelegate', (RowDelegate, TimelineDelegate), {})(self))  # the Timeline's look, the trees' row
        except ImportError:self.setItemDelegate(RowDelegate(self))
        self.itemActivated.connect(lambda item:tail.open_event(item))
        self.fit()

    def set_row(self, row):
        """The trees' row height for every line (pane_qt.place)."""
        if self.row_height != int(row):self.row_height = int(row);self.scheduleDelayedItemsLayout();self.viewport().update()
        self.fit()

    def fit(self):
        row = self.row_height or self.fontMetrics().height() + 8
        height = row * max(1, min(self.SHOWN, self.count())) + 2 * self.frameWidth()  # the lines exactly, none cut
        if self.minimumHeight() != height or self.maximumHeight() != height:self.setFixedHeight(height)

    def follow(self):
        rows = [self.tail.list.item(i) for i in range(max(0, self.tail.list.count() - self.SHOWN), self.tail.list.count())]
        texts = [item.text() for item in rows]
        if texts == self.texts:return
        self.texts = texts;self.clear()
        for item in rows:
            copy = QListWidgetItem(item.text());copy.setData(Qt.UserRole, item.data(Qt.UserRole));copy.setToolTip(item.toolTip());self.addItem(copy)
        self.fit()


# Install and place ----------------------------------------------------------------------------------------------------------

def _hide(*widgets):
    for widget in widgets:
        if widget is not None:widget.hide()


def _flat(layout):
    if layout is not None:layout.setContentsMargins(0, 0, 0, 0)


def install(host):
    """Build both panes from the parts the window already has (every object keeps its name for callers). Left: the three
    tabs, the active tree, Trash. Right: the three tabs, the active face, the empty foot. What the panes no longer show keeps
    working where it moved (docs/GRAPHITE_DESK.md, Homes)."""
    if hasattr(host, 'left_pane'):return host.left_pane, host.right_pane
    from PySide6.QtWidgets import QHBoxLayout
    from .settings_qt import ACTION_STYLE
    nav = host.settings_navigator;shell = host.shell2
    # The left pane --------------------------------------------------------------------------------------------------------
    old = host.nav_dock.widget()
    left_foot = PaneFoot('Left pane foot');trash = host.trash_can;trash.setParent(left_foot);left_foot.trash = trash;trash.show()
    left = PaneBody(nav.bar, nav.stack, left_foot, 'Left pane: Machine, Cabinet and Settings')
    host.nav_dock.setWidget(left);host.left_pane = left
    if old is not None:old.setParent(host.nav_dock);old.hide();host._left_pane_parts = old  # the machine strip and the old foot stay alive, out of sight
    _hide(nav.strip)
    mast = host.nav_dock.titleBarWidget()  # the explorer's mast (logo, tree search): kept, out of sight; the pane's top is the tab row
    if mast is not None:mast.hide();host._mast = mast;host.nav_dock.setTitleBarWidget(QWidget(host.nav_dock))
    nav.line = None  # the view line's picker is Arrange ▸ Cabinet now
    page = host.cabinet_page;page.footer_line = None
    _hide(page.logical, page.legacy, page.query, page.status, page.refresh_button, *page.transfer_buttons)
    _flat(page.layout());page.layout().setSpacing(0);_flat(page.stack.widget(0).layout());page.stack.widget(0).layout().setSpacing(0)
    _hide(nav.filter, nav.caption);_flat(nav.page.layout());nav.page.layout().setSpacing(0)
    nav.settings.setToolTip('Settings · ' + nav.caption.text().replace('\n', ' · '))  # the caption is out of the pane; the tab says it
    machine = host.machine_page;_hide(machine.details, machine.refresh_button, machine.caption);_flat(machine.layout());machine.layout().setSpacing(0)
    host.desk_trees = [machine.tree, page.tree, nav.tree]
    legacy = getattr(host, 'nav', None)
    if legacy is not None:legacy.twig_branches = False;legacy.desk_branches = True  # Existing views draw the same lines
    # The right pane -------------------------------------------------------------------------------------------------------
    pages = host.console_pages;holder = pages.parentWidget();layout = holder.layout()
    right_foot = PaneFoot('Right pane foot')
    pages.setDocumentMode(True)  # no frame around the faces: the pane's rule under the tabs is the only line
    right = PaneBody(shell.face_tabs, pages, right_foot, 'Right pane: Conversation, Activity and Context')
    layout.addWidget(right, 1);host.right_pane = right
    for face in (shell.face, host.operations_panel, host.arc_inspector):
        margins = face.layout().contentsMargins();face.layout().setContentsMargins(0, 0, 0, margins.bottom())
    panel = host.operations_panel;column = panel.col;_flat(column)
    # Activity: what Graphite took on and is doing (the Work block), what runs and waits (the Operations panel's work), and
    # what happened (the Timeline's last lines, the Work trail, the Return thread, Follow latest).
    face = shell.face;face.layout().removeWidget(face.work);column.insertWidget(0, face.work)
    tail = host.ledger_bridge.tail;tail.desk_foot = True
    head = tail.heading;head.setParent(None);head.setProperty('arcRole2', 'quiet');head.setWordWrap(True)
    recent = RecentLines(host, tail);panel.recent = recent
    original = tail.refresh
    def refresh(force=False, original=original, recent=recent):
        original(force);recent.follow()
    tail.refresh = refresh
    words = QHBoxLayout();words.setSpacing(12);trail = tail.trail;trail.setParent(None)
    trail.setProperty('settingsAction', True);trail.setProperty('paperFunctionalInk', True);trail.setStyleSheet(ACTION_STYLE);trail.setCursor(Qt.PointingHandCursor)
    # The foot's word said Work trail and opened the Organizer (ActivityTail.trail); in Activity it says where it goes. The
    # Work trail room is the work list's own Work trail word just above (desktop_header_qt.NicePopup.open_trail).
    trail.setText('Organizer');trail.setAccessibleName('Organizer');trail.setToolTip('Notes and notebooks: the Organizer room')
    footer = host.return_thread.footer;footer.setParent(None);follow = tail.follow;follow.setParent(None)  # parentless for a moment: never shown so
    for widget in (trail, footer):words.addWidget(widget)
    words.addStretch(1)
    at = column.count() - 1 if column.count() and column.itemAt(column.count() - 1).spacerItem() is not None else column.count()
    for offset, item in enumerate((head, recent)):column.insertWidget(at + offset, item)
    column.insertLayout(at + 2, words);column.insertWidget(at + 3, follow, 0, Qt.AlignLeft);follow.show();panel.timeline_words = words
    recent.follow()
    console = getattr(host, 'console', None)
    if console is not None:console.quiet_foot()
    # The workspace never asks the window for more height than it has (a page needing more scrolls or yields inside it), so
    # the window's layout is always satisfiable: the workspace's top and bottom are the panes' top and bottom, whatever page
    # is open and whether or not the centre foot shows (with the foot quiet in Line, a tall page used to move the top by a px).
    central = host.centralWidget()
    if central is not None:central.setMinimumHeight(CENTRE_MIN_HEIGHT)
    return left, right


def place(host, d):
    """Both panes for desk d: the shared tab metrics, the tab rows, the content boxes, the feet with Trash, the trees' rows."""
    left = getattr(host, 'left_pane', None);right = getattr(host, 'right_pane', None)
    if left is None or right is None or d is None:return None
    s = d.scale;I = d.inset;top = desk_qt.menu_px(s);floor = max(11, round(top * TAB_FLOOR));air = desk_qt.scaled(TAB_AIR, s)
    words = [b.text() for b in left.tabs.buttons + right.tabs.buttons];widest = widest_bold(words)
    least = widest(floor) + 2 * air  # a tab is never narrower than the widest word at the floor size (the gaps close first)
    h = desk_qt.word_height(QFontMetrics(tab_font(s)).height())  # the row's height from the menus' size: it never moves
    xs, T, g = tab_row(d.pane, I, desk_qt.scaled(TAB_GAP, s), 3, least)
    px = tab_px(T, top, floor, air, widest);font = tab_font(s, px=px);bold = QFontMetrics(tab_font(s, True, px))
    mark = tab_mark(T, max(round(T * .76), min(bold.horizontalAdvance(w) for w in words)))
    need = 3 * least + 2 * I
    trash = host.trash_can;trash.fit(s);gap = desk_qt.scaled(CONTENT_GAP, s);foot = foot_height(s, trash.height(), I)
    for pane, width in ((left, d.pane), (right, d.width - d.right - desk_qt.SEPARATOR)):
        positions, tab_width, _ = tab_row(width, I, desk_qt.scaled(TAB_GAP, s), 3, least)
        tab_underline = tab_mark(tab_width, max(round(tab_width * .76), mark[1]))
        key = (need, I, gap, foot, trash.width())
        pane.tabs.place(positions, I, tab_width, h, tab_underline, font, I, need);pane.inset = I;pane.gap = gap
        if pane.foot.height() != foot:pane.foot.setFixedHeight(foot)
        if getattr(pane, 'measured', None) != key:  # the pane's least width changed: its layout item must ask again (a
            pane.measured = key;pane.tabs.updateGeometry();pane.foot.updateGeometry();pane.updateGeometry()  # cached one kept a 28 pt need at 14 pt)
    left.foot.slot = QRect(d.pane - I - trash.width(), gap, trash.width(), trash.height())
    right.foot.slot = QRect(I, gap, trash.width(), trash.height())  # Trash's mirror: kept empty
    for pane in (left, right):pane.arrange()
    line = QFontMetrics(host.desk_trees[0].font()).height() if getattr(host, 'desk_trees', None) else 0
    row, indent = tree_metrics(line, s)
    for tree in getattr(host, 'desk_trees', []):tree.set_metrics(row, indent)
    legacy = getattr(host, 'nav', None)
    if legacy is not None and getattr(legacy, 'desk_branches', False) and legacy.indentation() != indent:legacy.desk_indent = indent;legacy.setIndentation(indent)
    recent = getattr(getattr(host, 'operations_panel', None), 'recent', None)
    if recent is not None:recent.set_row(row)
    host.panes = dict(T=T, gap=g, xs=xs, mark=mark, tab_height=h, tab_px=px, tab_px_top=top, least=least, need=need, foot=foot, row=row, indent=indent, content_gap=gap)
    return host.panes
