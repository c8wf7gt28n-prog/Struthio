"""Home's files, whole, in the window (Graphite 1.0 L6b).

1.0 L6 put the whole computer in the Files tab's tree ("This computer /", Home open at start). Here, everything a person does
to a file works in Home too, not only in the workspace's Files:

    the tree's right-click   on a file or folder of your home (or of Files, shown where it lives in Home): Open in <its
                             program> (A1's door: its window named on the board's tile, each save recorded as a revision),
                             Rename…, Move to…, New folder…, Delete; under More: Open here (its working view), Open with, Copy
                             the path. Delete puts it in DELETE: a file of Files in Files' own, a file of your home in your
                             home's own bin, the system's (home_trash: the freedesktop.org Trash in ~/.local/share), which the
                             owner's other programs share. Never removed for good. (On screen the place is always DELETE, the
                             owner's word of 14 November 2026; the specification's name stays in the code.)
    drag in the tree         a file or folder of your home dragged onto a folder of the tree moves into it (files.move, on
                             your press: the drop); dragged onto DELETE at the column's foot, it is deleted (into DELETE).
    Undo                     each of these says what it did on a line under the tab's header, with Undo for a while: the
                             old name back, the old folder back, the thing out of DELETE where it was (files.restore), a new
                             folder into DELETE. DELETE keeps a deletion until you restore it, Undo or not.
    DELETE, the room         lists what was deleted from your home ("From your home") under Files' own, each with restore.
    a focused file           a file of your home focused on the board is watched (as an open working view's file is, L4): a
                             save by another program is noticed at once, its new revision recorded (revisions.record: the
                             Kernel reads the bytes itself), the tile and the breadcrumb follow; renamed in its folder by
                             another program, it is found again by its inode and keeps its identity.

Every change here is the owner's own press through the Kernel (files.rename, files.move, files.mkdir, files.trash,
files.restore with the owner's principal). Her changes never come this way: they pass home_reach.her_change and her grants in
the Kernel (files_service.may_change, K2's tools, A1, K5, K9, K6's Apply).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QFileSystemWatcher, QMimeData, QObject, Qt, QTimer, QUrl
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from . import boss_theme as bt
from . import computer_tree_qt as ct
from . import home_reach as hr

ROW_MIME = 'application/x-graphite-home-row'     # a row of the tree dragged: its whole path
UNDO_MS = 45000                                   # the line with Undo stays this long (the Trash keeps a deletion for good)
FOCUS_MS = 900                                    # how often the focus is glanced at (a string compared; nothing read)
CALM_MS = 300                                     # a burst of file events is looked at once
KINDS = ('home-file', 'home-folder')


def kernel_of(host):
    return getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)


def act(host, op, args):
    """A Kernel operation with the owner's principal (your press): its result, or ValueError with its words."""
    kernel = kernel_of(host)
    if kernel is None:raise ValueError('Graphite\'s Kernel is not open')
    from .engineering_kernel import operator
    answer = kernel.dispatch(op, args, operator())
    if not answer.get('ok'):
        raise ValueError(str((answer.get('error') or {}).get('message') or 'not done'))
    return answer['result']


def say(host, words, ms=9000):
    try:host.statusBar().showMessage(words, ms)
    except (AttributeError, RuntimeError):pass
    return words


def shown(path):
    return hr.tilde(path)


def path_of_row(node_id):
    """The whole path a row of the computer's tree names (FS + branch + ':' + path), or ''."""
    node_id = str(node_id or '')
    if not node_id.startswith(ct.FS):return ''
    return node_id[len(ct.FS):].partition(':')[2]


def changeable(kernel, path):
    """(area, '') when the owner's tree offers to change this file or folder; else ('', why not). Your home and Files; never
    your home folder itself, Files itself or Graphite's own records and program."""
    path = Path(path)
    try:
        place = Path(os.path.realpath(path.parent)) / path.name
        where = hr.area(kernel, place) if not path.is_symlink() else hr.area(kernel, Path(os.path.realpath(path.parent)))
    except (OSError, RuntimeError):
        return '', 'not readable here'
    if where not in (hr.HOME, hr.FILES):return '', hr.AREA_WORDS.get(where, where)
    if place == hr.home():return '', 'your home folder itself'
    try:files = hr.files_root(kernel).resolve()
    except (OSError, RuntimeError):
        files = hr.files_root(kernel)
    if place == files:return '', 'the workspace\'s Files folder itself'
    from .home_trash import holds_graphite
    if path.is_dir() and not path.is_symlink() and holds_graphite(kernel, place):return '', 'it holds Graphite\'s workspace'
    return where, ''


