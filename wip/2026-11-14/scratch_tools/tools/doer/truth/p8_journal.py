exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/truth/common.py').read())
import os, csv, io
r = L('office.doctor'); print('   ->', short(r, 500))
r = L('ledger.journal.status'); print('   ->', short(r, 400))
j0 = L('ledger.journal.read', {'limit': 5}); print('   -> keys', sorted(j0), '| one event:', short((j0.get('events') or j0.get('entries') or [None])[-1], 600))
mark = (j0.get('events') or j0.get('entries') or [{}])[-1]
print('\n########## a candidate file as the way to change cells, with a cell-level difference')
g = L('office.get', {'id': BENCH}); cells = g['document']['sheets'][0]['cells']
rows = [[cells.get('%s%d' % (c, n), {}).get('value', '') for c in 'ABCDEF'] for n in range(1, 6)]; rows[2][1] = '300'
path = os.path.join(str(k.root), 'Files', 'bench_edit.csv'); os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w', newline='') as f: csv.writer(f).writerows(rows)
pv = L('office.candidate.preview', {'id': BENCH, 'expected_revision': g['revision'], 'path': path})
if pv:
    print('   -> keys', sorted(pv)); print('   -> changes:', short(pv['changes'], 900)); print('   -> losses:', short(pv['losses'], 300))
    cm = L('office.candidate.commit', {'plan': pv['id'], 'expected_digest': pv['digest']}); print('   ->', cm)
    g2 = L('office.get', {'id': BENCH}); print('   -> version', g2['version'], 'B3', g2['document']['sheets'][0]['cells']['B3'])
out = L('office.datasheet.recheck', {'id': SETTLED, 'expected_revision': 2})
if out: print('   -> new calc', out['document']['id'], [(i['cell'], i['value'], i['basis']) for i in out['document']['derivation']['inputs']], out['calculation']['outputs'][0]['value']['decimal'])
r = L('investigation.refresh', {'id': INV}); r = L('investigation.continue', {'id': INV})
print('\n########## what the journal holds for those writes')
j = L('ledger.journal.read', {'limit': 60})
ev = j.get('events') or j.get('entries') or []
for e in ev[-24:]: print('   ', short({kk: e.get(kk) for kk in ('seq', 'operation', 'state', 'actor', 'kind', 'action', 'summary', 'words') if e.get(kk) is not None}, 300))
if out:
    d = L('documents.get', {'id': out['document']['id']}); print('   -> page events:', d['events'])
d = L('documents.get', {'id': SETTLED}); print('   -> old page events:', d['events'])
r = L('ledger.trail.list', {'limit': 5}); print('   -> trail:', short(r, 700))
r = L('intake.item', {'id': PDF_BENCH}); print('   -> decisions on the source:', [(x['decision'], x['reason'], x['id'][:8]) for x in r['decisions']])
