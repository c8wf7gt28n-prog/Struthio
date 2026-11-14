import sys, os, json, sqlite3
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens')
from common import *
from workbench import field_page, office_service
open_window(); settle(30, 6)
real_get = office_service.get
def one_refuses(key, kernel=None, principal=None):
    raise ValueError('OFFICE_RECORD_DAMAGED')       # what the store says for a record whose digest no longer matches
office_service.get = one_refuses
def counts():
    db = sqlite3.connect('file:%s?mode=ro' % (RUN / 'ws/.ledger/engineering.sqlite3'), uri=True)
    out = (db.execute('SELECT count(*) FROM activity_journal').fetchone()[0], db.execute('SELECT count(*) FROM audit').fetchone()[0]); db.close(); return out
a = counts()
for n in range(2):
    w.show_field(); settle(20, 3); print('status line: %r' % w.statusBar().currentMessage()); print('census:', w.field_page.view.field.census()); field_page.leave_field(w); settle(20, 3)
b = counts(); print('journal rows %d -> %d, audit rows %d -> %d over two showings with 3 sheets that cannot be read' % (a[0], b[0], a[1], b[1]))
db = sqlite3.connect('file:%s?mode=ro' % (RUN / 'ws/.ledger/engineering.sqlite3'), uri=True)
for seq, payload in db.execute('SELECT seq,payload FROM activity_journal ORDER BY seq DESC LIMIT 3'):
    ev = json.loads(payload); print('   journal', seq, ev.get('operation'), ev.get('state'))
w._closing = True; print('DONE')
