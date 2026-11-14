"""A sheet imported from a CSV under the workspace; then the CSV changes on disk (outside Graphite); then it is deleted.
What does the Field say at the next showing (F9), and after R?"""
import sys
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-reader')
from wincommon import *
from workbench import field_page
from workbench.engineering_kernel import operator
open_window(); settle(50, 6)
k = w.ledger_bridge.kernel; p = operator()
def call(op, args=None):
    r = k.dispatch(op, args or {}, p)
    if not r.get('ok'): print('   REFUSED', op, r.get('error')); return None
    return r['result']
csv = RUN / 'ws' / 'parts.csv'; csv.write_text('part,qty\nR1,2\nC1,4\n')
plan = call('office.import.preview', {'path': str(csv)}); made = call('office.import.commit', {'plan': plan['id'], 'expected_digest': plan['digest']})
ident = 'office:' + made['document_id']
def look(tag, key=None):
    if key is None: w.a_field.trigger()
    else: QTest.keyClick(w.field_page.view, key)
    settle(30, 4); v = w.field_page.view; o = v.field.get(ident)
    rec = call('office.get', {'id': made['document_id']})['source_state']['state']
    print('%-52s record says %-22s | Field shows state=%r lines=%s | census: %s' % (tag, rec, o.state if o else None, o.lines if o else None, [c for c in v.field.census() if 'recheck' in c or 'sheet' in c]))
    return v
v = look('F9 after the import')
QTest.keyClick(v, Qt.Key_Escape); settle(30, 4)
csv.write_text('part,qty\nR1,2\nC1,9\n')           # the original changes on disk, outside Graphite
v = look('F9 after the CSV changed on disk')
v = look('R (look again)', Qt.Key_R)
QTest.keyClick(v, Qt.Key_Escape); settle(30, 4)
csv.unlink()
v = look('F9 after the CSV was deleted')
v = look('R (look again)', Qt.Key_R)
o = v.field.get(ident); v.field.select(ident); v._describe(); print('accessible description:', v.accessibleDescription())
w._closing = True; print('DONE')
