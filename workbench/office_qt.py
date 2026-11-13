"""Native office desk over private working records and explicit candidate review."""
import copy, json, uuid
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QProcess,QProcessEnvironment
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QWidget, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QLineEdit, QPlainTextEdit, QComboBox, QTabWidget, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QHeaderView, QDialogButtonBox, QCheckBox, QFileDialog, QInputDialog, QMessageBox, QScrollArea, QSizePolicy
from .engine import engineering
from .engineering_kernel import operator
from . import office_service,office_runtime
from sdk.cli.arc1cli import office_tables as t,office_documents as d
from . import locations

def plain(value=''):
    v=QLabel(value);v.setWordWrap(True);v.setTextFormat(Qt.PlainText);v.setMinimumWidth(0);return v
def invoke(host,op,args=None):
    if host.concern.store is None or host.concern.store.path.resolve()!=office_service.path().resolve():raise ValueError('Office and desktop profiles differ; reopen with one profile.')
    r=engineering(host.root).dispatch('office.'+op,args or {},operator())
    if not r['ok']:raise ValueError(r['error']['message'])
    return r['result']
def is_office(catalog,key):
    with catalog.db() as db:return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='office_documents'").fetchone() and db.execute('SELECT 1 FROM office_documents WHERE id=?',(key,)).fetchone())
def review_text(value):
    lines=[]
    if value.get('operation'):lines.append('Action: '+value['operation']+'\nFormat: '+value['format'])
    doc=value.get('document');source=value.get('origin',{}).get('source',{})
    if source:lines.append('Original: '+source.get('name','')+'\nSHA-256: '+source.get('sha256',''))
    if value.get('source_state'):lines.append('Source state: '+str(value['source_state'].get('state')))
    if doc and doc.get('schema')==t.SCHEMA:
        for sheet in doc['sheets']:
            lines.append('\nSheet: '+sheet['name'])
            for loc,c in sorted(sheet['cells'].items(),key=lambda x:t.xy(x[0]))[:100]:lines.append(loc+' · '+c['type']+' · '+str(c['formula'] if c['formula'] is not None else c['value'])+(' '+c['unit'] if c['unit'] else ''))
            if len(sheet['cells'])>100:lines.append('Preview shows the first 100 cells. Details contains every supported cell.')
    elif doc:
        lines.append(doc['title'])
        for b in doc['blocks'][:100]:lines.append(b['text'] if b['kind']=='paragraph' else '\n'.join(' | '.join(r) for r in b['rows'][:30]))
    for change in value.get('changes',[])[:100]:
        lines.append('\nChange: '+str(change.get('sheet',''))+' '+str(change.get('cell',change.get('position',''))));lines.append('Before: '+str(change.get('before')));lines.append('After: '+str(change.get('after')))
    if value.get('losses'):lines.extend(['\nConversion losses:']+[r['path']+': '+r['reason'].replace('_',' ').capitalize() for r in value['losses']])
    if value.get('notice'):lines.append(value['notice'])
    if not lines:lines.append(json.dumps(value,indent=2,ensure_ascii=False))
    lines.append('\nOriginals and accepted engineering records remain separate from this working action.');return '\n'.join(lines)
class Review(QDialog):
    def __init__(self,parent,value,title='Review working copy'):
        super().__init__(parent);self.setWindowTitle(title);self.resize(820,680);box=QVBoxLayout(self)
        box.addWidget(plain('Review content, source identity and losses. This changes no original or accepted engineering record.'))
        pages=QTabWidget();self.preview=QPlainTextEdit();self.preview.setReadOnly(True);self.preview.setPlainText(review_text(value));self.preview.setAccessibleName('Readable office preview and losses');pages.addTab(self.preview,'Preview')
        self.reading=QPlainTextEdit();self.reading.setReadOnly(True);self.reading.setPlainText(json.dumps(value,indent=2,ensure_ascii=False));self.reading.setAccessibleName('Office candidate content and losses');pages.addTab(self.reading,'Details');box.addWidget(pages,1)
        self.ack=QCheckBox('I reviewed the proposed working copy and its losses.');box.addWidget(self.ack);buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);self.ok=buttons.button(QDialogButtonBox.Ok);self.ok.setText('Continue reviewed action');self.ok.setEnabled(False);self.ack.toggled.connect(self.ok.setEnabled);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);box.addWidget(buttons)
