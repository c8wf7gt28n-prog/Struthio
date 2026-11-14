import sys, os, json, sqlite3
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/verify-reader')
from wincommon import *
from workbench import field_page, office_service
open_window(); settle(30, 6)
real_get = office_service.get
def one_refuses(key, kernel=None, principal=None):
    raise ValueError('OFFICE_RECORD_DAMAGED')       # what the store says for a record whose digest no longer matches
office_service.get = one_refuses
def counts():
    db = sqlite3.connect('file:%s?mode=ro' % (RUN / 'ws/.ledger/engineering.sqlite3'), uri=True)
    out = (db.execute('SELECT count(*) FROM activity_journal').fetchone()[0], db.execute('SELECT count(*) FROM audit').fetchone()[0]); db.close(); return out
asked = []
real_dispatch = Kernel.dispatch
def counted(self, operation, params=None, principal=None):
    asked.append(operation); return real_dispatch(self, operation, params, principal)
Kernel.dispatch = counted
a = counts()
for n in range(3):
    asked.clear(); w.show_field(); settle(20, 3); c = counts()
    print('showing %d: status line: %r | census: %s | unread remembered: %d | office.get asked: %d | all dispatches: %d | journal %d audit %d' % (n + 1, w.statusBar().currentMessage(), w.field_page.view.field.census(), len(w.field_page.unread), asked.count('office.get'), len(asked), c[0], c[1]))
    v = w.field_page.view
    for o in v.field.objects:
        if o.id.startswith('office:'): print('     ', o.kind, repr(o.tag), o.title, '| state=%r role=%r lines=%s' % (o.state, o.role, o.lines))
    if n == 0:
        o = next(o for o in v.field.objects if o.id.startswith('office:')); v.field.select(o.id); v._describe(); print('   accessible description:', v.accessibleDescription())
    print('   links into/out of the unread sheets:', [(l.source[:14], l.target[:14], l.stale) for l in v.field.links if l.source.startswith('office:') or l.target.startswith('office:')])
    field_page.leave_field(w); settle(20, 3)
b = counts(); print('journal rows %d -> %d, audit rows %d -> %d over three showings with 3 sheets that cannot be read' % (a[0], b[0], a[1], b[1]))
# a write elsewhere moves the journal head: is the unreadable record still not asked again?
from workbench.engineering_kernel import operator
k = w.ledger_bridge.kernel; k.dispatch('documents.create', {'title': 'A new page', 'text': 'x'}, operator())
a2 = counts(); asked.clear(); w.show_field(); settle(20, 3); c = counts()
print('after another record was written: office.get asked: %d | unread remembered: %d | journal %d -> %d audit %d -> %d | census %s' % (asked.count('office.get'), len(w.field_page.unread), a2[0], c[0], a2[1], c[1], w.field_page.view.field.census()))
# R looks again
asked.clear(); QTest.keyClick(w.field_page.view, Qt.Key_R); settle(20, 3); d = counts()
print('R pressed: office.get asked: %d | journal %d -> %d audit %d -> %d | status: %r' % (asked.count('office.get'), c[0], d[0], c[1], d[1], w.statusBar().currentMessage()))
office_service.get = real_get
asked.clear(); QTest.keyClick(w.field_page.view, Qt.Key_R); settle(20, 3)
print('record readable again + R: office.get asked: %d | states: %s | status: %r | problem: %r' % (asked.count('office.get'), [(o.title[:18], o.state) for o in w.field_page.view.field.objects if o.id.startswith('office:')], w.statusBar().currentMessage(), w.field_page.problem))
field_page.leave_field(w); settle(20, 3)
db = sqlite3.connect('file:%s?mode=ro' % (RUN / 'ws/.ledger/engineering.sqlite3'), uri=True)
for seq, payload in db.execute('SELECT seq,payload FROM activity_journal ORDER BY seq DESC LIMIT 3'):
    ev = json.loads(payload); print('   journal', seq, ev.get('operation'), ev.get('state'))
w._closing = True; print('DONE')
