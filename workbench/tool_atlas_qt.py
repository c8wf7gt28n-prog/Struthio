"""Read-only Atlas browser and explicit owner-private passport snapshots."""
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QComboBox, QTreeWidget, QTreeWidgetItem, QPlainTextEdit,
    QSplitter, QHeaderView, QTabWidget)
from .engineering_kernel import operator


class ToolAtlasTab(QWidget):
    def __init__(self, bridge):
        super().__init__(); self.bridge = bridge; self.offset = 0; self.current = None
        box = QVBoxLayout(self)
        box.addWidget(QLabel('TOOL ATLAS · operation contracts and passports'))
        row = QHBoxLayout(); self.search = QLineEdit()
        writing_prompt(self.search, 'Search Calc, Python, KiCad, ngspice or an operation ID; press Enter')
        self.kind = QComboBox(); self.kind.addItems(['All entries', 'Operations', 'Job tools'])
        find = QPushButton('Find'); row.addWidget(self.search, 1); row.addWidget(self.kind); row.addWidget(find)
        box.addLayout(row)
        splitter = QSplitter(Qt.Vertical)
        self.table = QTreeWidget(); self.table.setRootIsDecorated(False)
        self.table.setHeaderLabels(['Registered ID', 'Kind', 'Prerequisites', 'Qualification'])
        self.table.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 135); self.table.setColumnWidth(2, 370); self.table.setColumnWidth(3, 150)
        self.table.setAccessibleName('Tool Atlas search results')
        self.detail = QPlainTextEdit(); self.detail.setReadOnly(True)
        self.detail.setAccessibleName('Selected operation passport')
        self.technical = QPlainTextEdit(); self.technical.setReadOnly(True)
        details = QTabWidget(); details.addTab(self.detail, 'Passport'); details.addTab(self.technical, 'Exact contract')
        splitter.addWidget(self.table); splitter.addWidget(details); box.addWidget(splitter, 1)
        row = QHBoxLayout(); self.previous = QPushButton('Previous'); self.next = QPushButton('Next')
        self.save = QPushButton('Save passport snapshot'); self.save.setEnabled(False)
        for button in (self.previous, self.next, self.save): row.addWidget(button)
        row.addStretch(); box.addLayout(row)
        saved = QHBoxLayout(); self.snapshots = QComboBox(); saved.addWidget(self.snapshots, 1)
        open_saved = QPushButton('Check saved passport'); saved.addWidget(open_saved); box.addLayout(saved)
        self.note = QLabel('Discovery only. An installed tool is not a tested operation.'); self.note.setWordWrap(True); box.addWidget(self.note)
        find.clicked.connect(self.find); self.search.returnPressed.connect(self.find)
        self.kind.currentIndexChanged.connect(self.find); self.previous.clicked.connect(lambda: self.page(-1))
        self.next.clicked.connect(lambda: self.page(1)); self.table.itemSelectionChanged.connect(self.select)
        self.save.clicked.connect(self.save_snapshot); open_saved.clicked.connect(self.open_snapshot)
        self.find(); self.load_snapshots()

    def title(self): return 'Tool Atlas'

    def call(self, operation, arguments):
        response = self.bridge.kernel.dispatch(operation, arguments, operator())
        if not response['ok']:
            self.note.setText(response['error']['message']); return None
        return response['result']

    def find(self, *unused):
        self.offset = 0; self.refresh()

    def page(self, direction):
        self.offset = max(0, self.offset + direction * 40); self.refresh()

    def refresh(self):
        args = {'query': self.search.text(), 'limit': 40, 'offset': self.offset}
        if self.kind.currentIndex(): args['kind'] = ['OPERATION', 'JOB_TOOL'][self.kind.currentIndex() - 1]
        value = self.call('atlas.lookup', args)
        if value is None: return
        self.table.clear(); self.current = None; self.save.setEnabled(False); self.detail.clear(); self.technical.clear()
        for entry in value['entries']:
            item = QTreeWidgetItem([entry['name'], entry['kind'], entry['summary'], entry['qualification']])
            item.setData(0, Qt.UserRole, {'name': entry['name'], 'kind': entry['kind']}); self.table.addTopLevelItem(item)
        self.previous.setEnabled(self.offset > 0); self.next.setEnabled(value['has_more'])
        self.note.setText(str(value['matches']) + ' matches · ' + value['notice'])
        if self.table.topLevelItemCount(): self.table.setCurrentItem(self.table.topLevelItem(0))

    def select(self):
        item = self.table.currentItem(); self.current = item.data(0, Qt.UserRole) if item else None
        self.save.setEnabled(bool(self.current))
        if self.current:
            value = self.call('atlas.operation_schema', self.current)
            if value is not None: self.show_entry(value)

    def show_entry(self, value, prefix=''):
        contract = value['contract']; passport = value['passport']; assessment = value['assessment']
        arguments = contract.get('arguments', {})
        source = contract.get('source') or {}
        lines = [prefix + value['name'], value['kind'].replace('_', ' ').title(), '',
                 'NOT TESTED', 'No host-bound operation probe has qualified this entry.', '',
                 'Current prerequisites', value['summary'],
                 'Permission: ' + assessment['permitted']['state'].lower().replace('_', ' '),
                 'Required scope: ' + contract['scope'], '',
                 'Required arguments', ', '.join(arguments.get('required', [])) or
                    ('Use jobs.submit with this registered tool ID; runtime options are checked there.' if value['kind'] == 'JOB_TOOL' else 'None'), '',
                 'Source', str(source.get('path') or 'Unresolved'),
                 'SHA-256: ' + str(source.get('sha256') or 'Unavailable'), '',
                 'Licence', passport['licence'], '', 'Known limits', *passport['limits'], '',
                 'The Exact contract tab contains argument types and recorded bindings.']
        self.detail.setPlainText('\n'.join(lines))
        self.technical.setPlainText(json.dumps(value, indent=2, ensure_ascii=False))

    def load_snapshots(self, selected=None):
        value = self.call('atlas.passports.list', {'limit': 100})
        if value is None: return
        self.snapshots.clear()
        for item in value['passports']:
            self.snapshots.addItem(item['name'] + ' · ' + item['id'][:8], item['id'])
            if item['id'] == selected: self.snapshots.setCurrentIndex(self.snapshots.count() - 1)

    def save_snapshot(self):
        if not self.current: return
        value = self.call('atlas.passport.save', self.current)
        if value is not None:
            self.load_snapshots(value['id']); self.note.setText('Passport saved. This records a snapshot and grants no execution permission.')

    def open_snapshot(self):
        ident = self.snapshots.currentData()
        if not ident: return
        value = self.call('atlas.passport.get', {'id': ident})
        if value is not None:
            self.show_entry(value['current'] or value['snapshot']['entry'], value['freshness'] + '\n\n')
            self.technical.setPlainText(json.dumps(value, indent=2, ensure_ascii=False))
            self.note.setText(value['freshness'] + ' · qualification remains UNTESTED.')
