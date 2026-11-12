"""Concrete desktop front door for the shared bounded external-agent services."""
from .text_prompts import writing_prompt
import json
import uuid
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QPlainTextEdit, QTabWidget, QMessageBox)
from .engineering_kernel import Principal, operator


class ExternalClipTasks(QWidget):
    def __init__(self, host, kernel):
        super().__init__()
        self.host, self.kernel, self.selected = host, kernel, None
        self.actor = Principal('desktop-clip', frozenset({'read', 'candidate', 'execute'}))
        layout = QVBoxLayout(self)
        label = QLabel('GRAPHITE · DELEGATED AI TASK\nInspect → reproduce → propose → authorize exact test → review. Your chosen external agent supplies the reasoning; Graphite records and checks its work. No provider is called automatically.')
        label.setWordWrap(True)
        layout.addWidget(label)
        self.goal = QLineEdit()
        writing_prompt(self.goal, 'One concrete, testable ARC-OS defect')
        self.path = QLineEdit('software/arcos/src/host.c')
        layout.addWidget(self.goal)
        layout.addWidget(self.path)
        self.status = QLabel('Accepted source stays unchanged until independent owner acceptance.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        row = QHBoxLayout()
        for name, fn in [('Prepare isolated task', self.prepare), ('Refresh tasks', self.refresh)]:
            b = QPushButton(name); b.clicked.connect(fn); row.addWidget(b)
        layout.addLayout(row)
        self.tasks = QTreeWidget()
        self.tasks.setHeaderLabels(['State', 'Goal', 'Task ID'])
        self.tasks.setMaximumHeight(145)
        self.tasks.itemSelectionChanged.connect(self.select)
        layout.addWidget(self.tasks)
        self.views = QTabWidget()
        self.context = QPlainTextEdit(); self.context.setReadOnly(True)
        self.diff = QPlainTextEdit(); self.diff.setReadOnly(True)
        self.record = QPlainTextEdit(); self.record.setReadOnly(True)
        self.proposal = QPlainTextEdit()
        writing_prompt(self.proposal, 'Paste an agent proposal JSON: binding, agent, explanation, patch {path, sha256, content}. Runtime names are declarations, not authenticated provider identities.')
        for label, widget in [('Agent handoff', self.context), ('Source diff', self.diff), ('Tests / task', self.record), ('Agent proposal', self.proposal)]:
            self.views.addTab(widget, label)
        layout.addWidget(self.views, 1)
        for buttons in [
            [('Read handoff', self.inspect), ('Run baseline', lambda: self.test('baseline')), ('Attach agent proposal', self.propose)],
            [('Authorize reviewed execution', self.authorize), ('Run candidate', lambda: self.test('candidate')), ('Submit for source review', self.finish)]]:
            row = QHBoxLayout()
            for label, fn in buttons:
                b = QPushButton(label); b.clicked.connect(fn); row.addWidget(b)
            layout.addLayout(row)
        self.refresh()

    def call(self, op, params, actor=None):
        r = self.kernel.dispatch(op, params, actor or operator())
        if not r['ok']:
            self.status.setText(r['error']['message']); return None
        self.status.setText(op + ' completed · no source acceptance')
        return r['result']

    def prepare(self):
        r = self.call('clip.prepare', dict(goal=self.goal.text(), path=self.path.text().strip(), request_key=uuid.uuid4().hex), self.actor)
        if r:
            self.selected = r['id']; self.refresh(); self.inspect()

    def refresh(self):
        self.tasks.blockSignals(True); self.tasks.clear()
        for j in self.kernel.listing('jobs'):
            if j['tool'] == 'clip.external':
                item = QTreeWidgetItem([j['state'], j['goal'], j['id']]); item.setData(0, Qt.UserRole, j['id'])
                self.tasks.addTopLevelItem(item)
                if j['id'] == self.selected: item.setSelected(True)
        self.tasks.blockSignals(False)
        self.tasks.resizeColumnToContents(0)

    def select(self):
        items = self.tasks.selectedItems()
        if items:
            self.selected = items[0].data(0, Qt.UserRole); self.inspect()

    def inspect(self):
        if not self.selected: return
        r = self.call('clip.context', {'id': self.selected})
        status = self.call('clip.inspect', {'id': self.selected})
        if r and status:
            self.context.setPlainText(json.dumps(r, indent=2))
            d = self.call('candidates.diff', {'id': status['task']['candidate']})
            self.diff.setPlainText('\n'.join(x['diff'] for x in d['changes']) or 'No proposal yet.')
            self.record.setPlainText(json.dumps(status, indent=2))
            self.views.setCurrentWidget(self.context)

    def propose(self):
        if not self.selected: return
        try: proposal = json.loads(self.proposal.toPlainText())
        except ValueError as e: self.status.setText(str(e)); return
        j = self.kernel.record('jobs', self.selected)
        # The local OS operator explicitly delegates this task's originating
        # identity. Network callers cannot select an identity in parameters.
        actor = Principal(j['owner'], self.actor.scopes, tuple(j['scope']), ('arcos.test',))
        if self.call('clip.propose', {'id': self.selected, 'proposal': proposal}, actor):
            self.inspect(); self.views.setCurrentWidget(self.diff); self.refresh()

    def test(self, phase):
        if not self.selected: return
        r = self.call('clip.test', {'id': self.selected, 'phase': phase})
        if r:
            self.record.setPlainText(json.dumps(r, indent=2)); self.views.setCurrentWidget(self.record)
            self.status.setText('Follow job ' + r['id'] + ' in Jobs; refresh this task for evidence.')

    def authorize(self):
        if not self.selected: return
        j = self.kernel.record('jobs', self.selected)
        self.inspect(); self.views.setCurrentWidget(self.diff)
        if QMessageBox.question(self, 'Exact native-code execution', 'Review this diff first. The fixed test runs native candidate code with your OS account, without an OS sandbox. Authorize only this revision?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.call('candidates.authorize_execution', {'id': j['candidate']})

    def finish(self):
        if self.selected and self.call('clip.finish', {'id': self.selected}):
            self.inspect(); self.views.setCurrentWidget(self.record); self.refresh()
