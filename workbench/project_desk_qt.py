"""Project Desk: ordinary words first, exact Kernel records available to inspect."""
from __future__ import annotations
from .assistant_identity import named
from .text_prompts import writing_prompt
import json
import time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QScrollArea, QSpinBox, QSplitter,
    QTabWidget, QVBoxLayout, QWidget)
from .shell2 import button, call_write, role


def lines(widget):
    return [line.strip() for line in widget.toPlainText().splitlines() if line.strip()]


def editor(label, height=82, readonly=False):
    field = QPlainTextEdit(); field.setAccessibleName(label); field.setReadOnly(readonly); writing_prompt(field, label)
    field.setMinimumHeight(height); field.setMaximumHeight(height + 40)
    return field


class ProjectDeskTab(QWidget):
    def __init__(self, host):
        super().__init__(); self.host = host; self.project = None; self.assignment = None; self.sheet = None
        self.setObjectName('LibraryTab'); self.setProperty('ledgerRoom', True)
        outer = QVBoxLayout(self); outer.setContentsMargins(20, 18, 20, 16)
        # V-07: the title has its own line and the three words wrap onto a second row, so nothing is cut at 1366 px.
        self.heading_label = role(QLabel('Project Desk'), 'title'); outer.addWidget(self.heading_label)
        heading = QHBoxLayout(); heading.setSpacing(18); outer.addLayout(heading)
        refresh = button('Refresh', 'quiet'); refresh.clicked.connect(self.reload); heading.addWidget(refresh)
        changes = button('Review project changes', 'quiet'); changes.clicked.connect(lambda: __import__('workbench.change_sets_qt', fromlist=['show']).show(host)); heading.addWidget(changes)
        continuing=button('Continue an assignment','quiet');continuing.clicked.connect(lambda:__import__('workbench.continuing_work_qt',fromlist=['show']).show(host));heading.addWidget(continuing)
        heading.addStretch(1); self.heading_words = (refresh, changes, continuing)
        self.message = QLabel('Keep an idea, give it a project, and make the next assignment clear.')
        self.message.setWordWrap(True); self.message.setMaximumHeight(88); self.message.setTextFormat(Qt.PlainText); outer.addWidget(self.message)
        split = QSplitter(); outer.addWidget(split, 1)
        side = QWidget(); box = QVBoxLayout(side); box.setContentsMargins(0, 0, 12, 0)
        box.addWidget(role(QLabel('PROJECTS'), 'section'))
        self.projects = QListWidget(); self.projects.setAccessibleName('Projects'); box.addWidget(self.projects, 1)
        self.projects.itemClicked.connect(lambda item: self.open_project(item.data(Qt.UserRole)))
        self.project_title = QLineEdit(); self.project_title.setObjectName('ProjectTitle'); writing_prompt(self.project_title, 'New project title'); box.addWidget(self.project_title)  # a yellow passage (theme2, V-02)
        self.project_intent = editor('What is this project for?', 70); box.addWidget(self.project_intent)
        create = button('Create project', 'primary'); create.clicked.connect(self.create_project); box.addWidget(create)
        split.addWidget(side)
        self.tabs = QTabWidget(); split.addWidget(self.tabs); split.setStretchFactor(1, 1); split.setSizes([250, 800])
        self.build_ideas(); self.build_assignments(); self.build_links()
        from .slate_reasoning_qt import ReasoningPane
        self.reasoning = ReasoningPane(self); self.tabs.addTab(self.reasoning, named('Ask Stacy'))
        from .problem_qt import ProblemPane
        self.problem_pane = ProblemPane(self); self.tabs.addTab(self.problem_pane, 'Problem sheet'); self.reload()

    def title(self): return 'Project Desk'

    def info(self): return 'Ideas, projects, assignments and their review records'

    def ask(self, op, args=None):
        response = call_write(self.host, op, args or {})
        if not response.get('ok'):
            self.message.setText((response.get('error') or {}).get('message', 'That could not be saved.')); return None
        return response['result']

    def reload(self):
        records = self.ask('projects.list')
        if records is None: return
        self.projects.clear()
        for record in records['records']:
            item = QListWidgetItem(record['title']); item.setData(Qt.UserRole, record['id']); self.projects.addItem(item)
            if self.project and record['id'] == self.project['id']: self.projects.setCurrentItem(item)
        self.load_ideas()
        if self.project: self.open_project(self.project['id'])

    def open_project(self, ident):
        project = self.ask('projects.get', {'id': ident})
        if project is None: return
        self.project = project; self.message.setText(project['title'] + ' · ' + project['original_intent'][:240])
        self.project_links.setPlainText('\n\n'.join(link['role'].replace('_', ' ').title() + ': ' +
            (link.get('text') or link['source']['address']) for link in project['links']))
        self.collections.clear()
        for link in project['links']:
            source = link.get('source') or {}
            address = source.get('address') or ''
            if link['role'] == 'SOURCE' and address.startswith('collection:'):
                name = source['snapshot']['object']['name']
                self.collections.addItem(name, address.partition(':')[2])
        self.load_ideas(); self.assignment_list.blockSignals(True); self.assignment_list.clear()
        self.assignment_list.addItem('New assignment', None)
        records = self.ask('assignments.list', {'project': ident})
        for record in (records or {}).get('records', []):
            self.assignment_list.addItem(record['original_request'][:85], record['id'])
        index = self.assignment_list.findData(self.assignment['id']) if self.assignment else -1
        self.assignment_list.setCurrentIndex(max(0, index)); self.assignment_list.blockSignals(False)
        self.open_assignment(self.assignment_list.currentData())

    def create_project(self):
        result = self.ask('projects.create', {'title': self.project_title.text(), 'intent': self.project_intent.toPlainText()})
        if result:
            self.project_title.clear(); self.project_intent.clear(); self.project = result; self.assignment = None; self.reload()

    def build_ideas(self):
        tab = QWidget(); box = QVBoxLayout(tab)
        text = QLabel('Original words stay with the idea. A suggestion can be labelled as Graphite’s.'); text.setWordWrap(True); box.addWidget(text)
        self.idea_text = editor('An idea in your own words', 120); box.addWidget(self.idea_text)
        row = QHBoxLayout(); self.idea_origin = QComboBox(); self.idea_origin.setAccessibleName('Whose idea')  # V-21: a named choice box
        for label, value in [('My idea', 'HUMAN'), ('Graphite suggestion', 'SLATE'), ('Imported idea', 'IMPORTED')]: self.idea_origin.addItem(label, value)
        row.addWidget(self.idea_origin); capture = button('Keep idea', 'primary'); capture.clicked.connect(self.capture_idea); row.addWidget(capture); box.addLayout(row)
        self.ideas = QListWidget(); self.ideas.setAccessibleName('Recent ideas'); box.addWidget(self.ideas, 1)
        promote = button('Give selected idea a new project', 'quiet'); promote.clicked.connect(self.promote_idea); box.addWidget(promote)
        self.tabs.addTab(tab, 'Ideas')

    def load_ideas(self):
        self.ideas.clear(); records = self.ask('ideas.list')
        for idea in (records or {}).get('records', []):
            if idea.get('project') and (not self.project or idea['project'] != self.project['id']): continue
            item = QListWidgetItem(idea['text'][:220] + ('\nGraphite suggestion' if idea['origin'] == 'SLATE' else ''))
            item.setData(Qt.UserRole, idea); self.ideas.addItem(item)

    def capture_idea(self):
        args = {'text': self.idea_text.toPlainText(), 'origin': self.idea_origin.currentData()}
        if self.project: args['project'] = self.project['id']
        if self.ask('ideas.capture', args): self.idea_text.clear(); self.load_ideas(); self.message.setText('Idea kept, with its original words.')

    def promote_idea(self):
        item = self.ideas.currentItem()
        if not item: self.message.setText('Select an idea first.'); return
        idea = item.data(Qt.UserRole)
        title, ok = QInputDialog.getText(self, 'Give this idea a project', 'Project title:', text=idea['text'].splitlines()[0][:100])
        if not ok: return
        result = self.ask('ideas.promote', {'id': idea['id'], 'expected_revision': idea['revision'], 'title': title})
        if result: self.project = result['project']; self.assignment = None; self.reload(); self.tabs.setCurrentIndex(1)

    def build_assignments(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget(); box = QVBoxLayout(body); scroll.setWidget(body); self.tabs.addTab(scroll, 'Assignments')
        self.assignment_list = QComboBox(); self.assignment_list.setAccessibleName('Assignment'); box.addWidget(self.assignment_list)
        self.assignment_list.currentIndexChanged.connect(lambda: self.open_assignment(self.assignment_list.currentData()))
        form = QFormLayout(); box.addLayout(form)
        self.request = editor('Original request', 90); form.addRow('Original request', self.request)
        self.interpretation = editor('What this assignment means', 85); form.addRow('Interpretation', self.interpretation)
        self.output = QLineEdit(); self.output.setAccessibleName('Intended output'); form.addRow('Intended output', self.output)
        self.inputs = editor('One source address per line', 65); form.addRow('Input addresses', self.inputs)
        self.questions = editor('Questions that still need an answer', 60); form.addRow('Open questions', self.questions)
        self.success = editor('One success condition per line', 60); form.addRow('Success', self.success)
        self.stop = editor('When to stop or ask for help', 60); form.addRow('Stop when', self.stop)
        save = button('Save assignment', 'primary'); save.clicked.connect(self.save_assignment); box.addWidget(save)
        box.addWidget(role(QLabel('PLAN'), 'section'))
        label = QLabel('Freezing a plan records what is proposed. It does not start work or grant permission.'); label.setWordWrap(True); box.addWidget(label)
        plan = QFormLayout(); box.addLayout(plan)
        self.language = QComboBox(); self.language.addItem('Everyday query', 'QUERY'); self.language.addItem('Engineering staC', 'STAC'); plan.addRow('Language', self.language)
        self.program = editor('A query or staC program to preserve', 70); plan.addRow('Proposed program', self.program)
        self.seconds = QSpinBox(); self.seconds.setRange(1, 86400); self.seconds.setValue(300); plan.addRow('Time limit, seconds', self.seconds)
        self.steps = QSpinBox(); self.steps.setRange(1, 200); self.steps.setValue(10); plan.addRow('Step limit', self.steps)
        freeze = button('Freeze plan', 'quiet'); freeze.clicked.connect(self.freeze_plan); box.addWidget(freeze)
        self.history = editor('Plan and review status', 130, True); box.addWidget(self.history)
        inspect = button('Inspect saved record and history', 'quiet'); inspect.clicked.connect(self.inspect); box.addWidget(inspect)
        box.addWidget(role(QLabel('REVIEW'), 'section'))
        review = QFormLayout(); box.addLayout(review)
        self.review_decision = QComboBox()
        for label, value in [('Accept these outputs', 'ACCEPT'), ('Changes needed', 'CHANGES_REQUESTED'), ('Defer', 'DEFER')]: self.review_decision.addItem(label, value)
        review.addRow('Decision', self.review_decision)
        self.review_outputs = editor('One output address per line', 60); review.addRow('Outputs', self.review_outputs)
        self.review_note = editor('What you reviewed and why', 70); review.addRow('Review note', self.review_note)
        self.unresolved = editor('Remaining questions, one per line', 60); review.addRow('Still unresolved', self.unresolved)
        keep = button('Keep review', 'primary'); keep.clicked.connect(self.keep_review); box.addWidget(keep); box.addStretch(1)

    def open_assignment(self, ident):
        previous = self.assignment['id'] if self.assignment else None
        self.sheet = self.ask('assignments.reopen', {'id': ident}) if ident else None
        self.assignment = self.sheet['assignment'] if self.sheet else None
        if previous != ident:
            self.review_outputs.clear(); self.review_note.clear(); self.unresolved.clear()
        a = self.assignment or {}; self.request.setReadOnly(bool(a)); self.request.setPlainText(a.get('original_request', ''))
        self.interpretation.setPlainText(a.get('interpretation', '')); self.output.setText(a.get('intended_output', ''))
        self.inputs.setPlainText('\n'.join(source['address'] for source in a.get('inputs', [])))
        for field, key in [(self.questions, 'questions'), (self.success, 'success'), (self.stop, 'stop')]: field.setPlainText('\n'.join(a.get(key, [])))
        if not a: self.program.setPlainText('@project:' + self.project['id'] + ' | select title' if self.project else '')
        if not self.sheet: self.history.clear(); return
        plans = self.sheet['plans']; active = next((p for p in plans if p['id'] == a['plan']), None)
        if active: self.program.setPlainText(active.get('program') or ''); self.language.setCurrentIndex(0 if active['language'] == 'QUERY' else 1)
        summary = ['Revision %d · %s' % (a['revision'], a['state'].lower()),
            '%d saved plans · %d reviews' % (len(plans), len(self.sheet['reviews'])),
            'Inputs: ' + self.sheet['freshness']['state'].replace('_', ' ').lower(),
            'Reopened without execution.']
        if active: summary += ['Requested operations: ' + ', '.join(row['operation'] for row in active['operations']),
                              'Limits: %d seconds, %d steps; network off.' % (active['budget']['seconds'], active['budget']['steps'])]
        if self.sheet['unresolved']: summary.append('Needs attention: ' + ', '.join(self.sheet['unresolved']).replace('_', ' ').lower())
        if self.sheet['unresolved_questions']: summary.append('Open questions: ' + '; '.join(self.sheet['unresolved_questions']))
        self.history.setPlainText('\n'.join(summary))

    def save_assignment(self):
        if not self.project: self.message.setText('Create or select a project first.'); return
        args = {'interpretation': self.interpretation.toPlainText(), 'intended_output': self.output.text(),
            'inputs': lines(self.inputs), 'questions': lines(self.questions), 'success': lines(self.success), 'stop': lines(self.stop)}
        if self.assignment: args.update(id=self.assignment['id'], expected_revision=self.assignment['revision']); op = 'assignments.revise'
        else: args.update(project=self.project['id'], request=self.request.toPlainText()); op = 'assignments.create'
        result = self.ask(op, args)
        if result: self.assignment = result; self.open_project(self.project['id']); self.message.setText('Assignment saved. Earlier interpretations stay in its history.')

    def freeze_plan(self):
        if not self.assignment: self.message.setText('Save the assignment first.'); return
        if (self.interpretation.toPlainText() != self.assignment['interpretation'] or
            self.output.text() != self.assignment['intended_output'] or
            lines(self.inputs) != [b['address'] for b in self.assignment['inputs']] or
            any(lines(field) != self.assignment[key] for field, key in
                [(self.questions, 'questions'), (self.success, 'success'), (self.stop, 'stop')])):
            self.message.setText('Save your assignment changes before freezing the plan.'); return
        from .engineering_kernel import CAPABILITIES
        from .project_desk import DEFAULT_BUDGET
        language = self.language.currentData(); program = self.program.toPlainText()
        native = self.ask('language.parse' if language == 'QUERY' else 'stac.compile', {'text' if language == 'QUERY' else 'program': program})
        if native is None: return
        if language == 'QUERY':
            operations = {native['call']['operation']}
            for transform in native['transforms']:
                if transform['kind'] in ('join', 'missing'):
                    other = self.ask('language.parse', {'text': transform['source']})
                    if other is None: return
                    operations.add(other['call']['operation'])
        elif native['kind'] == 'ENGINEERING': operations = {n['op'] for n in native['ir']['nodes'] if n['op'] in CAPABILITIES}
        else: operations = {native['ir']['operation']}
        args = {'id': self.assignment['id'], 'expected_revision': self.assignment['revision'], 'language': language,
            'program': program, 'budget': {**DEFAULT_BUDGET, 'seconds': self.seconds.value(), 'steps': self.steps.value()},
            'permissions': {'operations': sorted(operations), 'effects': sorted({CAPABILITIES[op] for op in operations}),
                'working_roots': [], 'network': False, 'expires': time.time() + 86400}}
        result = self.ask('assignments.plan', args)
        if result: self.open_assignment(self.assignment['id']); self.message.setText('Plan frozen for 24 hours. No work was started.')

    def keep_review(self):
        if not self.assignment or not self.assignment['plan']: self.message.setText('Freeze a plan before reviewing its outputs.'); return
        result = self.ask('assignments.review', {'id': self.assignment['id'], 'expected_revision': self.assignment['revision'],
            'plan': self.assignment['plan'], 'decision': self.review_decision.currentData(), 'note': self.review_note.toPlainText(),
            'outputs': lines(self.review_outputs), 'unresolved': lines(self.unresolved)})
        if result: self.open_assignment(self.assignment['id']); self.message.setText('Review kept with frozen outputs. This records your judgment.')

    def inspect(self):
        if not self.assignment: return
        self.sheet = self.ask('assignments.reopen', {'id': self.assignment['id']})
        if not self.sheet: return
        dialog = QDialog(self); dialog.setWindowTitle('Assignment record and history'); dialog.resize(850, 650)
        box = QVBoxLayout(dialog); text = QPlainTextEdit(); text.setReadOnly(True)
        text.setPlainText(json.dumps(self.sheet, ensure_ascii=False, indent=2)); box.addWidget(text); dialog.exec()

    def build_links(self):
        tab = QWidget(); box = QVBoxLayout(tab)
        self.project_links = editor('Project sources, questions, decisions and outputs', 240, True); box.addWidget(self.project_links, 1)
        row = QHBoxLayout()
        self.collections = QComboBox()
        self.collections.setAccessibleName('Project source collections')
        self.collections.setPlaceholderText('Project source collections')
        row.addWidget(self.collections, 1)
        attach = button('Attach collection…', 'quiet'); attach.clicked.connect(self.attach_collection); row.addWidget(attach)
        open_collection = button('Open collection', 'quiet'); open_collection.clicked.connect(self.open_collection); row.addWidget(open_collection)
        box.addLayout(row)
        self.link_role = QComboBox()
        for role_name in ('SOURCE', 'QUESTION', 'DECISION', 'ALTERNATIVE', 'TASK', 'WORKING_COPY', 'OUTPUT'): self.link_role.addItem(role_name.replace('_', ' ').title(), role_name)
        box.addWidget(self.link_role)
        self.link_address = QLineEdit(); writing_prompt(self.link_address, 'Source address, or leave empty for a written note'); box.addWidget(self.link_address)
        self.link_text = editor('A question, decision or alternative', 85); box.addWidget(self.link_text)
        keep = button('Keep project link', 'primary'); keep.clicked.connect(self.keep_link); box.addWidget(keep); self.tabs.addTab(tab, 'Project notes')

    def attach_collection(self):
        if not self.project:
            self.message.setText('Select a project first.')
            return
        result = self.ask('intake.namespaces')
        if result is None:
            return
        rows = [row for row in result['namespaces'] if self.collections.findData(row['id']) < 0]
        if not rows:
            self.message.setText('Review incoming material in Intake to add another source collection.')
            return
        labels = [f"{row['name']} · {row['id'][:8]}" for row in rows]
        choice, ok = QInputDialog.getItem(self, 'Attach source collection', 'Collection', labels, editable=False)
        if ok:
            ident = rows[labels.index(choice)]['id']
            result = self.ask('projects.link', {'id': self.project['id'], 'expected_revision': self.project['revision'],
                'role': 'SOURCE', 'address': 'collection:' + ident})
            if result:
                self.open_project(result['id'])
                self.collections.setCurrentIndex(self.collections.findData(ident))

    def open_collection(self):
        ident = self.collections.currentData()
        if ident and self.project:
            tab = self.host.ledger_bridge.show_references()
            tab.open_collection(ident, self.project['id'])

    def keep_link(self):
        if not self.project: self.message.setText('Select a project first.'); return
        args = {'id': self.project['id'], 'expected_revision': self.project['revision'], 'role': self.link_role.currentData()}
        if self.link_address.text().strip(): args['address'] = self.link_address.text().strip()
        else: args['text'] = self.link_text.toPlainText()
        if self.ask('projects.link', args): self.link_address.clear(); self.link_text.clear(); self.open_project(self.project['id'])


def show(host):
    host._close_start()
    for i in range(host.tabs.count()):
        tab = host.tabs.widget(i)
        if isinstance(tab, ProjectDeskTab): host.tabs.setCurrentWidget(tab); tab.reload(); return tab
    tab = ProjectDeskTab(host); host.tabs.addTab(tab, tab.title()); host.tabs.setCurrentWidget(tab); return tab