def branch_id(path):
    """The tree's row for a path (Home's branch for a path in your home, else the computer's)."""
    path = Path(path)
    return ct.FS + ('home:' if hr.within(path, hr.home()) else 'root:') + str(path)


# ---- the right-click ------------------------------------------------------------------------------------------------------------
def target_for(host, page, node):
    """context_menu.find_cabinet: a file or folder of your home (or of Files) under the pointer, as a menu target of its own
    kind ('home-file', 'home-folder'); None for any other row."""
    ident = str(node.get('id') or '')
    if not ident.startswith(ct.FS) or node.get('role') not in ('file', 'folder'):return None
    kernel = kernel_of(host);path = path_of_row(ident)
    if kernel is None or not path:return None
    where, why = changeable(kernel, path)
    if not where:return None
    from .context_menu import Target
    folder = node.get('role') == 'folder'
    noun = '%s %s' % ('folder' if folder else 'file', hr.AREA_WORDS[where])
    return Target('home-folder' if folder else 'home-file', node.get('label') or Path(path).name, noun, ident=ident,
                  data=dict(node=node, path=str(path), area=where), surface='cabinet', owner=page, icon='files')


def entries(host, t):
    """context_menu's provider: what a person does to a file or folder of your home, from the tree."""
    if t.surface != 'cabinet' or t.kind not in KINDS:return []
    from .context_menu import Entry, Refused, copy_text
    path = Path(t.data['path']);folder = t.kind == 'home-folder';files = t.data.get('area') == hr.FILES

    def run(do, *args):
        def go():
            try:return do(host, *args)
            except ValueError as exc:raise Refused(str(exc).split(': ', 1)[-1]) from None
        return go
    out = []
    if not folder:
        from .app_files_qt import program_words
        words, name = program_words(host, path)
        out.append(Entry('open:outside', words if name else 'Open in its program…', 'open', run(open_in), glyph='window', operation='appfile.open',
                         tip='In its own program, in a window of its own; when the program saves it, the new revision is recorded here'))
    out.append(Entry('open', 'Open here' if not folder else 'Show it on the board', 'open', run(open_here, t.ident), operation='objects.get',
                     tip='Its working view in the centre' if not folder else 'The folder in the middle of the board'))
    out.append(Entry('rename', 'Rename…', 'modify', run(rename, path), operation='files.rename',
                     tip='A new name in the same folder; it keeps its identity. Undo puts the old name back'))
    out.append(Entry('move:to', 'Move to…', 'modify', run(move_to, path), operation='files.move',
                     tip='Into another folder (or drag it onto a folder in the tree); it keeps its identity. Undo puts it back'))
    out.append(Entry('new:folder', 'New folder…', 'tree', run(new_folder, path if folder else path.parent), operation='files.mkdir',
                     tip='A new folder in %s' % shown(path if folder else path.parent)))
    out.append(Entry('copy:path', 'Copy the path', 'edit', lambda: copy_text(host, str(path), 'Copied the path')))
    out.append(Entry('trash', 'Delete', 'danger', run(delete, path), operation='files.trash',
                     tip=('DELETE keeps it; restore puts it back' if files else
                          "DELETE keeps it, with where it was, in your home's own bin (%s, which your other programs share); restore, or Undo now, "
                          'puts it back' % shown(trash_place()))))
    return out


def trash_place():
    from .home_trash import trash_dir
    return trash_dir()


# ---- what a person does -----------------------------------------------------------------------------------------------------------
def open_in(host, path):
    """Open in <its program>: A1's door (appfile.open), so its window, its saves and its close are seen."""
    watch = getattr(host, 'app_files', None)
    if watch is None:
        from .apps_qt import open_default
        return open_default(host, str(path))
    result = watch.open(str(path))
    if not result.get('ok'):raise ValueError(result.get('words') or result.get('reason') or 'it did not start')
    return result


def open_here(host, node_id):
    living = getattr(host, 'living_nav', None)
    if living is None or living.computer is None:return None
    return living.computer.open(node_id)


