"""Recorded HDL traces, exact four-state cursor values and native diagnostics."""
from bisect import bisect_right
import json
from PySide6.QtCore import Qt,QTimer,Signal,QPointF,QRectF
from PySide6.QtGui import QPainter,QPen,QColor,QPixmap
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QTreeWidget, QTreeWidgetItem, QPlainTextEdit, QTabWidget, QHeaderView, QSlider, QLineEdit, QScrollArea
from sdk.cli.arc1cli import hdl_waveforms as wave
from . import hdl_tools as hdl,surfer_tools as surfer,record_io as io
from .engineering_kernel import operator
from .project_context import refusal


def time_label(tick,fs):
    ns=tick*fs/1000000
    return f'{ns/1000000:.3f} ms' if ns>=1000000 else f'{ns/1000:.3f} us' if ns>=1000 else f'{ns:.3f} ns'


class WaveformPlot(QWidget):
    cursor_changed=Signal(object)
    def __init__(self):
        super().__init__();self.trace=None;self.names=[];self.cursor=0;self.start=0;self.end=1;self.setMinimumHeight(260)
    def load(self,trace,names):
        self.trace=trace;self.names=names[:8];self.setMinimumHeight(max(260,40+36*len(self.names)));self.start=0;self.end=max(1,trace['end_tick']);self.cursor=0;self.update()
    def set_cursor(self,tick):
        self.cursor=max(0,min(self.trace['end_tick'] if self.trace else 0,int(tick)));self.update();self.cursor_changed.emit(self.cursor)
    def zoom(self,factor):
        if not self.trace:return
        width=max(2,int((self.end-self.start)*factor));width=min(width,max(2,self.trace['end_tick']))
        center=self.cursor if self.start<=self.cursor<=self.end else (self.start+self.end)//2
        self.start=max(0,min(center-width//2,max(0,self.trace['end_tick']-width)));self.end=self.start+width;self.update()
    def full(self):
        if self.trace:self.start=0;self.end=max(1,self.trace['end_tick']);self.update()
    def edge(self,direction):
        if not self.trace or not self.names:return
        changes=self.trace['signals'][self.names[0]]['changes'];i=bisect_right(changes,self.cursor,key=lambda pair:pair[0])
        i=i if direction>0 else max(0,i-2)
        if i<len(changes):self.set_cursor(changes[i][0])
    def mousePressEvent(self,event):
        if self.trace and event.position().x()>=160:
            fraction=max(0,min(1,(event.position().x()-160)/max(1,self.width()-180)))
            self.set_cursor(self.start+round(fraction*(self.end-self.start)))
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#0d141b'));p.setPen(QColor('#bacbd9'))
        if not self.trace:p.drawText(16,32,'Run a simulation to inspect its recorded digital trace.');return
        left=160;right=self.width()-20;width=max(1,right-left);span=max(1,self.end-self.start)
        row_height=max(36,min(58,(self.height()-40)//max(1,len(self.names))))
        def x(t):return left+(t-self.start)*width/span
        p.setPen(QColor('#33404d'))
        metrics=p.fontMetrics();labels=[time_label(self.start+int(span*i/5),self.trace['tick_fs']) for i in range(6)]
        count=max(1,min(6,width//(max(metrics.horizontalAdvance(label) for label in labels)+16)))
        for i in range(count):
            fraction=i/max(1,count-1);xx=left+width*fraction;p.drawLine(QPointF(xx,25),QPointF(xx,self.height()))
            label=metrics.elidedText(time_label(self.start+int(span*fraction),self.trace['tick_fs']),Qt.ElideRight,width)
            text_x=max(left,min(xx-metrics.horizontalAdvance(label)/2,right-metrics.horizontalAdvance(label)))
            p.setPen(QColor('#9cafc0'));p.drawText(QPointF(text_x,18),label);p.setPen(QColor('#33404d'))
        for index,name in enumerate(self.names):
            row=self.trace['signals'][name];changes=row['changes'];center=48+index*row_height
            bits=wave.value_at(row,self.cursor);p.setPen(QColor('#d5e0e8'));p.drawText(8,center-3,name.rsplit('.',1)[-1][:20]);p.setPen(QColor('#ffab58'));p.drawText(8,center+15,wave.display_value(bits)[:24])
            lo=max(0,bisect_right(changes,self.start,key=lambda pair:pair[0])-1);hi=bisect_right(changes,self.end,key=lambda pair:pair[0])
            p.setPen(QPen(QColor('#72d1b5'),1.4))
            if hi-lo>4000:
                for px in range(width):
                    t0=self.start+int(px*span/width);t1=self.start+int((px+1)*span/width)
                    i0=bisect_right(changes,t0,key=lambda pair:pair[0]);i1=bisect_right(changes,t1,key=lambda pair:pair[0]);value=wave.value_at(row,t0)
                    if i1-i0>1:
                        p.fillRect(QRectF(left+px,center-10,1,20),QColor('#42685f'));continue
                    y=center-8 if value=='1' else center+8 if value=='0' else center
                    p.setPen(QColor('#ffac54') if 'x' in value or 'z' in value else QColor('#72d1b5'))
                    p.drawLine(QPointF(left+px,y),QPointF(left+px+1,y))
            else:
                value=wave.value_at(row,self.start);previous=self.start
                final_value=changes[hi-1][1] if hi else value
                for tick,next_value in changes[lo:hi]+[[self.end,final_value]]:
                    tick=max(self.start,min(self.end,tick))
                    if tick<previous:continue
                    unknown='x' in value or 'z' in value;p.setPen(QPen(QColor('#ffac54') if unknown else QColor('#72d1b5'),1.4))
                    if row['width']==1:
                        yy=center-8 if value=='1' else center+8 if value=='0' else center
                        yn=center-8 if next_value=='1' else center+8 if next_value=='0' else center
                        p.drawLine(QPointF(x(previous),yy),QPointF(x(tick),yy));p.drawLine(QPointF(x(tick),yy),QPointF(x(tick),yn))
                    else:
                        p.drawLine(QPointF(x(previous),center-8),QPointF(x(tick),center-8));p.drawLine(QPointF(x(previous),center+8),QPointF(x(tick),center+8))
                        if x(tick)-x(previous)>55:p.drawText(QPointF(x(previous)+3,center+4),wave.display_value(value)[:16])
                    previous=tick;value=next_value
        if self.start<=self.cursor<=self.end:
            p.setPen(QPen(QColor('#ff8b31'),1.5));p.drawLine(QPointF(x(self.cursor),25),QPointF(x(self.cursor),self.height()))


class HdlTab(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.kernel=host.ledger_bridge.kernel;self.principal=operator();self.job_id=None;self.job_state=None;self.result=None;self.trace=None
        box=QVBoxLayout(self);title=QLabel('HDL · simulation, diagnostics and recorded waveforms');title.setWordWrap(True);box.addWidget(title)
        self.tools=QLabel();self.tools.setWordWrap(True);box.addWidget(self.tools)
        row=QHBoxLayout();self.engine=QComboBox();self.engine.addItems(['icarus','verilator']);row.addWidget(self.engine)
        self.profile=QComboBox();self.profile.setStyleSheet('QComboBox { min-width:0px; }')
        for key,spec in hdl.PROFILES.items():self.profile.addItem(spec['title'],key)
        row.addWidget(self.profile,1);box.addLayout(row)
        row=QHBoxLayout();self.run_button=QPushButton('Run profile');self.stop_button=QPushButton('Stop job');self.stop_button.setEnabled(False)
        self.run_button.clicked.connect(lambda:self.start(self.engine.currentText()+'.'+self.profile.currentData()));self.stop_button.clicked.connect(self.stop)
        row.addWidget(self.run_button);row.addWidget(self.stop_button)
        for label,callback in (('Surfer native capture',self.render_surfer),('Qualify Icarus',lambda:self.start('icarus.qualify')),
                               ('Qualify Verilator',lambda:self.start('verilator.qualify')),('Qualify Surfer',lambda:self.start('surfer.qualify')),
                               ('Compare pump outputs',self.compare),('Jobs / evidence',host.show_engineering),('Refresh',self.refresh)):
            button=QPushButton(label);button.clicked.connect(callback);row.addWidget(button)
        from .command_rows import fold
        fold(row,keep=('Run profile','Stop job'));box.addLayout(row)
        self.status=QLabel('Icarus: original RGMII/SDRAM benches. Verilator: RTL lint or shared pump simulation.');self.status.setWordWrap(True);box.addWidget(self.status)
        row=QHBoxLayout();row.addWidget(QLabel('Recorded run'));self.runs=QComboBox();self.runs.setStyleSheet('QComboBox { min-width:0px; }');row.addWidget(self.runs,1);box.addLayout(row)
        self.runs.activated.connect(lambda index:self.watch_job(self.kernel.record('jobs',self.runs.itemData(index))))
        self.pages=QTabWidget();box.addWidget(self.pages,1)
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(0,0,0,0)
        controls=QHBoxLayout()
        for label,callback in (('+',lambda:self.plot.zoom(.2)),('−',lambda:self.plot.zoom(5)),('Fit',lambda:self.plot.full()),('Previous',lambda:self.plot.edge(-1)),('Next',lambda:self.plot.edge(1))):
            button=QPushButton(label);button.setStyleSheet('QPushButton { min-width:0px; padding-left:8px; padding-right:8px; }');button.clicked.connect(callback);controls.addWidget(button)
        layout.addLayout(controls);self.plot=WaveformPlot();plot_scroll=QScrollArea();plot_scroll.setWidgetResizable(True);plot_scroll.setMinimumHeight(140);plot_scroll.setWidget(self.plot);layout.addWidget(plot_scroll,1)
        row=QHBoxLayout();row.addWidget(QLabel('Cursor tick'));self.cursor=QLineEdit('0');self.cursor.setMaximumWidth(150);self.cursor.editingFinished.connect(self.set_tick);row.addWidget(self.cursor)
        self.cursor_time=QLabel();row.addWidget(self.cursor_time,1);layout.addLayout(row)
        self.slider=QSlider(Qt.Horizontal);self.slider.setRange(0,10000);self.slider.valueChanged.connect(self.slide);layout.addWidget(self.slider)
        self.plot.cursor_changed.connect(self.cursor_changed);self.pages.addTab(page,'Waveform')
        self.signals=QTreeWidget();self.signals.setRootIsDecorated(False);self.signals.setHeaderLabels(['Recorded signal · select up to 8','Bits','Changes','X / Z'])
        self.signals.header().setStretchLastSection(False);self.signals.header().setSectionResizeMode(0,QHeaderView.Stretch);self.signals.itemChanged.connect(self.selection_changed);self.pages.addTab(self.signals,'Signals')
        self.findings=QTreeWidget();self.findings.setRootIsDecorated(False);self.findings.setHeaderLabels(['Severity / code','Source','Line','Native message']);self.findings.setColumnWidth(0,150);self.findings.setColumnWidth(1,240);self.pages.addTab(self.findings,'Diagnostics')
        self.logs=QPlainTextEdit();self.logs.setReadOnly(True);self.pages.addTab(self.logs,'Native log')
        self.scope=QPlainTextEdit();self.scope.setReadOnly(True);self.pages.addTab(self.scope,'Sources / scope')
        scroll=QScrollArea();scroll.setWidgetResizable(True);self.native_image=QLabel('Run a Surfer native capture to view its actual rendered waveform and saved-state receipt.');self.native_image.setWordWrap(True);self.native_image.setAlignment(Qt.AlignTop|Qt.AlignLeft);scroll.setWidget(self.native_image);self.pages.addTab(scroll,'Surfer capture')
        self.note=QLabel('Digital RTL evidence only. Shaded dense regions need zooming; cursor values use exact recorded events. X / Z remain explicit. Physical timing / programming HOLD.');self.note.setWordWrap(True);box.addWidget(self.note)
        self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.poll);self.timer.start();host.master_stop_controller.completed.connect(lambda _:self.poll());self.refresh()
    def title(self):return 'HDL · simulation / traces'
    def set_running(self,running):
        self.run_button.setEnabled(not running);self.stop_button.setEnabled(running);self.engine.setEnabled(not running);self.profile.setEnabled(not running);self.runs.setEnabled(not running)
    def refresh(self):
        self.tools.setText('Icarus: '+hdl.discover('icarus')['state']+' · Verilator: '+hdl.discover('verilator')['state']+' · Surfer capture: '+surfer.discover()['state'])
        jobs=[j for j in self.kernel.listing('jobs') if j['tool'].startswith(('icarus.','verilator.','surfer.'))];current=self.runs.currentData();self.runs.clear()
        for job in sorted(jobs,key=lambda j:j['created'],reverse=True):self.runs.addItem(job['tool']+' · '+job['state']+' · '+job['id'][:8],job['id'])
        index=self.runs.findData(current or self.job_id)
        if index>=0:self.runs.setCurrentIndex(index)
        active=[j for j in jobs if j['state'] in ('Queued','Running')]
        if active:self.watch_job(max(active,key=lambda j:j['created']));return
        self.set_running(False)
        if jobs and not self.result:self.watch_job(max(jobs,key=lambda j:j['created']))
    def start(self,tool):
        response=self.kernel.dispatch('jobs.submit',{'tool':tool,'timeout':600},self.principal)
        if response['ok'] and refusal(response['result']):self.status.setText(refusal(response['result']))
        elif response['ok']:self.watch_job(response['result'])
        else:self.status.setText(response['error']['message'])
    def render_surfer(self):
        key=self.profile.currentData();engine=self.engine.currentText()
        if engine=='verilator' and key!='pump':self.status.setText('This Verilator profile is lint only. Select Icarus for its simulation trace.');return
        self.start('surfer.'+engine+'_'+key)
    def compare(self):
        result=self.kernel.dispatch('hdl.compare_pump',{},self.principal);self.status.setText(json.dumps(result['result'],indent=2) if result['ok'] else result['error']['message'])
    def watch_job(self,job):
        self.job_id=job['id'];self.job_state=None;self.result=None;self.timer.start();self.trace=None;self.plot.trace=None;self.plot.update()
        self.native_image.clear();self.native_image.setMinimumSize(0,0);self.native_image.setText('No native Surfer capture is attached to this run.')
        for widget in (self.signals,self.findings,self.logs,self.scope):widget.clear()
        family,key=job['tool'].split('.',1)
        if family=='surfer' and key in surfer.PROFILES:family,key=surfer.PROFILES[key]
        if family in ('icarus','verilator'):self.engine.setCurrentText(family)
        index=self.profile.findData(key)
        if index>=0:self.profile.setCurrentIndex(index)
        self.set_running(job['state'] in ('Queued','Running'));self.poll()
    def stop(self):
        if self.job_id:self.kernel.dispatch('jobs.cancel',{'id':self.job_id},self.principal)
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
                result=self.kernel.dispatch('surfer.report' if job['tool'].startswith('surfer.') else 'hdl.report',{'id':self.job_id},self.principal)
                if result['ok']:self.result=result['result'];self.display()
                else:self.status.setText(state+' · no intact native record: '+result['error']['message'])
            else:self.status.setText(state+' · no completed simulation/capture verdict for this attempt.')
            index=self.runs.findData(self.job_id)
            if index<0:self.runs.insertItem(0,job['tool']+' · '+state+' · '+job['id'][:8],job['id']);index=0
            self.runs.setCurrentIndex(index)
    def display(self):
        result=self.result;source=result
        if result.get('parent'):
            response=self.kernel.dispatch('hdl.report',{'id':result['parent']['id']},self.principal)
            if response['ok']:source=response['result']
        self.status.setText(result['status']+' · '+result.get('kind','Native Surfer state / capture' if result.get('capture') else 'Capability fixture')+'\nInputs '+result['source_currentness']+' · '+result['class']+' · programming HOLD')
        if source.get('waveform'):
            try:
                path=hdl.trace_path(self.host.root,source)
                if io.sha(path)!=source['waveform']['sha256']:raise ValueError('Trace changed after verification')
                self.trace=wave.parse_vcd(path)
            except (OSError,ValueError) as exc:
                self.status.setText('INVALID TRACE · '+str(exc));self.trace=None;return
            self.signals.blockSignals(True);self.signals.clear()
            preferred={'rgmii':['rxc','rxd','rx_ctl','cnt_ok','cnt_crc','o_txd'],'sdram':['clk','init_done','cmd_valid','cmd_ready','rd_valid','rd_data'],'pump':['clk','txc','start','f_valid','f_data','received']}[source['profile_key']]
            names=[]
            for name,row in self.trace['signals'].items():
                item=QTreeWidgetItem([name,str(row['width']),str(len(row['changes'])),'YES' if any('x' in v or 'z' in v for _,v in row['changes']) else '—']);item.setData(0,Qt.UserRole,name)
                selected=name.rsplit('.',1)[-1] in preferred;item.setCheckState(0,Qt.Checked if selected else Qt.Unchecked);self.signals.addTopLevelItem(item)
                if selected:names.append(name)
            self.signals.blockSignals(False);self.plot.load(self.trace,names);self.plot.set_cursor(0)
        for row in result.get('diagnostics',[]):self.findings.addTopLevelItem(QTreeWidgetItem([row['severity']+' '+row.get('code',''),row.get('file',''),str(row.get('line','')),row['message']]))
        self.logs.clear()
        for name in result['artifacts']:
            if name.endswith(('native/stdout.txt','native/stderr.txt','native/run/stdout.txt','native/run/stderr.txt','native/surfer.log')):
                with io.project_path(self.host.root,name).open(errors='replace') as file:self.logs.appendPlainText(name+'\n'+file.read(100000))
        self.scope.setPlainText(json.dumps({k:v for k,v in result.items() if k not in ('artifacts','dependencies')},indent=2,ensure_ascii=False))
        if result.get('capture'):
            name='build/surfer/runs/'+result['id']+'/attempts/'+result['attempt']+'/native/surfer.png'
            self.native_image.setPixmap(QPixmap(str(io.project_path(self.host.root,name))));self.native_image.setMinimumSize(1280,800);self.pages.setCurrentIndex(5)
        else:self.pages.setCurrentIndex(0 if self.trace else 2 if result.get('kind')=='LINT' else 4)
        self.note.setText('Native Surfer capture; interactive cursor controls are on Waveform. Physical timing unqualified; programming HOLD.' if result.get('capture') else 'Digital trace · exact four-state cursor · zoom shaded regions for detail. Physical timing unqualified; programming HOLD.')
        if hasattr(self.host,'arc_inspector'):self.host.arc_inspector.refresh()
    def selection_changed(self,item,column):
        names=[self.signals.topLevelItem(i).data(0,Qt.UserRole) for i in range(self.signals.topLevelItemCount()) if self.signals.topLevelItem(i).checkState(0)==Qt.Checked]
        if len(names)>8:self.signals.blockSignals(True);item.setCheckState(0,Qt.Unchecked);self.signals.blockSignals(False);return
        self.plot.names=names;self.plot.setMinimumHeight(max(260,40+36*len(names)));self.plot.update()
    def set_tick(self):
        try:self.plot.set_cursor(int(self.cursor.text()))
        except ValueError:self.cursor.setText(str(self.plot.cursor))
    def slide(self,value):
        if self.trace:self.plot.set_cursor(value*self.trace['end_tick']//10000)
    def cursor_changed(self,tick):
        self.cursor.setText(str(tick));self.cursor_time.setText(time_label(tick,self.trace['tick_fs']) if self.trace else '')
        if self.trace:
            self.slider.blockSignals(True);self.slider.setValue(round(tick*10000/max(1,self.trace['end_tick'])));self.slider.blockSignals(False)
            if hasattr(self.host,'arc_inspector'):self.host.arc_inspector.refresh()
