"""Left-column registry and a shared, draft-preserving settings editor."""
from .text_prompts import writing_prompt
import copy
import json
import time
from PySide6.QtCore import Qt, QSignalBlocker, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QComboBox, QDoubleSpinBox,
    QStackedWidget, QPlainTextEdit, QHeaderView, QScrollArea)
from . import ledger_control, settings_registry
from .engineering_kernel import operator

INK='#eee9dd'
ACTION_STYLE="""QPushButton {background:transparent;color:#eee9dd;border:0;border-radius:0;padding:6px 7px;text-decoration:underline;}
QPushButton:focus {border-bottom:2px solid #eee9dd;}
QPushButton:disabled {color:#b0bcb9;text-decoration:none;}"""
# DESKTOP-01: the current left-column view is said by weight and a pink rule, not by colour alone (the words stay pink actions).
CHECKED_RULE="""
QPushButton[settingsAction="true"]:checked {font-weight:600;text-decoration:none;border-bottom:2px solid #eee9dd;}"""
# V-24: the settings filter is the same yellow writable passage as the cabinet filter (CabinetQuery), with the focus rule of every passage.
PASSAGE_STYLE="""QLineEdit#SettingsFilter {background:#493225;color:#eee9dd;border:0;border-radius:0;padding:7px;selection-background-color:#593a29;}
QLineEdit#SettingsFilter:focus {border-bottom:2px solid #eee9dd;}"""
# The left column's views in stack order. `settings_navigation.mode` persists all three since Session.NAVIGATION_MODES
# (DESKTOP-01, WI-1) accepts 'machine'; set PERSIST_MACHINE_MODE False to write 'cabinet' instead if a loader without the word must read the file.
VIEWS=('cabinet','settings','machine')
PERSIST_MACHINE_MODE=True
STYLE="""QWidget#SettingsEditor {background:#14191b;color:#eee9dd;}
QLineEdit#SettingValue,QComboBox#SettingValue,QDoubleSpinBox#SettingValue {
 background:#493225;color:#eee9dd;border:0;border-radius:0;padding:8px;min-height:30px;selection-background-color:#593a29;}
QLineEdit#SettingValue:focus,QComboBox#SettingValue:focus,QDoubleSpinBox#SettingValue:focus {border-bottom:2px solid #eee9dd;}
QComboBox#SettingValue::drop-down {border:0;background:transparent;}
QPushButton[settingsAction="true"] {background:transparent;color:#eee9dd;border:0;border-radius:0;padding:6px 7px;text-decoration:underline;}
QPushButton[settingsAction="true"]:focus {border-bottom:2px solid #eee9dd;}
QPushButton[settingsAction="true"]:disabled {color:#b0bcb9;text-decoration:none;}
QTreeWidget#SettingsHistory,QPlainTextEdit#SettingsDetail {background:transparent;color:#eee9dd;border:0;}
"""


def words(value):
    if value is None:return 'Not observed'
    return json.dumps(value,ensure_ascii=False) if not isinstance(value,str) else value


def action(label, callback):
    button=QPushButton(label);button.setProperty('settingsAction',True)
    button.setProperty('paperFunctionalInk',True)
    button.setStyleSheet(ACTION_STYLE)
    button.setCursor(Qt.PointingHandCursor);button.clicked.connect(callback)
    button.setAccessibleName(label);return button


