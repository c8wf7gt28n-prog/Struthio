"""Scale: a fake kernel answering in the real handlers' shapes; no database, no window. Times the reader, the model and the view."""
import json, os, sys, tempfile, time, statistics
from pathlib import Path
L = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens')
RUN = Path(tempfile.mkdtemp(prefix='scale-', dir=str(L / 'run'))); HOME = RUN / 'home'; HOME.mkdir()
SCREEN = RUN / 'screen.json'
SCREEN.write_text(json.dumps({'screens': [{'name': 'shot', 'x': 0, 'y': 0, 'width': 1920, 'height': 1200, 'logicalDpi': 96, 'logicalBaseDpi': 96, 'dpr': 1.0}]}))
os.environ.update(PYTHONDONTWRITEBYTECODE='1', QT_QPA_PLATFORM='offscreen:configfile=' + str(SCREEN), ARC_LEDGER_EMBEDDED='1', ARC_LEDGER_DISABLE_BOOK_WATCHER='1',
                  HOME=str(HOME), ARC1_WORKBENCH_CONFIG_HOME=str(RUN / 'profile'), ARC_LEDGER_CONCERN=str(HOME / 'Concern'))
os.chdir(RUN); sys.path.insert(0, '/home/user/Struthio'); sys.dont_write_bytecode = True
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPainter
from PySide6.QtTest import QTest
from workbench.qt_app import make_app
app = make_app([])
from workbench import field_source, field_model
from workbench.field_qt import FieldView

N_SHEETS, N_DOCS, N_DERIVED, N_INV, N_CLAIMS, N_ITEMS = [int(x) for x in (sys.argv[1:7] + ['300', '300', '150', '3', '60', '40'][len(sys.argv) - 1:])]
class FakeKernel:
    def __init__(self): self.calls = 0
    def dispatch(self, op, args, principal):
        self.calls += 1; a = args or {}
        return {'ok': True, 'result': getattr(self, op.replace('.', '_'))(a)}
    def intake_namespaces(self, a): return {'namespaces': [{'id': 'ns1', 'name': 'Sources', 'owner': 'desktop-owner', 'generation': 1, 'readers': [], 'policy': {}}]}
    def references_sources(self, a): return {'sources': [{'item': 'item%03d' % i, 'name': 'Datasheet_%03d.pdf' % i, 'state': 'CURRENT'} for i in range(N_ITEMS)]}
    def intake_items(self, a): return {'total': N_ITEMS, 'items': [{'id': 'item%03d' % i, 'name': 'Datasheet_%03d.pdf' % i, 'sha256': 'a' * 64, 'admission': 'ACCEPTED'} for i in range(N_ITEMS)], 'generation': 1}
    def office_list(self, a): return {'documents': [{'id': 'owner:%032x' % i, 'version': 1, 'title': 'Sheet %03d of the limits table' % i, 'state': 'active', 'kind': 'table'} for i in range(N_SHEETS)]}
    def office_get(self, a):
        i = int(a['id'].split(':')[1], 16)
        return {'id': a['id'], 'revision': '%064x' % i, 'origin': {'profile': 'x', 'pdf': {'item': 'item%03d' % (i % N_ITEMS), 'page_index': i % 7}}, 'source_state': {'state': 'CURRENT_PDF_SOURCE' if i % 9 else 'PDF_SOURCE_REVIEW_REQUIRED'}, 'document': {}}
    def documents_list(self, a): return {'documents': [{'id': '%032x' % i, 'title': 'Report %03d · total power' % i, 'revision': 1 + i % 5} for i in range(N_DOCS)], 'limit': 100, 'offset': 0}
    def documents_get(self, a):
        i = int(a['id'], 16); doc = {'id': a['id'], 'title': 'Report %03d' % i, 'blocks': []}; out = {'document': doc, 'summary': {}, 'events': [], 'plain': ''}
        if i < N_DERIVED:
            doc['derivation'] = {'sheet': 'owner:%032x' % (i % max(1, N_SHEETS)), 'inputs': [{'cell': 'B%d' % (2 + i % 5)}, {'cell': 'B%d' % (3 + i % 5)}]}
            out['source_state'] = {'state': 'CURRENT' if i % 11 else 'SHEET_CHANGED'}
        return out
    def investigation_list(self, a): return {'investigations': [{'id': 'inv%d' % i, 'question': 'Question %d about the rails?' % i, 'state': 'WAITING'} for i in range(N_INV)]}
    def investigation_sheet(self, a):
        n = int(a['id'][3:]); claims = [{'id': 'c%d_%d' % (n, j), 'text': 'Claim %d of investigation %d holds on Rev B.' % (j, n), 'role': 'FINDING' if j % 6 else 'QUESTION',
                                          'evidence_state': 'SUPPORTED' if j % 6 else 'UNKNOWN', 'review': 'CURRENT'} for j in range(N_CLAIMS)]
        return {'id': a['id'], 'question': 'Question %d' % n, 'learned': [c for c in claims if c['role'] == 'FINDING'], 'unresolved': [c for c in claims if c['role'] == 'QUESTION']}
    def investigation_path(self, a):
        n, j = [int(x) for x in a['claim'][1:].split('_')]
        return {'path': [{'kind': 'SOURCE', 'address': 'intake:item%03d' % ((n * 7 + j) % N_ITEMS), 'direction': 'SUPPORTS'},
                         {'kind': 'CHECK', 'program': 'read @office:owner:%032x' % ((n * 13 + j) % max(1, N_SHEETS)), 'outcome': 'PASSED'}]}
    def conditions_list(self, a): return {'conditions': []}

