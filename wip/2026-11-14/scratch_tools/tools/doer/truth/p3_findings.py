exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/truth/common.py').read())
def path(claim, tag=''):
    r = L('investigation.path', {'claim': claim}, tag)
    print('   -> evidence_state=%s support=%s opposition=%s review=%s' % (r['evidence_state'], r['independent_support'], r['independent_opposition'], r['review']))
    for s in r['path']: print('      step', {kk: (str(vv)[:70]) for kk, vv in s.items() if kk in ('kind', 'direction', 'address', 'program', 'outcome', 'counts', 'source_state', 'inputs')})
    return r
print('########## B0. shape of a staC read used as a check program')
for text in ('@document:%s | select source_state.state' % SETTLED,
             '@document:%s | pick document.derivation.calculation.outputs | select value.decimal,value.unit' % SETTLED,
             '@office:%s | pick document.sheets | pick cells | select B3.value,C3.value' % BENCH):
    r = L('language.run', {'text': text})
    if r: print('   -> keys', sorted(r), '| rows:', short(r.get('rows'), 300), '| value:', short(r.get('value'), 200), '| count', r.get('count'))
print('\n########## B1. bind a finding to the calculation it quotes: two checks and two registered sources')
c1 = L('investigation.check', {'claim': F_SETTLED, 'program': '@document:%s | pick document.derivation.calculation.outputs | select value.decimal,value.unit' % SETTLED,
        'oracle': 'The settled power calculation gives 3.36 W.', 'expect': 'CONTAINS', 'value': '"value.decimal": "3.36"'}); print('   ->', c1)
c2 = L('investigation.check', {'claim': F_SETTLED, 'program': '@document:%s | select source_state.state' % SETTLED,
        'oracle': 'The settled power calculation still agrees with its sheet.', 'expect': 'NOT_CONTAINS', 'value': 'RECHECK_SHEET_CHANGED', 'refutes_on_fail': True}); print('   ->', c2)
r = L('investigation.continue', {'id': INV}, 'run what is due: the two new checks'); print('   -> ran=%s authority=%s state=%s next=%s' % (r['ran'], r['authority'], r['state'], r['next']))
a1 = L('investigation.add_source', {'id': INV, 'address': 'document:' + SETTLED}); print('   ->', a1)
a2 = L('investigation.add_source', {'id': INV, 'address': 'office:' + BENCH}); print('   ->', a2)
inv_state(); path(F_SETTLED)
print('\n########## B2. change the cell')
sheet = L('office.get', {'id': BENCH}); doc2 = copy.deepcopy(sheet['document']); doc2['sheets'][0]['cells']['B3']['value'] = '300'
L('office.save', {'id': BENCH, 'expected_revision': sheet['revision'], 'document': doc2}, 'B3 280 -> 300', hide=('document',))
print('\n########## B3. READ-ONLY check of the investigation: read each registered source again and compare digests (no write)')
s = L('investigation.sheet', {'id': INV})
for row in s['read']:
    if row['state'] != 'CURRENT': continue
    got = L('ledger.address.read', {'address': row['address']})
    now = sha_obj(got['object']) if got else 'UNAVAILABLE'
    print('   -> %s recorded %s now %s  %s' % (row['address'][:40], row['digest'][:10], now[:10], 'SAME' if now == row['digest'] else 'CHANGED'))
field('before refresh (the Field has not noticed the findings yet)')
print('\n########## B4. the write that notices')
r = L('investigation.refresh', {'id': INV}); print('   -> changed=%s state=%s reason=%r next=%s' % (r['changed'], r['state'], r['reason'], r['next']))
inv_state(); path(F_SETTLED); field('after refresh')
print('\n########## B5. continue while a review is due: does it rerun the stale checks?')
r = L('investigation.continue', {'id': INV}); print('   -> ran=%s state=%s next=%s' % (r['ran'], r['state'], r['next']))
print('\n########## B6. owner decision, then rerun')
r = L('investigation.review', {'claim': F_SETTLED, 'decision': 'ACCEPT_CHANGE'}); print('   -> keys', sorted(r), 'review', r['review'], 'evidence_state', r['evidence_state'])
inv_state('after ACCEPT_CHANGE')
r = L('investigation.continue', {'id': INV}); print('   -> ran=%s state=%s reason=%r next=%s' % (r['ran'], r['state'], r['reason'], r['next']))
inv_state(); path(F_SETTLED); field('after review + continue')
print('\n########## B7. repair the calculation, then the finding')
g = L('documents.get', {'id': SETTLED}); out = L('office.datasheet.recheck', {'id': SETTLED, 'expected_revision': g['document']['revision']}); NEW = out['document']['id']; print('   -> new calculation', NEW)
r = L('investigation.review', {'claim': F_SETTLED, 'decision': 'RETIRE'}, 'the words "3.36 W" are no longer true'); print('   ->', r['review'], r['evidence_state'])
n = L('investigation.claim', {'id': INV, 'text': 'Settled draw is 3.6 W. Rev B allows 6 W.', 'role': 'FINDING'}); print('   ->', n)
a = L('investigation.add_source', {'id': INV, 'address': 'document:' + NEW}); print('   ->', a)
e = L('investigation.evidence', {'claim': n['claim'], 'direction': 'SUPPORTS', 'source': a['source'], 'note': 'The recomputed calculation.'}); print('   -> keys', sorted(e), e['evidence_state'])
c = L('investigation.check', {'claim': n['claim'], 'program': '@document:%s | pick document.derivation.calculation.outputs | select value.decimal,value.unit' % NEW,
       'oracle': 'The settled power calculation gives 3.6 W.', 'expect': 'CONTAINS', 'value': '"value.decimal": "3.6"'}); print('   ->', c)
r = L('investigation.continue', {'id': INV}); print('   -> ran=%s state=%s reason=%r next=%s' % (r['ran'], r['state'], r['reason'], r['next']))
inv_state(); path(n['claim']); field('after the repair')
print('\n########## THE SEQUENCE'); print('\n'.join(LINES))
