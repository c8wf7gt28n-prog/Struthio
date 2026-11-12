"""Deliberate direction corrections, retaining the existing feedback history."""
import uuid
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPlainTextEdit,QLineEdit
from .settings_qt import action
from .text_prompts import writing_prompt
from .engineering_kernel import operator


class DirectionEditor(QWidget):
    def __init__(self,room):
        super().__init__();self.room=room;self.host=room.host;self.active=False;self.editing=False;self.loading=False
        self.record=None;self.ident=None;self.replacement=None;self.guard=None
        self.setObjectName('MemoryDirectionEditor');box=QVBoxLayout(self);box.setContentsMargins(0,0,0,0);box.setSpacing(8)
        self.begin=action('Revise this direction…',self.start);box.addWidget(self.begin,0,Qt.AlignLeft)
        self.status=QLabel();self.status.setTextFormat(Qt.PlainText);self.status.setWordWrap(True);box.addWidget(self.status)
        self.form=QWidget();col=QVBoxLayout(self.form);col.setContentsMargins(0,0,0,0);col.setSpacing(8)
        for text in ('Write the corrected direction.',):col.addWidget(QLabel(text))
        self.writing=QPlainTextEdit();self.writing.setObjectName('CabinetWriting');self.writing.setMaximumHeight(100)
        self.writing.setProperty('arcReadingRole','prose')  # a corrected direction is prose, not code (V-03)
        self.writing.setAccessibleName('Corrected saved direction');writing_prompt(self.writing,'Corrected direction');col.addWidget(self.writing)
        col.addWidget(QLabel('Why keep this correction?'))
        self.reason=QLineEdit();self.reason.setObjectName('CabinetWriting');self.reason.setMaxLength(200)
        self.reason.setAccessibleName('Reason for the direction correction');writing_prompt(self.reason,'Reason for the correction');col.addWidget(self.reason)
        from .writing_marker import attach
        attach(self.host,self.writing);attach(self.host,self.reason)  # the same cabinet writing vocabulary, so the same marker
        self.save=action('Keep correction and history',self.commit);col.addWidget(self.save,0,Qt.AlignLeft)
        box.addWidget(self.form);self.writing.textChanged.connect(self.save_draft);self.reason.textChanged.connect(self.save_draft);self.hide()

    def bind(self,ident,record):
        self.active=record.get('kind')=='memory_feedback';self.ident=ident;self.record=record;self.replacement=uuid.uuid4().hex;self.guard=None
        self.editing=False;self.loading=True
        draft=self.room.drafts.get(ident) if self.active else None
        self.writing.setPlainText(draft['text'] if draft else record.get('instruction',''))
        self.reason.setText(draft['title'] if draft else '');self.loading=False
        self.editing=bool(draft);self.form.setVisible(self.editing);self.setVisible(self.active)
        editable=self.active and record.get('editable',False)
        self.begin.setText('Use this shown history for the recovered correction…' if draft else 'Revise this direction…')
        self.begin.setEnabled(editable);self.save.setEnabled(False)
        self.status.setText(('Recovered writing needs a deliberate history review. Choose Use this shown history before keeping the correction.' if editable and draft else
            'A correction replaces earlier directions for this preference and context, while keeping their history and the stored agreement. It is a persistent owner correction.' if editable else
            'This history entry is read-only here. Editing requires an active direction and owner approval; separate recovery writing can still be reviewed.'))

    def start(self):
        if not self.record or not self.record.get('editable'):return
        self.guard=self.record['history_digest'];self.save.setEnabled(True)
        self.editing=True;self.form.show();self.writing.setFocus(Qt.OtherFocusReason)
        self.status.setText('This correction uses the history shown above. Any further history change will block it. Earlier words and the stored agreement are retained.')
        self.room.scroll.ensureWidgetVisible(self.writing)

    def save_draft(self,*_):
        if not self.active or not self.editing or self.loading or self.room.loading:return
        text=self.writing.toPlainText();reason=self.reason.text()
        if text!=self.record.get('instruction','') or reason:self.room.drafts[self.ident]=dict(text=text,title=reason)
        else:self.room.drafts.pop(self.ident,None)

    def commit(self):
        if not self.active or not self.record.get('editable') or self.guard is None:return
        args=dict(id=self.record['id'],replacement=self.replacement,expected_history=self.guard,
                  instruction=self.writing.toPlainText(),reason=self.reason.text())
        response=self.host.ledger_bridge.kernel.dispatch('memory.direction.revise',args,operator())
        if not response['ok']:
            self.room.note.setText(response['error']['message']+' Your proposed words remain in the writing space.');return
        self.room.drafts.pop(self.ident,None);destination='memory:feedback:'+response['result']['record']['id']
        # Do not reinsert the just-committed old draft when the room changes ID.
        self.room.loading=True
        self.host.cabinet_page.refresh(force=True);self.host.cabinet_page.select(destination,reveal=True)
        if not self.room.open(destination):self.room.loading=False
        self.room.note.setText('Correction kept. Earlier owner directions remain in history; model weights and engineering permissions are unchanged.')
