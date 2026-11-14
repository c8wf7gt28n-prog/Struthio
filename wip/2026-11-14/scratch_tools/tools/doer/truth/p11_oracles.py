exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/truth/common.py').read())
for text in ('@document:%s | pick source_state | where state=CURRENT' % SETTLED, '@office:%s | pick document.sheets | select cells.B3.value,cells.C3.value' % BENCH,
             '@intake:%s | select name,sha256,decision' % PDF_BENCH, '@condition:%s' % ('0' * 32)):
    r = L('language.run', {'text': text}); print('   -> rows:', short(r.get('rows'), 300) if r else None)
c1 = L('investigation.check', {'claim': F_SETTLED, 'program': '@document:%s | pick source_state | where state=CURRENT' % SETTLED, 'oracle': 'The settled power calculation agrees with its sheet.', 'expect': 'COUNT_AT_LEAST', 'value': '1', 'refutes_on_fail': True})
c2 = L('investigation.check', {'claim': F_SETTLED, 'program': '@office:%s | pick document.sheets | select cells.B3.value,cells.C3.value' % BENCH, 'oracle': 'The settled current on the bench sheet is 280 mA.', 'expect': 'CONTAINS', 'value': '"cells.B3.value": "280"', 'refutes_on_fail': True})
L('investigation.add_source', {'id': INV, 'address': 'document:' + SETTLED}); L('investigation.add_source', {'id': INV, 'address': 'office:' + BENCH})
r = L('investigation.continue', {'id': INV}); print('   -> ran', [x['outcome'] for x in r['ran']])
sheet = L('office.get', {'id': BENCH}); doc2 = copy.deepcopy(sheet['document']); doc2['sheets'][0]['cells']['B3']['value'] = '300'
L('office.save', {'id': BENCH, 'expected_revision': sheet['revision'], 'document': doc2}, 'B3 -> 300', hide=('document',))
r = L('investigation.refresh', {'id': INV}); print('   -> changed', r['changed'])
L('investigation.review', {'claim': F_SETTLED, 'decision': 'ACCEPT_CHANGE'})
r = L('investigation.continue', {'id': INV}); print('   -> ran', [x['outcome'] for x in r['ran']], '| state', r['state'], '| next', r['next'])
pth = L('investigation.path', {'claim': F_SETTLED}); print('   -> evidence_state', pth['evidence_state'], 'support', pth['independent_support'], 'opposition', pth['independent_opposition'], [(x['kind'], x['direction'], x.get('outcome'), x['counts']) for x in pth['path']])
f = field('after the checks ran again'); print('   the finding:', [(o.state, o.lines) for o in f.objects if o.id == 'claim:' + F_SETTLED])
s = L('investigation.sheet', {'id': INV}); print('   -> checked', [(c['oracle'][:40], c['last_outcome']) for c in s['checked']], '| state', s['state'], s['reason'])
