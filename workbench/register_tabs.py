"""Contextual Qt register, vendor and book workspaces over the shared kernel."""
from __future__ import annotations
from .text_prompts import writing_prompt
import html
import json
import os
from pathlib import Path
import shutil
import uuid
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Qt
from shiboken6 import isValid
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QSizePolicy, QLabel, QPushButton, QLineEdit, QTreeWidget, QTreeWidgetItem, QTabWidget, QTextBrowser, QComboBox, QCheckBox, QFileDialog, QSplitter
from .engine import engineering
from .engineering_kernel import operator
from .project_context import refusal
from . import record_io as io
from .command_rows import fold
from .ux_polish import overline, readable_error, empty_hint
from . import locations


def esc(value): return html.escape(str(value))


def icon(root, name):
    from .ux_assets import icon as themed
    found=themed(root,name)
    return found if not found.isNull() else QIcon(str(locations.program(root) / "branding/ux16" / (name + ".svg")))


class Call(QThread):
    ready = Signal(object)
    def __init__(self, kernel, op, params, principal, parent):
        super().__init__(parent); self.kernel=kernel; self.op=op; self.params=params; self.principal=principal
    def run(self):
        try: result=self.kernel.dispatch(self.op, self.params, self.principal)
        except Exception as exc: result={"ok":False,"error":{"message":str(exc)}}
        self.ready.emit(result)


class ServiceTab(QWidget):
    def __init__(self, host):
        super().__init__(); self.host=host; self.kernel=engineering(host.root); self.principal=operator(); self.workers=[];self.stopping=False
        if not hasattr(host,'service_workers'):host.service_workers=[]
        self.outer=QVBoxLayout(self); self.status=QLabel(); self.status.setWordWrap(True)
    def call(self, op, params, done, failed=None):
        if self.stopping or self.host._closing:return None
        epoch=getattr(self.host,'_operation_epoch',0)
        worker=Call(self.kernel,op,params,self.principal,self.host);self.workers.append(worker);self.host.service_workers.append(worker)
        def result(r):
            if self.stopping or self.host._closing or not isValid(self) or epoch!=getattr(self.host,'_operation_epoch',0):return
            if not r.get("ok"):
                message=r.get("error",{}).get("message","Operation failed")
                self.status.setText(readable_error(message,self.host.root));self.status.setToolTip(message)
                if failed:failed(r.get("error",{}))
                return
            if isinstance(r['result'],dict) and r['result'].get('status')=='PROJECT_NOT_ATTACHED':
                self.status.setText('PROJECT NOT ATTACHED · original work is sealed separately. Project intake is Pass 4.')
                return
            done(r["result"])
        worker.ready.connect(result)
        worker.finished.connect(lambda:self.workers.remove(worker) if worker in self.workers else None)
        worker.finished.connect(lambda:self.host.service_workers.remove(worker) if worker in self.host.service_workers else None)
        worker.finished.connect(worker.deleteLater);worker.start();return worker
    def submit(self, tool, done=None, request_key=None):
        self.status.setText("Submitting " + tool + " through the Engineering Kernel…")
        def submitted(job):
            self.status.setText("Job " + job["id"][:12] + " · " + job["state"])
            self.pending_job=job["id"]
            self.job_timer=QTimer(self);self.job_timer.setInterval(700)
            def poll():
                r=self.kernel.dispatch("jobs.get",{"id":job["id"]},self.principal)
                if not r["ok"]:return
                j=r["result"];self.status.setText(tool + " · " + j["state"])
                if j["state"] in ("Completed","Failed","Cancelled","Interrupted"):
                    self.job_timer.stop()
                    if done:done(j)
            self.job_timer.timeout.connect(poll);self.job_timer.start()
        return self.call("jobs.submit",{"tool":tool,"request_key":request_key or uuid.uuid4().hex,"timeout":300},submitted)
    def shutdown_engineering(self):
        self.stopping=True
        if hasattr(self,"job_timer"):self.job_timer.stop()
        for worker in list(self.workers):worker.wait(10000)