class CellDialog(QDialog):
    def __init__(self,parent,value):
        super().__init__(parent);self.value=None;self.setWindowTitle('Edit working cell');self.resize(640,520);box=QVBoxLayout(self);box.addWidget(plain('Edit the working cell. Formula definitions and stored values remain separate; Save commits the table.'))
        self.type=QComboBox();self.type.addItems(t.TYPES);self.type.setCurrentText(value['type']);self.type.setAccessibleName('Cell value type');box.addWidget(self.type)
        box.addWidget(plain('Literal or stored value'));self.text=QPlainTextEdit();self.text.setPlainText('' if value['value'] is None else str(value['value']).lower() if type(value['value']) is bool else str(value['value']));self.text.setAccessibleName('Cell literal or cached value');box.addWidget(self.text,1)
        box.addWidget(plain('Formula definition (optional; never runs here)'));self.formula=QLineEdit(value['formula'] or '');self.formula.setAccessibleName('Saved formula definition');box.addWidget(self.formula)
        self.dialect=QComboBox();self.dialect.addItems(['xlsx-a1','odf-openformula','unsupported']);self.dialect.setCurrentText(value['formula_dialect'] if value['formula_dialect']!='none' else 'xlsx-a1');box.addWidget(self.dialect)
        box.addWidget(plain('Unit annotation'));self.unit=QLineEdit(value['unit']);self.unit.setAccessibleName('Cell unit annotation');box.addWidget(self.unit);self.status=plain();box.addWidget(self.status);self.original=value
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.apply);buttons.rejected.connect(self.reject);box.addWidget(buttons)
    def apply(self):
        try:
            typ=self.type.currentText();v=self.text.toPlainText()
            if typ=='boolean':
                if v.casefold() not in ('true','false'):raise ValueError('Enter true or false for a boolean.')
                v=v.casefold()=='true'
            elif typ=='blank':v=None
            value=t.cell(typ,v,self.formula.text() or None,self.dialect.currentText(),self.original['number_format'],self.unit.text());t.document('Cell',[t.sheet('Cell',{'A1':value})]);self.value=value;self.accept()
        except ValueError as e:self.status.setText(str(e))

class CSVColumns(QDialog):
    def __init__(self,parent,doc):
        super().__init__(parent);self.setWindowTitle('CSV column types');self.resize(700,520);box=QVBoxLayout(self);box.addWidget(plain('Choose types explicitly. Keep identifiers as text to preserve leading zeroes. Unit annotations remain Graphite metadata; a Unit column travels with external files.'))
        self.header=QCheckBox('The first row contains column headings.');self.header.setChecked(True);box.addWidget(self.header);cells=doc['sheets'][0]['cells'];columns=max((t.xy(a)[1] for a in cells),default=1);self.grid=QTableWidget(columns,3);self.grid.setHorizontalHeaderLabels(['Column','Read as','Unit annotation']);self.grid.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch);box.addWidget(self.grid,1)
        for c in range(1,columns+1):
            key=t.address(1,c)[:-1];name=str(cells.get(key+'1',{}).get('value',''));item=QTableWidgetItem(key+' · '+name);item.setFlags(item.flags()&~Qt.ItemIsEditable);self.grid.setItem(c-1,0,item);typ=QComboBox();typ.addItems(['text','number','boolean','date']);self.grid.setCellWidget(c-1,1,typ);self.grid.setCellWidget(c-1,2,QLineEdit())
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);box.addWidget(buttons)
    def options(self):
        columns={};units={}
        for r in range(self.grid.rowCount()):
            key=t.address(1,r+1)[:-1];columns[key]=self.grid.cellWidget(r,1).currentText();unit=self.grid.cellWidget(r,2).text()
            if unit:units[key]=unit
        return {'columns':columns,'units':units,'header_rows':int(self.header.isChecked())}

