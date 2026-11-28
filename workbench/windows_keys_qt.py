"""A Windows hand's keys in Graphite's window (Graphite 1.1 W1), and the keys that work whichever app is in front.

PLAN_1.1.md, W1 (a) to (c). windows_hand holds the settings, the file clipboard and Properties' words; here is the window:

  in Files         over the Files tree (the keys go to the tree first, so the window's own Copy and Paste for text do not
                   take them): Ctrl+C and Ctrl+X hold the chosen files, Ctrl+V pastes them into the folder in front as one
                   change with one Undo (files.batch); F2 renames; Delete puts the chosen in the bin (one Undo); Shift+Delete
                   asks, then deletes for good; Enter opens a file in its app; Alt+Enter shows Properties; F5 reads the
                   folders again; Backspace goes back; Ctrl+A chooses every row; Ctrl+Z takes the last change back.
  Properties       a small page: name, kind, size, dates, where it is, who may read and change it, what opens it. Esc closes.
  from any app     graphite-do (tools/graphite-do) speaks to the running window over a local socket of this user's
                   ($XDG_RUNTIME_DIR/graphite-do.sock): apps, files, show, lock, tasks, screenshot. Fluxbox's keys file,
                   written by the session (LS_XSESSION.sh, graphite-do --write-keys), puts them on the Windows key, Win+E,
                   Win+D, Win+L, Ctrl+Alt+Del and PrintScreen; Alt+Tab and Alt+F4 are Fluxbox's own NextWindow and Close.
  Show keys        Rules ▸ Show keys: menus and tips print their keys (the default in 1.1), or none (as 0.5.2 to 1.0).
  DOS words        Rules ▸ DOS words: on, show me only, off (dos_words).

Every change here is the owner's own press through the Kernel, as the tree's right-click is (home_files_qt, bulk_files_qt).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication, QKeySequence
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QMenu, QMessageBox, QVBoxLayout

from . import windows_hand as wh

VERBS = ('apps', 'files', 'show', 'lock', 'tasks', 'screenshot', 'ping')
SOCKET_NAME = 'graphite-do.sock'


def socket_path(environ=None):
    """Where the window listens: GRAPHITE_DO_SOCKET, else $XDG_RUNTIME_DIR/graphite-do.sock, else one in the temporary folder
    named for this user. tools/graphite-do reads the same."""
    environ = os.environ if environ is None else environ
    if environ.get('GRAPHITE_DO_SOCKET'):return Path(environ['GRAPHITE_DO_SOCKET'])
    run = environ.get('XDG_RUNTIME_DIR')
    if run and os.path.isdir(run):return Path(run) / SOCKET_NAME
    return Path('/tmp') / ('graphite-do-%d.sock' % os.getuid())


def say(host, words, ms=9000):
    try:host.statusBar().showMessage(words, ms)
    except (AttributeError, RuntimeError):pass
    return words


def kernel_of(host):
    return getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)


# ---- the Files tree's keys ---------------------------------------------------------------------------------------------------------
KEYS = {  # (key, modifiers) -> what it does
    (Qt.Key_C, Qt.ControlModifier): 'copy', (Qt.Key_X, Qt.ControlModifier): 'cut', (Qt.Key_V, Qt.ControlModifier): 'paste',
    (Qt.Key_F2, Qt.NoModifier): 'rename', (Qt.Key_Delete, Qt.NoModifier): 'delete', (Qt.Key_Delete, Qt.ShiftModifier): 'for_good',
    (Qt.Key_Return, Qt.NoModifier): 'open', (Qt.Key_Enter, Qt.KeypadModifier): 'open', (Qt.Key_Return, Qt.AltModifier): 'properties',
    (Qt.Key_Enter, Qt.AltModifier | Qt.KeypadModifier): 'properties', (Qt.Key_F5, Qt.NoModifier): 'read_again',
    (Qt.Key_Backspace, Qt.NoModifier): 'back', (Qt.Key_A, Qt.ControlModifier): 'all', (Qt.Key_Z, Qt.ControlModifier): 'undo',
}
TIPS = {'copy': ('Copy', 'Ctrl+C'), 'cut': ('Cut', 'Ctrl+X'), 'paste': ('Paste', 'Ctrl+V'), 'rename': ('Rename', 'F2'),
        'delete': ('Delete (into the bin)', 'Delete'), 'for_good': ('Delete for good (asks first)', 'Shift+Delete'),
        'open': ('Open', 'Enter'), 'properties': ('Properties', 'Alt+Enter'), 'read_again': ('Read again', 'F5'),
        'back': ('Back', 'Backspace'), 'all': ('Choose all', 'Ctrl+A'), 'undo': ('Undo', 'Ctrl+Z')}


def chosen(host):
    """[(path, 'file'|'folder')] the Files tree has chosen (its rows of files and folders), in the tree's order."""
    page = getattr(host, 'cabinet_page', None)
    if page is None:return []
    from .home_files_qt import path_of_row
    try:items = page.tree.selectedItems() or ([page.tree.currentItem()] if page.tree.currentItem() is not None else [])
    except RuntimeError:
        return []
    order = {id(item): n for n, item in enumerate(page.items.values())}
    out = []
    for item in sorted(items, key=lambda i: order.get(id(i), 0)):
        node = item.data(0, Qt.UserRole) or {}
        path = path_of_row(node.get('id')) if node.get('role') in ('file', 'folder') else ''
        if path:out.append((path, node.get('role')))
    return out