class RegisterTab(ServiceTab):
    def __init__(self, host):
        super().__init__(host);self.data=None;self.workbook_args=None;self.pending_preview=None
        row=QHBoxLayout();row.addWidget(overline("Engineering Register"))
        self.find=QLineEdit();writing_prompt(self.find, "Find a requirement, component or action");row.addWidget(self.find,1)
        refresh=QPushButton(icon(host.root,"refresh"),"Refresh");refresh.clicked.connect(self.refresh);row.addWidget(refresh);self.outer.addLayout(row)
        self.outer.addWidget(self.status)
        self.pages=QTabWidget();self.trees={}
        for kind in ("requirements","evidence","actions","objects"):
            tree=QTreeWidget();tree.setHeaderLabels(["ID","Statement or description","State","Source"]);empty_hint(tree,"Reading the source-bound register…");tree.setColumnWidth(0,205);tree.setColumnWidth(1,360);tree.setColumnWidth(2,190)
            tree.itemSelectionChanged.connect(lambda k=kind:self.select(k));self.trees[kind]=tree;self.pages.addTab(tree,kind.title())
        self.detail=QTextBrowser();self.detail.setOpenExternalLinks(False);self.detail.setOpenLinks(False);self.detail.setMinimumHeight(190)
        split=QSplitter(Qt.Vertical);split.addWidget(self.pages);split.addWidget(self.detail);split.setSizes([340,250]);self.outer.addWidget(split,1)
        self.action_layout=QGridLayout();self.action_buttons=[];self.action_columns=None
        for label,name,fn in [("Run core DC analysis","power-rail",lambda:self.submit("register.analyze_power",lambda j:self.refresh())),("Export JSON and XLSX","export",self.export), ("Preview workbook changes","import",self.preview), ("Create text candidate","candidate",self.propose), ("Brain Link","brain-link",self.open_brain_link), ("Orange Book","page-link",host.show_orange_book)]:
            button=QPushButton(icon(host.root,name),label);button.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Fixed);button.clicked.connect(fn);self.action_buttons.append(button)
        self.action_buttons=fold(None,keep=("Export JSON and XLSX","Preview workbook changes","Create text candidate"),buttons=self.action_buttons)
        self.outer.addLayout(self.action_layout);self.arrange_actions()
        self.find.textChanged.connect(self.populate)
        QTimer.singleShot(0,self.refresh)
    def title(self):return "Engineering Register"
    def arrange_actions(self):
        available=self.width()-self.outer.contentsMargins().left()-self.outer.contentsMargins().right()
        width=max(b.sizeHint().width() for b in self.action_buttons)
        gap=max(0,self.action_layout.horizontalSpacing())
        columns=4 if available>=width*4+gap*3 else 3 if available>=width*3+gap*2 else 2 if available>=width*2+gap else 1
        if columns==self.action_columns:return
        self.action_columns=columns
        for i,button in enumerate(self.action_buttons):
            self.action_layout.removeWidget(button);self.action_layout.addWidget(button,i//columns,i%columns)
        for i in range(4):self.action_layout.setColumnStretch(i,1 if i<columns else 0)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,"action_buttons"):self.arrange_actions()
    def refresh(self):
        self.status.setText("Reading current source bindings…")
        self.call("register.inspect",{},self.loaded)
    def loaded(self,data):
        self.data=data;self.status.setText("%d requirements · %d actions · source %s · fabrication HOLD"%(len(data["requirements"]),len(data["actions"]),data["source_catalog_revision"][:12]));self.populate()
        if hasattr(self,'requested_focus'):
            self.focus_record(*self.requested_focus);return
        tree=self.trees["requirements"]
        for i in range(tree.topLevelItemCount()):
            item=tree.topLevelItem(i)
            if item.text(0)=="REQ-R10-CORE-SUPERVISION":tree.setCurrentItem(item);tree.scrollToItem(item);break
    def focus_record(self,query,kind='requirements'):
        self.requested_focus=(query,kind);self.find.setText(query)
        tree=self.trees[kind];self.pages.setCurrentWidget(tree)
        if tree.topLevelItemCount():tree.setCurrentItem(tree.topLevelItem(0))
    def populate(self):
        if not self.data:return
        query=self.find.text().casefold()
        for kind,tree in self.trees.items():
            tree.clear()
            empty_hint(tree,'No %s match “%s”.'%(kind,self.find.text()) if query else 'No %s recorded in this register snapshot.'%kind)
            for row in self.data[kind]:
                if query and query not in json.dumps(row).casefold():continue
                state=row.get("currency") or row.get("fulfillment") or row.get("status") or row.get("state") or "SOURCE"
                if kind=="evidence":state=(row.get("outcome") or "Not run")+" / "+row["currency"]
                refs=row.get("source_refs",[])
                item=QTreeWidgetItem([row["record_id"],row.get("statement") or row.get("summary") or row.get("value") or "",state,refs[0]["path"] if refs else ""]);item.setData(0,Qt.UserRole,row);tree.addTopLevelItem(item)
    def select(self,kind):
        item=self.trees[kind].currentItem()
        if item is None:return
        row=item.data(0,Qt.UserRole)
        if kind=='requirements' and hasattr(self.host,'select_object'):self.host.select_object({'kind':'requirement','target':row['record_id']},principal=self.principal,origin=self)
        body="<h2>"+esc(row["record_id"])+"</h2>"
        for k in ("statement","acceptance_criterion","summary","owner","status","outcome","currency","target_status","footprint","native_uuid"):
            if row.get(k) is not None:body+="<p><b>"+esc(k.replace("_"," ").title())+"</b> "+esc(row[k])+"</p>"
        if row.get("check_plan_refs"):body+="<p><b>Check plans</b> "+esc(", ".join(row["check_plan_refs"]))+"</p>"
        if row.get("object_refs"):body+="<p><b>Native objects</b> "+esc(", ".join(row["object_refs"]))+"</p>"
        if row["record_id"]=="REQ-R10-CORE-SUPERVISION" and self.data:
            body+="<h3>Current calculation</h3><p>Design calculation only. Dynamic and physical qualification remain open.</p><table border='1' cellpadding='5'><tr><th>Quantity</th><th>mV</th><th>Currency</th></tr>"
            for q in self.data["quantities"]:body+="<tr><td>"+esc(q["record_id"])+"</td><td>%.3f</td><td>"% (float(q["value_decimal"])*1000)+esc(q["currency"])+"</td></tr>"
            body+="</table>"
        if row.get("pins"):
            body+="<h3>Native pin map</h3><table border='1' cellpadding='4'><tr><th>Pin</th><th>Function</th><th>Net</th></tr>"+"".join("<tr><td>"+esc(p["pin"])+"</td><td>"+esc(p["function"])+"</td><td>"+esc(p["net"])+"</td></tr>" for p in row["pins"])+"</table>"
        body+="<h3>Owning sources</h3>"
        for ref in row.get("source_refs",[]):body+="<p>"+esc(ref["path"])+"<br>"+esc(ref.get("locator",""))+"<br><small>SHA-256 "+esc(ref.get("sha256"))+"</small></p>"
        self.detail.setHtml(body)
    def export(self):
        directory=QFileDialog.getExistingDirectory(self,"Save register snapshots")
        if not directory:return
        def saved(result):
            for entry in result["files"]:
                source=io.project_path(self.host.root,entry["path"],private=True)
                shutil.copyfile(source,Path(directory)/source.name)
            self.last_export=result;self.status.setText("Saved private JSON and XLSX snapshots · export "+result["export_id"][:12]+" · edit text, then preview")
        self.call("register.export",{},saved)
    def preview(self):
        path,_=QFileDialog.getOpenFileName(self,"Preview workbook changes","","Register workbook (*.xlsx)")
        if not path:return
        if Path(path).stat().st_size>20*1024*1024:self.status.setText("Workbook exceeds the 20 MiB import profile");return
        from .register_exchange import read_xlsx
        try:
            meta={r["key"]:r["value"] for r in read_xlsx(Path(path))["Meta"]}
            rel="build/register/imports/"+uuid.uuid4().hex+".xlsx";dest=io.project_path(self.host.root,rel,False);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
        except Exception as exc:self.status.setText(str(exc));return
        def shown(result):
            self.pending_preview=result
            self.workbook_args={"export_id":meta.get("export_id",""),"path":rel}
            self.status.setText(result["status"]+" · source writes 0")
            self.detail.setHtml("<h2>Workbook proposal preview</h2><pre>"+esc(json.dumps(result,indent=2))+"</pre>")
        self.call("register.preview",{"export_id":meta.get("export_id",""),"path":rel},shown)


    def propose(self):
        if not self.workbook_args or not self.pending_preview or self.pending_preview.get('status')!='PREVIEW' or not self.pending_preview.get('changes'):
            self.status.setText('Preview a nonempty workbook text change before creating a candidate.');return
        def created(result):
            self.status.setText('Text candidate '+result['candidate_id'][:12]+' · accepted source writes 0 · owner review required')
            self.detail.setHtml('<h2>Workbook text candidate</h2><p>Review the diff in Engineering Jobs and Candidates and authorize execution for this exact revision. Run register.validate_text on baseline and candidate, then review and accept or reject.</p><pre>'+esc(json.dumps(result,indent=2))+'</pre>')
        self.call('register.propose',self.workbook_args,created)
    def open_brain_link(self):
        ref='J14'
        current=self.pages.currentIndex();kind=list(self.trees)[current] if 0<=current<len(self.trees) else 'requirements'
        item=self.trees[kind].currentItem()
        if item:
            row=item.data(0,Qt.UserRole)
            if row['record_id'].startswith('R10:'):ref=row['record_id'][4:]
            elif row.get('object_refs'):ref=row['object_refs'][0].removeprefix('R10:')
        if not self.host.tabs.pin(self):return
        tab=self.host.show_brain_link()
        if tab and tab.component.count():tab.choose(ref)
        elif tab:QTimer.singleShot(250,lambda:tab.choose(ref))


