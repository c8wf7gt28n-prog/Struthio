"""Ask Slate from Project Desk, with source selection and provisional prose visible."""
from __future__ import annotations
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QFrame, QHBoxLayout, QLayout, QLineEdit,
    QPlainTextEdit, QScrollArea, QSpinBox, QVBoxLayout, QWidget)
from .register_tabs import ServiceTab
from .shell2 import button, call_write


class ReasoningPane(ServiceTab):
    def __init__(self, desk):
        super().__init__(desk.host)
        self.desk = desk
        self.context = self.job = self.record = None
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        body = QWidget()
        box = QVBoxLayout(body)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        scroll.setWidget(body)
        self.outer.addWidget(scroll)
        self.notice = self.status
        self.notice.setTextFormat(Qt.TextFormat.PlainText)
        self.notice.setText('Prepare evidence from this assignment and any extra sources.')
        box.addWidget(self.notice)
        self.question = QPlainTextEdit(); writing_prompt(self.question, 'What would you like Graphite to help with?'); self.question.setAccessibleName('Question for Graphite'); self.question.setFixedHeight(54); box.addWidget(self.question)
        form = QFormLayout(); box.addLayout(form)
        self.addresses = QPlainTextEdit(); self.addresses.setFixedHeight(75); writing_prompt(self.addresses, 'Source addresses or namespace:ID, one per line'); form.addRow('Extra sources', self.addresses)
        self.budget = QSpinBox(); self.budget.setRange(512, 32000); self.budget.setValue(6000); self.budget.setSingleStep(512); form.addRow('Context characters', self.budget)
        self.task = QComboBox()
        for label, value in [('Answer from sources', 'ANSWER'), ('Suggest staC reads', 'PLAN'), ('Draft exact text edit', 'EDIT'), ('Clarify the request', 'CLARIFY')]: self.task.addItem(label, value)
        form.addRow('Help with', self.task)
        self.target = QLineEdit(); writing_prompt(self.target, 'For an edit: files:NAME of an input already selected'); form.addRow('Edit target', self.target)
        self.task.currentIndexChanged.connect(lambda: form.setRowVisible(self.target, self.task.currentData() == 'EDIT'))
        form.setRowVisible(self.target, False)
        self.tokens = QSpinBox(); self.tokens.setRange(64, 4096); self.tokens.setSingleStep(64); self.tokens.setValue(512); form.addRow('Output token limit', self.tokens)

        row = QHBoxLayout()
        self.calculate = QCheckBox('Include an exact calculation')
        row.addWidget(self.calculate)
        self.calc_details = button('Show calculation inputs', 'quiet')
        self.calc_details.setCheckable(True)
        self.calc_details.hide()
        row.addWidget(self.calc_details)
        row.addStretch()
        box.addLayout(row)
        calc = QWidget()
        fields = QFormLayout(calc)
        fields.setContentsMargins(0, 0, 0, 0)
        self.expression = QLineEdit()
        writing_prompt(self.expression, 'voltage * current')
        fields.addRow('Expression', self.expression)
        self.inputs = QPlainTextEdit()
        self.inputs.setFixedHeight(58)
        writing_prompt(self.inputs, 'voltage = 12 V\ncurrent = files:rail.txt | 200 mA')
        self.inputs.setToolTip('Enter one named quote per line. Prefix a quote with a source address and | to choose its source.')
        fields.addRow('Source quotes', self.inputs)
        self.unit = QLineEdit()
        writing_prompt(self.unit, 'W')
        fields.addRow('Result unit', self.unit)
        self.condition = QLineEdit()
        writing_prompt(self.condition, 'Use the same operating condition for both inputs')
        fields.addRow('Condition', self.condition)
        box.addWidget(calc)
        calc.hide()
        self.calc_details.toggled.connect(calc.setVisible)
        self.calc_details.toggled.connect(
            lambda visible: self.calc_details.setText('Hide calculation inputs' if visible else 'Show calculation inputs'))
        self.calculate.toggled.connect(self.calc_details.setVisible)
        self.calculate.toggled.connect(self.calc_details.setChecked)

        row = QHBoxLayout(); collect = button('Prepare evidence', 'quiet'); collect.clicked.connect(self.assemble); row.addWidget(collect)
        ask = button('Ask local Graphite', 'primary'); ask.clicked.connect(self.ask); row.addWidget(ask)
        stop = button('Stop this reply', 'quiet'); stop.clicked.connect(self.stop); row.addWidget(stop); box.addLayout(row)
        self.sources = QPlainTextEdit(); self.sources.setReadOnly(True); self.sources.setAccessibleName('Prepared evidence and source gaps'); self.sources.setMinimumHeight(120); box.addWidget(self.sources, 2)
        row = QHBoxLayout()
        self.passages = QComboBox()
        self.passages.setAccessibleName('Included and omitted source passages')
        self.passages.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.passages.setPlaceholderText('Choose a source passage')
        row.addWidget(self.passages, 1)
        read = button('Read passage', 'quiet'); read.clicked.connect(self.read_passage); row.addWidget(read)
        focus = button('Focus next turn', 'quiet'); focus.clicked.connect(self.focus_passage); row.addWidget(focus)
        box.addLayout(row)
        self.reply = QPlainTextEdit(); self.reply.setReadOnly(True); self.reply.setAccessibleName('Graphite answer or draft'); box.addWidget(self.reply, 1)
        writing_prompt(self.reply, 'A local model reply will appear here.')
        inspect = button('Inspect context and result', 'quiet'); inspect.clicked.connect(self.inspect); box.addWidget(inspect)
        row = QHBoxLayout(); use = button('Use this interpretation', 'quiet'); use.clicked.connect(self.use_interpretation); row.addWidget(use)
        keep = button('Keep reply link with project', 'quiet'); keep.clicked.connect(self.keep_reply); row.addWidget(keep); box.addLayout(row)
        self.timer = QTimer(self); self.timer.setInterval(350); self.timer.timeout.connect(self.poll)

    def call(self, op, args):
        response = call_write(self.host, op, args)
        if not response.get('ok'): self.notice.setText((response.get('error') or {}).get('message', 'That could not be read.')); return None
        return response['result']

    def source_signature(self):
        assignment = self.desk.assignment or {}
        project = self.desk.project or {}
        calculation = (self.expression.text(), self.inputs.toPlainText(), self.unit.text(), self.condition.text())
        return (project.get('id'), project.get('revision'), assignment.get('id'), assignment.get('revision'),
                self.addresses.toPlainText(), calculation if self.calculate.isChecked() else None)

    def signature(self):
        return self.source_signature(), self.question.toPlainText(), self.budget.value()

    def calculation(self):
        expression = self.expression.text().strip()
        inputs = []
        for line in self.inputs.toPlainText().splitlines():
            if not line.strip():
                continue
            symbol, equals, quote = line.partition('=')
            if not equals or not symbol.strip() or not quote.strip():
                raise ValueError('Enter source quotes as name = exact quote.')
            source, bar, text = quote.partition('|')
            row = {'symbol': symbol.strip(), 'quote': (text if bar else source).strip()}
            if bar:
                row['address'] = source.strip()
            inputs.append(row)
        if not expression or not inputs:
            raise ValueError('Enter an expression and its named source quotes.')
        calculation = {'expression': expression, 'inputs': inputs}
        if self.unit.text().strip():
            calculation['output_unit'] = self.unit.text().strip()
        if self.condition.text().strip():
            calculation['assumptions'] = [self.condition.text().strip()]
        return calculation

    def prepare(self, op, args):
        signature = self.signature()

        def prepared(context):
            if signature != self.signature():
                self.notice.setText('The question or sources changed. Prepare the current evidence again.')
                return
            self.context = context
            self._signature = signature
            self.record = None
            self.calc_details.setChecked(False)
            self.show_evidence(context)
            self.notice.setText('Evidence prepared locally. Review its inputs and conditions below.')
            self.reply.clear()

        self.notice.setText('Reading sources and preparing evidence…')
        super().call(op, args, prepared)

    @property
    def preparing(self):
        return bool(self.workers)

    def busy(self):
        if self.job:
            self.notice.setText('Finish or stop the current reply first.')
        elif self.preparing:
            self.notice.setText('Evidence preparation is still running.')
        return bool(self.job or self.preparing)

    def assemble(self):
        if self.busy():
            return
        sources = [line.strip() for line in self.addresses.toPlainText().splitlines() if line.strip()]
        args = {'question': self.question.toPlainText(), 'char_budget': self.budget.value(),
                'addresses': [line for line in sources if not line.startswith('namespace:')],
                'namespaces': [line.partition(':')[2].strip() for line in sources if line.startswith('namespace:')]}
        if self.calculate.isChecked():
            try:
                args['calculations'] = [self.calculation()]
            except ValueError as exc:
                self.notice.setText(str(exc))
                return
        if self.desk.assignment: args['assignment'] = self.desk.assignment['id']
        elif self.desk.project: args['project'] = self.desk.project['id']
        self.prepare('slate.context.create', args)

    def show_evidence(self, context):
        prepared = context.get('preparation', {})
        selected = {p['id'] for p in context['selection']['selected']}
        lines = []
        for calculation in prepared.get('calculations', []):
            if calculation['state'] != 'EXACT':
                lines.extend('Needs input · ' + gap for gap in calculation['gaps'])
                continue
            result = calculation['result']['outputs'][0]['value']
            if isinstance(result, dict):
                rendered = f'{result["decimal"]} {result["unit"]}'
                if result['rational'] != result['decimal']:
                    rendered += f'  ({result["rational"]} exact)'
            else:
                rendered = 'true' if result else 'false'
            lines.append(f'{calculation["expression"]} = {rendered} · exact under the declared inputs')
            lines.append('Inputs · ' + ', '.join(row['symbol'] + ' = ' + row['quote'] for row in calculation['inputs']))
            lines.extend('Condition · ' + condition for condition in calculation['assumptions'])
            if set(calculation['source_ids']) - selected:
                lines.append('Outside the current passage budget · increase context to include its sources.')
        if prepared.get('facts'):
            lines.append(f'{len(prepared["facts"])} reviewed source facts · original conditions retained')
        if prepared.get('quantities'):
            lines.append('Source quantities to interpret · ' + ', '.join(dict.fromkeys(row['text'] for row in prepared['quantities'])))
        if prepared.get('tools'):
            lines.append('Relevant reads · ' + ', '.join(row['operation'] for row in prepared['tools']))
        lines.append('Selected %d passages · %d characters' % (len(selected), context['selection']['characters_used']))
        for p in context['selection']['selected']: lines += [p['title'] + ' · ' + p['kind'].replace('_', ' ').lower(), '  ' + p['why']]
        for p in context['selection']['excluded']: lines.append('Excluded: ' + p['title'] + ' · ' + p['reason'].replace('_', ' ').lower())
        for p in context['unavailable']: lines.append('Unavailable: ' + str(p.get('address', p.get('namespace', 'source'))) + ' · ' + str(p.get('reason', p.get('state', 'not available'))))
        self.sources.setPlainText('\n'.join(lines))
        self.show_passages(context, selected)

    def show_passages(self, context, selected):
        self.passages.clear()
        for source in context['corpus']:
            if source.get('binding') is None:
                continue
            state = 'Included' if source['id'] in selected else 'Omitted'
            locator = source['locator']
            page = locator.get('page') or locator.get('first_line')
            location = f' · {locator["kind"].replace("_", " ").lower()} {page}' if page else ''
            self.passages.addItem(f'{state} · {source["title"]}{location}', source['id'])
        self.passages.setCurrentIndex(-1)

    def read_passage(self):
        if not self.context or not self.passages.currentData() or self.preparing:
            return

        def opened(result):
            source = result['source']
            self.notice.setText('Passage read from the current source revision.')
            dialog = QDialog(self)
            dialog.setWindowTitle(source['title'])
            dialog.resize(650, 420)
            box = QVBoxLayout(dialog)
            passage = QPlainTextEdit()
            passage.setReadOnly(True)
            passage.setPlainText(json.dumps(source['locator'], ensure_ascii=False) + '\n\n' + source['text'])
            box.addWidget(passage)
            dialog.exec()

        self.notice.setText('Checking the passage against its source…')
        super().call('slate.context.passage', {'id': self.context['id'], 'passage': self.passages.currentData()}, opened)

    def focus_passage(self):
        if self.busy() or not self.context or not self.passages.currentData():
            return
        if self.source_signature() != self._signature[0]:
            self.notice.setText('Prepare the changed inputs before focusing a passage.')
            return
        self.prepare('slate.context.focus', {'id': self.context['id'], 'passage': self.passages.currentData(),
            'question': self.question.toPlainText(), 'char_budget': self.budget.value()})

    def ask(self):
        if self.busy():
            return
        if not self.context or self._signature != self.signature(): self.notice.setText('Prepare the current question and sources first.'); return
        args = {'context': self.context['id'], 'task': self.task.currentData(), 'max_tokens': self.tokens.value()}
        if args['task'] == 'EDIT': args['target_address'] = self.target.text().strip()
        if args['task'] == 'ANSWER':
            args['follow_up'] = True
        result = self.call('slate.ask', args)
        if result is None: return
        self.job = result['id']; self.reply.clear(); self.notice.setText('Local Graphite is reading. Incoming text is a draft until checks finish.'); self.timer.start()

    def poll(self):
        if not self.job: self.timer.stop(); return
        progress = self.call('slate.progress', {'job': self.job})
        if progress is None: self.timer.stop(); return
        if progress.get('display_text'): self.reply.setPlainText('Draft — not yet checked\n\n' + progress['display_text'])
        if progress.get('job_state', progress['state']) not in ('Completed', 'Failed', 'Cancelled', 'Interrupted'): return
        ident = self.job; self.job = None; self.timer.stop()
        value = self.call('slate.result', {'job': ident})
        if not value or value['state'] != 'Completed':
            self.reply.setPlainText('No validated result was returned.\n' + str((value or {}).get('error') or (value or {}).get('state', 'Unavailable')))
            self.notice.setText('Stopped. No action or edit was applied.'); return
        result = value['result'] or {}; self.record = result; candidate = result.get('candidate', {})
        text = candidate.get('text', '')
        if candidate.get('interpretation'): text += '\n\nInterpretation: ' + candidate['interpretation']
        if candidate.get('questions'): text += '\n\nQuestions:\n' + '\n'.join(candidate['questions'])
        for action in candidate.get('actions', []): text += '\n\nSuggested read, not run:\n' + action['operation'] + ' ' + json.dumps(action['arguments'], ensure_ascii=False)
        validation = result.get('validation', {})
        self.show_passages(self.context, {p['id'] for p in result.get('provided', [])})
        follow_up = validation.get('follow_up', {})
        if follow_up.get('question'):
            text += '\n\nNext question\n' + follow_up['question']
        if follow_up.get('source'):
            source = follow_up['source']
            text += '\n\nRequested passage\n' + source['title']
            self.passages.setCurrentIndex(self.passages.findData(source['id']))
        for citation in validation.get('citations', []): text += '\n\n[' + citation['alias'] + '] ' + citation['title'] + ' · ' + json.dumps(citation['locator'], ensure_ascii=False)
        if validation.get('proposed_text') is not None: text += '\n\nDraft only — no file changed:\n' + validation['proposed_text']
        self.reply.setPlainText(text or 'Inspect the result for details.')
        self.notice.setText('Complete response and source checks passed. Model-generated content still needs your judgment.')
        extra = [p for p in result.get('excluded', []) if p.get('reason') == 'MEASURED_TOKEN_BUDGET']
        if extra: self.sources.appendPlainText('\nExcluded by the model token budget:\n' + '\n'.join(p['title'] for p in extra))

    def stop(self):
        if self.job: self.call('jobs.cancel', {'id': self.job})

    def keep_reply(self):
        if not self.record or not self.record.get('job_id') or not self.desk.project:
            self.notice.setText('A completed reply and selected project are needed first.'); return False
        project = self.call('projects.get', {'id': self.desk.project['id']})
        if project is None: return False
        result = self.call('projects.link', {'id': project['id'], 'expected_revision': project['revision'],
            'role': 'ALTERNATIVE', 'address': 'job:' + self.record['job_id']})
        if result is None: return False
        self.desk.open_project(project['id']); self.notice.setText('Graphite’s draft reply is linked as an alternative, with its model job and source context.'); return True

    def use_interpretation(self):
        candidate = (self.record or {}).get('candidate', {})
        if not self.desk.assignment or not candidate.get('interpretation'):
            self.notice.setText('Select an assignment and ask for a staC suggestion first.'); return
        if not self.keep_reply(): return
        self.desk.interpretation.setPlainText(candidate['interpretation']); self.desk.questions.setPlainText('\n'.join(candidate.get('questions', [])))
        self.desk.tabs.setCurrentIndex(1)
        self.desk.message.setText('Graphite’s interpretation is in the editor. Save the assignment to keep a new revision; the original request is retained.')

    def inspect(self):
        if not self.context: return
        dialog = QDialog(self); dialog.setWindowTitle('Graphite sources and result'); dialog.resize(850, 650)
        box = QVBoxLayout(dialog); text = QPlainTextEdit(); text.setReadOnly(True)
        text.setPlainText(json.dumps({'context': self.context, 'result': self.record}, indent=2, ensure_ascii=False)); box.addWidget(text); dialog.exec()