def current(host):
    """(path, role) of the tree's current row, or ('', '')."""
    page = getattr(host, 'cabinet_page', None)
    if page is None:return '', ''
    from .home_files_qt import path_of_row
    item = page.tree.currentItem()
    node = (item.data(0, Qt.UserRole) or {}) if item is not None else {}
    path = path_of_row(node.get('id')) if node.get('role') in ('file', 'folder') else ''
    return (path, node.get('role')) if path else ('', '')


def folder_in_front(host):
    """The folder a paste goes into: the current row when it is a folder, else the folder that holds it."""
    path, role = current(host)
    if not path:return ''
    return path if role == 'folder' else str(Path(path).parent)


class TreeKeys(QObject):
    """The Files tree's Windows keys (an event filter: the tree takes them before the window's own actions)."""

    def __init__(self, host, tree):
        super().__init__(tree)
        self.host = host;self.tree = tree;self.clipboard = wh.FileClipboard();self.last = ''
        tree.installEventFilter(self)

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind not in (QEvent.ShortcutOverride, QEvent.KeyPress):return False
        try:what = KEYS.get((event.key(), event.modifiers()))
        except RuntimeError:
            return False
        if what is None:return False
        if what == 'open' and current(self.host)[1] != 'file':return False      # a folder or a record: the tree's own Enter
        if kind == QEvent.ShortcutOverride:event.accept();return True
        self.last = what
        try:self.do(what)
        except ValueError as exc:
            say(self.host, 'Not done: %s' % str(exc).split(': ', 1)[-1])
        return True

    def do(self, what):
        host = self.host
        from . import bulk_files_qt as bq
        from . import home_files_qt as hq
        rows = chosen(host);paths = [p for p, _ in rows]
        if what in ('copy', 'cut'):
            if not paths:return say(host, 'Choose a file or folder first.')
            return say(host, self.clipboard.hold(paths, 'copy' if what == 'copy' else 'move'))
        if what == 'paste':
            folder = folder_in_front(host)
            if not self.clipboard.paths:return say(host, 'Nothing is held to paste: copy or cut a file first.')
            if not folder:return say(host, 'Choose the folder to paste into.')
            args = self.clipboard.batch_args(folder)
            return bq.batch(host, args['act'], args['paths'], to=args['to'], said=self.clipboard.pasted)
        if what == 'rename':
            path, _ = current(host)
            return hq.rename(host, path) if path else say(host, 'Choose a file or folder to rename.')
        if what == 'delete':
            if not paths:return None
            return hq.delete(host, paths[0]) if len(paths) == 1 else bq.batch(host, 'delete', paths)
        if what == 'for_good':return for_good(host, paths)
        if what == 'open':return hq.open_in(host, current(host)[0])
        if what == 'properties':
            path, _ = current(host)
            return show_properties(host, path) if path else None
        if what == 'read_again':
            page = getattr(host, 'cabinet_page', None)
            if page is not None:page.refresh(force=True)
            return say(host, 'Read again.')
        if what == 'back':
            living = getattr(host, 'living_nav', None)
            return living.back() if living is not None else None
        if what == 'all':self.tree.selectAll();return None
        if what == 'undo':
            note = getattr(getattr(host, 'home_files', None), 'note', None)
            if note is not None and getattr(note, 'undo', None) is not None:return note.undo_now()
            return say(host, 'Nothing to take back here.')
        return None