class VendorTab(ServiceTab):
    def __init__(self,host):
        super().__init__(host);self.document=None
        row=QHBoxLayout();row.addWidget(overline("Vendor Vault"));self.find=QLineEdit("tCEM");writing_prompt(self.find, "Search exact vendor sources");self.find.returnPressed.connect(self.search);row.addWidget(self.find,1)
        b=QPushButton(icon(host.root,"search"),"Search");b.clicked.connect(self.search);row.addWidget(b)
        b=QPushButton(icon(host.root,"build"),"Build index");b.clicked.connect(lambda:self.submit("vendor.refresh",lambda j:self.refresh()));row.addWidget(b);self.outer.addLayout(row);self.outer.addWidget(self.status)
        self.hits=QTreeWidget();self.hits.setHeaderLabels(["Document","Page","Original","Fact state","Excerpt"]);self.hits.setColumnWidth(0,160);self.hits.setColumnWidth(1,55);self.hits.setColumnWidth(2,90);self.hits.setColumnWidth(3,135);self.hits.itemSelectionChanged.connect(self.page)
        self.detail=QTextBrowser();self.detail.setOpenLinks(False);self.detail.setOpenExternalLinks(False)
        split=QSplitter(Qt.Vertical);split.addWidget(self.hits);split.addWidget(self.detail);split.setSizes([210,360]);self.outer.addWidget(split,1)
        row=QHBoxLayout();b=QPushButton(icon(host.root,"source-fact"),"Verify page in original");b.clicked.connect(lambda:self.page(True));row.addWidget(b)
        b=QPushButton(icon(host.root,"fact-review"),"Show fact review states");b.clicked.connect(self.facts);row.addWidget(b);row.addStretch();self.outer.addLayout(row)
        QTimer.singleShot(0,self.refresh)
    def title(self):return "Vendor Vault"
    def refresh(self):self.call("vendor.status",{},self.loaded)
    def loaded(self,data):
        if data["status"]!="AVAILABLE":self.status.setText("Index unavailable · "+data.get("reason",""));return
        meta=data["meta"];self.status.setText("%s documents · %s pages · %s · private originals"%(meta["document_count"],meta["page_count"],meta.get("pin_profile","F00 original pins")));self.search()
    def search(self):
        if not self.find.text().strip():return
        self.call("vendor.search",{"query":self.find.text(),"limit":20},self.searched)
    def searched(self,data):
        self.hits.clear()
        for h in data["hits"]:
            item=QTreeWidgetItem([h["document_id"],h["page_label"],h["source_state"],h["fact_state"],h["snippet"]]);item.setData(0,Qt.UserRole,h);self.hits.addTopLevelItem(item)
        if self.hits.topLevelItemCount():self.hits.setCurrentItem(self.hits.topLevelItem(0))
        else:self.detail.setHtml("<h2>No matching pages</h2><p>Try a vendor term or select a different query.</p>")
    def page(self,original=False):
        item=self.hits.currentItem()
        if item is None:return
        h=item.data(0,Qt.UserRole);self.call("vendor.page",{"document_id":h["document_id"],"page_index":h["page_index"],"original":bool(original)},self.show_page)
    def show_page(self,data):
        p=data["page"];d=data["document"];self.document=d
        text=p.get("page_text",p.get("text",""));hazards=p.get("hazards",p.get("extraction_hazards",[]))
        self.detail.setHtml("<h2>"+esc(d["title"])+"</h2><p>Revision "+esc(d["revision"])+" · printed page "+esc(p["page_label"])+" · "+esc(d["source_state"])+" · "+esc(d["rights"])+"</p><p><b>EXTRACTED_TEXT</b> · search content is not an approved engineering value.</p><p><small>SHA-256 "+esc(d["source_sha256"])+"</small></p>"+("<p>Extraction hazards: "+esc(hazards)+"</p>" if hazards else "")+"<pre>"+esc(text)+"</pre>")
    def facts(self):
        def show(data):self.detail.setHtml("<h2>Fact review states</h2><pre>"+esc(json.dumps(data["facts"],indent=2,ensure_ascii=False))+"</pre>")
        self.call("vendor.facts",{},show)


