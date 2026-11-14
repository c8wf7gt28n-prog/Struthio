"""Existing-workspace UI for the source-backed Slate foundation."""
from __future__ import annotations
from .text_prompts import writing_prompt

import json
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTabWidget, QTreeWidget, QTreeWidgetItem, QPlainTextEdit,
    QHeaderView, QSplitter)
from .engineering_kernel import operator
from . import stacy_foundation as foundation


def selected_view(tab):
    """Only supported concrete selections become ViewContext input."""
    from .control_qt import SettingsTab, CommandsTab
    from .hdl_qt import HdlTab
    if isinstance(tab, SettingsTab):
        row = tab.current
        if row and row.get('key') and not tab.tools.isVisible():
            return {'view': 'settings', 'selection': row['key']}
    if isinstance(tab, CommandsTab):
        item = tab.table.currentItem()
        row = item.data(0, Qt.UserRole) if item else None
        if row and row.get('kind') == 'Kernel command':
            return {'view': 'commands', 'selection': row['command']}
    if isinstance(tab, HdlTab):
        value = tab.profile.currentData()
        if value in ('rgmii', 'sdram', 'pump'):
            return {'view': 'hdl', 'selection': value}
    return None


def selected_program(tab):
    """Capture only bounded local Programs metadata from the actual selected tab."""
    from .edit_storage import relative
    from .local_brain import PROGRAM_CONTEXT_LIMIT, compact_program_context
    from .program_rooms_qt import ProgramRoom

    if not isinstance(tab, ProgramRoom):
        return None
    packet = {'room': tab.key}
    if tab.busy:
        return packet

    def add(key, value):
        if value and len(compact_program_context({**packet, key: value}).encode('utf-8')) <= PROGRAM_CONTEXT_LIMIT:
            packet[key] = value

    def file_path(value):
        try:
            value = relative(value)
        except ValueError:
            return None
        return value if all(not part.startswith('.') for part in value.split('/')) else None

    def binding(value, hash_key='sha256', *, require_hash=True):
        path = file_path(value.get('path'))
        digest = value.get(hash_key)
        if not path:
            return None
        if isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest):
            return {'path': path, 'sha256': digest}
        return None if require_hash else {'path': path}

    if tab.output:
        add('result', binding(tab.output, 'expected_sha256'))
    if tab.key == 'delivery':
        entries = (tab.current or {}).get('entries', [])
        if entries:
            verified = [binding(item) for item in entries]
            add('entry_count', len(entries))
            if all(verified):
                add('entries', verified)
        else:
            paths = [file_path(path) for path in tab.staged]
            if all(paths):
                add('paths', paths)
    elif tab.key != 'transfer':
        add('source', binding(tab.current or {'path': tab.source.text().strip()}, require_hash=False))
    destination = getattr(tab, 'destination', None)
    if destination is not None:
        add('destination', file_path(destination.text().strip()))
    combos = {'freecad': ('object', 'shape', 200), 'godot': ('scene', 'scene', 1000),
              'cartridge': ('core', 'core', 80), 'mail': ('index', 'attachment', 0)}
    if tab.key in combos:
        key, attr, size = combos[tab.key]
        choice = getattr(tab, attr).currentData()
        if ((isinstance(choice, str) and 0 < len(choice) <= size)
                or (key == 'index' and type(choice) is int and 0 <= choice <= 999)):
            add('selection', {key: choice})
    elif tab.key == 'print':
        add('selection', {'paper': tab.paper.currentText(), 'title': tab.print_title.text().strip()})
    elif tab.key == 'media':
        add('selection', {'start_seconds': tab.start.value(), 'duration_seconds': tab.duration.value()})
    return packet


