"""The workshop's capability entrance. Search and selection never execute work.

Shared by Hatch (the doorway: six tool groups first) and the Explore word (the broad discovery route): the same
descriptor words for the same stored or passive state, and the same keyboard access for both popups.
"""
import json
from PySide6.QtCore import Qt,QTimer,QSignalBlocker,QObject,QEvent
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QComboBox,QApplication,
    QTreeWidget,QTreeWidgetItem,QHeaderView,QPlainTextEdit,QSplitter,QMenu,QToolButton,QScrollArea,QLayout,QSizePolicy)
from . import explore
from .engineering_kernel import operator,CAPABILITIES
from .settings_qt import action,STYLE,INK
from .text_prompts import writing_prompt


def label(text=''):
    widget=QLabel(text);widget.setTextFormat(Qt.PlainText);widget.setWordWrap(True);widget.setMinimumWidth(0);return widget


def command(text,callback):
    button=action(text.replace('&','&&'),callback);button.setAccessibleName(text);return button


def selected_record(host):
    current=host.tabs.currentWidget()
    ident=current.property('cabinet_node') if current is not None else None
    if ident:return ident
    page=getattr(host,'cabinet_page',None)
    item=page.tree.currentItem() if page is not None else None
    return item.data(0,Qt.UserRole)['id'] if item else None


# Shared by the Hatch launcher and the Explore button: the same words for the same stored or live state.
BRAIN_WORDS={'READY':'ready','MODEL_STOPPED':'stopped','NO_MODEL_SELECTED':'no model selected'}
COUNTERS=(('running_jobs','running'),('queued_jobs','queued'),('interrupted_jobs','interrupted'))
ROOM_NOTE='Opens as a retained workspace beside your current work; your Preview and pins are not replaced.'
UNASSESSED='Qualification: not assessed on this host.'
NO_EXECUTION='Opening runs no tool.'
F1_NOTE='F1 reads the highlighted row into the typing-bar note.'
# The Explore tab's Kind column for the three presentation kinds of explore.VIEWS.
PRESENTATION_WORDS={'workspace':'Workspace','checks':'Tool checks','operations':'App operations'}


def view_open(host,entry):
    return any(type(host.tabs.widget(i)).__name__==entry['view_class'] for i in range(host.tabs.count()))


def brain_state(kernel):
    """The local-model status for one menu opening. A failed read is the explicit sentinel, never a guess."""
    import sqlite3
    from . import local_brain
    try:return local_brain.status(kernel)
    except (ValueError,OSError,KeyError,TypeError,AttributeError,sqlite3.Error):return {'state':'UNAVAILABLE'}


def brain_word(brain):
    """None when no state was read (no word is shown); 'state unavailable' only for a failed read."""
    return BRAIN_WORDS.get(brain.get('state'),'state unavailable') if isinstance(brain,dict) else None


def capability_text(entry,opened,brain=None):
    """Row words: presence, missing setup, open tab and owner job rows; never a registration count or a readiness claim."""
    text=entry['title'].replace('&','&&')
    if not entry['view_available']:return text+' · unavailable'
    if entry.get('tool_status')=='Needs setup':text+=' · needs setup'  # visible without hover (HT03)
    if opened:text+=' · open'
    for key,word in COUNTERS:
        if entry.get(key):text+=' · %d %s'%(entry[key],word)
    if entry['key']=='brain' and brain_word(brain):text+=' · '+brain_word(brain)
    return text


def slate_line(entry):
    """The registered family operations with their scopes, from the catalogue; a bounded list, never a count claim."""
    rows=entry.get('slate_operations') or []
    if not rows:return 'Graphite can: no registered operation for this family'
    more=int(entry.get('operations',len(rows)))-len(rows)
    return 'Graphite can: '+', '.join('%s (%s)'%(r['operation'],r['scope']) for r in rows)+(' and %d more'%more if more>0 else '')


