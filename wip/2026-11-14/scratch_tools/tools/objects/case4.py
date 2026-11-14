import sys, json; sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/objects')
import common; ws, prof = common.copy_case(); common.setup(profile=prof, workspace=ws)
from workbench.engineering_kernel import Kernel, operator
from collections import Counter
k = Kernel(ws); p = operator(); common.hold_processes()
def call(op, args=None):
    v = k.dispatch(op, args or {}, p)
    if not v['ok']:
        print('!!', op, args, v['error']); return None
    return v['result']
ns = call('intake.namespaces')['namespaces'][0]['id']; item = 'c1d3fc85730d57bc35404c6065dbe1dc'
print('##### references.pdf.info'); r = call('references.pdf.info', {'namespace': ns, 'item': item}); print(common.short(r, 900))
print('##### references.pdf.annotations'); r = call('references.pdf.annotations', {'namespace': ns, 'item': item}); print(common.short(r, 1500))
for it in call('intake.items', {'namespace': ns})['items']:
    a = call('references.pdf.annotations', {'namespace': ns, 'item': it['id']}); print('   annotations', it['name'], len((a or {}).get('annotations', [])) if isinstance(a, dict) else a)
print('##### references.passages'); r = call('references.passages', {'namespace': ns, 'item': item}); print(common.short(r, 700))
print('##### references.impact'); r = call('references.impact', {'namespace': ns, 'item': item}); print(common.short(r, 900))
print('##### intake.read'); r = call('intake.read', {'id': item}); print(sorted(r) if r else r, common.short(r, 500))
print('##### ledger.cabinet'); r = call('ledger.cabinet', {'limit': 200}); print('keys', sorted(r))
nodes = r.get('nodes') or r.get('items') or []
print('count', len(nodes), Counter(n.get('role') or n.get('kind') for n in nodes)); [print('  ', common.short(n, 420)) for n in nodes[:4]]
for n in nodes:
    if n.get('role') in ('document', 'investigation', 'office', 'reference', 'source', 'intake') or 'document' in str(n.get('id')): print('  >', common.short({x: n.get(x) for x in ('id', 'label', 'role', 'parent', 'revision', 'provider', 'canonical_id', 'scope', 'open', 'destination')}, 420))
print('##### ledger.explore'); r = call('ledger.explore', {'limit': 50}); print('keys', sorted(r)); common.shape(r, depth=2, n=300)
print('##### ledger.object.current'); print(common.short(call('ledger.object.current'), 600))
print('##### ledger.address.read document'); d = call('documents.list')['documents'][0]; r = call('ledger.address.read', {'address': 'document:' + d['id']}); print(sorted(r), r['operation'], r['arguments'], sorted(r['object']))
print('##### ledger.trail.list'); r = call('ledger.trail.list', {'limit': 5}); print('keys', sorted(r)); common.shape(r, depth=2, n=200)
