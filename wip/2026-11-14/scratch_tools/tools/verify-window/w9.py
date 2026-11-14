from winbase import *
from collections import Counter
from workbench.engineering_kernel import operator
k = w.ledger_bridge.kernel
seen = Counter(); real = Kernel.dispatch
def counting(self, operation, arguments=None, principal=None, *a, **kw):
    seen[operation] += 1; return real(self, operation, arguments, principal, *a, **kw)
patch.object(Kernel, 'dispatch', counting).start()
def step(tag, fn):
    seen.clear(); fn(); settle(); where(tag); print('   Kernel reads during this step: %d %s' % (sum(seen.values()), dict(seen) if sum(seen.values()) < 12 else '(%d operations)' % len(seen)))
w.show_start(); settle(); where('Home')
step('F9 from Home (first reading)', lambda: w.a_field.trigger())
v = w.field_page.view; first = [(o.id, o.title, o.state) for o in v.field.objects]
step('F9 again while the Field shows', lambda: w.a_field.trigger()); print('   _field_from_home:', w._field_from_home, '| focus:', type(app.focusWidget()).__name__)
step('F9 a third time (key, focus in the Field)', lambda: QTest.keyClick(v, Qt.Key_F9))
step('Esc', lambda: QTest.keyClick(v, Qt.Key_Escape))
step('F9 from Home again, nothing recorded since', lambda: w.a_field.trigger())
step('R (look again)', lambda: QTest.keyClick(v, Qt.Key_R))
QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc -> Home')
# something is recorded: a page is renamed through the Kernel as its room does
docs = real(k, 'documents.list', {}, operator())['result']['documents']; row = next(d for d in docs if 'conclusion' in d['title'].lower()); print('   page:', row['title'], '| revision', row.get('revision'))
got = real(k, 'documents.get', {'id': row['id']}, operator())['result']
ops = [o for o in real(k, 'ledger.operations', {}, operator())['result'].get('operations', []) if str(o.get('name', o) if isinstance(o, dict) else o).startswith('documents.')] if real(k, 'ledger.operations', {}, operator()).get('ok') else []
print('   document operations:', [o.get('name') if isinstance(o, dict) else o for o in ops][:20])
finish()
