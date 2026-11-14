exec(open('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/doer/truth/common.py').read())
import os, csv
from workbench.engineering_kernel import Principal
print('########## M1. what a read-only principal may run')
ro = Principal(p.identity, frozenset({'read'}), p.paths, p.tools, p.mode)
for op, args in (('investigation.sheet', {'id': INV}), ('conditions.list', {}), ('office.get', {'id': BENCH}), ('documents.get', {'id': SETTLED}), ('ledger.address.read', {'address': 'intake:' + PDF_BENCH}),
                 ('office.datasheet.preview', {'job': '61234750570a46209b6af69f1e391573', 'rect': [0.075, 0.315, 0.855, 0.34], 'layer': 'native'}), ('intake.item', {'id': PDF_BENCH}),
                 ('investigation.refresh', {'id': INV}), ('investigation.continue', {'id': INV}), ('conditions.recheck', {'id': '0' * 32}), ('office.datasheet.recheck', {'id': SETTLED, 'expected_revision': 2})):
    r = k.dispatch(op, args, ro); print('   %-28s %s' % (op, 'ok' if r['ok'] else 'REFUSED: ' + r['error']['message'][:80]))
ex = Principal(p.identity, frozenset({'read', 'execute'}), p.paths, p.tools, p.mode)
for op, args in (('investigation.refresh', {'id': INV}), ('investigation.continue', {'id': INV}), ('office.datasheet.recheck', {'id': SETTLED, 'expected_revision': 2}), ('investigation.review', {'claim': F_SETTLED, 'decision': 'ACCEPT_CHANGE'}), ('office.save', {'id': BENCH, 'expected_revision': '0' * 64, 'document': {}})):
    r = k.dispatch(op, args, ex); print('   read+execute %-28s %s' % (op, 'ok' if r['ok'] else 'REFUSED: ' + r['error']['message'][:80]))
print('\n########## M2. a sheet from a file (not a PDF): its original changes')
path = os.path.join(str(k.root), 'Files', 'loads.csv'); os.makedirs(os.path.dirname(path), exist_ok=True)
open(path, 'w').write('Load,Power\nFan,1.5\nPump,2.5\n')
pv = L('office.import.preview', {'path': path}); print('   -> keys', sorted(pv), 'mode', pv['mode'])
cm = L('office.import.commit', {'plan': pv['id'], 'expected_digest': pv['digest']}); print('   ->', cm); SID = cm['document_id']
g = L('office.get', {'id': SID}); print('   -> source_state', g['source_state'], '| origin keys', sorted(g['origin']))
open(path, 'w').write('Load,Power\nFan,1.5\nPump,3.5\n')
g = L('office.get', {'id': SID}, 'after the file on disk changed'); print('   -> source_state', g['source_state'])
f = field('file sheet stale'); print('   in the Field:', [(o.title, o.state, o.lines) for o in f.objects if o.id == 'office:' + SID])
pv = L('office.candidate.preview', {'id': SID, 'expected_revision': g['revision'], 'path': path}); print('   -> changes', short(pv['changes'], 500))
cm = L('office.candidate.commit', {'plan': pv['id'], 'expected_digest': pv['digest']}); print('   ->', cm)
g = L('office.get', {'id': SID}, 'after the changed original was taken in'); print('   -> version', g['version'], 'source_state', g['source_state'])
print('\n########## M3. a source held at review')
it = L('intake.item', {'id': PDF_REVA})
L('intake.decide', {'id': PDF_REVA, 'decision': 'HELD', 'expected_sha256': it['sha256'], 'expected_policy_hash': it['policy_hash'], 'expected_decision': it['decision_id'], 'reason': 'Rehearsal: hold Rev A.'})
f = field('with a held source'); 
r = L('intake.items', {'namespace': NS, 'state': 'HELD'}); print('   ->', [(i['name'], i['admission'], i['reasons']) for i in r['items']])
