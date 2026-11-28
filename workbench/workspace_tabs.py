"""One central tab policy for every existing workspace factory."""
import json
from pathlib import PurePath
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabWidget, QPushButton, QMessageBox, QInputDialog, QPlainTextEdit

# Tabs that are made with the bridge (control_qt.LedgerBridge): it opens the Office and Graphite rooms, and the engineering
# conversation listens to it. The window installs the bridge after it has restored its session, so a saved row of one of
# these kinds cannot be opened then; it waits until the window is whole (WorkspaceTabs.restore, restore_waiting).
NEEDS_BRIDGE=('OfficeBuildingTab','SlateRoomTab','ClipWorkspaceTab')
# The tabs the desk opens by a place (shell2.open_destination), by kind: its rooms, and the tabs the bridge opens from its
# navigation. Until 0.8.4 restore knew none of them, nor the program rooms: each one left open was set aside at the next
# start, and set aside again at every start the owner opened it once more, so Reopen deferred tabs grew by one per such
# tab per start. They are reopened now, with what each needs of its row (descriptor: the folder Files was in, the kind the
# Library was showing; destination below), once the window is whole, as the bridge's rooms are: the Library is opened by
# the shell, the program rooms and the navigation's tabs by the bridge.
DESK_ROOMS={'DocumentsTab':'documents','TrashTab':'trash','AgendaTab':'agenda','ChangesTab':'changes','DeploymentTab':'deployment',
            'WorkTab':'continuing','InvestigationTab':'investigations'}
NAVIGATION={'DiscoveryTab':'discovery','AlgorithmAtlasTab':'algorithms','ToolAtlasTab':'atlas','CommandsTab':'commands','WorkTrailTab':'trail',
            'OrganizerTab':'organizer','PackageTab':'packages','View':'object_glass','BrainTab':'brain','IntakeTab':'intake','ReferenceTab':'references',
            'KnowledgeTab':'sources','MemoryTab':'memory','AwarenessTab':'stacy_awareness','DeveloperToolsTab':'developer_tools','KiBotTab':'kibot',
            'SpiceTab':'spice','YosysTab':'yosys','ImplementationTab':'implementation','HdlTab':'hdl','StacyFoundationTab':'stacy_knowledge'}
# What the screen calls each kind the desk opens (its tab's title, the same in every look), for a saved row without its title:
# 0.8.3 wrote none. A class name is not shown: StacyFoundationTab would read 'Stacy foundation' (0.8.4).
SHOWN_AS={'DocumentsTab':'Documents','FilesTab':'Files','LibraryTab':'Library','TrashTab':'DELETE','AgendaTab':'Agenda','ChangesTab':'Changes',
          'DeploymentTab':'Exchange & deployment','WorkTab':'Night Shift','InvestigationTab':'Investigations','ProjectDeskTab':'Project Desk',
          'OfficeBuildingTab':'Office','SlateRoomTab':'Graphite','ReturnTab':'Return thread','HostPanel':'Service details','ComputerTab':'This computer',
          'PillsTab':'Pills','CompareTab':'Compare','ExploreTab':'Explore','SettingsTab':'Settings','BlenderRoom':'Blender','CartridgeRoom':'Cartridge Bay',
          'DeliveryRoom':'Delivery','FreeCADRoom':'FreeCAD','GodotRoom':'Godot','InkscapeRoom':'Inkscape','MailRoom':'Mail','MediaRoom':'Media Bench',
          'PrintProofRoom':'Print Proof','TransferRoom':'Transfer','DiscoveryTab':'Inquiries','AlgorithmAtlasTab':'Algorithm & Theory Atlas',
          'ToolAtlasTab':'Tool Atlas','CommandsTab':'Graphite commands','WorkTrailTab':'Work trail','OrganizerTab':'Organizer','PackageTab':'Package desk',
          'View':'Object Glass','BrainTab':'Graphite · Brain','IntakeTab':'Graphite · Intake','ReferenceTab':'Graphite · References',
          'KnowledgeTab':'Graphite · Source connections','MemoryTab':'Graphite · Memory','AwarenessTab':'Graphite awareness',
          'DeveloperToolsTab':'Source assistance · Host debugger','KiBotTab':'KiBot · outputs','SpiceTab':'ngspice · circuits','YosysTab':'Yosys · synthesis',
          'ImplementationTab':'FPGA · route / pack','HdlTab':'HDL · simulation / traces','StacyFoundationTab':'Graphite · knowledge',
          'EngineeringTab':'Engineering · Jobs & Candidates','BrainLinkTab':'Brain Link','ClipWorkspaceTab':'Graphite · Engineering conversation',
          'GenesisTab':'ARC Concern · Genesis','RegisterTab':'Engineering Register','VendorTab':'Vendor Vault','DevelopmentTab':'Development Lab',
          'ManualTab':'R10 Manual','ReadinessTab':'Console Readiness','ToolInventoryTab':'Tool Inventory','ProjectSearchTab':'Project Search',
          'BoardViewerTab':'R10 Board Layers','QTextBrowser':'Installation Guide','PdfDocumentTab':'A PDF'}
