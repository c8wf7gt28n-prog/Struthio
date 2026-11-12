"""Owner-facing inquiry drafts, revision history and checked receipt links."""
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QPlainTextEdit, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QTextBrowser, QSpinBox)
from .engineering_kernel import operator
from . import discovery_ir


class DiscoveryTab(QWidget):
    def __init__(self, bridge):
        super().__init__(); self.bridge = bridge; self.current = None; self.revision = None
        box = QVBoxLayout(self); heading = QLabel('INQUIRIES'); heading.setObjectName('section'); box.addWidget(heading)
        row = QHBoxLayout(); self.saved = QComboBox(); self.saved.setMinimumWidth(260); row.addWidget(self.saved, 1)
        self.open_button = QPushButton('Open'); new = QPushButton('New inquiry'); self.save_button = QPushButton('Save revision'); self.refresh_button = QPushButton('Check bindings')
        for button in (self.open_button, new, self.save_button, self.refresh_button): row.addWidget(button)
        box.addLayout(row)
        self.title_input = QLineEdit(); writing_prompt(self.title_input, 'Inquiry title'); box.addWidget(self.title_input)
        box.addWidget(QLabel('Question')); self.question = QPlainTextEdit(); self.question.setMaximumHeight(85); box.addWidget(self.question)
        box.addWidget(QLabel('Stopping criteria · one per line')); self.stop = QPlainTextEdit(); self.stop.setMaximumHeight(65); box.addWidget(self.stop)
        self.tabs = QTabWidget(); box.addWidget(self.tabs, 1)
        overview = QWidget(); layout = QVBoxLayout(overview)
        self.summary = QLabel('New draft'); self.summary.setWordWrap(True); layout.addWidget(self.summary)
        self.nodes = QTreeWidget(); self.nodes.setRootIsDecorated(False)
        self.nodes.setHeaderLabels(['Entity', 'Kind', 'Status', 'Declared dependencies'])
        self.nodes.setColumnWidth(0, 150); self.nodes.setColumnWidth(1, 150); self.nodes.setColumnWidth(2, 230)
        self.nodes.header().setSectionResizeMode(3, QHeaderView.Stretch); layout.addWidget(self.nodes, 1)
        self.why = QTextBrowser(); self.why.setMaximumHeight(145); layout.addWidget(self.why)
        self.tabs.addTab(overview, 'Inquiry')
        self.details = QPlainTextEdit(); self.details.setAccessibleName('Optional typed inquiry structure')
        self.tabs.addTab(self.details, 'Optional structure')
        observation = QWidget(); layout = QVBoxLayout(observation)
        layout.addWidget(QLabel('Link an existing checked receipt · this does not run a tool'))
        row = QHBoxLayout(); self.target = QComboBox(); self.method = QComboBox(); self.reader = QComboBox(); self.reader.addItems(['MATH', 'SCHEDULE'])
        for label, widget in (('Claim / hypothesis', self.target), ('Method', self.method), ('Reader', self.reader)):
            row.addWidget(QLabel(label)); row.addWidget(widget, 1)
        layout.addLayout(row); self.receipt = QLineEdit(); writing_prompt(self.receipt, 'Math action ID, or schedule receipt ID'); layout.addWidget(self.receipt)
        row = QHBoxLayout(); self.expected = QComboBox(); self.expected.addItems(['Expected true', 'Expected false'])
        self.output = QSpinBox(); self.output.setRange(0, 15); row.addWidget(self.expected); row.addWidget(QLabel('Math Boolean output index')); row.addWidget(self.output)
        attach = QPushButton('Link checked predicate'); row.addWidget(attach); layout.addLayout(row)
        self.observation_note = QLineEdit(); writing_prompt(self.observation_note, 'Scope/note for this check'); layout.addWidget(self.observation_note)
        self.checks = QTreeWidget(); self.checks.setHeaderLabels(['Target', 'Predicate', 'Freshness', 'Receipt']); self.checks.header().setSectionResizeMode(3, QHeaderView.Stretch)
        layout.addWidget(self.checks, 1); self.tabs.addTab(observation, 'Checked predicates')
        self.history = QPlainTextEdit(); self.history.setReadOnly(True); self.tabs.addTab(self.history, 'History')
        self.note = QLabel('A saved inquiry is a proposal. Pin this workspace to keep unsaved edits while switching views.'); self.note.setWordWrap(True); box.addWidget(self.note)
        self.open_button.clicked.connect(self.open_selected); new.clicked.connect(self.new)
        self.save_button.clicked.connect(self.save); self.refresh_button.clicked.connect(self.refresh)
        self.nodes.itemSelectionChanged.connect(self.selected); attach.clicked.connect(self.attach)
        self.reader.currentTextChanged.connect(lambda value: self.output.setEnabled(value == 'MATH'))
        self.load_list(); self.new()

    def title(self): return 'Inquiries'

    def call(self, operation, arguments):
        response = self.bridge.kernel.dispatch(operation, arguments, operator())
        if not response['ok']:
            self.note.setText(response['error']['message']); return None
        return response['result']

    def load_list(self, selected=None):
        value = self.call('discovery.list', {'limit': 100})
        if value is None: return
        self.saved.clear()
        for item in value['inquiries']:
            self.saved.addItem(item['title'] + ' · r' + str(item['revision']), item['id'])
            if item['id'] == selected: self.saved.setCurrentIndex(self.saved.count() - 1)

    def set_document(self, document):
        self.title_input.setText(document['title']); self.question.setPlainText(document['goal']['question'])
        self.stop.setPlainText('\n'.join(document['goal']['stopping_criteria']))
        self.details.setPlainText(json.dumps({k: v for k, v in document.items() if k not in ('schema', 'title', 'goal')}, indent=2))

    def document(self):
        from .record_io import strict_json
        structure = strict_json(self.details.toPlainText().encode())
        if not isinstance(structure, dict) or set(structure) & {'schema', 'title', 'goal'}:
            raise ValueError('Optional structure contains collections and budget only; use the visible question fields above.')
        return {'schema': discovery_ir.SCHEMA, **structure, 'title': self.title_input.text(),
                'goal': {'question': self.question.toPlainText(), 'stopping_criteria': [v.strip() for v in self.stop.toPlainText().splitlines() if v.strip()]}}

    def new(self):
        self.current = self.revision = None; self.set_document(discovery_ir.template())
        self.nodes.clear(); self.checks.clear(); self.history.clear(); self.why.clear(); self.target.clear(); self.method.clear()
        self.summary.setText('New inquiry · save a question now; optional structure can be added later.')
        self.note.setText('Unsaved draft. Saving does not launch a check or grant execution permission.')

    def open_selected(self):
        ident = self.saved.currentData()
        if ident is None: return
        self.current = ident; self.refresh(load_document=True)

    def save(self):
        try: document = self.document()
        except (ValueError, UnicodeError) as exc: self.note.setText(str(exc)); return
        args = {'document': document}
        if self.current: args.update(id=self.current, expected_revision=self.revision)
        value = self.call('discovery.revise' if self.current else 'discovery.create', args)
        if value is None: return
        self.current = value['id']; self.load_list(self.current); self.refresh(load_document=True)

    def refresh(self, *unused, load_document=False):
        if not self.current: return
        value = self.call('discovery.get', {'id': self.current})
        if value is None: return
        self.revision = value['inquiry']['revision']
        # Checking bindings must not replace an edited buffer. Saving still uses
        # the revision from the last loaded/saved document, not a newer refresh.
        if load_document:
            from .project_desk import digest
            self.loaded_revision = self.revision; self.loaded_document_digest = digest(value['inquiry']['document']); self.set_document(value['inquiry']['document'])
        else: self.revision = getattr(self, 'loaded_revision', self.revision)
        self.summary.setText('Revision ' + str(value['inquiry']['revision']) + ' · ' + value['state'].lower().replace('_', ' ') + ' · claim interpretations remain proposed')
        self.nodes.clear(); self.target.clear(); self.method.clear()
        for node in value['nodes']:
            item = QTreeWidgetItem([node['key'], node['kind'].replace('_', ' '), node['status'], ', '.join(node['depends_on'])])
            item.setData(0, Qt.UserRole, node); self.nodes.addTopLevelItem(item)
            if node['kind'] in ('claims', 'hypotheses'): self.target.addItem(node['key'])
            if node['kind'] == 'candidate_methods': self.method.addItem(node['key'])
        self.checks.clear()
        for observed in value['observations']:
            item = QTreeWidgetItem([observed['target'], observed['check']['state'], observed['status'], observed['receipt']])
            item.setToolTip(0, observed['check']['scope']); item.setToolTip(2, '\n'.join(observed['reasons'])); self.checks.addTopLevelItem(item)
        history = self.call('discovery.history', {'id': self.current, 'limit': 100})
        if history: self.history.setPlainText(json.dumps(history, indent=2))
        self.note.setText(value['notice'])
        if self.nodes.topLevelItemCount(): self.nodes.setCurrentItem(self.nodes.topLevelItem(0))

    def selected(self):
        item = self.nodes.currentItem()
        if item:
            node = item.data(0, Qt.UserRole)
            self.why.setPlainText('\n'.join([node['key'] + ' · ' + node['status'], *node['reasons'],
                'Changed causes: ' + ', '.join(node['causes']), 'Dependencies: ' + ', '.join(node['depends_on'])]))

    def attach(self):
        if not self.current: self.note.setText('Save the inquiry before linking a receipt.'); return
        from .project_desk import digest
        try:
            if digest(self.document()) != self.loaded_document_digest:
                self.note.setText('Save draft changes before linking a receipt to this version.'); return
        except (ValueError, UnicodeError) as exc: self.note.setText(str(exc)); return
        predicate = {'kind': 'BOOLEAN_OUTPUT' if self.reader.currentText() == 'MATH' else 'CAPACITY_FITS', 'expected': self.expected.currentIndex() == 0}
        if predicate['kind'] == 'BOOLEAN_OUTPUT': predicate['output'] = self.output.value()
        value = self.call('discovery.observe', {'id': self.current, 'expected_revision': self.revision,
            'target': self.target.currentText(), 'method': self.method.currentText(), 'reader': self.reader.currentText(),
            'receipt': self.receipt.text(), 'predicate': predicate, 'note': self.observation_note.text()})
        if value is not None:
            self.revision = self.loaded_revision = value['revision']; self.load_list(self.current); self.refresh()