def timed(fn, n=3):
    out = []
    for _ in range(n):
        t = time.perf_counter(); r = fn(); out.append((time.perf_counter() - t) * 1000)
    return min(out), r
k = FakeKernel()
ms, (field, refused) = timed(lambda: field_source.read_field(k, object(), ''), 1)
print('objects %d, links %d, refused %d, dispatch calls %d' % (len(field.objects), len(field.links), len(refused), k.calls))
print('census:', field.census())
print('read_field (fake kernel, includes one Field construction): %.0f ms' % ms)
objs = list(field.objects); links = list(field.links)
ms, f2 = timed(lambda: field_model.Field(list(objs), list(links), 'x'), 2); print('Field(...) construction alone: %.0f ms' % ms)
print('columns:', {r: len(field.column(r)) for r in field.ranks()})
ms, (placed, surface) = timed(lambda: field.place(1368, 1010 - 58 - 92, 1.0), 3); print('place(1368 x body): %.2f ms; surface height %.0f px' % (ms, surface))
ms, _ = timed(lambda: field.depth(), 3); print('depth(): %.2f ms' % ms)
v = FieldView(); v.resize(1368, 1010); v.set_field(field); v.show(); app.processEvents()
print('view scale:', v.scale(), 'font px', v.fontInfo().pixelSize())
img = QImage(1368, 1010, QImage.Format_ARGB32_Premultiplied)
def paint():
    v.render(img)
ms, _ = timed(paint, 3); print('one paint at 1368x1010 (render to image): %.0f ms' % ms)
def key(kk):
    QTest.keyClick(v, kk); paint()
for name, kk in (('Down', Qt.Key_Down), ('Left', Qt.Key_Left), ('Tab', Qt.Key_Tab)):
    ms, _ = timed(lambda: key(kk), 3); print('one %s key press + repaint: %.0f ms' % (name, ms))
ms, _ = timed(lambda: v._describe(), 3); print('_describe(): %.2f ms; description length %d chars' % (ms, len(v.accessibleDescription())))
img.save(str(L / 'out' / ('scale_%d_%d.png' % (N_SHEETS, N_DOCS))))
print('DONE')
