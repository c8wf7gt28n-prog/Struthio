"""Desktop surfaces for the shared command/settings/activity services."""
from .text_prompts import writing_prompt
import json
import os
import threading
import time
from contextlib import contextmanager
from PySide6.QtCore import QObject, QTimer, Qt, Signal, QSignalBlocker
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,
    QTreeWidget,QTreeWidgetItem,QComboBox,QCheckBox,QDoubleSpinBox,QListWidget,QListWidgetItem,
    QPlainTextEdit,QStackedWidget,QHeaderView)
from . import engine,activity,ledger_control,stacy_control
from .engineering_kernel import operator,Principal
from .project_context import refusal
from .session import Session


from .settings_qt import SettingsTab

class CommandsTab(QWidget):
    def __init__(self,bridge):
        super().__init__();self.bridge=bridge
        box=QVBoxLayout(self);box.addWidget(QLabel('GRAPHITE COMMANDS · shared Kernel / CLI / Graphite'))
        self.search=QLineEdit();writing_prompt(self.search, 'Filter commands, workspaces or actions');box.addWidget(self.search)
        self.table=QTreeWidget();self.table.setRootIsDecorated(False);self.table.setHeaderLabels(['Command / action','Connection','Scope'])
        self.table.header().setSectionResizeMode(0,QHeaderView.Stretch);self.table.setColumnWidth(1,230);box.addWidget(self.table,1)
        self.details=QPlainTextEdit();self.details.setReadOnly(True);self.details.setMaximumHeight(130);box.addWidget(self.details)
        self.input=QLineEdit();writing_prompt(self.input, '/call jobs.list {} · /set operations.priority background · /open brain link')
        box.addWidget(self.input);self.input.returnPressed.connect(self.send)
        self.search.textChanged.connect(self.refresh);self.table.itemSelectionChanged.connect(self.selected)
        self.bridge.command_finished.connect(self.finished);self.refresh()

    def title(self):return 'Graphite commands'

    def refresh(self,*_):
        self.table.clear()
        for row in ledger_control.catalog(self.bridge.kernel,operator(),self.search.text())['commands']:
            item=QTreeWidgetItem([row.get('label',row['command']),row['status'],row.get('scope','Desktop')]);item.setData(0,Qt.UserRole,row);self.table.addTopLevelItem(item)

    def selected(self):
        item=self.table.currentItem()
        if not item:return
        r=item.data(0,Qt.UserRole);self.details.setPlainText(json.dumps(r,indent=2))
        if r['kind']=='Kernel command':self.input.setText('/call '+r['command']+' {}')
        elif r.get('destination'):self.input.setText('/open '+r['destination'])

    def send(self):
        text=self.input.text().strip()
        if text:self.bridge.handle_text(text);self.input.clear()

    def finished(self,summary):
        results=getattr(self.bridge,'last_results',None)
        self.details.setPlainText(json.dumps(results,indent=2)[:18000] if results and not self.bridge.busy else summary)


