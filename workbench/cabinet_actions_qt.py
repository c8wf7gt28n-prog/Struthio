"""One presentation of checked cabinet actions for shelves and context menus."""
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QMenu
from .engineering_kernel import operator
from .settings_qt import action,STYLE


def model(host,ident):
    response=host.ledger_bridge.kernel.dispatch('ledger.cabinet.actions',{'id':ident},operator())
    if not response['ok']:raise ValueError(response['error']['message'])
    return response['result']


def perform(host,ident,key,signature):
    """Re-resolve the captured identity, never the tree's later selection."""
    live=model(host,ident)
    if live['context'] is None:raise ValueError(live['notice'])
    if live['signature']!=signature:raise ValueError('This record or its available actions changed. Refresh the actions and choose again.')
    spec=next((row for row in live['actions'] if row['id']==key),None)
    if spec is None or not spec['enabled']:raise ValueError(spec['unavailable_reason'] if spec else 'This action is no longer available.')
    if spec['kind']=='READ':
        response=host.ledger_bridge.kernel.dispatch(spec['operation'],spec['arguments'],operator())
        if not response['ok']:raise ValueError(response['error']['message'])
        room=host.cabinet_page.open(ident)
        if room is not None:
            room.result.setPlainText(json.dumps(response['result'],indent=2,ensure_ascii=False)[:100000]);room.result.show()
            room.note.setText(spec['label']+' · current provider result read.')
        return response['result']
    if spec['kind']=='PREPARE':
        room=host.cabinet_page.open(ident)
        if room is None or room.form_mode!=spec['form']:raise ValueError('The writing space changed. Refresh the record.')
        target=room.new_title if spec['form']=='project' else room.writing
        room.scroll.ensureWidgetVisible(target);target.setFocus(Qt.OtherFocusReason)
        room.note.setText('Your existing draft is ready to continue. Keep or Create saves it separately.')
        return room
    if spec['kind']=='WORKSPACE':
        from .explore_qt import open_instrument
        # Open existing controls only. Context is intentionally not bound to a
        # problem sheet or copied into an existing view's edited inputs.
        return open_instrument(host,{'id':spec['instrument']})
    if spec['kind']=='EXPLORE':
        from .explore_qt import show
        return show(host,ident)
    raise ValueError('This action has no current presentation handler.')


def explanation(spec):
    return (spec['unavailable_reason'] if not spec['enabled'] else spec['reason'])+'\n'+' '.join(spec['checks_remaining'])


def menu(host,ident,parent=None,snapshot=None):
    value=snapshot if snapshot is not None else model(host,ident)
    popup=QMenu(parent);popup.setObjectName('CabinetActionMenu');popup.setToolTipsVisible(True)
    popup.setStyleSheet(STYLE+'''
    QMenu {background:#22292c;color:#eee9dd;border:1px solid #394549;}
    QMenu::item {padding:8px 20px;}
    QMenu::item:selected {background:#493225;}
    QMenu::item:disabled {color:#b0bcb9;}
    ''')
    popup.action_model=value
    # V-14: QMenu::addSection text does not render under the application stylesheet (explore_qt notes the same), so the
    # heading is a visible, italic, disabled row followed by a rule; its words say which record the actions belong to.
    heading=popup.addAction(('With '+value['context']['label'][:70]).replace('&','&&') if value['context'] else 'Selection unavailable')
    heading.setEnabled(False);font=heading.font();font.setItalic(True);heading.setFont(font);popup.heading=heading;popup.addSeparator()
    def run(key):
        try:perform(host,ident,key,value['signature'])
        except (ValueError,OSError,ImportError) as exc:host.statusBar().showMessage(str(exc),7000)
    for spec in value['actions']:
        text=spec['label']+(' · unavailable' if not spec['enabled'] else '…' if spec['kind']=='PREPARE' else '')
        entry=popup.addAction(text.replace('&','&&'),lambda checked=False,key=spec['id']:run(key))
        entry.setData(spec['id']);entry.setEnabled(spec['enabled']);entry.setToolTip(explanation(spec))
        if not spec['enabled']:
            reason=popup.addAction('    '+spec['unavailable_reason'].replace('&','&&'));reason.setEnabled(False)
    if not value['actions']:
        entry=popup.addAction(value['notice']);entry.setEnabled(False)
    return popup


class ActionShelf(QWidget):
    def __init__(self,host,report,parent=None):
        super().__init__(parent);self.host=host;self.report=report;self.ident=None;self.snapshot=None;self.buttons={}
        self.setObjectName('CabinetActionShelf');self.setProperty('paperFunctionalInk',True)
        self.box=QVBoxLayout(self);self.box.setContentsMargins(0,2,0,2);self.box.setSpacing(6)

    def bind(self,ident):
        self.ident=ident
        while self.box.count():
            child=self.box.takeAt(0)
            if child.widget():child.widget().deleteLater()
        self.buttons={}
        try:self.snapshot=model(self.host,ident)
        except (ValueError,OSError) as exc:self.report(str(exc));return
        title=QLabel('WITH THIS RECORD');title.setTextFormat(Qt.PlainText);self.box.addWidget(title)
        if self.snapshot['context'] is None:
            note=QLabel(self.snapshot['notice']);note.setWordWrap(True);self.box.addWidget(note);return
        # Keep the shelf compact. The full menu exposes the same ordered list.
        for spec in self.snapshot['actions'][:3]:
            row=QWidget();line=QHBoxLayout(row);line.setContentsMargins(0,0,0,0);line.setSpacing(12)
            button=action(spec['label'].replace('&','&&'),lambda checked=False,key=spec['id'],signature=self.snapshot['signature'],ident=ident:self.run(ident,key,signature))
            button.setEnabled(spec['enabled']);button.setToolTip(explanation(spec));button.setAccessibleName(spec['label'])
            button.setMaximumWidth(260);line.addWidget(button)
            note=QLabel(spec['unavailable_reason'] if not spec['enabled'] else spec['reason']);note.setTextFormat(Qt.PlainText)
            note.setWordWrap(True);note.setMinimumWidth(0);line.addWidget(note,1);self.box.addWidget(row);self.buttons[spec['id']]=button
        more=action('All actions…',self.more);self.box.addWidget(more,0,Qt.AlignLeft);self.more_button=more

    def run(self,ident,key,signature):
        try:perform(self.host,ident,key,signature)
        except (ValueError,OSError,ImportError) as exc:
            self.bind(ident);self.report(str(exc))

    def more(self):
        try:
            popup=menu(self.host,self.ident,self)
            popup.exec(self.more_button.mapToGlobal(self.more_button.rect().bottomLeft()))
        except (ValueError,OSError) as exc:self.report(str(exc))
