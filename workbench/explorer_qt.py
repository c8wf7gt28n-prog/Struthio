"""The Explorer in the window (Graphite 1.1 E1): the Files tree and the centre as an Explorer, the board as its third view.

PLAN_1.1.md, E1; proposal_familiar.md section 4. explorer.py holds the words and rules; here is the window:

    the navigation pane   the Files tree in the Explorer's order (explorer.arrange): Quick access first, then the Desk, then
                          This computer (System (C:) one press down, the drives with letters and free space); the bin is the
                          can at the pane's foot, named "Recycle Bin" on a new profile and DELETE on one that used 1.0.
                          A folder chosen in the tree opens in the centre in the view it was left in (List the first time,
                          Icons for a folder mostly of pictures); a file chosen there opens its folder with it chosen. The
                          Desk's records open on the board, as in 1.0.
    the centre            ExplorerPage, a page of the centre's stack like the Field: List (Name, Modified, Type, Size, Links;
                          a press on a column sorts by it, again turns it round; Ctrl and Shift choose many), Icons (a
                          thumbnail for each picture, read with Qt's QImageReader at a small size on the floor's worker and
                          kept in ~/.cache/graphite/thumbs: the window never waits for one), and a line at the foot (how
                          many, how many chosen, the drive's free space).
    the centre bar        the one bar (centre_one_qt) gains the address field (in place of the breadcrumb while the Explorer
                          is in front; a typed path opens, ~ and DOS's C:\\ too) and List · Icons · Board, also shown on the
                          board, so List brings the board's thing back in its folder. Board puts the chosen thing (or the
                          folder) in the middle of 1.0's board, unchanged. Back and Forward walk the folders too.
    keys and right-click  W1's: Ctrl+C, Ctrl+X, Ctrl+V (W1's file clipboard, shared with the tree), F2, Delete, Shift+Delete,
                          Enter, Alt+Enter (W1's Properties), F5, Backspace (Back), Ctrl+A, Ctrl+Z; and Alt+Up (the folder
                          above), Ctrl+L (the address), Ctrl+B (Board). Each change is the owner's own press through the
                          Kernel (home_files_qt, bulk_files_qt: one line, one Undo; many files, one batch with one Undo).

Nothing here changes a file by itself; reading a folder goes through the Kernel (ledger.browse), as the Finder's does.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QFileSystemWatcher, QItemSelectionModel, QObject, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QImage, QImageReader, QKeySequence, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QListView, QListWidget, QListWidgetItem, QMenu, QSizePolicy, QStackedWidget, QToolButton,
                               QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import boss_theme as bt
from . import explorer as ex

ENTRY = Qt.UserRole + 41
LIMIT = 2000                 # rows read from a folder (ledger.browse's most)
THUMB_PX = 96                # a thumbnail's longest side at 14 pt
THUMBS_AT_ONCE = 6           # pictures read in one job on the floor's worker
PATH = 'path:'               # computer_tree_qt.PATH


def kernel_of(host):
    return getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)


def bin_word(host):
    return ex.bin_word(getattr(getattr(host, 'session', None), 'state', None))


def say(host, words, ms=7000):
    try:host.statusBar().showMessage(ex.in_words(words, bin_word(host)), ms)
    except (AttributeError, RuntimeError):
        pass


def scale_of(host):
    return float((getattr(host, 'reading_profile', None) or {}).get('ui_pt', 14.0)) / 14.0


def tilde(path):
    from . import home_reach as hr
    return hr.tilde(path)


# ---- thumbnails, on the floor's worker --------------------------------------------------------------------------------------
def thumbnail(path, px, cache=None):
    """A picture's thumbnail as a QImage (never a QPixmap: this runs off the window's thread), read from the cache when it
    is there, else read small with QImageReader and kept. None when the file is not a picture Qt can read."""
    try:st = os.stat(path)
    except OSError:
        return None
    cache = Path(cache or ex.thumbs_dir());kept = cache / ex.thumb_name(path, st.st_size, st.st_mtime_ns, px)
    if kept.is_file():
        image = QImage(str(kept))
        if not image.isNull():return image
    reader = QImageReader(str(path));reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid() and (size.width() > px or size.height() > px):reader.setScaledSize(size.scaled(px, px, Qt.KeepAspectRatio))
    image = reader.read()
    if image.isNull():return None
    try:
        cache.mkdir(parents=True, exist_ok=True)
        temp = kept.with_suffix('.writing.png')
        if image.save(str(temp), 'PNG'):os.replace(temp, kept)
    except OSError:
        pass
    return image


# ---- the page in the centre -----------------------------------------------------------------------------------------------------
class ExplorerPage(QWidget):
    """The folder in front, in List or Icons, with a line at its foot."""

    def __init__(self, explorer):
        super().__init__()
        self.explorer = explorer;self.host = explorer.host
        self.setObjectName('GraphiteExplorer');self.setAccessibleName('Explorer: the folder in front')
        box = QVBoxLayout(self);box.setContentsMargins(0, 0, 0, 0);box.setSpacing(0)
        self.stack = QStackedWidget(self);box.addWidget(self.stack, 1)
        self.list = QTreeWidget(self);self.list.setObjectName('ExplorerList');self.list.setAccessibleName('The folder as a list')
        self.list.setColumnCount(len(ex.COLUMNS));self.list.setHeaderLabels(list(ex.COLUMNS));self.list.setRootIsDecorated(False)
        self.list.setUniformRowHeights(True);self.list.setSelectionMode(QAbstractItemView.ExtendedSelection);self.list.setAllColumnsShowFocus(True)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu);self.list.setSortingEnabled(False)
        head = self.list.header();head.setSectionsClickable(True);head.setSortIndicatorShown(True);head.setStretchLastSection(False)
        head.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, len(ex.COLUMNS)):head.setSectionResizeMode(column, QHeaderView.ResizeToContents)      # the name has the rest
        self.list.setTextElideMode(Qt.ElideMiddle)      # a long name keeps its end: its kind's letters
        head.sectionClicked.connect(explorer.sort_by)
        self.icons = QListWidget(self);self.icons.setObjectName('ExplorerIcons');self.icons.setAccessibleName('The folder as icons')
        self.icons.setViewMode(QListView.IconMode);self.icons.setResizeMode(QListView.Adjust);self.icons.setMovement(QListView.Static)
        self.icons.setWrapping(True);self.icons.setWordWrap(True);self.icons.setUniformItemSizes(True)
        self.icons.setSelectionMode(QAbstractItemView.ExtendedSelection);self.icons.setContextMenuPolicy(Qt.CustomContextMenu)
        self.empty = QLabel(self);self.empty.setObjectName('ExplorerEmpty');self.empty.setAlignment(Qt.AlignCenter);self.empty.setWordWrap(True)
        for w in (self.list, self.icons, self.empty):self.stack.addWidget(w)
        self.foot = QLabel(self);self.foot.setObjectName('ExplorerFoot');self.foot.setAccessibleName('What is in the folder')
        box.addWidget(self.foot)
        for view in (self.list, self.icons):
            view.customContextMenuRequested.connect(lambda point, v=view: explorer.menu_at(v, point))
            view.itemSelectionChanged.connect(explorer.chosen_changed)
        self.list.itemActivated.connect(lambda item, column=0: explorer.activate(item.data(0, ENTRY)))
        self.icons.itemActivated.connect(lambda item: explorer.activate(item.data(ENTRY)))
        self.restyle()

    def restyle(self):
        s = scale_of(self.host);px = max(12, round(14 * s));thumb = round(THUMB_PX * s)
        self.icons.setIconSize(QSize(thumb, thumb));self.icons.setGridSize(QSize(thumb + round(40 * s), thumb + round(48 * s)))
        self.list.setIconSize(QSize(round(18 * s), round(18 * s)))
        self.list.header().setMinimumSectionSize(round(48 * s))
        self.setStyleSheet(
            'QWidget#GraphiteExplorer {background:%(card)s;} '
            'QTreeWidget#ExplorerList, QListWidget#ExplorerIcons {font-family:"%(face)s";font-size:%(px)dpx;color:%(text)s;background:%(card)s;border:none;} '
            'QListWidget#ExplorerIcons {padding:10px 4px 0 10px;} '
            'QLabel#ExplorerEmpty {font-family:"%(face)s";font-size:%(px)dpx;color:%(quiet)s;background:%(card)s;} '
            'QLabel#ExplorerFoot {font-family:"%(face)s";font-size:%(small)dpx;color:%(quiet)s;background:%(card)s;border-top:1px solid %(line)s;padding:3px 10px;}'
            % dict(card=bt.CARD, face=bt.FACE, px=px, small=max(11, round(12.5 * s)), text=bt.TEXT, quiet=bt.QUIET, line=bt.LINE))

    def view_widget(self):
        return self.icons if self.stack.currentWidget() is self.icons else self.list


# ---- the bar's parts: the address and List · Icons · Board ---------------------------------------------------------------------
class Switch(QWidget):
    """List · Icons · Board: three presses, one of them down (its word underlined as well as coloured)."""

    def __init__(self, explorer):
        super().__init__()
        self.setObjectName('ExplorerViews');self.setAccessibleName('How the folder is shown: List, Icons or Board')
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        row = QHBoxLayout(self);row.setContentsMargins(0, 0, 0, 0);row.setSpacing(0)
        self.group = QButtonGroup(self);self.group.setExclusive(True);self.buttons = {}
        tips = {'list': 'List: name, modified, type, size and links; a press on a column sorts by it',
                'icons': 'Icons: a thumbnail for each picture', 'board': 'Board: the chosen thing in the middle, what is linked to it around it (Ctrl+B)'}
        for view in ex.VIEWS:
            b = QToolButton(self);b.setObjectName('ExplorerView' + ex.VIEW_WORDS[view]);b.setText(ex.VIEW_WORDS[view]);b.setCheckable(True)
            b.setAccessibleName(ex.VIEW_WORDS[view]);b.setToolTip(tips[view]);b.setCursor(Qt.PointingHandCursor);b.setFocusPolicy(Qt.TabFocus)
            b.clicked.connect(lambda checked=False, v=view: explorer.set_view(v))
            self.group.addButton(b);self.buttons[view] = b;row.addWidget(b)
        self.restyle()

    def restyle(self, scale=1.0):
        px = max(12, round(14 * scale))
        self.setStyleSheet(
            'QToolButton {font-family:"%(face)s";font-size:%(px)dpx;color:%(quiet)s;background:transparent;border:1px solid %(line)s;padding:2px 8px;} '
            'QToolButton:checked {color:%(text)s;background:%(raised)s;border:1px solid %(strong)s;text-decoration:underline;font-weight:600;}'
            % dict(face=bt.FACE, px=px, quiet=bt.QUIET, line=bt.LINE, text=bt.TEXT, raised=bt.RAISED, strong=bt.LINE_STRONG))

    def show_view(self, view):
        b = self.buttons.get(view)
        if b is not None and not b.isChecked():b.setChecked(True)


class Address(QLineEdit):
    def __init__(self, explorer):
        super().__init__()
        self.explorer = explorer;self.setObjectName('ExplorerAddress');self.setAccessibleName('Address: the folder in front; type a path and press Enter')
        self.setPlaceholderText('a folder or a file: ~/Documents, /etc, C:\\');self.setClearButtonEnabled(False)
        self.setToolTip('Type a path and press Enter: ~ is Home, / the top of the computer, C:\\ and D:\\ its drives')
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed);self.returnPressed.connect(lambda: explorer.go_typed(self.text()))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.explorer.sync_bar(force=True);self.explorer.page.view_widget().setFocus();event.accept();return
        super().keyPressEvent(event)

    def restyle(self, scale=1.0):
        self.setMinimumWidth(round(160 * scale))
        self.setStyleSheet('QLineEdit#ExplorerAddress {font-family:"%s";font-size:%dpx;color:%s;background:%s;border:1px solid %s;padding:2px 6px;}'
                           % (bt.FACE, max(12, round(14 * scale)), bt.TEXT, bt.CARD, bt.LINE_STRONG))


# ---- the keys over the views ------------------------------------------------------------------------------------------------------
KEYS = {
    (Qt.Key_C, Qt.ControlModifier): 'copy', (Qt.Key_X, Qt.ControlModifier): 'cut', (Qt.Key_V, Qt.ControlModifier): 'paste',
    (Qt.Key_F2, Qt.NoModifier): 'rename', (Qt.Key_Delete, Qt.NoModifier): 'delete', (Qt.Key_Delete, Qt.ShiftModifier): 'for_good',
    (Qt.Key_Return, Qt.NoModifier): 'open', (Qt.Key_Enter, Qt.KeypadModifier): 'open', (Qt.Key_Return, Qt.AltModifier): 'properties',
    (Qt.Key_Enter, Qt.AltModifier | Qt.KeypadModifier): 'properties', (Qt.Key_F5, Qt.NoModifier): 'read_again',
    (Qt.Key_Backspace, Qt.NoModifier): 'back', (Qt.Key_A, Qt.ControlModifier): 'all', (Qt.Key_Z, Qt.ControlModifier): 'undo',
    (Qt.Key_Up, Qt.AltModifier): 'up', (Qt.Key_L, Qt.ControlModifier): 'address', (Qt.Key_D, Qt.AltModifier): 'address',
    (Qt.Key_B, Qt.ControlModifier): 'board',
    (Qt.Key_Period, Qt.ControlModifier): 'command',  # 1.1 B4: Command… (the exact line it is or runs)
}


class Keys(QObject):
    def __init__(self, explorer, views):
        super().__init__(explorer.page)
        self.explorer = explorer
        for v in views:v.installEventFilter(self)

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind not in (QEvent.ShortcutOverride, QEvent.KeyPress):return False
        try:what = KEYS.get((event.key(), event.modifiers()))
        except RuntimeError:
            return False
        if what is None:return False
        if kind == QEvent.ShortcutOverride:event.accept();return True
        try:self.explorer.do(what)
        except ValueError as exc:
            say(self.explorer.host, 'Not done: %s' % str(exc).split(': ', 1)[-1])
        return True


# ---- the Explorer -------------------------------------------------------------------------------------------------------------
class Explorer(QObject):
    def __init__(self, host):
        super().__init__(host)
        self.host = host;self.living = host.living_nav;self.folder = '';self.listing = {};self.entries = [];self.view = 'list'
        self.sort = (0, False);self.generation = 0;self.waiting = [];self.thumbs = {};self.left_count = 0;self.chosen_after = []
        self.page = ExplorerPage(self);host.central_stack.addWidget(self.page)
        self.keys = Keys(self, (self.page.list, self.page.icons))
        self.watcher = QFileSystemWatcher(self);self.watcher.directoryChanged.connect(lambda *_: self.again.start())
        self.again = QTimer(self);self.again.setSingleShot(True);self.again.setInterval(250);self.again.timeout.connect(self.reload)
        self.address = Address(self);self.switch = Switch(self);self.place_on_bar()
        self.hook()

    # ---- where it stands ------------------------------------------------------------------------------------------------------
    def in_front(self):
        try:return self.host.central_stack.currentWidget() is self.page
        except RuntimeError:
            return False

    def computer(self):
        return getattr(self.living, 'computer', None)

    def home(self):
        computer = self.computer()
        return str(computer.home) if computer is not None else str(Path.home())

    def place_on_bar(self):
        one = getattr(self.host, 'one_bar', None)
        crumbs = getattr(one, 'crumbs', None)
        if one is None or crumbs is None:
            self.address.hide();self.switch.hide();return
        row = one.row;at = row.indexOf(crumbs.words)
        self.address.setParent(one.bar);self.switch.setParent(one.bar)
        row.insertWidget(at + 1, self.address, 1);row.insertSpacing(at + 2, 8);row.insertWidget(at + 3, self.switch, 0)
        self.address.hide();self.switch.hide();self.restyle()

    def restyle(self):
        s = scale_of(self.host);self.address.restyle(s);self.switch.restyle(s);self.page.restyle()

    # ---- hooks into the tree, the history, the bar and the window --------------------------------------------------------------
    def hook(self):
        host = self.host;living = self.living;explorer = self
        tree_model = living.tree_model

        def arranged(model, _original=tree_model):
            return explorer.arranged(_original(model))
        living.tree_model = arranged
        computer = self.computer()
        if computer is not None:
            go = computer.go

            def computer_go(node_id, via='tree', _go=go):
                done = explorer.tree_go(node_id, via)
                return True if done else _go(node_id, via)
            computer.go = computer_go
            QTimer.singleShot(0, lambda: explorer.wait_land(80))
        restore = living.restore

        def restored(entry, _restore=restore):
            if getattr(entry, 'depth', '') == 'explorer':return explorer.restore(entry)
            return _restore(entry)
        living.restore = restored
        one = getattr(host, 'one_bar', None)
        if one is not None:
            sync = one.sync

            def one_sync(_sync=sync):
                _sync();explorer.sync_bar()
            one.sync = one_sync
        close_start = host._close_start

        def close(_close=close_start):
            _close();explorer.leave()
        host._close_start = close
        self.left_count = host.tabs.count()
        host.tabs.currentChanged.connect(self.tab_changed)
        host.central_stack.currentChanged.connect(lambda *_: self.sync_bar())
        note = getattr(getattr(host, 'home_files', None), 'note', None)
        if note is not None and hasattr(note, 'tell'):
            tell = note.tell

            def told(words, *args, _tell=tell, **kwargs):
                return _tell(ex.in_words(words, bin_word(host)), *args, **kwargs)
            note.tell = told
        switch = getattr(computer, 'switch', None)
        if switch is not None:switch.toggled.connect(lambda *_: self.reload() if self.in_front() else None)

    def arranged(self, model):
        """The tree's rows in the Explorer's order (explorer.arrange), and living_nav's indexes made again for them."""
        computer = self.computer()
        if computer is None or not isinstance(model, dict):return model
        try:
            from .cabinet import digest
            rows, paths = ex.arrange(model.get('nodes') or [], computer.home_id, ex.quick_places(computer.home), computer.canonical, ex.letters())
        except Exception as exc:  # noqa: BLE001 - the tree stands as 1.0 drew it
            say(self.host, 'The Explorer could not arrange the tree: %s' % str(exc)[:160]);return model
        computer.paths.update(paths)
        model = dict(model, nodes=rows)
        model['signature'] = digest([model.get('signature'), [(n['id'], n['label'], n['parent']) for n in rows if n['id'] in paths or n['id'] == ex.COMPUTER]])
        living = self.living;living.nodes = {n['id']: n for n in rows};living.by_canonical = {}
        for n in rows:
            known = living.by_canonical.get(n['canonical_id'])
            if known is None or (n['provider'] == 'living_nav' and living.nodes[known]['provider'] != 'living_nav') or (n.get('owning') and not living.nodes[known].get('owning')):
                living.by_canonical[n['canonical_id']] = n['id']
        return model

    def tree_go(self, node_id, via):
        """A folder of the tree opens in the centre in its view; a file opens its folder with it chosen. A folder or file left
        on Board goes to the board as in 1.0 (False: the tree's own way)."""
        from .home_files_qt import path_of_row
        node = self.living.nodes.get(node_id) or {}
        role = node.get('role');path = path_of_row(node_id)
        if role not in ('file', 'folder') or not path:return False
        folder = path if role == 'folder' else str(Path(path).parent)
        if not os.path.isdir(folder):return False
        if ex.view_for(folder) == 'board':return False
        return self.show(folder, via=via, chosen=[path] if role == 'file' else ())

    def wait_land(self, tries):
        computer = self.computer()
        if computer is None or getattr(self.host, '_closing', False):return
        if getattr(computer, 'landed', False):return self.landed()
        if tries > 0:QTimer.singleShot(50, lambda: self.wait_land(tries - 1))
        return None

    def landed(self):
        """The start: Quick access open, Home chosen on it (its folders closed, so the six places read at once), and Home in the
        centre when nothing else is there: never a blank centre."""
        computer = self.computer();page = getattr(self.host, 'cabinet_page', None)
        if computer is None or page is None:return
        item = page.items.get(computer.home_id)
        if item is not None and item.isExpanded():item.setExpanded(False)
        QTimer.singleShot(0, self.first_folder)

    def first_folder(self):
        host = self.host
        if getattr(host, '_closing', False) or getattr(host, '_initializing', False):return
        if host.tabs.count() or getattr(host, '_field_active', False) or getattr(host, '_home_active', False):return
        if host.central_stack.currentWidget() is not getattr(host, 'workspace_split', None):return
        self.show(self.home(), via='start')

    def tab_changed(self, index):
        """A tab that comes forward (one opened, or chosen) is what the owner asked to see; a tab closing leaves the folder."""
        count = self.host.tabs.count();closed = count < self.left_count;self.left_count = count
        if index >= 0 and not closed:self.leave()

    def leave(self):
        host = self.host
        if getattr(host, '_initializing', False) or not self.in_front():return
        host.central_stack.setCurrentWidget(host.workspace_split)

    def bring(self):
        host = self.host
        if getattr(host, '_field_active', False):
            from . import field_page
            field_page.leave_field(host)
        if getattr(host, '_home_active', False):host._close_start()
        if not self.in_front():host.central_stack.setCurrentWidget(self.page)
        host.setWindowTitle('%s — Kas' % (Path(self.folder).name or self.folder))

    # ---- reading and showing a folder ----------------------------------------------------------------------------------------
    def read(self, path):
        kernel = kernel_of(self.host)
        if kernel is None:return None, 'Kas\'s Kernel is not open yet'
        from .engineering_kernel import operator
        computer = self.computer();hidden = bool(getattr(computer, 'hidden', False))
        try:answer = kernel.dispatch('ledger.browse', {'path': str(path), 'all': hidden, 'limit': LIMIT}, operator())
        except Exception as exc:  # noqa: BLE001 - words, never a traceback
            return None, str(exc)[:200]
        if not answer.get('ok'):return None, str((answer.get('error') or {}).get('message') or 'not read')
        return answer['result'], ''

    def show(self, path, via='tree', chosen=(), view=None, record=True):
        """The folder in the centre, in its view (or `view`), the `chosen` paths chosen. False when it cannot be read."""
        path = os.path.normpath(str(path))
        listing, why = self.read(path)
        if listing is None:
            say(self.host, '%s cannot be shown: %s' % (tilde(path), why));return False
        view = view or ex.view_for(path, listing.get('entries') or ())
        if view == 'board':
            self.folder = path;self.listing = listing
            return self.to_board(list(chosen)[0] if chosen else path, via)
        self.folder = path;self.listing = listing;self.view = view;self.chosen_after = [os.path.normpath(str(c)) for c in chosen]
        self.entries = self.with_links([dict(e, path=os.path.join(path, e['name'])) for e in listing.get('entries') or ()])
        watched = self.watcher.directories()
        if watched:self.watcher.removePaths(watched)
        if os.path.isdir(path):self.watcher.addPath(path)
        self.bring();self.fill()
        if record:self.record(path, via)
        self.sync_bar(force=True)
        return True

    def reload(self):
        if not self.folder:return
        keep = self.chosen_paths()
        if not os.path.isdir(self.folder):
            parent = str(Path(self.folder).parent)
            say(self.host, '%s is not there any more; its folder is shown.' % tilde(self.folder))
            return self.show(parent, via='tree', record=False)
        listing, why = self.read(self.folder)
        if listing is None:return say(self.host, '%s cannot be read again: %s' % (tilde(self.folder), why))
        self.listing = listing;self.chosen_after = keep
        self.entries = self.with_links([dict(e, path=os.path.join(self.folder, e['name'])) for e in listing.get('entries') or ()])
        self.fill()
        return True

    def with_links(self, entries):
        """Each row's recorded links on the board's reading of the desk (a count only where there are some)."""
        board = getattr(getattr(self.host, 'field_page', None), 'board', None)
        desk = getattr(board, 'desk', None);known = getattr(self.living, 'files_by_abs', None) or {}
        if desk is None:return entries
        for e in entries:
            ident = known.get(e['path'])
            if ident:
                try:e['links'] = len(desk.recorded(ident))
                except Exception:  # noqa: BLE001 - no count rather than a wrong one
                    pass
        return entries

    def record(self, path, via):
        """A place in the window's history (Back and Forward), and the tree kept to it where it already shows its row."""
        living = self.living;computer = self.computer()
        ident = PATH + path;node = ''
        if computer is not None:
            from .home_files_qt import branch_id
            for candidate in (ex.FS + 'quick:' + path, branch_id(path), ex.SYSTEM_ID if path == '/' else ''):
                if candidate and candidate in living.nodes:node = candidate;break
        try:living.go(ident, 'tree', 'explorer', title=Path(path).name or path, node=node)      # the tree is kept below, without reading it again
        except ValueError:      # a history that does not know the Explorer's depth
            return
        page = getattr(self.host, 'cabinet_page', None)
        if via not in ('tree',) and page is not None and node in getattr(page, 'items', {}):
            living.with_applying(lambda: page.select(node, reveal=True))

    def restore(self, entry):
        focus = str(getattr(entry, 'focus', '') or '')
        path = focus[len(PATH):] if focus.startswith(PATH) else ''
        if path and os.path.isdir(path):self.show(path, via='breadcrumb', view=None, record=False)

    def type_words(self, entry):
        from .finder_qt import kind_word
        return kind_word(entry)

    def fill(self):
        page = self.page;column, descending = self.sort
        rows = ex.ordered(self.entries, column, descending, self.type_words)
        self.generation += 1;self.waiting = []
        from .finder_qt import glyph, glyph_kind, when
        s = scale_of(self.host);small = round(18 * s);thumb = round(THUMB_PX * s)
        head = page.list.header();head.setSortIndicator(column, Qt.DescendingOrder if descending else Qt.AscendingOrder)
        for view in (page.list, page.icons):view.blockSignals(True)
        page.list.clear();page.icons.clear();chosen = set(self.chosen_after);first = None
        for e in rows:
            folder = e.get('kind') == 'folder'
            links = int(e.get('links') or 0)
            item = QTreeWidgetItem([e['name'], when(e['modified']) if e.get('modified') else '', self.type_words(e),
                                    '' if folder else (ex.bytes_words(e['bytes']) if e.get('bytes') is not None else '—'),
                                    ('%d ─' % links) if links else ''])
            item.setData(0, ENTRY, e);item.setIcon(0, QIcon(glyph(glyph_kind(e), small)));item.setToolTip(0, tilde(e['path']))
            if links:item.setToolTip(4, '%d recorded link%s: Board shows %s' % (links, '' if links == 1 else 's', 'them' if links > 1 else 'it'))
            for c in (1, 3, 4):item.setTextAlignment(c, Qt.AlignRight | Qt.AlignVCenter)
            for c in (1, 2, 3, 4):item.setForeground(c, QColor(bt.QUIET))
            if not e.get('readable', True):item.setForeground(0, QColor(bt.QUIET));item.setToolTip(0, item.toolTip(0) + ' · cannot be read')
            page.list.addTopLevelItem(item)
            icon = QListWidgetItem(e['name']);icon.setData(ENTRY, e);icon.setToolTip('%s · %s' % (e['name'], self.type_words(e)))
            if not folder and ex.is_picture(e['name']):
                kept = self.thumbs.get(e['path'])
                icon.setIcon(QIcon(kept) if kept is not None else QIcon(glyph('image', thumb)))
                if kept is None:self.waiting.append(e['path'])
            else:icon.setIcon(QIcon(glyph(glyph_kind(e), thumb)))
            page.icons.addItem(icon)
            if e['path'] in chosen:
                item.setSelected(True);icon.setSelected(True)
                if first is None:first = (item, icon)
        if first is not None:
            page.list.setCurrentItem(first[0], 0, QItemSelectionModel.NoUpdate);page.icons.setCurrentItem(first[1], QItemSelectionModel.NoUpdate)
            page.list.scrollToItem(first[0]);page.icons.scrollToItem(first[1])
        for view in (page.list, page.icons):view.blockSignals(False)
        if not rows:
            page.empty.setText('This folder is empty.' if not self.listing.get('count') else 'Nothing here is shown.')
            page.stack.setCurrentWidget(page.empty)
        else:page.stack.setCurrentWidget(page.icons if self.view == 'icons' else page.list)
        self.chosen_after = []
        self.say_foot()
        if self.view == 'icons' and self.waiting:self.next_thumbs(self.generation)

    def next_thumbs(self, generation):
        if generation != self.generation or not self.waiting:return
        batch, self.waiting = self.waiting[:THUMBS_AT_ONCE], self.waiting[THUMBS_AT_ONCE:]
        px = round(THUMB_PX * scale_of(self.host));cache = ex.thumbs_dir()
        from . import floor

        def work(batch=tuple(batch), px=px, cache=cache):
            return [(p, thumbnail(p, px, cache)) for p in batch]

        def done(result, error, generation=generation):
            if generation != self.generation:return
            for path, image in result or ():
                if image is None:continue
                pixmap = QPixmap.fromImage(image);self.thumbs[path] = pixmap
                for i in range(self.page.icons.count()):
                    item = self.page.icons.item(i)
                    if (item.data(ENTRY) or {}).get('path') == path:item.setIcon(QIcon(pixmap));break
            if len(self.thumbs) > 3000:self.thumbs.clear()
            self.next_thumbs(generation)
        floor.submit(work, done, key=('explorer-thumbs', id(self)))

    def say_foot(self):
        listing = self.listing or {};count = int(listing.get('count') or len(self.entries));chosen = len(self.chosen_paths())
        words = ['%d thing%s' % (count, '' if count == 1 else 's')]
        if listing.get('truncated') and count > len(self.entries):words.append('the first %d listed' % len(self.entries))
        if chosen:words.append('%d chosen' % chosen)
        if listing.get('free_bytes') is not None and listing.get('total_bytes'):
            letter = ex.letter_of(self.folder, ex.letters())
            words.append('%s free of %s on %s' % (ex.bytes_words(listing['free_bytes']), ex.bytes_words(listing['total_bytes']),
                                                    'System (C:)' if letter == 'C' else 'the drive %s:' % letter))
        self.page.foot.setText(' · '.join(words))

    # ---- choosing and doing ---------------------------------------------------------------------------------------------------
    def chosen_paths(self):
        view = self.page.view_widget()
        try:items = view.selectedItems()
        except RuntimeError:
            return []
        get = (lambda i: i.data(0, ENTRY)) if view is self.page.list else (lambda i: i.data(ENTRY))
        rows = [get(i) or {} for i in items]
        order = {e['path']: n for n, e in enumerate(ex.ordered(self.entries, *self.sort, self.type_words))}
        return [r['path'] for r in sorted(rows, key=lambda r: order.get(r.get('path'), 0)) if r.get('path')]

    def current_path(self):
        view = self.page.view_widget();item = view.currentItem()
        if item is None:return ''
        e = item.data(0, ENTRY) if view is self.page.list else item.data(ENTRY)
        return (e or {}).get('path', '') if item.isSelected() else ''

    def chosen_changed(self):
        self.say_foot()

    def activate(self, entry):
        """Enter or a double press: a folder opens here, a file in its app (A1's door)."""
        entry = entry or {}
        path = entry.get('path')
        if not path:return None
        if entry.get('kind') == 'folder' or os.path.isdir(path):return self.show(path, via='open')
        from . import home_files_qt as hq
        return hq.open_in(self.host, path)

    def clipboard(self):
        keys = getattr(self.host, 'windows_keys', None)
        if keys is not None and getattr(keys, 'clipboard', None) is not None:return keys.clipboard
        if getattr(self, '_clipboard', None) is None:
            from .windows_hand import FileClipboard
            self._clipboard = FileClipboard()
        return self._clipboard

    def do(self, what):
        host = self.host;paths = self.chosen_paths()
        from . import bulk_files_qt as bq
        from . import home_files_qt as hq
        if what in ('copy', 'cut'):
            if not paths:return say(host, 'Choose a file or folder first.')
            return say(host, self.clipboard().hold(paths, 'copy' if what == 'copy' else 'move'))
        if what == 'paste':
            clip = self.clipboard()
            if not clip.paths:return say(host, 'Nothing is held to paste: copy or cut a file first.')
            args = clip.batch_args(self.folder)
            return bq.batch(host, args['act'], args['paths'], to=args['to'], said=clip.pasted)
        if what == 'rename':
            path = self.current_path() or (paths[0] if paths else '')
            return hq.rename(host, path) if path else say(host, 'Choose a file or folder to rename.')
        if what == 'delete':
            if not paths:return None
            return hq.delete(host, paths[0]) if len(paths) == 1 else bq.batch(host, 'delete', paths)
        if what == 'for_good':
            from .windows_keys_qt import for_good
            return for_good(host, paths)
        if what == 'open':
            view = self.page.view_widget();item = view.currentItem()
            if item is None:return None
            return self.activate(item.data(0, ENTRY) if view is self.page.list else item.data(ENTRY))
        if what == 'properties':
            from .windows_keys_qt import show_properties
            return show_properties(host, self.current_path() or (paths[0] if paths else self.folder))
        if what == 'command':  # 1.1 B4: Command…, the exact line it is or runs (command_card_qt)
            from .command_card_qt import show as show_command  # 1.1 B4
            return show_command(host, self.current_path() or (paths[0] if paths else self.folder))  # 1.1 B4
        if what == 'read_again':self.reload();return say(host, 'Read again.')
        if what == 'back':return self.living.back()
        if what == 'up':
            parent = str(Path(self.folder).parent)
            return self.show(parent, via='breadcrumb', chosen=[self.folder]) if parent != self.folder else None
        if what == 'all':self.page.view_widget().selectAll();return None
        if what == 'undo':
            # 1.1: a paste's files land before its Undo is recorded; a quick Ctrl+Z waits up to a second for it
            def take_back(left=10):
                note = getattr(getattr(host, 'home_files', None), 'note', None)
                if note is not None and getattr(note, 'undo', None) is not None:return note.undo_now()
                if left > 0:return QTimer.singleShot(100, lambda: take_back(left - 1))
                return say(host, 'Nothing to take back here.')
            return take_back()
        if what == 'address':self.address.setFocus(Qt.ShortcutFocusReason);self.address.selectAll();return None
        if what == 'board':return self.set_view('board')
        return None

    def menu_at(self, view, point):
        """The right-click: what the keys do, in words (each with its key when keys are shown)."""
        from .windows_hand import keyed
        item = view.itemAt(point);menu = QMenu(view);menu.setObjectName('ExplorerMenu')
        if item is not None and not item.isSelected():
            view.clearSelection();item.setSelected(True);view.setCurrentItem(item)
        paths = self.chosen_paths() if item is not None else []

        def add(words, key, what, enabled=True):
            a = menu.addAction(keyed(words, key));a.setEnabled(enabled);a.triggered.connect(lambda checked=False, w=what: self.do(w));return a
        if paths:
            add('Open', 'Enter', 'open');add('Board', 'Ctrl+B', 'board');menu.addSeparator()
            add('Cut', 'Ctrl+X', 'cut');add('Copy', 'Ctrl+C', 'copy');add('Paste', 'Ctrl+V', 'paste', bool(self.clipboard().paths))
            menu.addSeparator();add('Rename', 'F2', 'rename', len(paths) == 1);add('Delete', 'Delete', 'delete')
            add('Delete for good…', 'Shift+Delete', 'for_good');menu.addSeparator()
            copy_path = menu.addAction('Copy the path');copy_path.triggered.connect(lambda: QApplication.clipboard().setText('\n'.join(paths)))
            add('Command…', 'Ctrl+.', 'command', len(paths) == 1)  # 1.1 B4: above Properties, the line it is or runs
            add('Properties', 'Alt+Enter', 'properties', len(paths) == 1)
        else:
            add('Paste', 'Ctrl+V', 'paste', bool(self.clipboard().paths))
            made = menu.addAction('New folder…')
            from . import home_files_qt as hq
            made.triggered.connect(lambda: hq.new_folder(self.host, Path(self.folder)))
            menu.addSeparator();views = menu.addMenu('View')
            for v in ex.VIEWS:
                a = views.addAction(ex.VIEW_WORDS[v]);a.setCheckable(True);a.setChecked(v == self.view)
                a.triggered.connect(lambda checked=False, v=v: self.set_view(v))
            add('Read again', 'F5', 'read_again');add('Command…', 'Ctrl+.', 'command')  # 1.1 B4: the folder's own line
            add('Properties', 'Alt+Enter', 'properties')
        menu.exec(view.viewport().mapToGlobal(point))
        return menu

    # ---- the views --------------------------------------------------------------------------------------------------------------
    def set_view(self, view):
        """List, Icons or Board. From the board, List and Icons bring back the folder of what is in its middle."""
        if view not in ex.VIEWS:return False
        if not self.in_front():
            folder, chosen = self.folder_of_focus()
            if view == 'board':self.sync_bar(force=True);return True
            ex.remember_view(folder, view)
            return self.show(folder, via='board', chosen=[chosen] if chosen else (), view=view)
        if view == 'board':
            target = self.current_path() or (self.chosen_paths() or [self.folder])[0]
            ex.remember_view(self.folder, 'board')
            return self.to_board(target, 'tree')
        ex.remember_view(self.folder, view);self.view = view
        page = self.page
        if page.stack.currentWidget() is not page.empty:
            keep = self.chosen_paths();self.chosen_after = keep
            page.stack.setCurrentWidget(page.icons if view == 'icons' else page.list)
            other = page.icons if view == 'icons' else page.list
            for i in range(other.topLevelItemCount() if other is page.list else other.count()):
                item = other.topLevelItem(i) if other is page.list else other.item(i)
                e = item.data(0, ENTRY) if other is page.list else item.data(ENTRY)
                item.setSelected((e or {}).get('path') in keep)
        if view == 'icons' and not self.waiting:
            self.waiting = [e['path'] for e in self.entries if e.get('kind') != 'folder' and ex.is_picture(e['name']) and e['path'] not in self.thumbs]
        if view == 'icons' and self.waiting:self.next_thumbs(self.generation)
        self.sync_bar(force=True);self.say_foot()
        return True

    def folder_of_focus(self):
        """(the folder to show, the thing to choose in it) for what is in the board's middle; the last folder for a record."""
        living = self.living;focus = getattr(living.nav, 'focus', None) or ''
        entry = (getattr(living, 'files_by_id', None) or {}).get(focus);computer = self.computer()
        path = computer.whole(entry) if entry is not None and computer is not None else ''
        if not path and focus.startswith(PATH):path = focus[len(PATH):]
        if path and os.path.isdir(path):return path, ''
        if path and os.path.isdir(os.path.dirname(path)):return os.path.dirname(path), path
        return (self.folder or self.home()), ''

    def ident_of(self, path):
        """The object id the board knows a file or folder by (made now, objects.get, when it has none)."""
        living = self.living
        known = (getattr(living, 'files_by_abs', None) or {}).get(str(path))
        if known:return known
        found = living.call('objects.get', {'path': str(path)})
        if found is None:
            say(self.host, '%s could not be put on the board: %s' % (tilde(path), living.problem or 'not read'));return ''
        computer = self.computer()
        if computer is not None:computer.hold(found)
        return found['id']

    def to_board(self, path, via='tree'):
        """1.0's board, unchanged, with this file or folder in its middle."""
        ident = self.ident_of(path)
        if not ident:return False
        self.living.go(ident, via if via in ('tree', 'board', 'search', 'breadcrumb', 'open', 'tab', 'start') else 'tree', 'board', title=Path(path).name or str(path))
        self.sync_bar(force=True)
        return True

    def go_typed(self, text):
        path = ex.address(text, self.folder, self.home(), ex.letters())
        if not path:
            say(self.host, 'No folder or file is at %s.' % (str(text).strip() or 'that address'));self.address.selectAll();return False
        if os.path.isdir(path):done = self.show(path, via='open', view=None if ex.view_for(path) != 'board' else 'list')
        else:done = self.show(os.path.dirname(path), via='open', chosen=[path], view=None if ex.view_for(os.path.dirname(path)) != 'board' else 'list')
        if done:self.page.view_widget().setFocus(Qt.OtherFocusReason)
        return done

    def sync_bar(self, force=False):
        """The bar's parts for what is in front: the address in place of the breadcrumb while the Explorer is; List · Icons ·
        Board there and on the board."""
        one = getattr(self.host, 'one_bar', None);crumbs = getattr(one, 'crumbs', None)
        if one is None or crumbs is None:return
        try:
            from .centre_one_qt import depth
            front = self.in_front();where = depth(self.host)
            if crumbs.words.isVisibleTo(one.bar) == front:crumbs.words.setVisible(not front)
            if self.address.isVisibleTo(one.bar) != front:self.address.setVisible(front)
            on = front or where in ('board', 'map')
            if self.switch.isVisibleTo(one.bar) != on:self.switch.setVisible(on)
            self.switch.show_view(self.view if front else 'board')
            if on and not front:      # on the board's narrow bar: the breadcrumb gives way first, then Icons (List brings the folder back)
                s = scale_of(self.host);least = round(120 * s)
                if crumbs.words.minimumWidth() > least:crumbs.words.setMinimumWidth(least)
                narrow = one.bar.width() < round(760 * s)
                if self.switch.buttons['icons'].isVisibleTo(self.switch) == narrow:self.switch.buttons['icons'].setVisible(not narrow)
            elif front and not self.switch.buttons['icons'].isVisibleTo(self.switch):self.switch.buttons['icons'].setVisible(True)
            if front and (force or not self.address.hasFocus()):
                words = tilde(self.folder) if self.folder else ''
                if self.address.text() != words:self.address.setText(words)
        except RuntimeError:      # the window is closing
            pass

    def status(self):
        """What the Explorer shows, for tests and checks."""
        page = self.page;view = page.view_widget()
        listed = [page.list.topLevelItem(i).text(0) for i in range(page.list.topLevelItemCount())]
        icons = [page.icons.item(i) for i in range(page.icons.count())]
        return {'front': self.in_front(), 'folder': self.folder, 'view': self.view, 'sort': [ex.COLUMNS[self.sort[0]], 'down' if self.sort[1] else 'up'],
                'rows': listed, 'chosen': [Path(p).name for p in self.chosen_paths()], 'foot': page.foot.text(),
                'address': self.address.text(), 'address_shown': self.address.isVisibleTo(self.address.parentWidget()) if self.address.parentWidget() else False,
                'switch': [v for v, b in self.switch.buttons.items() if b.isChecked()],
                'thumbnails': sum(1 for i in icons if (i.data(ENTRY) or {}).get('path') in self.thumbs),
                'pictures': sum(1 for i in icons if ex.is_picture(i.text())), 'showing': 'empty' if page.stack.currentWidget() is page.empty else ('icons' if view is page.icons else 'list')}

    def sort_by(self, column):
        """A press on a column sorts by it; a second press turns it round. A first press on Modified, Size or Links puts the newest,
        largest or most linked first."""
        current, descending = self.sort
        if column == current:descending = not descending
        else:descending = ex.FIRST_ORDER.get(column) == 'down'
        self.sort = (column, descending);self.chosen_after = self.chosen_paths();self.fill()