class ActivityTail(QWidget):
    def __init__(self,bridge):
        super().__init__();self.bridge=bridge;self.signature=None
        box=QVBoxLayout(self);box.setContentsMargins(8,3,8,3);box.setSpacing(2)
        row=QHBoxLayout();self.heading=QLabel('ACTIVITY · local events');self.heading.setWordWrap(True);self.heading.setMinimumWidth(0);row.addWidget(self.heading,1)
        self.follow=QCheckBox('Follow latest');self.follow.setChecked(True);row.addWidget(self.follow)
        self.trail=QPushButton('Organizer');self.trail.clicked.connect(bridge.show_organizer);row.addWidget(self.trail)
        self.expand=QPushButton('Expand');self.expand.setCheckable(True);row.addWidget(self.expand);box.addLayout(row)
        self.search=QLineEdit();writing_prompt(self.search, 'Search retained activity');self.search.hide();box.addWidget(self.search)
        self.list=QListWidget();self.list.setObjectName('LedgerActivityTail');self.list.setAccessibleName('Live Graphite activity tail')
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setStyleSheet('QListWidget#LedgerActivityTail {background:#121820;border:1px solid #34404b;} QListWidget#LedgerActivityTail::item {padding:1px 5px;}')
        box.addWidget(self.list);self.resize_lines()
        self.expand.toggled.connect(self.expanded);self.search.textChanged.connect(lambda:self.refresh(True))
        self.follow.toggled.connect(lambda on:self.list.scrollToBottom() if on else None)
        self.list.verticalScrollBar().sliderPressed.connect(lambda:self.follow.setChecked(False))
        self.list.itemActivated.connect(self.open_event)
        self.list.viewport().installEventFilter(self)

    def eventFilter(self,obj,event):
        from PySide6.QtCore import QEvent
        if obj is self.list.viewport() and event.type()==QEvent.Wheel and event.angleDelta().y()>0:self.follow.setChecked(False)
        return super().eventFilter(obj,event)

    def resize_lines(self):
        height=(self.list.fontMetrics().height()+4)*(9 if self.expand.isChecked() else 4)+8
        self.list.setFixedHeight(height)

    def expanded(self,on):
        self.expand.setText('Collapse' if on else 'Expand');self.search.setVisible(on);self.resize_lines();self.refresh(True)

    def refresh(self,force=False):
        stream=activity.tail(self.bridge.host.root,query=self.search.text(),limit=200)
        from .stacy_awareness import inspect
        awareness=inspect(self.bridge.kernel)
        signature=(stream['cursor'],self.search.text(),awareness['cursor'],awareness['state'])
        if signature==self.signature and not force:return
        self.signature=signature;bar=self.list.verticalScrollBar();old=bar.value();self.list.clear();self._last_words=None
        from .tail_words import readable,in_flight
        events=stream['events'];open_requests=in_flight(events)
        for e in events:
            if e['state']=='REQUEST_RECEIVED' and e.get('correlation_id') not in open_requests:continue  # its completion line says it
            words=readable(e)
            if self.list.count() and getattr(self,'_last_words',None)==words:continue  # the job and the Kernel say the same thing
            self._last_words=words
            text=time.strftime('%H:%M:%S',time.localtime(e['at']))+'  '+words
            item=QListWidgetItem(text);item.setData(Qt.UserRole,e)
            item.setToolTip(json.dumps(e,indent=2));self.list.addItem(item)
        if not self.list.count():self.list.addItem('No recorded events in this view.')
        if self.follow.isChecked():self.list.scrollToBottom()
        else:bar.setValue(old)
        self.resize_lines()
        self.heading.setText('Timeline · Graphite '+{'CURRENT':'is up to date','BEHIND':'is catching up','INCOMPLETE':'has a gap in the record'}.get(awareness['state'],awareness['state'].lower())+
                             ('' if awareness['cursor']==awareness['head'] else ' · %d of %d read'%(awareness['cursor'],awareness['head'])))
        self.heading.setToolTip(awareness['journal'].get('reason',awareness['journal']['coverage']))

    def open_event(self,item):
        event=item.data(Qt.UserRole)
        if not event:return
        if event.get('job_id'):
            tab=self.bridge.host.show_engineering()
            for i in range(tab.jobs.topLevelItemCount()):
                item=tab.jobs.topLevelItem(i)
                if item.data(0,Qt.UserRole)==event['job_id']:
                    tab.jobs.setCurrentItem(item);tab.select_job();break
        elif event['operation'].startswith('ledger.settings'):self.bridge.show_settings()
        else:self.bridge.show_commands()