def for_good(host, paths, ask=None):
    """Shift+Delete: asks first, in words; then files.delete_for_good for each (your press). `ask` is for tests."""
    paths = [str(p) for p in paths]
    if not paths:return None
    from .bulk_files import counted
    names = ', '.join(Path(p).name for p in paths[:3]) + (' and %d more' % (len(paths) - 3) if len(paths) > 3 else '')
    question = 'Delete %s for good? %s will not go to the bin, and cannot be put back.' % (counted(paths), names)
    if ask is None:
        box = QMessageBox(QMessageBox.Warning, 'Delete for good', question, QMessageBox.NoButton, host)
        yes = box.addButton('Delete for good', QMessageBox.DestructiveRole);no = box.addButton('Keep them', QMessageBox.RejectRole)
        box.setDefaultButton(no);box.setEscapeButton(no);box.exec()
        agreed = box.clickedButton() is yes
    else:agreed = bool(ask(question))
    if not agreed:return say(host, 'Nothing was deleted.')
    kernel = kernel_of(host)
    if kernel is None:return say(host, 'Graphite\'s Kernel is not open; nothing was deleted.')
    from .engineering_kernel import operator
    gone, left = [], []
    for p in paths:
        answer = kernel.dispatch('files.delete_for_good', {'path': p}, operator())
        (gone if answer.get('ok') else left).append((p, answer))
    page = getattr(host, 'cabinet_page', None)
    if page is not None:
        try:page.refresh(force=True)
        except RuntimeError:pass
    words = 'Deleted for good: %s.' % (counted([p for p, _ in gone]) if gone else 'nothing')
    if left:words += ' Not deleted: %s.' % '; '.join('%s (%s)' % (Path(p).name, str((a.get('error') or {}).get('message', '')).split(': ', 1)[-1]) for p, a in left[:3])
    return say(host, words)


# ---- Properties --------------------------------------------------------------------------------------------------------------------
class PropertiesPage(QDialog):
    """Alt+Enter: a small page of what the file is. Esc or Close closes it."""

    def __init__(self, host, path, query=None):
        super().__init__(host)
        self.setWindowTitle('Properties · %s' % Path(path).name);self.setObjectName('GraphiteProperties')
        layout = QVBoxLayout(self);form = QFormLayout();layout.addLayout(form)
        self.rows = wh.properties(path, query)
        for label, words in self.rows:
            value = QLabel(words);value.setWordWrap(True);value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            form.addRow(label, value)
        buttons = QDialogButtonBox(QDialogButtonBox.Close);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
        self.setMinimumWidth(420);self.adjustSize()      # as tall as its rows, no more


def show_properties(host, path, query=None):
    try:page = PropertiesPage(host, path, query)
    except OSError as exc:
        return say(host, 'No properties: %s' % (exc.strerror or exc))
    page.show();page.raise_();host._properties_page = page
    return page


# ---- the screen's picture ----------------------------------------------------------------------------------------------------------
def screenshot(host, folder=None, now=None):
    """PrintScreen: a picture of the whole screen into ~/Pictures/Screenshots, and says so. The path, or '' when not saved."""
    folder = Path(folder) if folder else Path.home() / 'Pictures' / 'Screenshots'
    stamp = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime(now))
    try:folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        say(host, 'No picture of the screen: %s' % (exc.strerror or exc));return ''
    target = folder / ('Screenshot %s.png' % stamp);n = 2
    while target.exists():target = folder / ('Screenshot %s (%d).png' % (stamp, n));n += 1
    screen = QGuiApplication.primaryScreen()
    picture = screen.grabWindow(0) if screen is not None else None
    if picture is None or picture.isNull() or not picture.save(str(target), 'PNG'):
        say(host, 'No picture of the screen: this screen gave none.');return ''
    from . import home_reach as hr
    say(host, 'Saved a picture of the screen: %s' % hr.tilde(target), 12000)
    return str(target)


# ---- the keys from any app: graphite-do's door ------------------------------------------------------------------------------------
def bring(host):
    try:
        if host.isMinimized():host.showNormal()
        host.show();host.raise_();host.activateWindow()
    except RuntimeError:
        pass


def act(host, verb):
    """What one of graphite-do's words does in the window: {ok, words}."""
    if verb not in VERBS:return {'ok': False, 'words': 'graphite-do knows: %s' % ', '.join(VERBS)}
    if verb == 'ping':return {'ok': True, 'words': 'Graphite is here.'}
    if verb == 'screenshot':
        made = screenshot(host)
        return {'ok': bool(made), 'words': ('Saved %s' % made) if made else 'No picture was saved.', 'path': made}
    bring(host)
    if verb == 'show':return {'ok': True, 'words': 'Graphite is in front.'}
    if verb == 'apps':
        top = getattr(getattr(host, 'shell2', None), 'top', None)
        if top is None or getattr(top, 'programs', None) is None:return {'ok': False, 'words': 'Apps is not on this window.'}
        top.programs.click();return {'ok': True, 'words': 'Apps is open.'}
    if verb == 'files':
        from .desk_doers import run
        out = run(host, 'go.files', {}, door='owner')
        return {'ok': bool(out.get('ok')), 'words': out.get('words') or str((out.get('error') or {}).get('words') or '')}
    if verb == 'tasks':
        top = getattr(getattr(host, 'shell2', None), 'top', None);pulse = getattr(top, 'pulse', None)
        if pulse is None:return {'ok': False, 'words': 'The page of what runs is not on this window.'}
        pulse.open_card('CPU');return {'ok': True, 'words': 'What runs is shown.'}
    if verb == 'lock':
        from .session_power import run_lock
        result = run_lock(host)
        return {'ok': bool(result.get('locked')), 'words': result.get('reason', '')}
    return {'ok': False, 'words': 'not known'}


