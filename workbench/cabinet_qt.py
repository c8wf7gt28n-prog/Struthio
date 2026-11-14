"""Logical cabinet projection and an identity-preserving central record room."""
from .text_prompts import writing_prompt
import json
from PySide6.QtCore import Qt,QTimer,QSignalBlocker
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QTreeWidget,
    QTreeWidgetItem,QStackedWidget,QPlainTextEdit,QScrollArea)
from . import cabinet
from .engineering_kernel import operator,CAPABILITIES
from .settings_qt import action,STYLE,INK
from .boss_theme import recolour


def plain(text=''):
    label=QLabel(text);label.setTextFormat(Qt.PlainText);label.setWordWrap(True)
    label.setMinimumWidth(0);return label


class CabinetRecordTab(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.current=None;self.data=None;self.loading=False
        self.setProperty('ledgerRoom',True);self.setProperty('paperFunctionalInk',True)
        # Selection is eraser pink (#593a29): the theme's AMBER_SOFT equals the passage's AMBER, so a selection was invisible (V-02).
        self.setObjectName('CabinetRecord');self.setStyleSheet(STYLE+recolour('''
        QLineEdit#CabinetWriting,QPlainTextEdit#CabinetWriting {background:#493225;color:#eee9dd;border:0;padding:8px;border-radius:0;selection-background-color:#593a29;selection-color:#eee9dd;}
        QLineEdit#CabinetWriting:focus,QPlainTextEdit#CabinetWriting:focus {border-bottom:2px solid #eee9dd;}
        QPlainTextEdit#CabinetRead {background:transparent;color:#eee9dd;border:0;selection-background-color:#593a29;selection-color:#eee9dd;}
        '''))
        if not hasattr(host.ledger_bridge,'cabinet_drafts'):host.ledger_bridge.cabinet_drafts={}
        self.drafts=host.ledger_bridge.cabinet_drafts
        outer=QVBoxLayout(self);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.NoFrame);outer.addWidget(scroll)
        self.scroll=scroll
        page=QWidget();scroll.setWidget(page);box=QVBoxLayout(page);box.setContentsMargins(22,18,22,18);box.setSpacing(12)
        self.breadcrumb=plain('CABINET');filing=QHBoxLayout();filing.addWidget(self.breadcrumb,1)
        self.reveal_button=action('Show in cabinet',self.reveal);filing.addWidget(self.reveal_button);box.addLayout(filing)
        self.heading=plain();self.heading.setProperty('arcReadingRole','heading');box.addWidget(self.heading)
        self.meta=plain();self.meta.setTextInteractionFlags(Qt.TextSelectableByMouse);box.addWidget(self.meta)
        self.body=QPlainTextEdit();self.body.setObjectName('CabinetRead');self.body.setReadOnly(True);self.body.setAccessibleName('Current saved record')
        self.body.setProperty('arcReadingRole','prose')  # the saved words are prose (V-03); the JSON viewers below stay in the code font
        self.body.setMinimumHeight(130);self.body.setMaximumHeight(300);box.addWidget(self.body)
        self.children=plain();box.addWidget(self.children)
        from .cabinet_actions_qt import ActionShelf
        self.action_shelf=ActionShelf(host,lambda text:self.note.setText(text));box.addWidget(self.action_shelf)
        from .memory_cabinet_qt import DirectionEditor
        self.direction_editor=DirectionEditor(self);box.addWidget(self.direction_editor)
        self.form_label=plain();box.addWidget(self.form_label)
        self.new_title=QLineEdit();self.new_title.setObjectName('CabinetWriting');self.new_title.setAccessibleName('New project title');self.new_title.setMaxLength(200);writing_prompt(self.new_title, 'Project title');box.addWidget(self.new_title)
        self.writing=QPlainTextEdit();self.writing.setObjectName('CabinetWriting');self.writing.setAccessibleName('Words to keep');writing_prompt(self.writing, 'Write an idea or project intent.');self.writing.setMaximumHeight(140);box.addWidget(self.writing)
        self.writing.setProperty('arcReadingRole','prose')  # written by the owner: prose font and size, not code (V-03)
        from .writing_marker import attach
        attach(host,self.new_title);attach(host,self.writing)  # the two cabinet writing passages opt into the margin marker (VS03)
        self.keep=action('Keep idea',self.save_words);box.addWidget(self.keep,0,Qt.AlignLeft)
        self.new_title.textChanged.connect(self.save_draft);self.writing.textChanged.connect(self.save_draft)
        row=QHBoxLayout();row.addWidget(action('Refresh saved record',lambda:self.open(self.current) if self.current else None))
        row.addWidget(action('Detail',lambda:self.detail.setVisible(not self.detail.isVisible())))
        row.addWidget(action('Explore this work',lambda:__import__('workbench.explore_qt',fromlist=['show']).show(self.host,self.current)))
        row.addStretch();box.addLayout(row)
        self.read_actions=QHBoxLayout();box.addLayout(self.read_actions)
        self.note=plain('Record views read the original identity. Keep saves new writing through the shared commands.');box.addWidget(self.note)
        self.result=QPlainTextEdit();self.result.setObjectName('CabinetRead');self.result.setReadOnly(True);self.result.setMaximumHeight(230);self.result.hide();box.addWidget(self.result)
        self.detail=QPlainTextEdit();self.detail.setObjectName('CabinetRead');self.detail.setReadOnly(True);self.detail.setMaximumHeight(300);self.detail.hide();box.addWidget(self.detail)
        box.addStretch()

    def title(self):return 'Cabinet record'

    def call(self,operation,args):
        response=self.host.ledger_bridge.kernel.dispatch(operation,args,operator())
        if not response['ok']:self.note.setText(response['error']['message']);return None
        return response['result']

    def save_draft(self,*_):
        if self.loading or not self.current:return
        if self.direction_editor.active:
            self.direction_editor.save_draft();return
        text=self.writing.toPlainText();title=self.new_title.text()
        if text or title:self.drafts[self.current]={'text':text,'title':title}
        else:self.drafts.pop(self.current,None)

    def open(self,ident):
        self.save_draft();value=self.call('ledger.cabinet.get',{'id':ident})
        if value is None:return False
        self.loading=True;self.current=ident;self.data=value;node=value['node'];record=value['record'] or {}
        self.setProperty('cabinet_node',ident)
        self.setProperty('concern_context',node['target']['id'] if node.get('target') and node['target']['kind']=='catalog' else None)
        self.heading.setText(node['label']);self.breadcrumb.setText('CABINET / '+node['role'].replace('_',' ').upper())
        words={'owner_private':'Your saved work','connected_profile':'Concern catalogue','mixed':'Shared filing views'}
        self.meta.setText(words.get(node['scope'],node['scope'])+(' · revision '+str(node['revision']) if node.get('revision') is not None else '')+
                          (' · Reference to '+node['canonical_id'] if node['role']=='reference' else ''))
        kind=record.get('kind') if node['provider']=='project_desk' else None
        if node['provider']=='slate_memory' and 'display_text' in record:text=record['display_text']
        elif kind=='project':text=record['original_intent']
        elif kind=='idea':text=record['text']
        elif kind=='document':text='\n'.join(b['text'] for b in record.get('blocks',[]))[:20000] or '(an empty page)'  # the saved page, as words
        elif kind=='assignment':text=record['original_request']+'\n\n'+record.get('interpretation','')
        elif kind=='discovery_inquiry':text=record['document']['goal']['question']+'\n\n'+node['description']
        elif kind=='project_reference':text=record.get('text') or 'Saved target: '+str((record.get('source') or {}).get('address'))+'\n\n'+node['description']
        elif node['role']=='working_copy':text='Working copy of '+record['source']+'\n\nStored state: '+record['state']+'\nContent and original freshness have not been rechecked.'
        elif node['role']=='investigation':text=record['question']+'\n\n'+record.get('objective','')
        else:text=(record.get('note') or {}).get('body') or record.get('summary') or record.get('description') or node.get('description','')
        self.body.setPlainText(text)
        self.children.setText(('Filed here: '+', '.join(r['label'] for r in value['children'][:12])) if value['children'] else '')
        self.form_mode=('project' if ident in ('cabinet:projects','catalog:projects') else
                        'idea' if node['role']=='project' or ident in ('cabinet:unassigned','cabinet:concern') else None)
        self.new_title.setVisible(self.form_mode=='project')
        for widget in (self.form_label,self.writing,self.keep):widget.setVisible(self.form_mode is not None)
        self.form_label.setText('Write the new project’s intent.' if self.form_mode=='project' else 'Write an idea to keep here.')
        self.keep.setText('Create project' if self.form_mode=='project' else 'Keep idea')
        draft=self.drafts.get(ident,{})
        self.new_title.setText(draft.get('title',''));self.writing.setPlainText(draft.get('text',''))
        self.direction_editor.bind(ident,record)
        while self.read_actions.count():
            item=self.read_actions.takeAt(0)
            if item.widget():item.widget().deleteLater()
        self.available_actions=[]
        for spec in value['actions']:
            if CAPABILITIES.get(spec['operation'])!='read':continue
            button=action(spec['label'],lambda checked=False,spec=spec:self.read_action(spec))
            self.read_actions.addWidget(button);self.available_actions.append(button)
        self.read_actions.addStretch()
        self.detail.setPlainText(json.dumps(value,indent=2,ensure_ascii=False)[:100000]);self.result.hide()
        self.loading=False;self.note.setText('Saved record · draft writing stays in this desktop until you Keep it.')
        self.action_shelf.bind(ident)
        navigation=getattr(self.host,'navigation_controller',None)
        if navigation:navigation.changed(self)
        return True

    def reveal(self):
        navigation=getattr(self.host,'navigation_controller',None)
        if navigation and self.current:
            navigation.reveal_record(self.current,refresh=True);navigation.changed(self)

    def read_action(self,spec):
        if CAPABILITIES.get(spec['operation'])!='read':return
        value=self.call(spec['operation'],spec['arguments'])
        if value is None:return
        self.result.setPlainText(json.dumps(value,indent=2,ensure_ascii=False)[:100000]);self.result.show()
        self.note.setText(spec['label']+' · '+str(value.get('state','Read complete')))

    def save_words(self):
        operation='projects.create' if self.form_mode=='project' else 'ideas.capture'
        if self.form_mode=='project':
            result=self.call('projects.create',{'title':self.new_title.text(),'intent':self.writing.toPlainText()})
            destination='project:'+result['id'] if result else None
        else:
            args={'text':self.writing.toPlainText()}
            if self.data['node']['role']=='project':args['project']=self.data['node']['target']['id']
            result=self.call('ideas.capture',args);destination='idea:'+result['id'] if result else None
        if result is None:return
        self.drafts.pop(self.current,None);self.loading=True;self.new_title.clear();self.writing.clear();self.loading=False
        self.host.cabinet_page.refresh(force=True)
        self.host.cabinet_page.select(destination,reveal=True);self.open(destination)
        self.note.setText('Project created.' if operation=='projects.create' else 'Idea kept.')