# ---- Rules: the bin's name -------------------------------------------------------------------------------------------------------
def set_bin_word(host, word):
    if word not in ex.BIN_WORDS:return None
    session = getattr(host, 'session', None)
    if session is not None:
        session.state['bin_word'] = word
        try:session.save()
        except Exception:  # noqa: BLE001 - kept for this run at least
            pass
    can = getattr(host, 'trash_can', None)
    if can is not None and hasattr(can, 'name_it'):can.name_it(word)
    say(host, 'The bin is called %s.' % word)
    return word


def rules_lines(host, menu):
    """Rules ▸ The bin's name: Recycle Bin or DELETE."""
    words = QMenu("The bin's name", menu);group = QActionGroup(words);group.setExclusive(True)
    for word in ex.BIN_WORDS:
        row = words.addAction(word);row.setCheckable(True);row.setChecked(bin_word(host) == word);group.addAction(row)
        row.triggered.connect(lambda checked=False, word=word: set_bin_word(host, word))
    menu.addMenu(words)
    return words


# ---- install ------------------------------------------------------------------------------------------------------------------
def install(host):
    """shell2 calls this once the tree, the history and the one bar stand (after W1's keys)."""
    if getattr(host, 'explorer', None) is not None:return host.explorer
    if getattr(host, 'living_nav', None) is None or getattr(host, 'central_stack', None) is None:
        host.explorer = None;return None
    host.explorer = Explorer(host)
    page = getattr(host, 'cabinet_page', None)
    if page is not None:
        try:page.refresh(force=True)
        except RuntimeError:
            pass
    return host.explorer
