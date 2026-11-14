exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/truth/common.py').read())
print('########## A. BASELINE'); field('baseline')
L('conditions.list'); calc_state(SETTLED); inv_state()
print('\n########## A1. MAKE STALE: change one input cell of the reviewed sheet (B3 280 -> 300 mA)')
sheet = L('office.get', {'id': BENCH}); print('   -> version=%s revision=%s source_state=%s' % (sheet['version'], sheet['revision'], sheet['source_state']))
doc2 = copy.deepcopy(sheet['document']); doc2['sheets'][0]['cells']['B3']['value'] = '300'
saved = L('office.save', {'id': BENCH, 'expected_revision': sheet['revision'], 'document': doc2}, 'document = office.get().document with sheets[0].cells.B3.value="300"', hide=('document',))
print('   -> keys', sorted(saved), 'version=%s revision=%s' % (saved['version'], saved['revision']))
print('\n########## A2. WHAT THE READS SAY')
s2 = L('office.get', {'id': BENCH}); print('   -> version=%s revision=%s source_state=%s' % (s2['version'], s2['revision'], s2['source_state']))
print('   ->', L('conditions.list'))
g_settled = calc_state(SETTLED, 'the calculation that uses B2,B3'); g_startup = calc_state(STARTUP, 'the calculation that uses B2,B4 (cells unchanged)')
inv_state('before any refresh')
field('after the cell edit')
print('\n   stac reads of the same thing:')
for text in ('documents.get {"id":"%s"} | select source_state.state' % SETTLED, '@document:%s | select source_state.state,summary.title' % SETTLED,
             'office.get {"id":"%s"} | select source_state.state,version' % BENCH):
    r = L('language.run', {'text': text}); print('   ->', short(r, 500))
r = L('investigation.refresh', {'id': INV}, 'compare every registered source of the investigation again'); print('   -> changed:', r['changed'], '| state', r['state'], '| next', r['next'])
print('\n########## A3. BRING BACK: recompute the calculation from its recorded recipe')
out = L('office.datasheet.recheck', {'id': SETTLED, 'expected_revision': g_settled['document']['revision']})
if out:
    nd = out['document']; print('   -> result keys', sorted(out), '| NEW document id=%s title=%r revision=%s' % (nd['id'], nd['title'], nd['revision']))
    print('   -> calculation:', short(out['calculation']['outputs'], 400))
    print('   -> derivation.inputs:', [(i['symbol'], i['cell'], i['parameter'], i['value'], i['unit'], i['conditions'], i['basis']) for i in nd['derivation']['inputs']])
    print('   -> derivation.recipe:', nd['derivation']['recipe'], '| sheet_revision', nd['derivation']['sheet_revision'][:12])
    NEW_SETTLED = nd['id']
    calc_state(SETTLED, 'the OLD calculation after the recheck'); calc_state(NEW_SETTLED, 'the NEW calculation')
out2 = L('office.datasheet.recheck', {'id': STARTUP, 'expected_revision': g_startup['document']['revision']})
if out2: NEW_STARTUP = out2['document']['id']; print('   -> NEW document', NEW_STARTUP, out2['document']['title'])
r = L('documents.list'); print('   -> documents:', [(d['id'][:8], d['title'], d['revision']) for d in r['documents']])
field('after both rechecks')
print('\n########## A4. Can the old stale calculation be settled? try: put the cell back')
s3 = L('office.get', {'id': BENCH}); doc3 = copy.deepcopy(s3['document']); doc3['sheets'][0]['cells']['B3']['value'] = '280'
saved3 = L('office.save', {'id': BENCH, 'expected_revision': s3['revision'], 'document': doc3}, 'B3 back to 280', hide=('document',)); print('   -> version', saved3['version'], 'revision', saved3['revision'][:12], '(first was 69dada6fef72)')
calc_state(SETTLED, 'OLD calc after the cell was put back'); calc_state(NEW_SETTLED, 'NEW calc (made at 300) after the cell was put back')
print('\n########## A5. THE UNIT CHECK: make the unit of B3 wrong (mA -> s) and recheck')
s4 = L('office.get', {'id': BENCH}); doc4 = copy.deepcopy(s4['document']); doc4['sheets'][0]['cells']['C3']['value'] = 's'
L('office.save', {'id': BENCH, 'expected_revision': s4['revision'], 'document': doc4}, 'C3 unit mA -> s', hide=('document',))
g = calc_state(NEW_SETTLED); L('office.datasheet.recheck', {'id': NEW_SETTLED, 'expected_revision': g['document']['revision']}, 'expect the unit check to refuse')
s5 = L('office.get', {'id': BENCH}); doc5 = copy.deepcopy(s5['document']); doc5['sheets'][0]['cells']['C3']['value'] = 'mA'; doc5['sheets'][0]['cells']['A3']['value'] = 'Idle current'
L('office.save', {'id': BENCH, 'expected_revision': s5['revision'], 'document': doc5}, 'unit back; parameter name of row 3 changed', hide=('document',))
L('office.datasheet.recheck', {'id': NEW_SETTLED, 'expected_revision': g['document']['revision']}, 'expect: names a different parameter')
print('\n########## direct exact calculator reads (no sheet)')
r = L('math.evaluate', {'model': g['document']['derivation']['calculation'].get('model', {})}) if g['document']['derivation']['calculation'].get('model') else None
print('   calc keys:', sorted(g['document']['derivation']['calculation']))
print('\n########## THE SEQUENCE'); print('\n'.join(LINES))