class StacyFoundationTab(QWidget):
    def __init__(self, bridge):
        super().__init__()
        self.bridge, self.kernel = bridge, bridge.kernel
        self.last_packet = None
        box = QVBoxLayout(self)
        heading = QLabel('GRAPHITE KNOWLEDGE · foundation')
        heading.setObjectName('section')
        box.addWidget(heading)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.PlainText)
        box.addWidget(self.status)
        notice = QLabel('Source-bound knowledge seed · Durable awareness is active · Open the Brain room for local inference.')
        notice.setWordWrap(True)
        box.addWidget(notice)
        self.pages = QTabWidget()
        box.addWidget(self.pages, 1)

        overview = QWidget(); layout = QVBoxLayout(overview)
        self.summary = QPlainTextEdit(); self.summary.setReadOnly(True)
        layout.addWidget(self.summary)
        self.pages.addTab(overview, 'Overview')

        caps = QWidget(); layout = QVBoxLayout(caps)
        self.cap_filter = QLineEdit(); writing_prompt(self.cap_filter, 'Filter registered capabilities, for example boot.inspect')
        layout.addWidget(self.cap_filter)
        self.cap_table = QTreeWidget(); self.cap_table.setRootIsDecorated(False)
        self.cap_table.setHeaderLabels(['Operation', 'Status', 'Scope'])
        self.cap_table.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cap_table.setColumnWidth(1, 215)
        layout.addWidget(self.cap_table, 1)
        self.cap_detail = QPlainTextEdit(); self.cap_detail.setReadOnly(True); self.cap_detail.setMaximumHeight(190)
        layout.addWidget(self.cap_detail)
        self.cap_technical=QPushButton('Technical capability details');self.cap_technical.setCheckable(True)
        self.cap_technical.toggled.connect(lambda _:self.cap_selected());layout.addWidget(self.cap_technical)
        self.inspect_button = QPushButton('Read operation')
        self.inspect_button.setToolTip('Run a supported read through the existing Kernel; no native job is launched.')
        layout.addWidget(self.inspect_button)
        self.inspect_button.clicked.connect(self.read_selected)
        self.cap_table.itemSelectionChanged.connect(self.cap_selected)
        self.cap_filter.textChanged.connect(self.refresh_capabilities)
        self.pages.addTab(caps, 'Capabilities')

        seed = QWidget(); layout = QVBoxLayout(seed)
        self.query = QLineEdit(); writing_prompt(self.query, 'Search the indexed knowledge seed')
        layout.addWidget(self.query)
        self.seed_table = QTreeWidget(); self.seed_table.setRootIsDecorated(False)
        self.seed_table.setHeaderLabels(['Seed record', 'Kind'])
        self.seed_table.header().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.seed_table, 1)
        self.seed_detail = QPlainTextEdit(); self.seed_detail.setReadOnly(True)
        layout.addWidget(self.seed_detail, 1)
        self.query.textChanged.connect(self.search_seed)
        self.seed_table.itemSelectionChanged.connect(self.seed_selected)
        self.pages.addTab(seed, 'Seed')

        explain = QWidget(); layout = QVBoxLayout(explain)
        row = QHBoxLayout()
        self.view = QComboBox(); self.view.addItems(list(foundation.contracts.VIEWS))
        self.view.setMinimumContentsLength(7)
        self.view.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.view.setMaximumWidth(135)
        self.selection = QLineEdit('reading.code_pt')
        writing_prompt(self.selection, 'Setting key, Kernel operation or HDL profile')
        describe = QPushButton('Explain'); current = QPushButton('Use last selected view')
        row.addWidget(self.view); row.addStretch(); row.addWidget(describe)
        layout.addLayout(row); layout.addWidget(self.selection); layout.addWidget(current)
        self.explanation = QPlainTextEdit(); self.explanation.setReadOnly(True)
        self.source_packet = QPlainTextEdit(); self.source_packet.setReadOnly(True)
        split = QSplitter(Qt.Vertical); split.addWidget(self.explanation); split.addWidget(self.source_packet)
        split.setSizes([180, 310]); layout.addWidget(split, 1)
        describe.clicked.connect(self.describe)
        current.clicked.connect(self.use_current)
        self.selection.returnPressed.connect(self.describe)
        self.view.currentTextChanged.connect(lambda v:self.selection.setText({'settings':'reading.code_pt','commands':'boot.inspect','hdl':'rgmii'}[v]))
        self.pages.addTab(explain, 'Explain')

        row = QHBoxLayout(); refresh = QPushButton('Refresh seed')
        refresh.setToolTip('Recheck the declared seed source bindings and current descriptors.')
        refresh.clicked.connect(self.refresh); row.addWidget(refresh); row.addStretch()
        self.note = QLabel('Read only · No job started')
        self.note.setToolTip('This foundation does not launch a native process or contact a provider.')
        self.note.setWordWrap(True); self.note.setTextFormat(Qt.PlainText)
        row.addWidget(self.note, 1); box.addLayout(row)
        self.refresh()

    def title(self): return 'Graphite · knowledge'

    def request(self, operation, args=None):
        result = self.kernel.dispatch(operation, args or {}, operator())
        if not result['ok']:
            raise ValueError(result['error']['message'])
        return result['result']

    def refresh(self):
        data = self.request('stacy.foundation')
        seed = data['seed']
        state={'VERIFIED_SOURCE_BINDINGS':'verified','SOURCE_UNAVAILABLE':'source unavailable','NOT_GENERATED':'not generated'}.get(seed['state'],seed['state'].lower())
        self.status.setText(f"Seed {state} · {seed['records']} records · {data['registered_operations']} operations · {data['registered_job_tools']} job tools")
        self.status.setToolTip(json.dumps(seed,indent=2))
        self.summary.setPlainText(
            'GRAPHITE FIRST\n\n' + foundation.OWNER_INTENT + '\n\n'
            'AVAILABLE IN THIS PASS\n'
            '• Indexed, source-bound knowledge seed with original source references.\n'
            '• Capability schemas with honest missing-input states.\n'
            '• Selected setting, command and HDL profile descriptors.\n'
            '• Deterministic field claims checked against their evidence packet.\n\n'
            'PASS 16\n'
            'The organizer and the lines share task views. Package desk separates inspection, review copies and admission.\n\n'
            'NEXT PASS\n'
            'Pass 17 develops PDF evidence; SW-002 follows it with document views.\n\n'
            'PROGRESS\nCore campaign: 40.5%; windows: 20%; combined scope: 38.2%. Independent acceptance remains open.\n'
            'Legacy knowledge campaign remains 61%; these are milestone weights, not engineering confidence.\n\n' +
            json.dumps(data, indent=2))
        self.refresh_capabilities(); self.search_seed()

    def refresh_capabilities(self, *_):
        self.cap_table.clear(); self.cap_detail.clear()
        try:
            data = self.request('stacy.capabilities', {'query':self.cap_filter.text()})
            for row in data['operations']:
                item = QTreeWidgetItem([row['operation'], row['summary'], row['scope']])
                item.setData(0, Qt.UserRole, row); self.cap_table.addTopLevelItem(item)
            if self.cap_table.topLevelItemCount():self.cap_table.setCurrentItem(self.cap_table.topLevelItem(0))
        except ValueError as exc:self.cap_detail.setPlainText(str(exc))

    def cap_selected(self):
        item = self.cap_table.currentItem()
        row=item.data(0,Qt.UserRole) if item else None
        if not row:self.cap_detail.clear()
        elif self.cap_technical.isChecked():self.cap_detail.setPlainText(json.dumps(row,indent=2))
        else:
            a=row['assessment']
            self.cap_detail.setPlainText(row['operation']+'\n'+row['summary']+'\n\n'+
                '\n'.join(label.capitalize()+': '+a[label]['state'] for label in ('declared','installed','available','permitted','qualified'))+
                '\n\nDispatch rechecks actual inputs and authority. No operation is qualified by this catalogue.')
        self.inspect_button.setEnabled(bool(item and item.data(0,Qt.UserRole)['operation'] in foundation.READERS))

    def read_selected(self):
        item = self.cap_table.currentItem()
        if not item:return
        operation = item.data(0, Qt.UserRole)['operation']
        try:
            data = self.request('stacy.reader', {'operation':operation})
            self.cap_detail.setPlainText(json.dumps(data, indent=2))
        except ValueError as exc:self.cap_detail.setPlainText(str(exc))

    def search_seed(self, *_):
        self.seed_table.clear(); self.seed_detail.clear()
        try:
            data = self.request('stacy.seed.search', {'query':self.query.text(), 'limit':20})
            for row in data['records']:
                item = QTreeWidgetItem([row['id'], row['kind']]); item.setData(0, Qt.UserRole, row)
                self.seed_table.addTopLevelItem(item)
            if self.seed_table.topLevelItemCount():self.seed_table.setCurrentItem(self.seed_table.topLevelItem(0))
        except ValueError as exc:self.seed_detail.setPlainText(str(exc))

    def seed_selected(self):
        item = self.seed_table.currentItem()
        self.seed_detail.setPlainText(json.dumps(item.data(0, Qt.UserRole), indent=2) if item else '')

    def use_current(self):
        context = getattr(self.bridge, 'last_stacy_view', None)
        if not context:
            self.explanation.setPlainText('Select a setting, Kernel command or HDL profile first.');return
        self.view.setCurrentText(context['view']); self.selection.setText(context['selection'])
        self.describe()

    def describe(self):
        self.last_packet = None; self.explanation.clear(); self.source_packet.clear()
        try:
            data = self.request('stacy.explain', {'view':self.view.currentText(), 'selection':self.selection.text().strip()})
            self.last_packet = data['packet']
            self.explanation.setPlainText(data['text']+'\n\n'+data['notice']+'\n\nUnknowns:\n'+'\n'.join(data['packet']['unknowns']))
            self.source_packet.setPlainText(json.dumps({'claims':data['answer']['claims'], 'packet':data['packet']}, indent=2))
        except ValueError as exc:self.explanation.setPlainText('BLOCKED · '+str(exc))
