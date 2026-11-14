import sys; sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/objects')
import common; ws, prof = common.copy_case(); common.setup(profile=prof, workspace=ws)
from workbench.engineering_kernel import Kernel, operator
k = Kernel(ws); p = operator(); common.hold_processes()
def call(op, args=None):
    v = k.dispatch(op, args or {}, p)
    if not v['ok']:
        print('!!', op, args, v['error']); return None
    return v['result']
print('##### office.get per sheet')
for row in call('office.list')['documents']:
    s = call('office.get', {'id': row['id']})
    print('--', row); print('   keys', sorted(s)); print('   revision', s['revision'][:12], 'source_state', s['source_state'])
    o = s['origin']; print('   origin keys', sorted(o), 'profile', o.get('profile'))
    print('   origin.pdf', common.short(o.get('pdf'), 700))
    print('   reviewed_rows', len(o.get('reviewed_rows', [])), common.short(o.get('reviewed_rows', [None])[0], 500))
    d = s['document']; print('   document keys', sorted(d), 'sheets', [(x.get('name'), len(x.get('cells', {}))) for x in d.get('sheets', [])])
    cells = d['sheets'][0]['cells']; print('   cells sample', common.short({a: cells[a] for a in sorted(cells)[:8]}, 600))
print('##### documents.get per document')
for row in call('documents.list')['documents']:
    g = call('documents.get', {'id': row['id']}); doc = g['document']
    print('--', row['id'], row['title'], 'rev', row['revision']); print('   get keys', sorted(g), '| document keys', sorted(doc))
    print('   source_state', g.get('source_state')); d = doc.get('derivation')
    if d:
        print('   derivation keys', sorted(d), 'profile', d['profile'], 'sheet', d['sheet'], 'sheet_revision', d['sheet_revision'][:12])
        print('   derivation.pdf', common.short(d['pdf'], 500)); print('   derivation.inputs[0]', common.short(d['inputs'][0], 500))
        print('   derivation.recipe', common.short(d['recipe'], 300)); print('   calculation keys', sorted(d['calculation']), common.short(d['calculation'].get('outputs'), 400))
    print('   events', common.short(g['events'], 300))
