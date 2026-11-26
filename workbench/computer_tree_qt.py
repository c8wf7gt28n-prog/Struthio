"""The whole computer in the Files tree (Graphite 1.0 L6).

The owner, 26 November 2026: "Shouldn't the files part of the left tree start at root /?" The Files tab's tree (the cabinet
tree, cabinet_qt, with L1's rows by identity, living_nav_qt) now starts at the computer:

    This computer /             the top row: the folder /, so every folder the owner's account can read is reachable
      Home                      the owner's home folder: open at start, and where the tree lands (selected)
        …                       its folders and files, listed when a folder is opened, one level at a time; never deeper
        workspace  (the mark)   Graphite's workspace where it lives in Home, marked with Graphite's glyph; its Files
                                folder keeps its own rules (her own area, Slate); its records are the Desk drawer below
      Drives                    near the top, under Home: the removable drives (S4, udisks2): each drive, its volumes;
                                a mounted one is a folder like any other, an unmounted one opens Storage in the centre
      bin, boot, etc, …         the other folders of /, collapsed
      dev · system, …           the pseudo-filesystems /proc, /sys, /dev and /run: shown as such, never read (never
                                opened, never on the board, never given an id)
    Concern …  Desk             the cabinet, and the Desk drawer of records as L1 built it

Dot-names are left out unless the owner turns on "Show hidden" in the tab's header. Nothing here scans the disk: a
folder is read when it is opened (and while it stays open, each time the tree is read), one level, at most
home_reach.MOST_ROWS rows. A row's identity is its path until it is focused, opened or linked: then it is given L1's
stable id (objects.get with its path, lazily), and the board can focus it like any file of Files (a FILE or FOLDER tile).
A row of the workspace's Files carries the id L1's reading of Files gave it.

The owner's own actions anywhere follow the system's permissions; her changes reach only inside Home (home_reach, the
Files rules and K3's grants enforce it in the Kernel's path, not here).
"""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QWidget

from . import boss_theme as bt
from . import home_reach as hr

COMPUTER = 'living:computer'
DRIVES = 'living:drives'
FS = 'living:fs:'                 # FS + branch + ':' + path: a folder or file row (branch: home, root, drive)
NOTE = 'living:fs-note:'          # a row that only says something (more not listed, not readable, no drive)
WAIT = 'living:fs-wait:'          # the row under a folder not read yet, so it can be opened
DRIVE = 'living:drive:'
JUMP = 'living:fs-home:'          # the owner's own folder seen under /home: a way to Home
PATH = 'path:'                    # a row's identity until it is given an id
DRIVE_SECONDS = 10                # the drives are read again at most this often (the Machine tab shares the reading)
KEY = 'computer_tree'             # the session's key: which folders are read (open), Show hidden


def mine(node_id):
    return str(node_id).startswith((COMPUTER, DRIVES, FS, NOTE, WAIT, DRIVE, JUMP))


