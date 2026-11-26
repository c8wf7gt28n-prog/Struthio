"""One navigation state in the window (Graphite 1.0 L1): the tree on the left and the centre share one focus, by identity.

    the tree        the Files tab's tree (the cabinet tree, cabinet_qt) gets two drawers of its own under Concern: Files, the
                    Files folder on this computer with a stable id for every file and folder (living_nav, objects.files), and
                    Desk, the work on this desk as the board shows it (sources, sheets, calculations, pages, findings,
                    questions, goals, …), each row by the record's own id. A row's identity is its object's, never its name:
                    two files of the same name are two rows, and a renamed file is the same row with its new name.
    the centre      the board (until L2's board, the Field of field_page is the board): a click in the tree focuses that
                    object on the board; a plain file is drawn there as a FILE tile (a folder as a FOLDER tile), wired to the
                    admitted source that has the same bytes. A click on a tile focuses it, and the tree reveals it: its
                    folders opened, no other branch closed, the tree's scroll kept (moved only as far as the row needs).
                    Opening (a double click, Enter, Open) is the work depth: the object's working view in a tab.
    Search          a file or a desk object found by Search is focused as a click in the tree is (console_qt.reveal_record).
    the breadcrumb  above the centre: Back and Forward, then where the focus is, its folders and its name (each one a place to
                    go), following a rename as soon as Files is read again (the file watcher reads it within a moment).
    history         living_nav.Navigator: each entry the focus, the depth, the pane, the board's zoom and place, the place in
                    the document and how the owner got there. Back and Forward put an entry back whole: the board seen as it
                    was, or the document's tab with its scroll and cursor where they were.

Nothing here writes a file or a record (the identity index aside, through objects.files). The window's own Back of the
Field (Backspace, its trail) is the Field's and stays as it was.

1.0 L6, the whole computer: the Files drawer gave way to the computer's rows (computer_tree_qt): "This computer /" at the
top, Home open and selected at start (the workspace and its Files are in it, where they live), Drives near the top; the
Desk drawer stays. A row anywhere is focused like a file of Files: it is given its id when it is chosen (lazily), held
beside Files' reading (extra), and the board, the breadcrumb, Back and Open find it.
"""
from __future__ import annotations

import time  # 1.0 D2: the launch's tree kept at its top
import weakref
from pathlib import Path

from PySide6.QtCore import QEvent, QFileSystemWatcher, QObject, QPointF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFontMetrics, QIcon, QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import QAbstractScrollArea, QHBoxLayout, QLabel, QPlainTextEdit, QSizePolicy, QTextEdit, QToolButton, QWidget

from . import boss_theme as bt
from . import living_nav as ln

LIVING = 'living:'
FILES_NODE = 'living:files'
DESK = 'living:desk'
GROUPS = (('source', 'sources', 'Sources'), ('sheet', 'sheets', 'Sheets'), ('calculation', 'calculations', 'Calculations'),
          ('document', 'pages', 'Pages'), ('finding', 'findings', 'Findings'), ('question', 'questions', 'Questions'),
          ('goal', 'goals', 'Goals'), ('rule', 'rules', 'Rule cards'), ('word', 'words', 'Your word'),
          ('condition', 'totals', 'Totals'), ('method', 'methods', 'Methods'), ('job', 'work', 'Work'))
SEPARATOR = ' / '
KIND_WORDS = {'.pdf': 'PDF', '.txt': 'Text', '.md': 'Markdown', '.csv': 'Table', '.tsv': 'Table', '.ods': 'Spreadsheet', '.xlsx': 'Spreadsheet',
              '.odt': 'Document', '.docx': 'Document', '.json': 'JSON', '.png': 'Image', '.jpg': 'Image', '.jpeg': 'Image', '.svg': 'Drawing',
              '.py': 'Code', '.kicad_pcb': 'KiCad board', '.kicad_sch': 'KiCad schematic', '.step': 'STEP model', '.stl': 'STL model', '.zip': 'ZIP archive'}


