"""Engineering-first virtual console over the shared Kernel and native C process."""
import json, uuid
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter,QColor,QFont,QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QComboBox, QTreeWidget, QTreeWidgetItem, QTabWidget, QPlainTextEdit, QFileDialog, QSizePolicy
from .register_tabs import ServiceTab
from .ux_assets import icon,assets
from . import record_io as io
from .command_rows import fold
from . import locations

KEYS={Qt.Key_Up:(0,0),Qt.Key_Right:(2,0),Qt.Key_Down:(4,0),Qt.Key_Left:(6,0),Qt.Key_Z:(8,1),Qt.Key_X:(8,2),Qt.Key_Return:(8,256),Qt.Key_Enter:(8,256)}


class ConsoleScreen(QWidget):
    def __init__(self,tab):
        super().__init__();self.tab=tab;self.frame=None;self.setMinimumSize(320,210);self.setFocusPolicy(Qt.StrongFocus)
        self.logo=QPixmap(str(locations.program(tab.host.root)/'branding/ARC1_ADAPTIVE_RISCV_CONSOLE_OFFICIAL.jpg'))
        self.setAccessibleName('ARC-OS virtual television. Arrow keys navigate, Z selects, X backs out, Enter returns from game.')
    def keyPressEvent(self,event):
        if event.key() in KEYS:
            if not event.isAutoRepeat():self.tab.key(event.key(),True)
            event.accept()
        else:super().keyPressEvent(event)
    def keyReleaseEvent(self,event):
        if event.key() in KEYS:
            if not event.isAutoRepeat():self.tab.key(event.key(),False)
            event.accept()
        else:super().keyReleaseEvent(event)
    def focusOutEvent(self,event):self.tab.held.clear();self.tab.needs_input=True;self.tab.step();super().focusOutEvent(event)
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),Qt.black);scale=min(self.width()/960,self.height()/540)
        p.translate((self.width()-960*scale)/2,(self.height()-540*scale)/2);p.scale(scale,scale);p.setRenderHint(QPainter.Antialiasing)
        f=self.frame;p.setPen(QColor('#b6bec5'));p.drawRoundedRect(QRectF(18,16,924,508),18,18)
        if not f:
            p.setFont(QFont('DejaVu Sans',18));p.drawText(QRectF(80,180,800,160),Qt.AlignCenter,'ARC-OS\nBoot the virtual console to begin');return
        if f['screen']=='GAME':
            p.save();p.translate(32,32);p.scale(2.8,2.6);p.setClipRect(QRectF(0,0,320,180))
            for x,y,w,h,color in f['rects']:p.fillRect(x,y,w,h,QColor.fromRgb(color))
            p.restore();return
        p.drawPixmap(QRectF(300,25,360,120),self.logo,QRectF(self.logo.rect()))
        p.setFont(QFont('DejaVu Sans',18,QFont.Bold));p.setPen(QColor('#ff9a32'));p.drawText(QRectF(220,125,520,28),Qt.AlignCenter,'ARCOS')
        if f['screen']=='MENU':
            for i,label in enumerate(('Start','Eject','Settings','Off')):
                y=160+i*74;selected=i==f['selection'];p.setPen(QColor('#ff9a32' if selected else '#080808'))
                if selected:p.drawRoundedRect(QRectF(280,y-5,400,58),13,13)
                symbol=('start','eject','settings','off')[i];variant='focused' if selected else 'normal'
                from PySide6.QtSvg import QSvgRenderer
                from PySide6.QtCore import QByteArray
                render=QSvgRenderer(QByteArray(assets(self.tab.host.root).read('05_arcos/icons/'+symbol+'-'+variant+'.svg')))
                render.render(p,QRectF(305,y+7,32,32));p.setPen(QColor('#eeeef0'));p.setFont(QFont('DejaVu Sans',23))
                p.drawText(QRectF(360,y,300,48),Qt.AlignVCenter,label)
            p.setFont(QFont('DejaVu Sans',12));p.setPen(QColor('#c5cbd0'))
            error=(self.tab.state or {}).get('media',{}).get('error','')
            note=(self.tab.state.get('game',{}).get('name','STRUTHIO')+' · USB game media ready') if f['card'] else 'Insert a game thumb drive' if not f.get('ejected') else 'Game media safely ejected'
            if error.startswith(('MEDIA_CORRUPT','USB_','FAT_')):note='Game media could not be read. Replace or reinsert it.'
            elif error.startswith(('MEDIA_INCOMPATIBLE','MEDIA_STALE')):note='Game media is incompatible with this system.'
            p.drawText(QRectF(130,470,700,25),Qt.AlignCenter,note)
        elif f['screen']=='SETTINGS':
            p.setFont(QFont('DejaVu Sans',24));p.setPen(QColor('#eeeef0'));p.drawText(QRectF(160,190,640,60),Qt.AlignCenter,'Settings')
            p.setFont(QFont('DejaVu Sans',18));p.drawText(QRectF(120,280,720,50),Qt.AlignCenter,'Event volume: '+str(f['volume']))
            p.setFont(QFont('DejaVu Sans',12));p.drawText(QRectF(100,375,760,45),Qt.AlignCenter,'Left / Right changes · X returns')
        else:
            p.setFont(QFont('DejaVu Sans',22));p.setPen(QColor('#eeeef0'));p.drawText(QRectF(180,220,600,90),Qt.AlignCenter,'Console off')


