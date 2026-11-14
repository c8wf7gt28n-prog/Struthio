"""Orchestrator's probe: the reader against a made-up large workspace (a stand-in kernel, nothing written anywhere)."""
import os, sys, time
from pathlib import Path
PROGRAM = Path(sys.argv[1]).resolve(); os.environ['QT_QPA_PLATFORM'] = 'offscreen'; sys.path.insert(0, str(PROGRAM)); sys.dont_write_bytecode = True
N = int(sys.argv[2])
class Big:
    calls = 0
    def dispatch(self, op, args, principal):
        Big.calls += 1; time.sleep(0.006)          # about what one real read cost on the worked case
        if op == 'intake.namespaces': r = {'namespaces': [{'id': 'ns', 'name': 'Sources'}]}
        elif op == 'references.sources': r = {'sources': [{'item': 'i%d' % n, 'state': 'CURRENT'} for n in range(N)]}
        elif op == 'intake.items': r = {'items': [{'id': 'i%d' % n, 'name': 'source_%d.pdf' % n, 'admission': 'ACCEPTED'} for n in range(N)]}
        elif op == 'office.list': r = {'documents': [{'id': 'owner:s%d' % n, 'title': 'Sheet %d' % n} for n in range(N)]}
        elif op == 'office.get': r = {'source_state': {'state': 'CURRENT_PDF_SOURCE'}, 'revision': 'abc', 'origin': {'pdf': {'item': 'i' + args['id'][7:], 'page_index': 0}}}
        elif op == 'documents.list': r = {'documents': [{'id': 'd%d' % n, 'title': 'Report %d' % n, 'revision': 1, 'updated': n} for n in range(N)]}
        elif op == 'documents.get': r = {'document': {'derivation': {'sheet': 'owner:s' + args['id'][1:], 'inputs': [{'cell': 'B2'}]}}, 'source_state': {'state': 'CURRENT'}}
        elif op == 'investigation.list': r = {'investigations': [{'id': 'v%d' % n, 'question': 'Question %d' % n, 'state': 'OPEN', 'updated': n} for n in range(3)]}
        elif op == 'investigation.sheet': r = {'learned': [{'id': '%s-c%d' % (args['id'], n), 'text': 'Claim %d' % n, 'evidence_state': 'SUPPORTED', 'review': 'CURRENT'} for n in range(60)], 'unresolved': []}
        elif op == 'investigation.path': r = {'path': [{'kind': 'SOURCE', 'address': 'intake:i1', 'direction': 'SUPPORTS'}]}
        elif op == 'conditions.list': r = {'conditions': []}
        else: return {'ok': False, 'error': 'unknown'}
        return {'ok': True, 'result': r}
from workbench.field_source import read_field
t = time.time(); field, refused = read_field(Big(), None); dt = time.time() - t
print('records of each kind in the workspace:', N, '| Kernel reads:', Big.calls, '| read time %.2fs' % dt, '| objects shown:', len(field.objects), '| links:', len(field.links))
print('note:', field.note, '| refused:', refused)
from PySide6.QtWidgets import QApplication
app = QApplication([]); from workbench.field_qt import FieldView
v = FieldView(); v.resize(1368, 1010); t = time.time(); v.set_field(field); v.show(); app.processEvents(); img = v.grab(); print('first paint %.3fs' % (time.time() - t))
t = time.time(); v.field.move('down'); v._layout(); v.update(); app.processEvents(); print('one key move and repaint %.3fs' % (time.time() - t))