def size_words(size):
    """A size in words, in whole numbers (no floating point): 812 bytes, 14 KB, 3 MB."""
    size = int(size or 0)
    if size < 1024:return '%d byte%s' % (size, '' if size == 1 else 's')
    if size < 1024 * 1024:return '%d KB' % ((size + 512) // 1024)
    return '%d MB' % ((size + 512 * 1024) // (1024 * 1024))


def kind_words(name, kind='file'):
    if kind == 'folder':return 'Folder'
    return KIND_WORDS.get(Path(name).suffix.lower(), (Path(name).suffix[1:].upper() + ' file') if Path(name).suffix else 'File')


def chevron(left, colour, px):
    """Back and Forward drawn as a shape (a chevron), so they read the same in every look's face."""
    pixmap = QPixmap(px, px);pixmap.fill(Qt.transparent)
    p = QPainter(pixmap);p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(colour), max(1.6, px / 9.0));pen.setCapStyle(Qt.RoundCap);pen.setJoinStyle(Qt.RoundJoin);p.setPen(pen)
    a, b, c = (0.62, 0.38, 0.62) if left else (0.38, 0.62, 0.38)
    path = QPainterPath(QPointF(px * a, px * 0.2));path.lineTo(QPointF(px * b, px * 0.5));path.lineTo(QPointF(px * c, px * 0.8))
    p.drawPath(path);p.end()
    return pixmap


def scale_of(host):
    return float((getattr(host, 'reading_profile', None) or {}).get('ui_pt', 14.0)) / 14.0


def alive(ref):
    try:
        widget = ref() if ref is not None else None
        if widget is not None:widget.objectName()      # a deleted widget raises here
        return widget
    except RuntimeError:
        return None


def scroll_area(widget):
    """The document's own scroller in a tab: the widget itself when it is one, else its largest visible scroll area."""
    if widget is None:return None
    candidates = ([widget] if isinstance(widget, QAbstractScrollArea) else []) + [w for w in widget.findChildren(QAbstractScrollArea) if w.isVisible()]
    if not candidates:return None
    return max(candidates, key=lambda w: (w is widget, w.width() * w.height()))


def doc_position(widget):
    """Where the document is in its tab: its scroll both ways and, in a text, the cursor. A tab may say it itself
    (document_position / set_document_position), as the working views of L4 and L5 can."""
    if widget is None:return {}
    own = getattr(widget, 'document_position', None)
    if callable(own):
        try:return {'own': own()}
        except Exception:  # noqa: BLE001 - a place not read is a place not restored, never an error
            pass
    area = scroll_area(widget)
    if area is None:return {}
    place = {'v': area.verticalScrollBar().value(), 'h': area.horizontalScrollBar().value()}
    if isinstance(area, (QPlainTextEdit, QTextEdit)):place['cursor'] = area.textCursor().position()
    return place


def set_doc_position(widget, place):
    if widget is None or not place:return
    if 'own' in place and callable(getattr(widget, 'set_document_position', None)):
        try:widget.set_document_position(place['own']);return
        except Exception:  # noqa: BLE001
            return
    area = scroll_area(widget)
    if area is None:return
    if 'cursor' in place and isinstance(area, (QPlainTextEdit, QTextEdit)):
        cursor = area.textCursor();cursor.setPosition(min(int(place['cursor']), max(0, area.document().characterCount() - 1)));area.setTextCursor(cursor)
    if 'v' in place:area.verticalScrollBar().setValue(int(place['v']))
    if 'h' in place:area.horizontalScrollBar().setValue(int(place['h']))


class Crumbs(QWidget):
    """The breadcrumb above the centre: Back, Forward, then the focus's folders and its name."""

    def __init__(self, living):
        super().__init__()
        self.living = living;self.host = living.host;self.parts = [];self.note = ''
        self.setObjectName('LivingCrumbs');self.setAccessibleName('Where you are')
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        row = QHBoxLayout(self);row.setContentsMargins(10, 2, 10, 3);row.setSpacing(4)
        self.back = QToolButton(self);self.forward = QToolButton(self)
        for button, name, go in ((self.back, 'Back', living.back), (self.forward, 'Forward', living.forward)):
            button.setAutoRaise(True);button.setAccessibleName(name);button.setFocusPolicy(Qt.TabFocus);button.clicked.connect(go)
            button.setCursor(Qt.PointingHandCursor);button.setStyleSheet('QToolButton {border:0;background:transparent;padding:2px;} QToolButton:hover {background:%s;}' % bt.RAISED)
            row.addWidget(button)
        self.words = QLabel(self);self.words.setObjectName('LivingCrumbWords');self.words.setTextFormat(Qt.RichText)
        self.words.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred);self.words.linkActivated.connect(self.chosen)
        self.words.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        row.addSpacing(6);row.addWidget(self.words, 1)
        self.restyle()

    def restyle(self):
        s = scale_of(self.host);px = max(12, round(15 * s));icon = max(14, round(18 * s))
        self.words.setStyleSheet('QLabel#LivingCrumbWords {font-family:"%s";font-size:%dpx;color:%s;background:transparent;}' % (bt.FACE, px, bt.QUIET))
        for button, left in ((self.back, True), (self.forward, False)):
            pic = QIcon();pic.addPixmap(chevron(left, bt.TEXT, icon), QIcon.Normal);pic.addPixmap(chevron(left, bt.LINE_MID, icon), QIcon.Disabled)
            button.setIcon(pic);button.setIconSize(QSize(icon, icon));button.setFixedSize(icon + 8, icon + 8)
        self.setFixedHeight(max(icon + 8, QFontMetrics(self.words.font()).height()) + 6)
        self.show_parts(self.parts, self.note)

    def paintEvent(self, event):
        p = QPainter(self);p.fillRect(self.rect(), QColor(bt.PANEL))
        p.setPen(QPen(QColor(bt.LINE), 1));p.drawLine(0, self.height() - 1, self.width(), self.height() - 1);p.end()

    def resizeEvent(self, event):
        super().resizeEvent(event);self.show_parts(self.parts, self.note)

    def show_parts(self, parts, note=''):
        """parts: [(label, node id or '')], the last the focus's own name. Long trails lose their middle first ("…")."""
        from html import escape
        self.parts = list(parts);self.note = note
        nav = self.living.nav
        self.back.setEnabled(nav.can_back());self.forward.setEnabled(nav.can_forward())
        for button, entry, word in ((self.back, nav.peek(-1), 'Back to '), (self.forward, nav.peek(1), 'Forward to ')):
            button.setToolTip(word + (entry.title or 'where you were') if entry is not None else ('Nothing to go back to yet' if word == 'Back to ' else 'Nothing further on'))
        if not parts:
            self.words.setText('');self.words.setAccessibleName('Where you are: nothing in focus yet');return
        metrics = QFontMetrics(self.words.font());room = max(80, self.words.width() - 4)
        from PySide6.QtGui import QFont
        bold = QFont(self.words.font());bold.setWeight(QFont.DemiBold);strong = QFontMetrics(bold)      # 1.0 D2: the name is drawn bold
        shown = list(enumerate(parts));tail = ''

        def width(rows):      # 1.0 D2: the name measured in the weight it is drawn in (it was measured regular, so it was clipped)
            words = [label for _, (label, _) in rows]
            if not words:return 0
            named = rows[-1][0] == len(parts) - 1
            head = SEPARATOR.join(words[:-1]) + (SEPARATOR if len(words) > 1 else '')
            return metrics.horizontalAdvance(head) + (strong if named else metrics).horizontalAdvance(words[-1]) + 2
        if len(shown) > 2 and width(shown) > room:      # the first folder and the name stay; the middle gives way first
            for cut in range(2, len(shown)):
                trial = [shown[0], (-1, ('…', ''))] + shown[cut:]
                if width(trial) <= room or cut == len(shown) - 1:shown = trial;break
        if width(shown) > room and len(shown) > 1:      # 1.0 D2: still too long: only the name, behind "… /"
            shown = [(-1, ('…', ''))] + shown[-1:]
        if width(shown) > room:      # 1.0 D2: the name itself, shortened at its end in its own weight, never cut mid-letter
            at, (label, node) = shown[-1]
            lead = width(shown[:-1] + [(-1, ('', ''))]) if len(shown) > 1 else 0
            shown[-1] = (at, ((strong if at == len(parts) - 1 else metrics).elidedText(label, Qt.ElideRight, max(24, room - lead - 2)), node))
        if note:          # what happened to it (renamed from …) has the room the trail leaves, shortened in its middle
            left = room - width(shown) - metrics.horizontalAdvance('  ·  ')
            if left >= metrics.horizontalAdvance('renamed from …'):tail = '  ·  ' + metrics.elidedText(note, Qt.ElideMiddle, left)
        pieces = []
        for at, (label, node) in shown:
            if at == len(parts) - 1:
                pieces.append('<span style="color:%s;font-weight:600">%s</span>' % (bt.TEXT, escape(label)))
            elif at >= 0 and node:
                pieces.append('<a href="crumb:%d" style="color:%s;text-decoration:none">%s</a>' % (at, bt.QUIET, escape(label)))
            else:
                pieces.append('<span style="color:%s">%s</span>' % (bt.FAINT, escape(label)))
        sep = '<span style="color:%s">%s</span>' % (bt.FAINT, escape(SEPARATOR))
        self.words.setText(sep.join(pieces) + ('<span style="color:%s">%s</span>' % (bt.FAINT, escape(tail)) if tail else ''))
        self.words.setAccessibleName('Where you are: ' + SEPARATOR.join(label for label, _ in parts) + tail)

    def text(self):
        """What the breadcrumb says, as plain words (the trail and the note)."""
        return SEPARATOR.join(label for label, _ in self.parts) + (('  ·  ' + self.note) if self.note else '')

    def chosen(self, link):
        try:at = int(str(link).split(':', 1)[1])
        except (IndexError, ValueError):return
        if 0 <= at < len(self.parts) and self.parts[at][1]:self.living.go_node(self.parts[at][1], via='breadcrumb')


