"""The left column's Machine view: a one-line strip that is always visible, and a navigator of this computer, the work and Settings.

The strip and the tree read `machine_overview` (/proc, /sys, os.statvfs) and the existing cabinet model. Work rows are the
cabinet's own project identities; choosing one selects that record in the cabinet and opens it, never a copy. Nothing here
runs a tool, starts a job or changes a setting. Trash keeps its fixed place at the foot of the column; this file never touches it.
"""
import time
from PySide6.QtCore import Qt, QTimer, QSize, QSignalBlocker
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QPlainTextEdit, QSizePolicy
from . import machine_overview, host_observations, locations
from .engineering_kernel import operator
from .settings_qt import action, STYLE, INK

GRAPHITE = '#504d46'  # Paper v1.1 TEXT; metadata is never pale
BYTE_KEYS = {'size', 'total', 'free', 'used', 'available', 'limit', 'current'}
FLAG_KEYS = {'readonly', 'removable', 'carrier', 'exists'}
STRIP_INTERVAL_MS = 2000
STALE_SECONDS = 30
PAGE_STYLE = STYLE + '''
QTreeWidget#MachineTree {background:transparent;color:#504d46;border:0;}
QTreeWidget#MachineTree::item {padding:5px 2px;}
QTreeWidget#MachineTree::item:selected {background:#f3e3e2;color:#504d46;}
QPlainTextEdit#MachineDetail {background:transparent;color:#504d46;border:0;border-top:1px solid #dad4c8;padding:4px 0;}
'''


def when(stamp):
    return time.strftime('%H:%M:%S', time.localtime(stamp)) if stamp else 'not sampled'


def words(key, value):
    """Values as words for the details pane; bytes become sizes, booleans yes/no, nothing invented for None."""
    if value is None:
        return 'not observed'
    if isinstance(value, bool):
        return 'yes' if value else 'no'
    if key == 'rotational' and value in (0, 1):
        return 'rotating' if value else 'solid state'
    if key in FLAG_KEYS and value in (0, 1):
        return 'yes' if value else 'no'
    if key in BYTE_KEYS and isinstance(value, int):
        return machine_overview.human(value)
    if isinstance(value, (list, tuple)):
        return ', '.join(str(v) for v in value) or 'none'
    if isinstance(value, dict):
        return ', '.join('%s %s' % (k, words(k, v)) for k, v in value.items()) or 'none'
    return str(value)


def plain(text=''):
    label = QLabel(text); label.setTextFormat(Qt.PlainText); label.setWordWrap(True); label.setMinimumWidth(0); return label


class StripLabel(QLabel):
    """One line that elides to the column instead of widening it; the accessible text stays complete."""

    def __init__(self):
        super().__init__(); self.full = ''
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred); self.setMinimumWidth(0)

    def set_full(self, text):
        self.full = text; self.setText(text); self.update()

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())

    def paintEvent(self, event):
        painter = QPainter(self); painter.setPen(QColor(GRAPHITE))
        painter.drawText(self.rect(), Qt.AlignLeft | Qt.AlignVCenter, self.fontMetrics().elidedText(self.full, Qt.ElideRight, max(0, self.width() - 2)))
        painter.end()


