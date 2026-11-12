"""The rooms along the top of the workspace: Home · Office · Files · Slate · Engineering.

Home is its own page. Office and Slate are room tabs: they stay open, are never
replaced by a Preview and do not use one of the five pins. Files holds what you
open (code, the universal viewer, PDFs). Engineering opens the ARC-1 views.
"""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QVBoxLayout, QWidget

ROOMS = (('home', 'Home', 'console', 'show_start', 'What is waiting, and where to start'),
         ('office', 'Office', 'import', 'show_office', 'Receive files, catalog them and read them as staC'),
         ('files', 'Files', 'c', 'show_files', 'The files and tools you have open'),
         ('slate', 'Graphite', 'brain-link', 'show_slate', 'The local brain, staC plans and the instruction matrix'),
         ('engineering', 'Engineering', 'trace', None, 'ARC-1 views: Brain Link, Source, Simulator, Orange Book and tools'))
# Earlier activity names still name the room that now holds them.
ALIASES = {'brain': 'engineering', 'simulator': 'engineering', 'book': 'engineering', 'source': 'files'}
ENGINEERING = (('Brain Link', 'brain_link'), ('Source', 'source'), ('Simulator', 'arcos'), ('Orange Book', 'orange_book'),
               (None, None), ('Engineering jobs', 'engineering'), ('Hardware ledger', 'ledger'), ('KiCad · native checks', 'cad'),
               ('KiBot', 'kibot'), ('SPICE', 'spice'), ('Yosys', 'yosys'), ('Place and route', 'implementation'), ('HDL', 'hdl'))
ENGINEERING_TABS = {'BrainLinkTab', 'CadViewerTab', 'HardwareOverviewTab', 'AssemblyTab', 'OrangeBookTab', 'ManualTab', 'VendorTab',
                    'DatabaseROMTab', 'VirtualConsoleTab', 'NativeGameTab', 'ArcOSTab', 'EngineeringTab', 'RegisterTab', 'HardwareLedgerTab',
                    'HardwareReviewTab', 'HardwareProofTab', 'NorFlashTab', 'BoardViewerTab', 'KicadTab', 'KiBotTab', 'SpiceTab', 'YosysTab',
                    'PnrTab', 'HdlTab', 'DeviceTab', 'DeviceGroupTab', 'WorkshopTab', 'ConsoleTab'}


class RoomButtons(dict):
    """The five room buttons. Looking up an earlier activity name finds its room."""

    def __getitem__(self, key):
        return super().__getitem__(ALIASES.get(key, key))

    def get(self, key, default=None):
        return super().get(ALIASES.get(key, key), default)


def room_for(widget, home_active=False):
    if home_active:return 'home'
    if widget is None:return 'files'
    kind = type(widget).__name__
    if kind == 'SlateRoomTab':return 'slate'
    if kind == 'OfficeBuildingTab':return 'office'
    if kind in ENGINEERING_TABS or kind == 'EmptyWorkspaceTab' or kind.endswith(('DeviceTab', 'HardwareTab')):return 'engineering'
    return 'files'


def is_room(widget):
    return bool(widget is not None and widget.property('ledgerRoom'))


def show_files(host):
    """Return to the most recent open file or tool; with nothing open, show where to start."""
    host._close_start()
    for index in range(host.tabs.count() - 1, -1, -1):
        widget = host.tabs.widget(index)
        if not is_room(widget) or isinstance(widget, FilesStart):
            host.tabs.setCurrentWidget(widget);return widget
    tab = FilesStart(host);host.tabs.addTab(tab, host.nav_icon('folder'), tab.title());host.tabs.setCurrentWidget(tab)
    return tab


FILES_NOTE = 'Open anything read-only in the universal viewer, or find a file in the workspace. Drop a file here to open it.'


class FilesStart(QWidget):
    """Files, before anything is open: open a file, find one, or pick a recent one."""

    def __init__(self, host):
        super().__init__();self.host = host;self.setProperty('ledgerRoom', True);self.setAcceptDrops(True)
        box = QVBoxLayout(self);box.setContentsMargins(28, 24, 28, 24)
        title = QLabel('Files');title.setStyleSheet('font-size:18px;color:#edaa69;font-weight:bold');box.addWidget(title)
        from .shell2 import QuietWords  # the quiet-script rule (D1-fix): the room's explanation is a note you may skip
        lead = QuietWords(host);lead.explain(FILES_NOTE);self.lead = lead;box.addWidget(lead)
        row = QHBoxLayout()
        for label, tip, fn in (('Open in viewer…', 'Ctrl+Alt+V · any file, anywhere', lambda:host.open_in_viewer()),
                               ('Find a file…', 'Ctrl+P · files in this workspace', host.quick_open),
                               ('Open…', 'Ctrl+O · open to edit', host.open_dialog)):
            button = QPushButton(label);button.setToolTip(tip);button.clicked.connect(fn);row.addWidget(button)
        row.addStretch(1);box.addLayout(row)
        recent = QLabel('Recent');recent.setStyleSheet('color:#b5bec8;font-weight:bold;margin-top:12px');box.addWidget(recent)
        self.recent = QListWidget();self.recent.setAccessibleName('Recent files');self.recent.itemActivated.connect(self.open_recent);box.addWidget(self.recent, 1)
        self.fill()

    def fill(self):
        self.recent.clear()
        for path in getattr(self.host, '_viewer_recent', [])[:10]:
            item = QListWidgetItem(Path(path).name + '   ·   viewed · ' + str(Path(path).parent));item.setData(Qt.UserRole + 1, path);self.recent.addItem(item)
        for rel in list(self.host.session.state.get('recent', []))[:20]:
            item = QListWidgetItem(str(rel));item.setData(Qt.UserRole, str(rel));self.recent.addItem(item)
        if not self.recent.count():self.recent.addItem('Nothing opened yet.')

    def open_recent(self, item):
        if item.data(Qt.UserRole + 1):self.host.open_in_viewer(item.data(Qt.UserRole + 1));return
        rel = item.data(Qt.UserRole)
        if rel:self.host.open_document(self.host.root / rel)

    def title(self):return 'Files'

    def inspector(self):
        recent = len(self.host.session.state.get('recent', []))
        from .shell2 import Note  # the two ways in are notes you may skip: the Paper script, the keys printed
        return 'Files', [('Open', Note('Ctrl+Alt+V opens any file read-only.\nCtrl+P finds a file in this workspace.')), ('Recent', '%d files' % recent),
                         ('Kinds', 'Code, PDF, images, Gerber, archives, disk images and more')]

    def info(self):return 'Open a file · find a file · recent files'

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and all(u.isLocalFile() for u in event.mimeData().urls()):event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if Path(url.toLocalFile()).is_file():self.host.open_in_viewer(url.toLocalFile())
        event.acceptProposedAction()


