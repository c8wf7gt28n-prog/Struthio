import sys; sys.path.insert(0, '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/objects')
import common; ws, prof = common.copy_case(); common.setup(profile=prof, workspace=ws)
from workbench.engineering_kernel import Kernel, operator
k = Kernel(ws); p = operator(); common.hold_processes()
def call(op, args=None):
    v = k.dispatch(op, args or {}, p)
    if not v['ok']:
        print('!!', op, args, v['error']); return None
    return v['result']
inv = call('investigation.list')['investigations'][0]
s = call('investigation.sheet', {'id': inv['id']})
print('##### investigation.sheet keys', sorted(s)); print('question', s['question'], '| objective', s['objective'], '| state', s['state'], '| budget', s['budget'], '| used', s['used'], '| next', s['next'])
print('read (sources):')
for r in s['read']: print('  ', common.short(r, 400))
print('attempted:'); [print('  ', common.short(r, 700)) for r in s['attempted']]
print('checked:'); [print('  ', common.short(r, 900)) for r in s['checked']]
print('learned:'); [print('  ', common.short(r, 500)) for r in s['learned']]
print('unresolved:'); [print('  ', common.short(r, 500)) for r in s['unresolved']]
print('retired:', len(s['retired']))
for c in s['learned'] + s['unresolved']:
    pth = call('investigation.path', {'claim': c['id']}); print('path', c['id'][:8], c['role'], pth['evidence_state'], common.short(pth['path'], 900))
ns = call('intake.namespaces')['namespaces'][0]['id']
print('##### references.sources'); r = call('references.sources', {'namespace': ns}); common.shape(r, depth=3, n=260)
print('##### references.status'); common.shape(call('references.status', {'namespace': ns}), depth=2, n=200)
print('##### references.collection'); common.shape(call('references.collection', {'namespace': ns}), depth=2, n=200)
print('##### intake.items'); r = call('intake.items', {'namespace': ns}); common.shape(r, depth=3, n=200)
print('##### intake.catalog'); r = call('intake.catalog', {'namespace': ns}); common.shape(r, depth=3, n=200)
