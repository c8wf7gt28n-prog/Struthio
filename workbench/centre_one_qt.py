"""One centre bar (Graphite 1.0 D1; the design direction's section 3: chrome that never stacks).

Above the centre there were three rows: L1's breadcrumb row (Back, Forward, the breadcrumb, and L4's Board on it), the bar
above a working view (centre_bar: ‹ Field, the name of what is open, Find, − +, Undo, Redo, Save, and L4's Save and Return,
Full program, Close, L5's Split), and, at board depth, the board's own head painted on the board (BOARD, the focus's title,
"7 recorded · 3 possible, not verified", Whole desk). They are one bar now, at every depth, left to right:

    ‹ ›  the breadcrumb (the focus's folders and its name)   [whether it is saved]
         at board depth:  ━ 7 recorded  ┄ 3 possible, not verified   Whole desk
         on the whole desk (the Field):  Board
         at work depth:   Board   Find   − +   Undo  Redo   Save   Save and Return   Full program   Split   Close

Nothing is lost: each control is the very one it was (the same object, its click, its tip, its dimming with a reason), moved
into the one row; ‹ Field is the board's Whole desk one press away (and the Field stays on its menus and keys); the name of
what is open is the breadcrumb's last part, and whether it is saved stays beside it. The board draws no head of its own
(board_qt asks one_bar), so its rings have the room. The line under the bar that says what happened to a file (L4) and the
line Find opens are not bars: they come only when there is something to say.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QIcon, QPainter
from PySide6.QtWidgets import QMenu, QPushButton, QSizePolicy, QToolButton, QWidget

from . import boss_theme as bt
from . import state_words as sw


def depth(host):
    """'work' (a working view in front), 'board', 'map' (the whole desk, the Field), or '' (Home, or the centre before it is set)."""
    bar = getattr(host, 'centre_bar', None)
    try:
        if bar is not None and bar.page() is not None:return 'work'
    except RuntimeError:
        return ''
    if getattr(host, '_field_active', False):
        page = getattr(host, 'field_page', None)
        return 'board' if getattr(page, 'mode', 'map') == 'board' else 'map'
    return ''


class Counts(QWidget):
    """The board's counts, as the board's head said them, each with its wire's shape: ━ recorded, ┄ possible, not verified."""

    def __init__(self, one):
        super().__init__();self.one = one;self.counts = (0, 0);self.setObjectName('CentreBoardCounts')
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

    def font_(self):
        f = QFont(bt.MONO);f.setPixelSize(max(12, round(12 * self.one.scale())));return f

    FORMS = (('recorded', 'possible, not verified'), ('recorded', 'possible'), ('', ''))      # whole, short, the numbers by their shapes

    def parts(self, form=0):
        recorded, possible = self.counts;a, b = self.FORMS[form]
        return (('recorded', ('%d %s' % (recorded, a)).strip()), ('possible', ('%d %s' % (possible, b)).strip()))

    def width_of(self, form):
        fm = QFontMetricsF(self.font_());line = 22 * self.one.scale()
        return round(sum(fm.horizontalAdvance(w) + line + 22 * self.one.scale() for _, w in self.parts(form)))

    def form(self):
        return next((f for f in range(len(self.FORMS)) if self.width_of(f) <= self.width() + 1), len(self.FORMS) - 1)

    def set_counts(self, recorded, possible):
        if (recorded, possible) != self.counts:
            self.counts = (recorded, possible);self.updateGeometry();self.update()
        said = ', '.join(words for _, words in self.parts())
        self.setToolTip('The links on this board: %s. A solid wire is recorded; a dashed one is only possible until you keep it.' % said)
        self.setAccessibleName('Board links: ' + said)

    def sizeHint(self):
        fm = QFontMetricsF(self.font_());return QSize(self.width_of(0), round(fm.height() + 8))

    def minimumSizeHint(self):
        fm = QFontMetricsF(self.font_());return QSize(self.width_of(len(self.FORMS) - 1), round(fm.height() + 8))

    def paintEvent(self, event):
        p = QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        try:
            f = self.font_();p.setFont(f);fm = QFontMetricsF(f);s = self.one.scale();x = 0.0;cy = self.height() / 2.0
            for key, words in self.parts(self.form()):      # whole words, or fewer of them: never a word cut short
                line = 22 * s;colour = bt.DAY_MARKS['WIRE_SOFT' if key == 'possible' else 'WIRE'] if bt.LAUNCH else (bt.TEAL_EDGE if bt.APPEARANCE == 'kasandra' else bt.LINE_STRONG)      # 1.0 P4: Day and Night
                sw.paint(p, QRectF(x, cy - 4, line, 8), key, colour, 1.6);x += line + 6 * s
                p.setPen(QColor(bt.QUIET));p.drawText(QRectF(x, 0, fm.horizontalAdvance(words) + 2, self.height()), Qt.AlignLeft | Qt.AlignVCenter, words)
                x += fm.horizontalAdvance(words) + 16 * s
        finally:
            p.end()


