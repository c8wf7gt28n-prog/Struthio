"""R8: nested reads of office.get (notebook.get / notebook.resolve / book.contents) and the journal, reader level."""
from common import *
from workbench.field_source import read_field, problems
k = Kernel(RUN / 'ws'); hold_processes()
def rows():
    with k.db() as db: return db.execute('SELECT count(*) FROM activity_journal').fetchone()[0], db.execute('SELECT count(*) FROM audit').fetchone()[0]
nb = call(k, 'notebook.create', {'title': 'Probe notebook'}); doc = call(k, 'office.from.notebook', {'notebook': nb['id'], 'expected_revision': nb['revision']})
print('notebook copy:', doc.get('id'), doc.get('REFUSED'))
book = call(k, 'office.from.book'); print('book copy:', json.dumps(book, default=str)[:200])
print('office.list:', [(r['title'], r['kind'], call(k, 'office.get', {'id': r['id']})['source_state']['state']) for r in call(k, 'office.list')['documents']])
seen = []
real = Kernel.dispatch
def spy(self, operation, arguments=None, principal=None, *a, **kw):
    seen.append(operation); return real(self, operation, arguments, principal, *a, **kw)
a = rows()
with patch.object(Kernel, 'dispatch', spy):
    for _ in range(3): f, r = read_field(k, P)
b = rows()
print('three readings: nested reads seen: %s | journal/audit rows %s -> %s | problems %r' % ({op: seen.count(op) for op in ('notebook.get', 'notebook.resolve', 'book.contents')}, a, b, problems(r)))
with k.db() as db:
    for seq, payload in db.execute('SELECT seq,payload FROM activity_journal ORDER BY seq DESC LIMIT 3'): ev = json.loads(payload); print('   last journal rows:', seq, ev.get('operation'), ev.get('state'))