class LedgerBridge(QObject):
    command_finished=Signal(str)
    completed=Signal(int,object)

    def __init__(self,host):
        super().__init__(host);self.host=host;self.kernel=engine.engineering(host.root)
        from .study_qt import IdleBridge
        host.study_idle=IdleBridge(host,self.kernel)
        self.desktop_id=host.desktop_lease.stem
        ledger_control.bind(self.kernel,host.session);self.last_profile_mtime=None
        self.startup_at_launch=host.session.state['view_preferences']['startup']
        self._cursive_applied=host.session.state.get('cursive',True);self._provider_revision=None
        self._views_applied=dict(host.session.state.get('category_views',{}))
        from . import writing_marker
        self.marker=writing_marker.install(host);self._marker_applied=self.marker.enabled
        initial=ledger_control.settings(self.kernel)['settings']
        self._layout_revisions={r['key']:r['revision'] for r in initial if r['key'].startswith('layout.')}
        self._layout_requested={r['key']:r['stored'] for r in initial if r['key'].startswith('layout.')}
        host.output_dock.visibilityChanged.connect(self.output_visibility_changed)
        self._published=None;self.busy=False;self.completed.connect(self.finished)
        self.tail=ActivityTail(self);host.center_layout.insertWidget(host.center_layout.count()-1,self.tail)
        self.timer=QTimer(self);self.timer.setInterval(750);self.timer.timeout.connect(self.tick);self.timer.start()
        self.publish();self.tick()
        activity.record(host.root,'DESKTOP','ledger.open','READY','Shared commands, settings and activity connected')

    def navigation(self):
        h=self.host
        return {'discovery':self.show_discovery,'algorithms':self.show_algorithms,'atlas':self.show_atlas,'settings':self.show_settings,'commands':self.show_commands,'activity':self.show_activity,'trail':self.show_work_trail,'organizer':self.show_organizer,'packages':self.show_packages,'object_glass':h.show_object_glass,
                'brain':self.show_brain,'intake':self.show_intake,'references':self.show_references,'sources':self.show_sources,'memory':self.show_memory,
                'stacy_awareness':self.show_awareness,'home':h.show_start,'engineering':h.show_engineering,'brain_link':h.show_brain_link,
                'native_game':h.show_native_game,'orange_book':h.show_orange_book,'ledger':h.show_hardware_ledger,
                'arcos':h.show_arcos,'native_pcb':h.show_native_board,'developer_tools':h.show_developer_tools,'cad':self.show_cad,'kibot':self.show_kibot,'spice':self.show_spice,'yosys':self.show_yosys,'implementation':self.show_implementation,'hdl':self.show_hdl,'stacy_knowledge':self.show_stacy_knowledge,'office':self.show_office,'slate':self.show_slate,'files':h.show_files,
                'documents':self.show_documents,'investigations':self.show_investigations}

    def show_documents(self):
        from .document_qt import show
        return show(self.host)

    def show_investigations(self):
        from .investigations_qt import show
        return show(self.host)

    def show_discovery(self):
        from .discovery_qt import DiscoveryTab
        return self.add_tab(DiscoveryTab,lambda:DiscoveryTab(self))

    def show_algorithms(self):
        from .algorithm_atlas_qt import AlgorithmAtlasTab
        return self.add_tab(AlgorithmAtlasTab,lambda:AlgorithmAtlasTab(self))

    def show_atlas(self):
        from .tool_atlas_qt import ToolAtlasTab
        return self.add_tab(ToolAtlasTab,lambda:ToolAtlasTab(self))

    def show_stacy_knowledge(self):
        from .stacy_foundation_qt import StacyFoundationTab
        self.publish()
        return self.add_tab(StacyFoundationTab,lambda:StacyFoundationTab(self))

    def show_awareness(self):
        from .stacy_awareness_qt import AwarenessTab
        return self.add_tab(AwarenessTab,lambda:AwarenessTab(self))

    def show_office(self):
        from .office_building_qt import OfficeBuildingTab
        return self.add_tab(OfficeBuildingTab,lambda:OfficeBuildingTab(self.host))

    def show_slate(self):
        from .office_building_qt import SlateRoomTab
        return self.add_tab(SlateRoomTab,lambda:SlateRoomTab(self.host))

    def show_brain(self):
        from .brain_qt import BrainTab
        return self.add_tab(BrainTab,lambda:BrainTab(self.host))

    def show_intake(self):
        from .intake_qt import IntakeTab
        return self.add_tab(IntakeTab,lambda:IntakeTab(self.host))

    def show_memory(self):
        from .memory_qt import MemoryTab
        return self.add_tab(MemoryTab,lambda:MemoryTab(self.host))

    def show_sources(self):
        from .knowledge_qt import KnowledgeTab
        return self.add_tab(KnowledgeTab,lambda:KnowledgeTab(self.host))

    def show_references(self):
        from .reference_qt import ReferenceTab
        return self.add_tab(ReferenceTab,lambda:ReferenceTab(self.host))

    def show_hdl(self):
        from .hdl_qt import HdlTab
        return self.add_tab(HdlTab,lambda:HdlTab(self.host))

    def show_implementation(self):
        from .pnr_qt import ImplementationTab
        return self.add_tab(ImplementationTab,lambda:ImplementationTab(self.host))

    def show_yosys(self):
        from .yosys_qt import YosysTab
        return self.add_tab(YosysTab,lambda:YosysTab(self.host))

    def show_spice(self):
        from .spice_qt import SpiceTab
        return self.add_tab(SpiceTab,lambda:SpiceTab(self.host))

    def show_kibot(self):
        from .kibot_qt import KiBotTab
        return self.add_tab(KiBotTab,lambda:KiBotTab(self.host))

    def show_cad(self):
        if getattr(self.host,'project_required',None) and self.host.project_required('KiCad · Native Checks'):return None
        from .kicad_qt import KiCadTab
        return self.add_tab(KiCadTab,lambda:KiCadTab(self.host))

    def add_tab(self,kind,create):
        self.host._close_start()
        for i in range(self.host.tabs.count()):
            tab=self.host.tabs.widget(i)
            if type(tab) is kind:self.host.tabs.setCurrentWidget(tab);return tab
        tab=create()
        if getattr(self,'_retain_views',0):tab.setProperty('ledgerRoom',True)
        i=self.host.tabs.addTab(tab,self.host.nav_icon('config'),tab.title());self.host.tabs.setCurrentIndex(i);return tab

    @contextmanager
    def retained_views(self):
        """Explore opens the original factories without replacing an edited Preview."""
        self._retain_views=getattr(self,'_retain_views',0)+1
        try:yield
        finally:self._retain_views-=1

    def show_settings(self,category='All settings',key=None):
        nav=getattr(self.host,'settings_navigator',None)
        if nav:
            nav.show(True)
            if key is None and category=='All settings':key=nav.selected_key() or nav.saved.get('selected','setting:reading.family').removeprefix('setting:')
        tab=self.add_tab(SettingsTab,lambda:SettingsTab(self,category))
        # The string value passage opts into the writing marker (idempotent; the editor itself is unchanged).
        from .writing_marker import attach
        attach(self.host,tab.string)
        if key in ledger_control.BY_KEY:tab.load_key(key)
        else:tab.set_category(category)
        if nav and category!='Tools':nav.select(tab.key)
        return tab

    def show_commands(self):return self.add_tab(CommandsTab,lambda:CommandsTab(self))
    def show_organizer(self):
        from .organizer_qt import OrganizerTab
        return self.add_tab(OrganizerTab,lambda:OrganizerTab(self))

    def show_packages(self):
        from .organizer_qt import PackageTab
        return self.add_tab(PackageTab,lambda:PackageTab(self))

    def show_work_trail(self):
        from .work_trail_qt import WorkTrailTab
        return self.add_tab(WorkTrailTab,lambda:WorkTrailTab(self))

    def show_activity(self):
        self.host._close_start();self.tail.expand.setChecked(True);self.tail.search.setFocus();return self.tail

    def sync_profile(self,force=False):
        path=self.host.session.path
        try:stamp=path.stat().st_mtime_ns
        except OSError:return
        if not force and stamp==self.last_profile_mtime:return
        self.last_profile_mtime=stamp
        fresh=Session(path,self.host.root)
        state=self.host.session.state
        for key in ('reading_profile','view_preferences'):
            if key in fresh.state:state[key]=fresh.state[key]
        state['layout']['stacy_reactions']=fresh.layout['stacy_reactions']
        state['cursive']=fresh.state['cursive']
        for key in ('toolbar_favorites','toolbar_favorites_version'):state[key]=fresh.state[key]
        views=dict(fresh.state.get('category_views',{}));state['category_views']=views
        if views!=self._views_applied:
            # A Set/Undo/Default from Slate, the CLI or the Settings page reaches every open pane; consumers never re-journal.
            # Compared with the map last pushed, not with memory: an in-process Set already updated the bound session.
            self._views_applied=views
            for tab in self.hardware_panes():tab.follow_saved(views)
        from .writing_marker import enabled_in
        marker=enabled_in(fresh.state);state['writing_marker']=marker
        if marker!=self._marker_applied:
            # Immediate application: the one controller repaints its marks; Reduce motion is read by the controller itself.
            self._marker_applied=marker;self.marker.set_enabled(marker)
        from sdk.cli.arc1cli.command_bar import session_favorites
        favorites=session_favorites(state)
        if favorites!=self.host.favorites:
            self.host.favorites=favorites;self.host._update_favorite_marks();self.host._refresh_favorite_buttons()
            shell=getattr(self.host,'shell2',None)
            if shell:shell.hide_favorites()
            menu=getattr(self.host,'favorite_commands_menu',None)
            if menu is not None and not menu.isVisible():
                from .presentation_qt import fill_favorites_menu
                fill_favorites_menu(self.host)
        for key in self._layout_requested:state['layout'][key.split('.',1)[1]]=fresh.layout[key.split('.',1)[1]]
        from .reading_profile import DEFAULT
        if state.get('reading_profile',DEFAULT)!=getattr(self.host,'reading_profile',DEFAULT):
            from .reading_preferences import apply
            apply(self.host);self.tail.resize_lines()
        if self.host.view_preferences['mode']!=state['view_preferences']['mode']:
            self.host.set_workspace_layout(state['view_preferences']['mode'],persist=False)
        self.host.view_preferences['startup']=state['view_preferences']['startup']
        if not state['layout']['stacy_reactions']:self.host.clip.presence.dismiss()
        if self._cursive_applied!=state['cursive'] and hasattr(self.host,'shell2'):
            from .shell2 import cursive_on,pleasantry,quiet_script
            self._cursive_applied=state['cursive'];cursive_on(self.host)
            script=getattr(self.host.shell2,'script_action',None)
            if script:
                with QSignalBlocker(script):script.setChecked(self._cursive_applied)
            self.host.shell2.restyle(getattr(self.host,'reading_profile',None))
            for label in self.host.findChildren(QLabel):
                if label.property('pleasantry'):pleasantry(label,self.host,int(label.property('pleasantry_px') or 26))
                elif label.property('quiet_script'):quiet_script(label)
                elif label.property('quiet_words'):label.restyle()  # the panes' notes (shell2.QuietWords)
            top=getattr(self.host.shell2,'top',None)
            if top is not None:top.ledger_head()  # the word Graphite: the script, or print with the script off
            inspector=getattr(self.host,'arc_inspector',None)
            if inspector is not None:inspector.refresh()  # the Context face's notes (shell2.Note) in the script or print
        for row in ledger_control.settings(self.kernel,'Workspace')['settings']:
            key=row['key']
            if key not in self._layout_revisions or self._layout_revisions[key]==row['revision']:continue
            self._layout_requested[key]=row['stored'];self._layout_revisions[key]=row['revision']
            if key=='layout.navigator_width':
                self.host.resizeDocks([self.host.nav_dock],[row['stored']],Qt.Horizontal)
                bar=getattr(self.host,'type_bar',None)
                if bar is not None:bar.align()  # the desk's panes are fixed at one width: it applies the owner's width now, not on its next tick
            elif key=='layout.output_height':self.output_visibility_changed(self.host.output_dock.isVisible())
            elif key=='layout.output_visible':self.host.output_dock.setVisible(row['stored'])
            elif key=='layout.output_tab':
                for index in range(self.host.output_tabs.count()):
                    if self.host.output_tabs.tabText(index)==row['stored']:self.host.output_tabs.setCurrentIndex(index);break

    def output_visibility_changed(self,visible):
        if visible and not self.host._closing:
            self.host.resizeDocks([self.host.output_dock],[self._layout_requested['layout.output_height']],Qt.Vertical)

    def hardware_panes(self):
        from .hardware_overview import HardwareGroupTab
        return [tab for tab in (self.host.tabs.widget(i) for i in range(self.host.tabs.count())) if isinstance(tab,HardwareGroupTab)]

    def sync_provider(self):
        from . import clip
        try:preferences=clip.preferences()
        except OSError as exc:
            if str(exc)!=getattr(self,'_provider_error',None):self.host.statusBar().showMessage(str(exc),6000)
            self._provider_error=str(exc);return
        self._provider_error=None
        if preferences['revision']==self._provider_revision:return
        self._provider_revision=preferences['revision']
        overlay=getattr(self.host,'clip_overlay',None)
        if overlay is None:return # The chat creates its Settings from disk when opened.
        overlay.settings=clip.Settings.load()
        with QSignalBlocker(overlay.include):overlay.include.setChecked(preferences['include_file'])
        overlay.refresh()

    def sync_catalogue(self):
        concern=getattr(self.host,'concern',None)
        if concern is None or concern.store is None:return
        from .catalog_settings import read
        try:view,_=read(self.kernel)
        except ValueError:return
        if concern.view==view:return
        concern.remember();concern.view=view
        selector=getattr(concern,'selector',None)
        if selector is not None:selector.setCurrentIndex(selector.findData(view))
        # Rebuild only the selected Existing views presentation, keeping cabinet IDs.
        self.host.refresh_navigator()

    def publish_settings_readback(self):
        self.sync_catalogue()
        from .reading_preferences import family, in_force
        from .reading_profile import DEFAULT
        profile=getattr(self.host,'reading_profile',DEFAULT)
        values={'reading.'+key:{'requested':value,'effective':value} for key,value in profile.items()}
        names=tuple(profile[key] for key in ('family','prose_family','code_family'))
        actual=in_force(names)      # the faces the window is drawn in: the appearance's own while the owner keeps the defaults
        for key,name in zip(('family','prose_family','code_family'),actual):
            values['reading.'+key]['effective']=family(name,key=='code_family')
        values['workspace.mode']={'requested':self.host.view_preferences['mode'],'effective':self.host.view_preferences['mode']}
        values['workspace.startup']={'requested':self.startup_at_launch,'effective':self.startup_at_launch}
        reactions=self.host.session.layout['stacy_reactions']
        values['stacy.reactions']={'requested':reactions,'effective':reactions}
        if hasattr(self.host,'shell2'):
            from .shell2 import SCRIPT_ON
            values['appearance.cursive']={'requested':self._cursive_applied,'effective':SCRIPT_ON[0]}
        values['layout.navigator_width']={'requested':self._layout_requested['layout.navigator_width'],'effective':self.host.nav_dock.width()}
        visible=self.host.output_dock.isVisible()
        values['layout.output_visible']={'requested':self._layout_requested['layout.output_visible'],'effective':visible}
        values['layout.output_height']={'requested':self._layout_requested['layout.output_height'],
            'effective':self.host.output_dock.height() if visible else None,'state':'OBSERVED' if visible else 'WAITING_FOR_PANEL'}
        values['layout.output_tab']={'requested':self._layout_requested['layout.output_tab'],
            'effective':self.host.output_tabs.tabText(self.host.output_tabs.currentIndex())}
        from sdk.cli.arc1cli.command_bar import FAVORITE_KEYS
        for key,group in FAVORITE_KEYS.items():
            pins=list(self.host.favorites[group]);values[key]={'requested':pins,'effective':pins}
        concern=getattr(self.host,'concern',None)
        if concern is not None and concern.store is not None:
            values['catalog.view']={'requested':concern.view,'effective':concern.view}
        panes={tab.view_key:tab.mode.currentText() for tab in self.hardware_panes()}
        values['hardware.category_views']={'requested':dict(self.host.session.state.get('category_views',{})),'effective':panes,
            'state':'OBSERVED' if panes else 'NO_OPEN_PANE'}
        values['appearance.writing_marker']=self.marker.readback()
        ledger_control.publish_settings_runtime(self.kernel,self.desktop_id,values)

    def publish(self):
        from .operation_stop import process_identity
        mapping={'home':'home','engineering':'engineering','brain_link':'brain_link','native_game':'native_game',
                 'orange_book':'orange_book','ledger':'ledger','arcos':'arcos','native_pcb':'native_pcb','developer_tools':'developer_tools',
                 'discovery':'discovery','algorithms':'algorithms','atlas':'atlas','ledger_settings':'settings','ledger_commands':'commands','ledger_activity':'activity','stacy_knowledge':'stacy_knowledge','cad_checks':'cad','kibot_outputs':'kibot','spice_checks':'spice','yosys_synthesis':'yosys','fpga_implementation':'implementation','hdl_waveforms':'hdl'}
        rows=[]
        for key,action in self.host.favorite_actions.items():
            destination=mapping.get(key)
            rows.append({'command':'desktop.'+key,'label':action.text().replace('&',''),'kind':'Desktop action',
                         'status':'CONNECTED' if destination else 'INTERACTIVE_DESKTOP',
                         'destination':destination,'enabled':action.isEnabled(),
                         'execution':'ledger.navigate' if destination else 'Use the existing desktop control; source edits and acceptance retain their existing routes.'})
        for key in ('settings','commands','activity','organizer','packages'):
            rows.append({'command':'desktop.'+key,'label':key.title(),'kind':'Desktop action','status':'CONNECTED','destination':key})
        data={'pid':os.getpid(),'start':process_identity(os.getpid()),'desktop_id':self.desktop_id,'actions':rows}
        current=self.host.tabs.currentWidget()
        context={'surface':'home' if self.host._home_active else 'workspace',
                 'workspace':type(current).__name__ if current else None,
                 'selection':{k:self.host.selection_context.get(k) for k in ('kind','reference','native_uuid')} if self.host.selection_context else None}
        from .stacy_foundation_qt import selected_view
        supported=selected_view(current) if not self.host._home_active else None
        if supported:
            self.last_stacy_view=supported
        context['stacy_view']=supported
        cabinet_node=current.property('cabinet_node') if current else None
        if cabinet_node:context['cabinet_selection']={'id':cabinet_node,'read_operation':'ledger.cabinet.get'}
        path=engine.document_path(getattr(current,'path',None))
        if path is not None:
            try:context['active_file']=str(path.relative_to(self.host.root))
            except ValueError:pass
        serialized=json.dumps([data,context],sort_keys=True)
        if serialized==self._published:return
        self._published=serialized
        with self.kernel.db() as db:
            for key,value in (('ledger.desktop_catalog',data),('ledger.desktop_context',context)):
                db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,json.dumps(value)))

    def tick(self):
        if self.host._closing:return
        try:
            self.sync_profile();self.sync_provider();self.publish_settings_readback();self.publish()
            from .stacy_awareness import catch_up
            catch_up(self.kernel,limit=200)
            for request in ledger_control.pending(self.kernel):
                if request.get('desktop_id') not in (None,self.desktop_id):continue
                if time.time()-request['created']>30:
                    ledger_control.acknowledge(self.kernel,request,'EXPIRED','No desktop acknowledgment within 30 seconds');continue
                try:
                    if request['action']=='navigate':self.navigation()[request['args']['destination']]()
                    elif request['action']=='open':
                        path=self.kernel.safe(request['args']['path']);tab=self.host.open_document(path)
                        if tab is None:raise ValueError('Desktop did not open the requested file')
                    else:raise ValueError('Unknown presentation intent')
                    ledger_control.acknowledge(self.kernel,request,'OPENED')
                except (ValueError,KeyError,OSError,RuntimeError) as exc:ledger_control.acknowledge(self.kernel,request,'FAILED',str(exc))
            self.tail.refresh()
            current=self.host.tabs.currentWidget()
            if isinstance(current,SettingsTab):current.poll()
            for index in range(self.host.tabs.count()):
                tab=self.host.tabs.widget(index)
                if type(tab).__name__=='AwarenessTab':tab.refresh()
        except (ValueError,OSError,RuntimeError) as exc:self.host.statusBar().showMessage('Graphite control: '+activity.redact(exc),5000)

    def handle_text(self,text):
        try:actions=stacy_control.parse(text,self.kernel)
        except ValueError as exc:self.command_finished.emit(str(exc));return True
        if actions is None:return False
        self.run(actions);return True

    def run(self,actions,provider=False,private_local=False,when_done=None):
        if self.busy:
            self.command_finished.emit('A Graphite command is already being processed.');return
        if actions==[stacy_control.call('__master_stop__')]:self.host.master_stop_all();return
        scopes={'read','execute','approve'} if private_local else {'read','execute'}
        principal=Principal('desktop-owner',frozenset(scopes)) if provider else operator()
        try:stacy_control.validate_actions(actions,principal,provider=provider,private_local=private_local)
        except (ValueError,TypeError,KeyError) as exc:self.command_finished.emit('Not executed: '+str(exc));return
        epoch=self.host._operation_epoch;self.busy=True;self._when_done=when_done
        self.command_finished.emit('Running '+', '.join(a['operation'] for a in actions)+'…')
        def work():
            results=[]
            for action in actions:
                if epoch!=self.host._operation_epoch or self.host._closing:break
                arguments=dict(action['arguments'])
                if action['operation'] in ('ledger.navigate','ledger.open'):arguments['desktop_id']=self.desktop_id
                result=self.kernel.dispatch(action['operation'],arguments,principal)
                if epoch!=self.host._operation_epoch and action['operation']=='jobs.submit' and result.get('ok') and not refusal(result['result']):
                    self.kernel.dispatch('jobs.cancel',{'id':result['result']['id']},principal)
                if epoch!=self.host._operation_epoch and action['operation'] in ('ledger.navigate','ledger.open') and result.get('ok'):
                    ledger_control.acknowledge(self.kernel,result['result'],'CANCELLED','Master stop or closing interrupted the command')
                results.append({'operation':action['operation'],**result})
                if not result['ok']:break
            self.completed.emit(epoch,results)
        threading.Thread(target=work,daemon=True).start()

    def finished(self,epoch,results):
        self.busy=False;when_done=getattr(self,'_when_done',None);self._when_done=None
        if epoch!=self.host._operation_epoch or self.host._closing:return
        self.last_results=results
        for result in results:
            if result['operation']=='jobs.submit' and result.get('ok') and result['result'].get('tool','').startswith('cad.'):
                from .kicad_qt import KiCadTab
                for i in range(self.host.tabs.count()):
                    tab=self.host.tabs.widget(i)
                    if isinstance(tab,KiCadTab):tab.watch_job(result['result'])
            if result['operation']=='jobs.submit' and result.get('ok') and result['result'].get('tool','').startswith('kibot.'):
                from .kibot_qt import KiBotTab
                for i in range(self.host.tabs.count()):
                    tab=self.host.tabs.widget(i)
                    if isinstance(tab,KiBotTab):tab.watch_job(result['result'])
            if result['operation']=='jobs.submit' and result.get('ok') and result['result'].get('tool','').startswith('spice.'):
                from .spice_qt import SpiceTab
                for i in range(self.host.tabs.count()):
                    tab=self.host.tabs.widget(i)
                    if isinstance(tab,SpiceTab):tab.watch_job(result['result'])
            if result['operation']=='jobs.submit' and result.get('ok') and result['result'].get('tool','').startswith('yosys.'):
                from .yosys_qt import YosysTab
                for i in range(self.host.tabs.count()):
                    tab=self.host.tabs.widget(i)
                    if isinstance(tab,YosysTab):tab.watch_job(result['result'])
            if result['operation']=='jobs.submit' and result.get('ok') and result['result'].get('tool','').startswith(('nextpnr.','trellis.')):
                from .pnr_qt import ImplementationTab
                for i in range(self.host.tabs.count()):
                    tab=self.host.tabs.widget(i)
                    if isinstance(tab,ImplementationTab):tab.watch_job(result['result'])
            if result['operation']=='jobs.submit' and result.get('ok') and result['result'].get('tool','').startswith(('icarus.','verilator.','surfer.')):
                from .hdl_qt import HdlTab
                for i in range(self.host.tabs.count()):
                    tab=self.host.tabs.widget(i)
                    if isinstance(tab,HdlTab):tab.watch_job(result['result'])
        self.tick();self.command_finished.emit(stacy_control.describe_results(results))
        if when_done:when_done(results)