class OfficePanel(QWidget):
    def __init__(self,host,key):
        super().__init__(host);self.host=host;self.ident=key;self.writer=uuid.uuid4().hex;self.recovered_writer=None;self.dirty=False;self.loading=True;self.last_result=None;self.job=None;self.selected_block=None
        QFontDatabase.addApplicationFont(str(locations.program(host.root)/'branding/fonts/NotoSansCJKsc-Regular.otf'))
        self.setProperty('concern_id',key);self.setProperty('ledgerTitle','Office working copy');outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0);self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);outer.addWidget(self.scroll);content=QWidget();self.scroll.setWidget(content);box=QVBoxLayout(content)
        from .theme2 import tool,more
        KEPT='Working copy · originals remain separate. Save commits; conversion and recalculation require review.'
        self.title_edit=QLineEdit();self.title_edit.setAccessibleName('Office working title');self.title_edit.setToolTip(KEPT);box.addWidget(self.title_edit)
        # The page's actions. What is used every time is a row of tools above the work; what is used now and then is one click
        # further, under More. Every button the page ever had is still made and still does what it did (the page enables,
        # disables and presses them by name): the ones not in the row are kept out of sight and More presses them.
        self.kept=QWidget(self);self.kept.hide();row=QGridLayout(self.kept)
        self.save_button=QPushButton('Save working');self.save_button.setToolTip('Save this working copy');self.save_button.clicked.connect(self.save_concern_note);row.addWidget(self.save_button,0,0);self.recovery=QPushButton('Review recovery');self.recovery.clicked.connect(self.recover);row.addWidget(self.recovery,0,1)
        self.format=QComboBox();self.format.setAccessibleName('Office export format');self.format.setToolTip('The format Preview export writes');self.export_button=QPushButton('Preview export');self.export_button.clicked.connect(lambda:self.operation('export'))
        self.calc=QPushButton('Recalculate');self.calc.clicked.connect(lambda:self.operation('recalculate'));self.edit_copy=QPushButton('Prepare edit copy');self.edit_copy.clicked.connect(lambda:self.operation('edit'));row.addWidget(self.edit_copy,2,1)
        self.review_file=QPushButton('Review file');self.review_file.setToolTip('Review the saved external candidate and its changes');self.review_file.clicked.connect(self.candidate);row.addWidget(self.review_file,3,0);self.copy=QPushButton('Save output copy');self.copy.clicked.connect(self.copy_output);row.addWidget(self.copy,3,1)
        self.open_editor=QPushButton('Open editor');self.open_editor.clicked.connect(self.launch_editor);row.addWidget(self.open_editor,4,0);self.bom=QPushButton('Compare BOM');self.bom.clicked.connect(self.compare_bom);row.addWidget(self.bom,4,1)
        from .datasheet_qt import calculate_report
        self.datasheet_report=QPushButton('Calculate and write report…')
        self.datasheet_report.clicked.connect(lambda:calculate_report(self))
        self.datasheet_report.setToolTip('Work a number out from this sheet and write it up as a page, with what it stands on')
        self.calc.setToolTip('Have the office program work the formulas out again; the result is reviewed before it is kept')
        self.export_button.setToolTip('Write this working copy in the chosen format, to look at before it is kept')
        SAYS={'Save working':('Save this working copy (Save in the bar above does the same)','Nothing to save: no changes since the last save'),
              'Review recovery':('Look at a draft kept from an earlier session','There is no kept draft to look at'),
              'Prepare edit copy':('Prepare a copy to edit in the full office program','Save first: the copy is made from what is saved'),
              'Review file':('Review the saved external candidate and its changes','Save first, then review'),
              'Open editor':('Open the prepared copy in the office program','Prepare an edit copy first'),
              'Save output copy':('Write the last result to a file you choose','There is no result yet: Recalculate, Preview export or Prepare edit copy first'),
              'Compare BOM':('Compare this bill of materials with the board it came from','This sheet did not come from a bill of materials, or it has unsaved changes')}
        def now_and_then():
            return [('This is a working copy: the original is kept',lambda:None,False,KEPT),None]+\
                   [(b.text(),b.click,b.isEnabled(),SAYS[b.text()][0 if b.isEnabled() else 1]) for b in (self.save_button,self.recovery)]+[None]+\
                   [(b.text(),b.click,b.isEnabled(),SAYS[b.text()][0 if b.isEnabled() else 1]) for b in (self.edit_copy,self.open_editor,self.review_file,self.copy)]+[None]+\
                   [(self.bom.text(),self.bom.click,self.bom.isEnabled(),SAYS['Compare BOM'][0 if self.bom.isEnabled() else 1])]
        self.more=more('More',now_and_then,'What is needed now and then: recovery, the full office program, output copies')
        tools=QHBoxLayout();tools.setContentsMargins(0,2,0,2);tools.setSpacing(8)
        for one in (self.datasheet_report,self.calc,self.export_button):tool(one)
        tools.addWidget(self.datasheet_report);tools.addWidget(self.calc);tools.addSpacing(6);tools.addWidget(self.format);tools.addWidget(self.export_button);tools.addSpacing(6);tools.addWidget(self.more);tools.addStretch(1)
        self.format.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Fixed);box.addLayout(tools)
        self.pages=QTabWidget();self.pages.setMinimumHeight(360);box.addWidget(self.pages,1);self.working=QWidget();self.work_box=QVBoxLayout(self.working);self.pages.addTab(self.working,'Working content')
        self.readings=QPlainTextEdit();self.readings.setReadOnly(True);self.readings.setProperty('arcReadingRole','prose');self.readings.setAccessibleName('Measured results and BOM comparison');self.pages.addTab(self.readings,'Readings')
        self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setAccessibleName('Office source and exact record details');self.pages.addTab(self.details,'Details');self.status=plain();self.status.setAccessibleName('Office save and job status');box.addWidget(self.status)
        self.draft_timer=QTimer(self);self.draft_timer.setSingleShot(True);self.draft_timer.setInterval(650);self.draft_timer.timeout.connect(self.flush_draft)
        self.job_timer=QTimer(self);self.job_timer.setInterval(350);self.job_timer.timeout.connect(self.poll_job);self.editor=QProcess(self);self.editor.setObjectName('OfficeCandidateEditor');self.editor.finished.connect(lambda *a:self.status.setText('Editor closed. Review the changed candidate file before Save.'));self.editor.errorOccurred.connect(lambda *a:self.status.setText('The external editor could not start. The prepared copy is retained.'))
        self.title_edit.textChanged.connect(self.title_changed);saved=invoke(host,'get',{'id':key});self.table=saved['document']['schema']==t.SCHEMA
        if self.table:self.setup_table();self.format.addItems(['ods','xlsx','csv'])
        else:self.setup_document();self.format.addItems(['docx','pdf'])
        self.load(saved);self.loading=False
        for button in self.findChildren(QPushButton):button.setMinimumHeight(button.sizeHint().height())
    def title(self):return self.doc['title']+(' •' if self.dirty else '')
    def is_dirty(self):return self.dirty
    def set_dirty(self,value=True):
        self.dirty=value;self.save_button.setEnabled(value)
        if value:self.draft_timer.start()
        else:self.draft_timer.stop()
        index=self.host.tabs.indexOf(self)
        if index>=0:self.host.tabs.setTabText(index,self.title())
        for b in (self.export_button,self.calc,self.edit_copy,self.review_file,self.bom):b.setEnabled(not value)
        self.datasheet_report.setEnabled(not value)
        self.calc.setEnabled(self.table and not value);self.bom.setEnabled(self.table and not value and bool(self.base['origin'].get('components')));self.copy.setEnabled(bool(self.last_result));self.open_editor.setEnabled(bool(self.last_result and self.last_result['mode']=='edit'));self.host.concern.track_current()
    def load(self,saved):
        from .datasheet_work import SHEET
        self.datasheet_report.setVisible(saved['origin'].get('profile')==SHEET)
        self.loading=True;self.base=saved;self.doc=copy.deepcopy(saved['document']);self.title_edit.setText(self.doc['title']);self.details.setPlainText(json.dumps({'source':saved['origin'],'source_state':saved.get('source_state'),'working_revision':saved['revision'],'formula_values':'Stored values are not recalculation evidence.'},indent=2,ensure_ascii=False));self.refresh();self.loading=False;self.set_dirty(False);self.status.setText('Saved working copy. Original and accepted records are unchanged.')
    def title_changed(self,value):
        if not self.loading:self.doc['title']=value;self.set_dirty()
    def flush_draft(self):
        if not self.dirty:return True
        try:invoke(self.host,'draft.save',{'id':self.ident,'writer':self.writer,'base_revision':self.base['revision'],'document':self.doc});self.status.setText('Unsaved office draft is recoverable. Save commits.');return True
        except (ValueError,OSError) as e:self.status.setText('Draft could not be stored: '+str(e));return False
    def save_concern_note(self):
        self.draft_timer.stop()
        try:saved=invoke(self.host,'save',{'id':self.ident,'expected_revision':self.base['revision'],'document':self.doc})
        except (ValueError,OSError) as e:self.flush_draft();self.status.setText(str(e));return False
        cleanup=False
        for writer in {self.writer,self.recovered_writer}-{None}:
            try:invoke(self.host,'draft.discard',{'id':self.ident,'writer':writer})
            except (ValueError,OSError):cleanup=True
        self.recovered_writer=None;self.load(saved);self.host.concern.rebuild();self.host.concern.changed.emit();self.status.setText('Working copy saved.'+(' A recovery draft could not be cleared; review it before recovering.' if cleanup else ' Original and engineering acceptance are unchanged.'));return True
    def recover(self):
        try:
            rows=invoke(self.host,'drafts',{'id':self.ident})['drafts'];saved=invoke(self.host,'get',{'id':self.ident})
            if not rows:self.status.setText('No stored recovery draft.');return
            row=rows[0];dialog=Review(self,{'draft':row,'current_saved':saved['document']},'Review office recovery');dialog.ack.setText('Recover this as an unsaved draft for review.')
            if row['base_revision']!=saved['revision']:dialog.ack.setEnabled(False);dialog.ack.setText('Saved base changed. Compare and merge explicitly; this draft is retained.')
            if dialog.exec()==QDialog.Accepted:
                self.load(saved);self.doc=copy.deepcopy(row['document']);self.recovered_writer=row['writer'];self.loading=True;self.title_edit.setText(self.doc['title']);self.refresh();self.loading=False;self.set_dirty();self.status.setText('Recovered draft. Save is still required.')
        except (ValueError,OSError) as e:self.status.setText(str(e))
    def operation(self,mode):
        if self.dirty:self.status.setText('Save the working copy before reviewing an operation.');return
        try:
            fmt=('ods' if self.table else 'docx') if mode=='edit' else 'ods' if mode=='recalculate' else self.format.currentText();args={'id':self.ident,'expected_revision':self.base['revision'],'mode':mode,'format':fmt}
            if self.table and fmt=='csv':args['sheet']=self.sheets.currentData()
            plan=invoke(self.host,'operation.preview',args);dialog=Review(self,{'operation':mode,'format':fmt,'source_state':plan['source_state'],'runtime':plan['environment'],'losses':plan['losses'],'notice':'Recalculation returns a separate measured result. An editor copy is reviewed again before it can replace working content.'},'Review office operation')
            if dialog.exec()!=QDialog.Accepted:return
            job=invoke(self.host,'operation.run',{'plan':plan['id'],'expected_digest':plan['digest']});self.job=job['id'];self.status.setText('Office job '+job['state'].lower()+'. Original and saved working copy remain separate.');self.job_timer.start()
        except (ValueError,OSError) as e:self.status.setText(str(e))
    def poll_job(self):
        if not self.job:self.job_timer.stop();return
        try:
            result=invoke(self.host,'operation.result',{'job':self.job})
            if result['state'] in ('Queued','Running','Waiting for Approval'):return
            self.job_timer.stop()
            if result['state'] in ('Failed','Cancelled','Interrupted'):self.status.setText('Office '+result['state'].lower()+': '+str(result.get('error') or 'Inspect Jobs and evidence.'));return
            self.last_result=result;self.details.setPlainText(json.dumps(result,indent=2,ensure_ascii=False));lines=['Completed '+result['mode']+'.','Working copy and originals were not changed.','']
            for m in result['measurement']:lines.append(m['sheet']+'!'+m['cell']+' · '+m['formula']+'\nStored: '+str(m['stored_value'])+'\nMeasured: '+str(m['measured_value'])+' · '+m['state'])
            if result['mode']=='edit':lines.append('Prepared copy is ready. Open it in Office, save and close that editor, then Review changed file. The editor has no arbitrary editing deadline.')
            else:lines.extend('Output: '+r['name'] for r in result['files'])
            if result['losses']:lines.extend(['','Losses:']+[r['reason'].replace('_',' ').capitalize() for r in result['losses']])
            if result.get('roundtrip_changes'):lines.extend(['','Engine changes:']+[r['sheet']+'!'+r['cell']+' · '+r['change'].replace('_',' ').capitalize()+' · '+str(r.get('before',''))+' to '+str(r.get('after','')) for r in result['roundtrip_changes']])
            self.readings.setPlainText('\n'.join(lines));self.pages.setCurrentWidget(self.readings);self.copy.setEnabled(True);self.open_editor.setEnabled(result['mode']=='edit');self.status.setText('Office result available. Save new output copy exports a new file.')
        except (ValueError,OSError) as e:self.job_timer.stop();self.status.setText(str(e))
    def candidate(self):
        if self.editor.state()!=QProcess.NotRunning:self.status.setText('Save and close the external editor before reviewing its candidate.');return
        path,_=QFileDialog.getOpenFileName(self,'Choose saved candidate file','','Tables and documents (*.csv *.xlsx *.ods *.docx)')
        if not path:return
        try:
            plan=invoke(self.host,'candidate.preview',{'id':self.ident,'expected_revision':self.base['revision'],'path':path});dialog=Review(self,plan,'Review candidate differences')
            if dialog.exec()!=QDialog.Accepted:return
            invoke(self.host,'candidate.commit',{'plan':plan['id'],'expected_digest':plan['digest']});self.load(invoke(self.host,'get',{'id':self.ident}));self.host.concern.changed.emit();self.status.setText('Reviewed candidate saved. Untouched original remains retained.')
        except (ValueError,OSError) as e:self.status.setText(str(e))
    def copy_output(self):
        if not self.last_result:return
        from . import files_service
        from .engine import engineering
        row=self.last_result['files'][0];start=files_service.root(engineering(self.host.root))/files_service.EXPORTS/row['name']  # Egress: the folder files leave from (D28)
        path,_=QFileDialog.getSaveFileName(self,'Save a new output copy',str(start),options=QFileDialog.DontConfirmOverwrite)
        if not path:return
        try:v=invoke(self.host,'output.copy',{'job':self.last_result['job'],'file':row['name'],'expected_sha256':row['sha256'],'destination':path});self.status.setText('Saved new output copy: '+v['path'])
        except (ValueError,OSError) as e:self.status.setText(str(e))
    def launch_editor(self):
        if not self.last_result or self.last_result['mode']!='edit':return
        if self.editor.state()!=QProcess.NotRunning:self.status.setText('This candidate editor is already open.');return
        try:
            current=invoke(self.host,'operation.result',{'job':self.last_result['job']})
            if current['state']!='AVAILABLE' or office_runtime.probe()!=current['reviewed_environment']['renderer']:raise ValueError('Source or editor changed. Prepare and review a new copy.')
            path=Path(current['directory'])/current['files'][0]['name'];args,env=office_runtime.editor_command(path,Path(current['directory'])/'desktop-editor');process_env=QProcessEnvironment.systemEnvironment()
            for k,v in env.items():process_env.insert(k,v)
            self.editor.setProcessEnvironment(process_env);self.editor.setProgram(args[0]);self.editor.setArguments(args[1:]);self.editor.start();self.status.setText('Opening isolated candidate editor. Save and close it before candidate review.')
        except (ValueError,OSError) as e:self.status.setText(str(e))
    def compare_bom(self):
        try:
            value=invoke(self.host,'bom.compare',{'id':self.ident,'expected_revision':self.base['revision']});self.details.setPlainText(json.dumps(value,indent=2,ensure_ascii=False));lines=[value.get('link_state','BOM comparison')]
            for row in value['changes']:lines.append(row['change']+' '+(row['after'] or row['before'])['reference']+' · '+', '.join(row['fields'])+'\nNative component '+row['native_id'])
            if not value['changes']:lines.append('No current linked changes to display.')
            lines.append('Working BOM comparison changes no native CAD source or engineering acceptance.');self.readings.setPlainText('\n\n'.join(lines));self.pages.setCurrentWidget(self.readings)
        except (ValueError,OSError) as e:self.status.setText(str(e))
    def setup_table(self):
        row=QHBoxLayout();self.sheets=QComboBox();self.sheets.setAccessibleName('Working sheet');self.sheets.currentIndexChanged.connect(self.refresh_table);row.addWidget(self.sheets,1);self.address=QLineEdit('A1');self.address.setMaximumWidth(110);self.address.setAccessibleName('Working cell address');row.addWidget(self.address);self.edit_cell_button=QPushButton('Edit cell');__import__('workbench.theme2',fromlist=['tool']).tool(self.edit_cell_button,'Change the selected cell (a double-click on the cell does the same)');self.edit_cell_button.clicked.connect(self.edit_cell);row.addWidget(self.edit_cell_button);self.work_box.addLayout(row)
        self.grid=QTableWidget();self.grid.setEditTriggers(QTableWidget.NoEditTriggers);self.grid.verticalHeader().setDefaultSectionSize(max(34,self.fontMetrics().height()+14));self.grid.setAccessibleName('Typed working table');self.grid.itemSelectionChanged.connect(self.cell_selected);self.grid.cellDoubleClicked.connect(lambda *a:self.edit_cell());self.work_box.addWidget(self.grid,1);self.cell_info=plain();self.work_box.addWidget(self.cell_info)
        self.source_bench = QWidget(self.working)
        evidence = QHBoxLayout(self.source_bench)
        evidence.setContentsMargins(0, 0, 0, 0)
        self.source_row_info = plain()
        self.source_row_info.setAccessibleName('Reviewed PDF row')
        evidence.addWidget(self.source_row_info, 1)
        self.source_row_button = QPushButton('Open source row')
        __import__('workbench.theme2', fromlist=['tool']).tool(self.source_row_button)
        self.source_row_button.setToolTip('Pin this sheet to keep it open while viewing the original PDF.')
        self.source_row_button.clicked.connect(self.open_source_row)
        evidence.addWidget(self.source_row_button)
        self.source_bench.hide()
        self.work_box.addWidget(self.source_bench)
    def current_sheet(self):return next((s for s in self.doc['sheets'] if s['id']==self.sheets.currentData()),None)
    def refresh_table(self,*a):
        if not hasattr(self,'doc'):return
        sheet=self.current_sheet()
        if not sheet:return
        self.grid.clear();rows=max((t.xy(a)[0] for a in sheet['cells']),default=1);cols=max((t.xy(a)[1] for a in sheet['cells']),default=1);self.grid.setRowCount(rows);self.grid.setColumnCount(cols);self.grid.setHorizontalHeaderLabels([t.address(1,c)[:-1] for c in range(1,cols+1)])
        for loc,v in sheet['cells'].items():
            r,c=t.xy(loc);text=v['formula'] if v['formula'] is not None else '(blank)' if v['value'] is None else str(v['value']).lower() if type(v['value']) is bool else str(v['value']);item=QTableWidgetItem(text);item.setToolTip(v['type']+' · '+v['cache_state']+(' · '+v['unit'] if v['unit'] else ''));self.grid.setItem(r-1,c-1,item)
            if v['type']=='excel-date-serial':
                try:item.setText(t.excel_date(v));item.setToolTip('Original Excel serial: '+v['value']+' · '+v['number_format'])
                except (ValueError,OverflowError):pass
        for col in range(cols):self.grid.setColumnWidth(col,190 if col else 150)
        self.grid.setCurrentCell(0,0)
    def cell_selected(self):
        r,c=self.grid.currentRow(),self.grid.currentColumn()
        self.show_source_row()
        if r<0 or c<0:return
        loc=t.address(r+1,c+1);self.address.setText(loc);value=self.current_sheet()['cells'].get(loc,t.cell('blank',None));self.cell_info.setText(loc+' · '+value['type']+' · '+('stored cache; not recalculated' if value['formula'] else 'literal')+(' · unit '+value['unit'] if value['unit'] else ''))

    def reviewed_source_row(self):
        from .datasheet_work import SHEET
        origin = self.base['origin']
        sheet = self.current_sheet()
        if origin.get('profile') != SHEET or sheet is None or sheet['id'] != self.base['document']['sheets'][0]['id']:
            return None
        number = self.grid.currentRow() + 1
        parameter = sheet['cells'].get(f'A{number}', {}).get('value')
        return next((row for row in origin['reviewed_rows']
                     if row['sheet_row'] == number and row['parameter'] == parameter), None)

    def show_source_row(self):
        from .datasheet_work import SHEET
        origin = self.base['origin']
        reviewed = origin.get('profile') == SHEET
        self.source_bench.setVisible(reviewed)
        if not reviewed:
            return
        row = self.reviewed_source_row()
        self.source_row_button.setEnabled(row is not None)
        if row is None:
            self.source_row_info.setText('Source Bench · Select a row with a reviewed PDF binding.')
            return
        page = origin['pdf']['page_index'] + 1
        excerpt = '  ·  '.join(row['original_cells'])
        self.source_row_info.setText(f"Source Bench · PDF page {page} · reviewed text\n{excerpt}")

    def open_source_row(self):
        row = self.reviewed_source_row()
        if row is None:
            return
        from .pdf_qt import open_pdf
        source = self.base['origin']['pdf']
        rects = [word['rect'] for word in row.get('source_words', [])]
        region = source['rect']
        if rects:
            left = min(x for x, _, _, _ in rects)
            top = min(y for _, y, _, _ in rects)
            right = max(x + w for x, _, w, _ in rects)
            bottom = max(y + h for _, y, _, h in rects)
            region = [left, top, right - left, bottom - top]
        open_pdf(self.host, source['namespace'], source['item'], source['source_sha256'],
                 source['page_index'], region)
    def edit_cell(self):
        try:
            loc=self.address.text().strip().upper();t.xy(loc);sheet=self.current_sheet();dialog=CellDialog(self,sheet['cells'].get(loc,t.cell('blank',None)))
            if dialog.exec()==QDialog.Accepted:sheet['cells'][loc]=dialog.value;self.refresh_table();r,c=t.xy(loc);self.grid.setCurrentCell(r-1,c-1);self.set_dirty()
        except ValueError as e:self.status.setText(str(e))
    def setup_document(self):
        self.blocks=QComboBox();self.blocks.setAccessibleName('Editable document block');self.blocks.currentIndexChanged.connect(self.select_block);self.work_box.addWidget(self.blocks)
        self.prose=QPlainTextEdit();self.prose.setProperty('arcReadingRole','prose');self.prose.setAccessibleName('Editable document paragraph');self.prose.textChanged.connect(self.prose_changed);self.work_box.addWidget(self.prose,1)
        self.doc_table=QTableWidget();self.doc_table.setEditTriggers(QTableWidget.NoEditTriggers);self.doc_table.cellDoubleClicked.connect(self.edit_doc_cell);self.doc_table.setAccessibleName('Editable document table');self.work_box.addWidget(self.doc_table,1)
        add=QPushButton('Add paragraph');add.clicked.connect(self.add_paragraph);self.work_box.addWidget(add)
    def select_block(self,*a):
        if not hasattr(self,'doc'):return
        b=next((b for b in self.doc['blocks'] if b['id']==self.blocks.currentData()),None);self.selected_block=b;self.loading=True
        self.prose.setVisible(bool(b and b['kind']=='paragraph'));self.doc_table.setVisible(bool(b and b['kind']=='table'))
        if b and b['kind']=='paragraph':self.prose.setPlainText(b['text'])
        elif b:
            self.doc_table.setRowCount(len(b['rows']));self.doc_table.setColumnCount(len(b['rows'][0]))
            for r,row in enumerate(b['rows']):
                for c,value in enumerate(row):self.doc_table.setItem(r,c,QTableWidgetItem(value))
            self.doc_table.resizeColumnsToContents()
        self.loading=False
    def prose_changed(self):
        if not self.loading and self.selected_block and self.selected_block['kind']=='paragraph':self.selected_block['text']=self.prose.toPlainText();self.set_dirty()
    def edit_doc_cell(self,r,c):
        if not self.selected_block:return
        value,ok=QInputDialog.getMultiLineText(self,'Edit working table cell','Text',self.selected_block['rows'][r][c])
        if ok:self.selected_block['rows'][r][c]=value;self.select_block();self.set_dirty()
    def add_paragraph(self):self.doc['blocks'].append(d.paragraph());self.refresh();self.blocks.setCurrentIndex(self.blocks.count()-1);self.set_dirty()
    def refresh(self):
        if self.table:
            selected=self.sheets.currentData();self.sheets.blockSignals(True);self.sheets.clear()
            for sheet in self.doc['sheets']:self.sheets.addItem(sheet['name'],sheet['id'])
            self.sheets.setCurrentIndex(max(0,self.sheets.findData(selected)));self.sheets.blockSignals(False);self.refresh_table()
        else:
            selected=self.blocks.currentData();self.blocks.blockSignals(True);self.blocks.clear()
            for i,b in enumerate(self.doc['blocks']):self.blocks.addItem(str(i+1)+' · '+b['kind']+(' · '+b['text'][:50] if b['kind']=='paragraph' else ''),b['id'])
            self.blocks.setCurrentIndex(max(0,self.blocks.findData(selected)));self.blocks.blockSignals(False);self.select_block()
    def can_close_concern(self):
        if self.editor.state()!=QProcess.NotRunning:self.status.setText('Save and close the candidate editor before closing this workspace.');return False
        if not self.dirty:return True
        self.flush_draft();box=QMessageBox(self);box.setWindowTitle('Keep working copy changes');box.setText('Save this working copy before closing? Other writers’ recovery drafts remain.');box.setStandardButtons(QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel);choice=box.exec()
        if choice==QMessageBox.Save:return self.save_concern_note()
        if choice==QMessageBox.Discard:
            try:invoke(self.host,'draft.discard',{'id':self.ident,'writer':self.writer});self.set_dirty(False);return True
            except ValueError as e:self.status.setText(str(e))
        return False
    def shutdown_engineering(self):self.job_timer.stop();self.draft_timer.stop()

