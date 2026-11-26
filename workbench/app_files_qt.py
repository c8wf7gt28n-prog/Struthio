"""Programs by window and file, in the window (Graphite 1.0 A1): from a tile or a file, Open in <program>; the program's
window named on the board's tile while it lives; each save recorded with a line in her column; the close said.

    the board's menu    a FILE tile's right-click: Open in <its default program> (or the family's own bridge: Godot's editor
                        on the project, Blender with its scripts not run), Open with… (S2's dialog), Bring <program>'s
                        window forward while it is open (S3's controller, the owner's press), and the existing rooms of its
                        family: KiCad checks for a KiCad project, the Godot room for project.godot (navigation only)
    every other door    Open with and the default program anywhere in the window (apps_qt.open_app: the tree, Search, the
                        viewer) and L4's Full program open a file of Files through the same route (appfile.open), so its
                        window, its saves and its close are seen the same way; a file outside Files opens as S2 always did
    the watch           while a session is open: its files are watched (QFileSystemWatcher, taken up again when a program
                        writes a new file over the old one), and a light glance (GLANCE_MS) compares the files' sizes and
                        times, the window list (S3's reading, no X call when it reads slowly) and the processes. Only when
                        something differs is the Kernel asked to look (appfile.look, off the window's thread): it reads the
                        window list and the bytes itself, records a new revision through L4, and says what changed
    what is said        each change is a line in her column (her fixed words, app_files.WORDS) and in the status line; the
                        board is drawn again so its FILE tile says OPEN IN <PROGRAM>, the revision, <PROGRAM> CLOSED, and what
                        rests on it is marked to recheck (app_files.mark_board, depths.mark_board)

Nothing here decides anything for the owner: a program starts only on a press; nothing in the program is touched (her hand
in other programs is 1.0 K9's); nothing is accepted into Intake; a revision is what the disk holds.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer, Signal

from . import app_files as af

GLANCE_MS = 1200          # the light look while a session is open (files' sizes and times, the window list, the processes)
CALM_MS = 250             # a burst of file events is looked at once


def kernel_of(host):
    return getattr(getattr(host, 'ledger_bridge', None), 'kernel', None)


def call(host, op, args=None):
    from .apps_qt import call as owner_call
    return owner_call(host, op, args)


def shown(name):
    """A file's name in her words: never markup."""
    return str(name).replace('<', '‹').replace('>', '›')


