"""Human-facing develop/debug loop using the same case services as agents."""
from .text_prompts import writing_prompt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTreeWidget,QTreeWidgetItem,QHeaderView,QPlainTextEdit,QApplication
from . import development,clip
from .command_rows import fold
from .ux_polish import overline, readable_error, empty_hint

class DevelopmentTab(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;self.data=None
        v=QVBoxLayout(self)
        heading=overline('Development Lab','reproduce, edit and compare an isolated case');v.addWidget(heading)
        description=QLabel('Use ARC-1 evidence → reproduce a fault → edit a candidate → compare results → review')
        description.setWordWrap(True);v.addWidget(description)
        self.banner=QLabel();self.banner.setWordWrap(True);self.banner.setObjectName('simBanner');v.addWidget(self.banner)
        self.buttons={};row=QHBoxLayout()
        for text,fn in [('Prepare case',self.prepare),('Open working source',self.open_source),
                        ('Run baseline',lambda:window.run_development('baseline')),
                        ('Run working copy',lambda:window.run_development('working')),
                        ('Compare both',lambda:window.run_development('compare'))]:
            b=QPushButton(text);b.clicked.connect(fn);row.addWidget(b);self.buttons[text]=b
        fold(row,keep=('Prepare case','Run baseline','Run working copy','Compare both'))
        v.addLayout(row)
        self.state=QLabel();self.state.setWordWrap(True);v.addWidget(self.state)
        self.results=QTreeWidget();self.results.setRootIsDecorated(False)
        self.results.setHeaderLabels(['Source','Check','Result','Freshness']);empty_hint(self.results,'Prepare a case, then run the baseline to see its checks here.')
        self.results.setColumnWidth(0,100);self.results.setColumnWidth(1,360);self.results.setColumnWidth(2,95)
        self.results.header().setSectionResizeMode(3,QHeaderView.Stretch);v.addWidget(self.results,2)
        self.output=QPlainTextEdit();self.output.setReadOnly(True);self.output.setMaximumHeight(190);writing_prompt(self.output, 'Actual compiler and test output appears here.');v.addWidget(self.output,1)
        row=QHBoxLayout()
        for text,fn in [('Refresh evidence',self.refresh),('View source diff',self.show_diff),
                        ('Copy AI brief',self.copy_brief),('Draft in Graphite',self.draft_clip),('Open run report',self.open_report)]:
            b=QPushButton(text);b.clicked.connect(fn);row.addWidget(b)
        fold(row,keep=('View source diff',))
        v.addLayout(row)
        self.ai_state=QLabel();self.ai_state.setWordWrap(True);v.addWidget(self.ai_state)
        footer=QLabel('HOST_SIM candidate · Imported hardware preserved · Independent review pending · No board programming')
        footer.setWordWrap(True);v.addWidget(footer);self.refresh()

    def title(self):return 'Development Lab'
    def info(self):return 'Reproducible ARC-1 development cases · baseline versus working source · source-bound evidence'
    def prepare(self):
        from .execution_lock import ExecutionLock
        lock=ExecutionLock(self.window.root)
        if not lock.acquire():
            self.state.setText('Another command is running. Prepare the case when it finishes.');return
        try:development.prepare(self.window.root);self.refresh()
        except (ValueError,OSError) as exc:self.window.message('Could not prepare case',str(exc),error=True)
        finally:lock.release()
    def open_source(self):
        if not self.data or not self.data['prepared']:return
        self.window.open_document(self.window.root/(development.WORK+'/src/arc1_diag.c'))
    def refresh(self):
        self.results.clear();self.output.clear()
        try:
            self.data=development.inspect(self.window.root)
            ready=self.data['prepared'];self.buttons['Prepare case'].setEnabled(not ready)
            for name in ('Open working source','Run baseline','Run working copy','Compare both'):self.buttons[name].setEnabled(ready)
            self.banner.setText('P10 diagnostic ticket isolation\nForeign, copied and pre-reset tickets must not change the wrong counters.')
            self.state.setText('Evidence: '+self.data['state']+' · '+self.data['result_origin']+' · Saved sources only; independent review pending.')
            for run in (self.data.get('latest') or {}).get('runs',[]):
                fresh='CURRENT' if run.get('fresh') else 'STALE — rerun after edits'
                for check in run['checks']:
                    self.results.addTopLevelItem(QTreeWidgetItem([run['variant'],check['name'],check['status'],fresh]))
                    for line in check['stdout'].splitlines():
                        if line.startswith('CASE '):
                            _,name,result=line.split();self.results.addTopLevelItem(QTreeWidgetItem([run['variant'],name.replace('_',' '),result,fresh]))
                    self.output.appendPlainText(run['variant']+' / '+check['name']+'\n'+check['stdout']+check['stderr'])
            settings=clip.Settings.load()
            self.ai_state.setText('AI interface: structured JSONL available · Graphite: '+('key configured (connection not tested)' if settings.ready() else 'not configured; external chat unavailable')+'\nCopy AI brief includes this case, actual results and source hashes. Draft in Graphite does not send until you press Send.')
        except (ValueError,OSError,KeyError) as exc:
            self.state.setText('Development evidence unavailable · '+readable_error(type(exc).__name__+': '+str(exc),self.window.root));self.data=None
    def show_diff(self):
        import difflib
        root=self.window.root;parts=[]
        try:
            for name in development.SOURCE_NAMES:
                original=(root/development.BASE/name).read_text().splitlines(True)
                current=(root/development.WORK/'src'/name).read_text().splitlines(True)
                parts.extend(difflib.unified_diff(original,current,fromfile='imported/'+name,tofile='working/'+name))
            self.output.setPlainText(''.join(parts) or 'Working source matches imported baseline.')
        except OSError as exc:self.window.message('Diff unavailable',str(exc),error=True)
    def copy_brief(self):
        try:
            text=development.brief(self.window.root);QApplication.clipboard().setText(text)
            self.output.setPlainText(text);self.state.setText('AI brief copied — case, results and source hashes. Preview below.')
        except (ValueError,OSError) as exc:self.window.message('Brief unavailable',str(exc),error=True)
    def draft_clip(self):
        try:
            brief=development.brief(self.window.root)
            if self.window.clip_overlay is None or not self.window.clip_overlay.isVisible():self.window.open_clip()
            overlay=self.window.clip_overlay
            if overlay.busy:return
            overlay.input.setText(brief);overlay.input.setCursorPosition(0)
            self.state.setText('Case brief drafted in Graphite. No external request sent.')
        except (ValueError,OSError) as exc:self.window.message('Brief unavailable',str(exc),error=True)
    def open_report(self):
        data=development.inspect(self.window.root)
        if data.get('report_path'):self.window.open_document(self.window.root/data['report_path'])
        else:self.state.setText('Run the case to create its first report.')
    def refresh_if_changed(self):
        if not self.data:return
        try:
            data=development.inspect(self.window.root)
            signature=lambda d:(d.get('state'),(d.get('latest') or {}).get('created_unix'))
            if signature(data)!=signature(self.data):self.refresh()
        except (ValueError,OSError):self.refresh()
