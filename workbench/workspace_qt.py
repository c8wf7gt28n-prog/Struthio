"""Native palette and selected-object inspector; every lookup uses the Kernel."""
from .text_prompts import writing_prompt
import json
import sqlite3
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLineEdit,QTreeWidget,
    QTreeWidgetItem,QTextBrowser,QPushButton,QLabel,QWidget,QToolButton,QSizePolicy)
from .register_tabs import Call
from .engine import engineering
from .engineering_kernel import operator
from . import record_io as io


class SelectionInspector(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host
        box=QVBoxLayout(self);box.setContentsMargins(6,4,6,4)
        row=QHBoxLayout();self.label=QLabel('Select a component in Brain Link or search')
        self.label.setWordWrap(True);self.label.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse);row.addWidget(self.label,1)
        self.refresh=QToolButton();self.refresh.setText('Refresh');self.refresh.clicked.connect(host.refresh_selection)
        row.addWidget(self.refresh);box.addLayout(row)
        self.identity=QLabel();self.identity.setWordWrap(True);self.identity.setProperty('arcRole','metadata')
        self.identity.setTextInteractionFlags(Qt.TextSelectableByMouse);box.addWidget(self.identity)
        from PySide6.QtWidgets import QGridLayout
        row=QGridLayout();self.buttons={}
        for index,name in enumerate(('CAD','Source','Knowledge','Evidence')):
            button=QPushButton(name);button.clicked.connect(lambda _=False,key=name:host.open_selection_view(key))
            button.setEnabled(False);row.addWidget(button,index//2,index%2);self.buttons[name]=button
        box.addLayout(row)

    def loaded(self,data):
        state=data.get('state','NO_SELECTION');selected=data.get('selection')
        title=selected['reference'] if selected else 'No native selection'
        self.label.setText(title+' · '+state)
        self.identity.setText(('ID '+selected['native_uuid'][:12]+' · inputs '+selected['revision'][:12] if selected else '')+
            ('\n'+data.get('export_binding',{}).get('state','') if state=='CURRENT_INPUTS' else '\n'+data.get('message','')))
        for button in self.buttons.values():button.setEnabled(state=='CURRENT_INPUTS')
        self.identity.setToolTip(json.dumps(selected,indent=2) if selected else '')
        self.refresh.setEnabled(selected is not None)


class WorkspacePalette(QDialog):
    def __init__(self,host):
        super().__init__(host);self.host=host;self.kernel=engineering(host.root);self.worker=None;self.generation=0
        self.setWindowTitle('Find components, nets, source, knowledge and commands');self.resize(980,680)
        box=QVBoxLayout(self);self.query=QLineEdit();writing_prompt(self.query, 'J14, R139, USBA3_DP, a file, vendor text or a command')
        box.addWidget(self.query);self.note=QLabel('Select to inspect. Open navigates; commands open their existing controls.');self.note.setWordWrap(True);box.addWidget(self.note)
        self.results=QTreeWidget();self.results.setHeaderLabels(['Type','Result','Source / currentness']);self.results.setColumnWidth(0,175);self.results.setColumnWidth(1,340);box.addWidget(self.results,2)
        self.detail=QTextBrowser();self.detail.setPlainText('Nothing executes when a result is selected.');box.addWidget(self.detail,1)
        row=QHBoxLayout();self.open_button=QPushButton('Open selected');self.open_button.clicked.connect(self.open_selected)
        row.addWidget(self.open_button);close=QPushButton('Close');close.clicked.connect(self.reject);row.addWidget(close);box.addLayout(row)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(180);self.timer.timeout.connect(self.search)
        self.query.textChanged.connect(self.changed);self.results.itemSelectionChanged.connect(self.inspect)
        self.results.itemDoubleClicked.connect(lambda *_:self.open_selected());self.query.returnPressed.connect(self.search)
        self.search();self.query.setFocus()

    def changed(self):
        self.results.clear();self.open_button.setEnabled(False);self.detail.setPlainText('Searching current saved objects…');self.timer.start()

    def search(self):
        if self.worker is not None and self.worker.isRunning():
            self.timer.start();return
        self.generation+=1;generation=self.generation;query=self.query.text().strip()
        self.note.setText('Searching current saved objects…')
        self.worker=Call(self.kernel,'workspace.search',{'query':query,'limit':75},operator(),self)
        def done(result):
            if generation!=self.generation or query!=self.query.text().strip():return
            self.results.clear()
            if not result['ok']:self.note.setText(result['error']['message']);return
            data=result['result'];rows=data['results']
            for key,action in self.host.favorite_actions.items():
                title=action.text().replace('&','')
                if action.isEnabled() and query and query.casefold() in title.casefold():
                    rows.append({'kind':'menu action','title':title,'source':'Existing native QAction','currentness':'AVAILABLE','action_key':key})
            for row in rows:
                item=QTreeWidgetItem([row['kind'],row['title'],row['source']+' · '+row['currentness']]);item.setData(0,Qt.UserRole,row)
                item.setToolTip(2,row['source']+'\n'+row['currentness']);self.results.addTopLevelItem(item)
            catalog_error = None
            catalog = getattr(self.host, 'concern', None)
            if catalog and catalog.store:
                try:
                    hits = catalog.store.search(query)
                except (ValueError, sqlite3.Error, OSError) as exc:
                    hits = []; catalog_error = str(exc)
                for hit in hits:
                    row = {'kind': 'Concern item', 'title': hit['title'], 'source': hit['search_profile'],
                           'currentness': hit['state'], 'concern_id': hit['id'], 'version': hit['version']}
                    item = QTreeWidgetItem([row['kind'], row['title'], row['source'] + ' · ' + row['currentness']])
                    item.setData(0, Qt.UserRole, row); self.results.addTopLevelItem(item); rows.append(row)
            missing=list(data['unavailable'])
            if catalog_error:missing.append({'kind':'Concern catalog','reason':catalog_error})
            self.note.setText(str(len(rows))+' results · selection executes nothing'+(' · unavailable: '+', '.join(row['kind'] for row in missing) if missing else ''))
            self.note.setToolTip('\n'.join(row['kind']+': '+row['reason'] for row in missing))
            self.open_button.setEnabled(bool(rows))
            if rows:self.results.setCurrentItem(self.results.topLevelItem(0))
        self.worker.ready.connect(done);self.worker.start()

    def inspect(self):
        rows=self.results.selectedItems()
        if not rows:return
        value=rows[0].data(0,Qt.UserRole)
        self.detail.setPlainText(json.dumps(value,indent=2))
        self.open_button.setText('Open job controls' if value['kind']=='command' else 'Run selected menu action' if value['kind']=='menu action' else 'Open selected')

    def open_selected(self):
        items=self.results.selectedItems()
        if not items:return
        value=items[0].data(0,Qt.UserRole)
        try:self.host.open_search_result(value)
        except (OSError,ValueError) as exc:self.note.setText(str(exc));return
        self.accept()

    def done(self,result):
        self.timer.stop()
        if self.worker is not None and self.worker.isRunning():self.worker.wait(10000)
        super().done(result)