def install(host):
    bridge=host.ledger_bridge=LedgerBridge(host)
    add_navigation(host)
    from .organizer_qt import install as install_organizer
    install_organizer(bridge)
    return bridge


def add_navigation(host):
    parent=host._workspace_areas.get('ledger_active')
    if parent is None:return
    root=QTreeWidgetItem(['Settings']);root.setIcon(0,host.nav_icon('config'));root.setData(0,Qt.UserRole+2,'ledger_settings')
    root.setData(0,Qt.UserRole+4,'All settings');parent.insertChild(0,root)
    for category in ('Appearance','Slate','Workspace','Operations','Tools'):
        node=QTreeWidgetItem([{'Slate':'Assistant'}.get(category,category)]);node.setData(0,Qt.UserRole+2,'ledger_settings');node.setData(0,Qt.UserRole+4,category);root.addChild(node)  # GRAPHITE-01: shown as the settings root is (settings_registry.ROOT_NAMES); the category key stays
    from .navigator_catalog import LEGACY_WORKSPACES
    for title,destination in LEGACY_WORKSPACES:
        node=QTreeWidgetItem([title]);node.setData(0,Qt.UserRole+2,'ledger_control');node.setData(0,Qt.UserRole+4,destination);parent.insertChild(1 if destination=='commands' else 2,node)
    motherboard=next((item for item in host._nav_items() if item.data(0,Qt.UserRole+2)=='nav_device' and item.data(0,Qt.UserRole+4)=='pcb'),None)
    if motherboard is not None:
        node=QTreeWidgetItem(['KiCad · native checks']);node.setIcon(0,host.nav_icon('native_pcb'))
        node.setData(0,Qt.UserRole+2,'ledger_control');node.setData(0,Qt.UserRole+4,'cad');motherboard.insertChild(0,node)
        node=QTreeWidgetItem(['KiBot · BOM / fabrication']);node.setIcon(0,host.nav_icon('config'))
        node.setData(0,Qt.UserRole+2,'ledger_control');node.setData(0,Qt.UserRole+4,'kibot');motherboard.insertChild(1,node)
        node=QTreeWidgetItem(['ngspice · circuit checks']);node.setIcon(0,host.nav_icon('config'))
        node.setData(0,Qt.UserRole+2,'ledger_control');node.setData(0,Qt.UserRole+4,'spice');motherboard.insertChild(2,node)
        node=QTreeWidgetItem(['Yosys · FPGA synthesis']);node.setIcon(0,host.nav_icon('config'))
        node.setData(0,Qt.UserRole+2,'ledger_control');node.setData(0,Qt.UserRole+4,'yosys');motherboard.insertChild(3,node)
        node=QTreeWidgetItem(['nextpnr + Trellis · implementation']);node.setIcon(0,host.nav_icon('config'))
        node.setData(0,Qt.UserRole+2,'ledger_control');node.setData(0,Qt.UserRole+4,'implementation');motherboard.insertChild(4,node)
        node=QTreeWidgetItem(['HDL · simulation / waveforms']);node.setIcon(0,host.nav_icon('trace'))
        node.setData(0,Qt.UserRole+2,'ledger_control');node.setData(0,Qt.UserRole+4,'hdl');motherboard.insertChild(5,node)