def add_live_tree(host):
    """Office and Slate at the top of the navigator, with what is waiting in each. Labels refresh every few seconds."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QTreeWidgetItem
    nav = host.nav
    for i in range(nav.topLevelItemCount() - 1, -1, -1):
        if nav.topLevelItem(i).data(0, Qt.UserRole + 2) == 'nav_live':nav.takeTopLevelItem(i)
    def node(title, destination, icon_name, parent=None, tip=''):
        item = QTreeWidgetItem([title]);item.setData(0, Qt.UserRole + 2, 'ledger_control' if parent is not None else 'nav_live')
        item.setData(0, Qt.UserRole + 4, destination);item.setIcon(0, host.nav_icon(icon_name));item.setToolTip(0, tip)
        if parent is None:nav.insertTopLevelItem(0 if destination == 'office' else 1, item)
        else:parent.addChild(item)
        return item
    office = node('Office', 'office', 'import', tip='Receive files, catalog them and read them as staC')
    host._live_inbox = node('Ingress', 'office', 'folder', office, 'Files that came in and wait to be received')
    host._live_deliveries = node('Deliveries', 'office', 'evidence', office, 'Recent deliveries')
    slate = node('Graphite', 'slate', 'brain-link', tip='The local brain and what it has learned')
    host._live_brain = node('Brain', 'slate', 'brain-link', slate, 'The local model')
    host._live_matrix = node('Instruction matrix', 'slate', 'trace', slate, 'What worked and what failed')
    # Clicking a live branch opens its room (the click handler treats these like Ledger controls).
    office.setData(0, Qt.UserRole + 4, 'office');slate.setData(0, Qt.UserRole + 4, 'slate')
    office.setExpanded(True);slate.setExpanded(True)
    if not hasattr(host, '_live_timer'):
        host._live_timer = QTimer(host);host._live_timer.setInterval(5000);host._live_timer.timeout.connect(lambda:refresh_live_tree(host));host._live_timer.start()
    refresh_live_tree(host)


def refresh_live_tree(host):
    if getattr(host, '_closing', False) or not hasattr(host, '_live_inbox'):return
    from .engine import engineering
    from .engineering_kernel import operator
    def call(op, args=None):
        try:
            r = engineering(host.root).dispatch(op, args or {}, operator());return r['result'] if r.get('ok') else None
        except Exception:return None
    try:
        status = call('receiving.status') or {};waiting = len(status.get('inbox_waiting') or [])
        deliveries = (call('receiving.deliveries', {'limit': 30}) or {}).get('deliveries', [])
        yours = sum(1 for d in deliveries if d['stage'] == 'REVIEWED');moving = sum(1 for d in deliveries if d['stage'] in ('SCANNING', 'REVIEWING', 'INDEXING'))
        host._live_inbox.setText(0, 'Ingress · %d new' % waiting if waiting else 'Ingress · nothing new');host._status_inbox = waiting
        host._live_deliveries.setText(0, 'Deliveries · ' + (', '.join(x for x in (('%d reading' % moving) if moving else '', ('%d for you' % yours) if yours else '') if x) or str(len(deliveries))))
        brain = call('brain.status') or {}
        words = {'READY': 'ready', 'MODEL_STOPPED': 'stopped', 'NO_MODEL_SELECTED': 'no model yet'}.get(brain.get('state'), 'unknown')
        host._live_brain.setText(0, 'Brain · ' + words)
        counts = (call('matrix.status') or {}).get('counts', {})
        host._live_matrix.setText(0, 'Instruction matrix · %d worked · %d failed' % (counts.get('SUCCESS', 0), counts.get('FAILED', 0) + counts.get('BLOCKED', 0)))
    except RuntimeError:
        return  # the tree was rebuilt while refreshing; the next tick uses the new items


def status_text(host, widget, short, lang):
    """The status bar: engineering work keeps its target; everything else names the workspace."""
    from .project_context import detached
    if not detached(host.root) and (room_for(widget, host._home_active) == 'engineering' or type(widget).__name__ == 'CodeEditor' and short not in ('', None)):
        return 'ARC-1 · %s · %s · UTF-8' % (short, lang)  # the attached ARC-1 project names its target
    from . import locations
    try:value = locations.marker(host.root)
    except ValueError:value = None
    name = (value or {}).get('name') or ('Program workspace' if locations.contains_program(host.root) else Path(host.root).name)
    parts = [name + ' workspace']
    brain = getattr(host, '_status_brain', None)
    if brain:parts.append('Brain ' + brain)
    waiting = getattr(host, '_status_inbox', None)
    if waiting:parts.append('%d arrived' % waiting)
    return ' · '.join(parts)