class AppFiles(QObject):
    """The window's watch on files open in other programs (host.app_files)."""
    looked = Signal(object)

    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.sessions = {}            # id -> the session row as the Kernel last gave it
        self.seen = {}                # id -> what the last glance saw: {'files': {abs: state}, 'window': id or '', 'alive': (pids)}
        self.busy = False;self.again = False;self.lines = [];self.nudged = {}
        self.watcher = QFileSystemWatcher(self);self.watcher.fileChanged.connect(self.file_changed)
        self.calm = QTimer(self);self.calm.setSingleShot(True);self.calm.setInterval(CALM_MS);self.calm.timeout.connect(self.look)
        self.timer = QTimer(self);self.timer.setInterval(GLANCE_MS);self.timer.timeout.connect(self.glance)
        self.looked.connect(self.handle)
        QTimer.singleShot(0, self.resume)

    # ---- opening ----------------------------------------------------------------------------------------------------------------
    def in_files(self, path):
        kernel = kernel_of(self.host)
        if kernel is None:return False
        try:
            from .files_service import root
            return Path(path).resolve().is_relative_to(root(kernel).resolve()) and Path(path).is_file()
        except (OSError, ValueError):
            return False

    def open(self, path, app='', chosen=False):
        """appfile.open as the owner: the result (with 'words'), or {'ok': False, 'reason'}."""
        args = {'path': str(Path(path).resolve())}
        if app:args['app'] = str(app)
        if chosen:args['chosen'] = True
        try:result = call(self.host, 'appfile.open', args)
        except ValueError as exc:
            why = str(exc).split(': ', 1)[-1]
            words = af.say('refused', name=shown(Path(path).name), why=why)
            self.say(words, status=True)
            return {'ok': False, 'reason': why, 'words': words}
        self.sessions[result['session']] = {'id': result['session'], 'path': result['path'], 'state': 'starting', 'pids': result.get('pids') or [],
                                            'window': '', 'program': result['program'], 'files': {}}
        self.say(result['words'], status=True)
        self.resume()
        self.redraw()
        return result

    def resume(self):
        """The open sessions as the Kernel keeps them (after a restart too): their files watched, the glance running."""
        try:rows = call(self.host, 'appfile.list', {'open': True}).get('sessions') or []
        except (ValueError, RuntimeError):
            return
        self.sessions = {r['id']: r for r in rows}
        self.watch_all()
        for row in rows:
            self.seen.setdefault(row['id'], self.glimpse(row))
        if rows and not self.timer.isActive():self.timer.start()
        if not rows:self.timer.stop()

    def paths_of(self, row):
        kernel = kernel_of(self.host)
        if kernel is None:return []
        from .files_service import root
        base = root(kernel)
        return [str(base / rel) for rel in sorted(row.get('files') or {})] or [str(base / row['path'])]

    def watch_all(self):
        wanted = set()
        for row in self.sessions.values():wanted.update(self.paths_of(row))
        have = set(self.watcher.files())
        if have - wanted:self.watcher.removePaths(sorted(have - wanted))
        for path in sorted(wanted - have):
            if os.path.isfile(path):self.watcher.addPath(path)

    # ---- the glance: something changed? -----------------------------------------------------------------------------------
    def glimpse(self, row):
        files = {}
        for path in self.paths_of(row):
            try:st = os.stat(path);files[path] = (st.st_size, st.st_mtime_ns, st.st_ino)
            except OSError:files[path] = None
        window = ''
        reading = self.window_reading(row)
        if reading is not None:
            found, _ = af.match_window(row, reading)
            window = found['id'] if found is not None else ''
        from .session_launch import start_time
        alive = tuple(p for p in row.get('pids') or () if start_time(p) is not None)
        return {'files': files, 'window': window, 'alive': alive, 'listed': reading is not None}

    def window_reading(self, row):
        try:
            from . import windows_x11
            watcher = windows_x11.shared()
            if not watcher.start():return None
            slow = getattr(watcher.backend, 'blocking', False)
            if not slow:watcher.refresh()        # a few round trips through libX11: fine on the window's thread
            seq = row.get('seq')
            look = watcher.observe(seq if isinstance(seq, int) and seq >= 0 else None, fresh=False)
            return look if look.get('available') else None
        except Exception:  # noqa: BLE001 - no window list: the processes are glanced at
            return None

    def glance(self):
        if not self.sessions:
            self.timer.stop();return
        changed = False
        for ident, row in list(self.sessions.items()):
            now = self.glimpse(row);was = self.seen.get(ident)
            if was is None or now != was:changed = True
            elif self.differs(row, now):
                key = (row.get('state'), row.get('window'), now['window'], now['alive'], now['listed'])
                if self.nudged.get(ident) != key:      # the same disagreement is asked about once, never in a loop
                    self.nudged[ident] = key;changed = True
            self.seen[ident] = now
        if changed:self.look()

    def differs(self, row, now):
        """What the glance sees and what the Kernel last recorded disagree (a window it has not named yet, one it named that is
        gone, a process that ended); a program still looked for past the Kernel's patience is asked about once more."""
        state = row.get('state')
        if now['listed']:
            if now['window'] and (state != 'open' or row.get('window') != now['window']):return True
            if not now['window'] and state == 'open' and row.get('window'):return True
        else:
            if now['alive'] and state == 'starting':return True
            if not now['alive'] and state != 'closed':return True
        if state == 'starting' and not now['alive'] and time.time_ns() - int(row.get('started_ns') or 0) > af.FIND_LONGEST_NS:return True
        return False

    def file_changed(self, path):
        if path not in self.watcher.files() and os.path.isfile(path):self.watcher.addPath(path)
        self.calm.start()

    # ---- the Kernel's look, off the window's thread -------------------------------------------------------------------------
    def look(self):
        if self.busy:
            self.again = True;return
        kernel = kernel_of(self.host)
        if kernel is None:return
        self.busy = True

        def work():
            from .engineering_kernel import operator
            try:
                answer = kernel.dispatch('appfile.look', {}, operator())
                result = answer.get('result') if answer.get('ok') else {'events': [], 'error': (answer.get('error') or {}).get('message')}
            except Exception as exc:  # noqa: BLE001 - said, never taking the window down
                result = {'events': [], 'error': str(exc)}
            self.looked.emit(result)
        threading.Thread(target=work, name='appfile-look', daemon=True).start()

    def handle(self, result):
        self.busy = False
        try:
            if result.get('sessions') is not None:
                self.sessions = {r['id']: r for r in result['sessions']}
                for ident in list(self.seen):
                    if ident not in self.sessions:self.seen.pop(ident, None)
                for row in self.sessions.values():self.seen[row['id']] = self.glimpse(row)
            self.watch_all()
            events = result.get('events') or []
            for event in events:self.say(event['words'], status=True)
            if events:
                if any(e['event'] == 'saved' for e in events):
                    nav = getattr(self.host, 'living_nav', None)
                    if nav is not None:QTimer.singleShot(0, nav.read_again)      # the tree reads Files again: the same object, its new bytes
                self.redraw()
            if not self.sessions:self.timer.stop()
            elif not self.timer.isActive():self.timer.start()
        except RuntimeError:      # the window is closing
            return
        if self.again:
            self.again = False;QTimer.singleShot(0, self.look)

    # ---- what is said and shown -----------------------------------------------------------------------------------------------
    def say(self, words, status=False):
        """A line in her column (her fixed words), kept; and in the status line."""
        self.lines.append((time.strftime('%H:%M'), words));del self.lines[:-40]
        try:
            face = getattr(getattr(self.host, 'shell2', None), 'face', None)
            if face is not None and hasattr(face, 'say'):
                from .her_column_qt import plain
                face.say(plain(words))
        except Exception:  # noqa: BLE001 - the status line still says it
            pass
        if status:
            try:self.host.statusBar().showMessage(words, 12000)
            except (AttributeError, RuntimeError):pass

    def redraw(self):
        """The board drawn again from a new reading of the desk (its FILE tiles' words come from appfile.list)."""
        page = getattr(self.host, 'field_page', None);board = getattr(page, 'board', None)
        if board is None:return
        try:
            board._desk_key = None;board._stale = True
            if board.isVisible():board.rebuild()
        except RuntimeError:
            pass

    def session_of(self, path):
        """The open session of a file (by its path in Files), or None."""
        kernel = kernel_of(self.host)
        if kernel is None:return None
        try:
            from .files_service import root
            rel = Path(path).resolve().relative_to(root(kernel).resolve()).as_posix()
        except (OSError, ValueError):
            return None
        return next((r for r in self.sessions.values() if r.get('path') == rel and r.get('state') != 'closed'), None)