class MachineStrip(QWidget):
    """CPU model · RAM used/total · free space of the workspace mount · network up/down, every two seconds (NV01)."""

    def __init__(self, host):
        super().__init__(); self.host = host; self.setObjectName('MachineStrip'); self.setProperty('paperFunctionalInk', True)
        self.setAccessibleName('Machine overview'); self.sample = None; self.model = None; self.model_at = 0
        row = QHBoxLayout(self); row.setContentsMargins(10, 6, 10, 0); row.setSpacing(0)
        self.label = StripLabel(); self.label.setAccessibleName('Machine overview line'); row.addWidget(self.label, 1)
        self.timer = QTimer(self); self.timer.setInterval(STRIP_INTERVAL_MS); self.timer.timeout.connect(self.refresh); self.timer.start()
        self.refresh()

    def workspace(self):
        return getattr(self.host, 'root', None) or locations.PACKAGE

    def refresh(self):
        if getattr(self.host, '_closing', False):
            self.timer.stop(); return
        clock = time.time()
        if self.model is None or clock - self.model_at > 60:
            self.model = machine_overview.cpu_model(); self.model_at = clock
        memory = host_observations.memory(); space = machine_overview.space(self.workspace()); up, names = machine_overview.network_up()
        self.sample = dict(sampled_at=clock, cpu=self.model, memory=memory, space=space, network_up=up, network_interfaces=names)
        parts = [machine_overview.short_model(self.model) or 'Processor unavailable',
                 ('RAM %s/%s' % (machine_overview.human(memory['used']), machine_overview.human(memory['total']))) if memory else 'RAM unavailable',
                 (machine_overview.human(space['free']) + ' free') if space else 'Storage unavailable',
                 'net up' if up else 'net down' if up is False else 'net unavailable']
        self.label.set_full(' · '.join(parts))
        page = getattr(self.host, 'machine_page', None)
        if page is not None and page.items:page.strip_line(self.label.full)
        detail = ('Observed %s on the computer Graphite runs on · processor /proc/cpuinfo · RAM /proc/meminfo · free space os.statvfs of the workspace mount'
                  ' · network /sys/class/net operstate and carrier%s. Unavailable values stay unavailable; nothing is animated.'
                  % (when(clock), (' (' + ', '.join(names) + ')') if names else ''))
        self.setToolTip(detail); self.setAccessibleDescription(detail)