def id_of(host, path):
    """The object id a path has now (L1's, or one made for it in Home), or ''."""
    living = getattr(host, 'living_nav', None)
    known = dict(getattr(living, 'files_by_abs', None) or {})
    kernel = kernel_of(host)
    if kernel is not None:
        from . import living_nav
        known.update(living_nav.known_outside(kernel))
    return known.get(str(path)) or ''


def rename(host, path, name=None):
    path = Path(path)
    if name is None:
        name, ok = QInputDialog.getText(host, 'Rename', 'A new name for %s' % path.name, text=path.name)
        if not ok:return None
    name = str(name).strip()
    if not name or name == path.name:return None
    ident = id_of(host, path)
    act(host, 'files.rename', {'path': str(path), 'name': name})
    new = path.with_name(name)
    return after(host, ident, new, 'Renamed %s to %s, in %s.' % (path.name, name, shown(path.parent)),
                 undo=lambda: (act(host, 'files.rename', {'path': str(new), 'name': path.name}), path)[1], undo_words='the old name is back')


def move_to(host, path, folder=None):
    path = Path(path)
    if folder is None:
        folder = QFileDialog.getExistingDirectory(host, 'Move %s to' % path.name, str(path.parent))
        if not folder:return None
    folder = Path(folder)
    if folder == path.parent:return say(host, '%s is in %s already.' % (path.name, shown(folder)))
    ident = id_of(host, path)
    moved = act(host, 'files.move', {'path': str(path), 'to': str(folder)})
    new = folder / str(moved.get('name') or path.name)
    return after(host, ident, new, 'Moved %s to %s.' % (path.name, shown(folder)),
                 undo=lambda: _move_back(host, new, path), undo_words='it is back in %s' % shown(path.parent))


def _move_back(host, new, old):
    back = act(host, 'files.move', {'path': str(new), 'to': str(old.parent)})
    return old.parent / str(back.get('name') or old.name)


def new_folder(host, folder, name=None):
    folder = Path(folder)
    if name is None:
        name, ok = QInputDialog.getText(host, 'New folder', 'The new folder\'s name, in %s' % shown(folder), text='New folder')
        if not ok:return None
    name = str(name).strip()
    if not name:return None
    act(host, 'files.mkdir', {'path': str(folder), 'name': name})
    made = folder / name
    return after(host, '', made, 'Made the folder %s in %s.' % (name, shown(folder)),
                 undo=lambda: (act(host, 'files.trash', {'path': str(made)}), None)[1], undo_words='the new folder is in DELETE')


def delete(host, path):
    """Delete, on your press: into DELETE (for a file of your home, your home's own bin, the freedesktop.org one; for a file of
    Files, Files' own); Undo restores it."""
    path = Path(path)
    ident = id_of(host, path)
    gone = act(host, 'files.trash', {'path': str(path)})
    return after(host, ident, None, '%s is in DELETE (from %s).' % (path.name, shown(path.parent)),
                 undo=lambda: _restore(host, gone['id']), undo_words='it is back where it was', trash=True)


def _restore(host, ident):
    back = act(host, 'files.restore', {'id': ident})
    restored = str(back.get('restored') or '')
    if restored and not restored.startswith('/'):
        kernel = kernel_of(host)
        restored = str(hr.files_root(kernel) / restored) if kernel is not None else restored
    return Path(restored) if restored else None


def restore(host, ident, place=''):
    """Restore from the Trash (the DELETE room's rows): back where it was; the tree shows it."""
    back = _restore(host, ident)
    return after(host, id_of(host, back) if back else '', back, 'Restored %s.' % (shown(back) if back else place or 'it'), keep_undo=False)