def needs_line(entry):
    """Prerequisites apart from qualification: the missing executables by name, or what passive detection found."""
    status=entry.get('tool_status')
    if status=='Needs setup':return 'Needs: '+', '.join(entry.get('setup_needed') or ['setup'])
    if status=='Detected · checks remain':return 'Prerequisites present (unmeasured)'
    if status=='Not assessed':return 'Prerequisites: no native profile to check'
    return 'Prerequisites: none beyond Graphite'


def context_line(context):
    if not isinstance(context,dict) or not context:return 'Context: none selected'
    return 'Context: '+str(context.get('label') or context.get('id') or 'selected record')+' · '+str(context.get('role') or 'record').replace('_',' ')


def capability_tip(entry,brain=None,context=None):
    """The descriptor (INTEGRATION_CONTRACTS capability_presentation): what opens, what Slate can do, what is missing,
    the owner's job rows, the unassessed qualification, the current work context, and that opening runs nothing."""
    lines=[entry['description']]
    if entry['view_available']:lines.append('Opens: '+str(entry.get('presentation') or 'Graphite workspace'))
    else:lines.append('View unavailable: '+', '.join(entry.get('missing_modules') or [entry['source']['path']]))
    lines.append(slate_line(entry));lines.append(needs_line(entry))
    counts=[(entry.get(key,0),word) for key,word in COUNTERS]
    lines.append(' · '.join('%d %s'%(n,word) for n,word in counts if n)+' for this owner' if any(n for n,_ in counts) else 'No jobs for this owner')
    if entry['key']=='brain' and brain_word(brain):lines.append('Local model: '+brain_word(brain))
    if entry.get('project_required'):lines.append('Needs an attached project.')
    lines.append(UNASSESSED);lines.append(context_line(context));lines.append(NO_EXECUTION)
    lines.append(ROOM_NOTE)
    return '\n'.join(lines)


def descriptor(action):
    """One line for the typing-bar note: the row's words and its descriptor, without the room note."""
    text=action.text().replace('&&','&')
    lines=[line for line in action.toolTip().split('\n') if line and line!=ROOM_NOTE]
    if not lines and action.menu() is not None:lines=['a group of rows; Right or Enter opens it']
    return text+' — '+' · '.join(lines) if lines else text


def activate_first(menu):
    """The first enabled row becomes active (a keyboard opening must not start with nothing highlighted)."""
    first=next((a for a in menu.actions() if a.isEnabled() and a.isVisible() and not a.isSeparator()),None)
    if first is not None:menu.setActiveAction(first)
    return first


class LauncherKeys:
    """Mixed into the two launcher buttons: Return and Enter open the popup like Space, and a keyboard opening
    starts with its first enabled row active (ACC-02). The button's prepare() calls open_with_keyboard()."""
    _keyboard_open=False

    def event(self,event):
        if event.type()==QEvent.ShortcutOverride and event.key() in (Qt.Key_Return,Qt.Key_Enter):event.accept();return True
        return super().event(event)

    def keyPressEvent(self,event):
        if event.key() in (Qt.Key_Return,Qt.Key_Enter,Qt.Key_Space,Qt.Key_Select) and not event.isAutoRepeat():
            self._keyboard_open=True
            if event.key() in (Qt.Key_Return,Qt.Key_Enter):self.showMenu();return
        super().keyPressEvent(event)

    def keyboard_opening(self):
        flag=self._keyboard_open;self._keyboard_open=False
        return flag or (self.hasFocus() and QApplication.mouseButtons()==Qt.NoButton)


def open_with_keyboard(button,menu):
    """On a keyboard opening the first enabled row is active; a deferred pass covers the show that follows aboutToShow."""
    if not button.keyboard_opening():return False
    activate_first(menu)
    QTimer.singleShot(0,lambda:activate_first(menu) if menu.isVisible() and menu.activeAction() is None else None)
    return True


