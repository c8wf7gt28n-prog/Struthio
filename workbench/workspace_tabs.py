"""One central tab policy for every existing workspace factory."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabWidget, QPushButton, QMessageBox, QInputDialog, QPlainTextEdit


class WorkspaceTabs(QTabWidget):
    def __init__(self, host):
        super().__init__(); self.host=host; self.replacing=False;self.last_open_cancelled=False
        self.pin_button=QPushButton('Pin / Unpin')
        self.pin_button.setToolTip('Keep this workspace open · maximum five pins · workspaces opened from the menu or Explore are rooms and are not counted')
        self.pin_button.clicked.connect(self.toggle_pin)
        self.setCornerWidget(self.pin_button,Qt.TopRightCorner)
        self.tabBarDoubleClicked.connect(lambda i:self.pin(self.widget(i)))

    # Room tabs (Office, Slate, Files) stay open: they are neither the Preview nor one of the five pins.
    def pinned(self):
        return [self.widget(i) for i in range(self.count()) if self.widget(i).property('ledgerPinned') and not self.widget(i).property('ledgerRoom')]

    def preview(self):
        return next((self.widget(i) for i in range(self.count()) if not self.widget(i).property('ledgerPinned') and not self.widget(i).property('ledgerRoom')),None)

    def setTabText(self,index,text):
        widget=self.widget(index)
        if widget is None:return
        widget.setProperty('ledgerTitle',text)
        if widget.property('ledgerRoom'):super().setTabText(index,text);return
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
        if type(widget).__name__=='PdfDocumentTab' and widget.source.get('source_sha256'):
            row.update(pdf_namespace=widget.source['namespace'],pdf_item=widget.source['item'],pdf_sha256=widget.source['source_sha256'],pdf_page=widget.page_index)
        path=getattr(widget,'path',None)
        if path:
            try:row['path']=path.resolve().relative_to(self.host.root).as_posix()
            except ValueError:pass
        if widget.property('concern_id'):row['concern']=widget.property('concern_id')
        if widget.property('concern_context'):row['concern_context']=widget.property('concern_context')
        if hasattr(widget,'device'):row['device']=widget.device.id
        if hasattr(widget,'group'):row['group']=widget.group.title
        if hasattr(widget,'case'):row['case']=bool(widget.case)
        if hasattr(widget,'position'):row['line'],row['column']=widget.position()
        return row

    def snapshot(self):
        return dict(tabs=[self.descriptor(self.widget(i)) for i in range(self.count())],
                    active=self.currentIndex(),deferred=getattr(self,'deferred',[]))

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
        if row.get('kind')=='FilesStart':return None
        if row.get('kind') in methods:return getattr(self.host,methods[row['kind']])()
        return None

    def restore(self,state):
        self.deferred=list(state.get('deferred',[]));selected=None;opened=[]
        # Pins first: a Preview may have been dragged before a pin in the strip.
        # Restoring that visual order directly would replace the Preview.
        records=list(enumerate(state.get('tabs',[])))
        for i,row in sorted(records,key=lambda pair:not pair[1].get('pinned')):
            # Legacy Start tabs are now the separate Home surface, not a pin.
            if row.get('kind')=='StartPage':continue
            if (row.get('pinned') and len(self.pinned())>=5) or (not row.get('pinned') and self.preview() is not None):
                self.deferred.append(row);continue
            try:tab=self.open_record(row)
            except (KeyError,ValueError,OSError):tab=None
            if tab is None or self.indexOf(tab)<0:self.deferred.append(row);continue
            if isinstance(row.get('concern_context'),str):tab.setProperty('concern_context',row['concern_context'])
            if row.get('pinned'):self.pin(tab)
            opened.append((i,tab))
            if i==state.get('active'):selected=tab
        for position,(_,tab) in enumerate(sorted(opened,key=lambda pair:pair[0])):
            self.tabBar().moveTab(self.indexOf(tab),position)
        if selected:self.setCurrentWidget(selected)
        if self.deferred:
            self.host.statusBar().showMessage('%d former tabs retained in View → Reopen deferred tabs'%len(self.deferred),15000)

    def reopen_deferred(self):
        rows=getattr(self,'deferred',[])
        if not rows:return
        labels=[str(i+1)+'. '+str(r.get('path') or r.get('device') or r.get('kind')) for i,r in enumerate(rows)]
        label,ok=QInputDialog.getItem(self,'Retained workspace tabs','Open in Preview:',labels,0,False)
        if ok:
            row=rows[labels.index(label)];tab=self.open_record(row)
            if tab is not None and self.indexOf(tab)>=0:rows.remove(row)