class CabinetPage(QWidget):
    def __init__(self,host,footer_line=None):
        super().__init__();self.host=host;self.footer_line=footer_line;self.model=None;self.items={};self.loading=False
        self.saved=host.session.state.get('cabinet_navigation',{});self.using_legacy=False
        self.setProperty('paperFunctionalInk',True)
        self.setStyleSheet(STYLE+recolour('''QLineEdit#CabinetQuery {background:#493225;color:#eee9dd;border:0;padding:7px;selection-background-color:#593a29;selection-color:#eee9dd;}
        QTreeWidget#LogicalCabinet {background:transparent;color:#eee9dd;border:0;}
        QTreeWidget#LogicalCabinet::item {padding:5px 2px;}
        QTreeWidget#LogicalCabinet::item:selected {background:#493225;color:#eee9dd;}'''))
        box=QVBoxLayout(self);box.setContentsMargins(8,6,8,0);box.setSpacing(8)
        row=QHBoxLayout();self.logical=action('Logical cabinet',lambda:self.set_legacy(False));self.legacy=action('Existing views',lambda:self.set_legacy(True))
        from .settings_qt import ACTION_STYLE
        for button in (self.logical,self.legacy):
            # Three px of side padding instead of four minus the underline's shortfall: the last letter is no longer cut (V-15).
            button.setCheckable(True);button.setStyleSheet(ACTION_STYLE+'QPushButton {padding:6px 7px;}');row.addWidget(button)
        from .finder_qt import keep_bold_room;keep_bold_room(self.logical,self.legacy)  # a checked word is drawn bold: keep its room (G-B)
        row.addStretch();box.addLayout(row)
        self.stack=QStackedWidget();box.addWidget(self.stack,1)
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(0,0,0,0);layout.setSpacing(7)
        self.query=QLineEdit();self.query.setObjectName('CabinetQuery');self.query.setAccessibleName('Find cabinet records');writing_prompt(self.query, 'Find work…');layout.addWidget(self.query)
        from .pane_qt import BranchTree
        self.tree=BranchTree();self.tree.setObjectName('LogicalCabinet');self.tree.setHeaderHidden(True)  # D1b: the desk's tree (rows, indent, branch lines)
        self.tree.setAccessibleName('Logical filing cabinet');layout.addWidget(self.tree,1)
        self.status=plain('Reading saved work…');layout.addWidget(self.status)
        self.refresh_button=action('Refresh cabinet',lambda:self.refresh(force=True));layout.addWidget(self.refresh_button,0,Qt.AlignLeft)
        self.stack.addWidget(page);self.stack.addWidget(host.nav)
        # Directional actions stay outside the filing tree, above fixed Trash. HATCH DESK D1b: the pane shows only its tabs, the
        # tree and Trash; these words stay (out of sight) for callers, and Import and Export are Work menu entries.
        transfers=QHBoxLayout();self.transfer_buttons=[]
        for transfer in cabinet.TRANSFERS:
            button=action(transfer['label'],lambda checked=False,t=transfer:self.transfer(t))
            button.setToolTip(transfer['description']);button.setAccessibleName(transfer['label']+' transfer controls');transfers.addWidget(button);self.transfer_buttons.append(button)
        transfers.addStretch();box.addLayout(transfers)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu);self.tree.customContextMenuRequested.connect(self.context_menu)
        self.tree.itemClicked.connect(self.clicked);self.tree.itemActivated.connect(self.clicked)
        self.tree.itemExpanded.connect(self.remember);self.tree.itemCollapsed.connect(self.remember)
        self.tree.verticalScrollBar().sliderReleased.connect(self.remember);self.query.textChanged.connect(self.filtered)
        self.timer=QTimer(self);self.timer.setInterval(2500);self.timer.timeout.connect(self.refresh);self.timer.start()
        self.set_legacy(bool(self.saved.get('legacy')),persist=False)
        QTimer.singleShot(0,lambda:self.refresh(force=True))

    def set_legacy(self,on,persist=True):
        self.using_legacy=bool(on);self.stack.setCurrentIndex(int(on));self.logical.setChecked(not on);self.legacy.setChecked(on)
        if self.footer_line:self.footer_line.setVisible(on and self.isVisible())
        if not on:self.refresh(force=True)
        if persist:self.remember()

    def transfer(self,transfer):
        from .shell2 import open_destination
        return open_destination(self.host,transfer['destination'])

    def refresh(self,force=False):
        if self.host._closing or (not force and (not self.isVisible() or self.using_legacy)):return
        response=self.host.ledger_bridge.kernel.dispatch('ledger.cabinet',{},operator())
        if not response['ok']:self.status.setText(response['error']['message']);return
        model=response['result']
        if not force and self.model and self.model['signature']==model['signature']:return
        current=self.tree.currentItem();selected=(current.data(0,Qt.UserRole)['id'] if current else self.saved.get('selected'))
        expanded=([ident for ident,item in self.items.items() if item.isExpanded()] if self.model and not self.query.text() else
                  self.saved.get('expanded',['cabinet:concern','catalog:projects','cabinet:projects','cabinet:unassigned']))
        scroll=self.tree.verticalScrollBar().value() if self.model else self.saved.get('scroll',0)
        self.loading=True;self.model=model;self.tree.clear();self.items={}
        with QSignalBlocker(self.tree):
            for node in model['nodes']:
                item=QTreeWidgetItem([node['label']]);item.setData(0,Qt.UserRole,node);self.items[node['id']]=item
                item.setToolTip(0,node.get('description','')+'\n'+node['canonical_id'])
                if node['target']:item.setForeground(0,QColor(INK))
                if node['parent']:self.items[node['parent']].addChild(item)
                else:self.tree.addTopLevelItem(item)
                if node['id'] in expanded:item.setExpanded(True)
            if selected in self.items:self.tree.setCurrentItem(self.items[selected])
        self.loading=False;self.filtered(self.query.text());self.tree.verticalScrollBar().setValue(scroll)
        self.status.setText(('Some records are outside this bounded view. Existing views and workspace search remain available.' if model['partial'] else
                             str(sum(r['owning'] for r in model['nodes']))+' saved records · '+model['sort_policy']+' order')+
                            ('\n'+' '.join(model['notices']) if model['notices'] else ''))
        self.tell_status()
        if getattr(self.host,'trash_can',None) is not None:
            count=self.host.ledger_bridge.kernel.dispatch('files.trash_list',{},operator())
            if count['ok']:self.host.trash_can.set_count(len(count['result']['trash']))

    def tell_status(self):
        """HATCH DESK D1b: the status line is out of the pane; its words are the Cabinet tab's tooltip."""
        tab=getattr(getattr(self.host,'settings_navigator',None),'cabinet',None)
        if tab is not None:tab.setToolTip('Cabinet · '+self.status.text())

    def select(self,ident,reveal=False):
        item=self.items.get(ident)
        if item is None:return
        with QSignalBlocker(self.tree):
            if reveal:
                from .navigation_qt import hidden
                if hidden(item):self.query.clear()
                parent=item.parent()
                while parent:parent.setExpanded(True);parent=parent.parent()
            self.tree.setCurrentItem(item)
            if reveal:self.tree.scrollToItem(item)
        self.remember()

    def clicked(self,item,column=0):
        node=item.data(0,Qt.UserRole);self.remember()
        # UI-04: a project node that names a folder on disk tells the Finder (while Home is active) before its record opens.
        finder=getattr(self.host,'finder',None)
        if finder is not None and node.get('role')=='project':
            target=node.get('target') if isinstance(node.get('target'),dict) else {}
            place=node.get('folder') or target.get('path') or target.get('folder')
            if isinstance(place,str) and place.startswith('/'):finder.show_place(place)
        self.open(node['id'])

    def open(self,ident):
        bridge=self.host.ledger_bridge
        room=bridge.add_tab(CabinetRecordTab,lambda:CabinetRecordTab(self.host))
        return room if room.open(ident) else None

    def context_menu(self,point):
        """HATCH DESK D4: the right-click menu (workbench/context_menu.py) for the record under the pointer, or for the cabinet tree
        itself on its empty place: the cabinet's own checked actions (cabinet_actions_qt, as this menu held them), the record's staC,
        and the tree's Refresh, View as, New Idea, New Project, Import and Export."""
        from .context_menu import open_at
        try:return open_at(self.host,self.tree.viewport(),point)
        except (ValueError,OSError) as exc:self.status.setText(str(exc))

    def remember(self,*_):
        if self.loading:return
        current=self.tree.currentItem();node=current.data(0,Qt.UserRole) if current else {}
        data=dict(selected=node.get('id',self.saved.get('selected','cabinet:concern')),legacy=self.using_legacy,
                  expanded=self.saved.get('expanded',[]) if self.query.text() else [ident for ident,item in self.items.items() if item.isExpanded()],
                  scroll=self.tree.verticalScrollBar().value())
        self.saved=data;self.host.ledger_bridge.sync_profile();self.host.session.state['cabinet_navigation']=data;self.host.session.save()

    def filtered(self,text):
        query=text.strip().casefold()
        def visit(item,inherited=False):
            node=item.data(0,Qt.UserRole);match=inherited or not query or query in (node['label']+' '+node['role']).casefold()
            children=[visit(item.child(i),match) for i in range(item.childCount())]
            show=match or any(children);item.setHidden(not show)
            if query and children and show:item.setExpanded(True)
            return show
        with QSignalBlocker(self.tree):
            for index in range(self.tree.topLevelItemCount()):visit(self.tree.topLevelItem(index))
            if not query and self.saved.get('expanded') is not None:
                for ident,item in self.items.items():item.setExpanded(ident in self.saved['expanded'])