def after(host, ident, new_path, words, undo=None, undo_words='', trash=False, keep_undo=True):
    """After a change from the tree: the object keeps its id at its new place (held beside Files' reading), the tree shows the
    new place, the board and the breadcrumb follow, the words said with Undo."""
    living = getattr(host, 'living_nav', None)
    if living is not None and living.computer is not None:
        tree = living.computer
        if ident:
            try:
                found = living.call('objects.get', {'id': ident})
                if found is not None:
                    tree.hold(found)
                    if new_path is not None:living.nav.renamed(ident, Path(new_path).name)
            except Exception:  # noqa: BLE001 - the next reading of the tree finds it all the same
                pass
        if new_path is not None:
            chain = [];folder = Path(new_path).parent
            while hr.within(folder, hr.home()) and folder != hr.home().parent:
                chain.append(branch_id(folder))
                if folder == hr.home():break
                folder = folder.parent
            tree.listed |= set(chain);tree.keep_open(chain);tree.remember()
        page = tree.page()
        if page is not None:
            page.refresh(force=True)
            row = branch_id(new_path) if new_path is not None else ''
            if row and row in page.items:page.select(row, reveal=True)
        try:living.after_reading()
        except Exception:  # noqa: BLE001 - the breadcrumb is drawn again at the next move
            pass
    watch = getattr(host, 'home_files', None)
    if watch is not None:
        watch.note.tell(words, undo if keep_undo else None, undo_words, trash)
        watch.redraw()
    try:
        from .shell2 import refresh_library
        refresh_library(host)          # DELETE's count at the column's foot
    except Exception:  # noqa: BLE001
        pass
    return say(host, words)


# ---- the line under the tab's header: what was done, with Undo -------------------------------------------------------------------
class Note(QWidget):
    def __init__(self, host, parent=None):
        super().__init__(parent)
        self.host = host;self.undo = None;self.undo_words = '';self.setObjectName('HomeFilesNote')
        self.setAccessibleName('What was just done in your home, with Undo')
        column = QVBoxLayout(self);column.setContentsMargins(8, 5, 8, 6);column.setSpacing(4)      # the words over their buttons: the column is narrow
        self.words = QLabel(self);self.words.setObjectName('HomeFilesWords');self.words.setWordWrap(True);column.addWidget(self.words)
        box = QHBoxLayout();box.setContentsMargins(0, 0, 0, 0);box.setSpacing(8);box.addStretch(1);column.addLayout(box)
        self.back = QPushButton('Undo', self);self.back.setObjectName('HomeFilesUndo');self.back.setCursor(Qt.PointingHandCursor)
        self.back.setAccessibleName('Undo what was just done');self.back.clicked.connect(self.undo_now);box.addWidget(self.back)
        self.bin = QPushButton('DELETE', self);self.bin.setObjectName('HomeFilesBin');self.bin.setCursor(Qt.PointingHandCursor)
        self.bin.setAccessibleName('Open DELETE');self.bin.setToolTip('DELETE: what you deleted, from Files and from your home, each with restore')
        self.bin.clicked.connect(self.open_trash);box.addWidget(self.bin)
        self.timer = QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(UNDO_MS);self.timer.timeout.connect(self.calm)
        self.restyle();self.hide()

    def restyle(self):
        try:
            from .living_nav_qt import scale_of
            px = max(12, round(13 * scale_of(self.host)))
        except Exception:  # noqa: BLE001
            px = 13
        self.setStyleSheet(
            'QWidget#HomeFilesNote {background:%s;border:1px solid %s;border-radius:6px;}'
            'QLabel#HomeFilesWords {font-family:"%s";font-size:%dpx;color:%s;background:transparent;border:0;}'
            'QPushButton {font-family:"%s";font-size:%dpx;color:%s;background:%s;border:1px solid %s;border-radius:5px;padding:2px 10px;}'
            'QPushButton:hover {border-color:%s;}'
            % (bt.CARD, bt.LINE, bt.FACE, px, bt.TEXT, bt.FACE, px, bt.TEXT, bt.RAISED, bt.LINE_STRONG, bt.LINE_STRONG))
        self.setAttribute(Qt.WA_StyledBackground, True)

    def tell(self, words, undo=None, undo_words='', trash=False):
        self.words.setText(words);self.undo = undo;self.undo_words = undo_words
        self.back.setVisible(undo is not None);self.back.setEnabled(undo is not None);self.bin.setVisible(bool(trash))
        self.show();self.timer.start()

    def undo_now(self):
        do, self.undo = self.undo, None
        if do is None:return None
        self.back.setEnabled(False)
        try:
            back = do()
        except ValueError as exc:
            self.tell('Not undone: %s' % str(exc).split(': ', 1)[-1]);return None
        words = 'Undone: %s.' % self.undo_words if self.undo_words else 'Undone.'
        return after(self.host, id_of(self.host, back) if isinstance(back, Path) else '', back if isinstance(back, Path) else None, words, keep_undo=False)

    def open_trash(self):
        from .shell2 import open_destination
        return open_destination(self.host, 'trash')

    def calm(self):
        self.undo = None;self.hide()


