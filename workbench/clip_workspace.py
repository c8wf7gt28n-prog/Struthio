"""Long-form local conversation over shared Ledger commands and real services.

Deterministic commands and provider proposals are labelled separately.
Component source sharing retains its existing opt-in path.
"""
from .text_prompts import writing_prompt

import json
from .static_bird import icon as bird_icon
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QLineEdit,
    QPushButton,
    QCheckBox,
)
from .engine import engineering
from .engineering_kernel import Principal


class ClipWorkspaceTab(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.kernel = engineering(host.root)
        self.principal = Principal("desktop-tutor", mode="Tutor")
        self.selected_component = None
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        self.portrait = QLabel()
        self.portrait.setAccessibleName('Graphite, your workspace assistant')
        self.portrait.setFixedSize(104, 130)
        self.portrait.setAlignment(Qt.AlignCenter)
        self.portrait.setPixmap(bird_icon(host.root).pixmap(300,300).scaled(
            QSize(104, 130), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        header.addWidget(self.portrait)
        label = QLabel(
            "GRAPHITE · COMMANDS\nLocal commands use the shared Kernel. Gemini can propose commands for your review."
        )
        label.setWordWrap(True)
        header.addWidget(label, 1)
        layout.addLayout(header)
        self.transcript = QPlainTextEdit()
        self.transcript.setProperty('arcReadingRole','prose')
        self.transcript.setReadOnly(True)
        layout.addWidget(self.transcript, 1)
        self.input = QLineEdit()
        writing_prompt(self.input, "/commands · /settings · /set operations.priority background · /jobs · /tail")
        self.input.returnPressed.connect(self.send)
        layout.addWidget(self.input)
        row = QHBoxLayout()
        for name, fn in [
            ("Send local command", self.send),
            ("Cloud chat / provider settings", host.open_clip),
            ("Prepare bounded AI task", self.open_task),
        ]:
            button = QPushButton(name)
            button.clicked.connect(fn)
            row.addWidget(button)
        layout.addLayout(row)
        self.share_component = QCheckBox('Share selected component facts with Gemini when I choose Ask Gemini')
        self.share_component.setToolTip('The free API may use submitted content for improvement and human review. This sends source-derived facts, paths and issue summaries, not vendor originals or secrets.')
        layout.addWidget(self.share_component)
        button = QPushButton('Ask Gemini about the selected component')
        button.clicked.connect(self.ask_component)
        layout.addWidget(button)
        self.transcript.setPlainText(
            "Graphite local commands\nUse /commands to discover the registered operations. /set KEY VALUE changes a validated setting.\n/open brain link · /build struthio.build · /jobs · /tail\nLocal commands need no provider key. Source proposals keep the existing candidate/review workflow.\n"
        )
        host.ledger_bridge.command_finished.connect(self.transcript.appendPlainText)

    def title(self):
        return "Graphite · Engineering conversation"

    def load_component(self,reference):
        r=self.kernel.dispatch('workshop.component_context',{'component':reference},self.principal)
        if r['ok'] and 'component' in r['result']:
            self.selected_component=r['result']
            self.transcript.appendPlainText('\nGraphite local source context · '+reference+'\n'+json.dumps(r['result'],indent=2))
        elif r['ok']:self.transcript.appendPlainText(r['result'].get('reason') or 'No source context for '+reference)
        else:self.transcript.appendPlainText(r['error']['message'])

    def ask_component(self):
        if not self.selected_component:
            self.transcript.appendPlainText('Choose a component in Brain Link and select Discuss in Graphite.');return
        if not self.share_component.isChecked():
            self.transcript.appendPlainText('Select the source-sharing checkbox before sending component context.');return
        data=self.selected_component
        args={'component':data['component']['reference'],'expected_revision':data['revision']}
        r=self.kernel.dispatch('workshop.component_context',args,self.principal)
        if not r['ok'] or r['result'].get('state') in ('STALE',None):
            self.transcript.appendPlainText('Component context changed. Refresh the selection before sharing.');return
        prompt='Explain this selected ARC-1 component for a learner. Cite the supplied source paths and issue IDs. Separate documented intent, executable host evidence and unavailable physical qualification. Do not invent timings or pin facts.\n'+json.dumps(r['result'])
        if len(prompt.encode())>24000:
            self.transcript.appendPlainText('Context exceeds the bounded sharing allowance; select a smaller source context.');return
        self.host._submit_clip_from_dock(prompt)

    def open_task(self):
        tab = self.host.show_engineering()
        if tab is not None:
            tab.pages.setCurrentWidget(tab.workshop)

    def send(self):
        message = self.input.text().strip()
        if not message:
            return
        self.input.clear()
        self.transcript.appendPlainText("\nYou: " + message)
        if self.host.ledger_bridge.handle_text(message):return
        self.transcript.appendPlainText('Open Cloud chat for this request, or use /commands for the local command list.')
