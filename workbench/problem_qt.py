"""The shared problem sheet inside Project Desk."""
from __future__ import annotations
from .text_prompts import writing_prompt
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPlainTextEdit, QScrollArea, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)
from .shell2 import button, call_write


def edit(label, height=72, readonly=False):
    widget = QPlainTextEdit(); widget.setAccessibleName(label); widget.setReadOnly(readonly); writing_prompt(widget, label)
    widget.setMinimumHeight(height); widget.setMaximumHeight(height + 40)
    return widget


def lines(widget):
    return [v.strip() for v in widget.toPlainText().splitlines() if v.strip()]


class ProblemPane(QWidget):
    def __init__(self, desk):
        super().__init__(); self.desk = desk; self.host = desk.host; self.current = None; self.pending_sources = []
        box = QVBoxLayout(self)
        row = QHBoxLayout(); self.problems = QComboBox(); self.problems.setAccessibleName('Saved problem')
        row.addWidget(self.problems, 1)
        refresh = button('Reopen', 'quiet'); refresh.clicked.connect(self.reload); row.addWidget(refresh)
        new = button('New problem', 'quiet'); new.clicked.connect(self.new); row.addWidget(new)
        lab = button('Start Clock Lab', 'primary'); lab.clicked.connect(self.start_lab); row.addWidget(lab); box.addLayout(row)
        self.message = QLabel('Keep the question, unknowns and evidence together.'); self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.PlainText); box.addWidget(self.message)
        self.problems.currentIndexChanged.connect(lambda: self.open(self.problems.currentData()))
        self.pages = QTabWidget(); box.addWidget(self.pages, 1)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); body = QWidget(); formbox = QVBoxLayout(body); scroll.setWidget(body)
        form = QFormLayout(); formbox.addLayout(form)
        self.name = QLineEdit(); self.name.setAccessibleName('Problem title'); form.addRow('Title', self.name)
        self.request = edit('Original request'); form.addRow('Original request', self.request)
        self.goals = edit('One goal per line'); form.addRow('Goals', self.goals)
        self.assumptions = edit('Declared assumptions'); form.addRow('Assumptions', self.assumptions)
        self.questions = edit('Unanswered questions'); form.addRow('Open questions', self.questions)
        self.candidates = edit('Candidate approaches'); form.addRow('Candidates', self.candidates)
        self.variables = QTableWidget(0, 6); self.variables.setAccessibleName('Typed variables and unknown values')
        self.variables.setHorizontalHeaderLabels(['Name', 'Type', 'Unit', 'State', 'Value', 'Basis'])
        self.variables.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.variables.horizontalHeader().setStretchLastSection(True); self.variables.setMinimumHeight(235)
        formbox.addWidget(self.variables)
        row = QHBoxLayout(); add = button('Add variable', 'quiet'); add.clicked.connect(lambda: self.add_variable()); row.addWidget(add)
        remove = button('Remove selected variable', 'quiet'); remove.clicked.connect(self.remove_variable); row.addWidget(remove)
        save = button('Save problem revision', 'primary'); save.clicked.connect(self.save); row.addWidget(save); formbox.addLayout(row)
        self.pages.addTab(scroll, 'Question')
        sources = QWidget(); sourcebox = QVBoxLayout(sources)
        form = QFormLayout(); self.copies = QComboBox(); self.copies.setAccessibleName('Source working copy'); form.addRow('Working copy', self.copies)
        self.path = QLineEdit(); writing_prompt(self.path, 'requirements.md'); self.path.setAccessibleName('Source path'); form.addRow('Text file', self.path)
        sourcebox.addLayout(form)
        add = button('Add source to next saved revision', 'quiet'); add.clicked.connect(self.add_source); sourcebox.addWidget(add)
        self.sources = QComboBox(); self.sources.setAccessibleName('Bound source'); sourcebox.addWidget(self.sources)
        row = QHBoxLayout(); remove = button('Remove selected source', 'quiet'); remove.clicked.connect(self.remove_source); row.addWidget(remove)
        read = button('Read selected source and keep result', 'primary'); read.clicked.connect(self.read_source); row.addWidget(read); sourcebox.addLayout(row)
        self.freshness = QLabel(); self.freshness.setWordWrap(True); self.freshness.setTextFormat(Qt.PlainText); sourcebox.addWidget(self.freshness)
        self.results = QComboBox(); self.results.setAccessibleName('Saved actual read result'); self.results.currentIndexChanged.connect(self.show_receipt); sourcebox.addWidget(self.results)
        self.result = QPlainTextEdit(); self.result.setReadOnly(True); self.result.setAccessibleName('Actual tool output'); sourcebox.addWidget(self.result, 1)
        self.pages.addTab(sources, 'Sources and results')
        self.tools = QPlainTextEdit(); self.tools.setReadOnly(True); self.tools.setAccessibleName('Relevant tools and readiness'); self.pages.addTab(self.tools, 'Tools')
        from .calculator_qt import CalculatorPane
        self.calculator = CalculatorPane(self)
        calculation_scroll=QScrollArea(); calculation_scroll.setWidgetResizable(True); calculation_scroll.setWidget(self.calculator)
        self.pages.addTab(calculation_scroll, 'Calculate')
        from .lab_qt import LabPane
        self.lab = LabPane(self)
        lab_scroll=QScrollArea(); lab_scroll.setWidgetResizable(True); lab_scroll.setWidget(self.lab)
        self.pages.addTab(lab_scroll, 'Investigate')
        from .joined_qt import JoinedPane
        self.joined=JoinedPane(self);self.pages.addTab(self.joined,'Connected work')
        self.reload()

    def call(self, op, args=None):
        response = call_write(self.host, op, args or {})
        if not response.get('ok'):
            self.message.setText((response.get('error') or {}).get('message', 'Operation did not complete.')); return None
        return response['result']

    def reload(self, selected=None):
        if not isinstance(selected, str): selected = self.current['id'] if self.current else None
        result = self.call('problems.list')
        if result is None: return
        self.problems.blockSignals(True); self.problems.clear(); self.problems.addItem('Choose a saved problem', None)
        for value in result['records']: self.problems.addItem(value['title'], value['id'])
        self.problems.setCurrentIndex(max(0, self.problems.findData(selected))); self.problems.blockSignals(False)
        copies = self.call('copies.list'); self.copies.clear()
        for value in (copies or {}).get('copies', []):
            if value.get('for_slate') and value.get('state') == 'WORKING': self.copies.addItem(value.get('name', value['work']), value['id'])
        self.open(self.problems.currentData())

    def open(self, ident):
        sheet = self.call('problems.get', {'id': ident}) if ident else None
        if ident and sheet is None: return
        self.current = sheet['problem'] if sheet else None; value = self.current or {}
        self.name.setText(value.get('title', '')); self.request.setReadOnly(bool(value)); self.request.setPlainText(value.get('original_request', ''))
        for widget, key in [(self.goals, 'goals'), (self.assumptions, 'assumptions'), (self.questions, 'questions'), (self.candidates, 'candidates')]:
            widget.setPlainText('\n'.join(value.get(key, [])))
        self.variables.setRowCount(0)
        for variable in value.get('variables', []): self.add_variable(variable)
        self.pending_sources = [{k: s[k] for k in ('copy', 'path', 'label')} for s in value.get('sources', [])]; self.show_sources()
        self.results.blockSignals(True); self.results.clear()
        for receipt in (sheet or {}).get('receipts', []):
            self.results.addItem(receipt['arguments']['path'] + ' · problem revision ' + str(receipt['problem_revision']), receipt)
        self.results.blockSignals(False); self.show_receipt()
        if sheet:
            self.message.setText('Revision %d · Unknown: %s' % (value['revision'], ', '.join(sheet['unknowns']) or 'none declared'))
            self.freshness.setText('Sources: ' + sheet['freshness']['state'].lower().replace('_', ' ') + '. Saved observations retain their original revision.')
            self.load_tools()
        else: self.freshness.clear(); self.tools.clear()
        self.calculator.reload()
        self.lab.reload()
        self.joined.reload()

    def new(self):
        self.problems.setCurrentIndex(0); self.open(None)
        if self.desk.assignment: self.request.setPlainText(self.desk.assignment['original_request'])
        self.message.setText('Save a question in the selected project, or independently when no project is selected.')

    def add_variable(self, value=None):
        value = value if isinstance(value, dict) else {'type': 'quantity', 'state': 'UNKNOWN'}
        row = self.variables.rowCount(); self.variables.insertRow(row)
        for column, key in enumerate(('name', 'type', 'unit', 'state', 'value', 'basis')):
            if key in ('type', 'state'):
                cell = QComboBox(); cell.addItems(['quantity', 'interval', 'boolean', 'text'] if key == 'type' else ['UNKNOWN', 'KNOWN'])
                cell.setCurrentText(value.get(key, 'UNKNOWN')); self.variables.setCellWidget(row, column, cell)
            else: self.variables.setItem(row, column, QTableWidgetItem(value.get(key, '')))

    def remove_variable(self):
        if self.variables.currentRow() >= 0: self.variables.removeRow(self.variables.currentRow())

    def values(self):
        result = []
        for row in range(self.variables.rowCount()):
            value = {key: self.variables.cellWidget(row, col).currentText() if col in (1, 3)
                else self.variables.item(row, col).text() for col, key in enumerate(('name', 'type', 'unit', 'state', 'value', 'basis'))}
            if value['state'] == 'UNKNOWN': value.pop('value')
            result.append(value)
        return result

    def arguments(self):
        return {'title': self.name.text(), 'goals': lines(self.goals), 'variables': self.values(),
            'assumptions': lines(self.assumptions), 'questions': lines(self.questions),
            'candidates': lines(self.candidates), 'sources': self.pending_sources}

    def bound(self):
        return {'id': self.current['id'], 'expected_revision': self.current['revision'],
                'expected_context_digest': self.current['context_digest']}

    def save(self):
        args = self.arguments()
        if self.current: args.update(self.bound()); op = 'problems.revise'
        else:
            args['request'] = self.request.toPlainText(); op = 'problems.create'
            if self.desk.project: args['project'] = self.desk.project['id']
            if self.desk.assignment: args['assignment'] = self.desk.assignment['id']
        result = self.call(op, args)
        if result: self.reload(result['id']); self.message.setText('Problem revision saved. Original words and earlier revisions remain available.')

    def show_sources(self):
        self.sources.clear()
        for source in self.pending_sources: self.sources.addItem(source['label'] + ' · ' + source['path'])

    def add_source(self):
        if not self.copies.currentData() or not self.path.text().strip(): self.message.setText('Select a delegated copy and its relative text path.'); return
        self.pending_sources.append({'copy': self.copies.currentData(), 'path': self.path.text().strip(), 'label': self.path.text().strip()[:200]})
        self.show_sources(); self.message.setText('Save the problem to bind this source revision.')

    def remove_source(self):
        if self.sources.currentIndex() >= 0: self.pending_sources.pop(self.sources.currentIndex()); self.show_sources()
        self.message.setText('Save the problem to keep this source selection.')

    def read_source(self):
        if not self.current: self.message.setText('Save the problem first.'); return
        original = {k: self.current[k] for k in ('title', 'goals', 'variables', 'assumptions', 'questions', 'candidates')}
        original['sources'] = [{k: s[k] for k in ('copy', 'path', 'label')} for s in self.current['sources']]
        if self.arguments() != original: self.message.setText('Save the problem changes before reading a source.'); return
        if self.sources.currentIndex() < 0: self.message.setText('Select a bound source.'); return
        action = self.call('problems.prepare', {**self.bound(), 'source': self.sources.currentIndex()})
        if not action: return
        result = self.call('problems.run', {'action': action['id']})
        if result:
            self.open(self.current['id']); self.pages.setCurrentIndex(1)
            self.message.setText('Actual working-copy read saved with its problem revision and source digest.')

    def show_receipt(self):
        value = self.results.currentData()
        if not value: self.result.setPlainText('No tool result has been kept for this problem yet.'); return
        self.result.setPlainText('work.read · %d bytes\nSource SHA-256: %s\nProblem revision: %d\nResult SHA-256: %s\n\n%s' %
            (value['snapshot']['bytes'], value['snapshot']['sha256'], value['problem_revision'], value['output_digest'], value['snapshot']['text']))

    def load_tools(self):
        value = self.call('problems.tools', {'id': self.current['id']})
        if not value: return
        rows = ['Relevant tools for this source-reading pass', '%d registered operations · %d job tools in the full catalogue' %
            (value['registered_operations'], value['registered_job_tools'])]
        for tool in value['operations']:
            a = tool['assessment']
            rows += ['', tool['description'], 'Input: ' + tool['input_description'], 'Output: ' + tool['output_description'],
                'Declared: %s · Installed: %s · Permitted: %s · Qualified: %s' %
                (a['declared']['state'], a['installed']['state'], a['permitted']['state'], a['qualified']['state'])]
        rows += ['', 'Read selected source uses the registered text reader. Broader model tool selection follows in a later pass.']
        self.tools.setPlainText('\n'.join(rows))

    def start_lab(self):
        parent = QFileDialog.getExistingDirectory(self, 'Choose a home-folder location for a new Clock Lab example', str(Path.home()))
        if not parent: return
        from . import clock_lab
        from .engine import engineering
        from .engineering_kernel import operator
        destination = Path(parent) / 'Clock_Lab_I01'
        try:
            kernel = engineering(self.host.root)
            from .working_copies import allowed_place
            allowed_place(kernel, str(destination))
            clock_lab.copy_inputs(destination)
            result = clock_lab.start(kernel, destination, operator())
        except (ValueError, OSError) as exc:
            self.message.setText(str(exc)); return
        self.desk.project = result['project']; self.desk.assignment = result['assignment']; self.desk.reload()
        self.reload(result['problem']['id']); self.message.setText('Clock Lab working copy ready. Read a source and keep the observed result.')