class MachinePage(QWidget):
    """Machine → its sections; Work → the cabinet's projects by identity; Settings → the settings view. Details name source and freshness."""

    def __init__(self, host):
        super().__init__(); self.host = host; self.model = None; self.built_at = 0; self.items = {}
        self.expanded = {'machine', 'work'}; self.selected_id = 'machine'
        self.setProperty('paperFunctionalInk', True); self.setStyleSheet(PAGE_STYLE); self.setAccessibleName('Machine and work navigator')
        box = QVBoxLayout(self); box.setContentsMargins(8, 6, 8, 0); box.setSpacing(8)
        from .pane_qt import BranchTree
        self.tree = BranchTree(); self.tree.setObjectName('MachineTree'); self.tree.setHeaderHidden(True)  # D1b: the desk's tree (rows, indent, branch lines)
        self.tree.setAccessibleName('Machine and work navigator'); box.addWidget(self.tree, 1)
        self.details = QPlainTextEdit(); self.details.setObjectName('MachineDetail'); self.details.setReadOnly(True)
        self.details.setProperty('arcReadingRole', 'prose')  # words about the machine, not code: the prose family (V-03 rule)
        self.details.setAccessibleName('Machine detail: source and freshness'); self.details.setMaximumHeight(self.details_height()); box.addWidget(self.details)
        row = QHBoxLayout(); self.refresh_button = action('Refresh machine view', lambda: self.build(force=True)); row.addWidget(self.refresh_button); row.addStretch(); box.addLayout(row)
        self.caption = plain('Reading this computer…'); box.addWidget(self.caption)
        self.tree.itemSelectionChanged.connect(self.selected); self.tree.itemClicked.connect(self.activate); self.tree.itemActivated.connect(self.activate)
        self.tree.itemExpanded.connect(lambda item: self.expanded.add(item.data(0, Qt.UserRole)['id']))
        self.tree.itemCollapsed.connect(lambda item: self.expanded.discard(item.data(0, Qt.UserRole)['id']))

    def details_height(self):
        """Scales with the interface size, and yields to the tree on a short window (at most three tenths of the page)."""
        scale = float((getattr(self.host, 'reading_profile', None) or {}).get('ui_pt', 14.0)) / 14.0
        wanted = max(120, round(170 * scale))
        return min(wanted, max(90, int(self.height() * 0.3))) if self.height() > 0 else wanted

    def resizeEvent(self, event):
        super().resizeEvent(event); self.details.setMaximumHeight(self.details_height())

    def showEvent(self, event):
        super().showEvent(event)
        if self.model is None or time.time() - self.built_at > STALE_SECONDS:
            QTimer.singleShot(0, self.build)

    # ------------------------------------------------------------ data
    def kernel(self):
        bridge = getattr(self.host, 'ledger_bridge', None)
        return getattr(bridge, 'kernel', None)

    def projects(self):
        """The cabinet's project nodes, by the identities the cabinet itself shows; never a separate copy."""
        page = getattr(self.host, 'cabinet_page', None)
        nodes = (page.model or {}).get('nodes') if page is not None and page.model else None
        if nodes is None:
            kernel = self.kernel()
            if kernel is None:
                return []
            response = kernel.dispatch('ledger.cabinet', {}, operator())
            nodes = response['result']['nodes'] if response['ok'] else []
        rows = [node for node in nodes if node.get('role') == 'project']
        return sorted(rows, key=lambda node: (machine_overview.natural(node['label']), node['id']))

    def build(self, force=False):
        kernel = self.kernel()
        if kernel is None or getattr(self.host, '_closing', False):
            return False
        if not force and self.model is not None and time.time() - self.built_at < 1:
            return True
        response = kernel.dispatch('ledger.machine', {}, operator())
        if not response['ok']:
            self.caption.setText(response['error']['message']); return False
        self.model = response['result']; self.built_at = time.time()
        current = self.tree.currentItem()
        if current is not None:
            self.selected_id = current.data(0, Qt.UserRole)['id']
        self.items = {}
        with QSignalBlocker(self.tree):
            self.tree.clear()
            machine = self.add(None, 'machine', 'Machine', dict(kind='root', id='machine'))
            for section in self.model['sections']:
                suffix = {'UNAVAILABLE': ' · unavailable', 'NONE': ' · none detected', 'PARTIAL': ' · bounded'}.get(section['state'], '')
                node = self.add(machine, section['id'], section['title'] + suffix, dict(kind='section', id=section['id'], section=section))
                node.setToolTip(0, 'Observed ' + when(section['sampled_at']) + ' · ' + ' · '.join(section['sources']))
                for row in section['items']:
                    leaf = self.add(node, row['id'], row['label'], dict(kind='item', id=row['id'], section=section['id'], item=row))
                    leaf.setToolTip(0, ('Observed ' if row['state'] == 'OBSERVED' else row['state'].capitalize() + ' · ') + when(row['sampled_at']) + ' · ' + row['source'])
            work = self.add(None, 'work', 'Work', dict(kind='work_root', id='work'))
            projects = self.projects()
            if projects:
                for node in projects:
                    leaf = self.add(work, node['id'], node['label'], dict(kind='work', id=node['id'], node=node))
                    leaf.setForeground(0, QColor(INK)); leaf.setToolTip(0, 'The same record as the cabinet · ' + node['canonical_id'])
            else:
                work.setText(0, 'Work · no projects yet'); work.setData(0, Qt.UserRole, dict(kind='work_empty', id='work'))
            settings = self.add(None, 'settings', 'Settings', dict(kind='settings', id='settings'))
            settings.setForeground(0, QColor(INK)); settings.setToolTip(0, 'Show the Graphite settings hierarchy in this column')
            for ident, item in self.items.items():
                if item.childCount():
                    item.setExpanded(ident in self.expanded)
            # HATCH DESK D1b: the details pane is out of the left pane; each row's tooltip carries its whole description
            # (source, time, values), and the Machine row the strip's one line as well.
            for item in self.items.values():item.setToolTip(0, self.describe(item.data(0, Qt.UserRole) or {}))
            self.strip_line()
            chosen = self.items.get(self.selected_id) or machine
            self.tree.setCurrentItem(chosen)
        self.selected()
        self.caption.setText('Observed %s on this computer from /proc, /sys and os.statvfs · nothing was run · %s' % (when(self.model['sampled_at']), self.model['basis'].replace('_', ' ').lower()))
        tab = getattr(getattr(self.host, 'settings_navigator', None), 'machine', None)
        if tab is not None:tab.setToolTip('Machine · ' + self.caption.text())  # D1b: the caption is out of the pane; the tab says it
        return True

    def strip_line(self, text=None):
        """The machine strip's one line (processor · RAM · free space · network) on the Machine row: the strip left the pane
        for the Machine tab (HATCH DESK D1b), and its facts are the Processor, Memory, Storage and Connections rows below."""
        strip = getattr(self.host, 'machine_strip', None);root = self.items.get('machine')
        text = text if text is not None else (strip.label.full if strip is not None else '')
        if root is None:return
        tip = (text + '\n\n' if text else '') + self.describe(root.data(0, Qt.UserRole) or {})
        if root.toolTip(0) != tip:root.setToolTip(0, tip)

    def add(self, parent, ident, label, data):
        item = QTreeWidgetItem([label]); item.setData(0, Qt.UserRole, data); self.items[ident] = item
        if parent is None:
            self.tree.addTopLevelItem(item)
        else:
            parent.addChild(item)
        return item

    # ------------------------------------------------------------ words
    def describe(self, data):
        kind = data.get('kind'); model = self.model or {}
        if kind == 'root':
            host = model.get('host') or {}
            return '\n'.join(['Machine · the computer Graphite runs on now',
                              'Observed %s · sources /proc, /sys and os.statvfs · nothing was run' % when(model.get('sampled_at')),
                              'Kernel %s · host name %s' % (host.get('kernel') or 'not observed', host.get('hostname') or 'not observed'),
                              'Program folder: %s' % (model.get('program_folder') or 'not observed'), 'Workspace: %s' % (model.get('workspace') or 'not observed'),
                              'Basis: these observations qualify nothing about the owner\'s ThinkPad; they describe this host only.',
                              'ARC project hardware is design material under Work / Project, not this machine.'])
        if kind == 'section':
            section = data['section']
            state = {'OBSERVED': '%d observations' % section['count'], 'PARTIAL': '%d observations · bounded list, more exist' % section['count'],
                     'NONE': 'nothing detected', 'UNAVAILABLE': 'unavailable'}.get(section['state'], section['state'])
            lines = [section['title'] + ' · ' + state, 'Observed ' + when(section['sampled_at']), 'Sources: ' + ' · '.join(section['sources'])]
            lines += ['Note: ' + note for note in section['notes']]
            lines.append('Order: ' + section['order'])
            return '\n'.join(lines)
        if kind == 'item':
            row = data['item']
            lines = [row['label'], ('Observed ' if row['state'] == 'OBSERVED' else row['state'].capitalize() + ' · ') + when(row['sampled_at']) + ' · source ' + row['source']]
            if row.get('reason'):
                lines.append('Reason: ' + row['reason'])
            lines += ['%s: %s' % (key.replace('_', ' '), words(key, value)) for key, value in row['values'].items()]
            return '\n'.join(lines)
        if kind == 'work_root':
            return 'Work · the cabinet\'s projects, by their own identities\nChoose a project to select the same record in the cabinet and open it in the centre. Nothing is copied.'
        if kind == 'work':
            node = data['node']
            return '\n'.join(['Project · ' + node['label'], 'Identity %s · the same record the cabinet shows (no copy)%s' % (
                node['canonical_id'], (' · revision %s' % node['revision']) if node.get('revision') is not None else ''),
                              'Choose it to select the record in the cabinet and open it in the centre.'])
        if kind == 'work_empty':
            return 'No projects are saved yet. New Project in the menu creates one; it appears here and in the cabinet under the same identity.'
        if kind == 'settings':
            from .settings_registry import SPECS
            return 'Settings · %d definitions in the shared registry\nChoose it to show the settings hierarchy in this column; the editor opens in the centre.' % len(SPECS)
        return ''

    def selected(self):
        item = self.tree.currentItem()
        self.details.setPlainText(self.describe(item.data(0, Qt.UserRole)) if item is not None else '')

    # ------------------------------------------------------------ navigation
    def finder_place(self, data):
        """UI-04: a storage row (the program folder, the workspace, a mount) names a folder; the Finder shows it while Home is active."""
        if data.get('kind') != 'item' or not str(data.get('id', '')).startswith(('storage:path:', 'storage:mount:')):
            return None
        values = (data.get('item') or {}).get('values') or {}
        return values.get('path') or values.get('mountpoint')

    def activate(self, item, column=0):
        data = item.data(0, Qt.UserRole) or {}
        place = self.finder_place(data)
        if place:
            finder = getattr(self.host, 'finder', None)
            if finder is not None:
                finder.show_place(place)
        elif data.get('kind') == 'work':
            self.open_work(data['id'])
        elif data.get('kind') == 'settings':
            bridge = getattr(self.host, 'ledger_bridge', None)
            if bridge is not None:
                bridge.show_settings()

    def open_work(self, ident):
        """Select the identity in the cabinet and open its record room; the cabinet view takes the column (NV02)."""
        page = getattr(self.host, 'cabinet_page', None); navigator = getattr(self.host, 'settings_navigator', None)
        if page is None:
            return None
        if page.model is None or ident not in page.items:
            page.refresh(force=True)
        if page.using_legacy:
            page.set_legacy(False)
        if navigator is not None:
            navigator.show_view('cabinet')
        page.select(ident, reveal=True)
        return page.open(ident)
