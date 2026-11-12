"""Native source-page reader with separate explicit annotations and recovery."""
from __future__ import annotations
from .text_prompts import writing_prompt
import json,uuid
from PySide6.QtCore import Qt,QTimer,QRectF,Signal
from PySide6.QtGui import QPixmap,QPainter,QPen,QColor,QTextCursor,QFontDatabase
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QSpinBox, QComboBox, QLineEdit, QPlainTextEdit, QTabWidget, QScrollArea, QSplitter, QTreeWidget, QTreeWidgetItem, QApplication, QMessageBox, QInputDialog, QFileDialog, QTextEdit
from .register_tabs import ServiceTab
from sdk.cli.arc1cli import pdf_evidence as pdf,record_store as records
from . import locations

_CJK_FONTS=set()


class PageCanvas(QWidget):
    selected=Signal(object)
    def __init__(self):
        super().__init__();self.image=QPixmap();self.region=[0,0,1,1];self.annotations=[];self.origin=None
        self.setAccessibleName('Original PDF page; drag a region for a source-bound note')
        self.setMinimumSize(1,1)
    def clear(self):self.image=QPixmap();self.setFixedSize(1,1);self.update()
    def set_image(self,path,width):
        self.image=QPixmap(str(path))
        if self.image.isNull():raise ValueError('Rendered original page is unavailable')
        self.scale_to(width)
    def scale_to(self,width):
        if self.image.isNull():return
        width=max(100,min(5000,int(width)));self.setFixedSize(width,max(1,round(width*self.image.height()/self.image.width())));self.update()
    def paintEvent(self,event):
        if self.image.isNull():return
        p=QPainter(self);p.drawPixmap(self.rect(),self.image)
        for region in [v['anchor']['rect'] for v in self.annotations]+[self.region]:
            if region==[0,0,1,1]:continue
            x,y,w,h=region;p.setPen(QPen(QColor('#d38f39'),2));p.drawRect(QRectF(x*self.width(),y*self.height(),w*self.width(),h*self.height()))
    def point(self,event):return [max(0,min(1,event.position().x()/self.width())),max(0,min(1,event.position().y()/self.height()))]
    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton and not self.image.isNull():self.origin=self.point(event)
    def mouseMoveEvent(self,event):
        if self.origin is not None:
            x,y=self.point(event);a,b=self.origin;self.region=[min(x,a),min(y,b),abs(x-a),abs(y-b)];self.update()
    def mouseReleaseEvent(self,event):
        if self.origin is not None:
            self.mouseMoveEvent(event);self.origin=None
            if min(self.region[2:])>.002:self.region=pdf.rect(self.region);self.selected.emit(self.region)