class SettingsTab(QWidget):
    def __init__(self,bridge,category='All settings'):
        super().__init__();self.bridge=bridge;self.key=None;self.current=None;self.drafts={};self._loading=False
        self.last_change=None;self.setObjectName('SettingsEditor');self.setProperty('paperFunctionalInk',True);self.setStyleSheet(STYLE)
        self.setProperty('ledgerRoom',True)  # Configuration stays beside an edited Preview and does not consume a pin.
        if not hasattr(bridge,'settings_drafts'):bridge.settings_drafts={}
        self.drafts=bridge.settings_drafts
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0)
        scroll=self.scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.NoFrame);outer.addWidget(scroll)
        self.page=QWidget();scroll.setWidget(self.page);box=QVBoxLayout(self.page);box.setContentsMargins(24,20,24,18);box.setSpacing(14)
        self.breadcrumb=QLabel('SETTINGS');box.addWidget(self.breadcrumb)
        self.heading=QLabel();self.heading.setProperty('arcReadingRole','heading');self.heading.setWordWrap(True);box.addWidget(self.heading)
        self.key_label=QLabel();self.key_label.setWordWrap(True);self.key_label.setTextInteractionFlags(Qt.TextSelectableByMouse);box.addWidget(self.key_label)
        self.description=QLabel();self.description.setWordWrap(True);box.addWidget(self.description)
        self.state=QLabel();self.state.setWordWrap(True);self.state.setTextInteractionFlags(Qt.TextSelectableByMouse);box.addWidget(self.state)
        self.draft_label=QLabel('Write the value in the highlighted passage.');self.draft_label.setWordWrap(True);box.addWidget(self.draft_label)
        self.editors=QStackedWidget();self.string=QLineEdit();self.choice=QComboBox();self.boolean=QComboBox();self.boolean.addItems(['Off','On'])
        self.number=QDoubleSpinBox();self.number.setDecimals(2);self.number.setSingleStep(.1);self.number.setButtonSymbols(QDoubleSpinBox.NoButtons)
        for widget in (self.string,self.choice,self.boolean,self.number):
            widget.setObjectName('SettingValue');widget.setAccessibleName('Setting value');self.editors.addWidget(widget)
        from .presentation_qt import FavoriteSlots
        self.favorite_slots=FavoriteSlots(bridge.host,self.edited);self.editors.addWidget(self.favorite_slots)
        from .hardware_settings_qt import ViewModes
        self.view_modes=ViewModes(bridge.host,self.edited);self.editors.addWidget(self.view_modes)
        box.addWidget(self.editors)
        writing_prompt(self.string,'Setting value')
        self.string.textChanged.connect(self.edited);self.choice.currentTextChanged.connect(self.edited)
        self.boolean.currentIndexChanged.connect(self.edited);self.number.valueChanged.connect(self.edited)
        row=QHBoxLayout();self.apply_button=action('Apply',self.save);self.reset_button=action('Default',lambda:self.save(default=True))
        self.detail_button=action('Detail',self.toggle_detail);self.reload_button=action('Reload saved value',self.reload_latest)
        for button in (self.apply_button,self.reset_button,self.detail_button,self.reload_button):row.addWidget(button)
        row.addStretch();box.addLayout(row)
        self.note=QLabel('Edits use the existing stores and shared command history.');self.note.setWordWrap(True);self.note.setAccessibleName('Settings result');box.addWidget(self.note)
        self.detail=QPlainTextEdit();self.detail.setObjectName('SettingsDetail');self.detail.setReadOnly(True)
        self.detail.setAccessibleName('Setting definition and consumer receipts');self.detail.setMaximumHeight(250);self.detail.hide();box.addWidget(self.detail)
        from .model_settings_qt import ModelPanel
        self.model_panel=ModelPanel(bridge,self.note.setText);self.model_panel.hide();box.addWidget(self.model_panel)
        box.addWidget(QLabel('CHANGE HISTORY · you and Graphite use the same journal'))
        self.history=QTreeWidget();self.history.setObjectName('SettingsHistory');self.history.setRootIsDecorated(False)
        self.history.setHeaderLabels(['When / actor','Before → after','State']);self.history.setAccessibleName('Setting change history')
        self.history.header().setSectionResizeMode(0,QHeaderView.ResizeToContents)
        self.history.header().setSectionResizeMode(1,QHeaderView.Stretch);self.history.setMaximumHeight(210);box.addWidget(self.history)
        self.undo_button=action('Undo selected change',self.undo);self.undo_button.setEnabled(False);box.addWidget(self.undo_button,0,Qt.AlignLeft)
        self.history.itemSelectionChanged.connect(self.history_selected)
        coverage=QLabel('Model activation, credentials, memory import, deletion and archives retain their existing controls.');coverage.setWordWrap(True);box.addWidget(coverage)
        related=QHBoxLayout()
        for label,callback in [('Local models',bridge.show_brain),('Memory',bridge.show_memory),('Credential controls',bridge.host.open_clip)]:related.addWidget(action(label,callback))
        related.addStretch();box.addLayout(related)
        box.addStretch(1)
        # Preserve the legacy Tools destination as an inventory, never fake settings.
        self.tools=QTreeWidget();self.tools.setHeaderLabels(['Tool','Status']);self.tools.hide();outer.addWidget(self.tools)
        self.categories=QComboBox(self);self.categories.addItems(['All settings','Appearance','Slate','Workspace','Operations','Tools']);self.categories.hide()
        self.categories.currentTextChanged.connect(self.set_category)
        self.set_category(category)

    def title(self):return 'Settings'

    def set_category(self,category):
        self._capture();self.tools.setVisible(category=='Tools');self.scroll.setVisible(category!='Tools')
        if category=='Tools':
            from .tool_inventory import inspect
            self.tools.clear()
            for row in inspect(root=self.bridge.host.root)['tools']:
                self.tools.addTopLevelItem(QTreeWidgetItem([row['label'],row['status']]))
            for row in inspect(root=self.bridge.host.root).get('operation_adapters',[]):
                self.tools.addTopLevelItem(QTreeWidgetItem([row['id'],row['state']]))
            self.tools.setAccessibleName('Tool inventory; status rather than settings');return
        rows=ledger_control.settings(self.bridge.kernel,'' if category=='All settings' else category)['settings']
        if rows:self.load_key(self.key if any(r['key']==self.key for r in rows) else rows[0]['key'])

    def editor_value(self):
        editor=self.editors.currentWidget()
        if editor is self.boolean:return bool(self.boolean.currentIndex())
        if editor is self.favorite_slots:return self.favorite_slots.value()
        if editor is self.view_modes:return self.view_modes.value()
        if editor is self.choice:return self.choice.currentData() if self.choice.currentData() is not None else self.choice.currentText()
        if editor is self.number:return int(self.number.value()) if self.current and self.current['type']=='integer' else self.number.value()
        if self.current and self.current.get('editor')=='number_text':
            try:return float(self.string.text().strip())
            except ValueError:return self.string.text()
        return self.string.text()

    def _capture(self):
        if self._loading or not self.current or not getattr(self,'_can_edit_current',True):return
        value=self.editor_value()
        if value!=self.current['value']:
            self.drafts[self.key]={'row':copy.deepcopy(self.current),'value':value}
        else:self.drafts.pop(self.key,None)

    def edited(self,*_):
        if self._loading:return
        self._capture();self.draft_label.setText('Unsaved edit · Apply uses the revision you opened.' if self.key in self.drafts else 'Write the value in the highlighted passage.')

    def load_key(self,key):
        changed_key=self.key!=key;self._capture();self.key=key
        fresh=next(r for r in ledger_control.settings(self.bridge.kernel)['settings'] if r['key']==key)
        draft=self.drafts.get(key);self.current=copy.deepcopy(draft['row'] if draft else fresh)
        value=draft['value'] if draft else fresh['value'];self._loading=True
        shown=settings_registry.public(fresh)  # GRAPHITE-01: the public words; the definition and the detail below stay as stored
        self.scroll.show();self.page.show();self.tools.hide();self.breadcrumb.setText('SETTINGS / '+shown['root_name'].upper()+' / '+fresh['group'].upper())
        self.heading.setText(shown['label']);self.key_label.setText(fresh['key']+' · '+fresh['type']+' · '+fresh['scope'])
        self.description.setText(shown['description'])
        editable=fresh.get('editable',True)
        self._can_edit_current=editable
        # Default is offered for an unreadable store only when ledger.settings.restore actually repairs it: program-owned rows flagged
        # repairable, and the local-model launch defaults whose stored row is invalid (model_settings names exactly that failure).
        repairable=bool(fresh.get('repairable')) or (not editable and 'launch defaults are unavailable or invalid' in str(fresh.get('effective_source','')))
        self.editors.setVisible(editable);self.apply_button.setEnabled(editable);self.reset_button.setEnabled(editable or repairable)
        if not editable:self.description.setText(shown['description']+' '+fresh['effective_source'])
        from .presentation_qt import display
        show=lambda value:display(self.bridge.host,fresh,value)
        self.state.setText('Saved: '+show(fresh['stored'])+'    Default: '+show(fresh['default'])+'\nEffective: '+show(fresh['effective'])+
            ' · '+fresh['application_state'].replace('_',' ').lower()+'\nApplies: '+shown['effect']+'.')
        if not editable:self.editors.setCurrentWidget(self.string);self.string.clear()
        elif fresh.get('editor')=='favorite_slots':
            self.favorite_slots.configure(fresh['favorite_group'],value);self.editors.setCurrentWidget(self.favorite_slots)
        elif fresh.get('editor')=='view_modes':
            self.view_modes.configure(fresh,value);self.editors.setCurrentWidget(self.view_modes)
        elif fresh.get('editor')=='number_text':
            self.string.setText(value if isinstance(value,str) else repr(value));self.editors.setCurrentWidget(self.string)
        elif 'choices' in fresh:
            self.choice.clear()
            for item in fresh['choices']:self.choice.addItem(fresh.get('choice_labels',{}).get(item,item),item)
            self.choice.setCurrentIndex(self.choice.findData(value));self.editors.setCurrentWidget(self.choice)
        elif fresh['type']=='boolean':self.boolean.setCurrentIndex(int(value));self.editors.setCurrentWidget(self.boolean)
        elif fresh['type'] in ('number','integer'):
            self.number.setSpecialValueText(fresh.get('zero_label',''))
            self.number.setDecimals(0 if fresh['type']=='integer' else 2);self.number.setSingleStep(1 if fresh['type']=='integer' else .1)
            self.number.setRange(fresh['minimum'],fresh['maximum']);self.number.setValue(value);self.editors.setCurrentWidget(self.number)
        else:self.string.setText(value);self.editors.setCurrentWidget(self.string)
        self.editors.setFixedHeight(max(46,self.editors.currentWidget().sizeHint().height()))
        self.editors.currentWidget().setAccessibleName(shown['label']+' value')
        self.detail.setPlainText(json.dumps({**fresh,'editor_base_revision':self.current['revision']},indent=2,ensure_ascii=False))
        self._loading=False;self.edited()
        self.signature=(fresh['revision'],fresh['effective'],fresh['application_state'],fresh.get('runtime_revision'))
        self.model_panel.setVisible(key in settings_registry.MODEL_KEYS)
        if key in settings_registry.MODEL_KEYS:self.model_panel.bind(fresh.get('model_runtime'))
        if draft and not editable:self.note.setText('The settings store is unavailable. Your draft is preserved.')
        elif draft and draft['row']['revision']!=fresh['revision']:
            self.note.setText('A newer saved revision exists. Your highlighted draft is preserved; inspect it or Reload saved value.')
        elif changed_key:
            self.note.setText(fresh['effective_source'] if key in settings_registry.MEMORY_KEYS else
                              'Saved value read. Apply records a new change through the existing store.')
        self.history.clear()
        for change in ledger_control.history(self.bridge.kernel,key)['changes']:
            item=QTreeWidgetItem([time.strftime('%H:%M:%S',time.localtime(change['at']))+' · '+change['actor'],
                show(change['before'])+' → '+show(change['after']),'Undone' if change['undone'] else 'Reversible' if change['can_undo'] else 'Earlier revision'])
            item.setData(0,Qt.UserRole,change);item.setToolTip(0,change['id']);self.history.addTopLevelItem(item)
        if self.history.topLevelItemCount():self.history.setCurrentItem(self.history.topLevelItem(0))
        self.history_selected()
        navigation=getattr(self.bridge.host,'navigation_controller',None)
        if navigation:navigation.changed(self)

    def refresh(self,*_):
        if self.key:self.load_key(self.key)

    def poll(self):
        if not self.key or self.tools.isVisible():return
        fresh=next(r for r in ledger_control.settings(self.bridge.kernel)['settings'] if r['key']==self.key)
        if (fresh['revision'],fresh['effective'],fresh['application_state'],fresh.get('runtime_revision'))!=self.signature:self.load_key(self.key)

    def reload_latest(self):
        if not self.key:return
        self.drafts.pop(self.key,None);self.current=None;self.load_key(self.key)
        self.note.setText('Loaded the saved revision. Other settings drafts are retained.')

    def save(self,checked=False,default=False):
        if not self.current:return
        args={'key':self.key,'expected_revision':self.current['revision']}
        if not default:args['value']=self.editor_value()
        response=self.bridge.kernel.dispatch('ledger.settings.restore' if default else 'ledger.settings.set',args,operator())
        if not response['ok']:
            self._capture();message=response['error']['message']
            self.note.setText(message if 'preserved' in message else message+' · Your draft is preserved.');return
        self.last_change=response['result']['id'];self.drafts.pop(self.key,None);self.current=None
        self.bridge.sync_profile(force=True);self.bridge.sync_provider();self.bridge.publish_settings_readback();self.load_key(self.key)
        self.note.setText('Saved '+self.key+' · change '+self.last_change[:8]+'. Inspect effective state above.')

    def history_selected(self):
        item=self.history.currentItem();row=item.data(0,Qt.UserRole) if item else None
        self.undo_button.setEnabled(bool(row and row['can_undo']))

    def undo(self):
        item=self.history.currentItem();row=item.data(0,Qt.UserRole) if item else None
        if not row:return
        response=self.bridge.kernel.dispatch('ledger.settings.undo',{'id':row['id']},operator())
        if response['ok']:
            self.last_change=response['result']['id'];self.bridge.sync_profile(force=True);self.bridge.sync_provider();self.bridge.publish_settings_readback()
            self.refresh();self.note.setText('Previous value restored as a new journal revision.')
        else:self.note.setText(response['error']['message'])

    def toggle_detail(self):self.detail.setVisible(not self.detail.isVisible())


