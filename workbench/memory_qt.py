"""Ledger-native personality teaching, verified checkpoints and staC workbench."""
from .text_prompts import writing_prompt
import html,json,uuid
from pathlib import Path
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (QWidget,QLabel,QPushButton,QComboBox,QLineEdit,QPlainTextEdit,QTextBrowser,QTreeWidget,QTreeWidgetItem,
 QVBoxLayout,QHBoxLayout,QGridLayout,QFormLayout,QTabWidget,QSplitter,QFileDialog,QInputDialog,QDoubleSpinBox,QCheckBox,QScrollArea)
from .register_tabs import ServiceTab
from . import local_brain
from sdk.cli.arc1cli.learning_contracts import CONTEXTS,WEIGHTS
from . import locations

class MemoryTab(ServiceTab):
    def __init__(self,host):
        super().__init__(host);self.job=None;self.last_checkpoint=None;self.current_reference=None;self.pending_binding=None;self.profile_enabled=False;self.task_epoch=0
        h=QLabel('GRAPHITE · MEMORY');h.setStyleSheet('font-size:18px;color:#edaa69;font-weight:bold');self.outer.addWidget(h)
        self.note=QLabel('Teach through explicit feedback. Save and verify a checkpoint before starting a fresh working context.');self.note.setWordWrap(True);self.outer.addWidget(self.note)
        row=QHBoxLayout();self.context_label=QLabel('Interaction context');row.addWidget(self.context_label);self.context_choice=QComboBox();self.context_choice.addItems(CONTEXTS);self.context_choice.setCurrentText('engineering_execution');self.context_choice.currentTextChanged.connect(self.refresh_profile);row.addWidget(self.context_choice,1);self.outer.addLayout(row)
        self.pages=QTabWidget();self.learning_page=QWidget();learn=QVBoxLayout(self.learning_page);learn.setContentsMargins(0,0,0,0)
        self.profile_label=QLabel('No personality seed imported.');self.profile_label.setWordWrap(True);learn.addWidget(self.profile_label)
        self.enabled=QCheckBox('Use this private personality reference in local replies');self.enabled.toggled.connect(self.toggle_profile);learn.addWidget(self.enabled)
        buttons=QGridLayout()
        for i,(label,fn) in enumerate([('Import personality JSON',self.import_seed),('Refresh learning',self.refresh_profile),('Export private memory',self.export_memory),('Restore private memory',self.restore_memory),('Erase profile and feedback',self.delete_profile)]):self.add_button(buttons,label,fn,i)
        learn.addLayout(buttons);form=QFormLayout();self.preference=QLineEdit('technical_depth');form.addRow('Preference ID',self.preference);self.direction=QLineEdit();writing_prompt(self.direction, 'Describe the response you want from Graphite');form.addRow('Owner direction',self.direction)
        self.feedback_value=QDoubleSpinBox();self.feedback_value.setRange(0,1);self.feedback_value.setSingleStep(.25);self.feedback_value.setValue(1);self.feedback_value.setDecimals(2);form.addRow('Agreement (0–1)',self.feedback_value)
        self.feedback_kind=QComboBox();self.feedback_kind.addItems(WEIGHTS);form.addRow('Feedback kind',self.feedback_kind);self.soft=QCheckBox('Soft evidence may decay; direct corrections persist');form.addRow(self.soft);learn.addLayout(form)
        commit=QPushButton('Teach this preference');commit.clicked.connect(self.teach);learn.addWidget(commit)
        self.feedback_tree=QTreeWidget();self.feedback_tree.setHeaderLabels(['Preference / context','Posterior / status','Owner direction']);self.feedback_tree.setColumnWidth(0,190);self.feedback_tree.setColumnWidth(1,150);learn.addWidget(self.feedback_tree,1)
        row=QHBoxLayout()
        for label,fn in [('Undo selected feedback',self.undo_feedback),('Forget selected feedback',self.forget_feedback)]:b=QPushButton(label);b.clicked.connect(fn);row.addWidget(b)
        learn.addLayout(row);self.pages.addTab(self.learning_page,'Personality / learning')
        self.task_page=QWidget();tasks=QVBoxLayout(self.task_page);tasks.setContentsMargins(0,0,0,0);row=QHBoxLayout();self.task_choice=QComboBox();self.task_choice.currentIndexChanged.connect(self.load_task);row.addWidget(self.task_choice,1);new=QPushButton('New task');new.clicked.connect(self.new_task);row.addWidget(new);refresh=QPushButton('Reload tasks');refresh.clicked.connect(self.load_tasks);row.addWidget(refresh);tasks.addLayout(row)
        self.task_state=QLabel('Create a task to begin.');self.task_state.setWordWrap(True);tasks.addWidget(self.task_state);self.task_pages=QTabWidget();tasks.addWidget(self.task_pages,1)
        save_page=QWidget();save_box=QVBoxLayout(save_page);save_box.setContentsMargins(0,0,0,0);form=QFormLayout();self.goal=QLineEdit();self.next_step=QLineEdit();self.summary_edit=self.small_text();self.constraints=self.small_text();self.findings=self.small_text();self.contradictions=self.small_text();self.reference_json=self.small_text('[]');self.jobs_edit=QLineEdit();self.conversation_id=QLineEdit(uuid.uuid4().hex)
        for label,widget in [('Goal',self.goal),('Summary',self.summary_edit),('Constraints (one per line)',self.constraints),('Findings (owner notes)',self.findings),('Contradictions / gaps',self.contradictions),('Next useful step',self.next_step),('Source bindings (JSON)',self.reference_json),('Job IDs (comma separated)',self.jobs_edit),('Working conversation',self.conversation_id)]:form.addRow(label,widget)
        save_box.addLayout(form);save=QPushButton('Save and verify checkpoint');save.clicked.connect(self.save_checkpoint);save_box.addWidget(save);save_scroll=QScrollArea();save_scroll.setWidgetResizable(True);save_scroll.setWidget(save_page);self.task_pages.addTab(save_scroll,'Checkpoint')
        resume_page=QWidget();resume=QVBoxLayout(resume_page);resume.setContentsMargins(0,0,0,0)
        for label,fn in [('Preview current checkpoint context',self.preview_context),('Start fresh context from checkpoint',self.clear_context),('Relink identical restored sources',self.rebind_sources)]:b=QPushButton(label);b.clicked.connect(fn);resume.addWidget(b)
        self.question=QLineEdit();writing_prompt(self.question, 'Ask about the saved task and its current sources');resume.addWidget(self.question);ask=QPushButton('Resume with local Graphite');ask.clicked.connect(self.ask);resume.addWidget(ask);cancel=QPushButton('Cancel local reply');cancel.clicked.connect(self.cancel);resume.addWidget(cancel)
        self.answer=QTextBrowser();self.answer.setOpenLinks(False);self.answer.anchorClicked.connect(self.follow_citation);resume.addWidget(self.answer,1);self.task_pages.addTab(resume_page,'Resume / compact')
        lesson_page=QWidget();lessons=QVBoxLayout(lesson_page);lessons.setContentsMargins(0,0,0,0);self.lesson_title=QLineEdit();writing_prompt(self.lesson_title, 'Procedure title');lessons.addWidget(self.lesson_title);self.lesson_body=QPlainTextEdit();writing_prompt(self.lesson_body, 'A proposed lesson is not trusted until you review it.');lessons.addWidget(self.lesson_body,1)
        row=QHBoxLayout()
        for label,fn in [('Propose procedure',self.propose_lesson),('Approve selected',lambda:self.review_lesson(True)),('Reject selected',lambda:self.review_lesson(False)),('Refresh procedures',self.refresh_lessons)]:b=QPushButton(label);b.clicked.connect(fn);row.addWidget(b)
        lessons.addLayout(row);self.lesson_tree=QTreeWidget();self.lesson_tree.setHeaderLabels(['Procedure','Review','Sources']);self.lesson_tree.itemSelectionChanged.connect(self.select_lesson);lessons.addWidget(self.lesson_tree,1);self.task_pages.addTab(lesson_page,'Reviewed procedures');self.pages.addTab(self.task_page,'Tasks / memory')
        self.stac_page=QWidget();stac=QVBoxLayout(self.stac_page);stac.setContentsMargins(0,0,0,0);self.program=QPlainTextEdit('use ARC1@R10 | part U45 | fact tCEM | claim | witness | verify');self.program.setMaximumHeight(95);stac.addWidget(self.program)
        grid=QGridLayout()
        for i,(label,fn) in enumerate([('Compile the line',lambda:self.stac('stac.compile')),('Run the read',lambda:self.stac('stac.run')),('Record read observation',lambda:self.stac('stac.observe')),('Export the result',self.export_stac),('Read observation history',lambda:self.call('stac.history',{},self.show_record)),('Use attached reference',self.stac_reference)]):self.add_button(grid,label,fn,i)
        stac.addLayout(grid);self.english=QLineEdit();writing_prompt(self.english, 'Controlled English: What remains to prove U45 tCEM on ARC1 R10?');stac.addWidget(self.english);translate=QPushButton('Translate controlled English');translate.clicked.connect(lambda:self.call('stac.translate',{'text':self.english.text()},self.translated));stac.addWidget(translate)
        info=QLabel('A line uses the existing Kernel and your permissions. Compile grants no authority. Missing native sources stay blocked. Internal file redirection needs the explicit owner export action here.');info.setWordWrap(True);stac.addWidget(info);stac.addStretch(1);self.pages.addTab(self.stac_page,'Lines')
        from .research_qt import ResearchTab
        self.research_page=ResearchTab(host,self);self.pages.addTab(self.research_page,'Research exchange')
        from .study_qt import StudyTab
        self.study_page=StudyTab(host,self);self.pages.addTab(self.study_page,'Study / editions')
        self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setAccessibleName('Memory and source evidence');split=QSplitter(Qt.Vertical);split.addWidget(self.pages);split.addWidget(self.details);split.setSizes([620,180]);self.outer.addWidget(split,1);self.outer.addWidget(self.status)
        font_path=locations.program(host.root)/'branding/fonts/NotoSansCJKsc-Regular.otf'
        if font_path.is_file():
            font_id=QFontDatabase.addApplicationFont(str(font_path));families=QFontDatabase.applicationFontFamilies(font_id)
            if families:
                for widget in self.findChildren(QWidget):
                    if isinstance(widget,(QLineEdit,QPlainTextEdit,QTextBrowser,QTreeWidget)):
                        font=widget.font();font.setFamilies([font.family(),families[0]]);widget.setFont(font)
        self.pages.currentChanged.connect(self.active_page_changed)
        self.timer=QTimer(self);self.timer.setInterval(700);self.timer.timeout.connect(self.poll);self.timer.start();QTimer.singleShot(0,self.refresh_profile);QTimer.singleShot(0,self.load_tasks);QTimer.singleShot(0,self.refresh_lessons)
    def active_page_changed(self,*args):
        research=self.pages.currentWidget() in (self.research_page,self.study_page)
        self.details.setVisible(not research);self.context_choice.setVisible(not research);self.context_label.setVisible(not research)
        self.note.setText('One question, selected originals, a reviewed return.' if research else 'Teach through explicit feedback. Save and verify a checkpoint before starting a fresh working context.')
    def title(self):return 'Graphite · Memory'
    def info(self):return 'Explicit teaching · verified checkpoints · Kernel-owned lines'
    def add_button(self,grid,label,fn,index):
        b=QPushButton(label);b.setAccessibleName(label);b.clicked.connect(fn);grid.addWidget(b,index//2,index%2)
    def small_text(self,value=''):
        e=QPlainTextEdit(value);e.setMaximumHeight(65);return e
    def context(self):return self.context_choice.currentText()
    def show_record(self,value):self.details.setPlainText(json.dumps(value,indent=2,ensure_ascii=False));self.update_inspector()
    def update_inspector(self):
        if hasattr(self.host,'arc_inspector') and self.host.tabs.currentWidget() is self:self.host.arc_inspector.refresh()
    def refresh_profile(self,*args):
        def loaded(value):
            self.profile_enabled=value.get('enabled',False);self.enabled.blockSignals(True);self.enabled.setChecked(self.profile_enabled);self.enabled.blockSignals(False)
            self.profile_label.setText(('Private seed · '+value.get('expression',{}).get('name','')+' · '+value.get('original_sha256','')[:16]+' · '+('enabled' if self.profile_enabled else 'disabled')) if 'original_sha256' in value else 'No personality seed imported. Your profile stays outside the program ZIP.');self.update_inspector()
        self.call('memory.profile',{},loaded);context=self.context()
        def preferences(value):
            if self.context()!=context:return
            self.feedback_tree.clear()
            for row in value['preferences']:
                item=QTreeWidgetItem([row['preference']+' / '+context,'mean %.3f'%row['mean'],row['instruction']]);item.setData(0,Qt.UserRole,row['events'][-1]);self.feedback_tree.addTopLevelItem(item)
            self.last_preferences=value
        self.call('memory.preferences',{'context':context},preferences)
    def import_seed(self):
        path,_=QFileDialog.getOpenFileName(self,'Import private personality seed','','JSON (*.json)')
        if path:self.call('memory.profile.import',{'path':path},lambda v:(self.show_record(v),self.refresh_profile(),self.note.setText('Starting personality reference imported. Interpretations remain editable; feedback is explicit.')))
    def toggle_profile(self,enabled):self.call('memory.profile.enable',{'enabled':enabled},lambda v:self.refresh_profile())
    def teach(self):
        args={'id':uuid.uuid4().hex,'preference':self.preference.text().strip(),'context':self.context(),'feedback':self.feedback_value.value(),'instruction':self.direction.text().strip(),'source_reference':'Owner Memory panel feedback','kind':self.feedback_kind.currentText(),'soft':self.soft.isChecked()}
        self.call('memory.feedback',args,lambda v:(self.show_record(v),self.refresh_profile(),self.note.setText('Owner feedback saved. It will enter relevant local response context.')))
    def selected_feedback(self):
        row=self.feedback_tree.currentItem();return row.data(0,Qt.UserRole) if row else None
    def undo_feedback(self):
        ident=self.selected_feedback()
        if ident:self.call('memory.feedback.undo',{'id':ident},lambda v:(self.show_record(v),self.refresh_profile()))
    def forget_feedback(self):
        ident=self.selected_feedback()
        if ident:self.call('memory.feedback.forget',{'id':ident},lambda v:(self.show_record(v),self.refresh_profile()))
    def delete_profile(self):self.call('memory.profile.delete',{'reason':'Owner selected Erase profile and feedback'},lambda v:(self.show_record(v),self.refresh_profile(),self.note.setText('Profile and feedback erased. Tasks and external archives remain separate.')))
    def new_task(self):
        title,ok=QInputDialog.getText(self,'New memory task','Task title')
        if ok and title.strip():self.call('memory.task.create',{'title':title.strip()},self.created_task)
    def created_task(self,value):self.pending_task=value['id'];self.task_pages.setEnabled(False);self.load_tasks()
    def load_tasks(self):
        def loaded(value):
            current=getattr(self,'pending_task',None) or self.task_choice.currentData();self.pending_task=None;self.task_choice.blockSignals(True);self.task_choice.clear()
            for task in value['tasks']:self.task_choice.addItem(task['title'],task['id'])
            self.task_choice.setCurrentIndex(max(0,self.task_choice.findData(current)));self.task_choice.blockSignals(False);self.load_task()
        self.call('memory.tasks',{},loaded)
    def load_task(self,*args):
        ident=self.task_choice.currentData();self.task_epoch+=1;epoch=self.task_epoch
        if not ident:return
        self.task_pages.setEnabled(False)
        def loaded(value):
            if epoch!=self.task_epoch:return
            self.task_data=value
            if value['latest']:self.call('memory.checkpoint',{'id':value['latest']},lambda cp:self.loaded_checkpoint(cp) if epoch==self.task_epoch else None)
            else:
                self.last_checkpoint=None;self.goal.setText(value['title']);self.summary_edit.clear();self.constraints.clear();self.findings.clear();self.contradictions.clear();self.next_step.clear();self.jobs_edit.clear();self.conversation_id.setText(uuid.uuid4().hex);self.task_state.setText('New task · no durable checkpoint yet');self.task_pages.setEnabled(True);self.update_inspector()
        self.call('memory.task',{'id':ident},loaded)
    def loaded_checkpoint(self,value):
        self.task_pages.setEnabled(True);self.last_checkpoint=value;note=value['note'];self.goal.setText(note['goal']);self.next_step.setText(note['next_step']);self.summary_edit.setPlainText(note['summary'])
        for key,widget in [('constraints',self.constraints),('findings',self.findings),('contradictions',self.contradictions)]:widget.setPlainText('\n'.join(note[key]))
        self.reference_json.setPlainText(json.dumps([{k:r[k] for k in ('namespace','id','item')} for r in value['references']],ensure_ascii=False));self.jobs_edit.setText(','.join(j['id'] for j in value['jobs']))
        if value.get('working_conversation') or value.get('conversation'):self.conversation_id.setText(value.get('working_conversation') or value['conversation'])
        if self.pending_binding:self.bind_reference(*self.pending_binding);self.pending_binding=None
        self.task_state.setText('Verified checkpoint '+value['id'][:12]+' · saved owner notes · '+str(value['transcript_messages'])+' prior messages');self.update_inspector()
    def bind_reference(self,namespace,citation):
        self.current_reference=(namespace,citation);self.pending_binding=(namespace,citation)
        try:rows=json.loads(self.reference_json.toPlainText())
        except ValueError:rows=[]
        binding={'namespace':namespace,'id':citation['id'],'item':citation['item']}
        if binding not in rows:rows.append(binding)
        self.reference_json.setPlainText(json.dumps(rows,ensure_ascii=False));self.pages.setCurrentWidget(self.task_page);self.task_pages.setCurrentIndex(0);self.note.setText('Reference address attached. Save a checkpoint after reviewing the task notes.')
    def save_checkpoint(self):
        if not self.task_choice.currentData():self.note.setText('Create a task first.');return
        try:bindings=json.loads(self.reference_json.toPlainText())
        except ValueError:self.note.setText('Source bindings must be valid JSON.');return
        lines=lambda widget:[v.strip() for v in widget.toPlainText().splitlines() if v.strip()]
        note={'goal':self.goal.text().strip(),'next_step':self.next_step.text().strip(),'summary':self.summary_edit.toPlainText(),'constraints':lines(self.constraints),'findings':lines(self.findings),'contradictions':lines(self.contradictions)}
        args={'task':self.task_choice.currentData(),'expected_previous':self.last_checkpoint['id'] if self.last_checkpoint else '', 'note':note,'references':bindings,'jobs':[v.strip() for v in self.jobs_edit.text().split(',') if v.strip()]}
        if self.conversation_id.text().strip():args['conversation']=self.conversation_id.text().strip()
        self.call('memory.checkpoint.save',args,self.saved)
    def saved(self,value):
        self.loaded_checkpoint(value);self.show_record({'checkpoint':value['id'],'readback_verified':value['verified_readback'],'old_transcript_messages':value['transcript_messages'],'old_transcript_characters':value['transcript_characters'],'checkpoint_note_characters':len(json.dumps(value['note'],ensure_ascii=False)),'source_addresses':value['references'],'old_context_disposed':False});self.note.setText('Checkpoint committed and independently read back. Fresh context is a separate action.')
    def preview_context(self):
        if self.last_checkpoint:self.call('memory.checkpoint.context',{'id':self.last_checkpoint['id'],'context':self.context()},self.show_record)
    def rebind_sources(self):
        if not self.last_checkpoint:return
        def choose(value):
            rows=value['namespaces'];labels=[v['name']+' · '+v['id'][:8] for v in rows]
            if not labels:self.note.setText('Review and index recovered originals in Intake first.');return
            label,ok=QInputDialog.getItem(self,'Relink identical originals','Reviewed reference library',labels,0,False)
            if ok:self.call('memory.checkpoint.rebind',{'id':self.last_checkpoint['id'],'namespace':rows[labels.index(label)]['id'],'reason':'Owner selected reviewed identical originals after recovery'},lambda v:(self.loaded_checkpoint(v),self.show_record(v)))
        self.call('intake.namespaces',{},choose)
    def clear_context(self):
        if self.last_checkpoint:self.call('memory.context.clear',{'checkpoint':self.last_checkpoint['id'],'expected_context':self.last_checkpoint['transcript_digest']},self.cleared)
    def cleared(self,value):self.conversation_id.setText(value['conversation']);self.show_record(value);self.task_pages.setCurrentIndex(1);self.note.setText('Fresh working context ready. The checkpoint and old private history are preserved.')
    def ask(self):
        if self.job or not self.last_checkpoint:return
        args={'message':self.question.text().strip() or 'What is the next useful step for this task?','memory_checkpoint':self.last_checkpoint['id'],'conversation':self.conversation_id.text().strip(),'interaction_context':self.context()}
        self.call('brain.ask',args,self.watch)
    def watch(self,job):self.job=job['id'];self.answer.setPlainText('Local Graphite is reading the current checkpoint and its available sources.');self.note.setText('Local reply running · '+job['id'][:12])
    def poll(self):
        if not self.job or self.stopping:return
        r=self.kernel.dispatch('brain.result',{'id':self.job},self.principal)
        if not r['ok']:return
        v=r['result']
        if v['state'] not in ('Completed','Failed','Cancelled','Interrupted'):return
        self.job=None;result=v.get('result') or {};self.show_record(result)
        if v['state']=='Completed':
            body='<p>'+html.escape(result['text'].partition('\n\nSources:\n')[0]).replace('\n','<br>')+'</p>'
            for row in result.get('references',[]):body+='<p><a style="color:#504d46;text-decoration:underline;text-decoration-color:#cba5a4" href="reference:'+row['id']+'">'+html.escape(row['name']+' · '+row['label'])+'</a></p>'
            self.answer.setHtml(body+'<p><small>Local model interpretation; source locations checked separately.</small></p>');self.note.setText('Local reply ready · resumed from durable memory')
        else:self.answer.setPlainText(result.get('reason') or v.get('error') or v['state']);self.note.setText('Local reply '+v['state'])
    def cancel(self):
        if self.job:self.call('jobs.cancel',{'id':self.job},lambda v:self.note.setText('Reply cancellation requested through the shared Kernel.'))
    def follow_citation(self,url):
        ident=url.toString().removeprefix('reference:');row=next((v for v in (self.last_checkpoint or {}).get('references',[]) if v['id']==ident),None)
        if row:
            self.call('references.resolve',{k:row[k] for k in ('namespace','id','item')},lambda v:self.details.setPlainText((v.get('text') or 'Original unavailable; cached text withheld.')+'\n\n'+json.dumps({k:x for k,x in v.items() if k!='text'},indent=2,ensure_ascii=False)))
    def propose_lesson(self):
        try:bindings=json.loads(self.reference_json.toPlainText())
        except ValueError:self.note.setText('Source bindings must be valid JSON.');return
        self.call('memory.lesson.propose',{'title':self.lesson_title.text().strip(),'body':self.lesson_body.toPlainText(),'references':bindings},lambda v:(self.show_record(v),self.refresh_lessons()))
    def refresh_lessons(self):
        def loaded(value):
            self.lesson_tree.clear()
            for row in value['lessons']:
                item=QTreeWidgetItem([row['title'],row['review'],row['applicability']]);item.setData(0,Qt.UserRole,row);self.lesson_tree.addTopLevelItem(item)
        self.call('memory.lessons',{},loaded)
    def select_lesson(self):
        row=self.lesson_tree.currentItem()
        if row:self.show_record(row.data(0,Qt.UserRole))
    def review_lesson(self,approved):
        row=self.lesson_tree.currentItem()
        if row:self.call('memory.lesson.review',{'id':row.data(0,Qt.UserRole)['id'],'approved':approved,'reason':'Owner reviewed procedure in Memory panel'},lambda v:(self.show_record(v),self.refresh_lessons()))
    def stac(self,op):self.call(op,{'program':self.program.toPlainText().strip()},self.show_record)
    def stac_reference(self):
        if self.current_reference:
            namespace,row=self.current_reference;self.program.setPlainText('library '+namespace+' | reference '+row['id'])
        else:self.note.setText('Attach a selected reference using Keep in task memory in Exact references.')
    def translated(self,value):self.program.setPlainText(value['program']);self.show_record(value)
    def export_stac(self):
        path,_=QFileDialog.getSaveFileName(self,'Export a fresh result','','JSON (*.json)')
        if path:self.call('stac.export',{'program':self.program.toPlainText().strip(),'destination':path},self.show_record)
    def export_memory(self):
        path,_=QFileDialog.getSaveFileName(self,'Export private memory and a separate recovery key','','ZIP (*.zip)')
        if path:self.call('memory.archive.export',{'destination':path,'key_path':str(Path(path).with_suffix('.key'))},lambda v:(self.show_record(v),self.note.setText('Private snapshot saved. Keep the separate recovery key. This ZIP contains private data and is not encrypted.')))
    def restore_memory(self):
        path,_=QFileDialog.getOpenFileName(self,'Restore into empty private learning state','','ZIP (*.zip)')
        if not path:return
        key,_=QFileDialog.getOpenFileName(self,'Select the separate recovery key','','Recovery key (*.key)')
        if key:self.call('memory.archive.restore',{'path':path,'key_path':key},lambda v:(self.show_record(v),self.refresh_profile(),self.load_tasks(),self.refresh_lessons(),self.note.setText('Memory restored. Source copies await Intake review and explicit checkpoint relinking.')))
    def shutdown_engineering(self):self.timer.stop();self.research_page.shutdown_engineering();self.study_page.shutdown_engineering();super().shutdown_engineering()