class VirtualConsoleTab(ServiceTab):
    def __init__(self,host):
        super().__init__(host);self.session_id=None;self.state=None;self.busy=False;self.job_id=None;self.autoboot=False;self.held=set();self.port=0
        row=QHBoxLayout();title=QLabel('ARC-1 virtual console');title.setProperty('arcRole','section');row.addWidget(title);row.addStretch()
        self.needs_input=False
        self.fixture=QComboBox()
        for label,value in [('STRUTHIO thumb drive','normal'),('Missing media','missing'),('Corrupt media','corrupt'),('Incompatible media','incompatible'),('Bad BOT status tag','bad_csw'),('Malformed FAT32','bad_fat'),('First native game','sample'),('Stale D213 readiness','stale_d213'),('Reset before ARC-OS','reset_participant')]:self.fixture.addItem(label,value)
        row.addWidget(self.fixture);self.outer.addLayout(row);self.outer.addWidget(self.status)
        self.status.setText('Functional host model · physical ARC-1 remains blocked')
        self.actions=QGridLayout();self.action_buttons=[];self.buttons={}
        for label,name,fn in [('Boot virtual console','power',self.run),('Pause','pause',self.pause),('Step','step',self.step),('Insert / replace drive','usb-media',self.insert),('Remove drive','eject',self.remove),('Capture','camera',self.capture)]:
            button=QPushButton(icon(host.root,name),label);button.clicked.connect(fn);button.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed);self.action_buttons.append(button);self.buttons[label]=button
        for original,short in [('Boot virtual console','Boot / Resume'),('Insert / replace drive','Insert media'),('Remove drive','Eject media')]:
            self.buttons[original].setText(short)
        self.outer.addLayout(self.actions);self.arrange_actions()
        self.pages=QTabWidget();self.outer.addWidget(self.pages,1)
        engineering=QWidget();v=QVBoxLayout(engineering);v.setContentsMargins(0,5,0,0)
        self.summary=QLabel('Boot the model. Follow its startup, game media and native C execution.');self.summary.setWordWrap(True);v.addWidget(self.summary)
        from .arc_trace import RecordedEvents
        overview=QHBoxLayout();self.event_strip=RecordedEvents();overview.addWidget(self.event_strip,1)
        preview_box=QVBoxLayout();self.mini_screen=ConsoleScreen(self)
        self.mini_screen.setMinimumSize(210,118);self.mini_screen.setMaximumSize(280,158)
        preview_box.addWidget(self.mini_screen)
        enlarge=QPushButton('Enlarge graphics');enlarge.clicked.connect(lambda:self.pages.setCurrentIndex(1))
        preview_box.addWidget(enlarge);overview.addLayout(preview_box);v.addLayout(overview)
        filters=QHBoxLayout();filters.addWidget(QLabel('Trace'));self.trace_filter=QComboBox();self.trace_filter.addItems(['All events','Session milestones','USB media','12F RTL']);self.trace_filter.setCurrentIndex(1);self.trace_filter.currentIndexChanged.connect(self.render_trace);filters.addWidget(self.trace_filter);filters.addStretch();v.addLayout(filters)
        self.trace=QTreeWidget();self.trace.setHeaderLabels(['Step / event','Evidence and state','Value / detail']);self.trace.setColumnWidth(0,240);self.trace.setColumnWidth(1,280);v.addWidget(self.trace,1)
        from .ux_polish import empty_hint;empty_hint(self.trace,'Boot the virtual console to record its startup, media and game events here.')
        limitation=QLabel('Clock/DDR uses the existing synthetic 128 MiB fixture, not the 64 MiB F133 design. USB media uses modeled high-speed enumeration, BOT, block reads and read-only FatFs. One existing 12F BRAM command path runs real RTL. Configuration and D213 startup remain fixtures; physical USB, full/low-speed HID, DDR and electrical timing remain unqualified.');limitation.setWordWrap(True);limitation.hide()
        from PySide6.QtWidgets import QToolButton, QHeaderView
        scope=QToolButton();scope.setText('Model scope && limitations');scope.setCheckable(True);scope.toggled.connect(limitation.setVisible)
        v.addWidget(scope);v.addWidget(limitation)
        self.trace.header().setSectionResizeMode(0,QHeaderView.Interactive)
        self.trace.header().setSectionResizeMode(1,QHeaderView.Interactive)
        self.trace.setColumnWidth(0,300);self.trace.setColumnWidth(1,160)
        self.trace.header().setSectionResizeMode(2,QHeaderView.Stretch)
        row=QHBoxLayout()
        for label,name,fn in [('Brain Link','brain-link',host.show_brain_link),('Boot source','firmware',lambda:host.open_document(host.root/'software/arcos/bsp/virtual_console/virtual_boot.c')),('SDK diagnostics','diagnostic',host.show_arcos_diagnostics),('Native starter','firmware',host.show_native_project)]:
            b=QPushButton(icon(host.root,name),label);b.clicked.connect(lambda checked=False,f=fn:self.open_link(f));row.addWidget(b)
        fold(row,groups=[('Open',('Brain Link','Boot source','SDK diagnostics','Native starter'))]);row.addStretch()
        v.addLayout(row);self.pages.addTab(engineering,icon(host.root,'trace'),'Engineering')
        graphics=QWidget();g=QVBoxLayout(graphics);g.setContentsMargins(0,0,0,0);self.screen=ConsoleScreen(self);g.addWidget(self.screen,1)
        self.graphic_note=QLabel('Native C launcher state and game draw commands · diagnostic graphics · click the screen for controller keys');self.graphic_note.setWordWrap(True);g.addWidget(self.graphic_note)
        row=QHBoxLayout()
        for label,key in [('↑',Qt.Key_Up),('↓',Qt.Key_Down),('←',Qt.Key_Left),('→',Qt.Key_Right),('A / Z',Qt.Key_Z),('B / X',Qt.Key_X),('Start / Enter',Qt.Key_Return)]:
            b=QPushButton(label);b.pressed.connect(lambda k=key:self.key(k,True));b.released.connect(lambda k=key:self.key(k,False));row.addWidget(b)
        g.addLayout(row);self.pages.addTab(graphics,icon(host.root,'hdmi'),'Console graphics')
        self.plan_page=self.make_plan();self.pages.addTab(self.plan_page,icon(host.root,'nor'),'Offline image plan')
        self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setObjectName('outputText');self.pages.addTab(self.details,icon(host.root,'evidence'),'Evidence / SDK')
        self.timer=QTimer(self);self.timer.setInterval(17);self.timer.timeout.connect(self.step)
        self.poll=QTimer(self);self.poll.setInterval(300);self.poll.timeout.connect(self.poll_job)
        QTimer.singleShot(0,self.refresh)
    def arrange_actions(self):
        width=self.width()-24;need=max(b.sizeHint().width() for b in self.action_buttons)
        columns=6 if width>=need*6+30 else 3 if width>=need*3+12 else 2 if width>=need*2+6 else 1
        while self.actions.count():self.actions.takeAt(0)
        for i,b in enumerate(self.action_buttons):self.actions.addWidget(b,i//columns,i%columns)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'action_buttons'):self.arrange_actions()
    def title(self):return 'Virtual console · ARC-OS'
    def open_link(self,fn):
        if self.host.tabs.pin(self):fn()
    def refresh(self):self.call('console.inspect',{},lambda r:self.details.setPlainText(json.dumps(r,indent=2)))
    def job(self,action):
        tool=action if action.startswith(('console.','arcos.')) else 'arcos.'+action
        if self.job_id:return
        if not self.host.save_all():return
        def started(job):self.job_id=job['id'];self.status.setText('Queued '+tool);self.poll.start()
        self.call('jobs.submit',{'tool':tool,'request_key':uuid.uuid4().hex,'timeout':180},started)
    def poll_job(self):
        if not self.job_id:return
        r=self.kernel.dispatch('jobs.get',{'id':self.job_id},self.principal)
        if not r['ok']:return
        job=r['result'];self.status.setText(job['tool']+' · '+job['state'])
        if job['state'] in ('Completed','Failed','Cancelled','Interrupted'):
            self.job_id=None;self.poll.stop();self.details.setPlainText(json.dumps(job,indent=2))
            if job['state']=='Completed' and self.autoboot:self.autoboot=False;self.boot()
            else:self.autoboot=False
    def run(self):
        if self.job_id:return
        if self.session_id and self.state and self.state['state']=='RUNNING':self.timer.start();return
        def ready(r):
            if not r.get('build') or not r['build']['current']:self.autoboot=True;self.job('console.build')
            else:self.boot()
        self.call('console.inspect',{},ready)
    def boot(self):
        def started(state):self.session_id=state['id'];self.loaded(state);self.timer.start()
        self.call('console.open',{'fixture':self.fixture.currentData()},started,self.rejected)
    def rejected(self,error):
        # A refused boot leaves no live session; show its recorded events so the refusal is inspectable.
        message=error.get('message','');marker='recorded trace '
        if marker not in message:return
        folder=message.rsplit(marker,1)[1].strip().rsplit('/',1)[0]
        try:saved=io.strict_json(io.project_path(self.host.root,folder+'/state.json',private=True).read_bytes())
        except (OSError,ValueError):return
        self.timer.stop();self.session_id=None;self.state=saved;self.trace_sequence=saved.get('last_sequence')
        self.event_strip.set_trace(saved['trace']);self.render_trace()
        refusal=next((row for row in reversed(saved['trace']) if row['event']!='BOOT_REJECTED' and any(word in row['state'] for word in ('REJECT','INVALID','FAIL','STALE'))),None)
        self.status.setText('Boot rejected · '+(refusal['event']+' · '+refusal['state'].replace('_',' ').lower() if refusal else 'see recorded events')+' · no media or game admitted')
        self.status.setToolTip(message)
    def pause(self):self.timer.stop();self.held.clear();self.status.setText('Paused · explicit logical ticks; no board timing claim')
    def key(self,key,down):
        if down:self.held.add(key)
        else:self.held.discard(key)
        self.needs_input=True;self.step()
    def step(self):
        if not self.session_id or self.busy or self.stopping or (self.state and self.state['state']!='RUNNING'):return
        hat=next((KEYS[k][0] for k in (Qt.Key_Up,Qt.Key_Right,Qt.Key_Down,Qt.Key_Left) if k in self.held),8)
        buttons=0
        for k in self.held:buttons|=KEYS[k][1]
        self.busy=True;self.needs_input=False
        worker=self.call('console.input',{'id':self.session_id,'port':self.port,'hat':hat,'buttons':buttons},self.loaded)
        if worker:
            def finished():
                self.busy=False
                if self.needs_input:QTimer.singleShot(0,self.step)
            worker.finished.connect(finished)
            worker.ready.connect(lambda r:self.timer.stop() if not r.get('ok') else None)
        else:self.busy=False
    def loaded(self,state):
        self.state=state;f=state['frame'];self.screen.frame=f;self.screen.update()
        self.mini_screen.frame=f;self.mini_screen.update();self.event_strip.set_trace(state['trace'])
        self.status.setText('HOST MODEL · '+f['screen'].replace('_',' ').capitalize()+' · '+state.get('game',{}).get('name','')+' · '+('USB ready' if f['card'] else state['media']['error'] or 'No mounted media'))
        self.status.setToolTip('HOST_SIM · source '+state['revision']+' · physical target unqualified')
        self.summary.setText('Federation → USB media → ARC-OS → '+state.get('game',{}).get('name','STRUTHIO'))
        if getattr(self,'trace_sequence',None)!=state['last_sequence']:
            self.render_trace();self.trace_sequence=state['last_sequence']
        self.host.instruments.virtual_snapshot(state)
        from .arc_desktop import refresh
        refresh(self.host)
        if state['state']!='RUNNING':self.timer.stop()
    def render_trace(self):
        self.trace.clear()
        if not self.state:return
        mode=self.trace_filter.currentIndex()
        boot={'RESET','CLOCK_DDR','NOR_RESIDENT_CONTRACT','F133_BOOT_INFORMATION','FPGA12','D213_FPGA45','ARCOS_BOOT_INFORMATION','ARCOS','BOOT_REJECTED','MEDIA_DISCOVERY','ARCOS_STATE','FAT_MOUNT','FAT_OPEN_GAME_ARC','FPGA12_RTL_EXCHANGE'}
        for row in self.state['trace']:
            name=row['event'];details=row['details']
            if mode==1 and name not in boot and not name.startswith('FEDERATION_'):continue
            if mode==2 and name not in ('USB_HUB_CHILD_READY','USB_MEDIA_ENUMERATED','SCSI_READ10','BOT_RESET_RECOVERY','FAT_MOUNT','FAT_OPEN_GAME_ARC','FAT_FILE_READ','USB_FAT_MEDIA','MEDIA_DISCOVERY','MEDIA_SERVICE'):continue
            if mode==3 and row.get('class')!='RTL_SIM' and 'RTL' not in name:continue
            display=details
            if name=='FPGA12_RTL_EXCHANGE':display={k:details.get(k) for k in ('simulated_cycles','engine_status','request_sha256','response_sha256')}
            from sdk.cli.arc1cli.console_events import LABELS
            full=json.dumps(display,sort_keys=True)
            if isinstance(display,dict):
                brief=' · '.join(str(key).replace('_',' ')+': '+str(value) for key,value in list(display.items())[:3])
            else:brief=str(display)
            texts=[LABELS.get(name,name.replace('_',' ').capitalize()),row.get('class','HOST_SIM'),row['state'].replace('_',' ').capitalize()+' · '+brief]
            item=QTreeWidgetItem(texts)
            for column,text in enumerate(texts):item.setToolTip(column,name+'\n'+full)
            self.trace.addTopLevelItem(item)
        self.trace.scrollToBottom()
    def insert(self):
        if self.fixture.currentData() in ('stale_d213','reset_participant'):
            self.status.setText('This participant fault is checked during startup. Boot a new virtual console with it selected.');return
        if self.session_id:self.call('console.media',{'id':self.session_id,'fixture':self.fixture.currentData()},self.loaded)
    def remove(self):
        if self.session_id:self.call('console.media',{'id':self.session_id},self.loaded)
    def stop(self):
        self.timer.stop();self.held.clear()
        if self.session_id:
            self.kernel.dispatch('console.close',{'id':self.session_id},self.principal);self.session_id=None
    def reset(self):self.stop();self.run()
    def capture(self):
        if not self.state:return
        out=self.host.root/'build/virtual_console/captures';out.mkdir(parents=True,exist_ok=True);self.screen.grab().save(str(out/'console.png'));io.write_json(out/'state.json',self.state);self.status.setText('Saved native-state view and source-bound trace in build/virtual_console/captures')
    def make_plan(self):
        page=QWidget();v=QVBoxLayout(page);note=QLabel('Inspect an image without discovering, enumerating or opening any physical device. Accepted format/geometry never means board boot is qualified.');note.setWordWrap(True);v.addWidget(note)
        self.profile=QComboBox()
        for label,value in [('eGON format · host tool ceiling only','egon-format-tool-limit'),('QEMU virt RV64 · existing virtual geometry','qemu-virt-rv64-existing'),('F133 board · binding unavailable','r10-f133-board')]:self.profile.addItem(label,value)
        v.addWidget(self.profile);row=QHBoxLayout()
        for label,fn in [('Inspect generated format fixture',self.plan_fixture),('Choose image…',self.choose_image),('Build model / fixtures',lambda:self.job('console.build'))]:
            b=QPushButton(icon(self.host.root,'nor'),label);b.clicked.connect(fn);row.addWidget(b)
        v.addLayout(row);self.plan_output=QPlainTextEdit();self.plan_output.setReadOnly(True);v.addWidget(self.plan_output,1);return page
    def plan_fixture(self):self.plan('build/virtual_console/virtual-probe.egon')
    def choose_image(self):
        filename,_=QFileDialog.getOpenFileName(self,'Inspect an image offline','','Images (*.bin *.elf *.egon);;All files (*)')
        if not filename:return
        path=Path(filename)
        if path.is_symlink() or path.stat().st_size>16*1024*1024:self.plan_output.setPlainText('Select a regular image up to 16 MiB.');return
        name='build/virtual_console/plan_inputs/'+uuid.uuid4().hex+'.image';target=io.project_path(self.host.root,name,False);io.atomic(target,path.read_bytes());self.plan(name)
    def plan(self,path):
        def done(r):self.plan_output.setPlainText(json.dumps(r,indent=2))
        self.call('console.plan',{'path':path,'profile':self.profile.currentData()},done)
    def shutdown_engineering(self):
        self.timer.stop();self.poll.stop();super().shutdown_engineering();self.stop()