# ---- the doors ---------------------------------------------------------------------------------------------------------------
def watch_of(host):
    return getattr(host, 'app_files', None)


def open_with(host, ident, files):
    """apps_qt.open_app, first: one file of Files opened with a chosen app goes through appfile.open (its window, saves and
    close seen). Returns the words said, or None for S2's own route (several files, or one outside Files)."""
    watch = watch_of(host)
    files = [str(f) for f in files or ()]
    if watch is None or len(files) != 1 or not watch.in_files(files[0]):return None
    return watch.open(files[0], app=ident, chosen=True).get('words')


def open_for_view(host, app_id, path):
    """L4's Full program for a file of Files: appfile.open with its default program (a family's bridge may stand in for a
    default that is not of the family). The result in apps.open's shape, or None for S2's own route."""
    watch = watch_of(host)
    if watch is None or not watch.in_files(path):return None
    result = watch.open(path, app=app_id or '', chosen=False)
    if not result.get('ok'):raise ValueError(result.get('reason') or 'It did not start.')
    return result


def program_words(host, path):
    """(the words for Open in …, the program's name or '') for a file: the route appfile.open would take."""
    try:
        route, app, program, name, reason = af.choose(Path(path))
    except Exception:  # noqa: BLE001 - the catalogue could not be read
        return 'Open in its program', ''
    if not route:return 'Open in its program…', ''
    return 'Open in %s' % name, name


def add_menu(host, tile, menu):
    """board_qt.BoardView.tile_menu: a FILE tile's Open in <program>, Open with…, Bring its window forward, its family's room."""
    obj = getattr(tile, 'obj', None);target = getattr(obj, 'target', None)
    if not isinstance(target, dict) or target.get('kind') != 'file' or not target.get('path') or getattr(obj, 'kind', '') == 'folder':return
    path = str(target['path'])
    if not os.path.isfile(path):return
    watch = watch_of(host)
    menu.addSeparator()
    words, name = program_words(host, path)
    if name and watch is not None:
        menu.addAction(words, lambda p=path: watch.open(p))
    else:
        menu.addAction(words, lambda p=path: _open_with_dialog(host, p))
    menu.addAction('Open with…', lambda p=path: _open_with_dialog(host, p))
    row = watch.session_of(path) if watch is not None else None
    if row is not None and row.get('window'):
        menu.addAction('Bring %s’s window forward' % row.get('program', 'its'), lambda r=row: _forward(host, r))
    program = af.family(path)
    if program is not None and program.key in ('kicad', 'godot'):
        try:
            from .context_menu import adapter_entries
            from .files_service import root
            relative = Path(path).resolve().relative_to(root(kernel_of(host)).resolve()).as_posix()
            for entry in adapter_entries(host, Path(path).name, relative):
                if entry.key.startswith('adapter:') and entry.run is not None:
                    menu.addAction('Open the Godot room' if entry.key == 'adapter:godot' else entry.label, entry.run)
        except Exception:  # noqa: BLE001 - the rooms stay reachable from Explore
            pass


def _open_with_dialog(host, path):
    from .apps_qt import OpenWithDialog, kind_of, say
    found = kind_of(host, path)
    if 'error' in found:return say(host, found['error'])
    dialog = OpenWithDialog(host, path, found);dialog.open();return dialog


def _forward(host, row):
    """Bring the program's window forward: S3's controller through the Kernel (windows.activate), the owner's press."""
    try:
        answer = call(host, 'windows.activate', {'window': row['window']})
        words = '%s’s window: %s.' % (row.get('program', 'Its program'), answer.get('status_words') or ('in front' if answer.get('verified') else 'asked'))
    except ValueError as exc:
        words = str(exc)
    try:host.statusBar().showMessage(words, 8000)
    except (AttributeError, RuntimeError):pass


def install(host):
    if getattr(host, 'app_files', None) is not None:return host.app_files
    host.app_files = AppFiles(host)
    return host.app_files