class OfficeHub(QDialog):
    def __init__(self,host,parent='library'):
        super().__init__(host);self.host=host;self.parent_id=parent;self.setWindowTitle('Office tables and documents');self.resize(760,620);box=QVBoxLayout(self);box.addWidget(plain('Explicit working copies with untouched originals, reviewed differences and separate measured results.'))
        self.items=QTreeWidget();self.items.setHeaderLabels(['Working copy','Version']);self.items.setRootIsDecorated(False);self.items.header().setSectionResizeMode(0,QHeaderView.Stretch);box.addWidget(self.items,1);row=QGridLayout();self.import_button=QPushButton('Import working copy');self.import_button.clicked.connect(self.import_file);row.addWidget(self.import_button,0,0);self.open_button=QPushButton('Open selected');self.open_button.clicked.connect(self.open);row.addWidget(self.open_button,0,1)
        self.bom_button=QPushButton('BOM from KiCad PCB');self.bom_button.clicked.connect(lambda:self.import_file(True));row.addWidget(self.bom_button,1,0);self.notebook_button=QPushButton('Copy saved notebook');self.notebook_button.clicked.connect(self.from_notebook);row.addWidget(self.notebook_button,1,1)
        self.book_button=QPushButton('Copy current Orange Book');self.book_button.clicked.connect(self.from_book);row.addWidget(self.book_button,2,0);self.doctor=QPushButton('Inspect Office tools');self.doctor.clicked.connect(self.inspect_tools);row.addWidget(self.doctor,2,1);box.addLayout(row);[row.setAlignment(b,Qt.AlignLeft|Qt.AlignVCenter) for b in (self.import_button,self.open_button,self.bom_button,self.notebook_button,self.book_button,self.doctor)];self.status=plain();box.addWidget(self.status);self.reload()
    def reload(self):
        self.items.clear()
        try:
            for row in invoke(self.host,'list')['documents']:
                item=QTreeWidgetItem([row['title'],str(row['version'])]);item.setData(0,Qt.UserRole,row['id']);self.items.addTopLevelItem(item)
        except (ValueError,OSError) as e:self.status.setText(str(e))
    def open(self):
        item=self.items.currentItem()
        if item:open_office(self.host,item.data(0,Qt.UserRole));self.close()
    def import_file(self,bom=False):
        # clicked(bool) is an incidental Qt signal, not a request for a BOM.
        bom=bool(bom);path,_=QFileDialog.getOpenFileName(self,'Choose explicit '+('KiCad PCB' if bom else 'table or document'),'','KiCad PCB (*.kicad_pcb)' if bom else 'Tables and documents (*.csv *.xlsx *.ods *.docx)')
        if not path:return
        try:
            args={'path':path,'parent':self.parent_id};plan=invoke(self.host,'bom.preview' if bom else 'import.preview',args)
            if not bom and path.lower().endswith('.csv'):
                types=CSVColumns(self,plan['document'])
                if types.exec()!=QDialog.Accepted:return
                args['csv']=types.options();plan=invoke(self.host,'import.preview',args)
            dialog=Review(self,plan,'Review one-way working import')
            if dialog.exec()!=QDialog.Accepted:return
            result=invoke(self.host,'import.commit',{'plan':plan['id'],'expected_digest':plan['digest']});self.host.concern.rebuild();open_office(self.host,result['document_id']);self.close()
        except (ValueError,OSError) as e:self.status.setText(str(e))
    def from_notebook(self):
        from .notebook_qt import invoke as notebook_invoke
        try:
            rows=notebook_invoke(self.host,'list')['notebooks']
            if not rows:self.status.setText('Create and Save a notebook first.');return
            label,ok=QInputDialog.getItem(self,'Copy saved notebook','Notebook',[r['title']+' · '+r['id'][-8:] for r in rows],0,False)
            if not ok:return
            index=[r['title']+' · '+r['id'][-8:] for r in rows].index(label);saved=notebook_invoke(self.host,'get',{'id':rows[index]['id']});result=invoke(self.host,'from.notebook',{'notebook':saved['id'],'expected_revision':saved['revision']});self.host.concern.rebuild();open_office(self.host,result['id']);self.close()
        except (ValueError,OSError) as e:self.status.setText(str(e))
    def from_book(self):
        try:result=invoke(self.host,'from.book');self.host.concern.rebuild();open_office(self.host,result['id']);self.close()
        except (ValueError,OSError) as e:self.status.setText(str(e)+' · A current attached engineering book is required.')
    def inspect_tools(self):
        try:dialog=Review(self,invoke(self.host,'doctor'),'Installed Office tools');dialog.ack.hide();dialog.ok.setText('Close');dialog.ok.setEnabled(True);dialog.exec()
        except (ValueError,OSError) as e:self.status.setText(str(e))
def open_office(host,key):
    if host.concern.store is None or host.concern.store.path.resolve()!=office_service.path().resolve():host.statusBar().showMessage('Office and desktop profiles differ; reopen with one profile.',10000);return None
    for i in range(host.tabs.count()):
        tab=host.tabs.widget(i)
        if isinstance(tab,OfficePanel) and tab.ident==key:host.tabs.setCurrentWidget(tab);return tab
    host._close_start();tab=OfficePanel(host,key);host.tabs.addTab(tab,host.nav_icon('folder'),tab.title());host.tabs.setCurrentWidget(tab);return tab
def hub(host,parent='library'):
    dialog=OfficeHub(host,parent);host._office_hub=dialog;dialog.show();return dialog
