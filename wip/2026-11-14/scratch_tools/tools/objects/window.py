import sys, os, subprocess; sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/objects')
import common; ws, prof = common.copy_case(); common.setup(profile=prof, workspace=ws)
from unittest.mock import patch
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QMessageBox
from PySide6.QtTest import QTest
from workbench.qt_app import make_app, WorkbenchWindow
from workbench.engineering_kernel import Kernel
from workbench.session import Session
patch.object(Kernel, 'submit', side_effect=ValueError('No job submission (held by the probe)')).start()   # a refusal the Kernel reports, not a crash
patch.object(QMessageBox, 'question', return_value=QMessageBox.No).start()
app = make_app([]); session = Session(prof / 'session.json', ws)
w = WorkbenchWindow(ws, session, restore=False)
import platform; platform.processor()
patch.object(subprocess, 'Popen', side_effect=AssertionError('No process start')).start()
patch.object(os, 'system', side_effect=AssertionError('No shell command')).start()
patch.object(QProcess, 'startDetached', side_effect=AssertionError('No detached program')).start()
def settle(ms=40, n=6):
    for name in ('agenda_runner', 'study_idle'):
        obj = getattr(w, name, None)
        if obj and hasattr(obj, 'timer'): obj.timer.stop()
    for _ in range(n): app.processEvents(); QTest.qWait(ms)
w.resize(1600, 1000); w.show(); settle()
def tabs(): return [(type(w.tabs.widget(i)).__name__, w.tabs.tabText(i)) for i in range(w.tabs.count())]
print('root', w.root == ws.resolve(), '| session.path', session.path.name, '| session.state[project]', session.state.get('project'))
print('kernel is', type(w.ledger_bridge.kernel).__name__, 'kernel.root==root', getattr(w.ledger_bridge.kernel, 'root', None) == w.root)
print('concern.store.path', w.concern.store.path.relative_to(prof) if w.concern.store else None, '| concern.error', w.concern.error)
print('home active', w._home_active, '| central_stack current', type(w.central_stack.currentWidget()).__name__, '| tabs', tabs())
from workbench import document_qt, investigations_qt, office_qt, pdf_qt, shell2
k = w.ledger_bridge.kernel
docs = shell2.call(w, 'documents.list')['documents']; target = next(d for d in docs if 'Startup' in d['title'])
t = document_qt.show(w, target['id']); settle()
print('document_qt.show ->', type(t).__name__, 'document_id', t.document_id == target['id'], 'revision', t.revision, 'title', t.title_box.text(), 'report_derivation', bool(t.report_derivation), 'report hint', t.report_hint.text(), '| current tab is it', w.tabs.currentWidget() is t)
sheet_id = t.report_derivation['sheet']
o = office_qt.open_office(w, sheet_id); settle()
print('office_qt.open_office ->', type(o).__name__, 'ident', getattr(o, 'ident', None), 'title', o.title() if o else None, '| current', w.tabs.currentWidget() is o)
inv = shell2.call(w, 'investigation.list')['investigations'][0]
i = investigations_qt.show(w, inv['id']); settle()
print('investigations_qt.show ->', type(i).__name__, 'ident', i.ident == inv['id'], 'sheet question', (i.sheet or {}).get('question'), '| current', w.tabs.currentWidget() is i)
src = t.report_derivation['pdf']
p = pdf_qt.open_pdf(w, src['namespace'], src['item'], src['source_sha256'], src['page_index'], src['rect']); settle(80, 20)
print('pdf_qt.open_pdf ->', type(p).__name__, 'source', p.source, '| heading', p.heading.text(), '| status', p.status.text()[:200], '| document loaded', bool(p.document), '| current', w.tabs.currentWidget() is p)
d2 = shell2.open_destination(w, 'documents:' + docs[0]['id']); settle()
print('shell2.open_destination(documents:<id>) ->', type(d2).__name__, d2.document_id == docs[0]['id'])
print('tabs now', tabs())
out = common.S / 'tools/objects/out'; out.mkdir(exist_ok=True)
from collections import Counter
cab = shell2.call(w, 'ledger.cabinet', {'limit': 200}); print('cabinet (window bound) roles', Counter(n['role'] for n in cab['nodes']), [n['id'] for n in cab['nodes'] if n['id'].startswith('catalog:owner:')])
# a Preview (non-room, unpinned) tab is replaced by the next one: open again, pin, then open the next
o = office_qt.open_office(w, sheet_id); settle(); print('reopened sheet; is preview', w.tabs.preview() is o, '| pin ->', w.tabs.pin(o))
p = pdf_qt.open_pdf(w, src['namespace'], src['item'], src['source_sha256'], src['page_index'], src['rect']); settle(80, 10)
print('tabs after pin + pdf', tabs(), '| sheet still alive', w.tabs.indexOf(o) >= 0)
print('OfficePanel attrs', [a for a in ('ident', 'base', 'grid', 'address', 'status', 'source_row_info') if hasattr(o, a)], '| base keys', sorted(o.base), '| grid', o.grid.rowCount(), 'x', o.grid.columnCount())
print('DocumentsTab attrs', [a for a in ('document_id', 'revision', 'rows', 'page', 'title_box', 'report_bar', 'report_derivation', 'foot', 'dirty') if hasattr(t, a)], '| rows', len(t.rows))
print('InvestigationTab attrs', [a for a in ('ident', 'sheet', 'scroll', 'body') if hasattr(i, a)])
print('ledger.object.current', common.short(shell2.call(w, 'ledger.object.current'), 300))
for name, tab in (('doc', t), ('sheet', o), ('inv', i)):
    w.tabs.setCurrentWidget(tab); settle(60, 6); w.grab().save(str(out / ('case_%s.png' % name)), 'PNG')
print('saved', sorted(x.name for x in out.iterdir()))
w.close(); settle()
