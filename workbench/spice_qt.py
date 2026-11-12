"""Native circuit waveforms and measurements within the existing workspaces."""
import bisect
import json
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QRectF,QPointF,Signal
from PySide6.QtGui import QColor,QPainter,QPainterPath,QPen,QFont
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QComboBox,QTabWidget,QPlainTextEdit,QTreeWidget,QTreeWidgetItem,QHeaderView,QApplication,QScrollArea,QFrame)
from . import spice_tools, record_io as io
from .engineering_kernel import operator
from .project_context import refusal


class Waveform(QWidget):
    value_changed=Signal(str)
    COLORS=('#ffae47','#cce9f7','#65d2db','#c3b1ff','#a2d894','#fa9fc7','#e8db8c')

    def __init__(self):
        super().__init__();self.data=None;self.spec=None;self.channel=None;self.selected=None
        self.setMinimumHeight(210);self.setMouseTracking(True);self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName('Native ngspice waveform; exact samples also available in the CSV file')
        self.setToolTip('Move over a curve to inspect the nearest native sample. Left/right arrows step through samples.')

    def set_data(self,data,spec,channel=None):
        self.data=data;self.spec=spec;self.channel=channel;self.selected=None;self.update()

    def columns(self):
        if not self.data:return []
        names=[v['name'] for v in self.data['variables']]
        return [i for i in range(1,len(names)) if self.channel is None or names[i]==self.channel]

    def area(self):return QRectF(self.rect()).adjusted(65,18,-20,-54)

    def sample(self,index):
        self.selected=max(0,min(index,len(self.data['rows'])-1));row=self.data['rows'][self.selected]
        axis=f'{row[0]*1e9:.5g} ns' if self.spec['axis_unit']=='s' else f'{row[0]:.5g} V'
        text='Sample '+str(self.selected)+' · '+axis+' · '+' · '.join(self.data['variables'][i]['name']+' = '+f'{row[i]:.6g} V' for i in self.columns())
        self.value_changed.emit(text);self.update()

    def mouseMoveEvent(self,event):
        if not self.data:return
        area=self.area();rows=self.data['rows']
        ratio=max(0,min(1,(event.position().x()-area.left())/max(1,area.width())))
        x=rows[0][0]+ratio*(rows[-1][0]-rows[0][0]);axis=[r[0] for r in rows]
        index=min(bisect.bisect_left(axis,x),len(rows)-1)
        if index and abs(axis[index-1]-x)<abs(axis[index]-x):index-=1
        self.sample(index)

    def keyPressEvent(self,event):
        if self.data and event.key() in (Qt.Key_Left,Qt.Key_Right):
            self.sample((self.selected or 0)+(1 if event.key()==Qt.Key_Right else -1));event.accept()
        else:super().keyPressEvent(event)

    def paintEvent(self,event):
        painter=QPainter(self);painter.fillRect(self.rect(),QColor('#10161c'))
        painter.setRenderHint(QPainter.Antialiasing);painter.setFont(QFont('DejaVu Sans',10))
        area=self.area()
        if not self.data:
            painter.setPen(QColor('#bbc9d1'));painter.drawText(self.rect(),Qt.AlignCenter,'Run a circuit model to view native samples.');return
        rows=self.data['rows'];columns=self.columns();x0=rows[0][0];x1=rows[-1][0]
        low=min(0,min(r[c] for r in rows for c in columns));high=max(r[c] for r in rows for c in columns)
        high=max(high,low+1e-6);pad=(high-low)*.08;low-=pad;high+=pad
        def point(row,c):return QPointF(area.left()+(row[0]-x0)/(x1-x0)*area.width(),area.bottom()-(row[c]-low)/(high-low)*area.height())
        for tick in range(5):
            y=area.bottom()-tick/4*area.height();value=low+tick/4*(high-low)
            painter.setPen(QPen(QColor('#2d3a43'),1));painter.drawLine(QPointF(area.left(),y),QPointF(area.right(),y))
            painter.setPen(QColor('#b9c6ce'));painter.drawText(QRectF(0,y-10,58,20),Qt.AlignRight|Qt.AlignVCenter,f'{value:.3g}')
            x=area.left()+tick/4*area.width();axis=x0+tick/4*(x1-x0)
            if self.spec['axis_unit']=='s':axis*=1e9
            painter.drawText(QRectF(x-30,area.bottom()+6,60,22),Qt.AlignCenter,f'{axis:.4g}')
        painter.drawText(QRectF(area.left(),area.bottom()+29,area.width(),24),Qt.AlignCenter,
                         'Time (ns)' if self.spec['axis_unit']=='s' else 'Ideal supply sweep (V)')
        painter.drawText(QRectF(4,1,55,20),Qt.AlignCenter,'V')
        painter.save();painter.setClipRect(area)
        for c in columns:
            path=QPainterPath();path.moveTo(point(rows[0],c))
            for row in rows[1:]:path.lineTo(point(row,c))
            painter.setPen(QPen(QColor(self.COLORS[(c-1)%len(self.COLORS)]),2));painter.drawPath(path)
        if self.selected is not None:
            x=point(rows[self.selected],columns[0]).x();painter.setPen(QPen(QColor('#ffffff'),1,Qt.DashLine))
            painter.drawLine(QPointF(x,area.top()),QPointF(x,area.bottom()))
            for c in columns:
                painter.setBrush(QColor(self.COLORS[(c-1)%len(self.COLORS)]));painter.drawEllipse(point(rows[self.selected],c),4,4)
        painter.restore()


