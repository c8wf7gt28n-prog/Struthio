"""A working calculator and What if graph over the same exact mathematical IR."""
from .text_prompts import writing_prompt
from fractions import Fraction
from PySide6.QtCore import Qt,QTimer,QUrl,QPointF,QRectF
from PySide6.QtGui import QPainter,QPen,QColor,QPainterPath,QDesktopServices
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QComboBox,QLabel,QPlainTextEdit,QSpinBox,QSplitter
from .shell2 import button


class MathGraph(QWidget):
    def __init__(self):
        super().__init__();self.data=None;self.setMinimumHeight(260);self.setAccessibleName('What if graph with exact linear boundaries')

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.fillRect(self.rect(),QColor('#F8F7F3'));p.setPen(QColor('#35383C'))
        if not self.data:p.drawText(self.rect(),Qt.AlignCenter,'Choose a quantity and a range, then draw What if.');return
        samples=self.data['samples'];valid=[s for s in samples if s.get('value')]
        if not valid:p.drawText(self.rect(),Qt.AlignCenter,'This range has no defined numerical samples.');return
        try:
            import math
            xs=[float(Fraction(s['input']['rational'])) for s in samples]
            ys=[float(Fraction(s['value']['rational'])) for s in valid]+[float(Fraction(s['limit']['rational'])) for s in valid if s.get('limit')]
            if not all(math.isfinite(v) for v in xs+ys):raise OverflowError
        except OverflowError:p.drawText(self.rect(),Qt.AlignCenter,'Beyond the graph scale. The exact result is retained.');return
        xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys);pad=max((ymax-ymin)*.12,abs(ymax)*.04,.1);ymin-=pad;ymax+=pad
        plot=QRectF(70,28,max(80,self.width()-100),max(80,self.height()-85))
        def point(x,y):return QPointF(plot.left()+(x-xmin)/(xmax-xmin)*plot.width(),plot.bottom()-(y-ymin)/(ymax-ymin)*plot.height())
        for i in range(6):
            y=ymin+(ymax-ymin)*i/5;at=point(xmin,y);p.setPen(QColor('#DDDCD6'));p.drawLine(QPointF(plot.left(),at.y()),QPointF(plot.right(),at.y()))
            p.setPen(QColor('#55575A'));p.drawText(QRectF(0,at.y()-10,62,22),Qt.AlignRight|Qt.AlignVCenter,format(y,'.4g'))
        for which,color in [('value','#2459A9'),('limit','#B56945')]:
            path=QPainterPath();active=False
            for sample in samples:
                if not sample.get(which):active=False;continue
                pos=point(float(Fraction(sample['input']['rational'])),float(Fraction(sample[which]['rational'])))
                if active:path.lineTo(pos)
                else:path.moveTo(pos);active=True
            p.setPen(QPen(QColor(color),2));p.drawPath(path)
        p.setPen(QPen(QColor('#45484B'),1));p.drawRect(plot)
        for boundary in self.data['boundaries']:
            if not boundary['within_sample_range']:continue
            x=float(Fraction(boundary['input']['rational']));pos=point(x,ymin)
            p.setPen(QPen(QColor('#7C8273'),1,Qt.DashLine));p.drawLine(QPointF(pos.x(),plot.top()),pos)
            p.setPen(QColor('#35383C'));p.drawText(QPointF(pos.x()+5,plot.top()+17),'Boundary '+boundary['input']['rational']+' '+boundary['input']['unit'])
        p.setPen(QColor('#35383C'));p.drawText(QRectF(plot.left(),plot.bottom()+8,plot.width(),22),Qt.AlignCenter,
            self.data['variable']+' ('+self.data['input_unit']+')  '+str(xmin)+' to '+str(xmax))
        p.drawText(QPointF(plot.left(),18),'Result ('+valid[0]['value']['unit']+')');p.end()