class DescriptorKeys(QObject):
    """F1 or Shift+F1 on a highlighted row reads its descriptor into the typing-bar note through the existing status
    route (ACC-03); nothing is shown as a tooltip. The override is claimed so the window's F1 shortcut stays quiet."""
    def __init__(self,host,*menus):
        super().__init__(menus[0]);self.host=host;self.shown=None
        for menu in menus:self.watch(menu)

    def watch(self,menu):menu.installEventFilter(self)

    def eventFilter(self,menu,event):
        if event.type() in (QEvent.ShortcutOverride,QEvent.KeyPress) and event.key()==Qt.Key_F1:
            event.accept()
            if event.type()==QEvent.KeyPress and isinstance(menu,QMenu) and menu.activeAction() is not None:
                self.shown=descriptor(menu.activeAction());self.host.statusBar().showMessage(self.shown,12000)
            return True
        return False


# What each Hatch group holds, for the group row's descriptor (F1) and tooltip; the rows themselves carry the contract.
GROUP_NOTES={'Work':'Projects and ideas, questions, the Office, Files, the Operations agenda and the activity trail',
    'Reason':'Calculate and compare, the Laboratory and the methods atlas',
    'Instruments':'The Tool Atlas of registered operation contracts and tool passports',
    'Programs':'Graphite’s checks, profiles and output controls for the installed native tools; their own editors do not open here',
    'Knowledge':'Sources and knowledge, References and Graphite memory',
    'Configuration':'The local model and the shared Graphite settings'}


def group_menus(parent,prefix):
    """One persistent submenu per group, created once per button; each opening only refills them."""
    groups={}
    for group in explore.GROUPS:
        sub=QMenu(group,parent);sub.setToolTipsVisible(True);sub.setAccessibleName(prefix+': '+group);groups[group]=sub
        sub.menuAction().setToolTip(GROUP_NOTES.get(group,group)+'. Right or Enter opens the rows.')
    return groups


def fill_capability_groups(groups,host,value,launch,brain=None):
    """Refill the group submenus from one ledger.explore result; returns the number of rows."""
    count=0;context=value.get('context')
    for group,sub in groups.items():
        sub.clear()
        for entry in sorted((r for r in value['instruments'] if r['group']==group),key=lambda r:r['title'].casefold()):
            a=sub.addAction(capability_text(entry,view_open(host,entry),brain),lambda checked=False,e=entry:launch(e,context))
            a.setEnabled(entry['view_available']);a.setToolTip(capability_tip(entry,brain,context));count+=1
    return count


def open_instrument(host,entry,context=None):
    """Use original view factories, retaining newly opened views as existing Rooms."""
    bridge=host.ledger_bridge
    # Recheck current source/registry availability before opening a frozen result.
    current=bridge.kernel.dispatch('ledger.explore',{'kind':'INSTRUMENT'},operator())
    if not current['ok']:raise ValueError(current['error']['message'])
    live=next((r for r in current['result']['instruments'] if r['id']==entry['id']),None)
    if live is None or not live['view_available']:raise ValueError('This workspace is unavailable. Refresh Explore for details.')
    entry=live;route=live['destination']
    existing=any(type(host.tabs.widget(i)).__name__==entry['view_class'] for i in range(host.tabs.count()))
    from .shell2 import open_destination
    with bridge.retained_views():
        if route in ('calculate','laboratory'):
            tab=open_destination(host,'project_desk')
            if tab is None:return None
            if not existing and context and context['role']=='project':
                tab.open_project(context['canonical_id'].removeprefix('project:'))
            tab.tabs.setCurrentWidget(tab.problem_pane)
            tab.problem_pane.pages.setCurrentIndex(3 if route=='calculate' else 4)
        elif route.startswith('program:') or route in ('project_desk','agenda','files','investigations'):tab=open_destination(host,route)
        elif route=='documents':  # a selected document opens itself; any other context opens the room
            ident=context['canonical_id'].removeprefix('document:') if context and context.get('role')=='document' and str(context.get('canonical_id','')).startswith('document:') else ''
            tab=open_destination(host,'documents'+(':'+ident if ident else ''))
        else:
            callback=bridge.navigation().get(route)
            if callback is None:raise ValueError('This view has no current navigation route.')
            tab=callback()
    if isinstance(tab,QWidget):tab.setProperty('explore_instrument',entry['key'])
    return tab


