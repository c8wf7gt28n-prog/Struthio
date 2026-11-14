import sys, time, json, os
sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/rules-lens')
from common import *
from workbench import field_page
from workbench.engineering_kernel import operator
open_window(); settle(50, 10)
k = w.ledger_bridge.kernel; p = operator()
def call(op, args=None):
    r = k.dispatch(op, args or {}, p)
    if not r.get('ok'): print('   REFUSED', op, r.get('error')); return None
    return r['result']
# 1. an ordinary imported CSV sheet (the Office room's own import, on the disposable copy)
csv = RUN / 'parts.csv'; csv.write_text('part,qty\nR1,2\nC1,4\n')
plan = call('office.import.preview', {'path': str(csv)})
print('import preview keys:', sorted(plan)[:12] if plan else None)
made = call('office.import.commit', {'plan': plan['id'], 'expected_digest': plan['digest']}) if plan else None
print('imported sheet commit keys:', sorted(made) if made else None)
if made and 'id' not in made: made = made.get('saved') or made.get('document') or next((r for r in call('office.list')['documents'] if r['title'].lower().startswith('parts')), None)
print('imported sheet:', made and made.get('id'))
if made:
    got = call('office.get', {'id': made['id']}); print('  office.get source_state of the imported CSV:', got['source_state'])
# 2. a prose Office document copied from a notebook
nb = call('notebook.create', {'title': 'Probe notebook'})
print('notebook keys:', sorted(nb) if nb else None)
if nb:
    doc = call('office.from.notebook', {'notebook': nb['id'], 'expected_revision': nb['revision']})
    print('office doc from notebook:', {k2: doc.get(k2) for k2 in ('id', 'title')} if doc else None)
    if doc:
        got = call('office.get', {'id': doc['id']}); print('  office.get source_state of the notebook copy:', got['source_state'], '| listing kind:', [r['kind'] for r in call('office.list')['documents'] if r['id'] == doc['id']])
settle(50, 10)
A = snapshot()
for n in range(3):
    w.show_field(); settle(30, 4); field_page.leave_field(w); settle(30, 4)
B = snapshot(); diff(A, B, 'FIELD shown 3 times with one CSV sheet and one notebook-derived Office document present')
w.show_field(); settle(30, 4)
v = w.field_page.view
print('census:', v.field.census(), '| refused:', w.field_page.refused)
for o in v.field.objects:
    if o.kind == 'sheet': print('   %-10s %-34s role=%-16s state=%-8s lines=%s' % (o.kind, o.title[:34], o.role, o.state, o.lines))
import sqlite3
db = sqlite3.connect('file:%s?mode=ro' % (RUN / 'ws/.ledger/engineering.sqlite3'), uri=True)
for seq, payload in db.execute('SELECT seq,payload FROM activity_journal ORDER BY seq DESC LIMIT 8'):
    ev = json.loads(payload); print('   journal', seq, ev.get('origin'), ev.get('operation'), ev.get('state'))
OUT = L / 'out/kinds'; OUT.mkdir(parents=True, exist_ok=True)
align(); w.grab().save(str(OUT / 'field_with_csv_and_notebook_copy.png'), 'PNG')
w._closing = True; print('DONE')