class SettingsNavigator:
    """Separate left view; the cabinet widget, selection and scrolling survive."""
    def __init__(self,host,box,footer_line=None,footer_settings=None):
        self.host=host;self.line=footer_line;self.footer_settings=footer_settings;self.remembering=False
        self.saved=host.session.state.get('settings_navigation',{})
        # HATCH DESK D1b: the left pane's three tabs, Machine · Cabinet · Settings, with the desk's tab metrics (pane_qt): equal
        # widths and gaps, the row centred on the pane, the chosen tab marked by the short yellow mark. Each is still a checkable
        # push button under its old name (self.machine, self.cabinet, self.settings) for every caller.
        from .pane_qt import PaneTabs
        self.bar=PaneTabs(('Files','Machine','Settings'),'Left column views',host);self.cabinet,self.machine,self.settings=self.bar.buttons
        self.cabinet.clicked.connect(self.return_to_cabinet);self.machine.clicked.connect(self.show_machine);self.settings.clicked.connect(lambda:host.ledger_bridge.show_settings())
        self.bar.setProperty('paperFunctionalInk',True)
        self.stack=QStackedWidget();box.removeWidget(host.nav)
        from .cabinet_qt import CabinetPage
        host.cabinet_page=CabinetPage(host,footer_line);self.stack.addWidget(host.cabinet_page)
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(8,6,8,6);self.page=page
        self.filter=QLineEdit();self.filter.setObjectName('SettingsFilter');self.filter.setAccessibleName('Filter settings');writing_prompt(self.filter, 'Find a setting…')
        self.filter.setStyleSheet(PASSAGE_STYLE)
        layout.addWidget(self.filter)
        from .pane_qt import BranchTree
        self.tree=BranchTree();self.tree.setHeaderHidden(True);self.tree.setAccessibleName('Graphite settings hierarchy')  # D1b: the desk's tree (rows, indent, branch lines)
        layout.addWidget(self.tree,1)
        self.caption=QLabel(str(len(settings_registry.SPECS))+' settings\nOther settings retain their existing controls.');self.caption.setWordWrap(True);layout.addWidget(self.caption)
        self.stack.addWidget(page)
        # The Machine view is the third page; the strip above the switch bar keeps the machine visible whatever the column shows (NV01).
        # The foot of the column (view line, Settings word, fixed Trash) is untouched below the stack.
        from .machine_qt import MachinePage,MachineStrip
        host.machine_page=MachinePage(host);self.stack.addWidget(host.machine_page)
        self.strip=MachineStrip(host);host.machine_strip=self.strip
        box.insertWidget(0,self.stack,1);box.insertWidget(0,self.bar);box.insertWidget(0,self.strip)
        self.items={}
        for node in settings_registry.nodes():
            item=QTreeWidgetItem([node['label']]);item.setData(0,Qt.UserRole,node);self.items[node['id']]=item
            if node['parent']:self.items[node['parent']].addChild(item)
            else:self.tree.addTopLevelItem(item)
            if node['target']:
                item.setForeground(0,QColor(INK));item.setToolTip(0,node['target'])
        expanded=self.saved.get('expanded')
        for ident,item in self.items.items():
            if item.childCount():item.setExpanded(ident in expanded if expanded is not None else True)
        self.tree.itemSelectionChanged.connect(self.selected)
        self.tree.itemExpanded.connect(self.remember);self.tree.itemCollapsed.connect(self.remember)
        self.filter.textChanged.connect(self.filtered);self.show(False,persist=False)
        if self.footer_settings:self.footer_settings.hide()
        if self.saved.get('mode')=='settings':QTimer.singleShot(0,lambda:host.ledger_bridge.show_settings())
        elif self.saved.get('mode')=='machine':QTimer.singleShot(0,self.show_machine)  # the Machine view returns at start as Settings does

    def show(self,on,persist=True):
        """Existing callers: on → settings, off → cabinet. The Machine view is chosen through show_view/show_machine."""
        self.show_view('settings' if on else 'cabinet',persist)

    def show_view(self,name,persist=True):
        self.stack.setCurrentIndex(VIEWS.index(name))
        for button,view,description in ((self.cabinet,'cabinet','Show logical filing cabinet'),
                                        (self.machine,'machine','Show this computer: processor, memory, storage, connections, devices and installed tools'),
                                        (self.settings,'settings','Show Graphite settings')):
            button.setChecked(view==name);button.setAccessibleDescription('Current view' if view==name else description)
        if self.line:self.line.setVisible(name=='cabinet' and self.host.cabinet_page.using_legacy)
        if persist:self.remember()

    def current_view(self):return VIEWS[self.stack.currentIndex()]

    def show_machine(self):
        self.show_view('machine')
        page=getattr(self.host,'machine_page',None)
        if page is not None:page.build()

    def return_to_cabinet(self):
        navigation=getattr(self.host,'navigation_controller',None)
        if navigation:return navigation.cabinet()
        self.show(False)

    def select(self,key=None,reveal=True):
        if not key:
            current=self.tree.currentItem();node=current.data(0,Qt.UserRole) if current else {}
            ident=node.get('id') or self.saved.get('selected','setting:reading.family')
            item=self.items.get(ident)
        else:item=self.items.get('setting:'+key)
        if item is not None:
            with QSignalBlocker(self.tree):
                if reveal:
                    from .navigation_qt import hidden
                    if hidden(item):self.filter.clear()
                    parent=item.parent()
                    while parent:parent.setExpanded(True);parent=parent.parent()
                self.tree.setCurrentItem(item)
                if reveal:self.tree.scrollToItem(item)
            self.remember()

    def selected_key(self):
        item=self.tree.currentItem();node=item.data(0,Qt.UserRole) if item else {}
        return node.get('target')

    def selected(self):
        self.remember();key=self.selected_key()
        if key:self.host.ledger_bridge.show_settings(key=key)

    def remember(self,*_):
        if self.remembering:return
        self.remembering=True
        try:
            self.host.ledger_bridge.sync_profile()
            current=self.tree.currentItem();node=current.data(0,Qt.UserRole) if current else {}
            mode=self.current_view()
            if mode=='machine' and not PERSIST_MACHINE_MODE:mode='cabinet'  # a loader without the word would drop the whole record
            data=dict(mode=mode,selected=node.get('id',self.saved.get('selected','setting:reading.family')),
                      expanded=self.saved.get('expanded',[]) if self.filter.text().strip() else
                               [ident for ident,item in self.items.items() if item.childCount() and item.isExpanded()])
            self.saved=data;self.host.session.state['settings_navigation']=data;self.host.session.save()
        finally:self.remembering=False

    def filtered(self,text):
        query=text.strip().casefold()
        def visit(item,inherited=False):
            node=item.data(0,Qt.UserRole);match=inherited or not query or query in (node['label']+' '+(node['target'] or '')).casefold()
            children=[visit(item.child(i),match) for i in range(item.childCount())]
            visible=match or any(children);item.setHidden(not visible)
            if query and children and visible:item.setExpanded(True)
            return visible
        with QSignalBlocker(self.tree):
            for i in range(self.tree.topLevelItemCount()):visit(self.tree.topLevelItem(i))
            if not query:
                for ident,item in self.items.items():
                    if item.childCount():item.setExpanded(ident in self.saved.get('expanded',[]))
