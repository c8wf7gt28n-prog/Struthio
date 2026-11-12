"""Method discovery with editable scratch examples and explicit admission limits."""
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QHeaderView, QTabWidget, QTextBrowser,
    QPlainTextEdit, QComboBox, QSplitter)
from .engineering_kernel import operator


class AlgorithmAtlasTab(QWidget):
    def __init__(self, bridge):
        super().__init__(); self.bridge = bridge; self.current = None; self.catalog_digest = None
        box = QVBoxLayout(self)
        heading = QLabel('ALGORITHM & THEORY ATLAS'); heading.setObjectName('section'); box.addWidget(heading)
        row = QHBoxLayout(); self.search = QLineEdit()
        writing_prompt(self.search, 'Find a method: units, capacity, equations, constraints, dependencies…')
        find = QPushButton('Find'); row.addWidget(self.search, 1); row.addWidget(find); box.addLayout(row)
        split = QSplitter(Qt.Vertical)
        self.table = QTreeWidget(); self.table.setRootIsDecorated(False)
        self.table.setHeaderLabels(['Method', 'Implementation', 'Profile'])
        self.table.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 235); self.table.setColumnWidth(2, 230)
        self.table.setAccessibleName('Algorithm and theory search results'); split.addWidget(self.table)
        self.tabs = QTabWidget()
        self.method = QTextBrowser(); self.method.setOpenExternalLinks(False); self.method.setOpenLinks(False)
        self.tabs.addTab(self.method, 'Method')
        scratch = QWidget(); layout = QVBoxLayout(scratch); row = QHBoxLayout()
        self.examples = QComboBox(); row.addWidget(self.examples, 1)
        self.check = QPushButton('Check declared input'); row.addWidget(self.check); layout.addLayout(row)
        layout.addWidget(QLabel('Scratch only · pin this workspace to keep it open; nothing saved to problem sheets'))
        self.input = QPlainTextEdit(); self.input.setAccessibleName('Editable declared method input'); layout.addWidget(self.input, 1)
        self.tabs.addTab(scratch, 'Try an example')
        self.report = QTextBrowser(); self.report.setOpenExternalLinks(False); self.tabs.addTab(self.report, 'Admission check')
        self.technical = QPlainTextEdit(); self.technical.setReadOnly(True); self.tabs.addTab(self.technical, 'Exact descriptor')
        split.addWidget(self.tabs); split.setSizes([270, 530]); box.addWidget(split, 1)
        self.note = QLabel('A method match is a hypothesis. No solver or engineering job runs here.'); self.note.setWordWrap(True); box.addWidget(self.note)
        find.clicked.connect(self.find); self.search.returnPressed.connect(self.find)
        self.table.itemSelectionChanged.connect(self.select); self.examples.currentIndexChanged.connect(self.load_example)
        self.check.clicked.connect(self.check_input); self.find()

    def title(self): return 'Algorithm & Theory Atlas'

    def call(self, operation, arguments):
        response = self.bridge.kernel.dispatch(operation, arguments, operator())
        if not response['ok']:
            self.note.setText(response['error']['message']); return None
        return response['result']

    def find(self):
        value = self.call('algo.lookup', {'query': self.search.text()})
        if value is None: return
        self.table.clear(); self.current = None; self.method.clear(); self.input.clear(); self.report.clear(); self.technical.clear()
        self.examples.clear(); self.check.setEnabled(False); self.catalog_digest = value['catalog_digest']
        for entry in value['entries']:
            state = entry['implementation']['state']
            label = {'LINKED': 'Linked · not host qualified', 'NOT_IMPLEMENTED': 'Planned · reference only',
                     'DEPENDENCY_UNAVAILABLE': 'Needs pinned dependency'}.get(state, state.lower().replace('_', ' '))
            item = QTreeWidgetItem([entry['title'], label, entry['task'].lower().replace('_', ' ')])
            item.setData(0, Qt.UserRole, entry['id']); self.table.addTopLevelItem(item)
        self.note.setText(str(value['matches']) + ' methods · source-linked profiles and clearly marked reference entries')
        if self.table.topLevelItemCount(): self.table.setCurrentItem(self.table.topLevelItem(0))

    def select(self):
        item = self.table.currentItem()
        if item is None: return
        value = self.call('algo.get', {'id': item.data(0, Qt.UserRole), 'expected_catalog_digest': self.catalog_digest})
        if value is None: self.check.setEnabled(False); return
        self.current = entry = value['entry']; self.check.setEnabled(True)
        implementation = entry['implementation']; operations = implementation['operations']
        lines = [entry['title'], '', entry['signature'], '', 'Domain', entry['domain'], '', 'Preconditions',
                 *['• ' + text for text in entry['preconditions']], '', 'What the implementation checks', entry['guarantee'], '',
                 'Limits', *['• ' + text for text in entry['non_guarantees']], '', 'Cost and bounds', entry['cost'], '',
                 'Counterexample to keep in mind', entry['counterexample'], '', 'Implementation',
                 implementation['state'].replace('_', ' ').title(),
                 ', '.join(op['operation'] for op in operations) or 'No registered operation for this profile.', '',
                 'References', *entry['references'], '', 'Licence review', entry['licence']]
        self.method.setPlainText('\n'.join(lines)); self.technical.setPlainText(json.dumps(value, indent=2, ensure_ascii=False))
        self.report.clear(); self.examples.blockSignals(True); self.examples.clear()
        for example in entry['examples']: self.examples.addItem(example['label'])
        self.examples.blockSignals(False); self.load_example()

    def load_example(self, *unused):
        if self.current is None: return
        index = self.examples.currentIndex()
        if index >= 0: self.input.setPlainText(json.dumps(self.current['examples'][index]['context'], indent=2))

    def check_input(self):
        if self.current is None: return
        from .record_io import strict_json
        try: context = strict_json(self.input.toPlainText().encode())
        except (ValueError, UnicodeError) as exc:
            self.note.setText('Input could not be read: ' + str(exc)); return
        value = self.call('algo.find_applicable', {'algorithm': self.current['id'], 'context': context,
                                                  'expected_catalog_digest': self.catalog_digest})
        if value is None: return
        candidate = value['candidates'][0]; result = candidate['applicability']; state = result['state']
        title = {'MATCH_DECLARED_PROFILE': 'Fits the declared profile', 'MATCH_WITH_OBLIGATIONS': 'Fits · obligations remain',
                 'REJECTED_INPUT': 'Outside this profile', 'NEEDS_INPUT': 'More input needed',
                 'NOT_IMPLEMENTED': 'Reference only · no implementation', 'TASK_MISMATCH': 'Different task signature'}.get(state, state)
        text = [title, '', *result['reasons'], '', 'Outstanding obligations',
                *(result['obligations'] or ['No additional admission obligation listed. Runtime and evidence checks still apply.']), '',
                'Implementation: ' + candidate['implementation']['state'].lower().replace('_', ' '), '', value['notice']]
        self.report.setPlainText('\n'.join(text)); self.tabs.setCurrentWidget(self.report)
        self.note.setText(title + ' · no solver, job or grant issued')
