"""Consistent native summaries over pure SDK projections; plain text only."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout,QLabel,QFrame,QSizePolicy


class ResultSurface(QFrame):
    def __init__(self,parent=None,compact=False):
        super().__init__(parent);self.compact=compact
        self.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Maximum)
        self.setObjectName('WorkbenchResult')
        self.setStyleSheet('QFrame#WorkbenchResult {border:1px solid #46515a;border-left:3px solid #f09a49;border-radius:6px;}')
        self.box=QVBoxLayout(self);self.box.setContentsMargins(10,8,10,8);self.box.setSpacing(6)
        self.box.setAlignment(Qt.AlignTop)
        self.labels={}
        for key,role in [('title','heading'),('state','ui'),('summary','prose'),
                         ('context','ui'),('known','prose'),('uncertain','prose'),('next_step','prose')]:
            label=QLabel();label.setWordWrap(True);label.setTextFormat(Qt.PlainText)
            label.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
            label.setProperty('arcReadingRole','ui' if compact and role=='prose' else role)
            label.setAccessibleName('Workbench '+key.replace('_',' '))
            if key=='context':label.setTextInteractionFlags(Qt.TextSelectableByMouse|Qt.TextSelectableByKeyboard)
            self.labels[key]=label;self.box.addWidget(label)
        self.clear()

    def clear(self):
        self.model=None
        for label in self.labels.values():label.clear();label.hide()

    def present(self,model):
        self.clear();self.model=model
        content={**model,
                 'known':'Known · '+' · '.join(model.get('known',[])) if model.get('known') else '',
                 'uncertain':'Attention · '+' · '.join(model.get('uncertain',[])) if model.get('uncertain') else '',
                 'next_step':'Next · '+model.get('next_step','') if model.get('next_step') else ''}
        if self.compact:
            content['title']=''
            items=model.get('uncertain',[])
            content['uncertain']=('Attention · '+items[0]+(' More in Object Glass.' if len(items)>1 else '')) if items else ''
            content['next_step']=''
        for key,label in self.labels.items():
            text=content.get(key,'')
            if key=='state':text=text.replace('_',' ').capitalize()
            if key=='context' and self.compact and text:
                text='\n'.join(line[:40]+('…' if len(line)>40 else '') for line in text.splitlines())
            label.setText(text);label.setVisible(bool(text))
        self.setAccessibleDescription(model.get('summary',''))