# ---- drag a row onto a folder -------------------------------------------------------------------------------------------------------
class Dragging(QObject):
    """The tree's rows of your home can be dragged onto a folder of the tree (a move, on your drop) or onto DELETE."""

    def __init__(self, host, tree):
        super().__init__(tree)
        self.host = host;self.tree = tree;self.start = None;self.over = None
        tree.setAcceptDrops(True);tree.viewport().setAcceptDrops(True);tree.viewport().installEventFilter(self)

    def row_path(self, item):
        if item is None:return None
        try:node = item.data(0, Qt.UserRole) or {}
        except RuntimeError:
            return None
        if node.get('role') not in ('file', 'folder'):return None
        path = path_of_row(node.get('id'))
        kernel = kernel_of(self.host)
        if not path or kernel is None or not changeable(kernel, path)[0]:return None
        return Path(path), node.get('role')

    def eventFilter(self, obj, event):
        kind = event.type()
        try:
            if kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                point = event.position().toPoint();found = self.row_path(self.tree.itemAt(point))
                self.start = (point, found[0]) if found else None
                return False
            if kind == QEvent.MouseMove and self.start is not None and (event.buttons() & Qt.LeftButton):
                if (event.position().toPoint() - self.start[0]).manhattanLength() >= QApplication.startDragDistance():
                    path = self.start[1];self.start = None;self.drag(path);return True
                return False
            if kind == QEvent.MouseButtonRelease:
                self.start = None;return False
            if kind in (QEvent.DragEnter, QEvent.DragMove) and event.mimeData().hasFormat(ROW_MIME):
                source = Path(bytes(event.mimeData().data(ROW_MIME)).decode('utf-8', 'surrogateescape'))
                folder = self.folder_at(event.position().toPoint(), source)
                if folder is None:
                    event.ignore();self.over = None
                else:
                    event.setDropAction(Qt.MoveAction);event.accept()
                    if folder != self.over:say(self.host, 'Drop to move %s into %s' % (source.name, shown(folder)), 3000)
                    self.over = folder
                return True
            if kind == QEvent.DragLeave:
                self.over = None;return False
            if kind == QEvent.Drop and event.mimeData().hasFormat(ROW_MIME):
                source = Path(bytes(event.mimeData().data(ROW_MIME)).decode('utf-8', 'surrogateescape'))
                folder = self.folder_at(event.position().toPoint(), source);self.over = None
                if folder is None:
                    event.ignore();return True
                event.setDropAction(Qt.MoveAction);event.accept()
                QTimer.singleShot(0, lambda: self.dropped(source, folder))
                return True
        except RuntimeError:
            return False
        return False

    def folder_at(self, point, source):
        """The folder of the tree under the pointer that `source` may be moved into, or None (itself, inside itself, the folder it
        is in already, a row that is not a folder of your home or of Files)."""
        found = self.row_path(self.tree.itemAt(point))
        if found is None or found[1] != 'folder':return None
        folder = found[0]
        if folder == source or hr.within(folder, source) or folder == source.parent:return None
        return folder

    def drag(self, path):
        data = QMimeData();data.setData(ROW_MIME, str(path).encode('utf-8', 'surrogateescape'));data.setUrls([QUrl.fromLocalFile(str(path))])
        drag = QDrag(self.tree);drag.setMimeData(data)
        drag.exec(Qt.MoveAction)

    def dropped(self, source, folder):
        try:return move_to(self.host, source, folder)
        except ValueError as exc:
            return say(self.host, '%s was not moved: %s' % (source.name, str(exc).split(': ', 1)[-1]))