class SpiceTab(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.kernel=host.ledger_bridge.kernel;self.principal=operator()
        self.job_id=None;self.job_state=None;self.result=None
        box=QVBoxLayout(self);box.addWidget(QLabel('ngspice · circuit checks'))
        self.tool=QLabel();self.tool.setWordWrap(True);box.addWidget(self.tool)
        row=QHBoxLayout();self.profile=QComboBox()
        for key,title in spice_tools.PROFILES.items():self.profile.addItem(title,key)
        self.profile.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);self.profile.setMinimumContentsLength(1)
        self.profile.setStyleSheet('QComboBox { min-width:0px; }')
        row.addWidget(self.profile,1);self.run_button=QPushButton('Run model');self.stop_button=QPushButton('Stop job')
        self.stop_button.setEnabled(False);self.run_button.clicked.connect(lambda:self.start('spice.'+self.profile.currentData()))
        self.stop_button.clicked.connect(self.stop);row.addWidget(self.run_button);row.addWidget(self.stop_button)
        for title,callback in (('Qualify ngspice',lambda:self.start('spice.qualify')),('Jobs / evidence',host.show_engineering),('Refresh',self.refresh)):
            button=QPushButton(title);button.clicked.connect(callback);row.addWidget(button)
        from .command_rows import fold
        fold(row,keep=('Run model','Stop job'));box.addLayout(row)
        self.status=QLabel('No circuit run selected.');self.status.setWordWrap(True);box.addWidget(self.status)
        history=QHBoxLayout();history.addWidget(QLabel('Recorded run'));self.runs=QComboBox();history.addWidget(self.runs,1)
        self.runs.activated.connect(self.choose_run);box.addLayout(history)
        self.pages=QTabWidget();box.addWidget(self.pages,1)
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(0,0,0,0)
        self.channels=QComboBox();self.channels.currentIndexChanged.connect(self.select_channel);layout.addWidget(self.channels)
        self.plot=Waveform();layout.addWidget(self.plot,1)
        self.legend=QLabel();self.legend.setWordWrap(True);layout.addWidget(self.legend)
        self.cursor=QLabel('Move over a curve or use the arrow keys for exact native samples.');self.cursor.setWordWrap(True)
        self.plot.value_changed.connect(self.cursor.setText);layout.addWidget(self.cursor)
        scroller=QScrollArea();scroller.setWidgetResizable(True);scroller.setFrameShape(QFrame.NoFrame);scroller.setWidget(page)
        self.pages.addTab(scroller,'Waveform')
        self.metrics=QTreeWidget();self.metrics.setRootIsDecorated(False);self.metrics.setHeaderLabels(['Measurement','Native / derived value'])
        self.metrics.header().setSectionResizeMode(0,QHeaderView.Stretch);self.metrics.setColumnWidth(1,270);self.pages.addTab(self.metrics,'Measurements')
        self.deck=QPlainTextEdit();self.deck.setReadOnly(True);self.pages.addTab(self.deck,'Circuit model')
        self.scope=QPlainTextEdit();self.scope.setReadOnly(True);self.pages.addTab(self.scope,'Sources / assumptions')
        files=QWidget();layout=QVBoxLayout(files);layout.setContentsMargins(0,0,0,0)
        row=QHBoxLayout();self.file=QComboBox();self.file.setStyleSheet('QComboBox { min-width:0px; }');self.file.currentIndexChanged.connect(self.select_file);row.addWidget(self.file,1)
        self.copy=QPushButton('Copy CSV path');self.copy.clicked.connect(self.copy_csv);row.addWidget(self.copy);layout.addLayout(row)
        self.preview=QPlainTextEdit();self.preview.setReadOnly(True);layout.addWidget(self.preview,1)
        self.pages.addTab(files,'Native files')
        self.note=QLabel('Reduced passive models with ideal stimuli. Full board, IC and physical behaviour are unqualified; fabrication HOLD.')
        self.note.setWordWrap(True);box.addWidget(self.note)
        self.timer=QTimer(self);self.timer.setInterval(400);self.timer.timeout.connect(self.poll);self.timer.start();self.refresh()

    def title(self):return 'ngspice · circuits'

    def set_running(self,running):
        self.run_button.setEnabled(bool(spice_tools.discover()['executable']) and not running)
        self.stop_button.setEnabled(running);self.profile.setEnabled(not running);self.runs.setEnabled(not running)

    def refresh(self):
        response=self.kernel.dispatch('spice.inspect',{},self.principal)
        if not response['ok']:self.status.setText(response['error']['message']);return
        data=response['result'];tool=data['tool']
        self.tool.setText('R10 · native ngspice detected · numerical fixtures repeat each job' if tool['executable'] else tool['reason'])
        self.tool.setToolTip(tool.get('executable') or 'ngspice is not installed')
        jobs=[j for j in self.kernel.listing('jobs') if j['tool'].startswith('spice.')]
        current=self.runs.currentData();self.runs.clear()
        for job in sorted(jobs,key=lambda j:j.get('created',0),reverse=True):self.runs.addItem(job['tool']+' · '+job['state']+' · '+job['id'][:8],job['id'])
        index=self.runs.findData(current or self.job_id)
        if index>=0:self.runs.setCurrentIndex(index)
        active=[j for j in jobs if j['state'] in ('Queued','Running')]
        if active:
            latest=max(active,key=lambda j:j['created'])
            if latest['id']!=self.job_id:self.watch_job(latest)
            return
        self.set_running(False)
        if data['latest'].get('schema')==spice_tools.CONTRACT:self.result=data['latest'];self.display()
        else:self.status.setText(data['latest']['reason'])

    def choose_run(self,index):self.watch_job(self.kernel.record('jobs',self.runs.itemData(index)))

    def start(self,tool):
        response=self.kernel.dispatch('jobs.submit',{'tool':tool,'timeout':90},self.principal)
        if not response['ok']:self.status.setText(response['error']['message']);return
        if refusal(response['result']):self.status.setText(refusal(response['result']));return
        self.watch_job(response['result'])

    def watch_job(self,job):
        self.job_id=job['id'];self.job_state=None;self.result=None
        self.plot.set_data(None,None);self.metrics.clear();self.deck.clear();self.scope.clear();self.preview.clear();self.file.clear()
        self.channels.clear();self.legend.clear();self.cursor.setText('Waiting for a complete, verified native waveform.')
        profile=job['tool'].removeprefix('spice.');index=self.profile.findData(profile)
        if index>=0:self.profile.setCurrentIndex(index)
        self.set_running(job['state'] in ('Queued','Running'));self.poll()

    def stop(self):
        if self.job_id:
            response=self.kernel.dispatch('jobs.cancel',{'id':self.job_id},self.principal)
            self.status.setText('Cancellation requested.' if response['ok'] else response['error']['message'])

    def poll(self):
        if self.host._closing or not self.job_id:return
        response=self.kernel.dispatch('jobs.get',{'id':self.job_id},self.principal)
        if not response['ok']:return
        job=response['result'];state=job['state']
        if state==self.job_state:return
        self.job_state=state;self.status.setText(state+' · '+job['tool']+' · '+job['id'][:8])
        if state in ('Completed','Failed','Cancelled','Paused'):
            self.set_running(False)
            if state in ('Completed','Failed'):
                result=self.kernel.dispatch('spice.report',{'id':self.job_id},self.principal)
                if result['ok']:self.result=result['result'];self.display()
                else:self.status.setText(state+' · no intact circuit report: '+result['error']['message'])
            else:self.status.setText(state+' · no completed circuit verdict for this attempt.')
            index=self.runs.findData(self.job_id)
            if index<0:self.runs.insertItem(0,job['tool']+' · '+state+' · '+job['id'][:8],job['id']);index=0
            self.runs.setCurrentIndex(index)

    def native_path(self,name):
        prefix='build/spice/runs/'+self.result['id']+'/attempts/'+self.result['attempt']+'/native/'
        return io.project_path(self.host.root,prefix+name)

    def display(self):
        result=self.result;data=result.get('waveform');spec=result.get('model')
        if spec:
            index=self.profile.findData(spec['profile'])
            if index>=0:self.profile.setCurrentIndex(index)
        self.tool.setText('Recorded engine: ngspice '+result.get('tool',{}).get('version','unknown')+' · '+
                          ('operation fixtures passed' if result.get('qualification',{}).get('qualified') else 'qualification incomplete'))
        self.status.setText(result['status']+' · '+(str(data['points'])+' native samples · '+spec['analysis'] if data else result['reason'])+
                            '\nInputs '+result['source_currentness']+' · source '+('unchanged' if result.get('source_unchanged') else 'not verified')+' · HOST_SIM · fabrication HOLD')
        self.channels.blockSignals(True);self.channels.clear();self.channels.addItem('All modeled channels',None)
        if data:
            for v in data['variables'][1:]:self.channels.addItem(v['name'],v['name'])
        self.channels.blockSignals(False);self.select_channel()
        self.metrics.clear()
        for measure in result.get('measurements',[]):
            for key,value in measure.items():
                if key=='name':continue
                unit='';label=key.replace('_',' ')
                if isinstance(value,float):
                    if key.endswith('_seconds'):value=value*1e9;unit=' ns';label=label.removesuffix(' seconds')
                    text=f'{value:.9g}'+unit
                else:text=str(value)
                item=QTreeWidgetItem([measure['name']+' · '+label,text]);self.metrics.addTopLevelItem(item)
        self.deck.setPlainText(self.native_path('circuit.cir').read_text() if result.get('native') else 'No project model was executed.')
        scope={'model':(spec or {}).get('title','No project model'),
               'assumptions':(spec or {}).get('assumptions',[]),'omitted':(spec or {}).get('omitted',''),
               'source_currentness':result['source_currentness'],'source_export_binding':(spec or {}).get('export_binding'),
               'source_components':(spec or {}).get('components',[]),'source_node_mapping':(spec or {}).get('source_nodes',{}),
               'run':{k:v for k,v in result.items() if k not in ('model','waveform','artifacts','qualification')}}
        self.scope.setPlainText(json.dumps(scope,indent=2))
        self.file.clear()
        for name in ('waveform.csv','waveform.raw','circuit.cir','stdout.txt','stderr.txt'):
            try:path=self.native_path(name)
            except (ValueError,OSError):continue
            self.file.addItem(name,str(path))
        self.copy.setEnabled(bool(data));self.select_file()
        self.pages.setCurrentIndex(0 if data else 3)
        self.note.setText(('R80 '+spec['components'][0]['value']+' + C129 '+spec['components'][1]['value']+' · ideal 3.3 V / 1 ns test edge. Driver / receiver omitted. '
                           if data and spec['profile']=='clock' else 'Six isolated ideal dividers; supervisor ICs and PCB effects omitted. '
                           if data else result['reason']+' ')+ 'Reduced model only; physical gates HOLD.')

        if hasattr(self.host,'arc_inspector'):self.host.arc_inspector.refresh()

    def select_channel(self,*_):
        if not self.result or not self.result.get('waveform'):self.plot.set_data(None,None);return
        self.plot.set_data(self.result['waveform'],self.result['model'],self.channels.currentData())
        names=[self.result['waveform']['variables'][i]['name'] for i in self.plot.columns()]
        self.legend.setText('   ·   '.join('<span style="color:'+self.plot.COLORS[(i-1)%len(self.plot.COLORS)]+'">'+self.result['waveform']['variables'][i]['name']+'</span>' for i in self.plot.columns())+
                            ('   ·   Matching F45 / F12 curves overlap.' if self.result['operation']=='dividers' else ''))
        self.cursor.setText('Move over a curve or use the arrow keys for exact native samples.')

    def select_file(self,*_):
        path=self.file.currentData()
        if not path:self.preview.clear();return
        with Path(path).open(errors='replace') as f:raw=f.read(20000)
        self.preview.setPlainText(path+'\n\n'+raw+'\n\n[Preview limited to 20,000 characters; the complete file is retained.]')

    def copy_csv(self):
        if self.result and self.result.get('waveform'):
            QApplication.clipboard().setText(str(self.native_path('waveform.csv')))
            self.host.statusBar().showMessage('Copied the verified waveform CSV path.',5000)
