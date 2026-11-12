"""Project-wide retrieval and work coordination, inside the central workspace."""
from __future__ import annotations
from .text_prompts import writing_prompt
import time
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,
                             QCheckBox,QTreeWidget,QTreeWidgetItem,QHeaderView,QComboBox)
from . import project_services, activity
from .command_rows import fold
from .ux_polish import overline, empty_hint


class SearchWorker(QThread):
    result = Signal(object)
    def __init__(self,root,query,archives,case_sensitive,parent=None):
        super().__init__(parent)
        self.root,self.query,self.archives,self.case_sensitive=root,query,archives,case_sensitive
    def run(self):
        try:
            data=project_services.search(self.root,self.query,archives=self.archives,
                                        case_sensitive=self.case_sensitive,cancelled=self.isInterruptionRequested)
            self.result.emit(data)
        except Exception as e:
            self.result.emit({'error':str(e)})


class ProjectSearchTab(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.worker=None
        v=QVBoxLayout(self)
        title=QLabel('Search the ARC-1 project');title.setObjectName('heading');v.addWidget(title)
        row=QHBoxLayout();self.query=QLineEdit();writing_prompt(self.query, 'Literal text across source, RTL, schematics and documents')
        self.go=QPushButton('Search');self.cancel=QPushButton('Cancel');self.cancel.setEnabled(False)
        row.addWidget(self.query,1);row.addWidget(self.go);row.addWidget(self.cancel);v.addLayout(row)
        options=QHBoxLayout();self.archives=QCheckBox('Include archives / imported source records');self.case=QCheckBox('Match case')
        options.addWidget(self.archives);options.addWidget(self.case);options.addStretch();v.addLayout(options)
        self.note=QLabel('Searches saved files. Double-click a result to open its location.');self.note.setWordWrap(True);v.addWidget(self.note)
        self.results=QTreeWidget();self.results.setRootIsDecorated(False)
        self.results.setHeaderLabels(['File','Line','Text']);empty_hint(self.results,'Type literal text and press Search. Only saved files are searched.')
        self.results.setColumnWidth(0,290);self.results.setColumnWidth(1,50)
        self.results.header().setSectionResizeMode(2,QHeaderView.Stretch);v.addWidget(self.results,1)
        self.go.clicked.connect(self.start);self.query.returnPressed.connect(self.start)
        self.cancel.clicked.connect(lambda:self.worker and self.worker.requestInterruption())
        self.results.itemActivated.connect(self.open_result)
    def title(self):return 'Project Search'
    def info(self):return 'Saved project files · literal search · bounded results · no source changes'
    def start(self):
        if self.worker and self.worker.isRunning():return
        if not self.query.text().strip():return
        self.results.clear();self.go.setEnabled(False);self.cancel.setEnabled(True)
        self.note.setText('Searching saved project files…')
        self.worker=SearchWorker(self.window.root,self.query.text(),self.archives.isChecked(),self.case.isChecked(),self)
        self.worker.result.connect(self.show_result)
        self.worker.finished.connect(lambda:(self.go.setEnabled(True),self.cancel.setEnabled(False)))
        self.worker.start()
    def show_result(self,data):
        if 'error' in data:self.note.setText(data['error']);return
        for match in data['matches']:
            item=QTreeWidgetItem([match['path'],str(match['line']),match['preview']]);item.setData(0,Qt.UserRole,match)
            self.results.addTopLevelItem(item)
        self.note.setText(f"{len(data['matches'])} matching lines · {data['scanned']} files searched · {data['skipped']} unreadable/oversized files skipped"
                          + (' · Result limit reached or cancelled' if data['truncated'] else '')+' · Saved files only')
    def open_result(self,item,_column=0):
        match=item.data(0,Qt.UserRole);path=self.window.root/match['path']
        ed=self.window.open_document(path)
        if hasattr(ed,'go_to'):ed.go_to(match['line'],match['column'])
        from .editor_recovery import file_hash
        if file_hash(path)!=match['sha256']:
            self.window.statusBar().showMessage('File changed since search; line position may have moved',7000)
    def shutdown(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption();self.worker.wait(3000)
        return not self.worker or not self.worker.isRunning()


class ProjectDeskTab(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window
        v=QVBoxLayout(self)
        h=overline('Project Desk','workstreams, host workflow and recent activity');v.addWidget(h)
        intro=QLabel('In-house development office · firmware, FPGA, games and engineering records')
        intro.setWordWrap(True);v.addWidget(intro)
        self.goal=QLabel();self.goal.setObjectName('simBanner');self.goal.setWordWrap(True);v.addWidget(self.goal)
        row=QHBoxLayout()
        for label,cb in [('Development lab',window.show_development),('Hardware ledger',window.show_hardware_ledger),('Search all work',window.show_project_search),('Console evidence',window.show_readiness),
                         ('Full file explorer',lambda:window.browse(window.root)),('Workplan',lambda:window.open_document(window.root/'project/workplan.json'))]:
            b=QPushButton(label);b.clicked.connect(cb);row.addWidget(b)
        fold(row,groups=[('Open',('Development lab','Hardware ledger','Search all work','Console evidence','Full file explorer','Workplan'))]);row.addStretch()
        v.addLayout(row)
        self.tasks=QTreeWidget();self.tasks.setRootIsDecorated(False);self.tasks.setHeaderLabels(['Workstream','State','Next closure / evidence'])
        self.tasks.setColumnWidth(0,190);self.tasks.setColumnWidth(1,160);self.tasks.header().setSectionResizeMode(2,QHeaderView.Stretch)
        self.tasks.itemActivated.connect(self.open_task);v.addWidget(self.tasks,2);empty_hint(self.tasks,'Reading the workplan…')
        run=QHBoxLayout();self.project=QComboBox()
        from . import engine
        for p in engine.game_projects(window.root):self.project.addItem(p,p)
        run.addWidget(self.project,1)
        self.run_button=QPushButton('Run host workflow');self.run_button.clicked.connect(lambda:window.run_host_workflow(self.project.currentData()))
        run.addWidget(self.run_button);v.addLayout(run)
        label=QLabel('Build → tests → host frames → system trace. Stops on failure. Uses saved host C projects; no board programming.')
        label.setWordWrap(True);v.addWidget(label)
        self.state=QLabel('Workflow ready');self.state.setWordWrap(True);v.addWidget(self.state)
        self.events=QTreeWidget();self.events.setRootIsDecorated(False);self.events.setHeaderLabels(['Time','Origin','Operation','Result'])
        self.events.header().setSectionResizeMode(2,QHeaderView.Stretch);self.events.setMaximumHeight(150);v.addWidget(self.events,1);empty_hint(self.events,'No recorded activity yet.')
        refresh=QPushButton('Refresh work and activity');refresh.clicked.connect(self.refresh);v.addWidget(refresh)
        self.refresh()
    def title(self):return 'Project Desk'
    def info(self):return 'Project access and recorded work · 95% first-try reliability is a goal, not a measurement'
    def open_task(self,item,_column=0):
        value=item.data(0,Qt.UserRole)
        if value:self.window.open_document(self.window.root/value)
    def refresh(self):
        data=project_services.overview(self.window.root)
        ready=data['readiness']
        self.goal.setText(f"TARGET: ≥95% first-try out-of-box success · measured probability UNKNOWN\n"
                          f"{ready['verified_gates']}/{ready['required_gates']} reviewed evidence gates recorded · fabrication HOLD\n"
                          'Simulator: host gameplay + behavioral system model. Full chip emulation remains open.')
        self.tasks.clear()
        for task in data['tasks']:
            row=QTreeWidgetItem([task['title'],task['status'],task['closure']]);row.setToolTip(1,task['status']);row.setToolTip(2,task['closure']);row.setData(0,Qt.UserRole,task.get('path'));self.tasks.addTopLevelItem(row)
        self.refresh_activity()
    def refresh_activity(self):
        events=activity.recent(self.window.root)
        self.events.clear()
        for event in events[-8:]:
            self.events.addTopLevelItem(QTreeWidgetItem([time.strftime('%H:%M:%S',time.localtime(event['at'])),event['origin'],event['operation'],event['state']]))
        self.events.scrollToBottom()
        self.state.setText(getattr(self.window,'workflow_status','Workflow ready'))
        self.run_button.setEnabled(not getattr(self.window,'workflow_active',False))