class ExploreTab(QWidget):
    def __init__(self,host):
        super().__init__();self.host=host;self.model=None;self.context_id=None;self.offset=0;self.loading=False
        self.setObjectName('ExploreWorkspace');self.setProperty('ledgerRoom',True);self.setProperty('paperFunctionalInk',True)
        from .shell2 import AMBER,TEXT,ERASER_DEEP  # the yellow writing passage: visible selection (AMBER_SOFT equals AMBER), no border, bottom rule on focus
        self.setStyleSheet(STYLE+'''
            QLineEdit#ExploreQuery {background:%s;color:%s;border:0;padding:10px;min-height:26px;selection-background-color:%s;selection-color:%s;}
            QLineEdit#ExploreQuery:focus {border-bottom:2px solid %s;}'''%(AMBER,TEXT,ERASER_DEEP,TEXT,TEXT)+'''
            QTreeWidget#ExploreResults {background:transparent;color:#504d46;border:0;}
            QTreeWidget#ExploreResults::item {padding:7px 4px;}
            QTreeWidget#ExploreResults::item:selected {background:#f3e3e2;}
            QComboBox#ExploreKind {background:transparent;color:#885e64;border:0;border-bottom:1px solid #dad4c8;padding:8px 4px;}
            QComboBox#ExploreKind::drop-down {border:0;}
            QPlainTextEdit {background:transparent;color:#504d46;border:0;}
        ''')
        box=QVBoxLayout(self);box.setContentsMargins(22,18,22,16);box.setSpacing(12)
        heading=label('EXPLORE');heading.setProperty('arcReadingRole','heading');box.addWidget(heading)
        box.addWidget(label('What could this idea become?'))
        self.context_label=label('The workshop is open. Choose a capability or describe what you want to explore.');box.addWidget(self.context_label)
        row=QHBoxLayout();self.query=QLineEdit();self.query.setObjectName('ExploreQuery');self.query.setAccessibleName('Find capabilities, methods or registered operations')
        self.query.setMaxLength(180);writing_prompt(self.query,'Try units, memory, Python, a question, Calc, sources, or an exact operation ID.')
        row.addWidget(self.query,1);self.kind=QComboBox();self.kind.setObjectName('ExploreKind');self.kind.setAccessibleName('Explore result category')
        for title,key in [('Everything','ALL'),('Workspaces','INSTRUMENT'),('Methods','METHOD'),('Operations','OPERATION'),('Job tools','JOB_TOOL')]:self.kind.addItem(title,key)
        self.kind.setCurrentIndex(1)
        row.addWidget(self.kind);row.addWidget(action('Refresh',self.refresh));box.addLayout(row)
        self.suggestion_box=QHBoxLayout();box.addLayout(self.suggestion_box)
        split=QSplitter(Qt.Horizontal);box.addWidget(split,1)
        self.results=QTreeWidget();self.results.setObjectName('ExploreResults');self.results.setRootIsDecorated(False)
        self.results.setHeaderLabels(['Capability','Kind','Current view / prerequisites']);self.results.setAccessibleName('Explore capabilities and methods')
        self.results.header().setSectionResizeMode(0,QHeaderView.Stretch);self.results.setColumnWidth(1,105);self.results.header().setSectionResizeMode(2,QHeaderView.Stretch)
        split.addWidget(self.results)
        pane=QWidget();detail=QVBoxLayout(pane);detail.setContentsMargins(16,0,0,0);detail.setSizeConstraint(QLayout.SetMinimumSize)
        self.name=label('Choose an instrument or method.');self.name.setProperty('arcReadingRole','heading');detail.addWidget(self.name)
        self.description=label();detail.addWidget(self.description)
        self.readiness=label();detail.addWidget(self.readiness)
        self.open_button=action('Open workspace',self.open_selected);self.open_button.setEnabled(False);detail.addWidget(self.open_button,0,Qt.AlignLeft)
        self.why=label();detail.addWidget(self.why)
        detail.addWidget(action('Exact detail',lambda:self.technical.setVisible(not self.technical.isVisible())),0,Qt.AlignLeft)
        self.technical=QPlainTextEdit();self.technical.setReadOnly(True);self.technical.setAccessibleName('Exact selected capability descriptor');self.technical.hide();detail.addWidget(self.technical,1)
        self.receipt=QPlainTextEdit();self.receipt.setReadOnly(True);self.receipt.setAccessibleName('Explicit saved-record read result');self.receipt.hide();detail.addWidget(self.receipt,1)
        for widget in (self.name,self.description,self.readiness,self.why):widget.setSizePolicy(QSizePolicy.Preferred,QSizePolicy.Minimum)
        detail.addStretch();self.detail_scroll=QScrollArea();self.detail_scroll.setWidgetResizable(True);self.detail_scroll.setFrameShape(QScrollArea.NoFrame)
        self.detail_scroll.setWidget(pane);self.detail_scroll.setMinimumWidth(190);split.addWidget(self.detail_scroll);split.setSizes([680,380])
        row=QHBoxLayout();self.previous=action('Previous',lambda:self.page(-1));self.next=action('Next',lambda:self.page(1));row.addWidget(self.previous);row.addWidget(self.next)
        self.status=label();row.addWidget(self.status,1);row.addWidget(action('Find saved work',host.command_palette));box.addLayout(row)
        self.note=label('Opening a workspace leaves execution with its existing controls. Method suggestions need their own checks.');box.addWidget(self.note)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.setInterval(220);self.timer.timeout.connect(self.refresh)
        self.query.textChanged.connect(self.changed);self.query.returnPressed.connect(self.refresh);self.kind.currentIndexChanged.connect(self.changed)
        self.results.itemSelectionChanged.connect(self.inspect);self.results.itemDoubleClicked.connect(lambda *_:self.open_selected())

    def title(self):return 'Explore'

    def bind_context(self,ident):
        self.context_id=ident;self.setProperty('cabinet_node',ident);self.offset=0;self.refresh()
        navigation=getattr(self.host,'navigation_controller',None)
        if navigation:navigation.changed(self)

    def changed(self,*_):
        self.offset=0;self.open_button.setEnabled(False);self.results.setEnabled(False);self.timer.start()

    def page(self,direction):self.offset=max(0,self.offset+direction*60);self.refresh()

    def refresh(self):
        self.timer.stop();old=self.results.currentItem();selected=old.data(0,Qt.UserRole)['id'] if old else None
        args=dict(query=self.query.text(),kind=self.kind.currentData(),limit=60,offset=self.offset)
        if self.context_id:args['context']=self.context_id
        response=self.host.ledger_bridge.kernel.dispatch('ledger.explore',args,operator())
        if not response['ok']:
            # The previous rows stay usable; only the note carries the message.
            self.note.setText(response['error']['message']);self.results.setEnabled(True);self.inspect();return
        self.model=response['result'];context=self.model['context']
        self.context_label.setText(('Working from: '+context['label']+' · '+context['role'].replace('_',' ')) if context else
            'The workshop is open. Choose a capability or describe what you want to explore.')
        self.loading=True;self.results.clear();current=None
        for entry in self.model['entries']:
            state=entry.get('view_state',entry.get('status',''))
            if entry['kind']=='INSTRUMENT':
                opened=sum(type(self.host.tabs.widget(i)).__name__==entry['view_class'] for i in range(self.host.tabs.count()))
                state=('View already open' if opened else state)+' · '+entry['tool_status']
                if entry['active_jobs']:state+=' · '+str(entry['active_jobs'])+' active jobs'
            kind=PRESENTATION_WORDS.get(entry.get('presentation_kind'),'Workspace') if entry['kind']=='INSTRUMENT' else {'METHOD':'Method','OPERATION':'Operation','JOB_TOOL':'Job tool'}[entry['kind']]
            item=QTreeWidgetItem([entry['title'],kind,state])
            item.setData(0,Qt.UserRole,entry);item.setForeground(0,QColor(INK));item.setToolTip(0,entry.get('description',''))
            self.results.addTopLevelItem(item)
            if entry['id']==selected:current=item
        self.loading=False
        self.results.setEnabled(True)
        if current or self.results.topLevelItemCount():self.results.setCurrentItem(current or self.results.topLevelItem(0))
        else:self.name.setText('No matches yet.');self.description.setText('Try an instrument, method, subject, or exact operation name.');self.open_button.setEnabled(False)
        self.previous.setEnabled(self.offset>0);self.next.setEnabled(self.model['has_more'])
        self.status.setText(str(self.model['matches'])+' matches'+(' · more' if self.model['has_more'] else ''))  # registration totals are not readiness (V-10)
        while self.suggestion_box.count():
            child=self.suggestion_box.takeAt(0)
            if child.widget():child.widget().deleteLater()
        instruments={entry['key']:entry for entry in self.model['instruments']}
        for suggestion in self.model['suggestions']:
            entry=instruments[suggestion['id']]
            b=command(entry['title'],lambda checked=False,e=entry:self.open_entry(e));b.setToolTip(suggestion['reason']);self.suggestion_box.addWidget(b)
        for spec in self.model['context_actions']:
            if CAPABILITIES.get(spec['operation'])=='read':
                self.suggestion_box.addWidget(action(spec['label'],lambda checked=False,s=spec:self.read_context(s)))
        self.suggestion_box.addStretch()
        self.note.setText(' '.join(self.model['notices']) or 'Suggestions use the selected kind of work. Choosing a tool still requires its actual inputs and checks.')

    def inspect(self):
        if self.loading:return
        item=self.results.currentItem()
        if item is None:return
        entry=item.data(0,Qt.UserRole);self.name.setText(entry['title']);self.description.setText(entry.get('description',''))
        if entry['kind']=='INSTRUMENT':
            self.readiness.setText(entry['view_state']+'\nOpens: '+str(entry.get('presentation') or 'Graphite workspace')+'\n'+needs_line(entry)+' · '+entry['tool_status']+'\n'+str(entry['running_jobs'])+' running · '+str(entry['queued_jobs'])+' queued for this owner')
            self.open_button.setText('Open workspace');self.open_button.setEnabled(entry['view_available'])
        else:
            self.readiness.setText(entry.get('status','')+'\nQualification: not assessed on this host.')
            self.open_button.setText('Inspect method' if entry['kind']=='METHOD' else 'Inspect contract');self.open_button.setEnabled(True)
        self.why.setText('Inspection preserves original identities. The selected work remains in its existing record and revision history.')
        self.technical.setPlainText(json.dumps(entry,indent=2,ensure_ascii=False));self.receipt.hide()

    def open_selected(self):
        item=self.results.currentItem()
        if item:self.open_entry(item.data(0,Qt.UserRole))

    def open_entry(self,entry):
        try:
            if entry['kind']=='INSTRUMENT':
                open_instrument(self.host,entry,self.model['context']);return
            bridge=self.host.ledger_bridge
            with bridge.retained_views():
                if entry['kind']=='METHOD':
                    tab=bridge.show_algorithms()
                    if tab.input.document().isModified():
                        tab.note.setText('Your edited method input is retained. Explore requested: '+entry['title']+'. Choose Find when ready to change the method.')
                        return
                    tab.search.setText(entry['key']);tab.find()
                else:
                    tab=bridge.show_atlas();tab.search.setText(entry['key']);tab.kind.setCurrentIndex(2 if entry['kind']=='JOB_TOOL' else 1);tab.find()
        except (ValueError,OSError,ImportError) as exc:self.note.setText(str(exc))

    def read_context(self,spec):
        if CAPABILITIES.get(spec['operation'])!='read':return
        response=self.host.ledger_bridge.kernel.dispatch(spec['operation'],spec['arguments'],operator())
        if not response['ok']:self.note.setText(response['error']['message']);return
        self.receipt.setPlainText(json.dumps(response['result'],indent=2,ensure_ascii=False)[:100000]);self.receipt.show()
        self.note.setText(spec['label']+' · saved result read; no tool job started.')