class LivingNav(QObject):
    """The window's one navigation state: the Navigator, and the tree, the board and the breadcrumb kept to it."""

    def __init__(self, host):
        super().__init__(host)
        self.host = host;self.nav = ln.Navigator();self.applying = 0;self.user_input = False;self.pending = None
        self.files = None;self.files_by_id = {};self.files_by_abs = {};self.nodes = {};self.by_canonical = {}
        self.desk = None;self.desk_raw = None;self.desk_objects = [];self.note = '';self.hooked = None;self.problem = ''
        self.extra = {};self.computer = None      # 1.0 L6: objects held beside Files' reading; the computer's rows
        self.watcher = QFileSystemWatcher(self);self.watcher.directoryChanged.connect(self.disk_changed)
        self.reread = QTimer(self);self.reread.setSingleShot(True);self.reread.setInterval(150);self.reread.timeout.connect(self.read_again)
        self.syncing = QTimer(self);self.syncing.setSingleShot(True);self.syncing.setInterval(0);self.syncing.timeout.connect(self.sync_from_window)
        self.crumbs = Crumbs(self)
        layout = getattr(host, 'center_layout', None)
        if layout is not None:layout.insertWidget(0, self.crumbs)
        host.central_stack.currentChanged.connect(self.window_changed)
        host.tabs.currentChanged.connect(self.window_changed)
        page = getattr(host, 'cabinet_page', None)
        if page is not None:page.tree.itemActivated.connect(self.tree_activated)
        for keys, go in (('Alt+Left', self.back), ('Alt+Right', self.forward)):
            QShortcut(QKeySequence(keys), host, activated=go)
        self.hook_field()
        from .computer_tree_qt import install as computer
        self.computer = computer(self)      # 1.0 L6: the Files tab from "This computer /", Home open at start

    # ---- the Kernel --------------------------------------------------------------------------------------------------------
    def call(self, op, args=None):
        kernel = getattr(getattr(self.host, 'ledger_bridge', None), 'kernel', None)
        if kernel is None:return None
        from .engineering_kernel import operator
        answer = kernel.dispatch(op, args or {}, operator())
        if not answer.get('ok'):
            self.problem = str((answer.get('error') or {}).get('message') or 'not read');return None
        return answer['result']

    def read_files(self):
        """Files with its ids. A rename seen here moves nothing: the same id, the new name in the tree, the breadcrumb and the
        history; the focus said 'renamed from …' until it moves."""
        before = self.files_by_id;reading = self.call('objects.files')
        if reading is None:return self.files
        if self.computer is not None:reading = self.computer.merged(reading)      # 1.0 L6: what is held beside it
        self.files = reading;root = Path(reading['root'])
        self.files_by_id = {e['id']: e for e in reading['entries']}
        self.files_by_abs = {str(root / e['path']) if e['path'] else str(root): e['id'] for e in reading['entries']}
        moved = False
        for ident, entry in self.files_by_id.items():
            old = before.get(ident)
            if old is not None and old['path'] != entry['path']:
                self.nav.renamed(ident, entry['name']);moved = True
                if ident == self.nav.focus:self.note = 'renamed from ' + old['name'] if old['name'] != entry['name'] else 'moved from ' + (old['path'].rpartition('/')[0] or 'Files')
        if moved:QTimer.singleShot(0, self.after_reading)      # whichever reading saw it (the watcher's or the tree's own): the board and the breadcrumb follow
        folders = {str(root / e['path']) if e['path'] else str(root) for e in reading['entries'] if e['kind'] == 'folder'}
        watched = set(self.watcher.directories())
        if watched - folders:self.watcher.removePaths(sorted(watched - folders))
        if folders - watched:self.watcher.addPaths(sorted(folders - watched))
        return reading

    def disk_changed(self, *_):
        self.reread.start()

    def read_again(self):
        """Files changed on disk (another program, or Graphite): read it again; the tree, the breadcrumb and a FILE tile follow."""
        page = getattr(self.host, 'cabinet_page', None)
        if page is not None and not self.host._closing:page.refresh(force=True)
        else:self.read_files()

    def after_reading(self):
        focus = self.nav.focus
        if ln.is_file_id(focus) and self.on_board():
            view = self.host.field_page.view;obj = view.field.get(focus);entry = self.files_by_id.get(focus)
            if obj is not None and entry is not None and obj.title != entry['name'] and self.desk_raw is not None:
                self.with_applying(lambda: self.show_on_board(focus, again=True))
        self.show_crumbs()

    # ---- the desk's objects ------------------------------------------------------------------------------------------------
    def read_desk(self):
        """The work on this desk as the board shows it: the Field's last reading of its work face, else one reading of it."""
        if self.desk_raw is None:
            kernel = getattr(getattr(self.host, 'ledger_bridge', None), 'kernel', None)
            if kernel is None:return []
            try:
                from .engineering_kernel import operator
                from .field_source import read_field
                self.desk_raw, _ = read_field(kernel, operator(), title='')
            except Exception as exc:  # noqa: BLE001 - the tree still shows Files and the cabinet
                self.problem = str(exc)[:200];return []
        return [obj for obj in self.desk_raw.objects if not ln.is_file_id(obj.id)]

    # ---- the tree ------------------------------------------------------------------------------------------------------------
    def tree_model(self, model):
        """The cabinet's model with the Files and Desk drawers added (cabinet_qt.CabinetPage.refresh calls this)."""
        from .cabinet import caption, digest, natural
        root = model.get('root') or 'cabinet:concern';nodes = list(model.get('nodes') or ());taken = {n['id'] for n in nodes};mine = []

        def add(ident, parent, role, label, canonical, description='', **extra):
            if ident in taken:return
            mine.append(dict(id=ident, parent=parent, role=role, label=caption(label), target={'kind': 'living', 'id': canonical}, scope='owner_private',
                             provider='living_nav', canonical_id=canonical, owning=False, description=description, **extra))
            taken.add(ident)
        self.read_files()
        # 1.0 L6: the Files drawer gave way to the whole computer: "This computer /" first (Home open, the workspace and its
        # Files where they live in it), then Drives; the cabinet and its Desk drawer after them
        first = self.computer.nodes() if self.computer is not None else []
        taken.update(n['id'] for n in first)
        objects = self.read_desk()
        if objects:
            add(DESK, root, 'drawer', 'Desk', DESK, 'The work on this desk, as the board shows it')
            order = {kind: index for index, (kind, _, _) in enumerate(GROUPS)};words = {kind: (key, label) for kind, key, label in GROUPS}
            for obj in sorted(objects, key=lambda o: (order.get(o.kind, len(order)), natural(str(o.title)))):
                key, label = words.get(obj.kind, (obj.kind, str(obj.kind).title()))
                add('living:desk:' + key, DESK, 'folder_view', label, 'living:desk:' + key, 'The %s on this desk' % label.lower())
                add(LIVING + obj.id, 'living:desk:' + key, obj.kind, obj.title, obj.id, ' · '.join(x for x in (obj.role, obj.where) if x))
        model = dict(model, nodes=first + nodes + mine)      # 1.0 L6: the computer's rows first
        model['signature'] = digest([model.get('signature'), [(n['id'], n['label'], n['parent']) for n in first + mine]])
        self.nodes = {n['id']: n for n in model['nodes']}
        self.by_canonical = {}
        for node in model['nodes']:
            known = self.by_canonical.get(node['canonical_id'])
            if known is None or (node['provider'] == 'living_nav' and self.nodes[known]['provider'] != 'living_nav') or (node.get('owning') and not self.nodes[known].get('owning')):
                self.by_canonical[node['canonical_id']] = node['id']
        QTimer.singleShot(0, self.show_crumbs)
        return model

    def node_of(self, ident):
        if not ident:return None
        if ident in self.nodes:return ident
        return self.by_canonical.get(ident)

    def reveal(self, ident, node=None):
        """The tree shows the object: its folders opened, the others left as they are, the scroll kept as far as it can be."""
        page = getattr(self.host, 'cabinet_page', None)
        if page is None or not ident:return False
        row = node if node in self.nodes and self.nodes[node]['canonical_id'] == ident else self.node_of(ident)
        if row is None or row not in page.items:
            if self.computer is not None:self.computer.open_to(ident)      # 1.0 L6: the folders on its way listed and opened
            page.refresh(force=True);row = self.node_of(ident)
        if row is None or row not in page.items:return False
        if page.using_legacy:return False
        page.select(row, reveal=True)
        return True

    def tree_clicked(self, node):
        """A click on a row of the tree. Ours: the focus moves to it (the board shows it). A cabinet record keeps its own way
        (its record opens) and the history notes that the tree took the owner there."""
        if not isinstance(node, dict):return False
        if not str(node.get('id', '')).startswith(LIVING):
            self.pending = ('tree', node.get('id'));return False
        return self.go_node(node['id'], via='tree')

    def tree_activated(self, item, column=0):
        """Enter or a double click on one of our rows: its working view (a file in its editor or viewer, a sheet in its room)."""
        try:node = item.data(0, Qt.UserRole) or {}
        except RuntimeError:return
        if str(node.get('id', '')).startswith(LIVING):self.open_node(node['id'])

    def go_node(self, node_id, via='tree'):
        node = self.nodes.get(node_id)
        if node is None:return False
        if self.computer is not None and self.computer.owns(node_id):return self.computer.go(node_id, via)      # 1.0 L6
        if node.get('provider') != 'living_nav':
            page = getattr(self.host, 'cabinet_page', None)
            if page is None:return False
            self.pending = (via, node_id);page.select(node_id, reveal=True);page.open(node_id);return True
        ident = node['canonical_id']
        if node['role'] in ('drawer', 'folder_view', 'note'):            # Desk and its groups: the board as it is, the tree on them
            self.go(ident, via, 'board', title=node['label'], node=node_id, board_object=False);return True
        self.go(ident, via, 'board', title=node['label'], node=node_id);return True

    def open_node(self, node_id):
        node = self.nodes.get(node_id)
        if node is None:return None
        if self.computer is not None and self.computer.owns(node_id):return self.computer.open(node_id)      # 1.0 L6
        return self.open(node['canonical_id'], node=node_id)

    # ---- the board (the Field, until L2) ---------------------------------------------------------------------------------
    def page(self):
        return getattr(self.host, 'field_page', None)

    def on_board(self):
        return bool(getattr(self.host, '_field_active', False)) and self.page() is not None

    def hook_field(self):
        page = self.page()
        if page is None or self.hooked is page:return
        self.hooked = page;view = page.view;original = view.set_field
        living = self

        def set_field(field, original=original, page=page):
            if page.face == 'work' and field is not None:
                living.desk_raw = field;field = living.with_focus(field)
            original(field)
            focus = living.nav.focus
            if page.face == 'work' and focus and view.field.get(focus) is not None and view.field.selected != focus:
                living.with_applying(lambda: living.select_tile(focus))
        view.set_field = set_field
        view.selection_changed.connect(self.board_selected)
        view.opened.connect(self.board_opened)
        view.installEventFilter(self)
        board = getattr(page, 'board', None)       # 1.0 L2: the board (board_qt) is the centre's home at board depth
        if board is not None:board.focused.connect(self.board_focused)
        if page.face == 'work' and view.field is not None and view.field.objects:self.desk_raw = view.field

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick, QEvent.KeyPress):
            self.user_input = True;QTimer.singleShot(0, self.input_done)
        return False

    def input_done(self):
        self.user_input = False

    def with_focus(self, field):
        """The board's reading with the focused plain file (or folder) drawn on it, when it is not a record of the desk: a FILE
        tile, wired to the admitted source of the same bytes."""
        focus = self.nav.focus;entry = self.files_by_id.get(focus)
        if entry is None or field.get(focus) is not None:return field
        from dataclasses import replace
        from .field_model import FieldLink, FieldObject
        from .field_source import stac_json
        root = Path(self.files['root']) if self.files else None
        folder = entry['path'].rpartition('/')[0]
        if str(entry['path']).startswith('/'):      # 1.0 L6: a file or folder elsewhere on this computer
            from .home_reach import folder_words, role_words, tilde
            folder_like = entry['kind'] == 'folder'
            lines = ('a folder' if folder_like else '%s · %s' % (kind_words(entry['name']), size_words(entry['size'])), folder_words(entry['path']))
            tile = FieldObject(focus, 'folder' if folder_like else 'source', entry['name'], 'a %s %s' % ('folder' if folder_like else 'file', role_words(entry['path'])),
                               '', lines, tilde(entry['path']), {'kind': 'file', 'id': focus, 'path': entry['path']}, 'FOLDER' if folder_like else 'FILE',
                               'objects.get ' + stac_json(id=focus))
            return replace(field, objects=list(field.objects) + [tile], selected=focus)
        if entry['kind'] == 'folder':
            inside = sum(1 for e in self.files_by_id.values() if e['parent'] == entry['id'])
            lines = ('%d thing%s in it' % (inside, '' if inside == 1 else 's'), 'in ' + ('Files/' + folder if folder else 'Files') if entry['path'] else 'on this computer')
            tile = FieldObject(focus, 'folder', entry['name'] if entry['path'] else 'Files', 'a folder in Files', '', lines, 'Files/' + entry['path'],
                               {'kind': 'file', 'id': focus, 'path': str(root / entry['path']) if root else ''}, 'FOLDER', 'objects.get ' + stac_json(id=focus))
            links = []
        else:
            digest = self.digest_of(focus)
            same = [o for o in field.objects if o.kind == 'source' and isinstance(o.target, dict) and digest and o.target.get('sha256') == digest]
            lines = ('%s · %s' % (kind_words(entry['name']), size_words(entry['size'])), 'in ' + ('Files/' + folder if folder else 'Files'),
                     'brought in as a source' if same else 'not brought in')
            tile = FieldObject(focus, 'source', entry['name'], 'a file in Files', '', lines, 'Files/' + entry['path'],
                               {'kind': 'file', 'id': focus, 'path': str(root / entry['path']) if root else ''}, 'FILE', 'objects.get ' + stac_json(id=focus))
            links = [FieldLink(focus, o.id, 'same bytes') for o in same]
        return replace(field, objects=list(field.objects) + [tile], links=list(field.links) + links, selected=focus)

    def digest_of(self, ident):
        found = self.call('objects.get', {'id': ident}) if ln.is_file_id(ident) else None
        return (found or {}).get('digest') if (found or {}).get('digest_kind') == 'sha256' else None

    def select_tile(self, ident):
        page = self.page();view = page.view
        if getattr(page, 'mode', '') == 'board':      # 1.0 L2: the board brings it to the middle (the Field's selection follows)
            return page.board.focus_on(ident)
        if view.field.get(ident) is None:return False
        view.field.select(ident);view._reveal_pending = True;view._describe();view.update()
        return True

    def show_on_board(self, ident, again=False):
        """Bring the board to the front with this object in focus. A plain file or folder is drawn as its tile."""
        from . import field_page
        page = self.page()
        if not self.on_board():
            page = field_page.show_field(self.host);self.hook_field()
        elif page.face != 'work':
            page.show_face('work')
        view = page.view
        if (again or view.field.get(ident) is None) and ident in self.files_by_id and self.desk_raw is not None:
            view.set_field(self.desk_raw)
        if getattr(page, 'board', None) is not None:      # 1.0 L2: the focus is shown on the board, the centre's home
            from . import board_qt
            if not again:return board_qt.to_board(page, ident)
            if page.mode == 'board':return page.board.focus_on(ident, again=True)      # renamed: drawn again, on the board kept in front
        return self.select_tile(ident)

    def board_state(self):
        """How the board is seen: its zoom, the corner of what it shows, its face, and whether the size was the owner's (a
        zoom they set is kept; an automatic one is worked out again for the window it is shown in)."""
        page = self.page()
        if page is None:return None
        view = page.view
        from . import board_qt     # 1.0 L2: the board's own size and place, and which of the two (board, whole desk) was in front
        return dict({'zoom': view.zoom, 'x': view.scroll_x, 'y': view.scroll_y, 'face': page.face, 'auto': bool(view.auto_fit), 'whole': bool(view._fitted)},
                    **board_qt.state(page))

    def set_board(self, board, later=True):
        page = self.page()
        if page is None or not board:return
        from . import board_qt
        board_qt.restore(page, board)      # 1.0 L2
        view = page.view
        if board.get('whole'):
            view.auto_fit = False;view.zoom = view.fit();view._fitted = True
        elif board.get('zoom') and not board.get('auto'):
            view.auto_fit = False;view._fitted = False;view.set_zoom(board['zoom'], said=False)
        if 'x' in board:view.scroll_x = float(board['x']);view.scroll_y = float(board['y']);view._reveal_pending = False;view._layout()
        view.update()
        if later:      # the board is laid out again when it comes to the front (a resize): the place is put back after that
            QTimer.singleShot(0, lambda b=dict(board): self.set_board(b, later=False))

    def board_selected(self, obj):
        if self.applying or not self.user_input or obj is None or obj.id == self.nav.focus:return
        self.go(obj.id, 'board', 'board', title=obj.title, from_board=True)

    def board_focused(self, obj):
        """1.0 L2: a tile chosen on the board (the owner's click or key): the focus is it, the tree reveals it."""
        if self.applying or obj is None or obj.id == self.nav.focus:return
        self.go(obj.id, 'board', 'board', title=obj.title, from_board=True)

    def board_opened(self, obj):
        """The board opened an object's working view (field_page.open_object ran first): that tab is this object."""
        if obj is None:return
        tab = self.host.tabs.currentWidget()
        if tab is not None and not self.on_board():
            tab._living_oid = obj.id;self.pending = ('open', None);self.sync_soon()
            if hasattr(self.host.tabs, 'working'):self.host.tabs.working(tab)  # 1.0 L5: a named working tab, not the Preview

    # ---- the work depth ----------------------------------------------------------------------------------------------------
    def oid_of_tab(self, tab):
        if tab is None:return ''
        known = getattr(tab, '_living_oid', None)
        if known:return known
        from .cabinet_qt import CabinetRecordTab
        if isinstance(tab, CabinetRecordTab) and getattr(tab, 'current', None):
            node = self.nodes.get(tab.current)
            return node['canonical_id'] if node else tab.current
        for name in ('path', 'root_path', 'file_path'):
            value = getattr(tab, name, None)
            if isinstance(value, (str, Path)) and str(value) in self.files_by_abs:return self.files_by_abs[str(value)]
        return ''

    def tab_title(self, tab):
        index = self.host.tabs.indexOf(tab)
        return self.host.tabs.tabText(index).replace('&', '') if index >= 0 else ''

    def open(self, ident, node=None):
        """The object's working view, in a tab (the work depth): a file in the editor or the viewer, a desk object through the
        board's own opener. A folder has no working view of its own: it is focused on the board."""
        from .split_qt import bring_object
        bring_object(self.host, ident)  # 1.0 L5: open in the other pane: that pane comes into focus, and the opener finds the tab there
        entry = self.files_by_id.get(ident)
        if entry is not None:
            if entry['kind'] == 'folder':return self.go(ident, 'open', 'board', title=entry['name'], node=node)
            tab = open_path(self.host, Path(self.files['root']) / entry['path'])
            if tab is not None:
                tab._living_oid = ident;self.pending = ('open', node);self.sync_soon()
                if hasattr(self.host.tabs, 'working'):self.host.tabs.working(tab)  # 1.0 L5
            return tab
        page = self.page()
        obj = page.view.field.get(ident) if page is not None else None
        if obj is None and self.desk_raw is not None:obj = self.desk_raw.get(ident)
        if obj is not None:
            from . import field_page
            tab = field_page.open_object(self.host, obj)
            if tab is not None and hasattr(tab, 'objectName'):
                tab._living_oid = ident;self.pending = ('open', node);self.sync_soon()
                if hasattr(self.host.tabs, 'working') and self.host.tabs.indexOf(tab) >= 0:self.host.tabs.working(tab)  # 1.0 L5
            return tab
        return None

    # ---- following the window --------------------------------------------------------------------------------------------
    def window_changed(self, *_):
        self.hook_field()
        if not self.applying:self.sync_soon()

    def sync_soon(self):
        if not self.applying:self.syncing.start()

    def sync_from_window(self):
        """What the window shows now, as the navigation state: the board and its focus, or a tab (the work depth)."""
        if self.applying or self.host._closing:return
        via, node = self.pending or (None, None);self.pending = None
        if self.on_board():
            view = self.page().view;obj = view.field.get(view.field.selected)
            if getattr(self.page(), 'mode', '') == 'board':obj = self.page().board.focus_obj() or obj      # 1.0 L2: the board's focus
            focus = self.nav.focus
            if self.nav.depth == 'board' and focus and (view.field.get(focus) is None) and self.page().face == 'work' and not ln.is_file_id(focus):
                self.show_crumbs();return                         # a drawer of the tree in focus over the board as it is
            if obj is None:self.show_crumbs();return
            self.go(obj.id, via or ('start' if self.nav.current is None else 'board'), 'board', title=obj.title, node=node, from_board=True)
        elif self.host.central_stack.currentWidget() is getattr(self.host, 'workspace_split', None):
            tab = self.host.tabs.currentWidget()
            if tab is None:return
            split = getattr(self.host, 'split_panel', None)
            from .split_qt import is_on, pane_of  # 1.0 L5: the two panes are depth 'split'; the pane in focus (host.tabs) is the entry's pane
            depth = 'split' if is_on(self.host) or (split is not None and split.isVisible()) else 'work'
            ident = self.oid_of_tab(tab)
            title = (self.nodes.get(self.node_of(ident)) or {}).get('label') if ident else ''
            self.go(ident, via or ('start' if self.nav.current is None else 'tab'), depth, title=title or self.tab_title(tab), node=node, tab=tab, pane=pane_of(self.host))
        else:
            self.show_crumbs()

    # ---- moving ------------------------------------------------------------------------------------------------------------
    def snapshot(self):
        """The current entry as it is being left: the board's zoom and place (as it was last seen, even when a room has just
        been opened over it), and the document's place in its tab."""
        current = self.nav.current
        if current is None:return
        if self.on_board() or (current.depth == 'board' and self.page() is not None):
            state = self.board_state()
            if state:current.board = state
        tab = alive(current.tab)
        if current.depth in ('work', 'split') and tab is not None and self.host.tabs.currentWidget() is tab and not self.on_board():
            current.doc = doc_position(tab)

    def go(self, ident, via, depth='board', title='', node=None, tab=None, from_board=False, board_object=True, pane='main'):
        """A new place in the history, and the window kept to it: the board shows it (unless the board moved first), the tree
        reveals it (unless the tree moved first), and the breadcrumb says where it is."""
        if self.applying:return None
        current = self.nav.current
        same = current is not None and (current.focus, current.depth) == (ident, depth) and (depth == 'board' or alive(current.tab) is tab)
        if not same:
            self.snapshot()
            if current is None or current.focus != ident:self.note = ''
        node = node or self.node_of(ident) or ''
        entry = self.nav.go(ident, via, depth, pane=pane, title=title or self.title_of(ident), node=node, tab=weakref.ref(tab) if tab is not None else None)  # 1.0 L5: pane
        def apply():
            if depth == 'board' and not from_board and board_object:self.show_on_board(ident)
            elif depth == 'board' and not from_board and not board_object and not self.on_board():
                from . import field_page
                field_page.show_field(self.host);self.hook_field()
            if via not in ('tree', 'start'):
                self.reveal(ident, node)      # 1.0 L6: at start the tree lands on Home
                if time.monotonic() < getattr(self.host, 'launch_top_until', 0.0):      # 1.0 D2: the launch's first focus is revealed, the tree kept at "This computer /"
                    tree = getattr(getattr(self.host, 'cabinet_page', None), 'tree', None)
                    if tree is not None:      # after the reveal's own scroll, which Qt makes once the rows are laid out
                        tree.scrollToTop()
                        for ms in (0, 150, 600, 1500):QTimer.singleShot(ms, tree.scrollToTop)
            if depth == 'board' and self.on_board() and not same:entry.board = self.board_state() or entry.board
        self.with_applying(apply)
        self.show_crumbs()
        return entry

    def back(self):
        self.snapshot();entry = self.nav.back()
        if entry is not None:self.restore(entry)
        self.show_crumbs()

    def forward(self):
        self.snapshot();entry = self.nav.forward()
        if entry is not None:self.restore(entry)
        self.show_crumbs()

    def restore(self, entry):
        """Put an entry back whole: the board seen as it was, with its focus, or the document's tab at its place."""
        self.note = ''

        def apply():
            if entry.depth == 'board':
                if entry.focus and (self.files_by_id.get(entry.focus) or self.board_has(entry.focus)):self.show_on_board(entry.focus)
                elif not self.on_board():
                    from . import field_page
                    field_page.show_field(self.host);self.hook_field()
                face = (entry.board or {}).get('face')
                if face and self.page() is not None and self.page().face != face:self.page().show_face(face)
                self.set_board(entry.board)
            else:
                tab = alive(entry.tab)
                from .split_qt import bring_tab
                bring_tab(self.host, tab)  # 1.0 L5: a view in the other pane: that pane comes into focus with it
                if tab is None or self.host.tabs.indexOf(tab) < 0:
                    tab = self.open(entry.focus) if entry.focus else None
                    if tab is not None and hasattr(tab, 'objectName'):entry.tab = weakref.ref(tab)
                    else:tab = None
                if tab is not None:
                    self.host._close_start()
                    if self.on_board():
                        from . import field_page
                        field_page.leave_field(self.host)
                    self.host.tabs.setCurrentWidget(tab)
                    place = dict(entry.doc or {})
                    set_doc_position(tab, place)
                    QTimer.singleShot(0, lambda t=weakref.ref(tab), p=place: set_doc_position(alive(t), p))
                    if self.page() is not None and entry.board:self.set_board(entry.board)       # the board behind, as it was
                elif entry.focus:
                    self.show_on_board(entry.focus)
            self.reveal(entry.focus, entry.node)
        self.with_applying(apply)
        self.syncing.stop();self.pending = None

    def board_has(self, ident):
        page = self.page()
        board = getattr(page, 'board', None)      # 1.0 L2: an object only the board draws (an earlier revision of a calculation)
        return ((page is not None and page.view.field.get(ident) is not None) or (self.desk_raw is not None and self.desk_raw.get(ident) is not None)
                or (board is not None and board.desk is not None and ident in board.desk.objects))

    def with_applying(self, fn):
        self.applying += 1
        try:return fn()
        finally:self.applying -= 1

    # ---- the breadcrumb ----------------------------------------------------------------------------------------------------
    def title_of(self, ident):
        node = self.nodes.get(self.node_of(ident)) if ident else None
        if node is not None:return node['label']
        entry = self.files_by_id.get(ident)
        if entry is not None:return entry['name']
        page = self.page()
        obj = page.view.field.get(ident) if page is not None and ident else None
        board = getattr(page, 'board', None)      # 1.0 L2
        if obj is None and board is not None and board.desk is not None and ident:obj = board.desk.objects.get(ident)
        return obj.title if obj is not None else ''

    def trail(self, entry):
        """[(label, node id)] from the tree's root down to the focus (the root itself left out), or the focus alone."""
        if entry is None:return []
        row = entry.node if entry.node in self.nodes and self.nodes[entry.node]['canonical_id'] == entry.focus else self.node_of(entry.focus)
        if row is None:
            return [(entry.title or self.title_of(entry.focus) or 'This page', '')] if (entry.title or entry.focus) else []
        parts = [];seen = set()
        while row is not None and row in self.nodes and row not in seen:
            seen.add(row);node = self.nodes[row];parts.append((node['label'], row));row = node['parent']
        parts.reverse()
        if len(parts) > 1:parts = parts[1:]          # Concern, the root, is where everything is: not said
        return parts

    def show_crumbs(self):
        try:self.crumbs.show_parts(self.trail(self.nav.current), self.note)
        except RuntimeError:
            pass

    # ---- search ------------------------------------------------------------------------------------------------------------
    def found(self, node_id):
        if str(node_id).startswith(LIVING):return self.go_node(node_id, via='search')
        self.pending = ('search', node_id);return False