class CalculatorPane(QWidget):
    def __init__(self,problem_pane):
        super().__init__();self.pane=problem_pane;self.action=None;self.receipt=None;self.job=None;self.office=None
        box=QVBoxLayout(self);form=QFormLayout();box.addLayout(form)
        # V-21: the four writing fields carry the one writing invitation (poem) with their purpose as help; choice boxes are named.
        self.examples=QComboBox();self.examples.addItems(['Concurrent memory case','Typical power estimate','Declared power limit','Custom expression'])
        self.examples.setAccessibleName('Explore a prepared expression');self.examples.currentIndexChanged.connect(self.preset);form.addRow('Explore',self.examples)
        self.expression=QLineEdit();self.expression.setAccessibleName('Mathematical expression');writing_prompt(self.expression,'Mathematical expression');form.addRow('Expression',self.expression)
        self.unit=QLineEdit();writing_prompt(self.unit, 'Automatic, or MiB, MB, W, B/s…');form.addRow('Show unit',self.unit)
        self.assumptions=QLineEdit();self.assumptions.setAccessibleName('Calculation assumptions');writing_prompt(self.assumptions,'Calculation assumptions');form.addRow('Assumptions',self.assumptions)
        self.backend=QComboBox();self.backend.addItems(['EXACT','SYMPY','Z3']);self.backend.setAccessibleName('Calculation engine');form.addRow('Engine',self.backend)
        row=QHBoxLayout();calculate=button('Calculate and keep','primary');calculate.clicked.connect(self.calculate);row.addWidget(calculate)
        office=button('Make checked Calc and Writer files','quiet');office.clicked.connect(self.start_office);row.addWidget(office);box.addLayout(row)
        self.saved=QComboBox();self.saved.setAccessibleName('Saved calculations');self.saved.currentIndexChanged.connect(self.open_saved);box.addWidget(self.saved)
        self.answer=QLabel('Save a problem first. Calculations retain their own assumptions.');self.answer.setWordWrap(True);self.answer.setTextFormat(Qt.PlainText);box.addWidget(self.answer)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setAccessibleName('Mathematical result and open questions');self.details.setMaximumHeight(135);box.addWidget(self.details)
        row=QHBoxLayout();self.variable=QComboBox();self.variable.setAccessibleName('What if quantity');row.addWidget(self.variable,2)
        self.start=QLineEdit('0');self.start.setAccessibleName('What if start');self.stop=QLineEdit('10');self.stop.setAccessibleName('What if end')
        writing_prompt(self.start,'What if start');writing_prompt(self.stop,'What if end')
        row.addWidget(QLabel('From'));row.addWidget(self.start);row.addWidget(QLabel('to'));row.addWidget(self.stop)
        draw=button('Draw What if','quiet');draw.clicked.connect(self.draw);row.addWidget(draw);box.addLayout(row)
        self.graph=MathGraph();box.addWidget(self.graph,1)
        self.boundary=QLabel('Graphs sample the declared model. A linear boundary is calculated exactly.');self.boundary.setWordWrap(True);self.boundary.setTextFormat(Qt.PlainText);box.addWidget(self.boundary)
        self.office_status=QLabel();self.office_status.setWordWrap(True);self.office_status.setTextFormat(Qt.PlainText);box.addWidget(self.office_status)
        opened=button('Open generated working files','quiet');opened.clicked.connect(self.open_files);box.addWidget(opened)
        self.timer=QTimer(self);self.timer.setInterval(750);self.timer.timeout.connect(self.poll_office);self.preset(0)

    def preset(self,index):
        presets=[('buffer_A + buffer_B + workspace <= memory_limit','MiB','All three allocations are concurrent.'),
            ('voltage * assumed_typical_current','W','Declared typical-current assumptions; no maximum-current guarantee.'),
            ('voltage * declared_current_limit','W','Declared supply and current limit.'),('','','')]
        if index>=len(presets):return
        expression,unit,assumptions=presets[index];self.expression.setText(expression);self.unit.setText(unit);self.assumptions.setText(assumptions)

    def reload(self,selected=None):
        problem=self.pane.current
        self.saved.blockSignals(True);self.saved.clear();self.saved.addItem('Saved calculations',None)
        if problem:
            result=self.pane.call('math.list',{'id':problem['id']})
            for action in (result or {}).get('actions',[]):self.saved.addItem(action['backend']+' · '+(action.get('expression') or 'Typed model'),action['id'])
        self.saved.setCurrentIndex(max(0,self.saved.findData(selected)));self.saved.blockSignals(False)
        self.open_saved()

    def calculate(self):
        if not self.pane.current:self.answer.setText('Save the problem first.');return
        original={k:self.pane.current[k] for k in ('title','goals','variables','assumptions','questions','candidates')}
        original['sources']=[{k:s[k] for k in ('copy','path','label')} for s in self.pane.current['sources']]
        if self.pane.arguments()!=original:self.answer.setText('Save the problem changes before calculating.');return
        args={**self.pane.bound(),'expression':self.expression.text(),'backend':self.backend.currentText(),
            'assumptions':[self.assumptions.text()] if self.assumptions.text().strip() else []}
        if self.unit.text().strip():args['output_unit']=self.unit.text().strip()
        action=self.pane.call('math.prepare',args)
        if not action:return
        observed=self.pane.call('math.run',{'action':action['id']})
        if observed:self.reload(action['id'])

    def open_saved(self):
        ident=self.saved.currentData();self.action=None;self.receipt=None;self.variable.clear();self.graph.data=None;self.graph.update()
        if not ident:return
        value=self.pane.call('math.get',{'id':ident})
        if not value:return
        self.action=value['action'];self.receipt=value['receipt']
        self.expression.setText(self.action.get('expression') or '');self.unit.setText(self.action.get('output_unit') or '')
        self.assumptions.setText('; '.join(self.action['model']['assumptions']));self.backend.setCurrentText(self.action['backend'])
        for name,variable in self.action['model']['variables'].items():self.variable.addItem(name+' ('+variable['unit']+')',name)
        preferred=self.variable.findData('workspace')
        if preferred>=0:self.variable.setCurrentIndex(preferred)
        if not self.receipt:self.answer.setText('Prepared without an observed result.');return
        result=self.receipt['snapshot'];evaluation=result.get('evaluation',result);parts=[]
        for output in evaluation.get('outputs',[]):
            if 'value' not in output:parts.append('Unknown');continue
            if output['kind']=='quantity':v=output['value'];parts.append(v['rational']+' '+v['unit'])
            else:
                left,right=output.get('left',{}),output.get('right',{});parts.append(str(output['value'])+' · '+left.get('decimal','')+' '+left.get('unit','')+' compared with '+right.get('decimal','')+' '+right.get('unit',''))
        self.answer.setText(' · '.join(parts) if parts else result.get('reason') or result.get('state','Unknown'))
        self.details.setPlainText('Engine: '+self.action['backend']+' · '+str(result.get('state'))+'\nProblem revision '+str(self.action['problem_revision'])+' · '+value['applicability'].lower().replace('_',' ')+'\nUnder: '+'; '.join(self.action['model']['assumptions'])+
            '\nScope: declared model. Open questions: '+'; '.join((self.pane.current or {}).get('questions',[])))

    def draw(self):
        if not self.action:self.answer.setText('Calculate and keep an expression first.');return
        if not self.variable.currentData():self.boundary.setText('This expression has no variable to vary.');return
        data=self.pane.call('math.sweep',{'action':self.action['id'],'variable':self.variable.currentData(),'start':self.start.text(),'stop':self.stop.text(),'count':81})
        if not data:return
        self.graph.data=data;self.graph.update()
        boundaries=data['boundaries']
        self.boundary.setText('; '.join('Exact boundary: '+b['input']['rational']+' '+b['input']['unit']+' under the declared assumptions.' for b in boundaries) or data['notice'])

    def start_office(self):
        if self.timer.isActive():return
        if not self.receipt:self.office_status.setText('Calculate and keep a complete numerical result first.');return
        plan=self.pane.call('math.office.prepare',{'receipt':self.receipt['id']})
        if not plan:return
        job=self.pane.call('math.office.run',{'action':plan['id'],'expected_digest':plan['binding_digest']})
        if job:self.job=job['id'];self.office=None;self.office_status.setText('Calc and Writer job '+job['state'].lower()+'. Inspect or cancel it in Jobs.');self.timer.start()

    def poll_office(self):
        value=self.pane.call('math.office.result',{'job':self.job})
        if not value:self.timer.stop();return
        if value['state'] in ('Queued','Running'):self.office_status.setText('Native Calc and Writer are working on the bound calculation.');return
        self.timer.stop();self.office=value
        if value['state']=='AVAILABLE':
            published=self.pane.call('math.office.publish',{'job':self.job})
            if not published:self.office_status.setText('Native files were checked. Copying them into the working folder did not complete; inspect the problem message.');return
            self.office['directory']=published['directory']
            self.office_status.setText('Recalculated, saved and reopened. '+str(len(value['measurement']))+' formula measurements agree. '+published.get('notice','Working files are ready.'))
        else:self.office_status.setText(value['state']+': '+str(value.get('error') or 'Inputs changed; inspect the historical receipt.'))

    def open_files(self):
        if self.office and self.office.get('directory'):QDesktopServices.openUrl(QUrl.fromLocalFile(self.office['directory']))
