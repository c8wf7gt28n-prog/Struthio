"""Compact records browser and durable archive queue in the existing workspace."""
from .text_prompts import writing_prompt
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QHBoxLayout,QGridLayout,QLabel,QLineEdit,QPushButton,
    QTabWidget,QTreeWidget,QTreeWidgetItem,QTextBrowser,QSplitter,QWidget,QVBoxLayout,
    QFileDialog,QInputDialog)
from .register_tabs import ServiceTab, esc
from .database_rom import select
from .ux_polish import overline
from sdk.cli.arc1cli.record_store import atomic,sha,inside


class DatabaseROMTab(ServiceTab):
    def __init__(self,host):
        super().__init__(host);self.last_operation=""
        row=QHBoxLayout();row.addWidget(overline("Database ROM"));self.find=QLineEdit("reset timing")
        writing_prompt(self.find, "Search indexed records, parts or history");self.find.returnPressed.connect(self.search);row.addWidget(self.find,1)
        b=QPushButton("Search");b.clicked.connect(self.search);row.addWidget(b);self.outer.addLayout(row);self.outer.addWidget(self.status)
        self.pages=QTabWidget();self.outer.addWidget(self.pages,1)
        library=QWidget();layout=QVBoxLayout(library)
        self.hits=QTreeWidget();self.hits.setHeaderLabels(["Record","Page","Original","Excerpt"])
        self.hits.setColumnWidth(0,240);self.hits.setColumnWidth(1,55);self.hits.setColumnWidth(2,120);self.hits.itemSelectionChanged.connect(self.selected)
        self.detail=QTextBrowser();self.detail.setOpenLinks(False);self.detail.setOpenExternalLinks(False)
        split=QSplitter(Qt.Vertical);split.addWidget(self.hits);split.addWidget(self.detail);split.setSizes([230,320]);layout.addWidget(split,1)
        buttons=QGridLayout()
        for i,(label,method) in enumerate((("Attach volume",self.attach),("Open verified original",self.open_original),("Hardware research",self.research),("Refresh catalog",self.refresh))):
            b=QPushButton(label);b.clicked.connect(method);buttons.addWidget(b,i//2,i%2)
        layout.addLayout(buttons);self.pages.addTab(library,"Library")
        queue=QWidget();layout=QVBoxLayout(queue)
        note=QLabel("Staged records survive restarts. Prepare a volume, write it, then verify it and a second copy before clearing staging.");note.setWordWrap(True);layout.addWidget(note)
        self.queue=QTreeWidget();self.queue.setHeaderLabels(["Queue","State","Records","Bytes"]);self.queue.setColumnWidth(0,190);self.queue.setColumnWidth(1,245);layout.addWidget(self.queue,1)
        buttons=QGridLayout()
        for i,(label,method) in enumerate((("Queue output files",self.stage),("Prepare selected volume",self.prepare),("Clear verified staging",self.clear))):
            b=QPushButton(label);b.clicked.connect(method);buttons.addWidget(b,i//2,i%2)
        layout.addLayout(buttons);self.pages.addTab(queue,"Archive queue")
        QTimer.singleShot(0,self.refresh)
    def title(self):return "Database ROM"
    def refresh(self):self.call("records.status",{},self.loaded)
    def loaded(self,data):
        rows=data["volumes"];total=sum(r["records"] for r in rows)
        scope='Full text cached separately.' if rows[0].get('index_scope')=='FULL_SEALED_TEXT' else 'Small catalog and research index; attach ROM for full text.'
        self.status.setText("%d sealed volume(s) / %d records / %.0f MB allowance. %s"%(len(rows),total,rows[0]["budget_bytes"]/1e6,self.last_operation or scope))
        self.queue.clear()
        for row in data["pending"]:
            item=QTreeWidgetItem([row["id"][:16],row["state"],str(row["records"]),str(row["bytes"])]);item.setData(0,Qt.UserRole,row);self.queue.addTopLevelItem(item)
        self.search()
    def search(self):self.call("records.search",{"query":self.find.text(),"limit":30},self.searched)
    def searched(self,data):
        self.hits.clear()
        for row in data["hits"]:
            item=QTreeWidgetItem([row["record_id"],row["page_label"],row["original_state"],row["excerpt"]]);item.setData(0,Qt.UserRole,row);item.setToolTip(0,row["record_id"]);self.hits.addTopLevelItem(item)
        if self.hits.topLevelItemCount():self.hits.setCurrentItem(self.hits.topLevelItem(0))
        else:self.detail.setHtml("<h2>No matching indexed records</h2><p>Try a part number, pinout, clock or a pass number. Missing native text remains an extraction gap.</p>")
    def selected(self):
        item=self.hits.currentItem()
        if not item:return
        row=item.data(0,Qt.UserRole)
        self.call("records.page",{k:row[k] for k in ("record_id","volume_id","page_index")},self.show_page)
    def show_page(self,row):
        if row['record_id'].endswith('.md'):
            text=row['text'];start=text.find('\n# ');text=text[start+1:] if start>=0 else text
            self.detail.setMarkdown(row['volume_id']+' / '+row['original_state']+'\n\n'+text+'\n\nSource SHA-256: '+row['source_sha256']);return
        kind='Catalog metadata' if row.get('content_state')=='CATALOG_METADATA' else 'Sealed indexed text'
        self.detail.setHtml("<h2>"+esc(row["record_id"])+"</h2><p>"+esc(row["volume_id"])+" / page "+esc(row["page_label"])+" / "+esc(row["original_state"])+"</p><p>"+kind+". Engineering applicability and approval remain in the current register.</p><pre style='white-space:pre-wrap'>"+esc(row["text"])+"</pre><p style='font-size:10px'>SHA-256 "+esc(row["source_sha256"])+"</p>")
    def attach(self):
        path=QFileDialog.getExistingDirectory(self,"Select mounted Database ROM or verified records folder")
        if path:
            self.status.setText("Verifying complete volume before attaching...")
            self.call("records.attach",{"path":path},lambda r:self.finished("Attached "+r["volume_id"]+"; logical readback verified."))
    def finished(self,text):self.last_operation=text;self.refresh()
    def open_original(self):
        item=self.hits.currentItem()
        if not item:return
        try:
            row=item.data(0,Qt.UserRole);store=select(self.host.root,row["volume_id"]);location=store.locate(row["record_id"])
            if location["path"] is None:self.status.setText("Insert "+row["volume_id"]+" or attach a verified records copy.");return
            if Path(row["record_id"]).suffix.lower() not in ('.pdf','.txt','.md','.json','.csv','.png','.jpg','.jpeg','.html'):
                self.status.setText("Use SDK locate for this binary or source record; it is not launched by the records browser.");return
            # A named private cache gives the OS the original PDF/text extension.
            target=inside(store.private,"open/"+location["sha256"]+"/"+Path(row["record_id"]).name)
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.is_file() or sha(target)!=location["sha256"]:
                atomic(target,location["path"].read_bytes())
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        except (OSError,ValueError) as exc:self.status.setText(str(exc))
    def research(self):
        self.call("records.page",{"record_id":"research/HARDWARE_RESEARCH_REPORT.md","page_index":0},self.show_page)
    def stage(self):
        paths,_=QFileDialog.getOpenFileNames(self,"Queue completed outputs or incoming reference records",str(self.host.root/"build"))
        if not paths:return
        try:names=[Path(p).resolve().relative_to(self.host.root.resolve()).as_posix() for p in paths]
        except ValueError:self.status.setText("Choose project build outputs or project/records/incoming files.");return
        self.call("records.stage",{"paths":names},lambda r:self.finished("Queued %d records; originals preserved."%len(r["records"])))
    def queue_row(self):
        item=self.queue.currentItem()
        if not item:self.status.setText("Select an archive queue entry.");return None
        return item.data(0,Qt.UserRole)
    def prepare(self):
        row=self.queue_row()
        if not row:return
        ident,ok=QInputDialog.getText(self,"New sealed volume","Unique volume ID:",text="ARC-ROM-002")
        if ok:self.call("records.prepare",{"queue_id":row["id"],"volume_id":ident},lambda r:self.finished("Prepared "+r["volume_id"]+" at "+r["folder"]))
    def clear(self):
        row=self.queue_row()
        if not row:return
        first=QFileDialog.getExistingDirectory(self,"Select written volume for complete readback")
        if not first:return
        second=QFileDialog.getExistingDirectory(self,"Select independent backup copy for complete readback")
        if second:self.call("records.clear_staging",{"queue_id":row["id"],"primary_path":first,"backup_path":second},lambda r:self.finished("Staging cleared after two readbacks; active source files preserved."))