def open_path(host, path):
    """A plain file's working view: the editor for a text inside the workspace (its own rule), the viewer for the rest."""
    path = Path(path)
    if not path.is_file():
        host.statusBar().showMessage('%s is not where it was; Files is read again' % path.name, 6000);return None
    root = Path(getattr(host, 'root', '/'))
    try:inside = path.resolve().is_relative_to(root.resolve())
    except (OSError, ValueError):inside = False
    return host.open_document(path) if inside else host.open_in_viewer(path)


def living(host):
    return getattr(host, 'living_nav', None)


def extend(host, model):
    """cabinet_qt: the cabinet's model with the Files and Desk drawers, or the model as it was when anything is amiss."""
    nav = living(host)
    if nav is None or not isinstance(model, dict):return model
    try:return nav.tree_model(model)
    except Exception as exc:  # noqa: BLE001 - the cabinet is drawn as it always was
        nav.problem = str(exc)[:200];return model


def clicked(host, node):
    nav = living(host)
    return bool(nav is not None and nav.tree_clicked(node))


def open_node(host, node_id):
    nav = living(host)
    return nav.open_node(node_id) if nav is not None else None


def found(host, node_id):
    """Search found a row of the tree (console_qt.reveal_record): ours is focused as a click is; a cabinet record keeps its way."""
    nav = living(host)
    return bool(nav is not None and nav.found(node_id))


def open_file(host, target):
    """field_page.open_object for a FILE tile."""
    nav = living(host)
    if nav is not None and target.get('id'):return nav.open(target['id'])
    return open_path(host, target.get('path') or '')


def install(host):
    if getattr(host, 'living_nav', None) is not None:return host.living_nav
    host.living_nav = LivingNav(host)
    QTimer.singleShot(0, host.living_nav.sync_from_window)
    return host.living_nav