# ---- a focused file of your home, watched ---------------------------------------------------------------------------------------
class Focused(QObject):
    """The file of your home in the board's focus, watched like an open view's file: another program's save is noticed, its
    revision recorded; a rename in its folder by another program is found by its inode."""

    def __init__(self, host):
        super().__init__(host)
        self.host = host;self.ident = '';self.path = None;self.state = None;self.digest = ''
        self.watcher = QFileSystemWatcher(self);self.watcher.fileChanged.connect(self.changed);self.watcher.directoryChanged.connect(self.changed)
        self.calm = QTimer(self);self.calm.setSingleShot(True);self.calm.setInterval(CALM_MS);self.calm.timeout.connect(self.look)
        self.timer = QTimer(self);self.timer.setInterval(FOCUS_MS);self.timer.timeout.connect(self.glance);self.timer.start()

    def glance(self):
        living = getattr(self.host, 'living_nav', None)
        focus = str(getattr(getattr(living, 'nav', None), 'focus', '') or '')
        if focus != self.ident:self.follow(focus)

    def follow(self, ident):
        """Watch the focused object when it is a file of your home (outside Files: Files has L1's own watch)."""
        if self.watcher.files() or self.watcher.directories():
            self.watcher.removePaths(list(self.watcher.files()) + list(self.watcher.directories()))
        self.ident = ident;self.path = None;self.state = None;self.digest = ''
        living = getattr(self.host, 'living_nav', None);kernel = kernel_of(self.host)
        entry = (getattr(living, 'files_by_id', None) or {}).get(ident) if ident else None
        if not entry or kernel is None or entry.get('kind') == 'folder' or not str(entry.get('path') or '').startswith('/'):return
        path = Path(entry['path'])
        if hr.area(kernel, path) != hr.HOME or not path.is_file():return
        from . import depths as dp
        self.path = path;self.state = dp.file_state(path)
        try:self.digest = dp.sha256_of(path)[0] if path.stat().st_size <= dp.BIGGEST else ''
        except OSError:
            self.digest = ''
        self.watcher.addPath(str(path));self.watcher.addPath(str(path.parent))

    def changed(self, *_):
        self.calm.start()

    def elsewhere(self):
        """Another program's own Save (LibreOffice's, Graphite's view's, A1's session) records it with better words."""
        watch = getattr(self.host, 'app_files', None)
        try:
            if watch is not None and watch.session_of(self.path) is not None:return True
            from .depths_qt import path_of
            from .split_qt import all_tabs
            return any(path_of(tab) is not None and Path(path_of(tab)) == self.path for tab in all_tabs(self.host))
        except Exception:  # noqa: BLE001 - nothing else watches it: this watch records it
            return False

    def look(self):
        if self.path is None:return None
        from . import depths as dp
        path = self.path
        if not path.is_file():return self.lost()
        if str(path) not in self.watcher.files():self.watcher.addPath(str(path))      # a program that writes a new file over the old one
        state = dp.file_state(path)
        if state == self.state:return None
        self.state = state
        try:digest = dp.sha256_of(path)[0] if state[0] <= dp.BIGGEST else ''
        except OSError:
            return None
        if not digest or digest == self.digest:return None
        before, self.digest = self.digest, digest
        words = '%s was saved by another program at %s.' % (path.name, time.strftime('%H:%M'))
        if not self.elsewhere():
            try:
                got = act(self.host, 'revisions.record', dict({'path': str(path), 'expected_sha256': digest, 'how': 'outside'},
                                                              **({'previous_sha256': before} if before else {})))
                if got.get('recorded'):words = '%s was saved by another program at %s: revision %d is recorded.' % (path.name, time.strftime('%H:%M'), got['revision'])
            except ValueError as exc:
                words += ' Its revision was not recorded: %s' % str(exc).split(': ', 1)[-1]
        self.refresh()
        return say(self.host, words, 12000)

    def lost(self):
        """Not at its path: renamed or moved in its folder by another program (found by its inode), or gone."""
        path = self.path;living = getattr(self.host, 'living_nav', None)
        try:inode = (self.state[2] if self.state else None)
        except (TypeError, IndexError):
            inode = None
        found = None
        try:
            for entry in os.scandir(path.parent):
                try:
                    if inode is not None and entry.is_file(follow_symlinks=False) and entry.inode() == inode:found = Path(entry.path);break
                except OSError:
                    continue
        except OSError:
            pass
        if found is None:
            self.path = None
            return say(self.host, '%s is not where it was (%s): moved or deleted by another program.' % (path.name, shown(path.parent)), 12000)
        got = living.call('objects.get', {'path': str(found)}) if living is not None else None
        if got is not None and living.computer is not None:
            living.computer.hold(got)
            if got['id'] == self.ident:
                living.nav.renamed(got['id'], found.name);living.note = 'renamed from ' + path.name
        self.follow(self.ident)
        self.refresh()
        return say(self.host, '%s was renamed %s by another program; it is the same file.' % (path.name, found.name), 12000)

    def refresh(self):
        """The focused object read again (its size, its state), the board, the tree and the breadcrumb drawn from it."""
        living = getattr(self.host, 'living_nav', None)
        if living is None:return
        try:
            got = living.call('objects.get', {'id': self.ident}) if self.ident else None
            if got is not None and living.computer is not None:living.computer.hold(got)
            living.after_reading()
        except Exception:  # noqa: BLE001 - drawn again at the next reading
            pass
        watch = getattr(self.host, 'home_files', None)
        if watch is not None:watch.redraw()