def show(host,context=None):
    ident=selected_record(host) if context is None else context
    tab=host.ledger_bridge.add_tab(ExploreTab,lambda:ExploreTab(host));tab.bind_context(ident);return tab


class ExploreButton(LauncherKeys,QToolButton):
    """The Explore word: the broad discovery route and the suggestions for the selected record. The six tool groups
    live in Hatch, the doorway, and are not repeated here (DESKTOP-01 VS02 de-duplication)."""
    def __init__(self,host):
        super().__init__();self.host=host;self.setText('Explore');self.setAccessibleName('Explore capabilities launcher');self.snapshot=None
        self.setCursor(Qt.PointingHandCursor);self.setMinimumHeight(34);self.setProperty('paperFunctionalInk',True)
        self.setStyleSheet('QToolButton {background:transparent;color:#885e64;border:0;padding:5px 3px;text-decoration:underline;} QToolButton:focus {border-bottom:2px solid #504d46;}')
        self.setToolTip('Open the Explore workspace, or a suggested workspace for the selected record. The tool groups are in the menu. '+F1_NOTE)
        self.setAccessibleDescription('Explore the workshop, suggestions for the selected record, find saved work. '+F1_NOTE)
        self.setPopupMode(QToolButton.InstantPopup);self.popup=QMenu(self);self.popup.setObjectName('ExploreMenu');self.popup.setAccessibleName('Explore menu')
        self.popup.setToolTipsVisible(True);self.setMenu(self.popup);self.keys=DescriptorKeys(host,self.popup)
        self.popup.aboutToShow.connect(self.prepare)

    def prepare(self):
        # One snapshot per opening; targets stay still until the menu closes.
        self.popup.clear();ident=selected_record(self.host);args={'kind':'INSTRUMENT'}
        if ident:args['context']=ident
        response=self.host.ledger_bridge.kernel.dispatch('ledger.explore',args,operator())
        a=self.popup.addAction('Explore the workshop…',lambda:show(self.host,ident))
        a.setToolTip('Opens: the Explore workspace, a Graphite workspace that searches every workspace, method and registered operation. '+NO_EXECUTION)
        if not response['ok']:
            a=self.popup.addAction('Capability view unavailable');a.setEnabled(False);a.setToolTip(str(response['error']['message']))
        else:
            value=response['result'];self.snapshot=value
            if value['context']:
                # A disabled row, not addSection: section text does not render under the application stylesheet.
                heading=self.popup.addAction(('For '+value['context']['label'][:65]).replace('&','&&'));heading.setEnabled(False)
                heading.setToolTip('Suggestions follow the selected record kind; they infer no method fit and grant nothing.')
                entries={r['key']:r for r in value['instruments']}
                for suggestion in value['suggestions']:
                    entry=entries[suggestion['id']];a=self.popup.addAction(capability_text(entry,view_open(self.host,entry)),lambda checked=False,e=entry:self.launch(e,value['context']))
                    a.setToolTip(suggestion['reason']+'\n'+capability_tip(entry,None,value['context']));a.setEnabled(entry['view_available'])
        self.popup.addSeparator();a=self.popup.addAction('Find saved work…',self.host.command_palette)
        a.setToolTip('Find names and words in your Files, received files, commands and the Timeline. '+NO_EXECUTION)
        open_with_keyboard(self,self.popup)

    def launch(self,entry,context):
        try:open_instrument(self.host,entry,context)
        except (ValueError,OSError,ImportError) as exc:self.host.statusBar().showMessage(str(exc),6000)