# The saved kinds that are rooms: neither the Preview nor one of the five pins, so a Preview already open at a room's turn
# (one dragged to the left of it) does not set the room aside. The navigation's tabs are not rooms: one of them is a pin or
# the Preview, as it was when it was saved.
ROOMS=('OfficeBuildingTab','SlateRoomTab','ReturnTab','FilesTab','LibraryTab','HostPanel','ComputerTab','PillsTab')+tuple(DESK_ROOMS)
# Saved kinds with nothing to reopen: the legacy Start tab is the Home surface now, Files' start shows where to begin when
# nothing is open (open_record never reopened it, so it only sat in Reopen deferred tabs), and "Needs a project" explains
# why a project action did nothing; it is said again when the owner asks for project work and still has none attached.
NOTHING_TO_REOPEN=('StartPage','FilesStart','EmptyWorkspaceTab',
                   'UtilityTab')      # 1.0 K6: a utility's tab is not reopened at the next start (its utility and runs are kept)
KEPT=20      # Reopen deferred tabs keeps the twenty newest; until 0.8.4 it had no bound
WHERE='View → Reopen deferred tabs'      # the menu the item is in (menus2: the View group; 1.1 K0: under the title View, 1.0's Arrange)


def destination(row):
    """Where the desk goes to reopen a saved room (shell2.open_destination), or None for a row that is not one."""
    kind=row.get('kind')
    if kind=='FilesTab':return 'files:'+(row['folder'] if isinstance(row.get('folder'),str) else '')
    if kind=='LibraryTab':
        from .shell2 import KINDS
        return 'library:'+(row['library'] if isinstance(row.get('library'),str) and row['library'] in {key for key,_,_ in KINDS} else 'all')      # a damaged session's list is not looked up (TypeError)
    if kind in DESK_ROOMS:return DESK_ROOMS[kind]
    if kind in NAVIGATION:return NAVIGATION[kind]
    return program(kind)


def program(kind):
    """'program:<key>' for a program room's kind (program_rooms_qt.ROOMS), or None."""
    from .program_rooms_qt import ROOMS as PROGRAMS
    return next(('program:'+key for key,room in PROGRAMS.items() if room.__name__==kind),None)


def waits(row):
    """A row that is opened only once the window is whole (restore, restore_waiting)."""
    return row.get('kind') in NEEDS_BRIDGE or destination(row) is not None


def room(row):
    return row.get('kind') in ROOMS or program(row.get('kind')) is not None


def same(row):
    """What makes two saved rows one tab: not whether it was pinned, where its cursor was or what it was called; and a
    room is one room wherever it was looking."""
    return json.dumps({k:v for k,v in row.items() if k not in ('pinned','working','line','column','pdf_page','title','folder','library')},sort_keys=True,default=str)  # 1.0 L5: 'working'


def kept(rows,open_rows=()):
    """What Reopen deferred tabs keeps: each tab once (its newest row), none that is open as well, the newest KEPT."""
    taken={same(row) for row in open_rows};out=[]
    for row in reversed(rows):
        if not isinstance(row,dict) or row.get('kind') in NOTHING_TO_REOPEN or same(row) in taken:continue
        taken.add(same(row));out.append(row)
    return out[:KEPT][::-1]