class PdfDocumentTab(ServiceTab):
    def __init__(self,host):
        super().__init__(host);self.setProperty('concern_context','library')
        # Cold session restoration can open this reader before Exact References
        # has registered the already bundled, licensed Chinese fallback font.
        cjk=locations.program(host.root)/'branding/fonts/NotoSansCJKsc-Regular.otf'
        if cjk.is_file() and str(cjk) not in _CJK_FONTS and QFontDatabase.addApplicationFont(str(cjk))>=0:_CJK_FONTS.add(str(cjk))
        frame=self.outer;self.content=QWidget();self.outer=QVBoxLayout(self.content);self.outer.setContentsMargins(0,0,0,0)
        self.reader_scroll=QScrollArea();self.reader_scroll.setWidgetResizable(True);self.reader_scroll.setWidget(self.content);frame.addWidget(self.reader_scroll)
        self.document=None;self.page_result=None;self.source={};self.page_index=0;self._epoch=0;self._page_job=None;self._export_job=None
        self.table_page_job=None
        self.writer=uuid.uuid4().hex;self.edit_id=None;self.version=0;self.baseline={};self._loading=False
        self.heading=QLabel('Technical PDF');self.heading.setTextFormat(Qt.PlainText);self.heading.setWordWrap(True);self.heading.setStyleSheet('font-size:18px;font-weight:bold');self.outer.addWidget(self.heading)
        self.navigation_grid=QGridLayout();self.previous=QPushButton('Previous');self.previous.clicked.connect(lambda:self.go(-1))
        self.page=QSpinBox();self.page.setRange(1,512);self.page.setAccessibleName('Physical PDF page');self.page.editingFinished.connect(lambda:self.navigate(self.page.value()-1))
        self.next=QPushButton('Next');self.next.clicked.connect(lambda:self.go(1))
        self.zoom=QComboBox();self.zoom.addItems(['Fit width','125%','150%','200%']);self.zoom.currentIndexChanged.connect(self.fit)
        self.refresh_button=QPushButton('Check original');self.refresh_button.clicked.connect(self.recheck)
        self.navigation_widgets=[self.previous,self.page,self.next,self.zoom,self.refresh_button];self.outer.addLayout(self.navigation_grid)
        self.location=QLabel('Choose an admitted PDF in Exact References.');self.location.setWordWrap(True);self.location.setTextFormat(Qt.PlainText);self.outer.addWidget(self.location)
        self.action_grid=QGridLayout();self.buttons={}
        from .datasheet_qt import review_pdf_table
        for index,(label,fn) in enumerate((('Copy citation',self.copy_citation),('Open citation',self.open_citation),('OCR this page',self.ocr),
                ('Review table',lambda:review_pdf_table(self)),('Export library volume',self.export),
                ('Focus reading',lambda:host.set_workspace_layout('focus')),('Share page view',self.share_page))):
            button=QPushButton(label);button.clicked.connect(fn);self.buttons[label]=button
        self.outer.addLayout(self.action_grid)
        self.split=QSplitter(Qt.Horizontal);self.views=QTabWidget();self.scroll=QScrollArea();self.scroll.setWidgetResizable(False);self.canvas=PageCanvas();self.scroll.setWidget(self.canvas);self.views.addTab(self.scroll,'Original page')
        self.native=QPlainTextEdit();self.native.setReadOnly(True);self.views.addTab(self.native,'Native text')
        self.ocr_text=QPlainTextEdit();self.ocr_text.setReadOnly(True);self.views.addTab(self.ocr_text,'OCR · unverified')
        self.proof=QPlainTextEdit();self.proof.setReadOnly(True);self.views.addTab(self.proof,'Source / tools')
        self.split.addWidget(self.views)
        notes=QWidget();box=QVBoxLayout(notes);box.setContentsMargins(4,0,0,0)
        self.list=QTreeWidget();self.list.setHeaderLabels(['Page / kind','Your annotation']);self.list.setAccessibleName('Saved PDF annotations');self.list.itemActivated.connect(self.select_annotation);box.addWidget(self.list,1)
        self.kind=QComboBox();self.kind_labels={'NOTE':'Note','QUESTION':'Question','TABLE_CONTEXT':'Table context','FIGURE_CONTEXT':'Figure context','PRINTED_PAGE':'Printed page label'}
        for key,label in self.kind_labels.items():self.kind.addItem(label,key)
        self.kind.setAccessibleName('Annotation kind');box.addWidget(self.kind)
        self.printed=QLineEdit();writing_prompt(self.printed, 'Printed label you observed · optional');self.printed.setAccessibleName('Owner-observed printed page label');box.addWidget(self.printed)
        self.editor=QPlainTextEdit();self.editor.setProperty('arcReadingRole','prose');writing_prompt(self.editor, 'Your note. Drag a page region to keep its table or figure context.');self.editor.setAccessibleName('PDF annotation text');self.editor.setMinimumHeight(95);self.editor.setEnabled(False);box.addWidget(self.editor,1)
        buttons=QGridLayout();self.save_button=QPushButton('Save note');self.save_button.clicked.connect(self.save_note);buttons.addWidget(self.save_button,0,0)
        new=QPushButton('New note');new.clicked.connect(self.new_note);buttons.addWidget(new,0,1)
        reload=QPushButton('Reload notes');reload.clicked.connect(self.reload_notes);buttons.addWidget(reload,1,0)
        self.recover_button=QPushButton('Recover draft');self.recover_button.clicked.connect(self.recover);buttons.addWidget(self.recover_button,1,1);box.addLayout(buttons)
        self.region_label=QLabel('Full page · notes remain owner annotations');self.region_label.setWordWrap(True);box.addWidget(self.region_label)
        self.split.addWidget(notes);self.split.setSizes([780,330]);self.outer.addWidget(self.split,1);self.outer.addWidget(self.status)
        self.draft_timer=QTimer(self);self.draft_timer.setSingleShot(True);self.draft_timer.setInterval(600);self.draft_timer.timeout.connect(self.flush_draft)
        self.editor.textChanged.connect(self.edited);self.kind.currentTextChanged.connect(self.edited);self.printed.textChanged.connect(self.edited);self.canvas.selected.connect(self.region_selected)
        self.timer=QTimer(self);self.timer.setInterval(350);self.timer.timeout.connect(self.poll);self.timer.start();self.clear_editor();self.arrange()
    def title(self):return 'PDF · '+(self.document['name'] if self.document else 'original source')
    def share_page(self):
        from .window_views_qt import share_pdf
        return share_pdf(self)
    def info(self):return self.location.text()
    def resizeEvent(self,event):
        if hasattr(self,'split'):self.arrange();self.fit()
        super().resizeEvent(event)
    def arrange(self):
        available=max(250,self.reader_scroll.viewport().width()-20)
        state=(5 if available>=800 else 3 if available>=500 else 2,3 if available>=850 else 2 if available>=620 else 1,available<720)
        if state==getattr(self,'_arrangement',None):return
        self._arrangement=state
        for grid,widgets,columns in ((self.navigation_grid,self.navigation_widgets,state[0]),(self.action_grid,list(self.buttons.values()),state[1])):
            for index,widget in enumerate(widgets):grid.removeWidget(widget);grid.addWidget(widget,index//columns,index%columns)
            for column in range(5):grid.setColumnStretch(column,1 if column<columns else 0)
        self.split.setOrientation(Qt.Vertical if state[2] else Qt.Horizontal);self.split.setMinimumHeight(650 if state[2] else 360)
    def fit(self,*args):
        factor=(1,1.25,1.5,2)[self.zoom.currentIndex()];self.canvas.scale_to(max(150,self.scroll.viewport().width()-6)*factor)
    def fields(self):return {'text':self.editor.toPlainText(),'kind':self.kind.currentData(),'printed_label':self.printed.text(),'rect':list(self.canvas.region)}
    def is_dirty(self):
        fields=self.fields();return fields['text']!=self.baseline.get('text','') or bool(fields['text']) and fields!=self.baseline
    def clear_editor(self,value=None):
        self._loading=True;value=value or {};self.edit_id=value.get('id');self.version=value.get('version',0)
        self.editor.setPlainText(value.get('text',''));self.kind.setCurrentIndex(self.kind.findData(value.get('kind','NOTE')));self.printed.setText(value.get('printed_label',''))
        self.canvas.region=list(value.get('anchor',{}).get('rect',[0,0,1,1]));self.canvas.update();self.baseline=self.fields();self._loading=False
    def edited(self,*args):
        if not self._loading and self.is_dirty():self.draft_timer.start()
    def region_selected(self,region):
        self.region_label.setText('Selected page region · '+', '.join(str(round(v,3)) for v in region));self.edited()
    def open_document(self,namespace,item,source_sha=None,page_index=0,region=None):
        if not self.can_close_pdf():return
        self._epoch+=1;epoch=self._epoch
        self.invalidate_page();self.document=None;self.list.clear();self._annotations=[]
        self.source={'namespace':namespace,'item':item};self.page_index=page_index;self.clear_editor();self._wanted_region=region
        if source_sha:self.source['source_sha256']=source_sha
        self.call('references.pdf.info',dict(self.source),lambda value:self.loaded_info(epoch,value),lambda error:self.unavailable(error.get('message','Original unavailable')) if epoch==self._epoch else None)
    def loaded_info(self,epoch,value):
        if epoch!=self._epoch:return
        if value['state']!='CURRENT':self.unavailable('; '.join(value['gaps']));return
        self.document=value;self.source['source_sha256']=value['source_sha256'];self.heading.setText(value['name'])
        self.host.tabs.setTabText(self.host.tabs.indexOf(self),self.title())
        if not 0<=self.page_index<value['page_count']:self.unavailable('Physical page is outside this original.');return
        self.page.setMaximum(value['page_count']);self.page.setValue(self.page_index+1);self.load_page();self.reload_notes()
    def recheck(self):
        if self.source:self.open_document(**{'namespace':self.source['namespace'],'item':self.source['item'],'source_sha':self.source.get('source_sha256'),'page_index':self.page_index})
    def go(self,delta):self.navigate(self.page_index+delta)
    def navigate(self,index):
        if not self.document or index==self.page_index or not 0<=index<self.document['page_count']:return
        if not self.can_close_pdf():self.page.setValue(self.page_index+1);return
        self.page_index=index;self.page.setValue(index+1);self.clear_editor();self._wanted_region=None;self.load_page();self.load_draft_status()
    def load_page(self,ocr=False,language='eng'):
        if self._page_job:self.kernel.dispatch('jobs.cancel',{'id':self._page_job},self.principal)
        self._page_job=None;self.invalidate_page()
        self._epoch+=1;epoch=self._epoch;self.timer.start();self.status.setText('Reading the exact original page…')
        args={**self.source,'page_index':self.page_index,'ocr':ocr,'language':language,'request_key':uuid.uuid4().hex}
        self.call('references.pdf.page',args,lambda job:self.watch(epoch,job),lambda error:self.unavailable(error.get('message','Page unavailable')) if epoch==self._epoch else None)
    def watch(self,epoch,job):
        if epoch!=self._epoch:
            self.kernel.dispatch('jobs.cancel',{'id':job['id']},self.principal);return
        self._page_job=job['id'];self._job_epoch=epoch
    def poll(self):
        for attr in ('_page_job','_export_job'):
            ident=getattr(self,attr)
            if not ident:continue
            result=self.kernel.dispatch('jobs.get',{'id':ident},self.principal)
            if not result['ok']:continue
            job=result['result']
            if job['state'] not in ('Completed','Failed','Cancelled','Interrupted'):continue
            setattr(self,attr,None)
            if attr=='_page_job':
                epoch=self._job_epoch
                self.call('references.pdf.result',{'job':ident},lambda value, epoch=epoch, ident=ident:self.rendered(epoch,value,ident))
            elif job['state']=='Completed':
                self.call('references.volume.publish',{'job':ident},
                    lambda value:self.status.setText('Library volume exported · '+value['path']))
            else:self.status.setText('Library volume export · '+job['state'])
    def invalidate_page(self):
        self.page_result=None;self.table_page_job=None;self.canvas.clear();self.native.clear();self.ocr_text.clear();self.proof.clear()
        self.editor.setEnabled(False);self.save_button.setEnabled(False);self.recover_button.setEnabled(False)
        self.location.setText('Checking original page…')
    def unavailable(self,message):
        self.invalidate_page();self.location.setText('Original unavailable · '+message);self.status.setText(message)
        if self.host.tabs.currentWidget() is self:self.host.update_document_info()
    def rendered(self,epoch,envelope,job=None):
        if epoch!=self._epoch:return
        value=envelope.get('result') or {}
        if envelope['state']!='Completed' or value.get('status')!='RENDERED':self.unavailable(value.get('reason') or '; '.join(value.get('gaps',[])) or envelope['state']);return
        try:
            image=self.kernel.safe(value['image'])
            if records.sha(image)!=value['image_sha256']:raise ValueError('Page image changed; check the original again.')
            self.canvas.set_image(image,max(150,self.scroll.viewport().width()-6))
        except (ValueError,OSError) as exc:self.unavailable(str(exc));return
        self.page_result=value;self.table_page_job=job;self.save_button.setEnabled(True);self.editor.setEnabled(True);self.native.setPlainText(value['native']['text'] or 'No native text layer. OCR is available as a separate, unverified derivative.')
        self.ocr_text.setPlainText((value['ocr'] or {}).get('text','OCR was not requested.'))
        self.ocr_text.setExtraSelections([])
        if value['ocr']:
            selections=[];start=0
            for word in value['ocr']['words']:
                found=self.ocr_text.toPlainText().find(word['text'],start)
                if found<0:continue
                start=found+len(word['text'])
                if word['uncertain']:
                    selection=QTextEdit.ExtraSelection();cursor=self.ocr_text.textCursor();cursor.setPosition(found);cursor.setPosition(start,QTextCursor.KeepAnchor);selection.cursor=cursor;selection.format.setBackground(QColor('#73591d'));selections.append(selection)
            self.ocr_text.setExtraSelections(selections)
        self.proof.setPlainText(json.dumps({k:v for k,v in value.items() if k not in ('native','ocr')},indent=2,ensure_ascii=False)+'\n\nNative and OCR are derivatives. Confidence is an engine score, not correctness probability.')
        self.refresh_location()
        self.status.setText(('OCR is unverified · '+str(value['ocr']['uncertain_words'])+' lower-score words highlighted · check symbols and units against the image.') if value['ocr'] else 'Original and page checked · drag a region for table or figure context. No accepted fact is created.')
        if self._wanted_region:self.canvas.region=list(self._wanted_region);self.canvas.update();self._wanted_region=None
        self.fit();self.load_draft_status();self.update_regions()
    def ocr(self):
        if not self.page_result:return
        language,ok=QInputDialog.getItem(self,'OCR language','Installed language data is checked before recognition:',list(pdf.LANGUAGES),0,False)
        if ok:self.load_page(True,language)
    def args(self):
        value={**self.source,'page_index':self.page_index,**self.fields(),'expected_version':self.version,'writer':self.writer}
        if self.edit_id:value['id']=self.edit_id
        return value
    def save_note(self):
        if not self.page_result or not self.editor.toPlainText().strip():self.status.setText('Write a note on an available original page before saving.');return False
        args=self.args();result=self.kernel.dispatch('references.pdf.annotation.save',args,self.principal)
        if not result['ok']:self.status.setText(result['error']['message']);return False
        self.clear_editor(result['result']);self.reload_notes();self.status.setText('Annotation saved separately from the original and accepted facts.');return True
    def flush_draft(self):
        if not self.source.get('source_sha256') or not self.is_dirty():return True
        result=self.kernel.dispatch('references.pdf.draft.put',self.args(),self.principal)
        if not result['ok']:self.status.setText('Recovery draft could not be saved: '+result['error']['message'])
        return result['ok']
    def load_draft_status(self):
        if not self.source.get('source_sha256'):return
        epoch=self._epoch
        self.call('references.pdf.draft.get',{**self.source,'page_index':self.page_index},lambda value:self.recover_button.setEnabled(bool(value['drafts']) and self.page_result is not None) if epoch==self._epoch else None)
    def recover(self):
        if not self.can_close_pdf():return
        value=self.kernel.dispatch('references.pdf.draft.get',{**self.source,'page_index':self.page_index},self.principal)
        if not value['ok'] or not value['result']['drafts']:return
        draft=value['result']['drafts'][0];self._loading=True
        self.editor.setPlainText(draft['text']);self.kind.setCurrentIndex(self.kind.findData(draft['kind']));self.printed.setText(draft.get('printed_label',''));self.canvas.region=list(draft['rect'])
        self.edit_id=draft.get('id');self.version=draft['expected_version'];self._loading=False;self.canvas.update();self.edited();self.status.setText('Recovery draft loaded for review. Save is still required.')
    def can_close_pdf(self):
        if not self.is_dirty():return True
        if not self.flush_draft():return False
        choice=QMessageBox.question(self,'Unsaved PDF annotation','Save this annotation before leaving this page?',QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel,QMessageBox.Cancel)
        if choice==QMessageBox.Cancel:return False
        return self.save_note() if choice==QMessageBox.Save else True
    def new_note(self):
        if self.can_close_pdf():self.clear_editor()
    def reload_notes(self):
        if not self.source:return
        source=dict(self.source)
        self.call('references.pdf.annotations',{'namespace':source['namespace'],'item':source['item']},lambda value:self.notes_loaded(value) if source==self.source else None)
    def notes_loaded(self,value):
        self.list.clear();self._annotations=value['annotations']
        for note in value['annotations']:
            row=QTreeWidgetItem([str(note['anchor']['page_index']+1)+' · '+self.kind_labels[note['kind']],note['text'][:100]]);row.setData(0,Qt.UserRole,note);row.setToolTip(0,note['binding_state']+' · '+self.kind_labels[note['kind']]);row.setToolTip(1,note['text']);self.list.addTopLevelItem(row)
        self.update_regions()
    def update_regions(self):
        self.canvas.annotations=[v for v in getattr(self,'_annotations',[]) if v['anchor']['page_index']==self.page_index and v['anchor']['source_sha256']==self.source.get('source_sha256')];self.canvas.update()
        self.refresh_location()
    def refresh_location(self):
        if not self.page_result:return
        value=self.page_result;page=value['page'];labels={v['printed_label'] for v in self.canvas.annotations if v.get('printed_label')}
        observed=next(iter(labels))+' (owner observed)' if len(labels)==1 else 'conflicting owner observations' if labels else 'not established'
        self.location.setText('Physical page '+str(page['physical_page'])+' / '+str(value['page_count'])+' · PDF label '+(page['pdf_label'] or 'not declared')+' · printed label '+observed+'\nOriginal SHA-256 '+value['source_sha256'][:20]+'… · full identity in Source / tools')
        if self.host.tabs.currentWidget() is self:self.host.update_document_info()
    def select_annotation(self,row,*args):
        if not self.can_close_pdf():return
        value=row.data(0,Qt.UserRole)
        if value['anchor']['source_sha256']!=self.source.get('source_sha256'):self.status.setText('This annotation belongs to another original edition.');return
        self.page_index=value['anchor']['page_index'];self.page.setValue(self.page_index+1);self.clear_editor(value);self._wanted_region=value['anchor']['rect'];self.load_page()
    def copy_citation(self):
        if not self.page_result:return
        QApplication.clipboard().setText(json.dumps(pdf.citation(self.source['namespace'],self.source['item'],self.source['source_sha256'],self.page_index,self.canvas.region),ensure_ascii=False))
        self.status.setText('Exact original/page/region citation copied. Printed page labels remain separate.')
    def open_citation(self):
        text,ok=QInputDialog.getMultiLineText(self,'Open exact citation','Paste a Graphite PDF citation:')
        if not ok:return
        try:value=record_io_json(text)
        except ValueError:self.status.setText('This is not a valid citation object.');return
        def opened(result):
            c=result['citation'];self.open_document(c['namespace'],c['item'],c['source_sha256'],c['page_index'],c['rect'])
        self.call('references.pdf.citation.resolve',{'citation':value},opened)
    def export(self):
        if not self.source:return
        namespace=self.source['namespace']
        destination,_=QFileDialog.getSaveFileName(self,'Export originals, indexed references and your annotations','','Reference volume (*.zip)')
        if not destination:return
        def status(value):
            self.call('references.volume.export',{'namespace':namespace,'destination':destination,'expected_generation':value['generation']},lambda job:setattr(self,'_export_job',job['id']))
        self.call('references.status',{'namespace':namespace},status);self.timer.start()
    def shutdown_engineering(self):
        self.timer.stop();self.draft_timer.stop();self.flush_draft();super().shutdown_engineering()

def record_io_json(text):
    from .record_io import strict_json
    if len(text)>4096:raise ValueError('Citation limit')
    return strict_json(text)

def open_pdf(host,namespace,item,source_sha=None,page_index=0,region=None):
    host._close_start()
    for i in range(host.tabs.count()):
        tab=host.tabs.widget(i)
        if isinstance(tab,PdfDocumentTab) and tab.source.get('namespace')==namespace and tab.source.get('item')==item:
            host.tabs.setCurrentWidget(tab);tab.open_document(namespace,item,source_sha,page_index,region);return tab
    tab=PdfDocumentTab(host)
    if host.tabs.addTab(tab,'Technical PDF')<0:return None
    host.tabs.setCurrentWidget(tab);tab.open_document(namespace,item,source_sha,page_index,region);return tab