class OneBar(QObject):
    """The one bar: centre_bar's CentreBar, with the breadcrumb's parts and the board's head moved into it."""

    def __init__(self, host):
        super().__init__(host)
        self.host = host;self.bar = bar = host.centre_bar;self.nav = getattr(host, 'living_nav', None);self.watched = set()
        self.crumbs = getattr(self.nav, 'crumbs', None);self.row = bar.layout().itemAt(0).layout()
        depths = getattr(host, 'l4_depths', None) or getattr(host, 'depths', None)
        self.depth_board = getattr(depths, 'board', None) or self.find(QToolButton, 'DepthBoard')
        self.counts = Counts(self)
        self.whole = self.plate('Whole desk', 'CentreWholeDesk', self.to_whole, 'The whole desk: every record as tiles and wires; the board comes back on its selection')
        self.board = self.board_button()
        self.arrange()
        bar.setAccessibleName('The centre: where you are, and the controls for what is in front')
        original = bar.sync

        def sync(_original=original):
            _original();self.sync()
        bar.sync = sync
        fit = bar.fit_title

        def fit_title(_fit=fit):
            _fit();self.fit_title()
        bar.fit_title = fit_title
        if self.crumbs is not None:
            self.crumbs.words.installEventFilter(self)
        bar.installEventFilter(self)
        field_button = getattr(getattr(host, 'field_page', None), 'board_button', None)
        if field_button is not None:field_button.hide()
        self.sync()

    # ---- the parts -----------------------------------------------------------------------------------------------------------
    def find(self, kind, name):
        for w in self.host.findChildren(kind):
            if w.objectName() == name:return w
        return None

    def scale(self):
        return float((getattr(self.host, 'reading_profile', None) or {}).get('ui_pt', 14.0)) / 14.0

    def plate(self, words, name, does, tip):
        b = QPushButton(words);b.setObjectName(name);b.setCursor(Qt.PointingHandCursor);b.setFocusPolicy(Qt.TabFocus)
        b.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed);b.setToolTip(tip);b.setAccessibleName(words);b.clicked.connect(does)
        return b

    def board_button(self):
        """Board on the whole desk: the board on the Field's selection (it was a button on the Field's own corner)."""
        b = QToolButton();b.setObjectName('CentreToBoard');b.setText('Board');b.setAccessibleName('Board')
        b.setToolTip('The board: the selected sheet in the middle, what is linked to it around it')
        b.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);b.setCursor(Qt.PointingHandCursor);b.setFocusPolicy(Qt.TabFocus)
        b.clicked.connect(self.to_board)
        if self.depth_board is not None:
            b.setIcon(self.depth_board.icon());b.setIconSize(self.depth_board.iconSize());b.setStyleSheet(self.depth_board.styleSheet().replace('DepthBoard', 'CentreToBoard'))
        return b

    def space(self, width):
        """A gap in the row that is there only while the widget after it is shown (spaced() sets them)."""
        self.row.addSpacing(width);self.gaps.append([self.row.itemAt(self.row.count() - 1).spacerItem(), width, None])

    def spaced(self):
        """Each gap as wide as it is only before a widget that is shown: a hidden group leaves no gap."""
        row = self.row;gaps = {id(g[0]): g for g in self.gaps};pending = [];changed = False
        for i in range(row.count()):
            item = row.itemAt(i);spacer = item.spacerItem()
            if spacer is not None and id(spacer) in gaps:pending.append(gaps[id(spacer)]);continue
            w = item.widget()
            if w is None:continue
            for gap in pending:
                want = gap[1] if w.isVisibleTo(self.bar) else 0
                if gap[0].sizeHint().width() != want:gap[0].changeSize(want, 0, QSizePolicy.Fixed, QSizePolicy.Minimum);changed = True
            pending = []
        if changed:row.invalidate()

    def arrange(self):
        """The row, left to right: Back, Forward, the breadcrumb, whether it is saved; the board's counts and Whole desk; Board
        (the whole desk's, and the working view's); then the work's controls in the direction's order."""
        bar = self.bar;row = self.row;self.gaps = []
        while row.count():
            item = row.takeAt(0)
            if item.widget() is not None:item.widget().setParent(bar)
        crumbs = self.crumbs
        if crumbs is not None:
            crumbs.back.setParent(bar);crumbs.forward.setParent(bar);crumbs.words.setParent(bar)
            row.addWidget(crumbs.back);row.addWidget(crumbs.forward);row.addSpacing(6);row.addWidget(crumbs.words, 1)
            crumbs.words.setMinimumWidth(round(120 * self.scale()))      # the breadcrumb always has room to say where you are
            crumbs.hide();crumbs.setMaximumHeight(0)      # its parts live in the bar now; the row itself is not shown
        bar.field.hide()      # ‹ Field: the board's Whole desk is one press away; the Field keeps its menus and keys
        row.addWidget(bar.title, 0 if crumbs is not None else 1)
        if crumbs is not None:bar.title.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        self.space(8);row.addWidget(self.counts);self.space(10);row.addWidget(self.whole)
        row.addWidget(self.board)
        if self.depth_board is not None:
            self.depth_board.setParent(bar);self.space(4);row.addWidget(self.depth_board)
        depths = self.find_depths()
        split = getattr(getattr(self.host, 'l5_split', None), 'button', None)
        groups = ((bar.find,), (bar.smaller, bar.larger), (bar.undo, bar.redo), (bar.save,),
                  (getattr(depths, 'save_return', None),), (getattr(depths, 'full', None),), (split,), (getattr(depths, 'close_button', None),))
        self.work = []
        for group in groups:
            group = [b for b in group if b is not None]
            if not group:continue
            self.space(8)
            for b in group:row.addWidget(b);self.work.append(b)
        self.more = QToolButton(bar);self.more.setObjectName('CentreMore');self.more.setText('More ▾');self.more.setAccessibleName('More controls')
        self.more.setToolTip('The controls this narrow bar has no room for: each does what it does on the bar');self.more.setCursor(Qt.PointingHandCursor)
        self._standing = []      # 1.0 D2: the controls that may show their glyph alone (fold)
        self.more.setPopupMode(QToolButton.InstantPopup);self.more.setFocusPolicy(Qt.TabFocus);self.more.setMenu(QMenu(self.more))
        self.more.menu().aboutToShow.connect(self.fill_more);self.more.setStyleSheet(
            'QToolButton#CentreMore {font-family:"%s";color:%s;background:transparent;border:1px solid %s;padding:2px 8px;border-radius:2px;} '
            'QToolButton#CentreMore::menu-indicator {image:none;width:0px;}' % (bt.FACE, bt.TEXT, bt.LINE_STRONG))
        self.space(4);row.addWidget(self.more);self.more.hide();self.folded = []

    def find_depths(self):
        from . import depths_qt
        try:return depths_qt.depths_of(self.host)
        except Exception:  # noqa: BLE001
            return None

    # ---- what shows ----------------------------------------------------------------------------------------------------------
    def sync(self):
        """Every depth has the bar: the breadcrumb always; the board's counts and Whole desk at board depth; Board on the whole
        desk; the work's controls at work depth (each as the view in front can serve it, as before). What a narrow centre has no
        room for is behind More (fold): decided from the controls' sizes, then shown once, so the bar never flickers."""
        try:
            where = depth(self.host);bar = self.bar
            if not bar.isVisible() and not getattr(self.host, '_closing', False):bar.setVisible(True)
            board = self.board_view()
            focused = board is not None and board.board.focus is not None      # an empty board has no links to count
            shown = {self.counts: where == 'board' and focused, self.whole: where == 'board' and board is not None,
                     self.board: where == 'map' and board is not None, bar.title: where == 'work' and bool(bar.title.text())}
            if self.depth_board is not None:shown[self.depth_board] = where == 'work'
            if self.crumbs is not None:      # where you are is said whole where the bar has the room (the board's counts take fewer words first)
                from PySide6.QtGui import QFontMetrics
                least = round(120 * self.scale())
                whole = round(QFontMetrics(self.crumbs.words.font()).horizontalAdvance(self.crumbs.text()) * 1.1) + 8
                want = least if where == 'work' else max(least, min(whole, bar.width() // 2))
                if self.crumbs.words.minimumWidth() != want:self.crumbs.words.setMinimumWidth(want)
            self.folded = self.fold(shown) if where == 'work' else []
            for b in self.work:shown[b] = where == 'work' and b not in self.folded
            shown[self.more] = bool(self.folded)
            for w, on in shown.items():
                if w.isVisibleTo(bar) != on:w.setVisible(on)
            self.spaced()
            if board is not None:
                self.watch(board);self.watch(getattr(board.page, 'view', None))
                if where == 'board':
                    counts = board.board.counts();self.counts.set_counts(int(counts.get('recorded', 0)), int(counts.get('possible', 0)))
                field_button = getattr(board.page, 'board_button', None)
                if field_button is not None and field_button.isVisible():field_button.hide()
        except RuntimeError:      # the window is closing
            pass

    # ---- a narrow centre: what does not fit goes behind More, from the least used; nothing is lost ----------------------------
    FOLD_ORDER = (('CentreLarger', 'CentreSmaller'), ('CentreFullProgram',), ('CentreRedo', 'CentreUndo'), ('CentreSplit',), ('CentreSaveReturn',))      # 1.0 D2: − + go first; Save and Return and Split stay longest
    BARE_FIRST = ('CentreSaveReturn', 'CentreSplit', 'CentreFullProgram')      # 1.0 D2: before anything folds, these show their glyphs alone

    def need(self, on, alone=()):
        """The row's width with these widgets shown (on: widget -> shown), the breadcrumb at its least. 1.0 D2: `alone`, the
        controls counted at their glyph's width (tool_faces: a glyph alone)."""
        from . import tool_faces
        row = self.row;total = row.contentsMargins().left() + row.contentsMargins().right() + 4;pending = 0
        crumbs = self.crumbs;always = (crumbs.back, crumbs.forward, crumbs.words) if crumbs is not None else ()
        gaps = {id(g[0]): g[1] for g in self.gaps}
        for i in range(row.count()):
            item = row.itemAt(i);w = item.widget()
            if w is None:
                spacer = item.spacerItem()
                if spacer is not None:pending += gaps.get(id(spacer), spacer.sizeHint().width())
                continue
            if not (w in always or on.get(w, False)):
                pending = 0;continue
            wide = max(w.minimumWidth(), min(w.sizeHint().width(), w.maximumWidth()))      # 1.0 D2: the width the row gives it (a glyph's face is fixed)
            if w in self._standing:wide = tool_faces.face_width(w, w in alone)
            total += pending + row.spacing() + (w.minimumWidth() if crumbs is not None and w is crumbs.words else wide);pending = 0
        return total

    def fold(self, shown):
        """The work's controls to put behind More so that the row fits the bar, the least used first."""
        room = self.bar.width()
        on = dict(shown);on.update({b: True for b in self.work});on[self.more] = False
        alone = self._standing = self.can_stand_alone()
        bare = {b: False for b in alone}
        try:
            if room < 50 or self.need(on) <= room:return []
            bare = {b: True for b in alone}      # 1.0 D2: their glyphs alone first (the coordinator: Save and Return and Split stayed behind More)
            if self.need(on, alone) <= room:return []
        finally:
            self.bare_faces(bare)
        folded = [];on[self.more] = True;by_name = {b.objectName(): b for b in self.work}
        for names in self.FOLD_ORDER:      # a pair (Undo and Redo, − and +) goes together
            for name in names:
                b = by_name.get(name)
                if b is not None:on[b] = False;folded.append(b)
            if self.need(on, alone) <= room:break
        return folded

    def can_stand_alone(self):
        """1.0 D2: the controls that can show their glyph alone now (icons chosen, a glyph of their own)."""
        from . import tool_faces
        if tool_faces.mode() != 'icons':return []
        return [b for b in self.work if b.objectName() in self.BARE_FIRST and tool_faces.glyph_of(b) is not None]

    def bare_faces(self, which):
        """1.0 D2: Save and Return, Split and Full program as their glyphs alone, or with their words ({button: alone})."""
        from . import tool_faces
        for b, on in which.items():
            if bool(b.property('faceBare')) != bool(on):
                b.setProperty('faceBare', bool(on))
                try:tool_faces.fit(b)
                except RuntimeError:
                    pass

    def fill_more(self):
        menu = self.more.menu();menu.clear()
        for b in self.folded:
            words = b.text().strip() or b.accessibleName() or (b.toolTip().split('\n')[0][:40])
            if b.objectName() == 'CentreFullProgram':words = 'Full program'
            act = menu.addAction(words, b.click);act.setEnabled(b.isEnabled());act.setToolTip(b.toolTip())

    def sync_soon(self):
        QTimer.singleShot(0, self.sync)

    def board_view(self):
        page = getattr(self.host, 'field_page', None)
        return getattr(page, 'board', None) if page is not None else None

    def watch(self, widget):
        if widget is None or id(widget) in self.watched:return
        self.watched.add(id(widget));widget.installEventFilter(self)

    def eventFilter(self, watched, event):
        kind = event.type()
        if kind in (QEvent.Show, QEvent.Hide) and watched is not self.bar:self.sync_soon()      # the board or the whole desk came to the front
        elif kind == QEvent.Resize and watched is self.bar:self.sync_soon()      # a narrower or wider centre: what fits, again
        elif kind == QEvent.Resize and self.crumbs is not None and watched is self.crumbs.words:
            QTimer.singleShot(0, lambda: self.crumbs.show_parts(self.crumbs.parts, self.crumbs.note))
        return False

    def fit_title(self):
        """Beside the breadcrumb, the name of what is open only when the breadcrumb does not say it already; its saved state
        always ("not saved yet", "read only")."""
        bar = self.bar;crumbs = self.crumbs
        if crumbs is None:return
        said = str(getattr(bar, '_said', '') or '');name = str(getattr(bar, '_name', '') or '')
        last = crumbs.parts[-1][0] if crumbs.parts else ''
        state = said[len(name):].strip(' ·') if name and said.startswith(name) else ''
        shown = ('· ' + state) if (last and name and last.strip() == name.strip()) else said
        if not state and last and name and last.strip() == name.strip():shown = ''
        if bar.title.text() != shown:bar.title.setText(shown)
        bar.title.setVisible(depth(self.host) == 'work' and bool(shown))

    # ---- the presses -----------------------------------------------------------------------------------------------------------
    def to_whole(self):
        board = self.board_view()
        if board is not None:board.whole.emit()
        self.sync_soon()

    def to_board(self):
        board = self.board_view()
        if board is None:return
        from . import board_qt
        page = board.page;board_qt.to_board(page, page.view.field.selected, said=True);self.sync_soon()

    def board_changed(self):
        """board_qt: the board was built again (its counts may have changed)."""
        if depth(self.host) == 'board':self.sync_soon()

    def describe(self):
        """What the bar shows now, in words, left to right (for a reader of the window: frames, the smoke)."""
        out = []
        for i in range(self.row.count()):
            w = self.row.itemAt(i).widget()
            if w is None or not w.isVisible():continue
            if w is getattr(self.crumbs, 'words', None):out.append('breadcrumb: ' + self.crumbs.text())
            elif w is self.counts:out.append('counts: ' + ', '.join(words for _, words in self.counts.parts(self.counts.form())))
            elif isinstance(w, (QPushButton, QToolButton)):out.append(w.text() or w.accessibleName() or w.toolTip().split('\n')[0][:30])
            elif hasattr(w, 'text'):out.append(w.text())
        return out


def install(host):
    """shell2's start, after the breadcrumb (L1), the depths (L4) and the split (L5): host.one_bar. When it cannot be made, the
    rows stay as they were."""
    if getattr(host, 'one_bar', None) is not None:return host.one_bar
    if getattr(host, 'centre_bar', None) is None:return None
    try:
        host.one_bar = OneBar(host)
    except Exception:  # noqa: BLE001 - the window starts with its rows as they were rather than not at all
        import traceback
        traceback.print_exc();host.one_bar = None
    return host.one_bar