class BookAutoWatcher(QObject):
    refreshed=Signal(object)
    def __init__(self,host):
        super().__init__(host);self.host=host;self.kernel=engineering(host.root);self.principal=operator();self.active=False;self.worker=None;self.signature=None;self.attempted=set();self.last_status=None;self.last_error=None
        self.timer=QTimer(self);self.timer.setInterval(2500);self.timer.timeout.connect(self.check)
        flag=io.project_path(host.root,".ledger/orange_book_enabled.json",False,private=True)
        try:
            enabled=io.strict_json(flag.read_bytes()).get("auto_refresh",True) if flag.is_file() else io.load(host.root,"docs/orange_book/bindings.json").get("auto_export_default",True)
            if type(enabled) is not bool:raise ValueError("Preference must be a boolean")
        except (ValueError,OSError,AttributeError) as exc:
            enabled=False;self.last_error="Automatic-update preference unreadable; enable updates to reset it: "+str(exc)
        self.active=bool(enabled) and not os.environ.get("ARC_LEDGER_DISABLE_BOOK_WATCHER")
        self.timer.start()
    def activate(self,enabled=True):
        self.active=enabled and not os.environ.get("ARC_LEDGER_DISABLE_BOOK_WATCHER")
        flag=io.project_path(self.host.root,".ledger/orange_book_enabled.json",False,private=True)
        io.write_json(flag,{"auto_refresh":bool(enabled),"exports":True})
        if self.active:self.signature=None;self.check()
    def check(self):
        if not self.active or self.host._closing or self.worker is not None:return
        try:
            from .orange_book import watch_signature
            signature=watch_signature(self.host.root)
            if signature==self.signature and self.last_status and self.last_status.get("exports_current"):return
        except Exception as exc:self.last_error=str(exc);return
        self.signature=signature
        worker=Call(self.kernel,"book.status",{},self.principal,self);self.worker=worker
        def done(r):
            if not self.active or self.host._closing:return
            if not r.get("ok"):self.last_error=r.get("error",{}).get("message");return
            status=r["result"];self.last_status=status;self.last_error=None;self.refreshed.emit(status)
            stamp=status["input_fingerprint"]
            if status.get("exports_current") or stamp in self.attempted:return
            # Shared scheduler stays authoritative. An active user job has
            # priority; retry only after it is no longer active.
            jobs=self.kernel.dispatch("jobs.list",{},self.principal)
            if jobs["ok"] and any(j["state"] in ("Queued","Running","Paused") for j in jobs["result"]):return
            result=self.kernel.dispatch("jobs.submit",{"tool":"book.refresh","request_key":"orange-book-auto-"+stamp,"timeout":300},self.principal)
            if result["ok"] and refusal(result["result"]):self.attempted.add(stamp);self.last_error=refusal(result["result"])
            elif result["ok"]:self.attempted.add(stamp)
            else:self.last_error=result.get("error",{}).get("message")
        worker.ready.connect(done)
        def finished():self.worker=None;worker.deleteLater()
        worker.finished.connect(finished);worker.start()
    def shutdown(self):
        self.active=False
        self.timer.stop()
        if self.worker is not None:self.worker.wait(10000)