# ---- the DELETE room: your home's Trash, with Restore ----------------------------------------------------------------------------
def trash_rows(tab):
    """files_qt.TrashTab: your home's Trash under Files' DELETE, each entry with Restore."""
    from .files_qt import when
    from .shell2 import QUIET, call, escape_text, role, sentence
    data = call(tab.host, 'files.trash_list') or {}
    rows = data.get('home') or []
    first = tab.box.itemAt(1).widget() if tab.box.count() > 1 else None      # Files' own lead: said of Files, when your home's are here
    if rows and isinstance(first, QLabel) and first.text() == 'Nothing is in DELETE.':first.setText('Nothing from Files is in DELETE.')
    tab.box.addWidget(role(QLabel('From your home'), 'item'))
    lead = QLabel(('Nothing deleted from your home is here.' if not rows else
                   "What you deleted in your home waits here, kept in your home's own bin (%s), as your other programs keep it. Restore "
                   'puts each back where it was.') % escape_text(str(data.get('home_trash') or '')))
    lead.setWordWrap(True);lead.setStyleSheet('color:%s' % QUIET);tab.box.addWidget(lead)

    def put_back(row):
        try:restore(tab.host, row['id'], row.get('place') or '')
        except ValueError as exc:
            say(tab.host, 'Not restored: %s' % str(exc).split(': ', 1)[-1])
        tab.reload()
    for row in rows[:200]:
        kind = 'folder' if row.get('kind') == 'folder' else 'file'
        tab.box.addWidget(sentence('%s  ·  a %s  ·  deleted %s  ·  {restore}' % (escape_text(row.get('place') or row.get('original') or row.get('name')), kind,
                                                                              when(row['at']) if row.get('at') else 'at a time not said'),
                                   {'restore': ('restore', lambda r=row: put_back(r))}))
    if len(rows) > 200:
        more = QLabel('%d more in DELETE, not listed here.' % (len(rows) - 200));more.setStyleSheet('color:%s' % QUIET);tab.box.addWidget(more)


def trash_count(result):
    """DELETE's count at the column's foot: Files' DELETE and your home's Trash."""
    result = result or {}
    return len(result.get('trash') or ()) + len(result.get('home') or ())


# ---- installed once ---------------------------------------------------------------------------------------------------------------
class HomeFiles(QObject):
    def __init__(self, tree):
        super().__init__(tree)
        self.tree = tree;self.host = tree.host
        page = tree.page()
        self.note = Note(self.host)
        if page is not None:
            holder = page.stack.widget(0) if page.stack.count() else None
            layout = holder.layout() if holder is not None else None
            if layout is not None:
                self.note.setParent(holder);layout.insertWidget(1, self.note)
            self.dragging = Dragging(self.host, page.tree)
        self.focused = Focused(self.host)

    def redraw(self):
        """The board drawn again from a new reading of the desk (its FILE tiles' words)."""
        watch = getattr(self.host, 'app_files', None)
        if watch is not None and hasattr(watch, 'redraw'):return watch.redraw()
        page = getattr(self.host, 'field_page', None);board = getattr(page, 'board', None)
        if board is None:return None
        try:
            board._desk_key = None;board._stale = True
            if board.isVisible():board.rebuild()
        except RuntimeError:
            pass
        return None


def install(tree):
    """computer_tree_qt.install calls this once, with the computer's rows."""
    host = tree.host
    if getattr(host, 'home_files', None) is not None:return host.home_files
    host.home_files = HomeFiles(tree)
    return host.home_files