def name(row):
    """A saved row as the owner reads it: the tab's title as it was shown, its file, what the screen calls its kind, or, for
    a kind this Graphite no longer opens, its kind in words, with her name where the code's words have the internal one."""
    if isinstance(row.get('title'),str) and row['title'].strip():return row['title'].strip()
    if isinstance(row.get('path'),str) and row['path']:return row['path'].rsplit('/',1)[-1]
    if row.get('kind') in SHOWN_AS:return SHOWN_AS[row['kind']]
    kind=str(row.get('kind') or 'A tab');kind=kind[:-3] if kind.endswith('Tab') and len(kind)>3 else kind
    words=''.join(' '+c.lower() if c.isupper() and i else c for i,c in enumerate(kind))
    from .assistant_identity import named
    return named(words[:1].upper()+words[1:])


class WorkspaceTabs(QTabWidget):
    def __init__(self, host):
        super().__init__(); self.host=host; self.replacing=False;self.last_open_cancelled=False
        self.deferred=[];self.waiting=[];self.restored=[];self.restore_active=None  # a session being restored (restore, restore_waiting)
        self.untold=[]      # (row, why) for each row this start set aside, said once at the end of the restore (tell)
        self.pin_button=QPushButton('Pin / Unpin')
        self.pin_button.setToolTip('Keep this workspace open · maximum five pins · workspaces opened from the menu or Explore are rooms and are not counted')
        self.pin_button.clicked.connect(self.toggle_pin)
        from .tool_faces import wear
        wear(self.pin_button)       # with icons it is a pin; its words are in its tip
        self.setCornerWidget(self.pin_button,Qt.TopRightCorner)
        self.tabBarDoubleClicked.connect(lambda i:self.pin(self.widget(i)))

    # Room tabs (Office, Slate, Files) stay open: they are neither the Preview nor one of the five pins.
    def pinned(self):
        return [self.widget(i) for i in range(self.count()) if self.widget(i).property('ledgerPinned') and not self.widget(i).property('ledgerRoom')]

    def preview(self):
        # 1.0 L5: a working tab (a view the navigation opened: the board, the tree, Search) is never the Preview
        return next((self.widget(i) for i in range(self.count()) if not self.widget(i).property('ledgerPinned') and not self.widget(i).property('ledgerRoom')
                     and not self.widget(i).property('ledgerWorking')),None)

    def working(self,widget,retitle=True):
        """1.0 L5: this view is a named working tab: it stays open beside the others; the next opening does not replace it."""
        if widget is None:return
        widget.setProperty('ledgerWorking',True)
        index=self.indexOf(widget)
        if retitle and index>=0:self.setTabText(index,widget.property('ledgerTitle') or self.tabText(index).replace('Preview · ','',1))

    def tabRemoved(self,index):
        super().tabRemoved(index)
        from .split_qt import tab_removed  # 1.0 L5: the pane in focus lost its last view while the other pane holds some: one pane again
        tab_removed(self.host)

    def setTabText(self,index,text):
        widget=self.widget(index)
        if widget is None:return
        widget.setProperty('ledgerTitle',text)
        if widget.property('ledgerRoom'):super().setTabText(index,text);return
        if widget.property('ledgerWorking') and not widget.property('ledgerPinned'):super().setTabText(index,text);return  # 1.0 L5: a working tab is named plainly
        super().setTabText(index,('◆ ' if widget.property('ledgerPinned') else 'Preview · ')+text)

    def dirty_choice(self,widget):
        box=QMessageBox(self);box.setWindowTitle('Keep your edited Preview')
        box.setText('Choose what to do before opening another item.')
        actions={}
        for label,key,role in [('Save and replace','save',QMessageBox.AcceptRole),
                               ('Pin and keep','pin',QMessageBox.ActionRole),
                               ('Discard with recovery copy','discard',QMessageBox.DestructiveRole),
                               ('Cancel','cancel',QMessageBox.RejectRole)]:
            actions[box.addButton(label,role)]=key
        box.exec();return actions.get(box.clickedButton(),'cancel')

    def release_preview(self):
        old=self.preview()
        if old is None:return True
        if isinstance(old,QPlainTextEdit) and old.document().isModified():
            choice=self.dirty_choice(old)
            if choice=='pin':return self.pin(old)
            if choice=='cancel':return False
            if choice=='save' and not self.host.save_document(old):return False
            if choice=='discard':
                self.host.recovery.put(old.path.relative_to(self.host.root).as_posix(),
                                       old.toPlainText(),old.disk_sha256)
                old.recovery_owned=False
                old.document().setModified(False)
        self.replacing=True
        try:return self.host.close_tab(self.indexOf(old))
        finally:self.replacing=False

    def addTab(self,widget,*args):
        self.last_open_cancelled=False
        if self.indexOf(widget)>=0:return self.indexOf(widget)
        from .split_qt import duplicate  # 1.0 L5: an object already open in the other pane is not opened twice: that pane comes into focus with it
        if duplicate(self.host,widget) is not None:
            widget.deleteLater();return -1
        if widget.property('ledgerRoom'):
            # Rooms sit at the left, in the order they were opened.
            rooms=sum(1 for i in range(self.count()) if self.widget(i).property('ledgerRoom'))
            index=super().insertTab(rooms,widget,*args);self.setTabText(index,args[-1]);return index
        if not self.release_preview():
            self.last_open_cancelled=True
            widget.deleteLater();return -1
        widget.setProperty('ledgerPinned',False)
        index=super().addTab(widget,*args)
        self.setTabText(index,args[-1]);return index

    def choose_replacement(self,pins):
        labels=[str(i+1)+'. '+str(w.property('ledgerTitle')) for i,w in enumerate(pins)]
        value,ok=QInputDialog.getItem(self,'Five pins are already open',
                                    'Choose a pin to close, or Cancel:',labels,0,False)
        return pins[labels.index(value)] if ok else None

    def pin(self,widget):
        if widget is None or self.indexOf(widget)<0:return False
        if widget.property('ledgerPinned'):return True
        pins=self.pinned()
        if len(pins)>=5:
            victim=self.choose_replacement(pins)
            if victim is None or not self.host.close_tab(self.indexOf(victim)):return False
        widget.setProperty('ledgerPinned',True)
        self.setTabText(self.indexOf(widget),widget.property('ledgerTitle') or '')
        return True

    def toggle_pin(self):
        widget=self.currentWidget()
        if widget is None:return
        if not widget.property('ledgerPinned'):self.pin(widget);return
        if not self.release_preview():return
        widget.setProperty('ledgerPinned',False)
        self.setTabText(self.indexOf(widget),widget.property('ledgerTitle') or '')

    def descriptor(self,widget):
        row={'kind':type(widget).__name__,'pinned':bool(widget.property('ledgerPinned'))}
        if widget.property('ledgerWorking'):row['working']=True  # 1.0 L5: a working tab reopens as one
        if isinstance(widget.property('ledgerTitle'),str) and widget.property('ledgerTitle'):row['title']=widget.property('ledgerTitle')      # its name in what restoring says
        if type(widget).__name__=='FilesTab' and isinstance(getattr(widget,'folder',None),str):row['folder']=widget.folder
        if type(widget).__name__=='LibraryTab' and isinstance(getattr(widget,'kind',None),str):row['library']=widget.kind
        if type(widget).__name__=='PdfDocumentTab' and widget.source.get('source_sha256'):
            row.update(pdf_namespace=widget.source['namespace'],pdf_item=widget.source['item'],pdf_sha256=widget.source['source_sha256'],pdf_page=widget.page_index)
        # A file's path. Only a path is one: Night Shift's 'path' is its chooser of a text path, and until 0.8.4 leaving
        # with Night Shift open raised here, so that session was not saved (as with the Manual's group, below).
        path=getattr(widget,'path',None)
        if isinstance(path,PurePath):
            try:row['path']=path.resolve().relative_to(self.host.root).as_posix()
            except ValueError:pass
        if widget.property('concern_id'):row['concern']=widget.property('concern_id')
        if widget.property('concern_context'):row['concern_context']=widget.property('concern_context')
        if hasattr(widget,'device'):row['device']=widget.device.id
        # A device group's name. Only text is one: the Manual's 'group' is its chooser, which has no title, and until 0.8.4
        # leaving with the Manual open raised here, so that session was not saved.
        group=getattr(getattr(widget,'group',None),'title',None)
        if isinstance(group,str):row['group']=group
        if hasattr(widget,'case'):row['case']=bool(widget.case)
        if hasattr(widget,'position'):row['line'],row['column']=widget.position()
        return row

    def snapshot(self):
        from .split_qt import other_tabs  # 1.0 L5: the other pane's views are kept with the session too
        tabs=[self.descriptor(self.widget(i)) for i in range(self.count())]+[self.descriptor(w) for w in other_tabs(self.host)]
        return dict(tabs=tabs,active=self.currentIndex(),deferred=kept(getattr(self,'deferred',[]),tabs))

    def open_record(self,row):
        if row.get('kind')=='ReturnTab':
            controller=getattr(self.host,'return_thread',None)
            return controller.show() if controller is not None else None
        if row.get('kind')=='PdfDocumentTab' and all(isinstance(row.get(k),str) for k in ('pdf_namespace','pdf_item','pdf_sha256')):
            from .pdf_qt import open_pdf
            return open_pdf(self.host,row['pdf_namespace'],row['pdf_item'],row['pdf_sha256'],row.get('pdf_page',0))
        if row.get('kind')=='ConcernDossier' and isinstance(row.get('concern'),str):
            return self.host.show_concern(row['concern'])
        if row.get('path'):
            tab=self.host.open_document(self.host.root/row['path'],remember=False)
            if tab and hasattr(tab,'go_to'):tab.go_to(row.get('line',1),row.get('column',1))
            return tab
        if row.get('device') in self.host._nav_devices:
            if row.get('group'):return self.host.show_device_group(row['device'],row['group'])
            return self.host.show_device(row['device'])
        methods={'GenesisTab':'show_genesis','BrainLinkTab':'show_brain_link','CandidateReviewTab':'show_parser_review','AssetGalleryTab':'show_asset_gallery','RegisterTab':'show_engineering_register',
                 'VendorTab':'show_vendor_vault','OrangeBookTab':'show_orange_book',
                 'DatabaseROMTab':'show_database_rom','VirtualConsoleTab':'show_arcos','ArcOSTab':'show_arcos_diagnostics','HardwareProofTab':'show_hardware_proof',
                 'EngineeringTab':'show_engineering','ClipWorkspaceTab':'show_clip_workspace',
                 'NativeGameTab':'show_native_game','ProjectDeskTab':'show_project_desk',
                 'DevelopmentTab':'show_development','ManualTab':'show_manual',
                 'ReadinessTab':'show_readiness','ToolInventoryTab':'show_tools',
                 'NorFlashTab':'show_nor','BoardViewerTab':'show_board','StartPage':'show_start',
                 'HardwareLedgerTab':'show_hardware_ledger','HardwareReviewTab':'show_hardware_review',
                 'ProjectSearchTab':'show_project_search'}
        if row.get('kind')=='AssemblyTab':return self.host.show_assembly(row.get('case',False))
        if row.get('kind')=='OfficeBuildingTab':return self.host.show_office()
        if row.get('kind')=='SlateRoomTab':return self.host.show_slate()
        if row.get('kind') in methods:return getattr(self.host,methods[row['kind']])()
        if row.get('kind')=='HostPanel' and hasattr(self.host,'a_host_service'):      # Background service (host_qt)
            self.host.a_host_service.trigger()
            return next((self.widget(i) for i in range(self.count()) if type(self.widget(i)).__name__=='HostPanel'),None)
        if row.get('kind')=='MachineRoom':      # 1.0 S4: a Machine page (Storage, Power, Network, Sound, Screens), by its title
            from .machine_room_qt import reopen
            return reopen(self.host,row)
        if row.get('kind')=='SystemSettingsRoom':      # 1.0 S5: a page of Settings ▸ This computer, by its title
            from .system_settings_qt import reopen as reopen_settings
            return reopen_settings(self.host,row)
        if row.get('kind') in ('ComputerTab','PillsTab'):      # This Computer, and Pills and Paired Computers (menus2)
            from importlib import import_module
            return import_module({'ComputerTab':'.computer_qt','PillsTab':'.pills_qt'}[row['kind']],__package__).show(self.host)
        if destination(row):
            from .shell2 import open_destination
            return open_destination(self.host,destination(row))
        return None

    def restore(self,state):
        """Open the tabs the session was saved with. A row whose tab is made with the bridge (NEEDS_BRIDGE) waits while
        the host has no bridge yet, and the rows after it wait with it, so every row still has its turn in the order it
        always had; restore_waiting opens them once the window is whole. 0.8.3 opened such a row at once, on a bridge
        that did not exist yet, and a session saved with the Office open stopped the next start (0.8.4)."""
        self.deferred=kept(list(state.get('deferred',[])));self.restore_active=state.get('active');self.restored=[];self.untold=[]
        # Pins first: a Preview may have been dragged before a pin in the strip.
        # Restoring that visual order directly would replace the Preview.
        self.waiting=sorted(enumerate(state.get('tabs',[])),key=lambda pair:not pair[1].get('pinned'))
        self.restore_rows(wait=not hasattr(self.host,'ledger_bridge'))

    def restore_waiting(self):
        """The rows that waited for the bridge, in their turn. One that still cannot be opened is kept in Reopen deferred tabs."""
        self.restore_rows(wait=False)

    def set_aside(self,row,why):
        self.deferred.append(row);self.untold.append((row,why))

    def restore_rows(self,wait):
        while self.waiting and not (wait and waits(self.waiting[0][1])):
            i,row=self.waiting.pop(0)
            if row.get('kind') in NOTHING_TO_REOPEN:continue
            if row.get('pinned') and len(self.pinned())>=5:self.set_aside(row,'five pins were already open');continue
            if not row.get('pinned') and not row.get('working') and not room(row) and self.preview() is not None:self.set_aside(row,'another tab was already in the Preview');continue  # 1.0 L5: working tabs are not the Preview
            why=None
            try:tab=self.open_record(row)
            except (KeyError,ValueError,OSError):tab=None;why='it is no longer there'
            except Exception:  # noqa: BLE001 - a former tab that cannot be opened must not stop start-up (0.8.4): it is kept, and why is printed
                import traceback
                traceback.print_exc();tab=None;why='it failed to open'
            if tab is None or self.indexOf(tab)<0:
                gone=any(row.get(k) for k in ('path','pdf_item','concern','device'))
                self.set_aside(row,why or ('it is no longer there' if gone else 'Graphite cannot reopen this kind of tab'));continue
            if isinstance(row.get('concern_context'),str):tab.setProperty('concern_context',row['concern_context'])
            if row.get('working') and not row.get('pinned'):self.working(tab)  # 1.0 L5
            if row.get('pinned'):self.pin(tab)
            self.restored.append((i,tab))
        self.restored=[(i,tab) for i,tab in self.restored if self.indexOf(tab)>=0]
        for position,(_,tab) in enumerate(sorted(self.restored,key=lambda pair:pair[0])):
            self.tabBar().moveTab(self.indexOf(tab),position)
        selected=next((tab for i,tab in self.restored if i==self.restore_active),None)
        if selected:self.setCurrentWidget(selected)
        if self.waiting:return
        self.restored=[]
        try:opened=[self.descriptor(self.widget(n)) for n in range(self.count())]
        except Exception:  # noqa: BLE001 - a tab that cannot be written down is met at leaving; it must not stop the start
            import traceback
            traceback.print_exc();opened=[]
        self.deferred=kept(self.deferred,opened)
        told,self.untold=[(row,why) for row,why in self.untold if any(row is kept_row for kept_row in self.deferred)],[]
        if told:self.tell(told)
        if self.deferred:
            self.host.statusBar().showMessage('%d former tabs retained in %s'%(len(self.deferred),WHERE),15000)

    def tell(self,told):
        """Say once, where the desk says what happened (the Activity, in every look), which saved tabs this start did not
        reopen and why, in words. Until 0.8.4 a reason went to stderr only, which the owner never sees in the full-screen
        session; the traceback still goes there, for whoever reads it."""
        words=['%s (%s)'%(name(row),why) for row,why in told[:4]]+(['%d more'%(len(told)-4)] if len(told)>4 else [])
        from . import activity
        activity.record(self.host.root,'DESKTOP','ledger.restore','SET_ASIDE','; '.join(words)+'. Kept in '+WHERE)

    def reopen_deferred(self):
        rows=getattr(self,'deferred',[])
        if not rows:return
        labels=[str(i+1)+'. '+name(r) for i,r in enumerate(rows)]
        label,ok=QInputDialog.getItem(self,'Retained workspace tabs','Open in Preview:',labels,0,False)
        if ok:
            row=rows[labels.index(label)];tab=self.open_record(row)
            if tab is not None and self.indexOf(tab)>=0:rows.remove(row)