class OrangeBookTab(ServiceTab):
    def __init__(self,host):
        super().__init__(host);self.input_fingerprint=None;self.current_page="arc-workshop"
        row=QHBoxLayout();row.addWidget(overline("The Orange Book"));self.contents=QComboBox();self.contents.setMinimumContentsLength(28);self.contents.activated.connect(self.read);row.addWidget(self.contents,1)
        self.auto=QCheckBox("Automatic updates");self.auto.setChecked(host.book_watcher.active);self.auto.toggled.connect(host.book_watcher.activate);row.addWidget(self.auto);self.outer.addLayout(row)
        self.outer.addWidget(self.status)
        self.reader=QTextBrowser();self.reader.setOpenLinks(False);self.reader.setOpenExternalLinks(False);self.reader.anchorClicked.connect(self.anchor)
        self.reader.setObjectName('OrangeBookPaper')
        self.reader.setStyleSheet('QTextBrowser {background:#faf7f0;color:#182330;padding:20px;border-radius:5px;}')
        self.read_split=QSplitter(Qt.Horizontal)
        sidebar=QWidget();side=QVBoxLayout(sidebar);side.setContentsMargins(8,8,12,8)
        from PySide6.QtSvg import QSvgRenderer
        cover=QLabel();cover.setAlignment(Qt.AlignCenter)
        pix=QPixmap(180,216);pix.fill(Qt.transparent);painter=QPainter(pix)
        QSvgRenderer(str(locations.program(host.root)/'branding/noir/orange-book.svg')).render(painter)
        painter.end();cover.setPixmap(pix);side.addWidget(cover)
        self.chapter_list=QTreeWidget();self.chapter_list.setHeaderHidden(True)
        self.chapter_list.setRootIsDecorated(False);self.chapter_list.setIndentation(0)
        self.chapter_list.setAccessibleName('Orange Book chapters')
        self.chapter_list.itemClicked.connect(lambda item,_:self.select_chapter(item.data(0,Qt.UserRole)))
        side.addWidget(self.chapter_list,1)
        self.read_split.addWidget(sidebar);self.read_split.addWidget(self.reader)
        self.read_split.setSizes([220,800]);self.read_split.setStretchFactor(1,1)
        self.outer.addWidget(self.read_split,1)
        self.contents.hide()
        row=QHBoxLayout();self.find=QLineEdit();writing_prompt(self.find, "Find in the Orange Book");self.find.returnPressed.connect(self.search);row.addWidget(self.find,1)
        b=QPushButton(icon(host.root,"search"),"Find");b.clicked.connect(self.search);row.addWidget(b)
        b=QPushButton(icon(host.root,"refresh"),"Refresh DOCX and PDF");b.clicked.connect(lambda:self.submit("book.refresh",lambda j:self.refresh()));row.addWidget(b)
        b=QPushButton(icon(host.root,"export"),"Save current exports");b.clicked.connect(self.save_exports);row.addWidget(b);self.outer.addLayout(row)
        host.book_watcher.refreshed.connect(self.automatic_changed)
        if host.book_watcher.active:host.book_watcher.check()
        QTimer.singleShot(0,self.refresh)
    def title(self):return "Orange Book"
    def refresh(self):self.call("book.contents",{},self.loaded)
    def loaded(self,data):
        self.input_fingerprint=data["input_fingerprint"];self.contents.clear()
        self.chapter_list.clear()
        for p in data["pages"]:
            self.contents.addItem(p["title"],p["id"])
            item=QTreeWidgetItem([p['title']]);item.setData(0,Qt.UserRole,p['id'])
            item.setToolTip(0,p['title']);self.chapter_list.addTopLevelItem(item)
        index=self.contents.findData(self.current_page);self.contents.setCurrentIndex(max(0,index));self.read()
    def read(self,*args):
        page=self.contents.currentData()
        if not page:return
        self.current_page=page;self.call("book.read",{"page":page},self.show_page)
    def show_page(self,data):
        self.input_fingerprint=data["input_fingerprint"]
        self.reader.document().setDefaultStyleSheet(data["css"]+"body,p,li,td{color:#182330;background:#faf7f0;} h1,h2,h3{color:#182330;} a{color:#9b3f00;} code{color:#893a0c;} .note,.warning,.identity{color:#485462;} th{background:#e8ded0;color:#182330;}")
        self.reader.setHtml(data["page"]["html"])
        from .reading_preferences import apply as apply_reading
        apply_reading(self.host)
        flags=len(data["review"]["changed"])
        self.status.setText("Source-linked handbook · %d chapter references need review"%flags)
        self.status.setToolTip('Current guide · live source '+self.input_fingerprint+' · physical qualification remains open')
        from .arc_desktop import refresh
        refresh(self.host)
        for index in range(self.chapter_list.topLevelItemCount()):
            item=self.chapter_list.topLevelItem(index)
            if item.data(0,Qt.UserRole)==self.current_page:
                self.chapter_list.setCurrentItem(item);break

    def select_chapter(self,page):
        index=self.contents.findData(page)
        if index>=0:self.contents.setCurrentIndex(index);self.read()
    def automatic_changed(self,status):
        if status["input_fingerprint"]!=self.input_fingerprint:self.refresh()
    def anchor(self,url):
        if url.scheme()=='arc':
            methods={'brain':'show_brain_link','starter':'show_native_project','simulator':'show_arcos',
                     'review':'show_parser_review','reading':'show_reading','references':'show_database_rom'}
            key=url.path()
            if key in methods and self.host.tabs.pin(self):getattr(self.host,methods[key])()
            return
        target=url.fragment()
        if target.startswith("page_"):target=target.replace("page_","page-")
        index=self.contents.findData(target)
        if index>=0:self.contents.setCurrentIndex(index);self.read()
    def search(self):
        from . import orange_book
        try:
            status=orange_book.ensure(self.host.root)
            pages=io.strict_json(io.project_path(self.host.root,status["pages_file"]).read_bytes())
            query=self.find.text().casefold()
            if not query:return
            for page in pages:
                if query in __import__("re").sub("<[^>]+>"," ",html.unescape(page["html"])).casefold():
                    i=self.contents.findData(page["id"]);self.contents.setCurrentIndex(i);self.read();return
            self.status.setText("No matching book page")
        except Exception as exc:self.status.setText(str(exc))
    def save_exports(self):
        data=self.kernel.dispatch("book.status",{},self.principal)
        if not data["ok"]:self.status.setText(data["error"]["message"]);return
        status=data["result"]
        if not status["exports_current"]:self.status.setText("Exports are not current. Refresh DOCX and PDF first.");return
        directory=QFileDialog.getExistingDirectory(self,"Save current Orange Book exports")
        if not directory:return
        for entry in status["exports"]["files"]:
            source=io.project_path(self.host.root,entry["path"])
            if io.sha(source)!=entry["sha256"]:self.status.setText("Export file changed; regenerate before saving");return
            shutil.copyfile(source,Path(directory)/source.name)
        self.status.setText("Saved current exports · generated material requires editorial review")
