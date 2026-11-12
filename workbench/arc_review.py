"""Read-only comparison of a proposed parser repair; no promotion or execution."""
import difflib
import hashlib
import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QTextCursor, QTextFormat
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QSplitter,QPlainTextEdit,QTextEdit,QFrame)
from .ux_assets import icon
from .qt_app import CodeEditor


class ReviewEditor(CodeEditor):
    def _highlight(self):
        super()._highlight()
        self.setExtraSelections(list(self.extraSelections())+getattr(self,'review_selections',[]))


class CandidateReviewTab(QWidget):
    def __init__(self,host):
        super().__init__()
        self.host=host
        self.setObjectName('CandidateReview')
        box=QVBoxLayout(self);box.setContentsMargins(16,14,16,12);box.setSpacing(12)
        heading=QLabel('Review command-parser repair');heading.setProperty('arcRole','section');box.addWidget(heading)
        note=QLabel('Isolated proposal · current source remains unchanged');note.setWordWrap(True);note.setProperty('arcRole','metadata');box.addWidget(note)
        folder=host.root/'project/review/command_parser'
        binding=json.loads((folder/'SOURCE.json').read_text())
        self.source_path=host.root/binding['path']
        original=self.source_path.read_bytes();proposed=(folder/'host.c').read_bytes()
        self.binding_current=(hashlib.sha256(original).hexdigest()==binding['base_sha256'] and
            hashlib.sha256(proposed).hexdigest()==binding['candidate_sha256'])
        self.binding_label=QLabel('Source bytes match the proposal binding' if self.binding_current else 'Source changed · proposal requires rechecking')
        self.binding_label.setWordWrap(True);box.addWidget(self.binding_label)
        split=QSplitter(Qt.Horizontal);self.editors=[]
        for title,path,raw in [('Current source',self.source_path,original),('Proposed candidate',folder/'host.c',proposed)]:
            panel=QWidget();v=QVBoxLayout(panel);v.setContentsMargins(0,0,0,0)
            caption=QLabel(title);caption.setProperty('arcRole','section');v.addWidget(caption)
            ed=ReviewEditor(path,host.root);ed.setPlainText(raw.decode());ed.setReadOnly(True)
            ed.minimap.WIDTH=0;ed.minimap.hide();ed._update_margins()
            ed.setLineWrapMode(QPlainTextEdit.WidgetWidth)
            ed.document().setModified(False);v.addWidget(ed,1);split.addWidget(panel);self.editors.append(ed)
        split.setSizes([500,500]);box.addWidget(split,1)
        old=original.decode().splitlines();new=proposed.decode().splitlines()
        self.hunks=[]
        for tag,a,b,c,d in difflib.SequenceMatcher(None,old,new,autojunk=False).get_opcodes():
            if tag=='equal':continue
            self.hunks.append((a,c))
            for ed,start,end,color in [(self.editors[0],a,b,'#f8e5e1'),(self.editors[1],c,d,'#e8f1dd')]:
                selections=list(getattr(ed,'review_selections',[]))
                for line in range(start,end):
                    selected=QTextEdit.ExtraSelection();selected.cursor=QTextCursor(ed.document().findBlockByNumber(line))
                    selected.format.setBackground(QColor(color));selected.format.setProperty(QTextFormat.FullWidthSelection,True)
                    selections.append(selected)
                ed.review_selections=selections
        self.hunk_index=1 if len(self.hunks)>1 else 0
        navigation=QHBoxLayout()
        for title,delta in [('Previous change',-1),('Next change',1)]:
            button=QPushButton(title);button.clicked.connect(lambda checked=False,value=delta:self.change_hunk(value));navigation.addWidget(button)
        box.insertLayout(3,navigation)
        self.change_hunk(0)
        evidence=QFrame();evidence.setObjectName('HomeActions');row=QHBoxLayout(evidence)
        for title,text in [('Source','Hash-bound comparison'),('Parser checks','Run before acceptance'),
                           ('Acceptance','Pending review'),('Physical target','Not qualified')]:
            col=QVBoxLayout();label=QLabel(title);label.setProperty('arcRole','metadata');col.addWidget(label)
            value=QLabel(text);value.setWordWrap(True);col.addWidget(value);row.addLayout(col,1)
        box.addWidget(evidence)
        self.explanation=QLabel('Review scope: reject partial commands, signed values, overflow and oversized input. This comparison does not execute tests or accept source changes.')
        self.explanation.setWordWrap(True);box.addWidget(self.explanation)
        row=QHBoxLayout()
        for title,asset,method in [('Open engineering controls','evidence',host.show_engineering),
                ('Discuss with Graphite','clip',host.open_clip),('Open current source','c',lambda:host.open_document(self.source_path))]:
            button=QPushButton(icon(host.root,asset),title);button.clicked.connect(lambda checked=False,fn=method:self.follow(fn));row.addWidget(button)
        box.addLayout(row)

    def follow(self,fn):
        if self.host.tabs.pin(self):return fn()

    def change_hunk(self,delta):
        if not self.hunks:return
        self.hunk_index=(self.hunk_index+delta)%len(self.hunks)
        for ed,line in zip(self.editors,self.hunks[self.hunk_index]):
            ed.go_to(line+1);ed.centerCursor()

    def title(self):return 'Parser review'
    def info(self):return 'Isolated parser proposal · independent review pending'
