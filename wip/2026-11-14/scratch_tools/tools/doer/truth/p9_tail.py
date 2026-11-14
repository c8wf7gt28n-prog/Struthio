exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/truth/common.py').read())
head = L('ledger.journal.status')['head']
sheet = L('office.get', {'id': BENCH}); doc2 = copy.deepcopy(sheet['document']); doc2['sheets'][0]['cells']['B3']['value'] = '300'
L('office.save', {'id': BENCH, 'expected_revision': sheet['revision'], 'document': doc2}, hide=('document',))
out = L('office.datasheet.recheck', {'id': SETTLED, 'expected_revision': 2})
L('investigation.add_source', {'id': INV, 'address': 'document:' + out['document']['id']})
L('investigation.refresh', {'id': INV}); L('investigation.continue', {'id': INV})
L('investigation.review', {'claim': F_SETTLED, 'decision': 'ACCEPT_CHANGE'})
j0 = L('ledger.journal.read', {'limit': 1}); print('   cursor', j0.get('cursor'), 'head', j0.get('head'), type(j0.get('cursor'))); j = L('ledger.journal.read', {'after': str(head), 'limit': 100})
for e in j['events']: print('   ', e['seq'], e['operation'], e['state'], '|', e.get('origin'), '|', str(e.get('detail'))[:120])
d = L('documents.get', {'id': out['document']['id']}); print('   -> new page events:', d['events'], '| last_change', d['document']['last_change'])
import sqlite3
from workbench.office_service import path as office_path
db = sqlite3.connect(str(office_path())); 
print('   office catalog tables:', [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")])
try: print('   office events tail:', db.execute('SELECT * FROM events ORDER BY rowid DESC LIMIT 3').fetchall())
except Exception as exc: print('   (no events table read:', exc, ')')
print('   office history rows for the sheet:', db.execute('SELECT id, version, length(payload) FROM office_history').fetchall())
