"""Native C starter controls using fixed Kernel operations."""
from .text_prompts import writing_prompt
import json,uuid,html
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel,QLineEdit,QPushButton,QGridLayout,QPlainTextEdit,QTabWidget,QTextBrowser
from .register_tabs import ServiceTab
from .ux_polish import overline, readable_error

class NativeProjectTab(ServiceTab):
    def __init__(self,host):
        super().__init__(host);self.job_id=None;self.after_build=False
        title=overline('Native C starter','ARC-OS host ABI 1');self.outer.addWidget(title)
        self.name=QLineEdit('first_arc_game');writing_prompt(self.name, 'lowercase_project_name');self.outer.addWidget(self.name)
        note=QLabel('Create from the existing SDK template, build a local native module and FAT32 thumb-drive image, then boot through the compiled USB BOT / FatFs model. Builds and games run with your host account. Physical ARC-1 boot remains blocked.');note.setWordWrap(True);self.outer.addWidget(note)
        buttons=QGridLayout();self.buttons={}
        for i,(label,fn) in enumerate([('Create project',self.create),('Open source',self.source),('Build native project',self.build),('Boot native game',self.boot),('Inspect',self.inspect)]):
            button=QPushButton(label);button.clicked.connect(fn);buttons.addWidget(button,i//3,i%3);self.buttons[label]=button
        self.outer.addLayout(buttons);self.outer.addWidget(self.status)
        self.views=QTabWidget();self.overview=QTextBrowser();self.overview.setObjectName('OrangeBookPaper')
        self.overview.setStyleSheet('QTextBrowser {background:#faf7f0;color:#182330;padding:24px;}')
        self.details=QPlainTextEdit();self.details.setReadOnly(True)
        self.views.addTab(self.overview,'Your game');self.views.addTab(self.details,'Build details');self.outer.addWidget(self.views,1)
        self.name.textChanged.connect(self.selection_changed);self.selection_changed()
        self.poll=QTimer(self);self.poll.setInterval(300);self.poll.timeout.connect(self.poll_job)
        QTimer.singleShot(0,self.inspect)
    def title(self):return 'Native C starter'
    def selected(self):return self.name.text().strip()
    def selection_changed(self):
        exists=(self.host.root/'examples'/self.selected()/'native.json').is_file()
        self.buttons['Create project'].setEnabled(not exists)
        for label in ('Open source','Build native project','Boot native game','Inspect'):self.buttons[label].setEnabled(exists)
        self.overview.setHtml('<h1 style="color:#182330">'+html.escape(self.selected() or 'Your next game')+'</h1><p style="color:#182330">'+
            ('An existing native C project. Open its source, build it, then boot it in the host model.' if exists else
             'Choose a lowercase project name, then Create project. Graphite will make a new example from the SDK template.')+'</p>')
    def inspect(self):
        name=self.selected()
        self.call('native.inspect',{'name':name},lambda r:self.loaded(r) if name==self.selected() else None)
    def loaded(self,r):
        ready=r['state']=='CURRENT_INPUTS'
        self.status.setText('Ready to boot in the host model' if ready else 'Build this project to prepare its game media')
        self.status.setToolTip(r['reason']);self.details.setPlainText(json.dumps(r,indent=2))
        self.selection_changed()
        self.overview.setHtml('<div style="color:#182330"><h1>'+html.escape(r['name'])+'</h1><p>Native C · ARC-OS host ABI</p>'+
            '<h2>1 · Open the source</h2><p>'+html.escape(r['path'])+'</p>'+
            '<h2>2 · Build your game</h2><p>The SDK compiles the local module, GameCard and FAT32 USB-media image.</p>'+
            '<h2>3 · Boot and play</h2><p>'+('The verified build is current. Boot native game opens it in Simulator.' if ready else 'Build native project first, then choose Boot native game.')+'</p>'+
            '<p>This runs on your development computer using its native account. Physical ARC-1 boot is unqualified.</p></div>')
    def create(self):
        self.call('native.create',{'name':self.selected()},lambda r:(self.host.refresh_navigator(),self.source(),self.inspect()))
    def source(self):
        from .native_projects import project
        try:p=project(self.host.root,self.selected())
        except ValueError as exc:self.status.setText(str(exc));return
        self.host.tabs.pin(self);self.host.open_document(p/'game.c')
    def build(self):
        if self.job_id or not self.host.save_all():return
        def ready(r):
            self.after_build=not r.get('build') or not r['build']['current']
            self.submit('console.build' if self.after_build else 'native.build')
        self.call('console.inspect',{},ready)
    def submit(self,tool):
        args={'tool':tool,'request_key':uuid.uuid4().hex,'timeout':180}
        if tool=='native.build':args['project']=self.selected()
        def started(j):self.job_id=j['id'];self.status.setText('Queued '+tool);self.poll.start()
        self.call('jobs.submit',args,started)
    def poll_job(self):
        if not self.job_id:return
        r=self.kernel.dispatch('jobs.get',{'id':self.job_id},self.principal)
        if not r['ok']:self.poll.stop();self.status.setText(readable_error(r['error']['message'],self.host.root));return
        j=r['result'];self.status.setText(j['tool']+' · '+j['state'])
        if j['state'] in ('Completed','Failed','Cancelled','Interrupted'):
            self.job_id=None;self.poll.stop();self.details.setPlainText(json.dumps(j,indent=2))
            if j['state']=='Completed' and self.after_build:self.after_build=False;self.submit('native.build')
            elif j['state']=='Completed':self.inspect()
            else:self.after_build=False
    def boot(self):
        if self.job_id or not self.host.save_all():return
        if not self.host.tabs.pin(self):return
        tab=self.host.show_arcos()
        if tab is None:return
        tab.pause()
        def opened(state):
            tab.fixture.setCurrentIndex(tab.fixture.findData('sample'));tab.session_id=state['id'];tab.loaded(state);tab.timer.start()
        def start(_=None):tab.call('native.open',{'name':self.selected()},opened)
        if tab.session_id:tab.call('console.close',{'id':tab.session_id},start)
        else:start()
    def shutdown_engineering(self):
        self.poll.stop();super().shutdown_engineering()
