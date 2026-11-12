"""Contextual Hardware Proof Laboratory using only shared kernel operations."""
import html
import json
import uuid
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QHeaderView, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTreeWidget, QTreeWidgetItem, QTabWidget, QTextBrowser, QSplitter)
from .engine import engineering
from .engineering_kernel import operator
from .project_context import refusal
from .hardware_proof import FAULTS
from .ux_polish import overline, readable_error, empty_hint

LABELS = {'power_reset':'Power / reset', 'pin_electrical':'Exact pins / electrical',
    'clock_timing':'Clocks / timing', 'boot_configuration':'Boot / configuration / DDR',
    'data_flow':'Interchip data flow', 'physical_manufacture':'Physical manufacture'}

def esc(value): return html.escape(str(value))
def bullets(values): return '<ul>'+''.join('<li>'+esc(x)+'</li>' for x in values)+'</ul>'

class HardwareProofTab(QWidget):
    def __init__(self, host):
        super().__init__(); self.host=host; self.kernel=engineering(host.root)
        self.principal=operator(); self.report=None; self.job_id=None; self.loaded_evidence=None
        layout=QVBoxLayout(self)
        heading=overline('Hardware viability','source coverage and six-domain proof'); layout.addWidget(heading)
        self.status=QLabel('Reading source-bound findings…'); self.status.setWordWrap(True);layout.addWidget(self.status)
        row=QHBoxLayout();layout.addLayout(row)
        for label,fn in [('Refresh sources',self.refresh),('Run qualification',self.run),('Stop job',self.stop),('Jobs / evidence',host.show_engineering)]:
            button=QPushButton(label);button.clicked.connect(fn);row.addWidget(button)
        self.job_status=QLabel('No proof job selected. Static inspection does not execute a compiler.')
        self.job_status.setWordWrap(True);layout.addWidget(self.job_status)
        self.pages=QTabWidget();layout.addWidget(self.pages,1)
        coverage_page=QWidget();cl=QVBoxLayout(coverage_page)
        self.coverage_summary=QLabel();self.coverage_summary.setWordWrap(True);cl.addWidget(self.coverage_summary)
        coverage_button=QPushButton('Run source reconciliation');coverage_button.clicked.connect(self.run_coverage);cl.addWidget(coverage_button)
        self.coverage=QTreeWidget();self.coverage.setHeaderLabels(['Item / interface','State','Evidence gap']);cl.addWidget(self.coverage)
        empty_hint(self.coverage,'Coverage appears after the sources are read.');self.coverage.header().setSectionResizeMode(1,QHeaderView.ResizeToContents)
        self.pages.addTab(coverage_page,'Coverage')
        split=QSplitter(Qt.Horizontal)
        self.findings=QTreeWidget();self.findings.setHeaderLabels(['Domain / finding','Result']);split.addWidget(self.findings)
        self.detail=QTextBrowser();self.detail.document().setDefaultStyleSheet('a { color: #ff9b6b; }');self.detail.setOpenLinks(False);self.detail.anchorClicked.connect(self.open_source);split.addWidget(self.detail)
        split.setSizes([290,580]);self.pages.addTab(split,'Six domains')
        self.findings.currentItemChanged.connect(self.show_finding)
        graph_page=QWidget();gl=QVBoxLayout(graph_page);fr=QHBoxLayout();gl.addLayout(fr)
        fr.addWidget(QLabel('Dependency fault scenario:'));self.fault=QComboBox();self.fault.addItems(FAULTS);fr.addWidget(self.fault,1)
        self.graph=QTreeWidget();self.graph.setHeaderLabels(['Step / required predecessor','State','Missing proof / recovery']);gl.addWidget(self.graph)
        self.graph.itemDoubleClicked.connect(self.open_node)
        self.fault.currentTextChanged.connect(self.refresh_graph)
        self.pages.addTab(graph_page,'Power → picture')
        self.service_view=QTextBrowser();self.service_view.document().setDefaultStyleSheet('a { color: #ff9b6b; }');self.service_view.setOpenLinks(False);self.service_view.anchorClicked.connect(self.open_source)
        self.pages.addTab(self.service_view,'Runtime dependencies')
        self.results=QTextBrowser();self.pages.addTab(self.results,'Qualification evidence')
        self.results.setHtml('<p>Run qualification to compile the independent C margin checker and execute host firmware regressions. Missing tools are recorded as blocked.</p>')
        self.timer=QTimer(self);self.timer.timeout.connect(self.poll);self.timer.start(1500)
        self.refresh()
        jobs=self.call('jobs.list')
        if jobs:
            rows=jobs if isinstance(jobs,list) else jobs.get('jobs',[])
            latest=next((j for j in rows if j['tool']=='proof.qualify'),None)
            if latest:self.job_id=latest['id'];self.poll()

    def title(self): return 'Hardware Proof · Six Domains'
    def shutdown_engineering(self): self.timer.stop()  # Durable jobs deliberately outlive the tab.
    def call(self,op,params=None):
        response=self.kernel.dispatch(op,params or {},self.principal)
        if not response['ok']:
            self.status.setText(readable_error(response['error']['message'],self.host.root));self.status.setToolTip(response['error']['message']);return None
        if refusal(response['result']):self.status.setText(refusal(response['result']));return None
        return response['result']
    def refresh(self):
        coverage=self.call('hardware.coverage.inspect')
        if coverage:
            t=coverage['totals'];self.coverage.clear()
            self.coverage_summary.setText('%d components · %d interface/mechanical records · %d mapped to source check · %d unmapped · %d with open validation gaps\nRevision %s · Fabrication HOLD' %
                (t['components'],t['interfaces'],t['mapped_to_source_check'],t['unmapped'],t['with_gaps'],coverage['revision'][:16]))
            for item in coverage['items']:
                row=QTreeWidgetItem([item['id'],item['validation'],'; '.join(item['gaps'])]);row.setToolTip(0,json.dumps(item,indent=2));self.coverage.addTopLevelItem(row)
            self.coverage.setColumnWidth(0,230);self.coverage.setColumnWidth(1,90)
        data=self.call('hardware.proof.inspect')
        if not data:return
        self.report=data
        self.status.setText('Design feasibility: NOT YET DETERMINABLE  ·  Fabrication: HOLD  ·  %d source hashes checked'%len(data['source_hashes']))
        self.findings.clear()
        for domain in data['domains']:
            parent=QTreeWidgetItem([LABELS[domain],'']);self.findings.addTopLevelItem(parent)
            for finding in data['findings']:
                if finding['domain']==domain:
                    item=QTreeWidgetItem([finding['id']+' · '+finding['component'],finding['status']]);item.setData(0,Qt.UserRole,finding);parent.addChild(item)
            parent.setExpanded(True)
        self.findings.setColumnWidth(0,245)
        self.findings.setCurrentItem(self.findings.topLevelItem(0).child(0))
        self.service_view.setHtml('<h2>ARC-OS target service dependencies</h2><p>The compiled ARC-OS host is available under Operating System. Target drivers and physical runtime remain unproven.</p>'+''.join(
            '<h3>'+esc(s['service'])+' · '+esc(s['status'])+'</h3><p>'+esc(s['missing_proof'])+'</p>'+self.citation(s['source']) for s in data['services']))
        self.refresh_graph()
        if self.loaded_evidence:self.loaded_evidence=None;self.poll()
    def citation(self,s):
        return '<p><a href="source:'+esc(s['path'])+'">'+esc(s['path'])+'</a><br><small>SHA-256 '+esc(s.get('sha256'))+'</small></p>'
    def show_finding(self,item,previous=None):
        f=item.data(0,Qt.UserRole) if item else None
        if not f:return
        body='<h2>'+esc(f['id']+' · '+f['component'])+'</h2><p><b>'+esc(f['status'])+'</b> · '+esc(f['evidence_state'])+' · '+esc(f['severity'])+'</p><p>'+esc(f['claim'])+'</p>'
        body+='<h3>Missing proof</h3>'+bullets(f['missing_proof'])+'<h3>Next executable check</h3><p>'+esc(f['next_executable_check'])+'</p>'
        if f['id']=='PWR-01':
            body+='<h3>Recomputed worst-case DC margins</h3><table cellpadding="6"><tr><th>FPGA</th><th>Brownout</th><th>Startup</th><th>Upper</th></tr>'
            for m in f['details']['models']:
                body+='<tr><td>'+esc(m['case']['fpga'])+'</td>'+''.join('<td>%.4f mV</td>'%(m['result']['margins_v'][k]*1000) for k in ('brownout_headroom_v','startup_headroom_v','upper_operating_headroom_v'))+'</tr>'
            body+='</table><p>The 5 mV criterion is an explicit study assumption, not a qualified board requirement. Dynamic budgets are missing.</p>'
        if f['id']=='PIN-01':
            p=f['details']['package'];body+='<p><b>%d active pad locks / %d commented proposals.</b> Package-table fixture: %s. This is not exact-package implementation proof.</p>'%(len(p['active_locations']),len(p['proposed_locations']),esc(f['details']['fixture_check']['status']))
        body+='<h3>Assumptions</h3>'+bullets(f['assumptions'])+'<h3>Source evidence</h3>'+''.join(self.citation(s) for s in f['sources'])
        self.detail.setHtml(body)
    def open_source(self,url):
        if url.scheme()=='source':self.host.open_document(self.host.root/url.toString()[7:])
    def refresh_graph(self,*args):
        if not self.report:return
        d=self.call('hardware.proof.trace',{'expected_sources':self.report['source_hashes'],'fault':self.fault.currentText()})
        if not d:return
        g=d['graph'];unavailable=set(g['fault']['unavailable']);self.graph.clear()
        for n in g['nodes']:
            item=QTreeWidgetItem([n['title'],'UNAVAILABLE (model)' if n['id'] in unavailable else n['status'],n['missing_proof']]);item.setData(0,Qt.UserRole,n['source']);self.graph.addTopLevelItem(item)
            for e in g['edges']:
                if e['to']==n['id']:item.addChild(QTreeWidgetItem(['Requires '+e['from'],e['status'],e['missing_proof']]))
            item.addChild(QTreeWidgetItem(['Recovery','UNPROVEN',n['recovery']]))
        self.graph.setColumnWidth(0,245);self.graph.setColumnWidth(1,160)
    def open_node(self,item,column):
        source=item.data(0,Qt.UserRole)
        if source:self.host.open_document(self.host.root/source['path'])
    def run(self):
        j=self.call('jobs.submit',{'tool':'proof.qualify','timeout':300,'goal':'Reproduce source-backed hardware proof blockers and reject invalid fixtures','request_key':uuid.uuid4().hex})
        if j:self.job_id=j['id'];self.loaded_evidence=None;self.poll()
    def run_coverage(self):
        j=self.call('jobs.submit',{'tool':'proof.coverage','timeout':300,'goal':'Reconcile current hardware coverage','request_key':uuid.uuid4().hex})
        if j:self.job_id=j['id'];self.loaded_evidence=None;self.poll()
    def stop(self):
        if self.job_id:self.call('jobs.cancel',{'id':self.job_id});self.poll()
    def poll(self):
        if not self.job_id:return
        j=self.call('jobs.get',{'id':self.job_id})
        if not j:return
        self.job_status.setText(j['state']+' · '+j.get('current_operation','proof.qualify')+' · '+j['id'])
        if not j.get('evidence') or j['evidence']==self.loaded_evidence:return
        result=self.call('hardware.proof.result',{'id':j['evidence']})
        if not result:return
        self.loaded_evidence=j['evidence'];e=result['evidence'];r=e['diagnostics']
        body='<h2>Qualification '+esc(r.get('status','UNKNOWN'))+'</h2><p>Evidence '+esc(e['id'])+'</p><p><b>Source binding (checked when loaded / refreshed): '+('CURRENT' if result['source_current'] else 'STALE — rerun required')+'</b></p><p>'+esc(r.get('qualification_scope',''))+'</p>'
        body+='<h3>Executed checks</h3><table cellpadding="5">'+''.join('<tr><td>'+esc(c['id'])+'</td><td>'+('PASS' if c['passed'] else 'FAIL')+'</td></tr>' for c in r.get('cases',[])+r.get('independent_checks',[]))+'</table>'
        if 'totals' in r:
            body+='<h3>Source reconciliation</h3><pre>'+esc(json.dumps(dict(totals=r['totals'],cross_source=r['cross_source']),indent=2))+'</pre><p>'+esc(r['notice'])+'</p>'
        body+='<h3>Blocked / unqualified</h3>'+bullets(r.get('blockers',[]))+'<h3>Commands and measured duration</h3>'+bullets(' '.join(c['argv'])+' · exit '+str(c['exit_status'])+' · %.3f s'%c['duration_seconds'] for c in r.get('commands',[]))
        self.results.setHtml(body)
