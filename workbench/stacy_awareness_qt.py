"""Compact journal and project status in the existing Ledger tab system."""
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QPlainTextEdit,QLineEdit
from . import stacy_awareness,activity
from .engineering_kernel import operator

class AwarenessTab(QWidget):
    def __init__(self,bridge):
        super().__init__();self.bridge=bridge;self.signature=None
        box=QVBoxLayout(self);self.heading=QLabel();self.heading.setWordWrap(True);box.addWidget(self.heading)
        self.description=QLabel('Graphite follows committed events without model inference. Original project work is sealed separately; project intake is Pass 4.')
        self.description.setWordWrap(True);box.addWidget(self.description)
        self.query=QLineEdit();writing_prompt(self.query, 'Find a capability, e.g. jobs or settings');box.addWidget(self.query)
        row=QHBoxLayout()
        find=QPushButton('Find tools');find.clicked.connect(self.search);row.addWidget(find)
        recover=QPushButton('Recover log');recover.clicked.connect(self.recover);row.addWidget(recover);box.addLayout(row)
        self.output=QPlainTextEdit();self.output.setReadOnly(True);box.addWidget(self.output,1)
        self.timer=QTimer(self);self.timer.setInterval(1500);self.timer.timeout.connect(self.refresh);self.timer.start();self.refresh()
    def title(self):return 'Graphite awareness'
    def info(self):return 'Durable local journal · model calls: 0'
    def refresh(self):
        data=stacy_awareness.inspect(self.bridge.kernel)
        self.heading.setText('GRAPHITE · %s · processed %s / %s · %s' % (data['state'],data['cursor'],data['head'],data['project']['state']))
        self.heading.setToolTip(data['journal'].get('reason','Commit order; not a guarantee that every program feature is instrumented.'))
        if not self.query.text():
            rendered=json.dumps(data,indent=2)
            if rendered!=getattr(self,'_rendered',None):
                scroll=self.output.verticalScrollBar().value();self.output.setPlainText(rendered)
                self.output.verticalScrollBar().setValue(scroll);self._rendered=rendered
    def search(self):
        data=stacy_awareness.discovery(self.bridge.kernel,operator(),self.query.text(),30)
        self.output.setPlainText(json.dumps(data,indent=2));self.refresh()
    def recover(self):
        self.bridge.kernel.dispatch('ledger.journal.recover',{},operator());self.refresh()
