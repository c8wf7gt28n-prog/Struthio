"""Ledger-native exact references, original pages, evidence and local EKPs."""
from .text_prompts import writing_prompt
import html,json
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QPixmap,QFontDatabase
from PySide6.QtWidgets import (QWidget,QLabel,QPushButton,QComboBox,QLineEdit,QPlainTextEdit,QTextBrowser,QTreeWidget,QTreeWidgetItem,
 QHBoxLayout,QVBoxLayout,QGridLayout,QSplitter,QTabWidget,QScrollArea,QFileDialog,QDialog,QDialogButtonBox,QFormLayout,QAbstractItemView)
from .register_tabs import ServiceTab
from . import reference_service as refs,local_brain
from sdk.cli.arc1cli import record_store as records
from . import locations,page_light
from . import doorway  # 0.8.7 C1 (the doorway)
from . import page_marks  # 0.8.7 C2 (pages in pencil)

def esc(value):return html.escape(str(value))

class ReferenceTab(ServiceTab):
    def __init__(self,host):
        super().__init__(host);self.job=None;self.citation=None;self.packet=None;self.generation=0;self.current_sources=0;self.offset=0;self.total=0;self.list_epoch=0;self.mode='browse'
        self.project_collection=None
        heading=QLabel('GRAPHITE · EXACT REFERENCES');heading.setStyleSheet('font-size:18px;color:#edaa69;font-weight:bold');self.outer.addWidget(heading)
        self.note=QLabel('Search admitted originals, inspect their exact locations, and collect the evidence for a question. Source admission and engineering qualification remain separate.');self.note.setWordWrap(True);self.outer.addWidget(self.note)
        row=QHBoxLayout();self.namespaces=QComboBox();self.namespaces.setAccessibleName('Reference library');self.namespaces.currentIndexChanged.connect(self.changed_namespace);row.addWidget(self.namespaces,1)
        intake=QPushButton('Review intake');intake.clicked.connect(host.ledger_bridge.show_intake);row.addWidget(intake);connections=QPushButton('Source connections');connections.clicked.connect(host.ledger_bridge.show_sources);row.addWidget(connections);self.outer.addLayout(row)
        grid=QGridLayout()
        for i,(label,fn) in enumerate([('Index admitted sources',self.index),('Refresh',self.refresh),('Open original location',self.original),('Read technical PDF',self.read_pdf),('Export collection',self.export),('Cancel job',self.cancel),('Keep in task memory',self.remember)]):
            button=QPushButton(label);button.setAccessibleName(label);button.clicked.connect(fn);grid.addWidget(button,i//2,i%2)
        self.outer.addLayout(grid);self.outer.addWidget(self.status)
        self.pages=QTabWidget();browse=QWidget();box=QVBoxLayout(browse);box.setContentsMargins(0,0,0,0)
        self.sources=QComboBox();self.sources.setAccessibleName('Indexed source');self.sources.currentIndexChanged.connect(self.source_changed);box.addWidget(self.sources)
        self.sources.activated.connect(lambda _:self.source_changed() if self.mode=='search' else None)
        row=QHBoxLayout();self.query=QLineEdit();writing_prompt(self.query, 'Find words, identifiers or Chinese text');self.query.returnPressed.connect(self.search);row.addWidget(self.query,1);find=QPushButton('Find');find.clicked.connect(self.search);row.addWidget(find);box.addLayout(row)
        self.hits=QTreeWidget();self.hits.setHeaderLabels(['Original','Exact location','State']);self.hits.setColumnWidth(0,200);self.hits.setColumnWidth(1,250);self.hits.setSelectionMode(QAbstractItemView.ExtendedSelection);self.hits.itemSelectionChanged.connect(self.selected);self.hits.setAccessibleName('Exact reference passages');box.addWidget(self.hits,1)
        pager=QHBoxLayout();previous=QPushButton('Previous');previous.clicked.connect(lambda:self.page(-1));pager.addWidget(previous);self.page_label=QLabel();pager.addWidget(self.page_label,1);following=QPushButton('Next');following.clicked.connect(lambda:self.page(1));pager.addWidget(following);box.addLayout(pager);self.pages.addTab(browse,'References')
        atlas=QWidget();abox=QVBoxLayout(atlas);abox.setContentsMargins(0,0,0,0)
        self.subject=QLineEdit();writing_prompt(self.subject, 'Subject, for example J14 or U45');abox.addWidget(self.subject)
        buttons=QGridLayout()
        for i,(label,fn) in enumerate([('Evidence atlas',self.atlas),('Preview source impact',self.impact),('Review a source fact',self.fact),('Link this reference',self.link)]):
            button=QPushButton(label);button.clicked.connect(fn);buttons.addWidget(button,i//2,i%2)
        abox.addLayout(buttons);fields=QFormLayout();self.property_field=QLineEdit();writing_prompt(self.property_field, 'Property, for example tCEM');fields.addRow('Property',self.property_field);self.variant=QLineEdit();fields.addRow('Exact variant',self.variant);self.conditions=QLineEdit('{}');fields.addRow('Conditions (JSON)',self.conditions);abox.addLayout(fields)
        ask=QPushButton('Ask the source records');ask.clicked.connect(self.question_records);abox.addWidget(ask);self.atlas_view=QTextBrowser();self.atlas_view.setOpenLinks(False);abox.addWidget(self.atlas_view,1);self.pages.addTab(atlas,'Evidence / impact')
        packets=QWidget();pbox=QVBoxLayout(packets);pbox.setContentsMargins(0,0,0,0);self.question=QLineEdit();writing_prompt(self.question, 'Question for the selected references');pbox.addWidget(self.question)
        compile_button=QPushButton('Compile selected references');compile_button.clicked.connect(self.compile);pbox.addWidget(compile_button)
        ask=QPushButton('Ask local Graphite with this packet');ask.clicked.connect(self.ask);pbox.addWidget(ask);self.answer=QTextBrowser();self.answer.setOpenLinks(False);self.answer.anchorClicked.connect(self.follow_citation);pbox.addWidget(self.answer,1)
        export=QPushButton('Export reference volume');export.clicked.connect(self.export);pbox.addWidget(export);verify=QPushButton('Verify a reference volume');verify.clicked.connect(self.verify);pbox.addWidget(verify);self.pages.addTab(packets,'Packets / volume')
        # 0.8.7 W7 (the window wiring): Ask the Library here: the places at once, the desk's own cut quote lit, the wires into it, the footer
        library=QWidget();lbox=QVBoxLayout(library);lbox.setContentsMargins(0,0,0,0);lrow=QHBoxLayout();self.library_found=None;self.library_asking=0
        self.library_query=QLineEdit();writing_prompt(self.library_query,'Ask a question of the pages admitted in this library');self.library_query.setAccessibleName('Your question for the Library');self.library_query.returnPressed.connect(self.ask_library);lrow.addWidget(self.library_query,1)
        asking=QPushButton('Ask the Library');asking.setAccessibleName('Ask the Library');asking.clicked.connect(self.ask_library);lrow.addWidget(asking);lbox.addLayout(lrow)
        self.library_view=QTextBrowser();self.library_view.setOpenLinks(False);self.library_view.setAccessibleName('What the Library says');self.library_view.anchorClicked.connect(self.library_link);lbox.addWidget(self.library_view,1);self.pages.addTab(library,'Ask the Library');self.library_tab=library
        self.detail=QTabWidget();self.excerpt=QPlainTextEdit();self.excerpt.setReadOnly(True);self.detail.addTab(self.excerpt,'Verified excerpt')
        self.image_label=QLabel('Choose a PDF passage, then Open original location.');self.image_label.setAlignment(Qt.AlignCenter);self.image_label.setWordWrap(True);self.image_scroll=QScrollArea();self.image_scroll.setWidgetResizable(True);self.image_scroll.setWidget(self.image_label);self.detail.addTab(self.image_scroll,'Original page')
        self.proof=QPlainTextEdit();self.proof.setReadOnly(True);self.detail.addTab(self.proof,'Provenance')
        # 0.8.7 C1 (the doorway): the passage as it stands at the door, lines written to an assistant outlined with the reason in words
        self.door_view=QTextBrowser();self.door_view.setOpenLinks(False);self.door_view.setAccessibleName('At the door');self.detail.addTab(self.door_view,'At the door')
        # 0.8.7 C2 (pages in pencil): Read this page; pencil underlines with Keep and Rub out; nothing is kept until you keep it
        self.pencil_marks=[];self.pencil_column='';self.pencil_said=[];pencil=QWidget();pen=QVBoxLayout(pencil);pen.setContentsMargins(0,0,0,0);prow=QHBoxLayout()
        self.read_button=QPushButton('Read this page');self.read_button.setAccessibleName('Read this page');self.read_button.clicked.connect(self.read_page);prow.addWidget(self.read_button)
        self.pencil_line=QLabel('Choose a passage, then Read this page. Marks stay in pencil until you keep them.');self.pencil_line.setWordWrap(True);prow.addWidget(self.pencil_line,1);pen.addLayout(prow)
        self.pencil_view=QTextBrowser();self.pencil_view.setOpenLinks(False);self.pencil_view.setAccessibleName('In pencil');self.pencil_view.anchorClicked.connect(self.pencil_link);pen.addWidget(self.pencil_view,1);self.detail.addTab(pencil,'In pencil');self.pencil_tab=pencil
        # 0.8.7 W7 (the window wiring): Read this table on a page with a table (its columns, its rows, its closing line); the page's cross-references drawn beside its places
        self.table_button=QPushButton('Read this table');self.table_button.setAccessibleName('Read this table');self.table_button.setEnabled(False);self.table_button.setToolTip('This page has no table the desk can cut');self.table_button.clicked.connect(self.read_table);prow.insertWidget(1,self.table_button)
        self.table_view=QTextBrowser();self.table_view.setOpenLinks(False);self.table_view.setAccessibleName('This table, read');self.detail.addTab(self.table_view,'Table');self.page_links={};self.pending_place=None;self.wanted_namespace=None
        split=QSplitter(Qt.Vertical);split.addWidget(self.pages);split.addWidget(self.detail);split.setSizes([340,250]);self.outer.addWidget(split,1);self.split=split   # 0.8.7 W7: room given to what was asked for
        self.unavailable_sources=0;self.reference_font_id=-1
        font_path=locations.program(host.root)/'branding/fonts/NotoSansCJKsc-Regular.otf'
        if font_path.is_file():
            self.reference_font_id=QFontDatabase.addApplicationFont(str(font_path))
            families=QFontDatabase.applicationFontFamilies(self.reference_font_id) if self.reference_font_id>=0 else []
            if families:
                for widget in (self.query,self.sources,self.namespaces,self.hits,self.excerpt,self.proof,self.atlas_view,self.answer,self.question,self.subject,self.property_field,self.variant,self.conditions):
                    font=widget.font();font.setFamilies([font.family(),families[0]]);widget.setFont(font)
        self.timer=QTimer(self);self.timer.setInterval(800);self.timer.timeout.connect(self.poll);self.timer.start();QTimer.singleShot(0,self.load_namespaces)
    def title(self):return 'Graphite · References'
    def info(self):return 'Exact references · %d current sources · reference generation %d · source records only'%(self.current_sources,self.generation)
    def ns(self):return self.namespaces.currentData()
    def clear_location(self):
        self.citation=None;self.requested=None;self.excerpt.clear();self.proof.clear();self.door_view.clear();self.pencil_view.clear();self.pencil_marks=[];self.pencil_column='';self.pencil_said=[];self.image_label.clear();self.image_label.setText('Choose a PDF passage, then Open original location.');self.update_inspector()
        self.table_view.clear();self.table_button.setEnabled(False);self.scroll_to_line=None   # 0.8.7 W7: Read this table waits for a page with a table
    def load_namespaces(self):self.call('intake.namespaces',{},self.loaded_namespaces)
    def open_collection(self, namespace, project):
        self.project_collection=(namespace,project)
        index=self.namespaces.findData(namespace)
        if index >= 0:
            self.namespaces.setCurrentIndex(index)
        else:
            self.load_namespaces()
        self.pages.setCurrentIndex(0)

    def loaded_namespaces(self,value):
        current=self.project_collection[0] if self.project_collection else (self.wanted_namespace or self.ns())   # 0.8.7 W7: a place opened from her column chooses its library
        self.namespaces.blockSignals(True);self.namespaces.clear()
        for ns in value['namespaces']:self.namespaces.addItem(ns['name'],ns['id'])
        index=self.namespaces.findData(current)
        self.namespaces.setCurrentIndex(index if self.project_collection else max(0,index))
        self.namespaces.blockSignals(False);self.changed_namespace()
        if self.project_collection and index < 0:
            self.status.setText('The linked source collection is unavailable. Bring it in through Intake.')
    def changed_namespace(self,*args):
        self.list_epoch+=1;self.packet=None;self.mode='browse';self.hits.clear();self.clear_location();self.answer.clear();self.atlas_view.clear();self.offset=0;self.refresh()
    def refresh_status(self):
        if not self.ns():return
        nsid=self.ns()
        def status(value):
            if self.ns()!=nsid:return
            self.generation=value['generation'];self.current_sources=value['current_sources'];self.unavailable_sources=len(value['unavailable']);self.status.setText('%d current sources · generation %d · %d unavailable'%(self.current_sources,self.generation,self.unavailable_sources));self.update_inspector()
        self.call('references.status',{'namespace':nsid},status)
    def refresh(self):
        if not self.ns():self.status.setText('Create a library and admit sources in Review intake.');return
        nsid=self.ns();self.refresh_status()
        def sources(value):
            if self.ns()!=nsid:return
            current=self.sources.currentData();self.sources.blockSignals(True);self.sources.clear()
            for source in value['sources']:self.sources.addItem(source['name']+' · '+source['state'],source['item'])
            self.sources.setCurrentIndex(max(0,self.sources.findData(current)));self.sources.blockSignals(False)
            if self.mode=='browse':self.load_passages()
        self.call('references.sources',{'namespace':nsid},sources)
    def update_inspector(self):
        if hasattr(self.host,'arc_inspector') and self.host.tabs.currentWidget() is self:self.host.arc_inspector.refresh()
    def source_changed(self,*args):self.mode='browse';self.offset=0;self.load_passages()
    def load_passages(self):
        if not self.ns() or not self.sources.currentData():return
        self.list_epoch+=1;epoch=self.list_epoch;nsid=self.ns();item=self.sources.currentData();selected=self.citation['id'] if self.citation and self.citation['item']==item else None;self.hits.clear();self.clear_location()
        def loaded(value):
            if self.list_epoch!=epoch or self.ns()!=nsid:return
            self.total=value['total'];self.hits.blockSignals(True);self.hits.clear()
            for row in value['passages']:
                entry=QTreeWidgetItem([self.sources.currentText().split(' · ')[0],row['label'],'Located']);entry.setData(0,Qt.UserRole,{'id':row['id'],'item':item});self.hits.addTopLevelItem(entry)
            self.hits.blockSignals(False);self.page_label.setText('%d–%d of %d'%(min(self.total,self.offset+1),min(self.total,self.offset+100),self.total))
            if selected:
                entry=next((self.hits.topLevelItem(i) for i in range(self.hits.topLevelItemCount()) if self.hits.topLevelItem(i).data(0,Qt.UserRole)['id']==selected),None)
                if entry:self.hits.setCurrentItem(entry);entry.setSelected(True);self.resolve(entry.data(0,Qt.UserRole))
            if self.pending_place and self.pending_place.get('namespace')==nsid:   # 0.8.7 W7: the place opened from her column
                place=self.pending_place;self.pending_place=None;self.wanted_namespace=None;self.resolve({'id':place['segment'],'item':place['item']});self.scroll_to_line=place.get('first');self.detail.setCurrentWidget(self.pencil_tab)
        self.call('references.passages',{'namespace':nsid,'item':item,'offset':self.offset,'limit':100},loaded)
    def page(self,direction):
        offset=self.offset+direction*100
        if self.mode=='browse' and 0<=offset<self.total:self.offset=offset;self.load_passages()
    def search(self):
        if not self.ns() or not self.query.text().strip():return
        self.mode='search';self.list_epoch+=1;epoch=self.list_epoch;nsid=self.ns();self.clear_location()
        def loaded(value):
            if self.list_epoch!=epoch or self.ns()!=nsid:return
            self.hits.blockSignals(True);self.hits.clear()
            for row in value['hits']:
                entry=QTreeWidgetItem([row['name'],row['label'],row['state']]);entry.setData(0,Qt.UserRole,{'id':row['id'],'item':row['item']});self.hits.addTopLevelItem(entry)
            self.hits.blockSignals(False);self.page_label.setText('%d exact references'%len(value['hits']));self.note.setText('%d current matches · %d located but unavailable · lexical search'%(len(value['hits']),len(value.get('unavailable',[]))))
        self.call('references.search',{'namespace':nsid,'query':self.query.text().strip()},loaded)
    def selected(self):
        row=self.hits.currentItem()
        if row and row.isSelected():self.resolve(row.data(0,Qt.UserRole))
        else:self.clear_location()
    def resolve(self,row):
        self.clear_location();self.requested=row['id'];nsid=self.ns();self.excerpt.setPlainText('Checking the current original and exact location…')
        def loaded(value):
            if self.ns()!=nsid or self.requested!=row['id']:return
            self.citation=value if value['state']=='CURRENT' else None;self.excerpt.setPlainText(value.get('text') or 'Original unavailable. Cached text is not supplied.\n'+ '\n'.join(value.get('gaps',[])));self.proof.setPlainText(json.dumps({k:v for k,v in value.items() if k!='text'},indent=2,ensure_ascii=False))
            if value.get('text'):  # 0.8.7 C1: checked at the door, no model; a page with lines aimed at an assistant opens on this view
                door=doorway.scan(value['text']);self.door_view.setHtml(doorway.owner_html(door))
                if door.withheld():self.detail.setCurrentWidget(self.door_view)
                if self.citation:self.load_pencil()
                if self.citation:   # 0.8.7 W7: Read this table where the desk can cut one; the page's cross-references
                    from . import library_qt
                    found=library_qt.has_table(value['text'],value.get('name') or '');self.table_button.setEnabled(found)
                    self.table_button.setToolTip('Cut this page’s table into columns and check its sums' if found else 'This page has no table the desk can cut')
                    self.load_links()
            self.update_inspector()
        self.call('references.resolve',{'namespace':nsid,**row},loaded)
    # ---- 0.8.7 C2 (pages in pencil) -------------------------------------------------------------------------------------
    def read_page(self):
        if not self.citation or not self.ns():self.pencil_line.setText('Choose a current passage first.');return
        nsid=self.ns();ident=self.citation['id'];self.read_button.setEnabled(False);self.pencil_line.setText('Reading this page…')
        def done(value):
            self.read_button.setEnabled(True)
            if self.ns()!=nsid or not self.citation or self.citation['id']!=ident:return
            self.pencil_column=value['column'];self.pencil_said=list(value.get('said') or []);self.load_pencil();self.detail.setCurrentWidget(self.pencil_tab)
        def failed(error):self.read_button.setEnabled(True);self.pencil_line.setText('This page could not be read in pencil: '+str((error or {}).get('message',''))[:200])
        self.call('library.read',{'namespace':nsid,'id':ident,'item':self.citation['item']},done,failed)
    def load_pencil(self):
        if not self.citation or not self.ns():return
        nsid=self.ns();ident=self.citation['id']
        def loaded(value):
            if self.ns()!=nsid or not self.citation or self.citation['id']!=ident:return
            self.pencil_marks=value['marks'];self.draw_pencil()
        self.call('library.marks',{'namespace':nsid,'id':ident,'item':self.citation['item'],'all':True},loaded)
    def draw_pencil(self):
        text=self.citation['text'] if self.citation else '';door=doorway.scan(text);held=set(door.withheld());by_line={}
        for m in self.pencil_marks:
            now=m.get('now') or {}
            if now.get('state')=='GONE':continue
            by_line.setdefault(now.get('line') or m['line'],[]).append(m)
        live=[m for m in self.pencil_marks if m['state']!='RUBBED_OUT']
        self.pencil_line.setText(self.pencil_column or ('%d places in pencil or ink on this page.'%len(live) if live else 'Nothing on this page is in pencil yet. Read this page to mark it.'))
        body=''.join('<p><small>'+esc(s)+'</small></p>' for s in self.pencil_said)
        from . import library_qt   # 0.8.7 W7: the page's cross-references, a quiet wire beside each place they join
        links=self.page_links.get((self.ns(),self.citation['item'])) if self.citation else None;page_index=((self.citation or {}).get('locator') or {}).get('page_index') or 0
        wires=library_qt.wires_on_page(links,text,page_index);count=library_qt.wires_count(links,page_index)
        if count:body+='<p><small>'+esc(library_qt.say('wires_head',count=count))+'</small></p>'
        for row in door.lines:
            n=row['n']
            if n in held:body+='<p style="color:#8a8a8a">'+str(n)+' · [not shown to the model: this line '+esc(doorway.line_words(door,n))+']</p>';continue
            marks=by_line.get(n,[]);line=row['text'];ink=[0]*len(line)
            for m in marks:
                if m['state']=='RUBBED_OUT':continue
                s,e=(m.get('now') or {}).get('offsets') or m['offsets']
                for i in range(max(0,s),min(len(line),e)):ink[i]=max(ink[i],2 if m['state']=='KEPT' else 1)
            html_line='';i=0
            while i<len(line):
                j=i
                while j<len(line) and ink[j]==ink[i]:j+=1
                part=esc(line[i:j])
                if ink[i]==1:part='<u style="color:#7c7c7c">'+part+'</u>'
                elif ink[i]==2:part='<u style="color:#1f1f1f;font-weight:bold">'+part+'</u>'
                html_line+=part;i=j
            body+='<p style="margin:2px 0"><a name="l'+str(n)+'"></a>'+str(n)+' · '+html_line+'</p>'   # 0.8.7 W7: each line an anchor
            for wire in wires.get(n,()):body+='<p style="margin:0 0 3px 24px;color:#8a8a8a"><small>⤷ '+esc(wire)+'</small></p>'   # 0.8.7 W7
            for m in marks:
                label=m['label_shown']+(' ('+m['label_mark']+')' if m.get('label_mark') else '')
                tag=esc(m['kind'].replace('_',' ')+' · '+label+' · '+' '.join(m['value'].split()))
                state=esc(m['said']+(' · '+m['note'] if m.get('note') else ''))
                if (m.get('now') or {}).get('state')=='MOVED':state+=esc(' · '+page_marks.WORDS['moved'].format(line=m['now']['line']))
                links=''
                if m['state']=='PENCIL':links=' <a href="keep:'+m['id']+'">Keep</a> · <a href="rubout:'+m['id']+'">Rub out</a>'
                elif m['state']=='RUBBED_OUT':links=' <a href="undo:'+m['id']+'">Undo</a>'
                style='color:#8a8a8a;text-decoration:line-through' if m['state']=='RUBBED_OUT' else 'color:#5a5a5a'
                body+='<p style="margin:0 0 4px 24px;'+style+'"><small>'+tag+' — '+state+'</small>'+links+'</p>'
        self.pencil_view.setHtml(body or '<p>This page has no lines.</p>')
        if getattr(self,'scroll_to_line',None):QTimer.singleShot(0,lambda n=self.scroll_to_line:self.pencil_view.scrollToAnchor('l%d'%n))   # 0.8.7 W7: the place opened
    def pencil_link(self,url):
        action,_,ident=url.toString().partition(':');mark=next((m for m in self.pencil_marks if m['id']==ident),None)
        if mark is None:return
        if action=='rubout':self.call('library.rubout',{'id':ident,'expected_revision':mark['revision']},lambda value:self.load_pencil())
        elif action=='undo':self.call('library.rubout',{'id':ident,'expected_revision':mark['revision'],'undo':True},lambda value:self.load_pencil())
        elif action=='keep':self.keep_mark(mark)
    def keep_mark(self,mark):
        quantities=(mark.get('reading') or {}).get('quantities') or []
        doors=(['As a reviewed reference fact'] if quantities and (mark.get('reading') or {}).get('as')=='QUANTITY' else [])+(['As a pinned quote'] if mark.get('rect') else [])
        if not doors:self.pencil_line.setText('This mark has no door to keep it through yet: it is not a number with a unit from the units table, and the page has no region for a pinned quote.');return
        door=doors[0]
        if len(doors)>1:
            chosen=self.dialog('Keep this mark',[('door','Keep it',doors[0])],{'door':doors})
            if chosen is None:return
            door=chosen['door']
        args={'id':mark['id'],'expected_revision':mark['revision']}
        if door=='As a pinned quote':
            values=self.dialog('Keep as a pinned quote',[('label','Label','' if mark.get('model_label') else mark['label_shown'][:80])])
            if values is None:return
            args.update(door='QUOTE',**({'label':values['label']} if values['label'] else {}))
        else:
            first=quantities[0]
            values=self.dialog('Keep as a reviewed reference fact',[('subject','Subject',self.subject.text()),('property','Property','' if mark.get('model_label') else mark['label_shown'][:120]),('value','Exact decimal',first['value']),('unit','Unit',first['unit']),('variant','Exact variant',self.variant.text()),('conditions','Conditions JSON','{}'),('role','Evidence role',''),('polarity','Support',''),('reason','Review reason','')],{'role':['SOURCE_CLAIM','REQUIREMENT','HYPOTHESIS'],'polarity':['SUPPORT','REFUTE']})
            if values is None:return
            try:values['conditions']=json.loads(values['conditions'])
            except ValueError:self.note.setText('Conditions must be valid JSON.');return
            args.update(door='FACT',**values)
        self.call('library.keep',args,lambda value:(self.pencil_line.setText(value['said']),self.load_pencil(),self.refresh_status()))
    # ---- 0.8.7 W7 (the window wiring): Ask the Library, Read this table, the page's cross-references, a place opened -------
    def room_for(self,upper):
        """Most of the room to the upper pages (an answer of the Library) or to the page below (a page, its table, its wires); on
        a short window all of it, the other half folded away behind the splitter's handle (drag it to bring it back)."""
        total=sum(self.split.sizes()) or 600;short=total<520
        if upper:self.split.setSizes([total,0] if short else [total*3//4,total-total*3//4])
        else:self.split.setSizes([0,total] if short else [total//3,total-total//3])
    def ask_library(self):
        query=self.library_query.text().strip()
        if not query or not self.ns():return
        from . import library_qt
        nsid=self.ns();self.library_asking+=1;asking=self.library_asking;self.pages.setCurrentWidget(self.library_tab);self.room_for(True)
        self.library_view.setHtml('<p>'+esc(library_qt.say('asking',query=query))+'</p>')
        def done(value):
            if asking!=self.library_asking or self.ns()!=nsid:return
            self.library_found=value;self.library_view.setHtml(library_qt.answer_html(value))
        def failed(error):self.library_view.setHtml('<p>'+esc(library_qt.say('could_not',why=str((error or {}).get('message',''))[:200]))+'</p>')
        self.call('library.ask',{'namespace':nsid,'query':query[:300]},done,failed)
    def library_link(self,url):
        action,_,n=url.toString().partition(':')
        places=list(((self.library_found or {}).get('places') or {}).get('places') or [])
        if action=='place' and n.isdigit() and int(n)<len(places):self.open_place(places[int(n)])
    def open_place(self,place):
        """A place of the Library opened here: its library chosen, its page resolved and drawn (in pencil, with its wires)."""
        nsid=place.get('namespace')
        if not nsid:return
        self.hits.blockSignals(True);self.hits.clearSelection();self.hits.setCurrentItem(None);self.hits.blockSignals(False)   # the list no longer names what is shown
        self.room_for(False)
        if self.ns()==nsid:self.resolve({'id':place['segment'],'item':place['item']});self.scroll_to_line=place.get('first');self.detail.setCurrentWidget(self.pencil_tab);return
        self.pending_place=place;self.wanted_namespace=nsid;index=self.namespaces.findData(nsid)
        if index>=0:self.namespaces.setCurrentIndex(index)
    def read_table(self):
        if not self.citation or not self.ns():return
        from . import library_qt
        nsid=self.ns();ident=self.citation['id'];self.table_button.setEnabled(False);self.table_view.setHtml('<p>'+esc(library_qt.say('reading_table'))+'</p>');self.detail.setCurrentWidget(self.table_view);self.room_for(False)
        def done(value):
            self.table_button.setEnabled(True)
            if self.ns()!=nsid or not self.citation or self.citation['id']!=ident:return
            self.table_view.setHtml(library_qt.table_html(value))
        def failed(error):self.table_button.setEnabled(True);self.table_view.setHtml('<p>'+esc(library_qt.say('could_not',why=str((error or {}).get('message',''))[:200]))+'</p>')
        self.call('library.table',{'namespace':nsid,'id':ident,'item':self.citation['item']},done,failed)
    def load_links(self):
        if not self.citation or not self.ns():return
        key=(self.ns(),self.citation['item'])
        if key in self.page_links:self.draw_pencil();return
        def loaded(value):
            self.page_links[key]=value
            if self.citation and (self.ns(),self.citation['item'])==key:self.draw_pencil()
        self.call('library.links',{'namespace':key[0],'item':key[1]},loaded)
    def launch(self,op,args):
        if self.job:self.note.setText('Finish or cancel the current reference job first.');return
        nsid=self.ns();self.call(op,args,lambda job:self.watch(job,nsid))
    def watch(self,job,nsid):self.job=job['id'];self.job_tool=job['tool'];self.job_namespace=nsid;self.note.setText(job['tool']+' · working through the shared Kernel')
    def index(self):
        if self.ns():self.launch('references.index',{'namespace':self.ns()})
    def cancel(self):
        if self.job:self.call('jobs.cancel',{'id':self.job},lambda value:self.note.setText('Cancellation requested. Existing committed index remains usable.'))
    def poll(self):
        if not self.job or self.stopping:return
        response=self.kernel.dispatch('jobs.get',{'id':self.job},self.principal)
        if not response['ok'] or response['result']['state'] not in ('Completed','Failed','Cancelled','Interrupted'):return
        job=response['result'];ident=self.job;tool=self.job_tool;self.job=None
        if tool=='references.export' and job['state']=='Completed':
            self.call('references.volume.publish',{'job':ident},
                lambda value:self.note.setText('Collection exported · '+value['path']))
            return
        if self.job_namespace!=self.ns():self.note.setText('Job finished for the previously selected library. Its result remains in Jobs.');return
        if tool=='brain.respond':
            result=local_brain.result(self.kernel,ident,self.principal);answer=result.get('result') or {}
            if job['state']=='Completed':
                body='<p>'+esc(answer['text'].partition('\n\nSources:\n')[0]).replace('\n','<br>')+'</p>'
                for row in answer.get('references',[]):body+='<p><a href="reference:'+row['id']+'">'+esc(row['name']+' · '+row['label'])+'</a></p>'
                self.answer.setHtml(body+'<p><small>Source IDs checked; interpretation requires review.</small></p>');self.note.setText('Local answer ready · source locations checked')
            else:self.answer.setPlainText(answer.get('reason') or result.get('error') or job['state']);self.note.setText('Local answer unavailable · '+job['state'])
        elif tool=='references.render':
            nsid=self.ns();self.call('references.render.result',{'job':ident},lambda value:self.rendered(value) if self.ns()==nsid else None)
        else:
            path=self.host.root/'build/references/runs'/ident/'result.json'
            result=json.loads(path.read_text()) if path.is_file() else {'status':job['state']}
            self.proof.setPlainText(json.dumps(result,indent=2));self.note.setText(tool+' · '+job['state']+' · '+result.get('reason',result.get('status','')));self.refresh()
    def remember(self):
        if self.citation:
            namespace=self.ns();citation=dict(self.citation);tab=self.host.ledger_bridge.show_memory();tab.bind_reference(namespace,citation)

    def original(self):
        if not self.citation:return
        if self.citation['locator']['kind']=='pdf_page':
            from .pdf_qt import open_pdf
            return open_pdf(self.host,self.ns(),self.citation['item'],self.citation['source_sha256'],self.citation['locator']['page_index'])
        self.detail.setCurrentWidget(self.excerpt);self.note.setText(self.citation['name']+' · '+self.citation['label']+' · original bytes and this location were checked')
    def read_pdf(self):
        if not self.ns() or not self.sources.currentData():return
        from .pdf_qt import open_pdf
        return open_pdf(self.host,self.ns(),self.sources.currentData())
    def rendered(self,value):
        result=value.get('result') or {}
        if value['state']!='Completed' or result.get('status')!='RENDERED':self.note.setText(result.get('reason') or result.get('status') or value['state']);return
        if not self.citation or result['citation']!=self.citation['id']:self.note.setText('The previous page render finished. Select its reference to render it again.');return
        path=self.kernel.safe(result['image'])
        if records.sha(path)!=result['image_sha256']:self.note.setText('Rendered page changed; render it again.');return
        pixmap=page_light.lit(QPixmap(str(path)),page_light.own(self.host));self.image_label.setPixmap(pixmap.scaledToWidth(max(300,self.image_scroll.viewport().width()-20),Qt.SmoothTransformation));self.detail.setCurrentWidget(self.image_scroll);self.note.setText('Original PDF page '+str(result['page_index']+1)+' · render derived from the verified original')
    def atlas(self):
        if not self.ns() or not self.subject.text().strip():return
        self.call('references.atlas',{'namespace':self.ns(),'subject':self.subject.text().strip()},self.atlas_loaded)
    def atlas_loaded(self,value):
        body='<h3>'+esc(value['subject'])+' · evidence atlas</h3><p>Native project: '+esc(value['native_project']['state'])+'<br>Physical qualification: '+esc(value['physical_qualification'])+'</p>'
        for fact in value['facts']:
            quantity=fact.get('quantity',{});body+='<p><b>'+esc(fact['property'])+'</b> '+esc(quantity.get('value','unavailable'))+' '+esc(quantity.get('unit',''))+' · '+esc(fact['variant'])+'<br>'+esc(fact['applicability'])+' · '+esc(fact['role'])+'</p>'
        for link in value['links']:body+='<p>'+esc(link['relation'])+' · '+esc(link['basis'])+' · '+esc(link['applicability'])+'<br>Verified connectivity: false</p>'
        for gap in value['native_project'].get('gaps',[]):body+='<p>'+esc(gap.replace('_',' '))+'</p>'
        self.atlas_view.setHtml(body);self.proof.setPlainText(json.dumps(value,indent=2,ensure_ascii=False))
    def impact(self):
        if not self.ns() or not self.citation:return
        self.call('references.impact',{'namespace':self.ns(),'item':self.citation['item']},lambda value:(self.atlas_view.setPlainText(json.dumps(value,indent=2)),self.proof.setPlainText(json.dumps(value,indent=2))))
    def question_records(self):
        if not self.ns():return
        try:conditions=json.loads(self.conditions.text())
        except ValueError:self.note.setText('Conditions must be a JSON object.');return
        args={'namespace':self.ns(),'subject':self.subject.text().strip(),'property':self.property_field.text().strip(),'variant':self.variant.text().strip(),'conditions':conditions}
        self.call('references.question',args,lambda value:(self.atlas_view.setPlainText(json.dumps(value,indent=2,ensure_ascii=False)),self.proof.setPlainText(json.dumps(value,indent=2,ensure_ascii=False))))
    def dialog(self,title,fields,combos=None):
        dialog=QDialog(self);dialog.setWindowTitle(title);box=QVBoxLayout(dialog);form=QFormLayout();widgets={}
        for key,label,default in fields:
            if combos and key in combos:
                widget=QComboBox();widget.addItems(combos[key])
            else:widget=QLineEdit(default)
            widget.setAccessibleName(label);widgets[key]=widget;form.addRow(label,widget)
        box.addLayout(form);buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);box.addWidget(buttons)
        if dialog.exec()!=QDialog.Accepted:return None
        return {key:widget.currentText() if isinstance(widget,QComboBox) else widget.text().strip() for key,widget in widgets.items()}
    def fact(self):
        if not self.citation:return
        values=self.dialog('Review source fact',[('subject','Subject',self.subject.text()),('property','Property',self.property_field.text()),('value','Exact decimal',''),('unit','Unit','us'),('variant','Exact variant',self.variant.text()),('conditions','Conditions JSON',self.conditions.text()),('role','Evidence role',''),('polarity','Support',''),('quote','Exact source quote',self.citation['text'][:1800]),('reason','Review reason','')],{'role':['REQUIREMENT','SOURCE_CLAIM','HYPOTHESIS'],'polarity':['SUPPORT','REFUTE']})
        if values is None:return
        try:values['conditions']=json.loads(values['conditions'])
        except ValueError:self.note.setText('Conditions must be valid JSON.');return
        self.call('references.fact.add',{'namespace':self.ns(),'id':self.citation['id'],**values},lambda value:(self.note.setText('Source fact reviewed; fitted-part and physical qualification remain separate.'),self.refresh_status()))
    def link(self):
        if not self.citation:return
        values=self.dialog('Link this reference',[('subject','Subject',self.subject.text()),('relation','Relationship',''),('basis','Basis',''),('job','Completed job ID (if used)',''),('reason','Reason','')],{'relation':['CITES','REQUIREMENT_FOR','RELATED_SOURCE','JOB_RESULT_FOR'],'basis':['OWNER_DECLARED','INFERRED']})
        if values is None:return
        if not values['job']:values.pop('job')
        self.call('references.link.add',{'namespace':self.ns(),'id':self.citation['id'],**values},lambda value:(self.note.setText('Relationship recorded with its declared basis.'),self.refresh_status()))
    def compile(self):
        selected=list(dict.fromkeys(row.data(0,Qt.UserRole)['id'] for row in self.hits.selectedItems()))
        if not selected or not self.ns():self.note.setText('Select up to eight passages on the References tab first.');return
        args={'namespace':self.ns(),'passages':selected,'question':self.question.text().strip()}
        if self.subject.text().strip():args['subject']=self.subject.text().strip()
        self.call('references.packet.create',args,self.compiled)
    def compiled(self,value):
        self.packet=value;self.proof.setPlainText(json.dumps(value,indent=2,ensure_ascii=False));self.answer.setPlainText('Local reference packet ready. '+str(len(value['passages']))+' checked passages.\nNo cloud disclosure granted.');self.pages.setCurrentIndex(2);self.note.setText('Reference packet '+value['id'][:12]+' · CURRENT')
    def ask(self):
        if not self.packet:self.note.setText('Compile a reference packet first.');return
        self.launch('brain.ask',{'message':self.question.text().strip() or 'Summarize the supplied reference briefly and cite it.','reference_packet':self.packet['id']})
    def follow_citation(self,url):
        value=url.toString()
        if value.startswith('reference:'):
            ident=value.removeprefix('reference:');source=next((v for v in (self.packet or {}).get('passages',[]) if v['id']==ident),None)
            self.resolve({'id':ident,**({'item':source['item']} if source else {})});self.detail.setCurrentWidget(self.excerpt)
    def export(self):
        if not self.ns():return
        nsid=self.ns()
        def ready(value):
            if self.ns()!=nsid:return
            self.generation=value['generation'];self.update_inspector()
            from .files_service import root as files_root
            start=files_root(self.kernel,create=True)/'Egress'/'Reference_Collection.zip'
            path,_=QFileDialog.getSaveFileName(self,'Export a dated reference collection',str(start),'ZIP archive (*.zip)')
            if path:
                args={'namespace':nsid,'destination':path,'expected_generation':value['generation'],'readable':True}
                if self.project_collection and self.project_collection[0]==nsid:
                    args['project']=self.project_collection[1]
                self.launch('references.volume.export',args)
        self.call('references.status',{'namespace':nsid},ready)
    def verify(self):
        path,_=QFileDialog.getOpenFileName(self,'Verify a reference volume','','ZIP archive (*.zip)')
        if path:self.launch('references.volume.verify',{'path':path})
    def shutdown_engineering(self):self.timer.stop();super().shutdown_engineering()
