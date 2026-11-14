exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/truth/common.py').read())
def sheet_state(ident, tag=''):
    g = L('office.get', {'id': ident}, tag)
    if g: print('   -> title=%r version=%s source_state=%s pdf.decision=%s' % (g['document']['title'], g['version'], g['source_state'], g['origin']['pdf']['decision'][:8]))
    return g
def item_state(ident):
    r = L('intake.items', {'namespace': NS}); row = next(i for i in r['items'] if i['id'] == ident)
    print('   -> %s admission=%s decision_id=%s sha256=%s | generation %s' % (row['name'], row['admission'], (row['decision_id'] or '')[:8], row['sha256'][:10], r['generation'])); return row
print('########## S0. reads about a source')
r = L('references.pdf.info', {'namespace': NS, 'item': PDF_BENCH}); print('   ->', short({kk: vv for kk, vv in r.items() if kk != 'pages'}, 500), '| pages', len(r.get('pages', [])))
r = L('references.impact', {'namespace': NS, 'item': PDF_BENCH}); print('   ->', short(r, 700))
r = L('intake.policy', {'namespace': NS}); print('   ->', short(r, 400)); POLICY = r['policy_hash']
r = L('intake.catalog', {'namespace': NS}); print('   ->', short({kk: vv for kk, vv in r.items() if kk != 'items'}, 300), [i['name'] for i in r['items']])
r = L('intake.checkpoints', {'namespace': NS}); print('   ->', short(r, 400))
r = L('intake.status'); print('   ->', short(r, 400))
old = sheet_state(BENCH)
print('\n########## S1. READ-ONLY re-read of the reviewed region: does the page still extract the reviewed rows?')
o = old['origin']['pdf']
r = L('references.pdf.result', {'job': o['job']}, 'the render job the sheet was reviewed from'); print('   -> state', r['state'], '| result', short({kk: vv for kk, vv in (r['result'] or {}).items() if kk not in ('native', 'ocr')}, 400))
pv = L('office.datasheet.preview', {'job': o['job'], 'rect': o['rect'], 'layer': o['layer']})
if pv:
    print('   -> keys', sorted(pv), 'state', pv['state'], 'digest', pv['digest'][:12]); print('   -> rows:', [(x['source_row'], x['cells'], x['gaps']) for x in pv['rows']])
    same = [x['cells'] for x in pv['rows']] == [x['original_cells'] for x in sorted(old['origin']['reviewed_rows'], key=lambda q: q['source_row'])]
    print('   -> the page region still extracts the rows the sheet was reviewed from:', same)
print('\n########## S2. MAKE STALE: the owner withdraws the source')
cp = L('intake.checkpoint', {'namespace': NS, 'label': 'before revoke'}); print('   ->', short(cp, 400))
row = item_state(PDF_BENCH)
r = L('intake.revoke', {'id': PDF_BENCH, 'expected_decision': row['decision_id'], 'reason': 'Rehearsal: withdraw the bench readings.'}); print('   ->', short({kk: vv for kk, vv in r.items() if kk != 'assessment'}, 500))
item_state(PDF_BENCH); sheet_state(BENCH); calc_state(SETTLED)
r = L('ledger.address.read', {'address': 'intake:' + PDF_BENCH})
r = L('references.pdf.info', {'namespace': NS, 'item': PDF_BENCH})
field('after revoke, before refresh')
r = L('investigation.refresh', {'id': INV}); print('   -> changed=%s state=%s reason=%r' % (r['changed'], r['state'], r['reason']))
field('after revoke and refresh')
print('\n########## S3. BRING BACK (a): accept the same file again')
it = L('intake.item', {'id': PDF_BENCH}); print('   -> assessment.recommendation', it['assessment']['recommendation'], 'eligible', it['assessment']['eligible'], 'reasons', it['assessment']['reasons'])
r = L('intake.decide', {'id': PDF_BENCH, 'decision': 'ACCEPTED', 'expected_sha256': it['sha256'], 'expected_policy_hash': it['policy_hash'], 'expected_decision': it['decision_id'], 'reason': 'Rehearsal: admit again.'}); print('   ->', short({kk: vv for kk, vv in (r or {}).items() if kk != 'assessment'}, 500))
item_state(PDF_BENCH); sheet_state(BENCH, 'the sheet after its source was admitted again'); calc_state(SETTLED)
r = L('investigation.refresh', {'id': INV}); print('   -> changed=%s state=%s reason=%r' % (r['changed'], r['state'], r['reason']))
s = inv_state()
field('after re-admission')
print('\n########## S4. BRING BACK (b): review the sheet again from the page (a new sheet), then the calculation')
job = L('references.pdf.page', {'namespace': NS, 'item': PDF_BENCH, 'source_sha256': o['source_sha256'], 'page_index': o['page_index']}); print('   -> job', short({kk: job.get(kk) for kk in ('id', 'state', 'tool')}, 300))
done = wait_job(job['id'], 120, 'render')
r = L('references.pdf.result', {'job': job['id']}); print('   -> state', r['state'], '| result', short({kk: vv for kk, vv in (r['result'] or {}).items() if kk not in ('native', 'ocr')}, 500))
pv = L('office.datasheet.preview', {'job': job['id'], 'rect': o['rect'], 'layer': o['layer']})
if pv:
    print('   -> state', pv['state'], 'digest', pv['digest'][:12], 'rows', [(x['source_row'], x['parameter'], x['value'], x['unit'], x['conditions'], x['gaps']) for x in pv['rows']])
    rows = [{kk: x[kk] for kk in ('source_row', 'parameter', 'value', 'unit', 'conditions')} for x in pv['rows']]
    ns = L('office.datasheet.create', {'job': job['id'], 'rect': o['rect'], 'layer': o['layer'], 'expected_digest': pv['digest'], 'title': '07 Bench readings (reviewed again)', 'rows': rows})
    if ns:
        print('   -> NEW sheet', ns['id'], 'version', ns['version'], 'revision', ns['revision'][:12]); sheet_state(ns['id'])
        g = L('documents.get', {'id': SETTLED}); rc = g['document']['derivation']['recipe']
        rep = L('office.datasheet.report', {'id': ns['id'], 'expected_revision': ns['revision'], **rc}, 'the old recipe on the new sheet')
        if rep: print('   -> NEW calculation', rep['document']['id'], rep['document']['title'], short(rep['calculation']['outputs'][0]['value'], 200)); calc_state(rep['document']['id'])
sheet_state(BENCH, 'the OLD sheet'); calc_state(SETTLED, 'the OLD calculation')
L('office.datasheet.recheck', {'id': SETTLED, 'expected_revision': 2}, 'can the old calculation be rechecked while its sheet waits for source review?')
field('after re-review')
print('\n########## S5. another way back: restore the catalog checkpoint (tried on Rev A)')
cp2 = L('intake.checkpoint', {'namespace': NS, 'label': 'before revoking Rev A'}); row = item_state(PDF_REVA)
L('intake.revoke', {'id': PDF_REVA, 'expected_decision': row['decision_id'], 'reason': 'Rehearsal: withdraw Rev A.'}); sheet_state(REVA)
gen = L('intake.items', {'namespace': NS})['generation']
r = L('intake.catalog.restore', {'id': cp2['id'] if cp2 and 'id' in cp2 else '', 'expected_generation': gen, 'reason': 'Rehearsal: undo the withdrawal.'}); print('   ->', short(r, 500))
item_state(PDF_REVA); sheet_state(REVA, 'after the restore')
print('\n########## THE SEQUENCE'); print('\n'.join(LINES))