class Door(QObject):
    """The local socket graphite-do speaks to: one line in (a word of VERBS), one line of JSON out. Only this user's."""

    def __init__(self, host, path=None):
        super().__init__(host)
        from PySide6.QtNetwork import QLocalServer
        self.host = host;self.path = Path(path) if path else socket_path();self.heard = []
        self.server = QLocalServer(self);self.server.setSocketOptions(QLocalServer.UserAccessOption)
        try:
            if self.path.exists():
                if _alive(self.path):self.why = 'another Graphite answers there';self.listening = False;return
                self.path.unlink()
        except OSError:
            pass
        self.listening = self.server.listen(str(self.path))
        self.why = '' if self.listening else self.server.errorString()
        if self.listening:
            try:os.chmod(self.path, 0o600)
            except OSError:pass
        self.server.newConnection.connect(self.arrived)

    def arrived(self):
        while self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            sock.readyRead.connect(lambda s=sock: self.read(s))
            sock.disconnected.connect(sock.deleteLater)

    def read(self, sock):
        if not sock.canReadLine():return
        verb = bytes(sock.readLine()).decode('utf-8', 'replace').strip().lower()[:40]
        self.heard.append(verb)
        try:answer = act(self.host, verb)
        except Exception as exc:  # noqa: BLE001 - the key's answer says why; the window goes on
            answer = {'ok': False, 'words': str(exc)[:200]}
        sock.write((json.dumps(answer) + '\n').encode('utf-8'));sock.flush();sock.disconnectFromServer()

    def close(self):
        self.server.close()
        try:self.path.unlink()
        except OSError:pass


def _alive(path):
    import socket
    probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM);probe.settimeout(0.5)
    try:probe.connect(str(path));return True
    except OSError:
        return False
    finally:
        probe.close()


# ---- Show keys, in menus and tips ------------------------------------------------------------------------------------------------
def apply_show_keys(host, shown=None):
    """Every action of the window shows its key in a menu, or none; the app's default for menus follows."""
    from PySide6.QtCore import QCoreApplication
    shown = wh.show_keys() if shown is None else shown
    QCoreApplication.setAttribute(Qt.AA_DontShowShortcutsInContextMenus, not shown)
    for action in host.findChildren(QAction):
        try:action.setShortcutVisibleInContextMenu(shown)
        except RuntimeError:pass
    return shown


def rules_lines(host, menu):
    """Rules: "Show keys" (a tick) and "DOS words" (on, show me only, off)."""
    line = QAction('Show keys', menu);line.setCheckable(True);line.setChecked(wh.show_keys())
    line.setToolTip('Menus and tips show their keys; untick it and no key is printed')
    line.toggled.connect(lambda on: (wh.write(show_keys=bool(on)), apply_show_keys(host, bool(on)),
                                     say(host, 'Keys are shown in menus and tips.' if on else 'No key is printed in menus and tips.')))
    menu.addAction(line)
    words = QMenu('DOS words', menu);group = QActionGroup(words);group.setExclusive(True)
    for mode in wh.DOS_MODES:
        row = words.addAction(wh.DOS_WORDS[mode]);row.setCheckable(True);row.setChecked(wh.dos_words() == mode);group.addAction(row)
        row.triggered.connect(lambda checked=False, mode=mode: (wh.write(dos_words=mode), say(host, 'DOS words in the Terminal: %s.' % wh.DOS_WORDS[mode])))
    menu.addMenu(words)
    return line, words


# ---- install --------------------------------------------------------------------------------------------------------------------
def install(host):
    """shell2 calls this once the panes stand: the Files tree's keys, graphite-do's door, keys shown in menus."""
    if getattr(host, 'windows_keys', None) is not None:return host.windows_keys
    page = getattr(host, 'cabinet_page', None)
    host.windows_keys = TreeKeys(host, page.tree) if page is not None else None
    if os.environ.get('GRAPHITE_DO', '1') != '0':
        try:
            host.graphite_door = Door(host)
            from PySide6.QtWidgets import QApplication
            QApplication.instance().aboutToQuit.connect(host.graphite_door.close)
        except Exception:  # noqa: BLE001 - no door: the keys inside the window still work
            host.graphite_door = None
    QTimer.singleShot(0, lambda: apply_show_keys(host))
    return host.windows_keys