class ComputerTree(QObject):
    """The rows of the computer for the cabinet's model, read lazily; the start on Home; Show hidden; the way to a path."""

    def __init__(self, living):
        super().__init__(living)
        self.living = living;self.host = living.host
        self.home = hr.home();self.home_id = FS + 'home:' + str(self.home)
        page = self.page()
        try:saved = dict(self.host.session.state.get(KEY) or {})
        except Exception:  # noqa: BLE001 - no session: nothing remembered
            saved = {}
        self.listed = set(saved.get('listed') or ()) | {COMPUTER, self.home_id}
        self.hidden = bool(saved.get('hidden'));self.landed = False
        self.paths = {}               # row id -> its path
        self.drives = None;self.drives_at = 0.0
        self.switch = None
        if page is not None:
            page.tree.itemExpanded.connect(self.expanded);page.tree.itemCollapsed.connect(self.collapsed)
            self.add_switch(page)
        QTimer.singleShot(0, self.land)

    def page(self):
        return getattr(self.host, 'cabinet_page', None)

    # ---- the tab's header: Show hidden -------------------------------------------------------------------------------------
    def add_switch(self, page):
        holder = page.stack.widget(0) if page.stack.count() else None
        layout = holder.layout() if holder is not None else None
        if layout is None:return
        row = QWidget(holder);row.setObjectName('ComputerTreeHeader');row.setAccessibleName('The Files tab: what it shows')
        box = QHBoxLayout(row);box.setContentsMargins(2, 0, 2, 2);box.setSpacing(6);box.addStretch(1)
        self.switch = QCheckBox('Show hidden', row);self.switch.setObjectName('ComputerShowHidden')
        self.switch.setAccessibleName('Show hidden files and folders (names that start with a dot)')
        self.switch.setToolTip('Files and folders whose names start with a dot are hidden; tick to show them in the tree')
        self.switch.setChecked(self.hidden);self.switch.setCursor(Qt.PointingHandCursor);self.switch.toggled.connect(self.show_hidden)
        box.addWidget(self.switch);layout.insertWidget(0, row);self.restyle()

    def restyle(self):
        if self.switch is None:return
        from .living_nav_qt import scale_of
        px = max(12, round(13 * scale_of(self.host)))
        self.switch.setStyleSheet('QCheckBox#ComputerShowHidden {font-family:"%s";font-size:%dpx;color:%s;background:transparent;spacing:6px;}' % (bt.FACE, px, bt.QUIET))

    def show_hidden(self, on):
        self.hidden = bool(on);self.remember()
        page = self.page()
        if page is not None:page.refresh(force=True)

    def remember(self):
        try:
            self.host.session.state[KEY] = {'listed': sorted(self.listed)[:400], 'hidden': self.hidden};self.host.session.save()
        except Exception:  # noqa: BLE001 - what is open is remembered when it can be
            pass

    # ---- the start: Home open and selected --------------------------------------------------------------------------------
    def land(self):
        page = self.page()
        if self.landed or page is None or getattr(self.host, '_closing', False):return
        self.landed = True
        self.listed |= {COMPUTER, self.home_id}
        self.keep_open([COMPUTER, self.home_id, DRIVES])      # Drives open too: a drive stands as its own row
        page.refresh(force=True)
        if page.using_legacy:return
        page.select(self.home_id, reveal=True)
        page.tree.scrollToTop()

    def keep_open(self, ids):
        """These rows stay open through the cabinet's own reading (its saved expanded list wins over the items)."""
        page = self.page()
        if page is None:return
        saved = dict(page.saved or {});expanded = list(saved.get('expanded') or [])
        for ident in ids:
            if ident not in expanded:expanded.append(ident)
        saved['expanded'] = expanded;page.saved = saved

    # ---- opening and closing a folder in the tree -------------------------------------------------------------------------
    def expanded(self, item):
        try:node = item.data(0, Qt.UserRole) or {}
        except RuntimeError:
            return
        ident = str(node.get('id', ''))
        if not ident.startswith((COMPUTER, DRIVES, FS)) or ident in self.listed or node.get('role') == 'file':return
        self.listed.add(ident);self.remember()
        QTimer.singleShot(0, lambda: self.page() is not None and self.page().refresh(force=True))

    def collapsed(self, item):
        try:node = item.data(0, Qt.UserRole) or {}
        except RuntimeError:
            return
        ident = str(node.get('id', ''))
        if ident.startswith(FS) and ident in self.listed and ident != self.home_id:
            self.listed.discard(ident);self.remember()

    # ---- the rows ---------------------------------------------------------------------------------------------------------
    def nodes(self):
        """The rows for the cabinet's model, in order: This computer, Home and what is open under it, Drives, the folders of /."""
        out = [];self.paths = {}
        workspace = self.workspace()
        known = dict(self.living.files_by_abs or {})
        kernel = self.kernel()
        if kernel is not None:
            from . import living_nav
            from . import read_beside      # 1.0 F2b: read beside her writes
            known.update(read_beside.first(living_nav.known_outside, kernel))
        for entry in (getattr(self.living, 'extra', None) or {}).values():
            path = self.whole(entry)
            if path:known.setdefault(path, entry['id'])
        self.known = known

        def add(ident, parent, role, label, canonical, description='', **extra):
            out.append(dict(id=ident, parent=parent, role=role, label=label, target={'kind': 'living', 'id': canonical}, scope='owner_private',
                            provider='living_nav', canonical_id=canonical, owning=False, description=description, **extra))

        add(COMPUTER, None, 'drawer', 'This computer /', COMPUTER, 'This computer, from its top folder /: every folder your account can read')
        if COMPUTER in self.listed:
            self.folder_row(add, 'home', self.home, COMPUTER, 'Home', workspace, home=True)
            self.drive_nodes(add, workspace)      # near the top: right under Home, above the folders of /
            self.children(add, 'root', Path('/'), COMPUTER, workspace, skip={str(self.home)})
        else:
            add(WAIT + COMPUTER, COMPUTER, 'note', '…', WAIT + COMPUTER, 'Open it to list what is in it')
        return out

    def kernel(self):
        return getattr(getattr(self.host, 'ledger_bridge', None), 'kernel', None)

    def workspace(self):
        """The folder Graphite's workspace keeps its Files in (marked with Graphite's glyph where it is in the tree)."""
        files = getattr(self.living, 'files', None) or {}
        root = files.get('root')
        return str(Path(root).parent) if root else ''

    def whole(self, entry):
        path = str(entry.get('path') or '')
        if path.startswith('/'):return path
        root = (getattr(self.living, 'files', None) or {}).get('root')
        return str(Path(root) / path) if root and path else (str(root) if root else '')

    def canonical(self, path):
        return self.known.get(str(path)) or PATH + str(path)

    def folder_row(self, add, branch, path, parent, label, workspace, home=False):
        ident = FS + branch + ':' + str(path);self.paths[ident] = str(path)
        if home:
            words = 'Home, your own folder (%s): every folder and file in it, as your account sees them' % str(path)
        elif str(path) == workspace:
            words = "Graphite's workspace (%s): its Files folder and its records; the records are also in the Desk drawer" % hr.tilde(path)
        else:
            words = 'Folder · %s' % hr.tilde(path)
        extra = {'glyph': 'graphite'} if str(path) == workspace else {}
        add(ident, parent, 'folder', label, self.canonical(path), words, **extra)
        if ident in self.listed:self.children(add, branch, Path(path), ident, workspace)
        else:add(WAIT + ident, ident, 'note', '…', WAIT + ident, 'Open it to list what is in it')
        return ident

    def children(self, add, branch, folder, parent, workspace, skip=()):
        from .living_nav_qt import kind_words
        read = hr.listing(folder, hidden=self.hidden)
        if read['error']:
            add(NOTE + parent, parent, 'note', read['error'], NOTE + parent, '%s: %s' % (hr.tilde(folder), read['error']));return
        if not read['rows']:
            add(NOTE + parent, parent, 'note', 'empty' if not read['hidden'] else 'only hidden names (Show hidden lists them)', NOTE + parent,
                'Nothing in %s%s' % (hr.tilde(folder), ' but names that start with a dot' if read['hidden'] else ''))
        for row in read['rows']:
            path = row['path']
            if path in skip:continue
            if row['kind'] == 'system':
                ident = FS + branch + ':' + path;self.paths[ident] = path
                add(ident, parent, 'system', '%s · system' % row['name'], ident, '%s: %s; Graphite never reads it' % (path, hr.SYSTEM_WORDS))
                continue
            if row['kind'] == 'folder' and branch == 'root' and Path(path) == self.home:
                add(JUMP + path, parent, 'note', '%s · Home' % row['name'], JUMP + path, 'Your home folder: it is Home, at the top of this computer');continue
            if row['kind'] == 'folder':
                label = row['name'] + (' →' if row['link'] else '')
                self.folder_row(add, branch, path, parent, label, workspace)
                continue
            ident = FS + branch + ':' + path;self.paths[ident] = path
            add(ident, parent, 'file', row['name'], self.canonical(path), '%s · %s%s' % (kind_words(row['name']), hr.tilde(path), ' (a link)' if row['link'] else ''))
        if read['left']:
            add(NOTE + 'more:' + parent, parent, 'note', '%d more not listed here' % read['left'], NOTE + 'more:' + parent,
                'This folder holds more than the tree lists; the Finder lists all of it')

    # ---- Drives (S4) ------------------------------------------------------------------------------------------------------
    def storage(self):
        now = time.monotonic()
        if self.drives is None or now - self.drives_at > DRIVE_SECONDS:
            try:
                from . import machine_room_qt
                self.drives = machine_room_qt.reading(self.host, 'storage')
            except Exception as exc:  # noqa: BLE001 - the tree stands without the drives
                self.drives = {'available': False, 'short': 'not available', 'why': str(exc)[:200], 'drives': []}
            self.drives_at = now
        return self.drives

    def drive_nodes(self, add, workspace):
        data = self.storage() or {}
        drives = data.get('drives') or [] if data.get('available') else []
        add(DRIVES, COMPUTER, 'drawer', 'Drives', DRIVES, 'The removable drives: USB sticks, cards and discs (udisks2)')
        if not data.get('available'):
            add(NOTE + DRIVES, DRIVES, 'note', str(data.get('short') or 'not available'), NOTE + DRIVES, str(data.get('why') or 'Removable drives are not read here'))
            return
        if not drives:
            add(NOTE + DRIVES, DRIVES, 'note', 'no removable drive', NOTE + DRIVES, 'No removable drive is plugged in')
            return
        for drive in drives:
            mounted = [v for v in drive.get('volumes') or () if v.get('mounted')]
            ident = DRIVE + str(drive['id'])
            add(ident, DRIVES, 'drive', '%s · %s' % (drive['name'], 'mounted' if mounted else 'not mounted'), ident,
                'A removable drive: choose it to open Storage in the centre (Mount, Open in Files, Unmount, Eject safely)')
            for volume in drive.get('volumes') or ():
                name = volume.get('label') or Path(str(volume.get('device') or 'volume')).name
                if volume.get('mounted'):
                    place = volume['mounted'][0]
                    self.folder_row(add, 'drive', Path(place), ident, name, workspace)
                else:
                    add(NOTE + ident + ':' + str(volume.get('id')), ident, 'note', '%s · not mounted' % name, DRIVE + str(drive['id']),
                        'Not mounted: choose it to open Storage in the centre, where Mount is')

    # ---- choosing a row ---------------------------------------------------------------------------------------------------
    def owns(self, node_id):
        return mine(node_id)

    def say(self, words, ms=7000):
        bar = getattr(self.host, 'statusBar', None)
        if callable(bar):self.host.statusBar().showMessage(words, ms)

    def go(self, node_id, via='tree'):
        """A click on one of the computer's rows: a folder or a file is focused on the board (given its id now if it has
        none), a system folder says it is never read, a drive opens Storage, This computer and Drives keep the board."""
        living = self.living;node = living.nodes.get(node_id) or {}
        role = node.get('role');label = node.get('label') or ''
        if role == 'system':
            self.say('%s is %s.' % (self.paths.get(node_id, label), hr.SYSTEM_WORDS));return True
        if node_id.startswith(JUMP):
            page = self.page()
            if page is not None:page.select(self.home_id, reveal=True)
            return living.go_node(self.home_id, via)
        if role == 'drive' or (role == 'note' and str(node.get('canonical_id', '')).startswith(DRIVE)):
            try:
                from . import machine_room_qt
                machine_room_qt.show(self.host, 'storage')
            except Exception as exc:  # noqa: BLE001
                self.say('Storage could not be opened: %s' % str(exc)[:160])
            return True
        if role in ('drawer', 'note'):
            living.go(node.get('canonical_id') or node_id, via, 'board', title=label, node=node_id, board_object=False);return True
        ident = self.identify(node_id)
        if not ident:return True
        living.go(ident, via, 'board', title=label.rstrip(' →'), node=node_id)
        return True

    def open(self, node_id):
        node = self.living.nodes.get(node_id) or {}
        if node.get('role') in ('file', 'folder'):
            ident = self.identify(node_id)
            return self.living.open(ident, node=node_id) if ident else None
        self.go(node_id, 'open');return None

    def identify(self, node_id):
        """The row's stable id, made now when it has none (objects.get with its path): the board and the history hold it."""
        living = self.living;node = living.nodes.get(node_id) or {}
        canonical = str(node.get('canonical_id') or '')
        from . import living_nav as ln
        if ln.is_file_id(canonical) and canonical in (living.files_by_id or {}):return canonical
        path = self.paths.get(node_id) or (canonical[len(PATH):] if canonical.startswith(PATH) else '')
        if not path:return canonical if ln.is_file_id(canonical) else ''
        found = living.call('objects.get', {'path': path})
        if found is None:
            self.say('%s could not be focused: %s' % (hr.tilde(path), living.problem or 'not read'));return ''
        self.hold(found)
        node['canonical_id'] = found['id'];node['target'] = {'kind': 'living', 'id': found['id']}
        living.by_canonical[found['id']] = node_id
        return found['id']

    def hold(self, found):
        """An object found outside Files' reading (elsewhere on this computer, or a name Files' reading leaves out) is held
        beside it, so the board, the breadcrumb and Open find it like any file of Files."""
        from . import living_nav as ln
        living = self.living
        if found['id'] in (living.files_by_id or {}) and not (living.extra or {}).get(found['id']):return
        entry = ln.entry_outside(found)
        if not str(found.get('path') or '').startswith('/'):entry['outside'] = False
        living.extra[found['id']] = entry
        if living.files is not None:living.files = self.merged(dict(living.files, entries=[e for e in living.files['entries'] if not e.get('held')]))
        root = Path((living.files or {}).get('root') or '/')
        living.files_by_id = dict(living.files_by_id or {}, **{found['id']: entry})
        living.files_by_abs = dict(living.files_by_abs or {}, **{self.whole(entry) or str(root / entry['path']): found['id']})

    def merged(self, reading):
        """Files' reading with the objects held beside it (living_nav_qt.read_files)."""
        extra = getattr(self.living, 'extra', None) or {}
        if not extra or not isinstance(reading, dict):return reading
        have = {e['id'] for e in reading.get('entries') or ()}
        added = [dict(e, held=True) for i, e in extra.items() if i not in have]
        return dict(reading, entries=list(reading.get('entries') or ()) + added) if added else reading

    # ---- the way to an object -----------------------------------------------------------------------------------------------
    def open_to(self, ident):
        """The tree is to show this object: every folder on its way is listed and kept open (Home's branch for a path in
        Home, the drive's for a path on a mounted drive, else from /)."""
        living = self.living;entry = (living.files_by_id or {}).get(ident)
        if entry is None:return False
        path = Path(self.whole(entry))
        if not str(path).startswith('/'):return False
        branch, top, first = 'root', Path('/'), [COMPUTER]
        if hr.within(path, self.home):branch, top, first = 'home', self.home, [COMPUTER, self.home_id]
        else:
            for drive in (self.storage() or {}).get('drives') or ():
                for volume in drive.get('volumes') or ():
                    for place in volume.get('mounted') or ():
                        if hr.within(path, Path(place)):branch, top, first = 'drive', Path(place), [COMPUTER, DRIVES, DRIVE + str(drive['id'])]
        opened = list(first)
        folder = path.parent if path != top else None
        chain = []
        while folder is not None and hr.within(folder, top):
            chain.append(FS + branch + ':' + str(folder))
            if folder == top or folder == folder.parent:break
            folder = folder.parent
        if branch == 'root':chain = [c for c in chain if c != FS + 'root:/']
        opened += list(reversed(chain))
        self.listed |= set(o for o in opened if o.startswith((COMPUTER, DRIVES, FS)))
        self.keep_open(opened);self.remember()
        return True


def install(living):
    """LivingNav (living_nav_qt) calls this once: the computer's rows in its tree."""
    tree = ComputerTree(living)
    try:
        from .home_files_qt import install as home_files
        home_files(tree)      # 1.0 L6b: rename, move (drag), new folder and Delete (into DELETE) in your home, with Undo; a focused file watched
    except Exception:  # noqa: BLE001 - the tree stands without them
        pass
    return tree
