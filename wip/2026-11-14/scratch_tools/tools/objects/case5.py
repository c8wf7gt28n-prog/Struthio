import sys, json; sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/objects')
import common; ws, prof = common.copy_case(); common.setup(profile=prof, workspace=ws)
from workbench.engineering_kernel import Kernel, operator
k = Kernel(ws); p = operator(); common.hold_processes()
def call(op, args=None):
    v = k.dispatch(op, args or {}, p)
    if not v['ok']: print('!!', op, args, v['error']); return None
    return v['result']
r = call('references.pdf.result', {'job': '61234750570a46209b6af69f1e391573'})
print('references.pdf.result keys', sorted(r) if r else r)
if r: print({x: (r[x] if not isinstance(r[x], (dict, list)) else type(r[x]).__name__ + '(%d)' % len(r[x])) for x in r}); print('image exists', (ws / r['image']).is_file() if r.get('image') else None)
j = call('jobs.get', {'id': '61234750570a46209b6af69f1e391573'}); print('jobs.get keys', sorted(j)); print('request_spec', common.short(j.get('request_spec'), 500))
e = call('evidence.read', {'id': j['evidence']}); print('evidence.read keys', sorted(e))
print('ledger.related sample', common.short(call('ledger.related', {'text': 'Startup pulse exceeds the Rev B duration condition 80 ms; settled power 3.36 W', 'limit': 5}), 900))
print('math.evaluate (read) sample', common.short(call('math.evaluate', {'model': {'schema': 'x'}}), 200))
print('ledger.address.kinds n', len(call('ledger.address.kinds')['kinds']))
print('address intake:', sorted(call('ledger.address.read', {'address': 'intake:c1d3fc85730d57bc35404c6065dbe1dc'})['object']))
print('office address:', sorted(call('ledger.address.read', {'address': 'office:owner:4f357ff3c843489a9758db71e23bf4b4'})['object']))
res = r['result']; print('pdf result keys', sorted(res)); print({x: res[x] for x in ('status', 'image', 'page_index', 'name', 'layer') if x in res}, '| image file exists', (ws / res['image']).is_file() if res.get('image') else None, '| native keys', sorted(res['native']) if isinstance(res.get('native'), dict) else res.get('native'))
